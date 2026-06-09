# /// script
# dependencies = [
#     "altair==6.1.0",
#     "great-tables==0.21.0",
#     "marimo",
#     "numpy==2.4.4",
#     "pandas==3.0.3",
#     "pyarrow==24.0.0",
# ]
# requires-python = ">=3.13"
# ///

import marimo

__generated_with = "0.23.6"
app = marimo.App(width="columns")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## GNW Longitudinal Eval Analysis

    Pass/fail results across multiple runs. Each row is a `test_id`, each column is a score.
    **Faded cells** = stable (same result across last N runs). **Vivid cells** = changed at least once.
    Toggle **"Show changed rows only"** to focus on regressions and improvements.
    Click any cell to see the run-by-run history and latest reason text.
    """)
    return


@app.cell(hide_code=True)
def _():
    import os
    import re

    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd
    from great_tables import GT, loc, style as gt_style


    return GT, alt, gt_style, loc, mo, np, os, pd, re


@app.cell
def _():
    import os as _os

    # --- Configuration ---
    _here = _os.path.dirname(_os.path.abspath(__file__))
    eval_results_dir = _os.path.normpath(_os.path.join(_here, "..", "outputs")) + _os.sep
    N_RUNS = 5  # number of recent runs to consider for change detection and pass rate

    return N_RUNS, eval_results_dir


@app.cell(hide_code=True)
def _(eval_results_dir, os, pd, re):
    # Scan outputs/eval-csv-*/ folders; load only those with test_id
    _run_records = []

    for _folder_name in sorted(os.listdir(eval_results_dir)):
        _folder_path = os.path.join(eval_results_dir, _folder_name)
        if not (os.path.isdir(_folder_path) and _folder_name.startswith("eval-csv-")):
            continue

        _csvs = [f for f in os.listdir(_folder_path) if f.endswith("_summary.csv")]
        if not _csvs:
            continue
        _csv_name = _csvs[0]
        _csv_path = os.path.join(_folder_path, _csv_name)

        with open(_csv_path) as _fh:
            _header = _fh.readline()
        if "test_id" not in _header:
            continue

        _m = re.search(r"(20\d{6}_\d{6})", _csv_name)
        _run_date = _m.group(1) if _m else _folder_name

        # Extract env from folder name: eval-csv-<env>-<id>
        _env_m = re.match(r"eval-csv-(staging|prod)-", _folder_name)
        _run_env = _env_m.group(1) if _env_m else "unknown"

        _df = pd.read_csv(_csv_path)
        _df["run_date"] = _run_date
        _df["run_folder"] = _folder_name
        _df["run_env"] = _run_env
        _run_records.append(_df)

    if _run_records:
        df_all = pd.concat(_run_records, ignore_index=True)
        print(f"Loaded {len(_run_records)} runs, {len(df_all)} total rows")
        print(f"Envs: {df_all[['run_date','run_env','run_folder']].drop_duplicates().to_string(index=False)}")
    else:
        df_all = pd.DataFrame()
        print("WARNING: No qualifying runs found")

    return (df_all,)


@app.cell(hide_code=True)
def _(eval_results_dir, os, pd, re):
    # Load detailed CSVs from the same qualifying folders (same test_id filter)
    _det_records = []

    for _folder_name in sorted(os.listdir(eval_results_dir)):
        _folder_path = os.path.join(eval_results_dir, _folder_name)
        if not (os.path.isdir(_folder_path) and _folder_name.startswith("eval-csv-")):
            continue

        _csvs = [f for f in os.listdir(_folder_path) if f.endswith("_detailed.csv")]
        if not _csvs:
            continue
        _csv_path = os.path.join(_folder_path, _csvs[0])

        # Only load if the paired summary had test_id (check detailed header too)
        with open(_csv_path) as _fh:
            _header = _fh.readline()
        if "test_id" not in _header:
            continue

        _m = re.search(r"(20\d{6}_\d{6})", _csvs[0])
        _run_date = _m.group(1) if _m else _folder_name

        _df = pd.read_csv(_csv_path)
        _df["run_date"] = _run_date
        _df["run_folder"] = _folder_name
        _det_records.append(_df)


    if _det_records:
        df_all_detailed = pd.concat(_det_records, ignore_index=True)
    else:
        df_all_detailed = pd.DataFrame()
        print("WARNING: No detailed CSV files found")

    return (df_all_detailed,)


@app.cell(hide_code=True)
def _(df_all):
    score_map = {
        "agent_answer_score": "Agent Answer",
        "charts_answer_score": "Charts Answer",
        "aoi_id_match_score": "AOI GADM ID Match",
        "subregion_match_score": "AOI Subregion Match",
        "dataset_id_match_score": "Dataset ID Match",
        "date_match_score": "Date Match",
        "context_layer_match_score": "Context Layer Match",
        "data_pull_exists_score": "Data Pull Exists",
        "dataset_parameter_match_score": "Dataset Parameters Match",
        "clarification_requested_score": "Clarification Requested",
        "expected_text_match_score": "Expected Text Match",
    }

    # Only include scores that appear in the loaded data
    score_cols = [c for c in score_map.keys() if c in df_all.columns]
    print("Score columns found:", score_cols)

    return score_cols, score_map


@app.cell(hide_code=True)
def _():
    # Per-score diagnostic columns (expected / actual / reason)
    # Used to build the longitudinal detail panel on click
    score_to_columns = {
        "agent_answer_score": [
            "agent_answer_score_reason",
            "expected_answer",
            "actual_agent_answer",
        ],
        "charts_answer_score": [
            "chart_answer_score_reason",
            "expected_answer",
            "actual_charts_answer",
        ],
        "aoi_id_match_score": [
            "expected_aoi_ids",
            "actual_id",
            "match_aoi_id",
        ],
        "dataset_id_match_score": [
            "expected_dataset_id",
            "actual_dataset_id",
            "expected_dataset_name",
            "actual_dataset_name",
        ],
        "dataset_parameter_match_score": [
            "expected_dataset_parameters",
            "actual_dataset_parameters",
        ],
        "context_layer_match_score": [
            "expected_context_layer",
            "actual_context_layer",
        ],
        "date_match_score": [
            "expected_start_date",
            "actual_start_date",
            "expected_end_date",
            "actual_end_date",
            "date_success",
        ],
        "data_pull_exists_score": [
            "row_count",
            "data_pull_success",
        ],
        "clarification_requested_score": [
            "expected_clarification",
            "actual_clarification_requested",
        ],
        "expected_text_match_score": [
            "expected_text_match_score_reason",
            "expected_text",
            "actual_agent_answer",
        ],
    }

    # Columns always shown regardless of score
    _detail_base_cols = ["run_date", "trace_url", "execution_time", "error"]

    def get_detail_cols(score: str) -> list[str]:
        """Return the columns to pull from df_all_detailed for a given score."""
        score_specific = score_to_columns.get(score, [score])
        return _detail_base_cols + [score] + [c for c in score_specific if c != score]


    return (get_detail_cols,)


@app.cell
def _(df_all, mo, score_cols, score_map):
    _eval_sets = sorted(df_all["eval_set"].dropna().unique().tolist())
    _default_set = "gold" if "gold" in _eval_sets else _eval_sets[0]

    eval_set_ui = mo.ui.dropdown(
        options=_eval_sets,
        value=_default_set,
        label="Eval set",
    )

    _envs_available = sorted(df_all["run_env"].dropna().unique().tolist())
    env_ui = mo.ui.radio(
        options=["any"] + _envs_available,
        value="any",
        label="Environment",
        inline=True,
    )

    _default_scores = [
        "agent_answer_score",
        "charts_answer_score",
        "dataset_id_match_score",
        "date_match_score",
        "data_pull_exists_score",
    ]
    # options: label -> key so .value returns keys
    _score_options = {v: k for k, v in score_map.items() if k in score_cols}
    score_select_ui = mo.ui.multiselect(
        options=_score_options,
        value=[score_map[k] for k in _default_scores if k in score_cols],
        label="Scores to display",
    )

    show_changed_ui = mo.ui.switch(
        value=False,
        label="Show changed rows only",
    )

    mo.hstack([eval_set_ui, env_ui], gap=2),

    return env_ui, eval_set_ui, score_select_ui, show_changed_ui


@app.cell(hide_code=True)
def _(N_RUNS, df_all, env_ui, eval_set_ui):
    # Filter to selected eval_set and env
    df_filtered = df_all[df_all["eval_set"] == eval_set_ui.value].copy()

    if env_ui.value != "any":
        df_filtered = df_filtered[df_filtered["run_env"] == env_ui.value]

    # Sorted run dates (ascending); take last N
    _all_run_dates = sorted(df_filtered["run_date"].unique())
    _recent_run_dates = _all_run_dates[-N_RUNS:]

    df_recent = df_filtered[df_filtered["run_date"].isin(_recent_run_dates)].copy()


    print(f"Eval set: {eval_set_ui.value!r}  |  Env: {env_ui.value!r}")
    print(f"All run dates: {_all_run_dates}")
    print(f"Using last {N_RUNS}: {_recent_run_dates}")
    print(f"Rows in df_recent: {len(df_recent)} (long form)")

    return (df_recent,)


@app.cell(hide_code=True)
def _(df_recent, score_cols):
    # For each (test_id, score_col), changed = values not all identical across recent runs.
    # NaN (missing) counts as a distinct state: if some runs had a value and others didn't,
    # or if the numeric value itself changed, we flag it as changed.

    def _is_changed(series):
        # Treat NaN as its own category by filling with a sentinel
        filled = series.fillna(-1)
        return filled.nunique() > 1

    change_flags = (
        df_recent.groupby("test_id")[score_cols]
        .agg(_is_changed)
        .reset_index()
        .melt(id_vars="test_id", var_name="score", value_name="changed")
    )

    # test_ids that have at least one changed score
    changed_test_ids = set(
        change_flags.loc[change_flags["changed"], "test_id"]
    )
    print(f"Number of tests: {df_recent['test_id'].nunique()}")
    print(f"Tests with at least one changed score: {len(changed_test_ids)} / {df_recent['test_id'].nunique()}")

    return change_flags, changed_test_ids


@app.cell(hide_code=True)
def _(
    change_flags,
    changed_test_ids,
    df_recent,
    np,
    pd,
    score_cols,
    score_map,
    score_select_ui,
    show_changed_ui,
):
    # Scores selected by the shared multiselect
    selected_score_cols = [k for k in score_cols if k in score_select_ui.value]

    # Build df_latest: one row per test_id using the most recent run it appeared in.
    latest_run_date = sorted(df_recent["run_date"].unique())[-1]

    _all_tids = sorted(df_recent["test_id"].unique())
    _latest_rows = []
    for _tid in _all_tids:
        _tid_runs = df_recent[df_recent["test_id"] == _tid].sort_values("run_date")
        _in_latest = _tid_runs[_tid_runs["run_date"] == latest_run_date]
        _row = _in_latest.iloc[[0]] if len(_in_latest) else _tid_runs.iloc[[-1]]
        _latest_rows.append(_row)

    df_latest = pd.concat(_latest_rows, ignore_index=True)

    _missing_from_latest = set(_all_tids) - set(
        df_recent.loc[df_recent["run_date"] == latest_run_date, "test_id"]
    )
    if _missing_from_latest:
        print(f"Test IDs not in latest run (showing last known): {sorted(_missing_from_latest)}")

    # Melt to long form using selected_score_cols only
    long_latest = df_latest.melt(
        id_vars=["test_id", "run_date"],
        value_vars=selected_score_cols,
        var_name="score",
        value_name="value",
    )

    long_latest["state"] = long_latest["value"].map({1.0: "pass", 0.0: "fail"}).fillna("missing")
    long_latest["score_label"] = long_latest["score"].map(score_map).fillna(long_latest["score"])

    long_latest = long_latest.merge(change_flags[["test_id", "score", "changed"]], on=["test_id", "score"], how="left")
    long_latest["changed"] = long_latest["changed"].fillna(False)

    _pass_rates = (
        df_recent.groupby("test_id")[selected_score_cols]
        .apply(lambda g: g.notna().sum().where(g.notna().sum() > 0, other=np.nan).rdiv(g.sum()))
        .reset_index()
        .melt(id_vars="test_id", var_name="score", value_name="pass_rate")
    )
    _run_counts = (
        df_recent.groupby("test_id")[selected_score_cols]
        .apply(lambda g: g.notna().sum())
        .reset_index()
        .melt(id_vars="test_id", var_name="score", value_name="n_runs")
    )
    long_latest = long_latest.merge(_pass_rates, on=["test_id", "score"], how="left")
    long_latest = long_latest.merge(_run_counts, on=["test_id", "score"], how="left")
    long_latest["pass_rate_label"] = long_latest.apply(
        lambda r: f"{int(round(r['pass_rate'] * r['n_runs']))}/{int(r['n_runs'])} runs" if pd.notna(r["pass_rate"]) else "n/a",
        axis=1,
    )

    long_latest["opacity"] = long_latest["changed"].map({True: 1.0, False: 0.3})

    if show_changed_ui.value:
        long_latest = long_latest[long_latest["test_id"].isin(changed_test_ids)]

    print(f"Heatmap rows (long form): {len(long_latest)}, unique test_ids: {long_latest['test_id'].nunique()}")
    print(f"Latest run date: {latest_run_date} | Tests missing from latest: {len(_missing_from_latest)}")

    return df_latest, latest_run_date, long_latest, selected_score_cols


@app.cell(hide_code=True)
def _(mo, score_select_ui, show_changed_ui):
    mo.hstack([score_select_ui,  show_changed_ui], gap=15),
    return


@app.cell(hide_code=True)
def _(
    N_RUNS,
    alt,
    eval_set_ui,
    latest_run_date,
    long_latest,
    mo,
    score_map,
    selected_score_cols,
):
    _n_tests = long_latest["test_id"].nunique()
    _chart_height = min(900, 14 * _n_tests + 40)

    _heatmap = (
        alt.Chart(long_latest)
        .mark_rect()
        .encode(
            x=alt.X(
                "score_label:N",
                sort=[score_map[c] for c in selected_score_cols],
                title=None,
                axis=alt.Axis(orient="top", labelAngle=-35, labelPadding=4),
            ),
            y=alt.Y(
                "test_id:N",
                sort="ascending",
                title=None,
                axis=alt.Axis(labelFontSize=10),
            ),
            color=alt.Color(
                "state:N",
                scale=alt.Scale(
                    domain=["pass", "fail", "missing"],
                    range=["#7aa37a", "#c26a6a", "#e6e6e6"],
                ),
                legend=None,
            ),
            opacity=alt.Opacity(
                "opacity:Q",
                scale=alt.Scale(domain=[0.0, 1.0], range=[0.0, 1.0]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("test_id:N", title="Test ID"),
                alt.Tooltip("score_label:N", title="Score"),
                alt.Tooltip("state:N", title="Latest result"),
                alt.Tooltip("pass_rate_label:N", title=f"Pass rate (last {N_RUNS} runs)"),
                alt.Tooltip("changed:N", title="Changed across runs?"),
            ],
        )
        .properties(
            width=max(200, 28 * len(selected_score_cols)),
            height=_chart_height,
            title=alt.TitleParams(
                text=f"Latest run: {latest_run_date}  |  Eval set: {eval_set_ui.value}  |  Faded = stable across {N_RUNS} runs",
                fontSize=12,
                color="#666",
            ),
        )
    )

    _sel = alt.selection_point(fields=["test_id", "score"], on="click", clear="dblclick")
    _heatmap_interactive = _heatmap.add_params(_sel)

    longitudinal_chart = mo.ui.altair_chart(
        _heatmap_interactive,
        chart_selection=False,
        legend_selection=False,
    )
    longitudinal_chart

    return (longitudinal_chart,)


@app.cell(hide_code=True)
def _(longitudinal_chart):
    sel_df = longitudinal_chart.value
    selected_test_id = None if sel_df.empty else sel_df.iloc[0]["test_id"]
    selected_score = None if sel_df.empty else sel_df.iloc[0]["score"]

    return sel_df, selected_score, selected_test_id


@app.cell(hide_code=True)
def _(
    alt,
    df_latest,
    df_recent,
    mo,
    score_map,
    sel_df,
    selected_score,
    selected_test_id,
):
    mo.stop(sel_df.empty, mo.md("*Click a cell in the heatmap to see run history for that test x score.*"))

    _score_label = score_map.get(selected_score, selected_score)

    # ── Query text ────────────────────────────────────────────────────────────────
    _query_row = df_latest.loc[df_latest["test_id"] == selected_test_id, "query"]
    _query_text = _query_row.values[0] if len(_query_row) else "n/a"

    # ── Sparkline data ────────────────────────────────────────────────────────────
    spark_hist = (
        df_recent[df_recent["test_id"] == selected_test_id][["run_date", selected_score]]
        .sort_values("run_date")
        .rename(columns={selected_score: "value"})
        .copy()
    )
    spark_hist["state"] = spark_hist["value"].map({1.0: "pass", 0.0: "fail"}).fillna("missing")
    spark_hist["run_label"] = spark_hist["run_date"].str.replace(
        r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", r"\1-\2-\3 \4:\5", regex=True
    )

    # ── Clickable sparkline ───────────────────────────────────────────────────────
    _spark_sel = alt.selection_point(fields=["run_date"], on="click", clear="dblclick")

    _spark_chart = (
        alt.Chart(spark_hist)
        .mark_rect(cornerRadius=3)
        .encode(
            x=alt.X("run_label:N", sort=list(spark_hist["run_label"]),
                    title="Run (click to inspect)", axis=alt.Axis(labelAngle=-20)),
            color=alt.Color(
                "state:N",
                scale=alt.Scale(domain=["pass", "fail", "missing"], range=["#7aa37a", "#c26a6a", "#e6e6e6"]),
                legend=None,
            ),
            opacity=alt.condition(_spark_sel, alt.value(1.0), alt.value(0.45)),
            tooltip=[alt.Tooltip("run_label:N", title="Run"), alt.Tooltip("state:N", title="Result")],
        )
        .add_params(_spark_sel)
        .properties(width=max(120, 70 * len(spark_hist)), height=50, title=_score_label)
    )

    spark_chart_ui = mo.ui.altair_chart(_spark_chart, chart_selection=False, legend_selection=False)

    mo.vstack([
        mo.md(f"### Test `{selected_test_id}` — {_score_label}"),
        mo.md(f"**Query:** {_query_text}"),
        spark_chart_ui,
    ])

    return (spark_chart_ui,)


@app.cell(hide_code=True)
def _(df_recent, mo, sel_df, spark_chart_ui):
    mo.stop(sel_df.empty)

    # Default to latest run; update when user clicks a sparkline segment
    _clicked = spark_chart_ui.value
    if not _clicked.empty and "run_date" in _clicked.columns:
        selected_run_date = _clicked.iloc[0]["run_date"]
    else:
        selected_run_date = sorted(df_recent["run_date"].unique())[-1]

    print(f"Showing detail for run: {selected_run_date}")

    return (selected_run_date,)


@app.cell(hide_code=True)
def _(
    GT,
    df_all_detailed,
    eval_set_ui,
    get_detail_cols,
    gt_style,
    loc,
    mo,
    pd,
    score_map,
    sel_df,
    selected_run_date,
    selected_score,
    selected_test_id,
):
    mo.stop(sel_df.empty)

    _score_label = score_map.get(selected_score, selected_score)

    # Pull the one row for this test_id + run from detailed CSV
    _det = df_all_detailed[
        (df_all_detailed["test_id"] == selected_test_id) &
        (df_all_detailed["run_date"] == selected_run_date)
    ]
    if "eval_set" in _det.columns:
        _det = _det[_det["eval_set"] == eval_set_ui.value]

    mo.stop(_det.empty, mo.md(f"*No detailed data found for run `{selected_run_date}`*"))

    _row = _det.iloc[[0]]

    _cols = get_detail_cols(selected_score)
    _cols = [c for c in _cols if c in _row.columns and c not in ("run_date",)]

    _kv = _row[_cols].T.reset_index()
    _kv.columns = ["Field", "Value"]
    _kv["Value"] = _kv["Value"].astype(str).replace("nan", "")

    _score_val = _row[selected_score].values[0]
    _result = "PASS" if _score_val == 1.0 else ("FAIL" if _score_val == 0.0 else "missing")
    _kv = pd.concat([
        _kv,
        pd.DataFrame([{"Field": "result", "Value": _result}])
    ], ignore_index=True)

    _m = __import__("re").search(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", selected_run_date)
    _run_label = f"{_m.group(1)}-{_m.group(2)}-{_m.group(3)} {_m.group(4)}:{_m.group(5)}" if _m else selected_run_date

    if "trace_url" in _kv["Field"].values:
        _mask = _kv["Field"].eq("trace_url")
        _urls = _kv.loc[_mask, "Value"].astype(str)
        _trace_id = _urls.values[-1].split("/")[-1]
        _kv.loc[_mask, "Value"] = _urls.map(
            lambda u: f'<a href="{u}" target="_blank">Langfuse trace {_trace_id}</a>'
        )

    (
        GT(_kv)
        .tab_header(
            title=f"Diagnostic: {_score_label}",
            subtitle=f"Test {selected_test_id} — run {_run_label} — {_result}",
        )
        .cols_width(cases={"Field": "200px", "Value": "750px"})
        .fmt_markdown(columns="Value")
        .tab_options(column_labels_hidden=True)
        .tab_style(
            style=gt_style.text(whitespace="pre-wrap"),
            locations=loc.body(columns="Value"),
        )
        .tab_style(
            style=gt_style.text(size="0.8rem"),
            locations=loc.body(columns="Field"),
        )
        .tab_style(
            style=gt_style.fill(color="#f3f3f3"),
            locations=loc.body(rows=lambda d: d["Field"].eq("query"), columns=["Field", "Value"]),
        )
        .tab_style(
            style=gt_style.text(weight="bold", size="1.3rem"),
            locations=loc.body(rows=lambda d: d["Field"].eq("result"), columns=["Value"]),
        )
    )

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Variant 2 — Square Wave Sparklines

    Each cell shows the last N runs as a logic-circuit square wave.
    **Line color** = latest result (green/red/grey).
    **Opacity** = stability — vivid = changed, faded = stable.
    """)
    return


