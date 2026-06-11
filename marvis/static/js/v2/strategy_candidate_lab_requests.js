/** Candidate Lab form collection and typed request validation. */

import {
  CROSS_PAIR_ID_RE,
  CROSS_RULE_ID_RE,
  CROSS_RULE_SEARCH_ID_RE,
  CROSS_SEARCH_ID_RE,
  INTERACTIVE_TREE_FRONTIER_SOURCE_NODE_ID_RE,
  INTERACTIVE_TREE_NODE_ID_RE,
  INTERACTIVE_TREE_REVISION_ID_RE,
  INTERACTIVE_TREE_SOURCE_ID_RE,
  INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_RE,
  INTERACTIVE_TREE_SPLIT_SEARCH_ID_RE,
  PROJECT_CONTEXT_FIELD_PATH_RE,
  PROJECT_CONTEXT_PLATFORM_FIELD_RE,
  STRATEGY_CANDIDATE_LAB_WORKFLOWS,
  STRATEGY_ID_RE,
  STRATEGY_POOL_ACTION_TYPES,
  STRATEGY_POOL_ADD_SELECTION_RE,
  STRATEGY_POOL_ADD_SOURCE_KINDS,
  STRATEGY_POOL_APPLY_PREFIX_RE,
  STRATEGY_POOL_CANDIDATE_ASSET_ID_RE,
  STRATEGY_POOL_ENTRY_ID_RE,
  STRATEGY_POOL_TYPES,
  STRATEGY_POOL_VOTING_PLACEMENTS,
  VOTING_COMBO_ID_RE,
  VOTING_RULE_ID_RE,
  VOTING_SEARCH_ID_RE,
  VOTING_SEARCH_METRICS,
  fieldLabel,
  formField,
  formValue,
  minimalProjectedPoolAction,
  nonEmptyText,
} from "./strategy_candidate_lab_contracts.js";

export { STRATEGY_CANDIDATE_LAB_WORKFLOWS };

