"""Unit tests for new evaluators: chart_type, parameter, insight_quality, language.

Usage
$ uv run pytest tests/test_new_evaluators.py -v
"""

from unittest.mock import MagicMock, patch

from gnw_evals.evaluators.chart_type_evaluator import evaluate_chart_type
from gnw_evals.evaluators.insight_quality_evaluator import evaluate_insight_quality
from gnw_evals.evaluators.language_evaluator import evaluate_language
from gnw_evals.evaluators.parameter_evaluator import evaluate_parameters

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state_with_chart(chart_type: str, insight: str = "Some insight.") -> dict:
    """Build a minimal agent state containing a single chart."""
    return {
        "charts_data": [
            {
                "type": chart_type,
                "insight": insight,
                "data": [{"row": 1}, {"row": 2}],
            },
        ],
        "dataset": {"dataset_id": "4", "context_layer": ""},
        "messages": [],
    }


def _state_with_params(
    canopy_density: str = "",
    forest_filter: str = "",
    context_layer: str = "",
    insight: str = "Some insight.",
) -> dict:
    """Build a minimal agent state with parameter fields."""
    return {
        "canopy_density": canopy_density,
        "forest_filter": forest_filter,
        "charts_data": [{"type": "bar", "insight": insight, "data": []}],
        "dataset": {
            "dataset_id": "4",
            "context_layer": context_layer,
        },
        "messages": [],
    }


# ---------------------------------------------------------------------------
# chart_type_evaluator
# ---------------------------------------------------------------------------


class TestChartTypeEvaluator:
    """Tests for evaluate_chart_type."""

    def test_exact_match(self):
        """Single expected type that matches exactly returns 1.0."""
        state = _state_with_chart("line")
        result = evaluate_chart_type(state, "line")
        assert result["chart_type_match_score"] == 1.0
        assert result["actual_chart_type"] == "line"

    def test_multiple_valid_first_option(self):
        """First option in a semicolon-separated list matches."""
        state = _state_with_chart("pie")
        result = evaluate_chart_type(state, "pie;bar")
        assert result["chart_type_match_score"] == 1.0

    def test_multiple_valid_second_option(self):
        """Second option in a semicolon-separated list matches."""
        state = _state_with_chart("bar")
        result = evaluate_chart_type(state, "pie;bar")
        assert result["chart_type_match_score"] == 1.0

    def test_mismatch(self):
        """Chart type not in valid list returns 0.0."""
        state = _state_with_chart("line")
        result = evaluate_chart_type(state, "pie;bar")
        assert result["chart_type_match_score"] == 0.0

    def test_missing_expected_returns_none(self):
        """Empty expected_chart_type returns None (not applicable)."""
        state = _state_with_chart("line")
        result = evaluate_chart_type(state, "")
        assert result["chart_type_match_score"] is None

    def test_no_charts_data_returns_zero(self):
        """No charts data when a chart type is expected returns 0.0."""
        state = {"charts_data": [], "dataset": {}, "messages": []}
        result = evaluate_chart_type(state, "line")
        assert result["chart_type_match_score"] == 0.0
        assert result["actual_chart_type"] is None

    def test_case_insensitive(self):
        """Comparison is case-insensitive."""
        state = _state_with_chart("Stacked-Bar")
        result = evaluate_chart_type(state, "stacked-bar")
        assert result["chart_type_match_score"] == 1.0


# ---------------------------------------------------------------------------
# parameter_evaluator — canopy cover
# ---------------------------------------------------------------------------


