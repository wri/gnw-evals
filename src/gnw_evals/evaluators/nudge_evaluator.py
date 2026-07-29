"""Nudge evaluator.

Checks the generic ``nudge`` state field (``{type, options}``) that the agent
emits via ``send_nudge`` or the ``pick_aoi``/``pick_dataset`` nudge migrations
(aoi_choice, dataset_choice) - see wri/project-zeno#770. This is a deterministic
substitute for LLM-judged clarification detection whenever a test case expects
one of these specific nudge shapes: the nudge type and options are read
directly off agent state instead of inferred from prose.

Both the nudge type and the option wording are themselves LLM-generated for
aoi_choice/dataset_choice nudges (only the literal send_nudge-with-fixed-args
case is fully deterministic), so both comparisons below are deliberately
loose: type accepts a semicolon-separated set of acceptable values, and
options match by case-insensitive substring containment rather than exact
equality, so annotation drift (e.g. "Tree cover loss" vs "Tree cover loss
(annual)") doesn't fail the check.
"""

from typing import Any


def _option_matches(actual: str, expected: str) -> bool:
    """Check if an actual/expected option pair refer to the same thing.

    Case-insensitive substring containment in either direction, so short
    canonical names (e.g. "Odisha, India") match longer LLM-phrased variants
    (e.g. "Puri, Odisha, India (District)") regardless of which one is more
    verbose.
    """
    a = actual.strip().lower()
    e = expected.strip().lower()
    return a == e or a in e or e in a


def evaluate_nudge(
    agent_state: dict[str, Any],
    expected_nudge_type: str | None,
    expected_nudge_options: list[str] | None,
) -> dict[str, Any]:
    """Check if the agent emitted the expected nudge type and options.

    Args:
        agent_state: Final agent state after execution
        expected_nudge_type: Expected nudge type(s), semicolon-separated if
            more than one value is acceptable (e.g. "aoi_choice;clarify_aoi").
            Empty/None means no type check.
        expected_nudge_options: Allowed nudge options. The agent must offer
            at least one, and may not offer any outside this set (matched by
            substring, not exact equality - see `_option_matches`). Empty/None
            means no options check.

    Returns:
        Dict with:
        - nudge_match_score (0/1/None): 1.0 if the actual nudge type (when
          expected) matches and the actual options (when expected) are a
          valid non-empty subset of the expected options, 0.0 otherwise,
          None if neither expected_nudge_type nor expected_nudge_options is
          provided
        - actual_nudge_type (str | None): Actual nudge type from agent state
        - actual_nudge_options (str | None): Semicolon-separated actual nudge
          options from agent state

    """
    if not expected_nudge_type and not expected_nudge_options:
        return {
            "nudge_match_score": None,
            "actual_nudge_type": None,
            "actual_nudge_options": None,
        }

    nudge = agent_state.get("nudge")
    nudge = nudge if isinstance(nudge, dict) else {}

    actual_type = str(nudge.get("type") or "").strip()

    raw_options = nudge.get("options", [])
    if isinstance(raw_options, str):
        actual_options_list = [o.strip() for o in raw_options.split(";") if o.strip()]
    elif isinstance(raw_options, list):
        actual_options_list = [str(o).strip() for o in raw_options if str(o).strip()]
    else:
        actual_options_list = []

    actual_options_str = "; ".join(actual_options_list) if actual_options_list else None

    type_ok = True
    if expected_nudge_type:
        expected_types = {
            t.strip().lower() for t in expected_nudge_type.split(";") if t.strip()
        }
        type_ok = actual_type.lower() in expected_types

    options_ok = True
    if expected_nudge_options:
        if not actual_options_list:
            options_ok = False
        else:
            at_least_one_match = any(
                _option_matches(actual, expected)
                for actual in actual_options_list
                for expected in expected_nudge_options
            )
            all_within_expected = all(
                any(
                    _option_matches(actual, expected)
                    for expected in expected_nudge_options
                )
                for actual in actual_options_list
            )
            options_ok = at_least_one_match and all_within_expected

    score = 1.0 if (type_ok and options_ok) else 0.0

    return {
        "nudge_match_score": score,
        "actual_nudge_type": actual_type or None,
        "actual_nudge_options": actual_options_str,
    }
