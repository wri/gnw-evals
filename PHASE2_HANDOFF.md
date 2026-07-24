# GNW Eval Metrics — Phase 2 Handoff

> Self-contained pickup note for continuing the eval-metrics programme on another
> machine. Written 2026-07-24. Everything referenced here is on the gnw-evals
> branch **`eval-metrics-slice-1`** unless stated otherwise. Read the Methodology
> section first if you have not worked on this programme before — the rest assumes it.

## 0. TL;DR — where we are

- **Slice 1 (TCL × {quantification, trend, comparison})** is built and has its first
  official production run (2026-07-20): e2e pass rates quant **74%**, trend **93%**,
  comparison **89%**. Run summaries are committed under `runs/`.
- **Phase 2 case authoring is done**: all applicable dataset × numeric-intent cells
  across the full 12-dataset catalog now have permutation manifests + instruction
  files. **Generation is held** — no LLM prompt wordings have been generated yet, so
  the new cells have zero promoted cases (0% prompt coverage by design).
- **The blocker for scoring the new cells**: the ground-truth path is hardwired to
  Tree Cover Loss. Expanding it is the Phase 2 evaluator plan (§5, §6).
- Nothing is generated or run against any API in this state. Resume steps are §6.

## 1. Where things live

| Thing | Location | In git? |
|---|---|---|
| Eval harness, evaluators, generation tooling, cases, run summaries | `gnw-evals/` (this repo), branch `eval-metrics-slice-1`, remote `git@github.com:wri/gnw-evals.git` | **yes** — pushed |
| Dataset catalog YAMLs (source of truth for facts) | `project-zeno/src/agent/datasets/catalog/*.yml` | in project-zeno |
| Programme PRDs (master plan, roadmap, prompt-gen spec, Phase 2 plan) | `../PRDs/` in the workspace root | **NO** — the workspace root is not a git repo, so these do **not** travel with a `git pull`. Get them from AJ / the origin machine if you need the full text. Their essentials are summarised below. |

Workspace PRDs worth having (paths relative to the workspace root, `Workspace/GNW/`):
`PRDs/eval-metrics-programme.md` (master), `PRDs/evaluator-coverage-roadmap.md` (living
evaluator map / surface-coverage denominator), `PRDs/eval-prompt-generation.md`
(synthetic-first generation spec), `PRDs/eval-slice-1-tcl-numeric.md` (slice 1),
`PRDs/eval-phase-2-numeric-expansion.md` (the evaluator plan this handoff operationalises).

## 2. Methodology (read this first)

The goal is a **publishable quality scorecard**: an **intent × dataset matrix** where
each cell publishes two things — a **coverage tier** (how thoroughly we test the cell)
and a **quality score** (how well the agent does). Internally the scorecard is richer
(per-bucket, per-evaluator, case-level drill-down). Renderer: `gnw_scorecard`
(`src/gnw_evals/data_handlers/scorecard.py`) → `runs/scorecard.html`.

### 2.1 Intents and datasets
- **Intents** are the trace-analytics taxonomy labels (`project-zeno-next .../lib/analytics/taxonomy.ts`).
  The scorecard columns are the 11 substantive intents; this programme scores the three
  **numeric** ones first: quantification, trend, comparison.
- **Datasets** are the 12 catalog datasets (ids 0–11); the row order + slug map is
  `DATASET_SLUGS` in `src/gnw_evals/data_handlers/run_summary.py`.

### 2.2 Three internal buckets + staged gate
Every evaluator's score field belongs to one bucket (`SCORE_FIELD_BUCKETS` in
`src/gnw_evals/evaluators/registry.py`):
- **Retrieval** — did the agent understand the prompt and select the right AOI /
  dataset / parameters / dates, or correctly defer? (aoi, dataset, date, canopy,
  forest_filter, intersections, clarification, suggested_datasets)
- **Analysis** — did it pull and compute the right numbers? (`data_pull_exists`,
  `data_fidelity` = pulled numbers match independently computed ground truth)
- **Explanation** — did it use the numbers well in what the user sees? (answer/chart
  judges, `number_usage`, chart_type, crop/gas focus, dashboards)

