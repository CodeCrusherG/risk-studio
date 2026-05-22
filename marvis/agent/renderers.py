"""Tool-output renderers for V2 plan-driver messages.

Each renderer turns a Tool's raw output into ``(markdown_text, table_blocks)``.
This facade keeps cross-domain dispatch outside ``plan_driver.py``; large
domain families live in ``marvis.agent.presenters`` and register here without
moving presentation rules back into the execution loop.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from marvis.agent.presenters.modeling_evidence import (
    MODELING_EVIDENCE_PRESENTERS,
)
from marvis.agent.presenters.runtime import build_trusted_presenter_runtime
from marvis.agent.presenters.strategy_exploration import (
    STRATEGY_EXPLORATION_PRESENTERS,
)
from marvis.agent.presenters._shared import (
    MONITOR_LEVEL_LABEL as _MONITOR_LEVEL_LABEL,
    format_number as _num,
    format_percent as _pct,
    format_value as _fmt,
)
from marvis.agent.presenters import strategy as _strategy_presenters
from marvis.agent.presenters.strategy import (
    STRATEGY_RENDERERS,
    strategy_integrity_failure,
)
from marvis.orchestrator.evidence import artifact_bindings, artifact_refs


_TRUSTED_RUNTIME_PRESENTERS = {
    **MODELING_EVIDENCE_PRESENTERS,
    **STRATEGY_EXPLORATION_PRESENTERS,
}
if len(_TRUSTED_RUNTIME_PRESENTERS) != (
    len(MODELING_EVIDENCE_PRESENTERS) + len(STRATEGY_EXPLORATION_PRESENTERS)
):
    raise RuntimeError("duplicate authenticated runtime presenter refs")


# ---------------------------------------------------------------------------
# tool -> table registry (decision #4 in the driver spec)
# Each renderer turns a tool's raw output into (markdown text, [table dicts]).
# Task differences land HERE; the driver loop above stays task-agnostic. A table
# dict is {title, columns, rows} — the frontend maps it onto renderMetricTableSection.
# ---------------------------------------------------------------------------
def _names(items) -> list[str]:
    out = []
    for item in items or []:
        out.append(item[0] if isinstance(item, (list, tuple)) and item else item)
    return [str(x) for x in out]


def _range_text(minimum, maximum) -> str:
    if minimum is None and maximum is None:
        return "n/a"
    return f"{_fmt(minimum)} - {_fmt(maximum)}"


def _triple(item):
    """A (feature, ks, reason) row from a leakage/suspected entry, tolerant of shape."""
    if isinstance(item, (list, tuple)):
        feat = str(item[0]) if len(item) > 0 else ""
        ks = item[1] if len(item) > 1 else None
        reason = str(item[2]) if len(item) > 2 else ""
        return feat, ks, reason
    return str(item), None, ""


def _key_label(column, dictionary: dict) -> str:
    """A raw key-column code, appended with "(Meaning: ...)" when the task's data
    dictionary has a business-name entry for it (GAP-4); the bare code otherwise."""
    name = str(column) if column is not None else "?"
    meaning = dictionary.get(name) if dictionary else None
    return f"{name}(Meaning:{meaning})" if meaning else name


def _render_screen(o: dict):
    selected = o.get("selected") or []
    leak = o.get("leakage") or []
    susp = o.get("suspected") or []
    unusable = o.get("unusable") or []
    excluded_categorical = o.get("excluded_categorical") or []
    scores = o.get("scores") if isinstance(o.get("scores"), dict) else {}
    leak_names = _names(leak)
    susp_names = _names(susp)
    n = o.get("n_screened") or o.get("n") or (len(selected) + len(leak) + len(susp))
    text = (
        f"**Feature filter complete.**:From {n} Proposal to retain **{len(selected)}** Characteristics.\n"
        f"- Dismissed.**Leak.** {len(leak_names)} individual"
        + (f"(Like {leak_names[:3]})" if leak_names else "")
        + "\n"
        f"- Suspect**Model Output/Rating**Columns {len(susp_names)} individual"
        + (f"(Like {susp_names[:5]})" if susp_names else "")
        + "\n"
        f"- Remove**Not Available**(Constant/Scatter) {len(unusable)} individual"
    )
    if excluded_categorical:
        preview = ",".join(
            f"{item.get('column')}(Base{item.get('cardinality')})"
            for item in excluded_categorical[:8]
            if isinstance(item, dict)
        )
        more = (
            f" Wait {len(excluded_categorical)} individual"
            if len(excluded_categorical) > 8
            else ""
        )
        text += (
            f"\n- **{len(excluded_categorical)} Unmolded Class Columns**:{preview}{more};"
            "If needed,Please. woe_encode_categorical Encoding,Or change it. catboost(Original Support Category Column)."
        )
    nan_dropped = o.get("nan_labels_dropped") or 0
    if nan_dropped:
        text += (
            f"\n- 🚩 **{nan_dropped} Line Tabs are empty(NaN)Discarded by Confirm**,"
            "This time, this is the screening. KS/IV The leak determination is based only on labeled samples."
        )
    tables = []
    if selected:
        rows = []
        for feat in selected[:20]:
            s = scores.get(feat) if isinstance(scores.get(feat), dict) else {}
            rows.append(
                [
                    feat,
                    _num(s.get("ks")),
                    _num(s.get("iv")),
                    _pct(s.get("missing_rate")),
                ]
            )
        tables.append(
            {
                "title": "Select Character(Front20)",
                "columns": ["Characteristics", "KS", "IV", "Missing Rate"],
                "rows": rows,
            }
        )
    if leak:
        tables.append(
            {
                "title": f"Possible leak.(KS≥Threshold,Total{len(leak)})",
                "columns": ["Characteristics", "KS", "Reason"],
                "rows": [
                    [f, _num(k), r] for f, k, r in (_triple(i) for i in leak[:20])
                ],
            }
        )
    if susp:
        tables.append(
            {
                "title": f"Suspected Model Output/Breakdown of assessments(Total{len(susp)})",
                "columns": ["Characteristics", "KS", "Reason"],
                "rows": [
                    [f, _num(k), r] for f, k, r in (_triple(i) for i in susp[:20])
                ],
            }
        )
    if unusable:
        rows = []
        for item in unusable[:20]:
            if isinstance(item, (list, tuple)):
                rows.append(
                    [
                        str(item[0]) if item else "",
                        str(item[1]) if len(item) > 1 else "",
                    ]
                )
            else:
                rows.append([str(item), ""])
        tables.append(
            {
                "title": f"Remove·Not Available(Constant/Scatter,Total{len(unusable)})",
                "columns": ["Characteristics", "Reason"],
                "rows": rows,
            }
        )
    return text, tables


def _render_select(o: dict):
    """FS-1 multivariate refinement gate: IV floor + correlation (+ optional VIF) funnel
    between the sanity-level screen and tuning. Surfaces per-stage drop counts/reasons so
    the confirm gate reads as a funnel, not just a final list."""
    selected = o.get("selected") or []
    dropped = o.get("dropped") or []
    scores = o.get("scores") if isinstance(o.get("scores"), dict) else {}
    n_in = len(selected) + len(dropped)
    low_iv = [
        item
        for item in dropped
        if isinstance(item, (list, tuple))
        and len(item) > 1
        and "low" in str(item[1])
        and "IV" in str(item[1])
    ]
    collinear = [
        item
        for item in dropped
        if isinstance(item, (list, tuple))
        and len(item) > 1
        and "collinear" in str(item[1])
    ]
    high_vif = [
        item
        for item in dropped
        if isinstance(item, (list, tuple)) and len(item) > 1 and "VIF" in str(item[1])
    ]
    top_k_dropped = [
        item
        for item in dropped
        if isinstance(item, (list, tuple)) and len(item) > 1 and "top_k" in str(item[1])
    ]
    other = [
        item
        for item in dropped
        if item not in low_iv
        and item not in collinear
        and item not in high_vif
        and item not in top_k_dropped
    ]
    text = (
        f"**Select feature completed**:From {n_in} The best of the candidates. **{len(selected)}** Characteristics"
        f"(Phase-out {len(dropped)} individual).\n"
        f"- IV Bottom-line phase-out {len(low_iv)} individual\n"
        f"- Relevance to Redundancy {len(collinear)} individual\n"
        f"- High VIF Phase-out {len(high_vif)} individual\n"
        f"- Over top_k Phase-out {len(top_k_dropped)} individual"
    )
    if other:
        text += f"\n- Other reasons for phasing out {len(other)} individual"
    fit_rows = o.get("fit_rows")
    fit_split = o.get("fit_split")
    if fit_rows is not None:
        text += f"\n\nStatistical calibration:{fit_split or 'train'} Go, go, go! {fit_rows} Okay.."
    tables = []
    if selected:
        rows = []
        for feat in selected[:20]:
            s = scores.get(feat) if isinstance(scores.get(feat), dict) else {}
            rows.append([feat, _num(s.get("iv")), _num(s.get("ks"))])
        tables.append(
            {
                "title": f"Final list(Front20,Total{len(selected)})",
                "columns": ["Characteristics", "IV", "KS"],
                "rows": rows,
            }
        )
    if dropped:
        rows = []
        for item in dropped[:30]:
            if isinstance(item, (list, tuple)) and item:
                feat = str(item[0])
                reason = str(item[1]) if len(item) > 1 else ""
            else:
                feat, reason = str(item), ""
            rows.append([feat, reason])
        tables.append(
            {
                "title": f"Phase-out list(Front30,Total{len(dropped)})",
                "columns": ["Characteristics", "Reason"],
                "rows": rows,
            }
        )
    return text, tables


def _render_choose_modeling_spec(o: dict):
    recipes = [str(item) for item in (o.get("recipes") or [])]
    target_type = str(o.get("target_type") or "binary")
    sample_weight_col = str(o.get("sample_weight_col") or "")
    metric_policy = str(o.get("metric_policy") or "")
    text = (
        f"**Model specifications generated**:Target type `{target_type}`,"
        f"Algorithm {'/'.join(recipes) or '-'},Select Policy `{metric_policy}`."
    )
    tables = [
        {
            "title": "Modeling Specifications",
            "columns": ["Item", "Value"],
            "rows": [
                ["Target type", target_type],
                ["Main reference algorithm", str(o.get("recipe") or "")],
                ["Training algorithms", "/".join(recipes)],
                ["Sample weight column", sample_weight_col or "Do Not Use"],
                ["Number of candidates", _fmt(o.get("feature_count", ""))],
                ["Number of reference rounds", _fmt(o.get("n_trials", ""))],
                ["Select Indicators", metric_policy],
            ],
        }
    ]
    eligible = o.get("eligible_algorithms") or []
    disabled = [
        item for item in (o.get("disabled_algorithms") or []) if isinstance(item, dict)
    ]
    if eligible or disabled:
        tables.append(
            {
                "title": "Algorithms Availability",
                "columns": ["Algorithm", "Status", "Annotations"],
                "rows": (
                    [[str(recipe), "Available", ""] for recipe in eligible]
                    + [
                        [
                            str(item.get("recipe", "")),
                            "Not Available",
                            str(item.get("reason", "")),
                        ]
                        for item in disabled
                    ]
                ),
            }
        )
    diagnostics = [
        item
        for item in (o.get("sample_weight_diagnostics") or [])
        if isinstance(item, dict)
    ]
    if diagnostics:
        tables.append(
            {
                "title": "Sample weight candidate diagnosis",
                "columns": ["Columns", "Status", "Missing Rate", "Scope", "Mean", "Annotations"],
                "rows": [
                    [
                        str(item.get("column") or ""),
                        "Available" if item.get("valid") else "Checked",
                        _pct(item.get("missing_rate")),
                        _range_text(item.get("min"), item.get("max")),
                        _fmt(item.get("mean")),
                        str(item.get("reason") or "Access mode characteristics excluded"),
                    ]
                    for item in diagnostics
                ],
            }
        )
    warnings = [str(item) for item in (o.get("warnings") or [])]
    if warnings:
        text += "\n" + "\n".join(f"- {warning}" for warning in warnings)
    return text, tables


def _render_configure_tuning(o: dict):
    tune_enabled = bool(o.get("tune_enabled"))
    sample_weight_col = str(o.get("sample_weight_col") or "")
    budgets = (
        o.get("n_trials_by_recipe")
        if isinstance(o.get("n_trials_by_recipe"), dict)
        else {}
    )
    recipes = [str(item) for item in (o.get("recipes") or []) if str(item)]
    total_n_trials = o.get("total_n_trials")
    multi = len(budgets) > 1
    if multi:
        budget_note = ",".join(
            f"{recipe}={budgets[recipe]}" for recipe in recipes if recipe in budgets
        )
        text = (
            f"**Participation Configuration Generated**:Candidate algorithm {'/'.join(recipes)},"
            f"{'Each algorithm is executed separately.' if tune_enabled else 'Skip'}Two-stage random search"
            f"(Algorithmic budget {budget_note};Total budget for multi-calculations=ΣBudgets per formulation={_fmt(total_n_trials)} Wheel)."
        )
    else:
        text = (
            f"**Participation Configuration Generated**:Algorithm `{o.get('recipe', '')}`,"
            f"{'Implementation' if tune_enabled else 'Skip'}Two-stage random search,"
            f"Rounds {o.get('n_trials', 0)}."
        )
    rows = [
        ["Target type", str(o.get("target_type") or "")],
        ["Algorithm", "/".join(recipes) if recipes else str(o.get("recipe") or "")],
        ["Random Search", "Yes." if tune_enabled else "Yes"],
    ]
    if multi:
        rows.append(
            [
                "Altitude of budget(Rounds,Total budget=ΣBudgets per formulation)",
                ",".join(
                    f"{recipe}={budgets[recipe]}"
                    for recipe in recipes
                    if recipe in budgets
                ),
            ]
        )
        rows.append(["Total budget", _fmt(total_n_trials)])
    else:
        rows.append(["Number of reference rounds", _fmt(o.get("n_trials", ""))])
    rows.append(["Sample weight column", sample_weight_col or "Do Not Use"])
    rows.append(["Annotations", str(o.get("reason") or "")])
    tables = [
        {
            "title": " Access Configuration",
            "columns": ["Item", "Value"],
            "rows": rows,
        }
    ]
    params = o.get("params") if isinstance(o.get("params"), dict) else {}
    if params:
        tables.append(
            {
                "title": "Fixed/Control Parameters",
                "columns": ["Parameters", "Value"],
                "rows": [[str(key), _fmt(value)] for key, value in params.items()],
            }
        )
    return text, tables


def _render_tune(o: dict):
    best_params = o.get("best_params") or {}
    best_metrics = o.get("best_metrics") or {}
    trials = [t for t in (o.get("trials") or []) if isinstance(t, dict)]
    text = f"**Relocation complete.**:{o.get('n_trials', '?')} Wheel search,Select the best supersengine combination."
    tables = []
    if trials:
        # trials leaderboard (G4): each trial's train/test/oot KS + overfit gap,
        # ranked by the in-time selection score (OOT is the unbiased final metric).
        ranked = sorted(
            trials,
            key=lambda t: (
                t.get("score")
                if isinstance(t.get("score"), (int, float))
                else float("-inf")
            ),
            reverse=True,
        )
        rows = []
        for rank, trial in enumerate(ranked[:15], start=1):
            train_ks, test_ks = trial.get("train_ks"), trial.get("test_ks")
            # overfit gaps: prefer stored values, fall back to deriving train-test.
            gap_tt = trial.get("overfit_gap_tt")
            if (
                gap_tt is None
                and isinstance(train_ks, (int, float))
                and isinstance(test_ks, (int, float))
            ):
                gap_tt = train_ks - test_ks
            rows.append(
                [
                    str(rank),
                    _num(train_ks),
                    _num(test_ks),
                    _num(trial.get("oot_ks")),
                    _num(trial.get("test_auc")),
                    _num(trial.get("oot_auc")),
                    _num(trial.get("lift_head_5")),
                    _num(trial.get("lift_head_10")),
                    _num(trial.get("lift_tail_5")),
                    _num(trial.get("lift_tail_10")),
                    _num(gap_tt),
                    _num(trial.get("overfit_gap_to")),
                ]
            )
        tables.append(
            {
                "title": "trials Line(Press in-time Picking Eclipse;Front15)",
                "columns": [
                    "#",
                    "train_ks",
                    "test_ks",
                    "oot_ks",
                    "test_auc",
                    "oot_auc",
                    "Headlift5%",
                    "Headlift10%",
                    "Endlift5%",
                    "Endlift10%",
                    "Compromisegap(tt)",
                    "Compromisegap(to)",
                ],
                "rows": rows,
            }
        )
    if best_metrics:
        tables.append(
            {
                "title": "Best trial Indicators",
                "columns": ["Indicators", "Value"],
                "rows": [[k, _fmt(v)] for k, v in best_metrics.items()],
            }
        )
    if best_params:
        tables.append(
            {
                "title": "Best cross-check.",
                "columns": ["Parameters", "Value"],
                "rows": [[k, _fmt(v)] for k, v in best_params.items()],
            }
        )
    return text, tables


def _render_train(o: dict):
    metrics = o.get("metrics") or {}
    text = "**Training complete.**."
    tables = []
    if metrics:
        scalar = {
            k: v for k, v in metrics.items() if isinstance(v, (int, float, str, bool))
        }
        if scalar:
            tables.append(
                {
                    "title": "Model indicators",
                    "columns": ["Indicators", "Value"],
                    "rows": [[k, _fmt(v)] for k, v in scalar.items()],
                }
            )
    importance = o.get("feature_importance") or []
    rows = []
    for item in importance[:15]:
        if isinstance(item, (list, tuple)) and item:
            rows.append([str(item[0]), _fmt(item[1]) if len(item) > 1 else ""])
    if rows:
        tables.append(
            {"title": "Characteristic importance(Front15)", "columns": ["Characteristics", "Importance"], "rows": rows}
        )
    return text, tables


# C9: champion-selection metric labels emitted by the tool
# (marvis/packs/modeling/train_tools.py). The renderer maps each LABEL to the
# per-experiment value used for selection so the evidence sentence cites the axis
# the champion actually won on, not a hard-coded OOT KS. Kept in sync with
# train_tools._CHAMPION_OVERFIT_PENALTY / BINARY_SELECTION_METRIC /
# RESPONSE_LIFT_SELECTION_METRIC; test_strategy_development guards drift.
_CHAMPION_OVERFIT_PENALTY = 0.5
_BINARY_SELECTION_METRIC = "test_ks(overfit-penalized)"
_RESPONSE_LIFT_SELECTION_METRIC = "test_lift_head_10"


def _penalized_test_ks(metrics: dict):
    """Mirror of train_tools._overfit_penalized_test_ks: ``test_ks - 0.5*max(0,
    train_ks - test_ks)``, weighted-aware. Returns None when test_ks is missing so
    the evidence line falls back to omitting the experiment (INV-1: recomputes only
    the already-computed KS numbers, same formula that drove selection)."""
    test_ks = metrics.get("weighted_test_ks")
    if not isinstance(test_ks, (int, float)):
        test_ks = metrics.get("test_ks")
    if not isinstance(test_ks, (int, float)):
        return None
    train_ks = metrics.get("weighted_train_ks")
    if not isinstance(train_ks, (int, float)):
        train_ks = metrics.get("train_ks")
    gap = (
        float(train_ks) - float(test_ks) if isinstance(train_ks, (int, float)) else 0.0
    )
    return float(test_ks) - _CHAMPION_OVERFIT_PENALTY * max(0.0, gap)


def _key_value(key: str):
    """Per-experiment value extractor that reads a plain metrics dict key."""

    def _extract(metrics: dict):
        value = metrics.get(key)
        return float(value) if isinstance(value, (int, float)) else None

    return _extract


def _selection_axis(o: dict):
    """C9: resolve (display_label, value_of, higher_is_better) from the tool's
    emitted ``selection_metric`` LABEL so the evidence sentence renders the true
    selection axis. ``selection_metric`` is a presentation label, not a metrics key,
    so each label maps to the extractor that fetches its per-experiment value.
    Falls back to the per-target_type defaults for legacy outputs that predate the
    selection_metric field (the fallback label no longer claims 'OOT KS' unless OOT
    KS was in fact the basis for that target type)."""
    sel = str(o.get("selection_metric") or "")
    if sel == _BINARY_SELECTION_METRIC:
        return ("Press test KS(Im gonna make it work.)", _penalized_test_ks, True)
    if sel == _RESPONSE_LIFT_SELECTION_METRIC:
        return ("Press test Head10%Raise", _key_value("test_lift_head_10"), True)
    if sel == "oot_rmse":
        return ("Press OOT RMSE", _key_value("oot_rmse"), False)
    if sel == "oot_macro_auc":
        return ("Press OOT macro-AUC", _key_value("oot_macro_auc"), True)
    if sel == "oot_logloss":
        return ("Press OOT logloss", _key_value("oot_logloss"), False)
    # Legacy fallback (no selection_metric field): keep today's per-target_type
    # basis so replayed/cached outputs do not crash. This is the ONLY path that may
    # still label 'OOT KS', and only because that was the historical binary default.
    target_type = str(o.get("target_type") or "binary")
    if target_type == "continuous":
        return ("Press OOT RMSE", _key_value("oot_rmse"), False)
    if target_type == "multiclass":
        return ("Press OOT macro-AUC", _key_value("oot_macro_auc"), True)
    return ("Press OOT KS", _key_value("oot_ks"), True)


def _champion_evidence_text(
    experiments, best_id, value_of, selector_label, higher_is_better
) -> str:
    """LT-11 (B.1/B.2) + C9: champion evidence -- the SELECTION metric's champion
    value and the gap to the runner-up algorithm on that SAME axis, both read from
    the experiments' own metrics via ``value_of`` (INV-1: presentation only, the gap
    is a subtraction on existing fields). Because the axis is now the one the
    champion actually won on, the 'High'/'Low' direction word is truthful by
    construction; a defensive guard emits neutral phrasing if the champion is
    somehow not the extreme. Empty when the champion or a runner-up value is
    unavailable."""

    def _val(exp):
        return value_of(exp.get("metrics") or {})

    champion = next((e for e in experiments if e.get("experiment_id") == best_id), None)
    champion_value = _val(champion) if champion is not None else None
    if champion_value is None:
        return ""
    others = [
        (e, _val(e))
        for e in experiments
        if e.get("experiment_id") != best_id and _val(e) is not None
    ]
    if not others:
        return f"(Basis:{selector_label}={champion_value:.4f},For the only comparable algorithm)"
    runner_up, runner_value = (
        max(others, key=lambda item: item[1])
        if higher_is_better
        else min(others, key=lambda item: item[1])
    )
    gap = champion_value - runner_value
    champion_leads = gap >= 0 if higher_is_better else gap <= 0
    if not champion_leads:
        # Defensive: champion is not the extreme on this axis. Do not assert 'High'/'Low';
        # state the values without a false lead claim.
        return (
            f"(Basis:{selector_label}={champion_value:.4f},"
            f"Min Yu {runner_up.get('recipe', '?')}({runner_value:.4f})"
            f",The difference. {abs(gap):.4f})"
        )
    return (
        f"(Basis:{selector_label}={champion_value:.4f},"
        f"Less Excellent {runner_up.get('recipe', '?')}({runner_value:.4f})"
        f"{'High' if higher_is_better else 'Low'} {abs(gap):.4f})"
    )


def _render_train_models(o: dict):
    experiments = [e for e in (o.get("experiments") or []) if isinstance(e, dict)]
    best_id = o.get("best_experiment_id")
    best_recipe = o.get("best_recipe")
    target_type = str(o.get("target_type") or "binary")
    tables = []
    rows = []
    best_metrics: dict = {}
    if target_type == "continuous":
        metric_columns = [
            "train_rmse",
            "test_rmse",
            "oot_rmse",
            "test_mae",
            "oot_mae",
            "test_r2",
            "oot_r2",
        ]
    elif target_type == "multiclass":
        metric_columns = [
            "train_macro_auc",
            "test_macro_auc",
            "oot_macro_auc",
            "test_logloss",
            "oot_logloss",
            "test_accuracy",
            "oot_accuracy",
        ]
    else:
        metric_columns = ["train_ks", "test_ks", "oot_ks", "test_auc", "oot_auc"]
    # C9: the evidence SENTENCE metric comes from the tool's emitted selection_metric
    # (not a hard-coded per-target_type key). The comparison TABLE columns above are
    # the full metric grid and stay unchanged. selection_axis falls back to the
    # per-target_type default only for legacy outputs lacking selection_metric.
    selector_label, value_of, higher_is_better = _selection_axis(o)
    for exp in experiments:
        metrics = exp.get("metrics") or {}
        is_best = exp.get("experiment_id") == best_id
        if is_best:
            best_metrics = metrics
        rows.append(
            [str(exp.get("recipe", "?")) + (" ★" if is_best else "")]
            + [_num(metrics.get(column)) for column in metric_columns]
        )
    if len(experiments) > 1:
        # LT-11 (B.1/B.2) + C9: the champion choice carries its evidence -- the REAL
        # selection metric it won on (selector_label from selection_metric), the
        # champion's own value on that axis, and the gap to the runner-up algorithm on
        # that SAME axis so the user sees what the champion actually beat. All numbers
        # are the experiments' own already-computed metrics (INV-1: presentation only;
        # the penalized-KS value recomputes the same formula that drove selection).
        evidence = _champion_evidence_text(
            experiments, best_id, value_of, selector_label, higher_is_better
        )
        text = (
            f"**Training complete.**:Comparison {len(experiments)} An algorithm.,"
            f"Best **{best_recipe}**(★;{selector_label}){evidence}."
        )
        tables.append(
            {
                "title": "Candidate model comparison",
                "columns": ["Algorithm", *metric_columns],
                "rows": rows,
            }
        )
    else:
        text = "**Training complete.**."
    # the best model's full metrics (mirrors the single-model Model indicators table)
    scalar = {
        k: v for k, v in best_metrics.items() if isinstance(v, (int, float, str, bool))
    }
    if scalar:
        tables.append(
            {
                "title": "Model indicators",
                "columns": ["Indicators", "Value"],
                "rows": [[k, _fmt(v)] for k, v in scalar.items()],
            }
        )
    return text, tables


def _render_compare(o: dict):
    experiments = o.get("experiments") or []
    rows = []
    for exp in experiments:
        if not isinstance(exp, dict):
            continue
        caps = exp.get("capabilities") or {}
        rows.append(
            [
                exp.get("recipe") or "?",
                "Yes." if caps.get("pmml_supported") else "Yes",
                "Yes." if caps.get("handoff_supported") else "Yes",
                "Yes." if caps.get("native_model_supported") else "Yes",
                caps.get("reason") or "",
            ]
        )
    tables = []
    if rows:
        tables.append(
            {
                "title": "Post-training mobility",
                "columns": ["Algorithm", "PMML", "Handover Certification", "Native model", "Annotations"],
                "rows": rows,
            }
        )
    return f"**Experimental comparison completed.**:Total {len(experiments)} An experimental candidate..", tables


def _render_select_experiment(o: dict):
    selected = o.get("selected_experiment_id") or ""
    recipe = o.get("recipe") or "?"
    metric = o.get("selection_metric") or ""
    reason = o.get("selection_reason") or ""
    caps = o.get("capabilities") or {}
    text = f"**Final Experiment Selected**:`{selected}`({recipe});{reason}"
    rows = [
        ["PMML", "Yes." if caps.get("pmml_supported") else "Yes"],
        ["Handover Certification", "Yes." if caps.get("handoff_supported") else "Yes"],
        ["Native model", "Yes." if caps.get("native_model_supported") else "Yes"],
    ]
    if caps.get("reason"):
        rows.append(["Annotations", caps.get("reason")])
    policy = (
        o.get("policy_decision") if isinstance(o.get("policy_decision"), dict) else {}
    )
    if policy:
        rows.append(["Policy door control", policy.get("status") or "not_requested"])
        violations = [
            str(item.get("message") or item.get("code") or "")
            for item in (policy.get("violations") or [])
            if isinstance(item, dict)
        ]
        if violations:
            rows.append(["Policy statement", "; ".join(item for item in violations if item)])
        if policy.get("override_reason"):
            rows.append(["Override", policy.get("override_reason")])
    tables = [
        {
            "title": f"Final model delivery capacity({metric})",
            "columns": ["Capacity", "Status"],
            "rows": rows,
        }
    ]
    metrics = o.get("metrics") or {}
    if metrics:
        tables.append(
            {
                "title": "Final model indicators",
                "columns": ["Indicators", "Value"],
                "rows": [[key, _fmt(value)] for key, value in metrics.items()],
            }
        )
    return text, tables


def _render_report(o: dict):
    path = o.get("report_path") or ""
    sections = [
        section
        for section in (o.get("section_status") or [])
        if isinstance(section, dict)
    ]
    available = sum(1 for section in sections if section.get("available"))
    skipped = len(sections) - available
    text = (
        f"**Model development report generated**:`{path}`"
        f"(Operational chapters {available}/{len(sections)} Generable"
        + (f",{skipped} Short Inputs/Skip" if skipped else "")
        + ",Downloadable in Right Bar)."
    )
    tables = []
    if sections:
        tables.append(
            {
                "title": "Status of the Chapters of the Report",
                "columns": ["Chapter", "Status", "Annotations"],
                "rows": [
                    [
                        str(section.get("section", "")),
                        "Generable" if section.get("available") else "Missing Input/Skip",
                        str(section.get("reason") or ""),
                    ]
                    for section in sections
                ],
            }
        )
    calibration_table = _calibration_table(o.get("calibration"))
    if calibration_table:
        tables.append(calibration_table)
    score_band_table = _score_band_table(o.get("score_bands"))
    if score_band_table:
        tables.append(score_band_table)
    return text, tables


def _render_reports(o: dict):
    reports = [item for item in (o.get("reports") or []) if isinstance(item, dict)]
    primary_path = str(o.get("report_path") or "")
    generated = [item for item in reports if str(item.get("report_path") or "").strip()]
    text = (
        f"**Model development report generated**:Total {len(generated)} Grandpa."
        + (f",Main report `{primary_path}`" if primary_path else "")
        + ".Please use the results below this Article(Download Model Development Report)button."
    )
    tables = []
    if reports:
        tables.append(
            {
                "title": "Report on candidate models",
                "columns": ["Experiment", "Algorithm", "Status", "Report"],
                "rows": [
                    [
                        str(item.get("experiment_id") or ""),
                        str(item.get("recipe") or ""),
                        "Generated"
                        if str(item.get("report_path") or "").strip()
                        else "Missing",
                        str(item.get("report_path") or ""),
                    ]
                    for item in reports
                ],
            }
        )
    return text, tables


# VD-4: calibration/score_bands are already produced by generate_model_report
# (report_tools.py::_artifact_calibration_rows / _score_band_rows) and land in
# the Excel workbook, but never reached the agent-conversation payload at all
# -- these two helpers reshape the same numbers (no new computation, INV-1)
# into the {title, columns, rows, chart} shape agentMessageTablesHtml expects,
# where `chart` carries the coordinate-ready series for the frontend SVG.
def _calibration_table(rows) -> dict | None:
    rows = [row for row in (rows or []) if isinstance(row, dict)]
    if not rows:
        return None
    summary = next((row for row in rows if row.get("score_type") == "summary"), {})
    points = [
        row
        for row in rows
        if row.get("score_type") == "raw" and row.get("avg_predicted_pd") is not None
    ]
    chart = {
        "kind": "calibration_curve",
        "points": [
            {
                "avg_predicted_pd": float(row["avg_predicted_pd"]),
                "observed_bad_rate": float(row["observed_bad_rate"]),
                "sample_count": int(row.get("sample_count") or 0),
                "bin": row.get("bin"),
            }
            for row in points
            if row.get("observed_bad_rate") is not None
        ],
        "brier_raw": summary.get("brier_raw"),
        "brier_calibrated": summary.get("brier_calibrated"),
        "ece_raw": summary.get("ece_raw"),
        "ece_calibrated": summary.get("ece_calibrated"),
    }
    table_rows = [row for row in rows if row.get("score_type") in ("raw", "calibrated")]
    return {
        "title": "Probability calibration(Reliability Curve)",
        "columns": [
            "Type",
            "Box",
            "Forecast Probability Range",
            "Sample Volume",
            "Projected average",
            "Actual bad rate",
            "Offset",
        ],
        "rows": [
            [
                "Original" if row.get("score_type") == "raw" else "After calibration,",
                _num(row.get("bin")),
                f"{_num(row.get('prob_lower'))} - {_num(row.get('prob_upper'))}",
                _num(row.get("sample_count")),
                _num(row.get("avg_predicted_pd")),
                _num(row.get("observed_bad_rate")),
                _num(row.get("abs_gap")),
            ]
            for row in table_rows
        ],
        "chart": chart,
    }


def _score_band_table(rows) -> dict | None:
    rows = [row for row in (rows or []) if isinstance(row, dict)]
    if not rows:
        return None
    # One split at a time reads clearest as a bar+line combo; oot (or the first
    # split present) mirrors what a risk reviewer checks first for cutoff work.
    preferred_order = ["oot", "test", "train"]
    available_splits = {row.get("split") for row in rows}
    split = next(
        (s for s in preferred_order if s in available_splits), rows[0].get("split")
    )
    split_rows = [row for row in rows if row.get("split") == split]
    split_rows.sort(key=lambda row: row.get("bin") if row.get("bin") is not None else 0)
    has_unscored = any(int(row.get("unscored_count") or 0) > 0 for row in split_rows)
    chart = {
        "kind": "score_band_bars",
        "split": split,
        "bands": [
            {
                "bin": row.get("bin"),
                "score_lower": row.get("score_lower"),
                "score_upper": row.get("score_upper"),
                "sample_count": row.get("sample_count"),
                "bad_rate": row.get("bad_rate"),
            }
            for row in split_rows
        ],
    }
    columns = [
        "Box",
        "Fractional interval",
        "Sample Volume",
        "Bad rate",
        "Cumulative rate of rejection",
        "Rejecting crowd failure rate",
        "lift",
    ]
    if has_unscored:
        columns.extend(["Rating coverage", "Unrated"])
    table_rows = []
    for row in split_rows:
        values = [
            _num(row.get("bin")),
            f"{_num(row.get('score_lower'))} - {_num(row.get('score_upper'))}",
            _num(row.get("sample_count")),
            _num(row.get("bad_rate")),
            _num(row.get("cum_reject_rate", row.get("cum_count_pct"))),
            _num(row.get("cum_bad_rate")),
            _num(row.get("lift")),
        ]
        if has_unscored:
            values.extend(
                [
                    _num(row.get("score_coverage")),
                    _num(row.get("unscored_count")),
                ]
            )
        table_rows.append(values)
    return {
        "title": f"Rating Session({split})",
        "columns": columns,
        "rows": table_rows,
        "chart": chart,
    }


def _render_feature_metrics(o: dict):
    metrics = [
        metric for metric in (o.get("metrics") or []) if isinstance(metric, dict)
    ]
    # FEATURE §2: every metric is independently selectable. A missing key means
    # "not selected", while a present key with ``None`` means "selected but not
    # computable" and must retain its structured reason.
    has_iv = any("iv" in metric for metric in metrics)
    has_ks = any("ks" in metric for metric in metrics)
    has_auc = any("auc" in metric for metric in metrics)
    has_head_tail = any("lift_head_5" in metric for metric in metrics)
    has_importance = any("importance" in metric for metric in metrics)
    has_quality = any(
        any(
            key in metric
            for key in (
                "coverage",
                "valid_count",
                "missing_rate",
                "mode_rate",
                "zero_rate",
                "unique_count",
                "unique_rate",
            )
        )
        for metric in metrics
    )
    has_distribution = any(
        any(
            key in metric
            for key in ("mean", "std", "median", "min", "q25", "q75", "max")
        )
        for metric in metrics
    )
    has_meaning = any(
        any(
            key in metric
            for key in (
                "business_meaning",
                "expected_direction",
                "actual_direction",
                "meaning_consistency",
                "meaning_consistency_reason",
            )
        )
        for metric in metrics
    )
    columns = ["Characteristics"]
    metric_keys: list[str] = []
    if has_iv:
        columns.append("IV")
        metric_keys.append("iv")
    if has_ks:
        columns.append("KS")
        metric_keys.append("ks")
    if has_auc:
        columns.append("AUC")
        metric_keys.append("auc")
    if has_importance:
        columns.append("Importance")
        metric_keys.append("importance")
    rows = [
        [
            str(metric.get("feature", "?")),
            *[_num(metric.get(key)) for key in metric_keys],
        ]
        for metric in metrics
    ]
    selected_labels = [
        label
        for key, label in (
            ("iv", "IV"),
            ("ks", "KS"),
            ("auc", "AUC"),
            ("coverage", "Overwrite/Quality"),
            ("psi", "PSI"),
            ("psi_month_first", "MonthPSI(First month benchmark)"),
            ("psi_month_last", "MonthPSI(End-month baseline)"),
            ("psi_month_previous", "MonthPSI(Monthly Rings)"),
            ("psi_split", "Sample CollectionPSI"),
            ("vif", "VIF"),
            ("head_tail_lift", "End of the headLift"),
            ("importance", "Importance"),
            ("meaning_consistency", "Consistency of meaning"),
        )
        if key in set(o.get("selected_metrics") or [])
    ]
    selected_text = ",".join(selected_labels) if selected_labels else "Indicators for this return"
    text = (
        f"**Characteristic analysis complete.**:{len(rows)} Characteristics,Calculated {selected_text},and generate Agent Recommendations."
        "The complete indicator can be downloaded by the button below the result of this article."
    )
    tables = []
    if rows:
        tables.append(
            {
                "title": "Feature indicators",
                "columns": columns,
                "rows": rows,
            }
        )
        tables.append(
            {
                "title": "Agent Feature Recommendations",
                "columns": [
                    "Characteristics",
                    "AgentRecommendations",
                    "Reason for recommendation",
                    "Recommended status",
                    "Evidence confidence",
                    "Support indicators",
                ],
                "rows": [
                    [
                        str(metric.get("feature", "?")),
                        str(metric.get("recommendation") or "To be assessed"),
                        str(metric.get("recommendation_reason") or "-"),
                        str(metric.get("recommendation_state") or "unevaluated"),
                        str(metric.get("recommendation_confidence") or "none"),
                        ";".join(
                            f"{item.get('metric')}={item.get('value')}"
                            for item in (metric.get("recommendation_evidence") or [])
                            if isinstance(item, dict) and item.get("metric")
                        )
                        or "-",
                    ]
                    for metric in metrics
                ],
            }
        )
        psi_views = [
            ("psi", "PSI"),
            ("psi_month_first", "MonthPSI(First month benchmark)"),
            ("psi_month_last", "MonthPSI(End-month baseline)"),
            ("psi_month_previous", "MonthPSI(Monthly Rings)"),
            ("psi_split", "Sample CollectionPSI"),
        ]
        selected_psi_views = [
            (key, label)
            for key, label in psi_views
            if any(key in metric for metric in metrics)
        ]
        if selected_psi_views:
            psi_columns = ["Characteristics"]
            for _key, label in selected_psi_views:
                psi_columns.extend([label, f"{label}Annotations"])
            tables.append(
                {
                    "title": "PSI Stability",
                    "columns": psi_columns,
                    "rows": [
                        [
                            str(metric.get("feature", "?")),
                            *[
                                value
                                for key, _label in selected_psi_views
                                for value in (
                                    _num(metric.get(key)),
                                    _feature_reason_text(
                                        metric.get(f"{key}_reason"),
                                        fallback="Completed calculations"
                                        if metric.get(key) is not None
                                        else "Reason not provided",
                                    ),
                                )
                            ],
                        ]
                        for metric in metrics
                    ],
                }
            )
            psi_detail_rows = []
            for metric in metrics:
                for key, label in selected_psi_views:
                    series = metric.get(f"{key}_series")
                    if not isinstance(series, list):
                        continue
                    for point in series:
                        if not isinstance(point, dict):
                            continue
                        psi_detail_rows.append(
                            [
                                str(metric.get("feature", "?")),
                                label,
                                str(point.get("base") or ""),
                                str(point.get("compare") or ""),
                                _num(point.get("psi")),
                            ]
                        )
            if psi_detail_rows:
                tables.append(
                    {
                        "title": "PSI Details",
                        "columns": ["Characteristics", "caliber", "Benchmark", "Comparison", "PSI"],
                        "rows": psi_detail_rows,
                    }
                )
        if has_quality:
            tables.append(
                {
                    "title": "Data quality",
                    "columns": [
                        "Characteristics",
                        "Valid sample",
                        "Coverage",
                        "Missing Rate",
                        "Single Value Rate",
                        "Zero Rate",
                    ],
                    "rows": [
                        [
                            str(metric.get("feature", "?")),
                            str(int(metric.get("valid_count") or 0)),
                            _num(metric.get("coverage")),
                            _num(metric.get("missing_rate")),
                            _num(metric.get("mode_rate")),
                            _num(metric.get("zero_rate")),
                        ]
                        for metric in metrics
                    ],
                }
            )
            tables.append(
                {
                    "title": "Single Value Check",
                    "columns": ["Characteristics", "Single value", "Unique Value"],
                    "rows": [
                        [
                            str(metric.get("feature", "?")),
                            str(int(metric.get("unique_count") or 0)),
                            _num(metric.get("unique_rate")),
                        ]
                        for metric in metrics
                    ],
                }
            )
        if has_head_tail:
            tables.append(
                {
                    "title": "End of the head Lift(Risk orientation)",
                    "columns": [
                        "Characteristics",
                        "Headlift5%",
                        "Headlift10%",
                        "Endlift5%",
                        "Endlift10%",
                    ],
                    "rows": [
                        [
                            str(metric.get("feature", "?")),
                            _num(metric.get("lift_head_5")),
                            _num(metric.get("lift_head_10")),
                            _num(metric.get("lift_tail_5")),
                            _num(metric.get("lift_tail_10")),
                        ]
                        for metric in metrics
                    ],
                }
            )
            tables.append(
                {
                    "title": "Lift Accounting instructions",
                    "columns": ["Characteristics", "Annotations"],
                    "rows": [
                        [
                            str(metric.get("feature", "?")),
                            str(metric.get("lift_reason") or "Completed calculations"),
                        ]
                        for metric in metrics
                    ],
                }
            )
        if has_distribution:
            tables.append(
                {
                    "title": "Distribution statistics(Centre)",
                    "columns": ["Characteristics", "Mean", "Standard deviation", "Medium"],
                    "rows": [
                        [
                            str(metric.get("feature", "?")),
                            _num(metric.get("mean")),
                            _num(metric.get("std")),
                            _num(metric.get("median")),
                        ]
                        for metric in metrics
                    ],
                }
            )
            tables.append(
                {
                    "title": "Distribution statistics(Scope)",
                    "columns": ["Characteristics", "Min", "P25", "P75", "Maximum"],
                    "rows": [
                        [
                            str(metric.get("feature", "?")),
                            _num(metric.get("min")),
                            _num(metric.get("q25")),
                            _num(metric.get("q75")),
                            _num(metric.get("max")),
                        ]
                        for metric in metrics
                    ],
                }
            )
        if has_meaning:
            tables.append(
                {
                    "title": "Consistency of meaning",
                    "columns": [
                        "Characteristics",
                        "Business implications",
                        "Expected orientation",
                        "Actual orientation",
                        "Conclusions",
                        "Annotations",
                    ],
                    "rows": [
                        [
                            str(metric.get("feature", "?")),
                            str(metric.get("business_meaning") or "-"),
                            str(metric.get("expected_direction") or "-"),
                            str(metric.get("actual_direction") or "-"),
                            str(metric.get("meaning_consistency") or "n/a"),
                            _feature_reason_text(
                                metric.get("meaning_consistency_reason"),
                                fallback="Check completed"
                                if metric.get("meaning_consistency")
                                else "Reason not provided",
                            ),
                        ]
                        for metric in metrics
                    ],
                }
            )
    # Optional collinear / VIF section (computed only when the metric was selected).
    collinear = o.get("collinear")
    if isinstance(collinear, dict):
        vif = collinear.get("vif") or {}
        if vif:
            tables.append(
                {
                    "title": "VIF(Colinear)",
                    "columns": ["Characteristics", "VIF"],
                    "rows": [[str(feat), _num(value)] for feat, value in vif.items()],
                }
            )
        pairs = [
            p
            for p in (collinear.get("collinear_pairs") or [])
            if isinstance(p, (list, tuple)) and len(p) >= 3
        ]
        if pairs:
            tables.append(
                {
                    "title": "High-relevant characteristics pair",
                    "columns": ["CharacteristicsA", "CharacteristicsB", "Related coefficient"],
                    "rows": [[str(p[0]), str(p[1]), _num(p[2])] for p in pairs],
                }
            )
    return text, tables


def _feature_reason_text(value, *, fallback: str) -> str:
    if isinstance(value, dict):
        return str(value.get("message") or value.get("code") or fallback)
    if value not in (None, ""):
        return str(value)
    return fallback


def _render_feature_report(o: dict):
    # Reuse the metrics wide table (the tool echoes metrics) and append the report link.
    text, tables = _render_feature_metrics(o)
    bin_text, bin_tables = _render_feature_bins(o)
    if bin_text:
        text += f"\n\n{bin_text}"
    tables.extend(bin_tables)
    path = o.get("report_path") or ""
    if path:
        text += f"\n\n**Characteristic analysis reports generated**:`{path}`.Please use the results below this Article(Download feature analysis)button."
    return text, tables


def _render_feature_bins(o: dict):
    analyses = [item for item in (o.get("binning") or []) if isinstance(item, dict)]
    if not analyses:
        return "Skipped Selected Box Analysis.", []
    rows = []
    for analysis in analyses:
        feature = str(analysis.get("feature") or "")
        requested = int(analysis.get("requested_bins") or 0)
        actual = int(analysis.get("actual_bins") or 0)
        for item in analysis.get("rows") or []:
            if not isinstance(item, dict):
                continue
            rows.append(
                [
                    feature,
                    requested,
                    int(item.get("bin_index") or 0),
                    int(item.get("risk_rank") or 0),
                    str(item.get("interval") or ""),
                    int(item.get("count") or 0),
                    int(item.get("bad_count") or 0),
                    int(item.get("good_count") or 0),
                    _num(item.get("bad_rate")),
                    _num(item.get("cumulative_bad_rate")),
                    _num(item.get("lift")),
                    _num(item.get("cumulative_lift")),
                    _num(item.get("ks")),
                    _num(item.get("woe")),
                    _num(item.get("iv_contribution")),
                    actual,
                    str(analysis.get("direction") or "unknown"),
                    str(analysis.get("degraded_reason") or ""),
                ]
            )
    table = {
        "title": "Box analysis",
        "columns": [
            "Characteristics",
            "Number of boxes requested",
            "Box number",
            "Risk sorting",
            "Intersection",
            "Number of samples",
            "Number of bad samples",
            "Good sample numbers",
            "Bad rate",
            "Cumulative bad rate",
            "SingleLift",
            "CumulativeLift",
            "KS",
            "WOE",
            "IVContribution",
            "Actual boxes",
            "Risk orientation",
            "Box description",
        ],
        "rows": rows,
    }
    return f"**The case analysis is complete.**:Analysed {len(analyses)} Characteristics selected by individual users.", [table]


def _render_vintage_curve(o: dict):
    cohorts = [str(item) for item in (o.get("cohorts") or [])]
    mob_axis = list(o.get("mob_axis") or [])
    summary = o.get("summary") if isinstance(o.get("summary"), dict) else {}
    trend = str(summary.get("trend") or "stable")
    text = f"**Vintage Curve complete**:{len(cohorts)} individual cohort,Trends `{trend}`."
    tables = []
    curves = o.get("curves") if isinstance(o.get("curves"), dict) else {}
    counts = o.get("counts") if isinstance(o.get("counts"), dict) else {}
    if cohorts and mob_axis:
        tables.append(
            {
                "title": "Vintage Cumulative bad debt rate",
                "columns": ["cohort", "Number of samples", *[f"MOB{mob}" for mob in mob_axis]],
                "rows": [
                    [
                        cohort,
                        _fmt(counts.get(cohort, "")),
                        *[
                            _pct(value) if value is not None else "n/a"
                            for value in (curves.get(cohort) or [])[: len(mob_axis)]
                        ],
                    ]
                    for cohort in cohorts
                ],
            }
        )
    at_ref = summary.get("at_ref") if isinstance(summary.get("at_ref"), dict) else {}
    if at_ref:
        tables.append(
            {
                "title": "References MOB Bad debt rate",
                "columns": ["cohort", "Bad debt rate"],
                "rows": [
                    [str(cohort), _pct(value)] for cohort, value in at_ref.items()
                ],
            }
        )
    # A1: surface the vintage kernel's data-quality warnings (e.g. the snapshot-flag
    # red flag when data looks cumulative but was declared incremental) as red flags,
    # mirroring _render_slice_aggregate. De-duplicated: the kernel attaches the same
    # flag to every point, so warnings arrives with one entry per point.
    seen: set[str] = set()
    flag_lines = []
    for warning in o.get("warnings") or []:
        text_warning = str(warning)
        if text_warning and text_warning not in seen:
            seen.add(text_warning)
            flag_lines.append(f"🚩 {text_warning}")
    if flag_lines:
        text += "\n" + "\n".join(flag_lines)
    return text, tables


# S6 ad-hoc slice/aggregate result. INV-1: every number here comes from the
# slice_aggregate tool (a single deterministic DuckDB SQL); this renderer only
# lays the tool's own rows/columns into a table and echoes the confirmed caliber
# (spec_echo) + any red flags, never (re)computing anything.
_SLICE_OP_LABEL = {
    "count": "Number",
    "sum": "Peace.",
    "mean": "Mean",
    "min": "Min",
    "max": "Maximum",
    "bad_rate": "Bad rate",
    "approval_rate": "Pass rate",
    "distinct": "Go to the count again.",
}


def _slice_metric_text(metric: dict) -> str:
    op = str(metric.get("op") or "")
    label = _SLICE_OP_LABEL.get(op, op)
    col = metric.get("col")
    return f"{col} Its...{label}" if col else label


def _render_slice_aggregate(o: dict):
    columns = [str(c) for c in (o.get("columns") or [])]
    rows = [row for row in (o.get("rows") or []) if isinstance(row, dict)]
    spec = o.get("spec_echo") if isinstance(o.get("spec_echo"), dict) else {}
    group_by = [str(c) for c in (spec.get("group_by") or [])]
    metrics = [m for m in (spec.get("metrics") or []) if isinstance(m, dict)]
    group_text = ",".join(group_by) if group_by else "All samples"
    metric_text = ",".join(_slice_metric_text(m) for m in metrics) or "—"
    echo_parts = [f"caliber:Press〔{group_text}〕Statistics〔{metric_text}〕"]
    if spec.get("month_col") and spec.get("months"):
        echo_parts.append(
            f",Time〔{','.join(str(m) for m in spec.get('months') or [])}〕"
        )
    filters = [f for f in (spec.get("filters") or []) if isinstance(f, dict)]
    if filters:
        filter_text = ",".join(
            f"{f.get('col')}{f.get('op')}{f.get('value')}" for f in filters
        )
        echo_parts.append(f",Filter〔{filter_text}〕")
    text = (
        "**Results of summary questioning**(" + str(len(rows)) + " Okay.).\n" + "".join(echo_parts) + "."
    )
    # A4: bad_rate/approval_rate may now be NULL for an all-unlabeled group — render it as
    # "n/a" rather than the literal "None" so the honest "no labeled samples" answer reads
    # cleanly. The companion unlabeled_count_<col> columns flow through automatically.
    tables = [
        {
            "title": "Aggregation result",
            "columns": columns,
            "rows": [
                [
                    "n/a" if row.get(col) is None else _fmt(row.get(col))
                    for col in columns
                ]
                for row in rows
            ],
        }
    ]
    red_flags = [f for f in (o.get("red_flags") or []) if isinstance(f, dict)]
    if red_flags:
        text += "\n" + "\n".join(f"🚩 {str(f.get('message') or '')}" for f in red_flags)
    return text, tables


_PROFILE_SECTION_LABELS = {
    "overview": "Overview",
    "target": "Target Distribution",
    "missing": "Missing",
    "distribution": "Distribution",
    "correlation": "Related Matrix",
}

_PROFILE_CORRELATION_REASON_LABELS = {
    "insufficient_pairs": "Insufficient number of valid samples",
    "zero_variance_left": "Left Constant",
    "zero_variance_right": "Right Constant",
    "zero_variance_both": "Double Constant",
    "nonfinite_result": "Results are not limited",
    "unsafe_numeric_precision": "Numerical precision is not safe",
    "unsafe_numeric_precision_left": "Left value accuracy is not safe",
    "unsafe_numeric_precision_right": "Right value accuracy is not safe",
    "unsafe_numeric_precision_both": "The double-sided accuracy is not safe.",
}


def _profile_tagged_value(value) -> str:
    if not isinstance(value, dict):
        return "n/a" if value is None else str(value)
    if value.get("type") == "null":
        return "NULL"
    nonfinite = value.get("nonfinite")
    if nonfinite:
        return {
            "negative_infinity": "-Infinity",
            "positive_infinity": "+Infinity",
            "nan": "NaN",
        }.get(str(nonfinite), str(nonfinite))
    raw = value.get("value")
    return "n/a" if raw is None else str(raw)


def _profile_semantics(o: dict) -> tuple[dict, dict]:
    semantics = o.get("semantics") if isinstance(o.get("semantics"), dict) else {}
    roles = (
        semantics.get("field_roles")
        if isinstance(semantics.get("field_roles"), dict)
        else {}
    )
    names = (
        semantics.get("business_names")
        if isinstance(semantics.get("business_names"), dict)
        else {}
    )
    return roles, names


def _profile_field_label(name, business_names: dict) -> str:
    raw = str(name or "")
    business = str(business_names.get(raw) or "").strip()
    return f"{raw}({business})" if business else raw


def _profile_frequency_text(frequency: dict) -> str:
    items = frequency.get("items") if isinstance(frequency.get("items"), list) else []
    parts = []
    for item in items[:8]:
        if not isinstance(item, dict):
            continue
        parts.append(
            f"{_profile_tagged_value(item.get('value'))}:"
            f"{_fmt(item.get('count'))}({_pct(item.get('rate_all'))})"
        )
    other_count = frequency.get("other_count")
    if isinstance(other_count, int) and other_count > 0:
        parts.append(f"Other:{other_count}")
    return ";".join(parts) if parts else "n/a"


def _profile_correlation_cell(value, reason, pair_count) -> str:
    if reason == "ok" and value is not None:
        return _fmt(value)
    label = _PROFILE_CORRELATION_REASON_LABELS.get(str(reason), str(reason or "Not Available"))
    return f"n/a({label},n={_fmt(pair_count)})"


def _render_profile_dataset(o: dict):
    """Lay out deterministic profile evidence without calculating new metrics."""

    result = o.get("result") if isinstance(o.get("result"), dict) else {}
    dataset = result.get("dataset") if isinstance(result.get("dataset"), dict) else {}
    fields = [
        field for field in (result.get("fields") or []) if isinstance(field, dict)
    ]
    options = o.get("options_echo") if isinstance(o.get("options_echo"), dict) else {}
    sections = [
        str(item) for item in (options.get("sections") or _PROFILE_SECTION_LABELS)
    ]
    requested = set(sections)
    roles, business_names = _profile_semantics(o)
    row_count = o.get("row_count_scanned", dataset.get("row_count", 0))
    text = (
        f"**Sample description is complete.**:Dataset `{str(o.get('dataset_id') or '')}`,"
        f"Full scan. {_fmt(row_count)} Okay.;The result is bound. dataset hash,Analyse generational and semantic versions."
    )
    if requested != set(_PROFILE_SECTION_LABELS):
        labels = ",".join(
            _PROFILE_SECTION_LABELS.get(section, section) for section in sections
        )
        text += f" Show as requested:{labels}."

    tables = []
    if "overview" in requested:
        tables.append(
            {
                "title": "Field Overview",
                "columns": [
                    "Fields",
                    "Role",
                    "Type",
                    "Total lines",
                    "Missing",
                    "Missing Rate",
                    "Single value",
                ],
                "rows": [
                    [
                        _profile_field_label(field.get("name"), business_names),
                        str(roles.get(str(field.get("name") or "")) or "—"),
                        str(field.get("duckdb_type") or field.get("kind") or "—"),
                        _fmt(field.get("row_count")),
                        _fmt(field.get("null_count")),
                        _pct(field.get("null_rate")),
                        _fmt(field.get("distinct_count")),
                    ]
                    for field in fields
                ],
            }
        )

    if "missing" in requested:
        tables.append(
            {
                "title": "Missing analysis",
                "columns": ["Fields", "Missing", "Missing Rate", "Total lines"],
                "rows": [
                    [
                        _profile_field_label(field.get("name"), business_names),
                        _fmt(field.get("null_count")),
                        _pct(field.get("null_rate")),
                        _fmt(field.get("row_count")),
                    ]
                    for field in sorted(
                        fields,
                        key=lambda item: (
                            -int(item.get("null_count") or 0),
                            str(item.get("name") or ""),
                        ),
                    )
                ],
            }
        )

    target = result.get("target_distribution")
    if "target" in requested and isinstance(target, dict):
        frequency = (
            target.get("frequency") if isinstance(target.get("frequency"), dict) else {}
        )
        items = [
            item for item in (frequency.get("items") or []) if isinstance(item, dict)
        ]
        tables.append(
            {
                "title": "Target Distribution",
                "columns": ["Value", "Number of samples", "Percentage"],
                "rows": [
                    [
                        _profile_tagged_value(item.get("value")),
                        _fmt(item.get("count")),
                        _pct(item.get("rate_all")),
                    ]
                    for item in items
                ],
            }
        )

    if "distribution" in requested:
        tables.append(
            {
                "title": "Field Distribution",
                "columns": [
                    "Fields",
                    "Type",
                    "Min",
                    "P25",
                    "P50",
                    "P75",
                    "Max",
                    "Summary of frequency",
                ],
                "rows": [
                    [
                        _profile_field_label(field.get("name"), business_names),
                        str(field.get("kind") or field.get("duckdb_type") or "—"),
                        _fmt((field.get("numeric") or {}).get("min"))
                        if isinstance(field.get("numeric"), dict)
                        else "n/a",
                        _fmt((field.get("numeric") or {}).get("p25"))
                        if isinstance(field.get("numeric"), dict)
                        else "n/a",
                        _fmt((field.get("numeric") or {}).get("p50"))
                        if isinstance(field.get("numeric"), dict)
                        else "n/a",
                        _fmt((field.get("numeric") or {}).get("p75"))
                        if isinstance(field.get("numeric"), dict)
                        else "n/a",
                        _fmt((field.get("numeric") or {}).get("max"))
                        if isinstance(field.get("numeric"), dict)
                        else "n/a",
                        _profile_frequency_text(field.get("frequency") or {})
                        if isinstance(field.get("frequency"), dict)
                        else "n/a",
                    ]
                    for field in fields
                ],
            }
        )

    correlations = result.get("correlations")
    if "correlation" in requested and isinstance(correlations, dict):
        columns = [str(item) for item in (correlations.get("columns") or [])]
        values = correlations.get("values") or []
        counts = correlations.get("pair_counts") or []
        reasons = correlations.get("reasons") or []
        rows = []
        for row_index, column in enumerate(columns):
            row = [_profile_field_label(column, business_names)]
            for column_index in range(len(columns)):
                value = values[row_index][column_index]
                reason = reasons[row_index][column_index]
                count = counts[row_index][column_index]
                row.append(_profile_correlation_cell(value, reason, count))
            rows.append(row)
        tables.append(
            {
                "title": "Related Matrix",
                "columns": [
                    "Fields",
                    *[_profile_field_label(name, business_names) for name in columns],
                ],
                "rows": rows,
            }
        )
    return text, tables


_TRANSFORM_OPERATION_LABELS = {
    "rename_columns": "A life-threatening section.",
    "drop_columns": "Delete Fields",
    "cast_columns": "Convert Field Type",
    "fill_missing": "Fill Missing",
    "filter_rows": "Filter Samples",
    "derive_columns": "Generate Fields",
    "deduplicate": "Go heavy.",
}


def _transform_field_list(value) -> str:
    if not isinstance(value, (list, tuple)):
        return "n/a"
    fields = [str(item) for item in value]
    return ",".join(fields) if fields else "None"


def _transform_mapping_text(value) -> str:
    if not isinstance(value, dict) or not value:
        return "None"
    return ";".join(f"{source} → {target}" for source, target in value.items())


def _transform_impact_text(op: str, impact) -> str:
    """Render the kernel's impact evidence without deriving replacement metrics."""

    if not isinstance(impact, dict):
        return "n/a"
    if op == "rename_columns":
        return (
            f"Rename {_fmt(impact.get('renamed_count'))} individual:"
            f"{_transform_mapping_text(impact.get('mapping'))}"
        )
    if op == "drop_columns":
        return (
            f"Delete {_fmt(impact.get('dropped_count'))} individual:"
            f"{_transform_field_list(impact.get('columns'))}"
        )
    if op == "cast_columns":
        return (
            f"Convert Fields:{_transform_field_list(impact.get('columns'))};"
            f"Enter non-empty {_fmt(impact.get('non_null_input_count'))};"
            f"Invalid emptiness {_fmt(impact.get('invalid_to_null_count'))}"
        )
    if op == "fill_missing":
        return (
            f"Fill {_fmt(impact.get('filled_count'))} Missing value:"
            f"{_transform_field_list(impact.get('columns'))}"
        )
    if op == "filter_rows":
        return (
            f"Reservations {_fmt(impact.get('kept_rows'))} Okay.;"
            f"Remove {_fmt(impact.get('removed_rows'))} Okay."
        )
    if op == "derive_columns":
        return (
            f"Generate {_fmt(impact.get('derived_count'))} Fields:"
            f"{_transform_field_list(impact.get('columns'))}"
        )
    if op == "deduplicate":
        return (
            f"Press {_transform_field_list(impact.get('keys'))} Go heavy.;"
            f"Reservations {_fmt(impact.get('kept_rows'))} Okay.;"
            f"Remove {_fmt(impact.get('removed_rows'))} Okay."
        )
    scalar_items = [
        f"{key}={_fmt(value)}"
        for key, value in impact.items()
        if isinstance(value, (str, int, float, bool)) or value is None
    ]
    return ";".join(scalar_items) if scalar_items else "n/a"


