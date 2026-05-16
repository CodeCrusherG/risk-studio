"""S3 Group Analysis Template(PORTFOLIO_ANALYSIS).

Seven steps: 1 traffic∥ 2 Migration heat∥ 3 Disaggregate Image∥ 4 Trends in stability (Yes)experiment_id I am not a citizen of the world.
5 The damage estimates (dependent on migratory heat),6 summary of the combination analysis (dependent on all the steps ahead,decision_point +
needs_confirmation,The doorworks are coming together.red_flags=Door.checklist),7 Generate group reports
(The government is not interested in the government.post nonempty report_path).

Step 1-4 I don't have to rely on each other.executor The word "ready" is natural parallel.experiment_id Use not to include defaults
TrendsPORTFOLIO_ANALYSIS_NO_TREND Variable (Stract semantics:planner from_template No, no, no, no.
So, bysetup Selecting a variable to achieve"Noneexperiment_id Get rid of the trend.").
"""

from __future__ import annotations

from marvis.orchestrator.contracts import PostCheck
from marvis.orchestrator.templates import (
    SlotSpec,
    StepTemplate,
    WorkflowTemplate,
)
from marvis.plugins.manifest import ToolRef

_GOAL_PATTERNS = ("Group analysis", "Cluster report", "Asset quality", "portfolio analysis")


def _base_slots() -> tuple[SlotSpec, ...]:
    return (
        SlotSpec("performance_dataset_id", True, "task_context", "Registered performance snapshot dataset id"),
        SlotSpec(
            "performance_dataset_content_hash",
            True,
            "task_context",
            "SHA-256 of the human-confirmed performance dataset bytes",
        ),
        SlotSpec("id_col", True, "task_context", "Loan id column"),
        SlotSpec("snapshot_col", True, "task_context", "Snapshot month column"),
        SlotSpec("bucket_col", True, "task_context", "Delinquency bucket column"),
        SlotSpec("states", True, "task_context", "Ordered bucket states (worst last), human-confirmed"),
        SlotSpec("balance_col", True, "task_context", "Monetary balance/EAD column"),
        SlotSpec("segment_col", True, "user", "Business segment column for the profile step"),
        SlotSpec("loss_state", True, "user", "Human-selected absorbing loss state"),
        SlotSpec("lgd", True, "user", "Explicit loss-given-default assumption in [0, 1]"),
        SlotSpec("horizon_months", True, "user", "Explicit positive expected-loss horizon in months"),
        SlotSpec("score_col", False, "user", "Score column for the trend step"),
        SlotSpec("experiment_id", False, "user", "Experiment id for the stability-trend step"),
    )


def _flow_step() -> StepTemplate:
    return StepTemplate(
        title="Flow analysis",
        tool_ref=ToolRef("analysis", "flow_rate"),
        inputs_template={
            "dataset_id": "{slot:performance_dataset_id}",
            "expected_content_hash": "{slot:performance_dataset_content_hash}",
            "id_col": "{slot:id_col}",
            "snapshot_col": "{slot:snapshot_col}",
            "bucket_col": "{slot:bucket_col}",
            "states": "{slot:states}",
            "balance_col": "{slot:balance_col}",
        },
        depends_on_titles=(),
        post_checks=(PostCheck("nonempty", {"field": "months"}),),
    )


def _migration_step() -> StepTemplate:
    return StepTemplate(
        title="Migration heatmap",
        tool_ref=ToolRef("analysis", "bucket_migration"),
        inputs_template={
            "dataset_id": "{slot:performance_dataset_id}",
            "expected_content_hash": "{slot:performance_dataset_content_hash}",
            "id_col": "{slot:id_col}",
            "snapshot_col": "{slot:snapshot_col}",
            "bucket_col": "{slot:bucket_col}",
            "states": "{slot:states}",
            "balance_col": "{slot:balance_col}",
        },
        depends_on_titles=(),
        post_checks=(PostCheck("nonempty", {"field": "avg_matrix"}),),
    )


def _segment_step() -> StepTemplate:
    return StepTemplate(
        title="Segment profiles",
        tool_ref=ToolRef("analysis", "segment_profile"),
        inputs_template={
            "dataset_id": "{slot:performance_dataset_id}",
            "expected_content_hash": "{slot:performance_dataset_content_hash}",
            "segment_col": "{slot:segment_col}",
            "ead_col": "{slot:balance_col}",
        },
        depends_on_titles=(),
        post_checks=(PostCheck("nonempty", {"field": "segments"}),),
    )