class TestCanopyCover:
    """Tests for canopy cover evaluation within evaluate_parameters."""

    def test_match(self):
        """Correct canopy density threshold returns 1.0."""
        state = _state_with_params(canopy_density="30")
        result = evaluate_parameters(state, expected_canopy_cover="30")
        assert result["canopy_cover_match_score"] == 1.0
        assert result["actual_canopy_cover"] == "30"

    def test_mismatch(self):
        """Wrong canopy density threshold returns 0.0."""
        state = _state_with_params(canopy_density="30")
        result = evaluate_parameters(state, expected_canopy_cover="50")
        assert result["canopy_cover_match_score"] == 0.0

    def test_missing_expected_returns_none(self):
        """Empty expected_canopy_cover returns None (not applicable)."""
        state = _state_with_params(canopy_density="30")
        result = evaluate_parameters(state, expected_canopy_cover="")
        assert result["canopy_cover_match_score"] is None

    def test_missing_actual_returns_zero(self):
        """No canopy density in state when expected returns 0.0."""
        state = _state_with_params(canopy_density="")
        result = evaluate_parameters(state, expected_canopy_cover="30")
        assert result["canopy_cover_match_score"] == 0.0


# ---------------------------------------------------------------------------
# parameter_evaluator — forest filter
# ---------------------------------------------------------------------------


class TestForestFilter:
    """Tests for forest filter evaluation within evaluate_parameters."""

    def test_primary_forest_match(self):
        """primary_forest filter applied correctly returns 1.0."""
        state = _state_with_params(forest_filter="primary_forest")
        result = evaluate_parameters(state, expected_forest_filter="primary_forest")
        assert result["forest_filter_match_score"] == 1.0

    def test_ifl_match(self):
        """intact_forest_landscape filter applied correctly returns 1.0."""
        state = _state_with_params(forest_filter="intact_forest_landscape")
        result = evaluate_parameters(
            state, expected_forest_filter="intact_forest_landscape",
        )
        assert result["forest_filter_match_score"] == 1.0

    def test_no_filter_when_not_specified(self):
        """No expected forest filter returns None (not applicable)."""
        state = _state_with_params(forest_filter="")
        result = evaluate_parameters(state, expected_forest_filter="")
        assert result["forest_filter_match_score"] is None

    def test_mismatch(self):
        """Wrong forest filter applied returns 0.0."""
        state = _state_with_params(forest_filter="primary_forest")
        result = evaluate_parameters(
            state, expected_forest_filter="intact_forest_landscape",
        )
        assert result["forest_filter_match_score"] == 0.0


# ---------------------------------------------------------------------------
# parameter_evaluator — intersections
# ---------------------------------------------------------------------------


class TestIntersections:
    """Tests for intersection / context layer evaluation within evaluate_parameters."""

    def test_driver_match(self):
        """Driver intersection applied correctly returns 1.0."""
        state = _state_with_params(context_layer="driver")
        result = evaluate_parameters(state, expected_intersections="driver")
        assert result["intersections_match_score"] == 1.0
        assert result["actual_intersections"] == "driver"

    def test_natural_lands_match(self):
        """natural_lands intersection applied correctly returns 1.0."""
        state = _state_with_params(context_layer="natural_lands")
        result = evaluate_parameters(state, expected_intersections="natural_lands")
        assert result["intersections_match_score"] == 1.0

    def test_missing_expected_returns_none(self):
        """Empty expected_intersections returns None (not applicable)."""
        state = _state_with_params(context_layer="driver")
        result = evaluate_parameters(state, expected_intersections="")
        assert result["intersections_match_score"] is None

    def test_mismatch(self):
        """Wrong intersection applied returns 0.0."""
        state = _state_with_params(context_layer="grasslands")
        result = evaluate_parameters(state, expected_intersections="driver")
        assert result["intersections_match_score"] == 0.0


# ---------------------------------------------------------------------------
# parameter_evaluator — crop types (LLM-judged)
# ---------------------------------------------------------------------------


