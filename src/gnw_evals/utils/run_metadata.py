"""Helpers for eval run metadata shown in the E2E summary."""

import os
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from gnw_evals.utils.models import HAIKU


@dataclass(frozen=True)
class LatencyStats:
    """Per-test latency statistics in seconds."""

    count: int
    avg: float
    std: float
    min: float
    max: float


@dataclass(frozen=True)
class RunSummaryContext:
    """Metadata printed in the SIMPLE E2E TEST SUMMARY header."""

    api_base_url: str
    environment: str
    run_timestamp: datetime
    gnw_code_version: str
    gnw_prompts_version: str
    gnw_agent_llm: str
    eval_judge_llm: str
    latency: LatencyStats | None = None


def infer_environment(api_base_url: str) -> str:
    """Map API base URL to a short environment label."""
    host = urlparse(api_base_url).netloc.lower()
    if "staging" in host:
        return "staging"
    if (
        host in {"localhost", "127.0.0.1"}
        or host.startswith("localhost:")
        or host.startswith("127.0.0.1:")
    ):
        return "localhost"
    if "globalnaturewatch.org" in host:
        return "prod"
    return "custom"


def get_eval_judge_llm_label() -> str:
    """Return the LLM family and model used by eval judges in this repo."""
    model = getattr(HAIKU, "model_name", None) or getattr(HAIKU, "model", "unknown")
    return f"Anthropic / {model}"


def _format_gnw_agent_llm(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return "unknown (metadata unavailable)"
    model_info = metadata.get("model") or {}
    current = model_info.get("current", "unknown")
    model_class = model_info.get("model_class", "unknown")
    small = model_info.get("small", "unknown")
    small_class = model_info.get("small_model_class", "unknown")
    return f"primary {current} ({model_class}), small {small} ({small_class})"


def resolve_gnw_versions(metadata: dict[str, Any] | None) -> tuple[str, str]:
    """Resolve GNW code and prompts versions from env vars or API metadata."""
    code_version = os.getenv("GNW_CODE_VERSION")
    if not code_version and metadata:
        code_version = metadata.get("version")
    if not code_version:
        code_version = "unknown"

    prompts_version = os.getenv("GNW_PROMPTS_VERSION")
    if not prompts_version:
        prompts_version = "unknown"

    return code_version, prompts_version


async def fetch_gnw_api_metadata(api_base_url: str) -> dict[str, Any] | None:
    """Fetch public /api/metadata from the GNW API."""
    url = f"{api_base_url.rstrip('/')}/api/metadata"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        print(f"Warning: could not fetch GNW API metadata from {url}: {exc}")
        return None


def compute_latency_stats(durations: list[float]) -> LatencyStats | None:
    """Compute latency statistics from per-test durations in seconds."""
    if not durations:
        return None
    return LatencyStats(
        count=len(durations),
        avg=statistics.mean(durations),
        std=statistics.stdev(durations) if len(durations) > 1 else 0.0,
        min=min(durations),
        max=max(durations),
    )


def build_run_summary_context(
    api_base_url: str,
    run_timestamp: datetime,
    api_metadata: dict[str, Any] | None,
    durations: list[float],
) -> RunSummaryContext:
    """Build summary context from API metadata, env overrides, and latencies."""
    code_version, prompts_version = resolve_gnw_versions(api_metadata)
    return RunSummaryContext(
        api_base_url=api_base_url,
        environment=infer_environment(api_base_url),
        run_timestamp=run_timestamp,
        gnw_code_version=code_version,
        gnw_prompts_version=prompts_version,
        gnw_agent_llm=_format_gnw_agent_llm(api_metadata),
        eval_judge_llm=get_eval_judge_llm_label(),
        latency=compute_latency_stats(durations),
    )


def format_run_timestamp(run_timestamp: datetime) -> str:
    """Format run timestamp for console output."""
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.replace(tzinfo=UTC)
    return run_timestamp.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def print_run_summary_header(context: RunSummaryContext) -> None:
    """Print run metadata block before metric lines."""
    print(f"Environment:           {context.environment}")
    print(f"API Base URL:          {context.api_base_url}")
    print(f"Run timestamp:         {format_run_timestamp(context.run_timestamp)}")
    print(f"GNW code version:      {context.gnw_code_version}")
    print(f"GNW prompts version:   {context.gnw_prompts_version}")
    print(f"GNW agent LLM:         {context.gnw_agent_llm}")
    print(f"Eval judge LLM:        {context.eval_judge_llm}")
    if context.latency:
        latency = context.latency
        print(
            "API latency (s):       "
            f"avg={latency.avg:.1f}, std={latency.std:.1f}, "
            f"min={latency.min:.1f}, max={latency.max:.1f} "
            f"(n={latency.count})",
        )
    else:
        print("API latency (s):       n/a")
    print()
