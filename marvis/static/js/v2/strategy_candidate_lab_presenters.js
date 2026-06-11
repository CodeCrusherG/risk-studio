/** Candidate Lab structured payload to escaped HTML presenters. */

import { escapeHtml } from "../ui-utils.js";

import {
  INTERACTIVE_TREE_REVISION_ID_RE,
  INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_RE,
  INTERACTIVE_TREE_SPLIT_SEARCH_ID_RE,
  STRATEGY_TYPE_LABELS,
  collectionItems,
  fieldLabel,
  interactiveTreeEligiblePointers,
  interactiveTreeFrontierEligiblePointers,
  interactiveTreeThresholdEligiblePointers,
  isRecord,
  nonEmptyText,
  projectedStrategyItems,
  readableValue,
  stablePrimitiveText,
} from "./strategy_candidate_lab_contracts.js";

const COLLECTION_DEFINITIONS = Object.freeze([
  {
    key: "univariate",
    title: "Univariate candidates",
    description: "Binning results, candidate rankings and metrics",
    pointerKey: "bins",
  },
  {
    key: "cross_matrix",
    title: "Cross Matrix",
    description: "Two-dimensional bins, cell counts and risk metrics",
    pointerKey: "cells",
  },
  {
    key: "cross_search",
    title: "Field-pair search",
    description: "Field pairs, interaction gains and sparse-cell diagnostics",
    pointerKey: "",
  },
  {
    key: "cross_rule_search",
    title: "Threshold-rule search",
    description: "Two- and three-dimensional thresholds, constraints and rule identifiers",
    pointerKey: "",
  },
  {
    key: "cross_rule_candidate",
    title: "Threshold-rule candidate",
    description: "Candidate created from a selected threshold rule",
    pointerKey: "",
  },
  {
    key: "automatic_tree",
    title: "Automatic tree",
    description: "Tree structure, available branches and outcome metrics",
    pointerKey: "leaves",
  },
  {
    key: "interactive_tree_revision",
    title: "Interactive tree revision",
    description: "Tree structure, available branches, version history and validation results",
    pointerKey: "frontier",
  },
  {
    key: "interactive_tree_split_search",
    title: "Tree split candidates",
    description: "Threshold search over selected features within the specified budget",
    pointerKey: "",
  },
  {
    key: "scorecard_band",
    title: "Scorecard bands",
    description: "Raw PD bands, scorecard points and cutoff comparisons",
    pointerKey: "bands",
  },
  {
    key: "scorecard_cutoff_selection",
    title: "Cutoff selection",
    description: "Selected cutoff and source results",
    pointerKey: "",
  },
  {
    key: "voting_search",
    title: "Voting combinations",
    description: "Combination counts, eligibility constraints and identifiers",
    pointerKey: "",
  },
]);

function safeDownloadUrl(value) {
  const url = nonEmptyText(value);
  return url.startsWith("/api/") ? url.slice(1) : "";
}

function collectionTotal(collection) {
  return Number.isInteger(collection?.total) && collection.total >= 0
    ? collection.total
    : null;
}

function evidenceIdentityHtml(item) {
  const artifact = isRecord(item?.artifact) ? item.artifact : {};
  const rows = [
    ["Candidate ID", item?.candidate_id],
    ["Evidence Hash", item?.evidence_hash],
    ["Artifact ID", artifact.artifact_id],
    ["Content Hash", artifact.content_hash],
    ["Created", artifact.created_at],
  ].filter(([, value]) => value !== null && value !== undefined && value !== "");
  const downloadUrl = safeDownloadUrl(artifact.download_url);
  return [
    '<dl class="candidate-lab-identity">',
    ...rows.map(([label, value]) => (
      `<div><dt>${escapeHtml(label)}</dt><dd><code>${escapeHtml(value)}</code></dd></div>`
    )),
    "</dl>",
    downloadUrl
      ? `<a class="button compact secondary candidate-lab-download" href="${escapeHtml(downloadUrl)}" download>Download artifact</a>`
      : "",
  ].join("");
}

function factRows(value, options = {}) {
  if (!isRecord(value)) return [];
  const excluded = new Set(options.exclude || []);
  return Object.entries(value)
    .filter(([key, item]) => !excluded.has(key) && item !== null && item !== undefined)
    .slice(0, options.limit || 40);
}

function factsTableHtml(value, options = {}) {
  const rows = factRows(value, options);
  if (!rows.length) return "";
  return [
    '<div class="candidate-lab-table-scroll">',
    '<table class="candidate-lab-table candidate-lab-facts"><tbody>',
    ...rows.map(([key, item]) => (
      `<tr><th>${escapeHtml(fieldLabel(key))}</th><td>${escapeHtml(readableValue(item))}</td></tr>`
    )),
    "</tbody></table>",
    "</div>",
  ].join("");
}

function lifecycleHtml(value) {
  if (!isRecord(value)) return "";
  const facts = factsTableHtml(value);
  return facts
    ? `<section class="candidate-lab-subsection"><h5>Lifecycle</h5>${facts}</section>`
    : "";
}

function riskHtml(value) {
  if (!isRecord(value)) return "";
  const redFlags = Array.isArray(value.red_flags) ? value.red_flags : [];
  const reportGaps = Array.isArray(value.report_info_gaps) ? value.report_info_gaps : [];
  if (!redFlags.length && !reportGaps.length) return "";
  const list = (items, label, tone) => {
    if (!items.length) return "";
    return [
      `<div class="candidate-lab-risk-group" data-tone="${escapeHtml(tone)}">`,
      `<strong>${escapeHtml(label)}</strong>`,
      "<ul>",
      ...items.slice(0, 24).map((item) => `<li>${escapeHtml(readableValue(item))}</li>`),
      "</ul>",
      items.length > 24 ? "<p>Additional risk items are omitted from this view.</p>" : "",
      "</div>",
    ].join("");
  };
  return [
    '<section class="candidate-lab-subsection"><h5>Risks and reporting gaps</h5>',
    list(redFlags, "Risk flags", "warn"),
    list(reportGaps, "Reporting gaps", "info"),
    "</section>",
  ].join("");
}

function pointerColumns(pointerKey) {
  if (pointerKey === "bins") {
    return ["feature", "method", "bin_id"];
  }
  if (pointerKey === "cells") {
    return ["cell_id", "row_bin_id", "column_bin_id", "effect"];
  }
  return [
    "leaf_id",
    "fragment_id",
    "rule_id",
    "effect_id",
    "condition",
    "metrics",
  ];
}

function pointerTableHtml(item, pointerKey) {
  const pointers = Array.isArray(item?.pointers?.[pointerKey])
    ? item.pointers[pointerKey].filter(isRecord)
    : [];
  if (!pointers.length) return "";
  const columns = pointerColumns(pointerKey);
  const header = columns.map((key) => `<th>${escapeHtml(fieldLabel(key))}</th>`).join("");
  const rows = pointers.map((pointer) => [
    "<tr>",
    ...columns.map((key) => `<td>${escapeHtml(readableValue(pointer[key]))}</td>`),
    "</tr>",
  ].join("")).join("");
  const total = Number.isInteger(item.total) && item.total >= 0 ? item.total : null;
  const truncation = item.truncated
    ? `<p class="candidate-lab-truncated">Showing ${escapeHtml(pointers.length)}${total === null ? "" : ` / ${escapeHtml(total)}`} items. Additional results are omitted.</p>`
    : "";
  return [
    '<section class="candidate-lab-subsection">',
    `<h5>${pointerKey === "bins" ? "Candidate bins" : pointerKey === "cells" ? "Matrix cells" : pointerKey === "frontier" ? "Available branch rules" : "Leaf nodes"}</h5>`,
    '<div class="candidate-lab-table-scroll">',
    `<table class="candidate-lab-table"><thead><tr>${header}</tr></thead><tbody>${rows}</tbody></table>`,
    "</div>",
    truncation,
    "</section>",
  ].join("");
}

