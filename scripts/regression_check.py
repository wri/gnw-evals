"""Check for score regressions across recent eval runs.

Loads summary CSVs from eval-csv-* subfolders, computes a rolling pass-rate
per score type over the last N runs, and exits non-zero if any score drops
more than THRESHOLD standard deviations below its historical mean.
"""

import argparse
import os
import re
import sys

import numpy as np
import pandas as pd

SCORE_COLS = [
    "agent_answer_score",
    "charts_answer_score",
    "aoi_id_match_score",
    "dataset_id_match_score",
    "date_match_score",
    "context_layer_match_score",
    "data_pull_exists_score",
    "dataset_parameter_match_score",
    "clarification_requested_score",
    "expected_text_match_score",
]


def load_runs(
    base_dir: str,
    eval_set: str,
    min_tests: int,
) -> tuple[pd.DataFrame, list[str]]:
    """Load summary CSVs from eval-csv-* subfolders."""
    records = []
    for folder in sorted(os.listdir(base_dir)):
        folder_path = os.path.join(base_dir, folder)
        if not (os.path.isdir(folder_path) and folder.startswith("eval-csv-")):
            continue
        for root, _dirs, files in os.walk(folder_path):
            for fname in files:
                if not fname.endswith("_summary.csv"):
                    continue
                path = os.path.join(root, fname)
                m = re.search(r"(20\d{6}_\d{6})", fname)
                run_date = m.group(1) if m else folder
                df = pd.read_csv(path)
                if "test_id" not in df.columns:
                    continue
                if eval_set and "eval_set" in df.columns:
                    df = df[df["eval_set"] == eval_set]
                df["run_date"] = run_date
                records.append(df)

    if not records:
        return pd.DataFrame(), []

    df_all = pd.concat(records, ignore_index=True)
    run_sizes = df_all.groupby("run_date")["test_id"].nunique()
    full_runs = sorted(run_sizes[run_sizes >= min_tests].index.tolist())
    df_all = df_all[df_all["run_date"].isin(full_runs)]
    return df_all, full_runs


def main() -> None:
    """Run regression check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-dir", default="outputs",
        help="Directory containing eval-csv-* subfolders (default: outputs)",
    )
    parser.add_argument("--eval-set", default="gold")
    parser.add_argument("--n-runs", type=int, default=10,
                        help="Rolling window size including current run")
    parser.add_argument("--threshold", type=float, default=1.0,
                        help="Std deviations below mean to trigger failure")
    parser.add_argument("--min-tests", type=int, default=50,
                        help="Minimum tests for a run to count as full")
    args = parser.parse_args()

    df_all, full_runs = load_runs(args.base_dir, args.eval_set, args.min_tests)

    if len(full_runs) < 2:
        print(f"Not enough runs found (need ≥2, found {len(full_runs)}). Skipping check.")
        sys.exit(0)

    window = full_runs[-args.n_runs:]
    history_runs = window[:-1]
    last_run = window[-1]

    print(f"Eval set  : {args.eval_set}")
    print(f"Window    : {window[0]} → {last_run} ({len(window)} runs, threshold {args.threshold}σ)")
    print(f"Baseline  : {len(history_runs)} previous runs")
    print()

    score_cols = [c for c in SCORE_COLS if c in df_all.columns]
    pass_rates = df_all.groupby("run_date")[score_cols].mean().loc[window]

    hist = pass_rates.loc[list(history_runs)]
    latest = pass_rates.loc[last_run]

    W = 36
    print(f"{'Score':<{W}} {'mean':>6} {'std':>6} {'var':>7} {'latest':>8} {'drop/std':>9}")
    print("-" * (W + 40))

    regressions = []
    for col in score_cols:
        h = hist[col].dropna()
        c = latest[col]
        if pd.isna(c) or len(h) < 2:
            continue
        mean = h.mean()
        std = h.std()
        var = h.var()
        if std == 0 or np.isnan(std):
            drop_std = float("nan")
            flag = ""
        else:
            drop_std = (mean - c) / std
            flag = "  ⚠ REGRESSION" if drop_std > args.threshold else ""
            if drop_std > args.threshold:
                regressions.append((col, mean, std, c, drop_std))

        std_str = f"{drop_std:>9.2f}" if not np.isnan(drop_std) else f"{'n/a':>9}"
        print(f"{col:<{W}} {mean:>6.3f} {std:>6.3f} {var:>7.4f} {c:>8.3f} {std_str}{flag}")

    print()

    if regressions:
        print(f"FAILED: {len(regressions)} score(s) dropped more than {args.threshold}σ below historical mean:")
        for col, mean, std, c, drop_std in regressions:
            print(f"  {col}: {c:.3f}  (mean={mean:.3f}, std={std:.3f}, drop={drop_std:.2f}σ)")
        sys.exit(1)
    else:
        print(f"OK: all scores within {args.threshold}σ of historical mean.")
        sys.exit(0)


if __name__ == "__main__":
    main()
