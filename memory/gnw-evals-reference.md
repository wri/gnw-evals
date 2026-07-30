# gnw-evals reference — definitions, scoring, critical concepts

Companion to `CLAUDE.md` (which holds the run commands). This file is the
conceptual model: what the harness measures, what each term means, and where the
implementation diverges from the docs.

Source of truth ranking when they disagree: **code > `SCORING_METHODOLOGY.md` >
`README.md` > `GOLDENSET_GUIDELINES.md`**. Several doc statements are stale
(flagged below).

---

## 1. What the harness actually does

Per test row, `APITestRunner.run_test` (`src/gnw_evals/runners/api.py`):

1. Generates a fresh `thread_id` (uuid4).
2. `POST {api_base_url}/api/chat` with `{query, user_persona: "Researcher",
   thread_id, metadata: {langfuse_tags: ["simple_e2e_test"]}, user_id: "test_user"}`,
   `Authorization: Bearer {API_TOKEN}`, and consumes the newline-delimited stream.
3. Captures `trace_id` / `trace_url` from the stream event where `node == "trace_info"`
   (Langfuse). The trace URL is printed in `--verbose` mode and is the fastest way
   to debug an individual failure.
4. `GET {api_base_url}/api/threads/{thread_id}/state`, deserialises via
   `langchain_core.load.loads` into `agent_state`.
5. If `agent_state["dashboard_id"]` is set, `GET /api/dashboards/{id}`. A failed fetch
   degrades to `dashboard=None` with a printed warning rather than erroring the row.
6. Runs **eleven** evaluator functions against `agent_state` (plus the fetched
   dashboard), producing **16 scores**, and computes `overall_score`.

So this is a **black-box E2E eval against a deployed API**, not a unit test of the
agent graph. A red run can mean a bad agent, a slow API, or a stale expected value.
Check the Langfuse trace before blaming the agent.

Environments — **there is no `--env` flag and no `ENV_URLS`; both were removed.** The only
control is `--api-base-url` / `API_BASE_URL`.

- prod → `https://api.globalnaturewatch.org`
- staging → `https://api.staging.globalnaturewatch.org`
- The CLI default is **staging**, but the local `.env` sets `API_BASE_URL` to **prod**,
  and `.env` is loaded before click parses — so runs go to prod unless you pass the flag.
- `API_TOKEN` is environment-specific. The token currently in `.env` is **prod-only**:
  staging returns 401, prod returns an authenticated 404.

**Prod is missing two capabilities the gold sheet tests (verified 2026-07-30, GNW
`2026.6.17.3`), so nine rows cannot be scored there:** dashboards are absent
(`dashboard_created = 0` on all six of 1-108–1-113, reproduced with no `--ff` at all, so
not a flag artifact), and `send_nudge` does not exist — the agent replies *"I do not have
a tool called `send_nudge`"* (1-117–1-119). Those rows nudge correctly in prose but leave
the `nudge` state field empty. Treat their zeros as untested, not as agent quality.

## 2. Core vocabulary

**Eval set** — a named tab in the GNW evals Google Sheet, mapped to a GID in
`src/gnw_evals/utils/sheet_registry.py`. Selected with `--eval-set`. `all` runs
every set in sequence and writes one combined CSV.

| Eval set | GID | Primary metric |
|---|---|---|
| `gold` | 0 | `agent_answer_score` |
| `location_id` | 1835901063 | `aoi_id_match_score` |
| `dataset_id` | 563440160 | `dataset_id_match_score` |
| `dataset_interpretation` | 2002527957 | `agent_answer_score` |
| `analysis_results` | 333186364 | `agent_answer_score` |
| `analysis_interpretation` | 785648141 | `agent_answer_score` |
| `guardrail` | 927934976 | `clarification_requested_score` |
| `date_selection` | 1962457177 | `date_match_score` |
| `all` | — | per-set breakdown |

