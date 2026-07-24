"""Tests for the run-summary artefact and scorecard rendering.

Usage:
    $ uv run pytest tests/test_run_summary.py -v
"""

import json

from gnw_evals.data_handlers.run_summary import (
    DATASET_SLUGS,
    METHODOLOGY_VERSION,
    build_run_summary,
    coverage_tier,
)
from gnw_evals.data_handlers.scorecard import render_scorecard
from gnw_evals.utils.eval_types import TestResult


def _result(**overrides) -> TestResult:
    base = {
        "thread_id": "t",
        "query": "q",
        "overall_score": 1.0,
        "execution_time": "2026-07-16T00:00:00",
        "test_id": overrides.pop("test_id", "case-1"),
        "intent": overrides.pop("intent", "quantification"),
        "expected_dataset_id": "4",
        "e2e_score": 1.0,
        "retrieval_score": 1.0,
        "analysis_score": 1.0,
        "explanation_score": 1.0,
    }
    base.update(overrides)
    return TestResult(**base)


class TestCoverageTier:
    def test_minimal_on_low_case_count(self):
        assert coverage_tier(5, 1.0, 1.0, 3) == "minimal"

    def test_minimal_on_low_surface(self):
        assert coverage_tier(50, 1.0, 0.3, 0) == "minimal"

    def test_partial(self):
        assert coverage_tier(30, 0.4, 0.57, 0) == "partial"

    def test_good(self):
        assert coverage_tier(30, 0.6, 0.75, 0) == "good"

    def test_comprehensive_needs_languages(self):
        assert coverage_tier(50, 0.9, 0.95, 0) == "good"
        assert coverage_tier(50, 0.9, 0.95, 2) == "comprehensive"


class TestBuildRunSummary:
    def test_groups_results_into_cells(self):
        results = [
            _result(test_id="a", intent="quantification"),
            _result(
                test_id="b",
                intent="quantification",
                e2e_score=0.0,
                retrieval_score=0.0,
                analysis_score=None,
                explanation_score=None,
            ),
            _result(test_id="c", intent="trend"),
        ]
        summary = build_run_summary(
            results,
            api_base_url="https://api.globalnaturewatch.org",
            ff=None,
            num_trials=1,
        )
        assert summary["environment"] == "prod"
        assert summary["agent_profile"] == "default"
        assert summary["methodology_version"] == METHODOLOGY_VERSION
        assert len(summary["cells"]) == 2

        quant = next(c for c in summary["cells"] if c["intent"] == "quantification")
        assert quant["n_cases"] == 2
        assert quant["quality"]["e2e_pass_rate"] == 0.5
        assert quant["quality"]["retrieval"] == 0.5
        # The failing case is gated: analysis has only the passing case.
        assert quant["quality"]["analysis"] == 1.0
        assert quant["coverage"]["tier"] in (
            "minimal",
            "partial",
            "good",
            "comprehensive",
        )

        failing = next(c for c in quant["cases"] if c["test_id"] == "b")
        assert failing["failed_stage"] == "retrieval"

    def test_non_intent_results_are_counted_not_celled(self):
        results = [
            _result(),
            TestResult(
                thread_id="t",
                query="gold row",
                overall_score=1.0,
                execution_time="now",
                intent="",
            ),
        ]
        summary = build_run_summary(
            results,
            api_base_url="http://localhost:8000",
            ff=None,
            num_trials=1,
        )
        assert summary["non_matrix_results"] == 1
        assert len(summary["cells"]) == 1

    def test_prompt_coverage_read_from_case_files(self):
        summary = build_run_summary(
            [_result()],
            api_base_url="https://api.staging.globalnaturewatch.org",
            ff="experimental",
            num_trials=3,
        )
        cell = summary["cells"][0]
        # The committed TCL quantification manifest is fully covered.
        assert cell["coverage"]["prompt"] == 1.0
        assert summary["agent_profile"] == "experimental"
        assert summary["num_trials"] == 3

    def test_summary_is_json_serialisable(self):
        summary = build_run_summary(
            [_result()],
            api_base_url="https://api.globalnaturewatch.org",
            ff=None,
            num_trials=1,
        )
        json.dumps(summary)


