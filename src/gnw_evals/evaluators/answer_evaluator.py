from typing import Any

from gnw_evals.evaluators.llm_judges import llm_judge


def evaluate_final_answer(
    agent_state: dict[str, Any],
    expected_answer: str,
    expected_clarification: bool = False,
) -> dict[str, Any]:
    """Check if final answer contains key information from expected answer using LLM-as-a-judge.

    Task 3: Now returns TWO separate scores:
    - charts_answer_score: Compares expected_answer to charts_data[0]["insight"]
    - agent_answer_score: Compares expected_answer to messages[-1].content

    Args:
        agent_state: Final agent state after execution
        expected_answer: Expected answer text
        expected_clarification: Whether clarification is expected (kept for consistency)

    Returns:
        Dict with charts_answer_score, agent_answer_score, and actual values

    """
    # If no expected answer, both scores are None (check not applicable)
    if not expected_answer:
        return {
            "charts_answer_score": None,
            "agent_answer_score": None,
            "actual_charts_answer": None,
            "actual_agent_answer": None,
            "error": "Missing expected answer",
        }

    # Extract charts insight
    charts_data = agent_state.get("charts_data", [])
    actual_charts_answer = charts_data[0].get("insight", "") if charts_data else ""

    # Extract agent message
    messages = agent_state.get("messages", [])
    actual_agent_answer = ""
    if messages:
        content = messages[-1].content
        # For Gemini, content is a list, with thinking and query as separate messages
        if isinstance(content, list):
            actual_agent_answer = content[-1]
        else:
            actual_agent_answer = content

    # Score charts answer
    charts_answer_score = None
    if actual_charts_answer:
        # Has insight (even if empty string), evaluate it
        charts_answer_score = llm_judge(expected_answer, actual_charts_answer)
    # else: No charts data at all, return None (not applicable)

    # Score agent answer
    agent_answer_score = None
    if actual_agent_answer:
        # Has message response, evaluate it
        agent_answer_score = llm_judge(expected_answer, actual_agent_answer)
    # else: No agent message, return None (not applicable)

    # Set actual values to None if empty strings for cleaner CSV output
    return {
        "charts_answer_score": charts_answer_score,
        "agent_answer_score": agent_answer_score,
        "actual_charts_answer": actual_charts_answer or None,
        "actual_agent_answer": actual_agent_answer or None,
        "error": "",
    }
