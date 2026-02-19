"""AOI (Area of Interest) selection evaluator."""

from typing import Any

from gnw_evals.evaluators.utils import normalize_gadm_id, normalize_value


def evaluate_aoi_selection(
    agent_state: dict[str, Any],
    expected_aoi_ids: list[str],
    expected_subregion: str | None,
    query: str = "",
) -> dict[str, Any]:
    """Check if the correct AOI was selected.

    Clarification detection is handled separately by evaluate_clarification().
    This function only evaluates AOI selection.

    Args:
        agent_state: Final agent state after execution
        expected_aoi_ids: Expected AOI IDs (e.g., ["BRA", "USA.5_1"])
        expected_subregion: Expected subregion (e.g., "state-province", "country")
        query: Original user query (kept for compatibility but not used)

    Returns:
        Dict with aoi_id_match_score (0/1/None), subregion_match_score (0/1/None),
        actual_id, actual_name, actual_subtype, actual_source, actual_subregion

    """
    # Initialize result dict with all fields
    result = {
        "aoi_id_match_score": None,
        "subregion_match_score": None,
        "actual_id": None,
        "actual_name": None,
        "actual_subtype": None,
        "actual_source": None,
        "actual_subregion": None,
        "match_aoi_id": False,
        "match_subregion": None,
    }

    # STEP 1: Extract actual values from agent_state (ALWAYS do this if data exists)
    actual_data = _extract_actual_aoi_data(agent_state)
    if actual_data:
        result.update(
            {
                "actual_id": actual_data["ids"],
                "actual_name": actual_data["names"],
                "actual_subtype": actual_data["subtypes"],
                "actual_source": actual_data["sources"],
                "actual_subregion": actual_data["subregion"],
            },
        )

    # STEP 2: Early exit if we can't evaluate (no expected values or no actual data)
    if not expected_aoi_ids:
        return result

    if not actual_data:
        return result

    # STEP 3: Normalize and compare AOI IDs
    normalized_actual, normalized_expected = _normalize_aoi_ids(
        actual_data["raw_ids"],
        expected_aoi_ids,
        actual_data["source"],
    )

    match_aoi_id = set(normalized_actual) == set(normalized_expected)
    result["match_aoi_id"] = match_aoi_id
    result["aoi_id_match_score"] = 1.0 if match_aoi_id else 0.0

    # STEP 4: Evaluate subregion (if expected)
    expected_subregion_str = normalize_value(expected_subregion)
    if expected_subregion_str:
        match_subregion = expected_subregion_str == actual_data["subregion"]
        result["match_subregion"] = match_subregion
        result["subregion_match_score"] = 1.0 if match_subregion else 0.0

    return result


def _extract_actual_aoi_data(agent_state: dict[str, Any]) -> dict[str, Any] | None:
    """Extract actual AOI data from agent state.

    Args:
        agent_state: Final agent state after execution

    Returns:
        Dict with extracted data, or None if no AOI data available

    """
    aoi_selection = agent_state.get("aoi_selection", [])
    aois = aoi_selection.get("aois", []) if aoi_selection else []

    if not aois:
        return None

    # Extract lists
    raw_ids = [aoi.get("src_id", "") for aoi in aois]
    names = [aoi.get("name", "") for aoi in aois]
    subtypes = [aoi.get("subtype", "") for aoi in aois]
    sources = [aoi.get("source", "") for aoi in aois]

    # Get subregion (from subregion field or fall back to subtype)
    subregion = agent_state.get("subregion")
    if not subregion:
        subregion = agent_state.get("subtype")

    return {
        "raw_ids": raw_ids,
        "ids": str(raw_ids),
        "names": str(names),
        "subtypes": str(subtypes),
        "sources": str(sources),
        "source": sources[0] if sources else "",
        "subregion": normalize_value(subregion),
    }


def _normalize_aoi_ids(
    actual_ids: list[str],
    expected_ids: list[str],
    source: str,
) -> tuple[list[str], list[str]]:
    """Normalize AOI IDs based on source type.

    Args:
        actual_ids: Actual AOI IDs from agent state
        expected_ids: Expected AOI IDs from test data
        source: AOI source (e.g., "gadm", "kba", "wdpa")

    Returns:
        Tuple of (normalized_actual, normalized_expected)

    """
    if source == "gadm":
        return (
            [normalize_gadm_id(id) for id in actual_ids],
            [normalize_gadm_id(id) for id in expected_ids],
        )
    else:
        return (
            [id.lower() for id in actual_ids],
            [id.lower() for id in expected_ids],
        )