function candidateDetailHtml(item, pointerKey) {
  const detail = isRecord(item?.detail) ? item.detail : {};
  const title = nonEmptyText(detail.asset_id)
    || nonEmptyText(item?.candidate_id)
    || nonEmptyText(item?.artifact?.artifact_id)
    || "Candidate results";
  const detailFacts = factsTableHtml(detail);
  return [
    '<details class="candidate-lab-evidence-card">',
    '<summary>',
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(title)}</strong>`,
    `<small>${escapeHtml(nonEmptyText(item?.kind) || "Verified candidate")}</small>`,
    "</span>",
    '<span class="candidate-lab-card-state">View results</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    evidenceIdentityHtml(item),
    lifecycleHtml(item.lifecycle),
    detailFacts
      ? `<section class="candidate-lab-subsection"><h5>Summary of results</h5>${detailFacts}</section>`
      : "",
    pointerTableHtml(item, pointerKey),
    riskHtml(item.risks),
    item?.truncated && !Array.isArray(item?.pointers?.[pointerKey])
      ? '<p class="candidate-lab-truncated">Additional candidates are omitted from this view.</p>'
      : "",
    "</div>",
    "</details>",
  ].join("");
}

function scorecardDirectionNoteHtml() {
  return [
    '<div class="candidate-lab-boundary-note" data-tone="info">',
    "<strong>Score direction</strong>",
    "<p>Higher raw PD means higher risk. Higher scorecard points mean lower risk.</p>",
    "<p>Choose a cutoff to record the boundary. Approval or rejection actions are assigned separately in the strategy pool.</p>",
    "</div>",
  ].join("");
}

function scorecardRowsTableHtml(rows, columns, emptyText) {
  const visible = Array.isArray(rows) ? rows.filter(isRecord) : [];
  if (!visible.length) {
    return `<p class="candidate-lab-empty">${escapeHtml(emptyText)}</p>`;
  }
  return [
    '<div class="candidate-lab-table-scroll">',
    '<table class="candidate-lab-table"><thead><tr>',
    ...columns.map((key) => `<th>${escapeHtml(fieldLabel(key))}</th>`),
    "</tr></thead><tbody>",
    ...visible.map((row) => [
      "<tr>",
      ...columns.map((key) => `<td>${escapeHtml(readableValue(row[key]))}</td>`),
      "</tr>",
    ].join("")),
    "</tbody></table>",
    "</div>",
  ].join("");
}

function scorecardPointIntervalText(row) {
  const lowerMissing = row.lower === null || row.lower === undefined || row.lower === "";
  const upperMissing = row.upper === null || row.upper === undefined || row.upper === "";
  if (lowerMissing && upperMissing) return "-";
  const lower = lowerMissing ? "-∞" : stablePrimitiveText(row.lower);
  const upper = upperMissing ? "+∞" : stablePrimitiveText(row.upper);
  return `${lower} ~ ${upper}`;
}

function scorecardPointValue(row, key) {
  if (key === "feature" && row.feature === "__base__") {
    return "Base points";
  }
  if (key === "interval") return scorecardPointIntervalText(row);
  return stablePrimitiveText(row[key]);
}

function scorecardScaleHtml(rows) {
  const base = rows.find((row) => row.feature === "__base__");
  if (!base) return "";
  const scale = factsTableHtml({
    base_points: base.points,
    base_score: base.base_score,
    pdo: base.pdo,
    base_odds: base.base_odds,
    factor: base.factor,
    offset: base.offset,
  });
  return scale
    ? `<section class="candidate-lab-subsection"><h6>Base points and scaling</h6>${scale}</section>`
    : "";
}

function scorecardPointsDetailHtml(item, rows) {
  const visible = Array.isArray(rows) ? rows.filter(isRecord) : [];
  const columns = [
    ["feature", "Fields"],
    ["bin_label", "Bin label"],
    ["interval", "Intersection"],
    ["count", "Sample count"],
    ["good_count", "Good outcomes"],
    ["bad_count", "Bad outcomes"],
    ["bad_rate", "Bad rate"],
    ["woe", "WOE"],
    ["iv_contribution", "IV Contribution"],
    ["coefficient", "coefficient"],
    ["monotonic_direction", "Unarranged"],
    ["points", "Value"],
  ];
  const table = visible.length
    ? [
      '<div class="candidate-lab-table-scroll">',
      '<table class="candidate-lab-table"><thead><tr>',
      ...columns.map(([, label]) => `<th>${escapeHtml(label)}</th>`),
      "</tr></thead><tbody>",
      ...visible.map((row) => [
        "<tr>",
        ...columns.map(([key]) => (
          `<td>${escapeHtml(scorecardPointValue(row, key))}</td>`
        )),
        "</tr>",
      ].join("")),
      "</tbody></table>",
      "</div>",
    ].join("")
    : '<p class="candidate-lab-empty">Scorecard point details are unavailable.</p>';
  const truncation = item?.truncated
    ? `<p class="candidate-lab-truncated">Showing the first ${escapeHtml(visible.length)} scorecard rows.</p>`
    : "";
  return [
    '<details class="candidate-lab-evidence-card candidate-lab-scorecard-points" data-candidate-lab-scorecard-points>',
    "<summary>",
    '<span class="candidate-lab-card-title">',
    "<strong>Scorecard point details</strong>",
    `<small>${escapeHtml(visible.length)} rows</small>`,
    "</span>",
    '<span class="candidate-lab-card-state">View points</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    '<div class="candidate-lab-boundary-note" data-tone="info">',
    "<strong>Score direction</strong>",
    "<p>Higher scorecard points indicate lower risk.</p>",
    "</div>",
    scorecardScaleHtml(visible),
    table,
    truncation,
    "</div>",
    "</details>",
  ].join("");
}

function scorecardBandDetailHtml(item) {
  const detail = isRecord(item?.detail) ? item.detail : {};
  const pointers = isRecord(item?.pointers) ? item.pointers : {};
  const title = nonEmptyText(detail.asset_id)
    || nonEmptyText(item?.candidate_id)
    || "Scorecard bands";
  return [
    '<details class="candidate-lab-evidence-card candidate-lab-scorecard-card">',
    '<summary>',
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(title)}</strong>`,
    "<small>Verified scorecard bands</small>",
    "</span>",
    '<span class="candidate-lab-card-state">View bands and cutoffs</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    evidenceIdentityHtml(item),
    lifecycleHtml(item.lifecycle),
    scorecardDirectionNoteHtml(),
    '<section class="candidate-lab-subsection"><h5>Samples and performance</h5>',
    factsTableHtml({
      asset_id: detail.asset_id,
      sample: detail.sample,
      performance: detail.performance,
    }),
    "</section>",
    '<section class="candidate-lab-subsection"><h5>Band results</h5>',
    scorecardRowsTableHtml(
      pointers.bands,
      [
        "ordinal",
        "bin_id",
        "lower_bound",
        "upper_bound",
        "count",
        "share",
        "labeled_count",
        "bad_count",
        "bad_rate",
        "average_pd",
      ],
      "Scorecard bands are unavailable.",
    ),
    "</section>",
    '<section class="candidate-lab-subsection"><h5>Cutoff metrics</h5>',
    scorecardRowsTableHtml(
      pointers.cutoffs,
      [
        "ordinal",
        "cutoff_id",
        "execution_pd",
        "display_points",
        "lower_risk",
        "higher_risk",
      ],
      "Cutoff results are unavailable.",
    ),
    "</section>",
    scorecardPointsDetailHtml(item, pointers.scorecard_points),
    riskHtml(item.risks),
    "</div>",
    "</details>",
  ].join("");
}

function scorecardSelectionDetailHtml(item) {
  const detail = isRecord(item?.detail) ? item.detail : {};
  const effect = isRecord(detail.effect) ? [detail.effect] : [];
  const title = nonEmptyText(detail.selection_id)
    || nonEmptyText(item?.candidate_id)
    || "Cutoff selection";
  return [
    '<details class="candidate-lab-evidence-card candidate-lab-scorecard-card">',
    '<summary>',
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(title)}</strong>`,
    "<small>Manually selected cutoff</small>",
    "</span>",
    '<span class="candidate-lab-card-state">View selection</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    evidenceIdentityHtml(item),
    lifecycleHtml(item.lifecycle),
    scorecardDirectionNoteHtml(),
    '<section class="candidate-lab-subsection"><h5>Selection record</h5>',
    factsTableHtml({
      selection_id: detail.selection_id,
      asset_id: detail.asset_id,
      cutoff_id: detail.cutoff_id,
      reason: detail.reason,
    }),
    "</section>",
    '<section class="candidate-lab-subsection"><h5>Cutoff metrics</h5>',
    scorecardRowsTableHtml(
      effect,
      [
        "ordinal",
        "cutoff_id",
        "execution_pd",
        "display_points",
        "lower_risk",
        "higher_risk",
      ],
      "No cutoff metrics are available for this selection.",
    ),
    "</section>",
    riskHtml(item.risks),
    "</div>",
    "</details>",
  ].join("");
}

function votingSearchDetailHtml(item) {
  const combinations = Array.isArray(item?.combinations)
    ? item.combinations.filter(isRecord)
    : [];
  const title = nonEmptyText(item?.search_id) || "Voting combinations";
  const summary = {
    strategy_type: item?.strategy_type,
    pool_revision: item?.pool_revision,
    member_count: item?.member_count,
    n: item?.n,
    objective: item?.objective,
    constraints: item?.constraints,
    include_rule_ids: item?.include_rule_ids,
    exclude_rule_ids: item?.exclude_rule_ids,
    max_combinations: item?.max_combinations,
    search_space: item?.search_space,
    evaluated: item?.evaluated,
    eligible: item?.eligible,
    truncated: item?.truncated,
  };
  return [
    '<details class="candidate-lab-evidence-card candidate-lab-voting-card">',
    "<summary>",
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(title)}</strong>`,
    "<small>Search results · candidate not yet built</small>",
    "</span>",
    '<span class="candidate-lab-card-state">View combinations</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    evidenceIdentityHtml({ artifact: item?.artifact }),
    '<div class="candidate-lab-boundary-note" data-tone="info">',
    "<strong>Candidate selection</strong>",
    "<p>Compare the evaluated combinations against your objective and constraints, then select one to build.</p>",
    "</div>",
    '<section class="candidate-lab-subsection"><h5>Search parameters and counts</h5>',
    factsTableHtml(summary),
    "</section>",
    '<section class="candidate-lab-subsection"><h5>Combination identifiers</h5>',
    scorecardRowsTableHtml(
      combinations,
      ["combo_id", "members", "eligible", "failures", "metrics"],
      "No combinations are available.",
    ),
    "</section>",
    item?.truncated
      ? '<p class="candidate-lab-truncated">The search budget limits the results shown.</p>'
      : "",
    "</div>",
    "</details>",
  ].join("");
}

