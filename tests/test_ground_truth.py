"""Tests for the ground-truth eval mode (analytics client + two-stage evaluator).

No network or LLM calls: the judge path is only exercised up to its early
returns; fidelity and payload logic are pure functions.
"""

import pytest

from gnw_evals.data_handlers.html_reporter import write_html_report
from gnw_evals.evaluators.ground_truth_evaluator import (
    _derive_facts,
    _evaluate_data_fidelity,
    _evaluate_number_usage,
    _required_row_metrics,
    _selected_parameters,
    evaluate_ground_truth,
)
from gnw_evals.utils.analytics_client import (
    _columnar_to_rows,
    build_tcl_payload,
    resolve_x_environment,
)
from gnw_evals.utils.eval_types import ExpectedData, TestResult

GROUND_TRUTH = {
    "rows": [
        {
            "aoi_id": "BRA",
            "aoi_type": "admin",
            "tree_cover_loss_year": 2020,
            "area_ha": 3290646.41,
            "carbon_emissions_MgCO2e": 1686982574.26,
        },
        {
            "aoi_id": "BRA",
            "aoi_type": "admin",
            "tree_cover_loss_year": 2021,
            "area_ha": 2990029.08,
            "carbon_emissions_MgCO2e": 1873646286.96,
        },
    ],
    "metadata": {},
    "x_environment": "staging",
}


def _case(**overrides) -> ExpectedData:
    defaults = {
        "test_id": "gt-test",
        "intent": "quantification",
        "eval_subtype": "single_year",
        "expected_aoi_ids": "BRA",
        "expected_start_date": "2020-01-01",
        "expected_end_date": "2021-12-31",
        "expected_canopy_cover": "30",
    }
    defaults.update(overrides)
    return ExpectedData(**defaults)


class TestBuildTclPayload:
    def test_defaults_canopy_30_when_no_threshold_or_filter(self):
        payload = build_tcl_payload(_case(expected_canopy_cover=""))
        assert payload["canopy_cover"] == 30

    def test_full_payload(self):
        payload = build_tcl_payload(
            _case(
                expected_aoi_ids="BRA;IDN",
                expected_canopy_cover="75",
                expected_forest_filter="primary_forest",
                expected_intersections="driver",
            ),
        )
        assert payload == {
            "aoi": {"type": "admin", "ids": ["BRA", "IDN"]},
            "start_year": "2020",
            "end_year": "2021",
            "intersections": ["driver"],
            "canopy_cover": 75,
            "forest_filter": "primary_forest",
        }

    def test_missing_aoi_fails_loudly(self):
        with pytest.raises(ValueError, match="expected_aoi_ids"):
            build_tcl_payload(_case(expected_aoi_ids=""))

    def test_bad_dates_fail_loudly(self):
        with pytest.raises(ValueError, match="4-digit years"):
            build_tcl_payload(_case(expected_start_date="recently"))


class TestResolveXEnvironment:
    def test_staging_maps_to_staging(self):
        url = "https://api.staging.globalnaturewatch.org"
        assert resolve_x_environment(url) == "staging"

    def test_prod_maps_to_production(self):
        assert (
            resolve_x_environment("https://api.globalnaturewatch.org") == "production"
        )

    def test_override_wins(self, monkeypatch):
        monkeypatch.setenv("ANALYTICS_X_ENVIRONMENT", "staging")
        assert resolve_x_environment("http://localhost:8000") == "staging"


class TestColumnarToRows:
    def test_rows_sorted_by_aoi_then_year(self):
        result = {
            "__dtypes__": {"area_ha": "float"},
            "aoi_id": ["IDN", "BRA", "BRA"],
            "tree_cover_loss_year": [2020, 2021, 2020],
            "area_ha": [3.0, 2.0, 1.0],
        }
        rows = _columnar_to_rows(result)
        assert [(r["aoi_id"], r["tree_cover_loss_year"]) for r in rows] == [
            ("BRA", 2020),
            ("BRA", 2021),
            ("IDN", 2020),
        ]

    def test_empty_result(self):
        assert _columnar_to_rows({}) == []


