import json
from typing import Any

from gnw_evals.evaluators.llm_judges import (
    llm_judge,
    llm_judge_chart,
    llm_judge_expected_text,
)


def _serialize_chart_json(chart: dict[str, Any]) -> str:
    """Serialize chart JSON without prose-only insight text."""
    chart_json = {key: value for key, value in chart.items() if key != "insight"}
    if not chart_json:
        return ""
    serialized = json.dumps(chart_json, ensure_ascii=False, default=str)
    return serialized[:50000]


def evaluate_final_answer(
    agent_state: dict[str, Any],
    expected_answer: str,
    expected_text: str = "",
    query: str = "",
) -> dict[str, Any]:
    """Check if final answer contains key information from expected answer using LLM-as-a-judge.

    Clarification detection is handled separately by evaluate_clarification().
    This function only evaluates answers.

    Returns answer scores:
    - charts_answer_score: Judges whether charts_data[0] JSON is appropriate
      for the query and expected answer
    - agent_answer_score: Compares expected_answer to messages[-1].content
    - expected_text_match_score: Checks whether messages[-1].content includes
      expected_text semantically

    Args:
        agent_state: Final agent state after execution
        expected_answer: Expected answer text
        expected_text: Expected text, meaning, or behavior to check in agent response
        query: Original user query

    Returns:
        Dict with charts_answer_score, agent_answer_score, and actual values

    """
    # Extract charts insight
    charts_data = agent_state.get("charts_data", [])
    actual_charts_answer = charts_data[0].get("insight", "") if charts_data else ""
    actual_charts_json = _serialize_chart_json(charts_data[0]) if charts_data else ""

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

    # Score chart JSON, not prose insight text.
    charts_answer_score = None
    if expected_answer and actual_charts_json:
        charts_answer_score = llm_judge_chart(
            query,
            expected_answer,
            actual_charts_json,
        )

    # Score agent answer
    agent_answer_score = None
    if expected_answer and actual_agent_answer:
        # Has message response, evaluate it
        agent_answer_score = llm_judge(expected_answer, actual_agent_answer)
    # else: No agent message, return None (not applicable)

    expected_text_match_score = None
    if expected_text and actual_agent_answer:
        expected_text_match_score = llm_judge_expected_text(
            expected_text,
            actual_agent_answer,
        )

    # Set actual values to None if empty strings for cleaner CSV output
    return {
        "charts_answer_score": charts_answer_score,
        "agent_answer_score": agent_answer_score,
        "expected_text_match_score": expected_text_match_score,
        "actual_charts_answer": actual_charts_answer or None,
        "actual_charts_json": actual_charts_json or None,
        "actual_agent_answer": actual_agent_answer or None,
    }
