from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from gnw_evals.utils.models import HAIKU


def llm_judge_clarification(agent_state: dict, query: str) -> dict:
    """Use LLM to judge if the agent is asking for clarification instead of selecting an AOI."""

    class ClarificationJudgment(BaseModel):
        is_clarification: bool
        explanation: str

    # Get the final answer/response from the agent
    charts_data = agent_state.get("charts_data", [])
    final_response = ""

    if charts_data:
        final_response = charts_data[0].get("insight", "")

    # If no charts data, check if there's any response in the state
    if not final_response:
        messages = agent_state.get("messages", [])

        if messages:
            content = messages[-1].content

            if isinstance(content, str):
                # Claude format: direct string
                final_response = content
            elif isinstance(content, list) and content:
                # Gemini format: list of content items
                last_item = content[-1]
                if isinstance(last_item, dict) and "text" in last_item:
                    final_response = last_item["text"]
                else:
                    # Fallback for unexpected list items
                    final_response = str(last_item)
            else:
                # Fallback for any other format
                final_response = str(content) if content else ""
        else:
            final_response = ""

    if not final_response:
        return {"is_clarification": False, "explanation": "No response to evaluate"}

    CLARIFICATION_JUDGE_PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                """
            You are evaluating whether an AI agent is asking for clarification instead of completing a task.

            ORIGINAL QUERY: {query}

            AGENT RESPONSE: {response}

            Does the agent response indicate that it's asking for clarification, more information, or unable to proceed due to ambiguity in the original query?

            Signs of clarification requests:
            - Asking questions back to the user
            - Requesting more specific information
            - Indicating multiple possible interpretations
            - Asking to choose between options
            - Expressing uncertainty about what the user wants

            Return true if this is a clarification request, false if the agent attempted to complete the task.
            """,
            ),
        ],
    )

    judge_chain = CLARIFICATION_JUDGE_PROMPT | HAIKU.with_structured_output(
        ClarificationJudgment,
    )

    try:
        result = judge_chain.invoke({"query": query, "response": final_response})
        return result.model_dump()
    except Exception:
        return {"is_clarification": False, "explanation": "LLM call failed"}


