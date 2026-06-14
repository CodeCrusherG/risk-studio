import { escapeHtml } from "../ui-utils.js";

function isRecord(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function cleanText(value) {
  return value === undefined || value === null ? "" : String(value).trim();
}

function escapedText(value) {
  return escapeHtml(value === undefined || value === null ? "" : String(value));
}

function diagnosticFactsHtml(diagnostic) {
  const facts = [];
  const location = cleanText(diagnostic.location);
  if (location) facts.push({ label: "Error location", value: location });
  if (Array.isArray(diagnostic.evidence)) {
    diagnostic.evidence.forEach((item) => {
      if (!isRecord(item)) return;
      const value = cleanText(item.value);
      if (!value) return;
      facts.push({ label: cleanText(item.label) || "Diagnostic evidence", value });
    });
  }
  if (!facts.length) return "";
  return [
    '<dl class="workflow-error-card__facts">',
    ...facts.map(({ label, value }) => [
      '<div class="workflow-error-card__fact">',
      `<dt>${escapeHtml(label)}</dt>`,
      `<dd>${escapeHtml(value)}</dd>`,
      "</div>",
    ].join("")),
    "</dl>",
  ].join("");
}

function diagnosticActionsHtml(actions) {
  const items = Array.isArray(actions)
    ? actions.map(cleanText).filter(Boolean)
    : [];
  if (!items.length) return "";
  return [
    '<div class="workflow-error-card__section">',
    "<h4>Step details</h4>",
    '<ol class="workflow-error-card__actions">',
    ...items.map((item) => `<li>${escapeHtml(item)}</li>`),
    "</ol>",
    "</div>",
  ].join("");
}

function diagnosticTechnicalHtml(diagnostic) {
  const code = cleanText(diagnostic.code);
  const workflow = cleanText(diagnostic.workflow);
  const detail = cleanText(diagnostic.technical_detail);
  const rows = [
    code ? `<div><dt>Error code</dt><dd><code>${escapeHtml(code)}</code></dd></div>` : "",
    workflow ? `<div><dt>Workstream</dt><dd>${escapeHtml(workflow)}</dd></div>` : "",
  ].filter(Boolean).join("");
  return [
    '<details class="workflow-error-card__technical">',
    "<summary>Technical details</summary>",
    rows ? `<dl>${rows}</dl>` : "",
    detail
      ? `<pre><code>${escapeHtml(detail)}</code></pre>`
      : '<p class="workflow-error-card__technical-empty">No further technical information is available.</p>',
    "</details>",
  ].join("");
}

function diagnosticRecoveryHtml(diagnostic) {
  const prompt = cleanText(diagnostic.agent_prompt);
  const actions = Array.isArray(diagnostic.recovery_actions)
    ? diagnostic.recovery_actions.filter(isRecord)
    : [];
  if (!prompt && !actions.length) return "";
  return [
    '<div class="workflow-error-card__recovery">',
    prompt ? `<p>${escapeHtml(prompt)}</p>` : "",
    actions.length ? '<div class="workflow-error-card__recovery-actions">' : "",
    ...actions.map((action) => {
      const label = cleanText(action.label) || "Continue";
      const command = cleanText(action.command);
      if (!command) return "";
      return `<button type="button" class="button compact primary" data-workflow-recovery-command="${escapeHtml(command)}">${escapeHtml(label)}</button>`;
    }),
    actions.length ? "</div>" : "",
    "</div>",
  ].join("");
}

export function hasWorkflowErrorDiagnostic(metadata = {}) {
  return isRecord(metadata?.error_diagnostic);
}

export function workflowErrorDiagnosticHtml(diagnostic) {
  if (!isRecord(diagnostic)) return "";
  const code = cleanText(diagnostic.code);
  const workflow = cleanText(diagnostic.workflow);
  const title = cleanText(diagnostic.title) || "Workflow failed";
  const summary = cleanText(diagnostic.summary)
    || "Review the error details and recovery options before retrying.";
  const cause = cleanText(diagnostic.cause);
  const retryable = diagnostic.retryable === true
    ? { value: "true", label: "Try again" }
    : diagnostic.retryable === false
      ? { value: "false", label: "Manual action required" }
      : null;
  const eyebrow = [workflow, code].filter(Boolean).map(escapeHtml).join(" · ");
  return [
    `<section class="workflow-error-card" role="alert" aria-label="${escapeHtml(title)}"`
      + `${code ? ` data-error-code="${escapeHtml(code)}"` : ""}`
      + `${retryable ? ` data-retryable="${retryable.value}"` : ""}>`,
    '<header class="workflow-error-card__header">',
    '<span class="workflow-error-card__icon" aria-hidden="true">!</span>',
    '<div class="workflow-error-card__heading">',
    eyebrow ? `<div class="workflow-error-card__eyebrow">${eyebrow}</div>` : "",
    `<h3>${escapeHtml(title)}</h3>`,
    "</div>",
    retryable
      ? `<span class="workflow-error-card__retry">${retryable.label}</span>`
      : "",
    "</header>",
    `<p class="workflow-error-card__summary">${escapeHtml(summary)}</p>`,
    cause
      ? `<div class="workflow-error-card__section"><h4>Cause</h4><p>${escapeHtml(cause)}</p></div>`
      : "",
    diagnosticFactsHtml(diagnostic),
    diagnosticActionsHtml(diagnostic.actions),
    diagnosticRecoveryHtml(diagnostic),
    diagnosticTechnicalHtml(diagnostic),
    "</section>",
  ].join("");
}

function noticeSeverityLabel(value) {
  const severity = cleanText(value);
  if (!severity) return "";
  const normalized = severity.toLowerCase();
  if (normalized === "warning" || normalized === "warn") return "Warning";
  if (normalized === "info" || normalized === "information") return "Information";
  if (normalized === "error" || normalized === "danger") return "Error";
  return severity;
}

function ingestNoticeItemHtml(notice) {
  const code = cleanText(notice.code);
  const severity = cleanText(notice.severity);
  const file = cleanText(notice.file);
  const declared = cleanText(notice.declared_format);
  const detected = cleanText(notice.detected_format);
  const message = cleanText(notice.message)
    || "The file format was detected during import.";
  const severityLabel = noticeSeverityLabel(severity);
  const formatHtml = declared || detected
    ? [
      '<span class="workflow-ingest-notice__format">',
      "Format:",
      `<code>${escapeHtml(declared || "Undeclared")}</code>`,
      '<span aria-hidden="true"> → </span><span class="visually-hidden">detected as</span>',
      `<code>${escapeHtml(detected || "Unknown")}</code>`,
      "</span>",
    ].join("")
    : "";
  return [
    `<li class="workflow-ingest-notice__item"`
      + `${code ? ` data-notice-code="${escapeHtml(code)}"` : ""}`
      + `${severity ? ` data-notice-severity="${escapeHtml(severity)}"` : ""}>`,
    `<p>${escapeHtml(message)}</p>`,
    '<div class="workflow-ingest-notice__meta">',
    file ? `<span>File: <code>${escapeHtml(file)}</code></span>` : "",
    formatHtml,
    code ? `<span>Code: <code>${escapeHtml(code)}</code></span>` : "",
    severityLabel ? `<span>${escapeHtml(severityLabel)}</span>` : "",
    "</div>",
    "</li>",
  ].join("");
}

export function ingestNoticesHtml(notices) {
  const items = Array.isArray(notices) ? notices.filter(isRecord) : [];
  if (!items.length) return "";
  return [
    '<aside class="workflow-ingest-notice" role="status" aria-label="Import notices">',
    '<header class="workflow-ingest-notice__header">',
    '<span class="workflow-ingest-notice__icon" aria-hidden="true">✓</span>',
    "<strong>Import notices</strong>",
    items.length > 1 ? `<span>${items.length} notices</span>` : "",
    "</header>",
    '<ul class="workflow-ingest-notice__list">',
    ...items.map(ingestNoticeItemHtml),
    "</ul>",
    "</aside>",
  ].join("");
}

// One shared presentation boundary for Agent chat and manual Driver analysis.
// The callback remains responsible for trusted Markdown rendering; the default
// fallback is escaped plain text. A structured diagnostic replaces the raw
// exception body, while non-error notices are prepended and preserve it.
export function workflowMessageContentHtml(message = {}, renderContent = escapedText) {
  const metadata = isRecord(message?.metadata) ? message.metadata : {};
  const noticesHtml = ingestNoticesHtml(metadata.ingest_notices);
  const diagnosticHtml = workflowErrorDiagnosticHtml(metadata.error_diagnostic);
  const content = message?.content === undefined || message?.content === null
    ? ""
    : String(message.content);
  const bodyHtml = diagnosticHtml || String(renderContent(content) ?? "");
  return `${noticesHtml}${bodyHtml}`;
}
