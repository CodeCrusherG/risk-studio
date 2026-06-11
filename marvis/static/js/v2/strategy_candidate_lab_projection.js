/** Candidate Lab payload projection, form synchronization, and currentness. */

import { escapeHtml } from "../ui-utils.js";

import {
  CROSS_PAIR_ID_RE,
  CROSS_RULE_ID_RE,
  CROSS_RULE_SEARCH_ID_RE,
  CROSS_SEARCH_ID_RE,
  INTERACTIVE_TREE_NODE_ID_RE,
  INTERACTIVE_TREE_REVISION_ID_RE,
  INTERACTIVE_TREE_SOURCE_ID_RE,
  INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_RE,
  INTERACTIVE_TREE_SPLIT_SEARCH_ID_RE,
  STRATEGY_ID_RE,
  STRATEGY_POOL_ACTION_TYPES,
  STRATEGY_POOL_ADD_SELECTION_RE,
  STRATEGY_POOL_ADD_SOURCE_KINDS,
  STRATEGY_POOL_CANDIDATE_ASSET_ID_RE,
  STRATEGY_POOL_ENTRY_ID_RE,
  STRATEGY_POOL_OPERATION_WORKFLOWS,
  STRATEGY_POOL_TYPES,
  STRATEGY_POOL_VOTING_PLACEMENTS,
  STRATEGY_TYPE_LABELS,
  VOTING_COMBO_ID_RE,
  VOTING_RULE_ID_RE,
  VOTING_SEARCH_ID_RE,
  _MAX_STRATEGY_POOL_ADD_SOURCES,
  collectionItems,
  formField,
  formValue,
  interactiveTreeEligiblePointers,
  interactiveTreeFeatureEligiblePointers,
  interactiveTreeFrontierEligiblePointers,
  interactiveTreeThresholdEligiblePointers,
  isRecord,
  minimalProjectedPoolAction,
  nonEmptyText,
  projectedStrategyItems,
  readableValue,
  stablePrimitiveText,
} from "./strategy_candidate_lab_contracts.js";

export function syncSampleDesignV2StatusControls(form, fieldName) {
  if (!form) return false;
  if (fieldName === "sample_maturity_status") {
    const status = formValue(form, fieldName);
    const reason = formField(form, "sample_maturity_reason");
    if (!reason) return false;
    if (status === "confirmed_matured") {
      reason.value = "";
    } else if (
      ["unknown", "unavailable"].includes(status)
      && !nonEmptyText(reason.value)
    ) {
      reason.value = "Outcome maturity has not been confirmed.";
    }
    return true;
  }
  if (fieldName === "sample_historical_score_status") {
    const status = formValue(form, fieldName);
    const reason = formField(form, "sample_historical_score_reason");
    if (!reason) return false;
    if (status === "available") {
      reason.value = "";
    } else if (!nonEmptyText(reason.value)) {
      reason.value = status === "not_applicable"
        ? "Historical scores are not applicable."
        : "No historical scores are available.";
    }
    return true;
  }
  return false;
}

function refinementForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="univariate_candidate_refinement"]',
  ) || null;
}

function setRefinementPanelVisible(panel, visible) {
  if (!panel) return;
  panel.classList?.toggle?.("hidden", !visible);
  panel.setAttribute?.("aria-hidden", visible ? "false" : "true");
  const controls = panel.querySelectorAll?.("input, select, textarea, button") || [];
  for (const control of controls) control.disabled = !visible;
}

export function syncRefinementMode(form) {
  if (!form) return;
  const mode = formValue(form, "refinement_mode") || "fresh";
  const panels = form.querySelectorAll?.("[data-candidate-lab-refinement-panel]") || [];
  for (const modePanel of panels) {
    setRefinementPanelVisible(
      modePanel,
      modePanel.dataset?.candidateLabRefinementPanel === mode,
    );
  }
}

function univariateProjectionCandidates(payload) {
  const collection = isRecord(payload?.candidates?.univariate)
    ? payload.candidates.univariate
    : {};
  const seen = new Set();
  return collectionItems(collection).filter((item) => {
    const candidateId = nonEmptyText(item.candidate_id);
    if (!candidateId || seen.has(candidateId)) return false;
    seen.add(candidateId);
    return true;
  });
}

export function interactiveTreeForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="interactive_tree_revision"]',
  ) || null;
}

export function interactiveTreeSplitSearchForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="interactive_tree_split_search"]',
  ) || null;
}

function interactiveTreeProjectionSources(payload) {
  const candidates = isRecord(payload?.candidates) ? payload.candidates : {};
  const collections = [
    candidates.automatic_tree,
    candidates.interactive_tree_revision,
  ];
  const seen = new Set();
  return collections.flatMap((collection) => collectionItems(collection))
    .filter((item) => {
      const sourceTreeId = nonEmptyText(item?.detail?.source_tree_id);
      if (
        !INTERACTIVE_TREE_SOURCE_ID_RE.test(sourceTreeId)
        || seen.has(sourceTreeId)
      ) {
        return false;
      }
      seen.add(sourceTreeId);
      return true;
    });
}

export function syncInteractiveTreeSplitSearchControls(
  form,
  payload,
  { preserveNode = true } = {},
) {
  if (!form) return;
  const sourceSelect = formField(
    form,
    "interactive_tree_search_source_id",
  );
  const nodeSelect = formField(form, "interactive_tree_search_node_id");
  if (!sourceSelect || !nodeSelect) return;
  const sources = interactiveTreeProjectionSources(payload);
  const previousSource = nonEmptyText(sourceSelect.value);
  const previousNode = preserveNode ? nonEmptyText(nodeSelect.value) : "";
  sourceSelect.innerHTML = [
    '<option value="">Select a source tree or revision</option>',
    ...sources.map((item) => {
      const sourceTreeId = nonEmptyText(item?.detail?.source_tree_id);
      const featureUniverse = Array.isArray(
        item?.pointers?.feature_universe,
      )
        ? item.pointers.feature_universe.map(nonEmptyText).filter(Boolean)
        : [];
      const visibleCount = (
        Array.isArray(item?.pointers?.nodes)
          ? item.pointers.nodes
          : []
      ).filter((node) => node?.is_visible === true).length;
      return projectionOptionHtml(
        sourceTreeId,
        `${sourceTreeId} · ${visibleCount} visible nodes · ${featureUniverse.length} features`,
        {
          "candidate-lab-projection": "1",
          "source-tree-id": sourceTreeId,
          "feature-universe": featureUniverse.join("\u001f"),
        },
      );
    }),
  ].join("");
  sourceSelect.value = selectContainsValue(sourceSelect, previousSource)
    ? previousSource
    : "";
  const selectedSourceId = nonEmptyText(sourceSelect.value);
  const selectedSource = sources.find(
    (item) => item?.detail?.source_tree_id === selectedSourceId,
  );
  const nodes = (
    Array.isArray(selectedSource?.pointers?.nodes)
      ? selectedSource.pointers.nodes
      : []
  ).filter((node) => (
    isRecord(node)
    && node.is_visible === true
    && INTERACTIVE_TREE_NODE_ID_RE.test(nonEmptyText(node.node_id))
  ));
  nodeSelect.innerHTML = [
    '<option value="">Select a node to analyse</option>',
    ...nodes.map((node) => projectionOptionHtml(
      node.node_id,
      `${node.node_id} · ${node.kind}${node.feature ? ` · ${node.feature} ≤ ${stablePrimitiveText(node.threshold)}` : ""}`,
      {
        "candidate-lab-projection": "1",
        "source-tree-id": selectedSourceId,
        "node-id": node.node_id,
      },
    )),
  ].join("");
  nodeSelect.value = selectContainsValue(nodeSelect, previousNode)
    ? previousNode
    : "";
  const selectedSourceOption = Array.from(
    sourceSelect.selectedOptions || [],
  )[0] || null;
  const featurePanel = form.querySelector?.(
    "[data-candidate-lab-tree-search-features-panel]",
  );
  const selectedMode = formValue(form, "interactive_tree_search_mode")
    || "all_features";
  featurePanel?.classList?.toggle?.(
    "hidden",
    selectedMode !== "selected_features",
  );
  const help = form.querySelector?.(
    "[data-candidate-lab-tree-search-help]",
  );
  if (help) {
    if (!sources.length) {
      help.textContent = "Build a rule tree before continuing.";
    } else if (!selectedSource) {
      help.textContent = "Select a source tree or revision.";
    } else if (!nodes.length) {
      help.textContent = "This tree has no visible nodes to search.";
    } else if (!nodeSelect.value) {
      help.textContent = "Select a node to search.";
    } else {
      const featureCount = nonEmptyText(
        selectedSourceOption?.dataset?.featureUniverse,
      ).split("\u001f").filter(Boolean).length;
      help.textContent = (
        selectedMode === "all_features"
          ? `Search all ${featureCount} available features.`
          : `Select a subset of the ${featureCount} available features.`
      ) + " Review the ranked results before changing the tree.";
    }
  }
}

export function interactiveTreePointer(payload, sourceTreeId, nodeId) {
  return interactiveTreeRevisionPointer(
    payload,
    sourceTreeId,
    nodeId,
    "prune_subtree",
  );
}

function interactiveTreePointersForOperation(item, operation) {
  if (operation === "adjust_split_threshold") {
    return interactiveTreeThresholdEligiblePointers(item);
  }
  if (operation === "replace_split_feature") {
    return interactiveTreeFeatureEligiblePointers(item);
  }
  return interactiveTreeEligiblePointers(item);
}

export function interactiveTreeRevisionPointer(
  payload,
  sourceTreeId,
  nodeId,
  operation,
) {
  const source = interactiveTreeProjectionSources(payload).find(
    (item) => item?.detail?.source_tree_id === sourceTreeId,
  );
  if (!source) return null;
  return interactiveTreePointersForOperation(source, operation).find(
    (pointer) => pointer.node_id === nodeId,
  ) || null;
}

export function interactiveTreeRevisionRequestIsCurrent(payload, inputs) {
  if (!isRecord(inputs)) return false;
  const operation = nonEmptyText(inputs.operation);
  const pointer = interactiveTreeRevisionPointer(
    payload,
    nonEmptyText(inputs.source_tree_id),
    nonEmptyText(inputs.node_id),
    operation,
  );
  if (!pointer) return false;
  if (operation === "prune_subtree") {
    return (
      !Object.prototype.hasOwnProperty.call(inputs, "feature")
      && !Object.prototype.hasOwnProperty.call(inputs, "threshold")
    );
  }
  if (
    operation !== "adjust_split_threshold"
    && operation !== "replace_split_feature"
  ) return false;
  const threshold = Number(inputs.threshold);
  if (
    typeof inputs.threshold !== "number"
    || !Number.isFinite(threshold)
  ) return false;
  if (operation === "adjust_split_threshold") {
    return threshold !== Number(pointer.current_threshold);
  }
  const source = interactiveTreeProjectionSources(payload).find(
    (item) => item?.detail?.source_tree_id === inputs.source_tree_id,
  );
  const features = new Set(
    (Array.isArray(source?.pointers?.feature_universe)
      ? source.pointers.feature_universe
      : [])
      .map(nonEmptyText)
      .filter(Boolean),
  );
  return (
    typeof inputs.feature === "string"
    && features.has(inputs.feature)
    && inputs.feature !== pointer.current_feature
    && (
      threshold !== Number(pointer.current_threshold)
      || inputs.feature !== pointer.current_feature
    )
  );
}

export function interactiveTreeSplitSearchRequestIsCurrent(payload, inputs) {
  if (!isRecord(inputs)) return false;
  const sourceTreeId = nonEmptyText(inputs.source_tree_id);
  const nodeId = nonEmptyText(inputs.node_id);
  const source = interactiveTreeProjectionSources(payload).find(
    (item) => item?.detail?.source_tree_id === sourceTreeId,
  );
  const node = (
    Array.isArray(source?.pointers?.nodes)
      ? source.pointers.nodes
      : []
  ).find((item) => (
    item?.node_id === nodeId && item?.is_visible === true
  ));
  const featureUniverse = new Set(
    (Array.isArray(source?.pointers?.feature_universe)
      ? source.pointers.feature_universe
      : [])
      .map(nonEmptyText)
      .filter(Boolean),
  );
  if (
    !source
    || !node
    || !Number.isInteger(inputs.max_thresholds_per_feature)
    || inputs.max_thresholds_per_feature < 1
    || inputs.max_thresholds_per_feature > 20
    || !Number.isInteger(inputs.max_row_evaluations)
    || inputs.max_row_evaluations < 1
    || inputs.max_row_evaluations > 20000000
  ) return false;
  if (inputs.mode === "all_features") {
    return !Object.prototype.hasOwnProperty.call(inputs, "features");
  }
  return (
    inputs.mode === "selected_features"
    && Array.isArray(inputs.features)
    && inputs.features.length > 0
    && inputs.features.length <= 50
    && new Set(inputs.features).size === inputs.features.length
    && inputs.features.every((feature) => featureUniverse.has(feature))
  );
}

