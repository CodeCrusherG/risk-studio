import { escapeHtml } from "./ui-utils.js";
import { schemaTableHtml } from "./v2/schema_table.js";

// The plugin-admin token replaces the old fixed "local-dev" magic header. The
// server embeds the per-workspace token into <body data-marvis-plugin-admin-
// token> for local clients only (see marvis/app.py index handler); promote /
// reject echo it back via X-MARVIS-Plugin-Admin. A remote client never receives
// it and is additionally blocked by the shared-host access guard.
function pluginAdminToken() {
  return typeof document !== "undefined"
    ? document.body?.dataset?.marvisPluginAdminToken || ""
    : "";
}

function draftStatusLabel(status) {
  return {
    draft: "Draft",
    tested: "Tested",
    promoted: "Approved",
    rejected: "Rejected",
  }[status] || status || "Unknown";
}

function draftSourceLabel(source) {
  return {
    web_learning: "Online learning",
    llm_generated: "Model generated",
    hand_written: "Manual",
  }[source] || source || "Unknown source";
}

export function createDraftToolsPanelController({
  $,
  api,
  runAction,
  showPlatformConfirm,
} = {}) {
  let draftTools = [];
  let selectedDraftToolId = "";
  let selectedDraftToolDetail = null;
  let loaded = false;

  function setStatus(message = "", kind = "") {
    const status = $("draftToolsStatus");
    if (!status) return;
    status.textContent = message;
    status.className = ["status", kind].filter(Boolean).join(" ");
  }

  function query() {
    const params = new URLSearchParams();
    const status = String($("draftStatusFilter")?.value || "").trim();
    if (status) params.set("status", status);
    return params.toString();
  }

  function renderList() {
    const list = $("draftToolsList");
    if (!list) return;
    if (!draftTools.length) {
      list.innerHTML = '<div class="draft-tool-empty">No draft tools found.</div>';
      return;
    }
    list.innerHTML = draftTools.map((draft) => {
      const draftId = String(draft.id || "");
      const selected = draftId === selectedDraftToolId;
      const meta = [
        draftSourceLabel(draft.source),
        draftStatusLabel(draft.status),
        draft.task_id ? `Task ${draft.task_id}` : "",
      ].filter(Boolean).join(" · ");
      return [
        `<article class="draft-tool-item${selected ? " selected" : ""}" data-draft-tool-id="${escapeHtml(draftId)}" role="button" tabindex="0">`,
        '<div class="draft-tool-item-main">',
        `<strong>${escapeHtml(draft.name || "Untitled draft")}</strong>`,
        `<span>${escapeHtml(meta)}</span>`,
        draft.summary ? `<p>${escapeHtml(draft.summary)}</p>` : "",
        "</div>",
        "</article>",
      ].join("");
    }).join("");
  }

  function renderLearningNote(note) {
    const target = $("draftLearningNote");
    if (!target) return;
    if (!note) {
      target.innerHTML = '<span>No source notes available.</span>';
      return;
    }
    const sources = (note.sources || []).map((source) => `<li>${escapeHtml(source)}</li>`).join("");
    target.innerHTML = [
      '<strong>Source notes</strong>',
      `<p>${escapeHtml(note.distilled || "")}</p>`,
      sources ? `<ul>${sources}</ul>` : "",
    ].join("");
  }

  function renderRunHistory(runs = []) {
    const target = $("draftRunHistory");
    if (!target) return;
    if (!runs.length) {
      target.innerHTML = '<div class="draft-tool-empty">No test runs recorded.</div>';
      return;
    }
    target.innerHTML = runs.map((run) => [
      '<div class="draft-run-item">',
      `<strong>${run.ok ? "Passed" : "Failed"}</strong>`,
      `<span>${escapeHtml(run.at || "")}</span>`,
      run.error ? `<code>${escapeHtml(run.error)}</code>` : "",
      "</div>",
    ].join("")).join("");
  }

  function renderDetail(payload = null) {
    selectedDraftToolDetail = payload;
    const draft = payload?.draft || null;
    const body = $("draftToolBody");
    const empty = $("draftToolEmpty");
    if (!body || !empty) return;
    if (!draft) {
      selectedDraftToolId = "";
      empty.classList.remove("hidden");
      body.classList.add("hidden");
      return;
    }
    selectedDraftToolId = String(draft.id || "");
    empty.classList.add("hidden");
    body.classList.remove("hidden");
    $("draftToolName").textContent = draft.name || "Untitled draft";
    $("draftToolSummary").textContent = draft.summary || "";
    $("draftToolStatus").textContent = draftStatusLabel(draft.status);
    $("draftToolStatus").dataset.status = draft.status || "";
    $("draftToolMeta").textContent = [
      draftSourceLabel(draft.source),
      draft.determinism,
      draft.task_id ? `Task ${draft.task_id}` : "",
      draft.created_at || "",
    ].filter(Boolean).join(" · ");
    $("draftToolCode").textContent = draft.code || "";
    $("draftInputSchema").innerHTML = schemaTableHtml(draft.input_schema || {}, "Input");
    $("draftOutputSchema").innerHTML = schemaTableHtml(draft.output_schema || {}, "Output");
    renderLearningNote(payload.learning_note || null);
    renderRunHistory(payload.runs || []);
    $("draftRunInputs").value = "{}";
    $("draftPromotionTestCases").value = '[\n  {"inputs": {}, "expect": {}}\n]';
    const terminal = ["promoted", "rejected"].includes(String(draft.status || ""));
    $("runDraftButton").disabled = !selectedDraftToolId;
    $("promoteDraftButton").disabled = terminal || !selectedDraftToolId;
    $("rejectDraftButton").disabled = terminal || !selectedDraftToolId;
    renderList();
  }

  function parseJsonField(fieldId, fallback) {
    const raw = String($(fieldId)?.value || "").trim();
    if (!raw) return fallback;
    try {
      return JSON.parse(raw);
    } catch (_) {
      throw new Error("Enter valid JSON.");
    }
  }

  async function load({ preserveSelection = false } = {}) {
    setStatus("Loading draft tools…");
    const filter = query();
    const payload = await api("/api/drafts" + (filter ? `?${filter}` : ""));
    loaded = true;
    draftTools = Array.isArray(payload?.drafts) ? payload.drafts : [];
    renderList();
    const selectedStillVisible = draftTools.some((draft) => String(draft.id || "") === selectedDraftToolId);
    if (preserveSelection && selectedStillVisible) {
      await inspect(selectedDraftToolId);
    } else {
      renderDetail(null);
    }
    setStatus(`Draft tools loaded: ${draftTools.length}.`, "success");
  }

  async function inspect(draftId) {
    if (!draftId) return;
    setStatus("Loading draft details…");
    const payload = await api(`/api/drafts/${encodeURIComponent(draftId)}`);
    renderDetail(payload);
    setStatus("Draft details loaded.", "success");
  }

  async function run() {
    const draftId = selectedDraftToolId;
    if (!draftId) return;
    const inputs = parseJsonField("draftRunInputs", {});
    setStatus("Running test…");
    const runPayload = await api(`/api/drafts/${encodeURIComponent(draftId)}/run`, {
      method: "POST",
      body: JSON.stringify({ inputs }),
    });
    await inspect(draftId);
    setStatus(
      runPayload.ok ? "Test passed." : `Test failed: ${runPayload.error || "No details available"}`,
      runPayload.ok ? "success" : "error"
    );
  }

  async function promote() {
    const draftId = selectedDraftToolId;
    if (!draftId) return;
    const testCases = parseJsonField("draftPromotionTestCases", []);
    if (!Array.isArray(testCases) || testCases.length === 0) {
      setStatus("Add at least one test case before approval.", "error");
      return;
    }
    const confirmed = await showPlatformConfirm({
      title: "Approve tool",
      message: "This adds the tool to the approved library for use in future tasks. Approve this tool?",
      confirmText: "Approve tool",
      cancelText: "Cancel",
      tone: "warning",
    });
    if (!confirmed) return;
    setStatus("Checking tests and approving tool…");
    const payload = await api(`/api/drafts/${encodeURIComponent(draftId)}/promote`, {
      method: "POST",
      headers: { "X-MARVIS-Plugin-Admin": pluginAdminToken() },
      body: JSON.stringify({ test_cases: testCases }),
    });
    await load({ preserveSelection: true });
    setStatus(`Approved: ${payload?.plugin?.name || "tool"}.`, "success");
  }

  async function reject() {
    const draftId = selectedDraftToolId;
    if (!draftId) return;
    const reason = window.prompt("Reason for rejection", "") || "";
    setStatus("Rejecting draft…");
    await api(`/api/drafts/${encodeURIComponent(draftId)}/reject`, {
      method: "POST",
      headers: { "X-MARVIS-Plugin-Admin": pluginAdminToken() },
      body: JSON.stringify({ reason }),
    });
    await load({ preserveSelection: true });
    setStatus("Draft rejected.", "success");
  }

  function inspectFromEvent(event) {
    const item = event.target?.closest?.("[data-draft-tool-id]");
    if (!item) return false;
    event.preventDefault();
    runAction(() => inspect(item.dataset.draftToolId), {
      actionId: "draftTools",
      busyText: "Loading draft details…",
    });
    return true;
  }

  function handleListClick(event) {
    inspectFromEvent(event);
  }

  function handleListKeydown(event) {
    if (event.key !== "Enter" && event.key !== " ") return;
    inspectFromEvent(event);
  }

  return {
    detail: () => selectedDraftToolDetail,
    handleListClick,
    handleListKeydown,
    hasLoaded: () => loaded,
    hasItems: () => draftTools.length > 0,
    inspect,
    load,
    promote,
    reject,
    renderDetail,
    renderList,
    run,
    setStatus,
  };
}
