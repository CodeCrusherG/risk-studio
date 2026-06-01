from __future__ import annotations

from marvis.model_algorithms import (
    is_platform_default_training_description,
    model_training_report_text,
)
from marvis.validation.results import (
    ConsistencyStatus,
    OverallRow,
    SplitRow,
    ValidationResults,
)


COMPUTED_REPORT_TEXT_KEYS = frozenset({
    "TEXT:sample_period",
    "TEXT:sample_start_month",
    "TEXT:sample_end_month",
    "TEXT:data_source_summary",
    "TEXT:dataset_split_summary",
    "TEXT:train_test_period",
    "TEXT:train_test_ratio",
    "TEXT:oot_period",
    "TEXT:train_count",
    "TEXT:test_count",
    "TEXT:oot_count",
    "TEXT:train_bad_rate",
    "TEXT:test_bad_rate",
    "TEXT:oot_bad_rate",
    "TEXT:oot_ks",
    "TEXT:oot_psi",
    "TEXT:reproducibility_summary",
    "TEXT:pmml_scoring_summary",
    "TEXT:stress_test_summary",
})

AGENT_CONFIRMED_REPORT_TEXT_KEYS = frozenset({
    "TEXT:pressure_test_summary",
    "TEXT:pressure_impact_recommendation",
    "TEXT:final_validation_conclusion",
    "TEXT:model_training_description",
})


def report_text_values_from_results(
    results: ValidationResults,
    *,
    report_values: dict[str, str] | None = None,
    manual_values: dict[str, str] | None = None,
) -> dict[str, str]:
    overall_by_split = {row.split: row for row in results.effectiveness.overall}
    split_summary = {row.split: row for row in results.basic_info.split_summary}
    sample_period = _period_text(
        results.basic_info.sample_period[0],
        results.basic_info.sample_period[1],
    )
    version_suffix = f"{results.model_version}Version" if results.model_version else ""

    stress_summary = _stress_text(results)
    scoring_summary = _score_test_text(results)
    values: dict[str, str] = {
        "TEXT:report_title": f"{results.model_name}Model{version_suffix}Authentication Document",
        "TEXT:model_name": results.model_name,
        "TEXT:model_version": results.model_version,
        "TEXT:algorithm": results.algorithm,
        "TEXT:model_training_description": model_training_report_text(
            results.algorithm,
            results.basic_info.hyperparameters,
        ),
        "TEXT:sample_period": sample_period,
        "TEXT:sample_start_month": results.basic_info.sample_period[0],
        "TEXT:sample_end_month": results.basic_info.sample_period[1],
        "TEXT:data_source_summary": f"Model sample overlay{sample_period},The platform automatically identifies the sample cycle and distribution based on the sample file.",
        "TEXT:dataset_split_summary": _dataset_split_text(split_summary),
        "TEXT:train_test_period": _train_test_period_text(split_summary),
        "TEXT:train_test_ratio": _train_test_ratio_text(split_summary),
        "TEXT:oot_period": _split_period_text(split_summary.get("oot")),
        "TEXT:train_count": _count(split_summary.get("train")),
        "TEXT:test_count": _count(split_summary.get("test")),
        "TEXT:oot_count": _count(split_summary.get("oot")),
        "TEXT:train_bad_rate": _percent(split_summary.get("train")),
        "TEXT:test_bad_rate": _percent(split_summary.get("test")),
        "TEXT:oot_bad_rate": _percent(split_summary.get("oot")),
        "TEXT:oot_ks": _decimal4(overall_by_split.get("oot")),
        "TEXT:oot_psi": _decimal4_psi(overall_by_split.get("oot")),
        # Keep the historical placeholder populated so existing Word templates
        # render unchanged. V2 templates may use the explicit PMML key below.
        "TEXT:reproducibility_summary": scoring_summary,
        "TEXT:stress_test_summary": stress_summary,
        "TEXT:pressure_test_summary": stress_summary,
    }
    if results.pmml_scoring is not None:
        values["TEXT:pmml_scoring_summary"] = scoring_summary
    return merge_report_text_values(
        values,
        report_values=report_values,
        manual_values=manual_values,
    )