Sheet URL is built as
`https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}`,
so `SPREADSHEET_ID` must be set for any `--eval-set` run. A `--test-file` run
bypasses this entirely.

**Primary metric** — `EVAL_SET_PRIMARY_METRIC` in the registry. The one score
that is meaningful for that set. Used in the multi-set breakdown. Quote this, not
`overall_score`.

**GOLD set** — the release smoke test for GNW capabilities. Its purpose is to
catch regressions: it is run **every release** to verify that agent changes have
not broken a capability that previously worked. It is explicitly **not** a measure
of answer quality or accuracy.

That purpose determines how to reason about it:

- **It should cover every capability.** Anything GNW can do needs a row, because a
  capability absent from GOLD ships unverified. Coverage gaps are the failure mode
  to hunt for — more consequential than any individual score. This is why the nine
  currently-unscoreable rows and the missing dashboard / dataset-suggestion
  evaluators matter so much: those are capabilities the release check cannot see.
- **Rows must fail only when the code breaks.** A smoke test that fails for
  incidental reasons trains people to ignore it. So determinism beats natural
  phrasing: fixed date ranges rather than "the last 3 months", real boundaries
  rather than informal regions like "Borneo", single self-contained queries rather
  than conversational follow-ups (the harness opens a fresh `thread_id` per row and
  cannot replay a prior turn).
- **`expected_answer` is a liveness proxy, not a grade.** It's there so the judge
  can confirm the pipeline produced the right sort of result, which is why a 5%
  numeric tolerance is acceptable. Reading GOLD as an accuracy score is a category
  error; answer quality belongs to the other eval sets and to trace analysis.

Per `GOLDENSET_GUIDELINES.md` rows should have complete unambiguous inputs and
never require clarification. *Practice diverges on size:* the guideline says 20–50
curated queries, while the live sheet carries 97 rows and
`data/gold-28032026.csv` has 77 / 68 non-empty. Given that coverage is the goal,
the sheet growing past the guideline is expected rather than a problem — but every
row still has to earn its place by covering a capability no other row does.

**AOI** — Area of Interest. The geography the agent resolved. Sources seen in the
gold set: `gadm` (admin boundaries), `kba` (Key Biodiversity Area), `wdpa`
(protected areas), `Landmark` (Indigenous & community lands).

**Subregion** — the administrative *level* of the answer, e.g. `country`,
`state-province`, `district`. Distinct from the AOI itself: a query can resolve
the right country but aggregate at the wrong level.

**Context layer** — a secondary slicing layer applied on top of the dataset, e.g.
`driver`, `natural_lands`.

**Guardrail query** — a free-text factual question about metadata, citations,
methodology or coverage, where there is no data pull and no number to check.
`expected_guardrail_answer` and its dedicated judge **no longer exist**; the gold tab has
dropped the column. Express these with **`expected_text`** instead, which takes a
behavioural instruction ("refuses to analyse because TCL is annual") and judges semantic
inclusion. Still do **not** put them in `expected_answer` — that judge expects a
comparable value, not prose.

**Nudge** — the generic `{type, options}` state field the agent emits via `send_nudge` or
the `pick_aoi`/`pick_dataset` migrations (`aoi_choice`, `dataset_choice`). Read directly
off state, so it is deterministic where clarification detection is not. Absent on prod
(§2), and note a row can nudge correctly *in prose* while leaving the field empty.

**Dashboard** — created in-turn; `agent_state` carries only `dashboard_id`, so the runner
fetches `/api/dashboards/{id}` for AOI and widget detail. Widget types seen: `insight`,
`map`.

**Clarification** — the agent asking a follow-up instead of answering. For gold,
any clarification is a failure by definition.

## 3. Test sheet columns

Always required: **`query`**.

Checks are opt-in: an `expected_*` column that is empty or absent means that check
returns `None` and is excluded from scoring. `CSVLoader` injects any missing
`ExpectedData` field as `""` rather than erroring.

