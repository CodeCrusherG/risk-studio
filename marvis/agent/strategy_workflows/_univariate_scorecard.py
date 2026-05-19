from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import math
import re
from typing import Any

from .contracts import (
    PreparedStrategyPlan,
    StrategyWorkflowPreparationContext,
    StrategyWorkflowRequirements,
    StrategyWorkflowResolutionContext,
    StrategyWorkflowValidationError,
    deep_freeze,
    deep_thaw,
)


UNIVARIATE_ANALYSIS_WORKFLOW_ID = "univariate_candidate_analysis"
UNIVARIATE_REFINEMENT_WORKFLOW_ID = "univariate_candidate_refinement"
CANDIDATE_STABILITY_WORKFLOW_ID = "candidate_monthly_stability"
SCORECARD_EVIDENCE_WORKFLOW_ID = "scorecard_model_score_evidence_build"
SCORECARD_BAND_WORKFLOW_ID = "scorecard_band_build"
SCORECARD_CUTOFF_WORKFLOW_ID = "scorecard_cutoff_selection"

UNIVARIATE_BINNING_METHODS = (
    "equal_frequency",
    "equal_width",
    "chimerge",
    "tree",
    "manual",
)
UNIVARIATE_REFINEMENT_METHODS = (*UNIVARIATE_BINNING_METHODS, "categorical")
STRATEGY_TYPES = (
    "approval",
    "reject",
    "limit",
    "pricing",
    "segmentation",
)

_CANDIDATE_ID_RE = re.compile(r"^candidate-[0-9a-f]{32}$")
_CANDIDATE_ASSET_ID_RE = re.compile(r"^candidate-asset-[0-9a-f]{32}$")
_POOL_ENTRY_ID_RE = re.compile(r"^pool-entry-[0-9a-f]{32}$")
_SCORECARD_BAND_ASSET_ID_RE = re.compile(
    r"^scorecard-band-asset-[0-9a-f]{32}$"
)
_SCORECARD_CUTOFF_ID_RE = re.compile(r"^scorecard-cutoff-[0-9a-f]{32}$")

_DATA_REQUIREMENTS = StrategyWorkflowRequirements(
    dataset=True,
    target=True,
    complete_labels=True,
)
_NO_REQUIREMENTS = StrategyWorkflowRequirements(
    dataset=False,
    target=False,
    complete_labels=False,
)


def univariate_refinement_requirements(
    inputs: Mapping[str, Any],
) -> StrategyWorkflowRequirements:
    """Preserve the legacy fresh-vs-existing source dependency boundary."""

    required = {"feature", "method", "selection"}
    if not isinstance(inputs, Mapping) or not required <= set(inputs):
        raise RuntimeError(
            "univariate_candidate_refinement requirements need normalized inputs"
        )
    return _NO_REQUIREMENTS if "source_candidate_id" in inputs else _DATA_REQUIREMENTS


def validate_univariate_analysis_inputs(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowResolutionContext,
    *,
    manual_features: Sequence[str] | None = None,
) -> dict[str, Any]:
    allowed = {
        "features",
        "methods",
        "bin_count",
        "min_bin_pct",
        "loan_amount_col",
        "overdue_amount_col",
        "sentinel_values",
        "manual_breakpoints",
    }
    workflow = UNIVARIATE_ANALYSIS_WORKFLOW_ID
    _reject_fields(inputs, allowed, workflow=workflow)

    raw_features = inputs.get("features", [])
    if (
        not isinstance(raw_features, Sequence)
        or isinstance(raw_features, str | bytes | bytearray)
        or len(raw_features) > 50
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow} features An orderly array of up to 50 fields must be in place."
        )
    features = [
        _column(
            value,
            name=f"{workflow} features",
            whitelist=context.allowed_columns,
        )
        for value in raw_features
    ]
    if len(features) != len(set(features)):
        raise StrategyWorkflowValidationError(
            f"{workflow} features Could not close temporary folder: %s"
        )
    if context.target_col is not None and context.target_col in features:
        raise StrategyWorkflowValidationError(
            f"{workflow} features Cannot include target column{context.target_col}."
        )

    methods_supplied = "methods" in inputs
    raw_methods = inputs.get("methods", [])
    if (
        not isinstance(raw_methods, Sequence)
        or isinstance(raw_methods, str | bytes | bytearray)
        or (
            methods_supplied
            and not 1 <= len(raw_methods) <= len(UNIVARIATE_BINNING_METHODS)
        )
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow} methods Must contain 1 to"
            f"{len(UNIVARIATE_BINNING_METHODS)} A boxing method."
        )
    methods = [
        _required_text(value, name=f"{workflow} methods")
        for value in raw_methods
    ]
    unknown_methods = sorted(set(methods) - set(UNIVARIATE_BINNING_METHODS))
    if unknown_methods:
        raise StrategyWorkflowValidationError(
            f"{workflow} The boxing method is not supported:" + ",".join(unknown_methods) + "."
        )
    if len(methods) != len(set(methods)):
        raise StrategyWorkflowValidationError(
            f"{workflow} methods Repetition methods cannot be included."
        )

    bin_count = inputs.get("bin_count", 10)
    if (
        isinstance(bin_count, bool)
        or not isinstance(bin_count, int)
        or not 3 <= bin_count <= 20
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow} bin_count Must be the integer number of 3 to 20."
        )
    min_bin_pct = _bounded_number(
        inputs.get("min_bin_pct", 0.02),
        name=f"{workflow} min_bin_pct",
        maximum=0.5,
    )
    normalized: dict[str, Any] = {
        "features": features,
        "methods": methods,
        "bin_count": bin_count,
        "min_bin_pct": min_bin_pct,
        "sentinel_values": _sentinel_sequence(
            inputs.get("sentinel_values", []),
            name=f"{workflow} sentinel_values",
        ),
    }
    expected_manual_features = (
        features if manual_features is None else list(manual_features)
    )
    manual_breakpoints = _validate_manual_breakpoint_mapping(
        inputs.get("manual_breakpoints"),
        manual_requested="manual" in methods,
        expected_features=expected_manual_features,
        workflow=workflow,
    )
    if manual_breakpoints:
        normalized["manual_breakpoints"] = manual_breakpoints
    for field in ("loan_amount_col", "overdue_amount_col"):
        if field in inputs:
            normalized[field] = _column(
                inputs[field],
                name=f"{workflow} {field}",
                whitelist=context.allowed_columns,
            )
            if (
                context.target_col is not None
                and normalized[field] == context.target_col
            ):
                raise StrategyWorkflowValidationError(
                    f"{workflow} {field} The target column cannot be used."
                )
    if normalized.get("loan_amount_col") is not None and normalized.get(
        "loan_amount_col"
    ) == normalized.get("overdue_amount_col"):
        raise StrategyWorkflowValidationError(
            f"{workflow} loan_amount_col andoverdue_amount_col It must be different fields."
        )
    return normalized


