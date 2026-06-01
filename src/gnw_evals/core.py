import asyncio
import statistics
import time
from datetime import UTC, datetime

import click
import dotenv

from gnw_evals.data_handlers import CSVLoader, ResultExporter
from gnw_evals.runners import APITestRunner
from gnw_evals.utils.eval_types import ExpectedData, TestResult
from gnw_evals.utils.run_metadata import (
    RunSummaryContext,
    build_run_summary_context,
    fetch_gnw_api_metadata,
    print_run_summary_header,
)
from gnw_evals.utils.sheet_registry import EVAL_SETS, get_sheet_url

dotenv.load_dotenv()

_OVERALL_SCORE_FIELD = "overall_score"


def _check_scores_from_result(result: TestResult) -> list[tuple[str, float]]:
    """Return (field_name, score) pairs for per-check metrics on a result."""
    return [
        (field, value)
        for field, value in result.model_dump().items()
        if field.endswith("_score")
        and field != _OVERALL_SCORE_FIELD
        and value is not None
    ]


def _all_checks_passed(result: TestResult) -> bool:
    """Return whether every evaluated check scored 1.0 and the run had no error."""
    if result.error:
        return False
    scores = _check_scores_from_result(result)
    if not scores:
        return True
    return all(score == 1.0 for _, score in scores)


def _test_display_id(test_case, test_index: int) -> str:
    """Prefer CSV test_id; fall back to 1-based index."""
    test_id = getattr(test_case, "test_id", None) or ""
    if test_id:
        return test_id
    return f"#{test_index + 1}"


def _print_pass_progress() -> None:
    print(".", end="", flush=True)


def _print_failure_details(
    test_case,
    test_index: int,
    total_tests: int,
    result: TestResult,
    duration: float,
) -> None:
    """Print multi-line details for tests that did not pass all checks."""
    scores = _check_scores_from_result(result)
    checks_passed = sum(1 for _, score in scores if score == 1.0)
    checks_total = len(scores)
    test_id = _test_display_id(test_case, test_index)
    query = getattr(test_case, "query", "") or result.query

    print()
    print(
        f"[FAIL] {test_id} ({test_index + 1}/{total_tests}): "
        f"{checks_passed}/{checks_total} checks passed ({duration:.1f}s)",
    )
    if query:
        print(f"  query: {query[:120]}{'...' if len(query) > 120 else ''}")
    if result.error:
        print(f"  error: {result.error}")

    failed_checks = [(name, score) for name, score in scores if score != 1.0]
    for name, score in failed_checks:
        label = name.removesuffix("_score").replace("_", " ")
        print(f"  {label}: {score}")


def _build_default_output_filename(
    eval_set: str,
    sample_size: int,
    num_workers: int,
    offset: int,
) -> str:
    """Build default output filename prefix from run configuration."""
    return (
        f"eval_results_{eval_set}"
        f"_sample_{sample_size}"
        f"_workers_{num_workers}"
        f"_offset_{offset}"
    )


async def run_single_test(
    runner,
    test_case,
    test_index,
    total_tests,
) -> TestResult:
    """Run a single test case."""
    start_time = time.time()

    # Convert test case to ExpectedData (remove query field)
    test_dict = test_case.model_dump()
    expected_data = ExpectedData(
        **{k: v for k, v in test_dict.items() if k != "query"},
    )
    result = await runner.run_test(test_case.query, expected_data)
    duration = time.time() - start_time
    result.duration_seconds = duration

    if _all_checks_passed(result):
        _print_pass_progress()
    else:
        _print_failure_details(test_case, test_index, total_tests, result, duration)

    return result


_SCORE_FIELDS = [
    "overall_score",
    "aoi_id_match_score",
    "dataset_id_match_score",
    "dataset_parameter_match_score",
    "context_layer_match_score",
    "data_pull_exists_score",
    "date_match_score",
    "charts_answer_score",
    "agent_answer_score",
    "expected_text_match_score",
    "clarification_requested_score",
]