def _render_transform_dataset(o: dict):
    """Present only persisted transform, semantic, workspace and lineage evidence."""

    source_id = str(o.get("source_dataset_id") or "")
    result_id = str(o.get("result_dataset_id") or "")
    text = (
        f"**Data processing complete**:`{source_id}`({_fmt(o.get('row_count_before'))} Okay. / "
        f"{_fmt(o.get('column_count_before'))} Columns)→ `{result_id}`"
        f"({_fmt(o.get('row_count_after'))} Okay. / "
        f"{_fmt(o.get('column_count_after'))} Columns)."
    )
    if o.get("cached") is True:
        text += " This time, re-use verified evidence."

    steps = [item for item in (o.get("steps") or []) if isinstance(item, dict)]
    semantic = (
        o.get("semantic_migration")
        if isinstance(o.get("semantic_migration"), dict)
        else {}
    )
    protected = [str(item) for item in (semantic.get("dropped_protected_fields") or [])]
    if protected:
        text += f" Delete protected fields as expressly confirmed:{','.join(protected)}."

    tables = []
    if steps:
        tables.append(
            {
                "title": "Process step impact",
                "columns": [
                    "Steps",
                    "Operation",
                    "Number of front lines processed",
                    "Lines after processing",
                    "Line change",
                    "Impact evidence",
                ],
                "rows": [
                    [
                        _fmt(step.get("step")),
                        _TRANSFORM_OPERATION_LABELS.get(
                            str(step.get("op") or ""),
                            str(step.get("op") or "Unknown operation"),
                        ),
                        _fmt(step.get("row_count_before")),
                        _fmt(step.get("row_count_after")),
                        _fmt(step.get("row_delta")),
                        _transform_impact_text(
                            str(step.get("op") or ""), step.get("impact")
                        ),
                    ]
                    for step in steps
                ],
            }
        )

    renamed_fields = semantic.get("renamed_fields")
    dropped_fields = [str(item) for item in (semantic.get("dropped_fields") or [])]
    semantic_rows = [
        [
            "Semantic Map SHA-256",
            f"{semantic.get('before_hash') or 'n/a'} → {semantic.get('after_hash') or 'n/a'}",
        ],
        ["A life-threatening section.", _transform_mapping_text(renamed_fields)],
        ["Delete Fields", ",".join(dropped_fields) if dropped_fields else "None"],
    ]
    if protected:
        semantic_rows.append(["Confirmed Delete Protected Fields", ",".join(protected)])
    tables.append(
        {
            "title": "Field Semantic Migration",
            "columns": ["Item", "Tool evidence"],
            "rows": semantic_rows,
        }
    )

    workspace = o.get("workspace") if isinstance(o.get("workspace"), dict) else {}
    tables.append(
        {
            "title": "Workspace Version Migration",
            "columns": ["Item", "Before processing", "After processing"],
            "rows": [
                [
                    "Revision",
                    _fmt(workspace.get("source_revision")),
                    _fmt(workspace.get("result_revision")),
                ],
                [
                    "Analysis of generation",
                    _fmt(workspace.get("source_analysis_generation")),
                    _fmt(workspace.get("result_analysis_generation")),
                ],
            ],
        }
    )

    lineage = o.get("lineage") if isinstance(o.get("lineage"), dict) else {}
    tables.append(
        {
            "title": "Data blood",
            "columns": ["Parent Data Set", "Subset", "Relations", "Side Serial Number"],
            "rows": [
                [
                    str(lineage.get("parent_dataset_id") or ""),
                    str(lineage.get("child_dataset_id") or ""),
                    str(lineage.get("relation_kind") or ""),
                    _fmt(lineage.get("edge_order")),
                ]
            ],
        }
    )

    tables.append(
        {
            "title": "Evidence and downloads",
            "columns": ["Item", "Value"],
            "rows": [
                ["Run ID", str(o.get("run_id") or "")],
                ["Result SHA-256", str(o.get("result_content_hash") or "")],
                ["Proof of evidence.", str(o.get("evidence_artifact_id") or "")],
                ["Download Address", str(o.get("evidence_download_url") or "")],
            ],
        }
    )
    return text, tables


