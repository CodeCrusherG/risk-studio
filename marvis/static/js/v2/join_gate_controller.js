import { escapeHtml } from "../ui-utils.js";
import { datasetTableHtml } from "./artifact_view.js";
import {
  confirmationSnapshotAttributes,
  confirmationSnapshotFromControl,
  refreshAfterConfirmationConflict,
} from "./driver_gate_confirm.js";

const DEDUP_STRATEGY_LABELS = { first: "Keep the first row", last: "Keep the last row" };
// UX-6: first/last follows raw file row order (not a business timestamp), so the
// picker states that plainly next to the strategy select instead of letting the user
// assume it means something like "most recent".
const DEDUP_STRATEGY_NOTE = "First and last refer to file row order. Sort by the appropriate time column or aggregate the data before joining if row order has no business meaning.";

function joinGateContext(context = {}) {
  return {
    taskId: typeof context.getSelectedTaskId === "function"
      ? context.getSelectedTaskId()
      : context.selectedTaskId,
    api: context.api,
    acceptanceMode: typeof context.agentAcceptanceModeValue === "function"
      ? context.agentAcceptanceModeValue()
      : context.acceptanceMode,
    setActionStatus: context.setActionStatus || (() => {}),
    setAgentMessages: context.setAgentMessages || (() => {}),
    renderAgentConversation: context.renderAgentConversation || (() => {}),
    pollAgentMessagesUntilSettled: context.pollAgentMessagesUntilSettled || (() => Promise.resolve()),
    refreshAgentMessages: context.refreshAgentMessages,
    resetFetchThrottle: context.resetFetchThrottle || (() => {}),
    renderWorkflowStepper: context.renderWorkflowStepper || (() => {}),
    setDriverExecutionBusy: context.setDriverExecutionBusy || (() => {}),
  };
}

// UX-1: the driver turn triggered by these gate submissions now runs inside a
// task job (REL-1) and can take minutes (execute_join / retrain downstream of an
// adjust). Give immediate busy feedback, poll agent messages so intermediate
// step content streams in, and force the plan rail to re-fetch on a short
// interval so the running step doesn't look frozen.
function withDriverTurnBusyFeedback(taskId, context, run) {
  const {
    setActionStatus,
    pollAgentMessagesUntilSettled,
    resetFetchThrottle,
    renderWorkflowStepper,
    setDriverExecutionBusy,
  } = context;
  setDriverExecutionBusy(true, taskId);
  setActionStatus("Running the next step…", "busy");
  let planRailTimer = null;
  if (typeof setInterval === "function") {
    planRailTimer = setInterval(() => {
      resetFetchThrottle(taskId);
      renderWorkflowStepper({ force: true });
    }, 1500);
  }
  const stopPlanRailTicker = () => {
    if (planRailTimer !== null) clearInterval(planRailTimer);
    setDriverExecutionBusy(false, taskId);
    resetFetchThrottle(taskId);
    renderWorkflowStepper({ force: true });
  };
  return run(pollAgentMessagesUntilSettled).finally(stopPlanRailTicker);
}

