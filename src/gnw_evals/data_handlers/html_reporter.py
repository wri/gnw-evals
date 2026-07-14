"""Self-contained HTML report for an eval run.

Written alongside the CSV outputs for every run. Sections degrade gracefully:
ground-truth blocks (intent tiles, intent x subtype grid) only render when the
run contains ground-truth cases; the failures section and per-case table cover
every run. No external assets: inline CSS, light and dark via
prefers-color-scheme, stdlib only.
"""

import ast
import html
from datetime import datetime
from pathlib import Path
from typing import Any

from gnw_evals.evaluators.utils import normalize_gadm_id
from gnw_evals.utils.eval_types import TestResult

_OVERALL_SCORE_FIELD = "overall_score"

_CSS = """
:root {
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e;
  --muted: #898781; --grid: #e1e0d9; --border: rgba(11,11,11,0.10);
  --series-1: #2a78d6; --good: #0ca30c; --good-text: #006300;
  --critical: #d03b3b; --warning: #fab219;
}
@media (prefers-color-scheme: dark) {
  :root {
    --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink-2: #c3c2b7;
    --muted: #898781; --grid: #2c2c2a; --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --good-text: #0ca30c;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--page); color: var(--ink);
  font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
}
main { max-width: 1080px; margin: 0 auto; padding: 24px 20px 48px; }
h1 { font-size: 20px; margin: 0 0 4px; }
h2 { font-size: 15px; margin: 28px 0 10px; }
.meta { color: var(--ink-2); font-size: 13px; }
.meta span + span::before { content: " \\00b7 "; color: var(--muted); }
.tiles { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 16px; }
.tile {
  flex: 1 1 150px; background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px 14px;
}
.tile .label { color: var(--ink-2); font-size: 12px; }
.tile .value { font-size: 26px; font-weight: 650; margin-top: 2px; }
.tile .sub { color: var(--muted); font-size: 12px; }
.tablewrap { overflow-x: auto; background: var(--surface);
  border: 1px solid var(--border); border-radius: 8px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { text-align: left; padding: 7px 10px; vertical-align: top;
  border-top: 1px solid var(--grid); }
thead th { border-top: none; color: var(--ink-2); font-weight: 600;
  font-size: 12px; white-space: nowrap; }
td.num, th.num { font-variant-numeric: tabular-nums; white-space: nowrap; }
.meter { display: inline-flex; align-items: center; gap: 8px; min-width: 130px; }
.meter .track { width: 72px; height: 8px; border-radius: 4px;
  background: var(--grid); overflow: hidden; flex: none; }
.meter .fill { height: 100%; border-radius: 0 4px 4px 0;
  background: var(--series-1); }
.badge { display: inline-flex; align-items: center; gap: 5px;
  padding: 1px 8px; border-radius: 999px; font-size: 12px; font-weight: 600;
  border: 1px solid var(--border); white-space: nowrap; }
.badge .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
td.param .sel { font-size: 12px; }
td.param .sel.same { color: var(--muted); }
td.param .sel.diff { color: var(--critical); font-weight: 600; }
p.legend { color: var(--muted); font-size: 12px; margin: 4px 0 8px; }
.badge.pass .dot { background: var(--good); }
.badge.fail .dot { background: var(--critical); }
.badge.na { color: var(--muted); }
.query { color: var(--ink-2); max-width: 420px; }
.card { background: var(--surface); border: 1px solid var(--border);
  border-left: 3px solid var(--critical); border-radius: 8px;
  padding: 12px 14px; margin: 10px 0; }
.card .id { font-weight: 650; }
.card .q { color: var(--ink-2); margin: 4px 0 8px; }
.card dl { margin: 0; display: grid; grid-template-columns: 150px 1fr;
  gap: 3px 12px; font-size: 13px; }
.card dt { color: var(--muted); }
.card dd { margin: 0; }
a { color: var(--series-1); text-decoration: none; }
a:hover { text-decoration: underline; }
details summary { cursor: pointer; color: var(--ink-2); font-size: 12px; }
.footnote { color: var(--muted); font-size: 12px; margin-top: 24px; }
"""


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _check_scores(result: TestResult) -> list[tuple[str, float]]:
    return [
        (field, value)
        for field, value in result.model_dump().items()
        if field.endswith("_score")
        and field != _OVERALL_SCORE_FIELD
        and value is not None
    ]


def _case_failed(result: TestResult) -> bool:
    if result.error:
        return True
    return any(score < 1.0 for _, score in _check_scores(result))


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _score_values(results: list[TestResult], field: str) -> list[float]:
    return [v for r in results if (v := getattr(r, field)) is not None]


