"""Candidate, tree, Voting, Cross, and scorecard presenters."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import re
from typing import Any

from marvis.agent.presenters._shared import (
    format_number as _num,
    format_percent as _pct,
    format_value as _fmt,
)


def _scorecard_download_text(o: Mapping, *, fallback: str) -> str:
    artifacts = [
        item for item in (o.get("artifacts") or []) if isinstance(item, Mapping)
    ]
    artifact = next(
        (item for item in artifacts if item.get("download_url")),
        None,
    )
    if artifact is None:
        return ""
    label = str(artifact.get("filename") or artifact.get("kind") or fallback)
    return f"\n\n**GovernanceJSON**:[{label}]({artifact['download_url']})"


def _render_design_strategy_candidate(o: dict):
    evidence = o.get("design_evidence")
    evidence = evidence if isinstance(evidence, dict) else {}
    strategy_type = str(o.get("strategy_type") or evidence.get("strategy_type") or "")
    bands = [band for band in (evidence.get("bands") or []) if isinstance(band, dict)]
    objective = str(evidence.get("objective") or "")
    source_hash = str(o.get("source_dataset_content_hash") or "")
    text = (
        f"**{strategy_type or 'Non-approval'}Strategic candidate certainty generation**:"
        f"Total{len(bands)} A valid box, target.`{objective or '-'}`,"
        f"policy `{o.get('candidate_policy_version') or '-'}`."
        "This draft is subject to review and has not yet been accepted; manual confirmation is still required for its adoption."
    )
    if source_hash:
        text += f" Data evidence`{source_hash[:12]}…`."
    assumptions = [str(item) for item in (evidence.get("assumptions") or [])]
    if assumptions:
        text += "\n" + "\n".join(f"- caliber:{item}" for item in assumptions)
    red_flags = [
        flag for flag in (evidence.get("red_flags") or []) if isinstance(flag, dict)
    ]
    if red_flags:
        text += "\n" + "\n".join(
            f"- {str(flag.get('level') or 'warning').upper()}:"
            f"{flag.get('message') or flag.get('kind') or flag.get('code')}"
            for flag in red_flags
        )

    rows = []
    for band in bands:
        action = band.get("selected_action")
        action = action if isinstance(action, dict) else {}
        lower = "-∞" if band.get("lower") is None else _fmt(band.get("lower"))
        upper = "+∞" if band.get("upper") is None else _fmt(band.get("upper"))
        rows.append(
            [
                str(band.get("band_id") or ""),
                f"{lower} ~ {upper}",
                _fmt(band.get("count")),
                _pct(band.get("population_share")),
                _pct(band.get("bad_rate")),
                _fmt(band.get("risk_estimate")),
                str(action.get("type") or ""),
                _fmt(action.get("value")),
            ]
        )
    tables = []
    if rows:
        tables.append(
            {
                "title": "Specific Subboxes and Actions",
                "columns": [
                    "Box",
                    "Scope",
                    "Number of samples",
                    "Percentage",
                    "Observation of bad rate",
                    "Risk estimates",
                    "Actions",
                    "Value",
                ],
                "rows": rows,
            }
        )
    return text, tables


def _render_analyze_univariate_candidates(o: dict):
    rankings = [item for item in (o.get("rankings") or []) if isinstance(item, dict)]
    red_flags = [str(item) for item in (o.get("red_flags") or [])]
    artifacts = [item for item in (o.get("artifacts") or []) if isinstance(item, dict)]
    text = (
        f"**Single variable candidate analysis completed**:Analysed{o.get('feature_count', 0)} Fields,"
        f"Got it.{o.get('available_method_count', 0)} Fields Available/A combination of boxing methods."
        f"Proof of candidacy`{o.get('candidate_id', '')}` Only in"
        "`development / unvalidated`,It does not represent independent validation, adoption or online."
    )
    if rankings:
        top = rankings[0]
        text += (
            f" CurrentIV First place in the ranking is...`{top.get('feature', '')}` / "
            f"`{top.get('method', '')}`;The indicators are calculated by the Platform for certainty."
        )
    if o.get("nan_labels_dropped"):
        text += (
            f"\n- - It's off the grid as you confirm.{o['nan_labels_dropped']} (a) Empty tags;"
            "The evidence presented in the candidacy recorded this calibre."
        )
    if any(flag.startswith("loan_amount_metrics_unavailable") for flag in red_flags):
        text += "\n- No loan value list has been configured; if available, I can supplement the value calibration impact analysis."
    if any(flag.startswith("overdue_amount_metrics_unavailable") for flag in red_flags):
        text += "\n- The list of overdue amounts has not yet been configured; if available, I can supplement the analysis of the overdue amounts."
    links = [
        f"[{str(item.get('filename') or item.get('kind') or 'Download')}]"
        f"({str(item.get('download_url'))})"
        for item in artifacts
        if item.get("download_url")
    ]
    if links:
        text += "\n\n**Candidate reports**:" + ";".join(links)

    tables = []
    if rankings:
        tables.append(
            {
                "title": "Single variable candidate ranking (first 20)",
                "columns": ["Characteristics", "Boxing method", "IV", "KS", "AUC"],
                "rows": [
                    [
                        str(item.get("feature") or ""),
                        str(item.get("method") or ""),
                        _num(item.get("iv")),
                        _num(item.get("ks")),
                        _num(item.get("auc")),
                    ]
                    for item in rankings[:20]
                ],
            }
        )
    material_flags = [
        flag
        for flag in red_flags
        if not flag.startswith("loan_amount_metrics_unavailable")
        and not flag.startswith("overdue_amount_metrics_unavailable")
    ]
    if material_flags:
        tables.append(
            {
                "title": "Candidate Analysis Hint",
                "columns": ["Hint"],
                "rows": [[flag] for flag in material_flags[:30]],
            }
        )
    return text, tables


def _automatic_tree_condition_text(value: object) -> str:
    if value in (None, {}, []):
        return "All samples"
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError):
            return "n/a"
    return str(value)


def _render_build_automatic_tree_candidate(o: dict):
    """Render canonical leaves without deriving a ranking or recommendation."""

    summary = o.get("summary") if isinstance(o.get("summary"), dict) else {}
    leaves = [item for item in (o.get("leaf_index") or []) if isinstance(item, dict)]
    artifacts = [item for item in (o.get("artifacts") or []) if isinstance(item, dict)]
    red_flags = [item for item in (o.get("red_flags") or []) if isinstance(item, dict)]
    gaps = [
        item
        for item in (o.get("report_info_gaps") or [])
        if isinstance(item, dict) and item.get("blocking") is False
    ]
    lifecycle = " / ".join(
        str(summary.get(field) or "unknown")
        for field in ("candidate_stage", "observation_stage", "validation_status")
    )
    text = (
        f"**Auto-tree candidate complete**:Assets`{summary.get('asset_id', '')}`,"
        f"asset hash `{summary.get('asset_hash', '')}`,"
        f"tree result hash `{summary.get('tree_result_hash', '')}`."
        f"Current Status`{lifecycle}`;Indicators, conditions and foliage sequences are derived from the Platform ' s certainty results.\n"
        "**Leaves have not been selected, pools have not been put in place, actions have not been configured and have not been adopted or deployed.**"
    )

    links = [
        f"[{str(item.get('filename') or item.get('kind') or 'Download')}]"
        f"({str(item.get('download_url'))})"
        for item in artifacts
        if item.get("download_url")
    ]
    if links:
        text += "\n\n**Auto-tree Delivery**:" + ";".join(links)

    if gaps:
        labels = {
            "sample_weight": "Sample weights",
            "loan_amount": "Amount released",
            "overdue_amount": "Overdue amounts",
        }
        missing = ",".join(
            labels.get(
                str(item.get("context") or ""),
                str(item.get("context") or item.get("code") or "Additional information"),
            )
            for item in gaps
        )
        text += (
            f"\n\nThe report contains additional information that is currently lacking:{missing}.(b) If available;"
            "There is no jump, and the final report is empty. This does not block the continuation of the strategy."
        )

    if red_flags:
        text += (
            "\n\n**Red flag for risk direction**:There are split nodes that are not in line with the desired risk orientation."
            "`directions` (a) In the current automatic tree, it is a diagnostic expectation, not a binding partition constraint;"
            "The candidate remainsdevelopment / unvalidated,The choice of leaves must be reviewed on a case-by-case basis."
        )

    rows = []
    for leaf in leaves:
        basis = (
            leaf.get("metric_basis")
            if isinstance(leaf.get("metric_basis"), dict)
            else {}
        )
        primary = str(basis.get("primary") or "unweighted")
        measurements = (
            leaf.get("measurements")
            if isinstance(leaf.get("measurements"), dict)
            else {}
        )
        metrics = (
            measurements.get(primary)
            if isinstance(measurements.get(primary), dict)
            else {}
        )
        rows.append(
            [
                str(leaf.get("leaf_id") or ""),
                str(leaf.get("rule_id") or ""),
                primary,
                _num(metrics.get("total")),
                _pct(metrics.get("share")),
                _pct(metrics.get("bad_rate")),
                _pct(metrics.get("bad_capture")),
                _num(metrics.get("lift")),
                _automatic_tree_condition_text(leaf.get("condition")),
            ]
        )
    tables = []
    if red_flags:
        direction_labels = {
            "increasing": "Incremental",
            "decreasing": "Decline",
        }
        tables.append(
            {
                "title": "Auto tree risk direction red flag",
                "columns": ["Type", "Node ID", "Characteristics", "Expected risk orientation"],
                "rows": [
                    [
                        str(flag.get("code") or ""),
                        str(flag.get("node_id") or ""),
                        str(flag.get("feature") or ""),
                        direction_labels.get(
                            str(flag.get("expected_direction") or ""),
                            str(flag.get("expected_direction") or ""),
                        ),
                    ]
                    for flag in red_flags
                ],
            }
        )
    if rows:
        tables.append(
            {
                "title": "Automatic whole leaf node list",
                "columns": [
                    "Leaf ID",
                    "Rule ID",
                    "Indicator calibration",
                    "Number of samples",
                    "Samples as a percentage",
                    "Bad rate",
                    "Bad sample capture rate",
                    "Lift",
                    "Conditions",
                ],
                "rows": rows,
            }
        )
    return text, tables


def _render_materialize_automatic_tree_leaf_fragment(o: dict):
    artifacts = [item for item in (o.get("artifacts") or []) if isinstance(item, dict)]
    artifact = next(
        (
            item
            for item in artifacts
            if item.get("kind") == "strategy_automatic_tree_leaf_fragment_json"
            and item.get("format") == "json"
            and item.get("download_url")
        ),
        None,
    )
    text = (
        "**Automatic foliage reference is physically modified.**"
        "The product is only`pointer-only` Quoted, no rules, indicators or actions copied;"
        "Unpositioned, unconfigured, unapproved, undeployed."
    )
    if artifact is not None:
        label = str(
            artifact.get("filename")
            or artifact.get("kind")
            or "automatic-tree-leaf-selection.json"
        )
        text += f"\n\n**Leaf Node ReferenceJSON**:[{label}]({artifact['download_url']})"

    reason = o.get("selection_reason")
    reason_text = str(reason) if reason is not None else "Not provided"
    artifact_id = str(artifact.get("artifact_id") or "") if artifact else ""
    artifact_content_hash = str(artifact.get("content_hash") or "") if artifact else ""
    rows = [
        ["Selection ID", str(o.get("selection_id") or "")],
        ["Selection Hash", str(o.get("selection_hash") or "")],
        ["Tree Asset ID", str(o.get("tree_asset_id") or "")],
        ["Tree Asset Hash", str(o.get("tree_asset_hash") or "")],
        ["Tree Result Hash", str(o.get("tree_result_hash") or "")],
        ["Leaf ID", str(o.get("leaf_id") or "")],
        ["Fragment ID", str(o.get("fragment_id") or "")],
        ["Fragment Hash", str(o.get("fragment_hash") or "")],
        ["Rule ID", str(o.get("rule_id") or "")],
        ["Effect ID", str(o.get("effect_id") or "")],
        ["Artifact ID", artifact_id],
        ["Artifact Content Hash", artifact_content_hash],
        ["Selection Reason", reason_text],
    ]
    return text, [
        {
            "title": "Auto-leaf Exact Reference",
            "columns": ["Fields", "Value"],
            "rows": rows,
        }
    ]


def _render_materialize_interactive_tree_frontier_selection(o: dict):
    """Render one pointer-only frontier selection without implying admission."""

    artifacts = [item for item in (o.get("artifacts") or []) if isinstance(item, dict)]
    artifact = next(
        (
            item
            for item in artifacts
            if item.get("kind") == "strategy_interactive_tree_frontier_selection_json"
            and item.get("format") == "json"
            and item.get("download_url")
        ),
        None,
    )
    text = (
        "**The precise node references for the interactive decision tree are physically modified.**"
        "The`pointer-only` The product is bound to a precise revision and one of the front-line nodes."
        "No copying conditions, indicators or actions;"
        "Unpositioned, unconfigured, unapproved, undeployed."
    )
    if artifact is not None:
        label = str(
            artifact.get("filename")
            or artifact.get("kind")
            or "interactive-tree-frontier-selection.json"
        )
        text += f"\n\n**Frontline Node ReferenceJSON**:[{label}]({artifact['download_url']})"

    reason = o.get("selection_reason")
    artifact_id = str(artifact.get("artifact_id") or "") if artifact else ""
    artifact_content_hash = str(artifact.get("content_hash") or "") if artifact else ""
    rows = [
        ["Selection ID", str(o.get("selection_id") or "")],
        ["Selection Hash", str(o.get("selection_hash") or "")],
        ["Revision ID", str(o.get("revision_id") or "")],
        ["Semantic Tree ID", str(o.get("semantic_tree_id") or "")],
        ["Tree Hash", str(o.get("tree_hash") or "")],
        ["Source Node ID", str(o.get("source_node_id") or "")],
        ["Leaf ID", str(o.get("leaf_id") or "")],
        ["Fragment ID", str(o.get("fragment_id") or "")],
        ["Fragment Hash", str(o.get("fragment_hash") or "")],
        ["Rule ID", str(o.get("rule_id") or "")],
        ["Effect ID", str(o.get("effect_id") or "")],
        ["Artifact ID", artifact_id],
        ["Artifact Content Hash", artifact_content_hash],
        ["Selection Reason", str(reason) if reason is not None else "Not provided"],
    ]
    return text, [
        {
            "title": "Interactive decision tree node reference",
            "columns": ["Fields", "Value"],
            "rows": rows,
        }
    ]


def _render_materialize_interactive_tree_frontier_group_selection(o: dict):
    """Render one pointer-only frontier OR group without implying admission."""

    artifacts = [item for item in (o.get("artifacts") or []) if isinstance(item, dict)]
    artifact = next(
        (
            item
            for item in artifacts
            if item.get("kind")
            == "strategy_interactive_tree_frontier_group_selection_json"
            and item.get("format") == "json"
            and item.get("download_url")
        ),
        None,
    )
    source_node_ids = [
        str(item)
        for item in (o.get("source_node_ids") or [])
        if isinstance(item, str) and item
    ]
    member_count = o.get("member_count")
    text = (
        "**Frontline of interactive decision treeOR Group references are physically developed.**"
        f"The`pointer-only` In the revised version of the product binding{member_count} Frontline"
        "Node, semantic is hit by either member (OR),No copying conditions, indicators or actions;"
        "Unpositioned, unconfigured, unapplied, unapplied, unapplied, undeployed."
    )
    if artifact is not None:
        label = str(
            artifact.get("filename")
            or artifact.get("kind")
            or "interactive-tree-frontier-group-selection.json"
        )
        text += f"\n\n**FrontOR Group ReferenceJSON**:[{label}]({artifact['download_url']})"

    reason = o.get("selection_reason")
    artifact_id = str(artifact.get("artifact_id") or "") if artifact else ""
    artifact_content_hash = str(artifact.get("content_hash") or "") if artifact else ""
    rows = [
        ["Selection ID", str(o.get("selection_id") or "")],
        ["Selection Hash", str(o.get("selection_hash") or "")],
        ["Group ID", str(o.get("group_id") or "")],
        ["Revision ID", str(o.get("revision_id") or "")],
        ["Semantic Tree ID", str(o.get("semantic_tree_id") or "")],
        ["Tree Hash", str(o.get("tree_hash") or "")],
        ["Member Count", str(member_count if member_count is not None else "")],
        ["Source Node IDs", ",".join(source_node_ids)],
        ["Fragment ID", str(o.get("fragment_id") or "")],
        ["Rule ID", str(o.get("rule_id") or "")],
        ["Effect ID", str(o.get("effect_id") or "")],
        ["Artifact ID", artifact_id],
        ["Artifact Content Hash", artifact_content_hash],
        ["Selection Reason", str(reason) if reason is not None else "Not provided"],
    ]
    return text, [
        {
            "title": "Frontline of interactive decision treeOR Group Reference",
            "columns": ["Fields", "Value"],
            "rows": rows,
        }
    ]


def _automatic_tree_apply_integrity_failure() -> tuple[str, list[dict]]:
    return (
        "**Failed to verify full-scale result return**:Planning cachesource tree,"
        "Discrepancies, lines orevidence The binding is inconsistent and the results are stopped."
        "Download interfaces will still be pressedTaskArtifact Registrationhash Check the product.",
        [],
    )


def _validate_automatic_tree_apply_renderer_output(o: object) -> dict:
    """Validate the exact Tool envelope before rendering any cached value."""

    import re

    if not isinstance(o, dict):
        raise ValueError("automatic-tree apply output must be an object")

    def exact(value: object, fields: set[str], name: str) -> dict:
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError(f"{name} fields are invalid")
        return value

    def text(value: object, name: str) -> str:
        if (
            not isinstance(value, str)
            or not value
            or "\x00" in value
            or "\n" in value
            or "\r" in value
        ):
            raise ValueError(f"{name} is invalid")
        return value

    hash_pattern = re.compile(r"^[0-9a-f]{64}$")
    asset_pattern = re.compile(r"^candidate-asset-[0-9a-f]{32}$")
    run_pattern = re.compile(r"^atar_[0-9a-f]{32}$")
    column_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

    def digest(value: object, name: str) -> str:
        normalized = text(value, name)
        if hash_pattern.fullmatch(normalized) is None:
            raise ValueError(f"{name} is invalid")
        return normalized

    def count(value: object, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} is invalid")
        return value

    top = exact(
        o,
        {
            "schema_version",
            "run_id",
            "input_hash",
            "cached",
            "activated",
            "source",
            "result",
            "columns",
            "leaf_distribution",
            "workspace",
            "evidence",
        },
        "output",
    )
    if top["schema_version"] != "strategy.apply-automatic-tree-tool.v1":
        raise ValueError("schema version is invalid")
    if run_pattern.fullmatch(text(top["run_id"], "run_id")) is None:
        raise ValueError("run_id is invalid")
    digest(top["input_hash"], "input_hash")
    if type(top["cached"]) is not bool or type(top["activated"]) is not bool:
        raise ValueError("apply flags are invalid")

    source = exact(
        top["source"],
        {
            "tree_artifact_id",
            "tree_artifact_content_hash",
            "asset_id",
            "asset_hash",
            "tree_result_hash",
            "dataset_id",
            "dataset_content_hash",
            "row_count",
        },
        "source",
    )
    text(source["tree_artifact_id"], "source.tree_artifact_id")
    digest(source["tree_artifact_content_hash"], "source.tree_artifact_content_hash")
    if asset_pattern.fullmatch(text(source["asset_id"], "source.asset_id")) is None:
        raise ValueError("source.asset_id is invalid")
    digest(source["asset_hash"], "source.asset_hash")
    digest(source["tree_result_hash"], "source.tree_result_hash")
    text(source["dataset_id"], "source.dataset_id")
    digest(source["dataset_content_hash"], "source.dataset_content_hash")
    source_rows = count(source["row_count"], "source.row_count")

    result = exact(
        top["result"],
        {"dataset_id", "dataset_content_hash", "row_count", "result_hash"},
        "result",
    )
    text(result["dataset_id"], "result.dataset_id")
    digest(result["dataset_content_hash"], "result.dataset_content_hash")
    digest(result["result_hash"], "result.result_hash")
    if (
        count(result["row_count"], "result.row_count") != source_rows
        or result["dataset_id"] == source["dataset_id"]
    ):
        raise ValueError("derived dataset identity is invalid")

    columns = exact(top["columns"], {"leaf_id", "rule_id"}, "columns")
    for field in ("leaf_id", "rule_id"):
        if column_pattern.fullmatch(text(columns[field], f"columns.{field}")) is None:
            raise ValueError(f"columns.{field} is invalid")
    if columns["leaf_id"].casefold() == columns["rule_id"].casefold():
        raise ValueError("output columns are not distinct")

    distribution = top["leaf_distribution"]
    if not isinstance(distribution, list) or not distribution:
        raise ValueError("leaf_distribution is invalid")
    leaf_ids: set[str] = set()
    rule_ids: set[str] = set()
    distributed_rows = 0
    for index, item in enumerate(distribution):
        row = exact(item, {"leaf_id", "rule_id", "row_count"}, f"leaf[{index}]")
        leaf_id = text(row["leaf_id"], f"leaf[{index}].leaf_id")
        rule_id = text(row["rule_id"], f"leaf[{index}].rule_id")
        if leaf_id in leaf_ids or rule_id in rule_ids:
            raise ValueError("leaf distribution identities are not unique")
        leaf_ids.add(leaf_id)
        rule_ids.add(rule_id)
        distributed_rows += count(row["row_count"], f"leaf[{index}].row_count")
    if distributed_rows != source_rows:
        raise ValueError("leaf distribution does not conserve rows")

    workspace = exact(
        top["workspace"],
        {
            "source_revision",
            "source_analysis_generation",
            "source_semantic_mapping_hash",
            "result_revision",
            "result_analysis_generation",
            "result_semantic_mapping_hash",
            "active_dataset_id",
        },
        "workspace",
    )
    count(workspace["source_revision"], "workspace.source_revision")
    count(
        workspace["source_analysis_generation"],
        "workspace.source_analysis_generation",
    )
    digest(
        workspace["source_semantic_mapping_hash"],
        "workspace.source_semantic_mapping_hash",
    )
    digest(
        workspace["result_semantic_mapping_hash"],
        "workspace.result_semantic_mapping_hash",
    )
    text(workspace["active_dataset_id"], "workspace.active_dataset_id")
    if top["activated"]:
        count(workspace["result_revision"], "workspace.result_revision")
        count(
            workspace["result_analysis_generation"],
            "workspace.result_analysis_generation",
        )
        if workspace["active_dataset_id"] != result["dataset_id"]:
            raise ValueError("activated workspace binding is invalid")
    elif (
        workspace["result_revision"] is not None
        or workspace["result_analysis_generation"] is not None
        or workspace["active_dataset_id"] != source["dataset_id"]
    ):
        raise ValueError("inactive workspace binding is invalid")

    evidence = exact(
        top["evidence"],
        {"artifact_id", "content_hash", "download_url"},
        "evidence",
    )
    text(evidence["artifact_id"], "evidence.artifact_id")
    digest(evidence["content_hash"], "evidence.content_hash")
    download_url = text(evidence["download_url"], "evidence.download_url")
    if not (
        download_url.startswith("/api/tasks/")
        and download_url.endswith("/download")
        and "/task-artifacts/" in download_url
    ):
        raise ValueError("evidence.download_url is invalid")
    return top


def _render_apply_automatic_tree(o: dict):
    try:
        o = _validate_automatic_tree_apply_renderer_output(o)
    except (TypeError, ValueError, RecursionError):
        return _automatic_tree_apply_integrity_failure()

    source = o["source"]
    result = o["result"]
    columns = o["columns"]
    evidence = o["evidence"]
    workspace_note = (
        f"Currentworkspace Switched to derivative dataset`{result['dataset_id']}`."
        if o["activated"]
        else (f"Currentworkspace Uninterchanged, still pointing to original data set`{source['dataset_id']}`.")
    )
    text = (
        f"**Auto-tree Full Volume Relay Complete**:Full tree asset`{source['asset_id']}`(source "
        f"artifact `{source['tree_artifact_id']}`)Qualified application to original dataset"
        f"`{source['dataset_id']}`,Generate non-variable data sets`{result['dataset_id']}`;"
        f"Reservations**{source['row_count']}** Line. The leaf node output column`{columns['leaf_id']}`,"
        f"Rule Output Column`{columns['rule_id']}`.{workspace_note}\n"
        "The border is as follows:**development / unvalidated**;It's reversible data."
        "**Not in pool, not accepted, not deployed**,Nor did it generate business actions.\n\n"
        f"**Write back the evidence.**:[{evidence['artifact_id']}]({evidence['download_url']})"
    )
    identity_rows = [
        ["Source Tree Asset", source["asset_id"]],
        ["Source Tree Artifact", source["tree_artifact_id"]],
        ["Source Dataset", source["dataset_id"]],
        ["Result Dataset", result["dataset_id"]],
        ["Leaf ID Column", columns["leaf_id"]],
        ["Rule ID Column", columns["rule_id"]],
        ["Evidence Artifact", evidence["artifact_id"]],
    ]
    distribution_rows = [
        [item["leaf_id"], item["rule_id"], str(item["row_count"])]
        for item in o["leaf_distribution"]
    ]
    return text, [
        {
            "title": "Auto-tree full ID",
            "columns": ["Fields", "Value"],
            "rows": identity_rows,
        },
        {
            "title": "Autoleaf node write back distribution",
            "columns": ["Leaf ID", "Rule ID", "Lines"],
            "rows": distribution_rows,
        },
    ]


def _render_refine_univariate_candidate(o: dict):
    rule = o.get("rule") if isinstance(o.get("rule"), dict) else {}
    effect = o.get("effect") if isinstance(o.get("effect"), dict) else {}
    artifacts = [item for item in (o.get("artifacts") or []) if isinstance(item, dict)]
    text = (
        f"**Candidate selection and merger completed**:`{o.get('feature', '')}` / "
        f"`{o.get('method', '')}` Generated candidate assets`{o.get('asset_id', '')}`."
        "The asset is only in the`development / unvalidated`,It does not represent independent validation, adoption or online."
    )
    if o.get("parent_candidate_id"):
        text += f" The source's candidate is`{o['parent_candidate_id']}`."
    rule_id = rule.get("rule_id")
    effect_id = o.get("effect_id") or effect.get("effect_id")
    if rule_id or effect_id:
        text += (
            f" RuleID `{rule_id or '-'}`,EffectsID `{effect_id or '-'}`;"
            "Conditions and indicators are re-emplaced and calculated by the Platform from the definitive end of the bound sample."
        )
    links = [
        f"[{str(item.get('filename') or item.get('kind') or 'Download')}]"
        f"({str(item.get('download_url'))})"
        for item in artifacts
        if item.get("download_url")
    ]
    if links:
        text += "\n\n**Candidate assets**:" + ";".join(links)
    return text, []


def _render_build_voting_candidate(o: dict):
    """Render one governed n-of-k candidate without implying adoption."""

    selected_entries = [
        item for item in (o.get("selected_entries") or []) if isinstance(item, dict)
    ]
    distribution = [
        item for item in (o.get("hit_distribution") or []) if isinstance(item, dict)
    ]
    artifacts = [item for item in (o.get("artifacts") or []) if isinstance(item, dict)]
    observations = [
        item for item in (o.get("metric_observations") or []) if isinstance(item, dict)
    ]
    effect = o.get("effect") if isinstance(o.get("effect"), dict) else {}
    revision = o.get("pool_revision", o.get("revision"))
    snapshot_hash = str(o.get("pool_snapshot_hash") or o.get("snapshot_hash") or "")
    n = o.get("n")
    k = o.get("k")
    lifecycle = " / ".join(
        str(o.get(field) or "unknown")
        for field in ("candidate_stage", "observation_stage", "validation_status")
    )
    dataset_id = str(o.get("dataset_id") or "n/a")
    target_col = str(o.get("target_col") or "n/a")
    population_count = o.get("population_count", effect.get("population_count"))
    labeled_count = o.get("labeled_count", effect.get("labeled_count"))
    nan_labels_dropped = o.get("nan_labels_dropped")
    drop_nan_labels = o.get("drop_nan_labels")
    population_text = "n/a" if population_count is None else _fmt(population_count)
    labeled_text = "n/a" if labeled_count is None else _fmt(labeled_count)
    dropped_text = "n/a" if nan_labels_dropped is None else _fmt(nan_labels_dropped)
    drop_text = (
        "true"
        if drop_nan_labels is True
        else "false"
        if drop_nan_labels is False
        else "n/a"
    )
    text = (
        f"**Voting n-of-k Strategy candidate complete.**:Assets`{o.get('asset_id', '')}`,"
        f"asset hash `{o.get('asset_hash', '')}`;Grouping as**{n}-of-{k}**."
        f"SourcePool `{o.get('pool_id', '')}` revision {revision},"
        f"snapshot hash `{snapshot_hash}`;Status`{lifecycle}`.\n"
        "**This step is the only one that generates candidates and is not in the pool; it is not applied back, not accepted, not deployed.**"
    )
    text += (
        "\n\n**Blank sample caliber**:"
        f"dataset `{dataset_id}`,target `{target_col}`;"
        f"population {population_text},labeled {labeled_text};"
        f"drop_nan_labels `{drop_text}`,nan_labels_dropped {dropped_text}."
    )
    text += (
        "\n\n**Blank sample observations (not independently validated)**:"
        "The following values are calculated by the Platform for certainty on the above-mentioned binding samples and do not represent independent validation or upline effects."
        f"Hit rate{_pct(effect.get('matched_rate'))},"
        f"Hit rate.{_pct(effect.get('matched_bad_rate'))},"
        f"Bad sample capture rate{_pct(effect.get('bad_capture_rate'))},"
        f"Lift {_num(effect.get('lift'))}."
    )

    links = [
        f"[{str(item.get('filename') or item.get('kind') or 'Download')}]"
        f"({str(item.get('download_url'))})"
        for item in artifacts
        if item.get("download_url")
    ]
    if links:
        text += "\n\n**Voting Candidate assets**:" + ";".join(links)

    tables = []
    if selected_entries:
        tables.append(
            {
                "title": "Voting Rule of membership (byPool position)",
                "columns": ["Pool position", "rule_id", "entry_id"],
                "rows": [
                    [
                        str(item.get("pool_position") or 0),
                        str(item.get("rule_id") or ""),
                        str(item.get("entry_id") or ""),
                    ]
                    for item in selected_entries
                ],
            }
        )
    if distribution:
        tables.append(
            {
                "title": "Voting Hit distribution",
                "columns": [
                    "Number of hits",
                    "Number of samples",
                    "Samples as a percentage",
                    "Number of bad samples",
                    "Bad rate",
                    "Lift",
                ],
                "rows": [
                    [
                        str(item.get("hit_count") or 0),
                        _fmt(item.get("count")),
                        _pct(item.get("share")),
                        _fmt(item.get("bad_count")),
                        _pct(item.get("bad_rate")),
                        _num(item.get("lift")),
                    ]
                    for item in distribution
                ],
            }
        )
    observation_by_identity = {
        (str(item.get("metric_name") or ""), str(item.get("dimension") or "")): item
        for item in observations
    }
    amount_rows = []
    for dimension, dimension_label in (
        ("loan_amount", "Amount released"),
        ("overdue_amount", "Overdue amounts"),
    ):
        for metric_name, metric_label in (
            ("voting.hit_share", "Voting The amount hit."),
            ("voting.bad_capture_rate", "Percentage of bad sample captures"),
        ):
            observation = observation_by_identity.get((metric_name, dimension))
            if observation is None:
                continue
            status = str(observation.get("status") or "unavailable")
            value = _pct(observation.get("value")) if status == "observed" else "n/a"
            amount_rows.append([dimension_label, metric_label, status, value])
    if amount_rows:
        text += "\n\n**Observation of monetary dimensions**:The status and values of the observation of the monetary dimension are shown in the table below."
        tables.append(
            {
                "title": "Voting Critical observations of monetary dimensions",
                "columns": ["Amount dimension", "Indicators", "Status", "Observations"],
                "rows": amount_rows,
            }
        )
    else:
        text += "\n\n**Observation of monetary dimensions**:This output does not provide a measurable quantitative dimension observation."
    return text, tables


def _render_build_voting_candidate_from_search(
    o: dict,
    *,
    trusted_inputs: Mapping[str, Any] | None,
):
    """Project an exact search pointer without implying automatic selection."""

    validated = _validated_build_voting_candidate_from_search_output(
        o,
        trusted_inputs=trusted_inputs,
    )
    if validated is None:
        return (
            "**Voting Failed to verify the integrity of the search result**:The platform will not display unrestricted"
            " pointer,Search sources, constraints or candidates for the verification of candidate structures and life cycle consistency"
            "fact;please re-execut this builder step.",
            [],
        )
    source, candidate = validated

    search_id = source["search_id"]
    combo_id = source["combo_id"]
    eligibility = source.get("eligible")
    prefix = (
        f"**Voting Search for group precise build source**:User-specific roll callsearch "
        f"`{search_id}` Mediumcombo `{combo_id}`."
    )
    if eligibility is True:
        prefix += (
            " The group meets the eligibility limits for search; this is only for userspointer The evidence indicates that the police are not responsible for the attack."
            "This does not represent an automatic selection or recommendation by the platform."
        )
    elif eligibility is False:
        failures = [
            item
            for item in (source.get("constraint_failures") or [])
            if isinstance(item, dict)
        ]
        rendered_failures = ";".join(
            f"{item.get('metric', '-')}"
            f" {item.get('operator', '-')} {_num(item.get('threshold'))}"
            f"(actual {_num(item.get('actual'))})"
            for item in failures
        )
        prefix += (
            " **Warning: The combination does not meet the eligibility constraints for search.**"
            + (f" Failed to limit:{rendered_failures}." if rendered_failures else "")
            + " Still building because the user precisely called it.combo,Not recommended by the Platform."
        )
    else:
        prefix += " The eligibility status at the time of the search is not available; the platform will not claim that the combination is restrained or recommended on this basis."

    candidate_text, tables = _render_build_voting_candidate(candidate)
    return f"{prefix}\n\n{candidate_text}", tables


def _validated_build_voting_candidate_from_search_output(
    output: object,
    *,
    trusted_inputs: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Validate the wrapper before projecting any search-selection claim."""

    top_fields = {
        "schema_version",
        "source_search_selection",
        "voting_candidate",
        "not_mutated_pool",
        "not_admitted",
        "not_applied",
        "not_adopted",
        "not_deployed",
    }
    source_fields = {
        "search_id",
        "combo_id",
        "strategy_type",
        "rank",
        "member_rule_ids",
        "n",
        "eligible",
        "constraint_failures",
    }
    candidate_fields = {
        "schema_version",
        "asset_id",
        "asset_hash",
        "candidate_id",
        "evidence_hash",
        "rule_id",
        "rule_hash",
        "fragment_id",
        "fragment_hash",
        "effect_id",
        "effect_hash",
        "pool_id",
        "revision",
        "snapshot_hash",
        "selected_entries",
        "n",
        "k",
        "dataset_id",
        "target_col",
        "sample_design_ref",
        "drop_nan_labels",
        "nan_labels_dropped",
        "population_count",
        "labeled_count",
        "candidate_stage",
        "observation_stage",
        "validation_status",
        "effect",
        "metrics",
        "hit_distribution",
        "metric_observations",
        "not_admitted",
        "not_applied",
        "not_adopted",
        "not_deployed",
        "artifacts",
    }
    hash_fields = {
        "asset_hash",
        "evidence_hash",
        "rule_hash",
        "fragment_hash",
        "effect_hash",
        "snapshot_hash",
    }
    id_patterns = {
        "asset_id": r"candidate-asset-[0-9a-f]{32}",
        "candidate_id": r"candidate-[0-9a-f]{32}",
        "rule_id": r"candidate-rule-[0-9a-f]{32}",
        "fragment_id": r"candidate-fragment-[0-9a-f]{32}",
        "effect_id": r"candidate-effect-[0-9a-f]{32}",
    }
    try:
        if not isinstance(output, dict) or set(output) != top_fields:
            return None
        if output["schema_version"] != (
            "strategy.build-voting-candidate-from-search-tool.v1"
        ):
            return None
        if any(
            output[field] is not True
            for field in (
                "not_mutated_pool",
                "not_admitted",
                "not_applied",
                "not_adopted",
                "not_deployed",
            )
        ):
            return None
        source = output["source_search_selection"]
        candidate = output["voting_candidate"]
        if (
            not isinstance(trusted_inputs, Mapping)
            or set(trusted_inputs)
            not in (
                {"search_id", "combo_id"},
                {"search_id", "combo_id", "strategy_type"},
            )
            or not isinstance(source, dict)
            or set(source) != source_fields
            or not isinstance(candidate, dict)
            or set(candidate) != candidate_fields
        ):
            return None
        if (
            trusted_inputs["search_id"] != source["search_id"]
            or trusted_inputs["combo_id"] != source["combo_id"]
            or (
                "strategy_type" in trusted_inputs
                and trusted_inputs["strategy_type"] != source["strategy_type"]
            )
        ):
            return None
        if (
            re.fullmatch(
                r"voting-search-[0-9a-f]{32}",
                str(source["search_id"]),
            )
            is None
            or re.fullmatch(
                r"voting-combo-[0-9a-f]{32}",
                str(source["combo_id"]),
            )
            is None
            or source["strategy_type"]
            not in {"approval", "reject", "limit", "pricing", "segmentation"}
            or isinstance(source["rank"], bool)
            or not isinstance(source["rank"], int)
            or not 1 <= source["rank"] <= 10_000
        ):
            return None
        members = source["member_rule_ids"]
        if (
            not isinstance(members, list)
            or not 2 <= len(members) <= 50
            or len(set(members)) != len(members)
            or any(
                not isinstance(rule_id, str)
                or re.fullmatch(r"candidate-rule-[0-9a-f]{32}", rule_id) is None
                for rule_id in members
            )
        ):
            return None
        source_n = source["n"]
        failures = source["constraint_failures"]
        if (
            isinstance(source_n, bool)
            or not isinstance(source_n, int)
            or not 1 <= source_n <= len(members)
            or not isinstance(source["eligible"], bool)
            or not isinstance(failures, list)
            or len(failures) > 32
            or source["eligible"] is not (len(failures) == 0)
        ):
            return None
        for failure in failures:
            if (
                not isinstance(failure, dict)
                or set(failure) != {"metric", "operator", "threshold", "actual"}
                or not isinstance(failure["metric"], str)
                or not failure["metric"]
                or failure["operator"] not in {"gte", "lte"}
                or isinstance(failure["threshold"], bool)
                or not isinstance(failure["threshold"], (int, float))
                or isinstance(failure["actual"], bool)
                or not isinstance(failure["actual"], (int, float))
            ):
                return None
        if candidate["schema_version"] != "strategy.build-voting-candidate-tool.v2":
            return None
        if any(
            re.fullmatch(pattern, str(candidate[field])) is None
            for field, pattern in id_patterns.items()
        ) or any(
            re.fullmatch(r"[0-9a-f]{64}", str(candidate[field])) is None
            for field in hash_fields
        ):
            return None
        candidate_n = candidate["n"]
        candidate_k = candidate["k"]
        selected_entries = candidate["selected_entries"]
        if (
            not isinstance(candidate["pool_id"], str)
            or not candidate["pool_id"]
            or isinstance(candidate["revision"], bool)
            or not isinstance(candidate["revision"], int)
            or candidate["revision"] < 1
            or isinstance(candidate_n, bool)
            or not isinstance(candidate_n, int)
            or isinstance(candidate_k, bool)
            or not isinstance(candidate_k, int)
            or not 2 <= candidate_k <= 50
            or not 1 <= candidate_n <= candidate_k
            or candidate_n != source_n
            or not isinstance(selected_entries, list)
            or len(selected_entries) != candidate_k
        ):
            return None
        selected_rule_ids: list[str] = []
        selected_entry_ids: list[str] = []
        selected_pool_positions: list[int] = []
        for entry in selected_entries:
            if (
                not isinstance(entry, dict)
                or set(entry) != {"pool_position", "entry_id", "rule_id"}
                or isinstance(entry["pool_position"], bool)
                or not isinstance(entry["pool_position"], int)
                or entry["pool_position"] < 0
                or not isinstance(entry["entry_id"], str)
                or not entry["entry_id"]
                or not isinstance(entry["rule_id"], str)
                or not entry["rule_id"]
            ):
                return None
            selected_pool_positions.append(entry["pool_position"])
            selected_entry_ids.append(entry["entry_id"])
            selected_rule_ids.append(entry["rule_id"])
        if (
            len(set(selected_pool_positions)) != len(selected_pool_positions)
            or len(set(selected_entry_ids)) != len(selected_entry_ids)
            or len(set(selected_rule_ids)) != len(selected_rule_ids)
            or set(selected_rule_ids) != set(members)
        ):
            return None
        if (
            candidate["candidate_stage"] != "development"
            or candidate["observation_stage"] != "backtested"
            or candidate["validation_status"] != "unvalidated"
            or any(
                candidate[field] is not True or candidate[field] is not output[field]
                for field in (
                    "not_admitted",
                    "not_applied",
                    "not_adopted",
                    "not_deployed",
                )
            )
            or not isinstance(candidate["dataset_id"], str)
            or not candidate["dataset_id"]
            or not isinstance(candidate["target_col"], str)
            or not candidate["target_col"]
            or not isinstance(candidate["effect"], dict)
            or not isinstance(candidate["metrics"], dict)
            or not isinstance(candidate["hit_distribution"], list)
            or not isinstance(candidate["metric_observations"], list)
        ):
            return None
        sample_ref = candidate["sample_design_ref"]
        if (
            not isinstance(sample_ref, dict)
            or set(sample_ref)
            != {
                "artifact_id",
                "artifact_content_hash",
                "sample_design_id",
                "sample_design_content_hash",
                "partition",
            }
            or sample_ref["partition"] not in {"development", "risk/development"}
            or any(
                re.fullmatch(r"[0-9a-f]{64}", str(sample_ref[field])) is None
                for field in (
                    "artifact_id",
                    "artifact_content_hash",
                    "sample_design_content_hash",
                )
            )
        ):
            return None
        artifacts = candidate["artifacts"]
        if (
            not isinstance(artifacts, list)
            or len(artifacts) != 1
            or not isinstance(artifacts[0], dict)
            or set(artifacts[0])
            != {
                "artifact_id",
                "kind",
                "format",
                "filename",
                "content_hash",
                "download_url",
            }
            or artifacts[0]["kind"] != "strategy_voting_candidate_json"
            or artifacts[0]["format"] != "json"
            or re.fullmatch(
                r"[0-9a-f]{64}",
                str(artifacts[0]["content_hash"]),
            )
            is None
        ):
            return None
    except Exception:
        return None
    return source, candidate


