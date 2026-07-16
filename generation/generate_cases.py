"""Generate candidate eval cases from a permutation manifest.

For every manifest row with fewer promoted cases than its ``n_cases``
target, this script asks an LLM to write the missing prompt wordings
(honouring the per-cell instruction files) and constructs the full case row
mechanically from the manifest parameters: the LLM only ever writes the
query text, never expected values.

Candidates land in ``cases/candidates/`` for human spot-checking; promotion
(appending to the main ``cases/*.csv`` with status=ready) is deliberately
manual. See generation/README.md for the workflow.

Usage:
    uv run python generation/generate_cases.py --intent quantification
    uv run python generation/generate_cases.py --intent trend --dry-run
"""

import csv
from pathlib import Path

import click
import dotenv
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO_ROOT / "cases" / "manifests"
CASES_DIR = REPO_ROOT / "cases"
CANDIDATES_DIR = CASES_DIR / "candidates"
INSTRUCTIONS_DIR = Path(__file__).resolve().parent

DATASET_SLUG = "tree_cover_loss"
DATASET_ID = "4"

# Mirrors the promoted case files (the original PoC column order plus
# manifest_id); DictWriter fills unset columns with "".
CASE_COLUMNS = [
    "query",
    "expected_aoi_ids",
    "expected_subregion",
    "expected_aoi_source",
    "expected_dataset_id",
    "expected_dataset_name",
    "expected_context_layer",
    "expected_start_date",
    "expected_end_date",
    "expected_answer",
    "expected_clarification",
    "expected_chart_type",
    "expected_canopy_cover",
    "expected_forest_filter",
    "expected_intersections",
    "expected_crop_types",
    "expected_gas_types",
    "judge_instruction",
    "expected_language",
    "test_group",
    "status",
    "test_id",
    "intent",
    "eval_subtype",
    "manifest_id",
]

COUNTRY_NAMES = {
    "BRA": "Brazil",
    "IDN": "Indonesia",
    "COD": "the Democratic Republic of the Congo",
    "CRI": "Costa Rica",
    "GBR": "the United Kingdom",
}


class Wordings(BaseModel):
    """Structured output: the generated prompt wordings only."""

    wordings: list[str] = Field(
        description="The generated user prompts, one string per requested wording",
    )


def _existing_wordings(intent: str) -> dict[str, list[str]]:
    """Existing queries per manifest row (promoted cases plus candidates)."""
    wordings: dict[str, list[str]] = {}
    for path in (
        CASES_DIR / f"{DATASET_SLUG}__{intent}.csv",
        CANDIDATES_DIR / f"{DATASET_SLUG}__{intent}.candidates.csv",
    ):
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for case in csv.DictReader(f):
                manifest_id = (case.get("manifest_id") or "").strip()
                if manifest_id:
                    wordings.setdefault(manifest_id, []).append(case.get("query", ""))
    return wordings


def _row_brief(row: dict) -> str:
    countries = "; ".join(
        COUNTRY_NAMES.get(a, a) for a in row["aoi_ids"].split(";") if a
    )
    lines = [
        f"- intent: {row['intent']}, subtype: {row['eval_subtype']}",
        f"- country/countries: {countries}",
        f"- window: {row['start_year']} to {row['end_year']}"
        + (" (single year)" if row["start_year"] == row["end_year"] else ""),
        f"- canopy threshold: {row['canopy_cover'] or '30'}"
        + (" (default: do NOT mention it)" if (row["canopy_cover"] or "30") == "30" else " (MUST be stated)"),
        f"- forest filter: {row['forest_filter'] or 'none (plain tree cover loss; opt out of forest-type filters explicitly)'}",
        f"- intersections: {row['intersections'] or 'none'}",
        f"- phrasing style: {row['phrasing']}",
        f"- language: {row['expected_language'] or 'en'}",
    ]
    if row.get("judge_note"):
        lines.append(f"- scoring context (do not quote in the prompt): {row['judge_note']}")
    if row.get("notes"):
        lines.append(f"- notes: {row['notes']}")
    return "\n".join(lines)