def _fmt_rate(rate: float | None) -> str:
    return "n/a" if rate is None else f"{rate * 100:.0f}%"


def _meter(rate: float | None, *, std: float | None = None) -> str:
    if rate is None:
        return '<span class="badge na">n/a</span>'
    width = max(0.0, min(1.0, rate)) * 100
    label = f"{rate * 100:.0f}%"
    if std:
        label += f" &plusmn; {std * 100:.0f}"
    return (
        f'<span class="meter"><span class="track">'
        f'<span class="fill" style="width:{width:.0f}%"></span></span>'
        f'<span class="num">{label}</span></span>'
    )


def _score_badge(score: float | None, *, reason: str | None = None) -> str:
    if score is None:
        return '<span class="badge na">n/a</span>'
    title = f' title="{_esc(reason)}"' if reason else ""
    if score >= 1.0:
        return f'<span class="badge pass"{title}><span class="dot"></span>pass</span>'
    if score <= 0.0:
        return f'<span class="badge fail"{title}><span class="dot"></span>fail</span>'
    return (
        f'<span class="badge"{title}><span class="dot" '
        f'style="background:var(--warning)"></span>{score:.2f}</span>'
    )


def _header_html(results: list[TestResult], run_meta: dict | None) -> str:
    run_meta = run_meta or {}
    num_trials = max((r.num_trials for r in results), default=1)
    parts = [
        f"<span>{_esc(run_meta.get('api_base_url', 'unknown API'))}</span>",
        f"<span>{datetime.now().strftime('%Y-%m-%d %H:%M')}</span>",
        f"<span>{len(results)} cases</span>",
    ]
    if num_trials > 1:
        parts.append(f"<span>{num_trials} trials per case (scores are means)</span>")
    if run_meta.get("ff"):
        parts.append(f"<span>profile: {_esc(run_meta['ff'])}</span>")
    return f'<h1>GNW eval run report</h1><div class="meta">{"".join(parts)}</div>'


def _tiles_html(results: list[TestResult]) -> str:
    ground_truth = [r for r in results if r.intent]
    failed = sum(1 for r in results if _case_failed(r))
    tiles = [
        ("Cases run", str(len(results)), f"{failed} with failed checks"),
        (
            "Overall score (mean)",
            f"{_mean([r.overall_score for r in results]) or 0:.2f}",
            "all checks, all cases",
        ),
    ]
    if ground_truth:
        fidelity = _mean(_score_values(ground_truth, "data_fidelity_score"))
        usage = _mean(_score_values(ground_truth, "number_usage_score"))
        unquantified = sum(1 for r in ground_truth if r.unquantified)
        tiles += [
            ("Data fidelity", _fmt_rate(fidelity), "right numbers pulled"),
            ("Number usage", _fmt_rate(usage), "numbers used correctly"),
            (
                "Unquantified answers",
                str(unquantified),
                "correct but cited no figures",
            ),
        ]
    cells = "".join(
        f'<div class="tile"><div class="label">{_esc(label)}</div>'
        f'<div class="value">{_esc(value)}</div>'
        f'<div class="sub">{_esc(sub)}</div></div>'
        for label, value, sub in tiles
    )
    return f'<div class="tiles">{cells}</div>'


