import { escapeHtml } from "./ui-utils.js";

export const REPORT_DRAFT_FIELDS = [
  {
    key: "TEXT:final_validation_conclusion",
    label: "Final validation conclusion",
    long: true,
  },
  {
    key: "TEXT:pressure_test_summary",
    label: "Stress test summary",
    long: true,
  },
  {
    key: "TEXT:pressure_impact_recommendation",
    label: "Stress response recommendations",
    long: true,
  },
  {
    key: "TEXT:model_overview",
    label: "Model overview",
    long: true,
  },
  {
    key: "TEXT:model_scope",
    label: "Model scope",
    long: false,
  },
  {
    key: "TEXT:sample_audience",
    label: "Sample population",
    long: false,
  },
  {
    key: "TEXT:bad_sample_definition",
    label: "Adverse outcome definition",
    long: false,
  },
  {
    key: "TEXT:good_sample_definition",
    label: "Non-adverse outcome definition",
    long: false,
  },
  {
    key: "TEXT:model_training_description",
    label: "Model training notes",
    long: true,
  },
];

const REQUIRED_REPORT_DRAFT_KEYS = [
  "TEXT:pressure_test_summary",
  "TEXT:pressure_impact_recommendation",
  "TEXT:final_validation_conclusion",
];

export function latestPendingReportDraftMessageId(messages = []) {
  if (!Array.isArray(messages)) return "";
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.stage === "word_conclusion_confirmed") return "";
    if (message?.role !== "assistant") continue;
    if (message?.stage !== "word_conclusion_draft") continue;
    if (!hasReportDraftValues(message?.metadata?.draft_values)) continue;
    return String(message.id || "");
  }
  return "";
}

export function hasReportDraftValues(values) {
  return Boolean(values) && typeof values === "object" && !Array.isArray(values)
    && Object.keys(values).length > 0;
}

export function collectReportDraftValues(root) {
  const values = {};
  if (!root?.querySelectorAll) return values;
  root.querySelectorAll("[data-report-draft-key]").forEach((field) => {
    const key = field.getAttribute("data-report-draft-key");
    if (!key) return;
    values[key] = String(field.value || "");
  });
  return values;
}

export function reportDraftHasRequiredValues(values = {}) {
  return REQUIRED_REPORT_DRAFT_KEYS.every((key) => String(values[key] || "").trim());
}

export function reportDraftTableHtml(
  values = {},
  {
    editable = false,
    revision = 0,
    messageId = "",
    taskId = "",
    state = null,
  } = {},
) {
  const rows = REPORT_DRAFT_FIELDS.map((field) => reportDraftRowHtml(
    field,
    String(values[field.key] || ""),
    editable,
    Boolean(state?.confirming),
  )).join("");
  const revisionValue = Number.isFinite(Number(revision)) ? Number(revision) : 0;
  const messageAttr = messageId
    ? ` data-report-draft-message-id="${escapeHtml(String(messageId))}"`
    : "";
  const confirmHtml = editable
    ? [
      '<footer class="report-draft-actions">',
      `<button type="button" class="button compact secondary" data-report-draft-save${state?.confirming ? " disabled" : ""}>Save draft</button>`,
      `<button type="button" class="button compact primary" data-report-draft-confirm${state?.conflict || state?.confirming ? " disabled" : ""}>`,
      "Confirm and generate reports",
      "</button>",
      "</footer>",
    ].join("")
    : "";
  return [
    `<section class="report-draft-panel" data-report-draft-table="true"${messageAttr}`,
    ` data-report-draft-task-id="${escapeHtml(taskId)}"`,
    ` data-report-revision="${escapeHtml(String(revisionValue))}"`,
    ` data-report-draft-editable="${editable ? "true" : "false"}">`,
    '<header class="report-draft-head">',
    "<h3>Report conclusions</h3>",
    editable
      ? '<p>Changes are saved automatically. Confirm the draft to generate Word and Excel reports.</p><span class="report-draft-save-status" role="status" aria-live="polite" data-report-draft-save-status>' + escapeHtml(state?.status || "Draft") + '</span>'
      : "<p>The draft has been confirmed or replaced by an updated version.</p>",
    "</header>",
    '<div data-report-draft-feedback>' + reportDraftFeedbackHtml(state) + '</div>',
    confirmHtml,
    '<div class="report-draft-table-wrap"><table class="report-draft-table">',
    "<thead><tr><th>Section</th><th>Content</th></tr></thead>",
    `<tbody>${rows}</tbody>`,
    "</table></div>",
    '<details class="report-draft-mapping"><summary>Template field mapping</summary>',
    REPORT_DRAFT_FIELDS.map((field) => `<div>${escapeHtml(field.label)} <code>${escapeHtml(field.key)}</code></div>`).join(""),
    '</details>',
    "</section>",
  ].join("");
}

function reportDraftRowHtml(field, value, editable, confirming) {
  const control = editable
    ? reportDraftControlHtml(field, value, confirming)
    : `<div class="report-draft-readonly">${escapeHtml(value) || "—"}</div>`;
  return [
    "<tr>",
    "<th scope=\"row\">",
    `<span class="report-draft-label">${escapeHtml(field.label)}</span>`,
    editable ? `<button type="button" class="report-draft-revise" data-report-draft-revise="${escapeHtml(field.label)}"${confirming ? " disabled" : ""}>Request revision</button>` : "",
    "</th>",
    `<td>${control}</td>`,
    "</tr>",
  ].join("");
}

export function reportDraftFeedbackHtml(state) {
  if (!state) return "";
  const error = state.error ? `<p role="alert">${escapeHtml(state.error)}</p>` : "";
  if (!state.conflict) return error;
  if (state.conflict.unavailable) return error + '<p>This draft is no longer editable. Copy any unsaved changes, then request a new draft in the conversation.</p>';
  const differences = REPORT_DRAFT_FIELDS.filter((field) =>
    String(state.values[field.key] || "") !== String(state.conflict.values[field.key] || ""));
  return error + '<details class="report-draft-conflict" open><summary>Resolve conflicting changes before saving</summary>'
    + differences.map((field) => `<div><strong>${escapeHtml(field.label)}</strong><p>Your changes: ${escapeHtml(state.values[field.key] || "(empty)")}</p><p>Saved version: ${escapeHtml(state.conflict.values[field.key] || "(empty)")}</p></div>`).join("")
    + '<button type="button" class="button compact secondary" data-report-draft-resolve="server">Use saved version</button> '
    + '<button type="button" class="button compact secondary" data-report-draft-resolve="local">Keep my changes</button></details>';
}

function reportDraftControlHtml(field, value, confirming) {
  const keyAttr = escapeHtml(field.key);
  const labelAttr = escapeHtml(field.label);
  const valueAttr = escapeHtml(value);
  if (field.long) {
    return [
      `<textarea class="report-draft-input" data-report-draft-key="${keyAttr}"`,
      ` aria-label="${labelAttr}" placeholder="Enter content" rows="4"${confirming ? " readonly" : ""}>${valueAttr}</textarea>`,
    ].join("");
  }
  return [
    `<input class="report-draft-input" data-report-draft-key="${keyAttr}"`,
    ` aria-label="${labelAttr}" placeholder="Enter content" type="text" value="${valueAttr}"${confirming ? " readonly" : ""}>`,
  ].join("");
}
