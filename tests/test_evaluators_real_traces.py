"""Evaluator tests using real-structure agent state fixtures.

Fixtures are based on actual API trace structures from live runs.
LLM-judged evaluators are mocked; deterministic evaluators run against real state shape.

Usage:
    $ uv run pytest tests/test_evaluators_real_traces.py -v
"""

from unittest.mock import MagicMock, patch

from fixtures.agent_states import (
    BRAZIL_TCL_DRIVERS,
    EMPTY_STATE,
    INDONESIA_PRIMARY_FOREST,
    INDONESIA_SPANISH_TCL,
    INDONESIA_TCL_CANOPY_50,
    KALIMANTAN_DRIVER_INTERSECT,
    NIGERIA_AGRICULTURAL_LAND,
)

from gnw_evals.evaluators.chart_type_evaluator import evaluate_chart_type
from gnw_evals.evaluators.data_pull_evaluator import (
    evaluate_data_pull,
    evaluate_date_selection,
)
from gnw_evals.evaluators.insight_quality_evaluator import evaluate_insight_quality
from gnw_evals.evaluators.language_evaluator import evaluate_language
from gnw_evals.evaluators.parameter_evaluator import evaluate_parameters


def _mock_haiku(module_path: str, score: int, explanation: str = ""):
    """Return a context manager patching HAIKU.with_structured_output().invoke()."""
    mock_judgement = MagicMock()
    mock_judgement.score = score
    mock_judgement.explanation = explanation
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_judgement
    mock_haiku = MagicMock()
    mock_haiku.with_structured_output.return_value = mock_structured
    return patch(module_path, mock_haiku)


# ---------------------------------------------------------------------------
# data_pull_evaluator — real state structure
# ---------------------------------------------------------------------------


class TestDataPullRealState:
    """Tests for evaluate_data_pull using real agent state structure."""

    def test_nigeria_has_data(self):
        """Nigeria state with a source_url statistics entry scores 1.0."""
        result = evaluate_data_pull(NIGERIA_AGRICULTURAL_LAND, expects_data_pull=True)
        assert result["data_pull_exists_score"] == 1.0
        assert result["data_pull_success"] is True

    def test_brazil_has_data(self):
        """Brazil state with a source_url statistics entry scores 1.0."""
        result = evaluate_data_pull(BRAZIL_TCL_DRIVERS, expects_data_pull=True)
        assert result["data_pull_exists_score"] == 1.0
        assert result["data_pull_success"] is True

    def test_indonesia_spanish_has_data(self):
        """Indonesia LANG state with a source_url statistics entry scores 1.0."""
        result = evaluate_data_pull(INDONESIA_SPANISH_TCL, expects_data_pull=True)
        assert result["data_pull_exists_score"] == 1.0
        assert result["data_pull_success"] is True

    def test_empty_state_scores_zero(self):
        """Empty charts_data scores 0.0."""
        result = evaluate_data_pull(EMPTY_STATE, expects_data_pull=True)
        assert result["data_pull_exists_score"] == 0.0
        assert result["row_count"] == 0

    def test_no_data_pull_expected_returns_none(self):
        """When the case does not require analytics data, the score is not applicable."""
        result = evaluate_data_pull(NIGERIA_AGRICULTURAL_LAND, expects_data_pull=False)
        assert result["data_pull_exists_score"] is None


# ---------------------------------------------------------------------------
# evaluate_date_selection — real state structure
# ---------------------------------------------------------------------------


class TestDateSelectionRealState:
    """Tests for evaluate_date_selection using real agent state structure."""

    def test_nigeria_no_expected_dates_returns_none(self):
        """No expected dates → None (not evaluated)."""
        result = evaluate_date_selection(NIGERIA_AGRICULTURAL_LAND)
        assert result["date_match_score"] is None
        assert result["actual_start_date"] == "2024-01-01"

    def test_brazil_date_range_matches(self):
        """Brazil start=2001, end=2024 matches expected range."""
        result = evaluate_date_selection(
            BRAZIL_TCL_DRIVERS,
            expected_start_date="2001-01-01",
            expected_end_date="2024-12-31",
        )
        assert result["date_match_score"] == 1.0

    def test_date_mismatch_scores_zero(self):
        """Wrong expected dates score 0.0."""
        result = evaluate_date_selection(
            BRAZIL_TCL_DRIVERS,
            expected_start_date="2010-01-01",
            expected_end_date="2024-12-31",
        )
        assert result["date_match_score"] == 0.0

    def test_empty_state_with_expected_dates_scores_zero(self):
        """Missing actual dates when expected → 0.0."""
        result = evaluate_date_selection(
            EMPTY_STATE,
            expected_start_date="2020-01-01",
            expected_end_date="2023-12-31",
        )
        assert result["date_match_score"] == 0.0


# ---------------------------------------------------------------------------
# evaluate_chart_type — real state structure
# ---------------------------------------------------------------------------