def _matrix_html(results: list[TestResult]) -> str:
    ground_truth = [r for r in results if r.intent]
    if not ground_truth:
        return ""
    groups: dict[tuple[str, str], list[TestResult]] = {}
    for result in ground_truth:
        groups.setdefault((result.intent, result.eval_subtype), []).append(result)

    rows = []
    for (intent, subtype), subset in sorted(groups.items()):
        fidelity = _mean(_score_values(subset, "data_fidelity_score"))
        usage = _mean(_score_values(subset, "number_usage_score"))
        rows.append(
            f"<tr><td>{_esc(intent)}</td><td>{_esc(subtype)}</td>"
            f'<td class="num">{len(subset)}</td>'
            f"<td>{_meter(fidelity)}</td><td>{_meter(usage)}</td></tr>",
        )
    return (
        "<h2>Quality by intent and subtype</h2>"
        '<div class="tablewrap"><table><thead><tr>'
        "<th>Intent</th><th>Subtype</th><th class='num'>Cases</th>"
        "<th>Data fidelity</th><th>Number usage</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _failure_cards_html(results: list[TestResult]) -> str:
    failing = [r for r in results if _case_failed(r)]
    if not failing:
        return "<h2>Failures</h2><p>No failing cases.</p>"

    cards = []
    for result in failing:
        detail_rows = []
        expected_params = " &middot; ".join(
            part
            for part in (
                _esc("; ".join(result.expected_aoi_ids or [])),
                _esc(_expected_years(result)),
                (
                    f"canopy {_esc(str(getattr(result, 'expected_canopy_cover', '')))}"
                    if getattr(result, "expected_canopy_cover", "")
                    else ""
                ),
                _esc(_expected_filter(result)),
            )
            if part
        )
        if expected_params:
            detail_rows.append(("expected params", expected_params))
        selected_params = " &middot; ".join(
            part
            for part in (
                _esc(
                    "; ".join(
                        normalize_gadm_id(i).upper()
                        for i in _parse_id_list(result.actual_id)
                    ),
                ),
                _esc(_year_range(result.actual_start_date, result.actual_end_date)),
                (
                    f"canopy {_esc(str(result.actual_canopy_cover))}"
                    if getattr(result, "actual_canopy_cover", None)
                    else ""
                ),
                _esc(_selected_filter(result)),
            )
            if part
        )
        if selected_params:
            detail_rows.append(("selected params", selected_params))
        if result.error:
            detail_rows.append(("run error", result.error))
        for field, score in _check_scores(result):
            if score < 1.0:
                detail_rows.append(
                    (field.removesuffix("_score").replace("_", " "), f"{score:g}"),
                )
        if result.data_fidelity_missing:
            detail_rows.append(("missing values", result.data_fidelity_missing))
        if result.number_usage_failure_comment:
            detail_rows.append(("judge comment", result.number_usage_failure_comment))
        if result.number_usage_reasoning:
            detail_rows.append(("judge reasoning", result.number_usage_reasoning))
        links = []
        if result.app_thread_url:
            links.append(f'<a href="{_esc(result.app_thread_url)}">thread</a>')
        if result.trace_url:
            links.append(f'<a href="{_esc(result.trace_url)}">trace</a>')
        if links:
            detail_rows.append(("links", " &middot; ".join(links)))

        prerendered = {"links", "expected params", "selected params"}
        dl = "".join(
            f"<dt>{_esc(label)}</dt>"
            f"<dd>{value if label in prerendered else _esc(value)}</dd>"
            for label, value in detail_rows
        )
        intent_label = (
            f" &middot; {_esc(result.intent)}/{_esc(result.eval_subtype)}"
            if result.intent
            else ""
        )
        cards.append(
            f'<div class="card"><div class="id">{_esc(result.test_id or result.thread_id)}'
            f'{intent_label}</div><div class="q">{_esc(result.query)}</div>'
            f"<dl>{dl}</dl></div>",
        )
    return f"<h2>Failures ({len(failing)})</h2>{''.join(cards)}"


def _year_range(start: str | None, end: str | None) -> str:
    start = (start or "").strip()[:4]
    end = (end or "").strip()[:4]
    if not (start or end):
        return ""
    return start if start == end else f"{start}-{end}"


def _expected_years(result: TestResult) -> str:
    return _year_range(result.expected_start_date, result.expected_end_date)


def _expected_filter(result: TestResult) -> str:
    """Combine forest filter and intersection into one spot-check column."""
    parts = [
        str(getattr(result, field, "") or "")
        for field in ("expected_forest_filter", "expected_intersections")
    ]
    return " + ".join(p for p in parts if p)


def _parse_id_list(value: Any) -> list[str]:
    """actual_id may arrive as a list or its string repr; normalise to a list."""
    if isinstance(value, list):
        return [str(v) for v in value]
    text = str(value or "").strip()
    if text.startswith("["):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        except (ValueError, SyntaxError):
            pass
    return [text] if text else []


def _selected_filter(result: TestResult) -> str:
    return str(
        getattr(result, "actual_forest_filter", None)
        or result.actual_context_layer
        or "",
    )


def _norm_param(value: str) -> str:
    """Normalise a param value for equality: lowercase, drop a '(default)' note."""
    return (value or "").split("(")[0].strip().lower()


def _pair_cell(expected: str, selected: str, *, numeric: bool = False) -> str:
    """One parameter cell: expected on top, agent-selected below."""
    css = "param num" if numeric else "param"
    if not expected and not selected:
        return f'<td class="{css}">&mdash;</td>'
    same = _norm_param(expected) == _norm_param(selected)
    return (
        f'<td class="{css}"><div>{_esc(expected) or "&mdash;"}</div>'
        f'<div class="sel {"same" if same else "diff"}">'
        f"{_esc(selected) or '&mdash;'}</div></td>"
    )


def _param_cells(result: TestResult) -> str:
    expected_aoi = "; ".join(result.expected_aoi_ids or [])
    selected_aoi = "; ".join(
        normalize_gadm_id(i).upper() for i in _parse_id_list(result.actual_id)
    )
    canopy_expected = str(getattr(result, "expected_canopy_cover", "") or "")
    canopy_selected = str(getattr(result, "actual_canopy_cover", None) or "")
    return (
        _pair_cell(expected_aoi, selected_aoi, numeric=True)
        + _pair_cell(
            _expected_years(result),
            _year_range(result.actual_start_date, result.actual_end_date),
            numeric=True,
        )
        + _pair_cell(canopy_expected, canopy_selected, numeric=True)
        + _pair_cell(_expected_filter(result), _selected_filter(result))
    )


def _cases_table_html(results: list[TestResult]) -> str:
    has_ground_truth = any(r.intent for r in results)
    rows = []
    for result in results:
        links = []
        if result.app_thread_url:
            links.append(f'<a href="{_esc(result.app_thread_url)}">thread</a>')
        if result.trace_url:
            links.append(f'<a href="{_esc(result.trace_url)}">trace</a>')
        ground_truth_cells = ""
        if has_ground_truth:
            unquantified = (
                "yes" if result.unquantified else ("no" if result.intent else "")
            )
            ground_truth_cells = (
                f"<td>{_esc(result.intent)}</td><td>{_esc(result.eval_subtype)}</td>"
                f"{_param_cells(result)}"
                f"<td>{_score_badge(result.data_fidelity_score, reason=result.data_fidelity_missing)}</td>"
                f"<td>{_score_badge(result.number_usage_score, reason=result.number_usage_reasoning)}</td>"
                f"<td>{_esc(unquantified)}</td>"
            )
        rows.append(
            f'<tr><td class="num">{_esc(result.test_id or "-")}</td>'
            f'<td class="query">{_esc(result.query)}</td>'
            f"{ground_truth_cells}"
            f'<td class="num">{result.overall_score:g}</td>'
            f'<td class="num">{"" if result.duration_seconds is None else f"{result.duration_seconds:.0f}s"}</td>'
            f"<td>{' &middot; '.join(links)}</td></tr>",
        )
    ground_truth_headers = (
        "<th>Intent</th><th>Subtype</th>"
        "<th class='num'>AOI</th><th class='num'>Years</th>"
        "<th class='num'>Canopy</th><th>Filter</th>"
        "<th>Fidelity</th><th>Usage</th><th>Unquantified</th>"
        if has_ground_truth
        else ""
    )
    legend = (
        '<p class="legend">AOI, Years, Canopy and Filter cells show the '
        "expected value on top and the agent-selected value below "
        "(highlighted when they differ).</p>"
        if has_ground_truth
        else ""
    )
    return (
        "<h2>All cases</h2>"
        f"{legend}"
        '<div class="tablewrap"><table><thead><tr>'
        f"<th>id</th><th>Query</th>{ground_truth_headers}"
        "<th class='num'>Overall</th><th class='num'>Time</th><th>Links</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def write_html_report(
    results: list[TestResult],
    base_filename: str,
    run_meta: dict | None = None,
) -> str:
    """Write the run report next to the CSV outputs; returns the file path."""
    output_dir = Path(__file__).parent.parent.parent.parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / f"{base_filename}_report.html"

    ground_truth = [r for r in results if r.intent]
    footnote = ""
    if ground_truth:
        footnote = (
            '<p class="footnote">Ground truth is fetched at run time from the '
            "same analytics API the agent queries, so these scores measure "
            "retrieval and usage fidelity (right query built, numbers used "
            "correctly), not the correctness of the underlying data. "
            "Pass tolerances: data fidelity 0.1% relative on pulled values; "
            "number usage 5% relative, unit-aware, judged by "
            "claude-haiku-4-5.</p>"
        )

    document = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>GNW eval run report</title>"
        f"<style>{_CSS}</style></head><body><main>"
        f"{_header_html(results, run_meta)}"
        f"{_tiles_html(results)}"
        f"{_matrix_html(results)}"
        f"{_failure_cards_html(results)}"
        f"{_cases_table_html(results)}"
        f"{footnote}"
        "</main></body></html>"
    )
    path.write_text(document, encoding="utf-8")
    return str(path)