_EXPORT_SAFETY_LABELS = (
    ("formula_cells_escaped", "Formula Injection Conversion"),
    ("text_column_cells_written", "Text field cells"),
    ("csv_text_cells_coerced", "CSV Text protection"),
    ("large_integer_cells_as_text", "Integers of excess by text"),
    ("decimal_cells_as_text", "Decimal by Text"),
    ("high_precision_decimal_cells_as_text", "High precision decimal by text"),
    ("non_finite_cells_as_text", "Non-limited values by text"),
    ("xlsx_control_characters_escaped", "Excel Control character conversion"),
)


def _export_integer(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError, OverflowError):
        return "n/a"


def _export_size(value) -> str:
    try:
        size = int(value)
    except (TypeError, ValueError, OverflowError):
        return "n/a"
    if size < 0:
        return "n/a"
    if size < 1024:
        return f"{size} B"
    if size < 1024**2:
        return f"{size / 1024:.2f} KB"
    if size < 1024**3:
        return f"{size / 1024**2:.2f} MB"
    return f"{size / 1024**3:.2f} GB"


def _render_export_dataset(o: dict):
    """Render only the persisted export artifact and safety evidence."""

    export_format = str(o.get("format") or "").casefold()
    if export_format == "csv":
        format_label = "CSV"
    elif export_format == "xlsx":
        format_label = "Excel"
    else:
        format_label = export_format.upper() or "Unknown format"
    text = (
        f"**Data Export Complete**:{format_label},"
        f"{_export_integer(o.get('row_count'))} Okay. / "
        f"{_export_integer(o.get('column_count'))} Columns,"
        f"File Size {_export_size(o.get('size_bytes'))}."
    )
    if o.get("cached") is True:
        text += " This reusable validated product."

    options = o.get("options") if isinstance(o.get("options"), dict) else {}
    text_columns = [str(item) for item in (options.get("text_columns") or [])]
    safety = o.get("safety") if isinstance(o.get("safety"), dict) else {}
    return text, [
        {
            "title": "Export File",
            "columns": ["Item", "Value"],
            "rows": [
                ["Format", format_label],
                ["Dataset", str(o.get("dataset_id") or "")],
                ["Dataset SHA-256", str(o.get("dataset_content_hash") or "")],
                ["Workspace Revision", _num(o.get("workspace_revision"))],
                ["Analysis of generation", _num(o.get("analysis_generation"))],
                ["File Size", _export_size(o.get("size_bytes"))],
                ["Documentation SHA-256", str(o.get("content_hash") or "")],
                ["Exported Fields by Text", ",".join(text_columns) if text_columns else "None"],
                ["Products", str(o.get("artifact_id") or "")],
                ["Download Address", str(o.get("download_url") or "")],
            ],
        },
        {
            "title": "Security handling",
            "columns": ["Protection projects", "Processing Cells"],
            "rows": [
                [label, _export_integer(safety.get(key))]
                for key, label in _EXPORT_SAFETY_LABELS
            ],
        },
    ]


