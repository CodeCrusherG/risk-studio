"""Strategy lifecycle, analytics, monitoring, and rule presenters."""

from __future__ import annotations


from marvis.agent.presenters._shared import (
    MONITOR_LEVEL_LABEL as _MONITOR_LEVEL_LABEL,
    format_number as _num,
    format_percent as _pct,
    format_value as _fmt,
    red_flag_table as _red_flag_table,
)

_STRATEGY_DECISION_LABEL = {
    "approve": "Pass.",
    "review": "Review",
    "decline": "Reject",
}

_MONITORING_RED_CHECKLIST = (
    "Recommendations for disposal(Red light.,Please answer the key words together.):",
    "1. Maintain and watch - Reply to \"Watch\" to maintain current strategy,Strengthening the next cycle of surveillance;",
    "2. Run back to the threshold - rerun the monitoring after returning to the \"trend\" control plan threshold;",
    "3. Start a new version of the policy - Reply to the \"New version\" and start a new version of the re-entry policy based on the current strategy.",
)


def _render_build_strategy(o: dict):
    rules = [rule for rule in (o.get("rules") or []) if isinstance(rule, dict)]
    strategy_type = str(o.get("strategy_type") or "approval")
    default_decision = str(o.get("default_decision") or "")
    score_col = str(o.get("score_col") or "")
    text = (
        f"**Policy candidate generated**:`{o.get('strategy_id', '')}`."
        f"Type`{strategy_type}`,Breakdown of assessments`{score_col}`,Default Action`{default_decision}`."
    )
    tables = []
    if rules:
        tables.append(
            {
                "title": "Policy rules (in order of hits)",
                "columns": ["#", "Conditions", "Actions", "Value"],
                "rows": [
                    [
                        str(index),
                        str(rule.get("condition", "")),
                        str(rule.get("decision", "")),
                        _fmt(rule.get("value"))
                        if rule.get("value") is not None
                        else "-",
                    ]
                    for index, rule in enumerate(rules, start=1)
                ],
            }
        )
    return text, tables


def _backtest_view(o: dict) -> tuple[str, dict, list[dict], list[dict], dict]:
    """Normalize the versioned V2 envelope and legacy flat approval output.

    The versioned envelope is authoritative whenever it is present.  Top-level
    approval fields may still accompany it as a temporary Tool compatibility
    projection, but presentation must not let those aliases override canonical
    metrics.  Legacy plan outputs have no ``strategy_type``/``metrics`` and keep
    their historical approval interpretation.
    """

    metrics = o.get("metrics")
    strategy_type = o.get("strategy_type")
    if isinstance(metrics, dict) and isinstance(strategy_type, str):
        return (
            strategy_type,
            metrics,
            [row for row in (o.get("breakdown") or []) if isinstance(row, dict)],
            [row for row in (o.get("transitions") or []) if isinstance(row, dict)],
            o.get("economics") if isinstance(o.get("economics"), dict) else {},
        )
    return (
        "approval",
        o,
        [row for row in (o.get("by_segment") or []) if isinstance(row, dict)],
        [],
        {
            "expected_profit": o.get("expected_profit"),
            "profit_note": o.get("profit_note"),
        },
    )


def _render_backtest_strategy(o: dict):
    strategy_type, metrics, breakdown, transitions, economics = _backtest_view(o)
    if strategy_type in {"approval", "reject"}:
        text, tables = _render_decision_backtest(
            o,
            strategy_type=strategy_type,
            metrics=metrics,
            breakdown=breakdown,
            transitions=transitions,
            economics=economics,
        )
    elif strategy_type == "limit":
        text, tables = _render_limit_backtest(o, metrics, breakdown, economics)
    elif strategy_type == "pricing":
        text, tables = _render_pricing_backtest(o, metrics, breakdown, economics)
    elif strategy_type == "segmentation":
        text, tables = _render_segmentation_backtest(o, metrics, breakdown, transitions)
    else:
        text = f"**Policy feedback complete.**:Unknown policy type`{strategy_type}`,Please check the results of the structured."
        tables = []
    return _append_backtest_warnings(text, tables, o)