def computed_report_text_values_from_payload(payload: dict) -> dict[str, str]:
    basic_info = payload.get("basic_info", {})
    values: dict[str, str] = {}
    sample_period = basic_info.get("sample_period")
    if isinstance(sample_period, (list, tuple)) and len(sample_period) >= 2:
        start = str(sample_period[0])
        end = str(sample_period[1])
        period = _period_text(start, end)
        values.update({
            "TEXT:sample_period": period,
            "TEXT:sample_start_month": start,
            "TEXT:sample_end_month": end,
            "TEXT:data_source_summary": f"Model sample overlay{period},The platform automatically identifies the sample cycle and distribution based on the sample file.",
        })

    split_summary = _split_rows_from_payload(basic_info.get("split_summary", []))
    if split_summary:
        values.update({
            "TEXT:dataset_split_summary": _dataset_split_text(split_summary),
            "TEXT:train_test_period": _train_test_period_text(split_summary),
            "TEXT:train_test_ratio": _train_test_ratio_text(split_summary),
            "TEXT:oot_period": _split_period_text(split_summary.get("oot")),
            "TEXT:train_count": _count(split_summary.get("train")),
            "TEXT:test_count": _count(split_summary.get("test")),
            "TEXT:oot_count": _count(split_summary.get("oot")),
            "TEXT:train_bad_rate": _percent(split_summary.get("train")),
            "TEXT:test_bad_rate": _percent(split_summary.get("test")),
            "TEXT:oot_bad_rate": _percent(split_summary.get("oot")),
        })

    for row in payload.get("effectiveness", {}).get("overall", []):
        if row.get("split") != "oot":
            continue
        oot = _overall_row_from_payload(row)
        values["TEXT:oot_ks"] = _decimal4(oot)
        values["TEXT:oot_psi"] = _decimal4_psi(oot)
        break
    return values


def merge_report_text_values(
    generated_values: dict[str, str],
    *,
    report_values: dict[str, str] | None = None,
    manual_values: dict[str, str] | None = None,
) -> dict[str, str]:
    values = dict(generated_values)
    for candidate_values, allowed_computed_keys in (
        (report_values, AGENT_CONFIRMED_REPORT_TEXT_KEYS),
        (manual_values, frozenset()),
    ):
        if not candidate_values:
            continue
        values.update({
            key: value
            for key, value in _with_text_prefix(candidate_values).items()
            if _should_accept_report_text(
                key,
                value,
                generated_values=generated_values,
                allowed_computed_keys=allowed_computed_keys,
            )
        })
    return _apply_report_text_aliases(values)


def _should_accept_report_text(
    key: str,
    value: str,
    *,
    generated_values: dict[str, str],
    allowed_computed_keys: frozenset[str],
) -> bool:
    if not str(value or "").strip():
        return False
    if key in COMPUTED_REPORT_TEXT_KEYS and key not in allowed_computed_keys:
        return False
    if key in AGENT_CONFIRMED_REPORT_TEXT_KEYS and key not in allowed_computed_keys:
        return False
    if key == "TEXT:model_training_description" and is_platform_default_training_description(
        value,
        generated_values.get("TEXT:algorithm"),
    ):
        return False
    return True


def _apply_report_text_aliases(values: dict[str, str]) -> dict[str, str]:
    values = dict(values)
    recommendation = values.get("TEXT:pressure_recommendation_summary")
    if recommendation is not None:
        values["TEXT:pressure_impact_recommendation"] = recommendation
    pressure_summary = str(values.get("TEXT:pressure_test_summary") or "").strip()
    stress_summary = str(values.get("TEXT:stress_test_summary") or "").strip()
    if not pressure_summary and stress_summary:
        values["TEXT:pressure_test_summary"] = stress_summary
    return values


def _with_text_prefix(values: dict[str, str]) -> dict[str, str]:
    return {
        key if key.startswith("TEXT:") else f"TEXT:{key}": str(value)
        for key, value in values.items()
        if value is not None
    }


def _split_rows_from_payload(rows) -> dict[str, SplitRow]:
    split_rows: dict[str, SplitRow] = {}
    if not isinstance(rows, list):
        return split_rows
    for row in rows:
        if not isinstance(row, dict) or not row.get("split"):
            continue
        split_rows[str(row["split"])] = SplitRow(
            split=str(row["split"]),
            sample_count=int(row.get("sample_count") or 0),
            bad_count=int(row.get("bad_count") or 0),
            bad_rate=float(row.get("bad_rate") or 0.0),
            period_start=str(row.get("period_start") or ""),
            period_end=str(row.get("period_end") or ""),
        )
    return split_rows


def _overall_row_from_payload(row: dict) -> OverallRow:
    return OverallRow(
        split=str(row.get("split") or ""),
        ks=float(row.get("ks") or 0.0),
        psi_vs_train=float(row.get("psi_vs_train") or 0.0),
        sample_count=int(row.get("sample_count") or 0),
        bad_rate=float(row.get("bad_rate") or 0.0),
        bad_count=int(row.get("bad_count") or 0),
        auc=float(row.get("auc") or 0.0),
        head_lift_5pct=_optional_float(row.get("head_lift_5pct")),
        tail_lift_5pct=_optional_float(row.get("tail_lift_5pct")),
    )


def _count(row) -> str:
    return str(row.sample_count) if row else "Sample data not available pending review"


def _percent(row) -> str:
    return f"{row.bad_rate:.2%}" if row else "Sample data not available pending review"


def _period_text(start: str, end: str) -> str:
    if not start and not end:
        return "No sample cycle pending review"
    if not start:
        return str(end)
    if not end:
        return str(start)
    return str(start) if start == end else f"{start}-{end}"


def _split_period_text(row: SplitRow | None) -> str:
    if not row or row.sample_count == 0:
        return "No sample cycle pending review"
    return _period_text(row.period_start, row.period_end)


