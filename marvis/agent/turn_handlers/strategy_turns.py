"""strategy_turns driver-turn handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from types import SimpleNamespace
from marvis.agent.plan_driver import CONFIRMATION_SOURCE_HUMAN
from marvis.agent.strategy_setup import STRATEGY_INTENT_FULL_DEVELOPMENT, STRATEGY_INTENT_LIMIT_PRICING, STRATEGY_INTENT_MONITORING, STRATEGY_INTENT_PORTFOLIO_ANALYSIS, STRATEGY_INTENT_QUICK_ANALYSIS, STRATEGY_INTENT_RULE_MINING, STRATEGY_INTENT_STANDARD_ANALYSIS, StrategySetupError, build_monitoring_setup_proposal, build_rule_strategy_proposal, build_strategy_dataset_context, build_strategy_development_proposal, build_strategy_proposal, preview_strategy_dataset_context, resolve_strategy_intent, strategy_development_clarification
from marvis.agent.strategy_request_compiler import CompiledStrategyRequestDraft, StandardWorkflowRequestDraft, StrategyRequestDraft
from marvis.agent.strategy_workflows import migrated_workflow_requirements
from marvis.artifacts.transactional import ArtifactTransactionError
from marvis.data.labels import nan_label_mask
from marvis.repositories.modeling import ModelingRepository
from marvis.repositories.strategy import StrategyRepository
from marvis.repositories.tasks import TaskRepository
from marvis.domain import TASK_TYPE_PORTFOLIO, StrategyProfitInput, StrategyTaskInput, TaskRecord
from marvis.strategy_lifecycle import ASSET_STATUS_ADOPTED_LOCAL
from marvis.files import sha256_file
from marvis.packs.strategy.voting_candidate import VOTING_CANDIDATE_ASSET_TYPE
from marvis.packs.strategy.voting_candidate_search_tools import VOTING_CANDIDATE_SEARCH_ARTIFACT_KIND, load_historical_voting_candidate_search_artifact
from marvis.packs.strategy.cross_candidate_search_tools import CROSS_CANDIDATE_SEARCH_ARTIFACT_KIND, load_cross_candidate_search_artifact
from marvis.packs.strategy.cross_rule_search_tools import CROSS_RULE_SEARCH_ARTIFACT_KIND, load_cross_rule_search_artifact
from marvis.packs.strategy.errors import StrategyError
from marvis.packs.strategy.dsl import strategy_spec_hash
from marvis.packs.modeling.errors import ModelingError
from marvis.packs.modeling.evidence import MODELING_TRAINING_EVIDENCE_ARTIFACT_KIND
from marvis.packs.modeling.evidence_tools import build_training_evidence_ref, load_modeling_training_evidence_artifacts
from marvis.packs.modeling.experiment import ExperimentStore
from marvis.packs.modeling.score_evidence import MODEL_SCORE_EVIDENCE_ARTIFACT_KIND
from marvis.packs.modeling.score_evidence_tools import load_model_score_evidence_artifacts
from marvis.packs.strategy.model_evidence_tools import MODEL_EVIDENCE_V2_ARTIFACT_KIND, derive_strategy_model_evidence_candidate_execution_ref, load_strategy_model_evidence_v2_artifact, strategy_model_evidence_registry_snapshot_token
from marvis.packs.strategy.impact_cube_tools import IMPACT_CUBE_ARTIFACT_KIND
from marvis.packs.strategy.pool_impact_tools import POOL_IMPACT_ARTIFACT_KIND, load_historical_strategy_pool_impact_artifact
from marvis.packs.strategy.pool_stability_tools import POOL_STABILITY_ARTIFACT_KIND, load_strategy_pool_stability_artifact
from marvis.packs.strategy.pool_tools import bind_strategy_pool_development_execution, load_current_strategy_candidate_pool_artifact
from marvis.packs.strategy.pool_requirement_resolver import pool_requirement_bindings_provenance, project_pool_entry_requirements, resolve_pool_requirements
from marvis.packs.strategy.report_bundle_adapters import validate_candidate_stability_report_compatibility, validate_cross_candidate_search_report_compatibility, validate_cross_rule_search_report_compatibility
from marvis.packs.strategy.report_bundle_tools import authenticate_strategy_report_identity_for_pool_on_connection, load_strategy_impact_cube_artifact
from marvis.packs.strategy.sample_design_v2_tools import SAMPLE_DESIGN_V2_BUNDLE_ARTIFACT_KIND, SAMPLE_DESIGN_V2_MEMBERSHIP_ARTIFACT_KIND, load_any_strategy_sample_design_v2_artifacts
from marvis.packs.strategy.sample_design_v2_native_tools import SAMPLE_DESIGN_V2_NATIVE_MEMBERSHIP_ARTIFACT_KIND
from marvis.repositories.task_artifacts import TaskArtifactConflictError, TaskArtifactDataError, TaskArtifactNotFoundError, TaskArtifactRepository
from marvis.repositories.strategy_pool import StrategyCandidatePoolRepository, strategy_pool_snapshot_hash
from marvis.packs.strategy.candidate_stability_tools import ARTIFACT_KIND as CANDIDATE_STABILITY_ARTIFACT_KIND, load_candidate_stability_artifact

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import DriverTurnRuntime
    from . import _STORED_EVALUATION_OPERATIONS
    from . import _STRATEGY_REPORT_CROSS_SEARCH_REPLAY_LIMIT
    from . import _STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT
    from . import _STRATEGY_REPORT_POOL_COMMAND_RE
    from . import _STRATEGY_REPORT_POOL_HISTORY_RE
    from . import _STRATEGY_REPORT_POOL_SELECTOR_RE
    from . import _STRATEGY_REPORT_POOL_STABILITY_REPLAY_LIMIT
    from . import _STRATEGY_REPORT_POOL_TITLE_RE
    from . import _STRATEGY_REPORT_POOL_TYPE_NEGATION_RE
    from . import _STRATEGY_REPORT_POOL_TYPE_PATTERNS
    from . import _STRATEGY_REPORT_VOTING_SEARCH_REPLAY_LIMIT
    from . import _STRATEGY_SAMPLE_DESIGN_REQUIRED_FIELDS
    from . import _TYPED_EVALUATION_OPERATIONS
    from . import _TurnHandlerSpec
    from . import _append_strategy_nan_label_clarification
    from . import _identity_display_text
    from . import _ingest_notice_text
    from . import _latest_matching_strategy_sample_design_ref
    from . import _latest_verified_strategy_sample_design_v2_binding
    from . import _modeling_data_runtime
    from . import _raise_corrupt_report_optional
    from . import _require_strategy_pool_impact_workspace
    from . import _run_driver_turn
    from . import _standard_workflow_request_preflight
    from . import _stored_strategy_request_preflight
    from . import _strategy_sample_design_dataset_preview

def run_strategy_driver_turn(
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    *,
    user_text: str | None,
    selection: list | None = None,
    dedup_strategies: dict | None = None,
    adjust_params: dict | None = None,
    expected_step_id: str | None = None,
    expected_plan_id: str | None = None,
    expected_plan_status: str | None = None,
    expected_plan_revision: int | None = None,
    expected_plan_fingerprint: str | None = None,
    expected_step_fingerprint: str | None = None,
    confirmation_source: str = CONFIRMATION_SOURCE_HUMAN,
    ui_action: str | None = None,
) -> dict:
    return _run_driver_turn(
        _STRATEGY_SPEC,
        runtime,
        repo,
        task,
        user_text=user_text,
        selection=selection,
        dedup_strategies=dedup_strategies,
        adjust_params=adjust_params,
        expected_step_id=expected_step_id,
        expected_plan_id=expected_plan_id,
        expected_plan_status=expected_plan_status,
        expected_plan_revision=expected_plan_revision,
        expected_plan_fingerprint=expected_plan_fingerprint,
        expected_step_fingerprint=expected_step_fingerprint,
        confirmation_source=confirmation_source,
        ui_action=ui_action,
    )

def _strategy_success_criteria(task: TaskRecord) -> list[dict] | None:
    """Turn the governed strategy contract into deterministic final-review limits."""
    strategy_input = getattr(task, "strategy_input", None)
    if isinstance(strategy_input, dict):
        bad_rate_max = strategy_input.get("max_bad_rate")
        approval_min = strategy_input.get("min_approval_rate")
    else:
        bad_rate_max = getattr(strategy_input, "max_bad_rate", None)
        approval_min = getattr(strategy_input, "min_approval_rate", None)
    # Compatibility for tasks/tests created before StrategyTaskInput existed.
    if bad_rate_max is None:
        bad_rate_max = getattr(task, "strategy_bad_rate_max", None)
    if approval_min is None:
        approval_min = getattr(task, "strategy_approval_min", None)
    criteria: list[dict] = []
    if bad_rate_max is not None:
        criteria.append({"metric": "approved_bad_rate", "max": float(bad_rate_max)})
    if approval_min is not None:
        criteria.append({"metric": "approval_rate", "min": float(approval_min)})
    return criteria or None

def _run_strategy_setup(
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    user_text: str | None,
    confirmation_source: str = CONFIRMATION_SOURCE_HUMAN,
    *,
    forced_intent: str | None = None,
) -> dict | tuple:
    strategy_input = getattr(task, "strategy_input", None)
    intent = forced_intent or resolve_strategy_intent(
        strategy_input, user_text, getattr(task, "model_name", None)
    )
    if intent in {
        STRATEGY_INTENT_LIMIT_PRICING,
        STRATEGY_INTENT_PORTFOLIO_ANALYSIS,
        STRATEGY_INTENT_STANDARD_ANALYSIS,
    }:
        return _strategy_intent_redirect_response(repo, task, intent)

    backend, registry = _modeling_data_runtime(runtime.settings)
    if intent == STRATEGY_INTENT_MONITORING:
        return _run_strategy_monitoring_setup(runtime, repo, task, backend, registry)
    raw_strategy_type = (
        getattr(strategy_input, "strategy_type", None)
        if not isinstance(strategy_input, dict)
        else strategy_input.get("strategy_type")
    )
    strategy_type = str(raw_strategy_type or "approval").strip().lower()
    if strategy_type not in {"approval", "reject"}:
        return _strategy_clarification_response(
            repo,
            task,
            {
                "code": "strategy_typed_spec_required",
                "entry_mode": (
                    getattr(strategy_input, "entry_mode", None)
                    if not isinstance(strategy_input, dict)
                    else strategy_input.get("entry_mode")
                )
                or "strategy_development",
                "strategy_type": strategy_type,
                "missing_fields": ["strategy_spec"],
                "message": (
                    f"{strategy_type} The strategy cannot be applied to access.cutoff Work flow;"
                    "Need to be compiled and confirmed for typology by natural language requestStrategy DSL."
                ),
            },
        )
    if intent == STRATEGY_INTENT_RULE_MINING:
        return _run_rule_strategy_setup(runtime, repo, task, backend, registry)
    if intent == STRATEGY_INTENT_FULL_DEVELOPMENT:
        clarification = strategy_development_clarification(strategy_input)
        if clarification is not None:
            return _strategy_clarification_response(repo, task, clarification)
        proposal = build_strategy_development_proposal(
            registry,
            backend,
            task.id,
            task.source_dir,
            strategy_input=strategy_input,
            target_col=getattr(task, "target_col", "") or None,
            score_col=getattr(task, "score_col", "") or None,
        )
        notices = registry.consume_ingest_notices(task.id)
        note_text = ("\n" + " ".join(proposal.notes)) if proposal.notes else ""
        bad = (
            f"(Bad rate{proposal.bad_rate:.2%})" if proposal.bad_rate is not None else ""
        )
        constraints = []
        if proposal.max_bad_rate is not None:
            constraints.append(f"The downfall of the customer base.≤ {proposal.max_bad_rate:.2%}")
        if proposal.min_approval_rate is not None:
            constraints.append(f"Pass rate≥ {proposal.min_approval_rate:.2%}")
        slots = proposal.template_slots()
        context = _strategy_dataset_context(runtime, task, require_target=True)
        try:
            slots["sample_design_ref"] = _latest_matching_strategy_sample_design_ref(
                runtime,
                task,
                context=context,
                drop_nan_labels=False,
                allow_native_risk_development=True,
            )
        except _StrategySampleDesignRequiredError as exc:
            return _strategy_request_clarification_response(
                repo,
                task,
                code="strategy_sample_design_required",
                message=str(exc),
                fields=_STRATEGY_SAMPLE_DESIGN_REQUIRED_FIELDS,
                ingest_notices=notices,
            )
        repo.add_agent_message(
            task.id,
            role="assistant",
            stage="chat",
            content=(
                f"Start full policy development:Sample`{proposal.dataset_name}`,Target column"
                f"`{proposal.target_col}`{bad},Breakdown of assessments`{proposal.score_col}`."
                f"Operational objectives`{proposal.objective}`,Constraints{';'.join(constraints)}."
                "Not generatedcutoff or default rules; automatically scan, construct and retrospect viable options after the plan is launched,"
                "Only manual decision-making is made upon adoption."
                f"{note_text}{_ingest_notice_text(notices)}"
            ),
            metadata={
                "intent": STRATEGY_INTENT_FULL_DEVELOPMENT,
                "ingest_notices": notices,
            },
        )
        return (proposal.template_id, slots, {})

    if intent != STRATEGY_INTENT_QUICK_ANALYSIS:
        raise StrategySetupError(f"unsupported strategy intent: {intent}")
    proposal = build_strategy_proposal(
        registry,
        backend,
        task.id,
        task.source_dir,
        target_col=getattr(task, "target_col", "") or None,
        score_col=getattr(task, "score_col", "") or None,
    )
    notices = registry.consume_ingest_notices(task.id)
    note_text = ("\n" + " ".join(proposal.notes)) if proposal.notes else ""
    bad = f"(Bad rate{proposal.bad_rate:.2%})" if proposal.bad_rate is not None else ""
    slots = proposal.template_slots()
    context = _strategy_dataset_context(runtime, task, require_target=True)
    try:
        slots["sample_design_ref"] = _latest_matching_strategy_sample_design_ref(
            runtime,
            task,
            context=context,
            drop_nan_labels=False,
            allow_native_risk_development=True,
        )
    except _StrategySampleDesignRequiredError as exc:
        return _strategy_request_clarification_response(
            repo,
            task,
            code="strategy_sample_design_required",
            message=str(exc),
            fields=_STRATEGY_SAMPLE_DESIGN_REQUIRED_FIELDS,
            ingest_notices=notices,
        )
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=(
            f"Start strategy analysis.:Sample`{proposal.dataset_name}`,Target column`{proposal.target_col}`{bad},"
            f"Breakdown of assessments`{proposal.score_col}`.The default approval strategy candidate has been generated and will automatically complete the backsight and analysis."
            f"{note_text}{_ingest_notice_text(notices)}"
        ),
        metadata={
            "intent": STRATEGY_INTENT_QUICK_ANALYSIS,
            "ingest_notices": notices,
        },
    )
    return (proposal.template_id, slots, {})

def _strategy_intent_redirect_response(
    repo: TaskRepository, task: TaskRecord, intent: str
) -> dict:
    if intent == STRATEGY_INTENT_LIMIT_PRICING:
        detail = {
            "intent": intent,
            "code": "strategy_standard_workflow_inputs_required",
            "available_workflow": "limit_pricing_matrix",
            "message": (
                "Recognized as a line pricing matrix.Workflow Implemented; please add a separate assessment in natural languages,"
                "PD/The target line, the box, the amount and interest rate grid, and the economic parameters, are the same.Agent It will be compiled and re-discovered before running."
            ),
        }
    elif intent == STRATEGY_INTENT_STANDARD_ANALYSIS:
        detail = {
            "intent": intent,
            "code": "strategy_standard_workflow_inputs_required",
            "available_workflows": ["profit_calc", "roll_rate_matrix"],
            "message": (
                "Please add a natural language to the analysis column, and use the manual to develop the analysis."
                "(a) State order or profit economy;Agent You choose the criteria.Workflow,Retrospect and request confirmation."
            ),
        }
    elif intent == STRATEGY_INTENT_PORTFOLIO_ANALYSIS:
        detail = {
            "intent": intent,
            "code": "strategy_portfolio_entry_required",
            "capability_status": "available",
            "suggested_task_type": TASK_TYPE_PORTFOLIO,
            "message": (
                "The combination analysis is identified as a combination analysis intent. The combination analysis has an independent official entry; the current strategic task is not wrong"
                "approval plan.Please create new or switch to the \"assembly analysis\" task and continue after binding the sample."
            ),
        }
    else:
        raise StrategySetupError(f"unsupported strategy redirect intent: {intent}")

    redirect_fields = {
        key: value
        for key, value in detail.items()
        if key
        in {
            "available_workflow",
            "available_workflows",
            "capability_status",
            "suggested_task_type",
        }
    }
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=detail["message"],
        metadata={
            "intent": intent,
            "kind": "clarification",
            "code": detail["code"],
            **redirect_fields,
            "clarification": dict(detail),
        },
    )
    return {
        "task_id": task.id,
        "status": "clarification_required",
        "intent": intent,
        "code": detail["code"],
        **redirect_fields,
        "clarification": dict(detail),
        "messages": repo.list_agent_messages(task.id),
    }

def _strategy_clarification_response(
    repo: TaskRepository, task: TaskRecord, clarification: dict
) -> dict:
    current_input = _strategy_input_snapshot(getattr(task, "strategy_input", None))
    clarification_payload = {
        **dict(clarification),
        "current_input": current_input,
    }
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=(
            f"{clarification['message']} Missing:"
            + ",".join(f"`{field}`" for field in clarification["missing_fields"])
            + ".Please add that to start strategy development; if only a technical preview is required, select explicitly the `quick-Track Analysis'."
        ),
        metadata={
            "intent": "strategy_clarification",
            "kind": "clarification",
            "current_input": current_input,
            "clarification": clarification_payload,
        },
    )
    return {
        "task_id": task.id,
        "status": "clarification_required",
        "current_input": current_input,
        "clarification": clarification_payload,
        "messages": repo.list_agent_messages(task.id),
    }

def _strategy_input_snapshot(strategy_input) -> dict | None:
    """Return only the governed strategy contract for clarification prefill."""

    if strategy_input is None:
        return None
    if not isinstance(strategy_input, dict):
        return asdict(strategy_input)

    allowed = (
        "entry_mode",
        "strategy_type",
        "objective",
        "max_bad_rate",
        "min_approval_rate",
        "baseline_strategy_id",
        "profit",
    )
    payload = {key: strategy_input[key] for key in allowed if key in strategy_input}
    profit = payload.get("profit")
    if profit is not None and not isinstance(profit, dict):
        payload["profit"] = asdict(profit)
    return payload

def _run_rule_strategy_setup(
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    backend,
    registry,
) -> dict | tuple:
    proposal = build_rule_strategy_proposal(
        registry,
        backend,
        task.id,
        task.source_dir,
        target_col=getattr(task, "target_col", "") or None,
        score_col=getattr(task, "score_col", "") or None,
    )
    notices = registry.consume_ingest_notices(task.id)
    note_text = ("\n" + " ".join(proposal.notes)) if proposal.notes else ""
    bad = f"(Bad rate{proposal.bad_rate:.2%})" if proposal.bad_rate is not None else ""
    slots = proposal.template_slots()
    context = _strategy_dataset_context(runtime, task, require_target=True)
    slots["sample_design_ref"] = _latest_matching_strategy_sample_design_ref(
        runtime,
        task,
        context=context,
        drop_nan_labels=False,
        allow_native_risk_development=True,
    )
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=(
            f"Start the rule-trucking.:Sample`{proposal.dataset_name}`,Target column`{proposal.target_col}`{bad}."
            f"The automatic excavation, selection, evaluation and retesting of the rejection rule will be left to manual decision-making only upon adoption.{note_text}"
            f"{_ingest_notice_text(notices)}"
        ),
        metadata={
            "intent": STRATEGY_INTENT_RULE_MINING,
            "ingest_notices": notices,
        },
    )
    return (proposal.template_id, slots, {})

def _run_strategy_monitoring_setup(
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    backend,
    registry,
) -> dict | tuple:
    proposal = build_monitoring_setup_proposal(
        registry,
        backend,
        runtime.settings.db_path,
        task.id,
        task.source_dir,
        target_col=getattr(task, "target_col", "") or None,
        score_col=getattr(task, "score_col", "") or None,
    )
    notices = registry.consume_ingest_notices(task.id)
    note_text = ("\n" + " ".join(proposal.notes)) if proposal.notes else ""
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=(
            f"Start tactical surveillance.:Locally Adopted Policy`{proposal.strategy_id}` Run a surveillance.,Sample"
            f"`{proposal.dataset_name}`.The monitoring is automatically completed and is manually determined at the police disposal door.{note_text}"
            f"{_ingest_notice_text(notices)}"
        ),
        metadata={
            "intent": STRATEGY_INTENT_MONITORING,
            "ingest_notices": notices,
        },
    )
    return (proposal.template_id, proposal.template_slots(), {})

_STRATEGY_SPEC = _TurnHandlerSpec(
    intent="strategy",
    setup_error_types=(StrategySetupError,),
    error_label="Error in policy analysis",
    run_setup=_run_strategy_setup,
    format_user_display=_identity_display_text,
    success_criteria=_strategy_success_criteria,
)

_STRATEGY_REQUEST_META_KEY = "strategy_request"

_STRATEGY_POOL_WORKFLOWS = frozenset(
    {
        "strategy_pool_add_candidate",
        "strategy_pool_remove_entry",
        "strategy_pool_set_action",
        "strategy_pool_reorder",
        "strategy_pool_compile",
    }
)

_STRATEGY_POOL_MEASUREMENT_WORKFLOWS = frozenset({"strategy_pool_impact"})

_STRATEGY_REQUEST_ACTION_RE = re.compile(
    r"(?:Development|Design|Development|Create|Generate|Build|Training|Physicalization|Solid|Freeze|Explore|Collapse|Combination|Summary|Reassembly|Collection|Refresh|Update|Rewind|Inventory|Records|Do it.|Calculate|Measurement|Analysis|Evaluation|View|Take a look.|Look at this.|Retrospect|Test|Authentication|Playback|Apply|Implementation|Write back|Back up.|Fill Back|Mark|"
    r"Comparison|Comparison|Search|Find|Search|Enumeration|Accepted|Adopt|Online.|Report|Document|Monitor|Floating|Digging|Selection|Filter|Reservations|Merge|Edit|"
    r"Add|Add|Into the pool.|Delete|Remove|Sort|Reorder|For|Compile|Preview|"
    r"develop|design|create|build|train|materialize|aggregate|collect|compute|calculate|analy[sz]e|evaluate|backtest|validate|replay|run|apply|compare|"
    r"search|find|enumerate|screen|adopt|report|monitor|mine|refine|select|merge|add|remove|delete|reorder|compile|preview)",
    re.IGNORECASE,
)

_STRATEGY_REQUEST_SUBJECT_RE = re.compile(
    r"(?:Policy|Context of the Policy Item|Project context|Current item(?:Status|Situation)|History(?:Version)?Policy|Policy sample|Sample design|Sample boundary|Policy pool|Rule pool|Access|Approval|Reject|Amount|Letters|Pricing|Interest rate|Group|Layer|Rule|Candidates|Candidates|Single Variable|Box|Autotree|Decision Tree|Leaves.|Leaf Node|Vote.|Voting|n[-_ ]?of[-_ ]?k|(?:Two-dimensional.|2\s*[dD])?\s*(?:Cross|cross)\s*(?:Matrix|matrix)|cutoff|Profit|Proceeds|"
    r"Recover.|Scroll Rate|Migration rate|Migration Matrix|Pricing matrix|Scale Matrix|Grid|ROA|"
    r"roll(?:\s|-|_)*rate|strategy(?:\s|-|_)*pool|pool|strategy|approval|reject|limit|pricing|segment|rule|candidate|automatic(?:\s|-|_)*tree|decision(?:\s|-|_)*tree|leaf|"
    r"candidate\s+bins?|\bbins?\b|univariate|binning|sample(?:\s|-|_)*design|profit|collection)",
    re.IGNORECASE,
)

_STRATEGY_AUTOMATIC_TREE_SHORTHAND_RE = re.compile(
    r"(?:Construction\s*(?:One.)?\s*(?:Automatic)?(?:Decision-making)?Tree(?!Status|Berry.|House)|"
    r"Training\s*(?:One.)?\s*(?:Automatic)?(?:Decision-making)?Tree(?:Model)?|"
    r"(?<![A-Za-z0-9_])(?:build|train)\s+(?:an?\s+)?"
    r"(?:(?:automatic|decision)\s+)?tree(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_STRATEGY_REQUEST_CANCEL_RE = re.compile(
    r"(?:Not yet.|Don't.|No, I'm fine.|Not implemented|Not yet.|Not yet.|Pause|Stop|Cancel|"
    r"do\s*not|don't|dont|stop|cancel|wait)",
    re.IGNORECASE,
)

_STRATEGY_REQUEST_NON_EXECUTION_RE = re.compile(
    r"(?:Do Not Execute|Do Not Run|Don't do it yet.|Don't run yet.|Not implemented yet|Do Not Run|"
    r"Preview only|Preview only|Only Discussion|Discussion only|Just talking.|For discussion only|"
    r"do\s+not\s+(?:execute|run)|don't\s+(?:execute|run)|"
    r"preview\s+only|discussion\s+only|discuss\s+only)",
    re.IGNORECASE,
)

_STRATEGY_POOL_COMPILE_REQUEST_RE = re.compile(
    r"(?=.*(?:Policy pool|Rule pool|strategy(?:\s|-|_)*pool|\bpool\b))"
    r"(?=.*(?:Compile|Preview|compile|preview))",
    re.IGNORECASE,
)

_STRATEGY_POOL_IMPACT_REQUEST_RE = re.compile(
    r"(?=.*(?:Policy pool|Rule pool|strategy(?:\s|-|_)*pool|\bpool\b))"
    r"(?=.*(?:Impact|Effects|Falls|Month by Month|Pass rate|Bad debt rate|Risk rate|Measurement|Evaluation|Calculate|Retrospect|"
    r"impact|effect|waterfall|monthly|approval\s+rate|bad\s+rate|risk\s+rate|"
    r"measure|assess|evaluat|calculate|backtest))",
    re.IGNORECASE,
)

_STRATEGY_POOL_VALIDATION_REQUEST_RE = re.compile(
    r"(?=.*(?:Policy pool|Rule pool|strategy(?:\s|-|_)*pool|\bpool\b))"
    r"(?=.*(?:Independent sample|Playback Independently|Playback Validation|Independent validation|"
    r"independent\s+(?:sample\s+)?replay|independent\s+validation|"
    r"replay\s+validation))"
    r"(?=.*(?:Authentication Set|Validation of samples|Validation Partition|"
    r"(?<![A-Za-z0-9_])(?:validation|oot)(?![A-Za-z0-9_])))",
    re.IGNORECASE,
)

_PROJECT_CONTEXT_UNAVAILABLE_ANSWER_RE = re.compile(
    r"(?:Not yet.|Not available|Not yet.|No, I'm not.|Not provided|Not Available|I don't know.|Unknown|To be completed|"
    r"unavailable|not\s+available|unknown|missing)",
    re.IGNORECASE,
)

_PROJECT_CONTEXT_ALL_PENDING_RE = re.compile(
    r"(?:These.|above|Above|All|All|Both|all\s+of\s+them|all)",
    re.IGNORECASE,
)

_PROJECT_CONTEXT_ANSWER_PATTERNS = {
    "current.status_fields.volume": re.compile(
        r"Number of applications|Import|Loans|Volume of business|Size|volume", re.IGNORECASE
    ),
    "current.status_fields.approval": re.compile(
        r"Pass rate|Approval rate|Access rate|approval", re.IGNORECASE
    ),
    "current.status_fields.risk": re.compile(
        r"Bad debt rate|Risk rate|Overdue rate|risk|bad\s+rate", re.IGNORECASE
    ),
    "current.status_fields.economics": re.compile(
        r"Proceeds|Profit|Cost|Economy|economics|profit", re.IGNORECASE
    ),
    "current.maturity_summary": re.compile(
        r"Mature|Show the window.|Watch the windows.|maturity|performance\s+window", re.IGNORECASE
    ),
    "historical_strategy_reviews": re.compile(
        r"History(?:Version)?Policy|Historical material|Old version policy|Previous version of the policy|history|historical",
        re.IGNORECASE,
    ),
}

class _StrategySampleDesignRequiredError(StrategySetupError):
    """The current strategy request has no exact mature sample-design binding."""

class _StrategySampleDesignPolicyMismatchError(StrategySetupError):
    """A valid newest sample exists, but the probed null-label policy differs."""

class _StrategyV2EvidenceSetupError(StrategySetupError):
    """Typed preflight failure for platform-owned V2 evidence discovery."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code