def _render_decision_backtest(
    o: dict,
    *,
    strategy_type: str,
    metrics: dict,
    breakdown: list[dict],
    transitions: list[dict],
    economics: dict,
) -> tuple[str, list[dict]]:
    typed = isinstance(o.get("metrics"), dict)
    approval_rate = (
        metrics.get("approve_rate") if typed else metrics.get("approval_rate")
    )
    approved_count = (
        metrics.get("approve_count") if typed else metrics.get("approved_count")
    )
    approved_bad_rate = (
        metrics.get("approve_bad_rate") if typed else metrics.get("approved_bad_rate")
    )
    rejected_count = (
        metrics.get("reject_count") if typed else metrics.get("rejected_count")
    )
    rejected_bad_rate = (
        metrics.get("reject_bad_rate") if typed else metrics.get("rejected_bad_rate")
    )
    review_count = metrics.get("review_count")
    review_rate = metrics.get("review_rate")
    review_bad_rate = metrics.get("review_bad_rate")
    expected_profit = economics.get("expected_profit")
    profit_note = economics.get("profit_note")
    label = "Refuse strategic backshow complete." if strategy_type == "reject" else "Policy feedback complete."
    text = (
        f"**{label}**:"
        f"Approval rate{_pct(approval_rate)},"
        f"The downfall of the customer base.{_pct(approved_bad_rate)},"
        f"Deny the customer base bad rate.{_pct(rejected_bad_rate)},"
        f"Expected profits{_num(expected_profit)}."
    )
    if o.get("label_coverage") is not None:
        text += f" Label Coverage{_pct(o.get('label_coverage'))}."
    if int(review_count or 0):
        text += (
            f" Manual review{review_count} Household{_pct(review_rate)}),"
            f"Review the client\'s down rate.{_pct(review_bad_rate)}."
        )
    if strategy_type == "reject":
        text += (
            f" Bad customer catch rate{_pct(metrics.get('bad_capture_rate'))},"
            f"Good customer rejection rate.{_pct(metrics.get('good_reject_rate'))}."
        )
    if profit_note:
        text += f" Profit calibration hint:{profit_note}"

    rows = [
        ["Approval rate", _pct(approval_rate)],
        ["Number of persons adopted", _fmt(approved_count)],
        ["Passing the bad rate.", _pct(approved_bad_rate)],
        ["Number of rejected", _fmt(rejected_count)],
        ["Reject the bad rate.", _pct(rejected_bad_rate)],
        ["Number of manual reviews", _fmt(review_count)],
        ["Manual review rate", _pct(review_rate)],
        ["Review the client's down rate.", _pct(review_bad_rate)],
        ["Expected profits", _num(expected_profit)],
    ]
    if profit_note:
        rows.append(["Profit caliber hint", str(profit_note)])
    if strategy_type == "reject":
        rows.extend(
            [
                ["Bad customer catch rate", _pct(metrics.get("bad_capture_rate"))],
                ["Good customer rejection rate.", _pct(metrics.get("good_reject_rate"))],
            ]
        )
    if typed:
        rows.append(["Label Coverage", _pct(o.get("label_coverage"))])
    else:
        rows.extend(
            [
                ["swap-in", _fmt(metrics.get("swap_in_count"))],
                ["swap-out", _fmt(metrics.get("swap_out_count"))],
                ["Label Coverage", _pct(o.get("label_coverage"))],
            ]
        )
    tables: list[dict] = [
        {"title": "Policy Reaction Summary", "columns": ["Indicators", "Value"], "rows": rows}
    ]
    if breakdown:
        if typed:
            tables.append(
                {
                    "title": "Grouped by decision",
                    "columns": ["Decision-making", "Number of samples", "Percentage", "Number of labels", "Bad sample.", "Bad rate"],
                    "rows": [
                        [
                            str(row.get("action", "")),
                            _fmt(row.get("count")),
                            _pct(row.get("rate")),
                            _fmt(row.get("labeled_count")),
                            _fmt(row.get("bad_count")),
                            _pct(row.get("bad_rate")),
                        ]
                        for row in breakdown
                    ],
                }
            )
        else:
            tables.append(
                {
                    "title": "Grouped by decision",
                    "columns": ["Decision-making", "Number of samples", "Bad sample.", "Bad rate"],
                    "rows": [
                        [
                            str(row.get("decision", "")),
                            _fmt(row.get("count")),
                            _fmt(row.get("bad_count")),
                            _pct(row.get("bad_rate")),
                        ]
                        for row in breakdown
                    ],
                }
            )
    transition_table = _transition_table(strategy_type, transitions)
    if transition_table is not None:
        tables.append(transition_table)
    return text, tables


def _render_limit_backtest(
    o: dict, metrics: dict, breakdown: list[dict], economics: dict
) -> tuple[str, list[dict]]:
    text = (
        "**The scale policy is complete.**:"
        f"Overwrite{_fmt(metrics.get('count', o.get('population_count')))} Household,"
        f"Total Degrees{_num(metrics.get('total_limit'))},"
        f"Average household size{_num(metrics.get('mean_limit'))},"
        f"Change over baseline total{_num(metrics.get('total_limit_delta'))}."
    )
    if o.get("label_coverage") is not None:
        text += f" Label Coverage{_pct(o.get('label_coverage'))}."
    rows = [
        ["Number of samples", _fmt(metrics.get("count", o.get("population_count")))],
        ["Total Degrees", _num(metrics.get("total_limit"))],
        ["Average household size", _num(metrics.get("mean_limit"))],
        ["Minimum", _num(metrics.get("min_limit"))],
        ["Maximum", _num(metrics.get("max_limit"))],
        ["Number of persons drawing on", _num(metrics.get("up_count"))],
        ["Number of persons reduced", _num(metrics.get("down_count"))],
        ["Number of persons without change", _num(metrics.get("unchanged_count"))],
        ["Total changes", _num(metrics.get("total_limit_delta"))],
        ["ProjectedEAD", _num(economics.get("expected_ead"))],
        ["Expected losses", _num(economics.get("expected_loss"))],
        ["Label Coverage", _pct(o.get("label_coverage"))],
    ]
    tables: list[dict] = [
        {"title": "Summary of the magnitude policy feedback", "columns": ["Indicators", "Value"], "rows": rows}
    ]
    if breakdown:
        tables.append(
            {
                "title": "Amount distribution",
                "columns": ["Amount", "Number of samples", "Percentage", "Number of labels", "Bad sample.", "Bad rate"],
                "rows": [
                    [
                        _num(row.get("assigned_limit")),
                        _fmt(row.get("count")),
                        _pct(row.get("share")),
                        _fmt(row.get("labeled_count")),
                        _fmt(row.get("bad_count")),
                        _pct(row.get("bad_rate")),
                    ]
                    for row in breakdown
                ],
            }
        )
    return text, tables


