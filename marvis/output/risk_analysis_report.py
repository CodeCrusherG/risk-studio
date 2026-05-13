"""Excel renderer for deterministic VTG-terminal and profitability results.

This module is intentionally presentation-only: every number arrives through
``RiskAnalysisReportPayload``.  Calculation and validation remain in the builtin
``risk_analysis`` pack so the workbook cannot silently diverge from tool output.
"""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from marvis.output.styles import FONT_NAME
from marvis.spreadsheet_safety import safe_xlsx_text


RISK_ANALYSIS_REPORT_SHEETS = ["Summary of conclusions", "Detailed results", "caliber and assumptions", "Data quality"]

_TITLE_FILL = "163A5F"
_SECTION_FILL = "D9EAF7"
_HEADER_FILL = "1F4E78"
_HEADER_FONT = "FFFFFF"
_WARN_FILL = "FFF2CC"
_FAIL_FILL = "F4CCCC"
_PASS_FILL = "D9EAD3"
_BORDER_COLOR = "C9D2DC"

_ANALYSIS_LABELS = {
    "vtg_terminal": "VTG End and year-old bad measurements",
    "profitability": "Proceeds measure",
}

_LABELS = {
    "product": "Products",
    "cohort": "Cohort",
    "asset_class": "Asset class",
    "as_of_period": "Data period",
    "as_of_date": "Data intersection",
    "scenario": "scene",
    "amount_unit": "Amount units",
    "row_count": "Lines",
    "asset_class_count": "Number of asset classes",
    "analysis_slice_count": "Analyse the number of slices",
    "product_count": "Number of products",
    "cohort_count": "Cohort Number",
    "negative_product_count": "Number of products with negative net gain",
    "disbursement_amount": "Amount released",
    "total_disbursement_amount": "Total amount released",
    "avg_daily_balance": "Average balance per day",
    "total_avg_daily_balance": "Total average balance per day",
    "turnover": "Number of turnovers",
    "day_count_basis": "Annual Days Base",
    "mob_days": "MOB Days",
    "mob_balance_rate": "MOB Average daily balance rate",
    "mob_balance_amount": "MOB Average daily balance amount",
    "portfolio_turnover": "Group turnover times",
    "mob14_bad_rate": "MOB14 Bad rate",
    "weighted_mob14_bad_rate": "WeightedMOB14 Bad rate",
    "terminal_bad_rate": "End-value bad rate",
    "weighted_terminal_bad_rate": "Weighted end value bad rate",
    "terminal_bad_rate_source": "End Source",
    "terminal_method": "End-of-value method",
    "auxiliary_terminal_bad_rate": "Assisted end-of-life rate",
    "observed_annualized_bad_rate": "Observe annual downscaling rate",
    "annualized_bad_rate": "Annualized under-representation rate",
    "highest_annualized_bad_rate": "Highest annualized rate of under-representation",
    "highest_annualized_product": "Top year bad products",
    "highest_annualized_cohort": "Highest ageCohort",
    "long_term_recovery_rate": "Long-term recovery rate",
    "supplied_long_term_recovery_rate": "Enter long-term recovery rate",
    "realized_long_term_recovery_rate": "Achieve long-term recovery rates",
    "previous_mob14_bad_rate": "Prior periodMOB14 Bad rate",
    "previous_terminal_bad_rate": "Disadvantage rate at end of prior period",
    "previous_turnover": "Prior period turnover",
    "previous_turnover_source": "Prior period turnover sources",
    "previous_annualized_bad_rate": "Prior-period annualized downscaling rate",
    "previous_annualized_bad_rate_source": "Sources of previous year-end malformation",
    "previous_disbursement_amount": "Amount of prior period ' s loan",
    "previous_avg_daily_balance": "Average balance at prior period",
    "annualized_bad_rate_change": "Change in annualized bad rate",
    "weight": "Weights",
    "weight_basis": "Weight caliber",
    "weight_sum": "Total weightings",
    "customer_rate": "Interest rate on clients",
    "terminal_vintage_rate": "End valueVintage Rate",
    "risk_turnover": "Risk turnover",
    "loss_timing_factor": "Time factor for loss",
    "profit_share_ratio": "Contract share",
    "customer_stage_count": "Number of client phases",
    "transaction_weight_sum": "Total trade weights at stage",
    "customer_stage_provenance": "Client phase calculation retroactive",
    "per_application_cost": "Single application cost",
    "credit_approval_rate": "Pass rate",
    "draw_initiation_rate": "Startup rate with letters",
    "draw_approval_rate": "Passage rate",
    "average_ticket": "Average value of items",
    "data_annualization_factor": "Data cost annualization factor",
    "tax_method": "Tax and excise methodology",
    "tax_inclusive_divisor": "Including tax division",
    "tax_combined_rate": "Combined tax rates",
    "interest_loss_rate": "Rate of loss of interest",
    "interest_loss_rate_source": "Source of interest loss",
    "revenue_share_rate": "Rates of depreciation",
    "risk_cost_rate": "Risk cost rate",
    "risk_cost_rate_source": "Source of risk costs",
    "acquisition_cost_rate": "Cost-of-takers rate",
    "acquisition_cost_rate_source": "Source of cost of the customer",
    "data_cost_rate": "Data cost rate",
    "data_cost_rate_source": "Data cost sources",
    "payment_cost_rate": "Cost of payment",
    "collection_cost_rate": "Routine cost",
    "funding_cost_rate": "Cost of funds",
    "other_cost_rate": "Other cost rates",
    "tax_rate": "Tax rate",
    "tax_rate_source": "Source of taxes and fees",
    "fixed_income_yield": "Class solid harvest rate of return",
    "total_cost_rate": "Total cost rate",
    "net_yield": "Net rate of return",
    "lowest_net_yield": "Minimum net rate of return",
    "lowest_net_yield_product": "Minimum net revenue product",
    "lowest_net_yield_as_of_period": "Minimum net gain period",
    "lowest_net_yield_scenario": "Minimum net proceeds scenario",
    "highest_net_yield": "Maximum net return",
    "highest_net_yield_product": "Top net revenue product",
    "highest_net_yield_as_of_period": "Period of maximum net gain",
    "highest_net_yield_scenario": "Top net proceeds scenario",
    "max_cost_rate": "Maximum cost rate",
    "max_cost_component": "Maximum Cost Item",
    "max_cost_product": "Maximum cost product",
    "max_cost_as_of_period": "Maximum cost period",
    "max_cost_scenario": "Maximum Cost scene",
    "largest_scenario_net_yield_spread": "Maximum net gain on scene",
    "largest_scenario_net_yield_spread_product": "Max. scenario differential product",
    "largest_scenario_net_yield_spread_as_of_period": "Maximum scenario duration",
    "largest_scenario_net_yield_spread_high_scenario": "High net revenue scenario",
    "largest_scenario_net_yield_spread_low_scenario": "Low net revenue scenario",
}