export function interactiveTreeSplitCandidatePointer(
  payload,
  searchId,
  candidateId,
) {
  const searches = collectionItems(
    payload?.candidates?.interactive_tree_split_search,
  );
  const search = searches.find((item) => (
    item?.kind === "interactive_tree_split_search"
    && item?.search_id === searchId
    && INTERACTIVE_TREE_SPLIT_SEARCH_ID_RE.test(searchId)
  ));
  const candidate = (
    Array.isArray(search?.candidates) ? search.candidates : []
  ).find((item) => (
    item?.candidate_id === candidateId
    && item?.eligible === true
    && INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_RE.test(candidateId)
  ));
  return search && candidate ? { search, candidate } : null;
}

export function syncInteractiveTreeRevisionControls(
  form,
  payload,
  {
    requestedOperation = "",
    requestedSourceTreeId = "",
    requestedNodeId = "",
    preserveNode = true,
  } = {},
) {
  if (!form) return;
  const operationField = formField(form, "interactive_tree_operation");
  const sourceSelect = formField(form, "interactive_tree_source_id");
  const nodeSelect = formField(form, "interactive_tree_node_id");
  if (!sourceSelect || !nodeSelect) return;
  const allowedOperations = [
    "prune_subtree",
    "adjust_split_threshold",
    "replace_split_feature",
  ];
  const requested = nonEmptyText(requestedOperation);
  if (operationField && allowedOperations.includes(requested)) {
    operationField.value = requested;
  }
  const operation = allowedOperations.includes(formValue(
    form,
    "interactive_tree_operation",
  ))
    ? formValue(form, "interactive_tree_operation")
    : "prune_subtree";
  const sources = interactiveTreeProjectionSources(payload);
  const previousSource = nonEmptyText(sourceSelect.value);
  const previousNode = preserveNode ? nonEmptyText(nodeSelect.value) : "";
  const previousNodeOption = Array.from(
    nodeSelect.selectedOptions || [],
  )[0] || null;
  const previousPointerIdentity = previousNodeOption
    ? [
      nonEmptyText(previousNodeOption.dataset?.sourceTreeId),
      nonEmptyText(previousNodeOption.dataset?.nodeId),
      nonEmptyText(previousNodeOption.dataset?.operation),
      nonEmptyText(previousNodeOption.dataset?.currentThreshold),
    ].join("\u001f")
    : "";
  const thresholdField = formField(form, "interactive_tree_threshold");
  const previousThreshold = String(thresholdField?.value ?? "");
  sourceSelect.innerHTML = [
    '<option value="">Select a source tree or revision</option>',
    ...sources.map((item) => {
      const sourceTreeId = nonEmptyText(item?.detail?.source_tree_id);
      const eligibleCount = interactiveTreePointersForOperation(
        item,
        operation,
      ).length;
      const type = item?.kind === "interactive_tree_revision"
        ? "revision"
        : "automatic";
      const pointerLabel = operation === "adjust_split_threshold"
        ? "nodes with adjustable thresholds"
        : (
          operation === "replace_split_feature"
            ? "nodes with replaceable features"
            : "prunable nodes"
        );
      return projectionOptionHtml(
        sourceTreeId,
        `${sourceTreeId} · ${type} · ${eligibleCount} ${pointerLabel}`,
        {
          "candidate-lab-projection": "1",
          "source-tree-id": sourceTreeId,
        },
      );
    }),
  ].join("");
  const preferredSource = nonEmptyText(requestedSourceTreeId) || previousSource;
  if (selectContainsValue(sourceSelect, preferredSource)) {
    sourceSelect.value = preferredSource;
  } else {
    sourceSelect.value = "";
  }

  const selectedSourceId = nonEmptyText(sourceSelect.value);
  const selectedSource = sources.find(
    (item) => item?.detail?.source_tree_id === selectedSourceId,
  );
  const pointers = selectedSource
    ? interactiveTreePointersForOperation(selectedSource, operation)
    : [];
  nodeSelect.innerHTML = [
    '<option value="">Select a split node</option>',
    ...pointers.map((pointer) => {
      const node = selectedSource?.pointers?.nodes?.find?.(
        (item) => item?.node_id === pointer.node_id,
      );
      const label = node?.feature
        ? `${pointer.node_id} · ${node.feature} ≤ ${stablePrimitiveText(node.threshold)}`
        : pointer.node_id;
      return projectionOptionHtml(
        pointer.node_id,
        label,
        {
          "candidate-lab-projection": "1",
          "source-tree-id": pointer.source_tree_id,
          "node-id": pointer.node_id,
          operation,
          ...(operation !== "prune_subtree"
            ? {
              feature: pointer.feature || pointer.current_feature,
              "current-threshold": stablePrimitiveText(
                pointer.current_threshold,
              ),
            }
            : {}),
        },
      );
    }),
  ].join("");
  const preferredNode = nonEmptyText(requestedNodeId) || previousNode;
  if (selectContainsValue(nodeSelect, preferredNode)) {
    nodeSelect.value = preferredNode;
  } else {
    nodeSelect.value = "";
  }
  const selectedNodeOption = Array.from(
    nodeSelect.selectedOptions || [],
  )[0] || null;
  const selectedPointerIdentity = selectedNodeOption
    ? [
      nonEmptyText(selectedNodeOption.dataset?.sourceTreeId),
      nonEmptyText(selectedNodeOption.dataset?.nodeId),
      nonEmptyText(selectedNodeOption.dataset?.operation),
      nonEmptyText(selectedNodeOption.dataset?.currentThreshold),
    ].join("\u001f")
    : "";
  const isThresholdAdjustment = operation === "adjust_split_threshold";
  const isFeatureReplacement = operation === "replace_split_feature";
  const isSplitAdjustment = (
    isThresholdAdjustment || isFeatureReplacement
  );
  const thresholdPanel = form.querySelector?.(
    "[data-candidate-lab-tree-threshold-panel]",
  );
  thresholdPanel?.classList?.toggle?.("hidden", !isSplitAdjustment);
  const thresholdFeature = form.querySelector?.(
    "[data-candidate-lab-tree-threshold-feature]",
  );
  if (thresholdFeature) {
    thresholdFeature.textContent = isSplitAdjustment
      ? nonEmptyText(selectedNodeOption?.dataset?.feature) || "Select a node first"
      : "—";
  }
  const currentThreshold = form.querySelector?.(
    "[data-candidate-lab-tree-current-threshold]",
  );
  if (currentThreshold) {
    currentThreshold.textContent = isSplitAdjustment
      ? nonEmptyText(selectedNodeOption?.dataset?.currentThreshold)
        || "Select a node first"
      : "—";
  }
  if (thresholdField) {
    thresholdField.value = (
      isSplitAdjustment
      && previousPointerIdentity
      && previousPointerIdentity === selectedPointerIdentity
    )
      ? previousThreshold
      : "";
  }
  const featurePanel = form.querySelector?.(
    "[data-candidate-lab-tree-feature-panel]",
  );
  featurePanel?.classList?.toggle?.("hidden", !isFeatureReplacement);
  const featureField = formField(form, "interactive_tree_feature");
  if (featureField) {
    const currentFeature = nonEmptyText(
      selectedNodeOption?.dataset?.feature,
    );
    const featureUniverse = Array.isArray(
      selectedSource?.pointers?.feature_universe,
    )
      ? selectedSource.pointers.feature_universe
        .map(nonEmptyText)
        .filter((feature) => feature && feature !== currentFeature)
      : [];
    featureField.innerHTML = [
      '<option value="">Select a feature</option>',
      ...featureUniverse.map((feature) => projectionOptionHtml(
        feature,
        feature,
        {
          "candidate-lab-projection": "1",
          "source-tree-id": selectedSourceId,
        },
      )),
    ].join("");
  }
  const help = form.querySelector?.("[data-candidate-lab-tree-help]");
  if (help) {
    if (!sources.length) {
      help.textContent = "Build a rule tree before continuing.";
    } else if (!selectedSource) {
      help.textContent = "Select a source tree or revision.";
    } else if (!pointers.length) {
      help.textContent = isThresholdAdjustment
        ? "This branch has no nodes with adjustable thresholds."
        : "This branch has no eligible split nodes.";
    } else if (!selectedNodeOption) {
      help.textContent = "Select the split node to modify.";
    } else if (isFeatureReplacement) {
      help.textContent = "Select a replacement feature and enter a finite threshold. Confirmation creates a new revision.";
    } else if (isThresholdAdjustment) {
      help.textContent = `Current ${nonEmptyText(
        selectedNodeOption.dataset?.feature,
      )} threshold: ${nonEmptyText(
        selectedNodeOption.dataset?.currentThreshold,
      )}. Enter a different threshold to create a new revision.`;
    } else {
      help.textContent = "Confirmation creates a new revision. Add its candidates to a strategy pool in a separate step.";
    }
  }
}

export function interactiveTreeFrontierMaterializationForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="interactive_tree_frontier_materialization"]',
  ) || null;
}

export function interactiveTreeFrontierGroupMaterializationForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="interactive_tree_frontier_group_materialization"]',
  ) || null;
}

function interactiveTreeFrontierProjectionSources(payload) {
  const collection = payload?.candidates?.interactive_tree_revision;
  const seen = new Set();
  return collectionItems(collection).filter((item) => {
    const revisionId = nonEmptyText(item?.detail?.revision_id);
    if (
      item?.kind !== "interactive_tree_revision"
      || !INTERACTIVE_TREE_REVISION_ID_RE.test(revisionId)
      || seen.has(revisionId)
    ) {
      return false;
    }
    seen.add(revisionId);
    return true;
  });
}

export function interactiveTreeFrontierPointer(payload, revisionId, sourceNodeId) {
  const source = interactiveTreeFrontierProjectionSources(payload).find(
    (item) => item?.detail?.revision_id === revisionId,
  );
  if (!source) return null;
  return interactiveTreeFrontierEligiblePointers(source).find(
    (pointer) => pointer.source_node_id === sourceNodeId,
  ) || null;
}

export function interactiveTreeFrontierGroupPointers(
  payload,
  revisionId,
  sourceNodeIds,
) {
  if (
    !Array.isArray(sourceNodeIds)
    || sourceNodeIds.length < 2
    || sourceNodeIds.length > 50
    || new Set(sourceNodeIds).size !== sourceNodeIds.length
  ) {
    return [];
  }
  const source = interactiveTreeFrontierProjectionSources(payload).find(
    (item) => item?.detail?.revision_id === revisionId,
  );
  if (!source) return [];
  const byId = new Map(
    interactiveTreeFrontierEligiblePointers(source).map(
      (pointer) => [pointer.source_node_id, pointer],
    ),
  );
  const pointers = sourceNodeIds.map((sourceNodeId) => byId.get(sourceNodeId));
  return pointers.every(Boolean) ? pointers : [];
}

export function syncInteractiveTreeFrontierMaterializationControls(
  form,
  payload,
  {
    requestedRevisionId = "",
    requestedSourceNodeId = "",
    preserveNode = true,
  } = {},
) {
  if (!form) return;
  const revisionSelect = formField(
    form,
    "interactive_tree_frontier_revision_id",
  );
  const nodeSelect = formField(
    form,
    "interactive_tree_frontier_source_node_id",
  );
  if (!revisionSelect || !nodeSelect) return;
  const revisions = interactiveTreeFrontierProjectionSources(payload);
  const previousRevision = nonEmptyText(revisionSelect.value);
  revisionSelect.innerHTML = [
    '<option value="">Select a tree revision</option>',
    ...revisions.map((item) => {
      const revisionId = nonEmptyText(item?.detail?.revision_id);
      const frontierCount = interactiveTreeFrontierEligiblePointers(item).length;
      return projectionOptionHtml(
        revisionId,
        `${revisionId} · ${frontierCount} available frontier nodes`,
        {
          "candidate-lab-projection": "1",
          "revision-id": revisionId,
        },
      );
    }),
  ].join("");
  const preferredRevision = (
    nonEmptyText(requestedRevisionId) || previousRevision
  );
  if (selectContainsValue(revisionSelect, preferredRevision)) {
    revisionSelect.value = preferredRevision;
  } else if (revisions.length) {
    revisionSelect.value = nonEmptyText(revisions[0]?.detail?.revision_id);
  }

  const revisionId = nonEmptyText(revisionSelect.value);
  const selectedRevision = revisions.find(
    (item) => item?.detail?.revision_id === revisionId,
  );
  const pointers = selectedRevision
    ? interactiveTreeFrontierEligiblePointers(selectedRevision)
    : [];
  const previousNode = preserveNode ? nonEmptyText(nodeSelect.value) : "";
  nodeSelect.innerHTML = [
    '<option value="">Select a frontier node</option>',
    ...pointers.map((pointer) => {
      const sourceNodeId = nonEmptyText(pointer.source_node_id);
      const node = selectedRevision?.pointers?.nodes?.find?.(
        (item) => item?.node_id === sourceNodeId,
      );
      const label = node?.condition
        ? `${sourceNodeId} · ${readableValue(node.condition)}`
        : sourceNodeId;
      return projectionOptionHtml(
        sourceNodeId,
        label,
        {
          "candidate-lab-projection": "1",
          "revision-id": revisionId,
          "source-node-id": sourceNodeId,
        },
      );
    }),
  ].join("");
  const preferredNode = nonEmptyText(requestedSourceNodeId) || previousNode;
  if (selectContainsValue(nodeSelect, preferredNode)) {
    nodeSelect.value = preferredNode;
  } else if (pointers.length) {
    nodeSelect.value = nonEmptyText(pointers[0]?.source_node_id);
  }
  const help = form.querySelector?.(
    "[data-candidate-lab-interactive-tree-frontier-help]",
  );
  if (help) {
    help.textContent = revisions.length
      ? pointers.length
        ? "Create one candidate from the selected frontier node, then add it to a pool separately."
        : "This revision has no eligible frontier nodes."
      : "Create a tree revision before continuing.";
  }
}