def validate_univariate_refinement_inputs(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = UNIVARIATE_REFINEMENT_WORKFLOW_ID
    analysis_fields = {
        "features",
        "methods",
        "bin_count",
        "min_bin_pct",
        "loan_amount_col",
        "overdue_amount_col",
        "sentinel_values",
        "manual_breakpoints",
    }
    allowed = analysis_fields | {
        "feature",
        "method",
        "merge_groups",
        "selection",
        "selection_reason",
        "source_candidate_id",
    }
    _reject_fields(inputs, allowed, workflow=workflow)
    missing = sorted({"feature", "method", "selection"} - set(inputs))
    if missing:
        raise StrategyWorkflowValidationError(
            f"{workflow} Missing field:" + ",".join(missing) + "."
        )

    source_candidate_id = None
    if "source_candidate_id" in inputs:
        source_candidate_id = _required_text(
            inputs["source_candidate_id"],
            name=f"{workflow} source_candidate_id",
        )
        if _CANDIDATE_ID_RE.fullmatch(source_candidate_id) is None:
            raise StrategyWorkflowValidationError(
                f"{workflow} source_candidate_id It has to be complete.candidate id."
            )
        ignored_analysis_fields = sorted(set(inputs) & analysis_fields)
        if ignored_analysis_fields:
            raise StrategyWorkflowValidationError(
                f"{workflow} Already boundcandidate , and then reset the analysis parameters:"
                + ",".join(ignored_analysis_fields)
                + "."
            )

    feature = (
        _required_text(inputs["feature"], name=f"{workflow} feature")
        if source_candidate_id is not None
        else _column(
            inputs["feature"],
            name=f"{workflow} feature",
            whitelist=context.allowed_columns,
        )
    )
    if context.target_col is not None and feature == context.target_col:
        raise StrategyWorkflowValidationError(
            f"{workflow} feature The target column cannot be used."
        )
    method = _required_text(inputs["method"], name=f"{workflow} method")
    if method not in UNIVARIATE_REFINEMENT_METHODS:
        raise StrategyWorkflowValidationError(
            f"{workflow} Do not support the boxing method{method};Optional value is:"
            + ",".join(UNIVARIATE_REFINEMENT_METHODS)
            + "."
        )

    analysis: dict[str, Any] = {}
    if source_candidate_id is None:
        analysis_inputs = {
            field: inputs[field] for field in analysis_fields if field in inputs
        }
        if "features" not in analysis_inputs:
            analysis_inputs["features"] = [feature]
        if "methods" not in analysis_inputs and method != "categorical":
            analysis_inputs["methods"] = [method]
        analysis = validate_univariate_analysis_inputs(
            analysis_inputs,
            context,
        )
        if feature not in analysis["features"]:
            raise StrategyWorkflowValidationError(
                f"{workflow} feature Must include in this candidate fieldfeatures Medium."
            )
        if method != "categorical" and method not in analysis["methods"]:
            raise StrategyWorkflowValidationError(
                f"{workflow} method Must contain in this value box methodmethods Medium."
            )

    merge_groups = _candidate_merge_groups(
        inputs.get("merge_groups", []),
        name=f"{workflow} merge_groups",
    )
    selection = _candidate_selection(
        inputs["selection"],
        name=f"{workflow} selection",
    )
    uses_source_bin_ids = "source_bin_ids" in selection or bool(merge_groups)
    if uses_source_bin_ids and source_candidate_id is None:
        raise StrategyWorkflowValidationError(
            f"{workflow} Usesource bin id It must be provided that the user has already seen the evidence."
            "source_candidate_id,No re-analysis can be followed by speculation of binding."
        )
    normalized = {
        **analysis,
        "feature": feature,
        "method": method,
        "merge_groups": merge_groups,
        "selection": selection,
    }
    if source_candidate_id is not None:
        normalized["source_candidate_id"] = source_candidate_id
    if "selection_reason" in inputs:
        reason = _required_text(
            inputs["selection_reason"],
            name=f"{workflow} selection_reason",
        )
        if len(reason) > 500:
            raise StrategyWorkflowValidationError(
                f"{workflow} selection_reason Maximum 500 characters."
            )
        normalized["selection_reason"] = reason
    return normalized


def validate_candidate_monthly_stability_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    """Validate only the user's immutable source pointer."""

    workflow = CANDIDATE_STABILITY_WORKFLOW_ID
    if any(not isinstance(key, str) for key in inputs):
        raise StrategyWorkflowValidationError(f"{workflow} Field names must be text.")
    fields = set(inputs)
    if fields == {"asset_id"}:
        asset_id = _required_text(
            inputs["asset_id"],
            name=f"{workflow} asset_id",
        )
        if _CANDIDATE_ASSET_ID_RE.fullmatch(asset_id) is None:
            raise StrategyWorkflowValidationError(
                f"{workflow} asset_id It must be.candidate-asset- Pick up."
                "32 Bit lowercase hexadecimal character."
            )
        return {"asset_id": asset_id}
    if fields == {"strategy_type", "entry_id"}:
        strategy_type = _required_text(
            inputs["strategy_type"],
            name=f"{workflow} strategy_type",
        )
        if strategy_type not in STRATEGY_TYPES:
            raise StrategyWorkflowValidationError(
                f"{workflow} strategy_type It can only be:"
                + ",".join(STRATEGY_TYPES)
                + "."
            )
        entry_id = _required_text(
            inputs["entry_id"],
            name=f"{workflow} entry_id",
        )
        if _POOL_ENTRY_ID_RE.fullmatch(entry_id) is None:
            raise StrategyWorkflowValidationError(
                f"{workflow} entry_id It must be.pool-entry- Pick up."
                "32 Bit lowercase hexadecimal character."
            )
        return {
            "strategy_type": strategy_type,
            "entry_id": entry_id,
        }
    platform_fields = sorted(
        fields
        & {
            "source_kind",
            "source_artifact_id",
            "expected_artifact_content_hash",
            "expected_asset_id",
            "expected_asset_hash",
            "expected_pool_revision",
            "expected_pool_snapshot_hash",
            "dataset_id",
            "expected_dataset_content_hash",
            "workspace_revision",
            "workspace_generation",
            "analysis_generation",
            "semantic_mapping_hash",
            "sample_design_ref",
            "target_col",
            "month_col",
            "metrics",
            "psi",
        }
    )
    if platform_fields:
        raise StrategyWorkflowValidationError(
            f"{workflow} Include Platform-owned fields:"
            + ",".join(platform_fields)
            + ";These fields must bepreflight Restore.",
            code="candidate_monthly_stability_platform_binding_forbidden",
            fields=platform_fields,
        )
    raise StrategyWorkflowValidationError(
        f"{workflow} It must and can only provide a complete picture.asset_id,"
        "Or at the same time, provide claritystrategy_type With a completeentry_id.",
        code="candidate_monthly_stability_source_required",
        fields=("asset_id", "strategy_type", "entry_id"),
    )


def validate_scorecard_model_score_evidence_inputs(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = SCORECARD_EVIDENCE_WORKFLOW_ID
    allowed = {
        "features",
        "sample_weight_col",
        "seed",
        "max_iter",
        "scorecard_max_bins",
    }
    _reject_fields(inputs, allowed, workflow=workflow)
    missing = sorted(
        {"features", "seed", "max_iter", "scorecard_max_bins"} - set(inputs)
    )
    if missing:
        raise StrategyWorkflowValidationError(
            f"{workflow} Missing field:" + ",".join(missing) + "."
        )

    raw_features = inputs["features"]
    if (
        not isinstance(raw_features, Sequence)
        or isinstance(raw_features, str | bytes | bytearray)
        or not 1 <= len(raw_features) <= 50
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow} features An orderly array of 1 to 50 fields must be in place."
        )
    features = [
        _column(
            value,
            name=f"{workflow} features",
            whitelist=context.allowed_columns,
        )
        for value in raw_features
    ]
    if len(features) != len(set(features)):
        raise StrategyWorkflowValidationError(
            f"{workflow} features Could not close temporary folder: %s"
        )
    if context.target_col is not None and context.target_col in features:
        raise StrategyWorkflowValidationError(
            f"{workflow} features Cannot include target column{context.target_col}."
        )

    seed = inputs["seed"]
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or not 0 <= seed <= 4_294_967_295
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow} seed It must be 0 to 4294967295 integer."
        )
    max_iter = inputs["max_iter"]
    if (
        isinstance(max_iter, bool)
        or not isinstance(max_iter, int)
        or not 20 <= max_iter <= 5_000
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow} max_iter It must be 20 to 5,000 integers."
        )
    max_bins = inputs["scorecard_max_bins"]
    if (
        isinstance(max_bins, bool)
        or not isinstance(max_bins, int)
        or not 2 <= max_bins <= 20
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow} scorecard_max_bins Must be the integer number of 2 to 20."
        )

    normalized: dict[str, Any] = {
        "features": features,
        "seed": seed,
        "max_iter": max_iter,
        "scorecard_max_bins": max_bins,
    }
    if "sample_weight_col" in inputs:
        weight_col = _column(
            inputs["sample_weight_col"],
            name=f"{workflow} sample_weight_col",
            whitelist=context.allowed_columns,
        )
        if context.target_col is not None and weight_col == context.target_col:
            raise StrategyWorkflowValidationError(
                f"{workflow} sample_weight_col The target column cannot be used."
            )
        if weight_col in features:
            raise StrategyWorkflowValidationError(
                f"{workflow} sample_weight_col It cannot be a modeling feature at the same time."
            )
        normalized["sample_weight_col"] = weight_col
    return normalized


