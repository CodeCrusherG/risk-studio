import {
  confirmationSnapshotAttributes,
  confirmationSnapshotFromControl,
  refreshAfterConfirmationConflict,
} from "./driver_gate_confirm.js";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatSpecialValue(value) {
  if (value === null) return "null";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch (_error) {
    return String(value);
  }
}

function formatShare(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  const ratio = number >= 0 && number <= 1 ? number * 100 : number;
  return `${ratio.toFixed(ratio >= 10 ? 1 : 2)}%`;
}

function valueEvidenceHtml(values = []) {
  return values.map((item) => {
    const value = item && typeof item === "object" && Object.prototype.hasOwnProperty.call(item, "value")
      ? item.value
      : item;
    const share = item && typeof item === "object" ? formatShare(item.share) : "";
    return [
      '<span class="special-value-chip">',
      `<strong>${escapeHtml(formatSpecialValue(value))}</strong>`,
      share ? `<span>${escapeHtml(share)}</span>` : "",
      "</span>",
    ].join("");
  }).join("");
}

export function renderSpecialValueGate(message, options = {}) {
  const payload = message?.metadata?.special_values;
  if (!payload || !Array.isArray(payload.columns) || payload.columns.length === 0) return "";
  const interactive = options.interactive !== false;
  const disabled = interactive ? "" : " disabled";
  const planId = String(message?.metadata?.plan_id || "");
  const stepId = String(message?.metadata?.step_id || payload.step_id || "");
  const snapshotAttrs = confirmationSnapshotAttributes(
    message?.metadata?.confirmation_snapshot || {},
  );
  const rows = payload.columns.map((item) => {
    const column = String(item?.column || "");
    if (!column) return "";
    return [
      `<article class="special-value-row" data-special-value-row data-special-value-column="${escapeHtml(column)}">`,
      '<div class="special-value-evidence">',
      `<div class="special-value-column"><strong>${escapeHtml(column)}</strong><span>Possible special values</span></div>`,
      `<div class="special-value-chips">${valueEvidenceHtml(item?.values || [])}</div>`,
      "</div>",
      '<div class="special-value-decision">',
      `<label><span>Treatment</span><select data-special-value-action aria-label="${escapeHtml(column)} treatment"${disabled}>`,
      '<option value="">Choose</option>',
      '<option value="mask">Treat as missing</option>',
      '<option value="retain">Retain original value (justification required)</option>',
      '<option value="drop">Remove this feature</option>',
      "</select></label>",
      `<label class="special-value-reason"><span>Reason for retaining values</span><input type="text" data-special-value-reason maxlength="500" placeholder="Required when retaining original values"${disabled}></label>`,
      "</div>",
      "</article>",
    ].join("");
  }).join("");
  return [
    `<section class="special-value-gate" data-special-value-plan-id="${escapeHtml(planId)}" data-special-value-step-id="${escapeHtml(stepId)}"${snapshotAttrs}>`,
    '<header class="special-value-gate-heading">',
    '<div><span class="special-value-kicker">Review required</span><h4>Special value treatment</h4>',
    '<p>Choose how to handle the detected values for each feature.</p></div>',
    `<span class="special-value-count">${payload.columns.length} features to review</span>`,
    "</header>",
    `<div class="special-value-list">${rows}</div>`,
    '<div class="special-value-actions gate-action-bar">',
    `<button type="button" class="button compact primary" data-special-value-submit${disabled}>Confirm and continue</button>`,
    "</div>",
    "</section>",
  ].join("");
}

export function collectSpecialValueDecisions(wrap) {
  const decisions = {};
  const errors = [];
  for (const row of wrap?.querySelectorAll?.("[data-special-value-row]") || []) {
    const column = String(row.dataset?.specialValueColumn || "").trim();
    const action = String(row.querySelector?.("[data-special-value-action]")?.value || "").trim();
    const reason = String(row.querySelector?.("[data-special-value-reason]")?.value || "").trim();
    if (!column) continue;
    if (!["mask", "retain", "drop"].includes(action)) {
      errors.push(`${column}: select a treatment`);
      continue;
    }
    const decision = { action };
    if (action === "retain") {
      if (!reason) {
        errors.push(`${column}: enter a reason for retaining the original values`);
        continue;
      }
      decision.confirmed = true;
      decision.reason = reason;
    }
    decisions[column] = decision;
  }
  return { decisions, errors };
}

