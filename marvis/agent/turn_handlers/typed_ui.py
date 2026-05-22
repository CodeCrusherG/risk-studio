"""typed_ui driver-turn handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
import sqlite3
from marvis.agent.join_setup import AuthenticatedJoinSelection, C1TargetValidationError
from marvis.agent.plan_driver import DriverError, confirmation_is_explicitly_withheld
from marvis.agent.strategy_workflows import MANUAL_STANDARD_STRATEGY_WORKFLOWS
from marvis.data.registry import DatasetRegistry
from marvis.repositories.tasks import TaskRepository
from marvis.domain import TaskRecord
from marvis.orchestrator.contracts import Plan, PlanStatus, StepStatus, plan_fingerprint, plan_step_confirmation_fingerprint
from marvis.packs.strategy.errors import StrategyError
from marvis.packs.strategy.sample_design_binding import StrategySampleDesignRef

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import DriverTurnRuntime
    from . import _STRATEGY_SAMPLE_BOUND_TOOLS
    from . import _TERMINAL_PLAN_STATUS_VALUES
    from . import _TurnHandlerSpec
    from . import append_driver_messages

def _validate_typed_ui_action_target(
    plan: Plan | None,
    *,
    ui_action: str | None,
    user_text: str | None,
    expected_plan_id: str | None,
    expected_step_id: str | None,
    expected_plan_status: str | None,
    expected_plan_revision: int | None,
    expected_plan_fingerprint: str | None,
    expected_step_fingerprint: str | None,
) -> None:
    """Fail closed when a rendered authorization control is stale.

    This executes inside the task's driver-job lock and before any success audit
    message is persisted. A plan id alone is insufficient for ``start_plan``:
    the same plan may already have advanced to a per-step gate in another tab.
    """

    plan_actions = {
        "start_plan",
        "confirm_dedup",
        "apply_join_keys",
        "exclude_join_feature",
        "confirm_features",
        "adjust_screen_thresholds",
        "confirm_feature_binning",
        "apply_modeling_setup",
        "confirm_adoption",
        "confirm_gate",
    }
    if ui_action not in plan_actions:
        return
    if confirmation_is_explicitly_withheld(user_text or ""):
        raise DriverError("Interface operation conflicts with a stop or suspend command, and please refresh and re-select.")
    # The action enum is the authorization signal.  ``user_text`` is only the
    # localized audit/display copy and may legitimately describe an adjustment
    # (for example (Rediagnosing Script Keys"or (Adjust Modeling Specifications...)).  Requiring a magic
    # confirmation word here would make genuine rendered controls unusable.
    rendered_plan_id = str(expected_plan_id or "").strip()
    if plan is None or not rendered_plan_id or rendered_plan_id != plan.id:
        raise DriverError("This operation has changed its plan, so please try again after you have refreshed the page.")
    if (
        expected_plan_status is None
        or expected_plan_revision is None
        or expected_plan_fingerprint is None
    ):
        raise DriverError("This operation lacks a complete plan snapshot, so please refresh the page and try again.")
    plan_status = PlanStatus(getattr(plan.status, "value", plan.status))
    if str(expected_plan_status) != plan_status.value:
        raise DriverError("This operation has changed its planned status, so please refresh the page and try again.")
    if int(expected_plan_revision) != int(plan.replan_count):
        raise DriverError("The corresponding plan version has changed, so please try again after you have refreshed the page.")
    if str(expected_plan_fingerprint) != plan_fingerprint(plan):
        raise DriverError("This operation has changed the plan content. Please try again after you have refreshed the page.")
    if ui_action == "start_plan":
        if plan_status != PlanStatus.VALIDATED:
            raise DriverError("This start button has expired, please update the page and run the current step.")
        return
    if plan_status != PlanStatus.AWAITING_CONFIRM:
        raise DriverError("This confirmation button is expired, please update the page and run the current step.")
    rendered_step_id = str(expected_step_id or "").strip()
    current_gate = next(
        (
            step
            for step in plan.steps
            if getattr(step.status, "value", step.status)
            == StepStatus.AWAITING_CONFIRM.value
        ),
        None,
    )
    if (
        current_gate is None
        or not rendered_step_id
        or rendered_step_id != current_gate.id
    ):
        raise DriverError("This confirmation button has changed the corresponding step, so please refresh the page and try again.")
    if expected_step_fingerprint is None:
        raise DriverError("This operation lacks a complete step snapshot, so please refresh the page and try again.")
    if str(expected_step_fingerprint) != plan_step_confirmation_fingerprint(
        current_gate,
        confirmed=False,
    ):
        raise DriverError("This confirmation button has changed the content of the corresponding steps, and please refresh the page and try again.")
    gate_tool = current_gate.tool_ref.tool
    dependency_tools = {
        step.tool_ref.tool
        for step in plan.steps
        if step.id in set(current_gate.depends_on or [])
    }
    action_matches_gate = {
        "confirm_dedup": (
            gate_tool == "execute_join" and "confirm_join" in dependency_tools
        ),
        "apply_join_keys": (
            gate_tool == "execute_join" and "propose_join" in dependency_tools
        ),
        "exclude_join_feature": (
            gate_tool == "execute_join" and "propose_join" in dependency_tools
        ),
        "confirm_features": "screen_features" in dependency_tools,
        "adjust_screen_thresholds": "screen_features" in dependency_tools,
        "confirm_feature_binning": gate_tool == "analyze_feature_bins",
        "apply_modeling_setup": (
            gate_tool == "screen_features"
            and "choose_modeling_spec" in dependency_tools
        ),
        "confirm_adoption": "adoption_reason" in (current_gate.inputs or {}),
    }
    if ui_action in action_matches_gate and not action_matches_gate[ui_action]:
        raise DriverError("This interface does not match the current steps to be confirmed. Please try again after you have a new page.")

def _append_successful_ui_action_messages(
    spec: _TurnHandlerSpec,
    repo: TaskRepository,
    task: TaskRecord,
    *,
    user_text: str | None,
    ui_action: str | None,
    expected_plan_id: str | None,
    expected_step_id: str | None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Persist UI authorization evidence only after the command succeeds."""

    if user_text is None or not ui_action:
        return
    message_metadata: dict[str, object] = {
        "intent": spec.intent,
        "ui_action": ui_action,
        "display_in_timeline": False,
    }
    if expected_plan_id:
        message_metadata["expected_plan_id"] = expected_plan_id
    if expected_step_id:
        message_metadata["expected_step_id"] = expected_step_id
    def add_message(**kwargs) -> None:
        if conn is None:
            repo.add_agent_message(task.id, **kwargs)
        else:
            repo.add_agent_message_on_connection(conn, task.id, **kwargs)
    add_message(
        role="user",
        stage="chat",
        content=spec.format_user_display(user_text),
        metadata=message_metadata,
    )
    acknowledgements = {
        "confirm_roles": "The role and target line is confirmed and the implementation plan is initiated.",
        "confirm_dedup": "We're getting a red tape confirmation and we're starting to get the fusion.",
        "apply_join_keys": "A spell key selection is received and the solution is being rediagnosed.",
        "exclude_join_feature": "The feature table was received to exclude adjustments and re-diagnosticization of the fusion is under way.",
        "confirm_features": "The next step is to begin with the signature selection confirmation.",
        "adjust_screen_thresholds": "Checking threshold adjustments received, and recalculation is ongoing.",
        "confirm_feature_binning": "The selection of the boxes was received and the production of the results and the characterization analysis of the boxes was initiated.",
        "apply_modeling_setup": "Received the modelling settings and started recalculating the next steps.",
        "confirm_adoption": "The acceptance confirmation was received, the reasons were initially tied and the audit records generated.",
        "confirm_gate": "We have confirmation that we are beginning to move on.",
        "start_plan": "Confirmed, implementation started as planned.",
    }
    acknowledgement_metadata: dict[str, object] = {
        "intent": "ui_action_ack",
        "ui_action": ui_action,
    }
    if expected_plan_id:
        acknowledgement_metadata["expected_plan_id"] = expected_plan_id
    if expected_step_id:
        acknowledgement_metadata["expected_step_id"] = expected_step_id
    add_message(
        role="assistant",
        stage="chat",
        content=acknowledgements.get(ui_action, "We have confirmation that we are beginning to move on."),
        metadata=acknowledgement_metadata,
    )

