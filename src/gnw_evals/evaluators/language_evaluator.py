"""Multilingual response evaluator.

Checks whether the agent responded in the same language as the query.
Minor use of English for technical terms (e.g. dataset names, "tree cover
loss") is acceptable — the surrounding prose must be in the expected language.
"""

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from gnw_evals.evaluators.utils import normalize_value
from gnw_evals.utils.models import HAIKU

logger = logging.getLogger(__name__)

LANGUAGE_NAMES: dict[str, str] = {
    "es": "Spanish",
    "id": "Bahasa Indonesian",
    "fr": "French",
    "pt": "Portuguese",
    "zh": "Mandarin Chinese",
}

_JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "user",
            """You are checking whether an AI agent responded in the correct language.

EXPECTED LANGUAGE: {expected_language_name}
AGENT RESPONSE: {response}

Is this response written primarily in {expected_language_name}?
Minor use of English for technical terms (e.g. dataset names, "tree cover loss") is acceptable —
the surrounding prose and explanations should be in {expected_language_name}.

Return 1 if the response is in the expected language, 0 if it is not.""",
        ),
    ],
)


def evaluate_language(
    agent_state: dict[str, Any],
    expected_language: str,
) -> dict[str, Any]:
    """Check whether the agent responded in the expected language.

    Args:
        agent_state: Final agent state after execution
        expected_language: BCP-47 language code ("es", "id", "fr", "pt", "zh"),
            or empty string for English / not applicable

    Returns:
        Dict with language_match_score (0/1/None)

    """
    result: dict[str, Any] = {"language_match_score": None}

    lang_code = normalize_value(expected_language).lower()
    if not lang_code:
        return result

    language_name = LANGUAGE_NAMES.get(lang_code)
    if not language_name:
        return result

    # Build a combined response from charts insight + final message
    response_parts: list[str] = []

    charts_data = agent_state.get("charts_data", [])
    if charts_data:
        insight = charts_data[0].get("insight", "")
        if insight:
            response_parts.append(insight)

    messages = agent_state.get("messages", [])
    if messages:
        content = messages[-1].content
        if isinstance(content, str):
            response_parts.append(content)
        elif isinstance(content, list) and content:
            last_item = content[-1]
            if isinstance(last_item, dict) and "text" in last_item:
                response_parts.append(last_item["text"])
            else:
                response_parts.append(str(last_item))

    response = "\n\n".join(response_parts).strip()
    if not response:
        result["language_match_score"] = 0.0
        return result

    class LanguageJudgement(BaseModel):
        score: int

    try:
        messages = _JUDGE_PROMPT.format_messages(
            expected_language_name=language_name,
            response=response,
        )
        judgement = HAIKU.with_structured_output(LanguageJudgement).invoke(messages)
        result["language_match_score"] = float(judgement.score)
    except Exception:
        logger.exception("language_evaluator failed for lang_code=%r", lang_code)

    return result
