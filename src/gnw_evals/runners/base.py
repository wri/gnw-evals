"""Base test runner interface for E2E testing framework."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from gnw_evals.evaluators.registry import (
    EVALUATORS,
    compute_stage_scores,
    resolve_case_evaluators,
)
from gnw_evals.utils.eval_types import ExpectedData, TestResult


class BaseTestRunner(ABC):
    """Abstract base class for test runners."""

    # Run-level evaluator toggle; None means all registered evaluators.
    enabled_evaluators: frozenset[str] | None = None

    @abstractmethod
    async def run_test(
        self,
        query: str,
        expected_data: ExpectedData,
    ) -> TestResult:
        """Run a single E2E test.

        Args:
            query: User query to test
            expected_data: Expected test results for evaluation

        Returns:
            TestResult with evaluation scores and metadata

        """
        pass

    def _create_empty_evaluation_result(
        self,
        thread_id: str,
        trace_url: str,
        app_thread_url: str | None,
        query: str,
        expected_data: ExpectedData,
        error: str,
    ) -> TestResult:
        """Create empty evaluation result for error cases."""
        kwargs = expected_data.to_dict()

        kwargs.pop("thread_id", None)
        kwargs.pop("trace_id", None)
        kwargs.pop("trace_url", None)
        kwargs.pop("query", None)
        kwargs.pop("overall_score", None)
        kwargs.pop("execution_time", None)

        return TestResult(
            thread_id=thread_id,
            app_thread_url=app_thread_url,
            trace_id=None,
            trace_url=trace_url,
            query=query,
            overall_score=0.0,
            execution_time=datetime.now().isoformat(),
            # AOI evaluation fields
            aoi_id_match_score=None,
            actual_id=None,
            actual_name=None,
            actual_subtype=None,
            actual_source=None,
            match_aoi_id=False,
            # Dataset evaluation fields
            dataset_id_match_score=None,
            dataset_parameter_match_score=None,
            context_layer_match_score=None,
            actual_dataset_id=None,
            actual_dataset_name=None,
            actual_dataset_parameters=None,
            actual_context_layer=None,
            # Data pull evaluation fields
            data_pull_exists_score=None,
            date_match_score=None,
            row_count=0,
            min_rows=1,
            data_pull_success=False,
            date_success=None,
            actual_start_date=None,
            actual_end_date=None,
            # Answer evaluation fields
            charts_answer_score=None,
            chart_answer_score_reason=None,
            agent_answer_score=None,
            agent_answer_score_reason=None,
            expected_text_match_score=None,
            expected_text_match_score_reason=None,
            actual_charts_answer=None,
            actual_charts_json=None,
            actual_agent_answer=None,
            # Clarification evaluation fields
            actual_clarification_requested=None,
            clarification_requested_score=None,
            # Suggested datasets evaluation fields
            suggested_datasets_match_score=None,
            actual_suggested_datasets=None,
            # Dashboard evaluation fields
            dashboard_created_score=None,
            actual_dashboard_created=None,
            actual_dashboard_id=None,
            dashboard_aoi_match_score=None,
            actual_dashboard_aoi_count=None,
            actual_dashboard_aoi_id=None,
            actual_dashboard_aoi_source=None,
            dashboard_widgets_match_score=None,
            actual_dashboard_widget_types=None,
            dashboard_widgets_valid_score=None,
            # Chart type / parameter evaluation fields
            chart_type_match_score=None,
            actual_chart_type=None,
            canopy_cover_match_score=None,
            forest_filter_match_score=None,
            intersections_match_score=None,
            actual_intersections=None,
            crop_type_match_score=None,
            gas_type_match_score=None,
            # Staged-gate fields: a run error is an end-to-end failure with
            # no stage evaluated.
            retrieval_score=None,
            analysis_score=None,
            explanation_score=None,
            e2e_score=0.0,
            # Expected data
            **kwargs,
            # Error
            error=error,
        )

    def _run_evaluations(
        self,
        agent_state: dict[str, Any],
        expected_data: ExpectedData,
        query: str = "",
        dashboard: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run enabled evaluators from the registry and merge their results.

        Registry order defines merge order (ground_truth last so its
        selected-parameter reporting wins for intent cases). Staged-gate
        bucket scores are derived from the merged per-check scores; gating
        never changes which evaluators run or their individual scores.
        """
        enabled = resolve_case_evaluators(self.enabled_evaluators, expected_data)

        evaluations: dict[str, Any] = {}
        for spec in EVALUATORS:
            if spec.name not in enabled:
                continue
            evaluations.update(spec.run(agent_state, expected_data, query, dashboard))

        evaluations.update(compute_stage_scores(evaluations))
        return evaluations

    def _calculate_overall_score(
        self,
        evaluations: dict[str, Any],
        expected_data: ExpectedData,
    ) -> float:
        """Calculate overall score from individual evaluation scores.

        Each check (AOI ID, dataset ID, context layer, data pull,
        date match, answer, clarification) is scored independently as 0 or 1.

        Only non-None scores are included in the average. A score of None
        means that check was not applicable (missing expected value).
        """
        scores = []

        # Clarification check
        if expected_data.expected_clarification is not None:
            scores.append(evaluations.get("clarification_requested_score"))

        # AOI checks
        if expected_data.expected_aoi_ids:
            scores.append(evaluations.get("aoi_id_match_score"))

        # Dataset checks
        if expected_data.expected_dataset_id:
            scores.append(evaluations.get("dataset_id_match_score"))
        if expected_data.expected_dataset_parameters:
            scores.append(evaluations.get("dataset_parameter_match_score"))
        if expected_data.expected_context_layer:
            scores.append(evaluations.get("context_layer_match_score"))

        # Data pull checks — only when the test expects an insight/answer
        if expected_data.expects_data_pull():
            scores.append(evaluations.get("data_pull_exists_score"))
        if expected_data.expected_start_date and expected_data.expected_end_date:
            scores.append(evaluations.get("date_match_score"))

        # Suggested datasets check
        if expected_data.expected_suggested_datasets:
            scores.append(evaluations.get("suggested_datasets_match_score"))

        # Dashboard checks
        # NOTE: uses `is not None` (not truthy) so expected_dashboard_created=False
        # guardrail rows are still included - a truthy check would silently drop them.
        if expected_data.expected_dashboard_created is not None:
            scores.append(evaluations.get("dashboard_created_score"))
        if expected_data.expected_dashboard_created and expected_data.expected_aoi_ids:
            scores.append(evaluations.get("dashboard_aoi_match_score"))
        if expected_data.expected_dashboard_widgets:
            scores.append(evaluations.get("dashboard_widgets_match_score"))
        if expected_data.expected_dashboard_created:
            scores.append(evaluations.get("dashboard_widgets_valid_score"))

        # Answer checks
        if expected_data.expected_answer:
            scores.append(evaluations.get("charts_answer_score"))
            scores.append(evaluations.get("agent_answer_score"))
        if expected_data.expected_text:
            scores.append(evaluations.get("expected_text_match_score"))

        # Chart type check
        if expected_data.expected_chart_type:
            scores.append(evaluations.get("chart_type_match_score"))

        # Parameter checks (canopy/filter/intersections deterministic,
        # crop/gas judged on the presented insight)
        if expected_data.expected_canopy_cover:
            scores.append(evaluations.get("canopy_cover_match_score"))
        if expected_data.expected_forest_filter:
            scores.append(evaluations.get("forest_filter_match_score"))
        if expected_data.expected_intersections:
            scores.append(evaluations.get("intersections_match_score"))
        if expected_data.expected_crop_types:
            scores.append(evaluations.get("crop_type_match_score"))
        if expected_data.expected_gas_types:
            scores.append(evaluations.get("gas_type_match_score"))

        # Ground-truth checks (intent cases with runtime-fetched ground truth)
        if expected_data.intent and expected_data.ground_truth:
            scores.append(evaluations.get("data_fidelity_score"))
            scores.append(evaluations.get("number_usage_score"))

        # Filter out None values (checks that weren't applicable)
        valid_scores = [s for s in scores if s is not None]

        if not valid_scores:
            return 0.0

        return round(sum(valid_scores) / len(valid_scores), 2)
