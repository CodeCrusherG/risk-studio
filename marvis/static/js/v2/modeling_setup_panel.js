import { escapeHtml } from "../ui-utils.js";
import {
  confirmationSnapshotAttributes,
  confirmationSnapshotFromControl,
  refreshAfterConfirmationConflict,
} from "./driver_gate_confirm.js";

export function renderModelingSetupPanel(message, options = {}) {
  const setup = message?.metadata?.modeling_setup;
  if (!setup || typeof setup !== "object") return "";
  const messageId = message?.id ? String(message.id) : "";
  const planId = message?.metadata?.plan_id ? String(message.metadata.plan_id) : "";
  const gateStepId = message?.metadata?.step_id ? String(message.metadata.step_id) : "";
  const snapshotAttrs = confirmationSnapshotAttributes(
    message?.metadata?.confirmation_snapshot || {},
  );
  const candidates = Array.isArray(setup.sample_weight_candidates)
    ? setup.sample_weight_candidates.map((value) => String(value)).filter(Boolean)
    : [];
  const selected = String(setup.sample_weight_col || "");
  const currentTargetType = String(setup.target_type || "binary");
  const interactive = options.interactive !== false;
  const disabledAttr = interactive ? "" : " disabled aria-disabled=\"true\"";
  const uniqueCandidates = [...new Set(selected ? [selected, ...candidates] : candidates)];
  const recipeText = Array.isArray(setup.recipes) && setup.recipes.length
    ? setup.recipes.map((recipe) => String(recipe)).join("/")
    : "-";
  const primaryRecipe = String(setup.recipe || (Array.isArray(setup.recipes) ? setup.recipes[0] : "") || "-");
  const featureCount = Number.isFinite(Number(setup.feature_count)) ? String(Number(setup.feature_count)) : "-";
  const candidateFeatureCount = Number.isFinite(Number(setup.candidate_feature_count))
    ? String(Number(setup.candidate_feature_count))
    : "";
  const rawNTrials = setup.n_trials;
  const nTrials = rawNTrials !== null
    && rawNTrials !== undefined
    && String(rawNTrials).trim() !== ""
    && Number.isFinite(Number(rawNTrials))
    ? String(Number(rawNTrials))
    : "-";
  const metricPolicy = String(setup.metric_policy || "-");
  const metricPolicyLabel = humanMetricPolicy(metricPolicy);
  const supportedPmml = new Set(Array.isArray(setup.pmml_supported_algorithms)
    ? setup.pmml_supported_algorithms.map((item) => String(item))
    : []);
  const setupWarnings = Array.isArray(setup.warnings)
    ? setup.warnings.map((item) => String(item)).filter(Boolean)
    : [];
  const splitSummary = setup.split_summary && typeof setup.split_summary === "object" ? setup.split_summary : null;
  const splitCounts = splitSummary && splitSummary.split_counts && typeof splitSummary.split_counts === "object"
    ? Object.entries(splitSummary.split_counts)
    : [];
  const splitWarnings = splitSummary && Array.isArray(splitSummary.warnings)
    ? splitSummary.warnings.map((item) => String(item)).filter(Boolean)
    : [];
  const splitConfig = splitSummary?.split_config && typeof splitSummary.split_config === "object"
    ? splitSummary.split_config
    : {};
  const splitColumns = Array.isArray(splitSummary?.available_columns)
    ? splitSummary.available_columns.map(String).filter(Boolean)
    : [];
  const splitMode = splitConfig.oot_by_time ? "time" : splitConfig.random_oot ? "random" : "none";
  const testPercent = Number.isFinite(Number(splitConfig.test_size)) ? Number(splitConfig.test_size) * 100 : 25;
  const ootPercent = Number.isFinite(Number(splitConfig.oot_size)) ? Number(splitConfig.oot_size) * 100 : 20;
  const specChips = [
    ["Objective", String(setup.target_type || "binary")],
    ["Algorithm", recipeText],
    ["Primary algorithm", primaryRecipe],
    [
      candidateFeatureCount ? "Selected features" : "Candidate features",
      featureCount,
      candidateFeatureCount ? `${candidateFeatureCount} candidates; ${featureCount} selected` : featureCount,
    ],
    ["Tuning trials", nTrials],
    ["Selection metric", metricPolicyLabel, metricPolicy],
  ].map(([label, value, detail = value]) => `<div class="modeling-spec-chip" title="${escapeHtml(detail)}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
  const eligibleAlgorithms = Array.isArray(setup.eligible_algorithms)
    ? setup.eligible_algorithms.map((item) => String(item)).filter(Boolean)
    : [];
  const selectedRecipes = Array.isArray(setup.recipes)
    ? setup.recipes.map((item) => String(item)).filter(Boolean)
    : [];
  const disabledAlgorithms = Array.isArray(setup.disabled_algorithms)
    ? setup.disabled_algorithms.filter((item) => item && typeof item === "object")
    : [];
  const algorithmChoices = uniqueRecipeChoices([
    ...eligibleAlgorithms.map((recipe) => ({
    recipe,
    state: "Available",
    reason: supportedPmml.has(recipe) ? "PMML export available" : "Native model only",
    enabled: true,
  })), ...disabledAlgorithms.map((item) => ({
    recipe: String(item.recipe || ""),
    state: "Unavailable",
    reason: String(item.reason || ""),
    enabled: false,
  }))]);
  const algorithmHtml = algorithmChoices.filter((item) => item.recipe).map((item) => `<div class="modeling-algorithm-chip" data-enabled="${item.enabled ? "true" : "false"}">
      <strong>${escapeHtml(item.recipe)}</strong>
      <span>${escapeHtml(item.state)} · ${escapeHtml(item.reason || "-")}</span>
    </div>`).join("");
  const splitCountsHtml = splitCounts.map(([split, count]) => {
    const total = Number(splitSummary?.total_rows || 0);
    const n = Number(count);
    const pct = total > 0 && Number.isFinite(n) ? `${((n / total) * 100).toFixed(1)}%` : "n/a";
    return `<div class="modeling-split-chip"><span>${escapeHtml(String(split).toUpperCase())}</span><strong>${escapeHtml(String(count))}</strong><small>${escapeHtml(pct)}</small></div>`;
  }).join("");
  const warningHtml = [...setupWarnings, ...splitWarnings].map((warning) => (
    `<div class="modeling-setup-warning">${escapeHtml(warning)}</div>`
  )).join("");
  const guidance = Array.isArray(setup.override_guidance)
    ? setup.override_guidance.filter((item) => item && typeof item === "object")
    : [];
  const guidanceHtml = guidance.map((item) => {
    const level = ["info", "review", "warning"].includes(String(item.level || ""))
      ? String(item.level)
      : "info";
    return `<div class="modeling-guidance-item" data-level="${escapeHtml(level)}">
      <strong>${escapeHtml(String(item.label || "Guidance"))}</strong>
      <span>${escapeHtml(String(item.message || ""))}</span>
    </div>`;
  }).join("");
  const targetOptions = ["binary", "continuous", "multiclass"].map((value) => (
    `<option value="${escapeHtml(value)}"${value === currentTargetType ? " selected" : ""}>${escapeHtml(value)}</option>`
  )).join("");
  const recipeOptions = algorithmChoices.filter((item) => item.recipe).map((item) => {
    const recipe = item.recipe;
    const checked = selectedRecipes.includes(recipe);
    const pmmlText = supportedPmml.has(recipe) ? "PMML" : "Native";
    return `<label class="modeling-recipe-option">
      <input type="checkbox" class="modeling-recipe-pick" value="${escapeHtml(recipe)}"${checked ? " checked" : ""}${disabledAttr} />
      <span>${escapeHtml(recipe)}</span>
      <small>${escapeHtml(recipeFamily(recipe))} · ${escapeHtml(pmmlText)}</small>
    </label>`;
  }).join("");
  const splitModeOptions = [
    ["none", "No holdout set", "Use train and test sets"],
    ["time", "Time-based holdout", "Reserve the most recent period"],
    ["random", "Random holdout", "Use when no reliable time column exists"],
  ].map(([value, label, note]) => `<label class="modeling-split-mode-option">
    <input type="radio" name="modelingSplitMode-${escapeHtml(messageId)}" class="modeling-split-mode" value="${value}"${splitMode === value ? " checked" : ""}${disabledAttr}>
    <span><strong>${escapeHtml(label)}</strong><small>${escapeHtml(note)}</small></span>
  </label>`).join("");
  const timeColumnOptions = ['<option value="">Select a time column</option>'].concat(splitColumns.map((column) => (
    `<option value="${escapeHtml(column)}"${String(splitConfig.oot_by_time || "") === column ? " selected" : ""}>${escapeHtml(column)}</option>`
  ))).join("");
  const splitControlsHtml = splitSummary ? `<section class="modeling-split-controls">
    <div class="modeling-section-heading"><strong>Dataset split</strong><span>Review the split before feature selection and training.</span></div>
    <div class="modeling-split-mode-list" role="radiogroup" aria-label="Holdout method">${splitModeOptions}</div>
    <div class="modeling-split-fields">
      <label>Test share of remaining samples (%)<input type="number" class="modeling-test-size-input" min="1" max="50" step="1" value="${escapeHtml(String(testPercent))}"${disabledAttr}></label>
      <label>Holdout share (%)<input type="number" class="modeling-oot-size-input" min="1" max="50" step="1" value="${escapeHtml(String(ootPercent))}"${disabledAttr}></label>
      <label>Time column<select class="modeling-time-column-select"${disabledAttr}>${timeColumnOptions}</select></label>
    </div>
    <p class="modeling-split-help">Rows with the same group key stay together to prevent customer overlap between splits. A holdout is optional.</p>
  </section>` : "";
  const targetAlgorithmControlsHtml = `<div class="modeling-setup-controls modeling-target-controls">
    <label>Target type
      <select class="modeling-target-select"${disabledAttr} data-current-target-type="${escapeHtml(currentTargetType)}">${targetOptions}</select>
    </label>
    ${recipeOptions ? `<div class="modeling-recipe-control" data-current-recipes="${escapeHtml(selectedRecipes.join(","))}">
      <span>Training algorithms</span>
      <div class="modeling-recipe-options">${recipeOptions}</div>
    </div>` : ""}
  </div>`;
  const reasonControlHtml = `<label class="modeling-override-reason">Reason for changes
    <textarea class="modeling-override-reason-input" rows="2" placeholder="Explain changes to the proposed target, algorithms or tuning trials"${disabledAttr}></textarea>
  </label>`;
  const optionRows = [
    { value: "", label: "Do not use weights" },
    ...uniqueCandidates.map((value) => ({ value, label: value })),
  ].map((option) => {
    const checked = option.value === selected || (!selected && option.value === "");
    return `<label class="modeling-weight-option">
      <input type="radio" name="modelingWeight-${escapeHtml(messageId)}" class="modeling-weight-pick" value="${escapeHtml(option.value)}"${checked ? " checked" : ""}${disabledAttr} />
      <span>${escapeHtml(option.label)}</span>
    </label>`;
  }).join("");
  const tuningControlsHtml = `<div class="modeling-tuning-layout">
    <label class="modeling-trial-control">
      <span>Tuning trials</span>
      <strong data-modeling-live-value="trials">${escapeHtml(nTrials)}</strong>
      <input type="number" class="modeling-n-trials-input" min="1" max="200" step="1" value="${escapeHtml(nTrials === "-" ? "" : nTrials)}"${disabledAttr} data-current-n-trials="${escapeHtml(nTrials === "-" ? "" : nTrials)}" />
      <small>More trials explore more parameter settings and take longer.</small>
    </label>
    <div class="modeling-weight-control">
      <span>Sample weights</span>
      <div class="modeling-weight-options" role="radiogroup" aria-label="Sample weight column">${optionRows}</div>
    </div>
  </div>`;
  const diagnostics = Array.isArray(setup.sample_weight_diagnostics)
    ? setup.sample_weight_diagnostics.filter((item) => item && typeof item === "object")
    : [];
  const diagnosticsByColumn = new Map(diagnostics.map((item) => [String(item.column || ""), item]));
  const diagnosticsHtml = uniqueCandidates
    .map((column) => {
      const item = diagnosticsByColumn.get(column);
      if (!item) return "";
      const missing = Number.isFinite(Number(item.missing_rate))
        ? `${(Number(item.missing_rate) * 100).toFixed(1)}%`
        : "n/a";
      const min = item.min ?? "n/a";
      const max = item.max ?? "n/a";
      const mean = item.mean ?? "n/a";
      const state = item.valid ? "Available" : "Review required";
      const reason = item.reason || "Excluded from model features";
      return `<div class="modeling-weight-diagnostic" data-valid="${item.valid ? "true" : "false"}">
        <strong>${escapeHtml(column)}</strong>
        <span>${escapeHtml(state)} · Missing: ${escapeHtml(missing)} · Range: ${escapeHtml(min)}-${escapeHtml(max)} · Mean: ${escapeHtml(mean)}</span>
        <small>${escapeHtml(reason)}</small>
      </div>`;
    })
    .filter(Boolean)
    .join("");
  const journey = [
    ["split", "Sample split", "Train, test and holdout"],
    ["model", "Model Candidates", "Target type and algorithm"],
    ["tuning", "Training strategy", "Tuning budget and sample weights"],
    ["review", "Review and run", "Review settings"],
  ];
  const journeyNav = journey.map(([id, label, note], index) => `<button type="button" class="modeling-journey-node${index === 0 ? " is-active" : ""}" data-modeling-step-jump="${id}" data-step-index="${index + 1}" aria-current="${index === 0 ? "step" : "false"}"${disabledAttr}>
    <span>${index + 1}</span><strong>${label}</strong><small>${note}</small>
  </button>`).join("");
  return `<div class="modeling-setup-panel" data-modeling-weight-form="${escapeHtml(messageId)}" data-modeling-plan-id="${escapeHtml(planId)}" data-modeling-gate-step-id="${escapeHtml(gateStepId)}" data-modeling-current-weight="${escapeHtml(selected)}" data-current-split-config="${escapeHtml(JSON.stringify(splitConfig))}" data-modeling-active-step="split"${snapshotAttrs}${interactive ? "" : ' data-modeling-readonly="true"'}>
    <div class="modeling-setup-head">
      <span class="modeling-setup-title"><small>Model setup</small><strong>Configure training</strong></span>
      <span class="modeling-setup-status"><i></i>${interactive ? "Awaiting confirmation" : "Previous settings"}</span>
    </div>
    <div class="modeling-agent-note"><span aria-hidden="true">✦</span><p><strong>Proposed settings</strong> Review each step, then confirm to start training.</p></div>
    <nav class="modeling-journey" aria-label="Modelling specification steps">${journeyNav}</nav>
    <div class="modeling-step-progress" aria-hidden="true"><i></i></div>
    <div class="modeling-step-error" role="status" aria-live="polite"></div>
    <section class="modeling-journey-stage is-active" data-modeling-stage="split">
      <div class="modeling-stage-heading"><span>01</span><div><strong>Choose the sample split</strong><small>Choose whether to reserve a holdout and set the test share.</small></div></div>
      ${splitControlsHtml || '<div class="modeling-stage-empty">No split preview is available. The existing split will be used.</div>'}
      ${splitCountsHtml ? `<div class="modeling-split-summary"><div class="modeling-section-label">Split column: ${escapeHtml(String(splitSummary?.split_col || "split"))} · Preview</div><div class="modeling-split-grid">${splitCountsHtml}</div></div>` : ""}
      <div class="modeling-stage-actions"><button type="button" class="button compact secondary" data-modeling-step-next="model"${disabledAttr}>Next step: Model candidates</button></div>
    </section>
    <section class="modeling-journey-stage" data-modeling-stage="model">
      <div class="modeling-stage-heading"><span>02</span><div><strong>Choose target and algorithms</strong><small>Review algorithm availability and select candidates for comparison.</small></div></div>
      ${targetAlgorithmControlsHtml}
      ${algorithmHtml ? `<div class="modeling-algorithm-grid">${algorithmHtml}</div>` : ""}
      ${guidanceHtml ? `<div class="modeling-guidance-list">${guidanceHtml}</div>` : ""}
      <div class="modeling-stage-actions"><button type="button" class="button compact ghost" data-modeling-step-back="split"${disabledAttr}>Back: sample split</button><button type="button" class="button compact secondary" data-modeling-step-next="tuning"${disabledAttr}>Next step: Training strategy</button></div>
    </section>
    <section class="modeling-journey-stage" data-modeling-stage="tuning">
      <div class="modeling-stage-heading"><span>03</span><div><strong>Set training options</strong><small>Set the number of tuning trials. Sample weights apply to training and are excluded from model features.</small></div></div>
      ${tuningControlsHtml}
      ${diagnosticsHtml ? `<div class="modeling-weight-diagnostics">${diagnosticsHtml}</div>` : ""}
      <div class="modeling-stage-actions"><button type="button" class="button compact ghost" data-modeling-step-back="model"${disabledAttr}>Back: algorithms</button><button type="button" class="button compact secondary" data-modeling-step-next="review"${disabledAttr}>Next: review</button></div>
    </section>
    <section class="modeling-journey-stage" data-modeling-stage="review">
      <div class="modeling-stage-heading"><span>04</span><div><strong>Review settings</strong><small>Confirm these settings to begin feature selection, tuning, training and evaluation.</small></div></div>
      <div class="modeling-spec-grid">${specChips}</div>
      ${warningHtml ? `<div class="modeling-setup-warnings">${warningHtml}</div>` : ""}
      ${reasonControlHtml}
      <div class="modeling-setup-foot gate-action-bar">
        <button type="button" class="button compact ghost" data-modeling-step-back="tuning"${disabledAttr}>Back: training options</button>
        <span>Changes will rerun the affected steps.</span>
        <button type="button" class="button compact secondary modeling-weight-adjust"${interactive ? ` data-modeling-weight-adjust="${escapeHtml(messageId)}"` : disabledAttr}>${interactive ? "Confirm and run" : "Previous settings"}</button>
      </div>
    </section>
  </div>`;
}

export async function submitModelingWeightAdjust(button, context = {}) {
  const form = button.closest(".modeling-setup-panel");
  const taskId = typeof context.getSelectedTaskId === "function"
    ? context.getSelectedTaskId()
    : context.selectedTaskId;
  const api = context.api;
  const setActionStatus = context.setActionStatus || (() => {});
  if (!form || !taskId || typeof api !== "function") return;
  if (form.dataset.modelingReadonly === "true") {
    setActionStatus("These settings are from a previous step. Use the latest confirmation to make changes.", "error");
    return;
  }
  const splitError = modelingSplitInputError(form);
  if (splitError) {
    setActionStatus(splitError, "error");
    return;
  }
  const adjustParams = collectModelingSetupAdjustParams(form);
  const hasAdjustments = Object.keys(adjustParams).length > 0;
  const reason = String(form.querySelector(".modeling-override-reason-input")?.value || "").trim();
  const structuralKeys = ["target_type", "recipes", "n_trials"];
  if (Array.isArray(adjustParams.recipes) && !adjustParams.recipes.length) {
    setActionStatus("Please select at least one training algorithm.", "error");
    return;
  }
  const targetType = selectedModelingTargetType(form);
  const selectedRecipes = selectedModelingRecipes(form);
  const mismatchedRecipe = selectedRecipes.find((recipe) => recipeFamily(recipe) !== targetType);
  if (mismatchedRecipe) {
    setActionStatus(`Algorithm ${mismatchedRecipe} does not support target type ${targetType}. Select a compatible algorithm.`, "error");
    return;
  }
  if (structuralKeys.some((key) => Object.prototype.hasOwnProperty.call(adjustParams, key)) && reason.length < 4) {
    setActionStatus("Enter a reason of at least four characters for changes to the target, algorithms or tuning trials.", "error");
    return;
  }
  const expectedStepId = form.dataset.modelingGateStepId || "";
  const expectedPlanId = form.dataset.modelingPlanId || "";
  const confirmationSnapshot = confirmationSnapshotFromControl(
    form,
    { requireStep: true },
  );
  if (!expectedPlanId || !expectedStepId || !confirmationSnapshot) {
    setActionStatus("Refresh the task to load the current confirmation, then try again.", "error");
    return;
  }
  button.disabled = true;
  // UX-1: this adjust reruns the driver turn (now job-wrapped, REL-1) and can
  // rerun screen/tune/train downstream, so give immediate busy feedback, poll
  // agent messages so intermediate step content streams in, and force the plan
  // rail to re-fetch on a short interval so the running step doesn't look frozen.
  const pollAgentMessagesUntilSettled = context.pollAgentMessagesUntilSettled || (() => Promise.resolve());
  const resetFetchThrottle = context.resetFetchThrottle || (() => {});
  const renderWorkflowStepper = context.renderWorkflowStepper || (() => {});
  setActionStatus("Applying model settings…", "busy");
  let planRailTimer = null;
  if (typeof setInterval === "function") {
    planRailTimer = setInterval(() => {
      resetFetchThrottle(taskId);
      renderWorkflowStepper({ force: true });
    }, 1500);
  }
  try {
    const requestPromise = api(`/api/tasks/${taskId}/agent/messages`, {
      method: "POST",
      body: JSON.stringify({
        content: hasAdjustments ? (reason ? `Model settings changed: ${reason}` : "Update model settings") : "Confirm.",
        ui_action: hasAdjustments ? "apply_modeling_setup" : "confirm_gate",
        ...(hasAdjustments ? { adjust_params: adjustParams } : {}),
        expected_plan_id: expectedPlanId,
        expected_step_id: expectedStepId,
        ...confirmationSnapshot,
        acceptance_mode: typeof context.agentAcceptanceModeValue === "function"
          ? context.agentAcceptanceModeValue()
          : (context.acceptanceMode || "manual"),
      }),
    });
    const streamPollPromise = pollAgentMessagesUntilSettled(taskId, requestPromise, { preserveOptimistic: true });
    const result = await requestPromise;
    await streamPollPromise;
    if (typeof context.setAgentMessages === "function") {
      context.setAgentMessages(result.messages);
    }
    if (typeof context.renderAgentConversation === "function") {
      context.renderAgentConversation();
    }
  } catch (error) {
    const conflictHandled = await refreshAfterConfirmationConflict(error, {
      taskId,
      refreshAgentMessages: context.refreshAgentMessages,
      setActionStatus,
    });
    if (!conflictHandled) {
      button.disabled = false;
      setActionStatus(error?.message || "Could not apply model settings", "error");
    }
  } finally {
    if (planRailTimer !== null) clearInterval(planRailTimer);
    resetFetchThrottle(taskId);
    renderWorkflowStepper({ force: true });
  }
}

function collectModelingSetupAdjustParams(form) {
  const params = {};
  const splitMode = form.querySelector(".modeling-split-mode:checked");
  if (splitMode) {
    const currentSplit = normalizeSplitConfig(parseSplitConfig(form.dataset.currentSplitConfig));
    const selectedSplit = selectedSplitConfig(form, currentSplit);
    if (JSON.stringify(selectedSplit) !== JSON.stringify(currentSplit)) {
      params.split_config = selectedSplit;
    }
  }
  const target = form.querySelector(".modeling-target-select");
  if (target) {
    const value = String(target.value || "").trim();
    const current = String(target.getAttribute("data-current-target-type") || "").trim();
    if (value && value !== current) params.target_type = value;
  }
  const nTrials = form.querySelector(".modeling-n-trials-input");
  if (nTrials) {
    const rawValue = String(nTrials.value ?? "").trim();
    const rawCurrent = String(nTrials.getAttribute("data-current-n-trials") ?? "").trim();
    if (rawValue) {
      const value = Number(rawValue);
      const current = rawCurrent ? Number(rawCurrent) : null;
      if (Number.isFinite(value) && value !== current) params.n_trials = value;
    }
  }
  const recipeControl = form.querySelector(".modeling-recipe-control");
  if (recipeControl) {
    const selected = [...recipeControl.querySelectorAll(".modeling-recipe-pick:checked")]
      .map((input) => String(input.value || "").trim())
      .filter(Boolean);
    const current = String(recipeControl.dataset.currentRecipes || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const selectedSet = [...new Set(selected)].sort();
    const currentSet = [...new Set(current)].sort();
    if (selectedSet.join(",") !== currentSet.join(",")) params.recipes = selected;
  }
  const picked = form.querySelector(".modeling-weight-pick:checked");
  const sampleWeightCol = picked ? String(picked.value || "").trim() : "";
  const currentWeight = String(form.dataset.modelingCurrentWeight || "").trim();
  if (sampleWeightCol !== currentWeight) params.sample_weight_col = sampleWeightCol;
  return params;
}

function parseSplitConfig(value) {
  try {
    const parsed = JSON.parse(String(value || "{}"));
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function normalizeSplitConfig(config = {}) {
  const normalized = {};
  if (Number.isFinite(Number(config.test_size))) normalized.test_size = Number(config.test_size);
  if (config.oot_by_time) normalized.oot_by_time = String(config.oot_by_time);
  if (config.random_oot) normalized.random_oot = true;
  if ((config.oot_by_time || config.random_oot) && Number.isFinite(Number(config.oot_size))) {
    normalized.oot_size = Number(config.oot_size);
  }
  if (Array.isArray(config.group_cols) && config.group_cols.length) {
    normalized.group_cols = config.group_cols.map(String);
  }
  if (Array.isArray(config.rules) && config.rules.length) normalized.rules = config.rules;
  return normalized;
}

function selectedSplitConfig(form, current) {
  const mode = String(form.querySelector(".modeling-split-mode:checked")?.value || "none");
  const testPercent = Number(form.querySelector(".modeling-test-size-input")?.value || 25);
  const ootPercent = Number(form.querySelector(".modeling-oot-size-input")?.value || 20);
  const timeColumn = String(form.querySelector(".modeling-time-column-select")?.value || "").trim();
  const selected = { ...current };
  // An empty split_config means "keep the setup's existing 75/25 split". The
  // form renders that effective default as 25%; leaving it untouched must be a
  // confirmation, not a synthetic adjustment that reruns the same gate.
  if (Object.prototype.hasOwnProperty.call(current, "test_size") || testPercent !== 25) {
    selected.test_size = testPercent / 100;
  } else {
    delete selected.test_size;
  }
  delete selected.oot_by_time;
  delete selected.random_oot;
  delete selected.oot_size;
  if (mode === "time") {
    selected.oot_by_time = timeColumn;
    selected.oot_size = ootPercent / 100;
  } else if (mode === "random") {
    selected.random_oot = true;
    selected.oot_size = ootPercent / 100;
  }
  return normalizeSplitConfig(selected);
}

function modelingSplitInputError(form) {
  const modeControl = form.querySelector(".modeling-split-mode:checked");
  if (!modeControl) return "";
  const testPercent = Number(form.querySelector(".modeling-test-size-input")?.value);
  if (!Number.isFinite(testPercent) || testPercent <= 0 || testPercent > 50) {
    return "The test set must be greater than 0% and not exceed 50%.";
  }
  const mode = String(modeControl.value || "none");
  if (mode !== "none") {
    const ootPercent = Number(form.querySelector(".modeling-oot-size-input")?.value);
    if (!Number.isFinite(ootPercent) || ootPercent <= 0 || ootPercent > 50) {
      return "Holdout share must be greater than 0% and at most 50%.";
    }
  }
  if (mode === "time" && !String(form.querySelector(".modeling-time-column-select")?.value || "").trim()) {
    return "Select a time column for the time-based holdout.";
  }
  return "";
}

function selectedModelingTargetType(form) {
  const target = form.querySelector(".modeling-target-select");
  return String(target?.value || "binary").trim() || "binary";
}

function selectedModelingRecipes(form) {
  const recipeControl = form.querySelector(".modeling-recipe-control");
  if (!recipeControl) return [];
  return [...recipeControl.querySelectorAll(".modeling-recipe-pick:checked")]
    .map((input) => String(input.value || "").trim())
    .filter(Boolean);
}

function uniqueRecipeChoices(items) {
  const seen = new Set();
  const choices = [];
  for (const item of items) {
    const recipe = String(item.recipe || "");
    if (!recipe || seen.has(recipe)) continue;
    seen.add(recipe);
    choices.push(item);
  }
  return choices;
}

function recipeFamily(recipe) {
  const normalized = String(recipe || "").trim().toLowerCase();
  if (normalized.endsWith("_regressor")) return "continuous";
  if (normalized.endsWith("_multiclass")) return "multiclass";
  return "binary";
}

function humanMetricPolicy(policy) {
  const value = String(policy || "-").trim();
  const normalized = value.toLocaleLowerCase();
  if (normalized.includes("overfit") && normalized.includes("test") && normalized.includes("ks")) {
    return "Test KS with overfitting penalty";
  }
  if (normalized === "oot_ks" || normalized.includes("oot ks")) return "OOT KS";
  if (normalized === "test_ks" || normalized.includes("test ks")) return "Test KS";
  if (normalized.includes("auc")) return normalized.includes("oot") ? "OOT AUC" : "AUC";
  return value;
}

export function activateModelingJourneyStep(form, requestedStep) {
  if (!form || form.dataset.modelingReadonly === "true") return false;
  const stages = [...form.querySelectorAll("[data-modeling-stage]")];
  const nodes = [...form.querySelectorAll("[data-modeling-step-jump]")];
  const targetIndex = stages.findIndex((stage) => stage.dataset.modelingStage === requestedStep);
  if (targetIndex < 0) return false;
  stages.forEach((stage, index) => stage.classList.toggle("is-active", index === targetIndex));
  nodes.forEach((node, index) => {
    node.classList.toggle("is-active", index === targetIndex);
    node.classList.toggle("is-complete", index < targetIndex);
    node.setAttribute("aria-current", index === targetIndex ? "step" : "false");
  });
  form.dataset.modelingActiveStep = requestedStep;
  const progress = form.querySelector(".modeling-step-progress > i");
  if (progress) progress.style.setProperty("--modeling-progress", `${targetIndex / Math.max(stages.length - 1, 1) * 100}%`);
  form.querySelector("[data-modeling-stage].is-active")?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  return true;
}

export function handleModelingSetupInteraction(event) {
  const form = event.target?.closest?.(".modeling-setup-panel");
  if (!form || form.dataset.modelingReadonly === "true") return;
  if (event.type === "input" && event.target?.matches?.(".modeling-n-trials-input")) {
    const value = String(event.target.value || "-");
    const liveValue = form.querySelector('[data-modeling-live-value="trials"]');
    if (liveValue) liveValue.textContent = value;
    return;
  }
  const control = event.target?.closest?.("[data-modeling-step-next], [data-modeling-step-back], [data-modeling-step-jump]");
  if (!control) return;
  event.preventDefault();
  const target = control.dataset.modelingStepNext
    || control.dataset.modelingStepBack
    || control.dataset.modelingStepJump;
  const error = form.querySelector(".modeling-step-error");
  if (control.dataset.modelingStepNext && form.dataset.modelingActiveStep === "split") {
    const detail = modelingSplitInputError(form);
    if (detail) {
      if (error) error.textContent = detail;
      return;
    }
  }
  if (control.dataset.modelingStepNext && form.dataset.modelingActiveStep === "model") {
    const recipes = selectedModelingRecipes(form);
    const targetType = selectedModelingTargetType(form);
    const mismatch = recipes.find((recipe) => recipeFamily(recipe) !== targetType);
    const detail = !recipes.length
      ? "Please select at least one candidate algorithm first."
      : mismatch
        ? `Algorithm ${mismatch} does not support target type ${targetType}.`
        : "";
    if (detail) {
      if (error) error.textContent = detail;
      return;
    }
  }
  if (error) error.textContent = "";
  activateModelingJourneyStep(form, target);
}

export function handleModelingWeightAdjustClick(event, context = {}) {
  const button = event.target?.closest?.("[data-modeling-weight-adjust]");
  if (!button) return;
  event.preventDefault();
  return submitModelingWeightAdjust(button, context);
}
