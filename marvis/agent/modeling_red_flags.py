"""Deterministic red-flag checklists for modeling gates (AGT-9).

The JOIN/screening gates already get a platform-computed [Platform Red Flagchecklist]
(``auto_drive._extract_red_flags``) so the LLM re-checks numbers instead of
inventing its own. That coverage stopped at JOIN — the two most consequential
modeling decision gates (which tuning-config funnel to accept, which trained
experiment to select) handed AUTO a bare table of KS/AUC numbers and left the
comparisons to the model itself, exactly the arithmetic a weak model is worst
at.

Both functions here read ONLY numbers a platform tool already computed
(INV-1: the LLM re-checks, it never computes) and return plain Chinese
sentences meant to sit in a gate message's ``metadata['red_flags']`` /
``decide_gate`` prompt, next to the existing JOIN/screen red flags.
"""

from __future__ import annotations

# & Intracting the Configuration Gate("Select Character" gate, pauses before "Configure & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & &" runs): flags derived from
# the split ("Scratch samples"/make_split) + modeling-spec ("Select Model Specification"/
# choose_modeling_spec) outputs, both direct dependencies of that gate.
MIN_SAMPLE_SIZE = 5000
MAX_FEATURE_COUNT = 200

# Select the test door.("Select Experiment" gate): flags derived from the tuning ("Transfer"/
# tune_hyperparameters) + training ("Training model"/train_models) outputs, both
# direct dependencies of that gate.
MAX_TRAIN_TEST_KS_GAP = 0.10
MIN_CHAMPION_RUNNER_UP_KS_GAP = 0.005


def tuning_setup_red_flags(*, split_output: dict | None, modeling_spec_output: dict | None) -> list[str]:
    """Red flags for the tuning-config gate (samples too small, too many
    features, OOT missing) — the checks named in AGT-9's - The door is open.list that this
    template's gate can actually see (make_split + choose_modeling_spec are
    both direct dependencies of that gate)."""
    flags: list[str] = []
    analysis = _dict(split_output).get("sample_analysis")
    split_counts = _split_counts(analysis)
    total_rows = _safe_int(_dict(analysis).get("total_rows"))
    if total_rows is None and split_counts:
        total_rows = sum(split_counts.values())
    if total_rows is not None and total_rows < MIN_SAMPLE_SIZE:
        flags.append(f"Small sample (total){total_rows} Okay.< {MIN_SAMPLE_SIZE}),The sample of indicators may have a higher noise level.")
    if split_counts and split_counts.get("oot", 0) <= 0:
        flags.append("Sample splitting missingOOT((Extra-time) subset, stability conclusions need to be carefully concluded.")
    feature_count = _safe_int(_dict(modeling_spec_output).get("feature_count"))
    if feature_count is not None and feature_count > MAX_FEATURE_COUNT:
        flags.append(f"Multiple candidate characteristics (%){feature_count} > {MAX_FEATURE_COUNT}),Increased risk of matching and training costs.")
    return flags


def select_experiment_red_flags(*, tune_output: dict | None, train_models_output: dict | None) -> list[str]:
    """Red flags for the select-experiment gate (train-test overfit gap,
    champion vs. runner-up margin too thin to be meaningful, weighted vs.
    unweighted champion disagreement, any failed candidate)."""
    flags: list[str] = []
    flags.extend(_overfit_gap_flags(tune_output))
    experiments = [
        item for item in _dict(train_models_output).get("experiments") or [] if isinstance(item, dict)
    ]
    flags.extend(_champion_runner_up_flags(experiments))
    flags.extend(_weighted_unweighted_mismatch_flags(experiments))
    failed = [item for item in _dict(train_models_output).get("failed") or [] if isinstance(item, dict)]
    if failed:
        recipes = ", ".join(str(item.get("recipe") or "?") for item in failed[:8])
        flags.append(f"- In the training phase.{len(failed)} Could not close temporary folder: %s{recipes}),The range of comparisons is incomplete.")
    return flags


def _overfit_gap_flags(tune_output: dict | None) -> list[str]:
    trials = [item for item in _dict(tune_output).get("trials") or [] if isinstance(item, dict)]
    worst_gap = None
    for trial in trials:
        train_ks = _finite(trial.get("train_ks"))
        test_ks = _finite(trial.get("test_ks"))
        if train_ks is None or test_ks is None:
            continue
        gap = train_ks - test_ks
        if worst_gap is None or gap > worst_gap:
            worst_gap = gap
    if worst_gap is not None and worst_gap > MAX_TRAIN_TEST_KS_GAP:
        return [
            f"Transfertrial Medium Maxtrain-test KS Difference{worst_gap:.3f}(> {MAX_TRAIN_TEST_KS_GAP}),There were signs of convergence."
        ]
    return []


def _champion_runner_up_flags(experiments: list[dict]) -> list[str]:
    scores = sorted(
        (score for score in (_champion_score(item) for item in experiments) if score is not None),
        reverse=True,
    )
    if len(scores) < 2:
        return []
    gap = scores[0] - scores[1]
    if gap < MIN_CHAMPION_RUNNER_UP_KS_GAP:
        return [
            f"The champion and the army.test_ks Gaps only{gap:.4f}(< {MIN_CHAMPION_RUNNER_UP_KS_GAP}),"
            "The championship option may fall within the noise range and recommend review rather than direct acceptance."
        ]
    return []


def _weighted_unweighted_mismatch_flags(experiments: list[dict]) -> list[str]:
    weighted_best = _best_recipe(experiments, "weighted_test_ks")
    unweighted_best = _best_recipe(experiments, "test_ks")
    if weighted_best and unweighted_best and weighted_best != unweighted_best:
        return [
            f"Weighted bytest_ks & Unweightedtest_ks The winning algorithms are not consistent."
            f"(Weighted={weighted_best},Unweighted={unweighted_best}),Please confirm whether sample weights should be included in the selected calibre."
        ]
    return []


def _champion_score(experiment: dict) -> float | None:
    metrics = experiment.get("metrics") if isinstance(experiment.get("metrics"), dict) else {}
    value = metrics.get("weighted_test_ks")
    if not isinstance(value, (int, float)):
        value = metrics.get("test_ks")
    return float(value) if isinstance(value, (int, float)) else None


def _best_recipe(experiments: list[dict], metric_key: str) -> str | None:
    best_recipe = None
    best_value = None
    for item in experiments:
        metrics = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}
        value = metrics.get(metric_key)
        if not isinstance(value, (int, float)):
            continue
        if best_value is None or value > best_value:
            best_value = value
            best_recipe = str(item.get("recipe") or "") or None
    return best_recipe


def _split_counts(analysis) -> dict[str, int]:
    counts: dict[str, int] = {}
    raw = _dict(analysis).get("split_counts")
    for key, value in (raw.items() if isinstance(raw, dict) else ()):
        number = _safe_int(value)
        if number is not None:
            counts[str(key).lower()] = number
    return counts


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _finite(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


__all__ = ["select_experiment_red_flags", "tuning_setup_red_flags"]
