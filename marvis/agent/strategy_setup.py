"""Setup (slot-filling) for strategy tasks.

The standard product entry is governed strategy development: it resolves the
sample and business contract but never invents an operating cutoff.  The old
20%-quantile candidate remains available only through the explicit quick-analysis
entry.  More-specific strategy intents are classified before either entry mode so
pricing or portfolio requests can never fall through to an approval plan.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import pandas as pd

from marvis.agent.sample_setup import detect_setup
from marvis.data.contracts import Dataset
from marvis.data.errors import DatasetContentDriftError
from marvis.data.labels import nan_label_mask
from marvis.data.workspace import data_semantic_mapping_hash
from marvis.repositories.strategy import StrategyRepository
from marvis.domain import STRATEGY_OBJECTIVES, FileRole
from marvis.files import scan_source_dir, sha256_file
from marvis.repositories.data_workspace import (
    DataWorkspaceDataError,
    DataWorkspaceRepository,
)
from marvis.strategy_lifecycle import ASSET_STATUS_ADOPTED_LOCAL

_DATA_ROLES = frozenset({FileRole.SAMPLE.value, "sample", "strategy_sample"})
_SCORE_HINTS = (
    "score",
    "pred",
    "prediction",
    "prob",
    "probability",
    "pd",
    "risk_score",
    "model_score",
    "credit_score",
)


# S4: goal phrases that route a strategy task to the rule_strategy template
# (rule mining) instead of the default strategy_analysis. Kept in sync with
# RULE_STRATEGY.goal_patterns; the strategy_setup intent branch multi-recognizes
# these -- parallel to how strategy_development got its own goal_patterns (S2).
_RULE_STRATEGY_GOAL_PATTERNS = (
    "Rule dig",
    "Rule of Refuse",
    "Rule Policy",
    "rule mining",
    "rule strategy",
)

# S5: goal phrases that route a strategy task to the strategy_monitoring template
# (run one monitoring pass for an adopted strategy) instead of a development flow.
# Kept in sync with STRATEGY_MONITORING.goal_patterns; the strategy_setup intent
# branch multi-recognizes these -- the same S4 precedent as rule_strategy above.
_STRATEGY_MONITORING_GOAL_PATTERNS = (
    "Policy monitoring",
    "Run surveillance.",
    "Monitor running policy",
    "monitoring run Policy",
    "strategy monitoring",
    "Monitoring policy",
)

STRATEGY_ENTRY_DEVELOPMENT = "strategy_development"
STRATEGY_ENTRY_ANALYSIS = "strategy_analysis"
_QUICK_STRATEGY_ANALYSIS_GOAL_PATTERNS = (
    "Quick-track analysis",
    "Quick-Trackback",
    "quick strategy analysis",
    "quick strategy backtest",
)
_LIMIT_PRICING_GOAL_PATTERNS = (
    "Amount pricing",
    "Pricing matrix",
    "limit pricing",
    "limit-pricing",
)
_PORTFOLIO_ANALYSIS_GOAL_PATTERNS = (
    "Group analysis",
    "Portfolio risk analysis",
    "portfolio analysis",
)
_STANDARD_ANALYSIS_GOAL_PATTERNS = (
    "Profit analysis",
    "Profit measurement",
    "Proceeds measure",
    "The customer's profit.",
    "Profit calculations",
    "Profit and profitroa",
    "roa",
    "profit analysis",
    "profit calculation",
    "profit calc",
    "Scroll Rate",
    "Migration rate",
    "roll rate",
    "roll-rate",
    "roll_rate",
)
_LIFECYCLE_PROFIT_PATTERNS = (
    "Maximum profit",
    "Maximizing profit",
    "Profit targets",
    "max profit",
    "Approval",
    "Access",
    "cutoff",
)

STRATEGY_INTENT_FULL_DEVELOPMENT = "full_development"
STRATEGY_INTENT_QUICK_ANALYSIS = "quick_analysis"
STRATEGY_INTENT_RULE_MINING = "rule_mining"
STRATEGY_INTENT_MONITORING = "monitoring"
STRATEGY_INTENT_LIMIT_PRICING = "limit_pricing"
STRATEGY_INTENT_PORTFOLIO_ANALYSIS = "portfolio_analysis"
STRATEGY_INTENT_STANDARD_ANALYSIS = "standard_analysis"
_PROFIT_PARAM_FIELDS = (
    "annual_rate",
    "funding_rate",
    "lgd",
    "operating_cost_per_loan",
    "term_months",
)


def is_rule_strategy_goal(*texts: str | None) -> bool:
    haystack = " ".join(text.lower() for text in texts if text)
    return any(pattern.lower() in haystack for pattern in _RULE_STRATEGY_GOAL_PATTERNS)


def is_strategy_monitoring_goal(*texts: str | None) -> bool:
    haystack = " ".join(text.lower() for text in texts if text)
    return any(
        pattern.lower() in haystack for pattern in _STRATEGY_MONITORING_GOAL_PATTERNS
    )


def is_quick_strategy_analysis_goal(*texts: str | None) -> bool:
    """True only for an explicit quick/lightweight request.

    Generic task names such as ``The scale of access strategy is retrofitted.`` are deliberately not treated as
    a quick-mode choice: the product card itself uses that wording, so doing so would
    silently turn the standard development entry back into the lightweight workflow.
    """

    haystack = " ".join(text.lower() for text in texts if text)
    return any(
        pattern.lower() in haystack
        for pattern in _QUICK_STRATEGY_ANALYSIS_GOAL_PATTERNS
    )


def is_limit_pricing_goal(*texts: str | None) -> bool:
    """Recognize an explicit limit/pricing request without matching generic Amount of access."""

    haystack = " ".join(text.lower() for text in texts if text)
    return any(pattern.lower() in haystack for pattern in _LIMIT_PRICING_GOAL_PATTERNS)


def is_portfolio_analysis_goal(*texts: str | None) -> bool:
    haystack = " ".join(text.lower() for text in texts if text)
    return any(
        pattern.lower() in haystack for pattern in _PORTFOLIO_ANALYSIS_GOAL_PATTERNS
    )


def is_standard_strategy_analysis_goal(*texts: str | None) -> bool:
    """Guard standalone deterministic analyses from approval-plan fallback."""

    haystack = " ".join(text.lower() for text in texts if text)
    if not any(
        pattern.lower() in haystack for pattern in _STANDARD_ANALYSIS_GOAL_PATTERNS
    ):
        return False
    if any(
        token in haystack
        for token in ("Scroll Rate", "Migration rate", "roll rate", "roll-rate", "roll_rate")
    ):
        return True
    return not any(
        pattern.lower() in haystack for pattern in _LIFECYCLE_PROFIT_PATTERNS
    )


def resolve_strategy_intent(strategy_input, *texts: str | None) -> str:
    """Return the canonical strategy intent using one explicit priority order.

    Monitoring and rule operations retain their existing precedence.  The two
    recognized-but-not-executed intents follow, so they can return a governed
    redirect instead of silently becoming an approval strategy.  Quick analysis
    must remain explicit; every other strategy request is full development.
    """

    if is_strategy_monitoring_goal(*texts):
        return STRATEGY_INTENT_MONITORING
    if is_rule_strategy_goal(*texts):
        return STRATEGY_INTENT_RULE_MINING
    if is_limit_pricing_goal(*texts):
        return STRATEGY_INTENT_LIMIT_PRICING
    if is_portfolio_analysis_goal(*texts):
        return STRATEGY_INTENT_PORTFOLIO_ANALYSIS
    if is_standard_strategy_analysis_goal(*texts):
        return STRATEGY_INTENT_STANDARD_ANALYSIS
    if is_quick_strategy_analysis_goal(*texts):
        return STRATEGY_INTENT_QUICK_ANALYSIS
    entry_mode = str(_input_value(strategy_input, "entry_mode") or "").strip().lower()
    if entry_mode == STRATEGY_ENTRY_ANALYSIS:
        return STRATEGY_INTENT_QUICK_ANALYSIS
    return STRATEGY_INTENT_FULL_DEVELOPMENT


def strategy_development_clarification(strategy_input) -> dict | None:
    """Return a structured missing-input envelope, or ``None`` when start is safe."""

    strategy_type = (
        str(_input_value(strategy_input, "strategy_type") or "approval").strip().lower()
    )
    if strategy_type not in {"approval", "reject"}:
        return {
            "code": "strategy_typed_spec_required",
            "entry_mode": STRATEGY_ENTRY_DEVELOPMENT,
            "strategy_type": strategy_type,
            "missing_fields": ["strategy_spec"],
            "message": (
                f"{strategy_type} The strategy cannot be applied to access.cutoff Work flow;"
                "Need to be compiled and confirmed for typology by natural language requestStrategy DSL."
            ),
        }

    missing: list[str] = []
    objective = str(_input_value(strategy_input, "objective") or "").strip()
    if not objective:
        missing.append("objective")
    if (
        _input_value(strategy_input, "max_bad_rate") is None
        and _input_value(strategy_input, "min_approval_rate") is None
    ):
        missing.append("max_bad_rate_or_min_approval_rate")

    if objective == "max_profit":
        profit = _input_value(strategy_input, "profit")
        if not str(_input_value(profit, "ead_col") or "").strip():
            missing.append("profit.ead_col")
        if not str(_input_value(profit, "pd_col") or "").strip():
            missing.append("profit.pd_col")
        for field in _PROFIT_PARAM_FIELDS:
            if _input_value(profit, field) is None:
                missing.append(f"profit.{field}")

    if not missing:
        return None
    return {
        "code": "strategy_business_inputs_required",
        "entry_mode": STRATEGY_ENTRY_DEVELOPMENT,
        "missing_fields": missing,
        "message": "Full strategy development requires the identification of business objectives and constraints, and the platform will not use technology defaults as a substitute for business decision-making.",
    }


def strategy_development_slot_clarification(slots) -> dict | None:
    """Validate the generic-plan slot shape before a full plan is instantiated.

    Generic plans expose EAD/PD as top-level slots and the financial assumptions
    under ``profit_params``.  This is intentionally a business one-of/conditional
    validator rather than a set of globally-required ``SlotSpec`` declarations.
    """

    missing: list[str] = []
    invalid: list[str] = []
    objective_value = _input_value(slots, "objective")
    objective = str(objective_value or "").strip()
    if _contract_value_missing(objective_value):
        missing.append("objective")
    elif not isinstance(
        objective_value, str
    ) or objective not in STRATEGY_OBJECTIVES - {""}:
        invalid.append("objective")

    constraint_values = {
        "max_bad_rate": _input_value(slots, "max_bad_rate"),
        "min_approval_rate": _input_value(slots, "min_approval_rate"),
    }
    supplied_constraints = [
        field
        for field, value in constraint_values.items()
        if not _contract_value_missing(value)
    ]
    if not supplied_constraints:
        missing.append("max_bad_rate_or_min_approval_rate")
    else:
        for field in supplied_constraints:
            if not _valid_contract_number(
                constraint_values[field], minimum=0.0, maximum=1.0
            ):
                invalid.append(field)

    if objective == "max_profit":
        for field in ("ead_col", "pd_col"):
            value = _input_value(slots, field)
            if _contract_value_missing(value):
                missing.append(field)
            elif not isinstance(value, str):
                invalid.append(field)
        profit_params = _input_value(slots, "profit_params")
        if profit_params is not None and not isinstance(profit_params, dict):
            invalid.append("profit_params")
        else:
            for field in _PROFIT_PARAM_FIELDS:
                path = f"profit_params.{field}"
                value = _input_value(profit_params, field)
                if _contract_value_missing(value):
                    missing.append(path)
                    continue
                if field in {"annual_rate", "funding_rate", "lgd"}:
                    valid = _valid_contract_number(value, minimum=0.0, maximum=1.0)
                elif field == "operating_cost_per_loan":
                    valid = _valid_contract_number(value, minimum=0.0)
                else:
                    valid = (
                        isinstance(value, int)
                        and not isinstance(value, bool)
                        and value >= 1
                    )
                if not valid:
                    invalid.append(path)

    if not missing and not invalid:
        return None
    return {
        "code": (
            "strategy_business_inputs_invalid"
            if invalid
            else "strategy_business_inputs_required"
        ),
        "template_id": STRATEGY_ENTRY_DEVELOPMENT,
        "missing_fields": missing,
        "invalid_fields": invalid,
        "message": (
            "The full policy development parameter format or range is invalid, please click on the businesscontract Amendments."
            if invalid
            else "Full strategy development requires the identification of business objectives and constraints, and the platform will not use technology defaults as a substitute for business decision-making."
        ),
    }


def _contract_value_missing(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _valid_contract_number(
    value,
    *,
    minimum: float,
    maximum: float | None = None,
) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        return False
    return maximum is None or number <= maximum


class StrategySetupError(ValueError):
    """Raised when a strategy task cannot infer a scored binary sample."""


@dataclass(frozen=True)
class StrategyDatasetContext:
    """Task-owned dataset facts exposed to request compilation and workflows.

    This is deliberately narrower than a strategy proposal: resolving context
    must not invent a cutoff, rule, action or business objective.
    """

    dataset_id: str
    dataset_name: str
    target_col: str | None
    columns: tuple[str, ...]
    dataset_content_hash: str | None = None
    workspace_revision: int | None = None
    analysis_generation: int | None = None
    semantic_mapping_hash: str | None = None


@dataclass(frozen=True)
class StrategyDatasetPreview:
    """Read-only dataset facts used before the user confirms a request."""

    dataset_id: str | None
    dataset_name: str
    target_col: str | None
    columns: tuple[str, ...]
    identity: dict


@dataclass(frozen=True)
class _ResolvedStrategyDataset:
    dataset: Dataset
    path: Path
    workspace_target_col: str | None = None
    workspace_revision: int | None = None
    analysis_generation: int | None = None
    semantic_mapping_hash: str | None = None


def preview_strategy_dataset_context(
    registry,
    backend,
    task_id: str,
    source_dir,
    *,
    target_col: str | None = None,
) -> StrategyDatasetPreview:
    """Inspect columns without registering, converting or persisting a dataset."""

    active = _resolve_active_workspace_dataset(registry, task_id)
    datasets = []
    if active is None:
        datasets = [
            dataset
            for dataset in registry.list_for_task(task_id)
            if dataset.role in _DATA_ROLES
        ]
    if active is not None or datasets:
        if active is None:
            dataset = _select_dataset(datasets)
            path = registry.resolve_path(dataset.id)
            workspace_target_col = None
        else:
            dataset = active.dataset
            path = active.path
            workspace_target_col = active.workspace_target_col
        identity = {
            "kind": "registered",
            "dataset_id": dataset.id,
            # The catalog hash describes the bytes at registration time.  The
            # confirmation boundary must bind the bytes that are actually on
            # disk now, otherwise an out-of-band same-schema rewrite could
            # reuse an already-confirmed request against different rows.
            "content_hash": sha256_file(path),
        }
        dataset_id = dataset.id
        dataset_name = _dataset_name(dataset)
    else:
        if source_dir is None:
            raise StrategySetupError("No data files were found for the strategic analysis.")
        artifacts = [
            artifact
            for artifact in scan_source_dir(Path(source_dir))
            if artifact.role == FileRole.SAMPLE
        ]
        if not artifacts:
            raise StrategySetupError(f"Data files not found in the policy analysis:{source_dir}")
        if len(artifacts) != 1:
            raise StrategySetupError(
                "The policy directory contains multiple samples; please clearly select a sample of the strategy, and the platform does not speculate before confirmation."
            )
        artifact = artifacts[0]
        path = Path(artifact.path)
        stat = path.stat()
        identity = {
            "kind": "source",
            "source_path": str(path.resolve()),
            "size_bytes": int(stat.st_size),
            "mtime_ns": int(stat.st_mtime_ns),
            "sha256": artifact.sha256,
        }
        dataset_id = None
        dataset_name = path.name

    identity.update(_strategy_workspace_identity(registry, task_id))

    columns = list(backend.column_names(path))
    try:
        resolved_target = _resolve_target_col(
            backend,
            path,
            columns,
            _preferred_target_col(
                columns,
                requested=target_col,
                workspace_target_col=workspace_target_col
                if active is not None
                else None,
            ),
        )
    except StrategySetupError:
        resolved_target = None
    return StrategyDatasetPreview(
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        target_col=resolved_target,
        columns=tuple(columns),
        identity=identity,
    )


def build_strategy_dataset_context(
    registry,
    backend,
    task_id: str,
    source_dir,
    *,
    target_col: str | None = None,
    require_target: bool = True,
) -> StrategyDatasetContext:
    """Register the sample and resolve only the evidence required by an operation.

    Evaluation needs a binary target; deterministic application to a production
    sample does not. Keeping that distinction here prevents ``apply`` from
    inventing or requiring a label that is unavailable at decision time.
    """

    resolved = _resolve_dataset_binding(registry, task_id, source_dir)
    dataset = resolved.dataset
    path = resolved.path
    columns = list(backend.column_names(path))
    preferred_target = _preferred_target_col(
        columns,
        requested=target_col,
        workspace_target_col=resolved.workspace_target_col,
    )
    if require_target:
        resolved_target = _resolve_target_col(
            backend,
            path,
            columns,
            preferred_target,
        )
    else:
        try:
            resolved_target = _resolve_target_col(
                backend,
                path,
                columns,
                preferred_target,
            )
        except StrategySetupError:
            resolved_target = None
    workspace_revision = None
    analysis_generation = None
    semantic_mapping_hash = None
    dataset_repo = getattr(registry, "_repo", None)
    db_path = getattr(dataset_repo, "db_path", None)
    if db_path is not None:
        try:
            snapshot = DataWorkspaceRepository(Path(db_path)).get_or_default(task_id)
        except (DataWorkspaceDataError, KeyError, TypeError, ValueError) as exc:
            raise StrategySetupError(
                "The data workspace for strategic analysis is invalid. Please re-select the task data set."
            ) from exc
        if snapshot.active_dataset_id is not None and (
            snapshot.active_dataset_id != dataset.id
            or snapshot.active_dataset_content_hash != dataset.content_hash
        ):
            raise StrategySetupError("The data workspaces for strategic analysis changed during context analysis.")
        workspace_revision = snapshot.revision
        analysis_generation = snapshot.analysis_generation
        semantic_mapping_hash = data_semantic_mapping_hash(snapshot.semantic_mapping)
    return StrategyDatasetContext(
        dataset_id=dataset.id,
        dataset_name=_dataset_name(dataset),
        target_col=resolved_target,
        columns=tuple(columns),
        dataset_content_hash=dataset.content_hash,
        workspace_revision=workspace_revision,
        analysis_generation=analysis_generation,
        semantic_mapping_hash=semantic_mapping_hash,
    )


@dataclass
class StrategyProposal:
    dataset_id: str
    dataset_name: str
    target_col: str
    score_col: str
    strategy_type: str
    rules: list[dict]
    default_decision: str
    cutoff: float
    direction: str
    bad_rate: float | None
    notes: list[str]
    template_id: str = "strategy_analysis"

    def template_slots(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "target_col": self.target_col,
            "score_col": self.score_col,
            "strategy_type": self.strategy_type,
            "rules": self.rules,
            "default_decision": self.default_decision,
        }


@dataclass
class StrategyDevelopmentProposal:
    """Slots for the full workflow, without a pre-built cutoff or rule candidate."""

    dataset_id: str
    dataset_name: str
    target_col: str
    score_col: str
    strategy_type: str
    objective: str
    max_bad_rate: float | None
    min_approval_rate: float | None
    baseline_strategy_id: str | None
    ead_col: str | None
    pd_col: str | None
    profit_params: dict | None
    bad_rate: float | None
    notes: list[str]
    template_id: str = STRATEGY_ENTRY_DEVELOPMENT

    def template_slots(self) -> dict:
        slots = {
            "dataset_id": self.dataset_id,
            "target_col": self.target_col,
            "score_col": self.score_col,
            "strategy_type": self.strategy_type,
            "objective": self.objective,
            "max_bad_rate": self.max_bad_rate,
            "min_approval_rate": self.min_approval_rate,
            "baseline_strategy_id": self.baseline_strategy_id,
            "ead_col": self.ead_col,
            "pd_col": self.pd_col,
            "profit_params": self.profit_params,
        }
        return {key: value for key, value in slots.items() if value is not None}


@dataclass
class RuleStrategyProposal:
    """S4: setup proposal that routes to the rule_strategy template. Unlike the
    lightweight strategy_analysis proposal it carries no pre-built rules -- the
    template's mine_rules step discovers them -- only the dataset/target anchor
    and the rule-mining slots. The adoption reason is collected only at the final
    evidence-bound gate, never during task setup."""

    dataset_id: str
    dataset_name: str
    target_col: str
    score_col: str | None
    bad_rate: float | None
    notes: list[str]
    template_id: str = "rule_strategy"

    def template_slots(self) -> dict:
        slots: dict = {
            "dataset_id": self.dataset_id,
            "target_col": self.target_col,
        }
        if self.score_col:
            slots["score_col"] = self.score_col
        return slots


@dataclass
class MonitoringSetupProposal:
    """S5: setup proposal that routes to the strategy_monitoring template. Resolves
    the task's single adopted strategy plus the fresh monitoring sample; the
    template's run_strategy_monitoring step reads the plan off the adopted strategy
    and grades drift against the adoption baseline."""

    strategy_id: str
    dataset_id: str
    dataset_name: str
    score_col: str | None
    target_col: str | None
    notes: list[str]
    template_id: str = "strategy_monitoring"

    def template_slots(self) -> dict:
        slots: dict = {"strategy_id": self.strategy_id, "dataset_id": self.dataset_id}
        if self.score_col:
            slots["score_col"] = self.score_col
        if self.target_col:
            slots["target_col"] = self.target_col
        return slots


def build_monitoring_setup_proposal(
    registry,
    backend,
    db_path,
    task_id: str,
    source_dir,
    *,
    target_col: str | None = None,
    score_col: str | None = None,
) -> MonitoringSetupProposal:
    """Resolve the locally adopted strategy + fresh sample for a monitoring task.

    A monitoring task must have exactly one adopted strategy to monitor; if none is
    adopted yet, that is a setup error (nothing to monitor). The dataset is the new
    performance/application sample (resolved the same way as a development task's
    sample). target_col/score_col are optional passthroughs (labels may not have
    matured; score_col only matters for a model-backed strategy)."""
    adopted = [
        meta
        for meta in StrategyRepository(db_path).list_meta_for_task(task_id)
        if meta.get("asset_status") == ASSET_STATUS_ADOPTED_LOCAL
    ]
    if not adopted:
        raise StrategySetupError(
            "The current mission has no locally adopted strategy to implement monitoring; please adopt a strategy first."
            "Locally accepted, not representing production on line."
        )
    strategy_id = str(adopted[-1]["id"])
    dataset = _resolve_dataset(registry, task_id, source_dir)
    path = registry.resolve_path(dataset.id)
    columns = backend.column_names(path)
    resolved_target = target_col if (target_col and target_col in columns) else None
    resolved_score = _optional_score_col(columns, score_col)
    notes = [
        f"Locally adopted strategy{strategy_id} Run a surveillance and drift with the adopted baseline."
        "Locally accepted, not representing production on line."
    ]
    return MonitoringSetupProposal(
        strategy_id=strategy_id,
        dataset_id=dataset.id,
        dataset_name=_dataset_name(dataset),
        score_col=resolved_score,
        target_col=resolved_target,
        notes=notes,
    )


def build_strategy_proposal(
    registry,
    backend,
    task_id: str,
    source_dir,
    *,
    target_col: str | None = None,
    score_col: str | None = None,
) -> StrategyProposal:
    dataset = _resolve_dataset(registry, task_id, source_dir)
    path = registry.resolve_path(dataset.id)
    columns = backend.column_names(path)
    resolved_target = _resolve_target_col(backend, path, columns, target_col)
    resolved_score = _resolve_score_col(columns, score_col)
    if not resolved_score.isidentifier():
        raise StrategySetupError(
            f"Policy conditions are now only supportedPython Identifiers listing; breakdown`{resolved_score}` You need to rename it before retesting."
        )
    frame = backend.read_frame(path, columns=[resolved_target, resolved_score])
    profile = _score_profile(
        frame, target_col=resolved_target, score_col=resolved_score
    )
    rule = {
        "condition": profile["condition"],
        "decision": "reject",
    }
    return StrategyProposal(
        dataset_id=dataset.id,
        dataset_name=_dataset_name(dataset),
        target_col=resolved_target,
        score_col=resolved_score,
        strategy_type="approval",
        rules=[rule],
        default_decision="approve",
        cutoff=profile["cutoff"],
        direction=profile["direction"],
        bad_rate=profile["bad_rate"],
        notes=profile["notes"],
    )


def build_strategy_development_proposal(
    registry,
    backend,
    task_id: str,
    source_dir,
    *,
    strategy_input,
    target_col: str | None = None,
    score_col: str | None = None,
) -> StrategyDevelopmentProposal:
    """Build the full-workflow slots without choosing a cutoff or creating rules."""

    clarification = strategy_development_clarification(strategy_input)
    if clarification is not None:
        raise StrategySetupError(clarification["message"])

    dataset = _resolve_dataset(registry, task_id, source_dir)
    path = registry.resolve_path(dataset.id)
    columns = backend.column_names(path)
    resolved_target = _resolve_target_col(backend, path, columns, target_col)
    resolved_score = _resolve_score_col(columns, score_col)
    if not resolved_score.isidentifier():
        raise StrategySetupError(
            f"Policy conditions are now only supportedPython Identifiers listing; breakdown`{resolved_score}` You need to rename it before retesting."
        )

    profit = _input_value(strategy_input, "profit")
    ead_col = _optional_text(_input_value(profit, "ead_col"))
    pd_col = _optional_text(_input_value(profit, "pd_col"))
    objective = str(_input_value(strategy_input, "objective") or "").strip()
    if objective == "max_profit":
        missing_columns = [
            column for column in (ead_col, pd_col) if column not in columns
        ]
        if missing_columns:
            raise StrategySetupError(
                "The data column quoted by the profit target does not exist:"
                + ",".join(f"`{column}`" for column in missing_columns)
            )

    bad_rate, n_nan_labels = _target_bad_rate(backend, path, resolved_target)
    notes = ["Not generatedcutoff or rules; viable options will be scanned according to the identified business objectives and constraints."]
    if n_nan_labels:
        notes.append(
            f"Target column`{resolved_target}` Yes.{n_nan_labels} Line Tabs are empty/(a) Illegal;"
            "The preview bad rate has been excluded from these lines, and the door still needs to be identified by tag processing for implementation."
        )
    return StrategyDevelopmentProposal(
        dataset_id=dataset.id,
        dataset_name=_dataset_name(dataset),
        target_col=resolved_target,
        score_col=resolved_score,
        strategy_type=str(_input_value(strategy_input, "strategy_type") or "approval"),
        objective=objective,
        max_bad_rate=_optional_float_value(
            _input_value(strategy_input, "max_bad_rate")
        ),
        min_approval_rate=_optional_float_value(
            _input_value(strategy_input, "min_approval_rate")
        ),
        baseline_strategy_id=_optional_text(
            _input_value(strategy_input, "baseline_strategy_id")
        ),
        ead_col=ead_col,
        pd_col=pd_col,
        profit_params=_profit_params_payload(profit),
        bad_rate=bad_rate,
        notes=notes,
    )


def build_rule_strategy_proposal(
    registry,
    backend,
    task_id: str,
    source_dir,
    *,
    target_col: str | None = None,
    score_col: str | None = None,
) -> RuleStrategyProposal:
    """S4: resolve the dataset/target anchor for a rule-mining task. Score is
    optional here (rule mining works on arbitrary numeric features, not just a
    single score); when present it is passed through so build_strategy's rule
    direction self-check can fire on any score-band rules."""
    dataset = _resolve_dataset(registry, task_id, source_dir)
    path = registry.resolve_path(dataset.id)
    columns = backend.column_names(path)
    resolved_target = _resolve_target_col(backend, path, columns, target_col)
    resolved_score = _optional_score_col(columns, score_col)
    bad_rate, n_nan_labels = _target_bad_rate(backend, path, resolved_target)
    notes = ["The rule of rejection will be excavated on data and resonated and adopted after the selection of the rule set."]
    if n_nan_labels:
        notes.append(
            f"Note: Target column`{resolved_target}` Yes.{n_nan_labels} Line Tabs are empty/Illegally,"
            "The preview bad rate has been excluded from these lines; the treatment will be reconfirmed at the time of the return."
        )
    return RuleStrategyProposal(
        dataset_id=dataset.id,
        dataset_name=_dataset_name(dataset),
        target_col=resolved_target,
        score_col=resolved_score,
        bad_rate=bad_rate,
        notes=notes,
    )


def _optional_score_col(columns: list[str], requested: str | None) -> str | None:
    requested = str(requested or "").strip()
    if requested and requested in columns:
        return requested if requested.isidentifier() else None
    return None


def _input_value(payload, name: str):
    if payload is None:
        return None
    if isinstance(payload, dict):
        return payload.get(name)
    return getattr(payload, name, None)


def _optional_text(value) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_float_value(value) -> float | None:
    return None if value is None else float(value)


def _profit_params_payload(profit) -> dict | None:
    if profit is None or any(
        _input_value(profit, field) is None for field in _PROFIT_PARAM_FIELDS
    ):
        return None
    return {field: _input_value(profit, field) for field in _PROFIT_PARAM_FIELDS}


def _target_bad_rate(backend, path, target_col: str) -> tuple[float | None, int]:
    """Preview bad-rate over finite labels, plus the NaN-label count excluded.

    T2-1: this is a pre-gate PREVIEW surface, so it cannot hard-stop the way the
    canonical ``resolve_labeled_frame`` gate does at backtest time. But it must not
    SILENTLY diverge either: it reads finite labels via the same ``nan_label_mask``
    the gate uses (so the bad-rate matches the gated value after a confirmed drop)
    and returns ``n_nan`` so the caller can surface exactly what the gate would.
    Returns ``(None, 0)`` when the column is unreadable or non-numeric (the preview
    stays best-effort; the gate still fires with a hard error downstream).
    """
    try:
        frame = backend.read_frame(path, columns=[target_col])
        mask = nan_label_mask(frame, target_col)
    except Exception:
        return None, 0
    finite = pd.to_numeric(frame[target_col], errors="coerce").to_numpy(dtype=float)[
        ~mask
    ]
    if finite.size == 0:
        return None, int(mask.sum())
    return float((finite == 1).mean()), int(mask.sum())


def _resolve_dataset(registry, task_id: str, source_dir) -> Dataset:
    """Compatibility view for setup paths that only need the dataset record."""

    return _resolve_dataset_binding(registry, task_id, source_dir).dataset


def _resolve_dataset_binding(
    registry,
    task_id: str,
    source_dir,
) -> _ResolvedStrategyDataset:
    active = _resolve_active_workspace_dataset(registry, task_id)
    if active is not None:
        return active
    datasets = [d for d in registry.list_for_task(task_id) if d.role in _DATA_ROLES]
    if not datasets and source_dir is not None:
        for artifact in scan_source_dir(Path(source_dir)):
            if artifact.role == FileRole.SAMPLE:
                registry.register_from_upload(
                    task_id, Path(artifact.path), role="sample"
                )
        datasets = [d for d in registry.list_for_task(task_id) if d.role in _DATA_ROLES]
    if not datasets:
        raise StrategySetupError(f"Data files not found in the policy analysis:{source_dir}")
    dataset = _select_dataset(datasets)
    return _ResolvedStrategyDataset(
        dataset=dataset,
        path=registry.resolve_path(dataset.id),
    )


def _resolve_active_workspace_dataset(
    registry,
    task_id: str,
) -> _ResolvedStrategyDataset | None:
    """Return the exact task-scoped workspace selection, if one exists.

    Some narrow legacy/unit-test registries do not expose a database-backed
    repository.  They retain the pre-workspace fallback.  A real registry with
    a workspace selection is fail-closed: an invalid owner, catalog hash, or
    physical file hash must never silently select a different (often larger)
    historical sample.
    """

    dataset_repo = getattr(registry, "_repo", None)
    db_path = getattr(dataset_repo, "db_path", None)
    if db_path is None:
        return None
    try:
        snapshot = DataWorkspaceRepository(Path(db_path)).get_or_default(task_id)
    except (DataWorkspaceDataError, KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "The data workspace for strategic analysis is invalid. Please re-select the task data set."
        ) from exc
    if snapshot.active_dataset_id is None:
        return None
    try:
        dataset = registry.get(snapshot.active_dataset_id)
        if dataset.task_id != task_id:
            raise StrategySetupError("The activity data set for strategic analysis is not part of the current task.")
        if dataset.content_hash != snapshot.active_dataset_content_hash:
            raise StrategySetupError("The activity data set for strategic analysis does not match the binding of the workspace.")
        path = registry.resolve_verified_path(dataset.id)
    except StrategySetupError:
        raise
    except (DatasetContentDriftError, KeyError, OSError, ValueError) as exc:
        raise StrategySetupError(
            "The activity data set for strategic analysis cannot be validated by attribution or content."
        ) from exc
    return _ResolvedStrategyDataset(
        dataset=dataset,
        path=path,
        workspace_target_col=snapshot.semantic_mapping.target_col,
        workspace_revision=snapshot.revision,
        analysis_generation=snapshot.analysis_generation,
        semantic_mapping_hash=data_semantic_mapping_hash(snapshot.semantic_mapping),
    )


def _strategy_workspace_identity(registry, task_id: str) -> dict[str, object]:
    dataset_repo = getattr(registry, "_repo", None)
    db_path = getattr(dataset_repo, "db_path", None)
    if db_path is None:
        return {}
    try:
        snapshot = DataWorkspaceRepository(Path(db_path)).get_or_default(task_id)
    except (DataWorkspaceDataError, KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "The data workspace for strategic analysis is invalid. Please re-select the task data set."
        ) from exc
    return {
        "workspace_revision": snapshot.revision,
        "analysis_generation": snapshot.analysis_generation,
        "semantic_mapping_hash": data_semantic_mapping_hash(snapshot.semantic_mapping),
    }


def _preferred_target_col(
    columns: list[str],
    *,
    requested: str | None,
    workspace_target_col: str | None,
) -> str | None:
    requested = str(requested or "").strip()
    if requested and requested in columns:
        return requested
    workspace_target = str(workspace_target_col or "").strip()
    if workspace_target and workspace_target in columns:
        return workspace_target
    return requested or None


def _select_dataset(datasets):
    return sorted(
        datasets,
        key=lambda d: (
            not bool(getattr(d, "has_target", False)),
            -int(getattr(d, "row_count", 0) or 0),
        ),
    )[0]


def _resolve_target_col(
    backend, path: Path, columns: list[str], requested: str | None
) -> str:
    requested = str(requested or "").strip()
    if requested and requested in columns:
        return requested
    setup = detect_setup(backend, path)
    if setup.target_col:
        return setup.target_col
    raise StrategySetupError("Unrecognized 0/1 destination bar;specify when creating jobstarget_col.")


def _resolve_score_col(columns: list[str], requested: str | None) -> str:
    requested = str(requested or "").strip()
    if requested and requested in columns:
        return requested
    lowered = {column.lower(): column for column in columns}
    for hint in _SCORE_HINTS:
        if hint in lowered:
            return lowered[hint]
    for column in columns:
        low = column.lower()
        if "score" in low or low in {"pred", "pd"} or "prob" in low:
            return column
    raise StrategySetupError("Could not identify rating breakdown; please specify when creating taskscore_col.")


def _score_profile(frame: pd.DataFrame, *, target_col: str, score_col: str) -> dict:
    clean = frame[[target_col, score_col]].copy()
    # T2-1: read finite labels via the canonical nan_label_mask so the preview
    # bad-rate uses the SAME label semantics as the resolve_labeled_frame gate that
    # backtesting applies later (no silent divergence). A NaN *score* drop is a
    # legitimately different concern (score is not a label), so it stays a plain
    # dropna; only the NaN-LABEL count is surfaced back to the user.
    try:
        label_nan_mask = nan_label_mask(clean, target_col)
    except Exception as exc:  # non-numeric labels: mirror the gate's hard error
        raise StrategySetupError(
            f"Target column`{target_col}` Includes non-numeric labels, not available as 0/1 Target preview; please try again after correction."
        ) from exc
    n_nan_labels = int(label_nan_mask.sum())
    clean[target_col] = pd.to_numeric(clean[target_col], errors="coerce")
    clean[score_col] = pd.to_numeric(clean[score_col], errors="coerce")
    clean = clean.loc[~label_nan_mask].dropna()
    if clean.empty:
        raise StrategySetupError("Target column/The breakdown does not have a valid value for strategic retrospect.")
    target = clean[target_col].astype(int)
    scores = clean[score_col].astype(float)
    bad_rate = float((target == 1).mean())
    corr = scores.rank(method="average").corr(target)
    higher_score_riskier = bool(corr is not None and pd.notna(corr) and corr > 0)
    quantile = 0.80 if higher_score_riskier else 0.20
    cutoff = float(scores.quantile(quantile))
    cutoff_literal = _number_literal(cutoff)
    if higher_score_riskier:
        condition = f"{score_col} >= {cutoff_literal}"
        direction = "higher_score_riskier"
        notes = [
            f"The higher the rating, the higher the negative sample rate, the higher the default rejection rate of about 20% (cutoff={cutoff_literal})."
        ]
    else:
        condition = f"{score_col} < {cutoff_literal}"
        direction = "lower_score_riskier"
        notes = [
            f"The lower the rating, the higher the negative sample rate, the default rejection of the lowest rating of about 20% (%)cutoff={cutoff_literal})."
        ]
    if n_nan_labels:
        notes.append(
            f"Note: Target column`{target_col}` Yes.{n_nan_labels} Line Tabs are empty/Illegally,"
            "Preview the bad rate andcutoff These lines have been excluded; the treatment will be reconfirmed at the back of the survey."
        )
    return {
        "condition": condition,
        "cutoff": cutoff,
        "direction": direction,
        "bad_rate": bad_rate,
        "notes": notes,
    }


def _number_literal(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{float(value):.6g}"


def _dataset_name(dataset) -> str:
    source = getattr(dataset, "source_path", None)
    return Path(source).name if source else str(getattr(dataset, "id", ""))


__all__ = [
    "MonitoringSetupProposal",
    "RuleStrategyProposal",
    "STRATEGY_ENTRY_ANALYSIS",
    "STRATEGY_ENTRY_DEVELOPMENT",
    "STRATEGY_INTENT_FULL_DEVELOPMENT",
    "STRATEGY_INTENT_LIMIT_PRICING",
    "STRATEGY_INTENT_MONITORING",
    "STRATEGY_INTENT_PORTFOLIO_ANALYSIS",
    "STRATEGY_INTENT_QUICK_ANALYSIS",
    "STRATEGY_INTENT_RULE_MINING",
    "STRATEGY_INTENT_STANDARD_ANALYSIS",
    "StrategyDevelopmentProposal",
    "StrategyDatasetContext",
    "StrategyDatasetPreview",
    "StrategyProposal",
    "StrategySetupError",
    "build_monitoring_setup_proposal",
    "build_rule_strategy_proposal",
    "build_strategy_dataset_context",
    "build_strategy_development_proposal",
    "build_strategy_proposal",
    "preview_strategy_dataset_context",
    "is_limit_pricing_goal",
    "is_portfolio_analysis_goal",
    "is_quick_strategy_analysis_goal",
    "is_rule_strategy_goal",
    "is_strategy_monitoring_goal",
    "is_standard_strategy_analysis_goal",
    "resolve_strategy_intent",
    "strategy_development_clarification",
    "strategy_development_slot_clarification",
]