class TestCropTypes:
    """Tests for crop type evaluation (LLM-judged) within evaluate_parameters."""

    def test_crop_match(self):
        """Insight mentions expected crop returns 1.0 from LLM judge."""
        state = _state_with_params(
            insight="The emission factor for Soybean in Brazil is 3.2 tCO2e per tonne.",
        )
        with patch(
            "gnw_evals.evaluators.parameter_evaluator._llm_judge_focus",
            return_value=1.0,
        ):
            result = evaluate_parameters(
                state, expected_crop_types="Soybean", insight_text=state["charts_data"][0]["insight"],
            )
        assert result["crop_type_match_score"] == 1.0

    def test_missing_expected_returns_none(self):
        """Empty expected_crop_types returns None (not applicable)."""
        state = _state_with_params()
        result = evaluate_parameters(state, expected_crop_types="")
        assert result["crop_type_match_score"] is None


# ---------------------------------------------------------------------------
# parameter_evaluator — gas types (LLM-judged)
# ---------------------------------------------------------------------------


class TestGasTypes:
    """Tests for gas type evaluation (LLM-judged) within evaluate_parameters."""

    def test_gas_match(self):
        """Insight reports on expected gas type returns 1.0 from LLM judge."""
        state = _state_with_params(
            insight="CO2 emissions from soybean deforestation: 2.8 tCO2e per tonne.",
        )
        with patch(
            "gnw_evals.evaluators.parameter_evaluator._llm_judge_focus",
            return_value=1.0,
        ):
            result = evaluate_parameters(
                state, expected_gas_types="CO2", insight_text=state["charts_data"][0]["insight"],
            )
        assert result["gas_type_match_score"] == 1.0

    def test_missing_expected_returns_none(self):
        """Empty expected_gas_types returns None (not applicable)."""
        state = _state_with_params()
        result = evaluate_parameters(state, expected_gas_types="")
        assert result["gas_type_match_score"] is None


# ---------------------------------------------------------------------------
# insight_quality_evaluator
# ---------------------------------------------------------------------------


class TestInsightQualityEvaluator:
    """Tests for evaluate_insight_quality (LLM-as-judge for quality/compliance)."""

    def _make_state(self, insight: str, chart_type: str = "bar") -> dict:
        """Build a minimal state with a single chart."""
        return {
            "charts_data": [
                {"type": chart_type, "insight": insight, "data": [{"year": 2023, "area_ha": 1000}]},
            ],
            "messages": [],
        }

    def test_no_instruction_returns_none(self):
        """Empty judge_instruction returns None (not applicable)."""
        state = self._make_state("Brazil lost 1000 ha of tree cover in 2023.")
        result = evaluate_insight_quality(state, query="How much?", judge_instruction="")
        assert result["insight_quality_score"] is None
        assert result["insight_quality_explanation"] is None

    def test_no_charts_data_returns_none(self):
        """No charts data returns None even with a judge instruction."""
        state = {"charts_data": [], "messages": []}
        result = evaluate_insight_quality(
            state, query="How much?", judge_instruction="Check units.",
        )
        assert result["insight_quality_score"] is None

    def _patch_haiku(self, score: int, explanation: str = ""):
        """Return a context manager that patches HAIKU.with_structured_output().invoke."""
        mock_judgement = MagicMock()
        mock_judgement.score = score
        mock_judgement.explanation = explanation
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = mock_judgement
        mock_haiku = MagicMock()
        mock_haiku.with_structured_output.return_value = mock_structured
        return patch(
            "gnw_evals.evaluators.insight_quality_evaluator.HAIKU",
            mock_haiku,
        )

    def test_with_instruction_returns_score(self):
        """Judge instruction provided: returns LLM score and explanation."""
        state = self._make_state("Brazil lost 1,200 kha of tree cover in 2023.")
        with self._patch_haiku(score=1, explanation="Units are correct."):
            result = evaluate_insight_quality(
                state,
                query="How much tree cover loss in Brazil?",
                judge_instruction="Check values are in kha.",
            )
        assert result["insight_quality_score"] == 1.0
        assert "Units are correct" in result["insight_quality_explanation"]

    def test_terminology_check_fails(self):
        """Judge catches use of 'deforestation' when 'tree cover loss' is required."""
        state = self._make_state("Brazil suffered massive deforestation in 2023.")
        with self._patch_haiku(
            score=0, explanation="Used 'deforestation' instead of 'tree cover loss'.",
        ):
            result = evaluate_insight_quality(
                state,
                query="Show me deforestation in Brazil.",
                judge_instruction="Insight MUST use 'tree cover loss', not 'deforestation'.",
            )
        assert result["insight_quality_score"] == 0.0

    def test_caveat_check_fails(self):
        """Judge catches missing caveat about plantation cycles in gain insight."""
        state = self._make_state("Indonesia gained 500 kha of tree cover.")
        with self._patch_haiku(score=0, explanation="Missing caveat about plantation cycles."):
            result = evaluate_insight_quality(
                state,
                query="How much tree cover has Indonesia gained?",
                judge_instruction=(
                    "Must note gain includes plantation cycles and natural regrowth."
                ),
            )
        assert result["insight_quality_score"] == 0.0


