const STRATEGY_CLARIFICATION_CODE = "strategy_business_inputs_required";

const MISSING_FIELD_LABELS = {
  objective: "Business objective",
  constraints: "At least one approval or bad-rate constraint",
  max_bad_rate_or_min_approval_rate: "At least one approval or bad-rate constraint",
  "profit.ead_col": "EAD column",
  "profit.pd_col": "PD column",
  "profit.annual_rate": "Annual interest rate",
  "profit.funding_rate": "Cost of funds",
  "profit.lgd": "LGD",
  "profit.operating_cost_per_loan": "Operating cost per loan",
  "profit.term_months": "Term (months)",
};

export function isStrategyClarificationMessage(message) {
  const metadata = message?.metadata || {};
  return metadata.kind === "clarification"
    && metadata.clarification?.code === STRATEGY_CLARIFICATION_CODE;
}

function missingFieldLabels(message) {
  const fields = Array.isArray(message?.metadata?.clarification?.missing_fields)
    ? message.metadata.clarification.missing_fields
    : [];
  const labels = [];
  for (const field of fields) {
    const label = MISSING_FIELD_LABELS[String(field)] || String(field);
    if (label && !labels.includes(label)) labels.push(label);
  }
  return labels;
}

function option(value, label, selectedValue) {
  const selected = value === selectedValue ? " selected" : "";
  return `<option value="${escapeHtml(value)}"${selected}>${escapeHtml(label)}</option>`;
}

function inputValue(value) {
  return value === null || value === undefined ? "" : escapeHtml(value);
}

export function renderStrategyClarification(message, options = {}) {
  if (!isStrategyClarificationMessage(message)) return "";
  const interactive = options.interactive !== false;
  const readonly = interactive ? "false" : "true";
  const disabled = interactive ? "" : " disabled";
  const readonlyTitle = interactive
    ? ""
    : ' title="Historical request: read only"';
  const clarification = message?.metadata?.clarification || {};
  const missingFields = clarification.missing_fields || [];
  const currentInput = clarification.current_input
    && typeof clarification.current_input === "object"
    ? clarification.current_input
    : {};
  const currentProfit = currentInput.profit && typeof currentInput.profit === "object"
    ? currentInput.profit
    : {};
  const currentObjective = String(currentInput.objective || "").trim();
  const inferredObjective = !currentObjective
    && Array.isArray(missingFields)
    && missingFields.some((field) => String(field).startsWith("profit."))
    ? "max_profit"
    : "";
  const selectedObjective = currentObjective || inferredObjective;
  const missingLabels = missingFieldLabels(message);
  const missingHtml = missingLabels.length
    ? `<p class="strategy-clarification-missing">Missing: ${missingLabels.map(escapeHtml).join(", ")}</p>`
    : "";
  const profitHidden = selectedObjective === "max_profit" ? "" : " hidden";
  const actionLabel = interactive ? "Save inputs and start strategy development" : "Historical request (read only)";

  return [
    `<div class="strategy-clarification-card" data-strategy-clarification="1" data-strategy-clarification-readonly="${readonly}"${readonlyTitle}>`,
    '<header class="strategy-clarification-head">',
    '<div><span class="strategy-clarification-eyebrow">Required inputs</span><h4>Strategy objectives and constraints</h4></div>',
    '<p>Choose an objective and at least one approval or bad-rate constraint.</p>',
    "</header>",
    missingHtml,
    '<div class="strategy-clarification-grid">',
    '<label class="strategy-clarification-field"><span>Objective<b aria-hidden="true">*</b></span>',
    `<select data-strategy-objective${disabled}>`,
    option("", "Select an objective", selectedObjective),
    option("max_approval", "Maximise approval rate within the bad-rate limit", selectedObjective),
    option("max_profit", "Maximise expected profit", selectedObjective),
    "</select></label>",
    '<label class="strategy-clarification-field"><span>Maximum approved bad rate (0–1)</span>',
    `<input data-strategy-max-bad-rate type="number" min="0" max="1" step="0.001" inputmode="decimal" value="${inputValue(currentInput.max_bad_rate)}" placeholder="Decimal proportion"${disabled}></label>`,
    '<label class="strategy-clarification-field"><span>Minimum approval rate (0–1)</span>',
    `<input data-strategy-min-approval-rate type="number" min="0" max="1" step="0.001" inputmode="decimal" value="${inputValue(currentInput.min_approval_rate)}" placeholder="Decimal proportion"${disabled}></label>`,
    '<label class="strategy-clarification-field is-wide"><span>Baseline strategy ID (optional)</span>',
    `<input data-strategy-baseline-id autocomplete="off" value="${inputValue(currentInput.baseline_strategy_id)}" placeholder="Strategy ID for comparison"${disabled}></label>`,
    "</div>",
    `<fieldset class="strategy-clarification-profit" data-strategy-profit-fields${profitHidden}${disabled}>`,
    '<legend>Profit parameters</legend>',
    '<p>Profit optimisation requires EAD, PD, rates, loss assumptions, costs and term. Enter rates as decimals.</p>',
    '<div class="strategy-clarification-grid">',
    '<label class="strategy-clarification-field"><span>EAD column</span>',
    `<input data-strategy-ead-col autocomplete="off" value="${inputValue(currentProfit.ead_col)}" placeholder="EAD column name"${disabled}></label>`,
    '<label class="strategy-clarification-field"><span>PD column</span>',
    `<input data-strategy-pd-col autocomplete="off" value="${inputValue(currentProfit.pd_col)}" placeholder="PD column name"${disabled}></label>`,
    '<label class="strategy-clarification-field"><span>Annual interest rate</span>',
    `<input data-strategy-annual-rate type="number" min="0" max="1" step="0.001" inputmode="decimal" value="${inputValue(currentProfit.annual_rate)}" placeholder="Decimal rate"${disabled}></label>`,
    '<label class="strategy-clarification-field"><span>Cost of funds</span>',
    `<input data-strategy-funding-rate type="number" min="0" max="1" step="0.001" inputmode="decimal" value="${inputValue(currentProfit.funding_rate)}" placeholder="Decimal rate"${disabled}></label>`,
    '<label class="strategy-clarification-field"><span>LGD</span>',
    `<input data-strategy-lgd type="number" min="0" max="1" step="0.001" inputmode="decimal" value="${inputValue(currentProfit.lgd)}" placeholder="Decimal proportion"${disabled}></label>`,
    '<label class="strategy-clarification-field"><span>Operating cost per loan</span>',
    `<input data-strategy-operating-cost type="number" min="0" step="0.01" inputmode="decimal" value="${inputValue(currentProfit.operating_cost_per_loan)}" placeholder="Cost in the loan currency"${disabled}></label>`,
    '<label class="strategy-clarification-field"><span>Term (months)</span>',
    `<input data-strategy-term-months type="number" min="1" step="1" inputmode="numeric" value="${inputValue(currentProfit.term_months)}" placeholder="Whole months"${disabled}></label>`,
    "</div>",
    "</fieldset>",
    '<p class="strategy-clarification-error" data-strategy-clarification-error role="alert" aria-live="polite"></p>',
    '<div class="strategy-clarification-actions">',
    `<button type="button" class="button compact primary" data-strategy-clarification-submit="1"${disabled}${readonlyTitle}>${actionLabel}</button>`,
    "</div>",
    "</div>",
  ].join("");
}

