"""Validate permutation manifests against the dataset catalog and case files.

The manifest is the prompt-coverage denominator (see the workspace
eval-prompt-generation spec): every row is a permutation a well-tested cell
should cover. This script fails loudly on rows that could not produce a
valid analytics query, and reports coverage of manifest rows by cases.

Each manifest's dataset is resolved from its filename via
``generation/dataset_config.py``; its validation surface (legal canopy
values, context layers, year range) comes from that dataset's catalog YAML
in ``--catalog-dir``.

Usage:
    uv run python generation/validate_manifest.py \
        --catalog-dir ../project-zeno/src/agent/datasets/catalog
"""

import csv
import re
import sys
from pathlib import Path

import click
import yaml
from dataset_config import DatasetConfig, config_for_manifest

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO_ROOT / "cases" / "manifests"
CASES_DIR = REPO_ROOT / "cases"

VALID_PHRASINGS = {"direct", "conversational", "imprecise"}
_AOI_ID = re.compile(r"^[A-Z]{3}$")  # GADM level-0 slice; widen per phase
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Date-expression classes legal per date_mode.
_DATE_EXPRESSIONS = {
    "years": {"absolute_year", "absolute_range"},
    "dates": {"absolute_date", "absolute_date_range", "relative_recent"},
    "blank": {"none", "fixed"},
}


def _load_catalog(catalog_path: Path) -> dict:
    """Extract the validation surface from the dataset catalog YAML."""
    data = yaml.safe_load(catalog_path.read_text())
    canopy_values: set[str] = set()
    for param in data.get("parameters") or []:
        if param.get("name") == "canopy_cover":
            canopy_values = {str(v) for v in param.get("values") or []}
    forest_filters = {
        str(layer.get("value")) for layer in data.get("context_layers") or []
    }
    # Alert-stream datasets (0, 11) declare no end_date (open-ended to
    # "today"); year bounds are only consulted for date_mode="years"
    # datasets, which always declare both, so a wide default is safe.
    return {
        "dataset_id": str(data["dataset_id"]),
        "canopy_values": canopy_values,
        "forest_filters": forest_filters,
        "start_year": int(str(data.get("start_date") or "0001")[:4]),
        "end_year": int(str(data.get("end_date") or "9999")[:4]),
    }


def _validate_row(row: dict, cfg: DatasetConfig, catalog: dict) -> list[str]:
    errors = []
    rid = row.get("manifest_id", "<missing id>")

    if row.get("intent") not in cfg.intents:
        errors.append(
            f"{rid}: intent {row.get('intent')!r} not applicable to {cfg.slug} "
            f"(applicable: {sorted(cfg.intents)})",
        )
    if not row.get("eval_subtype"):
        errors.append(f"{rid}: empty eval_subtype")

    aoi_ids = [a for a in (row.get("aoi_ids") or "").split(";") if a]
    if not aoi_ids:
        errors.append(f"{rid}: no aoi_ids")
    for aoi in aoi_ids:
        if not _AOI_ID.match(aoi):
            errors.append(f"{rid}: aoi id {aoi!r} is not a GADM level-0 ISO3 code")

    errors.extend(_validate_dates(row, cfg, catalog))
    errors.extend(_validate_params(row, cfg, catalog))

    if row.get("phrasing") not in VALID_PHRASINGS:
        errors.append(f"{rid}: phrasing {row.get('phrasing')!r} unknown")
    try:
        if int(row["n_cases"]) < 1:
            errors.append(f"{rid}: n_cases must be >= 1")
    except (KeyError, ValueError):
        errors.append(f"{rid}: n_cases must be an integer")

    return errors


def _validate_dates(row: dict, cfg: DatasetConfig, catalog: dict) -> list[str]:
    rid = row.get("manifest_id", "<missing id>")
    errors: list[str] = []
    expr = row.get("date_expression")
    if expr not in _DATE_EXPRESSIONS[cfg.date_mode]:
        errors.append(
            f"{rid}: date_expression {expr!r} not valid for date_mode "
            f"{cfg.date_mode!r} (expected one of "
            f"{sorted(_DATE_EXPRESSIONS[cfg.date_mode])})",
        )

    if cfg.date_mode == "years":
        try:
            start, end = int(row["start_year"]), int(row["end_year"])
            if not (catalog["start_year"] <= start <= end <= catalog["end_year"]):
                errors.append(
                    f"{rid}: years {start}-{end} outside catalog range "
                    f"{catalog['start_year']}-{catalog['end_year']} or reversed",
                )
        except (KeyError, ValueError):
            errors.append(f"{rid}: start_year/end_year must be 4-digit years")
    elif cfg.date_mode == "dates":
        for col in ("start_date", "end_date"):
            value = (row.get(col) or "").strip()
            if not _ISO_DATE.match(value):
                errors.append(f"{rid}: {col} {value!r} must be YYYY-MM-DD")
    return errors


