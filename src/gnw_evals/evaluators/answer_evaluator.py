from typing import Any

from gnw_evals.evaluators.llm_judges import llm_judge


def evaluate_final_answer(
    agent_state: dict[str, Any],
    expected_answer: str,
    expected_clarification: bool = False,
) -> dict[str, Any]:
    """Check if final answer contains key information from expected answer using LLM-as-a-judge.

    Args:
        agent_state: Final agent state after execution
        expected_answer: Expected answer text
        expected_clarification: Whether clarification is expected (Task 2, kept for consistency)
    Returns:
        Dict with answer_score (0 or 1), actual_answer

    Note:
        Per Task 2 requirements, answer_score is evaluated independently of expected_clarification.
        If expected_answer is provided, we evaluate it regardless of clarification expectations.

    """
    if not expected_answer:
        return {
            "answer_score": None,
            "actual_answer": None,
            "error": "Missing expected answer",
        }

    charts_data = agent_state.get("charts_data", [])

    if not charts_data or not expected_answer:
        messages = agent_state.get("messages", [])

        if messages:
            content = messages[-1].content
            # For Gemini, content is a list, with thinking and query as separate messages
            if isinstance(content, list):
                final_response = content[-1]
            else:
                final_response = content
        else:
            final_response = "Missing charts data or expected answer"
        return {
            "answer_score": 0,
            "actual_answer": None,
            "error": final_response,
        }

    # Get GNW Insight from charts data
    insight = charts_data[0].get("insight", "") if charts_data else ""

    if not insight:
        return {
            "answer_score": 0,
            "actual_answer": insight,
            "error": "No insight generated",
        }

    score = llm_judge(expected_answer, insight)

    return {
        "answer_score": score,
        "actual_answer": insight,
        "error": "",
    }
