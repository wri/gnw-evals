from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from gnw_evals.utils.models import HAIKU

# Relative tolerance for numeric answers, as a fraction of the expected value.
# Interpolated into the prompt so the threshold and its worked examples cannot drift.
#
# Applies to `llm_judge` (agent_answer) only. `llm_judge_chart` deliberately has no
# tolerance rule: it does not reliably compute the comparison. Asked about a chart whose
# 25 yearly values sum to 25.31 Mha, it reported that same chart as summing to 27.4 Mha
# and to 26.0 Mha, each time "within tolerance" of whatever expected value it was given.
# A prose tolerance there turns wrong-number failures into false passes, so the chart
# judge needs the comparison done in code. See llm/TASKS.md.
NUMERIC_TOLERANCE = 0.02
_TOLERANCE_PCT = f"{NUMERIC_TOLERANCE:.0%}"

# Numeric scoring rules for the answer judge. Kept at module level, and free of `{}` so
# it can be concatenated into a ChatPromptTemplate without being read as a placeholder —
# and so tests can assert on it without an API call.
_NUMERIC_RULES = f"""
                **NUMERIC** (numbers with optional units):
                - Expected answer contains numbers: "198.4 hectares", "0.20%", "211 kha", "924,000 km²"
                - **Extraction rule**: Identify THE main answer number (usually stated as "total", "X hectares were", or the first/most prominent number directly answering the question)
                - **Tolerance formula**: Calculate |actual - expected| / expected
                  - If result <= {NUMERIC_TOLERANCE} ({_TOLERANCE_PCT}), then MATCH (1)
                  - If result > {NUMERIC_TOLERANCE} ({_TOLERANCE_PCT}), then NO MATCH (0)
                - Examples of MATCH (within {_TOLERANCE_PCT} tolerance):
                  - Expected "198.4 hectares" vs Actual "200 hectares" → MATCH (1) [0.8% difference]
                  - Expected "211 kha" vs Actual "215 kha" → MATCH (1) [1.9% difference]
                  - Expected "100 hectares" vs Actual "102 hectares" → MATCH (1) [exactly {_TOLERANCE_PCT}, the boundary is inclusive]
                  - Expected "200 kha" vs Actual "200,000 hectares" → MATCH (1) [same value, different units]
                - Examples of NO MATCH (exceeds {_TOLERANCE_PCT} tolerance):
                  - Expected "100 hectares" vs Actual "103 hectares" → NO MATCH (0) [3% difference]
                  - Expected "0.20%" vs Actual "0.19%" → NO MATCH (0) [5% difference]
                  - Expected "211 kha" vs Actual "235 kha" → NO MATCH (0) [11.4% difference]
                  - Expected "198.4 hectares" vs Actual "232 hectares" → NO MATCH (0) [16.9% difference]
                - For percentages, compare the percentage values directly
                - **When multiple numbers present**: Use the number that directly answers the question, not breakdown/detail numbers
                  - Example: "A total of 231.97 hectares were affected. Short vegetation had 176.36 ha..." → Use 231.97, not 176.36
"""

