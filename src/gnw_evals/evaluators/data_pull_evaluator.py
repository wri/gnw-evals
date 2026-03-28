"""Data pull evaluator."""

from typing import Any

from gnw_evals.evaluators.utils import normalize_end_date, normalize_start_date


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
    expected_start_str = normalize_start_date(expected_start_date)
    expected_end_str = normalize_end_date(expected_end_date)

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
    actual_start_str = normalize_start_date(actual_start_date)
    actual_end_str = normalize_end_date(actual_end_date)

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
    expected_clarification: bool | None = None,
    min_rows: int = 1,
    query: str = "",
) -> dict[str, Any]:
    """Check if data was successfully pulled.

    Clarification detection is handled separately by evaluate_clarification().
    Date evaluation is handled separately by evaluate_date_selection().

    Args:
        agent_state: Final agent state after execution
        expected_clarification: Expected clarification behavior (True/False/None)
        min_rows: Minimum number of rows expected
        query: Original user query (kept for compatibility but not used)

    Returns:
        Dict with:
        - data_pull_exists_score (0/1/None): 1.0 if data pulled with sufficient rows,
          0.0 if insufficient rows or no data, None if not applicable
        - row_count (int): Number of rows in pulled data
        - data_pull_success (bool): Whether data pull met minimum row requirement
        - error (str): Error message if applicable

    """
    # Data is stored in raw_data as {src_id: {dataset_id: {col: [values]}}}
    raw_data_state = agent_state.get("raw_data", {})
    if raw_data_state:
        # Count rows from the first column array found
        row_count = 0
        for src_data in raw_data_state.values():
            if isinstance(src_data, dict):
                for dataset_data in src_data.values():
                    if isinstance(dataset_data, dict) and dataset_data:
                        first_col = next(iter(dataset_data.values()))
                        if isinstance(first_col, list):
                            row_count += len(first_col)
        error = ""
    else:
        row_count = 0
        error = "no data retrieved"

    if row_count < min_rows:
        data_pull_success = False
        error = "insufficient rows of data retrieved"
    else:
        data_pull_success = True

    # If we expect clarification, data pull evaluation is not applicable
    if expected_clarification is True:
        data_pull_exists_score = None
    else:
        data_pull_exists_score = 1.0 if data_pull_success else 0.0

    return {
        "data_pull_exists_score": data_pull_exists_score,
        "row_count": row_count,
        "error": error,
    }
