# Global Nature Watch Agent E2E Testing

## Quickstart

Install the package and its dependencies into your env

```bash
uv sync
```

Copy the example env file and set your **GNW machine user key** and
**Anthropic API key** in the new `.env` file:

```bash
cp .env.example .env
```

Then run the evals like this

```bash
uv run gnw_evals
```

By default this will read tests from a google sheet with
gold standard tests and evaluate the **production** environment.

To see all available config options:

```bash
uv run gnw_evals --help
```

All CLI flags can also be set via environment variables in `.env`.

## Evaluation Method Overview

The E2E testing framework evaluates the complete agent workflow by testing four core tools:

1. **AOI Selection** (`pick_aoi`) - Evaluates location selection accuracy
2. **Dataset Selection** (`pick_dataset`) - Evaluates dataset choice accuracy
3. **Data Pull** (`pull_data`) - Evaluates data retrieval success
4. **Final Answer** (`generate_insights`) - Evaluates answer quality using LLM-as-a-judge
5. **Guardrail / Metadata** - Evaluates free-text factual answers (citations, methodology, coverage) using a separate LLM judge

**For detailed scoring methodology and calculation details, see [SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md).**

## Test Dataset Structure

### Multiple Values in Test Cases

When a test case can have multiple valid values for a field (e.g., accepting multiple datasets), separate the values with semicolons (;). For example:

- `expected_aoi_ids = "IND.21_1;IND.27_1"` - Test passes if either Odisha (21) or Maharashtra (27) is selected
- `expected_dataset_id = "0;1"` - Test passes if either dataset 0 or 1 is selected
- `expected_context_layer = "driver;natural_lands"` - Test passes if either context layer is selected

### Columns

The eval harness executes checks based on `expected_*` columns. Where an expected value is not provided (empty or missing column), the corresponding score is skipped.

**Always required:**
- **`query`** - The user query to test

**Expected value columns** (provide to enable corresponding score):
- `expected_aoi_ids` - Expected AOI / GADM identifier
- `expected_subregion` - Expected subregion
- `expected_dataset_id` - Expected dataset ID (0–8 for current datasets)
- `expected_context_layer` - Expected context layer
- `expected_dataset_name` - Expected dataset name (reference only, not evaluated)
- `expected_start_date` - Expected start date (YYYY or YYYY-MM-DD)
- `expected_end_date` - Expected end date (YYYY or YYYY-MM-DD)
- `expected_answer` - Expected answer for LLM-as-a-judge comparison (numeric, boolean, named entity, or year)
- `expected_clarification` - Set to `True` if the agent should request clarification rather than answer
- `expected_guardrail_answer` - Expected free-text answer for metadata/citation/methodology queries. Uses a separate LLM judge that checks factual content rather than applying numeric/boolean rules. Use this instead of `expected_answer` for guardrail-type queries.

**Optional metadata columns:**
- `priority` - Test priority (`high`, `medium`, `low`)
- `test_group` - Test grouping for filtering (e.g., `dataset`, `rel-accuracy`, `abs-accuracy`)
- `status` - Execution status. Use `--status-filter` to filter:
  - `ready` - Ready to run (default)
  - `rerun` - Should be re-executed
  - `skip` - Skip during execution

### Golden eval set

For the GOLDEN eval set, recommended columns (no empty cells):
- `query`
- `test_group`, `status`
- `expected_aoi_ids`, `expected_dataset_id`, `expected_start_date`, `expected_end_date`, `expected_answer`, `expected_clarification`

**See [GOLDENSET_GUIDELINES.md](GOLDENSET_GUIDELINES.md) for best practices.**

## Running E2E Tests

### Targeting environments

Use `--env` to select the target environment (defaults to `prod`):

```bash
# Run against production (default)
uv run gnw_evals --env prod

# Run against staging
uv run gnw_evals --env staging

# Run against a custom URL (e.g. local dev) — overrides --env
uv run gnw_evals --api-base-url http://localhost:8000
```

Environment resolution priority:
```
--api-base-url / API_BASE_URL  >  --env / ENV  >  default (prod)
```

### Running against a local CSV

```bash
# Run against a local test file instead of the remote spreadsheet
uv run gnw_evals --test-file data/my_tests.csv --sample-size -1
```

Place local test files in `data/`. The `data/` directory is gitignored.

### Verbose output

Use `--verbose` to print per-test diagnostics as tests complete — useful for monitoring long runs:

```bash
uv run gnw_evals --verbose --test-file data/gold-28032026.csv --sample-size -1
```

For real-time log output (disables Python stdout buffering):

```bash
PYTHONUNBUFFERED=1 uv run gnw_evals --verbose
```

### Timeout

Use `--timeout` to control how long (in seconds) the eval client waits for the API to respond before marking a test as timed out. Default is 240s.

```bash
# 5 minute timeout
uv run gnw_evals --timeout 300

# No timeout (let API run to completion)
uv run gnw_evals --timeout 0
```

Timed-out tests are excluded from the pass rate denominator and flagged with `timed_out=True` in the output CSV.

### Usage Examples

```bash
# Full gold set run (env vars set in .env)
uv run gnw_evals --verbose --test-file data/gold-28032026.csv --sample-size -1 --num-workers 10

# Sample run against staging
uv run gnw_evals --env staging --sample-size 5 --output-filename "staging_sample"

# Filter by test group or status
uv run gnw_evals --test-group-filter rel-accuracy
uv run gnw_evals --status-filter ready,rerun

# Run all eval sets
uv run gnw_evals --eval-set all --sample-size -1
```

## Output Files

Each run generates three files in the `outputs/` directory:

1. **`*_summary.csv`** — Query and scores only
2. **`*_detailed.csv`** — Expected vs actual values side-by-side, including:
   - All score fields
   - `timed_out` flag
   - `latency` (wall-clock seconds from test start to completion)
   - `guardrail_answer_score`, `expected_guardrail_answer`, `actual_guardrail_answer`
3. **`*_report.md`** — Human-readable markdown summary with metric table and per-test results

## Scoring Summary

Individual scores are **binary** (0 or 1, or `None` if not evaluated). The overall score is the **simple average** of all applicable scores:

```
overall_score = sum(valid_scores) / count(valid_scores)
```

Scores are only calculated when the corresponding `expected_*` value is provided.

**Pass threshold:** ≥ 0.7 (70%)

Tests with `overall_score = None` (no applicable metrics, or timed out) are excluded from the pass rate denominator.

**For complete details on score calculation, see [SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md).**

---

## Common Issues and Troubleshooting

1. **Empty results:** Check that `status` column contains `ready` or `rerun`, and use `--status-filter ready,rerun`. Without `--status-filter`, all rows are included regardless of status.
2. **AOI mismatches:** Verify GADM ID format (e.g., `USA.5_1` not `USA_5_1`)
3. **High timeout rate:** Try `--timeout 0` on a small sample to see if the API completes given enough time, or run against staging during off-peak hours.
4. **Comparative queries (A or B?):** The agent only stores one AOI in state for comparative queries. Leave `expected_aoi_ids` empty for these and rely on `expected_answer` to validate correctness.
5. **Relative date queries ("past decade"):** Agent interprets dates relative to today, so expected dates will drift. Use fixed date ranges in queries for deterministic evals.
6. **Slow log output:** Set `PYTHONUNBUFFERED=1` to flush stdout in real time.
7. **Parallel execution:** Reduce `--num-workers` if hitting rate limits.
8. **Missing arguments:** Use `--help` to see all available options and their defaults.
