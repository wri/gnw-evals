"""Unit tests for the answer judge's numeric tolerance.

The tolerance is prose inside a prompt, so what can be tested without an API call is
that it is single-sourced, that it reaches the prompt, and that splicing it in has not
broken the LangChain placeholders. That last one matters: a stray `{` in a shared
fragment becomes a template variable and the judge call fails at runtime.

`llm_judge_chart` intentionally has no tolerance rule — see the comment on
NUMERIC_TOLERANCE and llm/TASKS.md.

Usage
$ uv run python -m pytest tests/test_numeric_tolerance.py -v
"""

from langchain_core.prompts import ChatPromptTemplate

from gnw_evals.evaluators.llm_judges import (
    _NUMERIC_RULES,
    ANSWER_JUDGE_PROMPT,
    NUMERIC_TOLERANCE,
)

TOLERANCE_PCT = f"{NUMERIC_TOLERANCE:.0%}"


def test_tolerance_is_two_percent():
    """The agreed threshold. Changing it should be a deliberate, visible edit."""
    assert NUMERIC_TOLERANCE == 0.02


def test_answer_judge_prompt_states_the_tolerance():
    """The answer judge decides numeric rows on this figure, so it must carry it."""
    assert f"<= {NUMERIC_TOLERANCE} ({TOLERANCE_PCT})" in ANSWER_JUDGE_PROMPT
    assert f"> {NUMERIC_TOLERANCE} ({TOLERANCE_PCT})" in ANSWER_JUDGE_PROMPT
    assert _NUMERIC_RULES in ANSWER_JUDGE_PROMPT


def test_threshold_and_examples_cannot_drift_apart():
    """Every worked example is generated from the constant, so 5% cannot linger."""
    assert "0.05" not in _NUMERIC_RULES
    assert f"within {TOLERANCE_PCT} tolerance" in _NUMERIC_RULES
    assert f"exceeds {TOLERANCE_PCT} tolerance" in _NUMERIC_RULES


def test_answer_judge_prompt_has_no_stale_five_percent_match_example():
    """0.20% vs 0.19% is a 5% difference: a MATCH at the old threshold, not at 2%."""
    assert 'Expected "0.20%" vs Actual "0.19%" → NO MATCH' in ANSWER_JUDGE_PROMPT


def test_answer_judge_prompt_documents_the_inclusive_boundary():
    """100 vs 102 is exactly 2%; the rule says the boundary is inclusive."""
    assert (
        'Expected "100 hectares" vs Actual "102 hectares" → MATCH'
        in ANSWER_JUDGE_PROMPT
    )
    assert (
        'Expected "100 hectares" vs Actual "103 hectares" → NO MATCH'
        in ANSWER_JUDGE_PROMPT
    )


def test_numeric_rules_add_no_template_variables():
    """A stray brace in the fragment would become a required input variable."""
    assert (
        ChatPromptTemplate.from_messages([("user", _NUMERIC_RULES)]).input_variables
        == []
    )


def test_assembled_prompt_exposes_exactly_the_expected_variables():
    """Guards against the fragment capturing or dropping a placeholder."""
    answer = ChatPromptTemplate.from_messages([("user", ANSWER_JUDGE_PROMPT)])
    assert sorted(answer.input_variables) == ["actual_answer", "expected_answer"]
