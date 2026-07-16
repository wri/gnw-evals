"""Human-readable formatting for --print-results output."""

from gnw_evals.utils.eval_types import TestResult

_OVERALL_SCORE_FIELD = "overall_score"
_MAX_LINE_WIDTH = 120
_MAX_VALUE_WIDTH = 240

# Fields never shown in comparisons (too large or redundant with scores).
_SKIP_COMPARISON_ACTUALS = frozenset({"actual_charts_json"})

# (expected_field, actual_field, optional score_field to gate on failure)
_COMPARISONS: list[tuple[str, str, str | None]] = [
    ("expected_aoi_ids", "actual_id", "aoi_id_match_score"),
    ("expected_aoi_source", "actual_source", None),
    ("expected_dataset_id", "actual_dataset_id", "dataset_id_match_score"),
    ("expected_dataset_name", "actual_dataset_name", None),
    (
        "expected_dataset_parameters",
        "actual_dataset_parameters",
        "dataset_parameter_match_score",
    ),
    ("expected_context_layer", "actual_context_layer", "context_layer_match_score"),
    ("expected_start_date", "actual_start_date", "date_match_score"),
    ("expected_end_date", "actual_end_date", None),
    ("expected_answer", "actual_charts_answer", "charts_answer_score"),
    ("expected_text", "actual_agent_answer", "expected_text_match_score"),
    (
        "expected_clarification",
        "actual_clarification_requested",
        "clarification_requested_score",
    ),
    ("expected_chart_type", "actual_chart_type", "chart_type_match_score"),
    ("expected_canopy_cover", "actual_canopy_cover", "canopy_cover_match_score"),
    ("expected_forest_filter", "actual_forest_filter", "forest_filter_match_score"),
    ("expected_intersections", "actual_intersections", "intersections_match_score"),
]

_REASON_BY_SCORE: dict[str, str] = {
    "charts_answer_score": "chart_answer_score_reason",
    "agent_answer_score": "agent_answer_score_reason",
    "expected_text_match_score": "expected_text_match_score_reason",
    "data_fidelity_score": "data_fidelity_missing",
    "number_usage_score": "number_usage_failure_comment",
}


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def _truncate(text: str, max_width: int) -> str:
    text = " ".join(text.split())
    if len(text) <= max_width:
        return text
    return text[: max_width - 3] + "..."


def _format_value(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return "; ".join(str(item) for item in value) if value else "—"
    text = str(value).strip()
    if not text:
        return "—"
    return _truncate(text, _MAX_VALUE_WIDTH)


def _score_fields(result: TestResult) -> list[tuple[str, float]]:
    return [
        (field, value)
        for field, value in result.model_dump().items()
        if field.endswith("_score") and value is not None
    ]


def _checks_passed(result: TestResult) -> bool:
    if result.error:
        return False
    scores = [
        (field, value)
        for field, value in _score_fields(result)
        if field != _OVERALL_SCORE_FIELD
    ]
    if not scores:
        return True
    return all(value == 1.0 for _, value in scores)


def _should_show_comparison(
    result: TestResult,
    expected_field: str,
    score_field: str | None,
) -> bool:
    expected = getattr(result, expected_field)
    if not _is_empty(expected):
        return True
    if score_field is None:
        return False
    score = getattr(result, score_field)
    return score is not None and score < 1.0


def _comparison_label(field: str) -> str:
    return field.removeprefix("expected_").replace("_", " ")


def _format_scores(result: TestResult) -> list[str]:
    lines: list[str] = []
    for field, value in sorted(_score_fields(result)):
        if field == _OVERALL_SCORE_FIELD:
            continue
        label = field.removesuffix("_score").replace("_", " ")
        marker = "✓" if value == 1.0 else "✗"
        lines.append(f"  {marker} {label}: {value}")
        reason_field = _REASON_BY_SCORE.get(field)
        if reason_field and value < 1.0:
            reason = getattr(result, reason_field, None)
            if reason:
                lines.append(f"      → {_truncate(str(reason), _MAX_LINE_WIDTH)}")
    return lines


def _format_comparisons(result: TestResult) -> list[str]:
    lines: list[str] = []
    for expected_field, actual_field, score_field in _COMPARISONS:
        if actual_field in _SKIP_COMPARISON_ACTUALS:
            continue
        if not _should_show_comparison(result, expected_field, score_field):
            continue
        label = _comparison_label(expected_field)
        expected = _format_value(getattr(result, expected_field))
        actual = _format_value(getattr(result, actual_field))
        lines.append(f"  {label}:")
        lines.append(f"    expected: {expected}")
        lines.append(f"    actual:   {actual}")

    if result.aoi_id_match_score is not None and result.aoi_id_match_score < 1.0:
        for extra_field in ("actual_name", "actual_subtype"):
            value = getattr(result, extra_field, None)
            if not _is_empty(value):
                label = extra_field.removeprefix("actual_").replace("_", " ")
                lines.append(f"    {label}: {_format_value(value)}")

    if (
        result.data_pull_exists_score is not None
        and result.data_pull_exists_score < 1.0
        and result.row_count
    ):
        lines.append(f"  rows pulled: {result.row_count} (min {result.min_rows})")

    return lines


def format_test_result(result: TestResult, *, index: int, total: int) -> str:
    """Format a single test result for terminal output."""
    passed = _checks_passed(result)
    status = "PASS" if passed else "FAIL"
    test_id = result.test_id or f"#{index}"
    duration = (
        f"{result.duration_seconds:.1f}s"
        if result.duration_seconds is not None
        else result.execution_time
    )

    lines = [
        f"[{status}] {test_id} ({index}/{total})"
        f" | overall {result.overall_score} | {duration}",
    ]
    if result.eval_set and result.eval_set != "custom":
        lines[0] += f" | {result.eval_set}"
    if result.test_group and result.test_group != "unknown":
        lines[0] += f" | group {result.test_group}"

    query = (result.query or "").strip()
    if query:
        lines.append(f"  query: {_truncate(query, _MAX_LINE_WIDTH)}")

    if result.trace_url:
        lines.append(f"  trace: {result.trace_url}")

    if result.error:
        lines.append(f"  error: {_truncate(result.error, _MAX_VALUE_WIDTH)}")

    score_lines = _format_scores(result)
    if score_lines:
        lines.append("  checks:")
        lines.extend(score_lines)

    comparison_lines = _format_comparisons(result)
    if comparison_lines:
        lines.append("  details:")
        lines.extend(comparison_lines)

    return "\n".join(lines)


def print_results_to_screen(results: list[TestResult]) -> None:
    """Print per-test results in a human-readable format."""
    total = len(results)
    passed = sum(1 for result in results if _checks_passed(result))
    failed = total - passed

    print(f"\n{'=' * 72}")
    print(f"RESULTS ({total} test{'s' if total != 1 else ''})")
    print(f"{'=' * 72}")

    for index, result in enumerate(results, 1):
        print()
        print(format_test_result(result, index=index, total=total))

    print()
    print(f"{'—' * 72}")
    print(f"Summary: {passed} passed, {failed} failed")
    if total:
        print(
            f"Mean overall score: {sum(r.overall_score for r in results) / total:.3f}",
        )
