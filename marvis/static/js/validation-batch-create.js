export const MIN_VALIDATION_BATCH_ROWS = 2;
export const MAX_VALIDATION_BATCH_ROWS = 10;

const FILE_ROLE_ORDER = ["notebook", "sample", "pmml", "dictionary"];

export const VALIDATION_BATCH_FILE_RULES = {
  notebook: {
    label: "Notebook",
    accept: ".ipynb",
    extensions: [".ipynb"],
    hint: "Jupyter notebook (.ipynb)",
  },
  sample: {
    label: "Validation sample",
    accept: ".csv,.parquet,.feather,.xlsx,.xls",
    extensions: [".csv", ".parquet", ".feather", ".xlsx", ".xls"],
    hint: "CSV, Parquet, Feather or Excel",
  },
  pmml: {
    label: "PMML Model",
    accept: ".pmml",
    extensions: [".pmml"],
    hint: "PMML Model File (.pmml)",
  },
  dictionary: {
    label: "Data dictionary",
    accept: ".csv,.parquet,.xlsx,.xls",
    extensions: [".csv", ".parquet", ".xlsx", ".xls"],
    hint: "CSV, Parquet or Excel",
  },
};

function normalizedText(value) {
  return String(value || "").trim();
}

function fileExtension(file) {
  const name = normalizedText(file?.name).toLowerCase();
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot) : "";
}

const DICTIONARY_NAME_PATTERN = /Dictionary|dict|dictionary|metadata|meta|feature/i;
const SAMPLE_NAME_PATTERN = /Sample|sample|train|oot|data/i;

export function classifyValidationBatchFiles(files = []) {
  const list = Array.from(files || []).filter(Boolean);
  const assigned = {
    notebook: null,
    sample: null,
    pmml: null,
    dictionary: null,
  };
  const isAssigned = (file) => Object.values(assigned).includes(file);
  const take = (role, predicate) => {
    if (assigned[role]) return;
    const match = list.find((file) => !isAssigned(file) && predicate(file));
    if (match) assigned[role] = match;
  };

  take("notebook", (file) => fileExtension(file) === ".ipynb");
  take("pmml", (file) => fileExtension(file) === ".pmml");
  take("dictionary", (file) => {
    const ext = fileExtension(file);
    return VALIDATION_BATCH_FILE_RULES.dictionary.extensions.includes(ext)
      && DICTIONARY_NAME_PATTERN.test(normalizedText(file.name));
  });
  take("sample", (file) => {
    const ext = fileExtension(file);
    return VALIDATION_BATCH_FILE_RULES.sample.extensions.includes(ext)
      && SAMPLE_NAME_PATTERN.test(normalizedText(file.name));
  });
  take("sample", (file) => (
    VALIDATION_BATCH_FILE_RULES.sample.extensions.includes(fileExtension(file))
  ));
  take("dictionary", (file) => (
    VALIDATION_BATCH_FILE_RULES.dictionary.extensions.includes(fileExtension(file))
  ));
  if (!assigned.notebook || !assigned.sample || !assigned.pmml || !assigned.dictionary) {
    return null;
  }
  if (assigned.sample === assigned.dictionary) return null;
  return assigned;
}

function errorMessage(error, fallback = "Request failed") {
  const message = normalizedText(error?.message || error?.detail || error);
  return message || fallback;
}

function safeUploadFilename(file, role) {
  const rawName = normalizedText(file?.name) || `${role}.bin`;
  const basename = rawName.split(/[\\/]/).pop() || `${role}.bin`;
  const safeName = basename.replace(/[\u0000-\u001f\u007f]/g, "_").replace(/^\.+$/, "file");
  return safeName || `${role}.bin`;
}

function validationRowKey(row, index) {
  return normalizedText(row?.id) || `row-${index + 1}`;
}