| Column | Enables | Notes |
|---|---|---|
| `expected_aoi_ids` | `aoi_id_match_score` | GADM `USA.5_1`, or KBA/WDPA numeric ID. Also the dashboard AOI check. |
| `expected_aoi_source` | (dashboard AOI only) | `gadm`, `kba`, `wdpa`, `Landmark` |
| `expected_dataset_id` | `dataset_id_match_score` | 0–10 currently. **No longer gates data pull.** |
| `expected_dataset_parameters` | `dataset_parameter_match_score` | JSON on `name`+`values`, e.g. `[{"name": "canopy_cover", "values": [10]}]`. A bare scalar never matches. |
| `expected_context_layer` | `context_layer_match_score` | `no_selection` asserts empty |
| `expected_start_date` + `expected_end_date` | `date_match_score` | needs **both**; `YYYY`, `YYYY-MM-DD`, `M/D/YYYY`. **Avoid on annual datasets — §8.** |
| `expected_answer` | `charts_answer_score` **and** `agent_answer_score` | LLM judge; also switches on the data-pull check |
| `expected_text` | `expected_text_match_score` | semantic inclusion; accepts behavioural instructions |
| `expected_clarification` | `clarification_requested_score` | `True`/`False`; blank = judge never called |
| `expected_suggested_datasets` | `suggested_datasets_match_score` | subset semantics |
| `expected_nudge_type` / `expected_nudge_options` | `nudge_match_score` | type OR; options subset by substring |
| `expected_dashboard_created` | `dashboard_created_score`, and gates the other dashboard checks | tri-state; `False` is a useful guardrail |
| `expected_dashboard_widgets` | `dashboard_widgets_match_score` | multiset, e.g. `insight;insight;map`. Containing `insight` also requires a data pull. |
| `expected_dataset_name` | — | reference only, never evaluated |
| `test_id`, `status`, `test_group` | filtering / joining only | blank `test_id` breaks `--test-id` and result joins |

Removed from the harness entirely: `expected_subregion`, `expected_guardrail_answer`.

**Semicolon semantics vary per column — there is no single rule.** `README.md` and
`SCORING_METHODOLOGY.md` both claim semicolon-separated values pass if the actual matches
any one of them. That is true for exactly one column.

| Column | Split on `;`? | Comparison |
|---|---|---|
| `expected_nudge_type` | yes | **OR** over acceptable values — the documented behaviour |
| `expected_aoi_ids` | yes | **set equality** against every AOI in state — not OR |
| `expected_suggested_datasets` | yes | subset: ≥1 must match, none outside the set |
| `expected_nudge_options` | yes | subset, matched by case-insensitive **substring** either way |
| `expected_dashboard_widgets` | yes | **multiset** — order free, counts matter |
| `expected_dataset_id` | **no** | plain `==` after `normalize_value`. `"0;1"` compared literally, always fails |
| `expected_context_layer` | **no** | same. `no_selection` sentinel asserts the layer is empty |

`normalize_value` lowercases and strips, so the dataset-id and context-layer comparisons
are case-insensitive (the sheet mixes `natural_lands`, `IFL`, `primary_forest`, `driver`).

> **Correction, 2026-07-30 — this file previously claimed multi-value `expected_aoi_ids`
> was a guaranteed 0.** That is no longer true. `_extract_actual_aoi_data` now reads
> `agent_state["aoi_selection"]["aois"]`, a **list**, and returns every `src_id`. So a
> multi-value expected set can match when the agent genuinely selects that set, and the
> ~20 parent-child comparison rows previously written off are scoreable again. The set
> comparison still means "exactly this set", not OR — a multi-value expectation fails if
> the agent picks a strict subset.

Still true: `aoi_id_match_score` is an upper bound because `normalize_gadm_id` truncates
at the underscore (`USA.5_1` and `USA.5_2` both → `usa.5`).

