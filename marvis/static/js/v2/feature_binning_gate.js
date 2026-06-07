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

export function renderFeatureBinningGate(message, options = {}) {
  const payload = message?.metadata?.feature_binning;
  if (!payload || !Array.isArray(payload.features)) return "";
  const interactive = options.interactive !== false;
  const disabled = interactive ? "" : " disabled";
  const planId = String(message?.metadata?.plan_id || "");
  const stepId = String(message?.metadata?.step_id || "");
  const snapshotAttrs = confirmationSnapshotAttributes(
    message?.metadata?.confirmation_snapshot || {},
  );
  const minBins = Number(payload.min_bins || 3);
  const maxBins = Number(payload.max_bins || 20);
  const defaultBins = Number(payload.default_bins || 10);
  const optionsHtml = payload.features.map((item) => {
    const feature = String(item?.feature || "");
    const recommendation = String(item?.recommendation || "");
    const reason = String(item?.recommendation_reason || "");
    return [
      '<label class="feature-binning-option">',
      `<input type="checkbox" data-feature-binning-pick value="${escapeHtml(feature)}"${disabled}>`,
      '<span class="feature-binning-option-main">',
      '<span class="feature-binning-option-title">',
      `<strong>${escapeHtml(feature)}</strong>`,
      recommendation ? `<span class="feature-binning-recommendation">${escapeHtml(recommendation)}</span>` : "",
      "</span>",
      reason ? `<small title="${escapeHtml(reason)}">${escapeHtml(reason)}</small>` : "",
      "</span>",
      "</label>",
    ].join("");
  }).join("");
  return [
    `<section class="feature-binning-gate" data-feature-binning-plan-id="${escapeHtml(planId)}" data-feature-binning-step-id="${escapeHtml(stepId)}"${snapshotAttrs}>`,
    '<div class="feature-binning-heading"><div><h4>Feature binning</h4><p>Select features to analyse, or skip binning and generate the report.</p></div>',
    `<label class="feature-binning-count"><span>Number of bins</span><input type="number" data-feature-binning-count min="${minBins}" max="${maxBins}" value="${defaultBins}"${disabled}></label></div>`,
    `<div class="feature-binning-options">${optionsHtml}</div>`,
    '<div class="feature-binning-actions gate-action-bar">',
    `<button type="button" class="button compact secondary" data-feature-binning-submit="skip"${disabled}>Skip binning and generate report</button>`,
    `<button type="button" class="button compact primary" data-feature-binning-submit="selected"${disabled}>Analyse features and generate report</button>`,
    "</div>",
    "</section>",
  ].join("");
}

function contextValues(context = {}) {
  return {
    taskId: typeof context.getSelectedTaskId === "function" ? context.getSelectedTaskId() : context.selectedTaskId,
    api: context.api,
    setActionStatus: context.setActionStatus || (() => {}),
    setAgentMessages: context.setAgentMessages || (() => {}),
    renderAgentConversation: context.renderAgentConversation || (() => {}),
    pollAgentMessagesUntilSettled: context.pollAgentMessagesUntilSettled || (() => Promise.resolve()),
    resetFetchThrottle: context.resetFetchThrottle || (() => {}),
    renderWorkflowStepper: context.renderWorkflowStepper || (() => {}),
    refreshAgentMessages: context.refreshAgentMessages,
  };
}

export async function submitFeatureBinning(button, context = {}) {
  const values = contextValues(context);
  const wrap = button?.closest?.("[data-feature-binning-step-id]");
  if (!wrap || !values.taskId || typeof values.api !== "function") return;
  const expectedPlanId = wrap.dataset.featureBinningPlanId || "";
  const expectedStepId = wrap.dataset.featureBinningStepId || "";
  const confirmationSnapshot = confirmationSnapshotFromControl(
    wrap,
    { requireStep: true },
  );
  if (!expectedPlanId || !expectedStepId || !confirmationSnapshot) {
    values.setActionStatus("The plan has changed. Refresh and confirm it again.", "error");
    return;
  }
  const mode = button.dataset.featureBinningSubmit || "skip";
  const features = mode === "skip"
    ? []
    : [...wrap.querySelectorAll("[data-feature-binning-pick]:checked")].map((input) => input.value);
  const bins = Number(wrap.querySelector("[data-feature-binning-count]")?.value || 10);
  if (mode === "selected" && features.length === 0) {
    values.setActionStatus("Select at least one feature, or choose Skip binning and generate report.", "error");
    return;
  }
  if (!Number.isInteger(bins) || bins < 3 || bins > 20) {
    values.setActionStatus("The number of bins must be an integer from 3 to 20.", "error");
    return;
  }
  wrap.querySelectorAll("button, input").forEach((node) => { node.disabled = true; });
  values.setActionStatus(features.length ? "Calculating bins and generating the report…" : "Generating the report…", "busy");
  try {
    const request = values.api(`/api/tasks/${values.taskId}/agent/messages`, {
      method: "POST",
      body: JSON.stringify({
        content: "Confirm.",
        ui_action: "confirm_feature_binning",
        expected_plan_id: expectedPlanId,
        expected_step_id: expectedStepId,
        ...confirmationSnapshot,
        adjust_params: { features, bins },
      }),
    });
    const poll = values.pollAgentMessagesUntilSettled(values.taskId, request, { preserveOptimistic: true });
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
      wrap.querySelectorAll("button, input").forEach((node) => { node.disabled = false; });
      values.setActionStatus(error?.message || "Could not submit binning settings.", "error");
    }
  } finally {
    values.resetFetchThrottle(values.taskId);
    values.renderWorkflowStepper({ force: true });
  }
}

export function handleFeatureBinningClick(event, context = {}) {
  const button = event.target?.closest?.("[data-feature-binning-submit]");
  if (!button) return false;
  event.preventDefault();
  void submitFeatureBinning(button, context);
  return true;
}