@dataclass(frozen=True)
class RiskAnalysisReportPayload:
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
    detail_rows: list[dict[str, Any]] = field(default_factory=list)
    summary_rows: list[dict[str, Any]] = field(default_factory=list)
    formula_definitions: list[dict[str, str]] = field(default_factory=list)
    data_quality: list[dict[str, str]] = field(default_factory=list)


def render_risk_analysis_report(
    payload: RiskAnalysisReportPayload,
    out_path: Path,
) -> Path:
    """Render a calculation payload to ``out_path`` without recalculation."""

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    workbook.remove(workbook.active)
    workbook.properties.title = _ANALYSIS_LABELS.get(
        payload.analysis_kind, payload.analysis_kind
    )
    workbook.properties.subject = "Risk Studio A definitive risk analysis statement"
    _write_conclusions(workbook, payload)
    _write_details(workbook, payload)
    _write_assumptions(workbook, payload)
    _write_data_quality(workbook, payload)
    workbook.save(out_path)
    return out_path


def _write_conclusions(workbook: Workbook, payload: RiskAnalysisReportPayload) -> None:
    sheet = workbook.create_sheet("Summary of conclusions")
    _prepare_sheet(sheet)
    sheet.merge_cells("A1:D1")
    title = _ANALYSIS_LABELS.get(payload.analysis_kind, payload.analysis_kind)
    sheet["A1"] = f"{title}Report"
    _style_title(sheet["A1"])
    sheet["A2"] = "Analysis Type"
    sheet["B2"] = title
    sheet["C2"] = "Source data rows"
    sheet["D2"] = payload.source_row_count
    sheet["A3"] = "Product range"
    sheet["B3"] = _safe_excel_text(",".join(payload.product_scope) or "Not provided")
    sheet["C3"] = "Data period"
    sheet["D3"] = _cell_value(payload.as_of_period)
    sheet["A4"] = "Number of result lines"
    sheet["B4"] = payload.row_count
    for cell in (
        sheet["A2"],
        sheet["C2"],
        sheet["A3"],
        sheet["C3"],
        sheet["A4"],
    ):
        cell.font = Font(name=FONT_NAME, bold=True, color="334155")
        cell.fill = PatternFill("solid", fgColor=_SECTION_FILL)

    row = 5
    row = _write_section_title(sheet, row, "Core indicators")
    sheet.cell(row=row, column=1, value="Indicators")
    sheet.cell(row=row, column=2, value="Value")
    _style_header_row(sheet, row, 2)
    for key, value in payload.headline_metrics.items():
        row += 1
        sheet.cell(row=row, column=1, value=_label(key))
        value_cell = sheet.cell(row=row, column=2, value=_cell_value(value))
        _apply_number_format(value_cell, key)

    row += 2
    row = _write_section_title(sheet, row, "Key findings")
    for index, point in enumerate(payload.key_points, start=1):
        sheet.cell(row=row, column=1, value=index)
        sheet.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        sheet.cell(row=row, column=2, value=_cell_value(point))
        sheet.cell(row=row, column=2).alignment = Alignment(
            wrap_text=True, vertical="top"
        )
        row += 1

    row += 1
    row = _write_section_title(sheet, row, "Risk tip")
    flags = payload.red_flags or ["No red flags were found for operations or data quality that required separate alerts."]
    for index, flag in enumerate(flags, start=1):
        sheet.cell(row=row, column=1, value=index)
        sheet.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        cell = sheet.cell(row=row, column=2, value=_cell_value(flag))
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        if payload.red_flags:
            cell.fill = PatternFill("solid", fgColor=_WARN_FILL)
        row += 1

    sheet.freeze_panes = "A5"
    sheet.column_dimensions["A"].width = 25
    sheet.column_dimensions["B"].width = 34
    sheet.column_dimensions["C"].width = 22
    sheet.column_dimensions["D"].width = 24
    _style_used_range(sheet)