export function syncInteractiveTreeFrontierGroupMaterializationControls(
  form,
  payload,
  { preserveNodes = true } = {},
) {
  if (!form) return;
  const revisionSelect = formField(
    form,
    "interactive_tree_frontier_group_revision_id",
  );
  const nodeSelect = formField(
    form,
    "interactive_tree_frontier_group_source_node_ids",
  );
  if (!revisionSelect || !nodeSelect) return;
  const revisions = interactiveTreeFrontierProjectionSources(payload);
  const previousRevision = nonEmptyText(revisionSelect.value);
  revisionSelect.innerHTML = [
    '<option value="">Select a tree revision</option>',
    ...revisions.map((item) => {
      const revisionId = nonEmptyText(item?.detail?.revision_id);
      const frontierCount = interactiveTreeFrontierEligiblePointers(item).length;
      return projectionOptionHtml(
        revisionId,
        `${revisionId} · ${frontierCount} frontier nodes available for grouping`,
        {
          "candidate-lab-projection": "1",
          "revision-id": revisionId,
        },
      );
    }),
  ].join("");
  if (
    previousRevision
    && selectContainsValue(revisionSelect, previousRevision)
  ) {
    revisionSelect.value = previousRevision;
  } else if (revisions.length) {
    revisionSelect.value = nonEmptyText(revisions[0]?.detail?.revision_id);
  }

  const revisionId = nonEmptyText(revisionSelect.value);
  const selectedRevision = revisions.find(
    (item) => item?.detail?.revision_id === revisionId,
  );
  const pointers = selectedRevision
    ? interactiveTreeFrontierEligiblePointers(selectedRevision)
    : [];
  const previousNodeIds = preserveNodes
    ? new Set(selectedValues(nodeSelect))
    : new Set();
  nodeSelect.innerHTML = pointers.map((pointer) => {
    const sourceNodeId = nonEmptyText(pointer.source_node_id);
    const node = selectedRevision?.pointers?.nodes?.find?.(
      (item) => item?.node_id === sourceNodeId,
    );
    const label = node?.condition
      ? `${sourceNodeId} · ${readableValue(node.condition)}`
      : sourceNodeId;
    return projectionOptionHtml(
      sourceNodeId,
      label,
      {
        "candidate-lab-projection": "1",
        "revision-id": revisionId,
        "source-node-id": sourceNodeId,
      },
    );
  }).join("");
  for (const option of Array.from(nodeSelect.options || [])) {
    option.selected = previousNodeIds.has(option.value);
  }
  const help = form.querySelector?.(
    "[data-candidate-lab-interactive-tree-frontier-group-help]",
  );
  if (help) {
    help.textContent = revisions.length
      ? pointers.length >= 2
        ? "Hold Command or Ctrl to select 2–50 nodes for an OR group. Add the group to a pool separately."
        : "An OR group requires at least two eligible frontier nodes."
      : "Create a tree revision before continuing.";
  }
}

function univariateCandidatePairs(candidate) {
  const bins = Array.isArray(candidate?.pointers?.bins)
    ? candidate.pointers.bins.filter(isRecord)
    : [];
  const seen = new Set();
  return bins.reduce((pairs, bin) => {
    const feature = nonEmptyText(bin.feature);
    const method = nonEmptyText(bin.method);
    const key = `${feature}\u001f${method}`;
    if (!feature || !method || seen.has(key)) return pairs;
    seen.add(key);
    pairs.push({ feature, method });
    return pairs;
  }, []);
}

function projectionOptionHtml(value, label, data = {}) {
  const attributes = Object.entries(data)
    .map(([key, item]) => ` data-${key}="${escapeHtml(item)}"`)
    .join("");
  return `<option value="${escapeHtml(value)}"${attributes}>${escapeHtml(label)}</option>`;
}

export function selectContainsValue(select, value) {
  return Array.from(select?.options || []).some((option) => option.value === value);
}

function selectedValues(select) {
  return Array.from(select?.selectedOptions || [])
    .map((option) => nonEmptyText(option.value))
    .filter(Boolean);
}

export function syncRefinementCandidateControls(form, payload, { preserveBins = true } = {}) {
  if (!form) return;
  const candidates = univariateProjectionCandidates(payload);
  const sourceSelect = formField(form, "source_candidate_id");
  const pairSelect = formField(form, "source_feature_method");
  const binSelect = formField(form, "source_bin_ids");
  if (!sourceSelect || !pairSelect || !binSelect) return;

  const previousCandidateId = nonEmptyText(sourceSelect.value);
  sourceSelect.innerHTML = [
    '<option value="">Select a candidate</option>',
    ...candidates.map((candidate) => {
      const candidateId = nonEmptyText(candidate.candidate_id);
      const binCount = Array.isArray(candidate?.pointers?.bins)
        ? candidate.pointers.bins.length
        : 0;
      return projectionOptionHtml(
        candidateId,
        `${candidateId} · ${binCount} visible bins`,
        { "candidate-lab-projection": "1" },
      );
    }),
  ].join("");
  if (selectContainsValue(sourceSelect, previousCandidateId)) {
    sourceSelect.value = previousCandidateId;
  } else if (candidates.length) {
    sourceSelect.value = nonEmptyText(candidates[0].candidate_id);
  }

  const candidateId = nonEmptyText(sourceSelect.value);
  const candidate = candidates.find((item) => item.candidate_id === candidateId);
  const pairs = univariateCandidatePairs(candidate);
  const previousPairValue = nonEmptyText(pairSelect.value);
  pairSelect.innerHTML = [
    '<option value="">Select a feature and method</option>',
    ...pairs.map(({ feature, method }, index) => projectionOptionHtml(
      `pair-${index}`,
      `${feature} · ${method}`,
      {
        "candidate-lab-projection": "1",
        "source-candidate-id": candidateId,
        feature,
        method,
      },
    )),
  ].join("");
  if (selectContainsValue(pairSelect, previousPairValue)) {
    pairSelect.value = previousPairValue;
  } else if (pairs.length) {
    pairSelect.value = "pair-0";
  }

  const pairOption = Array.from(pairSelect.selectedOptions || [])[0] || null;
  const feature = nonEmptyText(pairOption?.dataset?.feature);
  const method = nonEmptyText(pairOption?.dataset?.method);
  const previousBinIds = preserveBins ? new Set(selectedValues(binSelect)) : new Set();
  const bins = Array.isArray(candidate?.pointers?.bins)
    ? candidate.pointers.bins.filter((bin) => (
      isRecord(bin)
      && bin.feature === feature
      && bin.method === method
      && nonEmptyText(bin.bin_id)
    ))
    : [];
  binSelect.innerHTML = bins.map((bin) => projectionOptionHtml(
    nonEmptyText(bin.bin_id),
    `${nonEmptyText(bin.bin_id)} · ${readableValue(bin.condition)}`,
    {
      "candidate-lab-projection": "1",
      "source-candidate-id": candidateId,
      feature,
      method,
    },
  )).join("");
  for (const option of Array.from(binSelect.options || [])) {
    option.selected = previousBinIds.has(option.value);
  }

  const empty = form.querySelector?.("[data-candidate-lab-refinement-empty]");
  if (empty) {
    empty.textContent = candidates.length
      ? bins.length
        ? "Hold Command or Ctrl to select multiple bins."
        : "No bins are available for this candidate, feature and method."
      : "Run univariate analysis to create a candidate.";
  }
}

export function syncRefinementForm(root, payload, options = {}) {
  const form = refinementForm(root);
  if (!form) return;
  syncRefinementMode(form);
  syncRefinementCandidateControls(form, payload, options);
}

function scorecardBandBuildForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="scorecard_band_build"]',
  ) || null;
}

function scorecardCutoffSelectionForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="scorecard_cutoff_selection"]',
  ) || null;
}

function setScorecardBandingPanelVisible(panel, visible) {
  if (!panel) return;
  panel.classList?.toggle?.("hidden", !visible);
  panel.setAttribute?.("aria-hidden", visible ? "false" : "true");
  const controls = panel.querySelectorAll?.("input, select, textarea, button") || [];
  for (const control of controls) control.disabled = !visible;
}

export function syncScorecardBandingMode(form) {
  if (!form) return;
  const mode = formValue(form, "scorecard_banding_mode") || "equal_frequency";
  const panels = form.querySelectorAll?.(
    "[data-candidate-lab-scorecard-banding-panel]",
  ) || [];
  for (const modePanel of panels) {
    setScorecardBandingPanelVisible(
      modePanel,
      modePanel.dataset?.candidateLabScorecardBandingPanel === mode,
    );
  }
}

function scorecardBandProjectionCandidates(payload) {
  const collection = isRecord(payload?.candidates?.scorecard_band)
    ? payload.candidates.scorecard_band
    : {};
  const seen = new Set();
  return collectionItems(collection).filter((item) => {
    const assetId = nonEmptyText(item?.detail?.asset_id);
    if (
      !/^scorecard-band-asset-[0-9a-f]{32}$/.test(assetId)
      || seen.has(assetId)
    ) {
      return false;
    }
    seen.add(assetId);
    return true;
  });
}

function scorecardProjectionCutoffs(candidate) {
  const rows = Array.isArray(candidate?.pointers?.cutoffs)
    ? candidate.pointers.cutoffs.filter(isRecord)
    : [];
  const seen = new Set();
  return rows.filter((row) => {
    const cutoffId = nonEmptyText(row.cutoff_id);
    if (
      !/^scorecard-cutoff-[0-9a-f]{32}$/.test(cutoffId)
      || seen.has(cutoffId)
    ) {
      return false;
    }
    seen.add(cutoffId);
    return true;
  });
}

export function syncScorecardCutoffControls(
  form,
  payload,
  { preserveCutoff = true } = {},
) {
  if (!form) return;
  const candidates = scorecardBandProjectionCandidates(payload);
  const assetSelect = formField(form, "scorecard_asset_id");
  const cutoffSelect = formField(form, "scorecard_cutoff_id");
  if (!assetSelect || !cutoffSelect) return;

  const previousAssetId = nonEmptyText(assetSelect.value);
  assetSelect.innerHTML = [
    '<option value="">Select a scorecard analysis</option>',
    ...candidates.map((candidate) => {
      const assetId = nonEmptyText(candidate?.detail?.asset_id);
      const cutoffCount = scorecardProjectionCutoffs(candidate).length;
      return projectionOptionHtml(
        assetId,
        `${assetId} · ${cutoffCount} available cutoffs`,
        { "candidate-lab-projection": "1" },
      );
    }),
  ].join("");
  if (selectContainsValue(assetSelect, previousAssetId)) {
    assetSelect.value = previousAssetId;
  } else {
    assetSelect.value = "";
  }

  const assetId = nonEmptyText(assetSelect.value);
  const candidate = candidates.find(
    (item) => nonEmptyText(item?.detail?.asset_id) === assetId,
  );
  const cutoffs = scorecardProjectionCutoffs(candidate);
  const previousCutoffId = nonEmptyText(cutoffSelect.value);
  const previousCutoffSource = nonEmptyText(
    Array.from(cutoffSelect.selectedOptions || [])[0]?.dataset?.sourceAssetId,
  );
  cutoffSelect.innerHTML = [
    '<option value="">Select a cutoff</option>',
    ...cutoffs.map((cutoff) => {
      const cutoffId = nonEmptyText(cutoff.cutoff_id);
      const pd = stablePrimitiveText(cutoff.execution_pd);
      const points = stablePrimitiveText(cutoff.display_points);
      return projectionOptionHtml(
        cutoffId,
        `${cutoffId} · PD ${pd} · ${points} min`,
        {
          "candidate-lab-projection": "1",
          "source-asset-id": assetId,
        },
      );
    }),
  ].join("");
  if (
    preserveCutoff
    && previousCutoffSource === assetId
    && selectContainsValue(cutoffSelect, previousCutoffId)
  ) {
    cutoffSelect.value = previousCutoffId;
  } else {
    cutoffSelect.value = "";
  }

  const empty = form.querySelector?.("[data-candidate-lab-scorecard-empty]");
  if (empty) {
    empty.textContent = candidates.length
      ? assetId
        ? cutoffs.length
          ? "Select a cutoff from this scorecard analysis."
          : "No cutoffs are available for this scorecard analysis."
        : "Select a scorecard analysis from this task."
      : "Run scorecard analysis before continuing.";
  }
}