def _terminate_stale_strategy_sample_plan(
    spec: _TurnHandlerSpec,
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    plan: Plan,
) -> dict | None:
    """Fail closed before resuming pre-sample-binding strategy plans.

    V2 plans are serialized, so a plan created before sample-design binding can
    outlive a deployment and otherwise resume directly into a data-reading Tool.
    Only unfinished sample-bound steps are migration-sensitive: completed
    historical evidence remains readable, while newly compiled plans carry an
    exact authenticated development-partition reference and resume unchanged.
    """

    if spec.intent != "strategy":
        return None
    stale_steps = _stale_strategy_sample_steps(plan)
    if not stale_steps:
        return None

    current_status = PlanStatus(getattr(plan.status, "value", plan.status))
    if current_status in {
        PlanStatus.DRAFT,
        PlanStatus.VALIDATED,
        PlanStatus.RUNNING,
        PlanStatus.REVIEW,
    }:
        terminal_status = PlanStatus.FAILED
    elif current_status in {
        PlanStatus.CONFIRMED,
        PlanStatus.AWAITING_CONFIRM,
    }:
        # These states cannot legally transition directly to FAILED. CANCELLED
        # is their governed terminal path and prevents any Tool invocation.
        terminal_status = PlanStatus.CANCELLED
    else:
        return None

    runtime.plan_repo.set_plan_status(plan.id, terminal_status)
    stale_step_payload = [
        {
            "step_id": step.id,
            "tool": step.tool_ref.tool,
            "step_status": getattr(step.status, "value", step.status),
        }
        for step in stale_steps
    ]
    runtime.plan_repo.write_audit(
        kind="strategy.plan.sample_design_stale",
        target_ref=plan.id,
        outcome="blocked",
        detail={
            "task_id": task.id,
            "template_id": plan.template_id,
            "from_status": current_status.value,
            "to_status": terminal_status.value,
            "clarification_code": "strategy_plan_sample_design_stale",
            "stale_steps": stale_step_payload,
        },
    )
    message = (
        "The policy plan was created from the old version, and the incomplete data analysis or retrospect steps were not designed to bind the current mature sample"
        "Precisionsample_design_ref.The platform has safely terminated the old plan and has not called upon any analytical tools."
        "Please confirm the current mature sample design and re-launch the strategy request based on that design; the platform will be re-established."
    )
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=message,
        metadata={
            "intent": "strategy",
            "kind": "clarification",
            "code": "strategy_plan_sample_design_stale",
            "plan_id": plan.id,
            "template_id": plan.template_id,
            "plan_status": terminal_status.value,
            "stale_steps": stale_step_payload,
        },
    )
    return {
        "task_id": task.id,
        "status": "clarification_required",
        "code": "strategy_plan_sample_design_stale",
        "plan_id": plan.id,
        "plan_status": terminal_status.value,
        "messages": repo.list_agent_messages(task.id),
    }