def _write_details(workbook: Workbook, payload: RiskAnalysisReportPayload) -> None:
    sheet = workbook.create_sheet("Detailed results")
    _prepare_sheet(sheet)
    sheet.merge_cells("A1:F1")
    sheet["A1"] = "Product summary"
    _style_title(sheet["A1"])
    row = 3
    row = _write_dict_table(sheet, payload.summary_rows, start_row=row)
    row += 2
    sheet.cell(row=row, column=1, value="Line-by-line result")
    _style_section_cell(sheet.cell(row=row, column=1))
    detail_header_row = row + 1
    detail_end_row = _write_dict_table(
        sheet, payload.detail_rows, start_row=detail_header_row
    )
    if payload.detail_rows:
        last_col = get_column_letter(len(_headers(payload.detail_rows)))
        sheet.auto_filter.ref = f"A{detail_header_row}:{last_col}{detail_end_row - 1}"
        sheet.freeze_panes = f"A{detail_header_row + 1}"
        _add_negative_yield_rules(
            sheet, payload.detail_rows, detail_header_row, detail_end_row - 1
        )
    else:
        sheet.freeze_panes = "A3"
    _autofit_columns(sheet)
    _style_used_range(sheet)


def _write_assumptions(workbook: Workbook, payload: RiskAnalysisReportPayload) -> None:
    sheet = workbook.create_sheet("caliber and assumptions")
    _prepare_sheet(sheet)
    sheet.merge_cells("A1:D1")
    sheet["A1"] = "Field mapping, calibration and assumptions"
    _style_title(sheet["A1"])
    headers = ["Category", "Item", "Formula/Source", "Annotations"]
    for column, header in enumerate(headers, start=1):
        sheet.cell(row=3, column=column, value=header)
    _style_header_row(sheet, 3, len(headers))
    row = 4
    for canonical, source in payload.column_map.items():
        sheet.append(
            [
                "Field Map",
                _cell_value(canonical),
                _cell_value(source),
                _cell_value(f"{_label(canonical)} <- {source}"),
            ]
        )
        row += 1
    for item in payload.formula_definitions:
        sheet.append(
            [
                "Formula",
                _cell_value(item.get("metric")),
                _cell_value(item.get("formula")),
                _cell_value(item.get("note")),
            ]
        )
        row += 1
    for index, assumption in enumerate(payload.assumptions, start=1):
        sheet.append(["Operational assumptions", f"Assumptions{index}", "", _cell_value(assumption)])
        row += 1
    sheet.auto_filter.ref = f"A3:D{max(3, row - 1)}"
    sheet.freeze_panes = "A4"
    sheet.column_dimensions["A"].width = 14
    sheet.column_dimensions["B"].width = 28
    sheet.column_dimensions["C"].width = 58
    sheet.column_dimensions["D"].width = 62
    _style_used_range(sheet)


