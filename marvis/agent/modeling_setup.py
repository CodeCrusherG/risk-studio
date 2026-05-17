"""Setup (slot-filling) for the modeling task.

Discovers the registered sample, detects the target column, the train/test/oot
split column + values, and the numeric candidate features, then fills the
`modeling` template slots. When the sample already carries a split column we use
it. When it does not, we generate a grouped train/test split via ``make_split``
(spec §2 G1): anti-leakage grouping by an identity column when present, fixed
seed, non-empty guards. When a date/month business column has been detected
(e.g. loan_month/apply_month), OOT is time-extrapolated by default — the most
recent slice of the timeline is held out as OOT, credit-risk-standard (SEL-1).
Without such a column, no OOT is fabricated: a real out-of-time holdout needs a
time/split column, so downstream OOT metrics simply degrade to n/a rather than
mislabelling a random holdout as out-of-time.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from marvis.agent.data_setup import reconcile_source_data_tables
from marvis.data.data_dictionary import resolve_data_dictionary_id
from marvis.agent.join_setup import (
    AuthenticatedJoinSelection,
    authenticate_join_selection,
    propose_roles,
)
from marvis.agent.sample_setup import detect_setup
from marvis.data.errors import DatasetContentDriftError
from marvis.domain import FileRole
from marvis.modeling_limits import normalize_n_trials
from marvis.packs.modeling.defaults import DEFAULT_RANDOM_SEED
from marvis.packs.modeling.prepare import DEFAULT_OOT_SIZE

_DATA_ROLES = frozenset({FileRole.SAMPLE.value, "sample", "feature"})
_DEFAULT_N_TRIALS = 1


class ModelingSetupError(ValueError):
    """Raised when the sample can't be set up for modeling."""


@dataclass
class ModelingProposal:
    dataset_id: str
    dataset_name: str
    target_col: str
    feature_cols: list[str]
    split_col: str
    split_values: dict[str, str]
    holdout_values: list[str]
    bad_rate: float | None
    counts: dict[str, int]
    recipe: str = "lgb"  # primary recipe (the one tuned, if lgb is among recipes)
    recipes: list[str] = field(default_factory=lambda: ["lgb"])  # all recipes to train + compare
    seed: int = DEFAULT_RANDOM_SEED
    n_trials: int = _DEFAULT_N_TRIALS
    target_type: str = "binary"  # derived: _regressor⇒continuous, *multiclass*⇒multiclass, else binary
    notes: list[str] = field(default_factory=list)
    template_id: str = "modeling"
    anchor_id: str | None = None
    join_feature_ids: list[str] = field(default_factory=list)
    sample_weight_col: str = ""
    sample_weight_candidates: list[str] = field(default_factory=list)
    sample_weight_diagnostics: list[dict] = field(default_factory=list)
    business_columns: dict[str, object] = field(default_factory=dict)
    feature_dictionary_id: str = ""
    # Auto-split config for flows where the split can only happen inside the plan
    # (joined modeling: the frame does not exist until Execute Spelling). {} = passthrough.
    split_config: dict[str, object] = field(default_factory=dict)
    ingest_notices: list[dict] = field(default_factory=list)

    def template_slots(self) -> dict:
        selection_policy = _default_selection_policy(self.target_type)
        if self.template_id == "modeling_with_join":
            slots = {
                "anchor_id": self.anchor_id or self.dataset_id,
                "feature_ids": list(self.join_feature_ids),
                "target_col": self.target_col,
                # Empty means: infer candidate numeric features from the joined schema.
                "feature_cols": [],
                "split_col": self.split_col,
                "split_values": self.split_values,
                "recipe": self.recipe,
                "recipes": self.recipes,
                "seed": self.seed,
                "n_trials": self.n_trials,
                "holdout_values": self.holdout_values,
                "target_type": self.target_type,
                "split_config": dict(self.split_config),
                "sample_weight_col": self.sample_weight_col,
                "sample_weight_candidates": list(self.sample_weight_candidates),
                "sample_weight_diagnostics": list(self.sample_weight_diagnostics),
                "passthrough_cols": _unique([
                    self.sample_weight_col,
                    *self.sample_weight_candidates,
                    *_business_passthrough_cols(self.business_columns),
                ]),
                "selection_policy": selection_policy,
            }
            return _with_optional_business_slots(slots, self)
        slots = {
            "dataset_id": self.dataset_id,
            "target_col": self.target_col,
            "feature_cols": self.feature_cols,
            "split_col": self.split_col,
            "split_values": self.split_values,
            "recipe": self.recipe,
            "recipes": self.recipes,
            "seed": self.seed,
            "n_trials": self.n_trials,
            "holdout_values": self.holdout_values,
            "target_type": self.target_type,
            # The G1 make_split gate passes the setup-decided split through unchanged
            # ({} = passthrough); re-splitting with rules/time/group config is an adjust.
            "split_config": {},
            "sample_weight_col": self.sample_weight_col,
            "sample_weight_candidates": list(self.sample_weight_candidates),
            "sample_weight_diagnostics": list(self.sample_weight_diagnostics),
            "passthrough_cols": _unique([
                self.sample_weight_col,
                *self.sample_weight_candidates,
                *_business_passthrough_cols(self.business_columns),
            ]),
            "selection_policy": selection_policy,
        }
        return _with_optional_business_slots(slots, self)


