from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from marvis.artifacts import TransactionalArtifactStore
from marvis.output.xlsx_safety import safe_xlsx_cell
from marvis.packs.modeling.report_compute import ReportSectionStatus


MODEL_REPORT_SHEETS = [
    "Summary",
    "Sample analysis",
    "Vintage",
    "Characteristic importance",
    "Scorecard",
    "Rating Session",
    "Probability calibration",
    "ootBox evaluation_Ten-pack.",
    "Single Variable Analysis",
    "Pressure test",
]


@dataclass(frozen=True)
class ModelReportPayload:
    project_meta: dict
    dataset_split: list[dict]
    stability: list[dict]
    sample_analysis: list[dict] | None
    vintage: dict | None
    feature_importance: list[dict]
    scorecard_table: list[dict] = field(default_factory=list)
    score_bands: list[dict] = field(default_factory=list)
    calibration: list[dict] = field(default_factory=list)
    univariate: list[dict] = field(default_factory=list)
    oot_bin_table: list[dict] = field(default_factory=list)
    stress_product_removal: dict = field(default_factory=dict)
    stress_low_pricing: dict | None = None
    narratives: dict = field(default_factory=dict)
    section_status: list[ReportSectionStatus] = field(default_factory=list)


def render_model_report(payload: ModelReportPayload, out_path: Path) -> Path:
    out_path = Path(out_path)
    workbook = Workbook()
    workbook.remove(workbook.active)
    _write_summary(workbook, payload)
    _write_section_sheet(
        workbook,
        "Sample analysis",
        payload.sample_analysis,
        _unavailable_reason(payload, "sample_analysis"),
    )
    _write_section_sheet(
        workbook,
        "Vintage",
        _vintage_rows(payload.vintage),
        _unavailable_reason(payload, "vintage"),
    )
    _write_section_sheet(workbook, "Characteristic importance", payload.feature_importance, None)
    _write_section_sheet(workbook, "Scorecard", payload.scorecard_table, None)
    _write_score_band_sheet(workbook, payload.score_bands)
    _write_section_sheet(workbook, "Probability calibration", payload.calibration, None)
    _write_section_sheet(
        workbook,
        "ootBox evaluation_Ten-pack.",
        payload.oot_bin_table,
        _unavailable_reason(payload, "amount_bin"),
    )
    _write_section_sheet(workbook, "Single Variable Analysis", payload.univariate, None)
    _write_stress_sheet(workbook, payload)
    artifact = TransactionalArtifactStore(out_path.parent).stage(out_path.name)
    try:
        workbook.save(artifact.path)
        final_path = artifact.promote()
        artifact.commit()
        return final_path
    except Exception:
        artifact.rollback()
        raise


def _write_summary(workbook: Workbook, payload: ModelReportPayload) -> None:
    sheet = workbook.create_sheet("Summary")
    rows = [
        ("I. CONTEXT OF THE MODEL", ""),
        ("Project metadata", ""),
        *[(str(key), _cell(value)) for key, value in payload.project_meta.items()],
        ("Datasets", ""),
        *_dict_rows(payload.dataset_split),
        ("Stability indicators", ""),
        *_dict_rows(payload.stability),
        ("II. Sample analysis findings", str(payload.narratives.get("sample", ""))),
        ("III.VintageAnalytical findings", str(payload.narratives.get("vintage", ""))),
        ("IV. Model conclusions", str(payload.narratives.get("model", ""))),
        ("V. List of products used", _product_list_summary(payload)),
        ("VI. Pressure testing", str(payload.narratives.get("stress", ""))),
    ]
    _write_rows(sheet, rows)


def _write_section_sheet(
    workbook: Workbook,
    title: str,
    rows: list[dict] | None,
    unavailable_reason: str | None,
) -> None:
    sheet = workbook.create_sheet(title)
    if unavailable_reason:
        sheet["A1"] = f"No operational data available (%){unavailable_reason})"
        sheet["A1"].font = Font(bold=True, color="9C0006")
        sheet["A1"].fill = PatternFill("solid", fgColor="FFC7CE")
        return
    _write_dict_table(sheet, rows or [])


