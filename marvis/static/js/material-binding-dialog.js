const MATERIAL_BINDING_ROLES = [
  { role: "notebook", field: "notebook_path", label: "Notebook", caption: "Notebook" },
  { role: "sample", field: "sample_path", label: "Sample", caption: "Sample data" },
  { role: "model_pmml", field: "pmml_path", label: "PMML", caption: "PMML model" },
  { role: "data_dictionary", field: "dictionary_path", label: "Metadata", caption: "Data dictionary / feature metadata" },
];

const MATERIAL_BINDING_ROLE_ICONS = {
  notebook: '<path d="M6 4.5h9.8A2.2 2.2 0 0 1 18 6.7v12.8H7.4A2.4 2.4 0 0 1 5 17.1V5.5a1 1 0 0 1 1-1Z"></path><path d="M9 8h5.5M9 11h4"></path><path d="M7.4 19.5A2.4 2.4 0 0 1 5 17.1"></path>',
  sample: '<ellipse cx="12" cy="6.5" rx="6.5" ry="2.7"></ellipse><path d="M5.5 6.5v10.8c0 1.5 2.9 2.7 6.5 2.7s6.5-1.2 6.5-2.7V6.5"></path><path d="M5.5 12c0 1.5 2.9 2.7 6.5 2.7s6.5-1.2 6.5-2.7"></path>',
  model_pmml: '<path d="M12 3.5 19 7.5v8.8l-7 4-7-4V7.5Z"></path><path d="M5.3 7.7 12 11.5l6.7-3.8"></path><path d="M12 11.6v8.1"></path>',
  data_dictionary: '<path d="M5.5 4.5h9.2A3.8 3.8 0 0 1 18.5 8.3v11.2H7.7a2.2 2.2 0 0 1-2.2-2.2Z"></path><path d="M8.5 8.5h6M8.5 12h5M8.5 15.5h3.5"></path>',
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatBytes(value) {
  const size = Number(value || 0);
  if (!Number.isFinite(size) || size <= 0) return "";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export function materialCandidateSelectable(role, candidate) {
  if (candidate?.available === false) return false;
  if (role?.role !== "data_dictionary") return true;
  return candidate?.metadata_compatibility?.status !== "incompatible";
}

function candidateText(candidate) {
  const size = formatBytes(candidate?.size_bytes);
  const metadataStatus = candidate?.metadata_compatibility?.status;
  const compatibility = candidate?.recommended
    ? " · Recommended: matches PMML features"
    : metadataStatus === "compatible"
      ? " · Matches PMML features"
      : metadataStatus === "incompatible"
        ? " · Incomplete metadata"
        : metadataStatus === "not_evaluated"
          ? " · Manual confirmation required"
          : "";
  const unavailable = metadataStatus === "incompatible" || candidate?.available === false
    ? " · Unoptional"
    : "";
  return `${candidate?.relative_path || candidate?.name || "Unnamed file"}${size ? ` · ${size}` : ""}${compatibility}${unavailable}`;
}

function defaultSelectionForRole(role, candidates, selection) {
  const selected = String(selection?.[role.field] || "");
  const selectableCandidates = candidates.filter((candidate) => (
    materialCandidateSelectable(role, candidate)
  ));
  const selectedCandidate = selectableCandidates.find((candidate) => (
    String(candidate?.relative_path || "") === selected
  ));
  if (selected && selectedCandidate) return selected;
  const recommendedCandidates = selectableCandidates.filter((candidate) => candidate.recommended);
  if (recommendedCandidates.length === 1) return recommendedCandidates[0].relative_path || "";
  const hasMetadataAssessment = candidates.some((candidate) => candidate.metadata_compatibility);
  if (role.role === "data_dictionary" && (hasMetadataAssessment || candidates.length > 1)) return "";
  const exactRoleCandidates = selectableCandidates.filter((candidate) => candidate.role === role.role);
  if (exactRoleCandidates.length === 1) return exactRoleCandidates[0].relative_path || "";
  if (selectableCandidates.length === 1) return selectableCandidates[0].relative_path || "";
  return "";
}

function completeSelection(selection = {}) {
  return MATERIAL_BINDING_ROLES.every((role) => String(selection[role.field] || "").trim());
}

export function materialSelectionIssue(selection = {}, payload = {}) {
  const role = MATERIAL_BINDING_ROLES.find((item) => item.role === "data_dictionary");
  const candidates = Array.isArray(payload?.candidates?.data_dictionary)
    ? payload.candidates.data_dictionary
    : [];
  const selected = String(selection?.dictionary_path || "");
  const selectedCandidate = candidates.find((candidate) => (
    String(candidate?.relative_path || "") === selected
  ));
  const guidance = "Choose another PMML file or add the feature, category and importance columns, then scan again.";
  if (selectedCandidate && !materialCandidateSelectable(role, selectedCandidate)) {
    return `Feature metadata are unavailable. ${guidance}`;
  }
  if (candidates.length && !candidates.some((candidate) => materialCandidateSelectable(role, candidate))) {
    return `No feature metadata match the selected PMML file. ${guidance}`;
  }
  return "";
}

export function renderRoleRow(role, candidates, value) {
  const selectableCandidates = candidates.filter((candidate) => (
    materialCandidateSelectable(role, candidate)
  ));
  const disabled = selectableCandidates.length === 0 ? " disabled" : "";
  const icon = MATERIAL_BINDING_ROLE_ICONS[role.role] || "";
  const options = candidates.length
    ? [
        '<option value="">Choose</option>',
        ...candidates.map((candidate) => {
          const relativePath = candidate.relative_path || "";
          const selectable = materialCandidateSelectable(role, candidate);
          const selected = selectable && relativePath === value ? " selected" : "";
          const unavailable = selectable ? "" : ' disabled aria-disabled="true"';
          return `<option value="${escapeHtml(relativePath)}"${selected}${unavailable}>${escapeHtml(candidateText(candidate))}</option>`;
        }),
      ].join("")
    : '<option value="">No matching files found</option>';
  const unavailableHint = candidates.length && !selectableCandidates.length
    ? '<small class="material-binding-unavailable">No feature metadata match the selected PMML file. Choose another model or complete the metadata columns, then scan again.</small>'
    : "";
  return [
    '<label class="material-binding-row">',
    '<span class="material-binding-role">',
    `<span class="material-binding-role-icon" aria-hidden="true"><svg viewBox="0 0 24 24" focusable="false">${icon}</svg></span>`,
    '<span class="material-binding-role-text">',
    `<strong>${escapeHtml(role.label)}</strong>`,
    `<small>${escapeHtml(role.caption)}</small>`,
    "</span>",
    "</span>",
    `<select data-material-binding-field="${escapeHtml(role.field)}" aria-label="Selection${escapeHtml(role.caption)}"${disabled}>${options}</select>`,
    unavailableHint,
    "</label>",
  ].join("");
}

export function createMaterialBindingDialogController({ $, api } = {}) {
  let pendingResolve = null;
  let activeTask = null;
  let activePayload = null;
  let previewRequestSequence = 0;

  function setStatus(message, kind = "info") {
    const status = $("materialBindingStatus");
    if (!status) return;
    status.textContent = message;
    status.className = `status ${kind}`;
  }

  function render(payload) {
    const rows = $("materialBindingRows");
    if (!rows) return;
    activePayload = payload || {};
    const selection = payload?.selection || {};
    rows.innerHTML = MATERIAL_BINDING_ROLES.map((role) => {
      const candidates = Array.isArray(payload?.candidates?.[role.role])
        ? payload.candidates[role.role]
        : [];
      const selected = defaultSelectionForRole(role, candidates, selection);
      return renderRoleRow(role, candidates, selected);
    }).join("");
  }

  function collectSelection() {
    const selection = {};
    document.querySelectorAll("[data-material-binding-field]").forEach((select) => {
      selection[select.dataset.materialBindingField] = select.value;
    });
    return selection;
  }

  async function refreshMetadataRecommendation(pmmlPath) {
    if (!activeTask?.id) return;
    const requestSequence = ++previewRequestSequence;
    const dictionarySelect = document.querySelector(
      '[data-material-binding-field="dictionary_path"]',
    );
    if (dictionarySelect) dictionarySelect.value = "";
    const confirmButton = $("materialBindingConfirmButton");
    if (confirmButton) confirmButton.disabled = true;
    setStatus("Checking the PMML model against feature metadata…", "busy");
    try {
      const payload = await api(
        `/api/tasks/${activeTask.id}/materials?pmml_path=${encodeURIComponent(pmmlPath)}`,
      );
      if (requestSequence !== previewRequestSequence) return;
      const currentSelection = collectSelection();
      render({
        ...payload,
        selection: {
          ...(payload.selection || {}),
          ...currentSelection,
          pmml_path: pmmlPath,
        },
      });
      setStatus(
        payload.recommendation
          ? "Matching feature metadata are selected. Review and confirm the files."
          : "Metadata checks have been updated for the selected PMML model. Review the results.",
        "info",
      );
    } catch (error) {
      if (requestSequence !== previewRequestSequence) return;
      setStatus(error?.message || "Could not check feature metadata", "error");
    } finally {
      if (requestSequence === previewRequestSequence && confirmButton) {
        confirmButton.disabled = false;
      }
    }
  }

  function resolvePending(value) {
    if (!pendingResolve) return;
    const resolve = pendingResolve;
    pendingResolve = null;
    resolve(value);
  }

  function closeWith(value) {
    previewRequestSequence += 1;
    activeTask = null;
    activePayload = null;
    resolvePending(value);
    const dialog = $("materialBindingDialog");
    if (dialog?.open) dialog.close(value ? "confirm" : "cancel");
  }

  async function confirmSelection() {
    if (!activeTask?.id) return;
    const selection = collectSelection();
    const issue = materialSelectionIssue(selection, activePayload || {});
    if (issue) {
      setStatus(issue, "error");
      return;
    }
    if (!completeSelection(selection)) {
      setStatus("Select a file for each of the four input categories.", "error");
      return;
    }
    setStatus("Saving file selections…", "busy");
    try {
      const result = await api(`/api/tasks/${activeTask.id}/materials`, {
        method: "PUT",
        body: JSON.stringify(selection),
      });
      setStatus("File selections saved.", "success");
      closeWith(result.task || activeTask);
    } catch (error) {
      setStatus(error?.message || "Could not save file selections.", "error");
    }
  }

  async function ensureMaterialSelection(task, { force = false } = {}) {
    if (!task || (task.task_type || "validation") !== "validation") return task;
    const payload = await api(`/api/tasks/${task.id}/materials`);
    const selectionIssue = materialSelectionIssue(payload.selection || {}, payload);
    if (!force && completeSelection(payload.selection) && !selectionIssue) return task;
    previewRequestSequence += 1;
    activeTask = task;
    render(payload);
    const confirmButton = $("materialBindingConfirmButton");
    if (confirmButton) confirmButton.disabled = false;
    setStatus(selectionIssue, selectionIssue ? "error" : "info");
    const dialog = $("materialBindingDialog");
    if (!dialog) return task;
    dialog.showModal();
    return await new Promise((resolve) => {
      pendingResolve = resolve;
    });
  }

  function bind() {
    $("materialBindingRows")?.addEventListener("change", (event) => {
      const field = event.target?.dataset?.materialBindingField;
      if (field === "pmml_path") {
        refreshMetadataRecommendation(event.target.value || "");
      }
    });
    $("materialBindingConfirmButton")?.addEventListener("click", confirmSelection);
    $("materialBindingCancelButton")?.addEventListener("click", () => closeWith(null));
    $("closeMaterialBindingDialogButton")?.addEventListener("click", () => closeWith(null));
    $("materialBindingDialog")?.addEventListener("cancel", (event) => {
      event.preventDefault();
      closeWith(null);
    });
    $("materialBindingDialog")?.addEventListener("close", () => {
      resolvePending(null);
    });
  }

  return {
    bind,
    ensureMaterialSelection,
  };
}