def _render_propose_join(o: dict):
    joins = o.get("joins") or []
    # GAP-4: business-meaning lookup for raw key-column codes (e.g. als_m3_id_nbank_orgnum),
    # present only when the task has a registered data dictionary; {} otherwise, in which
    # case _key_label below degrades to the plain column name (no visible change).
    dictionary = o.get("dictionary") if isinstance(o.get("dictionary"), dict) else {}
    rows = []
    has_key_alternatives = False
    any_conflict = False
    any_fp_mismatch = False
    any_dtype_mismatch = False
    for j in joins:
        diag = j.get("diagnostics") or {}
        match_rate = diag.get("match_rate")
        unique = diag.get("feature_key_unique")
        fan_out = diag.get("fan_out_detected", diag.get("fan_out"))
        # Prefer the friendly file name (features.parquet) over the raw ds_<hash> id.
        fname = str(j.get("feature_name") or j.get("feature_id", "?"))
        key_pairs = j.get("key_pairs") or []
        keys = (
            ", ".join(
                f"{_key_label(p.get('anchor_col'), dictionary)}={_key_label(p.get('feature_col'), dictionary)}"
                for p in key_pairs
            )
            or "?"
        )
        # Dynamic key relaxation proposals (spec §4/§5): low-match keys may match better with
        # one element dropped — surface as suggestions (the user confirms; never auto-applied).
        for alt in diag.get("key_alternatives") or []:
            if not isinstance(alt, dict):
                continue
            has_key_alternatives = True
        # Fingerprint consistency (spec §5 C2 "Fingerprints raw=md5? ✓/✗"): transform_side == "both"
        # means anchor and feature key share format (both raw or both md5); anything else
        # means one side is raw and the other md5 (Key Format Unaligned), joinable only via a hash
        # transform — surfaced so the user can sanity-check the key beforeImplementation.
        fp_consistent = (
            all((p.get("transform_side") or "both") == "both" for p in key_pairs)
            if key_pairs
            else True
        )
        if not fp_consistent:
            any_fp_mismatch = True
        fp_cell = "✓" if fp_consistent else "✗ raw≠md5"
        # T1-B8: key-dtype divergence (one side text, one side float/int) risks a silent miss
        # via precision / leading-zero loss. A "red" (text↔float) divergence forces confirm.
        divergences = [
            d for d in (diag.get("key_dtype_divergences") or []) if isinstance(d, dict)
        ]
        red_divergence = any(d.get("level") == "red" for d in divergences)
        if red_divergence:
            any_dtype_mismatch = True
            dtype_cell = "✗ text≠float"
        elif divergences:
            dtype_cell = "⚠️Type inconsistent"
        else:
            dtype_cell = "✓"
        # Two-level dedup breakdown (spec §6): safe whole-row dups vs same-key conflicts.
        report = diag.get("conflict_report") or {}
        conflict_keys = int(report.get("n_conflict_keys") or 0)
        safe_dropped = int(report.get("safe_dropped") or 0)
        if conflict_keys:
            any_conflict = True
        dedup_cell = "-" if unique else f"Clear.{safe_dropped}/⚠️Conflict{conflict_keys}"
        rows.append(
            [
                fname,
                keys,
                fp_cell,
                dtype_cell,
                _fmt(match_rate) if match_rate is not None else "n/a",
                "Yes." if unique else "Yes",
                "⚠️Yes." if fan_out else "Yes",
                dedup_cell,
            ]
        )
    text = (
        f"**Collapse diagnostic complete.**:{len(joins)} A feature sheet to be left to connect to anchor sample(Number of anchor lines **1:1 Reservations**).\n"
        "Check the hit rate for each of the tables./Key Moniency/Whether to expand.Keys are not the only features to select from the re-policy;Its not until we know its a clutter.."
    )
    if any_conflict:
        text += (
            "\n\n⚠️ Detected**Conflict of same key**(Multiple rows with the same key but not consistent feature values):This kind.**Its not automatically deleted.**,"
            "Please confirm the strategy or data cleansing before we spell it.."
        )
    if any_fp_mismatch:
        text += (
            "\n\n⚠️ Detected**The key prints dont match.**(`✗ raw≠md5`:anchor/Feature side one is the original,- Yes. md5):"
            "The system will automatically connect to Zihashi.,But please confirm that this is the same sign.(Avoid misalignment)."
        )
    if any_dtype_mismatch:
        text += (
            "\n\n⚠️ Detected**Key type inconsistent**(side text,Floating side/Integer):There may have been a loss of precision./Lead zero lost"
            "It causes a silent leak.,Make sure its the same mark before you spell it.(We need confirmation before we can execute it.)."
        )
    if has_key_alternatives:
        text += (
            "\n\n💡 Multiple candidates for the spell key were detected.Press Down**Each feature sheet**Show Select Keys Separate;"
            "The system will be recalculated at the current step after selection.,Unique and expanding.,No direct encircling.."
        )
    # T3-1: dual-path reconciliation red flags. Each feature's match count is computed two
    # independent ways (DuckDB SQL vs pandas); any divergence beyond tolerance is a BLOCKING
    # red flag showing BOTH path values, so the human sees the disagreement rather than
    # rubber-stamping one number. Silent (no line) when the two paths agree.
    reconcile_summary = (
        o.get("reconcile_summary")
        if isinstance(o.get("reconcile_summary"), dict)
        else {}
    )
    for flag in reconcile_summary.get("red_flags") or []:
        if isinstance(flag, dict) and flag.get("message"):
            text += f"\n\n🚩 {str(flag.get('message'))}"
    tables = []
    if rows:
        tables.append(
            {
                "title": "Collapse diagnostics(Feature by Feature Table)",
                "columns": [
                    "Feature Table",
                    "Match key",
                    "Fingerprints(raw=md5?)",
                    "Key Type",
                    "Hit rate",
                    "Only key",
                    "Quiz",
                    "Go heavy.(Clear./Conflict keys)",
                ],
                "rows": rows,
            }
        )
    # T3: expandable "Digital trace" detail — the two-path match count + the provenance tuple
    # (dataset fingerprint / code version / params digest / seed) behind each feature's
    # headline number, so the displayed number is auditable back to its inputs.
    trust_rows = _join_trust_rows(joins)
    if trust_rows:
        tables.append(
            {
                "title": "Digital trace(Reconciliation + Blood.)",
                "columns": [
                    "Feature Table",
                    "Match Lines(Authority Road)",
                    "Match Lines(Independence Road)",
                    "Reconciliation",
                    "Data fingerprint",
                    "Code Version",
                    "Summary of parameters",
                    "seed",
                ],
                "rows": trust_rows,
            }
        )
    return text, tables


