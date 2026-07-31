"""Deterministic numeric check for chart rows.

`llm_judge_chart` cannot be trusted with the arithmetic. Asked about a chart whose 25
yearly values sum to 25.31 Mha, it reported that same chart as summing to 27.4 Mha and to
26.0 Mha, each "within tolerance" of whatever expected value it had been handed. So the
comparison happens here instead: the expected figure is parsed from the sheet, the
candidate figures are computed from the chart's own encoded data, and the model is left to
judge only whether the chart is an appropriate, complete answer to the query.

Support is deliberately three-valued. `None` means "no numeric claim to check" — a year, a
bare place name, or a figure whose decimal separator is ambiguous — and leaves the verdict
entirely to the judge.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

# Scale written as a word, which the sheet uses as often as a unit prefix: "25.54 million
# hectares" sits beside "25 Mha". Missing these was worth three false failures on the
# 2026-07-31 run, each reported as a difference of tens of millions of percent.
_SCALE_WORDS = {
    "thousand": 1_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
}

# Unit suffix -> multiplier into the unit the chart data is encoded in. Anything not
# listed is treated as a bare number (MgCO2e, tonnes, counts), which compares directly.
_UNIT_MULTIPLIERS = {
    "mha": 1_000_000,
    "kha": 1_000,
    "ha": 1,
    "hectares": 1,
    "hectare": 1,
    "hektar": 1,  # Indonesian; gold has multilingual rows
    "hektare": 1,
}

# Keys that hold labels or ordinals rather than measures. Summing a `year` column gives
# 50,325, which would otherwise become a candidate figure.
_NON_MEASURE_KEYS = frozenset(
    {
        "year",
        "years",
        "month",
        "day",
        "date",
        "id",
        "index",
        "order",
        "position",
        "rank",
    },
)

# A number written as `230.003` may be two hundred thousand (Indonesian, Spanish) or two
# hundred point oh oh three. Exactly three digits after a single dot, with no second
# decimal group, is unresolvable from the string alone.
_AMBIGUOUS_DECIMAL = re.compile(r"^\d{1,3}\.\d{3}$")

# A leading number, optionally with thousands separators and a decimal part.
_NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)")

_YEAR = re.compile(r"^(19|20)\d{2}$")


def _fmt(value: float) -> str:
    """Render a figure the way the sheet writes them, not as 2.5e+07.

    These strings land in `chart_answer_score_reason` and get read next to the sheet's
    own cells, so thousands separators matter more than compactness.
    """
    if abs(value) >= 1_000:
        return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"
    return f"{value:g}"


@dataclass(frozen=True)
class ExpectedNumber:
    """A numeric claim parsed out of an `expected_answer` cell."""

    value: float
    is_percent: bool
    raw: str


def parse_expected_number(expected_answer: str) -> ExpectedNumber | None:
    """Pull the figure out of an expected answer, or None when there isn't one to check.

    Returns None for years ("2003"), bare named entities ("Waikato"), empty cells, and
    figures whose decimal separator is ambiguous — every case where a deterministic
    comparison would be a guess.
    """
    text = (expected_answer or "").strip()
    if not text:
        return None

    match = _NUMBER.search(text)
    if not match:
        return None

    token = match.group(1)
    if _YEAR.match(token):
        return None
    if _AMBIGUOUS_DECIMAL.match(token):
        return None

    try:
        value = float(token.replace(",", ""))
    except ValueError:
        return None
    if value == 0:
        # A relative difference against zero is undefined.
        return None

    remainder = text[match.end() :].lstrip()
    is_percent = remainder.startswith("%")
    if not is_percent:
        # A written scale comes before the unit: "million hectares", "billion tCO2e".
        word = re.match(r"[A-Za-z]+", remainder)
        if word and word.group(0).lower() in _SCALE_WORDS:
            value *= _SCALE_WORDS[word.group(0).lower()]
            remainder = remainder[word.end() :].lstrip()

        unit = re.match(r"[A-Za-z²]+", remainder)
        if unit:
            value *= _UNIT_MULTIPLIERS.get(unit.group(0).lower(), 1)

    return ExpectedNumber(value=value, is_percent=is_percent, raw=token)


def _numeric_items(node: Any) -> list[tuple[str, float]]:
    """Every numeric leaf in the structure, paired with the key that held it."""
    found: list[tuple[str, float]] = []

    def walk(value: Any, key: str) -> None:
        if isinstance(value, bool):
            return
        if isinstance(value, int | float):
            found.append((key.lower(), float(value)))
        elif isinstance(value, dict):
            for k, v in value.items():
                walk(v, str(k))
        elif isinstance(value, list):
            for item in value:
                walk(item, key)

    walk(node, "")
    return found


def _series_aggregates(node: Any) -> list[float]:
    """Totals and maxima of every measure column in every list-of-records found.

    A chart that plots 25 yearly values supports an expected period total even though it
    never draws one, so the sum has to be a candidate.
    """
    aggregates: list[float] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
            return
        if not isinstance(value, list):
            return

        records = [item for item in value if isinstance(item, dict)]
        if records:
            keys = {k for record in records for k in record}
            for key in keys:
                if key.lower() in _NON_MEASURE_KEYS:
                    continue
                numbers = [
                    float(record[key])
                    for record in records
                    if isinstance(record.get(key), int | float)
                    and not isinstance(record.get(key), bool)
                ]
                if numbers:
                    aggregates.append(sum(numbers))
                    aggregates.append(max(numbers))
        for item in value:
            walk(item)

    walk(node)
    return aggregates


def _percent_candidates(node: Any) -> list[float]:
    """Each measure value as a percentage of its own column total.

    Charts encode areas; the sheet often expects the share ("8.57%"), so the share has to
    be derived here rather than asked of the model.
    """
    shares: list[float] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
            return
        if not isinstance(value, list):
            return

        records = [item for item in value if isinstance(item, dict)]
        if records:
            keys = {k for record in records for k in record}
            for key in keys:
                if key.lower() in _NON_MEASURE_KEYS:
                    continue
                numbers = [
                    float(record[key])
                    for record in records
                    if isinstance(record.get(key), int | float)
                    and not isinstance(record.get(key), bool)
                ]
                total = sum(numbers)
                if total:
                    shares.extend(number / total * 100 for number in numbers)
        for item in value:
            walk(item)

    walk(node)
    return shares


def chart_candidate_values(charts_json: str, is_percent: bool = False) -> list[float]:
    """Every figure a reader could take from the chart, for matching against expected.

    Leaf values, column totals and column maxima; plus per-column shares when the expected
    answer is a percentage. Label-ish columns (`year`, `id`, ...) are excluded from
    aggregates so their sums don't become candidates.
    """
    try:
        charts = json.loads(charts_json or "")
    except (json.JSONDecodeError, TypeError):
        return []

    candidates = [
        value for key, value in _numeric_items(charts) if key not in _NON_MEASURE_KEYS
    ]
    candidates += _series_aggregates(charts)
    if is_percent:
        candidates += _percent_candidates(charts)
    return [value for value in candidates if value != 0]


def evaluate_numeric_support(
    expected_answer: str,
    charts_json: str,
    tolerance: float,
) -> dict[str, Any]:
    """Check whether the chart's own data supports the expected figure.

    Returns `support` as "supported", "unsupported", or None when there is no numeric
    claim to check. `explanation` is written for the score reason so a verdict can be
    audited without re-running anything.
    """
    result: dict[str, Any] = {
        "support": None,
        "expected_value": None,
        "closest_value": None,
        "difference": None,
        "explanation": "",
    }

    expected = parse_expected_number(expected_answer)
    if expected is None:
        return result

    result["expected_value"] = expected.value
    candidates = chart_candidate_values(charts_json, is_percent=expected.is_percent)
    unit = "%" if expected.is_percent else ""

    if not candidates:
        result["support"] = "unsupported"
        result["explanation"] = (
            f"deterministic check: the chart data holds no figure to compare against the "
            f"expected {_fmt(expected.value)}{unit}"
        )
        return result

    closest = min(candidates, key=lambda value: abs(value - expected.value))
    difference = abs(closest - expected.value) / abs(expected.value)
    within = difference <= tolerance

    result["support"] = "supported" if within else "unsupported"
    result["closest_value"] = closest
    result["difference"] = difference
    result["explanation"] = (
        f"deterministic check: the chart's closest figure to the expected "
        f"{_fmt(expected.value)}{unit} is {_fmt(closest)}{unit}, "
        f"a {difference:.2%} difference, "
        f"{'within' if within else 'exceeding'} the {tolerance:.0%} tolerance"
    )
    return result