@app.cell(hide_code=True)
def _(mo, score_select_ui):
    v2_changed_only = mo.ui.switch(value=False, label="V2: Changed rows only")
    mo.hstack([score_select_ui,  v2_changed_only], gap=15),
    return (v2_changed_only,)


@app.cell(hide_code=True)
def _(
    change_flags,
    df_recent,
    score_cols,
    score_map,
    score_select_ui,
    v2_changed_only,
):
    import math

    # ---- SVG square wave generator -----------------------------------------------
    def make_wave_svg(values, w=64, h=22, stroke="#3d7a3d"):
        n = len(values)
        if n == 0:
            return f'<svg width="{w}" height="{h}"></svg>'

        seg_w = w / n
        y_high, y_low, y_mid = 4.0, 18.0, 11.0
        sw = 2.2

        def y_for(v):
            if math.isnan(v): return None
            return y_high if v == 1.0 else y_low

        solid_parts = []
        dash_parts  = []
        prev_y = None

        for i, v in enumerate(values):
            x0 = i * seg_w
            x1 = x0 + seg_w
            cy = y_for(v)

            if cy is None:
                dash_parts.append(f"M {x0:.1f},{y_mid:.1f} H {x1:.1f}")
                prev_y = None
            else:
                if prev_y is not None and prev_y != cy:
                    solid_parts.append(f"M {x0:.1f},{prev_y:.1f} V {cy:.1f}")
                elif prev_y is None:
                    solid_parts.append(f"M {x0:.1f},{cy:.1f}")
                solid_parts.append(f"H {x1:.1f}")
                prev_y = cy

        solid_d = " ".join(solid_parts)
        dash_d  = " ".join(dash_parts)
        parts = []
        if solid_d:
            parts.append(
                f'<path d="{solid_d}" stroke="{stroke}" stroke-width="{sw}" '
                f'fill="none" stroke-linecap="square"/>'
            )
        if dash_d:
            parts.append(
                f'<path d="{dash_d}" stroke="{stroke}" stroke-width="{sw}" '
                f'fill="none" stroke-dasharray="2.5,2" opacity="0.6"/>'
            )

        return (
            f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'xmlns="http://www.w3.org/2000/svg" style="display:block;">'
            + "".join(parts) + "</svg>"
        )


    # ---- Color palette -----------------------------------------------------------
    _STROKE = {"pass": "#2e6b2e", "fail": "#8b2020", "missing": "#888888"}
    _BG     = {"pass": "rgba(122,163,122,0.18)", "fail": "rgba(194,106,106,0.18)", "missing": "rgba(200,200,200,0.18)"}

    # ---- Selected scores: shared score_select_ui ---------------------------------
    v2_selected_scores = [k for k in score_cols if k in score_select_ui.value]

    # ---- Change flags scoped to selected scores ----------------------------------
    _v2_change = (
        change_flags[change_flags["score"].isin(v2_selected_scores)]
        .groupby("test_id")["changed"]
        .any()
    )
    v2_changed_ids = set(_v2_change[_v2_change].index)

    # ---- Run sequence ------------------------------------------------------------
    _run_dates = sorted(df_recent["run_date"].unique())

    # ---- Row set -----------------------------------------------------------------
    _all_test_ids = sorted(df_recent["test_id"].unique())
    _row_ids = [t for t in _all_test_ids if t in v2_changed_ids] if v2_changed_only.value else _all_test_ids

    # ---- Pivot: test_id x score -> [val per run_date] ----------------------------
    _pivot = {}
    for tid in _row_ids:
        _pivot[tid] = {}
        for sc in v2_selected_scores:
            _vals = []
            for rd in _run_dates:
                _r = df_recent[(df_recent["test_id"] == tid) & (df_recent["run_date"] == rd)]
                _v = float(_r[sc].values[0]) if len(_r) and not _r[sc].isna().values[0] else float("nan")
                _vals.append(_v)
            _pivot[tid][sc] = _vals


    # ---- Table helpers -----------------------------------------------------------
    def _latest_state(vals):
        for v in reversed(vals):
            if not math.isnan(v):
                return "pass" if v == 1.0 else "fail"
        return "missing"

    def _has_change(vals):
        seen = set()
        for v in vals:
            seen.add(v if not math.isnan(v) else "nan")
        return len(seen) > 1

    _COL_W   = 68
    _ROW_H   = 26
    _LABEL_W = 52

    # ---- Header row --------------------------------------------------------------
    _th_style = (
        "writing-mode:vertical-lr; transform:rotate(180deg); "
        "font-size:11px; font-weight:500; padding:4px 2px; "
        "white-space:nowrap; text-align:left; vertical-align:bottom; color:#444;"
    )
    _headers = "".join(
        f'<th style="{_th_style}">{score_map[sc]}</th>'
        for sc in v2_selected_scores
    )
    _header_row = f'<tr><th style="width:{_LABEL_W}px"></th>{_headers}</tr>'

    # ---- Data rows ---------------------------------------------------------------
    _data_rows = []
    for tid in _row_ids:
        _cells = [
            f'<td style="padding-right:6px; font-size:10px; color:#555; '
            f'white-space:nowrap; vertical-align:middle;">{tid}</td>'
        ]
        for sc in v2_selected_scores:
            _vals   = _pivot[tid][sc]
            _state  = _latest_state(_vals)
            _changed = _has_change(_vals)
            _opacity = "1.0" if _changed else "0.28"
            _svg    = make_wave_svg(_vals, w=_COL_W - 6, h=_ROW_H - 4, stroke=_STROKE[_state])
            _cells.append(
                f'<td style="width:{_COL_W}px; height:{_ROW_H}px; '
                f'background:{_BG[_state]}; opacity:{_opacity}; '
                f'padding:2px 3px; vertical-align:middle;">{_svg}</td>'
            )
        _data_rows.append("<tr>" + "".join(_cells) + "</tr>")

    _n_runs = len(_run_dates)
    v2_table_html = (
        '<div style="overflow-x:auto; font-family:sans-serif;">'
        '<table style="border-collapse:separate; border-spacing:2px 2px;">'
        f'<thead>{_header_row}</thead>'
        f'<tbody>{"".join(_data_rows)}</tbody>'
        '</table>'
        f'<p style="font-size:10px; color:#888; margin-top:6px;">'
        f'Showing {_n_runs} runs | Wave: oldest-to-newest left-to-right | '
        f'Vivid = changed, faded = stable'
        '</p></div>'
    )

    return v2_selected_scores, v2_table_html


