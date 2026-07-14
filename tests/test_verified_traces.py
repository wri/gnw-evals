"""Evaluator tests verified against a real eval run.

Each test reproduces the exact scores reported by the eval run on 2026-03-27
(output: trace_fixture_run_20260327_093127_detailed.csv).

The fixture state for BRAZIL_TCL_2020_2023 was fetched directly from the API
immediately after the run (thread ad54c8ac-a6fd-4104-aad8-83a3f7a33fa4).

Eval run reported scores for that thread:
    dataset_id_match_score : 1.0  (act=4, exp=4)
    data_pull_exists_score : 1.0  (8 rows)
    date_match_score       : 1.0  (2020-01-01 / 2023-12-31)
    canopy_cover_match_score: 0.0  (act=None, exp=30)
    insight_quality_score  : 0.0  (insight reported wrong date range)

Usage:
    $ uv run pytest tests/test_verified_traces.py -v
"""

from unittest.mock import MagicMock, patch

from gnw_evals.evaluators.chart_type_evaluator import evaluate_chart_type
from gnw_evals.evaluators.data_pull_evaluator import evaluate_data_pull, evaluate_date_selection
from gnw_evals.evaluators.insight_quality_evaluator import evaluate_insight_quality
from gnw_evals.evaluators.parameter_evaluator import evaluate_parameters
from fixtures.agent_states import BRAZIL_TCL_2020_2023


def _mock_haiku_score(score: int, explanation: str = ""):
    """Patch HAIKU.with_structured_output().invoke() for insight quality evaluator."""
    mock_judgement = MagicMock()
    mock_judgement.score = score
    mock_judgement.explanation = explanation
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_judgement
    mock_haiku = MagicMock()
    mock_haiku.with_structured_output.return_value = mock_structured
    return patch("gnw_evals.evaluators.insight_quality_evaluator.HAIKU", mock_haiku)


JUDGE_INSTRUCTION = (
    "Check that the chart data and insight text report area in hectares (ha) or kha or Mha "
    "— NOT percentages or proportions. Emissions should be in MgCO2e and shown in a SEPARATE "
    "chart from area."
)


class TestBrazilTCL2020to2023VerifiedTrace:
    """Reproduces the exact evaluator scores from the real eval run for the Brazil INSIGHT-UNIT test.

    Thread: ad54c8ac-a6fd-4104-aad8-83a3f7a33fa4
    Run output: trace_fixture_run_20260327_093127
    """

    def test_dataset_id_scores_1(self):
        """Agent selected dataset_id=4, expected 4 → 1.0. Matches eval run."""
        from gnw_evals.evaluators.dataset_evaluator import evaluate_dataset_selection

        result = evaluate_dataset_selection(
            BRAZIL_TCL_2020_2023,
            expected_dataset_id="4",
            expected_context_layer="",
        )
        assert result["dataset_id_match_score"] == 1.0, (
            f"Expected 1.0, got {result['dataset_id_match_score']}. "
            f"Actual dataset_id={result.get('actual_dataset_id')}"
        )

    def test_data_pull_scores_1(self):
        """charts_data[0]['data'] has 8 rows → 1.0. Confirms data_pull fix uses charts_data."""
        result = evaluate_data_pull(BRAZIL_TCL_2020_2023)
        assert result["data_pull_exists_score"] == 1.0, (
            f"Expected 1.0, got {result['data_pull_exists_score']}. "
            f"row_count={result['row_count']}"
        )
        assert result["row_count"] == 8

    def test_date_match_scores_1(self):
        """start=2020-01-01, end=2023-12-31 both match expected → 1.0."""
        result = evaluate_date_selection(
            BRAZIL_TCL_2020_2023,
            expected_start_date="2020-01-01",
            expected_end_date="2023-12-31",
        )
        assert result["date_match_score"] == 1.0, (
            f"Expected 1.0, got {result['date_match_score']}. "
            f"actual={result['actual_start_date']}/{result['actual_end_date']}"
        )

    def test_canopy_cover_scores_0(self):
        """canopy_density=None in state, expected '30' → 0.0.

        The agent does NOT set canopy_density for the default 30% threshold —
        it only stores this field when the user explicitly overrides it.
        Eval run confirmed this scores 0.0.
        """
        result = evaluate_parameters(BRAZIL_TCL_2020_2023, expected_canopy_cover="30")
        assert result["canopy_cover_match_score"] == 0.0, (
            f"Expected 0.0, got {result['canopy_cover_match_score']}. "
            f"actual_canopy_cover={result['actual_canopy_cover']}"
        )
        assert result["actual_canopy_cover"] is None

    def test_insight_quality_scores_0_wrong_date_range(self):
        """Insight reports 2001-2024 but query asked for 2020-2023 → judge scores 0.

        The agent generated an insight with the wrong date range, which the
        judge should catch. Eval run confirmed insight_quality_score=0.0.
        """
        with _mock_haiku_score(
            score=0,
            explanation=(
                "Insight reports 'From 2001 to 2024' but the query requested 2020 to 2023. "
                "The date range in the insight does not match the selected period."
            ),
        ):
            result = evaluate_insight_quality(
                BRAZIL_TCL_2020_2023,
                query="How much tree cover loss occurred in Brazil from 2020 to 2023?",
                judge_instruction=JUDGE_INSTRUCTION,
            )
        assert result["insight_quality_score"] == 0.0

    def test_chart_type_is_bar(self):
        """Agent returned a bar chart — checking the actual type from state."""
        result = evaluate_chart_type(BRAZIL_TCL_2020_2023, "bar")
        assert result["chart_type_match_score"] == 1.0
        assert result["actual_chart_type"] == "bar"

    def test_context_layer_is_dataset_name_not_filter(self):
        """context_layer in state is 'Tree cover loss' (dataset name), not a real filter.

        This is a real quirk: the agent stores the dataset name in context_layer
        for non-intersection queries. Intersection evaluator should not match this.
        """
        result = evaluate_parameters(BRAZIL_TCL_2020_2023, expected_intersections="driver")
        assert result["intersections_match_score"] == 0.0, (
            "context_layer='Tree cover loss' should not match expected 'driver'"
        )

    def test_no_forest_filter_applied(self):
        """forest_filter=None in state when no filter expected → None (not applicable)."""
        result = evaluate_parameters(BRAZIL_TCL_2020_2023, expected_forest_filter="")
        assert result["forest_filter_match_score"] is None
