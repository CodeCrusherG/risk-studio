"""Canonical Strategy Pool request and plan-preparation adapters.

All persisted Pool, artifact, sample, workspace and current-strategy facts are
resolved through ``bind_workflow_evidence``.  This module validates user-owned
controls and prepares immutable plans; it never reads persistence or runs a Tool.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import math
import re
from typing import Any

from marvis.packs.strategy.dsl import StrategyAction
from marvis.packs.strategy.errors import StrategyError

from .contracts import (
    PreparedStrategyPlan,
    StrategyWorkflowPreparationContext,
    StrategyWorkflowRequirements,
    StrategyWorkflowResolutionContext,
    StrategyWorkflowSpec,
    StrategyWorkflowValidationError,
    deep_freeze,
    deep_thaw,
)


POOL_ADD_WORKFLOW_ID = "strategy_pool_add_candidate"
POOL_REMOVE_WORKFLOW_ID = "strategy_pool_remove_entry"
POOL_SET_ACTION_WORKFLOW_ID = "strategy_pool_set_action"
POOL_REORDER_WORKFLOW_ID = "strategy_pool_reorder"
POOL_COMPILE_WORKFLOW_ID = "strategy_pool_compile"
POOL_MATERIALIZE_WORKFLOW_ID = "strategy_pool_materialize"
POOL_APPLY_WORKFLOW_ID = "strategy_pool_apply"
POOL_VALIDATION_WORKFLOW_ID = "strategy_pool_validation"
POOL_IMPACT_WORKFLOW_ID = "strategy_pool_impact"
IMPACT_CUBE_WORKFLOW_ID = "strategy_impact_cube"
POOL_STABILITY_WORKFLOW_ID = "strategy_pool_stability"

STRATEGY_TYPES = (
    "approval",
    "reject",
    "limit",
    "pricing",
    "segmentation",
)
_POOL_ACTION_TYPES = {
    "approval": frozenset({"approval", "reject", "review"}),
    "reject": frozenset({"approval", "reject", "review"}),
    "limit": frozenset({"limit"}),
    "pricing": frozenset({"pricing"}),
    "segmentation": frozenset({"segment"}),
}
_POOL_ADD_PLACEMENT_MODES = frozenset(
    {"before_selected_members", "replace_selected_members"}
)
_IMPACT_CUBE_PARTITION_ORDER = ("development", "validation", "oot")
_IMPACT_CUBE_ECONOMICS_COMPONENTS = {
    "approval": frozenset(
        {
            "ead",
            "pd",
            "annual_rate",
            "funding_rate",
            "lgd",
            "operating_cost_per_loan",
            "term_months",
        }
    ),
    "reject": frozenset(
        {
            "ead",
            "pd",
            "annual_rate",
            "funding_rate",
            "lgd",
            "operating_cost_per_loan",
            "term_months",
        }
    ),
    "limit": frozenset({"pd", "lgd", "utilization"}),
    "pricing": frozenset(
        {
            "ead",
            "pd",
            "lgd",
            "funding_rate",
            "term_months",
            "operating_cost_per_loan",
        }
    ),
    "segmentation": frozenset(),
}

_CANDIDATE_ASSET_ID_RE = re.compile(r"candidate-asset-[0-9a-f]{32}")
_POOL_SOURCE_ASSET_ID_RE = re.compile(
    r"(?:candidate-asset|interactive-tree|scorecard-band-asset)-[0-9a-f]{32}"
)
_SELECTION_ID_RE = re.compile(
    r"(?:automatic-tree-leaf-selection|"
    r"interactive-tree-frontier-group-selection|"
    r"interactive-tree-frontier-selection|"
    r"cross-matrix-cell-selection|"
    r"scorecard-cutoff-selection)-[0-9a-f]{32}"
)
_POOL_ITEM_ID_RE = re.compile(r"(?:candidate-rule|pool-entry)-[0-9a-f]{32}")
_CANDIDATE_RULE_ID_RE = re.compile(r"candidate-rule-[0-9a-f]{32}")
_POOL_APPLY_SAFE_PREFIX_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,47}")
_HASH_RE = re.compile(r"[0-9a-f]{64}")

_POOL_IDENTITY_FIELDS = frozenset(
    {"expected_pool_revision", "expected_pool_snapshot_hash"}
)
_ADD_EVIDENCE_FIELDS = _POOL_IDENTITY_FIELDS | frozenset(
    {
        "source_artifact_id",
        "expected_artifact_content_hash",
        "expected_asset_id",
        "expected_asset_hash",
        "placement_mode",
    }
)
_REMOVE_EVIDENCE_FIELDS = _POOL_IDENTITY_FIELDS | frozenset({"rule_id"})
_REORDER_EVIDENCE_FIELDS = _POOL_IDENTITY_FIELDS | frozenset({"ordered_rule_ids"})
_MATERIALIZE_EVIDENCE_FIELDS = frozenset(
    {
        "expected_pool_revision",
        "expected_pool_snapshot_hash",
        "expected_pool_artifact_id",
        "expected_pool_artifact_content_hash",
        "expected_design_hash",
    }
)
_VALIDATION_EVIDENCE_FIELDS = frozenset(
    {"pool_ref", "sample_design_ref", "population", "comparison_mode"}
)
_IMPACT_CUBE_EVIDENCE_FIELDS = frozenset(
    {
        "pool_ref",
        "sample_design_ref",
        "partitions",
        "population",
        "dimension_bindings",
        "current_strategy_ref",
        "economics_inputs",
    }
)
_STABILITY_EVIDENCE_FIELDS = frozenset({"pool_ref", "sample_design_ref", "partitions"})
_POOL_IMPACT_REQUIRED_EVIDENCE_FIELDS = frozenset(
    {
        "expected_pool_revision",
        "expected_pool_snapshot_hash",
        "dataset_id",
        "expected_dataset_content_hash",
        "workspace_revision",
        "workspace_generation",
        "semantic_mapping_hash",
        "target_col",
        "sample_design_ref",
        "drop_nan_labels",
    }
)
_POOL_IMPACT_OPTIONAL_EVIDENCE_FIELDS = frozenset(
    {"month_col", "loan_amount_col", "overdue_amount_col"}
)

_NO_REQUIREMENTS = StrategyWorkflowRequirements(False, False, False)
_IMPACT_REQUIREMENTS = StrategyWorkflowRequirements(True, True, True)


def validate_strategy_pool_add_candidate_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    return _validate_pool_control(POOL_ADD_WORKFLOW_ID, inputs)


def validate_strategy_pool_remove_entry_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    return _validate_pool_control(POOL_REMOVE_WORKFLOW_ID, inputs)


def validate_strategy_pool_set_action_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    return _validate_pool_control(POOL_SET_ACTION_WORKFLOW_ID, inputs)


def validate_strategy_pool_reorder_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    return _validate_pool_control(POOL_REORDER_WORKFLOW_ID, inputs)


def validate_strategy_pool_compile_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    return _validate_pool_control(POOL_COMPILE_WORKFLOW_ID, inputs)


def _validate_pool_control(
    workflow: str,
    inputs: Mapping[str, Any],
) -> dict[str, Any]:
    common = {"strategy_type", "reason"}
    allowed_by_workflow = {
        POOL_ADD_WORKFLOW_ID: common
        | {
            "candidate_asset_id",
            "selection_id",
            "default_action",
            "action",
            "placement_mode",
        },
        POOL_REMOVE_WORKFLOW_ID: common | {"rule_id", "entry_id"},
        POOL_SET_ACTION_WORKFLOW_ID: common | {"rule_id", "entry_id", "action"},
        POOL_REORDER_WORKFLOW_ID: common | {"ordered_ids"},
        POOL_COMPILE_WORKFLOW_ID: {"strategy_type"},
    }
    _reject_fields(inputs, allowed_by_workflow[workflow], workflow=workflow)
    strategy_type = _strategy_type(inputs, workflow=workflow)
    normalized: dict[str, Any] = {"strategy_type": strategy_type}

    if workflow == POOL_ADD_WORKFLOW_ID:
        missing = sorted({"default_action", "action"} - set(inputs))
        if missing:
            raise StrategyWorkflowValidationError(
                f"{workflow} Missing field:" + ",".join(missing) + ".",
                fields=missing,
            )
        source_fields = tuple(
            name for name in ("candidate_asset_id", "selection_id") if name in inputs
        )
        if len(source_fields) != 1:
            raise StrategyWorkflowValidationError(
                f"{workflow} It must and must becandidate_asset_id andselection_id One out of two.",
                fields=("candidate_asset_id", "selection_id"),
            )
        source_field = source_fields[0]
        source_id = _required_text(
            inputs[source_field], name=source_field, workflow=workflow
        )
        source_pattern = (
            _CANDIDATE_ASSET_ID_RE
            if source_field == "candidate_asset_id"
            else _SELECTION_ID_RE
        )
        if source_pattern.fullmatch(source_id) is None:
            if source_field == "candidate_asset_id":
                _invalid(
                    workflow,
                    "candidate_asset_id It has to be complete.candidate-asset id.",
                    source_field,
                )
            _invalid(
                workflow,
                "selection_id It must be.automatic-tree-leaf-selection- ,"
                "interactive-tree-frontier-group-selection-,"
                "interactive-tree-frontier-selection-,"
                "cross-matrix-cell-selection- or"
                "scorecard-cutoff-selection- is followed by 32-bit lowercase hexadecimal characters.",
                source_field,
            )
        normalized.update(
            {
                source_field: source_id,
                "default_action": _strategy_pool_action(
                    inputs["default_action"],
                    strategy_type=strategy_type,
                    name="default_action",
                    workflow=workflow,
                ),
                "action": _strategy_pool_action(
                    inputs["action"],
                    strategy_type=strategy_type,
                    name="action",
                    workflow=workflow,
                ),
            }
        )
        if "placement_mode" in inputs:
            placement = _required_text(
                inputs["placement_mode"],
                name="placement_mode",
                workflow=workflow,
            )
            if placement not in _POOL_ADD_PLACEMENT_MODES:
                _invalid(
                    workflow,
                    "placement_mode It's just...before_selected_members or"
                    "replace_selected_members.",
                    "placement_mode",
                )
            normalized["placement_mode"] = placement
    elif workflow in {POOL_REMOVE_WORKFLOW_ID, POOL_SET_ACTION_WORKFLOW_ID}:
        identifiers = [name for name in ("rule_id", "entry_id") if name in inputs]
        if len(identifiers) != 1:
            raise StrategyWorkflowValidationError(
                f"{workflow} It must and can only be providedrule_id orentry_id One.",
                fields=("rule_id", "entry_id"),
            )
        identifier_name = identifiers[0]
        normalized[identifier_name] = _pool_identifier(
            inputs[identifier_name],
            name=identifier_name,
            workflow=workflow,
        )
        if workflow == POOL_SET_ACTION_WORKFLOW_ID:
            if "action" not in inputs:
                _invalid(workflow, "Missingaction.", "action")
            normalized["action"] = _strategy_pool_action(
                inputs["action"],
                strategy_type=strategy_type,
                name="action",
                workflow=workflow,
            )
    elif workflow == POOL_REORDER_WORKFLOW_ID:
        if "ordered_ids" not in inputs:
            _invalid(workflow, "Missingordered_ids.", "ordered_ids")
        raw_order = inputs["ordered_ids"]
        if (
            not isinstance(raw_order, Sequence)
            or isinstance(raw_order, str | bytes | bytearray)
            or not 1 <= len(raw_order) <= 200
        ):
            _invalid(
                workflow,
                "ordered_ids Must be 1 to 200 completerule_id/entry_id.",
                "ordered_ids",
            )
        ordered_ids = [
            _pool_identifier(item, name="ordered_ids", workflow=workflow)
            for item in raw_order
        ]
        if len(set(ordered_ids)) != len(ordered_ids):
            _invalid(workflow, "ordered_ids No repetitions includedID.", "ordered_ids")
        normalized["ordered_ids"] = ordered_ids

    if workflow != POOL_COMPILE_WORKFLOW_ID and "reason" in inputs:
        reason = _required_text(inputs["reason"], name="reason", workflow=workflow)
        if len(reason) > 500:
            _invalid(workflow, "reason Maximum 500 characters.", "reason")
        normalized["reason"] = reason
    return normalized


def validate_strategy_pool_apply_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = POOL_APPLY_WORKFLOW_ID
    _reject_fields(inputs, {"strategy_type", "output_prefix"}, workflow=workflow)
    normalized: dict[str, Any] = {
        "strategy_type": _strategy_type(inputs, workflow=workflow)
    }
    if "output_prefix" in inputs:
        prefix = _required_text(
            inputs["output_prefix"], name="output_prefix", workflow=workflow
        )
        if _POOL_APPLY_SAFE_PREFIX_RE.fullmatch(prefix) is None:
            _invalid(
                workflow,
                "output_prefix Must be the maximum 48 charactersASCII identifier prefix,"
                "And not start with numbers.",
                "output_prefix",
            )
        normalized["output_prefix"] = prefix
    return normalized


def validate_strategy_pool_materialize_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = POOL_MATERIALIZE_WORKFLOW_ID
    _reject_fields(inputs, {"strategy_type"}, workflow=workflow)
    return {"strategy_type": _strategy_type(inputs, workflow=workflow)}


def validate_strategy_pool_validation_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = POOL_VALIDATION_WORKFLOW_ID
    _reject_fields(inputs, {"strategy_type", "partition"}, workflow=workflow)
    missing = [field for field in ("strategy_type", "partition") if field not in inputs]
    if missing:
        raise StrategyWorkflowValidationError(
            f"{workflow} Missing" + ",".join(missing) + ".",
            fields=missing,
        )
    strategy_type = _strategy_type(inputs, workflow=workflow)
    partition = _required_text(inputs["partition"], name="partition", workflow=workflow)
    if partition not in {"validation", "oot"}:
        _invalid(
            workflow,
            "partition It's just...validation oroot;development Not a stand-alone sample playback validation.",
            "partition",
        )
    return {"strategy_type": strategy_type, "partition": partition}


def validate_strategy_pool_stability_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = POOL_STABILITY_WORKFLOW_ID
    _reject_fields(inputs, {"strategy_type"}, workflow=workflow)
    return {"strategy_type": _strategy_type(inputs, workflow=workflow)}


def validate_strategy_pool_impact_inputs(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = POOL_IMPACT_WORKFLOW_ID
    allowed = {
        "strategy_type",
        "comparison_mode",
        "baseline_strategy_id",
        "month_col",
        "loan_amount_col",
        "overdue_amount_col",
        "drop_nan_labels",
    }
    _reject_fields(inputs, allowed, workflow=workflow)
    strategy_type = _strategy_type(inputs, workflow=workflow)
    if strategy_type not in {"approval", "reject"}:
        raise StrategyWorkflowValidationError(
            "strategy_pool_impact FirstV2 Even if only supportapproval orreject Pool;"
            "limit,pricing andsegmentation The impact calibration will be used to determine the impact of the current situation.V2 The following is a post-delivery report."
            "No access currently used/Rejected caliber.",
            fields=("strategy_type",),
        )
    comparison_mode = inputs.get("comparison_mode", "absolute")
    if not isinstance(comparison_mode, str) or comparison_mode not in {
        "absolute",
        "vs_baseline",
    }:
        _invalid(
            workflow,
            "comparison_mode It's just...absolute orvs_baseline.",
            "comparison_mode",
        )
    baseline_strategy_id = None
    if "baseline_strategy_id" in inputs:
        baseline_strategy_id = _required_text(
            inputs["baseline_strategy_id"],
            name="baseline_strategy_id",
            workflow=workflow,
        )
    if comparison_mode == "vs_baseline" and baseline_strategy_id is None:
        _invalid(
            workflow,
            "Usevs_baseline It must be provided from time to timebaseline_strategy_id.",
            "baseline_strategy_id",
        )
    if comparison_mode == "absolute" and baseline_strategy_id is not None:
        _invalid(
            workflow,
            "Useabsolute It's forbidden to supplybaseline_strategy_id.",
            "baseline_strategy_id",
        )
    normalized: dict[str, Any] = {
        "strategy_type": strategy_type,
        "comparison_mode": comparison_mode,
    }
    if baseline_strategy_id is not None:
        normalized["baseline_strategy_id"] = baseline_strategy_id
    for field in ("month_col", "loan_amount_col", "overdue_amount_col"):
        if field in inputs:
            normalized[field] = _column(
                inputs[field],
                name=field,
                workflow=workflow,
                whitelist=context.allowed_columns,
            )
    drop_nan_labels = inputs.get("drop_nan_labels", False)
    if not isinstance(drop_nan_labels, bool):
        _invalid(
            workflow,
            "drop_nan_labels Must be a boolean value.",
            "drop_nan_labels",
        )
    normalized["drop_nan_labels"] = drop_nan_labels
    return normalized


def validate_strategy_impact_cube_inputs(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = IMPACT_CUBE_WORKFLOW_ID
    allowed = {
        "strategy_type",
        "partitions",
        "month_col",
        "group_col",
        "segment_col",
        "current_strategy_id",
        "economics_inputs",
    }
    _reject_fields(inputs, allowed, workflow=workflow)
    strategy_type = _strategy_type(inputs, workflow=workflow)
    normalized: dict[str, Any] = {"strategy_type": strategy_type}

    if "partitions" in inputs:
        raw_partitions = inputs["partitions"]
        if (
            not isinstance(raw_partitions, Sequence)
            or isinstance(raw_partitions, str | bytes | bytearray)
            or not 1 <= len(raw_partitions) <= len(_IMPACT_CUBE_PARTITION_ORDER)
        ):
            _invalid(
                workflow,
                "partitions Must be one to three clear partitions.",
                "partitions",
            )
        partitions = [
            _required_text(item, name="partitions", workflow=workflow)
            for item in raw_partitions
        ]
        if len(set(partitions)) != len(partitions) or any(
            item not in _IMPACT_CUBE_PARTITION_ORDER for item in partitions
        ):
            _invalid(
                workflow,
                "partitions It can only be used without repetition.development,validation,oot.",
                "partitions",
            )
        normalized["partitions"] = [
            item for item in _IMPACT_CUBE_PARTITION_ORDER if item in partitions
        ]

    dimension_columns: list[str] = []
    for field in ("month_col", "group_col", "segment_col"):
        if field not in inputs:
            continue
        column = _column(
            inputs[field],
            name=field,
            workflow=workflow,
            whitelist=context.allowed_columns,
        )
        normalized[field] = column
        dimension_columns.append(column)
    if len(dimension_columns) != len(set(dimension_columns)):
        raise StrategyWorkflowValidationError(
            f"{workflow} month/group/segment A different column must be bound.",
            fields=("month_col", "group_col", "segment_col"),
        )

    if "current_strategy_id" in inputs:
        normalized["current_strategy_id"] = _required_text(
            inputs["current_strategy_id"],
            name="current_strategy_id",
            workflow=workflow,
        )

    if "economics_inputs" in inputs and inputs["economics_inputs"] is not None:
        raw_economics = inputs["economics_inputs"]
        if (
            not isinstance(raw_economics, Mapping)
            or not 1 <= len(raw_economics) <= 16
            or any(not isinstance(key, str) for key in raw_economics)
        ):
            _invalid(
                workflow,
                "economics_inputs Must be 1 to 16typed bindings.",
                "economics_inputs",
            )
        unsupported = sorted(
            set(raw_economics) - _IMPACT_CUBE_ECONOMICS_COMPONENTS[strategy_type]
        )
        if unsupported:
            raise StrategyWorkflowValidationError(
                f"{workflow} {strategy_type} Not supportedeconomics_inputs:"
                + ",".join(unsupported)
                + ".",
                fields=("economics_inputs",),
            )
        economics: dict[str, dict[str, Any]] = {}
        for component in sorted(raw_economics):
            binding = raw_economics[component]
            if not isinstance(binding, Mapping):
                _invalid(
                    workflow,
                    f"economics_inputs.{component} It must be.typed binding.",
                    "economics_inputs",
                )
            kind = binding.get("kind")
            if kind == "column" and set(binding) == {"kind", "column"}:
                economics[component] = {
                    "kind": "column",
                    "column": _column(
                        binding["column"],
                        name=f"economics_inputs.{component}.column",
                        workflow=workflow,
                        whitelist=context.allowed_columns,
                    ),
                }
            elif kind == "scalar" and set(binding) == {"kind", "value"}:
                value = binding["value"]
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int | float)
                    or not math.isfinite(float(value))
                    or (isinstance(value, int) and abs(value) > 2**53 - 1)
                ):
                    _invalid(
                        workflow,
                        f"economics_inputs.{component}.value Figures must be limited and precise.",
                        "economics_inputs",
                    )
                if component == "term_months" and (
                    not isinstance(value, int) or value < 1
                ):
                    _invalid(
                        workflow,
                        "economics_inputs.term_months Must be the number of months in whole.",
                        "economics_inputs",
                    )
                economics[component] = {"kind": "scalar", "value": value}
            else:
                _invalid(
                    workflow,
                    f"economics_inputs.{component} It's just...column orscalar binding.",
                    "economics_inputs",
                )
        normalized["economics_inputs"] = economics
    return normalized


def strategy_pool_add_candidate_confirmation(inputs: Mapping[str, Any]) -> str:
    source_field = "selection_id" if "selection_id" in inputs else "candidate_asset_id"
    source_label = "Selecting results precisely" if source_field == "selection_id" else "Candidate assets"
    details = [
        "Recognized as [ ]Strategy Pool Add CandidateWorkflow〕",
        f"{source_label}:{inputs[source_field]}",
        f"Policy type:{inputs['strategy_type']}",
        "Default action:" + _compact_json(inputs["default_action"]),
        "Hit action:" + _compact_json(inputs["action"]),
        "Platform will be from the currenttask ♪ The unchanging ♪artifact Tiehash,rule/effect/metrics,"
        "And show it.development / unvalidated Automatically write reversible after evidencedraft Pool revision",
        "This operation only changesdraft Pool,No strategy will be adopted or deployed",
    ]
    if "reason" in inputs:
        details.append(f"Operational description:{inputs['reason']}")
    if "placement_mode" in inputs:
        details.append(f"Voting Members placed:{inputs['placement_mode']}")
    return _confirmation(details)


def strategy_pool_remove_entry_confirmation(inputs: Mapping[str, Any]) -> str:
    return _pool_item_mutation_confirmation(
        inputs,
        workflow_label="Delete Entry",
    )


def strategy_pool_set_action_confirmation(inputs: Mapping[str, Any]) -> str:
    return _pool_item_mutation_confirmation(
        inputs,
        workflow_label="Modify Action",
    )


def _pool_item_mutation_confirmation(
    inputs: Mapping[str, Any],
    *,
    workflow_label: str,
) -> str:
    identifier_name = "rule_id" if "rule_id" in inputs else "entry_id"
    details = [
        f"Recognized as [ ]Strategy Pool {workflow_label} Workflow〕",
        f"Policy type:{inputs['strategy_type']}",
        f"Objective{identifier_name}:{inputs[identifier_name]}",
        "Platform will be fromtask CurrentPool Parsing and binding the full entryrevision/hash,Oldrevision Keep it unchanged.",
        "This operation will not adopt or deploy a strategy.",
    ]
    if "action" in inputs:
        details.append("New action:" + _compact_json(inputs["action"]))
    if "reason" in inputs:
        details.append(f"Operational description:{inputs['reason']}")
    return _confirmation(details)


def strategy_pool_reorder_confirmation(inputs: Mapping[str, Any]) -> str:
    details = [
        "Recognized as [ ]Strategy Pool Full ReorderWorkflow〕",
        f"Policy type:{inputs['strategy_type']}",
        "Full order:" + " → ".join(inputs["ordered_ids"]),
        "The platform will check the list with the currentPool is the same set of non-repeated entries; omissions will not be considered deleted",
        "Oldrevision Keep it unchanged. This operation will not adopt or deploy a strategy.",
    ]
    if "reason" in inputs:
        details.append(f"Operational description:{inputs['reason']}")
    return _confirmation(details)


def strategy_pool_compile_confirmation(inputs: Mapping[str, Any]) -> str:
    return _confirmation(
        [
            "Recognized as [ ]Strategy Pool Compile PreviewWorkflow〕",
            f"Policy type:{inputs['strategy_type']}",
            "Platform read-only compiles the currenttask Pool Yescanonical StrategySpec And calculatedesign hash",
            "The result is a preview of the draft, which does not create the adopted strategy, nor does it adopt or deploy",
        ]
    )


def strategy_pool_materialize_confirmation(inputs: Mapping[str, Any]) -> str:
    return _confirmation(
        [
            "Recognized as [ ]Strategy Pool Physicalizationdraft Strategy Workflow〕",
            f"Policy type:{inputs['strategy_type']}",
            "Platform will fully authenticate current non-empty when planned to be createdPool,And freezerevision,snapshot,"
            "artifact anddesign hash",
            "This step only creates or accurately reuses for durabilitydraft Strategy;I don't want to be in the same position."
            "Follow-up check,DSL Delivery, adoption and monitoring remain subject to the respective evidence and life-cycle door limitations",
        ]
    )


def strategy_pool_apply_confirmation(inputs: Mapping[str, Any]) -> str:
    return _confirmation(
        [
            "Recognized as [ ]Strategy Pool Apply WritebackWorkflow〕",
            f"Policy type:{inputs['strategy_type']}",
            "Platform will authenticate the current at the time of implementationtask Only non-empty for the specified typePool,CAS revision/hash,"
            "Source sample andrequirements,Re-specify line-by-line application",
            "This step only creates non-variable datasets that keep the original rows; no active or replacement of the currentworkspace,"
            "No, no, no, no, no.Pool",
            "Output prefix:"
            + (
                str(inputs["output_prefix"])
                if "output_prefix" in inputs
                else "ControlledTool Use default prefix"
            ),
        ]
    )


def strategy_pool_validation_confirmation(inputs: Mapping[str, Any]) -> str:
    return _confirmation(
        [
            "Recognized as [ ]Strategy Pool Independent sample playback validationWorkflow〕",
            f"Policy type:{inputs['strategy_type']}",
            f"Independent sample partition:{inputs['partition']}",
            "Platform will resume current non-empty when plannedPool,Exact and mature."
            "StrategySampleDesign V2 membership/bundle,Data/Objective/Semantics and"
            " requirements,And by certaintyTool Re-accreditation",
            "And the result is...independent replay evidence:Approval/Refuse to show actions, risks,"
            "Amount and monthly evidence, amount/Pricing/(b) Retaining primary values or group distributions in groups;"
            "No claim.PSI,Stability or drift",
            "This step will not be modifiedPool,No strategy created, no promotions, no adoptions, no deployments",
        ]
    )


def strategy_pool_stability_confirmation(inputs: Mapping[str, Any]) -> str:
    return _confirmation(
        [
            "Recognized as [ ]Strategy Pool Cross-divisional stabilityWorkflow〕",
            f"Policy type:{inputs['strategy_type']}",
            "Platform will freeze current non-empty at planned creationPool,The latest certified and mature risk results"
            "StrategySampleDesign V2,anddevelopment and all available non-empty"
            "validation/OOT Division",
            "Agent Yes, sir.exact ImpactCube,And then you can quote four exact outputs of this step."
            "Directly to certaintyTool Calculatewaterfall/action DistributionPSI",
            "The result is only a stable distribution across divisions, not equivalent to independent validation of effects; no changesPool,"
            "Create strategy, no adoption, no promotion, no deployment",
        ]
    )


def strategy_impact_cube_confirmation(inputs: Mapping[str, Any]) -> str:
    details = [
        "Recognized as [Uniform]Strategy ImpactCube Workflow〕",
        f"Policy type:{inputs['strategy_type']}",
        "Platform will bind the current non-emptyPool,Latest authenticationStrategySampleDesign V2,"
        "Data/Semantic versions and user clear controls to calculate five types of typologies for certainty",
        "Division:"
        + (
            ",".join(inputs["partitions"])
            if "partitions" in inputs
            else "All available and non-emptydevelopment/validation/OOT"
        ),
        "Month by Month/Group/When the cluster is not provided in a visible manner, only the only semantic role identified is used;"
        "The cut when missingunavailable,Clarification in case of conflict",
        "Results are issued only as aggregated, downloadable and reversible evidence; no changesPool,Create, adopt, promote or deploy strategies",
    ]
    for field, label in (
        ("month_col", "Month"),
        ("group_col", "Group Columns"),
        ("segment_col", "Grouping"),
    ):
        if field in inputs:
            details.append(f"{label}:{inputs[field]}")
    if "current_strategy_id" in inputs:
        details.append(f"Current PolicyID:{inputs['current_strategy_id']}")
    if "economics_inputs" in inputs:
        details.append("Economic caliber:" + _compact_json(inputs["economics_inputs"]))
    return _confirmation(details)


def strategy_pool_impact_confirmation(inputs: Mapping[str, Any]) -> str:
    mode_label = (
        "Relative baseline" if inputs["comparison_mode"] == "vs_baseline" else "Absolute effect"
    )
    details = [
        "Recognized as [ ]Strategy Pool Impact measurementWorkflow〕",
        f"Policy type:{inputs['strategy_type']}",
        f"Comparative caliber:{mode_label}",
        "Platform will bind the current non-emptyPool,ActivitiesDataWorkspace,Datahash,"
        "Confirmed target column and semantic version, definitive calculation cascadewaterfall and risk impact",
        "Month/Amount released/The late amount list is provided without a visible provision, only with the only semantic role recognized;"
        "No character, no result.unavailable,Multiple roles will clarify first.",
        "This step generates downloadable only read-only evidence; no strategy will be created, modified, adopted or deployed",
    ]
    if "baseline_strategy_id" in inputs:
        details.append(f"Baseline strategyID:{inputs['baseline_strategy_id']}")
    for field, label in (
        ("month_col", "Month"),
        ("loan_amount_col", "Lending amount line"),
        ("overdue_amount_col", "Overdue Amount Column"),
    ):
        if field in inputs:
            details.append(f"{label}:{inputs[field]}")
    details.append(
        "Empty tag processing:"
        + (
            "User expressly allows the retention of sample lines, except from the risk denominator"
            if inputs["drop_nan_labels"]
            else "Do not default to exclude from the risk denominator"
        )
    )
    return _confirmation(details)


def prepare_strategy_pool_add_candidate(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    canonical = {
        field: deep_thaw(deep_freeze(inputs[field]))
        for field in ("strategy_type", "default_action", "action", "reason")
        if field in inputs
    }
    evidence = _workflow_evidence(
        POOL_ADD_WORKFLOW_ID,
        inputs,
        context,
        canonical,
        required_fields=_ADD_EVIDENCE_FIELDS,
    )
    _validate_pool_identity(POOL_ADD_WORKFLOW_ID, evidence, minimum_revision=0)
    _validate_artifact_identity(POOL_ADD_WORKFLOW_ID, evidence)
    placement = evidence["placement_mode"]
    if placement not in {"append", *_POOL_ADD_PLACEMENT_MODES}:
        _evidence_invalid(
            POOL_ADD_WORKFLOW_ID,
            "placement_mode Invalid.",
            "placement_mode",
        )
    requested_placement = inputs.get("placement_mode")
    if requested_placement is not None and placement != requested_placement:
        _evidence_conflict(
            POOL_ADD_WORKFLOW_ID,
            "The platform tied up.placement_mode Not consistent with user selection.",
            "placement_mode",
        )
    if (
        requested_placement is None
        and "selection_id" in inputs
        and placement != "append"
    ):
        _evidence_conflict(
            POOL_ADD_WORKFLOW_ID,
            "NotVoting selection Only useappend Place semantics.",
            "placement_mode",
        )
    if (
        "candidate_asset_id" in inputs
        and evidence["expected_asset_id"] != inputs["candidate_asset_id"]
    ):
        _evidence_conflict(
            POOL_ADD_WORKFLOW_ID,
            "Platform evidence does not bind the user to a specific choicecandidate_asset_id.",
            "candidate_asset_id",
            "expected_asset_id",
        )
    return _prepared(POOL_ADD_WORKFLOW_ID, {**canonical, **evidence})


def prepare_strategy_pool_remove_entry(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    return _prepare_pool_item_mutation(
        POOL_REMOVE_WORKFLOW_ID,
        inputs,
        context,
        include_action=False,
    )


def prepare_strategy_pool_set_action(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    return _prepare_pool_item_mutation(
        POOL_SET_ACTION_WORKFLOW_ID,
        inputs,
        context,
        include_action=True,
    )


def _prepare_pool_item_mutation(
    workflow_id: str,
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
    *,
    include_action: bool,
) -> PreparedStrategyPlan:
    fields = ["strategy_type", "reason"]
    if include_action:
        fields.append("action")
    canonical = {
        field: deep_thaw(deep_freeze(inputs[field]))
        for field in fields
        if field in inputs
    }
    evidence = _workflow_evidence(
        workflow_id,
        inputs,
        context,
        canonical,
        required_fields=_REMOVE_EVIDENCE_FIELDS,
    )
    _validate_pool_identity(workflow_id, evidence, minimum_revision=1)
    rule_id = evidence["rule_id"]
    if not isinstance(rule_id, str) or _CANDIDATE_RULE_ID_RE.fullmatch(rule_id) is None:
        _evidence_invalid(workflow_id, "rule_id Invalid.", "rule_id")
    if "rule_id" in inputs and rule_id != inputs["rule_id"]:
        _evidence_conflict(
            workflow_id,
            "The platform tied up.rule_id With Userspointer Inconsistent.",
            "rule_id",
        )
    return _prepared(workflow_id, {**canonical, **evidence})


def prepare_strategy_pool_reorder(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    canonical = {
        field: inputs[field] for field in ("strategy_type", "reason") if field in inputs
    }
    evidence = _workflow_evidence(
        POOL_REORDER_WORKFLOW_ID,
        inputs,
        context,
        canonical,
        required_fields=_REORDER_EVIDENCE_FIELDS,
    )
    _validate_pool_identity(POOL_REORDER_WORKFLOW_ID, evidence, minimum_revision=1)
    ordered_rule_ids = evidence["ordered_rule_ids"]
    if (
        not isinstance(ordered_rule_ids, Sequence)
        or isinstance(ordered_rule_ids, str | bytes | bytearray)
        or not 1 <= len(ordered_rule_ids) <= 200
        or any(
            not isinstance(rule_id, str)
            or _CANDIDATE_RULE_ID_RE.fullmatch(rule_id) is None
            for rule_id in ordered_rule_ids
        )
        or len(set(ordered_rule_ids)) != len(ordered_rule_ids)
    ):
        _evidence_invalid(
            POOL_REORDER_WORKFLOW_ID,
            "ordered_rule_ids Must be complete, the only, the currently desolvedPool rule Order.",
            "ordered_rule_ids",
        )
    return _prepared(POOL_REORDER_WORKFLOW_ID, {**canonical, **evidence})


def prepare_strategy_pool_compile(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    canonical = {"strategy_type": inputs["strategy_type"]}
    evidence = _workflow_evidence(
        POOL_COMPILE_WORKFLOW_ID,
        inputs,
        context,
        canonical,
        required_fields=_POOL_IDENTITY_FIELDS,
    )
    _validate_pool_identity(POOL_COMPILE_WORKFLOW_ID, evidence, minimum_revision=1)
    return _prepared(POOL_COMPILE_WORKFLOW_ID, {**canonical, **evidence})


def prepare_strategy_pool_materialize(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    canonical = {"strategy_type": inputs["strategy_type"]}
    evidence = _workflow_evidence(
        POOL_MATERIALIZE_WORKFLOW_ID,
        inputs,
        context,
        canonical,
        required_fields=_MATERIALIZE_EVIDENCE_FIELDS,
    )
    _validate_pool_identity(
        POOL_MATERIALIZE_WORKFLOW_ID,
        evidence,
        minimum_revision=1,
    )
    for field in (
        "expected_pool_artifact_id",
        "expected_pool_artifact_content_hash",
        "expected_design_hash",
    ):
        if (
            not isinstance(evidence[field], str)
            or _HASH_RE.fullmatch(evidence[field]) is None
        ):
            _evidence_invalid(
                POOL_MATERIALIZE_WORKFLOW_ID,
                f"{field} It must be complete 64-bit Hashi.",
                field,
            )
    return _prepared(POOL_MATERIALIZE_WORKFLOW_ID, {**canonical, **evidence})


def prepare_strategy_pool_apply(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    canonical = deep_thaw(deep_freeze(inputs))
    assert isinstance(canonical, dict)
    evidence = _workflow_evidence(
        POOL_APPLY_WORKFLOW_ID,
        inputs,
        context,
        canonical,
        required_fields=_POOL_IDENTITY_FIELDS,
    )
    _validate_pool_identity(POOL_APPLY_WORKFLOW_ID, evidence, minimum_revision=1)
    return _prepared(POOL_APPLY_WORKFLOW_ID, {**canonical, **evidence})


def prepare_strategy_pool_validation(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    canonical = deep_thaw(deep_freeze(inputs))
    assert isinstance(canonical, dict)
    evidence = _workflow_evidence(
        POOL_VALIDATION_WORKFLOW_ID,
        inputs,
        context,
        canonical,
        required_fields=_VALIDATION_EVIDENCE_FIELDS,
    )
    _validate_pool_and_v2_sample_refs(POOL_VALIDATION_WORKFLOW_ID, evidence)
    if evidence["population"] != "risk" or evidence["comparison_mode"] != "absolute":
        _evidence_invalid(
            POOL_VALIDATION_WORKFLOW_ID,
            "population/comparison_mode It must be fixed.risk/absolute.",
            "population",
            "comparison_mode",
        )
    return _prepared(POOL_VALIDATION_WORKFLOW_ID, {**canonical, **evidence})


def prepare_strategy_pool_impact(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    if not isinstance(context.dataset_id, str) or not context.dataset_id.strip():
        raise StrategyWorkflowValidationError(
            "Strategy Pool Impact measurement requires activityDataWorkspace dataset_id.",
            code="strategy_workflow_dataset_binding_required",
            fields=("dataset_id",),
        )
    canonical = {
        field: deep_thaw(deep_freeze(inputs[field]))
        for field in ("strategy_type", "comparison_mode", "baseline_strategy_id")
        if field in inputs
    }
    evidence = _workflow_evidence(
        POOL_IMPACT_WORKFLOW_ID,
        inputs,
        context,
        canonical,
        required_fields=_POOL_IMPACT_REQUIRED_EVIDENCE_FIELDS,
        optional_fields=_POOL_IMPACT_OPTIONAL_EVIDENCE_FIELDS,
    )
    _validate_pool_identity(POOL_IMPACT_WORKFLOW_ID, evidence, minimum_revision=1)
    if evidence["dataset_id"] != context.dataset_id:
        _evidence_conflict(
            POOL_IMPACT_WORKFLOW_ID,
            "Platform evidencedataset_id This is not consistent with the current context of the preparation.",
            "dataset_id",
        )
    for field in (
        "dataset_id",
        "expected_dataset_content_hash",
        "semantic_mapping_hash",
        "target_col",
    ):
        if not isinstance(evidence[field], str) or not evidence[field].strip():
            _evidence_invalid(
                POOL_IMPACT_WORKFLOW_ID,
                f"{field} It must be a non-empty platform identity.",
                field,
            )
    for field in ("workspace_revision", "workspace_generation"):
        value = evidence[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _evidence_invalid(
                POOL_IMPACT_WORKFLOW_ID,
                f"{field} Must be a non-negative integer.",
                field,
            )
    if evidence["drop_nan_labels"] is not context.drop_nan_labels:
        _evidence_conflict(
            POOL_IMPACT_WORKFLOW_ID,
            "Platform evidencedrop_nan_labels This is not consistent with the confirmed label calibre.",
            "drop_nan_labels",
        )
    _validate_legacy_sample_ref(
        POOL_IMPACT_WORKFLOW_ID,
        evidence["sample_design_ref"],
    )
    for field in _POOL_IMPACT_OPTIONAL_EVIDENCE_FIELDS:
        if field in evidence:
            value = evidence[field]
            if not isinstance(value, str) or not value.strip():
                _evidence_invalid(
                    POOL_IMPACT_WORKFLOW_ID,
                    f"{field} Must be a non-empty authentication field.",
                    field,
                )
            if field in inputs and value != inputs[field]:
                _evidence_conflict(
                    POOL_IMPACT_WORKFLOW_ID,
                    f"The platform tied up.{field} Not consistent with user-specific fields.",
                    field,
                )
        elif field in inputs:
            _evidence_conflict(
                POOL_IMPACT_WORKFLOW_ID,
                f"Platform evidence missing user-specific fields{field}.",
                field,
            )
    return _prepared(POOL_IMPACT_WORKFLOW_ID, {**canonical, **evidence})


def prepare_strategy_impact_cube(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    canonical = {"strategy_type": inputs["strategy_type"]}
    evidence = _workflow_evidence(
        IMPACT_CUBE_WORKFLOW_ID,
        inputs,
        context,
        canonical,
        required_fields=_IMPACT_CUBE_EVIDENCE_FIELDS,
    )
    _validate_pool_and_v2_sample_refs(IMPACT_CUBE_WORKFLOW_ID, evidence)
    if evidence["population"] != "risk":
        _evidence_invalid(
            IMPACT_CUBE_WORKFLOW_ID,
            "population It must be fixed.risk.",
            "population",
        )
    partitions = _validated_evidence_partitions(
        IMPACT_CUBE_WORKFLOW_ID,
        evidence["partitions"],
    )
    if "partitions" in inputs and partitions != list(inputs["partitions"]):
        _evidence_conflict(
            IMPACT_CUBE_WORKFLOW_ID,
            "The platform ' s partitioning does not coincide with the user ' s clear partitioning.",
            "partitions",
        )
    dimensions = evidence["dimension_bindings"]
    if not isinstance(dimensions, Mapping) or set(dimensions) != {
        "month_col",
        "group_col",
        "segment_col",
    }:
        _evidence_invalid(
            IMPACT_CUBE_WORKFLOW_ID,
            "dimension_bindings Must contain preciselymonth/group/segment.",
            "dimension_bindings",
        )
    nonnull_dimensions = []
    for field, value in dimensions.items():
        if value is not None and (not isinstance(value, str) or not value.strip()):
            _evidence_invalid(
                IMPACT_CUBE_WORKFLOW_ID,
                f"dimension_bindings.{field} Must be non-empty field names ornull.",
                "dimension_bindings",
            )
        if value is not None:
            nonnull_dimensions.append(value)
        if field in inputs and value != inputs[field]:
            _evidence_conflict(
                IMPACT_CUBE_WORKFLOW_ID,
                f"The platform tied up.{field} Not consistent with user-specific fields.",
                field,
            )
    if len(nonnull_dimensions) != len(set(nonnull_dimensions)):
        _evidence_invalid(
            IMPACT_CUBE_WORKFLOW_ID,
            "dimension_bindings Fields cannot be used again.",
            "dimension_bindings",
        )

    current_ref = evidence["current_strategy_ref"]
    if "current_strategy_id" in inputs:
        if (
            not isinstance(current_ref, Mapping)
            or current_ref.get("strategy_id") != inputs["current_strategy_id"]
            or set(current_ref) != {"strategy_id", "expected_strategy_spec_hash"}
            or not isinstance(current_ref.get("expected_strategy_spec_hash"), str)
            or _HASH_RE.fullmatch(current_ref["expected_strategy_spec_hash"]) is None
        ):
            _evidence_conflict(
                IMPACT_CUBE_WORKFLOW_ID,
                "Current policy reference does not precisely bind the usercurrent_strategy_id.",
                "current_strategy_id",
                "current_strategy_ref",
            )
    elif current_ref is not None:
        _evidence_invalid(
            IMPACT_CUBE_WORKFLOW_ID,
            "When the user does not request the current policy comparisoncurrent_strategy_ref I must.null.",
            "current_strategy_ref",
        )

    economics = evidence["economics_inputs"]
    expected_economics = inputs.get("economics_inputs")
    if economics != expected_economics:
        _evidence_conflict(
            IMPACT_CUBE_WORKFLOW_ID,
            "Platform economics andcanonical economics_inputs Inconsistent.",
            "economics_inputs",
        )
    return _prepared(IMPACT_CUBE_WORKFLOW_ID, {**canonical, **evidence})


def prepare_strategy_pool_stability(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    canonical = {"strategy_type": inputs["strategy_type"]}
    evidence = _workflow_evidence(
        POOL_STABILITY_WORKFLOW_ID,
        inputs,
        context,
        canonical,
        required_fields=_STABILITY_EVIDENCE_FIELDS,
    )
    _validate_pool_and_v2_sample_refs(POOL_STABILITY_WORKFLOW_ID, evidence)
    partitions = _validated_evidence_partitions(
        POOL_STABILITY_WORKFLOW_ID,
        evidence["partitions"],
    )
    if "development" not in partitions or not any(
        partition in partitions for partition in ("validation", "oot")
    ):
        _evidence_invalid(
            POOL_STABILITY_WORKFLOW_ID,
            "Cross-divisional stability needsdevelopment And at least one.validation/OOT Division.",
            "partitions",
        )
    return _prepared(POOL_STABILITY_WORKFLOW_ID, {**canonical, **evidence})


def _workflow_evidence(
    workflow_id: str,
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
    canonical_slots: Mapping[str, Any],
    *,
    required_fields: frozenset[str],
    optional_fields: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    binder = context.bind_workflow_evidence
    if binder is None:
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Evidence bound for lack of Platform authentication.",
            code="strategy_workflow_evidence_binding_required",
        )
    evidence = binder(workflow_id, deep_freeze(deep_thaw(inputs)))
    if not isinstance(evidence, Mapping):
        raise StrategyWorkflowValidationError(
            f"{workflow_id} The Platform evidence binds must return to the object.",
            code="strategy_workflow_evidence_invalid",
        )
    if any(not isinstance(key, str) for key in evidence):
        raise StrategyWorkflowValidationError(
            f"{workflow_id} The name of the Platform evidence bound field must be text.",
            code="strategy_workflow_evidence_invalid",
        )
    conflicts = sorted(set(evidence) & set(canonical_slots))
    if conflicts:
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Platform evidence cannot be overwrittencanonical slots:"
            + ",".join(conflicts)
            + ".",
            code="strategy_workflow_evidence_conflict",
            fields=conflicts,
        )
    actual = frozenset(evidence)
    missing = sorted(required_fields - actual)
    unexpected = sorted(actual - required_fields - optional_fields)
    if missing or unexpected:
        details = []
        if missing:
            details.append("Missing" + ",".join(missing))
        if unexpected:
            details.append("Include unauthorized fields" + ",".join(unexpected))
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Platform evidenceschema Invalid:" + ";".join(details) + ".",
            code="strategy_workflow_evidence_invalid",
            fields=(*missing, *unexpected),
        )
    if not _mapping_keys_are_text(evidence):
        raise StrategyWorkflowValidationError(
            f"{workflow_id} The platform evidence embedded field name must be text.",
            code="strategy_workflow_evidence_invalid",
        )
    copied = deep_thaw(deep_freeze(evidence))
    if not isinstance(copied, dict):  # pragma: no cover - Mapping guarded above
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Platform evidence binds cannot be copied.",
            code="strategy_workflow_evidence_invalid",
        )
    return copied


def _validate_pool_identity(
    workflow_id: str,
    evidence: Mapping[str, Any],
    *,
    minimum_revision: int,
) -> None:
    revision = evidence["expected_pool_revision"]
    snapshot_hash = evidence["expected_pool_snapshot_hash"]
    if (
        isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision < minimum_revision
    ):
        _evidence_invalid(
            workflow_id,
            f"expected_pool_revision Must be no less than{minimum_revision} .",
            "expected_pool_revision",
        )
    if not isinstance(snapshot_hash, str) or _HASH_RE.fullmatch(snapshot_hash) is None:
        _evidence_invalid(
            workflow_id,
            "expected_pool_snapshot_hash Must be complete 64 bits of Hashi.",
            "expected_pool_snapshot_hash",
        )


def _validate_artifact_identity(
    workflow_id: str,
    evidence: Mapping[str, Any],
) -> None:
    artifact_id = evidence["source_artifact_id"]
    asset_id = evidence["expected_asset_id"]
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        _evidence_invalid(
            workflow_id,
            "source_artifact_id It must be a non-empty platform quote.",
            "source_artifact_id",
        )
    if (
        not isinstance(asset_id, str)
        or _POOL_SOURCE_ASSET_ID_RE.fullmatch(asset_id) is None
    ):
        _evidence_invalid(
            workflow_id,
            "expected_asset_id It has to be complete, supported.Pool source asset ID.",
            "expected_asset_id",
        )
    for field in ("expected_artifact_content_hash", "expected_asset_hash"):
        value = evidence[field]
        if not isinstance(value, str) or _HASH_RE.fullmatch(value) is None:
            _evidence_invalid(
                workflow_id,
                f"{field} Must be complete 64 bits of Hashi.",
                field,
            )


def _validate_pool_and_v2_sample_refs(
    workflow_id: str,
    evidence: Mapping[str, Any],
) -> None:
    pool_ref = evidence["pool_ref"]
    if not isinstance(pool_ref, Mapping) or set(pool_ref) != {
        "artifact_id",
        "expected_artifact_content_hash",
        "expected_pool_id",
        "expected_revision",
        "expected_revision_id",
        "expected_snapshot_hash",
    }:
        _evidence_invalid(
            workflow_id,
            "pool_ref It has to be complete and precise.Pool Reference.",
            "pool_ref",
        )
    revision = pool_ref["expected_revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        _evidence_invalid(
            workflow_id,
            "pool_ref.expected_revision Must be positive integers.",
            "pool_ref",
        )
    for field in (
        "artifact_id",
        "expected_artifact_content_hash",
        "expected_pool_id",
        "expected_revision_id",
        "expected_snapshot_hash",
    ):
        if not isinstance(pool_ref[field], str) or not pool_ref[field].strip():
            _evidence_invalid(
                workflow_id,
                f"pool_ref.{field} It must be non-empty.",
                "pool_ref",
            )
    sample_ref = evidence["sample_design_ref"]
    expected_sample_fields = {
        "membership_artifact_id",
        "expected_membership_artifact_content_hash",
        "bundle_artifact_id",
        "expected_bundle_artifact_content_hash",
        "expected_bundle_id",
        "expected_sample_design_id",
        "expected_sample_design_content_hash",
    }
    if not isinstance(sample_ref, Mapping) or set(sample_ref) != expected_sample_fields:
        _evidence_invalid(
            workflow_id,
            "sample_design_ref It has to be complete.V2 membership/bundle Reference.",
            "sample_design_ref",
        )
    if any(
        not isinstance(sample_ref[field], str) or not sample_ref[field].strip()
        for field in expected_sample_fields
    ):
        _evidence_invalid(
            workflow_id,
            "sample_design_ref All identification fields must be non-empty.",
            "sample_design_ref",
        )


def _validate_legacy_sample_ref(workflow_id: str, value: object) -> None:
    expected_fields = {
        "artifact_id",
        "artifact_content_hash",
        "sample_design_id",
        "sample_design_content_hash",
        "partition",
    }
    if not isinstance(value, Mapping) or set(value) != expected_fields:
        _evidence_invalid(
            workflow_id,
            "sample_design_ref It has to be complete.development SampleDesign Reference.",
            "sample_design_ref",
        )
    if any(
        not isinstance(value[field], str) or not value[field].strip()
        for field in expected_fields
    ):
        _evidence_invalid(
            workflow_id,
            "sample_design_ref All identification fields must be non-empty.",
            "sample_design_ref",
        )


def _validated_evidence_partitions(workflow_id: str, value: object) -> list[str]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, str | bytes | bytearray)
        or not value
        or len(value) > len(_IMPACT_CUBE_PARTITION_ORDER)
        or any(item not in _IMPACT_CUBE_PARTITION_ORDER for item in value)
        or len(set(value)) != len(value)
    ):
        _evidence_invalid(
            workflow_id,
            "partitions It must be non-empty, only.development/validation/oot list.",
            "partitions",
        )
    normalized = [item for item in _IMPACT_CUBE_PARTITION_ORDER if item in value]
    if list(value) != normalized:
        _evidence_invalid(
            workflow_id,
            "partitions Must usecanonical .",
            "partitions",
        )
    return normalized


def _mapping_keys_are_text(value: object) -> bool:
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str) and _mapping_keys_are_text(item)
            for key, item in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return all(_mapping_keys_are_text(item) for item in value)
    return True


def _prepared(workflow_id: str, slots: Mapping[str, Any]) -> PreparedStrategyPlan:
    return PreparedStrategyPlan(
        workflow_id=workflow_id,
        template_id=workflow_id,
        slots=deep_freeze(slots),
        success_criteria=(),
    )


def _strategy_type(inputs: Mapping[str, Any], *, workflow: str) -> str:
    if "strategy_type" not in inputs:
        _invalid(workflow, "Missingstrategy_type.", "strategy_type")
    strategy_type = _required_text(
        inputs["strategy_type"], name="strategy_type", workflow=workflow
    )
    if strategy_type not in STRATEGY_TYPES:
        _invalid(
            workflow,
            "strategy_type It can only be:" + ",".join(STRATEGY_TYPES) + ".",
            "strategy_type",
        )
    return strategy_type


def _strategy_pool_action(
    value: object,
    *,
    strategy_type: str,
    name: str,
    workflow: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _invalid(workflow, f"{name} It must be.typed StrategyAction object.", name)
    try:
        action = StrategyAction.from_dict(value)
    except StrategyError as exc:
        raise StrategyWorkflowValidationError(
            f"{workflow} {name} Invalid:{exc}",
            fields=(name,),
        ) from exc
    if action.type not in _POOL_ACTION_TYPES[strategy_type]:
        _invalid(
            workflow,
            f"{name} It's...{action.type} Action does not apply{strategy_type} Strategy.",
            name,
        )
    return action.to_dict()


def _pool_identifier(value: object, *, name: str, workflow: str) -> str:
    identifier = _required_text(value, name=name, workflow=workflow)
    if _POOL_ITEM_ID_RE.fullmatch(identifier) is None:
        _invalid(
            workflow,
            f"{name} It has to be complete and safe.rule_id orentry_id.",
            name,
        )
    return identifier


def _column(
    value: object,
    *,
    name: str,
    workflow: str,
    whitelist: Sequence[str],
) -> str:
    column = _required_text(value, name=name, workflow=workflow)
    if column not in whitelist:
        _invalid(
            workflow,
            f"{name} Use column of the data set that does not exist{column}].",
            name,
        )
    return column


def _required_text(value: object, *, name: str, workflow: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _invalid(workflow, f"{name} It must be non-empty.", name)
    return value.strip()


def _reject_fields(
    inputs: Mapping[str, Any],
    allowed: set[str],
    *,
    workflow: str,
) -> None:
    if any(not isinstance(key, str) for key in inputs):
        raise StrategyWorkflowValidationError(
            f"{workflow} workflow_inputs Field names must be text."
        )
    unexpected = sorted(set(inputs) - allowed)
    if unexpected:
        raise StrategyWorkflowValidationError(
            f"{workflow} workflow_inputs Contains unsupported fields:"
            + ",".join(unexpected)
            + ".",
            fields=unexpected,
        )


def _compact_json(value: object) -> str:
    return json.dumps(
        deep_thaw(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _confirmation(details: list[str]) -> str:
    details.append(
        "Please confirm the above calibre.Agent Only trusted tools are organized; all numbers are calculated by the platform ' s certainty."
    )
    return ";".join(details)


def _invalid(workflow: str, message: str, *fields: str) -> None:
    raise StrategyWorkflowValidationError(
        f"{workflow} {message}",
        fields=fields,
    )


def _evidence_invalid(workflow: str, message: str, *fields: str) -> None:
    raise StrategyWorkflowValidationError(
        f"{workflow} {message}",
        code="strategy_workflow_evidence_invalid",
        fields=fields,
    )


def _evidence_conflict(workflow: str, message: str, *fields: str) -> None:
    raise StrategyWorkflowValidationError(
        f"{workflow} {message}",
        code="strategy_workflow_evidence_conflict",
        fields=fields,
    )


POOL_WORKFLOW_SPECS: tuple[StrategyWorkflowSpec, ...] = (
    StrategyWorkflowSpec(
        workflow_id=POOL_ADD_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(POOL_ADD_WORKFLOW_ID,),
        validator=validate_strategy_pool_add_candidate_inputs,
        confirmation=strategy_pool_add_candidate_confirmation,
        preparer=prepare_strategy_pool_add_candidate,
    ),
    StrategyWorkflowSpec(
        workflow_id=POOL_REMOVE_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(POOL_REMOVE_WORKFLOW_ID,),
        validator=validate_strategy_pool_remove_entry_inputs,
        confirmation=strategy_pool_remove_entry_confirmation,
        preparer=prepare_strategy_pool_remove_entry,
    ),
    StrategyWorkflowSpec(
        workflow_id=POOL_SET_ACTION_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(POOL_SET_ACTION_WORKFLOW_ID,),
        validator=validate_strategy_pool_set_action_inputs,
        confirmation=strategy_pool_set_action_confirmation,
        preparer=prepare_strategy_pool_set_action,
    ),
    StrategyWorkflowSpec(
        workflow_id=POOL_REORDER_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(POOL_REORDER_WORKFLOW_ID,),
        validator=validate_strategy_pool_reorder_inputs,
        confirmation=strategy_pool_reorder_confirmation,
        preparer=prepare_strategy_pool_reorder,
    ),
    StrategyWorkflowSpec(
        workflow_id=POOL_COMPILE_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(POOL_COMPILE_WORKFLOW_ID,),
        validator=validate_strategy_pool_compile_inputs,
        confirmation=strategy_pool_compile_confirmation,
        preparer=prepare_strategy_pool_compile,
    ),
    StrategyWorkflowSpec(
        workflow_id=POOL_MATERIALIZE_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(POOL_MATERIALIZE_WORKFLOW_ID,),
        validator=validate_strategy_pool_materialize_inputs,
        confirmation=strategy_pool_materialize_confirmation,
        preparer=prepare_strategy_pool_materialize,
    ),
    StrategyWorkflowSpec(
        workflow_id=POOL_APPLY_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(POOL_APPLY_WORKFLOW_ID,),
        validator=validate_strategy_pool_apply_inputs,
        confirmation=strategy_pool_apply_confirmation,
        preparer=prepare_strategy_pool_apply,
    ),
    StrategyWorkflowSpec(
        workflow_id=POOL_VALIDATION_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(POOL_VALIDATION_WORKFLOW_ID,),
        validator=validate_strategy_pool_validation_inputs,
        confirmation=strategy_pool_validation_confirmation,
        preparer=prepare_strategy_pool_validation,
    ),
    StrategyWorkflowSpec(
        workflow_id=POOL_IMPACT_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_IMPACT_REQUIREMENTS,
        template_ids=(POOL_IMPACT_WORKFLOW_ID,),
        validator=validate_strategy_pool_impact_inputs,
        confirmation=strategy_pool_impact_confirmation,
        preparer=prepare_strategy_pool_impact,
    ),
    StrategyWorkflowSpec(
        workflow_id=IMPACT_CUBE_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(IMPACT_CUBE_WORKFLOW_ID,),
        validator=validate_strategy_impact_cube_inputs,
        confirmation=strategy_impact_cube_confirmation,
        preparer=prepare_strategy_impact_cube,
    ),
    StrategyWorkflowSpec(
        workflow_id=POOL_STABILITY_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(POOL_STABILITY_WORKFLOW_ID,),
        validator=validate_strategy_pool_stability_inputs,
        confirmation=strategy_pool_stability_confirmation,
        preparer=prepare_strategy_pool_stability,
    ),
)


__all__ = [
    "IMPACT_CUBE_WORKFLOW_ID",
    "POOL_ADD_WORKFLOW_ID",
    "POOL_APPLY_WORKFLOW_ID",
    "POOL_COMPILE_WORKFLOW_ID",
    "POOL_IMPACT_WORKFLOW_ID",
    "POOL_MATERIALIZE_WORKFLOW_ID",
    "POOL_REMOVE_WORKFLOW_ID",
    "POOL_REORDER_WORKFLOW_ID",
    "POOL_SET_ACTION_WORKFLOW_ID",
    "POOL_STABILITY_WORKFLOW_ID",
    "POOL_VALIDATION_WORKFLOW_ID",
    "POOL_WORKFLOW_SPECS",
    "prepare_strategy_impact_cube",
    "prepare_strategy_pool_add_candidate",
    "prepare_strategy_pool_apply",
    "prepare_strategy_pool_compile",
    "prepare_strategy_pool_impact",
    "prepare_strategy_pool_materialize",
    "prepare_strategy_pool_remove_entry",
    "prepare_strategy_pool_reorder",
    "prepare_strategy_pool_set_action",
    "prepare_strategy_pool_stability",
    "prepare_strategy_pool_validation",
    "strategy_impact_cube_confirmation",
    "strategy_pool_add_candidate_confirmation",
    "strategy_pool_apply_confirmation",
    "strategy_pool_compile_confirmation",
    "strategy_pool_impact_confirmation",
    "strategy_pool_materialize_confirmation",
    "strategy_pool_remove_entry_confirmation",
    "strategy_pool_reorder_confirmation",
    "strategy_pool_set_action_confirmation",
    "strategy_pool_stability_confirmation",
    "strategy_pool_validation_confirmation",
    "validate_strategy_impact_cube_inputs",
    "validate_strategy_pool_add_candidate_inputs",
    "validate_strategy_pool_apply_inputs",
    "validate_strategy_pool_compile_inputs",
    "validate_strategy_pool_impact_inputs",
    "validate_strategy_pool_materialize_inputs",
    "validate_strategy_pool_remove_entry_inputs",
    "validate_strategy_pool_reorder_inputs",
    "validate_strategy_pool_set_action_inputs",
    "validate_strategy_pool_stability_inputs",
    "validate_strategy_pool_validation_inputs",
]
