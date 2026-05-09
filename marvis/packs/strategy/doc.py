from __future__ import annotations


# The strategy doc never recomputes metrics (INV-1): every number here comes from
# the persisted strategy / backtests / band stats passed in, formatted for a
# Chinese-language markdown deliverable.
_ASSET_STATUS_LABEL = {
    "draft": "Draft",
    "validated": "Authenticated",
    "adopted_local": "Locally accepted",
    "retired": "Retired",
}
_LEGACY_ASSET_STATUS = {
    "draft": "draft",
    "adopted": "adopted_local",
    "retired": "retired",
}


def render_strategy_doc_markdown(
    *,
    strategy: dict,
    meta: dict,
    backtests: list[dict],
    artifacts: list[dict],
    band_stats: list[dict],
    red_flags: list[dict] | None = None,
) -> tuple[str, list[str]]:
    strategy_type = str(strategy.get("strategy_type") or "")
    decision_strategy = strategy_type in {"approval", "reject"}
    distribution_section = "Split Belt" if decision_strategy else "Type distribution"
    sections = [
        "Overview of strategies",
        "List of rules",
        "Revert Summary",
        distribution_section,
        "Red flag and disposal records",
        "Summary of the control plan",
    ]
    lines: list[str] = []
    strategy_id = str(strategy.get("id", ""))
    lines.append(f"# Policy document.{strategy_id}")
    lines.append("")

    # 1. Overview
    lines.append("## Overview of strategies")
    version = meta.get("version", 1)
    legacy_status = str(meta.get("status", "draft"))
    asset_status = str(
        meta.get("asset_status") or _LEGACY_ASSET_STATUS.get(legacy_status, legacy_status)
    )
    status = _ASSET_STATUS_LABEL.get(asset_status, asset_status)
    parent = meta.get("parent_strategy_id")
    lines.append(f"- Type:{strategy.get('strategy_type', '')}")
    lines.append(f"- Version:v{version}")
    lines.append(f"- Status:{status}")
    if asset_status == "adopted_local":
        lines.append("- Deployment boundary: Local adoption does not represent the operationalization of the production environment")
    lines.append(f"- Parental strategy:{parent if parent else 'None'}")
    if meta.get("adopted_at"):
        lines.append(f"- Adoption:{meta.get('adopted_at')}")
    if meta.get("adoption_reason"):
        lines.append(f"- Reasons for adoption:{meta.get('adoption_reason')}")
    lines.append("")

    # 2. Rules
    lines.append("## List of rules")
    lines.append("| # | Conditions| Decision-making| Value|")
    lines.append("| --- | --- | --- | --- |")
    for index, rule in enumerate(strategy.get("rules") or [], start=1):
        value = rule.get("value")
        lines.append(
            f"| {index} | {rule.get('condition', '')} | {rule.get('decision', '')} | "
            f"{'-' if value is None else value} |"
        )
    lines.append(f"| - | Default Action| {strategy.get('default_decision', '')} | - |")
    lines.append("")

    # 3. Backtest summary (incl. swap)
    lines.append("## Revert Summary")
    if backtests:
        lines.extend(_backtest_summary_lines(backtests[-1]))
    else:
        lines.append("- There is no return.")
    lines.append("")

    # 4. Bands
    lines.append(f"## {distribution_section}")
    if not decision_strategy:
        lines.append("- The typology distribution and risk indicators are presented in the retrospect summary; no fraction calibration is used for this type.")
    elif band_stats:
        lines.append("| band Intersection| Samples as a percentage| Bad rate| Cumulative approval rate| Cumulative bad rate| Decision-making|")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for band in band_stats:
            lines.append(
                f"| [{_g(band.get('lo'))},{_g(band.get('hi'))}) | {_pct(band.get('pop_pct'))} | "
                f"{_pct(band.get('bad_rate'))} | {_pct(band.get('cum_approval_rate'))} | "
                f"{_pct(band.get('cum_bad_rate'))} | {band.get('decision', '')} |"
            )
    else:
        lines.append("- No fractional chronology is provided.")
    lines.append("")

    # 5. Red flags
    lines.append("## Red flag and disposal records")
    flags = _effective_red_flags(red_flags, backtests)
    if flags:
        lines.append("| Level| code | Annotations|")
        lines.append("| --- | --- | --- |")
        for flag in flags:
            lines.append(
                f"| {flag.get('level', '')} | {flag.get('code', '')} | {flag.get('message', '')} |"
            )
    else:
        lines.append("- No red flag record.")
    lines.append("")

    # 6. Monitoring plan summary
    lines.append("## Summary of the control plan")
    monitoring = [a for a in artifacts if a.get("kind") == "monitoring_plan_json"]
    if monitoring:
        lines.append(f"- The monitoring plan has been registered:{monitoring[-1].get('path', '')}")
        if decision_strategy:
            lines.append("- Monitoring indicators: declining approval rate through bad-for-client rate (%)S5 (c) Closed consumption.")
        else:
            lines.append("- Monitoring indicators: implemented by structured measurement indicators of this type of strategy.")
    else:
        lines.append("- No surveillance plan has been generated.")
    lines.append("")

    return "\n".join(lines), sections


