"""Internal scorecard: static HTML rendered from committed run summaries.

Reads every ``runs/*.json`` artefact and writes ``runs/scorecard.html``:
the full intent x dataset matrix (every catalog dataset, latest result per
cell across runs), per-cell drill-down (staged-gate buckets, per-evaluator
rates, failing cases with judge comments) and the history of e2e pass rates
across runs with methodology-version markers.

Usage:
    uv run gnw_scorecard
"""

import html
import json
from pathlib import Path

import click

from gnw_evals.data_handlers.run_summary import DATASET_SLUGS, RUNS_DIR
from gnw_evals.evaluators.registry import SCORE_FIELD_BUCKETS

# Column order: the 11 substantive intents from the trace-analytics taxonomy
# (project-zeno-next .../lib/analytics/taxonomy.ts INTENT_LABELS).
INTENTS = [
    "quantification",
    "trend",
    "monitoring",
    "spatial",
    "causal",
    "comparison",
    "risk",
    "feasibility",
    "conceptual",
    "identification",
    "other",
]

# Non-dataset surfaces from the programme PRD's matrix design (phase 3):
# behaviours scored across the whole assistant rather than per dataset.
EXTRA_ROWS = ["guardrails", "clarification", "cross-dataset"]

_TIER_COLOURS = {
    "minimal": "#9aa0a6",
    "partial": "#e8a33d",
    "good": "#3d9970",
    "comprehensive": "#1e6b4e",
}

# Staged-gate bucket order and chip colours, shared by the stage table and
# the per-evaluator table so the parent bucket of each score is visible.
_BUCKET_ORDER = {"retrieval": 0, "analysis": 1, "explanation": 2}
_BUCKET_COLOURS = {
    "retrieval": "#5b7fa6",
    "analysis": "#7a5ba6",
    "explanation": "#a65b7f",
}


def _bucket_chip(bucket: str | None) -> str:
    if bucket is None:
        return '<span class="n">ungated</span>'
    return (
        f'<span class="tier" style="background:{_BUCKET_COLOURS[bucket]}">'
        f"{bucket}</span>"
    )


# Tier definitions from the programme PRD (provisional thresholds, mirrored
# from run_summary.coverage_tier); rendered as the scorecard legend.
_TIER_LEGEND = [
    ("minimal", "Fewer than 10 cases, or surface coverage below 40%"),
    ("partial", "10+ cases and surface coverage 40%+, but prompt coverage below 50%"),
    ("good", "Prompt coverage 50%+ and surface coverage 70%+"),
    (
        "comprehensive",
        "Prompt coverage 80%+ and surface coverage 90%+, "
        "including at least two non-English languages",
    ),
]


def _quality_colour(rate: float | None) -> str:
    if rate is None:
        return "#9aa0a6"
    if rate >= 0.8:
        return "#3d9970"
    if rate >= 0.5:
        return "#e8a33d"
    return "#c0392b"


def _pct(value: float | None) -> str:
    return f"{value:.0%}" if value is not None else "–"


def _load_runs(runs_dir: Path) -> list[dict]:
    runs = [json.loads(path.read_text()) for path in sorted(runs_dir.glob("*.json"))]
    runs.sort(key=lambda r: r["timestamp"])
    return runs


def _slug(cell: dict) -> str:
    # Resolve through the catalog so summaries written before a dataset was
    # added to DATASET_SLUGS (raw-id slugs) land on the same row as new ones.
    return DATASET_SLUGS.get(str(cell.get("dataset_id")), cell["dataset_slug"])


def _cell_key(cell: dict) -> tuple[str, str]:
    return (_slug(cell), cell["intent"])


def _latest_cells(runs: list[dict]) -> dict[tuple[str, str], tuple[dict, dict]]:
    """Most recent (cell, run) per matrix position across all runs.

    Official runs cover one cell each, so the matrix must merge runs rather
    than render only the newest file.
    """
    merged: dict[tuple[str, str], tuple[dict, dict]] = {}
    for run in runs:  # oldest first; later runs overwrite
        for cell in run["cells"]:
            merged[_cell_key(cell)] = (cell, run)
    return merged


