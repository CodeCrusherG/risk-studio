"""labeling driver-turn handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
from collections.abc import Mapping
import hmac
import sqlite3
from marvis.agent.plan_driver import CONFIRMATION_SOURCE_HUMAN, DriverError, is_confirm
from marvis.data.errors import DatasetContentDriftError
from marvis.repositories.tasks import TaskRepository
from marvis.domain import TASK_TYPE_DATA_JOIN, TaskRecord
from marvis.packs.labeling.contracts import LabelingContractError, LabelingRequest, build_labeling_proposal
from marvis.repositories.plans import PlanRepository
from marvis.repositories.data_workspace import DataWorkspaceRepository

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import DriverTurnRuntime
    from . import _active_plan
    from . import _driver
    from . import _modeling_data_runtime
    from . import _semantic_exact_gate_authorization
    from . import join_turn_response

def _handle_structured_labeling_request_turn(
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    *,
    user_text: str | None,
    labeling_request: Mapping[str, object],
) -> dict:
    """Build a read-only label proposal; never create or execute a plan."""

    if task.task_type != TASK_TYPE_DATA_JOIN:
        raise DriverError("labeling_request Only for usedata_join Type of task.")
    if _active_plan(runtime.plan_repo, task.id) is not None:
        raise DriverError("Current data processing tasks are planned and labels cannot be modified to build calibres.")
    try:
        contract = LabelingRequest(**dict(labeling_request))
    except (LabelingContractError, TypeError) as exc:
        return _labeling_clarification_response(
            repo,
            task,
            code="labeling_request_invalid",
            content=f"Label construction caliber invalid:{exc}",
        )

    repo.add_agent_message(
        task.id,
        role="user",
        stage="chat",
        content=str(user_text or "").strip(),
        metadata={
            "intent": "labeling_setup",
            "request_source": "manual_ui",
            "proposal_hash": contract.contract_hash,
            "fields": sorted(labeling_request),
        },
    )
    backend, registry = _modeling_data_runtime(runtime.settings)
    workspace = DataWorkspaceRepository(runtime.settings.db_path).get_or_default(
        task.id
    )
    try:
        proposal = build_labeling_proposal(
            registry,
            backend,
            workspace,
            task_id=task.id,
            request=contract,
        )
    except (LabelingContractError, DatasetContentDriftError, KeyError) as exc:
        return _labeling_clarification_response(
            repo,
            task,
            code="labeling_request_invalid",
            content=f"The label construction proposal was not verified by source data:{exc}",
            proposal_hash=contract.contract_hash,
        )

    maturity = proposal.maturity
    maturity_text = (
        "Allcohort mature"
        if maturity["all_matured"]
        else (
            f"{len(maturity['immature_cohorts'])} individualcohort Not yet mature; after confirmation of these loans"
            "♪ Keep asNaN Labels and remain controlled by empty downstream tab doors"
        )
    )
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=(
            "The label construction proposal has been generated.**No plan created, no data written**.\n"
            f"- Data set:`{proposal.source_dataset_name}`({proposal.rows_at_as_of} Line integration"
            f"as-of,{proposal.rows_excluded_after_as_of} Lines are excluded by the cut-off date)\n"
            f"- Other Organiser`{contract.as_of_date}`\n"
            f"- Observation period/ Performance period/ Set a time point:MOB {contract.observation_window} / "
            f"{contract.performance_window} / {contract.at_mob}\n"
            f"- Settling rules:`{proposal.rule_summary}` → `{contract.target_col}`\n"
            f"- Mature:{maturity_text}\n"
            "Please authorize continuation only when both the above calibre and maturity are correct (which can be directly stated as to your approval)"
            "The current complete proposal. When any field is modified, re-submit the full structured calibre; the platform will not"
            "guess or spell fields from the response."
        ),
        metadata={
            "intent": "labeling_setup",
            "kind": "labeling_preplan_confirmation",
            "labeling_proposal": proposal.to_gate_state(),
        },
    )
    return join_turn_response(repo, task.id)

def _maybe_handle_labeling_preplan_confirmation_turn(
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    *,
    user_text: str | None,
    confirmation_source: str,
) -> dict | None:
    """Require one independently reviewed human turn before a label plan exists."""

    if task.task_type != TASK_TYPE_DATA_JOIN:
        return None
    if _active_plan(runtime.plan_repo, task.id) is not None:
        return None
    proposal_state = _latest_open_labeling_proposal(
        repo.list_agent_messages(task.id)
    )
    if proposal_state is None:
        return None

    text = str(user_text or "").strip()
    proposal_hash = str(proposal_state.get("proposal_hash") or "")
    semantic_authorization = None
    deterministically_confirmed = (
        confirmation_source == CONFIRMATION_SOURCE_HUMAN and is_confirm(text)
    )
    if (
        not deterministically_confirmed
        and confirmation_source == CONFIRMATION_SOURCE_HUMAN
        and runtime.require_semantic_text_authorization
    ):
        semantic_authorization = _semantic_exact_gate_authorization(
            runtime,
            text,
            gate_context=(
                "The label construction scheme creates authorization: users have seen current full label calibre, maturity processing and"
                "(a) The content of the proposal;confirm Only means that the user is clearly, promptly and unconditionally authorized to comply with that integrity"
                "The proposal creates a plan that does not allow any changes from the normal text."
            ),
            proposed_params={"proposal_hash": proposal_hash},
        )
    if not deterministically_confirmed and semantic_authorization is None:
        repo.add_agent_message(
            task.id,
            role="user",
            stage="chat",
            content=text,
            metadata={
                "intent": "labeling_preplan_confirmation",
                "confirmation_source": confirmation_source,
                "proposal_hash": proposal_hash,
            },
        )
        return _labeling_clarification_response(
            repo,
            task,
            code="labeling_human_confirmation_required",
            content=(
                "The label construction defines the modelling objective and must be manually authorized to complete the current proposal without ambiguity."
                "You can just say you're in favour of the current scheme; no questions, no terms, no requests or modifications."
                "Release. If you need to change, re-submit the full structured calibre."
            ),
            proposal_hash=proposal_hash,
        )

    try:
        request_payload = proposal_state.get("request")
        if not isinstance(request_payload, dict):
            raise LabelingContractError("persisted proposal request is unavailable")
        contract = LabelingRequest(**request_payload)
        if not hmac.compare_digest(contract.contract_hash, proposal_hash):
            raise LabelingContractError("persisted proposal hash is inconsistent")
        backend, registry = _modeling_data_runtime(runtime.settings)
        workspace = DataWorkspaceRepository(
            runtime.settings.db_path
        ).get_or_default(task.id)
        proposal = build_labeling_proposal(
            registry,
            backend,
            workspace,
            task_id=task.id,
            request=contract,
        )
    except (LabelingContractError, DatasetContentDriftError, KeyError) as exc:
        return _labeling_clarification_response(
            repo,
            task,
            code="labeling_proposal_stale",
            content=(
                "Source data or data bound by the label construction proposalDataWorkspace Changed, original confirmation denied;"
                f"Please update and resubmit the full calibre.{exc}"
            ),
            proposal_hash=proposal_hash,
            resolution="stale",
        )

    def persist_confirmation_and_overview(
        conn: sqlite3.Connection,
        turn,
    ) -> None:
        repo.add_agent_message_on_connection(
            conn,
            task.id,
            role="user",
            stage="chat",
            content=text,
            metadata={
                "intent": "labeling_preplan_confirmation",
                "confirmation_source": CONFIRMATION_SOURCE_HUMAN,
                "proposal_hash": proposal_hash,
                "semantic_authorized": semantic_authorization is not None,
            },
        )
        if semantic_authorization is not None:
            repo.add_agent_message_on_connection(
                conn,
                task.id,
                role="assistant",
                stage="chat",
                content="The current full-scale tag calibre proposal has been confirmed through an independent semantic review.",
                metadata={
                    "intent": "labeling_semantic_authorization",
                    "display_in_timeline": False,
                    "proposal_hash": proposal_hash,
                    "semantic_authorization": semantic_authorization,
                },
            )
        repo.add_agent_message_on_connection(
            conn,
            task.id,
            role="assistant",
            stage="chat",
            content="Manual tag calibre confirmations have been recorded and a reviewable implementation plan is being generated.",
            metadata={
                "intent": "labeling_preplan_confirmation",
                "proposal_hash": proposal_hash,
                "labeling_proposal_resolution": "confirmed",
            },
        )
        for message in turn.messages:
            repo.add_agent_message_on_connection(
                conn,
                task.id,
                role="assistant",
                stage="chat",
                content=message.content,
                metadata=dict(message.metadata),
            )

    _driver(runtime).start(
        task_id=task.id,
        template_id="label_construction",
        slots=proposal.to_template_slots(
            confirm_immature_cohorts=bool(
                proposal.maturity["immature_cohorts"]
            ),
        ),
        tier=runtime.tier,
        _persist_start_turn=persist_confirmation_and_overview,
    )
    return join_turn_response(repo, task.id)

def _latest_open_labeling_proposal(
    conversation: list[dict],
) -> dict[str, object] | None:
    for message in reversed(conversation):
        metadata = message.get("metadata") or {}
        if metadata.get("labeling_proposal_resolution"):
            return None
        proposal = metadata.get("labeling_proposal")
        if (
            metadata.get("kind") == "labeling_preplan_confirmation"
            and isinstance(proposal, dict)
        ):
            return proposal
    return None

def is_labeling_deterministic_turn(
    repo: TaskRepository,
    plan_repo: PlanRepository,
    task: TaskRecord,
    user_text: str | None,
) -> bool:
    """Bypass LLM only for exact deterministic label-flow confirmations."""

    if task.task_type != TASK_TYPE_DATA_JOIN:
        return False
    if _latest_open_labeling_proposal(repo.list_agent_messages(task.id)) is not None:
        return is_confirm(str(user_text or ""))
    # Once the plan exists, ordinary Agent text must go through the same
    # semantic route/review as every other live plan gate.  Browser controls
    # remain deterministic through their typed, snapshot-bound ``ui_action``.
    return False

def _labeling_clarification_response(
    repo: TaskRepository,
    task: TaskRecord,
    *,
    code: str,
    content: str,
    proposal_hash: str | None = None,
    resolution: str | None = None,
) -> dict:
    metadata: dict[str, object] = {
        "intent": "labeling_setup",
        "kind": "clarification",
        "code": code,
    }
    if proposal_hash:
        metadata["proposal_hash"] = proposal_hash
    if resolution:
        metadata["labeling_proposal_resolution"] = resolution
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=content,
        metadata=metadata,
    )
    return {
        "task_id": task.id,
        "status": "clarification_required",
        "messages": repo.list_agent_messages(task.id),
    }
