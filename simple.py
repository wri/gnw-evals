import marimo

__generated_with = "0.19.9"
app = marimo.App(width="medium")

with app.setup(hide_code=True):
    import marimo as mo
    import numpy as np
    import os

    import pandas as pd
    import altair as alt


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Global Nature Watch offline LLM evaluations

    This notebook examines results from a single run of GNW LLM evals.

    Experts have prepared queries and corresponding correct ("expected") answers. The purpose of these offline evals is to ensure the LLM responses ("actual"). The prepared Q&A pairs are in this spreadsheet: [GNW eval sets](https://docs.google.com/spreadsheets/d/1_G1aq2fSCPqhT6w55_Od6VU7sov76t1lHQTBeZZxbdM/edit?usp=sharing)
    """)
    return


@app.cell
def _():
    eval_results_dir = "outputs/"

    source_file_name_simple = "combined_20260212_205134_summary.csv"
    source_file_name_detailed = "combined_20260212_205134_detailed.csv"
    return eval_results_dir, source_file_name_detailed, source_file_name_simple


@app.cell
def _():
    # sorted(os.listdir(eval_results_dir))
    return


@app.cell(hide_code=True)
def _(eval_results_dir, source_file_name_simple):
    _eval_path = os.path.join(eval_results_dir, source_file_name_simple)
    print (f"Loading {_eval_path}")

    results_simple = pd.read_csv(_eval_path)

    # add an id column
    results_simple = results_simple.reset_index(drop=True)
    results_simple["idx"] = results_simple.index
    return (results_simple,)


@app.cell(hide_code=True)
def _(results_simple):
    score_map = {
        "agent_answer_score": "Agent Answer",
        "charts_answer_score": "Charts Answer",
        "aoi_id_match_score": "AOI GADM ID Match",
        "subregion_match_score": "AOI Subregion Match",
        "dataset_id_match_score": "Dataset ID Match",
        "date_match_score": "Date Match",
        "context_layer_match_score": "Context Layer Match",
        "data_pull_exists_score": "Data Pull Exists",
        #"clarification_requested_score": "Clarification Requested",
    }

    # Keep explicit ordering (and only columns that actually exist in df)
    score_cols = [c for c in score_map.keys() if c in results_simple.columns]

    df_score_cols = [c for c in results_simple.columns if 'score' in c]

    # Current approach will fail for non-binary values
    # Include this as reminder

    vals = results_simple[score_cols].to_numpy().ravel()
    vals = vals[~np.isnan(vals)]  # drop NaNs

    assert np.isin(vals, [0, 1]).all(), "Non-binary values detected in score columns"

    print (f"The following columns are not being visualized: {[c for c in df_score_cols if c not in score_cols]}")
    return score_cols, score_map


@app.cell
def _():
    mo.md("""
    ## Average Scores
    """)
    return


@app.cell
def _(results_simple, score_cols, score_map):
    #results_simple
    means = results_simple[score_cols].rename(columns=score_map).mean()
    means.apply(lambda v: np.around(v, 2) or np.nan).rename_axis("Score").rename({"value": "mean"})
    return


@app.cell(hide_code=True)
def _(results_simple, score_cols, score_map):
    # Average of each score
    print ("Average Scores")
    print ("-----")
    for s in score_cols: 
        stext = score_map[s] + " score"
        print(f"{stext:<30} :  {results_simple[s].mean():0.2f}")

    #results_simple[score_cols].mean()
    return


@app.cell(hide_code=True)
def _(results_simple, score_cols, score_map):
    # create an id as there is none in the CSV
    df2 = results_simple.reset_index(drop=True).copy()
    df2["idx"] = df2.index

    # Long form 
    long = df2.melt(id_vars="idx", value_vars=score_cols, var_name="score", value_name="value")
    long["state"] = long["value"].map({1: "pass", 0: "fail"}).fillna("missing")

    # Add human-readable label for the x axis + tooltip
    long["score_label"] = long["score"].map(score_map).fillna(long["score"])
    return df2, long


@app.cell(hide_code=True)
def _(df2, long, score_cols, score_map):
    # create basic heatmap
    heatmap = (
        alt.Chart(long)
        .mark_rect()
        .encode(
            x=alt.X(
                "score_label:N",
                sort=[score_map[c] for c in score_cols],
                title=None,
                axis=alt.Axis(
                    orient="top",
                    labelAngle=-35,
                    labelPadding=4
                ),
            ),
            y=alt.Y(
                "idx:N",
                sort="ascending",
                title=None,
                axis=alt.Axis(labels=False, ticks=False, domain=False)  # (1) hide row tick labels
            ),
            color=alt.Color(
                "state:N",
                scale=alt.Scale(
                    domain=["pass", "fail", "missing"],
                    range=["#7aa37a", "#c26a6a", "#e6e6e6"],  # muted green/red + neutral grey
                ),
                legend=None
            ),
            tooltip=[
                alt.Tooltip("idx:Q", title="Test idx"),
                alt.Tooltip("score_label:N", title="Score"),
                alt.Tooltip("state:N", title="Result"),
                #alt.Tooltip("value:Q", title="Raw value"),
                #alt.Tooltip("fail_count:Q", title="Total fails in this test"),
                #alt.Tooltip("missing_count:Q", title="Missing in test"),
                #alt.Tooltip("failed_scores:N", title="Failed scores"),
                #alt.Tooltip("missing_scores:N", title="Missing scores"),
            ],
        )
        .properties(width=25 * len(score_cols), height=12 * df2.shape[0])
    )

    # This is the basic (non-interactive) heatmap
    # commented out
    # heatmap
    return (heatmap,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Heatmap
    """)
    return


