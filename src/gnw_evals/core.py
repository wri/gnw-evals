import asyncio
import time

import click
import dotenv

from gnw_evals.data_handlers import CSVLoader, ResultExporter
from gnw_evals.runners import APITestRunner
from gnw_evals.utils.eval_types import ExpectedData, TestResult
from gnw_evals.utils.sheet_registry import (
    EVAL_SET_PRIMARY_METRIC,
    EVAL_SETS,
    get_sheet_url,
)

dotenv.load_dotenv()


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
    print(f"[STARTED]   Test {test_index + 1}/{total_tests}: {test_case.query[:60]}...")

    # Convert test case to ExpectedData (remove query field)
    test_dict = test_case.model_dump()
    expected_data = ExpectedData(
        **{k: v for k, v in test_dict.items() if k != "query"},
    )
    result = await runner.run_test(test_case.query, expected_data)

    # Print completion with timing
    duration = time.time() - start_time
    all_scores = [
        v
        for k, v in result.model_dump().items()
        if k.endswith("_score") and k != "overall_score" and v is not None
    ]
    checks_passed = sum(1 for s in all_scores if s == 1.0)
    checks_total = len(all_scores)
    print(
        f"[COMPLETED] Test {test_index + 1}/{total_tests}: {checks_passed} out of {checks_total} checks passed ({duration:.1f}s)",
    )

    return result


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
    print(
        f"Running {len(test_cases)} tests with {effective_num_workers} workers...",
    )

    # Setup test runner
    runner = APITestRunner(
        api_base_url=config.api_base_url,
        api_token=config.api_token,
    )
    print(f"Using API endpoint: {config.api_base_url}")

    # Run tests in parallel
    start_time = time.time()

    if effective_num_workers <= 1:
        # Sequential execution for single worker
        results = []
        for i, test_case in enumerate(test_cases):
            result = await run_single_test(
                runner,
                test_case,
                i,
                len(test_cases),
            )
            results.append(result)
    else:
        # Parallel execution with semaphore
        semaphore = asyncio.Semaphore(effective_num_workers)

        async def run_test_with_semaphore(test_case, test_index):
            async with semaphore:
                return await run_single_test(
                    runner,
                    test_case,
                    test_index,
                    len(test_cases),
                )

        # Create tasks for all tests
        tasks = [
            run_test_with_semaphore(test_case, i)
            for i, test_case in enumerate(test_cases)
        ]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

    total_duration = time.time() - start_time
    print(f"\nAll tests completed in {total_duration:.1f} seconds")

    # Print summary
    _print_csv_summary(results)
    return results


def _print_csv_summary(results: list[TestResult]) -> None:
    """Print CSV test summary statistics."""
    total_tests = len(results)
    if total_tests == 0:
        return

    passed = sum(1 for r in results if r.overall_score >= 0.7)

    # Label column width based on longest label ("Dataset Parameter Match" = 23 chars)
    LABEL_WIDTH = 25

    def _metric_line(label: str, scores: list) -> str:
        label_col = f"{label}:"
        evaluated = len(scores)
        passed = sum(1 for s in scores if s == 1.0)
        if evaluated > 0:
            avg = passed / evaluated
            return (
                f"{label_col:<{LABEL_WIDTH}} {passed:>3} / {evaluated:>3} ({avg:.2f})"
            )
        return f"{label_col:<{LABEL_WIDTH}} {0:>3} / {0:>3}"

    print(f"\n{'=' * 50}")
    print("SIMPLE E2E TEST SUMMARY")
    print(f"{'=' * 50}")
    print(f"Tests Run (after filters): {total_tests}")
    print()

    # Agent Answer first - most important metric
    agent_answer_scores = [
        r.agent_answer_score for r in results if r.agent_answer_score is not None
    ]
    print(_metric_line("Agent Answer", agent_answer_scores))
    print()

    # Component-specific stats
    aoi_scores = [
        r.aoi_id_match_score for r in results if r.aoi_id_match_score is not None
    ]
    print(_metric_line("AOI ID Match", aoi_scores))

    dataset_id_scores = [
        r.dataset_id_match_score
        for r in results
        if r.dataset_id_match_score is not None
    ]
    print(_metric_line("Dataset ID Match", dataset_id_scores))

    dataset_parameter_scores = [
        r.dataset_parameter_match_score
        for r in results
        if r.dataset_parameter_match_score is not None
    ]
    print(_metric_line("Dataset Parameter Match", dataset_parameter_scores))

    context_scores = [
        r.context_layer_match_score
        for r in results
        if r.context_layer_match_score is not None
    ]
    print(_metric_line("Context Layer Match", context_scores))

    data_pull_scores = [
        r.data_pull_exists_score
        for r in results
        if r.data_pull_exists_score is not None
    ]
    print(_metric_line("Data Pull Exists", data_pull_scores))

    date_scores = [
        r.date_match_score for r in results if r.date_match_score is not None
    ]
    print(_metric_line("Date Match", date_scores))

    charts_scores = [
        r.charts_answer_score for r in results if r.charts_answer_score is not None
    ]
    print(_metric_line("Charts Answer", charts_scores))

    clarification_scores = [
        r.clarification_requested_score
        for r in results
        if r.clarification_requested_score is not None
    ]
    print(_metric_line("Clarification Requested", clarification_scores))

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

        # Print summary
        print(f"\n{'=' * 70}")
        print("RESULTS SUMMARY")
        print(f"{'=' * 70}")
        print(f"Total tests: {len(all_results)}")

        if len(eval_sets_to_run) > 1:
            # Longest field name is "dataset_id_match_score" = 22 chars, +1 for colon
            METRIC_COL_WIDTH = 23
            print("\nBreakdown by eval set:")
            for es in eval_sets_to_run:
                es_results = [r for r in all_results if r.eval_set == es]
                if not es_results:
                    continue
                metric_field = EVAL_SET_PRIMARY_METRIC.get(es, "agent_answer_score")
                metric_label = f"{metric_field}:"
                scores = [
                    v
                    for r in es_results
                    if (v := getattr(r, metric_field, None)) is not None
                ]
                evaluated = len(scores)
                passed = sum(1 for s in scores if s == 1.0)
                if evaluated > 0:
                    metric_str = f"{metric_label:<{METRIC_COL_WIDTH}} {passed:>3} / {evaluated:>3} ({passed / evaluated:.2f})"
                else:
                    metric_str = f"{metric_label:<{METRIC_COL_WIDTH}} {0:>3} / {0:>3}"
                print(f"  {es:30} | Tests: {len(es_results):3} | {metric_str}")
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

    config = Config()
    try:
        results = asyncio.run(run_csv_tests(config))
        return results
    except ValueError as e:
        print(f"❌ ERROR: {e}")
        return []  # Return empty list on error


if __name__ == "__main__":
    run_evals()