def _write_data_quality(workbook: Workbook, payload: RiskAnalysisReportPayload) -> None:
    sheet = workbook.create_sheet("Data quality")
    _prepare_sheet(sheet)
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "Data quality checks and red flags of operations"
    _style_title(sheet["A1"])
    for column, header in enumerate(("Status", "Checkpoint", "Results statement"), start=1):
        sheet.cell(row=3, column=column, value=header)
    _style_header_row(sheet, 3, 3)
    row = 4
    for check in payload.data_quality:
        status = str(check.get("status") or "PASS").upper()
        sheet.cell(row=row, column=1, value=status)
        sheet.cell(row=row, column=2, value=_cell_value(check.get("check")))
        sheet.cell(row=row, column=3, value=_cell_value(check.get("detail")))
        _style_status_cell(sheet.cell(row=row, column=1), status)
        row += 1
    if payload.red_flags:
        for flag in payload.red_flags:
            sheet.cell(row=row, column=1, value="WARN")
            sheet.cell(row=row, column=2, value="Red flag for operations")
            sheet.cell(row=row, column=3, value=_cell_value(flag))
            _style_status_cell(sheet.cell(row=row, column=1), "WARN")
            row += 1
    else:
        sheet.cell(row=row, column=1, value="PASS")
        sheet.cell(row=row, column=2, value="Red flag for operations")
        sheet.cell(row=row, column=3, value="Not found.")
        _style_status_cell(sheet.cell(row=row, column=1), "PASS")
        row += 1
    sheet.auto_filter.ref = f"A3:C{row - 1}"
    sheet.freeze_panes = "A4"
    sheet.column_dimensions["A"].width = 12
    sheet.column_dimensions["B"].width = 28
    sheet.column_dimensions["C"].width = 86
    _style_used_range(sheet)


def _write_dict_table(sheet, rows: list[dict[str, Any]], *, start_row: int) -> int:
    if not rows:
        sheet.cell(row=start_row, column=1, value="No data available")
        return start_row + 1
    headers = _headers(rows)
    for column, key in enumerate(headers, start=1):
        sheet.cell(row=start_row, column=column, value=_label(key))
    _style_header_row(sheet, start_row, len(headers))
    row_index = start_row + 1
    for item in rows:
        for column, key in enumerate(headers, start=1):
            cell = sheet.cell(
                row=row_index, column=column, value=_cell_value(item.get(key))
            )
            _apply_number_format(cell, key)
        row_index += 1
    return row_index