def _render_search_voting_candidates(o: dict):
    """Render a bounded aggregate projection without implying a selection."""

    validated = _validated_voting_search_tool_output(o)
    if validated is None:
        return (
            "**Voting Failed to verify the integrity of search results**:The platform will not be shown withoutcanonical "
            "hash,Counting for consistencyartifact hash (a) Accredited search counts, rankings or indicators;"
            "Please re-enforce.Voting Group search.",
            [],
        )
    result, artifact_hash = validated
    search_id = result["search_id"]
    raw_combinations = result.get("combinations")
    combinations = (
        [
            item
            for item in raw_combinations
            if isinstance(item, dict)
            and item.get("eligible") is True
            and re.fullmatch(
                r"voting-combo-[0-9a-f]{32}",
                str(item.get("combo_id") or ""),
            )
            is not None
            and isinstance(item.get("member_ids"), list)
            and all(
                re.fullmatch(
                    r"candidate-rule-[0-9a-f]{32}",
                    str(rule_id),
                )
                is not None
                for rule_id in item["member_ids"]
            )
        ][:10]
        if isinstance(raw_combinations, list)
        else []
    )
    configuration = result.get("configuration")
    objective = (
        configuration.get("objective")
        if isinstance(configuration, dict)
        and isinstance(configuration.get("objective"), dict)
        else {}
    )
    objective_metric = str(objective.get("metric") or "")
    metric_order = [
        objective_metric,
        "hit_share",
        "bad_rate",
        "bad_capture_rate",
        "lift",
        "weighted_hit_share",
        "weighted_bad_rate",
        "weighted_bad_capture_rate",
        "hit_amount_share",
        "bad_amount_rate",
        "bad_amount_capture_rate",
    ]
    displayed_metrics: list[str] = []
    for metric in metric_order:
        if (
            metric
            and metric not in displayed_metrics
            and any(
                isinstance(item.get("metrics"), dict)
                and item["metrics"].get(metric) is not None
                for item in combinations
            )
        ):
            displayed_metrics.append(metric)

    text = (
        f"**Voting Group Read-only Search complete**:search ID `{search_id}`;"
        f"search_space {_voting_search_count_text(result['search_space'])},"
        f"evaluated {_voting_search_count_text(result['evaluated'])},"
        f"eligible {_voting_search_count_text(result['eligible'])}."
    )
    if result["truncated"] is True:
        text += (
            "\n\n**Search budget cut**:Presscanonical The first step in the process is to assess the budget in order of priority."
            "The following is only assessedTop-N;Conclusions that have not been assessed shall not be extrapolated."
        )
    else:
        text += "\n\nThe current search space is fully assessed."
    text += (
        "\n\n**Border**:This step is not modifiedPool,No grouping selected, no candidate built, no candidate selected"
        "If you need to build a subsequent application, you must quote a separate reference."
        "The configuration members also initiate requests for governance."
    )
    text += (
        "\n\n**Full aggregation resultartifact**:ContentsSHA-256 "
        f"`{artifact_hash}`;Please download from the unified product column of the current task."
        "Pool Identity, exclusion of detail and download route not always certifiedTool Field projection on the outer layer."
    )

    rows = []
    for item in combinations:
        metrics = item.get("metrics")
        assert isinstance(metrics, dict)
        rows.append(
            [
                str(item.get("rank") or ""),
                str(item["combo_id"]),
                ",".join(str(rule_id) for rule_id in item["member_ids"]),
                str(item.get("n") or ""),
                *[
                    _voting_search_metric_text(metric, metrics.get(metric))
                    for metric in displayed_metrics
                ],
            ]
        )
    return text, [
        {
            "title": "Voting Search for the bounds within the assessed rangeTop-10",
            "columns": [
                "Rank",
                "Combo ID",
                "MembersRule IDs",
                "n",
                *displayed_metrics,
            ],
            "rows": rows,
        }
    ]


