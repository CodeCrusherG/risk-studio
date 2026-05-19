"""strategy_candidates driver-turn handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import hashlib
import hmac
import json
from pathlib import Path
import re
import sqlite3
from types import SimpleNamespace
from marvis.agent.strategy_setup import StrategySetupError
from marvis.agent.strategy_request_compiler import CompiledStrategyRequestDraft, StandardWorkflowRequestDraft, StrategyRequestDraft
from marvis.agent.strategy_workflows import StrategyWorkflowValidationError
from marvis.data.errors import DatasetContentDriftError
from marvis.data.workspace import DataSemanticMapping, DataWorkspaceDraft, data_semantic_mapping_hash
from marvis.repositories.strategy import StrategyRepository
from marvis.domain import TaskRecord
from marvis.files import sha256_file
from marvis.packs.strategy.automatic_tree_leaf_fragment import AUTOMATIC_TREE_LEAF_FRAGMENT_ARTIFACT_KIND, AUTOMATIC_TREE_LEAF_FRAGMENT_ORIGIN_TOOL, AUTOMATIC_TREE_SOURCE_ARTIFACT_KIND, AUTOMATIC_TREE_SOURCE_ARTIFACT_ORIGIN_TOOL
from marvis.packs.strategy.automatic_tree_leaf_tools import load_verified_automatic_tree_leaf_selection_artifact_on_connection, load_verified_automatic_tree_source_artifact_on_connection
from marvis.packs.strategy.interactive_tree_frontier_selection import INTERACTIVE_TREE_FRONTIER_SELECTION_ARTIFACT_KIND, INTERACTIVE_TREE_FRONTIER_SELECTION_ARTIFACT_SCHEMA_VERSION, INTERACTIVE_TREE_FRONTIER_SELECTION_ARTIFACT_SCHEMA_VERSION_V2, INTERACTIVE_TREE_FRONTIER_SELECTION_ORIGIN_TOOL
from marvis.packs.strategy.interactive_tree_frontier_group_selection import INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ARTIFACT_KIND, INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ARTIFACT_SCHEMA_VERSION, INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ARTIFACT_SCHEMA_VERSION_V2, INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ORIGIN_TOOL, interactive_tree_frontier_group_selection_to_verified_candidate_fragment
from marvis.packs.strategy.interactive_tree_frontier_group_tools import load_verified_interactive_tree_frontier_group_selection_artifact_on_connection
from marvis.packs.strategy.interactive_tree_frontier_tools import load_verified_interactive_tree_frontier_selection_artifact_on_connection
from marvis.packs.strategy.interactive_tree_revision import interactive_tree_topology_evidence
from marvis.packs.strategy.interactive_tree_tools import MAX_INTERACTIVE_TREE_REVISION_ANCESTRY_BYTES, _RevisionReadBudget, _resolve_revision_source_on_connection, load_verified_interactive_tree_revision
from marvis.packs.strategy.voting_candidate_fragment import VOTING_CANDIDATE_ARTIFACT_KIND, VOTING_CANDIDATE_ORIGIN_TOOL
from marvis.packs.strategy.voting_candidate_tools import load_verified_voting_candidate_artifact_on_connection
from marvis.packs.strategy.voting_candidate_search_tools import resolve_voting_candidate_search_selection, resolve_voting_candidate_search_inputs
from marvis.packs.strategy.cross_matrix_candidate_tools import ASSET_ARTIFACT_KIND as CROSS_MATRIX_SOURCE_ARTIFACT_KIND, ASSET_ARTIFACT_SCHEMA_VERSION as CROSS_MATRIX_SOURCE_ARTIFACT_SCHEMA_VERSION, ORIGIN_TOOL as CROSS_MATRIX_SOURCE_ARTIFACT_ORIGIN_TOOL
from marvis.packs.strategy.cross_candidate_search_tools import resolve_cross_candidate_search_pair
from marvis.packs.strategy.cross_rule_search_tools import resolve_cross_rule_search_rule
from marvis.packs.strategy.cross_matrix_cell_selection import CROSS_MATRIX_CELL_SELECTION_ARTIFACT_KIND, CROSS_MATRIX_CELL_SELECTION_ARTIFACT_SCHEMA_VERSION, CROSS_MATRIX_CELL_SELECTION_ORIGIN_TOOL
from marvis.packs.strategy.cross_matrix_cell_selection_tools import load_verified_cross_matrix_cell_selection_artifact_on_connection, load_verified_cross_matrix_source_artifact_on_connection
from marvis.packs.strategy.errors import StrategyError
from marvis.packs.strategy.dsl_delivery import MAX_EQUIVALENCE_ROWS
from marvis.packs.modeling.errors import ModelingError
from marvis.packs.modeling.evidence import RAW_SCORE_PRODUCT
from marvis.packs.modeling.evidence_tools import build_training_evidence_ref
from marvis.packs.modeling.score_evidence import MODEL_SCORE_EVIDENCE_ARTIFACT_KIND, MODEL_SCORE_VECTOR_ARTIFACT_KIND
from marvis.packs.modeling.score_evidence_tools import MATERIALIZE_MODEL_SCORE_EVIDENCE_V2_ORIGIN_TOOL, load_historical_model_score_evidence_artifacts, load_model_score_evidence_artifacts
from marvis.packs.strategy.model_score_comparison_tools import model_score_comparison_registry_snapshot_token
from marvis.packs.strategy.model_score_evidence_adapter import ModelScoreEvidenceComparisonError, build_model_score_comparison
from marvis.packs.strategy.model_evidence import MAX_MODEL_EVIDENCE
from marvis.packs.strategy.candidate_fragment import verified_fragment_pool_parts
from marvis.packs.strategy.scorecard_candidate import SCORECARD_BAND_ASSET_ARTIFACT_KIND, SCORECARD_BAND_ASSET_ARTIFACT_SCHEMA_VERSION, SCORECARD_BAND_ASSET_ORIGIN_TOOL, SCORECARD_CUTOFF_SELECTION_ARTIFACT_KIND, SCORECARD_CUTOFF_SELECTION_ARTIFACT_SCHEMA_VERSION, SCORECARD_CUTOFF_SELECTION_ORIGIN_TOOL, scorecard_cutoff_selection_to_verified_candidate_fragment
from marvis.packs.strategy.scorecard_candidate_tools import load_scorecard_band_asset_artifact, load_scorecard_cutoff_selection_artifact
from marvis.packs.strategy.model_evidence_tools import _MAX_UNIVARIATE_SOURCES, _load_candidate_sources, _validate_inputs as _validate_model_evidence_v2_inputs, derive_strategy_model_evidence_candidate_execution_ref
from marvis.packs.strategy.pool_tools import load_current_strategy_candidate_pool_artifact
from marvis.packs.strategy.pool_validation_tools import load_strategy_pool_validation_artifacts, select_latest_strategy_pool_validation_refs
from marvis.packs.strategy.pool_requirement_resolver import resolve_pool_requirements
from marvis.packs.strategy.project_context import strategy_project_context_structured_request_sha256
from marvis.packs.strategy.project_context_tools import load_current_strategy_project_context_artifact
from marvis.packs.strategy.report_bundle_adapters import build_strategy_report_bundle_source_inputs
from marvis.packs.strategy.sample_design_execution import StrategyRiskDevelopmentRef
from marvis.packs.strategy.sample_design_v2_tools import SAMPLE_DESIGN_V2_BUNDLE_ARTIFACT_KIND, SAMPLE_DESIGN_V2_MEMBERSHIP_ARTIFACT_KIND, SAMPLE_DESIGN_V2_ORIGIN_TOOL
from marvis.repositories.task_artifacts import TaskArtifactRepository
from marvis.repositories.strategy_pool import ABSENT_POOL_REVISION, ABSENT_POOL_SNAPSHOT_HASH, StrategyCandidatePoolRepository, strategy_pool_snapshot_hash
from marvis.repositories.strategy_project_context import StrategyProjectContextDataError, StrategyProjectContextRepository
from marvis.repositories.strategy_reports import StrategyReportRepository
from marvis.packs.strategy.candidate_asset import canonical_candidate_asset_json, validate_candidate_asset
from marvis.packs.strategy.candidate_asset_tools import load_verified_candidate_refinement_source
from marvis.packs.strategy.candidate_stability_tools import resolve_candidate_monthly_stability_inputs
from marvis.repositories.data_workspace import DataWorkspaceDataError, DataWorkspaceDatasetNotFound, DataWorkspaceRepository, DataWorkspaceRevisionConflict

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import DriverTurnRuntime
    from . import _STRATEGY_V2_ARTIFACT_ERRORS
    from . import _StrategyV2EvidenceSetupError
    from . import _latest_matching_strategy_sample_design_ref
    from . import _latest_verified_strategy_sample_design_v2_binding
    from . import _modeling_data_runtime
    from . import _strategy_dataset_context
    from . import _strategy_dataset_preview
    from . import _strategy_dsl_delivery_strategy_ref
    from . import _strategy_impact_cube_current_strategy_ref
    from . import _strategy_impact_cube_dimensions
    from . import _strategy_impact_cube_economics
    from . import _strategy_impact_cube_partitions
    from . import _strategy_impact_cube_registry_token
    from . import _strategy_pool_complete_rule_order
    from . import _strategy_pool_entries
    from . import _strategy_pool_impact_column
    from . import _strategy_pool_impact_pool_binding
    from . import _strategy_pool_rule_id
    from . import _strategy_report_current_pool_binding
    from . import _strategy_report_identity
    from . import _strategy_report_latest_candidate_stability_binding
    from . import _strategy_report_latest_cross_rule_search_binding
    from . import _strategy_report_latest_cross_search_binding
    from . import _strategy_report_latest_impact_cube_binding
    from . import _strategy_report_latest_pool_impact_binding
    from . import _strategy_report_latest_pool_stability_binding
    from . import _strategy_report_latest_sample_binding
    from . import _strategy_report_latest_voting_search_binding
    from . import _strategy_report_optional_model_evidence
    from . import _strategy_report_optional_score_evidence
    from . import _strategy_report_optional_training_evidence
    from . import _strategy_report_read_runtime
    from . import _strategy_report_requested_pool_type
    from . import _strategy_report_sample_ref
    from . import _strategy_v2_artifact_snapshot
    from . import _strategy_v2_read_runtime
    from . import _strategy_v2_registry_token

def _bind_univariate_dataset_evidence(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    workflow_inputs: Mapping[str, object],
    *,
    context,
    drop_nan_labels: bool,
) -> dict[str, object]:
    """Bind the authenticated workspace and mature sample for fresh analysis."""

    if context is None:
        raise StrategyWorkflowValidationError(
            "The current policy operation requires the context of the task.",
            code="strategy_dataset_required",
        )
    binding: dict[str, object] = {
        "dataset_id": getattr(context, "dataset_id", None),
        "expected_content_hash": getattr(
            context,
            "dataset_content_hash",
            None,
        ),
        "workspace_revision": getattr(context, "workspace_revision", None),
        "analysis_generation": getattr(context, "analysis_generation", None),
        "semantic_mapping_hash": getattr(
            context,
            "semantic_mapping_hash",
            None,
        ),
        "target_col": getattr(context, "target_col", None),
    }
    if (
        not isinstance(binding["expected_content_hash"], str)
        or not isinstance(binding["semantic_mapping_hash"], str)
        or isinstance(binding["workspace_revision"], bool)
        or not isinstance(binding["workspace_revision"], int)
        or isinstance(binding["analysis_generation"], bool)
        or not isinstance(binding["analysis_generation"], int)
    ):
        raise StrategySetupError(
            "The policy candidate analysis cannot bind the current data workspace. Please re-select the active dataset."
        )
    binding["sample_design_ref"] = _latest_matching_strategy_sample_design_ref(
        runtime,
        task,
        context=context,
        drop_nan_labels=drop_nan_labels,
        allow_native_risk_development=True,
        weight_col=workflow_inputs.get("sample_weight_col"),
        loan_amount_col=workflow_inputs.get("loan_amount_col"),
        overdue_amount_col=workflow_inputs.get("overdue_amount_col"),
    )
    return binding

def _platform_evidence_only(
    workflow_id: str,
    bound_slots: Mapping[str, object],
    *,
    expected_user_slots: Mapping[str, object],
) -> dict[str, object]:
    """Verify resolver echoes without letting them override canonical slots."""

    mismatched = sorted(
        key
        for key, expected in expected_user_slots.items()
        if key not in bound_slots or bound_slots[key] != expected
    )
    if mismatched:
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Platform binding andcanonical Userslots Inconsistencies:"
            + ",".join(mismatched)
            + ".",
            code="strategy_workflow_evidence_conflict",
            fields=mismatched,
        )
    return {
        str(key): value
        for key, value in bound_slots.items()
        if key not in expected_user_slots
    }

def _bind_candidate_monthly_stability_evidence(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    workflow_inputs: Mapping[str, object],
) -> dict[str, object]:
    """Resolve a user pointer and return only platform-owned evidence."""

    if set(workflow_inputs) == {"asset_id"}:
        user_pointer: dict[str, object] = {
            "source_kind": "univariate_asset",
            "asset_id": workflow_inputs["asset_id"],
        }
    elif set(workflow_inputs) == {"strategy_type", "entry_id"}:
        user_pointer = {
            "source_kind": "pool_entry",
            "strategy_type": workflow_inputs["strategy_type"],
            "entry_id": workflow_inputs["entry_id"],
        }
    else:  # pragma: no cover - compiler validation owns this shape
        raise StrategySetupError(
            "(a) The candidate must provide the only asset for the month-to-month stability of the candidate, orPool Type and Uniqueentry."
        )
    try:
        resolved = resolve_candidate_monthly_stability_inputs(
            _strategy_v2_read_runtime(runtime),
            task_id=task.id,
            user_pointer=user_pointer,
        )
    except (
        StrategyError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        *_STRATEGY_V2_ARTIFACT_ERRORS,
    ) as exc:
        message = str(exc)
        if "month field" in message:
            raise StrategySetupError(
                "It's under governance.StrategySampleDesign There are no single and non-empty monthly fields;"
                "Please supplement and re-establish.month Caliber, recalculation of monthly stability of candidate."
            ) from exc
        raise StrategySetupError(
            "Candidates are steady from sources, activities.workspace,SampleDesign orlineage "
            f"Not fully certified:{message}"
        ) from exc
    expected_user_slots = user_pointer
    if user_pointer["source_kind"] == "univariate_asset":
        if resolved.get("expected_asset_id") != user_pointer["asset_id"]:
            raise StrategyWorkflowValidationError(
                "candidate_monthly_stability Platform binding and userasset_id Inconsistent.",
                code="strategy_workflow_evidence_conflict",
                fields=("asset_id",),
            )
        expected_user_slots = {"source_kind": "univariate_asset"}
    return _platform_evidence_only(
        "candidate_monthly_stability",
        resolved,
        expected_user_slots=expected_user_slots,
    )

def _scorecard_registry_token(
    artifacts: Sequence[Mapping],
) -> str:
    """CAS all score/sample rows that may change a Scorecard source choice."""

    supported = {
        (
            MODEL_SCORE_EVIDENCE_ARTIFACT_KIND,
            MATERIALIZE_MODEL_SCORE_EVIDENCE_V2_ORIGIN_TOOL,
        ),
        (
            MODEL_SCORE_VECTOR_ARTIFACT_KIND,
            MATERIALIZE_MODEL_SCORE_EVIDENCE_V2_ORIGIN_TOOL,
        ),
        (
            SAMPLE_DESIGN_V2_MEMBERSHIP_ARTIFACT_KIND,
            SAMPLE_DESIGN_V2_ORIGIN_TOOL,
        ),
        (
            SAMPLE_DESIGN_V2_BUNDLE_ARTIFACT_KIND,
            SAMPLE_DESIGN_V2_ORIGIN_TOOL,
        ),
        (
            SCORECARD_BAND_ASSET_ARTIFACT_KIND,
            SCORECARD_BAND_ASSET_ORIGIN_TOOL,
        ),
        (
            SCORECARD_CUTOFF_SELECTION_ARTIFACT_KIND,
            SCORECARD_CUTOFF_SELECTION_ORIGIN_TOOL,
        ),
    }
    relevant = [
        {
            "id": artifact.get("id"),
            "kind": artifact.get("kind"),
            "content_hash": artifact.get("content_hash"),
            "origin_tool": artifact.get("origin_tool"),
            "provenance": artifact.get("provenance"),
            "created_at": artifact.get("created_at"),
        }
        for artifact in artifacts
        if (artifact.get("kind"), artifact.get("origin_tool")) in supported
    ]
    try:
        payload = json.dumps(
            relevant,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_registry_invalid",
            "Scorecard source artifact registry Cannot be standardized; no plans created this time.",
        ) from exc
    return hashlib.sha256(payload).hexdigest()

def _scorecard_artifact_snapshot(
    read_runtime: SimpleNamespace,
    *,
    task_id: str,
) -> tuple[Mapping, ...]:
    try:
        artifacts = tuple(read_runtime.task_artifacts.list_for_task(task_id))
    except _STRATEGY_V2_ARTIFACT_ERRORS as exc:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_registry_unavailable",
            "Could not read current taskScorecard source artifact registry.",
        ) from exc
    if any(not isinstance(artifact, Mapping) for artifact in artifacts):
        raise _StrategyV2EvidenceSetupError(
            "scorecard_registry_invalid",
            "Scorecard source artifact registry Contains invalid records.",
        )
    return artifacts

def _scorecard_ref_hash(value: object, *, field: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_source_ref_invalid",
            f"LatestScorecard source It's...{field} Missing 64 bitshash.",
        )
    return value

def _scorecard_score_evidence_ref(record: Mapping) -> dict[str, str]:
    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping):
        raise _StrategyV2EvidenceSetupError(
            "scorecard_band_score_evidence_invalid",
            "Evidence of scoring of pending models is incompleteprovenance;Platforms do not skip silently or"
            "Back to oldScorecard Evidence.",
        )
    return {
        "evidence_artifact_id": _scorecard_ref_hash(
            record.get("id"),
            field="evidence_artifact_id",
        ),
        "expected_evidence_artifact_content_hash": _scorecard_ref_hash(
            record.get("content_hash"),
            field="expected_evidence_artifact_content_hash",
        ),
        "score_vector_artifact_id": _scorecard_ref_hash(
            provenance.get("score_vector_artifact_id"),
            field="score_vector_artifact_id",
        ),
        "expected_score_vector_artifact_content_hash": _scorecard_ref_hash(
            provenance.get("score_vector_artifact_content_hash"),
            field="expected_score_vector_artifact_content_hash",
        ),
    }

def _scorecard_score_evidence_contract(score: object) -> bool:
    """Return False only for a fully authenticated, clearly non-scorecard model."""

    try:
        training = score.training
        evidence = training.evidence
        evidence_experiment = evidence["experiment"]
        evidence_model = evidence["model_artifact"]
        identities = (
            training.experiment.recipe_id,
            training.model_artifact.algorithm,
            evidence_experiment["recipe_id"],
            evidence_model["algorithm"],
        )
    except (AttributeError, KeyError, TypeError) as exc:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_band_score_evidence_invalid",
            "Lack of consistency in the evidence for the scoring of the pending modelrecipe/algorithm Identity.",
        ) from exc
    scorecard_flags = tuple(value == "scorecard" for value in identities)
    if not any(scorecard_flags):
        return False
    if not all(scorecard_flags):
        raise _StrategyV2EvidenceSetupError(
            "scorecard_band_score_evidence_invalid",
            "Number of cases pending scoring evidenceScorecard recipe/algorithm Identities are not consistent.",
        )
    metadata = evidence_model.get("scoring_metadata")
    envelope = getattr(score, "envelope", None)
    scoring_contract = (
        envelope.get("scoring_contract")
        if isinstance(envelope, Mapping)
        else None
    )
    if (
        not isinstance(metadata, Mapping)
        or not isinstance(envelope, Mapping)
        or not isinstance(scoring_contract, Mapping)
        or envelope.get("score_product") != RAW_SCORE_PRODUCT
        or metadata.get("score_product") != RAW_SCORE_PRODUCT
        or scoring_contract.get("score_direction") != "higher_is_riskier"
        or metadata.get("score_direction") != "higher_is_riskier"
        or metadata.get("points_direction") != "higher_is_better"
        or metadata.get("calibration_status") != "not_applied"
        or not isinstance(metadata.get("scorecard_table"), list)
        or not metadata["scorecard_table"]
    ):
        raise _StrategyV2EvidenceSetupError(
            "scorecard_band_score_contract_invalid",
            "LatestScorecard The score must contain the evidence.raw uncalibrated bad probability,"
            "higher-is-riskier Score direction,higher-is-better points And complete"
            " scorecard_table.",
        )
    return True

def _bind_scorecard_model_score_evidence(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
) -> dict[str, object]:
    """Bind the latest authenticated SampleDesign V2 only."""

    read_runtime = _strategy_v2_read_runtime(runtime)
    artifacts = _strategy_v2_artifact_snapshot(
        read_runtime,
        task_id=task.id,
    )
    sample = _latest_verified_strategy_sample_design_v2_binding(
        read_runtime,
        task_id=task.id,
        artifacts=artifacts,
    )
    design = sample.bundle["sample_design"]
    sample_design_ref = {
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
    return {"sample_design_ref": sample_design_ref}

def _bind_scorecard_band_evidence(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
) -> dict[str, object]:
    """Bind the newest exact score evidence and latest compatible sample."""

    read_runtime = _strategy_report_read_runtime(runtime)
    artifacts = _scorecard_artifact_snapshot(read_runtime, task_id=task.id)
    registry_token = _scorecard_registry_token(artifacts)
    try:
        sample = _latest_verified_strategy_sample_design_v2_binding(
            read_runtime,
            task_id=task.id,
            artifacts=artifacts,
        )
        sample_ref = _strategy_report_sample_ref(sample)
    except _StrategyV2EvidenceSetupError as exc:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_band_sample_invalid",
            "Scorecard The fractional strip needs up-to-date and complete authentication.StrategySampleDesign V2;"
            "The platform will not retreat to the old sample.",
        ) from exc

    score_records = [
        artifact
        for artifact in artifacts
        if artifact.get("kind") == MODEL_SCORE_EVIDENCE_ARTIFACT_KIND
        and artifact.get("origin_tool")
        == MATERIALIZE_MODEL_SCORE_EVIDENCE_V2_ORIGIN_TOOL
    ]
    if not score_records:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_band_score_evidence_required",
            "The current task is not available yet.Scorecard Modelling evidence for fractional bands;"
            "Please be governed.raw bad-probability score evidence.",
        )
    score_ref: dict[str, str] | None = None
    for record in reversed(score_records):
        candidate_ref = _scorecard_score_evidence_ref(record)
        try:
            candidate = load_model_score_evidence_artifacts(
                read_runtime,
                task_id=task.id,
                **candidate_ref,
            )
        except (
            ModelingError,
            OSError,
            KeyError,
            TypeError,
            ValueError,
            *_STRATEGY_V2_ARTIFACT_ERRORS,
        ) as exc:
            raise _StrategyV2EvidenceSetupError(
                "scorecard_band_score_evidence_invalid",
                "The latest evidence of the rating of the pending model was not documented,hash,registry,Model or"
                "full authentication of fraction vectors; platform does not skip or backside silentlyScorecard Evidence.",
            ) from exc
        if not _scorecard_score_evidence_contract(candidate):
            # A fully authenticated non-scorecard result cannot satisfy this
            # workflow and is safe to skip while searching backward.
            continue
        try:
            training_ref = build_training_evidence_ref(candidate.training)
        except (ModelingError, KeyError, TypeError, ValueError) as exc:
            raise _StrategyV2EvidenceSetupError(
                "scorecard_band_score_evidence_invalid",
                "LatestScorecard I'm a scorer.TrainingEvidence Quoted incompletely.",
            ) from exc
        if training_ref.get("sample_design_ref") != sample_ref:
            raise _StrategyV2EvidenceSetupError(
                "scorecard_band_sample_incompatible",
                "LatestScorecard Rating evidence and latestStrategySampleDesign V2 "
                "Not part of the same non-variable sample; please re-create the scoring evidence based on the current sample.",
            )
        score_ref = candidate_ref
        break
    if score_ref is None:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_band_score_evidence_required",
            "The model rating evidence for the current task is not fully certifiedScorecard raw-PD "
            "Rating evidence; finish firstScorecard Training and scoring evidence materialization.",
        )

    refreshed = _scorecard_artifact_snapshot(read_runtime, task_id=task.id)
    if _scorecard_registry_token(refreshed) != registry_token:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_band_source_changed",
            "Scorecard Qualification evidence or evidence ofSampleDesign Changes before the plan is created;"
            "Please try again on the basis of the latest evidence.",
        )

    return {
        "score_evidence_ref": score_ref,
        "sample_design_ref": sample_ref,
    }

def _bind_scorecard_cutoff_evidence(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    workflow_inputs: Mapping[str, object],
) -> dict[str, object]:
    """Bind one explicit asset/cutoff pair to one authenticated full band."""

    asset_id = workflow_inputs.get("asset_id")
    cutoff_id = workflow_inputs.get("cutoff_id")
    read_runtime = _strategy_report_read_runtime(runtime)
    artifacts = _scorecard_artifact_snapshot(read_runtime, task_id=task_id)
    registry_token = _scorecard_registry_token(artifacts)
    matches = []
    for artifact in artifacts:
        provenance = artifact.get("provenance")
        if (
            artifact.get("kind") == SCORECARD_BAND_ASSET_ARTIFACT_KIND
            and artifact.get("origin_tool") == SCORECARD_BAND_ASSET_ORIGIN_TOOL
            and isinstance(provenance, Mapping)
            and provenance.get("schema_version")
            == SCORECARD_BAND_ASSET_ARTIFACT_SCHEMA_VERSION
            and provenance.get("asset_id") == asset_id
        ):
            matches.append(artifact)
    if not matches:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_cutoff_source_required",
            f"Current task incompleteScorecard Split Belt{asset_id};"
            "Please copy the full results from the latest results.asset ID.",
        )
    if len(matches) != 1:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_cutoff_source_ambiguous",
            f"Scorecard Split Belt{asset_id} Multipleartifact,"
            "Currently, it is not possible to safely choose the source.",
        )
    record = matches[0]
    provenance = record["provenance"]
    assert isinstance(provenance, Mapping)
    artifact_id = _scorecard_ref_hash(
        record.get("id"),
        field="source_artifact_id",
    )
    content_hash = _scorecard_ref_hash(
        record.get("content_hash"),
        field="expected_source_artifact_content_hash",
    )
    asset_hash = _scorecard_ref_hash(
        provenance.get("asset_hash"),
        field="expected_asset_hash",
    )
    try:
        binding = load_scorecard_band_asset_artifact(
            read_runtime,
            task_id=task_id,
            artifact_id=artifact_id,
            expected_artifact_content_hash=content_hash,
            expected_asset_id=str(asset_id),
            expected_asset_hash=asset_hash,
        )
    except (
        StrategyError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        *_STRATEGY_V2_ARTIFACT_ERRORS,
    ) as exc:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_cutoff_source_invalid",
            "Complete user callupScorecard Fractional strip failed file,hash,registry,"
            "score evidence orSampleDesign Complete authentication.",
        ) from exc
    cutoffs = binding.asset.get("cutoffs")
    if (
        binding.asset.get("asset_id") != asset_id
        or binding.asset.get("asset_hash") != asset_hash
        or not isinstance(cutoffs, Sequence)
        or isinstance(cutoffs, str | bytes | bytearray)
        or len(
            [
                cutoff
                for cutoff in cutoffs
                if isinstance(cutoff, Mapping)
                and cutoff.get("cutoff_id") == cutoff_id
            ]
        )
        != 1
    ):
        raise _StrategyV2EvidenceSetupError(
            "scorecard_cutoff_pointer_invalid",
            "User-calledcutoff Not fullScorecard (a) Split bands;"
            "Platforms do not replace, rank or recommend otherscutoff.",
        )
    refreshed = _scorecard_artifact_snapshot(read_runtime, task_id=task_id)
    if _scorecard_registry_token(refreshed) != registry_token:
        raise _StrategyV2EvidenceSetupError(
            "scorecard_cutoff_source_changed",
            "Scorecard The fraction is inselection plan; please try again.",
        )
    return {
        "source_artifact_id": binding.artifact_id,
        "expected_source_artifact_content_hash": binding.content_hash,
        "expected_asset_id": str(asset_id),
        "expected_asset_hash": asset_hash,
    }

def _bind_candidate_source_artifact_evidence(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    candidate_id: str,
    workflow_inputs: Mapping,
) -> dict[str, str]:
    artifact_repository = TaskArtifactRepository(runtime.settings.db_path)
    matches = (
        artifact_repository.find_for_task_kind_origin_by_provenance_candidate_id(
            task_id,
            "strategy_candidate_json",
            "strategy.analyze_univariate_candidates",
            candidate_id,
        )
    )
    if not matches:
        raise StrategySetupError(
            f"No evidence of a candidate for the current mission.{candidate_id};Please run a single variable analysis first."
            "Use the results again.candidate ID andsource bin id."
        )
    if len(matches) > 1:
        raise StrategySetupError(
            f"Proof of candidacy{candidate_id} Multiple UnchangeableJSON artifact,"
            "Currently, it is not possible to safely choose the source."
        )
    artifact = matches[0]
    provenance = artifact["provenance"]
    content_hash = artifact.get("content_hash")
    evidence_hash = provenance.get("evidence_hash")
    artifact_id = artifact.get("id")
    if (
        not isinstance(artifact_id, str)
        or not artifact_id
        or not isinstance(content_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", content_hash) is None
        or not isinstance(evidence_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", evidence_hash) is None
    ):
        raise StrategySetupError(
            f"Proof of candidacy{candidate_id} It's...artifact binds are incomplete, and recreates the single variable analysis."
        )
    loader_runtime = SimpleNamespace(
        settings=runtime.settings,
        task_artifacts=artifact_repository,
    )
    try:
        verified = load_verified_candidate_refinement_source(
            loader_runtime,
            task_id=task_id,
            artifact_id=artifact_id,
            expected_content_hash=content_hash,
            expected_candidate_id=candidate_id,
            expected_evidence_hash=evidence_hash,
            feature=workflow_inputs.get("feature"),
            method=workflow_inputs.get("method"),
            merge_groups=workflow_inputs.get("merge_groups", []),
            selection=workflow_inputs.get("selection"),
        )
    except (OSError, StrategyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            f"Proof of candidacy{candidate_id} I can't pass.canonical artifact andrefinement "
            "Control check, recreate analysis or checkfeature,method andsource bin id."
        ) from exc
    return {
        "source_artifact_id": verified.artifact_id,
        "expected_artifact_content_hash": verified.content_hash,
        "expected_candidate_id": verified.candidate_id,
        "expected_evidence_hash": verified.evidence_hash,
    }

def _interactive_tree_split_search_plan_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Authenticate the exact visible node and feature universe before planning."""

    inputs = draft.to_dict()["workflow_inputs"]
    source_tree_id = inputs.get("source_tree_id")
    node_id = inputs.get("node_id")
    if not isinstance(source_tree_id, str) or not isinstance(node_id, str):
        raise StrategySetupError(
            "Node candidate search must provide the full source treeID and Current Visiblenode ID."
        )
    repository = TaskArtifactRepository(runtime.settings.db_path)
    read_runtime = SimpleNamespace(
        settings=runtime.settings,
        task_artifacts=repository,
    )
    try:
        with repository.transaction() as conn:
            source = _resolve_revision_source_on_connection(
                conn,
                runtime=read_runtime,
                task_id=task_id,
                source_tree_id=source_tree_id,
                revision_cache={},
                automatic_source_cache={},
                budget=_RevisionReadBudget(
                    MAX_INTERACTIVE_TREE_REVISION_ANCESTRY_BYTES
                ),
            )
        ancestors = source.ancestor_revisions
        topology = (
            interactive_tree_topology_evidence(source.automatic_source.asset)
            if source.parent_revision is None
            else interactive_tree_topology_evidence(
                source.automatic_source.asset,
                revision_payload=source.parent_revision,
                parent_revision=ancestors[0] if ancestors else None,
                ancestor_revisions=ancestors[1:],
            )
        )
    except Exception as exc:
        raise StrategySetupError(
            f"Source Tree{source_tree_id} Not certified through complete or parent-linking of current task."
        ) from exc
    matches = [
        node
        for node in topology.get("nodes", [])
        if isinstance(node, Mapping) and node.get("node_id") == node_id
    ]
    if len(matches) != 1 or matches[0].get("is_visible") is not True:
        raise StrategySetupError(
            f"Nodes{node_id} It's not a tree.{source_tree_id} Visible nodes in the current projection;"
            "Please refresh the tree view and re-select."
        )
    feature_universe = set(
        source.automatic_source.asset["tree_result"]["training"][
            "feature_order"
        ]
    )
    requested = (
        feature_universe
        if inputs.get("mode") == "all_features"
        else set(inputs.get("features", []))
    )
    if not requested or not requested.issubset(feature_universe):
        raise StrategySetupError(
            "The characteristics of the node candidate search are not the full set of authentication features of the source tree;"
            "Please update the candidate laboratory and re-choice."
        )
    return dict(inputs)