export function renderJoinC1Form(message, options = {}) {
  const c1 = message?.metadata?.join_c1;
  if (!c1 || !Array.isArray(c1.files) || !c1.files.length) return "";
  const messageId = message?.id ? String(message.id) : "";
  const gateStepId = message?.metadata?.step_id ? String(message.metadata.step_id) : "";
  // UX-2: earlier C1 forms (superseded by a later gate) render read-only so a
  // stale tab cannot re-submit role assignments against an already-advanced
  // step — mirrors the screen/modeling-setup readonly convention.
  const interactive = options.interactive !== false;
  const disabledAttr = interactive ? "" : " disabled aria-disabled=\"true\"";
  const roleSelect = (file, selected) => {
    const datasetId = file?.dataset_id || "";
    const targetOptions = c1TargetColumns(file);
    const opt = (value, label) =>
      `<option value="${value}"${selected === value ? " selected" : ""}>${label}</option>`;
    return (
      `<select class="c1-role" data-c1-dataset="${escapeHtml(datasetId)}" data-c1-target-options="${escapeHtml(JSON.stringify(targetOptions))}"${disabledAttr}>`
      + opt("anchor", "Primary sample table")
      + opt("feature", "Feature table")
      + opt("ignore", "Ignore")
      + "</select>"
    );
  };
  const rows = c1.files
    .map(
      (file) => `<tr>
      <td class="c1-file"><button type="button" class="c1-file-preview" data-c1-preview-dataset="${escapeHtml(file.dataset_id || "")}" data-c1-preview-name="${escapeHtml(file.name || "")}" title="Preview the first 10 rows">${escapeHtml(file.name || "")}</button></td>
      <td>${escapeHtml(String(file.row_count ?? ""))}</td>
      <td>${escapeHtml(String(file.n_cols ?? ""))}</td>
      <td>${file.has_target ? "✓" : ""}</td>
      <td>${roleSelect(file, file.proposed_role || "feature")}</td>
    </tr>`,
    )
    .join("");
  const selectedAnchorId = String(
    c1.anchor_id
      || c1.files.find((file) => file?.proposed_role === "anchor")?.dataset_id
      || "",
  );
  const selectedAnchor = c1.files.find(
    (file) => String(file?.dataset_id || "") === selectedAnchorId,
  );
  const targetOptions = c1TargetOptionsHtml(
    c1TargetColumns(selectedAnchor),
    String(c1.target_col || ""),
  );
  return `<div class="c1-form" data-c1-form="${escapeHtml(messageId)}" data-c1-gate-step-id="${escapeHtml(gateStepId)}"${interactive ? "" : ' data-c1-readonly="true"'}>
    <table class="c1-form-table">
      <thead><tr><th>File</th><th>Rows</th><th>Columns</th><th>Contains target</th><th>Role</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="c1-form-foot gate-action-bar">
      <label class="c1-target-label">Target column<select class="c1-target"${disabledAttr}>${targetOptions}</select></label>
      <button type="button" class="button compact primary c1-confirm"${interactive ? ` data-c1-confirm="${escapeHtml(messageId)}"` : disabledAttr}>${interactive ? "Confirm table roles" : "Previous results"}</button>
    </div>
  </div>`;
}

function c1TargetColumns(file) {
  if (!file || typeof file !== "object") return [];
  const candidates = Array.isArray(file.target_candidates)
    ? file.target_candidates
    : [];
  const source = candidates.length
    ? candidates
    : (Array.isArray(file.columns) ? file.columns : []);
  return [...new Set(source.map(String).filter(Boolean))];
}

function c1TargetOptionsHtml(columns, selected = "") {
  const selectedValue = columns.includes(selected) ? selected : "";
  return ['<option value="">(Not specified)</option>']
    .concat(columns.map(
      (column) => `<option value="${escapeHtml(column)}"${column === selectedValue ? " selected" : ""}>${escapeHtml(column)}</option>`,
    ))
    .join("");
}

function c1RoleTargetColumns(roleSelect) {
  const raw = roleSelect?.getAttribute?.("data-c1-target-options");
  if (raw === null || raw === undefined) return null;
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed)
      ? [...new Set(parsed.map(String).filter(Boolean))]
      : [];
  } catch (_error) {
    return [];
  }
}

export function syncC1TargetOptions(form) {
  const target = form?.querySelector?.(".c1-target");
  if (!target) return;
  const anchors = [...(form.querySelectorAll?.(".c1-role") || [])]
    .filter((select) => select.value === "anchor");
  const columns = anchors.length === 1
    ? (c1RoleTargetColumns(anchors[0]) || [])
    : [];
  const selected = columns.includes(String(target.value || ""))
    ? String(target.value || "")
    : "";
  target.innerHTML = c1TargetOptionsHtml(columns, selected);
  target.value = selected;
}

export function handleC1RoleChange(event) {
  const roleSelect = event.target?.closest?.(".c1-role");
  if (!roleSelect) return false;
  const form = roleSelect.closest?.(".c1-form");
  if (!form || form.dataset?.c1Readonly === "true") return false;
  syncC1TargetOptions(form);
  return true;
}