# Recipes selectable for the binary credit-risk default; lgb is the recommended
# starting algorithm. mlp = a sklearn DNN (impute→scale→MLP pipeline).
# lgb_regressor = the continuous-target (regression) recipe. ensemble (SEL-6) is
# an explicit opt-in only -- never part of any DEFAULT recipe list (see
# _default_recipe_for_target_type), selectable by naming it explicitly in
# `recipes`.
_SUPPORTED_RECIPES = (
    "lgb",
    "xgb",
    "catboost",
    "lr",
    "scorecard",
    "mlp",
    "ensemble",
    "lgb_regressor",
    "xgb_regressor",
    "lr_regressor",
    "mlp_regressor",
    "lgb_multiclass",
    "xgb_multiclass",
    "lr_multiclass",
    "mlp_multiclass",
)


def supported_modeling_recipes() -> list[str]:
    """Return the recipe ids accepted by the deterministic setup validator."""

    return list(_SUPPORTED_RECIPES)


_BINARY_RECIPES = frozenset({"lgb", "xgb", "catboost", "lr", "scorecard", "mlp", "ensemble"})
_WEIGHT_NAME_HINTS = ("sample_weight", "sampleweight", "weight", "Sample weights", "Weights")
# LT-14: a weight column strongly correlated with the target is a leakage red
# flag (the weight is very likely derived from the outcome itself, e.g. a
# post-hoc "how wrong we were" adjustment) rather than a legitimate sampling /
# reject-inference / business weight, which should be independent of the label.
_SAMPLE_WEIGHT_TARGET_CORR_HIGH_RISK = 0.3
_BUSINESS_COLUMN_ALIASES = {
    "loan_month_col": ("loan_month", "apply_month", "book_month", "Month of the loan", "Month of loan", "Month of application"),
    "interest_rate_col": ("interest_rate", "rate", "apr", "pricing_rate", "Interest rate", "Annual interest rate", "Pricing rate"),
    "loan_amount_col": ("loan_amount", "amount", "loan_amt", "Amount released", "Amount of loan", "Contract amount"),
    "term_col": ("term", "loan_term", "periods", "Term", "Duration", "Loan term"),
    "drawdown_amount_col": ("drawdown_amount", "drawdown", "Amount spent", "Amount of withdrawals", "Amount disbursed"),
    "credit_limit_col": ("credit_limit", "limit", "Credit amount", "Amount", "Credit levels"),
}