def _stale_strategy_sample_steps(plan: Plan) -> list:
    status = getattr(plan.status, "value", plan.status)
    if status in _TERMINAL_PLAN_STATUS_VALUES:
        return []
    stale_steps = []
    for step in plan.steps:
        step_status = getattr(step.status, "value", step.status)
        if step_status in {StepStatus.DONE.value, StepStatus.SKIPPED.value}:
            continue
        if (
            step.tool_ref.plugin != "strategy"
            or step.tool_ref.tool not in _STRATEGY_SAMPLE_BOUND_TOOLS
        ):
            continue
        try:
            StrategySampleDesignRef.from_value(
                step.inputs.get("sample_design_ref")
            )
        except StrategyError:
            stale_steps.append(step)
    return stale_steps

def _append_spec_messages(
    repo: TaskRepository,
    task: TaskRecord,
    turn,
    runtime: DriverTurnRuntime,
) -> None:
    append_driver_messages(repo, task, turn, runtime=runtime)

def _identity_display_text(user_text: str) -> str:
    return user_text

def _validated_authenticated_c1_target(
    registry: DatasetRegistry,
    selection: AuthenticatedJoinSelection,
    target_col: object,
) -> str | None:
    """Bind a submitted target to the schema of the authenticated anchor bytes."""

    normalized = str(target_col or "").strip() or None
    if normalized is None:
        return None
    anchor_columns = set(
        registry.authenticated_binding_column_names(selection.anchor)
    )
    if normalized in anchor_columns:
        return normalized
    feature_only = any(
        normalized
        in set(registry.authenticated_binding_column_names(binding))
        for binding in selection.features
    )
    if feature_only:
        raise C1TargetValidationError(
            f"Target column`{normalized}` Only in the feature table; target columns must be from the current sample master table."
        )
    raise C1TargetValidationError(
        f"Target column`{normalized}` Does not exist in the current sample master table; please re-select."
    )

_TYPED_EVALUATION_OPERATIONS = frozenset({"analyze", "backtest"})

_STORED_EVALUATION_OPERATIONS = frozenset({"analyze", "backtest", "compare"})

_MANUAL_STRATEGY_WORKFLOWS = frozenset(MANUAL_STANDARD_STRATEGY_WORKFLOWS)

def _auto_decision_content(decision: dict) -> str:
    reason = str(decision.get("reason") or "").strip() or "Automatic decision-making is generated."
    action = decision.get("action")
    if action == "clarify" and decision.get("clarifying_question"):
        return f"🤖 {reason}\n\nNeed to be confirmed:{decision['clarifying_question']}"
    if action == "replan" and decision.get("replan_goal"):
        return f"🤖 {reason}\n\nRe-programming objectives:{decision['replan_goal']}"
    # LT-11 (B.3): when AUTO auto-confirms a low-risk gate, append the "why safe"
    # rationale (_apply_safety_policy attached it because no risk flag / wide reset
    # fired) so the auto-confirm explains itself. A halt already cites the specific
    # risk_flag code in its reason (from _gate_risk_reason), so no extra line there.
    rationale = str(decision.get("safety_rationale") or "").strip()
    if action == "confirm" and rationale:
        return f"🤖 {reason}\n\nWhy do you automatically confirm?:{rationale}"
    return f"🤖 {reason}"
