from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

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
        return False  # No response to evaluate

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
        return False  # Default to not clarification if LLM call fails


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
                - Expected answer contains: "TRUE", "FALSE", "true", "false", "yes", "no", "Yes", "No"
                - Scoring: Exact semantic match required
                - Examples: 
                  - Expected "TRUE" vs Actual "true" → MATCH (1)
                  - Expected "TRUE" vs Actual "yes" → MATCH (1)
                  - Expected "TRUE" vs Actual "The statement is correct" → MATCH (1) if actual clearly affirms
                  - Expected "FALSE" vs Actual "TRUE" → NO MATCH (0)

                **NUMERIC** (numbers with optional units):
                - Expected answer contains numbers: "198.4 hectares", "0.20%", "211 kha", "924,000 km²"
                - Scoring: Extract the primary numeric value and compare with 5% tolerance
                - Examples:
                  - Expected "198.4 hectares" vs Actual "200 hectares" → MATCH (1) [within tolerance]
                  - Expected "0.20%" vs Actual "0.19%" → MATCH (1) [within tolerance]
                  - Expected "211 kha" vs Actual "220 kha" → NO MATCH (0) [exceeds tolerance]
                  - Expected "200 kha" vs Actual "200,000 hectares" → MATCH (1) [within tolerance]
                - For percentages, compare the percentage values directly

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

    score = judge_chain.invoke(
        {
            "expected_answer": expected_answer,
            "actual_answer": actual_answer,
        },
    )

    # Currently not doing anything with other structured output
    # score.answer_eval_type

    return score.score
