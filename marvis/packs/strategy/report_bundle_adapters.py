"""Pure projections from authenticated V2 evidence into report inputs.

This module intentionally has no persistence or runtime dependency.  Every
input must already be a typed artifact binding produced by a governed loader.
The adapter revalidates the canonical evidence carried by those bindings and
copies only aggregate/structural facts into ``StrategyReportBundle`` fields and
tables.  It never reads raw rows, scores a model, evaluates a rule, or upgrades
development evidence to an independent-validation or production claim.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import hashlib
import json
from pathlib import Path
from typing import Any

from marvis.packs.modeling.evidence import (
    canonical_modeling_training_evidence_json,
    validate_modeling_training_evidence,
)
from marvis.packs.modeling.evidence_tools import (
    ModelingTrainingEvidenceArtifactBinding,
    build_training_evidence_ref,
)
from marvis.packs.modeling.score_evidence import (
    canonical_model_score_evidence_json,
    validate_model_score_evidence_envelope,
)
from marvis.packs.modeling.score_evidence_tools import (
    ModelScoreEvidenceArtifactBinding,
)
from marvis.packs.strategy.candidate_stability import (
    CANDIDATE_STABILITY_PRODUCER_VERSION,
    canonical_candidate_stability_artifact_json,
    validate_candidate_stability_artifact,
)
from marvis.packs.strategy.candidate_stability_tools import (
    ARTIFACT_SCHEMA_VERSION as CANDIDATE_STABILITY_ARTIFACT_SCHEMA_VERSION,
    StrategyCandidateStabilityArtifactBinding,
)
from marvis.packs.strategy.cross_candidate_search import (
    CROSS_CANDIDATE_SEARCH_PRODUCER_VERSION,
    canonical_cross_candidate_search_result_json,
    validate_cross_candidate_search_result,
)
from marvis.packs.strategy.cross_candidate_search_tools import (
    CROSS_CANDIDATE_SEARCH_ARTIFACT_SCHEMA_VERSION,
    CrossCandidateSearchArtifactBinding,
)
from marvis.packs.strategy.cross_rule_search import (
    canonical_cross_rule_search_result_json,
    validate_cross_rule_search_result,
)
from marvis.packs.strategy.cross_rule_search_tools import (
    CrossRuleSearchArtifactBinding,
)
from marvis.packs.strategy.model_evidence import (
    canonical_strategy_model_evidence_bundle_json,
    validate_strategy_model_evidence_bundle,
)
from marvis.packs.strategy.model_evidence_tools import (
    StrategyModelEvidenceV2ArtifactBinding,
)
from marvis.packs.strategy.dsl import strategy_spec_hash
from marvis.packs.strategy.errors import StrategyError
from marvis.packs.strategy.impact_cube_binding import (
    StrategyImpactCubeArtifactBinding,
    validate_strategy_impact_cube_artifact_binding as _validate_impact_cube_binding,
)
from marvis.packs.strategy.impact_cube_tools import (
    IMPACT_CUBE_ARTIFACT_SCHEMA_VERSION,
    IMPACT_CUBE_REQUIREMENTS_ARTIFACT_SCHEMA_VERSION,
    impact_cube_producer_run_ref,
)
from marvis.packs.strategy.pool import (
    canonical_strategy_pool_json,
    compile_strategy_pool,
    validate_strategy_pool,
)
from marvis.packs.strategy.pool_impact import (
    canonical_strategy_pool_impact_json,
    validate_strategy_pool_impact_assessment,
)
from marvis.packs.strategy.pool_impact_tools import (
    StrategyPoolImpactArtifactBinding,
)
from marvis.packs.strategy.pool_stability import (
    POOL_STABILITY_PRODUCER_VERSION,
    canonical_strategy_pool_stability_json,
    validate_strategy_pool_stability,
)
from marvis.packs.strategy.pool_stability_tools import (
    POOL_STABILITY_ARTIFACT_KIND,
    POOL_STABILITY_ARTIFACT_SCHEMA_VERSION,
    POOL_STABILITY_ORIGIN_TOOL,
    POOL_STABILITY_PRODUCER_RUN_SCHEMA_VERSION,
    POOL_STABILITY_TOOL_SCHEMA_VERSION,
    StrategyPoolStabilityArtifactBinding,
)
from marvis.packs.strategy.pool_validation import (
    STRATEGY_POOL_VALIDATION_PRODUCER_VERSION,
    canonical_strategy_pool_validation_json,
    validate_strategy_pool_validation_evidence,
)
from marvis.packs.strategy.pool_validation_typed import (
    STRATEGY_POOL_TYPED_VALIDATION_SCHEMA_VERSION,
)
from marvis.packs.strategy.pool_tools import (
    StrategyCandidatePoolArtifactBinding,
    StrategyPoolDevelopmentDatasetBinding,
    StrategyPoolDevelopmentExecutionBinding,
    project_scorecard_report_evidence,
)
from marvis.packs.strategy.pool_validation_tools import (
    POOL_VALIDATION_ARTIFACT_SCHEMA_VERSION,
    POOL_VALIDATION_REQUIREMENTS_ARTIFACT_SCHEMA_VERSION,
    StrategyPoolValidationArtifactBinding,
)
from marvis.packs.strategy.pool_requirement_resolver import (
    ResolvedPoolRequirements,
    normalize_pool_requirements,
    pool_requirement_bindings_provenance,
    validate_pool_requirement_bindings_provenance,
)
from marvis.packs.strategy.project_context import (
    build_report_field,
    build_source_ref,
    canonical_strategy_project_context_revision_json,
    validate_report_field,
    validate_strategy_project_context_revision,
)
from marvis.packs.strategy.project_context_tools import (
    StrategyProjectContextArtifactBinding,
)
from marvis.packs.strategy.report_bundle import (
    REPORT_SECTION_KEYS,
    StrategyReportBundleError,
    build_named_report_field,
    build_strategy_report_section,
    build_strategy_report_table,
)
from marvis.packs.strategy.sample_design_v2 import (
    canonical_strategy_sample_design_v2_bundle_json,
    validate_strategy_sample_design_v2_bundle,
)
from marvis.packs.strategy.sample_design_execution import (
    StrategyRiskDevelopmentExecutionBinding,
    StrategyRiskDevelopmentRef,
)
from marvis.packs.strategy.sample_design_v2_native_tools import (
    StrategySampleDesignV2NativeArtifactBinding,
)
from marvis.packs.strategy.sample_design_v2_tools import (
    StrategySampleDesignV2ArtifactBinding,
    resolve_strategy_sample_design_v2_source_mode,
)
from marvis.packs.strategy.voting_candidate import (
    VOTING_CANDIDATE_ASSET_TYPE,
)
from marvis.packs.strategy.voting_candidate_search import (
    VOTING_CANDIDATE_SEARCH_PRODUCER_VERSION,
    canonical_voting_candidate_search_result_json,
    validate_voting_candidate_search_result,
)
from marvis.packs.strategy.voting_candidate_search_tools import (
    VOTING_CANDIDATE_SEARCH_ARTIFACT_SCHEMA_VERSION,
    VotingCandidateSearchArtifactBinding,
)
from marvis.repositories.task_artifacts import stable_task_artifact_id
from marvis.strategy_lifecycle import resolve_asset_status


_StrategySampleDesignV2Binding = (
    StrategySampleDesignV2ArtifactBinding
    | StrategySampleDesignV2NativeArtifactBinding
)


_MAX_SCORECARD_REPORT_TABLE_FIELDS = 50_000
_MAX_SCORECARD_REPORT_TABLE_REFS = 10_000
_MAX_SCORECARD_REPORT_TABLE_JSON_BYTES = 8 * 1024 * 1024
_MAX_VOTING_SEARCH_REPORT_COMBINATIONS = 20
_VOTING_SEARCH_REPORT_TITLE = (
    "VotingCandidate group search results (developing backspecies, only for selection, not built)/(Uninhabited)"
)
_MAX_CROSS_SEARCH_REPORT_PAIRS = 20
_CROSS_SEARCH_REPORT_TITLE = (
    "CrossCandidate field for search results (developed backspect for explicit selection only, not built)/(Uninhabited)"
)
_MAX_CROSS_RULE_REPORT_RULES = 50
_CROSS_RULE_REPORT_TITLE = (
    "2D/3D CrossThreshold rule search results"
    "(Develop backsights for explicit selection only, not built automatically/(Uninhabited)"
)
_VOTING_SEARCH_PROVENANCE_FIELDS = frozenset(
    {
        "schema_version",
        "producer_version",
        "task_id",
        "search_id",
        "search_content_hash",
        "request_hash",
        "pool_ref",
        "dataset_binding",
        "sample_design_ref",
        "sample_context_hash",
        "target_binding",
        "observation_bindings",
        "requirement_bindings",
        "excluded_unsupported_rule_ids",
        "lifecycle",
    }
)
_VOTING_SEARCH_LIFECYCLE = {
    "mutated_pool": False,
    "selected": False,
    "admitted": False,
    "applied": False,
    "adopted": False,
    "deployed": False,
}
_CROSS_SEARCH_PROVENANCE_FIELDS = frozenset(
    {
        "schema_version",
        "producer_version",
        "task_id",
        "search_id",
        "search_content_hash",
        "request_hash",
        "source_artifact_id",
        "source_artifact_content_hash",
        "candidate_id",
        "evidence_hash",
        "dataset_id",
        "dataset_content_hash",
        "registry_metadata_hash",
        "workspace_revision",
        "workspace_generation",
        "semantic_mapping_hash",
        "sample_design_ref",
        "sample_context_hash",
        "sample_partition",
        "target_col",
        "drop_nan_labels",
        "nan_labels_dropped",
        "labeled_count",
        "features",
        "max_pairs",
        "lifecycle",
    }
)
_CROSS_SEARCH_LIFECYCLE = {
    "selected": False,
    "admitted": False,
    "applied": False,
    "adopted": False,
    "deployed": False,
}


_SECTION_TITLES = {
    "current_project": "Current project status",
    "historical_versions": "Historical version policy effects",
    "sample_design": "This sample design",
    "univariate_and_models": "Single Variables and Model Analysis",
    "candidate_combinations": "Candidate group and strategy design",
    "impact_assessment": "Policy impact measurement",
    "final_document": "Final strategy conclusions",
}
_SAMPLE_STATUS_TO_AVAILABILITY = {
    "present": "present",
    "unavailable": "unavailable",
    "insufficient_data": "unavailable",
    "not_matured": "not_matured",
    "not_applicable": "not_applicable",
}
_MODEL_STATUS_TO_AVAILABILITY = {
    "present": "present",
    "unavailable": "unavailable",
    "not_matured": "not_matured",
    "not_applicable": "not_applicable",
}
_CANDIDATE_STABILITY_PROVENANCE_FIELDS = frozenset(
    {
        "schema_version",
        "producer_version",
        "task_id",
        "stability_id",
        "stability_content_hash",
        "basis",
        "source_kind",
        "source_artifact_id",
        "source_artifact_content_hash",
        "source_id",
        "source_hash",
        "rule_id",
        "entry_id",
        "pool_id",
        "pool_revision",
        "pool_revision_id",
        "dataset_id",
        "dataset_content_hash",
        "workspace_revision",
        "workspace_generation",
        "semantic_mapping_hash",
        "target_col",
        "month_col",
        "sample_design_ref",
        "sample_context_hash",
        "sample_partition",
    }
)
_POOL_VALIDATION_PROVENANCE_FIELDS = frozenset(
    {
        "schema_version",
        "producer_version",
        "task_id",
        "evidence_id",
        "evidence_content_hash",
        "pool_ref",
        "sample_design_ref",
        "dataset_binding",
        "target_binding",
        "field_bindings",
        "partition",
        "population",
        "comparison_mode",
        "lifecycle_stage",
        "validation_status",
    }
)
_CANDIDATE_STABILITY_LIFECYCLE = {
    "candidate_stage": "development",
    "observation_stage": "backtested",
    "validation_status": "unvalidated",
    "not_created_strategy": True,
    "not_adopted": True,
    "not_deployed": True,
}


def validate_strategy_impact_cube_artifact_binding(
    binding: StrategyImpactCubeArtifactBinding,
) -> dict[str, Any]:
    """Revalidate one typed ImpactCube artifact binding for downstream use."""

    return _authenticated_impact_cube(binding)


def validate_candidate_stability_report_compatibility(
    *,
    candidate_stability: StrategyCandidateStabilityArtifactBinding,
    sample_design: _StrategySampleDesignV2Binding,
    candidate_pool: StrategyCandidatePoolArtifactBinding,
) -> dict[str, Any]:
    """Authenticate stability evidence and bind it to the exact report sources.

    Agent preflight may use this pure helper to distinguish an authentic but
    unrelated historical result from evidence for the current SampleDesign V2
    and Candidate Pool.  It performs no reads, writes, or report projection.
    """

    stability = _authenticated_candidate_stability(candidate_stability)
    sample = _authenticated_sample_design(sample_design)
    pool, _compiled = _authenticated_candidate_pool(candidate_pool)
    _require_same_task(
        candidate_stability.task_id,
        sample_design=sample_design,
        candidate_pool=candidate_pool,
    )
    _require_candidate_stability_identity(
        stability=stability,
        sample_binding=sample_design,
        sample=sample,
        pool=pool,
        pool_binding=candidate_pool,
    )
    return stability


def validate_cross_candidate_search_report_compatibility(
    *,
    cross_candidate_search: CrossCandidateSearchArtifactBinding,
    sample_design: _StrategySampleDesignV2Binding,
) -> dict[str, Any]:
    """Authenticate aggregate Cross search evidence for one exact V2 sample."""

    sample = _authenticated_sample_design(sample_design)
    _require_same_task(
        sample_design.task_id,
        cross_candidate_search=cross_candidate_search,
    )
    return _authenticated_cross_candidate_search(
        cross_candidate_search,
        sample_binding=sample_design,
        sample=sample,
    )


def validate_cross_rule_search_report_compatibility(
    *,
    cross_rule_search: CrossRuleSearchArtifactBinding,
    sample_design: _StrategySampleDesignV2Binding,
) -> dict[str, Any]:
    """Authenticate aggregate 2D/3D rule evidence for one exact V2 sample."""

    sample = _authenticated_sample_design(sample_design)
    _require_same_task(
        sample_design.task_id,
        cross_rule_search=cross_rule_search,
    )
    return _authenticated_cross_rule_search(
        cross_rule_search,
        sample_binding=sample_design,
        sample=sample,
    )


def build_strategy_report_bundle_source_inputs(
    *,
    project_context: StrategyProjectContextArtifactBinding,
    sample_design: _StrategySampleDesignV2Binding,
    candidate_pool: StrategyCandidatePoolArtifactBinding,
    pool_validations: Sequence[
        StrategyPoolValidationArtifactBinding
    ] = (),
    candidate_stability: StrategyCandidateStabilityArtifactBinding | None = None,
    pool_stability: StrategyPoolStabilityArtifactBinding | None = None,
    voting_candidate_search: VotingCandidateSearchArtifactBinding | None = None,
    cross_candidate_search: CrossCandidateSearchArtifactBinding | None = None,
    cross_rule_search: CrossRuleSearchArtifactBinding | None = None,
    pool_impact: StrategyPoolImpactArtifactBinding | None = None,
    impact_cube: StrategyImpactCubeArtifactBinding | None = None,
    model_evidence: StrategyModelEvidenceV2ArtifactBinding | None = None,
    training_evidence: ModelingTrainingEvidenceArtifactBinding | None = None,
    score_evidence: ModelScoreEvidenceArtifactBinding | None = None,
    strategy_lifecycle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic evidence-only kwargs for ``build_strategy_report_bundle``.

    The caller still owns title, report status/revision, generated time, and any
    independently governed strategy identity.  The returned mapping contains
    only the seven sections plus the four source inventories accepted by the
    report contract.
    """

    project = _authenticated_project_context(project_context)
    task_id = project_context.task_id
    _require_same_task(
        task_id,
        sample_design=sample_design,
        candidate_pool=candidate_pool,
        candidate_stability=candidate_stability,
        pool_stability=pool_stability,
        voting_candidate_search=voting_candidate_search,
        cross_candidate_search=cross_candidate_search,
        cross_rule_search=cross_rule_search,
        pool_impact=(
            None if impact_cube is not None else pool_impact
        ),
        impact_cube=impact_cube,
        model_evidence=model_evidence,
        training_evidence=training_evidence,
        score_evidence=score_evidence,
    )
    for validation in pool_validations:
        _require_same_task(task_id, pool_validation=validation)
    sample = _authenticated_sample_design(sample_design)
    resolve_strategy_sample_design_v2_source_mode(
        sample["sample_design"],
        capability="physical_v2",
        consumer="strategy_report_bundle",
    )
    pool, design = _authenticated_candidate_pool(candidate_pool)
    validations = _authenticated_pool_validations(
        pool_validations,
        sample_binding=sample_design,
        sample=sample,
        pool_binding=candidate_pool,
        pool=pool,
        compiled_design=design,
    )
    voting_search = (
        None
        if voting_candidate_search is None
        else _authenticated_voting_candidate_search(
            voting_candidate_search,
            sample_binding=sample_design,
            sample=sample,
            pool_binding=candidate_pool,
            pool=pool,
            compiled_design=design,
        )
    )
    cross_search = (
        None
        if cross_candidate_search is None
        else _authenticated_cross_candidate_search(
            cross_candidate_search,
            sample_binding=sample_design,
            sample=sample,
        )
    )
    cross_rule = (
        None
        if cross_rule_search is None
        else _authenticated_cross_rule_search(
            cross_rule_search,
            sample_binding=sample_design,
            sample=sample,
        )
    )
    try:
        scorecard_report = project_scorecard_report_evidence(candidate_pool)
    except StrategyError as exc:
        raise StrategyReportBundleError(
            "candidate-pool scorecard lineage is invalid"
        ) from exc
    stability = (
        None
        if candidate_stability is None
        else validate_candidate_stability_report_compatibility(
            candidate_stability=candidate_stability,
            sample_design=sample_design,
            candidate_pool=candidate_pool,
        )
    )
    if impact_cube is None and pool_impact is None:
        raise StrategyReportBundleError(
            "an authenticated ImpactCube or legacy PoolImpact is required"
        )
    cube = (
        None
        if impact_cube is None
        else _authenticated_impact_cube(impact_cube)
    )
    impact = (
        None
        if cube is not None or pool_impact is None
        else _authenticated_pool_impact(pool_impact)
    )
    pool_stability_evidence = (
        None
        if pool_stability is None
        else _authenticated_pool_stability(pool_stability)
    )
    effective_training = _effective_training_binding(
        training_evidence=training_evidence,
        score_evidence=score_evidence,
    )
    training = (
        None
        if effective_training is None
        else _authenticated_training_evidence(effective_training, sample)
    )
    model = (
        None
        if model_evidence is None
        else _authenticated_model_evidence(model_evidence, sample)
    )
    score = (
        None
        if score_evidence is None
        else _authenticated_score_evidence(
            score_evidence,
            sample=sample,
            training_binding=effective_training,
            training=training,
        )
    )
    _require_same_task(
        task_id,
        training_evidence=effective_training,
    )
    _require_sample_identity(
        sample_design=sample_design,
        sample=sample,
        model_evidence=model_evidence,
        training_evidence=effective_training,
        score_evidence=score_evidence,
    )
    if cube is not None:
        assert impact_cube is not None
        _require_impact_cube_identity(
            sample_binding=sample_design,
            sample=sample,
            pool_binding=candidate_pool,
            pool=pool,
            compiled_design=design,
            impact_binding=impact_cube,
            cube=cube,
        )
        if pool_stability_evidence is not None:
            assert pool_stability is not None
            _require_pool_stability_identity(
                stability=pool_stability_evidence,
                stability_binding=pool_stability,
                sample_binding=sample_design,
                pool_binding=candidate_pool,
                pool=pool,
                compiled_design=design,
                impact_binding=impact_cube,
                cube=cube,
            )
    else:
        if pool_stability_evidence is not None:
            raise StrategyReportBundleError(
                "Pool stability requires the report's exact ImpactCube"
            )
        assert pool_impact is not None and impact is not None
        _require_pool_impact_identity(
            sample_binding=sample_design,
            sample=sample,
            pool_binding=candidate_pool,
            pool=pool,
            compiled_design=design,
            impact_binding=pool_impact,
            impact=impact,
        )

    pool_ref = _artifact_ref(
        "strategy_candidate_pool",
        candidate_pool.artifact_id,
        candidate_pool.artifact_content_hash,
    )
    lifecycle = _strategy_lifecycle_projection(
        strategy_lifecycle,
        pool=pool,
        pool_ref=pool_ref,
    )
    stability_source_ref = (
        None
        if stability is None
        else _candidate_stability_frozen_artifact_ref(
            stability,
            pool_ref=pool_ref,
        )
    )
    voting_search_ref = (
        None
        if voting_candidate_search is None
        else _artifact_ref(
            "voting_candidate_search",
            voting_candidate_search.artifact_id,
            voting_candidate_search.artifact_content_hash,
        )
    )
    cross_search_ref = (
        None
        if cross_candidate_search is None
        else _artifact_ref(
            "cross_candidate_search",
            cross_candidate_search.artifact_id,
            cross_candidate_search.artifact_content_hash,
        )
    )
    cross_rule_ref = (
        None
        if cross_rule_search is None
        else _artifact_ref(
            "cross_rule_search",
            cross_rule_search.artifact_id,
            cross_rule_search.artifact_content_hash,
        )
    )
    validation_refs = {
        evidence["partition"]: _artifact_ref(
            "strategy_validation",
            binding.artifact_id,
            binding.artifact_content_hash,
        )
        for binding, evidence in validations
    }
    pool_stability_ref = (
        None
        if pool_stability is None
        else _artifact_ref(
            "pool_stability",
            pool_stability.artifact_id,
            pool_stability.artifact_content_hash,
        )
    )
    refs = _EvidenceRefs(
        project=_artifact_ref(
            "strategy_project_context",
            project_context.artifact_id,
            project_context.artifact_content_hash,
        ),
        sample=_artifact_ref(
            "sample_design",
            sample_design.bundle_artifact_id,
            sample_design.bundle_artifact_content_hash,
        ),
        pool=pool_ref,
        impact=_artifact_ref(
            "strategy_impact" if cube is not None else "pool_impact",
            (
                impact_cube.artifact_id
                if cube is not None and impact_cube is not None
                else pool_impact.artifact_id
            ),
            (
                impact_cube.artifact_content_hash
                if cube is not None and impact_cube is not None
                else pool_impact.artifact_content_hash
            ),
        ),
        model=(
            None
            if model_evidence is None
            else _artifact_ref(
                "strategy_model_evidence",
                model_evidence.artifact_id,
                model_evidence.artifact_content_hash,
            )
        ),
        training=(
            None
            if effective_training is None
            else _artifact_ref(
                "modeling_training_evidence",
                _record_text(effective_training.evidence_record, "id"),
                _record_text(effective_training.evidence_record, "content_hash"),
            )
        ),
        score=(
            None
            if score_evidence is None
            else _artifact_ref(
                "model_score_evidence",
                _record_text(score_evidence.evidence_record, "id"),
                _record_text(score_evidence.evidence_record, "content_hash"),
            )
        ),
        stability=(
            None
            if candidate_stability is None
            else _artifact_ref(
                "backtest",
                candidate_stability.artifact_id,
                candidate_stability.artifact_content_hash,
            )
        ),
        stability_source=stability_source_ref,
    )
    scorecard_backtest_refs = _scorecard_backtest_refs(scorecard_report)
    scorecard_frozen_refs = _scorecard_frozen_refs(scorecard_report)
    state = project["state"]
    pre_impact_sections = {
        "current_project": _current_project_section(project, refs.project),
        "historical_versions": _history_section(project, refs.project),
        "sample_design": _sample_section(sample, refs.sample),
        "univariate_and_models": _model_section(
            model=model,
            training=training,
            score=score,
            refs=refs,
        ),
        "candidate_combinations": _candidate_section(
            pool=pool,
            compiled_design=design,
            pool_ref=refs.pool,
            scorecard_report=scorecard_report,
            scorecard_backtest_refs=scorecard_backtest_refs,
            scorecard_frozen_refs=scorecard_frozen_refs,
            stability=stability,
            stability_ref=refs.stability,
            stability_source_ref=refs.stability_source,
            voting_search=voting_search,
            voting_search_ref=voting_search_ref,
            cross_search=cross_search,
            cross_search_ref=cross_search_ref,
            cross_rule_search=cross_rule,
            cross_rule_search_ref=cross_rule_ref,
            dataset_ref=_dataset_ref_from_sample(sample),
            strategy_lifecycle=lifecycle,
        ),
    }
    allow_oot_validated = not _has_validation_blocker(
        sections=pre_impact_sections.values(),
        missing_information=state["missing_information_records"],
    )
    base_impact_section = (
        _impact_cube_section(
            cube=cube,
            pool_ref=refs.pool,
            impact_ref=refs.impact,
            allow_oot_validated=allow_oot_validated,
        )
        if cube is not None
        else _impact_section(
            impact=impact,
            pool_ref=refs.pool,
            impact_ref=refs.impact,
        )
    )
    impact_section = _with_pool_validation_evidence(
        section=base_impact_section,
        validations=validations,
        validation_refs=validation_refs,
        pool_ref=refs.pool,
        claim_oot_validated=allow_oot_validated,
    )
    if pool_stability_evidence is not None:
        assert pool_stability_ref is not None
        impact_section = _with_pool_stability_evidence(
            section=impact_section,
            stability=pool_stability_evidence,
            stability_ref=pool_stability_ref,
        )
    base_final_document = (
        _impact_cube_final_document_section(
            pool=pool,
            compiled_design=design,
            cube=cube,
            pool_ref=refs.pool,
            impact_ref=refs.impact,
            allow_oot_validated=allow_oot_validated,
            strategy_lifecycle=lifecycle,
        )
        if cube is not None
        else _final_document_section(
            pool=pool,
            compiled_design=design,
            impact=impact,
            pool_ref=refs.pool,
            impact_ref=refs.impact,
            strategy_lifecycle=lifecycle,
        )
    )
    final_document = _with_pool_validation_final_document(
        section=base_final_document,
        impact_section=impact_section,
        validations=validations,
        validation_refs=validation_refs,
        claim_oot_validated=allow_oot_validated,
    )
    if pool_stability_evidence is not None:
        assert pool_stability_ref is not None
        final_document = _with_pool_stability_final_document(
            section=final_document,
            stability=pool_stability_evidence,
            stability_ref=pool_stability_ref,
        )
    sections_by_key = {
        **pre_impact_sections,
        "impact_assessment": impact_section,
        "final_document": final_document,
    }
    snapshot = state["current_project_snapshot"]
    dataset_refs = _dedupe_refs(
        [
            *snapshot["dataset_refs"],
            _dataset_ref_from_sample(sample),
            *(
                []
                if stability is None
                else [_dataset_ref_from_candidate_stability(stability)]
            ),
            *(
                []
                if pool_stability_evidence is None
                else [
                    _dataset_ref_from_pool_stability(
                        pool_stability_evidence
                    )
                ]
            ),
            (
                _dataset_ref_from_impact_cube(cube)
                if cube is not None
                else _dataset_ref_from_impact(impact)
            ),
            *(
                _dataset_ref_from_pool_validation(evidence)
                for _binding, evidence in validations
            ),
        ]
    )
    tool_run_refs = _dedupe_refs(
        [
            *snapshot["tool_run_refs"],
            *(
                ref
                for history in state["historical_strategy_reviews"]
                for ref in history["tool_run_refs"]
            ),
            *(
                []
                if impact_cube is None
                else [
                    impact_cube_producer_run_ref(
                        impact_cube.artifact_provenance["producer_run"]
                    )
                ]
            ),
            *(
                []
                if pool_stability is None
                else [
                    _artifact_ref(
                        "tool_run",
                        pool_stability.artifact_provenance[
                            "producer_run"
                        ]["run_id"],
                        pool_stability.artifact_provenance[
                            "producer_run"
                        ]["content_hash"],
                    )
                ]
            ),
        ]
    )
    return {
        "sections": [
            sections_by_key[key]
            for key in REPORT_SECTION_KEYS
        ],
        "dataset_refs": dataset_refs,
        "strategy_artifact_refs": _dedupe_refs(
            [
                refs.pool,
                refs.impact,
                *scorecard_report["artifact_refs"],
                *scorecard_backtest_refs,
                *scorecard_frozen_refs,
                *([] if refs.stability is None else [refs.stability]),
                *(
                    []
                    if refs.stability_source is None
                    else [refs.stability_source]
                ),
                *(
                    []
                    if voting_search_ref is None
                    else [voting_search_ref]
                ),
                *(
                    []
                    if cross_search_ref is None
                    else [cross_search_ref]
                ),
                *(
                    []
                    if strategy_lifecycle is None
                    else [lifecycle["source_ref"]]
                ),
                *validation_refs.values(),
                *(
                    []
                    if pool_stability_ref is None
                    else [pool_stability_ref]
                ),
            ]
        ),
        "tool_run_refs": tool_run_refs,
        "missing_information": list(state["missing_information_records"]),
    }


class _EvidenceRefs:
    __slots__ = (
        "project",
        "sample",
        "pool",
        "impact",
        "model",
        "training",
        "score",
        "stability",
        "stability_source",
    )

    def __init__(
        self,
        *,
        project: dict[str, str],
        sample: dict[str, str],
        pool: dict[str, str],
        impact: dict[str, str],
        model: dict[str, str] | None,
        training: dict[str, str] | None,
        score: dict[str, str] | None,
        stability: dict[str, str] | None,
        stability_source: dict[str, str] | None,
    ) -> None:
        self.project = project
        self.sample = sample
        self.pool = pool
        self.impact = impact
        self.model = model
        self.training = training
        self.score = score
        self.stability = stability
        self.stability_source = stability_source