export function validationBatchRelativePaths(files = {}) {
  return Object.fromEntries(
    FILE_ROLE_ORDER.map((role) => [
      role,
      `${role}/${safeUploadFilename(files[role], role)}`,
    ]),
  );
}

export function validateValidationBatchDraft(draft = {}) {
  const formErrors = [];
  const rowErrors = {};
  const rows = Array.isArray(draft.rows) ? draft.rows : [];

  if (!normalizedText(draft.batchName)) formErrors.push("Enter the batch name.");
  if (!normalizedText(draft.validator)) formErrors.push("Enter the reviewer name.");
  if (rows.length < MIN_VALIDATION_BATCH_ROWS || rows.length > MAX_VALIDATION_BATCH_ROWS) {
    formErrors.push("Each batch must contain 2 to 10 models.");
  }

  rows.forEach((row, index) => {
    const errors = [];
    const rowKey = validationRowKey(row, index);
    if (!normalizedText(row?.modelName)) errors.push("Enter the model name.");
    if (normalizedText(row?.sourceDir)) {
      if (errors.length) rowErrors[rowKey] = errors;
      return;
    }
    FILE_ROLE_ORDER.forEach((role) => {
      const rule = VALIDATION_BATCH_FILE_RULES[role];
      const file = row?.files?.[role];
      if (!file) {
        errors.push(`Upload the ${rule.label.toLowerCase()}.`);
        return;
      }
      if (!rule.extensions.includes(fileExtension(file))) {
        errors.push(`${rule.label} supports ${rule.extensions.join(", ")}.`);
      }
      if (Number(file.size) === 0) errors.push(`${rule.label} is empty. Select a file containing data.`);
    });
    if (errors.length) rowErrors[rowKey] = errors;
  });

  return {
    valid: formErrors.length === 0 && Object.keys(rowErrors).length === 0,
    formErrors,
    rowErrors,
  };
}

export function buildValidationBatchUploadFormData(row) {
  const formData = new FormData();
  const relativePaths = validationBatchRelativePaths(row?.files);
  FILE_ROLE_ORDER.forEach((role) => {
    const file = row.files[role];
    formData.append("files", file, file.name);
    formData.append("relative_paths", relativePaths[role]);
  });
  return formData;
}

function uploadFingerprint(row) {
  return FILE_ROLE_ORDER.map((role) => {
    const file = row?.files?.[role];
    return [role, file?.name || "", file?.size ?? "", file?.lastModified ?? ""].join(":");
  }).join("|");
}

function batchItemFromUpload(row, upload, relativePaths) {
  const sourceDir = normalizedText(upload?.source_dir);
  if (!sourceDir) throw new Error("The upload response did not include a files folder. No batch was created.");
  const uploadToken = normalizedText(upload?.upload_token);
  if (!uploadToken) throw new Error("The upload response did not include an upload token. No batch was created.");
  return {
    model_name: normalizedText(row.modelName),
    model_version: normalizedText(row.modelVersion),
    source_dir: sourceDir,
    upload_token: uploadToken,
    notebook_path: relativePaths.notebook,
    sample_path: relativePaths.sample,
    pmml_path: relativePaths.pmml,
    dictionary_path: relativePaths.dictionary,
  };
}

