"""Data pull evaluator."""

from typing import Any

from gnw_evals.evaluators.utils import normalize_end_date, normalize_start_date


def _latest_statistics(agent_state: dict[str, Any]) -> dict[str, Any]:
    """Return the most recent statistics entry from agent state."""
    stats = agent_state.get("statistics")
    if not stats:
        return {}
    if isinstance(stats, dict):
        return stats
    if isinstance(stats, list) and stats:
        last = stats[-1]
        return last if isinstance(last, dict) else {}
    return {}


def _count_rows(raw_data: Any) -> int:
    """Count rows in legacy inline statistics data."""
    if isinstance(raw_data, list):
        return len(raw_data)
    if isinstance(raw_data, dict):
        if not raw_data:
            return 0
        lengths = [len(v) for v in raw_data.values() if isinstance(v, list)]
        return max(lengths) if lengths else 0
    return 0


def _data_pull_outcome(
    stat_entry: dict[str, Any],
    *,
    min_rows: int,
) -> tuple[bool, int, str]:
    """Determine whether a data pull succeeded and how many rows are available."""
    source_url = (stat_entry.get("source_url") or "").strip()
    id = stat_entry.get("id") or ""
    print(f"source_url: {source_url}, id: {id}")
    if source_url and id:
        return True, 1, ""

    row_count = _count_rows(stat_entry.get("data"))
    if row_count < min_rows:
        return False, row_count, "insufficient rows of data retrieved"
    return True, row_count, ""


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
    stat_entry = _latest_statistics(agent_state)
    actual_start_date = agent_state.get("start_date") or stat_entry.get(
        "start_date",
        "",
    )
    actual_end_date = agent_state.get("end_date") or stat_entry.get("end_date", "")

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
    expected_answer: str = "",
    min_rows: int = 1,
    query: str = "",
) -> dict[str, Any]:
    """Check if data was successfully pulled.

    Clarification detection is handled separately by evaluate_clarification().
    Date evaluation is handled separately by evaluate_date_selection().

    Args:
        agent_state: Final agent state after execution
        expected_clarification: Expected clarification behavior (True/False/None)
        expected_answer: Expected answer text. Data pull is only evaluated when provided.
        min_rows: Minimum number of rows expected (legacy inline data only)
        query: Original user query (kept for compatibility but not used)

    Returns:
        Dict with:
        - data_pull_exists_score (0/1/None): 1.0 if data pull succeeded,
          0.0 if pull missing or failed, None if not applicable
        - row_count (int): 1 when source_url is present, else legacy row count
        - data_pull_success (bool): Whether data pull met success criteria
        - error (str): Error message if applicable

    """
    stat_entry = _latest_statistics(agent_state)
    if stat_entry:
        data_pull_success, row_count, error = _data_pull_outcome(
            stat_entry,
            min_rows=min_rows,
        )
    else:
        data_pull_success = False
        row_count = 0
        error = "no data retrieved"

    # If we expect clarification or no answer check, data pull evaluation is not applicable.
    if expected_clarification is True or not expected_answer:
        data_pull_exists_score = None
    else:
        data_pull_exists_score = 1.0 if data_pull_success else 0.0

    return {
        "data_pull_exists_score": data_pull_exists_score,
        "row_count": row_count,
        "data_pull_success": data_pull_success,
        "error": error,
    }
