import base64
import json
from typing import Any

from gnw_evals.evaluators.llm_judges import (
    llm_judge,
    llm_judge_chart,
    llm_judge_expected_text,
)


def _decode_codeact_parts(raw_parts: list[dict[str, Any]]) -> str:
    """Decode base64-encoded codeact parts into a readable summary string.

    The codeact_parts from agent state are stored with base64-encoded content.
    Parts have types: 'code_block' (Python code), 'text_output' (LLM reasoning),
    'execution_output' (printed stats/results).

    Returns a formatted string grouped by type, capped at a reasonable length.
    """
    if not raw_parts:
        return ""

    grouped: dict[str, list[str]] = {}
    for part in raw_parts:
        part_type = part.get("type", "unknown")
        content_b64 = part.get("content", "")
        try:
            decoded = base64.b64decode(content_b64).decode("utf-8")
        except Exception:
            decoded = content_b64  # fallback: use raw content

        grouped.setdefault(part_type, []).append(decoded)

    sections = []
    type_labels = {
        "code_block": "CODE",
        "text_output": "LLM REASONING",
        "execution_output": "EXECUTION OUTPUT",
    }
    for part_type, contents in grouped.items():
        label = type_labels.get(part_type, part_type.upper())
        combined = "\n---\n".join(contents)
        combined = combined[:8000]
        sections.append(f"## {label}\n\n{combined}")

    return "\n\n".join(sections)


def _serialize_charts_json(charts: list[dict[str, Any]]) -> str:
    """Serialize all chart JSONs without prose-only insight text."""
    if not charts:
        return ""
    chart_jsons = []
    for chart in charts:
        cleaned = {key: value for key, value in chart.items() if key != "insight"}
        if cleaned:
            chart_jsons.append(cleaned)
    if not chart_jsons:
        return ""
    serialized = json.dumps(chart_jsons, ensure_ascii=False, default=str)
    return serialized[:80000]


def _score_and_reason(result: Any) -> tuple[float | None, str | None]:
    """Normalize judge responses that may be a score or score/reason mapping."""
    if isinstance(result, dict):
        return result.get("score"), result.get("reason")
    return result, None


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
    - *_reason fields: Concise LLM explanations for each score

    Args:
        agent_state: Final agent state after execution
        expected_answer: Expected answer text
        expected_text: Expected text, meaning, or behavior to check in agent response
        query: Original user query

    Returns:
        Dict with charts_answer_score, agent_answer_score, and actual values

    """
    # Extract charts data (all charts, not just the first)
    charts_data = agent_state.get("charts_data", [])
    actual_charts_answer = "; ".join(
        chart.get("insight", "") for chart in charts_data if chart.get("insight")
    )
    actual_charts_json = _serialize_charts_json(charts_data)

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

    # Extract codeact parts (base64-encoded code/output from agent reasoning)
    raw_codeact_parts = agent_state.get("codeact_parts", [])
    codeact_summary = _decode_codeact_parts(raw_codeact_parts)

    # Score chart JSON, not prose insight text.
    charts_answer_score = None
    charts_answer_score_reason = None
    if expected_answer and actual_charts_json:
        charts_answer_score, charts_answer_score_reason = _score_and_reason(
            llm_judge_chart(
                query,
                expected_answer,
                actual_charts_json,
                codeact_summary=codeact_summary,
                include_reason=True,
            ),
        )

    # Score agent answer
    agent_answer_score = None
    agent_answer_score_reason = None
    if expected_answer and actual_agent_answer:
        # Has message response, evaluate it
        agent_answer_score, agent_answer_score_reason = _score_and_reason(
            llm_judge(
                expected_answer,
                actual_agent_answer,
                include_reason=True,
            ),
        )
    # else: No agent message, return None (not applicable)

    expected_text_match_score = None
    expected_text_match_score_reason = None
    if expected_text and actual_agent_answer:
        expected_text_match_score, expected_text_match_score_reason = _score_and_reason(
            llm_judge_expected_text(
                expected_text,
                actual_agent_answer,
                include_reason=True,
            ),
        )

    # Set actual values to None if empty strings for cleaner CSV output
    return {
        "charts_answer_score": charts_answer_score,
        "chart_answer_score_reason": charts_answer_score_reason,
        "agent_answer_score": agent_answer_score,
        "agent_answer_score_reason": agent_answer_score_reason,
        "expected_text_match_score": expected_text_match_score,
        "expected_text_match_score_reason": expected_text_match_score_reason,
        "actual_charts_answer": actual_charts_answer or None,
        "actual_charts_json": actual_charts_json or None,
        "actual_agent_answer": actual_agent_answer or None,
        "actual_codeact_summary": codeact_summary or None,
    }
