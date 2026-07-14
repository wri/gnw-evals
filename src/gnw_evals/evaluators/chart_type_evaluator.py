"""Chart type evaluator."""

from typing import Any

from gnw_evals.evaluators.utils import normalize_value


def evaluate_chart_type(
    agent_state: dict[str, Any],
    expected_chart_type: str,
) -> dict[str, Any]:
    """Check if the correct chart type was produced.

    Supports multiple valid types as a semicolon-separated string
    (e.g. "pie;bar" means either pie or bar is acceptable).

    Args:
        agent_state: Final agent state after execution
        expected_chart_type: Expected chart type(s), semicolon-separated

    Returns:
        Dict with chart_type_match_score (0/1/None) and actual_chart_type

    """
    charts_data = agent_state.get("charts_data", [])
    actual_chart_type = charts_data[0].get("type", "") if charts_data else None

    result: dict[str, Any] = {
        "chart_type_match_score": None,
        "actual_chart_type": actual_chart_type or None,
    }

    expected_str = normalize_value(expected_chart_type)
    if not expected_str:
        return result

    if not actual_chart_type:
        result["chart_type_match_score"] = 0.0
        return result

    valid_types = {t.strip().lower() for t in expected_str.split(";") if t.strip()}
    match = actual_chart_type.strip().lower() in valid_types
    result["chart_type_match_score"] = 1.0 if match else 0.0

    return result