def _aggregate_trial_results(trial_results: list[TestResult]) -> TestResult:
    """Aggregate N trial results into a single result using mean and std."""
    base = trial_results[0].model_copy(deep=True)
    base.num_trials = len(trial_results)

    for field in _SCORE_FIELDS:
        values = [v for r in trial_results if (v := getattr(r, field)) is not None]
        if values:
            mean = round(sum(values) / len(values), 4)
            std = round(statistics.stdev(values), 4) if len(values) > 1 else 0.0
            setattr(base, field, mean)
            setattr(base, f"{field}_std", std)
        else:
            setattr(base, field, None)
            setattr(base, f"{field}_std", None)

    return base


async def run_trials_for_test(
    runner,
    test_case,
    test_index: int,
    total_tests: int,
    num_trials: int,
) -> TestResult:
    """Run a single test case num_trials times and return an aggregated result."""
    if num_trials == 1:
        return await run_single_test(runner, test_case, test_index, total_tests)

    trial_results = []
    for t in range(num_trials):
        print(f"  [trial {t + 1}/{num_trials}] ", end="")
        result = await run_single_test(runner, test_case, test_index, total_tests)
        trial_results.append(result)

    return _aggregate_trial_results(trial_results)


async def run_csv_tests(config) -> list[TestResult]:
    """Run E2E tests using CSV data files with parallel execution."""
    print(f"Loading test data from: {config.test_file}")

    # Load test data
    loader = CSVLoader()
    test_cases = loader.load_test_data(
        config.test_file,
        config.sample_size,
        config.test_group_filter,
        config.status_filter,
        config.random_seed,
        config.offset,
    )
    effective_num_workers = min(config.num_workers, 5, len(test_cases))
    num_trials = getattr(config, "num_trials", 1)
    print(
        f"Running {len(test_cases)} tests with {effective_num_workers} workers"
        + (f", {num_trials} trials each" if num_trials > 1 else "")
        + "...",
    )

    # Setup test runner
    runner = APITestRunner(
        api_base_url=config.api_base_url,
        api_token=config.api_token,
    )
    print(f"Using API endpoint: {config.api_base_url}")

    run_started_at = datetime.now(UTC)
    api_metadata = await fetch_gnw_api_metadata(config.api_base_url)

    # Run tests in parallel
    start_time = time.time()

    if effective_num_workers <= 1:
        # Sequential execution for single worker
        results = []
        for i, test_case in enumerate(test_cases):
            result = await run_trials_for_test(
                runner,
                test_case,
                i,
                len(test_cases),
                num_trials,
            )
            results.append(result)
    else:
        # Parallel execution with semaphore
        semaphore = asyncio.Semaphore(effective_num_workers)

        async def run_test_with_semaphore(test_case, test_index):
            async with semaphore:
                return await run_trials_for_test(
                    runner,
                    test_case,
                    test_index,
                    len(test_cases),
                    num_trials,
                )

        # Create tasks for all tests
        tasks = [
            run_test_with_semaphore(test_case, i)
            for i, test_case in enumerate(test_cases)
        ]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

    total_duration = time.time() - start_time
    print()
    print(f"All tests completed in {total_duration:.1f} seconds")

    # Print summary
    summary_context = build_run_summary_context(
        api_base_url=config.api_base_url,
        run_timestamp=run_started_at,
        api_metadata=api_metadata,
        durations=[
            float(r.duration_seconds)
            for r in results
            if isinstance(r.duration_seconds, int | float)
        ],
    )
    _print_csv_summary(results, summary_context)
    return results


