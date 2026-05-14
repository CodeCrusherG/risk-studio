"""S3 Group Analysis Packagepack The entrance.(manifest module = marvis.packs.analysis.tools).

Every one.tool_* We're good.subprocess runner:Signature(inputs: dict, ctx) -> dict,
ctx Exposureworkspace/datasets_root/task_id/seed.Tool reading performance data set from the register as
pandas DataFrame,Call the kernel. Call the kernel.dataclass Result_jsonable Then back.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import hmac
import json
import math
from pathlib import Path
import re
import shutil
import tempfile

import pandas as pd

from marvis.artifacts import ArtifactUnitOfWork
from marvis.data.authenticated_snapshot import (
    AuthenticatedSnapshotError,
    read_authenticated_parquet_snapshot,
)
from marvis.repositories.modeling import ModelingRepository
from marvis.files import sha256_file
from marvis.packs.analysis.errors import AnalysisError, MissingBaselineError
from marvis.packs.analysis.flow import bucket_migration, flow_rate
from marvis.packs.analysis.loss import expected_loss_estimate
from marvis.packs.analysis.segment import ProfitParams, segment_profile
from marvis.packs.analysis.report import build_report, gate_summary_payload
from marvis.packs.analysis.trend import feature_csi_trend, score_stability_trend
from marvis.packs.modeling.experiment import ExperimentStore
from marvis.plugins.sdk import PackRuntime
from marvis.repositories.task_artifacts import TaskArtifactRepository


_PORTFOLIO_REPORT_ARTIFACT_KIND = "portfolio_report_xlsx"
_PORTFOLIO_REPORT_ARTIFACT_SCHEMA_VERSION = "portfolio-report-artifact.v1"
_PORTFOLIO_REPORT_ORIGIN_TOOL = "analysis.portfolio_report"
_PORTFOLIO_REPORT_PRODUCER_VERSION = "analysis.portfolio_report.v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class _Runtime(PackRuntime):
    def _extend(self, ctx) -> None:
        self.experiments = ExperimentStore(self.settings.db_path)
        self.modeling_repo = ModelingRepository(self.settings.db_path)
        self.task_artifacts = TaskArtifactRepository(self.settings.db_path)


def _runtime(ctx) -> _Runtime:
    return _Runtime(ctx)


def tool_flow_rate(inputs: dict, ctx) -> dict:
    runtime = _runtime(ctx)
    frame = _dataset_frame(
        runtime,
        str(inputs["dataset_id"]),
        expected_content_hash=str(inputs["expected_content_hash"]),
        task_id=str(ctx.task_id),
    )
    result = flow_rate(
        frame,
        id_col=str(inputs["id_col"]),
        snapshot_col=str(inputs["snapshot_col"]),
        bucket_col=str(inputs["bucket_col"]),
        states=[str(state) for state in inputs["states"]],
        balance_col=_optional_str(inputs.get("balance_col")),
        bad_states=_optional_str_list(inputs.get("bad_states")),
    )
    base_kind = "balance" if inputs.get("balance_col") else "count"
    return {
        "states": list(result.states),
        "to_states": list(result.to_states),
        "months": list(result.months),
        "matrix_by_month": [
            {
                "month": transition.month,
                "to_month": transition.to_month,
                "from_to_matrix": [[float(cell) for cell in row] for row in transition.from_to_matrix],
                "base": {state: float(value) for state, value in transition.base.items()},
                "base_kind": base_kind,
                "pair_count": transition.pair_count,
            }
            for transition in result.transitions
        ],
        "net_flows": [
            {
                "month": transition.month,
                "into_bad": float(transition.into_bad),
                "out_of_bad": float(transition.out_of_bad),
            }
            for transition in result.transitions
        ],
        "red_flags": _jsonable(result.red_flags),
    }


def tool_bucket_migration(inputs: dict, ctx) -> dict:
    runtime = _runtime(ctx)
    frame = _dataset_frame(
        runtime,
        str(inputs["dataset_id"]),
        expected_content_hash=str(inputs["expected_content_hash"]),
        task_id=str(ctx.task_id),
    )
    result = bucket_migration(
        frame,
        id_col=str(inputs["id_col"]),
        snapshot_col=str(inputs["snapshot_col"]),
        bucket_col=str(inputs["bucket_col"]),
        states=[str(state) for state in inputs["states"]],
        balance_col=_optional_str(inputs.get("balance_col")),
        window=_optional_str_list(inputs.get("window")),
        bad_states=_optional_str_list(inputs.get("bad_states")),
    )
    return {
        "states": list(result.states),
        "to_states": list(result.to_states),
        "window_months": list(result.window_months),
        "avg_matrix": [[float(cell) for cell in row] for row in result.avg_matrix],
        "worst_matrix": [[float(cell) for cell in row] for row in result.worst_matrix],
        "heat_table": _jsonable(result.heat_table),
        "red_flags": _jsonable(result.red_flags),
    }


def tool_segment_profile(inputs: dict, ctx) -> dict:
    runtime = _runtime(ctx)
    frame = _dataset_frame(
        runtime,
        str(inputs["dataset_id"]),
        expected_content_hash=str(inputs["expected_content_hash"]),
        task_id=str(ctx.task_id),
    )
    result = segment_profile(
        frame,
        segment_col=str(inputs["segment_col"]),
        target_col=_optional_str(inputs.get("target_col")),
        score_col=_optional_str(inputs.get("score_col")),
        approved_col=_optional_str(inputs.get("approved_col")),
        profit_params=_profit_params(inputs.get("profit_params")),
        ead_col=_optional_str(inputs.get("ead_col")),
        pd_col=_optional_str(inputs.get("pd_col")),
        top_k=int(inputs.get("top_k", 20)),
    )
    return {
        "segments": [_jsonable(asdict(row)) for row in result.segments],
        "concentration": _jsonable(asdict(result.concentration)),
        "concentration_basis": result.concentration_basis,
        "ead_concentration": (
            _jsonable(asdict(result.ead_concentration))
            if result.ead_concentration is not None
            else None
        ),
        "ead_concentration_basis": result.ead_concentration_basis,
        "red_flags": _jsonable(result.red_flags),
    }


def tool_expected_loss_estimate(inputs: dict, ctx) -> dict:
    runtime = _runtime(ctx)
    frame = _dataset_frame(
        runtime,
        str(inputs["dataset_id"]),
        expected_content_hash=str(inputs["expected_content_hash"]),
        task_id=str(ctx.task_id),
    )
    result = expected_loss_estimate(
        frame,
        id_col=str(inputs["id_col"]),
        snapshot_col=str(inputs["snapshot_col"]),
        bucket_col=str(inputs["bucket_col"]),
        states=[str(state) for state in inputs["states"]],
        balance_col=str(inputs["balance_col"]),
        loss_state=_optional_str(inputs.get("loss_state")),
        lgd=float(inputs.get("lgd", 0.6)),
        horizon_months=int(inputs.get("horizon_months", 12)),
        window=_optional_str_list(inputs.get("window")),
    )
    return {
        "loss_state": result.loss_state,
        "chain": [_jsonable(asdict(row)) for row in result.chain],
        "el_by_month": [_jsonable(asdict(row)) for row in result.el_by_month],
        "total_el": float(result.total_el),
        "assumptions": _jsonable(result.assumptions),
        "red_flags": _jsonable(result.red_flags),
    }


def tool_score_stability_trend(inputs: dict, ctx) -> dict:
    runtime = _runtime(ctx)
    baseline = _baseline(runtime, str(inputs["experiment_id"]))
    score_col = str(inputs.get("score_col") or "model_score")
    month_frames = _month_frames(
        runtime,
        inputs,
        score_col=score_col,
        task_id=str(ctx.task_id),
    )
    thresholds = _trend_thresholds(inputs.get("thresholds"))
    result = score_stability_trend(
        baseline,
        month_frames,
        score_col=score_col,
        warn=thresholds[0],
        fail=thresholds[1],
    )
    return _trend_output(result)


def tool_feature_csi_trend(inputs: dict, ctx) -> dict:
    runtime = _runtime(ctx)
    baseline = _baseline(runtime, str(inputs["experiment_id"]))
    score_col = str(inputs.get("score_col") or "model_score")
    month_frames = _month_frames(
        runtime,
        inputs,
        score_col=score_col,
        task_id=str(ctx.task_id),
    )
    thresholds = _trend_thresholds(inputs.get("thresholds"))
    result = feature_csi_trend(
        baseline,
        month_frames,
        feature_cols=_optional_str_list(inputs.get("feature_cols")),
        warn=thresholds[0],
        fail=thresholds[1],
    )
    return _trend_output(result)


def tool_portfolio_gate_summary(inputs: dict, ctx) -> dict:
    """Pure assembler: aggregate each injected step output's red_flags + key
    numbers into a gate payload (the red-flag list is the gate checklist)."""
    return gate_summary_payload(
        flow=_as_dict(inputs.get("flow")),
        migration=_as_dict(inputs.get("migration")),
        segment=_as_dict(inputs.get("segment")),
        trend=_as_dict(inputs.get("trend")),
        expected_loss=_as_dict(inputs.get("expected_loss")),
    )


def tool_portfolio_report(inputs: dict, ctx) -> dict:
    runtime = _runtime(ctx)
    task_id = str(ctx.task_id)
    out_dir = Path(runtime.settings.tasks_dir) / task_id / "portfolio"
    out_dir.mkdir(parents=True, exist_ok=True)
    input_hash = _canonical_payload_hash(inputs)
    with tempfile.TemporaryDirectory(prefix=".portfolio-report-", dir=out_dir) as temp_dir:
        rendered_path, sheets = build_report(
            project_meta=_as_dict(inputs.get("project_meta")) or {},
            flow=_as_dict(inputs.get("flow")),
            migration=_as_dict(inputs.get("migration")),
            segment=_as_dict(inputs.get("segment")),
            trend=_as_dict(inputs.get("trend")),
            expected_loss=_as_dict(inputs.get("expected_loss")),
            out_path=Path(temp_dir) / "portfolio_report.xlsx",
        )
        content_hash = sha256_file(rendered_path)
        uow = ArtifactUnitOfWork()
        artifact = uow.stage_file(
            out_dir,
            f"portfolio_report_{content_hash[:16]}.xlsx",
        )
        try:
            shutil.copyfile(rendered_path, artifact.path)
            if sha256_file(artifact.path) != content_hash:
                raise AnalysisError("The combination report's temporary content for Hashi verification failed.")
            provenance = {
                "schema_version": _PORTFOLIO_REPORT_ARTIFACT_SCHEMA_VERSION,
                "producer_version": _PORTFOLIO_REPORT_PRODUCER_VERSION,
                "task_id": task_id,
                "input_hash": input_hash,
                "sheets": list(sheets),
            }

            def _register_and_audit(conn):
                if sha256_file(artifact.final_path) != content_hash:
                    raise AnalysisError("The Hashi verification failed before the release of the combined report.")
                record = runtime.task_artifacts.register_on_connection(
                    conn,
                    task_id=task_id,
                    kind=_PORTFOLIO_REPORT_ARTIFACT_KIND,
                    path=str(artifact.final_path),
                    content_hash=content_hash,
                    origin_tool=_PORTFOLIO_REPORT_ORIGIN_TOOL,
                    provenance=provenance,
                )
                runtime.repo.write_audit_on_connection(
                    conn,
                    kind="analysis.portfolio.report",
                    target_ref=task_id,
                    outcome="succeeded",
                    detail={
                        "report_path": str(artifact.final_path),
                        "sheets": sheets,
                        "artifact_id": str(record["id"]),
                        "artifact_content_hash": content_hash,
                    },
                )
                return record

            record = uow.finalize_with_connection(
                runtime.task_artifacts.transaction,
                _register_and_audit,
            )
        except Exception:
            uow.rollback()
            raise
    return {
        "report_path": str(artifact.final_path),
        "sheets": sheets,
        "artifact_id": str(record["id"]),
        "artifact_content_hash": content_hash,
    }


# ---- helpers -----------------------------------------------------------------


def _dataset_frame(
    runtime: _Runtime,
    dataset_id: str,
    *,
    expected_content_hash: str | None,
    task_id: str,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    try:
        dataset = runtime.registry.get(dataset_id)
    except KeyError as exc:
        raise AnalysisError(f"The combination analysis data set does not exist:{dataset_id}.") from exc
    if str(dataset.task_id) != task_id:
        raise AnalysisError(f"The group analysis data set is not part of the current task:{dataset_id}.")

    registered_hash = str(dataset.content_hash or "")
    expected_hash = (
        registered_hash
        if expected_content_hash is None
        else str(expected_content_hash)
    )
    if (
        _SHA256_RE.fullmatch(expected_hash) is None
        or _SHA256_RE.fullmatch(registered_hash) is None
        or not hmac.compare_digest(registered_hash, expected_hash)
    ):
        raise AnalysisError("The combination analysis data binding changed after manual confirmation and implementation was refused.")

    source_path = str(dataset.source_path)
    try:
        frame = read_authenticated_parquet_snapshot(
            runtime.datasets_root / source_path,
            root=runtime.datasets_root,
            expected_sha256=expected_hash,
            columns=columns,
        )
    except AuthenticatedSnapshotError as exc:
        raise AnalysisError(
            "The data snapshot confirmed by the combination analysis was not validated through non-variable content and was refused execution."
        ) from exc
    try:
        current = runtime.registry.get(dataset_id)
    except KeyError as exc:
        raise AnalysisError(
            "The combination analysis data binding disappeared during the implementation period and the results of the analysis were rejected."
        ) from exc
    if (
        str(current.task_id) != task_id
        or str(current.source_path) != source_path
        or not isinstance(current.content_hash, str)
        or not hmac.compare_digest(current.content_hash, expected_hash)
    ):
        raise AnalysisError(
            "The combination analysis data binding changed during the implementation period and the results were rejected."
        )
    return frame


def _as_dict(value) -> dict | None:
    return dict(value) if isinstance(value, dict) else None


def _canonical_payload_hash(payload: dict) -> str:
    canonical = json.dumps(
        _jsonable(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

def _baseline(runtime: _Runtime, experiment_id: str) -> dict:
    experiment = runtime.experiments.get(experiment_id)
    if experiment.artifact_id is None:
        raise MissingBaselineError(
            experiment_id=experiment_id,
            reason=f"Experiment{experiment_id} No training products are available to read the baseline distribution snapshot.",
        )
    artifact = runtime.modeling_repo.get_model_artifact(experiment.artifact_id)
    if artifact is None or not artifact.baseline_distributions:
        raise MissingBaselineError(
            experiment_id=experiment_id,
            reason=(
                f"Experiment{experiment_id} The distribution of the product without training period is based on a snapshot of the distribution of the product (in the case of the production of the product)S1b (a) Previous training or non-two classification targets;"
                "There are no comparable benchmarks for stability trends, and please repeat the tests to capture the benchmarks or to switch to those with benchmarks."
            ),
        )
    return dict(artifact.baseline_distributions)


def _month_frames(
    runtime: _Runtime,
    inputs: dict,
    *,
    score_col: str,
    task_id: str,
) -> list[tuple[str, pd.DataFrame]]:
    """I'll break the trend in to the month.(month, frame) list.

    Support for two models:
      - ``dataset_ids``:Every one.id It's a scoring derivative. Use it.``month`` Enter or in Data
        ``month_col`` Insumption of month; this requires that each table be either the same or the same month (takes)month_col Number/The first one is the one I'm talking about.
        Or directly by parallel.``months`` list.
      - ``dataset_id`` + ``month_col``:Press single score sheetmonth_col Cutting into moon-by-moon tables.
    """
    dataset_ids = inputs.get("dataset_ids")
    dataset_id = _optional_str(inputs.get("dataset_id"))
    month_col = _optional_str(inputs.get("month_col"))
    if dataset_ids:
        months = inputs.get("months")
        frames: list[tuple[str, pd.DataFrame]] = []
        for index, raw_id in enumerate(dataset_ids):
            frame = _dataset_frame(
                runtime,
                str(raw_id),
                expected_content_hash=None,
                task_id=task_id,
            )
            if months and index < len(months):
                month = str(months[index])
            elif month_col and month_col in frame.columns:
                month = str(frame[month_col].iloc[0]) if len(frame) else str(index)
            else:
                month = str(index)
            frames.append((month, frame))
        return sorted(frames, key=lambda item: item[0])
    if dataset_id and month_col:
        frame = _dataset_frame(
            runtime,
            dataset_id,
            expected_content_hash=_optional_str(
                inputs.get("expected_content_hash")
            ),
            task_id=task_id,
        )
        if month_col not in frame.columns:
            raise AnalysisError(f"The single-table trend requires a monthly list`{month_col}` There.")
        out: list[tuple[str, pd.DataFrame]] = []
        for month, group in frame.groupby(frame[month_col].astype(str), sort=True):
            out.append((str(month), group))
        return out
    raise AnalysisError("Trends tool needsdataset_ids or(dataset_id + month_col).")


def _trend_thresholds(payload) -> tuple[float, float]:
    if isinstance(payload, dict):
        warn = payload.get("warn")
        fail = payload.get("fail")
        if warn is not None and fail is not None:
            return float(warn), float(fail)
    from marvis.packs.analysis.trend import _PSI_FAIL, _PSI_WARN

    return _PSI_WARN, _PSI_FAIL


def _trend_output(result) -> dict:
    return {
        "metric_name": result.metric_name,
        "trend": [_jsonable(asdict(point)) for point in result.trend],
        "per_feature_trend": [_jsonable(asdict(point)) for point in result.per_feature_trend],
        "red_flags": _jsonable(result.red_flags),
    }

def _profit_params(payload) -> ProfitParams | None:
    if not payload:
        return None
    data = dict(payload)
    return ProfitParams(
        annual_rate=float(data["annual_rate"]),
        funding_rate=float(data["funding_rate"]),
        lgd=float(data["lgd"]),
        operating_cost_per_loan=float(data["operating_cost_per_loan"]),
        term_months=int(data["term_months"]),
    )


def _optional_str(value) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _optional_str_list(value) -> list[str] | None:
    if not value:
        return None
    return [str(item) for item in value]


def _jsonable(value):
    if value is None:
        return None
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


__all__ = [
    "tool_bucket_migration",
    "tool_expected_loss_estimate",
    "tool_feature_csi_trend",
    "tool_flow_rate",
    "tool_portfolio_gate_summary",
    "tool_portfolio_report",
    "tool_score_stability_trend",
    "tool_segment_profile",
]
