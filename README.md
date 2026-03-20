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
gold standard tests and evaluate the staging environment.

You can change multiple aspects of the runner like what tests to run
and parallelization of the tests.

To see the available config options run

```bash
uv run gnw_evals --help
```

You can also set all of these variables in the `.env` file as
an alternative to passing them on the cli command.

## Evaluation Method Overview

The E2E testing framework evaluates the complete agent workflow by testing four core tools:

1. **AOI Selection** (`pick_aoi`) - Evaluates location selection accuracy
2. **Dataset Selection** (`pick_dataset`) - Evaluates dataset choice accuracy
3. **Data Pull** (`pull_data`) - Evaluates data retrieval success
4. **Final Answer** (`generate_insights`) - Evaluates answer quality using LLM-as-a-judge

**For detailed scoring methodology and calculation details, see [SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md).**

## Test Dataset Structure

### Multiple Values in Test Cases

When a test case can have multiple valid values for a field (e.g., comparing multiple AOIs, accepting multiple datasets), separate the values with semicolons (;). For example:

- `expected_aoi_ids = "IND.21_1;IND.27_1"` - Test passes if either Odisha (21) or Maharashtra (27) is selected
- `expected_dataset_id = "0;1"` - Test passes if either dataset 0 or 1 is selected
- `expected_context_layer = "driver;natural_lands"` - Test passes if either driver or natural_lands context layer is selected

### Columns (Required for Tests)

The Eval harness will execute tests based on "expected" columns and values when
they are provided. Where the necessary expected value is not provided (either
the column does not exist or the cell is empty), the corresponding score is not
computed. 

The following column(s) are always required for the test to run :
- **`query`** - The user query to test (string)


For the corresponding score to be computed, expected values must be provided. The `expected_*` columns must be named exactly as follows:
- `expected_aoi_ids`  - Expected AOI identifier / GADM id. 
- `expected_subregion` - Expected subregion 
- `expected_dataset_id` - Expected dataset ID (0-8 for current datasets). For queries that may match multiple datasets, separate IDs with semicolons (e.g., "0;1" for DIST-ALERT and another dataset). Can be empty if not applicable.
- `expected_context_layer` - Expected context layer (varies by dataset). Multiple values can be separated by semicolons if multiple layers are acceptable. Can be empty if not applicable.
- `expected_dataset_name` - Expected dataset name (for reference, not evaluated)
- `expected_start_date` - Expected start date (YYYY-MM-DD or YYYY). For date ranges, use the earliest expected date.
- `expected_end_date` - Expected end date (YYYY-MM-DD or YYYY). For date ranges, use the latest expected date.
- `expected_answer` - Expected answer text for LLM-as-a-judge comparison. Can be empty if not applicable.
- `expected_clarification` - Boolean flag indicating whether agent should request clarification instead of completing the task (default: `False`)
- `expected_` 


Other columns, optional: 
- **`priority`** - Test priority ("high", "medium", "low")
- **`test_group`** - Test grouping for filtering (e.g., "dataset", "rel-accuracy", "abs-accuracy" etc). Default: "unknown"
- **`status`** - Test execution status. Default: "ready". Use `--status-filter` to filter by status:
  - `"ready"` - Test is ready to run (default for new tests)
  - `"rerun"` - Test should be re-executed (e.g., after fixing issues)
  - `"skip"` - Test should be skipped/ignored during execution
  - **Note:** If `--status-filter` is not provided, all rows are included regardless of status


### Golden eval set

For the GOLDEN eval set, it is recommended to include the following complete columns (fill in all values, no empty cells): 
- `query`
- `test_group`, `status` 
- Expected columns: `expected_aoi_ids`, `expected_dataset_id`, `expected_start_date`,  `expected_end_date`,  `expected_answer`, `expected_clarification`  

**A "golden set" for evaluations should follow best practice. A summary of these best practices is provided here: [GOLDENSET_GUIDELINES.md](GOLDENSET_GUIDELINES.md).**