def _train_test_period_text(split_summary: dict[str, SplitRow]) -> str:
    return _combined_split_period_text(
        split_summary.get("train"),
        split_summary.get("test"),
    )


def _train_test_ratio_text(split_summary: dict[str, SplitRow]) -> str:
    train_count = split_summary.get("train").sample_count if split_summary.get("train") else 0
    test_count = split_summary.get("test").sample_count if split_summary.get("test") else 0
    total = train_count + test_count
    if total == 0:
        return "No training at this time/Test samples pending review"
    return f"{train_count / total:.2%}:{test_count / total:.2%}"


def _combined_split_period_text(*rows: SplitRow | None) -> str:
    starts = [
        row.period_start
        for row in rows
        if row and row.sample_count and row.period_start
    ]
    ends = [
        row.period_end
        for row in rows
        if row and row.sample_count and row.period_end
    ]
    if not starts and not ends:
        return "No sample cycle pending review"
    start = min(starts) if starts else ""
    end = max(ends) if ends else ""
    return _period_text(start, end)


def _dataset_split_text(split_summary: dict[str, SplitRow]) -> str:
    train = split_summary.get("train")
    test = split_summary.get("test")
    oot = split_summary.get("oot")
    return (
        f"Training sample{train.sample_count if train else 0} Article,"
        f"Test sample{test.sample_count if test else 0} Article,"
        f"OOT Sample{oot.sample_count if oot else 0} Article;"
        f"Training/Test Period is{_train_test_period_text(split_summary)},"
        f"OOT Periodicity is{_split_period_text(oot)}."
    )


def _decimal4(row) -> str:
    return f"{row.ks:.4f}" if row else "Not yet.OOTModel effects data pending review"


def _decimal4_psi(row) -> str:
    return f"{row.psi_vs_train:.4f}" if row else "Not yet.OOTStability data pending review"


def _reproducibility_text(results: ValidationResults) -> str:
    if results.reproducibility is None:
        raise ValueError("legacy validation results have no reproducibility evidence")
    summary = results.reproducibility.summary
    status_word = {
        ConsistencyStatus.PASS: "Pass.",
        ConsistencyStatus.REVIEW: "Subject to review",
        ConsistencyStatus.FAIL: "I can't pass.",
    }[summary.status]
    return (
        f"Yeah.{results.reproducibility.sample_size} The three-way score is compared by the line sample."
        f"Alignment{summary.match_count} Okay, difference.{summary.mismatch_count} Okay."
        f"Max. Absolute{summary.max_abs_diff:.6f},Recoverability validation{status_word}."
    )


def _score_test_text(results: ValidationResults) -> str:
    if results.pmml_scoring is None:
        return _reproducibility_text(results)
    scoring = results.pmml_scoring
    status_word = "Pass." if scoring.status == "pass" else "I can't pass."
    return (
        f"PMMLRating Full{scoring.input_row_count} The sample is a score."
        f"Success{scoring.success_count} Okay, failure.{scoring.failure_count} Okay."
        f"Empty{scoring.null_count} Line, non-limited{scoring.non_finite_count} All right;"
        f"Output Field{scoring.output_field},Use{scoring.engine} "
        f"Batch scores, time-consuming{scoring.elapsed_seconds:.3f} Seconds,"
        f"Swallow.{scoring.rows_per_second:.2f} Okay./Seconds, test.{status_word}."
    )


def _stress_text(results: ValidationResults) -> str:
    items = []
    status_prefix = {
        "partial": "The stress test is partially completed, with attention to the unusual categories:",
        "failed": "The stress test was not completed and the anomaly must be repaired:",
        "skipped": "Pressure test not performed valid category:",
    }.get(results.stress_test.status, "")
    if results.stress_test.unclassified_features:
        features = results.stress_test.unclassified_features
        items.append(
            f"Unclassified features{len(features)} One:{_feature_name_preview(features)}"
        )
    for item in results.stress_test.per_category:
        if item.status == "skipped":
            items.append(f"{item.category}:No emulator characteristics found for pressure testing")
            continue
        if item.error or item.status == "error":
            items.append(f"{item.category}:{item.error}")
            continue
        delta = item.ks_delta if item.ks_delta is not None else 0.0
        psi = item.psi_vs_baseline if item.psi_vs_baseline is not None else 0.0
        items.append(
            f"{item.category}(Set-9999 {len(item.dropped_features)} Characteristics:"
            f"KS Change{delta:+.4f},PSI {psi:.4f}"
        )
    text = ";".join(items) or "No pressure test results"
    return f"{status_prefix}{text}" if status_prefix else text


def _feature_name_preview(features: list[str], *, limit: int = 20) -> str:
    visible = features[:limit]
    text = ",".join(visible)
    if len(features) > limit:
        return f"{text} Wait.{len(features)} individual"
    return text


def _optional_float(value) -> float | None:
    return None if value is None else float(value)