def _interactive_tree_auto_continuation_plan_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Authenticate the exact persisted search and explicit seed candidate."""

    inputs = draft.to_dict()["workflow_inputs"]
    search_id = inputs.get("search_id")
    candidate_id = inputs.get("candidate_id")
    if not isinstance(search_id, str) or not isinstance(candidate_id, str):
        raise StrategySetupError(
            "Autorenewal must provide completesearch ID And clearly chosencandidate ID."
        )
    repository = TaskArtifactRepository(runtime.settings.db_path)
    read_runtime = SimpleNamespace(
        settings=runtime.settings,
        task_artifacts=repository,
    )
    from marvis.packs.strategy.interactive_tree_split_search_tools import (
        load_verified_interactive_tree_split_search,
    )

    try:
        search = load_verified_interactive_tree_split_search(
            read_runtime,
            task_id=task_id,
            search_id=search_id,
        )
    except Exception as exc:
        raise StrategySetupError(
            f"Can not open message{search_id} Not certified through complete products of current tasks."
        ) from exc
    candidate = next(
        (
            item
            for item in search.result["candidates"]
            if item.get("candidate_id") == candidate_id
        ),
        None,
    )
    if candidate is None or candidate.get("eligible") is not True:
        raise StrategySetupError(
            f"Candidates{candidate_id} Other Organiser{search_id},or fails to pass the minimum leaf limit."
        )
    return dict(inputs)

def _interactive_tree_revision_plan_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Authenticate the threshold target, then inject only user controls.

    This read-side projection is a usability preflight, not the execution
    authority.  ``revise_interactive_tree`` repeats the complete source/ancestry
    authentication under its writer lock before deterministic replay.
    """

    inputs = draft.to_dict()["workflow_inputs"]
    source_tree_id = inputs.get("source_tree_id")
    node_id = inputs.get("node_id")
    operation = inputs.get("operation")
    if (
        operation
        not in {"adjust_split_threshold", "replace_split_feature"}
        or not isinstance(source_tree_id, str)
        or not isinstance(node_id, str)
    ):
        raise StrategySetupError(
            "The interactive tree division adjustment must provide the full source tree, current visiblesplit node and"
            "Accurate control value."
        )

    repository = TaskArtifactRepository(runtime.settings.db_path)
    if source_tree_id.startswith("candidate-asset-"):
        try:
            artifacts = repository.list_for_task(task_id)
        except Exception as exc:
            raise StrategySetupError(
                "Interactive Tree for Current Taskartifact registry Could not read, can not check the current projection."
            ) from exc
        matches = []
        for artifact in artifacts:
            if not isinstance(artifact, Mapping):
                raise StrategySetupError(
                    "Interactive Tree for Current Taskartifact The recording structure is invalid."
                )
            provenance = artifact.get("provenance")
            if (
                artifact.get("kind") == AUTOMATIC_TREE_SOURCE_ARTIFACT_KIND
                and artifact.get("origin_tool")
                == AUTOMATIC_TREE_SOURCE_ARTIFACT_ORIGIN_TOOL
                and isinstance(provenance, Mapping)
                and provenance.get("asset_id") == source_tree_id
            ):
                matches.append(artifact)
        if len(matches) != 1:
            raise StrategySetupError(
                f"The current task does not have a single automatic tree asset{source_tree_id};Project from the current tree"
                "Copy Full SourceID."
            )
        artifact = matches[0]
        provenance = artifact.get("provenance")
        assert isinstance(provenance, Mapping)
        required = (
            artifact.get("id"),
            artifact.get("content_hash"),
            provenance.get("asset_hash"),
            provenance.get("tree_result_hash"),
        )
        if not all(isinstance(value, str) and value for value in required):
            raise StrategySetupError(
                f"Auto-tree assets{source_tree_id} , re-construct."
            )
        try:
            with repository.transaction() as conn:
                verified_source = (
                    load_verified_automatic_tree_source_artifact_on_connection(
                        conn,
                        tasks_dir=runtime.settings.tasks_dir,
                        task_id=task_id,
                        artifact_id=str(artifact["id"]),
                        expected_content_hash=str(artifact["content_hash"]),
                        expected_asset_id=source_tree_id,
                        expected_asset_hash=str(provenance["asset_hash"]),
                        expected_tree_result_hash=str(
                            provenance["tree_result_hash"]
                        ),
                    )
                )
            topology = interactive_tree_topology_evidence(
                verified_source.asset,
            )
            authenticated_feature_order = tuple(
                verified_source.asset["tree_result"]["training"][
                    "feature_order"
                ]
            )
        except Exception as exc:
            raise StrategySetupError(
                f"Auto-tree assets{source_tree_id} The threshold cannot be adjusted without certification of the complete product."
            ) from exc
    else:
        read_runtime = SimpleNamespace(
            settings=runtime.settings,
            task_artifacts=repository,
        )
        try:
            verified_revision = load_verified_interactive_tree_revision(
                read_runtime,
                task_id=task_id,
                revision_id=source_tree_id,
            )
            ancestors = verified_revision.ancestor_revisions
            topology = interactive_tree_topology_evidence(
                verified_revision.automatic_source.asset,
                revision_payload=verified_revision.revision,
                parent_revision=(ancestors[0] if ancestors else None),
                ancestor_revisions=(ancestors[1:] if ancestors else ()),
            )
            authenticated_feature_order = tuple(
                verified_revision.automatic_source.asset["tree_result"][
                    "training"
                ]["feature_order"]
            )
        except Exception as exc:
            raise StrategySetupError(
                f"Interactive Tree Revision{source_tree_id} The threshold cannot be adjusted without complete parent-chain authentication."
            ) from exc

    projected_nodes = topology.get("nodes")
    matches = (
        [
            node
            for node in projected_nodes
            if isinstance(node, Mapping) and node.get("node_id") == node_id
        ]
        if isinstance(projected_nodes, list)
        else []
    )
    if (
        len(matches) != 1
        or matches[0].get("kind") != "split"
        or matches[0].get("is_visible") is not True
        or matches[0].get("can_prune") is not True
    ):
        raise StrategySetupError(
            f"Nodes{node_id} It's not a tree.{source_tree_id} Editable in Current Projection"
            "split node;Please refresh the tree view and re-select."
        )
    if operation == "replace_split_feature":
        feature = inputs.get("feature")
        if (
            not isinstance(feature, str)
            or feature not in authenticated_feature_order
            or feature == matches[0].get("feature")
        ):
            raise StrategySetupError(
                f"New feature{feature!r} Not a full set of authentication features of the source tree, or with nodes"
                "Current characteristics are the same; please re-select from the current candidate."
            )

    # Never pass projection rows, metrics, hashes or ancestry through a user
    # plan.  The deterministic Tool recovers those facts itself.
    return {
        field: inputs[field]
        for field in (
            "source_tree_id",
            "node_id",
            "operation",
            "feature",
            "threshold",
            "reason",
        )
        if field in inputs
    }

