"""Tests for human-readable --print-results formatting."""

from gnw_evals.utils.eval_types import TestResult
from gnw_evals.utils.result_display import format_test_result, print_results_to_screen


def _make_result(**overrides) -> TestResult:
    defaults = {
        "thread_id": "thread-1",
        "query": "Show vegetation in AOI X",
        "overall_score": 1.0,
        "execution_time": "2025-01-01T00:00:00Z",
        "duration_seconds": 3.5,
        "test_id": "t-001",
        "eval_set": "gold",
        "aoi_id_match_score": 1.0,
    }
    defaults.update(overrides)
    return TestResult(**defaults)


def test_format_passing_result_shows_summary_not_json():
    text = format_test_result(_make_result(), index=1, total=1)

    assert "[PASS]" in text
    assert "t-001" in text
    assert "overall 1.0" in text
    assert "Show vegetation" in text
    assert "thread-1" not in text
    assert "{" not in text


def test_format_failing_result_shows_scores_and_comparisons():
    text = format_test_result(
        _make_result(
            overall_score=0.5,
            aoi_id_match_score=0.0,
            expected_aoi_ids=["aoi-expected"],
            actual_id="aoi-wrong",
            actual_name="Wrong Place",
            error=None,
        ),
        index=2,
        total=5,
    )

    assert "[FAIL]" in text
    assert "2/5" in text
    assert "✗ aoi id match: 0.0" in text
    assert "expected: aoi-expected" in text
    assert "actual:   aoi-wrong" in text
    assert "Wrong Place" in text


def test_format_skips_empty_comparisons_and_large_json():
    text = format_test_result(
        _make_result(
            actual_charts_json='{"huge": true}',
            expected_dataset_id="",
            dataset_id_match_score=1.0,
        ),
        index=1,
        total=1,
    )

    assert "actual_charts_json" not in text
    assert "details:" not in text


def test_format_shows_score_reason_on_failure():
    text = format_test_result(
        _make_result(
            overall_score=0.0,
            charts_answer_score=0.0,
            chart_answer_score_reason="Chart missing expected series",
        ),
        index=1,
        total=1,
    )

    assert "Chart missing expected series" in text


def test_print_results_to_screen_prints_summary(capsys):
    print_results_to_screen(
        [
            _make_result(test_id="pass-1"),
            _make_result(
                test_id="fail-1",
                overall_score=0.0,
                aoi_id_match_score=0.0,
                expected_aoi_ids=["x"],
                actual_id="y",
            ),
        ],
    )

    out = capsys.readouterr().out
    assert "RESULTS (2 tests)" in out
    assert "Summary: 1 passed, 1 failed" in out
    assert "Mean overall score:" in out
    assert "[PASS] pass-1" in out
    assert "[FAIL] fail-1" in out