function crossSearchDetailHtml(item) {
  const features = Array.isArray(item?.features)
    ? item.features.filter(isRecord)
    : [];
  const pairs = Array.isArray(item?.pairs)
    ? item.pairs.filter(isRecord)
    : [];
  const title = nonEmptyText(item?.search_id) || "Field-pair search";
  const truncated = item?.truncated === true;
  return [
    '<details class="candidate-lab-evidence-card candidate-lab-cross-search-card">',
    "<summary>",
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(title)}</strong>`,
    `<small>${escapeHtml(stablePrimitiveText(item?.evaluated))} / ${escapeHtml(stablePrimitiveText(item?.search_space))} pairs evaluated · candidate not yet built</small>`,
    "</span>",
    '<span class="candidate-lab-card-state">View combinations</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    evidenceIdentityHtml({ artifact: item?.artifact }),
    '<div class="candidate-lab-boundary-note" data-tone="info">',
    "<strong>Candidate selection</strong>",
    "<p>Review rank, eligibility and metrics, then select a pair to build.</p>",
    "</div>",
    '<section class="candidate-lab-subsection"><h5>Search parameters and budget</h5>',
    factsTableHtml({
      max_pairs: item?.max_pairs,
      search_space: item?.search_space,
      evaluated: item?.evaluated,
      eligible: item?.eligible,
      truncated,
    }),
    "</section>",
    '<section class="candidate-lab-subsection"><h5>Univariate search fields</h5>',
    scorecardRowsTableHtml(
      features,
      ["feature", "method", "axis_iv", "bin_count"],
      "Search field configuration is unavailable.",
    ),
    "</section>",
    '<section class="candidate-lab-subsection"><h5>Field pairs</h5>',
    scorecardRowsTableHtml(
      pairs,
      [
        "rank",
        "pair_id",
        "x_feature",
        "x_method",
        "y_feature",
        "y_method",
        "x_axis_iv",
        "y_axis_iv",
        "cross_total_iv",
        "interaction_gain_iv",
        "cell_count",
        "empty_cell_count",
        "empty_cell_share",
        "min_nonempty_cell_count",
        "eligible",
      ],
      "No field pairs are available.",
    ),
    "</section>",
    truncated
      ? [
        '<div class="candidate-lab-risk-group" data-tone="warn">',
        "<strong>Search budget reached</strong>",
        `<p>${escapeHtml(stablePrimitiveText(item?.evaluated))} pairs evaluated from ${escapeHtml(stablePrimitiveText(item?.search_space))} possible pairs; budget: ${escapeHtml(stablePrimitiveText(item?.max_pairs))}.</p>`,
        "</div>",
      ].join("")
      : '<p class="candidate-lab-field-help">Search completed within budget. Select a pair to continue.</p>',
    "</div>",
    "</details>",
  ].join("");
}

function crossRuleSearchDetailHtml(item) {
  const features = Array.isArray(item?.features)
    ? item.features.filter(isRecord)
    : [];
  const rules = Array.isArray(item?.rules)
    ? item.rules.filter(isRecord)
    : [];
  return [
    '<details class="candidate-lab-evidence-card candidate-lab-cross-search-card">',
    "<summary>",
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(nonEmptyText(item?.search_id) || "Threshold-rule search")}</strong>`,
    `<small>${escapeHtml(stablePrimitiveText(item?.dimension))}D · ${escapeHtml(stablePrimitiveText(item?.evaluated))} / ${escapeHtml(stablePrimitiveText(item?.search_space))} rules evaluated · none selected</small>`,
    "</span>",
    '<span class="candidate-lab-card-state">View rules</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    evidenceIdentityHtml({ artifact: item?.artifact }),
    '<div class="candidate-lab-boundary-note" data-tone="info">',
    "<strong>Rule selection</strong>",
    "<p>Review eligibility and metrics, then select a rule ID to build.</p>",
    "</div>",
    '<section class="candidate-lab-subsection"><h5>Search parameters and budget</h5>',
    factsTableHtml({
      dimension: item?.dimension,
      constraints: item?.constraints,
      max_trials: item?.max_trials,
      search_space: item?.search_space,
      evaluated: item?.evaluated,
      eligible: item?.eligible,
      truncated: item?.truncated,
    }),
    "</section>",
    '<section class="candidate-lab-subsection"><h5>Threshold sources</h5>',
    scorecardRowsTableHtml(
      features,
      ["feature", "method", "risk_direction", "thresholds", "excluded_values", "missing_count", "missing_bad"],
      "Threshold configuration is unavailable.",
    ),
    "</section>",
    '<section class="candidate-lab-subsection"><h5>Rule identifiers</h5>',
    scorecardRowsTableHtml(
      rules,
      ["rank", "rule_id", "conditions", "metrics", "eligible", "constraint_failures"],
      "No rules are available.",
    ),
    "</section>",
    item?.rules_truncated
      ? '<p class="candidate-lab-truncated">Some evaluated rules are omitted. Download the search results for the full list.</p>'
      : "",
    "</div>",
    "</details>",
  ].join("");
}

function crossRuleCandidateDetailHtml(item) {
  const detail = isRecord(item?.detail) ? item.detail : {};
  return [
    '<details class="candidate-lab-evidence-card">',
    "<summary>",
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(nonEmptyText(detail.asset_id) || "Threshold-rule candidate")}</strong>`,
    `<small>${escapeHtml(stablePrimitiveText(detail.dimension))}D · development / ${escapeHtml(stablePrimitiveText(detail.validation_status))}</small>`,
    "</span>",
    '<span class="candidate-lab-card-state">View candidate</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    evidenceIdentityHtml({ artifact: item?.artifact }),
    '<section class="candidate-lab-subsection"><h5>Sources and outcomes</h5>',
    factsTableHtml(detail),
    "</section>",
    '<div class="candidate-lab-boundary-note" data-tone="info">',
    "<strong>Candidate status</strong>",
    "<p>Candidate created. Complete independent validation before adoption.</p>",
    "</div>",
    riskHtml(item?.risks),
    "</div>",
    "</details>",
  ].join("");
}

function interactiveTreeNodesHtml(item) {
  const nodes = Array.isArray(item?.pointers?.nodes)
    ? item.pointers.nodes.filter(isRecord)
    : [];
  if (!nodes.length) {
    return '<p class="candidate-lab-empty">No tree nodes are available.</p>';
  }
  const eligible = new Set(
    interactiveTreeEligiblePointers(item).map(
      (pointer) => `${pointer.source_tree_id}\u001f${pointer.node_id}`,
    ),
  );
  const thresholdAdjustments = new Map(
    interactiveTreeThresholdEligiblePointers(item).map(
      (pointer) => [
        `${pointer.source_tree_id}\u001f${pointer.node_id}`,
        pointer,
      ],
    ),
  );
  const sourceTreeId = nonEmptyText(item?.detail?.source_tree_id);
  const revisionId = item?.kind === "interactive_tree_revision"
    ? nonEmptyText(item?.detail?.revision_id)
    : "";
  const materializable = new Set(
    interactiveTreeFrontierEligiblePointers(item).map(
      (pointer) => pointer.source_node_id,
    ),
  );
  return [
    '<div class="candidate-lab-table-scroll candidate-lab-tree-scroll">',
    '<table class="candidate-lab-table candidate-lab-tree-table"><thead><tr>',
    "<th>Depth</th><th>Nodes</th><th>Split / condition</th><th>Sample metrics</th><th>Status</th><th>Operation</th>",
    "</tr></thead><tbody>",
    ...nodes.map((node) => {
      const nodeId = nonEmptyText(node.node_id);
      const key = `${sourceTreeId}\u001f${nodeId}`;
      const split = node.kind === "split"
        ? `${stablePrimitiveText(node.feature)} ≤ ${stablePrimitiveText(node.threshold)}; missing → ${stablePrimitiveText(node.missing_child)}`
        : readableValue(node.condition);
      const state = [
        node.is_visible === true ? "Visible" : "Hidden",
        node.is_frontier === true ? "frontier" : "",
      ].filter(Boolean).join(" · ");
      const actions = [];
      if (node.can_prune === true && eligible.has(key)) {
        actions.push([
          '<button type="button" class="button compact secondary candidate-lab-tree-prune"',
          ' data-candidate-lab-interactive-tree-prune="1"',
          ` data-source-tree-id="${escapeHtml(sourceTreeId)}"`,
          ` data-node-id="${escapeHtml(nodeId)}">Prune at this node</button>`,
        ].join(""));
      }
      const thresholdAdjustment = thresholdAdjustments.get(key);
      if (thresholdAdjustment) {
        actions.push([
          '<button type="button" class="button compact secondary candidate-lab-tree-threshold"',
          ' data-candidate-lab-interactive-tree-threshold="1"',
          ` data-source-tree-id="${escapeHtml(sourceTreeId)}"`,
          ` data-node-id="${escapeHtml(nodeId)}"`,
          ` data-feature="${escapeHtml(thresholdAdjustment.feature)}"`,
          ` data-current-threshold="${escapeHtml(stablePrimitiveText(
            thresholdAdjustment.current_threshold,
          ))}">Adjust ${escapeHtml(thresholdAdjustment.feature)} threshold</button>`,
        ].join(""));
      }
      if (
        INTERACTIVE_TREE_REVISION_ID_RE.test(revisionId)
        && materializable.has(nodeId)
      ) {
        actions.push([
          '<button type="button" class="button compact secondary candidate-lab-tree-frontier-materialize"',
          ' data-candidate-lab-interactive-tree-frontier-materialize="1"',
          ` data-revision-id="${escapeHtml(revisionId)}"`,
          ` data-source-node-id="${escapeHtml(nodeId)}">Create frontier candidate</button>`,
        ].join(""));
      }
      const action = actions.join(" ") || "—";
      return [
        "<tr>",
        `<td>${escapeHtml(stablePrimitiveText(node.depth))}</td>`,
        `<td><code>${escapeHtml(nodeId)}</code><small>${escapeHtml(stablePrimitiveText(node.kind))}</small></td>`,
        `<td>${escapeHtml(split)}</td>`,
        `<td>${escapeHtml(readableValue(node.metrics))}</td>`,
        `<td>${escapeHtml(state || "—")}</td>`,
        `<td>${action}</td>`,
        "</tr>",
      ].join("");
    }),
    "</tbody></table>",
    "</div>",
  ].join("");
}

