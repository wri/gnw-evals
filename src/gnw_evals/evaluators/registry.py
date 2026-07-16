"""Evaluator registry: bucket-tagged, toggleable evaluator dispatch.

Every evaluator registers here with metadata; the runner iterates the
registry instead of hand-calling evaluator functions. Two structures matter:

- ``EVALUATORS``: ordered specs used for dispatch and per-run/per-case
  toggles. Order is the merge order of result dicts; ``ground_truth`` stays
  last so its ``actual_canopy_cover``/``actual_forest_filter`` win over the
  ``parameters`` evaluator's extraction for intent cases.
- ``SCORE_FIELD_BUCKETS``: maps each gate-relevant score field to one of the
  three buckets (retrieval / analysis / explanation) used by the staged-gate
  scoring model. Bucket membership is per score field, not per evaluator,
  because one evaluator can span buckets (ground truth: stage 1 fidelity is
  analysis, stage 2 number usage is explanation) and the parameter
  evaluator's crop/gas checks judge the presented insight (explanation)
  while its canopy/filter/intersection checks are retrieval.

Staged gate (see PRDs/eval-metrics-programme.md in the workspace): a case's
retrieval checks must all pass for analysis to be scored, and analysis must
pass for explanation. Gating is applied at aggregation time only - every
enabled evaluator still runs, so per-check scores and legacy overall_score
are unchanged by the gate.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from gnw_evals.evaluators.answer_evaluator import evaluate_final_answer
from gnw_evals.evaluators.aoi_evaluator import evaluate_aoi_selection
from gnw_evals.evaluators.chart_type_evaluator import evaluate_chart_type
from gnw_evals.evaluators.clarification_evaluator import evaluate_clarification
from gnw_evals.evaluators.dashboard_evaluator import (
    evaluate_dashboard_aoi,
    evaluate_dashboard_created,
    evaluate_dashboard_widgets,
)
from gnw_evals.evaluators.data_pull_evaluator import (
    evaluate_data_pull,
    evaluate_date_selection,
)
from gnw_evals.evaluators.dataset_evaluator import evaluate_dataset_selection
from gnw_evals.evaluators.ground_truth_evaluator import evaluate_ground_truth
from gnw_evals.evaluators.parameter_evaluator import evaluate_parameters
from gnw_evals.evaluators.suggested_datasets_evaluator import (
    evaluate_suggested_datasets,
)
from gnw_evals.utils.eval_types import ExpectedData

RETRIEVAL = "retrieval"
ANALYSIS = "analysis"
EXPLANATION = "explanation"
BUCKETS = (RETRIEVAL, ANALYSIS, EXPLANATION)

# Adapter signature every registered evaluator is wrapped in.
EvaluatorFn = Callable[
    [dict[str, Any], ExpectedData, str, dict[str, Any] | None],
    dict[str, Any],
]


@dataclass(frozen=True)
class EvaluatorSpec:
    """A registered evaluator."""

    name: str
    kind: str  # "deterministic" | "llm_judge" | "mixed"
    score_fields: tuple[str, ...]
    run: EvaluatorFn


def _insight_text(agent_state: dict[str, Any]) -> str:
    """First chart's insight text, used by the crop/gas focus judges."""
    charts_data = agent_state.get("charts_data") or []
    if charts_data and isinstance(charts_data[0], dict):
        return charts_data[0].get("insight", "") or ""
    return ""