class TestDataFidelity:
    def test_matching_chart_values_pass(self):
        agent_state = {
            "charts_data": [
                {
                    "data": [
                        {"year": 2020, "value": 3290646.41},
                        {"year": 2021, "value": 2990029.08},
                    ],
                },
            ],
        }
        result = _evaluate_data_fidelity(agent_state, GROUND_TRUTH)
        assert result["data_fidelity_score"] == 1.0
        assert result["data_fidelity_missing"] is None

    def test_within_relative_tolerance_passes(self):
        agent_state = {
            "charts_data": [
                {"data": [{"value": 3290646.41 * 1.0005}, {"value": 2990029.08}]},
            ],
        }
        result = _evaluate_data_fidelity(agent_state, GROUND_TRUTH)
        assert result["data_fidelity_score"] == 1.0

    def test_wrong_values_fail_with_detail(self):
        agent_state = {
            "charts_data": [
                # Values as if pulled at a different canopy threshold.
                {"data": [{"value": 2500000.0}, {"value": 2990029.08}]},
            ],
        }
        result = _evaluate_data_fidelity(agent_state, GROUND_TRUTH)
        assert result["data_fidelity_score"] == 0.0
        assert "BRA 2020" in result["data_fidelity_missing"]

    def test_no_pulled_data_fails(self):
        result = _evaluate_data_fidelity({"charts_data": []}, GROUND_TRUTH)
        assert result["data_fidelity_score"] == 0.0
        assert "no pulled data" in result["data_fidelity_missing"]

    def test_inline_statistics_data_counts(self):
        agent_state = {
            "statistics": [
                {"data": {"area_ha": [3290646.41, 2990029.08]}},
            ],
        }
        result = _evaluate_data_fidelity(agent_state, GROUND_TRUTH)
        assert result["data_fidelity_score"] == 1.0


class TestRequiredRowMetrics:
    def test_plain_row_requires_total_area(self):
        metrics = _required_row_metrics({"area_ha": 100.0})
        assert metrics == [("area_ha", 100.0)]

    def test_fire_row_requires_split_not_total(self):
        row = {
            "area_ha": 100.0,
            "tree_cover_loss_from_fires_area_ha": 30.0,
            "tree_cover_loss_non_fires_area_ha": 70.0,
        }
        metrics = _required_row_metrics(row)
        assert ("fires area_ha", 30.0) in metrics
        assert ("non-fires area_ha", 70.0) in metrics
        assert all(label != "area_ha" for label, _ in metrics)


class TestFireDataFidelity:
    def test_split_values_pass(self):
        ground_truth = {
            "rows": [
                {
                    "aoi_id": "IDN",
                    "tree_cover_loss_year": 2020,
                    "area_ha": 961584.80,
                    "tree_cover_loss_from_fires_area_ha": 79955.99,
                    "tree_cover_loss_non_fires_area_ha": 881628.80,
                },
            ],
        }
        agent_state = {
            "charts_data": [{"data": [{"fires": 79955.99, "other": 881628.80}]}],
        }
        result = _evaluate_data_fidelity(agent_state, ground_truth)
        assert result["data_fidelity_score"] == 1.0


class TestSelectedParameters:
    def test_reads_context_layer_and_override_canopy(self):
        state = {
            "dataset": {
                "context_layer": "primary_forest",
                "parameters": [{"name": "canopy_cover", "values": [75]}],
            },
        }
        assert _selected_parameters(state) == {
            "actual_canopy_cover": "75",
            "actual_forest_filter": "primary_forest",
        }

    def test_absent_canopy_reported_as_default(self):
        result = _selected_parameters({"dataset": {}})
        assert result["actual_canopy_cover"] == "30 (default)"
        assert result["actual_forest_filter"] is None

    def test_no_dataset_is_default_canopy_no_filter(self):
        result = _selected_parameters({})
        assert result["actual_canopy_cover"] == "30 (default)"
        assert result["actual_forest_filter"] is None