**Staged gate** (`compute_stage_scores`): a case must pass retrieval before analysis is
scored, and analysis before explanation (a failed upstream stage sets downstream to
None/n-a). The published **e2e score** = pass iff every *evaluated* stage passed. Gating
is applied at aggregation only — every enabled evaluator still runs, so per-check scores
are unchanged by the gate.

### 2.3 Coverage tier (two sub-scores → one published tier)
- **Prompt coverage** = manifest rows with ≥1 promoted case / manifest rows. The
  **permutation manifest** is the denominator: one row per permutation a well-tested
  cell should span (subtype × parameters × context layer × AOI × date-expression class ×
  language × phrasing). Required axes exhaustive; long-tail axes sampled.
- **Surface coverage** = evaluator checks wired-and-applicable / checks mapped as
  applicable (denominator = `PRDs/evaluator-coverage-roadmap.md`). Currently a single
  constant `SURFACE_COVERAGE_NUMERIC = 8/14` for numeric cells — Phase 2 W3 makes this
  per-cell.
- **Tier thresholds** (`coverage_tier` in `run_summary.py`, provisional):
  - **minimal** — < 10 cases, or surface coverage < 40%
  - **partial** — 10+ cases and surface 40%+, but prompt coverage < 50%
  - **good** — prompt 50%+ and surface 70%+
  - **comprehensive** — prompt 80%+ and surface 90%+, and ≥ 2 non-English languages
  Tier says nothing about quality; a cell can score 100% while barely tested. TCL cells
  are "partial" today because surface is 57% (< 70%), *not* for lack of cases — wiring
  more evaluators is what lifts them.

### 2.4 Prompt generation (synthetic-first)
Locked decision: generate from the dataset catalog + intent taxonomy + code; use real
traces only to validate realism. Pipeline (see `generation/README.md`):
1. **Permutation manifest** per cell (`cases/manifests/<slug>__<intent>.manifest.csv`),
   curated by hand, validated against the catalog YAML.
2. **Per-cell instruction files** (`generation/<slug>/_shared.md` + `<intent>.md`) — the
   wording rules, derived from the catalog `prompt_instructions`/`cautions`.
3. `generation/generate_cases.py` asks an LLM (default `claude-sonnet-5`) for the missing
   prompt **wordings only**. **Every `expected_*` value is constructed mechanically** from
   the manifest row + the dataset's `generation/dataset_config.py` entry — the LLM never
   writes an expected value, so a generated case cannot smuggle in a wrong expectation.
4. Candidates land in `cases/candidates/` (gitignored workflow). Review gate: read every
   wording against the shared rules, review **100%** of `judge_instruction`s, then promote
   into `cases/<slug>__<intent>.csv` with `status=ready`. Every case that fails its first
   run is triaged (bad case vs real defect) before the set is treated as versioned.

Ground-truth numbers are **never stored in the CSV**: the harness computes them at run
time from case params (so they survive data-version bumps).

### 2.5 Ground-truth scoring (numeric intents)
- The harness fetches the true numbers from the analytics API for each case
  (`utils/analytics_client.py`) and attaches them as `case.ground_truth`.
- **Stage 1 `data_fidelity_score`** (deterministic): every number the agent pulled must
  match ground truth within tolerance (relative 0.1%, absolute 1.0 ha).
- **Stage 2 `number_usage_score`** (LLM judge, `claude-haiku-4-5`): a per-intent rubric
  checks the figures are *used* correctly (direction right, headline figure within ±5%,
  `unquantified` flagged when the agent gives no number). **Judge must emit reasoning
  before the score** — haiku contradicts itself otherwise (slice-1 triage finding).

### 2.6 Official runs + longitudinal model
- **Official run = production + default profile, per release.** Multi-trial
  (`--num-trials 3`) where flakiness matters. Each run writes a committed **run-summary
  JSON** to `runs/` (`--run-summary`); the scorecard renders history from these.
- Pass rates are comparable **only within a `methodology_version`** (`run_summary.py`);
  bump it when evaluators / gating / thresholds change materially — the scorecard marks
  the break instead of drawing a delta.
- Per-case `evaluators` column = whitelist (intersected with the run-level
  `--evaluators`/`--skip-evaluators`). Used e.g. to exclude the date check on `two_period`
  comparison rows (any sub-window of the compared span is a valid scope).

## 3. What was done this session (all committed on `eval-metrics-slice-1`)

