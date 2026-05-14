"""Pure deterministic calculations for the risk-analysis deliverable.

The pack tool owns dataset access and artifact persistence.  This module accepts an
already-loaded frame plus an explicit canonical-to-source column map, validates every
business input, and returns a JSON-safe calculation payload.  The Excel renderer only
formats this payload; it never recomputes a financial metric.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import math
from typing import Any

import pandas as pd


ANALYSIS_KINDS = frozenset({"vtg_terminal", "profitability"})
WEIGHT_SUM_TOLERANCE = 1e-4
PROFIT_RATE_RECONCILIATION_TOLERANCE = 1e-4
PRODUCT_SCOPE_LIMIT = 8
PRODUCT_SCOPE_ITEM_MAX_CHARS = 80
AS_OF_PERIOD_MAX_CHARS = 40
SCENARIO_MAX_CHARS = 40

_VTG_REQUIRED = (
    "product",
    "cohort",
    "as_of_date",
    "amount_unit",
    "disbursement_amount",
    "mob14_bad_rate",
)
_VTG_CURVE_REQUIRED = ("mob", "mob_days", "day_count_basis")
_VTG_CURVE_BALANCE_FIELDS = ("mob_balance_rate", "mob_balance_amount")
_VTG_CURVE_DAY_TOLERANCE = 1e-6
_VTG_BALANCE_RECONCILIATION_REL_TOLERANCE = 1e-4
_VTG_BALANCE_RECONCILIATION_ABS_TOLERANCE = 0.01
_VTG_RECOVERY_RECONCILIATION_TOLERANCE = 1e-4
_VTG_ANNUALIZED_RECONCILIATION_TOLERANCE = 1e-4
_VTG_OPTIONAL_RATES = (
    "terminal_bad_rate",
    "long_term_recovery_rate",
    "auxiliary_terminal_bad_rate",
    "previous_mob14_bad_rate",
    "previous_terminal_bad_rate",
    "previous_annualized_bad_rate",
)
_VTG_OPTIONAL_NONNEGATIVE = (
    "avg_daily_balance",
    "previous_disbursement_amount",
    "previous_avg_daily_balance",
)
_VTG_OPTIONAL_GROUP_TEXT = (
    "scenario",
    "channel",
    "selection_rule",
)

_PROFIT_REQUIRED = (
    "product",
    "as_of_period",
    "asset_class",
    "weight",
    "weight_basis",
    "customer_rate",
)
_PROFIT_COST_FIELDS = (
    "interest_loss_rate",
    "revenue_share_rate",
    "risk_cost_rate",
    "acquisition_cost_rate",
    "data_cost_rate",
    "payment_cost_rate",
    "collection_cost_rate",
    "funding_cost_rate",
    "other_cost_rate",
    "tax_rate",
)
_PROFIT_ALWAYS_EXPLICIT_COST_FIELDS = (
    "acquisition_cost_rate",
    "payment_cost_rate",
    "collection_cost_rate",
    "funding_cost_rate",
    "other_cost_rate",
)
_PROFIT_REQUIRED = (*_PROFIT_REQUIRED, *_PROFIT_ALWAYS_EXPLICIT_COST_FIELDS)
_PROFIT_DERIVABLE_COST_FIELDS = (
    "risk_cost_rate",
    "interest_loss_rate",
    "revenue_share_rate",
    "data_cost_rate",
    "tax_rate",
)
_PROFIT_DRIVER_FIELDS = (
    "amount_unit",
    "terminal_vintage_rate",
    "risk_turnover",
    "loss_timing_factor",
    "profit_share_ratio",
    "per_application_cost",
    "credit_approval_rate",
    "draw_initiation_rate",
    "draw_approval_rate",
    "average_ticket",
    "data_annualization_factor",
    "tax_method",
    "tax_inclusive_divisor",
    "tax_combined_rate",
)

_COST_LABELS = {
    "interest_loss_rate": "Loss of interest",
    "revenue_share_rate": "Earning costs",
    "risk_cost_rate": "Risk cost",
    "acquisition_cost_rate": "Cost of clients",
    "data_cost_rate": "Data cost",
    "payment_cost_rate": "Cost payment",
    "collection_cost_rate": "Cost recovery",
    "funding_cost_rate": "Cost of funds",
    "other_cost_rate": "Other costs",
    "tax_rate": "Taxes and charges",
}


class RiskAnalysisError(ValueError):
    """Typed, user-readable invalid-input error for the pack boundary."""

    def __init__(
        self,
        message: str,
        *,
        analysis_kind: str | None = None,
        field: str | None = None,
        row_number: int | None = None,
    ) -> None:
        self.analysis_kind = analysis_kind
        self.field = field
        self.row_number = row_number
        super().__init__(message)

    def to_detail(self) -> dict[str, Any]:
        return {
            "kind": "risk_analysis_invalid",
            "analysis_kind": self.analysis_kind,
            "field": self.field,
            "row_number": self.row_number,
            "message": str(self),
        }


@dataclass(frozen=True)
class RiskAnalysisCalculation:
    analysis_kind: str
    column_map: dict[str, str]
    product_scope: list[str]
    as_of_period: str
    headline_metrics: dict[str, Any]
    key_points: list[str]
    red_flags: list[str]
    assumptions: list[str]
    source_row_count: int
    row_count: int
    detail_rows: list[dict[str, Any]]
    summary_rows: list[dict[str, Any]]
    formula_definitions: list[dict[str, str]]
    data_quality: list[dict[str, str]]


def calculate_risk_analysis(
    frame: pd.DataFrame,
    *,
    analysis_kind: str,
    column_map: dict[str, str],
) -> RiskAnalysisCalculation:
    kind = str(analysis_kind or "").strip()
    if kind == "vtg_terminal":
        return calculate_vtg_terminal(frame, column_map=column_map)
    if kind == "profitability":
        return calculate_profitability(frame, column_map=column_map)
    raise RiskAnalysisError(
        f"Type of risk analysis not supported: {analysis_kind!r}",
        analysis_kind=kind or None,
    )


def calculate_vtg_terminal(
    frame: pd.DataFrame,
    *,
    column_map: dict[str, str],
) -> RiskAnalysisCalculation:
    kind = "vtg_terminal"
    data = _normalized_frame(frame, analysis_kind=kind)
    source_row_count = len(data)
    mapping = _normalize_column_map(data, column_map, analysis_kind=kind)
    _require_mappings(mapping, _VTG_REQUIRED, analysis_kind=kind)
    curve_derived_count = 0
    zero_disbursement_skipped_count = 0
    working_mapping = mapping
    if "turnover" not in mapping:
        _require_mappings(mapping, _VTG_CURVE_REQUIRED, analysis_kind=kind)
        if not any(field in mapping for field in _VTG_CURVE_BALANCE_FIELDS):
            raise RiskAnalysisError(
                "VTG Metrics are missingturnover The blog is also available.column_map At least."
                "mob_balance_rate ormob_balance_amount.",
                analysis_kind=kind,
                field="mob_balance_rate",
            )
        data, working_mapping, zero_disbursement_skipped_count = (
            _collapse_vtg_balance_curves(
                data,
                mapping=mapping,
                analysis_kind=kind,
            )
        )
        curve_derived_count = len(data)
    else:
        keep_positions: list[int] = []
        for position, row in data.iterrows():
            disbursement = _number(
                row,
                mapping,
                "disbursement_amount",
                kind,
                position + 1,
                required=True,
                minimum=0.0,
            )
            if disbursement == 0.0:
                zero_disbursement_skipped_count += 1
            else:
                keep_positions.append(position)
        data = data.loc[keep_positions].reset_index(drop=True)
    if data.empty:
        raise RiskAnalysisError(
            "VTG There are no positive value lines for the measurement of the amount of the loan; zero loans do not participate in the calculation.",
            analysis_kind=kind,
            field="disbursement_amount",
        )
    has_explicit_mob_auxiliary_method = (
        "terminal_method" in mapping and "auxiliary_terminal_bad_rate" in mapping
    )
    if (
        "terminal_bad_rate" not in mapping
        and "long_term_recovery_rate" not in mapping
        and not has_explicit_mob_auxiliary_method
    ):
        raise RiskAnalysisError(
            "VTG Final measurement at leastterminal_bad_rate,long_term_recovery_rate,"
            "orterminal_method=min_mob14_auxiliary with the auxiliary end.",
            analysis_kind=kind,
            field="terminal_bad_rate",
        )

    detail_rows: list[dict[str, Any]] = []
    substitution_count = 0
    auxiliary_min_count = 0
    derived_balance_count = 0
    terminal_above_mob_count = 0
    annualized_over_one_count = 0
    zero_mob_count = 0
    partial_previous_count = 0
    declared_terminal_methods: list[str] = []
    direct_recovery_reconciled_count = 0
    direct_auxiliary_ignored_count = 0
    explicit_mob_auxiliary_min_count = 0
    derived_previous_turnover_count = 0
    derived_previous_annualized_count = 0

    for position, row in data.iterrows():
        row_number = position + 1
        product = _required_text(row, working_mapping, "product", kind, row_number)
        cohort = _required_text(row, working_mapping, "cohort", kind, row_number)
        as_of_date = _required_text(
            row, working_mapping, "as_of_date", kind, row_number
        )
        amount_unit = _required_text(
            row, working_mapping, "amount_unit", kind, row_number
        )
        scenario = _optional_text(row, working_mapping, "scenario")
        channel = _optional_text(row, working_mapping, "channel")
        selection_rule = _optional_text(row, working_mapping, "selection_rule")
        tenor_months = _number(
            row,
            working_mapping,
            "tenor_months",
            kind,
            row_number,
            minimum=0.0,
            minimum_inclusive=False,
        )
        day_count_basis = _number(
            row,
            working_mapping,
            "day_count_basis",
            kind,
            row_number,
            minimum=0.0,
            minimum_inclusive=False,
        )
        mob_balance_source = _optional_text(row, working_mapping, "mob_balance_source")
        disbursement = _number(
            row,
            working_mapping,
            "disbursement_amount",
            kind,
            row_number,
            required=True,
            minimum=0.0,
            minimum_inclusive=False,
        )
        mob14 = _number(
            row,
            working_mapping,
            "mob14_bad_rate",
            kind,
            row_number,
            required=True,
            rate=True,
        )
        turnover = _number(
            row,
            working_mapping,
            "turnover",
            kind,
            row_number,
            required=True,
            minimum=0.0,
            minimum_inclusive=False,
        )
        direct_terminal = _number(
            row, working_mapping, "terminal_bad_rate", kind, row_number, rate=True
        )
        recovery_input = _number(
            row,
            working_mapping,
            "long_term_recovery_rate",
            kind,
            row_number,
            rate=True,
        )
        auxiliary_terminal = _number(
            row,
            working_mapping,
            "auxiliary_terminal_bad_rate",
            kind,
            row_number,
            rate=True,
        )
        terminal_method = _optional_text(row, working_mapping, "terminal_method")
        if terminal_method is not None:
            declared_terminal_methods.append(terminal_method)
        avg_daily_balance = _number(
            row,
            working_mapping,
            "avg_daily_balance",
            kind,
            row_number,
            minimum=0.0,
        )
        previous_mob14 = _number(
            row,
            working_mapping,
            "previous_mob14_bad_rate",
            kind,
            row_number,
            rate=True,
        )
        previous_terminal = _number(
            row,
            working_mapping,
            "previous_terminal_bad_rate",
            kind,
            row_number,
            rate=True,
        )
        previous_turnover = _number(
            row,
            working_mapping,
            "previous_turnover",
            kind,
            row_number,
            minimum=0.0,
            minimum_inclusive=False,
        )
        previous_annualized = _number(
            row,
            working_mapping,
            "previous_annualized_bad_rate",
            kind,
            row_number,
            minimum=0.0,
        )
        previous_disbursement = _number(
            row,
            working_mapping,
            "previous_disbursement_amount",
            kind,
            row_number,
            minimum=0.0,
        )
        previous_avg_balance = _number(
            row,
            working_mapping,
            "previous_avg_daily_balance",
            kind,
            row_number,
            minimum=0.0,
        )
        previous_turnover_source = "direct" if previous_turnover is not None else None
        if previous_disbursement is not None and previous_avg_balance is not None:
            if previous_avg_balance <= 0.0:
                raise RiskAnalysisError(
                    f"I'm sorry.{row_number} Lines Use Prior Period Amounts/The average daily balance is used to extrapolate the turnover."
                    "previous_avg_daily_balance Must be greater than zero.",
                    analysis_kind=kind,
                    field="previous_avg_daily_balance",
                    row_number=row_number,
                )
            if previous_disbursement <= 0.0:
                raise RiskAnalysisError(
                    f"I'm sorry.{row_number} Lines Use Prior Period Amounts/The average daily balance is used to extrapolate the turnover."
                    "previous_disbursement_amount Must be greater than zero.",
                    analysis_kind=kind,
                    field="previous_disbursement_amount",
                    row_number=row_number,
                )
            if previous_turnover is None:
                previous_turnover = previous_disbursement / previous_avg_balance
                previous_turnover_source = "derived_from_amount_balance"
                derived_previous_turnover_count += 1
            else:
                implied_previous_avg_balance = previous_disbursement / previous_turnover
                if not math.isclose(
                    previous_avg_balance,
                    implied_previous_avg_balance,
                    rel_tol=_VTG_BALANCE_RECONCILIATION_REL_TOLERANCE,
                    abs_tol=_VTG_BALANCE_RECONCILIATION_ABS_TOLERANCE,
                ):
                    raise RiskAnalysisError(
                        f"I'm sorry.{row_number} Okay.previous_turnover={previous_turnover} "
                        "andprevious_disbursement_amount/previous_avg_daily_balance "
                        "The calibre is not consistent.",
                        analysis_kind=kind,
                        field="previous_turnover",
                        row_number=row_number,
                    )

        implied_avg_daily_balance = disbursement / turnover
        if avg_daily_balance is not None and not math.isclose(
            avg_daily_balance,
            implied_avg_daily_balance,
            rel_tol=_VTG_BALANCE_RECONCILIATION_REL_TOLERANCE,
            abs_tol=_VTG_BALANCE_RECONCILIATION_ABS_TOLERANCE,
        ):
            raise RiskAnalysisError(
                f"I'm sorry.{row_number} Okay.avg_daily_balance={avg_daily_balance} and"
                f"Amount released/Number of turnovers={implied_avg_daily_balance} inconsistent;relatively different"
                f"{_VTG_BALANCE_RECONCILIATION_REL_TOLERANCE:g}.",
                analysis_kind=kind,
                field="avg_daily_balance",
                row_number=row_number,
            )

        if terminal_method == "min_mob14_auxiliary" and recovery_input is not None:
            raise RiskAnalysisError(
                f"I'm sorry.{row_number} Okay.terminal_method=min_mob14_auxiliary and"
                "long_term_recovery_rate It can't be provided at the same time.",
                analysis_kind=kind,
                field="long_term_recovery_rate",
                row_number=row_number,
            )
        if terminal_method == "min_mob14_auxiliary" and direct_terminal is not None:
            raise RiskAnalysisError(
                f"I'm sorry.{row_number} Okay.terminal_method=min_mob14_auxiliary and"
                "terminal_bad_rate It can't be provided at the same time.",
                analysis_kind=kind,
                field="terminal_bad_rate",
                row_number=row_number,
            )

        if direct_terminal is not None:
            terminal = direct_terminal
            terminal_source = "direct"
            if recovery_input is not None and mob14 > 0.0:
                direct_realized_recovery = (mob14 - direct_terminal) / mob14
                if not math.isclose(
                    recovery_input,
                    direct_realized_recovery,
                    rel_tol=0.0,
                    abs_tol=_VTG_RECOVERY_RECONCILIATION_TOLERANCE,
                ):
                    raise RiskAnalysisError(
                        f"I'm sorry.{row_number} Okay.long_term_recovery_rate={recovery_input} "
                        f"Rate of recovery achieved in relation to direct end value={direct_realized_recovery} Inconsistencies;"
                        f"Absolutely bad tolerance{_VTG_RECOVERY_RECONCILIATION_TOLERANCE:g}.",
                        analysis_kind=kind,
                        field="long_term_recovery_rate",
                        row_number=row_number,
                    )
                direct_recovery_reconciled_count += 1
            if auxiliary_terminal is not None:
                direct_auxiliary_ignored_count += 1
        else:
            if terminal_method == "min_mob14_auxiliary":
                if auxiliary_terminal is None:
                    raise RiskAnalysisError(
                        f"I'm sorry.{row_number} Okay.terminal_method=min_mob14_auxiliary "
                        "Timeauxiliary_terminal_bad_rate Can't be empty.",
                        analysis_kind=kind,
                        field="auxiliary_terminal_bad_rate",
                        row_number=row_number,
                    )
                terminal = min(mob14, auxiliary_terminal)
                terminal_source = "min(mob14,auxiliary)"
                explicit_mob_auxiliary_min_count += 1
            elif recovery_input is None:
                raise RiskAnalysisError(
                    f"I'm sorry.{row_number} Okay.terminal_bad_rate Missing and not availablelong_term_recovery_rate.",
                    analysis_kind=kind,
                    field="terminal_bad_rate",
                    row_number=row_number,
                )
            else:
                derived_terminal = mob14 * (1.0 - recovery_input)
                substitution_count += 1
                if auxiliary_terminal is not None:
                    if selection_rule != "min_auxiliary_recovery":
                        raise RiskAnalysisError(
                            f"I'm sorry.{row_number} Lines are available at the same timelong_term_recovery_rate and"
                            "auxiliary_terminal_bad_rate , the & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & &"
                            "selection_rule=min_auxiliary_recovery.",
                            analysis_kind=kind,
                            field="selection_rule",
                            row_number=row_number,
                        )
                    terminal = min(derived_terminal, auxiliary_terminal)
                    terminal_source = "min(auxiliary,recovery_derived)"
                    auxiliary_min_count += 1
                else:
                    terminal = derived_terminal
                    terminal_source = "recovery_derived"

        if avg_daily_balance is None:
            avg_daily_balance = implied_avg_daily_balance
            derived_balance_count += 1

        annualized = terminal * turnover
        observed_annualized = mob14 * turnover
        if mob14 == 0.0:
            realized_recovery = None
            zero_mob_count += 1
        else:
            realized_recovery = (mob14 - terminal) / mob14
        if terminal > mob14:
            terminal_above_mob_count += 1
        if annualized > 1.0 or observed_annualized > 1.0:
            annualized_over_one_count += 1

        previous_annualized_source = (
            "direct" if previous_annualized is not None else None
        )
        if previous_terminal is not None and previous_turnover is not None:
            implied_previous_annualized = previous_terminal * previous_turnover
            if previous_annualized is None:
                previous_annualized = implied_previous_annualized
                previous_annualized_source = "derived_from_terminal_turnover"
                derived_previous_annualized_count += 1
            elif not math.isclose(
                previous_annualized,
                implied_previous_annualized,
                rel_tol=0.0,
                abs_tol=_VTG_ANNUALIZED_RECONCILIATION_TOLERANCE,
            ):
                raise RiskAnalysisError(
                    f"I'm sorry.{row_number} Okay.previous_annualized_bad_rate="
                    f"{previous_annualized} andprevious_terminal_bad_rate × "
                    f"previous_turnover={implied_previous_annualized} Inconsistencies;"
                    f"Absolutely bad tolerance{_VTG_ANNUALIZED_RECONCILIATION_TOLERANCE:g}.",
                    analysis_kind=kind,
                    field="previous_annualized_bad_rate",
                    row_number=row_number,
                )
        if previous_annualized is not None and previous_annualized > 1.0:
            annualized_over_one_count += 1
        previous_fields_present = sum(
            value is not None
            for value in (
                previous_mob14,
                previous_terminal,
                previous_turnover,
                previous_annualized,
                previous_disbursement,
                previous_avg_balance,
            )
        )
        if previous_fields_present and previous_annualized is None:
            partial_previous_count += 1
        annualized_change = (
            annualized - previous_annualized
            if previous_annualized is not None
            else None
        )

        detail_rows.append(
            {
                "product": product,
                "cohort": cohort,
                "as_of_date": as_of_date,
                "amount_unit": amount_unit,
                "scenario": scenario,
                "channel": channel,
                "tenor_months": tenor_months,
                "selection_rule": selection_rule,
                "day_count_basis": day_count_basis,
                "mob_balance_source": mob_balance_source,
                "disbursement_amount": disbursement,
                "mob14_bad_rate": mob14,
                "terminal_bad_rate": terminal,
                "terminal_bad_rate_source": terminal_source,
                "terminal_method": terminal_method,
                "auxiliary_terminal_bad_rate": auxiliary_terminal,
                "turnover": turnover,
                "avg_daily_balance": avg_daily_balance,
                "observed_annualized_bad_rate": observed_annualized,
                "annualized_bad_rate": annualized,
                "long_term_recovery_rate": realized_recovery,
                "supplied_long_term_recovery_rate": recovery_input,
                "realized_long_term_recovery_rate": realized_recovery,
                "previous_mob14_bad_rate": previous_mob14,
                "previous_terminal_bad_rate": previous_terminal,
                "previous_turnover": previous_turnover,
                "previous_turnover_source": previous_turnover_source,
                "previous_annualized_bad_rate": previous_annualized,
                "previous_annualized_bad_rate_source": previous_annualized_source,
                "previous_disbursement_amount": previous_disbursement,
                "previous_avg_daily_balance": previous_avg_balance,
                "annualized_bad_rate_change": annualized_change,
            }
        )

    seen_vtg_slices: set[tuple[Any, ...]] = set()
    for row in detail_rows:
        slice_key = (
            row["product"],
            row["cohort"],
            row["as_of_date"],
            row.get("scenario") or "Benchmark",
            row.get("channel") or "Not provided",
            row.get("tenor_months"),
        )
        if slice_key in seen_vtg_slices:
            raise RiskAnalysisError(
                "VTG The aggregate particle size must be the only one.product × cohort × as_of_date × "
                "scenario × channel × tenor_months;Repetition of business slices detected"
                f"{slice_key!r}.The different end-of-life method is cross-diameter, not a composite summary that can be added.",
                analysis_kind=kind,
                field="cohort",
            )
        seen_vtg_slices.add(slice_key)

    amount_units = _ordered_unique(row["amount_unit"] for row in detail_rows)
    if len(amount_units) != 1:
        raise RiskAnalysisError(
            "VTG Combination summary requirementsamount_unit The table is consistent and actually:"
            + ",".join(amount_units)
            + ".",
            analysis_kind=kind,
            field="amount_unit",
        )
    scenario_scope = _ordered_unique(
        row.get("scenario") or "Benchmark" for row in detail_rows
    )
    if len(scenario_scope) > 1:
        raise RiskAnalysisError(
            "VTG Single combination reports do not allow multiple blendsscenario,The alternative scenario is not counted in the group;"
            "Please generate reports by scene.",
            analysis_kind=kind,
            field="scenario",
        )
    as_of_date_scope = _ordered_unique(row["as_of_date"] for row in detail_rows)
    if len(as_of_date_scope) > 1:
        raise RiskAnalysisError(
            "VTG Single combination reports do not allow multiple blendsas_of_date,To avoid double-checking the snapshots into the group;"
            "Please generate the report by cross-reference date.",
            analysis_kind=kind,
            field="as_of_date",
        )
    summary_rows = _vtg_product_summaries(detail_rows)
    total_disbursement = sum(row["disbursement_amount"] for row in detail_rows)
    total_avg_balance = sum(row["avg_daily_balance"] for row in detail_rows)
    terminal_loss = sum(
        row["terminal_bad_rate"] * row["disbursement_amount"] for row in detail_rows
    )
    observed_loss = sum(
        row["mob14_bad_rate"] * row["disbursement_amount"] for row in detail_rows
    )
    weighted_terminal = _safe_ratio(terminal_loss, total_disbursement)
    weighted_mob14 = _safe_ratio(observed_loss, total_disbursement)
    portfolio_annualized = _safe_ratio(terminal_loss, total_avg_balance)
    portfolio_observed_annualized = _safe_ratio(observed_loss, total_avg_balance)
    portfolio_turnover = _safe_ratio(total_disbursement, total_avg_balance)

    highest = max(detail_rows, key=lambda item: item["annualized_bad_rate"])
    key_points = [
        (
            f"Highest annualization: products{highest['product']} / cohort {highest['cohort']} Yes"
            f"{_format_percent(highest['annualized_bad_rate'])}."
        )
    ]
    if portfolio_annualized is not None:
        key_points.insert(
            0, f"Group weighted annualized downrate{_format_percent(portfolio_annualized)}."
        )
    change_rows = [
        row for row in detail_rows if row["annualized_bad_rate_change"] is not None
    ]
    if change_rows:
        largest_change = max(
            change_rows, key=lambda item: abs(item["annualized_bad_rate_change"])
        )
        key_points.append(
            "The greatest change in annualized poor: products"
            f"{largest_change['product']} / cohort {largest_change['cohort']},"
            f"Prior period{_format_change(largest_change['annualized_bad_rate_change'])}."
        )

    red_flags: list[str] = []
    if zero_disbursement_skipped_count:
        red_flags.append(
            f"{zero_disbursement_skipped_count} The amount of the zero-discounted funds is not measured, but it is not."
            "Not/The future.cohort Placed rows are recorded for data quality."
        )
    if terminal_above_mob_count:
        red_flags.append(
            f"{terminal_above_mob_count} End-of-line bad rate higherMOB14 Undesired rates, check end values and observation calibrations."
        )
    if substitution_count:
        red_flags.append(
            f"{substitution_count} Line Missingterminal_bad_rate,UsedMOB14 With long-term recovery rates."
        )
    if auxiliary_min_count:
        red_flags.append(
            f"{auxiliary_min_count} Lines have both a supporting end and recovery extrapolation, which is the minimum of both."
        )
    if direct_auxiliary_ignored_count:
        red_flags.append(
            f"{direct_auxiliary_ignored_count} Lines provide both direct and ancillary end values;"
            "In the case of direct end value, the ancillary end value is reserved only for retroactive and non-participation."
        )
    if derived_balance_count:
        red_flags.append(
            f"{derived_balance_count} Missing average daily balance by loan amount/Replace the number of times."
        )
    if annualized_over_one_count:
        red_flags.append(
            f"{annualized_over_one_count} The current, observed or prior-period annualized poor rate exceeds 100%, and the current rate of deterioration is higher than 100%."
            "Please verify the number and the calibration of turnover."
        )
    if zero_mob_count:
        red_flags.append(f"{zero_mob_count} Okay.MOB14 The negative rate is 0, and the long-term recovery rate is not possible to calculate.")
    if partial_previous_count:
        red_flags.append(
            f"{partial_previous_count} Line previous period fields are incomplete and no annualized changes are calculated."
        )

    assumptions = [
        "terminal_bad_rate End-value bad rate when missing= MOB14 Bad rate× (1 - Long-term recovery rate).",
        (
            "terminal_bad_rate The following is a list of the most important examples of the results of the study:"
            "Only visibleselection_rule=min_auxiliary_recovery takes the minimum of both values."
        ),
        (
            "Only whenterminal_method=min_mob14_auxiliary The government has also been able to provide a complete picture of the situation in the country, and the government has been able to provide a complete picture of the situation."
            "End value bymin(MOB14 Bad rate, Assisted end) Calculate."
        ),
        "Annualized under-representation rate= End-value bad rate× Number of turnovers; observation of annualized downscaling rate= MOB14 Bad rate× Number of rounds.",
        "By loan amount when the average balance is missing÷ Number of turnovers extrapolated.",
        (
            "When the summary model provides both average daily balances and turnover, the average daily balance and the amount of the loan is requested÷ (a) The number of turnovers is consistent;"
            f"Relatively poor{_VTG_BALANCE_RECONCILIATION_REL_TOLERANCE:g},It's absolutely bad."
            f"{_VTG_BALANCE_RECONCILIATION_ABS_TOLERANCE:g}."
        ),
        (
            "Number of prior period turnovers versus prior period amounts/(b) The average daily balance is presented with the same margin of representation;"
            "Prior-period annualized bad rate versus prior-period end value/The number of swings is provided at the same time as the absolute tolerance"
            f"{_VTG_ANNUALIZED_RECONCILIATION_TOLERANCE:g}(1 bp)Funny."
        ),
        "Long-term recovery rate= (MOB14 Bad rate- End-value bad rate) ÷ MOB14 Bad rate.",
        "The annualized downrate for the combined negative rate is the amount of the final loss.÷ The average daily balance is summarized.",
        (
            "mob14_bad_rate It has to be actually observed.MOB14 or is projected upstream by a clear method"
            "MOB14;This tool does not use premature raw.MOB Values are self-push."
        ),
        f"Amount fields are used uniformlyamount_unit={amount_units[0]}.",
    ]
    if curve_derived_count:
        if (
            "mob_balance_amount" in mapping
            and "mob_balance_rate" in mapping
        ):
            balance_basis = (
                "Amounts available in line by line or amount released× Balance rate; both are pre-existing"
            )
        elif "mob_balance_amount" in mapping:
            balance_basis = "Balance"
        else:
            balance_basis = "Amount released× Balance rate"
        day_count_bases = _ordered_unique(
            f"{row['day_count_basis']:g}" for row in detail_rows
        )
        assumptions.append(
            f"OriginalMOB Curves by groupsday_count_basis(This time:{','.join(day_count_bases)})Calculate:"
            f"Average balance per day= Σ({balance_basis} × MOB Days) ÷ day_count_basis,"
            "Number of turnovers= Amount released÷ Average balance per day.mob_balance_rate/mob_balance_amount "
            "It has to be individual.MOB Average daily balance rate between sectors/Amounts, which may not be directly used as balance at month end."
        )
    if zero_disbursement_skipped_count:
        assumptions.append("The zero-loaning line is the place-holder data and does not enter the final, working-group summary.")
    if declared_terminal_methods:
        assumptions.append(
            "Data declarationterminal_method The following is kept in the following detail for the purpose of caliber retroactive:"
            + ",".join(_ordered_unique(declared_terminal_methods))
            + ";Actual value priority still interminal_bad_rate_source Yes."
        )
    if direct_recovery_reconciled_count:
        assumptions.append(
            f"{direct_recovery_reconciled_count} The line provides both direct end value and long-term recovery rates;"
            "Savedsupplied_long_term_recovery_rate and"
            "realized_long_term_recovery_rate,And it's absolutely imperceptible."
            f"{_VTG_RECOVERY_RECONCILIATION_TOLERANCE:g}(1 bp)Finish the joke."
        )
    if explicit_mob_auxiliary_min_count:
        assumptions.append(
            f"{explicit_mob_auxiliary_min_count} Line-by-Specific"
            "terminal_method=min_mob14_auxiliary Calculate, there is no hidden application of the rule."
        )
    if derived_previous_turnover_count:
        assumptions.append(
            f"{derived_previous_turnover_count} The number of prior-period turnovers is based on the amount of prior-period loans÷ "
            "Average balance of prior-period balances extrapolated from the source recorded asderived_from_amount_balance."
        )
    if derived_previous_annualized_count:
        assumptions.append(
            f"{derived_previous_annualized_count} Prior-period annualized bad rate at end-of-period rate× "
            "The number of prior-period turnovers is extrapolated from the source recorded asderived_from_terminal_turnover."
        )
    if not change_rows:
        assumptions.append("The complete negative calibre of the previous period was not provided and the maximum change item was not generated.")
    if total_disbursement == 0.0 or total_avg_balance == 0.0:
        assumptions.append("The grouping value denominator is 0, leaving blank the corresponding weighted indicator.")

    headline_metrics = {
        "product_count": len({row["product"] for row in detail_rows}),
        "cohort_count": len({row["cohort"] for row in detail_rows}),
        "total_disbursement_amount": total_disbursement,
        "total_avg_daily_balance": total_avg_balance,
        "portfolio_turnover": portfolio_turnover,
        "weighted_mob14_bad_rate": weighted_mob14,
        "weighted_terminal_bad_rate": weighted_terminal,
        "observed_annualized_bad_rate": portfolio_observed_annualized,
        "annualized_bad_rate": portfolio_annualized,
        "highest_annualized_bad_rate": highest["annualized_bad_rate"],
        "highest_annualized_product": highest["product"],
        "highest_annualized_cohort": highest["cohort"],
    }
    all_products = _ordered_unique(row["product"] for row in detail_rows)
    product_scope = _product_scope(all_products)
    if len(all_products) > PRODUCT_SCOPE_LIMIT:
        assumptions.append(
            f"Total products{len(all_products)} One;DONE metadata It's...product_scope Save only before"
            f"{PRODUCT_SCOPE_LIMIT} - Yeah, it says it's fine."
        )
    as_of_period = _period_scope(row["as_of_date"] for row in detail_rows)
    formula_definitions = [
        {
            "metric": "terminal_bad_rate",
            "formula": (
                "direct terminal; otherwise min(mob14_bad_rate, auxiliary_terminal) "
                "when terminal_method=min_mob14_auxiliary; otherwise "
                "min(auxiliary_terminal, mob14_bad_rate * (1 - long_term_recovery_rate)) "
                "when both recovery substitutes exist"
            ),
            "note": (
                "direct terminal priority; substitution only enabled when direct terminal is missing; inputterminal_method "
                "The statement of business methodology is retained in the breakdown."
            ),
        },
        {
            "metric": "annualized_bad_rate",
            "formula": "terminal_bad_rate * turnover",
            "note": "Discrepancies in single-line years.",
        },
        {
            "metric": "avg_daily_balance",
            "formula": (
                "sum(mob_balance_amount * mob_days) / day_count_basis, or "
                "disbursement_amount * sum(mob_balance_rate * mob_days) / day_count_basis; "
                "otherwise disbursement_amount / turnover when missing"
            ),
            "note": (
                "Curve balance must beMOB Average day balance between sectors instead of month-end balance; summary pattern average balance only"
                "Push back the number of swings when missing."
            ),
        },
        {
            "metric": "long_term_recovery_rate",
            "formula": "(mob14_bad_rate - terminal_bad_rate) / mob14_bad_rate",
            "note": (
                "MOB14 leave space for 0; input value saved assupplied_long_term_recovery_rate,"
                "Save Achieved asrealized_long_term_recovery_rate."
            ),
        },
        {
            "metric": "previous_turnover",
            "formula": (
                "previous_disbursement_amount / previous_avg_daily_balance "
                "when previous_turnover is missing"
            ),
            "note": "The average balance of the previous period must be greater than 0; the extrapolation source is retained in the breakdown.",
        },
        {
            "metric": "previous_annualized_bad_rate",
            "formula": (
                "previous_terminal_bad_rate * previous_turnover "
                "when previous_annualized_bad_rate is missing"
            ),
            "note": "The extrapolation source is retained in the breakdown.",
        },
    ]
    data_quality = [
        {
            "check": "Source data rows",
            "status": "PASS",
            "detail": f"Verifyed{source_row_count} Line source data.",
        },
        {
            "check": "Number of result lines",
            "status": "PASS",
            "detail": f"Generated{len(detail_rows)} Line/cohort Results.",
        },
        {
            "check": "Input Rate Range",
            "status": "PASS",
            "detail": (
                "The probability rate is in.[0, 1];previous_annualized_bad_rate The government has been able to provide the necessary information to the public."
                "Allows more than 100% and creates risk tips."
            ),
        },
        {"check": "Amount range", "status": "PASS", "detail": "All amounts are non-negative."},
        {"check": "Number of turnovers", "status": "PASS", "detail": "All turnovers are greater than zero."},
        {
            "check": "Missing Fields Replace",
            "status": "WARN" if substitution_count or derived_balance_count else "PASS",
            "detail": f"End of value substitute{substitution_count} rows;average balance replacement{derived_balance_count} All right.",
        },
    ]
    if curve_derived_count:
        basis_scope = _ordered_unique(
            f"{row['day_count_basis']:g}" for row in detail_rows
        )
        data_quality.append(
            {
                "check": "MOB Balance Curve",
                "status": "PASS",
                "detail": (
                    f"Verifyed and Pressedday_count_basis={','.join(basis_scope)} Summary"
                    f"{curve_derived_count} Product/cohort curve."
                ),
            }
        )
    if zero_disbursement_skipped_count:
        data_quality.append(
            {
                "check": "Zero-discounted.",
                "status": "WARN",
                "detail": (
                    f"Source data{zero_disbursement_skipped_count} The loan is in the amount of 0, and the loan is in the amount of 10,540."
                    "Skipped and did not enter any weighted denominator."
                ),
            }
        )
    return RiskAnalysisCalculation(
        analysis_kind=kind,
        column_map=mapping,
        product_scope=product_scope,
        as_of_period=as_of_period,
        headline_metrics=headline_metrics,
        key_points=key_points,
        red_flags=_unique_strings(red_flags),
        assumptions=_unique_strings(assumptions),
        source_row_count=source_row_count,
        row_count=len(detail_rows),
        detail_rows=detail_rows,
        summary_rows=summary_rows,
        formula_definitions=formula_definitions,
        data_quality=data_quality,
    )


def calculate_profitability(
    frame: pd.DataFrame,
    *,
    column_map: dict[str, str],
) -> RiskAnalysisCalculation:
    kind = "profitability"
    data = _normalized_frame(frame, analysis_kind=kind)
    source_row_count = len(data)
    mapping = _normalize_column_map(data, column_map, analysis_kind=kind)
    _require_mappings(mapping, _PROFIT_REQUIRED, analysis_kind=kind)
    working_mapping = mapping
    customer_stage_group_count = 0
    if "customer_stage" in mapping:
        _require_mappings(mapping, ("transaction_weight",), analysis_kind=kind)
        data, working_mapping = _collapse_profitability_customer_stages(
            data,
            mapping=mapping,
            analysis_kind=kind,
        )
        customer_stage_group_count = len(data)

    detail_rows: list[dict[str, Any]] = []
    scenario_missing_count = 0
    derived_cost_counts = dict.fromkeys(_PROFIT_DERIVABLE_COST_FIELDS, 0)
    reconciled_cost_counts = dict.fromkeys(_PROFIT_DERIVABLE_COST_FIELDS, 0)
    supplied_driver_values: dict[str, list[Any]] = {
        field: [] for field in _PROFIT_DRIVER_FIELDS
    }

    for position, row in data.iterrows():
        row_number = position + 1
        product = _required_text(row, working_mapping, "product", kind, row_number)
        asset_class = _required_text(
            row, working_mapping, "asset_class", kind, row_number
        )
        as_of_period_value = _required_text(
            row, working_mapping, "as_of_period", kind, row_number
        )
        scenario = _optional_text(row, working_mapping, "scenario")
        if scenario is None:
            scenario_missing_count += 1
            scenario = "Benchmark"
        weight = _number(
            row,
            working_mapping,
            "weight",
            kind,
            row_number,
            required=True,
            rate=True,
        )
        weight_basis = _required_text(
            row, working_mapping, "weight_basis", kind, row_number
        )
        if weight_basis != "average_balance":
            raise RiskAnalysisError(
                f"I'm sorry.{row_number} Okay.weight_basis={weight_basis!r};"
                "The revenue measure is only supportedaverage_balance.",
                analysis_kind=kind,
                field="weight_basis",
                row_number=row_number,
            )
        customer_rate = _number(
            row,
            working_mapping,
            "customer_rate",
            kind,
            row_number,
            required=True,
            rate=True,
        )
        costs, cost_sources, drivers = _resolve_profitability_costs(
            row,
            mapping=working_mapping,
            analysis_kind=kind,
            row_number=row_number,
            customer_rate=customer_rate,
        )
        stage_data_source = _optional_text(
            row, working_mapping, "stage_data_cost_source"
        )
        customer_stage_provenance = _optional_text(
            row, working_mapping, "customer_stage_provenance"
        )
        customer_stage_count = _number(
            row,
            working_mapping,
            "customer_stage_count",
            kind,
            row_number,
            minimum=0.0,
            minimum_inclusive=False,
        )
        transaction_weight_sum = _number(
            row,
            working_mapping,
            "transaction_weight_sum",
            kind,
            row_number,
            minimum=0.0,
            minimum_inclusive=False,
        )
        if stage_data_source is not None:
            cost_sources["data_cost_rate"] = stage_data_source
            drivers["amount_unit"] = _optional_text(row, working_mapping, "amount_unit")
        for field in _PROFIT_DERIVABLE_COST_FIELDS:
            if cost_sources[field].startswith("derived_"):
                derived_cost_counts[field] += 1
            elif cost_sources[field].startswith("explicit_reconciled_"):
                reconciled_cost_counts[field] += 1
        for field, value in drivers.items():
            if value is not None:
                supplied_driver_values[field].append(value)

        fixed_income_yield = (
            customer_rate
            - costs["interest_loss_rate"]
            - costs["revenue_share_rate"]
            - costs["risk_cost_rate"]
            - costs["acquisition_cost_rate"]
        )
        total_cost_rate = sum(costs[field] for field in _PROFIT_COST_FIELDS)
        net_yield = customer_rate - total_cost_rate
        detail_rows.append(
            {
                "product": product,
                "asset_class": asset_class,
                "as_of_period": as_of_period_value,
                "scenario": scenario,
                "weight": weight,
                "weight_basis": weight_basis,
                "customer_rate": customer_rate,
                **{field: costs[field] for field in _PROFIT_COST_FIELDS},
                **{
                    f"{field}_source": cost_sources[field]
                    for field in _PROFIT_DERIVABLE_COST_FIELDS
                },
                **{field: drivers[field] for field in _PROFIT_DRIVER_FIELDS},
                "customer_stage_count": customer_stage_count,
                "transaction_weight_sum": transaction_weight_sum,
                "customer_stage_provenance": customer_stage_provenance,
                "fixed_income_yield": fixed_income_yield,
                "total_cost_rate": total_cost_rate,
                "net_yield": net_yield,
            }
        )

    seen_profit_slices: set[tuple[str, str, str, str]] = set()
    for row in detail_rows:
        slice_key = (
            row["product"],
            row["as_of_period"],
            row["scenario"],
            row["asset_class"],
        )
        if slice_key in seen_profit_slices:
            raise RiskAnalysisError(
                "The yield measure must be the only particle size.product × as_of_period × scenario × "
                f"asset_class;Repetition of business slices detected{slice_key!r}.",
                analysis_kind=kind,
                field="asset_class",
            )
        seen_profit_slices.add(slice_key)

    summary_rows = _profit_product_summaries(detail_rows, analysis_kind=kind)
    scenario_spreads: list[dict[str, Any]] = []
    scenario_group_keys = list(
        dict.fromkeys((row["product"], row["as_of_period"]) for row in summary_rows)
    )
    for product, period in scenario_group_keys:
        scenario_rows = [
            row
            for row in summary_rows
            if row["product"] == product and row["as_of_period"] == period
        ]
        if len({row["scenario"] for row in scenario_rows}) < 2:
            continue
        high = max(scenario_rows, key=lambda item: item["net_yield"])
        low = min(scenario_rows, key=lambda item: item["net_yield"])
        spread = high["net_yield"] - low["net_yield"]
        if math.isclose(spread, 0.0, rel_tol=0.0, abs_tol=1e-12):
            continue
        scenario_spreads.append(
            {
                "product": product,
                "as_of_period": period,
                "spread": spread,
                "high_scenario": high["scenario"],
                "low_scenario": low["scenario"],
            }
        )
    largest_scenario_spread = (
        max(scenario_spreads, key=lambda item: item["spread"])
        if scenario_spreads
        else None
    )
    lowest = min(summary_rows, key=lambda item: item["net_yield"])
    highest = max(summary_rows, key=lambda item: item["net_yield"])
    max_cost_product: str | None = None
    max_cost_field: str | None = None
    max_cost_rate = -math.inf
    for summary in summary_rows:
        for field in _PROFIT_COST_FIELDS:
            value = summary[field]
            if value > max_cost_rate:
                max_cost_rate = value
                max_cost_field = field
                max_cost_product = summary["product"]
    max_cost_slice = max(
        summary_rows,
        key=lambda item: item[max_cost_field or "risk_cost_rate"],
    )

    key_points = [
        f"The lowest net rate of return:{_profit_slice_identity(lowest)} Yes{_format_percent(lowest['net_yield'])}.",
        (
            f"Maximum cost item:{_profit_slice_identity(max_cost_slice)} It's..."
            f"{_COST_LABELS.get(max_cost_field or '', max_cost_field)} "
            f"Yes{_format_percent(max_cost_rate)}."
        ),
        f"The highest net rate of return was:{_profit_slice_identity(highest)} Yes{_format_percent(highest['net_yield'])}.",
    ]
    if largest_scenario_spread is not None:
        key_points.append(
            "The largest difference in net return from the scene: products"
            f"{largest_scenario_spread['product']} / Period"
            f"{largest_scenario_spread['as_of_period']},High scene"
            f"{largest_scenario_spread['high_scenario']},Low scene"
            f"{largest_scenario_spread['low_scenario']},Difference"
            f"{largest_scenario_spread['spread'] * 100:.2f} Percentage point."
        )
    red_flags = [
        f"{_profit_slice_identity(row)} Weighted net gain{_format_percent(row['net_yield'])},Less than zero."
        for row in summary_rows
        if row["net_yield"] < 0.0
    ]
    red_flags.extend(
        (
            f"{_profit_slice_identity(row)} Type of solid collection rate of return"
            f"{_format_percent(row['fixed_income_yield'])},Less than zero."
        )
        for row in summary_rows
        if row["fixed_income_yield"] < 0.0
    )

    assumptions = [
        (
            "Class solid harvest rate of return= Interest rate on clients- Rate of loss of interest- Rates of depreciation- Risk cost rate- (b) The cost of the acquisition;"
            "The rate of the profit-making factor must have been converted to the asset-rate-gain calibre and the contract-based share must not be passed directly."
        ),
        (
            "Net rate of return= Interest rate on clients- Rate of loss of interest- Rates of depreciation- Risk cost rate- Cost-of-takers rate- "
            "Data cost rate- Cost of payment- Routine cost- Cost of funds- Other cost rates- Tax rate."
        ),
        (
            "The weight of each product, data period, asset class within the landscape combination and the number of items to be included in the"
            f"1±{WEIGHT_SUM_TOLERANCE:g} Inside."
        ),
        "Each cost field is the annualization rate of the asset balance and cannot be commingled in amounts or contract splits.",
        "weight_basis I must.average_balance;Products/Period/The scene weights are aggregated by mean balance calibre.",
    ]
    if derived_cost_counts["risk_cost_rate"]:
        assumptions.append(
            "Risk cost rate= terminal_vintage_rate × risk_turnover;Present offer"
            f"terminal_vintage_rate={_format_value_set(supplied_driver_values['terminal_vintage_rate'], percent=True)},"
            f"risk_turnover={_format_value_set(supplied_driver_values['risk_turnover'])}."
        )
    if derived_cost_counts["interest_loss_rate"]:
        assumptions.append(
            "Rate of loss of interest= customer_rate × resolved_risk_cost_rate × loss_timing_factor;"
            "Present offerloss_timing_factor="
            f"{_format_value_set(supplied_driver_values['loss_timing_factor'])}."
        )
    if derived_cost_counts["revenue_share_rate"]:
        assumptions.append(
            "Rates of depreciation= (customer_rate - resolved_interest_loss_rate) × "
            "profit_share_ratio;Present offerprofit_share_ratio="
            f"{_format_value_set(supplied_driver_values['profit_share_ratio'], percent=True)}."
        )
    if derived_cost_counts["data_cost_rate"]:
        data_amount_units = _ordered_unique(
            str(value) for value in supplied_driver_values["amount_unit"]
        )
        if customer_stage_group_count:
            stage_descriptions = _ordered_unique(
                row["customer_stage_provenance"]
                for row in detail_rows
                if row.get("customer_stage_provenance")
            )
            assumptions.append(
                "Client phase data costs are extrapolated by the funnel formula and then pressedtransaction_weight (b) Weighting;"
                f"Already{source_row_count} Line Stage Source Collapse As"
                f"{customer_stage_group_count} The result of the asset."
                + ";".join(stage_descriptions)
                + f".Amount units={','.join(data_amount_units)}."
            )
        else:
            assumptions.append(
                "Data cost rate= per_application_cost ÷ (credit_approval_rate × "
                "draw_initiation_rate × draw_approval_rate × average_ticket) × "
                "data_annualization_factor;Present offerdata_annualization_factor="
                f"{_format_value_set(supplied_driver_values['data_annualization_factor'])},"
                f"per_application_cost andaverage_ticket It's...amount_unit="
                f"{','.join(data_amount_units)}."
            )
    if derived_cost_counts["tax_rate"]:
        assumptions.append(
            "tax_method=sample_net_revenue_vat_surcharge The tax base is strictly standard.D12 caliber= "
            "customer_rate - interest_loss_rate - revenue_share_rate - acquisition_cost_rate - "
            "data_cost_rate - payment_cost_rate - collection_cost_rate;"
            "Tax rate= Tax base÷ tax_inclusive_divisor × tax_combined_rate.Present offer"
            f"tax_inclusive_divisor={_format_value_set(supplied_driver_values['tax_inclusive_divisor'])},"
            f"tax_combined_rate={_format_value_set(supplied_driver_values['tax_combined_rate'], percent=True)}."
        )
    if any(reconciled_cost_counts.values()):
        assumptions.append(
            "When the apparent cost rate is provided in conjunction with its driver, it is already line-by-line; it is absolutely not acceptable"
            f"{PROFIT_RATE_RECONCILIATION_TOLERANCE:g}(1 bp).Number of funny stories:"
            + ";".join(
                f"{field} {count} Okay."
                for field, count in reconciled_cost_counts.items()
                if count
            )
            + "."
        )
    as_of_period = _period_scope(row["as_of_period"] for row in detail_rows)
    if scenario_missing_count:
        assumptions.append(
            f"The revenue-measured scenes are listed.{scenario_missing_count} Lines are missing, and these lines are classified as (baseline) scenarios."
        )

    all_products = _ordered_unique(row["product"] for row in detail_rows)
    product_scope = _product_scope(all_products)
    if len(all_products) > PRODUCT_SCOPE_LIMIT:
        assumptions.append(
            f"Total products{len(all_products)} One;DONE metadata It's...product_scope Save only before"
            f"{PRODUCT_SCOPE_LIMIT} - Yeah, it says it's fine."
        )

    headline_metrics = {
        "product_count": len({row["product"] for row in summary_rows}),
        "analysis_slice_count": len(summary_rows),
        "negative_product_count": len(
            {row["product"] for row in summary_rows if row["net_yield"] < 0.0}
        ),
        "lowest_net_yield": lowest["net_yield"],
        "lowest_net_yield_product": lowest["product"],
        "lowest_net_yield_as_of_period": lowest["as_of_period"],
        "lowest_net_yield_scenario": lowest["scenario"],
        "highest_net_yield": highest["net_yield"],
        "highest_net_yield_product": highest["product"],
        "highest_net_yield_as_of_period": highest["as_of_period"],
        "highest_net_yield_scenario": highest["scenario"],
        "max_cost_rate": max_cost_rate,
        "max_cost_component": max_cost_field,
        "max_cost_product": max_cost_product,
        "max_cost_as_of_period": max_cost_slice["as_of_period"],
        "max_cost_scenario": max_cost_slice["scenario"],
    }
    if largest_scenario_spread is not None:
        headline_metrics.update(
            {
                "largest_scenario_net_yield_spread": largest_scenario_spread["spread"],
                "largest_scenario_net_yield_spread_product": _bounded_text(
                    largest_scenario_spread["product"],
                    PRODUCT_SCOPE_ITEM_MAX_CHARS,
                ),
                "largest_scenario_net_yield_spread_as_of_period": _bounded_text(
                    largest_scenario_spread["as_of_period"],
                    AS_OF_PERIOD_MAX_CHARS,
                ),
                "largest_scenario_net_yield_spread_high_scenario": _bounded_text(
                    largest_scenario_spread["high_scenario"], SCENARIO_MAX_CHARS
                ),
                "largest_scenario_net_yield_spread_low_scenario": _bounded_text(
                    largest_scenario_spread["low_scenario"], SCENARIO_MAX_CHARS
                ),
            }
        )
    formula_definitions = [
        {
            "metric": "risk_cost_rate",
            "formula": (
                "explicit risk_cost_rate; otherwise terminal_vintage_rate * "
                "risk_turnover"
            ),
            "note": "Detailed.risk_cost_rate_source Marks the visible or extrapolating source.",
        },
        {
            "metric": "interest_loss_rate",
            "formula": (
                "explicit interest_loss_rate; otherwise customer_rate * "
                "resolved_risk_cost_rate * loss_timing_factor"
            ),
            "note": "loss_timing_factor No default value, must be provided by input.",
        },
        {
            "metric": "revenue_share_rate",
            "formula": (
                "explicit revenue_share_rate; otherwise (customer_rate - "
                "resolved_interest_loss_rate) * profit_share_ratio"
            ),
            "note": (
                "profit_share_ratio is the ratio of the contract torevenue_share_rate It's the same cost."
                "Original/(a) Annualization;acquisition_cost_rate Only for independent cost-sharing, which is different from that of the contract."
            ),
        },
        {
            "metric": "data_cost_rate",
            "formula": (
                "explicit data_cost_rate; otherwise per_application_cost / "
                "(credit_approval_rate * draw_initiation_rate * draw_approval_rate * "
                "average_ticket) * data_annualization_factor"
            ),
            "note": "The funnel rate, the per capita unit price and the annualization factor must be visible and the denominator greater than zero.",
        },
        {
            "metric": "tax_rate",
            "formula": (
                "explicit tax_rate; otherwise net_revenue_tax_base / "
                "tax_inclusive_divisor * tax_combined_rate when "
                "tax_method=sample_net_revenue_vat_surcharge"
            ),
            "note": "When the base is negative, it is not hidden.",
        },
        {
            "metric": "fixed_income_yield",
            "formula": "customer_rate - interest_loss_rate - revenue_share_rate - risk_cost_rate - acquisition_cost_rate",
            "note": "The sub-fields shall be converted to a cost factor; this indicator shall be free of cost for the financial and operational categories.",
        },
        {
            "metric": "net_yield",
            "formula": "customer_rate - interest_loss_rate - revenue_share_rate - risk_cost_rate - acquisition_cost_rate - data_cost_rate - payment_cost_rate - collection_cost_rate - funding_cost_rate - other_cost_rate - tax_rate",
            "note": "Final net rate of return.",
        },
        {
            "metric": "product_weighted_yield",
            "formula": "sum(asset_class_yield * weight) within product, as_of_period, and scenario",
            "note": (
                "weight_basis=average_balance;Products/Period/Scene group internal weights and allowed errors"
                f"{WEIGHT_SUM_TOLERANCE:g}."
            ),
        },
    ]
    data_quality = [
        {
            "check": "Source data rows",
            "status": "PASS",
            "detail": f"Verifyed{source_row_count} Line source data.",
        },
        {
            "check": "Number of result lines",
            "status": "PASS",
            "detail": f"Generated{len(detail_rows)} The result of the line-benefit measurement.",
        },
        {
            "check": "Input Rate Range",
            "status": "PASS",
            "detail": "All input rates and weights are equal[0, 1].",
        },
        {
            "check": "Products/Period/scene weight",
            "status": "PASS",
            "detail": f"All products/Period/The sum of the weights of the set is equal to 1±{WEIGHT_SUM_TOLERANCE:g}.",
        },
        {
            "check": "Cost field integrity",
            "status": "PASS",
            "detail": (
                "All net income cost fields are either visibly provided or extrapolated by the complete driver;"
                "Visible 0 is processed at zero cost."
            ),
        },
        {
            "check": "Cost field source",
            "status": "PASS",
            "detail": ";".join(
                f"{field} Insulation{derived_cost_counts[field]} Okay."
                f"Visible values are ridiculous{reconciled_cost_counts[field]} Okay."
                for field in _PROFIT_DERIVABLE_COST_FIELDS
            ),
        },
    ]
    return RiskAnalysisCalculation(
        analysis_kind=kind,
        column_map=mapping,
        product_scope=product_scope,
        as_of_period=as_of_period,
        headline_metrics=headline_metrics,
        key_points=key_points,
        red_flags=_unique_strings(red_flags),
        assumptions=_unique_strings(assumptions),
        source_row_count=source_row_count,
        row_count=len(detail_rows),
        detail_rows=detail_rows,
        summary_rows=summary_rows,
        formula_definitions=formula_definitions,
        data_quality=data_quality,
    )


def _collapse_profitability_customer_stages(
    data: pd.DataFrame,
    *,
    mapping: dict[str, str],
    analysis_kind: str,
) -> tuple[pd.DataFrame, dict[str, str]]:
    varying_fields = {
        "customer_stage",
        "transaction_weight",
        "per_application_cost",
        "credit_approval_rate",
        "draw_initiation_rate",
        "draw_approval_rate",
        "average_ticket",
        "data_annualization_factor",
        "data_cost_rate",
    }
    groups: dict[tuple[str, str, str, str], list[int]] = {}
    for position, row in data.iterrows():
        row_number = position + 1
        product = _required_text(row, mapping, "product", analysis_kind, row_number)
        asset_class = _required_text(
            row, mapping, "asset_class", analysis_kind, row_number
        )
        period = _optional_text(row, mapping, "as_of_period") or "Not provided"
        scenario = _optional_text(row, mapping, "scenario") or "Benchmark"
        groups.setdefault((product, period, scenario, asset_class), []).append(position)

    data_cost_column = _unused_column_name(data, "__stage_data_cost_rate")
    stage_count_column = _unused_column_name(data, "__customer_stage_count")
    weight_sum_column = _unused_column_name(data, "__transaction_weight_sum")
    provenance_column = _unused_column_name(data, "__customer_stage_provenance")
    source_column = _unused_column_name(data, "__stage_data_cost_source")
    collapsed_rows: list[pd.Series] = []

    for (product, period, scenario, asset_class), positions in groups.items():
        group = data.loc[positions]
        for field, source in mapping.items():
            if field in varying_fields:
                continue
            tokens = {_consistency_token(value) for value in group[source].tolist()}
            if len(tokens) != 1:
                raise RiskAnalysisError(
                    f"Products{product} / Period{period} / scene{scenario} / Assets"
                    f"{asset_class} It's...{field} There must be consistency between client phases.",
                    analysis_kind=analysis_kind,
                    field=field,
                    row_number=positions[0] + 1,
                )
        if "data_cost_rate" in mapping and any(
            not _is_missing(value) for value in group[mapping["data_cost_rate"]]
        ):
            raise RiskAnalysisError(
                f"Products{product} / Period{period} / scene{scenario} / Assets"
                f"{asset_class} Providedcustomer_stage It's not always available.data_cost_rate.",
                analysis_kind=analysis_kind,
                field="data_cost_rate",
                row_number=positions[0] + 1,
            )

        weighted_data_cost = 0.0
        transaction_weight_sum = 0.0
        provenance: list[str] = []
        seen_stages: set[str] = set()
        for position in positions:
            row = data.loc[position]
            row_number = position + 1
            stage = _required_text(
                row, mapping, "customer_stage", analysis_kind, row_number
            )
            if stage in seen_stages:
                raise RiskAnalysisError(
                    f"Products{product} / Period{period} / scene{scenario} / Assets"
                    f"{asset_class} It's...customer_stage It has to be the only duplicate value found.{stage!r}.",
                    analysis_kind=analysis_kind,
                    field="customer_stage",
                    row_number=row_number,
                )
            seen_stages.add(stage)
            transaction_weight = _number(
                row,
                mapping,
                "transaction_weight",
                analysis_kind,
                row_number,
                required=True,
                minimum=0.0,
                minimum_inclusive=False,
            )
            assert transaction_weight is not None
            stage_data_cost, _ = _derive_profitability_data_cost(
                row,
                mapping=mapping,
                analysis_kind=analysis_kind,
                row_number=row_number,
            )
            weighted_data_cost += stage_data_cost * transaction_weight
            transaction_weight_sum += transaction_weight
            provenance.append(
                f"{stage}(weight={transaction_weight:g},data_cost_rate={stage_data_cost:.6%})"
            )

        collapsed = data.loc[positions[0]].copy()
        collapsed[data_cost_column] = weighted_data_cost / transaction_weight_sum
        collapsed[stage_count_column] = len(positions)
        collapsed[weight_sum_column] = transaction_weight_sum
        collapsed[provenance_column] = ";".join(provenance)
        collapsed[source_column] = "derived_weighted_customer_stages"
        collapsed_rows.append(collapsed)

    working_mapping = dict(mapping)
    working_mapping["data_cost_rate"] = data_cost_column
    working_mapping["customer_stage_count"] = stage_count_column
    working_mapping["transaction_weight_sum"] = weight_sum_column
    working_mapping["customer_stage_provenance"] = provenance_column
    working_mapping["stage_data_cost_source"] = source_column
    return pd.DataFrame(collapsed_rows).reset_index(drop=True), working_mapping


def _derive_profitability_data_cost(
    row: pd.Series,
    *,
    mapping: dict[str, str],
    analysis_kind: str,
    row_number: int,
) -> tuple[float, dict[str, Any]]:
    amount_unit = _optional_text(row, mapping, "amount_unit")
    if amount_unit is None:
        raise RiskAnalysisError(
            f"I'm sorry.{row_number} Line Wizarddata_cost_rate Timeamount_unit Can't be empty.",
            analysis_kind=analysis_kind,
            field="amount_unit",
            row_number=row_number,
        )
    per_application_cost = _number(
        row,
        mapping,
        "per_application_cost",
        analysis_kind,
        row_number,
        required=True,
        minimum=0.0,
    )
    credit_approval_rate = _number(
        row,
        mapping,
        "credit_approval_rate",
        analysis_kind,
        row_number,
        required=True,
        rate=True,
        minimum=0.0,
        minimum_inclusive=False,
    )
    draw_initiation_rate = _number(
        row,
        mapping,
        "draw_initiation_rate",
        analysis_kind,
        row_number,
        required=True,
        rate=True,
        minimum=0.0,
        minimum_inclusive=False,
    )
    draw_approval_rate = _number(
        row,
        mapping,
        "draw_approval_rate",
        analysis_kind,
        row_number,
        required=True,
        rate=True,
        minimum=0.0,
        minimum_inclusive=False,
    )
    average_ticket = _number(
        row,
        mapping,
        "average_ticket",
        analysis_kind,
        row_number,
        required=True,
        minimum=0.0,
        minimum_inclusive=False,
    )
    annualization_factor = _number(
        row,
        mapping,
        "data_annualization_factor",
        analysis_kind,
        row_number,
        required=True,
        minimum=0.0,
        minimum_inclusive=False,
    )
    assert (
        per_application_cost is not None
        and credit_approval_rate is not None
        and draw_initiation_rate is not None
        and draw_approval_rate is not None
        and average_ticket is not None
        and annualization_factor is not None
    )
    funnel_denominator = (
        credit_approval_rate
        * draw_initiation_rate
        * draw_approval_rate
        * average_ticket
    )
    rate = _validated_derived_rate(
        per_application_cost / funnel_denominator * annualization_factor,
        field="data_cost_rate",
        analysis_kind=analysis_kind,
        row_number=row_number,
    )
    return rate, {
        "amount_unit": amount_unit,
        "per_application_cost": per_application_cost,
        "credit_approval_rate": credit_approval_rate,
        "draw_initiation_rate": draw_initiation_rate,
        "draw_approval_rate": draw_approval_rate,
        "average_ticket": average_ticket,
        "data_annualization_factor": annualization_factor,
    }


def _has_any_mapped_value(
    row: pd.Series,
    mapping: dict[str, str],
    fields: Iterable[str],
) -> bool:
    return any(
        field in mapping
        and not _is_missing(row[mapping[field]])
        and bool(str(row[mapping[field]]).strip())
        for field in fields
    )


def _reconcile_profit_rate(
    explicit: float,
    implied: float,
    *,
    field: str,
    analysis_kind: str,
    row_number: int,
) -> None:
    if math.isclose(
        explicit,
        implied,
        rel_tol=0.0,
        abs_tol=PROFIT_RATE_RECONCILIATION_TOLERANCE,
    ):
        return
    raise RiskAnalysisError(
        f"I'm sorry.{row_number} Okay.{field}={explicit} The driver's extrapolation value={implied} "
        f"Incoherent; absolute tolerance is{PROFIT_RATE_RECONCILIATION_TOLERANCE:g}.",
        analysis_kind=analysis_kind,
        field=field,
        row_number=row_number,
    )


def _resolve_profitability_costs(
    row: pd.Series,
    *,
    mapping: dict[str, str],
    analysis_kind: str,
    row_number: int,
    customer_rate: float,
) -> tuple[dict[str, float], dict[str, str], dict[str, Any]]:
    costs: dict[str, float] = {}
    sources: dict[str, str] = {}
    drivers: dict[str, Any] = dict.fromkeys(_PROFIT_DRIVER_FIELDS)

    for field in _PROFIT_ALWAYS_EXPLICIT_COST_FIELDS:
        value = _number(
            row,
            mapping,
            field,
            analysis_kind,
            row_number,
            required=True,
            rate=True,
        )
        assert value is not None
        costs[field] = value

    risk_cost = _number(
        row, mapping, "risk_cost_rate", analysis_kind, row_number, rate=True
    )
    terminal_vintage = _number(
        row, mapping, "terminal_vintage_rate", analysis_kind, row_number, rate=True
    )
    risk_turnover = _number(
        row,
        mapping,
        "risk_turnover",
        analysis_kind,
        row_number,
        minimum=0.0,
        minimum_inclusive=False,
    )
    if risk_cost is None:
        if terminal_vintage is None or risk_turnover is None:
            raise RiskAnalysisError(
                f"I'm sorry.{row_number} Okay.risk_cost_rate The blogger adds:"
                "terminal_vintage_rate andrisk_turnover It must be provided simultaneously.",
                analysis_kind=analysis_kind,
                field="risk_cost_rate",
                row_number=row_number,
            )
        drivers["terminal_vintage_rate"] = terminal_vintage
        drivers["risk_turnover"] = risk_turnover
        risk_cost = _validated_derived_rate(
            terminal_vintage * risk_turnover,
            field="risk_cost_rate",
            analysis_kind=analysis_kind,
            row_number=row_number,
        )
        sources["risk_cost_rate"] = "derived_terminal_vintage_turnover"
    else:
        if terminal_vintage is not None or risk_turnover is not None:
            if terminal_vintage is None or risk_turnover is None:
                raise RiskAnalysisError(
                    f"I'm sorry.{row_number} Lines keep visible simultaneouslyrisk_cost_rate When you push the drive, you can see the driver."
                    "terminal_vintage_rate andrisk_turnover It must be provided simultaneously.",
                    analysis_kind=analysis_kind,
                    field="risk_cost_rate",
                    row_number=row_number,
                )
            implied_risk_cost = _validated_derived_rate(
                terminal_vintage * risk_turnover,
                field="risk_cost_rate",
                analysis_kind=analysis_kind,
                row_number=row_number,
            )
            _reconcile_profit_rate(
                risk_cost,
                implied_risk_cost,
                field="risk_cost_rate",
                analysis_kind=analysis_kind,
                row_number=row_number,
            )
            drivers["terminal_vintage_rate"] = terminal_vintage
            drivers["risk_turnover"] = risk_turnover
            sources["risk_cost_rate"] = "explicit_reconciled_terminal_vintage_turnover"
        else:
            sources["risk_cost_rate"] = "explicit"
    costs["risk_cost_rate"] = risk_cost

    interest_loss = _number(
        row, mapping, "interest_loss_rate", analysis_kind, row_number, rate=True
    )
    loss_timing_factor = _number(
        row, mapping, "loss_timing_factor", analysis_kind, row_number, rate=True
    )
    if interest_loss is None:
        if loss_timing_factor is None:
            raise RiskAnalysisError(
                f"I'm sorry.{row_number} Okay.interest_loss_rate The blogger adds:"
                "loss_timing_factor It must be provided.",
                analysis_kind=analysis_kind,
                field="interest_loss_rate",
                row_number=row_number,
            )
        drivers["loss_timing_factor"] = loss_timing_factor
        interest_loss = _validated_derived_rate(
            customer_rate * risk_cost * loss_timing_factor,
            field="interest_loss_rate",
            analysis_kind=analysis_kind,
            row_number=row_number,
        )
        sources["interest_loss_rate"] = "derived_customer_risk_timing"
    else:
        if loss_timing_factor is not None:
            implied_interest_loss = _validated_derived_rate(
                customer_rate * risk_cost * loss_timing_factor,
                field="interest_loss_rate",
                analysis_kind=analysis_kind,
                row_number=row_number,
            )
            _reconcile_profit_rate(
                interest_loss,
                implied_interest_loss,
                field="interest_loss_rate",
                analysis_kind=analysis_kind,
                row_number=row_number,
            )
            drivers["loss_timing_factor"] = loss_timing_factor
            sources["interest_loss_rate"] = "explicit_reconciled_customer_risk_timing"
        else:
            sources["interest_loss_rate"] = "explicit"
    costs["interest_loss_rate"] = interest_loss

    revenue_share = _number(
        row, mapping, "revenue_share_rate", analysis_kind, row_number, rate=True
    )
    profit_share_ratio = _number(
        row, mapping, "profit_share_ratio", analysis_kind, row_number, rate=True
    )
    if revenue_share is None:
        if profit_share_ratio is None:
            raise RiskAnalysisError(
                f"I'm sorry.{row_number} Okay.revenue_share_rate The blogger adds:"
                "profit_share_ratio It must be provided.",
                analysis_kind=analysis_kind,
                field="revenue_share_rate",
                row_number=row_number,
            )
        drivers["profit_share_ratio"] = profit_share_ratio
        revenue_share = _validated_derived_rate(
            (customer_rate - interest_loss) * profit_share_ratio,
            field="revenue_share_rate",
            analysis_kind=analysis_kind,
            row_number=row_number,
        )
        sources["revenue_share_rate"] = "derived_net_interest_profit_share"
    else:
        if profit_share_ratio is not None:
            implied_revenue_share = _validated_derived_rate(
                (customer_rate - interest_loss) * profit_share_ratio,
                field="revenue_share_rate",
                analysis_kind=analysis_kind,
                row_number=row_number,
            )
            _reconcile_profit_rate(
                revenue_share,
                implied_revenue_share,
                field="revenue_share_rate",
                analysis_kind=analysis_kind,
                row_number=row_number,
            )
            drivers["profit_share_ratio"] = profit_share_ratio
            sources["revenue_share_rate"] = (
                "explicit_reconciled_net_interest_profit_share"
            )
        else:
            sources["revenue_share_rate"] = "explicit"
    costs["revenue_share_rate"] = revenue_share

    data_cost = _number(
        row, mapping, "data_cost_rate", analysis_kind, row_number, rate=True
    )
    if data_cost is None:
        data_cost, data_drivers = _derive_profitability_data_cost(
            row,
            mapping=mapping,
            analysis_kind=analysis_kind,
            row_number=row_number,
        )
        drivers.update(data_drivers)
        sources["data_cost_rate"] = "derived_application_funnel"
    else:
        data_driver_fields = (
            "per_application_cost",
            "credit_approval_rate",
            "draw_initiation_rate",
            "draw_approval_rate",
            "average_ticket",
            "data_annualization_factor",
        )
        if "stage_data_cost_source" not in mapping and _has_any_mapped_value(
            row, mapping, data_driver_fields
        ):
            implied_data_cost, data_drivers = _derive_profitability_data_cost(
                row,
                mapping=mapping,
                analysis_kind=analysis_kind,
                row_number=row_number,
            )
            _reconcile_profit_rate(
                data_cost,
                implied_data_cost,
                field="data_cost_rate",
                analysis_kind=analysis_kind,
                row_number=row_number,
            )
            drivers.update(data_drivers)
            sources["data_cost_rate"] = "explicit_reconciled_application_funnel"
        else:
            sources["data_cost_rate"] = "explicit"
    costs["data_cost_rate"] = data_cost

    tax_rate = _number(row, mapping, "tax_rate", analysis_kind, row_number, rate=True)
    if tax_rate is None:
        tax_method = _optional_text(row, mapping, "tax_method")
        if tax_method != "sample_net_revenue_vat_surcharge":
            raise RiskAnalysisError(
                f"I'm sorry.{row_number} Okay.tax_rate The blogger adds:tax_method I must."
                "sample_net_revenue_vat_surcharge.",
                analysis_kind=analysis_kind,
                field="tax_method",
                row_number=row_number,
            )
        tax_inclusive_divisor = _number(
            row,
            mapping,
            "tax_inclusive_divisor",
            analysis_kind,
            row_number,
            required=True,
            minimum=0.0,
            minimum_inclusive=False,
        )
        tax_combined_rate = _number(
            row,
            mapping,
            "tax_combined_rate",
            analysis_kind,
            row_number,
            required=True,
            rate=True,
        )
        assert tax_inclusive_divisor is not None and tax_combined_rate is not None
        drivers.update(
            {
                "tax_method": tax_method,
                "tax_inclusive_divisor": tax_inclusive_divisor,
                "tax_combined_rate": tax_combined_rate,
            }
        )
        tax_base = (
            customer_rate
            - interest_loss
            - revenue_share
            - costs["acquisition_cost_rate"]
            - data_cost
            - costs["payment_cost_rate"]
            - costs["collection_cost_rate"]
        )
        if tax_base < 0.0:
            raise RiskAnalysisError(
                f"I'm sorry.{row_number} Okay.sample_net_revenue_vat_surcharge "
                f"The tax base is being pushed.={tax_base},"
                "The tax base cannot be negative; please provide it in a visible formtax_rate Or check the cost calibration.",
                analysis_kind=analysis_kind,
                field="tax_rate",
                row_number=row_number,
            )
        tax_rate = _validated_derived_rate(
            tax_base / tax_inclusive_divisor * tax_combined_rate,
            field="tax_rate",
            analysis_kind=analysis_kind,
            row_number=row_number,
        )
        sources["tax_rate"] = "derived_sample_net_revenue_vat_surcharge"
    else:
        tax_driver_fields = (
            "tax_method",
            "tax_inclusive_divisor",
            "tax_combined_rate",
        )
        if _has_any_mapped_value(row, mapping, tax_driver_fields):
            tax_method = _optional_text(row, mapping, "tax_method")
            if tax_method != "sample_net_revenue_vat_surcharge":
                raise RiskAnalysisError(
                    f"I'm sorry.{row_number} Lines keep visible simultaneouslytax_rate The government has been working on the issue of the tax and tax drive."
                    "tax_method I must.sample_net_revenue_vat_surcharge.",
                    analysis_kind=analysis_kind,
                    field="tax_method",
                    row_number=row_number,
                )
            tax_inclusive_divisor = _number(
                row,
                mapping,
                "tax_inclusive_divisor",
                analysis_kind,
                row_number,
                required=True,
                minimum=0.0,
                minimum_inclusive=False,
            )
            tax_combined_rate = _number(
                row,
                mapping,
                "tax_combined_rate",
                analysis_kind,
                row_number,
                required=True,
                rate=True,
            )
            assert tax_inclusive_divisor is not None and tax_combined_rate is not None
            tax_base = (
                customer_rate
                - interest_loss
                - revenue_share
                - costs["acquisition_cost_rate"]
                - data_cost
                - costs["payment_cost_rate"]
                - costs["collection_cost_rate"]
            )
            if tax_base < 0.0:
                raise RiskAnalysisError(
                    f"I'm sorry.{row_number} Okay.sample_net_revenue_vat_surcharge "
                    f"The tax base is being pushed.={tax_base},The tax base cannot be negative.",
                    analysis_kind=analysis_kind,
                    field="tax_rate",
                    row_number=row_number,
                )
            implied_tax_rate = _validated_derived_rate(
                tax_base / tax_inclusive_divisor * tax_combined_rate,
                field="tax_rate",
                analysis_kind=analysis_kind,
                row_number=row_number,
            )
            _reconcile_profit_rate(
                tax_rate,
                implied_tax_rate,
                field="tax_rate",
                analysis_kind=analysis_kind,
                row_number=row_number,
            )
            drivers.update(
                {
                    "tax_method": tax_method,
                    "tax_inclusive_divisor": tax_inclusive_divisor,
                    "tax_combined_rate": tax_combined_rate,
                }
            )
            sources["tax_rate"] = "explicit_reconciled_sample_net_revenue_vat_surcharge"
        else:
            sources["tax_rate"] = "explicit"
    costs["tax_rate"] = tax_rate
    return costs, sources, drivers


def _collapse_vtg_balance_curves(
    data: pd.DataFrame,
    *,
    mapping: dict[str, str],
    analysis_kind: str,
) -> tuple[pd.DataFrame, dict[str, str], int]:
    """Collapse normalized long-form MOB balance curves to one row per cohort."""

    groups: dict[tuple[str, str, str, str, str, float | None, str], list[int]] = {}
    for position, row in data.iterrows():
        row_number = position + 1
        product = _required_text(row, mapping, "product", analysis_kind, row_number)
        cohort = _required_text(row, mapping, "cohort", analysis_kind, row_number)
        as_of_date = _required_text(
            row, mapping, "as_of_date", analysis_kind, row_number
        )
        scenario = _optional_text(row, mapping, "scenario") or "Benchmark"
        channel = _optional_text(row, mapping, "channel") or "Not provided"
        tenor_months = _number(
            row,
            mapping,
            "tenor_months",
            analysis_kind,
            row_number,
            minimum=0.0,
            minimum_inclusive=False,
        )
        selection_rule = _optional_text(row, mapping, "selection_rule") or "Not provided"
        groups.setdefault(
            (
                product,
                cohort,
                as_of_date,
                scenario,
                channel,
                tenor_months,
                selection_rule,
            ),
            [],
        ).append(position)

    curve_fields = {
        "mob",
        "mob_days",
        "mob_balance_rate",
        "mob_balance_amount",
    }
    group_level_fields = (
        *_VTG_REQUIRED,
        *_VTG_OPTIONAL_RATES,
        *_VTG_OPTIONAL_NONNEGATIVE,
        *_VTG_OPTIONAL_GROUP_TEXT,
        "previous_turnover",
        "terminal_method",
        "tenor_months",
        "day_count_basis",
    )
    turnover_column = _unused_column_name(data, "__derived_turnover")
    avg_balance_column = _unused_column_name(data, "__derived_avg_daily_balance")
    balance_source_column = _unused_column_name(data, "__mob_balance_source")
    collapsed_rows: list[pd.Series] = []
    zero_disbursement_skipped_count = 0

    for (
        product,
        cohort,
        as_of_date,
        scenario,
        channel,
        tenor_months,
        selection_rule,
    ), positions in groups.items():
        identity = (
            f"Products{product} / cohort {cohort} / As at{as_of_date} / scene{scenario} / "
            f"Channels{channel} / Duration{tenor_months or 'Not provided'} / Filter{selection_rule}"
        )
        group = data.loc[positions]
        for field in group_level_fields:
            if field in curve_fields or field not in mapping:
                continue
            source = mapping[field]
            tokens = {_consistency_token(value) for value in group[source].tolist()}
            if len(tokens) != 1:
                raise RiskAnalysisError(
                    f"{identity} It's...{field} Yes.MOB There must be consistency between curve lines.",
                    analysis_kind=analysis_kind,
                    field=field,
                    row_number=positions[0] + 1,
                )

        first_position = positions[0]
        first_row = data.loc[first_position]
        disbursement = _number(
            first_row,
            mapping,
            "disbursement_amount",
            analysis_kind,
            first_position + 1,
            required=True,
            minimum=0.0,
        )
        day_count_basis = _number(
            first_row,
            mapping,
            "day_count_basis",
            analysis_kind,
            first_position + 1,
            required=True,
            minimum=0.0,
            minimum_inclusive=False,
        )
        assert disbursement is not None and day_count_basis is not None
        if disbursement == 0.0:
            zero_disbursement_skipped_count += len(positions)
            continue
        seen_mobs: set[tuple[str, Any]] = set()
        balance_sources: set[str] = set()
        weighted_balance_days = 0.0
        total_mob_days = 0.0
        for position in positions:
            row = data.loc[position]
            row_number = position + 1
            mob_source = mapping["mob"]
            raw_mob = row[mob_source]
            if _is_missing(raw_mob) or not str(raw_mob).strip():
                raise RiskAnalysisError(
                    f"I'm sorry.{row_number} Okay.mob Can't be empty.",
                    analysis_kind=analysis_kind,
                    field="mob",
                    row_number=row_number,
                )
            mob_token = _consistency_token(raw_mob)
            if mob_token in seen_mobs:
                raise RiskAnalysisError(
                    f"{identity} It's...mob It has to be the only duplicate value found.{raw_mob!r}.",
                    analysis_kind=analysis_kind,
                    field="mob",
                    row_number=row_number,
                )
            seen_mobs.add(mob_token)
            mob_days = _number(
                row,
                mapping,
                "mob_days",
                analysis_kind,
                row_number,
                required=True,
                minimum=0.0,
                minimum_inclusive=False,
            )
            total_mob_days += mob_days
            balance_amount = _number(
                row,
                mapping,
                "mob_balance_amount",
                analysis_kind,
                row_number,
                minimum=0.0,
            )
            balance_rate = _number(
                row,
                mapping,
                "mob_balance_rate",
                analysis_kind,
                row_number,
                rate=True,
            )
            if balance_amount is None and balance_rate is None:
                raise RiskAnalysisError(
                    f"I'm sorry.{row_number} Okay.mob_balance_amount and"
                    "mob_balance_rate At least one can't be empty.",
                    analysis_kind=analysis_kind,
                    field="mob_balance_rate",
                    row_number=row_number,
                )
            if balance_amount is not None and balance_rate is not None:
                implied_balance_amount = disbursement * balance_rate
                if not math.isclose(
                    balance_amount,
                    implied_balance_amount,
                    rel_tol=_VTG_BALANCE_RECONCILIATION_REL_TOLERANCE,
                    abs_tol=_VTG_BALANCE_RECONCILIATION_ABS_TOLERANCE,
                ):
                    raise RiskAnalysisError(
                        f"I'm sorry.{row_number} Okay.mob_balance_amount={balance_amount} "
                        "anddisbursement_amount × mob_balance_rate="
                        f"{implied_balance_amount} Inconsistent.",
                        analysis_kind=analysis_kind,
                        field="mob_balance_amount",
                        row_number=row_number,
                    )
                balance_sources.add("mob_balance_amount_reconciled_with_rate")
            elif balance_amount is not None:
                balance_sources.add("mob_balance_amount")
            else:
                assert balance_rate is not None
                balance_amount = disbursement * balance_rate
                balance_sources.add("mob_balance_rate")
            weighted_balance_days += balance_amount * mob_days

        if abs(total_mob_days - day_count_basis) > _VTG_CURVE_DAY_TOLERANCE:
            raise RiskAnalysisError(
                f"{identity} It's...mob_days Total"
                f"{total_mob_days:.8f},It must be equal today_count_basis={day_count_basis:g}.",
                analysis_kind=analysis_kind,
                field="mob_days",
                row_number=first_position + 1,
            )

        avg_daily_balance = weighted_balance_days / day_count_basis
        if avg_daily_balance <= 0.0:
            raise RiskAnalysisError(
                f"{identity} It's...MOB The average daily balance of the balance curve must be greater than zero.",
                analysis_kind=analysis_kind,
                field=(
                    "mob_balance_amount"
                    if "mob_balance_amount" in mapping
                    and "mob_balance_rate" not in mapping
                    else "mob_balance_rate"
                ),
                row_number=first_position + 1,
            )
        supplied_avg_daily_balance = _number(
            first_row,
            mapping,
            "avg_daily_balance",
            analysis_kind,
            first_position + 1,
            minimum=0.0,
        )
        if supplied_avg_daily_balance is not None and not math.isclose(
            supplied_avg_daily_balance,
            avg_daily_balance,
            rel_tol=_VTG_BALANCE_RECONCILIATION_REL_TOLERANCE,
            abs_tol=_VTG_BALANCE_RECONCILIATION_ABS_TOLERANCE,
        ):
            raise RiskAnalysisError(
                f"{identity} Visibleavg_daily_balance={supplied_avg_daily_balance} and"
                f"MOB Curved extrapolation value={avg_daily_balance} Inconsistent.",
                analysis_kind=analysis_kind,
                field="avg_daily_balance",
                row_number=first_position + 1,
            )
        collapsed = first_row.copy()
        collapsed[turnover_column] = disbursement / avg_daily_balance
        collapsed[avg_balance_column] = avg_daily_balance
        balance_source = (
            next(iter(balance_sources))
            if len(balance_sources) == 1
            else "mixed(" + ",".join(sorted(balance_sources)) + ")"
        )
        collapsed[balance_source_column] = (
            f"{balance_source}_reconciled_with_explicit_avg"
            if supplied_avg_daily_balance is not None
            else balance_source
        )
        collapsed_rows.append(collapsed)

    working_mapping = dict(mapping)
    working_mapping["turnover"] = turnover_column
    working_mapping["avg_daily_balance"] = avg_balance_column
    working_mapping["mob_balance_source"] = balance_source_column
    return (
        pd.DataFrame(collapsed_rows).reset_index(drop=True),
        working_mapping,
        zero_disbursement_skipped_count,
    )


def _vtg_product_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    slice_keys = list(
        dict.fromkeys(
            (
                row["product"],
                row["as_of_date"],
                row.get("scenario") or "Benchmark",
                row.get("channel") or "Not provided",
                row.get("tenor_months"),
                row.get("selection_rule") or "Not provided",
            )
            for row in rows
        )
    )
    for (
        product,
        as_of_date,
        scenario,
        channel,
        tenor_months,
        selection_rule,
    ) in slice_keys:
        product_rows = [
            row
            for row in rows
            if (
                row["product"],
                row["as_of_date"],
                row.get("scenario") or "Benchmark",
                row.get("channel") or "Not provided",
                row.get("tenor_months"),
                row.get("selection_rule") or "Not provided",
            )
            == (
                product,
                as_of_date,
                scenario,
                channel,
                tenor_months,
                selection_rule,
            )
        ]
        disbursement = sum(row["disbursement_amount"] for row in product_rows)
        avg_balance = sum(row["avg_daily_balance"] for row in product_rows)
        terminal_loss = sum(
            row["terminal_bad_rate"] * row["disbursement_amount"]
            for row in product_rows
        )
        observed_loss = sum(
            row["mob14_bad_rate"] * row["disbursement_amount"] for row in product_rows
        )
        result.append(
            {
                "product": product,
                "as_of_date": as_of_date,
                "scenario": scenario,
                "channel": channel,
                "tenor_months": tenor_months,
                "selection_rule": selection_rule,
                "amount_unit": product_rows[0]["amount_unit"],
                "row_count": len(product_rows),
                "disbursement_amount": disbursement,
                "avg_daily_balance": avg_balance,
                "turnover": _safe_ratio(disbursement, avg_balance),
                "mob14_bad_rate": _safe_ratio(observed_loss, disbursement),
                "terminal_bad_rate": _safe_ratio(terminal_loss, disbursement),
                "observed_annualized_bad_rate": _safe_ratio(observed_loss, avg_balance),
                "annualized_bad_rate": _safe_ratio(terminal_loss, avg_balance),
            }
        )
    return result


def _profit_product_summaries(
    rows: list[dict[str, Any]],
    *,
    analysis_kind: str,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    weighted_fields = (
        "customer_rate",
        *_PROFIT_COST_FIELDS,
        "fixed_income_yield",
        "total_cost_rate",
        "net_yield",
    )
    group_keys = list(
        dict.fromkeys(
            (
                row["product"],
                row.get("as_of_period") or "Not provided",
                row.get("scenario") or "Benchmark",
            )
            for row in rows
        )
    )
    for product, as_of_period, scenario in group_keys:
        product_rows = [
            row
            for row in rows
            if (
                row["product"],
                row.get("as_of_period") or "Not provided",
                row.get("scenario") or "Benchmark",
            )
            == (product, as_of_period, scenario)
        ]
        weight_sum = sum(row["weight"] for row in product_rows)
        if abs(weight_sum - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise RiskAnalysisError(
                f"Products{product} / Period{as_of_period} / scene{scenario} It's...weight "
                f"Total{weight_sum:.8f},Must be about 1.",
                analysis_kind=analysis_kind,
                field="weight",
            )
        amount_units = {
            row["amount_unit"]
            for row in product_rows
            if row.get("amount_unit") is not None
        }
        if len(amount_units) > 1:
            raise RiskAnalysisError(
                f"Products{product} / Period{as_of_period} / scene{scenario} It's..."
                "Original data cost driveramount_unit It must be consistent, in practice:"
                + ",".join(sorted(amount_units))
                + ".",
                analysis_kind=analysis_kind,
                field="amount_unit",
            )
        summary: dict[str, Any] = {
            "product": product,
            "as_of_period": as_of_period,
            "scenario": scenario,
            "weight_basis": "average_balance",
            "amount_unit": next(iter(amount_units), None),
            "asset_class_count": len({row["asset_class"] for row in product_rows}),
            "weight_sum": weight_sum,
        }
        for field in weighted_fields:
            summary[field] = sum(row[field] * row["weight"] for row in product_rows)
        summaries.append(summary)
    return summaries


def _profit_slice_identity(row: dict[str, Any]) -> str:
    return (
        f"Products{row['product']} / Period{row.get('as_of_period') or 'Not provided'} / "
        f"scene{row.get('scenario') or 'Benchmark'}"
    )


def _normalized_frame(frame: pd.DataFrame, *, analysis_kind: str) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise RiskAnalysisError(
            "The risk analysis input must be tabular.", analysis_kind=analysis_kind
        )
    if frame.empty:
        raise RiskAnalysisError("Risk analysis data are empty.", analysis_kind=analysis_kind)
    return frame.reset_index(drop=True)


def _normalize_column_map(
    frame: pd.DataFrame,
    column_map: dict[str, str],
    *,
    analysis_kind: str,
) -> dict[str, str]:
    if not isinstance(column_map, dict) or not column_map:
        raise RiskAnalysisError(
            "column_map It must be non-empty.", analysis_kind=analysis_kind
        )
    normalized: dict[str, str] = {}
    source_owners: dict[str, str] = {}
    for raw_canonical, raw_source in column_map.items():
        canonical = str(raw_canonical or "").strip()
        source = str(raw_source or "").strip()
        if not canonical or not source:
            raise RiskAnalysisError(
                "column_map It's...canonical andsource It can't be empty.",
                analysis_kind=analysis_kind,
            )
        if source not in frame.columns:
            raise RiskAnalysisError(
                f"column_map Point to an absent column: {canonical} -> {source}",
                analysis_kind=analysis_kind,
                field=canonical,
            )
        if list(frame.columns).count(source) != 1:
            raise RiskAnalysisError(
                f"Source data is listed repeatedly and cannot be safely mapped: {source}",
                analysis_kind=analysis_kind,
                field=canonical,
            )
        if source in source_owners:
            raise RiskAnalysisError(
                "The same source column cannot map to multiple business fields: "
                f"{source_owners[source]} and{canonical} -> {source}",
                analysis_kind=analysis_kind,
                field=canonical,
            )
        source_owners[source] = canonical
        normalized[canonical] = source
    return normalized


def _require_mappings(
    mapping: dict[str, str],
    required: Iterable[str],
    *,
    analysis_kind: str,
) -> None:
    missing = [field for field in required if field not in mapping]
    if missing:
        raise RiskAnalysisError(
            "column_map Required Fields Missing: " + ", ".join(missing),
            analysis_kind=analysis_kind,
            field=missing[0],
        )


def _required_text(
    row: pd.Series,
    mapping: dict[str, str],
    field: str,
    analysis_kind: str,
    row_number: int,
) -> str:
    source = mapping[field]
    value = row[source]
    if _is_missing(value) or not str(value).strip():
        raise RiskAnalysisError(
            f"I'm sorry.{row_number} Okay.{field} Can't be empty.",
            analysis_kind=analysis_kind,
            field=field,
            row_number=row_number,
        )
    return str(value).strip()


def _optional_text(
    row: pd.Series,
    mapping: dict[str, str],
    field: str,
) -> str | None:
    source = mapping.get(field)
    if source is None:
        return None
    value = row[source]
    if _is_missing(value) or not str(value).strip():
        return None
    return str(value).strip()


def _number(
    row: pd.Series,
    mapping: dict[str, str],
    field: str,
    analysis_kind: str,
    row_number: int,
    *,
    required: bool = False,
    rate: bool = False,
    minimum: float | None = None,
    minimum_inclusive: bool = True,
) -> float | None:
    source = mapping.get(field)
    if source is None:
        if required:
            raise RiskAnalysisError(
                f"column_map Required Fields Missing: {field}",
                analysis_kind=analysis_kind,
                field=field,
                row_number=row_number,
            )
        return None
    value = row[source]
    if _is_missing(value):
        if required:
            raise RiskAnalysisError(
                f"I'm sorry.{row_number} Okay.{field} Can't be empty.",
                analysis_kind=analysis_kind,
                field=field,
                row_number=row_number,
            )
        return None
    if isinstance(value, bool):
        raise RiskAnalysisError(
            f"I'm sorry.{row_number} Okay.{field} It must be a value, not a boolean value.",
            analysis_kind=analysis_kind,
            field=field,
            row_number=row_number,
        )
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RiskAnalysisError(
            f"I'm sorry.{row_number} Okay.{field} Not valid: {value!r}",
            analysis_kind=analysis_kind,
            field=field,
            row_number=row_number,
        ) from exc
    if not math.isfinite(number):
        raise RiskAnalysisError(
            f"I'm sorry.{row_number} Okay.{field} It must be limited.",
            analysis_kind=analysis_kind,
            field=field,
            row_number=row_number,
        )
    if rate and not 0.0 <= number <= 1.0:
        raise RiskAnalysisError(
            f"I'm sorry.{row_number} Okay.{field}={number},Rate must be[0, 1].",
            analysis_kind=analysis_kind,
            field=field,
            row_number=row_number,
        )
    if minimum is not None:
        invalid = number < minimum if minimum_inclusive else number <= minimum
        if invalid:
            comparator = ">=" if minimum_inclusive else ">"
            raise RiskAnalysisError(
                f"I'm sorry.{row_number} Okay.{field}={number},I have to.{comparator} {minimum}.",
                analysis_kind=analysis_kind,
                field=field,
                row_number=row_number,
            )
    return number


def _is_missing(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _consistency_token(value: Any) -> tuple[str, Any]:
    if _is_missing(value):
        return ("missing", None)
    if isinstance(value, bool):
        return ("bool", value)
    if not isinstance(value, str):
        try:
            number = float(value)
        except (TypeError, ValueError):
            pass
        else:
            if math.isfinite(number):
                return ("number", number)
    return ("text", str(value).strip())


def _unused_column_name(frame: pd.DataFrame, base: str) -> str:
    name = base
    suffix = 1
    while name in frame.columns:
        name = f"{base}_{suffix}"
        suffix += 1
    return name


def _validated_derived_rate(
    value: float,
    *,
    field: str,
    analysis_kind: str,
    row_number: int,
) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise RiskAnalysisError(
            f"I'm sorry.{row_number} Lines can be extrapolated{field}={number},Rate must be[0, 1].",
            analysis_kind=analysis_kind,
            field=field,
            row_number=row_number,
        )
    return number


def _format_value_set(values: Iterable[Any], *, percent: bool = False) -> str:
    unique: list[Any] = []
    seen: set[tuple[str, Any]] = set()
    for value in values:
        token = _consistency_token(value)
        if token in seen:
            continue
        seen.add(token)
        unique.append(value)
    rendered = [
        _format_percent(float(value)) if percent else f"{float(value):g}"
        for value in unique[:8]
    ]
    if len(unique) > 8:
        rendered.append(f"Other{len(unique) - 8} Number")
    return ",".join(rendered) if rendered else "Not provided"


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    return float(numerator / denominator) if denominator > 0.0 else None


def _ordered_unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values))


def _period_scope(values: Iterable[str]) -> str:
    periods = sorted(
        {
            str(value).strip()
            for value in values
            if value is not None and str(value).strip()
        }
    )
    if not periods:
        return "Not provided"
    if len(periods) == 1:
        return _bounded_text(periods[0], AS_OF_PERIOD_MAX_CHARS)
    return _bounded_text(f"{periods[0]} ~ {periods[-1]}", AS_OF_PERIOD_MAX_CHARS)


def _product_scope(values: Iterable[str]) -> list[str]:
    return [
        _bounded_text(value, PRODUCT_SCOPE_ITEM_MAX_CHARS)
        for value in _ordered_unique(values)[:PRODUCT_SCOPE_LIMIT]
    ]


def _bounded_text(value: str, max_chars: int) -> str:
    text = str(value).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def _unique_strings(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _format_percent(value: float) -> str:
    return f"{float(value):.2%}"


def _format_change(value: float) -> str:
    direction = "Up" if value >= 0.0 else "Down"
    return f"{direction} {abs(float(value)) * 100:.2f} Percentage"


__all__ = [
    "ANALYSIS_KINDS",
    "PRODUCT_SCOPE_LIMIT",
    "WEIGHT_SUM_TOLERANCE",
    "RiskAnalysisCalculation",
    "RiskAnalysisError",
    "calculate_profitability",
    "calculate_risk_analysis",
    "calculate_vtg_terminal",
]