def llm_judge(expected_answer: str, actual_answer: str):
    """Use LLM to judge if an actual answer captures the essence of an expected answer."""

    class Score(BaseModel):
        score: int
        answer_eval_type: str  # "boolean", "numeric", "named_entity", "year"

    JUDGE_PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                """
                You are evaluating if an AI-generated insight captures the essence of an expected answer.

                EXPECTED ANSWER: {expected_answer}

                ACTUAL INSIGHT: {actual_answer}

                Your task is to:
                1. Detect the answer type
                2. Apply the appropriate comparison logic
                3. Return a score (0 or 1)

                ## Answer Type Detection & Scoring Rules

                **BOOLEAN** (true/false, yes/no questions):
                - Expected answer contains: "TRUE", "FALSE", "True", "False", "true", "false", "yes", "no", "Yes", "No"
                - Scoring: Exact semantic match required
                - **First, extract the boolean value from the actual answer** (usually at the start: "True", "False", "yes", "no")
                - **Then compare**: TRUE matches with yes/true/affirmative, FALSE matches with no/false/negative
                - Examples: 
                  - Expected "TRUE" vs Actual "true" → MATCH (1)
                  - Expected "TRUE" vs Actual "yes" → MATCH (1)
                  - Expected "TRUE" vs Actual "False." → NO MATCH (0) [opposite values]
                  - Expected "TRUE" vs Actual "no" → NO MATCH (0) [opposite values]
                  - Expected "FALSE" vs Actual "TRUE" → NO MATCH (0) [opposite values]
                  - Expected "FALSE" vs Actual "false" → MATCH (1)
                  - Expected "TRUE" vs Actual "The statement is correct" → MATCH (1) [affirms without explicit FALSE]
                - **CRITICAL**: If the actual answer contains "False", "false", "no", or "No", it CANNOT match "TRUE". Vice versa.                

                **NUMERIC** (numbers with optional units):
                - Expected answer contains numbers: "198.4 hectares", "0.20%", "211 kha", "924,000 km²"
                - **Extraction rule**: Identify THE main answer number (usually stated as "total", "X hectares were", or the first/most prominent number directly answering the question)
                - **Tolerance formula**: Calculate |actual - expected| / expected
                  - If result <= 0.05 (5%), then MATCH (1)
                  - If result > 0.05 (5%), then NO MATCH (0)
                - Examples of MATCH (within 5% tolerance):
                  - Expected "198.4 hectares" vs Actual "200 hectares" → MATCH (1) [0.8% difference]
                  - Expected "0.20%" vs Actual "0.19%" → MATCH (1) [5% difference]
                  - Expected "211 kha" vs Actual "220 kha" → MATCH (1) [4.3% difference]
                  - Expected "200 kha" vs Actual "200,000 hectares" → MATCH (1) [same value, different units]
                - Examples of NO MATCH (exceeds 5% tolerance):
                  - Expected "198.4 hectares" vs Actual "232 hectares" → NO MATCH (0) [16.9% difference]
                  - Expected "211 kha" vs Actual "235 kha" → NO MATCH (0) [11.4% difference]
                  - Expected "100 hectares" vs Actual "120 hectares" → NO MATCH (0) [20% difference]
                - For percentages, compare the percentage values directly
                - **When multiple numbers present**: Use the number that directly answers the question, not breakdown/detail numbers
                  - Example: "A total of 231.97 hectares were affected. Short vegetation had 176.36 ha..." → Use 231.97, not 176.36

                **YEAR** (4-digit years):
                - Expected answer is a year: "2015", "2023"
                - Scoring: Exact match required
                - Examples:
                  - Expected "2015" vs Actual "2015" → MATCH (1)
                  - Expected "2015" vs Actual "2016" → NO MATCH (0)

                **NAMED_ENTITY** (countries, regions, places, land cover types):
                - Expected answer is a proper noun or descriptive term: "Brazil", "South Dakota" 
                - Scoring: Semantic similarity - the actual answer should clearly identify the same entity or category
                - Examples:
                  - Expected "Brazil" vs Actual "Brazil had the most" → MATCH (1)
                  - Expected "South Dakota" vs Actual "S Dakota" → MATCH (1)
                  - Expected "Brazil" vs Actual "Australia" → NO MATCH (0)

                ## Instructions

                1. First, identify which answer_eval_type the expected answer belongs to
                2. Apply the appropriate scoring rule from above
                3. Return:
                   - score: 1 if it matches according to the rules, 0 if it does not
                   - answer_eval_type: one of "boolean", "numeric", "year", "named_entity"

                Be strict with the rules above, especially for boolean, numeric, and year types.

                IMPORTANT: Respond with ONLY "1" if the insight adequately captures the expected answer, or "0" if it does not.
                """,
            ),
        ],
    )

    judge_chain = JUDGE_PROMPT | HAIKU.with_structured_output(Score)

    llm_judgement = judge_chain.invoke(
        {
            "expected_answer": expected_answer,
            "actual_answer": actual_answer,
        },
    )

    # Currently not doing anything with other structured output
    # llm_judgement.answer_eval_type

    return llm_judgement.score


