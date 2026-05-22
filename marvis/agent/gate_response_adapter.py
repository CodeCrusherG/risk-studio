"""Gate response validation for PlanDriver.

This module owns the gate-control contract: structured UI/AUTO controls must be
bound to the current awaiting gate, and each control family may only operate on
gates whose dependency outputs can actually be recomputed.
"""

from __future__ import annotations

from marvis.agent.adjust_specs import (
    has_feature_binning_adjust,
    has_special_value_adjust,
    has_modeling_setup_adjust,
    has_join_key_adjust,
    has_screen_adjust,
    has_select_adjust,
    has_split_adjust,
    has_tuning_adjust,
)
from marvis.agent.plan_utils import gate_depends_on_tool
from marvis.orchestrator.contracts import Plan, PlanStep
from marvis.strategy_adoption import AdoptionReasonError, normalize_adoption_reason


class GateControlValidationError(Exception):
    pass


_STRUCTURED_DEDUP_STRATEGIES = frozenset({"first", "last"})
_ADOPTION_REASON_PARAM = "adoption_reason"
_MONITORING_DISPOSITION_PARAMS = frozenset(
    {"disposition", "reason", "threshold_patch"}
)


def validate_gate_control(
    plan: Plan,
    gate: PlanStep | None,
    *,
    expected_step_id: str | None,
    selection,
    dedup_strategies,
    adjust_params,
) -> None:
    if expected_step_id:
        if gate is None or gate.id != str(expected_step_id):
            raise GateControlValidationError("The current step to be confirmed has changed and please use the latest step control as updated.")
    screen_adjust = has_screen_adjust(adjust_params)
    select_adjust = has_select_adjust(adjust_params)
    modeling_setup_adjust = has_modeling_setup_adjust(adjust_params)
    tuning_adjust = has_tuning_adjust(adjust_params)
    split_adjust = has_split_adjust(adjust_params)
    join_key_adjust = has_join_key_adjust(adjust_params)
    feature_binning_adjust = has_feature_binning_adjust(adjust_params)
    special_value_adjust = has_special_value_adjust(adjust_params)
    adoption_reason_adjust = bool(
        isinstance(adjust_params, dict)
        and _ADOPTION_REASON_PARAM in adjust_params
    )
    monitoring_adjust = bool(
        isinstance(adjust_params, dict)
        and adjust_params
        and (
            bool(set(adjust_params) & _MONITORING_DISPOSITION_PARAMS)
            or (
                gate is not None
                and gate.tool_ref is not None
                and gate.tool_ref.tool == "apply_monitoring_disposition"
            )
        )
    )
    dedup_adjust = bool(dedup_strategies)
    if (
        selection is None
        and not dedup_adjust
        and not screen_adjust
        and not select_adjust
        and not modeling_setup_adjust
        and not tuning_adjust
        and not split_adjust
        and not adoption_reason_adjust
        and not monitoring_adjust
        and not join_key_adjust
        and not feature_binning_adjust
        and not special_value_adjust
    ):
        return
    if gate is None:
        raise GateControlValidationError("There are no steps to be confirmed at this time, and the control cannot be applied.")
    if not expected_step_id:
        raise GateControlValidationError("Please refresh and try again if this control lacks information to confirm the steps.")
    if adoption_reason_adjust:
        if gate.tool_ref is None or gate.tool_ref.tool != "adopt_strategy":
            raise GateControlValidationError("The reason control is only applicable to the adoption of a tactical confirmation step.")
        if set(adjust_params or {}) != {_ADOPTION_REASON_PARAM}:
            raise GateControlValidationError("Reason control can only be modifiedadoption_reason.")
        try:
            normalize_adoption_reason((adjust_params or {}).get(_ADOPTION_REASON_PARAM))
        except AdoptionReasonError as exc:
            raise GateControlValidationError(str(exc)) from exc
    if monitoring_adjust:
        if gate.tool_ref is None or gate.tool_ref.tool != "apply_monitoring_disposition":
            raise GateControlValidationError(
                "Controlled disposal controls only apply to the control result disposal confirmation steps."
            )
        unexpected = sorted(set(adjust_params or {}) - _MONITORING_DISPOSITION_PARAMS)
        if unexpected:
            raise GateControlValidationError(
                "Controlled disposal controls cannot be modified to freezeplan/run/strategy Evidence."
            )
    if (selection is not None or screen_adjust) and not gate_depends_on_tool(plan, gate, "screen_features"):
        raise GateControlValidationError("This control only applies to the feature screening confirmation step.")
    if select_adjust and not gate_depends_on_tool(plan, gate, "select_features"):
        raise GateControlValidationError("This control only applies to the preferred feature identification step.")
    if dedup_adjust and not gate_depends_on_tool(plan, gate, "confirm_join"):
        raise GateControlValidationError("This control only applies to the spell to reconfirm the step.")
    if dedup_adjust:
        invalid = sorted({
            str(value)
            for value in (dedup_strategies or {}).values()
            if str(value).strip() not in _STRUCTURED_DEDUP_STRATEGIES
        })
        if invalid:
            raise GateControlValidationError(
                f"Unsupported de-graving strategy: {', '.join(invalid)};Please usefirst orlast."
            )
    if join_key_adjust and not gate_depends_on_tool(plan, gate, "propose_join"):
        raise GateControlValidationError("Spell key control only applies to the spell diagnostic confirmation step.")
    if feature_binning_adjust and gate.tool_ref.tool != "analyze_feature_bins":
        raise GateControlValidationError("The box-separation controls only apply to the optional box analysis steps.")
    if special_value_adjust and (
        gate.tool_ref is None or gate.tool_ref.tool != "resolve_special_values"
    ):
        raise GateControlValidationError("Special value governance controls apply only to special value governance steps.")
    if modeling_setup_adjust and not gate_depends_on_tool(plan, gate, "choose_modeling_spec"):
        raise GateControlValidationError("The control only applies to the confirmation steps of the modeling specification.")
    if split_adjust and not gate_depends_on_tool(plan, gate, "make_split"):
        raise GateControlValidationError("The control only applies to the sample cut confirmation step.")
    if tuning_adjust and not (
        gate_depends_on_tool(plan, gate, "choose_modeling_spec")
        or gate_depends_on_tool(plan, gate, "tune_hyperparameters")
    ):
        raise GateControlValidationError("The control only applies to model specifications or to the reference confirmation steps.")


__all__ = ["GateControlValidationError", "validate_gate_control"]
