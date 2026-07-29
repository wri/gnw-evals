"""Unit tests for eval run metadata helpers."""

from datetime import UTC, datetime

import pytest

from gnw_evals.utils.run_metadata import (
    build_run_summary_context,
    compute_latency_stats,
    format_run_timestamp,
    get_eval_judge_llm_label,
    infer_environment,
    print_run_summary_header,
    resolve_gnw_versions,
)


@pytest.mark.parametrize(
    ("api_base_url", "expected"),
    [
        ("https://api.staging.globalnaturewatch.org", "staging"),
        ("https://api.globalnaturewatch.org", "prod"),
        ("http://localhost:8000", "localhost"),
        ("http://127.0.0.1:8000", "localhost"),
        ("https://custom.example.com", "custom"),
    ],
)
def test_infer_environment(api_base_url: str, expected: str) -> None:
    assert infer_environment(api_base_url) == expected


def test_resolve_gnw_versions_prefers_env_over_metadata(monkeypatch) -> None:
    monkeypatch.setenv("GNW_CODE_VERSION", "code-1.2.3")
    monkeypatch.setenv("GNW_PROMPTS_VERSION", "prompts-4.5.6")
    code, prompts = resolve_gnw_versions({"version": "0.1.0"})
    assert code == "code-1.2.3"
    assert prompts == "prompts-4.5.6"


def test_resolve_gnw_versions_uses_metadata_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("GNW_CODE_VERSION", raising=False)
    monkeypatch.delenv("GNW_PROMPTS_VERSION", raising=False)
    code, prompts = resolve_gnw_versions({"version": "0.9.0"})
    assert code == "0.9.0"
    assert prompts == "unknown"


def test_compute_latency_stats() -> None:
    stats = compute_latency_stats([10.0, 20.0, 30.0])
    assert stats is not None
    assert stats.count == 3
    assert stats.avg == 20.0
    assert stats.min == 10.0
    assert stats.max == 30.0
    assert stats.std == pytest.approx(10.0)


def test_compute_latency_stats_single_value_has_zero_std() -> None:
    stats = compute_latency_stats([42.5])
    assert stats is not None
    assert stats.std == 0.0


def test_build_run_summary_context_formats_agent_llm() -> None:
    context = build_run_summary_context(
        api_base_url="https://api.staging.globalnaturewatch.org",
        run_timestamp=datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        api_metadata={
            "version": "0.1.0",
            "model": {
                "current": "gemini",
                "model_class": "ChatGoogleGenerativeAI",
                "small": "gemini-flash",
                "small_model_class": "ChatGoogleGenerativeAI",
            },
        },
        durations=[100.0, 200.0],
    )
    assert context.environment == "staging"
    assert context.gnw_code_version == "0.1.0"
    assert "gemini" in context.gnw_agent_llm
    assert context.latency is not None
    assert context.latency.avg == 150.0


def test_get_eval_judge_llm_label_contains_anthropic() -> None:
    assert "Anthropic" in get_eval_judge_llm_label()


def test_format_run_timestamp_uses_utc() -> None:
    assert format_run_timestamp(datetime(2026, 5, 18, 12, 30, 45, tzinfo=UTC)) == (
        "2026-05-18 12:30:45 UTC"
    )


def test_print_run_summary_header(capsys) -> None:
    context = build_run_summary_context(
        api_base_url="https://api.staging.globalnaturewatch.org",
        run_timestamp=datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        api_metadata={"version": "0.1.0", "model": {}},
        durations=[12.3],
    )
    print_run_summary_header(context)
    output = capsys.readouterr().out
    assert "Environment:" in output
    assert "staging" in output
    assert "GNW code version:" in output
    assert "Eval judge LLM:" in output
    assert "API latency (s):" in output
