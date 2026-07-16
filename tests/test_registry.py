"""Tests for the evaluator registry, toggles and staged-gate scoring.

Usage:
    $ uv run pytest tests/test_registry.py -v
"""

import pytest
from fixtures.agent_states import BRAZIL_TCL_2020_2023

from gnw_evals.evaluators.chart_type_evaluator import evaluate_chart_type
from gnw_evals.evaluators.data_pull_evaluator import evaluate_date_selection
from gnw_evals.evaluators.dataset_evaluator import evaluate_dataset_selection
from gnw_evals.evaluators.registry import (
    EVALUATOR_NAMES,
    EVALUATORS,
    SCORE_FIELD_BUCKETS,
    compute_stage_scores,
    resolve_case_evaluators,
    resolve_enabled,
)
from gnw_evals.runners.api import APITestRunner
from gnw_evals.utils.eval_types import ExpectedData, TestResult


def _runner(enabled: frozenset[str] | None = None) -> APITestRunner:
    return APITestRunner("http://localhost:9", enabled_evaluators=enabled)


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------


class TestRegistryShape:
    def test_every_gate_field_is_a_test_result_field(self):
        """Every bucket-mapped score field must exist on TestResult."""
        for field in SCORE_FIELD_BUCKETS:
            assert field in TestResult.model_fields, field

    def test_every_spec_score_field_is_bucket_mapped(self):
        """Every score field an evaluator emits must have a bucket."""
        for spec in EVALUATORS:
            for field in spec.score_fields:
                assert field in SCORE_FIELD_BUCKETS, f"{spec.name}: {field}"

    def test_evaluator_names_unique(self):
        names = [spec.name for spec in EVALUATORS]
        assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# Staged gate maths
# ---------------------------------------------------------------------------


class TestComputeStageScores:
    def test_all_pass(self):
        stages = compute_stage_scores(
            {
                "aoi_id_match_score": 1.0,
                "dataset_id_match_score": 1.0,
                "data_pull_exists_score": 1.0,
                "agent_answer_score": 1.0,
            },
        )
        assert stages == {
            "retrieval_score": 1.0,
            "analysis_score": 1.0,
            "explanation_score": 1.0,
            "e2e_score": 1.0,
        }

    def test_retrieval_failure_gates_downstream(self):
        stages = compute_stage_scores(
            {
                "aoi_id_match_score": 0.0,
                "dataset_id_match_score": 1.0,
                "data_pull_exists_score": 1.0,
                "agent_answer_score": 1.0,
            },
        )
        assert stages["retrieval_score"] == 0.0
        assert stages["analysis_score"] is None
        assert stages["explanation_score"] is None
        assert stages["e2e_score"] == 0.0

    def test_analysis_failure_gates_explanation(self):
        stages = compute_stage_scores(
            {
                "aoi_id_match_score": 1.0,
                "data_fidelity_score": 0.0,
                "number_usage_score": 1.0,
            },
        )
        assert stages["retrieval_score"] == 1.0
        assert stages["analysis_score"] == 0.0
        assert stages["explanation_score"] is None
        assert stages["e2e_score"] == 0.0

    def test_explanation_failure_fails_e2e(self):
        stages = compute_stage_scores(
            {
                "aoi_id_match_score": 1.0,
                "data_pull_exists_score": 1.0,
                "number_usage_score": 0.0,
            },
        )
        assert stages["explanation_score"] == 0.0
        assert stages["e2e_score"] == 0.0

    def test_correct_deferral_passes_end_to_end(self):
        """A clarification/guardrail case ends at retrieval as a full pass."""
        stages = compute_stage_scores({"clarification_requested_score": 1.0})
        assert stages == {
            "retrieval_score": 1.0,
            "analysis_score": None,
            "explanation_score": None,
            "e2e_score": 1.0,
        }

    def test_inapplicable_analysis_does_not_block_explanation(self):
        stages = compute_stage_scores(
            {
                "aoi_id_match_score": 1.0,
                "agent_answer_score": 1.0,
            },
        )
        assert stages["analysis_score"] is None
        assert stages["explanation_score"] == 1.0
        assert stages["e2e_score"] == 1.0

    def test_nothing_applicable(self):
        stages = compute_stage_scores({})
        assert stages == {
            "retrieval_score": None,
            "analysis_score": None,
            "explanation_score": None,
            "e2e_score": None,
        }

    def test_none_scores_are_ignored(self):
        stages = compute_stage_scores(
            {
                "aoi_id_match_score": 1.0,
                "dataset_parameter_match_score": None,
                "data_pull_exists_score": None,
            },
        )
        assert stages["retrieval_score"] == 1.0
        assert stages["analysis_score"] is None


# ---------------------------------------------------------------------------
# Toggles
# ---------------------------------------------------------------------------


