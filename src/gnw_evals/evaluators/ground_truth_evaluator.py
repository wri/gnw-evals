"""Ground-truth evaluator: two-stage numeric quality checks per intent.

Stage 1 (deterministic, ``data_fidelity_score``): the numbers the agent pulled
(thread-state ``statistics`` / ``charts_data``) must contain every ground-truth
value within a tight tolerance. The agent queries the same analytics API the
ground truth comes from, so a gap here means the agent built the wrong query
(years, canopy threshold, filter, AOI), not that the data changed.

Stage 2 (LLM judge, ``number_usage_score``): given the ground-truth table, did
the final answer use the numbers correctly for the case's intent
(quantification / comparison / trend)? The judge must justify any failure in
``number_usage_failure_comment`` and flags figure-free answers as
``unquantified``.
"""

import json
import logging
import math
from typing import Any

import httpx
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from gnw_evals.evaluators.utils import extract_agent_answer
from gnw_evals.utils.eval_types import ExpectedData
from gnw_evals.utils.models import HAIKU

logger = logging.getLogger(__name__)

# Stage 1: same-source numbers should essentially match; 0.1% absorbs float
# noise without letting a wrong canopy threshold (typically >1% shift) pass.
_FIDELITY_RELATIVE_TOLERANCE = 0.001
_FIDELITY_ABSOLUTE_TOLERANCE_HA = 1.0

# NOTE: deliberately no actual_canopy_cover/actual_forest_filter keys here.
# The no-op path must not clobber the parameter evaluator's extraction when
# both run on a non-intent case; _selected_parameters() adds them for intent
# cases (ground_truth merges after "parameters" in the registry, so its
# version wins there).
_EMPTY_RESULT: dict[str, Any] = {
    "data_fidelity_score": None,
    "data_fidelity_missing": None,
    "number_usage_score": None,
    "number_usage_reasoning": None,
    "number_usage_failure_comment": None,
    "unquantified": None,
    "ground_truth_json": None,
}


_DEFAULT_CANOPY_COVER = "30"


def _selected_parameters(agent_state: dict[str, Any]) -> dict[str, Any]:
    """Report the canopy/filter the agent actually selected, for spot-checks.

    The applied forest layer lives on ``dataset.context_layer`` (the top-level
    ``forest_filter`` state field is usually unset). The canopy threshold is
    only surfaced in ``dataset.parameters`` when the agent overrides the 30%
    default, so an absent value is reported as the default rather than blank.
    """
    dataset = agent_state.get("dataset") or {}
    context_layer = dataset.get("context_layer") or agent_state.get("forest_filter")

    canopy: str | None = None
    for param in dataset.get("parameters") or []:
        if isinstance(param, dict) and param.get("name") == "canopy_cover":
            values = param.get("values") or []
            if values:
                canopy = str(values[0])
            break
    if canopy is None:
        canopy = f"{_DEFAULT_CANOPY_COVER} (default)"

    return {
        "actual_canopy_cover": canopy,
        "actual_forest_filter": context_layer or None,
    }


_INTENT_RUBRICS = {
    "quantification": (
        "The answer must state the figure the user asked for, matching ground "
        "truth within tolerance. A quantification answer that provides no "
        "figure at all fails (score 0, unquantified true)."
    ),
    "comparison": (
        "The comparative claim (which entity or period is larger, and the "
        "direction of the difference) must be correct per ground truth. Any "
        "volunteered figures or differences must match within tolerance. A "
        "correct claim citing no figures passes with unquantified true."
    ),
    "trend": (
        "The direction of the trend (rising, falling, flat, including "
        "reversals such as a spike year) over the requested window must be "
        "correct per ground truth. Any volunteered magnitudes, years (e.g. "
        "peak year) or percentage changes must match within tolerance. A "
        "correct direction citing no figures passes with unquantified true."
    ),
}

_JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "user",
            """You are a strict numerical fact-checker for Global Nature Watch, \
a geospatial environmental data platform. You are given the authoritative \
ground-truth data for a user's question and the agent's final answer. Decide \
whether the agent used the numbers correctly.

USER QUERY: {query}
INTENT: {intent} (subtype: {eval_subtype})

GROUND TRUTH (authoritative, from the platform's analytics API; area_ha is \
tree cover loss area in hectares, carbon_emissions_MgCO2e is the associated \
GHG emissions in tonnes CO2e):
{ground_truth_table}

DERIVED FACTS (computed deterministically from the table above; trust these \
over your own arithmetic):
{derived_facts}

AGENT ANSWER:
{agent_answer}

RUBRIC FOR THIS INTENT: {rubric}
{judge_instruction_line}
TOLERANCE AND UNITS: a figure passes if it is within 5% relative of ground \
truth in any reasonable unit. 1 Mha = 1,000,000 ha; 1 kha = 1,000 ha; \
1 km2 = 100 ha; Mg CO2e = tonnes CO2e; 1 Gt CO2e = 1,000,000,000 Mg CO2e. \
Accept honest rounding ("about 2.8 million hectares" for 2,805,359 ha).
The platform reports GHG emissions alongside loss area by design; if the \
answer volunteers emissions figures, check them against the carbon column, \
do not treat them as errors. Never penalise caveats (e.g. methodology \
changes), hedging language, or extra context that does not contradict the \
ground truth.

Return:
- score: 1 if the answer satisfies the rubric, else 0
- reasoning: 2-3 sentences explaining your judgement
- failure_comment: empty string when score is 1; otherwise 1-2 sentences \
quoting the specific wrong figure or claim and the ground-truth value it \
contradicts
- unquantified: true when the answer makes no numeric claims at all""",
        ),
    ],
)


class _NumberUsageJudgement(BaseModel):
    score: int = Field(description="1 pass, 0 fail")
    reasoning: str
    failure_comment: str = ""
    unquantified: bool = False


def _iter_numeric_values(data: Any) -> list[float]:
    """Collect numeric leaf values from list-of-dicts or dict-of-lists data."""
    values: list[float] = []
    if isinstance(data, dict):
        for value in data.values():
            values.extend(_iter_numeric_values(value))
    elif isinstance(data, list):
        for item in data:
            values.extend(_iter_numeric_values(item))
    elif isinstance(data, bool):
        pass
    elif isinstance(data, int | float):
        values.append(float(data))
    return values


def _fetch_source_url_values(source_url: str) -> list[float]:
    """Fetch the raw analytics result the agent stored a link to."""
    try:
        response = httpx.get(source_url, timeout=30.0)
        response.raise_for_status()
        result = response.json().get("data", {}).get("result") or {}
        return _iter_numeric_values(
            {k: v for k, v in result.items() if k != "__dtypes__"},
        )
    except Exception:
        logger.warning("could not fetch statistics source_url %s", source_url)
        return []


def _collect_agent_values(agent_state: dict[str, Any]) -> list[float]:
    """Gather every number the agent pulled, from all state locations."""
    values: list[float] = []

    stats = agent_state.get("statistics")
    entries = stats if isinstance(stats, list) else [stats] if stats else []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        values.extend(_iter_numeric_values(entry.get("data")))
        source_url = (entry.get("source_url") or "").strip()
        if source_url:
            values.extend(_fetch_source_url_values(source_url))

    for chart in agent_state.get("charts_data") or []:
        if isinstance(chart, dict):
            values.extend(_iter_numeric_values(chart.get("data")))

    return values


def _value_matches(expected: float, agent_values: list[float]) -> bool:
    if expected == 0:
        return any(abs(v) <= _FIDELITY_ABSOLUTE_TOLERANCE_HA for v in agent_values)
    return any(
        math.isclose(v, expected, rel_tol=_FIDELITY_RELATIVE_TOLERANCE)
        for v in agent_values
    )


def _row_label(row: dict[str, Any]) -> str:
    label = str(row.get("aoi_id", "?"))
    if "tree_cover_loss_year" in row:
        label += f" {row['tree_cover_loss_year']}"
    if "tree_cover_loss_driver" in row:
        label += f" {row['tree_cover_loss_driver']}"
    return label


def _evaluate_data_fidelity(
    agent_state: dict[str, Any],
    ground_truth: dict[str, Any],
) -> dict[str, Any]:
    agent_values = _collect_agent_values(agent_state)
    if not agent_values:
        return {
            "data_fidelity_score": 0.0,
            "data_fidelity_missing": "no pulled data found in agent state",
        }

    missing = [
        f"{_row_label(row)}: expected {label} {value:,.2f}, no match"
        for row in ground_truth["rows"]
        for label, value in _required_row_metrics(row)
        if not _value_matches(value, agent_values)
    ]
    return {
        "data_fidelity_score": 0.0 if missing else 1.0,
        "data_fidelity_missing": "; ".join(missing) or None,
    }