export function syncScorecardForms(root, payload) {
  syncScorecardBandingMode(scorecardBandBuildForm(root));
  syncScorecardCutoffControls(
    scorecardCutoffSelectionForm(root),
    payload,
  );
}

export function candidateStabilityForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="candidate_monthly_stability"]',
  ) || null;
}

function setCandidateStabilityPanelVisible(panel, visible) {
  if (!panel) return;
  panel.classList?.toggle?.("hidden", !visible);
  panel.setAttribute?.("aria-hidden", visible ? "false" : "true");
  const controls = panel.querySelectorAll?.("input, select, textarea, button") || [];
  for (const control of controls) control.disabled = !visible;
}

function candidateStabilityPoolOptions(payload) {
  const pools = collectionItems(isRecord(payload?.pools) ? payload.pools : {});
  const result = [];
  for (const pool of pools) {
    const strategyType = nonEmptyText(pool?.strategy_type);
    if (!["approval", "reject", "limit", "pricing", "segmentation"].includes(
      strategyType,
    )) {
      continue;
    }
    for (const entry of Array.isArray(pool?.entries) ? pool.entries : []) {
      const entryId = nonEmptyText(entry?.entry_id);
      if (!/^pool-entry-[0-9a-f]{32}$/.test(entryId)) continue;
      result.push({
        entryId,
        strategyType,
        ruleId: nonEmptyText(entry.rule_id),
        assetId: nonEmptyText(entry?.source?.asset_id),
        assetType: nonEmptyText(entry?.source?.asset_type),
      });
    }
  }
  return result;
}

export function syncCandidateStabilityControls(form, payload) {
  if (!form) return;
  const mode = formValue(form, "stability_source_mode") || "pool_entry";
  const panels = form.querySelectorAll?.(
    "[data-candidate-lab-stability-panel]",
  ) || [];
  for (const modePanel of panels) {
    setCandidateStabilityPanelVisible(
      modePanel,
      modePanel.dataset?.candidateLabStabilityPanel === mode,
    );
  }

  const entries = candidateStabilityPoolOptions(payload);
  const entrySelect = formField(form, "stability_pool_entry");
  if (entrySelect) {
    const previousEntry = nonEmptyText(entrySelect.value);
    entrySelect.innerHTML = [
      '<option value="">Select a pool entry</option>',
      ...entries.map((entry) => projectionOptionHtml(
        entry.entryId,
        `${entry.strategyType} · ${entry.ruleId || entry.entryId} · ${entry.assetType || "candidate"}`,
        {
          "candidate-lab-projection": "1",
          "strategy-type": entry.strategyType,
        },
      )),
    ].join("");
    entrySelect.value = selectContainsValue(entrySelect, previousEntry)
      ? previousEntry
      : "";
  }

  const assets = [];
  const seenAssets = new Set();
  for (const entry of entries) {
    if (
      entry.assetType !== "univariate_refinement"
      || !/^candidate-asset-[0-9a-f]{32}$/.test(entry.assetId)
      || seenAssets.has(entry.assetId)
    ) {
      continue;
    }
    seenAssets.add(entry.assetId);
    assets.push(entry);
  }
  const assetSelect = formField(form, "stability_asset_id");
  if (assetSelect) {
    const previousAsset = nonEmptyText(assetSelect.value);
    assetSelect.innerHTML = [
      '<option value="">Select a univariate candidate from the pool</option>',
      ...assets.map((entry) => projectionOptionHtml(
        entry.assetId,
        `${entry.assetId} · ${entry.strategyType}`,
        { "candidate-lab-projection": "1" },
      )),
    ].join("");
    assetSelect.value = selectContainsValue(assetSelect, previousAsset)
      ? previousAsset
      : "";
  }

  const empty = form.querySelector?.("[data-candidate-lab-stability-empty]");
  if (empty) {
    empty.textContent = entries.length
      ? "Select a source. The analysis uses the current pool revision, sample and month definitions."
      : "No pool entries are available for measurement.";
  }
}

export function strategyPoolApplyForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_pool_apply"]',
  ) || null;
}

export function strategyPoolAddForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_pool_add_candidate"]',
  ) || null;
}

function strategyPoolAddCurrentPools(payload) {
  const operationPools = strategyPoolOperationPools(payload);
  const rawPools = collectionItems(
    isRecord(payload?.pools) ? payload.pools : {},
  );
  return operationPools.flatMap((pool) => {
    const matches = rawPools.filter((item) => (
      item?.kind === "candidate_pool"
      && nonEmptyText(item?.strategy_type) === pool.strategyType
    ));
    if (matches.length !== 1) return [];
    const defaultAction = minimalProjectedPoolAction(
      matches[0].default_action,
      pool.strategyType,
    );
    if (!defaultAction) return [];
    return [{ ...pool, defaultAction }];
  });
}

function strategyPoolAddSourcePointer(source) {
  if (!isRecord(source)) return null;
  const sourceKind = nonEmptyText(source.source_kind);
  const pointerKind = STRATEGY_POOL_ADD_SOURCE_KINDS[sourceKind];
  if (!pointerKind) return null;
  const keys = Object.keys(source).sort();
  const expectedKeys = [
    "candidate_stage",
    pointerKind,
    "source_kind",
    "strategy_type",
    "validation_status",
  ].sort();
  if (
    keys.length !== expectedKeys.length
    || keys.some((key, index) => key !== expectedKeys[index])
  ) {
    return null;
  }
  const sourceId = nonEmptyText(source[pointerKind]);
  const selectionPrefix = {
    automatic_tree_leaf_selection: "automatic-tree-leaf-selection-",
    interactive_tree_frontier_selection:
      "interactive-tree-frontier-selection-",
    interactive_tree_frontier_group_selection:
      "interactive-tree-frontier-group-selection-",
    cross_matrix_cell_selection: "cross-matrix-cell-selection-",
    scorecard_cutoff_selection: "scorecard-cutoff-selection-",
  }[sourceKind];
  if (
    pointerKind === "candidate_asset_id"
      ? !STRATEGY_POOL_CANDIDATE_ASSET_ID_RE.test(sourceId)
      : (
        !STRATEGY_POOL_ADD_SELECTION_RE.test(sourceId)
        || !sourceId.startsWith(selectionPrefix)
      )
  ) {
    return null;
  }
  const strategyType = source.strategy_type === null
    ? ""
    : nonEmptyText(source.strategy_type);
  if (
    sourceKind === "voting_candidate"
      ? !STRATEGY_POOL_TYPES.includes(strategyType)
      : strategyType
  ) {
    return null;
  }
  if (
    !nonEmptyText(source.candidate_stage)
    || !nonEmptyText(source.validation_status)
  ) {
    return null;
  }
  return {
    sourceKind,
    pointerKind,
    sourceId,
    strategyType,
    candidateStage: nonEmptyText(source.candidate_stage),
    validationStatus: nonEmptyText(source.validation_status),
  };
}

function strategyPoolAddRawSourceIdentity(source) {
  if (!isRecord(source)) return "";
  const sourceKind = nonEmptyText(source.source_kind);
  const candidateAssetId = nonEmptyText(source.candidate_asset_id);
  const selectionId = nonEmptyText(source.selection_id);
  if (
    !sourceKind
    || Boolean(candidateAssetId) === Boolean(selectionId)
  ) return "";
  return `${sourceKind}\u001f${candidateAssetId || selectionId}`;
}

function strategyPoolAddSourceIsUnsupported(source) {
  if (!isRecord(source)) return false;
  const sourceKind = nonEmptyText(source.source_kind);
  return Boolean(sourceKind) && !Object.hasOwn(
    STRATEGY_POOL_ADD_SOURCE_KINDS,
    sourceKind,
  );
}

function strategyPoolAddSources(payload) {
  const collection = isRecord(payload?.pool_add_sources)
    ? payload.pool_add_sources
    : null;
  if (
    !collection
    || !Array.isArray(collection.all)
    || !Number.isInteger(collection.total)
    || collection.total < collection.all.length
    || collection.all.length > _MAX_STRATEGY_POOL_ADD_SOURCES
    || collection.truncated !== (collection.total > collection.all.length)
  ) {
    return [];
  }
  const rawIdentities = collection.all.map(
    strategyPoolAddRawSourceIdentity,
  );
  if (
    rawIdentities.some((identity) => !identity)
    || new Set(rawIdentities).size !== rawIdentities.length
  ) return [];
  const latestIdentity = collection.latest === null
    ? ""
    : strategyPoolAddRawSourceIdentity(collection.latest);
  if (
    rawIdentities.length
      ? latestIdentity !== rawIdentities[0]
      : collection.latest !== null
  ) return [];
  const projected = [];
  for (const source of collection.all) {
    if (strategyPoolAddSourceIsUnsupported(source)) continue;
    const pointer = strategyPoolAddSourcePointer(source);
    if (!pointer) return [];
    projected.push(pointer);
  }
  const identities = projected.map((source) => (
    `${source.pointerKind}\u001f${source.sourceId}`
  ));
  if (new Set(identities).size !== identities.length) return [];
  return projected;
}

export function setStrategyPoolAddPanelVisible(form, selector, visible) {
  const panel = form?.querySelector?.(selector);
  if (!panel) return;
  panel.classList?.toggle?.("hidden", !visible);
  panel.setAttribute?.("aria-hidden", visible ? "false" : "true");
  const controls = panel.querySelectorAll?.("input, select, textarea") || [];
  for (const control of controls) control.disabled = !visible;
}

function setStrategyPoolAddLocked(control, locked) {
  if (!control) return;
  if (!control.dataset) control.dataset = {};
  if (locked) {
    control.dataset.candidateLabPoolAddLocked = "1";
  } else {
    delete control.dataset.candidateLabPoolAddLocked;
  }
}

function syncStrategyPoolAddAction(
  form,
  strategyType,
  {
    typeField,
    valueField,
    valuePanel,
    projectedAction = null,
    locked = false,
  },
) {
  const typeSelect = formField(form, typeField);
  const valueInput = formField(form, valueField);
  if (!typeSelect || !valueInput) return;
  const allowed = STRATEGY_POOL_ACTION_TYPES[strategyType] || [];
  const previousType = nonEmptyText(typeSelect.value);
  const previousValue = String(valueInput.value || "");
  typeSelect.innerHTML = [
    '<option value="">Select a compatible action</option>',
    ...allowed.map((actionType) => projectionOptionHtml(
      actionType,
      actionType,
      { "candidate-lab-action-type": "1" },
    )),
  ].join("");
  const action = minimalProjectedPoolAction(projectedAction, strategyType);
  if (action) {
    typeSelect.value = action.type;
    valueInput.value = Object.hasOwn(action, "value")
      ? String(action.value)
      : "";
  } else {
    typeSelect.value = allowed.includes(previousType)
      ? previousType
      : allowed.length === 1
        ? allowed[0]
        : "";
    valueInput.value = previousValue;
  }
  if (locked && action) {
    typeSelect.dataset.candidateLabPoolAddTypedAction = JSON.stringify(action);
  } else {
    delete typeSelect.dataset.candidateLabPoolAddTypedAction;
  }
  const requiresValue = ["limit", "pricing", "segment"].includes(
    nonEmptyText(typeSelect.value),
  );
  setStrategyPoolAddPanelVisible(form, valuePanel, requiresValue);
  setStrategyPoolAddLocked(typeSelect, locked);
  setStrategyPoolAddLocked(valueInput, locked && requiresValue);
}

export function syncStrategyPoolAddPlacement(form) {
  if (!form) return;
  const selected = Array.from(
    formField(form, "pool_add_source_id")?.selectedOptions || [],
  )[0];
  const voting = (
    selected?.dataset?.candidateLabProjection === "1"
    && selected?.dataset?.sourceKind === "voting_candidate"
  );
  if (!voting) {
    const placement = formField(form, "pool_add_placement_mode");
    if (placement) placement.value = "";
  }
  setStrategyPoolAddPanelVisible(
    form,
    "[data-candidate-lab-pool-add-placement-panel]",
    voting,
  );
}

