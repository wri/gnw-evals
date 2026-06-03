"""Base test runner interface for E2E testing framework."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from gnw_evals.evaluators import (
    evaluate_aoi_selection,
    evaluate_clarification,
    evaluate_data_pull,
    evaluate_dataset_selection,
    evaluate_date_selection,
    evaluate_final_answer,
    evaluate_suggested_datasets,
)
from gnw_evals.utils.eval_types import ExpectedData, TestResult


class BaseTestRunner(ABC):
    """Abstract base class for test runners."""

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
    ) -> dict[str, Any]:
        """Run all evaluation functions on agent state.

        Clarification is checked once at the beginning, then all other
        evaluations run independently regardless of clarification status.
        """
        # Check clarification ONCE centrally
        clarification_eval = evaluate_clarification(
            agent_state,
            expected_data.expected_clarification,
            query,
        )

        # Run all other evaluations (they no longer check for clarification)
        aoi_eval = evaluate_aoi_selection(
            agent_state,
            expected_data.expected_aoi_ids,
            query,
        )
        dataset_eval = evaluate_dataset_selection(
            agent_state,
            expected_data.expected_dataset_id,
            expected_data.expected_dataset_parameters,
            expected_data.expected_context_layer,
            query,
        )
        date_eval = evaluate_date_selection(
            agent_state,
            expected_start_date=expected_data.expected_start_date,
            expected_end_date=expected_data.expected_end_date,
        )
        data_eval = evaluate_data_pull(
            agent_state,
            expected_clarification=expected_data.expected_clarification,
            expected_answer=expected_data.expected_answer,
            query=query,
        )
        answer_eval = evaluate_final_answer(
            agent_state,
            expected_data.expected_answer,
            expected_data.expected_text,
            query,
        )
        suggested_datasets_eval = evaluate_suggested_datasets(
            agent_state,
            expected_data.expected_suggested_datasets,
        )

        return {
            **clarification_eval,
            **aoi_eval,
            **dataset_eval,
            **date_eval,
            **data_eval,
            **answer_eval,
            **suggested_datasets_eval,
        }

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
        if expected_data.expected_clarification:
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

        # Data pull checks
        if (
            expected_data.expected_dataset_id
        ):  # Data pull only relevant if dataset expected
            scores.append(evaluations.get("data_pull_exists_score"))
        if expected_data.expected_start_date and expected_data.expected_end_date:
            scores.append(evaluations.get("date_match_score"))

        # Suggested datasets check
        if expected_data.expected_suggested_datasets:
            scores.append(evaluations.get("suggested_datasets_match_score"))

        # Answer checks
        if expected_data.expected_answer:
            scores.append(evaluations.get("charts_answer_score"))
            scores.append(evaluations.get("agent_answer_score"))
        if expected_data.expected_text:
            scores.append(evaluations.get("expected_text_match_score"))

        # Filter out None values (checks that weren't applicable)
        valid_scores = [s for s in scores if s is not None]

        if not valid_scores:
            return 0.0

        return round(sum(valid_scores) / len(valid_scores), 2)
