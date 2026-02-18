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
    if not expected_aoi_ids:
        return {
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

    aoi_selection = agent_state.get("aoi_selection", [])
    if aoi_selection:
        aois = aoi_selection.get("aois", [])
    else:
        aois = []

    subregion = agent_state.get("subregion")

    # If subregions were not selected, use the subregion type from the main aoi
    if not subregion:
        subregion = agent_state.get("subtype")

    if not aois:
        return {
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

    # Get actual AOI ID based on subtype
    actual_aoi_ids = [aoi.get("src_id", "") for aoi in aois]
    actual_aoi_names = [aoi.get("name", "") for aoi in aois]
    actual_aoi_subtypes = [aoi.get("subtype", "") for aoi in aois]
    actual_aoi_sources = [aoi.get("source", "") for aoi in aois]

    if actual_aoi_sources[0] == "gadm":
        # Normalize GADM ids
        normalized_actual = [
            normalize_gadm_id(actual_aoi_id) for actual_aoi_id in actual_aoi_ids
        ]
        normalized_expected = [
            normalize_gadm_id(expected_aoi_id) for expected_aoi_id in expected_aoi_ids
        ]
    else:
        normalized_actual = [actual_aoi_id.lower() for actual_aoi_id in actual_aoi_ids]
        normalized_expected = [
            expected_aoi_id.lower() for expected_aoi_id in expected_aoi_ids
        ]

    match_aoi_id = set(normalized_actual) == set(normalized_expected)

    # Normalize subregion values for comparison
    expected_subregion_str = normalize_value(expected_subregion)
    actual_subregion_str = normalize_value(subregion)

    # Binary scoring: Each component is 0 or 1 (or None if not evaluated)
    aoi_id_match_score = 1.0 if match_aoi_id else 0.0

    # If expected subregion is empty, return None (not evaluated)
    if not expected_subregion_str:
        match_subregion = None
        subregion_match_score = None
    else:
        match_subregion = expected_subregion_str == actual_subregion_str
        subregion_match_score = 1.0 if match_subregion else 0.0

    return {
        "aoi_id_match_score": aoi_id_match_score,
        "subregion_match_score": subregion_match_score,
        "actual_id": str(actual_aoi_ids),
        "actual_name": str(actual_aoi_names),
        "actual_subtype": str(actual_aoi_subtypes),
        "actual_source": str(actual_aoi_sources),
        "actual_subregion": actual_subregion_str,
        "match_aoi_id": match_aoi_id,
        "match_subregion": match_subregion,
    }