def _join_trust_rows(joins) -> list[list[str]]:
    """T3: one row per feature summarizing its match-count reconciliation + provenance
    tuple. Shows both computation paths' values, the reconcile verdict, and the minimal
    lineage (fingerprints truncated for readability). Empty when the trust layer is
    absent (e.g. an older stored plan) so this degrades to no extra table."""
    rows = []
    for j in joins:
        if not isinstance(j, dict):
            continue
        rec = j.get("reconcile") if isinstance(j.get("reconcile"), dict) else None
        prov = j.get("provenance") if isinstance(j.get("provenance"), dict) else None
        if not rec and not prov:
            continue
        fname = str(j.get("feature_name") or j.get("feature_id", "?"))
        primary = rec.get("primary") if rec else None
        secondary = rec.get("secondary") if rec else None
        # T3-2: an honest verdict. A number with no independent second path is "No independent review",
        # NOT the ✓ Unanimously (agree) badge -- a same-path self-comparison must never look verified.
        if rec and rec.get("trust") == "not_independently_verified":
            verdict = "⚠ No independent review"
        elif rec and rec.get("consistent"):
            verdict = "✓ Unanimously"
        elif rec:
            verdict = "🚩 Difference"
        else:
            verdict = "—"
        rows.append(
            [
                fname,
                _integer_text(primary) if primary is not None else "n/a",
                _integer_text(secondary) if secondary is not None else "n/a",
                verdict,
                _short_digest(prov.get("dataset_fingerprint")) if prov else "—",
                str(prov.get("code_version") or "—") if prov else "—",
                _short_digest(prov.get("params_digest")) if prov else "—",
                str(prov.get("seed")) if prov and prov.get("seed") is not None else "—",
            ]
        )
    return rows