_STRATEGY_V2_ARTIFACT_ERRORS = (
    ArtifactTransactionError,
    TaskArtifactConflictError,
    TaskArtifactDataError,
    TaskArtifactNotFoundError,
    sqlite3.Error,
)

_STRATEGY_MODEL_EVIDENCE_V2_REQUEST_RE = re.compile(
    r"(?:Strategy\s+Model\s*Evidence(?:\s+V2)?|"
    r"Model\s*Evidence(?:\s+V2)?|Model evidence(?:\s*V2)?|"
    r"Single Variable(?:Candidates)?Evidence(?:Package|Summary)?|Authentication Single Variables(?:Candidates)?(?:Evidence|Result))",
    re.IGNORECASE,
)

def _strategy_request_preflight(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: CompiledStrategyRequestDraft,
) -> tuple[str, str] | None:
    """Reject any compiled request whose trusted Workflow is not wired yet."""

    if isinstance(draft, StandardWorkflowRequestDraft):
        return _standard_workflow_request_preflight(runtime, task, draft)

    if draft.candidate_design is not None:
        if draft.operation != "develop" or draft.strategy_type not in {
            "limit",
            "pricing",
            "segmentation",
        }:
            return (
                "candidate_strategy_request_invalid",
                "The definitive candidate input is only allowed for the development of the level, pricing or sub-group strategy.",
            )
        if any(
            value is not None
            for value in (
                draft.objective,
                draft.max_bad_rate,
                draft.min_approval_rate,
                draft.strategy_id,
                draft.adoption_reason,
                draft.profit,
            )
        ):
            return (
                "candidate_strategy_unused_fields",
                "Candidate development will be based on only candidate search space, exclusive economic calibre of type and a comparable type of baseline;"
                "Objectives, approval constraints, strategiesID,Preadmissive justifications or approvals of profit margins would not be silently ignored.",
            )
        if draft.baseline_strategy_id:
            baseline = StrategyRepository(runtime.settings.db_path).get_strategy_meta(
                draft.baseline_strategy_id
            )
            if baseline is None or baseline.get("task_id") != task.id:
                return (
                    "strategy_baseline_not_owned_by_task",
                    "No baseline strategy has been found in the current mandate and no cross-mission comparison can be made.",
                )
            if baseline.get("strategy_type") != draft.strategy_type:
                return (
                    "strategy_baseline_type_mismatch",
                    "The candidate strategy is not consistent with the baseline strategy type and cannot generate a symmetric comparison.",
                )
        return None

    if draft.strategy_spec is not None:
        if draft.strategy_id is not None:
            return (
                "strategy_request_conflicting_identity",
                "The request was made at the same time.strategy_spec andstrategy_id;One indicating new draft rules,"
                "One indicates that there is a strategy, and please clearly choose one.",
            )
        if draft.adoption_reason is not None:
            return (
                "strategy_request_unused_adoption_reason",
                "The current request is not for an operation, and the reasons for adoption are not silently ignored; please delete and reconfirm.",
            )
        if draft.operation in {"develop", "apply"}:
            if any(
                value is not None
                for value in (
                    draft.objective,
                    draft.max_bad_rate,
                    draft.min_approval_rate,
                    draft.baseline_strategy_id,
                    draft.profit,
                    draft.economics_inputs,
                )
            ):
                operation_label = "Construct" if draft.operation == "develop" else "Apply"
                return (
                    "strategy_typed_operation_unused_fields",
                    f"Direct{operation_label}The type rules are only usedstrategy_spec;Objective, constraints,"
                    "Baselines and economic parameters will not be ignored silently, please delete these fields or replace them with an analysis/Retrospect.",
                )
            return None
        if draft.operation in _TYPED_EVALUATION_OPERATIONS:
            if draft.objective is not None:
                return (
                    "strategy_typed_evaluation_unused_objective",
                    "Analysis of which rules are clearly established/Retroactivity won't be optimized.objective;Please deleteobjective,"
                    "(c) To retain clear constraints and economic parameters to be tested.",
                )
            if draft.strategy_type not in {"approval", "reject"} and any(
                value is not None
                for value in (
                    draft.max_bad_rate,
                    draft.min_approval_rate,
                    draft.profit,
                )
            ):
                return (
                    "strategy_typed_business_contract_not_wired",
                    f"{draft.strategy_type} Passage cannot be applied/Bad rate/Profit constraints;"
                    "Please retain the type exclusive rules and economic parameters.",
                )
            if draft.baseline_strategy_id:
                baseline = StrategyRepository(
                    runtime.settings.db_path
                ).get_strategy_meta(draft.baseline_strategy_id)
                if baseline is None or baseline.get("task_id") != task.id:
                    return (
                        "strategy_baseline_not_owned_by_task",
                        "No baseline strategy has been found in the current mandate and no cross-mission comparison can be made.",
                    )
                if baseline.get("strategy_type") != draft.strategy_type:
                    return (
                        "strategy_baseline_type_mismatch",
                        "The new draft rules were not consistent with the type of baseline strategy and could not generate a comparison of calibre.",
                    )
            return None
        return (
            "strategy_operation_not_wired",
            f"Recognized{draft.operation} Requests, but this operation cannot be replaced by a typology assessment process;"
            "The current situation is not to be measured in silence.",
        )
    if draft.operation in {
        *_STORED_EVALUATION_OPERATIONS,
        "apply",
        "report",
        "adopt",
    }:
        return _stored_strategy_request_preflight(runtime, task, draft)
    if draft.operation == "develop":
        if draft.strategy_id is not None or draft.adoption_reason is not None:
            return (
                "strategy_request_unused_fields",
                "New policy development will not be used alreadystrategy_id Or pre-identify the reasons for adoption, and delete the fields.",
            )
        if draft.strategy_type not in {"approval", "reject"}:
            return (
                "strategy_typed_spec_required",
                f"{draft.strategy_type} Strategy development requires clear draft rules for typology;"
                "Please add the conditions, actions and values of the rules.",
            )
        if draft.objective not in {"max_approval", "max_profit"}:
            return (
                "strategy_objective_required",
                "Approval/Refusal to develop a strategy requires clarityobjective=max_approval ormax_profit.",
            )
        if draft.max_bad_rate is None and draft.min_approval_rate is None:
            return (
                "strategy_constraint_required",
                "Please indicate at least the maximum bad debt rate or the minimum pass rate, and that the platform will not fill in the operational constraints.",
            )
        if draft.objective == "max_profit" and draft.profit is None:
            return (
                "strategy_profit_contract_required",
                "The profit target needs to be complete.EAD/PD Columns and interest rates, cost of funds,LGD,Single cost, time calibre.",
            )
        return None
    if draft.operation == "mine_rules":
        if any(
            value is not None
            for value in (
                draft.objective,
                draft.max_bad_rate,
                draft.min_approval_rate,
                draft.baseline_strategy_id,
                draft.strategy_id,
                draft.adoption_reason,
                draft.profit,
                draft.economics_inputs,
            )
        ):
            return (
                "strategy_rule_request_unused_fields",
                "The drill entrance is not currently using targets, constraints, tactics.ID (b) Profit fields;"
                "Please delete these fields to avoid silent disregard of the calibre.",
            )
        if draft.strategy_type != "reject":
            return (
                "strategy_rule_type_required",
                "Current rule digs to generate rejection rule, please specify the type of strategy asreject.",
            )
        return None
    if draft.operation == "monitor":
        if any(
            value is not None
            for value in (
                draft.objective,
                draft.max_bad_rate,
                draft.min_approval_rate,
                draft.baseline_strategy_id,
                draft.adoption_reason,
                draft.profit,
                draft.economics_inputs,
            )
        ):
            return (
                "strategy_monitor_request_unused_fields",
                "The control entrance is subject only to the control; objectives, constraints, baselines, reasons for acceptance and profit fields"
                "Do not be ignored silently, please delete and try again.",
            )
        adopted = [
            meta
            for meta in StrategyRepository(runtime.settings.db_path).list_meta_for_task(
                task.id
            )
            if meta.get("asset_status") == ASSET_STATUS_ADOPTED_LOCAL
        ]
        if not adopted:
            return (
                "strategy_adopted_version_required",
                "The current mission has no locally adopted strategy, so please complete the back-up and manual adoption before initiating the monitoring."
                "Locally accepted, not representing production on line.",
            )
        selected = adopted[-1]
        if draft.strategy_id and draft.strategy_id != selected.get("id"):
            return (
                "strategy_monitor_target_mismatch",
                "The current security portal will only be the latest locally adopted strategy in the mission;"
                "The policy in the requestID Not consistent with it.",
            )
        if draft.strategy_type != selected.get("strategy_type"):
            return (
                "strategy_monitor_type_mismatch",
                "The type of strategy requested is not consistent with the latest locally adopted strategy within the mission."
                "Please confirm the subject.",
            )
        return None
    return (
        "strategy_operation_not_wired",
        f"Recognized{draft.operation} Request, but trustableWorkflow Not yet connected;"
        "It is not downgraded to other tactical operations.",
    )

