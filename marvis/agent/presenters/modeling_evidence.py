"""Fail-closed presenters for authenticated Modeling V2 evidence outputs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from marvis.packs.modeling.evidence_tools import (
    validate_train_model_with_evidence_v2_tool_output,
)
from marvis.packs.modeling.score_evidence_tools import (
    validate_materialize_model_score_evidence_v2_tool_output,
)


_INTEGRITY_ERROR = (
    "canonical Tool output authentication failed; presentation stopped"
)


class CanonicalPresenterIntegrityError(ValueError):
    """A governed Tool result could not be authenticated for presentation."""


def _trusted_task_id(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise CanonicalPresenterIntegrityError(_INTEGRITY_ERROR)
    return value.strip()


def _authenticate(
    validator: Callable[..., dict[str, Any]],
    output: object,
    *,
    runtime: object,
    task_id: object,
    trusted_inputs: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if runtime is None:
        raise CanonicalPresenterIntegrityError(_INTEGRITY_ERROR)
    trusted_task_id = _trusted_task_id(task_id)
    if not isinstance(trusted_inputs, Mapping):
        raise CanonicalPresenterIntegrityError(_INTEGRITY_ERROR)
    try:
        return validator(
            output,
            runtime=runtime,
            task_id=trusted_task_id,
            trusted_inputs=trusted_inputs,
        )
    except CanonicalPresenterIntegrityError:
        raise
    except Exception as exc:
        raise CanonicalPresenterIntegrityError(_INTEGRITY_ERROR) from exc


def _artifact_rows(artifacts: Mapping[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for role in sorted(artifacts):
        artifact = artifacts[role]
        rows.append(
            [
                role,
                str(artifact["kind"]),
                str(artifact["artifact_id"]),
                str(artifact["content_hash"]),
                str(artifact["filename"]),
            ]
        )
    return rows


def _render_train_model_with_evidence_v2(
    output: object,
    *,
    runtime: object,
    task_id: str,
    trusted_inputs: Mapping[str, Any] | None = None,
    trusted_artifacts: Mapping[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    del trusted_artifacts
    value = _authenticate(
        validate_train_model_with_evidence_v2_tool_output,
        output,
        runtime=runtime,
        task_id=task_id,
        trusted_inputs=trusted_inputs,
    )
    text = (
        "**Evidence of governance modelling is certified.**"
        f"Experiment`{value['experiment_id']}`,Model`{value['model_artifact_id']}` "
        f"and training evidence`{value['evidence_id']}` A non-variable product has been bound to the task."
        "This step is based on the materialization of candidate models and their certainty; un-pooled, unadoptional and non-deployment."
    )
    return text, [
        {
            "title": "Evidence identity for governance modelling",
            "columns": ["Fields", "Value"],
            "rows": [
                ["Schema Version", value["schema_version"]],
                ["Experiment ID", value["experiment_id"]],
                ["Model Artifact ID", value["model_artifact_id"]],
                ["Evidence ID", value["evidence_id"]],
                ["Evidence Content Hash", value["evidence_content_hash"]],
                ["Score Product", value["score_product"]],
            ],
        },
        {
            "title": "Invertable products in the mission",
            "columns": ["Role", "Kind", "Artifact ID", "Content Hash", "Filename"],
            "rows": _artifact_rows(value["artifacts"]),
        },
    ]


def _render_materialize_model_score_evidence_v2(
    output: object,
    *,
    runtime: object,
    task_id: str,
    trusted_inputs: Mapping[str, Any] | None = None,
    trusted_artifacts: Mapping[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    del trusted_artifacts
    value = _authenticate(
        validate_materialize_model_score_evidence_v2_tool_output,
        output,
        runtime=runtime,
        task_id=task_id,
        trusted_inputs=trusted_inputs,
    )
    text = (
        "**Modelling sub-evidence certified.**"
        f"Evidence`{value['evidence_id']}` & Coding with Single Model Evidence"
        f"`{value['single_model_evidence_id']}` A non-variable product has been bound to the task."
        "This step will only be used to distil evidence from space models and will not result in model or strategy conclusions;"
        "Unpositioned, unaccommodated, undeployed."
    )
    return text, [
        {
            "title": "Model evidence identity",
            "columns": ["Fields", "Value"],
            "rows": [
                ["Schema Version", value["schema_version"]],
                ["Evidence ID", value["evidence_id"]],
                ["Evidence Content Hash", value["evidence_content_hash"]],
                ["Single Model Evidence ID", value["single_model_evidence_id"]],
                [
                    "Single Model Evidence Content Hash",
                    value["single_model_evidence_content_hash"],
                ],
                ["Input Space", value["input_space"]],
                ["Tool Content Hash", value["content_hash"]],
            ],
        },
        {
            "title": "Invertable products in the mission",
            "columns": ["Role", "Kind", "Artifact ID", "Content Hash", "Filename"],
            "rows": _artifact_rows(value["artifacts"]),
        },
    ]


MODELING_EVIDENCE_PRESENTERS = {
    "train_model_with_evidence_v2": _render_train_model_with_evidence_v2,
    "materialize_model_score_evidence_v2": (
        _render_materialize_model_score_evidence_v2
    ),
}


__all__ = [
    "CanonicalPresenterIntegrityError",
    "MODELING_EVIDENCE_PRESENTERS",
]