class TestChartTypeRealState:
    """Tests for evaluate_chart_type using real agent state structure."""

    def test_nigeria_pie_matches(self):
        """Nigeria returns pie chart; expected pie → 1.0."""
        result = evaluate_chart_type(NIGERIA_AGRICULTURAL_LAND, "pie")
        assert result["chart_type_match_score"] == 1.0
        assert result["actual_chart_type"] == "pie"

    def test_brazil_bar_matches(self):
        """Brazil returns bar chart; expected bar → 1.0."""
        result = evaluate_chart_type(BRAZIL_TCL_DRIVERS, "bar")
        assert result["chart_type_match_score"] == 1.0

    def test_brazil_bar_in_multi_option(self):
        """Bar is valid when expected is 'pie;bar'."""
        result = evaluate_chart_type(BRAZIL_TCL_DRIVERS, "pie;bar")
        assert result["chart_type_match_score"] == 1.0

    def test_indonesia_line_mismatch(self):
        """Indonesia returns line; expected bar → 0.0."""
        result = evaluate_chart_type(INDONESIA_SPANISH_TCL, "bar")
        assert result["chart_type_match_score"] == 0.0

    def test_no_expected_returns_none(self):
        """Empty expected_chart_type returns None."""
        result = evaluate_chart_type(NIGERIA_AGRICULTURAL_LAND, "")
        assert result["chart_type_match_score"] is None

    def test_empty_state_with_expected_scores_zero(self):
        """No charts_data when chart type is expected → 0.0."""
        result = evaluate_chart_type(EMPTY_STATE, "bar")
        assert result["chart_type_match_score"] == 0.0
        assert result["actual_chart_type"] is None


# ---------------------------------------------------------------------------
# evaluate_parameters — canopy cover (real state)
# ---------------------------------------------------------------------------


class TestCanopyCoverRealState:
    """Tests for canopy cover evaluation using real agent state structure."""

    def test_canopy_50_matches(self):
        """State with canopy_density='50' matches expected '50'."""
        result = evaluate_parameters(
            INDONESIA_TCL_CANOPY_50,
            expected_canopy_cover="50",
        )
        assert result["canopy_cover_match_score"] == 1.0
        assert result["actual_canopy_cover"] == "50"

    def test_canopy_30_vs_50_mismatch(self):
        """State with canopy_density='30' when expected '50' → 0.0."""
        result = evaluate_parameters(
            INDONESIA_PRIMARY_FOREST,
            expected_canopy_cover="50",
        )
        assert result["canopy_cover_match_score"] == 0.0

    def test_no_expected_returns_none(self):
        """No expected canopy cover → None."""
        result = evaluate_parameters(INDONESIA_TCL_CANOPY_50, expected_canopy_cover="")
        assert result["canopy_cover_match_score"] is None

    def test_null_canopy_in_state_scores_zero(self):
        """State with canopy_density=None when cover expected → 0.0."""
        result = evaluate_parameters(
            NIGERIA_AGRICULTURAL_LAND,
            expected_canopy_cover="30",
        )
        assert result["canopy_cover_match_score"] == 0.0


# ---------------------------------------------------------------------------
# evaluate_parameters — forest filter (real state)
# ---------------------------------------------------------------------------


class TestForestFilterRealState:
    """Tests for forest filter evaluation using real agent state structure."""

    def test_primary_forest_matches(self):
        """State with forest_filter='primary_forest' matches."""
        result = evaluate_parameters(
            INDONESIA_PRIMARY_FOREST,
            expected_forest_filter="primary_forest",
        )
        assert result["forest_filter_match_score"] == 1.0
        assert result["actual_forest_filter"] == "primary_forest"

    def test_no_filter_when_primary_expected_scores_zero(self):
        """State with forest_filter=None when primary_forest expected → 0.0."""
        result = evaluate_parameters(
            BRAZIL_TCL_DRIVERS,
            expected_forest_filter="primary_forest",
        )
        assert result["forest_filter_match_score"] == 0.0

    def test_no_expected_returns_none(self):
        """No expected forest filter → None."""
        result = evaluate_parameters(
            INDONESIA_PRIMARY_FOREST,
            expected_forest_filter="",
        )
        assert result["forest_filter_match_score"] is None


# ---------------------------------------------------------------------------
# evaluate_parameters — intersections (real state)
# ---------------------------------------------------------------------------


class TestIntersectionsRealState:
    """Tests for intersection / context layer evaluation using real agent state structure."""

    def test_driver_intersection_matches(self):
        """State with context_layer='driver' matches expected 'driver'."""
        result = evaluate_parameters(
            KALIMANTAN_DRIVER_INTERSECT,
            expected_intersections="driver",
        )
        assert result["intersections_match_score"] == 1.0
        assert result["actual_intersections"] == "driver"

    def test_land_cover_vs_driver_mismatch(self):
        """State with context_layer='land_cover' when driver expected → 0.0."""
        result = evaluate_parameters(
            INDONESIA_SPANISH_TCL,
            expected_intersections="driver",
        )
        assert result["intersections_match_score"] == 0.0

    def test_null_context_layer_scores_zero(self):
        """State with context_layer=None when intersection expected → 0.0."""
        result = evaluate_parameters(
            NIGERIA_AGRICULTURAL_LAND,
            expected_intersections="driver",
        )
        assert result["intersections_match_score"] == 0.0

    def test_no_expected_returns_none(self):
        """No expected intersections → None."""
        result = evaluate_parameters(
            KALIMANTAN_DRIVER_INTERSECT,
            expected_intersections="",
        )
        assert result["intersections_match_score"] is None