def _integer_text(value) -> str:
    """Counts are discrete even when a computation backend returns float scalars."""
    try:
        return str(int(float(value)))
    except (TypeError, ValueError, OverflowError):
        return str(value)


def _short_digest(value) -> str:
    """Truncate a ``sha256:<hex>`` digest to a readable prefix for gate display."""
    text = str(value or "")
    if text.startswith("sha256:"):
        body = text[len("sha256:") :]
        return f"sha256:{body[:12]}…" if len(body) > 12 else text
    return text[:16] + "…" if len(text) > 16 else text


def _render_confirm_join(o: dict):
    # Internal plumbing step (marks engine specs confirmed). It is a dependency of
    # the execute_join gate, but its summary would show "Confirmed…" before the human
    # actually confirms, which is confusing — so render nothing at the gate…
    # T1-B8: a red key-dtype mismatch blocks confirmation until the user acknowledges it.
    needs_dtype = o.get("needs_dtype_ack") or []
    if needs_dtype:
        labels = o.get("needs_dtype_ack_labels") or {}
        listed = ",".join(f"`{labels.get(f, f)}`" for f in needs_dtype)
        return (
            f"⚠️ Characteristics {listed} Its...**The type of cipher is not consistent**(side text,Floating side:Could have lost precision/Lead Zero,"
            "It causes a silent leak.).Please confirm that this is the same sign.[Type of confirmation key]Go on.;or retry after importing the column with a string."
        ), []
    needs = o.get("needs_dedup") or []
    if needs:
        # …UNLESS a feature has a same-key conflict (spec §6): surface it so the user knows
        # the join can't execute until they pick a dedup strategy (or exclude the feature).
        labels = o.get("needs_dedup_labels") or {}
        listed = ",".join(f"`{labels.get(f, f)}`" for f in needs)
        return (
            f"⚠️ Characteristics {listed} Existence**Conflict with the same key**(Lines with Same Key,Unanimously characterised values),"
            "We need to reset our strategy to get it together..Reply[Go heavy. first](Retain the first article)or[Go heavy. last](Retain the last clause)Resolve;"
            "Or try again after you have excluded these features.."
        ), []
    return "", []