def validate_scorecard_band_build_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = SCORECARD_BAND_WORKFLOW_ID
    allowed = {"bin_count", "raw_pd_band_edges"}
    _reject_fields(inputs, allowed, workflow=workflow)
    if set(inputs) == allowed:
        raise StrategyWorkflowValidationError(
            f"{workflow} bin_count andraw_pd_band_edges One choice must be made;"
            "You can also omit all to use the Platform's default 10-frequency equivalent."
        )
    if "bin_count" in inputs:
        value = inputs["bin_count"]
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 2 <= value <= 20
        ):
            raise StrategyWorkflowValidationError(
                f"{workflow} bin_count Must be the integer number of 2 to 20."
            )
        return {"bin_count": value}
    if "raw_pd_band_edges" not in inputs:
        return {}
    raw = inputs["raw_pd_band_edges"]
    if (
        not isinstance(raw, Sequence)
        or isinstance(raw, str | bytes | bytearray)
        or not 3 <= len(raw) <= 21
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow} raw_pd_band_edges Must contain 3 to 21 numbers."
        )
    edges: list[float] = []
    for value in raw:
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(float(value))
        ):
            raise StrategyWorkflowValidationError(
                f"{workflow} raw_pd_band_edges Only limited numbers can be included."
            )
        edges.append(float(value))
    if edges[0] != 0.0 or edges[-1] != 1.0:
        raise StrategyWorkflowValidationError(
            f"{workflow} raw_pd_band_edges Must be from 0.0 Start and by 1.0 End."
        )
    if any(
        left >= right for left, right in zip(edges, edges[1:], strict=False)
    ):
        raise StrategyWorkflowValidationError(
            f"{workflow} raw_pd_band_edges It must be strictly incremental."
        )
    return {"raw_pd_band_edges": edges}