def _generation_prompt(
    row: dict,
    n_wordings: int,
    instructions: str,
    existing_wordings: list[str],
) -> str:
    existing_block = ""
    if existing_wordings:
        joined = "\n".join(f"  - {w}" for w in existing_wordings)
        existing_block = (
            f"\nWordings that already exist for this permutation (yours must "
            f"differ meaningfully in structure and vocabulary):\n{joined}\n"
        )
    return f"""You write user prompts for evaluating a geospatial AI assistant \
(Global Nature Watch). Each prompt must read like a real user and map to \
exactly one analytics query.

INSTRUCTIONS (follow every rule):

{instructions}

PERMUTATION TO EXPRESS:

{_row_brief(row)}
{existing_block}
Write exactly {n_wordings} prompt wording(s) for this permutation. Every \
parameter above must be unambiguously derivable from the wording alone \
(except defaults the instructions say not to mention). Return only the \
wordings."""


def _case_from_wording(row: dict, wording: str, variant_index: int) -> dict:
    variant = chr(ord("a") + variant_index)
    test_id = f"{row['manifest_id'].removeprefix('m-')}{variant}"
    return {
        "query": wording,
        "expected_aoi_ids": row["aoi_ids"],
        "expected_subregion": "country",
        "expected_aoi_source": "gadm",
        "expected_dataset_id": DATASET_ID,
        "expected_dataset_name": DATASET_SLUG,
        "expected_start_date": f"{row['start_year']}-01-01",
        "expected_end_date": f"{row['end_year']}-12-31",
        "expected_canopy_cover": row["canopy_cover"] or "30",
        "expected_forest_filter": row["forest_filter"],
        "expected_intersections": row["intersections"],
        "judge_instruction": row.get("judge_note", ""),
        "expected_language": row.get("expected_language", "en"),
        "test_group": f"GT-{row['intent'][:5].upper()}",
        "status": "candidate",
        "test_id": test_id,
        "intent": row["intent"],
        "eval_subtype": row["eval_subtype"],
        "manifest_id": row["manifest_id"],
    }


@click.command()
@click.option(
    "--intent",
    type=click.Choice(["quantification", "comparison", "trend"]),
    required=True,
)
@click.option("--model", default="claude-sonnet-5", show_default=True)
@click.option("--limit", type=int, default=0, help="Only process N manifest rows")
@click.option("--dry-run", is_flag=True, help="Print prompts instead of calling the LLM")
def main(intent: str, model: str, limit: int, dry_run: bool) -> None:
    """Generate candidate cases for one intent cell."""
    dotenv.load_dotenv(REPO_ROOT / ".env")

    manifest_path = MANIFEST_DIR / f"{DATASET_SLUG}__{intent}.manifest.csv"
    with open(manifest_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    instructions = (
        (INSTRUCTIONS_DIR / DATASET_SLUG / "_shared.md").read_text()
        + "\n\n"
        + (INSTRUCTIONS_DIR / DATASET_SLUG / f"{intent}.md").read_text()
    )

    existing = _existing_wordings(intent)
    todo = [
        (row, int(row["n_cases"]) - len(existing.get(row["manifest_id"], [])))
        for row in rows
        if len(existing.get(row["manifest_id"], [])) < int(row["n_cases"])
    ]
    if limit:
        todo = todo[:limit]
    if not todo:
        print("All manifest rows already meet their n_cases target.")
        return

    print(f"{len(todo)} manifest rows need wordings ({sum(n for _, n in todo)} total)")

    llm = None if dry_run else ChatAnthropic(model=model, temperature=1.0, max_tokens=2048)

    candidates: list[dict] = []
    for row, needed in todo:
        prior = existing.get(row["manifest_id"], [])
        prompt = _generation_prompt(row, needed, instructions, prior)
        if dry_run:
            print(f"\n=== {row['manifest_id']} (needs {needed}) ===\n{prompt}")
            continue
        result = llm.with_structured_output(Wordings).invoke(prompt)
        if len(result.wordings) != needed:
            raise RuntimeError(
                f"{row['manifest_id']}: asked for {needed} wordings, "
                f"got {len(result.wordings)}",
            )
        for i, wording in enumerate(result.wordings):
            candidates.append(_case_from_wording(row, wording, len(prior) + i))
        print(f"  {row['manifest_id']}: {needed} wording(s) generated")

    if dry_run or not candidates:
        return

    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CANDIDATES_DIR / f"{DATASET_SLUG}__{intent}.candidates.csv"
    exists = out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CASE_COLUMNS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerows(candidates)
    print(f"\n{len(candidates)} candidate case(s) appended to {out_path}")
    print("Spot-check them, then promote into the main cases file with status=ready.")


if __name__ == "__main__":
    main()
