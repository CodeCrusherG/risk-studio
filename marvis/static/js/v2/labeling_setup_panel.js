const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function requiredElement(getElementById, id) {
  const element = getElementById(id);
  if (!element) throw new Error(`labeling setup panel element is missing: ${id}`);
  return element;
}

function trimmedValue(element) {
  return String(element?.value || "").trim();
}

function nonNegativeInteger(element, label, { positive = false } = {}) {
  const value = Number(trimmedValue(element));
  if (!Number.isInteger(value) || value < (positive ? 1 : 0)) {
    throw new Error(`${label} must be a ${positive ? "positive" : "non-negative"} integer.`);
  }
  return value;
}

function validIsoDate(value) {
  if (!ISO_DATE_PATTERN.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function labelingUiState(messages = []) {
  const items = Array.isArray(messages) ? messages : [];
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const message = items[index];
    if (message?.role !== "assistant") continue;
    const metadata = message?.metadata || {};
    const resolution = metadata.labeling_proposal_resolution;
    if (resolution === "confirmed") return { mode: "complete", proposal: null };
    if (resolution === "stale" || resolution === "cancelled") {
      return { mode: "setup", proposal: null };
    }
    if (
      metadata.kind === "labeling_preplan_confirmation"
      && metadata.labeling_proposal
      && typeof metadata.labeling_proposal === "object"
    ) {
      return { mode: "confirm", proposal: metadata.labeling_proposal };
    }
  }
  return { mode: "setup", proposal: null };
}

function workspaceAvailability(workspaceController, task) {
  const state = workspaceController?.getState?.() || {};
  const snapshot = state.serverSnapshot;
  if (state.loading || state.saving) {
    return { ready: false, message: "Wait for the data workspace to finish loading or saving.", state, snapshot };
  }
  if (state.dirty) {
    return {
      ready: false,
      message: "Save or discard workspace changes before submitting label settings.",
      state,
      snapshot,
    };
  }
  if (!snapshot || snapshot.task_id !== task?.id) {
    return { ready: false, message: "Load the current task’s data workspace first.", state, snapshot };
  }
  if (
    !String(snapshot.active_dataset_id || "").trim()
    || !SHA256_PATTERN.test(String(snapshot.active_dataset_content_hash || ""))
  ) {
    return { ready: false, message: "Select a dataset and save the workspace.", state, snapshot };
  }
  if (
    !Number.isInteger(snapshot.revision)
    || snapshot.revision < 0
    || !Number.isInteger(snapshot.analysis_generation)
    || snapshot.analysis_generation < 0
  ) {
    return { ready: false, message: "The workspace version is invalid. Refresh and try again.", state, snapshot };
  }
  return { ready: true, message: "Set the observation window, performance window and adverse-outcome rule, then review the proposed labels.", state, snapshot };
}

function proposalSummary(proposal = {}) {
  const maturity = proposal.maturity && typeof proposal.maturity === "object"
    ? proposal.maturity
    : {};
  const immature = Array.isArray(maturity.immature_cohorts)
    ? maturity.immature_cohorts
    : [];
  const maturityText = maturity.all_matured
    ? "All cohorts meet the maturity requirement"
    : `Cohorts below the maturity requirement: ${immature.length} (${immature.join(", ") || "see details"})`;
  return [
    `Source: ${proposal.source_dataset_name || "Selected dataset"}`,
    `Rows at cutoff: ${Number(proposal.rows_at_as_of || 0)}`,
    `Rows after cutoff excluded: ${Number(proposal.rows_excluded_after_as_of || 0)}`,
    `Rule: ${proposal.rule_summary || "Not provided"}`,
    maturityText,
  ].join(" · ");
}

export function createLabelingSetupPanel(dependencies = {}) {
  const getElementById = dependencies.getElementById || ((id) => document.getElementById(id));
  const request = dependencies.api;
  const workspaceController = dependencies.workspaceController;
  const getSelectedTask = dependencies.getSelectedTask || (() => null);
  const getAgentMessages = dependencies.getAgentMessages || (() => []);
  const onMessages = dependencies.onMessages || (() => {});
  const onSubmitted = dependencies.onSubmitted || (() => {});
  const onError = dependencies.onError || (() => {});
  if (typeof request !== "function") throw new TypeError("labeling setup panel requires api");
  if (!workspaceController || typeof workspaceController.getState !== "function") {
    throw new TypeError("labeling setup panel requires a data workspace controller");
  }

  const elements = {
    root: requiredElement(getElementById, "labelingSetupPanel"),
    form: requiredElement(getElementById, "labelingSetupForm"),
    proposalPanel: requiredElement(getElementById, "labelingProposalPanel"),
    status: requiredElement(getElementById, "labelingSetupStatus"),
    submit: requiredElement(getElementById, "labelingSetupSubmit"),
    proposalSummary: requiredElement(getElementById, "labelingProposalSummary"),
    confirm: requiredElement(getElementById, "labelingProposalConfirm"),
    idCol: requiredElement(getElementById, "labelingIdCol"),
    mobCol: requiredElement(getElementById, "labelingMobCol"),
    cohortCol: requiredElement(getElementById, "labelingCohortCol"),
    dateCol: requiredElement(getElementById, "labelingDateCol"),
    asOfDate: requiredElement(getElementById, "labelingAsOfDate"),
    targetCol: requiredElement(getElementById, "labelingTargetCol"),
    observationWindow: requiredElement(getElementById, "labelingObservationWindow"),
    performanceWindow: requiredElement(getElementById, "labelingPerformanceWindow"),
    atMob: requiredElement(getElementById, "labelingAtMob"),
    ruleKind: requiredElement(getElementById, "labelingRuleKind"),
    dpdFields: requiredElement(getElementById, "labelingDpdFields"),
    dpdCol: requiredElement(getElementById, "labelingDpdCol"),
    thresholdDpd: requiredElement(getElementById, "labelingThresholdDpd"),
    statusFields: requiredElement(getElementById, "labelingStatusFields"),
    statusCol: requiredElement(getElementById, "labelingStatusCol"),
    thresholdStatus: requiredElement(getElementById, "labelingThresholdStatus"),
    states: requiredElement(getElementById, "labelingStates"),
  };

  let submitting = false;

  function setStatus(message = "", kind = "") {
    elements.status.textContent = message;
    elements.status.className = `labeling-setup-status${kind ? ` ${kind}` : ""}`;
  }

  function renderRuleFields() {
    const usesStatus = trimmedValue(elements.ruleKind).toLowerCase() === "status";
    elements.dpdFields.hidden = usesStatus;
    elements.statusFields.hidden = !usesStatus;
  }

  function renderAvailability() {
    const task = getSelectedTask();
    const uiState = labelingUiState(getAgentMessages());
    const taskVisible = task?.task_type === "data_join";
    const visible = taskVisible && uiState.mode !== "complete";
    const availability = workspaceAvailability(workspaceController, task);

    elements.root.hidden = !visible;
    elements.form.hidden = !visible || uiState.mode !== "setup";
    elements.proposalPanel.hidden = !visible || uiState.mode !== "confirm";
    renderRuleFields();

    if (!visible) {
      elements.submit.disabled = true;
      elements.confirm.disabled = true;
      return false;
    }
    if (uiState.mode === "confirm") {
      elements.proposalSummary.textContent = proposalSummary(uiState.proposal);
      elements.submit.disabled = true;
      elements.confirm.disabled = submitting || !availability.ready;
      setStatus(
        availability.ready
          ? "Validation is complete. Review and confirm the proposal to generate the labeling plan."
          : availability.message,
        availability.ready ? "success" : "warning",
      );
      return true;
    }
    elements.confirm.disabled = true;
    elements.submit.disabled = submitting || !availability.ready;
    setStatus(availability.message, availability.ready ? "" : "warning");
    return true;
  }

  function readContract(snapshot) {
    const contract = {
      dataset_id: String(snapshot.active_dataset_id),
      expected_content_hash: String(snapshot.active_dataset_content_hash),
      workspace_revision: snapshot.revision,
      analysis_generation: snapshot.analysis_generation,
    };
    const stringFields = [
      ["Loan ID column", "id_col", elements.idCol],
      ["Months-on-book column", "mob_col", elements.mobCol],
      ["Cohort column", "cohort_col", elements.cohortCol],
      ["Snapshot date column", "date_col", elements.dateCol],
      ["Target label column", "target_col", elements.targetCol],
    ];
    for (const [label, key, element] of stringFields) {
      const value = trimmedValue(element);
      if (!value) throw new Error(`Enter ${label}.`);
      contract[key] = value;
    }

    const ruleKind = trimmedValue(elements.ruleKind).toLowerCase();
    if (ruleKind !== "dpd" && ruleKind !== "status") {
      throw new Error("Choose a days-past-due or ordered-status rule.");
    }
    contract.rule_kind = ruleKind;
    if (ruleKind === "dpd") {
      const dpdCol = trimmedValue(elements.dpdCol);
      const thresholdDpd = Number(trimmedValue(elements.thresholdDpd));
      if (!dpdCol) throw new Error("Enter the days-past-due column.");
      if (!Number.isFinite(thresholdDpd) || thresholdDpd < 0) {
        throw new Error("The days-past-due threshold must be a non-negative number.");
      }
      contract.dpd_col = dpdCol;
      contract.threshold_dpd = thresholdDpd;
    } else {
      const statusCol = trimmedValue(elements.statusCol);
      const thresholdStatus = trimmedValue(elements.thresholdStatus);
      const states = trimmedValue(elements.states)
        .split(/[,,,\n]+/)
        .map((value) => value.trim())
        .filter(Boolean);
      if (!statusCol) throw new Error("Enter the status column.");
      if (!thresholdStatus) throw new Error("Enter the first status classified as an adverse outcome.");
      if (states.length < 2) throw new Error("Enter at least two statuses, ordered from best to worst.");
      if (new Set(states).size !== states.length) throw new Error("Each status must appear only once in the ordered list.");
      if (!states.includes(thresholdStatus)) throw new Error("The adverse-outcome threshold must appear in the ordered status list.");
      contract.status_col = statusCol;
      contract.threshold_status = thresholdStatus;
      contract.states = states;
    }

    const asOfDate = trimmedValue(elements.asOfDate);
    if (!validIsoDate(asOfDate)) throw new Error("Enter a valid cutoff date in YYYY-MM-DD format.");
    contract.as_of_date = asOfDate;
    contract.observation_window = nonNegativeInteger(elements.observationWindow, "Observation window");
    contract.performance_window = nonNegativeInteger(
      elements.performanceWindow,
      "Performance window",
      { positive: true },
    );
    contract.at_mob = nonNegativeInteger(elements.atMob, "Label month (MOB)", { positive: true });
    if (contract.at_mob <= contract.observation_window) {
      throw new Error("The label month must be later than the observation window.");
    }
    if (contract.at_mob > contract.observation_window + contract.performance_window) {
      throw new Error("The label month cannot exceed the observation window plus the performance window.");
    }
    return contract;
  }

  async function submit(event) {
    event?.preventDefault?.();
    if (submitting) return false;
    const task = getSelectedTask();
    if (!task?.id || task.task_type !== "data_join") {
      setStatus("Select a data-processing task before submitting label settings.", "error");
      return false;
    }
    const availability = workspaceAvailability(workspaceController, task);
    if (!availability.ready) {
      setStatus(availability.message, "warning");
      return false;
    }

    let labelingRequest;
    try {
      labelingRequest = readContract(availability.snapshot);
    } catch (error) {
      setStatus(error.message || "Complete the label settings before submitting.", "error");
      return false;
    }

    submitting = true;
    elements.submit.disabled = true;
    setStatus("Checking the cutoff date, columns and cohort maturity…", "busy");
    try {
      const result = await request(`api/tasks/${task.id}/agent/messages`, {
        method: "POST",
        body: JSON.stringify({
          content: "Submit label settings for validation",
          labeling_request: labelingRequest,
        }),
      });
      if (Array.isArray(result?.messages)) onMessages(result.messages);
      await onSubmitted(result);
      return true;
    } catch (error) {
      setStatus(error?.message || "Could not submit the label settings. Try again.", "error");
      onError(error);
      return false;
    } finally {
      submitting = false;
      renderAvailability();
    }
  }

  async function confirm() {
    if (submitting) return false;
    const task = getSelectedTask();
    const uiState = labelingUiState(getAgentMessages());
    const availability = workspaceAvailability(workspaceController, task);
    if (!task?.id || task.task_type !== "data_join" || uiState.mode !== "confirm") {
      setStatus("No label proposal is available to confirm.", "error");
      return false;
    }
    if (!availability.ready) {
      setStatus(availability.message, "warning");
      return false;
    }
    submitting = true;
    elements.confirm.disabled = true;
    setStatus("Confirming the proposal and generating the labeling plan…", "busy");
    try {
      const result = await request(`api/tasks/${task.id}/agent/messages`, {
        method: "POST",
        body: JSON.stringify({ content: "Confirm." }),
      });
      if (Array.isArray(result?.messages)) onMessages(result.messages);
      await onSubmitted(result);
      return true;
    } catch (error) {
      setStatus(error?.message || "Could not confirm the label proposal. Try again.", "error");
      onError(error);
      return false;
    } finally {
      submitting = false;
      renderAvailability();
    }
  }

  elements.ruleKind.addEventListener("change", renderRuleFields);
  elements.form.addEventListener("submit", submit);
  elements.confirm.addEventListener("click", confirm);
  workspaceController.subscribe?.(() => renderAvailability());
  renderAvailability();

  return { confirm, renderAvailability, submit };
}