def _render_execute_join(o: dict):
    anchor_rows = o.get("anchor_rows")
    joined_rows = o.get("joined_rows")
    ok = anchor_rows == joined_rows
    text = (
        f"**Collapse execution complete.**:Outcome dataset `{o.get('result_dataset_id', '')}`,"
        f"anchor {anchor_rows} → After the spell {joined_rows} Okay."
        + ("(1:1 Hold on. ✓)" if ok else "(⚠️ Change in number of lines,Check the swelling.)")
    )
    warnings = o.get("warnings") or []
    if warnings:
        text += "\nWarning:" + "; ".join(str(w) for w in warnings)
    # §8 per-table contribution summary from real diagnostics.
    tables = []
    per_table = [row for row in (o.get("per_table") or []) if isinstance(row, dict)]
    if per_table:
        tables.append(
            {
                "title": "Contribution of the characterization tables",
                "columns": ["Feature Table", "Hit rate", "New", "New column missing rate", "Re-strategize."],
                "rows": [
                    [
                        str(row.get("feature_id", "?")),
                        _num(row.get("match_rate")),
                        str(row.get("new_columns", "")),
                        _num(row.get("new_columns_null_rate")),
                        str(row.get("dedup_strategy", "None")),
                    ]
                    for row in per_table
                ],
            }
        )
    return text, tables


def _render_post_training_action(o: dict):
    actions = [item for item in (o.get("actions") or []) if isinstance(item, dict)]
    succeeded = sum(1 for item in actions if item.get("status") == "succeeded")
    skipped = sum(1 for item in actions if item.get("status") == "skipped")
    text = (
        f"**Post-training delivery complete.**:Success {succeeded} individual,Skip {skipped} individual."
        if actions
        else "**Post-training delivery complete.**."
    )
    rows = [
        [
            "Native model",
            "succeeded" if o.get("native_model_path") else "missing",
            o.get("native_model_path") or "",
            "",
        ],
    ]
    if o.get("approval_package_path"):
        rows.append(
            [
                "Approval of packages",
                "succeeded",
                o.get("approval_package_markdown_path")
                or o.get("approval_package_path"),
                "Model approval and delivery of evidence kits",
            ]
        )
    if o.get("model_card_path"):
        rows.append(
            [
                "Model card",
                "succeeded",
                o.get("model_card_markdown_path") or o.get("model_card_path"),
                "Final model card",
            ]
        )
    if o.get("monitoring_policy_path"):
        monitoring = (
            o.get("monitoring_policy")
            if isinstance(o.get("monitoring_policy"), dict)
            else {}
        )
        rows.append(
            [
                "Monitoring policy",
                monitoring.get("status") or "succeeded",
                o.get("monitoring_policy_markdown_path")
                or o.get("monitoring_policy_path"),
                monitoring.get("recommendation") or "Model monitoring threshold policy",
            ]
        )
    for item in actions:
        action = str(item.get("action") or "")
        status = str(item.get("status") or "")
        artifact = (
            item.get("pmml_path")
            or item.get("validation_task_id")
            or item.get("challenger_task_id")
            or item.get("markdown_path")
            or item.get("package_path")
            or ""
        )
        rows.append([action, status, artifact, str(item.get("reason") or "")])
    tables = [
        {
            "title": "Post-training delivery",
            "columns": ["Actions", "Status", "Products/Tasks", "Annotations"],
            "rows": rows,
        }
    ]
    caps = o.get("capabilities") or {}
    if caps:
        cap_rows = [
            ["PMML", "Yes." if caps.get("pmml_supported") else "Yes"],
            ["Handover Certification", "Yes." if caps.get("handoff_supported") else "Yes"],
            ["Native model", "Yes." if caps.get("native_model_supported") else "Yes"],
        ]
        if caps.get("reason"):
            cap_rows.append(["Annotations", caps.get("reason")])
        tables.append(
            {"title": "Final model delivery capacity", "columns": ["Capacity", "Status"], "rows": cap_rows}
        )
    return text, tables


def _render_make_split(o: dict, *, presentation_state: str = "preview"):
    """G1 split gate: surface the train/test/oot counts + per month/channel distribution so
    the user can sanity-check the split (proportions, OOT-by-time, no cross-group leakage)
    before spending compute on screening/training."""
    analysis = o.get("sample_analysis") or {}
    counts = analysis.get("split_counts") or {}
    total = analysis.get("total_rows")
    rows = [
        [str(split), int(n), _fmt(n / total) if total else "n/a"]
        for split, n in counts.items()
    ]
    if presentation_state == "adopted":
        text = (
            f"**Sample splitting used**:Total {total} Okay.;"
            "Follow-up feature screening and training is as follows: Train/Test/OOT Programme."
        )
    else:
        text = (
            f"**Sample spectrospect preview generated**:Total {total} Okay.,Not yet entered into characterization screening or training."
            "Please choose whether or not you want to go down there. OOT,Severing method and percentage;The programme will continue only after confirmation."
        )
    tables = []
    if rows:
        tables.append(
            {
                "title": "Cut-point count(train/test/oot)",
                "columns": ["Division", "Lines", "Percentage"],
                "rows": rows,
            }
        )
    for group_col, dist in (analysis.get("group_distributions") or {}).items():
        if not isinstance(dist, dict):
            continue
        group_values = sorted(
            {gv for per in dist.values() if isinstance(per, dict) for gv in per}
        )
        grows = [
            [str(split)] + [int(per.get(gv, 0)) for gv in group_values]
            for split, per in dist.items()
            if isinstance(per, dict)
        ]
        if grows:
            tables.append(
                {
                    "title": f"Press[{group_col}]Distribution(Division)",
                    "columns": ["Division", *[str(gv) for gv in group_values]],
                    "rows": grows,
                }
            )
    return text, tables


def _render_score_dataset(o: dict):
    direction_label = (
        "The higher the score, the higher the risk."
        if o.get("score_direction") == "higher_is_riskier"
        else "The higher the score, the lower the risk."
    )
    text = (
        f"**Scores complete.**({direction_label}):"
        f"{_fmt(o.get('row_count'))} Okay.,Score Column `{o.get('score_col')}`,"
        f"Missing Rate {_pct(o.get('score_missing_rate'))}."
    )
    rows = [
        ["Dataset", o.get("result_dataset_id") or ""],
        ["Score Column", o.get("score_col") or ""],
        ["Loss rate of fractions", _pct(o.get("score_missing_rate"))],
    ]
    if o.get("points_col"):
        text += f" Scorecard points Columns `{o.get('points_col')}`."
        rows.append(["points Columns", o.get("points_col") or ""])
        rows.append(["points Missing Rate", _pct(o.get("points_missing_rate"))])
    return text, [{"title": "Summary of the results of the scores", "columns": ["Item", "Value"], "rows": rows}]


def _render_monitor_run(o: dict):
    overall = str(o.get("overall_level") or "")
    checks = [c for c in (o.get("checks") or []) if isinstance(c, dict)]
    red_flags = [c for c in checks if c.get("level") == "red"]
    amber_flags = [c for c in checks if c.get("level") == "amber"]
    label = _MONITOR_LEVEL_LABEL.get(overall, overall)
    text = f"**Monitor run complete.**:General Level[{label}].{o.get('recommendation') or ''}"
    if red_flags:
        names = ",".join(str(c.get("label") or c.get("id")) for c in red_flags)
        text += f" Red flag:{names}."
    if amber_flags:
        names = ",".join(str(c.get("label") or c.get("id")) for c in amber_flags)
        text += f" Yellow Flag:{names}."
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
                "title": "Characteristic drift Top",
                "columns": ["Characteristics", "CSI"],
                "rows": [
                    [str(row.get("feature") or ""), _fmt(row.get("csi"))]
                    for row in drifted[:10]
                ],
            }
        )
    return text, tables


def _render_flow_rate(o: dict):
    months = [str(m) for m in (o.get("months") or [])]
    net_flows = [row for row in (o.get("net_flows") or []) if isinstance(row, dict)]
    red_flags = [f for f in (o.get("red_flags") or []) if isinstance(f, dict)]
    text = f"**Drum flow analysis complete.**:{len(months)} A month in the neighborhood.."
    if red_flags:
        text += f" Red flag {len(red_flags)} Item."
    tables = []
    if net_flows:
        tables.append(
            {
                "title": "Net monthly flows(Into bad. / Quit Bad)",
                "columns": ["Month", "Into bad.", "Quit Bad"],
                "rows": [
                    [
                        str(r.get("month") or ""),
                        _fmt(r.get("into_bad")),
                        _fmt(r.get("out_of_bad")),
                    ]
                    for r in net_flows
                ],
            }
        )
    if red_flags:
        tables.append(_data_quality_flag_table(red_flags))
    return text, tables


def _render_bucket_migration(o: dict):
    states = [str(s) for s in (o.get("states") or [])]
    to_states = [str(s) for s in (o.get("to_states") or [])]
    heat_table = [row for row in (o.get("heat_table") or []) if isinstance(row, dict)]
    red_flags = [f for f in (o.get("red_flags") or []) if isinstance(f, dict)]
    window = [str(m) for m in (o.get("window_months") or [])]
    text = f"**The barrel of the flow heat is complete.**:{len(states)} Status,Window {len(window)} Month."
    tables = []
    if heat_table and to_states:
        columns = ["from", *to_states]
        rows = [
            [str(row.get("from") or ""), *[_pct(row.get(state)) for state in to_states]]
            for row in heat_table
        ]
        # matrix-heat column_specs: the from label is text, each to-state cell is a
        # heat cell colored from its own 0..1 migration rate (frontend matrix-heat).
        column_specs = [{"kind": "text"}, *[{"kind": "matrix-heat"} for _ in to_states]]
        tables.append(
            {
                "title": "Matrix of average migration rates",
                "columns": columns,
                "rows": rows,
                "column_specs": column_specs,
            }
        )
    if red_flags:
        tables.append(_data_quality_flag_table(red_flags))
    return text, tables