function fieldValue(wrap, selector) {
  return String(wrap?.querySelector?.(selector)?.value ?? "").trim();
}

function optionalNumber(wrap, selector) {
  const value = fieldValue(wrap, selector);
  return value === "" ? null : Number(value);
}

function collectStrategyInput(wrap) {
  const objective = fieldValue(wrap, "[data-strategy-objective]");
  const input = {
    entry_mode: "strategy_development",
    objective,
    max_bad_rate: optionalNumber(wrap, "[data-strategy-max-bad-rate]"),
    min_approval_rate: optionalNumber(wrap, "[data-strategy-min-approval-rate]"),
    baseline_strategy_id: fieldValue(wrap, "[data-strategy-baseline-id]") || null,
    profit: null,
  };
  if (objective === "max_profit") {
    input.profit = {
      ead_col: fieldValue(wrap, "[data-strategy-ead-col]"),
      pd_col: fieldValue(wrap, "[data-strategy-pd-col]"),
      annual_rate: optionalNumber(wrap, "[data-strategy-annual-rate]"),
      funding_rate: optionalNumber(wrap, "[data-strategy-funding-rate]"),
      lgd: optionalNumber(wrap, "[data-strategy-lgd]"),
      operating_cost_per_loan: optionalNumber(wrap, "[data-strategy-operating-cost]"),
      term_months: optionalNumber(wrap, "[data-strategy-term-months]"),
    };
  }
  return input;
}