1. **Scorecard expanded** to the full 12-dataset × 11-intent matrix: merges the latest
   result per cell across runs (single-cell official runs no longer hide each other),
   adds the tier legend, and tags every per-evaluator score with its bucket. (`scorecard.py`,
   `run_summary.py` DATASET_SLUGS, `pyproject.toml`, `tests/test_run_summary.py`.)
2. **First official production run** committed (`runs/*.json` + `scorecard.html`): TCL
   quant 74% / trend 93% / comparison 89%. Failure themes: date-scoping flakiness (biggest
   retrieval drag), primary-forest substitution, 8–10% figure deviations on some national
   totals.
3. **Generation tooling generalised** to all datasets: `generation/dataset_config.py`
   (per-dataset config table), `--dataset` on `generate_cases.py`, `--catalog-dir` on
   `validate_manifest.py`, `tests/test_generation.py`. Backward-compatible with TCL.
4. **27 new cells authored**: quant+comp for all 12 datasets, trend for the 6 time-series
   datasets (ids 0,2,4,9,10,11). 247 manifest rows, ~310 target cases, 38 instruction
   files. All 30 manifests validate. **Generation held** (no wordings, no runs).
5. **Evaluator plan** written: `../PRDs/eval-phase-2-numeric-expansion.md`, roadmap +
   PRD index updated.

### Applicability (which cells exist and why)
Quant + comp apply to all 12 datasets. Trend applies only where the product supports a
time axis: **ids 0 (DIST-ALERT), 2 (grasslands), 4 (TCL, done), 9 (sLUC), 10 (fires),
11 (integrated alerts)**. Trend is **n/a** for snapshot/aggregate datasets — land cover
(1), natural lands (3), tree cover gain (5), GHG flux (6), tree cover (7), TCL-by-driver
(8) — the catalog forbids or cannot show a time series there; a "trend" prompt on those is
a Phase-3 guardrail/redirect case, not a numeric case.

## 4. State of the case set (what runs, what does not)

- The **3 TCL cells** are fully scorable and have official runs.
- The **27 new cells** have manifests + instruction files but **no promoted cases yet**.
  Even once cases are generated, they will only score the **retrieval-bucket
  deterministics** (aoi / dataset / date / parameters) until the ground-truth work in §5
  lands — because ground truth is TCL-only today.

## 5. The blocker: ground-truth is TCL-hardwired

- `utils/analytics_client.py` posts every intent case to one TCL endpoint
  (`/v0/land_change/tree_cover_loss/analytics`) with a TCL-shaped payload — no dataset
  dispatch.
- `evaluators/ground_truth_evaluator.py` hardcodes TCL column names (`area_ha`,
  `carbon_emissions_MgCO2e`, `tree_cover_loss_year`, the dominant-driver taxonomy) and
  ha/CO2e unit semantics in both stages and the judge prompt.
- **Silent-pass trap to fix first**: a ground-truth row lacking `area_ha` yields no
  required metrics, so stage-1 fidelity **vacuously passes** (green with nothing checked).

## 6. How to resume (exact steps)

### 6.1 Environment
```bash
cd gnw-evals
rm -rf .venv && uv sync           # if `uv run` can't import gnw_evals (stale shebang)
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/opt/libpq/lib   # macOS: psycopg/libpq
# Run tests/tools with UV_NO_SYNC=1 (or `uv run`) so uv.lock isn't retouched.
```
Secrets in `gnw-evals/.env`: `API_TOKEN` (production-scoped), `ANTHROPIC_API_KEY`.
Staging needs a different token (GH Actions secret `API_TOKEN_STAGING`); pass
`--api-base-url` explicitly, the local `.env` `API_BASE_URL` points at production.

### 6.2 Validate the manifests (no API, no LLM)
```bash
uv run python generation/validate_manifest.py \
  --catalog-dir ../project-zeno/src/agent/datasets/catalog
uv run pytest tests/          # 266 passing as of this handoff
```

