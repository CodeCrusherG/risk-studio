from __future__ import annotations

import time
from collections.abc import Callable

from marvis.agent.orchestrator import AgentValidationCancelled


def agent_stage_opening_text(
    stage: str,
    *,
    validation_workflow_version: int | None = None,
) -> str:
    if stage == "reproducibility":
        if validation_workflow_version == 2:
            return "Copy that. I'll continue.PMML Rating test, using submittedPMML The sample was rated in full."
        return "Copy that. I'm going to continue to run the model replicability validation.Notebook And check code model scores and submissionsPMML Consistency of scores."
    if stage == "metrics":
        return "Copy that. I'll continue to run the model effects and stability validation. Calculating.KS,PSI,Indicators such as case-boxing and stress testing."
    if stage == "word_conclusion_draft":
        return ""
    return "I'll continue with the next validation."


def agent_stage_label(
    stage: str,
    *,
    validation_workflow_version: int | None = None,
) -> str:
    if stage == "scan":
        return "Model material completeness validation"
    if stage == "reproducibility":
        if validation_workflow_version == 2:
            return "PMMLRating"
        return "Model Recurrence Validation"
    if stage == "metrics":
        return "Model Effects&Stability verification"
    if stage == "word_conclusion_draft":
        return "Draft report conclusions generated"
    return "Next Validation"


REPORT_DRAFT_FIELD_LABELS = {
    "TEXT:pressure_test_summary": "Summary of stress tests",
    "TEXT:pressure_impact_recommendation": "Pressure impact recommendations",
    "TEXT:final_validation_conclusion": "Final validation conclusion",
    "TEXT:model_overview": "Summary of the model",
    "TEXT:model_scope": "Scope of application",
    "TEXT:sample_audience": "Sample population",
    "TEXT:bad_sample_definition": "Bad sample definition",
    "TEXT:good_sample_definition": "Good sample definition",
    "TEXT:model_training_description": "Model training notes",
}
REPORT_DRAFT_FIELD_ORDER = tuple(REPORT_DRAFT_FIELD_LABELS)


def format_conclusion_values(values: dict[str, str]) -> str:
    ordered_keys = [key for key in REPORT_DRAFT_FIELD_ORDER if key in values]
    ordered_keys.extend(key for key in values if key not in REPORT_DRAFT_FIELD_LABELS)
    return "\n\n".join(
        f"{REPORT_DRAFT_FIELD_LABELS.get(key, key)}\n{value}"
        for key in ordered_keys
        if (value := values.get(key))
    )


def model_metadata(model_profile: dict) -> dict:
    return {
        "model_id": model_profile.get("model_id"),
        "display_name": model_profile.get("display_name"),
        "model_name": model_profile.get("model_name"),
    }


def add_streaming_agent_message(
    repo,
    task_id: str,
    *,
    stage: str,
    model_profile: dict,
) -> dict:
    return repo.add_agent_message(
        task_id,
        role="assistant",
        stage=stage,
        content="",
        metadata={**model_metadata(model_profile), "streaming": True},
    )


def add_and_stream_agent_message(
    repo,
    task_id: str,
    *,
    stage: str,
    model_profile: dict,
    producer: Callable[[Callable[[str], None]], tuple[str, dict]],
    raise_if_cancelled: Callable[[str], None],
) -> dict:
    message = add_streaming_agent_message(
        repo,
        task_id,
        stage=stage,
        model_profile=model_profile,
    )
    return stream_agent_message(
        repo,
        message["id"],
        task_id=task_id,
        model_profile=model_profile,
        producer=producer,
        raise_if_cancelled=raise_if_cancelled,
    )


_STREAM_FLUSH_INTERVAL_SECONDS = 0.5
_STREAM_FLUSH_CHARS = 512


def stream_agent_message(
    repo,
    message_id: str,
    *,
    task_id: str,
    model_profile: dict,
    producer: Callable[[Callable[[str], None]], tuple[str, dict]],
    raise_if_cancelled: Callable[[str], None],
) -> dict:
    parts: list[str] = []
    streaming_metadata = {**model_metadata(model_profile), "streaming": True}
    flush_state = {"last_flush": time.monotonic(), "chars_since_flush": 0}

    def on_delta(delta: str) -> None:
        if not delta:
            return
        # Cancellation must stay responsive on every delta; only the DB write is
        # throttled. The frontend already polls the full message on an interval,
        # so per-delta persistence has no consumer and only amplifies writes.
        raise_if_cancelled(task_id)
        parts.append(delta)
        flush_state["chars_since_flush"] += len(delta)
        now = time.monotonic()
        elapsed = now - flush_state["last_flush"]
        if (
            elapsed >= _STREAM_FLUSH_INTERVAL_SECONDS
            or flush_state["chars_since_flush"] >= _STREAM_FLUSH_CHARS
        ):
            repo.update_agent_message(
                message_id,
                content="".join(parts),
                metadata=streaming_metadata,
            )
            flush_state["last_flush"] = now
            flush_state["chars_since_flush"] = 0

    try:
        raise_if_cancelled(task_id)
        content, metadata = producer(on_delta)
        raise_if_cancelled(task_id)
        final_metadata = {
            **metadata,
            **model_metadata(model_profile),
            "streaming": False,
        }
        if parts:
            final_metadata["streamed"] = True
        raise_if_cancelled(task_id)
        return repo.update_agent_message(
            message_id,
            content=content,
            metadata=final_metadata,
        )
    except AgentValidationCancelled:
        cancelled_metadata = {
            **model_metadata(model_profile),
            "streaming": False,
            "cancelled": True,
        }
        if parts:
            cancelled_metadata["streamed"] = True
        repo.update_agent_message(
            message_id,
            content="".join(parts),
            metadata=cancelled_metadata,
        )
        raise
