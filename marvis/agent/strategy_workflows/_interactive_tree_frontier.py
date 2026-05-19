from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any
import unicodedata

from .contracts import (
    PreparedStrategyPlan,
    StrategyWorkflowPreparationContext,
    StrategyWorkflowResolutionContext,
    StrategyWorkflowValidationError,
    deep_freeze,
    deep_thaw,
)


SINGLETON_WORKFLOW_ID = "interactive_tree_frontier_materialization"
SINGLETON_TEMPLATE_ID = "strategy_interactive_tree_frontier_materialization"
GROUP_WORKFLOW_ID = "interactive_tree_frontier_group_materialization"
GROUP_TEMPLATE_ID = "strategy_interactive_tree_frontier_group_materialization"
_REVISION_ID_RE = re.compile(r"interactive-tree-revision-[0-9a-f]{32}")
_NODE_ID_RE = re.compile(r"(?:node|leaf)-[0-9a-f]{20}")


def validate_interactive_tree_frontier_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    allowed = {"revision_id", "source_node_id", "selection_reason"}
    unexpected = sorted(set(inputs) - allowed)
    if unexpected:
        raise StrategyWorkflowValidationError(
            f"{SINGLETON_WORKFLOW_ID} workflow_inputs Contains unsupported fields:"
            + ",".join(unexpected)
            + ".",
            fields=unexpected,
        )
    missing = sorted({"revision_id", "source_node_id"} - set(inputs))
    if missing:
        raise StrategyWorkflowValidationError(
            f"{SINGLETON_WORKFLOW_ID} Missing field:" + ",".join(missing) + ".",
            fields=missing,
        )
    revision_id = _required_text(
        inputs["revision_id"],
        name="revision_id",
        workflow_id=SINGLETON_WORKFLOW_ID,
    )
    if _REVISION_ID_RE.fullmatch(revision_id) is None:
        raise StrategyWorkflowValidationError(
            f"{SINGLETON_WORKFLOW_ID} revision_id It must be."
            "interactive-tree-revision- is followed by 32-bit lowercase hexadecimal characters.",
            fields=("revision_id",),
        )
    source_node_id = _required_text(
        inputs["source_node_id"],
        name="source_node_id",
        workflow_id=SINGLETON_WORKFLOW_ID,
    )
    if _NODE_ID_RE.fullmatch(source_node_id) is None:
        raise StrategyWorkflowValidationError(
            f"{SINGLETON_WORKFLOW_ID} source_node_id It must be.node- orleaf- "
            "followed by 20-bit lowercase hexadecimal characters.",
            fields=("source_node_id",),
        )
    normalized = {
        "revision_id": revision_id,
        "source_node_id": source_node_id,
    }
    if "selection_reason" in inputs:
        normalized["selection_reason"] = _selection_reason(
            inputs["selection_reason"],
            workflow_id=SINGLETON_WORKFLOW_ID,
        )
    return normalized


def interactive_tree_frontier_confirmation(inputs: Mapping[str, Any]) -> str:
    details = [
        "Recognized as [interactive tree frontier precision]Workflow〕",
        f"It's not gonna change.revision pointer:{inputs['revision_id']}",
        f"Precisionfrontier node/leaf pointer:{inputs['source_node_id']}",
        "Platform will be from the currenttask Only Restore and Authenticaterevision artifact,Full parent chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father, full father, full father, full father, full father, full father chain, full father chain, full father, full father, full father, full father, full father, full father, full family, full family, full family,"
        "Original Autotree and Determinationcandidate fragment",
        "This step only createssingleton pointer,Do Not Copycondition,metrics or business actions;"
        "I won't join you.Strategy Pool,I'm not going to accept, deploy, or write back.",
    ]
    if "selection_reason" in inputs:
        details.append(f"User selection statement:{inputs['selection_reason']}")
    return ";".join(details)