class TestScorecard:
    def _summary(
        self,
        e2e: float,
        methodology: str = METHODOLOGY_VERSION,
        intent: str = "quantification",
    ) -> dict:
        results = [
            _result(
                e2e_score=e2e,
                retrieval_score=e2e,
                analysis_score=None,
                explanation_score=None,
                intent=intent,
            ),
        ]
        summary = build_run_summary(
            results,
            api_base_url="https://api.globalnaturewatch.org",
            ff=None,
            num_trials=1,
        )
        summary["methodology_version"] = methodology
        return summary

    def test_renders_matrix_and_history(self):
        older = self._summary(0.5)
        older["timestamp"] = "2026-07-15T00:00:00+00:00"
        newer = self._summary(1.0)
        newer["timestamp"] = "2026-07-16T00:00:00+00:00"

        page = render_scorecard([older, newer])
        assert "tree_cover_loss" in page
        assert "100%" in page
        assert "+50%" in page  # delta vs previous run
        assert "quantification" in page

    def test_methodology_break_marks_no_delta(self):
        older = self._summary(0.5, methodology="1.0.0")
        older["timestamp"] = "2026-07-15T00:00:00+00:00"
        newer = self._summary(1.0, methodology="2.0.0")
        newer["timestamp"] = "2026-07-16T00:00:00+00:00"

        page = render_scorecard([older, newer])
        assert "methodology break" in page
        assert "+50%" not in page

    def test_matrix_merges_cells_across_runs(self):
        # Official runs cover one cell each; both must appear in the matrix.
        quant = self._summary(0.5, intent="quantification")
        quant["timestamp"] = "2026-07-15T00:00:00+00:00"
        trend = self._summary(1.0, intent="trend")
        trend["timestamp"] = "2026-07-16T00:00:00+00:00"

        page = render_scorecard([quant, trend])
        assert 'id="tree_cover_loss--quantification"' in page
        assert 'id="tree_cover_loss--trend"' in page

    def test_matrix_lists_every_catalog_dataset(self):
        page = render_scorecard([self._summary(1.0)])
        for slug in DATASET_SLUGS.values():
            assert slug in page
        assert "not yet" in page

    def test_matrix_includes_extra_rows_and_legend(self):
        page = render_scorecard([self._summary(1.0)])
        for surface in ("guardrails", "clarification", "cross-dataset"):
            assert surface in page
        assert "How to read this matrix" in page
        assert "surface coverage below 40%" in page  # minimal tier definition

    def test_evaluator_scores_tagged_with_gate_bucket(self):
        results = [
            _result(
                number_usage_score=0.5,  # explanation
                data_fidelity_score=1.0,  # analysis
                date_match_score=1.0,  # retrieval
            ),
        ]
        summary = build_run_summary(
            results,
            api_base_url="https://api.globalnaturewatch.org",
            ff=None,
            num_trials=1,
        )

        page = render_scorecard([summary])
        assert ">retrieval</span></td><td>date_match_score<" in page
        assert ">analysis</span></td><td>data_fidelity_score<" in page
        assert ">explanation</span></td><td>number_usage_score<" in page
        # Rows are ordered by gate stage, not alphabetically.
        assert (
            page.index("date_match_score")
            < page.index("data_fidelity_score")
            < page.index("number_usage_score")
        )

    def test_legacy_numeric_slug_normalised_to_catalog_slug(self):
        summary = self._summary(1.0)
        cell = summary["cells"][0]
        # Summaries written before the dataset joined DATASET_SLUGS carry
        # the raw id as slug; the scorecard must land them on the same row.
        cell["dataset_slug"] = "10"
        cell["dataset_id"] = "10"

        page = render_scorecard([summary])
        assert 'id="tree_cover_loss_from_fires--quantification"' in page