**Sheet drift is silent and is the highest-value thing to check.** `CSVLoader`
injects any `ExpectedData` field missing from the CSV as `""`, and ignores any CSV
column that isn't an `ExpectedData` field. Neither direction warns. The only
signal is the `✓ Expected fields detected:` line printed at load. So the sheet can
grow a new expectation column, curators can fill it in good faith, and those rows
will run at full API cost and score nothing.

This had already happened once. As of 2026-07-28 the live gold tab carried four columns no
evaluator read — `expected_text`, `expected_suggested_datasets`,
`expected_dashboard_created`, `expected_dashboard_widgets` — making nine rows unscoreable.

> **Resolved as of 2026-07-30.** All four now have evaluators, and every `expected_*`
> column on the live tab (119 rows) is read. No `ExpectedData` field is absent from the
> sheet except the internal `thread_id`. `expected_subregion` and
> `expected_guardrail_answer` were dropped from **both** sides — the columns are gone and
> so are `subregion_match_score` and `guardrail_answer_score`. Re-verify per snapshot;
> this is the highest-value thing to check and it regresses silently.

Also note row 1-092 has an end date of `31/12/2025` (D/M/YYYY), which
`normalize_date` does not accept; it normalises to `""` and scores 0 rather than
raising.

**Header auto-detection.** `_set_header()` scans the first 5 rows for a cell
equal to `query` in the first 10 columns and treats that row as the header. This
lets the sheet carry human-facing preamble rows above the real headers. If `query`
is not found in the first 5 rows it raises `ValueError: No header row found`.

Columns in `data/gold-28032026.csv` that the harness ignores entirely: `test_id`,
`Data`, `Analysis type`, `Analysis description`, `AOI type`, `expected_class_1`,
`expected_class_2`, `expected_threshold`, `value_1`, `value_2`, `priority`. They
are curation aids for humans.

## 4. The sixteen scores

Every score is **binary 1 / 0 / None**. `None` means not evaluated, and is
excluded from averages rather than counted as zero.

Hard-logic checks:

1. `aoi_id_match_score` — normalised GADM comparison, set equality against all AOIs.
2. `dataset_id_match_score` — normalised string compare (no OR — see §3).
3. `dataset_parameter_match_score` — JSON compare on `name`+`values` only.
4. `context_layer_match_score` — normalised string compare; `no_selection` sentinel.
5. `data_pull_exists_score` — a `source_url` or pull `id` counts as success; otherwise
   `row_count >= min_rows`. Gated by `ExpectedData.expects_data_pull()`, **not** by
   `expected_dataset_id` as this file previously stated.
6. `date_match_score` — both start and end must match. **Unreliable on annual
   datasets — see §8.**
7. `suggested_datasets_match_score` — subset semantics.
8. `nudge_match_score` — type OR + options subset, substring-matched.
9. `dashboard_created_score` — tri-state, see table below.
10. `dashboard_aoi_match_score` — dashboard must hold **exactly one** AOI; any other
    count scores 0. Reuses `expected_aoi_ids` / `expected_aoi_source`.
11. `dashboard_widgets_match_score` — multiset compare of `widget_type`.
12. `dashboard_widgets_valid_score` — content sanity: `insight` widgets need an
    `insight` payload, `map` widgets need a `tile_url`.

`subregion_match_score` and `guardrail_answer_score` **no longer exist.**

LLM-as-judge checks (`claude-haiku-4-5`, `temperature=0`, via `langchain_anthropic` in
`src/gnw_evals/utils/models.py`). Each writes a `*_reason` column alongside its score:

13. `charts_answer_score` — judges the **chart JSON** of *all* charts plus the decoded
    base64 `codeact_parts` (code, execution output, reasoning). It explicitly does **not**
    judge the prose insight; this file previously described it as judging
    `charts_data[0]["insight"]`, which is no longer the case.
14. `agent_answer_score` — judges `agent_state["messages"][-1].content`. Handles both a
    plain string (Claude) and a list-of-dicts (Gemini) shape.