def _matrix_html(runs: list[dict]) -> str:
    cells = _latest_cells(runs)
    # Every catalog dataset is a row, evaluated or not; keep any evaluated
    # slug the catalog does not know rather than dropping its results.
    dataset_slugs = list(DATASET_SLUGS.values())
    dataset_slugs += sorted(
        {slug for slug, _ in cells} - set(dataset_slugs),
    )

    head = "".join(f"<th>{html.escape(i)}</th>" for i in INTENTS)
    body_rows = []
    for slug in dataset_slugs:
        tds = []
        for intent in INTENTS:
            entry = cells.get((slug, intent))
            if entry is None:
                tds.append('<td class="empty">not yet<br>evaluated</td>')
                continue
            cell, _run = entry
            quality = cell["quality"]["e2e_pass_rate"]
            tier = cell["coverage"]["tier"]
            anchor = f"{slug}--{intent}"
            tds.append(
                f'<td class="cell" style="border-top: 4px solid '
                f'{_quality_colour(quality)}">'
                f'<a href="#{anchor}"><strong>{_pct(quality)}</strong></a><br>'
                f'<span class="tier" style="background:{_TIER_COLOURS[tier]}">'
                f"{tier}</span><br>"
                f'<span class="n">n={cell["n_cases"]}</span></td>',
            )
        body_rows.append(
            f"<tr><th>{html.escape(slug)}</th>{''.join(tds)}</tr>",
        )
    for surface in EXTRA_ROWS:
        body_rows.append(
            f"<tr><th>{html.escape(surface)}</th>"
            f'<td class="empty" colspan="{len(INTENTS)}">not yet evaluated '
            "(scored per assistant behaviour, not per intent)</td></tr>",
        )
    return (
        '<table class="matrix"><thead><tr><th></th>'
        f"{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
    )


def _legend_html() -> str:
    tier_rows = "".join(
        f'<tr><td><span class="tier" style="background:{_TIER_COLOURS[tier]}">'
        f"{tier}</span></td><td>{html.escape(definition)}</td></tr>"
        for tier, definition in _TIER_LEGEND
    )
    return f"""
<details class="legend"><summary>How to read this matrix</summary>
<p class="meta">Each evaluated cell shows three things:</p>
<ul class="meta">
  <li><strong>Pass rate</strong> — end-to-end pass rate under the staged
      gate (a case must pass retrieval before analysis counts, and analysis
      before explanation). Top border colour: green ≥ 80%, amber ≥ 50%,
      red below 50%.</li>
  <li><strong>Coverage tier</strong> — how thoroughly the cell is tested
      (see below). It says nothing about agent quality; a cell can score
      100% while barely tested, or 60% with excellent coverage.</li>
  <li><strong>n</strong> — number of cases in the run.</li>
</ul>
<p class="meta">The tier rolls up two sub-scores:
<strong>prompt coverage</strong> (share of the cell's permutation manifest —
intent subtypes × parameters × AOI types × date expressions × languages ×
phrasings — covered by at least one case) and <strong>surface coverage</strong>
(evaluator checks wired and running for the cell / checks mapped as
applicable in the coverage roadmap).</p>
<table class="detail"><thead><tr><th>tier</th><th>provisional definition</th></tr></thead>
<tbody>{tier_rows}</tbody></table>
</details>"""


