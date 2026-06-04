from __future__ import annotations

from typing import Any

from marvis.formatting import period_text as _period_text
from marvis.formatting import psi_reference_month_text as _psi_reference_month_text
from marvis.formatting import ratio as _ratio
from marvis.formatting import score_interval as _score_interval

LAYOUT_BY_KEY = {
    "IMAGE:overall_model_effect": "kpi_cards",
    "IMAGE:loan_month_effect": "trend_table",
}

PSI_THRESHOLDS = [0.02, 0.10]

COLUMN_SPEC_BY_HEADER = {
    # split / time
    "Dataset":        {"kind": "split-badge"},
    "Month":          {"kind": "text"},
    "Time frame":      {"kind": "period"},
    # counts / share
    "Sample Volume":        {"kind": "databar", "color": "primary"},
    "Samples as a percentage":      {"kind": "text"},
    "Total sample":      {"kind": "databar", "color": "primary"},
    "Bad sample quantity":      {"kind": "databar", "color": "neutral"},
    "Overdue":      {"kind": "databar", "color": "neutral"},
    "Cumulative share":      {"kind": "text"},
    # rates / risk
    "Overdue rate":        {"kind": "percent-heat"},
    "Cumulative overdue rate":    {"kind": "percent-heat"},
    # S3 portfolio: NxN migration/flow matrix cells (colored from the cell's own
    # 0..1 rate, reusing the percent-heat chip skin). Header-keyed entries cover
    # the fixed columns the migration renderer emits; dynamic per-state columns
    # instead carry an explicit matrix-heat column_spec on the renderer's table.
    "Migration rate":        {"kind": "matrix-heat"},
    "Transfer rate":        {"kind": "matrix-heat"},
    # discrimination
    "KS":            {"kind": "databar-primary"},
    "KS(%)":         {"kind": "databar-primary"},
    "ks":            {"kind": "text"},
    "AUC":           {"kind": "databar", "color": "accent"},
    "AUC(%)":        {"kind": "databar", "color": "accent"},
    "5%Headlift":    {"kind": "databar", "color": "accent"},
    "5%Endlift":    {"kind": "databar", "color": "accent"},
    "Single grouplift":      {"kind": "databar", "color": "accent"},
    "Cumulativelift":      {"kind": "databar-primary"},
    # stability
    "PSI":            {"kind": "psi", "thresholds": PSI_THRESHOLDS},
    "PSI(First month benchmark)":  {"kind": "psi", "thresholds": PSI_THRESHOLDS},
    "PSI(End-month benchmark)":  {"kind": "psi", "thresholds": PSI_THRESHOLDS},
    "PSI(Ring)":      {"kind": "psi", "thresholds": PSI_THRESHOLDS},
    "PSI(It's a lot more than the previous sample month.)": {"kind": "psi", "thresholds": PSI_THRESHOLDS},
    "PSIMonth of reference":      {"kind": "text"},
    "PSI vs baseline":{"kind": "psi", "thresholds": PSI_THRESHOLDS},
    # stress
    "Category":           {"kind": "text"},
    "KS_baseline":    {"kind": "text"},
    "KS_after":       {"kind": "databar", "color": "accent"},
    "KS_delta":       {"kind": "psi", "thresholds": [0.01, 0.03]},
    # feature
    "Rank":           {"kind": "text"},
    "Characteristics":           {"kind": "text"},
    "Importance":         {"kind": "databar-primary"},
}


def _column_specs_for(headers: list[str]) -> list[dict[str, Any]]:
    return [COLUMN_SPEC_BY_HEADER.get(header, {"kind": "text"}) for header in headers]


SECTION_THEME = {
    "Sample status": "cool-blue",
    "Overall effect&Stability": "warm-orange",
    "Month effect&Stability": "deep-purple",
    "Sorting of boxes": "heatmap",
    "Independent 10-centre semibox": "heatmap",
    "Characteristic importance": "cool-blue",
    "Pressure test": "warning-red",
    "ROC&KS Curve": "deep-purple",
}