15. `expected_text_match_score` — semantic-inclusion judge. Accepts behavioural
    instructions ("refuses because the dataset is annual"), not just literal text.
16. `clarification_requested_score` — detects whether the response *is* a clarification
    request, then compares to `expected_clarification`.

Two tri-state truth tables. **Note the clarification blank row — this file previously had
it wrong:**

| `expected_clarification` | agent asked? | score |
|---|---|---|
| `True` | yes / no | 1.0 / 0.0 |
| `False` | yes / no | 0.0 / **1.0** |
| blank → `None` | either | **`None` — the judge is never even called** |

> **Correction, 2026-07-30.** The old table claimed blank + a clarification scored 0.0 as
> an "unsolicited" penalty. `clarification_evaluator.py` now returns early on
> `expected_clarification is None`, so there is no such penalty and no LLM call.

`expected_dashboard_created` **does** carry that unsolicited penalty:

| `expected_dashboard_created` | created? | score |
|---|---|---|
| `True` | yes / no | 1.0 / 0.0 |
| `False` | yes / no | 0.0 / **1.0** |
| blank | yes | **0.0 — unsolicited dashboard** |
| blank | no | `None` |

`expected_clarification=False` still hands out free points in the printed "Clarification
Requested" metric line, but no longer enters `overall_score` (that gate is
`is not None` only for the dashboard check; clarification uses truthiness).

Judge behaviour: answer type is auto-classified as boolean / numeric / year /
named entity. Numeric comparisons pass within **5% relative tolerance**
(hardcoded in the judge prompt in `evaluators/llm_judges.py`). Boolean and year
require exact match. Named entities use semantic similarity.

> **Stale doc:** `SCORING_METHODOLOGY.md` says the judge is "Claude 3.5 Haiku via
> LangChain". The code uses `claude-haiku-4-5`.

Normalisation (`evaluators/utils.py`):

- `normalize_gadm_id`: `split("_")[0]`, `-` → `.`, lowercase.
- `normalize_value`: strips, maps `None`/`"None"`/blank to `""`.
- Dates: accepts `M/D/YYYY`, `YYYY-MM-DD`, `YYYY`. A bare `YYYY` becomes
  `YYYY-01-01` as a start date and `YYYY-12-31` as an end date.

> **Known bug, logged in `llm/TASKS.md`:** `normalize_gadm_id` discards everything
> after the underscore, so `USA.5_1` and `USA.5_2` both normalise to `usa.5` —
> different subregions score as a match. Treat `aoi_id_match_score` as an upper
> bound until fixed.

## 5. `overall_score` — and why not to lead with it

`BaseTestRunner._calculate_overall_score` collects scores conditionally, then
takes a flat mean rounded to 2dp:

```
overall_score = sum(valid_scores) / len(valid_scores)
```

Inclusion gates:

- `clarification_requested_score` only if `expected_clarification` is not `None`.
- `aoi_id_match_score` only if `expected_aoi_ids` is non-empty.
- `dataset_id_match_score`, `dataset_parameter_match_score` and
  `context_layer_match_score` on their own columns.
- `data_pull_exists_score` if **`expects_data_pull()`** — i.e. `expected_answer` is set,
  or `expected_dashboard_widgets` contains `insight`; and never when
  `expected_clarification is True`. It is no longer keyed off `expected_dataset_id`.
- `date_match_score` only if **both** dates provided.
- `suggested_datasets_match_score`, `nudge_match_score` on their own columns.
- Dashboard: `created` if the expectation `is not None` (deliberately not truthy, so
  `False` guardrail rows survive); `aoi_match` if created **and** `expected_aoi_ids`;
  `widgets_match` on its own column; `widgets_valid` if created.
- `charts_answer_score` and `agent_answer_score` both, if `expected_answer` set.
- `expected_text_match_score` if `expected_text` set.
- **All `None` → `overall_score = 0.0`, not `None`.** A row with no applicable
  expectations scores zero and counts as a failure in the pass-rate denominator — and
  because `_all_checks_passed` returns `True` when there are no scores, the progress line
  prints it as a **pass**. Seen live: gold 1-115 on 2026-07-30.

