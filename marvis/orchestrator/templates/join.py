from __future__ import annotations

from marvis.orchestrator.contracts import PostCheck
from marvis.orchestrator.templates import (
    SlotSpec,
    StepTemplate,
    WorkflowTemplate,
)
from marvis.orchestrator.templates._shared import JOIN_EXECUTE_POST_CHECKS
from marvis.plugins.manifest import ToolRef


DATA_JOIN = WorkflowTemplate(
    # V2 data-join template (foundation module). The driver instantiates it BY ID
    # for task_type="data_join". The sample table is the anchor (rows preserved
    # 1:1); feature tables are left-joined. Forced-confirmation is honored at two
    # layers: (a) the engine — execute_join hard-blocks until every spec is
    # confirmed (JoinNotConfirmedError); (b) the plan — execute_join is the
    # needs_confirmation human gate (validator INV-3), so the executor pauses
    # BEFORE the data-mutating join and the driver shows propose_join's
    # match/fan-out/fingerprint diagnostics. confirm_join runs between them to mark
    # the engine specs confirmed (per-feature, with optional dedup strategy).
    id="data_join",
    title="Data join",
    goal_patterns=("Data Collapse", "Spell Data", "Scatter samples", "join data", "data join"),
    slots=(
        SlotSpec("anchor_id", True, "task_context", "Anchor (sample) dataset id — rows preserved 1:1"),
        SlotSpec("feature_ids", True, "task_context", "Feature dataset ids to left-join onto the anchor"),
        SlotSpec("dedup_strategies", False, "task_context", "Optional per-feature dedup strategy map (feature_id -> first|last)"),
    ),
    steps=(
        StepTemplate(
            title="Review join diagnostics",
            tool_ref=ToolRef("data_ops", "propose_join"),
            inputs_template={
                "anchor_id": "{slot:anchor_id}",
                "feature_ids": "{slot:feature_ids}",
                "key_overrides": {},
            },
            depends_on_titles=(),
            post_checks=(PostCheck("nonempty", {"field": "join_plan_id"}),),
            # spec §2/§10: propose_join is a decision point — in agent mode the executor may
            # adapt the remaining plan from the diagnostics (match/fan-out/fingerprint). The
            # execute_join INV-3 confirmation gate + engine JoinNotConfirmedError backstop keep
            # the 1:1 anchor invariant regardless of any replan.
            decision_point=True,
            phase="Data readiness",
        ),
        StepTemplate(
            title="Confirm join settings",
            tool_ref=ToolRef("data_ops", "confirm_join"),
            inputs_template={
                "join_plan_id": "$ref:Review join diagnostics.output.join_plan_id",
                "dedup_strategies": "{slot:dedup_strategies}",
            },
            depends_on_titles=("Review join diagnostics",),
            # needs_dedup is a valid state (a non-unique key still awaiting a strategy): let
            # the plan reach the C2 gate to surface it rather than hard-failing here.
            post_checks=(PostCheck("one_of", {"field": "status", "values": ["confirmed", "needs_dedup"]}),),
            phase="Data readiness",
        ),
        StepTemplate(
            title="Join tables",
            tool_ref=ToolRef("data_ops", "execute_join"),
            inputs_template={
                "join_plan_id": "$ref:Review join diagnostics.output.join_plan_id",
            },
            depends_on_titles=("Review join diagnostics", "Confirm join settings"),
            post_checks=JOIN_EXECUTE_POST_CHECKS,
            # Force confirmation of doors(INV-3):execute_join I have to.needs_confirmation.Executor pauses until the real left connection,
            # Driver display collage diagnosis(Hit rate/Quiz/Key fingerprint),Organisation;There's another engine level.JoinNotConfirmedError Bottom of the road.
            needs_confirmation=True,
            phase="Data readiness",
        ),
    ),
    default_autonomy=1,
    source="builtin",
)
