"""Summary of portfolio analysis+ Report Collapse Tool(report.py).

- portfolio_gate_summary:All in one piece.$ref Stepred_flags With Key Numbersgate payload,
  For decision-making (%)needs_confirmation)display; red flag list is the doorchecklist(PrecedentsMONITORING_RUN Call the police door.
- portfolio_report:Move a pre-sequenced output into thexlsx(render_portfolio_report),
  Registrationartifact Audit line. Reports are only moved without recosting (inINV-1).
"""

from __future__ import annotations

from pathlib import Path

from marvis.output.portfolio_report import PortfolioReportPayload, render_portfolio_report


def collect_red_flags(*step_outputs) -> list[dict]:
    """Export a number of stepsdict - Yes.red_flags Compile a list (with source labels, not semantics)."""
    flags: list[dict] = []
    for label, output in step_outputs:
        if not isinstance(output, dict):
            continue
        for flag in output.get("red_flags") or []:
            if isinstance(flag, dict):
                flags.append({"source": label, **flag})
    return flags


def gate_summary_payload(
    *,
    flow: dict | None,
    migration: dict | None,
    segment: dict | None,
    trend: dict | None,
    expected_loss: dict | None,
) -> dict:
    """Summarypayload:Key figures+ C. List of red flags=Door.checklist)."""
    red_flags = collect_red_flags(
        ("flow_rate", flow),
        ("bucket_migration", migration),
        ("segment_profile", segment),
        ("score_stability_trend", trend),
        ("expected_loss_estimate", expected_loss),
    )
    highlights: dict = {}
    if expected_loss:
        highlights["total_el"] = expected_loss.get("total_el")
        # annotate the total_el caliber(reference-snapshot basis) so the gate headline
        # is self-documenting; pure pass-through of assumptions (INV-1, no recompute).
        el_assumptions = expected_loss.get("assumptions") or {}
        highlights["total_el_basis"] = el_assumptions.get("total_el_basis")
        highlights["reference_snapshot"] = el_assumptions.get("reference_snapshot")
    if segment and isinstance(segment.get("concentration"), dict):
        highlights["hhi"] = segment["concentration"].get("hhi")
        highlights["top1_pct"] = segment["concentration"].get("top1_pct")
    if migration:
        highlights["migration_months"] = migration.get("window_months")
    return {
        "highlights": highlights,
        "red_flags": red_flags,
        "red_flag_count": len(red_flags),
        "checklist": [flag.get("message") or flag.get("kind") for flag in red_flags],
    }


def build_report(
    *,
    project_meta: dict | None,
    flow: dict | None,
    migration: dict | None,
    segment: dict | None,
    trend: dict | None,
    expected_loss: dict | None,
    out_path: Path,
) -> tuple[Path, list[str]]:
    red_flags = collect_red_flags(
        ("flow_rate", flow),
        ("bucket_migration", migration),
        ("segment_profile", segment),
        ("score_stability_trend", trend),
        ("expected_loss_estimate", expected_loss),
    )
    payload = PortfolioReportPayload(
        project_meta=dict(project_meta or {}),
        flow=flow,
        migration=migration,
        segment=segment,
        trend=trend,
        expected_loss=expected_loss,
        red_flags=red_flags,
    )
    from marvis.output.portfolio_report import PORTFOLIO_REPORT_SHEETS

    final_path = render_portfolio_report(payload, out_path)
    return final_path, list(PORTFOLIO_REPORT_SHEETS)


__all__ = ["build_report", "collect_red_flags", "gate_summary_payload"]