def _required_row_metrics(row: dict[str, Any]) -> list[tuple[str, float]]:
    """Return the values a row must match: fire split when present, else total.

    Fires-dataset answers plot the two split columns rather than area_ha (per
    the catalog's code instructions), so requiring area_ha there would fail
    compliant answers.
    """
    fires = row.get("tree_cover_loss_from_fires_area_ha")
    if isinstance(fires, int | float):
        metrics = [("fires area_ha", float(fires))]
        non_fires = row.get("tree_cover_loss_non_fires_area_ha")
        if isinstance(non_fires, int | float):
            metrics.append(("non-fires area_ha", float(non_fires)))
        return metrics
    area = row.get("area_ha")
    return [("area_ha", float(area))] if isinstance(area, int | float) else []


def _format_ground_truth_table(rows: list[dict[str, Any]]) -> str:
    lines = []
    for row in rows:
        parts = [f"aoi={row.get('aoi_id', '?')}"]
        if "tree_cover_loss_year" in row:
            parts.append(f"year={row['tree_cover_loss_year']}")
        if "tree_cover_loss_driver" in row:
            parts.append(f"driver={row['tree_cover_loss_driver']}")
        for key, label in (
            ("area_ha", "area_ha"),
            ("tree_cover_loss_from_fires_area_ha", "fires_area_ha"),
            ("tree_cover_loss_non_fires_area_ha", "non_fires_area_ha"),
            ("carbon_emissions_MgCO2e", "carbon_emissions_MgCO2e"),
        ):
            value = row.get(key)
            if isinstance(value, int | float) and not math.isnan(value):
                parts.append(f"{label}={value:,.2f}")
        lines.append("  ".join(parts))
    return "\n".join(lines)


def _derive_facts(rows: list[dict[str, Any]]) -> str:
    """Pre-compute the aggregates the judge would otherwise have to derive."""
    facts: list[str] = []
    by_aoi: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_aoi.setdefault(str(row.get("aoi_id", "?")), []).append(row)

    totals: dict[str, float] = {}
    for aoi_id, aoi_rows in by_aoi.items():
        numeric = [r for r in aoi_rows if isinstance(r.get("area_ha"), int | float)]
        if not numeric:
            continue
        total = sum(float(r["area_ha"]) for r in numeric)
        totals[aoi_id] = total
        facts.append(f"{aoi_id}: total area_ha over all rows = {total:,.2f}")

        yearly = sorted(
            (r for r in numeric if "tree_cover_loss_year" in r),
            key=lambda r: r["tree_cover_loss_year"],
        )
        if len(yearly) > 1:
            first, last = yearly[0], yearly[-1]
            peak = max(yearly, key=lambda r: float(r["area_ha"]))
            change = float(last["area_ha"]) - float(first["area_ha"])
            pct = (
                (change / float(first["area_ha"])) * 100
                if float(first["area_ha"])
                else float("nan")
            )
            facts.append(
                f"{aoi_id}: first year {first['tree_cover_loss_year']} = "
                f"{float(first['area_ha']):,.2f} ha; last year "
                f"{last['tree_cover_loss_year']} = "
                f"{float(last['area_ha']):,.2f} ha; change = {change:,.2f} ha "
                f"({pct:+.1f}%); peak year = {peak['tree_cover_loss_year']} "
                f"({float(peak['area_ha']):,.2f} ha)",
            )

        drivers = [r for r in numeric if "tree_cover_loss_driver" in r]
        if drivers:
            dominant = max(drivers, key=lambda r: float(r["area_ha"]))
            share = float(dominant["area_ha"]) / total * 100 if total else 0
            known = [r for r in drivers if r["tree_cover_loss_driver"] != "Unknown"]
            known_total = sum(float(r["area_ha"]) for r in known)
            share_known = (
                float(dominant["area_ha"]) / known_total * 100 if known_total else 0
            )
            facts.append(
                f"{aoi_id}: dominant driver = "
                f"{dominant['tree_cover_loss_driver']} "
                f"({float(dominant['area_ha']):,.2f} ha, {share:.1f}% of "
                f"total, {share_known:.1f}% excluding the Unknown class)",
            )
            by_driver = {
                r["tree_cover_loss_driver"]: float(r["area_ha"]) for r in drivers
            }
            groupings = {
                "deforestation proxy (permanent agriculture + hard commodities "
                "+ settlements and infrastructure)": [
                    "Permanent agriculture",
                    "Hard commodities",
                    "Settlements and infrastructure",
                ],
                "temporary disturbance (shifting cultivation + logging + "
                "wildfire + other natural disturbances)": [
                    "Shifting cultivation",
                    "Logging",
                    "Wildfire",
                    "Other natural disturbances",
                ],
                "all agriculture (permanent agriculture + shifting cultivation)": [
                    "Permanent agriculture",
                    "Shifting cultivation",
                ],
            }
            for label, classes in groupings.items():
                subtotal = sum(by_driver.get(c, 0.0) for c in classes)
                facts.append(f"{aoi_id}: {label} = {subtotal:,.2f} ha")

        fire_rows = [
            r
            for r in numeric
            if isinstance(
                r.get("tree_cover_loss_from_fires_area_ha"),
                int | float,
            )
        ]
        if fire_rows:
            fires_total = sum(
                float(r["tree_cover_loss_from_fires_area_ha"]) for r in fire_rows
            )
            share = fires_total / total * 100 if total else 0
            facts.append(
                f"{aoi_id}: fire-driven loss total = {fires_total:,.2f} ha "
                f"({share:.1f}% of total loss); non-fire loss total = "
                f"{total - fires_total:,.2f} ha",
            )

    if len(totals) == 2:
        (aoi_a, total_a), (aoi_b, total_b) = sorted(
            totals.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )
        facts.append(
            f"comparison: {aoi_a} > {aoi_b} by {total_a - total_b:,.2f} ha "
            f"(totals over the requested range)",
        )
    return "\n".join(facts) or "none"