@app.cell(hide_code=True)
def _(mo, v2_table_html):
    mo.Html(v2_table_html)
    return


@app.cell(hide_code=True)
def _(df_recent, mo, score_map, v2_selected_scores):
    mo.stop(len(v2_selected_scores) == 0)

    v2_detail_test = mo.ui.dropdown(
        options=sorted(df_recent["test_id"].unique().tolist()),
        value=sorted(df_recent["test_id"].unique().tolist())[0],
        label="Test ID",
    )
    v2_detail_score = mo.ui.dropdown(
        options={score_map[k]: k for k in v2_selected_scores},
        value=list({score_map[k]: k for k in v2_selected_scores}.keys())[0],
        label="Score",
    )

    mo.hstack([
        mo.md("**Inspect:**"),
        v2_detail_test,
        v2_detail_score,
    ], gap=2, align="center")

    return v2_detail_score, v2_detail_test


@app.cell(hide_code=True)
def _(
    alt,
    df_latest,
    df_recent,
    mo,
    score_map,
    v2_detail_score,
    v2_detail_test,
    v2_selected_scores,
):
    mo.stop(len(v2_selected_scores) == 0)

    # Clickable sparkline for selected test x score
    _sc = v2_detail_score.value
    _tid = v2_detail_test.value
    _score_label = score_map.get(_sc, _sc)

    _hist = (
        df_recent[df_recent["test_id"] == _tid][["run_date", _sc]]
        .sort_values("run_date")
        .rename(columns={_sc: "value"})
        .copy()
    )
    _hist["state"] = _hist["value"].map({1.0: "pass", 0.0: "fail"}).fillna("missing")
    _hist["run_label"] = _hist["run_date"].str.replace(
        r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", r"\1-\2-\3 \4:\5", regex=True
    )

    _query_row = df_latest.loc[df_latest["test_id"] == _tid, "query"]
    _query_text = _query_row.values[0] if len(_query_row) else "n/a"

    _spark_sel2 = alt.selection_point(fields=["run_date"], on="click", clear="dblclick")
    _spark2 = (
        alt.Chart(_hist)
        .mark_rect(cornerRadius=3)
        .encode(
            x=alt.X("run_label:N", sort=list(_hist["run_label"]),
                    title="Run (click to inspect)", axis=alt.Axis(labelAngle=-20)),
            color=alt.Color(
                "state:N",
                scale=alt.Scale(domain=["pass", "fail", "missing"], range=["#7aa37a", "#c26a6a", "#e6e6e6"]),
                legend=None,
            ),
            opacity=alt.condition(_spark_sel2, alt.value(1.0), alt.value(0.45)),
            tooltip=[alt.Tooltip("run_label:N", title="Run"), alt.Tooltip("state:N", title="Result")],
        )
        .add_params(_spark_sel2)
        .properties(width=max(120, 70 * len(_hist)), height=50, title=_score_label)
    )
    v2_spark_ui = mo.ui.altair_chart(_spark2, chart_selection=False, legend_selection=False)

    mo.vstack([
        mo.md(f"### Test `{_tid}` — {_score_label}"),
        mo.md(f"**Query:** {_query_text}"),
        v2_spark_ui,
    ])

    return (v2_spark_ui,)


