from __future__ import annotations

from pathlib import Path

from marvis.agent.gates.contracts import FailureEnvelope
from marvis.data.errors import CsvParseError, DataIngestError
from marvis.error_kinds import ErrorKind


_WORKFLOW_NAMES = {
    "data_join": "Data processing",
    "feature_analysis": "Characteristic analysis",
    "modeling": "Model development",
    "strategy": "Policy analysis",
    "vintage": "Vintage Risk analysis",
    "portfolio": "Group analysis",
}


def build_workflow_error_diagnostic(
    *,
    workflow: str,
    exc: Exception,
    task=None,
    setup_error: bool = False,
) -> dict:
    workflow_name = _WORKFLOW_NAMES.get(workflow, "Workstream")
    if _is_metadata_serialization_failure(exc):
        diagnostic = _metadata_serialization_diagnostic(workflow_name)
    elif isinstance(exc, CsvParseError):
        diagnostic = _csv_parse_diagnostic(workflow, workflow_name, exc)
    elif isinstance(exc, FileNotFoundError):
        filename = Path(str(getattr(exc, "filename", "") or "")).name or "Material file"
        diagnostic = {
            "code": "material_file_missing",
            "phase": "material_ingest",
            "title": f"{workflow_name}Not started",
            "summary": f"Could not find material file to read`{filename}`.",
            "cause": "The file may have been moved, renamed or the path to the file saved by the task is invalid.",
            "location": filename,
            "evidence": [{"label": "Missing file", "value": filename}],
            "actions": [
                "The confirmation material remains in the task directory and the file name remains unchanged.",
                "The re-loading or re-belt of the material is followed by a re-launching of the mission.",
            ],
            "retryable": True,
            "error_kind": "file_missing",
        }
    elif isinstance(exc, DataIngestError):
        diagnostic = {
            "code": "material_ingest_failed",
            "phase": "material_ingest",
            "title": f"{workflow_name}Not started",
            "summary": "The Platform was unable to read the material into an analytical data set.",
            "cause": _safe_message(exc),
            "location": "Material reading phase",
            "evidence": [],
            "actions": [
                "Confirms that the document is in the same format, extension and content.",
                "UseExcel/The data tool re-exports the material and re-starts the mission.",
            ],
            "retryable": True,
            "error_kind": "data_ingest",
        }
    elif setup_error:
        diagnostic = {
            "code": "workflow_setup_incomplete",
            "phase": "prepare",
            "title": f"{workflow_name}Not ready",
            "summary": _safe_message(exc),
            "cause": "Current material or task configuration is not sufficient to generate an implementation plan.",
            "location": "Plan preparation phase",
            "evidence": [],
            "actions": [
                "Supplement or adjust materials by the missing items above.",
                f"Relaunch after completion{workflow_name}.",
            ],
            "retryable": True,
            "error_kind": "setup",
        }
    else:
        diagnostic = {
            "code": "workflow_execution_failed",
            "phase": "prepare",
            "title": f"{workflow_name}Not completed",
            "summary": f"{workflow_name}The preparatory or implementation phase was discontinued and the subsequent steps were not continued.",
            "cause": "The platform encountered an anomaly in implementation that could not be automatically restored.",
            "location": "Current workflow step",
            "evidence": [],
            "actions": [
                "Expand technical information and check the location of the failure.",
                "Try again after the material or parameter has been amended; if repeated, keep the task number checked.",
            ],
            "retryable": True,
            "error_kind": "execution",
        }

    technical = _technical_detail(exc, task=task)
    return {
        "schema_version": "workflow_error.v1",
        "workflow": workflow,
        "exception_type": exc.__class__.__name__,
        "technical_detail": technical,
        **diagnostic,
    }


