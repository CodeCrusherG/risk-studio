"""Estimated kernel for expected loss(expected_loss_estimate).

Usebucket_migration It's...avg_matrix As a monthly barrel transfer matrix,loss_state The blogger says:
Please, let's get to the point.horizon It's absorbed in the steps.loss_state The probability of (Markov absorption chain, determination of linear algebra,
No horizontal randomity./Total expected lossesEL = balance * P(loss) * lgd.

Chain approximation:P_h = (T^h)[:, loss],of whichT as forcedloss Lines absorb the squares.exited Columns,
Reconvert the probability quality.states The blogger says:T^h Gradually multiplied by matrix (h Sub-format multiplication.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from marvis.data.performance import parse_snapshot_month, validate_performance_frame
from marvis.packs.analysis.errors import AnalysisError
from marvis.packs.analysis.flow import bucket_migration

#: Months available< Value-> short_history Red flag.
SHORT_HISTORY_MIN_MONTHS = 3


@dataclass(frozen=True)
class ChainRow:
    from_state: str
    p_to_loss: float


@dataclass(frozen=True)
class MonthEL:
    month: str
    balance: float
    expected_loss: float
    is_reference: bool = False


@dataclass(frozen=True)
class ExpectedLossResult:
    loss_state: str
    lgd: float
    horizon_months: int
    chain: list[ChainRow]
    el_by_month: list[MonthEL]
    total_el: float
    assumptions: dict
    red_flags: list[dict] = field(default_factory=list)


def expected_loss_estimate(
    df: pd.DataFrame,
    *,
    id_col: str,
    snapshot_col: str,
    bucket_col: str,
    states: list[str] | tuple[str, ...],
    balance_col: str,
    loss_state: str | None = None,
    lgd: float = 0.6,
    horizon_months: int = 12,
    window: list[str] | tuple[str, ...] | None = None,
) -> ExpectedLossResult:
    if horizon_months < 1:
        raise AnalysisError("horizon_months Must be positive")
    contract = validate_performance_frame(
        df,
        id_col=id_col,
        snapshot_col=snapshot_col,
        bucket_col=bucket_col,
        states=states,
        balance_col=balance_col,
    )
    state_order = tuple(str(state) for state in states)
    resolved_loss = str(loss_state) if loss_state else state_order[-1]
    if resolved_loss not in state_order:
        raise AnalysisError(f"loss_state {resolved_loss!r} No, I'm not.states Internal")

    migration = bucket_migration(
        df,
        id_col=id_col,
        snapshot_col=snapshot_col,
        bucket_col=bucket_col,
        states=state_order,
        balance_col=None,  # transition probabilities are count-based, not balance-weighted
        window=window,
    )

    transition, was_absorbing = _absorbing_transition(migration.avg_matrix, state_order, resolved_loss)
    powered = _matrix_power(transition, horizon_months)
    loss_index = state_order.index(resolved_loss)
    chain = [
        ChainRow(from_state=state, p_to_loss=float(powered[i][loss_index]))
        for i, state in enumerate(state_order)
    ]
    p_to_loss = {row.from_state: row.p_to_loss for row in chain}

    el_by_month, total_el, months_available, reference_month = _el_by_month(
        df, contract, state_order, p_to_loss, lgd=lgd
    )

    red_flags: list[dict] = []
    if not was_absorbing:
        red_flags.append(
            {
                "kind": "matrix_not_absorbing",
                "loss_state": resolved_loss,
                "message": (
                    f"Loss pattern`{resolved_loss}` (a) Not a absorption state in observing migration matrices (with a probability of migration);"
                    "Forced by absorption (line self-ring)=1)The results are estimated to be conservative."
                ),
            }
        )
    if months_available < SHORT_HISTORY_MIN_MONTHS:
        red_flags.append(
            {
                "kind": "short_history",
                "months_available": months_available,
                "message": f"Quick-Size Moon Only{months_available} Number of<{SHORT_HISTORY_MIN_MONTHS}),The migration matrix is not well estimated.",
            }
        )

    assumptions = {
        "lgd": float(lgd),
        "horizon_months": int(horizon_months),
        "matrix_window": list(migration.window_months),
        "loss_state": resolved_loss,
        # total_el is a point-in-time EL of the reference snapshot (latest month),
        # NOT a cross-month sum; these keys document thatcaliberto gate/xlsx/renderer.
        "total_el_basis": "reference_snapshot",
        "reference_snapshot": reference_month,
    }
    return ExpectedLossResult(
        loss_state=resolved_loss,
        lgd=float(lgd),
        horizon_months=int(horizon_months),
        chain=chain,
        el_by_month=el_by_month,
        total_el=float(total_el),
        assumptions=assumptions,
        red_flags=red_flags,
    )


def _absorbing_transition(
    avg_matrix: list[list[float]], states: tuple[str, ...], loss_state: str
) -> tuple[np.ndarray, bool]:
    """- Put it on.avg_matrix (NxM, M=N+1 Hamexited) ShrinkNxN Quarter and Forceloss Lines absorb.

    - Drop it.exited Columns, re-integrate the probability mass for each rowstates Internal (lines and tables)=1);
    - loss Line Force asone-hot Self-ring (absorption mode).
    Back(Square, loss Is the state almost absorbed?).
    """
    n = len(states)
    square = np.zeros((n, n), dtype=float)
    for i in range(n):
        row = np.asarray(avg_matrix[i][:n], dtype=float)  # drop exited (last) column
        total = float(row.sum())
        if total > 0:
            square[i] = row / total
        else:
            square[i, i] = 1.0  # no observed transitions -> treat as self-absorbing
    loss_index = states.index(loss_state)
    # detect whether loss row was already (near-)absorbing before we force it
    was_absorbing = bool(square[loss_index, loss_index] >= 1.0 - 1e-9)
    square[loss_index] = 0.0
    square[loss_index, loss_index] = 1.0
    return square, was_absorbing


def _matrix_power(matrix: np.ndarray, power: int) -> np.ndarray:
    result = np.eye(matrix.shape[0], dtype=float)
    for _ in range(power):
        result = result @ matrix
    return result


def _el_by_month(
    df: pd.DataFrame,
    contract,
    states: tuple[str, ...],
    p_to_loss: dict[str, float],
    *,
    lgd: float,
) -> tuple[list[MonthEL], float, int, str | None]:
    """Per-month point-in-time EL rows + a reference-snapshot headline total_el.

    Each MonthEL row is a self-contained point-in-time EL for that snapshot month.
    `total_el` is NOT the cross-month sum (that double-counts the same loans once
    per snapshot they appear in, inflating ~N× on an N-month panel); it is the EL
    of the reference snapshot (default = latest month present in the frame). The
    reference row carries is_reference=True. Returns
    (rows, total_el, months_available, reference_month).
    """
    frame = df[[contract.snapshot_col, contract.bucket_col, contract.balance_col]].copy()
    frame["_month"] = frame[contract.snapshot_col].map(parse_snapshot_month)
    frame["_bucket"] = frame[contract.bucket_col].astype(str)
    frame["_balance"] = pd.to_numeric(frame[contract.balance_col], errors="coerce").fillna(0.0).astype(float)
    frame = frame[frame["_month"].notna()]
    months = sorted({str(month) for month in frame["_month"].tolist()})
    reference_month = months[-1] if months else None
    rows: list[MonthEL] = []
    for month in months:
        month_frame = frame[frame["_month"] == month]
        balance = float(month_frame["_balance"].sum())
        el = 0.0
        for bucket, group in month_frame.groupby("_bucket", sort=False):
            probability = p_to_loss.get(str(bucket), 0.0)
            el += float(group["_balance"].sum()) * probability * float(lgd)
        rows.append(
            MonthEL(
                month=month,
                balance=balance,
                expected_loss=el,
                is_reference=(month == reference_month),
            )
        )
    total_el = next(
        (row.expected_loss for row in rows if row.month == reference_month), 0.0
    )
    return rows, total_el, len(months), reference_month


__all__ = [
    "SHORT_HISTORY_MIN_MONTHS",
    "ChainRow",
    "ExpectedLossResult",
    "MonthEL",
    "expected_loss_estimate",
]
