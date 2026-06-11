/** Shared Candidate Lab identities and pure contract helpers. */

export const STRATEGY_CANDIDATE_LAB_WORKFLOWS = Object.freeze([
  "strategy_project_context",
  "strategy_sample_design_v2",
  "univariate_candidate_analysis",
  "univariate_candidate_refinement",
  "cross_matrix_analysis",
  "cross_matrix_candidate_search",
  "cross_matrix_candidate_build_from_search",
  "cross_rule_search",
  "cross_rule_candidate_build_from_search",
  "automatic_tree_candidate_build",
  "scorecard_model_score_evidence_build",
  "scorecard_band_build",
  "scorecard_cutoff_selection",
  "candidate_monthly_stability",
  "strategy_pool_add_candidate",
  "strategy_pool_compile",
  "strategy_pool_remove_entry",
  "strategy_pool_set_action",
  "strategy_pool_reorder",
  "strategy_pool_apply",
  "strategy_pool_validation",
  "strategy_pool_stability",
  "strategy_pool_impact",
  "strategy_impact_cube",
  "strategy_pool_materialize",
  "strategy_lifecycle_adopt",
  "strategy_dsl_delivery",
  "strategy_report_bundle_v2",
  "voting_candidate_search",
  "voting_candidate_build_from_search",
  "interactive_tree_split_search",
  "interactive_tree_auto_continuation",
  "interactive_tree_revision",
  "interactive_tree_frontier_group_materialization",
  "interactive_tree_frontier_materialization",
]);

export const VOTING_SEARCH_METRICS = Object.freeze([
  "hit_count",
  "hit_share",
  "good_count",
  "bad_count",
  "bad_rate",
  "lift",
  "bad_capture_rate",
  "weighted_hit_total",
  "weighted_hit_share",
  "weighted_good_total",
  "weighted_bad_total",
  "weighted_bad_rate",
  "weighted_bad_capture_rate",
  "hit_amount",
  "hit_amount_share",
  "good_amount",
  "bad_amount",
  "bad_amount_rate",
  "bad_amount_capture_rate",
]);

export const VOTING_RULE_ID_RE = /^candidate-rule-[0-9a-f]{32}$/;

export const VOTING_SEARCH_ID_RE = /^voting-search-[0-9a-f]{32}$/;

export const VOTING_COMBO_ID_RE = /^voting-combo-[0-9a-f]{32}$/;

export const CROSS_SEARCH_ID_RE = /^cross-search-[0-9a-f]{32}$/;

export const CROSS_PAIR_ID_RE = /^cross-pair-[0-9a-f]{32}$/;

export const CROSS_RULE_SEARCH_ID_RE = /^cross-rule-search-[0-9a-f]{32}$/;

export const CROSS_RULE_ID_RE = /^cross-rule-[0-9a-f]{32}$/;

export const INTERACTIVE_TREE_SOURCE_ID_RE = /^(?:candidate-asset-[0-9a-f]{32}|interactive-tree-revision-[0-9a-f]{32})$/;

export const INTERACTIVE_TREE_NODE_ID_RE = /^node-[0-9a-f]{20}$/;

export const INTERACTIVE_TREE_REVISION_ID_RE = /^interactive-tree-revision-[0-9a-f]{32}$/;

export const INTERACTIVE_TREE_FRONTIER_SOURCE_NODE_ID_RE = /^(?:node|leaf)-[0-9a-f]{20}$/;

export const INTERACTIVE_TREE_SPLIT_SEARCH_ID_RE = /^interactive-tree-split-search-[0-9a-f]{32}$/;

export const INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_RE = /^interactive-tree-split-candidate-[0-9a-f]{32}$/;

export const STRATEGY_POOL_TYPES = Object.freeze([
  "approval",
  "reject",
  "limit",
  "pricing",
  "segmentation",
]);

export const STRATEGY_POOL_ACTION_TYPES = Object.freeze({
  approval: Object.freeze(["approval", "reject", "review"]),
  reject: Object.freeze(["approval", "reject", "review"]),
  limit: Object.freeze(["limit"]),
  pricing: Object.freeze(["pricing"]),
  segmentation: Object.freeze(["segment"]),
});

