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

export function adoptionReasonSchema(message) {
  const schema = message?.metadata?.editable_input_schema;
  const reason = schema?.properties?.adoption_reason;
  return reason && typeof reason === "object" ? reason : null;
}

export function isAdoptionGate(message) {
  return Boolean(adoptionReasonSchema(message));
}

export function renderAdoptionGate(message, options = {}) {
  if (!isAdoptionGate(message)) return "";
  const interactive = options.interactive !== false;
  const planId = String(message?.metadata?.plan_id || "");
  const stepId = String(message?.metadata?.step_id || "");
  const snapshotAttrs = confirmationSnapshotAttributes(
    message?.metadata?.confirmation_snapshot || {},
  );
  const disabled = interactive ? "" : " disabled";
  const readonly = interactive ? "false" : "true";
  return [
    `<div class="adoption-gate" data-adoption-plan-id="${escapeHtml(planId)}" data-adoption-step-id="${escapeHtml(stepId)}" data-adoption-readonly="${readonly}"${snapshotAttrs}>`,
    '<label class="adoption-reason-field">',
    "<span>Adoption reason</span>",
    `<textarea data-adoption-reason rows="3" maxlength="1000" placeholder="Explain the objective, validation results and reason for approval."${disabled}></textarea>`,
    "</label>",
    '<p class="adoption-gate-note">The reason is recorded with this strategy version and its validation results. Provide a completed justification.</p>',
    '<div class="adoption-gate-actions gate-action-bar">',
    `<button type="button" class="button compact primary adoption-confirm" data-adoption-confirm="1"${disabled}>Confirm adoption</button>`,
    '</div>',
    "</div>",
  ].join("");
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

export async function submitAdoption(button, context = {}) {
  const {
    taskId, api, setActionStatus, setAgentMessages, renderAgentConversation,
    pollAgentMessagesUntilSettled, refreshAgentMessages, resetFetchThrottle,
    renderWorkflowStepper,
  } = contextValues(context);
  const wrap = button?.closest?.("[data-adoption-step-id]");
  const reason = wrap?.querySelector?.("[data-adoption-reason]")?.value?.trim?.() || "";
  const expectedPlanId = wrap?.dataset?.adoptionPlanId || "";
  const expectedStepId = wrap?.dataset?.adoptionStepId || "";
  if (!taskId || typeof api !== "function") return;
  if (reason.length < 2) {
    setActionStatus("Enter an adoption reason of at least two characters.", "error");
    return;
  }
  const confirmationSnapshot = confirmationSnapshotFromControl(
    wrap,
    { requireStep: true },
  );
  if (!expectedPlanId || !expectedStepId || !confirmationSnapshot) {
    setActionStatus("The adoption step has changed or is missing. Refresh and try again.", "error");
    return;
  }

  button.disabled = true;
  setActionStatus("Recording the reason and adopting the strategy…", "busy");
  try {
    const requestPromise = api(`/api/tasks/${taskId}/agent/messages`, {
      method: "POST",
      body: JSON.stringify({
        content: "Confirm strategy adoption.",
        ui_action: "confirm_adoption",
        adjust_params: { adoption_reason: reason },
        expected_plan_id: expectedPlanId,
        expected_step_id: expectedStepId,
        ...confirmationSnapshot,
      }),
    });
    const pollPromise = pollAgentMessagesUntilSettled(taskId, requestPromise, { preserveOptimistic: true });
    const result = await requestPromise;
    await pollPromise;
    setAgentMessages(result.messages);
    renderAgentConversation();
  } catch (error) {
    const conflictHandled = await refreshAfterConfirmationConflict(error, {
      taskId,
      refreshAgentMessages,
      setActionStatus,
    });
    if (!conflictHandled) {
      button.disabled = false;
      setActionStatus(error?.message || "Strategy adoption failed.", "error");
    }
  } finally {
    resetFetchThrottle(taskId);
    renderWorkflowStepper({ force: true });
  }
}

export function handleAdoptionConfirmClick(event, context = {}) {
  const button = event.target?.closest?.("[data-adoption-confirm]");
  if (!button) return false;
  event.preventDefault();
  void submitAdoption(button, context);
  return true;
}
