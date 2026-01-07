import asyncio
import time

from gnw_evals.data_handlers import CSVLoader, ResultExporter
from gnw_evals.runners import APITestRunner
from gnw_evals.utils.config import get_test_config
from gnw_evals.utils.eval_types import ExpectedData, TestResult


async def run_single_test(
    runner,
    test_case,
    test_index,
    total_tests,
) -> TestResult:
    """Run a single test case."""
    start_time = time.time()
    print(
        f"[STARTED] Test {test_index + 1}/{total_tests}: {test_case.query[:60]}...",
    )

    # Convert test case to ExpectedData (remove query field)
    test_dict = test_case.model_dump()
    expected_data = ExpectedData(
        **{k: v for k, v in test_dict.items() if k != "query"},
    )
    result = await runner.run_test(test_case.query, expected_data)

    # Print completion with timing
    duration = time.time() - start_time
    score = result.overall_score
    print(
        f"[COMPLETED] Test {test_index + 1}/{total_tests}: Score {score:.2f} ({duration:.1f}s)",
    )
    print(
        f"  AOI: {result.aoi_score} | Dataset: {result.dataset_score} | Data: {result.pull_data_score} | Answer: {result.answer_score}",
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
    print(
        f"Running {len(test_cases)} tests with {config.num_workers} workers...",
    )

    # Setup test runner
    runner = APITestRunner(
        api_base_url=config.api_base_url,
        api_token=config.api_token,
    )
    print(f"Using API endpoint: {config.api_base_url}")

    # Run tests in parallel
    start_time = time.time()

    if config.num_workers == 1:
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
        semaphore = asyncio.Semaphore(config.num_workers)

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

    # Save results
    exporter = ResultExporter()
    exporter.save_results_to_csv(results, config.output_filename)

    # Print summary
    _print_csv_summary(results)
    return results


def _print_csv_summary(results: list[TestResult]) -> None:
    """Print CSV test summary statistics."""
    total_tests = len(results)
    if total_tests == 0:
        return

    avg_score = sum(r.overall_score for r in results) / total_tests
    passed = sum(1 for r in results if r.overall_score >= 0.7)

    print(f"\n{'=' * 50}")
    print("SIMPLE E2E TEST SUMMARY")
    print(f"{'=' * 50}")
    print(f"Total Tests: {total_tests}")
    print(f"Average Score: {avg_score:.2f}")
    print(f"Passed (≥0.7): {passed}/{total_tests} ({passed / total_tests:.1%})")

    # Tool-specific stats
    aoi_nones = len([r for r in results if r.aoi_score is None])
    if total_tests - aoi_nones > 0:
        aoi_avg = sum(r.aoi_score for r in results if r.aoi_score is not None) / (
            total_tests - aoi_nones
        )
        aoi_avg = f"{aoi_avg:.2f}"
    else:
        aoi_avg = None
    print(f"AOI Selection: {aoi_avg} ({aoi_nones} None)")

    dataset_nones = len([r for r in results if r.dataset_score is None])
    if total_tests - dataset_nones > 0:
        dataset_avg = sum(
            r.dataset_score for r in results if r.dataset_score is not None
        ) / (total_tests - dataset_nones)
        dataset_avg = f"{dataset_avg:.2f}"
    else:
        dataset_avg = None
    print(f"Dataset Selection: {dataset_avg} ({dataset_nones} None)")

    data_nones = len([r for r in results if r.pull_data_score is None])
    if total_tests - data_nones > 0:
        data_avg = sum(
            r.pull_data_score for r in results if r.pull_data_score is not None
        ) / (total_tests - data_nones)
        data_avg = f"{data_avg:.2f}"
    else:
        data_avg = None
    print(f"Data Pull: {data_avg} ({data_nones} None)")

    answer_nones = len([r for r in results if r.answer_score is None])
    if total_tests - answer_nones > 0:
        answer_avg = sum(
            r.answer_score for r in results if r.answer_score is not None
        ) / (total_tests - answer_nones)
        answer_avg = f"{answer_avg:.2f}"
    else:
        answer_avg = None
    print(f"Final Answer: {answer_avg} ({answer_nones} None)")


async def run_evals():
    """Run main E2E test function for CSV based evaluation."""
    config = get_test_config()
    results = await run_csv_tests(config)
    assert len(results) > 0, "No test results from CSV"


if __name__ == "__main__":
    asyncio.run(run_evals())
