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
    return str(value).strip()


def normalize_date(date_str: str | None) -> str:
    """Normalize date strings to YYYY-MM-DD format for comparison.

    Handles multiple input formats:
    - M/D/YYYY or MM/DD/YYYY (e.g., 1/1/2023, 12/31/2023)
    - YYYY-MM-DD (already normalized - pass through)
    - YYYY (year only - converts to YYYY-01-01)
    - None, empty string, or "None" -> returns ""

    Args:
        date_str: Date string in various formats

    Returns:
        Normalized date string in YYYY-MM-DD format, or empty string if invalid

    Examples:
        >>> normalize_date("1/1/2023")
        "2023-01-01"
        >>> normalize_date("2023-08-15")
        "2023-08-15"
        >>> normalize_date("2024")
        "2024-01-01"
        >>> normalize_date(None)
        ""

    """
    if date_str is None or date_str == "None" or str(date_str).strip() == "":
        return ""

    date_str = str(date_str).strip()

    # Try parsing different formats
    formats = [
        "%m/%d/%Y",  # M/D/YYYY or MM/DD/YYYY
        "%Y-%m-%d",  # YYYY-MM-DD (already normalized)
        "%Y",  # Year only
    ]

    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Could not parse - treat as missing/invalid
    return ""
