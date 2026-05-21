"""Tests for CLI progress output during eval runs."""

from gnw_evals.core import (
    _all_checks_passed,
    _print_failure_details,
    _print_pass_progress,
    _test_display_id,
)
from gnw_evals.utils.eval_types import ExpectedData, TestResult


def _minimal_result(**kwargs) -> TestResult:
    defaults = {
        "thread_id": "t1",
        "query": "test query",
        "overall_score": 1.0,
        "execution_time": "2026-01-01T00:00:00",
    }
    defaults.update(kwargs)
    return TestResult(**defaults)


def test_all_checks_passed_when_all_scores_are_one() -> None:
    result = _minimal_result(
        agent_answer_score=1.0,
        aoi_id_match_score=1.0,
    )
    assert _all_checks_passed(result) is True


def test_all_checks_passed_false_when_any_score_below_one() -> None:
    result = _minimal_result(
        agent_answer_score=1.0,
        aoi_id_match_score=0.0,
    )
    assert _all_checks_passed(result) is False


def test_all_checks_passed_false_on_error() -> None:
    result = _minimal_result(error="API timeout")
    assert _all_checks_passed(result) is False


def test_test_display_id_prefers_test_id() -> None:
    case = ExpectedData(test_id="1-042")
    assert _test_display_id(case, 0) == "1-042"


def test_test_display_id_falls_back_to_index() -> None:
    case = ExpectedData()
    assert _test_display_id(case, 4) == "#5"


def test_print_pass_progress_writes_dot(capsys) -> None:
    _print_pass_progress()
    _print_pass_progress()
    assert capsys.readouterr().out == ".."


def test_print_failure_details_includes_test_id(capsys) -> None:
    case = ExpectedData(test_id="1-001", query="What is the area?")
    result = _minimal_result(agent_answer_score=0.0)
    _print_failure_details(case, 0, 10, result, 12.3)
    output = capsys.readouterr().out
    assert "[FAIL] 1-001" in output
    assert "0/1 checks passed" in output
    assert "agent answer: 0.0" in output
    assert "query: What is the area?" in output
