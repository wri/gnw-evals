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
            "eval_set",
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
            "guardrail_answer_score",
            "latency",
            "timed_out",
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
            "eval_set",
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
            "actual_clarification_requested",
            "clarification_requested_score",
            # Guardrail / metadata answer
            "expected_guardrail_answer",
            "actual_guardrail_answer",
            "guardrail_answer_score",
            # Metadata
            "test_group",
            "latency",
            "timed_out",
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

        # 3. Markdown report
        report_filename = f"{base_filename}_report.md"
        report_content = ResultExporter._generate_markdown_report(
            results, timestamp, summary_filename, detailed_filename
        )
        with open(output_dir / report_filename, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"Summary results saved to: {summary_filename}")
        print(f"Detailed results saved to: {detailed_filename}")
        print(f"Markdown report saved to:  {report_filename}")
        return summary_filename

    @staticmethod
    def _generate_markdown_report(
        results: list[TestResult],
        timestamp: str,
        summary_filename: str,
        detailed_filename: str,
    ) -> str:
        """Generate a markdown summary report from test results."""
        lines = []
        total = len(results)
        timed_out = sum(1 for r in results if r.timed_out)
        evaluated = [r for r in results if r.overall_score is not None]
        passed = sum(1 for r in evaluated if r.overall_score >= 0.7)

        ts_display = datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        lines.append(f"# GNW Eval Report — {ts_display}\n")

        # Run stats
        lines.append("## Run Summary\n")
        lines.append(f"- **Tests run:** {total}")
        if timed_out:
            lines.append(f"- **Timed out:** {timed_out}")
        if evaluated:
            lines.append(
                f"- **Pass rate (≥0.7):** {passed}/{len(evaluated)} "
                f"({passed / len(evaluated):.1%})"
            )
            if total - len(evaluated):
                lines.append(
                    f"- **No applicable metrics:** {total - len(evaluated)}"
                )
        lines.append("")

        # Metric scores table
        def _metric_row(label: str, field: str) -> str | None:
            scores = [
                getattr(r, field)
                for r in results
                if getattr(r, field, None) is not None
            ]
            if not scores:
                return None
            n_pass = sum(1 for s in scores if s == 1.0)
            rate = n_pass / len(scores)
            bar = "🟢" if rate >= 0.8 else ("🟡" if rate >= 0.5 else "🔴")
            return f"| {label} | {n_pass} / {len(scores)} | {rate:.2f} | {bar} |"

        lines.append("## Metric Scores\n")
        lines.append("| Metric | Passed / Total | Rate | |")
        lines.append("|--------|---------------|------|---|")
        metrics = [
            ("Agent Answer", "agent_answer_score"),
            ("AOI ID Match", "aoi_id_match_score"),
            ("Subregion Match", "subregion_match_score"),
            ("Dataset ID Match", "dataset_id_match_score"),
            ("Context Layer Match", "context_layer_match_score"),
            ("Data Pull Exists", "data_pull_exists_score"),
            ("Date Match", "date_match_score"),
            ("Charts Answer", "charts_answer_score"),
            ("Clarification Requested", "clarification_requested_score"),
            ("Guardrail Answer", "guardrail_answer_score"),
        ]
        for label, field in metrics:
            row = _metric_row(label, field)
            if row:
                lines.append(row)
        lines.append("")

        # Per-test table
        lines.append("## Per-Test Results\n")
        lines.append(
            "| Query | Score | Dataset | Data Pull | Dates | Answer | Guardrail | Latency | Status |"
        )
        lines.append(
            "|-------|-------|---------|-----------|-------|--------|-----------|---------|--------|"
        )

        def _fmt(val: float | None) -> str:
            if val is None:
                return "—"
            return "✅" if val == 1.0 else "❌"

        for r in results:
            query = (r.query or "")[:60].replace("|", "\\|")
            score = f"{r.overall_score:.2f}" if r.overall_score is not None else "—"
            status = "⏱ timeout" if r.timed_out else (r.error[:30] if r.error else "ok")
            latency = f"{r.latency:.0f}s" if r.latency is not None else "—"
            lines.append(
                f"| {query} | {score} | {_fmt(r.dataset_id_match_score)} "
                f"| {_fmt(r.data_pull_exists_score)} | {_fmt(r.date_match_score)} "
                f"| {_fmt(r.agent_answer_score)} | {_fmt(r.guardrail_answer_score)} "
                f"| {latency} | {status} |"
            )
        lines.append("")

        # File references
        lines.append("## Output Files\n")
        lines.append(f"- Summary CSV: `{summary_filename}`")
        lines.append(f"- Detailed CSV: `{detailed_filename}`")
        lines.append("")

        return "\n".join(lines)