def _write_score_band_sheet(workbook: Workbook, rows: list[dict]) -> None:
    """DOM-5: score-band sheet with a caption documenting the shared bin-edge basis
    and cumulation direction, followed by the table itself. Bin edges are computed
    once on train (see tools.py::_score_band_rows) so the caption states that
    explicitly instead of leaving readers to infer it from the data."""
    sheet = workbook.create_sheet("Rating Session")
    if not rows:
        sheet["A1"] = "No data available"
        return
    edges_source = rows[0].get("bin_edges_source") or "train"
    direction = rows[0].get("cum_direction") or "higher_is_riskier"
    direction_label = "High-risk scores (%)PD)" if direction == "higher_is_riskier" else "Lower the high-risk score (scoring card scores)"
    cum_reading = (
        "Cumulative column high score/High-risk boxes are cumulative to low, indicatingscore >= The rejection side of the current lower boundary accumulates"
        if direction == "higher_is_riskier"
        else "Cumulative column from low score/High-risk boxes aggregate to high-value, indicatingscore < Quantified rejection side of the current upper box"
    )
    example = _score_band_worked_example(rows)
    splits_present = "/".join(dict.fromkeys(row.get("split") for row in rows if row.get("split")))
    has_unscored = any(int(row.get("unscored_count") or 0) > 0 for row in rows)
    rate_note = (
        "cum_count_pct Cumulatively in the rated sample;cum_reject_rate/cum_pass_rate "
        "By all meanssplit Sample is the denominator, but the unrated sample is byscore_coverage/unscored_count Single column."
        if has_unscored
        else "cum_count_pct/cum_reject_rate The number of people who have been denied is not even a good idea.cum_pass_rate = 1 - Rate of rejection."
    )
    sheet["A1"] = (
        f"Boundary caliber of the box: the same frequency box border{edges_source} The blogger says:{splits_present} (a) Shared the same border;"
        f"{direction_label};{cum_reading};{rate_note}"
    )
    sheet["A1"].font = Font(bold=True)
    if example:
        sheet["A2"] = example
        sheet["A2"].font = Font(italic=True)
    _write_dict_table(sheet, rows, start_row=4)


def _score_band_worked_example(rows: list[dict]) -> str:
    """A single worked-reading row (DOM-5 how-to-fix #4): picks the OOT split's
    boundary of the cutoff-side band closest to 50% cumulative reject rate as a
    concrete "cutoff -> reject rate / bad rate" example for the report reader."""
    def reject_rate(row: dict):
        value = row.get("cum_reject_rate")
        return row.get("cum_count_pct") if value is None else value

    oot_rows = [
        row
        for row in rows
        if row.get("split") == "oot" and reject_rate(row) is not None
    ]
    candidates = oot_rows or [row for row in rows if reject_rate(row) is not None]
    if not candidates:
        return ""
    closest = min(candidates, key=lambda row: abs(reject_rate(row) - 0.5))
    direction = closest.get("cum_direction") or "higher_is_riskier"
    cutoff = (
        closest.get("score_lower")
        if direction == "higher_is_riskier"
        else closest.get("score_upper")
    )
    cum_pct = reject_rate(closest)
    cum_bad = closest.get("cum_bad_rate")
    if cutoff is None or cum_pct is None:
        return ""
    bad_text = f"{cum_bad:.2%}" if cum_bad is not None else "n/a"
    return (
        f"Example Method (Performance){closest.get('split')}):cutoff≈{cutoff:.4g} → Rate of rejections{cum_pct:.2%},"
        f"Rejecting the cumulative bad debt rate of the crowd{bad_text}"
    )