# ---------------------------------------------------------------------------
# evaluate_insight_quality — real insight text
# ---------------------------------------------------------------------------


class TestInsightQualityRealState:
    """Tests for evaluate_insight_quality using real insight text."""

    def test_nigeria_combine_instruction_pass(self):
        """Nigeria insight combines cropland+cultivated grassland → judge passes."""
        with _mock_haiku(
            "gnw_evals.evaluators.insight_quality_evaluator.HAIKU",
            score=1,
            explanation="Correctly combines Cropland (37,168,536 ha) and Cultivated grassland (4,012,000 ha).",
        ):
            result = evaluate_insight_quality(
                NIGERIA_AGRICULTURAL_LAND,
                query="How much agricultural land does Nigeria have in 2024?",
                judge_instruction=(
                    'The agent MUST combine "cropland" AND "cultivated grassland" into a single '
                    '"Agriculture" category. Score 1 only if both are summed.'
                ),
            )
        assert result["insight_quality_score"] == 1.0
        assert "Cropland" in result["insight_quality_explanation"]

    def test_brazil_insight_fails_interp_check(self):
        """Brazil insight fails interpretation instruction."""
        with _mock_haiku(
            "gnw_evals.evaluators.insight_quality_evaluator.HAIKU",
            score=0,
            explanation="Insight does not include percentage context for each driver class.",
        ):
            result = evaluate_insight_quality(
                BRAZIL_TCL_DRIVERS,
                query="How much tree cover has Brazil lost since 2001?",
                judge_instruction="Each driver class must include both absolute ha and % of total.",
            )
        assert result["insight_quality_score"] == 0.0

    def test_no_judge_instruction_returns_none(self):
        """Empty judge_instruction → None (not applicable)."""
        result = evaluate_insight_quality(
            NIGERIA_AGRICULTURAL_LAND,
            query="How much agricultural land does Nigeria have?",
            judge_instruction="",
        )
        assert result["insight_quality_score"] is None
        assert result["insight_quality_explanation"] is None

    def test_empty_state_returns_none(self):
        """No charts_data → None even with a judge instruction."""
        result = evaluate_insight_quality(
            EMPTY_STATE,
            query="Some query",
            judge_instruction="Check units.",
        )
        assert result["insight_quality_score"] is None

    def test_insight_term_kalimantan(self):
        """Kalimantan insight uses 'tree cover loss' not 'deforestation' → passes term check."""
        state = {
            "charts_data": [
                {
                    "type": "bar",
                    "insight": (
                        "From 2015 to 2023, Kalimantan experienced approximately 4.2 million "
                        "hectares of tree cover loss. The dominant driver was permanent "
                        "agriculture at 52%."
                    ),
                    "data": [{"year": y, "area_ha": 450000} for y in range(2015, 2024)],
                },
            ],
            "messages": [],
        }
        with _mock_haiku(
            "gnw_evals.evaluators.insight_quality_evaluator.HAIKU",
            score=1,
            explanation="Insight correctly uses 'tree cover loss' throughout.",
        ):
            result = evaluate_insight_quality(
                state,
                query="Show me deforestation in Kalimantan from 2015 to 2023",
                judge_instruction=(
                    "Even though the user says 'deforestation' the agent's insight text MUST "
                    "use 'tree cover loss' in its narrative. Score 0 if 'deforestation' appears."
                ),
            )
        assert result["insight_quality_score"] == 1.0


# ---------------------------------------------------------------------------
# evaluate_language — real Spanish insight
# ---------------------------------------------------------------------------


class TestLanguageRealState:
    """Tests for evaluate_language using real Spanish insight text."""

    def test_indonesia_spanish_insight_passes(self):
        """Spanish insight when 'es' expected → 1.0."""
        with _mock_haiku("gnw_evals.evaluators.language_evaluator.HAIKU", score=1):
            result = evaluate_language(INDONESIA_SPANISH_TCL, "es")
        assert result["language_match_score"] == 1.0

    def test_english_insight_fails_spanish_check(self):
        """English insight when 'es' expected → 0.0."""
        with _mock_haiku("gnw_evals.evaluators.language_evaluator.HAIKU", score=0):
            result = evaluate_language(BRAZIL_TCL_DRIVERS, "es")
        assert result["language_match_score"] == 0.0

    def test_no_expected_language_returns_none(self):
        """Empty expected_language → None."""
        result = evaluate_language(INDONESIA_SPANISH_TCL, "")
        assert result["language_match_score"] is None

    def test_empty_state_with_expected_language_scores_zero(self):
        """No charts_data when language expected → 0.0."""
        result = evaluate_language(EMPTY_STATE, "es")
        assert result["language_match_score"] == 0.0