export function syncStrategyPoolAddControls(
  form,
  payload,
  { preserveSource = true } = {},
) {
  if (!form) return;
  const typeSelect = formField(form, "pool_add_strategy_type");
  const sourceSelect = formField(form, "pool_add_source_id");
  if (!typeSelect || !sourceSelect) return;
  const previousType = nonEmptyText(typeSelect.value);
  typeSelect.innerHTML = [
    '<option value="">Select a strategy pool type</option>',
    ...STRATEGY_POOL_TYPES.map((strategyType) => projectionOptionHtml(
      strategyType,
      strategyType,
      { "candidate-lab-strategy-type": "1" },
    )),
  ].join("");
  typeSelect.value = STRATEGY_POOL_TYPES.includes(previousType)
    ? previousType
    : "";
  const strategyType = nonEmptyText(typeSelect.value);
  const currentPools = strategyPoolAddCurrentPools(payload);
  const currentPool = currentPools.find(
    (pool) => pool.strategyType === strategyType,
  );
  const eligible = strategyPoolAddSources(payload).filter((source) => (
    !source.strategyType
    || (
      source.strategyType === strategyType
      && currentPool
    )
  ));
  const previousSource = preserveSource
    ? nonEmptyText(sourceSelect.value)
    : "";
  sourceSelect.innerHTML = [
    '<option value="">Select an available candidate.</option>',
    ...eligible.map((source) => projectionOptionHtml(
      source.sourceId,
      `${source.sourceKind} · ${source.sourceId} · ${source.candidateStage}/${source.validationStatus}`,
      {
        "candidate-lab-projection": "1",
        "source-kind": source.sourceKind,
        "source-id": source.sourceId,
        "pointer-kind": source.pointerKind,
        "strategy-type": source.strategyType,
      },
    )),
  ].join("");
  if (selectContainsValue(sourceSelect, previousSource)) {
    sourceSelect.value = previousSource;
  } else if (eligible.length === 1) {
    sourceSelect.value = eligible[0].sourceId;
  } else {
    sourceSelect.value = "";
  }
  syncStrategyPoolAddAction(
    form,
    strategyType,
    {
      typeField: "pool_add_default_action_type",
      valueField: "pool_add_default_action_value",
      valuePanel: "[data-candidate-lab-pool-add-default-value-panel]",
      projectedAction: currentPool?.defaultAction || null,
      locked: Boolean(currentPool),
    },
  );
  syncStrategyPoolAddAction(
    form,
    strategyType,
    {
      typeField: "pool_add_action_type",
      valueField: "pool_add_action_value",
      valuePanel: "[data-candidate-lab-pool-add-action-value-panel]",
    },
  );
  syncStrategyPoolAddPlacement(form);
  const help = form.querySelector?.("[data-candidate-lab-pool-add-help]");
  if (help) {
    help.textContent = !strategyType
      ? "Select a pool type, then choose a candidate from this task."
      : !eligible.length
        ? "Create a candidate or voting group for this pool type."
        : currentPool
          ? "The pool default action is fixed for this operation."
          : "Set the default and match actions to create the first entry in this pool.";
  }
}

export function strategyPoolAddRequestIsCurrent(request, payload) {
  if (request?.workflow !== "strategy_pool_add_candidate") return true;
  const inputs = isRecord(request.workflow_inputs)
    ? request.workflow_inputs
    : {};
  const strategyType = nonEmptyText(inputs.strategy_type);
  if (!STRATEGY_POOL_TYPES.includes(strategyType)) return false;
  const pointerKind = Object.hasOwn(inputs, "candidate_asset_id")
    ? "candidate_asset_id"
    : Object.hasOwn(inputs, "selection_id")
      ? "selection_id"
      : "";
  const sourceId = nonEmptyText(inputs[pointerKind]);
  const source = strategyPoolAddSources(payload).find((item) => (
    item.pointerKind === pointerKind
    && item.sourceId === sourceId
    && (!item.strategyType || item.strategyType === strategyType)
  ));
  if (!source) return false;
  const rawMatches = collectionItems(
    isRecord(payload?.pools) ? payload.pools : {},
  ).filter((pool) => nonEmptyText(pool?.strategy_type) === strategyType);
  const currentPool = strategyPoolAddCurrentPools(payload).find(
    (pool) => pool.strategyType === strategyType,
  );
  if (rawMatches.length > 0 && (rawMatches.length !== 1 || !currentPool)) {
    return false;
  }
  const defaultAction = minimalProjectedPoolAction(
    inputs.default_action,
    strategyType,
  );
  if (!defaultAction) return false;
  if (
    currentPool
    && JSON.stringify(defaultAction) !== JSON.stringify(
      currentPool.defaultAction,
    )
  ) {
    return false;
  }
  if (source.sourceKind === "voting_candidate") {
    return Boolean(
      currentPool
      && STRATEGY_POOL_VOTING_PLACEMENTS.includes(inputs.placement_mode),
    );
  }
  return !Object.hasOwn(inputs, "placement_mode");
}

export function strategyPoolApplyOptions(payload) {
  const pools = collectionItems(isRecord(payload?.pools) ? payload.pools : {});
  const byType = new Map();
  const duplicates = new Set();
  for (const pool of pools) {
    const strategyType = nonEmptyText(pool?.strategy_type);
    const entries = Array.isArray(pool?.entries)
      ? pool.entries.filter(isRecord)
      : [];
    if (
      pool?.kind !== "candidate_pool"
      || !STRATEGY_POOL_TYPES.includes(strategyType)
      || entries.length < 1
      || !Number.isInteger(pool?.total)
      || pool.total < entries.length
    ) {
      continue;
    }
    if (byType.has(strategyType)) {
      duplicates.add(strategyType);
      continue;
    }
    byType.set(strategyType, {
      strategyType,
      entryCount: entries.length,
    });
  }
  for (const strategyType of duplicates) byType.delete(strategyType);
  return STRATEGY_POOL_TYPES
    .filter((strategyType) => byType.has(strategyType))
    .map((strategyType) => byType.get(strategyType));
}

export function syncStrategyPoolApplyControls(form, payload) {
  if (!form) return;
  const strategySelect = formField(form, "pool_apply_strategy_type");
  if (!strategySelect) return;
  const pools = strategyPoolApplyOptions(payload);
  const previousType = nonEmptyText(strategySelect.value);
  strategySelect.innerHTML = [
    '<option value="">Select a strategy pool</option>',
    ...pools.map((pool) => projectionOptionHtml(
      pool.strategyType,
      `${pool.strategyType} · ${pool.entryCount} rules`,
      {
        "candidate-lab-projection": "1",
        "strategy-type": pool.strategyType,
      },
    )),
  ].join("");
  if (previousType && selectContainsValue(strategySelect, previousType)) {
    strategySelect.value = previousType;
  } else if (pools.length === 1) {
    strategySelect.value = pools[0].strategyType;
  } else {
    strategySelect.value = "";
  }
  const help = form.querySelector?.("[data-candidate-lab-pool-apply-empty]");
  if (help) {
    help.textContent = pools.length === 0
      ? "Add rules to a strategy pool before continuing."
      : pools.length === 1
        ? "The available pool is selected. Set an optional output column prefix, then apply it."
        : "Select the strategy pool to apply.";
  }
}

function strategyPoolCompileForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_pool_compile"]',
  ) || null;
}

export function strategyProjectContextForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_project_context"]',
  ) || null;
}

export function strategyPoolMaterializeForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_pool_materialize"]',
  ) || null;
}

export function strategyLifecycleAdoptionForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_lifecycle_adopt"]',
  ) || null;
}

export function strategyDslDeliveryForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_dsl_delivery"]',
  ) || null;
}

export function strategyPoolValidationForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_pool_validation"]',
  ) || null;
}

export function strategyPoolStabilityForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_pool_stability"]',
  ) || null;
}

export function strategyPoolImpactForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_pool_impact"]',
  ) || null;
}

export function strategyImpactCubeForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_impact_cube"]',
  ) || null;
}

function strategyPoolRemoveEntryForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_pool_remove_entry"]',
  ) || null;
}

function strategyPoolSetActionForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_pool_set_action"]',
  ) || null;
}

export function strategyPoolReorderForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="strategy_pool_reorder"]',
  ) || null;
}

export function strategyPoolOperationPools(payload) {
  const pools = collectionItems(isRecord(payload?.pools) ? payload.pools : {});
  const byType = new Map();
  const duplicates = new Set();
  for (const pool of pools) {
    const strategyType = nonEmptyText(pool?.strategy_type);
    const entries = Array.isArray(pool?.entries)
      ? pool.entries.filter(isRecord)
      : [];
    const entryIds = entries.map((entry) => nonEmptyText(entry.entry_id));
    const completeEntries = (
      entries.length > 0
      && entries.length <= 200
      && pool?.total === entries.length
      && pool?.truncated !== true
      && new Set(entryIds).size === entryIds.length
      && entries.every((entry, index) => (
        STRATEGY_POOL_ENTRY_ID_RE.test(nonEmptyText(entry.entry_id))
        && entry.position === index
        && isRecord(entry.action)
        && nonEmptyText(entry.action.type)
      ))
    );
    if (
      pool?.kind !== "candidate_pool"
      || !STRATEGY_POOL_TYPES.includes(strategyType)
      || !completeEntries
    ) {
      continue;
    }
    if (byType.has(strategyType)) {
      duplicates.add(strategyType);
      continue;
    }
    byType.set(strategyType, {
      strategyType,
      poolId: nonEmptyText(pool.pool_id),
      entries: entries.map((entry) => ({
        entryId: nonEmptyText(entry.entry_id),
        position: entry.position,
        action: { ...entry.action },
      })),
    });
  }
  for (const strategyType of duplicates) byType.delete(strategyType);
  return STRATEGY_POOL_TYPES
    .filter((strategyType) => byType.has(strategyType))
    .map((strategyType) => byType.get(strategyType));
}

function syncStrategyPoolTypeSelect(select, pools) {
  if (!select) return "";
  const previousType = nonEmptyText(select.value);
  select.innerHTML = [
    '<option value="">Select a strategy pool</option>',
    ...pools.map((pool) => projectionOptionHtml(
      pool.strategyType,
      `${pool.strategyType} · ${pool.entries.length} rules`,
      {
        "candidate-lab-projection": "1",
        "strategy-type": pool.strategyType,
        "pool-id": pool.poolId,
      },
    )),
  ].join("");
  if (previousType && selectContainsValue(select, previousType)) {
    select.value = previousType;
  } else if (pools.length === 1) {
    select.value = pools[0].strategyType;
  } else {
    select.value = "";
  }
  return nonEmptyText(select.value);
}

export function syncStrategyProjectContextControls(form) {
  if (!form) return;
  const asOf = formField(form, "project_context_as_of");
  if (!asOf || nonEmptyText(asOf.value)) return;
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  asOf.value = `${year}-${month}-${day}`;
}

export function syncStrategyPoolMaterializeControls(form, payload) {
  if (!form) return;
  const pools = strategyPoolOperationPools(payload);
  const selectedType = syncStrategyPoolTypeSelect(
    formField(form, "pool_materialize_strategy_type"),
    pools,
  );
  const help = form.querySelector?.(
    "[data-candidate-lab-pool-materialize-help]",
  );
  if (help) {
    help.textContent = pools.length === 0
      ? "Add rules to a strategy pool before creating a draft."
      : pools.length === 1
        ? `Selected pool: ${selectedType}. Create a draft strategy from its rules.`
        : "Select a pool to create a draft strategy.";
  }
}

function strategyDeliveryOptions(payload) {
  return projectedStrategyItems(payload).filter((strategy) => (
    STRATEGY_ID_RE.test(nonEmptyText(strategy?.strategy_id))
    && STRATEGY_POOL_TYPES.includes(nonEmptyText(strategy?.strategy_type))
    && ["draft", "validated", "adopted_local"].includes(
      nonEmptyText(strategy?.asset_status),
    )
  )).map((strategy) => ({
    strategyId: nonEmptyText(strategy.strategy_id),
    strategyType: nonEmptyText(strategy.strategy_type),
    version: strategy.version,
    assetStatus: nonEmptyText(strategy.asset_status),
  }));
}

export function syncStrategyDslDeliveryControls(form, payload) {
  if (!form) return;
  const select = formField(form, "dsl_delivery_strategy_id");
  if (!select) return;
  const strategies = strategyDeliveryOptions(payload);
  const previous = nonEmptyText(select.value);
  select.innerHTML = [
    '<option value="">Select a strategy version</option>',
    ...strategies.map((strategy) => projectionOptionHtml(
      strategy.strategyId,
      `${strategy.strategyType} · v${stablePrimitiveText(strategy.version)} · ${strategy.assetStatus}`,
      {
        "candidate-lab-projection": "1",
        "strategy-id": strategy.strategyId,
      },
    )),
  ].join("");
  if (previous && selectContainsValue(select, previous)) {
    select.value = previous;
  } else if (strategies.length === 1) {
    select.value = strategies[0].strategyId;
  } else {
    select.value = "";
  }
  const help = form.querySelector?.(
    "[data-candidate-lab-dsl-delivery-help]",
  );
  if (help) {
    help.textContent = strategies.length === 0
      ? "Create a strategy from a pool before exporting it."
      : strategies.length === 1
        ? "The available strategy is selected. Export checks row-level equivalence against the active dataset."
        : "Select the strategy version to export.";
  }
}