function interactiveTreeDetailHtml(item) {
  const detail = isRecord(item?.detail) ? item.detail : {};
  const isRevision = item?.kind === "interactive_tree_revision";
  const identity = isRevision
    ? nonEmptyText(detail.revision_id)
    : nonEmptyText(detail.asset_id);
  const title = identity || (isRevision ? "Interactive tree revision" : "Automatic tree");
  const history = Array.isArray(item?.history)
    ? item.history.filter(isRecord)
    : [];
  return [
    '<details class="candidate-lab-evidence-card candidate-lab-tree-card">',
    "<summary>",
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(title)}</strong>`,
    `<small>${isRevision ? "Saved revision" : "Verified tree structure"}</small>`,
    "</span>",
    '<span class="candidate-lab-card-state">View tree</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    evidenceIdentityHtml(item),
    lifecycleHtml(item.lifecycle),
    '<div class="candidate-lab-boundary-note" data-tone="info">',
    "<strong>Tree revisions</strong>",
    "<p>Pruning or adjusting a threshold creates a new revision and preserves the source tree.</p>",
    "</div>",
    '<section class="candidate-lab-subsection"><h5>Tree and revision identifiers</h5>',
    factsTableHtml({
      source_tree_id: detail.source_tree_id,
      derived_from_source_tree_id: detail.derived_from_source_tree_id,
      parent_revision_id: detail.parent_revision_id,
      base_asset_id: detail.base_asset_id || detail.asset_id,
      asset_hash: detail.asset_hash,
      tree_id: detail.tree_id,
      tree_result_hash: detail.tree_result_hash,
      semantic_tree_id: detail.semantic_tree_id,
      tree_hash: detail.tree_hash,
      edit: detail.edit,
      summary: detail.summary,
    }),
    "</section>",
    isRevision
      ? [
        '<section class="candidate-lab-subsection"><h5>Branch history, newest first</h5>',
        scorecardRowsTableHtml(
          history,
          ["revision_id", "parent_revision_id", "edit", "semantic_tree_id"],
          "No history is available for this revision.",
        ),
        "</section>",
      ].join("")
      : "",
    pointerTableHtml(item, isRevision ? "frontier" : "leaves"),
    '<section class="candidate-lab-subsection"><h5>Tree nodes</h5>',
    interactiveTreeNodesHtml(item),
    "</section>",
    '<p class="candidate-lab-field-help">Available actions are checked against the current tree, task and sample when submitted.</p>',
    riskHtml(item.risks),
    "</div>",
    "</details>",
  ].join("");
}

function interactiveTreeSplitSearchDetailHtml(item) {
  const searchId = nonEmptyText(item?.search_id);
  const sourceTreeId = nonEmptyText(item?.source_tree_id);
  const nodeId = nonEmptyText(item?.node_id);
  const sourceNode = isRecord(item?.source_node) ? item.source_node : {};
  const candidates = Array.isArray(item?.candidates)
    ? item.candidates.filter(isRecord)
    : [];
  const canPrefill = (
    sourceNode.kind === "split"
    && sourceNode.is_visible === true
    && sourceNode.is_frontier !== true
    && sourceNode.can_prune === true
  );
  return [
    '<details class="candidate-lab-evidence-card candidate-lab-tree-card">',
    "<summary>",
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(searchId || "Tree split search")}</strong>`,
    `<small>${escapeHtml(sourceTreeId)} · ${escapeHtml(nodeId)}</small>`,
    "</span>",
    `<span class="candidate-lab-card-state">${escapeHtml(stablePrimitiveText(
      candidates.length,
    ))} Candidates</span>`,
    "</summary>",
    '<div class="candidate-lab-card-body">',
    evidenceIdentityHtml(item),
    '<div class="candidate-lab-boundary-note" data-tone="info">',
    "<strong>Split selection</strong>",
    "<p>Select a split, review the proposed change, then confirm to create a revision.</p>",
    "</div>",
    factsTableHtml({
      search_id: searchId,
      source_tree_id: sourceTreeId,
      node_id: nodeId,
      node_kind: item?.node_kind,
      mode: item?.mode,
      features: item?.features,
      population: item?.population,
      budget: item?.budget,
      claims: item?.claims,
    }),
    '<div class="candidate-lab-table-scroll">',
    '<table class="candidate-lab-table"><thead><tr>',
    "<th>Rank</th><th>Feature / threshold</th><th>Left</th><th>Right</th><th>Gain / direction</th><th>Eligibility</th><th>Operation</th>",
    "</tr></thead><tbody>",
    ...candidates.map((candidate) => {
      const candidateId = nonEmptyText(candidate.candidate_id);
      const feature = nonEmptyText(candidate.feature);
      const threshold = Number(candidate.threshold);
      const eligible = candidate.eligible === true;
      const changesSplit = (
        feature !== nonEmptyText(sourceNode.feature)
        || threshold !== Number(sourceNode.threshold)
      );
      const revisionAction = (
        eligible
        && canPrefill
        && changesSplit
        && INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_RE.test(candidateId)
        && Number.isFinite(threshold)
      )
        ? [
          '<button type="button" class="button compact secondary"',
          ' data-candidate-lab-interactive-tree-split-candidate="1"',
          ` data-search-id="${escapeHtml(searchId)}"`,
          ` data-candidate-id="${escapeHtml(candidateId)}"`,
          ` data-source-tree-id="${escapeHtml(sourceTreeId)}"`,
          ` data-node-id="${escapeHtml(nodeId)}"`,
          ` data-feature="${escapeHtml(feature)}"`,
          ` data-threshold="${escapeHtml(stablePrimitiveText(threshold))}">`,
          "Review tree revision</button>",
        ].join("")
        : "";
      const continuationAction = (
        eligible
        && sourceNode.is_visible === true
        && sourceNode.is_frontier === true
        && INTERACTIVE_TREE_SPLIT_SEARCH_ID_RE.test(searchId)
        && INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_RE.test(candidateId)
      )
        ? [
          '<button type="button" class="button compact secondary"',
          ' data-candidate-lab-interactive-tree-auto-continuation="1"',
          ` data-search-id="${escapeHtml(searchId)}"`,
          ` data-candidate-id="${escapeHtml(candidateId)}">`,
          "Review tree continuation</button>",
        ].join("")
        : "";
      const action = [revisionAction, continuationAction]
        .filter(Boolean)
        .join(" ") || "—";
      return [
        "<tr>",
        `<td>${escapeHtml(stablePrimitiveText(candidate.rank))}</td>`,
        `<td><strong>${escapeHtml(feature)}</strong><small>≤ ${escapeHtml(
          stablePrimitiveText(threshold),
        )} · Missing→${escapeHtml(stablePrimitiveText(candidate.missing_child))}</small></td>`,
        `<td>${escapeHtml(readableValue(candidate.left))}</td>`,
        `<td>${escapeHtml(readableValue(candidate.right))}</td>`,
        `<td>${escapeHtml(stablePrimitiveText(candidate.gain))}<small>${escapeHtml(
          readableValue(candidate.direction),
        )}</small></td>`,
        `<td>${eligible ? "Available" : escapeHtml(readableValue(candidate.failures))}</td>`,
        `<td>${action}</td>`,
        "</tr>",
      ].join("");
    }),
    "</tbody></table>",
    "</div>",
    item?.truncated === true
      ? '<p class="candidate-lab-truncated">Results are limited by the configured search budget.</p>'
      : "",
    "</div>",
    "</details>",
  ].join("");
}