function c1PreviewDocument(context = {}) {
  if (context.document) return context.document;
  return typeof document !== "undefined" ? document : null;
}

export async function showC1DatasetPreview(button, context = {}) {
  const doc = c1PreviewDocument(context);
  const dialog = doc?.getElementById?.("c1DatasetPreviewDialog");
  const title = doc?.getElementById?.("c1DatasetPreviewTitle");
  const body = doc?.getElementById?.("c1DatasetPreviewBody");
  const datasetId = button?.dataset?.c1PreviewDataset || "";
  const name = button?.dataset?.c1PreviewName || "Data file";
  if (!dialog || !title || !body || !datasetId || typeof context.api !== "function") return;

  title.textContent = `${name} · First 10 Lines`;
  body.innerHTML = '<div class="c1-preview-loading" role="status">Loading preview…</div>';
  if (!dialog.open) dialog.showModal();
  try {
    const preview = await context.api(`/api/datasets/${encodeURIComponent(datasetId)}/preview?rows=10`);
    body.innerHTML = datasetTableHtml(preview);
  } catch (error) {
    body.innerHTML = `<div class="c1-preview-error" role="alert">${escapeHtml(error?.message || "Could not load the preview")}</div>`;
  }
}

export function closeC1DatasetPreview(context = {}) {
  const dialog = c1PreviewDocument(context)?.getElementById?.("c1DatasetPreviewDialog");
  if (dialog?.open) dialog.close();
}

export function handleC1PreviewClick(event, context = {}) {
  const closeButton = event.target?.closest?.("[data-c1-preview-close]");
  if (closeButton) {
    event.preventDefault();
    closeC1DatasetPreview(context);
    return true;
  }
  const previewButton = event.target?.closest?.("[data-c1-preview-dataset]");
  if (!previewButton) return false;
  event.preventDefault();
  void showC1DatasetPreview(previewButton, context);
  return true;
}