class TestToggles:
    def test_no_toggles_means_all(self):
        assert resolve_enabled(None, None) is None

    def test_only_list(self):
        assert resolve_enabled("aoi,dataset", None) == frozenset({"aoi", "dataset"})

    def test_skip_list(self):
        enabled = resolve_enabled(None, "ground_truth")
        assert enabled == EVALUATOR_NAMES - {"ground_truth"}

    def test_only_then_skip(self):
        enabled = resolve_enabled("aoi,dataset,date", "date")
        assert enabled == frozenset({"aoi", "dataset"})

    def test_unknown_name_fails_loudly(self):
        with pytest.raises(ValueError, match="unknown evaluator"):
            resolve_enabled("aoi,not_an_evaluator", None)
        with pytest.raises(ValueError, match="unknown evaluator"):
            resolve_enabled(None, "nope")

    def test_case_column_intersects_run_level(self):
        expected = ExpectedData(evaluators="dataset;date")
        assert resolve_case_evaluators(None, expected) == frozenset(
            {"dataset", "date"},
        )
        assert resolve_case_evaluators(frozenset({"dataset"}), expected) == frozenset(
            {"dataset"},
        )

    def test_case_column_empty_means_run_level(self):
        expected = ExpectedData()
        assert resolve_case_evaluators(None, expected) == EVALUATOR_NAMES

    def test_case_column_unknown_name_fails_loudly(self):
        expected = ExpectedData(evaluators="bogus", test_id="case-1")
        with pytest.raises(ValueError, match="case-1"):
            resolve_case_evaluators(None, expected)


# ---------------------------------------------------------------------------
# Dispatch regression against a fixture state (deterministic evaluators only)
# ---------------------------------------------------------------------------


class TestDispatchRegression:
    """The registry must reproduce exactly what direct evaluator calls return."""

    EXPECTED = ExpectedData(
        expected_dataset_id="4",
        expected_start_date="2020-01-01",
        expected_end_date="2023-12-31",
        expected_chart_type="bar",
    )

    def test_merged_results_match_direct_calls(self):
        evaluations = _runner()._run_evaluations(
            BRAZIL_TCL_2020_2023,
            self.EXPECTED,
            query="How much tree cover loss in Brazil 2020-2023?",
        )

        direct_dataset = evaluate_dataset_selection(
            BRAZIL_TCL_2020_2023,
            "4",
            "",
            "",
        )
        direct_date = evaluate_date_selection(
            BRAZIL_TCL_2020_2023,
            expected_start_date="2020-01-01",
            expected_end_date="2023-12-31",
        )
        direct_chart = evaluate_chart_type(BRAZIL_TCL_2020_2023, "bar")

        for key, value in {**direct_dataset, **direct_date, **direct_chart}.items():
            assert evaluations[key] == value, key

    def test_stage_scores_for_passing_case(self):
        evaluations = _runner()._run_evaluations(
            BRAZIL_TCL_2020_2023,
            self.EXPECTED,
            query="How much tree cover loss in Brazil 2020-2023?",
        )
        assert evaluations["retrieval_score"] == 1.0
        # No expected_answer/intent, so no analysis checks apply.
        assert evaluations["analysis_score"] is None
        assert evaluations["explanation_score"] == 1.0
        assert evaluations["e2e_score"] == 1.0

    def test_disabled_evaluators_leave_no_keys(self):
        evaluations = _runner(frozenset({"dataset"}))._run_evaluations(
            BRAZIL_TCL_2020_2023,
            self.EXPECTED,
        )
        assert "dataset_id_match_score" in evaluations
        assert "date_match_score" not in evaluations
        assert "chart_type_match_score" not in evaluations

    def test_per_case_toggle_restricts_evaluators(self):
        expected = self.EXPECTED.model_copy(update={"evaluators": "date"})
        evaluations = _runner()._run_evaluations(
            BRAZIL_TCL_2020_2023,
            expected,
        )
        assert "date_match_score" in evaluations
        assert "dataset_id_match_score" not in evaluations

    def test_correct_deferral_via_dispatch(self):
        """expected_clarification=False with empty query skips the judge and passes."""
        expected = ExpectedData(expected_clarification=False)
        evaluations = _runner(frozenset({"clarification"}))._run_evaluations(
            BRAZIL_TCL_2020_2023,
            expected,
            query="",
        )
        assert evaluations["clarification_requested_score"] == 1.0
        assert evaluations["retrieval_score"] == 1.0
        assert evaluations["e2e_score"] == 1.0


# ---------------------------------------------------------------------------
# Legacy overall_score is unchanged by the refactor
# ---------------------------------------------------------------------------


class TestLegacyOverallScore:
    def test_gold_style_case_mean_unchanged(self):
        """A typical gold row: aoi + dataset + answer checks, one failure."""
        expected = ExpectedData(
            expected_aoi_ids=["BRA"],
            expected_dataset_id="4",
            expected_answer="some expected answer",
        )
        evaluations = {
            "aoi_id_match_score": 1.0,
            "dataset_id_match_score": 1.0,
            "data_pull_exists_score": 1.0,
            "charts_answer_score": 0.0,
            "agent_answer_score": 1.0,
        }
        # Old formula: mean of [aoi, dataset, data_pull, charts, agent]
        score = _runner()._calculate_overall_score(evaluations, expected)
        assert score == round(4 / 5, 2)

    def test_new_checks_only_count_when_expected(self):
        """chart_type/parameter checks join the mean only when the case sets them."""
        expected = ExpectedData(expected_dataset_id="4")
        evaluations = {
            "dataset_id_match_score": 1.0,
            "chart_type_match_score": 0.0,  # present but not expected -> ignored
        }
        assert _runner()._calculate_overall_score(evaluations, expected) == 1.0

        expected_with_chart = ExpectedData(
            expected_dataset_id="4",
            expected_chart_type="bar",
        )
        assert (
            _runner()._calculate_overall_score(evaluations, expected_with_chart) == 0.5
        )

    def test_error_result_has_e2e_zero(self):
        result = _runner()._create_empty_evaluation_result(
            thread_id="t",
            trace_url="",
            app_thread_url=None,
            query="q",
            expected_data=ExpectedData(expected_dataset_id="4"),
            error="boom",
        )
        assert result.e2e_score == 0.0
        assert result.retrieval_score is None