function candidateItemHtml(item, definition) {
  if (
    definition.key === "automatic_tree"
    || definition.key === "interactive_tree_revision"
  ) {
    return interactiveTreeDetailHtml(item);
  }
  if (definition.key === "scorecard_band") {
    return scorecardBandDetailHtml(item);
  }
  if (definition.key === "interactive_tree_split_search") {
    return interactiveTreeSplitSearchDetailHtml(item);
  }
  if (definition.key === "scorecard_cutoff_selection") {
    return scorecardSelectionDetailHtml(item);
  }
  if (definition.key === "voting_search") {
    return votingSearchDetailHtml(item);
  }
  if (definition.key === "cross_search") {
    return crossSearchDetailHtml(item);
  }
  if (definition.key === "cross_rule_search") {
    return crossRuleSearchDetailHtml(item);
  }
  if (definition.key === "cross_rule_candidate") {
    return crossRuleCandidateDetailHtml(item);
  }
  return candidateDetailHtml(item, definition.pointerKey);
}

function candidateCollectionHtml(candidates, definition) {
  const collection = isRecord(candidates?.[definition.key])
    ? candidates[definition.key]
    : {};
  const items = collectionItems(collection);
  const total = collectionTotal(collection);
  const countText = total === null ? "" : `${total} individual`;
  const list = items.length
    ? items.map((item) => candidateItemHtml(item, definition)).join("")
    : '<p class="candidate-lab-empty">Verified results are unavailable.</p>';
  return [
    '<section class="candidate-lab-result-group">',
    '<header class="candidate-lab-result-head">',
    "<div>",
    `<h4>${escapeHtml(definition.title)}</h4>`,
    `<p>${escapeHtml(definition.description)}</p>`,
    "</div>",
    countText ? `<strong>${escapeHtml(countText)}</strong>` : "",
    "</header>",
    collection?.truncated
      ? '<p class="candidate-lab-truncated">Only the latest candidates are shown.</p>'
      : "",
    `<div class="candidate-lab-result-list">${list}</div>`,
    "</section>",
  ].join("");
}

function poolEntryTableHtml(entries) {
  const rows = Array.isArray(entries) ? entries.filter(isRecord) : [];
  if (!rows.length) return '<p class="candidate-lab-empty">The pool has no entries.</p>';
  const columns = ["position", "rule_id", "source", "action", "execution", "enabled"];
  return [
    '<div class="candidate-lab-table-scroll">',
    '<table class="candidate-lab-table"><thead><tr>',
    ...columns.map((key) => `<th>${escapeHtml(fieldLabel(key))}</th>`),
    "</tr></thead><tbody>",
    ...rows.map((entry) => [
      "<tr>",
      ...columns.map((key) => `<td>${escapeHtml(readableValue(entry[key]))}</td>`),
      "</tr>",
    ].join("")),
    "</tbody></table>",
    "</div>",
  ].join("");
}

