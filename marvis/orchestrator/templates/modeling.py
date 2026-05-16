from __future__ import annotations

from marvis.orchestrator.contracts import PostCheck
from marvis.orchestrator.templates import (
    SlotSpec,
    StepTemplate,
    WorkflowTemplate,
)
from marvis.orchestrator.templates._shared import (
    BINARY_MODELING_SUCCESS_CRITERIA,
    JOIN_EXECUTE_POST_CHECKS,
)
from marvis.plugins.manifest import ToolRef


STANDARD_MODELING = WorkflowTemplate(
    id="standard_modeling",
    title="Standard model development",
    goal_patterns=("Standard Modelling", "Modelling", "Training model", "Model development", "build model", "train model", "standard modeling"),
    slots=(
        SlotSpec("dataset_id", True, "task_context", "Registered modeling dataset id"),
        SlotSpec("target_col", True, "task_context", "Model target column"),
        SlotSpec("feature_cols", True, "task_context", "Candidate feature columns"),
        SlotSpec("split_col", True, "task_context", "Train/test/oot split column"),
        SlotSpec("split_values", True, "task_context", "Split value mapping"),
        SlotSpec("recipe", True, "user", "Modeling recipe id"),
        SlotSpec("seed", True, "task_context", "Reproducibility seed"),
        SlotSpec("business_columns", False, "task_context", "Optional model report business-column mapping"),
        SlotSpec("feature_dictionary_id", False, "task_context", "Optional feature dictionary dataset id"),
        SlotSpec("project_meta", False, "user", "Optional model report project metadata"),
        SlotSpec("champion_reference", False, "task_context", "Optional prior Champion reference for post-training comparison"),
    ),
    steps=(
        StepTemplate(
            title="Check data quality",
            tool_ref=ToolRef("modeling", "check_data_quality"),
            inputs_template={
                "dataset_id": "{slot:dataset_id}",
                "target_col": "{slot:target_col}",
            },
            depends_on_titles=(),
            post_checks=(
                PostCheck(
                    "schema",
                    {
                        "type": "object",
                        "properties": {"issues": {"type": "array"}},
                        "required": ["issues"],
                    },
                ),
            ),
        ),
        StepTemplate(
            title="Check model readiness",
            tool_ref=ToolRef("modeling", "modeling_readiness"),
            inputs_template={
                "dataset_id": "{slot:dataset_id}",
                "target_col": "{slot:target_col}",
                "split_col": "{slot:split_col}",
            },
            depends_on_titles=("Check data quality",),
            post_checks=(PostCheck("one_of", {"field": "ready", "values": [True]}),),
        ),
        StepTemplate(
            title="Prepare model data",
            tool_ref=ToolRef("modeling", "prepare_modeling_frame"),
            inputs_template={
                "dataset_id": "{slot:dataset_id}",
                "target_col": "{slot:target_col}",
                "feature_cols": "{slot:feature_cols}",
                "split_col": "{slot:split_col}",
                "split_config": {},
                "seed": "{slot:seed}",
            },
            depends_on_titles=("Check model readiness",),
            post_checks=(PostCheck("nonempty", {"field": "result_dataset_id"}),),
        ),
        StepTemplate(
            title="Select features",
            tool_ref=ToolRef("modeling", "select_features"),
            inputs_template={
                "dataset_id": "$ref:Prepare model data.output.result_dataset_id",
                "features": "{slot:feature_cols}",
                "target_col": "{slot:target_col}",
                "split_col": "{slot:split_col}",
                "seed": "{slot:seed}",
            },
            depends_on_titles=("Prepare model data",),
            post_checks=(PostCheck("nonempty", {"field": "selected"}),),
        ),
        StepTemplate(
            title="Train models",
            tool_ref=ToolRef("modeling", "train_model"),
            inputs_template={
                "dataset_id": "$ref:Prepare model data.output.result_dataset_id",
                "recipe": "{slot:recipe}",
                "features": "$ref:Select features.output.selected",
                "target_col": "{slot:target_col}",
                "split_col": "{slot:split_col}",
                "split_values": "{slot:split_values}",
                "params": {},
                "seed": "{slot:seed}",
            },
            depends_on_titles=("Prepare model data", "Select features"),
            post_checks=(
                PostCheck("nonempty", {"field": "experiment_id"}),
                PostCheck("nonempty", {"field": "artifact_id"}),
            ),
        ),
        StepTemplate(
            title="Compare experiments",
            tool_ref=ToolRef("modeling", "compare_experiments"),
            inputs_template={"experiment_ids": ["$ref:Train models.output.experiment_id"]},
            depends_on_titles=("Train models",),
            post_checks=(PostCheck("nonempty", {"field": "experiments"}),),
        ),
        StepTemplate(
            title="Select an experiment",
            tool_ref=ToolRef("modeling", "select_experiment"),
            inputs_template={
                "experiment_ids": ["$ref:Train models.output.experiment_id"],
                "target_type": "binary",
                "selection_policy": {
                    "require_pmml": True,
                    "require_handoff": True,
                },
            },
            depends_on_titles=("Train models", "Compare experiments"),
            post_checks=(
                PostCheck("nonempty", {"field": "selected_experiment_id"}),
                PostCheck("nonempty", {"field": "artifact_id"}),
            ),
            needs_confirmation=True,
        ),
        StepTemplate(
            title="Generate model development report",
            tool_ref=ToolRef("modeling", "generate_model_report"),
            inputs_template={
                "experiment_id": "$ref:Select an experiment.output.selected_experiment_id",
                "dataset_id": "{slot:dataset_id}",
                "business_columns": "{slot:business_columns}",
                "feature_dictionary_id": "{slot:feature_dictionary_id}",
                "project_meta": "{slot:project_meta}",
            },
            depends_on_titles=("Select an experiment",),
            post_checks=(
                PostCheck("nonempty", {"field": "report_path"}),
                PostCheck("nonempty", {"field": "section_status"}),
            ),
            needs_confirmation=True,
        ),
        StepTemplate(
            title="Model export options",
            tool_ref=ToolRef("modeling", "post_training_action"),
            inputs_template={
                "experiment_id": "$ref:Select an experiment.output.selected_experiment_id",
                "sample_dataset_id": "{slot:dataset_id}",
                "actions": ["export_pmml", "handoff_to_validation", "create_challenger_backtest"],
                "selection_policy_decision": "$ref:Select an experiment.output.policy_decision",
                "champion_reference": "{slot:champion_reference}",
            },
            depends_on_titles=("Select an experiment", "Generate model development report"),
            post_checks=(
                PostCheck("nonempty", {"field": "artifact_id"}),
                PostCheck("nonempty", {"field": "actions"}),
            ),
            needs_confirmation=True,
        ),
    ),
    default_autonomy=1,
    success_criteria=BINARY_MODELING_SUCCESS_CRITERIA,
    source="builtin",
)

