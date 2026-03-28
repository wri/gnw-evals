from typing import Any

from gnw_evals.evaluators.llm_judges import llm_judge, llm_judge_text_quality


def evaluate_final_answer(
    agent_state: dict[str, Any],
    expected_answer: str,
) -> dict[str, Any]:
    """Check if final answer contains key information from expected answer using LLM-as-a-judge.

    Clarification detection is handled separately by evaluate_clarification().
    This function only evaluates answers.

    Returns TWO separate "answer" scores:
    - charts_answer_score: Compares expected_answer to charts_data[0]["insight"]
    - agent_answer_score: Compares expected_answer to messages[-1].content

    Args:
        agent_state: Final agent state after execution
        expected_answer: Expected answer text

    Returns:
        Dict with charts_answer_score, agent_answer_score, and actual values

    """
    # Extract charts insight
    charts_data = agent_state.get("charts_data", [])
    actual_charts_answer = charts_data[0].get("insight", "") if charts_data else ""

    # Extract agent message
    messages = agent_state.get("messages", [])
    actual_agent_answer = ""
    if messages:
        content = messages[-1].content

        if isinstance(content, str):
            # Claude format: direct string
            actual_agent_answer = content
        elif isinstance(content, list) and content:
            # Gemini format: list of content items
            last_item = content[-1]
            if isinstance(last_item, dict) and "text" in last_item:
                actual_agent_answer = last_item["text"]
            else:
                # Fallback for unexpected list items
                actual_agent_answer = str(last_item)
        else:
            # Fallback for any other format
            actual_agent_answer = str(content) if content else ""

    # If no expected answer, both scores are None
    if not expected_answer:
        return {
            "charts_answer_score": None,
            "agent_answer_score": None,
            "actual_charts_answer": actual_charts_answer,
            "actual_agent_answer": actual_agent_answer,
        }

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
    }


def evaluate_guardrail_answer(
    agent_state: dict[str, Any],
    expected_guardrail_answer: str,
) -> dict[str, Any]:
    """Evaluate metadata/guardrail answers using LLM-as-a-judge.

    Unlike evaluate_final_answer, this evaluator:
    - Does NOT require a data pull to have occurred
    - Uses a text quality judge suited for free-text factual answers
      (citations, methodology descriptions, coverage info)
    - Is triggered by expected_guardrail_answer column, independent of
      expected_dataset_id or data pull scoring

    Args:
        agent_state: Final agent state after execution
        expected_guardrail_answer: Expected answer text

    Returns:
        Dict with guardrail_answer_score (0/1/None) and actual_guardrail_answer

    """
    if not expected_guardrail_answer:
        return {
            "guardrail_answer_score": None,
            "actual_guardrail_answer": None,
        }

    # Extract agent's final message (same logic as evaluate_final_answer)
    messages = agent_state.get("messages", [])
    actual_answer = ""
    if messages:
        content = messages[-1].content
        if isinstance(content, str):
            actual_answer = content
        elif isinstance(content, list) and content:
            last_item = content[-1]
            if isinstance(last_item, dict) and "text" in last_item:
                actual_answer = last_item["text"]
            else:
                actual_answer = str(last_item)
        else:
            actual_answer = str(content) if content else ""

    if not actual_answer:
        return {
            "guardrail_answer_score": None,
            "actual_guardrail_answer": None,
        }

    score = llm_judge_text_quality(expected_guardrail_answer, actual_answer)
    return {
        "guardrail_answer_score": score,
        "actual_guardrail_answer": actual_answer or None,
    }
