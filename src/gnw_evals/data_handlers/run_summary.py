"""Committed run-summary artefact: the longitudinal unit of the scorecard.

Official runs write one JSON file to ``runs/`` capturing per-cell coverage
and staged-gate quality. The scorecard renders history from these files;
pass rates are comparable only within a ``methodology_version`` (bump it
when evaluators, gating or thresholds change materially).
"""

import csv
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from gnw_evals.evaluators.registry import SCORE_FIELD_BUCKETS
from gnw_evals.utils.eval_types import TestResult
from gnw_evals.utils.run_metadata import get_eval_judge_llm_label, infer_environment

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RUNS_DIR = REPO_ROOT / "runs"
CASES_DIR = REPO_ROOT / "cases"
MANIFEST_DIR = CASES_DIR / "manifests"

# Bump on material changes to evaluators, staged-gate logic or thresholds.
METHODOLOGY_VERSION = "1.0.0"

# dataset_id -> catalog slug, for joining results to case/manifest files.
# Mirrors project-zeno src/agent/datasets/catalog/*.yml (dataset_id fields);
# insertion order is the scorecard's row order.
DATASET_SLUGS = {
    "0": "global_all_ecosystem_disturbance_alerts_dist_alert",
    "1": "global_land_cover",
    "2": "global_natural_semi_natural_grassland_extent",
    "3": "sbtn_natural_lands_map",
    "4": "tree_cover_loss",
    "5": "tree_cover_gain",
    "6": "forest_greenhouse_gas_net_flux",
    "7": "tree_cover",
    "8": "tree_cover_loss_by_dominant_driver",
    "9": "deforestation_sluc_emission_factors_by_agricultural_crop",
    "10": "tree_cover_loss_from_fires",
    "11": "integrated_alerts",
}

# Surface coverage per the evaluator coverage roadmap (workspace
# PRDs/evaluator-coverage-roadmap.md): checks wired and applicable to
# numeric-intent cells vs checks mapped for them (wired + planned).
_WIRED_APPLICABLE = (
    "aoi",
    "dataset_parameters",
    "date",
    "parameters",
    "data_pull",
    "ground_truth_fidelity",
    "number_usage",
    "chart_type",
)
_MAPPED_PLANNED = (
    "language",
    "insight_quality",
    "limitation_compliance",
    "tool_selection",
    "query_correctness",
    "hallucination",
)
SURFACE_COVERAGE_NUMERIC = len(_WIRED_APPLICABLE) / (
    len(_WIRED_APPLICABLE) + len(_MAPPED_PLANNED)
)

_TIER_THRESHOLDS = {
    "comprehensive": {"prompt": 0.8, "surface": 0.9, "languages": 2},
    "good": {"prompt": 0.5, "surface": 0.7},
    "partial": {"min_cases": 10, "surface": 0.4},
}


def coverage_tier(
    n_cases: int,
    prompt_coverage: float | None,
    surface_coverage: float,
    non_english_languages: int,
) -> str:
    """Tier per the programme PRD's provisional thresholds.

    The minimal trap (too few cases or too little surface) applies first,
    regardless of how good the other numbers look.
    """
    prompt = prompt_coverage or 0.0
    if (
        n_cases < _TIER_THRESHOLDS["partial"]["min_cases"]
        or surface_coverage < _TIER_THRESHOLDS["partial"]["surface"]
    ):
        return "minimal"
    if (
        prompt >= _TIER_THRESHOLDS["comprehensive"]["prompt"]
        and surface_coverage >= _TIER_THRESHOLDS["comprehensive"]["surface"]
        and non_english_languages >= _TIER_THRESHOLDS["comprehensive"]["languages"]
    ):
        return "comprehensive"
    if (
        prompt >= _TIER_THRESHOLDS["good"]["prompt"]
        and surface_coverage >= _TIER_THRESHOLDS["good"]["surface"]
    ):
        return "good"
    return "partial"


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _rate(results: list[TestResult], field: str) -> float | None:
    values = [v for r in results if (v := getattr(r, field, None)) is not None]
    return _mean(values)


def _prompt_coverage(slug: str, intent: str) -> tuple[float | None, int, int]:
    """(coverage, non-english languages, case-set size) from the files on disk.

    Coverage is a property of the case set, not of the (possibly filtered)
    run, so it is always computed from the full case file.
    """
    manifest_path = MANIFEST_DIR / f"{slug}__{intent}.manifest.csv"
    cases_path = CASES_DIR / f"{slug}__{intent}.csv"
    if not manifest_path.exists() or not cases_path.exists():
        return None, 0, 0

    with open(manifest_path, encoding="utf-8") as f:
        manifest_ids = [row["manifest_id"] for row in csv.DictReader(f)]
    covered: set[str] = set()
    non_english: set[str] = set()
    case_set_size = 0
    with open(cases_path, encoding="utf-8") as f:
        for case in csv.DictReader(f):
            case_set_size += 1
            if case.get("manifest_id"):
                covered.add(case["manifest_id"])
            language = (case.get("expected_language") or "").strip().lower()
            if language and language != "en":
                non_english.add(language)
    if not manifest_ids:
        return None, len(non_english), case_set_size
    fraction = len(covered & set(manifest_ids)) / len(manifest_ids)
    return round(fraction, 4), len(non_english), case_set_size