MODELING = WorkflowTemplate(
    # V2 conversational model-development template. The plan-conversation driver
    # instantiates it BY ID for task_type="modeling"; it mirrors the proven
    # ModelingSession prototype flow on the real PlanExecutor:
    #   leakage-aware screen -> [confirm features] -> tune -> train -> compare
    #   -> [confirm model] -> report.
    # phase tags drive right-rail big-step grouping; needs_confirmation marks the
    # two human gates (the executor pauses BEFORE the gated step, so the driver
    # shows the *prior* step's just-computed result at each pause). goal_patterns
    # are intentionally narrow so generic goal routing still resolves the common
    # "Model development"/"Modelling" goals to standard_modeling (legacy select-based flow).
    id="modeling",
    title="Model development",
    goal_patterns=("Dialogue model development", "conversational model development"),
    slots=(
        SlotSpec("dataset_id", True, "task_context", "Registered modeling dataset id"),
        SlotSpec("target_col", True, "task_context", "Binary target column"),
        SlotSpec("feature_cols", True, "task_context", "Candidate feature columns"),
        SlotSpec("split_col", True, "task_context", "Train/test/oot split column"),
        SlotSpec("split_values", True, "task_context", "Split value mapping"),
        SlotSpec("recipe", True, "task_context", "Primary recipe to tune (lgb if among recipes)"),
        SlotSpec("recipes", True, "task_context", "Recipe ids to train + compare (≥1)"),
        SlotSpec("seed", True, "task_context", "Reproducibility seed"),
        SlotSpec("n_trials", False, "task_context", "Per-recipe tuning trial budget", default=1),
        SlotSpec("split_config", False, "task_context", "Split rules/config for the G1 make_split gate (passthrough when empty)"),
        SlotSpec("target_type", False, "task_context", "Target type: binary, continuous, or multiclass"),
        SlotSpec("holdout_values", False, "task_context", "OOT split value(s) held out of the leakage screen"),
        SlotSpec("sample_weight_col", False, "task_context", "Optional sample-weight column for fit/sample weighting"),
        SlotSpec("sample_weight_candidates", False, "task_context", "Detected sample-weight candidate columns"),
        SlotSpec("sample_weight_diagnostics", False, "task_context", "Sample-weight quality diagnostics"),
        SlotSpec("tuning_params", False, "task_context", "Optional fixed tuning/training params chosen by the user or agent"),
        SlotSpec("special_value_decisions", False, "user", "Per-column mask, retain, or drop decisions for detected special values"),
        SlotSpec("passthrough_cols", False, "task_context", "Non-feature columns to preserve in the modeling frame"),
        SlotSpec("business_columns", False, "task_context", "Optional model report business-column mapping"),
        SlotSpec("feature_dictionary_id", False, "task_context", "Optional feature dictionary dataset id"),
        SlotSpec("project_meta", False, "user", "Optional model report project metadata"),
        SlotSpec("champion_reference", False, "task_context", "Optional prior Champion reference for post-training comparison"),
        SlotSpec("selection_policy", False, "task_context", "Final model selection delivery policy"),
    ),
    steps=(
        StepTemplate(
            title="Partition samples",
            tool_ref=ToolRef("modeling", "make_split"),
            inputs_template={
                "dataset_id": "{slot:dataset_id}",
                "target_col": "{slot:target_col}",
                "feature_cols": "{slot:feature_cols}",
                "split_col": "{slot:split_col}",
                "split_config": "{slot:split_config}",
                "passthrough_cols": "{slot:passthrough_cols}",
                "seed": "{slot:seed}",
            },
            depends_on_titles=(),
            post_checks=(PostCheck("nonempty", {"field": "result_dataset_id"}),),
            phase="Characteristics",
        ),
        StepTemplate(
            title="Choose model settings",
            tool_ref=ToolRef("modeling", "choose_modeling_spec"),
            inputs_template={
                "target_col": "{slot:target_col}",
                "features": "$ref:Partition samples.output.feature_cols",
                "target_type": "{slot:target_type}",
                "recipe": "{slot:recipe}",
                "recipes": "{slot:recipes}",
                "sample_weight_col": "{slot:sample_weight_col}",
                "sample_weight_candidates": "{slot:sample_weight_candidates}",
                "sample_weight_diagnostics": "{slot:sample_weight_diagnostics}",
                # Product default is one trial per recipe, while an explicitly
                # proposed first-turn budget is carried through this slot.
                "n_trials": "{slot:n_trials}",
                "params": "{slot:tuning_params}",
                "seed": "{slot:seed}",
            },
            depends_on_titles=("Partition samples",),
            post_checks=(
                PostCheck("nonempty", {"field": "recipe"}),
                PostCheck("nonempty", {"field": "recipes"}),
            ),
            # This step defines the feature universe and target type consumed by
            # the following screen, so it belongs to feature preparation in the
            # execution rail rather than the later tuning/training phase.
            phase="Characteristics",
        ),
        StepTemplate(
            title="Screen features",
            tool_ref=ToolRef("modeling", "screen_features"),
            inputs_template={
                "dataset_id": "$ref:Partition samples.output.result_dataset_id",
                "features": "$ref:Choose model settings.output.feature_cols",
                "target_col": "{slot:target_col}",
                "split_col": "$ref:Partition samples.output.split_col",
                "sample_weight_col": "$ref:Choose model settings.output.sample_weight_col",
                "holdout_values": "$ref:Partition samples.output.holdout_values",
                "target_type": "$ref:Choose model settings.output.target_type",
                "leakage_ks": 0.4,
                "max_missing_rate": 0.95,
                # Loose top_k backstop (FS-1 decision #3): a wide raw table (hundreds/
                # thousands of clean columns) must not flow straight into multivariate
                # refinement unbounded — 200 is far above any real feature count but
                # caps the pathological case. iv_min/corr_max in "Select Character" below do the
                # real narrowing.
                "top_k": 200,
            },
            depends_on_titles=("Partition samples", "Choose model settings"),
            # Empty recommendations are a reviewable data-quality result. The
            # next gate still renders every metric/reason so the user can repair
            # the join or adjust thresholds instead of receiving a system error.
            post_checks=(),
            # G1 Door.:Confirm the cut.(train/test/oot Count, monthly/Channel distribution)Then sift the features.
            #(Executor Pause Before This Step,Driver Show"Scratch samples"Sample analysis of outputs)
            needs_confirmation=True,
            phase="Characteristics",
        ),
        StepTemplate(
            title="Handle special values",
            tool_ref=ToolRef("modeling", "resolve_special_values"),
            inputs_template={
                "dataset_id": "$ref:Partition samples.output.result_dataset_id",
                "features": "$ref:Screen features.output.selected",
                "sentinel_columns": "$ref:Screen features.output.sentinel_columns",
                "decisions": "{slot:special_value_decisions}",
                "seed": "$ref:Choose model settings.output.seed",
            },
            depends_on_titles=("Partition samples", "Choose model settings", "Screen features"),
            post_checks=(
                PostCheck("nonempty", {"field": "result_dataset_id"}),
                PostCheck("nonempty", {"field": "selected"}),
            ),
            # Special-value policy is a real pre-execution HITL gate.  The
            # preceding screen result is rendered here and the selected
            # mask/retain/drop decisions are written atomically onto this step
            # before it is allowed to run.
            needs_confirmation=True,
            phase="Characteristics",
        ),
        StepTemplate(
            # FS-1: multivariate refinement funnel between the sanity-level screen and
            # tuning — IV floor + correlation dedup narrow the screen's clean-but-
            # unranked candidate set before it reaches the model. VIF stays off by
            # default (vif_max=1e9 below never trips; tree recipes don't need
            # multicollinearity control the way linear scorecards do) but iv_min/
            # corr_max are adjustable via the gate's adjust path (same generic
            # mechanism as the screen gate's leakage_ks/max_missing_rate) to loosen or
            # effectively bypass the funnel.
            title="Select features",
            tool_ref=ToolRef("modeling", "select_features"),
            inputs_template={
                "dataset_id": "$ref:Handle special values.output.result_dataset_id",
                "features": "$ref:Handle special values.output.selected",
                "target_col": "{slot:target_col}",
                "split_col": "$ref:Partition samples.output.split_col",
                # FS-2/D11: selection must fit TRAIN ONLY. Do NOT forward the screen's
                # ['oot'] holdout slot here — let select_features apply its own
                # ('test','oot') default so IV/corr/VIF/top_k never see test-split
                # labels. The screen core also fits train-only; this holdout output is
                # retained there solely for OOT distribution-stability diagnostics.
                "target_type": "$ref:Choose model settings.output.target_type",
                "seed": "$ref:Choose model settings.output.seed",
                "space": "raw",
                "iv_min": 0.02,
                "corr_max": 0.95,
                # VIF off by default (tree recipes don't need multicollinearity control
                # the way linear scorecards do): 1e9 matches correlation.py's own VIF
                # cap sentinel, so the >vif_max check never trips. Set a real threshold
                # (e.g. 10.0) via adjust/template override to opt in.
                "vif_max": 1e9,
            },
            depends_on_titles=("Partition samples", "Screen features", "Handle special values", "Choose model settings"),
            post_checks=(PostCheck("nonempty", {"field": "selected"}),),
            # Door.:Confirm the selected feature funnel(In./Number of features,IV Bottom line and associated redundancy are phased out.)Configure the transfer later
            #(Executor Pause Before This Step,Driver Show"Feature Filter"Outputs;Confirm before entering the reference configuration)
            needs_confirmation=True,
            phase="Characteristics",
        ),
        StepTemplate(
            title="Configure hyperparameter tuning",
            tool_ref=ToolRef("modeling", "configure_tuning"),
            inputs_template={
                "recipe": "$ref:Choose model settings.output.recipe",
                "recipes": "$ref:Choose model settings.output.recipes",
                "target_type": "$ref:Choose model settings.output.target_type",
                "sample_weight_col": "$ref:Choose model settings.output.sample_weight_col",
                "n_trials_by_recipe": "$ref:Choose model settings.output.n_trials_by_recipe",
                "params": "$ref:Choose model settings.output.params",
                "seed": "$ref:Choose model settings.output.seed",
            },
            depends_on_titles=("Choose model settings", "Select features"),
            post_checks=(
                PostCheck("nonempty", {"field": "reason"}),
            ),
            needs_confirmation=True,
            phase="Modelling",
        ),
        StepTemplate(
            title="Tune hyperparameters",
            tool_ref=ToolRef("modeling", "tune_hyperparameters"),
            inputs_template={
                "dataset_id": "$ref:Handle special values.output.result_dataset_id",
                "features": "$ref:Select features.output.selected",
                "target_col": "{slot:target_col}",
                "split_col": "$ref:Partition samples.output.split_col",
                "split_values": "$ref:Partition samples.output.split_values",
                "recipe": "$ref:Configure hyperparameter tuning.output.recipe",
                "recipes": "$ref:Configure hyperparameter tuning.output.recipes",
                "sample_weight_col": "$ref:Configure hyperparameter tuning.output.sample_weight_col",
                "seed": "$ref:Configure hyperparameter tuning.output.seed",
                "params": "$ref:Configure hyperparameter tuning.output.params",
                "sentinel_columns": "$ref:Screen features.output.sentinel_columns",
                "special_value_governance": "$ref:Handle special values.output.governance",
                # Bounded two-stage random search per recipe so the synchronous
                # driver turn stays responsive; users can request a wider search
                # later (G3). Every BINARY_MODELING_RECIPES family now tunes
                # (TUNE-1/SEL-2) — each with its own budget from n_trials_by_recipe.
                "n_trials_by_recipe": "$ref:Configure hyperparameter tuning.output.n_trials_by_recipe",
            },
            depends_on_titles=("Partition samples", "Screen features", "Handle special values", "Select features", "Configure hyperparameter tuning"),
            # best_params must be present + a dict: single recipe -> flat params
            # dict (possibly empty for a non-tunable family); multiple recipes ->
            # a dict keyed by recipe id, each value itself the tuned params dict.
            post_checks=(PostCheck("schema", {
                "type": "object",
                "properties": {"best_params": {"type": "object"}},
                "required": ["best_params"],
            }),),
            # Door.:We'll use the force to adjust after we confirm the filtered feature set.(Executor Pause Before This Step,Driver Show"Feature Filter"Outputs)
            needs_confirmation=True,
            phase="Modelling",
        ),
        StepTemplate(
            title="Train models",
            tool_ref=ToolRef("modeling", "train_models"),
            inputs_template={
                "dataset_id": "$ref:Handle special values.output.result_dataset_id",
                "recipes": "$ref:Choose model settings.output.recipes",
                "features": "$ref:Select features.output.selected",
                "target_col": "{slot:target_col}",
                "split_col": "$ref:Partition samples.output.split_col",
                "split_values": "$ref:Partition samples.output.split_values",
                "params": "$ref:Tune hyperparameters.output.best_params",
                "sample_weight_col": "$ref:Choose model settings.output.sample_weight_col",
                "seed": "$ref:Choose model settings.output.seed",
                "target_type": "$ref:Choose model settings.output.target_type",
                "sentinel_columns": "$ref:Screen features.output.sentinel_columns",
                "special_value_governance": "$ref:Handle special values.output.governance",
            },
            depends_on_titles=("Partition samples", "Screen features", "Handle special values", "Choose model settings", "Select features", "Tune hyperparameters"),
            post_checks=(PostCheck("nonempty", {"field": "best_experiment_id"}),),
            phase="Modelling",
        ),
        StepTemplate(
            title="Compare experiments",
            tool_ref=ToolRef("modeling", "compare_experiments"),
            inputs_template={"experiment_ids": "$ref:Train models.output.experiment_ids"},
            depends_on_titles=("Train models",),
            post_checks=(PostCheck("nonempty", {"field": "experiments"}),),
            phase="Modelling",
        ),
        StepTemplate(
            title="Select an experiment",
            tool_ref=ToolRef("modeling", "select_experiment"),
            inputs_template={
                "experiment_ids": "$ref:Train models.output.experiment_ids",
                "target_type": "$ref:Choose model settings.output.target_type",
                "selection_policy": "{slot:selection_policy}",
            },
            depends_on_titles=("Choose model settings", "Tune hyperparameters", "Train models", "Compare experiments"),
            post_checks=(
                PostCheck("nonempty", {"field": "selected_experiment_id"}),
                PostCheck("nonempty", {"field": "artifact_id"}),
            ),
            needs_confirmation=True,
            phase="Modelling",
        ),
        StepTemplate(
            title="Generate model development report",
            tool_ref=ToolRef("modeling", "generate_model_reports"),
            inputs_template={
                # Preserve every trained version as a first-class report; the
                # selected experiment remains the sole delivery Champion.
                "experiment_ids": "$ref:Select an experiment.output.report_experiment_ids",
                "selected_experiment_id": "$ref:Select an experiment.output.selected_experiment_id",
                "dataset_id": "$ref:Handle special values.output.result_dataset_id",
                "business_columns": "{slot:business_columns}",
                "feature_dictionary_id": "{slot:feature_dictionary_id}",
                "project_meta": "{slot:project_meta}",
            },
            # depends on Transfertoo so the model gate shows the trials leaderboard (G4)
            # alongside the trained-model metrics before the report is finalized.
            depends_on_titles=("Handle special values", "Tune hyperparameters", "Train models", "Select an experiment"),
            post_checks=(
                PostCheck("nonempty", {"field": "report_path"}),
                PostCheck("nonempty", {"field": "reports"}),
            ),
            # Door.:Identification of training indicators/trials Finalize the report(Executor Pause Before This Step,Driver Showtrain+compare)
            needs_confirmation=True,
            phase="Report",
        ),
        StepTemplate(
            title="Model export options",
            tool_ref=ToolRef("modeling", "post_training_action"),
            inputs_template={
                "experiment_id": "$ref:Select an experiment.output.selected_experiment_id",
                "sample_dataset_id": "$ref:Handle special values.output.result_dataset_id",
                "actions": ["export_pmml", "handoff_to_validation", "create_challenger_backtest"],
                "selection_policy_decision": "$ref:Select an experiment.output.policy_decision",
                "champion_reference": "{slot:champion_reference}",
            },
            depends_on_titles=("Handle special values", "Select an experiment", "Generate model development report"),
            post_checks=(
                PostCheck("nonempty", {"field": "artifact_id"}),
                PostCheck("nonempty", {"field": "actions"}),
            ),
            needs_confirmation=True,
            phase="Delivery",
        ),
    ),
    default_autonomy=1,
    success_criteria=BINARY_MODELING_SUCCESS_CRITERIA,
    source="builtin",
)