def _strategy_pool_impact_pool_binding(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    strategy_type: str,
) -> tuple[Mapping, dict[str, object]]:
    """Load one non-empty Pool and return its exact confirmation binding."""

    if strategy_type not in {"approval", "reject"}:
        raise StrategySetupError(
            "Strategy Pool First impact measureV2 Even if only supportapproval/reject;"
            "Other types of strategy require a subsequent type of exclusive calibre."
        )
    try:
        pool = StrategyCandidatePoolRepository(
            runtime.settings.db_path
        ).get_current(task.id, strategy_type)
    except Exception as exc:
        raise StrategySetupError(
            "CurrentStrategy Pool The state cannot be verified through completeness and impact measurement cannot be performed."
        ) from exc
    if pool is None:
        raise StrategySetupError(
            f"No current task.{strategy_type} Strategy Pool,Impact cannot be measured."
        )
    if not _strategy_pool_entries(pool):
        raise StrategySetupError(
            f"Current{strategy_type} Strategy Pool is empty; please add the candidacy rule before measuring impact."
        )
    try:
        binding = {
            "strategy_type": strategy_type,
            "expected_pool_revision": int(pool["revision"]),
            "expected_pool_snapshot_hash": strategy_pool_snapshot_hash(pool),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "CurrentStrategy Pool revision/hash The binding is incomplete and impact measurement cannot be performed."
        ) from exc
    return pool, binding