def _cell_detail_html(cell: dict, run: dict) -> str:
    slug = _slug(cell)
    anchor = f"{slug}--{cell['intent']}"
    quality = cell["quality"]
    coverage = cell["coverage"]

    stages = "".join(
        f"<tr><td>{_bucket_chip(key) if key in _BUCKET_ORDER else label}</td>"
        f"<td>{_pct(quality[key])}</td></tr>"
        for label, key in (
            ("Retrieval", "retrieval"),
            ("Analysis", "analysis"),
            ("Explanation", "explanation"),
            ("End-to-end", "e2e_pass_rate"),
        )
    )
    evaluators = "".join(
        f"<tr><td>{_bucket_chip(SCORE_FIELD_BUCKETS.get(field))}</td>"
        f"<td>{html.escape(field)}</td><td>{_pct(rate)}</td></tr>"
        for field, rate in sorted(
            cell["per_evaluator"].items(),
            key=lambda kv: (
                _BUCKET_ORDER.get(SCORE_FIELD_BUCKETS.get(kv[0], ""), 3),
                kv[0],
            ),
        )
    )
    failures = [c for c in cell["cases"] if c.get("failed_stage")]
    failure_rows = "".join(
        f"<tr><td>{html.escape(c['test_id'])}</td>"
        f"<td>{html.escape(c.get('eval_subtype') or '')}</td>"
        f"<td>{html.escape(c['failed_stage'])}</td>"
        f"<td>{html.escape((c.get('failure_comment') or '')[:400])}</td>"
        f"<td>{_link(c.get('app_thread_url'), 'thread')} "
        f"{_link(c.get('trace_url'), 'trace')}</td></tr>"
        for c in failures
    )
    failures_html = (
        f'<table class="detail"><thead><tr><th>case</th><th>subtype</th>'
        f"<th>failed stage</th><th>comment</th><th>links</th></tr></thead>"
        f"<tbody>{failure_rows}</tbody></table>"
        if failures
        else "<p>No failing cases.</p>"
    )

    return f"""
<section class="cell-detail" id="{anchor}">
  <h3>{html.escape(slug)} × {html.escape(cell["intent"])}</h3>
  <p class="meta">from run {html.escape(run["run_id"])}
     · {html.escape(run["timestamp"][:16])}
     · env {html.escape(run["environment"])}
     · profile {html.escape(run["agent_profile"])}</p>
  <p>coverage: prompt {_pct(coverage["prompt"])}, surface {_pct(coverage["surface"])},
     tier <span class="tier" style="background:{_TIER_COLOURS[coverage["tier"]]}">{coverage["tier"]}</span>
     · {cell["n_cases"]} cases</p>
  <div class="cols">
    <table class="detail"><thead><tr><th>stage</th><th>pass rate</th></tr></thead>
      <tbody>{stages}</tbody></table>
    <table class="detail"><thead><tr><th>bucket</th><th>evaluator score</th>
      <th>pass rate</th></tr></thead>
      <tbody>{evaluators}</tbody></table>
  </div>
  <h4>Failing cases ({len(failures)})</h4>
  {failures_html}
</section>"""


def _link(url: str | None, label: str) -> str:
    if not url:
        return ""
    return f'<a href="{html.escape(url)}">{label}</a>'


def _history_html(runs: list[dict]) -> str:
    if len(runs) < 1:
        return ""
    all_keys = sorted(
        {_cell_key(c) for run in runs for c in run["cells"]},
    )
    sections = []
    for slug, intent in all_keys:
        rows = []
        previous_rate = None
        previous_methodology = None
        for run in runs:
            cell = next(
                (c for c in run["cells"] if _cell_key(c) == (slug, intent)),
                None,
            )
            if cell is None:
                continue
            rate = cell["quality"]["e2e_pass_rate"]
            methodology = run["methodology_version"]
            delta = ""
            if previous_rate is not None and rate is not None:
                if previous_methodology != methodology:
                    delta = "methodology break"
                else:
                    diff = rate - previous_rate
                    delta = f"{diff:+.0%}"
            rows.append(
                f"<tr><td>{html.escape(run['timestamp'][:16])}</td>"
                f"<td>{html.escape(run['environment'])}</td>"
                f"<td>{html.escape(methodology)}</td>"
                f"<td>{html.escape(run['case_set_version'])}</td>"
                f"<td>{cell['n_cases']}</td>"
                f"<td>{_pct(rate)}</td><td>{delta}</td></tr>",
            )
            previous_rate = rate
            previous_methodology = methodology
        sections.append(
            f"<h3>{html.escape(slug)} × {html.escape(intent)}</h3>"
            f'<table class="detail"><thead><tr><th>run</th><th>env</th>'
            f"<th>methodology</th><th>case set</th><th>n</th><th>e2e</th>"
            f"<th>Δ vs previous</th></tr></thead><tbody>{''.join(rows)}</tbody></table>",
        )
    return "".join(sections)