def _render_pricing_backtest(
    o: dict, metrics: dict, breakdown: list[dict], economics: dict
) -> tuple[str, list[dict]]:
    text = (
        "**The pricing policy is back.**:"
        f"Overwrite{_fmt(metrics.get('count', o.get('population_count')))} Household,"
        f"Average annualized interest rate{_pct(metrics.get('mean_rate'))},"
        f"Expected profits{_num(economics.get('profit'))},"
        f"ROA {_pct(economics.get('roa'))}."
    )
    if o.get("label_coverage") is not None:
        text += f" Label Coverage{_pct(o.get('label_coverage'))}."
    rows = [
        ["Number of samples", _fmt(metrics.get("count", o.get("population_count")))],
        ["Average annualized interest rate", _pct(metrics.get("mean_rate"))],
        ["Number of price increases", _num(metrics.get("repriced_up_count"))],
        ["Number of persons reduced", _num(metrics.get("repriced_down_count"))],
        ["Price constant", _num(metrics.get("unchanged_count"))],
        ["EAD Rights-plus rate", _pct(economics.get("ead_weighted_rate"))],
        ["Expected income", _num(economics.get("revenue"))],
        ["Expected losses", _num(economics.get("expected_loss"))],
        ["Cost of funds", _num(economics.get("funding_cost"))],
        ["Operating costs", _num(economics.get("operating_cost"))],
        ["Expected profits", _num(economics.get("profit"))],
        ["ROA", _pct(economics.get("roa"))],
        ["Baseline profit", _num(economics.get("baseline_profit"))],
        ["Change in profits over baseline", _num(economics.get("profit_delta_vs_baseline"))],
        ["Label Coverage", _pct(o.get("label_coverage"))],
    ]
    tables: list[dict] = [
        {"title": "Summary of price-fixing policy responses", "columns": ["Indicators", "Value"], "rows": rows}
    ]
    if breakdown:
        tables.append(
            {
                "title": "Pricing distribution",
                "columns": ["Annualized interest rate", "Number of samples", "Percentage", "Number of labels", "Bad sample.", "Bad rate"],
                "rows": [
                    [
                        _pct(row.get("assigned_rate")),
                        _fmt(row.get("count")),
                        _pct(row.get("share")),
                        _fmt(row.get("labeled_count")),
                        _fmt(row.get("bad_count")),
                        _pct(row.get("bad_rate")),
                    ]
                    for row in breakdown
                ],
            }
        )
    return text, tables


def _render_segmentation_backtest(
    o: dict, metrics: dict, breakdown: list[dict], transitions: list[dict]
) -> tuple[str, list[dict]]:
    text = (
        "**Group Policy Retrospect completed**:"
        f"Form{_fmt(metrics.get('segment_count'))} The crowd of guests,"
        f"Overall bad rate{_pct(metrics.get('overall_bad_rate'))}."
    )
    if o.get("label_coverage") is not None:
        text += f" Label Coverage{_pct(o.get('label_coverage'))}."
    rows = [
        [
            str(row.get("segment", "")),
            _fmt(row.get("count")),
            _pct(row.get("share")),
            _fmt(row.get("labeled_count")),
            _fmt(row.get("bad_count")),
            _pct(row.get("bad_rate")),
            _fmt(row.get("lift")),
        ]
        for row in breakdown
    ]
    tables: list[dict] = [
        {
            "title": "Client risk distribution",
            "columns": ["The guests.", "Number of samples", "Percentage", "Number of labels", "Bad sample.", "Bad rate", "Lift"],
            "rows": rows,
        }
    ]
    transition_table = _transition_table("segmentation", transitions)
    if transition_table is not None:
        tables.append(transition_table)
    return text, tables


def _transition_table(strategy_type: str, rows: list[dict]) -> dict | None:
    if not rows:
        return None
    if strategy_type in {"approval", "reject"}:
        return {
            "title": "Decision-making migration relative to baseline",
            "columns": ["Original decision-making", "New decision-making", "Number of samples", "Percentage of original decision-making", "Overall"],
            "rows": [
                [
                    str(row.get("from_action", "")),
                    str(row.get("to_action", "")),
                    _fmt(row.get("count")),
                    _pct(row.get("rate")),
                    _pct(row.get("population_share")),
                ]
                for row in rows
            ],
        }
    if strategy_type == "segmentation":
        return {
            "title": "Relocation of clients relative to baseline",
            "columns": ["Original guests", "New guests", "Number of samples", "Share of original clients", "Overall"],
            "rows": [
                [
                    str(row.get("from_segment", "")),
                    str(row.get("to_segment", "")),
                    _fmt(row.get("count")),
                    _pct(row.get("rate")),
                    _pct(row.get("population_share")),
                ]
                for row in rows
            ],
        }
    return None


def _append_backtest_warnings(
    text: str, tables: list[dict], o: dict
) -> tuple[str, list[dict]]:
    warnings = [str(item) for item in (o.get("warnings") or []) if str(item)]
    if warnings:
        text += " Warning:" + ";".join(warnings) + "."
        tables.append(
            {
                "title": "Revert Warning",
                "columns": ["Warning"],
                "rows": [[warning] for warning in warnings],
            }
        )
    red_flags = [
        item
        for item in (o.get("red_flags") or [])
        if isinstance(item, dict) and str(item.get("message") or "")
    ]
    if red_flags:
        tables.append(
            {
                "title": "Risk-based risk-based retrofit",
                "columns": ["Level", "Code", "Annotations"],
                "rows": [
                    [
                        str(item.get("level") or ""),
                        str(item.get("code") or ""),
                        str(item.get("message") or ""),
                    ]
                    for item in red_flags
                ],
            }
        )
    return text, tables


def _profit_delta_text(value, other) -> str:
    """Expected profit margin case (recommended)vs Alternative, subtract existing output fields only (no calculator added),
    andcompare Renderer's right.tool deltas The difference is the same.presentation-only INV-1)."""
    try:
        diff = float(value) - float(other)
    except (TypeError, ValueError):
        return "n/a"
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:.4f}"


def _tradeoff_alternatives(
    points: list, recommended: dict | None
) -> tuple[list[list], dict | None]:
    """LT-11 (B.2): the top-2 feasible cutoff alternatives *other than* the
    recommended one (each with its Expected profitsgap vs the recommended point) plus the
    single best alternative point itself, so the caller can also state the
    recommendation's advantage. All numbers are the points' own already-computed
    fields; the gap is a plain subtraction (no new computationcaliber)."""
    if not recommended:
        return [], None
    reco_cutoff = recommended.get("cutoff")
    feasible = [
        point
        for point in points
        if point.get("feasible", True) and point.get("cutoff") != reco_cutoff
    ]
    # Order by expected_profit desc (the same objective the recommend picked on), so
    # "Alternative" reads as the runner-up feasible operating points.
    feasible.sort(
        key=lambda p: (
            p.get("expected_profit")
            if isinstance(p.get("expected_profit"), (int, float))
            else float("-inf")
        ),
        reverse=True,
    )
    rows = [
        [
            _fmt(point.get("cutoff")),
            _pct(point.get("approval_rate")),
            _pct(point.get("bad_rate")),
            _num(point.get("expected_profit")),
            _profit_delta_text(
                point.get("expected_profit"), recommended.get("expected_profit")
            ),
        ]
        for point in feasible[:2]
    ]
    return rows, (feasible[0] if feasible else None)