def _strategy_dsl_delivery_strategy_ref(
    snapshot: object,
    *,
    task_id: str,
) -> dict[str, object]:
    if not isinstance(snapshot, Mapping):
        raise _StrategyV2EvidenceSetupError(
            "strategy_dsl_delivery_strategy_invalid",
            "Policy lacks a certified atomsnapshot,Or not in the current mandate.",
        )
    try:
        strategy = snapshot["strategy"]
        metadata = snapshot["metadata"]
        spec_hash = snapshot["strategy_spec_hash"]
        strategy_id = str(metadata["id"])
        strategy_type = str(metadata["strategy_type"])
        version = metadata["version"]
        canonical_spec_hash = (
            strategy_spec_hash(strategy.spec)
            if getattr(strategy, "spec", None) is not None
            else None
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_dsl_delivery_strategy_invalid",
            "Policysnapshot It's...identity,type,version orspec hash Incomplete.",
        ) from exc
    if (
        metadata.get("task_id") != task_id
        or getattr(strategy, "id", None) != strategy_id
        or getattr(strategy, "strategy_type", None) != strategy_type
        or strategy_type
        not in {"approval", "reject", "limit", "pricing", "segmentation"}
        or isinstance(version, bool)
        or not isinstance(version, int)
        or version < 1
        or not isinstance(spec_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", spec_hash) is None
        or canonical_spec_hash != spec_hash
    ):
        raise _StrategyV2EvidenceSetupError(
            "strategy_dsl_delivery_strategy_invalid",
            "strategy_id Must be part of the current mandate and have a consistent five categoriestype,Positive and"
            " canonical Strategy DSL/spec hash;History compatibility requires migration.",
        )
    return {
        "strategy_id": strategy_id,
        "expected_strategy_type": strategy_type,
        "expected_version": version,
        "expected_spec_hash": spec_hash,
    }

def _strategy_impact_cube_partitions(
    inputs: Mapping,
    *,
    sample,
) -> list[str]:
    order = ("development", "validation", "oot")
    try:
        counts = sample.membership["header"]["counts"]
        approval_counts = counts["approval"]
        risk_counts = counts["risk"]
    except (KeyError, TypeError) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_sample_invalid",
            "StrategySampleDesign V2 Missingapproval/risk Zone count.",
        ) from exc
    for population_counts in (approval_counts, risk_counts):
        if not isinstance(population_counts, Mapping) or any(
            isinstance(population_counts.get(partition), bool)
            or not isinstance(population_counts.get(partition), int)
            or population_counts[partition] < 0
            for partition in order
        ):
            raise _StrategyV2EvidenceSetupError(
                "strategy_impact_cube_sample_invalid",
                "StrategySampleDesign V2 , the partition count is invalid.",
            )

    requested = inputs.get("partitions")
    if requested is None:
        selected = [
            partition
            for partition in order
            if approval_counts[partition] > 0 and risk_counts[partition] > 0
        ]
    else:
        if (
            not isinstance(requested, Sequence)
            or isinstance(requested, str | bytes | bytearray)
        ):
            raise _StrategyV2EvidenceSetupError(
                "strategy_impact_cube_partitions_invalid",
                "ImpactCube partitions Must be a clear list of partitions.",
            )
        requested_set = set(requested)
        if (
            not requested_set
            or len(requested_set) != len(requested)
            or not requested_set.issubset(order)
        ):
            raise _StrategyV2EvidenceSetupError(
                "strategy_impact_cube_partitions_invalid",
                "ImpactCube Only accept non-repetition.development,validation,oot Division.",
            )
        selected = [
            partition for partition in order if partition in requested_set
        ]
    empty = [
        partition
        for partition in selected
        if approval_counts[partition] == 0 or risk_counts[partition] == 0
    ]
    if not selected or empty:
        detail = ",".join(empty) if empty else "All"
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_partition_empty",
            f"Selected Partitions{detail} Not all at once.approval andrisk (a) Overall;"
            "Please adjust the sample design or select non-empty partitions.",
        )
    return selected

def _strategy_impact_cube_dimensions(
    inputs: Mapping,
    *,
    sample,
) -> dict[str, str | None]:
    columns = tuple(sample.source_binding.columns)
    roles = dict(sample.source_binding.semantic_field_roles)
    provenance_request = sample.provenance.get("request")
    field_bindings = (
        provenance_request.get("field_bindings")
        if isinstance(provenance_request, Mapping)
        else None
    )
    if not isinstance(field_bindings, Mapping):
        field_bindings = {}

    def unique_role(role: str) -> str | None:
        matches = sorted(
            column
            for column, assigned in roles.items()
            if assigned == role and column in columns
        )
        if len(matches) > 1:
            raise _StrategyV2EvidenceSetupError(
                "strategy_impact_cube_dimension_ambiguous",
                f"There are several samples available.`{role}` Semantic fields:{','.join(matches)};"
                "Please specify the listing in the request.",
            )
        return matches[0] if matches else None

    defaults = {
        "month_col": field_bindings.get("month_field") or unique_role("month"),
        "group_col": field_bindings.get("group_field"),
        "segment_col": unique_role("segment"),
    }
    result: dict[str, str | None] = {}
    used: set[str] = set()
    for field in ("month_col", "group_col", "segment_col"):
        explicit = inputs.get(field)
        selected = explicit if explicit is not None else defaults[field]
        if selected is not None and (
            not isinstance(selected, str) or selected not in columns
        ):
            raise _StrategyV2EvidenceSetupError(
                "strategy_impact_cube_dimension_invalid",
                f"ImpactCube Dimensions{field} Not in the data column of the latest sample bound.",
            )
        if selected is not None and roles.get(selected) in {"id", "target"}:
            raise _StrategyV2EvidenceSetupError(
                "strategy_impact_cube_dimension_sensitive",
                f"Fields`{selected}` The semantic character is{roles[selected]},"
                "I can't do it.ImpactCube Aggregation dimensions.",
            )
        if selected is not None and selected in used:
            if explicit is not None:
                raise _StrategyV2EvidenceSetupError(
                    "strategy_impact_cube_dimension_duplicate",
                    "Months, grouping and grouping dimensions must be used in different fields.",
                )
            selected = None
        result[field] = selected
        if selected is not None:
            used.add(selected)
    return result

def _strategy_impact_cube_economics(
    value: object,
    *,
    sample,
) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_economics_invalid",
            "ImpactCube economics_inputs It must be.typed column/scalar Map.",
        )
    columns = set(sample.source_binding.columns)
    roles = dict(sample.source_binding.semantic_field_roles)
    result: dict[str, object] = {}
    for component, raw_binding in sorted(value.items()):
        if not isinstance(component, str) or not isinstance(raw_binding, Mapping):
            raise _StrategyV2EvidenceSetupError(
                "strategy_impact_cube_economics_invalid",
                "ImpactCube economics_inputs The component or binding structure is invalid.",
            )
        binding = dict(raw_binding)
        if binding.get("kind") == "column":
            column = binding.get("column")
            if (
                not isinstance(column, str)
                or column not in columns
                or roles.get(column) in {"id", "target"}
            ):
                raise _StrategyV2EvidenceSetupError(
                    "strategy_impact_cube_economics_column_invalid",
                    f"Economic parameters{component} Non-sensitive business columns were not bound to the current sample.",
                )
        result[component] = binding
    return result

def _strategy_impact_cube_current_strategy_ref(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    strategy_type: str,
    requested_id: object,
) -> dict[str, str] | None:
    if requested_id is None:
        return None
    if not isinstance(requested_id, str) or not requested_id:
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_current_strategy_invalid",
            "The current strategy needs to be complete.strategy_id.",
        )
    repository = StrategyRepository(runtime.settings.db_path)
    try:
        snapshot = repository.get_strategy_snapshot(requested_id)
    except Exception as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_current_strategy_invalid",
            "Current policycanonical StrategySpec Could not close temporary folder: %s",
        ) from exc
    if snapshot is None:
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_current_strategy_invalid",
            "current_strategy_id It must be the current task, the same type and completecanonical "
            "StrategySpec;The platform does not compare across tasks or types.",
        )
    meta = snapshot["metadata"]
    strategy = snapshot["strategy"]
    spec_hash = snapshot["strategy_spec_hash"]
    if (
        strategy.spec is None
        or meta.get("task_id") != task_id
        or meta.get("strategy_type") != strategy_type
        or strategy.strategy_type != strategy_type
        or not isinstance(spec_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", spec_hash) is None
    ):
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_current_strategy_invalid",
            "current_strategy_id It must be the current task, the same type and completecanonical "
            "StrategySpec;The platform does not compare across tasks or types.",
        )
    return {
        "strategy_id": requested_id,
        "expected_strategy_spec_hash": spec_hash,
    }

def _strategy_impact_cube_registry_token(
    artifacts: Sequence[Mapping],
    *,
    selected_artifact_ids: set[str],
) -> str:
    relevant = [
        {
            "id": item.get("id"),
            "kind": item.get("kind"),
            "content_hash": item.get("content_hash"),
            "origin_tool": item.get("origin_tool"),
            "provenance": item.get("provenance"),
        }
        for item in artifacts
        if item.get("id") in selected_artifact_ids
        or item.get("kind")
        in {
            SAMPLE_DESIGN_V2_MEMBERSHIP_ARTIFACT_KIND,
            SAMPLE_DESIGN_V2_BUNDLE_ARTIFACT_KIND,
        }
    ]
    return hashlib.sha256(
        json.dumps(
            relevant,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

def _strategy_v2_read_runtime(runtime: DriverTurnRuntime) -> SimpleNamespace:
    backend, registry = _modeling_data_runtime(runtime.settings)
    return SimpleNamespace(
        settings=runtime.settings,
        backend=backend,
        registry=registry,
        task_artifacts=TaskArtifactRepository(runtime.settings.db_path),
    )

def _strategy_v2_artifact_snapshot(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
) -> tuple[dict, ...]:
    """Read one deterministic registry snapshot or expose a governed error."""

    try:
        return tuple(read_runtime.task_artifacts.list_for_task(task_id))
    except _STRATEGY_V2_ARTIFACT_ERRORS as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_evidence_v2_registry_unavailable",
            "Could not read current taskStrategySampleDesign V2 artifact registry.",
        ) from exc

def _strategy_v2_registry_token(artifacts: Sequence[Mapping]) -> str:
    """CAS token for evidence rows relevant to one ModelEvidence V2 plan."""

    try:
        return strategy_model_evidence_registry_snapshot_token(artifacts)
    except StrategyError as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_evidence_v2_registry_unavailable",
            "Strategy ModelEvidence V2 registry snapshot Can not regulate this question.",
        ) from exc

def _strategy_report_read_runtime(
    runtime: DriverTurnRuntime,
) -> SimpleNamespace:
    backend, registry = _modeling_data_runtime(runtime.settings)
    task_artifacts = TaskArtifactRepository(runtime.settings.db_path)
    return SimpleNamespace(
        settings=runtime.settings,
        backend=backend,
        registry=registry,
        task_artifacts=task_artifacts,
        strategies=StrategyRepository(runtime.settings.db_path),
        experiments=ExperimentStore(runtime.settings.db_path),
        modeling_repo=ModelingRepository(runtime.settings.db_path),
    )

def _strategy_report_artifact_window(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    kind: str,
    limit: int,
    unavailable_code: str,
    invalid_code: str,
    label: str,
) -> tuple[tuple[Mapping, ...], int]:
    """Read one exact newest-first artifact window without full-task allocation."""

    try:
        records, total = (
            read_runtime.task_artifacts.list_recent_for_task_kind_with_count(
                task_id,
                kind,
                limit=limit,
            )
        )
    except _STRATEGY_V2_ARTIFACT_ERRORS as exc:
        raise _StrategyV2EvidenceSetupError(
            unavailable_code,
            f"Could not close temporary folder: %s{label} artifact window.",
        ) from exc
    try:
        if (
            not isinstance(records, Sequence)
            or isinstance(records, str | bytes | bytearray)
            or isinstance(total, bool)
            or not isinstance(total, int)
            or total < 0
        ):
            raise ValueError(f"{label} artifact window is invalid")
        window = tuple(records)
        if len(window) != min(total, limit) or any(
            not isinstance(item, Mapping) or item.get("kind") != kind
            for item in window
        ):
            raise ValueError(f"{label} artifact window is inconsistent")
        return window, total
    except (TypeError, ValueError) as exc:
        raise _StrategyV2EvidenceSetupError(
            invalid_code,
            f"{label} artifact Window and precise total orkind Inconsistencies;"
            "Othernewest-first The selection of the boundary cannot be confirmed.",
        ) from exc