export async function submitValidationBatchDraft(
  draft,
  {
    uploadMaterials,
    createBatch,
    cleanupMaterials,
    onRowStatus = () => {},
  } = {},
) {
  const validation = validateValidationBatchDraft(draft);
  if (!validation.valid) {
    const error = new Error("Check the required fields and file types.");
    error.name = "ValidationBatchDraftError";
    error.validation = validation;
    throw error;
  }
  if (typeof uploadMaterials !== "function" || typeof createBatch !== "function") {
    throw new Error("The batch creation service is unavailable.");
  }

  const items = [];
  const acquiredUploads = [];
  try {
    for (let index = 0; index < draft.rows.length; index += 1) {
      const row = draft.rows[index];
      const rowId = validationRowKey(row, index);
      if (normalizedText(row.sourceDir) && !row.files?.notebook) {
        onRowStatus(rowId, "uploaded", "Files folder selected. Ready to create the batch.");
        items.push({
          model_name: normalizedText(row.modelName),
          model_version: normalizedText(row.modelVersion) || "v1",
          source_dir: normalizedText(row.sourceDir),
          notebook_path: "",
          sample_path: "",
          pmml_path: "",
          dictionary_path: "",
        });
        continue;
      }
      const relativePaths = validationBatchRelativePaths(row.files);
      const fingerprint = uploadFingerprint(row);
      let upload = row.uploadCache?.fingerprint === fingerprint
        ? row.uploadCache.payload
        : null;

      if (!upload) {
        onRowStatus(
          rowId,
          "uploading",
          `Uploading files for model ${index + 1} of ${draft.rows.length}…`,
        );
        try {
          upload = await uploadMaterials({
            row,
            index,
            total: draft.rows.length,
            relativePaths,
          });
          if (!normalizedText(upload?.source_dir)) {
            throw new Error("The upload response did not include a files folder.");
          }
          if (!normalizedText(upload?.upload_token)) {
            throw new Error("The upload response did not include an upload token.");
          }
          row.uploadCache = { fingerprint, payload: upload };
        } catch (error) {
          onRowStatus(rowId, "error", `File upload failed: ${errorMessage(error)}`);
          throw error;
        }
      }
      acquiredUploads.push(upload);
      onRowStatus(rowId, "uploaded", "Four files uploaded. Ready to create the batch.");
      items.push(batchItemFromUpload(row, upload, relativePaths));
    }

    const result = await createBatch({
      batch_name: normalizedText(draft.batchName),
      validator: normalizedText(draft.validator),
      run_mode: "agent",
      items,
    });
    draft.rows.forEach((row) => { row.uploadCache = null; });
    return result;
  } catch (error) {
    const tokens = [...new Set(
      acquiredUploads
        .map((upload) => normalizedText(upload?.upload_token))
        .filter(Boolean),
    )];
    if (typeof cleanupMaterials === "function") {
      await Promise.allSettled(tokens.map((token) => cleanupMaterials(token)));
    }
    draft.rows.forEach((row) => { row.uploadCache = null; });
    throw error;
  }
}

function fileInputMarkup(role) {
  const rule = VALIDATION_BATCH_FILE_RULES[role];
  return `
    <label class="validation-batch-file-field">
      <span>${rule.label}<em>Required</em></span>
      <input type="file" required accept="${rule.accept}" data-batch-file-role="${role}" />
      <small>${rule.hint}</small>
    </label>
  `;
}

function rowMarkup(rowId) {
  return `
    <header class="validation-batch-create-row-head">
      <div>
        <span class="validation-batch-create-row-index">Model</span>
        <strong>Validation files</strong>
      </div>
      <button class="button compact secondary validation-batch-remove-row" type="button" data-remove-validation-batch-row="${rowId}">Remove</button>
    </header>
    <div class="validation-batch-model-fields">
      <label>
        <span>Model Name<em>Required</em></span>
        <input type="text" autocomplete="off" required data-batch-model-field="name" placeholder="Application scorecard" />
      </label>
      <label>
        <span>Model Version</span>
        <input type="text" autocomplete="off" data-batch-model-field="version" placeholder="Model version or release tag" />
      </label>
    </div>
    <fieldset class="validation-batch-file-grid">
      <legend>Upload a separate set of four files for this model.</legend>
      ${fileInputMarkup("notebook")}
      ${fileInputMarkup("sample")}
      ${fileInputMarkup("pmml")}
      ${fileInputMarkup("dictionary")}
    </fieldset>
    <p class="validation-batch-row-status" data-validation-batch-row-status role="status" aria-live="polite"></p>
  `;
}

