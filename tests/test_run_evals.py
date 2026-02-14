"""Unit tests for run_evals functionality.

Usage
$ uv run pytest tests/test_run_evals.py -v

"""

import json
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gnw_evals.core import run_csv_tests
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
            expected_clarification=False,
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
            expected_clarification=False,
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
            expected_clarification=False,
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
                            "subregion_match_score",
                        ), "Should have subregion_match_score field"
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


def test_aoi_evaluator_missing_expected_subregion():
    """Test that missing expected_subregion returns None for subregion_match_score.

    Missing "Expected" values should result in None scores, not positive scores.
    """
    from gnw_evals.evaluators import evaluate_aoi_selection

    agent_state = {
        "aoi": {
            "src_id": "BRA",
            "name": "Brazil",
            "subtype": "country",
            "source": "gadm",
        },
        "subregion": "country",
    }

    result = evaluate_aoi_selection(
        agent_state=agent_state,
        expected_aoi_ids=["BRA"],
        expected_subregion="",  # Empty - should return None
        query="",
    )

    assert result["aoi_id_match_score"] == 1.0, "AOI ID should match"
    assert result["subregion_match_score"] is None, (
        "Subregion score should be None when expected is empty"
    )
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


def test_data_pull_evaluator_missing_expected_dates():
    """Test that missing expected dates returns None for date_match_score.

    Missing "Expected" values should result in None scores, not positive scores.
    """
    from gnw_evals.evaluators import evaluate_data_pull, evaluate_date_selection

    agent_state = {
        "raw_data": [{"value": 100}, {"value": 200}],
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
    assert data_result["data_pull_success"] is True, (
        "Data pull success flag should be True"
    )
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
        "subregion_match_score": None,  # Not evaluated (missing expected)
        "dataset_id_match_score": 1.0,
        "context_layer_match_score": None,  # Not evaluated (missing expected)
        "data_pull_exists_score": 1.0,
        "date_match_score": None,  # Not evaluated (missing expected)
        "charts_answer_score": 0.0,
        "agent_answer_score": 1.0,
    }

    expected_data = ExpectedData(
        expected_aoi_ids=["BRA"],
        expected_subregion="",  # Empty
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

    Validates that both scores are calculated when both expected values are provided.
    """
    from gnw_evals.evaluators import evaluate_aoi_selection

    agent_state = {
        "aoi": {
            "src_id": "BRA",
            "name": "Brazil",
            "subtype": "country",
            "source": "gadm",
        },
        "subregion": "country",
    }

    result = evaluate_aoi_selection(
        agent_state=agent_state,
        expected_aoi_ids=["BRA"],
        expected_subregion="country",  # Provided
        query="",
    )

    assert result["aoi_id_match_score"] == 1.0, "AOI ID should match"
    assert result["subregion_match_score"] == 1.0, "Subregion should match"
    assert result["match_aoi_id"] is True
    assert result["match_subregion"] is True


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
        "raw_data": [{"value": 100}, {"value": 200}],
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
    assert data_result["data_pull_success"] is True
    assert date_result["date_match_score"] == 1.0, "Dates should match"
    assert date_result["date_success"] is True


# ============================================================================
# UNIT TESTS FOR CLARIFICATION SCORING
# ============================================================================


def test_clarification_expected_and_given_scores_1():
    """Test that clarification request scores 1.0 when expected.

    When expected_clarification=True AND agent requests clarification,
    clarification_requested_score should be 1.0, and other scores should be None.
    """
    from unittest.mock import patch

    from gnw_evals.evaluators import evaluate_aoi_selection

    agent_state = {
        "aoi": None,  # No AOI selected
        "messages": [
            type("obj", (object,), {"content": "Could you clarify which region?"})(),
        ],
    }

    with patch(
        "gnw_evals.evaluators.llm_judges.llm_judge_clarification",
    ) as mock_judge:
        mock_judge.return_value = {
            "is_clarification": True,
            "explanation": "Agent is asking for region clarification",
        }

        result = evaluate_aoi_selection(
            agent_state=agent_state,
            expected_aoi_ids=["BRA"],
            expected_subregion="",
            expected_clarification=True,
            query="Show me data",
        )

        assert result["clarification_requested_score"] == 1.0, (
            "Should score 1.0 when clarification is expected and given"
        )
        assert result["aoi_id_match_score"] is None, (
            "AOI score should be None when clarification is given"
        )
        assert result["subregion_match_score"] is None, (
            "Subregion score should be None when clarification is given"
        )


def test_clarification_not_expected_but_given_scores_0():
    """Test that clarification request scores 0.0 when NOT expected.

    When expected_clarification=False AND agent requests clarification,
    clarification_requested_score should be 0.0.
    """
    from unittest.mock import patch

    from gnw_evals.evaluators import evaluate_dataset_selection

    agent_state = {
        "dataset": None,  # No dataset selected
        "messages": [
            type("obj", (object,), {"content": "Which dataset did you mean?"})(),
        ],
    }

    with patch(
        "gnw_evals.evaluators.llm_judges.llm_judge_clarification",
    ) as mock_judge:
        mock_judge.return_value = {
            "is_clarification": True,
            "explanation": "Agent is asking which dataset",
        }

        result = evaluate_dataset_selection(
            agent_state=agent_state,
            expected_dataset_id="0",
            expected_context_layer="",
            expected_clarification=False,
            query="Get forest data",
        )

        assert result["clarification_requested_score"] == 0.0, (
            "Should score 0.0 when clarification is NOT expected but given"
        )
        assert result["dataset_id_match_score"] is None, (
            "Dataset score should be None when clarification is given"
        )


def test_overall_score_with_clarification():
    """Test that overall score calculation includes clarification_requested_score.

    When expected_clarification=True, the overall score should include
    clarification_requested_score in the average and exclude other None scores.
    """
    from gnw_evals.runners.api import APITestRunner
    from gnw_evals.utils.eval_types import ExpectedData

    runner = APITestRunner(api_base_url="http://test", api_token="test")

    # Scenario: Clarification was expected and given (1.0), no other checks applicable
    evaluations = {
        "clarification_requested_score": 1.0,
        "aoi_id_match_score": None,  # Not evaluated (clarification given)
        "subregion_match_score": None,
        "dataset_id_match_score": None,
        "context_layer_match_score": None,
        "data_pull_exists_score": None,
        "date_match_score": None,
        "answer_score": None,  # Not evaluated (no expected_answer)
    }

    expected_data = ExpectedData(
        expected_aoi_ids=["BRA"],
        expected_subregion="",
        expected_dataset_id="",
        expected_context_layer="",
        expected_start_date="",
        expected_end_date="",
        expected_answer="",
        expected_clarification=True,
    )

    score = runner._calculate_overall_score(evaluations, expected_data)

    # Should only average clarification_requested_score: 1.0 / 1 = 1.0
    assert score == 1.0, (
        f"Expected 1.0, got {score}. Clarification score should be the only score"
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
        "subregion_match_score": None,  # Not evaluated (missing expected)
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
        expected_subregion="",  # Empty
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
