from datetime import UTC, datetime, timedelta
import json
import logging
from pathlib import Path
import uuid

from marvis.db_schema import connect
from marvis.domain import (
    TASK_STATUS_REASON_SERVER_RESTART,
    TaskStatus,
)
from marvis.orchestrator.contracts import PlanStatus, StepStatus
from marvis.orchestrator.errors import PlanNotFoundError
from marvis.orchestrator.plan_recovery import PlanStepRecovery
from marvis.pipeline import METRICS_STAGE_FAILURE_PREFIX
from marvis.repositories.tasks import _now
from marvis.state_machine import ConflictError


logger = logging.getLogger(__name__)

RECLAIM_SERVER_RESTART_MESSAGE = "reclaimed: server restart while running"
METRICS_RECLAIM_RESUME_MESSAGE = (
    METRICS_STAGE_FAILURE_PREFIX + "Service restart aborted,Could be re-tested from the indicator stage"
)


ORPHAN_RECLAIM_STATUSES = frozenset(
    {
        TaskStatus.RUNNING,
        TaskStatus.COMPUTING_METRICS,
    }
)

_WORKFLOW_NAMES = {
    "data_join": "Data processing",
    "feature_analysis": "Characteristic analysis",
    "modeling": "Model development",
    "strategy": "Policy analysis",
    "vintage": "Vintage Risk analysis",
    "portfolio": "Group analysis",
}


def last_completed_step(task_dir: Path) -> str | None:
    execution_dir = task_dir / "execution"
    outputs_dir = task_dir / "outputs"
    if (
        (outputs_dir / "validation.xlsx").exists()
        and (outputs_dir / "validation_report.docx").exists()
    ):
        return "artifacts"
    if (
        (execution_dir / "code_model_scores.csv").exists()
        and (execution_dir / "runtime_contract.json").exists()
        and (execution_dir / "model_meta.json").exists()
    ):
        return "notebook"
    if execution_dir.exists():
        return "scan"
    return None


def reclaim_stale_running_tasks(
    db_path: Path,
    *,
    tasks_dir: Path | None = None,
    stale_after_seconds: int = 0,
) -> int:
    cutoff = (
        datetime.now(UTC) - timedelta(seconds=stale_after_seconds)
    ).isoformat()
    orphan_placeholders = ",".join(["?"] * len(ORPHAN_RECLAIM_STATUSES))
    with connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        reclaimed_task_ids = _stale_task_ids(conn, orphan_placeholders, cutoff)
        metrics_resumable_task_ids = _metrics_resumable_task_ids(
            conn, cutoff, tasks_dir=tasks_dir
        )
        agent_task_ids = _interrupted_agent_task_ids(
            conn, orphan_placeholders, cutoff
        )
        conn.execute(
            f"""
            UPDATE tasks
               SET status = ?,
                   status_message = ?,
                   status_reason_code = ?,
                   updated_at = ?
             WHERE updated_at <= ?
               AND status IN ({orphan_placeholders})
            """,
            (
                TaskStatus.FAILED.value,
                RECLAIM_SERVER_RESTART_MESSAGE,
                TASK_STATUS_REASON_SERVER_RESTART,
                _now(),
                cutoff,
                *(status.value for status in ORPHAN_RECLAIM_STATUSES),
            ),
        )
        if metrics_resumable_task_ids:
            placeholders = ",".join(["?"] * len(metrics_resumable_task_ids))
            conn.execute(
                f"""
                UPDATE tasks
                   SET status_message = ?,
                       updated_at = ?
                 WHERE id IN ({placeholders})
                   AND status = ?
                """,
                (
                    METRICS_RECLAIM_RESUME_MESSAGE,
                    _now(),
                    *metrics_resumable_task_ids,
                    TaskStatus.FAILED.value,
                ),
            )
        (
            reclaimed_batch_parent_task_ids,
            reclaimed_batch_child_task_ids,
        ) = _reconcile_reclaimed_validation_batches(
            conn,
            reclaimed_task_ids,
            cutoff=cutoff,
        )
        _finalize_interrupted_agent_messages(conn, agent_task_ids)
        _add_agent_restart_notices(conn, agent_task_ids)
        _fail_interrupted_jobs(
            conn,
            task_ids=sorted(
                set(reclaimed_task_ids)
                | set(agent_task_ids)
                | set(reclaimed_batch_parent_task_ids)
                | set(reclaimed_batch_child_task_ids)
            ),
            cutoff=cutoff,
        )
        reclaimed_count = len(
            set(reclaimed_task_ids) | set(reclaimed_batch_parent_task_ids)
        )
        if reclaimed_count:
            logger.info(
                "startup recovery reclaimed %d stale running task(s) as failed",
                reclaimed_count,
            )
        return reclaimed_count


