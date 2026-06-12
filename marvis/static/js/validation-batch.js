export const validationBatchTaskType = "validation_batch";

const terminalBatchStatuses = new Set([
  "completed",
  "failed",
  "cancelled",
]);

const statusLabels = {
  created: "Not started",
  queued: "Queued",
  running: "Running",
  awaiting_confirmation: "Awaiting confirmation",
  review_required: "Manual review required",
  succeeded: "Passed",
  completed: "Completed",
  partial_failure: "Partially failed",
  failed: "Failed",
  cancelled: "Cancelled",
};

const stressLabels = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
};

const stageLabels = {
  queued: "Queued",
  created: "Not started",
  batch_created: "Not started",
  scan: "File review",
  input_confirmation: "Review field mapping",
  reproducibility: "Reproducibility",
  pmml_scoring: "PMML scoring",
  notebook: "Notebook execution",
  metrics: "Metric evaluation",
  word_conclusion_draft: "Report conclusions",
  word_conclusion_generated: "Report conclusions",
  report_conclusion: "Report conclusions",
  report: "Report generation",
  summary: "Summary",
  completed: "Completed",
  failure: "Failed",
};

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function textValue(value) {
  return value === null || value === undefined ? "" : String(value).trim();
}

function firstText(...values) {
  for (const value of values) {
    const normalized = textValue(value);
    if (normalized) return normalized;
  }
  return "";
}

function finiteNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const normalized = Number(value);
  return Number.isFinite(normalized) ? normalized : null;
}

function booleanValue(value) {
  return value === true || value === 1 || String(value).toLowerCase() === "true";
}

