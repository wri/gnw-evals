"""Unit tests for run_evals functionality.

Usage
$ uv run pytest tests/test_run_evals.py -v

"""

import json
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gnw_evals.core import _build_default_output_filename, run_csv_tests
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
            expected_aoi_source="kba",
            expected_dataset_id="0",
            expected_dataset_name="Global All Ecosystem Disturbance Alerts (DIST-ALERT)",
            expected_context_layer="",
            expected_start_date="8/1/2023",
            expected_end_date="8/31/2024",
            expected_answer="TRUE",
            expected_clarification=False,
            test_group="",
            status="",
        ),
        ExpectedData(
            query="How much of Virunga National Park was impacted by high confidence disturbance alerts in the second half of 2023?",
            expected_aoi_ids=[],
            expected_aoi_source="wdpa",
            expected_dataset_id="0",
            expected_dataset_name="Global All Ecosystem Disturbance Alerts (DIST-ALERT)",
            expected_context_layer="",
            expected_start_date="7/1/2024",
            expected_end_date="12/31/2024",
            expected_answer="198.4 hectares",
            expected_clarification=False,
            test_group="",
            status="",
        ),
        ExpectedData(
            query="Which country had the most distrubed area in November 2023, Australia or Brazil?",
            expected_aoi_ids=["BRA", "AUS"],
            expected_aoi_source="gadm",
            expected_dataset_id="0",
            expected_dataset_name="Global All Ecosystem Disturbance Alerts (DIST-ALERT)",
            expected_context_layer="",
            expected_start_date="1/1/2023",
            expected_end_date="12/31/2023",
            expected_answer="Brazil",
            expected_clarification=False,
            test_group="",
            status="",
        ),
    ]