def _validated_voting_search_tool_output(
    output: object,
) -> tuple[dict[str, Any], str] | None:
    """Authenticate every renderer-owned Voting-search fact before projection."""

    from marvis.packs.strategy.voting_candidate_search import (
        canonical_voting_candidate_search_result_json,
        validate_voting_candidate_search_result,
    )

    expected_fields = {
        "schema_version",
        "search_id",
        "request_hash",
        "content_hash",
        "pool_id",
        "pool_revision",
        "pool_snapshot_hash",
        "search_space",
        "evaluated",
        "truncated",
        "eligible",
        "excluded_unsupported_rule_ids",
        "search_result",
        "artifacts",
        "not_mutated_pool",
        "not_selected",
        "not_admitted",
        "not_applied",
        "not_adopted",
        "not_deployed",
    }
    try:
        if not isinstance(output, dict) or set(output) != expected_fields:
            return None
        if output["schema_version"] != "strategy.search-voting-candidates-tool.v1":
            return None
        result = validate_voting_candidate_search_result(output["search_result"])
        for field in (
            "search_id",
            "request_hash",
            "content_hash",
            "search_space",
            "evaluated",
            "truncated",
            "eligible",
        ):
            if output[field] != result[field]:
                return None
        if (
            not isinstance(output["pool_id"], str)
            or not output["pool_id"]
            or isinstance(output["pool_revision"], bool)
            or not isinstance(output["pool_revision"], int)
            or output["pool_revision"] < 1
            or re.fullmatch(
                r"[0-9a-f]{64}",
                str(output["pool_snapshot_hash"]),
            )
            is None
        ):
            return None
        if any(
            output[field] is not True
            for field in (
                "not_mutated_pool",
                "not_selected",
                "not_admitted",
                "not_applied",
                "not_adopted",
                "not_deployed",
            )
        ):
            return None
        excluded = output["excluded_unsupported_rule_ids"]
        if (
            not isinstance(excluded, list)
            or excluded != sorted(set(excluded))
            or any(
                not isinstance(rule_id, str)
                or re.fullmatch(r"candidate-rule-[0-9a-f]{32}", rule_id) is None
                for rule_id in excluded
            )
        ):
            return None
        artifacts = output["artifacts"]
        if (
            not isinstance(artifacts, list)
            or len(artifacts) != 1
            or not isinstance(artifacts[0], dict)
            or set(artifacts[0])
            != {
                "artifact_id",
                "kind",
                "format",
                "filename",
                "content_hash",
                "download_url",
            }
        ):
            return None
        artifact = artifacts[0]
        canonical = canonical_voting_candidate_search_result_json(result).encode(
            "utf-8"
        )
        artifact_hash = hashlib.sha256(canonical).hexdigest()
        if (
            re.fullmatch(r"[0-9a-f]{64}", str(artifact["artifact_id"])) is None
            or artifact["kind"] != "strategy_voting_candidate_search_json"
            or artifact["format"] != "json"
            or not isinstance(artifact["filename"], str)
            or not artifact["filename"].endswith(".json")
            or artifact["content_hash"] != artifact_hash
            or not isinstance(artifact["download_url"], str)
            or not artifact["download_url"].startswith("/api/tasks/")
            or f"expected_content_hash={artifact_hash}" not in artifact["download_url"]
        ):
            return None
    except Exception:
        return None
    return result, artifact_hash


