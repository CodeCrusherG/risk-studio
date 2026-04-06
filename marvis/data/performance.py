"""Performance schedule contract(S3 Group Analysis Package, Commit 1).

Combination analysis package consumption"Show time."It's a long watch: every loan is on every observation month.
Overdue barrel status (optional balance). This module defines the minimum column contract and the validation function of the table
``validate_performance_frame``,Validation failed to throw and structuretyped error
(:class:`marvis.data.errors.PerformanceFrameError`),Cross-Subprocess Boundary Belt``to_detail()``
Diagnosis (withNanLabelNotConfirmedError (Same paragraph model)/It's not parseable.

Semantic order of the barrel state (good to bad)/ The machine is inconvenient. It's always through the caller.``states``
visible given; this module only"The buckets are all there.states Internal",No order infers.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from marvis.data.errors import PerformanceFrameError


#: The maximum number of characters (specific values embedded in the error file to avoid excessive length) that are cut when displaying a non-defeating sample rule value.
_SAMPLE_VALUE_MAX_LEN = 40
#: The maximum number of sample values for each category of question.
_MAX_SAMPLES = 5


@dataclass(frozen=True)
class PerformanceFrameContract:
    """The parsed column contract for the performance snapshot (repatriation after validation for direct use in downstream tools)."""

    id_col: str
    snapshot_col: str
    bucket_col: str
    balance_col: str | None
    row_count: int
    #: The actual barrel withdrawal value in the data (pressed)states in order, only including the presence).
    observed_states: tuple[str, ...]


def validate_performance_frame(
    df: pd.DataFrame,
    *,
    id_col: str,
    snapshot_col: str,
    bucket_col: str,
    states: list[str] | tuple[str, ...],
    balance_col: str | None = None,
) -> PerformanceFrameContract:
    """Verify a performance schedule to meet the minimum column contract and return the parsed:class:`PerformanceFrameContract`.

    The contract requires:

    - ``id_col`` / ``snapshot_col`` / ``bucket_col`` Three rows must exist (``balance_col`` If a given must also exist;
    - ``snapshot_col`` Each line can be deciphered.``YYYY-MM`` The moon is fast.
    - ``bucket_col`` Every non-empty take-off value falls on``states`` (a) Within the limits of the quantity;
    - ``balance_col`` If given, the value can be deciphered in each row.

    Any article that does not satisfy the throw:class:`PerformanceFrameError`,``to_detail()`` Carry
    ``reason`` / ``missing_columns`` / Standardized Diagnosis (Chinese Language)+ The blog is a short-term review of the situation.
    """
    state_order = tuple(str(state) for state in states)
    if not state_order:
        raise PerformanceFrameError(
            reason="states Can not be empty: The symmetric order of the barrel status must be visible by the caller.",
            problem="empty_states",
        )
    if len(set(state_order)) != len(state_order):
        raise PerformanceFrameError(
            reason="states Contains a duplicate barrel withdrawal value; each barrel can only occur once.",
            problem="duplicate_states",
            samples=[state for state in state_order if state_order.count(state) > 1][:_MAX_SAMPLES],
        )

    required = [id_col, snapshot_col, bucket_col]
    if balance_col:
        required.append(balance_col)
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise PerformanceFrameError(
            reason=f"The required column is missing in the performance chart:{', '.join(missing)}.",
            problem="missing_columns",
            missing_columns=missing,
        )

    row_count = int(len(df))

    # snapshot Columns by Row must be parsable toYYYY-MM.
    bad_snapshots = _unparseable_snapshots(df[snapshot_col])
    if bad_snapshots:
        raise PerformanceFrameError(
            reason=f"Quick-Moon`{snapshot_col}` Yes.{len(bad_snapshots)} Line Can not parse toYYYY-MM Quick moon.",
            problem="bad_snapshot",
            column=snapshot_col,
            samples=[_truncate(value) for value in bad_snapshots[:_MAX_SAMPLES]],
        )

    # bucket The non-empty values for each column must bestates Inside.
    unknown = _unknown_buckets(df[bucket_col], state_order)
    if unknown:
        raise PerformanceFrameError(
            reason=(
                f"Overdue barrel bar`{bucket_col}` Come on.states Extra value:{', '.join(_truncate(v) for v in unknown[:_MAX_SAMPLES])};"
                f"Declared barrel:{', '.join(state_order)}."
            ),
            problem="unknown_bucket",
            column=bucket_col,
            samples=[_truncate(value) for value in unknown[:_MAX_SAMPLES]],
        )

    if balance_col:
        bad_balances = _unparseable_balances(df[balance_col])
        if bad_balances:
            raise PerformanceFrameError(
                reason=f"Balance column`{balance_col}` Yes.{len(bad_balances)} Rows cannot be parsed to a value.",
                problem="bad_balance",
                column=balance_col,
                samples=[_truncate(value) for value in bad_balances[:_MAX_SAMPLES]],
            )

    observed = _observed_states(df[bucket_col], state_order)
    return PerformanceFrameContract(
        id_col=str(id_col),
        snapshot_col=str(snapshot_col),
        bucket_col=str(bucket_col),
        balance_col=str(balance_col) if balance_col else None,
        row_count=row_count,
        observed_states=observed,
    )


def parse_snapshot_month(value) -> str | None:
    """Make a snapshot standard.``YYYY-MM``;Unresolved Return``None``(Don't throw the anomaly."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m")
    if hasattr(value, "strftime") and not isinstance(value, str):
        try:
            return pd.Timestamp(value).strftime("%Y-%m")
        except (ValueError, TypeError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 6 and text.isdigit():
        year, month = int(text[:4]), int(text[4:])
        return f"{year:04d}-{month:02d}" if _valid_month(year, month) else None
    if len(text) >= 7 and text[4] == "-" and text[:4].isdigit() and text[5:7].isdigit():
        year, month = int(text[:4]), int(text[5:7])
        return f"{year:04d}-{month:02d}" if _valid_month(year, month) else None
    try:
        parsed = pd.to_datetime(text, errors="raise")
    except (ValueError, TypeError):
        return None
    return pd.Timestamp(parsed).strftime("%Y-%m")


def _valid_month(year: int, month: int) -> bool:
    return year >= 1 and 1 <= month <= 12


def _unparseable_snapshots(series: pd.Series) -> list:
    bad: list = []
    for value in series.tolist():
        if value is None or (not isinstance(value, str) and pd.isna(value)):
            bad.append(value)
            continue
        if parse_snapshot_month(value) is None:
            bad.append(value)
    return bad


def _unknown_buckets(series: pd.Series, states: tuple[str, ...]) -> list[str]:
    valid = set(states)
    seen: list[str] = []
    seen_set: set[str] = set()
    for value in series.tolist():
        if value is None or (not isinstance(value, str) and pd.isna(value)):
            continue
        text = str(value)
        if text not in valid and text not in seen_set:
            seen_set.add(text)
            seen.append(text)
    return seen


def _observed_states(series: pd.Series, states: tuple[str, ...]) -> tuple[str, ...]:
    present: set[str] = set()
    for value in series.tolist():
        if value is None or (not isinstance(value, str) and pd.isna(value)):
            continue
        present.add(str(value))
    return tuple(state for state in states if state in present)


def _unparseable_balances(series: pd.Series) -> list:
    numeric = pd.to_numeric(series, errors="coerce")
    original_na = series.isna().to_numpy()
    coerced_na = numeric.isna().to_numpy()
    bad: list = []
    values = series.tolist()
    for index in range(len(values)):
        if coerced_na[index] and not original_na[index]:
            bad.append(values[index])
    return bad


def _truncate(value) -> str:
    text = str(value)
    if len(text) > _SAMPLE_VALUE_MAX_LEN:
        return text[:_SAMPLE_VALUE_MAX_LEN] + "…"
    return text


__all__ = [
    "PerformanceFrameContract",
    "parse_snapshot_month",
    "validate_performance_frame",
]