export function createValidationBatchCreateController({
  api,
  getElementById = (id) => document.getElementById(id),
  onCreated = async () => {},
} = {}) {
  const $ = getElementById;
  let rowSequence = 0;
  let rows = [];
  let busy = false;
  let createdPayload = null;

  function dialog() {
    return $("validationBatchCreateDialog");
  }

  function setStatus(message, kind = "info") {
    const status = $("validationBatchCreateStatus");
    if (!status) return;
    status.textContent = message || "";
    status.className = `status ${kind}`;
  }

  function rowElement(rowId) {
    const container = $("validationBatchRows");
    if (!container) return null;
    return [...container.querySelectorAll("[data-validation-batch-row-id]")]
      .find((candidate) => candidate.dataset.validationBatchRowId === rowId) || null;
  }

  function setRowStatus(rowId, state, message) {
    const status = rowElement(rowId)?.querySelector("[data-validation-batch-row-status]");
    if (!status) return;
    status.textContent = message || "";
    status.dataset.state = state || "idle";
  }

  function updateRowControls() {
    const count = rows.length;
    $("validationBatchRowCount").textContent = `${count} / ${MAX_VALIDATION_BATCH_ROWS}`;
    $("addValidationBatchRowButton").disabled = busy || count >= MAX_VALIDATION_BATCH_ROWS;
    $("validationBatchRows").querySelectorAll("[data-validation-batch-row-id]").forEach((element, index) => {
      element.querySelector(".validation-batch-create-row-index").textContent = `Model ${index + 1}`;
      element.querySelector("[data-remove-validation-batch-row]").disabled = busy || count <= MIN_VALIDATION_BATCH_ROWS;
    });
  }

  function addRow() {
    if (busy || rows.length >= MAX_VALIDATION_BATCH_ROWS) return null;
    rowSequence += 1;
    const state = { id: `validation-batch-row-${rowSequence}`, uploadCache: null };
    rows.push(state);
    const element = document.createElement("article");
    element.className = "validation-batch-create-row";
    element.dataset.validationBatchRowId = state.id;
    element.innerHTML = rowMarkup(state.id);
    $("validationBatchRows").append(element);
    updateRowControls();
    return state;
  }

  function removeRow(rowId) {
    if (busy || rows.length <= MIN_VALIDATION_BATCH_ROWS) return false;
    const index = rows.findIndex((row) => row.id === rowId);
    if (index < 0) return false;
    rows.splice(index, 1);
    rowElement(rowId)?.remove();
    updateRowControls();
    return true;
  }

  function clearRowMessages() {
    rows.forEach((row) => setRowStatus(row.id, "idle", ""));
  }

  function collectDraft() {
    rows.forEach((row) => {
      const element = rowElement(row.id);
      row.modelName = element?.querySelector('[data-batch-model-field="name"]')?.value || "";
      row.modelVersion = element?.querySelector('[data-batch-model-field="version"]')?.value || "";
      row.files = Object.fromEntries(
        FILE_ROLE_ORDER.map((role) => [
          role,
          element?.querySelector(`[data-batch-file-role="${role}"]`)?.files?.[0] || null,
        ]),
      );
    });
    return {
      batchName: $("validationBatchName").value,
      validator: $("validationBatchValidator").value,
      rows,
    };
  }

  function showValidation(validation) {
    clearRowMessages();
    Object.entries(validation.rowErrors).forEach(([rowId, errors]) => {
      setRowStatus(rowId, "error", errors.join(" "));
    });
    setStatus(validation.formErrors.join(" ") || "Check the highlighted files.", "error");
  }

  function setBusy(nextBusy) {
    busy = Boolean(nextBusy);
    dialog()?.querySelectorAll("input, button").forEach((control) => {
      control.disabled = busy;
    });
    updateRowControls();
  }

  async function uploadMaterials({ row, relativePaths }) {
    const formData = new FormData();
    FILE_ROLE_ORDER.forEach((role) => {
      const file = row.files[role];
      formData.append("files", file, file.name);
      formData.append("relative_paths", relativePaths[role]);
    });
    return api("/api/validation-batches/material-uploads", {
      method: "POST",
      body: formData,
    });
  }

  async function cleanupMaterials(uploadToken) {
    const token = normalizedText(uploadToken);
    if (!token) return;
    await api(`/api/validation-batches/material-uploads/${encodeURIComponent(token)}`, {
      method: "DELETE",
    });
  }

  async function createBatch(payload) {
    return api("/api/validation-batches", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async function openCreatedParent() {
    await onCreated(createdPayload);
    setBusy(false);
    close();
    return createdPayload;
  }

  async function submit() {
    if (busy) return null;
    if (createdPayload) {
      setBusy(true);
      setStatus("Batch created. Opening the task…", "info");
      try {
        return await openCreatedParent();
      } catch (error) {
        setBusy(false);
        setStatus(`Batch created, but the task list could not be refreshed: ${errorMessage(error)}`, "warning");
        return null;
      }
    }

    const draft = collectDraft();
    const validation = validateValidationBatchDraft(draft);
    if (!validation.valid) {
      showValidation(validation);
      return null;
    }

    clearRowMessages();
    setBusy(true);
    setStatus(`Preparing files for ${draft.rows.length} models…`, "info");
    try {
      createdPayload = await submitValidationBatchDraft(draft, {
        uploadMaterials,
        createBatch,
        cleanupMaterials,
        onRowStatus: (rowId, state, message) => {
          setRowStatus(rowId, state, message);
          if (state === "uploading") setStatus(message, "info");
        },
      });
      setStatus("Batch created. Opening the task…", "success");
      return await openCreatedParent();
    } catch (error) {
      setBusy(false);
      if (createdPayload) {
        setStatus(`Batch created, but the task list could not be refreshed: ${errorMessage(error)}`, "warning");
      } else if (error?.validation) {
        showValidation(error.validation);
      } else {
        setStatus(`Batch creation failed: ${errorMessage(error)}`, "error");
      }
      return null;
    }
  }

  function reset() {
    if (busy) return false;
    rowSequence = 0;
    rows = [];
    createdPayload = null;
    $("validationBatchCreateForm")?.reset();
    $("validationBatchRows").replaceChildren();
    setStatus("");
    addRow();
    addRow();
    return true;
  }

  function open() {
    if (dialog()?.open) return;
    reset();
    dialog()?.showModal();
    $("validationBatchName")?.focus();
  }

  function close() {
    if (busy) return false;
    if (dialog()?.open) dialog().close();
    return true;
  }

  function bind() {
    dialog()?.addEventListener("click", (event) => {
      if (busy && event.target === dialog()) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    });
    $("validationBatchCreateForm")?.addEventListener("submit", (event) => {
      event.preventDefault();
      void submit();
    });
    $("addValidationBatchRowButton")?.addEventListener("click", addRow);
    $("closeValidationBatchCreateButton")?.addEventListener("click", close);
    $("cancelValidationBatchCreateButton")?.addEventListener("click", close);
    $("validationBatchRows")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-remove-validation-batch-row]");
      if (button) removeRow(button.dataset.removeValidationBatchRow);
    });
    $("validationBatchRows")?.addEventListener("change", (event) => {
      const input = event.target.closest("[data-batch-file-role]");
      if (!input) return;
      const element = input.closest("[data-validation-batch-row-id]");
      const row = rows.find((candidate) => candidate.id === element?.dataset.validationBatchRowId);
      if (row) row.uploadCache = null;
      setRowStatus(row?.id, "idle", input.files?.[0] ? `Selected:${input.files[0].name}` : "");
    });
    dialog()?.addEventListener("cancel", (event) => {
      if (busy) event.preventDefault();
    });
  }

  return {
    addRow,
    bind,
    close,
    open,
    removeRow,
    submit,
  };
}