function strategyLifecycleAdoptionOptions(payload) {
  return projectedStrategyItems(payload).filter((strategy) => (
    STRATEGY_ID_RE.test(nonEmptyText(strategy?.strategy_id))
    && STRATEGY_POOL_TYPES.includes(nonEmptyText(strategy?.strategy_type))
    && nonEmptyText(strategy?.asset_status) === "draft"
  )).map((strategy) => ({
    strategyId: nonEmptyText(strategy.strategy_id),
    strategyType: nonEmptyText(strategy.strategy_type),
    version: strategy.version,
    assetStatus: "draft",
    runtimeBlockers: Array.isArray(strategy?.materialization?.runtime_blockers)
      ? strategy.materialization.runtime_blockers.length
      : 0,
  }));
}

function strategyProjectionAvailableColumns(payload) {
  const workflow = isRecord(payload?.workflow) ? payload.workflow : {};
  const sample = isRecord(workflow.sample_design)
    ? workflow.sample_design
    : {};
  const sources = [
    payload?.available_columns,
    payload?.task?.available_columns,
    workflow.available_columns,
    sample.available_columns,
    sample.column_whitelist,
    sample.dataset?.available_columns,
  ];
  const columns = [];
  const seen = new Set();
  for (const source of sources) {
    if (!Array.isArray(source)) continue;
    for (const item of source) {
      const column = nonEmptyText(
        typeof item === "string" ? item : item?.name || item?.column,
      );
      if (!column || seen.has(column)) continue;
      seen.add(column);
      columns.push(column);
      if (columns.length >= 500) return columns;
    }
  }
  return columns;
}

export function syncStrategyLifecycleAdoptionEconomics(form, strategyType) {
  const economics = form?.querySelector?.(
    "[data-candidate-lab-adoption-economics]",
  );
  const economicType = ["limit", "pricing"].includes(strategyType);
  economics?.classList?.toggle?.("hidden", !economicType);
  const components = form?.querySelectorAll?.(
    "[data-candidate-lab-adoption-component]",
  ) || [];
  for (const component of components) {
    const name = nonEmptyText(component.dataset?.candidateLabAdoptionComponent);
    const allowedTypes = nonEmptyText(component.dataset?.strategyTypes)
      .split(/\s+/)
      .filter(Boolean);
    const visible = economicType && allowedTypes.includes(strategyType);
    component.classList?.toggle?.("hidden", !visible);
    const mode = formField(form, `lifecycle_adopt_${name}_mode`);
    if (visible && !["column", "value"].includes(nonEmptyText(mode?.value))) {
      mode.value = "column";
    }
    const selectedMode = nonEmptyText(mode?.value) || "column";
    const bindings = component.querySelectorAll?.(
      "[data-candidate-lab-adoption-binding]",
    ) || [];
    for (const binding of bindings) {
      binding.classList?.toggle?.(
        "hidden",
        nonEmptyText(binding.dataset?.candidateLabAdoptionBinding)
          !== selectedMode,
      );
    }
  }
}

export function syncStrategyLifecycleAdoptionControls(form, payload) {
  if (!form) return;
  const select = formField(form, "lifecycle_adopt_strategy_id");
  if (!select) return;
  const strategies = strategyLifecycleAdoptionOptions(payload);
  const previous = nonEmptyText(select.value);
  select.innerHTML = [
    '<option value="">Select a draft strategy</option>',
    ...strategies.map((strategy) => projectionOptionHtml(
      strategy.strategyId,
      `${STRATEGY_TYPE_LABELS[strategy.strategyType] || strategy.strategyType} · v${stablePrimitiveText(strategy.version)} · draft${strategy.runtimeBlockers ? ` · ${strategy.runtimeBlockers} blocking issues` : ""}`,
      {
        "candidate-lab-projection": "1",
        "strategy-id": strategy.strategyId,
        "strategy-type": strategy.strategyType,
        "asset-status": strategy.assetStatus,
      },
    )),
  ].join("");
  if (previous && selectContainsValue(select, previous)) {
    select.value = previous;
  } else if (strategies.length === 1) {
    select.value = strategies[0].strategyId;
  } else {
    select.value = "";
  }
  const selected = Array.from(select.selectedOptions || [])[0] || null;
  const strategyType = nonEmptyText(selected?.dataset?.strategyType);
  syncStrategyLifecycleAdoptionEconomics(form, strategyType);

  const help = form.querySelector?.("[data-candidate-lab-adoption-help]");
  if (help) {
    help.textContent = strategies.length === 0
      ? "Create a draft strategy from a pool before requesting adoption."
      : strategies.length === 1
        ? "The available draft is selected. Submission reruns checks and requests manual confirmation."
        : "Select a draft version to check and submit for confirmation.";
  }

  const columns = strategyProjectionAvailableColumns(payload);
  const datalist = form.querySelector?.(
    "[data-candidate-lab-adoption-available-columns]",
  );
  if (datalist) {
    datalist.innerHTML = columns.map(
      (column) => `<option value="${escapeHtml(column)}"></option>`,
    ).join("");
  }
  const columnsHelp = form.querySelector?.(
    "[data-candidate-lab-adoption-columns-help]",
  );
  if (columnsHelp) {
    columnsHelp.textContent = columns.length
      ? `${columns.length} columns are suggested. Entered column names are checked against the task dataset.`
      : "Enter column names from the task dataset. Missing or unusable columns will fail validation.";
  }
}

export function strategyWorkbenchRequestIsCurrent(request, payload) {
  if (request?.request_kind === "strategy_lifecycle") {
    return strategyLifecycleAdoptionOptions(payload).some((strategy) => (
      strategy.strategyId === request.strategy_id
      && strategy.strategyType === request.strategy_type
      && strategy.assetStatus === "draft"
    ));
  }
  if (request?.workflow === "strategy_pool_materialize") {
    return strategyPoolOperationPools(payload).some(
      (pool) => pool.strategyType === request.workflow_inputs?.strategy_type,
    );
  }
  if (request?.workflow === "strategy_dsl_delivery") {
    return strategyDeliveryOptions(payload).some(
      (strategy) => (
        strategy.strategyId === request.workflow_inputs?.strategy_id
      ),
    );
  }
  return true;
}

export function syncStrategyPoolValidationControls(form, payload) {
  if (!form) return;
  const pools = strategyPoolOperationPools(payload);
  const selectedType = syncStrategyPoolTypeSelect(
    formField(form, "pool_validation_strategy_type"),
    pools,
  );
  const help = form.querySelector?.(
    "[data-candidate-lab-pool-validation-help]",
  );
  if (help) {
    help.textContent = pools.length === 0
      ? "Add rules to a strategy pool before validation."
      : pools.length === 1
        ? `Selected pool: ${selectedType}. Choose the validation or out-of-time split.`
        : "Select a strategy pool to validate.";
  }
}

export function syncStrategyPoolStabilityControls(form, payload) {
  if (!form) return;
  const pools = strategyPoolOperationPools(payload);
  const selectedType = syncStrategyPoolTypeSelect(
    formField(form, "pool_stability_strategy_type"),
    pools,
  );
  const help = form.querySelector?.(
    "[data-candidate-lab-pool-stability-help]",
  );
  if (help) {
    help.textContent = pools.length === 0
      ? "Add rules to a strategy pool before measurement."
      : pools.length === 1
        ? `Selected pool: ${selectedType}. Compare development results with available validation and out-of-time splits.`
        : "Select a pool for stability analysis.";
  }
}

export function syncStrategyPoolImpactControls(form, payload) {
  if (!form) return;
  const pools = strategyPoolOperationPools(payload).filter((pool) => (
    ["approval", "reject"].includes(pool.strategyType)
  ));
  const selectedType = syncStrategyPoolTypeSelect(
    formField(form, "pool_impact_strategy_type"),
    pools,
  );
  const help = form.querySelector?.(
    "[data-candidate-lab-pool-impact-help]",
  );
  if (help) {
    help.textContent = pools.length === 0
      ? "Add rules to an approval or rejection pool before impact analysis."
      : pools.length === 1
        ? `Selected pool: ${selectedType}. Run impact analysis on its current rules.`
        : "Select an approval or rejection pool.";
  }
}

export function syncStrategyImpactCubeControls(form, payload) {
  if (!form) return;
  const pools = strategyPoolOperationPools(payload);
  const selectedType = syncStrategyPoolTypeSelect(
    formField(form, "impact_cube_strategy_type"),
    pools,
  );
  const help = form.querySelector?.(
    "[data-candidate-lab-impact-cube-help]",
  );
  if (help) {
    help.textContent = pools.length === 0
      ? "Add rules to a strategy pool before measurement."
      : pools.length === 1
        ? `Selected pool: ${selectedType}. Leave splits empty to include all available splits with data.`
        : "Select a pool to measure.";
  }
}

export function strategyMeasurementRequestIsCurrent(request, payload) {
  if (
    !["strategy_pool_impact", "strategy_impact_cube"].includes(
      request?.workflow,
    )
  ) {
    return true;
  }
  const strategyType = nonEmptyText(
    request?.workflow_inputs?.strategy_type,
  );
  const pools = strategyPoolOperationPools(payload);
  return pools.some((pool) => pool.strategyType === strategyType)
    && (
      request.workflow !== "strategy_pool_impact"
      || ["approval", "reject"].includes(strategyType)
    );
}

function strategyPoolEntryLabel(entry, displayPosition = entry.position) {
  const actionType = nonEmptyText(entry?.action?.type) || "unknown";
  return `#${displayPosition + 1} · ${entry.entryId} · ${actionType}`;
}

function syncStrategyPoolEntrySelect(
  select,
  pool,
  { preserveEntry = true } = {},
) {
  if (!select) return;
  const previousEntryId = nonEmptyText(select.value);
  const previousType = nonEmptyText(
    Array.from(select.selectedOptions || [])[0]?.dataset?.strategyType,
  );
  const entries = pool?.entries || [];
  select.innerHTML = [
    '<option value="">Select a pool entry</option>',
    ...entries.map((entry) => projectionOptionHtml(
      entry.entryId,
      strategyPoolEntryLabel(entry),
      {
        "candidate-lab-projection": "1",
        "strategy-type": pool.strategyType,
        "entry-id": entry.entryId,
      },
    )),
  ].join("");
  if (
    preserveEntry
    && previousType === pool?.strategyType
    && selectContainsValue(select, previousEntryId)
  ) {
    select.value = previousEntryId;
  } else {
    select.value = "";
  }
}

export function setStrategyPoolActionValuePanelVisible(form, visible) {
  const panel = form?.querySelector?.(
    "[data-candidate-lab-pool-action-value-panel]",
  );
  if (!panel) return;
  panel.classList?.toggle?.("hidden", !visible);
  panel.setAttribute?.("aria-hidden", visible ? "false" : "true");
  const controls = panel.querySelectorAll?.("input, select, textarea") || [];
  for (const control of controls) control.disabled = !visible;
}

function syncStrategyPoolActionTypes(
  form,
  strategyType,
  { preserveAction = true } = {},
) {
  const select = formField(form, "pool_action_type");
  if (!select) return;
  const previousAction = nonEmptyText(select.value);
  const allowed = STRATEGY_POOL_ACTION_TYPES[strategyType] || [];
  select.innerHTML = [
    '<option value="">Select a compatible action</option>',
    ...allowed.map((actionType) => projectionOptionHtml(
      actionType,
      actionType,
      { "candidate-lab-action-type": "1" },
    )),
  ].join("");
  if (
    preserveAction
    && previousAction
    && allowed.includes(previousAction)
    && selectContainsValue(select, previousAction)
  ) {
    select.value = previousAction;
  } else if (allowed.length === 1) {
    select.value = allowed[0];
  } else {
    select.value = "";
  }
  setStrategyPoolActionValuePanelVisible(
    form,
    ["limit", "pricing", "segment"].includes(nonEmptyText(select.value)),
  );
}

function syncStrategyPoolCompileControls(form, pools) {
  if (!form) return;
  const selectedType = syncStrategyPoolTypeSelect(
    formField(form, "pool_compile_strategy_type"),
    pools,
  );
  const help = form.querySelector?.("[data-candidate-lab-pool-compile-help]");
  if (help) {
    help.textContent = pools.length
      ? selectedType
        ? "Compile the current pool into a rule waterfall."
        : "Select a pool to compile."
      : "Add rules to a strategy pool before compiling it.";
  }
}