def _print_csv_summary(
    results: list[TestResult],
    summary_context: RunSummaryContext | None = None,
) -> None:
    """Print CSV test summary statistics."""
    total_tests = len(results)
    if total_tests == 0:
        return

    passed = sum(1 for r in results if r.overall_score >= 0.7)
    num_trials = max(r.num_trials for r in results)
    multi_trial = num_trials > 1

    # Label column width based on longest label ("Dataset Parameter Match" = 23 chars)
    LABEL_WIDTH = 25

    def _metric_line(label: str, score_field: str) -> str:
        label_col = f"{label}:"
        scores = [v for r in results if (v := getattr(r, score_field)) is not None]
        if not scores:
            return f"{label_col:<{LABEL_WIDTH}} {0:>3} / {0:>3}"
        if multi_trial:
            mean = sum(scores) / len(scores)
            std_values = [
                v
                for r in results
                if (v := getattr(r, f"{score_field}_std", None)) is not None
            ]
            avg_std = sum(std_values) / len(std_values) if std_values else 0.0
            return f"{label_col:<{LABEL_WIDTH}} {mean:.2f} ± {avg_std:.2f} (n={len(scores)}, {num_trials} trials)"
        evaluated = len(scores)
        n_passed = sum(1 for s in scores if s == 1.0)
        avg = n_passed / evaluated
        return f"{label_col:<{LABEL_WIDTH}} {n_passed:>3} / {evaluated:>3} ({avg:.2f})"

    print(f"\n{'=' * 50}")
    print("EVALUATION SUMMARY")
    print(f"{'=' * 50}")
    if summary_context is not None:
        print_run_summary_header(summary_context)
    print(f"Tests Run (after filters): {total_tests}")
    if multi_trial:
        print(f"Trials per test: {num_trials}")
    print()

    # Agent Answer first - most important metric
    print(_metric_line("Agent Answer", "agent_answer_score"))
    print()

    # Component-specific stats
    print(_metric_line("AOI ID Match", "aoi_id_match_score"))
    print(_metric_line("Dataset ID Match", "dataset_id_match_score"))
    print(_metric_line("Dataset Parameter Match", "dataset_parameter_match_score"))
    print(_metric_line("Context Layer Match", "context_layer_match_score"))
    print(_metric_line("Data Pull Exists", "data_pull_exists_score"))
    print(_metric_line("Date Match", "date_match_score"))
    print(_metric_line("Charts Answer", "charts_answer_score"))
    print(_metric_line("Expected Text Match", "expected_text_match_score"))
    print(_metric_line("Clarification Requested", "clarification_requested_score"))

    suggested_datasets_scores = [
        r.suggested_datasets_match_score
        for r in results
        if r.suggested_datasets_match_score is not None
    ]
    print(_metric_line("Suggested Datasets", suggested_datasets_scores))

    # Experimental section
    print()
    print("(warning: overall_score is experimental and untested)")
    print(
        f"Tests with overall score ≥0.7:  {passed:>{3}} / {total_tests:>{3}} ({passed / total_tests:.1%})",
    )
    print()


