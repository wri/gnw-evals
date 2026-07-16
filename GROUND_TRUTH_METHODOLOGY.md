# Ground-Truth Evals Methodology

## Overview

The ground-truth eval mode adds a **quality signal for numeric answers**: given a
user question that has one correct number (or one correct comparison / trend),
did the agent surface the right figure and use it correctly?

It complements the base harness (see `SCORING_METHODOLOGY.md`), which checks
*whether the agent selected the right AOI, dataset, dates, and produced an
answer*. Those checks can all pass while the headline number in the answer is
wrong. Ground-truth mode is the check that catches that.

Each ground-truth case is scored on two independent axes:

| Score | Type | Question it answers |
|---|---|---|
| `data_fidelity_score` | Deterministic | Did the agent **pull** the correct numbers? |
| `number_usage_score` | LLM-as-judge | Did the agent **use** those numbers correctly in its answer, for this intent? |

Both are binary (`1` / `0`) or `None` (not applicable — the case declares no
intent). A case is ground-truth-scored only when its CSV row has a non-empty
`intent`.

## What it measures — and what it does not

The agent's `pull_data` tool fetches its numbers from the **same analytics API**
(`analytics.globalnaturewatch.org`) that this harness queries to build ground
truth. Both sides therefore share one source of truth. This is deliberate, and
it bounds the claim:

- **In scope:** *retrieval and usage fidelity* — did the agent build the correct
  analytics query (right AOI, years, canopy threshold, forest filter,
  intersection) for the user's question, and did it report the returned numbers
  faithfully and reason about them correctly.
- **Out of scope:** *data correctness* — whether the analytics platform's numbers
  are themselves right. An independent check would require the underlying
  pre-computed zonal statistics or the source rasters, and even then both derive
  from the same UMD/Hansen inputs.

Ground truth is always computed from the **case's declared parameters**, never
from the agent's own trace, so a wrong-query error (e.g. wrong canopy threshold)
is still caught: the agent's numbers will not match the independently fetched
ground truth.

## Scope of the current proof of concept

- **Dataset family:** Tree cover loss — base (`dataset_id` 4), by dominant driver
  (8), and from fires (10).
- **AOI type:** GADM level-0 (country) admin areas.
- **Intents:** `quantification`, `comparison`, `trend`. These are three of the
  eleven intents in the frontend trace-analytics taxonomy
  (`project-zeno-next` `taxonomy.ts`); the label strings match so results can
  later join the trace-analytics heatmap (Intent × coarse Topic).

