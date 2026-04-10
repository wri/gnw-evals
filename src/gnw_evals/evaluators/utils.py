"""Utility functions for evaluators."""

from datetime import datetime


def normalize_gadm_id(gadm_id: str) -> str:
    """Normalize GADM ID for comparison."""
    if not gadm_id:
        return ""
    return gadm_id.split("_")[0].replace("-", ".").lower()


def normalize_value(value) -> str:
    """Normalize values for comparison, handling None, empty strings, and 'None' strings."""
    if value is None or value == "None" or str(value).strip() == "":
        return ""
    return str(value).strip().lower()


def normalize_date(date_str: str | None) -> str:
    """Normalize date strings to YYYY-MM-DD format.

    For YYYY format, defaults to January 1st. For start/end date pairs,
    use normalize_start_date() and normalize_end_date() instead.

    Formats: M/D/YYYY, YYYY-MM-DD, YYYY. Returns empty string if invalid.

    """
    if date_str is None or date_str == "None" or str(date_str).strip() == "":
        return ""

    date_str = str(date_str).strip()

    formats = ["%m/%d/%Y", "%Y-%m-%d", "%Y"]

    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return ""


def normalize_start_date(date_str: str | None) -> str:
    """Normalize a start date to YYYY-MM-DD format.

    YYYY format converts to beginning of year (YYYY-01-01).
    Other formats normalized via normalize_date().

    """
    if not date_str or date_str == "None" or str(date_str).strip() == "":
        return ""

    date_str = str(date_str).strip()

    # YYYY format -> beginning of year
    if len(date_str) == 4 and date_str.isdigit():
        return f"{date_str}-01-01"

    return normalize_date(date_str)


def normalize_end_date(date_str: str | None) -> str:
    """Normalize an end date to YYYY-MM-DD format.

    YYYY format converts to end of year (YYYY-12-31).
    Other formats normalized via normalize_date().

    """
    if not date_str or date_str == "None" or str(date_str).strip() == "":
        return ""

    date_str = str(date_str).strip()

    # YYYY format -> end of year
    if len(date_str) == 4 and date_str.isdigit():
        return f"{date_str}-12-31"

    return normalize_date(date_str)