@click.command()
@click.option(
    "--api-base-url",
    default="https://api.staging.globalnaturewatch.org",
    envvar="API_BASE_URL",
    help="Base URL for API tests (can also be set via API_BASE_URL env var)",
)
@click.option(
    "--api-token",
    default=None,
    envvar="API_TOKEN",
    help="API token for authentication (can also be set via API_TOKEN env var)",
)
@click.option(
    "--sample-size",
    default=5,
    type=int,
    envvar="SAMPLE_SIZE",
    help="Sample size: 1 means run single test (CI/CD friendly), -1 means run all rows (can also be set via SAMPLE_SIZE env var)",
)
@click.option(
    "--eval-set",
    default="gold",
    type=click.Choice([*list(EVAL_SETS.keys()), "all"], case_sensitive=False),
    envvar="EVAL_SET",
    help="Which eval set to run: gold, location_id, dataset_id, dataset_interpretation, analysis_results, analysis_interpretation, guardrail, date_selection, or all (can also be set via EVAL_SET env var)",
)
@click.option(
    "--test-file",
    default=None,
    envvar="TEST_FILE",
    help="Path or URL to test dataset CSV file (relative to project root) (can also be set via TEST_FILE env var)",
)
@click.option(
    "--test-group-filter",
    default=None,
    envvar="TEST_GROUP_FILTER",
    help="Filter by test_group column (can also be set via TEST_GROUP_FILTER env var)",
)
@click.option(
    "--status-filter",
    default=None,
    envvar="STATUS_FILTER",
    help="Filter by status column (comma-separated values) (can also be set via STATUS_FILTER env var)",
)
@click.option(
    "--output-filename",
    default=None,
    envvar="OUTPUT_FILENAME",
    help="Custom filename (timestamp will be appended) (can also be set via OUTPUT_FILENAME env var)",
)
@click.option(
    "--num-workers",
    default=1,
    type=int,
    envvar="NUM_WORKERS",
    help="Number of parallel workers for test execution (can also be set via NUM_WORKERS env var)",
)
@click.option(
    "--random-seed",
    default=0,
    type=int,
    envvar="RANDOM_SEED",
    help="Random seed for sampling (0 means no random sampling) (can also be set via RANDOM_SEED env var)",
)
@click.option(
    "--offset",
    default=0,
    type=int,
    envvar="OFFSET",
    help="Offset for getting subset. Ignored if random_seed is not 0 (can also be set via OFFSET env var)",
)
@click.option(
    "--num-trials",
    default=1,
    type=int,
    envvar="NUM_TRIALS",
    help="Number of trials per test for robustness measurement (can also be set via NUM_TRIALS env var)",
)
def run_evals(
    api_base_url: str,
    api_token: str | None,
    sample_size: int,
    eval_set: str,
    test_file: str | None,
    test_group_filter: str | None,
    status_filter: str | None,
    output_filename: str | None,
    num_workers: int,
    random_seed: int,
    offset: int,
    num_trials: int,
):
    """Run main E2E test function for CSV based evaluation."""
    # Validate API token
    if not api_token:
        raise click.BadParameter(
            "API token is required. Provide --api-token or set API_TOKEN environment variable.",
        )

    # Validate: user cannot specify both --eval-set (non-default) and --test-file (custom)
    if test_file and eval_set != "gold":
        raise click.BadParameter(
            "Cannot specify both --test-file and --eval-set. "
            "Use --eval-set to select a predefined sheet, or --test-file for a custom file.",
        )

    # Handle custom test file (bypass eval_set system)
    if test_file:
        _run_custom_test_file(
            api_base_url=api_base_url,
            api_token=api_token,
            sample_size=sample_size,
            test_file=test_file,
            test_group_filter=test_group_filter,
            status_filter=status_filter,
            output_filename=output_filename,
            num_workers=num_workers,
            random_seed=random_seed,
            offset=offset,
            num_trials=num_trials,
        )
        return

    # Determine which eval sets to run
    eval_sets_to_run = list(EVAL_SETS.keys()) if eval_set == "all" else [eval_set]

    # Collect results from all eval sets
    all_results = []

    for i, current_eval_set in enumerate(eval_sets_to_run, 1):
        # Print header for multi-set runs
        if len(eval_sets_to_run) > 1:
            print(f"\n{'=' * 70}")
            print(f"EVAL SET {i}/{len(eval_sets_to_run)}: {current_eval_set}")
            print(f"{'=' * 70}\n")

        # Run this eval set
        results = _run_single_eval_set(
            api_base_url=api_base_url,
            api_token=api_token,
            sample_size=sample_size,
            eval_set=current_eval_set,
            test_file=None,
            test_group_filter=test_group_filter,
            status_filter=status_filter,
            output_filename=None,
            num_workers=num_workers,
            random_seed=random_seed,
            offset=offset,
            num_trials=num_trials,
        )

        # Tag results with eval_set and accumulate
        if results:
            for result in results:
                result.eval_set = current_eval_set
            all_results.extend(results)

    # Write combined CSV
    if all_results:
        exporter = ResultExporter()
        final_output = output_filename or _build_default_output_filename(
            eval_set=eval_set,
            sample_size=sample_size,
            num_workers=num_workers,
            offset=offset,
        )
        exporter.save_results_to_csv(all_results, final_output)
    else:
        print("\n❌ No results collected from any eval set")