export async function submitC1Assignment(button, rawContext = {}) {
  const form = button.closest(".c1-form");
  const { taskId, api, acceptanceMode, setActionStatus, setAgentMessages, renderAgentConversation } = joinGateContext(rawContext);
  if (!form || !taskId || typeof api !== "function") return;
  if (form.dataset.c1Readonly === "true") {
    setActionStatus("This is a previous role assignment. Use the latest review step to make changes.", "error");
    return;
  }
  const anchorIds = [];
  const featureIds = [];
  let anchorSelect = null;
  for (const select of form.querySelectorAll(".c1-role")) {
    const datasetId = select.getAttribute("data-c1-dataset");
    if (select.value === "anchor") {
      anchorIds.push(datasetId);
      anchorSelect = select;
    }
    else if (select.value === "feature") featureIds.push(datasetId);
  }
  if (!anchorIds.length) {
    setActionStatus("Select one primary sample table.", "error");
    return;
  }
  if (anchorIds.length > 1) {
    setActionStatus("Choose one primary sample table. Set the others to Feature table or Ignore.", "error");
    return;
  }
  const targetCol = form.querySelector(".c1-target")?.value || "";
  const anchorTargetColumns = c1RoleTargetColumns(anchorSelect);
  if (
    targetCol
    && anchorTargetColumns !== null
    && !anchorTargetColumns.includes(targetCol)
  ) {
    setActionStatus("The target column must belong to the primary sample table.", "error");
    return;
  }
  button.disabled = true;
  const context = joinGateContext(rawContext);
  try {
    await withDriverTurnBusyFeedback(taskId, context, async (pollAgentMessagesUntilSettled) => {
      const body = {
        content: "[C1]" + JSON.stringify({ anchor_id: anchorIds[0], anchor_ids: anchorIds, feature_ids: featureIds, target_col: targetCol }),
        ui_action: "confirm_roles",
        acceptance_mode: acceptanceMode,
      };
      // C1 is authenticated against the latest pre-plan dataset/content card;
      // a historical PlanDriver step id is neither meaningful nor accepted by
      // the backend confirmation contract.
      const requestPromise = api(`/api/tasks/${taskId}/agent/messages`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      const streamPollPromise = pollAgentMessagesUntilSettled(taskId, requestPromise, { preserveOptimistic: true });
      const result = await requestPromise;
      await streamPollPromise;
      setAgentMessages(result.messages);
      renderAgentConversation();
    });
  } catch (error) {
    button.disabled = false;
    setActionStatus(error?.message || "Could not confirm table roles", "error");
  }
}

export function handleC1ConfirmClick(event, context = {}) {
  const button = event.target?.closest?.("[data-c1-confirm]");
  if (!button) return false;
  event.preventDefault();
  void submitC1Assignment(button, context);
  return true;
}

function joinKeyRate(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(2)}%` : "n/a";
}

export function renderJoinKeyPicker(message, options = {}) {
  const payload = message?.metadata?.join_keys;
  if (!payload || !Array.isArray(payload.features) || !payload.features.length) return "";
  const interactive = options.interactive !== false;
  const disabledAttr = interactive ? "" : ' disabled aria-disabled="true"';
  const messageId = String(message?.id || "");
  const planId = String(message?.metadata?.plan_id || "");
  const stepId = String(message?.metadata?.step_id || "");
  const snapshotAttrs = confirmationSnapshotAttributes(
    message?.metadata?.confirmation_snapshot || {},
  );
  const cards = payload.features.map((feature) => {
    const featureId = String(feature.feature_id || "");
    const featureName = String(feature.feature_name || featureId);
    const selected = new Set((feature.selected_anchor_cols || []).map(String));
    const currentKeys = (feature.current_keys || []).map((pair) => {
      const anchorCol = String(pair.anchor_col || "");
      const featureCol = String(pair.feature_col || "");
      return `<label class="join-key-option">
        <input type="checkbox" data-join-key-feature="${escapeHtml(featureId)}" value="${escapeHtml(anchorCol)}"${selected.has(anchorCol) ? " checked" : ""}${disabledAttr}>
        <span><code>${escapeHtml(anchorCol)}</code><span aria-hidden="true"> = </span><code>${escapeHtml(featureCol)}</code></span>
      </label>`;
    }).join("");
    const alternatives = (feature.alternatives || []).map((alternative) => {
      const anchorCols = (alternative.anchor_cols || []).map(String);
      const pairLabel = (alternative.key_pairs || []).map((pair) => `${pair[0]}=${pair[1]}`).join(" + ");
      const risks = [
        alternative.feature_key_unique ? "Unique keys" : "Duplicate keys",
        alternative.fan_out_detected ? "Row multiplication detected" : "No row multiplication",
      ].join(" · ");
      return `<button type="button" class="join-key-suggestion${alternative.fan_out_detected ? " is-risk" : ""}"
        data-join-key-suggestion="${escapeHtml(featureId)}"
        data-join-key-columns="${escapeHtml(JSON.stringify(anchorCols))}"${disabledAttr}>
        <span>${escapeHtml(pairLabel || anchorCols.join(" + "))}</span>
        <small>Match rate: ${escapeHtml(joinKeyRate(alternative.match_rate))} · ${escapeHtml(risks)}</small>
      </button>`;
    }).join("");
    return `<article class="join-key-card" data-join-key-card="${escapeHtml(featureId)}">
      <header><div><strong>${escapeHtml(featureName)}</strong>${featureName !== featureId ? `<small>${escapeHtml(featureId)}</small>` : ""}</div>
        <span>Current match rate: ${escapeHtml(joinKeyRate(feature.current_match_rate))}</span></header>
      <div class="join-key-options" role="group" aria-label="${escapeHtml(featureName)} join keys">${currentKeys}</div>
      ${alternatives ? `<div class="join-key-alternatives"><span>Suggested keys</span>${alternatives}</div>` : ""}
    </article>`;
  }).join("");
  return `<section class="join-key-picker" data-join-key-form="${escapeHtml(messageId)}" data-join-key-plan-id="${escapeHtml(planId)}" data-join-key-gate-step-id="${escapeHtml(stepId)}"${snapshotAttrs}${interactive ? "" : ' data-join-key-readonly="true"'}>
    <div class="join-key-picker-intro"><strong>Review join keys</strong><p>${payload.features.length} feature tables. Choose one set of keys per table, then rerun join diagnostics.</p></div>
    <div class="join-key-card-list">${cards}</div>
    <div class="gate-action-bar">${interactive
    ? `<button type="button" class="button compact primary" data-join-key-confirm="${escapeHtml(messageId)}">Check selected join keys</button>`
    : '<span class="gate-history-label" aria-label="Previous join result">Previous results</span>'}</div>
  </section>`;
}

export async function submitJoinKeySelection(button, rawContext = {}) {
  const form = button.closest(".join-key-picker");
  const context = joinGateContext(rawContext);
  const { taskId, api, acceptanceMode, setActionStatus, setAgentMessages, renderAgentConversation } = context;
  if (!form || !taskId || typeof api !== "function") return;
  if (form.dataset.joinKeyReadonly === "true") {
    setActionStatus("These are previous join settings. Use the latest review step to change them.", "error");
    return;
  }
  const keyOverrides = {};
  for (const card of form.querySelectorAll("[data-join-key-card]")) {
    const featureId = card.getAttribute("data-join-key-card");
    const selected = [...card.querySelectorAll("[data-join-key-feature]:checked")].map((input) => input.value);
    if (!selected.length) {
      setActionStatus("Select at least one join key for each feature table.", "error");
      return;
    }
    keyOverrides[featureId] = selected;
  }
  const expectedPlanId = form.dataset.joinKeyPlanId || "";
  const expectedStepId = form.dataset.joinKeyGateStepId || "";
  const confirmationSnapshot = confirmationSnapshotFromControl(
    form,
    { requireStep: true },
  );
  if (!expectedPlanId || !expectedStepId || !confirmationSnapshot) {
    setActionStatus("Refresh the task to load the current confirmation, then try again.", "error");
    return;
  }
  button.disabled = true;
  try {
    await withDriverTurnBusyFeedback(taskId, context, async (pollAgentMessagesUntilSettled) => {
      const requestPromise = api(`/api/tasks/${taskId}/agent/messages`, {
        method: "POST",
        body: JSON.stringify({
          content: "Checking join keys…",
          ui_action: "apply_join_keys",
          adjust_params: { key_overrides: keyOverrides },
          expected_plan_id: expectedPlanId,
          expected_step_id: expectedStepId,
          ...confirmationSnapshot,
          acceptance_mode: acceptanceMode,
        }),
      });
      const streamPollPromise = pollAgentMessagesUntilSettled(taskId, requestPromise, { preserveOptimistic: true });
      const result = await requestPromise;
      await streamPollPromise;
      setAgentMessages(result.messages);
      renderAgentConversation();
    });
  } catch (error) {
    const conflictHandled = await refreshAfterConfirmationConflict(error, {
      taskId,
      refreshAgentMessages: context.refreshAgentMessages,
      setActionStatus,
    });
    if (!conflictHandled) {
      button.disabled = false;
      setActionStatus(error?.message || "Could not check join keys", "error");
    }
  }
}

export function handleJoinKeyConfirmClick(event, context = {}) {
  const suggestion = event.target?.closest?.("[data-join-key-suggestion]");
  if (suggestion) {
    event.preventDefault();
    const form = suggestion.closest(".join-key-picker");
    if (form?.dataset.joinKeyReadonly === "true") return true;
    const featureId = suggestion.getAttribute("data-join-key-suggestion");
    let selected = [];
    try { selected = JSON.parse(suggestion.getAttribute("data-join-key-columns") || "[]"); } catch { selected = []; }
    for (const input of form?.querySelectorAll("[data-join-key-feature]") || []) {
      if (input.getAttribute("data-join-key-feature") === featureId) {
        input.checked = selected.includes(input.value);
      }
    }
    return true;
  }
  const button = event.target?.closest?.("[data-join-key-confirm]");
  if (!button) return false;
  event.preventDefault();
  void submitJoinKeySelection(button, context);
  return true;
}

// UX-6: cap the conflicting-column list shown per row so a wide table with many
// disagreeing columns doesn't blow out the picker layout.
const DEDUP_CONFLICT_COLUMNS_DISPLAY_CAP = 5;

// GAP-4: when the task has a registered data dictionary, each conflicting column
// name carries a title tooltip with its business meaning; falls back to the bare
// column name (unchanged behavior) when no dictionary entry exists.
function dedupColumnLabel(column, dictionary) {
  const meaning = dictionary && typeof dictionary === "object" ? dictionary[column] : "";
  return meaning
    ? `<span class="dedup-conflict-column" title="${escapeHtml(String(meaning))}">${escapeHtml(column)}</span>`
    : escapeHtml(column);
}

function dedupConflictColumnsHtml(feature, dictionary) {
  const columns = Array.isArray(feature?.conflict_columns) ? feature.conflict_columns : [];
  if (!columns.length) return "";
  const shown = columns.slice(0, DEDUP_CONFLICT_COLUMNS_DISPLAY_CAP);
  const more = columns.length > shown.length ? ` ${columns.length} columns in total` : "";
  const labels = shown
    .map((column) => `<span class="dedup-conflict-chip">${dedupColumnLabel(column, dictionary)}</span>`)
    .join("");
  return `<div class="dedup-conflict-columns"><span class="dedup-evidence-label">Conflicting columns</span><div class="dedup-conflict-chips">${labels}${more ? `<span class="dedup-conflict-more">${escapeHtml(more.trim())}</span>` : ""}</div></div>`;
}

// UX-6: one real conflicting-value example per feature (e.g. "k=138... Timebalance
// Two rows, 0 and 999."), sourced from the backend's sample_conflicts — replaces the
// previous "conflict_keys number only" black box with a concrete case the user can
// reason about before picking first/last.
function dedupExampleHtml(feature) {
  const examples = Array.isArray(feature?.examples) ? feature.examples : [];
  if (!examples.length) return "";
  const example = examples[0];
  const values = example?.values && typeof example.values === "object" ? example.values : {};
  const valueRows = Object.entries(values).map(([col, rawValues]) => {
    const items = Array.isArray(rawValues) ? rawValues : [rawValues];
    const protectedValue = items.some((item) => /\[REDACTED(?:_[A-Z]+)?\]/.test(String(item)));
    const valueHtml = protectedValue
      ? '<span class="dedup-value-protected">Values differ between rows. Sensitive values are hidden.</span>'
      : `<span class="dedup-value-pair">${items.map((item) => `<code>${escapeHtml(String(item ?? "Empty"))}</code>`).join('<span aria-hidden="true">→</span>')}</span>`;
    return `<div class="dedup-value-row"><span class="dedup-value-column">${escapeHtml(col)}</span>${valueHtml}</div>`;
  }).join("");
  if (!valueRows) return "";
  return `<div class="dedup-example"><div class="dedup-example-key"><span class="dedup-evidence-label">Example conflict</span><code>${escapeHtml(String(example.key || ""))}</code></div><div class="dedup-value-list">${valueRows}</div></div>`;
}

export function renderDedupPicker(message, options = {}) {
  const dedup = message?.metadata?.dedup;
  if (!dedup || !Array.isArray(dedup.features) || !dedup.features.length) return "";
  const messageId = message?.id ? String(message.id) : "";
  const planId = message?.metadata?.plan_id ? String(message.metadata.plan_id) : "";
  const gateStepId = message?.metadata?.step_id ? String(message.metadata.step_id) : "";
  const snapshotAttrs = confirmationSnapshotAttributes(
    message?.metadata?.confirmation_snapshot || {},
  );
  // UX-2: an earlier dedup gate (superseded by a later gate) renders read-only
  // so a stale tab cannot re-submit strategies against an already-advanced
  // step — mirrors the screen/modeling-setup readonly convention.
  const interactive = options.interactive !== false;
  const disabledAttr = interactive ? "" : " disabled aria-disabled=\"true\"";
  const strategies = Array.isArray(dedup.strategies) && dedup.strategies.length ? dedup.strategies : ["first", "last"];
  const cards = dedup.features
    .map((feature) => {
      const fid = String(feature.feature_id);
      const featureName = String(feature.feature_name || fid);
      const conflicts = feature.conflict_keys ? `${feature.conflict_keys} conflicting keys` : "Join keys are not unique";
      const options = strategies
        .map((strategy) => {
          const value = String(strategy);
          return `<option value="${escapeHtml(value)}">${escapeHtml(DEDUP_STRATEGY_LABELS[value] || value)}</option>`;
        })
        .join("");
      const evidence = dedupConflictColumnsHtml(feature, dedup.dictionary) + dedupExampleHtml(feature);
      // UX-6: "Exclude this feature table" — an exit for a table whose conflicts are too dirty to
      // resolve with first/last. Submits the same free-text instruction channel the
      // driver already routes adjust/replan through (agent mode acts on it; manual
      // mode — no LLM — shows the existing canned "Reply "Acknowledge" or transfer" hint, which is
      // still an honest, non-broken response).
      return `<article class="dedup-feature-card">
      <header class="dedup-feature-head">
        <div><strong>${escapeHtml(featureName)}</strong>${featureName !== fid ? `<small>${escapeHtml(fid)}</small>` : ""}</div>
        <span class="dedup-conflict-count">${escapeHtml(conflicts)}</span>
      </header>
      <div class="dedup-feature-evidence">${evidence}</div>
      <div class="dedup-feature-actions">
        <label><span>Duplicate handling</span>
        <select class="dedup-strategy" data-dedup-feature="${escapeHtml(fid)}"${disabledAttr}>${options}</select>
        </label>
        <button type="button" class="button compact secondary dedup-exclude" data-dedup-exclude="${escapeHtml(fid)}"${disabledAttr}>Exclude this feature table</button>
      </div>
    </article>`;
    })
    .join("");
  return `<div class="dedup-picker" data-dedup-form="${escapeHtml(messageId)}" data-dedup-plan-id="${escapeHtml(planId)}" data-dedup-gate-step-id="${escapeHtml(gateStepId)}"${snapshotAttrs}${interactive ? "" : ' data-dedup-readonly="true"'}>
    <p class="dedup-note">These tables have multiple rows per join key. Choose how to resolve duplicates before continuing.</p>
    <p class="dedup-strategy-note">${escapeHtml(DEDUP_STRATEGY_NOTE)}</p>
    <div class="dedup-feature-list">${cards}</div>
    <div class="dedup-foot gate-action-bar">
      <button type="button" class="button compact primary dedup-confirm"${interactive ? ` data-dedup-confirm="${escapeHtml(messageId)}"` : disabledAttr}>${interactive ? "Apply duplicate handling" : "Previous results"}</button>
    </div>
  </div>`;
}

export async function submitDedupStrategies(button, rawContext = {}) {
  const form = button.closest(".dedup-picker");
  const { taskId, api, acceptanceMode, setActionStatus, setAgentMessages, renderAgentConversation } = joinGateContext(rawContext);
  if (!form || !taskId || typeof api !== "function") return;
  if (form.dataset.dedupReadonly === "true") {
    setActionStatus("This is a previous result. Use the latest review step to confirm it.", "error");
    return;
  }
  const dedupStrategies = {};
  for (const select of form.querySelectorAll(".dedup-strategy")) {
    const featureId = select.getAttribute("data-dedup-feature");
    if (featureId) dedupStrategies[featureId] = select.value;
  }
  const expectedPlanId = form.dataset.dedupPlanId || "";
  const expectedStepId = form.dataset.dedupGateStepId || "";
  const confirmationSnapshot = confirmationSnapshotFromControl(
    form,
    { requireStep: true },
  );
  if (!expectedPlanId || !expectedStepId || !confirmationSnapshot) {
    setActionStatus("Refresh the task to load the current confirmation, then try again.", "error");
    return;
  }
  button.disabled = true;
  const context = joinGateContext(rawContext);
  try {
    await withDriverTurnBusyFeedback(taskId, context, async (pollAgentMessagesUntilSettled) => {
      const requestPromise = api(`/api/tasks/${taskId}/agent/messages`, {
        method: "POST",
        body: JSON.stringify({
          content: "Confirm.",
          ui_action: "confirm_dedup",
          dedup_strategies: dedupStrategies,
          expected_plan_id: expectedPlanId,
          expected_step_id: expectedStepId,
          ...confirmationSnapshot,
          acceptance_mode: acceptanceMode,
        }),
      });
      const streamPollPromise = pollAgentMessagesUntilSettled(taskId, requestPromise, { preserveOptimistic: true });
      const result = await requestPromise;
      await streamPollPromise;
      setAgentMessages(result.messages);
      renderAgentConversation();
    });
  } catch (error) {
    const conflictHandled = await refreshAfterConfirmationConflict(error, {
      taskId,
      refreshAgentMessages: context.refreshAgentMessages,
      setActionStatus,
    });
    if (!conflictHandled) {
      button.disabled = false;
      setActionStatus(error?.message || "Could not apply duplicate handling", "error");
    }
  }
}

export function handleDedupConfirmClick(event, context = {}) {
  const button = event.target?.closest?.("[data-dedup-confirm]");
  if (!button) return false;
  event.preventDefault();
  void submitDedupStrategies(button, context);
  return true;
}

// UX-6: "Exclude this feature table" is a typed, snapshot-bound structural adjustment. The
// server validates the feature id and atomically recomputes the join proposal;
// display copy is audit text only and is never reparsed as authority.
export async function submitDedupExclude(button, rawContext = {}) {
  const form = button.closest(".dedup-picker");
  const { taskId, api, acceptanceMode, setActionStatus, setAgentMessages, renderAgentConversation } = joinGateContext(rawContext);
  if (!form || !taskId || typeof api !== "function") return;
  if (form.dataset.dedupReadonly === "true") {
    setActionStatus("This is a previous result. Use the latest review step to confirm it.", "error");
    return;
  }
  const featureId = button.getAttribute("data-dedup-exclude") || "";
  if (!featureId) return;
  const expectedPlanId = form.dataset.dedupPlanId || "";
  const expectedStepId = form.dataset.dedupGateStepId || "";
  const confirmationSnapshot = confirmationSnapshotFromControl(
    form,
    { requireStep: true },
  );
  if (!expectedPlanId || !expectedStepId || !confirmationSnapshot) {
    setActionStatus("Refresh the task to load the current confirmation, then try again.", "error");
    return;
  }
  button.disabled = true;
  const context = joinGateContext(rawContext);
  try {
    await withDriverTurnBusyFeedback(taskId, context, async (pollAgentMessagesUntilSettled) => {
      const requestPromise = api(`/api/tasks/${taskId}/agent/messages`, {
        method: "POST",
        body: JSON.stringify({
          content: `Exclude feature table${featureId}; continue joining the remaining tables`,
          ui_action: "exclude_join_feature",
          adjust_params: { exclude_join_feature_id: featureId },
          expected_plan_id: expectedPlanId,
          expected_step_id: expectedStepId,
          ...confirmationSnapshot,
          acceptance_mode: acceptanceMode,
        }),
      });
      const streamPollPromise = pollAgentMessagesUntilSettled(taskId, requestPromise, { preserveOptimistic: true });
      const result = await requestPromise;
      await streamPollPromise;
      setAgentMessages(result.messages);
      renderAgentConversation();
    });
  } catch (error) {
    const conflictHandled = await refreshAfterConfirmationConflict(error, {
      taskId,
      refreshAgentMessages: context.refreshAgentMessages,
      setActionStatus,
    });
    if (!conflictHandled) {
      button.disabled = false;
      setActionStatus(error?.message || "Could not exclude the feature table", "error");
    }
  }
}

export function handleDedupExcludeClick(event, context = {}) {
  const button = event.target?.closest?.("[data-dedup-exclude]");
  if (!button) return false;
  event.preventDefault();
  void submitDedupExclude(button, context);
  return true;
}