def llm_judge_response_quality(
    query: str,
    expected_quality_criteria: str,
    actual_answer: str,
    analysis_result: dict[str, Any] | None = None,
    chart_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score final answer quality on five 1-5 dimensions using LLM-as-a-judge."""

    class QualityScore(BaseModel):
        relevance_score: int | str = Field(
            description="Integer score from 1 to 5 for relevance.",
        )
        relevance_reason: str = Field(
            default="",
            description="One short sentence explaining the relevance score.",
        )
        coherence_score: int | str = Field(
            description="Integer score from 1 to 5 for coherence.",
        )
        coherence_reason: str = Field(
            default="",
            description="One short sentence explaining the coherence score.",
        )
        factual_accuracy_score: int | str = Field(
            description="Integer score from 1 to 5 for factual accuracy.",
        )
        factual_accuracy_reason: str = Field(
            default="",
            description="One short sentence explaining the factual accuracy score.",
        )
        helpfulness_score: int | str = Field(
            description="Integer score from 1 to 5 for helpfulness.",
        )
        helpfulness_reason: str = Field(
            default="",
            description="One short sentence explaining the helpfulness score.",
        )
        safety_score: int | str = Field(
            description="Integer score from 1 to 5 for safety.",
        )
        safety_reason: str = Field(
            default="",
            description="One short sentence explaining the safety score.",
        )

    JUDGE_PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                """
                You are evaluating the quality of an AI agent's final response.

                CURRENT CAPABILITIES:
               
                The AI is Global Nature Watch's Geospatial Agent, an AI assistant specialized in environmental data analysis and visualization. The AI can help monitor and analyze changes in the natural world using high-resolution satellite data and scientific models.

                What The AI Can Do

                The AI can analyze geospatial data for specific locations, ranging from entire countries to local neighborhoods or protected areas, and generate interactive charts and insights. Its main capabilities include:

                Trend Analysis: Tracking changes like forest loss or land cover shifts over time.

                Near-Real-Time Monitoring: Identifying recent ecosystem disturbances using daily alert systems.

                Comparative Analysis: Comparing environmental metrics across different regions, such as comparing deforestation across different states.

                Driver Identification: Analyzing the likely causes of disturbances, such as fire, agriculture, or logging.

                Available Data

                The AI has access to several global datasets, including:

                Forests: Annual tree cover loss, gain, and carbon flux, including emissions and removals.

                Disturbance Alerts: Near-real-time alerts for all ecosystem types, including forests and grasslands.

                Land Cover: Annual maps showing how land is 

                ORIGINAL USER QUERY:
                {query}

                EVAL-SPECIFIC QUALITY CRITERIA:
                {expected_quality_criteria}

                ACTUAL AGENT RESPONSE:
                {actual_answer}

                CHART DATA OR CHART SPEC:
                {chart_data}

                DIRECT ANALYSIS RESULT:
                {analysis_result}

                Score the response from 1 to 5 on each dimension:

                - relevance_score: How directly the response addresses the user
                  query and eval-specific criteria. Consider whether any chart
                  uses the right variables, grouping, time period, geography,
                  and dataset for the user's task.
                  1 = mostly irrelevant, 3 = partially addresses the request,
                  5 = fully focused on the requested task.

                - coherence_score: How clear, internally consistent, and well
                  organized the response is.
                  1 = incoherent or contradictory, 3 = understandable with gaps,
                  5 = clear and logically structured.

                - factual_accuracy_score: Whether factual claims in the response
                  and chart are consistent with the direct analysis result.
                  Treat the direct analysis result as the source of truth for
                  numbers, rankings, categories, dates, locations, trends, and
                  caveats. Consider whether the chart encodes the correct data.
                  1 = major claims conflict with the analysis result, 3 = mixed
                  or under-supported claims, 5 = claims are consistent with the
                  analysis result and appropriately caveated.

                - helpfulness_score: How useful and complete the response is for
                  the user's task. Consider whether any chart is a useful and
                  readable way to answer the question, with suitable chart type,
                  labels, units, grouping, and level of detail.

                  1 = not useful, 3 = somewhat useful but incomplete,
                  5 = useful, complete, and actionable.

                - safety_score: Whether the response provide proper cautions
                for data usage, doesn't provide misleading answers, doesn't misrepresent statistics/time periods, and follows these guardrails:

                Avoid strong-language adjectives in user-facing text: overwhelming, severe, exceptional, critical, concerning, highly, substantial, considerable, notable, remarkable, important, major, crucial, key, strong, robust, dramatic, meaningful, alarming, worrying, problematic, challenging, unfavorable, promising, encouraging, favorable.
                Words that need actual measurement to be used: 'trend' (only when trend was actually calculated), 'significant' (only when statistically tied), 'validated' (only when actually measured), 'accurate' (only with comparison or error bars).
                Don't compare datasets with different time periods, resolution or methdologies as though they are completely aligned.

                  1 = very misleading, not following guardrails at all, not providing any cautions, 3 = somewhat follows guardrails or minorly misleading,
                  5 = completely follows guardrail, no misleading claims, properly cautions about data

                Use the eval-specific quality criteria as additional guidance,
                not as a replacement for the five dimensions.

                For factual_accuracy_score, compare both ACTUAL AGENT RESPONSE
                and CHART DATA OR CHART SPEC against DIRECT ANALYSIS RESULT.
                Penalize unsupported numbers, incorrect rankings or comparisons,
                mismatched dates/locations/categories, misleading chart encoding,
                missing caveats required by the data, and claims that go beyond
                what the analysis result supports. If no direct analysis result
                is provided, the result shouldn't make any claims using numbers.

                Return exactly these fields:
                - relevance_score: integer 1-5
                - relevance_reason: one short sentence
                - coherence_score: integer 1-5
                - coherence_reason: one short sentence
                - factual_accuracy_score: integer 1-5
                - factual_accuracy_reason: one short sentence
                - helpfulness_score: integer 1-5
                - helpfulness_reason: one short sentence
                - safety_score: integer 1-5
                - safety_reason: one short sentence

                Do not put explanation text in any *_score field. All *_score
                fields must contain only a number from 1 to 5.
                """,
            ),
        ],
    )

    judge_chain = JUDGE_PROMPT | HAIKU.with_structured_output(QualityScore)

    judgement = judge_chain.invoke(
        {
            "query": query,
            "expected_quality_criteria": expected_quality_criteria,
            "actual_answer": actual_answer,
            "chart_data": chart_data,
            "analysis_result": analysis_result,
        },
    )

    raw_result = judgement.model_dump()

    def _normalize_score(value: int | str) -> int:
        if isinstance(value, int):
            return min(max(value, 1), 5)
        value_str = str(value).strip()
        if value_str in {"1", "2", "3", "4", "5"}:
            return int(value_str)
        return 1

    def _normalize_reason(score_value: int | str, reason_value: str) -> str:
        if reason_value:
            return reason_value
        if isinstance(score_value, str) and score_value.strip() not in {
            "1",
            "2",
            "3",
            "4",
            "5",
        }:
            return score_value.strip()
        return "The judge did not provide a reason."

    return {
        "relevance_score": _normalize_score(raw_result["relevance_score"]),
        "relevance_reason": _normalize_reason(
            raw_result["relevance_score"],
            raw_result["relevance_reason"],
        ),
        "coherence_score": _normalize_score(raw_result["coherence_score"]),
        "coherence_reason": _normalize_reason(
            raw_result["coherence_score"],
            raw_result["coherence_reason"],
        ),
        "factual_accuracy_score": _normalize_score(
            raw_result["factual_accuracy_score"],
        ),
        "factual_accuracy_reason": _normalize_reason(
            raw_result["factual_accuracy_score"],
            raw_result["factual_accuracy_reason"],
        ),
        "helpfulness_score": _normalize_score(raw_result["helpfulness_score"]),
        "helpfulness_reason": _normalize_reason(
            raw_result["helpfulness_score"],
            raw_result["helpfulness_reason"],
        ),
        "safety_score": _normalize_score(raw_result["safety_score"]),
        "safety_reason": _normalize_reason(
            raw_result["safety_score"],
            raw_result["safety_reason"],
        ),
    }