def _render_tradeoff_view(o: dict):
    points = [point for point in (o.get("points") or []) if isinstance(point, dict)]
    recommended = (
        o.get("recommended") if isinstance(o.get("recommended"), dict) else None
    )
    direction_label = (
        "The higher the score, the lower the risk."
        if o.get("score_direction") == "higher_is_better"
        else "The higher the score, the higher the risk."
    )
    feasible_points = [point for point in points if point.get("feasible", True)]
    alt_rows, best_alt = _tradeoff_alternatives(points, recommended)
    if recommended:
        # LT-11 (B.1): the recommendation carries its evidence -- it is a *feasible*
        # operating point (constraint-satisfying), and how many of the scanned
        # cutoffs were feasible at all; plus (B.2) the profit advantage over the
        # next-best feasible cutoff so Recommendationsis not a bare conclusion. Every number is
        # a field already in the tool output (INV-1: presentation only, no
        # re-computation; the advantage is a subtraction of two existing points).
        evidence = f"Basis: Possible areas of compliance with the binding obligation (total){len(feasible_points)}/{len(points)} individualcutoff (Performance)"
        if best_alt is not None:
            advantage = _profit_delta_text(
                recommended.get("expected_profit"), best_alt.get("expected_profit")
            )
            evidence += f",And the expected profit is better.cutoff `{_fmt(best_alt.get('cutoff'))}` High{advantage}"
        text = (
            f"**Policy trade-off view complete**({direction_label}):"
            f"Recommendationscutoff `{_fmt(recommended.get('cutoff'))}`,"
            f"Approval rate{_pct(recommended.get('approval_rate'))},"
            f"Bad rate{_pct(recommended.get('bad_rate'))},"
            f"Expected profits{_num(recommended.get('expected_profit'))}"
            f"({evidence})."
        )
    else:
        text = f"**Policy trade-off view complete**({direction_label})."
    red_flags = [flag for flag in (o.get("red_flags") or []) if isinstance(flag, dict)]
    red_items = [flag for flag in red_flags if flag.get("level") == "red"]
    if red_items:
        names = ",".join(str(flag.get("code")) for flag in red_items)
        text += f" Red flag:{names}."
    tables = []
    reco_cutoff = recommended.get("cutoff") if recommended else None
    if points:
        tables.append(
            {
                "title": "cutoff Trade-offs.",
                "columns": ["Recommendations", "cutoff", "Approval rate", "Bad rate", "Expected profits", "It's possible."],
                "rows": [
                    [
                        "★"
                        if point.get("cutoff") == reco_cutoff and recommended
                        else "",
                        _fmt(point.get("cutoff")),
                        _pct(point.get("approval_rate")),
                        _pct(point.get("bad_rate")),
                        _num(point.get("expected_profit")),
                        "Yes." if point.get("feasible", True) else "Yes",
                    ]
                    for point in points[:20]
                ],
            }
        )
    # LT-11 (B.2): top-2 feasibleAlternativewith theExpected profitsgap toRecommendations, so the user sees
    # what the recommendation gives up relative to the runner-up operating points.
    if alt_rows:
        tables.append(
            {
                "title": "It's a good thing.cutoff((optional, including the difference with the recommended expected profit)",
                "columns": ["cutoff", "Approval rate", "Bad rate", "Expected profits", "Difference with recommended expected profit"],
                "rows": alt_rows,
            }
        )
    if red_flags:
        tables.append(_red_flag_table(red_flags))
    return text, tables


def _render_design_cutoff_bands(o: dict):
    bands = [band for band in (o.get("bands") or []) if isinstance(band, dict)]
    red_flags = [flag for flag in (o.get("red_flags") or []) if isinstance(flag, dict)]
    red_items = [flag for flag in red_flags if flag.get("level") == "red"]
    approved = [band for band in bands if band.get("decision") == "approve"]
    rules = [
        rule for rule in (o.get("recommended_rules") or []) if isinstance(rule, dict)
    ]
    rule_text = rules[0].get("condition") if rules else "None"
    # LT-11 (B.1): the recommended cut carries its evidence -- the cumulative bad
    # rate and approval rate *at the approved frontier* (theLast one.approve - Yeah.'s own
    # cum_* fields the bands already carry), so Recommended cutshows why it is safe rather
    # than only naming the rule. Numbers are the bands' own fields (INV-1: no
    # re-computation). Frontier band = the approved band with the widest cumulative
    # approval (the boundary the cut lands on).
    frontier = max(
        approved,
        key=lambda b: (
            b.get("cum_approval_rate")
            if isinstance(b.get("cum_approval_rate"), (int, float))
            else -1.0
        ),
        default=None,
    )
    evidence = ""
    if rules and frontier is not None:
        evidence = (
            f"(Based on: cumulative bad rate through the customer base{_pct(frontier.get('cum_bad_rate'))},"
            f"Cumulative approval rate{_pct(frontier.get('cum_approval_rate'))},(Full-out)"
        )
    text = (
        f"**Design of the fraction strip is complete.**:Recommended cut`{rule_text}`((Rejection rules){evidence},"
        f"Pass.{len(approved)}/{len(bands)} A fractional belt, red flag.{len(red_flags)} item."
    )
    if red_items:
        names = ",".join(str(flag.get("code")) for flag in red_items)
        text += f" Red item:{names}."
    tables = [
        {
            "title": "Split Belt",
            "columns": [
                "band Intersection",
                "Samples as a percentage",
                "Bad rate",
                "Cumulative approval rate",
                "Cumulative bad rate",
                "Decision-making",
            ],
            "rows": [
                [
                    f"[{_fmt(band.get('lo'))},{_fmt(band.get('hi'))})",
                    _pct(band.get("pop_pct")),
                    _pct(band.get("bad_rate")),
                    _pct(band.get("cum_approval_rate")),
                    _pct(band.get("cum_bad_rate")),
                    _STRATEGY_DECISION_LABEL.get(
                        str(band.get("decision")), str(band.get("decision", ""))
                    ),
                ]
                for band in bands
            ],
        }
    ]
    if red_flags:
        tables.append(_red_flag_table(red_flags))
    return text, tables


