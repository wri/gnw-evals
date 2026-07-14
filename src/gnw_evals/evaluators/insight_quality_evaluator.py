"""Insight quality evaluator using LLM-as-judge.

A single evaluator that covers multiple test types by accepting a per-test
judge_instruction:
  - INSIGHT-UNIT   correct units (ha, kha, MgCO2e, tCO2e, etc.)
  - INSIGHT-INTERP interpretation quality / presentation_instructions compliance
  - INSIGHT-TERM   terminology compliance
  - INSTRUCT-TEMPORAL temporal constraint enforcement
  - INSTRUCT-CAVEAT   required caveats and disclaimers
  - INSTRUCT-COMBINE  data combination rules
  - INSTRUCT-CHART    dataset-specific chart rules
  - INSTRUCT-REDIRECT dataset redirect recommendations
"""

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from gnw_evals.evaluators.utils import normalize_value
from gnw_evals.utils.models import HAIKU

logger = logging.getLogger(__name__)

_JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "user",
            """You are evaluating the quality of an AI-generated data insight for Global Nature Watch, a geospatial environmental data platform.

ORIGINAL QUERY: {query}
AGENT INSIGHT: {insight}
CHART TYPE PRODUCED: {chart_type}
DATA SUMMARY (first 5 rows): {data_summary}

EVALUATION INSTRUCTION: {judge_instruction}

Based on the evaluation instruction, does this insight meet the criteria?
Evaluate strictly against the instruction. The instruction may check for:
- Correct units (ha, kha, MgCO2e, tCO2e, etc.)
- Required terminology ("tree cover loss" not "deforestation", "tree cover gain" not "restoration")
- Required caveats and disclaimers (methodology changes, data limitations, interpretation warnings)
- Temporal constraint compliance (refusing timeseries for snapshot datasets)
- Correct dataset redirect recommendations
- Data combination rules (merging categories as instructed)
- Chart type restrictions per dataset

Return 1 if it passes ALL criteria in the instruction, 0 if it fails ANY criterion. Provide a brief explanation of your judgement.""",
        ),
    ],
)


def evaluate_insight_quality(
    agent_state: dict[str, Any],
    query: str,
    judge_instruction: str,
) -> dict[str, Any]:
    """Evaluate insight quality using a per-test LLM judge instruction.

    Args:
        agent_state: Final agent state after execution
        query: Original user query
        judge_instruction: Per-test evaluation criteria string

    Returns:
        Dict with insight_quality_score (0/1/None) and insight_quality_explanation

    """
    result: dict[str, Any] = {
        "insight_quality_score": None,
        "insight_quality_explanation": None,
    }

    if not normalize_value(judge_instruction):
        return result

    charts_data = agent_state.get("charts_data", [])
    if not charts_data:
        return result

    first_chart = charts_data[0]
    insight = first_chart.get("insight", "") or ""
    chart_type = first_chart.get("type", "") or ""
    raw_data = first_chart.get("data", []) or []

    if not insight:
        return result

    # Take the first 5 rows of data as a preview for the judge
    if isinstance(raw_data, list):
        data_preview = raw_data[:5]
    elif isinstance(raw_data, dict):
        # Handle dict-of-lists format
        data_preview = {k: v[:5] for k, v in raw_data.items() if isinstance(v, list)}
    else:
        data_preview = []

    class QualityJudgement(BaseModel):
        score: int
        explanation: str

    try:
        messages = _JUDGE_PROMPT.format_messages(
            query=query,
            insight=insight,
            chart_type=chart_type or "unknown",
            data_summary=str(data_preview),
            judge_instruction=judge_instruction,
        )
        judgement = HAIKU.with_structured_output(QualityJudgement).invoke(messages)
        result["insight_quality_score"] = float(judgement.score)
        result["insight_quality_explanation"] = judgement.explanation
    except Exception:
        logger.exception("insight_quality_evaluator failed for query=%r", query)

    return result