function safeLink(value) {
  const normalized = textValue(value);
  if (!normalized) return "";
  if (/^https?:\/\//i.test(normalized)) return normalized;
  if (/^\/(?!\/)/.test(normalized)) return normalized.slice(1);
  if (normalized.startsWith("?")) return normalized;
  return "";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function statusBucket(item) {
  const status = item.status;
  const outcome = item.outcome;
  if (["failed", "cancelled"].includes(status) || ["fail", "failed"].includes(outcome)) {
    return "failed";
  }
  if (["review_required", "awaiting_confirmation"].includes(status) || outcome === "manual_review") {
    return "awaitingConfirmation";
  }
  if (["succeeded", "completed"].includes(status) || outcome === "pass") return "succeeded";
  if (status === "running") return "running";
  return "queued";
}

function itemTone(item) {
  const bucket = statusBucket(item);
  if (bucket === "succeeded") return "success";
  if (bucket === "failed") return "danger";
  if (bucket === "running") return "running";
  if (bucket === "awaitingConfirmation") return "warning";
  return "neutral";
}

function normalizeBatchItem(rawItem, parentTaskId, fallbackOrdinal) {
  const item = objectValue(rawItem);
  const childTaskId = firstText(item.child_task_id, item.childTaskId, item.task_id, item.taskId);
  const itemId = firstText(item.id, item.item_id, item.itemId);
  const outcome = firstText(item.outcome, item.result).toLowerCase();
  const status = firstText(item.status, item.state, outcome || "queued").toLowerCase();
  const explicitManualUrl = safeLink(firstText(
    item.manual_review_url,
    item.manualReviewUrl,
    item.review_url,
  ));
  const manualReviewUrl = explicitManualUrl || (
    parentTaskId && childTaskId
      ? `?task=${encodeURIComponent(parentTaskId)}&item=${encodeURIComponent(childTaskId)}`
      : ""
  );
  return {
    id: itemId,
    parentTaskId,
    childTaskId,
    ordinal: Number.isInteger(Number(item.ordinal)) ? Number(item.ordinal) : fallbackOrdinal,
    modelName: firstText(item.model_name, item.modelName, item.name, `Model${fallbackOrdinal}`),
    modelVersion: firstText(item.model_version, item.modelVersion, item.version),
    status,
    stage: firstText(item.stage, item.current_stage, item.currentStage),
    inputContractStatus: firstText(
      item.input_contract_status,
      item.inputContractStatus,
    ).toLowerCase(),
    ootKs: finiteNumber(item.oot_ks ?? item.ootKs),
    ootPsi: finiteNumber(item.oot_psi ?? item.ootPsi),
    pmmlStatus: firstText(item.pmml_status, item.pmmlStatus).toLowerCase(),
    stressRisk: firstText(item.stress_risk, item.stressRisk).toLowerCase(),
    reportComplete: booleanValue(item.report_complete ?? item.reportComplete),
    outcome,
    errorCode: firstText(item.error_code, item.errorCode),
    errorMessage: firstText(
      item.error_message,
      item.errorMessage,
      item.failure_reason,
      item.failureReason,
      item.reason,
    ),
    contractUrl: safeLink(firstText(
      item.input_contract_url,
      item.inputContractUrl,
      item.validation_input_contract_url,
      item.contract_url,
      item.contractUrl,
    )),
    wordReportDownloadUrl: safeLink(firstText(
      item.word_report_download_url,
      item.wordReportDownloadUrl,
    )),
    analysisDownloadUrl: safeLink(firstText(
      item.analysis_download_url,
      item.analysisDownloadUrl,
    )),
    pendingReportDraft: booleanValue(item.pending_report_draft ?? item.pendingReportDraft),
    manualReviewUrl,
  };
}

export function parseTaskDeepLink(search = "") {
  const params = new URLSearchParams(String(search || "").replace(/^\?/, ""));
  return {
    taskId: textValue(params.get("task")),
    itemId: textValue(params.get("item")),
  };
}

export function preferredStartupTaskId(deepLink, storedTaskId = "") {
  return firstText(objectValue(deepLink).taskId, storedTaskId);
}

export function taskSelectionSearch(currentSearch, { taskId = "", itemId = "" } = {}) {
  const params = new URLSearchParams(String(currentSearch || "").replace(/^\?/, ""));
  const normalizedTaskId = textValue(taskId);
  const normalizedItemId = textValue(itemId);
  if (normalizedTaskId) {
    params.set("task", normalizedTaskId);
    if (normalizedItemId) params.set("item", normalizedItemId);
    else params.delete("item");
  } else {
    params.delete("task");
    params.delete("item");
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function syncTaskDeepLink(historyLike, locationLike, selection = {}) {
  if (!historyLike?.replaceState || !locationLike) return "";
  const nextSearch = taskSelectionSearch(locationLike.search, selection);
  const currentSearch = String(locationLike.search || "");
  if (nextSearch === currentSearch) return nextSearch;
  const path = locationLike.pathname || "/";
  const hash = locationLike.hash || "";
  try {
    historyLike.replaceState(historyLike.state, "", `${path}${nextSearch}${hash}`);
  } catch (_) {
    // Some embedded or sandboxed browsers block history mutation.
  }
  return nextSearch;
}

export function isValidationBatchTask(task) {
  return task?.task_type === validationBatchTaskType;
}

function formatLocalIsoDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatValidationBatchDate(value) {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return formatLocalIsoDate(value);
  }
  const raw = textValue(value);
  const parsed = raw ? new Date(raw) : new Date();
  if (Number.isNaN(parsed.getTime())) return formatLocalIsoDate(new Date());
  return formatLocalIsoDate(parsed);
}

export function formatValidationBatchTaskName(createdAt, itemCount) {
  const dateText = formatValidationBatchDate(createdAt);
  const count = Number(itemCount);
  if (Number.isInteger(count) && count > 0) {
    return `${dateText} Model validation batch (${count}Model)`;
  }
  return `${dateText} Model validation batch`;
}

export function usesAgentValidationWorkbench(task) {
  return isValidationBatchTask(task) && textValue(task?.run_mode).toLowerCase() === "agent";
}

export function resolveProjectedChildTaskId(batchPayload, requestedId = "") {
  const batch = batchPayload?.counts && Array.isArray(batchPayload?.items)
    ? batchPayload
    : normalizeValidationBatchPayload(batchPayload);
  const requested = textValue(requestedId);
  const match = (batch.items || []).find((item) => (
    item.childTaskId === requested || item.id === requested
  ));
  return match?.childTaskId || batch.items?.[0]?.childTaskId || "";
}

export function normalizeValidationBatchPayload(rawPayload = {}, fallbackParentTaskId = "") {
  const payload = objectValue(rawPayload);
  const batch = objectValue(payload.batch);
  const batchSource = Object.keys(batch).length ? batch : payload;
  const parentTaskId = firstText(
    batchSource.parent_task_id,
    batchSource.parentTaskId,
    batchSource.task_id,
    batchSource.taskId,
    fallbackParentTaskId,
  );
  const rawItems = Array.isArray(payload.items)
    ? payload.items
    : Array.isArray(payload.models)
      ? payload.models
      : Array.isArray(batchSource.items)
        ? batchSource.items
        : [];
  const items = rawItems
    .map((item, index) => normalizeBatchItem(item, parentTaskId, index + 1))
    .sort((left, right) => left.ordinal - right.ordinal);
  const declaredCount = Number(batchSource.item_count ?? batchSource.itemCount);
  const total = Number.isInteger(declaredCount) && declaredCount >= 0
    ? Math.max(declaredCount, items.length)
    : items.length;
  const counts = {
    total,
    queued: Math.max(0, total - items.length),
    running: 0,
    awaitingConfirmation: 0,
    succeeded: 0,
    failed: 0,
  };
  items.forEach((item) => {
    counts[statusBucket(item)] += 1;
  });
  return {
    parentTaskId,
    status: firstText(batchSource.status, batchSource.state, "created").toLowerCase(),
    errorMessage: firstText(
      batchSource.error_message,
      batchSource.errorMessage,
      batchSource.failure_reason,
    ),
    summaryDownloadUrl: safeLink(firstText(
      batchSource.summary_download_url,
      batchSource.summaryDownloadUrl,
      batchSource.download_url,
      payload.summary_download_url,
      payload.summaryDownloadUrl,
      payload.download_url,
    )),
    summaryPath: firstText(batchSource.summary_path, batchSource.summaryPath),
    createdAt: firstText(batchSource.created_at, batchSource.createdAt),
    updatedAt: firstText(batchSource.updated_at, batchSource.updatedAt),
    counts,
    items,
  };
}

function batchStatusLabel(status) {
  return statusLabels[status] || status || "Status unknown";
}

function metricText(value, { percent = false } = {}) {
  if (!Number.isFinite(value)) return "—";
  return percent ? `${(value * 100).toFixed(1)}%` : value.toFixed(4);
}

function itemStatusLabel(item) {
  return statusLabels[item.status] || statusLabels[item.outcome] || item.status || "Status unknown";
}

function itemStageLabel(item) {
  const stage = firstText(item?.stage);
  if (!stage) return "";
  return stageLabels[stage] || stage;
}

function itemProgressLabel(item) {
  const status = itemStatusLabel(item);
  const stage = itemStageLabel(item);
  const terminal = ["succeeded", "completed", "failed", "cancelled"].includes(item.status);
  if (!stage || terminal || stage === status || item.stage === item.status) return status;
  return `${status} · ${stage}`;
}

export function validationBatchItemNeedsContractConfirmation(item) {
  const contractStatus = firstText(
    item?.inputContractStatus,
    item?.input_contract_status,
  ).toLowerCase();
  if (contractStatus === "ready") return false;
  const status = textValue(item?.status).toLowerCase();
  return ["awaiting_confirmation", "pending", "pending_confirmation"].includes(status);
}

function remainingContractConfirmationCount(items, confirmedContractTaskIds) {
  return (items || []).filter((item) => (
    validationBatchItemNeedsContractConfirmation(item)
    && !confirmedContractTaskIds.has(item.childTaskId)
  )).length;
}

function pmmlLabel(value) {
  if (!value) return "—";
  if (value === "pass") return "Pass.";
  if (["fail", "failed"].includes(value)) return "Failed";
  return value;
}

function reportLabel(complete) {
  return complete ? "Complete" : "To be generated";
}

export function validationBatchStartAction(
  status,
  { inFlight = false, awaitingConfirmationCount = 0 } = {},
) {
  const normalized = textValue(status).toLowerCase();
  if (inFlight) {
    return { visible: true, disabled: true, label: "Submitting…" };
  }
  if (normalized === "created") {
    return { visible: true, disabled: false, label: "Start batch" };
  }
  if (normalized === "awaiting_confirmation") {
    return {
      visible: true,
      disabled: awaitingConfirmationCount > 0,
      label: "Continue after field review",
    };
  }
  if (normalized === "partial_failure") {
    return {
      visible: true,
      disabled: awaitingConfirmationCount > 0,
      label: "Continue unfinished models",
    };
  }
  if (normalized === "failed") {
    return {
      visible: true,
      disabled: awaitingConfirmationCount > 0,
      label: "Retry failed models",
    };
  }
  if (normalized === "running") {
    return { visible: true, disabled: true, label: "Batch running" };
  }
  return { visible: false, disabled: true, label: "" };
}

function itemLinksHtml(item, confirmedContractTaskIds = new Set()) {
  const links = [];
  const contractConfirmed = item.inputContractStatus === "ready"
    || confirmedContractTaskIds.has(item.childTaskId);
  if (contractConfirmed) {
    links.push('<span class="validation-batch-contract-confirmed">Fields confirmed</span>');
  } else if (item.childTaskId && validationBatchItemNeedsContractConfirmation(item)) {
    links.push(
      [
        '<button type="button" class="validation-batch-link validation-batch-contract-button"',
        ` data-batch-contract-task-id="${escapeHtml(item.childTaskId)}"`,
        ` data-batch-contract-item-id="${escapeHtml(item.id)}">Review field mapping</button>`,
      ].join(""),
    );
  }
  if (item.manualReviewUrl && statusBucket(item) !== "succeeded") {
    links.push(
      `<a class="validation-batch-link" href="${escapeHtml(item.manualReviewUrl)}">Manual review</a>`,
    );
  }
  if (item.wordReportDownloadUrl) {
    links.push(
      `<a class="validation-batch-link" href="${escapeHtml(item.wordReportDownloadUrl)}">Word</a>`,
    );
  }
  if (item.analysisDownloadUrl) {
    links.push(
      `<a class="validation-batch-link" href="${escapeHtml(item.analysisDownloadUrl)}">Excel</a>`,
    );
  }
  return links.length ? links.join("") : '<span class="validation-batch-muted">—</span>';
}

function itemRowHtml(item, requestedItemId, confirmedContractTaskIds) {
  const highlighted = requestedItemId
    && [item.childTaskId, item.id].includes(requestedItemId);
  const modelLabel = [item.modelName, item.modelVersion].filter(Boolean).join(" · ");
  const statusDetail = item.stage && item.stage !== item.status
    ? `<small>${escapeHtml(item.stage)}</small>`
    : "";
  const failure = item.errorMessage
    ? `<div class="validation-batch-error">${escapeHtml(item.errorMessage)}</div>`
    : "";
  return [
    `<tr class="validation-batch-row${highlighted ? " is-deep-linked" : ""}"`,
    ` data-batch-item-id="${escapeHtml(item.id)}"`,
    ` data-batch-child-task-id="${escapeHtml(item.childTaskId)}">`,
    `<td><strong>${escapeHtml(modelLabel)}</strong>${failure}</td>`,
    `<td><span class="validation-batch-status ${itemTone(item)}">${escapeHtml(itemStatusLabel(item))}</span>${statusDetail}</td>`,
    `<td class="numeric">${escapeHtml(metricText(item.ootKs, { percent: true }))}</td>`,
    `<td class="numeric">${escapeHtml(metricText(item.ootPsi))}</td>`,
    `<td>${escapeHtml(pmmlLabel(item.pmmlStatus))}</td>`,
    `<td>${escapeHtml(stressLabels[item.stressRisk] || item.stressRisk || "—")}</td>`,
    `<td>${escapeHtml(reportLabel(item.reportComplete))}</td>`,
    `<td><div class="validation-batch-links">${itemLinksHtml(item, confirmedContractTaskIds)}</div></td>`,
    "</tr>",
  ].join("");
}

export function validationBatchConfirmAllAction(
  batch,
  { inFlight = false } = {},
) {
  const items = batch?.items || [];
  const total = Number(batch?.counts?.total);
  if (!(total >= 2 || items.length >= 2)) {
    return { visible: false, disabled: true, label: "Confirm all reports" };
  }
  const actionable = items.filter((item) => !["failed", "cancelled"].includes(item.status));
  const pending = actionable.filter((item) => item.pendingReportDraft);
  const notReady = actionable.filter(
    (item) => !item.pendingReportDraft && !item.wordReportDownloadUrl,
  );
  const failed = items.filter((item) => item.status === "failed").length;
  const cancelled = items.filter((item) => item.status === "cancelled").length;
  const scope = [`${pending.length} Pending confirmation`, failed ? `${failed} failed` : "", cancelled ? `${cancelled} Cancelled` : "", notReady.length ? `${notReady.length} not ready` : ""].filter(Boolean).join(" · ");
  if (inFlight) {
    return { visible: true, disabled: true, label: "Generating all reports...", scope };
  }
  return {
    visible: true,
    disabled: pending.length === 0 || notReady.length > 0,
    label: "Confirm all reports",
    scope,
    title: notReady.length > 0
      ? "Some models have not finished drafting report conclusions."
      : pending.length === 0
        ? "No report drafts await confirmation."
        : `Confirm ${pending.length} report drafts and generate their documents. Failed and cancelled models are excluded.`,
  };
}

export function renderValidationBatchSwitcher(
  batchPayload,
  { selectedChildTaskId = "", confirmAllInFlight = false } = {},
) {
  const batch = batchPayload?.counts && Array.isArray(batchPayload?.items)
    ? batchPayload
    : normalizeValidationBatchPayload(batchPayload);
  const selected = textValue(selectedChildTaskId) || batch.items[0]?.childTaskId || "";
  const buttons = (batch.items || []).map((item) => {
    const isSelected = item.childTaskId === selected;
    const tone = itemTone(item);
    const progress = itemProgressLabel(item);
    const version = item.modelVersion ? ` · ${item.modelVersion}` : "";
    return [
      `<button type="button" class="validation-batch-switcher-item${isSelected ? " is-selected" : ""}"`,
      ` data-tone="${escapeHtml(tone)}"`,
      ` data-batch-switch-child="${escapeHtml(item.childTaskId)}"`,
      ` role="radio" aria-checked="${isSelected ? "true" : "false"}" tabindex="${isSelected ? "0" : "-1"}">`,
      `<span class="validation-batch-switcher-name">${escapeHtml(item.modelName || `Model${item.ordinal}`)}${escapeHtml(version)}</span>`,
      `<small class="validation-batch-switcher-progress">${escapeHtml(progress)}</small>`,
      "</button>",
    ].join("");
  }).join("");
  const showSummary = Number(batch.counts.total) >= 2;
  const confirmAll = validationBatchConfirmAllAction(batch, { inFlight: confirmAllInFlight });
  const confirmAllAction = confirmAll.visible
    ? [
      `<button type="button" class="button compact primary" data-batch-confirm-all="true"`,
      confirmAll.disabled ? ' disabled aria-disabled="true"' : "",
      confirmAll.title ? ` title="${escapeHtml(confirmAll.title)}"` : "",
      `>${escapeHtml(confirmAll.label)}</button>`,
      `<span class="validation-batch-confirm-scope" role="status">${escapeHtml(confirmAll.scope || "")}</span>`,
    ].join("")
    : "";
  const summaryAction = !showSummary
    ? ""
    : batch.summaryDownloadUrl
      ? `<a class="button compact validation-batch-download" href="${escapeHtml(batch.summaryDownloadUrl)}">Download summary workbook</a>`
      : "";
  const actions = confirmAllAction || summaryAction
    ? `<div class="validation-batch-switcher-actions">${confirmAllAction}${summaryAction}</div>`
    : "";
  return [
    '<div class="validation-batch-switcher" aria-label="Current validation model">',
    `<div class="validation-batch-switcher-list" role="radiogroup" aria-label="Select Authentication Model">${buttons}</div>`,
    actions,
    "</div>",
  ].join("");
}

export function renderValidationBatchOverview(
  batchPayload,
  {
    requestedItemId = "",
    startInFlight = false,
    confirmedContractTaskIds = new Set(),
  } = {},
) {
  const batch = batchPayload?.counts && Array.isArray(batchPayload?.items)
    ? batchPayload
    : normalizeValidationBatchPayload(batchPayload);
  const awaitingConfirmationCount = remainingContractConfirmationCount(
    batch.items,
    confirmedContractTaskIds,
  );
  const startAction = validationBatchStartAction(batch.status, {
    inFlight: startInFlight,
    awaitingConfirmationCount,
  });
  const startActionHtml = startAction.visible
    ? [
      `<button type="button" class="button compact primary" data-batch-start="true"`,
      startAction.disabled ? ' disabled aria-disabled="true"' : "",
      `>${escapeHtml(startAction.label)}</button>`,
    ].join("")
    : "";
  const showSummary = Number(batch.counts.total) >= 2;
  const summaryAction = !showSummary
    ? ""
    : batch.summaryDownloadUrl
    ? `<a class="button compact validation-batch-download" href="${escapeHtml(batch.summaryDownloadUrl)}">Download summary workbook</a>`
    : '<span class="validation-batch-summary-pending" aria-disabled="true">Summary not available yet</span>';
  const rows = batch.items.length
    ? batch.items
      .map((item) => itemRowHtml(item, requestedItemId, confirmedContractTaskIds))
      .join("")
    : '<tr><td class="validation-batch-empty" colspan="8">Preparing batch items. Refresh to check their status.</td></tr>';
  const batchError = batch.errorMessage
    ? `<p class="validation-batch-banner-error" role="alert">${escapeHtml(batch.errorMessage)}</p>`
    : "";
  const contractGuidance = batch.status === "awaiting_confirmation"
    ? [
      '<p class="validation-batch-contract-guidance">',
      "Review the detected field mappings in the conversation. Include the model name and field when requesting a correction. ",
      "You can also review each model using its field mapping form.",
      "</p>",
    ].join("")
    : "";
  return [
    '<div class="validation-batch-overview">',
    '<header class="validation-batch-head">',
    '<div><p class="validation-batch-eyebrow">MODEL VALIDATION BATCH</p>',
    '<div class="validation-batch-title-line"><h3>Batch overview</h3>',
    `<span class="validation-batch-status ${escapeHtml(batch.status)}">${escapeHtml(batchStatusLabel(batch.status))}</span></div>`,
    `<p>${escapeHtml(batch.counts.total)} models · Each model runs independently</p></div>`,
    '<div class="validation-batch-head-actions">',
    '<button type="button" class="button compact secondary" data-batch-refresh="true">Refresh batch</button>',
    startActionHtml,
    summaryAction,
    "</div></header>",
    batchError,
    contractGuidance,
    '<div class="validation-batch-stats" aria-label="Batch status summary">',
    `<div><strong>${escapeHtml(batch.counts.total)}</strong><span>Models</span></div>`,
    `<div><strong>${escapeHtml(batch.counts.running)}</strong><span>Running</span></div>`,
    `<div><strong>${escapeHtml(batch.counts.awaitingConfirmation)}</strong><span>Awaiting review</span></div>`,
    `<div><strong>${escapeHtml(batch.counts.succeeded)}</strong><span>Passed</span></div>`,
    `<div><strong>${escapeHtml(batch.counts.failed)}</strong><span>Failed</span></div>`,
    "</div>",
    '<div class="validation-batch-table-wrap"><table class="validation-batch-table">',
    '<thead><tr><th>Model</th><th>Status / stage</th><th>OOT KS</th><th>OOT PSI</th><th>PMML</th><th>Stress risk</th><th>Report</th><th>Actions</th></tr></thead>',
    `<tbody>${rows}</tbody>`,
    "</table></div></div>",
  ].join("");
}

export function focusValidationBatchItem(panel, requestedItemId) {
  const normalizedItemId = textValue(requestedItemId);
  const rows = Array.from(panel?.querySelectorAll?.("[data-batch-child-task-id]") || []);
  let target = null;
  rows.forEach((row) => {
    const matches = Boolean(normalizedItemId) && (
      row.dataset?.batchChildTaskId === normalizedItemId
      || row.dataset?.batchItemId === normalizedItemId
    );
    row.classList?.toggle
      ? row.classList.toggle("is-deep-linked", matches)
      : matches
        ? row.classList?.add?.("is-deep-linked")
        : row.classList?.remove?.("is-deep-linked");
    if (matches) target = row;
  });
  if (!target) return false;
  target.scrollIntoView?.({ block: "center", behavior: "smooth" });
  return true;
}

export function createValidationBatchPanelController({
  api,
  getElementById,
  getSelectedTask,
  deepLink = {},
  confirmStart = async () => false,
  openContract = async () => {},
  refreshParentTask = async () => true,
  onError = () => {},
  onRecovered = () => {},
  onProjectedChildChange = () => {},
  onLayoutChange = () => {},
  onBatchMeta = () => {},
  confirmAllReportDrafts = async () => {},
  schedulePoll = (callback, delay) => setTimeout(callback, delay),
  cancelPoll = (handle) => clearTimeout(handle),
  pollIntervalMs = 1500,
}) {
  let activeTaskId = "";
  let currentPayload = null;
  let requestVersion = 0;
  let startInFlight = false;
  let confirmAllInFlight = false;
  let pollHandle = null;
  let detailLoadErrorMessage = "";
  const confirmedContractTaskIds = new Set();
  const boundHosts = new Set();
  const initialTaskId = textValue(deepLink.taskId);
  const initialItemId = textValue(deepLink.itemId);
  let selectedChildTaskId = initialItemId;
  let lastNotifiedItemCount;

  function panelElement() {
    return getElementById("batchOverviewPanel");
  }

  function switcherHost() {
    const host = getElementById("validationBatchSwitcher");
    const panel = panelElement();
    return host && host !== panel ? host : null;
  }

  function usesHeroSwitcher() {
    return Boolean(switcherHost()) && usesAgentValidationWorkbench(getSelectedTask());
  }

  function notifyLayout() {
    try {
      onLayoutChange();
    } catch (_) {
      // Layout sync is presentational.
    }
  }

  function notifyBatchMeta() {
    if (!currentPayload) return;
    const itemCount = currentPayload.counts?.total;
    if (lastNotifiedItemCount === itemCount) return;
    lastNotifiedItemCount = itemCount;
    try {
      onBatchMeta({
        itemCount,
        createdAt: currentPayload.createdAt,
      });
    } catch (_) {
      // Title stamping is presentational.
    }
  }

  function setHostVisible(host, visible) {
    if (!host) return;
    host.classList?.toggle("hidden", !visible);
    host.toggleAttribute?.("hidden", !visible);
    host.setAttribute?.("aria-hidden", visible ? "false" : "true");
  }

  function requestedItemId() {
    return activeTaskId && activeTaskId === initialTaskId ? initialItemId : "";
  }

  function setVisible(visible) {
    const isBatch = Boolean(visible) && isValidationBatchTask(getSelectedTask());
    const heroSwitcher = usesHeroSwitcher();
    setHostVisible(panelElement(), isBatch && !heroSwitcher);
    setHostVisible(switcherHost(), isBatch && heroSwitcher);
    notifyLayout();
  }

  function renderLoading() {
    const loadingHtml = usesHeroSwitcher()
      ? '<div class="validation-batch-switcher-loading" role="status">Loading model status…</div>'
      : '<div class="validation-batch-loading" role="status">Loading batch status…</div>';
    const host = usesHeroSwitcher() ? switcherHost() : panelElement();
    if (host) host.innerHTML = loadingHtml;
  }

  function renderError(message) {
    const errorHtml = [
      '<div class="validation-batch-load-error" role="alert">',
      `<strong>Could not load batch status</strong><span>${escapeHtml(message || "Please try again later.")}</span>`,
      '<button type="button" class="button compact secondary" data-batch-refresh="true">Reload</button>',
      "</div>",
    ].join("");
    const host = usesHeroSwitcher() ? switcherHost() : panelElement();
    if (host) host.innerHTML = errorHtml;
  }

  function renderCurrent() {
    const panel = panelElement();
    const switcher = switcherHost();
    if (!currentPayload) return;
    if (usesAgentValidationWorkbench(getSelectedTask())) {
      selectedChildTaskId = resolveProjectedChildTaskId(currentPayload, selectedChildTaskId);
      const html = renderValidationBatchSwitcher(currentPayload, {
        selectedChildTaskId,
        confirmAllInFlight,
      });
      if (switcher) {
        switcher.innerHTML = html;
        if (panel) panel.innerHTML = "";
      } else if (panel) {
        panel.innerHTML = html;
      }
      notifyBatchMeta();
      notifyLayout();
      return;
    }
    if (switcher) switcher.innerHTML = "";
    if (!panel) return;
    panel.innerHTML = renderValidationBatchOverview(currentPayload, {
      requestedItemId: requestedItemId(),
      startInFlight,
      confirmedContractTaskIds,
    });
    notifyBatchMeta();
    notifyLayout();
  }

  function notifyProjectedChild({ force = false } = {}) {
    const childTaskId = resolveProjectedChildTaskId(currentPayload, selectedChildTaskId);
    selectedChildTaskId = childTaskId;
    if (!activeTaskId || !childTaskId) return;
    try {
      onProjectedChildChange({
        parentTaskId: activeTaskId,
        childTaskId,
        item: currentPayload?.items?.find((candidate) => candidate.childTaskId === childTaskId) || null,
        force,
      });
    } catch (_) {
      // Projection is presentational; batch detail remains authoritative.
    }
  }

  function clearScheduledPoll() {
    if (pollHandle === null) return;
    cancelPoll(pollHandle);
    pollHandle = null;
  }

  function scheduleParentRefreshRetry(taskId) {
    clearScheduledPoll();
    if (!activeTaskId || activeTaskId !== taskId) return;
    pollHandle = schedulePoll(async () => {
      pollHandle = null;
      if (!activeTaskId || activeTaskId !== taskId) return;
      try {
        const synchronized = await refreshParentTask({ parentTaskId: taskId });
        if (synchronized === false) scheduleParentRefreshRetry(taskId);
      } catch (_) {
        scheduleParentRefreshRetry(taskId);
      }
    }, pollIntervalMs);
  }

  function scheduleCurrentPoll() {
    clearScheduledPoll();
    if (!activeTaskId || !currentPayload) return;
    const workbench = usesAgentValidationWorkbench(getSelectedTask());
    const items = currentPayload.items || [];
    const unfinished = items.some((item) => (
      !["succeeded", "failed", "cancelled", "completed"].includes(item.status)
    ));
    if (workbench) {
      if (!unfinished) return;
    } else if (currentPayload.status !== "running") {
      return;
    }
    const taskId = activeTaskId;
    pollHandle = schedulePoll(async () => {
      pollHandle = null;
      if (!activeTaskId || activeTaskId !== taskId) return;
      const payload = await selectTask(getSelectedTask(), { force: true });
      if (!activeTaskId || activeTaskId !== taskId) return;
      let parentSynchronized = true;
      try {
        parentSynchronized = await refreshParentTask({ parentTaskId: taskId });
      } catch (_) {
        parentSynchronized = false;
      }
      if (
        payload
        && payload.status !== "running"
        && parentSynchronized === false
      ) {
        scheduleParentRefreshRetry(taskId);
      }
    }, pollIntervalMs);
  }

  async function selectTask(task, { force = false } = {}) {
    if (!isValidationBatchTask(task)) {
      clear();
      return null;
    }
    const taskId = textValue(task.id);
    if (!taskId) {
      clear();
      return null;
    }
    setVisible(true);
    if (!force && activeTaskId === taskId && currentPayload) {
      renderCurrent();
      scheduleCurrentPoll();
      notifyProjectedChild({ force: false });
      return currentPayload;
    }
    if (activeTaskId && activeTaskId !== taskId) {
      confirmedContractTaskIds.clear();
      detailLoadErrorMessage = "";
      selectedChildTaskId = taskId === initialTaskId ? initialItemId : "";
      lastNotifiedItemCount = undefined;
    }
    const previousPayload = activeTaskId === taskId ? currentPayload : null;
    activeTaskId = taskId;
    const version = ++requestVersion;
    if (!previousPayload) {
      currentPayload = null;
      renderLoading();
    }
    try {
      const raw = await api(`api/validation-batches/${encodeURIComponent(taskId)}`);
      if (version !== requestVersion || activeTaskId !== taskId) return null;
      const recoveredMessage = detailLoadErrorMessage;
      detailLoadErrorMessage = "";
      confirmedContractTaskIds.clear();
      currentPayload = normalizeValidationBatchPayload(raw, taskId);
      selectedChildTaskId = resolveProjectedChildTaskId(
        currentPayload,
        selectedChildTaskId || requestedItemId(),
      );
      renderCurrent();
      notifyProjectedChild({ force });
      focusRequestedItem();
      scheduleCurrentPoll();
      if (recoveredMessage) {
        try {
          onRecovered({ parentTaskId: taskId, message: recoveredMessage });
        } catch (_) {
          // Status restoration is presentational and must not restart polling.
        }
      }
      return currentPayload;
    } catch (error) {
      if (version !== requestVersion || activeTaskId !== taskId) return null;
      const message = error?.message || "Please try again later.";
      const shouldRetry = currentPayload?.status === "running";
      detailLoadErrorMessage = message;
      renderError(message);
      onError(message);
      if (shouldRetry) scheduleCurrentPoll();
      return null;
    }
  }

  function renderVisibility(task = getSelectedTask()) {
    setVisible(isValidationBatchTask(task));
  }

  function focusRequestedItem() {
    return focusValidationBatchItem(panelElement(), requestedItemId());
  }

  async function startOrContinue() {
    const awaitingConfirmationCount = remainingContractConfirmations();
    const action = validationBatchStartAction(currentPayload?.status, {
      inFlight: startInFlight,
      awaitingConfirmationCount,
    });
    if (!activeTaskId || !currentPayload || !action.visible || action.disabled) return false;
    const parentTaskId = activeTaskId;
    const confirmed = await confirmStart({
      parentTaskId,
      status: currentPayload.status,
      itemCount: currentPayload.counts.total,
      awaitingConfirmationCount: remainingContractConfirmations(),
    });
    if (!confirmed || activeTaskId !== parentTaskId) return false;
    startInFlight = true;
    let startFailed = false;
    clearScheduledPoll();
    renderCurrent();
    try {
      try {
        await api(`api/validation-batches/${encodeURIComponent(parentTaskId)}/start`, {
          method: "POST",
          body: JSON.stringify({}),
        });
      } catch (error) {
        startFailed = true;
        const message = error?.message || "Could not start the batch. Try again.";
        renderError(message);
        onError(message);
        return false;
      }
      if (activeTaskId === parentTaskId && currentPayload) {
        currentPayload = { ...currentPayload, status: "running" };
        renderCurrent();
      }
      try {
        await refreshParentTask();
      } catch (_) {
        // The accepted start request is the commit boundary. Shared task-list
        // refresh is best-effort; batch detail polling remains authoritative.
      }
      if (activeTaskId !== parentTaskId) return true;
      const currentTask = getSelectedTask();
      await selectTask(
        isValidationBatchTask(currentTask)
          ? currentTask
          : { id: parentTaskId, task_type: validationBatchTaskType },
        { force: true },
      );
      return true;
    } finally {
      startInFlight = false;
      if (!startFailed && currentPayload && activeTaskId === parentTaskId) {
        renderCurrent();
        scheduleCurrentPoll();
      }
    }
  }

  async function openItemContract(button) {
    const parentTaskId = activeTaskId;
    const childTaskId = textValue(button?.dataset?.batchContractTaskId);
    const itemId = textValue(button?.dataset?.batchContractItemId);
    const item = currentPayload?.items?.find((candidate) => (
      candidate.childTaskId === childTaskId
      && (!itemId || candidate.id === itemId)
    ));
    if (
      !parentTaskId
      || !childTaskId
      || !item
      || !validationBatchItemNeedsContractConfirmation(item)
    ) return false;
    try {
      await openContract({
        parentTaskId,
        childTaskId,
        itemId: item.id,
        modelName: item.modelName,
        modelVersion: item.modelVersion,
      });
      return activeTaskId === parentTaskId;
    } catch (error) {
      onError(error?.message || "Could not load the field mapping. Try again.");
      return false;
    }
  }

  function remainingContractConfirmations() {
    return remainingContractConfirmationCount(
      currentPayload?.items,
      confirmedContractTaskIds,
    );
  }

  function markContractConfirmed(childTaskId) {
    const normalizedTaskId = textValue(childTaskId);
    if (normalizedTaskId) confirmedContractTaskIds.add(normalizedTaskId);
    renderCurrent();
    return remainingContractConfirmations();
  }

  function clear() {
    requestVersion += 1;
    clearScheduledPoll();
    activeTaskId = "";
    currentPayload = null;
    startInFlight = false;
    confirmAllInFlight = false;
    detailLoadErrorMessage = "";
    selectedChildTaskId = initialItemId;
    lastNotifiedItemCount = undefined;
    confirmedContractTaskIds.clear();
    const panel = panelElement();
    const switcher = switcherHost();
    setVisible(false);
    if (panel) panel.innerHTML = "";
    if (switcher) switcher.innerHTML = "";
  }

  function handleBatchClick(event) {
    if (event.target?.closest?.("[data-batch-start]")) {
      void startOrContinue();
      return;
    }
    if (event.target?.closest?.("[data-batch-refresh]")) {
      void selectTask(getSelectedTask(), { force: true });
      return;
    }
    if (event.target?.closest?.("[data-batch-confirm-all]")) {
      void confirmAll();
      return;
    }
    const switchButton = event.target?.closest?.("[data-batch-switch-child]");
    if (switchButton) {
      const nextChild = textValue(switchButton.dataset.batchSwitchChild);
      if (nextChild && nextChild !== selectedChildTaskId) {
        selectedChildTaskId = nextChild;
        renderCurrent();
        notifyProjectedChild({ force: true });
      }
      return;
    }
    const contractButton = event.target?.closest?.("[data-batch-contract-task-id]");
    if (contractButton) {
      void openItemContract(contractButton);
    }
  }

  async function confirmAll() {
    const parentTaskId = currentPayload?.parentTaskId || activeTaskId;
    if (!parentTaskId || confirmAllInFlight) return;
    const action = validationBatchConfirmAllAction(currentPayload, { inFlight: false });
    if (!action.visible || action.disabled) return;
    confirmAllInFlight = true;
    renderCurrent();
    try {
      await confirmAllReportDrafts({ parentTaskId });
      await selectTask(getSelectedTask(), { force: true });
    } catch (error) {
      onError(error?.message || "Could not confirm the report drafts. Try again.");
    } finally {
      confirmAllInFlight = false;
      renderCurrent();
    }
  }

  function handleSwitcherWheel(event) {
    const list = event.target?.closest?.(".validation-batch-switcher-list");
    if (!list) return;
    if (list.scrollWidth <= list.clientWidth + 1) return;
    if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
    event.preventDefault();
    list.scrollLeft += event.deltaY;
  }

  function bindHost(host) {
    if (!host || boundHosts.has(host)) return;
    boundHosts.add(host);
    host.addEventListener("click", handleBatchClick);
    host.addEventListener("wheel", handleSwitcherWheel, { passive: false });
    host.addEventListener("keydown", (event) => {
      const current = event.target?.closest?.("[data-batch-switch-child]");
      if (!current || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
      const buttons = [...host.querySelectorAll("[data-batch-switch-child]")];
      const index = buttons.indexOf(current);
      const next = event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1
        : (index + (["ArrowLeft", "ArrowUp"].includes(event.key) ? -1 : 1) + buttons.length) % buttons.length;
      event.preventDefault();
      const childId = buttons[next].dataset.batchSwitchChild;
      selectChild(childId);
      [...host.querySelectorAll("[data-batch-switch-child]")].find((button) => button.dataset.batchSwitchChild === childId)?.focus();
    });
  }

  function selectChild(childTaskId) {
    const nextId = textValue(childTaskId);
    if (!nextId) return;
    selectedChildTaskId = currentPayload
      ? resolveProjectedChildTaskId(currentPayload, nextId)
      : nextId;
    if (currentPayload) renderCurrent();
    notifyProjectedChild({ force: true });
  }

  bindHost(panelElement());
  bindHost(switcherHost());

  return {
    clear,
    focusRequestedItem,
    markContractConfirmed,
    remainingContractConfirmations,
    renderVisibility,
    selectTask,
    selectChild,
    openItemContract,
    startOrContinue,
    statusIsTerminal: (status) => terminalBatchStatuses.has(textValue(status).toLowerCase()),
  };
}
