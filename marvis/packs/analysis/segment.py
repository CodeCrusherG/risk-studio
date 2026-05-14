"""Disaggregat image kernel(segment_profile).

Presssegment_col Group statistics/Percentage/Approval rate/Bad rate/Average/Net profit and give concentration
(top1/top5/HHI) And the red flag(high_concentration / sparse_segment & Add "Other").

Profit Row Reusestrategy Packageprofit kernel equation, but locally (not cross-contracting)import)——
The formula is simple. The two packages are locked in the same hand-held values. Comment points to each other.(strategy/profit.py profit_calc).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math

import pandas as pd

from marvis.packs.analysis.errors import AnalysisError

#: top_k A small breakdown outside is grouped to the label.
OTHER_SEGMENT = "Other"
#: top1 Ratio above this threshold-> high_concentration Red flag.
HIGH_CONCENTRATION_TOP1 = 0.40
#: HHI Beyond this threshold-> high_concentration Red flag.
HIGH_CONCENTRATION_HHI = 0.25


@dataclass(frozen=True)
class SegmentRow:
    segment: str
    count: int
    pop_pct: float
    approval_rate: float | None
    bad_rate: float | None
    avg_score: float | None
    net_profit: float | None


@dataclass(frozen=True)
class Concentration:
    top1_pct: float
    top5_pct: float
    hhi: float


@dataclass(frozen=True)
class SegmentProfileResult:
    segments: list[SegmentRow]
    concentration: Concentration
    red_flags: list[dict] = field(default_factory=list)
    concentration_basis: str = "count"
    ead_concentration: Concentration | None = None
    ead_concentration_basis: str | None = None


@dataclass(frozen=True)
class ProfitParams:
    """Local profit parameters (andstrategy.profit.ProfitParams Same field/is the formula."""

    annual_rate: float
    funding_rate: float
    lgd: float
    operating_cost_per_loan: float
    term_months: int


def segment_profile(
    df: pd.DataFrame,
    *,
    segment_col: str,
    target_col: str | None = None,
    score_col: str | None = None,
    approved_col: str | None = None,
    profit_params: ProfitParams | None = None,
    ead_col: str | None = None,
    pd_col: str | None = None,
    top_k: int = 20,
) -> SegmentProfileResult:
    required = [segment_col]
    for optional in (target_col, score_col, approved_col, ead_col, pd_col):
        if optional:
            required.append(optional)
    missing = [column for column in dict.fromkeys(required) if column not in df.columns]
    if missing:
        raise AnalysisError(f"segment_profile Missing columns:{', '.join(missing)}")

    total = int(len(df))
    if total == 0:
        raise AnalysisError("segment_profile: Empty data set")

    # concentration is computed over the *full* segment cardinality (before Group),
    # so The fact that the rest of the world is not covered up by the fact that the rest of the world is not the only one that is not.
    raw_counts = df[segment_col].astype(str).value_counts()
    concentration = _concentration(raw_counts, total)
    ead_concentration = None
    ead_concentration_basis = None
    if ead_col:
        ead = pd.to_numeric(df[ead_col], errors="coerce")
        if ead.isna().any() or any(not math.isfinite(float(value)) for value in ead):
            raise AnalysisError(f"segment_profile: EAD Columns`{ead_col}` Includes non-limited or non-values.")
        if (ead < 0).any():
            raise AnalysisError(f"segment_profile: EAD Columns`{ead_col}` Can't be negative.")
        total_ead = float(ead.sum())
        if total_ead <= 0:
            raise AnalysisError(f"segment_profile: EAD Columns`{ead_col}` The sum must be greater than zero.")
        ead_by_segment = (
            pd.DataFrame({"segment": df[segment_col].astype(str), "ead": ead})
            .groupby("segment", sort=False)["ead"]
            .sum()
            .sort_values(ascending=False)
        )
        ead_concentration = _concentration(ead_by_segment, total_ead)
        ead_concentration_basis = "ead"

    ranked_segments = list(raw_counts.index)
    kept = ranked_segments[:top_k]
    merged = set(ranked_segments[top_k:])

    rows: list[SegmentRow] = []
    grouped: dict[str, pd.DataFrame] = {}
    for segment in kept:
        grouped[segment] = df[df[segment_col].astype(str) == segment]
    if merged:
        grouped[OTHER_SEGMENT] = df[df[segment_col].astype(str).isin(merged)]

    for segment, group in grouped.items():
        rows.append(
            _segment_row(
                segment,
                group,
                total=total,
                target_col=target_col,
                score_col=score_col,
                approved_col=approved_col,
                profit_params=profit_params,
                ead_col=ead_col,
                pd_col=pd_col,
            )
        )

    red_flags: list[dict] = []
    if concentration.top1_pct > HIGH_CONCENTRATION_TOP1 or concentration.hhi > HIGH_CONCENTRATION_HHI:
        red_flags.append(
            {
                "kind": "high_concentration",
                "top1_pct": concentration.top1_pct,
                "hhi": concentration.hhi,
                "message": (
                    f"Subdivided with high concentration:top1 Percentage{concentration.top1_pct:.1%},HHI {concentration.hhi:.3f}"
                    f"(Thresholdtop1>{HIGH_CONCENTRATION_TOP1:.0%} orHHI>{HIGH_CONCENTRATION_HHI})."
                ),
            }
        )
    if merged:
        red_flags.append(
            {
                "kind": "sparse_segment",
                "merged_count": len(merged),
                "message": f"{len(merged)} The small subdivision has been added to the{OTHER_SEGMENT}](top_k={top_k}).",
            }
        )

    return SegmentProfileResult(
        segments=rows,
        concentration=concentration,
        concentration_basis="count",
        ead_concentration=ead_concentration,
        ead_concentration_basis=ead_concentration_basis,
        red_flags=red_flags,
    )


def _segment_row(
    segment: str,
    group: pd.DataFrame,
    *,
    total: int,
    target_col: str | None,
    score_col: str | None,
    approved_col: str | None,
    profit_params: ProfitParams | None,
    ead_col: str | None,
    pd_col: str | None,
) -> SegmentRow:
    count = int(len(group))
    pop_pct = count / total if total else 0.0
    approval_rate = None
    if approved_col:
        approved = pd.to_numeric(group[approved_col], errors="coerce")
        approval_rate = float(approved.mean()) if count else None
    bad_rate = None
    if target_col:
        target = pd.to_numeric(group[target_col], errors="coerce")
        valid = target.dropna()
        bad_rate = float(valid.mean()) if len(valid) else None
    avg_score = None
    if score_col:
        score = pd.to_numeric(group[score_col], errors="coerce")
        valid = score.dropna()
        avg_score = float(valid.mean()) if len(valid) else None
    net_profit = None
    if profit_params is not None and ead_col and pd_col:
        net_profit = _net_profit(group, profit_params, ead_col=ead_col, pd_col=pd_col)
    return SegmentRow(
        segment=str(segment),
        count=count,
        pop_pct=pop_pct,
        approval_rate=approval_rate,
        bad_rate=bad_rate,
        avg_score=avg_score,
        net_profit=net_profit,
    )


def _net_profit(group: pd.DataFrame, params: ProfitParams, *, ead_col: str, pd_col: str) -> float:
    """Local net profit formula, word for word.strategy/profit.py::_profit_result.

    net = revenue - expected_loss - funding_cost - operating_cost,of which
    revenue = sum(ead * annual_rate * term/12), expected_loss = sum(ead * pd * lgd),
    funding_cost = sum(ead * funding_rate * term/12), operating_cost = n * op_cost.
    """
    ead = pd.to_numeric(group[ead_col], errors="coerce").fillna(0.0).astype(float)
    pd_values = pd.to_numeric(group[pd_col], errors="coerce").fillna(0.0).astype(float)
    term_factor = float(params.term_months) / 12.0
    revenue = float((ead * float(params.annual_rate) * term_factor).sum())
    expected_loss = float((ead * pd_values * float(params.lgd)).sum())
    funding_cost = float((ead * float(params.funding_rate) * term_factor).sum())
    operating_cost = float(len(group) * float(params.operating_cost_per_loan))
    return revenue - expected_loss - funding_cost - operating_cost


def _concentration(weights: pd.Series, total: float) -> Concentration:
    shares = [float(value) / total for value in weights.tolist()] if total else []
    top1 = shares[0] if shares else 0.0
    top5 = float(sum(shares[:5]))
    hhi = float(sum(share * share for share in shares))
    return Concentration(top1_pct=float(top1), top5_pct=top5, hhi=hhi)


__all__ = [
    "HIGH_CONCENTRATION_HHI",
    "HIGH_CONCENTRATION_TOP1",
    "OTHER_SEGMENT",
    "Concentration",
    "ProfitParams",
    "SegmentProfileResult",
    "SegmentRow",
    "segment_profile",
]
