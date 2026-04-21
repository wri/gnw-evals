"""Dataset selection evaluator."""

import json
from typing import Any

from gnw_evals.evaluators.utils import normalize_value


def _normalize_dataset_parameters(value: Any) -> str:
    """Normalize dataset parameters for stable JSON comparison."""
    if value is None or value == "None" or str(value).strip() == "":
        return ""

    parsed_value = value
    if isinstance(value, str):
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            return normalize_value(value)

    return json.dumps(parsed_value, sort_keys=True, separators=(",", ":"))


def evaluate_dataset_selection(
    agent_state: dict[str, Any],
    expected_dataset_id: Any,
    expected_dataset_parameters: Any,
    expected_context_layer: Any,
    query: str = "",
) -> dict[str, Any]:
    """Check if the correct dataset was selected.

    Clarification detection is handled separately by evaluate_clarification().
    This function only evaluates dataset selection.

    Args:
        agent_state: Final agent state after execution
        expected_dataset_id: Expected dataset id as string
        expected_dataset_parameters: Expected dataset parameters as JSON string
        expected_context_layer: Expected context layer as string
        query: Original user query (kept for compatibility but not used)

    Returns:
        Dict with dataset_id_match_score (0/1/None), context_layer_match_score
        (0/1/None), dataset_parameter_match_score (0/1/None),
        actual_dataset_id, actual_dataset_name, actual_dataset_parameters,
        actual_context_layer

    """
    if not expected_dataset_id:
        return {
            "dataset_id_match_score": None,
            "dataset_parameter_match_score": None,
            "context_layer_match_score": None,
            "actual_dataset_id": None,
            "actual_dataset_name": None,
            "actual_dataset_parameters": None,
            "actual_context_layer": None,
            "error": "Missing dataset data",
        }

    dataset = agent_state.get("dataset")

    if not dataset:
        return {
            "dataset_id_match_score": 0.0,
            "dataset_parameter_match_score": None,
            "context_layer_match_score": None,
            "actual_dataset_id": None,
            "actual_dataset_name": None,
            "actual_dataset_parameters": None,
            "actual_context_layer": None,
            "error": "Missing dataset data",
        }

    actual_dataset_id = str(dataset.get("dataset_id", ""))
    actual_dataset_name = dataset.get("dataset_name", "")
    actual_dataset_parameters = json.dumps(
        dataset.get("parameters", []),
        separators=(",", ":"),
    )
    actual_context_layer = dataset.get("context_layer", "")

    # Normalize values for comparison
    expected_id_str = normalize_value(expected_dataset_id)
    actual_id_str = normalize_value(actual_dataset_id)
    dataset_match = expected_id_str == actual_id_str

    expected_parameters_str = _normalize_dataset_parameters(expected_dataset_parameters)
    actual_parameters_str = _normalize_dataset_parameters(actual_dataset_parameters)

    expected_context_str = normalize_value(expected_context_layer)
    actual_context_str = normalize_value(actual_context_layer)

    # Binary scoring: Each component is 0 or 1 (or None if not evaluated)
    dataset_id_match_score = 1.0 if dataset_match else 0.0

    if not expected_parameters_str:
        dataset_parameter_match_score = None
    else:
        dataset_parameter_match_score = (
            1.0 if expected_parameters_str == actual_parameters_str else 0.0
        )

    # Context layer matching: if expected is empty, return None (not evaluated)
    if not expected_context_str:
        context_layer_match_score = None
    elif expected_context_str == "no_selection":
        context_layer_match_score = 1.0 if not actual_context_str else 0.0
    else:
        context_layer_match = expected_context_str == actual_context_str
        context_layer_match_score = 1.0 if context_layer_match else 0.0

    return {
        "dataset_id_match_score": dataset_id_match_score,
        "dataset_parameter_match_score": dataset_parameter_match_score,
        "context_layer_match_score": context_layer_match_score,
        "actual_dataset_id": actual_dataset_id,
        "actual_dataset_name": actual_dataset_name,
        "actual_dataset_parameters": actual_dataset_parameters,
        "actual_context_layer": actual_context_layer,
        "error": "",
    }