def _evaluate_number_usage(
    agent_state: dict[str, Any],
    ground_truth: dict[str, Any],
    intent: str,
    eval_subtype: str,
    judge_instruction: str,
    query: str,
) -> dict[str, Any]:
    agent_answer = extract_agent_answer(agent_state)
    if not agent_answer:
        return {
            "number_usage_score": 0.0,
            "number_usage_reasoning": "agent produced no final answer",
            "number_usage_failure_comment": "The agent produced no final "
            "answer to judge against the ground truth.",
            "unquantified": True,
        }

    rubric = _INTENT_RUBRICS.get(intent)
    if rubric is None:
        raise ValueError(f"unknown ground-truth intent {intent!r}")

    judge_instruction_line = (
        f"CASE-SPECIFIC INSTRUCTION: {judge_instruction}\n" if judge_instruction else ""
    )
    messages = _JUDGE_PROMPT.format_messages(
        query=query,
        intent=intent,
        eval_subtype=eval_subtype or "unspecified",
        ground_truth_table=_format_ground_truth_table(ground_truth["rows"]),
        derived_facts=_derive_facts(ground_truth["rows"]),
        agent_answer=agent_answer,
        rubric=rubric,
        judge_instruction_line=judge_instruction_line,
    )
    judgement = HAIKU.with_structured_output(_NumberUsageJudgement).invoke(
        messages,
    )
    return {
        "number_usage_score": float(judgement.score),
        "number_usage_reasoning": judgement.reasoning,
        "number_usage_failure_comment": judgement.failure_comment or None,
        "unquantified": judgement.unquantified,
    }


def evaluate_ground_truth(
    agent_state: dict[str, Any],
    expected_data: ExpectedData,
    query: str = "",
) -> dict[str, Any]:
    """Run both ground-truth stages for a case; no-op without intent."""
    intent = expected_data.intent
    ground_truth = expected_data.ground_truth
    if not intent or not ground_truth:
        return dict(_EMPTY_RESULT)

    result = dict(_EMPTY_RESULT)
    result["ground_truth_json"] = json.dumps(
        ground_truth["rows"],
        ensure_ascii=False,
        default=str,
    )
    result.update(_selected_parameters(agent_state))
    result.update(_evaluate_data_fidelity(agent_state, ground_truth))
    result.update(
        _evaluate_number_usage(
            agent_state,
            ground_truth,
            intent,
            expected_data.eval_subtype,
            expected_data.judge_instruction,
            query,
        ),
    )
    return result
