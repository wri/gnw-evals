"""Unit tests for the deterministic numeric tolerance check.

The 5% tolerance used to exist only as prose inside the judge prompt, so the model
both chose which numbers to compare and did the arithmetic. `_numeric_verdict` moves
the comparison into code; the model now only extracts.

Usage
$ uv run pytest tests/test_numeric_tolerance.py -v
"""

from gnw_evals.evaluators.llm_judges import NUMERIC_TOLERANCE, _numeric_verdict


def _score(expected, actual, same_quantity=True):
    verdict = _numeric_verdict(expected, actual, same_quantity)
    return None if verdict is None else verdict[0]


def test_tolerance_constant_is_five_percent():
    assert NUMERIC_TOLERANCE == 0.05


def test_exact_match_passes():
    assert _score(198.4, 198.4) == 1


def test_just_inside_tolerance_passes():
    # 0.20 vs 0.19 is exactly 5% - the documented boundary case, inclusive.
    assert _score(0.20, 0.19) == 1


def test_just_outside_tolerance_fails():
    assert _score(100.0, 105.001) == 0


def test_large_overshoot_fails():
    """Gold 1-034: 13,359.47 expected, 10,765.60 returned - a 19.4% gap."""
    score, explanation = _numeric_verdict(13359.47, 10765.60, True)
    assert score == 0
    assert "19.42%" in explanation
    assert "exceeding" in explanation


def test_direction_does_not_matter():
    assert _score(100.0, 96.0) == _score(100.0, 104.0) == 1


def test_negative_values_compare_on_magnitude():
    """Emissions answers are negative for a net sink (gold 1-054)."""
    assert _score(-286993.68, -290000.0) == 1
    assert _score(-286993.68, -2793765.0) == 0


def test_different_quantity_fails_however_close_the_numbers():
    """The failure the tolerance alone cannot express.

    Tree cover loss vs primary forest loss can land within 5% of each other and still
    be the wrong answer, so the quantity check gates the comparison.
    """
    score, explanation = _numeric_verdict(13359.47, 13400.0, same_quantity=False)
    assert score == 0
    assert "same quantity" in explanation


def test_same_quantity_unknown_is_treated_as_comparable():
    """None means the model did not judge it, which must not fail the row."""
    assert _score(100.0, 102.0, same_quantity=None) == 1


def test_missing_extraction_defers_to_the_model():
    assert _numeric_verdict(None, 100.0, True) is None
    assert _numeric_verdict(100.0, None, True) is None
    assert _numeric_verdict(None, None, True) is None


def test_zero_expected_defers_to_the_model():
    """A relative difference against zero is undefined."""
    assert _numeric_verdict(0.0, 0.0, True) is None
    assert _numeric_verdict(0.0, 5.0, True) is None


def test_explanation_states_the_comparison():
    _, explanation = _numeric_verdict(211.0, 220.0, True)
    assert "211" in explanation and "220" in explanation
    assert "4.27%" in explanation
    assert "within" in explanation
