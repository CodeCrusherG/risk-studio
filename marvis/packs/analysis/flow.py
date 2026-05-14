"""barrel traffic/ The barrel migration core.(flow_rate + bucket_migration).

Both tools share the same"# Next to each other #"kernel``_aligned_transitions``:Press every loan
Sort it in the moon. Take the next moon.(from_month -> to_month),Statisticsfrom barrel-> to The barrel's moving.
The loan without next month's snapshot is included in the visible.``exited`` Hypocrisy state (indicated, silent abandonment).

- ``flow_rate``:♪ To be given the next month ♪NxN Transfer ratio matrix+ into_bad/out_of_bad Net flow.
- ``bucket_migration``:The monthly migration matrix is consolidated in the window.+ Cell-by-cell monthly matrix.

roll_rate_matrix (strategy Package) Keep it. That's..."Status×Timetable"The caliber. The nucleus is...
"# Next to each other #"The calibre, the semantics, are different.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from marvis.data.performance import parse_snapshot_month, validate_performance_frame
from marvis.packs.analysis.errors import AnalysisError

#: Visible hypocrisy: Loans have a snapshot of a month, but not a full picture of the month (exiting the observation window).
EXITED_STATE = "exited"
#: Aligning a month in a neighbourhood is below that threshold-> sparse_month Red flag.
SPARSE_MONTH_MIN_PAIRS = 100


@dataclass(frozen=True)
class MonthTransition:
    """A month next to each other.(from_month -> to_month) The transfer statistics."""

    month: str  # from_month (Month of transfer occurring)
    to_month: str
    #: from_to_matrix[i][j] = Fromstates[i] Transfer(states + [exited])[j] The share.
    from_to_matrix: list[list[float]]
    #: Every one.from Base number of barrels (in millions of barrels)count orbalance The caliber.
    base: dict[str, float]
    into_bad: float
    out_of_bad: float
    pair_count: int


@dataclass(frozen=True)
class FlowRateResult:
    states: tuple[str, ...]
    #: Output column order= states + [exited].
    to_states: tuple[str, ...]
    months: tuple[str, ...]
    transitions: list[MonthTransition]
    red_flags: list[dict] = field(default_factory=list)


def flow_rate(
    df: pd.DataFrame,
    *,
    id_col: str,
    snapshot_col: str,
    bucket_col: str,
    states: list[str] | tuple[str, ...],
    balance_col: str | None = None,
    bad_states: list[str] | tuple[str, ...] | None = None,
) -> FlowRateResult:
    """The transfer of a statistical barrel from one month to another (pure function).

    ``bad_states`` Default asstates Second half (used ininto_bad/out_of_bad Net flow calibre;
    Here's the default to take the worst of all worse than the first."Bad"The border is not universal enough.
    So it's clear: when default is neededstates The last is called to overwhelm in a visible manner as the only bad state.
    """
    contract = validate_performance_frame(
        df,
        id_col=id_col,
        snapshot_col=snapshot_col,
        bucket_col=bucket_col,
        states=states,
        balance_col=balance_col,
    )
    state_order = tuple(str(state) for state in states)
    bad_set = _resolve_bad_states(state_order, bad_states)
    prepared = _prepare_frame(df, contract)

    pairs = _adjacent_pairs(prepared, state_order)
    months = tuple(sorted({pair["from_month"] for pair in pairs}))
    transitions: list[MonthTransition] = []
    red_flags: list[dict] = []
    to_states = (*state_order, EXITED_STATE)

    for from_month in months:
        month_pairs = [pair for pair in pairs if pair["from_month"] == from_month]
        to_month = month_pairs[0]["to_month"] if month_pairs else ""
        matrix, base, into_bad, out_of_bad = _month_matrix(
            month_pairs, state_order, to_states, bad_set, use_balance=bool(balance_col)
        )
        pair_count = len(month_pairs)
        transitions.append(
            MonthTransition(
                month=from_month,
                to_month=to_month,
                from_to_matrix=matrix,
                base=base,
                into_bad=into_bad,
                out_of_bad=out_of_bad,
                pair_count=pair_count,
            )
        )
        if pair_count < SPARSE_MONTH_MIN_PAIRS:
            red_flags.append(
                {
                    "kind": "sparse_month",
                    "month": from_month,
                    "pair_count": pair_count,
                    "message": f"Month{from_month} Match Months Only{pair_count} Yes<{SPARSE_MONTH_MIN_PAIRS}),The transfer rate is not stable.",
                }
            )

    return FlowRateResult(
        states=state_order,
        to_states=to_states,
        months=months,
        transitions=transitions,
        red_flags=red_flags,
    )


@dataclass(frozen=True)
class BucketMigrationResult:
    states: tuple[str, ...]
    to_states: tuple[str, ...]
    window_months: tuple[str, ...]
    avg_matrix: list[list[float]]
    worst_matrix: list[list[float]]
    #: Rendering line list: Each line{"from": state, "<to_state>": rate, ...}.
    heat_table: list[dict]
    red_flags: list[dict] = field(default_factory=list)


def bucket_migration(
    df: pd.DataFrame,
    *,
    id_col: str,
    snapshot_col: str,
    bucket_col: str,
    states: list[str] | tuple[str, ...],
    balance_col: str | None = None,
    window: list[str] | tuple[str, ...] | None = None,
    bad_states: list[str] | tuple[str, ...] | None = None,
) -> BucketMigrationResult:
    """Convergence the next month of the window into an average migration matrix+ Cell-by-Branch monthly matrix (andflow_rate @Gymsym: #Gymnasium #Gymnasium"""
    result = flow_rate(
        df,
        id_col=id_col,
        snapshot_col=snapshot_col,
        bucket_col=bucket_col,
        states=states,
        balance_col=balance_col,
        bad_states=bad_states,
    )
    window_months = _resolve_window(result.months, window)
    selected = [t for t in result.transitions if t.month in window_months]
    state_order = result.states
    to_states = result.to_states

    n_from = len(state_order)
    n_to = len(to_states)
    if not selected:
        empty = [[0.0] * n_to for _ in range(n_from)]
        return BucketMigrationResult(
            states=state_order,
            to_states=to_states,
            window_months=tuple(window_months),
            avg_matrix=empty,
            worst_matrix=[[0.0] * n_to for _ in range(n_from)],
            heat_table=_heat_table(empty, state_order, to_states),
            red_flags=list(result.red_flags),
        )

    avg = [[0.0] * n_to for _ in range(n_from)]
    worst = [[0.0] * n_to for _ in range(n_from)]
    for i in range(n_from):
        for j in range(n_to):
            cell_values = [t.from_to_matrix[i][j] for t in selected]
            avg[i][j] = sum(cell_values) / len(cell_values)
            # worst = Worst month: Diagonal(Retention/Improvement)Minimal, non-opposite, most bad. Here you are.
            # Use"Maximum rate of emigration"Semantics-- worst Pays attention to the worst migration intensity, taking the maximum monthly value for each cell.
            worst[i][j] = max(cell_values)

    return BucketMigrationResult(
        states=state_order,
        to_states=to_states,
        window_months=tuple(window_months),
        avg_matrix=avg,
        worst_matrix=worst,
        heat_table=_heat_table(avg, state_order, to_states),
        red_flags=list(result.red_flags),
    )


# ---- shared alignment kernel -------------------------------------------------


def _prepare_frame(df: pd.DataFrame, contract) -> pd.DataFrame:
    frame = df[[contract.id_col, contract.snapshot_col, contract.bucket_col]].copy()
    if contract.balance_col:
        frame[contract.balance_col] = pd.to_numeric(df[contract.balance_col], errors="coerce").fillna(0.0)
    frame["_id"] = frame[contract.id_col].astype(str)
    frame["_month"] = frame[contract.snapshot_col].map(parse_snapshot_month)
    frame["_bucket"] = frame[contract.bucket_col].astype(str)
    frame = frame[frame["_month"].notna()].copy()
    if contract.balance_col:
        frame["_balance"] = frame[contract.balance_col].astype(float)
    else:
        frame["_balance"] = 1.0
    return frame


def _adjacent_pairs(frame: pd.DataFrame, states: tuple[str, ...]) -> list[dict]:
    """Monthly ranking of each loan, with output moving in the next month; no monthly snapshot-> exited."""
    valid_states = set(states)
    all_months = sorted({str(month) for month in frame["_month"].tolist()})
    month_pos = {month: index for index, month in enumerate(all_months)}
    pairs: list[dict] = []
    for _loan_id, group in frame.sort_values(["_id", "_month"], kind="mergesort").groupby("_id", sort=False):
        rows = group[["_month", "_bucket", "_balance"]].to_dict("records")
        by_month = {str(row["_month"]): row for row in rows}
        months_present = sorted(by_month.keys())
        for month in months_present:
            row = by_month[month]
            from_bucket = str(row["_bucket"])
            if from_bucket not in valid_states:
                # already validated, but guard defensively
                raise AnalysisError(f"unknown bucket in flow alignment: {from_bucket!r}")
            next_index = month_pos[month] + 1
            if next_index >= len(all_months):
                continue  # no defined next month in the panel; not an exit, just window edge
            next_month = all_months[next_index]
            if next_month in by_month:
                to_bucket = str(by_month[next_month]["_bucket"])
            else:
                to_bucket = EXITED_STATE
            pairs.append(
                {
                    "from_month": month,
                    "to_month": next_month,
                    "from_bucket": from_bucket,
                    "to_bucket": to_bucket,
                    "balance": float(row["_balance"]),
                }
            )
    return pairs


def _month_matrix(
    month_pairs: list[dict],
    states: tuple[str, ...],
    to_states: tuple[str, ...],
    bad_set: set[str],
    *,
    use_balance: bool,
) -> tuple[list[list[float]], dict[str, float], float, float]:
    from_index = {state: i for i, state in enumerate(states)}
    to_index = {state: j for j, state in enumerate(to_states)}
    n_from = len(states)
    n_to = len(to_states)
    counts = [[0.0] * n_to for _ in range(n_from)]
    base = {state: 0.0 for state in states}
    into_bad = 0.0
    out_of_bad = 0.0
    for pair in month_pairs:
        weight = pair["balance"] if use_balance else 1.0
        i = from_index[pair["from_bucket"]]
        j = to_index[pair["to_bucket"]]
        counts[i][j] += weight
        base[pair["from_bucket"]] += weight
        from_bad = pair["from_bucket"] in bad_set
        to_bad = pair["to_bucket"] in bad_set
        if not from_bad and to_bad:
            into_bad += weight
        elif from_bad and not to_bad and pair["to_bucket"] != EXITED_STATE:
            out_of_bad += weight
    matrix = [
        [(counts[i][j] / base[states[i]] if base[states[i]] else 0.0) for j in range(n_to)]
        for i in range(n_from)
    ]
    return matrix, base, into_bad, out_of_bad


def _heat_table(matrix: list[list[float]], states: tuple[str, ...], to_states: tuple[str, ...]) -> list[dict]:
    rows: list[dict] = []
    for i, from_state in enumerate(states):
        row = {"from": from_state}
        for j, to_state in enumerate(to_states):
            row[to_state] = matrix[i][j]
        rows.append(row)
    return rows


def _resolve_bad_states(
    states: tuple[str, ...], bad_states: list[str] | tuple[str, ...] | None
) -> set[str]:
    if bad_states:
        unknown = [state for state in bad_states if str(state) not in set(states)]
        if unknown:
            raise AnalysisError(f"bad_states not in states: {', '.join(str(s) for s in unknown)}")
        return {str(state) for state in bad_states}
    # default: the single worst (last) state
    return {states[-1]} if states else set()


def _resolve_window(
    months: tuple[str, ...], window: list[str] | tuple[str, ...] | None
) -> list[str]:
    if not window:
        return list(months)
    requested = [str(month) for month in window]
    return [month for month in months if month in requested]


__all__ = [
    "EXITED_STATE",
    "SPARSE_MONTH_MIN_PAIRS",
    "BucketMigrationResult",
    "FlowRateResult",
    "MonthTransition",
    "bucket_migration",
    "flow_rate",
]