## Running E2E Tests

Simple end-to-end agent test runner for API testing. 

Evals source. By default, gnw_evals will run tests against the live spreadsheet, URL specified in the `.env` file.

### Usage Examples: Basic

```bash
# Basic run with manual API token specification
uv run gnw_evals --api-token your_token

# With custom API endpoint instead of GNW Staging or GNW production
uv run gnw_evals --api-token your_token --api-base-url http://localhost:8000

# Run specific number of GOLDEN SET tests (default sample size is 5)
uv run gnw_evals --api-token your_token --sample-size 10

```

Suggested basis usage
* Add the following in the .env file: 
    * API_TOKEN 
    * ANTHROPIC_API_KEY
    * SPREADSHEET_ID
    * NUM_WORKERS=5

```bash
# run first 5 rows of the LOCATION ID tests
uv run gnw_evals --sample-size 5 --eval-set location_id --output-filename "sample_locationid_evals" 

# run all tests 
uv run gnw_evals --sample-size -1 --eval-set all --output-filename "all_evals" 

```

### Usage Examples: selecting eval sets and filters

Running GOLDEN SET filters in the spreadsheet
* REMINDER: Make sure the spreadsheet is properly specified in the `.env` file using `SPREADSHEET_ID`


```bash

# Run all GOLDEN SET tests
uv run gnw_evals --api-token your_token --sample-size -1

# Filter by test group
uv run gnw_evals --api-token your_token --test-group-filter rel-accuracy

# Filter by status (comma-separated)
uv run gnw_evals --api-token your_token --status-filter ready,rerun

```

The framework supports multiple specialized eval sets, not just the GOLDEN SET
- `gold` - Full E2E golden set (default)
- `location_id` - Location/AOI identification tests
- `dataset_id` - Dataset selection tests
- `date_selection` - Date selection tests
- and others.. 

**Note:** 
- REMINDER: Make sure the spreadsheet is properly specified in the `.env` file using `SPREADSHEET_ID`
- When using `--eval-set all`, separate output files are generated for each eval set (e.g., `gold_test_TIMESTAMP.csv`, `location_id_test_TIMESTAMP.csv`, etc.)
- You cannot use `--eval-set` and `--test-file` together. Use one or the other.

```bash
# Default (gold set)
uv run gnw_evals

# Run specific eval set
uv run gnw_evals --eval-set location_id --sample-size 10

# Run all eval sets (set and forget for multi-hour runs)
uv run gnw_evals --eval-set all --sample-size -1

# Via environment variable
export EVAL_SET=dataset_id
uv run gnw_evals
```

Custom evals: Run eval tests in a local CSV  file

```bash
# Run eval tests in a custom CSV  file
uv run gnw_evals --api-token your_token --test-file data/my_tests.csv
```

## Output Files

Tests generate two CSV files in the `outputs/` directory at the project root:

1. **`outputs/*_summary.csv`** - Query and scores only
2. **`outputs/*_detailed.csv`** - Expected vs actual values side-by-side


## Scoring Summary

Individual scores are **binary** (0 or 1, or `None` if not evaluated). The overall score is the **simple average** of all applicable scores:

```
overall_score = sum(valid_scores) / count(valid_scores)
```

Scores are only calculated when the corresponding `expected_*` value is provided in the test case.

**Pass Threshold:** ≥ 0.7 (70%)

**For complete details on score calculation, see [SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md).**

--- 

## Common Issues and Troubleshooting

1. **Empty Results:** Check that `status` column contains "ready" or "rerun", and use `--status-filter ready,rerun` to filter by status. Without `--status-filter`, all rows are included regardless of status.
2. **AOI Mismatches:** Verify GADM ID format (e.g., "USA.5_1" not "USA_5_1")
5. **Parallel Execution:** Reduce `--num-workers` if hitting rate limits
6. **Missing Arguments:** Use `--help` to see all available options and their defaults