def _automatic_tree_leaf_materialization_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Bind one explicit leaf request to one verified task-owned full tree."""

    inputs = draft.to_dict()["workflow_inputs"]
    asset_id = inputs.get("tree_asset_id")
    leaf_id = inputs.get("leaf_id")
    if not isinstance(asset_id, str) or not isinstance(leaf_id, str):
        raise StrategySetupError(
            "Autoleaf node materialization must provide completetree asset ID andleaf ID."
        )

    repository = TaskArtifactRepository(runtime.settings.db_path)
    try:
        artifacts = repository.list_for_task(task_id)
    except Exception as exc:
        raise StrategySetupError(
            "Autotree for current taskartifact registry It is not readable, it cannot securely bind the source."
        ) from exc
    matches = []
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise StrategySetupError("Autotree for current taskartifact The recording structure is invalid.")
        provenance = artifact.get("provenance")
        if (
            artifact.get("kind") == AUTOMATIC_TREE_SOURCE_ARTIFACT_KIND
            and artifact.get("origin_tool")
            == AUTOMATIC_TREE_SOURCE_ARTIFACT_ORIGIN_TOOL
            and isinstance(provenance, Mapping)
            and provenance.get("asset_id") == asset_id
        ):
            matches.append(artifact)
    if not matches:
        raise StrategySetupError(
            f"No automatic tree assets for current task{asset_id};Please use the complete display in the build result"
            "candidate-asset ID."
        )
    if len(matches) != 1:
        raise StrategySetupError(
            f"Auto-tree assets{asset_id} Multiplefull-tree JSON artifact,"
            "Currently, it is not possible to safely choose the source."
        )

    artifact = matches[0]
    provenance = artifact.get("provenance")
    assert isinstance(provenance, Mapping)
    artifact_id = artifact.get("id")
    content_hash = artifact.get("content_hash")
    asset_hash = provenance.get("asset_hash")
    tree_result_hash = provenance.get("tree_result_hash")
    if not all(
        isinstance(value, str) and value
        for value in (
            artifact_id,
            content_hash,
            asset_hash,
            tree_result_hash,
        )
    ):
        raise StrategySetupError(
            f"Auto-tree assets{asset_id} It's...artifact Complete binding is incomplete, please rebuild."
        )

    try:
        with repository.transaction() as conn:
            verified = load_verified_automatic_tree_source_artifact_on_connection(
                conn,
                tasks_dir=runtime.settings.tasks_dir,
                task_id=task_id,
                artifact_id=artifact_id,
                expected_content_hash=content_hash,
                expected_asset_id=asset_id,
                expected_asset_hash=asset_hash,
                expected_tree_result_hash=tree_result_hash,
            )
    except Exception as exc:
        raise StrategySetupError(
            f"Auto-tree assets{asset_id} Not adoptedartifact Complete verification, please rebuild."
        ) from exc

    fragments = verified.asset.get("fragments")
    if isinstance(fragments, Sequence) and not isinstance(
        fragments, str | bytes | bytearray
    ):
        leaf_matches = [
            fragment
            for fragment in fragments
            if isinstance(fragment, Mapping) and fragment.get("leaf_id") == leaf_id
        ]
    else:
        leaf_matches = []
    if len(leaf_matches) != 1:
        raise StrategySetupError(
            f"Auto-tree assets{asset_id} There is no single matching leaf node{leaf_id};"
            "Please copy the full list of leaf nodesleaf ID."
        )

    slots: dict[str, object] = {
        "source_artifact_id": verified.artifact_id,
        "expected_artifact_content_hash": verified.content_hash,
        "expected_asset_id": verified.asset["asset_id"],
        "expected_asset_hash": verified.asset["asset_hash"],
        "expected_tree_result_hash": verified.asset["tree_result"]["result_hash"],
        "leaf_id": leaf_id,
    }
    if "selection_reason" in inputs:
        slots["selection_reason"] = inputs["selection_reason"]
    return slots

def _automatic_tree_apply_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    draft: StandardWorkflowRequestDraft,
    context,
) -> dict[str, object]:
    """Bind full-tree writeback to its exact task-owned source workspace."""

    inputs = draft.to_dict()["workflow_inputs"]
    asset_id = inputs.get("tree_asset_id")
    if not isinstance(asset_id, str):
        raise StrategySetupError(
            "Auto-repeated full volume must provide completetree asset ID."
        )

    repository = TaskArtifactRepository(runtime.settings.db_path)
    try:
        artifacts = repository.list_for_task(task_id)
    except Exception as exc:
        raise StrategySetupError(
            "Autotree for current taskartifact registry It is not readable, it cannot securely bind the source."
        ) from exc
    matches = []
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise StrategySetupError("Autotree for current taskartifact The recording structure is invalid.")
        provenance = artifact.get("provenance")
        if (
            artifact.get("kind") == AUTOMATIC_TREE_SOURCE_ARTIFACT_KIND
            and artifact.get("origin_tool")
            == AUTOMATIC_TREE_SOURCE_ARTIFACT_ORIGIN_TOOL
            and isinstance(provenance, Mapping)
            and provenance.get("asset_id") == asset_id
        ):
            matches.append(artifact)
    if not matches:
        raise StrategySetupError(
            f"No automatic tree assets for current task{asset_id};Please use the complete display in the build result"
            "candidate-asset ID."
        )
    if len(matches) != 1:
        raise StrategySetupError(
            f"Auto-tree assets{asset_id} Multiplefull-tree JSON artifact,"
            "Currently, it is not possible to safely choose the source."
        )

    artifact = matches[0]
    provenance = artifact.get("provenance")
    assert isinstance(provenance, Mapping)
    artifact_id = artifact.get("id")
    content_hash = artifact.get("content_hash")
    asset_hash = provenance.get("asset_hash")
    tree_result_hash = provenance.get("tree_result_hash")
    if not all(
        isinstance(value, str) and value
        for value in (artifact_id, content_hash, asset_hash, tree_result_hash)
    ):
        raise StrategySetupError(
            f"Auto-tree assets{asset_id} It's...artifact Complete binding is incomplete, please rebuild."
        )

    try:
        with repository.transaction() as conn:
            verified = load_verified_automatic_tree_source_artifact_on_connection(
                conn,
                tasks_dir=runtime.settings.tasks_dir,
                task_id=task_id,
                artifact_id=artifact_id,
                expected_content_hash=content_hash,
                expected_asset_id=asset_id,
                expected_asset_hash=asset_hash,
                expected_tree_result_hash=tree_result_hash,
            )
    except Exception as exc:
        raise StrategySetupError(
            f"Auto-tree assets{asset_id} Not adoptedartifact Complete verification, please rebuild."
        ) from exc

    identity = verified.asset.get("identity")
    if not isinstance(identity, Mapping):
        raise StrategySetupError(
            f"Auto-tree assets{asset_id} Missing original samplelineage,Please rebuild."
        )
    try:
        workspace = DataWorkspaceRepository(
            runtime.settings.db_path
        ).get_or_default(task_id)
    except (DataWorkspaceDataError, KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "Current activityDataWorkspace Could not verify this."
        ) from exc

    semantic_hash = data_semantic_mapping_hash(workspace.semantic_mapping)
    expected_binding = {
        "task_id": task_id,
        "dataset_id": getattr(context, "dataset_id", None),
        "dataset_content_hash": getattr(context, "dataset_content_hash", None),
        "workspace_revision": getattr(context, "workspace_revision", None),
        "workspace_generation": getattr(context, "analysis_generation", None),
        "semantic_mapping_hash": getattr(context, "semantic_mapping_hash", None),
    }
    live_binding = {
        "task_id": task_id,
        "dataset_id": workspace.active_dataset_id,
        "dataset_content_hash": workspace.active_dataset_content_hash,
        "workspace_revision": workspace.revision,
        "workspace_generation": workspace.analysis_generation,
        "semantic_mapping_hash": semantic_hash,
    }
    if any(identity.get(field) != value for field, value in expected_binding.items()):
        raise StrategySetupError(
            f"Auto-tree assets{asset_id} Only original bound samples of construction are allowed to be written back;"
            "The context of the current policy data has changed, please rebuild or cut back to originalworkspace."
        )
    if live_binding != expected_binding:
        raise StrategySetupError(
            "CurrentDataWorkspace Change during automatic tree writing back binding; not implemented this time."
        )

    output_columns = {
        "leaf_id_column": inputs.get(
            "leaf_id_column", "automatic_tree_leaf_id"
        ),
        "rule_id_column": inputs.get(
            "rule_id_column", "automatic_tree_rule_id"
        ),
    }
    folded_source_columns = {
        str(column).casefold() for column in getattr(context, "columns", ())
    }
    if any(
        not isinstance(column, str)
        or column.casefold() in folded_source_columns
        for column in output_columns.values()
    ):
        raise StrategySetupError(
            "Auto-Brive Return column conflicts with existing fields in the current sample. Please specify a new leaf node and rulebar."
        )

    slots: dict[str, object] = {
        "source_artifact_id": verified.artifact_id,
        "expected_artifact_content_hash": verified.content_hash,
        "expected_asset_id": verified.asset["asset_id"],
        "expected_asset_hash": verified.asset["asset_hash"],
        "expected_tree_result_hash": verified.asset["tree_result"]["result_hash"],
        "dataset_id": identity["dataset_id"],
        "expected_content_hash": identity["dataset_content_hash"],
        "workspace_revision": identity["workspace_revision"],
        "analysis_generation": identity["workspace_generation"],
        "semantic_mapping_hash": identity["semantic_mapping_hash"],
    }
    for field in ("leaf_id_column", "rule_id_column"):
        if field in inputs:
            slots[field] = inputs[field]
    return slots

def _cross_matrix_cell_selection_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Bind exact user cell ids to one verified task-owned full matrix."""

    inputs = draft.to_dict()["workflow_inputs"]
    asset_id = inputs.get("cross_asset_id")
    cell_ids = inputs.get("cell_ids")
    if (
        not isinstance(asset_id, str)
        or not isinstance(cell_ids, Sequence)
        or isinstance(cell_ids, str | bytes | bytearray)
        or any(not isinstance(cell_id, str) for cell_id in cell_ids)
    ):
        raise StrategySetupError(
            "Cross Matrix Cell selection must provide completecross asset ID andcell ID list."
        )

    repository = TaskArtifactRepository(runtime.settings.db_path)
    try:
        artifacts = repository.list_for_task(task_id)
    except Exception as exc:
        raise StrategySetupError(
            "Current TaskCross Matrix artifact registry It is not readable, it cannot securely bind the source."
        ) from exc
    matches = []
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise StrategySetupError("Current TaskCross Matrix artifact The recording structure is invalid.")
        provenance = artifact.get("provenance")
        if (
            artifact.get("kind") == CROSS_MATRIX_SOURCE_ARTIFACT_KIND
            and artifact.get("origin_tool")
            == CROSS_MATRIX_SOURCE_ARTIFACT_ORIGIN_TOOL
            and isinstance(provenance, Mapping)
            and provenance.get("schema_version")
            == CROSS_MATRIX_SOURCE_ARTIFACT_SCHEMA_VERSION
            and provenance.get("asset_id") == asset_id
        ):
            matches.append(artifact)
    if not matches:
        raise StrategySetupError(
            f"Current task incompleteCross Matrix Assets{asset_id};Please use the build result"
            "Full displaycandidate-asset ID."
        )
    if len(matches) != 1:
        raise StrategySetupError(
            f"Cross Matrix Assets{asset_id} Multiplefull-matrix JSON artifact,"
            "Currently, it is not possible to safely choose the source."
        )

    artifact = matches[0]
    provenance = artifact.get("provenance")
    assert isinstance(provenance, Mapping)
    artifact_id = artifact.get("id")
    content_hash = artifact.get("content_hash")
    asset_hash = provenance.get("asset_hash")
    candidate_id = provenance.get("candidate_id")
    evidence_hash = provenance.get("evidence_hash")
    if not all(
        isinstance(value, str) and value
        for value in (
            artifact_id,
            content_hash,
            asset_hash,
            candidate_id,
            evidence_hash,
        )
    ):
        raise StrategySetupError(
            f"Cross Matrix Assets{asset_id} It's...artifact Complete binding is incomplete, please rebuild."
        )

    try:
        with repository.transaction() as conn:
            verified = load_verified_cross_matrix_source_artifact_on_connection(
                conn,
                tasks_dir=runtime.settings.tasks_dir,
                task_id=task_id,
                artifact_id=artifact_id,
                expected_content_hash=content_hash,
                expected_asset_id=asset_id,
                expected_asset_hash=asset_hash,
                expected_candidate_id=candidate_id,
                expected_evidence_hash=evidence_hash,
            )
    except Exception as exc:
        raise StrategySetupError(
            f"Cross Matrix Assets{asset_id} Not adoptedartifact Complete verification, please rebuild."
        ) from exc

    matrix = verified.asset.get("matrix")
    cells = matrix.get("cells") if isinstance(matrix, Mapping) else None
    if not isinstance(cells, Sequence) or isinstance(cells, str | bytes | bytearray):
        raise StrategySetupError(
            f"Cross Matrix Assets{asset_id} Missing completenesscell list, please rebuild."
        )
    source_cell_ids = [
        cell.get("cell_id") for cell in cells if isinstance(cell, Mapping)
    ]
    if (
        len(source_cell_ids) != len(cells)
        or len(set(source_cell_ids)) != len(source_cell_ids)
        or any(source_cell_ids.count(cell_id) != 1 for cell_id in cell_ids)
    ):
        raise StrategySetupError(
            f"Cross Matrix Assets{asset_id} Could not match all of themcell ID;"
            "Please copy the full list of cells correctlyID."
        )
    requested = set(cell_ids)
    ordered_cell_ids = [cell_id for cell_id in source_cell_ids if cell_id in requested]
    if len(ordered_cell_ids) != len(cell_ids):
        raise StrategySetupError(
            f"Cross Matrix Assets{asset_id} Could not match all of themcell ID;"
            "Please copy the full list of cells correctlyID."
        )

    evidence = verified.asset.get("candidate_evidence")
    if not isinstance(evidence, Mapping):
        raise StrategySetupError(
            f"Cross Matrix Assets{asset_id} If you are not bound by the candidate, please re-build."
        )
    slots: dict[str, object] = {
        "source_artifact_id": verified.artifact_id,
        "expected_artifact_content_hash": verified.content_hash,
        "expected_asset_id": verified.asset["asset_id"],
        "expected_asset_hash": verified.asset["asset_hash"],
        "expected_candidate_id": evidence["candidate_id"],
        "expected_evidence_hash": evidence["evidence_hash"],
        "cell_ids": ordered_cell_ids,
    }
    if "selection_reason" in inputs:
        slots["selection_reason"] = inputs["selection_reason"]
    return slots