ANSWER_JUDGE_PROMPT = (
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
"""
    + _NUMERIC_RULES
    + """
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
                   - reason: one concise sentence explaining why you gave that score
                   - answer_eval_type: one of "boolean", "numeric", "year", "named_entity"

                Be strict with the rules above, especially for boolean, numeric, and year types.
                """
)


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

            Do NOT count the response as a clarification request if the agent directly answers the user's question
            and only asks an optional follow-up question afterward, such as offering to analyze a specific region,
            compare locations, or continue with a next step.

            Only return true if the response primarily asks for more information before it can answer,
            or says it cannot proceed because the original query is ambiguous.

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


def llm_judge(
    expected_answer: str,
    actual_answer: str,
    include_reason: bool = False,
):
    """Use LLM to judge if an actual answer captures the essence of an expected answer."""

    class Score(BaseModel):
        answer_eval_type: str  # "boolean", "numeric", "named_entity", "year"
        reason: str
        score: int

    JUDGE_PROMPT = ChatPromptTemplate.from_messages([("user", ANSWER_JUDGE_PROMPT)])

    judge_chain = JUDGE_PROMPT | HAIKU.with_structured_output(Score)

    llm_judgement = judge_chain.invoke(
        {
            "expected_answer": expected_answer,
            "actual_answer": actual_answer,
        },
    )

    if include_reason:
        return {
            "score": llm_judgement.score,
            "reason": llm_judgement.reason,
        }

    return llm_judgement.score


def llm_judge_chart(
    query: str,
    expected_answer: str,
    charts_json: str,
    codeact_summary: str = "",
    include_reason: bool = False,
) -> int | dict[str, int | str]:
    """Judge whether chart JSON(s) are appropriate and support the expected answer.

    Uses both the chart specification(s) and the agent's code-act reasoning
    (code blocks, execution output, analysis text) to evaluate whether
    the chart(s) are actually correct and answer the query.

    Accepts a JSON array of chart objects; each chart is evaluated and the
    overall score is 1 only if the set of charts together answers the query.
    """

    class ChartScore(BaseModel):
        reason: str
        score: int

    codeact_section = ""
    codeact_instruction = ""
    if codeact_summary:
        codeact_section = """

CODEACT REASONING:
{codeact_summary}

This shows the code the agent executed, the intermediate results, and its
analytical reasoning that led to the chart(s) above."""
        codeact_instruction = """

If codeact reasoning is provided, use it to cross-check the chart data.
If the code shows correct data processing but the chart specification has
wrong metrics, filters, or structure, score 0 because the chart itself is
flawed. If the code reveals incorrect analysis (e.g., wrong aggregation,
wrong data source) even if the chart specification looks plausible on its
own, also score 0.

"""

    full_prompt = (
        """You are evaluating whether one or more chart specifications are useful and correct for answering a user query.

USER QUERY:
{query}

EXPECTED ANSWER:
{expected_answer}

CHART JSON (JSON array of chart objects):
{charts_json}"""
        + codeact_section
        + """

The input is a JSON array of chart objects. There may be one chart or multiple.
Evaluate whether the set of charts together answers the user's query.

Score 1 if the chart(s) together appear appropriate for the query and their
encoded data, chart types, labels, dimensions, measures, filters, and time
ranges would help a user verify or understand the expected answer.

Score 0 if the chart(s) are missing important data, use the wrong
metric/location/date range, have unsuitable chart types for the comparison,
contradict the expected answer, or are too incomplete to judge.

Do not score based on any prose insight or narrative answer. Focus on the
chart specifications, encoded data, labels, fields, and visual structures.

"""
        + codeact_instruction
        + """Return:
- score: 1 or 0
- reason: one concise sentence explaining why you gave that score"""
    )

    JUDGE_PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                full_prompt,
            ),
        ],
    )

    judge_chain = JUDGE_PROMPT | HAIKU.with_structured_output(ChartScore)

    invoke_kwargs = {
        "query": query,
        "expected_answer": expected_answer,
        "charts_json": charts_json,
    }
    if codeact_summary:
        invoke_kwargs["codeact_summary"] = codeact_summary

    llm_judgement = judge_chain.invoke(invoke_kwargs)

    if include_reason:
        return {
            "score": llm_judgement.score,
            "reason": llm_judgement.reason,
        }

    return llm_judgement.score


def llm_judge_expected_text(
    expected_text: str,
    actual_answer: str,
    include_reason: bool = False,
) -> int | dict[str, int | str]:
    """Judge whether an answer includes semantically similar expected text."""

    class TextMatchScore(BaseModel):
        reason: str
        score: int

    JUDGE_PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                """
                You are evaluating whether an AI-generated response includes
                the expected information, meaning, or behavior.

                EXPECTED TEXT OR INSTRUCTION:
                {expected_text}

                ACTUAL AGENT RESPONSE:
                {actual_answer}

                Return score 1 if the actual response includes information that
                is semantically similar to the expected text, even if the wording
                is different. Also return 1 if the expected text is an
                instruction or qualitative behavior and the response satisfies
                it.

                Return score 0 if the response omits, contradicts, or only
                weakly implies the expected text or behavior.

                Examples:
                - Expected "30 x 30 resolution" matches responses that say
                  "30-meter by 30-meter pixels" or "30 m resolution".
                - Expected "clarifies to user that dataset isn't available"
                  matches responses that explain the requested dataset is not
                  available and ask the user to choose another option.

                Return:
                - score: 1 if the expected text/behavior is included, otherwise 0
                - reason: one concise sentence explaining why you gave that score
                """,
            ),
        ],
    )

    judge_chain = JUDGE_PROMPT | HAIKU.with_structured_output(TextMatchScore)
    judgement = judge_chain.invoke(
        {
            "expected_text": expected_text,
            "actual_answer": actual_answer,
        },
    )

    if include_reason:
        return {
            "score": judgement.score,
            "reason": judgement.reason,
        }

    return judgement.score