Pass threshold is `>= 0.7`. The harness itself prints *"warning: overall_score is
experimental and untested"*.

The flaw is dependency: the checks are a pipeline, not independent dimensions. If
AOI resolution fails, the answer is necessarily wrong, yet dataset/date/data-pull
still contribute passing points, so a broken test can clear 0.7. Denominators also
vary row to row, so scores are not commensurable across tests or eval sets.
Weighted scoring, pipeline grouping and dependency modelling are all logged as
open options in `llm/TASKS.md`.

**Report `agent_answer_score` plus the per-metric table. Mention `overall_score`
only with the caveat.**

## 6. Timeouts — no longer the dominant failure mode

**`--timeout` no longer exists**, and neither does the `timed_out` column. The httpx
client is hardcoded to `timeout=240.0` in `runners/api.py`. A slow row raises, is caught,
and becomes an error row with `overall_score = 0.0` — **counted as a failure**, not
excluded from the denominator as this file previously described.

The historical picture (the `20260328_144052` run: 33 timeouts of 60 tests, latencies
900–2132s) no longer holds. Two full runs of the 20 newest gold rows on 2026-07-30
recorded **zero timeouts**, avg latency 30–33s, max 77s — comfortably inside 240s. The
API got dramatically faster; `duration_seconds` also now measures only the API call, not
judge time, which accounts for part of the apparent change.

If long rows do reappear the only levers are editing that constant or running fewer rows.
Still worth reporting an error count alongside a pass rate.

## 7. Output artefacts

Written to `outputs/` (gitignored), prefixed
`{--output-filename}_{YYYYMMDD_HHMMSS}`; the default prefix is
`eval_results_{eval_set}_sample_{n}_workers_{n}_offset_{n}`.

- `_summary.csv` — scores, judge `*_reason` columns, `duration_seconds`, `trace_url`.
- `_detailed.csv` — expected vs actual side by side for every check.

**`_report.md` is no longer produced** — only the two CSVs. There is a `test_id` column,
so join on that; fall back to `query` only where `test_id` is blank (a blank id also
prints as `#N` in the progress output and cannot be targeted with `--test-id`).

Also present: `inspect_output.py` and `nb_heatmap_01.py` (marimo notebook) for
reading results, with UI selection of input file and eval set.

## 8. Known-awkward test categories

- **Annual datasets and date checks — the big one.** For Tree cover loss (4), Tree cover
  loss due to fires (10) and other annual data, the agent **always pulls the full
  available range and slices to the requested period in code.** It never issues a
  year-scoped pull. `evaluate_date_selection` reads `agent_state["start_date"]` first,
  falling back to the latest `statistics` entry, and which window lands there is
  inconsistent: on 2026-07-30, five identically-shaped multilingual TCL rows all asking
  about 2022 produced four recorded as `2022-01-01 → 2022-12-31` and one (1-104) as
  `2001-01-01 → 2025-12-31`. All five answered the 2022 figure correctly.

  So on annual-dataset rows `date_match_score` measures state bookkeeping, not whether the
  agent used the right year, and it flips between runs. **Leave the date columns empty
  there and let `expected_answer` carry the year** — a wrong year yields a wrong number.
  Keep date expectations for genuinely date-scoped pulls (DIST-ALERT, satellite imagery).

- **Relative dates ("past decade", "recent")** — the agent resolves against today, so
  expected dates drift and the eval decays. Use fixed ranges.

- **Comparative queries ("A or B?")** — the AOI comparison is set equality, so a
  multi-value expectation fails unless the agent selects exactly that set. Leaving
  `expected_aoi_ids` blank and relying on `expected_answer` is still the safer pattern,
  but multi-AOI rows are no longer *guaranteed* zero (see §3).