def metric_table_sections_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not payload:
        return []

    basic_info = _as_dict(payload.get("basic_info"))
    effectiveness = _as_dict(payload.get("effectiveness"))
    stress_test = _as_dict(payload.get("stress_test"))
    roc_ks_curves = _as_dict(effectiveness.get("roc_ks_curves"))
    split_summary = _as_list(basic_info.get("split_summary"))
    monthly_distribution = _as_list(basic_info.get("monthly_distribution"))
    overall = _as_list(effectiveness.get("overall"))
    bin_tables = _as_dict(effectiveness.get("bin_tables"))
    independent_bin_tables = _as_dict(
        effectiveness.get("independent_quantile_bin_tables")
    )
    feature_importance = _as_list(basic_info.get("feature_importance"))
    per_category = _as_list(stress_test.get("per_category"))
    unclassified_features = [
        str(feature) for feature in _as_list(stress_test.get("unclassified_features"))
    ]

    sections = [
        {
            "title": "Sample status",
            "tables": [
                _table(
                    "IMAGE:sample_overall_distribution",
                    "Total distribution of samples",
                    ["Dataset", "Time frame", "Sample Volume", "Samples as a percentage", "Bad sample quantity", "Overdue rate"],
                    _sample_overall_rows(split_summary),
                ),
                _table(
                    "IMAGE:sample_month_distribution",
                    "Samples distributed monthly",
                    ["Month", "Sample Volume", "Samples as a percentage", "Bad sample quantity", "Overdue rate"],
                    _sample_month_rows(monthly_distribution),
                ),
            ],
        },
        {
            "title": "Overall effect&Stability",
            "tables": [
                _table(
                    "IMAGE:overall_model_effect",
                    "Overall effect&Stability",
                    [
                        "Dataset",
                        "Time frame",
                        "Sample Volume",
                        "Overdue rate",
                        "Bad sample quantity",
                        "KS(%)",
                        "AUC(%)",
                        "5%Headlift",
                        "5%Endlift",
                        "PSI",
                    ],
                    _overall_model_effect_rows(overall, split_summary),
                )
            ],
        },
        {
            "title": "Month effect&Stability",
            "tables": [
                _table(
                    "IMAGE:loan_month_effect",
                    "Month effect&Stability",
                    [
                        "Month",
                        "Sample Volume",
                        "Overdue rate",
                        "Bad sample quantity",
                        "KS(%)",
                        "AUC(%)",
                        "5%Headlift",
                        "5%Endlift",
                        "PSI(First month benchmark)",
                        "PSI(End-month benchmark)",
                        "PSI(It's a lot more than the previous sample month.)",
                        "PSIMonth of reference",
                    ],
                    _monthly_effect_rows(
                        _as_list(effectiveness.get("monthly_ks")),
                        _as_list(effectiveness.get("monthly_psi")),
                    ),
                )
            ],
        },
        {
            "title": "Sorting of boxes",
            "tables": _ranking_tables_for_splits(
                bin_tables,
                image_key_prefix="ranking_table",
                title_suffix="According totrainBox",
            ),
        },
        *(
            [
                {
                    "title": "Independent 10-centre semibox",
                    "tables": _ranking_tables_for_splits(
                        independent_bin_tables,
                        image_key_prefix="independent_quantile_ranking_table",
                        title_suffix="Independence 10 points",
                    ),
                }
            ]
            if _bin_tables_have_rows(independent_bin_tables)
            else []
        ),
        {
            "title": "Characteristic importance",
            "tables": [
                _table(
                    "IMAGE:top20_feature_ranking",
                    "Top20 Characteristic importance",
                    ["Rank", "Characteristics", "Category", "Importance"],
                    [
                        [
                            _value(row.get("rank")),
                            _value(row.get("feature")),
                            _value(row.get("category") or row.get("Category")),
                            _decimal(row.get("importance"), digits=4),
                        ]
                        for row in feature_importance[:20]
                        if isinstance(row, dict)
                    ],
                )
            ],
        },
        {
            "title": "Pressure test",
            "tables": [
                _table(
                    "IMAGE:pressure_ks_table",
                    "Pressure test",
                    ["Category", "Status", "KS_baseline", "KS_after", "KS_delta", "PSI vs baseline"],
                    _pressure_test_rows(_as_dict(stress_test.get("baseline")), per_category),
                ),
                _table(
                    "TEXT:stress_category_coverage",
                    "Pressure test class coverage",
                    ["Overall state", "Number of features not classified", "Unclassified features"],
                    [[
                        _stress_status_label(stress_test.get("status")),
                        _integer(len(unclassified_features)),
                        _feature_name_preview(unclassified_features),
                    ]],
                ),
            ],
        },
    ]
    if any(isinstance(roc_ks_curves.get(split), dict) for split in ("train", "test", "oot")):
        sections.append(_roc_ks_section(roc_ks_curves))
    return [_tag_section(section) for section in sections]


def _bin_tables_have_rows(bin_tables: dict[str, Any]) -> bool:
    return any(_as_list(bin_tables.get(split)) for split in ("train", "test", "oot"))