@pytest.fixture
def mock_agent_state():
    """Create a mock agent state that would be returned from the API."""
    return {
        "aoi_selection": {
            "name": "Mount Hakusan",
            "aois": [
                {
                    "src_id": "15060",
                    "name": "Mount Hakusan",
                    "subtype": "kba",
                    "source": "kba",
                },
            ],
        },
        "dataset": {
            "dataset_id": "0",
            "dataset_name": "Global All Ecosystem Disturbance Alerts (DIST-ALERT)",
            "context_layer": "",
        },
        "statistics": [
            {
                "data": {
                    "date": ["2023-08-01", "2023-08-15", "2024-08-01"],
                    "value": [100, 150, 80],
                },
                "start_date": "8/1/2023",
                "end_date": "8/31/2024",
            },
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


@dataclass
class TestConfig:
    """Test configuration dataclass."""

    api_base_url: str = "http://localhost:8000"
    api_token: str = "test_token"
    sample_size: int = 3
    test_file: str = "gnw-eval-sets-gold.csv"
    test_group_filter: str | None = None
    status_filter: list[str] | None = None
    output_filename: str = "test_results.csv"
    num_workers: int = 1
    random_seed: int = 0
    offset: int = 0


@pytest.fixture
def mock_config():
    """Create a mock test configuration."""
    return TestConfig()


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

                        # Verify score structure
                        first_result = results[0]
                        assert hasattr(
                            first_result,
                            "aoi_id_match_score",
                        ), "Should have aoi_id_match_score field"
                        assert hasattr(
                            first_result,
                            "dataset_id_match_score",
                        ), "Should have dataset_id_match_score field"
                        assert hasattr(
                            first_result,
                            "context_layer_match_score",
                        ), "Should have context_layer_match_score field"
                        assert hasattr(
                            first_result,
                            "data_pull_exists_score",
                        ), "Should have data_pull_exists_score field"
                        assert hasattr(
                            first_result,
                            "date_match_score",
                        ), "Should have date_match_score field"
                        assert hasattr(
                            first_result,
                            "charts_answer_score",
                        ), "Should have charts_answer_score field"
                        assert hasattr(
                            first_result,
                            "agent_answer_score",
                        ), "Should have agent_answer_score field"
                        assert hasattr(
                            first_result,
                            "clarification_requested_score",
                        ), "Should have clarification_requested_score field"

                        # Check that CSVLoader was called correctly
                        mock_loader.load_test_data.assert_called_once_with(
                            mock_config.test_file,
                            mock_config.sample_size,
                            mock_config.test_group_filter,
                            mock_config.status_filter,
                            mock_config.random_seed,
                            mock_config.offset,
                        )


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
async def test_run_csv_tests_caps_workers_to_five_and_sample_size(mock_config):
    """Worker count should be min(5, requested workers, loaded test count)."""
    mock_config.num_workers = 20
    mock_config.sample_size = 2

    with patch("gnw_evals.core.CSVLoader") as mock_loader_class:
        mock_loader = MagicMock()
        mock_loader.load_test_data.return_value = [MagicMock(), MagicMock()]
        mock_loader_class.return_value = mock_loader

        with patch("gnw_evals.core.APITestRunner"):
            with patch("gnw_evals.core._print_csv_summary"):
                with patch("gnw_evals.core.asyncio.Semaphore") as mock_semaphore:
                    with patch(
                        "gnw_evals.core.run_single_test",
                        new=AsyncMock(return_value=MagicMock()),
                    ):
                        await run_csv_tests(mock_config)

                        mock_semaphore.assert_called_once_with(2)


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


# ============================================================================
# UNIT TESTS FOR MISSING EXPECTED VALUES
# ============================================================================


def test_aoi_evaluator_with_aoi_ids_only():
    """Test AOI evaluator when only AOI IDs are expected."""
    from gnw_evals.evaluators import evaluate_aoi_selection

    agent_state = {
        "aoi_selection": {
            "name": "Brazil",
            "aois": [
                {
                    "src_id": "BRA",
                    "name": "Brazil",
                    "subtype": "country",
                    "source": "gadm",
                },
            ],
        },
    }

    result = evaluate_aoi_selection(
        agent_state=agent_state,
        expected_aoi_ids=["BRA"],
        query="",
    )

    assert result["aoi_id_match_score"] == 1.0, "AOI ID should match"
    assert result["match_aoi_id"] is True, "AOI ID match flag should be True"


def test_dataset_evaluator_missing_expected_context_layer():
    """Test that missing expected_context_layer returns None for context_layer_match_score.

    Missing "Expected" values should result in None scores, not positive scores.
    """
    from gnw_evals.evaluators import evaluate_dataset_selection

    agent_state = {
        "dataset": {
            "dataset_id": "0",
            "dataset_name": "DIST-ALERT",
            "context_layer": "tree_cover",
        },
    }

    result = evaluate_dataset_selection(
        agent_state=agent_state,
        expected_dataset_id="0",
        expected_context_layer="",  # Empty - should return None
        query="",
    )

    assert result["dataset_id_match_score"] == 1.0, "Dataset ID should match"
    assert result["context_layer_match_score"] is None, (
        "Context layer score should be None when expected is empty"
    )


def test_dataset_evaluator_none_expected_context_layer():
    """Test that missing expected_context_layer returns 1.0 for context_layer_match_score.

    No actual_context_layer when is expected_context_layer is "none" should return positive score.
    """
    from gnw_evals.evaluators import evaluate_dataset_selection

    agent_state = {
        "dataset": {
            "dataset_id": "0",
            "dataset_name": "DIST-ALERT",
            "context_layer": "",
        },
    }

    result = evaluate_dataset_selection(
        agent_state=agent_state,
        expected_dataset_id="0",
        expected_context_layer="no_selection",  # should assert no_selection
        query="",
    )

    assert result["dataset_id_match_score"] == 1.0, "Dataset ID should match"
    assert result["context_layer_match_score"] == 1.0, (
        "Context layer score should be 1.0 if no context_layer is selected."
    )


def test_dataset_evaluator_incorrect_expected_context_layer():
    """Test that incorrect context layer returns 0.0 for context_layer_match_score."""
    from gnw_evals.evaluators import evaluate_dataset_selection

    agent_state = {
        "dataset": {
            "dataset_id": "0",
            "dataset_name": "DIST-ALERT",
            "context_layer": "land_cover",
        },
    }

    result = evaluate_dataset_selection(
        agent_state=agent_state,
        expected_dataset_id="0",
        expected_context_layer="driver",  # Empty - should return None
        query="",
    )

    assert result["dataset_id_match_score"] == 1.0, "Dataset ID should match"
    assert result["context_layer_match_score"] == 0.0, (
        "Context layer score should be 0.0 if since context layers don't match."
    )


def test_data_pull_evaluator_missing_expected_dates():
    """Test that missing expected dates returns None for date_match_score.

    Missing "Expected" values should result in None scores, not positive scores.
    """
    from gnw_evals.evaluators import evaluate_data_pull, evaluate_date_selection

    agent_state = {
        "statistics": [
            {
                "data": {"value": [100, 200]},
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            },
        ],
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
    }

    # Data pull evaluation (no longer includes dates)
    data_result = evaluate_data_pull(
        agent_state=agent_state,
        min_rows=1,
        query="",
    )

    # Date evaluation (separate)
    date_result = evaluate_date_selection(
        agent_state=agent_state,
        expected_start_date=None,  # Missing
        expected_end_date=None,  # Missing
    )

    assert data_result["data_pull_exists_score"] == 1.0, "Data pull should succeed"
    assert date_result["date_match_score"] is None, (
        "Date score should be None when expected dates are missing"
    )


def test_overall_score_excludes_none_values():
    """Test that overall score calculation excludes None values from averaging.

    Overall score calculation should exclude None values (missing expected fields).
    """
    from gnw_evals.runners.api import APITestRunner
    from gnw_evals.utils.eval_types import ExpectedData

    runner = APITestRunner(api_base_url="http://test", api_token="test")

    # Evaluations with some None scores (missing expected values)
    evaluations = {
        "aoi_id_match_score": 1.0,
        "dataset_id_match_score": 1.0,
        "context_layer_match_score": None,  # Not evaluated (missing expected)
        "data_pull_exists_score": 1.0,
        "date_match_score": None,  # Not evaluated (missing expected)
        "charts_answer_score": 0.0,
        "agent_answer_score": 1.0,
    }

    expected_data = ExpectedData(
        expected_aoi_ids=["BRA"],
        expected_dataset_id="0",
        expected_context_layer="",  # Empty
        expected_start_date="",  # Empty
        expected_end_date="",  # Empty
        expected_answer="Test",
    )

    score = runner._calculate_overall_score(evaluations, expected_data)

    # Should average only: aoi_id (1.0), dataset_id (1.0), data_pull (1.0),
    #                      charts_answer (0.0), agent_answer (1.0)
    # = (1.0 + 1.0 + 1.0 + 0.0 + 1.0) / 5 = 0.8
    assert score == 0.8, (
        f"Expected 0.8, got {score}. None values should be excluded from average"
    )


def test_aoi_evaluator_all_fields_present():
    """Test AOI evaluator with all expected fields present.

    Validates that AOI ID score is calculated when expected AOI IDs are provided.
    """
    from gnw_evals.evaluators import evaluate_aoi_selection

    agent_state = {
        "aoi_selection": {
            "name": "Brazil",
            "aois": [
                {
                    "src_id": "BRA",
                    "name": "Brazil",
                    "subtype": "country",
                    "source": "gadm",
                },
            ],
        },
    }

    result = evaluate_aoi_selection(
        agent_state=agent_state,
        expected_aoi_ids=["BRA"],
        query="",
    )

    assert result["aoi_id_match_score"] == 1.0, "AOI ID should match"
    assert result["match_aoi_id"] is True


def test_dataset_evaluator_all_fields_present():
    """Test dataset evaluator with all expected fields present.

    Validates that both scores are calculated when both expected values are provided.
    """
    from gnw_evals.evaluators import evaluate_dataset_selection

    agent_state = {
        "dataset": {
            "dataset_id": "0",
            "dataset_name": "DIST-ALERT",
            "context_layer": "tree_cover",
        },
    }

    result = evaluate_dataset_selection(
        agent_state=agent_state,
        expected_dataset_id="0",
        expected_context_layer="tree_cover",  # Provided
        query="",
    )

    assert result["dataset_id_match_score"] == 1.0, "Dataset ID should match"
    assert result["context_layer_match_score"] == 1.0, "Context layer should match"


def test_data_pull_evaluator_all_fields_present():
    """Test data pull evaluator with all expected fields present.

    Validates that both scores are calculated when both expected values are provided.
    """
    from gnw_evals.evaluators import evaluate_data_pull, evaluate_date_selection

    agent_state = {
        "statistics": [
            {
                "data": {"value": [100, 200]},
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            },
        ],
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
    }

    # Data pull evaluation
    data_result = evaluate_data_pull(
        agent_state=agent_state,
        min_rows=1,
        query="",
    )

    # Date evaluation
    date_result = evaluate_date_selection(
        agent_state=agent_state,
        expected_start_date="2023-01-01",  # Provided
        expected_end_date="2023-12-31",  # Provided
    )

    assert data_result["data_pull_exists_score"] == 1.0, "Data pull should succeed"
    assert date_result["date_match_score"] == 1.0, "Dates should match"
    assert date_result["date_success"] is True


# ============================================================================
# UNIT TESTS FOR CLARIFICATION SCORING
# ============================================================================


def test_clarification_evaluator_all_scenarios():
    """Test all clarification scoring scenarios.

    Tests the centralized clarification evaluator with all 6 cases:
    1. expected=True, actual=True → score=1.0
    2. expected=True, actual=False → score=0.0
    3. expected=False, actual=True → score=0.0
    4. expected=False, actual=False → score=1.0
    5. expected=None (from empty ""), actual=True → score=0.0
    6. expected=None (from empty ""), actual=False → score=None
    """
    from unittest.mock import patch

    from gnw_evals.evaluators.clarification_evaluator import evaluate_clarification

    agent_state = {
        "messages": [
            type("obj", (object,), {"content": "Could you clarify?"})(),
        ],
    }

    # Case 1: expected=True, actual=True → 1.0
    with patch(
        "gnw_evals.evaluators.clarification_evaluator.llm_judge_clarification",
    ) as mock:
        mock.return_value = {"is_clarification": True, "explanation": "asking for info"}
        result = evaluate_clarification(
            agent_state,
            expected_clarification=True,
            query="test",
        )
        assert result["actual_clarification_requested"] is True, (
            "Case 1: Should detect clarification was requested"
        )
        assert result["clarification_requested_score"] == 1.0, (
            "Case 1: expected=True, actual=True should score 1.0"
        )

    # Case 2: expected=True, actual=False → 0.0
    with patch(
        "gnw_evals.evaluators.clarification_evaluator.llm_judge_clarification",
    ) as mock:
        mock.return_value = {"is_clarification": False, "explanation": "answered"}
        result = evaluate_clarification(
            agent_state,
            expected_clarification=True,
            query="test",
        )
        assert result["actual_clarification_requested"] is False, (
            "Case 2: Should detect clarification was NOT requested"
        )
        assert result["clarification_requested_score"] == 0.0, (
            "Case 2: expected=True, actual=False should score 0.0"
        )

    # Case 3: expected=False, actual=True → 0.0
    with patch(
        "gnw_evals.evaluators.clarification_evaluator.llm_judge_clarification",
    ) as mock:
        mock.return_value = {"is_clarification": True, "explanation": "asking for info"}
        result = evaluate_clarification(
            agent_state,
            expected_clarification=False,
            query="test",
        )
        assert result["actual_clarification_requested"] is True, (
            "Case 3: Should detect clarification was requested"
        )
        assert result["clarification_requested_score"] == 0.0, (
            "Case 3: expected=False, actual=True should score 0.0"
        )

    # Case 4: expected=False, actual=False → 1.0
    with patch(
        "gnw_evals.evaluators.clarification_evaluator.llm_judge_clarification",
    ) as mock:
        mock.return_value = {"is_clarification": False, "explanation": "answered"}
        result = evaluate_clarification(
            agent_state,
            expected_clarification=False,
            query="test",
        )
        assert result["actual_clarification_requested"] is False, (
            "Case 4: Should detect clarification was NOT requested"
        )
        assert result["clarification_requested_score"] == 1.0, (
            "Case 4: expected=False, actual=False should score 1.0"
        )

    # Case 5: expected=None (empty string), actual=True → 0.0
    with patch(
        "gnw_evals.evaluators.clarification_evaluator.llm_judge_clarification",
    ) as mock:
        mock.return_value = {"is_clarification": True, "explanation": "asking for info"}
        result = evaluate_clarification(
            agent_state,
            expected_clarification=None,
            query="test",
        )
        assert result["actual_clarification_requested"] is True, (
            "Case 5: Should detect clarification was requested"
        )
        assert result["clarification_requested_score"] == 0.0, (
            "Case 5: expected=None, actual=True should score 0.0 (unsolicited clarification)"
        )

    # Case 6: expected=None (empty string), actual=False → None
    with patch(
        "gnw_evals.evaluators.clarification_evaluator.llm_judge_clarification",
    ) as mock:
        mock.return_value = {"is_clarification": False, "explanation": "answered"}
        result = evaluate_clarification(
            agent_state,
            expected_clarification=None,
            query="test",
        )
        assert result["actual_clarification_requested"] is False, (
            "Case 6: Should detect clarification was NOT requested"
        )
        assert result["clarification_requested_score"] is None, (
            "Case 6: expected=None, actual=False should score None (not evaluated)"
        )


def test_clarification_evaluator_no_query():
    """Test clarification evaluator handles missing query gracefully."""
    from gnw_evals.evaluators.clarification_evaluator import evaluate_clarification

    agent_state = {"messages": []}

    # No query provided - expected=False
    result = evaluate_clarification(agent_state, expected_clarification=False, query="")
    assert result["actual_clarification_requested"] is False, (
        "No query should result in no clarification requested"
    )
    assert result["clarification_requested_score"] == 1.0, (
        "expected=False, actual=False should score 1.0"
    )

    # No query provided - expected=True
    result = evaluate_clarification(agent_state, expected_clarification=True, query="")
    assert result["actual_clarification_requested"] is False
    assert result["clarification_requested_score"] == 0.0, (
        "expected=True, actual=False should score 0.0"
    )

    # No query provided - expected=None
    result = evaluate_clarification(agent_state, expected_clarification=None, query="")
    assert result["actual_clarification_requested"] is False
    assert result["clarification_requested_score"] is None, (
        "expected=None, actual=False should score None"
    )


def test_clarification_and_other_evaluations_run_together():
    """Integration test: clarification detection doesn't block other evaluations.

    When agent requests clarification AND selects an AOI, both should be evaluated.
    All evaluations should run independently.
    """
    from unittest.mock import patch

    from gnw_evals.runners.api import APITestRunner
    from gnw_evals.utils.eval_types import ExpectedData

    runner = APITestRunner(api_base_url="http://test", api_token="test")

    # Agent state with both clarification AND AOI selection
    agent_state = {
        "aoi_selection": {
            "aois": [
                {
                    "src_id": "BRA",
                    "name": "Brazil",
                    "subtype": "country",
                    "source": "gadm",
                },
            ],
        },
        "messages": [
            type(
                "obj",
                (object,),
                {"content": "I found Brazil. By the way, which specific region?"},
            )(),
        ],
    }

    expected_data = ExpectedData(
        expected_aoi_ids=["BRA"],
        expected_clarification=True,
    )

    with patch(
        "gnw_evals.evaluators.clarification_evaluator.llm_judge_clarification",
    ) as mock_clarif:
        mock_clarif.return_value = {
            "is_clarification": True,
            "explanation": "asking for region",
        }

        evaluations = runner._run_evaluations(
            agent_state,
            expected_data,
            query="Show me Brazil",
        )

        # Verify clarification was detected and scored
        assert evaluations["actual_clarification_requested"] is True, (
            "Should detect that clarification was requested"
        )
        assert evaluations["clarification_requested_score"] == 1.0, (
            "Clarification score should be 1.0 (expected and given)"
        )

        # Verify AOI evaluation still ran (not blocked by clarification)
        assert evaluations["aoi_id_match_score"] == 1.0, (
            "AOI evaluation should run and match even when clarification requested"
        )
        assert evaluations["actual_id"] == "['BRA']", (
            "AOI ID should be extracted even when clarification requested"
        )


# ============================================================================
# UNIT TESTS FOR ANSWER SCORE SPLIT
# ============================================================================


def test_answer_evaluator_both_answers_present():
    """Test that both charts and agent answers are evaluated when both exist.

    Verifies that we get two separate scores when both data sources exist.
    Charts answer is correct (1.0), agent answer is wrong (0.0).
    """
    from unittest.mock import patch

    from gnw_evals.evaluators import evaluate_final_answer

    agent_state = {
        "charts_data": [{"insight": "The answer is Brazil with 500 hectares."}],
        "messages": [
            type(
                "obj",
                (object,),
                {"content": "Based on the data, Australia has more."},
            )(),
        ],
    }

    with patch("gnw_evals.evaluators.answer_evaluator.llm_judge") as mock_judge:
        # First call for charts answer (correct), second call for agent answer (wrong)
        mock_judge.side_effect = [1.0, 0.0]

        result = evaluate_final_answer(
            agent_state=agent_state,
            expected_answer="Brazil",
        )

        assert result["charts_answer_score"] == 1.0, (
            "Charts answer should score 1.0 (correct)"
        )
        assert result["agent_answer_score"] == 0.0, (
            "Agent answer should score 0.0 (wrong)"
        )
        assert (
            result["actual_charts_answer"] == "The answer is Brazil with 500 hectares."
        ), "Should capture charts insight"
        assert (
            result["actual_agent_answer"] == "Based on the data, Australia has more."
        ), "Should capture agent message"
        # Verify LLM judge was called twice
        assert mock_judge.call_count == 2, (
            "Should call LLM judge twice (charts + agent)"
        )


def test_answer_evaluator_no_charts_data():
    """Test that charts_answer_score is None when no charts_data exists.

    when pipeline fails before charts generation, charts_answer_score should be
    None (not applicable), not 0.
    """
    from unittest.mock import patch

    from gnw_evals.evaluators import evaluate_final_answer

    agent_state = {
        "charts_data": [],  # No charts - pipeline failed earlier
        "messages": [
            type("obj", (object,), {"content": "I need more information to answer."})(),
        ],
    }

    with patch("gnw_evals.evaluators.answer_evaluator.llm_judge") as mock_judge:
        # Only agent answer is evaluated (returns 0 - wrong answer)
        mock_judge.return_value = 0.0

        result = evaluate_final_answer(
            agent_state=agent_state,
            expected_answer="Brazil",
        )

        assert result["charts_answer_score"] is None, (
            "Charts score should be None when no charts_data exists (not applicable)"
        )
        assert result["agent_answer_score"] == 0.0, (
            "Agent answer should still be evaluated and score 0.0"
        )
        assert result["actual_charts_answer"] is None, (
            "No charts answer should be recorded"
        )
        assert result["actual_agent_answer"] == "I need more information to answer.", (
            "Should capture agent message"
        )
        # Verify LLM judge was called only once (for agent answer)
        assert mock_judge.call_count == 1, (
            "Should call LLM judge only once (agent answer only)"
        )


def test_answer_evaluator_response_quality_scores():
    """Test that expected_quality_criteria triggers five-dimension quality scoring."""
    from unittest.mock import patch

    from gnw_evals.evaluators import evaluate_final_answer

    agent_state = {
        "charts_data": [],
        "messages": [
            type(
                "obj",
                (object,),
                {
                    "content": (
                        "Brazil had the highest disturbance. The result should "
                        "be interpreted cautiously because alert counts can be "
                        "affected by data availability."
                    ),
                },
            )(),
        ],
    }

    with patch(
        "gnw_evals.evaluators.answer_evaluator.llm_judge_response_quality",
    ) as mock_judge:
        mock_judge.return_value = {
            "relevance_score": 5,
            "relevance_reason": "Directly answers the requested country comparison.",
            "coherence_score": 4,
            "coherence_reason": "Clear overall, with minor room for structure.",
            "factual_accuracy_score": 3,
            "factual_accuracy_reason": "Includes cautious claims but lacks citations.",
            "helpfulness_score": 5,
            "helpfulness_reason": "Gives a useful answer and caveat.",
            "safety_score": 4,
            "safety_reason": "Avoids harmful guidance and mostly handles uncertainty.",
        }

        result = evaluate_final_answer(
            agent_state=agent_state,
            expected_answer="",
            expected_quality_criteria=(
                "The response should answer directly and include uncertainty."
            ),
            query="Which country had the highest disturbance?",
        )

        assert result["charts_answer_score"] is None
        assert result["agent_answer_score"] is None
        assert result["response_relevance_score"] == 5
        assert (
            result["response_relevance_reason"]
            == "Directly answers the requested country comparison."
        )
        assert result["response_coherence_score"] == 4
        assert (
            result["response_coherence_reason"]
            == "Clear overall, with minor room for structure."
        )
        assert result["response_factual_accuracy_score"] == 3
        assert (
            result["response_factual_accuracy_reason"]
            == "Includes cautious claims but lacks citations."
        )
        assert result["response_helpfulness_score"] == 5
        assert result["response_helpfulness_reason"] == "Gives a useful answer and caveat."
        assert result["response_safety_score"] == 4
        assert (
            result["response_safety_reason"]
            == "Avoids harmful guidance and mostly handles uncertainty."
        )
        mock_judge.assert_called_once_with(
            query="Which country had the highest disturbance?",
            expected_quality_criteria=(
                "The response should answer directly and include uncertainty."
            ),
            actual_answer=agent_state["messages"][0].content,
        )


def test_overall_score_with_both_answer_scores():
    """Test that overall score calculation includes both answer scores.

    When expected_answer exists, overall score should include both
    charts_answer_score and agent_answer_score in the average.
    """
    from gnw_evals.runners.api import APITestRunner
    from gnw_evals.utils.eval_types import ExpectedData

    runner = APITestRunner(api_base_url="http://test", api_token="test")

    # Scenario: Charts answer correct (1.0), agent answer wrong (0.0)
    evaluations = {
        "aoi_id_match_score": 1.0,
        "dataset_id_match_score": 1.0,
        "context_layer_match_score": None,  # Not evaluated (missing expected)
        "data_pull_exists_score": 1.0,
        "date_match_score": None,  # Not evaluated (missing expected)
        "charts_answer_score": 1.0,  # Charts answer correct
        "agent_answer_score": 0.0,  # Agent answer wrong
        "clarification_requested_score": None,
    }

    expected_data = ExpectedData(
        expected_aoi_ids=["BRA"],
        expected_dataset_id="0",
        expected_context_layer="",  # Empty
        expected_start_date="",  # Empty
        expected_end_date="",  # Empty
        expected_answer="Brazil",  # Present - both answer scores should be included
    )

    score = runner._calculate_overall_score(evaluations, expected_data)

    # Should average: aoi_id (1.0), dataset_id (1.0), data_pull (1.0),
    #                 charts_answer (1.0), agent_answer (0.0)
    # = (1.0 + 1.0 + 1.0 + 1.0 + 0.0) / 5 = 0.8
    assert score == 0.8, (
        f"Expected 0.8, got {score}. Both answer scores should be included in average"
    )


def test_overall_score_with_response_quality_scores():
    """Test that 1-5 response quality scores are normalized in overall score."""
    from gnw_evals.runners.api import APITestRunner
    from gnw_evals.utils.eval_types import ExpectedData

    runner = APITestRunner(api_base_url="http://test", api_token="test")

    evaluations = {
        "aoi_id_match_score": 1.0,
        "dataset_id_match_score": None,
        "context_layer_match_score": None,
        "data_pull_exists_score": None,
        "date_match_score": None,
        "charts_answer_score": None,
        "agent_answer_score": None,
        "response_relevance_score": 1,
        "response_coherence_score": 4,
        "response_factual_accuracy_score": 3,
        "response_helpfulness_score": 5,
        "response_safety_score": 4,
        "clarification_requested_score": None,
    }

    expected_data = ExpectedData(
        expected_aoi_ids=["BRA"],
        expected_quality_criteria="Score final answer quality.",
    )

    score = runner._calculate_overall_score(evaluations, expected_data)

    # Average normalized scores: 1.0, 0.2, 0.8, 0.6, 1.0, 0.8 = 0.73
    assert score == 0.73, (
        f"Expected 0.73, got {score}. Quality scores should be normalized"
    )


# ============================================================================
# UNIT TESTS FOR DATE NORMALIZATION
# ============================================================================


def test_normalize_date_format_mismatch():
    """Test that M/D/YYYY format matches YYYY-MM-DD format after normalization.

    dates in different formats should normalize to the same string for comparison.
    """
    from gnw_evals.evaluators.utils import normalize_date

    # CSV format (M/D/YYYY) should normalize to ISO format
    assert normalize_date("1/1/2023") == "2023-01-01"
    assert normalize_date("12/31/2023") == "2023-12-31"
    assert normalize_date("8/1/2024") == "2024-08-01"

    # ISO format should pass through unchanged
    assert normalize_date("2023-01-01") == "2023-01-01"
    assert normalize_date("2023-12-31") == "2023-12-31"
    assert normalize_date("2024-08-01") == "2024-08-01"

    # Year-only should convert to Jan 1
    assert normalize_date("2023") == "2023-01-01"
    assert normalize_date("2024") == "2024-01-01"

    # Critical: Same date in different formats should produce same output
    assert normalize_date("1/1/2023") == normalize_date("2023-01-01")
    assert normalize_date("8/15/2024") == normalize_date("2024-08-15")


def test_normalize_date_invalid_returns_empty():
    """Test that invalid dates return empty string (treated as None/missing).

    Invalid expected dates should result in None score (not 0),
    """
    from gnw_evals.evaluators.utils import normalize_date

    # None, empty, and "None" string
    assert normalize_date(None) == ""
    assert normalize_date("") == ""
    assert normalize_date("None") == ""
    assert normalize_date("   ") == ""

    # Invalid date formats
    assert normalize_date("invalid-date") == ""
    assert normalize_date("13/32/2023") == ""  # Invalid month/day
    assert normalize_date("not a date") == ""
    assert normalize_date("2023-13-45") == ""  # Invalid ISO date


def test_normalize_start_date_yyyy_format():
    """Test that normalize_start_date converts YYYY to beginning of year."""
    from gnw_evals.evaluators.utils import normalize_start_date

    # YYYY format -> Jan 1
    assert normalize_start_date("2000") == "2000-01-01"
    assert normalize_start_date("2015") == "2015-01-01"

    # Other formats pass through standard normalization
    assert normalize_start_date("1/1/2023") == "2023-01-01"
    assert normalize_start_date("2023-01-01") == "2023-01-01"


def test_normalize_end_date_yyyy_format():
    """Test that normalize_end_date converts YYYY to end of year."""
    from gnw_evals.evaluators.utils import normalize_end_date

    # YYYY format -> Dec 31
    assert normalize_end_date("2000") == "2000-12-31"
    assert normalize_end_date("2016") == "2016-12-31"

    # Other formats pass through standard normalization
    assert normalize_end_date("12/31/2023") == "2023-12-31"
    assert normalize_end_date("2023-12-31") == "2023-12-31"


def test_evaluate_data_pull_with_date_format_mismatch():
    """Test that evaluate_date_selection handles date format mismatches correctly.

    Integration test - dates should match despite format differences,
    and genuinely different dates should still fail.
    """
    from gnw_evals.evaluators import evaluate_date_selection

    # Test 1: Format mismatch but same dates -> should PASS
    agent_state_matching = {
        "raw_data": [{"value": 100}],
        "start_date": "2023-01-01",  # ISO format (agent)
        "end_date": "2023-12-31",
    }

    result_matching = evaluate_date_selection(
        agent_state=agent_state_matching,
        expected_start_date="1/1/2023",  # Slash format (CSV)
        expected_end_date="12/31/2023",
    )

    assert result_matching["date_match_score"] == 1.0, (
        "Dates should match despite format difference"
    )
    assert result_matching["date_success"] is True

    # Test 2: Different dates -> should FAIL
    agent_state_different = {
        "raw_data": [{"value": 100}],
        "start_date": "2023-11-01",  # November (agent)
        "end_date": "2023-11-30",
    }

    result_different = evaluate_date_selection(
        agent_state=agent_state_different,
        expected_start_date="1/1/2023",  # January (CSV)
        expected_end_date="12/31/2023",  # December
    )

    assert result_different["date_match_score"] == 0.0, (
        "Different dates should not match even after normalization"
    )
    assert result_different["date_success"] is False

    # Test 3: Invalid expected dates -> should return None
    agent_state_valid = {
        "raw_data": [{"value": 100}],
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
    }

    result_invalid = evaluate_date_selection(
        agent_state=agent_state_valid,
        expected_start_date="invalid-date",  # Invalid
        expected_end_date="also-invalid",
    )

    assert result_invalid["date_match_score"] is None, (
        "Invalid expected dates should result in None score (not evaluated)"
    )
    assert result_invalid["date_success"] is None


# ============================================================================
# UNIT TESTS FOR EXPECTED_CLARIFICATION STRING PARSING
# ============================================================================


def test_expected_data_clarification_string_parsing():
    """Test that ExpectedData correctly parses string values for expected_clarification.

    CSV files provide string values that need to be converted to booleans or None.
    Empty strings from CSV should become None (no expectation).
    """
    from gnw_evals.utils.eval_types import ExpectedData

    # Test empty string (most common case from CSV) -> None
    data_empty = ExpectedData(expected_clarification="")
    assert data_empty.expected_clarification is None, (
        "Empty string should be parsed as None (no expectation)"
    )

    # Test string "true" values
    for true_val in ["true", "True", "TRUE", "1", "yes", "Yes"]:
        data = ExpectedData(expected_clarification=true_val)
        assert data.expected_clarification is True, (
            f"'{true_val}' should be parsed as True"
        )

    # Test string "false" values
    for false_val in ["false", "False", "FALSE", "0", "no", "No"]:
        data = ExpectedData(expected_clarification=false_val)
        assert data.expected_clarification is False, (
            f"'{false_val}' should be parsed as False"
        )

    # Test actual boolean values pass through
    data_true = ExpectedData(expected_clarification=True)
    assert data_true.expected_clarification is True

    data_false = ExpectedData(expected_clarification=False)
    assert data_false.expected_clarification is False

    # Test None passes through
    data_none = ExpectedData(expected_clarification=None)
    assert data_none.expected_clarification is None


# ============================================================================
# UNIT TESTS FOR STATUS FILTER
# ============================================================================


def test_status_filter_skips_matching_rows(tmp_path):
    """Test that rows with a matching status value are skipped.

    Rows with status "skip" or "not doing" should be excluded;
    rows with empty status or other values should be kept.
    Case-insensitive: "SKIP", "Skip", "skip" all match.
    """
    import pandas as pd

    from gnw_evals.data_handlers.csv_loader import CSVLoader

    csv_file = tmp_path / "test.csv"
    pd.DataFrame(
        {
            "query": ["q1", "q2", "q3", "q4", "q5", "q6"],
            "status": ["skip", "SKIP", "not doing", "rerun", "", "Not Doing"],
        },
    ).to_csv(csv_file, index=False)

    results = CSVLoader.load_test_data(
        str(csv_file),
        status_filter=["skip", "not doing"],
    )

    queries = [r.query for r in results]
    assert "q1" not in queries, "status='skip' should be skipped"
    assert "q2" not in queries, "status='SKIP' should be skipped (case-insensitive)"
    assert "q3" not in queries, "status='not doing' should be skipped"
    assert "q6" not in queries, (
        "status='Not Doing' should be skipped (case-insensitive)"
    )
    assert "q4" in queries, "status='rerun' should be kept"
    assert "q5" in queries, "empty status should be kept"


def test_status_filter_none_keeps_all_rows(tmp_path):
    """Test that no rows are filtered when status_filter is None.

    All rows should be included regardless of their status value
    when status_filter is not set.
    """
    import pandas as pd

    from gnw_evals.data_handlers.csv_loader import CSVLoader

    csv_file = tmp_path / "test.csv"
    pd.DataFrame(
        {
            "query": ["q1", "q2", "q3", "q4"],
            "status": ["skip", "not doing", "rerun", ""],
        },
    ).to_csv(csv_file, index=False)

    results = CSVLoader.load_test_data(str(csv_file), status_filter=None)

    assert len(results) == 4, "All rows should be kept when status_filter is None"


def test_default_output_filename_builder_for_single_eval_set():
    """Default filename should include eval_set and key run parameters."""
    filename = _build_default_output_filename(
        eval_set="gold",
        sample_size=-1,
        num_workers=2,
        offset=0,
    )
    assert filename == "eval_results_gold_sample_-1_workers_2_offset_0"


def test_default_output_filename_builder_for_all_eval_sets():
    """Default filename should preserve eval_set='all' label."""
    filename = _build_default_output_filename(
        eval_set="all",
        sample_size=5,
        num_workers=4,
        offset=10,
    )
    assert filename == "eval_results_all_sample_5_workers_4_offset_10"
