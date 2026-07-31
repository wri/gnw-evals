# gnw-evals — working memory

Repo: `WRI/gnw-evals`. End-to-end eval harness for the Global Nature Watch (GNW) /
Project Zeno agent. Sends real queries to the live GNW API, reads the resulting
agent state, and scores it against `expected_*` columns from a test sheet.

Deep reference (definitions, scoring, gotchas): `memory/gnw-evals-reference.md`.
Read it before interpreting any results or changing an evaluator.

## What the GOLD set is for

GOLD is a **capability smoke test, not a quality or accuracy measure.** It exists
to answer one question at release time: did an agent change break a capability
that used to work? It is run every release for exactly that reason.

Two consequences that should drive every judgement about it:

- **Coverage is the design criterion.** GOLD should exercise every GNW capability.
  A capability with no GOLD row ships untested. So a coverage gap is a more serious
  defect than a low score, and rows that run but score nothing are coverage holes
  rather than merely wasted API budget.
- **Determinism outranks realism.** A smoke test is only useful if it fails when
  the code breaks and passes otherwise. Anything that makes a row fail for reasons
  unrelated to the agent — relative dates that drift, AOIs that aren't a real
  boundary, multi-turn follow-ups the harness can't replay — disqualifies it,
  however natural the phrasing.

`expected_answer` is therefore a proxy for "did this capability execute correctly
end to end", not a grade on answer quality. Don't read the score as a measure of
how good GNW's answers are; that's what the other eval sets and trace analysis
are for.

## Run the GOLD set

Prereqs: `.env` must contain `API_TOKEN` (GNW machine-user token, **environment
specific**), `ANTHROPIC_API_KEY` (for the LLM judge), and `SPREADSHEET_ID`
(`1_G1aq2fSCPqhT6w55_Od6VU7sov76t1lHQTBeZZxbdM` — the eval sets workbook, gold is
gid 0; only needed when pulling from Sheets rather than a local CSV).

```bash
uv sync
```

### Snapshot the sheet first

The gold tab is live and hand-edited, so two runs a week apart are not
comparable. Pin the inputs before a run that matters:

```bash
uv run python fetch_gold_set.py          # → data/gold-YYYYMMDD.csv
uv run python fetch_gold_set.py --force  # overwrite today's
```

It prints the row count, the non-empty-query count, and the exact
`--status-filter` string for that snapshot's status values. The export URL is
link-shareable, so no credentials are involved. `data/` is gitignored but the
existing snapshot is tracked, so committing a new one needs `git add -f`.

**Canonical full gold run against the remote sheet:**

```bash
PYTHONUNBUFFERED=1 uv run gnw_evals \
  --eval-set gold \
  --env staging \
  --sample-size -1 \
  --num-workers 10 \
  --timeout 900 \
  --verbose
```

**Full gold run against the committed local CSV** (offline-repeatable, no sheet access):

```bash
PYTHONUNBUFFERED=1 uv run gnw_evals \
  --test-file data/gold-28032026.csv \
  --sample-size -1 \
  --num-workers 10 \
  --timeout 900 \
  --status-filter "not doing,warning" \
  --verbose \
  --output-filename gold_local
```

**Smoke test before committing to a long run** (3 tests, ~2 min):

```bash
uv run gnw_evals --eval-set gold --env staging --sample-size 3 --verbose
```

## Non-negotiable flags — get these wrong and the run is meaningless

| Flag | Default | Why it matters |
|---|---|---|
| `--sample-size` | **5** | Not all rows. Pass `-1` for a real gold run. |
| `--env` | **prod** | Defaults to production. Pass `--env staging` unless prod is intended. |
| `--timeout` | 240s | Far too low for gold. Observed gold latencies 900–2100s. Use 900+. |
| `--status-filter` | None | **This is a SKIP list, not a keep list.** See below. |
| `--num-workers` | 1 | Sequential. 10 is fine; back off if rate-limited. |

### `--status-filter` is inverted relative to the README

`csv_loader.py` does `df[~df["status"].isin(skip_statuses)]` — rows whose `status`
matches are **dropped**. README troubleshooting item 1 says to pass
`--status-filter ready,rerun`; doing that would discard exactly the tests you want
to run. Pass the statuses to *exclude*. Case-insensitive.

The values in use change over time, so read them off the snapshot rather than
trusting this file. On `data/gold-28032026.csv` they are `Not doing` (17) and
`WARNING` (1) → `--status-filter "not doing,warning"`. On the live sheet as of
2026-07-28 they are `Not doing`, `Todo` and `Done` → `--status-filter "not
doing,todo"`. `fetch_gold_set.py` prints the correct string for whatever it pulled.

### The live sheet has columns the harness cannot read

The live gold tab has drifted from `ExpectedData`. It now carries `expected_text`,
`expected_suggested_datasets`, `expected_dashboard_created` and
`expected_dashboard_widgets`, none of which any evaluator reads, and it has
**dropped** `expected_subregion` and `expected_guardrail_answer`.

Unknown columns are silently ignored — `CSVLoader` injects missing fields as `""`
and prints only the fields it *did* find. So the four Metadata rows (1-074 to
1-077) and the five dataset-suggestion rows (1-063, 1-094 to 1-097) now hold their
expected answers in columns the harness never looks at: they run, cost a full
agent call each, and produce no score. Check the `✓ Expected fields detected:`
line at load time against the sheet's real headers before trusting a run's
denominator.

### Other traps

- `--test-file` and `--eval-set` are mutually exclusive (unless `--eval-set` is
  left at its default `gold`). Supplying both raises `BadParameter`.
- Local `--test-file` paths resolve relative to **project root**, not cwd.
- `data/` and `outputs/` are gitignored. Copy anything worth keeping elsewhere.
- `--random-seed 0` (default) means sequential slicing with `--offset`. Any
  non-zero seed switches to random sampling and `--offset` is ignored.
- `--test-group-filter` is a no-op on `data/gold-28032026.csv` — that file's
  `test_group` column is entirely empty.

## Reading the output

Three files land in `outputs/`, prefixed `{output-filename}_{YYYYMMDD_HHMMSS}`:
`_summary.csv` (scores only), `_detailed.csv` (expected vs actual, `timed_out`,
`latency`, guardrail fields), `_report.md` (metric table + per-test rows).

**The headline number for the gold set is `agent_answer_score`, not
`overall_score`.** The harness prints "overall_score is experimental and
untested" for good reason — it flat-averages dependent checks, so a run that
picked the wrong AOI still banks points for date and dataset matches. Report
`agent_answer_score` and quote the per-metric table.

Timed-out tests get `overall_score = None` and are excluded from the pass-rate
denominator, which inflates the rate when timeouts are high. Always state the
timeout count alongside the pass rate.

## CI

`.github/workflows/run-evals-manual.yml`, `workflow_dispatch` only. Inputs:
`target_env` (default staging), `eval_set` (default gold), `sample_size`
(default -1), `num_workers` (default 2), `offset`. It selects `API_TOKEN_STAGING`
or `API_TOKEN_PROD`, uploads `outputs/*.csv` as artifacts, and optionally copies
to S3 if AWS secrets are present. Note it does **not** pass `--timeout`, so CI
runs at the 240s default and will show heavy timeouts on gold.

## Housekeeping

- Lint/format: `ruff` via pre-commit. Tests: `uv run pytest`.
- Open work is tracked in `llm/TASKS.md` (done items in `llm/COMPLETED_TASKS.md`).
  Check it before proposing a scoring change; several known issues are already logged.