def build_modeling_proposal(
    registry, backend, task_id: str, source_dir, *, seed: int = DEFAULT_RANDOM_SEED,
    recipe: str | None = None, recipes: list[str] | None = None,
    n_trials: int | None = None,
    target_type: str | None = None,
    sample_weight_col: str | None = None,
    time_col: str | None = None,
    anchor_id: str | None = None,
    join_feature_ids: list[str] | None = None,
    target_col: str | None = None,
    field_hints: dict | None = None,
    authenticated_selection: AuthenticatedJoinSelection | None = None,
    c1_expected_content_hashes: Mapping[str, str] | None = None,
) -> ModelingProposal:
    normalized_n_trials = _normalize_n_trials(n_trials)
    datasets = _resolve_datasets(registry, task_id, source_dir)
    by_id = {dataset.id: dataset for dataset in datasets}
    join_feature_ids = [str(item_id) for item_id in (join_feature_ids or []) if str(item_id)]
    if authenticated_selection is not None:
        authenticated_selection = _verify_authenticated_selection(
            registry,
            task_id,
            authenticated_selection,
            anchor_id=anchor_id,
            feature_ids=join_feature_ids,
        )
        anchor_id = authenticated_selection.anchor.dataset_id
        join_feature_ids = [
            item.dataset_id for item in authenticated_selection.features
        ]
        if c1_expected_content_hashes is None and set(by_id) != set(
            authenticated_selection.dataset_ids
        ):
            raise ModelingSetupError(
                "Model files assembled inC1 Changes after certification are updated and reconfirmed."
            )
        if c1_expected_content_hashes is not None:
            reviewed_hashes = {
                str(dataset_id): str(content_hash)
                for dataset_id, content_hash in c1_expected_content_hashes.items()
            }
            if set(by_id) != set(reviewed_hashes):
                raise ModelingSetupError(
                    "Model files assembled inC1 Changes after certification are updated and reconfirmed."
                )
            if not set(authenticated_selection.dataset_ids) <= set(reviewed_hashes):
                raise ModelingSetupError(
                    "The certified modelling file is not completeC1 Documents are assembled, please refresh and reconfirm."
                )
            try:
                for dataset_id, content_hash in reviewed_hashes.items():
                    registry.authenticate_dataset_binding(
                        dataset_id,
                        expected_task_id=str(task_id),
                        expected_content_hash=content_hash,
                    )
            except DatasetContentDriftError as exc:
                raise ModelingSetupError(
                    "Model file content inC1 Changes after certification are updated and reconfirmed."
                ) from exc
    if anchor_id:
        if anchor_id not in by_id:
            raise ModelingSetupError("The selected sample master table does not exist; please reconfirm the file role.")
        dataset = by_id[anchor_id]
        join_feature_ids = [
            item_id for item_id in join_feature_ids if item_id in by_id and item_id != anchor_id
        ]
        if authenticated_selection is None:
            selected_ids = [anchor_id, *join_feature_ids]
            authenticated_selection = authenticate_join_selection(
                registry,
                task_id,
                anchor_id=anchor_id,
                feature_ids=join_feature_ids,
                expected_content_hashes={
                    item_id: str(by_id[item_id].content_hash or "")
                    for item_id in selected_ids
                },
            )
        joined = bool(join_feature_ids)
    elif len(datasets) > 1:
        ranked = propose_roles(datasets)
        dataset = ranked[0]
        join_feature_ids = [item.id for item in ranked[1:]]
        joined = bool(join_feature_ids)
    else:
        dataset = datasets[0]
        join_feature_ids = []
        joined = False
    path = (
        authenticated_selection.anchor.path
        if authenticated_selection is not None
        else registry.resolve_verified_path(dataset.id)
    )
    available_columns = backend.column_names(path)
    business_columns = _infer_business_columns(available_columns)
    requested_target_type = _normalize_target_type(target_type)
    profiled_target_type = None
    if target_col:
        profiled_target_type = _infer_configured_target_type(
            backend,
            path,
            target_col=str(target_col),
        )
    inferred_target_type = None
    if not requested_target_type and not recipes and not recipe and target_col:
        inferred_target_type = profiled_target_type
        if inferred_target_type is None:
            raise ModelingSetupError(
                f"Cannot initialise Evolution's mail component.`{target_col}` Accurate value extraction of the complete valuebinary/continuous/"
                "multiclass;Please specify the target type and homologic algorithm in a visible way."
            )
    if recipes:
        recipe_list = [str(item).strip() for item in recipes]
    elif recipe:
        recipe_list = [str(recipe).strip()]
    else:
        recipe_list = [
            _default_recipe_for_target_type(
                requested_target_type or inferred_target_type or "binary"
            )
        ]
    for item in recipe_list:
        if item not in _SUPPORTED_RECIPES:
            raise ModelingSetupError(
                f"Unsupported algorithm`{item}`;Optional:{', '.join(_SUPPORTED_RECIPES)}."
            )
    derived_target_type = _derive_target_type(recipe_list)
    if requested_target_type and requested_target_type != derived_target_type:
        raise ModelingSetupError(
            f"Target type`{requested_target_type}` And algorithms`{', '.join(recipe_list)}` Not matched; please re-select an algorithm of the same type of target."
        )
    target_type = requested_target_type or inferred_target_type or derived_target_type
    setup = detect_setup(
        backend,
        path,
        configured_target=str(target_col or ""),
        target_type=target_type,
        field_hints=field_hints,
    )
    configured_target = str(target_col or "").strip()
    if (
        configured_target
        and profiled_target_type == target_type
        and setup.target_col != configured_target
    ):
        # ``detect_setup`` deliberately uses a bounded probe for general schema
        # discovery. When the complete target-only profile has already proved
        # the configured family, bind that exact user-selected target even if a
        # rare class was absent from the probe. Keep every other bounded setup
        # decision (split and candidate discovery) intact.
        setup.target_col = configured_target
        setup.candidates = [
            column for column in setup.candidates if column != configured_target
        ]
        setup.excluded_categorical = [
            item
            for item in setup.excluded_categorical
            if item.get("column") != configured_target
        ]
        setup.excluded_numeric = [
            item
            for item in setup.excluded_numeric
            if item.get("column") != configured_target
        ]
        if target_type != "binary":
            setup.bad_rate = None
        setup.notes = [
            note
            for note in setup.notes
            if not note.startswith(("Multiple job categories should be specified", "Return to task specified."))
        ]
    if not setup.target_col:
        if target_type == "continuous":
            raise ModelingSetupError("Could not identify a continuous goal column; please confirm that the data contain a numerical target column (e.g.income/amount)Try again after that.")
        if target_type == "multiclass":
            raise ModelingSetupError("Could not identify multiple categories of target columns; please specify 3-20 Target column for category (e.g., risk level)/(a) The following:")
        raise ModelingSetupError("Unrecognized 0/1 Target column; please confirm that the data contain label columns and try again.")
    # D12: the column that drives time-extrapolated OOT. An explicit user time_col
    # (from task creation) wins over the alias heuristic when it names a real anchor
    # column; a time col that IS the label is nonsensical (leakage) and is dropped.
    effective_time_col = _resolve_effective_time_col(time_col, available_columns, business_columns)
    if effective_time_col and effective_time_col == setup.target_col:
        effective_time_col = None
    # The tuner is lgb-specific, so the "primary" recipe (the one tuned) is lgb when
    # it is among the chosen recipes, else the first one (tuning is skipped for it).
    primary_recipe = "lgb" if "lgb" in recipe_list else recipe_list[0]
    notes = list(setup.notes)
    weight_diagnostics = _sample_weight_diagnostics(
        backend,
        path,
        target_col=setup.target_col,
        split_col=setup.split_col,
    )
    weight_candidates = [item["column"] for item in weight_diagnostics if item.get("valid")]
    selected_weight_col = _normalize_sample_weight_col(
        sample_weight_col,
        available_columns=available_columns,
    )
    if selected_weight_col:
        if selected_weight_col == setup.target_col or selected_weight_col == str(setup.split_col or ""):
            raise ModelingSetupError("Sample weights cannot be the target column or cut-down.")
        selected_diag = _sample_weight_diagnostics(
            backend,
            path,
            target_col=setup.target_col,
            split_col=setup.split_col,
            explicit_columns=[selected_weight_col],
        )
        if not selected_diag or not selected_diag[0].get("valid"):
            reason = selected_diag[0].get("reason") if selected_diag else "Not a Numeric weight column"
            raise ModelingSetupError(f"Sample weight column`{selected_weight_col}` Not Available:{reason}.")
        weight_diagnostics = _merge_weight_diagnostics(selected_diag, weight_diagnostics)
    if selected_weight_col:
        notes.append(f"Sample weight column:`{selected_weight_col}`(As Onlysample_weight,Not as an input feature.")
        weight_candidates = _unique([selected_weight_col, *weight_candidates])
    elif weight_candidates:
        display = "/".join(f"`{col}`" for col in weight_candidates[:3])
        notes.append(f"Sample weight candidate column detected:{display};If available, confirmsample_weight_col.")
    if target_type == "continuous":
        notes.append("Return missions (continuing objectives): use of indicatorsRMSE/MAE/R2,Do not calculate the bad rate/KS/AUC.")
    elif target_type == "multiclass":
        notes.append("Multi-classification tasks: use of indicatorsmacro-AUC/logloss/Accuracy rate, no bad rate./KS.")
    auto_split_config: dict[str, object] = {}
    if setup.split_col:
        dataset_id = dataset.id
        split_col = setup.split_col
        split_values = dict(setup.split_values)
        counts = dict(setup.counts)
        # D12 conflict policy: a detected split column wins (conservative — no change
        # for existing-split datasets). When the user explicitly requested a DIFFERENT
        # time_col, tell them the detected split shadowed the requested time-OOT.
        if effective_time_col and effective_time_col != split_col:
            notes.append(
                f"Cut-down detected`{split_col}`,Quantities to be applied (time line not requested)`{effective_time_col}` "
                "Do the time push.OOT);If it takes time to pushOOT,Please remove the cut-down or change the date column cut."
            )
    elif joined:
        dataset_id = dataset.id
        split_col = ""
        split_values = {}
        counts = {}
        group_cols = _detect_group_cols(dataset)
        # The joined frame does not exist yet, so the split must run inside the plan:
        # make_split(split_col="") generates it from this config after Execute Spelling. The
        # anchor's own columns (pre-join) are enough to detect a date/month column, so
        # the same time-extrapolated-OOT default (SEL-1) applies here too, keeping the
        # single-file and joined paths consistent.
        auto_split_config = {"test_size": 0.25, "group_cols": group_cols}
        grouping = f"(Press`{group_cols[0]}` (Cluster leakproof)" if group_cols else "(Line by Line Random)"
        if effective_time_col:
            auto_split_config["oot_by_time"] = effective_time_col
            auto_split_config["oot_size"] = DEFAULT_OOT_SIZE
            notes.append(
                f"Multi-file modelling will be pressed after the spell`{effective_time_col}` Time pushOOT(Recent{int(DEFAULT_OOT_SIZE * 100)}% Time horizon;"
                f"The rest press 75./25 Group Random Cuttrain/test{grouping}."
            )
        else:
            notes.append(
                f"Multi-file modelling will automatically be done after the spell is over 75/25 Group Random Cuttrain/test{grouping};"
                "Not setOOT(Time pushOOT The following is a list of the names of the people who are involved in the crime:OOT The relevant indicators will be shownn/a."
            )
    else:
        dataset_id, split_col, split_values, counts, note = _generate_split(
            registry,
            backend,
            dataset,
            setup,
            seed,
            passthrough_cols=_unique([
                selected_weight_col,
                *weight_candidates,
                *_business_passthrough_cols(business_columns),
            ]),
            time_col=effective_time_col,
        )
        notes.append(note)
    if len(recipe_list) > 1:
        notes.append(f"Algorithm:{'/'.join(recipe_list)}(After multi-calculations, press{_selection_metric_label(target_type)} The best.")
    else:
        notes.append(f"Algorithm:`{recipe_list[0]}`(Optional{'/'.join(_SUPPORTED_RECIPES)}).")
    feature_dictionary_id = resolve_data_dictionary_id(registry, task_id, source_dir)
    if business_columns:
        notes.append("Modelling report line identified, which will generate sample analysis/Vintage/Amounts/Available sections such as low pricing.")
    if feature_dictionary_id:
        notes.append("• Identified dictionaries, which will be used for reporting products/Vendor/Category interpretation.")
    oot = split_values.get("oot")
    return ModelingProposal(
        dataset_id=dataset_id,
        dataset_name=_dataset_name(registry, dataset),
        target_col=setup.target_col,
        feature_cols=list(setup.candidates),
        split_col=split_col,
        split_values=split_values,
        holdout_values=[oot] if oot else [],
        bad_rate=setup.bad_rate,
        counts=counts,
        recipe=primary_recipe,
        recipes=recipe_list,
        seed=seed,
        n_trials=normalized_n_trials,
        target_type=target_type,
        notes=notes,
        template_id="modeling_with_join" if joined else "modeling",
        anchor_id=dataset.id if joined else None,
        join_feature_ids=join_feature_ids,
        sample_weight_col=selected_weight_col,
        sample_weight_candidates=weight_candidates,
        sample_weight_diagnostics=weight_diagnostics,
        business_columns=business_columns,
        feature_dictionary_id=feature_dictionary_id,
        split_config=auto_split_config,
        ingest_notices=_consume_ingest_notices(registry, task_id),
    )


