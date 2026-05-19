from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import (
    PreparedStrategyPlan,
    StrategyWorkflowPreparationContext,
    StrategyWorkflowResolutionContext,
    StrategyWorkflowValidationError,
    deep_freeze,
    deep_thaw,
)


WORKFLOW_ID = "strategy_model_score_comparison_v2"
_INPUT_FIELDS = frozenset({"population", "partition"})
_BINDING_FIELDS = frozenset(
    {
        "sample_design_ref",
        "model_score_evidence_refs",
        "expected_registry_token",
    }
)
_POPULATIONS = frozenset({"approval", "risk"})
_PARTITIONS = frozenset({"overall", "development", "validation", "oot"})


def validate_model_score_comparison_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, str]:
    unexpected = sorted(set(inputs) - _INPUT_FIELDS)
    missing = sorted(_INPUT_FIELDS - set(inputs))
    if unexpected:
        raise StrategyWorkflowValidationError(
            f"{WORKFLOW_ID} workflow_inputs Contains unsupported fields:"
            + ",".join(unexpected)
            + ".",
            fields=unexpected,
        )
    if missing:
        raise StrategyWorkflowValidationError(
            f"{WORKFLOW_ID} Missing field:" + ",".join(missing) + ".",
            fields=missing,
        )
    population = inputs["population"]
    partition = inputs["partition"]
    if not isinstance(population, str) or population not in _POPULATIONS:
        raise StrategyWorkflowValidationError(
            "population It's just...approval orrisk.",
            fields=("population",),
        )
    if not isinstance(partition, str) or partition not in _PARTITIONS:
        raise StrategyWorkflowValidationError(
            "partition It's just...overall,development,validation oroot.",
            fields=("partition",),
        )
    return {"population": population, "partition": partition}


def model_score_comparison_confirmation(inputs: Mapping[str, Any]) -> str:
    return ";".join(
        [
            "Recognized as [comparison evidence rated by the governance model]Workflow〕",
            f"Overall:{inputs['population']}",
            f"Division:{inputs['partition']}",
            "The platform will automatically bind up up-to-date and fully certified samples of current tasks to at least two model score evidence",
            "This step only consists of the materialization of the same comparative evidence, defaultno_selection,No winner.",
            "No model is adopted, no model is deployed",
            "Please confirm the above operating calibre.Agent Only trusted tools are organized; all numbers are calculated by the platform ' s certainty.",
        ]
    )


def prepare_model_score_comparison(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    if context.bind_model_score_comparison is None:
        raise StrategyWorkflowValidationError(
            "Model scoring requires at least two fully certified and compatible scoring evidence within the current task.",
            code="strategy_model_score_comparison_evidence_required",
        )
    thawed = deep_thaw(inputs)
    binding = context.bind_model_score_comparison(
        str(thawed["population"]),
        str(thawed["partition"]),
    )
    if not isinstance(binding, Mapping) or set(binding) != _BINDING_FIELDS:
        raise StrategyWorkflowValidationError(
            "The evidence of model scoring obtained by the Platform is incomplete.",
            code="strategy_model_score_comparison_binding_invalid",
        )
    return PreparedStrategyPlan(
        workflow_id=WORKFLOW_ID,
        template_id=WORKFLOW_ID,
        slots=deep_freeze({**deep_thaw(binding), **thawed}),
    )


__all__ = [
    "model_score_comparison_confirmation",
    "prepare_model_score_comparison",
    "validate_model_score_comparison_inputs",
]
