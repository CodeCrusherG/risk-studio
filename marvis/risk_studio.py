"""Risk Studio analysis for user supplied institutional risk data.

The calculations are illustrative and do not produce approved bank ratings,
regulatory capital numbers, or exchange margin requirements.
"""

from __future__ import annotations

from collections import defaultdict
from math import isfinite, sqrt
from statistics import mean

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator


router = APIRouter(prefix="/api/risk-studio", tags=["risk-studio"])


class Counterparty(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sector: str = Field(default="Corporate", max_length=80)
    assets: float = Field(ge=0)
    current_assets: float = Field(ge=0)
    current_liabilities: float = Field(ge=0)
    debt: float = Field(ge=0)
    cash: float = Field(ge=0)
    ebitda: float
    interest_expense: float = Field(ge=0)
    revenue: float = Field(ge=0)
    net_income: float
    operating_cash_flow: float
    credit_limit: float = Field(gt=0)
    collateral: float = Field(ge=0)
    previous_net_exposure: float | None = Field(default=None, ge=0)


class Position(BaseModel):
    counterparty: str = Field(min_length=1, max_length=100)
    product: str = Field(min_length=1, max_length=80)
    notional: float
    mtm: float
    daily_volatility_pct: float = Field(ge=0, le=100)
    horizon_days: int = Field(ge=1, le=365)
    returns_pct: list[float] = Field(min_length=30, max_length=1000)


class AnalysisRequest(BaseModel):
    counterparties: list[Counterparty] = Field(min_length=1, max_length=100)
    positions: list[Position] = Field(min_length=1, max_length=500)
    margin_multiplier: float = Field(default=1.25, ge=1, le=5)

    @field_validator("counterparties", "positions")
    @classmethod
    def finite_numbers(cls, items: list[Counterparty] | list[Position]):
        for item in items:
            for value in item.model_dump().values():
                if isinstance(value, (int, float)) and not isfinite(value):
                    raise ValueError("All numeric inputs must be finite")
                if isinstance(value, list) and not all(isfinite(x) for x in value):
                    raise ValueError("All historical returns must be finite")
        return items


def _quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def analyze(payload: AnalysisRequest) -> dict:
    names = {item.name for item in payload.counterparties}
    if len(names) != len(payload.counterparties):
        raise ValueError("Counterparty names must be unique")
    unknown = {p.counterparty for p in payload.positions} - names
    if unknown:
        raise ValueError(f"Positions reference unknown counterparties: {', '.join(sorted(unknown))}")
    if len({len(p.returns_pct) for p in payload.positions}) != 1:
        raise ValueError("All positions must have the same number of aligned daily returns")

    reviews = []
    for cp in payload.counterparties:
        liquidity = cp.current_assets / cp.current_liabilities if cp.current_liabilities else None
        leverage = max(cp.debt - cp.cash, 0) / cp.ebitda if cp.ebitda > 0 else None
        coverage = cp.ebitda / cp.interest_expense if cp.interest_expense else None
        margin = cp.net_income / cp.revenue if cp.revenue else None
        flags = []
        if liquidity is not None and liquidity < 1:
            flags.append("Liquidity below 1.0×")
        if leverage is None or leverage > 4:
            flags.append("Elevated net leverage")
        if coverage is not None and coverage < 2:
            flags.append("Thin interest coverage")
        if cp.operating_cash_flow < 0:
            flags.append("Negative operating cash flow")
        if cp.assets and cp.debt / cp.assets > 0.65:
            flags.append("High debt to assets")
        band = "A" if not flags else "BBB" if len(flags) == 1 else "BB" if len(flags) == 2 else "B"
        reviews.append({
            "name": cp.name, "sector": cp.sector, "indicative_band": band,
            "liquidity": liquidity, "net_debt_ebitda": leverage,
            "interest_coverage": coverage, "net_margin": margin,
            "flags": flags,
            "review": (
                f"{cp.name} has {len(flags)} monitored financial warning signal(s). "
                + ("Review " + ", ".join(flags).lower() + " before any credit decision."
                   if flags else "No threshold warnings were observed in the supplied figures.")
            ),
        })

    by_name: dict[str, list[Position]] = defaultdict(list)
    for position in payload.positions:
        by_name[position.counterparty].append(position)
    exposures = []
    for cp in payload.counterparties:
        positions = by_name[cp.name]
        gross = sum(max(p.mtm, 0) for p in positions)
        add_on = sum(
            1.96 * abs(p.notional) * p.daily_volatility_pct / 100
            * sqrt(p.horizon_days / 252)
            for p in positions
        )
        pfe = gross + add_on
        net = max(gross - cp.collateral, 0)
        stressed = max(pfe - cp.collateral, 0)
        utilization = stressed / cp.credit_limit
        movement = net - cp.previous_net_exposure if cp.previous_net_exposure is not None else None
        if utilization > 1:
            comment = "Limit breach: escalate and review collateral or exposure reduction."
        elif movement is not None and movement > cp.credit_limit * 0.1:
            comment = "Net exposure rose more than 10% of the credit limit since the previous snapshot."
        elif utilization >= 0.8:
            comment = "Watchlist: utilization is above 80% of the approved limit."
        else:
            comment = "Exposure remains within the illustrative monitoring threshold."
        exposures.append({
            "name": cp.name, "sector": cp.sector, "gross_exposure": gross,
            "collateral": cp.collateral, "net_exposure": net,
            "potential_future_exposure": pfe, "stressed_exposure": stressed,
            "credit_limit": cp.credit_limit, "utilization": utilization,
            "breach": utilization > 1,
            "previous_net_exposure": cp.previous_net_exposure,
            "day_over_day_change": movement,
            "day_over_day_comment": comment,
        })

    observations = len(payload.positions[0].returns_pct)
    daily_pnl = [
        sum(p.notional * p.returns_pct[t] / 100 for p in payload.positions)
        for t in range(observations)
    ]
    losses = [-pnl for pnl in daily_pnl]
    var_99 = max(_quantile(losses, 0.99), 0)
    tail = [loss for loss in losses if loss >= var_99]
    es_99 = max(mean(tail), var_99) if tail else var_99
    initial_margin = var_99 * payload.margin_multiplier
    # A rolling prior-window estimate avoids comparing a point with a threshold
    # that already includes that same point.
    exceptions = 0
    backtest = []
    for t in range(30, observations):
        prior_var = max(_quantile(losses[t - 30:t], 0.99), 0)
        exception = losses[t] > prior_var
        exceptions += exception
        backtest.append({"day": t + 1, "loss": losses[t], "var_99": prior_var,
                         "exception": exception})
    product_stress = []
    stress_shocks = {"Equity": -0.12, "Bonds": -0.05, "Interest Rate Swap": -0.04,
                     "CDS": -0.08, "FX": -0.07, "Equity Option": -0.15}
    for p in payload.positions:
        shock = stress_shocks.get(p.product, -0.10)
        product_stress.append({"product": p.product, "counterparty": p.counterparty,
                               "shock_pct": shock * 100,
                               "estimated_pnl": p.notional * shock})

    return {
        "source": "User supplied data",
        "methodology": {
            "credit": "Transparent threshold screen; indicative only, not an approved rating model.",
            "pfe": "Positive MTM plus 1.96 × absolute notional × daily volatility × sqrt(horizon/252).",
            "var": "99th percentile of historical one-day portfolio losses; ES averages losses at or beyond VaR.",
            "margin": "Historical VaR multiplied by the selected buffer; not ISDA SIMM or exchange margin.",
            "backtest": "Daily loss versus 99% VaR estimated from the preceding 30 observations.",
        },
        "summary": {
            "counterparties": len(payload.counterparties),
            "positions": len(payload.positions),
            "gross_exposure": sum(x["gross_exposure"] for x in exposures),
            "net_exposure": sum(x["net_exposure"] for x in exposures),
            "pfe": sum(x["potential_future_exposure"] for x in exposures),
            "breaches": sum(x["breach"] for x in exposures),
            "var_99": var_99, "expected_shortfall_99": es_99,
            "initial_margin": initial_margin,
            "backtest_exceptions": exceptions,
            "backtest_observations": len(backtest),
        },
        "credit_reviews": reviews,
        "exposures": exposures,
        "daily_pnl": daily_pnl,
        "backtest": backtest,
        "stress": product_stress,
    }


@router.post("/analyze")
def run_analysis(payload: AnalysisRequest) -> dict:
    try:
        return analyze(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