EVALUATORS: tuple[EvaluatorSpec, ...] = (
    EvaluatorSpec(
        name="clarification",
        kind="llm_judge",
        score_fields=("clarification_requested_score",),
        run=lambda state, expected, query, dashboard: evaluate_clarification(
            state,
            expected.expected_clarification,
            query,
        ),
    ),
    EvaluatorSpec(
        name="aoi",
        kind="deterministic",
        score_fields=("aoi_id_match_score",),
        run=lambda state, expected, query, dashboard: evaluate_aoi_selection(
            state,
            expected.expected_aoi_ids,
            query,
        ),
    ),
    EvaluatorSpec(
        name="dataset",
        kind="deterministic",
        score_fields=(
            "dataset_id_match_score",
            "dataset_parameter_match_score",
            "context_layer_match_score",
        ),
        run=lambda state, expected, query, dashboard: evaluate_dataset_selection(
            state,
            expected.expected_dataset_id,
            expected.expected_dataset_parameters,
            expected.expected_context_layer,
            query,
        ),
    ),
    EvaluatorSpec(
        name="date",
        kind="deterministic",
        score_fields=("date_match_score",),
        run=lambda state, expected, query, dashboard: evaluate_date_selection(
            state,
            expected_start_date=expected.expected_start_date,
            expected_end_date=expected.expected_end_date,
        ),
    ),
    EvaluatorSpec(
        name="parameters",
        kind="mixed",
        score_fields=(
            "canopy_cover_match_score",
            "forest_filter_match_score",
            "intersections_match_score",
            "crop_type_match_score",
            "gas_type_match_score",
        ),
        run=lambda state, expected, query, dashboard: evaluate_parameters(
            state,
            expected_canopy_cover=expected.expected_canopy_cover,
            expected_forest_filter=expected.expected_forest_filter,
            expected_intersections=expected.expected_intersections,
            expected_crop_types=expected.expected_crop_types,
            expected_gas_types=expected.expected_gas_types,
            insight_text=_insight_text(state),
        ),
    ),
    EvaluatorSpec(
        name="data_pull",
        kind="deterministic",
        score_fields=("data_pull_exists_score",),
        run=lambda state, expected, query, dashboard: evaluate_data_pull(
            state,
            expects_data_pull=expected.expects_data_pull(),
            query=query,
        ),
    ),
    EvaluatorSpec(
        name="answer",
        kind="llm_judge",
        score_fields=(
            "charts_answer_score",
            "agent_answer_score",
            "expected_text_match_score",
        ),
        run=lambda state, expected, query, dashboard: evaluate_final_answer(
            state,
            expected.expected_answer,
            expected.expected_text,
            query,
        ),
    ),
    EvaluatorSpec(
        name="chart_type",
        kind="deterministic",
        score_fields=("chart_type_match_score",),
        run=lambda state, expected, query, dashboard: evaluate_chart_type(
            state,
            expected.expected_chart_type,
        ),
    ),
    EvaluatorSpec(
        name="suggested_datasets",
        kind="deterministic",
        score_fields=("suggested_datasets_match_score",),
        run=lambda state, expected, query, dashboard: evaluate_suggested_datasets(
            state,
            expected.expected_suggested_datasets,
        ),
    ),
    EvaluatorSpec(
        name="dashboard_created",
        kind="deterministic",
        score_fields=("dashboard_created_score",),
        run=lambda state, expected, query, dashboard: evaluate_dashboard_created(
            state,
            expected.expected_dashboard_created,
        ),
    ),
    EvaluatorSpec(
        name="dashboard_aoi",
        kind="deterministic",
        score_fields=("dashboard_aoi_match_score",),
        run=lambda state, expected, query, dashboard: evaluate_dashboard_aoi(
            dashboard,
            expected.expected_aoi_ids,
            expected.expected_aoi_source,
        ),
    ),
    EvaluatorSpec(
        name="dashboard_widgets",
        kind="deterministic",
        score_fields=(
            "dashboard_widgets_match_score",
            "dashboard_widgets_valid_score",
        ),
        run=lambda state, expected, query, dashboard: evaluate_dashboard_widgets(
            dashboard,
            expected.expected_dashboard_widgets,
        ),
    ),
    EvaluatorSpec(
        name="ground_truth",
        kind="mixed",
        score_fields=("data_fidelity_score", "number_usage_score"),
        run=lambda state, expected, query, dashboard: evaluate_ground_truth(
            state,
            expected,
            query,
        ),
    ),
)

EVALUATOR_NAMES: frozenset[str] = frozenset(spec.name for spec in EVALUATORS)

