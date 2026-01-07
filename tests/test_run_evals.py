"""Unit tests for run_evals functionality."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gnw_evals.core import run_csv_tests
from gnw_evals.utils.config import TestConfig
from gnw_evals.utils.eval_types import ExpectedData


class MockStreamContextManager:
    """Async context manager for mocking httpx stream responses."""

    def __init__(self, response_lines=None, raise_error=None):
        """Initialize with response lines or error to raise."""
        self.response_lines = response_lines or []
        self.raise_error = raise_error

    async def __aenter__(self):
        """Enter context manager."""
        if self.raise_error:
            raise self.raise_error
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            """Mock async iterator for stream lines."""
            for line in self.response_lines:
                yield line

        mock_response.aiter_lines = mock_aiter_lines
        return mock_response

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        return None


@pytest.fixture
def mock_test_cases():
    """Create mock test cases based on examples from gnw-eval-sets-gold.csv."""
    return [
        ExpectedData(
            query="True or false: Mount Hakusan had more area with high confidence disturbance alerts in August 2023 than August 2024",
            expected_aoi_ids=["15060"],
            expected_subregion="",
            expected_aoi_source="kba",
            expected_dataset_id="0",
            expected_dataset_name="Global All Ecosystem Disturbance Alerts (DIST-ALERT)",
            expected_context_layer="",
            expected_start_date="8/1/2023",
            expected_end_date="8/31/2024",
            expected_answer="TRUE",
            test_group="",
            status="",
        ),
        ExpectedData(
            query="How much of Virunga National Park was impacted by high confidence disturbance alerts in the second half of 2023?",
            expected_aoi_ids=[],
            expected_subregion="",
            expected_aoi_source="wdpa",
            expected_dataset_id="0",
            expected_dataset_name="Global All Ecosystem Disturbance Alerts (DIST-ALERT)",
            expected_context_layer="",
            expected_start_date="7/1/2024",
            expected_end_date="12/31/2024",
            expected_answer="198.4 hectares",
            test_group="",
            status="",
        ),
        ExpectedData(
            query="Which country had the most distrubed area in November 2023, Australia or Brazil?",
            expected_aoi_ids=["BRA", "AUS"],
            expected_subregion="country",
            expected_aoi_source="gadm",
            expected_dataset_id="0",
            expected_dataset_name="Global All Ecosystem Disturbance Alerts (DIST-ALERT)",
            expected_context_layer="",
            expected_start_date="1/1/2023",
            expected_end_date="12/31/2023",
            expected_answer="Brazil",
            test_group="",
            status="",
        ),
    ]


@pytest.fixture
def mock_agent_state():
    """Create a mock agent state that would be returned from the API."""
    return {
        "aoi": {
            "src_id": "15060",
            "name": "Mount Hakusan",
            "subtype": "kba",
            "source": "kba",
        },
        "dataset": {
            "dataset_id": "0",
            "dataset_name": "Global All Ecosystem Disturbance Alerts (DIST-ALERT)",
            "context_layer": "",
        },
        "raw_data": [
            {"date": "2023-08-01", "value": 100},
            {"date": "2023-08-15", "value": 150},
            {"date": "2024-08-01", "value": 80},
        ],
        "start_date": "8/1/2023",
        "end_date": "8/31/2024",
        "charts_data": [
            {
                "insight": "Mount Hakusan had more area with high confidence disturbance alerts in August 2023 (150 hectares) than in August 2024 (80 hectares). The answer is TRUE.",
            },
        ],
        "messages": [],
    }


@pytest.fixture
def mock_config():
    """Create a mock test configuration."""
    return TestConfig(
        api_base_url="http://localhost:8000",
        api_token="test_token",
        sample_size=3,
        test_file="data/gnw-eval-sets-gold.csv",
        test_group_filter=None,
        status_filter=None,
        output_filename="test_results.csv",
        num_workers=1,
        random_seed=0,
        offset=0,
    )


@pytest.mark.asyncio
async def test_run_csv_tests_with_mocked_data(
    mock_test_cases,
    mock_agent_state,
    mock_config,
):
    """Test run_csv_tests with mocked CSV loader and API calls."""
    # Mock the CSVLoader
    with patch("gnw_evals.core.CSVLoader") as mock_loader_class:
        mock_loader = MagicMock()
        mock_loader.load_test_data.return_value = mock_test_cases
        mock_loader_class.return_value = mock_loader

        # Mock httpx.AsyncClient for API calls
        stream_lines = [
            json.dumps(
                {
                    "node": "trace_info",
                    "update": json.dumps(
                        {
                            "trace_id": "test_trace_123",
                            "trace_url": "http://test.url/trace",
                        },
                    ),
                },
            ),
            json.dumps({"node": "message", "content": "Processing..."}),
        ]

        mock_state_response = MagicMock()
        mock_state_response.raise_for_status = MagicMock()
        mock_state_response.json.return_value = {
            "state": json.dumps(mock_agent_state),
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(
            return_value=MockStreamContextManager(response_lines=stream_lines),
        )
        mock_client.get = AsyncMock(return_value=mock_state_response)

        with patch("gnw_evals.runners.api.httpx.AsyncClient", return_value=mock_client):
            with patch("gnw_evals.core.ResultExporter") as mock_exporter_class:
                with patch(
                    "gnw_evals.evaluators.llm_judges.llm_judge",
                    return_value=1.0,
                ):
                    with patch(
                        "gnw_evals.evaluators.llm_judges.llm_judge_clarification",
                        return_value={"is_clarification": False, "explanation": ""},
                    ):
                        mock_exporter = MagicMock()
                        mock_exporter_class.return_value = mock_exporter

                        # Run the tests
                        results = await run_csv_tests(mock_config)

                        # Assertions
                        assert len(results) == 3, "Should return 3 test results"
                        assert all(r.overall_score >= 0 for r in results), (
                            "All scores should be non-negative"
                        )
                        assert all(r.query for r in results), (
                            "All results should have a query"
                        )

                        # Check that CSVLoader was called correctly
                        mock_loader.load_test_data.assert_called_once_with(
                            mock_config.test_file,
                            mock_config.sample_size,
                            mock_config.test_group_filter,
                            mock_config.status_filter,
                            mock_config.random_seed,
                            mock_config.offset,
                        )

                        # Check that results were saved
                        mock_exporter.save_results_to_csv.assert_called_once()
                        call_args = mock_exporter.save_results_to_csv.call_args
                        assert len(call_args[0][0]) == 3, "Should save 3 results"


@pytest.mark.asyncio
async def test_run_csv_tests_with_multiple_workers(
    mock_test_cases,
    mock_agent_state,
    mock_config,
):
    """Test run_csv_tests with multiple workers (parallel execution)."""
    mock_config.num_workers = 2

    with patch("gnw_evals.core.CSVLoader") as mock_loader_class:
        mock_loader = MagicMock()
        mock_loader.load_test_data.return_value = mock_test_cases
        mock_loader_class.return_value = mock_loader

        # Mock httpx.AsyncClient for API calls
        stream_lines = [
            json.dumps(
                {
                    "node": "trace_info",
                    "update": json.dumps(
                        {
                            "trace_id": "test_trace_123",
                            "trace_url": "http://test.url/trace",
                        },
                    ),
                },
            ),
        ]

        mock_state_response = MagicMock()
        mock_state_response.raise_for_status = MagicMock()
        mock_state_response.json.return_value = {
            "state": json.dumps(mock_agent_state),
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(
            return_value=MockStreamContextManager(response_lines=stream_lines),
        )
        mock_client.get = AsyncMock(return_value=mock_state_response)

        with patch("gnw_evals.runners.api.httpx.AsyncClient", return_value=mock_client):
            with patch("gnw_evals.core.ResultExporter") as mock_exporter_class:
                with patch(
                    "gnw_evals.evaluators.llm_judges.llm_judge",
                    return_value=1.0,
                ):
                    with patch(
                        "gnw_evals.evaluators.llm_judges.llm_judge_clarification",
                        return_value={"is_clarification": False, "explanation": ""},
                    ):
                        mock_exporter = MagicMock()
                        mock_exporter_class.return_value = mock_exporter

                        # Run the tests
                        results = await run_csv_tests(mock_config)

                        # Assertions
                        assert len(results) == 3, "Should return 3 test results"
                        assert all(r.overall_score >= 0 for r in results), (
                            "All scores should be non-negative"
                        )


@pytest.mark.asyncio
async def test_run_csv_tests_with_api_error(mock_test_cases, mock_config):
    """Test run_csv_tests handles API errors gracefully."""
    with patch("gnw_evals.core.CSVLoader") as mock_loader_class:
        mock_loader = MagicMock()
        mock_loader.load_test_data.return_value = mock_test_cases[
            :1
        ]  # Only one test case
        mock_loader_class.return_value = mock_loader

        # Mock httpx.AsyncClient to raise an error
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(
            return_value=MockStreamContextManager(
                raise_error=Exception("API connection error"),
            ),
        )

        with patch("gnw_evals.runners.api.httpx.AsyncClient", return_value=mock_client):
            with patch("gnw_evals.core.ResultExporter") as mock_exporter_class:
                with patch(
                    "gnw_evals.evaluators.llm_judges.llm_judge",
                    return_value=1.0,
                ):
                    with patch(
                        "gnw_evals.evaluators.llm_judges.llm_judge_clarification",
                        return_value={"is_clarification": False, "explanation": ""},
                    ):
                        mock_exporter = MagicMock()
                        mock_exporter_class.return_value = mock_exporter

                        # Run the tests - should handle error gracefully
                        results = await run_csv_tests(mock_config)

                        # Should still return a result, but with error
                        assert len(results) == 1, (
                            "Should return 1 test result even on error"
                        )
                        assert results[0].overall_score == 0.0, (
                            "Error should result in 0 score"
                        )
                        assert results[0].error is not None, "Error should be recorded"


@pytest.mark.asyncio
async def test_run_csv_tests_with_empty_data(mock_config):
    """Test run_csv_tests with empty test data."""
    with patch("gnw_evals.core.CSVLoader") as mock_loader_class:
        mock_loader = MagicMock()
        mock_loader.load_test_data.return_value = []  # Empty list
        mock_loader_class.return_value = mock_loader

        with patch("gnw_evals.core.ResultExporter") as mock_exporter_class:
            mock_exporter = MagicMock()
            mock_exporter_class.return_value = mock_exporter

            # Run the tests
            results = await run_csv_tests(mock_config)

            # Assertions
            assert len(results) == 0, "Should return empty results"
            mock_exporter.save_results_to_csv.assert_called_once_with(
                [],
                mock_config.output_filename,
            )
