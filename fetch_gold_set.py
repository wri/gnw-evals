"""Snapshot the GOLD eval set from Google Sheets to a local CSV.

The gold sheet is live and hand-edited, so a run against it today is not
comparable to a run from last week: a score change could be the agent, or it
could be someone retyping an expected answer. This writes a datestamped local
copy so `--test-file` runs are reproducible and diffable.

Usage:
    uv run python fetch_gold_set.py
    uv run python fetch_gold_set.py --force
    uv run python fetch_gold_set.py --out data/gold-before-prompt-change.csv

Then run against the snapshot:
    uv run gnw_evals --test-file data/gold-YYYYMMDD.csv --sample-size -1 ...

Requires SPREADSHEET_ID in .env. Writes raw bytes rather than a pandas
round-trip, so quoting and embedded newlines survive untouched.
"""

from datetime import date
from pathlib import Path

import click
import dotenv
import httpx
import pandas as pd

from gnw_evals.utils.sheet_registry import get_sheet_url

dotenv.load_dotenv()

PROJECT_ROOT = Path(__file__).parent
EVAL_SET = "gold"


@click.command()
@click.option(
    "--out",
    default=None,
    type=click.Path(path_type=Path),
    help="Output path. Defaults to data/gold-YYYYMMDD.csv (relative to project root).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite the output file if it already exists.",
)
@click.option(
    "--timeout",
    default=60,
    type=int,
    help="HTTP timeout in seconds.",
)
def fetch_gold_set(out: Path | None, force: bool, timeout: int) -> None:
    """Download the gold eval sheet and write it to a datestamped local CSV."""
    url = get_sheet_url(EVAL_SET)

    if out is None:
        out = Path("data") / f"{EVAL_SET}-{date.today():%Y%m%d}.csv"
    if not out.is_absolute():
        out = PROJECT_ROOT / out

    if out.exists() and not force:
        raise click.ClickException(
            f"{out} already exists. Pass --force to overwrite, or --out to write elsewhere.",
        )

    click.echo(f"Fetching {EVAL_SET} sheet...")
    # follow_redirects is required: the Sheets export URL 302s to googleusercontent.
    response = httpx.get(url, timeout=float(timeout), follow_redirects=True)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "csv" not in content_type:
        raise click.ClickException(
            f"Expected CSV, got '{content_type}'. The sheet is probably not "
            "link-shareable, or SPREADSHEET_ID/gid is wrong.",
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(response.content)

    _summarise(out)


def _summarise(path: Path) -> None:
    """Print a short sanity check on the snapshot that was just written."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    queries = (df["query"].str.strip() != "").sum() if "query" in df.columns else 0

    click.echo(f"\nWrote {path.relative_to(PROJECT_ROOT)}")
    click.echo(f"  Rows:            {len(df)}")
    click.echo(f"  Non-empty query: {queries}  (blank-query rows are skipped at load)")

    if "status" in df.columns:
        counts = df["status"].str.strip().replace("", "(blank)").value_counts()
        click.echo("  Status values:")
        for value, count in counts.items():
            click.echo(f"    {value:<12} {count:>3}")
        skip = sorted(
            v.strip().lower()
            for v in df["status"].unique()
            if v.strip() and v.strip().lower() != "done"
        )
        if skip:
            click.echo(
                f'\n  --status-filter "{",".join(skip)}"  '
                "(reminder: this is a SKIP list, not a keep list)",
            )

    click.echo(
        "\nNote: data/ is gitignored but the existing snapshot is tracked, so use "
        "`git add -f` if you want this one committed.",
    )


if __name__ == "__main__":
    fetch_gold_set()