def _voting_search_metric_text(metric: str, value: object) -> str:
    if value is None:
        return "n/a"
    if metric in {
        "hit_share",
        "bad_rate",
        "bad_capture_rate",
        "weighted_hit_share",
        "weighted_bad_rate",
        "weighted_bad_capture_rate",
        "hit_amount_share",
        "bad_amount_rate",
        "bad_amount_capture_rate",
    }:
        return _pct(value)
    return _fmt(value)


def _voting_search_count_text(value: object) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return _fmt(value)


def _cross_matrix_cell_metric(cell: dict, name: str):
    effect = cell.get("effect") if isinstance(cell.get("effect"), dict) else {}
    return effect.get(name, cell.get(name))


def _cross_matrix_observation_value(observation: dict, field: str, *, pct=False):
    status = str(observation.get("status") or "unavailable")
    value = observation.get(field)
    if status in {"unavailable", "insufficient_data", "not_applicable"}:
        return "n/a"
    return _pct(value) if pct else _num(value)


def _render_build_cross_matrix_candidate(o: dict):
    """Render a complete matrix in canonical axis order without selecting cells."""

    row_axis = o.get("row_axis") if isinstance(o.get("row_axis"), dict) else {}
    column_axis = o.get("column_axis") if isinstance(o.get("column_axis"), dict) else {}
    asset = (
        o.get("cross_matrix_candidate")
        if isinstance(o.get("cross_matrix_candidate"), dict)
        else {}
    )
    matrix = asset.get("matrix") if isinstance(asset.get("matrix"), dict) else {}
    cells = [item for item in (matrix.get("cells") or []) if isinstance(item, dict)]
    axes = [item for item in (asset.get("axes") or []) if isinstance(item, dict)]
    source_bin_by_id = {
        str(bin_row.get("bin_id") or ""): str(bin_row.get("source_bin_id") or "")
        for axis in axes
        for bin_row in (axis.get("bins") or [])
        if isinstance(bin_row, dict) and bin_row.get("bin_id")
    }
    artifacts = [item for item in (o.get("artifacts") or []) if isinstance(item, dict)]
    lifecycle = " / ".join(
        str(o.get(field) or "unknown")
        for field in ("candidate_stage", "observation_stage", "validation_status")
    )
    drop_text = (
        "true"
        if o.get("drop_nan_labels") is True
        else "false"
        if o.get("drop_nan_labels") is False
        else "n/a"
    )
    text = (
        f"**Two-dimensional.Cross Matrix Candidate build complete**:Assets`{o.get('asset_id', '')}`,"
        f"asset hash `{o.get('asset_hash', '')}`;Matrix candidate evidence"
        f"`{o.get('candidate_id', '')}` / `{o.get('evidence_hash', '')}`;"
        "Evidence of source-single variable candidate"
        f"`{o.get('parent_candidate_id', '')}` / `{o.get('parent_evidence_hash', '')}`.\n"
        f"- X Axis:{row_axis.get('feature', '')} / {row_axis.get('method', '')} / "
        f"{row_axis.get('bin_count', 0)} bins\n"
        f"- Y Axis:{column_axis.get('feature', '')} / "
        f"{column_axis.get('method', '')} / {column_axis.get('bin_count', 0)} bins\n"
        f"- Solid{o.get('cell_count', 0)} complete cells;state`{lifecycle}`.\n"
        "**This step only generates a complete matrixevidence:No cells selected, no pools not applied, no writing back,"
        "Not accepted, not deployed.**"
    )
    text += (
        "\n\n**Blank sample caliber**:"
        f"dataset `{o.get('dataset_id', 'n/a')}`,target `{o.get('target_col', 'n/a')}`;"
        f"population {_fmt(o.get('population_count'))},"
        f"labeled {_fmt(o.get('labeled_count'))};"
        f"drop_nan_labels `{drop_text}`,"
        f"nan_labels_dropped {_fmt(o.get('nan_labels_dropped'))}."
    )
    text += (
        "\n\n**Blank sample observations (not independently validated)**:"
        "The table below remains unchangedX/Y Box and completeCartesian the order of the assets in the cells, not at the rate of badness,Lift "
        "Or the other indicator is re-numbered and does not constitute a grid selection proposal."
    )
    links = [
        f"[{str(item.get('filename') or item.get('kind') or 'Download')}]"
        f"({str(item.get('download_url'))})"
        for item in artifacts
        if item.get("download_url")
    ]
    if links:
        text += "\n\n**Cross Matrix CompleteJSON**:" + ";".join(links)

    metric_rows = []
    amount_rows = []
    for cell in cells:
        row_bin_id = str(cell.get("row_bin_id") or "")
        column_bin_id = str(cell.get("column_bin_id") or "")
        row_bin = source_bin_by_id.get(
            row_bin_id,
            str(cell.get("row_source_bin_id") or row_bin_id),
        )
        column_bin = source_bin_by_id.get(
            column_bin_id,
            str(cell.get("column_source_bin_id") or column_bin_id),
        )
        cell_id = str(cell.get("cell_id") or f"{row_bin} × {column_bin}")
        metric_rows.append(
            [
                cell_id,
                row_bin,
                column_bin,
                _fmt(_cross_matrix_cell_metric(cell, "count")),
                _pct(_cross_matrix_cell_metric(cell, "share")),
                _fmt(_cross_matrix_cell_metric(cell, "good")),
                _fmt(_cross_matrix_cell_metric(cell, "bad")),
                _pct(_cross_matrix_cell_metric(cell, "bad_rate")),
                _num(_cross_matrix_cell_metric(cell, "lift")),
                _num(_cross_matrix_cell_metric(cell, "woe")),
                _num(_cross_matrix_cell_metric(cell, "iv_contribution")),
            ]
        )
        effect = cell.get("effect") if isinstance(cell.get("effect"), dict) else {}
        amounts = (
            effect.get("amount_metrics")
            if isinstance(effect.get("amount_metrics"), dict)
            else {}
        )
        for dimension, label in (
            ("loan_amount", "Amount released"),
            ("overdue_amount", "Overdue amounts"),
            ("overdue_rate", "Matching overdue rate"),
        ):
            observation = (
                amounts.get(dimension)
                if isinstance(amounts.get(dimension), dict)
                else None
            )
            if observation is None:
                continue
            status = str(observation.get("status") or "unavailable")
            covered = observation.get("covered_count")
            amount_rows.append(
                [
                    cell_id,
                    row_bin,
                    column_bin,
                    label,
                    status,
                    "n/a" if covered is None else _fmt(covered),
                    _cross_matrix_observation_value(
                        observation,
                        "coverage_rate",
                        pct=True,
                    ),
                    _cross_matrix_observation_value(
                        observation,
                        "value",
                        pct=dimension == "overdue_rate",
                    ),
                    str(observation.get("reason") or ""),
                ]
            )

    tables = []
    if metric_rows:
        tables.append(
            {
                "title": "Two-dimensional.Cross Matrix Full cell (maintenance)X/Y (Box indent)",
                "columns": [
                    "Cell ID",
                    "X source bin",
                    "Y source bin",
                    "Number of samples",
                    "Samples as a percentage",
                    "Good sample.",
                    "Bad sample.",
                    "Bad rate",
                    "Lift",
                    "WOE",
                    "IV",
                ],
                "rows": metric_rows,
            }
        )
    if amount_rows:
        tables.append(
            {
                "title": "Two-dimensional.Cross Matrix Value observations",
                "columns": [
                    "Cell ID",
                    "X source bin",
                    "Y source bin",
                    "Dimensions",
                    "Status",
                    "Overwrite Samples",
                    "Coverage",
                    "Observations",
                    "Reason",
                ],
                "rows": amount_rows,
            }
        )
    return text, tables


