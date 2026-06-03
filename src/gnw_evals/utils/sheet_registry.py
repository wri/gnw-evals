"""Registry of evaluation sheets and their Google Sheet GIDs."""

import os

import dotenv

dotenv.load_dotenv()

# Eval set name → GID mapping
EVAL_SETS = {
    "gold": "0",
    "location_id": "1835901063",
    "dataset_id": "563440160",
    "dataset_interpretation": "2002527957",
    "analysis_results": "333186364",
    "analysis_interpretation": "785648141",
    "guardrail": "927934976",
    "date_selection": "1962457177",
    "challenge": "532812347",
}

# Primary metric field per eval set.
# Used in the RESULTS SUMMARY breakdown to show the most meaningful score for each eval set.
# If an eval set is not listed here, agent_answer_score is used as the default.
EVAL_SET_PRIMARY_METRIC: dict[str, str] = {
    "gold": "agent_answer_score",
    "location_id": "aoi_id_match_score",
    "dataset_id": "dataset_id_match_score",
    "dataset_interpretation": "agent_answer_score",
    "analysis_results": "agent_answer_score",
    "analysis_interpretation": "agent_answer_score",
    "guardrail": "clarification_requested_score",
    "date_selection": "date_match_score",
}


def _get_spreadsheet_id() -> str:
    """Retrieve and validate the SPREADSHEET_ID environment variable.

    Returns:
        The spreadsheet ID string.

    Raises:
        ValueError: If SPREADSHEET_ID is not set.

    """
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    if not spreadsheet_id:
        raise ValueError(
            "SPREADSHEET_ID environment variable is required. "
            "Please set it in your .env file.",
        )
    return spreadsheet_id


def get_sheet_url(eval_set: str) -> str:
    """Construct Google Sheets CSV export URL for given eval set.

    Args:
        eval_set: Name of the eval set (e.g., 'gold', 'location_id', etc.)

    Returns:
        Full CSV export URL for the specified sheet

    Raises:
        ValueError: If eval_set is not recognized

    """
    if eval_set not in EVAL_SETS:
        available = ", ".join(EVAL_SETS.keys())
        raise ValueError(f"Unknown eval set: '{eval_set}'. Available: {available}")

    spreadsheet_id = _get_spreadsheet_id()
    gid = EVAL_SETS[eval_set]
    return (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/"
        f"export?format=csv&gid={gid}"
    )