def _reconcile_reclaimed_validation_batches(
    conn,
    reclaimed_task_ids: list[str],
    *,
    cutoff: str,
) -> tuple[list[str], list[str]]:
    rows = conn.execute(
        """
        SELECT parent_task_id
          FROM validation_batches
         WHERE status = 'running'
        """,
    ).fetchall()
    reclaimed_set = set(reclaimed_task_ids)
    parent_task_ids: list[str] = []
    for row in rows:
        parent_task_id = str(row[0])
        if parent_task_id in reclaimed_set:
            parent_task_ids.append(parent_task_id)
            continue
        active_job = conn.execute(
            """
            SELECT status, created_at,
                   COALESCE(heartbeat_at, started_at, created_at) AS activity_at
              FROM jobs
             WHERE task_id = ?
               AND kind = 'validation_batch'
               AND status IN ('queued', 'running')
             LIMIT 1
            """,
            (parent_task_id,),
        ).fetchone()
        if active_job is None or (
            str(active_job["status"]) == "queued"
            and str(active_job["created_at"]) <= cutoff
        ) or (
            str(active_job["status"]) == "running"
            and str(active_job["activity_at"]) <= cutoff
        ):
            parent_task_ids.append(parent_task_id)
    if not parent_task_ids:
        return [], []

    now = _now()
    parent_placeholders = ",".join(["?"] * len(parent_task_ids))
    child_rows = conn.execute(
        f"""
        SELECT id, parent_task_id, child_task_id, model_name, stage
          FROM validation_batch_items
         WHERE parent_task_id IN ({parent_placeholders})
           AND status = 'running'
        """,
        parent_task_ids,
    ).fetchall()
    child_task_ids = [str(row["child_task_id"]) for row in child_rows]
    running_item_parent_ids = {
        str(row["parent_task_id"])
        for row in child_rows
    }
    for row in child_rows:
        conn.execute(
            """
            INSERT INTO agent_messages
            (id, task_id, role, stage, content, created_at, metadata_json)
            VALUES (?, ?, 'assistant', 'failure', ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                str(row["parent_task_id"]),
                (
                    f"Model {row['model_name']} Yes.{row['stage']}Phase interrupted due to server restart;"
                    "This is isolated and marked to fail,Retrying after Recoverable."
                ),
                now,
                json.dumps(
                    {
                        "batch_item_failed": True,
                        "item_id": str(row["id"]),
                        "child_task_id": str(row["child_task_id"]),
                        "model_name": str(row["model_name"]),
                        "failed_stage": str(row["stage"]),
                        "error_code": "ServerRestart",
                        "retryable": True,
                        "interrupted_by_restart": True,
                        "streaming": False,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            ),
        )
    for parent_task_id in parent_task_ids:
        if parent_task_id in running_item_parent_ids:
            continue
        conn.execute(
            """
            INSERT INTO agent_messages
            (id, task_id, role, stage, content, created_at, metadata_json)
            VALUES (?, ?, 'assistant', 'failure', ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                parent_task_id,
                "Batch interrupted before the server restarted before the backstage job started;Restored to retryable state.",
                now,
                json.dumps(
                    {
                        "batch_failed_to_start": True,
                        "error_code": "ServerRestart",
                        "retryable": True,
                        "interrupted_by_restart": True,
                        "streaming": False,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            ),
        )
    conn.execute(
        f"""
        UPDATE validation_batch_items
           SET status = 'failed',
               outcome = 'failed',
               error_code = 'ServerRestart',
               error_message = ?,
               finished_at = ?,
               updated_at = ?
         WHERE parent_task_id IN ({parent_placeholders})
           AND status = 'running'
        """,
        (RECLAIM_SERVER_RESTART_MESSAGE, now, now, *parent_task_ids),
    )
    conn.execute(
        f"""
        UPDATE validation_batches
           SET status = 'partial_failure',
               summary_path = '',
               error_message = ?,
               finished_at = ?,
               updated_at = ?
         WHERE parent_task_id IN ({parent_placeholders})
           AND status = 'running'
        """,
        (RECLAIM_SERVER_RESTART_MESSAGE, now, now, *parent_task_ids),
    )
    conn.execute(
        f"""
        UPDATE tasks
           SET status = ?,
               status_message = ?,
               status_reason_code = ?,
               updated_at = ?
         WHERE id IN ({parent_placeholders})
        """,
        (
            TaskStatus.FAILED.value,
            RECLAIM_SERVER_RESTART_MESSAGE,
            TASK_STATUS_REASON_SERVER_RESTART,
            now,
            *parent_task_ids,
        ),
    )
    return parent_task_ids, child_task_ids


def _stale_task_ids(conn, orphan_placeholders: str, cutoff: str) -> list[str]:
    rows = conn.execute(
        f"""
        SELECT id
          FROM tasks
         WHERE updated_at <= ?
           AND status IN ({orphan_placeholders})
        """,
        (cutoff, *(status.value for status in ORPHAN_RECLAIM_STATUSES)),
    ).fetchall()
    return [str(row[0]) for row in rows]


def _metrics_resumable_task_ids(
    conn,
    cutoff: str,
    *,
    tasks_dir: Path | None,
) -> list[str]:
    """Tasks reclaimed out of COMPUTING_METRICS whose on-disk execution
    artifacts already completed the notebook step. These should resume via
    the metrics-only retry path instead of a full notebook re-run."""
    if tasks_dir is None:
        return []
    rows = conn.execute(
        """
        SELECT id
          FROM tasks
         WHERE updated_at <= ?
           AND status = ?
        """,
        (cutoff, TaskStatus.COMPUTING_METRICS.value),
    ).fetchall()
    resumable = []
    for row in rows:
        task_id = str(row[0])
        if last_completed_step(tasks_dir / task_id) == "notebook":
            resumable.append(task_id)
    return resumable


def _interrupted_agent_task_ids(
    conn,
    orphan_placeholders: str,
    cutoff: str,
) -> list[str]:
    rows = conn.execute(
        f"""
        SELECT id
          FROM tasks
         WHERE run_mode = 'agent'
           AND status IN ({orphan_placeholders})
           AND updated_at <= ?
        UNION
        SELECT tasks.id
          FROM tasks
          JOIN jobs ON jobs.task_id = tasks.id
         WHERE tasks.run_mode = 'agent'
           AND jobs.status IN ('queued', 'running')
           AND tasks.updated_at <= ?
        """,
        (*(status.value for status in ORPHAN_RECLAIM_STATUSES), cutoff, cutoff),
    ).fetchall()
    return [str(row[0]) for row in rows]


def _fail_interrupted_jobs(conn, *, task_ids: list[str], cutoff: str) -> None:
    params = [_now()]
    if task_ids:
        placeholders = ",".join(["?"] * len(task_ids))
        scope = f"(task_id IN ({placeholders}) OR created_at <= ?)"
        params.extend(task_ids)
        params.append(cutoff)
    else:
        scope = "created_at <= ?"
        params.append(cutoff)
    conn.execute(
        f"""
        UPDATE jobs
           SET status = 'failed',
               error_name = 'ServerRestart',
               error_value = 'process exited while job was running',
               finished_at = ?
         WHERE status IN ('queued', 'running')
           AND {scope}
        """,
        params,
    )


def _finalize_interrupted_agent_messages(
    conn,
    task_ids: list[str],
) -> None:
    if not task_ids:
        return
    placeholders = ",".join(["?"] * len(task_ids))
    rows = conn.execute(
        f"""
        SELECT id, content, metadata_json
          FROM agent_messages
         WHERE task_id IN ({placeholders})
        """,
        task_ids,
    ).fetchall()
    for message_id, content, metadata_json in rows:
        metadata = _load_metadata(metadata_json)
        if metadata.get("streaming") is not True:
            continue
        metadata["streaming"] = False
        metadata["interrupted_by_restart"] = True
        if metadata.get("kind") == "tool_progress":
            metadata["status"] = "interrupted"
            next_content = _interrupted_tool_progress_content(str(content or ""))
        else:
            next_content = _interrupted_agent_content(str(content or ""))
        conn.execute(
            """
            UPDATE agent_messages
               SET content = ?,
                   metadata_json = ?
             WHERE id = ?
            """,
            (
                next_content,
                json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
                message_id,
            ),
        )


def _add_agent_restart_notices(
    conn,
    task_ids: list[str],
) -> None:
    for task_id in task_ids:
        existing = conn.execute(
            """
            SELECT 1
              FROM agent_messages
             WHERE task_id = ?
               AND metadata_json LIKE '%"interrupted_by_restart":true%'
             LIMIT 1
            """,
            (task_id,),
        ).fetchone()
        if existing is not None:
            continue
        now = _now()
        conn.execute(
            """
            INSERT INTO agent_messages
            (id, task_id, role, stage, content, created_at, metadata_json)
            VALUES (?, ?, 'assistant', 'failure', ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                task_id,
                "Server restart,Previous round Agent Implementation interrupted;Retained previously written Agent Dialogue and Platform products.You can keep asking questions.,or re-send it according to current status(Go on.).",
                now,
                json.dumps(
                    {"interrupted_by_restart": True, "streaming": False},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            ),
        )


def _interrupted_agent_content(content: str) -> str:
    if not content.strip():
        return "Server restart,Previous round Agent Output aborted.The results of the dialogue and validation previously written on have been retained,You can keep asking questions or re-transmit them.(Go on.)."
    return content.rstrip() + "\n\n(Server restart,Agent Output aborted here.Current written content is retained.)"


def _interrupted_tool_progress_content(content: str) -> str:
    if not content.strip():
        return "Model reference interrupted due to server restart,Last progress is held."
    return content.rstrip() + "\n\n(Server restart,Transfer has been interrupted;Last progress is held.)"


def _load_metadata(value: str | None) -> dict:
    try:
        payload = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


PLAN_RESTART_NOTICE_MARKER = '"plan_interrupted_by_restart":true'


def reclaim_running_plans(
    plan_repo,
    reviewer,
    hook_dispatcher,
    harness_state,
    task_repo,
) -> int:
    """Reclaim V2 plans left in RUNNING by a crash/restart (REL-4).

    Startup-only counterpart to ``PlanExecutor._recover_inflight_steps``: a V2
    driver turn runs synchronously with no job/lock (REL-1), so a crash mid-turn
    leaves ``plans.status='running'`` forever — the task itself never enters
    tasks.status=RUNNING, so ``reclaim_stale_running_tasks`` above never sees it,
    and the plan spins until the user happens to resume() it. This reuses the
    exact same step-run-ledger recovery semantics (``PlanStepRecovery``, shared
    with the executor) for the RUNNING/CHECKING steps, then fails the plan itself,
    drops a Chinese restart notice into the owning task's conversation, and
    releases any orphaned driver job for that task.
    """
    step_recovery = PlanStepRecovery(plan_repo, reviewer, hook_dispatcher, harness_state)
    reclaimed = 0
    for plan in plan_repo.list_plans_by_status(PlanStatus.RUNNING):
        try:
            _reclaim_one_running_plan(plan_repo, step_recovery, task_repo, plan)
        except (PlanNotFoundError, ConflictError):
            # Plan was concurrently resumed/finished between the scan and the
            # reclaim attempt (e.g. a request already in flight when the
            # process restarted mid-request); leave it to the in-flight caller.
            continue
        except Exception:
            logger.exception("failed to reclaim running plan %s", plan.id)
            continue
        reclaimed += 1
    if reclaimed:
        logger.info("startup recovery reconciled %d running plan(s)", reclaimed)
    return reclaimed


def _reclaim_one_running_plan(plan_repo, step_recovery, task_repo, plan) -> None:
    step_recovery.recover_inflight_steps(plan)
    statuses = {step.status for step in plan.steps}
    resumed_at_confirmation = (
        StepStatus.AWAITING_CONFIRM in statuses
        and not statuses.intersection(
            {StepStatus.RUNNING, StepStatus.CHECKING, StepStatus.FAILED}
        )
    )
    plan_repo.set_plan_status(
        plan.id,
        PlanStatus.AWAITING_CONFIRM if resumed_at_confirmation else PlanStatus.FAILED,
    )
    recovered_plan = plan_repo.load_plan(plan.id)
    failed_steps = [
        step for step in recovered_plan.steps if step.status == StepStatus.FAILED
    ]
    failed_step = failed_steps[0] if len(failed_steps) == 1 else None
    task = task_repo.get_task(plan.task_id)
    with connect(task_repo.db_path) as conn:
        _finalize_interrupted_agent_messages(conn, [plan.task_id])
    _fail_orphan_task_jobs(task_repo, plan.task_id)
    _add_plan_restart_notice(
        task_repo,
        plan.task_id,
        plan.id,
        resumed_at_confirmation=resumed_at_confirmation,
        run_mode=task.run_mode,
        workflow=task.task_type,
        failed_step=failed_step,
    )


def _fail_orphan_task_jobs(task_repo, task_id: str) -> None:
    """Release a driver job stuck queued/running for this task (the process
    that owned it died with the plan mid-RUNNING); frees idx_jobs_active_task
    so the task isn't wedged behind a 409 after the restart notice invites a
    retry."""
    with connect(task_repo.db_path) as conn:
        rows = conn.execute(
            """
            SELECT id
              FROM jobs
             WHERE task_id = ?
               AND status IN ('queued', 'running')
            """,
            (task_id,),
        ).fetchall()
        for row in rows:
            conn.execute(
                """
                UPDATE jobs
                   SET status = 'failed',
                       error_name = 'ServerRestart',
                       error_value = 'process exited while job was running',
                       finished_at = ?
                 WHERE id = ?
                   AND status IN ('queued', 'running')
                """,
                (_now(), row["id"]),
            )


def _add_plan_restart_notice(
    task_repo,
    task_id: str,
    plan_id: str,
    *,
    resumed_at_confirmation: bool = False,
    run_mode: str = "manual",
    workflow: str = "",
    failed_step=None,
) -> None:
    stage = "chat" if resumed_at_confirmation else "failure"
    if resumed_at_confirmation:
        content = "Service restarted,Progress in implementation and intermediate products retained;Plan resumes to current confirmed node,Wait till you confirm.."
    elif run_mode == "agent":
        step_title = str(getattr(failed_step, "title", "") or "Current")
        content = (
            f"Service restarted,The plan is suspended.({step_title})Steps;The intermediate product is preserved.."
            "Please respond.(Retry current steps),Agent It will continue from the failure.,No reruns completed.."
        )
    else:
        content = "Service restarted,Plans are suspended for the current steps;The intermediate product is preserved.,Could retry failure steps in intermediate stream."

    metadata = {
        "plan_interrupted_by_restart": True,
        "plan_resumed_at_confirmation": resumed_at_confirmation,
        "plan_id": plan_id,
        "streaming": False,
    }
    if not resumed_at_confirmation and failed_step is not None:
        diagnostic, failure_envelope = _restart_failure_payload(
            plan_id=plan_id,
            workflow=workflow,
            failed_step=failed_step,
        )
        metadata.update(
            {
                "error": True,
                "error_diagnostic": diagnostic,
                "failure_envelope": failure_envelope,
            }
        )
    with connect(task_repo.db_path) as conn:
        existing = conn.execute(
            """
            SELECT 1
              FROM agent_messages
             WHERE task_id = ?
               AND metadata_json LIKE ?
             LIMIT 1
            """,
            (task_id, f'%{PLAN_RESTART_NOTICE_MARKER}%"plan_id":"{plan_id}"%'),
        ).fetchone()
        if existing is not None:
            return
        conn.execute(
            """
            INSERT INTO agent_messages
            (id, task_id, role, stage, content, created_at, metadata_json)
            VALUES (?, ?, 'assistant', ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                task_id,
                stage,
                content,
                _now(),
                json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
            ),
        )


def _restart_failure_payload(*, plan_id: str, workflow: str, failed_step) -> tuple[dict, dict]:
    step_title = str(getattr(failed_step, "title", "") or "Current steps")
    step_id = str(getattr(failed_step, "id", "") or "")
    error = str(getattr(failed_step, "error", "") or "ServerRestart")
    workflow_name = _WORKFLOW_NAMES.get(workflow, "Workstream")
    summary = f"The service is down.({step_title})Steps,Completed steps and intermediate products retained."
    diagnostic = {
        "schema_version": "workflow_error.v1",
        "workflow": workflow,
        "code": "server_restart_interrupted",
        "phase": "execution",
        "title": f"{workflow_name}Implementation aborted",
        "summary": summary,
        "cause": "Risk Studio Service restarted during the implementation of this step;Source material not modified.",
        "location": step_title,
        "evidence": [
            {"label": "Planned", "value": plan_id},
            {"label": "Step of failure", "value": step_id},
        ],
        "actions": ["Reply(Retry current steps),Proceed from the failed step."],
        "agent_prompt": "Please respond.(Retry current steps),Agent Reuse completed steps and intermediates continued.",
        "recovery_actions": [
            {"label": "Retry current steps", "command": "Retry current steps"}
        ],
        "retryable": True,
        "auto_recoverable": True,
        "impact": "Reliance steps after failure have not been implemented.",
        "exception_type": "ServerRestart",
        "technical_detail": f"ServerRestart: {error}",
    }
    failure_envelope = {
        "schema_version": "failure.v1",
        "failed_step_id": step_id,
        "error_kind": "ServerRestart",
        "message": summary,
        "retryable": True,
        "editable_input_schema": {},
        "suggested_actions": ["retry"],
        "downstream_reset": "dependent_steps",
        "downstream_reset_steps": [],
    }
    return diagnostic, failure_envelope