def _render_materialize_cross_matrix_cell_selection(o: dict):
    """Render pointer-only Cross cells in the tool's canonical source order."""

    artifacts = [item for item in (o.get("artifacts") or []) if isinstance(item, dict)]
    artifact = next(
        (
            item
            for item in artifacts
            if item.get("format") == "json" and item.get("download_url")
        ),
        None,
    )
    cell_ids = [str(value) for value in (o.get("cell_ids") or []) if value]
    lifecycle = " / ".join(
        str(o.get(field) or "unknown")
        for field in ("candidate_stage", "observation_stage", "validation_status")
    )
    text = (
        "**Cross Matrix Accurate cell selection is physically modified.**"
        f"Quite solidified by source matrix**{len(cell_ids)}** individualcell pointer;Multiplecell "
        "Use of certaintyOR Semantic. The product saves only the invertible references to the complete matrix and does not copy observations"
        "Indicators, not implementing rankings or recommendations, and not generating operational actions; not in pool, not applied, not adopted, not deployed."
        f"Current Status`{lifecycle}`."
    )
    if artifact is not None:
        label = str(
            artifact.get("filename")
            or artifact.get("kind")
            or "cross-matrix-cell-selection.json"
        )
        text += f"\n\n**Cross Matrix Cell SelectionJSON**:[{label}]({artifact['download_url']})"

    reason = o.get("selection_reason")
    details = [
        ["Selection ID", str(o.get("selection_id") or "")],
        ["Selection Hash", str(o.get("selection_hash") or "")],
        ["Group ID", str(o.get("group_id") or "")],
        ["Source Asset ID", str(o.get("source_asset_id") or "")],
        ["Source Asset Hash", str(o.get("source_asset_hash") or "")],
        ["Source Candidate ID", str(o.get("source_candidate_id") or "")],
        ["Source Evidence Hash", str(o.get("source_evidence_hash") or "")],
        ["Fragment ID", str(o.get("fragment_id") or "")],
        ["Fragment Type", str(o.get("fragment_type") or "")],
        ["Rule ID", str(o.get("rule_id") or "")],
        ["Effect ID", str(o.get("effect_id") or "")],
        ["Selection Reason", str(reason) if reason is not None else "Not provided"],
        ["Not Admitted", str(o.get("not_admitted"))],
        ["Not Applied", str(o.get("not_applied"))],
        ["Not Adopted", str(o.get("not_adopted"))],
        ["Not Deployed", str(o.get("not_deployed"))],
    ]
    tables = [
        {
            "title": "Cross Matrix Precision cell selection references",
            "columns": ["Fields", "Value"],
            "rows": details,
        }
    ]
    if cell_ids:
        tables.append(
            {
                "title": "SelectedCell IDs(Source Matrix Order)",
                "columns": ["Order", "Cell ID"],
                "rows": [
                    [str(index), cell_id]
                    for index, cell_id in enumerate(cell_ids, start=1)
                ],
            }
        )
    return text, tables