_CSS = """
body { font-family: -apple-system, "Segoe UI", sans-serif; margin: 2rem auto;
       max-width: 1100px; color: #1c2733; padding: 0 1rem; }
h1 { font-size: 1.5rem; } h2 { margin-top: 2.5rem; }
table { border-collapse: collapse; margin: 1rem 0; }
th, td { padding: 0.45rem 0.7rem; text-align: left; font-size: 0.85rem; }
.matrix th, .matrix td { border: 1px solid #d6dbe1; text-align: center; }
.matrix tbody th { text-align: left; font-size: 0.78rem; max-width: 13rem;
                   overflow-wrap: anywhere; }
.matrix td.cell { min-width: 5.2rem; background: #fbfcfd; }
.matrix td.empty { color: #b0b7bf; background: #f4f5f7; font-size: 0.7rem; }
.matrix a { text-decoration: none; color: inherit; }
.legend { margin: 1rem 0; }
.legend summary { cursor: pointer; font-size: 0.9rem; color: #4c5763; }
.legend ul { padding-left: 1.2rem; }
.tier { color: white; border-radius: 3px; padding: 0.05rem 0.4rem;
        font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em; }
.n { color: #6b7681; font-size: 0.75rem; }
.detail { border: 1px solid #d6dbe1; } .detail th { background: #f4f5f7; }
.detail td, .detail th { border: 1px solid #e3e7eb; vertical-align: top; }
.cols { display: flex; gap: 2rem; flex-wrap: wrap; }
.meta { color: #4c5763; font-size: 0.85rem; line-height: 1.6; }
.cell-detail { border-top: 1px solid #d6dbe1; padding-top: 1rem; margin-top: 1.5rem; }
"""


def render_scorecard(runs: list[dict]) -> str:
    """Render the full scorecard HTML from run summaries (oldest first)."""
    latest = runs[-1]
    merged = _latest_cells(runs)
    row_order = {slug: i for i, slug in enumerate(DATASET_SLUGS.values())}
    details = "".join(
        _cell_detail_html(cell, run)
        for (slug, intent), (cell, run) in sorted(
            merged.items(),
            key=lambda kv: (row_order.get(kv[0][0], len(row_order)), kv[0]),
        )
    )
    non_matrix = latest.get("non_matrix_results") or 0
    non_matrix_note = (
        f"<p class='meta'>{non_matrix} non-matrix results (no intent tag) "
        "in the latest run are excluded from the grid.</p>"
        if non_matrix
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>GNW eval scorecard</title><style>{_CSS}</style></head><body>
<h1>GNW eval scorecard (internal)</h1>
<p class="meta">
latest run <strong>{html.escape(latest["run_id"])}</strong>
· {html.escape(latest["timestamp"][:16])}
· env <strong>{html.escape(latest["environment"])}</strong>
· profile <strong>{html.escape(latest["agent_profile"])}</strong>
· methodology <strong>{html.escape(latest["methodology_version"])}</strong>
· case set <strong>{html.escape(latest["case_set_version"])}</strong>
· judge {html.escape(latest["judge_model"])}
· trials {latest["num_trials"]}
· harness sha {html.escape(latest["gnw_evals_sha"])}
</p>
<h2>Matrix: intent × dataset</h2>
<p class="meta">Every catalog dataset × every taxonomy intent. Evaluated
cells show the most recent official result for that cell across all runs;
grey cells have no eval coverage yet.</p>
{_matrix_html(runs)}
{_legend_html()}
{non_matrix_note}
<h2>Cell drill-down (latest result per cell)</h2>
{details}
<h2>History</h2>
<p class="meta">Pass rates are comparable only within a methodology version;
version changes are marked instead of showing a delta.</p>
{_history_html(runs)}
</body></html>"""


@click.command()
@click.option(
    "--runs-dir",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Directory of run summary JSON files (default: repo runs/)",
)
def main(runs_dir: Path | None) -> None:
    """Render runs/scorecard.html from the committed run summaries."""
    target_dir = runs_dir or RUNS_DIR
    runs = _load_runs(target_dir)
    if not runs:
        raise click.ClickException(f"no run summaries in {target_dir}")
    output = target_dir / "scorecard.html"
    output.write_text(render_scorecard(runs))
    print(f"Scorecard written to: {output} ({len(runs)} runs)")


if __name__ == "__main__":
    main()