# ---------------------------------------------------------------------------
# language_evaluator
# ---------------------------------------------------------------------------


class TestLanguageEvaluator:
    """Tests for evaluate_language (LLM-judged multilingual response check)."""

    def _state_with_response(self, insight: str, message: str = "") -> dict:
        """Build a state with a chart insight and optional final message."""
        state: dict = {
            "charts_data": [{"type": "bar", "insight": insight}],
            "messages": [],
        }
        if message:
            mock_msg = MagicMock()
            mock_msg.content = message
            state["messages"] = [mock_msg]
        return state

    def _patch_lang_haiku(self, score: int):
        """Return a context manager that patches HAIKU.with_structured_output().invoke."""
        mock_judgement = MagicMock()
        mock_judgement.score = score
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = mock_judgement
        mock_haiku = MagicMock()
        mock_haiku.with_structured_output.return_value = mock_structured
        return patch(
            "gnw_evals.evaluators.language_evaluator.HAIKU",
            mock_haiku,
        )

    def test_missing_expected_returns_none(self):
        """Empty expected_language returns None (not applicable)."""
        state = self._state_with_response("Some insight.")
        result = evaluate_language(state, "")
        assert result["language_match_score"] is None

    def test_spanish_match(self):
        """Spanish response when 'es' expected returns 1.0."""
        state = self._state_with_response(
            "Indonesia perdió 1.200 kha de cobertura arbórea en 2023.",
        )
        with self._patch_lang_haiku(1):
            result = evaluate_language(state, "es")
        assert result["language_match_score"] == 1.0

    def test_french_match(self):
        """French response when 'fr' expected returns 1.0."""
        state = self._state_with_response(
            "L'Indonésie a perdu 1 200 kha de couverture arborée en 2023.",
        )
        with self._patch_lang_haiku(1):
            result = evaluate_language(state, "fr")
        assert result["language_match_score"] == 1.0

    def test_chinese_match(self):
        """Mandarin Chinese response when 'zh' expected returns 1.0."""
        state = self._state_with_response("印度尼西亚在2023年损失了1200千公顷的树木覆盖。")
        with self._patch_lang_haiku(1):
            result = evaluate_language(state, "zh")
        assert result["language_match_score"] == 1.0

    def test_wrong_language_returns_zero(self):
        """English response when Spanish expected returns 0.0."""
        state = self._state_with_response(
            "Indonesia lost 1,200 kha of tree cover in 2023.",
        )
        with self._patch_lang_haiku(0):
            result = evaluate_language(state, "es")
        assert result["language_match_score"] == 0.0

    def test_english_technical_terms_acceptable(self):
        """French response that uses English dataset names should still pass."""
        state = self._state_with_response(
            "L'Indonésie a subi une importante perte de 'tree cover loss' en 2023.",
        )
        with self._patch_lang_haiku(1):
            result = evaluate_language(state, "fr")
        assert result["language_match_score"] == 1.0

    def test_no_response_returns_zero(self):
        """Empty agent state with language expected returns 0.0."""
        state = {"charts_data": [], "messages": []}
        result = evaluate_language(state, "pt")
        assert result["language_match_score"] == 0.0