MODELING_WITH_JOIN = WorkflowTemplate(
    id="modeling_with_join",
    title="Model development across tables",
    goal_patterns=("Multi-Table Model Development", "join then modeling"),
    slots=(
        SlotSpec("anchor_id", True, "task_context", "Anchor sample dataset id"),
        SlotSpec("feature_ids", True, "task_context", "Feature dataset ids to join"),
        SlotSpec("target_col", True, "task_context", "Target column on the anchor/joined sample"),
        SlotSpec("feature_cols", False, "task_context", "Candidate feature columns; empty means infer after join"),
        SlotSpec("split_col", False, "task_context", "Existing split column, if any"),
        SlotSpec("split_values", False, "task_context", "Existing split value mapping, if any"),
        SlotSpec("recipe", True, "task_context", "Primary recipe to tune (lgb if among recipes)"),
        SlotSpec("recipes", True, "task_context", "Recipe ids to train + compare"),
        SlotSpec("seed", True, "task_context", "Reproducibility seed"),
        SlotSpec("n_trials", False, "task_context", "Per-recipe tuning trial budget", default=1),
        SlotSpec("split_config", False, "task_context", "Split rules/config for the G1 make_split gate"),
        SlotSpec("target_type", False, "task_context", "Target type: binary, continuous, or multiclass"),
        SlotSpec("holdout_values", False, "task_context", "OOT split value(s) held out of the leakage screen"),
        SlotSpec("sample_weight_col", False, "task_context", "Optional sample-weight column for fit/sample weighting"),
        SlotSpec("sample_weight_candidates", False, "task_context", "Detected sample-weight candidate columns"),
        SlotSpec("sample_weight_diagnostics", False, "task_context", "Sample-weight quality diagnostics"),
        SlotSpec("tuning_params", False, "task_context", "Optional fixed tuning/training params chosen by the user or agent"),
        SlotSpec("special_value_decisions", False, "user", "Per-column mask, retain, or drop decisions for detected special values"),
        SlotSpec("passthrough_cols", False, "task_context", "Non-feature columns to preserve in the modeling frame"),
        SlotSpec("business_columns", False, "task_context", "Optional model report business-column mapping"),
        SlotSpec("feature_dictionary_id", False, "task_context", "Optional feature dictionary dataset id"),
        SlotSpec("project_meta", False, "user", "Optional model report project metadata"),
        SlotSpec("champion_reference", False, "task_context", "Optional prior Champion reference for post-training comparison"),
        SlotSpec("dedup_strategies", False, "task_context", "Optional per-feature dedup strategy map"),
        SlotSpec("selection_policy", False, "task_context", "Final model selection delivery policy"),
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
            post_checks=(PostCheck("one_of", {"field": "status", "values": ["confirmed", "needs_dedup"]}),),
            phase="Data readiness",
        ),
        StepTemplate(
            title="Join tables",
            tool_ref=ToolRef("data_ops", "execute_join"),
            inputs_template={"join_plan_id": "$ref:Review join diagnostics.output.join_plan_id"},
            depends_on_titles=("Review join diagnostics", "Confirm join settings"),
            post_checks=JOIN_EXECUTE_POST_CHECKS,
            needs_confirmation=True,
            phase="Data readiness",
        ),
        StepTemplate(
            title="Partition samples",
            tool_ref=ToolRef("modeling", "make_split"),
            inputs_template={
                "dataset_id": "$ref:Join tables.output.result_dataset_id",
                "target_col": "{slot:target_col}",
                "feature_cols": "{slot:feature_cols}",
                "split_col": "{slot:split_col}",
                "split_config": "{slot:split_config}",
                "passthrough_cols": "{slot:passthrough_cols}",
                "seed": "{slot:seed}",
            },
            depends_on_titles=("Join tables",),
            post_checks=(PostCheck("nonempty", {"field": "result_dataset_id"}),),
            phase="Characteristics",
        ),
        StepTemplate(
            title="Choose model settings",
            tool_ref=ToolRef("modeling", "choose_modeling_spec"),
            inputs_template={
                "target_col": "{slot:target_col}",
                "features": "$ref:Partition samples.output.feature_cols",
                "target_type": "{slot:target_type}",
                "recipe": "{slot:recipe}",
                "recipes": "{slot:recipes}",
                "sample_weight_col": "{slot:sample_weight_col}",
                "sample_weight_candidates": "{slot:sample_weight_candidates}",
                "sample_weight_diagnostics": "{slot:sample_weight_diagnostics}",
                "n_trials": "{slot:n_trials}",
                "params": "{slot:tuning_params}",
                "seed": "{slot:seed}",
            },
            depends_on_titles=("Partition samples",),
            post_checks=(
                PostCheck("nonempty", {"field": "recipe"}),
                PostCheck("nonempty", {"field": "recipes"}),
            ),
            phase="Characteristics",
        ),
        StepTemplate(
            title="Screen features",
            tool_ref=ToolRef("modeling", "screen_features"),
            inputs_template={
                "dataset_id": "$ref:Partition samples.output.result_dataset_id",
                "features": "$ref:Choose model settings.output.feature_cols",
                "target_col": "{slot:target_col}",
                "split_col": "$ref:Partition samples.output.split_col",
                "sample_weight_col": "$ref:Choose model settings.output.sample_weight_col",
                "holdout_values": "$ref:Partition samples.output.holdout_values",
                "target_type": "$ref:Choose model settings.output.target_type",
                "leakage_ks": 0.4,
                "max_missing_rate": 0.95,
                # Loose top_k backstop (FS-1 decision #3), same rationale as MODELING.
                "top_k": 200,
            },
            depends_on_titles=("Partition samples", "Choose model settings"),
            post_checks=(),
            needs_confirmation=True,
            phase="Characteristics",
        ),
        StepTemplate(
            title="Handle special values",
            tool_ref=ToolRef("modeling", "resolve_special_values"),
            inputs_template={
                "dataset_id": "$ref:Partition samples.output.result_dataset_id",
                "features": "$ref:Screen features.output.selected",
                "sentinel_columns": "$ref:Screen features.output.sentinel_columns",
                "decisions": "{slot:special_value_decisions}",
                "seed": "$ref:Choose model settings.output.seed",
            },
            depends_on_titles=("Partition samples", "Choose model settings", "Screen features"),
            post_checks=(
                PostCheck("nonempty", {"field": "result_dataset_id"}),
                PostCheck("nonempty", {"field": "selected"}),
            ),
            needs_confirmation=True,
            phase="Characteristics",
        ),
        StepTemplate(
            # FS-1 multivariate refinement funnel — see MODELING template for rationale.
            title="Select features",
            tool_ref=ToolRef("modeling", "select_features"),
            inputs_template={
                "dataset_id": "$ref:Handle special values.output.result_dataset_id",
                "features": "$ref:Handle special values.output.selected",
                "target_col": "{slot:target_col}",
                "split_col": "$ref:Partition samples.output.split_col",
                # FS-2/D11: selection must fit TRAIN ONLY. Do NOT forward make_split's
                # ['oot'] holdout into select — let select_features apply its own
                # ('test','oot') default so IV/corr/VIF/top_k never see test-split
                # labels. The screen core also fits train-only; that holdout output is
                # retained there solely for OOT distribution-stability diagnostics.
                "target_type": "$ref:Choose model settings.output.target_type",
                "seed": "$ref:Choose model settings.output.seed",
                "space": "raw",
                "iv_min": 0.02,
                "corr_max": 0.95,
                # VIF off by default — see MODELING template for rationale.
                "vif_max": 1e9,
            },
            depends_on_titles=("Partition samples", "Screen features", "Handle special values", "Choose model settings"),
            post_checks=(PostCheck("nonempty", {"field": "selected"}),),
            needs_confirmation=True,
            phase="Characteristics",
        ),
        StepTemplate(
            title="Configure hyperparameter tuning",
            tool_ref=ToolRef("modeling", "configure_tuning"),
            inputs_template={
                "recipe": "$ref:Choose model settings.output.recipe",
                "recipes": "$ref:Choose model settings.output.recipes",
                "target_type": "$ref:Choose model settings.output.target_type",
                "sample_weight_col": "$ref:Choose model settings.output.sample_weight_col",
                "n_trials_by_recipe": "$ref:Choose model settings.output.n_trials_by_recipe",
                "params": "$ref:Choose model settings.output.params",
                "seed": "$ref:Choose model settings.output.seed",
            },
            depends_on_titles=("Choose model settings", "Select features"),
            post_checks=(
                PostCheck("nonempty", {"field": "reason"}),
            ),
            needs_confirmation=True,
            phase="Modelling",
        ),
        StepTemplate(
            title="Tune hyperparameters",
            tool_ref=ToolRef("modeling", "tune_hyperparameters"),
            inputs_template={
                "dataset_id": "$ref:Handle special values.output.result_dataset_id",
                "features": "$ref:Select features.output.selected",
                "target_col": "{slot:target_col}",
                "split_col": "$ref:Partition samples.output.split_col",
                "split_values": "$ref:Partition samples.output.split_values",
                "recipe": "$ref:Configure hyperparameter tuning.output.recipe",
                "recipes": "$ref:Configure hyperparameter tuning.output.recipes",
                "sample_weight_col": "$ref:Configure hyperparameter tuning.output.sample_weight_col",
                "seed": "$ref:Configure hyperparameter tuning.output.seed",
                "params": "$ref:Configure hyperparameter tuning.output.params",
                "sentinel_columns": "$ref:Screen features.output.sentinel_columns",
                "special_value_governance": "$ref:Handle special values.output.governance",
                "n_trials_by_recipe": "$ref:Configure hyperparameter tuning.output.n_trials_by_recipe",
            },
            depends_on_titles=(
                "Partition samples",
                "Screen features",
                "Handle special values",
                "Select features",
                "Configure hyperparameter tuning",
            ),
            post_checks=(PostCheck("schema", {
                "type": "object",
                "properties": {"best_params": {"type": "object"}},
                "required": ["best_params"],
            }),),
            needs_confirmation=True,
            phase="Modelling",
        ),
        StepTemplate(
            title="Train models",
            tool_ref=ToolRef("modeling", "train_models"),
            inputs_template={
                "dataset_id": "$ref:Handle special values.output.result_dataset_id",
                "recipes": "$ref:Choose model settings.output.recipes",
                "features": "$ref:Select features.output.selected",
                "target_col": "{slot:target_col}",
                "split_col": "$ref:Partition samples.output.split_col",
                "split_values": "$ref:Partition samples.output.split_values",
                "params": "$ref:Tune hyperparameters.output.best_params",
                "sample_weight_col": "$ref:Choose model settings.output.sample_weight_col",
                "seed": "$ref:Choose model settings.output.seed",
                "target_type": "$ref:Choose model settings.output.target_type",
                "sentinel_columns": "$ref:Screen features.output.sentinel_columns",
                "special_value_governance": "$ref:Handle special values.output.governance",
            },
            depends_on_titles=(
                "Partition samples",
                "Screen features",
                "Handle special values",
                "Choose model settings",
                "Select features",
                "Tune hyperparameters",
            ),
            post_checks=(PostCheck("nonempty", {"field": "best_experiment_id"}),),
            phase="Modelling",
        ),
        StepTemplate(
            title="Compare experiments",
            tool_ref=ToolRef("modeling", "compare_experiments"),
            inputs_template={"experiment_ids": "$ref:Train models.output.experiment_ids"},
            depends_on_titles=("Train models",),
            post_checks=(PostCheck("nonempty", {"field": "experiments"}),),
            phase="Modelling",
        ),
        StepTemplate(
            title="Select an experiment",
            tool_ref=ToolRef("modeling", "select_experiment"),
            inputs_template={
                "experiment_ids": "$ref:Train models.output.experiment_ids",
                "target_type": "$ref:Choose model settings.output.target_type",
                "selection_policy": "{slot:selection_policy}",
            },
            depends_on_titles=("Choose model settings", "Tune hyperparameters", "Train models", "Compare experiments"),
            post_checks=(
                PostCheck("nonempty", {"field": "selected_experiment_id"}),
                PostCheck("nonempty", {"field": "artifact_id"}),
            ),
            needs_confirmation=True,
            phase="Modelling",
        ),
        StepTemplate(
            title="Generate model development report",
            tool_ref=ToolRef("modeling", "generate_model_reports"),
            inputs_template={
                "experiment_ids": "$ref:Select an experiment.output.report_experiment_ids",
                "selected_experiment_id": "$ref:Select an experiment.output.selected_experiment_id",
                "dataset_id": "$ref:Handle special values.output.result_dataset_id",
                "business_columns": "{slot:business_columns}",
                "feature_dictionary_id": "{slot:feature_dictionary_id}",
                "project_meta": "{slot:project_meta}",
            },
            depends_on_titles=("Handle special values", "Tune hyperparameters", "Train models", "Select an experiment"),
            post_checks=(
                PostCheck("nonempty", {"field": "report_path"}),
                PostCheck("nonempty", {"field": "reports"}),
            ),
            needs_confirmation=True,
            phase="Report",
        ),
        StepTemplate(
            title="Model export options",
            tool_ref=ToolRef("modeling", "post_training_action"),
            inputs_template={
                "experiment_id": "$ref:Select an experiment.output.selected_experiment_id",
                "sample_dataset_id": "$ref:Handle special values.output.result_dataset_id",
                "actions": ["export_pmml", "handoff_to_validation", "create_challenger_backtest"],
                "selection_policy_decision": "$ref:Select an experiment.output.policy_decision",
                "champion_reference": "{slot:champion_reference}",
            },
            depends_on_titles=("Handle special values", "Select an experiment", "Generate model development report"),
            post_checks=(
                PostCheck("nonempty", {"field": "artifact_id"}),
                PostCheck("nonempty", {"field": "actions"}),
            ),
            needs_confirmation=True,
            phase="Delivery",
        ),
    ),
    default_autonomy=1,
    success_criteria=BINARY_MODELING_SUCCESS_CRITERIA,
    source="builtin",
)