@app.cell(hide_code=True)
def _(heatmap, interpretation):
    # make interactive heatmap with clickable selection

    # Define single-cell click selection (captures idx + score)
    cell = alt.selection_point(
        fields=["idx", "score"],   # or ["idx","score_label"] if you prefer
        on="click",
        clear="dblclick"           # optional: double-click clears
    )

    heatmap_clickable = heatmap.add_params(cell).encode(
        # emphasize selected cell(s)
        opacity=alt.condition(cell, alt.value(1.0), alt.value(0.55))
    )

    clickable_heatmap = mo.ui.altair_chart(heatmap_clickable, chart_selection=False, legend_selection=False)

    mo.hstack([
        clickable_heatmap,
        interpretation],
             widths='equal'
             )
    return (clickable_heatmap,)


@app.cell(hide_code=True)
def _(clickable_heatmap):
    selected = clickable_heatmap.value   # a DataFrame of selected points
    selected_idx = None if selected.empty else selected.iloc[0]["idx"]
    selected_score = None if selected.empty else selected.iloc[0]["score"]
    return selected, selected_idx, selected_score


@app.cell(hide_code=True)
def _(score_map, selected, selected_idx, selected_score):
    mo.stop(selected.empty)

    mo.md(f"""
    You have selected **{score_map[selected_score]} score** for eval **test #{selected_idx}**.
    Details below.
    """)
    return


@app.cell
def _():
    return


@app.cell(hide_code=True)
def _(
    get_columns,
    render_diagnostic_table,
    results_detailed,
    score_map,
    selected,
    selected_idx,
    selected_score,
):
    mo.stop(selected.empty)

    _show_cols = get_columns(selected_score)
    _show_cols = [c for c in _show_cols if c in results_detailed.columns]

    # combine selection with dataframe from the "detailed" CSV
    diagnostic_info = results_detailed.iloc[[selected_idx]][_show_cols]

    # Rener this diagnostic info in a table with markdown support
    render_diagnostic_table(diagnostic_info, title=f"Diagnostic: {score_map[selected_score]} score", subtitle=f"for eval test #{selected_idx}")
    return


@app.cell(hide_code=True)
def _():
    # print the dataframe without the fancy table
    # commented out
    #diagnostic_info
    return


@app.cell(hide_code=True)
def _(eval_results_dir, source_file_name_detailed):
    _eval_path = os.path.join(eval_results_dir, source_file_name_detailed)
    print (f"Loading {_eval_path}")

    results_detailed = pd.read_csv(_eval_path)

    # add an id column
    results_detailed = results_detailed.reset_index(drop=True)
    results_detailed["idx"] = results_detailed.index
    return (results_detailed,)


