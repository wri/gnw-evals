"""Internal scorecard: static HTML rendered from committed run summaries.

Reads every ``runs/*.json`` artefact and writes ``runs/scorecard.html``:
the intent x dataset matrix (latest run), per-cell drill-down (staged-gate
buckets, per-evaluator rates, failing cases with judge comments) and the
history of e2e pass rates across runs with methodology-version markers.

Usage:
    uv run gnw_scorecard
"""

import html
import json
from pathlib import Path

import click

from gnw_evals.data_handlers.run_summary import RUNS_DIR

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

_TIER_COLOURS = {
    "minimal": "#9aa0a6",
    "partial": "#e8a33d",
    "good": "#3d9970",
    "comprehensive": "#1e6b4e",
}


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


def _cell_key(cell: dict) -> tuple[str, str]:
    return (cell["dataset_slug"], cell["intent"])


def _matrix_html(latest: dict) -> str:
    cells = {_cell_key(c): c for c in latest["cells"]}
    dataset_slugs = sorted({c["dataset_slug"] for c in latest["cells"]})
    if not dataset_slugs:
        return "<p>No matrix cells in the latest run.</p>"

    head = "".join(f"<th>{html.escape(i)}</th>" for i in INTENTS)
    body_rows = []
    for slug in dataset_slugs:
        tds = []
        for intent in INTENTS:
            cell = cells.get((slug, intent))
            if cell is None:
                tds.append('<td class="empty">–</td>')
                continue
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
    return (
        '<table class="matrix"><thead><tr><th></th>'
        f"{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
    )


def _cell_detail_html(cell: dict) -> str:
    anchor = f"{cell['dataset_slug']}--{cell['intent']}"
    quality = cell["quality"]
    coverage = cell["coverage"]

    stages = "".join(
        f"<tr><td>{label}</td><td>{_pct(quality[key])}</td></tr>"
        for label, key in (
            ("Retrieval", "retrieval"),
            ("Analysis", "analysis"),
            ("Explanation", "explanation"),
            ("End-to-end", "e2e_pass_rate"),
        )
    )
    evaluators = "".join(
        f"<tr><td>{html.escape(field)}</td><td>{_pct(rate)}</td></tr>"
        for field, rate in cell["per_evaluator"].items()
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
  <h3>{html.escape(cell["dataset_slug"])} × {html.escape(cell["intent"])}</h3>
  <p>coverage: prompt {_pct(coverage["prompt"])}, surface {_pct(coverage["surface"])},
     tier <span class="tier" style="background:{_TIER_COLOURS[coverage["tier"]]}">{coverage["tier"]}</span>
     · {cell["n_cases"]} cases</p>
  <div class="cols">
    <table class="detail"><thead><tr><th>stage</th><th>pass rate</th></tr></thead>
      <tbody>{stages}</tbody></table>
    <table class="detail"><thead><tr><th>evaluator score</th><th>pass rate</th></tr></thead>
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
.matrix td.cell { min-width: 5.2rem; background: #fbfcfd; }
.matrix td.empty { color: #b0b7bf; background: #f4f5f7; }
.matrix a { text-decoration: none; color: inherit; }
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
    details = "".join(_cell_detail_html(c) for c in latest["cells"])
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
<p class="meta">Cell shows end-to-end pass rate (staged gate), coverage tier
and case count. Grey cells have no eval coverage yet.</p>
{_matrix_html(latest)}
{non_matrix_note}
<h2>Cell drill-down (latest run)</h2>
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
