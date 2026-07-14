"""Parameter selection evaluator.

Covers five parameter types: canopy_cover, forest_filter, intersections,
crop_types (LLM-judged), and gas_types (LLM-judged).

Canopy cover, forest filter, and intersections are deterministic string
comparisons against agent_state. Crop types and gas types require an LLM
judge because the API always sends all values — evaluation must check what
the agent presented in the insight text.
"""

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from gnw_evals.evaluators.utils import normalize_value
from gnw_evals.utils.models import HAIKU

logger = logging.getLogger(__name__)


def _extract_from_state(agent_state: dict[str, Any], *keys: str) -> str:
    """Try multiple top-level keys in agent_state, returning the first non-empty value."""
    for key in keys:
        val = agent_state.get(key)
        if val is not None and str(val).strip() not in ("", "None"):
            return str(val).strip()
    # Also check inside the dataset dict
    dataset = agent_state.get("dataset") or {}
    for key in keys:
        val = dataset.get(key)
        if val is not None and str(val).strip() not in ("", "None"):
            return str(val).strip()
    return ""


def evaluate_parameters(
    agent_state: dict[str, Any],
    expected_canopy_cover: str = "",
    expected_forest_filter: str = "",
    expected_intersections: str = "",
    expected_crop_types: str = "",
    expected_gas_types: str = "",
    insight_text: str = "",
) -> dict[str, Any]:
    """Evaluate all parameter selections for a single test case.

    Args:
        agent_state: Final agent state after execution
        expected_canopy_cover: Expected canopy density threshold as string (e.g. "30", "50")
        expected_forest_filter: Expected forest filter ("primary_forest",
            "intact_forest_landscape", or "")
        expected_intersections: Expected intersection layer (e.g. "driver",
            "natural_lands", "grasslands", "land_cover")
        expected_crop_types: Expected crop type(s) as semicolon-separated string
        expected_gas_types: Expected gas type(s) as semicolon-separated string
        insight_text: The agent's insight text (charts_data[0]["insight"]) used for
            LLM-judged crop/gas evaluation

    Returns:
        Dict with individual match scores and actual values

    """
    result: dict[str, Any] = {
        "canopy_cover_match_score": None,
        "actual_canopy_cover": None,
        "forest_filter_match_score": None,
        "actual_forest_filter": None,
        "intersections_match_score": None,
        "actual_intersections": None,
        "crop_type_match_score": None,
        "gas_type_match_score": None,
    }

    result.update(_evaluate_canopy_cover(agent_state, expected_canopy_cover))
    result.update(_evaluate_forest_filter(agent_state, expected_forest_filter))
    result.update(_evaluate_intersections(agent_state, expected_intersections))

    if normalize_value(expected_crop_types):
        result["crop_type_match_score"] = _llm_judge_focus(
            insight_text,
            expected_crop_types,
            label="crop(s)",
        )

    if normalize_value(expected_gas_types):
        result["gas_type_match_score"] = _llm_judge_focus(
            insight_text,
            expected_gas_types,
            label="gas type(s)",
        )

    return result


# ---------------------------------------------------------------------------
# Deterministic sub-evaluators
# ---------------------------------------------------------------------------


def _evaluate_canopy_cover(
    agent_state: dict[str, Any],
    expected_canopy_cover: str,
) -> dict[str, Any]:
    """Evaluate canopy density threshold."""
    actual = _extract_from_state(
        agent_state,
        "canopy_density",
        "canopy_cover",
        "canopy_threshold",
    )
    result: dict[str, Any] = {
        "actual_canopy_cover": actual or None,
        "canopy_cover_match_score": None,
    }

    expected_str = normalize_value(expected_canopy_cover)
    if not expected_str:
        return result

    if not actual:
        result["canopy_cover_match_score"] = 0.0
        return result

    result["canopy_cover_match_score"] = 1.0 if actual == expected_str else 0.0
    return result


def _evaluate_forest_filter(
    agent_state: dict[str, Any],
    expected_forest_filter: str,
) -> dict[str, Any]:
    """Evaluate forest filter (primary_forest or intact_forest_landscape)."""
    actual = _extract_from_state(
        agent_state,
        "forest_filter",
        "primary_forest",
        "forest_type",
    )
    result: dict[str, Any] = {
        "actual_forest_filter": actual or None,
        "forest_filter_match_score": None,
    }

    expected_str = normalize_value(expected_forest_filter)
    if not expected_str:
        return result

    if not actual:
        result["forest_filter_match_score"] = 0.0
        return result

    result["forest_filter_match_score"] = (
        1.0 if actual.lower() == expected_str.lower() else 0.0
    )
    return result


def _evaluate_intersections(
    agent_state: dict[str, Any],
    expected_intersections: str,
) -> dict[str, Any]:
    """Evaluate intersection / context layer selection."""
    # Intersections are stored in the same place as context_layer
    dataset = agent_state.get("dataset") or {}
    actual = normalize_value(dataset.get("context_layer", ""))
    if not actual:
        actual = _extract_from_state(agent_state, "intersection", "intersections")

    result: dict[str, Any] = {
        "actual_intersections": actual or None,
        "intersections_match_score": None,
    }

    expected_str = normalize_value(expected_intersections)
    if not expected_str:
        return result

    if not actual:
        result["intersections_match_score"] = 0.0
        return result

    result["intersections_match_score"] = (
        1.0 if actual.lower() == expected_str.lower() else 0.0
    )
    return result


# ---------------------------------------------------------------------------
# LLM-as-judge sub-evaluator (crop types and gas types)
# ---------------------------------------------------------------------------


def _llm_judge_focus(
    insight_text: str,
    expected_values: str,
    label: str,
) -> float | None:
    """Use Claude Haiku to check whether the insight focuses on the expected values.

    Args:
        insight_text: The agent's insight text
        expected_values: Semicolon-separated expected values
        label: Human-readable label for the category (e.g. "crop(s)", "gas type(s)")

    Returns:
        1.0 if the insight focuses on the expected values, 0.0 otherwise,
        or None if no insight is available

    """
    if not insight_text or not normalize_value(expected_values):
        return None

    class FocusJudgement(BaseModel):
        score: int
        explanation: str

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                """You are evaluating whether an AI-generated insight focuses on the requested {label}.

EXPECTED {label_upper}: {expected_values}

AGENT INSIGHT: {insight}

Does this insight specifically focus on or report results for the requested {label}?
All expected {label} must be present and clearly addressed in the insight.

Return score 1 if the insight focuses on ALL of the expected {label}, 0 if any are missing or the wrong {label} is reported.""",
            ),
        ],
    )

    try:
        messages = prompt.format_messages(
            label=label,
            label_upper=label.upper(),
            expected_values=expected_values,
            insight=insight_text,
        )
        judgement = HAIKU.with_structured_output(FocusJudgement).invoke(messages)
        return float(judgement.score)
    except Exception:
        logger.exception("_llm_judge_focus failed for label=%r expected=%r", label, expected_values)
        return None
