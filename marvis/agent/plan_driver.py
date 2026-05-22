"""Generic plan-conversation driver — one driver for all V2 task types.

(Original spec: v2-plan-driver-spec.md, archived at docs/history-archive.md.)
Given a task's template + filled slots,
the driver builds a plan, runs it on the real PlanExecutor, and at each
``needs_confirmation`` gate turns the *just-computed prior-step output* into an
append-only assistant message (with inline rich tables). The executor pauses
BEFORE the gate step, so what the user confirms is exactly what just ran.
Confirm resumes execution; task differences live in the template + the
tool->table registry below, not in the driver. This replaces the bespoke
``ModelingSession`` / ``modeling_agent`` prototype (decision #9 / #4).

The driver is deliberately pure-ish: it mutates plan state through the repo and
the executor, but it *returns* the assistant messages rather than persisting
them, so the API/job layer owns ``agent_messages`` and the driver stays unit
testable offline.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re

from marvis.agent.adjust_specs import (
    adjust_param_error,
    has_feature_binning_adjust,
    has_special_value_adjust,
    normalize_adjust_params,
)
from marvis.agent.driver_turn import DriverMessage, DriverTurn
from marvis.agent.gate_execution_adapter import (
    ACTION_OUTCOME_METADATA_KEY,
    ACTION_OUTCOME_REJECTED,
    GateExecutionAdapter,
)
from marvis.agent.gate_param_schema import gate_param_schema
from marvis.agent.gate_response_adapter import GateControlValidationError, validate_gate_control
from marvis.agent.gates.adapters import (
    GateReplyContext,
    gate_editable_input_schema,
    get_gate_adapter,
    monitoring_plain_confirm_error,
    parse_dedup_instruction as _parse_dedup_instruction,
    parse_monitoring_disposition as _parse_monitoring_disposition,
    parse_rule_selection_instruction as _parse_rule_selection_instruction,
)
from marvis.agent.instruction_router import route_instruction
from marvis.agent.plan_message_composer import PlanMessageComposer
from marvis.agent.plan_utils import find_step
from marvis.agent.renderers import render_tool_output
from marvis.agent.semantic_authorization import review_semantic_authorization
from marvis.data.backend import DataBackend
from marvis.data.registry import DatasetRegistry
from marvis.governance.errors import AuthorizationError
from marvis.modeling_limits import normalize_n_trials
from marvis.orchestrator.contracts import (
    Plan,
    PlanStatus,
    PlanStep,
    StepStatus,
    plan_fingerprint,
    plan_step_confirmation_fingerprint,
)
from marvis.orchestrator.templates import get_template
from marvis.repositories.datasets import DatasetRepository
from marvis.repositories.task_artifacts import TaskArtifactRepository
from marvis.state_machine import ConflictError
from marvis.strategy_adoption import AdoptionReasonError, normalize_adoption_reason

# A reply counts as confirmation of the current gate only when, after stripping
# whitespace/punctuation, the *entire* remaining text is made up of short affirmative
# values (see _CONFIRM_COMPACT_VALUES below). This exact-value boundary — rather
# than a substring `.search` or arbitrary affirmative-token concatenation — is
# what stops questions ((Is that okay?"), conditionals (("and continue as soon as you know it's okay.") and
# embedded affirmatives from being misread as confirmation (AGT-1 / H4).
_CONFIRM_COMPACT_VALUES = frozenset({
    "Okay.",
    "Okay.",
    "Yeah.",
    "Confirm.",
    "Sure.",
    "Sure.",
    "Agreed.",
    "That's it.",
    "Go on.",
    "Start",
    "Right.",
    "Yeah.",
    "Okay.",
    "ok",
    "okay",
    "yes",
    "y",
    "go",
    "proceed",
    "okGo on.",
    "okayGo on.",
    "Okay, go ahead.",
    "Okay, go on.",
    "You can go on.",
    "Confirm that you're going to continue.",
    "Agreed to proceed.",
    "No problem.",
})
_MODELING_RECIPE_DISPLAY_NAMES = {
    "lgb": "LightGBM",
    "xgb": "XGBoost",
    "catboost": "CatBoost",
    "lr": "Logical regression",
    "scorecard": "Scorecard",
    "mlp": "MLP",
    "lgb_regressor": "LightGBM((Return)",
    "xgb_regressor": "XGBoost((Return)",
    "lr_regressor": "Logical regression (return)",
    "mlp_regressor": "MLP((Return)",
    "lgb_multiclass": "LightGBM((a) Multi-category",
    "xgb_multiclass": "XGBoost((a) Multi-category",
    "lr_multiclass": "Logical regression (multi-category)",
    "mlp_multiclass": "MLP((a) Multi-category",
    "ensemble": "Integrated Model",
}
# Interrogative guard: any hard question mark/particle disqualifies a reply from
# being read as confirmation even if it also contains an affirmative token (e.g.
# (Is that okay?", (KS- Is it high? - It's on the zero..3# Is it true? #, (Can you do it?").
_QUESTION = re.compile(
    r"[??]|- You're not?|Okay?|Can I?|Can you...|Okay?|Right?|Isn't that right?|And?$",
    re.IGNORECASE,
)
_NEGATED_CONFIRM = re.compile(
    r"(Not yet.|Don't do it.|Don't go on.|Don't start.|Don't.|No, I'm fine.|No, I don't.|Not implemented|No more.|Not yet.|Not yet.|Pause|Stop|Cancel|"
    r"Do Not Start|Not confirmed|No, you can't.|hold on|do\s*not|don't|dont|not\s+(start|continue|proceed|go)|stop|cancel|wait)",
    re.IGNORECASE,
)
_EXPLICITLY_WITHHELD_CONFIRM = re.compile(
    r"(?:Not yet.|Not yet.|Not yet.|Don't.|Don't.)(?:Again.)?(?:Implementation|Go on.|Start|Confirm.|Apply|Submit|Run|Operation|Down(?:Do it.|Let's go.))"
    r"|(?:No, no.|No, it's not.)(?:Implementation|Go on.|Start|Confirm.|Agreed.|Delegation of authority|Apply|Submit|Run)"
    r"|(?:I'm...)?(?:Reject|I disagree.)(?:Implementation|Go on.|Start|Confirm.|Delegation of authority|Apply|Submit|Run|Operation)?"
    r"|(?:Pause|Stop)(?:Implementation|Go on.|Operation|Tasks|Process)(?:[.!!\s]|$)"
    r"|Cancel(?:Implementation|Operation|Tasks|Process)(?:[.!!\s]|$)"
    r"|^\s*(?:First)?(?:Pause|Stop|Cancel)(?:One second.)?\s*[.!!]*\s*$"
    r"|(?:We'll talk later.|Wait a minute.|Wait a minute.|Wait a minute.|Hold on.|Let's just put it down.|I'll continue later.|Reluctance of decision)"
    r"|\b(?:do\s*not|don't|dont)\s+(?:execute|continue|proceed|start|confirm|apply|submit|run)\b"
    r"|\b(?:not\s+now|i\s+(?:refuse|do\s+not\s+agree)\s+to\s+(?:execute|continue|proceed|start|confirm|apply|submit|run))\b"
    r"|^\s*(?:please\s+)?(?:pause|stop|cancel|hold\s+off|wait)\s*[.!]*\s*$",
    re.IGNORECASE,
)
_SEMANTIC_RECOMMENDATION_REFERENCE = re.compile(
    r"(?:Recommendations|Stars|Best|Best|Current Candidate)"
    r"|\b(?:recommended|starred|best|top[-\s]?ranked|current\s+candidate)\b",
    re.IGNORECASE,
)
_STRIP_PUNCT = re.compile(r"[\s,.!~;:'\"()\-]+")
CONFIRMATION_SOURCE_HUMAN = "human"
CONFIRMATION_SOURCE_AUTO = "auto"
_CONFIRMATION_SOURCES = frozenset({
    CONFIRMATION_SOURCE_HUMAN,
    CONFIRMATION_SOURCE_AUTO,
})


def is_confirm(text: str) -> bool:
    raw = text or ""
    compact = _STRIP_PUNCT.sub("", raw)
    if _QUESTION.search(raw):
        return False
    if _NEGATED_CONFIRM.search(raw):
        return False
    if not compact:
        return False
    if _NEGATED_CONFIRM.search(compact):
        return False
    # Any longer sentence, including one beginning with (Confirm), belongs to the
    # two-pass semantic route.  Keeping the deterministic path to exact values
    # prevents a context-free task command from confirming the wrong live gate.
    # Typed UI controls are canonicalized to an exact confirmation by the turn
    # handler after their plan/step optimistic-lock target has been validated.
    return compact.lower() in _CONFIRM_COMPACT_VALUES


def confirmation_is_explicitly_withheld(text: str) -> bool:
    """Detect text that directly contradicts a typed confirmation action."""

    raw = str(text or "")
    compact = _STRIP_PUNCT.sub("", raw)
    return bool(
        _EXPLICITLY_WITHHELD_CONFIRM.search(raw)
        or _EXPLICITLY_WITHHELD_CONFIRM.search(compact)
    )


def _candidate_alias_is_mentioned(text: str, alias: str) -> bool:
    candidate = str(alias or "").strip().casefold()
    if not candidate:
        return False
    haystack = str(text or "").casefold()
    if candidate.isascii():
        return bool(
            re.search(
                rf"(?<![a-z0-9_]){re.escape(candidate)}(?![a-z0-9_])",
                haystack,
            )
        )
    return candidate in haystack


def _candidate_selection_text_error(
    candidates: list[dict],
    *,
    recommended_id: str,
    selected_id: str,
    user_text: str,
) -> str | None:
    """Bind an LLM-selected id back to the candidate named by the human.

    Membership in the live candidate set is necessary but insufficient: a
    mistaken router could otherwise submit a valid LR id for a turn that says
    XGBoost.  Exact ids, unique recipe/display aliases, and the authenticated
    recommendation marker are the only grounding signals accepted here.
    """

    raw = str(user_text or "").strip()
    if not raw:
        return "Please re-select candidates who lack auditable user language."

    exact_matches = {
        str(row.get("experiment_id") or "").strip()
        for row in candidates
        if _candidate_alias_is_mentioned(raw, row.get("experiment_id"))
    }
    residual = raw
    for row in candidates:
        experiment_id = str(row.get("experiment_id") or "").strip()
        if experiment_id:
            residual = re.sub(
                re.escape(experiment_id),
                " ",
                residual,
                flags=re.IGNORECASE,
            )

    alias_matches: set[str] = set()
    for row in candidates:
        experiment_id = str(row.get("experiment_id") or "").strip()
        aliases = (row.get("recipe"), row.get("display_name"))
        if experiment_id and any(
            _candidate_alias_is_mentioned(residual, alias) for alias in aliases
        ):
            alias_matches.add(experiment_id)

    recommendation_referenced = bool(
        _SEMANTIC_RECOMMENDATION_REFERENCE.search(residual)
    )
    if exact_matches and exact_matches != {selected_id}:
        return "Experiments in User WordsID If this is not in line with the submitted candidate, please re-elect."
    if alias_matches and (
        selected_id not in alias_matches
        or (not exact_matches and alias_matches != {selected_id})
    ):
        return "The user name is not uniquely tied to the submission of a candidate. Please re-select."
    if recommendation_referenced and (
        not recommended_id or selected_id != recommended_id
    ):
        return "Users are requesting a recommended candidate, but the submitted candidate is not the current one."
    if exact_matches or alias_matches or recommendation_referenced:
        return None
    return "Please specify if you are unable to bind the original user to the submission candidate.ID,Algorithms or recommended entries."


def _has_adoption_reason_adjust(adjust_params) -> bool:
    return isinstance(adjust_params, dict) and "adoption_reason" in adjust_params


def _is_adoption_gate(gate: PlanStep | None) -> bool:
    return bool(
        gate is not None
        and gate.tool_ref is not None
        and gate.tool_ref.tool == "adopt_strategy"
    )


class DriverError(Exception):
    pass


def _reject_failed_trusted_ui_action(
    turn: DriverTurn,
    *,
    trusted_ui_action: bool,
) -> DriverTurn:
    """Raise when a rendered control reached a deterministic no-mutation result."""

    if not trusted_ui_action:
        return turn
    rejected = next(
        (
            message
            for message in turn.messages
            if (message.metadata or {}).get(ACTION_OUTCOME_METADATA_KEY)
            == ACTION_OUTCOME_REJECTED
        ),
        None,
    )
    if rejected is not None:
        raise DriverError(rejected.content)
    return turn


def _normalize_confirmation_source(value: str) -> str:
    source = str(value or "").strip().lower()
    if source not in _CONFIRMATION_SOURCES:
        raise DriverError("Confirm that the source is invalid and must be marked by the platformhuman orauto.")
    return source


def _assert_source_may_operate_gate(gate: PlanStep | None, source: str) -> None:
    if source != CONFIRMATION_SOURCE_AUTO or gate is None:
        return
    policy = getattr(gate, "policy", None)
    if getattr(policy, "human_decision_gate", "none") == "required":
        raise DriverError("AUTO The mandatory manual business decision node cannot be operated or confirmed and is to be continued manually.")


class PlanDriver:
    def __init__(
        self,
        plan_repo,
        executor,
        *,
        planner=None,
        validator=None,
        llm_client=None,
        allow_manual_gate_adapters=True,
        require_semantic_text_authorization=False,
        governance_service=None,
        local_principal=None,
        cancellation_check=None,
    ):
        self._repo = plan_repo
        self._executor = executor
        self._planner = planner
        self._validator = validator
        # Optional LLM for agent-mode free-text gate instructions (adjust / replan).
        # None in manual mode — non-confirm replies then show the canned hint.
        self._llm = llm_client
        self._allow_manual_gate_adapters = bool(allow_manual_gate_adapters)
        self._require_semantic_text_authorization = bool(
            require_semantic_text_authorization
        )
        self._governance = governance_service
        self._principal = local_principal
        self._cancellation_check = cancellation_check
        artifact_repo = (
            TaskArtifactRepository(self._repo.db_path)
            if getattr(self._repo, "db_path", None) is not None
            else None
        )
        workspace = (
            Path(self._repo.db_path).parent
            if artifact_repo is not None
            else None
        )
        dataset_registry = (
            DatasetRegistry(
                DatasetRepository(self._repo.db_path),
                DataBackend(workspace / "datasets"),
                workspace / "datasets",
            )
            if workspace is not None
            else None
        )
        self._composer = PlanMessageComposer(
            load_output=self._repo.load_step_output,
            load_step_evidence=(
                self._repo.load_step_evidence
                if getattr(self._repo, "load_step_evidence", None) is not None
                else None
            ),
            load_task_artifact=(
                artifact_repo.get_for_task if artifact_repo is not None else None
            ),
            load_dataset=(
                dataset_registry.get if dataset_registry is not None else None
            ),
            resolve_verified_dataset_path=(
                dataset_registry.resolve_verified_path
                if dataset_registry is not None
                else None
            ),
            tasks_root=(
                workspace / "tasks"
                if artifact_repo is not None
                else None
            ),
            db_path=(
                Path(self._repo.db_path)
                if artifact_repo is not None
                else None
            ),
            latest_failed_step_run_error_kind=self._latest_failed_step_run_error_kind,
        )
        self._gate_execution = GateExecutionAdapter(
            self._repo,
            self._executor,
            safe_output=self._safe_output,
            run_and_handle=self._run_and_handle,
            plan_overview_message=self._composer.plan_overview_message,
        )

    # -- entry points ---------------------------------------------------------
    def start(
        self,
        *,
        task_id,
        template_id,
        slots,
        autonomy=None,
        tier=None,
        run_seq=0,
        success_criteria=None,
        _persist_start_turn=None,
    ) -> DriverTurn:
        """Build the plan and show its overview, then PAUSE at the plan-level Startgate.

        Spec §9 #2 (Locked): both modes first show the whole plan and only run after the
        user confirms [Start. The plan is left VALIDATED — nothing executes until
        resume() receives the Startconfirm (the agent auto-driver feeds it in AUTO
        mode). This is what makes the first analysis step never run unprompted.

        ``success_criteria`` (optional, AGT-4): user/AUTO-supplied deterministic
        thresholds (e.g. [{"metric": "oot_ks", "min": 0.3, ...}]) layered on top of
        the template's own success_criteria (empty for the built-in modeling
        templates today). Only final_review's deterministic evaluation reads this —
        never a hard-coded platform default.
        """
        plan = self._prepare_plan(
            task_id=task_id,
            template_id=template_id,
            slots=slots,
            autonomy=autonomy,
            tier=tier,
            success_criteria=success_criteria,
        )
        turn = DriverTurn(
            plan.id,
            plan.status.value,
            [self._composer.plan_overview_message(plan)],
        )
        if _persist_start_turn is None:
            self._repo.create_plan(plan)
        else:
            self._repo.create_plan(
                plan,
                on_connection=lambda conn: _persist_start_turn(conn, turn),
            )
        return turn

    def resume(
        self,
        *,
        plan_id,
        user_text,
        run_seq=0,
        selection=None,
        dedup_strategies=None,
        adjust_params=None,
        expected_step_id=None,
        expected_plan_status=None,
        expected_plan_revision=None,
        expected_plan_fingerprint=None,
        expected_step_fingerprint=None,
        confirmation_source=CONFIRMATION_SOURCE_HUMAN,
        _confirmation_reason=None,
        _expected_plan_revision=None,
        _expected_plan_status=None,
        _expected_plan_fingerprint=None,
        _trusted_ui_action=False,
    ) -> DriverTurn:
        """Advance the plan given a user reply. Two gate kinds are handled: the
        plan-level overview gate (plan not yet started) and per-step gates.

        ``selection`` (optional): the user's edited feature set from the §4 interactive
        screening table. When confirming a gate that depends on a ``screen_features``
        step, it is persisted atomically as that gate's concrete ``features`` input so
        downstream steps use exactly the reviewed set. The completed Tool output and
        its exact run receipt remain immutable.

        ``dedup_strategies`` (optional): the user's per-feature dedup strategy map from
        the §4 join dedup picker. At a join gate it re-confirms the ``confirm_join``
        dependency with those strategies (resolving non-unique-key conflicts) and
        re-pauses at the gate, now clear, for the final execute confirm.

        ``adjust_params`` (optional): structured manual control overrides. Unlike
        free-text instructions, these do not require an LLM router.

        ``_confirmation_reason`` is an internal audit-only override used after a
        semantic authorization has already been classified.  Authorization still
        requires the canonical deterministic ``user_text`` confirmation path; this
        value can only preserve the original human wording in the decision record.

        ``_expected_plan_revision``, ``_expected_plan_status`` and
        ``_expected_plan_fingerprint`` bind that internal semantic authorization to
        the exact persisted plan snapshot reviewed by the second LLM call.  The
        fingerprint also detects same-id, same-revision gate input mutations.

        The public ``expected_*`` values bind a typed browser control to the
        exact plan and step snapshot that was rendered.  They are mandatory
        for ``_trusted_ui_action`` and are intentionally separate from the
        internal semantic-review snapshot above.
        """
        confirmation_source = _normalize_confirmation_source(confirmation_source)
        deterministic_confirmation_allowed = (
            not self._require_semantic_text_authorization
            or bool(_trusted_ui_action)
            or bool(_confirmation_reason)
            or confirmation_source == CONFIRMATION_SOURCE_AUTO
        )
        confirmed = deterministic_confirmation_allowed and is_confirm(user_text)
        confirmation_reason = str(_confirmation_reason or user_text or "").strip()
        plan = self._repo.load_plan(plan_id)
        if _trusted_ui_action:
            if (
                expected_plan_status is None
                or expected_plan_revision is None
                or expected_plan_fingerprint is None
            ):
                raise DriverError("This interface does not have a complete plan snapshot, so please refresh and try again.")
            if plan.status.value != str(expected_plan_status):
                raise DriverError("The interface operation has changed its planned status, and please refresh and try again.")
            if int(plan.replan_count) != int(expected_plan_revision):
                raise DriverError("The plan version of the interface operation has changed, and please refresh and try again.")
            if plan_fingerprint(plan) != str(expected_plan_fingerprint):
                raise DriverError("The interface operation has changed the plan content. Please refresh and try again.")
        if (
            _expected_plan_revision is not None
            and int(plan.replan_count) != int(_expected_plan_revision)
        ):
            raise DriverError("Please update and try again as the semantic version of the plan has changed during the review.")
        if (
            _expected_plan_status is not None
            and plan.status.value != str(_expected_plan_status)
        ):
            raise DriverError("Please update and try again as the status of the plan has changed during the semantic review.")
        if (
            _expected_plan_fingerprint is not None
            and plan_fingerprint(plan) != str(_expected_plan_fingerprint)
        ):
            raise DriverError("Please update and re-test the symmetrical plans during the review period.")
        # Plan-level overview gate: nothing has run yet → [Startbegins execution.
        if plan.status == PlanStatus.VALIDATED:
            if confirmed:
                try:
                    self._repo.confirm_plan(
                        plan_id,
                        expected_plan_fingerprint=plan_fingerprint(plan),
                    )
                except ConflictError as exc:
                    raise DriverError(
                        "The plan overview has changed before confirmation, and please refresh and retry."
                    ) from exc
                return self._run_and_handle(plan_id, run_seq=run_seq)
            return self._handle_instruction(
                plan,
                None,
                user_text,
                run_seq,
                confirmation_source,
            )
        # Per-step needs_confirmation gate.
        gate = self._awaiting_step(plan)
        if _trusted_ui_action:
            if gate is None or expected_step_fingerprint is None:
                raise DriverError("This interface operation lacks a complete step snapshot, so please refresh and try again.")
            if plan_step_confirmation_fingerprint(
                gate,
                confirmed=False,
            ) != str(expected_step_fingerprint):
                raise DriverError("The content of the steps for which this interface operates has changed, and please refresh and try again.")
        try:
            validate_gate_control(
                plan,
                gate,
                expected_step_id=expected_step_id,
                selection=selection,
                dedup_strategies=dedup_strategies,
                adjust_params=adjust_params,
            )
        except GateControlValidationError as exc:
            raise DriverError(str(exc)) from exc
        # Defense in depth: AUTO's decision layer normally halts before this
        # call.  The driver still owns the final confirmation boundary so a
        # direct/internal caller cannot bypass the canonical step policy.
        _assert_source_may_operate_gate(gate, confirmation_source)
        if (
            confirmation_source == CONFIRMATION_SOURCE_AUTO
            and gate is not None
            and self._requires_governed_human_decision(gate)
        ):
            raise DriverError("AUTO The mandatory manual business decision node cannot be operated or confirmed and is to be continued manually.")
        # Join dedup picker: re-confirm with the chosen strategies, then re-pause at the
        # (now conflict-free) gate — do NOT confirm-execute yet; the user confirms after.
        if dedup_strategies and gate is not None:
            try:
                self._gate_execution.apply_dedup_strategies(
                    plan,
                    gate,
                    dedup_strategies,
                )
            except ConflictError as exc:
                raise DriverError(
                    "Current confirmation nodes have changed before adjustment. Please refresh and try again."
                ) from exc
            return self._run_and_handle(plan_id, run_seq=run_seq)
        if (
            isinstance(adjust_params, dict)
            and set(adjust_params) == {"exclude_join_feature_id"}
            and gate is not None
        ):
            if not confirmed:
                raise DriverError("Clear interface authorization must be submitted when excluding the feature sheet.")
            try:
                turn = self._gate_execution.exclude_join_feature(
                    plan,
                    gate,
                    str(adjust_params["exclude_join_feature_id"]),
                    run_seq,
                )
            except ConflictError as exc:
                raise DriverError(
                    "Current confirmation nodes have changed before adjustment. Please refresh and try again."
                ) from exc
            return _reject_failed_trusted_ui_action(
                turn,
                trusted_ui_action=_trusted_ui_action,
            )
        if _has_adoption_reason_adjust(adjust_params) and gate is not None:
            if not confirmed:
                raise DriverError("The submission of reasons for acceptance must be accompanied by confirmation of acceptance.")
            adoption_reason = self._require_adoption_reason(
                (adjust_params or {}).get("adoption_reason")
            )
            self._confirm_gate(
                plan,
                gate,
                reason=adoption_reason,
                input_updates={"adoption_reason": adoption_reason},
            )
            return self._run_and_handle(plan_id, run_seq=run_seq)
        if (
            isinstance(adjust_params, dict)
            and "selected_experiment_id" in adjust_params
            and gate is not None
        ):
            if not confirmed:
                raise DriverError("Candidate experiments must be submitted with clear authorization.")
            selection_error = self._experiment_selection_adjust_error(
                plan,
                gate,
                adjust_params,
            )
            if selection_error:
                raise DriverError(selection_error)
            selected_id = str(adjust_params["selected_experiment_id"]).strip()
            self._confirm_gate(
                plan,
                gate,
                reason=confirmation_reason or f"Manual selection experiment{selected_id}",
                input_updates={"selected_experiment_id": selected_id},
            )
            return self._run_and_handle(plan_id, run_seq=run_seq)
        if has_feature_binning_adjust(adjust_params) and gate is not None:
            if not confirmed:
                raise DriverError("The box setting must be confirmed at the same time as the box setting is submitted.")
            params = {
                "features": list((adjust_params or {}).get("features") or []),
                "bins": (adjust_params or {}).get("bins", 10),
            }
            error = adjust_param_error(params) or self._feature_binning_adjust_error(
                plan, gate, params["features"]
            )
            if error:
                raise DriverError(error)
            self._confirm_gate(
                plan,
                gate,
                reason=(
                    f"Manual Selection{len(params['features'])} Each feature is going.{int(params['bins'])} Box analysis"
                    if params["features"]
                    else "Manual selection skips the box selection analysis"
                ),
                input_updates={"features": params["features"], "bins": int(params["bins"])},
            )
            return self._run_and_handle(plan_id, run_seq=run_seq)
        if has_special_value_adjust(adjust_params) and gate is not None:
            if not confirmed:
                raise DriverError("Special value governance strategies must be presented with simultaneous confirmation.")
            raw_decisions = (adjust_params or {}).get("decisions")
            error = adjust_param_error({"decisions": raw_decisions})
            if error:
                raise DriverError(error)
            decisions = dict(raw_decisions)
            error = self._special_value_adjust_error(
                plan,
                gate,
                decisions,
                selection=selection,
            )
            if error:
                raise DriverError(error)
            selection_updates = (
                self._gate_execution.screen_selection_input_updates(
                    plan,
                    gate,
                    selection,
                )
                if selection is not None
                else {}
            )
            self._confirm_gate(
                plan,
                gate,
                reason="Manual recognition of special value governance strategy",
                input_updates={**selection_updates, "decisions": decisions},
            )
            return self._run_and_handle(plan_id, run_seq=run_seq)
        if adjust_params and gate is not None:
            try:
                turn = self._gate_execution.apply_adjust(
                    plan,
                    gate,
                    adjust_params,
                    run_seq,
                )
            except ConflictError as exc:
                raise DriverError(
                    "Current confirmation nodes have changed before adjustment. Please refresh and try again."
                ) from exc
            return _reject_failed_trusted_ui_action(
                turn,
                trusted_ui_action=_trusted_ui_action,
            )
        if confirmed:
            if (
                gate is not None
                and gate.tool_ref is not None
                and gate.tool_ref.tool == "select_experiment"
            ):
                return DriverTurn(
                    plan.id,
                    plan.status.value,
                    [
                        self._composer.instruction_message(
                            plan,
                            gate,
                            run_seq=run_seq,
                            text=(
                                "The current node must clearly select a candidate experiment that has been demonstrated;"
                                "Please submit a selection using a candidate control, which cannot be confirmed and selected by the platform."
                            ),
                        )
                    ],
                )
            monitoring_error = monitoring_plain_confirm_error(
                plan,
                gate,
                self._safe_output,
            )
            if monitoring_error:
                return DriverTurn(
                    plan.id,
                    plan.status.value,
                    [
                        self._composer.instruction_message(
                            plan,
                            gate,
                            run_seq=run_seq,
                            text=monitoring_error,
                        )
                    ],
                )
            if gate is not None:
                if gate.tool_ref is not None and gate.tool_ref.tool == "resolve_special_values":
                    raw_decisions = (gate.inputs or {}).get("decisions")
                    decision_error = self._special_value_adjust_error(
                        plan,
                        gate,
                        dict(raw_decisions) if isinstance(raw_decisions, dict) else {},
                        selection=selection,
                    )
                    if decision_error:
                        raise DriverError(decision_error)
                selection_updates = (
                    self._gate_execution.screen_selection_input_updates(
                        plan,
                        gate,
                        selection,
                    )
                    if selection is not None
                    else {}
                )
                if _is_adoption_gate(gate):
                    adoption_reason = self._require_adoption_reason(
                        (gate.inputs or {}).get("adoption_reason")
                    )
                    self._confirm_gate(
                        plan,
                        gate,
                        reason=adoption_reason,
                        input_updates={
                            **selection_updates,
                            "adoption_reason": adoption_reason,
                        },
                    )
                else:
                    confirmation_updates = dict(selection_updates)
                    if (
                        gate.tool_ref.tool == "apply_monitoring_disposition"
                        and not str((gate.inputs or {}).get("reason") or "").strip()
                    ):
                        confirmation_updates["reason"] = (
                            confirmation_reason or "Manually confirm the results of this surveillance."
                        )
                    self._confirm_gate(
                        plan,
                        gate,
                        reason=confirmation_reason or "Manual confirmation of current operational decision-making",
                        input_updates=confirmation_updates or None,
                    )
            return self._run_and_handle(plan_id, run_seq=run_seq)
        # Manual-mode TEXT gate reply, dispatched through the per-tool gate adapter
        # registry (marvis/agent/gates/adapters.py) instead of an inline per-tool
        # if-chain. Each adapter parses its own reply shape and applies it:
        #   * confirm_join      -- [Go heavy.first]/[Uselast "to weigh."(§6 same-key conflict)
        #   * select_rule_set   -- [Option 1,3,5]/["and remove the two."/[All of them."(§3 rule-set selection)
        #   * apply_monitoring_disposition -- Observation/ Threshold/ New Version(S5 red-light disposition)
        # A None from parse_reply (not this adapter's shape) or apply (a no-op, e.g.
        # a dedup instruction at a gate with no pending conflicts) falls through to
        # the generic confirm / LLM-router path unchanged.
        # Free-text adapters are a manual-mode compatibility boundary.  When an
        # LLM is available, every non-canonical sentence must go through the
        # semantic router and independent authorization reviewer; otherwise a
        # keyword buried in a conditional sentence could release the gate.
        adapter = (
            get_gate_adapter(gate)
            if self._llm is None and self._allow_manual_gate_adapters
            else None
        )
        if adapter is not None:
            parsed = adapter.parse_reply(user_text, self._gate_reply_context(plan, gate))
            if parsed is not None:
                turn = adapter.apply(self, plan, gate, parsed, run_seq=run_seq)
                if turn is not None:
                    return turn
        return self._handle_instruction(
            plan,
            gate,
            user_text,
            run_seq,
            confirmation_source,
        )

    def replan_structured(
        self,
        *,
        plan_id,
        goal: str,
        expected_step_id=None,
        run_seq=0,
        confirmation_source=CONFIRMATION_SOURCE_HUMAN,
    ) -> DriverTurn:
        """Structural replan driven by an already-decided goal (AGT-8).

        Unlike ``resume(user_text=...)``, this does NOT feed ``goal`` back through
        ``is_confirm``/``route_instruction`` — it goes straight to
        ``GateExecutionAdapter.apply_replan`` (the same structured path
        ``_handle_instruction``'s ``action == "replan"`` branch already uses for a
        user-typed instruction). This is for callers that already hold a
        *structured* replan decision (AUTO's ``decide_gate``) and would otherwise
        have to round-trip it back through the free-text router — risking
        ``is_confirm`` misreading a phrase like "……And keep on moving." as a plain confirm,
        or a second LLM classification pass misjudging it as ``clarify`` and
        silently dropping the replan intent (both routes never reach
        ``apply_replan`` in that case).
        """
        confirmation_source = _normalize_confirmation_source(confirmation_source)
        plan = self._repo.load_plan(plan_id)
        gate = None if plan.status == PlanStatus.VALIDATED else self._awaiting_step(plan)
        if expected_step_id and (gate is None or gate.id != str(expected_step_id)):
            raise DriverError("The current steps to be confirmed have changed and please refresh and try again.")
        _assert_source_may_operate_gate(gate, confirmation_source)
        if (
            confirmation_source == CONFIRMATION_SOURCE_AUTO
            and gate is not None
            and self._requires_governed_human_decision(gate)
        ):
            raise DriverError("AUTO The mandatory manual business decision node cannot be operated or confirmed and is to be continued manually.")
        return self._gate_execution.apply_replan(plan, gate, goal, run_seq)

    def retry_failed_step(
        self,
        plan_id: str,
        step_id: str,
        *,
        run_seq: int = 0,
        inputs: dict | None = None,
        preserve_target_confirmation: bool = False,
    ) -> DriverTurn:
        """Resume the same plan from its failed step, preserving prior outputs."""

        plan = self._repo.load_plan(plan_id)
        failed_step = find_step(plan, step_id)
        if failed_step is None:
            raise DriverError("The failure step does not exist, please try again after updating the task.")
        retry_inputs = normalize_adjust_params({**(failed_step.inputs or {}), **(inputs or {})})
        # Persisted template inputs may keep recipes as a ``$ref:...`` until
        # execution resolves the upstream configure-tuning output.  Validate
        # concrete recipe lists (including legacy aliases), but do not treat a
        # valid unresolved reference as a malformed user adjustment.
        if isinstance(retry_inputs.get("recipes"), list):
            recipe_error = adjust_param_error({"recipes": retry_inputs["recipes"]})
            if recipe_error:
                raise DriverError(recipe_error)
        elif "recipes" in (inputs or {}) and not str(retry_inputs.get("recipes") or "").startswith(
            "$ref:"
        ):
            recipe_error = adjust_param_error({"recipes": retry_inputs.get("recipes")})
            if recipe_error:
                raise DriverError(recipe_error)
        inputs_unchanged = retry_inputs == dict(failed_step.inputs or {})
        was_confirmed = self._repo.is_step_confirmed(step_id)
        reauthorize_governed_target = bool(
            preserve_target_confirmation
            and was_confirmed
            and inputs_unchanged
            and self._governance is not None
            and self._principal is not None
            and self._requires_governed_human_decision(failed_step)
        )
        self._repo.retry_failed_step(
            plan_id,
            step_id,
            inputs=retry_inputs,
            # A governed step needs a fresh immutable decision bound to the
            # current manifest/input/evidence hashes.  Keeping only the old
            # ``confirmed`` bit can leave execution with no live governance
            # context after a restart or platform fix.  Non-governed gates may
            # still reuse the prior bit when the repository proves inputs are
            # unchanged.
            preserve_target_confirmation=(
                preserve_target_confirmation and not reauthorize_governed_target
            ),
        )
        if reauthorize_governed_target:
            paused = self._run_and_handle(plan_id, run_seq=run_seq)
            paused_plan = self._repo.load_plan(plan_id)
            gate = self._awaiting_step(paused_plan)
            if paused.status != PlanStatus.AWAITING_CONFIRM.value or gate is None:
                return paused
            if gate.id != step_id:
                raise DriverError("Please refresh and try again when the failed step is retrying to confirm that node has changed.")
            self._confirm_gate(
                paused_plan,
                gate,
                reason=f"Manually explicitly authorize a re-test from the failed step:{failed_step.title}",
            )
        return self._run_and_handle(plan_id, run_seq=run_seq)

    def rollback_failed_plan_to_feature_screen(
        self,
        plan_id: str,
        failed_step_id: str,
        *,
        excluded_features: list[str],
        run_seq: int = 0,
    ) -> DriverTurn:
        """Revise the feature universe and resume the same plan from screening.

        This path is deliberately distinct from a failed-step retry.  It keeps
        the completed split/spec prefix, replaces the screen step's feature
        input with a concrete filtered list, and atomically invalidates that
        step plus every transitive descendant.  The screen gate is then shown
        again for fresh human confirmation.
        """

        plan = self._repo.load_plan(plan_id)
        if plan.status != PlanStatus.FAILED:
            raise DriverError("The current plan was not a failure and could not be implemented upstream.")
        failed_step = find_step(plan, failed_step_id)
        if failed_step is None or failed_step.status != StepStatus.FAILED:
            raise DriverError("The current failure step has changed, so please refresh and try again.")

        ancestor_ids = _ancestor_step_ids(plan, failed_step_id)
        roots = [
            step
            for step in plan.steps
            if step.id in ancestor_ids
            and step.tool_ref.plugin == "modeling"
            and step.tool_ref.tool == "screen_features"
        ]
        if len(roots) != 1:
            raise DriverError("Cannot locate only the model feature filter steps that have been completed, and the plan has not been modified.")
        root = roots[0]
        if root.status != StepStatus.DONE or not root.output_ref:
            raise DriverError("The feature screening process has not been completed and cannot be considered a safe retreat.")
        if not root.needs_confirmation:
            raise DriverError("The feature screening process lacks manual confirmation of the door and refuses to return automatically.")

        normalized_exclusions: list[str] = []
        for item in excluded_features:
            name = str(item).strip()
            if name and name not in normalized_exclusions:
                normalized_exclusions.append(name)
        if not normalized_exclusions:
            raise DriverError("At least one of the characteristics to be excluded must be identified and the plan has not been revised.")

        current_features = _resolve_revision_input(self._repo, (root.inputs or {}).get("features"))
        if not isinstance(current_features, list):
            current_features = _latest_ancestor_feature_cols(
                self._repo,
                plan,
                ancestor_ids,
                before_index=root.index,
            )
        feature_universe = _normalized_feature_list(current_features)
        if not feature_universe:
            raise DriverError("Could not resolve the profile from the completed model specification, the plan was not modified.")

        protected_names = {
            str(value).strip()
            for value in (
                _resolve_revision_input(self._repo, (root.inputs or {}).get("target_col")),
                _resolve_revision_input(self._repo, (root.inputs or {}).get("split_col")),
            )
            if isinstance(value, str) and str(value).strip()
        }
        protected = [name for name in normalized_exclusions if name in protected_names]
        if protected:
            raise DriverError(
                "Target columns or cut-downs cannot be excluded as general characteristics:" + ",".join(protected) + "."
            )
        unknown = [name for name in normalized_exclusions if name not in feature_universe]
        if unknown:
            raise DriverError(
                "The plan has not been modified in the following sets of characteristics not currently recognized:" + ",".join(unknown) + "."
            )
        excluded_set = set(normalized_exclusions)
        remaining = [name for name in feature_universe if name not in excluded_set]
        if not remaining:
            raise DriverError("The exclusion feature is empty and the plan is not modified.")

        revised_inputs = {**(root.inputs or {}), "features": remaining}
        try:
            self._repo.rollback_failed_plan_from_step(
                plan_id,
                root.id,
                failed_step_id,
                root_inputs=revised_inputs,
                excluded_features=normalized_exclusions,
                expected_plan_revision=int(plan.replan_count),
                expected_root_output_ref=str(root.output_ref),
            )
        except (ConflictError, KeyError, ValueError) as exc:
            raise DriverError(f"The planned status has changed, with no upstream rollback:{exc}") from exc
        return self._run_and_handle(plan_id, run_seq=run_seq)

    def rollback_failed_plan_to_tuning_config(
        self,
        plan_id: str,
        failed_step_id: str,
        *,
        default_n_trials: int | None,
        n_trials_by_recipe: dict[str, int],
        run_seq: int = 0,
    ) -> DriverTurn:
        """Revise tuning budgets without invalidating split or feature work.

        The completed ``configure_tuning`` ancestor is the only truthful
        rollback root: changing the failed tune step directly would leave the
        configuration card showing stale budgets, while changing modeling spec
        would unnecessarily invalidate feature screening.  The repository
        resets configuration and every descendant atomically; execution then
        pauses at the fresh configuration confirmation gate before any trial is
        run.
        """

        plan = self._repo.load_plan(plan_id)
        if plan.status != PlanStatus.FAILED:
            raise DriverError("The current plan was not a failure and the budget for the transfer could not be modified.")
        failed_step = find_step(plan, failed_step_id)
        if failed_step is None or failed_step.status != StepStatus.FAILED:
            raise DriverError("The current failure step has changed, so please refresh and try again.")

        ancestor_ids = _ancestor_step_ids(plan, failed_step_id)
        roots = [
            step
            for step in plan.steps
            if step.id in ancestor_ids
            and step.tool_ref.plugin == "modeling"
            and step.tool_ref.tool == "configure_tuning"
        ]
        if len(roots) != 1:
            raise DriverError("Cannot locate only the configured referencing steps that have been completed, and the plan is not modified.")
        root = roots[0]
        if root.status != StepStatus.DONE or not root.output_ref:
            raise DriverError("The deployment of the intervention steps has not yet been completed and cannot be used as a safe retreat point.")
        if not root.needs_confirmation:
            raise DriverError("Configure the participator steps without manual confirmation doors and reject automatic modification.")

        try:
            current_output = _load_bound_output(self._repo, root.id)
        except (KeyError, TypeError, ValueError) as exc:
            raise DriverError("Configure the reference output does not exist and the plan is not modified.") from exc
        recipes = _normalized_feature_list(current_output.get("recipes"))
        if not recipes:
            resolved_recipes = _resolve_revision_input(
                self._repo, (root.inputs or {}).get("recipes")
            )
            recipes = _normalized_feature_list(resolved_recipes)
        if not recipes:
            raise DriverError("Cannot parse candidate algorithm from the completed configuration. The plan is not modified.")

        requested: dict[str, int] = {}
        for raw_recipe, raw_count in dict(n_trials_by_recipe or {}).items():
            recipe = str(raw_recipe).strip()
            try:
                count = normalize_n_trials(raw_count)
            except ValueError:
                raise DriverError("The budget for each algorithm must be 1 to 200 integers.")
            if not recipe:
                raise DriverError("The budget for each algorithm must be 1 to 200 integers.")
            requested[recipe] = int(count)
        if default_n_trials is not None:
            try:
                default_budget = normalize_n_trials(default_n_trials)
            except ValueError:
                raise DriverError("The unified budget for the transfer must be 1 to 200 integers.")
            for recipe in recipes:
                requested.setdefault(recipe, int(default_budget))
        if not requested:
            raise DriverError("New budget transfers must be identified and the plan has not been revised.")
        unknown = [recipe for recipe in requested if recipe not in recipes]
        if unknown:
            raise DriverError(
                "The following algorithms are not in the current configuration and the plan is not modified:" + ",".join(unknown) + "."
            )

        current_budgets = current_output.get("n_trials_by_recipe")
        revised_budgets = {
            recipe: int(
                (current_budgets or {}).get(
                    recipe,
                    current_output.get("n_trials") or 1,
                )
            )
            for recipe in recipes
        }
        revised_budgets.update(requested)
        revised_inputs = {
            **(root.inputs or {}),
            "n_trials_by_recipe": revised_budgets,
        }
        try:
            self._repo.rollback_failed_plan_from_step(
                plan_id,
                root.id,
                failed_step_id,
                root_inputs=revised_inputs,
                tuning_budgets=revised_budgets,
                expected_plan_revision=int(plan.replan_count),
                expected_root_output_ref=str(root.output_ref),
            )
        except (ConflictError, KeyError, ValueError) as exc:
            raise DriverError(f"The planned status has changed without any change in the budget transfer:{exc}") from exc
        return self._run_and_handle(plan_id, run_seq=run_seq)

    def _handle_instruction(
        self,
        plan,
        gate,
        user_text,
        run_seq,
        confirmation_source,
    ) -> DriverTurn:
        """Route a non-confirm reply. Manual mode (no LLM) shows the canned hint;
        agent mode classifies the instruction into confirm / adjust / replan / clarify
        and acts on it (spec §3 Call the command.→Adjustment/Replanning)."""
        if self._llm is None:
            return self._adjust_placeholder(plan.id, gate, run_seq)
        context = gate.title if gate is not None else "Schedule Overview(Implementation has not yet started)"
        # AGT-5: tell the router which parameters this gate's dependency step(s)
        # actually declare (name/type/current value/bounds) instead of leaving it
        # to blind-guess key names from free text — a wrong guess previously only
        # surfaced as "No adjustable parameters recognized" after apply_adjust already failed.
        editable_schema = gate_editable_input_schema(
            plan,
            gate,
            self._safe_output,
        )
        param_schema = gate_param_schema(
            plan,
            gate,
            editable_input_schema=editable_schema,
        )
        selection_schema = self._experiment_selection_param_schema(plan, gate)
        # ``selected_experiment_id`` can appear as a resolved dependency input
        # on later report/delivery gates.  It is a live choice only at the
        # select_experiment gate; exposing it elsewhere makes the router's
        # candidate-recovery pass treat a report confirmation as an empty model
        # selection and keep the workflow stuck.
        param_schema = [
            item
            for item in param_schema
            if item.get("name") != "selected_experiment_id"
        ]
        if selection_schema is not None:
            # ``selected_experiment_id`` is a decision input on the pending gate
            # itself, not an input of an already-computed dependency. Surface
            # persisted candidates plus the platform recommendation so the LLM
            # grounds a free-text choice in real execution evidence.
            param_schema.append(selection_schema)
        route = route_instruction(
            self._llm,
            gate_context=context,
            instruction=user_text,
            param_schema=param_schema,
            strict_contract=True,
        )
        action = route["action"]
        if action == "confirm":
            route_params = dict(route.get("params") or {})
            route_constraint = str(route.get("constraint") or "").strip()
            if route_constraint:
                return DriverTurn(
                    plan.id,
                    plan.status.value,
                    [
                        self._composer.instruction_message(
                            plan,
                            gate,
                            run_seq=run_seq,
                            text=(
                                "The first time I understood that the intention to continue was still conditional or pre-empted, and that the intention was not to be met with a single decision."
                                "It cannot be granted immediate and unconditional authority as a current node and therefore has not been implemented."
                                f"Conditions recognized:{route_constraint}."
                                "Please reconfirm the conditions once they have been met or indicate what changes are to be made."
                            ),
                        )
                    ],
                )
            if selection_schema is not None and not route_params:
                return DriverTurn(
                    plan.id,
                    plan.status.value,
                    [
                        self._composer.instruction_message(
                            plan,
                            gate,
                            run_seq=run_seq,
                            text=(
                                "The current node must clearly select a candidate experiment that has been demonstrated;"
                                "The only way to say that is to continue to decide your candidacy."
                            ),
                        )
                    ],
                )
            if route_params and selection_schema is not None:
                selection_error = self._experiment_selection_adjust_error(
                    plan,
                    gate,
                    route_params,
                    selection_text=user_text,
                )
                if selection_error:
                    return DriverTurn(
                        plan.id,
                        plan.status.value,
                        [
                            self._composer.instruction_message(
                                plan,
                                gate,
                                run_seq=run_seq,
                                text=selection_error,
                            )
                        ],
                    )
            if (
                route.get("confidence") == "high"
                and route.get("explicit_authorization") is True
                and confirmation_source == CONFIRMATION_SOURCE_HUMAN
            ):
                reviewed_plan_fingerprint = plan_fingerprint(plan)
                review = review_semantic_authorization(
                    self._llm,
                    gate_context=context,
                    instruction=user_text,
                    proposed_params=route_params,
                )
                if review.authorized:
                    # Re-enter the canonical confirmation path instead of
                    # duplicating its monitoring, adoption, selection,
                    # governance and stale-snapshot checks.  Use a deterministic
                    # confirmation token exactly once; preserve the original
                    # human turn and the reviewer's exact quote as audit evidence.
                    semantic_reason = (
                        f"Semantic authorization of the original words:{str(user_text).strip()};"
                        f"The basis of the independent review is, word for word:{review.evidence_quote}"
                    )
                    try:
                        return self.resume(
                            plan_id=plan.id,
                            user_text="Confirm.",
                            run_seq=run_seq,
                            adjust_params=route_params or None,
                            expected_step_id=gate.id if gate is not None else None,
                            confirmation_source=confirmation_source,
                            _confirmation_reason=semantic_reason,
                            _expected_plan_revision=int(plan.replan_count),
                            _expected_plan_status=plan.status.value,
                            _expected_plan_fingerprint=reviewed_plan_fingerprint,
                        )
                    except DriverError as exc:
                        if not (
                            "Semantic authorization of plans during review" in str(exc)
                            or "Current steps to be confirmed have changed" in str(exc)
                        ):
                            raise
                        current = self._repo.load_plan(plan.id)
                        current_gate = (
                            None
                            if current.status == PlanStatus.VALIDATED
                            else self._awaiting_step(current)
                        )
                        return DriverTurn(
                            current.id,
                            current.status.value,
                            [
                                self._composer.instruction_message(
                                    current,
                                    current_gate,
                                    run_seq=run_seq,
                                    text=str(exc),
                                )
                            ],
                        )
                text = (
                    "The first time I understood the intention to continue, but the independent semantic review did not confirm that this was the current node,"
                    "The current set-up is an immediate and unconditional authorization and therefore not implemented."
                    + (f"Review of the note:{review.reason}." if review.reason else "")
                    + "Use the current confirmation control, or specify whether to continue, modify or deal with it later."
                )
            elif (
                route.get("confidence") == "high"
                and route.get("explicit_authorization") is True
            ):
                text = "Only current manual input can be carried by semantic authorization; the automated source still needs to use controlled actions."
            else:
                text = (
                    "I understand the possible continuing intent, but I cannot be sure whether this sentence is authorized to be implemented."
                    + (
                        f"Basis of judgement:{route.get('reason')}."
                        if route.get("reason")
                        else ""
                    )
                    + "Please state your intentions again."
                )
            return DriverTurn(
                plan.id,
                plan.status.value,
                [
                    self._composer.instruction_message(
                        plan,
                        gate,
                        run_seq=run_seq,
                        text=text,
                    )
                ],
            )
        if action == "adjust" and gate is not None and gate.depends_on:
            if self._gate_execution.is_noop_adjustment(
                plan,
                gate,
                route["params"],
            ):
                return DriverTurn(
                    plan.id,
                    plan.status.value,
                    [
                        self._composer.instruction_message(
                            plan,
                            gate,
                            run_seq=run_seq,
                            text=(
                                "I understand that the adjustment is consistent with the current parameters and has not been implemented or released this time."
                                "If you accept the current settings, click on the current confirmation control or reply explicitly to \"confirm\""
                                "If so, please describe the different parameters."
                            ),
                        )
                    ],
                )
            return self._gate_execution.apply_adjust(plan, gate, route["params"], run_seq)
        if action == "replan":
            return self._gate_execution.apply_replan(plan, gate, user_text, run_seq)
        return DriverTurn(
            plan.id,
            plan.status.value,
            [
                self._composer.instruction_message(
                    plan,
                    gate,
                    run_seq=run_seq,
                    text=route.get("reason") or "Please specify your instructions.:Reply \"Recognize\" to continue or specify the parameters to be adjusted.",
                )
            ],
        )

    def _experiment_selection_param_schema(
        self,
        plan: Plan,
        gate: PlanStep | None,
    ) -> dict | None:
        candidates, recommended_id = self._experiment_selection_candidate_context(
            plan,
            gate,
        )
        candidate_ids = [row["experiment_id"] for row in candidates]
        if not candidate_ids:
            return None
        return {
            "name": "selected_experiment_id",
            "type": "string",
            "current": recommended_id or candidate_ids[0],
            "enum": candidate_ids,
            "bounds": {"enum": candidate_ids},
            "candidates": candidates,
        }

    def _experiment_selection_candidates(
        self,
        plan: Plan,
        gate: PlanStep | None,
    ) -> tuple[list[str], str]:
        candidates, recommended_id = self._experiment_selection_candidate_context(
            plan,
            gate,
        )
        return [row["experiment_id"] for row in candidates], recommended_id

    def _experiment_selection_candidate_context(
        self,
        plan: Plan,
        gate: PlanStep | None,
    ) -> tuple[list[dict], str]:
        if (
            gate is None
            or gate.tool_ref is None
            or gate.tool_ref.tool != "select_experiment"
        ):
            return [], ""
        candidates: dict[str, dict] = {}
        recommended_id = ""

        def add(value, row: dict | None = None) -> None:
            candidate = str(value or "").strip()
            if not candidate:
                return
            details = candidates.setdefault(
                candidate,
                {
                    "experiment_id": candidate,
                    "recipe": "",
                    "display_name": "",
                    "recommended": False,
                },
            )
            if not isinstance(row, dict):
                return
            recipe = str(
                row.get("recipe")
                or row.get("algorithm")
                or details.get("recipe")
                or ""
            ).strip()
            display_name = str(
                row.get("display_name")
                or row.get("name")
                or details.get("display_name")
                or ""
            ).strip()
            if recipe:
                details["recipe"] = recipe
            if display_name:
                details["display_name"] = display_name

        for dep_id in gate.depends_on or []:
            output = self._safe_output(dep_id)
            if not isinstance(output, dict):
                continue
            if not recommended_id:
                recommended_id = str(
                    output.get("best_experiment_id")
                    or output.get("recommended_experiment_id")
                    or ""
                ).strip()
            raw_ids = output.get("experiment_ids")
            if isinstance(raw_ids, list):
                for item in raw_ids:
                    add(item)
            rows = output.get("experiments")
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict):
                        add(row.get("id") or row.get("experiment_id"), row)
        if recommended_id:
            add(recommended_id)
        for details in candidates.values():
            recipe = str(details.get("recipe") or "").strip()
            if not details.get("display_name"):
                details["display_name"] = (
                    _MODELING_RECIPE_DISPLAY_NAMES.get(recipe)
                    or recipe
                    or details["experiment_id"]
                )
            details["recommended"] = (
                details["experiment_id"] == recommended_id
            )
        return list(candidates.values()), recommended_id

    def _experiment_selection_adjust_error(
        self,
        plan: Plan,
        gate: PlanStep | None,
        params,
        *,
        selection_text: str | None = None,
    ) -> str | None:
        if not isinstance(params, dict):
            return "The candidate experiment must be structured."
        if (
            gate is None
            or gate.tool_ref is None
            or gate.tool_ref.tool != "select_experiment"
        ):
            return "The confirmation with parameters is not accepted at the current node, and please specify whether to continue or adjust."
        if set(params) != {"selected_experiment_id"}:
            return "Only submit when choosing an experimentselected_experiment_id."
        selected_id = str(params.get("selected_experiment_id") or "").strip()
        candidates, recommended_id = self._experiment_selection_candidate_context(
            plan,
            gate,
        )
        candidate_ids = [row["experiment_id"] for row in candidates]
        if not selected_id:
            return "Please select a specific candidate experiment."
        if selected_id not in candidate_ids:
            return "The selected experiment is not in the current task pool. Please select from the displayed candidate."
        if selection_text is not None:
            return _candidate_selection_text_error(
                candidates,
                recommended_id=recommended_id,
                selected_id=selected_id,
                user_text=selection_text,
            )
        return None

    def _adjust_placeholder(self, plan_id, gate, run_seq) -> DriverTurn:
        # Manual mode (no LLM): non-confirm free text can only show the canned hint.
        plan = self._repo.load_plan(plan_id)
        return DriverTurn(
            plan_id,
            plan.status.value,
            [self._composer.manual_adjust_placeholder_message(plan, gate, run_seq=run_seq)],
        )

    @staticmethod
    def _require_adoption_reason(value) -> str:
        try:
            return normalize_adoption_reason(value)
        except AdoptionReasonError as exc:
            raise DriverError(str(exc)) from exc

    # -- plan build -----------------------------------------------------------
    def build_plan(
        self,
        *,
        task_id,
        template_id,
        slots,
        autonomy=None,
        tier=None,
        success_criteria=None,
    ) -> Plan:
        plan = self._prepare_plan(
            task_id=task_id,
            template_id=template_id,
            slots=slots,
            autonomy=autonomy,
            tier=tier,
            success_criteria=success_criteria,
        )
        self._repo.create_plan(plan)
        return plan

    def _prepare_plan(
        self,
        *,
        task_id,
        template_id,
        slots,
        autonomy=None,
        tier=None,
        success_criteria=None,
    ) -> Plan:
        """Build, validate, and timestamp a plan without persisting it."""

        if self._planner is None:
            raise DriverError("driver has no planner to build plans")
        plan = self._planner.from_template(
            get_template(template_id), dict(slots), task_id, autonomy=autonomy
        )
        if tier:
            plan.tier = tier
        if success_criteria:
            # AGT-4: layer user/AUTO-supplied criteria on top of the template's own
            # (empty for the built-in modeling templates today) rather than replacing
            # it, so a future template with real defaults still gets to keep them.
            plan.success_criteria = [*plan.success_criteria, *success_criteria]
        if self._validator is not None:
            problems = self._validator.validate(plan)
            if problems:
                raise DriverError(f"plan failed validation: {problems}")
        plan.status = PlanStatus.VALIDATED
        now = datetime.now(UTC).isoformat()
        if not plan.created_at:
            plan.created_at = now
        if not plan.updated_at:
            plan.updated_at = plan.created_at
        return plan

    # -- core loop ------------------------------------------------------------
    def _run_and_handle(self, plan_id, *, run_seq) -> DriverTurn:
        if self._cancellation_check is None:
            result = self._executor.run(plan_id)
        else:
            result = self._executor.run(
                plan_id,
                cancellation_check=self._cancellation_check,
            )
        plan = self._repo.load_plan(plan_id)
        status = result.status
        if status == PlanStatus.AWAITING_CONFIRM:
            gate = self._awaiting_step(plan)
            return DriverTurn(plan_id, status.value, [self._composer.gate_message(plan, gate, run_seq=run_seq)])
        if status == PlanStatus.DONE:
            return DriverTurn(plan_id, status.value, [self._composer.done_message(plan, run_seq=run_seq)])
        if status == PlanStatus.REVIEW:
            return DriverTurn(plan_id, status.value, [self._composer.review_message(plan, run_seq=run_seq)])
        if status == PlanStatus.CANCELLED:
            return DriverTurn(
                plan_id,
                status.value,
                [self._composer.cancelled_message(plan, run_seq=run_seq)],
            )
        return DriverTurn(plan_id, status.value, [self._composer.failed_message(plan, run_seq=run_seq)])

    @staticmethod
    def _awaiting_step(plan: Plan) -> PlanStep | None:
        for step in sorted(plan.steps, key=lambda s: (s.index, s.id)):
            if step.status == StepStatus.AWAITING_CONFIRM:
                return step
        return None

    def _safe_output(self, step_id: str):
        try:
            return _load_bound_output(self._repo, step_id)
        except (KeyError, TypeError, ValueError):
            return None

    def _gate_reply_context(self, plan: Plan, gate: PlanStep) -> GateReplyContext:
        """The adapter-agnostic context a gate reply parser derives its needs from
        (the current plan + this driver's output loader). No adapter-specific detail
        lives here: e.g. the rule-set adapter reads its own mine_rules dependency's
        candidate count off this context, so the driver stays free of it."""
        return GateReplyContext(plan=plan, gate=gate, load_output=self._safe_output)

    def _feature_binning_adjust_error(
        self,
        plan: Plan,
        gate: PlanStep,
        features: list,
    ) -> str | None:
        allowed: set[str] = set()
        for dep_id in gate.depends_on or []:
            dep = find_step(plan, dep_id)
            if dep is None or dep.tool_ref.tool != "compute_feature_metrics":
                continue
            output = self._safe_output(dep.id)
            for metric in (output.get("metrics") or []) if isinstance(output, dict) else []:
                if isinstance(metric, dict) and str(metric.get("feature") or "").strip():
                    allowed.add(str(metric["feature"]).strip())
        unknown = sorted({str(item).strip() for item in features} - allowed)
        if unknown:
            return f"The box-discretion feature is not in the current single variable analysis: {', '.join(unknown)}."
        return None

    def _special_value_adjust_error(
        self,
        plan: Plan,
        gate: PlanStep,
        decisions: dict,
        *,
        selection=None,
    ) -> str | None:
        """Validate complete decisions against persisted screen evidence.

        This runs before mutating either the screen selection or the gate input,
        so a stale/partial UI submission cannot leave half-applied state.
        """
        selected: list[str] = []
        sentinel_columns: dict[str, object] = {}
        screen_found = False
        for dep_id in gate.depends_on or []:
            dep = find_step(plan, dep_id)
            if dep is None or dep.tool_ref.tool != "screen_features":
                continue
            screen_found = True
            output = self._safe_output(dep.id)
            if not isinstance(output, dict):
                return "The special value governance policy cannot be confirmed without the feature filter output."
            raw_selected = output.get("selected")
            if not isinstance(raw_selected, list):
                return "The feature filter output lacks a valid selected feature list to confirm the special value governance policy."
            selected = [
                str(item).strip()
                for item in (
                    selection if selection is not None else raw_selected
                )
                if str(item).strip()
            ]
            raw_columns = output.get("sentinel_columns")
            if not isinstance(raw_columns, dict):
                return "The feature-screening output lacks effective evidence of special value detection to confirm the governance strategy."
            sentinel_columns = dict(raw_columns)
            break
        if not screen_found:
            return "The special value governance steps were not tied to the feature screening evidence and could not be confirmed."
        relevant = [
            column
            for column in selected
            if column in sentinel_columns and sentinel_columns.get(column)
        ]
        if not relevant:
            return None
        decision_names = {str(column) for column in decisions}
        missing = [column for column in relevant if column not in decision_names]
        if missing:
            return (
                "The following selected features have been detected with special values and must be selected for transfer, retention or deletion before continuing:"
                + ",".join(missing)
                + "."
            )
        unrelated = sorted(decision_names - set(relevant))
        if unrelated:
            return "Governance decisions include features that are currently unselected or not detected:" + ",".join(unrelated) + "."
        return adjust_param_error({"decisions": decisions})

    def _apply_monitoring_disposition(
        self,
        gate: PlanStep,
        disposition: str,
        *,
        reason: str,
    ) -> None:
        """Bind an explicit alarm decision to the evidence-bound effect gate.

        The step remains ``AWAITING_CONFIRM`` while inputs are updated. Observe
        and new-version are immediately confirmed by the adapter; threshold
        adjustment remains paused until a concrete patch is supplied.
        """
        gate.inputs = {
            **(gate.inputs or {}),
            "disposition": disposition,
            "reason": reason,
        }
        self._repo.update_step(gate)

    def _confirm_gate(
        self,
        plan: Plan,
        gate: PlanStep,
        *,
        reason: str,
        input_updates: dict | None = None,
    ) -> None:
        expected_plan_fingerprint = plan_fingerprint(plan)
        expected_step_fingerprint = plan_step_confirmation_fingerprint(
            gate,
            confirmed=False,
        )
        if not self._requires_governed_human_decision(gate):
            try:
                if input_updates:
                    self._repo.confirm_step_with_inputs(
                        gate.id,
                        input_updates=input_updates,
                        expected_step_fingerprint=expected_step_fingerprint,
                        expected_plan_fingerprint=expected_plan_fingerprint,
                        expected_plan_revision=int(plan.replan_count),
                        expected_plan_status=plan.status.value,
                    )
                else:
                    self._repo.confirm_step(
                        gate.id,
                        expected_step_fingerprint=expected_step_fingerprint,
                        expected_plan_fingerprint=expected_plan_fingerprint,
                        expected_plan_revision=int(plan.replan_count),
                        expected_plan_status=plan.status.value,
                    )
            except ConflictError as exc:
                raise DriverError(
                    "Please refresh and try again for the current confirmation node which has changed before implementation."
                ) from exc
            return
        if self._governance is None or self._principal is None:
            raise DriverError(
                "The current step requires manual decision-making by the Platform to record the records, but the request does not have a valid local identity."
            )
        try:
            self._governance.authorize_step(
                plan_id=plan.id,
                step_id=gate.id,
                principal=self._principal,
                reason=str(reason or "Manual confirmation of current operational decision-making"),
                expected_plan_revision=int(plan.replan_count),
                expected_plan_status=plan.status.value,
                expected_plan_fingerprint=expected_plan_fingerprint,
                expected_step_fingerprint=expected_step_fingerprint,
                input_updates=input_updates,
            )
        except (AuthorizationError, ConflictError, TypeError, ValueError) as exc:
            raise DriverError(str(exc)) from exc

    def _requires_governed_human_decision(self, gate: PlanStep) -> bool:
        policy = getattr(gate, "policy", None)
        if getattr(policy, "human_decision_gate", "none") == "required":
            return True
        resolver = getattr(self._governance, "requires_human_decision", None)
        if not callable(resolver):
            return False
        try:
            return bool(resolver(gate))
        except (AuthorizationError, TypeError, ValueError) as exc:
            raise DriverError(str(exc)) from exc

    def _latest_failed_step_run_error_kind(self, step_id: str) -> str | None:
        latest_error_kind = getattr(self._repo, "latest_failed_step_run_error_kind", None)
        if callable(latest_error_kind):
            return latest_error_kind(step_id)
        return None
def _ancestor_step_ids(plan: Plan, step_id: str) -> set[str]:
    by_id = {step.id: step for step in plan.steps}
    result: set[str] = set()
    pending = list((by_id.get(step_id).depends_on or []) if by_id.get(step_id) else [])
    while pending:
        candidate = str(pending.pop())
        if candidate in result:
            continue
        result.add(candidate)
        parent = by_id.get(candidate)
        if parent is not None:
            pending.extend(parent.depends_on or [])
    return result


def _resolve_revision_input(repo, value):
    if not (isinstance(value, str) and value.startswith("$ref:")):
        return list(value) if isinstance(value, list) else value
    match = re.fullmatch(r"\$ref:(?P<step>.+?)\.output(?:\.(?P<field>.+))?", value)
    if match is None:
        return None
    try:
        current = _load_bound_output(repo, match.group("step"))
    except (KeyError, TypeError, ValueError):
        return None
    field = match.group("field")
    if not field:
        return current
    for part in field.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _latest_ancestor_feature_cols(
    repo,
    plan: Plan,
    ancestor_ids: set[str],
    *,
    before_index: int,
):
    candidates = sorted(
        (
            step
            for step in plan.steps
            if step.id in ancestor_ids and step.index < before_index and step.output_ref
        ),
        key=lambda step: (step.index, step.id),
        reverse=True,
    )
    for step in candidates:
        try:
            output = _load_bound_output(repo, step.id)
        except (KeyError, TypeError, ValueError):
            continue
        feature_cols = output.get("feature_cols") if isinstance(output, dict) else None
        if isinstance(feature_cols, list):
            return feature_cols
    return None


def _load_bound_output(repo, step_id: str) -> dict:
    loader = getattr(repo, "load_bound_step_output", None)
    if callable(loader):
        return loader(step_id)
    return repo.load_step_output(step_id)


def _normalized_feature_list(value) -> list[str]:
    if not isinstance(value, list) or not value:
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return []
        name = item.strip()
        if name not in result:
            result.append(name)
    return result


__all__ = [
    "CONFIRMATION_SOURCE_AUTO",
    "CONFIRMATION_SOURCE_HUMAN",
    "PlanDriver",
    "DriverMessage",
    "DriverTurn",
    "DriverError",
    "is_confirm",
    "confirmation_is_explicitly_withheld",
    "render_tool_output",
    # Backward-compat re-exports: the gate reply parsers moved to
    # marvis.agent.gates.adapters (LT-3) but tests + any external caller still
    # import them from here under their historical private names.
    "_parse_dedup_instruction",
    "_parse_monitoring_disposition",
    "_parse_rule_selection_instruction",
]
