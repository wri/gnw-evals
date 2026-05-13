# gnw-evals justfile
# Run `just` or `just help` to see CLI options.

# ── Default ───────────────────────────────────────────────────────────────────

_default:
    @just --list

# Show CLI help
help:
    uv run gnw_evals --help


# open local heatmap notebook
heatmap:
    uv run marimo edit --watch notebooks/nb_heatmap_01.py


# ── Smoke test ────────────────────────────────────────────────────────────────

# Sanity check: gold set, 5 samples
smoke:
    uv run gnw_evals --eval-set gold --sample-size 5 --output-filename "smoke"

# ── Full offline run ──────────────────────────────────────────────────────────

# Run all eval sets from default spreadsheet
run-all:
    uv run gnw_evals --eval-set all --sample-size -1 --output-filename "offline_evals"

# ── Helper (private) ──────────────────────────────────────────────────────────

# Run a specific eval set with full control over parameters.
# Usage: just _eval [eval_set] [n] [out] [workers] [offset]  (all positional)
# Example: just _eval date_selection 50
[private]
_eval eval_set="gold" n="25" out="" workers="10" offset="0":
    uv run gnw_evals \
        --eval-set {{ eval_set }} \
        --sample-size {{ n }} \
        --output-filename "{{ if out == "" { eval_set } else { out } }}" \
        --num-workers {{ workers }} \
        --offset {{ offset }}

# ── Isolated eval set ─────────────────────────────────────────────────────────
# Each accepts an optional sample size as a positional arg (default 25).
# e.g. `just gold 50`
# For more options (workers, offset, custom filename) use `just _eval` directly.

[group: 'isolated-eval-set']
gold sample="25":
    uv run gnw_evals --eval-set gold --sample-size {{ sample }} --output-filename "gold" --num-workers 10

[group: 'isolated-eval-set']
location-id sample="25":
    uv run gnw_evals --eval-set location_id --sample-size {{ sample }} --output-filename "location_id" --num-workers 10

[group: 'isolated-eval-set']
dataset-id sample="25":
    uv run gnw_evals --eval-set dataset_id --sample-size {{ sample }} --output-filename "dataset_id" --num-workers 10

[group: 'isolated-eval-set']
date-selection sample="25":
    uv run gnw_evals --eval-set date_selection --sample-size {{ sample }} --output-filename "date_selection" --num-workers 10

[group: 'isolated-eval-set']
analysis-results sample="25":
    uv run gnw_evals --eval-set analysis_results --sample-size {{ sample }} --output-filename "analysis_results" --num-workers 10

[group: 'isolated-eval-set']
dataset-interpretation sample="25":
    uv run gnw_evals --eval-set dataset_interpretation --sample-size {{ sample }} --output-filename "dataset_interpretation" --num-workers 10