def _authenticated_project_context(
    binding: StrategyProjectContextArtifactBinding,
) -> dict[str, Any]:
    _require_binding_type(
        binding,
        StrategyProjectContextArtifactBinding,
        "project-context",
    )
    revision = validate_strategy_project_context_revision(binding.revision)
    if revision != binding.revision or revision["task_id"] != binding.task_id:
        raise StrategyReportBundleError(
            "project-context binding identity changed"
        )
    _require_canonical_artifact_hash(
        binding.artifact_content_hash,
        canonical_strategy_project_context_revision_json(revision),
        "project-context",
    )
    return revision


def _authenticated_sample_design(
    binding: _StrategySampleDesignV2Binding,
) -> dict[str, Any]:
    _require_binding_type(
        binding,
        (
            StrategySampleDesignV2ArtifactBinding,
            StrategySampleDesignV2NativeArtifactBinding,
        ),
        "sample-design V2",
    )
    bundle = validate_strategy_sample_design_v2_bundle(binding.bundle)
    if bundle != binding.bundle:
        raise StrategyReportBundleError(
            "sample-design V2 binding content changed"
        )
    identity = bundle["sample_design"]["identity"]
    if identity["task_id"] != binding.task_id:
        raise StrategyReportBundleError(
            "sample-design V2 binding belongs to another task"
        )
    _require_canonical_artifact_hash(
        binding.bundle_artifact_content_hash,
        canonical_strategy_sample_design_v2_bundle_json(bundle),
        "sample-design V2",
    )
    return bundle


def _sample_risk_development_ref(
    binding: _StrategySampleDesignV2Binding,
) -> dict[str, str]:
    design = binding.bundle["sample_design"]
    source_mode = resolve_strategy_sample_design_v2_source_mode(
        design,
        capability="physical_v2",
        consumer="strategy_report_bundle",
    )
    if source_mode == "legacy_anchored":
        reference = StrategyRiskDevelopmentRef.from_value(
            design["compatibility"]["legacy_development_ref"]
        )
        if reference.partition != "development":
            raise StrategyReportBundleError(
                "legacy report development partition changed"
            )
        return reference.to_ref_dict()
    if source_mode == "native_active_dataset":
        return StrategyRiskDevelopmentRef.from_value(
            {
                "artifact_id": binding.bundle_artifact_id,
                "artifact_content_hash": binding.bundle_artifact_content_hash,
                "sample_design_id": design["sample_design_id"],
                "sample_design_content_hash": design["content_hash"],
                "partition": "risk/development",
            }
        ).to_ref_dict()
    raise StrategyReportBundleError(
        "sample-design V2 report source mode is unsupported"
    )


