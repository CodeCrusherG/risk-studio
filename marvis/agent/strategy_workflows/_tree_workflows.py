"""Canonical adapters for the governed automatic/interactive tree workflows.

This module deliberately stops at plan preparation.  Platform-owned artifact,
workspace, SampleDesign, ancestry, node and current-projection facts enter only
through ``bind_workflow_evidence``; no Tool or legacy request handler is called.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import re
from typing import Any
import unicodedata

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


AUTOMATIC_TREE_BUILD_WORKFLOW_ID = "automatic_tree_candidate_build"
AUTOMATIC_TREE_APPLY_WORKFLOW_ID = "automatic_tree_apply"
AUTOMATIC_TREE_LEAF_WORKFLOW_ID = "automatic_tree_leaf_materialization"
INTERACTIVE_TREE_SPLIT_SEARCH_WORKFLOW_ID = "interactive_tree_split_search"
INTERACTIVE_TREE_CONTINUATION_WORKFLOW_ID = "interactive_tree_auto_continuation"
INTERACTIVE_TREE_REVISION_WORKFLOW_ID = "interactive_tree_revision"

AUTOMATIC_TREE_BUILD_TEMPLATE_ID = "strategy_automatic_tree_candidate_build"
AUTOMATIC_TREE_APPLY_TEMPLATE_ID = "strategy_automatic_tree_apply"
AUTOMATIC_TREE_LEAF_TEMPLATE_ID = "strategy_automatic_tree_leaf_materialization"
INTERACTIVE_TREE_SPLIT_SEARCH_TEMPLATE_ID = "strategy_interactive_tree_split_search"
INTERACTIVE_TREE_CONTINUATION_TEMPLATE_ID = (
    "strategy_interactive_tree_auto_continuation"
)
INTERACTIVE_TREE_REVISION_TEMPLATE_ID = "strategy_interactive_tree_revision"

AUTOMATIC_TREE_DIRECTIONS = (
    "increasing",
    "decreasing",
    "unordered",
)

_CANDIDATE_ASSET_ID_RE = re.compile(r"candidate-asset-[0-9a-f]{32}")
_AUTOMATIC_TREE_LEAF_ID_RE = re.compile(r"leaf-[0-9a-f]{20}")
_INTERACTIVE_TREE_SOURCE_ID_RE = re.compile(
    r"(?:candidate-asset|interactive-tree-revision)-[0-9a-f]{32}"
)
_INTERACTIVE_TREE_NODE_ID_RE = re.compile(r"node-[0-9a-f]{20}")
_INTERACTIVE_TREE_SPLIT_SEARCH_ID_RE = re.compile(
    r"interactive-tree-split-search-[0-9a-f]{32}"
)
_INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_RE = re.compile(
    r"interactive-tree-split-candidate-[0-9a-f]{32}"
)
_APPLY_OUTPUT_COLUMN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")

_BUILD_EVIDENCE_FIELDS = frozenset(
    {
        "dataset_id",
        "expected_content_hash",
        "workspace_revision",
        "analysis_generation",
        "semantic_mapping_hash",
        "target_col",
        "sample_design_ref",
    }
)
_APPLY_EVIDENCE_FIELDS = frozenset(
    {
        "source_artifact_id",
        "expected_artifact_content_hash",
        "expected_asset_id",
        "expected_asset_hash",
        "expected_tree_result_hash",
        "dataset_id",
        "expected_content_hash",
        "workspace_revision",
        "analysis_generation",
        "semantic_mapping_hash",
    }
)
_LEAF_EVIDENCE_FIELDS = frozenset(
    {
        "source_artifact_id",
        "expected_artifact_content_hash",
        "expected_asset_id",
        "expected_asset_hash",
        "expected_tree_result_hash",
    }
)

_DATA_TARGET_REQUIREMENTS = StrategyWorkflowRequirements(
    dataset=True,
    target=True,
    complete_labels=True,
)
_DATA_REQUIREMENTS = StrategyWorkflowRequirements(
    dataset=True,
    target=False,
    complete_labels=False,
)
_NO_REQUIREMENTS = StrategyWorkflowRequirements(
    dataset=False,
    target=False,
    complete_labels=False,
)


def validate_automatic_tree_candidate_build_inputs(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = AUTOMATIC_TREE_BUILD_WORKFLOW_ID
    allowed = {
        "features",
        "sample_weight_col",
        "directions",
        "max_depth",
        "min_leaf_count",
        "min_weight_fraction_leaf",
        "seed",
        "loan_amount_col",
        "overdue_amount_col",
    }
    _reject_fields(inputs, allowed, workflow=workflow)
    if "features" not in inputs:
        _invalid(workflow, "Required Fields Missingfeatures.", "features")
    raw_features = inputs["features"]
    if (
        not isinstance(raw_features, Sequence)
        or isinstance(raw_features, str | bytes | bytearray)
        or not 1 <= len(raw_features) <= 50
    ):
        _invalid(
            workflow,
            "features An orderly array of 1 to 50 fields must be in place.",
            "features",
        )
    features = [
        _column(
            value,
            name="features",
            workflow=workflow,
            whitelist=context.allowed_columns,
        )
        for value in raw_features
    ]
    if len(features) != len(set(features)):
        _invalid(workflow, "features Could not close temporary folder: %s", "features")
    if context.target_col is not None and context.target_col in features:
        _invalid(
            workflow,
            f"features Cannot include target column{context.target_col}.",
            "features",
        )

    normalized: dict[str, Any] = {"features": features}
    for field in ("sample_weight_col", "loan_amount_col", "overdue_amount_col"):
        if field not in inputs:
            continue
        column = _column(
            inputs[field],
            name=field,
            workflow=workflow,
            whitelist=context.allowed_columns,
        )
        if context.target_col is not None and column == context.target_col:
            _invalid(workflow, f"{field} The target column cannot be used.", field)
        normalized[field] = column

    if "directions" in inputs:
        raw_directions = inputs["directions"]
        if not isinstance(raw_directions, Mapping) or not raw_directions:
            _invalid(
                workflow,
                "directions (a) The object must contain at least one characteristic direction;"
                "Please omit this field when there is no risk orientation diagnostic expectation or examination.",
                "directions",
            )
        if any(not isinstance(key, str) for key in raw_directions):
            _invalid(workflow, "directions field name must be text.", "directions")
        unexpected_features = sorted(set(raw_directions) - set(features))
        if unexpected_features:
            _invalid(
                workflow,
                "directions Unselected features are cited:"
                + ",".join(unexpected_features)
                + ".",
                "directions",
            )
        directions: dict[str, str] = {}
        for feature, value in raw_directions.items():
            if not isinstance(value, str) or value not in AUTOMATIC_TREE_DIRECTIONS:
                _invalid(
                    workflow,
                    f"directions.{feature} It\'s just...increasing,decreasing orunordered.",
                    "directions",
                )
            directions[feature] = value
        normalized["directions"] = directions

    if "max_depth" in inputs:
        normalized["max_depth"] = _bounded_int(
            inputs["max_depth"],
            name="max_depth",
            workflow=workflow,
            minimum=1,
            maximum=8,
        )
    if "min_leaf_count" in inputs:
        value = inputs["min_leaf_count"]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            _invalid(workflow, "min_leaf_count Must be positive integers.", "min_leaf_count")
        normalized["min_leaf_count"] = value
    if "min_weight_fraction_leaf" in inputs:
        normalized["min_weight_fraction_leaf"] = _bounded_number(
            inputs["min_weight_fraction_leaf"],
            name="min_weight_fraction_leaf",
            workflow=workflow,
            maximum=0.5,
        )
    if "seed" in inputs:
        normalized["seed"] = _bounded_int(
            inputs["seed"],
            name="seed",
            workflow=workflow,
            minimum=0,
            maximum=4_294_967_295,
        )

    assigned_columns = [
        normalized[field]
        for field in ("sample_weight_col", "loan_amount_col", "overdue_amount_col")
        if field in normalized
    ]
    duplicate_roles = {
        column for column in assigned_columns if assigned_columns.count(column) > 1
    }
    feature_conflicts = set(features) & set(assigned_columns)
    if duplicate_roles or feature_conflicts:
        conflicts = sorted(duplicate_roles | feature_conflicts)
        raise StrategyWorkflowValidationError(
            f"{workflow} features,sample_weight_col,loan_amount_col and"
            "overdue_amount_col Different fields must be used:" + ",".join(conflicts) + ".",
            fields=(
                "features",
                "sample_weight_col",
                "loan_amount_col",
                "overdue_amount_col",
            ),
        )
    return normalized


def automatic_tree_candidate_build_confirmation(inputs: Mapping[str, Any]) -> str:
    direction_labels = {
        "increasing": "Incremental",
        "decreasing": "Decline",
        "unordered": "Orderless",
    }
    details = [
        "Recognized as [Auto-Decision Tree Candidates Build]Workflow〕",
        "Candidate characteristics:" + ",".join(inputs["features"]),
    ]
    if "sample_weight_col" in inputs:
        details.append(f"Sample weight column{inputs['sample_weight_col']}")
    if "directions" in inputs:
        details.append(
            "Risk orientation diagnostic expectations:"
            + ",".join(
                f"{feature}={direction_labels[direction]}"
                for feature, direction in inputs["directions"].items()
            )
        )
    if "max_depth" in inputs:
        details.append(f"Maximum depth{inputs['max_depth']}")
    if "min_leaf_count" in inputs:
        details.append(f"Number of minimum leaf samples{inputs['min_leaf_count']}")
    if "min_weight_fraction_leaf" in inputs:
        details.append(f"Minimal foliage weight ratio{inputs['min_weight_fraction_leaf']:.2%}")
    if "seed" in inputs:
        details.append(f"Random Feeds{inputs['seed']}")
    if "loan_amount_col" in inputs:
        details.append(f"Lending amount line{inputs['loan_amount_col']}")
    if "overdue_amount_col" in inputs:
        details.append(f"Overdue Amount Column{inputs['overdue_amount_col']}")
    details.extend(
        [
            "data sets,hash,workspace,The target line, label handling and implementation budget are bound by the platform."
            "LLM Not Signed",
            "This step builds only full candidate tree and conclusive evidence; no automatic leaves selection, writing"
            "Strategy Pool,Adoption or deployment",
            "Platform does not generate an \"optimal\" automatic ranking of leaves; subsequent actions must be quoted clearly by the userleaf",
        ]
    )
    return ";".join(details)


def prepare_automatic_tree_candidate_build(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    _require_dataset_context(AUTOMATIC_TREE_BUILD_WORKFLOW_ID, context)
    slots = deep_thaw(deep_freeze(inputs))
    evidence = _workflow_evidence(
        AUTOMATIC_TREE_BUILD_WORKFLOW_ID,
        inputs,
        context,
        slots,
        required_fields=_BUILD_EVIDENCE_FIELDS,
    )
    _validate_evidence_values(
        AUTOMATIC_TREE_BUILD_WORKFLOW_ID,
        evidence,
        context=context,
        require_sample_design=True,
    )
    slots.update(evidence)
    if context.drop_nan_labels:
        slots["drop_nan_labels"] = True
    return _prepared(
        AUTOMATIC_TREE_BUILD_WORKFLOW_ID,
        AUTOMATIC_TREE_BUILD_TEMPLATE_ID,
        slots,
    )


def validate_automatic_tree_apply_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = AUTOMATIC_TREE_APPLY_WORKFLOW_ID
    allowed = {"tree_asset_id", "leaf_id_column", "rule_id_column"}
    _reject_fields(inputs, allowed, workflow=workflow)
    if "tree_asset_id" not in inputs:
        _invalid(workflow, "Missing field:tree_asset_id.", "tree_asset_id")
    tree_asset_id = _required_text(
        inputs["tree_asset_id"], name="tree_asset_id", workflow=workflow
    )
    if _CANDIDATE_ASSET_ID_RE.fullmatch(tree_asset_id) is None:
        _invalid(
            workflow,
            "tree_asset_id It must be a complete automatic tree.candidate asset id.",
            "tree_asset_id",
        )
    normalized: dict[str, Any] = {"tree_asset_id": tree_asset_id}
    for field in ("leaf_id_column", "rule_id_column"):
        if field not in inputs:
            continue
        value = _required_text(inputs[field], name=field, workflow=workflow)
        if _APPLY_OUTPUT_COLUMN_RE.fullmatch(value) is None:
            _invalid(
                workflow,
                f"{field} Must be 64 bits maximumASCII identifier.",
                field,
            )
        normalized[field] = value
    if (
        "leaf_id_column" in normalized
        and "rule_id_column" in normalized
        and normalized["leaf_id_column"].casefold()
        == normalized["rule_id_column"].casefold()
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow} leaf_id_column andrule_id_column It must be different (ignominious case).",
            fields=("leaf_id_column", "rule_id_column"),
        )
    return normalized


def automatic_tree_apply_confirmation(inputs: Mapping[str, Any]) -> str:
    details = [
        "Recognized as [Auto-Frive Back]Workflow〕",
        f"Full Tree Candidate Assetspointer:{inputs['tree_asset_id']}",
        (
            f"Leaf Node Output Column:{inputs['leaf_id_column']}"
            if "leaf_id_column" in inputs
            else "Leaf Node Output Column: ControlledTool Use default listing"
        ),
        (
            f"Rule output column:{inputs['rule_id_column']}"
            if "rule_id_column" in inputs
            else "Rule output column: controlledTool Use default listing"
        ),
        "Platform will be rechecked from current tasksource artifact/hash,asset hash,"
        "Original dataset andworkspace lineage,LLM Do not fill or overwrite",
        "This step creates a non-variable dataset, but does not activate or replace the current oneworkspace",
        "The result is stilldevelopment / unvalidated;No pool, no adoption, no deployment, no operational actions",
    ]
    return ";".join(details)


def prepare_automatic_tree_apply(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    _require_dataset_context(AUTOMATIC_TREE_APPLY_WORKFLOW_ID, context)
    slots = {
        field: deep_thaw(deep_freeze(inputs[field]))
        for field in ("leaf_id_column", "rule_id_column")
        if field in inputs
    }
    evidence = _workflow_evidence(
        AUTOMATIC_TREE_APPLY_WORKFLOW_ID,
        inputs,
        context,
        slots,
        required_fields=_APPLY_EVIDENCE_FIELDS,
    )
    _validate_evidence_values(
        AUTOMATIC_TREE_APPLY_WORKFLOW_ID,
        evidence,
        context=context,
        expected_asset_id=inputs["tree_asset_id"],
    )
    slots.update(evidence)
    return _prepared(
        AUTOMATIC_TREE_APPLY_WORKFLOW_ID,
        AUTOMATIC_TREE_APPLY_TEMPLATE_ID,
        slots,
    )


def validate_automatic_tree_leaf_materialization_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = AUTOMATIC_TREE_LEAF_WORKFLOW_ID
    allowed = {"tree_asset_id", "leaf_id", "selection_reason"}
    _reject_fields(inputs, allowed, workflow=workflow)
    missing = sorted({"tree_asset_id", "leaf_id"} - set(inputs))
    if missing:
        raise StrategyWorkflowValidationError(
            f"{workflow} Missing field:" + ",".join(missing) + ".",
            fields=missing,
        )
    tree_asset_id = _required_text(
        inputs["tree_asset_id"], name="tree_asset_id", workflow=workflow
    )
    if _CANDIDATE_ASSET_ID_RE.fullmatch(tree_asset_id) is None:
        _invalid(
            workflow,
            "tree_asset_id It must be a complete automatic tree.candidate asset id.",
            "tree_asset_id",
        )
    leaf_id = _required_text(inputs["leaf_id"], name="leaf_id", workflow=workflow)
    if _AUTOMATIC_TREE_LEAF_ID_RE.fullmatch(leaf_id) is None:
        _invalid(
            workflow,
            "leaf_id It must be.leaf- followed by 20-bit lowercase hexadecimal characters.",
            "leaf_id",
        )
    normalized: dict[str, Any] = {
        "tree_asset_id": tree_asset_id,
        "leaf_id": leaf_id,
    }
    if "selection_reason" in inputs:
        normalized["selection_reason"] = _canonical_reason(
            inputs["selection_reason"],
            name="selection_reason",
            workflow=workflow,
            maximum=None,
        )
    return normalized


def automatic_tree_leaf_materialization_confirmation(
    inputs: Mapping[str, Any],
) -> str:
    details = [
        "Recognized as [Automated Folic Exact Node]Workflow〕",
        f"Full Tree Candidate Assetspointer:{inputs['tree_asset_id']}",
        f"Precision of leaf nodespointer:{inputs['leaf_id']}",
        "This step only creates the inflexible point of the whole treepointer;"
        "Do not copy rules, conditions, indicators or business actions",
        "I won't join.Strategy Pool,And I'm not gonna take or deploy.",
    ]
    if "selection_reason" in inputs:
        details.append(f"User selection statement:{inputs['selection_reason']}")
    return ";".join(details)


def prepare_automatic_tree_leaf_materialization(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    slots: dict[str, Any] = {"leaf_id": inputs["leaf_id"]}
    if "selection_reason" in inputs:
        slots["selection_reason"] = inputs["selection_reason"]
    evidence = _workflow_evidence(
        AUTOMATIC_TREE_LEAF_WORKFLOW_ID,
        inputs,
        context,
        slots,
        required_fields=_LEAF_EVIDENCE_FIELDS,
    )
    _validate_evidence_values(
        AUTOMATIC_TREE_LEAF_WORKFLOW_ID,
        evidence,
        context=context,
        expected_asset_id=inputs["tree_asset_id"],
    )
    slots.update(evidence)
    return _prepared(
        AUTOMATIC_TREE_LEAF_WORKFLOW_ID,
        AUTOMATIC_TREE_LEAF_TEMPLATE_ID,
        slots,
    )


def validate_interactive_tree_split_search_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = INTERACTIVE_TREE_SPLIT_SEARCH_WORKFLOW_ID
    allowed = {
        "source_tree_id",
        "node_id",
        "mode",
        "features",
        "max_thresholds_per_feature",
        "max_row_evaluations",
    }
    _reject_fields(inputs, allowed, workflow=workflow)
    required = {
        "source_tree_id",
        "node_id",
        "mode",
        "max_thresholds_per_feature",
        "max_row_evaluations",
    }
    missing = sorted(required - set(inputs))
    if missing:
        raise StrategyWorkflowValidationError(
            f"{workflow} Missing field:" + ",".join(missing) + ".",
            fields=missing,
        )
    source_tree_id = _source_tree_id(inputs["source_tree_id"], workflow=workflow)
    node_id = _node_id(inputs["node_id"], workflow=workflow)
    mode = _required_text(inputs["mode"], name="mode", workflow=workflow)
    if mode not in {"all_features", "selected_features"}:
        _invalid(
            workflow,
            "mode Only allowedall_features orselected_features.",
            "mode",
        )
    has_features = "features" in inputs
    if mode == "all_features" and has_features:
        _invalid(workflow, "all_features Cannot providefeatures.", "features")
    if mode == "selected_features" and not has_features:
        _invalid(workflow, "selected_features Must providefeatures.", "features")
    normalized: dict[str, Any] = {
        "source_tree_id": source_tree_id,
        "node_id": node_id,
        "mode": mode,
    }
    if has_features:
        raw_features = inputs["features"]
        if isinstance(raw_features, str | bytes | bytearray) or not isinstance(
            raw_features, Sequence
        ):
            _invalid(workflow, "features must be a non-empty string array.", "features")
        features = [
            _required_text(item, name="features", workflow=workflow)
            for item in raw_features
        ]
        if not features or len(features) > 50 or len(features) != len(set(features)):
            _invalid(
                workflow,
                "features It must be non-empty, only and not more than 50.",
                "features",
            )
        normalized["features"] = sorted(features)
    normalized["max_thresholds_per_feature"] = _bounded_int(
        inputs["max_thresholds_per_feature"],
        name="max_thresholds_per_feature",
        workflow=workflow,
        minimum=1,
        maximum=20,
    )
    normalized["max_row_evaluations"] = _bounded_int(
        inputs["max_row_evaluations"],
        name="max_row_evaluations",
        workflow=workflow,
        minimum=1,
        maximum=20_000_000,
    )
    return normalized


def interactive_tree_split_search_confirmation(inputs: Mapping[str, Any]) -> str:
    details = [
        "Recognized as [interactive tree node split candidate]Workflow〕",
        f"Source Treepointer:{inputs['source_tree_id']}",
        f"Exact Visibilitynode pointer:{inputs['node_id']}",
        (
            "Search range: authenticate all characteristics of the tree"
            if inputs["mode"] == "all_features"
            else "Search range: user-defined feature subset" + ",".join(inputs["features"])
        ),
        f"Maximum candidate threshold for each feature:{inputs['max_thresholds_per_feature']}",
        f"The budget for the appraisal of the head office:{inputs['max_row_evaluations']}",
        "The platform will authenticate the complete tree parent chain, data set,workspace andSampleDesign,Only"
        "Enduring to aggregate risk evidence at the right and right nodes without exporting client details",
        "Ranking is only for browsing; this step does not select winners, modify trees, enter pools, apply, adopt or deploy",
    ]
    return ";".join(details)


def prepare_interactive_tree_split_search(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    return _prepare_pointer_only_interactive(
        INTERACTIVE_TREE_SPLIT_SEARCH_WORKFLOW_ID,
        INTERACTIVE_TREE_SPLIT_SEARCH_TEMPLATE_ID,
        inputs,
        context,
    )


def validate_interactive_tree_auto_continuation_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = INTERACTIVE_TREE_CONTINUATION_WORKFLOW_ID
    allowed = {
        "search_id",
        "candidate_id",
        "max_additional_depth",
        "min_gini_gain",
        "max_generated_nodes",
        "max_thresholds_per_feature",
        "max_row_evaluations",
        "objective",
        "tie_break",
        "reason",
    }
    _reject_fields(inputs, allowed, workflow=workflow)
    required = allowed - {"reason"}
    missing = sorted(required - set(inputs))
    if missing:
        raise StrategyWorkflowValidationError(
            f"{workflow} Missing field:" + ",".join(missing) + ".",
            fields=missing,
        )
    search_id = _required_text(inputs["search_id"], name="search_id", workflow=workflow)
    candidate_id = _required_text(
        inputs["candidate_id"], name="candidate_id", workflow=workflow
    )
    if _INTERACTIVE_TREE_SPLIT_SEARCH_ID_RE.fullmatch(search_id) is None:
        _invalid(workflow, "search_id Format is invalid.", "search_id")
    if _INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_RE.fullmatch(candidate_id) is None:
        _invalid(workflow, "candidate_id Format is invalid.", "candidate_id")
    normalized: dict[str, Any] = {
        "search_id": search_id,
        "candidate_id": candidate_id,
    }
    for field, minimum, maximum in (
        ("max_additional_depth", 1, 6),
        ("max_generated_nodes", 3, 127),
        ("max_thresholds_per_feature", 1, 20),
        ("max_row_evaluations", 1, 20_000_000),
    ):
        normalized[field] = _bounded_int(
            inputs[field],
            name=field,
            workflow=workflow,
            minimum=minimum,
            maximum=maximum,
        )
    normalized["min_gini_gain"] = _bounded_number(
        inputs["min_gini_gain"],
        name="min_gini_gain",
        workflow=workflow,
        maximum=0.5,
    )
    objective = _required_text(inputs["objective"], name="objective", workflow=workflow)
    tie_break = _required_text(inputs["tie_break"], name="tie_break", workflow=workflow)
    if objective != "max_gini_gain" or tie_break != (
        "eligible_gain_feature_threshold_candidate_id"
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow} objective ortie_break This does not fit into a fixed certainty strategy.",
            fields=("objective", "tie_break"),
        )
    normalized["objective"] = objective
    normalized["tie_break"] = tie_break
    if "reason" in inputs:
        normalized["reason"] = _canonical_reason(
            inputs["reason"],
            name="reason",
            workflow=workflow,
            maximum=500,
        )
    return normalized


def interactive_tree_auto_continuation_confirmation(
    inputs: Mapping[str, Any],
) -> str:
    details = [
        "Recognized as [interactive tree controlled automatic continuation]Workflow〕",
        f"Exact search for evidence:{inputs['search_id']}",
        f"Manually selected seed candidate:{inputs['candidate_id']}",
        f"Maximum additional depth:{inputs['max_additional_depth']}",
        f"MinGini Gains:{inputs['min_gini_gain']}",
        f"Maximum number of nodes generated:{inputs['max_generated_nodes']}",
        f"Maximum candidate threshold for each feature:{inputs['max_thresholds_per_feature']}",
        f"The budget for the appraisal of the head office:{inputs['max_row_evaluations']}",
        f"Fixed target:{inputs['objective']}",
        f"Fixed parallel rules:{inputs['tie_break']}",
        "The platform will certify search, candidate, tree curator, data set andSampleDesign,And"
        "Stable continuation within hard budget; no automatic selection of seed candidates",
        "It's just new.development / unvalidated Non-modifiable; no pool, application, adoption or deployment",
    ]
    if "reason" in inputs:
        details.append(f"Users\' originals continuation:{inputs['reason']}")
    return ";".join(details)


def prepare_interactive_tree_auto_continuation(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    return _prepare_pointer_only_interactive(
        INTERACTIVE_TREE_CONTINUATION_WORKFLOW_ID,
        INTERACTIVE_TREE_CONTINUATION_TEMPLATE_ID,
        inputs,
        context,
    )


def validate_interactive_tree_revision_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = INTERACTIVE_TREE_REVISION_WORKFLOW_ID
    allowed = {
        "source_tree_id",
        "node_id",
        "operation",
        "feature",
        "threshold",
        "reason",
    }
    _reject_fields(inputs, allowed, workflow=workflow)
    missing = sorted({"source_tree_id", "node_id", "operation"} - set(inputs))
    if missing:
        raise StrategyWorkflowValidationError(
            f"{workflow} Missing field:" + ",".join(missing) + ".",
            fields=missing,
        )
    source_tree_id = _source_tree_id(inputs["source_tree_id"], workflow=workflow)
    node_id = _node_id(inputs["node_id"], workflow=workflow)
    operation = _required_text(inputs["operation"], name="operation", workflow=workflow)
    if operation not in {
        "prune_subtree",
        "adjust_split_threshold",
        "replace_split_feature",
    }:
        _invalid(
            workflow,
            "operation Only allowedprune_subtree,adjust_split_threshold or"
            "replace_split_feature.",
            "operation",
        )
    has_threshold = "threshold" in inputs
    has_feature = "feature" in inputs
    if operation in {"adjust_split_threshold", "replace_split_feature"} and not (
        has_threshold
    ):
        _invalid(workflow, "The division must be provided.threshold.", "threshold")
    if operation == "prune_subtree" and has_threshold:
        _invalid(workflow, "prune_subtree Cannot providethreshold.", "threshold")
    if operation == "replace_split_feature" and not has_feature:
        _invalid(
            workflow,
            "replace_split_feature Must providefeature.",
            "feature",
        )
    if operation != "replace_split_feature" and has_feature:
        _invalid(
            workflow,
            "Onlyreplace_split_feature It's available.feature.",
            "feature",
        )
    normalized: dict[str, Any] = {
        "source_tree_id": source_tree_id,
        "node_id": node_id,
        "operation": operation,
    }
    if has_threshold:
        threshold = inputs["threshold"]
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, int | float)
            or not math.isfinite(float(threshold))
        ):
            _invalid(workflow, "threshold It must be.finite number.", "threshold")
        if isinstance(threshold, int) and abs(threshold) > 2**53 - 1:
            _invalid(
                workflow,
                "threshold Beyond precisionJSON number Scope.",
                "threshold",
            )
        normalized["threshold"] = float(threshold)
    if has_feature:
        normalized["feature"] = _required_text(
            inputs["feature"], name="feature", workflow=workflow
        )
    if "reason" in inputs:
        normalized["reason"] = (
            None
            if inputs["reason"] is None
            else _canonical_reason(
                inputs["reason"],
                name="reason",
                workflow=workflow,
                maximum=500,
            )
        )
    return normalized


def interactive_tree_revision_confirmation(inputs: Mapping[str, Any]) -> str:
    operation = inputs["operation"]
    details = [
        (
            "Recognized as [interactive tree threshold adjustment revision]Workflow〕"
            if operation == "adjust_split_threshold"
            else (
                "Recognized as [interactive tree-to-separation feature modification]Workflow〕"
                if operation == "replace_split_feature"
                else "Recognized as [interactive tree trimmed]Workflow〕"
            )
        ),
        f"Source Treepointer:{inputs['source_tree_id']}",
        f"Precisionsplit node pointer:{inputs['node_id']}",
        f"Operation:{operation}",
        "Platform will restore and authenticate the full automatic tree, parentrevision,data sets,workspace and"
        "SampleDesign,Anddevelopment Sample-by-line resetfrontier",
        "One unchangeable at a timerevision;No changes to the original tree, no additions."
        "Strategy Pool;No action will be taken or deployed, no action will be set up or written back",
    ]
    if operation in {"adjust_split_threshold", "replace_split_feature"}:
        details.insert(4, f"User-defined new threshold:{inputs['threshold']}")
    if operation == "replace_split_feature":
        details.insert(4, f"User-defined new split feature:{inputs['feature']}")
    if "reason" in inputs and inputs["reason"] is not None:
        details.append(f"User-name editorial notes:{inputs['reason']}")
    return ";".join(details)


def prepare_interactive_tree_revision(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    return _prepare_pointer_only_interactive(
        INTERACTIVE_TREE_REVISION_WORKFLOW_ID,
        INTERACTIVE_TREE_REVISION_TEMPLATE_ID,
        inputs,
        context,
    )


def _prepare_pointer_only_interactive(
    workflow_id: str,
    template_id: str,
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    slots = deep_thaw(deep_freeze(inputs))
    evidence = _workflow_evidence(
        workflow_id,
        inputs,
        context,
        slots,
        required_fields=frozenset(),
    )
    if evidence:  # Exact schema above already rejects this; defensive only.
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Runtime platform not acceptedevidence slots.",
            code="strategy_workflow_evidence_invalid",
            fields=tuple(sorted(evidence)),
        )
    return _prepared(workflow_id, template_id, slots)


def _workflow_evidence(
    workflow_id: str,
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
    canonical_slots: Mapping[str, Any],
    *,
    required_fields: frozenset[str],
) -> dict[str, Any]:
    binder = context.bind_workflow_evidence
    if binder is None:
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Evidence bound for lack of Platform authentication.",
            code="strategy_workflow_evidence_binding_required",
        )
    frozen_inputs = deep_freeze(deep_thaw(inputs))
    evidence = binder(workflow_id, frozen_inputs)
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
    actual_fields = frozenset(evidence)
    if actual_fields != required_fields:
        missing = sorted(required_fields - actual_fields)
        unexpected = sorted(actual_fields - required_fields)
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


def _validate_evidence_values(
    workflow_id: str,
    evidence: Mapping[str, Any],
    *,
    context: StrategyWorkflowPreparationContext,
    expected_asset_id: object | None = None,
    require_sample_design: bool = False,
) -> None:
    integer_fields = {"workspace_revision", "analysis_generation"} & set(evidence)
    invalid = [
        field
        for field in integer_fields
        if isinstance(evidence[field], bool)
        or not isinstance(evidence[field], int)
        or evidence[field] < 0
    ]
    text_fields = set(evidence) - integer_fields - {"sample_design_ref"}
    invalid.extend(
        field
        for field in text_fields
        if not isinstance(evidence[field], str) or not evidence[field].strip()
    )
    if require_sample_design and (
        not isinstance(evidence.get("sample_design_ref"), Mapping)
        or not evidence["sample_design_ref"]
    ):
        invalid.append("sample_design_ref")
    if invalid:
        fields = tuple(sorted(set(invalid)))
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Platform evidence values are incomplete or invalid:" + ",".join(fields) + ".",
            code="strategy_workflow_evidence_invalid",
            fields=fields,
        )
    if "dataset_id" in evidence and evidence["dataset_id"] != context.dataset_id:
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Platform evidencedataset_id This is not consistent with the current context of the preparation.",
            code="strategy_workflow_evidence_conflict",
            fields=("dataset_id",),
        )
    if expected_asset_id is not None and evidence.get("expected_asset_id") != (
        expected_asset_id
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Platform evidence does not bind the user to a specific choicetree_asset_id.",
            code="strategy_workflow_evidence_conflict",
            fields=("tree_asset_id", "expected_asset_id"),
        )


def _mapping_keys_are_text(value: object) -> bool:
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str) and _mapping_keys_are_text(item)
            for key, item in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return all(_mapping_keys_are_text(item) for item in value)
    return True


def _require_dataset_context(
    workflow_id: str,
    context: StrategyWorkflowPreparationContext,
) -> None:
    if not isinstance(context.dataset_id, str) or not context.dataset_id.strip():
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Current activity requiredDataWorkspace dataset_id.",
            code="strategy_workflow_dataset_binding_required",
            fields=("dataset_id",),
        )


def _prepared(
    workflow_id: str,
    template_id: str,
    slots: Mapping[str, Any],
) -> PreparedStrategyPlan:
    return PreparedStrategyPlan(
        workflow_id=workflow_id,
        template_id=template_id,
        slots=deep_freeze(slots),
        success_criteria=(),
    )


def _source_tree_id(value: object, *, workflow: str) -> str:
    source_tree_id = _required_text(value, name="source_tree_id", workflow=workflow)
    if _INTERACTIVE_TREE_SOURCE_ID_RE.fullmatch(source_tree_id) is None:
        _invalid(
            workflow,
            "source_tree_id It has to be complete.automatic-tree asset or"
            "interactive-tree revision ID.",
            "source_tree_id",
        )
    return source_tree_id


def _node_id(value: object, *, workflow: str) -> str:
    node_id = _required_text(value, name="node_id", workflow=workflow)
    if _INTERACTIVE_TREE_NODE_ID_RE.fullmatch(node_id) is None:
        _invalid(
            workflow,
            "node_id It must be.node- followed by 20-bit lowercase hexadecimal characters.",
            "node_id",
        )
    return node_id


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


def _column(
    value: object,
    *,
    name: str,
    workflow: str,
    whitelist: Sequence[str],
) -> str:
    column = _required_text(value, name=name, workflow=workflow)
    if column not in whitelist:
        _invalid(workflow, f"{name} Use column of the data set that does not exist{column}].", name)
    return column


def _required_text(value: object, *, name: str, workflow: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _invalid(workflow, f"{name} It must be non-empty.", name)
    return value.strip()


def _canonical_reason(
    value: object,
    *,
    name: str,
    workflow: str,
    maximum: int | None,
) -> str:
    if not isinstance(value, str):
        _invalid(workflow, f"{name} It must be text.", name)
    if "\x00" in value:
        _invalid(workflow, f"{name} Can not get folder: %s: %sNUL.", name)
    canonical = " ".join(unicodedata.normalize("NFC", value).split())
    if not canonical or (maximum is not None and len(canonical) > maximum):
        detail = (
            f"{name} It must be non-empty."
            if maximum is None
            else f"{name} Must be one to{maximum} character."
        )
        _invalid(workflow, detail, name)
    return canonical


def _bounded_int(
    value: object,
    *,
    name: str,
    workflow: str,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        _invalid(
            workflow,
            f"{name} It must be.{minimum} Present.{maximum} .",
            name,
        )
    return value


def _bounded_number(
    value: object,
    *,
    name: str,
    workflow: str,
    maximum: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        _invalid(workflow, f"{name} It must be limited.", name)
    number = float(value)
    if not math.isfinite(number) or number < 0 or number > maximum:
        _invalid(
            workflow,
            f"{name} It must be 0 to{maximum:g} There are limited numbers between.",
            name,
        )
    return number


def _invalid(workflow: str, message: str, *fields: str) -> None:
    raise StrategyWorkflowValidationError(
        f"{workflow} {message}",
        fields=fields,
    )


TREE_WORKFLOW_SPECS: tuple[StrategyWorkflowSpec, ...] = (
    StrategyWorkflowSpec(
        workflow_id=AUTOMATIC_TREE_BUILD_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_DATA_TARGET_REQUIREMENTS,
        template_ids=(AUTOMATIC_TREE_BUILD_TEMPLATE_ID,),
        validator=validate_automatic_tree_candidate_build_inputs,
        confirmation=automatic_tree_candidate_build_confirmation,
        preparer=prepare_automatic_tree_candidate_build,
    ),
    StrategyWorkflowSpec(
        workflow_id=AUTOMATIC_TREE_APPLY_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=False,
        requirements=_DATA_REQUIREMENTS,
        template_ids=(AUTOMATIC_TREE_APPLY_TEMPLATE_ID,),
        validator=validate_automatic_tree_apply_inputs,
        confirmation=automatic_tree_apply_confirmation,
        preparer=prepare_automatic_tree_apply,
    ),
    StrategyWorkflowSpec(
        workflow_id=AUTOMATIC_TREE_LEAF_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=False,
        requirements=_NO_REQUIREMENTS,
        template_ids=(AUTOMATIC_TREE_LEAF_TEMPLATE_ID,),
        validator=validate_automatic_tree_leaf_materialization_inputs,
        confirmation=automatic_tree_leaf_materialization_confirmation,
        preparer=prepare_automatic_tree_leaf_materialization,
    ),
    StrategyWorkflowSpec(
        workflow_id=INTERACTIVE_TREE_SPLIT_SEARCH_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(INTERACTIVE_TREE_SPLIT_SEARCH_TEMPLATE_ID,),
        validator=validate_interactive_tree_split_search_inputs,
        confirmation=interactive_tree_split_search_confirmation,
        preparer=prepare_interactive_tree_split_search,
    ),
    StrategyWorkflowSpec(
        workflow_id=INTERACTIVE_TREE_CONTINUATION_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(INTERACTIVE_TREE_CONTINUATION_TEMPLATE_ID,),
        validator=validate_interactive_tree_auto_continuation_inputs,
        confirmation=interactive_tree_auto_continuation_confirmation,
        preparer=prepare_interactive_tree_auto_continuation,
    ),
    StrategyWorkflowSpec(
        workflow_id=INTERACTIVE_TREE_REVISION_WORKFLOW_ID,
        fresh=True,
        replayable=True,
        manual=True,
        requirements=_NO_REQUIREMENTS,
        template_ids=(INTERACTIVE_TREE_REVISION_TEMPLATE_ID,),
        validator=validate_interactive_tree_revision_inputs,
        confirmation=interactive_tree_revision_confirmation,
        preparer=prepare_interactive_tree_revision,
    ),
)


__all__ = [
    "AUTOMATIC_TREE_APPLY_WORKFLOW_ID",
    "AUTOMATIC_TREE_BUILD_WORKFLOW_ID",
    "AUTOMATIC_TREE_DIRECTIONS",
    "AUTOMATIC_TREE_LEAF_WORKFLOW_ID",
    "INTERACTIVE_TREE_CONTINUATION_WORKFLOW_ID",
    "INTERACTIVE_TREE_REVISION_WORKFLOW_ID",
    "INTERACTIVE_TREE_SPLIT_SEARCH_WORKFLOW_ID",
    "TREE_WORKFLOW_SPECS",
    "automatic_tree_apply_confirmation",
    "automatic_tree_candidate_build_confirmation",
    "automatic_tree_leaf_materialization_confirmation",
    "interactive_tree_auto_continuation_confirmation",
    "interactive_tree_revision_confirmation",
    "interactive_tree_split_search_confirmation",
    "prepare_automatic_tree_apply",
    "prepare_automatic_tree_candidate_build",
    "prepare_automatic_tree_leaf_materialization",
    "prepare_interactive_tree_auto_continuation",
    "prepare_interactive_tree_revision",
    "prepare_interactive_tree_split_search",
    "validate_automatic_tree_apply_inputs",
    "validate_automatic_tree_candidate_build_inputs",
    "validate_automatic_tree_leaf_materialization_inputs",
    "validate_interactive_tree_auto_continuation_inputs",
    "validate_interactive_tree_revision_inputs",
    "validate_interactive_tree_split_search_inputs",
]