def _strategy_report_requested_pool_type(
    source_message: Mapping | None,
) -> str | None:
    text = (
        str(source_message.get("content") or "")
        if isinstance(source_message, Mapping)
        else ""
    )
    masked = list(text)
    for match in _STRATEGY_REPORT_POOL_TITLE_RE.finditer(text):
        masked[match.start() : match.end()] = " " * (
            match.end() - match.start()
        )
    command_text = "".join(masked)
    actions = tuple(_STRATEGY_REPORT_POOL_COMMAND_RE.finditer(command_text))
    selected: list[str] = []
    negated: list[str] = []
    for strategy_type, pattern in _STRATEGY_REPORT_POOL_TYPE_PATTERNS.items():
        for match in pattern.finditer(command_text):
            prefix = command_text[max(0, match.start() - 40) : match.start()]
            if _STRATEGY_REPORT_POOL_TYPE_NEGATION_RE.search(prefix):
                if strategy_type not in negated:
                    negated.append(strategy_type)
                continue
            clause_start = max(
                command_text.rfind(separator, 0, match.start())
                for separator in (",", ",", ";", ";", ".", ".", "!", "!", "?", "?", "\n")
            )
            clause_end_candidates = [
                position
                for separator in (
                    ",",
                    ",",
                    ";",
                    ";",
                    ".",
                    ".",
                    "!",
                    "!",
                    "?",
                    "?",
                    "\n",
                )
                if (position := command_text.find(separator, match.end())) >= 0
            ]
            clause_end = (
                min(clause_end_candidates)
                if clause_end_candidates
                else len(command_text)
            )
            local_clause = command_text[clause_start + 1 : clause_end]
            if _STRATEGY_REPORT_POOL_HISTORY_RE.search(local_clause):
                continue

            inside_creation = any(
                action.start() <= match.start()
                and match.end() <= action.end()
                for action in actions
            )
            explicitly_selected = (
                _STRATEGY_REPORT_POOL_SELECTOR_RE.search(prefix) is not None
                and _strategy_report_pool_selector_shares_command(
                    command_text,
                    mention_start=match.start(),
                    mention_end=match.end(),
                    actions=actions,
                )
            )
            if inside_creation or explicitly_selected:
                if strategy_type not in selected:
                    selected.append(strategy_type)
                break
    if len(selected) > 1:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_pool_type_ambiguous",
            "Multiple names for the same report requestStrategy Pool Type;"
            "Please select only one strategy type.",
        )
    if not selected and negated:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_pool_type_required",
            "The reporting request is only ruled out.Pool Type, not sure sure which choice to use"
            "Approval/Access, denial, amount, pricing or sub-groupingPool;The platform won't be bound."
            "- It's rejected.Pool.",
        )
    return selected[0] if selected else None

def _strategy_report_pool_selector_shares_command(
    utterance: str,
    *,
    mention_start: int,
    mention_end: int,
    actions: Sequence[re.Match[str]],
) -> bool:
    sentence_start = max(
        utterance.rfind(separator, 0, mention_start)
        for separator in (".", ".", "!", "!", "?", "?", ";", ";", "\n")
    )
    sentence_end_candidates = [
        position
        for separator in (".", ".", "!", "!", "?", "?", ";", ";", "\n")
        if (position := utterance.find(separator, mention_end)) >= 0
    ]
    sentence_end = (
        min(sentence_end_candidates)
        if sentence_end_candidates
        else len(utterance)
    )
    return any(
        sentence_start < action.start()
        and action.end() <= sentence_end
        for action in actions
    )

def _strategy_report_current_pool_binding(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    requested_type: str | None,
):
    repository = StrategyCandidatePoolRepository(
        read_runtime.settings.db_path
    )
    current: dict[str, Mapping] = {}
    strategy_types = (
        (requested_type,)
        if requested_type is not None
        else (
            "approval",
            "reject",
            "limit",
            "pricing",
            "segmentation",
        )
    )
    try:
        for strategy_type in strategy_types:
            pool = repository.get_current(task_id, strategy_type)
            if pool is not None and pool.get("entries"):
                current[strategy_type] = pool
    except Exception as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_pool_invalid",
            "CurrentStrategy Pool head/revision No integrity review was possible.",
        ) from exc

    if requested_type is not None:
        selected_type = requested_type
        if selected_type not in current:
            raise _StrategyV2EvidenceSetupError(
                "strategy_report_bundle_v2_pool_required",
                f"Current task is not empty{selected_type} Strategy Pool.",
            )
    elif len(current) == 1:
        selected_type = next(iter(current))
    elif not current:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_pool_required",
            "Current task is not available for reportingStrategy Pool.",
        )
    else:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_pool_type_required",
            "There are several non-empty currently available simultaneouslyStrategy Pool;Please specify in the reporting request"
            "Select approval/Access, denial, amount, pricing or sub-groupingPool,The platform won't guess.",
        )

    selected = current[selected_type]
    try:
        return load_current_strategy_candidate_pool_artifact(
            read_runtime,
            task_id=task_id,
            strategy_type=selected_type,
            expected_pool_revision=selected["revision"],
            expected_pool_snapshot_hash=strategy_pool_snapshot_hash(selected),
        )
    except (StrategyError, *_STRATEGY_V2_ARTIFACT_ERRORS) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_pool_invalid",
            f"Current{selected_type} Strategy Pool It\'s...artifact,Source or data binding"
            "No integrity review was conducted.",
        ) from exc

def _strategy_report_latest_sample_binding(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
):
    bundles, _total = _strategy_report_artifact_window(
        read_runtime,
        task_id=task_id,
        kind=SAMPLE_DESIGN_V2_BUNDLE_ARTIFACT_KIND,
        limit=1,
        unavailable_code="strategy_report_bundle_v2_sample_registry_unavailable",
        invalid_code="strategy_report_bundle_v2_sample_invalid",
        label="StrategySampleDesign V2 bundle",
    )
    if not bundles:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_sample_required",
            "No current task.StrategySampleDesign V2 membership/bundle Evidence.",
        )
    newest = bundles[0]
    provenance = newest.get("provenance")
    if not isinstance(provenance, Mapping):
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_sample_invalid",
            "LatestStrategySampleDesign V2 bundle provenance (a) Damaged;"
            "The platform does not retreat to the old sample design.",
        )
    try:
        return load_any_strategy_sample_design_v2_artifacts(
            read_runtime,
            task_id=task_id,
            membership_artifact_id=provenance.get("membership_artifact_id"),
            expected_membership_artifact_content_hash=provenance.get(
                "membership_artifact_content_hash"
            ),
            bundle_artifact_id=newest.get("id"),
            expected_bundle_artifact_content_hash=newest.get("content_hash"),
            expected_bundle_id=provenance.get("bundle_id"),
            expected_sample_design_id=provenance.get("sample_design_id"),
            expected_sample_design_content_hash=provenance.get(
                "sample_design_content_hash"
            ),
        )
    except (
        StrategyError,
        TypeError,
        ValueError,
        *_STRATEGY_V2_ARTIFACT_ERRORS,
    ) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_sample_invalid",
            "LatestStrategySampleDesign V2 membership/bundle Document not adopted,"
            "registry,provenance or data drift review; platform does not retreat to old version.",
        ) from exc

def _strategy_report_sample_ref(sample) -> dict[str, object]:
    design = sample.bundle["sample_design"]
    return {
        "membership_artifact_id": sample.membership_artifact_id,
        "expected_membership_artifact_content_hash": (
            sample.membership_artifact_content_hash
        ),
        "bundle_artifact_id": sample.bundle_artifact_id,
        "expected_bundle_artifact_content_hash": (
            sample.bundle_artifact_content_hash
        ),
        "expected_bundle_id": sample.bundle["bundle_id"],
        "expected_sample_design_id": design["sample_design_id"],
        "expected_sample_design_content_hash": design["content_hash"],
    }

def _strategy_report_latest_candidate_stability_binding(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    sample,
    pool,
):
    """Select the newest authenticated stability evidence for current sources.

    Every stability artifact is authenticated before its source identity is
    inspected.  A valid artifact for another Pool/SampleDesign is skipped; a
    corrupt candidate fails closed because its actual source cannot be trusted
    and the selector must not silently fall back to older evidence.
    """

    records, total = _strategy_report_artifact_window(
        read_runtime,
        task_id=task_id,
        kind=CANDIDATE_STABILITY_ARTIFACT_KIND,
        limit=_STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT,
        unavailable_code=(
            "strategy_report_bundle_v2_candidate_stability_registry_unavailable"
        ),
        invalid_code="strategy_report_bundle_v2_candidate_stability_invalid",
        label="candidate stability",
    )
    for item in records:
        provenance = item.get("provenance")
        try:
            binding = load_candidate_stability_artifact(
                read_runtime,
                task_id=task_id,
                artifact_id=item.get("id"),
                expected_artifact_content_hash=item.get("content_hash"),
                expected_stability_id=(
                    provenance.get("stability_id")
                    if isinstance(provenance, Mapping)
                    else None
                ),
                expected_stability_content_hash=(
                    provenance.get("stability_content_hash")
                    if isinstance(provenance, Mapping)
                    else None
                ),
            )
        except (
            StrategyError,
            TypeError,
            ValueError,
            *_STRATEGY_V2_ARTIFACT_ERRORS,
        ) as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_report_bundle_v2_candidate_stability_invalid",
                "The latest candidate for the decision is steady on a monthly basis.artifact Document not adopted,registry,"
                "provenance or content integrity review; its authenticityPool/SampleDesign "
                "Identity cannot be confirmed and the platform will not retreat to the old stability evidence.",
            ) from exc
        try:
            validate_candidate_stability_report_compatibility(
                candidate_stability=binding,
                sample_design=sample,
                candidate_pool=pool,
            )
        except StrategyError:
            continue
        return binding
    if total > _STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_candidate_stability_"
            "selection_window_exhausted",
            "Fully certified for update"
            f"{_STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT} Each candidate is stable on a monthly basis."
            "artifact,But...registry still record earlier; platform cannot prove outside window"
            "Cannot initialise Evolution's mail component.Pool/SampleDesign The government has been able to provide the necessary information to the government."
            "No reporting plan was created this time.",
        )
    return None

def _strategy_report_latest_voting_search_binding(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    sample,
    sample_ref: Mapping[str, object],
    pool,
):
    """Select newest-to-oldest fully authenticated exact Voting search evidence."""

    records, total = _strategy_report_artifact_window(
        read_runtime,
        task_id=task_id,
        kind=VOTING_CANDIDATE_SEARCH_ARTIFACT_KIND,
        limit=_STRATEGY_REPORT_VOTING_SEARCH_REPLAY_LIMIT,
        unavailable_code=(
            "strategy_report_bundle_v2_voting_candidate_search_"
            "registry_unavailable"
        ),
        invalid_code=(
            "strategy_report_bundle_v2_voting_candidate_search_invalid"
        ),
        label="Voting candidate search",
    )
    if not records:
        return None
    try:
        current_development = bind_strategy_pool_development_execution(
            read_runtime,
            pool,
        )
        entries = [
            dict(entry)
            for entry in pool.pool["entries"]
            if entry["enabled"] is True
            and entry["source"]["asset_type"]
            != VOTING_CANDIDATE_ASSET_TYPE
        ]
        candidate_ids = sorted(str(entry["rule_id"]) for entry in entries)
        requirements = project_pool_entry_requirements(entries)
        if requirements:
            resolved = resolve_pool_requirements(
                read_runtime,
                task_id=task_id,
                compiled_design={"requirements": list(requirements)},
                sample_design=sample,
            )
            requirement_bindings = pool_requirement_bindings_provenance(
                resolved
            )
        else:
            requirement_bindings = None
        execution_sample_ref = (
            derive_strategy_model_evidence_candidate_execution_ref(sample)
        )
        if (
            _strategy_report_sample_ref(sample) != dict(sample_ref)
            or current_development.sample_design.to_ref_dict()
            != execution_sample_ref
        ):
            return None
    except (
        KeyError,
        ModelingError,
        StrategyError,
        TypeError,
        ValueError,
        *_STRATEGY_V2_ARTIFACT_ERRORS,
    ) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_voting_candidate_search_invalid",
            "CurrentStrategy Pool It's...Voting Searching for matching identities cannot be fully certified;"
            "No reporting plan was created this time.",
        ) from exc

    for item in records:
        try:
            binding = load_historical_voting_candidate_search_artifact(
                read_runtime,
                task_id=task_id,
                artifact_id=item.get("id"),
                expected_artifact_content_hash=item.get("content_hash"),
            )
        except (
            KeyError,
            ModelingError,
            StrategyError,
            TypeError,
            ValueError,
            *_STRATEGY_V2_ARTIFACT_ERRORS,
        ) as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_report_bundle_v2_voting_candidate_search_invalid",
                "The latest pending decision.Voting Can not open messageartifact Not safe through history."
                "Documentation,registry,provenance,Pool or data binding review; its authenticity"
                "The identity could not be confirmed and the platform would not retreat to the old search evidence.",
            ) from exc
        if _strategy_report_voting_search_matches(
            binding,
            task_id=task_id,
            pool=pool,
            current_development=current_development,
            execution_sample_ref=execution_sample_ref,
            candidate_ids=candidate_ids,
            requirement_bindings=requirement_bindings,
        ):
            return binding
    if total > _STRATEGY_REPORT_VOTING_SEARCH_REPLAY_LIMIT:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_voting_candidate_search_"
            "selection_window_exhausted",
            "Fully certified for update"
            f"{_STRATEGY_REPORT_VOTING_SEARCH_REPLAY_LIMIT} individualVoting Candidates"
            "Searchartifact,But...registry Early search records still exist; the platform cannot prove"
            "There is no current outside the windowPool/SampleDesign The search for evidence is completely consistent."
            "No reporting plan was created this time.",
        )
    return None