The design generalises to other datasets, AOI types, and intents (see
[Extending the harness](#extending-the-harness)).

## The two stages

### Stage 1 — data fidelity (deterministic)

The evaluator collects every numeric value the agent pulled, from all state
locations: inline `statistics[].data`, any `statistics[].source_url` it fetches,
and `charts_data[].data`. It then requires that **every ground-truth value is
present** among the pulled numbers, within tolerance.

- Tolerance: **0.1 % relative** (`math.isclose(rel_tol=0.001)`). Because both
  sides hit the same API, a match should be near-exact; 0.1 % absorbs float noise
  while still failing a wrong canopy threshold or forest filter (which shift
  values by more than 1 %). Zero-valued ground truth uses a **1.0 ha absolute**
  tolerance instead.
- For the **fires** dataset the required values are the `fires` and `non-fires`
  split columns (which sum to the total), matching the catalog instruction to
  plot the split rather than `area_ha`.
- Score `0` lists the missing rows in `data_fidelity_missing` (e.g.
  `BRA 2023: expected area_ha 2,805,359.48, no match`), so a failure names the
  exact value the agent did not pull.

A fidelity failure means the agent built the wrong query. It is upstream of the
answer: if the numbers are wrong, how they are phrased does not matter.

### Stage 2 — number usage (LLM-as-judge)

A single judge call (`claude-haiku-4-5`, temperature 0, structured output)
receives:

- the query, intent and subtype;
- the full ground-truth table (per-year `area_ha`, carbon emissions, and any
  driver / fire split columns);
- **deterministically derived facts** — totals, first/last-year values, the peak
  year, the percentage change, the two-AOI comparison, the dominant driver (as a
  share of total and of known non-`Unknown` loss), and the three catalog driver
  groupings (deforestation proxy, temporary disturbance, all agriculture). These
  are computed in code and the judge is told to trust them over its own
  arithmetic;
- the agent's final answer;
- any per-case `judge_instruction`.

The judge returns a structured verdict:

| Field | Meaning |
|---|---|
| `number_usage_score` | `1` pass / `0` fail against the intent rubric |
| `number_usage_reasoning` | 2–3 sentence justification (always present) |
| `number_usage_failure_comment` | On failure, quotes the wrong figure/claim and the ground-truth value it contradicts; empty on pass |
| `unquantified` | `true` when the answer makes a correct qualitative claim but cites no figures |

### Per-intent rubrics

- **quantification** — the answer must state the requested figure, matching ground
  truth within tolerance. A quantification answer with no figure at all fails
  (`unquantified` true).
- **comparison** — the comparative claim (which side is larger, direction of the
  difference) must be correct; any volunteered figures or differences must match
  within tolerance. A correct claim citing no figures passes with `unquantified`
  true.
- **trend** — the direction over the requested window (rising / falling / flat,
  including reversals such as a spike year) must be correct; any volunteered
  magnitudes, peak years, or percentage changes must match. A correct direction
  citing no figures passes with `unquantified` true.

All intents: the judge accepts honest rounding and unit conversions
(ha / kha / Mha / km², MgCO₂e / GtCO₂e), checks volunteered GHG-emissions figures
against the carbon column rather than treating them as errors (the platform
reports emissions alongside loss by design), and never penalises caveats
(e.g. the 2001–2010 vs 2011–2025 methodology break), hedging, or extra context
that does not contradict the ground truth.

### Tolerance summary

| Stage | Tolerance | Rationale |
|---|---|---|
| Data fidelity | 0.1 % relative (1.0 ha absolute for zeros) | Same API; a gap means a wrong query |
| Number usage | 5 % relative, unit-aware | Absorbs honest prose rounding in the answer |

## Ground-truth construction

For every case with an `intent`, the harness fetches ground truth **at run time**
before the agent tests execute (`utils/analytics_client.py`, called from
`core.py::run_csv_tests` right after the CSV loads).

- **Source:** `POST /v0/land_change/tree_cover_loss/analytics`, then poll the
  returned link until `status` is `saved`/`success`. The API is asynchronous and
  idempotent (the resource id is a UUID5 of the request payload), so repeated
  fetches are effectively cached.
- **Payload** is built from the case's parameters: `aoi.ids` from
  `expected_aoi_ids`, years from the first four characters of
  `expected_start_date` / `expected_end_date`, `canopy_cover` and `forest_filter`
  from their columns, `intersections` from `expected_intersections`. When neither
  a canopy threshold nor a forest filter is set, canopy defaults to **30** — the
  product default on both the agent and analytics sides.
- **Environment matching:** the analytics `X-environment` header is chosen to
  match the agent under test (a staging agent queries staging analytics data), so
  ground truth and agent read the same data environment. Override with
  `ANALYTICS_X_ENVIRONMENT`; override the analytics host with
  `ANALYTICS_API_BASE_URL`.
- **Computed, not frozen:** ground truth is never stored in the CSV. It is
  refetched each run and recorded in the output (`ground_truth_json`), so results
  stay correct across analytics data-version bumps and remain auditable.
- **Fails loudly:** if any case's ground truth cannot be fetched or comes back
  empty, the run aborts rather than silently scoring against nothing.

### Whole-record datasets

The *by dominant driver* dataset is a single-period aggregate over the full
record (2001–2025) and is **not date-filterable**; the agent always pulls the
whole record. Driver cases therefore set the expected years to the full record so
ground truth matches what the agent pulls, and the case's `judge_instruction`
states that per-year or sub-range driver figures must not be required.

## The case CSV contract

Ground-truth cases use the standard eval CSV (see `SCORING_METHODOLOGY.md` and the
README for the base columns) plus:

| Column | Required | Purpose |
|---|---|---|
| `intent` | Yes (marks a case for ground-truth scoring) | `quantification` \| `comparison` \| `trend`. An unknown value fails loudly at load time |
| `eval_subtype` | Recommended | Free-text subtype for reporting breakdowns (e.g. `single_year`, `two_country`, `peak_year`, `driver_share`, `fires_split`) |
| `expected_canopy_cover` | No | Canopy threshold to request; blank ⇒ 30 default |
| `expected_forest_filter` | No | `primary_forest` \| `intact_forest` (the analytics API rejects `natural_forest` for admin AOIs) |
| `expected_intersections` | No | `driver` \| `fire` |
| `judge_instruction` | No | Per-case note passed verbatim to the stage-2 judge |

The existing `expected_aoi_ids`, `expected_start_date`, `expected_end_date`,
`expected_dataset_id` and `expected_context_layer` columns are reused: the first
three build the analytics query, and the last two are scored by the base harness.

### Authoring guidance

- **Be explicit about the parameters** so ground truth is unambiguous — one
  analytics query per case. Natural phrasing is fine, but pin the variables.
- **Reflect the dataset catalog.** The base tree-cover-loss catalog tells the
  agent to default to the `primary_forest` layer for general "forest loss /
  deforestation" requests within its pan-tropical extent, honouring an explicit
  opt-out for all tree cover. So:
  - to test **all tree cover**, say "all forest types" / "including plantations"
    (the opt-out) and leave the filter blank;
  - to test the **primary-forest default**, use "deforestation" wording for a
    tropical AOI and set `expected_forest_filter=primary_forest`;
  - to test an **explicit filter**, name it ("primary forest", "intact forest").
- **Match dataset semantics.** Use whole-record years for the driver dataset;
  use `expected_intersections=fire` and `dataset_id` 10 for fire-split questions.

## Running

Cases live in per-cell files under `cases/` (e.g.
`cases/tree_cover_loss__quantification.csv`), generated and reviewed via the
`generation/` workflow (see `generation/README.md`). The original
`ground_truth_tcl_poc.csv` was split into these files.

```bash
# dev loop: one case, printed to screen
uv run gnw_evals --api-base-url <api> --api-token <token> \
  --test-file cases/tree_cover_loss__quantification.csv \
  --test-id gt-quant-01 --print-results

# full run for one cell: CSVs + HTML report in outputs/
uv run gnw_evals --api-base-url <api> --api-token <token> \
  --test-file cases/tree_cover_loss__quantification.csv --num-workers 5 \
  --output-filename tcl_quantification

# robustness: mean + stdev over N trials
uv run gnw_evals ... --num-trials 3
```

Requires `ANTHROPIC_API_KEY` (the judge) and a GNW API token for the target
environment. The harness targets staging by default; pass `--api-base-url`
explicitly for production or localhost, and `--ff <profile>` to select an agent
tool profile.

## Outputs

Every run writes to `outputs/` (in both CSV and `--print-results` modes the HTML
report is written — it is the shareable artefact of a run):

- **`*_summary.csv`** — one row per case with the scores and the judge failure
  comment.
- **`*_detailed.csv`** — expected-vs-actual for every field, including the
  ground-truth fields: `intent`, `eval_subtype`, `expected_/actual_canopy_cover`,
  `expected_/actual_forest_filter`, `ground_truth_json`, both scores, the judge
  reasoning and failure comment, and `unquantified`.
- **`*_report.html`** — self-contained report: headline tiles (data fidelity,
  number usage, unquantified count), an Intent × subtype quality grid, failure
  cards with judge comments and thread/trace links, and an **All cases** table
  showing **expected over selected** values for AOI, years, canopy and filter
  (mismatches highlighted) for spot-checking.

The console summary prints data fidelity and number usage overall and broken down
by intent.

### Selected-parameter capture

The report's "selected" values come from the agent's final state: the applied
layer from `dataset.context_layer`, and the canopy threshold from
`dataset.parameters` (reported as `30 (default)` when the agent uses the implicit
default, which it does not otherwise surface).

## Interpreting results

- **Data fidelity fails, number usage n/a-or-fails** → the agent queried the wrong
  data (check the selected vs expected canopy / filter / years in the report). The
  answer is moot until the pull is right.
- **Data fidelity passes, number usage fails** → the agent pulled the right
  numbers but drew a wrong conclusion (misstated a figure, wrong comparison
  direction, or an overstated trend). The judge's failure comment quotes the
  offending claim.
- **`unquantified` true** → the qualitative claim is correct but no figure was
  cited. This passes (per the rubric) and is tracked separately so
  "correct but unquantified" rates can be reported without polluting the score.
- **Base-harness `date_match` can fail while ground-truth scores pass** — e.g. the
  agent pulls the whole timeseries and reports the requested single year. That is
  a base-harness date-selection signal, not a numeric-quality defect; the
  requested year's value is still present and correctly used.

## Limitations and caveats

- Shared data source with the agent (see [scope](#what-it-measures--and-what-it-does-not)): this is retrieval/usage fidelity, not data validation.
- The judge is a single `claude-haiku-4-5` call given the ground truth; it is a
  checker, not a solver. A stronger judge or a multi-vote panel is a future
  option if disagreement rates warrant it.
- The canopy threshold the agent used is only observable when it overrides the
  default; the default case is shown as `30 (default)` and is verified indirectly
  by data fidelity (a wrong threshold produces non-matching numbers).
- Analytics data-version bumps change absolute values mid-history; ground truth is
  refetched each run and recorded, but two runs across a bump are not directly
  comparable on raw values.

## Extending the harness

- **New dataset:** add an analytics client path for its endpoint and response
  columns in `utils/analytics_client.py`, and teach `_required_row_metrics`
  (`evaluators/ground_truth_evaluator.py`) which columns a compliant answer must
  match.
- **New intent:** add a rubric to `_INTENT_RUBRICS` and the label to
  `GROUND_TRUTH_INTENTS` in `utils/eval_types.py` (unknown intents fail loudly at
  load). Add any intent-specific derived facts to `_derive_facts`.
- **New reported dimension:** the score fields are hand-enumerated — add to
  `core.py::_SCORE_FIELDS`, the two `result_exporter.py` fieldname lists, and the
  report if a new column should surface.

## North star

The end goal is a published quality metric for every cell of the trace-analytics
heatmap, optionally broken down by intent subtype. This PoC establishes the
machinery for one cell's worth of data (tree cover loss × forest topic) across the
three numeric intents. Joining to live heatmap traffic additionally requires the
canonical prompt tagger that assigns intents to real traces (see the feature PRD,
`PRDs/ground-truth-evals-poc.md`, for the open item).