export function syncStrategyPoolRemoveEntryControls(
  form,
  pools,
  { preserveEntry = true } = {},
) {
  if (!form) return;
  const selectedType = syncStrategyPoolTypeSelect(
    formField(form, "pool_remove_strategy_type"),
    pools,
  );
  const pool = pools.find((item) => item.strategyType === selectedType);
  syncStrategyPoolEntrySelect(
    formField(form, "pool_remove_entry_id"),
    pool,
    { preserveEntry },
  );
  const help = form.querySelector?.("[data-candidate-lab-pool-remove-help]");
  if (help) {
    help.textContent = pools.length
      ? selectedType
        ? "Select the pool entry to remove."
        : "Select a strategy pool."
      : "There are no pool entries to remove.";
  }
}

export function syncStrategyPoolSetActionControls(
  form,
  pools,
  {
    preserveEntry = true,
    preserveAction = true,
  } = {},
) {
  if (!form) return;
  const selectedType = syncStrategyPoolTypeSelect(
    formField(form, "pool_action_strategy_type"),
    pools,
  );
  const pool = pools.find((item) => item.strategyType === selectedType);
  syncStrategyPoolEntrySelect(
    formField(form, "pool_action_entry_id"),
    pool,
    { preserveEntry },
  );
  syncStrategyPoolActionTypes(
    form,
    selectedType,
    { preserveAction },
  );
  const help = form.querySelector?.("[data-candidate-lab-pool-action-help]");
  if (help) {
    help.textContent = pools.length
      ? selectedType
        ? "Select an entry and an action compatible with the pool type."
        : "Select a strategy pool."
      : "There are no pool entries to update.";
  }
}

export function syncStrategyPoolReorderControls(form, pools) {
  if (!form) return;
  const selectedType = syncStrategyPoolTypeSelect(
    formField(form, "pool_reorder_strategy_type"),
    pools,
  );
  const pool = pools.find((item) => item.strategyType === selectedType);
  renderStrategyPoolReorderOrder(form, pool);
  const help = form.querySelector?.("[data-candidate-lab-pool-reorder-help]");
  if (help) {
    help.textContent = pools.length
      ? selectedType
        ? "Select an entry and use the arrows to reorder it. Save to apply the full ordering."
        : "Select a strategy pool."
      : "There are no pool entries to reorder.";
  }
}

export function strategyPoolOrderMatches(pool, orderedIds) {
  if (!pool || !Array.isArray(orderedIds)) return false;
  const currentIds = pool.entries.map((entry) => entry.entryId);
  return (
    orderedIds.length === currentIds.length
    && new Set(orderedIds).size === orderedIds.length
    && currentIds.every((entryId) => orderedIds.includes(entryId))
  );
}

export function renderStrategyPoolReorderOrder(
  form,
  pool,
  orderedIds = null,
  selectedEntryId = "",
) {
  const orderSelect = formField(form, "pool_reorder_ordered_ids");
  if (orderSelect) {
    const order = (
      strategyPoolOrderMatches(pool, orderedIds)
        ? orderedIds
        : pool?.entries.map((entry) => entry.entryId)
    ) || [];
    const byId = new Map(
      (pool?.entries || []).map((entry) => [entry.entryId, entry]),
    );
    orderSelect.innerHTML = pool
      ? order.map((entryId, index) => {
        const entry = byId.get(entryId);
        return projectionOptionHtml(
          entry.entryId,
          strategyPoolEntryLabel(entry, index),
          {
            "candidate-lab-projection": "1",
            "strategy-type": pool.strategyType,
            "entry-id": entry.entryId,
          },
        );
      }).join("")
      : '<option value="">Select a pool first.</option>';
    orderSelect.value = (
      selectedEntryId && selectContainsValue(orderSelect, selectedEntryId)
        ? selectedEntryId
        : ""
    );
  }
}

export function syncStrategyPoolOperationForms(root, payload) {
  const pools = strategyPoolOperationPools(payload);
  syncStrategyPoolCompileControls(strategyPoolCompileForm(root), pools);
  syncStrategyPoolRemoveEntryControls(
    strategyPoolRemoveEntryForm(root),
    pools,
  );
  syncStrategyPoolSetActionControls(
    strategyPoolSetActionForm(root),
    pools,
  );
  syncStrategyPoolReorderControls(strategyPoolReorderForm(root), pools);
}

export function strategyPoolOperationRequestIsCurrent(request, payload) {
  if (!STRATEGY_POOL_OPERATION_WORKFLOWS.includes(request?.workflow)) {
    return true;
  }
  const inputs = isRecord(request?.workflow_inputs)
    ? request.workflow_inputs
    : {};
  const pool = strategyPoolOperationPools(payload).find(
    (item) => item.strategyType === inputs.strategy_type,
  );
  if (!pool) return false;
  if (request.workflow === "strategy_pool_compile") return true;
  if (
    request.workflow === "strategy_pool_remove_entry"
    || request.workflow === "strategy_pool_set_action"
  ) {
    return pool.entries.some((entry) => entry.entryId === inputs.entry_id);
  }
  return strategyPoolOrderMatches(pool, inputs.ordered_ids);
}

export function strategyPoolValidationRequestIsCurrent(request, payload) {
  if (request?.workflow !== "strategy_pool_validation") return true;
  const strategyType = nonEmptyText(
    request?.workflow_inputs?.strategy_type,
  );
  return (
    STRATEGY_POOL_TYPES.includes(strategyType)
    && strategyPoolOperationPools(payload).some(
      (pool) => pool.strategyType === strategyType,
    )
  );
}

export function strategyPoolStabilityRequestIsCurrent(request, payload) {
  if (request?.workflow !== "strategy_pool_stability") return true;
  const strategyType = nonEmptyText(
    request?.workflow_inputs?.strategy_type,
  );
  return (
    STRATEGY_POOL_TYPES.includes(strategyType)
    && strategyPoolOperationPools(payload).some(
      (pool) => pool.strategyType === strategyType,
    )
  );
}

export function crossCandidateSearchForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="cross_matrix_candidate_search"]',
  ) || null;
}

export function crossCandidateBuildForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="cross_matrix_candidate_build_from_search"]',
  ) || null;
}

function crossSearchFeatureOptions(payload) {
  const byFeature = new Map();
  for (const candidate of univariateProjectionCandidates(payload)) {
    for (const pair of univariateCandidatePairs(candidate)) {
      if (!byFeature.has(pair.feature)) byFeature.set(pair.feature, new Set());
      byFeature.get(pair.feature).add(pair.method);
    }
  }
  return [...byFeature.entries()].map(([feature, methods]) => ({
    feature,
    methodCount: methods.size,
  }));
}

export function syncCrossCandidateSearchControls(form, payload) {
  if (!form) return;
  const select = formField(form, "cross_search_features");
  if (!select) return;
  const features = crossSearchFeatureOptions(payload);
  const previous = new Set(selectedValues(select));
  select.innerHTML = features.length
    ? features.map((item) => projectionOptionHtml(
      item.feature,
      `${item.feature} · ${item.methodCount} available binning methods`,
      {
        "candidate-lab-projection": "1",
        feature: item.feature,
      },
    )).join("")
    : '<option value="" disabled>No features available for search</option>';
  for (const option of Array.from(select.options || [])) {
    option.selected = previous.has(option.value);
  }
  const selectedCount = selectedValues(select).length;
  const searchSpace = selectedCount * (selectedCount - 1) / 2;
  const help = form.querySelector?.(
    "[data-candidate-lab-cross-search-help]",
  );
  if (help) {
    help.textContent = features.length < 2
      ? "Analyse at least two features before searching for pairs."
      : selectedCount < 2
        ? `${features.length} features available. Select 2–20 features.`
        : `${selectedCount} features selected: ${searchSpace} possible pairs. The pair limit bounds the number evaluated.`;
  }
}

function crossSearchProjectionCandidates(payload) {
  const collection = isRecord(payload?.candidates?.cross_search)
    ? payload.candidates.cross_search
    : {};
  const seen = new Set();
  return collectionItems(collection).filter((search) => {
    const searchId = nonEmptyText(search?.search_id);
    if (!CROSS_SEARCH_ID_RE.test(searchId) || seen.has(searchId)) return false;
    seen.add(searchId);
    return true;
  });
}

function crossSearchPairs(search) {
  const seen = new Set();
  return (Array.isArray(search?.pairs) ? search.pairs : []).filter((pair) => {
    const pairId = nonEmptyText(pair?.pair_id);
    if (!isRecord(pair) || !CROSS_PAIR_ID_RE.test(pairId) || seen.has(pairId)) {
      return false;
    }
    seen.add(pairId);
    return true;
  });
}

function crossPairOptionLabel(pair) {
  const eligibility = pair?.eligible === true
    ? "eligible"
    : "Below the minimum sample threshold";
  return [
    nonEmptyText(pair?.pair_id),
    `${nonEmptyText(pair?.x_feature)}/${nonEmptyText(pair?.x_method)}`,
    `× ${nonEmptyText(pair?.y_feature)}/${nonEmptyText(pair?.y_method)}`,
    eligibility,
    `empty cells${stablePrimitiveText(pair?.empty_cell_count)}/${stablePrimitiveText(pair?.cell_count)}`,
    `Percentage${stablePrimitiveText(pair?.empty_cell_share)}`,
    `rank ${stablePrimitiveText(pair?.rank)}`,
  ].join(" · ");
}

export function syncCrossCandidateBuildControls(
  form,
  payload,
  { preservePair = true } = {},
) {
  if (!form) return;
  const searches = crossSearchProjectionCandidates(payload);
  const searchSelect = formField(form, "cross_build_search_id");
  const pairSelect = formField(form, "cross_build_pair_id");
  if (!searchSelect || !pairSelect) return;
  const previousSearchId = nonEmptyText(searchSelect.value);
  searchSelect.innerHTML = [
    '<option value="">Select a pair search</option>',
    ...searches.map((search) => projectionOptionHtml(
      search.search_id,
      `${search.search_id} · assessed${stablePrimitiveText(search.evaluated)} / ${stablePrimitiveText(search.search_space)} · eligible ${stablePrimitiveText(search.eligible)}`,
      {
        "candidate-lab-projection": "1",
        "search-id": nonEmptyText(search.search_id),
      },
    )),
  ].join("");
  searchSelect.value = selectContainsValue(searchSelect, previousSearchId)
    ? previousSearchId
    : "";

  const searchId = nonEmptyText(searchSelect.value);
  const search = searches.find((item) => item.search_id === searchId);
  const pairs = crossSearchPairs(search);
  const previousPairId = nonEmptyText(pairSelect.value);
  const previousSource = nonEmptyText(
    Array.from(pairSelect.selectedOptions || [])[0]?.dataset?.searchId,
  );
  pairSelect.innerHTML = [
    `<option value="">${searchId ? "Select a feature pair" : "Select a search result."}</option>`,
    ...pairs.map((pair) => projectionOptionHtml(
      pair.pair_id,
      crossPairOptionLabel(pair),
      {
        "candidate-lab-projection": "1",
        "search-id": searchId,
        "pair-id": nonEmptyText(pair.pair_id),
        eligible: pair.eligible === true ? "1" : "0",
      },
    )),
  ].join("");
  if (
    preservePair
    && previousSource === searchId
    && selectContainsValue(pairSelect, previousPairId)
  ) {
    pairSelect.value = previousPairId;
  } else {
    pairSelect.value = "";
  }
  const help = form.querySelector?.("[data-candidate-lab-cross-build-help]");
  if (help) {
    help.textContent = searches.length === 0
      ? "Run a pair search before creating a candidate."
      : !searchId
        ? "Select the search results to review."
        : pairs.length === 0
          ? "No pairs are available in this result. Review the full evidence or run another search."
          : "Review eligibility, empty cells and sample counts, then select a pair.";
  }
}

export function crossCandidateRequestIsCurrent(request, payload) {
  if (request?.workflow === "cross_matrix_candidate_search") {
    const available = new Set(
      crossSearchFeatureOptions(payload).map((item) => item.feature),
    );
    const features = request?.workflow_inputs?.features;
    return (
      Array.isArray(features)
      && features.length >= 2
      && features.length <= 20
      && new Set(features).size === features.length
      && features.every((feature) => available.has(feature))
    );
  }
  if (
    request?.workflow !== "cross_matrix_candidate_build_from_search"
  ) {
    return true;
  }
  const search = crossSearchProjectionCandidates(payload).find(
    (item) => item.search_id === request?.workflow_inputs?.search_id,
  );
  return crossSearchPairs(search).some(
    (pair) => pair.pair_id === request?.workflow_inputs?.pair_id,
  );
}

export function crossRuleSearchForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="cross_rule_search"]',
  ) || null;
}

export function crossRuleBuildForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="cross_rule_candidate_build_from_search"]',
  ) || null;
}