def _strategy_report_voting_search_matches(
    binding,
    *,
    task_id: str,
    pool,
    current_development,
    execution_sample_ref: Mapping[str, object],
    candidate_ids: Sequence[str],
    requirement_bindings: Mapping[str, object] | None,
) -> bool:
    provenance = binding.artifact_provenance
    historical_development = binding.pool_development
    historical_pool = historical_development.pool
    if (
        binding.task_id != task_id
        or historical_pool.artifact_id != pool.artifact_id
        or historical_pool.artifact_content_hash
        != pool.artifact_content_hash
        or historical_pool.pool != pool.pool
        or provenance["task_id"] != task_id
        or provenance["pool_ref"]
        != {
            "artifact_id": pool.artifact_id,
            "artifact_content_hash": pool.artifact_content_hash,
            "pool_id": pool.pool["pool_id"],
            "strategy_type": pool.pool["strategy_type"],
            "revision": pool.pool["revision"],
            "revision_id": pool.pool["revision_id"],
            "snapshot_hash": pool.pool["snapshot_hash"],
        }
    ):
        return False
    if historical_development.sample_design.to_ref_dict() != dict(
        execution_sample_ref
    ):
        return False

    dataset = current_development.dataset
    execution_sample = current_development.sample_design
    expected_dataset = {
        "task_id": dataset.task_id,
        "dataset_id": dataset.dataset_id,
        "dataset_source_path": dataset.source_path,
        "dataset_content_hash": dataset.content_hash,
        "dataset_registry_metadata_hash": dataset.registry_metadata_hash,
        "workspace_revision": execution_sample.workspace_revision,
        "workspace_generation": execution_sample.workspace_generation,
        "semantic_mapping_hash": execution_sample.semantic_mapping_hash,
    }
    target = provenance["target_binding"]
    expected_target_identity = {
        "column": execution_sample.target_col,
        "raw_bad_value": execution_sample.target_bad_value,
        "normalized_bad_value": 1,
        "drop_nan_labels": execution_sample.drop_nan_labels,
        "sample_partition": execution_sample.reference.partition,
    }
    if (
        provenance["dataset_binding"] != expected_dataset
        or provenance["sample_design_ref"]
        != execution_sample.to_ref_dict()
        or provenance["sample_context_hash"]
        != current_development.evidence_identity["sample_context_hash"]
        or any(
            target.get(field) != expected
            for field, expected in expected_target_identity.items()
        )
        or target["labeled_count"] + target["nan_labels_dropped"]
        != execution_sample.development_population_count
        or (
            target["nan_labels_dropped"] > 0
            and not execution_sample.drop_nan_labels
        )
        or provenance["observation_bindings"]
        != {
            "weight_col": execution_sample.weight_col,
            "amount_col": execution_sample.loan_amount_col,
        }
        or provenance["requirement_bindings"]
        != (
            None
            if requirement_bindings is None
            else dict(requirement_bindings)
        )
        or binding.result["configuration"]["candidate_ids"]
        != list(candidate_ids)
    ):
        return False
    return True

def _strategy_report_latest_cross_search_binding(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    sample,
):
    """Select the newest fully authenticated Cross search for this V2 sample."""

    records, total = _strategy_report_artifact_window(
        read_runtime,
        task_id=task_id,
        kind=CROSS_CANDIDATE_SEARCH_ARTIFACT_KIND,
        limit=_STRATEGY_REPORT_CROSS_SEARCH_REPLAY_LIMIT,
        unavailable_code=(
            "strategy_report_bundle_v2_cross_candidate_search_"
            "registry_unavailable"
        ),
        invalid_code=(
            "strategy_report_bundle_v2_cross_candidate_search_invalid"
        ),
        label="Cross candidate search",
    )
    for item in records:
        try:
            binding = load_cross_candidate_search_artifact(
                read_runtime,
                task_id=task_id,
                artifact_id=item.get("id"),
                expected_artifact_content_hash=item.get("content_hash"),
            )
        except (
            KeyError,
            ModelingError,
            StrategyError,
            TypeError,
            ValueError,
            *_STRATEGY_V2_ARTIFACT_ERRORS,
        ) as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_report_bundle_v2_cross_candidate_search_invalid",
                "The latest pending decision.Cross Can not open messageartifact Document not adopted,registry,"
                "provenance or sample bound for review; whose true identity cannot be confirmed and the platform will not"
                "Back to old evidence.",
            ) from exc
        if _strategy_report_cross_search_matches(
            binding,
            sample=sample,
        ):
            return binding
    if total > _STRATEGY_REPORT_CROSS_SEARCH_REPLAY_LIMIT:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_cross_candidate_search_"
            "selection_window_exhausted",
            "Fully certified for update"
            f"{_STRATEGY_REPORT_CROSS_SEARCH_REPLAY_LIMIT} individualCross Can not open message"
            "artifact,But...registry still record earlier; platform cannot prove outside window"
            "Cannot initialise Evolution's mail component.SampleDesign Full consistency of search evidence, not created this time"
            "Reporting plan.",
        )
    return None

def _strategy_report_cross_search_matches(
    binding,
    *,
    sample,
) -> bool:
    try:
        validate_cross_candidate_search_report_compatibility(
            cross_candidate_search=binding,
            sample_design=sample,
        )
    except StrategyError:
        return False
    return True

def _strategy_report_latest_cross_rule_search_binding(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    sample,
):
    """Select the newest authenticated Cross rule search for this V2 sample."""

    records, total = _strategy_report_artifact_window(
        read_runtime,
        task_id=task_id,
        kind=CROSS_RULE_SEARCH_ARTIFACT_KIND,
        limit=_STRATEGY_REPORT_CROSS_SEARCH_REPLAY_LIMIT,
        unavailable_code=(
            "strategy_report_bundle_v2_cross_rule_search_registry_unavailable"
        ),
        invalid_code="strategy_report_bundle_v2_cross_rule_search_invalid",
        label="Cross rule search",
    )
    for item in records:
        try:
            binding = load_cross_rule_search_artifact(
                read_runtime,
                task_id=task_id,
                artifact_id=item.get("id"),
                expected_artifact_content_hash=item.get("content_hash"),
            )
        except (
            KeyError,
            ModelingError,
            StrategyError,
            TypeError,
            ValueError,
            *_STRATEGY_V2_ARTIFACT_ERRORS,
        ) as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_report_bundle_v2_cross_rule_search_invalid",
                "The latest pending decision.Cross Threshold rule searchartifact Document not adopted,"
                "registry,provenance or sample bound review; the platform does not retreat to old evidence.",
            ) from exc
        try:
            validate_cross_rule_search_report_compatibility(
                cross_rule_search=binding,
                sample_design=sample,
            )
        except StrategyError:
            continue
        return binding
    if total > _STRATEGY_REPORT_CROSS_SEARCH_REPLAY_LIMIT:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_cross_rule_search_"
            "selection_window_exhausted",
            "Fully certified for update"
            f"{_STRATEGY_REPORT_CROSS_SEARCH_REPLAY_LIMIT} individualCross Threshold"
            "Rule Searchartifact,But...registry Early records still exist; platform not available"
            "There is no evidence of compatibility outside the window and no reporting plan is created this time.",
        )
    return None

def _strategy_report_latest_impact_cube_binding(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    pool,
    sample_ref: Mapping[str, object],
):
    """Prefer the newest exact Pool + SampleDesign ImpactCube.

    The repository window is newest-first. Authenticate each candidate before
    inspecting its embedded Pool/SampleDesign identity. A valid unrelated cube
    can be skipped, while an unauthenticatable candidate fails closed because
    its raw provenance cannot safely prove that it was unrelated.
    """

    expected_pool_ref = {
        "artifact_id": pool.artifact_id,
        "expected_artifact_content_hash": pool.artifact_content_hash,
        "expected_pool_id": pool.pool["pool_id"],
        "expected_revision": pool.pool["revision"],
        "expected_revision_id": pool.pool["revision_id"],
        "expected_snapshot_hash": pool.pool["snapshot_hash"],
    }
    same_kind, total = _strategy_report_artifact_window(
        read_runtime,
        task_id=task_id,
        kind=IMPACT_CUBE_ARTIFACT_KIND,
        limit=_STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT,
        unavailable_code=(
            "strategy_report_bundle_v2_impact_cube_registry_unavailable"
        ),
        invalid_code="strategy_report_bundle_v2_impact_cube_invalid",
        label="ImpactCube",
    )
    for item in same_kind:
        provenance = item.get("provenance")
        try:
            binding = load_strategy_impact_cube_artifact(
                read_runtime,
                task_id=task_id,
                artifact_id=item.get("id"),
                expected_artifact_content_hash=item.get("content_hash"),
                expected_cube_id=(
                    provenance.get("cube_id")
                    if isinstance(provenance, Mapping)
                    else None
                ),
                expected_cube_content_hash=(
                    provenance.get("cube_content_hash")
                    if isinstance(provenance, Mapping)
                    else None
                ),
            )
            cube = binding.cube
            identity = cube["identity"]
            sources = cube["source_bindings"]
            pool_artifact = sources["pool_artifact"]
            sample = sources["sample_design_v2"]
            authenticated_pool_ref = {
                "artifact_id": pool_artifact["artifact_id"],
                "expected_artifact_content_hash": pool_artifact[
                    "artifact_content_hash"
                ],
                "expected_pool_id": identity["pool_id"],
                "expected_revision": identity["revision"],
                "expected_revision_id": identity["revision_id"],
                "expected_snapshot_hash": identity["snapshot_hash"],
            }
            authenticated_sample_ref = {
                "membership_artifact_id": sample[
                    "membership_artifact_id"
                ],
                "expected_membership_artifact_content_hash": sample[
                    "membership_artifact_content_hash"
                ],
                "bundle_artifact_id": sample["bundle_artifact_id"],
                "expected_bundle_artifact_content_hash": sample[
                    "bundle_artifact_content_hash"
                ],
                "expected_bundle_id": sample["bundle_id"],
                "expected_sample_design_id": sample["sample_design_id"],
                "expected_sample_design_content_hash": sample[
                    "sample_design_content_hash"
                ],
            }
        except (
            KeyError,
            StrategyError,
            TypeError,
            ValueError,
            *_STRATEGY_V2_ARTIFACT_ERRORS,
        ) as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_report_bundle_v2_impact_cube_invalid",
                "The latest pending decision.ImpactCube Candidatures not adopted,registry,"
                "provenance,producer-run oraudit Review; its truthPool/"
                "SampleDesign Identified. Platform will not go back to the old ones.ImpactCube "
                "orPoolImpact.",
            ) from exc
        if (
            authenticated_pool_ref == expected_pool_ref
            and authenticated_sample_ref == dict(sample_ref)
        ):
            return binding
    if total > _STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_impact_cube_"
            "selection_window_exhausted",
            "Fully certified for update"
            f"{_STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT} individualImpactCube artifact,"
            "But...registry Still earlier records; platform cannot prove that there is no current outside window"
            "Pool/SampleDesign It's exactly the same.ImpactCube,No reporting plan was created this time.",
        )
    return None

def _strategy_report_latest_pool_stability_binding(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    impact_cube_ref: Mapping[str, object],
):
    """Select the newest authenticated stability for the exact report cube."""

    records, total = _strategy_report_artifact_window(
        read_runtime,
        task_id=task_id,
        kind=POOL_STABILITY_ARTIFACT_KIND,
        limit=_STRATEGY_REPORT_POOL_STABILITY_REPLAY_LIMIT,
        unavailable_code=(
            "strategy_report_bundle_v2_pool_stability_registry_unavailable"
        ),
        invalid_code="strategy_report_bundle_v2_pool_stability_invalid",
        label="PoolStability",
    )
    for item in records:
        provenance = item.get("provenance")
        try:
            binding = load_strategy_pool_stability_artifact(
                read_runtime,
                task_id=task_id,
                artifact_id=item.get("id"),
                expected_artifact_content_hash=item.get("content_hash"),
                expected_stability_id=(
                    provenance.get("stability_id")
                    if isinstance(provenance, Mapping)
                    else None
                ),
                expected_stability_content_hash=(
                    provenance.get("stability_content_hash")
                    if isinstance(provenance, Mapping)
                    else None
                ),
            )
            source_ref = binding.stability["source_bindings"]["impact_cube"]
        except (
            KeyError,
            StrategyError,
            TypeError,
            ValueError,
            *_STRATEGY_V2_ARTIFACT_ERRORS,
        ) as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_report_bundle_v2_pool_stability_invalid",
                "The latest pending decision.PoolStability artifact Document not adopted,registry,"
                "provenance,producer-run,Oneaudit orembedded "
                "ImpactCube Review; the true source cannot be confirmed and the platform will not retreat to the old"
                "- Stability evidence.",
            ) from exc
        if source_ref == dict(impact_cube_ref):
            return binding
    if total > _STRATEGY_REPORT_POOL_STABILITY_REPLAY_LIMIT:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_pool_stability_"
            "selection_window_exhausted",
            "Fully certified for update"
            f"{_STRATEGY_REPORT_POOL_STABILITY_REPLAY_LIMIT} individual"
            "PoolStability artifact,But...registry Early records still exist; platform is not available"
            "Proves that there is no current outside the windowexact ImpactCube The evidence of stability is consistent."
            "No reporting plan was created this time.",
        )
    return None