def _latest_cross_candidate_search_source_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
) -> dict[str, str]:
    """Bind the newest univariate evidence exactly; never fall back on damage."""

    repository = TaskArtifactRepository(runtime.settings.db_path)
    try:
        artifacts = repository.list_for_task(task_id)
    except Exception as exc:
        raise StrategySetupError(
            "Single variable candidate for current taskartifact registry Can not read."
            "Can't create safelyCross Automatic search plan."
        ) from exc
    matches = [
        artifact
        for artifact in artifacts
        if isinstance(artifact, Mapping)
        and artifact.get("kind") == "strategy_candidate_json"
        and artifact.get("origin_tool")
        == "strategy.analyze_univariate_candidates"
    ]
    if not matches:
        raise StrategySetupError(
            "There is no single variable candidate for the current task; please start with the single variable candidate analysis."
            "Search again.Cross Matrix ."
        )
    latest = matches[-1]
    provenance = latest.get("provenance")
    artifact_id = latest.get("id")
    content_hash = latest.get("content_hash")
    candidate_id = (
        provenance.get("candidate_id")
        if isinstance(provenance, Mapping)
        else None
    )
    evidence_hash = (
        provenance.get("evidence_hash")
        if isinstance(provenance, Mapping)
        else None
    )
    if (
        not isinstance(artifact_id, str)
        or re.fullmatch(r"[0-9a-f]{64}", artifact_id) is None
        or not isinstance(content_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", content_hash) is None
        or not isinstance(candidate_id, str)
        or re.fullmatch(r"candidate-[0-9a-f]{32}", candidate_id) is None
        or not isinstance(evidence_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", evidence_hash) is None
    ):
        raise StrategySetupError(
            "The latest single variable candidate.artifact/candidate/evidence (a) Inadequate identity;"
            "The platform does not retreat to older evidence, please rerun the single variable analysis."
        )
    return {
        "source_artifact_id": artifact_id,
        "expected_artifact_content_hash": content_hash,
        "expected_candidate_id": candidate_id,
        "expected_evidence_hash": evidence_hash,
    }

def _strategy_cross_candidate_search_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Combine only user search controls with the platform-owned source."""

    if draft.workflow != "cross_matrix_candidate_search":
        raise StrategySetupError(
            "Cross Autogroup Searchslots We got the wrong one.Workflow."
        )
    inputs = draft.to_dict()["workflow_inputs"]
    return {
        **_latest_cross_candidate_search_source_slots(
            runtime,
            task_id=task.id,
        ),
        "features": list(inputs["features"]),
        "max_pairs": inputs["max_pairs"],
    }

def _strategy_cross_candidate_build_from_search_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Preflight exact pointers without copying recovered pair facts."""

    if draft.workflow != "cross_matrix_candidate_build_from_search":
        raise StrategySetupError(
            "Cross Search result buildslots We got the wrong one.Workflow."
        )
    inputs = draft.to_dict()["workflow_inputs"]
    try:
        read_runtime = _strategy_report_read_runtime(runtime)
        resolve_cross_candidate_search_pair(
            read_runtime,
            task_id=task.id,
            search_id=inputs["search_id"],
            pair_id=inputs["pair_id"],
        )
    except StrategyError as exc:
        raise StrategySetupError(str(exc)) from exc
    return {
        "search_id": inputs["search_id"],
        "pair_id": inputs["pair_id"],
    }

def _strategy_cross_rule_search_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Bind platform evidence separately from explicit rule-search controls."""

    if draft.workflow != "cross_rule_search":
        raise StrategySetupError(
            "Cross Threshold rule searchslots We got the wrong one.Workflow."
        )
    inputs = draft.to_dict()["workflow_inputs"]
    return {
        **_latest_cross_candidate_search_source_slots(
            runtime,
            task_id=task.id,
        ),
        "features": list(inputs["features"]),
        "dimension": inputs["dimension"],
        "constraints": dict(inputs["constraints"]),
        "max_trials": inputs["max_trials"],
    }

def _strategy_cross_rule_candidate_build_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Preflight one exact rule pointer; never infer from rank."""

    if draft.workflow != "cross_rule_candidate_build_from_search":
        raise StrategySetupError(
            "Cross Candidature for the threshold ruleslots We got the wrong one.Workflow."
        )
    inputs = draft.to_dict()["workflow_inputs"]
    try:
        resolve_cross_rule_search_rule(
            _strategy_report_read_runtime(runtime),
            task_id=task.id,
            search_id=inputs["search_id"],
            rule_id=inputs["rule_id"],
        )
    except StrategyError as exc:
        raise StrategySetupError(str(exc)) from exc
    return {
        "search_id": inputs["search_id"],
        "rule_id": inputs["rule_id"],
        "selection_reason": inputs.get("selection_reason"),
    }

def _strategy_voting_candidate_search_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Bind user controls to the exact current Pool through the Tool resolver."""

    if draft.workflow != "voting_candidate_search":
        raise StrategySetupError("Voting Group Searchslots We got the wrong one.Workflow.")
    try:
        read_runtime = _strategy_report_read_runtime(runtime)
        return resolve_voting_candidate_search_inputs(
            read_runtime,
            task_id=task.id,
            user_controls=draft.to_dict()["workflow_inputs"],
        )
    except StrategyError as exc:
        raise StrategySetupError(str(exc)) from exc

def _strategy_voting_candidate_build_from_search_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Preflight exact pointers without copying recovered state into the plan."""

    if draft.workflow != "voting_candidate_build_from_search":
        raise StrategySetupError(
            "Voting Search result buildslots We got the wrong one.Workflow."
        )
    inputs = draft.to_dict()["workflow_inputs"]
    try:
        read_runtime = _strategy_report_read_runtime(runtime)
        resolve_voting_candidate_search_selection(
            read_runtime,
            task_id=task.id,
            search_id=inputs["search_id"],
            combo_id=inputs["combo_id"],
            strategy_type=inputs.get("strategy_type"),
        )
    except StrategyError as exc:
        raise StrategySetupError(str(exc)) from exc
    return dict(inputs)

def _strategy_voting_candidate_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Bind explicit user rule ids to one exact current Pool snapshot."""

    inputs = draft.to_dict()["workflow_inputs"]
    strategy_type = inputs.get("strategy_type")
    rule_ids = inputs.get("rule_ids")
    n = inputs.get("n")
    if (
        not isinstance(strategy_type, str)
        or not isinstance(rule_ids, Sequence)
        or isinstance(rule_ids, str | bytes | bytearray)
        or isinstance(n, bool)
        or not isinstance(n, int)
    ):
        raise StrategySetupError(
            "Voting Candidates need to be clear about the type of strategic pool, complete.rule_id List and Integern."
        )
    try:
        current = StrategyCandidatePoolRepository(
            runtime.settings.db_path
        ).get_current(task.id, strategy_type)
    except Exception as exc:
        raise StrategySetupError(
            "CurrentStrategy Pool State cannot be verified through completeness, cannot buildVoting Candidates."
        ) from exc
    if current is None:
        raise StrategySetupError(
            f"No current task.{strategy_type} Strategy Pool;Please add at least two candidate rules to the pool."
        )
    try:
        entries = _strategy_pool_entries(current)
        revision = int(current["revision"])
        snapshot_hash = strategy_pool_snapshot_hash(current)
    except (KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "CurrentStrategy Pool revision,entries orhash The binding is incomplete."
        ) from exc

    selected: list[Mapping] = []
    for rule_id in rule_ids:
        matches = [entry for entry in entries if entry.get("rule_id") == rule_id]
        if len(matches) != 1:
            raise StrategySetupError(
                f"CurrentStrategy Pool There is no single rule for matching{rule_id};"
                "Please update from the latestPool Quite a copy.rule_id."
            )
        entry = matches[0]
        if entry.get("enabled") is not True:
            raise StrategySetupError(f"Rule{rule_id} Current not enabled, not availableVoting.")
        source = entry.get("source")
        if isinstance(source, Mapping) and source.get("asset_type") == "voting_n_of_k":
            raise StrategySetupError(
                "Current version rejects nesting firstVoting Candidates to avoid regressionlineage or recycling dependence;"
                "Select the original single variable or the automatic leaf rule."
            )
        selected.append(entry)
    selected.sort(key=lambda item: int(item.get("position", -1)))
    if not 2 <= len(selected) <= 50 or not 1 <= n <= len(selected):
        raise StrategySetupError("Voting Candidates 2 to 50 rules, andn Must be on 1 toK.")
    return {
        "strategy_type": strategy_type,
        "expected_pool_revision": revision,
        "expected_pool_snapshot_hash": snapshot_hash,
        "selected_entry_ids": [str(entry["entry_id"]) for entry in selected],
        "n": n,
    }

def _strategy_pool_apply_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Bind one specified current nonempty Pool without exposing its identity."""

    if draft.workflow != "strategy_pool_apply":
        raise StrategySetupError(
            "Strategy Pool Applyslots We got the wrong one.Workflow."
        )
    inputs = draft.to_dict()["workflow_inputs"]
    strategy_type = str(inputs["strategy_type"])
    try:
        pool = StrategyCandidatePoolRepository(
            runtime.settings.db_path
        ).get_current(task.id, strategy_type)
    except Exception as exc:
        raise StrategySetupError(
            "CurrentStrategy Pool The state cannot be verified through completeness and the application writing back cannot be executed."
        ) from exc
    if pool is None:
        raise StrategySetupError(
            f"No current task.{strategy_type} Strategy Pool,Could not close temporary folder: %s"
        )
    if not _strategy_pool_entries(pool):
        raise StrategySetupError(
            f"Current{strategy_type} Strategy Pool is empty; please add the candidacy rule before applying."
        )
    try:
        revision = pool["revision"]
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ValueError("invalid Pool revision")
        snapshot_hash = strategy_pool_snapshot_hash(pool)
        if (
            not isinstance(snapshot_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", snapshot_hash) is None
        ):
            raise ValueError("invalid Pool snapshot hash")
    except (KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "CurrentStrategy Pool revision/hash The binding is incomplete and the application writing back cannot be executed."
        ) from exc

    slots: dict[str, object] = {
        "strategy_type": strategy_type,
        "expected_pool_revision": revision,
        "expected_pool_snapshot_hash": snapshot_hash,
    }
    if "output_prefix" in inputs:
        slots["output_prefix"] = inputs["output_prefix"]
    return slots

def _strategy_pool_materialize_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Deeply authenticate one current nonempty Pool and freeze Tool identity."""

    if draft.workflow != "strategy_pool_materialize":
        raise StrategySetupError(
            "Strategy Pool Physicalizationslots We got the wrong one.Workflow."
        )
    strategy_type = str(draft.workflow_inputs["strategy_type"])
    read_runtime = _strategy_v2_read_runtime(runtime)
    try:
        binding = load_current_strategy_candidate_pool_artifact(
            read_runtime,
            task_id=task.id,
            strategy_type=strategy_type,
        )
    except (StrategyError, *_STRATEGY_V2_ARTIFACT_ERRORS) as exc:
        raise StrategySetupError(
            f"Current{strategy_type} Strategy Pool It's...artifact,Source, compilation results"
            "orlineage Could not close temporary folder: %sdraft Strategy."
        ) from exc

    pool = binding.pool
    design = binding.compiled_design
    try:
        if (
            binding.task_id != task.id
            or binding.strategy_type != strategy_type
            or not _strategy_pool_entries(pool)
        ):
            raise ValueError("Pool binding is not the requested nonempty current Pool")
        revision = pool["revision"]
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ValueError("invalid Pool revision")
        snapshot_hash = pool["snapshot_hash"]
        artifact_id = binding.artifact_id
        artifact_content_hash = binding.artifact_content_hash
        design_hash = design["design_hash"]
        for value in (
            snapshot_hash,
            artifact_id,
            artifact_content_hash,
            design_hash,
        ):
            if (
                not isinstance(value, str)
                or re.fullmatch(r"[0-9a-f]{64}", value) is None
            ):
                raise ValueError("invalid authenticated hash")
    except (KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "CurrentStrategy Pool orPool The non-empty conditions are not valid."
            "Can not create folder lock on %s: %sdraft Strategy."
        ) from exc

    return {
        "strategy_type": strategy_type,
        "expected_pool_revision": revision,
        "expected_pool_snapshot_hash": snapshot_hash,
        "expected_pool_artifact_id": artifact_id,
        "expected_pool_artifact_content_hash": artifact_content_hash,
        "expected_design_hash": design_hash,
    }

def _strategy_pool_validation_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Bind one current Pool to one exact mature independent V2 partition."""

    if draft.workflow != "strategy_pool_validation":
        raise StrategySetupError(
            "Strategy Pool Independent sample playback validationslots We got the wrong one.Workflow."
        )
    inputs = draft.to_dict()["workflow_inputs"]
    strategy_type = str(inputs.get("strategy_type") or "")
    partition = str(inputs.get("partition") or "")
    if strategy_type not in {
        "approval",
        "reject",
        "limit",
        "pricing",
        "segmentation",
    }:
        raise StrategySetupError(
            "Independent sample playback validationstrategy_type No support."
        )
    if partition not in {"validation", "oot"}:
        raise StrategySetupError(
            "Independent sample playback validationpartition It's just...validation oroot."
        )

    read_runtime = _strategy_v2_read_runtime(runtime)
    try:
        pool = _strategy_report_current_pool_binding(
            read_runtime,
            task_id=task.id,
            requested_type=strategy_type,
        )
    except _StrategyV2EvidenceSetupError as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_pool_validation_pool_invalid",
            f"Current{strategy_type} Strategy Pool Not passed Non-emptyhead,artifact,"
            "revision/hash Or complete.candidate lineage Certification.",
        ) from exc
    try:
        sample = _strategy_report_latest_sample_binding(
            read_runtime,
            task_id=task.id,
        )
    except _StrategyV2EvidenceSetupError as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_pool_validation_sample_invalid",
            "Independent sample re-play validation requires up-to-date and complete authenticationStrategySampleDesign V2 "
            "membership/bundle;The platform will not retreat to the old sample.",
        ) from exc

    try:
        design = sample.bundle["sample_design"]
        target = design["target_selector"]
        scope = design["sample_semantics"]["scope"]
        risk_populations = [
            item
            for item in sample.bundle["populations"]
            if item.get("role") == "risk"
        ]
        maturity = risk_populations[0]["maturity_evidence"]["status"]
        partition_count = sample.membership["header"]["counts"]["risk"][
            partition
        ]
        source = sample.source_binding
        dataset_id = source.dataset_id
        dataset_hash = source.dataset_content_hash
        workspace_revision = source.workspace_revision
        workspace_generation = source.workspace_generation
        semantic_hash = source.semantic_mapping_hash
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_pool_validation_sample_invalid",
            "StrategySampleDesign V2 Missingrisk Total, maturity, independent divisions,"
            "dataset/workspace/target Or semantic binding.",
        ) from exc
    if len(risk_populations) != 1 or maturity != "confirmed_matured":
        raise StrategySetupError(
            "Independent sample replay validation requirementsrisk Overall, there are proven mature performance results."
        )
    if (
        target.get("status") != "resolved"
        or not isinstance(target.get("column"), str)
        or not target["column"]
        or scope != "strategy_development"
    ):
        raise StrategySetupError(
            "Independent sample re-laying requires the parsing of target lines and the syntax of the governance strategy."
        )
    if (
        isinstance(partition_count, bool)
        or not isinstance(partition_count, int)
        or partition_count <= 0
    ):
        raise StrategySetupError(
            f"StrategySampleDesign V2 It's...risk/{partition} The independent division is empty."
            "Can not get folder: %s: %s"
        )
    if (
        not isinstance(dataset_id, str)
        or not dataset_id
        or not isinstance(dataset_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", dataset_hash) is None
        or isinstance(workspace_revision, bool)
        or not isinstance(workspace_revision, int)
        or workspace_revision < 0
        or isinstance(workspace_generation, bool)
        or not isinstance(workspace_generation, int)
        or workspace_generation < 0
        or not isinstance(semantic_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", semantic_hash) is None
    ):
        raise StrategySetupError(
            "Independent sample returned for validation.dataset/workspace/semantic identity Incomplete."
        )

    try:
        resolve_pool_requirements(
            read_runtime,
            task_id=task.id,
            compiled_design=pool.compiled_design,
            sample_design=sample,
        )
    except StrategyError as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_pool_validation_requirement_invalid",
            "CurrentStrategy Pool The model rating requires that it cannot be bound to precision"
            "StrategySampleDesign V2;Please recreate the rating evidence or candidate.",
        ) from exc

    snapshot = pool.pool
    try:
        pool_ref = {
            "artifact_id": pool.artifact_id,
            "expected_artifact_content_hash": pool.artifact_content_hash,
            "expected_pool_id": snapshot["pool_id"],
            "expected_revision": snapshot["revision"],
            "expected_revision_id": snapshot["revision_id"],
            "expected_snapshot_hash": snapshot["snapshot_hash"],
        }
        sample_ref = _strategy_report_sample_ref(sample)
    except (AttributeError, KeyError, TypeError) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_pool_validation_binding_invalid",
            "Strategy Pool orStrategySampleDesign V2 The precise reference is incomplete.",
        ) from exc
    return {
        "strategy_type": strategy_type,
        "partition": partition,
        "pool_ref": pool_ref,
        "sample_design_ref": sample_ref,
        "population": "risk",
        "comparison_mode": "absolute",
    }

def _strategy_pool_stability_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict[str, object]:
    """Freeze one current Pool and all usable comparison partitions once."""

    if draft.workflow != "strategy_pool_stability":
        raise StrategySetupError(
            "Strategy Pool stability slots We got the wrong one.Workflow."
        )
    strategy_type = draft.workflow_inputs.get("strategy_type")
    impact_draft = StandardWorkflowRequestDraft(
        workflow="strategy_impact_cube",
        workflow_inputs={"strategy_type": strategy_type},
    )
    impact_slots = _strategy_impact_cube_plan_slots(
        runtime,
        task,
        impact_draft,
        fixed_dimension_bindings={
            "month_col": None,
            "group_col": None,
            "segment_col": None,
        },
        include_optional_context=False,
    )
    partitions = impact_slots["partitions"]
    if (
        not isinstance(partitions, list)
        or "development" not in partitions
        or not any(
            partition in partitions for partition in ("validation", "oot")
        )
    ):
        raise _StrategyV2EvidenceSetupError(
            "strategy_pool_stability_comparison_required",
            "Pool Cross-zonal stability requires non-emptiness.development Baseline and at least one"
            "Non-emptyvalidation orOOT Comparative partitions; please refine the sample design first.",
        )
    return {
        "strategy_type": impact_slots["strategy_type"],
        "pool_ref": impact_slots["pool_ref"],
        "sample_design_ref": impact_slots["sample_design_ref"],
        "partitions": partitions,
    }

def _strategy_impact_cube_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
    *,
    expected_sample_binding: Mapping | None = None,
    fixed_dimension_bindings: Mapping[str, str | None] | None = None,
    include_optional_context: bool = True,
) -> dict[str, object]:
    """Bind one ImpactCube plan to a single authenticated evidence snapshot."""

    if draft.workflow != "strategy_impact_cube":
        raise StrategySetupError(
            "Strategy ImpactCube slots We got the wrong one.Workflow."
        )
    inputs = draft.to_dict()["workflow_inputs"]
    strategy_type = inputs.get("strategy_type")
    if strategy_type not in {
        "approval",
        "reject",
        "limit",
        "pricing",
        "segmentation",
    }:
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_type_invalid",
            "Harmonization of impact measurement needs to be clearapproval,reject,limit,pricing or"
            "segmentation Strategy Pool.",
        )

    read_runtime = _strategy_v2_read_runtime(runtime)
    try:
        artifacts = tuple(read_runtime.task_artifacts.list_for_task(task.id))
    except _STRATEGY_V2_ARTIFACT_ERRORS as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_registry_unavailable",
            "Could not read current taskImpactCube source artifact registry.",
        ) from exc
    try:
        sample = _latest_verified_strategy_sample_design_v2_binding(
            read_runtime,
            task_id=task.id,
            artifacts=artifacts,
        )
    except _StrategyV2EvidenceSetupError as exc:
        code = (
            "strategy_impact_cube_sample_required"
            if exc.code.endswith("_sample_required")
            else "strategy_impact_cube_sample_invalid"
        )
        raise _StrategyV2EvidenceSetupError(
            code,
            "ImpactCube The most up-to-date and complete authentication is requiredStrategySampleDesign V2 "
            "Two-total sample evidence; the platform does not retreat to the old sample.",
        ) from exc

    actual_sample_binding = {
        "kind": "strategy_sample_design_v2",
        "sample_design_ref": _strategy_report_sample_ref(sample),
        "dataset_id": sample.source_binding.dataset_id,
        "dataset_content_hash": sample.source_binding.dataset_content_hash,
    }
    if (
        expected_sample_binding is not None
        and dict(expected_sample_binding) != actual_sample_binding
    ):
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_sample_changed",
            "StrategySampleDesign V2 Changes between requests for translation and planned creation;"
            "No plans are created this time, please re-describe based on the latest sample.",
        )

    pool_repository = StrategyCandidatePoolRepository(runtime.settings.db_path)
    try:
        current_pool = pool_repository.get_current(task.id, strategy_type)
    except Exception as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_pool_invalid",
            f"Current{strategy_type} Strategy Pool head/revision No integrity review was possible.",
        ) from exc
    if current_pool is None or not _strategy_pool_entries(current_pool):
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_pool_required",
            f"Current task is not empty{strategy_type} Strategy Pool;"
            "Please add your candidacy to the list in your natural language.Pool.",
        )
    try:
        pool_revision = int(current_pool["revision"])
        pool_snapshot_hash = strategy_pool_snapshot_hash(current_pool)
        pool = load_current_strategy_candidate_pool_artifact(
            read_runtime,
            task_id=task.id,
            strategy_type=strategy_type,
            expected_pool_revision=pool_revision,
            expected_pool_snapshot_hash=pool_snapshot_hash,
        )
    except (StrategyError, *_STRATEGY_V2_ARTIFACT_ERRORS) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_pool_invalid",
            f"Current{strategy_type} Strategy Pool It's...artifact,Source, compilation results"
            "orlineage Not fully certified.",
        ) from exc
    if pool.compiled_design.get("requirements"):
        try:
            resolve_pool_requirements(
                read_runtime,
                task_id=task.id,
                compiled_design=pool.compiled_design,
                sample_design=sample,
            )
        except StrategyError as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_impact_cube_pool_requirement_invalid",
                "CurrentStrategy Pool The model rating requires that it cannot be tied to the latest."
                "StrategySampleDesign V2;Please recreate the rating evidence or candidate.",
            ) from exc
    if pool.artifact_id not in {
        item.get("id") for item in artifacts
    }:
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_registry_changed",
            "Strategy Pool artifact Change during the selection of evidence; please retest this test.",
        )

    partitions = _strategy_impact_cube_partitions(inputs, sample=sample)
    dimensions = (
        _strategy_impact_cube_dimensions(inputs, sample=sample)
        if fixed_dimension_bindings is None
        else dict(fixed_dimension_bindings)
    )
    economics_inputs = (
        _strategy_impact_cube_economics(
            inputs.get("economics_inputs"),
            sample=sample,
        )
        if include_optional_context
        else None
    )
    current_strategy_ref = (
        _strategy_impact_cube_current_strategy_ref(
            runtime,
            task_id=task.id,
            strategy_type=strategy_type,
            requested_id=inputs.get("current_strategy_id"),
        )
        if include_optional_context
        else None
    )

    selected_artifact_ids = {
        pool.artifact_id,
        sample.membership_artifact_id,
        sample.bundle_artifact_id,
    }
    registry_token = _strategy_impact_cube_registry_token(
        artifacts,
        selected_artifact_ids=selected_artifact_ids,
    )
    try:
        refreshed_artifacts = tuple(
            read_runtime.task_artifacts.list_for_task(task.id)
        )
        refreshed_pool = pool_repository.get_current(task.id, strategy_type)
    except Exception as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_registry_changed",
            "ImpactCube source registry orStrategy Pool head Before Plan Create"
            "Could not check again; no plan is created this time.",
        ) from exc
    if (
        _strategy_impact_cube_registry_token(
            refreshed_artifacts,
            selected_artifact_ids=selected_artifact_ids,
        )
        != registry_token
        or refreshed_pool is None
        or refreshed_pool.get("revision") != pool_revision
        or strategy_pool_snapshot_hash(refreshed_pool) != pool_snapshot_hash
    ):
        raise _StrategyV2EvidenceSetupError(
            "strategy_impact_cube_registry_changed",
            "StrategySampleDesign V2,Strategy Pool orartifact registry "
            "Change before the plan is created; please retest based on the latest evidence.",
        )
    if current_strategy_ref is not None:
        refreshed_current = _strategy_impact_cube_current_strategy_ref(
            runtime,
            task_id=task.id,
            strategy_type=strategy_type,
            requested_id=current_strategy_ref["strategy_id"],
        )
        if refreshed_current != current_strategy_ref:
            raise _StrategyV2EvidenceSetupError(
                "strategy_impact_cube_current_strategy_changed",
                "Current policycanonical StrategySpec Changes before the plan is created;"
                "No plans are created this time.",
            )

    return {
        "strategy_type": strategy_type,
        "pool_ref": {
            "artifact_id": pool.artifact_id,
            "expected_artifact_content_hash": pool.artifact_content_hash,
            "expected_pool_id": pool.pool["pool_id"],
            "expected_revision": pool.pool["revision"],
            "expected_revision_id": pool.pool["revision_id"],
            "expected_snapshot_hash": pool.pool["snapshot_hash"],
        },
        "sample_design_ref": _strategy_report_sample_ref(sample),
        "partitions": partitions,
        # ImpactCube owns both approval and risk denominators internally; this
        # retained v1 selector states which observed-outcome population supplies
        # risk metrics and cannot be supplied by the language model.
        "population": "risk",
        "dimension_bindings": dimensions,
        "current_strategy_ref": current_strategy_ref,
        "economics_inputs": economics_inputs,
    }