def _render_segment_profile(o: dict):
    segments = [row for row in (o.get("segments") or []) if isinstance(row, dict)]
    conc = o.get("concentration") if isinstance(o.get("concentration"), dict) else {}
    red_flags = [f for f in (o.get("red_flags") or []) if isinstance(f, dict)]
    text = (
        f"**Disaggregated image completed**:{len(segments)} Breakdown,top1 Percentage {_pct(conc.get('top1_pct'))},"
        f"HHI {_fmt(conc.get('hhi'))}."
    )
    tables = []
    if segments:
        tables.append(
            {
                "title": "Disaggregate Image",
                "columns": ["Breakdown", "Number of samples", "Percentage", "Bad rate", "Average", "Net profit"],
                "rows": [
                    [
                        str(r.get("segment") or ""),
                        _fmt(r.get("count")),
                        _pct(r.get("pop_pct")),
                        _pct(r.get("bad_rate"))
                        if r.get("bad_rate") is not None
                        else "n/a",
                        _fmt(r.get("avg_score"))
                        if r.get("avg_score") is not None
                        else "n/a",
                        _fmt(r.get("net_profit"))
                        if r.get("net_profit") is not None
                        else "n/a",
                    ]
                    for r in segments
                ],
            }
        )
    if red_flags:
        tables.append(_data_quality_flag_table(red_flags))
    return text, tables


def _render_el_estimate(o: dict):
    chain = [row for row in (o.get("chain") or []) if isinstance(row, dict)]
    el_by_month = [row for row in (o.get("el_by_month") or []) if isinstance(row, dict)]
    red_flags = [f for f in (o.get("red_flags") or []) if isinstance(f, dict)]
    assumptions = o.get("assumptions") if isinstance(o.get("assumptions"), dict) else {}
    ref = assumptions.get("reference_snapshot")
    # total_el is a reference-snapshotcaliber (latest month), NOT a cross-month sum;
    # annotate the headline so the user tiesTotal EL to a specific month.
    basis_note = f"(Reference Snapshot {ref} caliber)" if ref else ""
    text = f"**Expected losses are estimated to be completed**:Loss pattern `{o.get('loss_state', '')}`,Total EL {_fmt(o.get('total_el'))}{basis_note}."
    tables = []
    if chain:
        tables.append(
            {
                "title": "Absorption probability to loss state",
                "columns": ["Start Status", "P(Losses)"],
                "rows": [
                    [str(r.get("from_state") or ""), _pct(r.get("p_to_loss"))]
                    for r in chain
                ],
            }
        )
    if el_by_month:
        tables.append(
            {
                "title": "Expected monthly losses",
                "columns": ["Month", "Balance", "Expected losses"],
                "rows": [
                    [
                        ("★ " if r.get("is_reference") else "")
                        + str(r.get("month") or ""),
                        _fmt(r.get("balance")),
                        _fmt(r.get("expected_loss")),
                    ]
                    for r in el_by_month
                ],
            }
        )
    if red_flags:
        tables.append(_data_quality_flag_table(red_flags))
    return text, tables


def _render_portfolio_report(o: dict):
    sheets = [str(s) for s in (o.get("sheets") or [])]
    text = (
        f"**Group reports generated**:`{o.get('report_path', '')}`,Ham {len(sheets)} individual sheet."
    )
    tables = []
    if sheets:
        tables.append(
            {
                "title": "Report sheet",
                "columns": ["#", "sheet"],
                "rows": [[str(i), s] for i, s in enumerate(sheets, start=1)],
            }
        )
    return text, tables


def _render_risk_analysis_report(o: dict):
    kind_label = {
        "vtg_terminal": "VTGEnd and year-old poor",
        "profitability": "Proceeds measure",
    }.get(str(o.get("analysis_kind") or ""), "Risk analysis")
    key_points = [str(item) for item in (o.get("key_points") or [])]
    red_flags = [str(item) for item in (o.get("red_flags") or [])]
    assumptions = [str(item) for item in (o.get("assumptions") or [])]
    metrics = (
        o.get("headline_metrics") if isinstance(o.get("headline_metrics"), dict) else {}
    )
    source_row_count = o.get("source_row_count", o.get("row_count", 0))
    text = (
        f"**{kind_label}Report generated**:Source Data {_fmt(source_row_count)} Okay.,"
        f"Form {_fmt(o.get('row_count', 0))} Line Results,"
        "Its through the bottom.(Download Report)View full detail,caliber and data quality checks."
    )
    if key_points:
        text += "\n\n**Important findings**\n" + "\n".join(f"- {item}" for item in key_points)
    if red_flags:
        text += "\n\n**Need to focus.**\n" + "\n".join(f"- {item}" for item in red_flags)
    tables = []
    if metrics:
        metric_labels = {
            "annualized_bad_rate": "Combined annualized downrate",
            "weighted_terminal_bad_rate": "WeightedVTGEnd value",
            "portfolio_turnover": "Group turnover times",
            "observed_annualized_bad_rate": "MOB14Observe annual downscaling rate",
            "lowest_net_yield": "Minimum net product return",
            "highest_net_yield": "Top product net return",
            "negative_product_count": "Number of products with negative net gain",
            "max_cost_rate": "Maximum cost rate",
            "largest_scenario_net_yield_spread": "Maximum net gain on scene",
        }
        tables.append(
            {
                "title": "Core indicators",
                "columns": ["Indicators", "Value"],
                "rows": [
                    [
                        metric_labels.get(str(name), str(name)),
                        _pct(value)
                        if str(name).endswith(("_rate", "_yield", "_spread"))
                        else _fmt(value),
                    ]
                    for name, value in metrics.items()
                ],
            }
        )
    if assumptions:
        tables.append(
            {
                "title": "Calculating calibrations and assumptions",
                "columns": ["#", "caliber/Assumptions"],
                "rows": [
                    [str(index), item]
                    for index, item in enumerate(assumptions, start=1)
                ],
            }
        )
    return text, tables


def _render_portfolio_gate_summary(o: dict):
    checklist = [str(item) for item in (o.get("checklist") or [])]
    highlights = o.get("highlights") if isinstance(o.get("highlights"), dict) else {}
    text = f"**Summary of portfolio analysis**:{o.get('red_flag_count', 0)} Red flag for data quality,Please confirm and generate the report.."
    tables = []
    if highlights:
        tables.append(
            {
                "title": "Key figures",
                "columns": ["Indicators", "Value"],
                "rows": [[str(k), _fmt(v)] for k, v in highlights.items()],
            }
        )
    if checklist:
        tables.append(
            {
                "title": "Red flag checklist",
                "columns": ["#", "Red flag"],
                "rows": [[str(i), item] for i, item in enumerate(checklist, start=1)],
            }
        )
    return text, tables


def _data_quality_flag_table(red_flags: list[dict]) -> dict:
    return {
        "title": "Red flag for data quality",
        "columns": ["Type", "Annotations"],
        "rows": [
            [str(f.get("kind") or ""), str(f.get("message") or "")] for f in red_flags
        ],
    }


_RENDERERS = {
    "make_split": _render_make_split,
    "choose_modeling_spec": _render_choose_modeling_spec,
    "screen_features": _render_screen,
    "select_features": _render_select,
    "configure_tuning": _render_configure_tuning,
    "tune_hyperparameters": _render_tune,
    "train_model": _render_train,
    "train_models": _render_train_models,
    "compare_experiments": _render_compare,
    "select_experiment": _render_select_experiment,
    "post_training_action": _render_post_training_action,
    "generate_model_report": _render_report,
    "generate_model_reports": _render_reports,
    "propose_join": _render_propose_join,
    "confirm_join": _render_confirm_join,
    "execute_join": _render_execute_join,
    "compute_feature_metrics": _render_feature_metrics,
    "analyze_feature_bins": _render_feature_bins,
    "generate_feature_report": _render_feature_report,
    "generate_risk_analysis_report": _render_risk_analysis_report,
    "vintage_curve": _render_vintage_curve,
    "slice_aggregate": _render_slice_aggregate,
    "profile_dataset": _render_profile_dataset,
    "transform_dataset": _render_transform_dataset,
    "export_dataset": _render_export_dataset,
    "score_dataset": _render_score_dataset,
    "monitor_run": _render_monitor_run,
    "flow_rate": _render_flow_rate,
    "bucket_migration": _render_bucket_migration,
    "segment_profile": _render_segment_profile,
    "expected_loss_estimate": _render_el_estimate,
    "portfolio_gate_summary": _render_portfolio_gate_summary,
    "portfolio_report": _render_portfolio_report,
}


def _render_generic(o: dict):
    if not isinstance(o, dict) or not o:
        return "Completed.", []
    scalar = {k: v for k, v in o.items() if isinstance(v, (str, int, float, bool))}
    if scalar:
        head = ", ".join(f"{k}={_fmt(v)}" for k, v in list(scalar.items())[:6])
        return f"Completed:{head}", []
    return "Completed.", []


def _canonical_presenter_integrity_failure() -> tuple[str, list[dict]]:
    return (
        "**Result integrity verification failed**:Platform cannot authenticate the real-time invertible evidence from the current task Tool Output,"
        "Stopping display;Do not downgrade cache fields to normal success results.",
        [],
    )


def _trusted_step_evidence_matches(
    tool: str,
    output: object,
    *,
    trusted_output_ref: str | None,
    trusted_step_evidence: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(trusted_step_evidence, Mapping):
        return False
    if (
        not isinstance(trusted_output_ref, str)
        or not trusted_output_ref
        or trusted_step_evidence.get("output_ref") != trusted_output_ref
        or trusted_step_evidence.get("renderer_hint") != tool
    ):
        return False
    run_id = trusted_step_evidence.get("step_run_id")
    input_hash = trusted_step_evidence.get("input_hash")
    if not isinstance(run_id, str) or not run_id:
        return False
    if (
        not isinstance(input_hash, str)
        or not input_hash.startswith("sha256:")
        or len(input_hash) != 71
        or any(
            character not in "0123456789abcdef"
            for character in input_hash.removeprefix("sha256:")
        )
    ):
        return False
    recorded_refs = trusted_step_evidence.get("artifact_refs")
    if not isinstance(recorded_refs, list) or not all(
        isinstance(ref, str) and ref for ref in recorded_refs
    ):
        return False
    live_refs = artifact_refs(output)
    recorded_bindings = trusted_step_evidence.get("artifact_bindings")
    live_bindings = artifact_bindings(output)
    return (
        bool(live_refs)
        and live_refs == recorded_refs
        and isinstance(recorded_bindings, list)
        and bool(live_bindings)
        and live_bindings == recorded_bindings
    )


def has_tool_presenter(tool: str) -> bool:
    """Return whether a Tool has an explicit domain or facade presenter."""

    return (
        tool in _TRUSTED_RUNTIME_PRESENTERS
        or tool in STRATEGY_RENDERERS
        or tool in _RENDERERS
    )


def render_tool_output(
    tool: str,
    output: dict,
    *,
    trusted_task_id: str | None = None,
    trusted_workspace: Path | str | None = None,
    trusted_output_ref: str | None = None,
    trusted_step_evidence: Mapping[str, Any] | None = None,
    trusted_inputs: Mapping[str, Any] | None = None,
    trusted_artifacts: Mapping[str, Any] | None = None,
    presentation_state: str | None = None,
):
    """Render a tool output, with optional gate-specific presentation context."""
    authenticated_presenter = _TRUSTED_RUNTIME_PRESENTERS.get(tool)
    if authenticated_presenter is not None:
        try:
            if not _trusted_step_evidence_matches(
                tool,
                output,
                trusted_output_ref=trusted_output_ref,
                trusted_step_evidence=trusted_step_evidence,
            ):
                return _canonical_presenter_integrity_failure()
            runtime = build_trusted_presenter_runtime(
                tool,
                workspace=trusted_workspace,
                task_id=trusted_task_id,
            )
            if runtime is None:
                return _canonical_presenter_integrity_failure()
            return authenticated_presenter(
                output or {},
                runtime=runtime,
                task_id=trusted_task_id,
                trusted_inputs=trusted_inputs,
                trusted_artifacts=trusted_artifacts,
            )
        except Exception:
            return _canonical_presenter_integrity_failure()
    if tool == "make_split":
        try:
            return _render_make_split(
                output or {},
                presentation_state=presentation_state or "preview",
            )
        except Exception:
            return _render_generic(output or {})
    renderer = STRATEGY_RENDERERS.get(tool) or _RENDERERS.get(
        tool,
        _render_generic,
    )
    try:
        if tool == "build_voting_candidate_from_search":
            return renderer(
                output or {},
                trusted_inputs=trusted_inputs,
            )
        if tool in {
            "export_strategy_delivery",
            "measure_candidate_monthly_stability",
            "measure_strategy_pool_validation",
            "measure_strategy_pool_stability",
        }:
            return renderer(
                output or {},
                trusted_task_id=trusted_task_id,
                trusted_inputs=trusted_inputs,
                trusted_artifacts=trusted_artifacts,
            )
        return renderer(output or {})
    except Exception:
        integrity_failure = strategy_integrity_failure(tool)
        if integrity_failure is not None:
            return integrity_failure
        return _render_generic(output or {})


def __getattr__(name: str):
    """Keep historical private presenter imports working during migration."""

    try:
        return getattr(_strategy_presenters, name)
    except AttributeError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc


__all__ = ["has_tool_presenter", "render_tool_output"]