class TestDeriveFacts:
    def test_yearly_facts_include_peak_and_change(self):
        facts = _derive_facts(GROUND_TRUTH["rows"])
        assert "peak year = 2020" in facts
        assert "total area_ha over all rows = 6,280,675.49" in facts

    def test_two_aoi_comparison_fact(self):
        rows = [
            {"aoi_id": "BRA", "tree_cover_loss_year": 2023, "area_ha": 100.0},
            {"aoi_id": "IDN", "tree_cover_loss_year": 2023, "area_ha": 40.0},
        ]
        assert "comparison: BRA > IDN by 60.00 ha" in _derive_facts(rows)

    def test_driver_dominance_and_groupings(self):
        rows = [
            {"aoi_id": "BRA", "tree_cover_loss_driver": "Wildfire", "area_ha": 10.0},
            {
                "aoi_id": "BRA",
                "tree_cover_loss_driver": "Permanent agriculture",
                "area_ha": 90.0,
            },
            {
                "aoi_id": "BRA",
                "tree_cover_loss_driver": "Shifting cultivation",
                "area_ha": 20.0,
            },
            {"aoi_id": "BRA", "tree_cover_loss_driver": "Unknown", "area_ha": 30.0},
        ]
        facts = _derive_facts(rows)
        assert "dominant driver = Permanent agriculture" in facts
        # 90 / 150 total = 60%; 90 / 120 known = 75%
        assert "60.0% of total" in facts
        assert "75.0% excluding the Unknown class" in facts
        # groupings: deforestation proxy = 90 (perm ag only here)
        assert "all agriculture" in facts
        assert "110.00 ha" in facts  # permanent ag 90 + shifting 20

    def test_fire_totals_fact(self):
        rows = [
            {
                "aoi_id": "IDN",
                "tree_cover_loss_year": 2020,
                "area_ha": 100.0,
                "tree_cover_loss_from_fires_area_ha": 30.0,
                "tree_cover_loss_non_fires_area_ha": 70.0,
            },
        ]
        facts = _derive_facts(rows)
        assert "fire-driven loss total = 30.00 ha" in facts


class TestEvaluateGroundTruth:
    def test_no_intent_is_not_applicable(self):
        result = evaluate_ground_truth({}, ExpectedData(), query="q")
        assert result["data_fidelity_score"] is None
        assert result["number_usage_score"] is None

    def test_intent_without_ground_truth_is_not_applicable(self):
        result = evaluate_ground_truth({}, _case(), query="q")
        assert result["data_fidelity_score"] is None

    def test_no_answer_fails_usage_without_llm_call(self):
        result = _evaluate_number_usage(
            {"messages": []},
            GROUND_TRUTH,
            "quantification",
            "single_year",
            "",
            "How much loss?",
        )
        assert result["number_usage_score"] == 0.0
        assert result["number_usage_failure_comment"]
        assert result["unquantified"] is True

    def test_unknown_intent_rejected_at_case_load(self):
        with pytest.raises(ValueError, match="unknown intent"):
            ExpectedData(intent="ranking")


class TestExpectedDataGroundTruthFields:
    def test_csv_backfill_empty_string_becomes_none(self):
        assert ExpectedData(ground_truth="").ground_truth is None

    def test_intent_case_expects_data_pull(self):
        assert _case().expects_data_pull() is True


class TestHtmlReport:
    def test_report_written_with_failure_comment(self, tmp_path, monkeypatch):
        import gnw_evals.data_handlers.html_reporter as html_reporter

        monkeypatch.setattr(
            html_reporter.Path,
            "write_text",
            html_reporter.Path.write_text,
        )
        results = [
            TestResult(
                thread_id="t1",
                test_id="gt-quant-01",
                query="How much tree cover was lost?",
                overall_score=0.5,
                execution_time="now",
                intent="quantification",
                eval_subtype="single_year",
                expected_aoi_ids=["BRA", "IDN"],
                expected_start_date="2020-01-01",
                expected_end_date="2023-12-31",
                expected_canopy_cover="75",
                expected_forest_filter="primary_forest",
                data_fidelity_score=1.0,
                number_usage_score=0.0,
                number_usage_failure_comment="Answer said 5 Mha; ground truth "
                "is 2.8 Mha for 2023.",
                unquantified=False,
            ),
        ]
        path = write_html_report(results, f"{tmp_path.name}_test_run")
        content = open(path, encoding="utf-8").read()
        assert "Answer said 5 Mha" in content
        assert "quantification" in content
        assert "Number usage" in content
        # Expected params for spot-checking: table columns + failure cards
        assert "BRA; IDN" in content
        assert "2020-2023" in content
        assert "75" in content
        assert "primary_forest" in content
        assert "expected params" in content
        assert "canopy 75" in content
        # Clean up the generated file from outputs/.
        import os

        os.unlink(path)