function splitValues(value) {
  return String(value || "")
    .split(/[\s,,,;;]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function splitContextList(value) {
  return String(value || "")
    .split(/[\n,,;;]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseProjectBusinessContext(value) {
  const lines = String(value || "")
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (lines.length > 50) {
    throw new Error("Project information supports up to 50 fields.");
  }
  const context = {};
  for (const line of lines) {
    const separator = line.indexOf("=");
    if (separator <= 0 || separator === line.length - 1) {
      throw new Error("Enter one field.path=value item per line.");
    }
    const fieldPath = line.slice(0, separator).trim();
    const fieldValue = line.slice(separator + 1).trim();
    if (
      !PROJECT_CONTEXT_FIELD_PATH_RE.test(fieldPath)
      || PROJECT_CONTEXT_PLATFORM_FIELD_RE.test(fieldPath)
    ) {
      throw new Error(`Unsupported project field: ${fieldPath || "-"}.`);
    }
    if (Object.hasOwn(context, fieldPath)) {
      throw new Error(`Duplicate project field: ${fieldPath}.`);
    }
    if (!fieldValue || fieldValue.length > 4000) {
      throw new Error(`${fieldPath} must contain 1–4,000 characters.`);
    }
    context[fieldPath] = fieldValue;
  }
  return context;
}

function collectStrategyProjectContextInputs(form) {
  const asOf = formValue(form, "project_context_as_of");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(asOf)) {
    throw new Error("Enter the project as-of date in YYYY-MM-DD format.");
  }
  const inputs = {
    as_of: asOf,
    business_context: parseProjectBusinessContext(
      formValue(form, "project_context_business_context"),
    ),
    explicit_unavailable: checkedValues(form, "project_context_unavailable"),
    external_report_filenames: splitContextList(
      formValue(form, "project_context_external_reports"),
    ),
  };
  const scope = formValue(form, "project_context_scope");
  if (scope) inputs.scope = scope;
  if (inputs.external_report_filenames.length > 20) {
    throw new Error("Enter at most 20 historical filenames.");
  }
  if (
    inputs.external_report_filenames.some(
      (name) => !name || name.includes("/") || name.includes("\\") || name.includes("\0"),
    )
  ) {
    throw new Error("Choose historical files from the task material directory.");
  }
  if (
    inputs.explicit_unavailable.some(
      (fieldPath) => !PROJECT_CONTEXT_FIELD_PATH_RE.test(fieldPath),
    )
  ) {
    throw new Error("Invalid missing-information field path.");
  }
  return inputs;
}

function collectStrategyPoolMaterializeInputs(form) {
  const select = formField(form, "pool_materialize_strategy_type");
  const strategyType = nonEmptyText(select?.value);
  const option = select?.selectedOptions?.[0];
  if (
    !STRATEGY_POOL_TYPES.includes(strategyType)
    || option?.dataset?.candidateLabProjection !== "1"
    || nonEmptyText(option?.dataset?.poolId) === ""
  ) {
    throw new Error("Select a verified, non-empty strategy pool.");
  }
  return { strategy_type: strategyType };
}

function collectStrategyDslDeliveryInputs(form) {
  const select = formField(form, "dsl_delivery_strategy_id");
  const strategyId = nonEmptyText(select?.value);
  const option = select?.selectedOptions?.[0];
  if (
    !STRATEGY_ID_RE.test(strategyId)
    || option?.dataset?.candidateLabProjection !== "1"
    || nonEmptyText(option?.dataset?.strategyId) !== strategyId
  ) {
    throw new Error("Select a verified strategy version for this task.");
  }
  return { strategy_id: strategyId };
}

const STRATEGY_ADOPTION_ECONOMICS_COMPONENTS = Object.freeze({
  limit: Object.freeze(["pd", "lgd", "utilization"]),
  pricing: Object.freeze([
    "ead",
    "pd",
    "lgd",
    "funding_rate",
    "term_months",
    "operating_cost_per_loan",
  ]),
});

function collectStrategyLifecycleAdoptionRequest(form) {
  const option = selectedProjectionOption(
    form,
    "lifecycle_adopt_strategy_id",
    "Draft strategy",
  );
  const strategyId = nonEmptyText(option.value);
  const strategyType = nonEmptyText(option.dataset?.strategyType);
  if (
    !STRATEGY_ID_RE.test(strategyId)
    || nonEmptyText(option.dataset?.strategyId) !== strategyId
    || !STRATEGY_POOL_TYPES.includes(strategyType)
    || nonEmptyText(option.dataset?.assetStatus) !== "draft"
  ) {
    throw new Error("Select a verified draft strategy.");
  }
  const adoptionReason = formValue(form, "lifecycle_adoption_reason");
  if (adoptionReason.length < 2 || adoptionReason.length > 1000) {
    throw new Error("The adoption reason must contain 2–1,000 characters.");
  }
  const request = {
    request_kind: "strategy_lifecycle",
    operation: "adopt",
    strategy_type: strategyType,
    strategy_id: strategyId,
    adoption_reason: adoptionReason,
  };
  const components = STRATEGY_ADOPTION_ECONOMICS_COMPONENTS[strategyType];
  if (!components) return request;

  const economicsInputs = {};
  for (const component of components) {
    const mode = formValue(form, `lifecycle_adopt_${component}_mode`);
    if (mode === "column") {
      const column = formValue(
        form,
        `lifecycle_adopt_${component}_column`,
      );
      if (!column || column.length > 200) {
        throw new Error(`${fieldLabel(component)} requires a data column.`);
      }
      economicsInputs[`${component}_col`] = column;
      continue;
    }
    if (mode !== "value") {
      throw new Error(`${fieldLabel(component)}: choose a data column or fixed value.`);
    }
    const rawValue = formValue(form, `lifecycle_adopt_${component}_value`);
    const value = Number(rawValue);
    if (
      !rawValue
      || !Number.isFinite(value)
      || value < 0
      || (component === "term_months" && value <= 0)
      || (
        ["pd", "lgd", "utilization", "funding_rate"].includes(component)
        && value > 1
      )
    ) {
      throw new Error(`${fieldLabel(component)} is outside the permitted range.`);
    }
    economicsInputs[`${component}_value`] = value;
  }
  request.economics_inputs = economicsInputs;
  return request;
}

function uniqueValues(values, label) {
  if (new Set(values).size !== values.length) {
    throw new Error(`${label} cannot contain duplicates.`);
  }
  return values;
}

function optionalNumber(form, name, { integer = false } = {}) {
  const raw = formValue(form, name);
  if (!raw) return undefined;
  const value = Number(raw);
  if (!Number.isFinite(value) || (integer && !Number.isInteger(value))) {
    throw new Error(`${fieldLabel(name)} must be ${integer ? "an integer" : "a finite number"}.`);
  }
  return value;
}

function parseRequiredInteger(raw, label, { min, max }) {
  const value = Number(raw);
  if (
    !nonEmptyText(raw)
    || !Number.isSafeInteger(value)
    || value < min
    || value > max
  ) {
    throw new Error(`${label} must be an integer from ${min} to ${max}.`);
  }
  return value;
}

function optionalText(inputs, key, value) {
  const normalized = nonEmptyText(value);
  if (normalized) inputs[key] = normalized;
}

function optionalValue(inputs, key, value) {
  if (value !== undefined) inputs[key] = value;
}

function checkedValues(form, name) {
  const fields = form?.querySelectorAll?.(
    `[data-candidate-lab-field="${name}"]:checked`,
  ) || [];
  return Array.from(fields)
    .map((field) => nonEmptyText(field.value))
    .filter(Boolean);
}

function sentinelValues(form) {
  const raw = formValue(form, "sentinel_values");
  if (!raw) return [];
  const entries = raw
    .split(/[,,,;;\n]+/)
    .map((item) => item.trim())
    .filter(Boolean);
  const values = entries.map((entry) => {
    const separator = entry.indexOf(":");
    if (separator < 1) {
      throw new Error("Prefix special values with their type, such as text:001 or number:-9999.");
    }
    const type = entry.slice(0, separator).trim().toLowerCase();
    const value = entry.slice(separator + 1).trim();
    if (!value) throw new Error("A special-value type prefix is required.");
    if (type === "text") return value;
    if (type !== "number") {
      throw new Error("Special-value types must be text or number.");
    }
    const number = Number(value);
    if (!Number.isFinite(number)) {
      throw new Error(`Special value ${entry} must contain a finite number.`);
    }
    return number;
  });
  return uniqueValues(values, "Special value");
}

function parseFeatureNumberMapping(value, label) {
  const text = String(value || "").trim();
  if (!text) return {};
  const entries = text.split(/[;\n;]+/).map((item) => item.trim()).filter(Boolean);
  const mapping = {};
  for (const entry of entries) {
    const separator = entry.indexOf("=");
    if (separator < 1) {
      throw new Error(`${label}: use field=point1,point2;field2=point1.`);
    }
    const feature = entry.slice(0, separator).trim();
    const points = splitValues(entry.slice(separator + 1)).map((item) => Number(item));
    if (!feature || !points.length || points.some((item) => !Number.isFinite(item))) {
      throw new Error(`${label} requires finite numeric cut points for each field.`);
    }
    if (Object.prototype.hasOwnProperty.call(mapping, feature)) {
      throw new Error(`${label} contains duplicate field ${feature}.`);
    }
    if (points.some((point, index) => index > 0 && point <= points[index - 1])) {
      throw new Error(`${label}.${feature} cut points must be strictly increasing.`);
    }
    mapping[feature] = points;
  }
  return mapping;
}

function parseDirections(value) {
  const text = String(value || "").trim();
  if (!text) return {};
  const entries = text.split(/[;;,\n]+/).map((item) => item.trim()).filter(Boolean);
  const directions = {};
  for (const entry of entries) {
    const separator = entry.indexOf("=");
    if (separator < 1) {
      throw new Error("Use field=increasing, field=decreasing or field=unordered for risk direction.");
    }
    const feature = entry.slice(0, separator).trim();
    const direction = entry.slice(separator + 1).trim();
    if (!["increasing", "decreasing", "unordered"].includes(direction)) {
      throw new Error(`Risk direction for ${feature} must be increasing, decreasing or unordered.`);
    }
    if (Object.prototype.hasOwnProperty.call(directions, feature)) {
      throw new Error(`Duplicate risk-direction field: ${feature}.`);
    }
    directions[feature] = direction;
  }
  return directions;
}

function collectUnivariateInputs(form) {
  const features = uniqueValues(splitValues(formValue(form, "features")), "Analysis fields");
  if (!features.length) throw new Error("Enter at least one field for univariate analysis.");
  const inputs = { features };
  const methods = uniqueValues(checkedValues(form, "methods"), "Binning method");
  // Empty methods means the operator chose platform defaults. Omitting this
  // field is materially different from sending an invalid empty array.
  if (methods.length) inputs.methods = methods;
  optionalValue(inputs, "bin_count", optionalNumber(form, "bin_count", { integer: true }));
  optionalValue(inputs, "min_bin_pct", optionalNumber(form, "min_bin_pct"));
  optionalText(inputs, "loan_amount_col", formValue(form, "loan_amount_col"));
  optionalText(inputs, "overdue_amount_col", formValue(form, "overdue_amount_col"));
  const sentinels = sentinelValues(form);
  if (sentinels.length) inputs.sentinel_values = sentinels;
  const manualBreakpoints = parseFeatureNumberMapping(
    formValue(form, "manual_breakpoints"),
    "Manual cut points",
  );
  if (methods.includes("manual") && !Object.keys(manualBreakpoints).length) {
    throw new Error("Manual binning requires cut points.");
  }
  if (!methods.includes("manual") && Object.keys(manualBreakpoints).length) {
    throw new Error("Cut points are only used with manual binning.");
  }
  if (Object.keys(manualBreakpoints).length) {
    inputs.manual_breakpoints = manualBreakpoints;
  }
  return inputs;
}

function selectedProjectionOption(form, name, label) {
  const field = formField(form, name);
  const selected = Array.from(field?.selectedOptions || []);
  const option = selected[0] || null;
  if (
    !option
    || option.dataset?.candidateLabProjection !== "1"
    || !nonEmptyText(option.value)
  ) {
    throw new Error(`Select a verified ${label}.`);
  }
  return option;
}

function selectedProjectionValues(form, name, label) {
  const field = formField(form, name);
  const selected = Array.from(field?.selectedOptions || []);
  if (!selected.length) {
    throw new Error(`Select at least one ${label} from the current candidates.`);
  }
  if (selected.some((option) => option.dataset?.candidateLabProjection !== "1")) {
    throw new Error(`${label} must belong to the current candidates.`);
  }
  return uniqueValues(
    selected.map((option) => nonEmptyText(option.value)).filter(Boolean),
    label,
  );
}

function optionalProjectionValues(form, name, label) {
  const field = formField(form, name);
  const selected = Array.from(field?.selectedOptions || [])
    .filter((option) => nonEmptyText(option.value));
  if (selected.some((option) => option.dataset?.candidateLabProjection !== "1")) {
    throw new Error(`${label} must belong to the selected strategy pool.`);
  }
  return uniqueValues(
    selected.map((option) => nonEmptyText(option.value)),
    label,
  );
}

function parseRefinementMergeGroups(value, allowedBinIds) {
  const text = String(value || "").trim();
  if (!text) return [];
  const groups = text
    .split(/[;;\n]+/)
    .map((group) => group.split("+").map((item) => item.trim()).filter(Boolean))
    .filter((group) => group.length);
  const seen = new Set();
  for (const group of groups) {
    if (group.length < 2) {
      throw new Error("Each merge group needs at least two bin IDs, joined with +.");
    }
    for (const binId of group) {
      if (!allowedBinIds.has(binId)) {
        throw new Error(`Bin ${binId} is not available in the merge group.`);
      }
      if (seen.has(binId)) {
        throw new Error(`Duplicate bin ID in merge groups: ${binId}.`);
      }
      seen.add(binId);
    }
  }
  return groups;
}

function collectFreshRefinementInputs(form) {
  const feature = formValue(form, "refinement_feature");
  const method = formValue(form, "refinement_method");
  const operator = formValue(form, "risk_operator");
  const riskValue = optionalNumber(form, "risk_value");
  if (!feature) throw new Error("Enter the field to refine.");
  if (!method) throw new Error("Select a binning method.");
  if (![">=", ">", "<=", "<"].includes(operator)) {
    throw new Error("Select a valid bad-rate threshold operator.");
  }
  if (riskValue === undefined || riskValue < 0 || riskValue > 1) {
    throw new Error("The bad-rate threshold must be between 0 and 1.");
  }
  const inputs = {
    feature,
    method,
    selection: { risk_threshold: { operator, value: riskValue } },
  };
  optionalValue(inputs, "bin_count", optionalNumber(form, "bin_count", { integer: true }));
  optionalValue(inputs, "min_bin_pct", optionalNumber(form, "min_bin_pct"));
  optionalText(inputs, "loan_amount_col", formValue(form, "loan_amount_col"));
  optionalText(inputs, "overdue_amount_col", formValue(form, "overdue_amount_col"));
  const sentinels = sentinelValues(form);
  if (sentinels.length) inputs.sentinel_values = sentinels;

  const rawBreakpoints = formValue(form, "refinement_manual_breakpoints");
  if (method !== "manual" && rawBreakpoints) {
    throw new Error("Cut points are only used with manual binning.");
  }
  if (method === "manual") {
    const points = splitValues(rawBreakpoints).map((value) => Number(value));
    if (!points.length || points.some((value) => !Number.isFinite(value))) {
      throw new Error("Manual refinement requires finite numeric cut points.");
    }
    if (points.some((point, index) => index > 0 && point <= points[index - 1])) {
      throw new Error("Manual cut points must be strictly increasing.");
    }
    inputs.manual_breakpoints = { [feature]: points };
  }
  optionalText(inputs, "selection_reason", formValue(form, "selection_reason"));
  return inputs;
}

function collectExistingRefinementInputs(form) {
  const source = selectedProjectionOption(
    form,
    "source_candidate_id",
    "Existing candidate",
  );
  const pair = selectedProjectionOption(
    form,
    "source_feature_method",
    "Field and method",
  );
  const sourceCandidateId = nonEmptyText(source.value);
  const feature = nonEmptyText(pair.dataset?.feature);
  const method = nonEmptyText(pair.dataset?.method);
  if (
    !feature
    || !method
    || pair.dataset?.sourceCandidateId !== sourceCandidateId
  ) {
    throw new Error("The field and method must belong to the selected candidate.");
  }
  const sourceBinIds = selectedProjectionValues(
    form,
    "source_bin_ids",
    "Source bins",
  );
  const binField = formField(form, "source_bin_ids");
  const allowedBinIds = new Set(
    Array.from(binField?.options || [])
      .filter((option) => (
        option.dataset?.candidateLabProjection === "1"
        && option.dataset?.sourceCandidateId === sourceCandidateId
        && option.dataset?.feature === feature
        && option.dataset?.method === method
      ))
      .map((option) => nonEmptyText(option.value))
      .filter(Boolean),
  );
  if (sourceBinIds.some((binId) => !allowedBinIds.has(binId))) {
    throw new Error("The source bin must match the selected candidate, field and method.");
  }
  const inputs = {
    feature,
    method,
    source_candidate_id: sourceCandidateId,
    selection: { source_bin_ids: sourceBinIds },
  };
  const mergeGroups = parseRefinementMergeGroups(
    formValue(form, "merge_groups"),
    allowedBinIds,
  );
  if (mergeGroups.length) inputs.merge_groups = mergeGroups;
  optionalText(inputs, "selection_reason", formValue(form, "selection_reason"));
  return inputs;
}

function collectRefinementInputs(form) {
  const mode = formValue(form, "refinement_mode");
  if (mode === "fresh") return collectFreshRefinementInputs(form);
  if (mode === "existing") return collectExistingRefinementInputs(form);
  throw new Error("Choose a new analysis or refinement of an existing candidate.");
}

function collectCrossInputs(form) {
  const xFeature = formValue(form, "x_feature");
  const yFeature = formValue(form, "y_feature");
  const xMethod = formValue(form, "x_method");
  const yMethod = formValue(form, "y_method");
  if (!xFeature || !yFeature) throw new Error("Enter both X and Y fields.");
  if (xFeature === yFeature) throw new Error("X and Y must use different fields.");
  if (!xMethod || !yMethod) throw new Error("Select a binning method for each axis.");
  const inputs = {
    x_feature: xFeature,
    x_method: xMethod,
    y_feature: yFeature,
    y_method: yMethod,
  };
  optionalValue(inputs, "bin_count", optionalNumber(form, "bin_count", { integer: true }));
  optionalValue(inputs, "min_bin_pct", optionalNumber(form, "min_bin_pct"));
  optionalText(inputs, "loan_amount_col", formValue(form, "loan_amount_col"));
  optionalText(inputs, "overdue_amount_col", formValue(form, "overdue_amount_col"));
  const sentinels = sentinelValues(form);
  if (sentinels.length) inputs.sentinel_values = sentinels;

  const manualBreakpoints = {};
  for (const [feature, method, field] of [
    [xFeature, xMethod, "x_manual_breakpoints"],
    [yFeature, yMethod, "y_manual_breakpoints"],
  ]) {
    const raw = formValue(form, field);
    if (method !== "manual" && raw) {
      throw new Error(`${feature}: cut points require manual binning.`);
    }
    if (method !== "manual") continue;
    const points = splitValues(raw).map((value) => Number(value));
    if (!points.length || points.some((value) => !Number.isFinite(value))) {
      throw new Error(`${feature}: manual binning requires finite numeric cut points.`);
    }
    if (points.some((point, index) => index > 0 && point <= points[index - 1])) {
      throw new Error(`${feature}: cut points must be strictly increasing.`);
    }
    manualBreakpoints[feature] = points;
  }
  if (Object.keys(manualBreakpoints).length) {
    inputs.manual_breakpoints = manualBreakpoints;
  }
  return inputs;
}

function collectCrossCandidateSearchInputs(form) {
  const select = formField(form, "cross_search_features");
  const options = Array.from(select?.selectedOptions || []);
  if (options.length < 2 || options.length > 20) {
    throw new Error("Select 2–20 distinct fields for the cross-matrix search.");
  }
  if (options.some((option) => (
    option.dataset?.candidateLabProjection !== "1"
    || nonEmptyText(option.value) !== nonEmptyText(option.dataset?.feature)
    || !nonEmptyText(option.value)
  ))) {
    throw new Error("Select cross-matrix fields from the verified univariate results.");
  }
  const features = options.map((option) => nonEmptyText(option.value));
  if (new Set(features).size !== features.length) {
    throw new Error("Cross-matrix fields must be distinct.");
  }
  const maxPairs = optionalNumber(
    form,
    "cross_search_max_pairs",
    { integer: true },
  );
  if (maxPairs === undefined || maxPairs < 1 || maxPairs > 190) {
    throw new Error("The cross-matrix search budget must be an integer from 1 to 190 pairs.");
  }
  return { features, max_pairs: maxPairs };
}

function collectCrossCandidateBuildFromSearchInputs(form) {
  const search = selectedProjectionOption(
    form,
    "cross_build_search_id",
    "Field-pair search",
  );
  const pair = selectedProjectionOption(
    form,
    "cross_build_pair_id",
    "Field pair",
  );
  const searchId = nonEmptyText(search.value);
  const pairId = nonEmptyText(pair.value);
  if (
    !CROSS_SEARCH_ID_RE.test(searchId)
    || !CROSS_PAIR_ID_RE.test(pairId)
    || nonEmptyText(search.dataset?.searchId) !== searchId
    || nonEmptyText(pair.dataset?.searchId) !== searchId
    || nonEmptyText(pair.dataset?.pairId) !== pairId
  ) {
    throw new Error("The field pair must belong to the selected search.");
  }
  return { search_id: searchId, pair_id: pairId };
}

function collectCrossRuleSearchInputs(form) {
  const select = formField(form, "cross_rule_features");
  const options = Array.from(select?.selectedOptions || []);
  if (options.length < 2 || options.length > 12) {
    throw new Error("Select 2–12 distinct fields for the threshold-rule search.");
  }
  if (options.some((option) => (
    option.dataset?.candidateLabProjection !== "1"
    || nonEmptyText(option.value) !== nonEmptyText(option.dataset?.feature)
    || !nonEmptyText(option.value)
  ))) {
    throw new Error("Select threshold-rule fields from the verified univariate results.");
  }
  const features = options.map((option) => nonEmptyText(option.value));
  if (new Set(features).size !== features.length) {
    throw new Error("Threshold-rule search fields must be distinct.");
  }
  const dimension = optionalNumber(form, "cross_rule_dimension", {
    integer: true,
  });
  if (![2, 3].includes(dimension)) {
    throw new Error("Threshold-rule dimensions must be 2D or 3D.");
  }
  if (features.length < dimension) {
    throw new Error("Select at least as many fields as rule dimensions.");
  }
  const minLift = optionalNumber(form, "cross_rule_min_lift");
  const minBadCount = optionalNumber(form, "cross_rule_min_bad_count", {
    integer: true,
  });
  const maxHitShare = optionalNumber(form, "cross_rule_max_hit_share");
  const minAmountLift = optionalNumber(form, "cross_rule_min_amount_lift");
  const maxTrials = optionalNumber(form, "cross_rule_max_trials", {
    integer: true,
  });
  if (
    minLift === undefined || minLift < 0 || minLift > 1000
    || minBadCount === undefined || minBadCount < 0
    || maxHitShare === undefined || maxHitShare < 0 || maxHitShare > 1
    || (minAmountLift !== undefined
      && (minAmountLift < 0 || minAmountLift > 1000))
    || maxTrials === undefined || maxTrials < 1 || maxTrials > 5000
  ) {
    throw new Error("Threshold-rule constraints or trial budget are outside the permitted range.");
  }
  return {
    features,
    dimension,
    constraints: {
      min_lift: minLift,
      min_bad_count: minBadCount,
      max_hit_share: maxHitShare,
      min_amount_lift: minAmountLift === undefined ? null : minAmountLift,
    },
    max_trials: maxTrials,
  };
}

function collectCrossRuleCandidateBuildInputs(form) {
  const search = selectedProjectionOption(
    form,
    "cross_rule_build_search_id",
    "Threshold-rule search",
  );
  const rule = selectedProjectionOption(
    form,
    "cross_rule_build_rule_id",
    "Threshold rule",
  );
  const searchId = nonEmptyText(search.value);
  const ruleId = nonEmptyText(rule.value);
  if (
    !CROSS_RULE_SEARCH_ID_RE.test(searchId)
    || !CROSS_RULE_ID_RE.test(ruleId)
    || nonEmptyText(search.dataset?.searchId) !== searchId
    || nonEmptyText(rule.dataset?.searchId) !== searchId
    || nonEmptyText(rule.dataset?.ruleId) !== ruleId
  ) {
    throw new Error("The threshold rule must belong to the selected search.");
  }
  const inputs = { search_id: searchId, rule_id: ruleId };
  optionalText(
    inputs,
    "selection_reason",
    formValue(form, "cross_rule_selection_reason"),
  );
  return inputs;
}

function collectTreeInputs(form) {
  const features = uniqueValues(splitValues(formValue(form, "features")), "Tree field");
  if (!features.length) throw new Error("Enter at least one field for the automatic tree.");
  const inputs = { features };
  const directions = parseDirections(formValue(form, "directions"));
  const unknownDirectionFeatures = Object.keys(directions)
    .filter((feature) => !features.includes(feature));
  if (unknownDirectionFeatures.length) {
    throw new Error(`Risk directions reference unselected fields: ${unknownDirectionFeatures.join(", ")}.`);
  }
  if (Object.keys(directions).length) inputs.directions = directions;
  optionalValue(inputs, "max_depth", optionalNumber(form, "max_depth", { integer: true }));
  optionalValue(
    inputs,
    "min_leaf_count",
    optionalNumber(form, "min_leaf_count", { integer: true }),
  );
  optionalValue(
    inputs,
    "min_weight_fraction_leaf",
    optionalNumber(form, "min_weight_fraction_leaf"),
  );
  optionalValue(inputs, "seed", optionalNumber(form, "seed", { integer: true }));
  optionalText(inputs, "sample_weight_col", formValue(form, "sample_weight_col"));
  optionalText(inputs, "loan_amount_col", formValue(form, "loan_amount_col"));
  optionalText(inputs, "overdue_amount_col", formValue(form, "overdue_amount_col"));
  return inputs;
}

function parseRawPdBandEdges(value) {
  const edges = splitValues(value).map((item) => Number(item));
  if (
    edges.length < 3
    || edges.length > 21
    || edges.some((item) => !Number.isFinite(item))
  ) {
    throw new Error("PD boundaries require 3–21 finite numbers.");
  }
  if (edges[0] !== 0 || edges.at(-1) !== 1) {
    throw new Error("PD boundaries must start at 0 and end at 1.");
  }
  if (edges.some((item, index) => (
    item < 0
    || item > 1
    || (index > 0 && item <= edges[index - 1])
  ))) {
    throw new Error("PD boundaries must be between 0 and 1 and strictly increasing.");
  }
  return edges;
}

function collectScorecardModelScoreEvidenceInputs(form) {
  const features = uniqueValues(
    splitValues(formValue(form, "scorecard_model_features")),
    "Scorecard features",
  );
  if (!features.length || features.length > 50) {
    throw new Error("Scorecard modelling requires 1–50 distinct fields.");
  }
  const inputs = {
    features,
    seed: parseRequiredInteger(
      formValue(form, "scorecard_model_seed"),
      "Scorecard random seed",
      { min: 0, max: 4_294_967_295 },
    ),
    max_iter: parseRequiredInteger(
      formValue(form, "scorecard_model_max_iter"),
      "Maximum scorecard iterations",
      { min: 20, max: 5_000 },
    ),
    scorecard_max_bins: parseRequiredInteger(
      formValue(form, "scorecard_model_max_bins"),
      "Maximum scorecard bins",
      { min: 2, max: 20 },
    ),
  };
  optionalText(
    inputs,
    "sample_weight_col",
    formValue(form, "scorecard_model_sample_weight_col"),
  );
  if (inputs.sample_weight_col && features.includes(inputs.sample_weight_col)) {
    throw new Error("The sample-weight column cannot also be a model feature.");
  }
  return inputs;
}

function collectScorecardBandInputs(form) {
  const mode = formValue(form, "scorecard_banding_mode");
  if (mode === "equal_frequency") {
    const binCount = optionalNumber(
      form,
      "scorecard_bin_count",
      { integer: true },
    );
    if (binCount === undefined) return {};
    if (binCount < 2 || binCount > 20) {
      throw new Error("The number of scorecard bands must be an integer from 2 to 20.");
    }
    return { bin_count: binCount };
  }
  if (mode === "raw_pd_edges") {
    return {
      raw_pd_band_edges: parseRawPdBandEdges(
        formValue(form, "raw_pd_band_edges"),
      ),
    };
  }
  throw new Error("Select equal-frequency bands or custom PD boundaries.");
}

function collectScorecardCutoffSelectionInputs(form) {
  const asset = selectedProjectionOption(
    form,
    "scorecard_asset_id",
    "Scorecard bands",
  );
  const cutoff = selectedProjectionOption(
    form,
    "scorecard_cutoff_id",
    "Cutoff",
  );
  const assetId = nonEmptyText(asset.value);
  const cutoffId = nonEmptyText(cutoff.value);
  if (cutoff.dataset?.sourceAssetId !== assetId) {
    throw new Error("The cutoff must belong to the selected scorecard bands.");
  }
  const inputs = {
    asset_id: assetId,
    cutoff_id: cutoffId,
  };
  optionalText(
    inputs,
    "reason",
    formValue(form, "scorecard_selection_reason"),
  );
  return inputs;
}

function sampleDesignLiteral(rawValue) {
  const raw = nonEmptyText(rawValue);
  const separator = raw.indexOf(":");
  if (separator < 1) {
    throw new Error("Prefix population condition values with a type, such as text:APP or number:30.");
  }
  const type = raw.slice(0, separator).trim().toLowerCase();
  const value = raw.slice(separator + 1).trim();
  if (!value) throw new Error("Population condition values cannot be empty.");
  if (type === "text") return value;
  if (type === "boolean") {
    if (!["true", "false"].includes(value.toLowerCase())) {
      throw new Error("Boolean condition values must be true or false.");
    }
    return value.toLowerCase() === "true";
  }
  if (type !== "number") {
    throw new Error("Population condition types must be text, number or boolean.");
  }
  const number = Number(value);
  if (!Number.isFinite(number)) {
    throw new Error("Numeric population conditions require a finite value.");
  }
  return number;
}

function collectSamplePopulation(form, prefix) {
  const column = formValue(form, `${prefix}_population_column`);
  const operator = formValue(form, `${prefix}_population_operator`);
  const rawValue = formValue(form, `${prefix}_population_value`);
  if (!column && !operator && !rawValue) {
    return { inclusion: null, exclusion: null };
  }
  if (!column || !operator) {
    throw new Error(`${prefix === "approval" ? "Approval" : "Risk"} population conditions require a field and operator.`);
  }
  const condition = { column, operator };
  if (!["is_null", "is_not_null"].includes(operator)) {
    if (!rawValue) {
      throw new Error(`${prefix === "approval" ? "Approval" : "Risk"} population conditions require a typed value.`);
    }
    condition.value = sampleDesignLiteral(rawValue);
  } else if (rawValue) {
    throw new Error("Null checks do not require a condition value.");
  }
  return {
    inclusion: { match: "all", conditions: [condition] },
    exclusion: null,
  };
}

function nullableText(form, name) {
  return formValue(form, name) || null;
}

function nullableInteger(form, name) {
  const raw = formValue(form, name);
  if (!raw) return null;
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1) {
    throw new Error(`${fieldLabel(name)} must be a positive integer.`);
  }
  return value;
}

function sampleTimeRange(form, prefix, label) {
  const start = nullableText(form, `sample_${prefix}_start`);
  const end = nullableText(form, `sample_${prefix}_end`);
  if (!start && !end) {
    throw new Error(`${label} requires at least one date boundary.`);
  }
  if (start && end && start > end) {
    throw new Error(`${label}: the start date cannot follow the end date.`);
  }
  return { start, end };
}

function collectSampleDesignV2Inputs(form) {
  const targetBadValue = Number(formValue(form, "sample_target_bad_value"));
  if (![0, 1].includes(targetBadValue)) {
    throw new Error("The bad-outcome label must be 0 or 1.");
  }
  const relationship = formValue(form, "sample_relationship");
  if (!["nested_same_cohort", "parallel_time_cohorts"].includes(relationship)) {
    throw new Error("Select the relationship between the approval and risk populations.");
  }
  const timeField = formValue(form, "sample_time_field");
  if (!timeField) throw new Error("Enter the time field used to split the sample.");
  const maturityStatus = formValue(form, "sample_maturity_status");
  const performanceStatus = formValue(form, "sample_performance_status");
  const observationStatus = formValue(form, "sample_observation_status");
  const historicalStatus = formValue(form, "sample_historical_score_status");
  const maturityDays = nullableInteger(form, "sample_maturity_days");
  const maturityCutoff = nullableText(form, "sample_maturity_cutoff");
  const maturityReason = nullableText(form, "sample_maturity_reason");
  const performanceDays = nullableInteger(form, "sample_performance_days");
  const observationStart = nullableText(form, "sample_observation_start");
  const observationEnd = nullableText(form, "sample_observation_end");
  const historicalColumn = nullableText(
    form,
    "sample_historical_score_column",
  );
  const historicalDirection = nullableText(
    form,
    "sample_historical_score_direction",
  );
  const historicalReason = nullableText(
    form,
    "sample_historical_score_reason",
  );
  if (
    ![
      "confirmed_matured",
      "not_matured",
      "unknown",
      "unavailable",
    ].includes(maturityStatus)
  ) {
    throw new Error("Select a valid sample-maturity status.");
  }
  if (!["provided", "unavailable"].includes(performanceStatus)) {
    throw new Error("Select a valid performance-window status.");
  }
  if (!["provided", "unavailable"].includes(observationStatus)) {
    throw new Error("Select a valid observation-window status.");
  }
  const evaluatedMaturity = [
    "confirmed_matured",
    "not_matured",
  ].includes(maturityStatus);
  if (evaluatedMaturity) {
    if (!maturityDays || !maturityCutoff) {
      throw new Error("Assessed maturity requires performance days and a maturity cutoff date.");
    }
    if (performanceStatus !== "provided" || performanceDays !== maturityDays) {
      throw new Error("Maturity and performance windows must use the same number of days.");
    }
    if (maturityStatus === "not_matured" && !maturityReason) {
      throw new Error("Explain why the sample is not yet mature.");
    }
    if (maturityStatus === "confirmed_matured" && maturityReason) {
      throw new Error("Clear the maturity explanation when maturity is confirmed.");
    }
  } else if (maturityDays || maturityCutoff || !maturityReason) {
    throw new Error("For unknown or unavailable maturity, leave days and cutoff blank and provide an explanation.");
  }
  if (
    (performanceStatus === "provided" && !performanceDays)
    || (performanceStatus === "unavailable" && performanceDays)
  ) {
    throw new Error("The performance-window status does not match its number of days.");
  }
  if (observationStatus === "provided") {
    if (!observationStart || !observationEnd) {
      throw new Error("An available observation window requires start and end dates.");
    }
    if (observationStart > observationEnd) {
      throw new Error("The observation-window start date cannot follow its end date.");
    }
  } else if (observationStart || observationEnd) {
    throw new Error("Leave observation dates blank when the window is unavailable.");
  }
  if (
    !["available", "unavailable", "not_applicable"].includes(historicalStatus)
  ) {
    throw new Error("Select a valid historical-score status.");
  }
  if (historicalStatus === "available") {
    if (
      !historicalColumn
      || !["higher_is_riskier", "lower_is_riskier"].includes(
        historicalDirection,
      )
    ) {
      throw new Error("An available historical score requires its field and risk direction.");
    }
    if (historicalReason) {
      throw new Error("Clear the historical-score explanation when a score is available.");
    }
  } else if (historicalColumn || historicalDirection || !historicalReason) {
    throw new Error("For unavailable or inapplicable historical scores, provide only an explanation.");
  }
  return {
    target_bad_value: targetBadValue,
    drop_nan_labels: Boolean(
      formField(form, "sample_drop_nan_labels")?.checked,
    ),
    relationship,
    approval_population: collectSamplePopulation(form, "approval"),
    risk_population: collectSamplePopulation(form, "risk"),
    partitioning: {
      method: "time_ranges",
      column: timeField,
      ranges: {
        development: sampleTimeRange(form, "development", "Development set"),
        validation: sampleTimeRange(form, "validation", "Validation set"),
        oot: sampleTimeRange(form, "oot", "OOT"),
      },
    },
    maturity: {
      status: maturityStatus,
      performance_window_days: maturityDays,
      cutoff_date: maturityCutoff,
      reason: maturityReason,
    },
    performance_window: {
      status: performanceStatus,
      days: performanceDays,
    },
    observation_window: {
      status: observationStatus,
      start: observationStart,
      end: observationEnd,
    },
    field_bindings: {
      entity_field: nullableText(form, "sample_entity_field"),
      time_field: timeField,
      group_field: nullableText(form, "sample_group_field"),
      month_field: nullableText(form, "sample_month_field"),
      weight_field: nullableText(form, "sample_weight_field"),
      loan_amount_field: nullableText(form, "sample_loan_amount_field"),
      overdue_amount_field: nullableText(form, "sample_overdue_amount_field"),
    },
    historical_score: {
      status: historicalStatus,
      column: historicalColumn,
      direction: historicalDirection,
      reason: historicalReason,
    },
  };
}

function collectCandidateMonthlyStabilityInputs(form) {
  const mode = formValue(form, "stability_source_mode");
  if (mode === "pool_entry") {
    const entry = selectedProjectionOption(
      form,
      "stability_pool_entry",
      "Current pool entry",
    );
    const strategyType = nonEmptyText(entry.dataset?.strategyType);
    if (!strategyType) {
      throw new Error("The selected pool entry has no verified strategy type.");
    }
    return {
      strategy_type: strategyType,
      entry_id: nonEmptyText(entry.value),
    };
  }
  if (mode === "univariate_asset") {
    const asset = selectedProjectionOption(
      form,
      "stability_asset_id",
      "Univariate candidate asset",
    );
    return { asset_id: nonEmptyText(asset.value) };
  }
  throw new Error("Select a pool entry or univariate candidate asset.");
}

function collectStrategyPoolValidationInputs(form) {
  const strategyType = selectedStrategyPoolType(
    form,
    "pool_validation_strategy_type",
  );
  const partition = formValue(form, "pool_validation_partition");
  if (!STRATEGY_POOL_TYPES.includes(strategyType)) {
    throw new Error("Select a verified strategy pool for independent validation.");
  }
  if (!["validation", "oot"].includes(partition)) {
    throw new Error("Independent replay validation requires the validation or out-of-time sample.");
  }
  return {
    strategy_type: strategyType,
    partition,
  };
}

function collectStrategyPoolStabilityInputs(form) {
  return {
    strategy_type: selectedStrategyPoolType(
      form,
      "pool_stability_strategy_type",
    ),
  };
}

function collectStrategyPoolImpactInputs(form) {
  const strategyType = selectedStrategyPoolType(
    form,
    "pool_impact_strategy_type",
  );
  if (!["approval", "reject"].includes(strategyType)) {
    throw new Error("Pool impact supports approval and reject strategies only.");
  }
  const comparisonMode = formValue(form, "pool_impact_comparison_mode")
    || "absolute";
  const inputs = {
    strategy_type: strategyType,
    comparison_mode: comparisonMode,
    drop_nan_labels: Boolean(
      formField(form, "pool_impact_drop_nan_labels")?.checked,
    ),
  };
  optionalText(
    inputs,
    "baseline_strategy_id",
    formValue(form, "pool_impact_baseline_strategy_id"),
  );
  optionalText(inputs, "month_col", formValue(form, "pool_impact_month_col"));
  optionalText(
    inputs,
    "loan_amount_col",
    formValue(form, "pool_impact_loan_amount_col"),
  );
  optionalText(
    inputs,
    "overdue_amount_col",
    formValue(form, "pool_impact_overdue_amount_col"),
  );
  if (
    comparisonMode === "vs_baseline"
    && !inputs.baseline_strategy_id
  ) {
    throw new Error("Select a baseline strategy for historical comparison.");
  }
  if (
    comparisonMode === "absolute"
    && inputs.baseline_strategy_id
  ) {
    throw new Error("Absolute impact measurement does not use a baseline strategy.");
  }
  return inputs;
}

function collectStrategyImpactCubeInputs(form) {
  const inputs = {
    strategy_type: selectedStrategyPoolType(
      form,
      "impact_cube_strategy_type",
    ),
  };
  const partitions = uniqueValues(
    checkedValues(form, "impact_cube_partitions"),
    "Impact partitions",
  );
  if (partitions.length) inputs.partitions = partitions;
  optionalText(inputs, "month_col", formValue(form, "impact_cube_month_col"));
  optionalText(inputs, "group_col", formValue(form, "impact_cube_group_col"));
  optionalText(
    inputs,
    "segment_col",
    formValue(form, "impact_cube_segment_col"),
  );
  optionalText(
    inputs,
    "current_strategy_id",
    formValue(form, "impact_cube_current_strategy_id"),
  );
  const dimensions = [
    inputs.month_col,
    inputs.group_col,
    inputs.segment_col,
  ].filter(Boolean);
  if (new Set(dimensions).size !== dimensions.length) {
    throw new Error("Month, group and cohort dimensions must use different fields.");
  }
  return inputs;
}

function collectStrategyReportBundleV2Inputs(form) {
  const title = formValue(form, "strategy_report_title")
    || "Strategy review report";
  if (title.length > 200) throw new Error("The report title must be 200 characters or fewer.");
  const status = formValue(form, "strategy_report_status") || "partial";
  if (!["draft", "partial", "final"].includes(status)) {
    throw new Error("Report status must be draft, partial or final.");
  }
  return { title, status };
}

function collectStrategyPoolApplyInputs(form) {
  const selected = selectedProjectionOption(
    form,
    "pool_apply_strategy_type",
    "Non-empty strategy pool",
  );
  const strategyType = nonEmptyText(selected.value);
  if (
    !STRATEGY_POOL_TYPES.includes(strategyType)
    || nonEmptyText(selected.dataset?.strategyType) !== strategyType
  ) {
    throw new Error("Select a verified, non-empty pool for this task.");
  }
  const inputs = { strategy_type: strategyType };
  const outputPrefix = formValue(form, "pool_apply_output_prefix");
  if (outputPrefix) {
    if (!STRATEGY_POOL_APPLY_PREFIX_RE.test(outputPrefix)) {
      throw new Error("The output prefix must use up to 48 ASCII letters, digits or underscores and cannot start with a digit.");
    }
    inputs.output_prefix = outputPrefix;
  }
  return inputs;
}

function selectedStrategyPoolType(form, fieldName) {
  const selected = selectedProjectionOption(
    form,
    fieldName,
    "Non-empty strategy pool",
  );
  const strategyType = nonEmptyText(selected.value);
  if (
    !STRATEGY_POOL_TYPES.includes(strategyType)
    || nonEmptyText(selected.dataset?.strategyType) !== strategyType
  ) {
    throw new Error("Select a verified, non-empty pool for this task.");
  }
  return strategyType;
}

function selectedStrategyPoolEntry(form, fieldName, strategyType) {
  const selected = selectedProjectionOption(
    form,
    fieldName,
    "Current pool entry",
  );
  const entryId = nonEmptyText(selected.value);
  if (
    !STRATEGY_POOL_ENTRY_ID_RE.test(entryId)
    || nonEmptyText(selected.dataset?.strategyType) !== strategyType
    || nonEmptyText(selected.dataset?.entryId) !== entryId
  ) {
    throw new Error("Select an entry from the current pool.");
  }
  return entryId;
}

function optionalStrategyPoolReason(inputs, form, fieldName) {
  const reason = formValue(form, fieldName);
  if (!reason) return;
  if (reason.length > 500) {
    throw new Error("The pool-operation reason must be 500 characters or fewer.");
  }
  inputs.reason = reason;
}

function collectStrategyPoolCompileInputs(form) {
  return {
    strategy_type: selectedStrategyPoolType(
      form,
      "pool_compile_strategy_type",
    ),
  };
}

function collectStrategyPoolRemoveEntryInputs(form) {
  const strategyType = selectedStrategyPoolType(
    form,
    "pool_remove_strategy_type",
  );
  const inputs = {
    strategy_type: strategyType,
    entry_id: selectedStrategyPoolEntry(
      form,
      "pool_remove_entry_id",
      strategyType,
    ),
  };
  optionalStrategyPoolReason(inputs, form, "pool_remove_reason");
  return inputs;
}

function strategyPoolTypedAction(
  form,
  strategyType,
  typeField,
  valueField,
) {
  const typeControl = formField(form, typeField);
  const actionType = formValue(form, typeField);
  const allowed = STRATEGY_POOL_ACTION_TYPES[strategyType] || [];
  if (!allowed.includes(actionType)) {
    throw new Error(`${actionType || "Selected"} action is not supported by the ${strategyType} pool.`);
  }
  if (
    typeControl?.dataset?.candidateLabPoolAddLocked === "1"
    && typeControl.dataset.candidateLabPoolAddTypedAction
  ) {
    let projectedAction;
    try {
      projectedAction = JSON.parse(
        typeControl.dataset.candidateLabPoolAddTypedAction,
      );
    } catch {
      throw new Error("The default pool action is invalid. Refresh and select it again.");
    }
    const exactAction = minimalProjectedPoolAction(
      projectedAction,
      strategyType,
    );
    if (!exactAction || exactAction.type !== actionType) {
      throw new Error("The default pool action has changed. Refresh and select it again.");
    }
    return exactAction;
  }
  if (["approval", "reject", "review"].includes(actionType)) {
    return { type: actionType };
  }
  const rawValue = formValue(form, valueField);
  if (!rawValue) {
    throw new Error(`${actionType} requires an action value.`);
  }
  if (actionType === "segment") {
    return { type: actionType, value: rawValue };
  }
  const value = Number(rawValue);
  if (!Number.isFinite(value)) {
    throw new Error(`${actionType} requires a finite action value.`);
  }
  if (actionType === "limit" && value < 0) {
    throw new Error("The limit must be a finite, non-negative value.");
  }
  if (actionType === "pricing" && (value < 0 || value > 1)) {
    throw new Error("The pricing value must be a finite number between 0 and 1.");
  }
  return { type: actionType, value };
}

function strategyPoolAction(form, strategyType) {
  return strategyPoolTypedAction(
    form,
    strategyType,
    "pool_action_type",
    "pool_action_value",
  );
}

function collectStrategyPoolAddCandidateInputs(form) {
  const strategyType = formValue(form, "pool_add_strategy_type");
  if (!STRATEGY_POOL_TYPES.includes(strategyType)) {
    throw new Error("Select a supported strategy-pool type.");
  }
  const selected = selectedProjectionOption(
    form,
    "pool_add_source_id",
    "Candidate source",
  );
  const sourceId = nonEmptyText(selected.value);
  const sourceKind = nonEmptyText(selected.dataset?.sourceKind);
  const pointerKind = nonEmptyText(selected.dataset?.pointerKind);
  const expectedPointer = STRATEGY_POOL_ADD_SOURCE_KINDS[sourceKind];
  if (
    !expectedPointer
    || pointerKind !== expectedPointer
    || nonEmptyText(selected.dataset?.sourceId) !== sourceId
    || (
      pointerKind === "candidate_asset_id"
        ? !STRATEGY_POOL_CANDIDATE_ASSET_ID_RE.test(sourceId)
        : !STRATEGY_POOL_ADD_SELECTION_RE.test(sourceId)
    )
  ) {
    throw new Error("Select a verified candidate eligible for this pool.");
  }
  const sourceStrategyType = nonEmptyText(
    selected.dataset?.strategyType,
  );
  if (
    sourceKind === "voting_candidate"
      ? sourceStrategyType !== strategyType
      : Boolean(sourceStrategyType)
  ) {
    throw new Error("The candidate is incompatible with the pool type or its source has changed.");
  }
  const inputs = {
    strategy_type: strategyType,
    [pointerKind]: sourceId,
    default_action: strategyPoolTypedAction(
      form,
      strategyType,
      "pool_add_default_action_type",
      "pool_add_default_action_value",
    ),
    action: strategyPoolTypedAction(
      form,
      strategyType,
      "pool_add_action_type",
      "pool_add_action_value",
    ),
  };
  const placementMode = formValue(form, "pool_add_placement_mode");
  if (sourceKind === "voting_candidate") {
    if (!STRATEGY_POOL_VOTING_PLACEMENTS.includes(placementMode)) {
      throw new Error("Choose where to place the voting candidate in the pool.");
    }
    inputs.placement_mode = placementMode;
  } else if (placementMode) {
    throw new Error("The placement mode is only valid for voting candidates.");
  }
  optionalStrategyPoolReason(inputs, form, "pool_add_reason");
  return inputs;
}

function collectStrategyPoolSetActionInputs(form) {
  const strategyType = selectedStrategyPoolType(
    form,
    "pool_action_strategy_type",
  );
  const inputs = {
    strategy_type: strategyType,
    entry_id: selectedStrategyPoolEntry(
      form,
      "pool_action_entry_id",
      strategyType,
    ),
    action: strategyPoolAction(form, strategyType),
  };
  optionalStrategyPoolReason(inputs, form, "pool_action_reason");
  return inputs;
}

function collectStrategyPoolReorderInputs(form) {
  const strategyType = selectedStrategyPoolType(
    form,
    "pool_reorder_strategy_type",
  );
  const orderField = formField(form, "pool_reorder_ordered_ids");
  const options = Array.from(orderField?.options || []);
  if (options.length < 1 || options.length > 200) {
    throw new Error("Reordering must include every current entry, up to 200 entries.");
  }
  const orderedIds = options.map((option) => {
    const entryId = nonEmptyText(option.value);
    if (
      option.dataset?.candidateLabProjection !== "1"
      || !STRATEGY_POOL_ENTRY_ID_RE.test(entryId)
      || nonEmptyText(option.dataset?.strategyType) !== strategyType
      || nonEmptyText(option.dataset?.entryId) !== entryId
    ) {
      throw new Error("Reordering must use the current pool entry IDs.");
    }
    return entryId;
  });
  if (new Set(orderedIds).size !== orderedIds.length) {
    throw new Error("Reordering cannot contain duplicate entry IDs.");
  }
  const inputs = {
    strategy_type: strategyType,
    ordered_ids: orderedIds,
  };
  optionalStrategyPoolReason(inputs, form, "pool_reorder_reason");
  return inputs;
}

function parseVotingConstraints(value) {
  const text = String(value || "").trim();
  if (!text) return [];
  const rows = text
    .split(/[;;\n]+/)
    .map((row) => row.trim())
    .filter(Boolean);
  if (rows.length > 32) {
    throw new Error("Voting search supports up to 32 eligibility constraints.");
  }
  const seen = new Set();
  const constraints = rows.map((row) => {
    const match = row.match(
      /^([a-z_]+)\s*(>=|<=|gte|lte)\s*(\d+(?:\.\d+)?%?)$/i,
    );
    if (!match) {
      throw new Error(`Constraint ${row} must use metric >= value or metric <= value.`);
    }
    const metric = match[1].toLowerCase();
    if (!VOTING_SEARCH_METRICS.includes(metric)) {
      throw new Error(`Unsupported voting constraint metric: ${metric}.`);
    }
    const operator = [">=", "gte"].includes(match[2].toLowerCase())
      ? "gte"
      : "lte";
    const percent = match[3].endsWith("%");
    const number = Number(percent ? match[3].slice(0, -1) : match[3]);
    const normalized = percent ? number / 100 : number;
    if (!Number.isFinite(normalized) || normalized < 0) {
      throw new Error(`Voting constraint ${metric} requires a finite, non-negative value.`);
    }
    const identity = `${metric}\u001f${operator}`;
    if (seen.has(identity)) {
      throw new Error(`Duplicate voting constraint: ${metric} ${operator}.`);
    }
    seen.add(identity);
    return { metric, operator, value: normalized };
  });
  return constraints.sort(
    (left, right) => (
      left.metric.localeCompare(right.metric)
      || left.operator.localeCompare(right.operator)
      || left.value - right.value
    ),
  );
}

function collectVotingCandidateSearchInputs(form) {
  const strategy = selectedProjectionOption(
    form,
    "voting_strategy_type",
    "Current strategy pool",
  );
  const strategyType = nonEmptyText(strategy.value);
  const memberCount = optionalNumber(
    form,
    "voting_member_count",
    { integer: true },
  );
  const n = optionalNumber(form, "voting_n", { integer: true });
  const maxCombinations = optionalNumber(
    form,
    "voting_max_combinations",
    { integer: true },
  );
  if (memberCount === undefined || memberCount < 2 || memberCount > 50) {
    throw new Error("Members per voting group (K) must be an integer from 2 to 50.");
  }
  if (n === undefined || n < 1 || n > memberCount) {
    throw new Error(`The voting threshold (n) must be an integer from 1 to ${memberCount}.`);
  }
  if (
    maxCombinations === undefined
    || maxCombinations < 1
    || maxCombinations > 10000
  ) {
    throw new Error("The voting search budget must be an integer from 1 to 10,000.");
  }
  const objectiveMetric = formValue(form, "voting_objective_metric");
  const objectiveDirection = formValue(form, "voting_objective_direction");
  if (!VOTING_SEARCH_METRICS.includes(objectiveMetric)) {
    throw new Error("Select a supported voting ranking metric.");
  }
  if (!["maximize", "minimize"].includes(objectiveDirection)) {
    throw new Error("Voting ranking direction must be maximize or minimize.");
  }
  const includeRuleIds = optionalProjectionValues(
    form,
    "voting_include_rule_ids",
    "Required rules",
  ).sort();
  const excludeRuleIds = optionalProjectionValues(
    form,
    "voting_exclude_rule_ids",
    "Exclusion rules",
  ).sort();
  if (
    [...includeRuleIds, ...excludeRuleIds].some(
      (ruleId) => !VOTING_RULE_ID_RE.test(ruleId),
    )
  ) {
    throw new Error("The voting selection contains an invalid rule ID.");
  }
  const overlap = includeRuleIds.filter((ruleId) => excludeRuleIds.includes(ruleId));
  if (overlap.length) {
    throw new Error("Required and excluded rules cannot overlap.");
  }
  if (includeRuleIds.length > memberCount) {
    throw new Error("The number of required rules cannot exceed K.");
  }
  const constraints = parseVotingConstraints(
    formValue(form, "voting_constraints"),
  );
  const minimumShareMetric = {
    bad_rate: "hit_share",
    lift: "hit_share",
    weighted_bad_rate: "weighted_hit_share",
    bad_amount_rate: "hit_amount_share",
  }[objectiveMetric];
  if (
    objectiveDirection === "minimize"
    && minimumShareMetric
    && !constraints.some((constraint) => (
      constraint.metric === minimumShareMetric
      && constraint.operator === "gte"
      && constraint.value > 0
    ))
  ) {
    throw new Error(`Minimizing ${objectiveMetric} requires a positive ${minimumShareMetric} lower bound to exclude empty-hit combinations.`);
  }
  return {
    strategy_type: strategyType,
    member_count: memberCount,
    n,
    objective: {
      metric: objectiveMetric,
      direction: objectiveDirection,
    },
    constraints,
    include_rule_ids: includeRuleIds,
    exclude_rule_ids: excludeRuleIds,
    max_combinations: maxCombinations,
  };
}

function collectVotingCandidateBuildFromSearchInputs(form) {
  const search = selectedProjectionOption(
    form,
    "voting_search_id",
    "Voting search",
  );
  const combo = selectedProjectionOption(
    form,
    "voting_combo_id",
    "Voting combination",
  );
  const searchId = nonEmptyText(search.value);
  const comboId = nonEmptyText(combo.value);
  if (!VOTING_SEARCH_ID_RE.test(searchId) || !VOTING_COMBO_ID_RE.test(comboId)) {
    throw new Error("Invalid voting search or combination ID.");
  }
  if (nonEmptyText(combo.dataset?.sourceSearchId) !== searchId) {
    throw new Error("The voting combination must belong to the selected search.");
  }
  const inputs = {
    search_id: searchId,
    combo_id: comboId,
  };
  const strategyType = nonEmptyText(search.dataset?.strategyType);
  if (strategyType) inputs.strategy_type = strategyType;
  return inputs;
}

function collectInteractiveTreeSplitSearchInputs(form) {
  const source = selectedProjectionOption(
    form,
    "interactive_tree_search_source_id",
    "Tree or revision",
  );
  const node = selectedProjectionOption(
    form,
    "interactive_tree_search_node_id",
    "Current tree node",
  );
  const sourceTreeId = nonEmptyText(source.value);
  const nodeId = nonEmptyText(node.value);
  const mode = formValue(form, "interactive_tree_search_mode");
  if (
    !INTERACTIVE_TREE_SOURCE_ID_RE.test(sourceTreeId)
    || !INTERACTIVE_TREE_NODE_ID_RE.test(nodeId)
    || nonEmptyText(source.dataset?.sourceTreeId) !== sourceTreeId
    || nonEmptyText(node.dataset?.sourceTreeId) !== sourceTreeId
    || nonEmptyText(node.dataset?.nodeId) !== nodeId
    || !["all_features", "selected_features"].includes(mode)
  ) {
    throw new Error("Select a verified tree node for split search.");
  }
  const maxThresholds = parseRequiredInteger(
    formValue(form, "interactive_tree_search_max_thresholds"),
    "Maximum thresholds per feature",
    { min: 1, max: 20 },
  );
  const maxRowEvaluations = parseRequiredInteger(
    formValue(form, "interactive_tree_search_max_row_evaluations"),
    "Total evaluation budget",
    { min: 1, max: 20000000 },
  );
  const inputs = {
    source_tree_id: sourceTreeId,
    node_id: nodeId,
    mode,
    max_thresholds_per_feature: maxThresholds,
    max_row_evaluations: maxRowEvaluations,
  };
  if (mode === "selected_features") {
    const features = splitValues(
      formValue(form, "interactive_tree_search_features"),
    );
    const universe = new Set(
      nonEmptyText(source.dataset?.featureUniverse)
        .split("\u001f")
        .map(nonEmptyText)
        .filter(Boolean),
    );
    if (
      !features.length
      || features.length > 50
      || new Set(features).size !== features.length
      || features.some((feature) => !universe.has(feature))
    ) {
      throw new Error("Select distinct features from the source tree.");
    }
    inputs.features = features;
  }
  return inputs;
}

function collectInteractiveTreeAutoContinuationInputs(form) {
  const searchId = nonEmptyText(
    formValue(form, "interactive_tree_continuation_search_id"),
  );
  const candidateId = nonEmptyText(
    formValue(form, "interactive_tree_continuation_candidate_id"),
  );
  if (
    !INTERACTIVE_TREE_SPLIT_SEARCH_ID_RE.test(searchId)
    || !INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_RE.test(candidateId)
  ) {
    throw new Error("Select an eligible split candidate from the verified search results.");
  }
  const minimumGain = Number(
    formValue(form, "interactive_tree_continuation_min_gain"),
  );
  if (!Number.isFinite(minimumGain) || minimumGain < 0 || minimumGain > 0.5) {
    throw new Error("Minimum Gini gain must be between 0 and 0.5.");
  }
  const inputs = {
    search_id: searchId,
    candidate_id: candidateId,
    max_additional_depth: parseRequiredInteger(
      formValue(form, "interactive_tree_continuation_max_depth"),
      "Maximum additional depth",
      { min: 1, max: 6 },
    ),
    min_gini_gain: minimumGain,
    max_generated_nodes: parseRequiredInteger(
      formValue(form, "interactive_tree_continuation_max_nodes"),
      "Maximum number of nodes generated",
      { min: 3, max: 127 },
    ),
    max_thresholds_per_feature: parseRequiredInteger(
      formValue(form, "interactive_tree_continuation_max_thresholds"),
      "Maximum thresholds per feature",
      { min: 1, max: 20 },
    ),
    max_row_evaluations: parseRequiredInteger(
      formValue(form, "interactive_tree_continuation_max_row_evaluations"),
      "Total evaluation budget",
      { min: 1, max: 20000000 },
    ),
    objective: formValue(form, "interactive_tree_continuation_objective"),
    tie_break: formValue(form, "interactive_tree_continuation_tie_break"),
  };
  if (
    inputs.objective !== "max_gini_gain"
    || inputs.tie_break
      !== "eligible_gain_feature_threshold_candidate_id"
  ) {
    throw new Error("The target or tie-break rule has changed. Refresh the page.");
  }
  optionalText(
    inputs,
    "reason",
    formValue(form, "interactive_tree_continuation_reason"),
  );
  return inputs;
}

function collectInteractiveTreeRevisionInputs(form) {
  const source = selectedProjectionOption(
    form,
    "interactive_tree_source_id",
    "Tree or revision",
  );
  const node = selectedProjectionOption(
    form,
    "interactive_tree_node_id",
    "Tree node to revise",
  );
  const sourceTreeId = nonEmptyText(source.value);
  const nodeId = nonEmptyText(node.value);
  const operation = formValue(form, "interactive_tree_operation")
    || "prune_subtree";
  if (
    !INTERACTIVE_TREE_SOURCE_ID_RE.test(sourceTreeId)
    || !INTERACTIVE_TREE_NODE_ID_RE.test(nodeId)
    || nonEmptyText(source.dataset?.sourceTreeId) !== sourceTreeId
    || nonEmptyText(node.dataset?.sourceTreeId) !== sourceTreeId
    || nonEmptyText(node.dataset?.nodeId) !== nodeId
    || ![
      "prune_subtree",
      "adjust_split_threshold",
      "replace_split_feature",
    ].includes(operation)
    || node.dataset?.operation !== operation
  ) {
    throw new Error("Select a node from the current tree branch for this operation.");
  }
  const inputs = {
    source_tree_id: sourceTreeId,
    node_id: nodeId,
    operation,
  };
  if (
    operation === "adjust_split_threshold"
    || operation === "replace_split_feature"
  ) {
    const currentThreshold = Number(
      nonEmptyText(node.dataset?.currentThreshold),
    );
    const rawThreshold = formValue(form, "interactive_tree_threshold");
    const threshold = Number(rawThreshold);
    if (
      !nonEmptyText(node.dataset?.feature)
      || !Number.isFinite(currentThreshold)
    ) {
      throw new Error("Select a verified threshold adjustment with the current field and threshold.");
    }
    if (
      !rawThreshold
      || !Number.isFinite(threshold)
      || (
        Number.isInteger(threshold)
        && !Number.isSafeInteger(threshold)
      )
    ) {
      throw new Error("The new threshold must be a finite number.");
    }
    if (
      operation === "adjust_split_threshold"
      && threshold === currentThreshold
    ) {
      throw new Error("The new threshold must differ from the current threshold.");
    }
    inputs.threshold = threshold;
    if (operation === "replace_split_feature") {
      const featureOption = selectedProjectionOption(
        form,
        "interactive_tree_feature",
        "New split feature",
      );
      const feature = nonEmptyText(featureOption.value);
      if (
        !feature
        || nonEmptyText(featureOption.dataset?.sourceTreeId) !== sourceTreeId
        || featureOption.dataset?.candidateLabProjection !== "1"
        || feature === nonEmptyText(node.dataset?.feature)
      ) {
        throw new Error("Select the new split feature from the source tree.");
      }
      inputs.feature = feature;
    }
  }
  optionalText(inputs, "reason", formValue(form, "interactive_tree_reason"));
  return inputs;
}

function collectInteractiveTreeFrontierMaterializationInputs(form) {
  const revision = selectedProjectionOption(
    form,
    "interactive_tree_frontier_revision_id",
    "Interactive tree revision",
  );
  const frontier = selectedProjectionOption(
    form,
    "interactive_tree_frontier_source_node_id",
    "Frontpoint",
  );
  const revisionId = nonEmptyText(revision.value);
  const sourceNodeId = nonEmptyText(frontier.value);
  if (
    !INTERACTIVE_TREE_REVISION_ID_RE.test(revisionId)
    || !INTERACTIVE_TREE_FRONTIER_SOURCE_NODE_ID_RE.test(sourceNodeId)
    || nonEmptyText(revision.dataset?.revisionId) !== revisionId
    || nonEmptyText(frontier.dataset?.revisionId) !== revisionId
    || nonEmptyText(frontier.dataset?.sourceNodeId) !== sourceNodeId
  ) {
    throw new Error("Select a frontier node from the current tree revision.");
  }
  const inputs = {
    revision_id: revisionId,
    source_node_id: sourceNodeId,
  };
  optionalText(
    inputs,
    "selection_reason",
    formValue(form, "interactive_tree_frontier_selection_reason"),
  );
  return inputs;
}

function collectInteractiveTreeFrontierGroupMaterializationInputs(form) {
  const revision = selectedProjectionOption(
    form,
    "interactive_tree_frontier_group_revision_id",
    "Interactive tree revision",
  );
  const revisionId = nonEmptyText(revision.value);
  const nodeSelect = formField(
    form,
    "interactive_tree_frontier_group_source_node_ids",
  );
  const nodeOptions = Array.from(nodeSelect?.selectedOptions || []);
  if (nodeOptions.length < 2 || nodeOptions.length > 50) {
    throw new Error("Select 2–50 frontier nodes for an OR group.");
  }
  const sourceNodeIds = uniqueValues(
    nodeOptions.map((option) => nonEmptyText(option.value)),
    "Frontier nodes for the OR group",
  );
  if (
    !INTERACTIVE_TREE_REVISION_ID_RE.test(revisionId)
    || nonEmptyText(revision.dataset?.revisionId) !== revisionId
    || sourceNodeIds.some((sourceNodeId, index) => {
      const option = nodeOptions[index];
      return (
        option.dataset?.candidateLabProjection !== "1"
        || !INTERACTIVE_TREE_FRONTIER_SOURCE_NODE_ID_RE.test(sourceNodeId)
        || nonEmptyText(option.dataset?.revisionId) !== revisionId
        || nonEmptyText(option.dataset?.sourceNodeId) !== sourceNodeId
      );
    })
  ) {
    throw new Error("Select frontier-group nodes from the current tree revision.");
  }
  const inputs = {
    revision_id: revisionId,
    source_node_ids: sourceNodeIds,
  };
  optionalText(
    inputs,
    "selection_reason",
    formValue(form, "interactive_tree_frontier_group_selection_reason"),
  );
  return inputs;
}

export function collectStrategyCandidateLabRequest(form) {
  const workflow = nonEmptyText(form?.dataset?.candidateLabWorkflow);
  if (!STRATEGY_CANDIDATE_LAB_WORKFLOWS.includes(workflow)) {
    throw new Error("This strategy action is not available.");
  }
  if (workflow === "strategy_lifecycle_adopt") {
    return collectStrategyLifecycleAdoptionRequest(form);
  }
  const workflowInputs = {
    strategy_project_context: collectStrategyProjectContextInputs,
    strategy_sample_design_v2: collectSampleDesignV2Inputs,
    univariate_candidate_analysis: collectUnivariateInputs,
    univariate_candidate_refinement: collectRefinementInputs,
    cross_matrix_analysis: collectCrossInputs,
    cross_matrix_candidate_search: collectCrossCandidateSearchInputs,
    cross_matrix_candidate_build_from_search:
      collectCrossCandidateBuildFromSearchInputs,
    cross_rule_search: collectCrossRuleSearchInputs,
    cross_rule_candidate_build_from_search:
      collectCrossRuleCandidateBuildInputs,
    automatic_tree_candidate_build: collectTreeInputs,
    scorecard_model_score_evidence_build:
      collectScorecardModelScoreEvidenceInputs,
    scorecard_band_build: collectScorecardBandInputs,
    scorecard_cutoff_selection: collectScorecardCutoffSelectionInputs,
    candidate_monthly_stability: collectCandidateMonthlyStabilityInputs,
    strategy_pool_add_candidate: collectStrategyPoolAddCandidateInputs,
    strategy_pool_compile: collectStrategyPoolCompileInputs,
    strategy_pool_remove_entry: collectStrategyPoolRemoveEntryInputs,
    strategy_pool_set_action: collectStrategyPoolSetActionInputs,
    strategy_pool_reorder: collectStrategyPoolReorderInputs,
    strategy_pool_apply: collectStrategyPoolApplyInputs,
    strategy_pool_validation: collectStrategyPoolValidationInputs,
    strategy_pool_stability: collectStrategyPoolStabilityInputs,
    strategy_pool_impact: collectStrategyPoolImpactInputs,
    strategy_impact_cube: collectStrategyImpactCubeInputs,
    strategy_pool_materialize: collectStrategyPoolMaterializeInputs,
    strategy_dsl_delivery: collectStrategyDslDeliveryInputs,
    strategy_report_bundle_v2: collectStrategyReportBundleV2Inputs,
    voting_candidate_search: collectVotingCandidateSearchInputs,
    voting_candidate_build_from_search:
      collectVotingCandidateBuildFromSearchInputs,
    interactive_tree_split_search: collectInteractiveTreeSplitSearchInputs,
    interactive_tree_auto_continuation:
      collectInteractiveTreeAutoContinuationInputs,
    interactive_tree_revision: collectInteractiveTreeRevisionInputs,
    interactive_tree_frontier_group_materialization:
      collectInteractiveTreeFrontierGroupMaterializationInputs,
    interactive_tree_frontier_materialization:
      collectInteractiveTreeFrontierMaterializationInputs,
  }[workflow](form);
  return {
    request_kind: "standard_workflow",
    workflow,
    workflow_inputs: workflowInputs,
  };
}