def enrich_workflow_error_diagnostic(diagnostic: dict) -> dict:
    """Upgrade persisted generic failures when a safe current diagnosis exists."""

    result = dict(diagnostic or {})
    if _is_parquet_column_alias_detail(result.get("technical_detail")) or (
        _is_parquet_column_alias_detail(result.get("cause"))
    ):
        result.update(_parquet_column_alias_diagnostic())
    elif (
        str(result.get("code") or "") == "workflow_execution_failed"
        and _is_metadata_serialization_detail(result.get("technical_detail"))
    ):
        workflow_name = _WORKFLOW_NAMES.get(str(result.get("workflow") or ""), "Workstream")
        result.update(_metadata_serialization_diagnostic(workflow_name))
    return result


def _parquet_column_alias_diagnostic() -> dict:
    return {
        "code": "platform_parquet_column_alias_failed",
        "phase": "execution",
        "title": "Scratch samples need to be re-executed",
        "summary": "The data were read, but the platform was interrupted when it extracted the model fields from the list as they were standard.",
        "cause": (
            "SourceParquet Include empty listings; the platform defines them asC0 The original name before the reading is still used for the column cropping."
            "This is a question of platform listing suitability, not targeting columns, cut-down settings or material content errors."
        ),
        "location": "Scratch samples...Parquet Column Crop",
        "evidence": [
            {"label": "Normative listing", "value": "C0"},
            {"label": "Attribution of responsibility", "value": "PlatformParquet Read Logic"},
        ],
        "actions": [
            "No need to modify or re-upload material byAgent Try the cut samples again using the current data.",
            "The Platform will use standardized listing completion fields to cut.",
        ],
        "agent_prompt": "It's a question of whether the platform can be automatically restored.Agent Retrying current steps?",
        "recovery_actions": [
            {"label": "ByAgent Retry current steps", "command": "Please help me with this and try again."},
        ],
        "retryable": True,
        "auto_recoverable": True,
        "error_kind": "platform_parquet_schema",
        "impact": "No output was achieved on the step; subsequent modelling steps have not been implemented.",
    }


def _metadata_serialization_diagnostic(workflow_name: str) -> dict:
    return {
        "code": "platform_metadata_serialization_failed",
        "phase": "prepare",
        "title": f"{workflow_name}Preparatory steps need to be re-executed",
        "summary": "Data were successfully read, but the platform was interrupted while saving image of the date field and the next steps have not yet started.",
        "cause": (
            "Platform does not save a date field image firstTimestamp ConvertJSON (a) Saveable date text;"
            "The material itself was not damaged."
        ),
        "location": "Enduring DSD field image",
        "evidence": [
            {"label": "Anomalous Value Type", "value": "Timestamp"},
            {"label": "Attribution of responsibility", "value": "Platform data readiness logic"},
        ],
        "actions": [
            "No need to modify or re-upload the material, the Platform will standardize the date value toISO date text.",
            "ByAgent Re-executing preparatory steps using current materials.",
        ],
        "agent_prompt": "It's a question of whether the platform can be automatically restored.Agent Direct re-execution?",
        "recovery_actions": [
            {"label": "ByAgent Re-execution", "command": "Please help me with this and try again."},
        ],
        "retryable": True,
        "auto_recoverable": True,
        "error_kind": "platform_serialization",
        "impact": "Data not broken; the model preparation steps have not yet generated an implementation plan.",
    }


def _is_metadata_serialization_failure(exc: Exception) -> bool:
    return isinstance(exc, TypeError) and _is_metadata_serialization_detail(str(exc))


def _is_metadata_serialization_detail(detail: object) -> bool:
    text = str(detail or "").lower()
    return "timestamp" in text and "not json serializable" in text


def _is_parquet_column_alias_detail(detail: object) -> bool:
    text = str(detail or "").lower()
    return "no match for fieldref.name(c0)" in text


def failure_envelope_for_diagnostic(diagnostic: dict) -> dict:
    return FailureEnvelope(
        failed_step_id=None,
        error_kind=str(diagnostic.get("error_kind") or "execution"),
        message=str(diagnostic.get("summary") or ""),
        retryable=bool(diagnostic.get("retryable", True)),
        suggested_actions=tuple(str(item) for item in diagnostic.get("actions") or []),
        downstream_reset="none",
    ).to_dict()


