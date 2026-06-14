import { escapeHtml } from "../ui-utils.js";
import { listCapabilityTiers as listCapabilityTiersApi } from "./api_v2.js";
import {
  setCapabilityTiers,
  setSelectedTier,
} from "./state_v2.js";

export const selectedTierStorageKey = "marvis_v2_selected_tier";

const tierLabels = {
  deterministic_only: "Deterministic",
  guarded: "Guided",
  conservative: "Conservative",
  balanced: "Balanced",
  explorer: "Exploratory",
  autonomous: "Autonomous",
};

const tierLimitLabels = {
  name: "Name",
  summary: "Description",
  max_steps: "Step limit",
  max_replans: "Replanning limit",
  allow_parallel: "Parallel execution",
  allow_network: "Network access",
  default_autonomy_level: "Default autonomy level",
  max_replan_iterations: "Replanning limit",
  max_plan_depth: "Plan depth limit",
  allow_explore_mode: "Exploration",
  max_auto_gates: "Automatic confirmations per turn",
};

// Internal orchestrator knobs that mean nothing to a user reading a settings
// page; name/summary already render as the card title/description.
const hiddenTierLimitKeys = new Set([
  "name",
  "summary",
  "failure_driven_replan",
  "decision_point_replan",
  "explore_segment_size",
]);

// The slots only regulate the budget for self-government (re-planning, planned steps, exploration model) and confirm that the doors and security fences are consistent under all tranches
// (Seemarvis/domain.py It's...capability_tier Note). The summary only describes budget differences, with the values in the bottom label.
const tierNameSummaries = {
  conservative: "Lower limits for replanning and plan depth. Exploration is disabled.",
  balanced: "Default limits for replanning and plan depth. Exploration is enabled.",
  autonomous: "Higher limits for replanning and plan depth. Exploration is enabled.",
};

function closest(target, selector) {
  return typeof target?.closest === "function" ? target.closest(selector) : null;
}

function tierDisplayName(tier = {}) {
  return tierLabels[tier.name] || tier.name || "Unnamed profile";
}

function tierSummary(tier = {}) {
  const raw = String(tier.summary || "");
  const translated = {
    "Guarded execution": "Limited replanning and plan depth.",
    "Default autonomy": "Default limits for replanning and plan depth.",
    "Higher autonomy": "Higher limits for replanning and plan depth.",
  }[raw] || raw;
  return translated || tierNameSummaries[tier.name] || "";
}

function tierLimitValue(key, value) {
  if (typeof value === "boolean") return value ? "Allowed" : "Disabled";
  if (key === "default_autonomy_level") return `L${value}`;
  if (key === "max_replan_iterations" || key === "max_replans") return `${value} attempts`;
  if (key === "max_plan_depth" || key === "max_steps") return `${value} steps`;
  if (key === "max_auto_gates") return `${value} confirmations`;
  return String(value);
}

function tierOptionHtml(tier, defaultTier) {
  const selected = tier.name === defaultTier ? " selected" : "";
  const summary = tierSummary(tier);
  return `<option value="${escapeHtml(tier.name)}"${selected}>${escapeHtml(tierDisplayName(tier))}${summary ? ` - ${escapeHtml(summary)}` : ""}</option>`;
}

export function capabilitySelectHtmlFromData(data = {}) {
  const tiers = data.tiers || [];
  const options = tiers.map((tier) => tierOptionHtml(tier, data.default)).join("");
  return `<label>
    Autonomy profile
    <select id="tierSelect">${options}</select>
  </label>`;
}

export async function capabilitySelectHtml(deps = {}) {
  const actions = {
    listCapabilityTiers: listCapabilityTiersApi,
    ...deps,
  };
  const data = await actions.listCapabilityTiers();
  return capabilitySelectHtmlFromData(data);
}

function tierLimitsHtml(tier) {
  const entries = Object.entries(tier)
    .filter(([key]) => !hiddenTierLimitKeys.has(key))
    .map(([key, value]) => `<span class="tier-limit"><b>${escapeHtml(tierLimitLabels[key] || key)}</b>${escapeHtml(": ")}${escapeHtml(tierLimitValue(key, value))}</span>`)
    .join("");
  return entries || '<span class="tier-limit">No limits specified.</span>';
}

export function tierSettingsHtml(data = {}) {
  const tiers = data.tiers || [];
  const selected = data.selected || data.default || "";
  const rows = tiers.map((tier) => {
    const isSelected = tier.name === selected;
    const summary = tierSummary(tier);
    return `<label class="tier-row${isSelected ? " is-selected" : ""}">
      <input class="tier-row-radio" type="radio" name="capabilityTier" value="${escapeHtml(tier.name)}"${isSelected ? " checked" : ""} />
      <span class="tier-check" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false"><path d="M5 13l4 4L19 7"></path></svg>
      </span>
      <span class="tier-row-body">
        <h4>${escapeHtml(tierDisplayName(tier))}</h4>
        ${summary ? `<p>${escapeHtml(summary)}</p>` : ""}
        <div class="tier-limits">${tierLimitsHtml(tier)}</div>
      </span>
    </label>`;
  }).join("");
  return `<section class="tier-settings">
    <div class="tier-settings-head">
      <div class="settings-row-text">
        <strong>Autonomy profile</strong>
        <span>Set limits for replanning, plan depth and exploration. Required confirmations and data protections still apply.</span>
      </div>
    </div>
    <div class="tier-settings-list">${rows}</div>
  </section>`;
}

export function renderTierSettingsShell(container, data = {}) {
  if (!container) {
    throw new Error("renderTierSettingsShell requires a container");
  }
  if (container.dataset) {
    container.dataset.v2TierSettings = "true";
  }
  container.innerHTML = tierSettingsHtml(data);
  return () => {};
}

export async function renderTierSettings(container, deps = {}) {
  if (!container) {
    throw new Error("renderTierSettings requires a container");
  }
  if (container.dataset) {
    container.dataset.v2TierSettings = "true";
  }
  const actions = {
    listCapabilityTiers: listCapabilityTiersApi,
    ...deps,
  };
  const storage = deps.storage
    || (typeof localStorage !== "undefined" ? localStorage : null);
  const data = await actions.listCapabilityTiers();
  const persistedTier = String(storage?.getItem?.(selectedTierStorageKey) || "");
  const tierNames = new Set((data.tiers || []).map((tier) => String(tier.name || "")));
  const selectedTier = tierNames.has(persistedTier) ? persistedTier : data.default || "";
  setCapabilityTiers(data.tiers || []);
  setSelectedTier(selectedTier);
  container.innerHTML = tierSettingsHtml({ ...data, selected: selectedTier });
  return data;
}

export function attachCapabilityHandlers(root, deps = {}) {
  if (!root || typeof root.addEventListener !== "function") {
    throw new Error("attachCapabilityHandlers requires a stable event root");
  }
  const storage = deps.storage
    || (typeof localStorage !== "undefined" ? localStorage : null);
  const handler = async (event) => {
    const source = closest(event.target, "#tierSelect")
      || closest(event.target, 'input[name="capabilityTier"]');
    if (!source) {
      return;
    }
    const tier = String(source.value || "");
    setSelectedTier(tier);
    storage?.setItem?.(selectedTierStorageKey, tier);
  };
  root.addEventListener("change", handler);
  return () => root.removeEventListener?.("change", handler);
}
