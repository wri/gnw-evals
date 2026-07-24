"""Tests for the dataset-generic case generation tooling.

Generation itself (LLM wordings) is not exercised here; what matters is that
each dataset's manifest row deterministically yields the right ``expected_*``
values, since that is what makes a generated case scorable. See
generation/dataset_config.py and generation/generate_cases.py.

    $ uv run pytest tests/test_generation.py -v
"""

import sys
from pathlib import Path

import pytest

GENERATION_DIR = Path(__file__).resolve().parent.parent / "generation"
sys.path.insert(0, str(GENERATION_DIR))

from dataset_config import DATASET_CONFIGS, config_for_manifest
from generate_cases import _case_from_wording


def _row(**overrides) -> dict:
    base = {
        "manifest_id": "m-x-quant-01",
        "intent": "quantification",
        "eval_subtype": "single_year",
        "aoi_ids": "BRA",
        "start_year": "2023",
        "end_year": "2023",
        "phrasing": "direct",
        "n_cases": "1",
    }
    base.update(overrides)
    return base


class TestExpectedValues:
    def test_tcl_years_canopy_forest(self):
        cfg = DATASET_CONFIGS["tree_cover_loss"]
        case = _case_from_wording(cfg, _row(forest_filter="primary_forest"), "q", 0)
        assert case["expected_dataset_id"] == "4"
        assert case["expected_start_date"] == "2023-01-01"
        assert case["expected_end_date"] == "2023-12-31"
        assert case["expected_canopy_cover"] == "30"  # default filled
        assert case["expected_forest_filter"] == "primary_forest"
        assert case["test_id"] == "x-quant-01a"

    def test_grasslands_years_no_canopy(self):
        cfg = DATASET_CONFIGS["global_natural_semi_natural_grassland_extent"]
        case = _case_from_wording(cfg, _row(start_year="2005", end_year="2020"), "q", 0)
        assert case["expected_dataset_id"] == "2"
        assert case["expected_start_date"] == "2005-01-01"
        assert case["expected_end_date"] == "2020-12-31"
        assert case["expected_canopy_cover"] == ""  # dataset takes no canopy
        assert case["expected_forest_filter"] == ""

    def test_alerts_full_dates(self):
        cfg = DATASET_CONFIGS["integrated_alerts"]
        row = _row(
            date_expression="absolute_date_range",
            start_date="2024-01-01",
            end_date="2024-03-31",
        )
        case = _case_from_wording(cfg, row, "q", 0)
        assert case["expected_dataset_id"] == "11"
        assert case["expected_start_date"] == "2024-01-01"
        assert case["expected_end_date"] == "2024-03-31"
        assert case["expected_intersections"] == ""  # 11 has no intersections

    def test_snapshot_blank_dates_with_canopy(self):
        cfg = DATASET_CONFIGS["tree_cover"]
        case = _case_from_wording(cfg, _row(), "q", 0)
        assert case["expected_dataset_id"] == "7"
        assert case["expected_start_date"] == ""  # fixed-date dataset: no date check
        assert case["expected_end_date"] == ""
        assert case["expected_canopy_cover"] == "30"

    def test_driver_fixed_intersection(self):
        cfg = DATASET_CONFIGS["tree_cover_loss_by_dominant_driver"]
        case = _case_from_wording(cfg, _row(), "q", 0)
        assert case["expected_dataset_id"] == "8"
        assert case["expected_intersections"] == "driver"  # intrinsic to the dataset

    def test_fires_fixed_intersection(self):
        cfg = DATASET_CONFIGS["tree_cover_loss_from_fires"]
        case = _case_from_wording(cfg, _row(start_year="2020", end_year="2023"), "q", 0)
        assert case["expected_intersections"] == "fire"

    def test_sluc_crop_and_gas(self):
        cfg = DATASET_CONFIGS[
            "deforestation_sluc_emission_factors_by_agricultural_crop"
        ]
        row = _row(
            start_year="2024",
            end_year="2024",
            crop_types="Soybean",
            gas_types="CO2e",
        )
        case = _case_from_wording(cfg, row, "q", 0)
        assert case["expected_dataset_id"] == "9"
        assert case["expected_crop_types"] == "Soybean"
        assert case["expected_gas_types"] == "CO2e"
        assert case["expected_canopy_cover"] == ""


class TestConfigResolution:
    def test_manifest_name_resolves_to_config(self):
        cfg = config_for_manifest("tree_cover_loss__quantification.manifest.csv")
        assert cfg.dataset_id == "4"

    def test_driver_slug_not_shadowed_by_tcl(self):
        # tree_cover_loss is a prefix of tree_cover_loss_by_dominant_driver;
        # the longest-match rule must pick the driver dataset.
        cfg = config_for_manifest(
            "tree_cover_loss_by_dominant_driver__comparison.manifest.csv",
        )
        assert cfg.dataset_id == "8"

    def test_unknown_manifest_raises(self):
        with pytest.raises(KeyError):
            config_for_manifest("nonexistent_dataset__trend.manifest.csv")

    def test_trend_not_applicable_to_snapshot_datasets(self):
        for slug in (
            "global_land_cover",
            "sbtn_natural_lands_map",
            "tree_cover",
            "tree_cover_gain",
            "forest_greenhouse_gas_net_flux",
            "tree_cover_loss_by_dominant_driver",
        ):
            assert "trend" not in DATASET_CONFIGS[slug].intents