def workflow_error_content(diagnostic: dict) -> str:
    lines = [f"**{diagnostic['title']}**", str(diagnostic["summary"])]
    cause = str(diagnostic.get("cause") or "").strip()
    if cause:
        lines.extend(["", f"**Reason**:{cause}"])
    location = str(diagnostic.get("location") or "").strip()
    if location:
        lines.append(f"**Problem Location**:{location}")
    evidence = diagnostic.get("evidence") or []
    if evidence:
        lines.extend(["", "**Confirmed**:"])
        lines.extend(
            f"- {item.get('label', 'Evidence')}:{item.get('value', '')}"
            for item in evidence
        )
    actions = diagnostic.get("actions") or []
    if actions:
        lines.extend(["", "**Treatment of recommendations**:"])
        lines.extend(f"{index}. {action}" for index, action in enumerate(actions, start=1))
    return "\n".join(lines)


def _csv_parse_diagnostic(workflow: str, workflow_name: str, exc: CsvParseError) -> dict:
    filename = Path(exc.path).name
    line_number = exc.line_number
    expected = exc.expected_fields
    actual = exc.actual_fields
    if line_number is not None and expected is not None and actual is not None:
        summary = (
            f"CSV `{filename}` I'm sorry.{line_number} Number of line fields not consistent:"
            f"Projected{expected} Column, Actual{actual} Columns."
        )
        location = f"{filename} · I'm sorry.{line_number} Okay."
    else:
        summary = f"CSV `{filename}` , and the line structure cannot be broken down by the same field."
        location = filename
    evidence = [{"label": "Documentation", "value": filename}]
    if line_number is not None:
        evidence.append({"label": "Line Number", "value": str(line_number)})
    if expected is not None:
        evidence.append({"label": "Expected column(s)", "value": str(expected)})
    if actual is not None:
        evidence.append({"label": "Actual columns", "value": str(actual)})
    line_hint = f"I'm sorry.{line_number} Lines & Previous Lines" if line_number is not None else "Near the wrong line."
    return {
        "code": "csv_field_count_mismatch",
        "phase": "material_ingest",
        "title": f"{workflow_name}Not started",
        "summary": summary,
        "cause": (
            "ConfirmedCSV The number of lines is not consistent. Common possible reasons include the mixing of separator, the absence of quotation marks in the field."
            "or the document content does not match the extension; the platform does not skip bad lines to avoid silent changes in the sample."
        ),
        "location": location,
        "evidence": evidence,
        "actions": [
            f"UseExcel or text tool check`{filename}` It's...{line_hint},Amends the separator or quotation marks.",
            "Confirming that the documents are real.CSV;If it is,Excel,Save As`.xlsx` Or re-exportUTF-8 CSV.",
            f"Re-launch after maintaining the same number of columns as the table header{workflow_name}.",
        ],
        "retryable": True,
        "error_kind": ErrorKind.CSV_PARSE,
        "impact": "Data sets are not registered, implementation plans are not generated and follow-up steps are not operational.",
        "workflow": workflow,
        "line_number": line_number,
        "expected_fields": expected,
        "actual_fields": actual,
    }


def _technical_detail(exc: Exception, *, task=None) -> str:
    if isinstance(exc, CsvParseError):
        detail = f"ParserError: {exc.technical_message}"
    else:
        detail = f"{exc.__class__.__name__}: {_safe_message(exc)}"
    source_dir = str(getattr(task, "source_dir", "") or "")
    if source_dir:
        detail = detail.replace(source_dir, "<Catalogue of materials>")
    return detail[:2000]


def _safe_message(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


__all__ = [
    "build_workflow_error_diagnostic",
    "enrich_workflow_error_diagnostic",
    "failure_envelope_for_diagnostic",
    "workflow_error_content",
]