def _render_build_scorecard_band_asset(o: dict):
    """Render the complete measured band/cutoff set without choosing one."""

    asset = (
        o.get("scorecard_band_asset")
        if isinstance(o.get("scorecard_band_asset"), Mapping)
        else {}
    )
    bands = [item for item in (asset.get("bands") or []) if isinstance(item, Mapping)]
    cutoffs = [
        item for item in (asset.get("cutoffs") or []) if isinstance(item, Mapping)
    ]
    performance = (
        o.get("performance") if isinstance(o.get("performance"), Mapping) else {}
    )
    banding = o.get("banding") if isinstance(o.get("banding"), Mapping) else {}
    text = (
        f"**Scorecard Full fraction belt built**:Assets`{o.get('asset_id', '')}`,"
        f"asset hash `{o.get('asset_hash', '')}`;Solid"
        f"**{_fmt(o.get('band_count', len(bands)))}** A fractional band and"
        f"**{_fmt(o.get('cutoff_count', len(cutoffs)))}** Internalcutoff.\n"
        f"- Slotting method`{banding.get('method', 'n/a')}`;Request"
        f"{_fmt(banding.get('requested_bin_count', 'n/a'))} File, actual"
        f"{_fmt(banding.get('effective_bin_count', len(bands)))} Scan.\n"
        f"- risk/development Sample{_fmt(o.get('development_count'))} Okay."
        f"Labeled{_fmt(o.get('labeled_count'))} Okay, bad sample."
        f"{_fmt(o.get('bad_count'))};AUC {_num(performance.get('auc'))},"
        f"KS {_num(performance.get('ks'))}.\n"
        "**This step generates only complete, conclusive fractional evidence: no automatic selection, ranking or recommendation"
        "cutoff;Unpositioned, not applied, not accepted, not deployed.**"
    )
    text += _scorecard_download_text(o, fallback="scorecard-band.json")
    band_rows = [
        [
            str(band.get("band_id") or band.get("bin_id") or ""),
            _num(band.get("lower_bound")),
            _num(band.get("upper_bound")),
            _fmt(band.get("count")),
            _pct(band.get("share")),
            _fmt(band.get("labeled_count")),
            _fmt(band.get("bad_count")),
            _pct(band.get("bad_rate")),
            _num(band.get("average_pd")),
        ]
        for band in bands
    ]
    cutoff_rows = []
    for cutoff in cutoffs:
        lower = (
            cutoff.get("lower_risk")
            if isinstance(cutoff.get("lower_risk"), Mapping)
            else {}
        )
        higher = (
            cutoff.get("higher_risk")
            if isinstance(cutoff.get("higher_risk"), Mapping)
            else {}
        )
        cutoff_rows.append(
            [
                str(cutoff.get("cutoff_id") or ""),
                _num(cutoff.get("execution_pd")),
                _num(cutoff.get("display_points")),
                _fmt(lower.get("count")),
                _pct(lower.get("bad_rate")),
                _fmt(higher.get("count")),
                _pct(higher.get("bad_rate")),
                "Yes." if cutoff.get("mask_equivalence") is True else "Yes",
            ]
        )
    tables = []
    if band_rows:
        tables.append(
            {
                "title": "Scorecard Split Belt",
                "columns": [
                    "Band ID",
                    "Raw PD Bottom",
                    "Raw PD Upper boundary",
                    "Number of samples",
                    "Percentage",
                    "Labeled",
                    "Bad sample.",
                    "Bad rate",
                    "AveragePD",
                ],
                "rows": band_rows,
            }
        )
    if cutoff_rows:
        tables.append(
            {
                "title": "Scorecard cutoff Full evidence.",
                "columns": [
                    "Cutoff ID",
                    "ImplementationPD",
                    "Show Points",
                    "Low-risk sample",
                    "Low risk and risk rate",
                    "High-risk sample",
                    "High risk and risk",
                    "PD/Points Equivalent",
                ],
                "rows": cutoff_rows,
            }
        )
    return text, tables