def _render_compare_strategies(o: dict):
    if o.get("status") == "no_baseline":
        return (
            "**Policy comparison not implemented**:No baseline strategy provided; matrix, differences and label coveragen/a.",
            [],
        )
    matrix = o.get("matrix_2x2") if isinstance(o.get("matrix_2x2"), dict) else {}
    deltas = o.get("deltas") if isinstance(o.get("deltas"), dict) else {}
    red_flags = [flag for flag in (o.get("red_flags") or []) if isinstance(flag, dict)]
    text = f"**Policy comparison complete.**:{o.get('summary_text') or ''}"
    if o.get("label_coverage") is not None:
        text += f" Label Coverage{_pct(o.get('label_coverage'))}."
    conclusion = _compare_conclusion_line(deltas)
    if conclusion:
        text += f"\n\n{conclusion}"
    red_items = [flag for flag in red_flags if flag.get("level") == "red"]
    if red_items:
        names = ",".join(str(flag.get("code")) for flag in red_items)
        text += f" Red flag:{names}."

    def _cell(key: str) -> dict:
        return matrix.get(key) if isinstance(matrix.get(key), dict) else {}

    ba, on, ob, bd = (
        _cell("both_approve"),
        _cell("only_new"),
        _cell("only_baseline"),
        _cell("both_decline"),
    )
    # S6: the swap 2×2 is a matrix-heat card — each cell's own approved bad rate (0..1)
    # colors the heat chip (S3 matrix-heat kind reused); the count rides along as text.
    heat_columns = ["", "Baseline adopted", "Baseline rejection"]
    heat_rows = [
        ["New strategy is adopted.", _heat_cell(ba), _heat_cell(on)],
        ["New strategy rejected", _heat_cell(ob), _heat_cell(bd)],
    ]
    tables = [
        {
            "title": "swap 2×2 Bad-rate heat (including sample numbers)",
            "columns": heat_columns,
            "rows": heat_rows,
            "column_specs": [
                {"kind": "text"},
                {"kind": "matrix-heat"},
                {"kind": "matrix-heat"},
            ],
        },
        {
            "title": "Key indicators side by side (challengers)vs (baseline)",
            "columns": ["Indicators", "Challenger.−Baseline", "Direction"],
            "rows": [
                [
                    "Approval rate",
                    _pct(deltas.get("approval_rate")),
                    _delta_arrow(deltas.get("approval_rate")),
                ],
                [
                    "Passing the bad rate.",
                    _pct(deltas.get("approved_bad_rate")),
                    _delta_arrow(deltas.get("approved_bad_rate"), lower_is_better=True),
                ],
                [
                    "Expected profits",
                    _num(deltas.get("expected_profit")),
                    _delta_arrow(deltas.get("expected_profit")),
                ],
            ],
        },
    ]
    if red_flags:
        tables.append(_red_flag_table(red_flags))
    return text, tables