def _trend_step() -> StepTemplate:
    return StepTemplate(
        title="Stability trends",
        tool_ref=ToolRef("analysis", "score_stability_trend"),
        inputs_template={
            "experiment_id": "{slot:experiment_id}",
            "dataset_id": "{slot:performance_dataset_id}",
            "expected_content_hash": "{slot:performance_dataset_content_hash}",
            "month_col": "{slot:snapshot_col}",
            "score_col": "{slot:score_col}",
        },
        depends_on_titles=(),
        post_checks=(PostCheck("nonempty", {"field": "trend"}),),
    )


def _el_step() -> StepTemplate:
    return StepTemplate(
        title="Expected loss",
        tool_ref=ToolRef("analysis", "expected_loss_estimate"),
        inputs_template={
            "dataset_id": "{slot:performance_dataset_id}",
            "expected_content_hash": "{slot:performance_dataset_content_hash}",
            "id_col": "{slot:id_col}",
            "snapshot_col": "{slot:snapshot_col}",
            "bucket_col": "{slot:bucket_col}",
            "states": "{slot:states}",
            "balance_col": "{slot:balance_col}",
            "loss_state": "{slot:loss_state}",
            "lgd": "{slot:lgd}",
            "horizon_months": "{slot:horizon_months}",
        },
        depends_on_titles=("Migration heatmap",),
        post_checks=(PostCheck("nonempty", {"field": "chain"}),),
    )


def _gate_step(*, with_trend: bool) -> StepTemplate:
    inputs = {
        "flow": "$ref:Flow analysis.output",
        "migration": "$ref:Migration heatmap.output",
        "segment": "$ref:Segment profiles.output",
        "expected_loss": "$ref:Expected loss.output",
    }
    depends = ["Flow analysis", "Migration heatmap", "Segment profiles", "Expected loss"]
    if with_trend:
        inputs["trend"] = "$ref:Stability trends.output"
        depends.insert(3, "Stability trends")
    return StepTemplate(
        title="Summarize portfolio analysis",
        tool_ref=ToolRef("analysis", "portfolio_gate_summary"),
        inputs_template=inputs,
        depends_on_titles=tuple(depends),
        post_checks=(PostCheck("nonempty", {"field": "checklist"}),),
        decision_point=True,
        needs_confirmation=True,
    )


def _report_step(*, with_trend: bool) -> StepTemplate:
    inputs = {
        "flow": "$ref:Flow analysis.output",
        "migration": "$ref:Migration heatmap.output",
        "segment": "$ref:Segment profiles.output",
        "expected_loss": "$ref:Expected loss.output",
        "project_meta": "{slot:project_meta}",
    }
    # Every $ref needs a dependency edge (PlanValidator), so the report step
    # depends on each analysis step it carries numbers from -- plus the gate,
    # which serializes it after the confirmation.
    depends = ["Flow analysis", "Migration heatmap", "Segment profiles", "Expected loss", "Summarize portfolio analysis"]
    if with_trend:
        inputs["trend"] = "$ref:Stability trends.output"
        depends.insert(3, "Stability trends")
    return StepTemplate(
        title="Generate portfolio report",
        tool_ref=ToolRef("analysis", "portfolio_report"),
        inputs_template=inputs,
        depends_on_titles=tuple(depends),
        post_checks=(PostCheck("nonempty", {"field": "report_path"}),),
    )


PORTFOLIO_ANALYSIS = WorkflowTemplate(
    id="portfolio_analysis",
    title="Portfolio analysis",
    goal_patterns=_GOAL_PATTERNS,
    slots=(
        *_base_slots(),
        SlotSpec("project_meta", False, "task_context", "Project metadata for the report overview"),
    ),
    steps=(
        _flow_step(),
        _migration_step(),
        _segment_step(),
        _trend_step(),
        _el_step(),
        _gate_step(with_trend=True),
        _report_step(with_trend=True),
    ),
    default_autonomy=1,
    source="builtin",
)

# Pruned variant used when no experiment_id is supplied: the stability-trend
# step (4) is dropped and the gate/report no longer inject its $ref. Same id
# family/goal patterns are NOT reused -- this is a distinct id the setup selects.
PORTFOLIO_ANALYSIS_NO_TREND = WorkflowTemplate(
    id="portfolio_analysis_no_trend",
    title="Portfolio analysis without trends",
    goal_patterns=(),
    slots=(
        *_base_slots(),
        SlotSpec("project_meta", False, "task_context", "Project metadata for the report overview"),
    ),
    steps=(
        _flow_step(),
        _migration_step(),
        _segment_step(),
        _el_step(),
        _gate_step(with_trend=False),
        _report_step(with_trend=False),
    ),
    default_autonomy=1,
    source="builtin",
)


__all__ = ["PORTFOLIO_ANALYSIS", "PORTFOLIO_ANALYSIS_NO_TREND"]