def _ranking_tables_for_splits(
    bin_tables: dict[str, Any],
    *,
    image_key_prefix: str,
    title_suffix: str,
) -> list[dict[str, Any]]:
    ranking_headers = [
        "Total sample",
        "Cumulative share",
        "Overdue",
        "Overdue rate",
        "Cumulative overdue rate",
        "Single grouplift",
        "Cumulativelift",
        "ks",
    ]
    return [
        _table(
            f"IMAGE:{image_key_prefix}_{split}",
            title,
            [title, *ranking_headers],
            _ranking_rows(_as_list(bin_tables.get(split))),
        )
        for split, title in (
            ("train", f"Train({title_suffix})"),
            ("test", f"Test({title_suffix})"),
            ("oot", f"OOT({title_suffix})"),
        )
    ]


def _table(key: str, title: str, headers: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "headers": headers,
        "rows": rows,
        "layout": LAYOUT_BY_KEY.get(key, "table"),
        "column_specs": _column_specs_for(headers),
    }


def _tag_section(section: dict) -> dict:
    return {**section, "section_theme": SECTION_THEME.get(section["title"], "cool-blue")}


def _roc_ks_section(roc_ks_curves: dict[str, Any]) -> dict[str, Any]:
    curves: dict[str, dict[str, Any]] = {}
    for split in ("train", "test", "oot"):
        raw = roc_ks_curves.get(split)
        if not isinstance(raw, dict):
            continue
        curves[split] = {
            "fpr": [float(v) for v in raw.get("fpr") or []],
            "tpr": [float(v) for v in raw.get("tpr") or []],
            "ks_curve": [float(v) for v in raw.get("ks_curve") or []],
            "ks": _scalar(raw.get("ks")),
            "population_at_ks": _scalar(raw.get("population_at_ks")),
        }
    return {
        "title": "ROC&KS Curve",
        "tables": [
            {
                "key": "ROC_KS_CURVES",
                "title": "ROC&KS Curve",
                "layout": "roc_ks_curve",
                "headers": [],
                "rows": [],
                "column_specs": [],
                "curves": curves,
            }
        ],
    }


def _sample_overall_rows(rows: list[Any]) -> list[list[Any]]:
    total_count = sum(_number(row, "sample_count") for row in rows if isinstance(row, dict))
    return [
        [
            _value(row.get("split")),
            _period_text(row.get("period_start"), row.get("period_end"), default="-"),
            _integer(row.get("sample_count")),
            _percent(_ratio(_number(row, "sample_count"), total_count)),
            _integer(row.get("bad_count")),
            _percent(row.get("bad_rate")),
        ]
        for row in rows
        if isinstance(row, dict)
    ]


def _sample_month_rows(rows: list[Any]) -> list[list[Any]]:
    total_count = sum(_number(row, "sample_count") for row in rows if isinstance(row, dict))
    return [
        [
            _value(row.get("month")),
            _integer(row.get("sample_count")),
            _percent(_ratio(_number(row, "sample_count"), total_count)),
            _integer(row.get("bad_count")),
            _percent(row.get("bad_rate")),
        ]
        for row in rows
        if isinstance(row, dict)
    ]