def _strategy_report_latest_pool_impact_binding(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    pool,
):
    same_kind, total = _strategy_report_artifact_window(
        read_runtime,
        task_id=task_id,
        kind=POOL_IMPACT_ARTIFACT_KIND,
        limit=_STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT,
        unavailable_code=(
            "strategy_report_bundle_v2_pool_impact_registry_unavailable"
        ),
        invalid_code="strategy_report_bundle_v2_pool_impact_invalid",
        label="PoolImpact",
    )
    for item in same_kind:
        provenance = item.get("provenance")
        try:
            binding = load_historical_strategy_pool_impact_artifact(
                read_runtime,
                task_id=task_id,
                artifact_id=item.get("id"),
                expected_artifact_content_hash=item.get("content_hash"),
                expected_assessment_id=(
                    provenance.get("assessment_id")
                    if isinstance(provenance, Mapping)
                    else None
                ),
                expected_assessment_content_hash=(
                    provenance.get("assessment_content_hash")
                    if isinstance(provenance, Mapping)
                    else None
                ),
            )
        except (
            StrategyError,
            TypeError,
            ValueError,
            *_STRATEGY_V2_ARTIFACT_ERRORS,
        ) as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_report_bundle_v2_pool_impact_invalid",
                "The latest pending decision.PoolImpact Failure to pass historical security documents,registry,"
                "provenance,Pool Or a sample bound for review; whose true identity cannot be confirmed,"
                "The platform will not retreat to the old evidence of impact.",
            ) from exc
        if (
            binding.stage != "development_backtest"
            or binding.pool.artifact_id != pool.artifact_id
            or binding.pool.artifact_content_hash
            != pool.artifact_content_hash
            or binding.pool.pool != pool.pool
        ):
            continue
        return binding
    if total > _STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_pool_impact_"
            "selection_window_exhausted",
            "Checked for update"
            f"{_STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT} individualPoolImpact artifact,"
            "But...registry Still earlier documented; platform cannot prove that there is no current outside window"
            "Pool revision/snapshot Accuracydevelopment Evidence,"
            "No reporting plan was created this time.",
        )
    raise _StrategyV2EvidenceSetupError(
        "strategy_report_bundle_v2_pool_impact_required",
        "Current non-emptyStrategy Pool No, it's not the same.revision/snapshot It's...development "
        "PoolImpact;Please complete impact measurements alone.",
    )

def _strategy_report_optional_model_evidence(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    sample_ref: Mapping[str, object],
) -> tuple[object | None, dict[str, object] | None]:
    records, _total = _strategy_report_artifact_window(
        read_runtime,
        task_id=task_id,
        kind=MODEL_EVIDENCE_V2_ARTIFACT_KIND,
        limit=1,
        unavailable_code=(
            "strategy_report_bundle_v2_optional_evidence_registry_unavailable"
        ),
        invalid_code="strategy_report_bundle_v2_optional_evidence_invalid",
        label="ModelEvidence",
    )
    if not records:
        return None, None
    newest = records[0]
    provenance = newest.get("provenance")
    if not isinstance(provenance, Mapping):
        _raise_corrupt_report_optional("ModelEvidence")
    try:
        binding = load_strategy_model_evidence_v2_artifact(
            read_runtime,
            task_id=task_id,
            artifact_id=newest.get("id"),
            expected_artifact_content_hash=newest.get("content_hash"),
            expected_bundle_id=provenance.get("bundle_id"),
            expected_bundle_content_hash=provenance.get("bundle_content_hash"),
            sample_design_ref=provenance.get("sample_design_ref"),
        )
    except (
        ModelingError,
        StrategyError,
        TypeError,
        ValueError,
        *_STRATEGY_V2_ARTIFACT_ERRORS,
    ) as exc:
        _raise_corrupt_report_optional("ModelEvidence", cause=exc)
    reference = {
        "artifact_id": binding.artifact_id,
        "expected_artifact_content_hash": binding.artifact_content_hash,
        "expected_bundle_id": binding.bundle["bundle_id"],
        "expected_bundle_content_hash": binding.bundle["content_hash"],
    }
    if _strategy_report_sample_ref(binding.sample_design_binding) != dict(
        sample_ref
    ):
        return None, None
    return binding, reference

def _strategy_report_optional_training_evidence(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    sample_ref: Mapping[str, object],
) -> tuple[object | None, dict[str, object] | None]:
    records, _total = _strategy_report_artifact_window(
        read_runtime,
        task_id=task_id,
        kind=MODELING_TRAINING_EVIDENCE_ARTIFACT_KIND,
        limit=1,
        unavailable_code=(
            "strategy_report_bundle_v2_optional_evidence_registry_unavailable"
        ),
        invalid_code="strategy_report_bundle_v2_optional_evidence_invalid",
        label="training evidence",
    )
    if not records:
        return None, None
    newest = records[0]
    try:
        reference = _strategy_report_training_ref(
            read_runtime,
            task_id=task_id,
            record=newest,
        )
        binding = load_modeling_training_evidence_artifacts(
            read_runtime,
            task_id=task_id,
            **reference,
        )
        reference = build_training_evidence_ref(binding)
    except (
        ModelingError,
        StrategyError,
        TypeError,
        ValueError,
        *_STRATEGY_V2_ARTIFACT_ERRORS,
    ) as exc:
        _raise_corrupt_report_optional("training evidence", cause=exc)
    if reference["sample_design_ref"] != dict(sample_ref):
        return None, None
    return binding, reference

def _strategy_report_training_ref(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    record: Mapping,
) -> dict[str, object]:
    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValueError("training evidence provenance is invalid")
    sample_ref = _strategy_report_sample_ref_from_registry(
        read_runtime,
        task_id=task_id,
        membership_artifact_id=provenance.get(
            "sample_membership_artifact_id"
        ),
        bundle_artifact_id=provenance.get("sample_bundle_artifact_id"),
    )
    return {
        "sample_design_ref": sample_ref,
        "model_binary_artifact_id": provenance.get(
            "model_binary_artifact_id"
        ),
        "expected_model_binary_artifact_content_hash": provenance.get(
            "model_binary_artifact_content_hash"
        ),
        "evidence_artifact_id": record.get("id"),
        "expected_evidence_artifact_content_hash": record.get("content_hash"),
        "expected_experiment_id": provenance.get("experiment_id"),
        "expected_model_artifact_id": provenance.get("model_artifact_id"),
        "expected_evidence_id": provenance.get("evidence_id"),
        "expected_evidence_content_hash": provenance.get(
            "evidence_content_hash"
        ),
    }

def _strategy_report_sample_ref_from_registry(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    membership_artifact_id: object,
    bundle_artifact_id: object,
) -> dict[str, object]:
    membership = read_runtime.task_artifacts.get_for_task(
        task_id,
        membership_artifact_id,
    )
    bundle = read_runtime.task_artifacts.get_for_task(
        task_id,
        bundle_artifact_id,
    )
    if (
        not isinstance(membership, Mapping)
        or membership.get("kind")
        not in {
            SAMPLE_DESIGN_V2_MEMBERSHIP_ARTIFACT_KIND,
            SAMPLE_DESIGN_V2_NATIVE_MEMBERSHIP_ARTIFACT_KIND,
        }
        or not isinstance(bundle, Mapping)
        or bundle.get("kind") != SAMPLE_DESIGN_V2_BUNDLE_ARTIFACT_KIND
    ):
        raise ValueError("training evidence sample artifact pair is missing")
    provenance = bundle.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValueError("training evidence sample bundle provenance is invalid")
    return {
        "membership_artifact_id": membership.get("id"),
        "expected_membership_artifact_content_hash": membership.get(
            "content_hash"
        ),
        "bundle_artifact_id": bundle.get("id"),
        "expected_bundle_artifact_content_hash": bundle.get("content_hash"),
        "expected_bundle_id": provenance.get("bundle_id"),
        "expected_sample_design_id": provenance.get("sample_design_id"),
        "expected_sample_design_content_hash": provenance.get(
            "sample_design_content_hash"
        ),
    }

def _strategy_report_optional_score_evidence(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    sample_ref: Mapping[str, object],
    training_ref: Mapping[str, object] | None,
) -> tuple[object | None, dict[str, object] | None]:
    records, _total = _strategy_report_artifact_window(
        read_runtime,
        task_id=task_id,
        kind=MODEL_SCORE_EVIDENCE_ARTIFACT_KIND,
        limit=1,
        unavailable_code=(
            "strategy_report_bundle_v2_optional_evidence_registry_unavailable"
        ),
        invalid_code="strategy_report_bundle_v2_optional_evidence_invalid",
        label="score evidence",
    )
    if not records:
        return None, None
    newest = records[0]
    provenance = newest.get("provenance")
    if not isinstance(provenance, Mapping):
        _raise_corrupt_report_optional("score evidence")
    reference = {
        "evidence_artifact_id": newest.get("id"),
        "expected_evidence_artifact_content_hash": newest.get("content_hash"),
        "score_vector_artifact_id": provenance.get(
            "score_vector_artifact_id"
        ),
        "expected_score_vector_artifact_content_hash": provenance.get(
            "score_vector_artifact_content_hash"
        ),
    }
    try:
        binding = load_model_score_evidence_artifacts(
            read_runtime,
            task_id=task_id,
            **reference,
        )
    except (
        ModelingError,
        StrategyError,
        TypeError,
        ValueError,
        *_STRATEGY_V2_ARTIFACT_ERRORS,
    ) as exc:
        _raise_corrupt_report_optional("score evidence", cause=exc)
    bound_training_ref = build_training_evidence_ref(binding.training)
    if (
        bound_training_ref["sample_design_ref"] != dict(sample_ref)
        or (
            training_ref is not None
            and bound_training_ref != dict(training_ref)
        )
    ):
        return None, None
    return binding, {
        "evidence_artifact_id": binding.evidence_record["id"],
        "expected_evidence_artifact_content_hash": binding.evidence_record[
            "content_hash"
        ],
        "score_vector_artifact_id": binding.vector_record["id"],
        "expected_score_vector_artifact_content_hash": binding.vector_record[
            "content_hash"
        ],
    }

def _strategy_report_identity(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    candidate_pool,
) -> dict[str, str] | None:
    repository = StrategyRepository(runtime.settings.db_path)
    try:
        with repository.transaction() as conn:
            authenticated = (
                authenticate_strategy_report_identity_for_pool_on_connection(
                    repository,
                    conn,
                    task_id=task_id,
                    candidate_pool=candidate_pool,
                )
            )
    except Exception as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_strategy_identity_invalid",
            "CurrentStrategy Pool Identified strategies, non-negotiable books or life cycles"
            "No integrity review was adopted; no plan was created at this time.",
        ) from exc
    return (
        None
        if authenticated is None
        else dict(authenticated["identity"])
    )

def _strategy_pool_impact_column(
    inputs: Mapping,
    *,
    field: str,
    role: str,
    columns: tuple[str, ...],
    field_roles: Mapping,
) -> str | None:
    """Prefer an explicit validated column, else require a unique semantic role."""

    explicit = inputs.get(field)
    if explicit is not None:
        if not isinstance(explicit, str) or explicit not in columns:
            raise StrategySetupError(
                f"Impact Measurement Visible Fields{field} Not currently in activity data concentration."
            )
        return explicit
    matches = [
        column
        for column, assigned_role in field_roles.items()
        if assigned_role == role and column in columns
    ]
    if len(matches) > 1:
        raise StrategySetupError(
            f"DataWorkspace There\'s more than one.`{role}` Semantic fields:{','.join(sorted(matches))};"
            f"Please specify in your request{field},The platform will not be randomly chosen."
        )
    return matches[0] if matches else None

def _strategy_pool_entries(pool: Mapping) -> list[Mapping]:
    entries = pool.get("entries")
    if not isinstance(entries, Sequence) or isinstance(
        entries, str | bytes | bytearray
    ):
        raise StrategySetupError("CurrentStrategy Pool entries Invalid.")
    if any(not isinstance(entry, Mapping) for entry in entries):
        raise StrategySetupError("CurrentStrategy Pool entry Structure is invalid.")
    return list(entries)

def _strategy_pool_rule_id(pool: Mapping, identifier: str) -> str:
    matches = [
        entry
        for entry in _strategy_pool_entries(pool)
        if identifier in {str(entry.get("entry_id")), str(entry.get("rule_id"))}
    ]
    if len(matches) != 1:
        raise StrategySetupError(
            f"CurrentStrategy Pool There\'s no one match.rule_id/entry_id:{identifier}."
        )
    rule_id = matches[0].get("rule_id")
    if not isinstance(rule_id, str) or not rule_id:
        raise StrategySetupError("CurrentStrategy Pool entry Missing completenessrule_id.")
    return rule_id

