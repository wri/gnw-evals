"""Per-dataset generation config, shared by generate_cases and validate_manifest.

The manifest is dataset-agnostic (a superset of parameter columns); this
table is what makes a manifest row resolve to the right ``expected_*`` values
and the right validation surface for its dataset. Facts mirror the catalog
YAMLs in ``project-zeno/src/agent/datasets/catalog/`` and the analytics
handler (``src/agent/datasets/handlers/analytics_handler.py``); see the
workspace applicability map for the reasoning behind ``intents``/``date_mode``.

Only the numeric-intent surface (quantification/trend/comparison) is modelled
here. Each config declares:

- ``dataset_id`` / ``slug`` - catalog identity (slug = catalog filename stem).
- ``intents`` - which numeric intents apply (trend omitted for snapshot or
  aggregate datasets whose product forbids a time series).
- ``date_mode`` - how a manifest row's dates become ``expected_*`` dates:
  ``years`` (``start_year``/``end_year`` → ``YYYY-01-01``/``YYYY-12-31``),
  ``dates`` (``start_date``/``end_date`` verbatim, for alert streams), or
  ``blank`` (dataset ignores/fixes dates → no date expectation is scored).
- ``canopy_default`` - ``"30"`` for TCL-family + flux datasets that take a
  canopy threshold, else ``None`` (no canopy expectation emitted).
- ``fixed_intersections`` - intersection value intrinsic to choosing this
  dataset (``driver`` for id 8, ``fire`` for id 10); emitted on every case.
- ``forest_layers`` - legal ``forest_filter`` values (context layers).
- ``params`` - extra expected columns this dataset can carry
  (``crop_types``, ``gas_types``, ``land_cover_classes``, ``intersections``).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatasetConfig:
    """Generation + validation surface for one catalog dataset."""

    dataset_id: str
    slug: str
    intents: frozenset[str]
    date_mode: str  # "years" | "dates" | "blank"
    canopy_default: str | None = None
    fixed_intersections: str = ""
    forest_layers: frozenset[str] = field(default_factory=frozenset)
    params: frozenset[str] = field(default_factory=frozenset)
    aoi_subtype: str = "country"
    aoi_source: str = "gadm"


_ALL_THREE = frozenset({"quantification", "trend", "comparison"})
_QUANT_COMP = frozenset({"quantification", "comparison"})

DATASET_CONFIGS: dict[str, DatasetConfig] = {
    "global_all_ecosystem_disturbance_alerts_dist_alert": DatasetConfig(
        dataset_id="0",
        slug="global_all_ecosystem_disturbance_alerts_dist_alert",
        intents=_ALL_THREE,
        date_mode="dates",
        params=frozenset({"intersections"}),
    ),
    "global_land_cover": DatasetConfig(
        dataset_id="1",
        slug="global_land_cover",
        intents=_QUANT_COMP,
        date_mode="blank",
        params=frozenset({"land_cover_classes"}),
    ),
    "global_natural_semi_natural_grassland_extent": DatasetConfig(
        dataset_id="2",
        slug="global_natural_semi_natural_grassland_extent",
        intents=_ALL_THREE,
        date_mode="years",
    ),
    "sbtn_natural_lands_map": DatasetConfig(
        dataset_id="3",
        slug="sbtn_natural_lands_map",
        intents=_QUANT_COMP,
        date_mode="blank",
    ),
    "tree_cover_loss": DatasetConfig(
        dataset_id="4",
        slug="tree_cover_loss",
        intents=_ALL_THREE,
        date_mode="years",
        canopy_default="30",
        forest_layers=frozenset({"primary_forest", "intact_forest"}),
        params=frozenset({"intersections"}),
    ),
    "tree_cover_gain": DatasetConfig(
        dataset_id="5",
        slug="tree_cover_gain",
        intents=_QUANT_COMP,
        date_mode="years",
    ),
    "forest_greenhouse_gas_net_flux": DatasetConfig(
        dataset_id="6",
        slug="forest_greenhouse_gas_net_flux",
        intents=_QUANT_COMP,
        date_mode="blank",
        canopy_default="30",
        params=frozenset({"gas_types"}),
    ),
    "tree_cover": DatasetConfig(
        dataset_id="7",
        slug="tree_cover",
        intents=_QUANT_COMP,
        date_mode="blank",
        canopy_default="30",
        forest_layers=frozenset({"primary_forest"}),
    ),
    "tree_cover_loss_by_dominant_driver": DatasetConfig(
        dataset_id="8",
        slug="tree_cover_loss_by_dominant_driver",
        intents=_QUANT_COMP,
        date_mode="blank",
        canopy_default="30",
        fixed_intersections="driver",
        params=frozenset({"intersections"}),
    ),
    "deforestation_sluc_emission_factors_by_agricultural_crop": DatasetConfig(
        dataset_id="9",
        slug="deforestation_sluc_emission_factors_by_agricultural_crop",
        intents=_ALL_THREE,
        date_mode="years",
        params=frozenset({"crop_types", "gas_types"}),
    ),
    "tree_cover_loss_from_fires": DatasetConfig(
        dataset_id="10",
        slug="tree_cover_loss_from_fires",
        intents=_ALL_THREE,
        date_mode="years",
        canopy_default="30",
        fixed_intersections="fire",
        forest_layers=frozenset({"primary_forest", "intact_forest"}),
        params=frozenset({"intersections"}),
    ),
    "integrated_alerts": DatasetConfig(
        dataset_id="11",
        slug="integrated_alerts",
        intents=_ALL_THREE,
        date_mode="dates",
    ),
}

SLUG_BY_ID = {cfg.dataset_id: slug for slug, cfg in DATASET_CONFIGS.items()}


def config_for_manifest(filename: str) -> DatasetConfig:
    """Resolve the dataset config from a ``<slug>__<intent>.manifest.csv`` name.

    The slug can itself contain ``__`` only if a catalog ever does; we match
    the longest known slug that prefixes the filename to stay unambiguous.
    """
    stem = filename.removesuffix(".manifest.csv").removesuffix(".csv")
    for slug in sorted(DATASET_CONFIGS, key=len, reverse=True):
        if stem == slug or stem.startswith(f"{slug}__"):
            return DATASET_CONFIGS[slug]
    raise KeyError(f"no dataset config matches manifest {filename!r}")
