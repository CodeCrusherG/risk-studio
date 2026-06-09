import { escapeHtml } from "../ui-utils.js";

// VD-6: dual-encode signal state (shape, not just color) so ready/warning/
// error/neutral read clearly for color-blind users scanning the delivery
// panel. Semantic shapes: check / triangle-exclaim / cross / open circle.
const SIGNAL_GLYPH_PATHS = {
  ready: '<path d="M4 8.5 L6.7 11 L12 4.5" />',
  warning: '<path d="M8 3 L14 13 L2 13 Z" /><path d="M8 6.5 V9.5" /><circle cx="8" cy="11.3" r="0.6" fill="currentColor" stroke="none" />',
  error: '<path d="M4 4 L12 12" /><path d="M12 4 L4 12" />',
  neutral: '<circle cx="8" cy="8" r="5" />',
};

function signalGlyph(kind) {
  const path = SIGNAL_GLYPH_PATHS[kind] || SIGNAL_GLYPH_PATHS.neutral;
  return `<span class="signal-glyph" aria-hidden="true"><svg viewBox="0 0 16 16">${path}</svg></span>`;
}

const METRIC_ORDER = [
  "oot_ks",
  "test_ks",
  "oot_auc",
  "test_auc",
  "oot_rmse",
  "test_rmse",
  "oot_mae",
  "test_mae",
  "oot_r2",
  "test_r2",
  "oot_macro_auc",
  "test_macro_auc",
  "oot_logloss",
  "test_logloss",
  "oot_accuracy",
  "test_accuracy",
  "feature_count",
  "n_features",
];

export function renderModelDeliveryPanel(message, options = {}) {
  const delivery = message?.metadata?.model_delivery;
  if (!delivery || typeof delivery !== "object") return "";
  const taskId = String(
    delivery.task_id
    || message?.task_id
    || message?.metadata?.task_id
    || options.taskId
    || ""
  );
  const compact = options.compact === true;
  const sourceTool = String(delivery.source_tool || "");
  const title = sourceTool === "post_training_action"
    ? "Model outputs"
    : sourceTool === "select_experiment"
      ? "Final model selection"
      : "Candidate model comparison";
  const selectedExperimentId = String(delivery.selected_experiment_id || "");
  const artifactId = String(delivery.artifact_id || "");
  const recipe = String(delivery.recipe || "");
  const targetType = String(delivery.target_type || "");
  const selectionMetric = String(delivery.selection_metric || "");
  const reason = String(delivery.selection_reason || "");
  const chips = [
    ["Experiment", selectedExperimentId || "-"],
    ["Algorithm", recipe || "-"],
    ["Objective", targetType || "-"],
    ["Indicators", selectionMetric || "-"],
    ["Products", artifactId || "-"],
  ].filter(([, value]) => value !== "-" || !compact).map(([label, value]) => (
    `<div class="model-delivery-chip"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`
  )).join("");
  const readinessHtml = readinessCards(delivery.readiness);
  const businessHtml = businessSignalSummary(delivery.business_signals);
  const policyHtml = policySignalSummary(delivery.policy_signals);
  const policyDecisionHtml = policyDecisionSummary(delivery.policy_decision);
  const metricsHtml = metricsGrid(delivery.metrics);
  const expectedPlanId = String(message?.metadata?.plan_id || "");
  const expectedStepId = String(message?.metadata?.step_id || "");
  const candidateSelectionGate = message?.metadata?.kind === "gate"
    && String(message?.metadata?.gate_source_tool || "") === "select_experiment"
    && sourceTool === "compare_experiments";
  const candidatesHtml = candidateTable(delivery.candidates, {
    interactive: candidateSelectionGate,
    expectedPlanId,
    expectedStepId,
    recommendedExperimentId: trustedRecommendedExperimentId(delivery),
  });
  const actionsHtml = actionTable(delivery.actions);
  const reportHtml = reportSummary(delivery.report);
  const artifactsHtml = artifactList(delivery, { taskId });
  return `<div class="model-delivery-panel" data-model-delivery-source="${escapeHtml(sourceTool)}">
    <div class="model-delivery-head">
      <span>${escapeHtml(title)}</span>
      <small>${escapeHtml(readinessHeadline(delivery.readiness))}</small>
    </div>
    ${chips ? `<div class="model-delivery-chip-grid">${chips}</div>` : ""}
    ${reason ? `<div class="model-delivery-reason">${escapeHtml(reason)}</div>` : ""}
    ${readinessHtml}
    ${businessHtml}
    ${policyHtml}
    ${policyDecisionHtml}
    ${metricsHtml}
    ${candidatesHtml}
    ${actionsHtml}
    ${reportHtml}
    ${artifactsHtml}
  </div>`;
}