def _heat_cell(cell: dict) -> float:
    """matrix-heat value for a swap cell: its approved bad rate (0..1). The count is
    kept in the label the frontend renders alongside the heat chip."""
    try:
        return float(cell.get("bad_rate") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _delta_word(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Hold flat."
    if number > 0:
        return "Up"
    if number < 0:
        return "Down"
    return "Hold flat."


def _delta_arrow(value, *, lower_is_better: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Hold flat."
    if number == 0:
        return "Hold flat."
    improved = (number < 0) if lower_is_better else (number > 0)
    direction = "↑" if number > 0 else "↓"
    return f"{direction} {'More.' if improved else 'Worse.'}"


def _compare_conclusion_line(deltas: dict) -> str:
    """Templated Chinese conclusion — every number comes straight from the tool's
    deltas (INV-1: presentation only). Empty when there is no delta to talk about."""
    if not deltas:
        return ""
    approval = deltas.get("approval_rate")
    bad = deltas.get("approved_bad_rate")
    profit = deltas.get("expected_profit")
    if approval is None and bad is None and profit is None:
        return ""
    approval_word = _delta_word(approval)
    bad_word = _delta_word(bad)
    return (
        f"Conclusion: challengers are passing rates{approval_word} {abs(float(approval or 0)) * 100:.1f}pp I\'m not sure if you\'re going to be able to do this."
        f"The downfall of the customer base.{bad_word} {abs(float(bad or 0)) * 100:.2f}pp,"
        f"Changes in expected profits{float(profit or 0):.2f}."
    )


def _render_limit_pricing_matrix(o: dict):
    matrix = [cell for cell in (o.get("matrix") or []) if isinstance(cell, dict)]
    recommended = [
        item for item in (o.get("recommended") or []) if isinstance(item, dict)
    ]
    red_flags = [flag for flag in (o.get("red_flags") or []) if isinstance(flag, dict)]
    registered_artifacts = [
        item
        for item in (o.get("artifacts") or [])
        if isinstance(item, dict) and item.get("artifact_id")
    ]
    reco_keys = {
        (str(item.get("band")), _num(item.get("limit")), _num(item.get("rate")))
        for item in recommended
    }
    text = (
        f"**Amount×Price matrix complete.**:{len(matrix)} individualband×Amount×Pricing unit,"
        f"Recommendations{len(recommended)} Slotting (maximum profitable slot per band)."
    )
    red_items = [flag for flag in red_flags if flag.get("level") == "red"]
    if red_items:
        names = ",".join(str(flag.get("code")) for flag in red_items)
        text += f" Red flag:{names}."
    if registered_artifacts:
        text += f" Registered{len(registered_artifacts)} A file, downloadable from the strategic product card."

    def _cell_row(cell: dict) -> list:
        key = (str(cell.get("band")), _num(cell.get("limit")), _num(cell.get("rate")))
        recommended_mark = "★" if key in reco_keys else ""
        profit = cell.get("expected_profit")
        # Negative-profit cells are red-Dinby prefixing a marker the frontend maps to
        # the warning skin; recommended cells carry a ★ and are hoisted to the top.
        profit_text = _num(profit)
        try:
            if profit is not None and float(profit) < 0:
                profit_text = f"⚠{profit_text}"
        except (TypeError, ValueError):
            pass
        return [
            f"{recommended_mark}{cell.get('band', '')}",
            _num(cell.get("limit")),
            _pct(cell.get("rate")),
            _fmt(cell.get("count")),
            _pct(cell.get("pd")),
            _num(cell.get("el")),
            profit_text,
            _pct(cell.get("roa")),
            "Yes." if cell.get("feasible") else "Yes",
        ]

    # Recommended cells first (Top), then the rest in stable order.
    reco_cells = [
        cell
        for cell in matrix
        if (str(cell.get("band")), _num(cell.get("limit")), _num(cell.get("rate")))
        in reco_keys
    ]
    other_cells = [
        cell
        for cell in matrix
        if (str(cell.get("band")), _num(cell.get("limit")), _num(cell.get("rate")))
        not in reco_keys
    ]
    tables = [
        {
            "title": "Amount×Pricing Matrix (%2)★For the referral,⚠(for negative profit)",
            "columns": [
                "band",
                "Amount",
                "Age",
                "Number of samples",
                "PD",
                "EL",
                "Expected profits",
                "ROA",
                "It's possible.",
            ],
            "rows": [_cell_row(cell) for cell in [*reco_cells, *other_cells]],
        }
    ]
    if red_flags:
        tables.append(_red_flag_table(red_flags))
    return text, tables


def _render_profit_calc(o: dict):
    results = [row for row in (o.get("results") or []) if isinstance(row, dict)]
    warnings = [
        item for item in (o.get("quality_warnings") or []) if isinstance(item, dict)
    ]
    artifacts = [item for item in (o.get("artifacts") or []) if isinstance(item, dict)]
    registered_artifacts = [item for item in artifacts if item.get("artifact_id")]
    total_profit = sum(float(row.get("net_profit") or 0.0) for row in results)
    text = f"**Profit analysis complete.**:{len(results)} Group, total net profit{_num(total_profit)}."
    if warnings:
        text += f" {len(warnings)} A data quality hint."
    if registered_artifacts:
        text += f" Registered{len(registered_artifacts)} A file, downloadable from the strategic product card."
    elif artifacts:
        text += f" Generated{len(artifacts)} One document, but not yet registered for download."
    tables = [
        {
            "title": "Group profit results",
            "columns": [
                "Group",
                "Number of samples",
                "Income",
                "Expected losses",
                "Cost of funds",
                "Operating costs",
                "Net profit",
                "ROA",
            ],
            "rows": [
                [
                    str(row.get("segment", "")),
                    _fmt(row.get("count")),
                    _num(row.get("revenue")),
                    _num(row.get("expected_loss")),
                    _num(row.get("funding_cost")),
                    _num(row.get("operating_cost")),
                    _num(row.get("net_profit")),
                    _pct(row.get("roa")),
                ]
                for row in results
            ],
        }
    ]
    if warnings:
        tables.append(
            {
                "title": "Data quality tips",
                "columns": ["Code", "Impact Rows", "Annotations"],
                "rows": [
                    [
                        str(item.get("code", "")),
                        _fmt(item.get("count")),
                        str(item.get("message", "")),
                    ]
                    for item in warnings
                ],
            }
        )
    return text, tables


def _render_roll_rate_matrix(o: dict):
    states = [str(state) for state in (o.get("states") or [])]
    matrix = o.get("matrix") or []
    base_counts = o.get("base_counts") or {}
    warnings = [
        item
        for item in (o.get("data_quality_warnings") or [])
        if isinstance(item, dict)
    ]
    artifacts = [item for item in (o.get("artifacts") or []) if isinstance(item, dict)]
    registered_artifacts = [item for item in artifacts if item.get("artifact_id")]
    semantics = str(o.get("observation_semantics") or "adjacent_observation")
    semantics_text = "Neighbourly observation" if semantics == "adjacent_observation" else semantics
    text = f"**Roll-rate Matrix complete.**:{len(states)} State, caliber is{semantics_text}."
    if warnings:
        text += f" {len(warnings)} bar quality tips."
    if registered_artifacts:
        text += f" Registered{len(registered_artifacts)} A file, downloadable from the strategic product card."
    elif artifacts:
        text += f" Generated{len(artifacts)} One document, but not yet registered for download."

    rows = []
    for index, state in enumerate(states):
        raw_row = (
            matrix[index]
            if index < len(matrix) and isinstance(matrix[index], list)
            else []
        )
        rows.append(
            [
                state,
                _fmt(base_counts.get(state)),
                *[
                    _pct(raw_row[to_index] if to_index < len(raw_row) else None)
                    for to_index in range(len(states))
                ],
            ]
        )
    tables = [
        {
            "title": "NEOP rate",
            "columns": ["State of the beginning of period", "Base", *states],
            "rows": rows,
        }
    ]
    if warnings:
        tables.append(
            {
                "title": "Data quality tips",
                "columns": ["Code", "Annotations"],
                "rows": [
                    [str(item.get("code", "")), str(item.get("message", ""))]
                    for item in warnings
                ],
            }
        )
    return text, tables


def _render_adopt_strategy(o: dict):
    retired = [str(item) for item in (o.get("retired_strategy_ids") or [])]
    artifacts = [a for a in (o.get("artifacts") or []) if isinstance(a, dict)]
    text = (
        f"**The strategy has been adopted locally**:`{o.get('strategy_id', '')}` v{o.get('version', '')},"
        f"Asset status{o.get('asset_status', 'adopted_local')}(Compatibility status"
        f"{o.get('status', '')}),Retired{len(retired)} The old version."
        f"Generate{len(artifacts)} A delivery. Local adoption does not mean that the production environment is online."
    )
    tables = [
        {
            "title": "Delivery",
            "columns": ["Type", "Path"],
            "rows": [
                [str(a.get("kind", "")), str(a.get("path", ""))] for a in artifacts
            ],
        }
    ]
    if retired:
        tables.append(
            {
                "title": "Retire Strategy",
                "columns": ["Policyid"],
                "rows": [[item] for item in retired],
            }
        )
    return text, tables


def _render_challenger_report(o: dict):
    status = str(o.get("status") or "")
    artifacts = [a for a in (o.get("artifacts") or []) if isinstance(a, dict)]
    if status == "no_baseline":
        return "**Challenger comparison report**:No baseline provided (%)champion)Strategy, skip report.", []
    text = (
        f"**Challenger comparison report generated**:`{o.get('report_path', '')}`,"
        f"Registration{len(artifacts)} (c) A delivery."
    )
    tables = [
        {
            "title": "Delivery",
            "columns": ["Type", "Path"],
            "rows": [
                [str(a.get("kind", "")), str(a.get("path", ""))] for a in artifacts
            ],
        }
    ]
    return text, tables


def _render_strategy_doc(o: dict):
    sections = [str(item) for item in (o.get("sections") or [])]
    text = f"**Policy document generated**:`{o.get('doc_path', '')}`,Total{len(sections)} Chapters."
    tables = [
        {
            "title": "Document Chapter",
            "columns": ["#", "Chapter"],
            "rows": [
                [str(index), section] for index, section in enumerate(sections, start=1)
            ],
        }
    ]
    return text, tables


def _render_run_strategy_monitoring(o: dict):
    overall = str(o.get("overall_level") or "")
    checks = [c for c in (o.get("checks") or []) if isinstance(c, dict)]
    red_flags = [c for c in checks if c.get("level") == "red"]
    amber_flags = [c for c in checks if c.get("level") == "amber"]
    label = _MONITOR_LEVEL_LABEL.get(overall, overall)
    text = f"**Strategic surveillance complete.**:General rank [T]{label}]."
    if red_flags:
        names = ",".join(str(c.get("label") or c.get("id")) for c in red_flags)
        text += f" Red flag:{names}."
    if amber_flags:
        names = ",".join(str(c.get("label") or c.get("id")) for c in amber_flags)
        text += f" Yellow Flag:{names}."
    if overall == "red":
        text += "\n\n" + "\n".join(_MONITORING_RED_CHECKLIST)
    rows = [
        [
            str(c.get("label") or c.get("id") or ""),
            _MONITOR_LEVEL_LABEL.get(str(c.get("level")), str(c.get("level"))),
            _fmt(c.get("value")) if c.get("value") is not None else "n/a",
            str(c.get("message") or ""),
        ]
        for c in checks
    ]
    tables = [
        {
            "title": "Monitor the details.",
            "columns": ["Checkpoint", "Level", "Value", "Annotations"],
            "rows": rows,
        }
    ]
    drifted = [
        row for row in (o.get("top_drifted_features") or []) if isinstance(row, dict)
    ]
    if drifted:
        tables.append(
            {
                "title": "Characteristic driftTop",
                "columns": ["Characteristics", "CSI"],
                "rows": [
                    [str(row.get("feature") or ""), _fmt(row.get("csi"))]
                    for row in drifted[:10]
                ],
            }
        )
    return text, tables


def _render_apply_monitoring_disposition(o: dict):
    disposition = str(o.get("disposition") or "acknowledge")
    label = {
        "acknowledge": "Confirmed.",
        "observe": "Maintain and observe",
        "adjust_threshold": "Adjusting thresholds and reruning",
        "new_version": "Create a new version",
    }.get(disposition, disposition)
    level = str(o.get("overall_level") or "")
    level_label = _MONITOR_LEVEL_LABEL.get(level, level)
    text = f"**Control disposal implemented**:{label}"
    if level_label:
        text += f",Post-disposal rating [T]{level_label}]"
    resolved_run = o.get("resolved_monitoring_run_id")
    if resolved_run:
        text += f",Evidence Run`{resolved_run}`"
    if disposition == "new_version" and o.get("new_task_id"):
        text += (
            f".Created Policy Task`{o['new_task_id']}` and draft strategy"
            f"`{o.get('new_strategy_id', '')}`"
        )
    if disposition == "adjust_threshold" and o.get("monitoring_plan_revision"):
        text += f".The surveillance plan has been added torevision {o['monitoring_plan_revision']}"
    return text + ".", []


def _render_monitoring_report(o: dict):
    timeline = [row for row in (o.get("timeline") or []) if isinstance(row, dict)]
    overall = str(o.get("overall_level") or "")
    label = _MONITOR_LEVEL_LABEL.get(overall, overall) if overall else ""
    head = f"**Surveillance report generated**:`{o.get('report_path', '')}`"
    if label:
        head += f",Recent General Levels [T]{label}]"
    head += f",Historical monitoring{len(timeline)} - Second."
    next_action = (
        o.get("next_action") if isinstance(o.get("next_action"), dict) else None
    )
    if next_action and next_action.get("prompt"):
        head += f"\n\nNext:{next_action['prompt']}"
    tables = []
    if timeline:
        tables.append(
            {
                "title": "Monitor the sentencing timeline",
                "columns": ["Time", "General Level", "Sample Volume"],
                "rows": [
                    [
                        str(row.get("at") or ""),
                        _MONITOR_LEVEL_LABEL.get(
                            str(row.get("overall_level")),
                            str(row.get("overall_level") or ""),
                        ),
                        _fmt(row.get("row_count"))
                        if row.get("row_count") is not None
                        else "",
                    ]
                    for row in timeline
                ],
            }
        )
    return head, tables


def _render_mine_rules(o: dict):
    rules = [
        rule for rule in (o.get("candidate_rules") or []) if isinstance(rule, dict)
    ]
    red_flags = [flag for flag in (o.get("red_flags") or []) if isinstance(flag, dict)]
    n_rows = o.get("n_rows")
    text = (
        f"**The drill is complete.**:Yes.{_fmt(n_rows)} Proposed on line sample**{len(rules)}** Rule of rejection for candidacy"
        "(Presslift descending order; determining tree paths+ Single variable tangent two channels. Please reply to \" Select 1 \",3,5]/[\"and remove the two.\"/[The following is a list of rules to be adopted:"
    )
    red_items = [flag for flag in red_flags if flag.get("level") == "red"]
    if red_items:
        names = ",".join(str(flag.get("code")) for flag in red_items)
        text += f" Red flag:{names}."
    tables = []
    if rules:
        tables.append(
            {
                "title": "Candidate Rule (bylift (Deduction order)",
                "columns": ["#", "Rule", "Support", "Hit rate.", "lift", "Source"],
                "rows": [
                    [
                        str(index),
                        str(rule.get("condition", "")),
                        _pct(rule.get("support")),
                        _pct(rule.get("hit_bad_rate")),
                        _num(rule.get("lift")),
                        str(rule.get("source", "")),
                    ]
                    for index, rule in enumerate(rules, start=1)
                ],
            }
        )
    if red_flags:
        tables.append(_red_flag_table(red_flags))
    return text, tables


def _render_select_rule_set(o: dict):
    selected = [
        rule for rule in (o.get("selected_rules") or []) if isinstance(rule, dict)
    ]
    candidate_count = o.get("candidate_count")
    text = (
        f"**The rule book has been selected**:From{_fmt(candidate_count)} Selected from the list of candidates**{len(selected)}** Rule"
        "(The first command is effective in the order of selection. The rule set and the strategy will be evaluated after confirmation."
    )
    tables = []
    if selected:
        tables.append(
            {
                "title": "Selected rules (in order of hits)",
                "columns": ["#", "Rule", "Hit rate.", "lift", "Source"],
                "rows": [
                    [
                        str(index),
                        str(rule.get("condition", "")),
                        _pct(rule.get("hit_bad_rate"))
                        if rule.get("hit_bad_rate") is not None
                        else "n/a",
                        _num(rule.get("lift"))
                        if rule.get("lift") is not None
                        else "n/a",
                        str(rule.get("source", "")),
                    ]
                    for index, rule in enumerate(selected, start=1)
                ],
            }
        )
    return text, tables


def _render_evaluate_rule_set(o: dict):
    waterfall = [row for row in (o.get("waterfall") or []) if isinstance(row, dict)]
    residual = o.get("residual") if isinstance(o.get("residual"), dict) else {}
    combined = o.get("combined") if isinstance(o.get("combined"), dict) else {}
    red_flags = [flag for flag in (o.get("red_flags") or []) if isinstance(flag, dict)]
    text = (
        "**Rulebook assessment completed**:"
        f"Total rejection rate{_pct(combined.get('reject_rate'))},"
        f"Deny the customer base bad rate.{_pct(combined.get('rejected_bad_rate'))};"
        f"Residual pass rate{_pct(residual.get('approval_rate'))},"
        f"The downfall of the customer base.{_pct(residual.get('bad_rate'))}."
    )
    red_items = [
        flag
        for flag in red_flags
        if flag.get("code") in {"rule_shadowed", "high_overlap"}
    ]
    if red_items:
        names = ",".join(str(flag.get("code")) for flag in red_items)
        text += f" Call the police.:{names}."
    tables = []
    if waterfall:
        tables.append(
            {
                "title": "Hitfall falls (in order, first strike effective)",
                "columns": [
                    "Rule",
                    "Incremental hit.",
                    "Increment and bad rate",
                    "Cumulative rate of rejection",
                    "Cumulative rejection rate",
                ],
                "rows": [
                    [
                        str(row.get("rule_id", "")),
                        _fmt(row.get("incremental_hits")),
                        _pct(row.get("incremental_bad_rate")),
                        _pct(row.get("cum_reject_rate")),
                        _pct(row.get("cum_reject_bad_rate")),
                    ]
                    for row in waterfall
                ],
            }
        )
    overlap = o.get("overlap_matrix")
    if isinstance(overlap, list) and len(overlap) > 1:
        header = [f"R{index}" for index in range(1, len(overlap) + 1)]
        tables.append(
            {
                "title": "Rule-overlapping matrix (share of common lives)",
                "columns": ["", *header],
                "rows": [
                    [
                        f"R{i + 1}",
                        *[_pct(overlap[i][j]) for j in range(len(overlap[i]))],
                    ]
                    for i in range(len(overlap))
                ],
            }
        )
    if red_flags:
        tables.append(_red_flag_table(red_flags))
    return text, tables


LIFECYCLE_PRESENTERS = {
    "build_strategy": _render_build_strategy,
    "backtest_strategy": _render_backtest_strategy,
    "tradeoff_view": _render_tradeoff_view,
    "design_cutoff_bands": _render_design_cutoff_bands,
    "compare_strategies": _render_compare_strategies,
    "profit_calc": _render_profit_calc,
    "roll_rate_matrix": _render_roll_rate_matrix,
    "limit_pricing_matrix": _render_limit_pricing_matrix,
    "adopt_strategy": _render_adopt_strategy,
    "render_strategy_doc": _render_strategy_doc,
    "render_challenger_report": _render_challenger_report,
    "run_strategy_monitoring": _render_run_strategy_monitoring,
    "apply_monitoring_disposition": _render_apply_monitoring_disposition,
    "render_monitoring_report": _render_monitoring_report,
    "evaluate_rule_set": _render_evaluate_rule_set,
    "mine_rules": _render_mine_rules,
    "select_rule_set": _render_select_rule_set,
}

INTEGRITY_FAILURES = {}

__all__ = ["LIFECYCLE_PRESENTERS", "INTEGRITY_FAILURES"]