def validate_scorecard_cutoff_selection_inputs(
    inputs: Mapping[str, Any],
    _context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    workflow = SCORECARD_CUTOFF_WORKFLOW_ID
    allowed = {"asset_id", "cutoff_id", "reason"}
    _reject_fields(inputs, allowed, workflow=workflow)
    missing = sorted({"asset_id", "cutoff_id"} - set(inputs))
    if missing:
        raise StrategyWorkflowValidationError(
            f"{workflow} Missing field:" + ",".join(missing) + "."
        )
    asset_id = _required_text(inputs["asset_id"], name=f"{workflow} asset_id")
    cutoff_id = _required_text(
        inputs["cutoff_id"],
        name=f"{workflow} cutoff_id",
    )
    if _SCORECARD_BAND_ASSET_ID_RE.fullmatch(asset_id) is None:
        raise StrategyWorkflowValidationError(
            f"{workflow} asset_id It must be.scorecard-band-asset- Pick up."
            "32 Bit lowercase hexadecimal character."
        )
    if _SCORECARD_CUTOFF_ID_RE.fullmatch(cutoff_id) is None:
        raise StrategyWorkflowValidationError(
            f"{workflow} cutoff_id It must be.scorecard-cutoff- Pick up."
            "32 Bit lowercase hexadecimal character."
        )
    normalized = {"asset_id": asset_id, "cutoff_id": cutoff_id}
    if "reason" in inputs:
        reason = _required_text(inputs["reason"], name=f"{workflow} reason")
        if len(reason) > 500:
            raise StrategyWorkflowValidationError(
                f"{workflow} reason Maximum 500 characters."
            )
        normalized["reason"] = reason
    return normalized


def univariate_analysis_confirmation(inputs: Mapping[str, Any]) -> str:
    feature_text = (
        ",".join(inputs["features"])
        if inputs["features"]
        else "All candidate fields in the current semantic map"
    )
    method_text = (
        "Automatically compare numeric fields with equivalent, equidistance,ChiMerge,decision tree;class fields using equivalent boxes"
        if not inputs["methods"]
        else ",".join(inputs["methods"]) + ";Category fields are still using the equivalent box"
    )
    details = [
        "Recognized as [single variable candidate analysis]Workflow〕",
        f"Candidate fields:{feature_text}",
        "Boxing method:" + method_text,
        f"Target boxes{inputs['bin_count']},Minimum box share{inputs['min_bin_pct']:.2%}",
    ]
    if "loan_amount_col" in inputs:
        details.append(f"Disbursements:{inputs['loan_amount_col']}")
    if "overdue_amount_col" in inputs:
        details.append(f"Overdue amounts:{inputs['overdue_amount_col']}")
    if inputs["sentinel_values"]:
        details.append(
            "Independent sentry duty:"
            + ",".join(str(value) for value in inputs["sentinel_values"])
        )
    if "manual_breakpoints" in inputs:
        details.append(
            "Manual cut points:"
            + ";".join(
                feature
                + "=["
                + ",".join(f"{value:g}" for value in points)
                + "]"
                for feature, points in inputs["manual_breakpoints"].items()
            )
        )
    details.append("Generate Onlydevelopment/unvalidated The evidence is not a testimonial.")
    return ";".join(details)


def univariate_refinement_confirmation(inputs: Mapping[str, Any]) -> str:
    merge_text = (
        ";".join(" + ".join(group) for group in inputs["merge_groups"])
        if inputs["merge_groups"]
        else "Do not merge, keep the original box"
    )
    if "source_bin_ids" in inputs["selection"]:
        selection_text = "Visible selection" + ",".join(
            inputs["selection"]["source_bin_ids"]
        )
    else:
        threshold = inputs["selection"]["risk_threshold"]
        selection_text = (
            f"By observed bad rate{threshold['operator']} "
            f"{threshold['value']:.2%} Specific selection"
        )
    details = [
        "Recognized as [single variable candidate and merge]Workflow〕",
        f"Candidate fields and methods:{inputs['feature']} / {inputs['method']}",
        f"Box merge:{merge_text}",
        f"Candidate:{selection_text}",
        "The platform re-samples the sample from the mission evidence and recalculates the full indicator",
        "Generate Onlydevelopment/unvalidated Candidate assets, not independent validation, adoption or online",
    ]
    if "selection_reason" in inputs:
        details.append(f"Organisation{inputs['selection_reason']}")
    if "manual_breakpoints" in inputs:
        details.append(
            "Manual cut points:"
            + ";".join(
                feature
                + "=["
                + ",".join(f"{value:g}" for value in points)
                + "]"
                for feature, points in inputs["manual_breakpoints"].items()
            )
        )
    return ";".join(details)


def candidate_monthly_stability_confirmation(inputs: Mapping[str, Any]) -> str:
    details = ["Other OrganiserWorkflow〕"]
    if "asset_id" in inputs:
        details.extend(
            [
                f"Source: Single variable candidate assets available{inputs['asset_id']}",
                "Statistical calibration: the candidate hit/Undecided monthly distribution andPSI",
            ]
        )
    else:
        details.extend(
            [
                (
                    "Source: Current"
                    f"{inputs['strategy_type']} Strategy Pool Entry"
                    f"{inputs['entry_id']}"
                ),
                "Statistical calibration: the entry is currently usedPool The exact sequence of the first hit./Uncut distribution andPSI",
            ]
        )
    details.extend(
        [
            "Platform will be restored and certified before planned creationartifact/Pool CAS,Activitiesworkspace,"
            "Grown up.development SampleDesign Month Fields",
            "Base fixed to completedevelopment sample;eachYYYYMM The government has been working on the issue of the Internet."
            "No rolling changes to the benchmark",
            "This step generates only read-only stability evidence; it will not be modifiedPool,Pool entry, adoption or deployment",
        ]
    )
    return ";".join(details)


def scorecard_model_score_evidence_confirmation(
    inputs: Mapping[str, Any],
) -> str:
    details = [
        "Recognized as [ ]Scorecard Evidence of training and model scoringWorkflow〕",
        "Modelling characteristics:" + ",".join(inputs["features"]),
        f"Random torrent:{inputs['seed']}",
        f"Maximum number of words:{inputs['max_iter']}",
        f"Scorecard Maximum number of boxes:{inputs['scorecard_max_bins']}",
        "The platform will bind up to the latest complete authentication.StrategySampleDesign V2,First train the natives."
        " Scorecard,And then using the same training evidence to generate a full mission-level raw bad debts probability vector",
        "Models, training evidence, rating vectors and rating evidence are published and validated on a platform-by-platform basis",
        "This step is not comparable, selects, adopts, deploys and does not automatically selectcutoff",
    ]
    if "sample_weight_col" in inputs:
        details.append(f"Sample weight column:{inputs['sample_weight_col']}")
    return ";".join(details)


def scorecard_band_build_confirmation(inputs: Mapping[str, Any]) -> str:
    if "bin_count" in inputs:
        banding = f"Equivalent{inputs['bin_count']} Trail"
    elif "raw_pd_band_edges" in inputs:
        banding = (
            "raw PD Border["
            + ",".join(f"{value:g}" for value in inputs["raw_pd_band_edges"])
            + "]"
        )
    else:
        banding = "Ignored user band parameters, controlledTool Use default equal set of 10"
    return ";".join(
        [
            "Recognized as [ ]Scorecard Full fraction stripWorkflow〕",
            f"By-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-by-{banding}",
            "The platform will bind up to up-to-date, accurate and fully certifiedScoreEvidence,Original fraction vector"
            "andStrategySampleDesign V2;The latest evidence of damage is not going to be reversed.",
            "This step generates only a full and optional portion of the tape.cutoff Evidence; no automatic selection,"
            "Ranking or Recommendationscutoff",
            "Not going in, applied, adopted or deployed",
        ]
    )


def scorecard_cutoff_selection_confirmation(inputs: Mapping[str, Any]) -> str:
    details = [
        "Recognized as [ ]Scorecard cutoff Exact SelectionWorkflow〕",
        f"Full fraction with assetspointer:{inputs['asset_id']}",
        f"Precisioncutoff pointer:{inputs['cutoff_id']}",
        "The platform will be restored from the current tasksource artifact/hash (a) with a complete fractional strip;"
        "No automatic ranking or recommendation",
        "This step is only physical.pointer,Not copy all parts of the band; not enter pool, apply, adopt or deploy",
    ]
    if "reason" in inputs:
        details.append(f"User selection statement:{inputs['reason']}")
    return ";".join(details)


def prepare_univariate_analysis(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    slots = deep_thaw(inputs)
    assert isinstance(slots, dict)
    slots.update(_workflow_evidence(UNIVARIATE_ANALYSIS_WORKFLOW_ID, inputs, context, slots))
    if context.drop_nan_labels:
        slots["drop_nan_labels"] = True
    return PreparedStrategyPlan(
        workflow_id=UNIVARIATE_ANALYSIS_WORKFLOW_ID,
        template_id="strategy_univariate_candidate_analysis",
        slots=deep_freeze(slots),
    )


def prepare_univariate_refinement(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    slots = deep_thaw(inputs)
    assert isinstance(slots, dict)
    source_candidate_id = slots.pop("source_candidate_id", None)
    slots.update(
        _workflow_evidence(
            UNIVARIATE_REFINEMENT_WORKFLOW_ID,
            inputs,
            context,
            slots,
        )
    )
    existing = source_candidate_id is not None
    if context.drop_nan_labels and not existing:
        slots["drop_nan_labels"] = True
    return PreparedStrategyPlan(
        workflow_id=UNIVARIATE_REFINEMENT_WORKFLOW_ID,
        template_id=(
            "strategy_univariate_candidate_refinement_existing"
            if existing
            else "strategy_univariate_candidate_refinement"
        ),
        slots=deep_freeze(slots),
    )


def prepare_candidate_monthly_stability(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    if "asset_id" in inputs:
        slots: dict[str, Any] = {
            "source_kind": "univariate_asset",
        }
    else:
        slots = {
            "source_kind": "pool_entry",
            "strategy_type": inputs["strategy_type"],
            "entry_id": inputs["entry_id"],
        }
    slots.update(
        _workflow_evidence(CANDIDATE_STABILITY_WORKFLOW_ID, inputs, context, slots)
    )
    return PreparedStrategyPlan(
        workflow_id=CANDIDATE_STABILITY_WORKFLOW_ID,
        template_id="strategy_candidate_monthly_stability",
        slots=deep_freeze(slots),
    )


def prepare_scorecard_model_score_evidence(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    params: dict[str, Any] = {
        "max_iter": inputs["max_iter"],
        "scorecard_max_bins": inputs["scorecard_max_bins"],
    }
    if "sample_weight_col" in inputs:
        params["sample_weight_col"] = inputs["sample_weight_col"]
    slots: dict[str, Any] = {
        "features": deep_thaw(inputs["features"]),
        "params": params,
        "seed": inputs["seed"],
    }
    slots.update(
        _workflow_evidence(SCORECARD_EVIDENCE_WORKFLOW_ID, inputs, context, slots)
    )
    return PreparedStrategyPlan(
        workflow_id=SCORECARD_EVIDENCE_WORKFLOW_ID,
        template_id="strategy_scorecard_model_score_evidence_build",
        slots=deep_freeze(slots),
    )


def prepare_scorecard_band_build(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    slots: dict[str, Any] = {}
    if "bin_count" in inputs:
        slots["banding"] = {
            "method": "equal_frequency",
            "bin_count": inputs["bin_count"],
        }
    elif "raw_pd_band_edges" in inputs:
        slots["raw_pd_band_edges"] = deep_thaw(inputs["raw_pd_band_edges"])
    slots.update(
        _workflow_evidence(SCORECARD_BAND_WORKFLOW_ID, inputs, context, slots)
    )
    return PreparedStrategyPlan(
        workflow_id=SCORECARD_BAND_WORKFLOW_ID,
        template_id="strategy_scorecard_band_build",
        slots=deep_freeze(slots),
    )


def prepare_scorecard_cutoff_selection(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    slots: dict[str, Any] = {"cutoff_id": inputs["cutoff_id"]}
    if "reason" in inputs:
        slots["reason"] = inputs["reason"]
    slots.update(
        _workflow_evidence(SCORECARD_CUTOFF_WORKFLOW_ID, inputs, context, slots)
    )
    return PreparedStrategyPlan(
        workflow_id=SCORECARD_CUTOFF_WORKFLOW_ID,
        template_id="strategy_scorecard_cutoff_selection",
        slots=deep_freeze(slots),
    )


def _workflow_evidence(
    workflow_id: str,
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
    canonical_slots: Mapping[str, Any],
) -> dict[str, Any]:
    binder = context.bind_workflow_evidence
    if binder is None:
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Evidence bound for lack of Platform authentication.",
            code="strategy_workflow_evidence_binding_required",
        )
    frozen_inputs = deep_freeze(deep_thaw(inputs))
    evidence = binder(workflow_id, frozen_inputs)
    if not isinstance(evidence, Mapping):
        raise StrategyWorkflowValidationError(
            f"{workflow_id} The Platform evidence binds must return to the object.",
            code="strategy_workflow_evidence_invalid",
        )
    if any(not isinstance(key, str) for key in evidence):
        raise StrategyWorkflowValidationError(
            f"{workflow_id} The name of the Platform evidence bound field must be text.",
            code="strategy_workflow_evidence_invalid",
        )
    conflicts = sorted(set(evidence) & set(canonical_slots))
    if conflicts:
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Platform evidence cannot be overwrittencanonical slots:"
            + ",".join(conflicts)
            + ".",
            code="strategy_workflow_evidence_conflict",
            fields=conflicts,
        )
    copied = deep_thaw(deep_freeze(evidence))
    if not isinstance(copied, dict):  # pragma: no cover - Mapping guarded above
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Platform evidence binds cannot be copied.",
            code="strategy_workflow_evidence_invalid",
        )
    return copied


def _reject_fields(
    inputs: Mapping[str, Any],
    allowed: set[str],
    *,
    workflow: str,
) -> None:
    if any(not isinstance(key, str) for key in inputs):
        raise StrategyWorkflowValidationError(
            f"{workflow} workflow_inputs Field names must be text."
        )
    unexpected = sorted(set(inputs) - allowed)
    if unexpected:
        raise StrategyWorkflowValidationError(
            f"{workflow} workflow_inputs Contains unsupported fields:"
            + ",".join(unexpected)
            + "."
        )


def _column(
    value: object,
    *,
    name: str,
    whitelist: Sequence[str],
) -> str:
    column = _required_text(value, name=name)
    if column not in whitelist:
        raise StrategyWorkflowValidationError(
            f"{name} Use column of the data set that does not exist{column}]."
        )
    return column


def _required_text(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrategyWorkflowValidationError(f"{name} It must be non-empty.")
    return value.strip()


def _bounded_number(
    value: object,
    *,
    name: str,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise StrategyWorkflowValidationError(f"{name} It must be limited.")
    number = float(value)
    if (
        not math.isfinite(number)
        or number < 0
        or (maximum is not None and number > maximum)
    ):
        if maximum is None:
            raise StrategyWorkflowValidationError(
                f"{name} Must be a limited number greater than 0."
            )
        raise StrategyWorkflowValidationError(
            f"{name} It must be 0 to{maximum:g} There are limited numbers between."
        )
    return number


def _validate_manual_breakpoint_mapping(
    value: object,
    *,
    manual_requested: bool,
    expected_features: Sequence[str],
    workflow: str,
) -> dict[str, list[float]]:
    if value is None:
        if manual_requested:
            raise StrategyWorkflowValidationError(
                f"{workflow} manual The box must be provided.manual_breakpoints."
            )
        return {}
    if not manual_requested:
        raise StrategyWorkflowValidationError(
            f"{workflow} Only choice.manual It's only available when you're in the box.manual_breakpoints."
        )
    if not isinstance(value, Mapping) or not value:
        raise StrategyWorkflowValidationError(
            f"{workflow} manual_breakpoints Must be a non-empty field to the tangent array map."
        )
    expected = tuple(expected_features)
    if not expected or set(value) != set(expected) or len(value) != len(expected):
        raise StrategyWorkflowValidationError(
            f"{workflow} manual_breakpoints It must and can only be coveredmanual Axis/Fields:"
            + ",".join(expected)
            + "."
        )
    normalized: dict[str, list[float]] = {}
    for feature in expected:
        raw_points = value[feature]
        if (
            not isinstance(raw_points, Sequence)
            or isinstance(raw_points, str | bytes | bytearray)
            or not 1 <= len(raw_points) <= 19
        ):
            raise StrategyWorkflowValidationError(
                f"{workflow} manual_breakpoints.{feature} Must contain 1 to 19 cut points."
            )
        points: list[float] = []
        for item in raw_points:
            if isinstance(item, bool) or not isinstance(item, int | float):
                raise StrategyWorkflowValidationError(
                    f"{workflow} manual_breakpoints.{feature} Only limited numbers can be included."
                )
            if isinstance(item, int) and abs(item) > 2**53 - 1:
                raise StrategyWorkflowValidationError(
                    f"{workflow} manual_breakpoints.{feature} Beyond precisionJSON Scope."
                )
            number = float(item)
            if not math.isfinite(number):
                raise StrategyWorkflowValidationError(
                    f"{workflow} manual_breakpoints.{feature} Only limited numbers can be included."
                )
            points.append(number)
        if any(
            left >= right
            for left, right in zip(points, points[1:], strict=False)
        ):
            raise StrategyWorkflowValidationError(
                f"{workflow} manual_breakpoints.{feature} It must be strictly incremental and not repeated."
            )
        normalized[feature] = points
    return normalized


def _sentinel_sequence(value: object, *, name: str) -> list[str | int | float]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, str | bytes | bytearray)
        or len(value) > 20
    ):
        raise StrategyWorkflowValidationError(
            f"{name} must be a maximum of 20 text or limited number of arrays."
        )
    normalized: list[str | int | float] = []
    identities: set[str] = set()
    for item in value:
        if isinstance(item, bool) or not isinstance(item, str | int | float):
            raise StrategyWorkflowValidationError(
                f"{name} Only text or limited numbers are included."
            )
        if isinstance(item, float) and not math.isfinite(item):
            raise StrategyWorkflowValidationError(
                f"{name} Only text or limited numbers are included."
            )
        if isinstance(item, int) and abs(item) > 2**53 - 1:
            raise StrategyWorkflowValidationError(
                f"{name} Integer number in excess of precisionJSON Scope."
            )
        identity = json.dumps(
            [type(item).__name__, item],
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        if identity in identities:
            raise StrategyWorkflowValidationError(f"{name} Cannot contain duplicate values.")
        identities.add(identity)
        normalized.append(item)
    return normalized


def _candidate_merge_groups(value: object, *, name: str) -> list[list[str]]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, str | bytes | bytearray)
        or len(value) > 20
    ):
        raise StrategyWorkflowValidationError(
            f"{name} must be an array of up to 20 merged groups."
        )
    normalized: list[list[str]] = []
    seen: set[str] = set()
    for group_index, raw_group in enumerate(value):
        if (
            not isinstance(raw_group, Sequence)
            or isinstance(raw_group, str | bytes | bytearray)
            or not 2 <= len(raw_group) <= 20
        ):
            raise StrategyWorkflowValidationError(
                f"{name}[{group_index}] Must contain 2 to 20source bin id."
            )
        group: list[str] = []
        for raw_bin_id in raw_group:
            bin_id = _required_text(
                raw_bin_id,
                name=f"{name}[{group_index}]",
            )
            if len(bin_id) > 128:
                raise StrategyWorkflowValidationError(
                    f"{name} Mediumbin id Maximum 128 characters."
                )
            if bin_id in seen:
                raise StrategyWorkflowValidationError(
                    f"{name} Unable to repeatbin id {bin_id}."
                )
            seen.add(bin_id)
            group.append(bin_id)
        normalized.append(group)
    return normalized


def _candidate_selection(value: object, *, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str) for key in value
    ):
        raise StrategyWorkflowValidationError(f"{name} Must be the object.")
    keys = set(value)
    if keys not in ({"source_bin_ids"}, {"risk_threshold"}):
        raise StrategyWorkflowValidationError(
            f"{name} It must be.source_bin_ids andrisk_threshold One of the strictest."
        )
    if "source_bin_ids" in value:
        raw_ids = value["source_bin_ids"]
        if (
            not isinstance(raw_ids, Sequence)
            or isinstance(raw_ids, str | bytes | bytearray)
            or not 1 <= len(raw_ids) <= 50
        ):
            raise StrategyWorkflowValidationError(
                f"{name}.source_bin_ids Must contain 1 to 50source bin id."
            )
        bin_ids = [
            _required_text(item, name=f"{name}.source_bin_ids")
            for item in raw_ids
        ]
        if any(len(bin_id) > 128 for bin_id in bin_ids):
            raise StrategyWorkflowValidationError(
                f"{name}.source_bin_ids , and a value of up to 128 characters."
            )
        if len(bin_ids) != len(set(bin_ids)):
            raise StrategyWorkflowValidationError(
                f"{name}.source_bin_ids Cannot contain duplicate values."
            )
        return {"source_bin_ids": bin_ids}

    threshold = value["risk_threshold"]
    if not isinstance(threshold, Mapping) or any(
        not isinstance(key, str) for key in threshold
    ):
        raise StrategyWorkflowValidationError(
            f"{name}.risk_threshold Must be the object."
        )
    if set(threshold) != {"operator", "value"}:
        raise StrategyWorkflowValidationError(
            f"{name}.risk_threshold Only includeoperator andvalue."
        )
    operator = _required_text(
        threshold["operator"],
        name=f"{name}.risk_threshold.operator",
    )
    if operator not in {">=", ">", "<=", "<"}:
        raise StrategyWorkflowValidationError(
            f"{name}.risk_threshold.operator It's just...>=,>,<=,<."
        )
    risk_value = _bounded_number(
        threshold["value"],
        name=f"{name}.risk_threshold.value",
        maximum=1.0,
    )
    return {"risk_threshold": {"operator": operator, "value": risk_value}}


__all__ = [
    "UNIVARIATE_BINNING_METHODS",
    "UNIVARIATE_REFINEMENT_METHODS",
    "candidate_monthly_stability_confirmation",
    "prepare_candidate_monthly_stability",
    "prepare_scorecard_band_build",
    "prepare_scorecard_cutoff_selection",
    "prepare_scorecard_model_score_evidence",
    "prepare_univariate_analysis",
    "prepare_univariate_refinement",
    "scorecard_band_build_confirmation",
    "scorecard_cutoff_selection_confirmation",
    "scorecard_model_score_evidence_confirmation",
    "univariate_analysis_confirmation",
    "univariate_refinement_confirmation",
    "univariate_refinement_requirements",
    "validate_candidate_monthly_stability_inputs",
    "validate_scorecard_band_build_inputs",
    "validate_scorecard_cutoff_selection_inputs",
    "validate_scorecard_model_score_evidence_inputs",
    "validate_univariate_analysis_inputs",
    "validate_univariate_refinement_inputs",
]
