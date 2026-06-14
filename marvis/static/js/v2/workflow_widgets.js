import { escapeHtml } from "../ui-utils.js";

const MOUNTED = new WeakSet();

export function renderWorkflowDataWidget({
  title = "Data results",
  chartHtml = "",
  tableHtml = "",
  rowCount = 0,
  columnCount = 0,
  index = 0,
} = {}) {
  const filter = Number(rowCount) > 4
    ? `<label class="workflow-widget-search">
        <span class="sr-only">Filter ${escapeHtml(String(title))}</span>
        <input type="search" data-workflow-widget-filter placeholder="Filter rows…" autocomplete="off">
      </label>`
    : "";
  return `<section class="workflow-data-widget" data-workflow-widget data-widget-index="${Number(index) || 0}" style="--widget-order:${Number(index) || 0}">
    <header class="workflow-widget-head">
      <span class="workflow-widget-glyph" aria-hidden="true">${workflowWidgetGlyph(title)}</span>
      <span class="workflow-widget-title">
        <strong>${escapeHtml(String(title))}</strong>
        <small>${Number(rowCount) || 0} rows · ${Number(columnCount) || 0} columns</small>
      </span>
      <span class="workflow-widget-tools">
        ${filter}
        <button type="button" class="workflow-widget-toggle" data-workflow-widget-toggle data-gate-passive-control aria-expanded="true" aria-label="Collapse ${escapeHtml(String(title))}">
          <span aria-hidden="true">⌃</span>
        </button>
      </span>
    </header>
    <div class="workflow-widget-body">
      ${chartHtml}
      <div class="agent-inline-table-scroll workflow-widget-scroll">${tableHtml}</div>
      <div class="workflow-widget-empty" hidden>No matching rows</div>
    </div>
  </section>`;
}

export function mountWorkflowWidgetInteractions(root = document) {
  if (!root || MOUNTED.has(root) || typeof root.addEventListener !== "function") return;
  MOUNTED.add(root);
  root.addEventListener("click", handleWorkflowWidgetClick);
  root.addEventListener("input", handleWorkflowWidgetInput);
  root.addEventListener("pointerover", handleWorkflowWidgetPointerOver);
  root.addEventListener("pointerout", handleWorkflowWidgetPointerOut);
  root.addEventListener("pointermove", handleWorkflowWidgetPointerMove);
}

export function handleWorkflowWidgetClick(event) {
  const toggle = event.target?.closest?.("[data-workflow-widget-toggle]");
  if (!toggle) return;
  const widget = toggle.closest("[data-workflow-widget]");
  if (!widget) return;
  const collapsed = widget.classList.toggle("is-collapsed");
  toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
  const label = widget.querySelector(".workflow-widget-title strong")?.textContent || "Data table";
  toggle.setAttribute("aria-label", `${collapsed ? "Expand " : "Collapse "}${label}`);
}

export function handleWorkflowWidgetInput(event) {
  const input = event.target?.closest?.("[data-workflow-widget-filter]");
  if (!input) return;
  const widget = input.closest("[data-workflow-widget]");
  if (!widget) return;
  const query = String(input.value || "").trim().toLocaleLowerCase();
  const rows = [...widget.querySelectorAll("tbody tr")];
  let visible = 0;
  rows.forEach((row) => {
    const matched = !query || String(row.textContent || "").toLocaleLowerCase().includes(query);
    row.hidden = !matched;
    if (matched) visible += 1;
  });
  const empty = widget.querySelector(".workflow-widget-empty");
  if (empty) empty.hidden = visible > 0;
}

export function handleWorkflowWidgetPointerOver(event) {
  const cell = event.target?.closest?.(".workflow-data-widget :is(th, td)");
  if (!cell) return;
  const row = cell.parentElement;
  const table = cell.closest("table");
  if (!table || !row) return;
  const column = [...row.children].indexOf(cell);
  table.querySelectorAll(".is-column-hover").forEach((item) => item.classList.remove("is-column-hover"));
  if (column >= 0) {
    table.querySelectorAll(`tr > :nth-child(${column + 1})`).forEach((item) => item.classList.add("is-column-hover"));
  }
}

export function handleWorkflowWidgetPointerOut(event) {
  const widget = event.target?.closest?.("[data-workflow-widget]");
  if (!widget || widget.contains(event.relatedTarget)) return;
  widget.querySelectorAll(".is-column-hover").forEach((item) => item.classList.remove("is-column-hover"));
}

export function handleWorkflowWidgetPointerMove(event) {
  const widget = event.target?.closest?.("[data-workflow-widget]");
  if (!widget || typeof widget.getBoundingClientRect !== "function") return;
  const rect = widget.getBoundingClientRect();
  widget.style.setProperty("--spotlight-x", `${event.clientX - rect.left}px`);
  widget.style.setProperty("--spotlight-y", `${event.clientY - rect.top}px`);
}

function workflowWidgetGlyph(title) {
  const text = String(title || "");
  if (/Characteristics|Variables/.test(text)) return "◇";
  if (/Model|Modelling|Algorithm|Training|Experiment|Indicators/.test(text)) return "▥";
  if (/Collapse|Match|Keys/.test(text)) return "⇄";
  if (/Sample|Severation|Distribution|Quality|Missing/.test(text)) return "◫";
  if (/Report|Products/.test(text)) return "↗";
  return "∷";
}