def _headers(rows: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for row in rows:
        for key in row:
            if key not in result:
                result.append(key)
    return result


def _prepare_sheet(sheet) -> None:
    sheet.sheet_view.showGridLines = False
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0


def _style_title(cell) -> None:
    cell.fill = PatternFill("solid", fgColor=_TITLE_FILL)
    cell.font = Font(name=FONT_NAME, size=14, bold=True, color="FFFFFF")
    cell.alignment = Alignment(horizontal="left", vertical="center")
    cell.parent.row_dimensions[cell.row].height = 28


def _style_section_cell(cell) -> None:
    cell.fill = PatternFill("solid", fgColor=_SECTION_FILL)
    cell.font = Font(name=FONT_NAME, bold=True, color="1F2937")


def _write_section_title(sheet, row: int, title: str) -> int:
    sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    cell = sheet.cell(row=row, column=1, value=title)
    _style_section_cell(cell)
    return row + 1


def _style_header_row(sheet, row: int, column_count: int) -> None:
    for column in range(1, column_count + 1):
        cell = sheet.cell(row=row, column=column)
        cell.fill = PatternFill("solid", fgColor=_HEADER_FILL)
        cell.font = Font(name=FONT_NAME, bold=True, color=_HEADER_FONT)
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        cell.border = Border(bottom=Side(style="thin", color=_BORDER_COLOR))
    sheet.row_dimensions[row].height = 24


def _style_status_cell(cell, status: str) -> None:
    fill = (
        _PASS_FILL
        if status == "PASS"
        else _FAIL_FILL
        if status == "FAIL"
        else _WARN_FILL
    )
    cell.fill = PatternFill("solid", fgColor=fill)
    cell.font = Font(name=FONT_NAME, bold=True)
    cell.alignment = Alignment(horizontal="center")


def _style_used_range(sheet) -> None:
    thin = Side(style="hair", color=_BORDER_COLOR)
    for row in sheet.iter_rows(
        min_row=1,
        max_row=max(1, sheet.max_row),
        min_col=1,
        max_col=max(1, sheet.max_column),
    ):
        for cell in row:
            if cell.value is None:
                continue
            if cell.row != 1 and cell.font == Font():
                cell.font = Font(name=FONT_NAME, size=10, color="111827")
            elif cell.row != 1 and not cell.font.name:
                cell.font = Font(
                    name=FONT_NAME,
                    size=cell.font.sz or 10,
                    bold=cell.font.bold,
                    italic=cell.font.italic,
                    color=cell.font.color,
                )
            alignment = copy(cell.alignment)
            alignment.vertical = "top"
            alignment.wrap_text = True
            cell.alignment = alignment
            if not cell.border.bottom.style:
                cell.border = Border(bottom=thin)


def _autofit_columns(sheet) -> None:
    for column in range(1, sheet.max_column + 1):
        letter = get_column_letter(column)
        max_length = 0
        for cell in sheet[letter]:
            if cell.value is None:
                continue
            max_length = max(max_length, len(str(cell.value)))
        sheet.column_dimensions[letter].width = min(max(max_length + 2, 11), 36)


def _apply_number_format(cell, key: str) -> None:
    if not isinstance(cell.value, (int, float)) or isinstance(cell.value, bool):
        return
    normalized = str(key).lower()
    if normalized in {"weight", "weight_sum"} or normalized.endswith(
        ("_rate", "_yield", "_change", "_ratio", "_spread")
    ):
        cell.number_format = "0.00%;[Red](0.00%);-"
    elif "turnover" in normalized:
        cell.number_format = "0.00x;[Red](0.00x);-"
    elif any(token in normalized for token in ("amount", "balance")):
        cell.number_format = "#,##0.00;[Red](#,##0.00);-"
    elif "count" in normalized:
        cell.number_format = "#,##0;[Red](#,##0);-"
    else:
        cell.number_format = "#,##0.0000;[Red](#,##0.0000);-"


def _add_negative_yield_rules(
    sheet,
    rows: list[dict[str, Any]],
    header_row: int,
    end_row: int,
) -> None:
    if end_row <= header_row:
        return
    headers = _headers(rows)
    for key in ("net_yield", "fixed_income_yield"):
        if key not in headers:
            continue
        column = get_column_letter(headers.index(key) + 1)
        sheet.conditional_formatting.add(
            f"{column}{header_row + 1}:{column}{end_row}",
            CellIsRule(
                operator="lessThan",
                formula=["0"],
                fill=PatternFill("solid", fgColor=_FAIL_FILL),
            ),
        )


def _cell_value(value: Any) -> Any:
    if isinstance(value, str):
        return _safe_excel_text(value)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if hasattr(value, "item"):
        return _cell_value(value.item())
    if isinstance(value, (list, tuple)):
        return _safe_excel_text(",".join(str(item) for item in value))
    if isinstance(value, dict):
        return _safe_excel_text(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return _safe_excel_text(str(value))


def _safe_excel_text(value: str) -> str:
    """Keep uploaded labels/text from becoming formulas in the XLSX output."""

    return safe_xlsx_text(value)


def _label(key: str) -> str:
    return _LABELS.get(str(key), str(key))


__all__ = [
    "RISK_ANALYSIS_REPORT_SHEETS",
    "RiskAnalysisReportPayload",
    "render_risk_analysis_report",
]