export function syncCrossRuleSearchControls(form, payload) {
  if (!form) return;
  const select = formField(form, "cross_rule_features");
  if (!select) return;
  const features = crossSearchFeatureOptions(payload);
  const previous = new Set(selectedValues(select));
  select.innerHTML = features.length
    ? features.map((item) => projectionOptionHtml(
      item.feature,
      `${item.feature} · ${item.methodCount} available binning methods`,
      {
        "candidate-lab-projection": "1",
        feature: item.feature,
      },
    )).join("")
    : '<option value="" disabled>No features available for search</option>';
  for (const option of Array.from(select.options || [])) {
    option.selected = previous.has(option.value);
  }
  const selectedCount = selectedValues(select).length;
  const dimension = Number(formValue(form, "cross_rule_dimension"));
  const help = form.querySelector?.("[data-candidate-lab-cross-rule-help]");
  if (help) {
    help.textContent = features.length < 2
      ? "Analyse at least two features before searching for rules."
      : selectedCount < dimension
        ? `${selectedCount} features selected. A ${dimension}-dimensional search requires at least ${dimension}.`
        : `Search ${dimension}-dimensional rules across ${selectedCount} selected features. Thresholds and risk directions come from the feature analysis.`;
  }
}

function crossRuleSearchProjectionCandidates(payload) {
  const collection = isRecord(payload?.candidates?.cross_rule_search)
    ? payload.candidates.cross_rule_search
    : {};
  const seen = new Set();
  return collectionItems(collection).filter((search) => {
    const searchId = nonEmptyText(search?.search_id);
    if (
      !CROSS_RULE_SEARCH_ID_RE.test(searchId)
      || seen.has(searchId)
    ) return false;
    seen.add(searchId);
    return true;
  });
}

function crossRulePointers(search) {
  const seen = new Set();
  return (Array.isArray(search?.rules) ? search.rules : []).filter((rule) => {
    const ruleId = nonEmptyText(rule?.rule_id);
    if (!isRecord(rule) || !CROSS_RULE_ID_RE.test(ruleId) || seen.has(ruleId)) {
      return false;
    }
    seen.add(ruleId);
    return true;
  });
}

export function syncCrossRuleBuildControls(
  form,
  payload,
  { preserveRule = true } = {},
) {
  if (!form) return;
  const searches = crossRuleSearchProjectionCandidates(payload);
  const searchSelect = formField(form, "cross_rule_build_search_id");
  const ruleSelect = formField(form, "cross_rule_build_rule_id");
  if (!searchSelect || !ruleSelect) return;
  const previousSearchId = nonEmptyText(searchSelect.value);
  searchSelect.innerHTML = [
    '<option value="">Select a threshold rule search</option>',
    ...searches.map((search) => projectionOptionHtml(
      search.search_id,
      `${search.search_id} · ${stablePrimitiveText(search.dimension)}D · assessed${stablePrimitiveText(search.evaluated)} · eligible ${stablePrimitiveText(search.eligible)}`,
      {
        "candidate-lab-projection": "1",
        "search-id": nonEmptyText(search.search_id),
      },
    )),
  ].join("");
  searchSelect.value = selectContainsValue(searchSelect, previousSearchId)
    ? previousSearchId
    : "";
  const searchId = nonEmptyText(searchSelect.value);
  const search = searches.find((item) => item.search_id === searchId);
  const rules = crossRulePointers(search);
  const previousRuleId = nonEmptyText(ruleSelect.value);
  const previousSource = nonEmptyText(
    Array.from(ruleSelect.selectedOptions || [])[0]?.dataset?.searchId,
  );
  ruleSelect.innerHTML = [
    `<option value="">${searchId ? "Select a rule" : "Select a search result."}</option>`,
    ...rules.map((rule) => projectionOptionHtml(
      rule.rule_id,
      [
        rule.rule_id,
        `rank ${stablePrimitiveText(rule.rank)}`,
        rule.eligible === true ? "eligible" : "Unsatisfied",
        `lift ${stablePrimitiveText(rule?.metrics?.lift)}`,
        `Hit rate${stablePrimitiveText(rule?.metrics?.hit_share)}`,
      ].join(" · "),
      {
        "candidate-lab-projection": "1",
        "search-id": searchId,
        "rule-id": nonEmptyText(rule.rule_id),
        eligible: rule.eligible === true ? "1" : "0",
      },
    )),
  ].join("");
  if (
    preserveRule
    && previousSource === searchId
    && selectContainsValue(ruleSelect, previousRuleId)
  ) {
    ruleSelect.value = previousRuleId;
  } else {
    ruleSelect.value = "";
  }
  const help = form.querySelector?.("[data-candidate-lab-cross-rule-build-help]");
  if (help) {
    help.textContent = searches.length === 0
      ? "Run a threshold rule search before continuing."
      : !searchId
        ? "Select the search results to review."
        : rules.length === 0
          ? "No rules are available in this result. Review the full evidence or run another search."
          : "Review the constraints and metrics, then select a rule.";
  }
}

export function crossRuleRequestIsCurrent(request, payload) {
  if (request?.workflow === "cross_rule_search") {
    const available = new Set(
      crossSearchFeatureOptions(payload).map((item) => item.feature),
    );
    const features = request?.workflow_inputs?.features;
    return (
      Array.isArray(features)
      && features.length >= 2
      && features.length <= 12
      && new Set(features).size === features.length
      && features.every((feature) => available.has(feature))
    );
  }
  if (
    request?.workflow !== "cross_rule_candidate_build_from_search"
  ) return true;
  const search = crossRuleSearchProjectionCandidates(payload).find(
    (item) => item.search_id === request?.workflow_inputs?.search_id,
  );
  return crossRulePointers(search).some(
    (rule) => rule.rule_id === request?.workflow_inputs?.rule_id,
  );
}

function votingSearchForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="voting_candidate_search"]',
  ) || null;
}

function votingBuildForm(root) {
  return root?.querySelector?.(
    '[data-candidate-lab-workflow="voting_candidate_build_from_search"]',
  ) || null;
}

function votingPoolOptions(payload) {
  const pools = collectionItems(isRecord(payload?.pools) ? payload.pools : {});
  const seen = new Set();
  const result = [];
  for (const pool of pools) {
    const strategyType = nonEmptyText(pool?.strategy_type);
    if (
      !["approval", "reject", "limit", "pricing", "segmentation"].includes(
        strategyType,
      )
      || seen.has(strategyType)
    ) {
      continue;
    }
    const rules = (Array.isArray(pool?.entries) ? pool.entries : [])
      .filter((entry) => (
        isRecord(entry)
        && entry.enabled === true
        && nonEmptyText(entry?.source?.asset_type) !== "voting_n_of_k"
        && VOTING_RULE_ID_RE.test(nonEmptyText(entry.rule_id))
      ))
      .map((entry) => ({
        ruleId: nonEmptyText(entry.rule_id),
        assetType: nonEmptyText(entry?.source?.asset_type),
      }));
    if (rules.length < 2) continue;
    seen.add(strategyType);
    result.push({
      strategyType,
      revision: pool.revision,
      rules,
    });
  }
  return result;
}

export function syncVotingSearchControls(form, payload) {
  if (!form) return;
  const pools = votingPoolOptions(payload);
  const strategySelect = formField(form, "voting_strategy_type");
  const includeSelect = formField(form, "voting_include_rule_ids");
  const excludeSelect = formField(form, "voting_exclude_rule_ids");
  if (!strategySelect || !includeSelect || !excludeSelect) return;
  const previousType = nonEmptyText(strategySelect.value);
  strategySelect.innerHTML = [
    '<option value="">Select a strategy pool</option>',
    ...pools.map((pool) => projectionOptionHtml(
      pool.strategyType,
      `${pool.strategyType} · revision ${stablePrimitiveText(pool.revision)} · ${pool.rules.length} Searchable rules`,
      { "candidate-lab-projection": "1" },
    )),
  ].join("");
  if (selectContainsValue(strategySelect, previousType)) {
    strategySelect.value = previousType;
  } else if (pools.length === 1) {
    strategySelect.value = pools[0].strategyType;
  } else {
    strategySelect.value = "";
  }
  const selectedType = nonEmptyText(strategySelect.value);
  const selectedPool = pools.find((pool) => pool.strategyType === selectedType);
  const rules = selectedPool?.rules || [];
  for (const [select, placeholder] of [
    [includeSelect, "Required rules (optional)"],
    [excludeSelect, "Excluded rules (optional)"],
  ]) {
    const previous = new Set(selectedValues(select));
    select.innerHTML = [
      `<option value="" disabled>${escapeHtml(placeholder)}</option>`,
      ...rules.map((rule) => projectionOptionHtml(
        rule.ruleId,
        `${rule.ruleId} · ${rule.assetType || "candidate"}`,
        { "candidate-lab-projection": "1" },
      )),
    ].join("");
    for (const option of Array.from(select.options || [])) {
      option.selected = previous.has(option.value);
    }
  }
  const empty = form.querySelector?.("[data-candidate-lab-voting-pool-empty]");
  if (empty) {
    empty.textContent = pools.length
      ? selectedType
        ? "Select required or excluded rules from the enabled individual rules in this pool."
        : "Select a pool to search."
      : "Add at least two eligible rules to a pool before searching.";
  }
}

function votingSearchProjectionCandidates(payload) {
  const collection = isRecord(payload?.candidates?.voting_search)
    ? payload.candidates.voting_search
    : {};
  const currentPoolRevisions = new Map(
    collectionItems(isRecord(payload?.pools) ? payload.pools : {})
      .map((pool) => [
        nonEmptyText(pool?.strategy_type),
        pool?.revision,
      ]),
  );
  const seen = new Set();
  return collectionItems(collection).filter((item) => {
    const searchId = nonEmptyText(item?.search_id);
    const strategyType = nonEmptyText(item?.strategy_type);
    if (
      !VOTING_SEARCH_ID_RE.test(searchId)
      || seen.has(searchId)
      || currentPoolRevisions.get(strategyType) !== item?.pool_revision
    ) {
      return false;
    }
    seen.add(searchId);
    return true;
  });
}

function votingSearchCombinations(search) {
  const seen = new Set();
  return (Array.isArray(search?.combinations) ? search.combinations : [])
    .filter((combo) => {
      const comboId = nonEmptyText(combo?.combo_id);
      if (!isRecord(combo) || !VOTING_COMBO_ID_RE.test(comboId) || seen.has(comboId)) {
        return false;
      }
      seen.add(comboId);
      return true;
    });
}

export function syncVotingBuildControls(
  form,
  payload,
  { preserveCombo = true } = {},
) {
  if (!form) return;
  const searches = votingSearchProjectionCandidates(payload);
  const searchSelect = formField(form, "voting_search_id");
  const comboSelect = formField(form, "voting_combo_id");
  if (!searchSelect || !comboSelect) return;
  const previousSearchId = nonEmptyText(searchSelect.value);
  searchSelect.innerHTML = [
    '<option value="">Select a voting search</option>',
    ...searches.map((search) => projectionOptionHtml(
      search.search_id,
      `${search.search_id} · ${search.strategy_type} · K=${stablePrimitiveText(search.member_count)} / n=${stablePrimitiveText(search.n)}`,
      {
        "candidate-lab-projection": "1",
        "strategy-type": nonEmptyText(search.strategy_type),
      },
    )),
  ].join("");
  if (selectContainsValue(searchSelect, previousSearchId)) {
    searchSelect.value = previousSearchId;
  } else if (searches.length === 1) {
    searchSelect.value = searches[0].search_id;
  } else {
    searchSelect.value = "";
  }
  const searchId = nonEmptyText(searchSelect.value);
  const search = searches.find((item) => item.search_id === searchId);
  const combinations = votingSearchCombinations(search);
  const previousComboId = nonEmptyText(comboSelect.value);
  const previousSource = nonEmptyText(
    Array.from(comboSelect.selectedOptions || [])[0]?.dataset?.sourceSearchId,
  );
  comboSelect.innerHTML = [
    '<option value="">Select a rule group</option>',
    ...combinations.map((combo) => projectionOptionHtml(
      combo.combo_id,
      `${combo.combo_id} · ${readableValue(combo.members)} · ${combo.eligible ? "Meets constraints" : "Fails constraints"}`,
      {
        "candidate-lab-projection": "1",
        "source-search-id": searchId,
      },
    )),
  ].join("");
  if (
    preserveCombo
    && previousSource === searchId
    && selectContainsValue(comboSelect, previousComboId)
  ) {
    comboSelect.value = previousComboId;
  } else {
    comboSelect.value = "";
  }
  const empty = form.querySelector?.("[data-candidate-lab-voting-search-empty]");
  if (empty) {
    empty.textContent = searches.length
      ? searchId
        ? combinations.length
          ? "Review the results and select a rule group."
          : "No evaluated groups are available in this result."
        : "Select a voting search result."
      : "Run a voting group search before continuing.";
  }
}

export function syncVotingForms(root, payload) {
  syncVotingSearchControls(votingSearchForm(root), payload);
  syncVotingBuildControls(votingBuildForm(root), payload);
}
