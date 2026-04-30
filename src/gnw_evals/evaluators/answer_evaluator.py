from typing import Any

from gnw_evals.evaluators.llm_judges import (
    llm_judge,
    llm_judge_response_quality,
)

MAX_PREVIEW_ITEMS = 5
MAX_STRING_LENGTH = 500


def _extract_latest_analysis_result(agent_state: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the latest analysis/statistics result from agent state."""
    stats = agent_state.get("statistics", [])
    if not stats:
        return None
    latest_result = stats[-1]
    return latest_result if isinstance(latest_result, dict) else None


def _compact_for_judge(value: Any, max_items: int = MAX_PREVIEW_ITEMS) -> Any:
    """Create a bounded preview of large nested data before sending to an LLM."""
    if isinstance(value, dict):
        return {
            key: _compact_for_judge(nested_value, max_items)
            for key, nested_value in value.items()
        }

    if isinstance(value, list):
        if len(value) <= max_items * 2:
            return [_compact_for_judge(item, max_items) for item in value]
        return {
            "total_items": len(value),
            "first_items": [
                _compact_for_judge(item, max_items) for item in value[:max_items]
            ],
            "last_items": [
                _compact_for_judge(item, max_items) for item in value[-max_items:]
            ],
        }

    if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
        return {
            "truncated": True,
            "original_length": len(value),
            "preview": value[:MAX_STRING_LENGTH],
        }

    return value


def evaluate_final_answer(
    agent_state: dict[str, Any],
    expected_answer: str,
    expected_quality_criteria: str = "",
    query: str = "",
) -> dict[str, Any]:
    """Check if final answer contains key information from expected answer using LLM-as-a-judge.

    Clarification detection is handled separately by evaluate_clarification().
    This function only evaluates answers.

    Returns TWO separate "answer" scores:
    - charts_answer_score: Compares expected_answer to charts_data[0]["insight"]
    - agent_answer_score: Compares expected_answer to messages[-1].content
    - response quality scores: Scores messages[-1].content on relevance,
      coherence, factual accuracy, helpfulness, and safety

    Args:
        agent_state: Final agent state after execution
        expected_answer: Expected answer text
        expected_quality_criteria: Optional rubric for five-dimension quality scoring
        query: Original user query

    Returns:
        Dict with answer scores, response quality scores, and actual values

    """
    # Extract charts insight
    charts_data = agent_state.get("charts_data", [])
    actual_chart_data = (
        charts_data[0] if charts_data and isinstance(charts_data[0], dict) else None
    )
    actual_charts_answer = (
        actual_chart_data.get("insight", "") if actual_chart_data else ""
    )

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

    # Score charts answer
    charts_answer_score = None
    if expected_answer and actual_charts_answer:
        # Has insight (even if empty string), evaluate it
        charts_answer_score = llm_judge(expected_answer, actual_charts_answer)
    # else: No charts data at all, return None (not applicable)

    # Score agent answer
    agent_answer_score = None
    if expected_answer and actual_agent_answer:
        # Has message response, evaluate it
        agent_answer_score = llm_judge(expected_answer, actual_agent_answer)
    # else: No agent message, return None (not applicable)

    quality_scores = {
        "response_relevance_score": None,
        "response_relevance_reason": None,
        "response_coherence_score": None,
        "response_coherence_reason": None,
        "response_factual_accuracy_score": None,
        "response_factual_accuracy_reason": None,
        "response_helpfulness_score": None,
        "response_helpfulness_reason": None,
        "response_safety_score": None,
        "response_safety_reason": None,
    }
    analysis_result = _extract_latest_analysis_result(agent_state)
    if expected_quality_criteria and actual_agent_answer:
        quality_result = llm_judge_response_quality(
            query=query,
            expected_quality_criteria=expected_quality_criteria,
            actual_answer=actual_agent_answer,
            analysis_result=_compact_for_judge(analysis_result),
            chart_data=_compact_for_judge(actual_chart_data),
        )
        quality_scores = {
            "response_relevance_score": quality_result["relevance_score"],
            "response_relevance_reason": quality_result["relevance_reason"],
            "response_coherence_score": quality_result["coherence_score"],
            "response_coherence_reason": quality_result["coherence_reason"],
            "response_factual_accuracy_score": quality_result[
                "factual_accuracy_score"
            ],
            "response_factual_accuracy_reason": quality_result[
                "factual_accuracy_reason"
            ],
            "response_helpfulness_score": quality_result["helpfulness_score"],
            "response_helpfulness_reason": quality_result["helpfulness_reason"],
            "response_safety_score": quality_result["safety_score"],
            "response_safety_reason": quality_result["safety_reason"],
        }

    # Set actual values to None if empty strings for cleaner CSV output
    return {
        "charts_answer_score": charts_answer_score,
        "agent_answer_score": agent_answer_score,
        **quality_scores,
        "actual_charts_answer": actual_charts_answer or None,
        "actual_agent_answer": actual_agent_answer or None,
    }