### 6.3 Generate cases for a cell (the held step — this spends LLM tokens)
```bash
# dry-run prints the prompts without calling the LLM:
uv run python generation/generate_cases.py --dataset grasslands --intent trend --dry-run
# real generation writes cases/candidates/<slug>__<intent>.candidates.csv:
uv run python generation/generate_cases.py --dataset grasslands --intent trend
```
Then spot-check (read wordings vs `generation/<slug>/_shared.md`; review 100% of
`judge_instruction`s), promote into `cases/<slug>__<intent>.csv` with `status=ready`,
delete the candidates file, re-run `validate_manifest.py`. `--dataset` accepts any slug in
`dataset_config.py`; it refuses an intent the config marks not applicable.

### 6.4 Evaluator expansion (to actually score the new cells) — from the Phase 2 plan
- **W1 (P0)** — make `analytics_client.py` dataset-aware: per-dataset endpoint + payload
  dispatch keyed on `expected_dataset_id`, mirroring
  `project-zeno/src/agent/datasets/handlers/analytics_handler.py`. Handle years vs
  full-date vs fixed-date forms, canopy where applicable, gain's 5-year snap, crop/gas for
  sLUC. Fixture-backed unit tests per dataset (no live API in unit tests).
- **W2 (P0)** — generalise `ground_truth_evaluator.py` off TCL columns via a per-dataset
  metric-column config; **fix the vacuous pass** (missing metric column → hard error, not
  1.0); parameterise the judge's unit/driver text.
- **W3 (P1)** — add `applicable(intent, dataset_id)` to the evaluator spec so
  non-applicable checks are n/a (not vacuous passes) and surface coverage becomes per-cell.
- **W4/W5 (P1)** — new expected fields (land-cover class id 1, driver focus id 8) and wire
  the unwired judges: `insight_quality_evaluator` (drives off the per-case
  `judge_instruction`, which the new manifests already carry — high leverage) and a
  YAML-derived dataset-limitation-compliance judge. `language_evaluator` stays deferred
  (English-only round).
- Bump `METHODOLOGY_VERSION` when W1–W3 land.

### 6.5 Official run (once cells are scorable) — do NOT run in the held state
```bash
uv run gnw_evals --api-base-url https://api.globalnaturewatch.org \
  --test-file cases/<slug>__<intent>.csv \
  --sample-size -1 --num-workers 5 --num-trials 3 --run-summary \
  --output-filename official_<slug>_<intent>
uv run gnw_scorecard          # re-render runs/scorecard.html
```
Also keep the standing instruction: run the GOLD set (`gold.csv`) as a before/after
regression check against `main`, not just the feature cells.

## 7. Gotchas

- **Manifest header**: the 27 new manifests use a 21-column superset; the 3 TCL manifests
  keep their original 16 columns. Both are read via `csv.DictReader`, so both work — don't
  "normalise" them.
- **`dataset_config.py` module name**: deliberately not `datasets.py` (avoids shadowing
  the PyPI `datasets` package on `sys.path`). Scripts import it via the `generation/` dir
  being `sys.path[0]`; tests insert that dir on the path.
- **Fixed-date datasets (1,3,6,7,8)** ignore/clamp user dates → their manifests leave
  expected dates blank (`date_expression=none|fixed`) so the date check is correctly n/a.
- **Alert datasets (0,11)** use full `YYYY-MM-DD` windows, not years; id 0 always sets an
  `intersections` breakdown (the only reason to pick it over id 11), id 11 never does.
- **Driver (8) / fires (10)** intersection is injected by the tooling
  (`fixed_intersections`), not the manifest — leave the manifest `intersections` blank.
- **`two_period` comparison rows** carry the whitelist
  `clarification;aoi;dataset;parameters;data_pull;answer;chart_type;ground_truth` (omits
  `date`).
- **canopy quirk**: the agent handler sends `max(canopy values)` while every
  prompt_instruction says "use 30%"; ground truth must send the intended 30 so both sides
  agree — assert this when building W1.
- `outputs/` is gitignored (per-run detail); `runs/*.json` + `scorecard.html` are
  committed (the longitudinal record).
- Four evaluators (`language`, `insight_quality`, plus limitation/hallucination as
  planned) are in the tree/roadmap but **unwired** — their columns are not scored until
  W4/W5.

## 8. Open decisions for AJ
- Cell sizing: cells are ~10–12 cases (clears the "partial" 10-case floor). The
  prompt-generation PRD's target is 30–50 per cell — a later top-up.
- Whether to commit `runs/scorecard.html` long-term or treat it as a build artefact
  (currently committed for convenience).