function poolItemHtml(item) {
  const title = `${nonEmptyText(item.strategy_type) || "Strategy"} Pool · revision ${stablePrimitiveText(item.revision)}`;
  const facts = {
    pool_id: item.pool_id,
    strategy_type: item.strategy_type,
    revision: item.revision,
    revision_id: item.revision_id,
    snapshot_hash: item.snapshot_hash,
    status: item.status,
    validation_status: item.validation_status,
    default_action: item.default_action,
  };
  const visibleEntries = Array.isArray(item.entries) ? item.entries.length : 0;
  const total = Number.isInteger(item.total) && item.total >= 0 ? item.total : null;
  return [
    '<details class="candidate-lab-evidence-card candidate-lab-pool-card">',
    '<summary>',
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(title)}</strong>`,
    `<small>${escapeHtml(nonEmptyText(item.pool_id) || "Pool for this task")}</small>`,
    "</span>",
    '<span class="candidate-lab-card-state">View pool</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    evidenceIdentityHtml({ artifact: item.artifact }),
    '<section class="candidate-lab-subsection"><h5>Pool status</h5>',
    factsTableHtml(facts),
    "</section>",
    '<section class="candidate-lab-subsection"><h5>Entry order and actions</h5>',
    poolEntryTableHtml(item.entries),
    "</section>",
    item.truncated
      ? `<p class="candidate-lab-truncated">Showing ${escapeHtml(visibleEntries)}${total === null ? "" : ` / ${escapeHtml(total)}`} entries. Additional entries are omitted.</p>`
      : "",
    "</div>",
    "</details>",
  ].join("");
}

function poolCollectionHtml(pools) {
  const collection = isRecord(pools) ? pools : {};
  const items = collectionItems(collection);
  const total = collectionTotal(collection);
  return [
    '<section class="candidate-lab-result-group">',
    '<header class="candidate-lab-result-head">',
    "<div><h4>Strategy Pool</h4><p>Pool versions, entry order, actions and sources for this task</p></div>",
    total === null ? "" : `<strong>${escapeHtml(total)} pools</strong>`,
    "</header>",
    collection.truncated
      ? '<p class="candidate-lab-truncated">Additional pools are omitted.</p>'
      : "",
    '<div class="candidate-lab-result-list">',
    items.length
      ? items.map(poolItemHtml).join("")
      : '<p class="candidate-lab-empty">No strategy pools yet.</p>',
    "</div>",
    "</section>",
  ].join("");
}

const WORKFLOW_STAGE_STATUS_LABELS = Object.freeze({
  complete: "Completed",
  stale: "Refresh required",
  missing: "Not completed",
});

const REPORT_FIELD_AVAILABILITY_LABELS = Object.freeze({
  unavailable: "Not provided",
  not_applicable: "Not applicable",
  not_matured: "Outcomes not yet mature",
});

function workflowStageSpineHtml(stages) {
  const rows = Array.isArray(stages) ? stages.filter(isRecord).slice(0, 7) : [];
  if (!rows.length) {
    return '<p class="candidate-lab-empty">Stage status is unavailable.</p>';
  }
  return [
    '<ol class="candidate-lab-workflow-stages" aria-label="Strategy development stages">',
    ...rows.map((stage, index) => {
      const status = ["complete", "stale", "missing"].includes(stage.status)
        ? stage.status
        : "missing";
      return [
        `<li class="candidate-lab-workflow-stage" data-workflow-stage="${escapeHtml(nonEmptyText(stage.id) || String(index + 1))}" data-status="${escapeHtml(status)}">`,
        `<span>${index + 1}</span>`,
        `<strong>${escapeHtml(nonEmptyText(stage.label) || `Stage ${index + 1}`)}</strong>`,
        `<small>${escapeHtml(WORKFLOW_STAGE_STATUS_LABELS[status])}</small>`,
        "</li>",
      ].join("");
    }),
    "</ol>",
  ].join("");
}

function reportFieldReadableValue(field) {
  if (!isRecord(field)) return "Not provided";
  if (field.availability === "present") return readableValue(field.value);
  return REPORT_FIELD_AVAILABILITY_LABELS[field.availability]
    || nonEmptyText(field.availability)
    || "Not provided";
}

function projectContextHistoryHtml(histories) {
  const rows = Array.isArray(histories) ? histories.filter(isRecord) : [];
  if (!rows.length) {
    return '<p class="candidate-lab-empty">No historical strategy versions are available.</p>';
  }
  return [
    '<div class="candidate-lab-result-list">',
    ...rows.map((history) => [
      '<article class="candidate-lab-evidence-card candidate-lab-project-history">',
      `<strong>${history.version === null || history.version === undefined ? "External historical material" : `Version ${escapeHtml(history.version)}`}</strong>`,
      factsTableHtml({
        availability: history.availability,
        effective_period: reportFieldReadableValue(history.effective_period),
        asset_status: reportFieldReadableValue(history.asset_status),
        scope: reportFieldReadableValue(history.scope),
        traffic_allocation: reportFieldReadableValue(history.traffic_allocation),
        effect_stages: history.effect_stages,
        external_source_count: history.external_source_count,
      }),
      "</article>",
    ].join("")),
    "</div>",
  ].join("");
}

function projectContextMissingHtml(records) {
  const pending = Array.isArray(records)
    ? records.filter((item) => isRecord(item) && item.status === "pending")
    : [];
  if (!pending.length) return "";
  return [
    '<section class="candidate-lab-subsection candidate-lab-missing-information">',
    "<h5>Additional information</h5>",
    "<ul>",
    ...pending.map((item) => (
      `<li><strong>${escapeHtml(fieldLabel(item.field_path))}</strong><span>${escapeHtml(item.question)}</span></li>`
    )),
    "</ul>",
    "</section>",
  ].join("");
}

function projectContextWorkflowHtml(project) {
  if (!isRecord(project)) {
    return [
      '<section class="candidate-lab-subsection candidate-lab-project-context" data-status="missing">',
      "<h5>Project context and history</h5>",
      '<p class="candidate-lab-empty">Project context and history have not been saved.</p>',
      "</section>",
    ].join("");
  }
  const current = isRecord(project.current) ? project.current : {};
  const statusFields = isRecord(current.status_fields)
    ? current.status_fields
    : {};
  const downloadUrl = safeDownloadUrl(project.artifact?.download_url);
  return [
    '<section class="candidate-lab-subsection candidate-lab-project-context" data-status="complete">',
    "<header><div><h5>Project context and history</h5>",
    `<p>Context revision ${escapeHtml(stablePrimitiveText(project.revision))} · ${escapeHtml(stablePrimitiveText(project.as_of))}</p></div>`,
    downloadUrl
      ? `<a class="button compact secondary" href="${escapeHtml(downloadUrl)}" download>Download project context</a>`
      : "",
    "</header>",
    factsTableHtml({
      scope: reportFieldReadableValue(project.scope),
      volume: reportFieldReadableValue(statusFields.volume),
      approval: reportFieldReadableValue(statusFields.approval),
      risk: reportFieldReadableValue(statusFields.risk),
      economics: reportFieldReadableValue(statusFields.economics),
      maturity: reportFieldReadableValue(current.maturity_summary),
      history_resolution: project.history_resolution,
    }),
    '<section class="candidate-lab-subsection"><h5>Strategy version history</h5>',
    projectContextHistoryHtml(project.historical_versions),
    "</section>",
    projectContextMissingHtml(project.missing_information),
    "</section>",
  ].join("");
}

function samplePopulationHtml(role, population) {
  const title = role === "approval" ? "Approval population" : "Risk population";
  if (!isRecord(population)) {
    return [
      `<article class="candidate-lab-evidence-card candidate-lab-sample-population" data-population-role="${escapeHtml(role)}" data-status="missing">`,
      `<strong>${title}</strong>`,
      "<p>Not yet defined.</p>",
      "</article>",
    ].join("");
  }
  const maturity = isRecord(population.maturity) ? population.maturity : {};
  return [
    `<article class="candidate-lab-evidence-card candidate-lab-sample-population" data-population-role="${escapeHtml(role)}">`,
    `<strong>${title}</strong>`,
    factsTableHtml({
      total: population.total_count,
      partitions: population.partitions,
      maturity_status: maturity.status,
      performance_window_days: maturity.performance_window_days,
      cutoff_date: maturity.cutoff_date,
      eligible_count: maturity.eligible_count,
      labeled_count: maturity.labeled_count,
      reason: maturity.reason,
    }),
    "</article>",
  ].join("");
}

function sampleDesignWorkflowHtml(sample) {
  if (!isRecord(sample)) {
    return [
      '<section class="candidate-lab-subsection candidate-lab-sample-design" data-status="missing">',
      "<h5>Approval and risk samples</h5>",
      '<p class="candidate-lab-empty">Define approval and risk populations, sample splits and outcome maturity.</p>',
      "</section>",
    ].join("");
  }
  const artifactUrl = safeDownloadUrl(sample.artifact?.download_url);
  return [
    `<section class="candidate-lab-subsection candidate-lab-sample-design" data-status="${escapeHtml(sample.freshness === "stale" ? "stale" : "complete")}">`,
    "<header><h5>Approval and risk samples</h5>",
    artifactUrl
      ? `<a class="button compact secondary" href="${escapeHtml(artifactUrl)}" download>Download sample design</a>`
      : "",
    "</header>",
    factsTableHtml({
      source_mode: sample.source_mode,
      relationship: sample.relationship,
      analysis_universe_count: sample.analysis_universe_count,
      target: sample.target,
      relationship_counts: sample.relationship_counts,
      diagnostic_status: sample.diagnostics?.overall_status,
    }),
    '<div class="candidate-lab-result-list candidate-lab-dual-populations">',
    samplePopulationHtml("approval", sample.populations?.approval),
    samplePopulationHtml("risk", sample.populations?.risk),
    "</div>",
    "</section>",
  ].join("");
}

function workflowEvidenceItemHtml(label, item) {
  if (!isRecord(item)) {
    return [
      '<article class="candidate-lab-evidence-card" data-status="missing">',
      `<strong>${escapeHtml(label)}</strong>`,
      "<small>Not generated</small>",
      "</article>",
    ].join("");
  }
  const downloadUrl = safeDownloadUrl(item.artifact?.download_url);
  const freshness = item.freshness === "stale" ? "stale" : "complete";
  return [
    `<article class="candidate-lab-evidence-card" data-status="${freshness}">`,
    `<strong>${escapeHtml(label)}</strong>`,
    `<small>${freshness === "stale" ? "Based on an older pool revision; refresh required" : "Matches the current pool revision"}</small>`,
    factsTableHtml({
      strategy_type: item.strategy_type,
      pool_revision: item.pool_revision,
      partitions: item.partitions || item.comparison_partitions || item.partition,
      population_count: item.population_count,
      labeled_count: item.labeled_count,
      lifecycle: item.lifecycle,
    }),
    downloadUrl
      ? `<a class="button compact secondary" href="${escapeHtml(downloadUrl)}" download>Download evidence</a>`
      : "",
    "</article>",
  ].join("");
}

function workflowEvidenceHtml(latestEvidence) {
  const evidence = isRecord(latestEvidence) ? latestEvidence : {};
  const validations = isRecord(evidence.pool_validation)
    ? evidence.pool_validation
    : {};
  return [
    '<section class="candidate-lab-subsection candidate-lab-workflow-evidence">',
    "<h5>Latest impact and stability results</h5>",
    '<div class="candidate-lab-result-list">',
    workflowEvidenceItemHtml("Pool stability", evidence.pool_stability),
    workflowEvidenceItemHtml("Pool impact", evidence.pool_impact),
    workflowEvidenceItemHtml("Combined impact analysis", evidence.impact_cube),
    workflowEvidenceItemHtml("Validation sample", validations.validation),
    workflowEvidenceItemHtml("Out-of-time sample (OOT)", validations.oot),
    "</div>",
    "</section>",
  ].join("");
}

function workflowReportHtml(report) {
  if (!isRecord(report)) {
    return [
      '<section class="candidate-lab-subsection candidate-lab-workflow-report" data-status="missing">',
      "<h5>Strategy review report</h5>",
      '<p class="candidate-lab-empty">No report has been generated. Add the required information before generating one.</p>',
      "</section>",
    ].join("");
  }
  const artifacts = isRecord(report.artifacts) ? report.artifacts : {};
  const labels = {
    json: "JSON",
    markdown: "Markdown",
    xlsx: "Excel",
    docx: "Word",
  };
  const links = Object.entries(labels).map(([format, label]) => {
    const url = safeDownloadUrl(artifacts[format]?.download_url);
    return url
      ? `<a class="button compact secondary" href="${escapeHtml(url)}" download>${label}</a>`
      : `<span class="strategy-artifact-unavailable">${label} unavailable</span>`;
  }).join("");
  return [
    `<section class="candidate-lab-subsection candidate-lab-workflow-report" data-status="${escapeHtml(report.freshness === "stale" ? "stale" : "complete")}">`,
    "<h5>Strategy review report</h5>",
    factsTableHtml({
      report_id: report.report_id,
      revision: report.revision,
      status: report.status,
      title: report.title,
      created_at: report.created_at,
    }),
    `<div class="candidate-lab-form-actions">${links}</div>`,
    "</section>",
  ].join("");
}

function strategyWorkflowSpineHtml(workflow) {
  const value = isRecord(workflow) ? workflow : {};
  const hasProgress = value.stages?.some((stage) => stage.status === "complete");
  return [
    '<section class="candidate-lab-result-group candidate-lab-workflow-spine">',
    '<header class="candidate-lab-result-head">',
    "<div><h4>Strategy development</h4></div>",
    "</header>",
    workflowStageSpineHtml(value.stages),
    `<details${hasProgress ? " open" : ""}><summary>Stage details and results</summary>`,
    projectContextWorkflowHtml(value.project_context),
    sampleDesignWorkflowHtml(value.sample_design),
    workflowEvidenceHtml(value.latest_evidence),
    workflowReportHtml(value.report),
    "</details>",
    "</section>",
  ].join("");
}

const STRATEGY_ASSET_STATUS_LABELS = Object.freeze({
  draft: "draft",
  validated: "Authenticated",
  adopted_local: "Adopted locally",
});

function strategyMaterializationHtml(materialization) {
  if (!isRecord(materialization)) {
    return [
      '<section class="candidate-lab-subsection">',
      "<h5>Saved strategy and execution requirements</h5>",
      '<p class="candidate-lab-empty">No saved strategy version is available.</p>',
      "</section>",
    ].join("");
  }
  const blockers = Array.isArray(materialization.runtime_blockers)
    ? materialization.runtime_blockers
    : [];
  return [
    '<section class="candidate-lab-subsection">',
    "<h5>Saved strategy and execution requirements</h5>",
    factsTableHtml({
      materialization_id: materialization.materialization_id,
      pool_id: materialization.pool_id,
      pool_revision_id: materialization.pool_revision_id,
      pool_revision: materialization.pool_revision,
      requirements_count: materialization.requirements_count,
    }),
    blockers.length
      ? [
        '<div class="candidate-lab-risk-group" data-tone="warn">',
        "<strong>Execution blockers</strong>",
        "<ul>",
        ...blockers.slice(0, 24).map(
          (blocker) => `<li>${escapeHtml(readableValue(blocker))}</li>`,
        ),
        "</ul>",
        blockers.length > 24
          ? "<p>Additional execution blockers are omitted.</p>"
          : "",
        "</div>",
      ].join("")
      : '<p class="candidate-lab-boundary-note">No execution blockers were reported.</p>',
    "</section>",
  ].join("");
}

function strategyArtifactsHtml(artifacts) {
  const value = isRecord(artifacts) ? artifacts : {};
  const items = Array.isArray(value.all) ? value.all.filter(isRecord) : [];
  if (!items.length) {
    return [
      '<section class="candidate-lab-subsection">',
      "<h5>Strategy artifacts</h5>",
      '<p class="candidate-lab-empty">No verified downloads are available for this version.</p>',
      "</section>",
    ].join("");
  }
  return [
    '<section class="candidate-lab-subsection">',
    "<h5>Strategy artifacts</h5>",
    '<div class="candidate-lab-form-actions">',
    ...items.slice(0, 40).map((artifact) => {
      const filename = nonEmptyText(artifact.filename)
        || nonEmptyText(artifact.kind)
        || "Strategy artifacts";
      const url = safeDownloadUrl(artifact.download_url);
      return url
        ? `<a class="button compact secondary" href="${escapeHtml(url)}" download>Download ${escapeHtml(filename)}</a>`
        : `<span class="strategy-artifact-unavailable">${escapeHtml(filename)} unavailable</span>`;
    }),
    "</div>",
    value.truncated === true
      ? '<p class="candidate-lab-truncated">Additional artifacts are omitted.</p>'
      : "",
    "</section>",
  ].join("");
}

function strategyHistoryItemHtml(strategy, championIds) {
  const strategyId = nonEmptyText(strategy?.strategy_id) || "Strategy version";
  const strategyType = nonEmptyText(strategy?.strategy_type);
  const assetStatus = nonEmptyText(strategy?.asset_status);
  const isChampion = championIds.has(strategyId);
  return [
    '<details class="candidate-lab-evidence-card candidate-lab-strategy-history-card">',
    "<summary>",
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(strategyId)}</strong>`,
    `<small>${escapeHtml(STRATEGY_TYPE_LABELS[strategyType] || strategyType || "Strategy")} · v${escapeHtml(stablePrimitiveText(strategy?.version))} · ${escapeHtml(STRATEGY_ASSET_STATUS_LABELS[assetStatus] || assetStatus || nonEmptyText(strategy?.status) || "-")}</small>`,
    "</span>",
    isChampion
      ? '<span class="candidate-lab-card-state">Current local strategy</span>'
      : '<span class="candidate-lab-card-state">View version</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    factsTableHtml({
      status: strategy?.status,
      asset_status: STRATEGY_ASSET_STATUS_LABELS[assetStatus] || assetStatus,
      created_at: strategy?.created_at,
      adopted_at: strategy?.adopted_at,
      parent_strategy_id: strategy?.parent_strategy_id,
      rule_count: strategy?.rule_count,
    }),
    strategyMaterializationHtml(strategy?.materialization),
    strategyArtifactsHtml(strategy?.artifacts),
    "</div>",
    "</details>",
  ].join("");
}

