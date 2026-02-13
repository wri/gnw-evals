"""Result export functionality for E2E testing framework."""

import csv
from datetime import datetime
from pathlib import Path

from gnw_evals.utils.eval_types import TestResult


class ResultExporter:
    """Handles exporting test results to CSV files."""

    @staticmethod
    def save_results_to_csv(
        results: list[TestResult],
        filename: str | None = None,
    ) -> str:
        """Save test results to two CSV files: summary and detailed.

        Args:
            results: List of test results
            filename: Base filename (optional)

        Returns:
            Path to summary CSV file

        """
        if not results:
            return ""

        # Always append timestamp to filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not filename:
            base_filename = f"simple_e2e_{timestamp}"
        else:
            # Remove .csv extension if present and append timestamp
            clean_filename = filename.replace(".csv", "")
            base_filename = f"{clean_filename}_{timestamp}"

        output_dir = Path(__file__).parent.parent.parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)

        # 1. Summary CSV - just query and scores
        summary_fields = [
            "query",
            "overall_score",
            "aoi_id_match_score",
            "subregion_match_score",
            "dataset_id_match_score",
            "context_layer_match_score",
            "data_pull_exists_score",
            "date_match_score",
            "charts_answer_score",
            "agent_answer_score",
            "clarification_requested_score",
            "execution_time",
            "error",
            "trace_url",
        ]

        summary_filename = f"{base_filename}_summary.csv"
        with open(
            output_dir / summary_filename,
            "w",
            newline="",
            encoding="utf-8",
        ) as f:
            writer = csv.DictWriter(f, fieldnames=summary_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows([result.to_dict() for result in results])

        # 2. Detailed CSV - expected vs actual side by side
        detailed_fields = [
            # Basic info
            "query",
            "thread_id",
            "trace_id",
            "trace_url",
            "overall_score",
            "execution_time",
            # AOI: Expected vs Actual
            "expected_aoi_ids",
            "actual_id",
            "aoi_id_match_score",
            "match_aoi_id",
            "actual_name",
            "expected_subregion",
            "actual_subregion",
            "subregion_match_score",
            "match_subregion",
            "actual_subtype",
            "expected_aoi_source",
            "actual_source",
            # Dataset: Expected vs Actual
            "expected_dataset_id",
            "actual_dataset_id",
            "dataset_id_match_score",
            "expected_dataset_name",
            "actual_dataset_name",
            "expected_context_layer",
            "actual_context_layer",
            "context_layer_match_score",
            # Data Pull: Expected vs Actual
            "expected_start_date",
            "actual_start_date",
            "data_pull_exists_score",
            "expected_end_date",
            "actual_end_date",
            "date_match_score",
            "row_count",
            "data_pull_success",
            "date_success",
            # Answer: Expected vs Actual
            "expected_answer",
            "actual_charts_answer",
            "charts_answer_score",
            "actual_agent_answer",
            "agent_answer_score",
            # Clarification: Expected vs Actual
            "expected_clarification",
            "clarification_requested_score",
            # Metadata
            "test_group",
            "error",
        ]

        detailed_filename = f"{base_filename}_detailed.csv"
        with open(
            output_dir / detailed_filename,
            "w",
            newline="",
            encoding="utf-8",
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=detailed_fields,
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows([result.to_dict() for result in results])

        print(f"Summary results saved to: {summary_filename}")
        print(f"Detailed results saved to: {detailed_filename}")
        return summary_filename