def _run_custom_test_file(
    api_base_url: str,
    api_token: str,
    sample_size: int,
    test_file: str,
    test_group_filter: str | None,
    status_filter: str | None,
    output_filename: str | None,
    num_workers: int,
    random_seed: int,
    offset: int,
    num_trials: int = 1,
) -> None:
    """Run evals with a custom test file (not from standard eval sets).

    This function handles the case where user provides --test-file directly.
    Results are tagged with eval_set = "custom".
    """
    print("\nRunning with custom test file...")

    results = _run_single_eval_set(
        api_base_url=api_base_url,
        api_token=api_token,
        sample_size=sample_size,
        eval_set="custom",
        test_file=test_file,
        test_group_filter=test_group_filter,
        status_filter=status_filter,
        output_filename=None,
        num_workers=num_workers,
        random_seed=random_seed,
        offset=offset,
        num_trials=num_trials,
    )

    # Tag results with eval_set = "custom"
    for result in results:
        result.eval_set = "custom"

    # Write CSV
    if results:
        exporter = ResultExporter()
        final_output = output_filename or _build_default_output_filename(
            eval_set="custom",
            sample_size=sample_size,
            num_workers=num_workers,
            offset=offset,
        )
        exporter.save_results_to_csv(results, final_output)
        print(f"\n✓ Results saved: {len(results)} tests")
    else:
        print("\n❌ No results collected")


def _run_single_eval_set(
    api_base_url: str,
    api_token: str,
    sample_size: int,
    eval_set: str,
    test_file: str | None,
    test_group_filter: str | None,
    status_filter: str | None,
    output_filename: str | None,
    num_workers: int,
    random_seed: int,
    offset: int,
    num_trials: int = 1,
) -> list[TestResult]:
    """Run evals for a single eval set. Internal helper function.

    Returns:
        List of TestResult objects, or empty list if error occurs

    """
    # Resolve test file for single eval set
    if test_file:
        # User provided a custom test file
        resolved_test_file = test_file
        resolved_eval_set = "custom"
    else:
        # Use eval_set to determine which sheet
        resolved_test_file = get_sheet_url(eval_set)
        resolved_eval_set = eval_set

    print(
        f"""
========================
EVALUATION CONFIGURATION
========================
  API Base URL:      {api_base_url}
  Eval Set:          {resolved_eval_set}
  Test File:         {resolved_test_file}
  Sample Size:       {sample_size}
  Test Group Filter: {test_group_filter or "None"}
  Status Filter:     {status_filter or "None"}
  Output Filename:   {output_filename or "Auto-generated"}
  Num Workers:       {num_workers}
  Num Trials:        {num_trials}
  Random Seed:       {random_seed}
  Offset:            {offset}
========================
""",
    )

    # Validate inputs
    if sample_size < -1:
        raise click.BadParameter("SAMPLE_SIZE must be >= -1")
    if num_workers < 1:
        raise click.BadParameter("NUM_WORKERS must be >= 1")

    # Parse status_filter from comma-separated string to list
    status_filter_list = None
    if status_filter:
        status_filter_list = [s.strip() for s in status_filter.split(",") if s.strip()]

    # Create a simple config object
    class Config:
        def __init__(self):
            self.api_base_url = api_base_url
            self.api_token = api_token
            self.sample_size = sample_size
            self.test_file = resolved_test_file
            self.test_group_filter = test_group_filter
            self.status_filter = status_filter_list
            self.output_filename = output_filename
            self.num_workers = num_workers
            self.random_seed = random_seed
            self.offset = offset
            self.num_trials = num_trials

    config = Config()
    try:
        results = asyncio.run(run_csv_tests(config))
        return results
    except ValueError as e:
        print(f"❌ ERROR: {e}")
        return []  # Return empty list on error


if __name__ == "__main__":
    run_evals()