export function strategyClarificationInputError(input) {
  if (!input || !["max_approval", "max_profit"].includes(input.objective)) {
    return "Select a strategy objective.";
  }
  for (const [label, value] of [
    ["Maximum approved bad rate", input.max_bad_rate],
    ["Minimum approval rate", input.min_approval_rate],
  ]) {
    if (value !== null && (!Number.isFinite(value) || value < 0 || value > 1)) {
      return `${label} must be between 0 and 1.`;
    }
  }
  if (input.max_bad_rate === null && input.min_approval_rate === null) {
    return "Enter a maximum bad rate or a minimum approval rate.";
  }
  if (input.objective !== "max_profit") return "";
  const profit = input.profit || {};
  const requiredNumbers = [
    profit.annual_rate,
    profit.funding_rate,
    profit.lgd,
    profit.operating_cost_per_loan,
    profit.term_months,
  ];
  if (
    !profit.ead_col
    || !profit.pd_col
    || requiredNumbers.some((value) => value === null || !Number.isFinite(value))
  ) {
    return "Profit optimisation requires EAD and PD columns and all profit parameters.";
  }
  if (
    profit.annual_rate < 0 || profit.annual_rate > 1
    || profit.funding_rate < 0 || profit.funding_rate > 1
    || profit.lgd < 0 || profit.lgd > 1
    || profit.operating_cost_per_loan < 0
    || !Number.isInteger(profit.term_months) || profit.term_months < 1
  ) {
    return "Rates and LGD must be between 0 and 1, costs non-negative, and term a positive whole number.";
  }
  return "";
}

function controllerContext(context = {}) {
  return {
    taskId: typeof context.getSelectedTaskId === "function"
      ? context.getSelectedTaskId()
      : context.selectedTaskId,
    api: context.api,
    setActionStatus: context.setActionStatus || (() => {}),
    setAgentMessages: context.setAgentMessages || (() => {}),
    renderAgentConversation: context.renderAgentConversation || (() => {}),
    pollAgentMessagesUntilSettled: context.pollAgentMessagesUntilSettled
      || (() => Promise.resolve()),
    refreshAgentMessages: context.refreshAgentMessages || (() => Promise.resolve()),
    resetFetchThrottle: context.resetFetchThrottle || (() => {}),
    renderWorkflowStepper: context.renderWorkflowStepper || (() => {}),
  };
}

function setFormError(wrap, message) {
  const error = wrap?.querySelector?.("[data-strategy-clarification-error]");
  if (error) error.textContent = String(message || "");
}

export async function submitStrategyClarification(button, context = {}) {
  const wrap = button?.closest?.("[data-strategy-clarification]");
  const {
    taskId,
    api,
    setActionStatus,
    setAgentMessages,
    renderAgentConversation,
    pollAgentMessagesUntilSettled,
    refreshAgentMessages,
    resetFetchThrottle,
    renderWorkflowStepper,
  } = controllerContext(context);
  if (!wrap) return;
  if (wrap?.dataset?.strategyClarificationReadonly === "true") return;
  if (!taskId || typeof api !== "function") {
    const message = "The current strategy task is unavailable. Refresh and try again.";
    setFormError(wrap, message);
    setActionStatus(message, "error");
    return;
  }

  const strategyInput = collectStrategyInput(wrap);
  const validationError = strategyClarificationInputError(strategyInput);
  if (validationError) {
    setFormError(wrap, validationError);
    setActionStatus(validationError, "error");
    return;
  }

  setFormError(wrap, "");
  button.disabled = true;
  setActionStatus("Saving inputs and generating the plan…", "busy");
  try {
    const requestPromise = api(`/api/tasks/${taskId}/agent/messages`, {
      method: "POST",
      body: JSON.stringify({
        content: "Strategy objectives and constraints",
        strategy_input: strategyInput,
      }),
    });
    const pollPromise = Promise.resolve(
      pollAgentMessagesUntilSettled(taskId, requestPromise, { preserveOptimistic: true }),
    ).catch(() => {});
    const result = await requestPromise;
    await pollPromise;
    setAgentMessages(result?.messages);
    renderAgentConversation();
    await refreshAgentMessages(taskId);
    setActionStatus("Inputs saved and strategy plan generated.", "success");
  } catch (error) {
    button.disabled = false;
    const message = error?.message || "Could not save strategy inputs.";
    setFormError(wrap, message);
    setActionStatus(message, "error");
  } finally {
    resetFetchThrottle(taskId);
    renderWorkflowStepper({ force: true });
  }
}

export function handleStrategyClarificationSubmit(event, context = {}) {
  const button = event.target?.closest?.("[data-strategy-clarification-submit]");
  if (!button) return false;
  event.preventDefault();
  void submitStrategyClarification(button, context);
  return true;
}

export function handleStrategyClarificationChange(event) {
  const select = event.target?.closest?.("[data-strategy-objective]");
  if (!select) return false;
  const wrap = select.closest?.("[data-strategy-clarification]");
  const profitFields = wrap?.querySelector?.("[data-strategy-profit-fields]");
  if (profitFields) profitFields.hidden = select.value !== "max_profit";
  return true;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