def prepare_interactive_tree_frontier(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    return PreparedStrategyPlan(
        workflow_id=SINGLETON_WORKFLOW_ID,
        template_id=SINGLETON_TEMPLATE_ID,
        slots=deep_freeze(deep_thaw(inputs)),
    )


def validate_interactive_tree_frontier_group_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    allowed = {"revision_id", "source_node_ids", "selection_reason"}
    unexpected = sorted(set(inputs) - allowed)
    if unexpected:
        raise StrategyWorkflowValidationError(
            f"{GROUP_WORKFLOW_ID} workflow_inputs Contains unsupported fields:"
            + ",".join(unexpected)
            + ".",
            fields=unexpected,
        )
    missing = sorted({"revision_id", "source_node_ids"} - set(inputs))
    if missing:
        raise StrategyWorkflowValidationError(
            f"{GROUP_WORKFLOW_ID} Missing field:" + ",".join(missing) + ".",
            fields=missing,
        )
    revision_id = _required_text(
        inputs["revision_id"],
        name="revision_id",
        workflow_id=GROUP_WORKFLOW_ID,
    )
    if _REVISION_ID_RE.fullmatch(revision_id) is None:
        raise StrategyWorkflowValidationError(
            f"{GROUP_WORKFLOW_ID} revision_id It must be."
            "interactive-tree-revision- is followed by 32-bit lowercase hexadecimal characters.",
            fields=("revision_id",),
        )
    raw_node_ids = inputs["source_node_ids"]
    if not isinstance(raw_node_ids, list):
        raise StrategyWorkflowValidationError(
            f"{GROUP_WORKFLOW_ID} source_node_ids It must be an array.",
            fields=("source_node_ids",),
        )
    if not 2 <= len(raw_node_ids) <= 50:
        raise StrategyWorkflowValidationError(
            f"{GROUP_WORKFLOW_ID} source_node_ids Must contain 2 to 50 full nodesID.",
            fields=("source_node_ids",),
        )
    source_node_ids = [
        _required_text(
            value,
            name=f"source_node_ids[{index}]",
            workflow_id=GROUP_WORKFLOW_ID,
        )
        for index, value in enumerate(raw_node_ids)
    ]
    for index, source_node_id in enumerate(source_node_ids):
        if _NODE_ID_RE.fullmatch(source_node_id) is None:
            raise StrategyWorkflowValidationError(
                f"{GROUP_WORKFLOW_ID} source_node_ids[{index}] It must be.node- or"
                "leaf- followed by 20-bit lowercase hexadecimal characters.",
                fields=("source_node_ids",),
            )
    if len(source_node_ids) != len(set(source_node_ids)):
        raise StrategyWorkflowValidationError(
            f"{GROUP_WORKFLOW_ID} source_node_ids Cannot contain repeat nodesID.",
            fields=("source_node_ids",),
        )
    normalized: dict[str, Any] = {
        "revision_id": revision_id,
        "source_node_ids": source_node_ids,
    }
    if "selection_reason" in inputs:
        normalized["selection_reason"] = _selection_reason(
            inputs["selection_reason"],
            workflow_id=GROUP_WORKFLOW_ID,
        )
    return normalized


def interactive_tree_frontier_group_confirmation(
    inputs: Mapping[str, Any],
) -> str:
    details = [
        "Recognized as [interactive tree front visible]OR Grouping for objectizationWorkflow〕",
        f"It's not gonna change.revision pointer:{inputs['revision_id']}",
        "Precisionfrontier node/leaf pointers:"
        + ",".join(inputs["source_node_ids"]),
        "Combination syntax: Hit by any member (OR);The order of membership is not semantic and the platform will press"
        " revision frontier Order Normalization",
        "Platform will be from the currenttask Only Restore and Authenticaterevision artifact,Full parent chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father chain, full father, full father, full father, full father, full father, full father chain, full father chain, full father, full father, full father, full father, full father, full father, full family, full family, full family,"
        "Original Autotrees with All Memberscandidate fragment",
        "This step only createspointer-only OR group,Do Not Copycondition,metrics "
        "or business actions;do not joinStrategy Pool,It's not applied, adopted, deployed or written back.",
    ]
    if "selection_reason" in inputs:
        details.append(f"User selection statement:{inputs['selection_reason']}")
    return ";".join(details)


def prepare_interactive_tree_frontier_group(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    return PreparedStrategyPlan(
        workflow_id=GROUP_WORKFLOW_ID,
        template_id=GROUP_TEMPLATE_ID,
        slots=deep_freeze(deep_thaw(inputs)),
    )


def _required_text(value: object, *, name: str, workflow_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrategyWorkflowValidationError(
            f"{workflow_id} {name} It must be non-empty.",
            fields=(name,),
        )
    return value.strip()


def _selection_reason(value: object, *, workflow_id: str) -> str:
    if not isinstance(value, str):
        raise StrategyWorkflowValidationError(
            f"{workflow_id} selection_reason It must be text.",
            fields=("selection_reason",),
        )
    if "\x00" in value:
        raise StrategyWorkflowValidationError(
            f"{workflow_id} selection_reason Can not get folder: %s: %sNUL.",
            fields=("selection_reason",),
        )
    canonical = " ".join(unicodedata.normalize("NFC", value).split())
    if not canonical or len(canonical) > 500:
        raise StrategyWorkflowValidationError(
            f"{workflow_id} selection_reason Must be an empty text of between 1 and 500 characters.",
            fields=("selection_reason",),
        )
    return canonical


__all__ = [
    "GROUP_TEMPLATE_ID",
    "GROUP_WORKFLOW_ID",
    "SINGLETON_TEMPLATE_ID",
    "SINGLETON_WORKFLOW_ID",
    "interactive_tree_frontier_confirmation",
    "interactive_tree_frontier_group_confirmation",
    "prepare_interactive_tree_frontier",
    "prepare_interactive_tree_frontier_group",
    "validate_interactive_tree_frontier_group_inputs",
    "validate_interactive_tree_frontier_inputs",
]
