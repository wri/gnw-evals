"""Data pull evaluator."""

from typing import Any

from gnw_evals.evaluators.llm_judges import llm_judge_clarification
from gnw_evals.evaluators.utils import normalize_date


def evaluate_date_selection(
    agent_state: dict[str, Any],
    expected_start_date: str | None = None,
    expected_end_date: str | None = None,
) -> dict[str, Any]:
    """Evaluate if correct dates were selected.

    Evaluates date selection based on what the agent stored in state,
    regardless of whether data pull succeeded or clarification was requested.

    Args:
        agent_state: Final agent state after execution
        expected_start_date: Expected start date in various formats (M/D/YYYY, YYYY-MM-DD, etc.)
        expected_end_date: Expected end date in various formats

    Returns:
        Dict with:
        - date_match_score (0/1/None): 1.0 if both dates match, 0.0 if mismatch or missing,
          None if no expected dates provided or expected dates are invalid
        - date_success (bool | None): Boolean version of date_match_score
        - actual_start_date (str | None): Actual start date from agent state
        - actual_end_date (str | None): Actual end date from agent state

    """
    actual_start_date = agent_state.get("start_date", "")
    actual_end_date = agent_state.get("end_date", "")

    # If no expected dates, skip evaluation
    if not expected_start_date or not expected_end_date:
        return {
            "date_match_score": None,
            "date_success": None,
            "actual_start_date": actual_start_date or None,
            "actual_end_date": actual_end_date or None,
        }

    # Normalize expected dates
    expected_start_str = normalize_date(expected_start_date)
    expected_end_str = normalize_date(expected_end_date)

    # If expected dates are invalid, skip evaluation
    if not expected_start_str or not expected_end_str:
        return {
            "date_match_score": None,
            "date_success": None,
            "actual_start_date": actual_start_date or None,
            "actual_end_date": actual_end_date or None,
        }

    # If actual dates are missing/None, score as 0
    if not actual_start_date or not actual_end_date:
        return {
            "date_match_score": 0.0,  # Missing actual = wrong
            "date_success": False,
            "actual_start_date": None,
            "actual_end_date": None,
        }

    # Normalize actual dates and compare
    actual_start_str = normalize_date(actual_start_date)
    actual_end_str = normalize_date(actual_end_date)

    # If actual dates failed to parse, score as 0
    if not actual_start_str or not actual_end_str:
        return {
            "date_match_score": 0.0,  # Invalid actual = wrong
            "date_success": False,
            "actual_start_date": actual_start_date,
            "actual_end_date": actual_end_date,
        }

    # Compare normalized dates
    date_success = (
        expected_start_str == actual_start_str and expected_end_str == actual_end_str
    )
    date_match_score = 1.0 if date_success else 0.0

    return {
        "date_match_score": date_match_score,
        "date_success": date_success,
        "actual_start_date": actual_start_date,
        "actual_end_date": actual_end_date,
    }


def evaluate_data_pull(
    agent_state: dict[str, Any],
    min_rows: int = 1,
    expected_clarification: bool = False,
    query: str = "",
) -> dict[str, Any]:
    """Check if data was successfully pulled, or if the agent asked for clarification.

    Date evaluation is handled separately by evaluate_date_selection().

    Args:
        agent_state: Final agent state after execution
        min_rows: Minimum number of rows expected
        expected_clarification: Whether clarification request is expected
        query: Original user query for clarification detection

    Returns:
        Dict with:
        - data_pull_exists_score (0/1/None): 1.0 if data pulled with sufficient rows,
          0.0 if insufficient rows, None if clarification given
        - clarification_requested_score (0/1/None): Score for clarification handling
        - row_count (int): Number of rows in pulled data
        - data_pull_success (bool): Whether data pull met minimum row requirement
        - error (str): Error message if applicable

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
                "row_count": 0,
                "data_pull_success": False,
                "error": "",
            }

    if not raw_data:
        return {
            "data_pull_exists_score": 0.0,
            "clarification_requested_score": None,
            "row_count": 0,
            "data_pull_success": False,
            "error": "Error pulling data",
        }

    row_count = len(raw_data)
    data_pull_success = row_count >= min_rows
    data_pull_exists_score = 1.0 if data_pull_success else 0.0

    return {
        "data_pull_exists_score": data_pull_exists_score,
        "clarification_requested_score": None,  # No clarification when data pulled
        "row_count": row_count,
        "data_pull_success": data_pull_success,
        "error": "",
    }
