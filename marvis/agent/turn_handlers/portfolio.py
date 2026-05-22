"""portfolio driver-turn handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
from collections.abc import Mapping
from marvis.agent.plan_driver import CONFIRMATION_SOURCE_HUMAN, DriverError, is_confirm
from marvis.agent.portfolio_setup import PortfolioProposal, PortfolioSetupError, build_portfolio_proposal, build_states_gate_state, parse_states_reply, verify_portfolio_dataset_binding
from marvis.repositories.tasks import TaskRepository
from marvis.domain import TASK_TYPE_PORTFOLIO, TaskRecord
from marvis.orchestrator.contracts import PlanStatus
from marvis.repositories.plans import PlanRepository

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import DriverTurnRuntime
    from . import _TurnHandlerSpec
    from . import _active_plan
    from . import _identity_display_text
    from . import _ingest_notice_text
    from . import _modeling_data_runtime
    from . import _run_driver_turn
    from . import _semantic_exact_gate_authorization
    from . import append_workflow_error
    from . import join_turn_response

def run_portfolio_driver_turn(
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
        _PORTFOLIO_SPEC,
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

def _portfolio_success_criteria(task: TaskRecord) -> list[dict] | None:
    """S3: optional deterministic criterion mirroring _strategy_success_criteria.
    task's optional portfolio_el_max (getattr-based -- no schema migration backs
    it) becomes a total_el ceiling final_review can evaluate; absent -> no
    criterion injected (same graceful default as strategy/modeling)."""
    el_max = getattr(task, "portfolio_el_max", None)
    if el_max is None:
        return None
    return [{"metric": "total_el", "max": float(el_max)}]

def _latest_portfolio_states(conversation: list[dict]) -> dict | None:
    for message in reversed(conversation):
        if message.get("role") != "assistant":
            continue
        meta = message.get("metadata") or {}
        if "portfolio_states" in meta:
            return meta["portfolio_states"]
    return None

def _request_portfolio_setup(
    repo: TaskRepository,
    task: TaskRecord,
) -> dict:
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=(
            "Please specify the loan in the group calibre form before starting the portfolio analysisid,Quick moon, late barrel,"
            "Balance/EAD,Business group, loss pattern,LGD and predict the duration. Platforms do not use free text"
            "Conjecture these business syntaxes; if trend analysis is required, it must also be accompanied by fractional columns and experimentsID."
        ),
        metadata={
            "intent": "portfolio",
            "kind": "portfolio_setup_required",
            "required_fields": [
                "id_col",
                "snapshot_col",
                "bucket_col",
                "balance_col",
                "segment_col",
                "loss_state",
                "lgd",
                "horizon_months",
            ],
        },
    )
    return join_turn_response(repo, task.id)

def _begin_portfolio_setup(
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    request: Mapping[str, object],
) -> dict:
    backend, registry = _modeling_data_runtime(runtime.settings)
    proposal = build_portfolio_proposal(
        registry,
        backend,
        task.id,
        task.source_dir,
        id_col=str(request.get("id_col") or "") or None,
        snapshot_col=str(request.get("snapshot_col") or "") or None,
        bucket_col=str(request.get("bucket_col") or "") or None,
        balance_col=str(request.get("balance_col") or "") or None,
        segment_col=str(request.get("segment_col") or "") or None,
        loss_state=str(request.get("loss_state") or "") or None,
        lgd=request.get("lgd"),
        horizon_months=request.get("horizon_months"),
        score_col=str(request.get("score_col") or "") or None,
        experiment_id=str(request.get("experiment_id") or "") or None,
    )
    notices = registry.consume_ingest_notices(task.id)
    states_text = " → ".join(f"`{state}`" for state in proposal.proposed_states)
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=(
            f"Start group analysis:Performance table`{proposal.dataset_name}`,Loansid `{proposal.id_col}`,"
            f"Quick light.`{proposal.snapshot_col}`,Overdue barrels`{proposal.bucket_col}`,"
            f"Balance/EAD `{proposal.balance_col}`,Business cluster`{proposal.segment_col}`.\n"
            f"Loss pattern`{proposal.loss_state}`,LGD `{proposal.lgd:g}`,"
            f"Projected duration`{proposal.horizon_months}` Months.\n"
            f"I'm in the following order of the barrel of deterioration:{states_text}.\n"
            "**The semantic sequence of the barrel is inconvenient. You must confirm.**:If you are correct, you can state directly that you are in favor of the current"
            "order; reset all barrels in the order of good to bad (coma-separated)."
            f"{_ingest_notice_text(notices)}"
        ),
        metadata={
            "portfolio_states": build_states_gate_state(proposal),
            "kind": "gate",
            "intent": "portfolio",
            "ingest_notices": notices,
        },
    )
    return join_turn_response(repo, task.id)

def _run_portfolio_setup(
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    user_text: str | None,
    confirmation_source: str = CONFIRMATION_SOURCE_HUMAN,
) -> dict | tuple:
    conversation = repo.list_agent_messages(task.id)
    gate_state = _latest_portfolio_states(conversation)
    if gate_state is None:
        return _request_portfolio_setup(repo, task)

    text = str(user_text or "").strip()
    states = parse_states_reply(text, gate_state)
    semantic_authorization = None
    if (
        states is None
        and runtime.require_semantic_text_authorization
    ):
        proposed_states = [
            str(state) for state in gate_state.get("proposed_states") or []
        ]
        semantic_authorization = _semantic_exact_gate_authorization(
            runtime,
            text,
            gate_context=(
                "Group analysis of the sequence authorization for past-out barrels: users have seen the complete sequence of the barrels from good to bad;"
                "confirm Only express a clear, immediate and unconditional acceptance of the current full order."
                "The first one is the one that has to be submitted to the government.LLM No order may be guessed or rewritten."
            ),
            proposed_params={
                "dataset_content_hash": gate_state.get("dataset_content_hash"),
                "proposed_states": proposed_states,
            },
        )
        if semantic_authorization is not None:
            states = proposed_states
    if states is None:
        proposed = gate_state.get("proposed_states") or []
        states_text = " → ".join(f"`{state}`" for state in proposed)
        repo.add_agent_message(
            task.id,
            role="assistant",
            stage="chat",
            content=(
                "No barrel order confirmed. Default (good to bad):"
                f"{states_text}.You can specify the order of approval, or you can load all barrels by good to bad"
                "(Comma separation; questions, terms and rejections will not be released."
            ),
            metadata={"portfolio_states": gate_state, "kind": "gate"},
        )
        return join_turn_response(repo, task.id)

    _, registry = _modeling_data_runtime(runtime.settings)
    verify_portfolio_dataset_binding(
        registry,
        task_id=task.id,
        dataset_id=str(gate_state["dataset_id"]),
        expected_content_hash=str(gate_state["dataset_content_hash"]),
    )

    proposal = PortfolioProposal(
        dataset_id=gate_state["dataset_id"],
        dataset_content_hash=gate_state["dataset_content_hash"],
        dataset_name="",
        id_col=gate_state["id_col"],
        snapshot_col=gate_state["snapshot_col"],
        bucket_col=gate_state["bucket_col"],
        proposed_states=list(states),
        balance_col=gate_state.get("balance_col"),
        segment_col=gate_state.get("segment_col"),
        loss_state=gate_state.get("loss_state"),
        lgd=gate_state.get("lgd"),
        horizon_months=gate_state.get("horizon_months"),
        score_col=gate_state.get("score_col"),
        experiment_id=gate_state.get("experiment_id"),
    )
    post_start_messages = []
    if semantic_authorization is not None:
        post_start_messages.append(
            {
                "role": "assistant",
                "stage": "chat",
                "content": "The current full order of pasting barrels has been confirmed through an independent semantic review.",
                "metadata": {
                    "intent": "portfolio_semantic_authorization",
                    "display_in_timeline": False,
                    "dataset_content_hash": gate_state.get(
                        "dataset_content_hash"
                    ),
                    "proposed_states": list(states),
                    "semantic_authorization": semantic_authorization,
                },
            }
        )
    post_start_messages.append(
        {
            "role": "assistant",
            "stage": "chat",
            "content": (
                f"Order of confirmed barrels:{' → '.join(states)}.Start parallel analysis (flow)/Migration/Breakdown"
                + ("/Trends" if proposal.experiment_id else "")
                + "),This is followed by a summary confirmation."
            ),
            "metadata": {"intent": "portfolio"},
        }
    )
    return (
        proposal.template_id,
        proposal.template_slots(states),
        {"_post_start_messages": post_start_messages},
    )

_PORTFOLIO_SPEC = _TurnHandlerSpec(
    intent="portfolio",
    setup_error_types=(PortfolioSetupError,),
    error_label="Group analysis error",
    run_setup=_run_portfolio_setup,
    format_user_display=_identity_display_text,
    success_criteria=_portfolio_success_criteria,
)

def is_portfolio_deterministic_turn(
    repo: TaskRepository,
    plan_repo: PlanRepository,
    task: TaskRecord,
    user_text: str | None,
) -> bool:
    """Allow only exact human replies at an existing Portfolio gate.

    A typed setup already bypasses the LLM.  This companion predicate keeps
    the immediately following state-order and plan confirmations usable in
    agent mode without turning arbitrary Portfolio chat into a manual-mode
    escape hatch.
    """

    if task.task_type != TASK_TYPE_PORTFOLIO:
        return False
    conversation = repo.list_agent_messages(task.id)
    last_assistant = next(
        (
            message
            for message in reversed(conversation)
            if message.get("role") == "assistant"
        ),
        None,
    )
    if last_assistant is None:
        return False
    metadata = last_assistant.get("metadata") or {}
    state_gate = metadata.get("portfolio_states")
    if isinstance(state_gate, dict):
        return parse_states_reply(user_text, state_gate) is not None
    if metadata.get("kind") == "portfolio_setup_required":
        return is_confirm(str(user_text or ""))

    active = _active_plan(plan_repo, task.id)
    if active is None or metadata.get("kind") not in {"gate", "plan_overview"}:
        return False
    status = PlanStatus(getattr(active.status, "value", active.status))
    return status in {PlanStatus.VALIDATED, PlanStatus.AWAITING_CONFIRM} and is_confirm(
        str(user_text or "")
    )

def _handle_structured_portfolio_request_turn(
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    *,
    user_text: str | None,
    portfolio_request: Mapping[str, object],
) -> dict:
    """Start the human-owned portfolio setup contract without an LLM."""

    if task.task_type != TASK_TYPE_PORTFOLIO:
        raise DriverError("portfolio_request Only for useportfolio Type of task.")
    if _active_plan(runtime.plan_repo, task.id) is not None:
        raise DriverError("Current portfolio analysis missions are planned and cannot be modified.")
    repo.add_agent_message(
        task.id,
        role="user",
        stage="chat",
        content=str(user_text or "").strip(),
        metadata={
            "intent": "portfolio_setup",
            "request_source": "manual_ui",
            "fields": sorted(portfolio_request),
        },
    )
    try:
        return _begin_portfolio_setup(
            runtime,
            repo,
            task,
            portfolio_request,
        )
    except PortfolioSetupError as exc:
        return append_workflow_error(
            repo,
            task,
            _PORTFOLIO_SPEC,
            exc,
            setup_error=True,
        )
