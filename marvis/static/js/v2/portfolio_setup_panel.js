function requiredElement(getElementById, id) {
  const element = getElementById(id);
  if (!element) throw new Error(`portfolio setup panel element is missing: ${id}`);
  return element;
}

function trimmedValue(element) {
  return String(element?.value || "").trim();
}

function portfolioGateExists(messages = []) {
  return (Array.isArray(messages) ? messages : []).some((message) => (
    message?.role === "assistant"
    && message?.metadata
    && typeof message.metadata.portfolio_states === "object"
  ));
}

export function portfolioTurnUsesDeterministicRoute(task, messages = []) {
  if (task?.task_type !== "portfolio") return false;
  for (let index = (Array.isArray(messages) ? messages.length : 0) - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.role !== "assistant") continue;
    const metadata = message?.metadata || {};
    return metadata.kind === "portfolio_setup_required"
      || metadata.kind === "gate"
      || Boolean(metadata.portfolio_states);
  }
  return false;
}

export function createPortfolioSetupPanel(dependencies = {}) {
  const getElementById = dependencies.getElementById || ((id) => document.getElementById(id));
  const request = dependencies.api;
  const getSelectedTask = dependencies.getSelectedTask || (() => null);
  const getAgentMessages = dependencies.getAgentMessages || (() => []);
  const onMessages = dependencies.onMessages || (() => {});
  const onSubmitted = dependencies.onSubmitted || (() => {});
  const onError = dependencies.onError || (() => {});
  if (typeof request !== "function") throw new TypeError("portfolio setup panel requires api");

  const elements = {
    root: requiredElement(getElementById, "portfolioSetupPanel"),
    form: requiredElement(getElementById, "portfolioSetupForm"),
    status: requiredElement(getElementById, "portfolioSetupStatus"),
    submit: requiredElement(getElementById, "portfolioSetupSubmit"),
    idCol: requiredElement(getElementById, "portfolioIdCol"),
    snapshotCol: requiredElement(getElementById, "portfolioSnapshotCol"),
    bucketCol: requiredElement(getElementById, "portfolioBucketCol"),
    balanceCol: requiredElement(getElementById, "portfolioBalanceCol"),
    segmentCol: requiredElement(getElementById, "portfolioSegmentCol"),
    lossState: requiredElement(getElementById, "portfolioLossState"),
    lgd: requiredElement(getElementById, "portfolioLgd"),
    horizonMonths: requiredElement(getElementById, "portfolioHorizonMonths"),
    scoreCol: requiredElement(getElementById, "portfolioScoreCol"),
    experimentId: requiredElement(getElementById, "portfolioExperimentId"),
  };

  let submitting = false;

  function setStatus(message = "", kind = "") {
    elements.status.textContent = message;
    elements.status.className = `portfolio-setup-status${kind ? ` ${kind}` : ""}`;
  }

  function renderAvailability() {
    const task = getSelectedTask();
    const visible = task?.task_type === "portfolio"
      && !portfolioGateExists(getAgentMessages());
    elements.root.hidden = !visible;
    elements.submit.disabled = submitting || !visible;
    return visible;
  }

  function readContract() {
    const stringFields = [
      ["Loan ID column", "id_col", elements.idCol],
      ["Snapshot month column", "snapshot_col", elements.snapshotCol],
      ["Delinquency bucket column", "bucket_col", elements.bucketCol],
      ["Balance or EAD column", "balance_col", elements.balanceCol],
      ["Segment column", "segment_col", elements.segmentCol],
      ["Loss state", "loss_state", elements.lossState],
    ];
    const contract = {};
    for (const [label, key, element] of stringFields) {
      const value = trimmedValue(element);
      if (!value) throw new Error(`Enter ${label}.`);
      contract[key] = value;
    }

    const lgd = Number(trimmedValue(elements.lgd));
    if (!Number.isFinite(lgd) || lgd < 0 || lgd > 1) {
      throw new Error("LGD must be between 0 and 1.");
    }
    const horizonMonths = Number(trimmedValue(elements.horizonMonths));
    if (!Number.isInteger(horizonMonths) || horizonMonths <= 0) {
      throw new Error("The forecast horizon must be a positive number of whole months.");
    }
    contract.lgd = lgd;
    contract.horizon_months = horizonMonths;

    const scoreCol = trimmedValue(elements.scoreCol);
    const experimentId = trimmedValue(elements.experimentId);
    if (Boolean(scoreCol) !== Boolean(experimentId)) {
      throw new Error("Provide both the score column and experiment ID, or leave both blank.");
    }
    if (scoreCol) {
      contract.score_col = scoreCol;
      contract.experiment_id = experimentId;
    }
    return contract;
  }

  async function submit(event) {
    event?.preventDefault?.();
    if (submitting) return false;
    const task = getSelectedTask();
    if (!task?.id || task.task_type !== "portfolio") {
      setStatus("Select a portfolio analysis task before submitting.", "error");
      return false;
    }

    let portfolioRequest;
    try {
      portfolioRequest = readContract();
    } catch (error) {
      setStatus(error.message || "Complete the portfolio settings before submitting.", "error");
      return false;
    }

    submitting = true;
    elements.submit.disabled = true;
    setStatus("Validating portfolio columns and settings…", "busy");
    try {
      const result = await request(`api/tasks/${task.id}/agent/messages`, {
        method: "POST",
        body: JSON.stringify({
          content: "Submit portfolio settings for validation",
          portfolio_request: portfolioRequest,
        }),
      });
      if (Array.isArray(result?.messages)) onMessages(result.messages);
      setStatus("Settings validated. Review and confirm the delinquency bucket order.", "success");
      await onSubmitted(result);
      return true;
    } catch (error) {
      setStatus(error?.message || "Could not submit the portfolio settings. Try again.", "error");
      onError(error);
      return false;
    } finally {
      submitting = false;
      renderAvailability();
    }
  }

  elements.form.addEventListener("submit", submit);
  renderAvailability();

  return {
    renderAvailability,
    submit,
  };
}