function readinessCards(items) {
  const rows = Array.isArray(items) ? items.filter((item) => item && typeof item === "object") : [];
  if (!rows.length) return "";
  return `<div class="model-delivery-readiness-grid">${rows.map((item) => {
    const status = String(item.status || "");
    const artifact = String(item.artifact || "");
    const reason = String(item.reason || "");
    const kind = statusKind(status);
    return `<div class="model-delivery-readiness-card" data-readiness-kind="${escapeHtml(kind)}">
      <span>${escapeHtml(String(item.label || item.id || "Delivery"))}</span>
      <strong>${signalGlyph(kind)}${escapeHtml(statusLabel(status))}</strong>
      ${artifact ? `<code>${escapeHtml(shortArtifact(artifact))}</code>` : ""}
      ${reason ? `<small>${escapeHtml(reason)}</small>` : ""}
    </div>`;
  }).join("")}</div>`;
}

function metricsGrid(metrics) {
  const metricObject = metrics && typeof metrics === "object" ? metrics : {};
  const keys = sortedMetricKeys(Object.keys(metricObject)).slice(0, 10);
  if (!keys.length) return "";
  return `<div class="model-delivery-metrics">
    <div class="modeling-section-label">Final model metrics</div>
    <div class="model-delivery-metric-grid">${keys.map((key) => (
      `<div class="model-delivery-metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(formatMetric(metricObject[key]))}</strong></div>`
    )).join("")}</div>
  </div>`;
}

function trustedRecommendedExperimentId(delivery) {
  const candidates = Array.isArray(delivery?.candidates)
    ? delivery.candidates.filter((item) => item && typeof item === "object")
    : [];
  const ids = new Set(candidates.map((item) => String(item.id || "")).filter(Boolean));
  const declared = String(
    delivery?.recommended_experiment_id
    || delivery?.best_experiment_id
    || ""
  ).trim();
  if (declared && ids.has(declared)) return declared;
  const marked = candidates.find((item) => item.recommended === true);
  const markedId = String(marked?.id || "").trim();
  return ids.has(markedId) ? markedId : "";
}

function candidateTable(candidates, options = {}) {
  const rows = Array.isArray(candidates) ? candidates.filter((item) => item && typeof item === "object") : [];
  if (!rows.length) return "";
  const interactive = options.interactive === true;
  const expectedPlanId = String(options.expectedPlanId || "");
  const expectedStepId = String(options.expectedStepId || "");
  const recommendedExperimentId = String(options.recommendedExperimentId || "");
  const selectedRow = rows.find((row) => row.selected === true && String(row.id || ""));
  const firstCandidateId = String(rows.find((row) => String(row.id || ""))?.id || "");
  const defaultExperimentId = recommendedExperimentId
    || String(selectedRow?.id || "")
    || firstCandidateId;
  const radioName = `model-candidate-${expectedPlanId || "plan"}-${expectedStepId || "step"}`;
  const metricKeys = sortedMetricKeys([
    ...new Set(rows.flatMap((row) => Object.keys(row.metrics && typeof row.metrics === "object" ? row.metrics : {}))),
  ]).slice(0, 6);
  const headers = [
    ...(interactive ? ["Selection"] : []),
    "Algorithm", "Experiment", ...metricKeys, "Stability", "Number of features", "Calibration", "Delivery", "Monotonicity", "Approval",
  ];
  const selectionNote = interactive
    ? `<div class="model-delivery-selection-note">${recommendedExperimentId
      ? "The recommended candidate is selected. Review its results before confirming."
      : "The first candidate is selected. Review all candidates before confirming."}</div>`
    : "";
  return `<div class="model-delivery-table-wrap">
    <div class="modeling-section-label">Candidate model</div>
    ${selectionNote}
    <table class="model-delivery-table">
      <thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((row) => {
        const caps = row.capabilities && typeof row.capabilities === "object" ? row.capabilities : {};
        const metrics = row.metrics && typeof row.metrics === "object" ? row.metrics : {};
        const signals = row.business_signals && typeof row.business_signals === "object" ? row.business_signals : {};
        const policy = row.policy_signals && typeof row.policy_signals === "object" ? row.policy_signals : {};
        const candidateId = String(row.id || "");
        const selected = row.selected === true;
        const recommended = candidateId && candidateId === recommendedExperimentId;
        const checked = interactive && candidateId === defaultExperimentId;
        const choiceCell = interactive
          ? `<td><input type="radio" data-model-candidate-choice="1" data-expected-plan-id="${escapeHtml(expectedPlanId)}" data-expected-step-id="${escapeHtml(expectedStepId)}" name="${escapeHtml(radioName)}" value="${escapeHtml(candidateId)}" aria-label="Select candidate model ${escapeHtml(candidateId || "Unknown")}"${checked ? " checked" : ""}${candidateId ? "" : " disabled"}></td>`
          : "";
        const badges = [
          selected ? '<span class="model-delivery-selected">Selected</span>' : "",
          recommended ? '<span class="model-delivery-selected">Recommended</span>' : "",
        ].filter(Boolean).join(" ");
        return `<tr${selected ? ' class="is-selected"' : ""}>
          ${choiceCell}
          <td>${escapeHtml(String(row.recipe || "-"))}${badges ? ` ${badges}` : ""}</td>
          <td><code>${escapeHtml(String(row.id || "-"))}</code></td>
          ${metricKeys.map((key) => `<td class="model-delivery-num">${escapeHtml(formatMetric(metrics[key]))}</td>`).join("")}
          <td><span class="model-delivery-status" data-signal-kind="${escapeHtml(signalKind(signals.stability))}">${signalGlyph(signalKind(signals.stability))}${escapeHtml(String(signals.stability || "-"))}</span></td>
          <td class="model-delivery-num">${escapeHtml(formatMetric(signals.feature_count))}</td>
          <td>${escapeHtml(String(signals.calibration || "-"))}</td>
          <td>${escapeHtml(String(signals.delivery || (caps.pmml_supported && caps.handoff_supported ? "Transferable" : "Native only")))}</td>
          <td><span class="model-delivery-status" data-signal-kind="${escapeHtml(signalKind(policy.monotonicity_status || policy.monotonicity))}">${signalGlyph(signalKind(policy.monotonicity_status || policy.monotonicity))}${escapeHtml(String(policy.monotonicity || "-"))}</span></td>
          <td><span class="model-delivery-status" data-signal-kind="${escapeHtml(signalKind(policy.approval_status || policy.approval))}">${signalGlyph(signalKind(policy.approval_status || policy.approval))}${escapeHtml(String(policy.approval || "-"))}</span></td>
        </tr>`;
      }).join("")}</tbody>
    </table>
  </div>`;
}

function businessSignalSummary(signals) {
  const data = signals && typeof signals === "object" ? signals : {};
  const items = [
    ["Stability", data.stability || "Not assessed", signalKind(data.stability)],
    ["Number of features", data.feature_count === null || data.feature_count === undefined ? "-" : formatMetric(data.feature_count), "neutral"],
    ["Calibration", data.calibration || "Uncorrected", data.calibration === "Clarification" ? "warning" : "neutral"],
    ["Delivery", data.delivery || "Awaiting confirmation", data.delivery === "Transferable" ? "ready" : "warning"],
  ];
  return `<div class="model-delivery-business-grid">${items.map(([label, value, kind]) => (
    `<div class="model-delivery-business-card" data-signal-kind="${escapeHtml(kind)}">
      <span>${escapeHtml(label)}</span>
      <strong>${signalGlyph(kind)}${escapeHtml(String(value))}</strong>
    </div>`
  )).join("")}</div>`;
}

function policySignalSummary(signals) {
  const data = signals && typeof signals === "object" ? signals : {};
  if (!Object.keys(data).length) return "";
  const items = [
    ["Scorecard", data.scorecard || "Not assessed", signalKind(data.scorecard_status || data.scorecard)],
    ["Monotonicity", data.monotonicity || "Not assessed", signalKind(data.monotonicity_status || data.monotonicity)],
    ["Approval recommendation", data.approval || "Not assessed", signalKind(data.approval_status || data.approval)],
  ];
  const reasons = Array.isArray(data.reasons)
    ? data.reasons.map((item) => String(item)).filter(Boolean).slice(0, 3)
    : [];
  return `<div class="model-delivery-policy">
    <div class="modeling-section-label">Model policy</div>
    <div class="model-delivery-policy-grid">${items.map(([label, value, kind]) => (
      `<div class="model-delivery-policy-card" data-signal-kind="${escapeHtml(kind)}">
        <span>${escapeHtml(label)}</span>
        <strong>${signalGlyph(kind)}${escapeHtml(String(value))}</strong>
      </div>`
    )).join("")}</div>
    ${reasons.length ? `<div class="model-delivery-policy-reasons">${reasons.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>` : ""}
  </div>`;
}

function policyDecisionSummary(decision) {
  const data = decision && typeof decision === "object" ? decision : {};
  if (!Object.keys(data).length) return "";
  const status = String(data.status || "not_requested");
  const policy = data.policy && typeof data.policy === "object" ? data.policy : {};
  const profile = data.profile && typeof data.profile === "object" ? data.profile : {};
  const violations = Array.isArray(data.violations)
    ? data.violations.filter((item) => item && typeof item === "object")
    : [];
  const enabledRules = Object.entries(policy)
    .filter(([, value]) => value === true || typeof value === "number" || (typeof value === "string" && value.trim()))
    .map(([key, value]) => `${key}: ${value}`)
    .slice(0, 4);
  const items = [
    ["Execution results", policyDecisionLabel(status), policyDecisionKind(status)],
    ["PMML", profile.pmml_supported ? "Satisfied" : "Not met", profile.pmml_supported ? "ready" : "warning"],
    ["Transfer", profile.handoff_supported ? "Satisfied" : "Not met", profile.handoff_supported ? "ready" : "warning"],
    ["Monotonicity", profile.monotonicity_declared ? "Declared" : "Undeclared", profile.monotonicity_declared ? "ready" : "warning"],
  ];
  const violationText = violations
    .map((item) => String(item.message || item.code || ""))
    .filter(Boolean)
    .slice(0, 3);
  return `<div class="model-delivery-policy" data-policy-decision-status="${escapeHtml(status)}">
    <div class="modeling-section-label">Policy checks</div>
    <div class="model-delivery-policy-grid">${items.map(([label, value, kind]) => (
      `<div class="model-delivery-policy-card" data-signal-kind="${escapeHtml(kind)}">
        <span>${escapeHtml(label)}</span>
        <strong>${signalGlyph(kind)}${escapeHtml(String(value))}</strong>
      </div>`
    )).join("")}</div>
    ${enabledRules.length ? `<div class="model-delivery-policy-reasons">${enabledRules.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>` : ""}
    ${violationText.length ? `<div class="model-delivery-policy-reasons">${violationText.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>` : ""}
    ${data.override_reason ? `<div class="model-delivery-policy-reasons"><span>Override reason:  ${escapeHtml(String(data.override_reason))}</span></div>` : ""}
  </div>`;
}

function actionTable(actions) {
  const rows = Array.isArray(actions) ? actions.filter((item) => item && typeof item === "object") : [];
  if (!rows.length) return "";
  return `<div class="model-delivery-table-wrap">
    <div class="modeling-section-label">Output actions</div>
    <table class="model-delivery-table">
      <thead><tr><th>Actions</th><th>Status</th><th>Files / tasks</th><th>Notes</th></tr></thead>
      <tbody>${rows.map((row) => {
        const artifact = String(
          row.pmml_path
          || row.validation_task_id
          || row.challenger_task_id
          || row.markdown_path
          || row.package_path
          || ""
        );
        return `<tr>
          <td>${escapeHtml(actionLabel(row.action))}</td>
          <td><span class="model-delivery-status" data-readiness-kind="${escapeHtml(statusKind(row.status))}">${signalGlyph(statusKind(row.status))}${escapeHtml(statusLabel(row.status))}</span></td>
          <td>${artifact ? `<code>${escapeHtml(shortArtifact(artifact))}</code>` : "-"}</td>
          <td>${escapeHtml(String(row.reason || ""))}</td>
        </tr>`;
      }).join("")}</tbody>
    </table>
  </div>`;
}

function actionLabel(action) {
  const key = String(action || "");
  return {
    export_pmml: "ExportPMML",
    handoff_to_validation: "Create validation task",
    create_challenger_backtest: "Create challenger / backtest",
  }[key] || key || "-";
}

function artifactList(delivery, { taskId = "" } = {}) {
  const artifacts = [
    ["Native model", delivery.native_model_path, "native_model"],
    ["PMML", delivery.pmml_path, "pmml"],
    ["Model card", delivery.model_card_markdown_path || delivery.model_card_path, "model_card"],
    ["Approval package", delivery.approval_package_markdown_path || delivery.approval_package_path, "approval_package"],
    ...(delivery.approval_package_markdown_path && delivery.approval_package_path
      ? [["Approval package JSON", delivery.approval_package_path]]
      : []),
    ["Model report", delivery.report?.report_path],
    ["Monitoring policy", delivery.monitoring_policy_markdown_path || delivery.monitoring_policy_path],
    ["Champion comparison", delivery.challenger_comparison_markdown_path || delivery.challenger_comparison_path],
    ["Challenger/Backtest", delivery.challenger_task_id],
    ["Challenger / backtest package", delivery.challenger_package_markdown_path || delivery.challenger_package_path],
    ["Validation tasks", delivery.validation_task_id],
  ].filter(([, value]) => String(value || ""));
  if (!artifacts.length) return "";
  return `<div class="model-delivery-artifacts">${artifacts.map(([label, value, downloadKind]) => {
    const href = downloadKind ? taskArtifactDownloadUrl(value, taskId) : "";
    const downloadLabel = label === "PMML" ? "DownloadPMML" : `Download${label}`;
    return `<div><span>${escapeHtml(label)}</span><code>${escapeHtml(String(value))}</code>${href ? (
      `<a class="button compact secondary" data-model-delivery-download="${escapeHtml(downloadKind)}" href="${escapeHtml(href)}" download>${escapeHtml(downloadLabel)}</a>`
    ) : ""}</div>`;
  }).join("")}</div>`;
}

function taskArtifactDownloadUrl(value, taskId) {
  const relativePath = taskArtifactRelativePath(value, taskId);
  return relativePath ? `api/artifacts/${encodeURIComponent(relativePath)}` : "";
}

function taskArtifactRelativePath(value, taskId) {
  const safeTaskId = String(taskId || "").trim();
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(safeTaskId)) return "";
  const raw = String(value || "").trim().replaceAll("\\", "/");
  if (!raw) return "";
  const taskPrefix = `tasks/${safeTaskId}/`;
  const absoluteMarker = `/${taskPrefix}`;
  const markerIndex = raw.lastIndexOf(absoluteMarker);
  let relativePath = "";
  if (markerIndex >= 0) {
    relativePath = raw.slice(markerIndex + 1);
  } else if (raw.startsWith(taskPrefix)) {
    relativePath = raw;
  } else if (raw.startsWith("modeling_artifacts/")) {
    relativePath = `${taskPrefix}${raw}`;
  } else if (!raw.includes("/")) {
    relativePath = `${taskPrefix}modeling_artifacts/${raw}`;
  }
  const segments = relativePath.split("/");
  if (
    !relativePath.startsWith(taskPrefix)
    || segments.some((segment) => !segment || segment === "." || segment === "..")
  ) return "";
  return relativePath;
}

function reportSummary(report) {
  if (!report || typeof report !== "object") return "";
  const total = Number(report.total_sections || 0);
  const available = Number(report.available_sections || 0);
  const skipped = Number(report.skipped_sections || 0);
  const sections = Array.isArray(report.sections)
    ? report.sections.filter((item) => item && typeof item === "object").slice(0, 8)
    : [];
  const sectionHtml = sections.map((item) => (
    `<div class="model-delivery-report-section" data-available="${item.available ? "true" : "false"}">
      <span>${escapeHtml(String(item.section || "Untitled section"))}</span>
      <strong>${item.available ? "Generable" : "Missing input / skipped"}</strong>
      ${item.reason ? `<small>${escapeHtml(String(item.reason))}</small>` : ""}
    </div>`
  )).join("");
  return `<div class="model-delivery-report-summary">
    <div class="modeling-section-label">Report readiness</div>
    <div class="model-delivery-report-status">
      <strong>${escapeHtml(`${available}/${total || available} Sections to generate`)}</strong>
      <span>${skipped ? `${skipped} Sections with missing inputs or skipped` : "All report sections ready"}</span>
    </div>
    ${sectionHtml ? `<div class="model-delivery-report-grid">${sectionHtml}</div>` : ""}
  </div>`;
}

function readinessHeadline(items) {
  const rows = Array.isArray(items) ? items : [];
  if (!rows.length) return "Output status unavailable";
  const bad = rows.filter((item) => (
    ["unsupported", "skipped", "missing", "failed", "partial", "warn", "fail", "error"].includes(String(item?.status || "").toLowerCase())
  )).length;
  return bad ? `${bad} Issues to review / unsupported outputs` : "Outputs ready";
}

function sortedMetricKeys(keys) {
  return [...keys].sort((a, b) => {
    const ia = METRIC_ORDER.indexOf(a);
    const ib = METRIC_ORDER.indexOf(b);
    if (ia !== -1 || ib !== -1) return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    return a.localeCompare(b);
  });
}

function formatMetric(value) {
  const numeric = Number(value);
  if (Number.isFinite(numeric)) return Math.abs(numeric) >= 100 ? numeric.toFixed(2) : numeric.toFixed(4);
  return value === undefined || value === null || value === "" ? "-" : String(value);
}

function shortArtifact(value) {
  const raw = String(value || "");
  if (raw.length <= 72) return raw;
  return `...${raw.slice(-69)}`;
}

function statusKind(status) {
  const normalized = String(status || "").toLowerCase();
  if (["succeeded", "ready", "supported", "pass"].includes(normalized)) return "ready";
  if (["skipped", "unsupported", "missing", "partial", "warn", "needs_policy"].includes(normalized)) return "warning";
  if (["failed", "error", "fail"].includes(normalized)) return "error";
  return "neutral";
}

function signalKind(value) {
  const text = String(value || "").toLowerCase();
  if (["ready", "supported"].includes(text)) return "ready";
  if (["warning", "partial", "missing", "unsupported"].includes(text)) return "warning";
  if (["error", "failed"].includes(text)) return "error";
  if (["Steady.", "Transferable"].includes(String(value || ""))) return "ready";
  if (["Attention", "Review required", "High risk", "Clarification", "Native only", "Non-deliverable", "Confirmed", "Experimental candidate only"].includes(String(value || ""))) return "warning";
  if (text.includes("risk") || text.includes("High")) return "warning";
  return "neutral";
}

function policyDecisionKind(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "accepted") return "ready";
  if (normalized === "overridden") return "warning";
  if (normalized === "blocked") return "error";
  return "neutral";
}

function policyDecisionLabel(status) {
  const labels = {
    accepted: "Passed",
    overridden: "Manually overridden",
    blocked: "Blocked",
    not_requested: "Not requested",
  };
  return labels[String(status || "").toLowerCase()] || String(status || "Not assessed");
}

function statusLabel(status) {
  const normalized = String(status || "").toLowerCase();
  const labels = {
    succeeded: "Completed",
    ready: "Ready",
    supported: "Supported",
    pass: "Passed",
    warn: "Review required",
    skipped: "Skipped",
    unsupported: "Not supported",
    partial: "Partially completed",
    missing: "Missing",
    failed: "Failed",
    error: "Failed",
  };
  return labels[normalized] || (status ? String(status) : "Awaiting confirmation");
}