@app.cell(hide_code=True)
def _():
    # columns to show for each score
    score_to_columns = {
        "date_match_score": [
            "expected_start_date",
            "actual_start_date",
            "expected_end_date",
            "actual_end_date",
            "date_match_score",
            "date_success",
        ],
        "aoi_id_match_score": [
            "expected_aoi_ids",
            "match_aoi_id",
            "actual_id",
            "aoi_id_match_score",
        ],
        "subregion_match_score": [
            "expected_subregion",
            "actual_subregion",
            "match_subregion",
            "subregion_match_score",
        ],
        "dataset_id_match_score": [
            "expected_dataset_id",
            "actual_dataset_id",
            "expected_dataset_name",
            "actual_dataset_name",
            "dataset_id_match_score",
        ],
        "context_layer_match_score": [
            "expected_context_layer",
            "actual_context_layer",
            "context_layer_match_score",
        ],
        "charts_answer_score": [
            "expected_answer",
            "actual_charts_answer",
            "charts_answer_score",
        ],
        "agent_answer_score": [
            "expected_answer",
            "expected_agent_answer",
            "actual_agent_answer",
            "agent_answer_score",
        ],
        "data_pull_exists_score": [
            "data_pull_exists_score",
            "row_count",
            "data_pull_success",
        ],
        "clarification_requested_score": [
            "expected_clarification",
            "clarification_requested_score",
        ],
    }
    base_cols = [
        "query", 
        "trace_url", 
        #"overall_score", 
        #"error"
    ]


    def get_columns(score: str):
        cols = score_to_columns.get(score, [])
        cols = base_cols + cols
        return cols

    return (get_columns,)


@app.cell(hide_code=True)
def _(selected_score):
    # render table nicely with Great Tables
    from great_tables import GT, loc, style

    def render_diagnostic_table(diag_df: pd.DataFrame, title="Score Diagnostic", subtitle="abs"):
        """
        diag_df: transposed selection df (rows=fields, cols=1 eval column)
        """
        df_kv = diag_df.copy()

        # Convenience modifications to the diagnostic dataframe
        df_kv["result"] = df_kv[selected_score].map({1: "PASS", 0: "FAIL"}).fillna("missing")
        df_kv["query"] = '"' + df_kv["query"].astype(str) + '"'

        # important! Transpose 
        df_kv = df_kv.T

        value_col = df_kv.columns[0]

        # Turn index into a real column
        df_kv = df_kv.reset_index().rename(columns={"index": "Field", value_col: "Value"})

        # Make trace_url clickable; keep full url in the cell but show "trace"
        if "trace_url" in df_kv["Field"].values:
            mask = df_kv["Field"].eq("trace_url")
            urls = df_kv.loc[mask, "Value"].astype(str)
            _trace_id = (urls.values[-1].split('/')[-1])

            df_kv.loc[mask, "Value"] = urls.map(lambda u: f"[Langfuse trace {_trace_id}]({u})")

        gt = (
            GT(df_kv)
            .tab_header(title=title, subtitle=subtitle)
            #.cols_label(Field="Field", Value="Value")
            .cols_width(cases={"Field": "150px", "Value": "800px"})  # tune as needed

            # Render markdown for answer and enable link with [trace](url)
            .fmt_markdown(columns="Value")

            .tab_options(column_labels_hidden=True)

            # Wrap long content instead of clipping (whitespace controls wrapping behavior)
            .tab_style(
                style=style.text(whitespace="pre-wrap"),
                locations=loc.body(columns="Value"),
            )

                # Optional: make Field column visually “label-ish”
            .tab_style(
                style=style.text(size="0.8rem",),
                locations=loc.body(columns="Field"),
            )
        )

        # highlight query row
        gt = gt.tab_style(
            style=[
                style.fill(color="#f3f3f3"),  # light gray
                style.text(
                    #weight="bold", 
                    #size="1.5rem"
                ),
            ],
            locations=loc.body(
                rows=lambda d: d["Field"].eq("query"),
                columns=["Field", "Value"],
            ),
        )

        # highlight score 
        gt = gt.tab_style(
            style=[
                #style.fill(color="#f3f3f3"),  # light gray
                style.text(
                    weight="bold", 
                    size="1.5rem"
                ),
            ],

            locations=loc.body(
                rows=lambda d: d["Field"].str.contains("result", case=False, na=False),
                columns=["Value"],
            ),
        )

        return gt

    return (render_diagnostic_table,)


@app.cell(hide_code=True)
def _():
    interpretation=mo.md("""
    ### How to read this chart:

    **Each row reprents one eval test query.** <br>
    If 50 tests were run, the heatmap will be 50 units tall.

    **Each column reprents an eval score**<br>
    For each score, the correct "expected" value is compared to GNW's "actual" response.
    If no expected value is available, the score is not computed.

    **Each cell represents a result.**<br>
    Red/Green indicates passing or failing score.

    **This heatmap is interactive.**<br>
    Click on a cell to see the expected and actual values.
    """)
    return (interpretation,)


if __name__ == "__main__":
    app.run()