function contextValues(context = {}) {
  return {
    taskId: typeof context.getSelectedTaskId === "function"
      ? context.getSelectedTaskId()
      : context.selectedTaskId,
    api: context.api,
    setActionStatus: context.setActionStatus || (() => {}),
    setAgentMessages: context.setAgentMessages || (() => {}),
    renderAgentConversation: context.renderAgentConversation || (() => {}),
    pollAgentMessagesUntilSettled: context.pollAgentMessagesUntilSettled || (() => Promise.resolve()),
    refreshAgentMessages: context.refreshAgentMessages,
    resetFetchThrottle: context.resetFetchThrottle || (() => {}),
    renderWorkflowStepper: context.renderWorkflowStepper || (() => {}),
  };
}

function setControlsDisabled(wrap, disabled) {
  wrap?.querySelectorAll?.("button, select, input").forEach((node) => {
    node.disabled = disabled;
  });
}

export async function submitSpecialValueDecisions(button, context = {}) {
  const values = contextValues(context);
  const wrap = button?.closest?.("[data-special-value-step-id]");
  if (!wrap || !values.taskId || typeof values.api !== "function") return;
  const expectedPlanId = wrap.dataset.specialValuePlanId || "";
  const expectedStepId = wrap.dataset.specialValueStepId || "";
  const { decisions, errors } = collectSpecialValueDecisions(wrap);
  if (errors.length) {
    values.setActionStatus(errors[0], "error");
    return;
  }
  const rowCount = wrap.querySelectorAll?.("[data-special-value-row]")?.length || 0;
  if (!rowCount || Object.keys(decisions).length !== rowCount) {
    values.setActionStatus("Choose a treatment for every feature.", "error");
    return;
  }
  const confirmationSnapshot = confirmationSnapshotFromControl(
    wrap,
    { requireStep: true },
  );
  if (!expectedPlanId || !expectedStepId || !confirmationSnapshot) {
    values.setActionStatus("The plan has changed. Refresh and review the current values before confirming.", "error");
    return;
  }
  setControlsDisabled(wrap, true);
  values.setActionStatus("Applying special value treatments…", "busy");
  try {
    const request = values.api(`/api/tasks/${values.taskId}/agent/messages`, {
      method: "POST",
      body: JSON.stringify({
        content: "Confirm.",
        ui_action: "confirm_gate",
        expected_plan_id: expectedPlanId,
        expected_step_id: expectedStepId,
        ...confirmationSnapshot,
        adjust_params: { decisions },
      }),
    });
    const poll = values.pollAgentMessagesUntilSettled(
      values.taskId,
      request,
      { preserveOptimistic: true },
    );
    const result = await request;
    await poll;
    values.setAgentMessages(result.messages);
    values.renderAgentConversation();
  } catch (error) {
    const conflictHandled = await refreshAfterConfirmationConflict(error, {
      taskId: values.taskId,
      refreshAgentMessages: values.refreshAgentMessages,
      setActionStatus: values.setActionStatus,
    });
    if (!conflictHandled) {
      setControlsDisabled(wrap, false);
      values.setActionStatus(error?.message || "Could not apply special value treatments", "error");
    }
  } finally {
    values.resetFetchThrottle(values.taskId);
    values.renderWorkflowStepper({ force: true });
  }
}

export function handleSpecialValueClick(event, context = {}) {
  const button = event.target?.closest?.("[data-special-value-submit]");
  if (!button) return false;
  event.preventDefault();
  void submitSpecialValueDecisions(button, context);
  return true;
}