def _strategy_dsl_delivery_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
    *,
    context,
) -> dict[str, object]:
    """Bind one offline delivery to exact strategy and dataset snapshots."""

    if draft.workflow != "strategy_dsl_delivery":
        raise StrategySetupError(
            "Strategy DSL delivery slots We got the wrong one.Workflow."
        )
    requested_id = draft.to_dict()["workflow_inputs"].get("strategy_id")
    repository = StrategyRepository(runtime.settings.db_path)

    if requested_id is None:
        try:
            candidate_ids = [
                str(meta["id"])
                for meta in repository.list_meta_for_task(task.id)
                if isinstance(meta.get("id"), str)
            ]
        except Exception as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_dsl_delivery_registry_unavailable",
                "Could not read the strategy registration form for the current task, no delivery plan created.",
            ) from exc
        eligible: list[tuple[str, dict, dict[str, object]]] = []
        for strategy_id in candidate_ids:
            try:
                snapshot = repository.get_strategy_snapshot(strategy_id)
                strategy_ref = _strategy_dsl_delivery_strategy_ref(
                    snapshot,
                    task_id=task.id,
                )
            except (
                StrategyError,
                sqlite3.Error,
                TypeError,
                ValueError,
                _StrategyV2EvidenceSetupError,
            ):
                continue
            eligible.append((strategy_id, snapshot, strategy_ref))
        if not eligible:
            raise _StrategyV2EvidenceSetupError(
                "strategy_dsl_delivery_strategy_required",
                "No current task is deliverablescanonical Strategy;Please complete the strategy first.",
            )
        if len(eligible) != 1:
            raise _StrategyV2EvidenceSetupError(
                "strategy_dsl_delivery_strategy_ambiguous",
                "The current task has multiple deliverables, please specify the complete in the export commandstrategy_id.",
            )
        strategy_id, snapshot, strategy_ref = eligible[0]
    else:
        strategy_id = str(requested_id)
        try:
            snapshot = repository.get_strategy_snapshot(strategy_id)
        except Exception as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_dsl_delivery_strategy_invalid",
                "The strategy cannot be reviewed through the integrity of the current mandate.",
            ) from exc
        strategy_ref = _strategy_dsl_delivery_strategy_ref(
            snapshot,
            task_id=task.id,
        )

    dataset_id = getattr(context, "dataset_id", None)
    dataset_hash = getattr(context, "dataset_content_hash", None)
    workspace_revision = getattr(context, "workspace_revision", None)
    workspace_generation = getattr(context, "analysis_generation", None)
    semantic_mapping_hash = getattr(context, "semantic_mapping_hash", None)
    if (
        not isinstance(dataset_id, str)
        or not dataset_id
        or not isinstance(dataset_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", dataset_hash) is None
        or isinstance(workspace_revision, bool)
        or not isinstance(workspace_revision, int)
        or workspace_revision < 0
        or isinstance(workspace_generation, bool)
        or not isinstance(workspace_generation, int)
        or workspace_generation < 0
        or not isinstance(semantic_mapping_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", semantic_mapping_hash) is None
    ):
        raise _StrategyV2EvidenceSetupError(
            "strategy_dsl_delivery_dataset_invalid",
            "Current policy sample is not certifieddataset/workspace identity.",
        )
    try:
        workspace = DataWorkspaceRepository(
            runtime.settings.db_path
        ).get_or_default(task.id)
    except (
        DataWorkspaceDataError,
        KeyError,
        sqlite3.Error,
        TypeError,
        ValueError,
    ) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_dsl_delivery_dataset_invalid",
            "CurrentDataWorkspace No integrity review was possible.",
        ) from exc
    if (
        workspace.revision != workspace_revision
        or workspace.analysis_generation != workspace_generation
        or data_semantic_mapping_hash(workspace.semantic_mapping)
        != semantic_mapping_hash
        or (
            workspace.active_dataset_id is not None
            and (
                workspace.active_dataset_id != dataset_id
                or workspace.active_dataset_content_hash != dataset_hash
            )
        )
    ):
        raise _StrategyV2EvidenceSetupError(
            "strategy_dsl_delivery_dataset_invalid",
            "Current activityDataWorkspace Not consistent with the context of the data confirmed.",
        )
    workspace_ref = {
        "revision": workspace_revision,
        "analysis_generation": workspace_generation,
        "semantic_mapping_hash": semantic_mapping_hash,
        "active_dataset_id": workspace.active_dataset_id,
        "active_dataset_content_hash": (
            workspace.active_dataset_content_hash
        ),
    }
    _backend, registry = _modeling_data_runtime(runtime.settings)
    try:
        dataset = registry.get(dataset_id)
        registry.resolve_verified_path(dataset_id)
    except (
        DatasetContentDriftError,
        KeyError,
        OSError,
        sqlite3.Error,
        TypeError,
        ValueError,
    ) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_dsl_delivery_dataset_invalid",
            "The current policy sample is not passedtask ownership,registry or filehash Review.",
        ) from exc
    if (
        str(dataset.task_id) != task.id
        or dataset.content_hash != dataset_hash
    ):
        raise _StrategyV2EvidenceSetupError(
            "strategy_dsl_delivery_dataset_invalid",
            "The current sample of strategy is not part of this task orcontent hash Changed.",
        )
    dataset_ref = {
        "dataset_id": dataset_id,
        "expected_content_hash": dataset_hash,
    }

    # Close the selection window before plan creation. The Tool repeats the
    # same exact-ref checks under its publication transaction.
    try:
        refreshed_snapshot = repository.get_strategy_snapshot(strategy_id)
        refreshed_ref = _strategy_dsl_delivery_strategy_ref(
            refreshed_snapshot,
            task_id=task.id,
        )
        if requested_id is None:
            refreshed_eligible = []
            for meta in repository.list_meta_for_task(task.id):
                candidate_id = meta.get("id")
                if not isinstance(candidate_id, str):
                    continue
                try:
                    candidate_snapshot = repository.get_strategy_snapshot(
                        candidate_id
                    )
                    candidate_ref = _strategy_dsl_delivery_strategy_ref(
                        candidate_snapshot,
                        task_id=task.id,
                    )
                except (
                    StrategyError,
                    sqlite3.Error,
                    TypeError,
                    ValueError,
                    _StrategyV2EvidenceSetupError,
                ):
                    continue
                refreshed_eligible.append((candidate_id, candidate_ref))
        refreshed_dataset = registry.get(dataset_id)
        registry.resolve_verified_path(dataset_id)
        refreshed_workspace = DataWorkspaceRepository(
            runtime.settings.db_path
        ).get_or_default(task.id)
    except (
        DataWorkspaceDataError,
        DatasetContentDriftError,
        KeyError,
        OSError,
        sqlite3.Error,
        TypeError,
        ValueError,
        _StrategyV2EvidenceSetupError,
    ) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_dsl_delivery_binding_changed",
            "The policy or activity data set changes before the plan is created; no delivery plan is created this time.",
        ) from exc
    if (
        refreshed_ref != strategy_ref
        or (
            requested_id is None
            and refreshed_eligible != [(strategy_id, strategy_ref)]
        )
        or refreshed_workspace.revision != workspace_revision
        or refreshed_workspace.analysis_generation != workspace_generation
        or data_semantic_mapping_hash(refreshed_workspace.semantic_mapping)
        != semantic_mapping_hash
        or (
            refreshed_workspace.active_dataset_id is not None
            and (
                refreshed_workspace.active_dataset_id != dataset_id
                or refreshed_workspace.active_dataset_content_hash
                != dataset_hash
            )
        )
        or str(refreshed_dataset.task_id) != task.id
        or refreshed_dataset.content_hash != dataset_hash
    ):
        raise _StrategyV2EvidenceSetupError(
            "strategy_dsl_delivery_binding_changed",
            "The policy or activity data set changes before the plan is created; no delivery plan is created this time.",
        )

    return {
        "strategy_ref": strategy_ref,
        "dataset_ref": dataset_ref,
        "workspace_ref": workspace_ref,
        "maximum_equivalence_rows": MAX_EQUIVALENCE_ROWS,
    }

def _strategy_project_context_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
    *,
    source_message: Mapping | None,
) -> dict:
    if draft.workflow != "strategy_project_context":
        raise StrategySetupError("Project contextslots We got the wrong one.Workflow.")
    try:
        current = StrategyProjectContextRepository(
            runtime.settings.db_path
        ).get_current(task.id)
    except (StrategyProjectContextDataError, KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "Context of the current policy itemrevision Complete verification is not possible, and please repair the evidence for the endurance."
        ) from exc

    if (
        not isinstance(source_message, Mapping)
        or source_message.get("task_id") != task.id
        or source_message.get("role") != "user"
        or (source_message.get("metadata") or {}).get("intent")
        not in {"strategy_request", "strategy_project_context_answer"}
    ):
        raise StrategySetupError(
            "The context of the project must be refreshed by binding a user message that has been permanently completed by the current round; please retransmit the request."
        )
    message_id = source_message.get("id")
    content = source_message.get("content")
    if not isinstance(message_id, str) or not message_id or not isinstance(content, str):
        raise StrategySetupError("The context of the project cannot bind valid user message evidence.")

    inputs = draft.to_dict()["workflow_inputs"]
    new_business = dict(inputs.get("business_context") or {})
    explicit_unavailable = list(inputs.get("explicit_unavailable") or [])
    user_message_ref = {
        "message_id": message_id,
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
    structured_request_sha256 = (source_message.get("metadata") or {}).get(
        "structured_request_sha256"
    )
    if (
        (source_message.get("metadata") or {}).get("request_source") == "manual_ui"
        and not isinstance(structured_request_sha256, str)
    ):
        raise StrategySetupError(
            "Candidate Lab Please resubmit the form if you have no structured user request for binding in the context of the project."
        )
    if isinstance(structured_request_sha256, str):
        expected_structured_sha256 = (
            strategy_project_context_structured_request_sha256(
                as_of=inputs["as_of"],
                scope=inputs.get("scope"),
                business_context=inputs.get("business_context") or {},
                explicit_unavailable=inputs.get("explicit_unavailable") or [],
                external_report_filenames=inputs.get(
                    "external_report_filenames"
                )
                or [],
            )
        )
        if not hmac.compare_digest(
            structured_request_sha256,
            expected_structured_sha256,
        ):
            raise StrategySetupError(
                "Candidate Lab The project context is structured to request a change in binding. Please resubmit the form."
            )
        user_message_ref["structured_request_sha256"] = (
            structured_request_sha256
        )
    return {
        "expected_revision": 0 if current is None else current["revision"],
        "expected_revision_id": (
            None if current is None else current["revision_id"]
        ),
        "expected_state_hash": None if current is None else current["state_hash"],
        "user_message_ref": user_message_ref,
        "as_of": inputs["as_of"],
        "scope": inputs.get("scope"),
        "business_context": new_business,
        "explicit_unavailable": explicit_unavailable,
        "external_report_filenames": list(
            inputs.get("external_report_filenames") or []
        ),
    }

def _model_score_comparison_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    *,
    population: str,
    partition: str,
) -> dict[str, object]:
    """Bind the newest authenticated score evidence for every compatible model.

    Artifact identities, hashes, and the registry CAS never cross the user/API
    boundary.  A newer publication for the same model replaces an older one;
    the newest selected publication must authenticate or the request fails.
    """

    read_runtime = _strategy_report_read_runtime(runtime)
    artifacts = _strategy_v2_artifact_snapshot(
        read_runtime,
        task_id=task.id,
    )
    try:
        registry_token = model_score_comparison_registry_snapshot_token(
            artifacts
        )
    except StrategyError as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_score_comparison_registry_unavailable",
            "Model score comparisonartifact registry snapshot Can not regulate this question.",
        ) from exc
    try:
        sample = _latest_verified_strategy_sample_design_v2_binding(
            read_runtime,
            task_id=task.id,
            artifacts=artifacts,
        )
    except _StrategyV2EvidenceSetupError as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_score_comparison_sample_invalid",
            "Model scores need to be up to date and fully certifiedStrategySampleDesign V2;"
            "The platform will not retreat to the old sample.",
        ) from exc
    score_records = [
        artifact
        for artifact in artifacts
        if artifact.get("kind") == MODEL_SCORE_EVIDENCE_ARTIFACT_KIND
        and artifact.get("origin_tool")
        == MATERIALIZE_MODEL_SCORE_EVIDENCE_V2_ORIGIN_TOOL
    ]
    if not score_records:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_score_comparison_candidates_required",
            "The current task requires at least two model scoring evidence based on the latest sample, which is different and complete.",
        )
    if len(score_records) > MAX_MODEL_EVIDENCE:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_score_comparison_candidate_budget_exceeded",
            f"The number of scoring evidence for the current assignment exceeds the maximum number of individual authentications (in thousands of United States dollars){MAX_MODEL_EVIDENCE}).",
        )

    newest_by_model: dict[str, object] = {}
    for artifact in score_records:
        provenance = artifact.get("provenance")
        if not isinstance(provenance, Mapping):
            raise _StrategyV2EvidenceSetupError(
                "strategy_model_score_comparison_evidence_invalid",
                "A model rating evidence is incompleteprovenance;The platform does not speculate about its origin.",
            )
        request = {
            "evidence_artifact_id": artifact.get("id"),
            "expected_evidence_artifact_content_hash": artifact.get(
                "content_hash"
            ),
            "score_vector_artifact_id": provenance.get(
                "score_vector_artifact_id"
            ),
            "expected_score_vector_artifact_content_hash": provenance.get(
                "score_vector_artifact_content_hash"
            ),
        }
        try:
            binding = load_historical_model_score_evidence_artifacts(
                read_runtime,
                task_id=task.id,
                **request,
            )
        except (
            ModelingError,
            OSError,
            KeyError,
            TypeError,
            ValueError,
            *_STRATEGY_V2_ARTIFACT_ERRORS,
        ) as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_model_score_comparison_evidence_invalid",
                "The latest compatible model rating evidence was not documented,hash,registry,Model or"
                "Score vector complete authentication; platform does not retreat to old version.",
            ) from exc
        if (
            binding.task_id != task.id
            or binding.training.task_id != task.id
            or binding.training.sample.task_id != task.id
        ):
            raise _StrategyV2EvidenceSetupError(
                "strategy_model_score_comparison_evidence_incompatible",
                "Model scoring evidence is not part of the current task.",
            )
        if binding.training.sample.bundle != sample.bundle:
            continue
        model_id = binding.training.model_artifact.id
        if not isinstance(model_id, str) or not model_id:
            raise _StrategyV2EvidenceSetupError(
                "strategy_model_score_comparison_evidence_invalid",
                "A matching score is not fully certifiedmodel identity.",
            )
        newest_by_model[model_id] = binding

    if len(newest_by_model) < 2:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_score_comparison_candidates_required",
            "The current task requires at least two model scoring evidence based on the latest sample, which is different and complete.",
        )
    bindings = list(newest_by_model.values())
    refs: list[dict[str, str]] = []
    for binding in bindings:
        refs.append(
            {
                "evidence_artifact_id": binding.evidence_record["id"],
                "expected_evidence_artifact_content_hash": (
                    binding.evidence_record["content_hash"]
                ),
                "score_vector_artifact_id": binding.vector_record["id"],
                "expected_score_vector_artifact_content_hash": (
                    binding.vector_record["content_hash"]
                ),
            }
        )

    try:
        comparison = build_model_score_comparison(
            sample_design_bundle=sample.bundle,
            model_evidence=[
                binding.envelope["single_model_evidence"]
                for binding in bindings
            ],
            population=population,
            partition=partition,
        )
    except (ModelScoreEvidenceComparisonError, StrategyError, TypeError, ValueError) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_score_comparison_candidates_incompatible",
            "The certified model rating evidence does not allow the same comparable indicator to be developed in the selected total and subdivisions;"
            "No plans are created this time.",
        ) from exc
    if comparison.get("selection", {}).get("status") != "no_selection":
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_score_comparison_selection_forbidden",
            "The model rating comparison pre-screened the results; the platform has refused to create the plan.",
        )

    refreshed = _strategy_v2_artifact_snapshot(
        read_runtime,
        task_id=task.id,
    )
    try:
        refreshed_token = model_score_comparison_registry_snapshot_token(
            refreshed
        )
    except StrategyError as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_score_comparison_registry_unavailable",
            "Model score comparisonartifact registry snapshot Can not regulate this question.",
        ) from exc
    if refreshed_token != registry_token:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_score_comparison_registry_changed",
            "Model score evidence orStrategySampleDesign registry Changes before the plan is created;"
            "Please try again on the basis of the latest evidence.",
        )
    return {
        "sample_design_ref": _strategy_report_sample_ref(sample),
        "model_score_evidence_refs": refs,
        "expected_registry_token": registry_token,
    }

