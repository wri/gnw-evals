"""Dataset selection evaluator."""

from typing import Any

from gnw_evals.evaluators.llm_judges import llm_judge_clarification
from gnw_evals.evaluators.utils import normalize_value


def evaluate_dataset_selection(
    agent_state: dict[str, Any],
    expected_dataset_id: Any,
    expected_context_layer: Any,
    expected_clarification: bool = False,
    query: str = "",
) -> dict[str, Any]:
    """Check if the correct dataset was selected, or if the agent asked for clarification.

    Args:
        agent_state: Final agent state after execution
        expected_dataset_id: Expected dataset id as string
        expected_context_layer: Expected context layer as string
        expected_clarification: Whether clarification request is expected
        query: Original user query for clarification detection

    Returns:
        Dict with dataset_id_match_score (0/1/None), context_layer_match_score (0/1/None),
        clarification_requested_score (0/1/None), actual_dataset_id, actual_dataset_name,
        actual_context_layer

    """
    if not expected_dataset_id:
        return {
            "dataset_id_match_score": None,
            "context_layer_match_score": None,
            "clarification_requested_score": None,
            "actual_dataset_id": None,
            "actual_dataset_name": None,
            "actual_context_layer": None,
            "error": "Missing dataset data",
        }
    dataset = agent_state.get("dataset")

    # Check if agent asked for clarification instead of selecting a dataset
    if not dataset and query:
        clarification = llm_judge_clarification(agent_state, query)
        if clarification["is_clarification"]:
            # Score clarification based on whether it was expected
            clarification_score = 1.0 if expected_clarification else 0.0
            return {
                "clarification_requested_score": clarification_score,
                "dataset_id_match_score": None,  # Not applicable when clarification given
                "context_layer_match_score": None,  # Not applicable when clarification given
                "actual_dataset_id": f"CLARIFICATION_REQUEST: {clarification['explanation']}",
                "actual_dataset_name": "Agent requested clarification",
                "actual_context_layer": "N/A",
                "error": "",
            }

    if not dataset:
        return {
            "dataset_id_match_score": 0.0,
            "context_layer_match_score": None,
            "clarification_requested_score": None,
            "actual_dataset_id": None,
            "actual_dataset_name": None,
            "actual_context_layer": None,
            "error": "Missing dataset data",
        }

    actual_dataset_id = str(dataset.get("dataset_id", ""))
    actual_dataset_name = dataset.get("dataset_name", "")
    actual_context_layer = dataset.get("context_layer", "")

    # Normalize values for comparison
    expected_id_str = normalize_value(expected_dataset_id)
    actual_id_str = normalize_value(actual_dataset_id)
    dataset_match = expected_id_str == actual_id_str

    expected_context_str = normalize_value(expected_context_layer)
    actual_context_str = normalize_value(actual_context_layer)

    # Binary scoring: Each component is 0 or 1 (or None if not evaluated)
    dataset_id_match_score = 1.0 if dataset_match else 0.0

    # Context layer matching: if expected is empty, return None (not evaluated)
    if not expected_context_str:
        context_layer_match_score = None
    else:
        context_layer_match = expected_context_str == actual_context_str
        context_layer_match_score = 1.0 if context_layer_match else 0.0

    return {
        "dataset_id_match_score": dataset_id_match_score,
        "context_layer_match_score": context_layer_match_score,
        "clarification_requested_score": None,  # No clarification when dataset selected
        "actual_dataset_id": actual_dataset_id,
        "actual_dataset_name": actual_dataset_name,
        "actual_context_layer": actual_context_layer,
        "error": "",
    }
