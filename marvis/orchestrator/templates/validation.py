from __future__ import annotations

from marvis.orchestrator.contracts import PostCheck
from marvis.orchestrator.templates import (
    SlotSpec,
    StepTemplate,
    WorkflowTemplate,
)
from marvis.plugins.manifest import ToolRef


MODEL_VALIDATION = WorkflowTemplate(
    id="model_validation",
    title="Model validation",
    goal_patterns=("Model validation", "Validation Model", "model validation", "run validation"),
    slots=(
        SlotSpec("task_id", True, "task_context", "Current validation task id"),
    ),
    steps=(
        StepTemplate(
            title="Scan input files",
            tool_ref=ToolRef("v1_compat", "scan_materials"),
            inputs_template={"task_id": "{slot:task_id}"},
            depends_on_titles=(),
            post_checks=(
                PostCheck("one_of", {"field": "status", "values": ["scanned"]}),
                PostCheck("nonempty", {"field": "materials"}),
            ),
        ),
        StepTemplate(
            title="Run the notebook",
            tool_ref=ToolRef("v1_compat", "run_notebook"),
            inputs_template={"task_id": "{slot:task_id}"},
            depends_on_titles=("Scan input files",),
            post_checks=(
                PostCheck("one_of", {"field": "status", "values": ["executed"]}),
                PostCheck("nonempty", {"field": "evidence_ref"}),
            ),
        ),
        StepTemplate(
            title="Calculate validation metrics",
            tool_ref=ToolRef("v1_compat", "compute_validation_metrics"),
            inputs_template={"task_id": "{slot:task_id}"},
            depends_on_titles=("Run the notebook",),
            post_checks=(
                PostCheck("one_of", {"field": "status", "values": ["writing_artifacts", "review_required"]}),
                PostCheck("range", {"field": "ks", "min": 0.0, "max": 1.0}),
                PostCheck("range", {"field": "auc", "min": 0.0, "max": 1.0}),
                PostCheck("range", {"field": "psi", "min": 0.0, "allow_null": True}),
            ),
        ),
        StepTemplate(
            title="Generate report",
            tool_ref=ToolRef("v1_compat", "render_reports"),
            inputs_template={"task_id": "{slot:task_id}"},
            depends_on_titles=("Calculate validation metrics",),
            post_checks=(
                PostCheck("one_of", {"field": "status", "values": ["succeeded", "review_required"]}),
                PostCheck("nonempty", {"field": "artifacts"}),
            ),
            needs_confirmation=True,
        ),
    ),
    default_autonomy=1,
    source="builtin",
)