SCORE_FIELD_BUCKETS: dict[str, str] = {
    # Retrieval: did the agent understand the prompt and select the right
    # parameters, or correctly defer/reject?
    "clarification_requested_score": RETRIEVAL,
    "aoi_id_match_score": RETRIEVAL,
    "dataset_id_match_score": RETRIEVAL,
    "dataset_parameter_match_score": RETRIEVAL,
    "context_layer_match_score": RETRIEVAL,
    "date_match_score": RETRIEVAL,
    "canopy_cover_match_score": RETRIEVAL,
    "forest_filter_match_score": RETRIEVAL,
    "intersections_match_score": RETRIEVAL,
    "suggested_datasets_match_score": RETRIEVAL,
    # Analysis: did the system pull and compute the right numbers?
    "data_pull_exists_score": ANALYSIS,
    "data_fidelity_score": ANALYSIS,
    # Explanation: did the agent use the data well in what the user sees?
    # Crop/gas checks judge the presented insight text, hence explanation.
    "charts_answer_score": EXPLANATION,
    "agent_answer_score": EXPLANATION,
    "expected_text_match_score": EXPLANATION,
    "number_usage_score": EXPLANATION,
    "chart_type_match_score": EXPLANATION,
    "crop_type_match_score": EXPLANATION,
    "gas_type_match_score": EXPLANATION,
    "dashboard_created_score": EXPLANATION,
    "dashboard_aoi_match_score": EXPLANATION,
    "dashboard_widgets_match_score": EXPLANATION,
    "dashboard_widgets_valid_score": EXPLANATION,
}

STAGE_SCORE_FIELDS = (
    "retrieval_score",
    "analysis_score",
    "explanation_score",
    "e2e_score",
)


def _parse_names(raw: str) -> set[str]:
    """Split a comma- or semicolon-separated evaluator list."""
    return {
        item.strip()
        for chunk in raw.split(",")
        for item in chunk.split(";")
        if item.strip()
    }


def _validate_names(names: set[str], source: str) -> None:
    unknown = names - EVALUATOR_NAMES
    if unknown:
        raise ValueError(
            f"unknown evaluator name(s) in {source}: {sorted(unknown)}; "
            f"valid names: {sorted(EVALUATOR_NAMES)}",
        )


def resolve_enabled(
    only: str | None = None,
    skip: str | None = None,
) -> frozenset[str] | None:
    """Resolve run-level toggles into an enabled set (None means all).

    Raises ValueError on unknown evaluator names - a typo must fail the run,
    not silently score everything.
    """
    if not only and not skip:
        return None
    enabled = set(EVALUATOR_NAMES)
    if only:
        only_names = _parse_names(only)
        _validate_names(only_names, "--evaluators")
        enabled = only_names
    if skip:
        skip_names = _parse_names(skip)
        _validate_names(skip_names, "--skip-evaluators")
        enabled -= skip_names
    return frozenset(enabled)


def resolve_case_evaluators(
    run_enabled: frozenset[str] | None,
    expected_data: ExpectedData,
) -> frozenset[str]:
    """Combine run-level and per-case toggles into the effective enabled set.

    A non-empty ``evaluators`` column on a case means "only these apply to
    this case"; it is intersected with the run-level set.
    """
    enabled = run_enabled if run_enabled is not None else EVALUATOR_NAMES
    case_raw = expected_data.evaluators
    if case_raw:
        case_names = _parse_names(case_raw)
        _validate_names(
            case_names, f"case {expected_data.test_id or '?'} evaluators column"
        )
        enabled = frozenset(enabled & case_names)
    return frozenset(enabled)


def compute_stage_scores(evaluations: dict[str, Any]) -> dict[str, float | None]:
    """Apply the staged gate to a case's evaluation results.

    Per bucket: None when no check in that bucket was applicable, 1.0 when
    every applicable check passed, 0.0 otherwise. A failed stage gates the
    later stages to None (not scored). ``e2e_score`` is 1.0 only when no
    evaluated stage failed; a case whose only applicable stage is retrieval
    (correct clarification/refusal) passes end to end.
    """

    def bucket_outcome(bucket: str) -> float | None:
        values = [
            value
            for field, field_bucket in SCORE_FIELD_BUCKETS.items()
            if field_bucket == bucket and (value := evaluations.get(field)) is not None
        ]
        if not values:
            return None
        return 1.0 if all(value == 1.0 for value in values) else 0.0

    retrieval = bucket_outcome(RETRIEVAL)
    analysis = None if retrieval == 0.0 else bucket_outcome(ANALYSIS)
    explanation = (
        None if retrieval == 0.0 or analysis == 0.0 else bucket_outcome(EXPLANATION)
    )

    stages = (retrieval, analysis, explanation)
    evaluated = [stage for stage in stages if stage is not None]
    if not evaluated:
        e2e: float | None = None
    else:
        e2e = 0.0 if any(stage == 0.0 for stage in stages) else 1.0

    return {
        "retrieval_score": retrieval,
        "analysis_score": analysis,
        "explanation_score": explanation,
        "e2e_score": e2e,
    }
