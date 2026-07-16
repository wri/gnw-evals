"""Validate permutation manifests against the dataset catalog and case files.

The manifest is the prompt-coverage denominator (see the workspace
eval-prompt-generation spec): every row is a permutation a well-tested cell
should cover. This script fails loudly on rows that could not produce a
valid analytics query, and reports coverage of manifest rows by cases.

Usage:
    uv run python generation/validate_manifest.py \
        --catalog ../project-zeno/src/agent/datasets/catalog/tree_cover_loss.yml
"""

import csv
import re
import sys
from pathlib import Path

import click
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO_ROOT / "cases" / "manifests"
CASES_DIR = REPO_ROOT / "cases"

VALID_INTENTS = {"quantification", "comparison", "trend"}
VALID_DATE_EXPRESSIONS = {"absolute_year", "absolute_range"}
VALID_PHRASINGS = {"direct", "conversational", "imprecise"}
VALID_INTERSECTIONS = {"", "driver", "fire"}
_AOI_ID = re.compile(r"^[A-Z]{3}$")  # GADM level-0 slice; widen per phase


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
    return {
        "dataset_id": str(data["dataset_id"]),
        "canopy_values": canopy_values,
        "forest_filters": forest_filters | {""},
        "start_year": int(str(data["start_date"])[:4]),
        "end_year": int(str(data["end_date"])[:4]),
    }


def _validate_row(row: dict, catalog: dict) -> list[str]:
    errors = []
    rid = row.get("manifest_id", "<missing id>")

    if row.get("intent") not in VALID_INTENTS:
        errors.append(f"{rid}: unknown intent {row.get('intent')!r}")
    if not row.get("eval_subtype"):
        errors.append(f"{rid}: empty eval_subtype")

    aoi_ids = [a for a in (row.get("aoi_ids") or "").split(";") if a]
    if not aoi_ids:
        errors.append(f"{rid}: no aoi_ids")
    for aoi in aoi_ids:
        if not _AOI_ID.match(aoi):
            errors.append(f"{rid}: aoi id {aoi!r} is not a GADM level-0 ISO3 code")

    try:
        start = int(row["start_year"])
        end = int(row["end_year"])
        if not (catalog["start_year"] <= start <= end <= catalog["end_year"]):
            errors.append(
                f"{rid}: years {start}-{end} outside catalog range "
                f"{catalog['start_year']}-{catalog['end_year']} or reversed",
            )
    except (KeyError, ValueError):
        errors.append(f"{rid}: start_year/end_year must be 4-digit years")

    canopy = row.get("canopy_cover") or ""
    if canopy and canopy not in catalog["canopy_values"]:
        errors.append(
            f"{rid}: canopy {canopy!r} not a legal catalog value "
            f"{sorted(catalog['canopy_values'])}",
        )
    if (row.get("forest_filter") or "") not in catalog["forest_filters"]:
        errors.append(f"{rid}: forest_filter {row.get('forest_filter')!r} unknown")
    if (row.get("intersections") or "") not in VALID_INTERSECTIONS:
        errors.append(f"{rid}: intersections {row.get('intersections')!r} unknown")
    if row.get("date_expression") not in VALID_DATE_EXPRESSIONS:
        errors.append(f"{rid}: date_expression {row.get('date_expression')!r} unknown")
    if row.get("phrasing") not in VALID_PHRASINGS:
        errors.append(f"{rid}: phrasing {row.get('phrasing')!r} unknown")
    try:
        if int(row["n_cases"]) < 1:
            errors.append(f"{rid}: n_cases must be >= 1")
    except (KeyError, ValueError):
        errors.append(f"{rid}: n_cases must be an integer")

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
    "--catalog",
    "catalog_path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the dataset catalog YAML (tree_cover_loss.yml)",
)
@click.option(
    "--manifest-dir",
    type=click.Path(exists=True, path_type=Path),
    default=MANIFEST_DIR,
    help="Directory holding *.manifest.csv files",
)
def main(catalog_path: Path, manifest_dir: Path) -> None:
    """Validate all manifests and report case coverage per manifest row."""
    catalog = _load_catalog(catalog_path)
    manifests = sorted(manifest_dir.glob("*.manifest.csv"))
    if not manifests:
        raise click.ClickException(f"no *.manifest.csv files in {manifest_dir}")

    all_errors: list[str] = []
    for manifest_path in manifests:
        with open(manifest_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        ids = [r.get("manifest_id", "") for r in rows]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            all_errors.append(f"{manifest_path.name}: duplicate ids {duplicates}")

        for row in rows:
            all_errors.extend(_validate_row(row, catalog))

        cases_path = CASES_DIR / manifest_path.name.replace(".manifest", "")
        counts = _case_counts(cases_path)
        covered = sum(1 for r in rows if counts.get(r["manifest_id"], 0) > 0)
        unknown = set(counts) - set(ids)
        if unknown:
            all_errors.append(
                f"{cases_path.name}: cases reference unknown manifest ids {unknown}",
            )

        print(f"{manifest_path.name}: {len(rows)} rows")
        print(
            f"  prompt coverage: {covered}/{len(rows)} rows have at least one case "
            f"({covered / len(rows):.0%})",
        )
        short = [
            f"{r['manifest_id']} ({counts.get(r['manifest_id'], 0)}/{r['n_cases']})"
            for r in rows
            if counts.get(r["manifest_id"], 0) < int(r["n_cases"])
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