def _overall_model_effect_rows(rows: list[Any], split_summary: list[Any]) -> list[list[Any]]:
    split_by_name = {
        str(row.get("split")): row
        for row in split_summary
        if isinstance(row, dict)
    }
    formatted_rows: list[list[Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        split = str(row.get("split") or "")
        split_row = split_by_name.get(split) or {}
        formatted_rows.append([
            _value(split),
            _period_text(split_row.get("period_start"), split_row.get("period_end"), default="-"),
            _integer(row.get("sample_count")),
            _percent(row.get("bad_rate")),
            _integer(row.get("bad_count")),
            _percent_point(row.get("ks")),
            _percent_point(row.get("auc")),
            _decimal(row.get("head_lift_5pct"), digits=2),
            _decimal(row.get("tail_lift_5pct"), digits=2),
            "BASE" if split == "train" else _decimal(row.get("psi_vs_train"), digits=3),
        ])
    return formatted_rows


def _monthly_effect_rows(monthly_ks: list[Any], monthly_psi: list[Any]) -> list[list[Any]]:
    by_month: dict[str, dict[str, Any]] = {}
    for row in monthly_ks:
        if isinstance(row, dict):
            month = str(row.get("month") or "")
            by_month.setdefault(month, {}).update({
                "sample_count": row.get("sample_count"),
                "bad_rate": row.get("bad_rate"),
                "bad_count": row.get("bad_count"),
                "ks": row.get("ks"),
                "auc": row.get("auc"),
                "head_lift_5pct": row.get("head_lift_5pct"),
                "tail_lift_5pct": row.get("tail_lift_5pct"),
            })
    for row in monthly_psi:
        if isinstance(row, dict):
            month = str(row.get("month") or "")
            by_month.setdefault(month, {}).update({
                "psi_first_month": row.get("psi_first_month"),
                "psi_last_month": row.get("psi_last_month"),
                "psi_mom": row.get("psi_mom"),
                "psi_mom_reference_month": row.get("psi_mom_reference_month"),
                "psi_mom_has_calendar_gap": row.get("psi_mom_has_calendar_gap"),
            })

    months = sorted(month for month in by_month if month)
    first_month = months[0] if months else ""
    last_month = months[-1] if months else ""
    return [
        [
            month,
            _integer(data.get("sample_count")),
            _percent(data.get("bad_rate")),
            _integer(data.get("bad_count")),
            _percent_point(data.get("ks")),
            _percent_point(data.get("auc")),
            _decimal(data.get("head_lift_5pct"), digits=2),
            _decimal(data.get("tail_lift_5pct"), digits=2),
            "BASE" if month == first_month else _decimal(data.get("psi_first_month"), digits=3),
            "BASE" if month == last_month else _decimal(data.get("psi_last_month"), digits=3),
            "-" if month == first_month else _decimal(data.get("psi_mom"), digits=3),
            "-" if month == first_month else _psi_reference_month_text(
                _value(data.get("psi_mom_reference_month")),
                has_calendar_gap=bool(data.get("psi_mom_has_calendar_gap")),
            ),
        ]
        for month, data in ((month, by_month[month]) for month in months)
    ]


def _ranking_rows(rows: list[Any]) -> list[list[Any]]:
    valid_rows = [row for row in rows if isinstance(row, dict)]
    total = sum(_number(row, "sample_count") for row in valid_rows)
    total_bad = sum(_number(row, "bad_count") for row in valid_rows)
    overall_bad_rate = _ratio(total_bad, total)
    cumulative_count = 0.0
    cumulative_bad = 0.0
    formatted_rows: list[list[Any]] = []
    for row in valid_rows:
        cumulative_count += _number(row, "sample_count")
        cumulative_bad += _number(row, "bad_count")
        cumulative_bad_rate = _ratio(cumulative_bad, cumulative_count)
        formatted_rows.append([
            _score_interval(row.get("score_lower"), row.get("score_upper")),
            _integer(row.get("sample_count")),
            _percent(_ratio(cumulative_count, total)),
            _integer(row.get("bad_count")),
            _percent(row.get("bad_rate")),
            _percent(cumulative_bad_rate),
            _decimal(row.get("lift"), digits=2),
            _decimal(_ratio(cumulative_bad_rate, overall_bad_rate), digits=2),
            _decimal(row.get("ks"), digits=4),
        ])
    return formatted_rows


def _pressure_test_rows(baseline: dict[str, Any], rows: list[Any]) -> list[list[Any]]:
    baseline_ks = baseline.get("ks")
    return [
        [
            _value(row.get("category")),
            _stress_status_label(row.get("status"), row.get("error")),
            _decimal(baseline_ks, digits=4),
            _decimal(row.get("ks_after"), digits=4),
            _decimal(row.get("ks_delta"), digits=4),
            _decimal(row.get("psi_vs_baseline"), digits=4),
        ]
        for row in rows
        if isinstance(row, dict)
    ]


def _feature_name_preview(features: list[str], *, limit: int = 20) -> str:
    visible = features[:limit]
    text = ",".join(visible) if visible else "-"
    if len(features) > limit:
        return f"{text} Wait.{len(features)} individual"
    return text


def _stress_status_label(status: Any, error: Any = None) -> str:
    if error and not status:
        status = "error"
    return {
        "completed": "Completed",
        "skipped": "Skip",
        "error": "Unusual",
        "partial": "Partially completed",
        "failed": "Failed",
    }.get(str(status or "completed"), str(status or "completed"))


def _integer(value: Any) -> str:
    numeric = _to_float(value)
    return "-" if numeric is None else f"{numeric:,.0f}"


def _percent(value: Any) -> str:
    numeric = _to_float(value)
    return "-" if numeric is None else f"{numeric:.2%}"


def _percent_point(value: Any) -> str:
    numeric = _to_float(value)
    return "-" if numeric is None else f"{numeric * 100:.1f}"


def _decimal(value: Any, *, digits: int) -> str:
    numeric = _to_float(value)
    return "-" if numeric is None else f"{numeric:.{digits}f}"


def _number(row: dict[str, Any], key: str) -> float:
    return _to_float(row.get(key)) or 0.0


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _scalar(value: Any, default: float = 0.0) -> float:
    parsed = _to_float(value)
    return parsed if parsed is not None else default


def _value(value: Any) -> str:
    return "-" if value is None or value == "" else str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