function strategyHistoryHtml(collection) {
  const value = isRecord(collection) ? collection : {};
  const strategies = projectedStrategyItems({ strategies: value });
  const champions = Array.isArray(value.current_local_champions)
    ? value.current_local_champions.filter(isRecord)
    : [];
  const championIds = new Set(
    champions.map((champion) => nonEmptyText(champion.strategy_id)).filter(Boolean),
  );
  const championSummary = champions.length
    ? [
      '<div class="candidate-lab-boundary-note" data-tone="info">',
      "<strong>Current local strategy</strong>",
      `<p>${champions.slice(0, 5).map((champion) => {
        const type = nonEmptyText(champion.strategy_type);
        return `${escapeHtml(STRATEGY_TYPE_LABELS[type] || type)}:${escapeHtml(nonEmptyText(champion.strategy_id))}(v${escapeHtml(stablePrimitiveText(champion.version))})`;
      }).join(";")}</p>`,
      "</div>",
    ].join("")
    : '<p class="candidate-lab-empty">No strategy has been adopted for this task.</p>';
  return [
    '<section class="candidate-lab-result-group candidate-lab-strategy-history">',
    '<header class="candidate-lab-result-head">',
    "<div><h4>Strategy version history</h4><p>Saved versions, execution requirements and verified artifacts for this task.</p></div>",
    "</header>",
    championSummary,
    '<p class="candidate-lab-boundary-note">Local adoption requires validation results and explicit confirmation.</p>',
    strategies.length
      ? `<div class="candidate-lab-result-list">${strategies.map(
        (strategy) => strategyHistoryItemHtml(strategy, championIds),
      ).join("")}</div>`
      : '<p class="candidate-lab-empty">Create a draft strategy from a pool to start the version history.</p>',
    value.truncated === true
      ? `<p class="candidate-lab-truncated">Showing ${escapeHtml(strategies.length)} / ${escapeHtml(stablePrimitiveText(value.total))} versions. Older versions are omitted.</p>`
      : "",
    "</section>",
  ].join("");
}

function evidenceDrawerArtifactHtml(artifact) {
  const value = isRecord(artifact) ? artifact : {};
  const inputStatus = nonEmptyText(value.input_binding_status);
  const datasets = Array.isArray(value.datasets)
    ? value.datasets.filter(isRecord)
    : [];
  const explicitInputs = Array.isArray(value.explicit_input_hashes)
    ? value.explicit_input_hashes.filter(isRecord)
    : [];
  const downloadUrl = safeDownloadUrl(value.download_url);
  return [
    '<details class="candidate-lab-evidence-card candidate-lab-drawer-artifact">',
    "<summary>",
    '<span class="candidate-lab-card-title">',
    `<strong>${escapeHtml(nonEmptyText(value.kind) || nonEmptyText(value.artifact_id) || "Verified artifacts")}</strong>`,
    `<small>${escapeHtml(nonEmptyText(value.origin_tool) || "Unknown tool")} · ${escapeHtml(nonEmptyText(value.producer_version) || nonEmptyText(value.artifact_schema_version) || "Version unavailable")}</small>`,
    "</span>",
    '<span class="candidate-lab-card-state">View sources</span>',
    "</summary>",
    '<div class="candidate-lab-card-body">',
    factsTableHtml({
      artifact_id: value.artifact_id,
      artifact_schema_version: value.artifact_schema_version,
      producer_version: value.producer_version,
      origin_tool: value.origin_tool,
      created_at: value.created_at,
      content_hash: value.content_hash,
      provenance_hash: value.provenance_hash,
      input_binding_hash: value.input_binding_hash,
      input_binding_status: inputStatus === "explicit"
        ? "Recorded by the tool"
        : "Derived from full provenance; original input hash unavailable",
    }),
    datasets.length
      ? [
        '<section class="candidate-lab-subsection">',
        "<h5>Dataset binding</h5>",
        '<div class="candidate-lab-table-scroll">',
        '<table class="candidate-lab-table"><thead><tr><th>Role</th><th>Dataset ID</th><th>Content hash</th></tr></thead><tbody>',
        ...datasets.map((dataset) => [
          "<tr>",
          `<td>${escapeHtml(nonEmptyText(dataset.role) || "-")}</td>`,
          `<td><code>${escapeHtml(nonEmptyText(dataset.dataset_id) || "-")}</code></td>`,
          `<td><code>${escapeHtml(nonEmptyText(dataset.content_hash) || "Not recorded")}</code></td>`,
          "</tr>",
        ].join("")),
        "</tbody></table>",
        "</div>",
        "</section>",
      ].join("")
      : '<p class="candidate-lab-boundary-note">Dataset references are not recorded for this artifact.</p>',
    explicitInputs.length
      ? [
        '<section class="candidate-lab-subsection">',
        "<h5>Recorded input hashes</h5>",
        '<div class="candidate-lab-table-scroll">',
        '<table class="candidate-lab-table"><thead><tr><th>Fields</th><th>Hash</th></tr></thead><tbody>',
        ...explicitInputs.map((input) => [
          "<tr>",
          `<td>${escapeHtml(nonEmptyText(input.field) || "-")}</td>`,
          `<td><code>${escapeHtml(nonEmptyText(input.hash) || "-")}</code></td>`,
          "</tr>",
        ].join("")),
        "</tbody></table>",
        "</div>",
        "</section>",
      ].join("")
      : "",
    downloadUrl
      ? `<a class="button compact secondary candidate-lab-download" href="${escapeHtml(downloadUrl)}" download>Download verified artifact</a>`
      : "",
    "</div>",
    "</details>",
  ].join("");
}

