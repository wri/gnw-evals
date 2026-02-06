"""Type definitions for E2E testing framework."""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class TestResult(BaseModel):
    """Result of a single E2E test execution."""

    model_config = ConfigDict(extra="allow")

    thread_id: str
    trace_id: str | None = None
    trace_url: str | None = None
    query: str
    overall_score: float
    execution_time: str

    # AOI evaluation fields - separate binary scores (0/1/None)
    aoi_id_match_score: float | None = None
    subregion_match_score: float | None = None
    actual_id: str | None = None
    actual_name: str | None = None
    actual_subtype: str | None = None
    actual_source: str | None = None
    actual_subregion: str | None = None
    match_aoi_id: bool = False
    match_subregion: bool | None = None

    # Dataset evaluation fields - separate binary scores (0/1/None)
    dataset_id_match_score: float | None = None
    context_layer_match_score: float | None = None
    actual_dataset_id: str | None = None
    actual_dataset_name: str | None = None
    actual_context_layer: str | None = None

    # Data pull evaluation fields - separate binary scores (0/1/None)
    data_pull_exists_score: float | None = None
    date_match_score: float | None = None
    row_count: int = 0
    min_rows: int = 1
    data_pull_success: bool = False
    date_success: bool | None = None
    actual_start_date: str | None = None
    actual_end_date: str | None = None

    # Answer evaluation fields
    answer_score: float | None = None
    actual_answer: str | None = None

    # Expected data fields
    expected_aoi_ids: list[str] = []
    expected_subregion: str = ""
    expected_aoi_source: str = ""
    expected_dataset_id: str = ""
    expected_dataset_name: str = ""
    expected_context_layer: str = ""
    expected_start_date: str = ""
    expected_end_date: str = ""
    expected_answer: str = ""
    test_group: str = "unknown"
    status: str = "ready"

    # Error handling
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for CSV export."""
        return self.model_dump(exclude_none=False)


class ExpectedData(BaseModel):
    """Expected test data for evaluation."""

    model_config = ConfigDict(extra="allow")

    expected_aoi_ids: list[str] = []
    expected_subregion: str = ""
    expected_aoi_source: str = ""
    expected_dataset_id: str = ""
    expected_dataset_name: str = ""
    expected_context_layer: str = ""
    expected_start_date: str = ""
    expected_end_date: str = ""
    expected_answer: str = ""
    test_group: str = "unknown"
    status: str = "ready"
    thread_id: str | None = None

    @field_validator("expected_aoi_ids", mode="before")
    @classmethod
    def split_aoi_ids(cls, v: str | list[str]) -> list[str]:
        """Split string input into a list of strings."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Split by comma and strip whitespace, filter out empty strings
            return [item.strip() for item in v.split(";") if item.strip()]
        return []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(exclude_none=False)