def _render_materialize_scorecard_cutoff_selection(o: dict):
    """Render one explicit pointer without implying Pool admission or action."""

    reason = o.get("selection_reason")
    text = (
        "**Scorecard cutoff Exact selection is physically developed.**"
        f"From Full Score Belt`{o.get('source_asset_id', '')}` Createcutoff "
        f"`{o.get('cutoff_id', '')}` It's...pointer-only Can not be changed."
        "This step does not automatically rank or recommend, does not copy the full fractional tape or indicator, and does not generate business actions;"
        "**Unpositioned, not applied, not accepted, not deployed.**"
    )
    text += _scorecard_download_text(
        o,
        fallback="scorecard-cutoff-selection.json",
    )
    return text, [
        {
            "title": "Scorecard cutoff Select Reference",
            "columns": ["Fields", "Value"],
            "rows": [
                ["Selection ID", str(o.get("selection_id") or "")],
                ["Selection Hash", str(o.get("selection_hash") or "")],
                ["Source Asset ID", str(o.get("source_asset_id") or "")],
                ["Source Asset Hash", str(o.get("source_asset_hash") or "")],
                ["Cutoff ID", str(o.get("cutoff_id") or "")],
                [
                    "Selection Reason",
                    str(reason) if reason is not None else "Not provided",
                ],
                ["Not Admitted", str(o.get("not_admitted"))],
                ["Not Applied", str(o.get("not_applied"))],
                ["Not Adopted", str(o.get("not_adopted"))],
                ["Not Deployed", str(o.get("not_deployed"))],
            ],
        }
    ]