def _validate_params(row: dict, cfg: DatasetConfig, catalog: dict) -> list[str]:
    rid = row.get("manifest_id", "<missing id>")
    errors: list[str] = []

    canopy = (row.get("canopy_cover") or "").strip()
    if canopy:
        if cfg.canopy_default is None:
            errors.append(
                f"{rid}: {cfg.slug} takes no canopy_cover but row sets {canopy!r}",
            )
        elif catalog["canopy_values"] and canopy not in catalog["canopy_values"]:
            errors.append(
                f"{rid}: canopy {canopy!r} not a legal catalog value "
                f"{sorted(catalog['canopy_values'])}",
            )

    forest_filter = (row.get("forest_filter") or "").strip()
    if forest_filter and forest_filter not in cfg.forest_layers:
        errors.append(
            f"{rid}: forest_filter {forest_filter!r} not a context layer of "
            f"{cfg.slug} (legal: {sorted(cfg.forest_layers) or 'none'})",
        )

    intersections = (row.get("intersections") or "").strip()
    if intersections and "intersections" not in cfg.params:
        errors.append(
            f"{rid}: {cfg.slug} takes no intersections but row sets {intersections!r}",
        )

    for col, param in (("crop_types", "crop_types"), ("gas_types", "gas_types")):
        value = (row.get(col) or "").strip()
        if value and param not in cfg.params:
            errors.append(f"{rid}: {cfg.slug} takes no {param} but row sets {value!r}")
    return errors


def _case_counts(cases_path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not cases_path.exists():
        return counts
    with open(cases_path, encoding="utf-8") as f:
        for case in csv.DictReader(f):
            manifest_id = (case.get("manifest_id") or "").strip()
            if manifest_id:
                counts[manifest_id] = counts.get(manifest_id, 0) + 1
    return counts


@click.command()
@click.option(
    "--catalog-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory of dataset catalog YAMLs (project-zeno .../datasets/catalog)",
)
@click.option(
    "--manifest-dir",
    type=click.Path(exists=True, path_type=Path),
    default=MANIFEST_DIR,
    help="Directory holding *.manifest.csv files",
)
def main(catalog_dir: Path, manifest_dir: Path) -> None:
    """Validate all manifests and report case coverage per manifest row."""
    manifests = sorted(manifest_dir.glob("*.manifest.csv"))
    if not manifests:
        raise click.ClickException(f"no *.manifest.csv files in {manifest_dir}")

    all_errors: list[str] = []
    for manifest_path in manifests:
        try:
            cfg = config_for_manifest(manifest_path.name)
        except KeyError as exc:
            all_errors.append(str(exc))
            continue
        catalog_path = catalog_dir / f"{cfg.slug}.yml"
        if not catalog_path.exists():
            all_errors.append(
                f"{manifest_path.name}: no catalog YAML at {catalog_path}",
            )
            continue
        catalog = _load_catalog(catalog_path)
        if catalog["dataset_id"] != cfg.dataset_id:
            all_errors.append(
                f"{manifest_path.name}: catalog dataset_id {catalog['dataset_id']} "
                f"!= config {cfg.dataset_id}",
            )

        with open(manifest_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        ids = [r.get("manifest_id", "") for r in rows]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            all_errors.append(f"{manifest_path.name}: duplicate ids {duplicates}")

        for row in rows:
            all_errors.extend(_validate_row(row, cfg, catalog))

        cases_path = CASES_DIR / manifest_path.name.replace(".manifest", "")
        counts = _case_counts(cases_path)
        covered = sum(1 for r in rows if counts.get(r["manifest_id"], 0) > 0)
        unknown = set(counts) - set(ids)
        if unknown:
            all_errors.append(
                f"{cases_path.name}: cases reference unknown manifest ids {unknown}",
            )

        pct = f"{covered / len(rows):.0%}" if rows else "n/a"
        print(f"{manifest_path.name}: {len(rows)} rows")
        print(
            f"  prompt coverage: {covered}/{len(rows)} rows have at least one case ({pct})",
        )
        short = [
            f"{r['manifest_id']} ({counts.get(r['manifest_id'], 0)}/{r['n_cases']})"
            for r in rows
            if counts.get(r["manifest_id"], 0) < int(r["n_cases"] or 1)
        ]
        if short:
            print(f"  below n_cases target: {', '.join(short)}")

    if all_errors:
        print("\nVALIDATION ERRORS:", file=sys.stderr)
        for error in all_errors:
            print(f"  {error}", file=sys.stderr)
        raise SystemExit(1)
    print("\nAll manifests valid.")


if __name__ == "__main__":
    main()