def _strategy_model_evidence_v2_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    *,
    verify_current: bool = False,
) -> dict[str, object]:
    """Discover and live-authenticate task-owned V2 sample/candidate evidence."""

    read_runtime = _strategy_v2_read_runtime(runtime)
    artifacts = _strategy_v2_artifact_snapshot(
        read_runtime,
        task_id=task.id,
    )
    registry_token = _strategy_v2_registry_token(artifacts)
    sample_binding = _latest_verified_strategy_sample_design_v2_binding(
        read_runtime,
        task_id=task.id,
        artifacts=artifacts,
    )
    design = sample_binding.bundle["sample_design"]
    identity = design["identity"]
    dataset_ref = identity["dataset_ref"]
    workspace_ref = identity["workspace_ref"]
    expected_candidate_ref = (
        derive_strategy_model_evidence_candidate_execution_ref(sample_binding)
    )
    candidate_requests: list[dict[str, str]] = []
    for artifact in artifacts:
        provenance = artifact.get("provenance")
        if (
            artifact.get("kind") != "strategy_candidate_json"
            or artifact.get("origin_tool")
            != "strategy.analyze_univariate_candidates"
            or not isinstance(provenance, Mapping)
        ):
            continue
        generation = provenance.get("generation_parameters")
        if (
            provenance.get("dataset_id") != dataset_ref["dataset_id"]
            or provenance.get("dataset_content_hash") != dataset_ref["content_hash"]
            or provenance.get("workspace_revision") != workspace_ref["revision"]
            or provenance.get("workspace_generation") != workspace_ref["generation"]
            or provenance.get("semantic_mapping_hash")
            != workspace_ref["semantic_mapping_hash"]
        ):
            continue
        if not isinstance(generation, Mapping):
            raise _StrategyV2EvidenceSetupError(
                "strategy_model_evidence_v2_candidate_invalid",
                "One of the latest.StrategySampleDesign V2 A single variable candidate for a snapshot"
                "Missing completenessgeneration provenance;No plans are created this time.",
            )
        try:
            source_execution_ref = StrategyRiskDevelopmentRef.from_value(
                generation.get("sample_design_ref")
            ).to_ref_dict()
        except StrategyError as exc:
            raise _StrategyV2EvidenceSetupError(
                "strategy_model_evidence_v2_candidate_invalid",
                "One of the latest.StrategySampleDesign V2 A single variable candidate for a snapshot"
                "Include damaged or incompletesample_design_ref;No plans are created this time.",
            ) from exc
        if source_execution_ref != expected_candidate_ref:
            continue
        request = {
            "artifact_id": artifact.get("id"),
            "expected_artifact_content_hash": artifact.get("content_hash"),
            "expected_candidate_id": provenance.get("candidate_id"),
            "expected_evidence_hash": provenance.get("evidence_hash"),
        }
        if not all(isinstance(value, str) and value for value in request.values()):
            raise _StrategyV2EvidenceSetupError(
                "strategy_model_evidence_v2_candidate_invalid",
                "One of the latest.StrategySampleDesign V2 A single variable candidate for a snapshot"
                "Missingartifact,candidate orevidence ;no plans created this time.",
            )
        candidate_requests.append(request)

    if not candidate_requests:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_evidence_v2_candidate_required",
            "Current mission is not up to dateStrategySampleDesign V2 Strictly compatible and approved"
            " live loader Accredited single variable candidate evidence; start with the single variable analysis.",
        )
    candidate_requests.sort(
        key=lambda item: (item["expected_candidate_id"], item["artifact_id"])
    )
    candidate_ids = [item["expected_candidate_id"] for item in candidate_requests]
    artifact_ids = [item["artifact_id"] for item in candidate_requests]
    if len(set(candidate_ids)) != len(candidate_ids) or len(
        set(artifact_ids)
    ) != len(artifact_ids):
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_evidence_v2_duplicate_sources",
            "There is a duplication of compatible single variable evidencecandidate orartifact (a) Identity;"
            "The platform does not speculate or repeat the aggregation.",
        )
    if len(candidate_requests) > _MAX_UNIVARIATE_SOURCES:
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_evidence_v2_candidate_budget_exceeded",
            "With the latestStrategySampleDesign V2 More candidates for compatible single variables than"
            f"Single global source ceiling (%){_MAX_UNIVARIATE_SOURCES});"
            "Please reduce the candidature first.",
        )
    sample_design_ref = {
        "membership_artifact_id": sample_binding.membership_artifact_id,
        "expected_membership_artifact_content_hash": (
            sample_binding.membership_artifact_content_hash
        ),
        "bundle_artifact_id": sample_binding.bundle_artifact_id,
        "expected_bundle_artifact_content_hash": (
            sample_binding.bundle_artifact_content_hash
        ),
        "expected_bundle_id": sample_binding.bundle["bundle_id"],
        "expected_sample_design_id": design["sample_design_id"],
        "expected_sample_design_content_hash": design["content_hash"],
    }
    try:
        _validate_model_evidence_v2_inputs(
            {
                "sample_design_ref": sample_design_ref,
                "univariate_sources": candidate_requests,
            }
        )
        _load_candidate_sources(
            read_runtime,
            task_id=task.id,
            requests=candidate_requests,
            sample_binding=sample_binding,
        )
    except (StrategyError, *_STRATEGY_V2_ARTIFACT_ERRORS) as exc:
        # Validate and authenticate the entire source set in one batch.  This
        # preserves global count/duplicate/JSON and cumulative file-byte
        # budgets instead of resetting a budget for every candidate.
        raise _StrategyV2EvidenceSetupError(
            "strategy_model_evidence_v2_candidate_invalid",
            "One or more claims and latestStrategySampleDesign V2 Compatible Single Variable Candidates"
            "Failure to adopt global sources budget, documentation,hash,Path,provenance ortask "
            "Title review; no plans created in this case.",
        ) from exc
    if verify_current:
        current_artifacts = _strategy_v2_artifact_snapshot(
            read_runtime,
            task_id=task.id,
        )
        if _strategy_v2_registry_token(current_artifacts) != registry_token:
            raise _StrategyV2EvidenceSetupError(
                "strategy_model_evidence_v2_registry_changed",
                "StrategySampleDesign V2 Or a single variable candidate.registry Before Plan Create"
                "Change; the platform has frozen the creation of this plan, please try again based on the latest evidence.",
            )
    return {
        "sample_design_ref": sample_design_ref,
        "univariate_sources": candidate_requests,
        "expected_registry_token": registry_token,
    }

def _strategy_report_bundle_v2_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
    *,
    source_message: Mapping | None,
) -> dict[str, object]:
    """Bind one report plan to immutable, fully authenticated source refs."""

    inputs = draft.to_dict()["workflow_inputs"]
    read_runtime = _strategy_report_read_runtime(runtime)

    try:
        project_context = load_current_strategy_project_context_artifact(
            read_runtime,
            task_id=task.id,
        )
    except (
        StrategyError,
        StrategyProjectContextDataError,
        *_STRATEGY_V2_ARTIFACT_ERRORS,
    ) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_project_context_invalid",
            "CurrentStrategy ProjectContext Not adoptedhead,artifact,(a) Review of source or completeness of documentation;"
            "Please re-engineer the context of the project.",
        ) from exc
    if project_context is None:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_project_context_required",
            "The current report must be quenched before generating the policy reportStrategy ProjectContext.",
        )

    sample = _strategy_report_latest_sample_binding(
        read_runtime,
        task_id=task.id,
    )
    sample_ref = _strategy_report_sample_ref(sample)
    requested_pool_type = _strategy_report_requested_pool_type(source_message)
    pool = _strategy_report_current_pool_binding(
        read_runtime,
        task_id=task.id,
        requested_type=requested_pool_type,
    )
    candidate_pool_ref = {
        "strategy_type": pool.strategy_type,
        "expected_pool_revision": pool.pool["revision"],
        "expected_pool_snapshot_hash": pool.pool["snapshot_hash"],
        "expected_artifact_id": pool.artifact_id,
        "expected_artifact_content_hash": pool.artifact_content_hash,
    }
    candidate_stability = (
        _strategy_report_latest_candidate_stability_binding(
            read_runtime,
            task_id=task.id,
            sample=sample,
            pool=pool,
        )
    )
    candidate_stability_ref = (
        None
        if candidate_stability is None
        else {
            "artifact_id": candidate_stability.artifact_id,
            "expected_artifact_content_hash": (
                candidate_stability.artifact_content_hash
            ),
            "expected_stability_id": candidate_stability.stability[
                "stability_id"
            ],
            "expected_stability_content_hash": (
                candidate_stability.stability["content_hash"]
            ),
        }
    )
    voting_candidate_search = _strategy_report_latest_voting_search_binding(
        read_runtime,
        task_id=task.id,
        sample=sample,
        sample_ref=sample_ref,
        pool=pool,
    )
    voting_candidate_search_ref = (
        None
        if voting_candidate_search is None
        else {
            "artifact_id": voting_candidate_search.artifact_id,
            "expected_artifact_content_hash": (
                voting_candidate_search.artifact_content_hash
            ),
            "expected_search_id": voting_candidate_search.result["search_id"],
            "expected_search_content_hash": (
                voting_candidate_search.result["content_hash"]
            ),
        }
    )
    cross_candidate_search = _strategy_report_latest_cross_search_binding(
        read_runtime,
        task_id=task.id,
        sample=sample,
    )
    cross_candidate_search_ref = (
        None
        if cross_candidate_search is None
        else {
            "artifact_id": cross_candidate_search.artifact_id,
            "expected_artifact_content_hash": (
                cross_candidate_search.artifact_content_hash
            ),
            "expected_search_id": cross_candidate_search.result["search_id"],
            "expected_search_content_hash": (
                cross_candidate_search.result["content_hash"]
            ),
        }
    )
    cross_rule_search = _strategy_report_latest_cross_rule_search_binding(
        read_runtime,
        task_id=task.id,
        sample=sample,
    )
    cross_rule_search_ref = (
        None
        if cross_rule_search is None
        else {
            "artifact_id": cross_rule_search.artifact_id,
            "expected_artifact_content_hash": (
                cross_rule_search.artifact_content_hash
            ),
            "expected_search_id": cross_rule_search.result["search_id"],
            "expected_search_content_hash": (
                cross_rule_search.result["content_hash"]
            ),
        }
    )
    impact_cube = _strategy_report_latest_impact_cube_binding(
        read_runtime,
        task_id=task.id,
        pool=pool,
        sample_ref=sample_ref,
    )
    impact_cube_ref = (
        None
        if impact_cube is None
        else {
            "artifact_id": impact_cube.artifact_id,
            "expected_artifact_content_hash": (
                impact_cube.artifact_content_hash
            ),
            "expected_cube_id": impact_cube.cube["cube_id"],
            "expected_cube_content_hash": impact_cube.cube["content_hash"],
        }
    )
    pool_stability = (
        None
        if impact_cube_ref is None
        else _strategy_report_latest_pool_stability_binding(
            read_runtime,
            task_id=task.id,
            impact_cube_ref=impact_cube_ref,
        )
    )
    pool_stability_ref = (
        None
        if pool_stability is None
        else {
            "artifact_id": pool_stability.artifact_id,
            "expected_artifact_content_hash": (
                pool_stability.artifact_content_hash
            ),
            "expected_stability_id": pool_stability.stability["stability_id"],
            "expected_stability_content_hash": (
                pool_stability.stability["content_hash"]
            ),
        }
    )
    impact = None
    pool_impact_ref = None
    if impact_cube is None:
        if pool.strategy_type not in {"approval", "reject"}:
            raise _StrategyV2EvidenceSetupError(
                "strategy_report_bundle_v2_impact_cube_required",
                f"Current{pool.strategy_type} Strategy Pool No, it's not the same.revision,"
                "snapshot andSampleDesign It's...ImpactCube;This strategy type is not allowed"
                "Back to oldPoolImpact,Please finish this alone.ImpactCube Measure.",
            )
        impact = _strategy_report_latest_pool_impact_binding(
            read_runtime,
            task_id=task.id,
            pool=pool,
        )
        pool_impact_ref = {
            "artifact_id": impact.artifact_id,
            "expected_artifact_content_hash": impact.artifact_content_hash,
            "expected_assessment_id": impact.assessment["assessment_id"],
            "expected_assessment_content_hash": impact.assessment[
                "content_hash"
            ],
        }

    try:
        pool_validation_refs = (
            select_latest_strategy_pool_validation_refs(
                read_runtime,
                task_id=task.id,
                candidate_pool=pool,
                sample_design=sample,
            )
        )
        pool_validations = load_strategy_pool_validation_artifacts(
            read_runtime,
            task_id=task.id,
            refs=pool_validation_refs,
            candidate_pool=pool,
            sample_design=sample,
        )
    except (StrategyError, *_STRATEGY_V2_ARTIFACT_ERRORS) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_pool_validation_invalid",
            "CurrentStrategy Pool The independent sample was not confirmed.exact ref,"
            "Review of source or document integrity; no plans to create this.",
        ) from exc

    model_evidence, model_evidence_ref = (
        _strategy_report_optional_model_evidence(
            read_runtime,
            task_id=task.id,
            sample_ref=sample_ref,
        )
    )
    training_evidence, training_evidence_ref = (
        _strategy_report_optional_training_evidence(
            read_runtime,
            task_id=task.id,
            sample_ref=sample_ref,
        )
    )
    score_evidence, score_evidence_ref = _strategy_report_optional_score_evidence(
        read_runtime,
        task_id=task.id,
        sample_ref=sample_ref,
        training_ref=training_evidence_ref,
    )

    strategy_identity = _strategy_report_identity(
        runtime,
        task_id=task.id,
        candidate_pool=pool,
    )
    strategy_id = (
        None if strategy_identity is None else strategy_identity["strategy_id"]
    )
    try:
        head = StrategyReportRepository(runtime.settings.db_path).get_head(
            task_id=task.id,
            strategy_id=strategy_id,
        )
    except Exception as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_head_invalid",
            "Current strategy reporthead/CAS No integrity review was possible; no plan was created for this time.",
        ) from exc

    # Reuse the report adapter as the final cross-source preflight.  It proves
    # that the selected PoolImpact belongs to this exact Pool and V2
    # risk/development sample, and that every optional model chain matches the
    # same SampleDesign.
    try:
        build_strategy_report_bundle_source_inputs(
            project_context=project_context,
            sample_design=sample,
            candidate_pool=pool,
            pool_validations=pool_validations,
            candidate_stability=candidate_stability,
            pool_stability=pool_stability,
            voting_candidate_search=voting_candidate_search,
            cross_candidate_search=cross_candidate_search,
            cross_rule_search=cross_rule_search,
            pool_impact=impact,
            impact_cube=impact_cube,
            model_evidence=model_evidence,
            training_evidence=training_evidence,
            score_evidence=score_evidence,
        )
    except (ModelingError, StrategyError, *_STRATEGY_V2_ARTIFACT_ERRORS) as exc:
        raise _StrategyV2EvidenceSetupError(
            "strategy_report_bundle_v2_source_incompatible",
            "CurrentProjectContext,SampleDesign V2,Strategy Pool,"
            "ImpactCube/CompatibilityPoolImpact Or the alternative model evidence is not the same."
            "Authible chain of evidence; no plans created this time.",
        ) from exc

    return {
        "title": inputs["title"],
        "status": inputs["status"],
        "project_context_ref": {
            "artifact_id": project_context.artifact_id,
            "expected_artifact_content_hash": (
                project_context.artifact_content_hash
            ),
            "expected_revision": project_context.revision["revision"],
            "expected_revision_id": project_context.revision["revision_id"],
            "expected_state_hash": project_context.revision["state_hash"],
        },
        "sample_design_ref": sample_ref,
        "candidate_pool_ref": candidate_pool_ref,
        "pool_validation_refs": list(pool_validation_refs),
        "candidate_stability_ref": candidate_stability_ref,
        "pool_stability_ref": pool_stability_ref,
        "voting_candidate_search_ref": voting_candidate_search_ref,
        "cross_candidate_search_ref": cross_candidate_search_ref,
        "cross_rule_search_ref": cross_rule_search_ref,
        "pool_impact_ref": pool_impact_ref,
        "impact_cube_ref": impact_cube_ref,
        "report_revision": int(head["current_revision"]) + 1,
        "previous_report_id": head["current_report_id"],
        "previous_report_content_hash": head["current_content_hash"],
        "generated_at": datetime.now(UTC).isoformat(),
        "strategy_identity": strategy_identity,
        "model_evidence_ref": model_evidence_ref,
        "training_evidence_ref": training_evidence_ref,
        "score_evidence_ref": score_evidence_ref,
    }

def _strategy_pool_impact_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
    *,
    context,
    drop_nan_labels: bool,
    expected_pool_binding: Mapping | None = None,
) -> dict[str, object]:
    """Bind one read-only impact request to exact Pool and workspace evidence."""

    inputs = draft.to_dict()["workflow_inputs"]
    strategy_type = str(inputs.get("strategy_type") or "")
    pool, pool_binding = _strategy_pool_impact_pool_binding(
        runtime,
        task,
        strategy_type,
    )
    if expected_pool_binding is not None and dict(expected_pool_binding) != pool_binding:
        raise StrategySetupError(
            "Strategy Pool Changed during user confirmation; old confirmations do not bind newPool revision,"
            "Please base on currentPool Re-launching impact measurements."
        )
    entries = _strategy_pool_entries(pool)

    try:
        workspace = DataWorkspaceRepository(
            runtime.settings.db_path
        ).get_or_default(task.id)
    except (DataWorkspaceDataError, KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "Strategy Pool Impact measurement requires effective activitiesDataWorkspace."
        ) from exc
    if workspace.active_dataset_id is None:
        raise StrategySetupError(
            "Strategy Pool Impact measurement requires firstDataWorkspace Select the active data set;"
            "No, not fromsource_dir Or a few samples."
        )
    if (
        workspace.active_dataset_id != context.dataset_id
        or workspace.active_dataset_content_hash != context.dataset_content_hash
    ):
        raise StrategySetupError(
            "ActivitiesDataWorkspace If this is inconsistent with the context of the policy data, re-select the activity data set and try again."
        )
    target_col = workspace.semantic_mapping.target_col
    if (
        not isinstance(target_col, str)
        or not target_col
        or target_col not in context.columns
        or target_col != context.target_col
    ):
        raise StrategySetupError(
            "Strategy Pool Impact measurements are only available.DataWorkspace Dualizedtarget;"
            "Not usedLLM,Old task field or listing guess."
        )
    content_hash = workspace.active_dataset_content_hash
    semantic_hash = data_semantic_mapping_hash(workspace.semantic_mapping)
    if not isinstance(content_hash, str) or not content_hash:
        raise StrategySetupError("Activity data set missing contenthash,Impact measurement cannot be tied.")
    sample_identities: list[dict] = []
    for entry in entries:
        source = entry.get("source")
        evidence_identity = (
            source.get("evidence_identity")
            if isinstance(source, Mapping)
            else None
        )
        if not isinstance(evidence_identity, Mapping):
            raise StrategySetupError(
                "CurrentStrategy Pool The entries lacked a governance sample identity and could not perform impact measurements."
            )
        sample_identities.append(dict(evidence_identity))
    if any(identity != sample_identities[0] for identity in sample_identities[1:]):
        raise StrategySetupError(
            "CurrentStrategy Pool The entries are not from the same governance sample and impact measurements cannot be performed."
        )
    expected_sample = {
        "dataset_id": workspace.active_dataset_id,
        "dataset_content_hash": content_hash,
        "workspace_revision": workspace.revision,
        "workspace_generation": workspace.analysis_generation,
        "semantic_mapping_hash": semantic_hash,
    }
    if any(
        sample_identities[0].get(field) != expected
        for field, expected in expected_sample.items()
    ):
        raise StrategySetupError(
            "Current activityDataWorkspace andStrategy Pool The sample or semantic version that is bound when created is different;"
            "Please cut back to that.Pool , or rebuild candidate/supplier based on current dataPool Then we'll do it."
        )

    comparison_mode = str(inputs.get("comparison_mode") or "absolute")
    slots: dict[str, object] = {
        "strategy_type": strategy_type,
        "expected_pool_revision": pool_binding["expected_pool_revision"],
        "expected_pool_snapshot_hash": pool_binding[
            "expected_pool_snapshot_hash"
        ],
        "dataset_id": workspace.active_dataset_id,
        "expected_dataset_content_hash": content_hash,
        "workspace_revision": workspace.revision,
        "workspace_generation": workspace.analysis_generation,
        "semantic_mapping_hash": semantic_hash,
        "target_col": target_col,
        "comparison_mode": comparison_mode,
        "drop_nan_labels": bool(drop_nan_labels),
    }
    for field, role in (
        ("month_col", "month"),
        ("loan_amount_col", "loan_amount"),
        ("overdue_amount_col", "overdue_amount"),
    ):
        column = _strategy_pool_impact_column(
            inputs,
            field=field,
            role=role,
            columns=tuple(context.columns),
            field_roles=workspace.semantic_mapping.field_roles,
        )
        if column is not None:
            slots[field] = column

    slots["sample_design_ref"] = _latest_matching_strategy_sample_design_ref(
        runtime,
        task,
        context=context,
        drop_nan_labels=bool(drop_nan_labels),
        allow_native_risk_development=True,
        month_col=slots.get("month_col"),
        loan_amount_col=slots.get("loan_amount_col"),
        overdue_amount_col=slots.get("overdue_amount_col"),
    )

    baseline_strategy_id = inputs.get("baseline_strategy_id")
    if comparison_mode == "vs_baseline":
        if not isinstance(baseline_strategy_id, str) or not baseline_strategy_id:
            raise StrategySetupError(
                "The relative baseline measurement requires that the user clearly provide completenessbaseline_strategy_id."
            )
        repository = StrategyRepository(runtime.settings.db_path)
        try:
            baseline_meta = repository.get_strategy_meta(baseline_strategy_id)
            baseline = repository.get_strategy(baseline_strategy_id)
            baseline_hash = repository.get_strategy_spec_hash(baseline_strategy_id)
        except Exception as exc:
            raise StrategySetupError(
                "Baseline strategycanonical StrategySpec Could not close temporary folder: %s"
            ) from exc
        if (
            baseline_meta is None
            or baseline is None
            or baseline.spec is None
            or not isinstance(baseline_hash, str)
            or baseline_meta.get("task_id") != task.id
        ):
            raise StrategySetupError(
                "No with current taskcanonical StrategySpec The government is not going to be able to do anything about it."
                "It is not possible to cross the mandate or compare it with incomplete strategies."
            )
        if (
            baseline_meta.get("strategy_type") != strategy_type
            or baseline.strategy_type != strategy_type
        ):
            raise StrategySetupError(
                "baseline_strategy_id . The current policy typeStrategy Pool Inconsistent."
            )
        slots["baseline_strategy_id"] = baseline_strategy_id
    elif baseline_strategy_id is not None:
        raise StrategySetupError("absolute Impact measurement prohibits bindingbaseline_strategy_id.")
    return slots

