from __future__ import annotations

import csv
import io

# S5: the monitoring plan builder moved to monitoring_plan.py (single source of
# truth for the plan read/write path). Re-exported here so existing importers of
# ``deliverables.build_monitoring_plan`` keep working unchanged.
from marvis.packs.strategy.monitoring_plan import build_monitoring_plan


_DECISION_TABLE_HEADER = [
    "Serial number",
    "Conditions",
    "Decision-making",
    "Value",
    "bandIntersection",
    "Samples as a percentage",
    "Bad rate",
    "Expected profits",
]


def build_decision_table_rows(rules: list[dict], bands: list[dict]) -> list[dict]:
    """Row per rule aligned with the matching band by index; band stats come from
    the design_cutoff_bands output passed through, never recomputed (INV-1)."""
    rows: list[dict] = []
    for index, rule in enumerate(rules, start=1):
        band = bands[index - 1] if index - 1 < len(bands) else {}
        band_range = ""
        if band:
            band_range = f"[{_g(band.get('lo'))},{_g(band.get('hi'))})"
        rows.append(
            {
                "Serial number": index,
                "Conditions": str(rule.get("condition", "")),
                "Decision-making": str(rule.get("decision", "")),
                "Value": "" if rule.get("value") is None else str(rule.get("value")),
                "bandIntersection": band_range,
                "Samples as a percentage": _pct(band.get("pop_pct")),
                "Bad rate": _pct(band.get("bad_rate")),
                "Expected profits": _num(band.get("expected_profit")),
            }
        )
    return rows


def decision_table_csv(rules: list[dict], bands: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_DECISION_TABLE_HEADER)
    writer.writeheader()
    for row in build_decision_table_rows(rules, bands):
        writer.writerow(row)
    return buffer.getvalue()


def _g(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def _pct(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return ""


def _num(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


__all__ = [
    "build_decision_table_rows",
    "build_monitoring_plan",
    "decision_table_csv",
]
