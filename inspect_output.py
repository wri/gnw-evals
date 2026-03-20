# /// script
# dependencies = [
#     "altair==6.0.0",
#     "marimo",
#     "pandas==2.3.3",
# ]
# requires-python = ">=3.10"
# ///

import marimo

__generated_with = "0.19.6"
app = marimo.App(width="columns")


@app.cell
def _():
    import marimo as mo
    import pandas as pd

    return mo, pd


@app.cell
def _(pd):
    df_before_changes = pd.read_csv("outputs/simple_e2e_20260204_150826_detailed.csv")
    df_after_changes = pd.read_csv("outputs/gold_test_n25_20260210_115406_detailed.csv")
    return df_after_changes, df_before_changes


@app.cell
def _():
    # df.columns.to_list()
    return


@app.cell
def _(df_before_changes, keep_cols):
    _df = df_before_changes
    _display_cols = [c for c in _df.columns if c in keep_cols]
    _df[_display_cols]
    return


@app.cell
def _(df_after_changes, keep_cols):
    _df = df_after_changes
    _display_cols = [c for c in _df.columns if c in keep_cols]
    _df[_display_cols]
    return


@app.cell
def _():
    return


@app.cell
def _():
    keep_cols = [
        "query",
        # "overall_score",
        ## meta
        # "trace_url",
        # "thread_id",
        # "trace_id",
        # "execution_time",
        ## AOI ID
        # "expected_aoi_ids",
        # "actual_id",
        # "aoi_id_match_score",
        # "match_aoi_id",
        ## AOI other
        # "actual_name",
        # "expected_subregion",
        # "actual_subregion",
        # "subregion_match_score",
        # "match_subregion",
        # "actual_subtype",
        # "expected_aoi_source",
        # "actual_source",
        ## dataset
        # "expected_dataset_id",
        # "actual_dataset_id",
        # "dataset_id_match_score",
        # "expected_dataset_name",
        # "actual_dataset_name",
        # # data pull
        # "expected_context_layer",
        # "actual_context_layer",
        # "context_layer_match_score",
        # "data_pull_exists_score",
        # "row_count",
        # "data_pull_success",
        ## dates
        # "expected_start_date",
        # "actual_start_date",
        # "expected_end_date",
        # "actual_end_date",
        # "date_match_score",
        # "date_success",
        # Answer
        "expected_answer",
        "actual_charts_answer",
        "actual_answer",  # BEFORE ONLY
        "charts_answer_score",
        "actual_agent_answer",
        "agent_answer_score",
        "answer_score",  # BEFORE ONLY
        # other
        # "expected_clarification",
        # "clarification_requested_score",
        # "test_group",
        # "error"
    ]
    return (keep_cols,)


@app.cell
def _(df_before_changes):
    df_before_changes.columns
    return


@app.cell
def _(df_before_changes):
    [c for c in df_before_changes.columns if "answer" in c]
    return


@app.cell
def _(mo):
    mo.md(r"""
    scores
    AOI ID match
    datapull
    dataset ID match
    Answer match

    overall score = Sum: w_i * s_i

    Average

    eval query   [ ]    [R]   [G]  [ ]    [  ]      [ ]
    eval query   [ ]    [R]   [G]  [ ]    [  ]
    eval query   [ ]    [R]   [G]  [ ]    [  ]
    eval query   [ ]    [R]   [G]  [ ]    [  ]
    eval query   [ ]    [R]   [G]  [ ]    [  ]
    eval query   [ ]    [R]   [G]  [ ]    [  ]
    eval query   [ ]    [R]   [G]  [ ]    [  ]
    eval query   [ ]    [R]   [G]  [ ]    [  ]

    Average datapull score:
    Average answer score:

    Score:
    """)
    return


if __name__ == "__main__":
    app.run()