def _verify_authenticated_selection(
    registry,
    task_id: str,
    selection: AuthenticatedJoinSelection,
    *,
    anchor_id: str | None,
    feature_ids: list[str],
) -> AuthenticatedJoinSelection:
    """Re-authenticate a C1 binding immediately before modeling setup reads."""

    expected_task = str(task_id)
    if selection.task_id != expected_task:
        raise ModelingSetupError(
            "The selected authentication model file is not currently on the task, and please re-confirm it after updating."
        )
    if anchor_id and str(anchor_id) != selection.anchor.dataset_id:
        raise ModelingSetupError(
            "Authenticated sample master table with currentC1 The selection does not match, but please update and reconfirm."
        )
    selected_feature_ids = [item.dataset_id for item in selection.features]
    if feature_ids and feature_ids != selected_feature_ids:
        raise ModelingSetupError(
            "Authentication feature sheet and currentC1 The selection does not match, but please update and reconfirm."
        )
    verified_anchor = registry.verify_dataset_binding(selection.anchor)
    verified_features = tuple(
        registry.verify_dataset_binding(item) for item in selection.features
    )
    if any(item.task_id != expected_task for item in (verified_anchor, *verified_features)):
        raise ModelingSetupError(
            "The attribution of the certified data files has changed, and please update and reconfirm."
        )
    return AuthenticatedJoinSelection(
        task_id=expected_task,
        anchor=verified_anchor,
        features=verified_features,
    )


