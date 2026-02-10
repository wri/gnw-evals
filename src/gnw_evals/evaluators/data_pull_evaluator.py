"""Data pull evaluator."""

from typing import Any

from gnw_evals.evaluators.llm_judges import llm_judge_clarification
from gnw_evals.evaluators.utils import normalize_date, normalize_value


def evaluate_data_pull(
    agent_state: dict[str, Any],
    min_rows: int = 1,
    expected_start_date: str | None = None,
    expected_end_date: str | None = None,
    expected_clarification: bool = False,
    query: str = "",
) -> dict[str, Any]:
    """Check if data was successfully pulled, or if the agent asked for clarification.

    Args:
        agent_state: Final agent state after execution
        min_rows: Minimum number of rows expected
        expected_start_date: Expected start date
        expected_end_date: Expected end date
        expected_clarification: Whether clarification request is expected
        query: Original user query for clarification detection

    Returns:
        Dict with data_pull_exists_score (0/1), date_match_score (0/1/None),
        clarification_requested_score (0/1/None), row_count, min_rows,
        data_pull_success, date_success

    """
    raw_data = agent_state.get("raw_data")

    # Check if agent asked for clarification instead of pulling data
    if not raw_data and query:
        clarification = llm_judge_clarification(agent_state, query)
        if clarification["is_clarification"]:
            # Score clarification based on whether it was expected
            clarification_score = 1.0 if expected_clarification else 0.0
            return {
                "clarification_requested_score": clarification_score,
                "data_pull_exists_score": None,  # Not applicable when clarification given
                "date_match_score": None,  # Not applicable when clarification given
                "row_count": 0,
                "min_rows": min_rows,
                "data_pull_success": False,
                "date_success": None,
                "actual_start_date": f"CLARIFICATION_REQUEST: {clarification['explanation']}",
                "actual_end_date": "CLARIFICATION_REQUEST",
                "error": "",
            }

    if not raw_data:
        return {
            "data_pull_exists_score": 0.0,
            "date_match_score": None,
            "clarification_requested_score": None,
            "row_count": 0,
            "min_rows": min_rows,
            "data_pull_success": False,
            "date_success": None,
            "actual_start_date": agent_state.get("start_date", ""),
            "actual_end_date": agent_state.get("end_date", ""),
            "error": "Error pulling data",
        }

    row_count = len(raw_data)
    data_pull_success = row_count >= min_rows

    # Get actual dates from agent state
    actual_start_date = agent_state.get("start_date", "")
    actual_end_date = agent_state.get("end_date", "")

    # Binary scoring: Each component is 0 or 1 (or None if not evaluated)
    data_pull_exists_score = 1.0 if data_pull_success else 0.0

    if expected_start_date and expected_end_date:
        # Normalize date values to YYYY-MM-DD format for comparison
        expected_start_str = normalize_date(expected_start_date)
        expected_end_str = normalize_date(expected_end_date)
        actual_start_str = normalize_date(actual_start_date)
        actual_end_str = normalize_date(actual_end_date)

        # If any date failed to parse (empty string), treat as missing expected
        if not expected_start_str or not expected_end_str:
            date_success = None
            date_match_score = None
        else:
            date_success = (
                expected_start_str == actual_start_str
                and expected_end_str == actual_end_str
            )
            date_match_score = 1.0 if date_success else 0.0
    else:
        # Missing expected dates - return None (not evaluated)
        date_success = None
        date_match_score = None

    return {
        "data_pull_exists_score": data_pull_exists_score,
        "date_match_score": date_match_score,
        "clarification_requested_score": None,  # No clarification when data pulled
        "row_count": row_count,
        "min_rows": min_rows,
        "data_pull_success": data_pull_success,
        "date_success": date_success,
        "actual_start_date": actual_start_date,
        "actual_end_date": actual_end_date,
        "error": "",
    }
