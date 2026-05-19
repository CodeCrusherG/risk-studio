"""strategy_sample driver-turn handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
import json
import math
import re
from types import SimpleNamespace
from marvis.agent.strategy_setup import StrategySetupError, build_strategy_dataset_context, preview_strategy_dataset_context
from marvis.agent.strategy_request_compiler import StandardWorkflowRequestDraft, validate_strategy_request
from marvis.agent.strategy_workflows._foundation_delivery import select_sample_design_v2_template
from marvis.data.backend import DataBackend
from marvis.data.errors import DatasetContentDriftError
from marvis.data.registry import DatasetRegistry
from marvis.data.workspace import DataSemanticMapping, DataWorkspaceDraft, data_semantic_mapping_hash
from marvis.repositories.datasets import DatasetRepository
from marvis.repositories.tasks import TaskRepository
from marvis.domain import TaskRecord
from marvis.packs.strategy.errors import StrategyError, StrategySampleDesignScopeIneligibleError
from marvis.packs.strategy.sample_design_binding import load_strategy_sample_design_execution_binding
from marvis.packs.strategy.sample_design_execution import load_strategy_risk_development_execution_binding
from marvis.packs.strategy.sample_design_tools import SAMPLE_DESIGN_ARTIFACT_KIND, SAMPLE_DESIGN_ORIGIN_TOOL
from marvis.packs.strategy.sample_design_v2_tools import SAMPLE_DESIGN_V2_BUNDLE_ARTIFACT_KIND, SAMPLE_DESIGN_V2_ORIGIN_TOOL, load_any_strategy_sample_design_v2_artifacts
from marvis.packs.strategy.sample_design_v2_native_tools import SAMPLE_DESIGN_V2_NATIVE_ORIGIN_TOOL, authenticate_native_strategy_sample_design_v2_bundle_record
from marvis.repositories.task_artifacts import TaskArtifactRepository
from marvis.repositories.data_workspace import DataWorkspaceDataError, DataWorkspaceDatasetNotFound, DataWorkspaceRepository, DataWorkspaceRevisionConflict

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import DriverTurnRuntime
    from . import _STRATEGY_POOL_MEASUREMENT_WORKFLOWS
    from . import _STRATEGY_V2_ARTIFACT_ERRORS
    from . import _StrategySampleDesignPolicyMismatchError
    from . import _StrategySampleDesignRequiredError
    from . import _StrategyV2EvidenceSetupError
    from . import _active_plan
    from . import _modeling_data_runtime
    from . import _prepare_and_run_validated_strategy_request
    from . import _strategy_dataset_context
    from . import _strategy_dataset_preview
    from . import _strategy_pool_impact_dataset_preview
    from . import _strategy_pool_impact_pool_binding
    from . import _strategy_request_allowed_columns
    from . import _strategy_request_clarification_response
    from . import _strategy_request_preflight
    from . import latest_open_gate

_STRATEGY_SAMPLE_BOUND_TOOLS = frozenset(
    {
        "analyze_univariate_candidates",
        "backtest_strategy",
        "build_automatic_tree_candidate",
        "compare_strategies",
        "design_cutoff_bands",
        "design_strategy_candidate",
        "evaluate_rule_set",
        "limit_pricing_matrix",
        "measure_pool_impact",
        "mine_rules",
        "tradeoff_view",
    }
)

_STRATEGY_SAMPLE_DESIGN_REQUIRED_FIELDS = (
    "target_bad_value",
    "drop_nan_labels",
    "relationship",
    "approval_population",
    "risk_population",
    "partitioning",
    "maturity",
    "performance_window",
    "observation_window",
    "field_bindings",
    "historical_score",
)

_STRATEGY_SAMPLE_DESIGN_V2_MISSING_CONTROLS = (
    "target_bad_value",
    "drop_nan_labels",
    "relationship",
    "approval_population",
    "risk_population",
    "partitioning",
    "maturity",
    "performance_window",
    "observation_window",
    "field_bindings",
)

_STRATEGY_SAMPLE_BOUND_CANDIDATE_WORKFLOWS = frozenset(
    {
        "univariate_candidate_analysis",
        "univariate_candidate_refinement",
        "automatic_tree_candidate_build",
        "cross_matrix_analysis",
    }
)

_STRATEGY_NAN_LABEL_META_KEY = "strategy_nan_label_confirmation"

_STRATEGY_SAMPLE_V2_POLICY = {
    "minimum_partition_count": 1,
    "minimum_bad_count": 1,
    "minimum_label_coverage": 0.8,
    "minimum_historical_score_coverage": 0.8,
    "maximum_group_coverage_gap": 0.2,
    "diagnostic_severities": {
        "entity_overlap": "fail",
        "temporal_oot": "fail",
        "risk_outside_approval": "fail",
        "maturity": "fail",
        "label_coverage": "fail",
        "historical_score_coverage": "warn",
        "group_coverage_gap": "warn",
        "sufficiency": "fail",
    },
}

_STRATEGY_DROP_NAN_CONFIRM_RE = re.compile(
    r"(?:Confirm.|Agreed.|Allow|Yeah.).{0,12}(?:Drop|Exclude|Remove|Delete).{0,12}"
    r"(?:NaN|nan|Empty Tab|Missing tab|Invalid Tab)|"
    r"(?:Confirm.|Agreed.|Allow|Yeah.).{0,12}"
    r"(?:NaN|nan|Empty Tab|Missing tab|Invalid Tab).{0,24}"
    r"(?:Risk|Bad debts.).{0,8}Factor.{0,8}(?:Exclude|Remove)|"
    r"(?:confirm|allow).{0,12}(?:drop|exclude).{0,12}(?:nan|missing)\s+labels?",
    re.IGNORECASE,
)

_STRATEGY_DROP_NAN_CANCEL_RE = re.compile(
    r"(?:Do Not Abandon|Not ruled out.|Do Not Erase|Do Not Delete|Cancel|Stop|"
    r"do\s+not\s+(?:drop|exclude)|don't\s+(?:drop|exclude))",
    re.IGNORECASE,
)

def _strategy_sample_design_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
    *,
    context,
    drop_nan_labels: bool,
) -> dict[str, object]:
    """Bind user-owned sample facts to the exact active workspace snapshot."""

    try:
        workspace = _require_strategy_sample_design_workspace(runtime, task)
    except StrategySetupError:
        raise
    if (
        workspace.active_dataset_id != context.dataset_id
        or workspace.active_dataset_content_hash != context.dataset_content_hash
        or workspace.revision != context.workspace_revision
        or workspace.analysis_generation != context.analysis_generation
    ):
        raise StrategySetupError(
            "ActivitiesDataWorkspace Change before the sample design plan is created; please try again based on the current version."
        )
    target_col = workspace.semantic_mapping.target_col
    if (
        not isinstance(target_col, str)
        or not target_col
        or target_col != context.target_col
        or target_col not in context.columns
    ):
        raise StrategySetupError(
            "The policy sample is only available.DataWorkspace ."
        )
    content_hash = workspace.active_dataset_content_hash
    semantic_hash = data_semantic_mapping_hash(workspace.semantic_mapping)
    if not isinstance(content_hash, str) or not content_hash:
        raise StrategySetupError("Activity data set missing contenthash,No sample design can be solidified.")
    if semantic_hash != context.semantic_mapping_hash:
        raise StrategySetupError(
            "ActivitiesDataWorkspace ; please restart the sample design."
        )

    inputs = draft.to_dict()["workflow_inputs"]
    for field in (
        "split_col",
        "month_col",
        "weight_col",
        "loan_amount_col",
        "overdue_amount_col",
    ):
        column = inputs.get(field)
        if column is not None and column not in context.columns:
            raise StrategySetupError(
                f"Policy sample design visible field{field} Not currently in activity data concentration."
            )
    slots: dict[str, object] = {
        "dataset_id": workspace.active_dataset_id,
        "expected_dataset_content_hash": content_hash,
        "workspace_revision": workspace.revision,
        "workspace_generation": workspace.analysis_generation,
        "semantic_mapping_hash": semantic_hash,
        "target_col": target_col,
        "drop_nan_labels": bool(drop_nan_labels),
    }
    slots.update(
        {
            key: value
            for key, value in inputs.items()
            if key != "drop_nan_labels"
        }
    )
    return slots

def _strategy_sample_design_v2_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
    *,
    context,
    drop_nan_labels: bool,
) -> dict[str, object]:
    """Bind platform context, adding compatibility slots only when lossless."""

    workspace = _require_strategy_sample_design_workspace(runtime, task)
    if (
        workspace.active_dataset_id != context.dataset_id
        or workspace.active_dataset_content_hash != context.dataset_content_hash
        or workspace.revision != context.workspace_revision
        or workspace.analysis_generation != context.analysis_generation
    ):
        raise StrategySetupError(
            "ActivitiesDataWorkspace Yes.V2 Changes in the sample design plan prior to its creation;"
            "Please try again based on the current version."
        )
    target_col = workspace.semantic_mapping.target_col
    semantic_hash = data_semantic_mapping_hash(workspace.semantic_mapping)
    if (
        not isinstance(target_col, str)
        or not target_col
        or target_col != context.target_col
        or target_col not in context.columns
    ):
        raise StrategySetupError(
            "V2 The policy sample is only available.DataWorkspace ."
        )
    if (
        not isinstance(workspace.active_dataset_content_hash, str)
        or not workspace.active_dataset_content_hash
        or semantic_hash != context.semantic_mapping_hash
    ):
        raise StrategySetupError(
            "ActivitiesDataWorkspace Datahash or semantic map changed;"
            "Please re-start.V2 Sample design."
        )

    inputs = draft.to_dict()["workflow_inputs"]
    fields = inputs["field_bindings"]
    maturity = inputs["maturity"]
    performance = inputs["performance_window"]
    observation = inputs["observation_window"]
    scope = (
        "strategy_development"
        if maturity["status"] == "confirmed_matured"
        and performance["status"] == "provided"
        and observation["status"] == "provided"
        else "exploration_only"
    )
    compatibility_maturity = (
        "unknown" if maturity["status"] == "unavailable" else maturity["status"]
    )
    policy = {
        **_STRATEGY_SAMPLE_V2_POLICY,
        "diagnostic_severities": dict(
            _STRATEGY_SAMPLE_V2_POLICY["diagnostic_severities"]
        ),
    }
    slots: dict[str, object] = {
        "dataset_id": workspace.active_dataset_id,
        "expected_dataset_content_hash": workspace.active_dataset_content_hash,
        "workspace_revision": workspace.revision,
        "workspace_generation": workspace.analysis_generation,
        "semantic_mapping_hash": semantic_hash,
        "target_col": target_col,
        "relationship": inputs["relationship"],
        "scope": scope,
        "policy": policy,
        "target_bad_value": inputs["target_bad_value"],
        "drop_nan_labels": bool(drop_nan_labels),
        "approval_population": inputs["approval_population"],
        "risk_population": inputs["risk_population"],
        "partitioning": inputs["partitioning"],
        "maturity": maturity,
        "performance_window": performance,
        "observation_window": observation,
        "field_bindings": fields,
        "historical_score": inputs["historical_score"],
    }
    if (
        select_sample_design_v2_template(inputs)
        == "strategy_sample_design_v2_native"
    ):
        return slots

    split_col, split_values = _strategy_sample_v2_simple_split_projection(
        inputs["partitioning"]
    )
    compatibility_columns = [
        fields.get("month_field"),
        fields.get("weight_field"),
        fields.get("loan_amount_field"),
        fields.get("overdue_amount_field"),
    ]
    present_columns = [
        str(column) for column in compatibility_columns if column is not None
    ]
    if (
        split_col == target_col
        or split_col not in context.columns
        or any(column not in context.columns for column in present_columns)
        or target_col in present_columns
        or split_col in present_columns
        or len(present_columns) != len(set(present_columns))
    ):
        raise _StrategyV2EvidenceSetupError(
            "strategy_sample_design_v2_native_source_unsupported",
            "CurrentV2 Field binding cannot be safely executed by the active data set; please adjust the duplicate or conflicting field.",
        )
    slots.update(
        {
            "compatibility_performance_window_status": performance["status"],
            "compatibility_performance_window_days": performance["days"],
            "compatibility_observation_window_status": observation["status"],
            "compatibility_observation_start": observation["start"],
            "compatibility_observation_end": observation["end"],
            "compatibility_maturity_status": compatibility_maturity,
            "compatibility_split_col": split_col,
            "compatibility_development_values": [split_values["development"]],
            "compatibility_validation_values": [split_values["validation"]],
            "compatibility_oot_values": [split_values["oot"]],
            "compatibility_month_col": fields.get("month_field"),
            "compatibility_weight_col": fields.get("weight_field"),
            "compatibility_loan_amount_col": fields.get("loan_amount_field"),
            "compatibility_overdue_amount_col": fields.get(
                "overdue_amount_field"
            ),
        }
    )
    return slots

def _strategy_sample_v2_simple_split_projection(
    partitioning: object,
) -> tuple[str, dict[str, object]]:
    if (
        not isinstance(partitioning, Mapping)
        or set(partitioning) != {"method", "selectors"}
        or partitioning.get("method") != "predicate_ast"
        or not isinstance(partitioning.get("selectors"), Mapping)
    ):
        raise _StrategyV2EvidenceSetupError(
            "strategy_sample_design_v2_native_bootstrap_required",
            "Currentcompatibility anchor Only three simple equalimetric stratifications in the same column are supported;"
            "No plans are created this time.",
        )
    selectors = partitioning["selectors"]
    if set(selectors) != {"development", "validation", "oot"}:
        raise _StrategyV2EvidenceSetupError(
            "strategy_sample_design_v2_native_bootstrap_required",
            "V2 partitioning Must contain it completelydevelopment,validation andOOT.",
        )
    columns: list[str] = []
    values: dict[str, object] = {}
    for partition in ("development", "validation", "oot"):
        predicate = selectors[partition]
        if (
            not isinstance(predicate, Mapping)
            or set(predicate) != {"op", "left", "right"}
            or predicate.get("op") != "eq"
            or not isinstance(predicate.get("left"), Mapping)
            or set(predicate["left"]) != {"column"}
            or not isinstance(predicate.get("right"), Mapping)
            or set(predicate["right"]) != {"literal"}
        ):
            raise _StrategyV2EvidenceSetupError(
                "strategy_sample_design_v2_native_bootstrap_required",
                "Currentcompatibility anchor Support onlycolumn == literal (a) Simple cut-off;"
                "No plans are created this time.",
            )
        column = predicate["left"]["column"]
        literal = predicate["right"]["literal"]
        if not isinstance(column, str) or not column or literal is None:
            raise _StrategyV2EvidenceSetupError(
                "strategy_sample_design_v2_native_bootstrap_required",
                "V2 compatibility The division and the three cut-off values must be complete.",
            )
        columns.append(column)
        values[partition] = literal
    if len(set(columns)) != 1 or len(
        {json.dumps(value, sort_keys=True, ensure_ascii=False) for value in values.values()}
    ) != 3:
        raise _StrategyV2EvidenceSetupError(
            "strategy_sample_design_v2_native_bootstrap_required",
            "V2 compatibility The cut must use three different values in the same column.",
        )
    return columns[0], values

def _latest_verified_strategy_sample_design_v2_binding(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
    artifacts: Sequence[Mapping],
):
    # TaskArtifactRepository.list_for_task is deterministic
    # ORDER BY created_at, id; the final row is therefore the latest published
    # V2 bundle, and a drifted latest bundle is never bypassed for an older one.
    supported_origins = {
        SAMPLE_DESIGN_V2_ORIGIN_TOOL,
        SAMPLE_DESIGN_V2_NATIVE_ORIGIN_TOOL,
    }
    bundles = [
        artifact
        for artifact in artifacts
        if artifact.get("kind") == SAMPLE_DESIGN_V2_BUNDLE_ARTIFACT_KIND
        and artifact.get("origin_tool") in supported_origins
    ]
    if not bundles:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_evidence_v2_sample_required",
            "No current task.StrategySampleDesign V2 Two-total sample evidence;"
            "Please, just fix it in your native language.V2 Sample design.",
        )
    newest = bundles[-1]
    provenance = newest.get("provenance")
    if not isinstance(provenance, Mapping):
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_evidence_v2_sample_invalid",
            "LatestStrategySampleDesign V2 bundle Missing completenessprovenance,"
            "No plans are created this time.",
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
            "strategy_model_evidence_v2_sample_invalid",
            "LatestStrategySampleDesign V2 membership/bundle pair Not adopted"
            "Documentation,registry,provenance or data drift review; re-confirm sample design.",
        ) from exc

def _inherit_strategy_sample_drop_nan_policy(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    *,
    context,
) -> bool:
    """Reuse the exact missing-label policy already fixed by SampleDesign.

    Candidate Lab forms do not ask the user to restate this governed sample
    policy.  Probe both boolean identities through the normal authenticated
    loader and return the one owned by the newest exact sample design.  A
    corrupt or unsupported newest native record remains fail-closed.
    """

    failures: list[StrategySetupError] = []
    for candidate_policy in (False, True):
        try:
            _latest_matching_strategy_sample_design_ref(
                runtime,
                task,
                context=context,
                drop_nan_labels=candidate_policy,
                allow_native_risk_development=True,
            )
        except StrategySetupError as exc:
            failures.append(exc)
            continue
        return candidate_policy

    for failure in failures:
        if isinstance(failure, _StrategySampleDesignPolicyMismatchError):
            continue
        if not isinstance(failure, _StrategySampleDesignRequiredError):
            raise failure
    return False

def _latest_matching_strategy_sample_design_ref(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    *,
    context,
    drop_nan_labels: bool,
    allow_native_risk_development: bool = False,
    month_col: str | None = None,
    weight_col: str | None = None,
    loan_amount_col: str | None = None,
    overdue_amount_col: str | None = None,
) -> dict[str, str]:
    """Bind downstream execution to the newest exact governed sample design.

    The language model never supplies artifact ids or hashes.  Selection is
    deterministic over task-owned registry rows and only considers designs
    whose immutable provenance already matches the active data/workspace/label
    boundary.  The selected artifact is then fully reloaded and authenticated.
    """

    if not isinstance(context.target_col, str) or not context.target_col:
        raise StrategySetupError(
            "Strategy development needs to be firstDataWorkspace ."
        )
    expected = {
        "task_id": task.id,
        "dataset_id": context.dataset_id,
        "dataset_content_hash": context.dataset_content_hash,
        "workspace_revision": context.workspace_revision,
        "workspace_generation": context.analysis_generation,
        "semantic_mapping_hash": context.semantic_mapping_hash,
        "target_col": context.target_col,
    }
    matches: list[Mapping] = []
    latest_legacy_position = -1
    latest_native_position = -1
    latest_native_authenticated = None
    latest_invalid_native_position = -1
    latest_invalid_native_cause: Exception | None = None
    latest_native_policy_mismatch_position = -1
    artifact_repository = TaskArtifactRepository(runtime.settings.db_path)
    native_read_runtime = SimpleNamespace(
        settings=runtime.settings,
        task_artifacts=artifact_repository,
    )
    try:
        artifacts = artifact_repository.list_for_task(task.id)
    except Exception as exc:
        raise StrategySetupError(
            "The strategy sample design register for the current mission cannot be read and strategy development cannot continue safely."
        ) from exc
    for position, artifact in enumerate(artifacts):
        if (
            artifact.get("kind") == SAMPLE_DESIGN_V2_BUNDLE_ARTIFACT_KIND
            and artifact.get("origin_tool")
            == SAMPLE_DESIGN_V2_NATIVE_ORIGIN_TOOL
        ):
            try:
                authenticated = (
                    authenticate_native_strategy_sample_design_v2_bundle_record(
                        native_read_runtime,
                        task_id=task.id,
                        record=artifact,
                    )
                )
            except (StrategyError, TypeError, ValueError) as exc:
                latest_invalid_native_position = position
                latest_invalid_native_cause = exc
                continue
            relation = _native_sample_design_v2_context_relation(
                authenticated.source_provenance,
                expected=expected,
                drop_nan_labels=drop_nan_labels,
            )
            if relation == "invalid":
                latest_invalid_native_position = position
                latest_invalid_native_cause = None
                continue
            if relation == "policy_mismatch":
                latest_native_policy_mismatch_position = position
                continue
            if relation == "current":
                latest_native_position = position
                latest_native_authenticated = authenticated
            continue
        provenance = artifact.get("provenance")
        if (
            artifact.get("kind") != SAMPLE_DESIGN_ARTIFACT_KIND
            or artifact.get("origin_tool") != SAMPLE_DESIGN_ORIGIN_TOOL
            or not isinstance(provenance, Mapping)
            or any(provenance.get(field) != value for field, value in expected.items())
        ):
            continue
        request = provenance.get("request")
        if (
            not isinstance(request, Mapping)
            or request.get("drop_nan_labels") is not bool(drop_nan_labels)
        ):
            continue
        matches.append(artifact)
        latest_legacy_position = position
    latest_valid_position = max(
        latest_legacy_position,
        latest_native_position,
    )
    latest_blocking_native_position = max(
        latest_invalid_native_position,
        latest_native_policy_mismatch_position,
        *(() if allow_native_risk_development else (latest_native_position,)),
    )
    blocking_boundary = (
        latest_valid_position
        if allow_native_risk_development
        else latest_legacy_position
    )
    if latest_blocking_native_position > blocking_boundary:
        if (
            allow_native_risk_development
            and latest_native_policy_mismatch_position
            == latest_blocking_native_position
        ):
            raise _StrategySampleDesignPolicyMismatchError(
                "Current latest nativeStrategySampleDesign V2 ..and the current round of the missing tag policy"
                "Implementation calibres vary; no retreat to older samples."
            )
        error = _StrategyV2EvidenceSetupError(
            "strategy_sample_design_v2_native_source_unsupported",
            "Recent information on current execution calibresStrategySampleDesign V2 From the original"
            "orregistry,Documentation,provenance/source identity "
            "Unable to authenticate; this downstreamWorkflow It's not gonna be quieter back to the old ones.V1 "
            "compatibility Sample.",
        )
        if (
            latest_invalid_native_position
            == latest_blocking_native_position
            and latest_invalid_native_cause is not None
        ):
            raise error from latest_invalid_native_cause
        raise error
    select_native = (
        allow_native_risk_development
        and latest_native_position > latest_legacy_position
    )
    if not select_native and not matches:
        raise _StrategySampleDesignRequiredError(
            "Current activity data and label calibres do not have a sophisticated and implementable sample design of strategies."
            "Please indicate the values of the bad samples, the performance windows, the observation windows, the maturity and the severable cut in the natural language."
            "Jean.Risk Studio Solidified sample design."
        )

    if select_native:
        if latest_native_authenticated is None:
            raise StrategySetupError(
                "Current NativeStrategySampleDesign V2 The selection is incomplete,"
                "Please re-establish the sample design before implementation."
            )
        reference = {
            "artifact_id": latest_native_authenticated.artifact_id,
            "artifact_content_hash": (
                latest_native_authenticated.artifact_content_hash
            ),
            "sample_design_id": latest_native_authenticated.provenance[
                "sample_design_id"
            ],
            "sample_design_content_hash": (
                latest_native_authenticated.provenance[
                    "sample_design_content_hash"
                ]
            ),
            "partition": "risk/development",
        }
    else:
        artifact = matches[-1]
        provenance = artifact["provenance"]
        reference = {
            "artifact_id": artifact.get("id"),
            "artifact_content_hash": artifact.get("content_hash"),
            "sample_design_id": provenance.get("sample_design_id"),
            "sample_design_content_hash": provenance.get(
                "sample_design_content_hash"
            ),
            "partition": "development",
        }
    backend = DataBackend(runtime.settings.datasets_dir)
    read_runtime = SimpleNamespace(
        settings=runtime.settings,
        backend=backend,
        registry=DatasetRegistry(
            DatasetRepository(runtime.settings.db_path),
            backend,
            runtime.settings.datasets_dir,
        ),
        task_artifacts=TaskArtifactRepository(runtime.settings.db_path),
    )
    try:
        loader = (
            load_strategy_risk_development_execution_binding
            if allow_native_risk_development
            else load_strategy_sample_design_execution_binding
        )
        binding = loader(
            read_runtime,
            task_id=task.id,
            sample_design_ref=reference,
            dataset_id=context.dataset_id,
            dataset_content_hash=context.dataset_content_hash,
            workspace_revision=context.workspace_revision,
            workspace_generation=context.analysis_generation,
            semantic_mapping_hash=context.semantic_mapping_hash,
            target_col=context.target_col,
            drop_nan_labels=bool(drop_nan_labels),
            month_col=month_col,
            weight_col=weight_col,
            loan_amount_col=loan_amount_col,
            overdue_amount_col=overdue_amount_col,
        )
    except StrategySampleDesignScopeIneligibleError as exc:
        raise _StrategyV2EvidenceSetupError(
            exc.code,
            "Current latest nativeStrategySampleDesign V2 It's passed.task,registry,"
            "Documentation,hash,provenance/source identity and activitiesDataWorkspace "
            f"Review, butscope Yes`{exc.scope}`,Not for single variable or other policy development"
            "Implementation. Reconfirm sample design: confirm maturity and performance windows and provide observation windows;"
            "The platform won't putexploration-only The evidence is either silently upgraded or back to the old.V1 Sample.",
        ) from exc
    except StrategyError as exc:
        raise StrategySetupError(
            "The current latest strategy sample design has not been verified through completeness, maturity or field calibre;"
            "Please re-establish the sample design before implementation."
        ) from exc
    return binding.to_ref_dict()

def _native_sample_design_v2_context_relation(
    source_provenance: Mapping[str, object],
    *,
    expected: Mapping[str, object],
    drop_nan_labels: bool,
) -> str:
    """Classify one already-authenticated native source against execution."""

    if source_provenance.get("task_id") != expected["task_id"]:
        return "invalid"
    if source_provenance.get("dataset_id") != expected["dataset_id"]:
        return "other"
    if (
        source_provenance.get("dataset_content_hash")
        != expected["dataset_content_hash"]
    ):
        # Dataset ids are immutable; a different hash under the same id is
        # corruption, not another legitimate context.
        return "invalid"
    workspace_identity = (
        source_provenance.get("workspace_revision"),
        source_provenance.get("workspace_generation"),
    )
    expected_workspace_identity = (
        expected["workspace_revision"],
        expected["workspace_generation"],
    )
    if workspace_identity != expected_workspace_identity:
        return "other"
    if (
        source_provenance.get("semantic_mapping_hash")
        != expected["semantic_mapping_hash"]
        or source_provenance.get("target_col") != expected["target_col"]
    ):
        return "invalid"
    if source_provenance.get("drop_nan_labels") is not bool(drop_nan_labels):
        return "policy_mismatch"
    return "current"

def _strategy_sample_design_dataset_context(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
):
    """Resolve the sample-design source only from confirmed workspace state."""

    _require_strategy_sample_design_workspace(runtime, task)
    backend, registry = _modeling_data_runtime(runtime.settings)
    context = build_strategy_dataset_context(
        registry,
        backend,
        task.id,
        task.source_dir,
        target_col=None,
        require_target=True,
    )
    _validate_strategy_sample_design_target(
        registry,
        backend,
        dataset_id=context.dataset_id,
        target_col=context.target_col,
    )
    return context

def _strategy_sample_design_dataset_preview(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
):
    """Preview the exact active sample and its confirmed workspace target."""

    _ensure_strategy_sample_design_active_workspace(runtime, task)
    _require_strategy_sample_design_workspace(runtime, task)
    backend, registry = _modeling_data_runtime(runtime.settings)
    preview = preview_strategy_dataset_context(
        registry,
        backend,
        task.id,
        task.source_dir,
        target_col=None,
    )
    _validate_strategy_sample_design_target(
        registry,
        backend,
        dataset_id=preview.dataset_id,
        target_col=preview.target_col,
    )
    return preview

def _confirm_manual_sample_design_time_semantics(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    *,
    draft: StandardWorkflowRequestDraft,
    preview,
) -> None:
    """Persist the date role explicitly confirmed by the Candidate Lab form."""

    bindings = draft.workflow_inputs.get("field_bindings")
    time_field = (
        bindings.get("time_field")
        if isinstance(bindings, Mapping)
        else None
    )
    if time_field is None:
        return
    if (
        not isinstance(time_field, str)
        or not time_field
        or preview is None
        or time_field not in tuple(preview.columns)
    ):
        raise StrategySetupError(
            "Time fields designed for double-population samples are not in the current active sample, and re-select."
        )

    repository = DataWorkspaceRepository(runtime.settings.db_path)
    try:
        snapshot = repository.get_or_default(task.id)
        if (
            snapshot.active_dataset_id is None
            or snapshot.active_dataset_content_hash is None
            or not snapshot.semantic_mapping.target_col
        ):
            raise StrategySetupError(
                "The design of the double-population sample requires a defined activity sample and binary target column."
            )
        if time_field == snapshot.semantic_mapping.target_col:
            raise StrategySetupError(
                "The time field designed for the two-population sample cannot be the same as the target column."
            )
        roles = dict(snapshot.semantic_mapping.field_roles)
        roles[time_field] = "date"
        repository.save(
            task.id,
            DataWorkspaceDraft(
                active_dataset_id=snapshot.active_dataset_id,
                active_dataset_content_hash=(
                    snapshot.active_dataset_content_hash
                ),
                page=snapshot.page,
                selected_field=snapshot.selected_field,
                semantic_mapping=DataSemanticMapping(
                    target_col=snapshot.semantic_mapping.target_col,
                    field_roles=roles,
                    business_names=(
                        snapshot.semantic_mapping.business_names
                    ),
                ),
            ),
            expected_revision=snapshot.revision,
            audit={
                "actor": "user:strategy-candidate-lab",
                "detail": {
                    "reason": (
                        "confirm explicit sample-design time field "
                        "with date semantic role"
                    ),
                    "time_field": time_field,
                },
            },
        )
    except StrategySetupError:
        raise
    except (
        DataWorkspaceDataError,
        DataWorkspaceDatasetNotFound,
        DataWorkspaceRevisionConflict,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise StrategySetupError(
            "Time field confirmation period for double-population sample designDataWorkspace The change,"
            "Please refresh and try again."
        ) from exc

def _ensure_strategy_sample_design_active_workspace(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
) -> None:
    """Atomically bind one unambiguous sample and binary target on a fresh task."""

    repository = DataWorkspaceRepository(runtime.settings.db_path)
    try:
        snapshot = repository.get_or_default(task.id)
    except (DataWorkspaceDataError, KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "Policy sample design requires effective and identified activitiesDataWorkspace."
        ) from exc
    if snapshot.active_dataset_id is not None:
        if not snapshot.semantic_mapping.target_col:
            raise StrategySetupError(
                "The policy sample design requires firstDataWorkspace Confirms the binary goal column."
            )
        return

    backend, registry = _modeling_data_runtime(runtime.settings)
    registered = [
        dataset
        for dataset in registry.list_for_task(task.id)
        if str(dataset.task_id) == task.id
        and dataset.role in {"sample", "strategy_sample"}
    ]
    if len(registered) > 1:
        raise StrategySetupError(
            "The strategy sample design requires a clear sample of activities; there are currently multiple registered data sets, and the data set is not available."
            "Please be there first.DataWorkspace Select and save this sample."
        )

    try:
        preview = _strategy_dataset_preview(runtime, task)
    except StrategySetupError as exc:
        raise StrategySetupError(
            "The policy sample design requires firstDataWorkspace Select the only active sample:"
            f"{exc}"
        ) from exc
    if not preview.target_col:
        raise StrategySetupError(
            "The only two-fold target column that can be identified for the design of the strategy is confirmed.target_col."
        )
    try:
        context = _strategy_dataset_context(runtime, task, require_target=True)
    except StrategySetupError as exc:
        raise StrategySetupError(
            "Policy sample design cannot be from the currentDataWorkspace Candidatures to establish stable binding:"
            f"{exc}"
        ) from exc
    registered = [
        dataset
        for dataset in registry.list_for_task(task.id)
        if str(dataset.task_id) == task.id
        and dataset.role in {"sample", "strategy_sample"}
    ]
    if (
        len(registered) != 1
        or registered[0].id != context.dataset_id
        or (
            preview.dataset_id is not None
            and preview.dataset_id != context.dataset_id
        )
        or tuple(preview.columns) != tuple(context.columns)
        or preview.target_col != context.target_col
    ):
        raise StrategySetupError(
            "(b) The strategy sample design requires a clear and stable sample of activities;"
            "Please first specify the datasets that are currently available or in progressDataWorkspace Clear choice."
        )
    if (
        not isinstance(context.dataset_content_hash, str)
        or not context.dataset_content_hash
        or not context.target_col
    ):
        raise StrategySetupError(
            "The policy sample design cannot bind the sample Hash or binary target column. Please confirm the data andtarget_col."
        )
    _validate_strategy_sample_design_target(
        registry,
        backend,
        dataset_id=context.dataset_id,
        target_col=context.target_col,
    )

    try:
        pinned_dataset = registry.pin_authenticated_snapshot(context.dataset_id)
        if pinned_dataset.content_hash != context.dataset_content_hash:
            raise StrategySetupError(
                "The data identity of the policy sample design changes before binding, and please reconfirm the sample."
            )
        repository.save_initial_binding(
            task.id,
            DataWorkspaceDraft(
                active_dataset_id=context.dataset_id,
                active_dataset_content_hash=context.dataset_content_hash,
                semantic_mapping=DataSemanticMapping(
                    target_col=context.target_col,
                    field_roles={context.target_col: "target"},
                ),
            ),
            expected_revision=snapshot.revision,
            audit={
                "actor": "agent:strategy-sample-design",
                "detail": {
                    "reason": (
                        "atomically bind sole task sample and target "
                        "for strategy sample design"
                    )
                },
            },
        )
    except (
        DataWorkspaceDataError,
        DataWorkspaceDatasetNotFound,
        DataWorkspaceRevisionConflict,
        DatasetContentDriftError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise StrategySetupError(
            "The data fields of the strategy sampled changed before the plan was created."
            "Please reconfirm the sample and target column of the activity."
        ) from exc

def _validate_strategy_sample_design_target(
    registry,
    backend,
    *,
    dataset_id: object,
    target_col: object,
) -> tuple[int, int]:
    """Accept only native numeric 0/1 plus genuine null labels.

    Numeric strings are intentionally rejected even when pandas could coerce
    them. Infinite values and other finite numbers are hard errors, never NaN
    confirmation candidates.
    """

    if not isinstance(dataset_id, str) or not dataset_id:
        raise StrategySetupError(
            "The policy sample design must bind the registered activity data set before the target column can be verified."
        )
    if not isinstance(target_col, str) or not target_col:
        raise StrategySetupError("The policy sample design requires a confirmed binary target column.")
    try:
        path = registry.resolve_path(dataset_id)
        frame = backend.read_frame(path, columns=[target_col])
        target = frame[target_col]
    except Exception as exc:
        raise StrategySetupError(
            f"Target column`{target_col}` Could not close temporary folder: %s"
        ) from exc
    dtype_kind = getattr(target.dtype, "kind", None)
    if dtype_kind not in {"i", "u", "f"}:
        raise StrategySetupError(
            f"Target column`{target_col}` Must be a value 0/1 or real empty values;"
            "String'0'/'1',Booleans and other codes are not accepted."
        )
    null_mask = target.isna()
    for value in target.loc[~null_mask].tolist():
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise StrategySetupError(
                f"Target column`{target_col}` Must be a value 0/1 or real empty value."
            ) from exc
        if not math.isfinite(number) or number not in {0.0, 1.0}:
            raise StrategySetupError(
                f"Target column`{target_col}` Must be a value 0/1 or real empty values;"
                "inf,-inf and 0/1 Values other than those that are not allowed into the sample design."
            )
    return int(len(target)), int(null_mask.sum())

def _require_strategy_sample_design_workspace(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
):
    try:
        snapshot = DataWorkspaceRepository(runtime.settings.db_path).get_or_default(
            task.id
        )
    except (DataWorkspaceDataError, KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "Policy sample design requires effective and identified activitiesDataWorkspace."
        ) from exc
    if snapshot.active_dataset_id is None:
        raise StrategySetupError(
            "The policy sample design requires firstDataWorkspace Select and save the active data set."
        )
    if not snapshot.semantic_mapping.target_col:
        raise StrategySetupError(
            "The policy sample design requires firstDataWorkspace Confirms the binary goal column."
        )
    return snapshot

def _require_strategy_pool_impact_workspace(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
):
    try:
        snapshot = DataWorkspaceRepository(runtime.settings.db_path).get_or_default(
            task.id
        )
    except (DataWorkspaceDataError, KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "Strategy Pool Impact measurement requires effective activitiesDataWorkspace."
        ) from exc
    if snapshot.active_dataset_id is None:
        raise StrategySetupError(
            "Strategy Pool Impact measurement requires firstDataWorkspace Selects the active data set."
        )
    if not snapshot.semantic_mapping.target_col:
        raise StrategySetupError(
            "Strategy Pool Impact measurement requires firstDataWorkspace Confirms the binary goal column."
        )
    return snapshot

def _append_strategy_nan_label_clarification(
    repo: TaskRepository,
    task: TaskRecord,
    state: dict,
) -> dict:
    n_nan = int(state.get("n_nan") or 0)
    n_total = int(state.get("n_total") or 0)
    target_col = str(state.get("target_col") or "")
    payload = state.get("draft")
    is_pool_impact = (
        isinstance(payload, Mapping)
        and payload.get("workflow") in _STRATEGY_POOL_MEASUREMENT_WORKFLOWS
    )
    is_sample_design = (
        isinstance(payload, Mapping)
        and payload.get("workflow")
        in {"strategy_sample_design", "strategy_sample_design_v2"}
    )
    if is_pool_impact or is_sample_design:
        missing_description = "Empty Tab" if is_sample_design else "Empty or non-limited labels"
        retained_statistics = (
            "Overall, volume and weighting statistics" if is_sample_design else "General, action and monetary statistics"
        )
        message = (
            f"Target column`{target_col}` Yes.{n_nan}/{n_total} Okay.{missing_description}."
            f"These samples will remain in{retained_statistics}, only from bad debts/(a) Exclusion from the risk factor denominator;"
            "No plans have been created for this time, and the platform will not default on the calibre."
            "If so, please reply explicitly \"confirm that the empty labels are excluded and continue only from the risk denominator\";"
            "The response to this question is \"confirmation\" and it will not be implemented."
        )
    else:
        message = (
            f"Target column`{target_col}` Yes.{n_nan}/{n_total} Rows are empty or not limited."
            "This time, no plan has been created and the platform will not be discarded by default."
            "If so, please reply explicitly \"Certify that the drop of the empty label continues\""
            "The response to this question is \"confirmation\" and it will not be implemented."
        )
    repo.add_agent_message(
        task.id,
        role="assistant",
        stage="chat",
        content=message,
        metadata={
            "intent": "strategy_drop_nan_labels_confirmation",
            "kind": "clarification",
            "code": "strategy_drop_nan_labels_confirmation_required",
            "fields": ["drop_nan_labels"],
            _STRATEGY_NAN_LABEL_META_KEY: state,
        },
    )
    return {
        "task_id": task.id,
        "status": "clarification_required",
        "code": "strategy_drop_nan_labels_confirmation_required",
        "fields": ["drop_nan_labels"],
        "label_quality": {
            "target_col": target_col,
            "n_total": n_total,
            "n_nan": n_nan,
        },
        "messages": repo.list_agent_messages(task.id),
    }

def _repeat_strategy_nan_label_clarification(
    repo: TaskRepository,
    task: TaskRecord,
    state: dict,
) -> dict:
    return _append_strategy_nan_label_clarification(repo, task, dict(state))

def _resume_strategy_after_nan_label_confirmation(
    runtime: DriverTurnRuntime,
    repo: TaskRepository,
    task: TaskRecord,
    state: dict,
) -> dict:
    if (
        _active_plan(runtime.plan_repo, task.id) is not None
        or latest_open_gate(repo.list_agent_messages(task.id)) is not None
    ):
        return _strategy_request_clarification_response(
            repo,
            task,
            code="strategy_request_stale_confirmation",
            message="The status of the mission has changed and the empty tag processing confirmation is invalid; please restart when the current plan is completed.",
        )
    payload = state.get("draft")
    if not isinstance(payload, dict):
        return _strategy_request_clarification_response(
            repo,
            task,
            code="strategy_request_invalidated",
            message="Empty tag confirms that the calibrated strategy is missing. Please recapitulate the strategy request.",
        )
    is_pool_impact = payload.get("workflow") in _STRATEGY_POOL_MEASUREMENT_WORKFLOWS
    is_sample_design = payload.get("workflow") in {
        "strategy_sample_design",
        "strategy_sample_design_v2",
    }
    expected_pool_binding = None
    if is_pool_impact:
        expected_pool_binding = state.get("pool_binding")
        if not isinstance(expected_pool_binding, Mapping):
            return _strategy_request_clarification_response(
                repo,
                task,
                code="strategy_pool_context_changed",
                message=(
                    "Old empty tag confirmed not boundStrategy Pool revision/hash;"
                    "To avoid misusing the currentPool,Please re-launch impact measurements."
                ),
            )
        try:
            _pool, current_pool_binding = _strategy_pool_impact_pool_binding(
                runtime,
                task,
                str(expected_pool_binding.get("strategy_type") or ""),
            )
        except StrategySetupError as exc:
            return _strategy_request_clarification_response(
                repo,
                task,
                code="strategy_pool_context_changed",
                message=str(exc),
            )
        if dict(expected_pool_binding) != current_pool_binding:
            return _strategy_request_clarification_response(
                repo,
                task,
                code="strategy_pool_context_changed",
                message=(
                    "Strategy Pool The time frame for the empty tag confirmation changed; the old confirmation was not implemented, and the time frame was set for the release of the tag."
                    "Please base on currentPool Re-launching impact measurements."
                ),
            )
    try:
        preview = (
            _strategy_pool_impact_dataset_preview(runtime, task)
            if is_pool_impact
            else (
                _strategy_sample_design_dataset_preview(runtime, task)
                if is_sample_design
                else _strategy_dataset_preview(runtime, task)
            )
        )
    except StrategySetupError as exc:
        return _strategy_request_clarification_response(
            repo,
            task,
            code="strategy_dataset_context_required",
            message=str(exc),
        )
    expected_identity = state.get("dataset_identity")
    if (
        not isinstance(expected_identity, dict)
        or preview.identity != expected_identity
        or preview.dataset_id != state.get("dataset_id")
        or preview.target_col != state.get("target_col")
    ):
        return _strategy_request_clarification_response(
            repo,
            task,
            code="strategy_dataset_context_changed",
            message="The strategy sample or target column has changed; empty tag confirmed not implemented, re-describe the strategy request.",
        )
    compilation = validate_strategy_request(
        payload,
        allowed_columns=_strategy_request_allowed_columns(preview),
        target_col=preview.target_col,
        allow_legacy_replay=True,
    )
    if compilation.draft is None:
        return _strategy_request_clarification_response(
            repo,
            task,
            code="strategy_request_invalidated",
            message=compilation.clarification or "The strategic calibration failed, please recapitulate.",
        )
    preflight = _strategy_request_preflight(runtime, task, compilation.draft)
    if preflight is not None:
        code, message = preflight
        return _strategy_request_clarification_response(
            repo,
            task,
            code=code,
            message=message,
        )
    return _prepare_and_run_validated_strategy_request(
        runtime,
        repo,
        task,
        compilation.draft,
        preview=preview,
        auto_start=True,
        drop_nan_labels=True,
        expected_pool_binding=expected_pool_binding,
    )

def _latest_strategy_nan_label_confirmation(
    conversation: list[dict],
) -> dict | None:
    last_assistant = next(
        (
            message
            for message in reversed(conversation)
            if message.get("role") == "assistant"
        ),
        None,
    )
    if last_assistant is None:
        return None
    state = (last_assistant.get("metadata") or {}).get(_STRATEGY_NAN_LABEL_META_KEY)
    return state if isinstance(state, dict) else None
