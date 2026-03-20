"""Centralized clarification detection evaluator."""

from typing import Any

from gnw_evals.evaluators.llm_judges import llm_judge_clarification


def evaluate_clarification(
    agent_state: dict[str, Any],
    expected_clarification: bool | None,
    query: str,
) -> dict[str, Any]:
    """Detect if agent requested clarification and score it.

    This is the centralized clarification check - called once per evaluation
    before other evaluators run.

    Args:
        agent_state: Final agent state after execution
        expected_clarification: Expected clarification behavior
            - True: clarification is expected
            - False: clarification is not expected
            - None: no expectation (empty string from CSV)
        query: Original user query for clarification detection

    Returns:
        Dict with:
        - actual_clarification_requested (bool): Whether agent requested clarification
        - clarification_requested_score (float | None): Score based on expectation match
        - clarification_explanation (str): Explanation from LLM judge

    Scoring logic:
        expected=True,  actual=True  → 1.0 (correct)
        expected=True,  actual=False → 0.0 (wrong - expected but not given)
        expected=False, actual=True  → 0.0 (wrong - not expected but given)
        expected=False, actual=False → 1.0 (correct)
        expected=None,  actual=True  → 0.0 (unsolicited clarification)
        expected=None,  actual=False → None (not evaluated)

    """
    # If no query, can't detect clarification
    if not query:
        actual_clarification = False
        explanation = "No query provided"
    else:
        # Call LLM judge once to detect clarification
        clarification = llm_judge_clarification(agent_state, query)
        actual_clarification = clarification["is_clarification"]
        explanation = clarification["explanation"]

    # Calculate score based on expectation
    if expected_clarification is None:
        # No expectation case
        if actual_clarification:
            # Unsolicited clarification
            score = 0.0
        else:
            # No clarification and none expected - not evaluated
            score = None
    else:
        # Expectation exists (True or False)
        if actual_clarification == expected_clarification:
            # Matches expectation
            score = 1.0
        else:
            # Doesn't match expectation
            score = 0.0

    return {
        "actual_clarification_requested": actual_clarification,
        "clarification_requested_score": score,
        "clarification_explanation": explanation,
    }