def _consume_ingest_notices(registry, task_id: str) -> list[dict]:
    consume = getattr(registry, "consume_ingest_notices", None)
    return list(consume(task_id)) if callable(consume) else []


def _with_optional_business_slots(slots: dict, proposal: ModelingProposal) -> dict:
    if proposal.business_columns:
        slots["business_columns"] = dict(proposal.business_columns)
    if proposal.feature_dictionary_id:
        slots["feature_dictionary_id"] = proposal.feature_dictionary_id
    return slots


def _business_passthrough_cols(business_columns: dict[str, object]) -> list[str]:
    cols: list[str] = []
    for key, value in business_columns.items():
        if key == "mob_observe_cols" and isinstance(value, list):
            cols.extend(str(item) for item in value)
        elif isinstance(value, str):
            cols.append(value)
    return cols


def _infer_business_columns(columns: list[str]) -> dict[str, object]:
    by_lower = {str(column).strip().lower(): str(column) for column in columns}
    business: dict[str, object] = {}
    for key, aliases in _BUSINESS_COLUMN_ALIASES.items():
        matched = _first_matching_column(by_lower, aliases)
        if matched:
            business[key] = matched
    mob_cols = [
        str(column)
        for column in columns
        if _is_mob_observe_column(str(column))
    ]
    if mob_cols:
        business["mob_observe_cols"] = mob_cols
    return business