def _effective_red_flags(
    supplied: list[dict] | None,
    backtests: list[dict],
) -> list[dict]:
    flags = [dict(flag) for flag in (supplied or []) if isinstance(flag, dict)]
    latest = backtests[-1] if backtests else {}
    economics = latest.get("economics") if isinstance(latest, dict) else None
    profit_note = (
        economics.get("profit_note")
        if isinstance(economics, dict)
        else latest.get("profit_note")
    )
    if profit_note and not any(
        flag.get("code") == "expected_profit_unavailable" for flag in flags
    ):
        flags.append(
            {
                "level": "amber",
                "code": "expected_profit_unavailable",
                "message": str(profit_note),
            }
        )
    return flags


def _g(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def _pct(value) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def _num(value) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _typed_backtest_view(
    payload: dict,
) -> tuple[str, dict, list[dict], list[dict], dict, list[str]] | None:
    metrics = payload.get("metrics")
    strategy_type = payload.get("strategy_type")
    if not isinstance(metrics, dict) or not isinstance(strategy_type, str):
        return None
    return (
        strategy_type,
        metrics,
        [row for row in (payload.get("breakdown") or []) if isinstance(row, dict)],
        [row for row in (payload.get("transitions") or []) if isinstance(row, dict)],
        payload.get("economics")
        if isinstance(payload.get("economics"), dict)
        else {},
        [str(item) for item in (payload.get("warnings") or []) if str(item)],
    )


def _backtest_summary_lines(payload: dict) -> list[str]:
    """Format persisted metrics without deriving any new business number."""

    typed = _typed_backtest_view(payload)
    if typed is None:
        return _legacy_approval_backtest_lines(payload)
    strategy_type, metrics, breakdown, transitions, economics, warnings = typed
    if strategy_type in {"approval", "reject"}:
        lines = _decision_backtest_lines(
            payload,
            strategy_type=strategy_type,
            metrics=metrics,
            breakdown=breakdown,
            economics=economics,
        )
    elif strategy_type == "limit":
        lines = _limit_backtest_lines(payload, metrics, breakdown, economics)
    elif strategy_type == "pricing":
        lines = _pricing_backtest_lines(payload, metrics, breakdown, economics)
    elif strategy_type == "segmentation":
        lines = _segmentation_backtest_lines(payload, metrics, breakdown)
    else:
        lines = [f"- Unrecognized type of return:{strategy_type}"]
    lines.extend(_backtest_transition_lines(strategy_type, transitions))
    if warnings:
        lines.append("- Reaction warning:" + ";".join(warnings))
    return lines


def _legacy_approval_backtest_lines(payload: dict) -> list[str]:
    lines = [
        f"- Rate of approval:{_pct(payload.get('approval_rate'))}",
        f"- The following is the target of the crash:{_pct(payload.get('approved_bad_rate'))}",
        f"- Deny crowd badness:{_pct(payload.get('rejected_bad_rate'))}",
    ]
    if int(payload.get("review_count") or 0):
        lines.append(
            f"- Manual review:{payload.get('review_count')} Household,"
            f"Percentage{_pct(payload.get('review_rate'))},"
            f"Bad rate{_pct(payload.get('review_bad_rate'))}"
        )
    lines.extend(
        [
            f"- Expected profits:{_num(payload.get('expected_profit'))}",
            (
                f"- swap-in:{payload.get('swap_in_count', 0)} Household,"
                f"Bad rate{_pct(payload.get('swap_in_bad_rate'))}"
            ),
            (
                f"- swap-out:{payload.get('swap_out_count', 0)} Household,"
                f"Bad rate{_pct(payload.get('swap_out_bad_rate'))}"
            ),
        ]
    )
    if payload.get("profit_note"):
        lines.append(f"- Profit calibration hint:{payload['profit_note']}")
    return lines


def _decision_backtest_lines(
    payload: dict,
    *,
    strategy_type: str,
    metrics: dict,
    breakdown: list[dict],
    economics: dict,
) -> list[str]:
    lines = [
        f"- Reaction type:{'Reject Policy' if strategy_type == 'reject' else 'Access Policy'}",
        f"- Rate of approval:{_pct(metrics.get('approve_rate'))}",
        f"- The following is the target of the crash:{_pct(metrics.get('approve_bad_rate'))}",
        f"- Deny crowd badness:{_pct(metrics.get('reject_bad_rate'))}",
        f"- Manual review rate:{_pct(metrics.get('review_rate'))}",
        f"- Expected profits:{_num(economics.get('expected_profit'))}",
        f"- Label coverage:{_pct(payload.get('label_coverage'))}",
    ]
    if economics.get("profit_note"):
        lines.append(f"- Profit calibration hint:{economics['profit_note']}")
    if strategy_type == "reject":
        lines.extend(
            [
                f"- Bad customer catch rate:{_pct(metrics.get('bad_capture_rate'))}",
                f"- Good customer error rejection rate:{_pct(metrics.get('good_reject_rate'))}",
            ]
        )
    if breakdown:
        lines.extend(
            [
                "",
                "### Decision-making distribution",
                "| Decision-making| Number of samples| Percentage| Number of labels| Bad sample.| Bad rate|",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in breakdown:
            lines.append(
                f"| {row.get('action', '')} | {row.get('count', '')} | "
                f"{_pct(row.get('rate'))} | {row.get('labeled_count', '')} | "
                f"{row.get('bad_count', '')} | {_pct(row.get('bad_rate'))} |"
            )
    return lines


def _limit_backtest_lines(
    payload: dict, metrics: dict, breakdown: list[dict], economics: dict
) -> list[str]:
    lines = [
        "- Type of return: a volume strategy",
        f"- Number of samples:{metrics.get('count', payload.get('population_count', ''))}",
        f"- Total:{_num(metrics.get('total_limit'))}",
        f"- Average household:{_num(metrics.get('mean_limit'))}",
        f"- Minimum/Maximum:{_num(metrics.get('min_limit'))} / "
        f"{_num(metrics.get('max_limit'))}",
        f"- Drawdown/Reduction/Number of persons not changed:{_na(metrics.get('up_count'))} / "
        f"{_na(metrics.get('down_count'))} / {_na(metrics.get('unchanged_count'))}",
        f"- Total changes:{_num(metrics.get('total_limit_delta'))}",
        f"- ProjectedEAD:{_num(economics.get('expected_ead'))}",
        f"- Expected losses:{_num(economics.get('expected_loss'))}",
        f"- Label coverage:{_pct(payload.get('label_coverage'))}",
    ]
    if breakdown:
        lines.extend(
            [
                "",
                "### Amount distribution",
                "| Amount| Number of samples| Percentage| Number of labels| Bad sample.| Bad rate|",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in breakdown:
            lines.append(
                f"| {_num(row.get('assigned_limit'))} | {row.get('count', '')} | "
                f"{_pct(row.get('share'))} | {row.get('labeled_count', '')} | "
                f"{row.get('bad_count', '')} | {_pct(row.get('bad_rate'))} |"
            )
    return lines


def _pricing_backtest_lines(
    payload: dict, metrics: dict, breakdown: list[dict], economics: dict
) -> list[str]:
    lines = [
        "- Type of return: pricing policy",
        f"- Number of samples:{metrics.get('count', payload.get('population_count', ''))}",
        f"- Average annualized interest rate:{_pct(metrics.get('mean_rate'))}",
        f"- Price increases/Price reduction/Number of persons not changed:{_na(metrics.get('repriced_up_count'))} / "
        f"{_na(metrics.get('repriced_down_count'))} / "
        f"{_na(metrics.get('unchanged_count'))}",
        f"- EAD Rights-plus:{_pct(economics.get('ead_weighted_rate'))}",
        f"- Expected income:{_num(economics.get('revenue'))}",
        f"- Expected losses:{_num(economics.get('expected_loss'))}",
        f"- Expected profits:{_num(economics.get('profit'))}",
        f"- ROA:{_pct(economics.get('roa'))}",
        f"- Change in profits relative to baseline:{_num(economics.get('profit_delta_vs_baseline'))}",
        f"- Label coverage:{_pct(payload.get('label_coverage'))}",
    ]
    if breakdown:
        lines.extend(
            [
                "",
                "### Pricing distribution",
                "| Annualized interest rate| Number of samples| Percentage| Number of labels| Bad sample.| Bad rate|",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in breakdown:
            lines.append(
                f"| {_pct(row.get('assigned_rate'))} | {row.get('count', '')} | "
                f"{_pct(row.get('share'))} | {row.get('labeled_count', '')} | "
                f"{row.get('bad_count', '')} | {_pct(row.get('bad_rate'))} |"
            )
    return lines


def _segmentation_backtest_lines(
    payload: dict, metrics: dict, breakdown: list[dict]
) -> list[str]:
    lines = [
        "- Recovery type: grouping policy",
        f"- Number of visitors:{metrics.get('segment_count', 'n/a')}",
        f"- Overall bad rate:{_pct(metrics.get('overall_bad_rate'))}",
        f"- Label coverage:{_pct(payload.get('label_coverage'))}",
    ]
    if breakdown:
        lines.extend(
            [
                "",
                "### Client risk distribution",
                "| The guests.| Number of samples| Percentage| Number of labels| Bad sample.| Bad rate| Lift |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in breakdown:
            lines.append(
                f"| {row.get('segment', '')} | {row.get('count', '')} | "
                f"{_pct(row.get('share'))} | {row.get('labeled_count', '')} | "
                f"{row.get('bad_count', '')} | {_pct(row.get('bad_rate'))} | "
                f"{_g(row.get('lift'))} |"
            )
    return lines


def _backtest_transition_lines(
    strategy_type: str,
    transitions: list[dict],
) -> list[str]:
    """Format persisted baseline transitions without deriving summary metrics."""

    if not transitions:
        return []
    if strategy_type in {"approval", "reject"}:
        lines = [
            "",
            "### Decision-making migration relative to baseline",
            "| Original decision-making| New decision-making| Number of samples| Percentage of original decision-making| Overall| Number of labels| Bad rate|",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in transitions:
            lines.append(
                f"| {row.get('from_action', '')} | {row.get('to_action', '')} | "
                f"{row.get('count', '')} | {_pct(row.get('rate'))} | "
                f"{_pct(row.get('population_share'))} | {row.get('labeled_count', '')} | "
                f"{_pct(row.get('bad_rate'))} |"
            )
        return lines
    if strategy_type == "segmentation":
        lines = [
            "",
            "### Relocation of clients relative to baseline",
            "| Original guests| New guests| Number of samples| Share of original clients| Overall|",
            "| --- | --- | --- | --- | --- |",
        ]
        for row in transitions:
            lines.append(
                f"| {row.get('from_segment', '')} | {row.get('to_segment', '')} | "
                f"{row.get('count', '')} | {_pct(row.get('rate'))} | "
                f"{_pct(row.get('population_share'))} |"
            )
        return lines
    if strategy_type in {"limit", "pricing"}:
        lines = [
            "",
            "### Direction of adjustment relative to baseline",
            "| Direction| Number of samples| Percentage|",
            "| --- | --- | --- |",
        ]
        for row in transitions:
            lines.append(
                f"| {row.get('direction', '')} | {row.get('count', '')} | "
                f"{_pct(row.get('rate'))} |"
            )
        return lines
    return []


def _na(value) -> str:
    return "n/a" if value is None else str(value)


__all__ = ["render_strategy_doc_markdown"]
