"""Registry of evaluation sheets and their Google Sheet GIDs."""

import os

import dotenv

dotenv.load_dotenv()

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
if not SPREADSHEET_ID:
    raise ValueError(
        "SPREADSHEET_ID environment variable is required. "
        "Please set it in your .env file."
    )

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
}

# Default gold sheet URL (for backward compatibility checking)
DEFAULT_GOLD_URL = (
    f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"
)


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

    gid = EVAL_SETS[eval_set]
    return (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/"
        f"export?format=csv&gid={gid}"
    )