def _authenticated_candidate_pool(
    binding: StrategyCandidatePoolArtifactBinding,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require_binding_type(
        binding,
        StrategyCandidatePoolArtifactBinding,
        "candidate-pool",
    )
    pool = validate_strategy_pool(binding.pool)
    if pool != binding.pool or pool["task_id"] != binding.task_id:
        raise StrategyReportBundleError(
            "candidate-pool binding identity changed"
        )
    compiled = compile_strategy_pool(pool)
    if compiled != binding.compiled_design:
        raise StrategyReportBundleError(
            "candidate-pool compiled design changed"
        )
    if (
        pool["strategy_type"] != binding.strategy_type
        or pool["status"] != "draft"
        or pool["validation_status"] != "unvalidated"
    ):
        raise StrategyReportBundleError(
            "candidate-pool must remain draft and unvalidated"
        )
    _require_canonical_artifact_hash(
        binding.artifact_content_hash,
        canonical_strategy_pool_json(pool),
        "candidate-pool",
    )
    return pool, compiled


def _authenticated_pool_stability(
    binding: StrategyPoolStabilityArtifactBinding,
) -> dict[str, Any]:
    _require_binding_type(
        binding,
        StrategyPoolStabilityArtifactBinding,
        "Pool stability",
    )
    if not isinstance(binding.stability, Mapping):
        raise StrategyReportBundleError(
            "Pool stability binding payload is invalid"
        )
    source_bindings = binding.stability.get("source_bindings")
    if not isinstance(source_bindings, Mapping):
        raise StrategyReportBundleError(
            "Pool stability source bindings are invalid"
        )
    source_ref = source_bindings.get("impact_cube")
    if not isinstance(source_ref, Mapping):
        raise StrategyReportBundleError(
            "Pool stability ImpactCube source binding is invalid"
        )
    source_cube = _authenticated_impact_cube(binding.impact_cube)
    try:
        stability = validate_strategy_pool_stability(
            binding.stability,
            impact_cube=source_cube,
            impact_cube_ref=source_ref,
        )
    except StrategyError as exc:
        raise StrategyReportBundleError(
            "Pool stability evidence is invalid"
        ) from exc
    if (
        stability != binding.stability
        or binding.task_id != binding.impact_cube.task_id
        or stability["identity"]["task_id"] != binding.task_id
    ):
        raise StrategyReportBundleError(
            "Pool stability binding identity changed"
        )
    _require_canonical_artifact_hash(
        binding.artifact_content_hash,
        canonical_strategy_pool_stability_json(stability),
        "Pool stability",
    )
    if not isinstance(binding.tasks_root, Path) or not (
        binding.tasks_root.is_absolute()
    ):
        raise StrategyReportBundleError(
            "Pool stability governed task root changed"
        )
    expected_path = (
        binding.tasks_root
        / binding.task_id
        / "strategy_pool_stabilities"
        / f"{stability['stability_id']}.json"
    )
    if (
        not isinstance(binding.artifact_path, Path)
        or binding.artifact_path != expected_path
        or binding.artifact_id
        != stable_task_artifact_id(
            task_id=binding.task_id,
            kind=POOL_STABILITY_ARTIFACT_KIND,
            path=str(expected_path),
        )
    ):
        raise StrategyReportBundleError(
            "Pool stability governed artifact identity changed"
        )
    _require_pool_stability_provenance(binding, stability)
    return stability


def _require_pool_stability_provenance(
    binding: StrategyPoolStabilityArtifactBinding,
    stability: Mapping[str, Any],
) -> None:
    try:
        canonical = json.dumps(
            binding.artifact_provenance,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        provenance = json.loads(canonical)
    except (TypeError, ValueError, RecursionError) as exc:
        raise StrategyReportBundleError(
            "Pool stability artifact provenance is invalid"
        ) from exc
    if (
        not isinstance(provenance, dict)
        or binding.artifact_provenance_json != canonical
    ):
        raise StrategyReportBundleError(
            "Pool stability artifact provenance fields changed"
        )

    source = stability["source_bindings"]
    tool_ref = {
        "plugin": "strategy",
        "tool": "measure_strategy_pool_stability",
        "origin_tool": POOL_STABILITY_ORIGIN_TOOL,
        "tool_schema_version": POOL_STABILITY_TOOL_SCHEMA_VERSION,
        "producer_version": POOL_STABILITY_PRODUCER_VERSION,
    }
    request = source["impact_cube"]
    input_hash = hashlib.sha256(
        _canonical_pool_stability_value(
            {
                "task_id": binding.task_id,
                "request": request,
                "producer": tool_ref,
            }
        ).encode("utf-8")
    ).hexdigest()
    producer_body = {
        "schema_version": POOL_STABILITY_PRODUCER_RUN_SCHEMA_VERSION,
        "task_id": binding.task_id,
        "input_hash": input_hash,
        "request": request,
        "tool_ref": tool_ref,
        "stability_ref": {
            "stability_id": stability["stability_id"],
            "content_hash": stability["content_hash"],
        },
        "artifact_ref": {
            "artifact_id": binding.artifact_id,
            "kind": POOL_STABILITY_ARTIFACT_KIND,
            "filename": binding.artifact_path.name,
            "content_hash": binding.artifact_content_hash,
            "origin_tool": POOL_STABILITY_ORIGIN_TOOL,
        },
    }
    run_id = (
        "strategy-pool-stability-run-"
        + hashlib.sha256(
            _canonical_pool_stability_value(producer_body).encode("utf-8")
        ).hexdigest()[:24]
    )
    run_without_hash = {**producer_body, "run_id": run_id}
    producer_run = {
        **run_without_hash,
        "content_hash": hashlib.sha256(
            _canonical_pool_stability_value(run_without_hash).encode("utf-8")
        ).hexdigest(),
    }
    expected = {
        "schema_version": POOL_STABILITY_ARTIFACT_SCHEMA_VERSION,
        "producer_version": POOL_STABILITY_PRODUCER_VERSION,
        "task_id": binding.task_id,
        "stability_id": stability["stability_id"],
        "stability_content_hash": stability["content_hash"],
        "impact_cube_ref": request,
        "pool_identity": stability["identity"],
        "sample_design_v2": source["sample_design_v2"],
        "dataset_binding": source["dataset"],
        "baseline_partition": stability["baseline_partition"],
        "comparison_partitions": stability["comparison_partitions"],
        "lifecycle": stability["lifecycle"],
        "producer_run": producer_run,
    }
    if provenance != expected:
        raise StrategyReportBundleError(
            "Pool stability artifact provenance identity changed"
        )


def _canonical_pool_stability_value(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise StrategyReportBundleError(
            "Pool stability binding must contain finite canonical JSON"
        ) from exc


def _authenticated_pool_validations(
    bindings: Sequence[StrategyPoolValidationArtifactBinding],
    *,
    sample_binding: _StrategySampleDesignV2Binding,
    sample: Mapping[str, Any],
    pool_binding: StrategyCandidatePoolArtifactBinding,
    pool: Mapping[str, Any],
    compiled_design: Mapping[str, Any],
) -> tuple[
    tuple[StrategyPoolValidationArtifactBinding, dict[str, Any]],
    ...,
]:
    if isinstance(bindings, str | bytes | bytearray) or not isinstance(
        bindings,
        Sequence,
    ):
        raise StrategyReportBundleError(
            "Pool validation bindings must be a sequence"
        )
    if len(bindings) > 2:
        raise StrategyReportBundleError(
            "Pool validation bindings may contain at most validation and OOT"
        )
    by_partition: dict[
        str,
        tuple[StrategyPoolValidationArtifactBinding, dict[str, Any]],
    ] = {}
    for binding in bindings:
        _require_binding_type(
            binding,
            StrategyPoolValidationArtifactBinding,
            "Pool validation",
        )
        evidence = validate_strategy_pool_validation_evidence(
            binding.evidence
        )
        if (
            evidence != binding.evidence
            or binding.task_id != sample_binding.task_id
            or evidence["identity"]["task_id"] != binding.task_id
        ):
            raise StrategyReportBundleError(
                "Pool validation binding identity changed"
            )
        _require_canonical_artifact_hash(
            binding.artifact_content_hash,
            canonical_strategy_pool_validation_json(evidence),
            "Pool validation",
        )
        _require_pool_validation_provenance(binding, evidence)
        _require_pool_validation_provenance_requirements(
            binding,
            compiled_design=compiled_design,
        )
        _require_pool_validation_identity(
            evidence=evidence,
            sample_binding=sample_binding,
            sample=sample,
            pool_binding=pool_binding,
            pool=pool,
            compiled_design=compiled_design,
        )
        partition = evidence["partition"]
        if partition in by_partition:
            raise StrategyReportBundleError(
                f"Pool validation {partition} evidence is duplicated"
            )
        by_partition[partition] = (binding, evidence)
    return tuple(
        by_partition[partition]
        for partition in ("validation", "oot")
        if partition in by_partition
    )


def _require_pool_validation_provenance(
    binding: StrategyPoolValidationArtifactBinding,
    evidence: Mapping[str, Any],
) -> None:
    try:
        provenance_json = json.dumps(
            binding.artifact_provenance,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        provenance = json.loads(provenance_json)
    except (TypeError, ValueError, RecursionError) as exc:
        raise StrategyReportBundleError(
            "Pool validation provenance is invalid"
        ) from exc
    if (
        not isinstance(provenance, dict)
        or set(provenance) != _POOL_VALIDATION_PROVENANCE_FIELDS
        or binding.artifact_provenance_json != provenance_json
    ):
        raise StrategyReportBundleError(
            "Pool validation provenance fields changed"
        )
    schema_version = provenance["schema_version"]
    fields = provenance["field_bindings"]
    if (
        schema_version == POOL_VALIDATION_ARTIFACT_SCHEMA_VERSION
        and isinstance(fields, dict)
        and set(fields)
        == {"month_col", "loan_amount_col", "overdue_amount_col"}
    ):
        pass
    elif (
        schema_version
        == POOL_VALIDATION_REQUIREMENTS_ARTIFACT_SCHEMA_VERSION
        and isinstance(fields, dict)
        and set(fields)
        == {
            "month_col",
            "loan_amount_col",
            "overdue_amount_col",
            "requirements",
        }
    ):
        try:
            validate_pool_requirement_bindings_provenance(
                fields["requirements"]
            )
        except StrategyError as exc:
            raise StrategyReportBundleError(
                "Pool validation requirement provenance is invalid"
            ) from exc
    else:
        raise StrategyReportBundleError(
            "Pool validation provenance schema changed"
        )
    identity = evidence["identity"]
    sources = evidence["source_bindings"]
    sample_source = sources["sample_design_v2"]
    expected_pool_ref = {
        "artifact_id": sources["pool_artifact"]["artifact_id"],
        "expected_artifact_content_hash": sources["pool_artifact"][
            "artifact_content_hash"
        ],
        "expected_pool_id": identity["pool_id"],
        "expected_revision": identity["revision"],
        "expected_revision_id": identity["revision_id"],
        "expected_snapshot_hash": identity["snapshot_hash"],
        "pool_id": identity["pool_id"],
        "revision_id": identity["revision_id"],
    }
    expected_sample_ref = {
        "membership_artifact_id": sample_source["membership_artifact_id"],
        "expected_membership_artifact_content_hash": sample_source[
            "membership_artifact_content_hash"
        ],
        "bundle_artifact_id": sample_source["bundle_artifact_id"],
        "expected_bundle_artifact_content_hash": sample_source[
            "bundle_artifact_content_hash"
        ],
        "expected_bundle_id": sample_source["bundle_id"],
        "expected_sample_design_id": sample_source["sample_design_id"],
        "expected_sample_design_content_hash": sample_source[
            "sample_design_content_hash"
        ],
    }
    physical_fields = {
        key: fields[key]
        for key in ("month_col", "loan_amount_col", "overdue_amount_col")
    }
    expected_scalars = {
        "producer_version": STRATEGY_POOL_VALIDATION_PRODUCER_VERSION,
        "task_id": identity["task_id"],
        "evidence_id": evidence["evidence_id"],
        "evidence_content_hash": evidence["content_hash"],
        "partition": evidence["partition"],
        "population": "risk",
        "comparison_mode": "absolute",
        "lifecycle_stage": evidence["partition"],
        "validation_status": "independent_evidence",
    }
    if (
        any(
            provenance[key] != value
            for key, value in expected_scalars.items()
        )
        or provenance["pool_ref"] != expected_pool_ref
        or provenance["sample_design_ref"] != expected_sample_ref
        or provenance["dataset_binding"] != sources["dataset"]
        or provenance["target_binding"] != sources["target"]
        or physical_fields != sources["fields"]
    ):
        raise StrategyReportBundleError(
            "Pool validation provenance does not match embedded evidence"
        )


def _require_pool_validation_provenance_requirements(
    binding: StrategyPoolValidationArtifactBinding,
    *,
    compiled_design: Mapping[str, Any],
) -> None:
    requirements = list(
        normalize_pool_requirements(compiled_design["requirements"])
    )
    provenance = binding.artifact_provenance
    fields = provenance["field_bindings"]
    if requirements:
        if (
            provenance["schema_version"]
            != POOL_VALIDATION_REQUIREMENTS_ARTIFACT_SCHEMA_VERSION
            or "requirements" not in fields
        ):
            raise StrategyReportBundleError(
                "Pool validation requirements differ from the Candidate Pool"
            )
        try:
            bindings = validate_pool_requirement_bindings_provenance(
                fields["requirements"]
            )
        except StrategyError as exc:
            raise StrategyReportBundleError(
                "Pool validation requirement bindings are invalid"
            ) from exc
        if bindings["requirements"] != requirements:
            raise StrategyReportBundleError(
                "Pool validation requirements differ from the Candidate Pool"
            )
        return
    if (
        provenance["schema_version"] != POOL_VALIDATION_ARTIFACT_SCHEMA_VERSION
        or "requirements" in fields
    ):
        raise StrategyReportBundleError(
            "Pool validation requirements differ from the Candidate Pool"
        )


def _require_pool_validation_identity(
    *,
    evidence: Mapping[str, Any],
    sample_binding: _StrategySampleDesignV2Binding,
    sample: Mapping[str, Any],
    pool_binding: StrategyCandidatePoolArtifactBinding,
    pool: Mapping[str, Any],
    compiled_design: Mapping[str, Any],
) -> None:
    identity = evidence["identity"]
    sources = evidence["source_bindings"]
    partition = evidence["partition"]
    expected_identity = {
        "pool_id": pool["pool_id"],
        "task_id": pool["task_id"],
        "strategy_type": pool["strategy_type"],
        "revision": pool["revision"],
        "revision_id": pool["revision_id"],
        "snapshot_hash": pool["snapshot_hash"],
        "design_hash": compiled_design["design_hash"],
        "strategy_spec_hash": strategy_spec_hash(
            compiled_design["strategy_spec"]
        ),
    }
    header = sample_binding.membership["header"]
    design = sample["sample_design"]
    expected_sample = {
        "membership_artifact_id": sample_binding.membership_artifact_id,
        "membership_artifact_content_hash": (
            sample_binding.membership_artifact_content_hash
        ),
        "membership_id": header["membership_id"],
        "membership_content_hash": header["content_hash"],
        "bundle_artifact_id": sample_binding.bundle_artifact_id,
        "bundle_artifact_content_hash": (
            sample_binding.bundle_artifact_content_hash
        ),
        "bundle_id": sample["bundle_id"],
        "bundle_content_hash": sample["content_hash"],
        "sample_design_id": design["sample_design_id"],
        "sample_design_content_hash": design["content_hash"],
        "partition_key": f"risk/{partition}",
        "partition_count": header["counts"]["risk"][partition],
        "analysis_universe_row_count": header["row_count"],
    }
    source = sample_binding.source_binding
    try:
        expected_dataset = {
            "task_id": source.task_id,
            "dataset_id": source.dataset_id,
            "dataset_content_hash": source.dataset_content_hash,
            "dataset_source_path": source.dataset_source_path,
            "dataset_registry_metadata_hash": (
                source.dataset_registry_metadata_hash
            ),
            "workspace_revision": source.workspace_revision,
            "workspace_generation": source.workspace_generation,
            "semantic_mapping_hash": source.semantic_mapping_hash,
        }
    except AttributeError as exc:
        raise StrategyReportBundleError(
            "Pool validation sample dataset binding is incomplete"
        ) from exc
    target = design["target_selector"]
    fields = design["sample_semantics"]["field_bindings"]
    expected_development = {
        "legacy_development_ref": _sample_risk_development_ref(
            sample_binding
        ),
        "sample_binding": {
            "task_id": pool["task_id"],
            **pool["entries"][0]["source"]["evidence_identity"],
        },
    }
    if (
        identity != expected_identity
        or sources["pool_artifact"]
        != {
            "artifact_id": pool_binding.artifact_id,
            "artifact_content_hash": pool_binding.artifact_content_hash,
        }
        or sources["sample_design_v2"] != expected_sample
        or sources["dataset"] != expected_dataset
        or sources["development_lineage"] != expected_development
        or sources["target"]
        != {
            "column": target["column"],
            "good_value": target["good_value"],
            "bad_value": target["bad_value"],
            "missing_policy": (
                "retain_population_exclude_risk_denominator"
            ),
        }
        or sources["fields"]
        != {
            "month_col": fields["month_field"],
            "loan_amount_col": fields["loan_amount_field"],
            "overdue_amount_col": fields["overdue_amount_field"],
        }
    ):
        raise StrategyReportBundleError(
            "Pool validation evidence references another current Pool, "
            "SampleDesign V2, or dataset"
        )


def _authenticated_voting_candidate_search(
    binding: VotingCandidateSearchArtifactBinding,
    *,
    sample_binding: _StrategySampleDesignV2Binding,
    sample: Mapping[str, Any],
    pool_binding: StrategyCandidatePoolArtifactBinding,
    pool: Mapping[str, Any],
    compiled_design: Mapping[str, Any],
) -> dict[str, Any]:
    _require_binding_type(
        binding,
        VotingCandidateSearchArtifactBinding,
        "Voting search",
    )
    try:
        result = validate_voting_candidate_search_result(binding.result)
    except StrategyError as exc:
        raise StrategyReportBundleError(
            "Voting search result evidence is invalid"
        ) from exc
    if result != binding.result or binding.task_id != sample_binding.task_id:
        raise StrategyReportBundleError(
            "Voting search binding identity changed"
        )
    _require_canonical_artifact_hash(
        binding.artifact_content_hash,
        canonical_voting_candidate_search_result_json(result),
        "Voting search",
    )
    try:
        canonical_provenance = json.dumps(
            binding.artifact_provenance,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        provenance = json.loads(canonical_provenance)
    except (TypeError, ValueError, RecursionError) as exc:
        raise StrategyReportBundleError(
            "Voting search artifact provenance is invalid"
        ) from exc
    if (
        not isinstance(provenance, dict)
        or set(provenance) != _VOTING_SEARCH_PROVENANCE_FIELDS
        or binding.artifact_provenance_json != canonical_provenance
    ):
        raise StrategyReportBundleError(
            "Voting search artifact provenance fields changed"
        )

    development = binding.pool_development
    _require_binding_type(
        development,
        StrategyPoolDevelopmentExecutionBinding,
        "Voting search Pool development",
    )
    development_dataset = development.dataset
    _require_binding_type(
        development_dataset,
        StrategyPoolDevelopmentDatasetBinding,
        "Voting search development dataset",
    )
    if development.task_id != binding.task_id:
        raise StrategyReportBundleError(
            "Voting search Pool development belongs to another task"
        )
    development_pool, development_design = _authenticated_candidate_pool(
        development.pool
    )
    if (
        development.pool is not pool_binding
        and (
            development.pool.artifact_id != pool_binding.artifact_id
            or development.pool.artifact_content_hash
            != pool_binding.artifact_content_hash
        )
    ) or development_pool != pool or development_design != compiled_design:
        raise StrategyReportBundleError(
            "Voting search references another Candidate Pool"
        )
    design = sample["sample_design"]
    source_mode = resolve_strategy_sample_design_v2_source_mode(
        design,
        capability="physical_v2",
        consumer="strategy_report_bundle_voting_search",
    )
    bound_v2 = development.sample_design_v2
    if bound_v2 is not None and (
        _sample_identity(bound_v2) != _sample_identity(sample_binding)
        or _authenticated_sample_design(bound_v2) != sample
    ):
        raise StrategyReportBundleError(
            "Voting search references another sample-design V2 artifact"
        )
    if source_mode == "legacy_anchored" and bound_v2 is None:
        raise StrategyReportBundleError(
            "Voting search legacy development lacks SampleDesign V2 lineage"
        )
    identity = design["identity"]
    dataset = identity["dataset_ref"]
    workspace = identity["workspace_ref"]
    target = design["target_selector"]
    semantics = design["sample_semantics"]
    field_bindings = semantics["field_bindings"]
    execution_sample = development.sample_design
    _require_binding_type(
        execution_sample,
        StrategyRiskDevelopmentExecutionBinding,
        "Voting search risk-development sample design",
    )
    expected_development_ref = _sample_risk_development_ref(sample_binding)
    risk_population = next(
        (
            item
            for item in sample["populations"]
            if item["role"] == "risk"
        ),
        None,
    )
    if risk_population is None:
        raise StrategyReportBundleError(
            "Voting search sample-design risk population is missing"
        )
    development_population = next(
        (
            item
            for item in risk_population["partitions"]
            if item["name"] == "development"
        ),
        None,
    )
    if development_population is None:
        raise StrategyReportBundleError(
            "Voting search development population is missing"
        )
    expected_development_count = development_population["row_count"]
    if (
        execution_sample.to_ref_dict() != expected_development_ref
        or execution_sample.source_mode != source_mode
        or execution_sample.task_id != sample_binding.task_id
        or execution_sample.dataset_id != dataset["dataset_id"]
        or execution_sample.dataset_content_hash != dataset["content_hash"]
        or execution_sample.workspace_revision != workspace["revision"]
        or execution_sample.workspace_generation != workspace["generation"]
        or execution_sample.semantic_mapping_hash
        != workspace["semantic_mapping_hash"]
        or execution_sample.target_col != target["column"]
        or execution_sample.target_bad_value != target["bad_value"]
        or execution_sample.drop_nan_labels != target["drop_missing"]
        or (
            source_mode == "legacy_anchored"
            and execution_sample.split_column
            != getattr(execution_sample._legacy, "split_column", None)
        )
        or (
            source_mode == "native_active_dataset"
            and execution_sample.split_column is not None
        )
        or execution_sample.development_population_count
        != expected_development_count
        or execution_sample.active_population_count
        != (
            risk_population["total_count"]
            if source_mode == "legacy_anchored"
            else sample_binding.membership["header"]["row_count"]
        )
        or execution_sample.month_col != field_bindings["month_field"]
        or execution_sample.weight_col != field_bindings["weight_field"]
        or execution_sample.loan_amount_col
        != field_bindings["loan_amount_field"]
        or execution_sample.overdue_amount_col
        != field_bindings["overdue_amount_field"]
        or development.target_col != target["column"]
        or development.month_col != field_bindings["month_field"]
    ):
        raise StrategyReportBundleError(
            "Voting search sample-design, target, or observation binding changed"
        )
    if (
        development_dataset.task_id != sample_binding.task_id
        or development_dataset.dataset_id != dataset["dataset_id"]
        or development_dataset.content_hash != dataset["content_hash"]
    ):
        raise StrategyReportBundleError(
            "Voting search dataset binding differs from the current sample"
        )

    pool_evidence_identities = [
        entry["source"].get("evidence_identity")
        for entry in pool["entries"]
    ]
    if (
        not pool_evidence_identities
        or any(
            evidence is None
            or evidence.get("sample_context_hash")
            != development.evidence_identity.get("sample_context_hash")
            for evidence in pool_evidence_identities
        )
    ):
        raise StrategyReportBundleError(
            "Voting search Candidate Pool sample context changed"
        )
    if any(
        evidence != development.evidence_identity
        for evidence in pool_evidence_identities
    ):
        raise StrategyReportBundleError(
            "Voting search Candidate Pool development identity changed"
        )
    expected_development_identity = {
        "dataset_id": dataset["dataset_id"],
        "dataset_content_hash": dataset["content_hash"],
        "workspace_revision": workspace["revision"],
        "workspace_generation": workspace["generation"],
        "semantic_mapping_hash": workspace["semantic_mapping_hash"],
        "sample_context_hash": development.evidence_identity[
            "sample_context_hash"
        ],
    }
    if development.evidence_identity != expected_development_identity:
        raise StrategyReportBundleError(
            "Voting search sample context or workspace binding changed"
        )

    requirements = list(compiled_design["requirements"])
    if requirements:
        resolved = binding.resolved_requirements
        if (
            resolved is None
            or type(resolved) is not ResolvedPoolRequirements
            or resolved.task_id != binding.task_id
        ):
            raise StrategyReportBundleError(
                "Voting search requirement bindings are missing"
            )
        try:
            expected_requirements = pool_requirement_bindings_provenance(
                resolved
            )
        except StrategyError as exc:
            raise StrategyReportBundleError(
                "Voting search requirement bindings are invalid"
            ) from exc
        if expected_requirements["requirements"] != requirements:
            raise StrategyReportBundleError(
                "Voting search requirements differ from the Candidate Pool"
            )
    else:
        if binding.resolved_requirements is not None:
            raise StrategyReportBundleError(
                "Voting search has requirements absent from the Candidate Pool"
            )
        expected_requirements = None

    searchable = sorted(
        entry["rule_id"]
        for entry in pool["entries"]
        if entry["enabled"] is True
        and entry["source"]["asset_type"] != VOTING_CANDIDATE_ASSET_TYPE
    )
    excluded = sorted(
        entry["rule_id"]
        for entry in pool["entries"]
        if entry["enabled"] is True
        and entry["source"]["asset_type"] == VOTING_CANDIDATE_ASSET_TYPE
    )
    if result["configuration"]["candidate_ids"] != searchable:
        raise StrategyReportBundleError(
            "Voting search candidate universe differs from the current Pool"
        )

    target_binding = provenance["target_binding"]
    if not isinstance(target_binding, Mapping):
        raise StrategyReportBundleError(
            "Voting search target provenance is invalid"
        )
    dropped = target_binding.get("nan_labels_dropped")
    if (
        isinstance(dropped, bool)
        or not isinstance(dropped, int)
        or dropped < 0
        or result["population"]["row_count"] + dropped
        != expected_development_count
        or (dropped > 0 and not execution_sample.drop_nan_labels)
    ):
        raise StrategyReportBundleError(
            "Voting search NaN-label population binding changed"
        )
    if (
        bool(result["population"]["weight"]["available"])
        is not (execution_sample.weight_col is not None)
        or bool(result["population"]["amount"]["available"])
        is not (execution_sample.loan_amount_col is not None)
    ):
        raise StrategyReportBundleError(
            "Voting search observation availability changed"
        )

    expected_provenance = {
        "schema_version": VOTING_CANDIDATE_SEARCH_ARTIFACT_SCHEMA_VERSION,
        "producer_version": VOTING_CANDIDATE_SEARCH_PRODUCER_VERSION,
        "task_id": binding.task_id,
        "search_id": result["search_id"],
        "search_content_hash": result["content_hash"],
        "request_hash": result["request_hash"],
        "pool_ref": {
            "artifact_id": pool_binding.artifact_id,
            "artifact_content_hash": pool_binding.artifact_content_hash,
            "pool_id": pool["pool_id"],
            "strategy_type": pool["strategy_type"],
            "revision": pool["revision"],
            "revision_id": pool["revision_id"],
            "snapshot_hash": pool["snapshot_hash"],
        },
        "dataset_binding": {
            "task_id": development_dataset.task_id,
            "dataset_id": development_dataset.dataset_id,
            "dataset_source_path": development_dataset.source_path,
            "dataset_content_hash": development_dataset.content_hash,
            "dataset_registry_metadata_hash": (
                development_dataset.registry_metadata_hash
            ),
            "workspace_revision": execution_sample.workspace_revision,
            "workspace_generation": execution_sample.workspace_generation,
            "semantic_mapping_hash": execution_sample.semantic_mapping_hash,
        },
        "sample_design_ref": execution_sample.to_ref_dict(),
        "sample_context_hash": development.evidence_identity[
            "sample_context_hash"
        ],
        "target_binding": {
            "column": execution_sample.target_col,
            "raw_bad_value": execution_sample.target_bad_value,
            "normalized_bad_value": 1,
            "drop_nan_labels": execution_sample.drop_nan_labels,
            "nan_labels_dropped": dropped,
            "labeled_count": result["population"]["row_count"],
            "sample_partition": execution_sample.reference.partition,
        },
        "observation_bindings": {
            "weight_col": execution_sample.weight_col,
            "amount_col": execution_sample.loan_amount_col,
        },
        "requirement_bindings": expected_requirements,
        "excluded_unsupported_rule_ids": excluded,
        "lifecycle": _VOTING_SEARCH_LIFECYCLE,
    }
    if provenance != expected_provenance:
        raise StrategyReportBundleError(
            "Voting search artifact provenance identity changed"
        )
    return result


def _authenticated_cross_candidate_search(
    binding: CrossCandidateSearchArtifactBinding,
    *,
    sample_binding: _StrategySampleDesignV2Binding,
    sample: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate one aggregate Cross search against the report sample only."""

    _require_binding_type(
        binding,
        CrossCandidateSearchArtifactBinding,
        "Cross search",
    )
    try:
        result = validate_cross_candidate_search_result(binding.result)
    except StrategyError as exc:
        raise StrategyReportBundleError(
            "Cross search result evidence is invalid"
        ) from exc
    if result != binding.result or binding.task_id != sample_binding.task_id:
        raise StrategyReportBundleError(
            "Cross search binding identity changed"
        )
    _require_canonical_artifact_hash(
        binding.artifact_content_hash,
        canonical_cross_candidate_search_result_json(result),
        "Cross search",
    )
    try:
        canonical_provenance = json.dumps(
            binding.artifact_provenance,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        provenance = json.loads(canonical_provenance)
    except (TypeError, ValueError, RecursionError) as exc:
        raise StrategyReportBundleError(
            "Cross search artifact provenance is invalid"
        ) from exc
    if (
        not isinstance(provenance, dict)
        or set(provenance) != _CROSS_SEARCH_PROVENANCE_FIELDS
        or binding.artifact_provenance_json != canonical_provenance
    ):
        raise StrategyReportBundleError(
            "Cross search artifact provenance fields changed"
        )

    execution = binding.sample_binding
    _require_binding_type(
        execution,
        StrategyRiskDevelopmentExecutionBinding,
        "Cross search risk-development sample",
    )
    design = sample["sample_design"]
    identity = design["identity"]
    dataset_ref = identity["dataset_ref"]
    workspace_ref = identity["workspace_ref"]
    target = design["target_selector"]
    semantics = design["sample_semantics"]
    fields = semantics["field_bindings"]
    source_mode = resolve_strategy_sample_design_v2_source_mode(
        design,
        capability="physical_v2",
        consumer="strategy_report_bundle_cross_search",
    )
    expected_execution_ref = _sample_risk_development_ref(sample_binding)
    risk_population = next(
        (
            item
            for item in sample["populations"]
            if item["role"] == "risk"
        ),
        None,
    )
    if risk_population is None:
        raise StrategyReportBundleError(
            "Cross search sample-design risk population is missing"
        )
    development = next(
        (
            item
            for item in risk_population["partitions"]
            if item["name"] == "development"
        ),
        None,
    )
    if development is None:
        raise StrategyReportBundleError(
            "Cross search sample-design development population is missing"
        )
    expected_development_count = development["row_count"]
    if (
        execution.to_ref_dict() != expected_execution_ref
        or execution.reference.partition
        != expected_execution_ref["partition"]
        or execution.source_mode != source_mode
        or execution.task_id != sample_binding.task_id
        or execution.dataset_id != dataset_ref["dataset_id"]
        or execution.dataset_content_hash != dataset_ref["content_hash"]
        or execution.workspace_revision != workspace_ref["revision"]
        or execution.workspace_generation != workspace_ref["generation"]
        or execution.semantic_mapping_hash
        != workspace_ref["semantic_mapping_hash"]
        or execution.target_col != target["column"]
        or execution.target_bad_value != target["bad_value"]
        or execution.drop_nan_labels != target["drop_missing"]
        or (
            source_mode == "legacy_anchored"
            and execution.split_column
            != getattr(execution._legacy, "split_column", None)
        )
        or (
            source_mode == "native_active_dataset"
            and execution.split_column is not None
        )
        or execution.development_population_count
        != expected_development_count
        or execution.active_population_count
        != (
            risk_population["total_count"]
            if source_mode == "legacy_anchored"
            else sample_binding.membership["header"]["row_count"]
        )
        or execution.month_col != fields["month_field"]
        or execution.weight_col != fields["weight_field"]
        or execution.loan_amount_col != fields["loan_amount_field"]
        or execution.overdue_amount_col != fields["overdue_amount_field"]
    ):
        raise StrategyReportBundleError(
            "Cross search risk-development sample, target, or workspace changed"
        )

    dataset = binding.dataset
    source = binding.source
    if (
        getattr(dataset, "task_id", None) != sample_binding.task_id
        or getattr(dataset, "dataset_id", None) != dataset_ref["dataset_id"]
        or getattr(dataset, "content_hash", None) != dataset_ref["content_hash"]
        or getattr(source, "task_id", None) != sample_binding.task_id
    ):
        raise StrategyReportBundleError(
            "Cross search dataset or source belongs to another sample"
        )
    dropped = provenance["nan_labels_dropped"]
    if (
        isinstance(dropped, bool)
        or not isinstance(dropped, int)
        or dropped < 0
        or result["population"]["row_count"] + dropped
        != expected_development_count
        or (dropped > 0 and not execution.drop_nan_labels)
    ):
        raise StrategyReportBundleError(
            "Cross search labelled population binding changed"
        )
    expected_provenance = {
        "schema_version": CROSS_CANDIDATE_SEARCH_ARTIFACT_SCHEMA_VERSION,
        "producer_version": CROSS_CANDIDATE_SEARCH_PRODUCER_VERSION,
        "task_id": binding.task_id,
        "search_id": result["search_id"],
        "search_content_hash": result["content_hash"],
        "request_hash": result["request_hash"],
        "source_artifact_id": getattr(source, "artifact_id", None),
        "source_artifact_content_hash": getattr(source, "content_hash", None),
        "candidate_id": result["source"]["candidate_id"],
        "evidence_hash": result["source"]["evidence_hash"],
        "dataset_id": getattr(dataset, "dataset_id", None),
        "dataset_content_hash": getattr(dataset, "content_hash", None),
        "registry_metadata_hash": getattr(
            dataset,
            "registry_metadata_hash",
            None,
        ),
        "workspace_revision": execution.workspace_revision,
        "workspace_generation": execution.workspace_generation,
        "semantic_mapping_hash": execution.semantic_mapping_hash,
        "sample_design_ref": execution.to_ref_dict(),
        "sample_context_hash": result["source"]["sample_context_hash"],
        "sample_partition": "risk/development",
        "target_col": execution.target_col,
        "drop_nan_labels": execution.drop_nan_labels,
        "nan_labels_dropped": dropped,
        "labeled_count": result["population"]["row_count"],
        "features": result["configuration"]["features"],
        "max_pairs": result["configuration"]["max_pairs"],
        "lifecycle": _CROSS_SEARCH_LIFECYCLE,
    }
    if provenance != expected_provenance:
        raise StrategyReportBundleError(
            "Cross search artifact provenance identity changed"
        )
    return result


def _authenticated_cross_rule_search(
    binding: CrossRuleSearchArtifactBinding,
    *,
    sample_binding: _StrategySampleDesignV2Binding,
    sample: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate aggregate threshold-rule evidence for the exact report sample."""

    _require_binding_type(
        binding,
        CrossRuleSearchArtifactBinding,
        "Cross rule search",
    )
    try:
        result = validate_cross_rule_search_result(binding.result)
    except StrategyError as exc:
        raise StrategyReportBundleError(
            "Cross rule search result evidence is invalid"
        ) from exc
    if result != binding.result or binding.task_id != sample_binding.task_id:
        raise StrategyReportBundleError(
            "Cross rule search binding identity changed"
        )
    _require_canonical_artifact_hash(
        binding.artifact_content_hash,
        canonical_cross_rule_search_result_json(result),
        "Cross rule search",
    )
    execution = binding.sample_binding
    _require_binding_type(
        execution,
        StrategyRiskDevelopmentExecutionBinding,
        "Cross rule search risk-development sample",
    )
    design = sample["sample_design"]
    identity = design["identity"]
    dataset_ref = identity["dataset_ref"]
    workspace_ref = identity["workspace_ref"]
    target = design["target_selector"]
    risk_population = next(
        (
            item
            for item in sample["populations"]
            if item["role"] == "risk"
        ),
        None,
    )
    development = (
        None
        if risk_population is None
        else next(
            (
                item
                for item in risk_population["partitions"]
                if item["name"] == "development"
            ),
            None,
        )
    )
    if development is None:
        raise StrategyReportBundleError(
            "Cross rule search sample-design development population is missing"
        )
    provenance = binding.artifact_provenance
    dropped = provenance.get("nan_labels_dropped")
    if (
        execution.to_ref_dict()
        != _sample_risk_development_ref(sample_binding)
        or execution.task_id != sample_binding.task_id
        or execution.dataset_id != dataset_ref["dataset_id"]
        or execution.dataset_content_hash != dataset_ref["content_hash"]
        or execution.workspace_revision != workspace_ref["revision"]
        or execution.workspace_generation != workspace_ref["generation"]
        or execution.semantic_mapping_hash
        != workspace_ref["semantic_mapping_hash"]
        or execution.target_col != target["column"]
        or execution.target_bad_value != target["bad_value"]
        or execution.drop_nan_labels != target["drop_missing"]
        or getattr(binding.dataset, "dataset_id", None)
        != dataset_ref["dataset_id"]
        or getattr(binding.dataset, "content_hash", None)
        != dataset_ref["content_hash"]
        or isinstance(dropped, bool)
        or not isinstance(dropped, int)
        or dropped < 0
        or result["population"]["row_count"] + dropped
        != development["row_count"]
    ):
        raise StrategyReportBundleError(
            "Cross rule search sample, target, or workspace changed"
        )
    if (
        provenance.get("search_id") != result["search_id"]
        or provenance.get("search_content_hash") != result["content_hash"]
        or provenance.get("sample_design_ref") != execution.to_ref_dict()
        or provenance.get("features") != result["configuration"]["features"]
        or provenance.get("dimension")
        != result["configuration"]["dimension"]
        or provenance.get("constraints")
        != result["configuration"]["constraints"]
        or provenance.get("max_trials")
        != result["configuration"]["max_trials"]
    ):
        raise StrategyReportBundleError(
            "Cross rule search provenance identity changed"
        )
    return result


def _authenticated_candidate_stability(
    binding: StrategyCandidateStabilityArtifactBinding,
) -> dict[str, Any]:
    _require_binding_type(
        binding,
        StrategyCandidateStabilityArtifactBinding,
        "candidate-stability",
    )
    try:
        stability = validate_candidate_stability_artifact(binding.stability)
    except StrategyError as exc:
        raise StrategyReportBundleError(
            "candidate-stability evidence is invalid"
        ) from exc
    if (
        stability != binding.stability
        or stability["identity"]["task_id"] != binding.task_id
    ):
        raise StrategyReportBundleError(
            "candidate-stability binding identity changed"
        )
    _require_canonical_artifact_hash(
        binding.artifact_content_hash,
        canonical_candidate_stability_artifact_json(stability),
        "candidate-stability",
    )
    _require_candidate_stability_provenance(binding, stability)
    return stability


def _require_candidate_stability_provenance(
    binding: StrategyCandidateStabilityArtifactBinding,
    stability: Mapping[str, Any],
) -> None:
    try:
        canonical = json.dumps(
            binding.artifact_provenance,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        provenance = json.loads(canonical)
    except (TypeError, ValueError, RecursionError) as exc:
        raise StrategyReportBundleError(
            "candidate-stability artifact provenance is invalid"
        ) from exc
    if (
        not isinstance(provenance, dict)
        or set(provenance) != _CANDIDATE_STABILITY_PROVENANCE_FIELDS
        or binding.artifact_provenance_json != canonical
    ):
        raise StrategyReportBundleError(
            "candidate-stability artifact provenance fields changed"
        )

    source = stability["source_ref"]
    identity = stability["identity"]
    bindings = stability["bindings"]
    expected = {
        "schema_version": CANDIDATE_STABILITY_ARTIFACT_SCHEMA_VERSION,
        "producer_version": CANDIDATE_STABILITY_PRODUCER_VERSION,
        "task_id": binding.task_id,
        "stability_id": stability["stability_id"],
        "stability_content_hash": stability["content_hash"],
        "basis": stability["basis"],
        "source_kind": source["source_kind"],
        "source_artifact_id": source["artifact_id"],
        "source_artifact_content_hash": source["artifact_content_hash"],
        "source_id": (
            source["asset_id"]
            if source["source_kind"] == "univariate_asset"
            else source["pool_id"]
        ),
        "source_hash": (
            source["asset_hash"]
            if source["source_kind"] == "univariate_asset"
            else source["snapshot_hash"]
        ),
        "rule_id": source["rule_id"],
        "entry_id": source.get("entry_id"),
        "pool_id": source.get("pool_id"),
        "pool_revision": source.get("revision"),
        "pool_revision_id": source.get("revision_id"),
        "dataset_id": identity["dataset_id"],
        "dataset_content_hash": identity["dataset_content_hash"],
        "workspace_revision": identity["workspace_revision"],
        "workspace_generation": identity["workspace_generation"],
        "semantic_mapping_hash": identity["semantic_mapping_hash"],
        "target_col": bindings["target_col"],
        "month_col": bindings["month_col"],
        "sample_design_ref": stability["sample_design_ref"],
        "sample_context_hash": identity["sample_context_hash"],
        "sample_partition": stability["sample_design_ref"]["partition"],
    }
    if provenance != expected:
        raise StrategyReportBundleError(
            "candidate-stability artifact provenance identity changed"
        )


def _require_candidate_stability_identity(
    *,
    stability: Mapping[str, Any],
    sample_binding: _StrategySampleDesignV2Binding,
    sample: Mapping[str, Any],
    pool: Mapping[str, Any],
    pool_binding: StrategyCandidatePoolArtifactBinding,
) -> None:
    identity = stability["identity"]
    design = sample["sample_design"]
    dataset = design["identity"]["dataset_ref"]
    workspace = design["identity"]["workspace_ref"]
    expected_identity = {
        "task_id": design["identity"]["task_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_content_hash": dataset["content_hash"],
        "workspace_revision": workspace["revision"],
        "workspace_generation": workspace["generation"],
        "semantic_mapping_hash": workspace["semantic_mapping_hash"],
    }
    if any(identity[key] != value for key, value in expected_identity.items()):
        raise StrategyReportBundleError(
            "candidate-stability dataset or workspace identity differs "
            "from SampleDesign V2"
        )

    if stability["sample_design_ref"] != _sample_risk_development_ref(
        sample_binding
    ):
        raise StrategyReportBundleError(
            "candidate-stability is not bound to the SampleDesign V2 "
            "risk/development sample"
        )

    target = design["target_selector"]
    month_col = design["sample_semantics"]["field_bindings"]["month_field"]
    bindings = stability["bindings"]
    if (
        target["status"] != "resolved"
        or target["column"] != bindings["target_col"]
        # Candidate stability consumes the governed risk/development frame
        # after the shared execution boundary normalizes bad polarity to 1.
        # The exact raw bad value remains authenticated by sample_design_ref.
        or bindings["target_bad_value"] != 1
        or not isinstance(month_col, str)
        or not month_col
        or month_col != bindings["month_col"]
    ):
        raise StrategyReportBundleError(
            "candidate-stability target or month semantics differ "
            "from SampleDesign V2"
        )
    if stability["lifecycle"] != _CANDIDATE_STABILITY_LIFECYCLE:
        raise StrategyReportBundleError(
            "candidate-stability must remain development, backtested, "
            "unvalidated, and non-mutating"
        )

    entry = _candidate_stability_pool_entry(
        stability=stability,
        pool=pool,
        pool_binding=pool_binding,
    )
    entry_source = entry["source"]
    if (
        entry_source["candidate_stage"] != "development"
        or entry_source["observation_stage"] != "backtested"
        or entry_source["validation_status"] != "unvalidated"
    ):
        raise StrategyReportBundleError(
            "candidate-stability Pool source must remain "
            "development/backtested/unvalidated"
        )
    evidence_identity = {
        key: identity[key]
        for key in (
            "dataset_id",
            "dataset_content_hash",
            "workspace_revision",
            "workspace_generation",
            "semantic_mapping_hash",
            "sample_context_hash",
        )
    }
    if entry_source["evidence_identity"] != evidence_identity:
        raise StrategyReportBundleError(
            "candidate-stability evidence identity differs "
            "from the current Pool entry source"
        )


def _candidate_stability_pool_entry(
    *,
    stability: Mapping[str, Any],
    pool: Mapping[str, Any],
    pool_binding: StrategyCandidatePoolArtifactBinding,
) -> Mapping[str, Any]:
    source = stability["source_ref"]
    if source["source_kind"] == "pool_entry":
        entries = [
            entry
            for entry in pool["entries"]
            if entry["entry_id"] == source["entry_id"]
        ]
        expected_source = {
            "source_kind": "pool_entry",
            "artifact_id": pool_binding.artifact_id,
            "artifact_content_hash": pool_binding.artifact_content_hash,
            "pool_id": pool["pool_id"],
            "revision": pool["revision"],
            "revision_id": pool["revision_id"],
            "snapshot_hash": pool["snapshot_hash"],
            "entry_id": source["entry_id"],
            "rule_id": entries[0]["rule_id"] if len(entries) == 1 else None,
        }
        if len(entries) != 1 or source != expected_source:
            raise StrategyReportBundleError(
                "candidate-stability does not reference the exact current "
                "Candidate Pool entry"
            )
        return entries[0]

    entries = [
        entry
        for entry in pool["entries"]
        if source
        == {
            "source_kind": "univariate_asset",
            "artifact_id": entry["source"]["artifact_id"],
            "artifact_content_hash": entry["source"][
                "artifact_content_hash"
            ],
            "asset_id": entry["source"]["asset_id"],
            "asset_hash": entry["source"]["asset_hash"],
            "rule_id": entry["rule_id"],
        }
    ]
    if len(entries) != 1:
        raise StrategyReportBundleError(
            "candidate-stability univariate source is not the exact source "
            "of one current Candidate Pool entry"
        )
    return entries[0]


def _candidate_stability_frozen_artifact_ref(
    stability: Mapping[str, Any],
    *,
    pool_ref: Mapping[str, str],
) -> dict[str, str]:
    """Return the exact artifact whose rules produced the stability mask."""

    source = stability["source_ref"]
    if source["source_kind"] == "pool_entry":
        return _artifact_ref(
            pool_ref["kind"],
            pool_ref["ref_id"],
            pool_ref["content_hash"],
        )
    if source["source_kind"] == "univariate_asset":
        return _artifact_ref(
            "strategy_candidate_asset",
            source["artifact_id"],
            source["artifact_content_hash"],
        )
    raise StrategyReportBundleError(
        "candidate-stability frozen source kind is unsupported"
    )


def _authenticated_pool_impact(
    binding: StrategyPoolImpactArtifactBinding,
) -> dict[str, Any]:
    _require_binding_type(
        binding,
        StrategyPoolImpactArtifactBinding,
        "pool-impact",
    )
    impact = validate_strategy_pool_impact_assessment(binding.assessment)
    lifecycle = impact["lifecycle"]
    if (
        impact != binding.assessment
        or impact["identity"]["task_id"] != binding.task_id
        or binding.stage != "development_backtest"
        or binding.validation_status != "unvalidated"
        or lifecycle
        != {
            "candidate_stage": "development",
            "observation_stage": "backtested",
            "validation_status": "unvalidated",
            "creates_strategy": False,
            "adopted": False,
            "deployed": False,
        }
    ):
        raise StrategyReportBundleError(
            "pool-impact must remain development, backtested, and unvalidated"
        )
    _require_canonical_artifact_hash(
        binding.artifact_content_hash,
        canonical_strategy_pool_impact_json(impact),
        "pool-impact",
    )
    return impact


def _authenticated_impact_cube(
    binding: StrategyImpactCubeArtifactBinding,
) -> dict[str, Any]:
    try:
        return _validate_impact_cube_binding(binding)
    except StrategyError as exc:
        raise StrategyReportBundleError(str(exc)) from exc


def _authenticated_model_evidence(
    binding: StrategyModelEvidenceV2ArtifactBinding,
    sample: Mapping[str, Any],
) -> dict[str, Any]:
    _require_binding_type(
        binding,
        StrategyModelEvidenceV2ArtifactBinding,
        "model-evidence V2",
    )
    bundle = validate_strategy_model_evidence_bundle(
        binding.bundle,
        sample_design_bundle=sample,
    )
    if bundle != binding.bundle or bundle["sample_design_binding"]["task_id"] != binding.task_id:
        raise StrategyReportBundleError(
            "model-evidence V2 binding identity changed"
        )
    _require_canonical_artifact_hash(
        binding.artifact_content_hash,
        canonical_strategy_model_evidence_bundle_json(
            bundle,
            sample_design_bundle=sample,
        ),
        "model-evidence V2",
    )
    return bundle


def _authenticated_training_evidence(
    binding: ModelingTrainingEvidenceArtifactBinding,
    sample: Mapping[str, Any],
) -> dict[str, Any]:
    _require_binding_type(
        binding,
        ModelingTrainingEvidenceArtifactBinding,
        "training-evidence",
    )
    evidence = validate_modeling_training_evidence(
        binding.evidence,
        sample_design_bundle=sample,
    )
    if evidence != binding.evidence or evidence["task_id"] != binding.task_id:
        raise StrategyReportBundleError(
            "training-evidence binding identity changed"
        )
    canonical = canonical_modeling_training_evidence_json(
        evidence,
        sample_design_bundle=sample,
    )
    _require_canonical_artifact_hash(
        _record_text(binding.evidence_record, "content_hash"),
        canonical,
        "training-evidence",
    )
    if (
        _record_text(binding.model_binary_record, "id")
        != evidence["model_artifact"]["model_binary_ref"]["artifact_id"]
        or _record_text(binding.model_binary_record, "content_hash")
        != evidence["model_artifact"]["model_binary_ref"]["content_hash"]
    ):
        raise StrategyReportBundleError(
            "training-evidence model artifact identity changed"
        )
    return evidence


def _authenticated_score_evidence(
    binding: ModelScoreEvidenceArtifactBinding,
    *,
    sample: Mapping[str, Any],
    training_binding: ModelingTrainingEvidenceArtifactBinding | None,
    training: Mapping[str, Any] | None,
) -> dict[str, Any]:
    _require_binding_type(
        binding,
        ModelScoreEvidenceArtifactBinding,
        "model-score-evidence",
    )
    if training_binding is None or training is None:
        raise StrategyReportBundleError(
            "model-score-evidence requires authenticated training evidence"
        )
    expected_ref = build_training_evidence_ref(training_binding)
    envelope = validate_model_score_evidence_envelope(
        binding.envelope,
        sample_design_bundle=sample,
        training_evidence=training,
        expected_training_evidence_ref=expected_ref,
        score_vector=binding.vector,
    )
    if envelope != binding.envelope or envelope["task_id"] != binding.task_id:
        raise StrategyReportBundleError(
            "model-score-evidence binding identity changed"
        )
    canonical = canonical_model_score_evidence_json(
        envelope,
        sample_design_bundle=sample,
        training_evidence=training,
        expected_training_evidence_ref=expected_ref,
        score_vector=binding.vector,
    )
    _require_canonical_artifact_hash(
        _record_text(binding.evidence_record, "content_hash"),
        canonical,
        "model-score-evidence",
    )
    if (
        _record_text(binding.vector_record, "id")
        != envelope["score_vector_ref"]["ref_id"]
        or _record_text(binding.vector_record, "content_hash")
        != envelope["score_vector_ref"]["content_hash"]
    ):
        raise StrategyReportBundleError(
            "model-score-evidence vector artifact identity changed"
        )
    return envelope


def _effective_training_binding(
    *,
    training_evidence: ModelingTrainingEvidenceArtifactBinding | None,
    score_evidence: ModelScoreEvidenceArtifactBinding | None,
) -> ModelingTrainingEvidenceArtifactBinding | None:
    if score_evidence is None:
        if training_evidence is not None:
            _require_binding_type(
                training_evidence,
                ModelingTrainingEvidenceArtifactBinding,
                "training-evidence",
            )
        return training_evidence
    _require_binding_type(
        score_evidence,
        ModelScoreEvidenceArtifactBinding,
        "model-score-evidence",
    )
    score_training = score_evidence.training
    _require_binding_type(
        score_training,
        ModelingTrainingEvidenceArtifactBinding,
        "model-score-evidence training",
    )
    if training_evidence is not None and _training_identity(
        training_evidence
    ) != _training_identity(score_training):
        raise StrategyReportBundleError(
            "model-score-evidence uses different training evidence"
        )
    return score_training


def _require_same_task(task_id: str, **bindings: object | None) -> None:
    for name, binding in bindings.items():
        if binding is not None and getattr(binding, "task_id", None) != task_id:
            raise StrategyReportBundleError(
                f"{name.replace('_', '-')} binding belongs to another task"
            )


def _require_sample_identity(
    *,
    sample_design: _StrategySampleDesignV2Binding,
    sample: Mapping[str, Any],
    model_evidence: StrategyModelEvidenceV2ArtifactBinding | None,
    training_evidence: ModelingTrainingEvidenceArtifactBinding | None,
    score_evidence: ModelScoreEvidenceArtifactBinding | None,
) -> None:
    expected = _sample_identity(sample_design)
    if (
        model_evidence is not None
        and _sample_identity(model_evidence.sample_design_binding) != expected
    ):
        raise StrategyReportBundleError(
            "model-evidence V2 references another sample design"
        )
    if (
        training_evidence is not None
        and _sample_identity(training_evidence.sample) != expected
    ):
        raise StrategyReportBundleError(
            "training-evidence references another sample design"
        )
    if score_evidence is not None and _sample_identity(
        score_evidence.training.sample
    ) != expected:
        raise StrategyReportBundleError(
            "model-score-evidence references another sample design"
        )
    design = sample["sample_design"]
    if (
        design["sample_design_id"] != expected["sample_design_id"]
        or design["content_hash"] != expected["sample_design_content_hash"]
    ):
        raise StrategyReportBundleError(
            "sample-design binding semantic identity changed"
        )


def _require_pool_impact_identity(
    *,
    sample_binding: _StrategySampleDesignV2Binding,
    sample: Mapping[str, Any],
    pool_binding: StrategyCandidatePoolArtifactBinding,
    pool: Mapping[str, Any],
    compiled_design: Mapping[str, Any],
    impact_binding: StrategyPoolImpactArtifactBinding,
    impact: Mapping[str, Any],
) -> None:
    if impact_binding.pool is not pool_binding and (
        impact_binding.pool.artifact_id != pool_binding.artifact_id
        or impact_binding.pool.artifact_content_hash
        != pool_binding.artifact_content_hash
    ):
        raise StrategyReportBundleError(
            "pool-impact references another candidate-pool artifact"
        )
    identity = impact["identity"]
    expected_pool = {
        "pool_id": pool["pool_id"],
        "task_id": pool["task_id"],
        "strategy_type": pool["strategy_type"],
        "revision": pool["revision"],
        "revision_id": pool["revision_id"],
        "snapshot_hash": pool["snapshot_hash"],
        "design_hash": compiled_design["design_hash"],
    }
    if any(identity[key] != value for key, value in expected_pool.items()):
        raise StrategyReportBundleError(
            "pool-impact candidate-pool identity changed"
        )
    if (
        impact["bindings"]["sample_design_ref"]
        != _sample_risk_development_ref(sample_binding)
    ):
        raise StrategyReportBundleError(
            "pool-impact is not bound to the V2 risk/development sample"
        )


def _require_impact_cube_identity(
    *,
    sample_binding: _StrategySampleDesignV2Binding,
    sample: Mapping[str, Any],
    pool_binding: StrategyCandidatePoolArtifactBinding,
    pool: Mapping[str, Any],
    compiled_design: Mapping[str, Any],
    impact_binding: StrategyImpactCubeArtifactBinding,
    cube: Mapping[str, Any],
) -> None:
    identity = cube["identity"]
    expected_pool = {
        "pool_id": pool["pool_id"],
        "task_id": pool["task_id"],
        "strategy_type": pool["strategy_type"],
        "revision": pool["revision"],
        "revision_id": pool["revision_id"],
        "snapshot_hash": pool["snapshot_hash"],
        "design_hash": compiled_design["design_hash"],
        "strategy_spec_hash": strategy_spec_hash(
            compiled_design["strategy_spec"]
        ),
    }
    if any(identity[key] != value for key, value in expected_pool.items()):
        raise StrategyReportBundleError(
            "ImpactCube candidate-pool identity changed"
        )
    requirements = compiled_design["requirements"]
    requirement_bindings = impact_binding.artifact_provenance.get(
        "requirement_bindings"
    )
    if requirements:
        virtual_fields: list[str] = []
        for outer in requirements:
            field = outer["requirement"]["virtual_field"]
            if field not in virtual_fields:
                virtual_fields.append(field)
        expected_requirement_bindings = {
            "requirements_hash": hashlib.sha256(
                json.dumps(
                    requirements,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest(),
            "requirements": requirements,
            "virtual_fields": virtual_fields,
        }
        if (
            impact_binding.artifact_provenance.get("schema_version")
            != IMPACT_CUBE_REQUIREMENTS_ARTIFACT_SCHEMA_VERSION
            or requirement_bindings != expected_requirement_bindings
        ):
            raise StrategyReportBundleError(
                "ImpactCube requirement bindings differ from the Candidate Pool"
            )
    elif (
        impact_binding.artifact_provenance.get("schema_version")
        != IMPACT_CUBE_ARTIFACT_SCHEMA_VERSION
        or requirement_bindings is not None
    ):
        raise StrategyReportBundleError(
            "ImpactCube requirement bindings differ from the Candidate Pool"
        )
    source = cube["source_bindings"]
    if source["pool_artifact"] != {
        "artifact_id": pool_binding.artifact_id,
        "artifact_content_hash": pool_binding.artifact_content_hash,
    }:
        raise StrategyReportBundleError(
            "ImpactCube references another candidate-pool artifact"
        )
    design = sample["sample_design"]
    header = sample_binding.membership["header"]
    source_sample = source["sample_design_v2"]
    expected_sample = {
        "membership_artifact_id": sample_binding.membership_artifact_id,
        "membership_artifact_content_hash": (
            sample_binding.membership_artifact_content_hash
        ),
        "membership_id": header["membership_id"],
        "membership_content_hash": header["content_hash"],
        "bundle_artifact_id": sample_binding.bundle_artifact_id,
        "bundle_artifact_content_hash": (
            sample_binding.bundle_artifact_content_hash
        ),
        "bundle_id": sample["bundle_id"],
        "bundle_content_hash": sample["content_hash"],
        "sample_design_id": design["sample_design_id"],
        "sample_design_content_hash": design["content_hash"],
        "analysis_universe_row_count": header["counts"][
            "analysis_universe"
        ],
        "partition_counts": {
            partition: header["counts"]["risk"][partition]
            for partition in ("development", "validation", "oot")
            if partition in source_sample["partition_counts"]
        },
        "population_partition_counts": {
            role: {
                partition: header["counts"][role][partition]
                for partition in ("development", "validation", "oot")
                if partition
                in source_sample["population_partition_counts"][role]
            }
            for role in ("approval", "risk")
        },
    }
    if source_sample != expected_sample:
        raise StrategyReportBundleError(
            "ImpactCube references another sample-design V2 artifact"
        )
    if not pool["entries"]:
        raise StrategyReportBundleError(
            "ImpactCube Candidate Pool has no development lineage"
        )
    expected_development_binding = {
        "task_id": pool["task_id"],
        **pool["entries"][0]["source"]["evidence_identity"],
    }
    if (
        source["development_lineage"]["sample_binding"]
        != expected_development_binding
    ):
        raise StrategyReportBundleError(
            "ImpactCube development lineage differs from the Candidate Pool"
        )
    dataset = design["identity"]["dataset_ref"]
    workspace = design["identity"]["workspace_ref"]
    source_dataset = source["dataset"]
    expected_dataset_identity = {
        "task_id": sample_binding.task_id,
        "dataset_id": dataset["dataset_id"],
        "dataset_content_hash": dataset["content_hash"],
        "workspace_revision": workspace["revision"],
        "workspace_generation": workspace["generation"],
        "semantic_mapping_hash": workspace["semantic_mapping_hash"],
    }
    if any(
        source_dataset[key] != value
        for key, value in expected_dataset_identity.items()
    ):
        raise StrategyReportBundleError(
            "ImpactCube dataset binding differs from the sample design"
        )
    target = design["target_selector"]
    if (
        source["target"]["column"] != target["column"]
        or source["target"]["good_value"] != target["good_value"]
        or source["target"]["bad_value"] != target["bad_value"]
        or source["development_lineage"]["legacy_development_ref"]
        != _sample_risk_development_ref(sample_binding)
        or impact_binding.task_id != sample_binding.task_id
    ):
        raise StrategyReportBundleError(
            "ImpactCube target or development lineage changed"
        )


def _require_pool_stability_identity(
    *,
    stability: Mapping[str, Any],
    stability_binding: StrategyPoolStabilityArtifactBinding,
    sample_binding: _StrategySampleDesignV2Binding,
    pool_binding: StrategyCandidatePoolArtifactBinding,
    pool: Mapping[str, Any],
    compiled_design: Mapping[str, Any],
    impact_binding: StrategyImpactCubeArtifactBinding,
    cube: Mapping[str, Any],
) -> None:
    source = stability["source_bindings"]
    expected_impact_ref = {
        "artifact_id": impact_binding.artifact_id,
        "expected_artifact_content_hash": (
            impact_binding.artifact_content_hash
        ),
        "expected_cube_id": cube["cube_id"],
        "expected_cube_content_hash": cube["content_hash"],
    }
    nested = stability_binding.impact_cube
    if (
        source["impact_cube"] != expected_impact_ref
        or stability_binding.task_id != sample_binding.task_id
        or nested.task_id != impact_binding.task_id
        or nested.artifact_id != impact_binding.artifact_id
        or nested.artifact_content_hash
        != impact_binding.artifact_content_hash
        or nested.cube != cube
    ):
        raise StrategyReportBundleError(
            "Pool stability does not reference the report's exact ImpactCube"
        )

    expected_pool = {
        "pool_id": pool["pool_id"],
        "task_id": pool["task_id"],
        "strategy_type": pool["strategy_type"],
        "revision": pool["revision"],
        "revision_id": pool["revision_id"],
        "snapshot_hash": pool["snapshot_hash"],
        "design_hash": compiled_design["design_hash"],
        "strategy_spec_hash": strategy_spec_hash(
            compiled_design["strategy_spec"]
        ),
    }
    cube_source = cube["source_bindings"]
    if (
        stability["identity"] != expected_pool
        or source["sample_design_v2"]
        != cube_source["sample_design_v2"]
        or source["dataset"] != cube_source["dataset"]
        or cube_source["pool_artifact"]
        != {
            "artifact_id": pool_binding.artifact_id,
            "artifact_content_hash": pool_binding.artifact_content_hash,
        }
    ):
        raise StrategyReportBundleError(
            "Pool stability evidence references another current Pool, "
            "SampleDesign V2, or dataset"
        )


def _current_project_section(
    revision: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    state = revision["state"]
    snapshot = state["current_project_snapshot"]
    fields = [
        _named(
            "scope",
            "Scope of the project",
            _projected_context_field(snapshot["scope"]),
        ),
        *(
            _named(
                f"current_{key}",
                label,
                _projected_context_field(snapshot["status_fields"][key]),
            )
            for key, label in (
                ("volume", "Current size"),
                ("approval", "Current through performance"),
                ("risk", "Current risk performance"),
                ("economics", "Current performance of proceeds"),
            )
        ),
        _named(
            "maturity_summary",
            "Sample maturity",
            _projected_context_field(snapshot["maturity_summary"]),
        ),
    ]
    return build_strategy_report_section(
        key="current_project",
        title=_SECTION_TITLES["current_project"],
        availability="present",
        summary_fields=fields,
        red_flags=[*snapshot["red_flags"], *state["red_flags"]],
        source_refs=[source_ref],
    )


def _history_section(
    revision: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    histories = revision["state"]["historical_strategy_reviews"]
    if not histories:
        return _absent_section(
            "historical_versions",
            "unavailable",
        )
    columns = [
        _column("version", "Version"),
        _column("effective_period", "Entry into force"),
        _column("asset_status", "Asset status"),
        _column("scope", "Policy Scope"),
        _column("traffic_allocation", "Flow distribution"),
        _column("evidence_status", "Proof status"),
    ]
    rows = []
    for history in histories:
        version_field = (
            _present_field(history["version"], source_ref)
            if history["version"] is not None
            else _absent_field("unavailable", note="No version number is provided for historical material.")
        )
        rows.append(
            {
                "row_id": history["review_id"],
                "cells": {
                    "version": version_field,
                    "effective_period": _projected_context_field(
                        history["effective_period"]
                    ),
                    "asset_status": _projected_context_field(
                        history["asset_status"]
                    ),
                    "scope": _projected_context_field(history["scope"]),
                    "traffic_allocation": _projected_context_field(
                        history["traffic_allocation"]
                    ),
                    "evidence_status": _present_field(
                        history["availability"],
                        source_ref,
                    ),
                },
            }
        )
    table = build_strategy_report_table(
        table_id="historical_strategy_versions",
        title="History Policy Version",
        sheet_key="02_history",
        granularity="aggregate",
        content_class="lineage",
        columns=columns,
        rows=rows,
        source_refs=[source_ref],
    )
    return build_strategy_report_section(
        key="historical_versions",
        title=_SECTION_TITLES["historical_versions"],
        availability="present",
        summary_fields=[
            _named(
                "historical_version_count",
                "Number of historical versions",
                _present_field(len(histories), source_ref),
            )
        ],
        tables=[table],
        red_flags=[
            flag
            for history in histories
            for flag in history["red_flags"]
        ],
        source_refs=[source_ref],
    )


def _sample_section(
    bundle: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    design = bundle["sample_design"]
    populations = {
        item["role"]: item
        for item in bundle["populations"]
    }
    risk_maturity = populations["risk"]["maturity_evidence"]
    maturity_field = _maturity_field(risk_maturity, source_ref)
    observations_by_definition = {
        item["metric_definition_id"]: item
        for item in bundle["metric_definitions"]
    }
    metric_rows = []
    for observation in bundle["metric_observations"]:
        definition = observations_by_definition[
            observation["metric_definition_ref"]["metric_definition_id"]
        ]
        metric_rows.append(
            {
                "row_id": observation["observation_id"],
                "cells": {
                    "population": _present_field(
                        observation["population"],
                        source_ref,
                    ),
                    "partition": _present_field(
                        observation["partition"],
                        source_ref,
                    ),
                    "metric": _present_field(
                        definition["display_name"],
                        source_ref,
                    ),
                    "value": _status_field(
                        observation["status"],
                        observation["value"],
                        source_ref,
                        status_map=_SAMPLE_STATUS_TO_AVAILABILITY,
                    ),
                    "unit": _present_field(
                        observation["unit"],
                        source_ref,
                    ),
                },
            }
        )
    table = build_strategy_report_table(
        table_id="sample_population_metrics",
        title="Sample divisional indicators",
        sheet_key="03_sample",
        granularity="aggregate",
        content_class="metric_summary",
        columns=[
            _column("population", "Sample caliber"),
            _column("partition", "Sample partition"),
            _column("metric", "Indicators"),
            _column("value", "Indicator value"),
            _column("unit", "Units"),
        ],
        rows=metric_rows,
        source_refs=[source_ref],
    )
    historical = bundle["historical_score"]
    historical_field = (
        _present_field("available", source_ref)
        if historical["status"] == "available"
        else _absent_field(
            "unavailable",
            note=historical["reason"],
        )
    )
    return build_strategy_report_section(
        key="sample_design",
        title=_SECTION_TITLES["sample_design"],
        availability="present",
        summary_fields=[
            _named(
                "sample_design_id",
                "Sample designID",
                _present_field(design["sample_design_id"], source_ref),
            ),
            _named(
                "sample_relationship",
                "Double sample relationship",
                _present_field(design["relationship"], source_ref),
            ),
            _named(
                "analysis_universe_count",
                "Analysis of the total sample",
                _present_field(bundle["membership"]["row_count"], source_ref),
            ),
            _named(
                "approval_population_count",
                "Samples approved",
                _present_field(populations["approval"]["total_count"], source_ref),
            ),
            _named(
                "risk_population_count",
                "Number of risk-caliber samples",
                _present_field(populations["risk"]["total_count"], source_ref),
            ),
            _named("risk_maturity", "Risk sample maturity", maturity_field),
            _named("historical_score", "History fraction availability", historical_field),
        ],
        tables=[table],
        red_flags=[
            {
                "code": item["code"],
                "level": "amber" if item["status"] == "warn" else "red",
                "message": item["message"],
                "source_refs": [source_ref],
            }
            for item in bundle["diagnostics"]
            if item["status"] in {"warn", "fail"}
        ],
        source_refs=[source_ref],
    )


def _model_section(
    *,
    model: Mapping[str, Any] | None,
    training: Mapping[str, Any] | None,
    score: Mapping[str, Any] | None,
    refs: _EvidenceRefs,
) -> dict[str, Any]:
    source_refs = [
        ref
        for ref in (refs.model, refs.training, refs.score)
        if ref is not None
    ]
    if not source_refs:
        return _absent_section(
            "univariate_and_models",
            "unavailable",
        )
    fields: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    if model is not None and refs.model is not None:
        fields.extend(
            [
                _named(
                    "univariate_evidence_count",
                    "Single variable analysis",
                    _present_field(len(model["univariate_evidence"]), refs.model),
                ),
                _named(
                    "model_evidence_count",
                    "Model evidence",
                    _present_field(len(model["model_evidence"]), refs.model),
                ),
                _named(
                    "model_comparison_count",
                    "Model comparison",
                    _present_field(len(model["comparison_evidence"]), refs.model),
                ),
            ]
        )
        observation_rows = _model_bundle_observation_rows(model, refs.model)
        if observation_rows:
            tables.append(
                _observation_table(
                    table_id="univariate_model_observations",
                    title="Single variables and model indicators",
                    rows=observation_rows,
                    source_ref=refs.model,
                )
            )
        tables.extend(_model_comparison_tables(model, refs.model))
    if training is not None and refs.training is not None:
        training_model_ref = _training_model_ref(training)
        fields.extend(
            [
                _named(
                    "training_algorithm",
                    "Training algorithms",
                    _present_field(
                        training["model_artifact"]["algorithm"],
                        refs.training,
                    ),
                ),
                _named(
                    "training_feature_count",
                    "Training features",
                    _present_field(
                        len(training["training_contract"]["features"]),
                        refs.training,
                    ),
                ),
                _named(
                    "training_selection_status",
                    "Model selection status",
                    _model_selection_field(
                        model=model,
                        model_ref=training_model_ref,
                        identity_ref=refs.training,
                        selection_ref=refs.model,
                    ),
                ),
            ]
        )
        metric_rows = [
            {
                "row_id": f"training-metric-{metric}",
                "cells": {
                    "metric": _present_field(metric, refs.training),
                    "value": (
                        _present_field(value, refs.training)
                        if value is not None
                        else _absent_field("unavailable")
                    ),
                },
            }
            for metric, value in sorted(
                training["metrics_snapshot"]["values"].items()
            )
        ]
        tables.append(
            build_strategy_report_table(
                table_id="training_metrics",
                title="Model training indicators",
                sheet_key="04_univariate_model",
                granularity="aggregate",
                content_class="metric_summary",
                columns=[
                    _column("metric", "Indicators"),
                    _column("value", "Indicator value"),
                ],
                rows=metric_rows,
                source_refs=[refs.training],
            )
        )
        importance_rows = [
            {
                "row_id": f"feature-importance-{index:05d}",
                "cells": {
                    "feature": _present_field(item["feature"], refs.training),
                    "importance": _present_field(
                        item["importance"],
                        refs.training,
                    ),
                },
            }
            for index, item in enumerate(training["feature_importance"])
        ]
        if importance_rows:
            tables.append(
                build_strategy_report_table(
                    table_id="training_feature_importance",
                    title="Characteristic importance",
                    sheet_key="04_univariate_model",
                    granularity="aggregate",
                    content_class="metric_summary",
                    columns=[
                        _column("feature", "Characteristics"),
                        _column("importance", "Importance"),
                    ],
                    rows=importance_rows,
                    source_refs=[refs.training],
                )
            )
    if score is not None and refs.score is not None:
        score_model_ref = score["single_model_evidence"]["model_ref"]
        fields.extend(
            [
                _named(
                    "score_product",
                    "Rating products",
                    _present_field(score["score_product"], refs.score),
                ),
                _named(
                    "score_row_count",
                    "Number of rows",
                    _present_field(
                        score["score_vector_contract"]["row_count"],
                        refs.score,
                    ),
                ),
                _named(
                    "score_selection_status",
                    "Rating Selection Status",
                    _model_selection_field(
                        model=model,
                        model_ref=score_model_ref,
                        identity_ref=refs.score,
                        selection_ref=refs.model,
                    ),
                ),
            ]
        )
        score_rows = _single_model_observation_rows(
            score["single_model_evidence"],
            refs.score,
            prefix="score",
        )
        if score_rows:
            tables.append(
                _observation_table(
                    table_id="governed_score_observations",
                    title="Model score indicator",
                    rows=score_rows,
                    source_ref=refs.score,
                )
            )
    return build_strategy_report_section(
        key="univariate_and_models",
        title=_SECTION_TITLES["univariate_and_models"],
        availability="present",
        summary_fields=fields,
        tables=tables,
        source_refs=source_refs,
    )


def _strategy_lifecycle_projection(
    value: Mapping[str, Any] | None,
    *,
    pool: Mapping[str, Any],
    pool_ref: Mapping[str, str],
) -> dict[str, Any]:
    if value is None:
        return {
            "strategy_status": "candidate",
            "adoption_status": "not_adopted",
            "deployment_status": "not_deployed",
            "creates_strategy": False,
            "source_ref": dict(pool_ref),
        }
    fields = {
        "strategy_id",
        "strategy_version",
        "strategy_type",
        "status",
        "asset_status",
        "source_ref",
    }
    if not isinstance(value, Mapping) or set(value) != fields:
        raise StrategyReportBundleError(
            "strategy lifecycle projection fields are invalid"
        )
    text_fields = {}
    for field in fields - {"source_ref"}:
        item = value[field]
        if not isinstance(item, str) or not item or item != item.strip():
            raise StrategyReportBundleError(
                f"strategy lifecycle {field} is invalid"
            )
        text_fields[field] = item
    if (
        text_fields["strategy_type"] != pool["strategy_type"]
        or not text_fields["strategy_version"].isdigit()
        or int(text_fields["strategy_version"]) < 1
    ):
        raise StrategyReportBundleError(
            "strategy lifecycle identity differs from the Candidate Pool"
        )
    try:
        asset_status = resolve_asset_status(
            text_fields["status"],
            text_fields["asset_status"],
        )
    except (TypeError, ValueError) as exc:
        raise StrategyReportBundleError(
            "strategy lifecycle status pair is invalid"
        ) from exc
    source = value["source_ref"]
    if not isinstance(source, Mapping):
        raise StrategyReportBundleError(
            "strategy lifecycle source reference is invalid"
        )
    source_ref = _artifact_ref(
        str(source.get("kind")),
        str(source.get("ref_id")),
        str(source.get("content_hash")),
    )
    lifecycle_body = {
        field: text_fields[field]
        for field in (
            "strategy_id",
            "strategy_version",
            "strategy_type",
            "status",
            "asset_status",
        )
    }
    expected_hash = hashlib.sha256(
        json.dumps(
            lifecycle_body,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    if (
        source_ref["kind"] != "strategy_lifecycle"
        or source_ref["ref_id"] != text_fields["strategy_id"]
        or source_ref["content_hash"] != expected_hash
    ):
        raise StrategyReportBundleError(
            "strategy lifecycle source identity changed"
        )
    adopted_local = (
        text_fields["status"] == "adopted"
        and asset_status == "adopted_local"
    )
    return {
        "strategy_status": text_fields["status"],
        "adoption_status": (
            "adopted" if adopted_local else "not_adopted"
        ),
        "deployment_status": asset_status,
        "creates_strategy": True,
        "source_ref": source_ref,
    }


def _candidate_section(
    *,
    pool: Mapping[str, Any],
    compiled_design: Mapping[str, Any],
    pool_ref: Mapping[str, str],
    scorecard_report: Mapping[str, Any],
    scorecard_backtest_refs: Sequence[Mapping[str, str]],
    scorecard_frozen_refs: Sequence[Mapping[str, str]],
    stability: Mapping[str, Any] | None,
    stability_ref: Mapping[str, str] | None,
    stability_source_ref: Mapping[str, str] | None,
    voting_search: Mapping[str, Any] | None,
    voting_search_ref: Mapping[str, str] | None,
    cross_search: Mapping[str, Any] | None,
    cross_search_ref: Mapping[str, str] | None,
    cross_rule_search: Mapping[str, Any] | None,
    cross_rule_search_ref: Mapping[str, str] | None,
    dataset_ref: Mapping[str, str],
    strategy_lifecycle: Mapping[str, Any],
) -> dict[str, Any]:
    source_ref = pool_ref
    lifecycle_ref = strategy_lifecycle["source_ref"]
    candidate_rows = [
        {
            "row_id": entry["entry_id"],
            "cells": {
                "position": _present_field(entry["position"] + 1, source_ref),
                "rule_id": _present_field(entry["rule_id"], source_ref),
                "asset_type": _present_field(
                    entry["source"]["asset_type"],
                    source_ref,
                ),
                "action": _present_field(entry["action"]["type"], source_ref),
                "candidate_stage": _present_field(
                    entry["source"]["candidate_stage"],
                    source_ref,
                ),
                "validation_status": _present_field(
                    entry["source"]["validation_status"],
                    source_ref,
                ),
                "adoption_status": _present_field(
                    strategy_lifecycle["adoption_status"],
                    lifecycle_ref,
                ),
                "deployment_status": _present_field(
                    strategy_lifecycle["deployment_status"],
                    lifecycle_ref,
                ),
            },
        }
        for entry in pool["entries"]
    ]
    candidates = build_strategy_report_table(
        table_id="candidate_pool_entries",
        title="Candidate Strategy Pool",
        sheet_key="05_candidates",
        granularity="aggregate",
        content_class="rule_summary",
        columns=[
            _column("position", "Order"),
            _column("rule_id", "RuleID"),
            _column("asset_type", "Candidate Type"),
            _column("action", "Actions"),
            _column("candidate_stage", "Candidate stage"),
            _column("validation_status", "Authentication status"),
            _column("adoption_status", "Adopt Status"),
            _column("deployment_status", "Local asset status"),
        ],
        rows=candidate_rows,
        source_refs=_dedupe_refs([source_ref, lifecycle_ref]),
    )
    strategy_rows = [
        {
            "row_id": f"compiled-rule-{item['rule_id']}",
            "cells": {
                "priority": _present_field(item["priority"], source_ref),
                "rule_id": _present_field(item["rule_id"], source_ref),
                "action": _present_field(item["action"]["type"], source_ref),
                "strategy_status": _present_field(
                    strategy_lifecycle["strategy_status"],
                    lifecycle_ref,
                ),
                "adoption_status": _present_field(
                    strategy_lifecycle["adoption_status"],
                    lifecycle_ref,
                ),
                "deployment_status": _present_field(
                    strategy_lifecycle["deployment_status"],
                    lifecycle_ref,
                ),
            },
        }
        for item in compiled_design["strategy_spec"]["rules"]
    ]
    strategy = build_strategy_report_table(
        table_id="compiled_candidate_design",
        title="Compiled candidate strategy design",
        sheet_key="06_strategy",
        granularity="aggregate",
        content_class="rule_summary",
        columns=[
            _column("priority", "Priority"),
            _column("rule_id", "RuleID"),
            _column("action", "Actions"),
            _column("strategy_status", "Policy Status"),
            _column("adoption_status", "Adopt Status"),
            _column("deployment_status", "Local asset status"),
        ],
        rows=strategy_rows,
        source_refs=_dedupe_refs([source_ref, lifecycle_ref]),
    )
    summary_fields = [
        _named(
            "candidate_count",
            "Number of candidates",
            _present_field(len(pool["entries"]), source_ref),
        ),
        _named(
            "pool_status",
            "Policy pool state",
            _present_field(pool["status"], source_ref),
        ),
        _named(
            "pool_validation_status",
            "Policy pool validation status",
            _present_field(pool["validation_status"], source_ref),
        ),
        _named(
            "compiled_design_hash",
            "Candidate for design Hashi",
            _present_field(compiled_design["design_hash"], source_ref),
        ),
        _named(
            "strategy_status",
            "Policy Status",
            _present_field(
                strategy_lifecycle["strategy_status"],
                lifecycle_ref,
            ),
        ),
        _named(
            "adoption_status",
            "Adopt Status",
            _present_field(
                strategy_lifecycle["adoption_status"],
                lifecycle_ref,
            ),
        ),
        _named(
            "deployment_status",
            "Local asset status",
            _present_field(
                strategy_lifecycle["deployment_status"],
                lifecycle_ref,
            ),
        ),
    ]
    tables = [candidates, strategy]
    scorecard_tables = _scorecard_report_tables(
        scorecard_report=scorecard_report,
        pool_ref=pool_ref,
        scorecard_backtest_refs=scorecard_backtest_refs,
    )
    tables.extend(scorecard_tables)
    if len(scorecard_backtest_refs) != len(scorecard_frozen_refs):
        raise StrategyReportBundleError(
            "scorecard stage role refs do not match"
        )
    stage_evidence: list[dict[str, Any]] = [
        {
            "effect_stage": "backtested",
            "population": "risk",
            "partition": "development",
            "binding": {
                "kind": "development_backtest",
                "dataset_ref": dataset_ref,
                "frozen_artifact_ref": frozen_ref,
                "result_ref": backtest_ref,
            },
        }
        for frozen_ref, backtest_ref in zip(
            scorecard_frozen_refs,
            scorecard_backtest_refs,
            strict=True,
        )
    ]
    red_flags: list[dict[str, Any]] = []
    section_refs = _dedupe_refs(
        [
            pool_ref,
            lifecycle_ref,
            *scorecard_report["artifact_refs"],
            *scorecard_backtest_refs,
            *scorecard_frozen_refs,
            *([] if not scorecard_backtest_refs else [dataset_ref]),
        ]
    )
    if stability is not None:
        if stability_ref is None or stability_source_ref is None:
            raise StrategyReportBundleError(
                "candidate-stability projection requires an authenticated "
                "backtest and frozen source reference"
            )
        stability_summary = stability["summary"]
        summary_fields.extend(
            [
                _named(
                    "candidate_stability_id",
                    "Evidence of candidate stabilityID",
                    _present_field(stability["stability_id"], stability_ref),
                ),
                _named(
                    "candidate_stability_basis",
                    "Candidate stability calibration",
                    _present_field(stability["basis"], stability_ref),
                ),
                _named(
                    "candidate_stability_population_count",
                    "Number of stable development samples",
                    _present_field(
                        stability_summary["population_count"],
                        stability_ref,
                    ),
                ),
                _named(
                    "candidate_stability_month_count",
                    "Number of steady months",
                    _present_field(
                        stability_summary["month_count"],
                        stability_ref,
                    ),
                ),
                _named(
                    "candidate_stability_max_psi",
                    "Maximum month-by-monthPSI",
                    _present_field(stability_summary["max_psi"], stability_ref),
                ),
                _named(
                    "candidate_stability_max_psi_month",
                    "MaxPSIMonth",
                    _present_field(
                        stability_summary["max_psi_month"],
                        stability_ref,
                    ),
                ),
                _named(
                    "candidate_stability_insufficient_month_count",
                    "Low sample months",
                    _present_field(
                        stability_summary["insufficient_month_count"],
                        stability_ref,
                    ),
                ),
                _named(
                    "candidate_stability_validation_status",
                    "Stability Verification Status",
                    _present_field(
                        stability["lifecycle"]["validation_status"],
                        stability_ref,
                    ),
                ),
            ]
        )
        tables.append(
            _candidate_stability_table(
                stability=stability,
                source_ref=stability_ref,
            )
        )
        stage_evidence.append(
            {
                "effect_stage": "backtested",
                "population": "risk",
                "partition": "development",
                "binding": {
                    "kind": "development_backtest",
                    "dataset_ref": dataset_ref,
                    "frozen_artifact_ref": stability_source_ref,
                    "result_ref": stability_ref,
                },
            }
        )
        red_flags.extend(
            {
                "code": "candidate_stability_insufficient_month_rows",
                "level": "amber",
                "message": (
                    f"Candidate month-on-month stability{item['month']} For low samples:"
                    f"{item['observed_rows']} Lines below minimum"
                    f"{item['minimum_rows']} rows; only indicating evidence strength."
                ),
                "source_refs": [stability_ref],
            }
            for item in stability["red_flags"]
        )
        section_refs = _dedupe_refs(
            [
                pool_ref,
                lifecycle_ref,
                *scorecard_report["artifact_refs"],
                *scorecard_backtest_refs,
                *scorecard_frozen_refs,
                dataset_ref,
                stability_source_ref,
                stability_ref,
            ]
        )
    if voting_search is not None:
        if voting_search_ref is None:
            raise StrategyReportBundleError(
                "Voting search projection requires an authenticated result reference"
            )
        voting_projection = _voting_search_report_projection(
            voting_search,
            source_ref=voting_search_ref,
        )
        summary_fields.extend(voting_projection["summary_fields"])
        tables.append(voting_projection["table"])
        stage_evidence.append(
            {
                "effect_stage": "backtested",
                "population": "risk",
                "partition": "development",
                "binding": {
                    "kind": "development_backtest",
                    "dataset_ref": dataset_ref,
                    "frozen_artifact_ref": pool_ref,
                    "result_ref": voting_search_ref,
                },
            }
        )
        section_refs = _dedupe_refs(
            [
                *section_refs,
                dataset_ref,
                voting_search_ref,
            ]
        )
    if cross_search is not None:
        if cross_search_ref is None:
            raise StrategyReportBundleError(
                "Cross search projection requires an authenticated result reference"
            )
        cross_projection = _cross_search_report_projection(
            cross_search,
            source_ref=cross_search_ref,
        )
        summary_fields.extend(cross_projection["summary_fields"])
        tables.append(cross_projection["table"])
        stage_evidence.append(
            {
                "effect_stage": "backtested",
                "population": "risk",
                "partition": "development",
                "binding": {
                    "kind": "development_backtest",
                    "dataset_ref": dataset_ref,
                    "frozen_artifact_ref": cross_search_ref,
                    "result_ref": cross_search_ref,
                },
            }
        )
        section_refs = _dedupe_refs(
            [
                *section_refs,
                dataset_ref,
                cross_search_ref,
            ]
        )
    if cross_rule_search is not None:
        if cross_rule_search_ref is None:
            raise StrategyReportBundleError(
                "Cross rule search projection requires an authenticated "
                "result reference"
            )
        projection = _cross_rule_search_report_projection(
            cross_rule_search,
            source_ref=cross_rule_search_ref,
        )
        summary_fields.extend(projection["summary_fields"])
        tables.append(projection["table"])
        stage_evidence.append(
            {
                "effect_stage": "backtested",
                "population": "risk",
                "partition": "development",
                "binding": {
                    "kind": "development_backtest",
                    "dataset_ref": dataset_ref,
                    "frozen_artifact_ref": cross_rule_search_ref,
                    "result_ref": cross_rule_search_ref,
                },
            }
        )
        section_refs = _dedupe_refs(
            [
                *section_refs,
                dataset_ref,
                cross_rule_search_ref,
            ]
        )
    return build_strategy_report_section(
        key="candidate_combinations",
        title=_SECTION_TITLES["candidate_combinations"],
        availability="present",
        summary_fields=summary_fields,
        tables=tables,
        stage_evidence=stage_evidence,
        red_flags=red_flags,
        source_refs=section_refs,
    )


def _voting_search_report_projection(
    result: Mapping[str, Any],
    *,
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    objective = result["configuration"]["objective"]
    combinations = list(
        result["combinations"][:_MAX_VOTING_SEARCH_REPORT_COMBINATIONS]
    )
    rows = [
        {
            "row_id": combination["combo_id"],
            "cells": {
                "search_id": _present_field(result["search_id"], source_ref),
                "combo_id": _present_field(
                    combination["combo_id"],
                    source_ref,
                ),
                "member_ids": _present_field(
                    list(combination["member_ids"]),
                    source_ref,
                ),
                "n": _present_field(combination["n"], source_ref),
                "eligible": _present_field(
                    combination["eligible"],
                    source_ref,
                ),
                "objective_metric": _present_field(
                    objective["metric"],
                    source_ref,
                ),
                "objective_direction": _present_field(
                    objective["direction"],
                    source_ref,
                ),
                "objective_value": _present_field(
                    combination["objective_value"],
                    source_ref,
                ),
                "constraint_failures": _present_field(
                    list(combination["constraint_failures"]),
                    source_ref,
                ),
                "metrics": _present_field(
                    dict(combination["metrics"]),
                    source_ref,
                ),
            },
        }
        for combination in combinations
    ]
    table = build_strategy_report_table(
        table_id="voting_candidate_search_combinations",
        title=_VOTING_SEARCH_REPORT_TITLE,
        sheet_key="appendix_voting_search",
        granularity="aggregate",
        content_class="metric_summary",
        effect_stage="backtested",
        columns=[
            _column("search_id", "SearchID"),
            _column("combo_id", "GroupID"),
            _column("member_ids", "Rules of membershipID"),
            _column("n", "Hit thresholdn"),
            _column("eligible", "Whether or not the binding has been adopted"),
            _column("objective_metric", "Target indicators"),
            _column("objective_direction", "Target orientation"),
            _column("objective_value", "Target value"),
            _column("constraint_failures", "No detail on binding"),
            _column("metrics", "Complete indicators"),
        ],
        rows=rows,
        source_refs=[source_ref],
    )
    return {
        "summary_fields": [
            _named(
                "voting_search_search_space",
                "VotingSearchspace",
                _present_field(result["search_space"], source_ref),
            ),
            _named(
                "voting_search_evaluated",
                "VotingNumber of combinations assessed",
                _present_field(result["evaluated"], source_ref),
            ),
            _named(
                "voting_search_truncated",
                "VotingSearch for break",
                _present_field(result["truncated"], source_ref),
            ),
            _named(
                "voting_search_eligible",
                "VotingNumber of binding combinations",
                _present_field(result["eligible"], source_ref),
            ),
            _named(
                "voting_search_displayed",
                "VotingNumber of reports presented in combination",
                _present_field(len(combinations), source_ref),
            ),
        ],
        "table": table,
    }


def _cross_search_report_projection(
    result: Mapping[str, Any],
    *,
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    pairs = list(result["pairs"][:_MAX_CROSS_SEARCH_REPORT_PAIRS])
    fields = (
        "pair_id",
        "x_feature",
        "x_method",
        "y_feature",
        "y_method",
        "x_axis_iv",
        "y_axis_iv",
        "cross_total_iv",
        "interaction_gain_iv",
        "cell_count",
        "empty_cell_count",
        "empty_cell_share",
        "min_nonempty_cell_count",
        "eligible",
        "rank",
    )
    rows = [
        {
            "row_id": pair["pair_id"],
            "cells": {
                field: _present_field(pair[field], source_ref)
                for field in fields
            },
        }
        for pair in pairs
    ]
    table = build_strategy_report_table(
        table_id="cross_candidate_search_pairs",
        title=_CROSS_SEARCH_REPORT_TITLE,
        sheet_key="appendix_cross_search",
        granularity="aggregate",
        content_class="metric_summary",
        effect_stage="backtested",
        columns=[
            _column("pair_id", "Fields CorrectID"),
            _column("x_feature", "XFields"),
            _column("x_method", "XBoxing method"),
            _column("y_feature", "YFields"),
            _column("y_method", "YBoxing method"),
            _column("x_axis_iv", "XAxisIV"),
            _column("y_axis_iv", "YAxisIV"),
            _column("cross_total_iv", "Cross-over GeneralIV"),
            _column("interaction_gain_iv", "Interactive GainsIV"),
            _column("cell_count", "Number of Cells"),
            _column("empty_cell_count", "Number of empty cells"),
            _column("empty_cell_share", "Empty Cells Ratio"),
            _column("min_nonempty_cell_count", "Number of minimum non-empty cell samples"),
            _column("eligible", "Whether the construction condition is met"),
            _column("rank", "Stable Sorting"),
        ],
        rows=rows,
        source_refs=[source_ref],
    )
    return {
        "summary_fields": [
            _named(
                "cross_search_search_space",
                "CrossSearchspace",
                _present_field(result["search_space"], source_ref),
            ),
            _named(
                "cross_search_evaluated",
                "Crossevaluated field logarithm",
                _present_field(result["evaluated"], source_ref),
            ),
            _named(
                "cross_search_truncated",
                "CrossSearch for break",
                _present_field(result["truncated"], source_ref),
            ),
            _named(
                "cross_search_eligible",
                "CrossBuilds field logarithms",
                _present_field(result["eligible"], source_ref),
            ),
            _named(
                "cross_search_displayed",
                "CrossReport display field logarithm",
                _present_field(len(pairs), source_ref),
            ),
        ],
        "table": table,
    }


def _cross_rule_search_report_projection(
    result: Mapping[str, Any],
    *,
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    rules = list(result["rules"][:_MAX_CROSS_RULE_REPORT_RULES])
    rows = []
    for rule in rules:
        condition_text = " AND ".join(
            (
                f"{item['feature']} {item['operator']} "
                f"{item['threshold']:g}"
                + (" OR missing" if item["include_missing"] else "")
            )
            for item in rule["conditions"]
        )
        failures = ",".join(rule["constraint_failures"])
        metrics = rule["metrics"]
        rows.append(
            {
                "row_id": rule["rule_id"],
                "cells": {
                    "rank": _present_field(rule["rank"], source_ref),
                    "rule_id": _present_field(rule["rule_id"], source_ref),
                    "conditions": _present_field(
                        condition_text,
                        source_ref,
                    ),
                    "eligible": _present_field(
                        rule["eligible"],
                        source_ref,
                    ),
                    "constraint_failures": _present_field(
                        failures,
                        source_ref,
                    ),
                    "count": _present_field(metrics["count"], source_ref),
                    "bad": _present_field(metrics["bad"], source_ref),
                    "hit_share": _present_field(
                        metrics["hit_share"],
                        source_ref,
                    ),
                    "bad_rate": _optional_metric_field(
                        metrics["bad_rate"],
                        source_ref,
                        note="cross_rule_bad_rate_undefined",
                    ),
                    "lift": _optional_metric_field(
                        metrics["lift"],
                        source_ref,
                        note="cross_rule_lift_undefined",
                    ),
                    "bad_capture_rate": _optional_metric_field(
                        metrics["bad_capture_rate"],
                        source_ref,
                        note="cross_rule_bad_capture_rate_undefined",
                    ),
                    "amount_lift": _optional_metric_field(
                        metrics["amount_lift"],
                        source_ref,
                        note="cross_rule_amount_lift_undefined",
                    ),
                },
            }
        )
    table = build_strategy_report_table(
        table_id="cross_threshold_rule_search",
        title=_CROSS_RULE_REPORT_TITLE,
        sheet_key="appendix_cross_rules",
        granularity="aggregate",
        content_class="metric_summary",
        effect_stage="backtested",
        columns=[
            _column("rank", "Stable Sorting"),
            _column("rule_id", "RuleID"),
            _column("conditions", "Cross-Conditions"),
            _column("eligible", "Whether to meet search constraints"),
            _column("constraint_failures", "Unsatisfied"),
            _column("count", "Number of hits"),
            _column("bad", "Number of hits and bad samples"),
            _column("hit_share", "Life-rate ratio"),
            _column("bad_rate", "Bad debt hit rate"),
            _column("lift", "RiskLift"),
            _column("bad_capture_rate", "Bad sample capture rate"),
            _column("amount_lift", "AmountLift"),
        ],
        rows=rows,
        source_refs=[source_ref],
    )
    configuration = result["configuration"]
    return {
        "summary_fields": [
            _named(
                "cross_rule_dimension",
                "CrossThreshold rule dimensions",
                _present_field(configuration["dimension"], source_ref),
            ),
            _named(
                "cross_rule_search_space",
                "CrossThreshold rule search space",
                _present_field(result["search_space"], source_ref),
            ),
            _named(
                "cross_rule_evaluated",
                "CrossThe threshold rule has been assessed",
                _present_field(result["evaluated"], source_ref),
            ),
            _named(
                "cross_rule_eligible",
                "CrossThreshold rule meets binding values",
                _present_field(result["eligible"], source_ref),
            ),
            _named(
                "cross_rule_truncated",
                "CrossThreshold rule search for cut-off",
                _present_field(result["truncated"], source_ref),
            ),
            _named(
                "cross_rule_displayed",
                "CrossShowcasing of threshold rule reports",
                _present_field(len(rules), source_ref),
            ),
        ],
        "table": table,
    }


def _scorecard_report_tables(
    *,
    scorecard_report: Mapping[str, Any],
    pool_ref: Mapping[str, str],
    scorecard_backtest_refs: Sequence[Mapping[str, str]],
) -> list[dict[str, Any]]:
    models = scorecard_report["models"]
    usages = scorecard_report["usages"]
    if not models:
        if usages or scorecard_report["artifact_refs"]:
            raise StrategyReportBundleError(
                "empty scorecard report projection contains orphan evidence"
            )
        return []
    if len(scorecard_backtest_refs) != len(models):
        raise StrategyReportBundleError(
            "scorecard backtest refs do not match projected models"
        )

    usages_by_model: dict[int, list[Mapping[str, Any]]] = {
        int(model["model_index"]): [] for model in models
    }
    for usage in usages:
        model_index = int(usage["model_index"])
        if model_index not in usages_by_model:
            raise StrategyReportBundleError(
                "scorecard usage references an unknown model"
            )
        usages_by_model[model_index].append(usage)

    summary_rows: list[dict[str, Any]] = []
    point_rows: list[dict[str, Any]] = []
    band_rows: list[dict[str, Any]] = []
    cutoff_rows: list[dict[str, Any]] = []
    all_refs: list[Mapping[str, str]] = [
        pool_ref,
        *scorecard_report["artifact_refs"],
        *scorecard_backtest_refs,
    ]

    for model, backtest_ref in zip(
        models,
        scorecard_backtest_refs,
        strict=True,
    ):
        model_index = int(model["model_index"])
        band_ref = _scorecard_artifact_ref(model["band_artifact_ref"])
        model_usages = usages_by_model[model_index]
        usage_refs = _dedupe_refs(
            [
                _scorecard_artifact_ref(ref)
                for usage in model_usages
                for ref in usage["usage_artifact_refs"]
            ]
        )
        model_refs = _dedupe_refs(
            [band_ref, pool_ref, backtest_ref, *usage_refs]
        )
        all_refs.extend(model_refs)
        path_values = [
            _scorecard_usage_path_value(path)
            for usage in model_usages
            for path in usage["usage_paths"]
        ]
        vector = model["sample_summary"]
        performance = model["performance"]
        lifecycle = model["lifecycle"]
        scale = model["scale"]
        summary_rows.append(
            {
                "row_id": f"scorecard-model-{model_index:03d}",
                "cells": {
                    "model_index": _present_field_many(
                        model_index,
                        model_refs,
                    ),
                    "score_product": _present_field(
                        model["score_product"], band_ref
                    ),
                    "score_direction": _present_field(
                        model["score_direction"], band_ref
                    ),
                    "points_direction": _present_field(
                        model["points_direction"], band_ref
                    ),
                    "row_count": _present_field(vector["row_count"], band_ref),
                    "development_count": _present_field(
                        vector["development_count"], band_ref
                    ),
                    "labeled_count": _present_field(
                        vector["labeled_count"], band_ref
                    ),
                    "bad_count": _present_field(vector["bad_count"], band_ref),
                    "auc": _present_field(performance["auc"], band_ref),
                    "ks": _present_field(performance["ks"], band_ref),
                    "base_score": _present_field(
                        scale["base_score"], band_ref
                    ),
                    "pdo": _present_field(scale["pdo"], band_ref),
                    "base_odds": _present_field(
                        scale["base_odds"], band_ref
                    ),
                    "factor": _present_field(scale["factor"], band_ref),
                    "offset": _present_field(scale["offset"], band_ref),
                    "band_count": _present_field(
                        len(model["bands"]), band_ref
                    ),
                    "cutoff_count": _present_field(
                        len(model["cutoffs"]), band_ref
                    ),
                    "candidate_stage": _present_field(
                        lifecycle["candidate_stage"], band_ref
                    ),
                    "observation_stage": _present_field(
                        lifecycle["observation_stage"], band_ref
                    ),
                    "validation_status": _present_field(
                        lifecycle["validation_status"], band_ref
                    ),
                    "usage_count": _present_field_many(
                        len(path_values), model_refs
                    ),
                    "usage_paths": _present_field_many(
                        path_values, model_refs
                    ),
                },
            }
        )

        for row_index, row in enumerate(model["scorecard_points"]):
            point_rows.append(
                {
                    "row_id": (
                        f"scorecard-points-{model_index:03d}-"
                        f"{row_index:06d}"
                    ),
                    "cells": {
                        "model_index": _present_field_many(
                            model_index,
                            model_refs,
                        ),
                        **{
                            key: _scorecard_optional_field(
                                row[key],
                                band_ref,
                                note=f"scorecard_{key}_not_applicable",
                            )
                            for key in (
                                "feature",
                                "bin_index",
                                "bin_label",
                                "lower",
                                "upper",
                                "count",
                                "bad_count",
                                "good_count",
                                "bad_rate",
                                "woe",
                                "iv_contribution",
                                "coefficient",
                                "monotonic_direction",
                                "points",
                            )
                        },
                    },
                }
            )

        for band in model["bands"]:
            band_rows.append(
                {
                    "row_id": (
                        f"scorecard-band-{model_index:03d}-"
                        f"{int(band['ordinal']):03d}"
                    ),
                    "cells": {
                        "model_index": _present_field_many(
                            model_index,
                            model_refs,
                        ),
                        "ordinal": _present_field(
                            band["ordinal"], band_ref
                        ),
                        "bin_id": _present_field(band["bin_id"], band_ref),
                        "lower_bound": _scorecard_boundary_field(
                            band["lower_bound"],
                            unbounded="−∞",
                            source_ref=band_ref,
                        ),
                        "upper_bound": _scorecard_boundary_field(
                            band["upper_bound"],
                            unbounded="+∞",
                            source_ref=band_ref,
                        ),
                        "lower_inclusive": _present_field(
                            band["lower_inclusive"], band_ref
                        ),
                        "upper_inclusive": _present_field(
                            band["upper_inclusive"], band_ref
                        ),
                        "count": _present_field(band["count"], band_ref),
                        "share": _present_field(band["share"], band_ref),
                        "labeled_count": _present_field(
                            band["labeled_count"], band_ref
                        ),
                        "bad_count": _present_field(
                            band["bad_count"], band_ref
                        ),
                        "bad_rate": _scorecard_optional_field(
                            band["bad_rate"],
                            band_ref,
                            note="scorecard_band_bad_rate_undefined",
                        ),
                        "average_pd": _present_field(
                            band["average_pd"], band_ref
                        ),
                    },
                }
            )

        for cutoff in model["cutoffs"]:
            selected_usages = [
                usage
                for usage in model_usages
                if usage["cutoff_id"] == cutoff["cutoff_id"]
            ]
            selected_refs = _dedupe_refs(
                (
                    [
                        band_ref,
                        pool_ref,
                        backtest_ref,
                        *[
                            _scorecard_artifact_ref(ref)
                            for usage in selected_usages
                            for ref in usage["usage_artifact_refs"]
                        ],
                    ]
                    if selected_usages
                    else model_refs
                )
            )
            selection_reasons = [
                usage["selection_reason"]
                for usage in selected_usages
                if usage["selection_reason"] is not None
            ]
            selected_paths = [
                _scorecard_usage_path_value(path)
                for usage in selected_usages
                for path in usage["usage_paths"]
            ]
            lower = cutoff["lower_risk"]
            higher = cutoff["higher_risk"]
            cutoff_rows.append(
                {
                    "row_id": (
                        f"scorecard-cutoff-{model_index:03d}-"
                        f"{int(cutoff['ordinal']):03d}"
                    ),
                    "cells": {
                        "model_index": _present_field_many(
                            model_index,
                            model_refs,
                        ),
                        "ordinal": _present_field(
                            cutoff["ordinal"], band_ref
                        ),
                        "cutoff_id": _present_field(
                            cutoff["cutoff_id"], band_ref
                        ),
                        "execution_pd": _present_field(
                            cutoff["execution_pd"], band_ref
                        ),
                        "display_points": _present_field(
                            cutoff["display_points"], band_ref
                        ),
                        "selected": _present_field_many(
                            bool(selected_usages), selected_refs
                        ),
                        "selection_reason": (
                            _present_field_many(
                                selection_reasons, selected_refs
                            )
                            if selection_reasons
                            else _absent_field(
                                "not_applicable",
                                note=(
                                    "scorecard_cutoff_not_selected"
                                    if not selected_usages
                                    else "selection_reason_not_provided"
                                ),
                            )
                        ),
                        "usage_paths": _present_field_many(
                            selected_paths, selected_refs
                        ),
                        "lower_risk_count": _present_field(
                            lower["count"], band_ref
                        ),
                        "lower_risk_labeled_count": _present_field(
                            lower["labeled_count"], band_ref
                        ),
                        "lower_risk_bad_count": _present_field(
                            lower["bad_count"], band_ref
                        ),
                        "lower_risk_bad_rate": _scorecard_optional_field(
                            lower["bad_rate"],
                            band_ref,
                            note="scorecard_lower_risk_bad_rate_undefined",
                        ),
                        "higher_risk_count": _present_field(
                            higher["count"], band_ref
                        ),
                        "higher_risk_labeled_count": _present_field(
                            higher["labeled_count"], band_ref
                        ),
                        "higher_risk_bad_count": _present_field(
                            higher["bad_count"], band_ref
                        ),
                        "higher_risk_bad_rate": _scorecard_optional_field(
                            higher["bad_rate"],
                            band_ref,
                            note="scorecard_higher_risk_bad_rate_undefined",
                        ),
                    },
                }
            )

    refs = _dedupe_refs(all_refs)
    tables = [
        build_strategy_report_table(
            table_id="scorecard_model_summary",
            title=(
                "Summary of the model of the scorecard (original)PDThe higher the risk, the higher the risk."
                "The higher the risk, the lower the score."
            ),
            sheet_key="05_candidates",
            granularity="aggregate",
            content_class="metric_summary",
            effect_stage="backtested",
            columns=[
                _column("model_index", "Model Serial Number"),
                _column("score_product", "Value-sensitive products"),
                _column("score_direction", "OriginalPDDirection"),
                _column("points_direction", "Rating card score orientation"),
                _column("row_count", "Full number of lines"),
                _column("development_count", "Number of samples developed"),
                _column("labeled_count", "Number of labeled samples"),
                _column("bad_count", "Number of bad samples"),
                _column("auc", "AUC", precision=6),
                _column("ks", "KS", precision=6),
                _column("base_score", "Basic Scores", precision=6),
                _column("pdo", "PDO", precision=6),
                _column("base_odds", "The base is so bad.", precision=6),
                _column("factor", "Factor", precision=6),
                _column("offset", "Offset", precision=6),
                _column("band_count", "Risk segment"),
                _column("cutoff_count", "Candidate threshold"),
                _column("candidate_stage", "Candidate stage"),
                _column("observation_stage", "Observation phase"),
                _column("validation_status", "Authentication status"),
                _column("usage_count", "PoolNumber of times used"),
                _column("usage_paths", "Pool/VotingUse Path"),
            ],
            rows=summary_rows,
            source_refs=refs,
        ),
        build_strategy_report_table(
            table_id="scorecard_points",
            title="Rating card score details (higher risk is lower)",
            sheet_key="appendix_scorecard",
            granularity="aggregate",
            content_class="bin_summary",
            effect_stage="backtested",
            columns=[
                _column("model_index", "Model Serial Number"),
                _column("feature", "Variables"),
                _column("bin_index", "Serial number of the box"),
                _column("bin_label", "Box Tab"),
                _column("lower", "Bottom"),
                _column("upper", "Upper boundary"),
                _column("count", "Number of samples"),
                _column("bad_count", "Number of bad samples"),
                _column("good_count", "Good sample numbers"),
                _column("bad_rate", "Bad sample rate", unit="%", precision=6),
                _column("woe", "WOE", precision=6),
                _column("iv_contribution", "IVContribution", precision=6),
                _column("coefficient", "coefficient", precision=6),
                _column("monotonic_direction", "Unarranged"),
                _column("points", "Scorecard Score", precision=6),
            ],
            rows=point_rows,
            source_refs=refs,
        ),
        build_strategy_report_table(
            table_id="scorecard_bands",
            title="Risk belt of the scorecard (original)PD(The higher the risk)",
            sheet_key="appendix_scorecard",
            granularity="aggregate",
            content_class="bin_summary",
            effect_stage="backtested",
            columns=[
                _column("model_index", "Model Serial Number"),
                _column("ordinal", "Serial number"),
                _column("bin_id", "SubbandID"),
                _column("lower_bound", "OriginalPDBottom"),
                _column("upper_bound", "OriginalPDUpper boundary"),
                _column("lower_inclusive", "Include Bottom"),
                _column("upper_inclusive", "Include Upper Boundaries"),
                _column("count", "Number of samples"),
                _column("share", "Samples as a percentage", unit="%", precision=6),
                _column("labeled_count", "Number of labeled samples"),
                _column("bad_count", "Number of bad samples"),
                _column("bad_rate", "Bad sample rate", unit="%", precision=6),
                _column("average_pd", "Average rawPD", precision=6),
            ],
            rows=band_rows,
            source_refs=refs,
        ),
        build_strategy_report_table(
            table_id="scorecard_cutoff_evaluations",
            title=(
                "Assessment of the full threshold of the scorecard (original)PDThe higher the risk, the higher the risk."
                "(The higher the higher the higher the higher the higher)"
            ),
            sheet_key="appendix_scorecard",
            granularity="aggregate",
            content_class="metric_summary",
            effect_stage="backtested",
            columns=[
                _column("model_index", "Model Serial Number"),
                _column("ordinal", "Threshold serial number"),
                _column("cutoff_id", "ThresholdID"),
                _column("execution_pd", "Pre-bio bad probability threshold", precision=8),
                _column("display_points", "Show points", precision=6),
                _column("selected", "Selected"),
                _column("selection_reason", "Reason for selection"),
                _column("usage_paths", "Pool/VotingUse Path"),
                _column("lower_risk_count", "Number of low-risk side samples"),
                _column("lower_risk_labeled_count", "Number of labels on low risk side"),
                _column("lower_risk_bad_count", "Number of low-risk side bad samples"),
                _column(
                    "lower_risk_bad_rate",
                    "Low risk side bad sample rate",
                    unit="%",
                    precision=6,
                ),
                _column("higher_risk_count", "Number of high-risk side samples"),
                _column("higher_risk_labeled_count", "Number of labels on high-risk sides"),
                _column("higher_risk_bad_count", "Number of high-risk side bad samples"),
                _column(
                    "higher_risk_bad_rate",
                    "High-risk side bad sample rate",
                    unit="%",
                    precision=6,
                ),
            ],
            rows=cutoff_rows,
            source_refs=refs,
        ),
    ]
    _enforce_scorecard_report_table_budget(tables)
    return tables


def _enforce_scorecard_report_table_budget(
    tables: Sequence[Mapping[str, Any]],
) -> None:
    field_count = sum(
        len(row["cells"])
        for table in tables
        for row in table["rows"]
    )
    ref_count = sum(
        len(table["source_refs"])
        + sum(
            len(field["source_refs"])
            for row in table["rows"]
            for field in row["cells"].values()
        )
        for table in tables
    )
    if field_count > _MAX_SCORECARD_REPORT_TABLE_FIELDS:
        raise StrategyReportBundleError(
            "scorecard report table fields exceed reserved budget"
        )
    if ref_count > _MAX_SCORECARD_REPORT_TABLE_REFS:
        raise StrategyReportBundleError(
            "scorecard report table references exceed reserved budget"
        )
    encoded = json.dumps(
        tables,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > _MAX_SCORECARD_REPORT_TABLE_JSON_BYTES:
        raise StrategyReportBundleError(
            "scorecard report table JSON exceeds reserved budget"
        )


def _scorecard_backtest_refs(
    scorecard_report: Mapping[str, Any],
) -> list[dict[str, str]]:
    # SourceRef.kind is the report-contract role, not the TaskArtifact kind.
    # The governed band artifact is a combined frozen scorecard contract and
    # development aggregate result; retain its exact id/hash for both roles.
    return [
        _artifact_ref(
            "backtest",
            str(model["band_artifact_ref"]["ref_id"]),
            str(model["band_artifact_ref"]["content_hash"]),
        )
        for model in scorecard_report["models"]
    ]


def _scorecard_frozen_refs(
    scorecard_report: Mapping[str, Any],
) -> list[dict[str, str]]:
    return [
        _artifact_ref(
            "strategy_candidate_asset",
            str(model["band_artifact_ref"]["ref_id"]),
            str(model["band_artifact_ref"]["content_hash"]),
        )
        for model in scorecard_report["models"]
    ]


def _scorecard_artifact_ref(value: Mapping[str, Any]) -> dict[str, str]:
    return _artifact_ref(
        str(value["kind"]),
        str(value["ref_id"]),
        str(value["content_hash"]),
    )


def _scorecard_usage_path_value(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "label": _scorecard_usage_path_label(value["path"]),
        "artifact_refs": [
            _scorecard_artifact_ref(ref)
            for ref in value["artifact_refs"]
        ],
    }


def _scorecard_usage_path_label(
    path: Sequence[Mapping[str, Any]],
) -> str:
    parts: list[str] = []
    for node in path:
        prefix = (
            "Pool"
            if node["scope"] == "current_pool_entry"
            else "Voting"
        )
        label = (
            f"{prefix}[{int(node['position']) + 1}]"
            f":{node['rule_id']}"
        )
        if node["voting_n"] is not None:
            label += f"(n={node['voting_n']},k={node['voting_k']})"
        parts.append(label)
    return " > ".join(parts)


def _scorecard_optional_field(
    value: Any,
    source_ref: Mapping[str, str],
    *,
    note: str,
) -> dict[str, Any]:
    if value is None:
        return _absent_field("not_applicable", note=note)
    return _present_field(value, source_ref)


def _scorecard_boundary_field(
    value: Any,
    *,
    unbounded: str,
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    return _present_field(unbounded if value is None else value, source_ref)


def _candidate_stability_table(
    *,
    stability: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    rows = [
        {
            "row_id": "candidate-stability-baseline",
            "cells": {
                "period": _present_field("development_baseline", source_ref),
                **_candidate_stability_metric_cells(
                    stability["baseline"],
                    source_ref,
                ),
            },
        },
        *[
            {
                "row_id": f"candidate-stability-month-{item['month']}",
                "cells": {
                    "period": _present_field(item["month"], source_ref),
                    **_candidate_stability_metric_cells(item, source_ref),
                },
            }
            for item in stability["monthly"]
        ],
    ]
    return build_strategy_report_table(
        table_id="candidate_monthly_stability",
        title="Candidate month-by-month stability (development return, not independently validated)",
        sheet_key="appendix_candidate_stability",
        granularity="aggregate",
        content_class="monthly_summary",
        effect_stage="backtested",
        columns=[
            _column("period", "Month/Baseline"),
            _column("sample_count", "Number of samples", unit="count", precision=0),
            _column("hit_count", "Hits", unit="count", precision=0),
            _column("not_hit_count", "Uncut", unit="count", precision=0),
            _column("hit_share", "Life-rate ratio", unit="%", precision=6),
            _column("not_hit_share", "I'm not sure if I'm gonna get my life back.", unit="%", precision=6),
            _column("labeled_count", "Number of labeled samples", unit="count", precision=0),
            _column("label_coverage", "Label Coverage", unit="%", precision=6),
            _column(
                "hit_labeled_count",
                "Hit and tag number",
                unit="count",
                precision=0,
            ),
            _column(
                "hit_bad_count",
                "Number of hits and bad samples",
                unit="count",
                precision=0,
            ),
            _column("hit_bad_rate", "Hit rate.", unit="%", precision=6),
            _column("psi_vs_development", "Relative development setPSI", precision=6),
        ],
        rows=rows,
        source_refs=[source_ref],
    )


def _candidate_stability_metric_cells(
    metrics: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    return {
        "sample_count": _present_field(metrics["sample_count"], source_ref),
        "hit_count": _present_field(metrics["hit_count"], source_ref),
        "not_hit_count": _present_field(metrics["not_hit_count"], source_ref),
        "hit_share": _present_field(metrics["hit_share"], source_ref),
        "not_hit_share": _present_field(metrics["not_hit_share"], source_ref),
        "labeled_count": _present_field(metrics["labeled_count"], source_ref),
        "label_coverage": _present_field(metrics["label_coverage"], source_ref),
        "hit_labeled_count": _present_field(
            metrics["hit_labeled_count"],
            source_ref,
        ),
        "hit_bad_count": _present_field(
            metrics["hit_bad_count"],
            source_ref,
        ),
        "hit_bad_rate": _nullable_metric_field(
            metrics["hit_bad_rate"],
            source_ref,
        ),
        "psi_vs_development": _present_field(
            metrics["psi_vs_development"],
            source_ref,
        ),
    }


def _impact_cube_section(
    *,
    cube: Mapping[str, Any],
    pool_ref: Mapping[str, str],
    impact_ref: Mapping[str, str],
    allow_oot_validated: bool,
) -> dict[str, Any]:
    lifecycle = cube["lifecycle"]
    family_fields = []
    for family, status in cube["slice_families"].items():
        family_fields.append(
            _named(
                f"{family}_status",
                f"{family}Slice Status",
                (
                    _present_field("present", impact_ref)
                    if status["availability"] == "present"
                    else _absent_field(
                        status["availability"],
                        note=status["reason"],
                    )
                ),
            )
        )
    summary_fields = [
        _named(
            "impact_cube_id",
            "ImpactCube ID",
            _present_field(cube["cube_id"], impact_ref),
        ),
        _named(
            "strategy_type",
            "Policy Type",
            _present_field(
                cube["identity"]["strategy_type"],
                impact_ref,
            ),
        ),
        _named(
            "impact_slice_count",
            "Impact slices",
            _present_field(len(cube["slices"]), impact_ref),
        ),
        _named(
            "impact_partitions",
            "Measurement partitions",
            _present_field(
                list(
                    dict.fromkeys(
                        row["name"] for row in cube["partitions"]
                    )
                ),
                impact_ref,
            ),
        ),
        _named(
            "impact_populations",
            "Measuring the population",
            _present_field(["approval", "risk"], impact_ref),
        ),
        _named(
            "creates_strategy",
            "Whether to create a policy",
            _present_field(lifecycle["creates_strategy"], impact_ref),
        ),
        _named(
            "adoption_status",
            "Adopt Status",
            _present_field("not_adopted", impact_ref),
        ),
        _named(
            "deployment_status",
            "Deployment status",
            _present_field("not_deployed", impact_ref),
        ),
        *family_fields,
    ]
    tables = [
        _impact_cube_partition_table(
            cube,
            impact_ref,
            allow_oot_validated=allow_oot_validated,
        ),
        _impact_cube_slices_table(cube, impact_ref),
        _impact_cube_waterfall_table(cube, impact_ref),
        _impact_cube_transitions_table(cube, impact_ref),
        _impact_cube_economics_table(cube, impact_ref),
    ]
    dataset_ref = _dataset_ref_from_impact_cube(cube)
    return build_strategy_report_section(
        key="impact_assessment",
        title=_SECTION_TITLES["impact_assessment"],
        availability="present",
        summary_fields=summary_fields,
        tables=tables,
        stage_evidence=[
            {
                "effect_stage": row["effect_stage"],
                "population": row["role"],
                "partition": row["name"],
                "binding": {
                    "kind": (
                        "development_backtest"
                        if row["effect_stage"] == "backtested"
                        else "independent_validation"
                    ),
                    "dataset_ref": dataset_ref,
                    "frozen_artifact_ref": pool_ref,
                    "result_ref": impact_ref,
                },
            }
            for row in cube["partitions"]
            if (
                row["effect_stage"] != "oot_validated"
                or allow_oot_validated
            )
        ],
        red_flags=[
            {
                "code": item["code"],
                "level": item["level"],
                "message": item["message"],
                "source_refs": [impact_ref],
            }
            for item in cube["red_flags"]
        ]
        + (
            []
            if allow_oot_validated
            else [
                {
                    "code": "oot_claim_suppressed_by_validation_blocker",
                    "level": "amber",
                    "message": (
                        "ImpactCube It's...validation/OOT The results of the partitions are still maintained in the table."
                        "However, the current authentication block has not been resolved and therefore the report does not stateOOT Authenticated."
                    ),
                    "source_refs": [impact_ref],
                }
            ]
        ),
        source_refs=[pool_ref, impact_ref],
    )


def _with_pool_validation_evidence(
    *,
    section: Mapping[str, Any],
    validations: Sequence[
        tuple[StrategyPoolValidationArtifactBinding, Mapping[str, Any]]
    ],
    validation_refs: Mapping[str, Mapping[str, str]],
    pool_ref: Mapping[str, str],
    claim_oot_validated: bool,
) -> dict[str, Any]:
    if not validations:
        return dict(section)
    typed_validation = (
        validations[0][1]["schema_version"]
        == STRATEGY_POOL_TYPED_VALIDATION_SCHEMA_VERSION
    )
    if any(
        (
            evidence["schema_version"]
            == STRATEGY_POOL_TYPED_VALIDATION_SCHEMA_VERSION
        )
        != typed_validation
        for _binding, evidence in validations
    ):
        raise StrategyReportBundleError(
            "Pool validation evidence versions cannot be mixed"
        )
    summary_fields = list(section["summary_fields"])
    for _binding, evidence in validations:
        partition = evidence["partition"]
        source_ref = validation_refs[partition]
        population = evidence["population_metrics"]
        if typed_validation:
            risk = evidence["risk_summary"]
            summary_fields.extend(
                [
                    _named(
                        f"pool_{partition}_validation_status",
                        f"{partition} Independent Replay Status",
                        _present_field(
                            evidence["lifecycle"]["validation_status"],
                            source_ref,
                        ),
                    ),
                    _named(
                        f"pool_{partition}_strategy_type",
                        f"{partition} Independence Replay Policy Type",
                        _present_field(
                            evidence["identity"]["strategy_type"],
                            source_ref,
                        ),
                    ),
                    _named(
                        f"pool_{partition}_population_count",
                        f"{partition} Number of samples re-played independently",
                        _present_field(
                            population["population_count"],
                            source_ref,
                        ),
                    ),
                    _named(
                        f"pool_{partition}_label_coverage",
                        f"{partition} Label Coverage",
                        _present_field(
                            population["label_coverage"],
                            source_ref,
                        ),
                    ),
                    _named(
                        f"pool_{partition}_overall_bad_rate",
                        f"{partition} Overall bad sample rate",
                        _nullable_metric_field(
                            risk["overall_bad_rate"],
                            source_ref,
                        ),
                    ),
                ]
            )
        else:
            metrics = evidence["overall"]["actions"]["metrics"]
            summary_fields.extend(
                [
                    _named(
                        f"pool_{partition}_validation_status",
                        f"{partition} Independent Replay Status",
                        _present_field(
                            evidence["lifecycle"]["validation_status"],
                            source_ref,
                        ),
                    ),
                    _named(
                        f"pool_{partition}_population_count",
                        f"{partition} Number of samples re-played independently",
                        _present_field(
                            population["population_count"],
                            source_ref,
                        ),
                    ),
                    _named(
                        f"pool_{partition}_label_coverage",
                        f"{partition} Label Coverage",
                        _present_field(
                            population["label_coverage"],
                            source_ref,
                        ),
                    ),
                    _named(
                        f"pool_{partition}_overall_bad_rate",
                        f"{partition} Overall bad sample rate",
                        _nullable_metric_field(
                            metrics["overall_bad_rate"],
                            source_ref,
                        ),
                    ),
                ]
            )
    if typed_validation:
        tables = [
            *section["tables"],
            _typed_pool_validation_summary_table(
                validations,
                validation_refs=validation_refs,
                claim_oot_validated=claim_oot_validated,
            ),
            _typed_pool_validation_distribution_table(
                validations,
                validation_refs=validation_refs,
                claim_oot_validated=claim_oot_validated,
            ),
        ]
        monthly = _typed_pool_validation_monthly_table(
            validations,
            validation_refs=validation_refs,
            claim_oot_validated=claim_oot_validated,
        )
    else:
        tables = [
            *section["tables"],
            _pool_validation_summary_table(
                validations,
                validation_refs=validation_refs,
                claim_oot_validated=claim_oot_validated,
            ),
            _pool_validation_action_table(
                validations,
                validation_refs=validation_refs,
                claim_oot_validated=claim_oot_validated,
            ),
        ]
        monthly = _pool_validation_monthly_table(
            validations,
            validation_refs=validation_refs,
            claim_oot_validated=claim_oot_validated,
        )
    if monthly is not None:
        tables.append(monthly)
    red_flags = [
        *section["red_flags"],
        *(
            {
                "code": (
                    f"pool_validation_{evidence['partition']}_"
                    f"{item['code']}"
                ),
                "level": item["level"],
                "message": (
                    f"{evidence['partition']} Independent re-play:{item['message']}"
                ),
                "source_refs": [validation_refs[evidence["partition"]]],
            }
            for _binding, evidence in validations
            for item in evidence["red_flags"]
        ),
    ]
    stage_evidence = list(section["stage_evidence"])
    if claim_oot_validated:
        stage_evidence.extend(
            {
                "effect_stage": "oot_validated",
                "population": "risk",
                "partition": evidence["partition"],
                "binding": {
                    "kind": "independent_validation",
                    "dataset_ref": _dataset_ref_from_pool_validation(
                        evidence
                    ),
                    "frozen_artifact_ref": pool_ref,
                    "result_ref": validation_refs[evidence["partition"]],
                },
            }
            for _binding, evidence in validations
        )
    else:
        red_flags.append(
            {
                "code": "pool_validation_claim_suppressed_by_validation_blocker",
                "level": "amber",
                "message": (
                    "Independencevalidation/OOT Re-play evidence retained but mature or other authentication"
                    "Blockage items have not been resolved, and therefore the report does not stateOOT Authenticated."
                ),
                "source_refs": list(validation_refs.values()),
            }
        )
    return build_strategy_report_section(
        key=section["key"],
        title=section["title"],
        availability=section["availability"],
        summary_fields=summary_fields,
        tables=tables,
        stage_evidence=stage_evidence,
        red_flags=red_flags,
        source_refs=_dedupe_refs(
            [*section["source_refs"], *validation_refs.values()]
        ),
    )


def _with_pool_stability_evidence(
    *,
    section: Mapping[str, Any],
    stability: Mapping[str, Any],
    stability_ref: Mapping[str, str],
) -> dict[str, Any]:
    table = _pool_stability_summary_table(stability, stability_ref)
    tables = list(section["tables"])
    insert_at = (
        1
        if tables and tables[0]["table_id"] == "impact_cube_partitions"
        else 0
    )
    tables.insert(insert_at, table)
    drift_flags = []
    for population, comparison, distribution in (
        _pool_stability_distributions(stability)
    ):
        severity = distribution["severity"]
        if severity == "stable":
            continue
        population_role = population["population_role"]
        partition = comparison["partition"]
        basis = distribution["basis"]
        drift_flags.append(
            {
                "code": (
                    "pool_stability_distribution_drift_"
                    f"{population_role}_{partition}_{basis}"
                ),
                "level": "amber" if severity == "warning" else "red",
                "message": (
                    f"Pool stability {population_role}/{partition}/{basis} "
                    f"PSI={float(distribution['psi']):.6g},"
                    f"{severity} Only means drift across partition distribution; does not mean effect validation,"
                    "OOT The project has been validated, strategy adopted or promoted."
                ),
                "source_refs": [stability_ref],
            }
        )
    return build_strategy_report_section(
        key=section["key"],
        title=section["title"],
        availability=section["availability"],
        summary_fields=section["summary_fields"],
        tables=tables,
        stage_evidence=section["stage_evidence"],
        red_flags=[*section["red_flags"], *drift_flags],
        source_refs=_dedupe_refs(
            [*section["source_refs"], stability_ref]
        ),
    )


def _pool_stability_summary_table(
    stability: Mapping[str, Any],
    stability_ref: Mapping[str, str],
) -> dict[str, Any]:
    rows = [
        {
            "row_id": (
                "pool-stability-"
                f"{population['population_role']}-"
                f"{comparison['partition']}-"
                f"{distribution['basis']}"
            ),
            "cells": {
                "population": _present_field(
                    population["population_role"],
                    stability_ref,
                ),
                "baseline_partition": _present_field(
                    stability["baseline_partition"],
                    stability_ref,
                ),
                "comparison_partition": _present_field(
                    comparison["partition"],
                    stability_ref,
                ),
                "basis": _present_field(
                    distribution["basis"],
                    stability_ref,
                ),
                "development_sample_count": _present_field(
                    distribution["development_sample_count"],
                    stability_ref,
                ),
                "comparison_sample_count": _present_field(
                    distribution["comparison_sample_count"],
                    stability_ref,
                ),
                "psi": _present_field(
                    distribution["psi"],
                    stability_ref,
                ),
                "max_abs_share_delta": _present_field(
                    distribution["max_abs_share_delta"],
                    stability_ref,
                ),
                "severity": _present_field(
                    distribution["severity"],
                    stability_ref,
                ),
            },
        }
        for population, comparison, distribution in (
            _pool_stability_distributions(stability)
        )
    ]
    if len(rows) > 8:
        raise StrategyReportBundleError(
            "Pool stability report summary exceeds eight rows"
        )
    return build_strategy_report_table(
        table_id="strategy_pool_stability_summary",
        title="Summary of stability of the distribution across the policy pool (non-effect validation)",
        sheet_key="10_validation",
        granularity="aggregate",
        content_class="metric_summary",
        effect_stage=None,
        columns=[
            _column("population", "Mass calibration"),
            _column("baseline_partition", "Base Zone"),
            _column("comparison_partition", "Comparative partitions"),
            _column("basis", "Distribution caliber"),
            _column(
                "development_sample_count",
                "Number of baseline samples",
                unit="count",
                precision=0,
            ),
            _column(
                "comparison_sample_count",
                "Comparison of sample numbers",
                unit="count",
                precision=0,
            ),
            _column("psi", "PSI", precision=6),
            _column(
                "max_abs_share_delta",
                "Maximum ratio difference",
                unit="%",
                precision=6,
            ),
            _column("severity", "Distribution drift level"),
        ],
        rows=rows,
        source_refs=[stability_ref],
    )


def _pool_stability_distributions(
    stability: Mapping[str, Any],
) -> list[
    tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]
]:
    return [
        (population, comparison, distribution)
        for population in stability["populations"]
        for comparison in population["comparisons"]
        for distribution in comparison["distributions"]
    ]


def _with_pool_validation_final_document(
    *,
    section: Mapping[str, Any],
    impact_section: Mapping[str, Any],
    validations: Sequence[
        tuple[StrategyPoolValidationArtifactBinding, Mapping[str, Any]]
    ],
    validation_refs: Mapping[str, Mapping[str, str]],
    claim_oot_validated: bool,
) -> dict[str, Any]:
    if not validations:
        return dict(section)
    stage_order = ("estimated", "backtested", "oot_validated")
    observed_stages = {
        item["effect_stage"] for item in impact_section["stage_evidence"]
    }
    evidence_stages = [
        stage for stage in stage_order if stage in observed_stages
    ]
    ref_values = list(validation_refs.values())
    summary_fields: list[dict[str, Any]] = []
    existing_statuses: list[str] = []
    existing_status_refs: list[Mapping[str, str]] = []
    for item in section["summary_fields"]:
        field_id = item["field_id"]
        if field_id in {"evidence_stage", "evidence_stages"}:
            prior_refs = item["field"]["source_refs"]
            summary_fields.append(
                _named(
                    "evidence_stages",
                    "Current evidence phase",
                    _present_field_many(
                        evidence_stages,
                        _dedupe_refs([*prior_refs, *ref_values]),
                    ),
                )
            )
            continue
        if field_id == "validation_statuses":
            value = item["field"]["value"]
            if isinstance(value, list):
                existing_statuses.extend(str(status) for status in value)
            existing_status_refs.extend(item["field"]["source_refs"])
            continue
        summary_fields.append(item)
    validation_statuses = list(
        dict.fromkeys([*existing_statuses, "independent_evidence"])
    )
    conclusion = (
        "independent_replay_evidence_only"
        if claim_oot_validated
        else (
            "independent_replay_evidence_available_"
            "claim_suppressed_by_validation_blocker"
        )
    )
    replay_partitions = [
        evidence["partition"] for _binding, evidence in validations
    ]
    summary_fields.extend(
        [
            _named(
                "validation_statuses",
                "Authentication status",
                _present_field_many(
                    validation_statuses,
                    _dedupe_refs([*existing_status_refs, *ref_values]),
                ),
            ),
            _named(
                "independent_replay_partitions",
                "Independencevalidation/OOT Backplay Partition",
                _present_field_many(
                    replay_partitions,
                    ref_values,
                ),
            ),
            _named(
                "validation_conclusion",
                "Independencevalidation/OOT Play back the conclusion.",
                _present_field_many(
                    conclusion,
                    ref_values,
                ),
            ),
        ]
    )
    return build_strategy_report_section(
        key=section["key"],
        title=section["title"],
        availability=section["availability"],
        summary_fields=summary_fields,
        tables=section["tables"],
        stage_evidence=section["stage_evidence"],
        red_flags=section["red_flags"],
        source_refs=_dedupe_refs(
            [*section["source_refs"], *ref_values]
        ),
    )


def _with_pool_stability_final_document(
    *,
    section: Mapping[str, Any],
    stability: Mapping[str, Any],
    stability_ref: Mapping[str, str],
) -> dict[str, Any]:
    distributions = _pool_stability_distributions(stability)
    severities = [
        item["severity"]
        for _population, _comparison, item in distributions
    ]
    summary = {
        "baseline_partition": stability["baseline_partition"],
        "comparison_partitions": stability["comparison_partitions"],
        "max_psi": max(
            float(item["psi"])
            for _population, _comparison, item in distributions
        ),
        "stable_count": severities.count("stable"),
        "warning_count": severities.count("warning"),
        "material_count": severities.count("material"),
        "scope": "distribution_drift_only",
    }
    return build_strategy_report_section(
        key=section["key"],
        title=section["title"],
        availability=section["availability"],
        summary_fields=[
            *section["summary_fields"],
            _named(
                "pool_stability_distribution_drift_summary",
                "Summary of stability of the distribution across the policy pool",
                _present_field(summary, stability_ref),
            ),
        ],
        tables=section["tables"],
        stage_evidence=section["stage_evidence"],
        red_flags=section["red_flags"],
        source_refs=_dedupe_refs(
            [*section["source_refs"], stability_ref]
        ),
    )


def _typed_pool_validation_strategy_type(
    validations: Sequence[
        tuple[StrategyPoolValidationArtifactBinding, Mapping[str, Any]]
    ],
) -> str:
    strategy_types = {
        str(evidence["identity"]["strategy_type"])
        for _binding, evidence in validations
    }
    if len(strategy_types) != 1:
        raise StrategyReportBundleError(
            "typed Pool validation strategy types changed"
        )
    strategy_type = strategy_types.pop()
    if strategy_type not in {"limit", "pricing", "segmentation"}:
        raise StrategyReportBundleError(
            "typed Pool validation strategy type is unsupported"
        )
    return strategy_type


def _typed_pool_headline_columns(
    strategy_type: str,
) -> list[dict[str, Any]]:
    if strategy_type == "limit":
        return [
            _column("total_limit", "Total Degrees", unit="amount", precision=2),
            _column("mean_limit", "Average", unit="amount", precision=2),
            _column("min_limit", "Minimum", unit="amount", precision=2),
            _column("max_limit", "Maximum", unit="amount", precision=2),
        ]
    if strategy_type == "pricing":
        return [
            _column("mean_rate", "Average price rate", unit="%", precision=6),
        ]
    return [
        _column("segment_count", "Group", unit="count", precision=0),
    ]


def _typed_pool_headline_cells(
    strategy_type: str,
    metrics: Mapping[str, Any],
    *,
    source_ref: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    keys = {
        "limit": ("total_limit", "mean_limit", "min_limit", "max_limit"),
        "pricing": ("mean_rate",),
        "segmentation": ("segment_count",),
    }[strategy_type]
    return {
        key: _nullable_metric_field(metrics[key], source_ref)
        for key in keys
    }


def _typed_pool_validation_summary_table(
    validations: Sequence[
        tuple[StrategyPoolValidationArtifactBinding, Mapping[str, Any]]
    ],
    *,
    validation_refs: Mapping[str, Mapping[str, str]],
    claim_oot_validated: bool,
) -> dict[str, Any]:
    strategy_type = _typed_pool_validation_strategy_type(validations)
    rows = []
    for _binding, evidence in validations:
        partition = evidence["partition"]
        source_ref = validation_refs[partition]
        population = evidence["population_metrics"]
        risk = evidence["risk_summary"]
        result = evidence["typed_backtest"]
        rows.append(
            {
                "row_id": f"pool-typed-independent-{partition}",
                "cells": {
                    "partition": _present_field(partition, source_ref),
                    "lifecycle_stage": _present_field(
                        evidence["lifecycle"]["stage"],
                        source_ref,
                    ),
                    "validation_status": _present_field(
                        evidence["lifecycle"]["validation_status"],
                        source_ref,
                    ),
                    "strategy_type": _present_field(
                        strategy_type,
                        source_ref,
                    ),
                    "population_count": _present_field(
                        population["population_count"],
                        source_ref,
                    ),
                    "labelled_count": _present_field(
                        population["labelled_count"],
                        source_ref,
                    ),
                    "unlabelled_count": _present_field(
                        population["unlabelled_count"],
                        source_ref,
                    ),
                    "label_coverage": _present_field(
                        population["label_coverage"],
                        source_ref,
                    ),
                    "overall_bad_count": _present_field(
                        risk["overall_bad_count"],
                        source_ref,
                    ),
                    "overall_bad_rate": _nullable_metric_field(
                        risk["overall_bad_rate"],
                        source_ref,
                    ),
                    "monthly_status": _present_field(
                        evidence["monthly"]["status"],
                        source_ref,
                    ),
                    **_typed_pool_headline_cells(
                        strategy_type,
                        result["metrics"],
                        source_ref=source_ref,
                    ),
                },
            }
        )
    return build_strategy_report_table(
        table_id="strategy_pool_typed_independent_validation_summary",
        title="Current Policy Pooltyped Independencevalidation/OOT Replay Summary",
        sheet_key="10_validation",
        granularity="aggregate",
        content_class="metric_summary",
        effect_stage=(
            "oot_validated" if claim_oot_validated else None
        ),
        columns=[
            _column("partition", "Sample partition"),
            _column("lifecycle_stage", "Evidence partition"),
            _column("validation_status", "Authentication status"),
            _column("strategy_type", "Policy Type"),
            _column("population_count", "Number of samples", unit="count", precision=0),
            _column("labelled_count", "Number of labels", unit="count", precision=0),
            _column("unlabelled_count", "No tags", unit="count", precision=0),
            _column("label_coverage", "Label Coverage", unit="%", precision=4),
            _column(
                "overall_bad_count",
                "Total number of bad samples",
                unit="count",
                precision=0,
            ),
            _column("overall_bad_rate", "Overall bad sample rate", unit="%", precision=4),
            _column("monthly_status", "Monthly result-on-line status"),
            *_typed_pool_headline_columns(strategy_type),
        ],
        rows=rows,
        source_refs=list(validation_refs.values()),
    )


def _typed_pool_distribution_value_column(
    strategy_type: str,
) -> dict[str, Any]:
    if strategy_type == "limit":
        return _column(
            "assigned_limit",
            "Amount allocated",
            unit="amount",
            precision=2,
        )
    if strategy_type == "pricing":
        return _column(
            "assigned_rate",
            "Distribution interest rate",
            unit="%",
            precision=6,
        )
    return _column("segment", "Group")


def _typed_pool_distribution_value_key(strategy_type: str) -> str:
    return {
        "limit": "assigned_limit",
        "pricing": "assigned_rate",
        "segmentation": "segment",
    }[strategy_type]


def _typed_pool_validation_distribution_table(
    validations: Sequence[
        tuple[StrategyPoolValidationArtifactBinding, Mapping[str, Any]]
    ],
    *,
    validation_refs: Mapping[str, Mapping[str, str]],
    claim_oot_validated: bool,
) -> dict[str, Any]:
    strategy_type = _typed_pool_validation_strategy_type(validations)
    value_key = _typed_pool_distribution_value_key(strategy_type)
    rows = []
    for _binding, evidence in validations:
        partition = evidence["partition"]
        source_ref = validation_refs[partition]
        for position, item in enumerate(
            evidence["typed_backtest"]["breakdown"]
        ):
            cells = {
                "partition": _present_field(partition, source_ref),
                "strategy_type": _present_field(
                    strategy_type,
                    source_ref,
                ),
                value_key: _present_field(item[value_key], source_ref),
                "count": _present_field(item["count"], source_ref),
                "share": _present_field(item["share"], source_ref),
                "labelled_count": _present_field(
                    item["labeled_count"],
                    source_ref,
                ),
                "bad_count": _present_field(
                    item["bad_count"],
                    source_ref,
                ),
                "bad_rate": _nullable_metric_field(
                    item["bad_rate"],
                    source_ref,
                ),
            }
            if strategy_type == "segmentation":
                cells["lift"] = _nullable_metric_field(
                    item["lift"],
                    source_ref,
                )
            rows.append(
                {
                    "row_id": (
                        f"pool-typed-independent-{partition}-{position}"
                    ),
                    "cells": cells,
                }
            )
    columns = [
        _column("partition", "Sample partition"),
        _column("strategy_type", "Policy Type"),
        _typed_pool_distribution_value_column(strategy_type),
        _column("count", "Number of samples", unit="count", precision=0),
        _column("share", "Samples as a percentage", unit="%", precision=4),
        _column("labelled_count", "Number of labels", unit="count", precision=0),
        _column("bad_count", "Number of bad samples", unit="count", precision=0),
        _column("bad_rate", "Bad sample rate", unit="%", precision=4),
    ]
    if strategy_type == "segmentation":
        columns.append(_column("lift", "Risk Upgrading", precision=4))
    return build_strategy_report_table(
        table_id="strategy_pool_typed_independent_validation_distribution",
        title="Current Policy Pooltyped Re-distribution of Independence",
        sheet_key="10_validation",
        granularity="aggregate",
        content_class="metric_summary",
        effect_stage=(
            "oot_validated" if claim_oot_validated else None
        ),
        columns=columns,
        rows=rows,
        source_refs=list(validation_refs.values()),
    )


def _typed_pool_validation_monthly_table(
    validations: Sequence[
        tuple[StrategyPoolValidationArtifactBinding, Mapping[str, Any]]
    ],
    *,
    validation_refs: Mapping[str, Mapping[str, str]],
    claim_oot_validated: bool,
) -> dict[str, Any] | None:
    strategy_type = _typed_pool_validation_strategy_type(validations)
    rows = []
    used_refs: list[Mapping[str, str]] = []
    for _binding, evidence in validations:
        monthly = evidence["monthly"]
        if monthly["status"] != "available":
            continue
        partition = evidence["partition"]
        source_ref = validation_refs[partition]
        used_refs.append(source_ref)
        for position, period in enumerate(monthly["periods"]):
            result = period["typed_backtest"]
            risk = period["risk_summary"]
            period_value = (
                "(null)" if period["value"] is None else period["value"]
            )
            rows.append(
                {
                    "row_id": (
                        f"pool-typed-independent-{partition}-monthly-"
                        f"{position}"
                    ),
                    "cells": {
                        "partition": _present_field(
                            partition,
                            source_ref,
                        ),
                        "period": _present_field(
                            period_value,
                            source_ref,
                        ),
                        "strategy_type": _present_field(
                            strategy_type,
                            source_ref,
                        ),
                        "population_count": _present_field(
                            result["population_count"],
                            source_ref,
                        ),
                        "labelled_count": _present_field(
                            result["labeled_count"],
                            source_ref,
                        ),
                        "label_coverage": _present_field(
                            result["label_coverage"],
                            source_ref,
                        ),
                        "overall_bad_count": _present_field(
                            risk["overall_bad_count"],
                            source_ref,
                        ),
                        "overall_bad_rate": _nullable_metric_field(
                            risk["overall_bad_rate"],
                            source_ref,
                        ),
                        **_typed_pool_headline_cells(
                            strategy_type,
                            result["metrics"],
                            source_ref=source_ref,
                        ),
                    },
                }
            )
    if not rows:
        return None
    return build_strategy_report_table(
        table_id="strategy_pool_typed_independent_validation_monthly",
        title="Current Policy Pooltyped Independent re-departure monthly effect",
        sheet_key="10_validation",
        granularity="aggregate",
        content_class="monthly_summary",
        effect_stage=(
            "oot_validated" if claim_oot_validated else None
        ),
        columns=[
            _column("partition", "Sample partition"),
            _column("period", "Month"),
            _column("strategy_type", "Policy Type"),
            _column("population_count", "Number of samples", unit="count", precision=0),
            _column("labelled_count", "Number of labels", unit="count", precision=0),
            _column("label_coverage", "Label Coverage", unit="%", precision=4),
            _column(
                "overall_bad_count",
                "Total number of bad samples",
                unit="count",
                precision=0,
            ),
            _column("overall_bad_rate", "Overall bad sample rate", unit="%", precision=4),
            *_typed_pool_headline_columns(strategy_type),
        ],
        rows=rows,
        source_refs=_dedupe_refs(used_refs),
    )


def _pool_validation_summary_table(
    validations: Sequence[
        tuple[StrategyPoolValidationArtifactBinding, Mapping[str, Any]]
    ],
    *,
    validation_refs: Mapping[str, Mapping[str, str]],
    claim_oot_validated: bool,
) -> dict[str, Any]:
    rows = []
    for _binding, evidence in validations:
        partition = evidence["partition"]
        source_ref = validation_refs[partition]
        population = evidence["population_metrics"]
        effect = evidence["overall"]["effect"]
        metrics = evidence["overall"]["actions"]["metrics"]
        amounts = effect["amounts"]
        rows.append(
            {
                "row_id": f"pool-independent-{partition}",
                "cells": {
                    "partition": _present_field(partition, source_ref),
                    "lifecycle_stage": _present_field(
                        evidence["lifecycle"]["stage"],
                        source_ref,
                    ),
                    "validation_status": _present_field(
                        evidence["lifecycle"]["validation_status"],
                        source_ref,
                    ),
                    "population_count": _present_field(
                        population["population_count"],
                        source_ref,
                    ),
                    "labelled_count": _present_field(
                        population["labelled_count"],
                        source_ref,
                    ),
                    "unlabelled_count": _present_field(
                        population["unlabelled_count"],
                        source_ref,
                    ),
                    "label_coverage": _present_field(
                        population["label_coverage"],
                        source_ref,
                    ),
                    "approve_rate": _present_field(
                        metrics["approve_rate"],
                        source_ref,
                    ),
                    "reject_rate": _present_field(
                        metrics["reject_rate"],
                        source_ref,
                    ),
                    "review_rate": _present_field(
                        metrics["review_rate"],
                        source_ref,
                    ),
                    "overall_bad_rate": _nullable_metric_field(
                        metrics["overall_bad_rate"],
                        source_ref,
                    ),
                    "overall_bad_count": _present_field(
                        metrics["overall_bad_count"],
                        source_ref,
                    ),
                    "bad_capture_rate": _nullable_metric_field(
                        metrics["bad_capture_rate"],
                        source_ref,
                    ),
                    "good_reject_rate": _nullable_metric_field(
                        metrics["good_reject_rate"],
                        source_ref,
                    ),
                    "monthly_status": _present_field(
                        evidence["monthly"]["status"],
                        source_ref,
                    ),
                    **_pool_validation_amount_cells(
                        amounts,
                        source_ref=source_ref,
                    ),
                },
            }
        )
    return build_strategy_report_table(
        table_id="strategy_pool_independent_validation_summary",
        title="Current Strategy Pool Independencevalidation/OOT Replay Summary",
        sheet_key="10_validation",
        granularity="aggregate",
        content_class="metric_summary",
        effect_stage=(
            "oot_validated" if claim_oot_validated else None
        ),
        columns=[
            _column("partition", "Sample partition"),
            _column("lifecycle_stage", "Evidence partition"),
            _column("validation_status", "Authentication status"),
            _column("population_count", "Number of samples", unit="count", precision=0),
            _column("labelled_count", "Number of labels", unit="count", precision=0),
            _column("unlabelled_count", "No tags", unit="count", precision=0),
            _column("label_coverage", "Label Coverage", unit="%", precision=4),
            _column("approve_rate", "Pass rate", unit="%", precision=4),
            _column("reject_rate", "Rate of rejection", unit="%", precision=4),
            _column("review_rate", "Review rate", unit="%", precision=4),
            _column("overall_bad_rate", "Overall bad sample rate", unit="%", precision=4),
            _column(
                "overall_bad_count",
                "Total number of bad samples",
                unit="count",
                precision=0,
            ),
            _column("bad_capture_rate", "Bad sample capture rate", unit="%", precision=4),
            _column("good_reject_rate", "Good sample failure rate.", unit="%", precision=4),
            _column("monthly_status", "Monthly result-on-line status"),
            *_pool_validation_amount_columns(),
        ],
        rows=rows,
        source_refs=list(validation_refs.values()),
    )


def _pool_validation_action_table(
    validations: Sequence[
        tuple[StrategyPoolValidationArtifactBinding, Mapping[str, Any]]
    ],
    *,
    validation_refs: Mapping[str, Mapping[str, str]],
    claim_oot_validated: bool,
) -> dict[str, Any]:
    rows = []
    for _binding, evidence in validations:
        partition = evidence["partition"]
        source_ref = validation_refs[partition]
        for action in evidence["overall"]["actions"]["breakdown"]:
            rows.append(
                {
                    "row_id": (
                        f"pool-independent-{partition}-{action['action']}"
                    ),
                    "cells": {
                        "partition": _present_field(partition, source_ref),
                        "action": _present_field(
                            action["action"],
                            source_ref,
                        ),
                        "count": _present_field(action["count"], source_ref),
                        "rate": _present_field(action["rate"], source_ref),
                        "labelled_count": _present_field(
                            action["labelled_count"],
                            source_ref,
                        ),
                        "bad_count": _present_field(
                            action["bad_count"],
                            source_ref,
                        ),
                        "bad_rate": _nullable_metric_field(
                            action["bad_rate"],
                            source_ref,
                        ),
                    },
                }
            )
    return build_strategy_report_table(
        table_id="strategy_pool_independent_validation_actions",
        title="Replay action effects independently of current policy pool",
        sheet_key="10_validation",
        granularity="aggregate",
        content_class="metric_summary",
        effect_stage=(
            "oot_validated" if claim_oot_validated else None
        ),
        columns=[
            _column("partition", "Sample partition"),
            _column("action", "Actions"),
            _column("count", "Number of samples", unit="count", precision=0),
            _column("rate", "Samples as a percentage", unit="%", precision=4),
            _column("labelled_count", "Number of labels", unit="count", precision=0),
            _column("bad_count", "Number of bad samples", unit="count", precision=0),
            _column("bad_rate", "Bad sample rate", unit="%", precision=4),
        ],
        rows=rows,
        source_refs=list(validation_refs.values()),
    )


def _pool_validation_monthly_table(
    validations: Sequence[
        tuple[StrategyPoolValidationArtifactBinding, Mapping[str, Any]]
    ],
    *,
    validation_refs: Mapping[str, Mapping[str, str]],
    claim_oot_validated: bool,
) -> dict[str, Any] | None:
    rows = []
    used_refs: list[Mapping[str, str]] = []
    for _binding, evidence in validations:
        monthly = evidence["monthly"]
        if monthly["status"] != "available":
            continue
        partition = evidence["partition"]
        source_ref = validation_refs[partition]
        used_refs.append(source_ref)
        for period in monthly["periods"]:
            metrics = period["actions"]["metrics"]
            effect = period["effect"]
            rows.append(
                {
                    "row_id": (
                        f"pool-independent-{partition}-{period['period']}"
                    ),
                    "cells": {
                        "partition": _present_field(partition, source_ref),
                        "period": _present_field(
                            period["period"],
                            source_ref,
                        ),
                        "population_count": _present_field(
                            effect["population_count"],
                            source_ref,
                        ),
                        "labelled_count": _present_field(
                            effect["labelled_count"],
                            source_ref,
                        ),
                        "label_coverage": _present_field(
                            effect["label_coverage"],
                            source_ref,
                        ),
                        "bad_count": _present_field(
                            effect["bad_count"],
                            source_ref,
                        ),
                        "approve_rate": _present_field(
                            metrics["approve_rate"],
                            source_ref,
                        ),
                        "reject_rate": _present_field(
                            metrics["reject_rate"],
                            source_ref,
                        ),
                        "review_rate": _present_field(
                            metrics["review_rate"],
                            source_ref,
                        ),
                        "overall_bad_rate": _nullable_metric_field(
                            metrics["overall_bad_rate"],
                            source_ref,
                        ),
                        "bad_capture_rate": _nullable_metric_field(
                            metrics["bad_capture_rate"],
                            source_ref,
                        ),
                        "good_reject_rate": _nullable_metric_field(
                            metrics["good_reject_rate"],
                            source_ref,
                        ),
                        **_pool_validation_amount_cells(
                            effect["amounts"],
                            source_ref=source_ref,
                        ),
                    },
                }
            )
    if not rows:
        return None
    return build_strategy_report_table(
        table_id="strategy_pool_independent_validation_monthly",
        title="Current Policy Pool Independently Re-exiles Month Effects",
        sheet_key="10_validation",
        granularity="aggregate",
        content_class="monthly_summary",
        effect_stage=(
            "oot_validated" if claim_oot_validated else None
        ),
        columns=[
            _column("partition", "Sample partition"),
            _column("period", "Month"),
            _column("population_count", "Number of samples", unit="count", precision=0),
            _column("labelled_count", "Number of labels", unit="count", precision=0),
            _column("label_coverage", "Label Coverage", unit="%", precision=4),
            _column("bad_count", "Number of bad samples", unit="count", precision=0),
            _column("approve_rate", "Pass rate", unit="%", precision=4),
            _column("reject_rate", "Rate of rejection", unit="%", precision=4),
            _column("review_rate", "Review rate", unit="%", precision=4),
            _column("overall_bad_rate", "Overall bad sample rate", unit="%", precision=4),
            _column("bad_capture_rate", "Bad sample capture rate", unit="%", precision=4),
            _column("good_reject_rate", "Good sample failure rate.", unit="%", precision=4),
            *_pool_validation_amount_columns(),
        ],
        rows=rows,
        source_refs=_dedupe_refs(used_refs),
    )


def _pool_validation_amount_cells(
    amounts: Mapping[str, Any],
    *,
    source_ref: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    return {
        "loan_amount_status": _pool_validation_amount_field(
            amounts,
            amount_key="loan_amount",
            field="status",
            source_ref=source_ref,
        ),
        "loan_amount_coverage_count": _pool_validation_amount_field(
            amounts,
            amount_key="loan_amount",
            field="coverage_count",
            source_ref=source_ref,
        ),
        "loan_amount_coverage_rate": _pool_validation_amount_field(
            amounts,
            amount_key="loan_amount",
            field="coverage_rate",
            source_ref=source_ref,
        ),
        "loan_amount_sum": _pool_validation_amount_field(
            amounts,
            amount_key="loan_amount",
            field="sum",
            source_ref=source_ref,
        ),
        "overdue_amount_status": _pool_validation_amount_field(
            amounts,
            amount_key="overdue_amount",
            field="status",
            source_ref=source_ref,
        ),
        "overdue_amount_coverage_count": _pool_validation_amount_field(
            amounts,
            amount_key="overdue_amount",
            field="coverage_count",
            source_ref=source_ref,
        ),
        "overdue_amount_coverage_rate": _pool_validation_amount_field(
            amounts,
            amount_key="overdue_amount",
            field="coverage_rate",
            source_ref=source_ref,
        ),
        "overdue_amount_sum": _pool_validation_amount_field(
            amounts,
            amount_key="overdue_amount",
            field="sum",
            source_ref=source_ref,
        ),
        "paired_amount_status": _pool_validation_amount_field(
            amounts,
            amount_key="paired",
            field="status",
            source_ref=source_ref,
        ),
        "paired_coverage_count": _pool_validation_amount_field(
            amounts,
            amount_key="paired",
            field="coverage_count",
            source_ref=source_ref,
        ),
        "paired_coverage_rate": _pool_validation_amount_field(
            amounts,
            amount_key="paired",
            field="coverage_rate",
            source_ref=source_ref,
        ),
        "paired_loan_amount_sum": _pool_validation_amount_field(
            amounts,
            amount_key="paired",
            field="loan_amount_sum",
            source_ref=source_ref,
        ),
        "paired_overdue_amount_sum": _pool_validation_amount_field(
            amounts,
            amount_key="paired",
            field="overdue_amount_sum",
            source_ref=source_ref,
        ),
        "paired_overdue_rate": _pool_validation_amount_field(
            amounts,
            amount_key="paired",
            field="overdue_rate",
            source_ref=source_ref,
        ),
    }


def _pool_validation_amount_field(
    amounts: Mapping[str, Any],
    *,
    amount_key: str,
    field: str,
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    item = amounts[amount_key]
    if field == "status":
        return _present_field(item["status"], source_ref)
    if item["status"] != "available" or item[field] is None:
        return _absent_field("unavailable")
    return _present_field(item[field], source_ref)


def _pool_validation_amount_columns() -> list[dict[str, Any]]:
    return [
        _column("loan_amount_status", "Status of loan amount"),
        _column(
            "loan_amount_coverage_count",
            "Amount of loan covered",
            unit="count",
            precision=0,
        ),
        _column(
            "loan_amount_coverage_rate",
            "Coverage of loan amounts",
            unit="%",
            precision=4,
        ),
        _column("loan_amount_sum", "Total loan amount"),
        _column("overdue_amount_status", "Overdue amounts"),
        _column(
            "overdue_amount_coverage_count",
            "Overdue amounts covered",
            unit="count",
            precision=0,
        ),
        _column(
            "overdue_amount_coverage_rate",
            "Overdue amount coverage",
            unit="%",
            precision=4,
        ),
        _column("overdue_amount_sum", "Total overdue amounts"),
        _column("paired_amount_status", "Amount pairing state"),
        _column(
            "paired_coverage_count",
            "Amount paired overlay",
            unit="count",
            precision=0,
        ),
        _column(
            "paired_coverage_rate",
            "Value matching coverage",
            unit="%",
            precision=4,
        ),
        _column("paired_loan_amount_sum", "Total loan matching"),
        _column("paired_overdue_amount_sum", "Total overdue amount for matching"),
        _column(
            "paired_overdue_rate",
            "Matching of overdue amounts",
            unit="%",
            precision=4,
        ),
    ]


def _has_validation_blocker(
    *,
    sections: Iterable[Mapping[str, Any]],
    missing_information: Sequence[Mapping[str, Any]],
) -> bool:
    if any(
        item["blocking"] == "validation" and item["status"] != "provided"
        for item in missing_information
    ):
        return True
    for section in sections:
        for item in section["summary_fields"]:
            if item["field"]["blocking"] == "validation":
                return True
        for table in section["tables"]:
            for row in table["rows"]:
                if any(
                    field["blocking"] == "validation"
                    for field in row["cells"].values()
                ):
                    return True
    return False


def _impact_cube_partition_table(
    cube: Mapping[str, Any],
    source_ref: Mapping[str, str],
    *,
    allow_oot_validated: bool,
) -> dict[str, Any]:
    return build_strategy_report_table(
        table_id="impact_cube_partitions",
        title="ImpactCube Division and evidence phase",
        sheet_key="10_validation",
        granularity="aggregate",
        content_class="lineage",
        columns=[
            _column("population", "Mass calibration"),
            _column("partition", "Sample partition"),
            _column("population_key", "Area Key for the crowd"),
            _column("row_count", "Number of samples", unit="count", precision=0),
            _column("effect_stage", "Effect phase"),
            _column("validation_status", "Authentication status"),
        ],
        rows=[
            {
                "row_id": (
                    f"impact-partition-{row['role']}-{row['name']}"
                ),
                "cells": {
                    "population": _present_field(
                        row["role"],
                        source_ref,
                    ),
                    "partition": _present_field(
                        row["name"],
                        source_ref,
                    ),
                    "population_key": _present_field(
                        row["population_key"],
                        source_ref,
                    ),
                    "row_count": _present_field(
                        row["row_count"],
                        source_ref,
                    ),
                    "effect_stage": _impact_partition_claim_field(
                        row,
                        source_ref,
                        key="effect_stage",
                        allow_oot_validated=allow_oot_validated,
                    ),
                    "validation_status": _impact_partition_claim_field(
                        row,
                        source_ref,
                        key="validation_status",
                        allow_oot_validated=allow_oot_validated,
                    ),
                },
            }
            for row in cube["partitions"]
        ],
        source_refs=[source_ref],
    )


def _impact_partition_claim_field(
    partition: Mapping[str, Any],
    source_ref: Mapping[str, str],
    *,
    key: str,
    allow_oot_validated: bool,
) -> dict[str, Any]:
    if (
        partition["effect_stage"] == "oot_validated"
        and not allow_oot_validated
    ):
        return _absent_field(
            "unavailable",
            note="claim_suppressed_by_validation_blocker",
        )
    return _present_field(partition[key], source_ref)


def _impact_cube_slices_table(
    cube: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    rows = []
    for item in cube["slices"]:
        population = item["population"]
        population_value = (
            population["value"]
            if population["availability"] == "present"
            else None
        )
        risk = (
            None
            if population_value is None
            else population_value["risk"]
        )
        rows.append(
            {
                "row_id": item["slice_id"],
                "cells": {
                    "slice_id": _present_field(
                        item["slice_id"],
                        source_ref,
                    ),
                    "population": _present_field(
                        item["population_role"],
                        source_ref,
                    ),
                    "partition": _dimension_field(
                        item["dimensions"]["partition"],
                        source_ref,
                    ),
                    "family": _present_field(
                        item["family"],
                        source_ref,
                    ),
                    "month": _dimension_field(
                        item["dimensions"]["month"],
                        source_ref,
                    ),
                    "group": _dimension_field(
                        item["dimensions"]["group"],
                        source_ref,
                    ),
                    "segment": _dimension_field(
                        item["dimensions"]["segment"],
                        source_ref,
                    ),
                    "new_action": _dimension_field(
                        item["dimensions"]["new_action_bucket"],
                        source_ref,
                    ),
                    "slice_availability": _present_field(
                        item["availability"],
                        source_ref,
                    ),
                    "population_count": _wrapped_mapping_field(
                        population,
                        source_ref,
                        key="count",
                    ),
                    "population_share": _wrapped_mapping_field(
                        population,
                        source_ref,
                        key="share",
                    ),
                    "labeled_count": _wrapped_mapping_field(
                        population,
                        source_ref,
                        key="labeled_count",
                    ),
                    "label_coverage": _wrapped_mapping_field(
                        population,
                        source_ref,
                        key="label_coverage",
                    ),
                    "bad_count": _risk_field(
                        risk,
                        source_ref,
                        key="bad_count",
                    ),
                    "bad_rate": _risk_field(
                        risk,
                        source_ref,
                        key="bad_rate",
                    ),
                    "amounts": _wrapped_mapping_field(
                        population,
                        source_ref,
                        key="amounts",
                    ),
                    "new_metrics": _strategy_projection_field(
                        item["new"],
                        source_ref,
                        key="metrics",
                    ),
                    "new_breakdown": _strategy_projection_field(
                        item["new"],
                        source_ref,
                        key="breakdown",
                    ),
                    "current_metrics": _strategy_projection_field(
                        item["current"],
                        source_ref,
                        key="metrics",
                    ),
                    "current_breakdown": _strategy_projection_field(
                        item["current"],
                        source_ref,
                        key="breakdown",
                    ),
                },
            }
        )
    return build_strategy_report_table(
        table_id="impact_cube_slices",
        title="ImpactCube Results by Division, Month-to-Drive",
        sheet_key="08_impact",
        granularity="aggregate",
        content_class="segment_summary",
        columns=[
            _column("slice_id", "SliceID"),
            _column("population", "Mass calibration"),
            _column("partition", "Sample partition"),
            _column("family", "Slicing."),
            _column("month", "Month"),
            _column("group", "Group"),
            _column("segment", "The guests."),
            _column("new_action", "New Policy Action"),
            _column("slice_availability", "Slice Status"),
            _column("population_count", "Number of samples", unit="count", precision=0),
            _column("population_share", "Samples as a percentage", unit="%", precision=4),
            _column("labeled_count", "Number of labels", unit="count", precision=0),
            _column("label_coverage", "Label Coverage", unit="%", precision=4),
            _column("bad_count", "Number of bad samples", unit="count", precision=0),
            _column("bad_rate", "Bad debt rate", unit="%", precision=4),
            _column("amounts", "Value observations"),
            _column("new_metrics", "New Strategy Indicators"),
            _column("new_breakdown", "New policy distribution"),
            _column("current_metrics", "Current strategic indicators"),
            _column("current_breakdown", "Current policy distribution"),
        ],
        rows=rows,
        source_refs=[source_ref],
    )


def _impact_cube_waterfall_table(
    cube: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    rows = []
    for item in cube["slices"]:
        if item["family"] != "overall":
            continue
        waterfall = item["waterfall"]
        if waterfall["availability"] != "present":
            continue
        partition = item["dimensions"]["partition"]["value"]
        for entry in waterfall["value"]["entries"]:
            action = entry["action"]
            rows.append(
                {
                    "row_id": (
                        f"{item['slice_id']}-{entry['entry_id']}"
                    ),
                    "cells": {
                        "population": _present_field(
                            item["population_role"],
                            source_ref,
                        ),
                        "partition": _present_field(
                            partition,
                            source_ref,
                        ),
                        "position": _present_field(
                            entry["position"],
                            source_ref,
                        ),
                        "rule_id": _present_field(
                            entry["rule_id"],
                            source_ref,
                        ),
                        "action_type": _present_field(
                            action["type"],
                            source_ref,
                        ),
                        "action_value": _present_field(
                            action["value"],
                            source_ref,
                        ),
                        "standalone_count": _present_field(
                            entry["standalone"]["count"],
                            source_ref,
                        ),
                        "incremental_count": _present_field(
                            entry["incremental"]["count"],
                            source_ref,
                        ),
                        "shadowed_count": _present_field(
                            entry["shadowed"]["count"],
                            source_ref,
                        ),
                        "remaining_count": _present_field(
                            entry["remaining_after"]["count"],
                            source_ref,
                        ),
                        "incremental_bad_rate": _effect_risk_field(
                            entry["incremental"],
                            source_ref,
                            key="bad_rate",
                        ),
                    },
                }
            )
    return build_strategy_report_table(
        table_id="impact_cube_waterfall",
        title="ImpactCube First-match Waterfall",
        sheet_key="07_waterfall_swap",
        granularity="aggregate",
        content_class="rule_summary",
        columns=[
            _column("population", "Mass calibration"),
            _column("partition", "Sample partition"),
            _column("position", "Order of rules"),
            _column("rule_id", "RuleID"),
            _column("action_type", "Action Type"),
            _column("action_value", "Action Value"),
            _column("standalone_count", "Independence hits", unit="count", precision=0),
            _column("incremental_count", "Incremental hit", unit="count", precision=0),
            _column("shadowed_count", "Blocked", unit="count", precision=0),
            _column("remaining_count", "Remaining", unit="count", precision=0),
            _column("incremental_bad_rate", "Incremental bad debt rate", unit="%", precision=4),
        ],
        rows=rows,
        source_refs=[source_ref],
    )


def _impact_cube_transitions_table(
    cube: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    rows = []
    for item in cube["slices"]:
        if (
            item["family"] != "overall"
            or item["transition"]["availability"] != "present"
        ):
            continue
        partition = item["dimensions"]["partition"]["value"]
        for index, transition in enumerate(
            item["transition"]["value"]["rows"]
        ):
            effect = transition["effect"]
            rows.append(
                {
                    "row_id": (
                        f"{item['slice_id']}-transition-{index}"
                    ),
                    "cells": {
                        "population": _present_field(
                            item["population_role"],
                            source_ref,
                        ),
                        "partition": _present_field(
                            partition,
                            source_ref,
                        ),
                        "from_action": _present_field(
                            transition["from_bucket"],
                            source_ref,
                        ),
                        "to_action": _present_field(
                            transition["to_bucket"],
                            source_ref,
                        ),
                        "direction": _present_field(
                            transition["direction"],
                            source_ref,
                        ),
                        "count": _present_field(
                            effect["count"],
                            source_ref,
                        ),
                        "bad_count": _effect_risk_field(
                            effect,
                            source_ref,
                            key="bad_count",
                        ),
                        "bad_rate": _effect_risk_field(
                            effect,
                            source_ref,
                            key="bad_rate",
                        ),
                        "amounts": _present_field(
                            effect["amounts"],
                            source_ref,
                        ),
                    },
                }
            )
    return build_strategy_report_table(
        table_id="impact_cube_transitions",
        title="Current and new strategiesSwap/Migration",
        sheet_key="07_waterfall_swap",
        granularity="aggregate",
        content_class="metric_summary",
        columns=[
            _column("population", "Mass calibration"),
            _column("partition", "Sample partition"),
            _column("from_action", "Current Action"),
            _column("to_action", "New Action"),
            _column("direction", "Migration direction"),
            _column("count", "Number of samples", unit="count", precision=0),
            _column("bad_count", "Number of bad samples", unit="count", precision=0),
            _column("bad_rate", "Bad debt rate", unit="%", precision=4),
            _column("amounts", "Value observations"),
        ],
        rows=rows,
        source_refs=[source_ref],
    )


def _impact_cube_economics_table(
    cube: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    rows = []
    for item in cube["slices"]:
        economics = item["economics"]
        rows.append(
            {
                "row_id": f"{item['slice_id']}-economics",
                "cells": {
                    "population": _present_field(
                        item["population_role"],
                        source_ref,
                    ),
                    "partition": _dimension_field(
                        item["dimensions"]["partition"],
                        source_ref,
                    ),
                    "family": _present_field(
                        item["family"],
                        source_ref,
                    ),
                    "month": _dimension_field(
                        item["dimensions"]["month"],
                        source_ref,
                    ),
                    "group": _dimension_field(
                        item["dimensions"]["group"],
                        source_ref,
                    ),
                    "segment": _dimension_field(
                        item["dimensions"]["segment"],
                        source_ref,
                    ),
                    "new_action": _dimension_field(
                        item["dimensions"]["new_action_bucket"],
                        source_ref,
                    ),
                    "availability": _present_field(
                        economics["availability"],
                        source_ref,
                    ),
                    "current": _wrapped_mapping_field(
                        economics,
                        source_ref,
                        key="current",
                    ),
                    "new": _wrapped_mapping_field(
                        economics,
                        source_ref,
                        key="new",
                    ),
                    "delta": _wrapped_mapping_field(
                        economics,
                        source_ref,
                        key="delta",
                    ),
                },
            }
        )
    return build_strategy_report_table(
        table_id="impact_cube_economics",
        title="ImpactCube Gains and economics",
        sheet_key="09_economics",
        granularity="aggregate",
        content_class="metric_summary",
        columns=[
            _column("population", "Mass calibration"),
            _column("partition", "Sample partition"),
            _column("family", "Slicing."),
            _column("month", "Month"),
            _column("group", "Group"),
            _column("segment", "The guests."),
            _column("new_action", "New Policy Action"),
            _column("availability", "Economic status"),
            _column("current", "Current strategy economics"),
            _column("new", "New strategy economics"),
            _column("delta", "Economic changes"),
        ],
        rows=rows,
        source_refs=[source_ref],
    )


def _impact_cube_final_document_section(
    *,
    pool: Mapping[str, Any],
    compiled_design: Mapping[str, Any],
    cube: Mapping[str, Any],
    pool_ref: Mapping[str, str],
    impact_ref: Mapping[str, str],
    allow_oot_validated: bool,
    strategy_lifecycle: Mapping[str, Any],
) -> dict[str, Any]:
    claimable_partitions = [
        row
        for row in cube["partitions"]
        if (
            row["effect_stage"] != "oot_validated"
            or allow_oot_validated
        )
    ]
    stages = list(
        dict.fromkeys(
            row["effect_stage"] for row in claimable_partitions
        )
    )
    validation_statuses = list(
        dict.fromkeys(
            row["validation_status"] for row in claimable_partitions
        )
    )
    lifecycle_ref = strategy_lifecycle["source_ref"]
    return build_strategy_report_section(
        key="final_document",
        title=_SECTION_TITLES["final_document"],
        availability="present",
        summary_fields=[
            _named(
                "strategy_type",
                "Policy Type",
                _present_field(pool["strategy_type"], pool_ref),
            ),
            _named(
                "design_hash",
                "Candidate strategy design Hash",
                _present_field(compiled_design["design_hash"], pool_ref),
            ),
            _named(
                "evidence_stages",
                "Current evidence phase",
                _present_field(stages, impact_ref),
            ),
            _named(
                "validation_statuses",
                "Authentication status",
                _present_field(validation_statuses, impact_ref),
            ),
            _named(
                "strategy_status",
                "Policy Status",
                _present_field(
                    strategy_lifecycle["strategy_status"],
                    lifecycle_ref,
                ),
            ),
            _named(
                "adoption_status",
                "Adopt Status",
                _present_field(
                    strategy_lifecycle["adoption_status"],
                    lifecycle_ref,
                ),
            ),
            _named(
                "deployment_status",
                "Local asset status",
                _present_field(
                    strategy_lifecycle["deployment_status"],
                    lifecycle_ref,
                ),
            ),
            _named(
                "creates_strategy",
                "Create Local Policy Assets",
                _present_field(
                    strategy_lifecycle["creates_strategy"],
                    lifecycle_ref,
                ),
            ),
        ],
        source_refs=_dedupe_refs([pool_ref, impact_ref, lifecycle_ref]),
    )


def _impact_section(
    *,
    impact: Mapping[str, Any],
    pool_ref: Mapping[str, str],
    impact_ref: Mapping[str, str],
) -> dict[str, Any]:
    dataset_ref = _dataset_ref_from_impact(impact)
    population = impact["population"]
    lifecycle = impact["lifecycle"]
    summary_fields = [
        _named(
            "candidate_stage",
            "Candidate stage",
            _present_field(lifecycle["candidate_stage"], impact_ref),
        ),
        _named(
            "observation_stage",
            "Effect phase",
            _present_field(lifecycle["observation_stage"], impact_ref),
        ),
        _named(
            "validation_status",
            "Authentication status",
            _present_field(lifecycle["validation_status"], impact_ref),
        ),
        _named(
            "impact_population_count",
            "Measurement of samples",
            _present_field(population["population_count"], impact_ref),
        ),
        _named(
            "impact_label_coverage",
            "Label Coverage",
            _present_field(population["label_coverage"], impact_ref),
        ),
        _named(
            "monthly_status",
            "Monthly state of measurement",
            (
                _present_field("available", impact_ref)
                if impact["monthly"]["status"] == "available"
                else _absent_field(
                    "unavailable",
                    note=impact["monthly"]["reason"],
                )
            ),
        ),
    ]
    tables = [
        _waterfall_table(impact, impact_ref),
        _action_impact_table(impact, impact_ref),
        _lifecycle_table(impact, impact_ref),
    ]
    monthly = _monthly_impact_table(impact, impact_ref)
    if monthly is not None:
        tables.append(monthly)
    economics, economics_fields = _economics_table(impact, impact_ref)
    summary_fields.extend(economics_fields)
    if economics is not None:
        tables.append(economics)
    baseline = _baseline_table(impact, impact_ref)
    if baseline is not None:
        tables.append(baseline)
    return build_strategy_report_section(
        key="impact_assessment",
        title=_SECTION_TITLES["impact_assessment"],
        availability="present",
        summary_fields=summary_fields,
        tables=tables,
        stage_evidence=[
            {
                "effect_stage": "backtested",
                "population": "risk",
                "partition": "development",
                "binding": {
                    "kind": "development_backtest",
                    "dataset_ref": dataset_ref,
                    "frozen_artifact_ref": pool_ref,
                    "result_ref": impact_ref,
                },
            }
        ],
        red_flags=[
            {
                "code": item["code"],
                "level": item["level"],
                "message": item["message"],
                "source_refs": [impact_ref],
            }
            for item in impact["red_flags"]
        ],
        source_refs=[pool_ref, impact_ref],
    )


def _final_document_section(
    *,
    pool: Mapping[str, Any],
    compiled_design: Mapping[str, Any],
    impact: Mapping[str, Any],
    pool_ref: Mapping[str, str],
    impact_ref: Mapping[str, str],
    strategy_lifecycle: Mapping[str, Any],
) -> dict[str, Any]:
    lifecycle_ref = strategy_lifecycle["source_ref"]
    return build_strategy_report_section(
        key="final_document",
        title=_SECTION_TITLES["final_document"],
        availability="present",
        summary_fields=[
            _named(
                "strategy_type",
                "Policy Type",
                _present_field(pool["strategy_type"], pool_ref),
            ),
            _named(
                "design_hash",
                "Candidate strategy design Hash",
                _present_field(compiled_design["design_hash"], pool_ref),
            ),
            _named(
                "evidence_stage",
                "Current evidence phase",
                _present_field(
                    "development_backtested_unvalidated",
                    impact_ref,
                ),
            ),
            _named(
                "strategy_status",
                "Policy Status",
                _present_field(
                    strategy_lifecycle["strategy_status"],
                    lifecycle_ref,
                ),
            ),
            _named(
                "adoption_status",
                "Adopt Status",
                _present_field(
                    strategy_lifecycle["adoption_status"],
                    lifecycle_ref,
                ),
            ),
            _named(
                "deployment_status",
                "Local asset status",
                _present_field(
                    strategy_lifecycle["deployment_status"],
                    lifecycle_ref,
                ),
            ),
            _named(
                "creates_strategy",
                "Create Local Policy Assets",
                _present_field(
                    strategy_lifecycle["creates_strategy"],
                    lifecycle_ref,
                ),
            ),
        ],
        source_refs=_dedupe_refs([pool_ref, impact_ref, lifecycle_ref]),
    )


def _model_bundle_observation_rows(
    bundle: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for evidence in bundle["univariate_evidence"]:
        for observation in evidence["observations"]:
            rows.append(
                _observation_row(
                    observation,
                    source_ref,
                    row_id=f"univariate-{observation['observation_id']}",
                    subject=evidence["feature"],
                    status_map=_MODEL_STATUS_TO_AVAILABILITY,
                )
            )
    for evidence in bundle["model_evidence"]:
        rows.extend(
            _single_model_observation_rows(
                evidence,
                source_ref,
                prefix=evidence["evidence_id"],
            )
        )
    return rows


def _model_comparison_tables(
    bundle: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> list[dict[str, Any]]:
    comparisons = bundle["comparison_evidence"]
    if not comparisons:
        return []
    metric_rows: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    for comparison in comparisons:
        sample_ref = comparison["evaluation_sample_ref"]
        selection = comparison["selection"]
        selected_ref = selection["selected_model_evidence_ref"]
        for metric in comparison["metrics"]:
            values_by_model = {
                (
                    item["model_evidence_ref"]["evidence_id"],
                    item["model_evidence_ref"]["content_hash"],
                ): item["value"]
                for item in (metric["model_values"] or [])
            }
            for model_ref in comparison["model_evidence_refs"]:
                model_value = values_by_model.get(
                    (
                        model_ref["evidence_id"],
                        model_ref["content_hash"],
                    )
                )
                metric_rows.append(
                    {
                        "row_id": (
                            f"{comparison['comparison_id']}-"
                            f"{metric['comparison_metric_id']}-"
                            f"{model_ref['evidence_id']}"
                        ),
                        "cells": {
                            "comparison_id": _present_field(
                                comparison["comparison_id"],
                                source_ref,
                            ),
                            "population": _present_field(
                                sample_ref["population"],
                                source_ref,
                            ),
                            "partition": _present_field(
                                sample_ref["partition"],
                                source_ref,
                            ),
                            "metric": _present_field(
                                metric["metric_key"],
                                source_ref,
                            ),
                            "period": (
                                _present_field(metric["period"], source_ref)
                                if metric["period"] is not None
                                else _absent_field("not_applicable")
                            ),
                            "model_evidence_id": _present_field(
                                model_ref["evidence_id"],
                                source_ref,
                            ),
                            "value": _status_field(
                                metric["status"],
                                model_value,
                                source_ref,
                                status_map=_MODEL_STATUS_TO_AVAILABILITY,
                                note=metric["reason"],
                            ),
                            "delta": _status_field(
                                metric["status"],
                                metric["delta"],
                                source_ref,
                                status_map=_MODEL_STATUS_TO_AVAILABILITY,
                                note=metric["reason"],
                            ),
                            "selected": _present_field(
                                selection["status"] == "selected"
                                and model_ref == selected_ref,
                                source_ref,
                            ),
                        },
                    }
                )
        selection_rows.append(
            {
                "row_id": f"{comparison['comparison_id']}-selection",
                "cells": {
                    "comparison_id": _present_field(
                        comparison["comparison_id"],
                        source_ref,
                    ),
                    "status": _present_field(selection["status"], source_ref),
                    "selected_model_evidence_id": (
                        _present_field(
                            selected_ref["evidence_id"],
                            source_ref,
                        )
                        if selected_ref is not None
                        else _absent_field("not_applicable")
                    ),
                    "metric": (
                        _present_field(selection["metric_key"], source_ref)
                        if selection["metric_key"] is not None
                        else _absent_field("not_applicable")
                    ),
                    "period": (
                        _present_field(selection["period"], source_ref)
                        if selection["period"] is not None
                        else _absent_field("not_applicable")
                    ),
                    "direction": (
                        _present_field(selection["direction"], source_ref)
                        if selection["direction"] is not None
                        else _absent_field("not_applicable")
                    ),
                    "reason": (
                        _present_field(selection["reason"], source_ref)
                        if selection["reason"] is not None
                        else _absent_field("not_applicable")
                    ),
                },
            }
        )
    return [
        build_strategy_report_table(
            table_id="model_comparison_metrics",
            title="Model comparison indicators",
            sheet_key="04_univariate_model",
            granularity="aggregate",
            content_class="metric_summary",
            columns=[
                _column("comparison_id", "ComparisonID"),
                _column("population", "Sample caliber"),
                _column("partition", "Sample partition"),
                _column("metric", "Indicators"),
                _column("period", "Month"),
                _column("model_evidence_id", "Model evidenceID"),
                _column("value", "Indicator value"),
                _column("delta", "Comparative variance"),
                _column("selected", "Select"),
            ],
            rows=metric_rows,
            source_refs=[source_ref],
        ),
        build_strategy_report_table(
            table_id="model_selection_results",
            title="Model selection results",
            sheet_key="04_univariate_model",
            granularity="aggregate",
            content_class="lineage",
            columns=[
                _column("comparison_id", "ComparisonID"),
                _column("status", "Select Status"),
                _column("selected_model_evidence_id", "Select Model EvidenceID"),
                _column("metric", "Select Indicators"),
                _column("period", "Month"),
                _column("direction", "Optimizing direction"),
                _column("reason", "No reason selected"),
            ],
            rows=selection_rows,
            source_refs=[source_ref],
        ),
    ]


def _training_model_ref(evidence: Mapping[str, Any]) -> dict[str, str]:
    model_binary = evidence["model_artifact"]["model_binary_ref"]
    return {
        "kind": model_binary["kind"],
        "ref_id": model_binary["artifact_id"],
        "content_hash": model_binary["content_hash"],
    }


def _model_selection_field(
    *,
    model: Mapping[str, Any] | None,
    model_ref: Mapping[str, Any],
    identity_ref: Mapping[str, str],
    selection_ref: Mapping[str, str] | None,
) -> dict[str, Any]:
    if model is None or selection_ref is None:
        return _absent_field(
            "unavailable",
            note="No evidence of selection of models that could be accurately linked to the model was provided.",
        )
    matching_models = [
        evidence
        for evidence in model["model_evidence"]
        if evidence["model_ref"] == model_ref
    ]
    if len(matching_models) != 1:
        return _absent_field(
            "unavailable",
            note="The model is not the only precise reference that the model can be used to compare evidence.",
        )
    evidence_ref = {
        "evidence_id": matching_models[0]["evidence_id"],
        "content_hash": matching_models[0]["content_hash"],
    }
    statuses: set[str] = set()
    for comparison in model["comparison_evidence"]:
        if evidence_ref not in comparison["model_evidence_refs"]:
            continue
        selection = comparison["selection"]
        if selection["status"] == "no_selection":
            statuses.add("no_selection")
        elif selection["selected_model_evidence_ref"] == evidence_ref:
            statuses.add("selected")
        else:
            statuses.add("not_selected")
    if len(statuses) != 1:
        return _absent_field(
            "unavailable",
            note="The model does not have the only consistent model selection conclusion.",
        )
    return _present_field_many(
        statuses.pop(),
        [identity_ref, selection_ref],
    )


def _single_model_observation_rows(
    evidence: Mapping[str, Any],
    source_ref: Mapping[str, str],
    *,
    prefix: str,
) -> list[dict[str, Any]]:
    return [
        _observation_row(
            observation,
            source_ref,
            row_id=f"{prefix}-{observation['observation_id']}",
            subject=evidence["evidence_id"],
            status_map=_MODEL_STATUS_TO_AVAILABILITY,
        )
        for observation in evidence["observations"]
    ]


def _observation_row(
    observation: Mapping[str, Any],
    source_ref: Mapping[str, str],
    *,
    row_id: str,
    subject: str,
    status_map: Mapping[str, str],
) -> dict[str, Any]:
    sample_ref = observation["sample_ref"]
    return {
        "row_id": row_id,
        "cells": {
            "subject": _present_field(subject, source_ref),
            "population": _present_field(sample_ref["population"], source_ref),
            "partition": _present_field(sample_ref["partition"], source_ref),
            "metric": _present_field(observation["metric_key"], source_ref),
            "bin": (
                _present_field(observation["bin_id"], source_ref)
                if observation["bin_id"] is not None
                else _absent_field("not_applicable")
            ),
            "period": (
                _present_field(observation["period"], source_ref)
                if observation["period"] is not None
                else _absent_field("not_applicable")
            ),
            "value": _status_field(
                observation["status"],
                observation["value"],
                source_ref,
                status_map=status_map,
                note=observation["reason"],
            ),
            "unit": _present_field(observation["unit"], source_ref),
        },
    }


def _observation_table(
    *,
    table_id: str,
    title: str,
    rows: Sequence[Mapping[str, Any]],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    return build_strategy_report_table(
        table_id=table_id,
        title=title,
        sheet_key="04_univariate_model",
        granularity="aggregate",
        content_class="metric_summary",
        columns=[
            _column("subject", "Analyze Object"),
            _column("population", "Sample caliber"),
            _column("partition", "Sample partition"),
            _column("metric", "Indicators"),
            _column("bin", "Box"),
            _column("period", "Month"),
            _column("value", "Indicator value"),
            _column("unit", "Units"),
        ],
        rows=rows,
        source_refs=[source_ref],
    )


def _waterfall_table(
    impact: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    rows = [
        {
            "row_id": row["entry_id"],
            "cells": {
                "position": _present_field(row["position"], source_ref),
                "rule_id": _present_field(row["rule_id"], source_ref),
                "action": _present_field(row["action"]["type"], source_ref),
                "standalone_count": _present_field(
                    row["standalone"]["population_count"],
                    source_ref,
                ),
                "incremental_count": _present_field(
                    row["incremental"]["population_count"],
                    source_ref,
                ),
                "shadowed_count": _present_field(
                    row["shadowed"]["population_count"],
                    source_ref,
                ),
                "remaining_count": _present_field(
                    row["remaining_after"]["population_count"],
                    source_ref,
                ),
                "incremental_bad_rate": _nullable_metric_field(
                    row["incremental"]["bad_rate"],
                    source_ref,
                ),
            },
        }
        for row in impact["waterfall"]
    ]
    return build_strategy_report_table(
        table_id="strategy_waterfall",
        title="Rules Falls overlap with cover",
        sheet_key="07_waterfall_swap",
        granularity="aggregate",
        content_class="rule_summary",
        effect_stage="backtested",
        columns=[
            _column("position", "Order"),
            _column("rule_id", "RuleID"),
            _column("action", "Actions"),
            _column("standalone_count", "Independence hits", unit="count", precision=0),
            _column("incremental_count", "Incremental hit", unit="count", precision=0),
            _column("shadowed_count", "Blocked", unit="count", precision=0),
            _column("remaining_count", "Remaining", unit="count", precision=0),
            _column("incremental_bad_rate", "Incremental bad debt rate", unit="%", precision=4),
        ],
        rows=rows,
        source_refs=[source_ref],
    )


def _action_impact_table(
    impact: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    rows = [
        {
            "row_id": f"overall-action-{row['action']}",
            "cells": {
                "action": _present_field(row["action"], source_ref),
                "count": _present_field(row["count"], source_ref),
                "rate": _present_field(row["rate"], source_ref),
                "labelled_count": _present_field(
                    row["labelled_count"],
                    source_ref,
                ),
                "bad_count": _present_field(row["bad_count"], source_ref),
                "bad_rate": _nullable_metric_field(
                    row["bad_rate"],
                    source_ref,
                ),
            },
        }
        for row in impact["overall"]["actions"]["breakdown"]
    ]
    return build_strategy_report_table(
        table_id="overall_action_impact",
        title="Overall action impact",
        sheet_key="08_impact",
        granularity="aggregate",
        content_class="metric_summary",
        effect_stage="backtested",
        columns=[
            _column("action", "Actions"),
            _column("count", "Number of samples", unit="count", precision=0),
            _column("rate", "Samples as a percentage", unit="%", precision=4),
            _column("labelled_count", "Number of labels", unit="count", precision=0),
            _column("bad_count", "Number of bad samples", unit="count", precision=0),
            _column("bad_rate", "Bad debt rate", unit="%", precision=4),
        ],
        rows=rows,
        source_refs=[source_ref],
    )


def _monthly_impact_table(
    impact: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any] | None:
    monthly = impact["monthly"]
    if monthly["status"] != "available":
        return None
    rows = []
    for item in monthly["periods"]:
        metrics = item["actions"]["metrics"]
        rows.append(
            {
                "row_id": f"monthly-impact-{item['period']}",
                "cells": {
                    "period": _present_field(item["period"], source_ref),
                    "population_count": _present_field(
                        item["effect"]["population_count"],
                        source_ref,
                    ),
                    "approve_rate": _present_field(
                        metrics["approve_rate"],
                        source_ref,
                    ),
                    "reject_rate": _present_field(
                        metrics["reject_rate"],
                        source_ref,
                    ),
                    "review_rate": _present_field(
                        metrics["review_rate"],
                        source_ref,
                    ),
                    "overall_bad_rate": _nullable_metric_field(
                        metrics["overall_bad_rate"],
                        source_ref,
                    ),
                    "bad_capture_rate": _nullable_metric_field(
                        metrics["bad_capture_rate"],
                        source_ref,
                    ),
                    "good_reject_rate": _nullable_metric_field(
                        metrics["good_reject_rate"],
                        source_ref,
                    ),
                },
            }
        )
    return build_strategy_report_table(
        table_id="monthly_strategy_impact",
        title="Monthly policy implications",
        sheet_key="08_impact",
        granularity="aggregate",
        content_class="monthly_summary",
        effect_stage="backtested",
        columns=[
            _column("period", "Month"),
            _column("population_count", "Number of samples", unit="count", precision=0),
            _column("approve_rate", "Pass rate", unit="%", precision=4),
            _column("reject_rate", "Rate of rejection", unit="%", precision=4),
            _column("review_rate", "Review rate", unit="%", precision=4),
            _column("overall_bad_rate", "Corporate bad debt rate", unit="%", precision=4),
            _column("bad_capture_rate", "Bad sample capture rate", unit="%", precision=4),
            _column("good_reject_rate", "Good sample failure rate.", unit="%", precision=4),
        ],
        rows=rows,
        source_refs=[source_ref],
    )


def _economics_table(
    impact: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    paired = impact["overall"]["effect"]["amounts"]["paired"]
    fields = [
        _named(
            "loan_amount_sum",
            "Total loan amount",
            (
                _present_field(paired["loan_amount_sum"], source_ref)
                if paired["status"] == "available"
                else _absent_field("unavailable")
            ),
        ),
        _named(
            "overdue_amount_sum",
            "Total overdue amounts",
            (
                _present_field(paired["overdue_amount_sum"], source_ref)
                if paired["status"] == "available"
                else _absent_field("unavailable")
            ),
        ),
        _named(
            "overdue_rate",
            "Overdue amounts rate",
            (
                _nullable_metric_field(paired["overdue_rate"], source_ref)
                if paired["status"] == "available"
                else _absent_field("unavailable")
            ),
        ),
    ]
    if paired["status"] != "available":
        return None, fields
    table = build_strategy_report_table(
        table_id="overall_economics_impact",
        title="Overall financial impact",
        sheet_key="09_economics",
        granularity="aggregate",
        content_class="metric_summary",
        effect_stage="backtested",
        columns=[
            _column("coverage_count", "Number of samples covered by the amount", unit="count", precision=0),
            _column("coverage_rate", "Amount coverage", unit="%", precision=4),
            _column("loan_amount_sum", "Total loan amount"),
            _column("overdue_amount_sum", "Total overdue amounts"),
            _column("overdue_rate", "Overdue amounts rate", unit="%", precision=4),
        ],
        rows=[
            {
                "row_id": "overall-economics",
                "cells": {
                    "coverage_count": _present_field(
                        paired["coverage_count"],
                        source_ref,
                    ),
                    "coverage_rate": _present_field(
                        paired["coverage_rate"],
                        source_ref,
                    ),
                    "loan_amount_sum": _present_field(
                        paired["loan_amount_sum"],
                        source_ref,
                    ),
                    "overdue_amount_sum": _present_field(
                        paired["overdue_amount_sum"],
                        source_ref,
                    ),
                    "overdue_rate": _nullable_metric_field(
                        paired["overdue_rate"],
                        source_ref,
                    ),
                },
            }
        ],
        source_refs=[source_ref],
    )
    return table, fields


def _baseline_table(
    impact: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any] | None:
    baseline = impact["baseline"]
    if baseline["status"] != "available":
        return None
    rows = [
        {
            "row_id": f"baseline-delta-{key}",
            "cells": {
                "metric": _present_field(key, source_ref),
                "delta": _present_field(value, source_ref),
            },
        }
        for key, value in sorted(
            baseline["overall"]["metric_deltas"].items()
        )
    ]
    return build_strategy_report_table(
        table_id="baseline_metric_deltas",
        title="Change in relative baseline strategy",
        sheet_key="08_impact",
        granularity="aggregate",
        content_class="metric_summary",
        effect_stage="backtested",
        columns=[
            _column("metric", "Indicators"),
            _column("delta", "Change value"),
        ],
        rows=rows,
        source_refs=[source_ref],
    )


def _lifecycle_table(
    impact: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    lifecycle = impact["lifecycle"]
    return build_strategy_report_table(
        table_id="strategy_validation_status",
        title="Policy validation and life cycle status",
        sheet_key="10_validation",
        granularity="aggregate",
        content_class="lineage",
        effect_stage="backtested",
        columns=[
            _column("candidate_stage", "Candidate stage"),
            _column("observation_stage", "Effect phase"),
            _column("validation_status", "Authentication status"),
            _column("creates_strategy", "Create production strategies"),
            _column("adopted", "Accepted"),
            _column("deployed", "Deployed"),
        ],
        rows=[
            {
                "row_id": "development-backtest-lifecycle",
                "cells": {
                    key: _present_field(lifecycle[key], source_ref)
                    for key in (
                        "candidate_stage",
                        "observation_stage",
                        "validation_status",
                        "creates_strategy",
                        "adopted",
                        "deployed",
                    )
                },
            }
        ],
        source_refs=[source_ref],
    )


def _maturity_field(
    maturity: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    status = maturity["status"]
    if status == "confirmed_matured":
        return _present_field(status, source_ref)
    if status == "not_matured":
        return _absent_field(
            "not_matured",
            note=maturity["reason"],
            blocking="validation",
        )
    if status == "not_applicable":
        return _absent_field("not_applicable", note=maturity["reason"])
    return _absent_field(
        "unavailable",
        note=maturity["reason"],
        blocking="validation",
    )


def _status_field(
    status: str,
    value: Any,
    source_ref: Mapping[str, str],
    *,
    status_map: Mapping[str, str],
    note: str | None = None,
) -> dict[str, Any]:
    availability = status_map.get(status)
    if availability is None:
        raise StrategyReportBundleError(
            f"unsupported evidence availability status: {status}"
        )
    if availability == "present":
        return _present_field(value, source_ref)
    return _absent_field(availability, note=note or status)


def _nullable_metric_field(
    value: Any,
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    if value is None:
        return _absent_field("unavailable")
    return _present_field(value, source_ref)


def _dimension_field(
    dimension: Mapping[str, Any],
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    kind = dimension["kind"]
    if kind == "value":
        return _present_field(dimension["value"], source_ref)
    if kind == "null":
        return _present_field("(null)", source_ref)
    if kind == "redacted":
        return _absent_field(
            "unavailable",
            note="redacted_by_dimension_privacy_policy",
        )
    return _absent_field("not_applicable", note="all_values")


def _wrapped_mapping_field(
    wrapper: Mapping[str, Any],
    source_ref: Mapping[str, str],
    *,
    key: str,
) -> dict[str, Any]:
    availability = wrapper["availability"]
    if availability != "present":
        return _absent_field(
            availability,
            note=wrapper["reason"],
        )
    value = wrapper["value"]
    if not isinstance(value, Mapping) or key not in value:
        raise StrategyReportBundleError(
            f"ImpactCube present projection is missing {key}"
        )
    observed = value[key]
    if observed is None:
        return _absent_field(
            "unavailable",
            note=f"{key}_is_undefined",
        )
    return _present_field(observed, source_ref)


def _strategy_projection_field(
    wrapper: Mapping[str, Any],
    source_ref: Mapping[str, str],
    *,
    key: str,
) -> dict[str, Any]:
    return _wrapped_mapping_field(
        wrapper,
        source_ref,
        key=key,
    )


def _risk_field(
    risk: Mapping[str, Any] | None,
    source_ref: Mapping[str, str],
    *,
    key: str,
) -> dict[str, Any]:
    if risk is None:
        return _absent_field(
            "unavailable",
            note="population_slice_unavailable",
        )
    availability = risk["availability"]
    if availability != "present":
        return _absent_field(
            availability,
            note=risk["reason"],
        )
    value = risk[key]
    if value is None:
        return _absent_field(
            "unavailable",
            note=f"{key}_is_undefined",
        )
    return _present_field(value, source_ref)


def _effect_risk_field(
    effect: Mapping[str, Any],
    source_ref: Mapping[str, str],
    *,
    key: str,
) -> dict[str, Any]:
    risk = effect["risk"]
    availability = risk["availability"]
    if availability != "present":
        return _absent_field(
            availability,
            note=risk["reason"],
        )
    value = risk[key]
    if value is None:
        return _absent_field(
            "unavailable",
            note=f"{key}_is_undefined",
        )
    return _present_field(value, source_ref)


def _present_field(
    value: Any,
    source_ref: Mapping[str, str],
) -> dict[str, Any]:
    return build_report_field(
        value=value,
        availability="present",
        origin="tool_output",
        source_refs=[source_ref],
    )


def _projected_context_field(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    field = validate_report_field(value)
    if field["availability"] == "present" and field["blocking"] != "none":
        return {**field, "blocking": "none"}
    return field


def _present_field_many(
    value: Any,
    source_refs: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    return build_report_field(
        value=value,
        availability="present",
        origin="tool_output",
        source_refs=source_refs,
    )


def _optional_metric_field(
    value: Any,
    source_ref: Mapping[str, str],
    *,
    note: str,
) -> dict[str, Any]:
    if value is None:
        return _absent_field("not_applicable", note=note)
    return _present_field(value, source_ref)


def _absent_field(
    availability: str,
    *,
    note: str | None = None,
    blocking: str = "none",
) -> dict[str, Any]:
    return build_report_field(
        value=None,
        availability=availability,
        origin="repository",
        source_refs=[],
        blocking=blocking,
        note=note,
    )


def _named(
    field_id: str,
    label: str,
    field: Mapping[str, Any],
) -> dict[str, Any]:
    return build_named_report_field(
        field_id=field_id,
        label=label,
        field=validate_report_field(field),
    )


def _column(
    key: str,
    label: str,
    *,
    unit: str | None = None,
    precision: int | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "unit": unit,
        "precision": precision,
    }


def _absent_section(key: str, availability: str) -> dict[str, Any]:
    return build_strategy_report_section(
        key=key,
        title=_SECTION_TITLES[key],
        availability=availability,
    )


def _dataset_ref_from_sample(
    bundle: Mapping[str, Any],
) -> dict[str, str]:
    dataset = bundle["sample_design"]["identity"]["dataset_ref"]
    return _artifact_ref(
        "dataset",
        dataset["dataset_id"],
        dataset["content_hash"],
    )


def _dataset_ref_from_candidate_stability(
    stability: Mapping[str, Any],
) -> dict[str, str]:
    identity = stability["identity"]
    return _artifact_ref(
        "dataset",
        identity["dataset_id"],
        identity["dataset_content_hash"],
    )


def _dataset_ref_from_pool_stability(
    stability: Mapping[str, Any],
) -> dict[str, str]:
    dataset = stability["source_bindings"]["dataset"]
    return _artifact_ref(
        "dataset",
        dataset["dataset_id"],
        dataset["dataset_content_hash"],
    )


def _dataset_ref_from_impact(
    impact: Mapping[str, Any],
) -> dict[str, str]:
    sample = impact["bindings"]["sample"]
    return _artifact_ref(
        "dataset",
        sample["dataset_id"],
        sample["dataset_content_hash"],
    )


def _dataset_ref_from_impact_cube(
    cube: Mapping[str, Any],
) -> dict[str, str]:
    dataset = cube["source_bindings"]["dataset"]
    return _artifact_ref(
        "dataset",
        dataset["dataset_id"],
        dataset["dataset_content_hash"],
    )


def _dataset_ref_from_pool_validation(
    evidence: Mapping[str, Any],
) -> dict[str, str]:
    dataset = evidence["source_bindings"]["dataset"]
    return _artifact_ref(
        "dataset",
        dataset["dataset_id"],
        dataset["dataset_content_hash"],
    )


def _artifact_ref(
    kind: str,
    ref_id: str,
    content_hash: str,
) -> dict[str, str]:
    try:
        return build_source_ref(
            kind=kind,
            ref_id=ref_id,
            content_hash=content_hash,
        )
    except (TypeError, ValueError) as exc:
        raise StrategyReportBundleError(
            f"authenticated {kind} source identity is invalid"
        ) from exc


def _dedupe_refs(
    refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    normalized = [
        _artifact_ref(
            str(item["kind"]),
            str(item["ref_id"]),
            str(item["content_hash"]),
        )
        for item in refs
    ]
    by_identity = {
        (item["kind"], item["ref_id"], item["content_hash"]): item
        for item in normalized
    }
    return [
        by_identity[key]
        for key in sorted(by_identity)
    ]


def _sample_identity(
    binding: _StrategySampleDesignV2Binding,
) -> dict[str, str]:
    _require_binding_type(
        binding,
        (
            StrategySampleDesignV2ArtifactBinding,
            StrategySampleDesignV2NativeArtifactBinding,
        ),
        "sample-design V2",
    )
    design = binding.bundle["sample_design"]
    return {
        "membership_artifact_id": binding.membership_artifact_id,
        "membership_artifact_content_hash": (
            binding.membership_artifact_content_hash
        ),
        "bundle_artifact_id": binding.bundle_artifact_id,
        "bundle_artifact_content_hash": binding.bundle_artifact_content_hash,
        "bundle_id": binding.bundle["bundle_id"],
        "sample_design_id": design["sample_design_id"],
        "sample_design_content_hash": design["content_hash"],
    }


def _training_identity(
    binding: ModelingTrainingEvidenceArtifactBinding,
) -> tuple[str, str, str]:
    _require_binding_type(
        binding,
        ModelingTrainingEvidenceArtifactBinding,
        "training-evidence",
    )
    return (
        _record_text(binding.evidence_record, "id"),
        _record_text(binding.evidence_record, "content_hash"),
        str(binding.evidence["content_hash"]),
    )


def _record_text(record: Mapping[str, Any], field: str) -> str:
    if not isinstance(record, Mapping):
        raise StrategyReportBundleError(
            "authenticated TaskArtifact record is invalid"
        )
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise StrategyReportBundleError(
            f"authenticated TaskArtifact {field} is invalid"
        )
    return value


def _require_binding_type(
    value: object,
    expected: type | tuple[type, ...],
    name: str,
) -> None:
    if not isinstance(value, expected):
        expected_name = (
            expected.__name__
            if isinstance(expected, type)
            else " or ".join(item.__name__ for item in expected)
        )
        raise StrategyReportBundleError(
            f"{name} must be an authenticated {expected_name} binding"
        )


def _require_canonical_artifact_hash(
    supplied: object,
    canonical: str,
    name: str,
) -> None:
    if not isinstance(supplied, str):
        raise StrategyReportBundleError(
            f"{name} artifact content hash is invalid"
        )
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if supplied != expected:
        raise StrategyReportBundleError(
            f"{name} artifact content hash does not match canonical evidence"
        )


__all__ = [
    "StrategyImpactCubeArtifactBinding",
    "build_strategy_report_bundle_source_inputs",
    "validate_candidate_stability_report_compatibility",
    "validate_cross_candidate_search_report_compatibility",
    "validate_strategy_impact_cube_artifact_binding",
]
