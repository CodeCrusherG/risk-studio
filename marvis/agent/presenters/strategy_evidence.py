"""Strategy project, sample, model, report, and delivery presenters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from marvis.agent.presenters._shared import (
    format_number as _num,
    format_percent as _pct,
    format_value as _fmt,
)


def _strategy_report_integrity_failure() -> tuple[str, list[dict]]:
    return (
        "**StrategyReportBundle V2 Result integrity verification failed**:Schedule Caches & &canonical "
        "report bundle,Status or fourTaskArtifact Summary inconsistent, presentation stopped"
        "Identity, warning and download links. Recreate the report.",
        [],
    )


def _strategy_delivery_integrity_failure() -> tuple[str, list[dict]]:
    return (
        "**Complete validation of the policy delivery result failed**:Plan cache and trusted tasks/Step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-out, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in, step-in,"
        "canonical Strategy DSL,Equivalence evidence or evidence ofTaskArtifact registry Summary"
        "Inconsistencies, the display of delivery identities, sample numbers and download links has been stopped."
        "Delivery package; downloading interfaces will still be registeredhash Review of documents.",
        [],
    )


def _sample_design_integrity_failure() -> tuple[str, list[dict]]:
    return (
        "**The complete validation of the policy sample design results failed**:Schedule Caches & &canonical sample-design "
        "bundle/artifact The summary is inconsistent and the display of any sample indicator has been discontinued."
        "Download interfaces will still be pressedTaskArtifact Registrationhash Check the product.",
        [],
    )


def _sample_design_v2_integrity_failure() -> tuple[str, list[dict]]:
    return (
        "**Policy sample designV2 Result integrity verification failed**:Schedule Caches & &canonical "
        "sample-design bundle,membership orartifact Summary inconsistent, display stopped"
        "All samples are linked to the number, identity and download. Please rerun the strategy sample design; the unified product column will only"
        "Provision of passageTaskArtifact Registrationhash Validation of the product.",
        [],
    )


def _model_evidence_v2_integrity_failure() -> tuple[str, list[dict]]:
    return (
        "**Strategic analysis of evidenceV2 Result integrity verification failed**:Schedule Caches & &canonical "
        "sample-design/model-evidence bundle orartifact Summary inconsistent, display stopped"
        "Re-run strategy analysis of evidence generation; harmonize"
        "The product board will only show the registration and verify the pass.TaskArtifact.",
        [],
    )


def _model_score_comparison_integrity_failure() -> tuple[str, list[dict]]:
    return (
        "**Model rating compared to evidence integrity verification failed**:The plan cache did not prove the result to be maintained"
        " `no_selection`,The models, indicators and product information were discontinued as they were not adopted and deployed."
        "Please recreate comparative evidence; the platform does not extrapolate from abnormal loads or re-show champions.",
        [],
    )


def _project_context_integrity_failure() -> tuple[str, list[dict]]:
    return (
        "**The context integrity of the policy item failed**:Schedule Caches & &immutable revision/artifact "
        "Inconsistencies, the project status, history and missing information are discontinued.",
        [],
    )


def _render_materialize_project_context(o: dict):
    """Render only the authenticated project-context revision projection."""

    from marvis.packs.strategy.errors import StrategyError
    from marvis.packs.strategy.project_context_tools import (
        validate_materialize_project_context_tool_output,
    )

    try:
        o = validate_materialize_project_context_tool_output(o)
    except (StrategyError, RecursionError):
        return _project_context_integrity_failure()

    revision = o["revision"]
    state = revision["state"]
    current = state["current_project_snapshot"]
    histories = state["historical_strategy_reviews"]
    missing = state["missing_information_records"]
    artifact = o["context_artifact"]
    action = "Created" if o["created"] else "Unchanged, reused"
    text = (
        f"**Context of the Policy Item{action}**:revision **{revision['revision']}**,"
        f"Closing`{state['as_of']}`;Tie{len(state['source_refs'])} The evidence is not available."
        f"{len(histories)} A version of the history strategy.{len(missing)} entry.\n"
        f"Contextartifact:[{artifact['filename']}]({artifact['download_url']}),"
        f"content hash `{artifact['content_hash']}`."
    )
    if o["external_artifacts"]:
        text += (
            f"\n- Already{len(o['external_artifacts'])} (a) An external byte snapshot of the material;"
            "The Platform does not extract or speculate on any operational indicators from it."
        )
    if missing:
        text += (
            "\n- The questions that need to be added are recorded by field and level of blockage; after the user has explained that it is (not available for the time being),"
            "Report will be empty and markedunavailable,Not filled in zero."
        )

    status_rows = []
    for field_name in ("volume", "approval", "risk", "economics"):
        field = current["status_fields"][field_name]
        status_rows.append(
            [
                field_name,
                field["availability"],
                _fmt(field["value"]) if field["availability"] == "present" else "—",
                field.get("as_of") or "—",
                field.get("note") or "",
            ]
        )
    tables = [
        {
            "title": "Evidence of current project status",
            "columns": ["Fields", "Status", "Value", "As at", "Annotations"],
            "rows": status_rows,
        }
    ]
    if histories:

        def history_value(item, field_name):
            field = item[field_name]
            return field["value"] if field["availability"] == "present" else "—"

        tables.append(
            {
                "title": "History Policy Version",
                "columns": ["Version", "Asset status", "Effective date", "Availability", "Scope"],
                "rows": [
                    [
                        item.get("version") if item.get("version") is not None else "—",
                        history_value(item, "asset_status"),
                        (
                            f"{history_value(item, 'effective_period')['start']} ~ "
                            f"{history_value(item, 'effective_period')['end'] or 'Ongoing'}"
                            if history_value(item, "effective_period") != "—"
                            else "—"
                        ),
                        item["availability"],
                        history_value(item, "scope"),
                    ]
                    for item in histories
                ],
            }
        )
    if missing:
        tables.append(
            {
                "title": "Additional information to be provided",
                "columns": ["Fields", "Block Level", "Status", "Problem"],
                "rows": [
                    [
                        item["field_path"],
                        item["blocking"],
                        item["status"],
                        item["question"],
                    ]
                    for item in missing
                ],
            }
        )
    return text, tables


def _sample_design_metric_value(value: object, *, unit: str, status: str) -> str:
    if status != "present":
        return "n/a"
    if unit == "ratio":
        return _pct(value)
    return _num(value)


def _render_materialize_sample_design(o: dict):
    """Render only observations from the strictly validated Tool envelope."""

    from marvis.packs.strategy.errors import StrategyError
    from marvis.packs.strategy.sample_design_tools import (
        validate_materialize_sample_design_tool_output,
    )

    try:
        o = validate_materialize_sample_design_tool_output(o)
    except (StrategyError, RecursionError):
        return _sample_design_integrity_failure()

    bundle = o["bundle"]
    design = bundle["sample_design"]
    boundary = design["active_dataset_boundary"]
    performance = design["performance_window"]
    observation = design["observation_window"]
    target = design["target_definition"]
    split = design["split_definition"]
    optional = design["optional_fields"]
    lifecycle = design["lifecycle"]
    artifact = o["artifact"]
    performance_text = (
        f"provided / {performance['days']} Oh, my God."
        if performance["status"] == "provided"
        else "unavailable"
    )
    observation_text = (
        f"provided / {observation['start']} to{observation['end']}"
        if observation["status"] == "provided"
        else "unavailable"
    )
    text = (
        f"**Policy sample design solidified**:`{o['sample_design_id']}`,content hash "
        f"`{o['content_hash']}`;Sample activity**{_num(boundary['population_count'])}** All right."
        f"Show the window.`{performance_text}`,Watch the windows.`{observation_text}`,"
        f"Mature`{design['maturity']}`,Target column`{target['column']}`(Bad sample value"
        f"`{target['bad_value']}`,Good sample value`{target['good_value']}`),"
        f"Sample splitting`{split['status']}`.\n"
        f"Current life cycle`{lifecycle['candidate_stage']} / "
        f"{lifecycle['validation_status']}`;**Only sample evidence generated, no policy created or modified,"
        "Unmodeled, unconstructed, unpooled, unadoptioned, non-deployment.**"
    )
    if design["scope"] == "exploration_only":
        text += "\n- Current`exploration-only`:The sample cannot be claimed to be mature or to have been independently validated."
    if split["status"] == "unavailable":
        text += "\n- Development/Authentication/OOT Severationunavailable;Show Onlyoverall Sample evidence."
    missing_optional = [
        label
        for field, label in (
            ("month_field", "Month"),
            ("weight_field", "weight column"),
            ("loan_amount_field", "Lending amount line"),
            ("overdue_amount_field", "Overdue Amount Column"),
        )
        if optional[field] is None
    ]
    if missing_optional:
        text += "\n- Optional calibrationunavailable:" + ",".join(missing_optional) + "."
    if artifact.get("download_url"):
        text += (
            "\n\n**Sample design evidence**:"
            f"[{artifact['filename']}]({artifact['download_url']})"
        )

    definitions = {
        item["metric_definition_id"]: item for item in bundle["metric_definitions"]
    }
    rows_by_kind: dict[str, list[list[str]]] = {"overall": [], "split": []}
    for item in bundle["metric_observations"]:
        definition = definitions[item["metric_definition_ref"]["metric_definition_id"]]
        dimension = item["dimension"]
        rows_by_kind[dimension["kind"]].append(
            [
                str(dimension["value"]),
                str(definition["metric_key"]),
                str(definition["display_name"]),
                str(item["status"]),
                _sample_design_metric_value(
                    item["value"],
                    unit=str(definition["unit"]),
                    status=str(item["status"]),
                ),
                _num(item["numerator"]),
                _num(item["denominator"]),
                _num(item["sample_count"]),
            ]
        )
    columns = [
        "Sample dimensions",
        "Indicator Keys",
        "Indicators",
        "Status",
        "Value",
        "Molecular",
        "Factor",
        "Number of samples of dimensions",
    ]
    tables: list[dict] = []
    if rows_by_kind["overall"]:
        tables.append(
            {
                "title": "Policy sample designOverall Indicators",
                "columns": columns,
                "rows": rows_by_kind["overall"],
            }
        )
    if rows_by_kind["split"]:
        tables.append(
            {
                "title": "Policy sample design development/Authentication/OOT Indicators",
                "columns": columns,
                "rows": rows_by_kind["split"],
            }
        )
    red_flags = design["red_flags"]
    if red_flags:
        tables.append(
            {
                "title": "The red flag for the policy sample.",
                "columns": ["Level", "Code", "Annotations"],
                "rows": [
                    [flag["level"], flag["code"], flag["message"]] for flag in red_flags
                ],
            }
        )
    if o["warnings"]:
        text += "\n\n**Sample Design Tips**:" + ";".join(o["warnings"])
    return text, tables


def _strategy_sample_v2_population_rows(bundle: dict) -> list[list[str]]:
    rows: list[list[str]] = []
    for population in bundle["populations"]:
        partitions = {
            item["name"]: item["row_count"] for item in population["partitions"]
        }
        maturity = population["maturity_evidence"]
        rows.append(
            [
                population["role"],
                _num(population["total_count"]),
                _num(partitions["development"]),
                _num(partitions["validation"]),
                _num(partitions["oot"]),
                maturity["status"],
            ]
        )
    return rows


def _render_materialize_sample_design_v2(o: dict):
    """Render only facts validated from the cached V2 sample envelope."""

    from marvis.packs.strategy.errors import StrategyError
    from marvis.packs.strategy.sample_design_v2_tools import (
        validate_materialize_sample_design_v2_tool_output,
    )

    try:
        o = validate_materialize_sample_design_v2_tool_output(o)
    except (StrategyError, RecursionError):
        return _sample_design_v2_integrity_failure()
    return _render_validated_sample_design_v2(o)


def _render_materialize_sample_design_v2_native(o: dict):
    """Render only facts validated from the native V2 sample envelope."""

    from marvis.packs.strategy.errors import StrategyError
    from marvis.packs.strategy.sample_design_v2_native_tools import (
        validate_materialize_sample_design_v2_native_tool_output,
    )

    try:
        o = validate_materialize_sample_design_v2_native_tool_output(o)
    except (StrategyError, RecursionError):
        return _sample_design_v2_integrity_failure()
    return _render_validated_sample_design_v2(
        o,
        native_source=True,
    )


def _render_validated_sample_design_v2(
    o: dict,
    *,
    native_source: bool = False,
):
    """Render one already authenticated V2 envelope."""

    bundle = o["bundle"]
    design = bundle["sample_design"]
    semantics = design["sample_semantics"]
    historical = bundle["historical_score"]
    risk_population = next(
        item for item in bundle["populations"] if item["role"] == "risk"
    )
    maturity = risk_population["maturity_evidence"]
    score_detail = historical["status"]
    if historical["status"] == "available":
        score_detail += f" / {historical['column']} / {historical['direction']}"
    else:
        score_detail += f" / {historical['reason']}"

    text = (
        f"**Policy sample designV2 Solid**:Scope`{semantics['scope']}`,"
        f"Population relations`{design['relationship']}`;Lockedapproval/risk Two crowds."
        "development,validation,OOT Division.\n"
        f"- Risk sample maturity:`{maturity['status']}`;History rating:`{score_detail}`.\n"
        "- This step only solidifies sample and diagnostic evidence, without creating strategy, non-adoption and non-deployment."
    )
    if native_source:
        text += f"\n- Source: Primary Activity Data Set.`{o['source_binding']['source_mode']}`."
    if semantics["scope"] == "exploration_only":
        text += "\n- Current range isexploration-only,A mature sample validation cannot be claimed."
    if o["warnings"]:
        text += "\n- Diagnosis:" + ";".join(o["warnings"]) + "."
    else:
        text += "\n- Diagnostic tip: None."

    bundle_artifact = o["artifacts"]["bundle"]
    membership_artifact = o["artifacts"]["membership"]
    text += (
        "\n\n**Summary of sample products (non-)registry Identification)**:"
        f"bundle `{bundle_artifact['filename']}`,canonical content hash "
        f"`{bundle_artifact['content_hash']}`;membership "
        f"`{membership_artifact['filename']}`,membership semantic content hash "
        f"`{o['membership_content_hash']}`.\n"
        "- Downloads are done using the task page unified product bar.Tool v2 envelope Not credible"
        "download_url,registry artifact id ormembership binary artifact hash,"
        "This renderer does not spell links."
    )

    tables: list[dict] = [
        {
            "title": "Double-population sampled area",
            "columns": [
                "Population",
                "Total sample",
                "Development set",
                "Authentication Set",
                "OOT",
                "Mature",
            ],
            "rows": _strategy_sample_v2_population_rows(bundle),
        },
        {
            "title": "Sample design caliber",
            "columns": ["Item", "Status/Value", "Additional explanation"],
            "rows": [
                ["scope", semantics["scope"], "Sample use range"],
                ["relationship", design["relationship"], "Double crowd relationship"],
                ["risk maturity", maturity["status"], maturity["reason"] or ""],
                ["historical score", historical["status"], score_detail],
            ],
        },
        {
            "title": "Sample diagnostics",
            "columns": ["Category", "Code", "Status", "Annotations"],
            "rows": [
                [
                    item["category"],
                    item["code"],
                    item["status"],
                    item["message"],
                ]
                for item in bundle["diagnostics"]
            ],
        },
        {
            "title": "Summary of sample products",
            "columns": ["Role", "Type", "Documentation", "cached Authenticablehash"],
            "rows": [
                [
                    "sample-design bundle",
                    bundle_artifact["kind"],
                    bundle_artifact["filename"],
                    bundle_artifact["content_hash"],
                ],
                [
                    "membership",
                    membership_artifact["kind"],
                    membership_artifact["filename"],
                    f"semantic:{o['membership_content_hash']}",
                ],
            ],
        },
    ]
    return text, tables


def _strategy_model_v2_evidence_rows(bundle: dict) -> list[list[str]]:
    rows: list[list[str]] = []
    for evidence in bundle["univariate_evidence"]:
        statuses = {
            "present": 0,
            "unavailable": 0,
            "not_matured": 0,
            "not_applicable": 0,
        }
        for observation in evidence["observations"]:
            statuses[observation["status"]] += 1
        rows.append(
            [
                evidence["feature"],
                evidence["analysis_variant"],
                _num(len(evidence["bins"])),
                _num(len(evidence["observations"])),
                _num(statuses["present"]),
                _num(statuses["unavailable"]),
                _num(statuses["not_matured"]),
                _num(statuses["not_applicable"]),
            ]
        )
    return rows


def _render_materialize_model_evidence_v2(o: dict):
    """Render authenticated V2 univariate evidence without inventing a download."""

    from marvis.packs.strategy.errors import StrategyError
    from marvis.packs.strategy.model_evidence_tools import (
        validate_materialize_model_evidence_v2_tool_output,
    )

    try:
        o = validate_materialize_model_evidence_v2_tool_output(o)
    except (StrategyError, RecursionError):
        return _model_evidence_v2_integrity_failure()

    bundle = o["bundle"]
    evidence = bundle["univariate_evidence"]
    artifact = o["artifact"]
    text = (
        f"**Strategic analysis of evidenceV2 Solid**:Authenticated**{len(evidence)}** A single variable evidence,"
        "The scope of evidence is:`risk/development`.\n"
        "- For now.**univariate-only**:No model created, no model comparison performed, no adoption,"
        "Not deployed.\n"
        f"- Evidence documents`{artifact['filename']}`,content hash "
        f"`{artifact['content_hash']}`;Downloads are done using the task page unified product bar.Tool v3 "
        "envelope Not credibledownload_url orregistry artifact id,This rendering doesn't."
        "Self-screw links."
    )
    tables = [
        {
            "title": "Evidence for single variables",
            "columns": [
                "Variables",
                "Analysis methodology",
                "Number of boxes",
                "Number of observations",
                "present",
                "unavailable",
                "not_matured",
                "not_applicable",
            ],
            "rows": _strategy_model_v2_evidence_rows(bundle),
        }
    ]
    return text, tables


def _render_materialize_model_score_comparison_v2(o: dict):
    """Present deterministic same-sample evidence without implying selection."""

    comparison = o.get("comparison")
    governance = o.get("governance")
    artifact = o.get("artifact")
    if not all(
        isinstance(value, Mapping) for value in (comparison, governance, artifact)
    ):
        raise ValueError("model-score comparison presenter requires its envelope")
    assert isinstance(comparison, Mapping)
    assert isinstance(governance, Mapping)
    assert isinstance(artifact, Mapping)
    selection = comparison.get("selection")
    if (
        not isinstance(selection, Mapping)
        or selection.get("status") != "no_selection"
        or governance.get("selection_status") != "no_selection"
        or governance.get("winner_selected") is not False
        or governance.get("not_adopted") is not True
        or governance.get("not_deployed") is not True
    ):
        raise ValueError("model-score comparison governance is not nonselecting")

    metrics = [
        metric
        for metric in (comparison.get("metrics") or [])
        if isinstance(metric, Mapping)
    ]
    model_ids: list[str] = []
    for metric in metrics:
        for item in metric.get("model_values") or []:
            if not isinstance(item, Mapping):
                continue
            ref = item.get("model_evidence_ref")
            evidence_id = ref.get("evidence_id") if isinstance(ref, Mapping) else None
            if isinstance(evidence_id, str) and evidence_id not in model_ids:
                model_ids.append(evidence_id)

    rows = []
    for metric in metrics:
        values = {}
        for item in metric.get("model_values") or []:
            if not isinstance(item, Mapping):
                continue
            ref = item.get("model_evidence_ref")
            evidence_id = ref.get("evidence_id") if isinstance(ref, Mapping) else None
            if isinstance(evidence_id, str):
                values[evidence_id] = item.get("value")
        rows.append(
            [
                str(metric.get("metric_key") or ""),
                str(metric.get("period") or "Overall"),
                str(metric.get("unit") or ""),
                *[_num(values.get(evidence_id)) for evidence_id in model_ids],
                _num(metric.get("delta")),
            ]
        )

    text = (
        "**Model score comparison evidence generated**:"
        f"Same certified sample`{o.get('population', '')} / {o.get('partition', '')}`,"
        f"Comparison**{len(model_ids)}** A model.**{len(metrics)}** Common set of indicators.\n"
        "- State of governance:**No champions selected, no adoptable, no deployment**;This result provides only evidence of a comparative level of certainty."
    )
    filename = artifact.get("filename")
    download_url = artifact.get("download_url")
    if isinstance(filename, str) and isinstance(download_url, str):
        text += f"\n- Evidentiary documents:[{filename}]({download_url})"

    tables = []
    if rows:
        tables.append(
            {
                "title": "Same model score indicator",
                "columns": ["Indicators", "Period", "Units", *model_ids, "Difference"],
                "rows": rows,
            }
        )
    return text, tables


def _render_build_strategy_report_bundle_v2(o: dict):
    """Render only a fully validated governed report publication envelope."""

    from marvis.packs.strategy.errors import StrategyError
    from marvis.packs.strategy.report_bundle_tools import (
        validate_build_strategy_report_bundle_v2_tool_output,
    )

    try:
        o = validate_build_strategy_report_bundle_v2_tool_output(o)
    except (StrategyError, RecursionError):
        return _strategy_report_integrity_failure()

    warnings = o["warnings"]
    warning_text = ";".join(warnings) if warnings else "None"
    download_labels = {
        "json": "JSON",
        "markdown": "Markdown",
        "xlsx": "XLSX",
        "docx": "DOCX",
    }
    downloads = " · ".join(
        f"[{download_labels[artifact['format']]}]({artifact['download_url']})"
        for artifact in o["artifacts"]
    )
    text = (
        f"**StrategyReportBundle V2 Generated**:ReportID `{o['report_id']}`,"
        f"revision **{o['report_revision']}**,Status**{o['status']}**.\n"
        "- The steps in generating this report did not create or change strategic assets, nor did they implement adoption, deployment or online;"
        "The life cycle status of the report is derived from certified evidence.\n"
        f"- Integrity warning:{warning_text}\n"
        f"- Download:{downloads}"
    )
    return text, []


def _render_export_strategy_delivery(
    o: dict,
    *,
    trusted_task_id: str | None,
    trusted_inputs: Mapping[str, Any] | None,
    trusted_artifacts: Mapping[str, Any] | None,
):
    """Render the internally bound, hash-pinned Strategy DSL delivery."""

    from marvis.packs.strategy.dsl_delivery_tools import (
        DELIVERY_ARTIFACT_KINDS,
        StrategyDeliveryToolError,
        validate_export_strategy_delivery_tool_output,
        validate_strategy_delivery_artifact_records,
    )

    try:
        if (
            not isinstance(trusted_task_id, str)
            or not trusted_task_id
            or not isinstance(trusted_inputs, Mapping)
            or set(trusted_inputs)
            != {
                "strategy_ref",
                "dataset_ref",
                "workspace_ref",
                "maximum_equivalence_rows",
            }
            or not isinstance(trusted_artifacts, Mapping)
            or o.get("maximum_equivalence_rows")
            != trusted_inputs["maximum_equivalence_rows"]
        ):
            raise StrategyDeliveryToolError(
                "renderer is missing authenticated delivery context"
            )
        expected_artifacts = validate_strategy_delivery_artifact_records(
            trusted_artifacts,
            expected_task_id=trusted_task_id,
            expected_delivery_id=o.get("delivery_id"),
            expected_strategy_ref=trusted_inputs["strategy_ref"],
            expected_dataset_ref=trusted_inputs["dataset_ref"],
            expected_workspace_ref=trusted_inputs["workspace_ref"],
            expected_maximum_equivalence_rows=trusted_inputs[
                "maximum_equivalence_rows"
            ],
            expected_equivalence=o.get("equivalence"),
        )
        o = validate_export_strategy_delivery_tool_output(
            o,
            expected_task_id=trusted_task_id,
            expected_strategy_ref=trusted_inputs["strategy_ref"],
            expected_dataset_ref=trusted_inputs["dataset_ref"],
            expected_workspace_ref=trusted_inputs["workspace_ref"],
            expected_artifacts=expected_artifacts,
        )
    except (
        AttributeError,
        IndexError,
        KeyError,
        RecursionError,
        StrategyDeliveryToolError,
        TypeError,
    ):
        return _strategy_delivery_integrity_failure()

    download_labels = {
        DELIVERY_ARTIFACT_KINDS["python"]: "Python",
        DELIVERY_ARTIFACT_KINDS["sql"]: "DuckDB SQL",
        DELIVERY_ARTIFACT_KINDS["strategy_json"]: "Strategy JSON",
        DELIVERY_ARTIFACT_KINDS["equivalence_json"]: "Equivalence JSON",
    }
    downloads = " · ".join(
        f"[{download_labels[artifact['kind']]}]({artifact['download_url']})"
        for artifact in o["artifacts"]
    )
    equivalence = o["equivalence"]
    scope_status = "bounded" if equivalence["bounded"] else "full"
    text = (
        f"**Strategy DSL Offline delivery generated**:DeliveryID `{o['delivery_id']}`,"
        f"Policy Type**{o['strategy_type']}**,Version**{o['strategy_version']}**.\n"
        f"- Equivalent verification:sample_count **{equivalence['sample_count']}** / "
        f"source_row_count **{o['source_row_count']}**(**{scope_status}**).\n"
        "- Implementation of the border:**offline-only**;"
        "**not_applied=true / not_adopted=true / not_deployed=true**"
        "(Not applied, not accepted, not deployed.\n"
        f"- The content of the Hashi fixed download:{downloads}"
    )
    return text, []


EVIDENCE_PRESENTERS = {
    "build_report_bundle_v2": _render_build_strategy_report_bundle_v2,
    "export_strategy_delivery": _render_export_strategy_delivery,
    "materialize_project_context": _render_materialize_project_context,
    "materialize_sample_design": _render_materialize_sample_design,
    "materialize_sample_design_v2": _render_materialize_sample_design_v2,
    "materialize_sample_design_v2_native": _render_materialize_sample_design_v2_native,
    "materialize_model_evidence_v2": _render_materialize_model_evidence_v2,
    "materialize_model_score_comparison_v2": _render_materialize_model_score_comparison_v2,
}

INTEGRITY_FAILURES = {
    "build_report_bundle_v2": _strategy_report_integrity_failure,
    "export_strategy_delivery": _strategy_delivery_integrity_failure,
    "materialize_sample_design": _sample_design_integrity_failure,
    "materialize_sample_design_v2": _sample_design_v2_integrity_failure,
    "materialize_sample_design_v2_native": _sample_design_v2_integrity_failure,
    "materialize_model_evidence_v2": _model_evidence_v2_integrity_failure,
    "materialize_model_score_comparison_v2": _model_score_comparison_integrity_failure,
    "materialize_project_context": _project_context_integrity_failure,
}

__all__ = ["EVIDENCE_PRESENTERS", "INTEGRITY_FAILURES"]