def _strategy_pool_plan_slots(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    draft: StandardWorkflowRequestDraft,
) -> dict:
    """Resolve all Pool integrity inputs from task-owned state, never the LLM."""

    inputs = draft.to_dict()["workflow_inputs"]
    strategy_type = str(inputs["strategy_type"])
    try:
        current = StrategyCandidatePoolRepository(
            runtime.settings.db_path
        ).get_current(task.id, strategy_type)
    except Exception as exc:
        raise StrategySetupError(
            "CurrentStrategy Pool The status cannot be verified through completeness. Check the task data first."
        ) from exc

    if current is None:
        expected_revision = ABSENT_POOL_REVISION
        expected_snapshot_hash = ABSENT_POOL_SNAPSHOT_HASH
    else:
        try:
            expected_revision = int(current["revision"])
            expected_snapshot_hash = strategy_pool_snapshot_hash(current)
        except (KeyError, TypeError, ValueError) as exc:
            raise StrategySetupError(
                "CurrentStrategy Pool revision/hash The binding is incomplete and cannot continue."
            ) from exc

    slots: dict = {
        "strategy_type": strategy_type,
        "expected_pool_revision": expected_revision,
        "expected_pool_snapshot_hash": expected_snapshot_hash,
    }
    if "reason" in inputs:
        slots["reason"] = inputs["reason"]

    if draft.workflow == "strategy_pool_add_candidate":
        selection_id = inputs.get("selection_id")
        candidate_asset_id = inputs.get("candidate_asset_id")
        if (selection_id is None) == (candidate_asset_id is None):
            raise StrategySetupError(
                "AddStrategy Pool There must be and only one must be specified.candidate asset ID "
                "or supported precisionselection ID."
            )
        fragment_id: str | None = None
        is_voting_candidate = False
        if selection_id is not None:
            selection_slots, fragment_id = _candidate_selection_artifact_slots(
                runtime,
                task_id=task.id,
                selection_id=str(selection_id),
            )
            slots.update(selection_slots)
        else:
            candidate_slots = _candidate_asset_artifact_slots(
                runtime,
                task_id=task.id,
                asset_id=str(candidate_asset_id),
            )
            is_voting_candidate = (
                candidate_slots.pop("_candidate_asset_type", None) == "voting_n_of_k"
            )
            slots.update(candidate_slots)
        requested_placement = inputs.get("placement_mode")
        if is_voting_candidate:
            if requested_placement not in {
                "before_selected_members",
                "replace_selected_members",
            }:
                raise StrategySetupError(
                    "Voting The selection must be clear before candidates can enter the pool: the retention member is not in compliancen Time."
                    "Subsequent rules (art.before_selected_members),Or byVoting Atomic Substitution"
                    "These members (replace_selected_members)."
                )
            slots["placement_mode"] = requested_placement
        else:
            if requested_placement is not None:
                raise StrategySetupError(
                    "placement_mode Only forVoting Candidatures; general candidates keep additional semantics."
                )
            slots["placement_mode"] = "append"
        slots["default_action"] = inputs["default_action"]
        slots["action"] = inputs["action"]
        if current is not None and current.get("default_action") != inputs["default_action"]:
            raise StrategySetupError(
                "Requestingdefault_action Compare with CurrentStrategy Pool Inconsistencies;"
                "Unable to rewrite silently when adding entriesPool Default action."
            )
        asset_id = slots["expected_asset_id"]
        if current is not None:
            entries = _strategy_pool_entries(current)
            if fragment_id is None and any(
                isinstance(entry.get("source"), Mapping)
                and entry["source"].get("asset_id") == asset_id
                for entry in entries
            ):
                raise StrategySetupError(
                    f"Candidate assets{asset_id} Exists in CurrentStrategy Pool."
                )
            if fragment_id is not None and any(
                isinstance(entry.get("source"), Mapping)
                and entry["source"].get("asset_id") == asset_id
                and entry["source"].get("fragment_id") == fragment_id
                for entry in entries
            ):
                raise StrategySetupError(
                    f"Candidate assets{asset_id} Snippets{fragment_id} "
                    "Exists in CurrentStrategy Pool."
                )
        # The governed Pool kernel owns exact asset/fragment/rule uniqueness.
        # In particular, one automatic tree may contribute multiple distinct
        # leaves, so an asset-id-only preflight would reject valid requests.
        return slots

    if draft.workflow == "strategy_pool_compile":
        if current is None:
            raise StrategySetupError(
                "The current task is not of that type.Strategy Pool,Can not get folder: %s: %s"
            )
        return slots
    if current is None:
        raise StrategySetupError("The current task is not of that type.Strategy Pool,Could not close temporary folder: %s")

    if draft.workflow in {
        "strategy_pool_remove_entry",
        "strategy_pool_set_action",
    }:
        identifier = inputs.get("rule_id") or inputs.get("entry_id")
        slots["rule_id"] = _strategy_pool_rule_id(current, str(identifier))
        if draft.workflow == "strategy_pool_set_action":
            slots["action"] = inputs["action"]
        return slots

    if draft.workflow == "strategy_pool_reorder":
        slots["ordered_rule_ids"] = _strategy_pool_complete_rule_order(
            current,
            inputs["ordered_ids"],
        )
        return slots
    raise StrategySetupError(f"UnconnectedStrategy Pool Workflow:{draft.workflow}")

def _candidate_asset_artifact_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    asset_id: str,
) -> dict[str, str]:
    matches = []
    repository = TaskArtifactRepository(runtime.settings.db_path)
    try:
        artifacts = repository.list_for_task(task_id)
    except Exception as exc:
        raise StrategySetupError(
            "Candidate assets for current assignmentartifact registry It is not readable, it cannot securely bind the source."
        ) from exc
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise StrategySetupError("Candidate assets for current assignmentartifact The recording structure is invalid.")
        provenance = artifact.get("provenance")
        artifact_triple = (artifact.get("kind"), artifact.get("origin_tool"))
        if (
            artifact_triple
            == (
                CROSS_MATRIX_SOURCE_ARTIFACT_KIND,
                CROSS_MATRIX_SOURCE_ARTIFACT_ORIGIN_TOOL,
            )
            and isinstance(provenance, Mapping)
            and provenance.get("schema_version")
            == CROSS_MATRIX_SOURCE_ARTIFACT_SCHEMA_VERSION
            and provenance.get("asset_id") == asset_id
        ):
            raise StrategySetupError(
                "CompleteCross Matrix asset You can't just join in.Strategy Pool;Please be there first."
                "Single round of precise selectionscell,Reusecross-matrix-cell-selection ID Get in the pool."
            )
        supported_triples = {
            (
                "strategy_candidate_asset_json",
                "strategy.refine_univariate_candidate",
            ),
            (VOTING_CANDIDATE_ARTIFACT_KIND, VOTING_CANDIDATE_ORIGIN_TOOL),
        }
        if (
            artifact_triple in supported_triples
            and isinstance(provenance, Mapping)
            and provenance.get("asset_id") == asset_id
        ):
            matches.append(artifact)
    if not matches:
        raise StrategySetupError(
            f"No assets available for the current assignment{asset_id};Please use the complete display of the resultscandidate-asset ID."
        )
    if len(matches) != 1:
        raise StrategySetupError(
            f"Candidate assets{asset_id} Multipleartifact,Currently, it is not possible to safely choose the source."
        )
    artifact = matches[0]
    artifact_id = artifact.get("id")
    content_hash = artifact.get("content_hash")
    path_value = artifact.get("path")
    provenance = artifact.get("provenance")
    asset_hash = provenance.get("asset_hash") if isinstance(provenance, dict) else None
    if (
        not isinstance(artifact_id, str)
        or not artifact_id
        or not isinstance(content_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", content_hash) is None
        or not isinstance(asset_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", asset_hash) is None
        or not isinstance(path_value, str)
        or not path_value
    ):
        raise StrategySetupError(
            f"Candidate assets{asset_id} It's...artifact Complete binding is incomplete, please regenerate."
        )
    if (
        artifact.get("kind") == VOTING_CANDIDATE_ARTIFACT_KIND
        and artifact.get("origin_tool") == VOTING_CANDIDATE_ORIGIN_TOOL
    ):
        try:
            with repository.transaction() as conn:
                verified = load_verified_voting_candidate_artifact_on_connection(
                    conn,
                    tasks_dir=runtime.settings.tasks_dir,
                    task_id=task_id,
                    artifact_id=artifact_id,
                    expected_content_hash=content_hash,
                    expected_asset_id=asset_id,
                    expected_asset_hash=asset_hash,
                )
        except Exception as exc:
            raise StrategySetupError(
                f"Voting Candidate assets{asset_id} I can't pass.artifact The government has already made a statement."
                "Please regenerate."
            ) from exc
        return {
            "source_artifact_id": verified.artifact_id,
            "expected_artifact_content_hash": verified.content_hash,
            "expected_asset_id": verified.asset["asset_id"],
            "expected_asset_hash": verified.asset["asset_hash"],
            "_candidate_asset_type": "voting_n_of_k",
        }
    path = Path(path_value)
    try:
        content = path.read_bytes()
        if sha256_file(path) != content_hash:
            raise StrategySetupError(
                f"Candidate assets{asset_id} It's...artifact Content is drifting, cannot joinStrategy Pool."
            )
        payload = json.loads(content)
        normalized_asset = validate_candidate_asset(payload)
        if canonical_candidate_asset_json(normalized_asset).encode("utf-8") != content:
            raise StrategySetupError(
                f"Candidate assets{asset_id} No, it's not.canonical JSON,I can't.Strategy Pool."
            )
    except StrategySetupError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            f"Candidate assets{asset_id} I can't pass.artifact Verify, please recreate."
        ) from exc
    if (
        normalized_asset.get("asset_id") != asset_id
        or normalized_asset.get("asset_hash") != asset_hash
    ):
        raise StrategySetupError(
            f"Candidate assets{asset_id} andartifact provenance Not consistent. Not possible.Strategy Pool."
        )
    return {
        "source_artifact_id": artifact_id,
        "expected_artifact_content_hash": content_hash,
        "expected_asset_id": asset_id,
        "expected_asset_hash": asset_hash,
        "_candidate_asset_type": "univariate_refinement",
    }

def _automatic_tree_leaf_selection_artifact_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    selection_id: str,
) -> tuple[dict[str, str], str]:
    """Bind one exact selection ID to four verified Pool Tool slots."""

    if re.fullmatch(
        r"automatic-tree-leaf-selection-[0-9a-f]{32}", selection_id
    ) is None:
        raise StrategySetupError(
            "automatic-tree leaf selection ID format invalid;please copy completeselection ID."
        )
    repository = TaskArtifactRepository(runtime.settings.db_path)
    try:
        with repository.transaction() as conn:
            conn.execute("BEGIN")
            rows = conn.execute(
                """
                SELECT id, content_hash, provenance_json
                  FROM task_artifacts
                 WHERE task_id = ? AND kind = ? AND origin_tool = ?
                """,
                (
                    task_id,
                    AUTOMATIC_TREE_LEAF_FRAGMENT_ARTIFACT_KIND,
                    AUTOMATIC_TREE_LEAF_FRAGMENT_ORIGIN_TOOL,
                ),
            ).fetchall()
            matches: list[tuple[object, Mapping]] = []
            for row in rows:
                provenance_json = row["provenance_json"]
                if not isinstance(provenance_json, str):
                    raise StrategySetupError(
                        "Current Taskleaf selection artifact provenance Invalid."
                    )
                try:
                    provenance = json.loads(provenance_json)
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise StrategySetupError(
                        "Current Taskleaf selection artifact provenance Invalid."
                    ) from exc
                if not isinstance(provenance, Mapping):
                    raise StrategySetupError(
                        "Current Taskleaf selection artifact provenance Invalid."
                    )
                if provenance.get("selection_id") == selection_id:
                    matches.append((row, provenance))
            if not matches:
                raise StrategySetupError(
                    f"No current task.automatic-tree leaf selection {selection_id}."
                )
            if len(matches) != 1:
                raise StrategySetupError(
                    f"automatic-tree leaf selection {selection_id} Multiple"
                    "selection artifact,There is no safe binding of sources at this time."
                )
            row, provenance = matches[0]
            verified = (
                load_verified_automatic_tree_leaf_selection_artifact_on_connection(
                    conn,
                    tasks_dir=runtime.settings.tasks_dir,
                    task_id=task_id,
                    artifact_id=row["id"],
                    expected_content_hash=row["content_hash"],
                    expected_asset_id=provenance.get("tree_asset_id"),
                    expected_asset_hash=provenance.get("tree_asset_hash"),
                )
            )
            if verified.selection.get("selection_id") != selection_id:
                raise StrategySetupError(
                    "leaf selection artifact It's...selection ID Not in line with request."
                )
    except StrategySetupError:
        raise
    except Exception as exc:
        raise StrategySetupError(
            f"automatic-tree leaf selection {selection_id} Not adoptedartifact "
            "Complete Verification, Not AddStrategy Pool."
        ) from exc

    tree_asset = verified.selection.get("tree_asset")
    leaf = verified.selection.get("leaf")
    if not isinstance(tree_asset, Mapping) or not isinstance(leaf, Mapping):
        raise StrategySetupError(
            "leaf selection artifact Missing completenesstree/fragment Tie."
        )
    asset_id = tree_asset.get("asset_id")
    asset_hash = tree_asset.get("asset_hash")
    fragment_id = leaf.get("fragment_id")
    if not all(
        isinstance(value, str) and value
        for value in (asset_id, asset_hash, fragment_id)
    ):
        raise StrategySetupError(
            "leaf selection artifact Missing completenesstree/fragment Tie."
        )
    return (
        {
            "source_artifact_id": verified.artifact_id,
            "expected_artifact_content_hash": verified.content_hash,
            "expected_asset_id": asset_id,
            "expected_asset_hash": asset_hash,
        },
        fragment_id,
    )

def _candidate_selection_artifact_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    selection_id: str,
) -> tuple[dict[str, str], str]:
    """Dispatch only between explicitly versioned governed selection types."""

    if re.fullmatch(
        r"automatic-tree-leaf-selection-[0-9a-f]{32}", selection_id
    ) is not None:
        return _automatic_tree_leaf_selection_artifact_slots(
            runtime,
            task_id=task_id,
            selection_id=selection_id,
        )
    if re.fullmatch(
        r"interactive-tree-frontier-group-selection-[0-9a-f]{32}",
        selection_id,
    ) is not None:
        return _interactive_tree_frontier_group_selection_artifact_slots(
            runtime,
            task_id=task_id,
            selection_id=selection_id,
        )
    if re.fullmatch(
        r"interactive-tree-frontier-selection-[0-9a-f]{32}",
        selection_id,
    ) is not None:
        return _interactive_tree_frontier_selection_artifact_slots(
            runtime,
            task_id=task_id,
            selection_id=selection_id,
        )
    if re.fullmatch(
        r"cross-matrix-cell-selection-[0-9a-f]{32}", selection_id
    ) is not None:
        return _cross_matrix_cell_selection_artifact_slots(
            runtime,
            task_id=task_id,
            selection_id=selection_id,
        )
    if re.fullmatch(
        r"scorecard-cutoff-selection-[0-9a-f]{32}", selection_id
    ) is not None:
        return _scorecard_cutoff_selection_artifact_slots(
            runtime,
            task_id=task_id,
            selection_id=selection_id,
        )
    raise StrategySetupError(
        "selection ID format invalid; only complete supportautomatic-tree leaf selection,"
        "interactive-tree frontier group/singleton selection,"
        "Cross Matrix cell selection "
        "orScorecard cutoff selection ID."
    )

def _interactive_tree_frontier_group_selection_artifact_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    selection_id: str,
) -> tuple[dict[str, str], str]:
    """Resolve one task-local frontier OR group to authenticated Pool slots."""

    if re.fullmatch(
        r"interactive-tree-frontier-group-selection-[0-9a-f]{32}",
        selection_id,
    ) is None:
        raise StrategySetupError(
            "interactive-tree frontier group selection ID format is invalid;"
            "Please copy the complete copy.selection ID."
        )
    repository = TaskArtifactRepository(runtime.settings.db_path)
    try:
        with repository.transaction() as conn:
            conn.execute("BEGIN")
            rows = conn.execute(
                """
                SELECT id, content_hash, provenance_json
                  FROM task_artifacts
                 WHERE task_id = ? AND kind = ? AND origin_tool = ?
                """,
                (
                    task_id,
                    INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ARTIFACT_KIND,
                    INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ORIGIN_TOOL,
                ),
            ).fetchall()
            matches: list[tuple[object, Mapping]] = []
            for row in rows:
                provenance_json = row["provenance_json"]
                if not isinstance(provenance_json, str):
                    raise StrategySetupError(
                        "Current Taskinteractive-tree frontier group "
                        "selection artifact provenance Invalid."
                    )
                try:
                    provenance = json.loads(provenance_json)
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise StrategySetupError(
                        "Current Taskinteractive-tree frontier group "
                        "selection artifact provenance Invalid."
                    ) from exc
                if not isinstance(provenance, Mapping):
                    raise StrategySetupError(
                        "Current Taskinteractive-tree frontier group "
                        "selection artifact provenance Invalid."
                    )
                if provenance.get("selection_id") == selection_id:
                    matches.append((row, provenance))
            if not matches:
                raise StrategySetupError(
                    "No current task.interactive-tree frontier group selection "
                    f"{selection_id}."
                )
            if len(matches) != 1:
                raise StrategySetupError(
                    f"interactive-tree frontier group selection {selection_id} "
                    "Multiplegroup selection artifact,There is no safe binding of sources at this time."
                )
            row, provenance = matches[0]
            if provenance.get("schema_version") not in {
                INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ARTIFACT_SCHEMA_VERSION,
                INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ARTIFACT_SCHEMA_VERSION_V2,
            }:
                raise StrategySetupError(
                    "interactive-tree frontier group selection artifact "
                    "schema Invalid."
                )
            semantic_tree_id = provenance.get("semantic_tree_id")
            tree_hash = provenance.get("tree_hash")
            artifact_id = row["id"]
            content_hash = row["content_hash"]
            if (
                not isinstance(artifact_id, str)
                or not artifact_id
                or not isinstance(content_hash, str)
                or re.fullmatch(r"[0-9a-f]{64}", content_hash) is None
                or not isinstance(semantic_tree_id, str)
                or not semantic_tree_id
                or not isinstance(tree_hash, str)
                or re.fullmatch(r"[0-9a-f]{64}", tree_hash) is None
            ):
                raise StrategySetupError(
                    "interactive-tree frontier group selection artifact "
                    "Integrity binding is incomplete."
                )
            verified = (
                load_verified_interactive_tree_frontier_group_selection_artifact_on_connection(
                    conn,
                    runtime=SimpleNamespace(
                        settings=runtime.settings,
                        task_artifacts=repository,
                    ),
                    task_id=task_id,
                    artifact_id=artifact_id,
                    expected_content_hash=content_hash,
                    expected_asset_id=semantic_tree_id,
                    expected_asset_hash=tree_hash,
                )
            )
    except StrategySetupError:
        raise
    except Exception as exc:
        raise StrategySetupError(
            f"interactive-tree frontier group selection {selection_id} Not adopted"
            "selection,revision Parental chain andartifact Complete Verification, Not Add"
            "Strategy Pool."
        ) from exc

    if verified.selection.get("selection_id") != selection_id:
        raise StrategySetupError(
            "interactive-tree frontier group selection ID With authenticationartifact "
            "Inconsistent."
        )
    revision = verified.revision
    ancestry = revision.ancestor_revisions
    try:
        fragment = (
            interactive_tree_frontier_group_selection_to_verified_candidate_fragment(
                verified.selection,
                revision.revision,
                revision.automatic_source.asset,
                selection_artifact_binding=verified.artifact_binding(),
                revision_artifact_binding=revision.builder_binding(),
                parent_revision=ancestry[0] if ancestry else None,
                ancestor_revisions=ancestry[1:],
            )
        )
        pool_source, _rule_id, _execution = verified_fragment_pool_parts(
            fragment
        )
    except (StrategyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "interactive-tree frontier group selection Could not initialise Bonobolive revision "
            "Re-assignedOR fragment,I can't.Strategy Pool."
        ) from exc
    asset_id = pool_source.get("asset_id")
    asset_hash = pool_source.get("asset_hash")
    fragment_id = pool_source.get("fragment_id")
    if (
        asset_id != semantic_tree_id
        or asset_hash != tree_hash
        or not isinstance(fragment_id, str)
        or not fragment_id
    ):
        raise StrategySetupError(
            "interactive-tree frontier group selection It's...revision/fragment "
            "Binding and authenticateartifact Inconsistent."
        )
    return (
        {
            "source_artifact_id": verified.artifact_id,
            "expected_artifact_content_hash": verified.content_hash,
            "expected_asset_id": asset_id,
            "expected_asset_hash": asset_hash,
        },
        fragment_id,
    )