function evidenceDrawerDatasetsHtml(collection) {
  const value = isRecord(collection) ? collection : {};
  const items = Array.isArray(value.all) ? value.all.filter(isRecord) : [];
  if (!items.length) {
    return '<p class="candidate-lab-empty">No dataset references are available.</p>';
  }
  return [
    '<div class="candidate-lab-table-scroll">',
    '<table class="candidate-lab-table"><thead><tr><th>Dataset ID</th><th>Content hash</th><th>Related artifacts</th></tr></thead><tbody>',
    ...items.map((dataset) => [
      "<tr>",
      `<td><code>${escapeHtml(nonEmptyText(dataset.dataset_id) || "-")}</code></td>`,
      `<td><code>${escapeHtml(nonEmptyText(dataset.content_hash) || "Not recorded")}</code></td>`,
      `<td>${escapeHtml(stablePrimitiveText(Array.isArray(dataset.artifact_ids) ? dataset.artifact_ids.length : 0))}</td>`,
      "</tr>",
    ].join("")),
    "</tbody></table>",
    "</div>",
    value.truncated === true
      ? '<p class="candidate-lab-truncated">Additional dataset references are omitted.</p>'
      : "",
  ].join("");
}

function evidenceDrawerRedFlagsHtml(collection) {
  const value = isRecord(collection) ? collection : {};
  const items = Array.isArray(value.all) ? value.all.filter(isRecord) : [];
  if (!items.length) {
    return '<p class="candidate-lab-empty">No risk flags were reported.</p>';
  }
  return [
    '<div class="candidate-lab-risk-group" data-tone="warn">',
    "<strong>Risk flags</strong>",
    "<ul>",
    ...items.map((flag) => (
      `<li><code>${escapeHtml(nonEmptyText(flag.code) || "risk")}</code> ${escapeHtml(nonEmptyText(flag.message) || "-")}</li>`
    )),
    "</ul>",
    "</div>",
    value.truncated === true
      ? '<p class="candidate-lab-truncated">Additional risk flags are omitted.</p>'
      : "",
  ].join("");
}

function evidenceDrawerMemoryHtml(collection) {
  const value = isRecord(collection) ? collection : {};
  const items = Array.isArray(value.all) ? value.all.filter(isRecord) : [];
  if (!items.length) {
    return '<p class="candidate-lab-empty">The latest response has no saved-context references.</p>';
  }
  return [
    '<div class="candidate-lab-result-list">',
    ...items.map((reference) => [
      '<article class="candidate-lab-evidence-card candidate-lab-memory-reference">',
      '<div class="candidate-lab-card-body">',
      factsTableHtml({
        memory_id: reference.id,
        kind: reference.kind,
        memory_type: reference.memory_type,
        source_task_id: reference.source_task_id,
        confidence: reference.confidence,
        use_reason: reference.use_reason,
        support_count: reference.support_count,
        source_memory_count: reference.source_memory_count,
      }),
      "</div>",
      "</article>",
    ].join("")),
    "</div>",
    value.truncated === true
      ? '<p class="candidate-lab-truncated">Additional saved-context references are omitted.</p>'
      : "",
    Number(value.omitted || 0) > 0
      ? `<p class="candidate-lab-truncated">${escapeHtml(stablePrimitiveText(value.omitted))} invalid entries were omitted.</p>`
      : "",
  ].join("");
}

function strategyEvidenceDrawerHtml(drawer) {
  const value = isRecord(drawer) ? drawer : {};
  const artifacts = isRecord(value.artifacts) ? value.artifacts : {};
  const artifactItems = Array.isArray(artifacts.all)
    ? artifacts.all.filter(isRecord)
    : [];
  const hasRedFlags = Boolean(value.red_flags?.all?.length);
  return [
    `<details class="candidate-lab-result-group candidate-lab-evidence-drawer"${artifactItems.length || hasRedFlags ? " open" : ""}><summary>Sources and artifacts · ${artifactItems.length}${hasRedFlags ? " · Risk flags" : ""}</summary>`,
    '<header class="candidate-lab-result-head">',
    "<div><h4>Sources and artifacts</h4><p>Data sources, artifacts, tool versions, risk flags and saved context.</p></div>",
    "</header>",
    '<p class="candidate-lab-boundary-note">Verified sources for the current task. Input hashes link artifacts to the data used.</p>',
    '<details class="candidate-lab-evidence-card" open>',
    `<summary><span class="candidate-lab-card-title"><strong>Verified artifacts</strong><small>${escapeHtml(stablePrimitiveText(artifacts.total || 0))} artifacts for this task</small></span><span class="candidate-lab-card-state">View artifacts</span></summary>`,
    '<div class="candidate-lab-card-body">',
    artifactItems.length
      ? `<div class="candidate-lab-result-list">${artifactItems.map(
        (artifact) => evidenceDrawerArtifactHtml(artifact),
      ).join("")}</div>`
      : '<p class="candidate-lab-empty">No verified artifacts are available.</p>',
    artifacts.truncated === true
      ? '<p class="candidate-lab-truncated">Additional artifacts are omitted.</p>'
      : "",
    "</div>",
    "</details>",
    `<details class="candidate-lab-evidence-card"${hasRedFlags ? " open" : ""}>`,
    "<summary><span class=\"candidate-lab-card-title\"><strong>Datasets and risk flags</strong><small>Dataset lineage across artifacts</small></span><span class=\"candidate-lab-card-state\">View</span></summary>",
    '<div class="candidate-lab-card-body">',
    evidenceDrawerDatasetsHtml(value.datasets),
    evidenceDrawerRedFlagsHtml(value.red_flags),
    "</div>",
    "</details>",
    '<details class="candidate-lab-evidence-card">',
    "<summary><span class=\"candidate-lab-card-title\"><strong>Saved-context references</strong><small>References cited by the latest response</small></span><span class=\"candidate-lab-card-state\">View</span></summary>",
    `<div class="candidate-lab-card-body">${evidenceDrawerMemoryHtml(value.memory_references)}</div>`,
    "</details>",
    "</details>",
  ].join("");
}

export function strategyCandidateLabResultsHtml(payload = {}) {
  const candidates = isRecord(payload.candidates) ? payload.candidates : {};
  const populated = COLLECTION_DEFINITIONS.filter((definition) => collectionItems(candidates[definition.key]).length);
  const empty = COLLECTION_DEFINITIONS.filter((definition) => !collectionItems(candidates[definition.key]).length);
  return [
    strategyWorkflowSpineHtml(payload.workflow),
    strategyEvidenceDrawerHtml(payload.evidence_drawer),
    projectedStrategyItems({ strategies: payload.strategies }).length ? strategyHistoryHtml(payload.strategies)
      : `<details class="candidate-lab-empty-results"><summary>Strategy history · no saved versions</summary>${strategyHistoryHtml(payload.strategies)}</details>`,
    ...populated.map(
      (definition) => candidateCollectionHtml(candidates, definition),
    ),
    empty.length ? `<details class="candidate-lab-empty-results"><summary>Analysis not yet run · ${empty.length} categories</summary>${empty.map((definition) => candidateCollectionHtml(candidates, definition)).join("")}</details>` : "",
    collectionItems(payload.pools).length ? poolCollectionHtml(payload.pools)
      : `<details class="candidate-lab-empty-results"><summary>Strategy pools · no rules</summary>${poolCollectionHtml(payload.pools)}</details>`,
  ].join("");
}