def _render_search_cross_threshold_rules(o: dict):
    result = o.get("search_result") if isinstance(o.get("search_result"), dict) else {}
    configuration = (
        result.get("configuration")
        if isinstance(result.get("configuration"), dict)
        else {}
    )
    rules = [
        item for item in (result.get("rules") or [])[:20] if isinstance(item, dict)
    ]
    text = (
        "**2D/3D Cross The threshold rule search is complete.**"
        f"Search`{result.get('search_id', '')}` Use"
        f"{_fmt(configuration.get('dimension'))}D Group,"
        f"assessed{_fmt(result.get('evaluated'))} / "
        f"{_fmt(result.get('search_space'))} The bar test,"
        f"of which{_fmt(result.get('eligible'))} Article is binding."
        "**Sorting is used only for the presentation of evidence; platform does not automatically select, build, enter, apply,"
        "Adopt or deploy any rules.**"
    )
    return text, [
        {
            "title": "Cross Threshold rule search results (caps 20 shows)",
            "columns": [
                "Rank",
                "Rule ID",
                "Conditions",
                "Hit Share",
                "Bad Rate",
                "Lift",
                "Amount Lift",
                "Eligible",
                "Constraint Failures",
            ],
            "rows": [
                [
                    _fmt(rule.get("rank")),
                    str(rule.get("rule_id") or ""),
                    " AND ".join(
                        (
                            f"{item.get('feature', '')} "
                            f"{item.get('operator', '')} "
                            f"{_fmt(item.get('threshold'))}"
                            + (
                                " OR missing"
                                if item.get("include_missing") is True
                                else ""
                            )
                        )
                        for item in (rule.get("conditions") or [])
                        if isinstance(item, dict)
                    ),
                    _pct((rule.get("metrics") or {}).get("hit_share")),
                    _pct((rule.get("metrics") or {}).get("bad_rate")),
                    _fmt((rule.get("metrics") or {}).get("lift")),
                    _fmt((rule.get("metrics") or {}).get("amount_lift")),
                    str(rule.get("eligible")),
                    ",".join(rule.get("constraint_failures") or []),
                ]
                for rule in rules
            ],
        }
    ]


def _render_build_cross_rule_candidate_from_search(o: dict):
    candidate = o.get("candidate") if isinstance(o.get("candidate"), dict) else {}
    selection = (
        o.get("source_search_selection")
        if isinstance(o.get("source_search_selection"), dict)
        else {}
    )
    metrics = (
        candidate.get("metrics") if isinstance(candidate.get("metrics"), dict) else {}
    )
    text = (
        "**Cross The threshold rule candidate has been refined.**"
        f"Candidates`{candidate.get('asset_id', '')}` From Search"
        f"`{selection.get('search_id', '')}` Rules"
        f"`{selection.get('rule_id', '')}`;Originalrank "
        f"{_fmt(selection.get('rank'))},eligible "
        f"`{selection.get('eligible')}` As evidence of origin only."
        "**Candidates are still not independently validated, unfilled, unapplied, unaccommodated and undeployed.**"
    )
    return text, [
        {
            "title": "Cross Candidature for the threshold rule",
            "columns": ["Fields", "Value"],
            "rows": [
                ["Asset ID", str(candidate.get("asset_id") or "")],
                ["Rule ID", str(selection.get("rule_id") or "")],
                ["Dimension", _fmt(candidate.get("dimension"))],
                ["Hit Share", _pct(metrics.get("hit_share"))],
                ["Bad Rate", _pct(metrics.get("bad_rate"))],
                ["Lift", _fmt(metrics.get("lift"))],
                ["Amount Lift", _fmt(metrics.get("amount_lift"))],
                [
                    "Selection Reason",
                    str(candidate.get("selection_reason") or "Not provided"),
                ],
            ],
        }
    ]


CANDIDATE_PRESENTERS = {
    "design_strategy_candidate": _render_design_strategy_candidate,
    "analyze_univariate_candidates": _render_analyze_univariate_candidates,
    "build_automatic_tree_candidate": _render_build_automatic_tree_candidate,
    "apply_automatic_tree": _render_apply_automatic_tree,
    "materialize_automatic_tree_leaf_fragment": _render_materialize_automatic_tree_leaf_fragment,
    "materialize_interactive_tree_frontier_selection": _render_materialize_interactive_tree_frontier_selection,
    "materialize_interactive_tree_frontier_group_selection": _render_materialize_interactive_tree_frontier_group_selection,
    "search_voting_candidates": _render_search_voting_candidates,
    "build_voting_candidate_from_search": _render_build_voting_candidate_from_search,
    "build_voting_candidate": _render_build_voting_candidate,
    "build_cross_matrix_candidate": _render_build_cross_matrix_candidate,
    "search_cross_threshold_rules": _render_search_cross_threshold_rules,
    "build_cross_rule_candidate_from_search": _render_build_cross_rule_candidate_from_search,
    "materialize_cross_matrix_cell_selection": _render_materialize_cross_matrix_cell_selection,
    "build_scorecard_band_asset": _render_build_scorecard_band_asset,
    "materialize_scorecard_cutoff_selection": _render_materialize_scorecard_cutoff_selection,
    "refine_univariate_candidate": _render_refine_univariate_candidate,
}

INTEGRITY_FAILURES = {
    "apply_automatic_tree": _automatic_tree_apply_integrity_failure,
}

__all__ = ["CANDIDATE_PRESENTERS", "INTEGRITY_FAILURES"]