- **Satellite imagery rows** populate **no dataset and no dates** in agent state. Only
  `expected_aoi_ids` and `expected_text` are usable; a date or dataset expectation there
  fails on a correct answer.

- **Follow-up phrasing ("add that to the dashboard", "pick it as a layer")** is
  unreplayable — every row opens a fresh `thread_id`, so there is no prior turn.

## 8.1 Checks that vanish instead of failing

Four places where the worst outcome is *unmeasured* rather than scored 0, each making a
broken row look healthier than it is:

| Situation | Expected | Actual |
|---|---|---|
| Agent resolves **no AOI** | `aoi_id_match_score = 0` | `None` (`aoi_evaluator.py:54` early return) |
| Agent produces **no chart** | `charts_answer_score = 0` | `None` (needs non-empty `charts_json`) |
| **No dashboard created** | widget checks = 0 | all three dashboard sub-checks `None` |
| **No expectations at all** | `overall_score = None` | `0.0`, and prints as a pass (§5) |

On the 2026-07-30 run this cost **20 of 98** implied checks — 18 from six dashboard rows,
2 from answer rows that replied in prose with empty `charts_data`. Always reconcile the
checks the sheet implies against the checks that actually ran.

One further asymmetry: **`dataset_evaluator.py` withholds actual values unless an
expectation is already set.** You cannot discover the actual dataset or context layer from
a run without first guessing one — surface them by setting a throwaway expected value and
re-running.

## 9. Open work (`llm/TASKS.md`)

Redesign `overall_score` (weighting / pipeline grouping / dependency modelling);
verify the GADM normalisation false-positive; add row numbers to CSV output; handle the
non-E2E Q&A sheets and surface which checks a given file actually exercises; simplify and
split the test file; and extract a standalone column → logic → score document out of the
README.

Two items on that list are **already done**: multi-value AOI handling now reads the full
`aoi_selection.aois` list, and data-pull scoring is independent of `expected_dataset_id`
(gated by `expects_data_pull()` instead).

Newly identified, not yet in `TASKS.md`:

- The four vanishing-check cases in §8.1 should score 0, not `None`.
- `date_match_score` needs to know whether a dataset is annual, or gold rows on annual
  data need the date columns left empty by convention (§8).
- Blank `test_id` on gold rows breaks `--test-id` targeting and result joins.
- A run against prod silently mis-scores the nine dashboard/nudge rows (§2). Worth a
  guard that warns when a row's capability is absent from the target environment.

---

## Change Log

**2026-07-30 — reconciled against code at `7130857` after two full runs of the 20 newest
gold rows.** Companion operating manual: `.claude/CLAUDE.md`; run reports in
`.claude/reports/`.

Corrections to statements in this file that were wrong:

- Multi-value `expected_aoi_ids` is **no longer** a guaranteed 0 — the evaluator reads a
  list of AOIs (§3). The ~20 parent-child rows written off here are scoreable again.
- Blank `expected_clarification` + a clarification returns **`None`**, not 0.0. There is no
  unsolicited-clarification penalty; the dashboard check has one instead (§4).
- `data_pull_exists_score` is gated by `expects_data_pull()`, not `expected_dataset_id` (§5).
- All-`None` rows score **0.0**, not `None`, and print as a pass (§5).
- `--env`, `ENV_URLS`, `--timeout` and the `timed_out` column do not exist (§2, §6).
- `_report.md` is not produced (§7).
- `charts_answer_score` judges chart JSON + codeact reasoning across *all* charts, not
  `charts_data[0]["insight"]` (§4).
- Nine scores → **sixteen**; `subregion_match_score` and `guardrail_answer_score` removed (§4).
- Timeouts are no longer the dominant failure mode — zero across 40 row-runs (§6).

Added: prod capability gaps and the prod-only token (§2); per-column semicolon semantics
table (§3); sheet drift resolved (§3); the annual-dataset date finding (§8); vanishing
checks (§8.1); dashboard fetch step (§1).