export const STRATEGY_POOL_OPERATION_WORKFLOWS = Object.freeze([
  "strategy_pool_compile",
  "strategy_pool_remove_entry",
  "strategy_pool_set_action",
  "strategy_pool_reorder",
]);

export const STRATEGY_POOL_ENTRY_ID_RE = /^pool-entry-[0-9a-f]{32}$/;

export const STRATEGY_ID_RE = /^(?:strategy-[A-Za-z0-9][A-Za-z0-9_-]*|[0-9a-f]{32})$/;

export const PROJECT_CONTEXT_FIELD_PATH_RE = /^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){0,7}$/;

export const PROJECT_CONTEXT_PLATFORM_FIELD_RE = /(?:^|\.)(?:artifact_id|content_hash|dataset_id|revision|revision_id|strategy_id|target_col)$/;

export const STRATEGY_POOL_APPLY_PREFIX_RE = /^[A-Za-z_][A-Za-z0-9_]{0,47}$/;

export const STRATEGY_POOL_CANDIDATE_ASSET_ID_RE = /^candidate-asset-[0-9a-f]{32}$/;

export const STRATEGY_POOL_ADD_SELECTION_RE = /^(?:automatic-tree-leaf-selection|interactive-tree-frontier-selection|interactive-tree-frontier-group-selection|cross-matrix-cell-selection|scorecard-cutoff-selection)-[0-9a-f]{32}$/;

export const STRATEGY_POOL_ADD_SOURCE_KINDS = Object.freeze({
  univariate_asset: "candidate_asset_id",
  automatic_tree_leaf_selection: "selection_id",
  interactive_tree_frontier_selection: "selection_id",
  interactive_tree_frontier_group_selection: "selection_id",
  cross_matrix_cell_selection: "selection_id",
  scorecard_cutoff_selection: "selection_id",
  voting_candidate: "candidate_asset_id",
});

export const STRATEGY_POOL_VOTING_PLACEMENTS = Object.freeze([
  "before_selected_members",
  "replace_selected_members",
]);

export const _MAX_STRATEGY_POOL_ADD_SOURCES = 140;

export const FIELD_LABELS = Object.freeze({
  action: "Action",
  approval_rate: "Approval rate",
  asset_hash: "Asset hash",
  asset_id: "Asset ID",
  bad: "Bad outcomes",
  bad_rate: "Bad rate",
  bad_count: "Bad outcomes",
  base_odds: "Base odds",
  base_points: "Base points",
  base_score: "Base score",
  average_pd: "Average raw PD",
  artifact_id: "Artifact ID",
  artifact_schema_version: "Artifact schema version",
  bin_id: "Bin ID",
  bin_label: "Bin label",
  candidate_id: "Candidate ID",
  candidate_stage: "Candidate stage",
  cell_id: "Cell ID",
  column_bin_id: "Column bin",
  condition: "Match condition",
  confidence: "Confidence",
  content_hash: "Content hash",
  count: "Sample count",
  created_at: "Created",
  cutoff_id: "Cutoff ID",
  default_action: "Default action",
  effect: "Effect",
  effect_id: "Effect ID",
  eligible: "Eligible",
  empty_cell_count: "Empty cells",
  empty_cell_share: "Empty-cell share",
  evaluated: "Combinations evaluated",
  execution_pd: "Execution PD",
  enabled: "Enabled",
  evidence_hash: "Evidence hash",
  factor: "Factor",
  feature: "Feature",
  fragment_id: "Fragment ID",
  good: "Good outcomes",
  good_count: "Good outcomes",
  iv: "IV",
  iv_contribution: "IV Contribution",
  interaction_gain_iv: "Interaction Gain IV",
  input_binding_hash: "Input binding hash",
  input_binding_status: "Input binding status",
  ks: "KS",
  lifecycle: "Lifecycle",
  lower_bound: "Lower bound",
  lower_inclusive: "Inclusive lower bound",
  lower_risk: "Lower-risk side",
  monotonic_direction: "Monotonic direction",
  memory_id: "Memory ID",
  memory_type: "Memory category",
  node_id: "Node ID",
  lift: "Lift",
  method: "Binning method",
  max_pairs: "Maximum pairs",
  min_nonempty_cell_count: "Minimum non-empty cell count",
  observation_stage: "Observation stage",
  origin_tool: "Source tool",
  pool_id: "Pool ID",
  position: "Order",
  points: "Points",
  producer_version: "Producer version",
  provenance_hash: "Provenance hash",
  pair_id: "Pair ID",
  pdo: "PDO",
  display_points: "Scorecard points",
  revision: "Revision",
  revision_id: "Revision ID",
  risk: "Risk",
  row_bin_id: "Row bin",
  rule_id: "Rule ID",
  share: "Share",
  snapshot_hash: "Snapshot hash",
  status: "Status",
  search_id: "Search ID",
  search_space: "Search space",
  strategy_type: "Strategy type",
  source_tree_id: "Source tree",
  source_task_id: "Source task",
  source_memory_count: "Source memory count",
  support_count: "Support count",
  total: "Total",
  upper_bound: "Upper bound",
  upper_inclusive: "Inclusive upper bound",
  higher_risk: "Higher-risk side",
  coefficient: "Coefficient",
  offset: "Offset",
  tree_id: "Tree ID",
  tree_result_hash: "Tree result hash",
  x_axis_iv: "X Axis IV",
  x_feature: "X feature",
  x_method: "X binning method",
  y_axis_iv: "Y Axis IV",
  y_feature: "Y feature",
  y_method: "Y binning method",
  cross_total_iv: "Cross Total IV",
  cell_count: "Cell count",
  validation_status: "Validation status",
  value: "Value",
  use_reason: "Reason for use",
  woe: "WOE",
});