def _write_stress_sheet(workbook: Workbook, payload: ModelReportPayload) -> None:
    sheet = workbook.create_sheet("Pressure test")
    sheet["A1"] = "6.1 Missing products"
    _write_dict_table(sheet, _dict_payload_rows(payload.stress_product_removal), start_row=2)
    start_row = sheet.max_row + 2
    sheet.cell(row=start_row, column=1, value="6.2 Increase in the share of low-priced population")
    reason = _unavailable_reason(payload, "low_pricing")
    if reason:
        sheet.cell(row=start_row + 1, column=1, value=f"No operational data available (%){reason})")
    else:
        _write_dict_table(
            sheet,
            _dict_payload_rows(payload.stress_low_pricing or {}),
            start_row=start_row + 1,
        )


def _write_rows(sheet, rows: list[tuple]) -> None:
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row, start=1):
            sheet.cell(row=row_index, column=col_index, value=_cell(value))
    _style_header(sheet)


def _write_dict_table(sheet, rows: list[dict], *, start_row: int = 1) -> None:
    if not rows:
        sheet.cell(row=start_row, column=1, value="No data available")
        return
    headers = list(rows[0].keys())
    for col_index, header in enumerate(headers, start=1):
        sheet.cell(row=start_row, column=col_index, value=_cell(header))
    for row_index, row in enumerate(rows, start=start_row + 1):
        for col_index, header in enumerate(headers, start=1):
            sheet.cell(row=row_index, column=col_index, value=_cell(row.get(header)))
    _style_header(sheet, row=start_row)


def _dict_rows(rows: list[dict]) -> list[tuple]:
    out = []
    for row in rows:
        out.extend((str(key), _cell(value)) for key, value in row.items())
    return out


def _vintage_rows(vintage: dict | None) -> list[dict] | None:
    if vintage is None:
        return None
    headers = vintage.get("headers") or []
    counts = vintage.get("counts") or {}
    amounts = vintage.get("amounts") or {}
    rows = []
    for cohort, values in (vintage.get("curves") or {}).items():
        row = {"Month of the loan": cohort}
        if cohort in counts:
            row["Number of loans disbursed"] = counts[cohort]
        amount = amounts.get(cohort)
        if isinstance(amount, dict):
            row["Amount released"] = amount.get("total")
            row["Average value of items"] = amount.get("average")
        for header, value in zip(headers, values, strict=False):
            row[str(header)] = value
        rows.append(row)
    return rows


def _dict_payload_rows(payload: dict) -> list[dict]:
    rows = []
    for key, value in payload.items():
        if isinstance(value, dict):
            rows.append({"Item": key, **value})
        else:
            rows.append({"Item": key, "Value": _cell(value)})
    return rows


def _unavailable_reason(payload: ModelReportPayload, section: str) -> str | None:
    for status in payload.section_status:
        if status.section == section and not status.available:
            return status.reason or "Lack of operational data"
    return None


def _product_list_summary(payload: ModelReportPayload) -> str:
    unavailable = _unavailable_reason(payload, "product_list")
    if unavailable:
        return unavailable
    products = []
    seen = set()
    for row in payload.feature_importance:
        product = row.get("Product name")
        if not product:
            continue
        vendor = row.get("Vendor name")
        label = f"{product}({vendor})" if vendor else str(product)
        if label in seen:
            continue
        seen.add(label)
        products.append(label)
    return ";".join(products)


def _cell(value: Any):
    return safe_xlsx_cell(value)


def _style_header(sheet, *, row: int = 1) -> None:
    fill = PatternFill("solid", fgColor="1F4E78")
    for cell in sheet[row]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = fill


def payload_to_dict(payload: ModelReportPayload) -> dict:
    return {
        **asdict(payload),
        "section_status": [asdict(status) for status in payload.section_status],
    }


__all__ = ["MODEL_REPORT_SHEETS", "ModelReportPayload", "payload_to_dict", "render_model_report"]