def _strategy_pool_complete_rule_order(
    pool: Mapping,
    ordered_ids: object,
) -> list[str]:
    entries = _strategy_pool_entries(pool)
    if not isinstance(ordered_ids, Sequence) or isinstance(
        ordered_ids, str | bytes | bytearray
    ):
        raise StrategySetupError("Strategy Pool reorder It has to be complete.ID list.")
    resolved = [_strategy_pool_rule_id(pool, str(item)) for item in ordered_ids]
    current_rule_ids = [str(entry.get("rule_id") or "") for entry in entries]
    if (
        len(resolved) != len(current_rule_ids)
        or len(set(resolved)) != len(resolved)
        or set(resolved) != set(current_rule_ids)
    ):
        raise StrategySetupError(
            "Strategy Pool reorder Must provide all of the currentrule_id/entry_id complete, non-repeated ranking;"
            "MissingID It would not be interpreted as deleting."
        )
    return resolved

def _strategy_dataset_context(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    *,
    require_target: bool = True,
):
    backend, registry = _modeling_data_runtime(runtime.settings)
    return build_strategy_dataset_context(
        registry,
        backend,
        task.id,
        task.source_dir,
        target_col=getattr(task, "target_col", "") or None,
        require_target=require_target,
    )

def _strategy_pool_impact_dataset_context(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
):
    """Resolve target only from confirmed DataWorkspace semantics for impact."""

    _require_strategy_pool_impact_workspace(runtime, task)
    backend, registry = _modeling_data_runtime(runtime.settings)
    return build_strategy_dataset_context(
        registry,
        backend,
        task.id,
        task.source_dir,
        target_col=None,
        require_target=True,
    )

def _strategy_dataset_preview(runtime: DriverTurnRuntime, task: TaskRecord):
    backend, registry = _modeling_data_runtime(runtime.settings)
    return preview_strategy_dataset_context(
        registry,
        backend,
        task.id,
        task.source_dir,
        target_col=getattr(task, "target_col", "") or None,
    )

def _strategy_pool_impact_dataset_preview(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
):
    """Preview the active sample using only its confirmed workspace target."""

    _require_strategy_pool_impact_workspace(runtime, task)
    backend, registry = _modeling_data_runtime(runtime.settings)
    return preview_strategy_dataset_context(
        registry,
        backend,
        task.id,
        task.source_dir,
        target_col=None,
    )

def _strategy_impact_cube_dataset_preview(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
):
    """Expose compiler columns from the exact latest authenticated V2 sample."""

    read_runtime = _strategy_v2_read_runtime(runtime)
    try:
        artifacts = tuple(read_runtime.task_artifacts.list_for_task(task.id))
        sample = _latest_verified_strategy_sample_design_v2_binding(
            read_runtime,
            task_id=task.id,
            artifacts=artifacts,
        )
        target = sample.bundle["sample_design"]["target_selector"]["column"]
    except (
        KeyError,
        TypeError,
        _StrategyV2EvidenceSetupError,
        *_STRATEGY_V2_ARTIFACT_ERRORS,
    ) as exc:
        raise StrategySetupError(
            "ImpactCube Cannot initialise Evolution's mail component.StrategySampleDesign V2 (a) Authenticate the compilation field;"
            "Please re-establish the sample design."
        ) from exc
    if (
        not isinstance(target, str)
        or not target
        or target not in sample.source_binding.columns
    ):
        raise StrategySetupError(
            "LatestStrategySampleDesign V2 , and then click the target column."
        )
    return SimpleNamespace(
        dataset_id=sample.source_binding.dataset_id,
        columns=sample.source_binding.columns,
        target_col=target,
        identity={
            "kind": "strategy_sample_design_v2",
            "sample_design_ref": _strategy_report_sample_ref(sample),
            "dataset_id": sample.source_binding.dataset_id,
            "dataset_content_hash": sample.source_binding.dataset_content_hash,
        },
    )

def _strategy_dataset_binding_matches(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    *,
    preview,
    context,
    use_confirmed_workspace_target: bool = False,
    use_sample_design_workspace: bool = False,
) -> bool:
    """Verify the registered snapshot still represents the compiled preview."""

    if (
        tuple(context.columns) != tuple(preview.columns)
        or context.target_col != preview.target_col
    ):
        return False
    try:
        if use_sample_design_workspace:
            refreshed = _strategy_sample_design_dataset_preview(runtime, task)
        elif use_confirmed_workspace_target:
            refreshed = _strategy_pool_impact_dataset_preview(runtime, task)
        else:
            refreshed = _strategy_dataset_preview(runtime, task)
    except StrategySetupError:
        return False
    if (
        refreshed.dataset_id != context.dataset_id
        or tuple(refreshed.columns) != tuple(context.columns)
        or refreshed.target_col != context.target_col
    ):
        return False

    identity = preview.identity if isinstance(preview.identity, dict) else {}
    refreshed_identity = (
        refreshed.identity if isinstance(refreshed.identity, dict) else {}
    )
    context_fields = {
        "workspace_revision": getattr(context, "workspace_revision", None),
        "analysis_generation": getattr(context, "analysis_generation", None),
        "semantic_mapping_hash": getattr(context, "semantic_mapping_hash", None),
    }
    for field, context_value in context_fields.items():
        if field in identity and (
            identity[field] != refreshed_identity.get(field)
            or identity[field] != context_value
        ):
            return False
    if identity.get("kind") == "registered":
        return (
            identity.get("dataset_id") == refreshed_identity.get("dataset_id")
            and identity.get("content_hash") == refreshed_identity.get("content_hash")
            and identity.get("content_hash")
            == getattr(context, "dataset_content_hash", None)
        )
    if identity.get("kind") != "source":
        return False
    source_path = identity.get("source_path")
    expected_hash = identity.get("sha256")
    if not source_path or not expected_hash:
        return False
    try:
        # CSV/XLSX source registration may normalize bytes into Parquet.  The
        # confirmation binds the original source here; the registered Parquet
        # hash is bound separately in the plan/tool inputs.
        return sha256_file(Path(str(source_path))) == str(expected_hash)
    except OSError:
        return False

def _strategy_target_nan_stats(runtime: DriverTurnRuntime, context) -> tuple[int, int]:
    backend, registry = _modeling_data_runtime(runtime.settings)
    target_col = str(context.target_col or "").strip()
    if not target_col:
        raise StrategySetupError("The current strategy requires a clear dual objective line.")
    path = registry.resolve_path(context.dataset_id)
    try:
        frame = backend.read_frame(path, columns=[target_col])
        mask = nan_label_mask(frame, target_col)
    except Exception as exc:
        raise StrategySetupError(
            f"Target column`{target_col}` Only 0 must be included/1 and visiblely processed empty labels."
        ) from exc
    return int(len(frame)), int(mask.sum())

def _strategy_nan_label_clarification_response(
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    *,
    draft: CompiledStrategyRequestDraft,
    context,
    n_total: int,
    n_nan: int,
) -> dict:
    is_pool_impact = (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow in _STRATEGY_POOL_MEASUREMENT_WORKFLOWS
    )
    is_sample_design = (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow
        in {"strategy_sample_design", "strategy_sample_design_v2"}
    )
    refreshed = (
        _strategy_pool_impact_dataset_preview(runtime, task)
        if is_pool_impact
        else (
            _strategy_sample_design_dataset_preview(runtime, task)
            if is_sample_design
            else _strategy_dataset_preview(runtime, task)
        )
    )
    state = {
        "draft": draft.to_dict(),
        "dataset_id": context.dataset_id,
        "dataset_identity": dict(refreshed.identity),
        "target_col": context.target_col,
        "n_total": int(n_total),
        "n_nan": int(n_nan),
    }
    if is_pool_impact:
        try:
            _pool, pool_binding = _strategy_pool_impact_pool_binding(
                runtime,
                task,
                str(draft.workflow_inputs.get("strategy_type") or ""),
            )
        except StrategySetupError as exc:
            return _strategy_request_clarification_response(
                repo,
                task,
                code="strategy_pool_impact_binding_required",
                message=str(exc),
            )
        state["pool_binding"] = pool_binding
    return _append_strategy_nan_label_clarification(repo, task, state)

def _strategy_request_allowed_columns(preview) -> tuple[str, ...]:
    if preview is None:
        return ()
    # The observed target is evidence, never a deployable strategy feature or
    # an input to an LLM-authored profit contract.
    return tuple(column for column in preview.columns if column != preview.target_col)

def _strategy_request_requires_dataset(
    draft: CompiledStrategyRequestDraft,
) -> bool:
    if isinstance(draft, StandardWorkflowRequestDraft):
        migrated = migrated_workflow_requirements(
            draft.workflow,
            draft.workflow_inputs,
        )
        if migrated is not None:
            return migrated[0]
        if draft.workflow in {
            *_STRATEGY_POOL_WORKFLOWS,
            "strategy_project_context",
            "strategy_model_evidence_v2",
            "strategy_report_bundle_v2",
            "strategy_impact_cube",
            "strategy_pool_stability",
            "strategy_pool_apply",
            "strategy_pool_materialize",
            "strategy_pool_validation",
            "automatic_tree_leaf_materialization",
            "interactive_tree_split_search",
            "interactive_tree_auto_continuation",
            "interactive_tree_revision",
            "cross_matrix_cell_selection",
            "voting_candidate_search",
            "voting_candidate_build_from_search",
            "voting_candidate_build",
            "cross_matrix_candidate_search",
            "cross_matrix_candidate_build_from_search",
            "cross_rule_search",
            "cross_rule_candidate_build_from_search",
        }:
            return False
        return True
    return not (draft.strategy_spec is None and draft.operation == "report")

def _strategy_request_requires_target(
    draft: CompiledStrategyRequestDraft,
) -> bool:
    if isinstance(draft, StandardWorkflowRequestDraft):
        migrated = migrated_workflow_requirements(
            draft.workflow,
            draft.workflow_inputs,
        )
        if migrated is not None:
            return migrated[1]
        if draft.workflow == "strategy_project_context":
            return False
        return (
            draft.workflow
            in {
                "strategy_sample_design",
                "strategy_sample_design_v2",
                "automatic_tree_candidate_build",
                "cross_matrix_analysis",
                "strategy_pool_impact",
            }
        )
    if draft.operation in {"apply", "report", "monitor"}:
        return False
    if draft.operation == "develop" and draft.strategy_spec is not None:
        return False
    return True

def _strategy_request_requires_complete_labels(
    draft: CompiledStrategyRequestDraft,
) -> bool:
    """Whether execution would otherwise exclude missing supervision rows."""

    if isinstance(draft, StandardWorkflowRequestDraft):
        migrated = migrated_workflow_requirements(
            draft.workflow,
            draft.workflow_inputs,
        )
        if migrated is not None:
            return migrated[2]
        if draft.workflow == "strategy_project_context":
            return False
        return (
            draft.workflow
            in {
                "strategy_sample_design",
                "strategy_sample_design_v2",
                "automatic_tree_candidate_build",
                "cross_matrix_analysis",
                "strategy_pool_impact",
            }
        )
    if draft.operation in {"apply", "report", "monitor"}:
        return False
    if draft.operation == "develop" and draft.strategy_spec is not None:
        return False
    return True

def _strategy_slots_with_drop_nan(slots: dict, confirmed: bool) -> dict:
    if not confirmed:
        return slots
    return {**slots, "drop_nan_labels": True}

def _strategy_contract_from_draft(draft: StrategyRequestDraft) -> StrategyTaskInput:
    profit = None
    if draft.profit is not None:
        profit = StrategyProfitInput(**dict(draft.profit))
    return StrategyTaskInput(
        strategy_type=draft.strategy_type,
        objective=draft.objective or "",
        max_bad_rate=draft.max_bad_rate,
        min_approval_rate=draft.min_approval_rate,
        baseline_strategy_id=draft.baseline_strategy_id,
        profit=profit,
    )

def _strategy_request_success_criteria(
    draft: StrategyRequestDraft,
) -> list[dict] | None:
    if draft.strategy_type not in {"approval", "reject"}:
        return None
    criteria: list[dict] = []
    if draft.max_bad_rate is not None:
        criteria.append({"metric": "approved_bad_rate", "max": draft.max_bad_rate})
    if draft.min_approval_rate is not None:
        criteria.append({"metric": "approval_rate", "min": draft.min_approval_rate})
    return criteria or None

def _strategy_request_clarification_response(
    repo: TaskRepository,
    task: TaskRecord,
    *,
    code: str,
    message: str,
    fields: tuple[str, ...] | list[str] = (),
    ingest_notices: list[dict] | None = None,
) -> dict:
    normalized_fields = list(dict.fromkeys(str(field) for field in fields))
    normalized_notices = [
        dict(notice)
        for notice in (ingest_notices or [])
        if isinstance(notice, dict)
    ]
    metadata = {
        "intent": "strategy_request",
        "kind": "clarification",
        "code": code,
    }
    if normalized_fields:
        metadata["fields"] = normalized_fields
    if normalized_notices:
        metadata["ingest_notices"] = normalized_notices
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=f"{message}{_ingest_notice_text(normalized_notices)}",
        metadata=metadata,
    )
    response = {
        "task_id": task.id,
        "status": "clarification_required",
        "code": code,
        "messages": repo.list_agent_messages(task.id),
    }
    if normalized_fields:
        response["fields"] = normalized_fields
    if normalized_notices:
        response["ingest_notices"] = normalized_notices
    return response