@app.cell(hide_code=True)
def _(df_recent, mo, v2_selected_scores, v2_spark_ui):
    mo.stop(len(v2_selected_scores) == 0)

    _clicked2 = v2_spark_ui.value
    if not _clicked2.empty and "run_date" in _clicked2.columns:
        v2_selected_run_date = _clicked2.iloc[0]["run_date"]
    else:
        v2_selected_run_date = sorted(df_recent["run_date"].unique())[-1]

    return (v2_selected_run_date,)


@app.cell(hide_code=True)
def _(
    GT,
    df_all_detailed,
    eval_set_ui,
    get_detail_cols,
    gt_style,
    loc,
    mo,
    pd,
    score_map,
    v2_detail_score,
    v2_detail_test,
    v2_selected_run_date,
    v2_selected_scores,
):
    mo.stop(len(v2_selected_scores) == 0)

    _sc  = v2_detail_score.value
    _tid = v2_detail_test.value
    _score_label = score_map.get(_sc, _sc)

    _det = df_all_detailed[
        (df_all_detailed["test_id"] == _tid) &
        (df_all_detailed["run_date"] == v2_selected_run_date)
    ]
    if "eval_set" in _det.columns:
        _det = _det[_det["eval_set"] == eval_set_ui.value]

    mo.stop(_det.empty, mo.md(f"*No detailed data found for run `{v2_selected_run_date}`*"))

    _row = _det.iloc[[0]]
    _cols = get_detail_cols(_sc)
    _cols = [c for c in _cols if c in _row.columns and c != "run_date"]

    _kv = _row[_cols].T.reset_index()
    _kv.columns = ["Field", "Value"]
    _kv["Value"] = _kv["Value"].astype(str).replace("nan", "")

    _score_val = _row[_sc].values[0]
    _result = "PASS" if _score_val == 1.0 else ("FAIL" if _score_val == 0.0 else "missing")
    _kv = pd.concat([_kv, pd.DataFrame([{"Field": "result", "Value": _result}])], ignore_index=True)

    _m = __import__("re").search(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", v2_selected_run_date)
    _run_label = f"{_m.group(1)}-{_m.group(2)}-{_m.group(3)} {_m.group(4)}:{_m.group(5)}" if _m else v2_selected_run_date

    if "trace_url" in _kv["Field"].values:
        _mask = _kv["Field"].eq("trace_url")
        _urls = _kv.loc[_mask, "Value"].astype(str)
        _trace_id = _urls.values[-1].split("/")[-1]
        _kv.loc[_mask, "Value"] = _urls.map(
            lambda u: f'<a href="{u}" target="_blank">Langfuse trace {_trace_id}</a>'
        )

    (
        GT(_kv)
        .tab_header(
            title=f"Diagnostic: {_score_label}",
            subtitle=f"Test {_tid} — run {_run_label} — {_result}",
        )
        .cols_width(cases={"Field": "200px", "Value": "750px"})
        .fmt_markdown(columns="Value")
        .tab_options(column_labels_hidden=True)
        .tab_style(
            style=gt_style.text(whitespace="pre-wrap"),
            locations=loc.body(columns="Value"),
        )
        .tab_style(
            style=gt_style.text(size="0.8rem"),
            locations=loc.body(columns="Field"),
        )
        .tab_style(
            style=gt_style.fill(color="#f3f3f3"),
            locations=loc.body(rows=lambda d: d["Field"].eq("query"), columns=["Field", "Value"]),
        )
        .tab_style(
            style=gt_style.text(weight="bold", size="1.3rem"),
            locations=loc.body(rows=lambda d: d["Field"].eq("result"), columns=["Value"]),
        )
    )

    return


if __name__ == "__main__":
    app.run()
