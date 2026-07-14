"""Ground-truth client for the GNW analytics API.

Fetches the expected numbers for ground-truth eval cases (rows with an
``intent``) directly from the analytics API the agent itself uses
(https://analytics.globalnaturewatch.org). Because both sides share one data
source, the scores measure retrieval/usage fidelity, not data correctness.

The API is async (POST returns a poll link) and idempotent: the resource id is
a UUID5 of the request payload, so repeated fetches are effectively cached.
"""

import asyncio
import os
from typing import Any

import httpx

from gnw_evals.utils.eval_types import ExpectedData
from gnw_evals.utils.run_metadata import infer_environment

ANALYTICS_BASE_URL = os.getenv(
    "ANALYTICS_API_BASE_URL",
    "https://analytics.globalnaturewatch.org",
)
_TCL_ENDPOINT = "/v0/land_change/tree_cover_loss/analytics"
_POLL_TIMEOUT_SECONDS = 120.0
_MAX_CONCURRENT_FETCHES = 5


def resolve_x_environment(gnw_api_base_url: str) -> str:
    """Pick the analytics data environment matching the agent under test.

    The agent sends X-environment based on its own deployment (staging agents
    query staging analytics data), so ground truth must do the same or the
    numbers can legitimately diverge. Override with ANALYTICS_X_ENVIRONMENT
    when testing a localhost agent configured for a specific environment.
    """
    override = os.getenv("ANALYTICS_X_ENVIRONMENT")
    if override:
        return override
    environment = infer_environment(gnw_api_base_url)
    if environment == "staging":
        return "staging"
    return "production"


def build_tcl_payload(case: ExpectedData) -> dict[str, Any]:
    """Build the tree-cover-loss analytics request from a case's parameters."""
    if not case.expected_aoi_ids:
        raise ValueError(f"case {case.test_id!r} has no expected_aoi_ids")
    start_year = (case.expected_start_date or "").strip()[:4]
    end_year = (case.expected_end_date or "").strip()[:4]
    if not (start_year.isdigit() and end_year.isdigit()):
        raise ValueError(
            f"case {case.test_id!r} needs 4-digit years in expected_start_date/"
            f"expected_end_date, got {case.expected_start_date!r}/"
            f"{case.expected_end_date!r}",
        )

    payload: dict[str, Any] = {
        "aoi": {"type": "admin", "ids": case.expected_aoi_ids},
        "start_year": start_year,
        "end_year": end_year,
        "intersections": (
            [case.expected_intersections] if case.expected_intersections else []
        ),
    }
    if case.expected_canopy_cover:
        payload["canopy_cover"] = int(case.expected_canopy_cover)
    if case.expected_forest_filter:
        payload["forest_filter"] = case.expected_forest_filter
    if "canopy_cover" not in payload and "forest_filter" not in payload:
        # Product default on both sides (agent and GFW convention).
        payload["canopy_cover"] = 30
    return payload


def _columnar_to_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert the API's dict-of-arrays result into a list of row dicts."""
    columns = {k: v for k, v in result.items() if k != "__dtypes__"}
    if not columns:
        return []
    length = max(len(v) for v in columns.values())
    rows = [{k: v[i] for k, v in columns.items()} for i in range(length)]
    sort_key = (
        "tree_cover_loss_year" if "tree_cover_loss_year" in columns else "area_ha"
    )
    return sorted(rows, key=lambda r: (str(r.get("aoi_id", "")), r.get(sort_key) or 0))


async def fetch_tcl_ground_truth(
    payload: dict[str, Any],
    x_environment: str,
    client: httpx.AsyncClient,
) -> dict[str, Any]:
    """Submit a TCL analytics request and poll until the result is saved."""
    headers = {"X-environment": x_environment}
    response = await client.post(
        f"{ANALYTICS_BASE_URL}{_TCL_ENDPOINT}",
        json=payload,
        headers=headers,
    )
    response.raise_for_status()
    link = response.json()["data"]["link"]

    deadline = asyncio.get_event_loop().time() + _POLL_TIMEOUT_SECONDS
    while True:
        poll = await client.get(link, headers=headers)
        poll.raise_for_status()
        data = poll.json()["data"]
        status = data.get("status")
        if status in ("saved", "success"):
            break
        if status == "failed":
            raise RuntimeError(
                f"analytics request failed: {data.get('message')!r} ({link})",
            )
        if asyncio.get_event_loop().time() > deadline:
            raise TimeoutError(
                f"analytics result not ready after {_POLL_TIMEOUT_SECONDS:.0f}s: {link}",
            )
        retry_after = float(poll.headers.get("Retry-After", 1) or 1)
        await asyncio.sleep(retry_after)

    return {
        "rows": _columnar_to_rows(data.get("result") or {}),
        "metadata": data.get("metadata"),
        "x_environment": x_environment,
        "link": link,
    }


async def enrich_with_ground_truth(
    test_cases: list[ExpectedData],
    gnw_api_base_url: str,
) -> None:
    """Fetch and attach ground truth for every case that declares an intent.

    Fails loudly: a case whose ground truth cannot be fetched aborts the run,
    because scoring it against nothing would silently pass or fail arbitrarily.
    """
    ground_truth_cases = [c for c in test_cases if c.intent]
    if not ground_truth_cases:
        return

    x_environment = resolve_x_environment(gnw_api_base_url)
    print(
        f"Fetching analytics ground truth for {len(ground_truth_cases)} cases "
        f"(X-environment: {x_environment})...",
    )
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FETCHES)

    async with httpx.AsyncClient(timeout=30.0) as client:

        async def fetch_for_case(case: ExpectedData) -> None:
            async with semaphore:
                payload = build_tcl_payload(case)
                try:
                    case.ground_truth = await fetch_tcl_ground_truth(
                        payload,
                        x_environment,
                        client,
                    )
                except Exception as exc:
                    raise RuntimeError(
                        f"ground truth fetch failed for case {case.test_id!r}: {exc}",
                    ) from exc
                if not case.ground_truth["rows"]:
                    raise RuntimeError(
                        f"ground truth for case {case.test_id!r} is empty; "
                        f"check the case parameters ({payload})",
                    )

        await asyncio.gather(*(fetch_for_case(c) for c in ground_truth_cases))
    print("Ground truth fetched.")