def _first_matching_column(by_lower: dict[str, str], aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        matched = by_lower.get(str(alias).strip().lower())
        if matched:
            return matched
    return ""


def _resolve_effective_time_col(
    requested: str | None,
    available_columns: list[str],
    business_columns: dict[str, object],
) -> str | None:
    """Resolve the column that drives time-extrapolated OOT (D12).

    Precedence mirrors vintage_setup._resolve_named_col: an explicit user
    ``requested`` column wins when it exists in the anchor frame (case-insensitive,
    real column name preserved); otherwise fall back to the alias-detected
    loan_month column. A requested-but-absent value (including the inert default
    ``apply_month`` when no such column exists) is NOT fabricated — returning it
    would crash make_split (prepare.py raises 'missing columns'), so it falls
    through to the alias. Returns ``None`` when nothing resolves.
    """
    req = str(requested or "").strip()
    if req:
        if req in available_columns:
            return req
        lower = {str(col).strip().lower(): str(col) for col in available_columns}
        hit = lower.get(req.lower())
        if hit:
            return hit
        # requested but absent -> do not fabricate; fall through to alias
    alias = business_columns.get("loan_month_col")
    return alias if isinstance(alias, str) and alias else None


def _is_mob_observe_column(column: str) -> bool:
    normalized = column.strip().lower().replace("_", "").replace("-", "")
    suffix = normalized[3:] if normalized.startswith("mob") else ""
    return bool(suffix) and suffix[0].isdigit()


def _derive_target_type(recipe_list: list[str]) -> str:
    """Derive the task target_type from the chosen recipes.

    A regression recipe (id ends with "_regressor") ⇒ "continuous"; a multiclass recipe
    (id contains "multiclass") ⇒ "multiclass"; otherwise "binary". Recipe families are
    mutually exclusive within one run (different target shapes), so reject any mix rather
    than silently picking one."""
    has_regression = any(item.endswith("_regressor") for item in recipe_list)
    has_multiclass = any("multiclass" in item for item in recipe_list)
    has_binary = any(item in _BINARY_RECIPES for item in recipe_list)
    family_count = sum(1 for flag in (has_binary, has_regression, has_multiclass) if flag)
    if family_count > 1:
        raise ModelingSetupError(
            "Class II, regression and multi-classic algorithms cannot be used in the same training (different from the target column pattern); please model separately."
        )
    if has_regression:
        return "continuous"
    if has_multiclass:
        return "multiclass"
    return "binary"


def _normalize_target_type(value: str | None) -> str | None:
    if value is None:
        return None
    target_type = str(value).strip().lower()
    if not target_type:
        return None
    if target_type not in {"binary", "continuous", "multiclass"}:
        raise ModelingSetupError(f"Target type not supported`{target_type}`;Optional:binary/continuous/multiclass.")
    return target_type


def _normalize_n_trials(value: int | None) -> int:
    if value is None:
        return _DEFAULT_N_TRIALS
    try:
        normalized = normalize_n_trials(value)
    except ValueError as exc:
        raise ModelingSetupError("n_trials It must be one.-200 .") from exc
    return int(normalized)


def _infer_configured_target_type(backend, path: Path, *, target_col: str) -> str | None:
    """Infer an Agent-mode target family from an explicitly named target column.

    Agent-created modeling tasks intentionally start without a recipe family.
    Once C1 has bound an exact target column, the data profile is sufficient to
    choose the matching default family without requiring the user to recreate
    the task: numeric targets with more than the supported multiclass cardinality
    are continuous; 3-20 distinct values are multiclass; exact 0/1 remains
    binary. Ambiguous or unsupported shapes deliberately fall back to the
    existing binary setup error.
    """

    target_col = str(target_col or "").strip()
    if not target_col or target_col not in backend.column_names(path):
        return None
    frame = backend.read_frame(path, columns=[target_col])
    if target_col not in frame.columns:
        return None
    target = frame[target_col].dropna()
    if target.empty:
        return None
    if pd.api.types.is_numeric_dtype(target.dtype):
        numeric = target.to_numpy(dtype=float)
        if not np.isfinite(numeric).all():
            return None
    unique_values = target.unique().tolist()
    unique_count = len(unique_values)
    binary_values = set(unique_values)
    if unique_count == 2 and binary_values.issubset({0, 1, 0.0, 1.0, True, False}):
        return "binary"
    if 3 <= unique_count <= 20:
        return "multiclass"
    if pd.api.types.is_numeric_dtype(target.dtype) and unique_count > 20:
        return "continuous"
    return None


def _default_recipe_for_target_type(target_type: str) -> str:
    if target_type == "continuous":
        return "lgb_regressor"
    if target_type == "multiclass":
        return "lgb_multiclass"
    return "lgb"


def _default_selection_policy(target_type: str) -> dict[str, bool]:
    if target_type == "binary":
        return {"require_pmml": True, "require_handoff": True}
    return {"require_pmml": False, "require_handoff": False}


def _sample_weight_diagnostics(
    backend,
    path: Path,
    *,
    target_col: str,
    split_col: str | None,
    explicit_columns: list[str] | None = None,
    sample_rows: int = 4000,
) -> list[dict]:
    probe = backend.sample_rows(path, sample_rows, seed=0)
    excluded = {str(target_col), str(split_col or "")}
    columns = explicit_columns or [
        str(column)
        for column in probe.columns
        if any(hint in str(column).lower() or hint in str(column) for hint in _WEIGHT_NAME_HINTS)
    ]
    target_numeric = (
        pd.to_numeric(probe[str(target_col)], errors="coerce")
        if target_col and str(target_col) in probe.columns
        else None
    )
    diagnostics: list[dict] = []
    for column in columns:
        name = str(column)
        if name in excluded:
            continue
        if name not in probe.columns:
            continue
        numeric = pd.to_numeric(probe[name], errors="coerce")
        non_missing = numeric.dropna()
        missing_count = int(numeric.isna().sum())
        reason = ""
        valid = True
        if non_missing.empty:
            valid = False
            reason = "All empty or non-values"
        elif missing_count:
            valid = False
            reason = "Empty or non-value exists"
        elif (non_missing <= 0).any():
            valid = False
            reason = "Existence of an inverse weight"
        elif float(non_missing.sum()) <= 0:
            valid = False
            reason = "The overall weight is not positive"
        leakage_risk, target_corr = _sample_weight_leakage_risk(numeric, target_numeric)
        diagnostics.append({
            "column": name,
            "valid": valid,
            "reason": reason,
            "rows_sampled": int(len(probe)),
            "non_missing": int(non_missing.shape[0]),
            "missing_rate": float(missing_count / len(probe)) if len(probe) else 0.0,
            "min": _maybe_float(non_missing.min()) if not non_missing.empty else None,
            "max": _maybe_float(non_missing.max()) if not non_missing.empty else None,
            "mean": _maybe_float(non_missing.mean()) if not non_missing.empty else None,
            "excluded_from_features": True,
            "leakage_risk": leakage_risk,
            "target_correlation": target_corr,
        })
    return diagnostics


def _sample_weight_leakage_risk(
    weight_numeric: pd.Series, target_numeric: pd.Series | None
) -> tuple[str, float | None]:
    """LT-14: flag weight columns whose sample correlation with the target is
    large in magnitude -- a strong signal the "weight" is actually derived
    from the label (post-hoc, i.e. leakage) rather than an independent
    sampling / reject-inference / business weight. Best-effort only: any
    computation issue (e.g. degenerate variance) falls back to "low" rather
    than blocking setup, matching the existing warn-don't-block posture of
    this diagnostics function."""
    if target_numeric is None:
        return "low", None
    try:
        aligned = pd.concat([weight_numeric, target_numeric], axis=1).dropna()
        if len(aligned) < 2:
            return "low", None
        corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
    except (TypeError, ValueError):
        return "low", None
    if corr is None or pd.isna(corr):
        return "low", None
    corr_value = float(corr)
    risk = "high" if abs(corr_value) >= _SAMPLE_WEIGHT_TARGET_CORR_HIGH_RISK else "low"
    return risk, corr_value


def _merge_weight_diagnostics(primary: list[dict], secondary: list[dict]) -> list[dict]:
    by_column: dict[str, dict] = {}
    for item in [*primary, *secondary]:
        column = str(item.get("column") or "")
        if column and column not in by_column:
            by_column[column] = dict(item)
    return list(by_column.values())


def _maybe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_sample_weight_col(value: str | None, *, available_columns: list[str]) -> str:
    column = str(value or "").strip()
    if not column:
        return ""
    if column not in set(available_columns):
        raise ModelingSetupError(f"Sample weight column`{column}` No; please check for listing.")
    return column


def _selection_metric_label(target_type: str) -> str:
    if target_type == "continuous":
        return "OOT RMSE"
    if target_type == "multiclass":
        return "OOT macro-AUC"
    return "OOT KS"


# Identity-like column names used for anti-leakage grouping (best-effort).
_ID_TOKENS = ("cust_id", "user_id", "id_no", "loan_id", "order_id", "apply_id", "mobile", "phone", "ID card", "Cell phone.", "cust")


def _detect_group_cols(dataset) -> list[str]:
    for profile in dataset.columns:
        name = str(profile.name)
        low = name.lower()
        if any(token in low or token in name for token in _ID_TOKENS):
            return [name]
    return []


def _unique(values: list[str]) -> list[str]:
    return [value for value in dict.fromkeys(str(item).strip() for item in values) if value]


def _generate_split(
    registry, backend, dataset, setup, seed, *,
    passthrough_cols: list[str] | None = None,
    time_col: str | None = None,
):
    """No split column → build a grouped train/test split (spec §2 G1).

    When a date/month business column has been detected (``time_col``), OOT is time-
    extrapolated by default: the most recent slice of the timeline (``DEFAULT_OOT_SIZE``,
    i.e. the last ~1/5) is held out as OOT and the remainder is grouped-random 75/25
    train/test — the credit-risk-standard split (SEL-1). Without a time column, the
    prior behaviour is unchanged: no OOT is fabricated; downstream OOT metrics degrade
    to n/a.
    """
    from marvis.packs.modeling.errors import ModelingError
    from marvis.packs.modeling.prepare import prepare_modeling_frame

    group_cols = _detect_group_cols(dataset)
    split_config: dict[str, object] = {"test_size": 0.25, "group_cols": group_cols}
    passthrough_cols = _unique([*(passthrough_cols or []), *([time_col] if time_col else [])])
    if time_col:
        split_config["oot_by_time"] = time_col
        split_config["oot_size"] = DEFAULT_OOT_SIZE
    try:
        derived = prepare_modeling_frame(
            registry,
            backend,
            dataset.id,
            target_col=setup.target_col,
            feature_cols=list(setup.candidates),
            split_col=None,
            split_config=split_config,
            passthrough_cols=passthrough_cols,
            seed=seed,
        )
    except ModelingError as exc:
        raise ModelingSetupError(f"Auto-ditection failed:{exc}") from exc

    read_cols = ["split", time_col] if time_col else ["split"]
    frame = registry.read_authenticated_parquet_snapshot(
        derived.id,
        columns=read_cols,
    )
    split_series = frame["split"]
    counts = {str(key): int(value) for key, value in split_series.value_counts().items()}
    split_values = {role: role for role in counts}
    grouping = f"(Press`{group_cols[0]}` (Cluster leakproof)" if group_cols else "(Line by Line Random)"
    if time_col and counts.get("oot"):
        oot_time = frame.loc[frame["split"] == "oot", time_col]
        window = f"{oot_time.min()}~{oot_time.max()}"
        note = (
            f"No cut provided, by`{time_col}` Time pushOOT(Intersection{window},{counts['oot']} (a) Lines;"
            f"The rest press 75./25 Group Random Cuttrain/test{grouping}."
        )
    else:
        note = (
            f"No cut-down provided, automatic/25 Group Random Cuttrain/test{grouping};"
            "Not setOOT(Time pushOOT The following is a list of the names of the people who are involved in the crime:OOT The relevant indicators will be shownn/a."
        )
    return derived.id, "split", split_values, counts, note


def _resolve_datasets(registry, task_id: str, source_dir):
    datasets = reconcile_source_data_tables(
        registry,
        task_id,
        source_dir,
        accepted_roles=_DATA_ROLES,
        registered_role="sample",
    )
    if not datasets:
        raise ModelingSetupError(f"Modeling not found sample file:{source_dir}")
    return sorted(
        datasets,
        key=lambda d: (not bool(getattr(d, "has_target", False)), -int(getattr(d, "row_count", 0) or 0)),
    )


def _dataset_name(registry, dataset) -> str:
    source_identity = getattr(registry, "source_identity", None)
    if callable(source_identity):
        try:
            identity = source_identity(dataset.id)
        except (KeyError, OSError, TypeError, ValueError):
            identity = None
        original_name = (
            str(identity.get("original_name") or "").strip()
            if isinstance(identity, dict)
            else ""
        )
        if original_name:
            return original_name
    source = getattr(dataset, "source_path", None)
    return Path(source).name if source else str(getattr(dataset, "id", ""))


__all__ = ["build_modeling_proposal", "ModelingProposal", "ModelingSetupError"]