export function isRecord(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function nonEmptyText(value) {
  return typeof value === "string" ? value.trim() : "";
}

export function fieldLabel(key) {
  const normalized = String(key || "");
  return FIELD_LABELS[normalized]
    || normalized
      .split("_")
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
}

export function stablePrimitiveText(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "-";
  return String(value);
}

export function readableValue(value, depth = 0) {
  if (depth >= 3) return "…";
  if (Array.isArray(value)) {
    if (!value.length) return "-";
    const rendered = value.slice(0, 12).map((item) => readableValue(item, depth + 1));
    return rendered.join(";") + (value.length > 12 ? ";…" : "");
  }
  if (isRecord(value)) {
    const entries = Object.entries(value).slice(0, 16);
    if (!entries.length) return "-";
    const rendered = entries.map(
      ([key, item]) => `${fieldLabel(key)}:${readableValue(item, depth + 1)}`,
    );
    return rendered.join(";") + (Object.keys(value).length > 16 ? ";…" : "");
  }
  return stablePrimitiveText(value);
}

export function collectionItems(collection) {
  if (!isRecord(collection)) return [];
  const items = Array.isArray(collection.all)
    ? collection.all.filter(isRecord)
    : [];
  const latest = isRecord(collection.latest) ? collection.latest : null;
  if (!latest) return items;
  const latestArtifactId = nonEmptyText(latest.artifact?.artifact_id);
  const alreadyIncluded = items.some((item) => (
    item === latest
    || (
      latestArtifactId
      && nonEmptyText(item.artifact?.artifact_id) === latestArtifactId
    )
  ));
  return alreadyIncluded ? items : [latest, ...items];
}

export function interactiveTreeEligiblePointers(item) {
  const sourceTreeId = nonEmptyText(item?.detail?.source_tree_id);
  const nodes = new Map(
    (Array.isArray(item?.pointers?.nodes) ? item.pointers.nodes : [])
      .filter(isRecord)
      .map((node) => [nonEmptyText(node.node_id), node]),
  );
  const pointers = Array.isArray(item?.pointers?.eligible_prunes)
    ? item.pointers.eligible_prunes.filter(isRecord)
    : [];
  const seen = new Set();
  return pointers.filter((pointer) => {
    const pointerSource = nonEmptyText(pointer.source_tree_id);
    const nodeId = nonEmptyText(pointer.node_id);
    const node = nodes.get(nodeId);
    const key = `${pointerSource}\u001f${nodeId}`;
    if (
      pointerSource !== sourceTreeId
      || !INTERACTIVE_TREE_SOURCE_ID_RE.test(pointerSource)
      || !INTERACTIVE_TREE_NODE_ID_RE.test(nodeId)
      || pointer.operation !== "prune_subtree"
      || node?.kind !== "split"
      || node?.is_visible !== true
      || node?.is_frontier === true
      || node?.can_prune !== true
      || seen.has(key)
    ) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export function interactiveTreeThresholdEligiblePointers(item) {
  const sourceTreeId = nonEmptyText(item?.detail?.source_tree_id);
  const nodes = new Map(
    (Array.isArray(item?.pointers?.nodes) ? item.pointers.nodes : [])
      .filter(isRecord)
      .map((node) => [nonEmptyText(node.node_id), node]),
  );
  const pointers = Array.isArray(
    item?.pointers?.eligible_threshold_adjustments,
  )
    ? item.pointers.eligible_threshold_adjustments.filter(isRecord)
    : [];
  const seen = new Set();
  return pointers.filter((pointer) => {
    const pointerSource = nonEmptyText(pointer.source_tree_id);
    const nodeId = nonEmptyText(pointer.node_id);
    const feature = nonEmptyText(pointer.feature);
    const currentThreshold = Number(pointer.current_threshold);
    const node = nodes.get(nodeId);
    const nodeThreshold = Number(node?.threshold);
    const key = `${pointerSource}\u001f${nodeId}`;
    if (
      pointerSource !== sourceTreeId
      || !INTERACTIVE_TREE_SOURCE_ID_RE.test(pointerSource)
      || !INTERACTIVE_TREE_NODE_ID_RE.test(nodeId)
      || pointer.operation !== "adjust_split_threshold"
      || !feature
      || typeof pointer.current_threshold !== "number"
      || !Number.isFinite(currentThreshold)
      || node?.kind !== "split"
      || node?.is_visible !== true
      || node?.is_frontier === true
      || node?.can_prune !== true
      || nonEmptyText(node?.feature) !== feature
      || typeof node?.threshold !== "number"
      || !Number.isFinite(nodeThreshold)
      || nodeThreshold !== currentThreshold
      || seen.has(key)
    ) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export function interactiveTreeFeatureEligiblePointers(item) {
  const sourceTreeId = nonEmptyText(item?.detail?.source_tree_id);
  const featureUniverse = new Set(
    (Array.isArray(item?.pointers?.feature_universe)
      ? item.pointers.feature_universe
      : [])
      .map(nonEmptyText)
      .filter(Boolean),
  );
  const nodes = new Map(
    (Array.isArray(item?.pointers?.nodes) ? item.pointers.nodes : [])
      .filter(isRecord)
      .map((node) => [nonEmptyText(node.node_id), node]),
  );
  const pointers = Array.isArray(
    item?.pointers?.eligible_feature_replacements,
  )
    ? item.pointers.eligible_feature_replacements.filter(isRecord)
    : [];
  const seen = new Set();
  return pointers.filter((pointer) => {
    const pointerSource = nonEmptyText(pointer.source_tree_id);
    const nodeId = nonEmptyText(pointer.node_id);
    const currentFeature = nonEmptyText(pointer.current_feature);
    const currentThreshold = Number(pointer.current_threshold);
    const node = nodes.get(nodeId);
    const key = `${pointerSource}\u001f${nodeId}`;
    if (
      pointerSource !== sourceTreeId
      || !INTERACTIVE_TREE_SOURCE_ID_RE.test(pointerSource)
      || !INTERACTIVE_TREE_NODE_ID_RE.test(nodeId)
      || pointer.operation !== "replace_split_feature"
      || !featureUniverse.has(currentFeature)
      || featureUniverse.size < 2
      || typeof pointer.current_threshold !== "number"
      || !Number.isFinite(currentThreshold)
      || node?.kind !== "split"
      || node?.is_visible !== true
      || node?.is_frontier === true
      || node?.can_prune !== true
      || nonEmptyText(node?.feature) !== currentFeature
      || Number(node?.threshold) !== currentThreshold
      || seen.has(key)
    ) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export function interactiveTreeFrontierEligiblePointers(item) {
  if (item?.kind !== "interactive_tree_revision") return [];
  const revisionId = nonEmptyText(item?.detail?.revision_id);
  if (!INTERACTIVE_TREE_REVISION_ID_RE.test(revisionId)) return [];
  const nodes = new Map(
    (Array.isArray(item?.pointers?.nodes) ? item.pointers.nodes : [])
      .filter(isRecord)
      .map((node) => [nonEmptyText(node.node_id), node]),
  );
  const frontierIds = new Set(
    (Array.isArray(item?.pointers?.frontier_node_ids)
      ? item.pointers.frontier_node_ids
      : [])
      .map(nonEmptyText)
      .filter((nodeId) => (
        INTERACTIVE_TREE_FRONTIER_SOURCE_NODE_ID_RE.test(nodeId)
      )),
  );
  const pointers = Array.isArray(item?.pointers?.frontier)
    ? item.pointers.frontier.filter(isRecord)
    : [];
  const seen = new Set();
  return pointers.filter((pointer) => {
    const sourceNodeId = nonEmptyText(pointer.source_node_id);
    const node = nodes.get(sourceNodeId);
    if (
      !INTERACTIVE_TREE_FRONTIER_SOURCE_NODE_ID_RE.test(sourceNodeId)
      || !frontierIds.has(sourceNodeId)
      || node?.is_visible !== true
      || node?.is_frontier !== true
      || seen.has(sourceNodeId)
    ) {
      return false;
    }
    seen.add(sourceNodeId);
    return true;
  });
}

export const STRATEGY_TYPE_LABELS = Object.freeze({
  approval: "Approval strategy",
  reject: "Rejection strategy",
  limit: "Limit strategy",
  pricing: "Pricing strategy",
  segmentation: "Segmentation strategy",
});

export function formField(form, name) {
  return form?.querySelector?.(`[data-candidate-lab-field="${name}"]`) || null;
}

export function formValue(form, name) {
  return String(formField(form, name)?.value ?? "").trim();
}

export function minimalProjectedPoolAction(value, strategyType) {
  if (!isRecord(value)) return null;
  const actionType = nonEmptyText(value.type);
  if (!(STRATEGY_POOL_ACTION_TYPES[strategyType] || []).includes(actionType)) {
    return null;
  }
  if (["approval", "reject", "review"].includes(actionType)) {
    return { type: actionType };
  }
  const actionValue = value.value;
  if (actionType === "segment") {
    if (
      !["string", "number"].includes(typeof actionValue)
      || (typeof actionValue === "string" && !actionValue.trim())
      || (typeof actionValue === "number" && !Number.isFinite(actionValue))
    ) {
      return null;
    }
    return { type: actionType, value: actionValue };
  }
  if (
    typeof actionValue !== "number"
    || !Number.isFinite(actionValue)
    || (actionType === "limit" && actionValue < 0)
    || (
      actionType === "pricing"
      && (actionValue < 0 || actionValue > 1)
    )
  ) {
    return null;
  }
  return { type: actionType, value: actionValue };
}

export function projectedStrategyItems(payload) {
  const collection = isRecord(payload?.strategies) ? payload.strategies : {};
  const items = Array.isArray(collection.all)
    ? collection.all.filter(isRecord)
    : [];
  const seen = new Set();
  const unique = [];
  for (const strategy of items) {
    const strategyId = nonEmptyText(strategy.strategy_id);
    if (!strategyId || seen.has(strategyId)) continue;
    seen.add(strategyId);
    unique.push(strategy);
  }
  const latest = isRecord(collection.latest) ? collection.latest : null;
  const latestId = nonEmptyText(latest?.strategy_id);
  if (latestId && !seen.has(latestId)) unique.unshift(latest);
  return unique;
}