def _interactive_tree_frontier_selection_artifact_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    selection_id: str,
) -> tuple[dict[str, str], str]:
    """Resolve one task-local frontier pointer to authenticated Pool slots."""

    if re.fullmatch(
        r"interactive-tree-frontier-selection-[0-9a-f]{32}",
        selection_id,
    ) is None:
        raise StrategySetupError(
            "interactive-tree frontier selection ID format is invalid;"
            "Please copy the complete copy.selection ID."
        )
    repository = TaskArtifactRepository(runtime.settings.db_path)
    try:
        with repository.transaction() as conn:
            conn.execute("BEGIN")
            rows = conn.execute(
                """
                SELECT id, content_hash, provenance_json
                  FROM task_artifacts
                 WHERE task_id = ? AND kind = ? AND origin_tool = ?
                """,
                (
                    task_id,
                    INTERACTIVE_TREE_FRONTIER_SELECTION_ARTIFACT_KIND,
                    INTERACTIVE_TREE_FRONTIER_SELECTION_ORIGIN_TOOL,
                ),
            ).fetchall()
            matches: list[tuple[object, Mapping]] = []
            for row in rows:
                provenance_json = row["provenance_json"]
                if not isinstance(provenance_json, str):
                    raise StrategySetupError(
                        "Current Taskinteractive-tree frontier selection "
                        "artifact provenance Invalid."
                    )
                try:
                    provenance = json.loads(provenance_json)
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise StrategySetupError(
                        "Current Taskinteractive-tree frontier selection "
                        "artifact provenance Invalid."
                    ) from exc
                if not isinstance(provenance, Mapping):
                    raise StrategySetupError(
                        "Current Taskinteractive-tree frontier selection "
                        "artifact provenance Invalid."
                    )
                if provenance.get("selection_id") == selection_id:
                    matches.append((row, provenance))
            if not matches:
                raise StrategySetupError(
                    "No current task.interactive-tree frontier selection "
                    f"{selection_id}."
                )
            if len(matches) != 1:
                raise StrategySetupError(
                    f"interactive-tree frontier selection {selection_id} "
                    "Multiplefrontier selection artifact,There is no safe binding of sources at this time."
                )
            row, provenance = matches[0]
            if provenance.get("schema_version") not in {
                INTERACTIVE_TREE_FRONTIER_SELECTION_ARTIFACT_SCHEMA_VERSION,
                INTERACTIVE_TREE_FRONTIER_SELECTION_ARTIFACT_SCHEMA_VERSION_V2,
            }:
                raise StrategySetupError(
                    "interactive-tree frontier selection artifact schema Invalid."
                )
            semantic_tree_id = provenance.get("semantic_tree_id")
            tree_hash = provenance.get("tree_hash")
            artifact_id = row["id"]
            content_hash = row["content_hash"]
            if (
                not isinstance(artifact_id, str)
                or not artifact_id
                or not isinstance(content_hash, str)
                or re.fullmatch(r"[0-9a-f]{64}", content_hash) is None
                or not isinstance(semantic_tree_id, str)
                or not semantic_tree_id
                or not isinstance(tree_hash, str)
                or re.fullmatch(r"[0-9a-f]{64}", tree_hash) is None
            ):
                raise StrategySetupError(
                    "interactive-tree frontier selection artifact "
                    "Integrity binding is incomplete."
                )
            verified = (
                load_verified_interactive_tree_frontier_selection_artifact_on_connection(
                    conn,
                    runtime=SimpleNamespace(
                        settings=runtime.settings,
                        task_artifacts=repository,
                    ),
                    task_id=task_id,
                    artifact_id=artifact_id,
                    expected_content_hash=content_hash,
                    expected_asset_id=semantic_tree_id,
                    expected_asset_hash=tree_hash,
                )
            )
    except StrategySetupError:
        raise
    except Exception as exc:
        raise StrategySetupError(
            f"interactive-tree frontier selection {selection_id} Not adopted"
            "selection,revision Parental chain andartifact Complete Verification, Not Add"
            "Strategy Pool."
        ) from exc

    selection = verified.selection
    revision = selection.get("revision")
    frontier = selection.get("frontier")
    if not isinstance(revision, Mapping) or not isinstance(frontier, Mapping):
        raise StrategySetupError(
            "interactive-tree frontier selection Missing completenessrevision/fragment Tie."
        )
    asset_id = revision.get("semantic_tree_id")
    asset_hash = revision.get("tree_hash")
    fragment_id = frontier.get("fragment_id")
    if (
        selection.get("selection_id") != selection_id
        or asset_id != semantic_tree_id
        or asset_hash != tree_hash
        or not isinstance(fragment_id, str)
        or not fragment_id
    ):
        raise StrategySetupError(
            "interactive-tree frontier selection It's...revision/fragment "
            "Binding and authenticateartifact Inconsistent."
        )
    return (
        {
            "source_artifact_id": verified.artifact_id,
            "expected_artifact_content_hash": verified.content_hash,
            "expected_asset_id": asset_id,
            "expected_asset_hash": asset_hash,
        },
        fragment_id,
    )

def _scorecard_cutoff_selection_artifact_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    selection_id: str,
) -> tuple[dict[str, str], str]:
    """Replay one authenticated Scorecard pointer back to its full band."""

    read_runtime = _strategy_report_read_runtime(runtime)
    artifacts = _scorecard_artifact_snapshot(read_runtime, task_id=task_id)
    registry_token = _scorecard_registry_token(artifacts)
    matches = []
    for artifact in artifacts:
        provenance = artifact.get("provenance")
        if (
            artifact.get("kind")
            == SCORECARD_CUTOFF_SELECTION_ARTIFACT_KIND
            and artifact.get("origin_tool")
            == SCORECARD_CUTOFF_SELECTION_ORIGIN_TOOL
            and isinstance(provenance, Mapping)
            and provenance.get("schema_version")
            == SCORECARD_CUTOFF_SELECTION_ARTIFACT_SCHEMA_VERSION
            and provenance.get("selection_id") == selection_id
        ):
            matches.append(artifact)
    if not matches:
        raise StrategySetupError(
            f"No current task.Scorecard cutoff selection {selection_id}."
        )
    if len(matches) != 1:
        raise StrategySetupError(
            f"Scorecard cutoff selection {selection_id} Multipleartifact,"
            "There is no safe binding of sources at this time."
        )
    record = matches[0]
    provenance = record["provenance"]
    assert isinstance(provenance, Mapping)
    artifact_id = _scorecard_ref_hash(
        record.get("id"),
        field="selection_artifact_id",
    )
    content_hash = _scorecard_ref_hash(
        record.get("content_hash"),
        field="selection_artifact_content_hash",
    )
    selection_hash = _scorecard_ref_hash(
        provenance.get("selection_hash"),
        field="selection_hash",
    )
    try:
        verified = load_scorecard_cutoff_selection_artifact(
            read_runtime,
            task_id=task_id,
            artifact_id=artifact_id,
            expected_artifact_content_hash=content_hash,
            expected_selection_id=selection_id,
            expected_selection_hash=selection_hash,
        )
        source = verified.source_asset_binding
        fragment = scorecard_cutoff_selection_to_verified_candidate_fragment(
            verified.selection,
            source.asset,
            selection_artifact_binding=verified.to_domain_binding(),
            source_artifact_binding=source.to_domain_binding(),
        )
        pool_source, _rule_id, _execution = verified_fragment_pool_parts(
            fragment
        )
    except (
        StrategyError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        *_STRATEGY_V2_ARTIFACT_ERRORS,
    ) as exc:
        raise StrategySetupError(
            f"Scorecard cutoff selection {selection_id} Not adoptedselection,"
            "Completeband,score evidence,SampleDesign orfragment Play back,"
            "I can't.Strategy Pool."
        ) from exc
    asset_id = source.asset.get("asset_id")
    asset_hash = source.asset.get("asset_hash")
    fragment_id = pool_source.get("fragment_id")
    if (
        verified.selection.get("selection_id") != selection_id
        or not isinstance(asset_id, str)
        or re.fullmatch(r"scorecard-band-asset-[0-9a-f]{32}", asset_id)
        is None
        or not isinstance(asset_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", asset_hash) is None
        or not isinstance(fragment_id, str)
        or not fragment_id
        or pool_source.get("asset_id") != asset_id
        or pool_source.get("asset_hash") != asset_hash
    ):
        raise StrategySetupError(
            "Scorecard cutoff selection Lack of a consistent completenessband/fragment Tie."
        )
    refreshed = _scorecard_artifact_snapshot(read_runtime, task_id=task_id)
    if _scorecard_registry_token(refreshed) != registry_token:
        raise StrategySetupError(
            "Scorecard cutoff selection Or complete.band Before the pool is created"
            "changes;please base on latestevidence Try again."
        )
    return (
        {
            "source_artifact_id": verified.artifact_id,
            "expected_artifact_content_hash": verified.content_hash,
            "expected_asset_id": asset_id,
            "expected_asset_hash": asset_hash,
        },
        fragment_id,
    )

def _cross_matrix_cell_selection_artifact_slots(
    runtime: DriverTurnRuntime,
    *,
    task_id: str,
    selection_id: str,
) -> tuple[dict[str, str], str]:
    """Bind one exact Cross cell selection to verified Pool Tool inputs."""

    repository = TaskArtifactRepository(runtime.settings.db_path)
    try:
        artifacts = repository.list_for_task(task_id)
    except Exception as exc:
        raise StrategySetupError(
            "Current TaskCross Matrix cell selection registry Can not get message: %s %s"
        ) from exc
    matches = []
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise StrategySetupError(
                "Current TaskCross Matrix cell selection artifact The recording structure is invalid."
            )
        provenance = artifact.get("provenance")
        if (
            artifact.get("kind") == CROSS_MATRIX_CELL_SELECTION_ARTIFACT_KIND
            and artifact.get("origin_tool")
            == CROSS_MATRIX_CELL_SELECTION_ORIGIN_TOOL
            and isinstance(provenance, Mapping)
            and provenance.get("schema_version")
            == CROSS_MATRIX_CELL_SELECTION_ARTIFACT_SCHEMA_VERSION
            and provenance.get("selection_id") == selection_id
        ):
            matches.append(artifact)
    if not matches:
        raise StrategySetupError(
            f"No current task.Cross Matrix cell selection {selection_id}."
        )
    if len(matches) != 1:
        raise StrategySetupError(
            f"Cross Matrix cell selection {selection_id} Multipleartifact,"
            "There is no safe binding of sources at this time."
        )

    artifact = matches[0]
    provenance = artifact.get("provenance")
    assert isinstance(provenance, Mapping)
    artifact_id = artifact.get("id")
    content_hash = artifact.get("content_hash")
    asset_id = provenance.get("source_asset_id")
    asset_hash = provenance.get("source_asset_hash")
    if not all(
        isinstance(value, str) and value
        for value in (artifact_id, content_hash, asset_id, asset_hash)
    ):
        raise StrategySetupError(
            f"Cross Matrix cell selection {selection_id} Complete binding is incomplete."
        )
    try:
        with repository.transaction() as conn:
            verified = (
                load_verified_cross_matrix_cell_selection_artifact_on_connection(
                    conn,
                    tasks_dir=runtime.settings.tasks_dir,
                    task_id=task_id,
                    artifact_id=artifact_id,
                    expected_content_hash=content_hash,
                    expected_asset_id=asset_id,
                    expected_asset_hash=asset_hash,
                )
            )
    except Exception as exc:
        raise StrategySetupError(
            f"Cross Matrix cell selection {selection_id} Not adoptedartifact Integrity"
            "Verify, not allowed.Strategy Pool."
        ) from exc

    selection = verified.selection
    if selection.get("selection_id") != selection_id:
        raise StrategySetupError(
            "Cross Matrix cell selection artifact It's...selection ID Not in line with request."
        )
    source_asset = selection.get("source_asset")
    group_id = selection.get("group_id")
    if not isinstance(source_asset, Mapping) or not all(
        isinstance(value, str) and value
        for value in (
            source_asset.get("asset_id"),
            source_asset.get("asset_hash"),
            group_id,
        )
    ):
        raise StrategySetupError(
            "Cross Matrix cell selection artifact Missing completenessasset/group Tie."
        )
    return (
        {
            "source_artifact_id": verified.artifact_id,
            "expected_artifact_content_hash": verified.content_hash,
            "expected_asset_id": str(source_asset["asset_id"]),
            "expected_asset_hash": str(source_asset["asset_hash"]),
        },
        str(group_id),
    )

def _is_automatic_tree_build_draft(
    draft: CompiledStrategyRequestDraft,
) -> bool:
    return (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "automatic_tree_candidate_build"
    )

def _ensure_automatic_tree_active_workspace(
    runtime: DriverTurnRuntime,
    task: TaskRecord,
    *,
    preview,
    context,
):
    """Bind a fresh task's sole registered sample before governed tree evidence.

    Automatic-tree artifacts deliberately require an active, persisted data
    workspace.  A natural-language build on a fresh task may have just registered
    its sole source sample, so selecting that one unambiguous dataset is normal
    request preparation.  Multiple registered datasets remain a user decision.
    """

    repository = DataWorkspaceRepository(runtime.settings.db_path)
    try:
        snapshot = repository.get_or_default(task.id)
    except (DataWorkspaceDataError, KeyError, TypeError, ValueError) as exc:
        raise StrategySetupError(
            "Automatic trees require a valid data workspace, and please re-select the activity sample first."
        ) from exc
    if snapshot.active_dataset_id is not None:
        if (
            snapshot.active_dataset_id != context.dataset_id
            or snapshot.active_dataset_content_hash != context.dataset_content_hash
        ):
            raise StrategySetupError(
                "Automatic tree samples are not consistent with current activity data sets, and please select the samples clearly in the data area."
            )
        if snapshot.semantic_mapping.target_col != context.target_col:
            raise StrategySetupError(
                "Autotree Target Bar must be in the current data working areatarget Please confirm the semantics.target_col."
            )
        return preview, context

    _backend, registry = _modeling_data_runtime(runtime.settings)
    owned = [
        dataset
        for dataset in registry.list_for_task(task.id)
        if str(dataset.task_id) == task.id
    ]
    if len(owned) != 1 or owned[0].id != context.dataset_id:
        raise StrategySetupError(
            "Automatic trees require a clear sample of activities; there are currently multiple or uncertain data sets,"
            "Please select and save this sample in the data workspace first."
        )
    if not isinstance(context.dataset_content_hash, str) or not context.target_col:
        raise StrategySetupError(
            "Automatic tree cannot bind sample Hash or binary target columns. Please confirm the data andtarget_col."
        )

    try:
        pinned_dataset = registry.pin_authenticated_snapshot(context.dataset_id)
        if pinned_dataset.content_hash != context.dataset_content_hash:
            raise StrategySetupError(
                "The data identity of the automatic tree sample changes before binding, and please reconfirm the sample."
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
                "actor": "agent:strategy-automatic-tree-build",
                "detail": {
                    "reason": "atomically bind sole task sample and target for automatic tree"
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
            "The automatic tree data workspace changes before the plan is created. Please reconfirm the activity sample."
        ) from exc

    refreshed_preview = _strategy_dataset_preview(runtime, task)
    refreshed_context = _strategy_dataset_context(runtime, task, require_target=True)
    return refreshed_preview, refreshed_context

def _typed_strategy_slots(context, draft: StrategyRequestDraft) -> dict:
    slots = {
        "dataset_id": context.dataset_id,
        "target_col": context.target_col,
        "strategy_spec": draft.to_dict()["strategy_spec"],
    }
    if draft.baseline_strategy_id:
        slots["baseline_strategy_id"] = draft.baseline_strategy_id
    if draft.profit is not None:
        profit = dict(draft.profit)
        slots["ead_col"] = profit.pop("ead_col")
        slots["pd_col"] = profit.pop("pd_col")
        slots["profit_params"] = profit
    if draft.economics_inputs is not None:
        slots["economics_inputs"] = dict(draft.economics_inputs)
    return slots

def _is_auto_candidate_draft(draft: CompiledStrategyRequestDraft) -> bool:
    return (
        isinstance(draft, StrategyRequestDraft)
        and draft.operation == "develop"
        and draft.strategy_type in {"limit", "pricing", "segmentation"}
        and draft.candidate_design is not None
    )

def _candidate_strategy_slots(context, draft: StrategyRequestDraft) -> dict:
    slots = {
        "dataset_id": context.dataset_id,
        "target_col": context.target_col,
        "strategy_type": draft.strategy_type,
        # StrategyRequestDraft freezes nested sequences as tuples. Plan/tool
        # inputs are JSON values, so use its public thawed projection instead
        # of only copying the outer mapping.
        "candidate_design": draft.to_dict()["candidate_design"],
    }
    if draft.economics_inputs is not None:
        slots["economics_inputs"] = dict(draft.economics_inputs)
    if draft.baseline_strategy_id:
        slots["baseline_strategy_id"] = draft.baseline_strategy_id
    return slots

def _stored_strategy_slots(context, draft: StrategyRequestDraft) -> dict:
    slots = {
        "dataset_id": context.dataset_id,
        "target_col": context.target_col,
        "strategy_id": draft.strategy_id,
    }
    if draft.baseline_strategy_id:
        slots["baseline_strategy_id"] = draft.baseline_strategy_id
    if draft.adoption_reason:
        slots["adoption_reason"] = draft.adoption_reason
    if draft.profit is not None:
        profit = dict(draft.profit)
        slots["ead_col"] = profit.pop("ead_col")
        slots["pd_col"] = profit.pop("pd_col")
        slots["profit_params"] = profit
    if draft.economics_inputs is not None:
        slots["economics_inputs"] = dict(draft.economics_inputs)
    return slots