def _failed_stage(result: TestResult) -> str | None:
    if result.error:
        return "error"
    for stage, field in (
        ("retrieval", "retrieval_score"),
        ("analysis", "analysis_score"),
        ("explanation", "explanation_score"),
    ):
        value = getattr(result, field, None)
        if value is not None and value < 1.0:
            return stage
    return None


def _failure_comment(result: TestResult) -> str | None:
    return (
        result.error
        or result.number_usage_failure_comment
        or result.data_fidelity_missing
        or result.agent_answer_score_reason
        or None
    )


def _case_entry(result: TestResult) -> dict[str, Any]:
    return {
        "test_id": result.test_id,
        "manifest_id": getattr(result, "manifest_id", "") or "",
        "eval_subtype": result.eval_subtype,
        "e2e_score": result.e2e_score,
        "retrieval_score": result.retrieval_score,
        "analysis_score": result.analysis_score,
        "explanation_score": result.explanation_score,
        "failed_stage": _failed_stage(result),
        "failure_comment": _failure_comment(result),
        "app_thread_url": result.app_thread_url,
        "trace_url": result.trace_url,
    }


def _cell_summary(
    dataset_id: str,
    intent: str,
    results: list[TestResult],
) -> dict[str, Any]:
    slug = DATASET_SLUGS.get(dataset_id, dataset_id)
    prompt_coverage, non_english, case_set_size = _prompt_coverage(slug, intent)
    per_evaluator = {
        field: rate
        for field in sorted(SCORE_FIELD_BUCKETS)
        if (rate := _rate(results, field)) is not None
    }
    return {
        "dataset_id": dataset_id,
        "dataset_slug": slug,
        "intent": intent,
        "n_cases": len(results),
        "coverage": {
            "prompt": prompt_coverage,
            "surface": round(SURFACE_COVERAGE_NUMERIC, 4),
            # Tier reflects the committed case set (falling back to the run's
            # own size when no case file exists), not a filtered run subset.
            "case_set_size": case_set_size,
            "tier": coverage_tier(
                case_set_size or len(results),
                prompt_coverage,
                SURFACE_COVERAGE_NUMERIC,
                non_english,
            ),
        },
        "quality": {
            "e2e_pass_rate": _rate(results, "e2e_score"),
            "retrieval": _rate(results, "retrieval_score"),
            "analysis": _rate(results, "analysis_score"),
            "explanation": _rate(results, "explanation_score"),
        },
        "per_evaluator": per_evaluator,
        "cases": [_case_entry(r) for r in results],
    }


def _case_set_version() -> str:
    """Short content hash over the committed case files."""
    digest = hashlib.sha256()
    for path in sorted(CASES_DIR.glob("*.csv")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def _git_sha() -> str:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=True,
            ).stdout.strip()
            or "unknown"
        )
    except Exception:
        return "unknown"


def build_run_summary(
    results: list[TestResult],
    *,
    api_base_url: str,
    ff: str | None,
    num_trials: int,
    run_timestamp: datetime | None = None,
    api_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate a run's results into the committed summary structure."""
    timestamp = run_timestamp or datetime.now(UTC)

    by_cell: dict[tuple[str, str], list[TestResult]] = {}
    non_matrix: list[TestResult] = []
    for result in results:
        if result.intent:
            key = (str(result.expected_dataset_id), result.intent)
            by_cell.setdefault(key, []).append(result)
        else:
            non_matrix.append(result)

    cells = [
        _cell_summary(dataset_id, intent, cell_results)
        for (dataset_id, intent), cell_results in sorted(by_cell.items())
    ]

    e2e = _rate(results, "e2e_score")
    return {
        "run_id": f"run_{timestamp.strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:6]}",
        "timestamp": timestamp.isoformat(),
        "environment": infer_environment(api_base_url),
        "api_base_url": api_base_url,
        "agent_profile": ff or "default",
        "agent_llm": (api_metadata or {}).get("model") or None,
        "gnw_code_version": (api_metadata or {}).get("version") or None,
        "gnw_evals_sha": _git_sha(),
        "methodology_version": METHODOLOGY_VERSION,
        "case_set_version": _case_set_version(),
        "judge_model": get_eval_judge_llm_label(),
        "num_trials": num_trials,
        "cells": cells,
        "non_matrix_results": len(non_matrix),
        "totals": {
            "n_results": len(results),
            "e2e_pass_rate": e2e,
            "retrieval": _rate(results, "retrieval_score"),
            "analysis": _rate(results, "analysis_score"),
            "explanation": _rate(results, "explanation_score"),
        },
    }


def write_run_summary(summary: dict[str, Any]) -> Path:
    """Write the summary JSON to runs/ and return its path."""
    RUNS_DIR.mkdir(exist_ok=True)
    path = RUNS_DIR / f"{summary['run_id']}_{summary['environment']}.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return path
