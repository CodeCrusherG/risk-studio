import { api, sleep } from "./js/api.js";
import {
  createAgentMemoryPanelController,
  formatMemoryConfidence,
} from "./js/agent-memory-panel.js";
import { createDraftToolsPanelController } from "./js/draft-tools-panel.js";
import {
  agentMessageIsAdvanceIntent,
  agentReportMessagesForDisplay,
  agentRerunMessageFingerprint,
  agentTimelineStageDefinitions,
} from "./js/agent-conversation-view.js";
import {
  removeAgentTimelineBuckets as removeAgentTimelineBucketsDom,
  renderAgentTimeline as renderAgentTimelineDom,
  restoreResultScrollDefaultOrder as restoreResultScrollDefaultOrderDom,
  updateAgentMessageContentsInPlace as updateAgentMessageContentsInPlaceDom,
} from "./js/agent-conversation-mount.js";
import { applyBranding, normalizeBranding } from "./js/branding.js";
import { createCreateTaskDialogController } from "./js/create-task-dialog.js";
import { createValidationBatchCreateController } from "./js/validation-batch-create.js";
import {
  bindDialogBackdropDismissal,
  createMaterialSourceController,
  renderMaterialUploadSelection,
} from "./js/dialogs.js";
import { installFormControlFocusRingGuard } from "./js/focus-ring.js";
import { createLayoutResizeController } from "./js/layout-resize.js";
import { createMaterialBindingDialogController } from "./js/material-binding-dialog.js";
import { createPlatformConfirmController } from "./js/platform-confirm.js";
import { claimProgressPoll, createProgressPollRegistry, releaseProgressPoll } from "./js/polling.js";
import { renderAgentMarkdown } from "./js/render-agent.js";
import {
  collectReportDraftValues,
  hasReportDraftValues,
  latestPendingReportDraftMessageId,
  reportDraftTableHtml,
  reportDraftFeedbackHtml,
} from "./js/report-draft-table.js";
import { createReportDraftState } from "./js/report-draft-state.js";
import { bindTaskRowPreview } from "./js/task-row-preview.js";
import { safeSameOriginApiHref } from "./js/url-safety.js";
import {
  attachCalibrationInteractions,
  attachMetricTooltip,
  attachRocInteractions,
  metricHeaderShouldRightAlign,
  renderCalibrationCard,
  renderMetricTableSection,
  renderScoreBandCard,
} from "./js/metric-tables.js";
import { renderPrecisionConsistencyChart } from "./js/precision-consistency.js";
import { stepCheckerHtml } from "./js/step-checker.js";
import {
  loadResultScrollPositions as loadStoredResultScrollPositions,
  persistResultScrollPositions as persistStoredResultScrollPositions,
  rememberSelectedTaskId as rememberStoredSelectedTaskId,
  storedSelectedTaskId as readStoredSelectedTaskId,
} from "./js/task-workspace-state.js";
import {
  renderCurrentTaskWorkspace,
  renderTaskSnapshot as renderTaskSnapshotView,
  updateWorkspaceGreeting as updateWorkspaceGreetingView,
} from "./js/task-workspace-view.js";
import { createTaskSearchController } from "./js/task-search.js";
import { defaultTaskType, taskTypeDisplayOrder } from "./js/task-types.js";
import { createThemeController } from "./js/theme.js";
import { createComingSoonToastController } from "./js/toast.js";
import {
  createValidationBatchPanelController,
  formatValidationBatchTaskName,
  isValidationBatchTask,
  normalizeValidationBatchPayload,
  parseTaskDeepLink,
  preferredStartupTaskId,
  syncTaskDeepLink,
  usesAgentValidationWorkbench,
} from "./js/validation-batch.js";
import { renderTierSettings, selectedTierStorageKey } from "./js/v2/capability.js";
import { createDataWorkspaceController } from "./js/v2/data_workspace_controller.js";
import { createDataWorkspacePanel } from "./js/v2/data_workspace_panel.js";
import {
  createLabelingSetupPanel,
} from "./js/v2/labeling_setup_panel.js";
import {
  createPortfolioSetupPanel,
  portfolioTurnUsesDeterministicRoute,
} from "./js/v2/portfolio_setup_panel.js";
import { uploadDataset } from "./js/v2/api_v2.js";
import {
  handleAdoptionConfirmClick as handleAdoptionConfirmClickController,
  renderAdoptionGate,
  submitAdoption as submitAdoptionController,
} from "./js/v2/adoption_gate_controller.js";
import {
  driverGateBodyHtml as driverGateBodyHtmlController,
  driverGateHasWidget as driverGateHasWidgetController,
  driverManualAnalysisHtml as driverManualAnalysisHtmlController,
  filterRecoveredWorkflowFailures,
  gateMessageForCurrentTool,
  lastAssistantMessageId as lastAssistantMessageIdController,
  latestInteractiveScreenMessageId as latestInteractiveScreenMessageIdController,
  stripChatInstructions as stripChatInstructionsController,
} from "./js/v2/driver_manual_analysis.js";
import {
  hasWorkflowErrorDiagnostic,
  workflowMessageContentHtml,
} from "./js/v2/workflow_error_card.js";
import {
  confirmationSnapshotsEqual,
  createDriverGateApi,
  driverGateActionable,
  driverGatePendingClaimSignature,
  handleDriverConfirmClick as handleDriverConfirmClickController,
  reconcileDriverGateSubmissions,
  renderDriverGateButton,
  submitDriverConfirm as submitDriverConfirmController,
} from "./js/v2/driver_gate_confirm.js";
import { mountGovernanceExtensionPanels } from "./js/v2/governance_extensions.js";
import {
  handleDatasetTablePointerOut,
  handleDatasetTablePointerOver,
} from "./js/v2/artifact_view.js";
import {
  handleC1ConfirmClick as handleC1ConfirmClickController,
  handleC1PreviewClick as handleC1PreviewClickController,
  handleC1RoleChange as handleC1RoleChangeController,
  handleDedupConfirmClick as handleDedupConfirmClickController,
  handleDedupExcludeClick as handleDedupExcludeClickController,
  handleJoinKeyConfirmClick as handleJoinKeyConfirmClickController,
  renderDedupPicker,
  renderJoinKeyPicker,
  renderJoinC1Form,
  submitC1Assignment as submitC1AssignmentController,
  submitDedupExclude as submitDedupExcludeController,
  submitDedupStrategies as submitDedupStrategiesController,
  submitJoinKeySelection as submitJoinKeySelectionController,
} from "./js/v2/join_gate_controller.js";
import {
  handleModelingSetupInteraction,
  handleModelingWeightAdjustClick as handleModelingWeightAdjustClickController,
  renderModelingSetupPanel,
  submitModelingWeightAdjust as submitModelingWeightAdjustController,
} from "./js/v2/modeling_setup_panel.js";
import { renderModelDeliveryPanel } from "./js/v2/model_delivery_panel.js";
import {
  hideSupersededTuningThinking,
  normalizeModelTuningProgress,
  renderModelTuningMessageProgress,
} from "./js/v2/model_tuning_progress.js";
import {
  mountWorkflowWidgetInteractions,
  renderWorkflowDataWidget,
} from "./js/v2/workflow_widgets.js";
import {
  handleFeatureBinningClick as handleFeatureBinningClickController,
  renderFeatureBinningGate,
} from "./js/v2/feature_binning_gate.js";
import {
  handleSpecialValueClick as handleSpecialValueClickController,
  renderSpecialValueGate,
} from "./js/v2/special_value_gate.js";
import {
  createPlanRailController,
  taskUsesPlanRail,
  workflowStatusSnapshot,
} from "./js/v2/plan_rail_controller.js";
import { renderPluginManager } from "./js/v2/plugin_manager.js";
import {
  handleScreenAdjustClick as handleScreenAdjustClickController,
  handleScreenAgentRecommendClick as handleScreenAgentRecommendClickController,
  handleScreenBulkClick as handleScreenBulkClickController,
  handleScreenChipClick as handleScreenChipClickController,
  handleScreenConfirmClick as handleScreenConfirmClickController,
  handleScreenPageClick as handleScreenPageClickController,
  handleScreenMetricFilterInput as handleScreenMetricFilterInputController,
  handleScreenPickChange as handleScreenPickChangeController,
  handleScreenSearchInput as handleScreenSearchInputController,
  handleScreenSortClick as handleScreenSortClickController,
  renderScreenGateTable,
  submitScreenSelection as submitScreenSelectionController,
  submitScreenThresholdAdjust as submitScreenThresholdAdjustController,
} from "./js/v2/screen_gate_controller.js";
import { renderSkillManager } from "./js/v2/skill_manager.js";
import {
  handleStrategyClarificationChange as handleStrategyClarificationChangeController,
  handleStrategyClarificationSubmit as handleStrategyClarificationSubmitController,
  isStrategyClarificationMessage as isStrategyClarificationMessageController,
  renderStrategyClarification,
} from "./js/v2/strategy_clarification_controller.js";
import { createStrategyCandidateLabController } from "./js/v2/strategy_candidate_lab_controller.js";
import { getSelectedTier, onSelectedTierChange } from "./js/v2/state_v2.js";
import {
  columnFractions,
  parseNumeric,
  psiTier,
  psiTooltipText,
} from "./js/render-metrics.js";
import {
  activeValidationStatuses,
  agentComposerPreferenceStorageKey,
  agentTaskComposerStorageKey,
  createRenderSignatures,
  defaultBranding,
  defaultExecutionEnvironment,
  defaultPetPreference,
  explicitPetNoneStorageKey,
  metricOverviewCompleteStatuses,
  notebookReproducibilityCompleteStatuses,
  petPositionStorageKey,
  petPreferenceStorageKey,
  requiredMaterialRoles,
  resultScrollPositionsStorageKey,
  roleLabels,
  scanFailurePrefix,
  selectedTaskStorageKey,
  statusLabels,
  terminalTaskStatuses,
  workflowSteps,
} from "./js/state.js";
import {
  $,
  clamp,
  escapeHtml,
  fileName,
  signatureFromParts,
} from "./js/ui-utils.js";

let selectedTaskId = null;
let selectedTask = null;
let projectedValidationChildTaskId = "";
let projectedValidationChildTask = null;
let taskCache = [];
const initialTaskDeepLink = parseTaskDeepLink(window.location.search);
let lastMetricValues = {};
let lastMetricValuesTaskId = null;
let lastMetricTableSections = [];
const taskBusyActions = new Map();
let createTaskInFlight = false;
const agentRequestAbortControllers = new Map();
const progressPolls = createProgressPollRegistry();
const resultScrollPositionsByTask = new Map();
let globalBusyAction = null;
let actionStatusOverride = null;
const themeController = createThemeController({
  onChange: () => renderSettingsState(),
});
let taskSearchQuery = "";
let taskSortMode = "created_desc";
let taskGroupMode = "none";
let executionEnvironmentOptions = [];
let executionEnvironmentSettings = null;
let llmSettings = { default_model_id: "", models: [], enabled_models: [] };
let llmEditingIndex = null;
let agentMessages = [];
const agentComposerPreferences = restoreAgentComposerPreferences();
let agentSelectedModelId = agentComposerPreferences.model_id || "";
let agentSelectedEffort = agentComposerPreferences.effort || "high";
let agentAcceptanceMode = agentComposerPreferences.acceptance_mode || "normal";
let agentBatchAutoRunGeneration = 0;
let agentBatchAutoRunPromise = null;
let lastAgentRenderSignature = null;
let lastAgentStructuralSignature = null;
// Manual-mode driver tasks now host every interactive control (gate confirm,
// retry entry, download, analysis cards) in the middle #agentMessages region.
// The per-second poll re-enters renderAgentConversation → renderDriverManualAnalysis
// each tick even though manual mode never reloads agentMessages, so guard the
// unconditional innerHTML rebuild with a content signature: unchanged messages =
// skip the rebuild, preserving :hover / focus / text selection / entry animation
// on whatever card the user is interacting with. Reset at the same task-switch /
// leave-mode points as lastAgentRenderSignature.
let lastDriverManualAnalysisSignature = null;
// Cached render-input signatures so the per-second polling loop can skip
// rewriting DOM regions whose visible inputs have not changed. Reset only
// when task selection, validation run, or filter/sort/search state changes.
const renderSignatures = createRenderSignatures();
const agentTypingState = new Map();
// messageId -> content as it appeared when the typewriter caught up and the
// server stopped streaming. Lets a later streaming-resumed render seed
// visible with the bytes the user already saw, instead of replaying from 0.
const agentTypingCompleted = new Map();
let agentTypingTimer = null;
let agentAutoScrollFrame = null;
// taskId -> [{triggerMessageId, stage, sectionId, headingHtml, label,
//             contentClassName, contentHtml}, ...]
// One entry per rerun event: the previous live section's preview is frozen
// at the moment the rerun is requested and rendered inline above the rerun
// user message so chart history persists alongside the chat history.
const taskFrozenSectionSnapshots = new Map();
let pendingResultScrollRestoreTaskId = null;
let resultScrollRestoreFrame = null;
let resultScrollPersistFrame = null;
let suppressAgentAutoScrollTaskId = null;
let pendingTaskContentLoadTaskId = null;
let taskContentSettleTimer = null;
let projectedChildContentLoadVersion = 0;
let latestNotebookSteps = [];
let latestValidationInputContract = null;
let latestValidationInputContractTaskId = "";
let latestValidationInputContractContext = null;
let validationInputContractLoadVersion = 0;
let sidebarCollapsed = false;
let sidebarSlideTimer = null;
let scanAbortController = null;
let petPreference = defaultPetPreference;
let petDragState = null;
let petReactionMood = null;
let petReactionKey = "";
let petReactionTimer = null;
let taskHeroGlassFrame = null;
let taskHeroGlassActive = null;
let taskHeroCanScroll = false;
const platformConfirm = createPlatformConfirmController({ getElementById: $ });
const showPlatformConfirm = platformConfirm.showPlatformConfirm;
const bindPlatformConfirmDialog = platformConfirm.bindPlatformConfirmDialog;
const { showComingSoonToast } = createComingSoonToastController({
  body: document.body,
  getElementById: $,
});
const materialSourceController = createMaterialSourceController({
  $,
  onFilesChanged: (files) => renderMaterialUploadSelection({ files, getElementById: $ }),
});
const createTaskDialog = createCreateTaskDialogController({
  $,
  materialSourceController,
  getSelectedTier,
  hasEnabledAgent: () => Boolean(llmSettings.enabled_models?.length),
  selectedTierStorageKey,
  onUnavailableTaskType: (message) => {
    showComingSoonToast(message);
    setActionStatus(message, "info", "This task type is not available yet.");
  },
});
const materialBindingDialog = createMaterialBindingDialogController({ $, api });
const validationBatchErrorTitle = "Batch operation failed.";

function restoreValidationBatchActionStatusAfterRecovery({ parentTaskId, message } = {}) {
  const normalizedParentTaskId = String(parentTaskId || "");
  if (!normalizedParentTaskId || selectedTaskId !== normalizedParentTaskId) return false;
  const transientErrorSignature = signatureFromParts([
    selectedTaskId,
    validationBatchErrorTitle,
    "error",
    message || "",
  ]);
  if (renderSignatures.actionStatus !== transientErrorSignature) return false;
  const snapshot = taskActionStatusSnapshot(selectedTask);
  setActionStatus(snapshot.message, snapshot.kind, snapshot.detail);
  return true;
}

const validationBatchPanelController = createValidationBatchPanelController({
  api,
  getElementById: $,
  getSelectedTask: () => selectedTask,
  deepLink: initialTaskDeepLink,
  confirmStart: ({ status, itemCount }) => {
    const continuingAfterContractReview = status === "awaiting_confirmation";
    const continuingPartialBatch = status === "partial_failure";
    return showPlatformConfirm({
      title: continuingAfterContractReview
        ? "Continue after confirming inputs?"
        : continuingPartialBatch
          ? "Continue validation batch?"
          : "Start model validation batch?",
      message: continuingAfterContractReview
        ? "All model inputs are confirmed. Confirm to continue running the models in batch order."
        : continuingPartialBatch
          ? "Retry failed or incomplete models. Completed models and their audit records will be kept."
          : `Run ${itemCount || 0} models in order. A failed model will not stop the remaining models.`,
      confirmText: continuingAfterContractReview ? "Confirm and continue" : "Start validation",
      cancelText: "Cancel",
    });
  },
  openContract: async ({ parentTaskId, childTaskId, itemId, modelName, modelVersion }) => {
    if (selectedTaskId !== parentTaskId || !selectedTaskIsValidationBatch()) return;
    await loadValidationInputContract(childTaskId, {
      parentTaskId,
      item: { id: itemId, modelName, modelVersion },
      throwOnError: true,
    });
  },
  refreshParentTask: async ({ parentTaskId } = {}) => {
    await refreshTasks();
    renderChangedValidationViews();
    if (!parentTaskId || selectedTaskId !== parentTaskId) return true;
    return taskServerBusyAction(selectedTask) !== "validation_batch";
  },
  onRecovered: restoreValidationBatchActionStatusAfterRecovery,
  onProjectedChildChange: ({ childTaskId, force } = {}) => {
    void applyProjectedValidationChild(childTaskId, { force });
  },
  onLayoutChange: () => syncTaskHeroGlassLayout(),
  onBatchMeta: ({ itemCount } = {}) => stampValidationBatchItemCount(itemCount),
  confirmAllReportDrafts: confirmAllValidationBatchReportDrafts,
  onError: (message) => {
    setActionStatus(validationBatchErrorTitle, "error", message);
  },
});
const validationBatchCreateController = createValidationBatchCreateController({
  api,
  getElementById: $,
  onCreated: async (payload) => {
    const parentTaskId = payload && payload.batch ? payload.batch.parent_task_id : "";
    if (!parentTaskId) throw new Error("The batch response did not include a parent task ID.");
    await refreshTasks();
    const parentTask = findTaskInCache(parentTaskId);
    if (!parentTask) throw new Error("Batch created, but its parent task could not be found. Refresh the task list.");
    selectTask(parentTask);
  },
});
const dataWorkspaceController = createDataWorkspaceController();
const dataWorkspacePanel = createDataWorkspacePanel({
  getElementById: $,
  controller: dataWorkspaceController,
  resolveNavigationChoice: resolveDataWorkspaceNavigationChoice,
  onError: reportDataWorkspaceError,
});
const labelingSetupPanel = createLabelingSetupPanel({
  getElementById: $,
  api,
  workspaceController: dataWorkspaceController,
  getSelectedTask: () => selectedTask,
  getAgentMessages: () => agentMessages,
  onMessages: (messages) => {
    if (Array.isArray(messages)) agentMessages = messages;
  },
  onSubmitted: async () => {
    renderAll();
    await reloadDataWorkspace(selectedTaskId, { silent: true });
    setActionStatus("Label settings updated.", "success");
  },
  onError: (error) => {
    setActionStatus("Label definition processing failed.", "error", String(error?.message || error || ""));
  },
});
const portfolioSetupPanel = createPortfolioSetupPanel({
  getElementById: $,
  api,
  getSelectedTask: () => selectedTask,
  getAgentMessages: () => agentMessages,
  onMessages: (messages) => {
    if (Array.isArray(messages)) agentMessages = messages;
  },
  onSubmitted: async () => {
    renderAll();
    await reloadDataWorkspace(selectedTaskId, { silent: true });
    setActionStatus("Portfolio settings validated. Confirm that delinquency buckets run from lowest to highest risk.", "success");
  },
  onError: (error) => {
    setActionStatus("Could not save portfolio analysis settings.", "error", String(error?.message || error || ""));
  },
});
const agentMemoryPanel = createAgentMemoryPanelController({
  $,
  api,
  runAction,
  showPlatformConfirm,
  openMemorySettings: (navKey) => openGovernanceSettingsCenter(navKey),
  openMemoryDetails: () => {
    // The management workspace is always visible now (no longer a fold), so
    // "View memory" just scrolls it into view within the Memorypanel.
    const section = $("memoryManageSection");
    if (section) section.scrollIntoView({ block: "nearest" });
  },
});
const draftToolsPanel = createDraftToolsPanelController({
  $,
  api,
  runAction,
  showPlatformConfirm,
});
const planRailController = createPlanRailController({
  $,
  stepCheckerHtml,
  getSelectedTask: () => selectedTask,
  getSelectedTaskId: () => selectedTaskId,
  getTaskBusyAction: () => taskBusyAction(selectedTaskId),
  setDriverExecutionBusy: (active, taskId) => setBusy(
    active ? "driver_execute" : null,
    active ? "Running the next step..." : "",
    taskId,
  ),
  getAgentMessages: () => agentMessages,
  isAgentMode: selectedTaskIsAgentMode,
  renderWorkflowStepper,
  setActionStatus,
  refreshTasks,
  loadAgentMessages,
  renderAll,
  fillComposer: focusAgentComposerForIntervene,
});
const driverGateApi = createDriverGateApi({
  api,
  getLocalBusyAction: (taskId) => taskBusyActions.get(taskId) || "",
  setDriverExecutionBusy: (active, taskId) => setBusy(
    active ? "driver_execute" : null,
    active ? "Running the next step..." : "",
    taskId,
  ),
  onSubmissionStateChange: (binding) => {
    if (selectedTaskId !== binding.taskId) return;
    renderAgentConversation();
    renderWorkflowStepper({ force: true });
  },
});
const strategyCandidateLabController = createStrategyCandidateLabController({
  $,
  getSelectedTask: () => selectedTask,
  getSelectedTaskId: () => selectedTaskId,
  getBlockedReason: () => {
    if (latestOpenGateMessage()) return "open_gate";
    if (selectedTask?.task_type === "strategy" && selectedTaskIsBusy()) return "active_plan";
    return "";
  },
  setActionStatus,
  setAgentMessages: (messages) => {
    if (Array.isArray(messages)) agentMessages = messages;
  },
  renderAgentConversation,
  pollAgentMessagesUntilSettled,
  settleCandidateLabSubmission: (taskId) => pollValidationProgress(
    terminalTaskStatuses,
    taskId,
    { settleWhenServerIdle: true },
  ),
  refreshAgentMessages: loadAgentMessages,
  resetPlanFetchThrottle: (taskId) => planRailController.resetFetchThrottle(taskId),
  renderWorkflowStepper,
});
const taskSearchController = createTaskSearchController({
  getElementById: $,
  getQuery: () => taskSearchQuery,
  setQuery: (value) => {
    taskSearchQuery = value;
  },
  renderTaskList: () => renderTaskList(),
});
const openTaskSearch = taskSearchController.openTaskSearch;
const closeTaskSearch = taskSearchController.closeTaskSearch;
const toggleTaskSearch = taskSearchController.toggleTaskSearch;
const taskSearchIsActive = taskSearchController.isActive;

const PET_REACTION_DURATION_MS = 6500;
const AGENT_STREAM_POLL_INTERVAL_MS = 180;
const AGENT_STREAM_POLL_IDLE_INTERVAL_MS = 1000;
const AGENT_STREAM_POLL_LONG_INTERVAL_MS = 3000;
const AGENT_STREAM_POLL_IDLE_AFTER_MS = 2000;
const AGENT_STREAM_POLL_LONG_AFTER_MS = 15000;
const AGENT_TYPEWRITER_INTERVAL_MS = 12;
const AGENT_TYPEWRITER_CHARS_PER_TICK = 2;
// When the typewriter falls far behind a streamed message, drain the backlog
// across at most this many ticks so big late chunks still feel like a reveal
// instead of a dump, but finish in well under a second.
const AGENT_TYPEWRITER_CATCHUP_TICKS = 15;
const AGENT_NO_ENABLED_MODEL_MESSAGE = "Configure and enable an AI model in Settings before sending a message.";
const AGENT_NO_SELECTED_MODEL_MESSAGE = "Select an AI model before sending a message.";
// Follow-mode state machine: the typewriter only pulls the viewport to the
// bottom while agentAutoScrollFollows is true. recomputeAgentAutoScrollFollow
// runs on scroll events that arrive within AGENT_USER_SCROLL_INPUT_WINDOW_MS
// of a real wheel/touch — programmatic scrollTo() calls (typewriter snap-to-
// bottom, saved-position restore) reach the handler with no recent input, so
// they leave the flag alone and cannot override a still-fresh user scroll-up.
const AGENT_AUTO_SCROLL_BOTTOM_TOLERANCE_PX = 2;
const AGENT_USER_SCROLL_INPUT_WINDOW_MS = 250;
let agentAutoScrollFollows = true;
let lastUserScrollInputAt = 0;
const layoutResizeController = createLayoutResizeController({
  body: document.body,
  clamp,
  getComputedStyleFn: getComputedStyle,
  root: document.documentElement,
  storage: localStorage,
  windowObj: window,
});
const startResizeDrag = layoutResizeController.startResizeDrag;
const handleResizeKey = layoutResizeController.handleResizeKey;
const restoreLayoutWidths = layoutResizeController.restoreLayoutWidths;
const taskSortModes = new Set(["created_desc", "created_asc", "name_asc", "name_desc"]);
const taskGroupModes = new Set(["none", "task_type", "validator", "created_month"]);
const petReactionMoods = new Set(["success", "failed", "complete", "review"]);
const petCatalog = globalThis.MarvisPetCatalog;
const petDefinitions = petCatalog.definitions;

executionEnvironmentSettings = { ...defaultExecutionEnvironment };

function taskStopped(task = selectedTask) {
  return task?.stopped === true;
}

function taskBusyAction(taskId = selectedTaskId) {
  if (!taskId) return globalBusyAction;
  const localBusyAction = taskBusyActions.get(taskId);
  if (localBusyAction) return localBusyAction;
  if (taskId === selectedTaskId) return taskServerBusyAction();
  if (taskId === projectedValidationChildTaskId) {
    return taskServerBusyAction(projectedValidationChildTask);
  }
  return null;
}

function taskServerBusyAction(task = selectedTask) {
  const kind = task?.active_job_kind || "";
  if (kind === "agent") return "agent";
  if (kind === "plan") return "agent";
  // REL-1/UX-1: the V2 driver turn (JOIN/feature/modeling/strategy/vintage
  // conversation confirm) now runs inside a task job of kind "driver" so this
  // busy state is visible after a refresh or from any entry point, not just the
  // tab that sent the confirm — and it claims the same 1s progress polling as
  // every other long-running kind below.
  if (kind === "driver") return "agent";
  if (kind === "join") return "join";
  if (kind === "validation_batch") return "validation_batch";
  if (kind === "pipeline" || kind === "notebook") return "notebook";
  if (kind === "metrics") return "metrics";
  if (kind === "report") return "report";
  if (taskStopped(task)) return null;
  return null;
}

function selectedTaskIsBusy() {
  return Boolean(taskBusyAction());
}

// Real validator name -> display alias, populated from the workspace brand.json
// via GET api/branding. Empty by default so real names never ship in this bundle.
let agentValidatorAliases = {};

async function loadBranding() {
  try {
    const payload = await api("api/branding");
    const branding = normalizeBranding(payload);
    agentValidatorAliases = branding.validatorAliases || {};
    applyBranding(branding);
  } catch (_error) {
    applyBranding(defaultBranding);
  }
}

function usesPmmlScoringWorkflow(task = workbenchTask()) {
  return Number(task?.validation_workflow_version) === 2;
}

function workflowStepForTask(step, task = selectedTask) {
  if (!usesPmmlScoringWorkflow(task)) return step;
  if (step.id === "notebook") {
    return {
      ...step,
      title: "PMML scoring",
      hint: "PMML scoring",
    };
  }
  if (step.id === "metrics") {
    return {
      ...step,
      title: "Model performance and stability",
      hint: "Performance, stability, and stress tests",
    };
  }
  if (step.id === "report") {
    return {
      ...step,
      hint: "Word validation report",
    };
  }
  return step;
}

function syncScoringSectionCopy(task = selectedTask) {
  const title = $("scoringSectionTitle");
  if (title) title.textContent = usesPmmlScoringWorkflow(task) ? "PMML scoring" : "Score comparison";
}

function currentTaskSignature(task) {
  if (!task) return "empty";
  return signatureFromParts([
    task.id || "",
    task.name || "",
    task.status || "",
    task.workflow_status || "",
    task.failure_stage || "",
    task.active_job_kind || "",
    task.status_message || "",
    task.model_name || "",
    task.item_count || "",
    task.validation_workflow_version || 0,
    task.report_available ? 1 : 0,
    taskStopped(task) ? 1 : 0,
    // Plan-rail state can change after the task payload has already rendered.
    // Include the derived label/tone so a failed current plan invalidates a
    // stale optimistic (Completed/Submitted)hero without waiting for task fields to
    // change independently.
    taskStatusLabel(task),
    taskStatusTone(task),
  ]);
}

function stepFingerprint(steps) {
  // Backend-driven progress fields ONLY. Wall-clock-derived elapsed must
  // stay out; clock ticks belong in a separate text-only refresher
  // (refreshWorkflowStepperElapsedTimes), not in the structural signature.
  return Array.isArray(steps)
    ? steps.map((step) => [
        step?.id || "",
        step?.status || "",
        step?.started_at || "",
        step?.ended_at || "",
        Number.isFinite(step?.elapsed_seconds) ? Number(step.elapsed_seconds) : "",
        Number.isFinite(step?.cell_count) ? Number(step.cell_count) : "",
      ])
    : [];
}

function workflowStepperSignature(task) {
  if (!task) return "empty";
  return signatureFromParts([
    task.id || "",
    task.status || "",
    task.failure_stage || "",
    taskFailureStage(task) || "",
    task.status_message || "",
    task.active_job_kind || "",
    task.validation_workflow_version || 0,
    task.report_available ? 1 : 0,
    taskStopped(task) ? 1 : 0,
    taskBusyAction(task.id) || "",
    stepFingerprint(notebookStepsForRail()),
    stepFingerprint(metricStepsForRail()),
  ]);
}

function taskListSignature(tasks, totalTaskCount) {
  const list = Array.isArray(tasks) ? tasks : [];
  return signatureFromParts([
    list.map((task) => [
      task.id || "",
      task.name || "",
      task.model_name || "",
      task.item_count || "",
      task.task_type || "",
      task.status || "",
      // Driver task rows display the active plan's derived status while the
      // task record itself commonly remains `created`.  Include that derived
      // state so a recovered plan (failed -> running) invalidates the list's
      // render guard instead of leaving the old failure pill behind.
      taskStatusLabel(task),
      taskStatusTone(task),
      task.updated_at || "",
      task.active_job_kind || "",
      task.validator || "",
    ]),
    Number.isFinite(totalTaskCount) ? totalTaskCount : 0,
    taskSearchQuery || "",
    taskSortMode || "",
    taskGroupMode || "",
    selectedTaskId || "",
  ]);
}

function metricPreviewSignature(taskId, metricValues, tableSections, emptyMessage = "") {
  return signatureFromParts([
    taskId || "",
    emptyMessage || "",
    metricValues || {},
    tableSections || [],
  ]);
}

function resetReproducibilityRenderSignatures() {
  renderSignatures.reproducibilityEvidence = "";
  renderSignatures.reproducibilityEmpty = "";
  renderSignatures.reproducibilityTaskId = "";
  renderSignatures.reproducibilityAnimatedTaskId = "";
}

function taskTypeDefinition(taskType = createTaskDialog.activeTaskType()) {
  return createTaskDialog.taskTypeDefinition(taskType);
}

function taskTypeLabel(taskOrType = selectedTask) {
  const taskType = typeof taskOrType === "string" ? taskOrType : taskOrType?.task_type;
  return taskTypeDefinition(taskType).label;
}

function syncCreateTaskTierDefault() {
  createTaskDialog.syncCreateTaskTierDefault();
}

function openTaskDialog(taskType = defaultTaskType) {
  createTaskDialog.openTaskDialog(taskType);
}

function openTaskDialogFromCard(event) {
  const card = event.target.closest("[data-task-kind]");
  if (!card) return;
  createTaskDialog.openTaskDialogFromCard(event);
}

function openTaskTypeWelcome() {
  const taskDialog = $("taskDialog");
  if (taskDialog?.open) closeTaskDialog();
  const batchCreateDialog = $("validationBatchCreateDialog");
  if (batchCreateDialog?.open) validationBatchCreateController.close();
  if (selectedTaskId || selectedTask) {
    deselectCurrentTask();
    return;
  }
  rememberSelectedTaskId(null);
  setActionStatus("");
  renderCurrentTask({ force: true });
  renderTaskList();
}

function closeTaskDialog() {
  createTaskDialog.closeTaskDialog();
}

function bindRunModeDeselectableCards() {
  createTaskDialog.bindRunModeDeselectableCards();
}

function openLLMSettingsDialog() {
  setLLMSettingsStatus("Loading AI model settings…");
  openGovernanceSettingsCenter("llm");
}

function closeLLMSettingsDialog() {
  closeGovernanceSettingsDialog();
}

const governanceSettingsCopy = {
  "execution-environment": {
    title: "Python environment",
    subtitle: "Choose the Python environment for Notebooks and analysis tools.",
  },
  llm: {
    title: "AI models",
    subtitle: "Manage the AI models available in conversations.",
  },
  "memory-policy": {
    title: "Memory",
    subtitle: "Choose how the agent uses and saves memory, and review its saved summaries.",
  },
  plugins: {
    title: "Plugin",
    subtitle: "View installed plugins and manage which tools are enabled.",
    extensionTitle: "Plugin",
    extensionDescription: "View installed plugins and manage which tools are enabled.",
  },
  workflows: {
    title: "Workflow Templates",
    subtitle: "Use built-in workflow templates or add a custom template.",
    extensionTitle: "Workflow Templates",
    extensionDescription: "Use built-in workflow templates or add a custom template.",
  },
  capabilities: {
    title: "Agent autonomy",
    subtitle: "Set how much planning the agent can perform. Required reviews and confirmations still apply.",
    extensionTitle: "Agent autonomy",
    extensionDescription: "Set how much planning the agent can perform. Required reviews and confirmations still apply.",
  },
};

let activeGovernanceNav = "execution-environment";

function governanceNavButton(navKey) {
  return document.querySelector(`[data-governance-nav="${navKey}"]`);
}

function activeGovernanceButton(navKey = activeGovernanceNav) {
  return governanceNavButton(navKey) || governanceNavButton("execution-environment");
}

function setGovernanceCopy(navKey, button) {
  const copy = governanceSettingsCopy[navKey] || governanceSettingsCopy["execution-environment"];
  $("governanceSettingsTitle").textContent = copy.title;
  $("governanceSettingsSubtitle").textContent = copy.subtitle;
  if (button?.dataset?.extensionView) {
    $("governanceExtensionTitle").textContent = copy.extensionTitle || copy.title;
    $("governanceExtensionDescription").textContent = copy.extensionDescription || copy.subtitle;
  }
}

// Single, context-aware refresh for the dialog title bar. Only panels that load
// remote data appear here; execution-environment keeps its own Scan Environmentaction.
const governanceRefreshActions = {
  plugins: () => runGovernanceExtensionAction(refreshGovernancePlugins),
  workflows: () => runGovernanceExtensionAction(refreshGovernanceSkills),
  capabilities: () => runGovernanceExtensionAction(refreshGovernanceCapability),
};

function syncGovernanceRefreshButton(navKey = activeGovernanceNav) {
  const button = $("governanceRefreshButton");
  if (!button) return;
  const unavailable = !governanceRefreshActions[navKey];
  button.classList.toggle("is-unavailable", unavailable);
  button.disabled = unavailable;
  button.setAttribute("aria-hidden", unavailable ? "true" : "false");
}

function refreshActiveGovernancePanel() {
  const action = governanceRefreshActions[activeGovernanceNav];
  if (!action) return;
  const button = $("governanceRefreshButton");
  if (button) {
    button.classList.add("is-spinning");
    window.setTimeout(() => button.classList.remove("is-spinning"), 700);
  }
  action();
}

function setGovernanceSettingsPanel(navKey = "execution-environment", options = {}) {
  const button = activeGovernanceButton(navKey);
  const normalizedNav = button?.dataset?.governanceNav || "execution-environment";
  const panel = button?.dataset?.governancePanel || "execution-environment";
  activeGovernanceNav = normalizedNav;
  syncGovernanceRefreshButton(normalizedNav);
  for (const item of document.querySelectorAll("[data-governance-nav]")) {
    const selected = item === button;
    item.classList.toggle("selected", selected);
    item.setAttribute("aria-selected", selected ? "true" : "false");
  }
  for (const section of document.querySelectorAll("[data-governance-panel-content]")) {
    section.classList.toggle("selected", section.dataset.governancePanelContent === panel);
  }
  const dialog = $("governanceSettingsDialog");
  dialog.dataset.governanceActive = normalizedNav;
  dialog.dataset.extensionView = button?.dataset?.extensionView || "";
  setGovernanceCopy(normalizedNav, button);
  if (panel === "extensions") {
    mountGovernanceExtensions();
    setGovernanceExtensionStatus("");
  }
}

function refreshGovernancePanel(navKey = activeGovernanceNav, options = {}) {
  const button = activeGovernanceButton(navKey);
  if (button?.dataset?.governancePanel === "execution-environment" && options.load !== false) {
    runAction(loadExecutionEnvironmentSettings, {
      actionId: "executionEnvironment",
      busyText: "Loading Python environment...",
      taskScoped: false,
    });
  }
  if (button?.dataset?.governancePanel === "llm" && options.load !== false) {
    runAction(loadLLMSettings, { actionId: "llmSettings", busyText: "Loading AI model settings…", taskScoped: false });
  }
  if (button?.dataset?.governancePanel === "memory-policy" && options.load !== false) {
    runAction(loadMemoryPolicySettings, { actionId: "memoryPolicy", busyText: "Reading Memory Policy...", taskScoped: false });
    // The management workspace is always visible now, so load its records when
    // the panel opens (once) instead of lazily on a fold's toggle event.
    if (!agentMemoryPanel.hasItems()) {
      runAction(loadAgentMemoryItems, { actionId: "agentMemory", busyText: "Loading task memories...", taskScoped: false });
    }
  }
}

function openGovernanceSettingsCenter(navKey = "execution-environment", options = {}) {
  closeSidebarSettingsMenu();
  setGovernanceSettingsPanel(navKey, { reloadMemory: false });
  const dialog = $("governanceSettingsDialog");
  if (!dialog.open) {
    dialog.showModal();
  }
  refreshGovernancePanel(navKey, options);
}

function closeGovernanceSettingsDialog() {
  $("governanceSettingsDialog").close();
}

function closeSidebarSettingsMenu() {
  const settings = $("sidebarSettings");
  if (!settings) return;
  settings.open = false;
}

let sidebarSettingsOpenFrame = 0;

function scheduleGovernanceSettingsFromSidebar() {
  if (sidebarSettingsOpenFrame || $("governanceSettingsDialog")?.open) return;
  sidebarSettingsOpenFrame = window.requestAnimationFrame(() => {
    sidebarSettingsOpenFrame = 0;
    openGovernanceSettingsCenter("execution-environment");
  });
}

function handleGovernanceSettingsNavClick(event) {
  const viewTab = event.target.closest("[data-agent-memory-view]");
  if (viewTab) {
    setAgentMemoryViewMode(viewTab.dataset.agentMemoryView, { reload: true });
    return;
  }
  const jump = event.target.closest("[data-governance-jump]");
  const navKey = jump
    ? jump.dataset.governanceJump
    : event.target.closest("[data-governance-nav]")?.dataset.governanceNav;
  if (!navKey) return;
  setGovernanceSettingsPanel(navKey, { reloadMemory: false });
  refreshGovernancePanel(navKey);
}

function handleGovernanceSettingsSearch(event) {
  const query = String(event.target.value || "").trim().toLowerCase();
  let visibleCount = 0;
  for (const item of document.querySelectorAll("[data-governance-nav]")) {
    const hidden = Boolean(query && !item.textContent.toLowerCase().includes(query));
    item.classList.toggle("hidden", hidden);
    if (!hidden) visibleCount += 1;
  }
  for (const group of document.querySelectorAll(".governance-nav-group")) {
    const visibleItems = group.querySelectorAll("[data-governance-nav]:not(.hidden)");
    group.classList.toggle("hidden", visibleItems.length === 0);
  }
  const empty = $("governanceSettingsNavEmpty");
  if (empty) empty.hidden = visibleCount !== 0;
}

function syncAgentMemoryViewControls() {
  agentMemoryPanel.syncViewControls();
}

function setAgentMemoryViewMode(mode, { reload = true } = {}) {
  agentMemoryPanel.setViewMode(mode, { reload });
}

function openWordPreviewDialog() {
  const taskId = workbenchTaskId();
  if (!taskId) return;
  const frame = $("wordPreviewFrame");
  const task = workbenchTask();
  const title = task ? reportTitleForTask(task) : "Word Report Preview";
  $("wordPreviewTitle").textContent = `${title} · Word Report Preview`;
  frame.src = `api/tasks/${taskId}/report/preview?t=${Date.now()}`;
  $("wordPreviewDialog").showModal();
  setActionStatus("Word Report preview is open.", "success");
}

function closeWordPreviewDialog() {
  $("wordPreviewDialog").close();
  $("wordPreviewFrame").src = "about:blank";
}

function applySidebarCollapsed(collapsed) {
  const shouldKeepPetOnLeftEdge = petIsPinnedToWorkspaceLeftEdge();
  sidebarCollapsed = Boolean(collapsed);
  const shell = $("appShell");
  // Keep expanded text laid out at the expanded width while the grid column slides away.
  const expandedWidth =
    parseInt(getComputedStyle(document.documentElement).getPropertyValue("--sidebar-width"), 10) || 314;
  document.documentElement.style.setProperty("--rail-content-width", `${expandedWidth}px`);
  if (document.body.classList.contains("anim-ready")) {
    document.body.classList.add("sidebar-sliding");
    clearTimeout(sidebarSlideTimer);
    sidebarSlideTimer = setTimeout(() => document.body.classList.remove("sidebar-sliding"), 340);
  }
  shell.classList.toggle("sidebar-collapsed", sidebarCollapsed);
  window.requestAnimationFrame(() => {
    if (shouldKeepPetOnLeftEdge) {
      pinPetToWorkspaceLeftEdge({ persist: true });
    } else {
      ensurePetWithinViewport({ persist: true });
    }
    if (document.body.classList.contains("anim-ready")) {
      window.setTimeout(() => {
        if (shouldKeepPetOnLeftEdge) {
          pinPetToWorkspaceLeftEdge({ persist: true });
        } else {
          ensurePetWithinViewport({ persist: true });
        }
      }, 340);
    }
  });
  const button = $("sidebarCollapseButton");
  button.setAttribute("aria-expanded", String(!sidebarCollapsed));
  button.setAttribute("aria-label", sidebarCollapsed ? "Expand Sidebar" : "Close Sidebar");
  button.title = sidebarCollapsed ? "Expand Sidebar" : "Close Sidebar";
  const brandTrigger = $("sidebarBrandTrigger");
  brandTrigger.classList.toggle("is-collapse-trigger", sidebarCollapsed);
  brandTrigger.tabIndex = sidebarCollapsed ? 0 : -1;
  if (sidebarCollapsed) {
    brandTrigger.setAttribute("role", "button");
    brandTrigger.setAttribute("aria-label", "Expand Sidebar");
    brandTrigger.title = "Expand Sidebar";
  } else {
    brandTrigger.removeAttribute("role");
    brandTrigger.removeAttribute("aria-label");
    brandTrigger.removeAttribute("title");
  }
}

function toggleSidebarCollapsed() {
  applySidebarCollapsed(!sidebarCollapsed);
  try {
    localStorage.setItem("sidebarCollapsed", sidebarCollapsed ? "1" : "0");
  } catch (_) {
    // Sidebar persistence is optional in restricted notebook browsers.
  }
}

function restoreSidebarCollapsed() {
  try {
    applySidebarCollapsed(window.matchMedia("(max-width: 860px)").matches || localStorage.getItem("sidebarCollapsed") === "1");
  } catch (_) {
    applySidebarCollapsed(window.matchMedia("(max-width: 860px)").matches);
  }
}

function expandSidebarFromBrand(event) {
  if (!sidebarCollapsed) return;
  event?.preventDefault();
  toggleSidebarCollapsed();
}

function handleSidebarBrandKeydown(event) {
  if (!sidebarCollapsed || !["Enter", " "].includes(event.key)) return;
  expandSidebarFromBrand(event);
}

// VD-5: V2 driver (plan-rail) tasks never reach the V1-only "review_required"
// task status while a gate sits open awaiting confirmation - the task record
// itself typically stays at "running", so without this the mascot kept
// spinning its busy mood while the system was actually idle, waiting on the
// human. This is a pure read of already-polled state (agentMessages / the
// gate's own red-flag metadata) - no new backend calls, upholding INV-4.
function latestOpenGateMessage() {
  for (let index = agentMessages.length - 1; index >= 0; index--) {
    const message = agentMessages[index];
    if (message?.role !== "assistant") continue;
    const meta = message?.metadata || {};
    if (meta.kind === "gate" || meta.join_c1) return message;
    return null;
  }
  return null;
}

function basePetMoodFromTask() {
  const status = selectedTask?.status || "";
  if (taskStopped(selectedTask)) return "idle";
  if (taskUsesPlanRail(selectedTask) && !selectedTaskIsBusy()) {
    const openGate = latestOpenGateMessage();
    if (openGate) {
      return driverGateRedFlags(openGate).length ? "failed" : "review";
    }
  }
  if (selectedTaskIsBusy()) return "running";
  if (status === "succeeded") return "success";
  if (status === "failed") return "failed";
  if (status === "review_required") return "review";
  if (["running", "computing_metrics"].includes(status)) return "running";
  if (["scanned", "executed", "writing_artifacts"].includes(status)) return "complete";
  return "idle";
}

function clearPetReactionTimer() {
  if (!petReactionTimer) return;
  clearTimeout(petReactionTimer);
  petReactionTimer = null;
}

function petReactionKeyForMood(mood) {
  if (!petReactionMoods.has(mood)) return "";
  const task = selectedTask;
  return [
    task?.id || "",
    task?.status || "",
    task?.updated_at || "",
    task?.status_message || "",
    mood,
  ].join("|");
}

function schedulePetReactionReset(key) {
  clearPetReactionTimer();
  petReactionTimer = setTimeout(() => {
    if (petReactionKey !== key) return;
    petReactionMood = null;
    renderPetState();
  }, PET_REACTION_DURATION_MS);
}

function petMoodFromTask() {
  const mood = basePetMoodFromTask();
  if (!petReactionMoods.has(mood)) {
    petReactionMood = null;
    petReactionKey = "";
    clearPetReactionTimer();
    return mood;
  }

  const key = petReactionKeyForMood(mood);
  if (petReactionKey !== key) {
    petReactionMood = mood;
    petReactionKey = key;
    schedulePetReactionReset(key);
  }
  return petReactionMood || "idle";
}

function normalizePetPreference(value) {
  return petCatalog.normalizePreference(value);
}

function persistPetPreference(value, explicitNone = false) {
  try {
    localStorage.setItem(petPreferenceStorageKey, value);
    if (value === petCatalog.noneId && explicitNone) {
      localStorage.setItem(explicitPetNoneStorageKey, "1");
    } else {
      localStorage.removeItem(explicitPetNoneStorageKey);
    }
  } catch (_) {
    // Pet preference is optional in restricted notebook browsers.
  }
}

function applyPetPreference(value, options = {}) {
  const { persist = true, explicit = false } = options;
  const normalized = normalizePetPreference(value);
  petPreference = normalized;
  if ($("settingsPetSelect")) $("settingsPetSelect").value = petPreference;
  if (persist) {
    persistPetPreference(petPreference, explicit);
  }
  renderPetState();
  ensurePetWithinViewport({ persist });
}

function restorePetPreference() {
  try {
    const stored = localStorage.getItem(petPreferenceStorageKey);
    const explicitNone = localStorage.getItem(explicitPetNoneStorageKey) === "1";
    const normalized = stored ? petCatalog.resolveStoredPreference(stored, explicitNone) : petCatalog.noneId;
    applyPetPreference(normalized, { persist: Boolean(stored) && normalized !== stored });
  } catch (_) {
    applyPetPreference(petCatalog.noneId, { persist: false });
  }
}

function applyPetPosition(left, top) {
  const pet = $("petCompanion");
  if (!pet) return;
  const workspace = $("validationWorkspace")?.getBoundingClientRect();
  const offsetLeft = workspace ? left - workspace.left : left;
  pet.style.setProperty("--pet-offset-left", `${Math.round(offsetLeft)}px`);
  pet.style.left = "";
  pet.style.top = `${Math.round(top)}px`;
  pet.style.right = "auto";
  pet.style.bottom = "auto";
}

function savePetPosition(left, top) {
  try {
    const workspace = $("validationWorkspace")?.getBoundingClientRect();
    const payload = { left, top };
    if (workspace) payload.workspaceOffsetLeft = left - workspace.left;
    localStorage.setItem(petPositionStorageKey, JSON.stringify(payload));
  } catch (_) {
    // Drag position persistence is optional in restricted notebook browsers.
  }
}

function restorePetPosition() {
  try {
    const stored = JSON.parse(localStorage.getItem(petPositionStorageKey) || "{}");
    const workspace = $("validationWorkspace")?.getBoundingClientRect();
    const storedLeft =
      workspace && Number.isFinite(stored.workspaceOffsetLeft)
        ? workspace.left + stored.workspaceOffsetLeft
        : stored.left;
    if (Number.isFinite(storedLeft) && Number.isFinite(stored.top)) {
      const next = clampPetPosition(storedLeft, stored.top);
      applyPetPosition(next.left, next.top);
      if (
        next.left !== stored.left ||
        next.top !== stored.top ||
        !Number.isFinite(stored.workspaceOffsetLeft)
      ) {
        savePetPosition(next.left, next.top);
      }
    }
  } catch (_) {
    // Keep the default fixed bottom-left workspace position.
  }
}

function petCssPx(name, fallback) {
  const pet = $("petCompanion");
  const host = pet || $("appShell") || document.documentElement;
  const value = getComputedStyle(host).getPropertyValue(name);
  const parsed = parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function petDragBounds() {
  const pet = $("petCompanion");
  const workspace = $("validationWorkspace")?.getBoundingClientRect();
  const padding = 14;
  const minWorkspaceOffset = petCssPx("--pet-min-workspace-offset", padding);
  const minLeft = Math.max(
    padding,
    workspace ? workspace.left + minWorkspaceOffset : minWorkspaceOffset,
  );
  const minTop = Math.max(padding, workspace ? workspace.top + padding : padding);
  const maxLeft = Math.max(minLeft, window.innerWidth - (pet?.offsetWidth || 104) - padding);
  const maxTop = Math.max(minTop, window.innerHeight - (pet?.offsetHeight || 116) - padding);
  return { minLeft, minTop, maxLeft, maxTop };
}

function petWorkspaceOffset() {
  const pet = $("petCompanion");
  const workspace = $("validationWorkspace")?.getBoundingClientRect();
  if (!pet || !workspace) return null;
  return pet.getBoundingClientRect().left - workspace.left;
}

function petIsPinnedToWorkspaceLeftEdge() {
  const pet = $("petCompanion");
  if (!pet || pet.classList.contains("hidden")) return false;
  const offset = petWorkspaceOffset();
  if (!Number.isFinite(offset)) return false;
  const minWorkspaceOffset = petCssPx("--pet-min-workspace-offset", 14);
  return Math.abs(offset - minWorkspaceOffset) <= 2;
}

function pinPetToWorkspaceLeftEdge(options = {}) {
  const { persist = false } = options;
  const pet = $("petCompanion");
  const workspace = $("validationWorkspace")?.getBoundingClientRect();
  if (!pet || !workspace || pet.classList.contains("hidden")) return;
  const minWorkspaceOffset = petCssPx("--pet-min-workspace-offset", 14);
  const rect = pet.getBoundingClientRect();
  const next = clampPetPosition(workspace.left + minWorkspaceOffset, rect.top);
  applyPetPosition(next.left, next.top);
  if (persist) savePetPosition(next.left, next.top);
}

function clampPetPosition(left, top) {
  const bounds = petDragBounds();
  return {
    left: clamp(left, bounds.minLeft, bounds.maxLeft),
    top: clamp(top, bounds.minTop, bounds.maxTop),
  };
}

function ensurePetWithinViewport(options = {}) {
  const { persist = false } = options;
  const pet = $("petCompanion");
  if (!pet || pet.classList.contains("hidden")) return;
  const rect = pet.getBoundingClientRect();
  const next = clampPetPosition(rect.left, rect.top);
  if (Math.round(next.left) === Math.round(rect.left) && Math.round(next.top) === Math.round(rect.top)) return;
  applyPetPosition(next.left, next.top);
  if (persist) savePetPosition(next.left, next.top);
}

function renderPetState() {
  const pet = $("petCompanion");
  const sticker = $("petSticker");
  if (!pet || !sticker) return;

  const definition = petPreference === petCatalog.noneId ? null : petDefinitions[petPreference];
  pet.classList.toggle("hidden", !definition);
  pet.dataset.petId = petPreference;
  if (!definition) {
    sticker.replaceChildren();
    delete sticker.dataset.petId;
    pet.dataset.petMood = "idle";
    pet.setAttribute("aria-label", "No pets shown");
    return;
  }

  if (sticker.dataset.petId !== petPreference) {
    sticker.replaceChildren();
    if (definition.kind === "spritesheet") {
      const sprite = document.createElement("div");
      sprite.className = "pet-sprite";
      sprite.style.backgroundImage = `url("${definition.asset}")`;
      sprite.setAttribute("aria-hidden", "true");
      sticker.appendChild(sprite);
    } else {
      const image = document.createElement("img");
      image.className = "pet-image";
      image.src = definition.asset;
      image.alt = "";
      image.decoding = "async";
      image.draggable = false;
      sticker.appendChild(image);
    }
    sticker.dataset.petId = petPreference;
  }
  const mood = petMoodFromTask();
  pet.dataset.petMood = mood;
  pet.setAttribute("aria-label", `${definition.name},${definition.label}, current status: ${mood}`);
  ensurePetWithinViewport({ persist: false });
}

function startPetDrag(event) {
  const pet = $("petCompanion");
  if (!pet || pet.classList.contains("hidden")) return;
  if (event.button !== undefined && event.button !== 0) return;
  event.preventDefault();
  const rect = pet.getBoundingClientRect();
  petDragState = {
    offsetX: event.clientX - rect.left,
    offsetY: event.clientY - rect.top,
  };
  pet.classList.add("dragging");

  function onPointerMove(moveEvent) {
    if (!petDragState) return;
    const next = clampPetPosition(moveEvent.clientX - petDragState.offsetX, moveEvent.clientY - petDragState.offsetY);
    const current = pet.getBoundingClientRect();
    pet.dataset.petMood = next.left >= current.left ? "running-right" : "running-left";
    applyPetPosition(next.left, next.top);
  }

  function onPointerUp() {
    const current = pet.getBoundingClientRect();
    petDragState = null;
    pet.classList.remove("dragging");
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", onPointerUp);
    savePetPosition(current.left, current.top);
    renderPetState();
  }

  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp);
}

function renderSettingsState() {
  if ($("settingsSortSelect")) $("settingsSortSelect").value = taskSortMode;
  if ($("settingsGroupSelect")) $("settingsGroupSelect").value = taskGroupMode;
  if ($("settingsThemeSelect")) $("settingsThemeSelect").value = themeController.preference;
  if ($("settingsPetSelect")) $("settingsPetSelect").value = petPreference;
  renderExecutionEnvironmentSummary();
  renderLLMSettingsSummary();
}

function normalizeTaskSortMode(value) {
  return taskSortModes.has(value) ? value : "created_desc";
}

function normalizeTaskGroupMode(value) {
  return taskGroupModes.has(value) ? value : "none";
}

function saveTaskListSettings() {
  try {
    localStorage.setItem("marvis_task_list_settings", JSON.stringify({
      sort: taskSortMode,
      group: taskGroupMode,
    }));
  } catch (_) {
    // Sidebar list preferences are optional in restricted notebook browsers.
  }
}

function restoreTaskListSettings() {
  try {
    const stored = JSON.parse(localStorage.getItem("marvis_task_list_settings") || "{}");
    taskSortMode = normalizeTaskSortMode(stored.sort);
    taskGroupMode = normalizeTaskGroupMode(stored.group);
  } catch (_) {
    taskSortMode = "created_desc";
    taskGroupMode = "none";
  }
}

function handleSettingsMenuChange(event) {
  const target = event.target;
  if (target.id === "settingsSortSelect") {
    taskSortMode = normalizeTaskSortMode(target.value);
    saveTaskListSettings();
    renderTaskList();
    renderSettingsState();
    return;
  }
  if (target.id === "settingsGroupSelect") {
    taskGroupMode = normalizeTaskGroupMode(target.value);
    saveTaskListSettings();
    renderTaskList();
    renderSettingsState();
    return;
  }
  if (target.id === "settingsThemeSelect") {
    themeController.applyTheme(target.value);
  }
  if (target.id === "settingsPetSelect") {
    applyPetPreference(target.value, { explicit: true });
  }
}

function taskDisplayName(task) {
  if (!task) return "";
  if (isValidationBatchTask(task)) {
    if (Number.isInteger(Number(task.item_count)) && Number(task.item_count) > 0) {
      return formatValidationBatchTaskName(task.created_at, task.item_count);
    }
    const stored = String(task.model_name || "").trim();
    if (/^\d{4}-\d{2}-\d{2} Model Validation Batch/.test(stored)) return stored;
    return formatValidationBatchTaskName(task.created_at, task.item_count);
  }
  const name = String(task.model_name || "").trim();
  const version = String(task.model_version || "").trim();
  return version ? `${name} · ${version}` : name;
}

function stampValidationBatchItemCount(itemCount) {
  const count = Number(itemCount);
  if (!selectedTaskIsValidationBatch() || !Number.isInteger(count) || count < 1) return;
  const nextName = formatValidationBatchTaskName(selectedTask.created_at, count);
  const currentName = String(selectedTask.model_name || "").trim();
  if (Number(selectedTask?.item_count) === count && currentName === nextName) return;
  selectedTask = { ...selectedTask, item_count: count, model_name: nextName };
  taskCache = taskCache.map((task) => (
    task.id === selectedTaskId ? { ...task, item_count: count, model_name: nextName } : task
  ));
  renderCurrentTask();
  renderTaskList();
}

function reportTitleForTask(task) {
  const displayName = taskDisplayName(task);
  return displayName ? `${displayName} — Model validation report` : "No task selected";
}

function setCreateStatus(message, kind = "info") {
  createTaskDialog.setCreateStatus(message, kind);
}

function setExecutionEnvironmentStatus(message, kind = "info") {
  const status = $("executionEnvironmentStatus");
  status.textContent = message;
  status.className = `status ${kind}`;
}

function actionStatusPill(
  message,
  kind,
  task = typeof selectedTask !== "undefined" ? selectedTask : null,
) {
  if (!message) return null;
  if (kind === "error") {
    return /Review/.test(message)
      ? { label: "Pending review", tone: "ok" }
      : { label: "Failed", tone: "fail" };
  }
  if (kind === "stopped") return { label: "Stop", tone: "neutral" };
  if (kind === "busy") return { label: "Ongoing", tone: "run" };
  if (kind === "success") {
    if (taskStopped(task)) return { label: "Stop", tone: "neutral" };
    const planSnapshot = task && taskUsesPlanRail(task)
      ? taskPlanWorkflowStatusSnapshot(task)
      : null;
    const wholeTaskComplete = task
      ? (taskUsesPlanRail(task)
        ? ["Completed", "Pending review"].includes(String(planSnapshot?.label || ""))
        : ["succeeded", "review_required"].includes(String(task?.status || "")))
      : true;
    if (wholeTaskComplete) return { label: "Completed", tone: "ok" };
    if (/(?:Wait|Please.).*Confirm.|To be confirmed/.test(message)) {
      return { label: "To be confirmed", tone: "review" };
    }
    return { label: "Ready to continue", tone: "review" };
  }
  if (kind === "info" && /(?:Wait|- Wait.|Please.).*Confirm./.test(message)) {
    return { label: "To be confirmed", tone: "review" };
  }
  return { label: "Pending", tone: "neutral" };
}

function describeActionStatus(message, kind, detail) {
  if (!message) return "";
  const compactDetail = compactActionStatusDetail(detail);
  if (compactDetail && compactDetail !== message) return `${message} · ${compactDetail}`;
  return message;
}

function compactActionStatusDetail(value, maxChars = 180) {
  const firstLine = String(value || "").split(/\r?\n/, 1)[0].trim();
  if (firstLine.length <= maxChars) return firstLine;
  return `${firstLine.slice(0, Math.max(0, maxChars - 1)).trimEnd()}…`;
}

function setActionErrorDetail(message = "", kind = "info") {
  const detail = $("actionErrorDetail");
  if (!detail) return;
  detail.textContent = message || "";
  detail.setAttribute("role", kind === "error" ? "alert" : "status");
  detail.setAttribute("aria-live", kind === "error" ? "assertive" : "polite");
  detail.className = `action-error-detail ${kind === "error" ? "error" : ""}`.trim();
}

function setActionStatus(message, kind = "info", detail = "") {
  const info = actionStatusPill(message, kind, selectedTask);
  const nextSignature = signatureFromParts([
    selectedTaskId || "",
    message || "",
    kind || "info",
    detail || "",
    info?.label || "",
    info?.tone || "",
  ]);
  if (renderSignatures.actionStatus === nextSignature) return;
  renderSignatures.actionStatus = nextSignature;

  const pill = $("actionStatus");
  if (pill) {
    pill.textContent = info ? info.label : "";
    pill.className = `task-pill ${info ? info.tone : ""}`.trim();
    const hero = pill.closest(".task-hero");
    if (hero) hero.dataset.tone = info ? info.tone : "";
  }
  setActionErrorDetail(describeActionStatus(message, kind, detail), kind);
  requestAnimationFrame(syncTaskHeroGlassLayout);
}

function setActionStatusOverride(message, kind = "info", detail = "") {
  if (!selectedTaskId) {
    setActionStatus(message, kind, detail);
    return;
  }
  actionStatusOverride = { taskId: selectedTaskId, message, kind, detail };
  setActionStatus(message, kind, detail);
}

function clearActionStatusOverride(taskId = selectedTaskId) {
  if (!actionStatusOverride) return;
  if (!taskId || actionStatusOverride.taskId === taskId) actionStatusOverride = null;
}

function taskFailureActionStatusMessage(task = selectedTask) {
  if (!task || !["failed", "review_required"].includes(task.status)) return "";
  if (task.status === "review_required") return "Validation is complete. Review the report in the right panel.";
  if (task.status_message) return task.status_message;
  return "Task failed. Review the details and try again.";
}

function taskStoppedActionStatusMessage(task = selectedTask) {
  if (!taskStopped(task)) return "";
  return "The current action has stopped. Enter your next instruction.";
}

function taskFailedDuringScan(task = selectedTask) {
  return task?.status === "failed" && normalizedFailureStage(task.failure_stage) === "scan";
}

function taskFailureWasRestartReclaim(task = selectedTask) {
  return task?.status === "failed" && task?.failure_reason_code === "server_restart_while_running";
}

function normalizedFailureStage(stage) {
  const value = String(stage || "");
  return ["scan", "notebook", "metrics", "report"].includes(value) ? value : null;
}

function failureStageRank(stage) {
  return {
    scan: 0,
    notebook: 1,
    metrics: 2,
    report: 3,
  }[stage] ?? Number.POSITIVE_INFINITY;
}

function earliestFailureStage(...stages) {
  const normalizedStages = stages
    .map((stage) => normalizedFailureStage(stage))
    .filter(Boolean);
  if (normalizedStages.length === 0) return null;
  return normalizedStages.reduce((earliest, stage) => (
    failureStageRank(stage) < failureStageRank(earliest) ? stage : earliest
  ));
}

function notebookStepStageFailure() {
  if (notebookStepsForRail().some((step) => notebookStepTone(step?.status) === "failed")) {
    return "notebook";
  }
  if (metricStepsForRail().some((step) => notebookStepTone(step?.status) === "failed")) {
    return "metrics";
  }
  return null;
}

function taskFailureStage(task = selectedTask) {
  if (!task || task.status !== "failed") return null;
  const structuredStage = normalizedFailureStage(task.failure_stage);
  return earliestFailureStage(structuredStage, notebookStepStageFailure());
}

function taskFailedDuringMetrics(task = selectedTask) {
  return taskFailureStage(task) === "metrics";
}

function taskFailedDuringReport(task = selectedTask) {
  return taskFailureStage(task) === "report";
}

function taskFailedDuringNotebook(task = selectedTask) {
  return taskFailureStage(task) === "notebook";
}

function taskFailureActionStatusTitle(task = selectedTask) {
  if (!task || !["failed", "review_required"].includes(task.status)) return "";
  if (task.status === "review_required") return "Validation complete; review required.";
  const stage = taskFailureStage(task);
  if (stage === "scan") return "Could not identify input files.";
  if (stage === "metrics") return "Performance and stability checks failed.";
  if (stage === "report") return "Report output failed.";
  if (stage === "notebook") {
    return usesPmmlScoringWorkflow(task) ? "PMML scoring failed." : "Model reproducibility validation failed.";
  }
  return "Task failed.";
}

function taskStoppedActionStatusTitle(task = selectedTask) {
  if (!taskStopped(task)) return "";
  return "Stopped the current action.";
}

function setTaskFailureActionStatus(task = selectedTask) {
  if (taskStopped(task)) {
    setActionStatus(
      taskStoppedActionStatusTitle(task),
      "stopped",
      taskStoppedActionStatusMessage(task),
    );
    return true;
  }
  const message = taskFailureActionStatusMessage(task);
  if (!message) return false;
  const kind = task.status === "review_required" ? "success" : "error";
  setActionStatus(taskFailureActionStatusTitle(task), kind, message);
  return true;
}

function actionFailureStatusTitle(actionId) {
  switch (actionId) {
    case "agent":
      return "Agent action failed.";
    case "join":
      return "Data join failed.";
    case "scan":
      return "Could not identify input files.";
    case "notebook":
      return usesPmmlScoringWorkflow() ? "PMML scoring failed." : "Model reproducibility validation failed.";
    case "metrics":
      return "Could not calculate metrics.";
    case "report":
      return "Report output failed.";
    case "delete":
      return "Could not delete the task.";
    default:
      return "Operation failed.";
  }
}

function actionCancelledStatusTitle(actionId) {
  switch (actionId) {
    case "scan":
      return "File scan stopped.";
    case "notebook":
    case "cancelNotebook":
      return usesPmmlScoringWorkflow() ? "PMML scoring stopped. You can restart it." : "Notebook stopped. You can rerun it.";
    case "metrics":
    case "cancelMetrics":
      return "Metric calculation stopped. You can rerun it.";
    case "report":
    case "cancelReport":
      return "Report generation stopped. You can rerun it.";
    default:
      return "Operation stopped.";
  }
}

function taskActionStatusSnapshot(task = selectedTask) {
  if (!task) return { message: "", kind: "info", detail: "" };
  if (taskStopped(task)) {
    return { message: "Stopped the current action.", kind: "stopped", detail: "The current step stopped. You can restart it." };
  }
  if (task.active_job_kind === "join") {
    return { message: "Joining data...", kind: "busy", detail: "Current step: Join data." };
  }
  if (task.active_job_kind === "plan") {
    return { message: "Running the plan...", kind: "busy", detail: "Current step: Run the confirmed plan." };
  }
  if (task.active_job_kind === "validation_batch") {
    return {
      message: "Batch model validation is in progress.",
      kind: "busy",
      detail: "Models are being validated in batch order.",
    };
  }
  // REL-1/UX-1: V2 driver-turn task (data_join/feature_analysis/modeling/
  // strategy/vintage) job — these task types don't carry the V1.1 validation
  // task.status values the switch below keys on, so without this the busy pill
  // would go blank for the whole turn instead of showing "Running the next step...".
  if (task.active_job_kind === "driver") {
    return { message: "Running the next step...", kind: "busy", detail: "Current step: Run the workflow." };
  }
  const usesPlanWorkflow = typeof taskUsesPlanRail === "function" && taskUsesPlanRail(task);
  const workflowSnapshot = taskPlanWorkflowStatusSnapshot(task);
  if (workflowSnapshot) return workflowSnapshot;
  // Driver/portfolio task.status reuses the shared task record and can look
  // terminal after a setup/contract sub-stage. Until an authoritative plan or
  // workflow_status says `done`, never feed that value into the validation-only
  // switch below (which would claim the whole task/report is complete).
  if (usesPlanWorkflow) {
    return {
      message: "Confirm the next step.",
      kind: "info",
      detail: "Review the current step in the conversation and confirm to continue.",
    };
  }
  switch (task.status) {
    case "created":
      return { message: "Task created.", kind: "info", detail: "Next step: Identify input files." };
    case "scanned":
    case "configured":
      return {
        message: "Input files identified.",
        kind: "success",
        detail: usesPmmlScoringWorkflow(task)
          ? "Input files identified. Next: PMML scoring."
          : "Input files identified. Next: model reproducibility validation.",
      };
    case "running":
      return {
        message: usesPmmlScoringWorkflow(task) ? "PMML scoring tests are ongoing." : "Validating model reproducibility...",
        kind: "busy",
        detail: usesPmmlScoringWorkflow(task) ? "Current step: Parse PMML and score all rows." : "Current step: Run the notebook and compare scores.",
      };
    case "executed":
      return {
        message: usesPmmlScoringWorkflow(task) ? "PMML scoring complete." : "Model reproducibility validation complete.",
        kind: "success",
        detail: usesPmmlScoringWorkflow(task)
          ? "PMML scoring complete. Next: performance, stability, and stress tests."
          : "Model reproducibility validated. Next: performance and stability checks.",
      };
    case "computing_metrics":
      return {
        message: "Calculating metrics...",
        kind: "busy",
        detail: "Current step: Performance, stability, and stress tests.",
      };
    case "writing_artifacts":
      // writing_artifacts is dual-meaning: backend flips here the moment
      // metrics finishes (idle, awaiting "GenerateWord") and stays here while
      // the report job actually runs. Only the second case is in-progress.
      if (task.active_job_kind === "report") {
        return {
          message: "The report is in progress.",
          kind: "busy",
          detail: "Current step: Generate conclusions, the Word report, and Excel analysis.",
        };
      }
      return {
        message: "Performance and stability checks complete.",
        kind: "success",
        detail: "Performance, stability, and stress tests complete. Next: generate reports.",
      };
    case "succeeded":
      return {
        message: "Validation complete.",
        kind: "success",
        detail: usesPmmlScoringWorkflow(task)
          ? "File checks, PMML scoring, model validation, and reports are complete."
          : "File checks, reproducibility validation, model validation, and reports are complete.",
      };
    case "review_required":
      return {
        message: "Validation complete; manual review required.",
        kind: "success",
        detail: "Validation and reports are complete. Review the results before using them.",
      };
    default:
      return { message: "", kind: "info", detail: task.status_message || "" };
  }
}

function clearStatus() {
  setCreateStatus("");
  setActionStatus("");
}

function statusLabel(status) {
  return statusLabels[status] || status || "Unknown";
}

function planWorkflowCompletionIsUnproven(task, planSnapshot) {
  if (planSnapshot || !taskUsesPlanRail(task)) return false;
  return [
    "scanned",
    "configured",
    "executed",
    "writing_artifacts",
    "succeeded",
    "review_required",
  ].includes(String(task?.status || ""));
}

function taskPlanWorkflowStatusSnapshot(task) {
  if (
    typeof taskUsesPlanRail === "function"
    && typeof planRailController !== "undefined"
    && taskUsesPlanRail(task)
  ) {
    const planSnapshot = planRailController.statusSnapshot(task?.id);
    if (planSnapshot) return planSnapshot;
  }
  return workflowStatusSnapshot(task?.workflow_status);
}

function taskStatusLabel(task) {
  if (taskStopped(task)) return "Stop";
  const planSnapshot = taskPlanWorkflowStatusSnapshot(task);
  if (planSnapshot?.label) return planSnapshot.label;
  if (
    typeof planWorkflowCompletionIsUnproven === "function"
    && planWorkflowCompletionIsUnproven(task, planSnapshot)
  ) return "To be confirmed";
  return statusLabel(task?.status);
}

function statusTone(status) {
  if (status === "failed") return "danger";
  if (status === "review_required") return "success";
  if (status === "succeeded" || status === "executed") return "success";
  if (status === "running" || status === "computing_metrics") return "run";
  return "";
}

function taskStatusTone(task) {
  if (taskStopped(task)) return "";
  const planSnapshot = taskPlanWorkflowStatusSnapshot(task);
  if (planSnapshot) return planSnapshot.tone || "";
  if (
    typeof planWorkflowCompletionIsUnproven === "function"
    && planWorkflowCompletionIsUnproven(task, planSnapshot)
  ) return "";
  if (task?.status === "writing_artifacts") {
    return task.active_job_kind === "report" ? "run" : "success";
  }
  return statusTone(task?.status);
}

function notebookReproducibilityComplete(task = selectedTask) {
  return (
    notebookReproducibilityCompleteStatuses.has(task?.status || "") ||
    taskFailedDuringMetrics(task) ||
    taskFailedDuringReport(task) ||
    (taskFailureWasRestartReclaim(task) && workflowStageCompleteFromEvidence("notebook"))
  );
}

function shouldShowReproducibilitySection() {
  return Boolean(workbenchTaskId() && notebookReproducibilityComplete(workbenchTask()));
}

function renderReproducibilitySectionVisibility() {
  // Driver tasks (data_join / feature / modeling) have no validation notebook
  // section — they run through the conversation + plan rail.
  if (taskUsesPlanRail(selectedTask)) {
    $("notebookSection")?.classList.add("hidden");
    return;
  }
  syncScoringSectionCopy(workbenchTask());
  $("notebookSection")?.classList.toggle("hidden", !shouldShowReproducibilitySection());
}

function metricOverviewComplete(task = selectedTask) {
  return (
    metricOverviewCompleteStatuses.has(task?.status || "") ||
    taskFailedDuringReport(task) ||
    (taskFailureWasRestartReclaim(task) && workflowStageCompleteFromEvidence("metrics"))
  );
}

function shouldShowMetricSection() {
  return Boolean(workbenchTaskId() && metricOverviewComplete(workbenchTask()));
}

function renderMetricSectionVisibility() {
  // Driver tasks render metrics inline in the conversation, not in the validation
  // metric section.
  if (taskUsesPlanRail(selectedTask)) {
    $("metricSection")?.classList.add("hidden");
    return;
  }
  $("metricSection")?.classList.toggle("hidden", !shouldShowMetricSection());
}

function workflowIndex(status, task = selectedTask) {
  if (!selectedTaskId && !task?.id) return -1;
  if (taskFailedDuringScan(task)) return 0;
  if (taskFailedDuringMetrics(task)) return 2;
  if (taskFailedDuringReport(task)) return 3;
  if (status === "succeeded" || status === "review_required") return 3;
  if (status === "writing_artifacts") return 3;
  if (status === "computing_metrics" || status === "executed") return 2;
  if (status === "running" || status === "failed" || status === "scanned" || status === "configured") return 1;
  return 0;
}

function taskFailureStepId(task = selectedTask) {
  return taskFailureStage(task);
}

function taskRunningStepId(status = selectedTask?.status, taskId = selectedTaskId) {
  const selectedBusyAction = taskBusyAction(taskId);
  if (selectedBusyAction === "scan") return "scan";
  if (selectedBusyAction === "notebook" || selectedBusyAction === "cancelNotebook") return "notebook";
  if (selectedBusyAction === "metrics" || selectedBusyAction === "cancelMetrics") return "metrics";
  if (selectedBusyAction === "report" || selectedBusyAction === "cancelReport") return "report";
  if (status === "running") return "notebook";
  if (status === "computing_metrics") return "metrics";
  return null;
}

function recommendedAction() {
  if (!selectedTaskId || selectedTaskIsBusy()) return null;
  const status = selectedTask?.status;
  if (status === "created" || taskFailedDuringScan(selectedTask)) return "scan";
  if (taskFailedDuringMetrics(selectedTask)) return "metrics";
  if (taskFailedDuringReport(selectedTask)) return "report";
  if (taskFailedDuringNotebook(selectedTask)) return "notebook";
  if (status === "scanned" || status === "configured") {
    return "notebook";
  }
  if (status === "executed") return "metrics";
  if (status === "writing_artifacts") return "report";
  return null;
}

function canRunStepAction(actionId) {
  if (!selectedTaskId) return false;
  const status = selectedTask?.status;
  if (actionId === "notebook" && status === "running") return true;
  switch (actionId) {
    case "scan":
      return ["created", "scanned", "failed", "executed", "writing_artifacts", "succeeded", "review_required"].includes(status);
    case "notebook":
      if (taskFailedDuringScan(selectedTask)) return false;
      return ["scanned", "configured", "executed", "writing_artifacts", "succeeded", "review_required"].includes(status) || taskFailedDuringNotebook(selectedTask);
    case "metrics":
      return status === "executed" || taskFailedDuringMetrics(selectedTask);
    case "report":
      return ["writing_artifacts", "review_required"].includes(status) || taskFailedDuringReport(selectedTask);
    default:
      return false;
  }
}

function setBusy(actionId, message = "", taskId = selectedTaskId) {
  if (taskId) {
    if (actionId) taskBusyActions.set(taskId, actionId);
    else taskBusyActions.delete(taskId);
  } else {
    globalBusyAction = actionId;
  }
  if (actionId && (!taskId || isWorkbenchTaskId(taskId))) {
    setActionStatus(message || "Processing...", "busy");
  }
  renderWorkflowStepper();
  renderPetState();
  updateAgentSendDisabled();
}

function setAgentMemoryStatus(message = "", kind = "") {
  agentMemoryPanel.setStatus(message, kind);
}

function setGovernanceExtensionStatus(message = "", kind = "") {
  const status = $("governanceExtensionStatus");
  if (!status) return;
  status.textContent = message;
  status.className = ["status", kind].filter(Boolean).join(" ");
}

function governanceExtensionActions() {
  const showExtensionError = (message) => {
    setGovernanceExtensionStatus(message || "Operation failed", "error");
  };
  return {
    pluginActions: {
      showError: showExtensionError,
      confirmRemove: (name) => showPlatformConfirm({
        title: "Remove Plugin",
        message: `Remove plugin ${name}? Its tools will no longer be available.`,
        confirmText: "Remove",
        cancelText: "Cancel",
        tone: "danger",
      }),
    },
    skillActions: {
      showError: showExtensionError,
    },
    capabilityActions: {
      showError: showExtensionError,
    },
  };
}

function mountGovernanceExtensions() {
  const root = $("governanceExtensionMount");
  return root ? mountGovernanceExtensionPanels(root, governanceExtensionActions()) : null;
}

async function refreshGovernancePlugins() {
  const mounted = mountGovernanceExtensions();
  if (!mounted) return;
  const actions = governanceExtensionActions();
  setGovernanceExtensionStatus("Reading plugins...");
  await renderPluginManager(mounted.panels.pluginPanel, actions.pluginActions);
  setGovernanceExtensionStatus("Plugin updated.", "success");
}

async function refreshGovernanceSkills() {
  const mounted = mountGovernanceExtensions();
  if (!mounted) return;
  const actions = governanceExtensionActions();
  setGovernanceExtensionStatus("Loading workflow templates...");
  await renderSkillManager(mounted.panels.skillPanel, actions.skillActions);
  setGovernanceExtensionStatus("Workflow Template updated.", "success");
}

async function refreshGovernanceCapability() {
  const mounted = mountGovernanceExtensions();
  if (!mounted) return;
  const actions = governanceExtensionActions();
  setGovernanceExtensionStatus("Loading autonomy profiles...");
  await renderTierSettings(mounted.panels.capabilityPanel, actions.capabilityActions);
  setGovernanceExtensionStatus("Autonomy profile updated.", "success");
}

function runGovernanceExtensionAction(action) {
  action().catch((error) => {
    setGovernanceExtensionStatus(error?.message || "Extension operation failed", "error");
  });
}

async function loadAgentMemoryItems() {
  return agentMemoryPanel.loadItems();
}

async function loadAgentMessageMemoryReferences(taskId, messageId) {
  if (!taskId || !messageId) return [];
  const payload = await api(`api/tasks/${encodeURIComponent(taskId)}/agent/messages/${encodeURIComponent(messageId)}/memory-references`);
  return Array.isArray(payload?.memory_references) ? payload.memory_references : [];
}

function handleAgentMemoryListClick(event) {
  agentMemoryPanel.handleListClick(event);
}

function handleAgentMemoryInlineInspect(event) {
  agentMemoryPanel.handleInlineInspect(event);
}

function setDraftToolsStatus(message = "", kind = "") {
  draftToolsPanel.setStatus(message, kind);
}

async function loadDraftTools({ preserveSelection = false } = {}) {
  return draftToolsPanel.load({ preserveSelection });
}

async function inspectDraftTool(draftId) {
  return draftToolsPanel.inspect(draftId);
}

async function runDraftTool() {
  return draftToolsPanel.run();
}

async function promoteDraftTool() {
  return draftToolsPanel.promote();
}

async function rejectDraftTool() {
  return draftToolsPanel.reject();
}

function handleDraftToolsListClick(event) {
  draftToolsPanel.handleListClick(event);
}

function handleDraftToolsListKeydown(event) {
  draftToolsPanel.handleListKeydown(event);
}

function requireTaskId(taskId, actionName = "Current Operation") {
  const normalizedTaskId = String(taskId || "").trim();
  if (!normalizedTaskId) {
    throw new Error(`${actionName}Missing task ID. Refresh the list and try again.`);
  }
  return normalizedTaskId;
}

function normalizeExecutionEnvironment(settings = {}) {
  return {
    ...defaultExecutionEnvironment,
    ...(settings || {}),
  };
}

function executionEnvironmentSettingsFromOption(option = {}) {
  return {
    execution_mode: option.execution_mode || "jupyter_kernel",
    kernel_name: option.kernel_name || "",
    conda_env_name: option.conda_env_name || "",
    python_executable: option.python_executable || "",
  };
}

function executionEnvironmentSettingsMatch(option = {}, settings = {}) {
  const normalized = normalizeExecutionEnvironment(settings);
  if ((option.execution_mode || "") !== normalized.execution_mode) return false;
  if ((option.kernel_name || "") !== (normalized.kernel_name || "")) return false;
  if (normalized.execution_mode === "conda_env") {
    return (option.conda_env_name || "") === (normalized.conda_env_name || "");
  }
  if (normalized.execution_mode === "python_executable") {
    return (option.python_executable || "") === (normalized.python_executable || "");
  }
  return true;
}

function executionEnvironmentSettingsLabel(settings = executionEnvironmentSettings, options = executionEnvironmentOptions) {
  const normalized = normalizeExecutionEnvironment(settings);
  const matchedOption = (options || []).find((option) => executionEnvironmentSettingsMatch(option, normalized));
  if (matchedOption?.label) return matchedOption.label;
  if (normalized.execution_mode === "conda_env") {
    return `Conda · ${normalized.conda_env_name || "No Selection"}`;
  }
  if (normalized.execution_mode === "python_executable") {
    return `Python · ${fileName(normalized.python_executable) || "No Selection"}`;
  }
  return `Jupyter Kernel · ${normalized.kernel_name || "python3"}`;
}

function renderExecutionEnvironmentSummary() {
  const label = executionEnvironmentSettingsLabel();
  const systemButton = $("openGovernanceSettingsButton");
  if (systemButton) systemButton.title = `Open system settings, current execution environment:${label}`;
}

function addExecutionEnvironmentRow(list, option, selected) {
  const settings = executionEnvironmentSettingsFromOption(option);
  const unavailable = option.available === false;
  const row = document.createElement("button");
  row.type = "button";
  row.className = "exec-env-row" + (selected ? " selected" : "");
  row.setAttribute("role", "radio");
  row.setAttribute("aria-checked", selected ? "true" : "false");
  row.tabIndex = -1; // roving tabindex; the active row is promoted after render
  row.disabled = unavailable;
  row.dataset.settings = JSON.stringify(settings);
  const title = String(option.label || option.id || "Unnamed Environment").replace(/^Current(?=Python|Jupyter|Conda)/, "Current · ");
  const subParts = [];
  if (option.note) subParts.push(option.note);
  if (unavailable) subParts.push("Not Available");
  const sub = subParts.join(" · ");
  row.innerHTML =
    '<span class="exec-env-check" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12.5l4.2 4.2L19 7"></path></svg></span>' +
    '<span class="exec-env-row-text">' +
    `<span class="exec-env-row-title">${escapeHtml(title)}</span>` +
    (sub ? `<span class="exec-env-row-sub">${escapeHtml(sub)}</span>` : "") +
    "</span>";
  list.appendChild(row);
}

function renderExecutionEnvironmentOptions(options = [], settings = {}) {
  executionEnvironmentOptions = Array.isArray(options) ? options : [];
  const list = $("executionEnvironmentList");
  if (!list) return;
  const normalized = normalizeExecutionEnvironment(settings);
  list.innerHTML = "";

  const rows = [];
  let selected = false;
  for (const option of executionEnvironmentOptions) {
    // Only the first match is marked selected, so at most one row is checked.
    const matches = !selected && executionEnvironmentSettingsMatch(option, normalized);
    rows.push({ option, selected: matches });
    selected = selected || matches;
  }

  if (!selected && (normalized.kernel_name || normalized.conda_env_name || normalized.python_executable)) {
    rows.push({
      option: {
        id: "saved-current",
        label: "Saved environment",
        ...normalized,
        note: "Not matched in this scan",
        available: true,
      },
      selected: true,
    });
    selected = true;
  }

  if (rows.length === 0) {
    const empty = document.createElement("div");
    empty.className = "exec-env-empty";
    empty.textContent = "No Python environments found.";
    list.appendChild(empty);
    return;
  }

  if (!selected) {
    const firstAvailable = rows.find((row) => row.option.available !== false);
    if (firstAvailable) firstAvailable.selected = true;
  }

  for (const row of rows) addExecutionEnvironmentRow(list, row.option, row.selected);

  // Promote one row to the group's tab stop (roving tabindex): the selected
  // row, else the first selectable row.
  const focusTarget =
    list.querySelector(".exec-env-row.selected:not(:disabled)") ||
    list.querySelector(".exec-env-row:not(:disabled)");
  if (focusTarget) focusTarget.tabIndex = 0;
}

function handleExecutionEnvironmentListKeydown(event) {
  if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
  const rows = [...$("executionEnvironmentList").querySelectorAll(".exec-env-row:not(:disabled)")];
  if (!rows.length) return;
  event.preventDefault();
  const current = event.target.closest(".exec-env-row");
  let idx = rows.indexOf(current);
  if (event.key === "Home") idx = 0;
  else if (event.key === "End") idx = rows.length - 1;
  else if (event.key === "ArrowDown") idx = idx < 0 ? 0 : (idx + 1) % rows.length;
  else idx = idx < 0 ? rows.length - 1 : (idx - 1 + rows.length) % rows.length;
  const next = rows[idx];
  for (const row of rows) row.tabIndex = row === next ? 0 : -1;
  next.focus();
}

function populateExecutionEnvironmentForm(settings = {}, options = executionEnvironmentOptions) {
  const normalized = normalizeExecutionEnvironment(settings);
  executionEnvironmentSettings = normalized;
  renderExecutionEnvironmentOptions(options, normalized);
  renderNotebookMemoryLimitInput(normalized);
  renderExecutionEnvironmentSummary();
}

function renderNotebookMemoryLimitInput(settings = executionEnvironmentSettings) {
  const input = $("notebookMemoryLimitInput");
  if (!input || document.activeElement === input) return; // don't clobber mid-edit
  const limit = settings?.notebook_memory_limit_mb;
  input.value = Number.isFinite(limit) && limit > 0 ? String(limit) : "";
}

function handleNotebookMemoryLimitChange() {
  const input = $("notebookMemoryLimitInput");
  if (!input) return;
  const raw = String(input.value || "").trim();
  let limit = null;
  if (raw !== "") {
    const parsed = Number(raw);
    limit = Number.isFinite(parsed) && parsed > 0 ? Math.round(parsed) : null;
  }
  // No-op if unchanged, so a plain focus/blur doesn't trigger a save round-trip.
  if ((executionEnvironmentSettings?.notebook_memory_limit_mb ?? null) === limit) {
    renderNotebookMemoryLimitInput();
    return;
  }
  saveExecutionEnvironmentSettings({ ...executionEnvironmentSettings, notebook_memory_limit_mb: limit });
}

function handleExecutionEnvironmentListClick(event) {
  const row = event.target.closest(".exec-env-row");
  if (!row || row.disabled) return;
  let settings;
  try {
    settings = { ...defaultExecutionEnvironment, ...JSON.parse(row.dataset.settings || "{}") };
  } catch (_) {
    setExecutionEnvironmentStatus("Could not read the environment configuration. Scan again and select an environment.", "error");
    return;
  }
  // Selecting a kernel must not wipe a configured notebook memory cap.
  settings.notebook_memory_limit_mb = executionEnvironmentSettings?.notebook_memory_limit_mb ?? null;
  // Optimistically move the checkmark; saveExecutionEnvironmentSettings reverts on failure.
  for (const item of $("executionEnvironmentList").querySelectorAll(".exec-env-row")) {
    const on = item === row;
    item.classList.toggle("selected", on);
    item.setAttribute("aria-checked", on ? "true" : "false");
  }
  saveExecutionEnvironmentSettings(settings);
}

function renderExecutionEnvironmentValidation(validation = {}) {
  if (!validation || Object.keys(validation).length === 0) return;
  const parts = [
    validation.message,
    validation.kernel_name ? `Kernel: ${validation.kernel_name}` : "",
    validation.python_version ? `Python: ${validation.python_version}` : "",
  ].filter(Boolean);
  setExecutionEnvironmentStatus(parts.join(" · ") || "Python environment saved.", validation.ok === false ? "error" : "success");
}

async function loadExecutionEnvironmentSettings({ silent = false } = {}) {
  try {
    const payload = await api("/api/settings/execution-environment/options");
    populateExecutionEnvironmentForm(payload.settings, payload.options || []);
    if (!silent) {
      renderExecutionEnvironmentValidation(payload.validation);
      if (!payload.validation) setExecutionEnvironmentStatus("Python environment loaded.", "success");
    }
  } catch (error) {
    populateExecutionEnvironmentForm(defaultExecutionEnvironment, []);
    if (!silent) setExecutionEnvironmentStatus(error.message || "Could not load the Python environment.", "error");
  }
}

async function refreshExecutionEnvironmentOptions() {
  setExecutionEnvironmentStatus("Scanning Python environments...");
  await loadExecutionEnvironmentSettings();
}

async function saveExecutionEnvironmentSettings(settings) {
  const list = $("executionEnvironmentList");
  try {
    setExecutionEnvironmentStatus("Validating and saving environment...");
    if (list) list.classList.add("is-saving");
    const payload = await api("/api/settings/execution-environment", {
      method: "PUT",
      body: JSON.stringify({ ...defaultExecutionEnvironment, ...(settings || {}) }),
    });
    populateExecutionEnvironmentForm(payload.settings, executionEnvironmentOptions);
    renderExecutionEnvironmentValidation(payload.validation);
    if (!payload.validation) setExecutionEnvironmentStatus("Python environment saved.", "success");
  } catch (error) {
    // Revert the optimistic checkmark to the last known-good selection.
    populateExecutionEnvironmentForm(executionEnvironmentSettings, executionEnvironmentOptions);
    setExecutionEnvironmentStatus(error.message || "Could not save the Python environment.", "error");
  } finally {
    if (list) list.classList.remove("is-saving");
  }
}

function setLLMSettingsStatus(message, kind = "info") {
  const status = $("llmSettingsStatus");
  if (!status) return;
  status.textContent = message;
  status.className = `status ${kind}`.trim();
}

function setLLMEngineEditStatus(message, kind = "info") {
  const status = $("llmEngineEditStatus");
  if (!status) return;
  status.textContent = message;
  status.className = `status ${kind}`.trim();
}

// GAP-8: LLM configuration preflight -- lets the user confirm base_url/model
// name/api_key actually connect before saving, instead of only discovering a
// typo once the agent silently degrades mid-conversation.
function setLLMEngineTestResult(message, kind = "info") {
  const status = $("llmEngineTestResult");
  if (!status) return;
  status.textContent = message;
  status.className = `status ${kind}`.trim();
}

async function testLLMEngineConnection() {
  const editing = llmEditingIndex !== null ? (llmSettings.models[llmEditingIndex] || {}) : null;
  const apiKey = $("llmEngineApiKey").value.trim();
  const payload = {
    api_base_url: $("llmEngineBaseUrl").value.trim(),
    model_name: $("llmEngineModelName").value.trim(),
    api_key: apiKey,
  };
  if (!payload.api_base_url || !payload.model_name) {
    return setLLMEngineTestResult("Enter the API base URL and model name.", "error");
  }
  if (!apiKey && editing && editing.has_api_key && editing.model_id) {
    // Key left blank on an edit -- test the already-saved model_id so the
    // stored (masked) api_key is used instead of an empty string.
    payload.model_id = editing.model_id;
  } else if (!apiKey) {
    return setLLMEngineTestResult("Enter the API key.", "error");
  }
  setLLMEngineTestResult("Testing connection...");
  try {
    const result = await api("/api/settings/llm/test", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (result.ok) {
      setLLMEngineTestResult(
        `Connected in ${result.latency_ms} ms. Model: ${result.model_echo || "-"}.`,
        "success",
      );
    } else {
      setLLMEngineTestResult(result.error_detail || "Connection failed.", "error");
    }
  } catch (error) {
    setLLMEngineTestResult(error.message || "Connection test failed.", "error");
  }
}

function normalizeLLMSettings(payload = {}) {
  return {
    default_model_id: payload.default_model_id || "",
    models: Array.isArray(payload.models) ? payload.models : [],
    enabled_models: Array.isArray(payload.enabled_models) ? payload.enabled_models : [],
  };
}

function normalizeAgentEffort(value) {
  return ["low", "medium", "high"].includes(value) ? value : "high";
}

function normalizeAgentAcceptanceMode(value) {
  return value === "auto_accept" ? "auto_accept" : "normal";
}

function restoreAgentComposerPreferences() {
  try {
    const stored = JSON.parse(localStorage.getItem(agentComposerPreferenceStorageKey) || "{}");
    return {
      model_id: typeof stored.model_id === "string" ? stored.model_id : "",
      effort: normalizeAgentEffort(stored.effort),
      acceptance_mode: normalizeAgentAcceptanceMode(stored.acceptance_mode),
    };
  } catch (_) {
    return { model_id: "", effort: "high", acceptance_mode: "normal" };
  }
}

function saveAgentComposerPreferences() {
  localStorage.setItem(agentComposerPreferenceStorageKey, JSON.stringify({
    model_id: agentSelectedModelId || "",
    effort: normalizeAgentEffort(agentSelectedEffort),
    acceptance_mode: normalizeAgentAcceptanceMode(agentAcceptanceMode),
  }));
}

function loadAgentTaskComposerOverrides() {
  try {
    const stored = JSON.parse(localStorage.getItem(agentTaskComposerStorageKey) || "{}");
    if (stored && typeof stored === "object" && !Array.isArray(stored)) return stored;
  } catch (_) {
    /* fall through */
  }
  return {};
}

let agentTaskComposerOverrides = loadAgentTaskComposerOverrides();

function persistAgentTaskComposerOverrides() {
  try {
    localStorage.setItem(
      agentTaskComposerStorageKey,
      JSON.stringify(agentTaskComposerOverrides),
    );
  } catch (_) {
    /* swallow quota errors */
  }
}

function getAgentTaskComposerOverride(taskId) {
  if (!taskId) return null;
  const entry = agentTaskComposerOverrides[taskId];
  if (!entry || typeof entry !== "object") return null;
  const result = {};
  if (typeof entry.model_id === "string") result.model_id = entry.model_id;
  if (entry.effort) result.effort = normalizeAgentEffort(entry.effort);
  if (entry.acceptance_mode) {
    result.acceptance_mode = normalizeAgentAcceptanceMode(entry.acceptance_mode);
  }
  return result;
}

function updateAgentTaskComposerOverride(taskId, patch) {
  if (!taskId || !patch) return;
  // Re-read from localStorage so a sibling tab's overrides for OTHER tasks
  // are not silently clobbered. We still own the entry for `taskId`.
  const latest = loadAgentTaskComposerOverrides();
  const current = latest[taskId] || {};
  agentTaskComposerOverrides = { ...latest, [taskId]: { ...current, ...patch } };
  persistAgentTaskComposerOverrides();
}

function applyAgentTaskComposerPreferences(taskId) {
  // Called whenever a task becomes the selected one. Falls back to the
  // global seed preferences when no override exists so the composer always
  // shows a coherent state.
  const fallback = {
    model_id: agentComposerPreferences.model_id || "",
    effort: normalizeAgentEffort(agentComposerPreferences.effort),
    acceptance_mode: normalizeAgentAcceptanceMode(agentComposerPreferences.acceptance_mode),
  };
  const override = getAgentTaskComposerOverride(taskId) || {};
  agentSelectedModelId = override.model_id !== undefined
    ? override.model_id
    : fallback.model_id;
  agentSelectedEffort = override.effort !== undefined
    ? override.effort
    : fallback.effort;
  agentAcceptanceMode = override.acceptance_mode !== undefined
    ? override.acceptance_mode
    : fallback.acceptance_mode;
  const task = selectedTaskId === taskId && selectedTask
    ? selectedTask
    : findTaskInCache(taskId);
  if (override.acceptance_mode === undefined && usesAgentValidationWorkbench(task)) {
    agentAcceptanceMode = "auto_accept";
  }
}

function resetAgentComposerToGlobalDefaults() {
  agentSelectedModelId = agentComposerPreferences.model_id || "";
  agentSelectedEffort = normalizeAgentEffort(agentComposerPreferences.effort);
  agentAcceptanceMode = normalizeAgentAcceptanceMode(agentComposerPreferences.acceptance_mode);
}

function renderLLMSettingsSummary() {
  const models = llmSettings.models || [];
  const systemButton = $("openGovernanceSettingsButton");
  if (models.length === 0) {
    if (systemButton) systemButton.dataset.llmSummary = "Not configured";
    return;
  }
  const primary = models.find((model) => model.model_id === llmSettings.default_model_id) || models[0];
  const name = llmModelDisplayName(primary);
  if (systemButton) {
    systemButton.dataset.llmSummary = models.length > 1 ? `${name} · ${models.length} models` : name;
  }
}

function llmModelDisplayName(model = {}) {
  return model.display_name || model.model_name || model.model_id || "Unnamed Model";
}

function renderLLMModelProfiles() {
  const list = $("llmModelProfiles");
  if (!list) return;
  const models = llmSettings.models || [];
  if (models.length === 0) {
    list.innerHTML = '<div class="llm-engine-empty">No AI models configured. Select Add Model to configure one.</div>';
    return;
  }
  list.innerHTML = models.map((model, index) => {
    const name = llmModelDisplayName(model);
    const meta = [model.model_name, model.api_base_url].filter(Boolean).join(" · ") || "Model name and endpoint not provided";
    return [
      `<div class="llm-engine-item" data-llm-edit="${index}" role="button" tabindex="0">`,
      '<div class="llm-engine-item-info">',
      `<div class="llm-engine-item-name">${escapeHtml(name)}</div>`,
      `<div class="llm-engine-item-url">${escapeHtml(meta)}</div>`,
      "</div>",
      `<button class="engine-del-btn" type="button" data-llm-remove="${index}" title="Remove Model" aria-label="Remove Model">×</button>`,
      "</div>",
    ].join("");
  }).join("");
}

function collectLLMSettings() {
  const models = (llmSettings.models || []).map((model) => {
    const payload = {
      model_id: model.model_id || "",
      display_name: (model.display_name || "").trim(),
      provider: model.provider || "OpenAI Compatible",
      model_name: (model.model_name || "").trim(),
      api_base_url: (model.api_base_url || "").trim(),
      enabled: model.enabled !== false,
      enable_thinking: Boolean(model.enable_thinking),
      timeout_seconds: Number(model.timeout_seconds || 60),
    };
    if (typeof model.api_key === "string" && model.api_key.trim()) {
      payload.api_key = model.api_key.trim();
    } else if (model.has_api_key) {
      payload.has_api_key = true;
    }
    return payload;
  });
  // default_model_id is left for the server to derive — model selection happens
  // in the composer, not here.
  return { default_model_id: "", models };
}

async function loadLLMSettings({ silent = false } = {}) {
  try {
    const payload = await api("/api/settings/llm");
    llmSettings = normalizeLLMSettings(payload);
    renderLLMModelProfiles();
    renderLLMSettingsSummary();
    renderAgentModelOptions();
    if (!silent) setLLMSettingsStatus("");
  } catch (error) {
    llmSettings = normalizeLLMSettings();
    renderLLMModelProfiles();
    renderLLMSettingsSummary();
    renderAgentModelOptions();
    if (!silent) setLLMSettingsStatus(error.message || "Could not load AI model settings.", "error");
  }
}

// Persists the current in-memory engine list. Throws on failure so callers can
// roll back; status reporting is left to the caller's dialog.
async function saveLLMSettings() {
  const payload = await api("/api/settings/llm", {
    method: "PUT",
    body: JSON.stringify(collectLLMSettings()),
  });
  llmSettings = normalizeLLMSettings(payload);
  renderLLMModelProfiles();
  renderLLMSettingsSummary();
  renderAgentModelOptions();
}

function setMemoryPolicyStatus(message, kind = "info") {
  const status = $("memoryPolicyStatus");
  if (!status) return;
  status.textContent = message || "";
  status.className = `status ${kind}`;
}

function applyMemoryPolicy(settings = {}) {
  for (const input of document.querySelectorAll(".memory-policy-switch")) {
    const key = input.dataset.memoryPolicy;
    if (key && key in settings) input.checked = Boolean(settings[key]);
  }
}

function collectMemoryPolicy() {
  const out = {};
  for (const input of document.querySelectorAll(".memory-policy-switch")) {
    if (input.dataset.memoryPolicy) out[input.dataset.memoryPolicy] = Boolean(input.checked);
  }
  return out;
}

async function loadMemoryPolicySettings({ silent = false } = {}) {
  try {
    const payload = await api("/api/settings/memory-policy");
    applyMemoryPolicy(payload.settings || {});
    if (!silent) setMemoryPolicyStatus("");
  } catch (error) {
    if (!silent) setMemoryPolicyStatus(error.message || "Could not load memory settings.", "error");
  }
}

async function saveMemoryPolicySettings() {
  try {
    setMemoryPolicyStatus("Saving Memory Policy...");
    const payload = await api("/api/settings/memory-policy", {
      method: "PUT",
      body: JSON.stringify(collectMemoryPolicy()),
    });
    applyMemoryPolicy(payload.settings || {});
    setMemoryPolicyStatus("Memory policy saved.", "success");
  } catch (error) {
    setMemoryPolicyStatus(error.message || "Could not save memory settings.", "error");
    loadMemoryPolicySettings({ silent: true });
  }
}

function handleMemoryPolicyChange(event) {
  if (event.target.closest(".memory-policy-switch")) saveMemoryPolicySettings();
}

function addLLMModelProfile() {
  openLLMEngineEdit(null);
}

async function removeLLMModelProfile(index) {
  const previous = llmSettings.models || [];
  llmSettings = { ...llmSettings, models: previous.filter((_, i) => i !== index) };
  renderLLMModelProfiles();
  try {
    await saveLLMSettings();
    setLLMSettingsStatus("Model deleted.", "success");
  } catch (error) {
    llmSettings = { ...llmSettings, models: previous };
    renderLLMModelProfiles();
    setLLMSettingsStatus(error.message || "Could not remove the model.", "error");
  }
}

function openLLMEngineEdit(index) {
  llmEditingIndex = index;
  const model = index === null ? {} : (llmSettings.models[index] || {});
  $("llmEngineEditTitle").textContent = index === null ? "Add Model" : "Edit Model";
  $("llmEngineDisplayName").value = model.display_name || "";
  $("llmEngineModelName").value = model.model_name || "";
  $("llmEngineBaseUrl").value = model.api_base_url || "";
  $("llmEngineEnableThinking").checked = Boolean(model.enable_thinking);
  const keyInput = $("llmEngineApiKey");
  keyInput.value = "";
  keyInput.placeholder = model.has_api_key ? "Leave blank to keep the saved key" : "sk-...";
  setLLMEngineEditStatus("");
  setLLMEngineTestResult("");
  $("llmEngineEditDialog").showModal();
  $("llmEngineDisplayName").focus();
}

function closeLLMEngineEdit() {
  $("llmEngineEditDialog").close();
  llmEditingIndex = null;
}

async function saveLLMEngineEdit() {
  const displayName = $("llmEngineDisplayName").value.trim();
  const modelName = $("llmEngineModelName").value.trim();
  const baseUrl = $("llmEngineBaseUrl").value.trim();
  const apiKey = $("llmEngineApiKey").value.trim();
  const editing = llmEditingIndex !== null ? (llmSettings.models[llmEditingIndex] || {}) : null;
  if (!modelName) return setLLMEngineEditStatus("Enter the model name.", "error");
  if (!baseUrl) return setLLMEngineEditStatus("Enter the API base URL.", "error");
  if (!apiKey && !(editing && editing.has_api_key)) {
    return setLLMEngineEditStatus("Enter the API key.", "error");
  }

  const model = editing
    ? { ...editing }
    : { model_id: "", provider: "OpenAI Compatible", timeout_seconds: 60, enabled: true, has_api_key: false };
  model.display_name = displayName;
  model.model_name = modelName;
  model.api_base_url = baseUrl;
  model.enable_thinking = $("llmEngineEnableThinking").checked;
  if (apiKey) {
    model.api_key = apiKey;
    model.has_api_key = true;
  }

  const previous = llmSettings.models || [];
  const models = editing
    ? previous.map((item, i) => (i === llmEditingIndex ? model : item))
    : [...previous, model];
  llmSettings = { ...llmSettings, models };

  try {
    setLLMEngineEditStatus("Saving...");
    await saveLLMSettings();
    closeLLMEngineEdit();
    setLLMSettingsStatus("Model saved.", "success");
  } catch (error) {
    llmSettings = { ...llmSettings, models: previous };
    renderLLMModelProfiles();
    setLLMEngineEditStatus(error.message || "Save failed.", "error");
  }
}

function rememberSelectedTaskId(taskId) {
  rememberStoredSelectedTaskId(selectedTaskStorageKey, taskId);
  if (!taskId) {
    syncTaskDeepLink(window.history, window.location, { taskId: "", itemId: "" });
    return;
  }
  const currentLink = parseTaskDeepLink(window.location.search);
  const itemId = (
    (taskId === selectedTaskId && projectedValidationChildTaskId)
    || (currentLink.taskId === taskId ? currentLink.itemId : "")
    || (taskId === initialTaskDeepLink.taskId ? initialTaskDeepLink.itemId : "")
    || ""
  );
  syncTaskDeepLink(window.history, window.location, { taskId, itemId });
}

function storedSelectedTaskId() {
  return readStoredSelectedTaskId(selectedTaskStorageKey);
}

function loadResultScrollPositions() {
  loadStoredResultScrollPositions(resultScrollPositionsStorageKey, resultScrollPositionsByTask);
}

function persistResultScrollPositions() {
  persistStoredResultScrollPositions(resultScrollPositionsStorageKey, resultScrollPositionsByTask);
}

function scheduleResultScrollPositionsPersist() {
  if (resultScrollPersistFrame !== null) return;
  resultScrollPersistFrame = window.requestAnimationFrame(() => {
    resultScrollPersistFrame = null;
    persistResultScrollPositions();
  });
}

function restoreSelectedTaskPlaceholder() {
  if (selectedTaskId) return;
  const storedTaskId = storedSelectedTaskId();
  if (!storedTaskId) return;
  selectedTaskId = storedTaskId;
  selectedTask = null;
}

function syncSelectedTaskFromCache() {
  if (!selectedTaskId) {
    const storedTaskId = storedSelectedTaskId();
    if (storedTaskId) {
      const restored = taskCache.find((task) => task.id === storedTaskId);
      if (restored) {
        selectedTaskId = restored.id;
        selectedTask = restored;
        applyAgentTaskComposerPreferences(restored.id);
        prepareResultScrollRestoreForTask(restored.id);
        return;
      }
      rememberSelectedTaskId(null);
    }
    selectedTask = null;
    return;
  }
  const current = taskCache.find((task) => task.id === selectedTaskId);
  if (current) {
    const wasPlaceholder = !selectedTask;
    selectedTask = current;
    rememberSelectedTaskId(current.id);
    if (wasPlaceholder) {
      applyAgentTaskComposerPreferences(current.id);
      prepareResultScrollRestoreForTask(current.id);
    }
    return;
  }
  selectedTaskId = null;
  selectedTask = null;
  rememberSelectedTaskId(null);
}

function findTaskInCache(taskId) {
  return taskCache.find((task) => task.id === taskId) || null;
}

function ensureActiveTaskProgressPolling(task = selectedTask) {
  if (usesAgentValidationWorkbench(task)) {
    const childId = projectedValidationChildTaskId;
    const child = projectedValidationChildTask;
    if (!childId || !taskServerBusyAction(child)) return;
    if (progressPolls.has(childId)) return;
    pollValidationProgress(terminalTaskStatuses, childId, { background: true }).catch(() => null);
    return;
  }
  if (isValidationBatchTask(task)) return;
  const taskId = task?.id || selectedTaskId;
  if (!taskId || !taskServerBusyAction(task)) return;
  if (progressPolls.has(taskId)) return;
  pollValidationProgress(terminalTaskStatuses, taskId, { background: true }).catch(() => null);
}

function runModeLabel(mode) {
  return mode === "agent" ? "Agent Mode" : "Manual Mode";
}

function selectedTaskIsAgentMode(task = selectedTask) {
  return task?.run_mode === "agent";
}

function selectedTaskIsValidationBatch(task = selectedTask) {
  return isValidationBatchTask(task);
}

function workbenchTask() {
  if (usesAgentValidationWorkbench(selectedTask) && projectedValidationChildTask) {
    return projectedValidationChildTask;
  }
  return selectedTask;
}

function workbenchTaskId() {
  if (usesAgentValidationWorkbench(selectedTask) && projectedValidationChildTaskId) {
    return projectedValidationChildTaskId;
  }
  return selectedTaskId;
}

function isWorkbenchTaskId(taskId) {
  const id = String(taskId || "");
  return Boolean(id) && (id === selectedTaskId || id === projectedValidationChildTaskId);
}

function isCurrentProjectedChildLoad(loadVersion, childChanged) {
  return !childChanged || loadVersion === projectedChildContentLoadVersion;
}

async function applyProjectedValidationChild(childTaskId, { force = false } = {}) {
  const normalizedChildId = String(childTaskId || "").trim();
  if (!normalizedChildId || !usesAgentValidationWorkbench(selectedTask)) return false;
  if (
    !force
    && projectedValidationChildTaskId === normalizedChildId
    && projectedValidationChildTask
  ) {
    return true;
  }
  const childChanged = projectedValidationChildTaskId !== normalizedChildId;
  if (childChanged) rememberValidationView();
  const loadVersion = childChanged
    ? ++projectedChildContentLoadVersion
    : projectedChildContentLoadVersion;
  if (childChanged) {
    resetAgentTypingState();
    beginTaskContentLoad(normalizedChildId);
    suppressAgentAutoScrollTaskId = selectedTaskId;
    const scrollContent = $("resultScrollContent");
    if (scrollContent) scrollContent.scrollTop = 0;
  }
  projectedValidationChildTaskId = normalizedChildId;
  try {
    try {
      projectedValidationChildTask = await api(`api/tasks/${encodeURIComponent(normalizedChildId)}`);
    } catch (_error) {
      projectedValidationChildTask = {
        id: normalizedChildId,
        task_type: "validation",
        run_mode: "agent",
        validation_workflow_version: 2,
      };
    }
    if (!isWorkbenchTaskId(normalizedChildId)) return false;
    if (!isCurrentProjectedChildLoad(loadVersion, childChanged)) return false;
    rememberSelectedTaskId(selectedTaskId);
    await loadTaskEvidence(normalizedChildId);
    if (!isCurrentProjectedChildLoad(loadVersion, childChanged)) return false;
    await loadAgentMessages(normalizedChildId);
    if (!isCurrentProjectedChildLoad(loadVersion, childChanged)) return false;
    await loadReportFields(normalizedChildId);
    if (!isCurrentProjectedChildLoad(loadVersion, childChanged)) return false;
    renderAll();
    if (childChanged) {
      await nextAnimationFrame();
      await nextAnimationFrame();
      selectValidationView(activeValidationView, { remember: false });
    }
    return true;
  } finally {
    if (childChanged && loadVersion === projectedChildContentLoadVersion) {
      if (suppressAgentAutoScrollTaskId === selectedTaskId) {
        suppressAgentAutoScrollTaskId = null;
      }
      finishTaskContentLoad(normalizedChildId);
    }
  }
}

function selectedTaskIsRiskAnalysisAgent(task = selectedTask) {
  return task?.run_mode === "agent" && task?.task_type === "vintage";
}

function latestRiskAnalysisIntakePhase(messages = agentMessages) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const intake = messages[index]?.metadata?.risk_analysis_intake;
    if (intake && typeof intake === "object") return String(intake.phase || "");
  }
  return "";
}

function selectedTaskNeedsManualRiskIntake(
  task = selectedTask,
  messages = agentMessages,
) {
  if (task?.run_mode !== "manual" || task?.task_type !== "vintage") return false;
  return latestRiskAnalysisIntakePhase(messages) !== "ready";
}

function selectedTaskNeedsDeterministicPortfolioTurn(
  task = selectedTask,
  messages = agentMessages,
) {
  if (task?.task_type !== "portfolio") return false;
  return portfolioTurnUsesDeterministicRoute(task, messages);
}

function syncRiskMaterialUploadControl() {
  const button = $("riskMaterialUploadButton");
  if (!button) return;
  const visible = selectedTaskIsRiskAnalysisAgent()
    || selectedTaskNeedsManualRiskIntake();
  button.classList.toggle("hidden", !visible);
  button.disabled = !visible || taskBusyAction(selectedTaskId) === "agent";
}

function updateWorkspaceGreeting(now = new Date()) {
  updateWorkspaceGreetingView({ now, getElementById: $ });
}

function setTaskHeroGlassActive(hero, workspace, glassActive) {
  if (taskHeroGlassActive === glassActive) return;
  taskHeroGlassActive = glassActive;
  hero.classList.toggle("is-glass-active", glassActive);
  workspace.classList.toggle("is-glass-active", glassActive);
}

function updateTaskHeroGlassState({ measureScroll = false } = {}) {
  const scrollContent = $("resultScrollContent");
  const hero = $("taskHero");
  const workspace = $("resultWorkspace");
  if (!scrollContent || !hero || !workspace) return;
  if (measureScroll) {
    taskHeroCanScroll = scrollContent.scrollHeight > scrollContent.clientHeight + 1;
  }
  const glassActive = taskHeroCanScroll && scrollContent.scrollTop > 6;
  setTaskHeroGlassActive(hero, workspace, glassActive);
}

function beginTaskContentLoad(taskId) {
  if (taskContentSettleTimer !== null) {
    window.clearTimeout(taskContentSettleTimer);
    taskContentSettleTimer = null;
  }
  pendingTaskContentLoadTaskId = taskId || null;
  const workspace = $("validationWorkspace");
  workspace?.classList.remove("is-task-content-settling");
  workspace?.classList.toggle("is-task-content-loading", Boolean(taskId));
  $("validationWorkspaceNav")?.querySelectorAll("button").forEach((button) => { button.disabled = Boolean(taskId); });
}

function finishTaskContentLoad(taskId = pendingTaskContentLoadTaskId) {
  if (taskId && pendingTaskContentLoadTaskId !== taskId) return;
  pendingTaskContentLoadTaskId = null;
  $("validationWorkspaceNav")?.querySelectorAll("button").forEach((button) => { button.disabled = false; });
  const workspace = $("validationWorkspace");
  if (!workspace) return;
  workspace.classList.remove("is-task-content-loading");
  if (!taskId) {
    workspace.classList.remove("is-task-content-settling");
    return;
  }
  workspace.classList.add("is-task-content-settling");
  taskContentSettleTimer = window.setTimeout(() => {
    taskContentSettleTimer = null;
    workspace.classList.remove("is-task-content-settling");
  }, 220);
}

function clearTaskContentLoad() {
  if (taskContentSettleTimer !== null) {
    window.clearTimeout(taskContentSettleTimer);
    taskContentSettleTimer = null;
  }
  pendingTaskContentLoadTaskId = null;
  $("validationWorkspaceNav")?.querySelectorAll("button").forEach((button) => { button.disabled = false; });
  const workspace = $("validationWorkspace");
  workspace?.classList.remove("is-task-content-loading");
  workspace?.classList.remove("is-task-content-settling");
}

function rememberResultScrollPosition(taskId = selectedTaskId) {
  const scrollContent = $("resultScrollContent");
  if (!scrollContent || !taskId) return;
  resultScrollPositionsByTask.set(taskId, scrollContent.scrollTop);
  scheduleResultScrollPositionsPersist();
}

function cancelResultScrollRestoreFrame() {
  if (resultScrollRestoreFrame === null) return;
  window.cancelAnimationFrame(resultScrollRestoreFrame);
  resultScrollRestoreFrame = null;
}

function prepareResultScrollRestoreForTask(taskId) {
  if (!taskId) return;
  pendingResultScrollRestoreTaskId = taskId;
  suppressAgentAutoScrollTaskId = taskId;
  // Reset on every task switch so a stale `false` from the previous task
  // does not stop the next task's typewriter from auto-following.
  agentAutoScrollFollows = true;
  if (agentAutoScrollFrame !== null) {
    window.cancelAnimationFrame(agentAutoScrollFrame);
    agentAutoScrollFrame = null;
  }
}

function applyResultScrollPosition(taskId = selectedTaskId) {
  const scrollContent = $("resultScrollContent");
  if (!scrollContent || !taskId) return;
  const savedTop = resultScrollPositionsByTask.get(taskId) || 0;
  const maxTop = Math.max(0, scrollContent.scrollHeight - scrollContent.clientHeight);
  scrollContent.scrollTop = Math.min(savedTop, maxTop);
  updateTaskHeroGlassState({ measureScroll: true });
}

function syncAgentAutoScrollFollowFromCurrentPosition(taskId = selectedTaskId) {
  if (taskId !== selectedTaskId || !selectedTaskIsAgentMode()) return;
  const scrollContent = $("resultScrollContent");
  if (!scrollContent) return;
  if (scrollContent.scrollHeight <= scrollContent.clientHeight) {
    agentAutoScrollFollows = true;
    return;
  }
  const distance = scrollContent.scrollHeight - scrollContent.scrollTop - scrollContent.clientHeight;
  agentAutoScrollFollows = distance <= AGENT_AUTO_SCROLL_BOTTOM_TOLERANCE_PX;
}

function nextAnimationFrame() {
  return new Promise((resolve) => window.requestAnimationFrame(resolve));
}

async function restoreResultScrollPositionAfterRender(taskId = selectedTaskId) {
  if (!taskId) return;
  cancelResultScrollRestoreFrame();
  await nextAnimationFrame();
  await nextAnimationFrame();
  if (selectedTaskId !== taskId) {
    if (suppressAgentAutoScrollTaskId === taskId) suppressAgentAutoScrollTaskId = null;
    return;
  }
  applyResultScrollPosition(taskId);
  if (pendingResultScrollRestoreTaskId === taskId) pendingResultScrollRestoreTaskId = null;
  if (suppressAgentAutoScrollTaskId === taskId) suppressAgentAutoScrollTaskId = null;
  syncAgentAutoScrollFollowFromCurrentPosition(taskId);
}

function scheduleTaskHeroGlassState() {
  if (taskHeroGlassFrame !== null) return;
  taskHeroGlassFrame = requestAnimationFrame(() => {
    taskHeroGlassFrame = null;
    updateTaskHeroGlassState();
  });
}

function handleResultScroll() {
  if (pendingResultScrollRestoreTaskId !== selectedTaskId) {
    rememberResultScrollPosition();
  }
  scheduleTaskHeroGlassState();
  recomputeAgentAutoScrollFollow();
}

function recomputeAgentAutoScrollFollow() {
  if (!selectedTaskIsAgentMode()) return;
  const scrollContent = $("resultScrollContent");
  if (!scrollContent) return;
  // Programmatic scrolls reach this handler without a preceding wheel/touch
  // event. Treat them as no-ops so the typewriter's own snap-to-bottom cannot
  // re-enable follow-mode the user just disengaged a few milliseconds ago.
  if (performance.now() - lastUserScrollInputAt > AGENT_USER_SCROLL_INPUT_WINDOW_MS) return;
  if (scrollContent.scrollHeight <= scrollContent.clientHeight) return;
  const distance =
    scrollContent.scrollHeight - scrollContent.scrollTop - scrollContent.clientHeight;
  if (distance < 0) return;
  agentAutoScrollFollows = distance <= AGENT_AUTO_SCROLL_BOTTOM_TOLERANCE_PX;
}

function noteAgentUserScrollInput() {
  lastUserScrollInputAt = performance.now();
}

function routeWorkspaceWheelToResult(event) {
  const scrollContent = $("resultScrollContent");
  const appShell = $("appShell");
  const target = event.target instanceof Element ? event.target : null;
  if (!scrollContent || !appShell || !target) return;
  if (event.defaultPrevented || event.ctrlKey) return;
  if (!appShell.contains(target)) return;
  if (scrollTargetIsWithin(target, "#taskSidebar, #progressRail, #workflowStepper")) return;
  if (scrollTargetIsWithin(target, "#resultScrollContent")) return;
  if (scrollTargetIsWithin(target, "dialog, textarea, select, input, .metric-table-scroll")) return;

  const previousTop = scrollContent.scrollTop;
  const previousLeft = scrollContent.scrollLeft;
  scrollContent.scrollTop += event.deltaY;
  scrollContent.scrollLeft += event.deltaX;
  if (scrollContent.scrollTop !== previousTop || scrollContent.scrollLeft !== previousLeft) {
    event.preventDefault();
  }
}

function scrollTargetIsWithin(target, selector) {
  return target instanceof Element && Boolean(target.closest(selector));
}

function syncTaskHeroGlassLayout() {
  const workspace = $("resultWorkspace");
  const head = document.querySelector("#resultWorkspace .workspace-head");
  if (!workspace || !head) return;
  const headHeight = head.getBoundingClientRect().height;
  if (Number.isFinite(headHeight) && headHeight > 0) {
    workspace.style.setProperty("--workspace-head-space", `${Math.ceil(headHeight)}px`);
  }
  syncAgentComposerClearance();
  updateTaskHeroGlassState({ measureScroll: true });
}

function setTaskHeroCollapsed(collapsed) {
  const hero = $("taskHero");
  if (!hero) return;
  hero.classList.toggle("is-collapsed", collapsed);
  const details = $("taskHeroDetails");
  if (details) {
    details.setAttribute("aria-hidden", collapsed ? "true" : "false");
    details.toggleAttribute("inert", collapsed);
  }
  const toggle = $("taskHeroToggle");
  if (toggle) {
    const label = collapsed ? "Expand Task Details" : "Collapse task details";
    toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
    toggle.setAttribute("aria-label", label);
    toggle.setAttribute("title", label);
  }
  // The head shrank/grew, so scroll padding, composer clearance and the
  // scroll-driven glass tint all need a recompute once layout settles.
  requestAnimationFrame(syncTaskHeroGlassLayout);
}

function handleTaskHeroToggle(event) {
  // Interactive descendants (path-copy button, form controls) keep their own
  // behaviour instead of folding the card.
  if (event.target.closest("a[href], button:not(#taskHeroToggle), [data-copy], input, select, textarea, .task-hero-batch-switcher")) {
    return;
  }
  // Don't fold when the user is finishing a text selection inside the card.
  const selection = typeof window.getSelection === "function" ? window.getSelection() : null;
  const hero = $("taskHero");
  if (!hero) return;
  if (selection && !selection.isCollapsed && selection.anchorNode && hero.contains(selection.anchorNode)) {
    return;
  }
  setTaskHeroCollapsed(!hero.classList.contains("is-collapsed"));
}

function syncAgentComposerClearance() {
  const workspace = $("resultWorkspace");
  const composer = $("agentComposer");
  if (!workspace || !composer || composer.classList.contains("hidden")) return;
  const composerHeight = composer.getBoundingClientRect().height;
  const composerGap = parseFloat(getComputedStyle(workspace).getPropertyValue("--agent-composer-gap")) || 28;
  if (!Number.isFinite(composerHeight) || composerHeight <= 0) return;
  workspace.style.setProperty("--agent-composer-clearance", `${Math.ceil(composerHeight + composerGap)}px`);
}

function setWorkspaceActionStatus(message, kind = "info", detail = undefined) {
  const snapshot = taskActionStatusSnapshot(selectedTask);
  const persistentDetail = detail === undefined && snapshot.message === message
    ? snapshot.detail || ""
    : detail || "";
  setActionStatus(message, kind, persistentDetail);
}

function renderCurrentTask({ force = false } = {}) {
  const nextSignature = currentTaskSignature(selectedTask);
  if (!force && renderSignatures.currentTask === nextSignature) return;
  renderSignatures.currentTask = nextSignature;

  renderCurrentTaskWorkspace({
    selectedTask,
    selectedTaskId,
    getElementById: $,
    taskDisplayName,
    renderTaskSnapshot,
    setActionStatus: setWorkspaceActionStatus,
    updateGreeting: updateWorkspaceGreetingView,
    statusOverride: actionStatusOverride?.taskId === selectedTaskId ? actionStatusOverride : null,
    setTaskFailureActionStatus,
    taskActionStatusSnapshot,
    syncTaskHeroGlassLayout,
  });
}

function workflowStepStatus(index, activeIndex, task = selectedTask) {
  if (!selectedTaskId && !task?.id) return "pending";
  const status = task?.status || "";
  const step = workflowSteps[index];
  const runningStepId = taskRunningStepId(status, task?.id);
  if (runningStepId && step.id === runningStepId) return "running";
  if (taskFailureWasRestartReclaim(task) && workflowStageCompleteFromEvidence(step.id)) return "succeeded";
  const failedStepId = taskFailureStepId(task);
  if (failedStepId) {
    const failedIndex = workflowSteps.findIndex((candidate) => candidate.id === failedStepId);
    if (step.id === failedStepId) return "failed";
    if (failedIndex >= 0) return index < failedIndex ? "succeeded" : "pending";
  }
  if (status === "created") return "pending";
  if (status === "scanned" || status === "configured") {
    return index < 1 ? "succeeded" : "pending";
  }
  if (status === "running") {
    return index < 1 ? "succeeded" : index === 1 ? "running" : "pending";
  }
  if (status === "executed") {
    return index < 2 ? "succeeded" : "pending";
  }
  if (status === "computing_metrics") {
    return index < 2 ? "succeeded" : index === 2 ? "running" : "pending";
  }
  if (status === "writing_artifacts") {
    return index < 3 ? "succeeded" : index === 3 && taskServerBusyAction(task) === "report" ? "running" : "pending";
  }
  if (status === "review_required") return "succeeded";
  if (status === "succeeded") return "succeeded";
  return "pending";
}

function workflowStepStatusLabel(status, actionId) {
  if (status === "succeeded") return "Completed";
  if (status === "review") return "Pending review";
  if (status === "failed") return "Failed";
  if (status === "running" && taskBusyAction() === actionId) return "Running";
  if (status === "running") return "Current";
  return "Not started";
}

function stepStopAction(step, task = workbenchTask()) {
  const status = task?.status || "";
  const selectedBusyAction = taskBusyAction(task?.id);
  if (step.action === "notebook" && status === "running") return "cancelNotebook";
  if (step.action === "metrics" && status === "computing_metrics") return "cancelMetrics";
  if (step.action === "report" && (selectedBusyAction === "report" || taskServerBusyAction(task) === "report")) return "cancelReport";
  return null;
}

function completedReportReadyForDownloads(step, task = workbenchTask()) {
  const selectedBusyAction = taskBusyAction(task?.id);
  return (
    step.action === "report" &&
    selectedBusyAction !== "report" &&
    task?.report_available === true &&
    ["succeeded", "review_required"].includes(task?.status)
  );
}

function stepDownloadActionsHtml(step) {
  if (!completedReportReadyForDownloads(step)) return "";
  return [
    '<div class="step-download-actions">',
    '<button class="button compact step-action-button secondary" type="button" data-step-action="previewWordReport">',
    "Preview",
    "</button>",
    '<button class="button compact step-action-button primary word" type="button" data-step-action="downloadWordReport">',
    "DownloadWord",
    "</button>",
    '<button class="button compact step-action-button excel" type="button" data-step-action="downloadExcelAnalysis">',
    "DownloadExcel",
    "</button>",
    "</div>",
  ].join("");
}

function stepActionButtonHtml(step) {
  if (selectedTaskIsAgentMode()) return "";
  if (!step.action || completedReportReadyForDownloads(step)) return "";
  const selectedBusy = selectedTaskIsBusy();
  const stopAction = stepStopAction(step);
  const isStopAction = Boolean(stopAction);
  const action = stopAction || step.action;
  const canRunAction = isStopAction || canRunStepAction(step.action);
  const disabled = !selectedTaskId || (selectedBusy && !isStopAction) || !canRunAction;
  const recommended = !isStopAction && recommendedAction() === step.action;
  const tone = isStopAction ? "danger" : recommended ? "primary" : "secondary";
  const label = isStopAction ? "Stop" : step.actionLabel || "Implementation";
  const title = !selectedTaskId
    ? "Please select the task first"
    : (selectedBusy && !isStopAction)
      ? "The current task is running"
      : !canRunAction
        ? "Complete the previous step first."
      : isStopAction
        ? "Stop Current Execution"
        : "";
  return [
    `<button class="button compact step-action-button ${tone}" type="button" data-step-action="${escapeHtml(action)}"${disabled ? " disabled" : ""}${title ? ` title="${escapeHtml(title)}"` : ""}>`,
    escapeHtml(label),
    "</button>",
  ].join("");
}

function notebookStepTone(status) {
  const value = String(status || "").toLowerCase();
  if (["success", "succeeded", "done", "completed", "passed"].includes(value)) return "succeeded";
  if (taskStopped(selectedTask) && ["running", "executing", "active"].includes(value)) return "stopped";
  if (["running", "executing", "active"].includes(value)) return "running";
  if (["failed", "error", "exception"].includes(value)) return "failed";
  return "pending";
}

function notebookStepStartedOrFinished(step) {
  const tone = notebookStepTone(step?.status);
  return tone !== "pending" || Boolean(step?.started_at || step?.ended_at);
}

function notebookStepToneForRail(step, parentStatus = "", nextStep = null) {
  const tone = notebookStepTone(step?.status);
  if (parentStatus === "succeeded" && tone === "running") return "succeeded";
  if (tone === "running" && notebookStepStartedOrFinished(nextStep)) return "succeeded";
  return tone;
}

function stepWorkflowStage(step) {
  const id = String(step?.id || "");
  if (id.startsWith("system-metrics-")) return "metrics";
  return "notebook";
}

function notebookStepsForRail() {
  const pmmlWorkflow = typeof usesPmmlScoringWorkflow === "function"
    ? usesPmmlScoringWorkflow()
    : Number(selectedTask?.validation_workflow_version) === 2;
  if (pmmlWorkflow) {
    return latestNotebookSteps.filter((step) => {
      const id = String(step?.id || "");
      return id.startsWith("system-repro-");
    });
  }
  return latestNotebookSteps.filter((step) => stepWorkflowStage(step) === "notebook");
}

function metricStepsForRail() {
  return latestNotebookSteps.filter((step) => stepWorkflowStage(step) === "metrics");
}

const v2WorkflowSubstepPlans = {
  scan: [
    { id: "v2-scan-materials", title: "Identify input files" },
    { id: "v2-scan-metadata", title: "Data dictionary and feature metadata" },
    { id: "v2-scan-contract", title: "Confirm validation inputs" },
  ],
  notebook: [
    { id: "system-repro-parse", title: "Parse PMML" },
    { id: "system-repro-pmml", title: "Score all rows with PMML" },
    { id: "system-repro-validate", title: "Validate scores" },
  ],
  metrics: [
    { id: "system-metrics-prepare", title: "Prepare data for metric calculation" },
    { id: "system-metrics-effectiveness", title: "Calculate model performance" },
    { id: "system-metrics-stability", title: "Stability analysis" },
    { id: "system-metrics-stress", title: "Model stress test" },
    { id: "system-metrics-summary", title: "Overall assessment" },
  ],
  report: [
    { id: "v2-report-conclusion", title: "Final conclusions" },
    { id: "v2-report-word", title: "Word Report" },
    { id: "v2-report-excel", title: "Excel Analysis" },
  ],
};

function v2WorkflowSubsteps(stageId, parentStatus = "pending") {
  const plannedSteps = v2WorkflowSubstepPlans[stageId] || [];
  return plannedSteps.map((plannedStep, index) => {
    const existingStep = latestNotebookSteps.find((step) => step?.id === plannedStep.id) || null;
    const step = {
      ...(existingStep || {}),
      ...plannedStep,
      system: true,
    };
    if (parentStatus === "succeeded" || parentStatus === "review") {
      return { ...step, status: "succeeded" };
    }
    if (parentStatus === "pending") {
      return { ...step, status: "pending" };
    }
    if (parentStatus === "stopped") {
      const evidenceTone = notebookStepTone(existingStep?.status);
      return { ...step, status: evidenceTone === "succeeded" ? "succeeded" : "stopped" };
    }
    if (parentStatus === "failed") {
      const evidenceTone = notebookStepTone(existingStep?.status);
      if (evidenceTone === "succeeded" || evidenceTone === "failed") {
        return { ...step, status: evidenceTone };
      }
      return { ...step, status: index === 0 ? "failed" : "pending" };
    }
    return { ...step, status: existingStep?.status || "pending" };
  });
}

function workflowStageCompleteFromEvidence(stepId) {
  if (stepId === "scan") return latestNotebookSteps.length > 0;
  const stageSteps = stepId === "notebook"
    ? notebookStepsForRail()
    : stepId === "metrics"
      ? metricStepsForRail()
      : [];
  return stageSteps.length > 0 && stageSteps.every((step) => notebookStepTone(step.status) === "succeeded");
}

function plannedReproducibilitySteps() {
  if (usesPmmlScoringWorkflow()) {
    return [
      {
        id: "system-repro-pmml",
        title: "Score all rows with PMML",
        status: "pending",
        cell_count: 0,
        cell_indexes: [],
        source_previews: [],
        system: true,
      },
    ];
  }
  return [
    {
      id: "system-repro-pmml",
      title: "PMML Score",
      status: "pending",
      cell_count: 1,
      cell_indexes: [],
      source_previews: [],
      system: true,
    },
    {
      id: "system-repro-compare",
      title: "Score comparison",
      status: "pending",
      cell_count: 1,
      cell_indexes: [],
      source_previews: [],
      system: true,
    },
  ];
}

function plannedMetricSteps() {
  if (usesPmmlScoringWorkflow()) {
    return [
      {
        id: "system-metrics-prepare",
        title: "Prepare data for metric calculation",
        status: "pending",
        cell_count: 0,
        cell_indexes: [],
        source_previews: [],
        system: true,
      },
      {
        id: "system-metrics-effectiveness",
        title: "Performance and stability checks",
        status: "pending",
        cell_count: 0,
        cell_indexes: [],
        source_previews: [],
        system: true,
      },
      {
        id: "system-metrics-stress",
        title: "Model stress test",
        status: "pending",
        cell_count: 0,
        cell_indexes: [],
        source_previews: [],
        system: true,
      },
    ];
  }
  return [
    {
      id: "system-metrics-prepare",
      title: "Prepare data for metric calculation",
      status: "pending",
      cell_count: 1,
      cell_indexes: [],
      source_previews: [],
      system: true,
    },
    {
      id: "system-metrics-score",
      title: "Score all rows with RMC_SCORE_FN",
      status: "pending",
      cell_count: 1,
      cell_indexes: [],
      source_previews: [],
      system: true,
    },
    {
      id: "system-metrics-basic",
      title: "Overview of samples and variables",
      status: "pending",
      cell_count: 1,
      cell_indexes: [],
      source_previews: [],
      system: true,
    },
    {
      id: "system-metrics-ks",
      title: "Calculate KS",
      status: "pending",
      cell_count: 1,
      cell_indexes: [],
      source_previews: [],
      system: true,
    },
    {
      id: "system-metrics-psi",
      title: "Calculate PSI",
      status: "pending",
      cell_count: 1,
      cell_indexes: [],
      source_previews: [],
      system: true,
    },
    {
      id: "system-metrics-binning",
      title: "Calculate bin statistics",
      status: "pending",
      cell_count: 1,
      cell_indexes: [],
      source_previews: [],
      system: true,
    },
    {
      id: "system-metrics-stress",
      title: "Stress test",
      status: "pending",
      cell_count: 1,
      cell_indexes: [],
      source_previews: [],
      system: true,
    },
    {
      id: "system-metrics-output",
      title: "Save metric outputs",
      status: "pending",
      cell_count: 1,
      cell_indexes: [],
      source_previews: [],
      system: true,
    },
  ];
}

function shouldPrimeReproducibilitySteps() {
  return taskBusyAction() === "notebook" || selectedTask?.status === "running";
}

function shouldPrimeMetricSteps() {
  return taskBusyAction() === "metrics" || selectedTask?.status === "computing_metrics";
}

function mergePendingSystemSteps(notebookSteps = []) {
  const steps = Array.isArray(notebookSteps) ? [...notebookSteps] : [];
  const existingIds = new Set(steps.map((step) => step?.id).filter(Boolean));
  const plannedSteps = [
    ...(shouldPrimeReproducibilitySteps() ? plannedReproducibilitySteps() : []),
    ...(shouldPrimeMetricSteps() ? plannedMetricSteps() : []),
  ];
  plannedSteps.forEach((step) => {
    if (!existingIds.has(step.id)) steps.push(step);
  });
  return steps;
}

function appendPendingReproducibilitySteps() {
  latestNotebookSteps = mergePendingSystemSteps(latestNotebookSteps);
  renderWorkflowStepper();
}

function appendPendingMetricSteps() {
  latestNotebookSteps = mergePendingSystemSteps(latestNotebookSteps);
  renderWorkflowStepper();
}

function stepElapsedSeconds(step, nextStep = null) {
  const startedAt = Date.parse(step?.started_at || "");
  if (step?.status !== "running" && Number.isFinite(step?.elapsed_seconds)) {
    const elapsed = Number(step.elapsed_seconds);
    const nextStartedAt = Date.parse(nextStep?.started_at || "");
    if (
      elapsed < 1 &&
      Number.isFinite(startedAt) &&
      Number.isFinite(nextStartedAt) &&
      nextStartedAt > startedAt
    ) {
      return Math.max(elapsed, (nextStartedAt - startedAt) / 1000);
    }
    return elapsed;
  }
  if (!Number.isFinite(startedAt)) return null;
  const endedAt = Date.parse(step?.ended_at || "");
  const endMs = Number.isFinite(endedAt) ? endedAt : Date.now();
  return Math.max(0, (endMs - startedAt) / 1000);
}

function formatStepElapsed(step, nextStep = null) {
  const seconds = stepElapsedSeconds(step, nextStep);
  if (!Number.isFinite(seconds)) return "";
  const totalSeconds = Math.max(0, Math.round(seconds));
  if (totalSeconds === 0 && seconds >= 0 && step?.status !== "pending" && step?.started_at) return "0s";
  const minutes = Math.floor(totalSeconds / 60);
  const remainder = totalSeconds % 60;
  if (minutes <= 0) return `${remainder}s`;
  return `${minutes}m ${String(remainder).padStart(2, "0")}s`;
}

function stepAfterInLatestNotebookSteps(step) {
  if (!step || !Array.isArray(latestNotebookSteps)) return null;
  const index = latestNotebookSteps.findIndex((candidate) => (
    candidate === step || (step.id && candidate.id === step.id)
  ));
  return index >= 0 ? latestNotebookSteps[index + 1] || null : null;
}

const expandedValidationStages = new Map();
function renderNotebookStepRail(
  notebookSteps = latestNotebookSteps,
  title = "Stage progress",
  parentNumber = "",
  parentStatus = "",
  stageId = "",
) {
  if (!Array.isArray(notebookSteps) || notebookSteps.length === 0) {
    return "";
  }
  const tones = notebookSteps.map((step, index) => (
    notebookStepToneForRail(step, parentStatus, notebookSteps[index + 1] || null)
  ));
  // When the parent stage is running but the backend has not flagged a specific
  // sub-step as running yet, spin the first unfinished sub-step so it stays in
  // sync with the parent's spinner instead of sitting on a hollow circle.
  const hasRunning = tones.includes("running");
  const activeIndex = parentStatus === "running" && !hasRunning
    ? tones.findIndex((tone) => tone !== "succeeded" && tone !== "failed")
    : -1;
  const expansionKey = `${workbenchTaskId()}:${stageId}`;
  const hasException = tones.some((tone) => ["failed", "review", "stopped"].includes(tone));
  const expanded = expandedValidationStages.get(expansionKey)
    ?? (hasException || ["running", "review", "failed", "stopped"].includes(parentStatus));
  const completed = tones.filter((tone) => tone === "succeeded").length;
  return [
    `<details class="notebook-step-group" data-validation-stage-expansion="${escapeHtml(expansionKey)}"${expanded ? " open" : ""}>`,
    `<summary>${escapeHtml(title)} · ${completed}/${notebookSteps.length} Completed</summary>`,
    ...notebookSteps.map((step, index) => {
      const title = step.title || step.heading || step.name || `Steps${step.step_order ?? index + 1}`;
      const tone = index === activeIndex ? "running" : tones[index];
      const cells = Number.isFinite(step.cell_count) ? `${step.cell_count} cells` : "";
      const elapsed = formatStepElapsed(step, notebookSteps[index + 1] || stepAfterInLatestNotebookSteps(step));
      const number = parentNumber ? `${parentNumber}.${index + 1}` : `${index + 1}`;
      // Two separate spans so the per-second elapsed updater can rewrite just
      // the elapsed text without touching the rest of the substep DOM.
      const cellsHtml = cells ? `<span class="step-cells">${escapeHtml(cells)}</span>` : "";
      const elapsedKey = stageId && step?.id ? `${stageId}:${step.id}` : "";
      const elapsedHtml = elapsedKey
        ? `<span class="step-elapsed" data-step-elapsed-key="${escapeHtml(elapsedKey)}">${escapeHtml(elapsed)}</span>`
        : (elapsed ? `<span class="step-elapsed">${escapeHtml(elapsed)}</span>` : "");
      const separator = cellsHtml && elapsedHtml && elapsed ? '<span class="step-sep"> · </span>' : "";
      const metaHtml = cellsHtml || elapsedHtml ? `<small>${cellsHtml}${separator}${elapsedHtml}</small>` : "";
      return [
        `<div class="notebook-step ${tone}">`,
        stepCheckerHtml(tone),
        `<span class="notebook-step-no">${escapeHtml(number)}</span>`,
        "<strong>",
        escapeHtml(title),
        "</strong>",
        metaHtml,
        "</div>",
      ].join("");
    }),
    "</details>",
  ].join("");
}

function refreshWorkflowStepperElapsedTimes() {
  const stepper = $("workflowStepper");
  if (!stepper) return;
  const notebookSteps = notebookStepsForRail();
  const metricSteps = metricStepsForRail();
  const lookup = new Map();
  const fillLookup = (stageId, steps) => {
    steps.forEach((step, index, arr) => {
      if (!step?.id) return;
      lookup.set(`${stageId}:${step.id}`, {
        step,
        next: arr[index + 1] || stepAfterInLatestNotebookSteps(step),
      });
    });
  };
  fillLookup("notebook", notebookSteps);
  fillLookup("metrics", metricSteps);
  stepper.querySelectorAll("[data-step-elapsed-key]").forEach((node) => {
    const entry = lookup.get(node.dataset.stepElapsedKey || "");
    if (!entry) return;
    const elapsed = formatStepElapsed(entry.step, entry.next);
    if (node.textContent !== elapsed) node.textContent = elapsed;
  });
}

function renderWorkflowStepper({ force = false } = {}) {
  const progressRail = $("progressRail");
  const railTitle = document.querySelector("#progressRail .step-rail-head h3");
  progressRail?.classList.remove("hidden");
  if (planRailController.render({ force, renderSignatures })) {
    return;
  }
  progressRail?.setAttribute("aria-label", "Validation steps");
  planRailController.clearRetryPanel();
  planRailController.clearDriverActionsPanel();
  if (railTitle) railTitle.textContent = "Validation steps";
  const task = workbenchTask();
  const nextSignature = workflowStepperSignature(task);
  if (!force && renderSignatures.workflowStepper === nextSignature) {
    // Structure unchanged; still tick elapsed-seconds spans so running steps
    // do not freeze at the value captured during the last structural render.
    refreshWorkflowStepperElapsedTimes();
    return;
  }
  renderSignatures.workflowStepper = nextSignature;

  const stepper = $("workflowStepper");
  const activeIndex = workflowIndex(task?.status, task);
  const stepActionIds = ["scan", "notebook", "metrics", "report"];
  const renderTaskId = workbenchTaskId() || "";
  const previousScrollTop = stepper.dataset.taskId === renderTaskId ? stepper.scrollTop : 0;
  stepper.innerHTML = "";
  workflowSteps.forEach((step, index) => {
    if (step.action && !stepActionIds.includes(step.action)) return;
    const displayStep = workflowStepForTask(step, task);
    const item = document.createElement("div");
    const classes = ["step"];
    const stepStatus = workflowStepStatus(index, activeIndex, task);
    if (stepStatus === "succeeded") {
      classes.push("succeeded");
    } else if (stepStatus === "running") {
      classes.push("running");
    } else if (stepStatus === "failed") {
      classes.push("failed");
    } else if (stepStatus === "stopped") {
      classes.push("stopped");
    } else if (stepStatus === "review") {
      classes.push("review");
    } else {
      classes.push("pending");
    }
    item.className = classes.join(" ");
    item.dataset.stepTarget = displayStep.target;
    item.tabIndex = 0;
    item.setAttribute("role", "group");
    const childSteps = usesPmmlScoringWorkflow(task)
      ? v2WorkflowSubsteps(step.id, stepStatus)
      : [];
    item.innerHTML = [
      '<div class="step-head">',
      stepCheckerHtml(stepStatus),
      `<span class="step-number">${index + 1}</span>`,
      '<span class="step-copy">',
      `<strong class="step-title">${escapeHtml(displayStep.title)}</strong>`,
      `<small class="step-hint">${escapeHtml(displayStep.hint)}</small>`,
      "</span>",
      stepActionButtonHtml(displayStep),
      "</div>",
      usesPmmlScoringWorkflow(task)
        ? renderNotebookStepRail(childSteps, "Stage tasks", index + 1, stepStatus, step.id)
        : step.id === "notebook"
          ? renderNotebookStepRail(notebookStepsForRail(), "Stage progress", index + 1, stepStatus, "notebook")
          : "",
      !usesPmmlScoringWorkflow(task) && step.id === "metrics"
        ? renderNotebookStepRail(metricStepsForRail(), "Calculation progress", index + 1, stepStatus, "metrics")
        : "",
      stepDownloadActionsHtml(displayStep),
    ].join("");
    stepper.appendChild(item);
  });
  stepper.dataset.taskId = renderTaskId;
  stepper.scrollTop = previousScrollTop;
  refreshWorkflowStepperElapsedTimes();
}

function formatDate(value) {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch (_) {
    return value;
  }
}

function taskCreatedMonth(task) {
  const rawDate = task.created_at || task.updated_at || "";
  const date = new Date(rawDate);
  if (Number.isNaN(date.getTime())) return "Unknown creation month";
  return `${date.getFullYear()}Year${String(date.getMonth() + 1).padStart(2, "0")}Month`;
}

function sortMonthGroups([left], [right]) {
  if (left === right) return 0;
  if (left === "Unknown creation month") return 1;
  if (right === "Unknown creation month") return -1;
  const direction = taskSortMode === "created_asc" ? 1 : -1;
  return left.localeCompare(right, "zh-CN") * direction;
}

function sortTaskTypeGroups([left], [right]) {
  const leftType = left || defaultTaskType;
  const rightType = right || defaultTaskType;
  const leftRank = taskTypeDisplayOrder.indexOf(leftType);
  const rightRank = taskTypeDisplayOrder.indexOf(rightType);
  if (leftRank >= 0 && rightRank >= 0) return leftRank - rightRank;
  if (leftRank >= 0) return -1;
  if (rightRank >= 0) return 1;
  return taskTypeLabel(leftType).localeCompare(taskTypeLabel(rightType), "zh-CN");
}

function compareTasks(left, right) {
  if (taskSortMode === "name_asc") {
    return taskDisplayName(left).localeCompare(taskDisplayName(right), "zh-CN");
  }
  if (taskSortMode === "name_desc") {
    return taskDisplayName(right).localeCompare(taskDisplayName(left), "zh-CN");
  }
  const leftDate = Date.parse(left.created_at || left.updated_at || "") || 0;
  const rightDate = Date.parse(right.created_at || right.updated_at || "") || 0;
  return taskSortMode === "created_asc" ? leftDate - rightDate : rightDate - leftDate;
}

function applyTaskFilters(tasks = taskCache) {
  const query = taskSearchQuery.trim().toLowerCase();
  return tasks
    .filter((task) => {
      if (!query) return true;
      return [
        taskDisplayName(task),
        task.model_name,
        task.model_version,
        task.validator,
        task.status_message,
        task.source_dir,
      ].some((value) => String(value || "").toLowerCase().includes(query));
    })
    .sort(compareTasks);
}

// Layered, multi-tone glyphs for task kinds — one shared source used by
// the sidebar rows and the task-hero snapshot. Mirrors the welcome-card icons
// in index.html; classes (back/mid/cut/cs/cst/ln) are themed in styles.css.
const TASK_KIND_GLYPHS = {
  data_join:
    '<rect class="back" x="3" y="8" width="10.5" height="10.5" rx="3"></rect><rect class="mid" x="6.75" y="6.75" width="10.5" height="10.5" rx="3"></rect><rect x="10.5" y="5.5" width="10.5" height="10.5" rx="3"></rect><rect class="cut" x="13" y="8.7" width="5.5" height="1.3" rx="0.65"></rect><rect class="cut" x="13" y="11.2" width="3.8" height="1.3" rx="0.65"></rect>',
  feature_analysis:
    '<rect class="back" x="4.4" y="16.6" width="17" height="3.4" rx="1.6"></rect><rect x="5" y="10.5" width="3.2" height="6.6" rx="1"></rect><rect x="9.2" y="7.5" width="3.2" height="9.6" rx="1"></rect><rect x="13.4" y="5" width="3.2" height="12.1" rx="1"></rect><rect x="17.6" y="9" width="3.2" height="8.1" rx="1"></rect>',
  vintage:
    '<rect class="back" x="3.5" y="6" width="17" height="12.5" rx="2"></rect><path class="ln vintage-calendar-binding" d="M7.2 4.8v2.8M16.8 4.8v2.8"></path><path class="ln" d="M6.3 15.5 9.6 12.7 13 14.1 17.8 10"></path>',
  modeling:
    '<rect x="2.6" y="4.6" width="18.8" height="14.8" rx="2.6"></rect><path class="mid" d="M2.6 8 V7 Q2.6 4.6 5 4.6 H19 Q21.4 4.6 21.4 7 V8 Z"></path><circle class="cut" cx="5.5" cy="6.2" r="0.82"></circle><circle class="cut" cx="7.7" cy="6.2" r="0.82"></circle><circle class="cut" cx="9.9" cy="6.2" r="0.82"></circle><path class="cs" d="M8.2 11.2 11 13.8 8.2 16.4"></path><rect class="cut" x="12" y="14.9" width="4" height="1.5" rx="0.75"></rect>',
  validation:
    '<rect class="back" x="7" y="3.5" width="11.5" height="16" rx="2.2"></rect><rect x="5" y="5" width="11.5" height="15.5" rx="2.2"></rect><rect class="mid" x="7.75" y="3.7" width="6" height="2.2" rx="1.1"></rect><rect class="cut" x="7.4" y="9" width="6.6" height="1.2" rx="0.6"></rect><rect class="cut" x="7.4" y="12" width="6.6" height="1.2" rx="0.6"></rect><rect class="cut" x="7.4" y="15" width="4.4" height="1.2" rx="0.6"></rect><circle class="cut" cx="16.6" cy="17.6" r="4.9"></circle><circle cx="16.6" cy="17.6" r="4"></circle><path class="cst" d="M14.8 17.7 16 18.9 18.4 16.4"></path>',
  strategy:
    '<rect class="back" x="4" y="13.8" width="16" height="4.6" rx="1.8"></rect><rect class="mid" x="4" y="9.6" width="16" height="4.6" rx="1.8"></rect><rect x="4" y="5" width="16" height="5.6" rx="1.8"></rect><rect class="cut" x="6.6" y="6.2" width="7.2" height="1.3" rx="0.65"></rect><rect class="cut" x="6.6" y="8.1" width="4.6" height="1.3" rx="0.65"></rect>',
  portfolio:
    '<circle class="back" cx="10" cy="12" r="7.2"></circle><path class="mid" d="M10 4.8a7.2 7.2 0 0 1 6.24 10.8L10 12Z"></path><path d="M11.5 3.5a8.7 8.7 0 0 1 7.53 13.05l-2.79-.95A7.2 7.2 0 0 0 10 4.8Z"></path><circle class="cut" cx="10" cy="12" r="2.35"></circle>',
};

function taskKindIconKind(taskOrType = selectedTask) {
  const kind = typeof taskOrType === "string" ? taskOrType : taskOrType?.task_type;
  // N≥2 Still model validation desk, sidebar/Title icons are selected by the clipboard that is used to validate the single model.
  if (kind === "validation_batch") return "validation";
  return TASK_KIND_GLYPHS[kind] ? kind : defaultTaskType;
}

function taskKindIconHtml(taskOrType = selectedTask, extraClass = "") {
  const safeKind = taskKindIconKind(taskOrType);
  const cls = "task-kind-icon" + (extraClass ? ` ${extraClass}` : "");
  return `<svg class="${cls}" data-kind="${escapeHtml(safeKind)}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${TASK_KIND_GLYPHS[safeKind] || ""}</svg>`;
}

// Per-row content fingerprint. When two poll ticks produce the same value the
// row's inner DOM is left untouched, so the :hover target node under the cursor
// is never rebuilt (the flicker fix) — only the shell node's mutable children
// (name/status/selected/aria-label) refresh when this actually changes.
function taskRowContentSignature(task) {
  return signatureFromParts([
    task.id === selectedTaskId ? 1 : 0,
    taskDisplayName(task),
    task.item_count || "",
    task.task_type || "",
    taskStatusTone(task),
    taskStatusLabel(task),
    task.validator || "-",
    formatDate(task.created_at || task.updated_at),
  ]);
}

function taskRowAriaLabel(task) {
  const ownerLabel = taskTypeDefinition(task.task_type).validatorLabel || "Head";
  const createdText = formatDate(task.created_at || task.updated_at);
  return [
    taskDisplayName(task),
    taskStatusLabel(task),
    `${ownerLabel} ${task.validator || "-"}`,
    createdText ? `Created on${createdText}` : "",
  ].filter(Boolean).join(",");
}

// Builds the innerHTML for the `.task-row` button. Shared by fresh creation and
// in-place content refresh so both paths stay byte-for-byte identical.
function taskRowInnerHtml(task) {
  const tone = taskStatusTone(task);
  const displayName = taskDisplayName(task);
  return [
    '<span class="task-row-top">',
    '<span class="task-row-title">',
    taskKindIconHtml(task),
    `<strong class="task-row-name">${escapeHtml(displayName)}</strong>`,
    "</span>",
    `<span class="task-row-badges"><span class="pill ${tone}">${escapeHtml(taskStatusLabel(task))}</span></span>`,
    "</span>",
  ].join("");
}

// Creates a brand-new `.task-row-shell` node for a task (used when a row first
// appears). The returned node carries data-task-id / data-row-signature so the
// reconciler can key on it and skip untouched rows on later ticks.
function createTaskRowShell(task) {
  const item = document.createElement("div");
  item.className = "task-row-shell";
  item.setAttribute("role", "listitem");
  item.dataset.taskId = task.id || "";

  const row = document.createElement("button");
  row.type = "button";
  row.className = "task-row" + (task.id === selectedTaskId ? " selected" : "");
  row.setAttribute("aria-current", task.id === selectedTaskId ? "true" : "false");
  row.setAttribute("aria-label", taskRowAriaLabel(task));
  row.innerHTML = taskRowInnerHtml(task);
  row.onclick = () => requestTaskSelection(task);

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "delete-task-button";
  deleteButton.title = "Delete Task";
  deleteButton.setAttribute("aria-label", `Delete Task${taskDisplayName(task)}`);
  deleteButton.innerHTML = [
    '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">',
    '<path d="M5 7h14"></path>',
    '<path d="M9.5 7V5.5h5V7"></path>',
    '<path d="M6.5 7 7.4 19h9.2L17.5 7"></path>',
    '<path d="M10 10.5v5"></path>',
    '<path d="M14 10.5v5"></path>',
    "</svg>",
  ].join("");
  deleteButton.onclick = (event) => {
    event.stopPropagation();
    deleteTask(task);
  };

  item.appendChild(row);
  item.appendChild(deleteButton);
  item.dataset.rowSignature = taskRowContentSignature(task);
  return item;
}

// Refreshes an existing `.task-row-shell` in place: the shell/row/delete-button
// nodes are all preserved (so :hover never drops), and the row's inner content +
// selected class + click closure are rewritten only when the signature changed.
function updateTaskRowShell(item, task) {
  const nextSignature = taskRowContentSignature(task);
  const row = item.querySelector(".task-row");
  // The click closure captures the task object; refresh it every tick so a
  // click always requests the latest task snapshot through the workspace
  // navigation guard even when the visible signature is unchanged.
  if (row) row.onclick = () => requestTaskSelection(task);
  const deleteButton = item.querySelector(".delete-task-button");
  if (deleteButton) {
    deleteButton.onclick = (event) => {
      event.stopPropagation();
      deleteTask(task);
    };
    deleteButton.setAttribute("aria-label", `Delete Task${taskDisplayName(task)}`);
  }
  if (item.dataset.rowSignature === nextSignature) return;
  item.dataset.rowSignature = nextSignature;
  if (row) {
    row.className = "task-row" + (task.id === selectedTaskId ? " selected" : "");
    row.setAttribute("aria-current", task.id === selectedTaskId ? "true" : "false");
    row.setAttribute("aria-label", taskRowAriaLabel(task));
    row.innerHTML = taskRowInnerHtml(task);
  }
}

// Keyed reconciliation of task-row shells inside a container. Existing rows are
// reused (kept as the same node object so hover survives), new rows inserted,
// removed rows dropped, and order fixed with insertBefore. `stopBefore` marks
// the first node that is NOT a managed task row (e.g. the next group heading),
// so grouped rendering can reconcile one group's slice without disturbing the
// rest of the list.
// Splices `tasks` into `container` as keyed `.task-row-shell` nodes starting
// right after `anchor`. Existing shells (matched by data-task-id) are reused so
// the hovered node survives; missing/new/reordered rows are handled by move or
// create. Returns the last node placed (the next group's anchor).
//
// `removeMissing`: when true, shells left unmatched are removed here. In grouped
// rendering this MUST be false — the same container holds other groups' rows, so
// per-group removal would nuke sibling groups. The grouped caller
// (reconcileTaskListGroups) does one authoritative removal pass instead.
function reconcileTaskRows(container, tasks, { anchor = null, stopBefore = null, removeMissing = true } = {}) {
  // Index the shells currently present in this container by task id.
  const existing = new Map();
  for (const node of Array.from(container.children)) {
    if (node === stopBefore) break;
    if (node.classList && node.classList.contains("task-row-shell") && node.dataset.taskId) {
      existing.set(node.dataset.taskId, node);
    }
  }
  let cursor = anchor;
  for (const task of tasks) {
    const key = task.id || "";
    let node = existing.get(key);
    if (node) {
      updateTaskRowShell(node, task);
      existing.delete(key);
    } else {
      node = createTaskRowShell(task);
    }
    const desiredNext = cursor ? cursor.nextSibling : container.firstChild;
    if (node !== desiredNext) {
      container.insertBefore(node, desiredNext);
    } else if (!node.parentNode) {
      container.insertBefore(node, desiredNext);
    }
    cursor = node;
  }
  // Any shell left in `existing` corresponds to a task that vanished.
  if (removeMissing) {
    for (const node of existing.values()) {
      node.remove();
    }
  }
  return cursor;
}

function renderTaskSnapshot() {
  renderTaskSnapshotView({
    selectedTask,
    getElementById: $,
    taskTypeLabel,
    taskKindIconHtml,
    runModeLabel,
  });
}

// Computes the ordered group plan for the current group mode: an array of
// { key, name, tasks } entries. Plain (ungrouped) mode returns a single
// synthetic group so the reconciler has one uniform shape to consume.
function taskListGroupPlan(tasks) {
  if (taskGroupMode === "validator") {
    const groups = new Map();
    for (const task of tasks) {
      const key = task.validator || "No reviewer assigned";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(task);
    }
    return [...groups.entries()]
      .sort(([left], [right]) => left.localeCompare(right, "zh-CN"))
      .map(([key, groupTasks]) => ({ key: `validator:${key}`, name: key, tasks: groupTasks }));
  }
  if (taskGroupMode === "task_type") {
    const groups = new Map();
    for (const task of tasks) {
      const key = task.task_type || defaultTaskType;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(task);
    }
    return [...groups.entries()]
      .sort(sortTaskTypeGroups)
      .map(([taskType, groupTasks]) => ({
        key: `task_type:${taskType}`,
        name: taskTypeLabel(taskType),
        tasks: groupTasks,
      }));
  }
  if (taskGroupMode === "created_month") {
    const groups = new Map();
    for (const task of tasks) {
      const key = taskCreatedMonth(task);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(task);
    }
    return [...groups.entries()]
      .sort(sortMonthGroups)
      .map(([key, groupTasks]) => ({ key: `created_month:${key}`, name: key, tasks: groupTasks }));
  }
  return [{ key: "__all__", name: null, tasks }];
}

// Reconciles the whole task list against the desired group plan without ever
// replacing the shell node under the cursor. Group headings are keyed by their
// group key and task rows by task id, so a poll tick that only bumps updated_at
// touches nothing structural — the :hover'd card node survives intact.
function reconcileTaskListGroups(list, plan) {
  // Existing headings (by key) so a group that persists keeps its heading node.
  const existingHeadings = new Map();
  for (const node of Array.from(list.children)) {
    if (node.classList && node.classList.contains("task-group-title") && node.dataset.groupKey) {
      existingHeadings.set(node.dataset.groupKey, node);
    }
  }
  // Drop any stale empty-state placeholder left over from a previous render.
  for (const node of Array.from(list.children)) {
    if (node.classList && node.classList.contains("empty-state")) node.remove();
  }
  const keptTaskIds = new Set();
  let cursor = null;
  for (const group of plan) {
    if (group.name !== null) {
      let heading = existingHeadings.get(group.key);
      if (!heading) {
        heading = document.createElement("div");
        heading.className = "task-group-title";
        heading.dataset.groupKey = group.key;
      }
      if (heading.textContent !== group.name) heading.textContent = group.name;
      const desiredNext = cursor ? cursor.nextSibling : list.firstChild;
      if (heading !== desiredNext) list.insertBefore(heading, desiredNext);
      existingHeadings.delete(group.key);
      cursor = heading;
    }
    for (const task of group.tasks) keptTaskIds.add(task.id || "");
    cursor = reconcileTaskRows(list, group.tasks, { anchor: cursor, removeMissing: false });
  }
  // Remove headings for groups that disappeared.
  for (const heading of existingHeadings.values()) heading.remove();
  // Remove task-row shells whose task is no longer present anywhere in the plan.
  for (const node of Array.from(list.children)) {
    if (
      node.classList
      && node.classList.contains("task-row-shell")
      && !keptTaskIds.has(node.dataset.taskId || "")
    ) {
      node.remove();
    }
  }
}

function renderTaskList(tasks = applyTaskFilters(taskCache), { force = false } = {}) {
  const nextSignature = taskListSignature(tasks, taskCache.length);
  if (!force && renderSignatures.taskList === nextSignature) return;
  renderSignatures.taskList = nextSignature;

  const list = $("taskList");
  if (taskCache.length === 0) {
    list.innerHTML = '<div class="empty-state">No tasks yet</div>';
    return;
  }
  if (tasks.length === 0) {
    list.innerHTML = '<div class="empty-state">No matching tasks.</div>';
    return;
  }

  reconcileTaskListGroups(list, taskListGroupPlan(tasks));
}

function reportDataWorkspaceError(error) {
  const detail = error?.message || "Could not sync the data workspace.";
  if (Number(error?.status) === 412) {
    setActionStatus("Data workspace version conflict.", "error", detail);
    return;
  }
  setActionStatus("Could not sync the data workspace.", "error", detail);
}

async function resolveDataWorkspaceNavigationChoice() {
  const saveFirst = await showPlatformConfirm({
    title: "Unsaved changes in the data workspace",
    message: "Save field settings before switching tasks?",
    confirmText: "Save & Switch",
    cancelText: "Other options",
  });
  if (saveFirst) return "save";
  // <dialog> dispatches its close event after the first confirmation promise
  // resolves. Opening the discard confirmation in the same turn lets that
  // stale close event immediately close the new dialog. Cross one render frame
  // so the second choice remains visible and the user can still abort the task
  // switch without losing the draft.
  await new Promise((resolve) => requestAnimationFrame(() => resolve()));
  const discard = await showPlatformConfirm({
    title: "Discard data workspace changes?",
    message: "Changes to the target field, field roles, and business names will be lost.",
    confirmText: "Discard & Switch",
    cancelText: "Stay on current task",
    tone: "danger",
  });
  return discard ? "discard" : "cancel";
}

async function reloadDataWorkspace(taskId = selectedTaskId, options = {}) {
  const normalizedTaskId = String(taskId || "").trim();
  if (!normalizedTaskId || !taskUsesDataWorkspace(selectedTask)) {
    dataWorkspacePanel.clear();
    return false;
  }
  if (selectedTaskId !== normalizedTaskId) return false;
  return dataWorkspacePanel.reload(normalizedTaskId, options);
}

function taskUsesDataWorkspace(task) {
  return [
    "data_join",
    "feature_analysis",
    "modeling",
    "strategy",
    "vintage",
    "portfolio",
  ].includes(task?.task_type);
}

async function requestTaskSelection(task) {
  if (!task?.id) return false;
  if (!taskUsesDataWorkspace(task)) {
    dataWorkspacePanel.clear();
    selectTask(task);
    return true;
  }
  try {
    return await dataWorkspacePanel.requestNavigation(async () => {
      selectTask(task);
      await dataWorkspacePanel.selectTask(task.id);
    });
  } catch (error) {
    reportDataWorkspaceError(error);
    return false;
  }
}

function selectTask(task) {
  if (window.matchMedia("(max-width: 860px)").matches) applySidebarCollapsed(true);
  rememberValidationView();
  rememberResultScrollPosition();
  if (selectedTaskId === task.id && selectedTask) {
    selectedTask = task;
    rememberSelectedTaskId(task.id);
    void validationBatchPanelController.selectTask(task);
    renderCurrentTask();
    renderTaskList();
    strategyCandidateLabController.renderAvailability();
    labelingSetupPanel.renderAvailability();
    portfolioSetupPanel.renderAvailability();
    if (task.task_type === "strategy") {
      void strategyCandidateLabController.refresh(task.id, { silent: true });
    }
    return;
  }
  // Task identity is changing — drop any in-flight typewriter state so a
  // still-revealing message from the previous task can't re-reveal (or worse,
  // leak its visible-prefix via shared messageId) on the new task's panel.
  resetAgentTypingState();
  if (selectedTaskId !== task.id) {
    invalidateAgentBatchAutoRun();
    projectedValidationChildTaskId = "";
    projectedValidationChildTask = null;
  }
  selectedTaskId = task.id;
  selectedTask = task;
  rememberSelectedTaskId(task.id);
  applyAgentTaskComposerPreferences(task.id);
  beginTaskContentLoad(task.id);
  prepareResultScrollRestoreForTask(task.id);
  ensureActiveTaskProgressPolling(task);
  renderMetricPreview({});
  renderStoredStateSummaries();
  const validationBatchLoadPromise = validationBatchPanelController.selectTask(task);
  const candidateLabLoadPromise = strategyCandidateLabController.selectTask(task);
  runAction(async () => {
    try {
      renderTaskList();
      if (!usesAgentValidationWorkbench(task)) {
        await loadTaskEvidence();
        await loadReportFields();
        await loadAgentMessages(task.id);
      }
      await validationBatchLoadPromise;
      await candidateLabLoadPromise;
    } finally {
      renderAll();
      await restoreResultScrollPositionAfterRender(task.id);
      validationBatchPanelController.focusRequestedItem();
      finishTaskContentLoad(task.id);
    }
    maybeResumeAgentValidationBatch();
  }, { renderAfter: false });
}

function deselectCurrentTask() {
  invalidateAgentBatchAutoRun();
  rememberResultScrollPosition();
  clearTaskContentLoad();
  selectedTaskId = null;
  selectedTask = null;
  projectedValidationChildTaskId = "";
  projectedValidationChildTask = null;
  rememberSelectedTaskId(null);
  validationBatchPanelController.clear();
  dataWorkspacePanel.clear();
  latestNotebookSteps = [];
  agentMessages = [];
  strategyCandidateLabController.clear();
  resetAgentComposerToGlobalDefaults();
  renderMetricPreview({});
  setActionStatus("");
  renderStoredStateSummaries();
  renderAll();
}

function renderMetricPreview(
  metricValues = lastMetricValues,
  workbookSource = null,
  sections = lastMetricTableSections,
) {
  renderMetricSectionVisibility();
  lastMetricValues = metricValues || {};
  lastMetricValuesTaskId = selectedTaskId || null;
  lastMetricTableSections = Array.isArray(sections) ? sections : [];

  // Identical metric payloads (same taskId + same values + same sections) must
  // leave the existing DOM intact so charts and KPI cards do not replay their
  // animations or drop hover state during the per-second polling loop.
  const previewTaskId = lastMetricValuesTaskId || "";
  const emptyMessage = metricPreviewEmptyMessage();
  const nextSignature = metricPreviewSignature(
    previewTaskId,
    lastMetricValues,
    lastMetricTableSections,
    emptyMessage,
  );
  if (
    renderSignatures.metricPreviewTaskId === previewTaskId
    && renderSignatures.metricPreview === nextSignature
  ) {
    return;
  }
  renderSignatures.metricPreviewTaskId = previewTaskId;
  renderSignatures.metricPreview = nextSignature;

  // VD-9: play the databar/KPI-bar entry animation only on the first
  // populated metric render for this task - later rebuilds triggered by
  // real data drift (polling) still rebuild the DOM but skip the replay,
  // mirroring the reproducibility precision-bar animation policy above.
  const shouldAnimateMetricBars = renderSignatures.metricPreviewAnimatedTaskId !== previewTaskId;

  // Extract the standalone ROC&KS section so each curve can sit beneath
  // its matching KPI card. The original section is dropped from the
  // visible list (we render 6 sections, not 7).
  let rocCurves = null;
  const visibleSections = lastMetricTableSections.filter((section) => {
    const tables = Array.isArray(section && section.tables) ? section.tables : [];
    const isRocSection =
      (tables[0] && tables[0].layout === "roc_ks_curve")
      || (section && section.title === "ROC and KS curves");
    if (isRocSection) {
      rocCurves = (tables[0] && tables[0].curves) || null;
      return false;
    }
    return true;
  });

  if (visibleSections.length === 0) {
    renderMetricPreviewEmpty(emptyMessage);
    return;
  }
  const sectionHtml = visibleSections
    .map((section, index) => renderMetricTableSection(section, index, { rocCurves, animate: shouldAnimateMetricBars }))
    .join("");
  $("metricPreview").innerHTML = sectionHtml;
  attachRocInteractions($("metricPreview"));
  attachMetricTooltip($("metricPreview"));
  if (shouldAnimateMetricBars) {
    renderSignatures.metricPreviewAnimatedTaskId = previewTaskId;
  }
}

function currentMetricPreviewHasValues(taskId = selectedTaskId) {
  return lastMetricValuesTaskId === taskId && lastMetricTableSections.length > 0;
}

function roleCounts(artifacts) {
  return artifacts.reduce((counts, artifact) => {
    counts[artifact.role] = (counts[artifact.role] || 0) + 1;
    return counts;
  }, {});
}

function materialRoleField(role) {
  return {
    notebook: "notebook_path",
    sample: "sample_path",
    model_pmml: "pmml_path",
    data_dictionary: "dictionary_path",
  }[role] || "";
}

function scanCheckTone(status) {
  if (status === "success") return "success";
  if (status === "warning") return "warning";
  if (status === "error") return "danger";
  return "";
}

function renderScanResult(result, notebookCells = []) {
  const artifacts = result.artifacts || [];
  const checks = result.checks || [];
  const counts = roleCounts(artifacts);
  const selectedMaterials = result.selected_materials || {};
  const materialChecks = requiredMaterialRoles.map(({ role, label }) => {
    const selected = selectedMaterials[materialRoleField(role)];
    if (selected) {
      return `<span class="pill success">${escapeHtml(label)} · Assigned</span>`;
    }
    const found = counts[role] || 0;
    const tone = found === 0 ? "danger" : found > 1 ? "warning" : "success";
    const text = found === 0 ? "Missing" : found > 1 ? `${found} Candidates` : "Recognized";
    return `<span class="pill ${tone}">${escapeHtml(label)} · ${escapeHtml(text)}</span>`;
  }).join("");
  const preflightChecks = checks.length
    ? [
        '<div class="preflight-check-list" aria-label="Scan precheck">',
        ...checks.map((check) => {
          const tone = scanCheckTone(check.status);
          const contractClass = check.id === "notebook_contract" ? " notebook-contract-check" : "";
          const statusText = check.status === "error"
            ? "Unusual"
            : check.status === "warning"
              ? "Hint"
              : "Pass.";
          return [
            `<div class="preflight-check-item ${tone}${contractClass}" data-check-id="${escapeHtml(check.id || "")}">`,
            `<span class="pill ${tone}">${escapeHtml(statusText)}</span>`,
            `<strong>${escapeHtml(check.label || check.id || "Checkpoint")}</strong>`,
            `<small>${escapeHtml(check.message || "")}</small>`,
            "</div>",
          ].join("");
        }),
        "</div>",
      ].join("")
    : "";
  $("scanSummary").className = "result-summary";
  $("scanSummary").innerHTML = [
    `<strong>Identified ${artifacts.length} input files.</strong>`,
    `<div class="chip-row">${materialChecks}</div>`,
    preflightChecks,
  ].join("");
  renderValidationInputContract(result.validation_input_contract || null, {
    taskId: workbenchTaskId(),
  });
  updateAgentScanSectionVisibility();
  renderNotebookSteps(result.notebook_steps || [], result.notebook_cells || notebookCells);
}

function validationContractCandidates(contract, key) {
  const values = [];
  const seen = new Set();
  for (const candidate of contract?.candidates?.[key] || []) {
    const value = candidate?.value;
    const identity = JSON.stringify(value);
    if (identity === undefined || seen.has(identity)) continue;
    seen.add(identity);
    values.push(value);
  }
  return values;
}

function validationContractSelectHtml(contract, key, label, { requireExplicit = false } = {}) {
  const values = validationContractCandidates(contract, key);
  return [
    `<label>${escapeHtml(label)}<select name="${escapeHtml(key)}"${requireExplicit ? " required" : ""}>`,
    requireExplicit ? '<option value="" selected disabled>Please select a candidate</option>' : "",
    ...values.map((value, index) => {
      const text = typeof value === "object" ? JSON.stringify(value) : String(value);
      return `<option value="${index}">${escapeHtml(text)}</option>`;
    }),
    "</select></label>",
  ].join("");
}

function validationContractCandidateValue(form, contract, key) {
  const rawIndex = form.elements.namedItem(key)?.value;
  if (rawIndex === undefined || rawIndex === null || rawIndex === "") return undefined;
  const index = Number(rawIndex);
  if (!Number.isInteger(index) || index < 0) return undefined;
  return validationContractCandidates(contract, key)[index];
}

function validationContractScalar(value) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch (_) {
    return text;
  }
}

function renderValidationInputContract(record, options = {}) {
  const taskId = String(options.taskId || workbenchTaskId() || selectedTaskId || "");
  const parentTaskId = String(options.parentTaskId || "");
  const item = options.item || null;
  const panelId = options.panelId || (
    parentTaskId ? "batchValidationContractPanel" : "validationContractPanel"
  );
  const panel = $(panelId);
  if (!panel) return;
  const batchMode = Boolean(parentTaskId);
  const matchesWorkspace = batchMode
    ? selectedTaskId === parentTaskId && selectedTaskIsValidationBatch()
    : usesPmmlScoringWorkflow() && isWorkbenchTaskId(taskId);
  if (!record || !matchesWorkspace) {
    panel.classList.add("hidden");
    panel.innerHTML = "";
    if (latestValidationInputContractContext?.panelId === panelId) {
      latestValidationInputContract = null;
      latestValidationInputContractTaskId = "";
      latestValidationInputContractContext = null;
    }
    return;
  }
  latestValidationInputContract = record;
  latestValidationInputContractTaskId = taskId;
  latestValidationInputContractContext = {
    taskId,
    parentTaskId,
    item,
    panelId,
  };
  panel.classList.remove("hidden");
  const modelLabel = [item?.modelName, item?.modelVersion].filter(Boolean).join(" · ");
  const batchHead = batchMode
    ? [
      '<div class="validation-batch-contract-head">',
      '<div><span class="validation-batch-contract-eyebrow">MODEL INPUTS</span>',
      `<h4>Confirm validation fields${modelLabel ? ` · ${escapeHtml(modelLabel)}` : ""}</h4></div>`,
      '<button type="button" class="button compact secondary" data-validation-contract-close>Close</button>',
      "</div>",
    ].join("")
    : '<h4>Confirm validation fields</h4>';
  if (record.status === "ready") {
    if (batchMode) validationBatchPanelController.markContractConfirmed?.(taskId);
    panel.innerHTML = batchMode
      ? `${batchHead}<p>Validation fields confirmed for this model.</p>`
      : '<h4>Validation field confirmed</h4><p>Inputs are confirmed. You can start PMML scoring.</p>';
    return;
  }
  if (record.status !== "pending_confirmation") {
    panel.innerHTML = batchMode
      ? `${batchHead}<p>Validation fields are not confirmed: ${escapeHtml(record.status || "Unknown status")}</p>`
      : `<h4>Validation fields need confirmation</h4><p>${escapeHtml(record.status || "Unknown status")}</p>`;
    return;
  }
  const contract = record.contract || {};
  const timeField = validationContractCandidates(contract, "time_col")[0] || "";
  const timeGranularity = /date|day|dt/i.test(String(timeField)) ? "date" : "month";
  const algorithm = validationContractCandidates(contract, "algorithm")[0]
    || contract.pmml_manifest?.algorithm
    || "-";
  const formContextAttributes = [
    ` data-validation-contract-task-id="${escapeHtml(taskId)}"`,
    ` data-validation-contract-parent-task-id="${escapeHtml(parentTaskId)}"`,
    ` data-validation-contract-panel-id="${escapeHtml(panelId)}"`,
  ].join("");
  const explicitChoice = { requireExplicit: false };
  panel.innerHTML = [
    `<form id="validationContractForm"${formContextAttributes}>`,
    batchHead,
    batchMode
      ? `<p>Candidate fields were identified from this model’s notebook, PMML, samples, and data dictionary. Algorithm: ${escapeHtml(algorithm)}. Confirm the fields below, or specify changes in the conversation using the model name and field.</p>`
      : `<p>Candidate fields were identified from the notebook, PMML, samples, and data dictionary. Algorithm: ${escapeHtml(algorithm)}. Review the fields and confirm to continue.</p>`,
    '<div class="validation-contract-grid">',
    validationContractSelectHtml(contract, "target_col", "Target field", explicitChoice),
    '<label>Bad sample value<input name="positive_label" value="1" /></label>',
    '<label>Good sample value<input name="negative_label" value="0" /></label>',
    validationContractSelectHtml(contract, "split_col", "Sample partition field", explicitChoice),
    '<label>Training partition value<input name="split_train" value="train" /></label>',
    '<label>Test partition value<input name="split_test" value="test" /></label>',
    '<label>Out-of-time partition value<input name="split_oot" value="oot" /></label>',
    validationContractSelectHtml(contract, "time_col", "Time field", explicitChoice),
    `<label>Time granularity<select name="time_granularity"><option value="date"${timeGranularity === "date" ? " selected" : ""}>Day</option><option value="month"${timeGranularity === "month" ? " selected" : ""}>Month</option></select></label>`,
    validationContractSelectHtml(contract, "pmml_output_field", "PMML score output field", explicitChoice),
    validationContractSelectHtml(contract, "model_params", "Model Parameter Source", explicitChoice),
    validationContractSelectHtml(contract, "feature_metadata_selection", "Feature metadata source", explicitChoice),
    "</div>",
    '<div class="validation-contract-actions">',
    `<button class="button primary" type="submit" data-validation-contract-submit>${batchMode ? "Confirm model fields" : "Confirm Fields and Continue"}</button>`,
    '<span class="status" data-validation-contract-status></span>',
    "</div>",
    "</form>",
  ].join("");
  if (batchMode) {
    window.requestAnimationFrame(() => panel.scrollIntoView?.({ block: "nearest", behavior: "smooth" }));
  }
}

async function loadValidationInputContract(taskId = workbenchTaskId(), options = {}) {
  const parentTaskId = String(options.parentTaskId || "");
  const batchMode = Boolean(parentTaskId);
  if (!taskId || (!batchMode && !usesPmmlScoringWorkflow())) return null;
  const loadVersion = ++validationInputContractLoadVersion;
  const renderOptions = { ...options, taskId, parentTaskId };
  if (batchMode && selectedTaskId === parentTaskId) {
    const panel = $("batchValidationContractPanel");
    panel?.classList.remove("hidden");
    if (panel) panel.innerHTML = '<div class="validation-batch-loading" role="status">Loading model input fields...</div>';
  }
  try {
    const record = await api(`/api/tasks/${encodeURIComponent(taskId)}/validation-input-contract`);
    if (loadVersion !== validationInputContractLoadVersion) return null;
    if (batchMode) {
      if (selectedTaskId !== parentTaskId || !selectedTaskIsValidationBatch()) return null;
      renderValidationInputContract(record, renderOptions);
    } else if (isWorkbenchTaskId(taskId)) {
      renderValidationInputContract(record, renderOptions);
    }
    return record;
  } catch (error) {
    if (loadVersion !== validationInputContractLoadVersion) return null;
    if (batchMode && selectedTaskId === parentTaskId) {
      const panel = $("batchValidationContractPanel");
      panel?.classList.remove("hidden");
      if (panel) {
        panel.innerHTML = `<div class="validation-batch-load-error" role="alert"><strong>Could not load validation inputs</strong><span>${escapeHtml(error?.message || "Please try again later.")}</span></div>`;
      }
    }
    if (options.throwOnError) throw error;
    // The scan result remains the fallback until a contract record exists.
    return null;
  }
}

async function submitValidationInputContract(form) {
  const record = latestValidationInputContract;
  const taskId = form.dataset.validationContractTaskId || workbenchTaskId() || selectedTaskId;
  const parentTaskId = form.dataset.validationContractParentTaskId || "";
  const context = latestValidationInputContractContext || {};
  if (
    !record
    || !taskId
    || latestValidationInputContractTaskId !== taskId
    || record.status !== "pending_confirmation"
  ) return;
  if (parentTaskId) {
    if (selectedTaskId !== parentTaskId || !selectedTaskIsValidationBatch()) return;
  } else if (!isWorkbenchTaskId(taskId)) {
    return;
  }
  const contract = record.contract || {};
  const status = form.querySelector("[data-validation-contract-status]");
  const button = form.querySelector("[data-validation-contract-submit]");
  const candidateKeys = [
    "target_col",
    "split_col",
    "time_col",
    "pmml_output_field",
    "model_params",
    "feature_metadata_selection",
  ];
  const selectedCandidates = Object.fromEntries(
    candidateKeys.map((key) => [key, validationContractCandidateValue(form, contract, key)]),
  );
  if (
    parentTaskId
    && (
      candidateKeys.some((key) => selectedCandidates[key] === undefined)
      || !form.elements.time_granularity.value
    )
  ) {
    if (status) status.textContent = "Select all required fields and a time granularity.";
    return;
  }
  const metadata = selectedCandidates.feature_metadata_selection || {};
  button.disabled = true;
  if (status) status.textContent = "Validating fields...";
  try {
    const confirmed = await api(`/api/tasks/${encodeURIComponent(taskId)}/validation-input-contract`, {
      method: "PUT",
      body: JSON.stringify({
        revision: record.revision,
        target_col: selectedCandidates.target_col,
        positive_label: validationContractScalar(form.elements.positive_label.value),
        negative_label: validationContractScalar(form.elements.negative_label.value),
        split_col: selectedCandidates.split_col,
        split_value_mapping: {
          train: validationContractScalar(form.elements.split_train.value),
          test: validationContractScalar(form.elements.split_test.value),
          oot: validationContractScalar(form.elements.split_oot.value),
        },
        time_col: selectedCandidates.time_col,
        time_granularity: form.elements.time_granularity.value,
        pmml_output_field: selectedCandidates.pmml_output_field,
        model_params: selectedCandidates.model_params || {},
        metadata_sheet: metadata.metadata_sheet ?? null,
        feature_col: metadata.feature_col,
        category_col: metadata.category_col,
        importance_col: metadata.importance_col,
        transformations: contract.transformations || [],
      }),
    });
    if (parentTaskId) {
      if (selectedTaskId !== parentTaskId) return;
      await validationBatchPanelController.selectTask(selectedTask, { force: true });
      if (selectedTaskId !== parentTaskId || !selectedTaskIsValidationBatch()) return;
      const remaining = validationBatchPanelController.markContractConfirmed(taskId);
      if (latestValidationInputContractTaskId === taskId) {
        renderValidationInputContract(confirmed, context);
      }
      const modelLabel = [context.item?.modelName, context.item?.modelVersion]
        .filter(Boolean)
        .join(" · ");
      setActionStatus(
        remaining > 0
          ? `${modelLabel || "Current Model"}Fields confirmed. Automatic review is continuing.`
          : "Fields confirmed. Automatic review is continuing.",
        "success",
      );
      await continueAgentValidationBatch({ resumeChildId: taskId });
      return;
    }
    if (!isWorkbenchTaskId(taskId)) return;
    renderValidationInputContract(confirmed, { taskId });
    setActionStatus("Validation fields confirmed. Continuing PMML scoring.", "success");
    if (selectedTaskIsAgentMode()) {
      const input = $("agentComposerInput");
      input.value = "Continue";
      await startAgentValidation();
    }
  } catch (error) {
    button.disabled = false;
    if (status) status.textContent = error?.message || "Field confirmation failed";
    throw error;
  }
}

if (typeof document !== "undefined") {
  document.addEventListener("click", (event) => {
    if (!event.target?.closest?.("[data-validation-contract-close]")) return;
    validationInputContractLoadVersion += 1;
    renderValidationInputContract(null, {
      panelId: "batchValidationContractPanel",
      parentTaskId: selectedTaskId,
    });
  });
  document.addEventListener("submit", (event) => {
    const form = event.target?.closest?.("#validationContractForm");
    if (!form) return;
    event.preventDefault();
    runAction(() => submitValidationInputContract(form), {
      actionId: "validationContract",
      busyText: "Confirming validation field...",
    });
  });
}

function renderValidationResult(result) {
  if (!result?.status) return;
  setActionStatus(
    usesPmmlScoringWorkflow() ? "PMML scoring started." : "Notebook run started.",
    "busy",
  );
}

function evidenceEmpty(id, message) {
  const element = $(id);
  if (!element) return;
  element.className = "result-summary empty";
  element.textContent = message;
}

function reproducibilityEmptyMessage(task = selectedTask) {
  if (usesPmmlScoringWorkflow(task)) {
    const stage = taskFailureStage(task);
    if (stage === "notebook") return "PMML scoring failed. Check the PMML file and input fields, then restart.";
    if (stage === "scan") return "PMML scoring results are unavailable until input file checks pass.";
    return "Results appear after PMML scoring is complete.";
  }
  const stage = taskFailureStage(task);
  if (stage === "notebook") {
    return "Model reproducibility validation failed. Fix the notebook and rerun this stage.";
  }
  if (stage === "scan") {
    return "Score comparisons are unavailable until input file checks pass.";
  }
  return "Score comparisons appear after the model code runs.";
}

function metricPreviewEmptyMessage(task = selectedTask) {
  const stage = taskFailureStage(task);
  if (stage === "notebook") {
    return usesPmmlScoringWorkflow(task)
      ? "Performance and stability metrics are unavailable because PMML scoring did not pass."
      : "Performance and stability metrics are unavailable because reproducibility validation failed.";
  }
  if (stage === "metrics") {
    return "Performance and stability checks failed. Rerun the metric calculation.";
  }
  if (stage === "scan") {
    return "Performance and stability metrics are unavailable until input file checks pass.";
  }
  return "Results appear after performance and stability checks finish.";
}

function renderMetricPreviewEmpty(message = metricPreviewEmptyMessage()) {
  const element = $("metricPreview");
  if (!element) return;
  element.innerHTML = `<div class="result-summary empty">${escapeHtml(message)}</div>`;
}

function resetEvidenceSummaries() {
  latestNotebookSteps = [];
  evidenceEmpty("reproducibilitySummary", reproducibilityEmptyMessage());
  renderMetricPreviewEmpty();
  resetReproducibilityRenderSignatures();
  renderWorkflowStepper();
}

function normalizeNotebookSteps(notebookSteps = [], notebookCells = []) {
  const steps = Array.isArray(notebookSteps) ? notebookSteps : [];
  const cells = Array.isArray(notebookCells) ? notebookCells : [];
  if (!cells.length) return steps;
  const cellsByIndex = new Map(cells.map((cell) => [Number(cell?.cell_index), cell]));
  return steps.map((step) => {
    const id = String(step?.id || "");
    const cellIndexes = Array.isArray(step?.cell_indexes) ? step.cell_indexes : [];
    if (!step?.system || !id.startsWith("system-") || cellIndexes.length <= 1) return step;

    let latestCell = null;
    let latestCellIndex = null;
    let latestSourcePreview = null;
    cellIndexes.forEach((cellIndex, index) => {
      const numericIndex = Number(cellIndex);
      if (!Number.isFinite(numericIndex)) return;
      const cell = cellsByIndex.get(numericIndex);
      if (!cell || (cell.step_id && cell.step_id !== id)) return;
      if (latestCellIndex !== null && numericIndex < latestCellIndex) return;
      latestCell = cell;
      latestCellIndex = numericIndex;
      latestSourcePreview = Array.isArray(step.source_previews) ? step.source_previews[index] : null;
    });
    if (!latestCell || latestCellIndex === null) return step;

    const normalized = {
      ...step,
      status: latestCell.status || step.status,
      started_at: latestCell.started_at ?? step.started_at,
      ended_at: latestCell.ended_at ?? step.ended_at,
      elapsed_seconds: latestCell.elapsed_seconds ?? null,
      cell_count: 1,
      cell_indexes: [latestCellIndex],
    };
    if (latestSourcePreview !== null && latestSourcePreview !== undefined) {
      normalized.source_previews = [latestSourcePreview];
    }
    return normalized;
  });
}

function renderNotebookSteps(notebookSteps = [], notebookCells = []) {
  latestNotebookSteps = mergePendingSystemSteps(normalizeNotebookSteps(notebookSteps, notebookCells));
  renderReproducibilitySectionVisibility();
  renderMetricSectionVisibility();
  renderWorkflowStepper();
}

function formatScoreValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return number.toFixed(6);
}

function reproducibilityStatusLabel(status) {
  if (status === "pass") return "Unanimously";
  if (status === "fail") return "Inconsistencies";
  if (status === "review") return "Pending review";
  return status || "Unknown";
}

function reproducibilityStatusClass(status) {
  if (status === "pass") return "repro-status-pass";
  if (status === "fail") return "repro-status-fail";
  if (status === "review") return "repro-status-review";
  return "";
}

function reproducibilityEvidenceSignature(reproducibility = {}, summary = {}, rows = []) {
  return JSON.stringify({
    status: summary.status || "",
    sample_size: reproducibility.sample_size ?? null,
    seed: reproducibility.seed ?? null,
    mismatch_count: summary.mismatch_count ?? null,
    max_abs_diff: summary.max_abs_diff ?? null,
    rows: rows.map((row) => ({
      row_index: row.row_index ?? null,
      score_code_model: row.score_code_model ?? null,
      score_submitted_pmml: row.score_submitted_pmml ?? null,
      abs_diff: row.abs_diff ?? null,
      matched: row.matched ?? null,
    })),
  });
}

function currentReproducibilityTaskId() {
  return selectedTaskId || "unselected";
}

function renderPmmlScoringEvidence(scoring = {}) {
  const element = $("reproducibilitySummary");
  if (!element) return;
  const taskId = currentReproducibilityTaskId();
  if (!scoring || Object.keys(scoring).length === 0) {
    const emptyMessage = reproducibilityEmptyMessage();
    evidenceEmpty("reproducibilitySummary", emptyMessage);
    renderSignatures.reproducibilityTaskId = taskId;
    renderSignatures.reproducibilityEvidence = "";
    renderSignatures.reproducibilityEmpty = emptyMessage;
    return;
  }
  const evidenceSignature = JSON.stringify({
    status: scoring.status || "",
    input_row_count: scoring.input_row_count ?? null,
    success_count: scoring.success_count ?? null,
    failure_count: scoring.failure_count ?? null,
    null_count: scoring.null_count ?? null,
    non_finite_count: scoring.non_finite_count ?? null,
    output_field: scoring.output_field || "",
    engine: scoring.engine || "",
    elapsed_seconds: scoring.elapsed_seconds ?? null,
    rows_per_second: scoring.rows_per_second ?? null,
    bounded_errors: scoring.bounded_errors || [],
  });
  if (
    renderSignatures.reproducibilityTaskId === taskId
    && renderSignatures.reproducibilityEvidence === evidenceSignature
  ) {
    return;
  }
  const passed = scoring.status === "pass";
  const statusClass = passed ? "repro-status-pass" : "repro-status-fail";
  const errors = Array.isArray(scoring.bounded_errors) ? scoring.bounded_errors : [];
  const errorsHtml = errors.length
    ? `<div class="result-summary error-detail">${errors.slice(0, 5).map((error) => `<div>${escapeHtml(error)}</div>`).join("")}</div>`
    : "";
  const elapsed = Number(scoring.elapsed_seconds);
  const throughput = Number(scoring.rows_per_second);
  element.className = "result-summary";
  element.innerHTML = [
    '<div class="summary-grid">',
    `<div class="summary-item ${statusClass}"><span>Status</span><strong>${passed ? "Pass." : "Failed"}</strong></div>`,
    `<div class="summary-item"><span>Full sample</span><strong>${escapeHtml(scoring.input_row_count ?? "-")}</strong></div>`,
    `<div class="summary-item"><span>Success</span><strong>${escapeHtml(scoring.success_count ?? "-")}</strong></div>`,
    `<div class="summary-item"><span>Failed scoring</span><strong>${escapeHtml(scoring.failure_count ?? 0)}</strong></div>`,
    `<div class="summary-item"><span>Missing / non-finite</span><strong>${escapeHtml(scoring.null_count ?? 0)} / ${escapeHtml(scoring.non_finite_count ?? 0)}</strong></div>`,
    `<div class="summary-item"><span>Output Field</span><strong>${escapeHtml(scoring.output_field || "-")}</strong></div>`,
    `<div class="summary-item"><span>Batch Engine</span><strong>${escapeHtml(scoring.engine || "-")}</strong></div>`,
    `<div class="summary-item"><span>Elapsed time / throughput</span><strong>${Number.isFinite(elapsed) ? `${elapsed.toFixed(2)}s` : "-"} / ${Number.isFinite(throughput) ? `${Math.round(throughput)} Okay./s` : "-"}</strong></div>`,
    "</div>",
    errorsHtml,
  ].join("");
  renderSignatures.reproducibilityTaskId = taskId;
  renderSignatures.reproducibilityEvidence = evidenceSignature;
  renderSignatures.reproducibilityEmpty = "";
}

function renderReproducibilityEvidence(reproducibility = {}) {
  const summary = reproducibility?.summary || {};
  const rows = Array.isArray(reproducibility?.rows) ? reproducibility.rows : [];
  const element = $("reproducibilitySummary");
  const taskId = currentReproducibilityTaskId();
  if (!summary || Object.keys(summary).length === 0) {
    const emptyMessage = reproducibilityEmptyMessage();
    // While polling an active run, evidence payloads may transiently arrive
    // empty between populated ones (different backend writers update at
    // different times). Don't clobber a chart we've already rendered for
    // THIS task — that would let the next populated poll re-trigger the
    // precision-bar CSS entry animation, causing the bars to "keep
    // bouncing" each second.
    if (
      !taskFailedDuringNotebook(selectedTask)
      && renderSignatures.reproducibilityEvidence
      && renderSignatures.reproducibilityTaskId === taskId
    ) {
      return;
    }
    if (
      !renderSignatures.reproducibilityEvidence
      && emptyMessage === renderSignatures.reproducibilityEmpty
      && renderSignatures.reproducibilityTaskId === taskId
    ) {
      return;
    }
    evidenceEmpty("reproducibilitySummary", emptyMessage);
    renderSignatures.reproducibilityTaskId = taskId;
    renderSignatures.reproducibilityEvidence = "";
    renderSignatures.reproducibilityEmpty = emptyMessage;
    return;
  }
  const evidenceSignature = reproducibilityEvidenceSignature(reproducibility, summary, rows);
  if (
    renderSignatures.reproducibilityTaskId === taskId
    && renderSignatures.reproducibilityEvidence === evidenceSignature
  ) {
    return;
  }
  // Animation policy: play the precision-bar entry animation only on the
  // FIRST populated render for a given task. Subsequent rebuilds caused by
  // real data drift (rows changed, summary updated) still rebuild the DOM
  // but with `data-animation="none"` so the bars do not visually replay.
  const shouldAnimatePrecisionChart = renderSignatures.reproducibilityAnimatedTaskId !== taskId;
  const maxDiff = rows.reduce((current, row) => {
    const diff = row.abs_diff === null || row.abs_diff === undefined ? Number.NaN : Number(row.abs_diff);
    return Number.isFinite(diff) ? Math.max(current, diff) : current;
  }, 0);
  const rowLimit = 10;
  const rowItems = rows.slice(0, rowLimit).map((row) => {
    const diff = row.abs_diff === null || row.abs_diff === undefined ? Number.NaN : Number(row.abs_diff);
    const diffWidth = maxDiff > 0 && Number.isFinite(diff)
      ? Math.max(2, Math.min(100, (diff / maxDiff) * 100))
      : 0;
    return [
      `<div class="score-compare-row ${row.matched ? "matched" : "mismatched"}">`,
      `<span>${escapeHtml(row.row_index ?? "-")}</span>`,
      `<strong>${escapeHtml(formatScoreValue(row.score_code_model))}</strong>`,
      `<strong>${escapeHtml(formatScoreValue(row.score_submitted_pmml))}</strong>`,
      '<span class="score-diff-cell">',
      `<span>${escapeHtml(formatScoreValue(row.abs_diff))}</span>`,
      '<span class="score-diff-track" aria-hidden="true">',
      `<span class="score-diff-bar" style="width: ${diffWidth}%"></span>`,
      "</span>",
      "</span>",
      "</div>",
    ].join("");
  });
  const shouldShowRows = summary.status !== "pass";
  const rowsHtml = !shouldShowRows
    ? ""
    : rows.length
    ? [
        '<div class="score-compare-list">',
        '<div class="score-compare-row score-compare-head">',
        "<span>Line Number</span>",
        "<span>Code model score</span>",
        "<span>PMML score</span>",
        "<span>Absolute difference</span>",
        "</div>",
        ...rowItems,
        rows.length > rowLimit ? `<small>Showing the first ${rowLimit} of ${rows.length} rows.</small>` : "",
        "</div>",
      ].join("")
    : '<div class="result-summary empty">No details are available.</div>';
  const precisionChartHtml = renderPrecisionConsistencyChart(rows, {
    animate: shouldAnimatePrecisionChart,
  });
  const statusClass = ["summary-item", reproducibilityStatusClass(summary.status)]
    .filter(Boolean)
    .join(" ");
  element.className = "result-summary";
  element.innerHTML = [
    '<div class="summary-grid">',
    `<div class="${statusClass}"><span>Status</span><strong>${escapeHtml(reproducibilityStatusLabel(summary.status))}</strong></div>`,
    `<div class="summary-item"><span>Sample rows</span><strong>${escapeHtml(reproducibility.sample_size ?? "-")}</strong></div>`,
    `<div class="summary-item"><span>Mismatches at 6 decimal places</span><strong>${escapeHtml(summary.mismatch_count ?? 0)}</strong></div>`,
    `<div class="summary-item"><span>Max. absolute difference</span><strong>${escapeHtml(formatScoreValue(summary.max_abs_diff))}</strong></div>`,
    "</div>",
    precisionChartHtml,
    rowsHtml,
  ].join("");
  renderSignatures.reproducibilityTaskId = taskId;
  renderSignatures.reproducibilityEvidence = evidenceSignature;
  renderSignatures.reproducibilityEmpty = "";
  if (shouldAnimatePrecisionChart) {
    renderSignatures.reproducibilityAnimatedTaskId = taskId;
  }
}

function renderEvidence(evidence = {}) {
  renderReproducibilitySectionVisibility();
  if (evidence.scan && Object.keys(evidence.scan).length > 0) {
    renderScanResult(evidence.scan, evidence.notebook_cells || []);
  } else {
    renderNotebookSteps(evidence.notebook_steps || [], evidence.notebook_cells || []);
  }
  if (usesPmmlScoringWorkflow()) {
    renderPmmlScoringEvidence(evidence.pmml_scoring || {});
  } else {
    renderReproducibilityEvidence(evidence.reproducibility || {});
  }
  if (selectedTaskIsAgentMode()) {
    lastAgentRenderSignature = null;
    renderAgentConversation();
  }
}

async function loadTaskEvidence(taskId = workbenchTaskId()) {
  if (!taskId || (usesAgentValidationWorkbench(selectedTask) && taskId === selectedTaskId)) {
    resetEvidenceSummaries();
    return;
  }
  try {
    const evidence = await api(`/api/tasks/${taskId}/evidence`);
    if (!isWorkbenchTaskId(taskId)) return;
    renderEvidence(evidence || {});
    await loadValidationInputContract(taskId);
  } catch (_) {
    if (isWorkbenchTaskId(taskId) && !notebookReproducibilityComplete(workbenchTask())) {
      resetEvidenceSummaries();
    }
  }
}

function renderActionError(actionId, message) {
  const summaryId = {
    scan: "scanSummary",
    notebook: "reproducibilitySummary",
  }[actionId];
  if (!summaryId) return;
  $(summaryId).className = "result-summary error";
  $(summaryId).innerHTML = `<strong>Operation failed.</strong><span>${escapeHtml(message)}</span>`;
  if (actionId === "scan") updateAgentScanSectionVisibility();
}

function scanSummaryHasResult() {
  const scanSummary = $("scanSummary");
  return Boolean(scanSummary && !scanSummary.classList.contains("empty") && scanSummary.textContent.trim());
}

function updateAgentScanSectionVisibility() {
  const scanSection = $("scanSection");
  if (!scanSection) return;
  // Driver tasks (data_join / feature / modeling) never use the validation
  // scan→notebook→metrics flow — they drive everything through the conversation +
  // plan rail. Hide the scan section entirely so a manual driver task doesn't show
  // a dead "Click on the scan." prompt with no scan button to click.
  if (taskUsesPlanRail(selectedTask)) {
    scanSection.classList.add("hidden");
    return;
  }
  if (!selectedTaskIsAgentMode(workbenchTask())) {
    scanSection.classList.remove("hidden");
    return;
  }
  const hasScanResult = scanSummaryHasResult();
  scanSection.classList.toggle("hidden", !hasScanResult);
}

function updateAgentReportSectionVisibility() {
  const reportSection = $("reportSection");
  if (!reportSection) return;
  const hasReportMessages = ["agentReportLeadMessages", "agentReportMessages"]
    .some((targetId) => Boolean($(targetId)?.children.length));
  reportSection.setAttribute("aria-hidden", hasReportMessages ? "false" : "true");
}

function renderStoredStateSummaries() {
  renderReproducibilitySectionVisibility();
  renderMetricSectionVisibility();
  const scanEmptyText = selectedTaskId ? "Select Scan files to begin." : "Select a task, then select Scan files to begin.";
  $("scanSummary").className = "result-summary empty";
  $("scanSummary").textContent = selectedTaskIsAgentMode() ? "" : scanEmptyText;
  validationInputContractLoadVersion += 1;
  renderValidationInputContract(null);
  renderValidationInputContract(null, { panelId: "batchValidationContractPanel" });
  updateAgentScanSectionVisibility();
  resetEvidenceSummaries();
  updateAgentReportSectionVisibility();
  renderTaskSnapshot();
}

function renderAll() {
  renderCurrentTask({ force: true });
  validationBatchPanelController.renderVisibility(selectedTask);
  renderReproducibilitySectionVisibility();
  renderMetricSectionVisibility();
  renderWorkflowStepper({ force: true });
  renderTaskList();
  renderSettingsState();
  renderAgentConversation();
  strategyCandidateLabController.renderAvailability();
  labelingSetupPanel.renderAvailability();
  portfolioSetupPanel.renderAvailability();
  renderPetState();
  updateAgentSendDisabled();
}

// Lighter-weight repaint for the per-second polling loop: each renderer's
// own signature guard decides whether to touch the DOM, so unchanged regions
// keep their existing nodes (and animations) intact.
function renderChangedValidationViews() {
  renderCurrentTask();
  validationBatchPanelController.renderVisibility(selectedTask);
  renderReproducibilitySectionVisibility();
  renderMetricSectionVisibility();
  renderWorkflowStepper();
  renderTaskList();
  renderSettingsState();
  renderAgentConversation();
  strategyCandidateLabController.renderAvailability();
  labelingSetupPanel.renderAvailability();
  portfolioSetupPanel.renderAvailability();
  renderPetState();
  updateAgentSendDisabled();
}

function renderAgentModelOptions() {
  const select = $("agentModelSelect");
  if (!select) return;
  const enabledModels = llmSettings.enabled_models || [];
  const configureModel = $("configureAgentModelButton");
  if (configureModel) configureModel.hidden = enabledModels.length > 0;
  const preferred = agentPreferredModelId(enabledModels);
  const signature = JSON.stringify({
    default_model_id: llmSettings.default_model_id || "",
    models: enabledModels.map((model) => ({
      model_id: model.model_id || "",
      display_name: model.display_name || "",
      model_name: model.model_name || "",
    })),
  });
  if (select.dataset.agentModelOptionsSignature === signature) {
    select.disabled = enabledModels.length === 0;
    const preferredStillAvailable = Array.from(select.options).some((option) => option.value === preferred);
    if (document.activeElement !== select && preferred && preferredStillAvailable && select.value !== preferred) {
      select.value = preferred;
    }
    return;
  }
  select.dataset.agentModelOptionsSignature = signature;
  select.innerHTML = "";
  if (enabledModels.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No AI model configured";
    select.appendChild(option);
    select.disabled = true;
    return;
  }
  select.disabled = false;
  enabledModels.forEach((model) => {
    const option = document.createElement("option");
    option.value = model.model_id;
    option.textContent = model.display_name || model.model_name || model.model_id;
    if (option.value === preferred) option.selected = true;
    select.appendChild(option);
  });
}

function agentPreferredModelId(enabledModels = llmSettings.enabled_models || []) {
  const enabledIds = new Set(
    enabledModels
      .map((model) => model.model_id || "")
      .filter(Boolean),
  );
  if (agentSelectedModelId && enabledIds.has(agentSelectedModelId)) return agentSelectedModelId;
  if (llmSettings.default_model_id && enabledIds.has(llmSettings.default_model_id)) {
    return llmSettings.default_model_id;
  }
  return enabledModels.find((model) => model.model_id)?.model_id || "";
}

function setAgentComposerNotice(message = "", kind = "info") {
  const notice = $("agentComposerNotice");
  if (!notice) return;
  if (!message) clearActionStatusOverride();
  notice.textContent = message || "";
  notice.className = `agent-composer-notice ${message ? kind : ""}`.trim();
  notice.setAttribute("role", kind === "error" ? "alert" : "status");
  notice.setAttribute("aria-live", kind === "error" ? "assertive" : "polite");
  requestAnimationFrame(syncAgentComposerClearance);
}

function agentModelUnavailableMessage() {
  const enabledModels = llmSettings.enabled_models || [];
  if (enabledModels.length === 0) return AGENT_NO_ENABLED_MODEL_MESSAGE;
  const selectedId = $("agentModelSelect")?.value || "";
  if (!selectedId) return AGENT_NO_SELECTED_MODEL_MESSAGE;
  return "";
}

function agentModelConfigurationErrorMessage(error) {
  const message = String(error?.message || error || "");
  if (!message) return "";
  if (message.includes("Configure and enable an AI model in Settings first.")) {
    return AGENT_NO_ENABLED_MODEL_MESSAGE;
  }
  if (message.includes("The currently selected model is not available")) {
    return "The selected model is unavailable. Select another model or check its settings.";
  }
  if (message.includes("The selected model needs an API base URL and model name.")) {
    return "Add the API base URL in Settings to use this model.";
  }
  return "";
}

function showAgentModelGuidance(message) {
  if (!message) return false;
  setAgentComposerNotice(message, "error");
  setActionStatusOverride(message, "error");
  $("agentModelSelect")?.focus();
  return true;
}

function renderAgentEffortPreference() {
  const select = $("agentEffortSelect");
  if (!select) return;
  agentSelectedEffort = normalizeAgentEffort(agentSelectedEffort);
  if (select.value !== agentSelectedEffort) select.value = agentSelectedEffort;
}

function renderAgentAcceptanceModePreference() {
  const select = $("agentAcceptanceModeSelect");
  if (!select) return;
  agentAcceptanceMode = normalizeAgentAcceptanceMode(agentAcceptanceMode);
  if (select.value !== agentAcceptanceMode) select.value = agentAcceptanceMode;
  const chip = select.closest(".agent-composer-acceptance");
  if (chip) chip.dataset.acceptanceMode = agentAcceptanceMode;
  // Relabel the auto-accept option per task type so the chip reads naturally for the
  // current flow (AutoCall/Analysis/Modelling) instead of always "Automatic review".
  const autoOption = select.querySelector('option[value="auto_accept"]');
  if (autoOption) autoOption.textContent = autoAcceptLabel(selectedTask?.task_type);
}

function autoAcceptLabel(taskType) {
  switch (taskType) {
    case "data_join":
      return "AutoCall";
    case "feature_analysis":
      return "Autoanalyze";
    case "modeling":
      return "Automatic model development";
    case "portfolio":
      return "Automatic portfolio analysis";
    default:
      return "Automatic review";
  }
}

function requestAgentConversationScrollToLatest() {
  if (!selectedTaskIsAgentMode()) return;
  if (workbenchTask()?.task_type === "validation" && activeValidationView !== "conversation") return;
  if (suppressAgentAutoScrollTaskId === selectedTaskId) return;
  if (!agentAutoScrollFollows) return;
  const scrollContent = $("resultScrollContent");
  if (!scrollContent) return;
  if (agentAutoScrollFrame !== null) {
    window.cancelAnimationFrame(agentAutoScrollFrame);
  }
  agentAutoScrollFrame = window.requestAnimationFrame(() => {
    agentAutoScrollFrame = null;
    scrollContent.scrollTo({ top: scrollContent.scrollHeight, behavior: "auto" });
    if (typeof scheduleTaskHeroGlassState === "function") scheduleTaskHeroGlassState();
  });
}

const reportDraftState = createReportDraftState({ api, onChange: updateReportDraftSaveStatus });
const validationViewState = new Map();
let activeValidationViewTaskId = "";
let activeValidationView = "conversation";
let renderedReportDraftSignature = "";

function updateReportDraftSaveStatus(taskId, entry) {
  if (taskId !== workbenchTaskId()) return;
  const panel = $("reportDraftWorkspace");
  const status = panel?.querySelector("[data-report-draft-save-status]");
  if (status) status.textContent = entry.confirming ? "Confirming report. Editing is temporarily disabled." : entry.status;
  const feedback = panel?.querySelector("[data-report-draft-feedback]");
  if (feedback) feedback.innerHTML = reportDraftFeedbackHtml(entry);
  const confirm = panel?.querySelector("[data-report-draft-confirm]");
  if (confirm) confirm.disabled = Boolean(entry.conflict || entry.pending || entry.confirming);
  panel?.querySelectorAll("[data-report-draft-key]").forEach((field) => { field.readOnly = Boolean(entry.confirming); });
  panel?.querySelectorAll("[data-report-draft-save], [data-report-draft-revise], [data-report-draft-resolve]").forEach((button) => { button.disabled = Boolean(entry.confirming); });
}

function rememberValidationView() {
  if (!activeValidationViewTaskId) return;
  const state = validationViewState.get(activeValidationViewTaskId) || { view: activeValidationView, scroll: {} };
  const scroller = activeValidationView === "report" ? $("reportDraftWorkspace") : $("resultScrollContent");
  state.view = activeValidationView;
  state.scroll[activeValidationView] = scroller?.scrollTop || 0;
  validationViewState.set(activeValidationViewTaskId, state);
}

function selectValidationView(view, { remember = true } = {}) {
  if (remember) rememberValidationView();
  activeValidationView = view;
  const workspace = $("resultWorkspace");
  workspace.dataset.validationView = view;
  $("reportDraftWorkspace").hidden = view !== "report";
  $("resultScrollContent").hidden = view === "report";
  $("validationWorkspaceNav")?.querySelectorAll("[data-validation-view]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.validationView === view));
  });
  const state = validationViewState.get(activeValidationViewTaskId) || { scroll: {} };
  state.view = view;
  validationViewState.set(activeValidationViewTaskId, state);
  const scroller = view === "report" ? $("reportDraftWorkspace") : $("resultScrollContent");
  if (scroller) scroller.scrollTop = state.scroll[view] || 0;
}

function renderReportDraftWorkspace({ force = false } = {}) {
  const enabled = workbenchTask()?.task_type === "validation" && selectedTaskIsAgentMode();
  const nav = $("validationWorkspaceNav");
  if (!nav) return;
  nav.hidden = !enabled;
  if (!enabled) {
    activeValidationViewTaskId = "";
    $("reportDraftWorkspace").hidden = true;
    $("resultScrollContent").hidden = false;
    delete $("resultWorkspace").dataset.validationView;
    return;
  }
  const taskId = workbenchTaskId();
  const taskMessages = agentMessages.filter((item) => !item.task_id || item.task_id === taskId);
  const pendingId = latestPendingReportDraftMessageId(taskMessages);
  const message = [...taskMessages].reverse().find((item) => item.stage === "word_conclusion_draft" && hasReportDraftValues(item.metadata?.draft_values));
  const cached = reportDraftState.get(taskId);
  const pending = Boolean(message && message.id === pendingId);
  const latestReportEvent = [...taskMessages].reverse().find((item) =>
    ["word_conclusion_draft", "word_conclusion_confirmed"].includes(item.stage));
  // Another window may confirm a draft while this window still has edits.
  // Keep those edits reachable, with confirmation disabled, until copied or redrafted.
  const retained = !pending && cached?.dirty;
  const editable = pending || retained;
  const entry = pending ? reportDraftState.receive(taskId, message) : retained ? cached : null;
  // Evidence renders before messages load during a model switch. Missing messages
  // are a loading state; only an explicit confirmation can retire local edits.
  if (retained && latestReportEvent?.stage === "word_conclusion_confirmed") {
    entry.conflict = { unavailable: true };
    entry.status = "This draft was confirmed or withdrawn. Your unsaved edits are still shown.";
  }
  const values = entry?.values || message?.metadata?.draft_values || {};
  const signature = JSON.stringify([taskId, message?.id, editable, entry?.messageId, entry?.revision]);
  if (force || signature !== renderedReportDraftSignature) {
    const title = workbenchTask()?.model_name || "Current Model";
    $("reportDraftWorkspace").innerHTML = `<div class="report-workspace-title"><span>Current Model</span><h2>${escapeHtml(title)}</h2></div>` + (message
      ? reportDraftTableHtml(values, { editable, taskId, state: entry, revision: entry?.revision ?? message.metadata.report_revision, messageId: entry?.messageId || message.id })
      : '<div class="report-workspace-empty"><h3>Report not ready</h3><p>The report draft will appear here when it is ready.</p><button type="button" class="button compact" data-validation-view="conversation">Back to conversation</button></div>');
    renderedReportDraftSignature = signature;
  }
  if (activeValidationViewTaskId !== taskId) {
    activeValidationViewTaskId = taskId;
    selectValidationView(validationViewState.get(taskId)?.view || activeValidationView, { remember: false });
  }
  if (entry) updateReportDraftSaveStatus(taskId, entry);
  if (entry && !entry.dirty && !entry.pending) {
    $("reportDraftWorkspace").querySelectorAll("[data-report-draft-key]").forEach((field) => {
      const value = String(entry.values[field.dataset.reportDraftKey] || "");
      if (field.value !== value) field.value = value;
    });
  }
}

function renderAgentConversation() {
  renderReportDraftWorkspace();
  const panel = $("agentConversationPanel");
  const composer = $("agentComposer");
  const workspace = $("resultWorkspace");
  if (!panel) return;
  strategyCandidateLabController.renderAvailability();
  const isAgent = selectedTaskIsAgentMode();
  const showManualRiskIntake = selectedTaskNeedsManualRiskIntake();
  // Driver tasks (data_join / feature / modeling) show the same conversation +
  // controls in BOTH modes. Manual = the user operates the controls (no free-text
  // composer, no LLM); agent = an LLM operates them + free-text composer.
  const showConversation = isAgent || taskUsesPlanRail(selectedTask);
  panel.classList.toggle("hidden", !showConversation);
  panel.setAttribute("aria-hidden", showConversation ? "false" : "true");
  composer?.classList.toggle("hidden", !(isAgent || showManualRiskIntake));
  composer?.classList.toggle("manual-risk-intake", showManualRiskIntake);
  composer?.setAttribute("aria-hidden", isAgent || showManualRiskIntake ? "false" : "true");
  workspace?.classList.toggle("agent-composer-active", isAgent || showManualRiskIntake);
  const composerInput = $("agentComposerInput");
  if (composerInput) {
    composerInput.placeholder = showManualRiskIntake
      ? "Describe the analysis and input data"
      : "Describe a task or ask a question";
  }
  syncRiskMaterialUploadControl();
  renderAgentAcceptanceModePreference();
  renderAgentModelOptions();
  renderAgentEffortPreference();
  requestAnimationFrame(syncAgentComposerClearance);
  panel.classList.remove("driver-analysis-mode");
  panel.setAttribute("aria-label", "Agent conversation");
  // Manual mode for a driver task is a TOOL, not a conversation: render the step
  // outputs as analysis panels (no speaker labels / chat bubbles) and put the gate
  // confirm controls in the step rail — exactly like Model validationmanual mode. Only agent
  // mode is a genuine LLM conversation; keeping manual mode conversation-free is what
  // proves the agent-mode dialogue isn't pre-written.
  if (showConversation && !isAgent && taskUsesPlanRail(selectedTask)) {
    renderDriverManualAnalysis(agentMessages);
    planRailController.resetFetchThrottle(selectedTaskId);
    renderWorkflowStepper({ force: true });
    return;
  }
  // Any render that is NOT the driver-manual path leaves #agentMessages in a
  // different state (agent timeline buckets, or emptied). Drop the manual-analysis
  // cache so a later switch back into a manual driver task rebuilds it even if the
  // messages are byte-identical to the last manual render.
  lastDriverManualAnalysisSignature = null;
  if (!showConversation) {
    agentMessages = [];
    lastAgentRenderSignature = null;
    lastAgentStructuralSignature = null;
    resetAgentTypingState();
    clearAgentStageMessages();
    restoreResultScrollDefaultOrder();
    return;
  }
  // Polling re-renders the whole app every second. Only rebuild the transcript
  // DOM when the messages actually changed, so the entry animation does not
  // re-fire each tick and in-progress draft edits are never wiped.
  const visibleStages = agentTimelineVisibleStages();
  const reportMessages = agentReportMessagesForDisplay(agentMessages);
  const displayedMessages = hideSupersededTuningThinking(
    taskUsesPlanRail(selectedTask)
      ? filterRecoveredWorkflowFailures(reportMessages, driverManualMessageStepStatus)
      : reportMessages,
  );
  const driverPlanSignature = taskUsesPlanRail(selectedTask)
    ? {
      currentPlanId: planRailController.planId(selectedTaskId),
      stepStatuses: agentMessages.map((message) => [
        String(message?.id || ""),
        String(driverManualMessageStepStatus(message)),
        driverGateMessageInteractionState(message),
      ]),
    }
    : null;
  const structuralSignature = agentStructuralSignature(displayedMessages, visibleStages);
  const signature = JSON.stringify({
    messages: agentMessages,
    visibleStages,
    driverPlanSignature,
  });
  if (signature === lastAgentRenderSignature) return;
  if (
    lastAgentStructuralSignature !== null
    && structuralSignature === lastAgentStructuralSignature
    && updateAgentMessageContentsInPlace(displayedMessages)
  ) {
    // Fast path: structural layout unchanged (typewriter tick / streaming
    // delta). We only patched the content of the affected messages, so the
    // metric-section bars and other animated descendants are not moved or
    // re-rendered, which avoids the flicker observed during agent streaming.
    lastAgentRenderSignature = signature;
    requestAgentConversationScrollToLatest();
    return;
  }
  lastAgentRenderSignature = signature;
  lastAgentStructuralSignature = structuralSignature;
  // Snapshot the live preview HTML for any new rerun trigger BEFORE the
  // upcoming new run overwrites #metricPreview / #scanSummary / etc. This
  // keeps every previous run's chart visible at its chronological position.
  freezeAgentSectionSnapshotsForReruns();
  clearAgentStageMessages();
  renderAgentTimeline(displayedMessages);
  attachCalibrationInteractions($("agentMessages"));
  requestAgentConversationScrollToLatest();
  // The conversation just changed (a driver turn likely created/advanced the
  // plan). Plan-rail tasks have no validation poll tick to refresh the right
  // rail, so force a fresh plan fetch + re-render here (only on real changes,
  // since this is the post-signature full-rebuild path).
  if (taskUsesPlanRail(selectedTask)) {
    planRailController.resetFetchThrottle(selectedTaskId);
    renderWorkflowStepper({ force: true });
  }
}

function agentStructuralSignature(messages = [], visibleStages = []) {
  // Anything that changes message COUNT, ORDER, stage assignment, role,
  // streaming/thinking state, or label visibility forces a full timeline
  // rebuild. Pure content edits (typewriter tick) leave this signature
  // unchanged and take the fast path.
  // UX-2: a gate widget's interactive/read-only state (only the latest gate
  // is interactive) must also be part of this signature — otherwise a driver
  // turn that resolves the pending gate and opens a new one would leave the
  // OLD gate's widget stuck rendered as interactive (and the new one stuck
  // read-only) under the fast path, which only patches .agent-message-content
  // text and never touches widget markup.
  const latestGateId = (() => {
    for (let index = messages.length - 1; index >= 0; index--) {
      const message = messages[index];
      if (message?.role !== "assistant") continue;
      const meta = message?.metadata || {};
      if (meta.kind === "gate" || meta.join_c1) return String(message.id || "");
      return "";
    }
    return "";
  })();
  const latestPendingDraftId = latestPendingReportDraftMessageId(messages);
  let previousAssistantLabel = "";
  const skeleton = messages.map((message) => {
    const role = message?.role === "user" ? "user" : "assistant";
    const label = role === "user" ? "" : agentStageLabel(message?.stage);
    const hideMeta = Boolean(label && label === previousAssistantLabel);
    previousAssistantLabel = label || previousAssistantLabel;
    const metadata = message?.metadata || {};
    const hasWorkflowPresentation = role === "assistant" && (
      hasWorkflowErrorDiagnostic(metadata)
      || (Array.isArray(metadata.ingest_notices) && metadata.ingest_notices.length > 0)
    );
    return {
      id: message?.id || "",
      role,
      stage: message?.stage || "",
      label,
      hideMeta,
      streaming: agentMessageIsStreaming(message),
      thinking: agentMessageIsThinking(message),
      // Optimistic placeholders and chat metadata flags can change the bucket
      // structure (e.g. report confirmation), so include them.
      flags: {
        optimistic: Boolean(metadata.optimistic),
        awaiting_confirmation: Boolean(metadata.awaiting_confirmation),
        awaiting_next_stage: metadata.awaiting_next_stage || "",
        intent: metadata.intent || "",
        tool_call_name: metadata.tool_call?.name || "",
        // Live tuning messages commonly keep one stable message id while only
        // metadata.progress changes. The in-place fast path patches prose only,
        // so progress must participate in the structural key to rebuild the
        // reusable card/rail readout on every real progress advance.
        tool_progress: metadata.kind === "tool_progress"
          ? {
            status: metadata.status || "",
            streaming: Boolean(metadata.streaming),
            progress: metadata.progress || metadata,
          }
          : null,
        // Structured recovery/error cards must be rebuilt as a unit. The
        // streaming fast path only patches .agent-message-content with plain
        // Markdown, so include their content + metadata in the structural key
        // to prevent it from replacing a card with the legacy text body.
        workflow_presentation: hasWorkflowPresentation
          ? {
            content: message?.content || "",
            error_diagnostic: metadata.error_diagnostic || null,
            ingest_notices: metadata.ingest_notices || [],
          }
          : null,
        is_latest_gate: Boolean(latestGateId) && String(message?.id || "") === latestGateId,
        gate_actionable: (metadata.kind === "gate" || metadata.join_c1)
          ? driverGateMessageIsActionable(message)
          : false,
        report_draft: message?.stage === "word_conclusion_draft"
          ? {
            keys: hasReportDraftValues(metadata.draft_values)
              ? Object.keys(metadata.draft_values).sort().join(",")
              : "",
            editable: Boolean(latestPendingDraftId)
              && String(message?.id || "") === latestPendingDraftId,
            revision: metadata.report_revision ?? "",
          }
          : null,
        memory_references: Array.isArray(metadata.memory_references)
          ? metadata.memory_references.map((reference) => [
            reference.id || "",
            reference.memory_type || "",
            reference.source_task_id || "",
            reference.confidence ?? "",
            reference.use_reason || "",
          ])
          : [],
      },
    };
  });
  return JSON.stringify({ skeleton, visibleStages });
}

function updateAgentMessageContentsInPlace(messages = []) {
  return updateAgentMessageContentsInPlaceDom(messages, {
    getElementById: $,
    isStreaming: agentMessageIsStreaming,
    isThinking: agentMessageIsThinking,
    thinkingHtml: agentThinkingHtml,
    visibleContent: agentVisibleContent,
    formatMessageContent: formatAgentMessageContent,
    memoryReferencesHtml: agentMemoryReferencesHtml,
  });
}

function agentFrozenStageConfig(stage) {
  if (stage === "scan") {
    return {
      sectionId: "scanSection",
      contentId: "scanSummary",
      headingHtml: "<h3>Input files</h3>",
      label: "Input files (previous run)",
    };
  }
  if (stage === "reproducibility") {
    const pmmlScoring = usesPmmlScoringWorkflow();
    return {
      sectionId: "notebookSection",
      contentId: "reproducibilitySummary",
      headingHtml: pmmlScoring ? "<h3>PMML scoring</h3>" : "<h3>Score comparison</h3>",
      label: pmmlScoring ? "PMML scoring (previous run)" : "Score comparison (previous run)",
    };
  }
  if (stage === "metrics") {
    return {
      sectionId: "metricSection",
      contentId: "metricPreview",
      headingHtml: "<h3>Metrics</h3>",
      label: "Metrics (previous run)",
    };
  }
  return null;
}

function freezeAgentSectionSnapshotsForReruns() {
  // Capture the live preview HTML for any rerun message we have not yet
  // frozen. Must run BEFORE the new run's data overwrites the live section,
  // so we call it on every render pass — captures are idempotent per
  // triggerMessageId.
  if (!selectedTaskId) return;
  const stored = taskFrozenSectionSnapshots.get(selectedTaskId) || [];
  const frozenIds = new Set(stored.map((entry) => entry.triggerMessageId));
  // Optimistic rerun ids get replaced by server ids on the next poll. Track
  // fingerprints so we do not double-freeze the same rerun once the real id
  // arrives.
  const frozenFingerprints = new Set(
    stored.map((entry) => entry.triggerFingerprint).filter(Boolean),
  );
  let updated = false;
  for (const message of agentMessages) {
    const fingerprint = agentRerunMessageFingerprint(message);
    if (!fingerprint) continue;
    const stage = message?.metadata?.target_stage;
    const config = agentFrozenStageConfig(stage);
    if (!config) continue;
    const messageId = message?.id ? String(message.id) : "";
    if (!messageId) continue;
    if (frozenIds.has(messageId)) continue;
    if (frozenFingerprints.has(fingerprint)) continue;
    const contentNode = $(config.contentId);
    if (!contentNode) continue;
    if (contentNode.classList.contains("empty")) continue;
    const html = String(contentNode.innerHTML || "").trim();
    if (!html) continue;
    stored.push({
      triggerMessageId: messageId,
      triggerFingerprint: fingerprint,
      stage,
      sectionId: config.sectionId,
      headingHtml: config.headingHtml,
      label: config.label,
      contentClassName: contentNode.className || "",
      contentHtml: contentNode.innerHTML,
    });
    frozenIds.add(messageId);
    frozenFingerprints.add(fingerprint);
    updated = true;
  }
  if (updated) taskFrozenSectionSnapshots.set(selectedTaskId, stored);
}

function stripIdsFromHtml(html) {
  // Sanitize a frozen HTML fragment before re-inserting it:
  //  - remove id attributes so we never produce duplicate ids (e.g. two
  //    #metricPreview) that make getElementById/querySelector resolve to a stale
  //    frozen element;
  //  - as defense-in-depth, drop <script> elements and inline on* event handlers
  //    so a snapshot can never reintroduce active content (the live data source is
  //    already escaped, but frozen snapshots must stay inert).
  const template = document.createElement("template");
  template.innerHTML = String(html || "");
  template.content.querySelectorAll("script").forEach((el) => el.remove());
  template.content.querySelectorAll("*").forEach((el) => {
    el.removeAttribute("id");
    for (const attr of [...el.attributes]) {
      if (/^on/i.test(attr.name)) el.removeAttribute(attr.name);
    }
  });
  return template.innerHTML;
}

function createAgentFrozenSnapshotElement(snapshot) {
  const wrap = document.createElement("section");
  wrap.className = "progress-panel agent-frozen-snapshot";
  wrap.dataset.agentFrozenSnapshot = "true";
  wrap.dataset.frozenStage = snapshot.stage || "";
  wrap.dataset.frozenTrigger = snapshot.triggerMessageId || "";
  // Strip any id attributes from the snapshot HTML so we never end up with
  // duplicate ids (e.g. multiple #metricPreview) in the document.
  const innerWrapClass = String(snapshot.contentClassName || "").trim();
  wrap.innerHTML = [
    `<div class="agent-frozen-snapshot-label">${escapeHtml(snapshot.label || "History")}</div>`,
    snapshot.headingHtml || "",
    `<div class="${escapeHtml(innerWrapClass)}" data-frozen-snapshot-content="true">${stripIdsFromHtml(snapshot.contentHtml)}</div>`,
  ].join("");
  return wrap;
}

function agentPersistentTimelineElementIds() {
  return [
    "batchOverviewPanel",
    "scanSection",
    "notebookSection",
    "metricSection",
    "reportSection",
    "agentConversationPanel",
    "planRetryPanel",
    "planDriverActions",
  ];
}

function restoreResultScrollDefaultOrder() {
  restoreResultScrollDefaultOrderDom({
    getElementById: $,
    persistentElementIds: agentPersistentTimelineElementIds(),
  });
}

function appendOptimisticAgentUserMessage(content, modelId = "") {
  const metadata = { optimistic: true };
  if (modelId) metadata.model_id = modelId;
  if (agentMessageIsAdvanceIntent({ role: "user", stage: "chat", content, metadata })) {
    metadata.intent = "advance";
  }
  const message = {
    id: `optimistic-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    role: "user",
    stage: "chat",
    content,
    metadata,
  };
  agentMessages = [...agentMessages, message];
  lastAgentRenderSignature = null;
  renderAgentConversation();
  return message;
}

function appendOptimisticAgentThinkingMessage(modelId = "") {
  const metadata = { optimistic: true, streaming: true };
  if (modelId) metadata.model_id = modelId;
  const message = {
    id: `optimistic-thinking-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    role: "assistant",
    stage: "chat",
    content: "",
    metadata,
  };
  agentMessages = [...agentMessages, message];
  lastAgentRenderSignature = null;
  renderAgentConversation();
  return message;
}

function removeOptimisticAgentMessage(messageId) {
  if (!messageId) return;
  agentMessages = agentMessages.filter((message) => message.id !== messageId);
  lastAgentRenderSignature = null;
  renderAgentConversation();
}

function clearAgentStageMessages() {
  const stageMessageIds = [
    "agentScanLeadMessages",
    "agentScanBeforeMessages",
    "agentScanMessages",
    "agentReproducibilityLeadMessages",
    "agentReproducibilityMessages",
    "agentMetricLeadMessages",
    "agentMetricMessages",
    "agentReportLeadMessages",
    "agentReportMessages",
  ];
  for (const targetId of stageMessageIds) {
    const target = $(targetId);
    if (!target) continue;
    target.innerHTML = "";
    target.classList.add("hidden");
  }
  updateAgentReportSectionVisibility();
}

function removeAgentTimelineBuckets() {
  removeAgentTimelineBucketsDom(document);
}

function agentTimelineVisibleStages() {
  return agentTimelineStageDefinitions()
    .filter(({ sectionId }) => {
      const section = $(sectionId);
      return section && !section.classList.contains("hidden") && section.getAttribute("aria-hidden") !== "true";
    })
    .map(({ stage }) => stage);
}

function renderAgentTimeline(messages = []) {
  renderAgentTimelineDom(messages, {
    getElementById: $,
    visibleStages: agentTimelineVisibleStages(),
    selectedTaskId,
    taskFrozenSectionSnapshots,
    agentMessages,
    createFrozenSnapshotElement: createAgentFrozenSnapshotElement,
    persistentElementIds: agentPersistentTimelineElementIds(),
    agentStageLabel,
    // Agent mode keeps natural-language chat, while agentMessageHtml promotes
    // only the latest typed gate to an interactive control. Historical gates
    // remain conversation-only evidence so stale actions cannot be replayed.
    agentMessageHtml: (message, labelStage, options = {}) => agentMessageHtml(
      message,
      labelStage,
      { ...options, conversationOnly: true },
    ),
  });
}

function stripChatInstructions(content) {
  return stripChatInstructionsController(content);
}

function driverManualMessageStepStatus(message) {
  const metadata = message?.metadata || {};
  const currentPlanId = planRailController.planId(selectedTaskId);
  const messagePlanId = String(
    metadata.plan_id
    || metadata.failure_envelope?.plan_id
    || "",
  );
  if (currentPlanId && messagePlanId && messagePlanId !== currentPlanId) {
    return "historical";
  }
  const stepId = metadata.step_id
    || metadata.failure_envelope?.failed_step_id
    || "";
  return planRailController.planStep(
    { ...metadata, step_id: stepId },
    selectedTaskId,
  )?.status || "";
}

function driverGateMessageInteractionState(message) {
  const metadata = message?.metadata || {};
  const taskId = selectedTaskId || "";
  const planId = String(metadata.plan_id || "");
  const stepId = String(metadata.step_id || "");
  const localBusyAction = String(taskBusyActions.get(taskId) || "");
  const localBusy = ["driver_execute", "agent"].includes(localBusyAction);
  const currentTask = findTaskInCache(taskId) || selectedTask;
  const serverBusy = Boolean(currentTask?.active_job_kind);

  // C1 material-role assignment can be opened before a plan exists. It has no
  // CAS binding yet, but it must still respect task-level execution ownership.
  if (!planId || !stepId) {
    const prePlanC1 = Boolean(metadata.join_c1) && !planId && !stepId;
    return {
      actionable: prePlanC1 && !localBusy && !serverBusy,
      localBusy,
      serverBusy,
      pendingClaim: "",
      stepStatus: "",
    };
  }

  const step = planRailController.planStep(metadata, taskId);
  const stepStatus = String(step?.status || driverManualMessageStepStatus(message));
  const messageSnapshot = metadata.confirmation_snapshot || {};
  const snapshot = step?.confirmation_snapshot || {};
  const snapshotCurrent = confirmationSnapshotsEqual(messageSnapshot, snapshot, {
    requireStep: true,
  });
  const gate = {
    taskId,
    planId,
    stepId,
    stepStatus,
    snapshot,
    localBusy,
    serverBusy,
  };
  return {
    actionable: snapshotCurrent && driverGateActionable(gate),
    localBusy,
    serverBusy,
    pendingClaim: driverGatePendingClaimSignature(gate),
    stepStatus,
  };
}

function driverGateMessageIsActionable(message) {
  return driverGateMessageInteractionState(message).actionable;
}

function driverManualAnalysisHtml(messages) {
  return driverManualAnalysisHtmlController(messages, {
    renderAgentMarkdown,
    renderC1Form: agentMessageC1FormHtml,
    renderDedupPicker: agentMessageDedupPickerHtml,
    renderJoinKeyPicker: agentMessageJoinKeyPickerHtml,
    renderModelingSetup: agentMessageModelingSetupHtml,
    renderScreenTable: agentMessageScreenTableHtml,
    renderTables: agentMessageTablesHtml,
    renderModelDelivery: agentMessageModelDeliveryHtml,
    renderResultDataset: agentMessageResultDatasetHtml,
    renderReportDownload: agentMessageReportDownloadHtml,
    renderAdoptionGate: agentMessageAdoptionGateHtml,
    renderFeatureBinning: agentMessageFeatureBinningHtml,
    renderSpecialValues: agentMessageSpecialValuesHtml,
    renderStrategyClarification: agentMessageStrategyClarificationHtml,
    // The plain-gate confirm control now lives in the middle analysis section
    // (not the rail). renderDriverGateButton already returns "" for gates that
    // carry a structured widget, so only genuinely plain gates get this button —
    // reusing the same document-level data-driver-confirm handler.
    renderGateConfirm: agentMessageGateButtonHtml,
    // Retry history remains in agentMessages for auditability. Resolve each
    // message's step against the current plan so recovered failures cannot steal
    // the interactive slot from the newly-opened gate.
    stepStatus: driverManualMessageStepStatus,
    isGateActionable: driverGateMessageIsActionable,
  });
}

function latestInteractiveScreenMessageId(messages = []) {
  return latestInteractiveScreenMessageIdController(messages);
}

function renderDriverManualAnalysis(messages) {
  const panel = $("agentConversationPanel");
  const container = $("agentMessages");
  if (!panel || !container) return;
  // Gate interactivity also depends on the current plan step state. A retry can
  // move failed -> done and open the next gate without appending a new message,
  // so include per-message step status in the cache key or the stale failure DOM
  // survives even after the plan cache advances.
  const currentPlanId = planRailController.planId(selectedTaskId);
  const planStepStatuses = (messages || []).map((message) => {
    const metadata = message?.metadata || {};
    return [
      String(message?.id || ""),
      String(metadata.step_id || metadata.failure_envelope?.failed_step_id || ""),
      String(driverManualMessageStepStatus(message)),
      driverGateMessageInteractionState(message),
    ];
  });
  const signature = JSON.stringify({
    messages: messages || [],
    currentPlanId,
    planStepStatuses,
  });
  if (signature === lastDriverManualAnalysisSignature) return;
  removeAgentTimelineBuckets();
  resetAgentTypingState();
  panel.classList.remove("hidden");
  panel.classList.add("driver-analysis-mode");
  panel.setAttribute("aria-hidden", "false");
  panel.setAttribute("aria-label", "Analysis");
  container.innerHTML = driverManualAnalysisHtml(messages);
  lastDriverManualAnalysisSignature = signature;
  attachCalibrationInteractions(container);
  // Keep the (hidden-for-driver) validation sections ordered after the analysis
  // panel so a later switch to a validation task restores cleanly.
  const scrollContent = $("resultScrollContent");
  if (scrollContent) {
    scrollContent.appendChild(panel);
    for (const elementId of agentPersistentTimelineElementIds()) {
      if (elementId === "agentConversationPanel") continue;
      const element = $(elementId);
      if (element) scrollContent.appendChild(element);
    }
  }
}

function resetAgentTypingState() {
  agentTypingState.clear();
  agentTypingCompleted.clear();
  if (agentTypingTimer !== null) {
    window.clearTimeout(agentTypingTimer);
    agentTypingTimer = null;
  }
}

function agentMessageIsStreaming(message) {
  const metadata = message?.metadata || {};
  return message?.role !== "user" && metadata.streaming === true;
}

function agentMessageIsThinking(message) {
  return agentMessageIsStreaming(message) && !String(message?.content || "").trim();
}

function agentVisibleContent(message) {
  const content = String(message?.content || "");
  const messageId = message?.id || "";
  if (!messageId) return content;
  let typing = agentTypingState.get(messageId);
  const streaming = agentMessageIsStreaming(message);
  if (!typing) {
    if (!streaming) return content;
    // A previously-completed id flipping back to streaming = server resumed
    // delta delivery. Seed visible with the bytes the user already saw so
    // the new tail appends, instead of visually clearing the message and
    // re-typing from byte 0. The startsWith guard below resets to empty if
    // the server actually rewrote the message instead of appending.
    const seedVisible = agentTypingCompleted.get(messageId) || "";
    typing = { visible: seedVisible, target: content };
    agentTypingState.set(messageId, typing);
  }
  if (!content.startsWith(typing.visible)) {
    typing.visible = "";
  }
  typing.target = content;
  if (typing.visible.length < typing.target.length) {
    scheduleAgentTyping();
    return typing.visible;
  }
  // Caught up. Only drop the state once the server has also signaled that
  // no further chunks are coming; remember the completion so a later resume
  // takes the seeded-visible path above instead of replaying from empty.
  if (!streaming) {
    agentTypingState.delete(messageId);
    agentTypingCompleted.set(messageId, content);
  }
  return content;
}

function scheduleAgentTyping() {
  if (agentTypingTimer !== null) return;
  agentTypingTimer = window.setTimeout(tickAgentTyping, AGENT_TYPEWRITER_INTERVAL_MS);
}

function tickAgentTyping() {
  agentTypingTimer = null;
  let changed = false;
  let pending = false;
  for (const typing of agentTypingState.values()) {
    if (typing.visible.length < typing.target.length) {
      const backlog = typing.target.length - typing.visible.length;
      const chunkSize = Math.max(
        AGENT_TYPEWRITER_CHARS_PER_TICK,
        Math.ceil(backlog / AGENT_TYPEWRITER_CATCHUP_TICKS),
      );
      const nextLength = typing.visible.length + chunkSize;
      typing.visible += typing.target.slice(typing.visible.length, nextLength);
      changed = true;
    }
    if (typing.visible.length < typing.target.length) {
      pending = true;
    }
  }
  if (changed) {
    lastAgentRenderSignature = null;
    renderAgentConversation();
  }
  if (pending) scheduleAgentTyping();
}

function agentMemoryReferencesHtml(references = []) {
  if (!Array.isArray(references) || references.length === 0) return "";
  const rows = references.map((reference) => {
    const memoryId = String(reference.id || reference.memory_id || "");
    const kind = reference.kind || "raw";
    const type = reference.memory_type || "memory";
    const sourceTask = reference.source_task_id || "";
    const confidence = reference.confidence !== undefined ? formatMemoryConfidence(reference.confidence) : "";
    const reason = reference.use_reason || reference.reason || "";
    const sourceCount = Array.isArray(reference.source_memory_ids) ? reference.source_memory_ids.length : 0;
    const meta = [
      kind === "distillation" ? "Combined summaries" : "",
      type,
      sourceTask ? `Source${sourceTask}` : "",
      sourceCount ? `Source memory${sourceCount}` : "",
      reference.support_count !== undefined ? `Support${reference.support_count}` : "",
      confidence ? `Confidence${confidence}` : "",
    ].filter(Boolean).map(escapeHtml).join(" · ");
    return [
      '<li class="agent-memory-reference">',
      '<span class="agent-memory-reference-main">',
      `<strong>${escapeHtml(memoryId || type)}</strong>`,
      meta ? `<small>${meta}</small>` : "",
      reason ? `<span>${escapeHtml(reason)}</span>` : "",
      "</span>",
      memoryId
        ? `<button class="agent-memory-reference-action" type="button" data-agent-memory-inline-inspect="${escapeHtml(memoryId)}" data-agent-memory-inline-kind="${escapeHtml(kind)}">View</button>`
        : "",
      "</li>",
    ].join("");
  }).join("");
  return [
    '<details class="agent-memory-references">',
    `<summary>Referenced memories${references.length}</summary>`,
    `<ul>${rows}</ul>`,
    "</details>",
  ].join("");
}

// VD-1: infer a rich-cell kind from a driver table's header text, mirroring the
// column_specs mechanism the validation metric preview uses (app.js:3502+),
// since generic driver tables (JOIN diagnostics / feature metrics / model
// compare) carry no explicit specs — only a {title, columns, rows} shape.
function driverColumnKindFromHeader(headerLabel) {
  const label = String(headerLabel || "").trim();
  if (!label) return "text";
  if (/^PSI$/i.test(label)) return "psi";
  if (/(Match Rate|Hit rate|Missing Rate|Percentage|Percentage|Bad rate|Bad debt rate|Approval rate|Pass rate)/i.test(label)) return "databar-percent";
  if (/^(KS|KS\(%\)|AUC|AUC\(%\)|IV|VIF|Importance|Related coefficient|Expected profits|Gain|Lift|lift)/i.test(label)) return "databar";
  if (/(Lines|Number of columns|Number of samples|Number of records|New|Number of features|Number|Number)/i.test(label)) return "integer";
  return "text";
}

function driverIntegerText(value) {
  const numeric = parseNumeric(value);
  return numeric === null ? String(value ?? "") : String(Math.trunc(numeric));
}

// Champion / winning candidate rows in comparison tables (Candidate model comparisonetc.) are
// marked by the backend appending " ★" to the first cell (marvis/agent/
// renderers.py:350); render that as a highlighted row instead of a literal star.
function driverTableCellHtml(value, rowIndex, columnIndex, headerLabel, kind, fractionsForColumn) {
  const raw = value ?? "";
  if (columnIndex === 0 && typeof value === "string" && /\s★$/.test(value)) {
    const label = String(raw).replace(/\s★$/, "");
    return {
      cls: "cell-text cell-champion",
      html: `<span class="champion-badge" data-tip="Best performer, current candidate">${escapeHtml(label)}</span>`,
    };
  }
  if (kind === "psi") {
    const numeric = parseNumeric(raw);
    const thresholds = [0.02, 0.10];
    const tier = psiTier(numeric, thresholds);
    const tip = psiTooltipText(numeric, thresholds);
    const stripMarker = numeric === null
      ? ""
      : `<i class="psi-marker" style="left:${Math.min(Math.abs(numeric) / 0.20, 1) * 100}%"></i>`;
    return {
      cls: "cell-psi",
      html: `<span class="psi-cell" data-tip="${escapeHtml(tip)}">`
        + `<span class="psi-value" data-tier="${tier}">${escapeHtml(String(raw))}</span>`
        + `<span class="psi-strip"><span></span><span></span><span></span>${stripMarker}</span>`
        + `</span>`,
    };
  }
  if (kind === "integer") {
    return { cls: "cell-number cell-integer", html: escapeHtml(driverIntegerText(raw)) };
  }
  if (kind === "databar" || kind === "databar-percent") {
    const fraction = fractionsForColumn.get(rowIndex);
    if (fraction !== undefined && parseNumeric(raw) !== null) {
      const tip = `${headerLabel} ${raw}`;
      return {
        cls: "cell-databar",
        // VD-9: driver-timeline tables render once and are never rebuilt in
        // place (see comment on agentMessageTablesHtml below), so the entry
        // animation is always safe to play here - no data-animation gate
        // needed, unlike the polled validation metric preview above.
        html: `<span class="databar" data-color="primary" data-tip="${escapeHtml(tip)}" style="--fraction:${fraction.toFixed(4)};--bar-index:${rowIndex}">`
          + `<span class="databar-fill"></span>`
          + `<span class="databar-label">${escapeHtml(String(raw))}</span>`
          + `</span>`,
      };
    }
    if (metricHeaderShouldRightAlign(headerLabel) && parseNumeric(raw) !== null) {
      return { cls: "cell-number", html: escapeHtml(String(raw)) };
    }
    return { cls: "cell-text", html: escapeHtml(String(raw)) };
  }
  if (metricHeaderShouldRightAlign(headerLabel) && parseNumeric(raw) !== null) {
    return { cls: "cell-number", html: escapeHtml(String(raw)) };
  }
  return { cls: "cell-text", html: escapeHtml(String(raw)) };
}

// Inline rich tables carried by the generic plan driver (data_join / future
// feature / modeling). Format is the driver's simple {title, columns, rows};
// validation metric tables use a different path (metadata.sections). VD-1:
// column kind is inferred from the header text (no column_specs on this path)
// and rendered with the same databar / PSI-band / tabular-nums primitives the
// validation metric preview already uses (render-metrics.js). Each driver
// message is appended whole, so this renders once on the full timeline
// rebuild — no streaming fast-path interaction.
function agentMessageTablesHtml(message) {
  const tables = message?.metadata?.tables;
  if (!Array.isArray(tables) || !tables.length) return "";
  const blocks = tables
    // Historical gates may have persisted the old flattened alternatives table.
    // It made two key candidates for one feature look like two additional joins;
    // the per-feature join-key picker is now the single authoritative surface.
    .filter((table) => !String(table?.title || "").startsWith("Recommended join keys"))
    .map((table, tableIndex) => {
      const columns = Array.isArray(table?.columns) ? table.columns : [];
      const rows = Array.isArray(table?.rows) ? table.rows.map((row) => (Array.isArray(row) ? row : [row])) : [];
      if (!columns.length && !rows.length) return "";
      const kinds = columns.map((col) => driverColumnKindFromHeader(col));
      const fractionsByColumn = new Map();
      kinds.forEach((kind, columnIndex) => {
        if (kind === "databar" || kind === "databar-percent") {
          fractionsByColumn.set(columnIndex, columnFractions(rows, columnIndex));
        }
      });
      const head = columns.length
        ? `<thead><tr>${columns.map((col) => `<th>${escapeHtml(String(col))}</th>`).join("")}</tr></thead>`
        : "";
      const body = `<tbody>${rows
        .map((cells, rowIndex) => {
          const tds = cells.map((cell, columnIndex) => {
            const rendered = driverTableCellHtml(
              cell,
              rowIndex,
              columnIndex,
              columns[columnIndex] ?? "",
              kinds[columnIndex] || "text",
              fractionsByColumn.get(columnIndex) || new Map(),
            );
            return `<td class="${rendered.cls}">${rendered.html}</td>`;
          });
          return `<tr>${tds.join("")}</tr>`;
        })
        .join("")}</tbody>`;
      const chartHtml = driverTableChartHtml(table?.chart);
      const title = String(table?.title || `Results${tableIndex + 1}`);
      return `<div class="agent-inline-table">${renderWorkflowDataWidget({
        title,
        chartHtml,
        tableHtml: `<table>${head}${body}</table>`,
        rowCount: rows.length,
        columnCount: columns.length,
        index: tableIndex,
      })}</div>`;
    })
    .join("");
  return blocks ? `<div class="agent-message-tables">${blocks}</div>` : "";
}

// VD-4: renders the calibration reliability curve / score-band bar+line chart
// above its table when the driver table carries a `chart` payload (see
// marvis/agent/renderers.py::_calibration_table / _score_band_table). The
// table itself is unchanged and stays visible below the chart — the chart is
// an enhancement, not a replacement. Numbers are read straight off payload
// coordinates (no frontend computation, INV-1). Missing/empty chart data
// renders nothing rather than an empty frame.
function driverTableChartHtml(chart) {
  if (!chart || typeof chart !== "object") return "";
  if (chart.kind === "calibration_curve") {
    if (!Array.isArray(chart.points) || chart.points.length === 0) return "";
    return `<div class="agent-inline-table-chart">${renderCalibrationCard(chart)}</div>`;
  }
  if (chart.kind === "score_band_bars") {
    if (!Array.isArray(chart.bands) || chart.bands.length === 0) return "";
    return `<div class="agent-inline-table-chart">${renderScoreBandCard(chart)}</div>`;
  }
  return "";
}

function agentMessageModelingSetupHtml(message, options = {}) {
  return renderModelingSetupPanel(message, options);
}

function agentMessageModelDeliveryHtml(message, options = {}) {
  return renderModelDeliveryPanel(message, options);
}

function agentMessageAdoptionGateHtml(message, options = {}) {
  return renderAdoptionGate(message, options);
}

function agentMessageFeatureBinningHtml(message, options = {}) {
  return renderFeatureBinningGate(message, options);
}

function agentMessageSpecialValuesHtml(message, options = {}) {
  return renderSpecialValueGate(message, options);
}

function agentMessageStrategyClarificationHtml(message, options = {}) {
  return renderStrategyClarification(message, options);
}

async function refreshDriverGateState(taskId) {
  if (!taskId) return;
  planRailController.resetFetchThrottle(taskId);
  try {
    const [, , plan] = await Promise.all([
      loadAgentMessages(taskId),
      refreshTasks(),
      planRailController.maybeFetchPlan(taskId),
    ]);
    if (!plan) throw new Error("Could not load the latest plan.");
  } finally {
    if (selectedTaskId === taskId) {
      renderAgentConversation();
      renderWorkflowStepper({ force: true });
    }
  }
}

function handleStrategyClarificationSubmit(event) {
  return handleStrategyClarificationSubmitController(
    event,
    strategyClarificationControllerContext(),
  );
}

function handleStrategyClarificationChange(event) {
  return handleStrategyClarificationChangeController(event);
}

function strategyClarificationControllerContext() {
  return {
    ...driverConfirmControllerContext(),
    refreshAgentMessages: refreshDriverGateState,
  };
}

async function submitAdoption(button) {
  return submitAdoptionController(button, driverConfirmControllerContext());
}

function handleAdoptionConfirmClick(event) {
  return handleAdoptionConfirmClickController(event, driverConfirmControllerContext());
}

function handleFeatureBinningClick(event) {
  return handleFeatureBinningClickController(event, driverConfirmControllerContext());
}

function handleSpecialValueClick(event) {
  return handleSpecialValueClickController(event, driverConfirmControllerContext());
}

async function submitModelingWeightAdjust(button) {
  return submitModelingWeightAdjustController(button, modelingSetupControllerContext());
}

function handleModelingWeightAdjustClick(event) {
  return handleModelingWeightAdjustClickController(event, modelingSetupControllerContext());
}

function agentAcceptanceControllerContext() {
  const capturedTaskId = selectedTaskId;
  return {
    getSelectedTaskId: () => selectedTaskId,
    api: typeof driverGateApi === "function" ? driverGateApi : api,
    agentAcceptanceModeValue,
    setActionStatus,
    setAgentMessages: (messages) => {
      if (selectedTaskId !== capturedTaskId) return;
      agentMessages = messages || agentMessages;
    },
    renderAgentConversation,
    // UX-1: let the v2 gate controllers show busy state + keep the agent-message
    // stream and plan rail live while their driver turn (now job-wrapped, REL-1)
    // runs, instead of freezing until the request finally resolves.
    pollAgentMessagesUntilSettled,
    refreshAgentMessages: typeof refreshDriverGateState === "function"
      ? refreshDriverGateState
      : async () => {},
    resetFetchThrottle: (taskId) => planRailController.resetFetchThrottle(taskId),
    renderWorkflowStepper,
    setDriverExecutionBusy: (active, taskId) => setBusy(
      active ? "driver_execute" : null,
      active ? "Running the next step..." : "",
      taskId,
    ),
  };
}

function modelingSetupControllerContext() {
  return agentAcceptanceControllerContext();
}
if (typeof document !== "undefined") {
  mountWorkflowWidgetInteractions(document);
  document.addEventListener("click", handleModelingSetupInteraction);
  document.addEventListener("input", handleModelingSetupInteraction);
  document.addEventListener("click", handleModelingWeightAdjustClick);
  document.addEventListener("click", handleAdoptionConfirmClick);
  document.addEventListener("click", handleFeatureBinningClick);
  document.addEventListener("click", handleSpecialValueClick);
  document.addEventListener("click", handleStrategyClarificationSubmit);
  document.addEventListener("change", handleStrategyClarificationChange);
}

function agentMessageC1FormHtml(message, options = {}) {
  return renderJoinC1Form(message, options);
}

async function submitC1Assignment(button) {
  return submitC1AssignmentController(button, joinGateControllerContext());
}

function handleC1ConfirmClick(event) {
  return handleC1ConfirmClickController(event, joinGateControllerContext());
}

function handleC1PreviewClick(event) {
  return handleC1PreviewClickController(event, joinGateControllerContext());
}

function handleC1RoleChange(event) {
  return handleC1RoleChangeController(event);
}

function joinGateControllerContext() {
  return agentAcceptanceControllerContext();
}
if (typeof document !== "undefined") {
  document.addEventListener("click", handleC1ConfirmClick);
  document.addEventListener("click", handleC1PreviewClick);
  document.addEventListener("change", handleC1RoleChange);
  document.addEventListener("mouseover", handleDatasetTablePointerOver);
  document.addEventListener("mouseout", handleDatasetTablePointerOut);
}

function agentMessageScreenTableHtml(message, options = {}) {
  return renderScreenGateTable(message, options);
}

async function submitScreenThresholdAdjust(button) {
  return submitScreenThresholdAdjustController(button, screenGateControllerContext());
}

async function submitScreenSelection(button) {
  return submitScreenSelectionController(button, screenGateControllerContext());
}

function handleScreenAdjustClick(event) {
  return handleScreenAdjustClickController(event, screenGateControllerContext());
}

function handleScreenConfirmClick(event) {
  return handleScreenConfirmClickController(event, screenGateControllerContext());
}

function screenGateControllerContext() {
  const capturedTaskId = selectedTaskId;
  return {
    getSelectedTaskId: () => selectedTaskId,
    // UX-4: the search/sort/chip/page/bulk handlers re-render a gate message's
    // table client-side (no backend round trip), so they need to look the
    // message back up by id from the live conversation state.
    getAgentMessages: () => agentMessages,
    api: typeof driverGateApi === "function" ? driverGateApi : api,
    agentAcceptanceModeValue,
    setActionStatus,
    setAgentMessages: (messages) => {
      if (selectedTaskId !== capturedTaskId) return;
      agentMessages = messages || agentMessages;
    },
    renderAgentConversation,
    // UX-1: let the v2 gate controllers show busy state + keep the agent-message
    // stream and plan rail live while their driver turn (now job-wrapped, REL-1)
    // runs, instead of freezing until the request finally resolves.
    pollAgentMessagesUntilSettled,
    refreshAgentMessages: typeof refreshDriverGateState === "function"
      ? refreshDriverGateState
      : async () => {},
    resetFetchThrottle: (taskId) => planRailController.resetFetchThrottle(taskId),
    renderWorkflowStepper,
    setDriverExecutionBusy: (active, taskId) => setBusy(
      active ? "driver_execute" : null,
      active ? "Running the next step..." : "",
      taskId,
    ),
  };
}
function handleScreenSearchInput(event) {
  return handleScreenSearchInputController(event, screenGateControllerContext());
}
function handleScreenSortClick(event) {
  return handleScreenSortClickController(event, screenGateControllerContext());
}
function handleScreenChipClick(event) {
  return handleScreenChipClickController(event, screenGateControllerContext());
}
function handleScreenPageClick(event) {
  return handleScreenPageClickController(event, screenGateControllerContext());
}
function handleScreenBulkClick(event) {
  return handleScreenBulkClickController(event, screenGateControllerContext());
}
function handleScreenAgentRecommendClick(event) {
  return handleScreenAgentRecommendClickController(event, screenGateControllerContext());
}
function handleScreenMetricFilterInput(event) {
  return handleScreenMetricFilterInputController(event, screenGateControllerContext());
}
function handleScreenPickChange(event) {
  return handleScreenPickChangeController(event, screenGateControllerContext());
}
if (typeof document !== "undefined") {
  document.addEventListener("click", handleScreenAdjustClick);
  document.addEventListener("click", handleScreenConfirmClick);
  document.addEventListener("click", handleScreenSortClick);
  document.addEventListener("click", handleScreenChipClick);
  document.addEventListener("click", handleScreenPageClick);
  document.addEventListener("click", handleScreenBulkClick);
  document.addEventListener("click", handleScreenAgentRecommendClick);
  document.addEventListener("input", handleScreenSearchInput);
  document.addEventListener("input", handleScreenMetricFilterInput);
  document.addEventListener("change", handleScreenPickChange);
}

function agentMessageDedupPickerHtml(message, options = {}) {
  return renderDedupPicker(message, options);
}

function agentMessageJoinKeyPickerHtml(message, options = {}) {
  return renderJoinKeyPicker(message, options);
}

async function submitJoinKeySelection(button) {
  return submitJoinKeySelectionController(button, joinGateControllerContext());
}

function handleJoinKeyConfirmClick(event) {
  return handleJoinKeyConfirmClickController(event, joinGateControllerContext());
}

async function submitDedupStrategies(button) {
  return submitDedupStrategiesController(button, joinGateControllerContext());
}

function handleDedupConfirmClick(event) {
  return handleDedupConfirmClickController(event, joinGateControllerContext());
}

async function submitDedupExclude(button) {
  return submitDedupExcludeController(button, joinGateControllerContext());
}

function handleDedupExcludeClick(event) {
  return handleDedupExcludeClickController(event, joinGateControllerContext());
}
if (typeof document !== "undefined") {
  document.addEventListener("click", handleJoinKeyConfirmClick);
  document.addEventListener("click", handleDedupConfirmClick);
  document.addEventListener("click", handleDedupExcludeClick);
}

function agentMessageGateButtonHtml(message) {
  // UX-10: resolve the gate step's own tool (the step it is confirming) so the
  // button copy can state the consequence (Confirm and execute the fusion/Confirm the selected feature/...).
  const step = planRailController.planStep(message?.metadata || {});
  return renderDriverGateButton(message, {
    gateStepTool: step?.tool_ref?.tool || "",
    interactive: driverGateMessageIsActionable(message),
  });
}

async function submitDriverConfirm(button) {
  return submitDriverConfirmController(button, driverConfirmControllerContext());
}

function handleDriverConfirmClick(event) {
  return handleDriverConfirmClickController(event, driverConfirmControllerContext());
}

function driverConfirmControllerContext() {
  const capturedTaskId = selectedTaskId;
  return {
    getSelectedTaskId: () => selectedTaskId,
    api: typeof driverGateApi === "function" ? driverGateApi : api,
    setActionStatus,
    setAgentMessages: (messages) => {
      if (selectedTaskId !== capturedTaskId) return;
      agentMessages = messages || agentMessages;
    },
    renderAgentConversation,
    // UX-1: let the v2 gate controllers show busy state + keep the agent-message
    // stream and plan rail live while their driver turn (now job-wrapped, REL-1)
    // runs, instead of freezing until the request finally resolves.
    pollAgentMessagesUntilSettled,
    refreshAgentMessages: typeof refreshDriverGateState === "function"
      ? refreshDriverGateState
      : async () => {},
    resetFetchThrottle: (taskId) => planRailController.resetFetchThrottle(taskId),
    renderWorkflowStepper,
    setDriverExecutionBusy: (active, taskId) => setBusy(
      active ? "driver_execute" : null,
      active ? "Running the next step..." : "",
      taskId,
    ),
  };
}
if (typeof document !== "undefined") {
  document.addEventListener("click", handleDriverConfirmClick);
  document.addEventListener("click", handleReportDraftConfirmClick);
}

function handleReportDraftConfirmClick(event) {
  const button = event.target?.closest?.("[data-report-draft-confirm]");
  if (!button || button.disabled) return;
  event.preventDefault();
  void submitVisibleReportDraft(button);
}

if (typeof document !== "undefined") {
  document.addEventListener("input", (event) => {
    const field = event.target?.closest?.("[data-report-draft-key]");
    const table = field?.closest("[data-report-draft-table]");
    if (table) reportDraftState.edit(table.dataset.reportDraftTaskId, collectReportDraftValues(table));
  });
  document.addEventListener("click", (event) => {
    const view = event.target?.closest?.("[data-validation-view]");
    if (view) selectValidationView(view.dataset.validationView);
    const save = event.target?.closest?.("[data-report-draft-save]");
    if (save) void reportDraftState.save(workbenchTaskId()).catch(() => {});
    const resolution = event.target?.closest?.("[data-report-draft-resolve]");
    if (resolution) {
      reportDraftState.resolve(workbenchTaskId(), resolution.dataset.reportDraftResolve);
      renderReportDraftWorkspace({ force: true });
    }
    const revise = event.target?.closest?.("[data-report-draft-revise]");
    if (revise) {
      selectValidationView("conversation");
      const input = $("agentComposerInput");
      input.value = `Please revise the current model report based on current evidence.${revise.dataset.reportDraftRevise}]:`;
      input.focus();
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s"
      && workbenchTask()?.task_type === "validation" && selectedTaskIsAgentMode()
      && activeValidationView === "report") {
      event.preventDefault();
      void reportDraftState.save(workbenchTaskId()).catch(() => {});
    }
  });
  window.addEventListener("beforeunload", (event) => {
    if (reportDraftState.hasUnsaved()) { event.preventDefault(); event.returnValue = ""; }
  });
}

async function submitVisibleReportDraft(button) {
  const table = button.closest("[data-report-draft-table]");
  const taskId = table?.dataset.reportDraftTaskId;
  if (!table || !taskId || taskId !== workbenchTaskId() || pendingTaskContentLoadTaskId
    || reportDraftState.isConfirming(taskId)) return;
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = "Generating report...";
  reportDraftState.setConfirming([taskId], true);
  setBusy("report_confirm", "Generating report...", taskId);
  try {
    await reportDraftState.save(taskId);
    const draftPayload = reportDraftState.payload(taskId);
    if (!draftPayload) throw new Error("The current draft is not ready");
    const result = await api(`api/tasks/${encodeURIComponent(taskId)}/agent/report-draft/confirm`, {
      method: "POST",
      body: JSON.stringify(draftPayload),
    });
    reportDraftState.discard(taskId);
    if (taskId === workbenchTaskId() && Array.isArray(result?.messages)) agentMessages = result.messages;
    renderAgentConversation();
    await pollAgentMessagesUntilSettled(taskId, Promise.resolve());
    await refreshTasks();
    setActionStatus("Report findings confirmed. Generating Word and Excel files…", "busy");
  } catch (error) {
    button.disabled = false;
    button.textContent = originalLabel || "Confirm and generate reports";
    setActionStatus("Could not confirm the report.", "error", error?.message || "");
  } finally {
    reportDraftState.setConfirming([taskId], false);
    setBusy(null, "", taskId);
  }
}

async function confirmAllValidationBatchReportDrafts({ parentTaskId } = {}) {
  const parentId = String(parentTaskId || selectedTaskId || "").trim();
  if (!parentId) return;
  const overrides = {};
  let confirmationTaskIds = [];
  setBusy("report_confirm_all", "Generating all reports...", parentId);
  try {
    const detail = normalizeValidationBatchPayload(await api(`api/validation-batches/${encodeURIComponent(parentId)}`));
    const pendingIds = detail.items.filter((item) => item.pendingReportDraft && !["failed", "cancelled"].includes(item.status)).map((item) => item.childTaskId);
    if (pendingIds.some((id) => reportDraftState.isConfirming(id))) {
      throw new Error("A model report is being confirmed. Wait for it to finish.");
    }
    confirmationTaskIds = pendingIds;
    reportDraftState.setConfirming(confirmationTaskIds, true);
    await reportDraftState.flush(pendingIds);
    for (const id of pendingIds) {
      const saved = reportDraftState.payload(id);
      if (saved) overrides[id] = saved;
    }
    await api(`api/validation-batches/${encodeURIComponent(parentId)}/report-drafts/confirm-all`, {
      method: "POST",
      body: JSON.stringify({ overrides }),
    });
    pendingIds.forEach((id) => reportDraftState.discard(id));
    setActionStatus("All drafts confirmed. Generating Word, Excel, and summary files...", "busy");
    const currentChildId = workbenchTaskId();
    if (currentChildId) {
      await loadAgentMessages(currentChildId);
      await pollAgentMessagesUntilSettled(currentChildId, Promise.resolve());
    }
    await refreshTasks();
  } catch (error) {
    setActionStatus("Confirmation failed", "error", error?.message || "");
    throw error;
  } finally {
    reportDraftState.setConfirming(confirmationTaskIds, false);
    setBusy(null, "", parentId);
  }
}

function handleDriverReportDownloadClick(event) {
  const button = event.target?.closest?.("[data-driver-report-download]");
  if (!button || !selectedTaskId) return;
  event.preventDefault();
  window.location.href = `api/tasks/${encodeURIComponent(selectedTaskId)}/driver-report/download`;
}

function agentMessageResultDatasetHtml(message) {
  const result = message?.metadata?.result_dataset;
  const datasetId = String(result?.dataset_id || "").trim();
  if (!datasetId) return "";
  const persistedHref = String(result?.download_url || "");
  const expectedPrefix = selectedTaskId
    ? `/api/tasks/${encodeURIComponent(selectedTaskId)}/datasets/${encodeURIComponent(datasetId)}/download?`
    : "";
  const href = expectedPrefix
    && persistedHref.startsWith(expectedPrefix)
    && persistedHref.includes("plan_id=")
    && persistedHref.includes("step_id=")
    && persistedHref.includes("output_ref=")
    && persistedHref.includes("expected_content_hash=")
    ? safeSameOriginApiHref(persistedHref)
    : "";
  if (!href) return "";
  const title = String(result?.title || "Result dataset ready");
  const downloadLabel = String(result?.download_label || "Download result dataset");
  return [
    '<section class="result-dataset-download">',
    '<div class="result-dataset-download-copy">',
    `<strong>${escapeHtml(title)}</strong>`,
    `<span>Dataset${escapeHtml(datasetId)}</span>`,
    '</div>',
    `<a class="button compact primary" data-result-dataset-download href="${escapeHtml(href)}" download>${escapeHtml(downloadLabel)}</a>`,
    '</section>',
  ].join("");
}

function agentMessageReportDownloadHtml(message) {
  const multiple = Array.isArray(message?.metadata?.report_downloads)
    ? message.metadata.report_downloads
    : [];
  const fallback = message?.metadata?.report_download;
  const reports = (multiple.length ? multiple : [fallback])
    .map((report) => ({
      ...report,
      download_url: safeSameOriginApiHref(report?.download_url),
    }))
    .filter((report) => report.download_url);
  if (!reports.length) return "";
  const links = reports.map((report) => {
    const href = String(report.download_url || "").trim();
    const storedLabel = String(report.label || "Download analysis");
    const activeTaskType = typeof selectedTask === "undefined"
      ? ""
      : String(selectedTask?.task_type || "");
    // Historical Portfolio completion messages persisted before the typed
    // label existed. Keep those immutable messages, but render their legacy
    // modeling fallback with the task's actual report type.
    const label = activeTaskType === "portfolio"
      && storedLabel === "Download Model Development Report"
      && href.includes("driver-report/download")
      ? "Download the portfolio analysis report"
      : storedLabel;
    const detail = [report.recipe, report.experiment_id].filter(Boolean).join(" · ");
    return [
      '<div class="report-result-download-item">',
      detail ? `<span>${escapeHtml(detail)}</span>` : "",
      `<a class="button compact primary" data-agent-report-download href="${escapeHtml(href)}" download>${escapeHtml(label)}</a>`,
      '</div>',
    ].join("");
  }).join("");
  return [
    '<section class="result-dataset-download report-result-download">',
    '<div class="result-dataset-download-copy">',
    `<strong>${reports.length > 1 ? `Generated${reports.length} Analysis reports` : "Analysis reports ready"}</strong>`,
    '<span>The Excel report contains metrics, notes, and agent recommendations.</span>',
    '</div>',
    `<div class="report-result-download-list">${links}</div>`,
    '</section>',
  ].join("");
}
if (typeof document !== "undefined") {
  document.addEventListener("click", handleDriverReportDownloadClick);
}

function handleWorkflowRecoveryCommandClick(event) {
  const button = event.target?.closest?.("[data-workflow-recovery-command]");
  if (!button || !selectedTaskId) return;
  event.preventDefault();
  const command = String(button.dataset.workflowRecoveryCommand || "").trim();
  const input = $("agentComposerInput");
  if (!command || !input) return;
  input.value = command;
  autoGrowComposerInput();
  updateAgentSendDisabled();
  runAction(startAgentValidation, { actionId: "agent", busyText: "Restoring the current step..." });
}
if (typeof document !== "undefined") {
  document.addEventListener("click", handleWorkflowRecoveryCommandClick);
}

// Red flags are read from the backend's already-emitted "⚠️" markers for the
// compact task status.  Agent prose itself remains unboxed; structured widgets
// own their individual visual surfaces.
function driverGateRedFlags(message) {
  const flags = [];
  const content = String(message?.content || "");
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.startsWith("⚠️")) {
      flags.push(trimmed.replace(/^⚠️\s*/, "").replace(/\*\*/g, ""));
    }
  }
  const tables = Array.isArray(message?.metadata?.tables) ? message.metadata.tables : [];
  for (const table of tables) {
    const columns = Array.isArray(table?.columns) ? table.columns : [];
    const rows = Array.isArray(table?.rows) ? table.rows : [];
    rows.forEach((row) => {
      const cells = Array.isArray(row) ? row : [row];
      cells.forEach((cell, columnIndex) => {
        if (typeof cell !== "string" || !cell.includes("⚠️")) return;
        const label = columns[columnIndex] ?? "";
        const rowLabel = cells[0] ?? "";
        flags.push(`${escapeHtml(String(rowLabel))} · ${escapeHtml(String(label))}:${escapeHtml(cell.replace(/⚠️/g, "").trim())}`.replace(/^ · /, ""));
      });
    });
  }
  return flags;
}

// UX-2: agent-mode gate widgets reuse the exact renderers + widget/table
// placement manual mode uses (driverGateBodyHtmlController), instead of a
// separate agent-only render branch, so a screening table / dedup picker /
// modeling setup panel / join-C1 form always looks and behaves identically
// in both modes — the controllers underneath (screen_gate_controller.js etc.)
// are already mode-agnostic and post through the same structured
// /agent/messages fields (selection / dedup_strategies / adjust_params /
// expected_step_id). Free text in the composer remains a second channel that
// can advance the same gate (agent mode's LLM-routing value is kept, not
// replaced).
function agentGateUsesConversationOnly(options = {}) {
  return options.conversationOnly === true;
}

function stripGateButtonsHtml(html) {
  // Historical gate widgets remain valuable evidence, but stale continuation
  // buttons must not survive after a newer gate appears. Passive component
  // controls (collapse, local inspection) do not advance the workflow and stay
  // useful. The latest typed gate bypasses this filter and remains actionable.
  return String(html || "").replace(
    /<button\b(?![^>]*\bdata-gate-passive-control\b)[^>]*>[\s\S]*?<\/button>/gi,
    "",
  );
}

function normalizeAgentConversationGateContent(content) {
  return String(content || "")
    .replace(
      /Confirm that you will continue with the "Recognize" response; you can directly handle the lower control or use text to specify the parameters to be adjusted./g,
      "Review the result. Confirm in the conversation or use the controls below to continue or make changes.",
    )
    .replace(
      /Confirm yes. Make sure you have the next control.\/The target line is followed by "recognizing the role"./g,
      "Review the field roles and target. Confirm in the conversation or use the controls below to make changes.",
    )
    .replace(
      /Agent The mode is described in the following language: "Continue" or "Record" if you need to adjust./g,
      "Reply Continue to proceed, or describe the changes you need.",
    )
    .replace(
      /The last step has been completed. Please reply " Continue " or indicate what needs to be adjusted./g,
      "Step complete. Reply Continue to proceed, or describe the changes you need.",
    )
    .replace(
      /The following is a list of the most recent posts on the website:Agent The mode is "start" or "continue"./g,
      "Use Start in manual mode, or ask the agent to start in the conversation.",
    )
    .replace(
      /Copy that. Please continue with the confirmation./g,
      "Review the results and confirm to continue.",
    )
    .replace(
      /The following is a list of the following:/g,
      "Confirm to continue, or use the controls below to make changes.",
    )
    .replace(
      /Please look at the current node and reply "Acknowledge" or give an adjustment order to continue./g,
      "Review the current step. Confirm to continue, or describe the changes you need.",
    );
}

function agentMessageGateBodyHtml(message, interactive, options = {}) {
  const conversationOnly = agentGateUsesConversationOnly(options);
  const html = driverGateBodyHtmlController(message, {
    renderC1Form: agentMessageC1FormHtml,
    renderDedupPicker: agentMessageDedupPickerHtml,
    renderJoinKeyPicker: agentMessageJoinKeyPickerHtml,
    renderModelingSetup: agentMessageModelingSetupHtml,
    renderScreenTable: agentMessageScreenTableHtml,
    renderTables: agentMessageTablesHtml,
    renderAdoptionGate: agentMessageAdoptionGateHtml,
    renderFeatureBinning: agentMessageFeatureBinningHtml,
    renderSpecialValues: agentMessageSpecialValuesHtml,
  }, { interactive: conversationOnly ? false : interactive });
  return conversationOnly ? stripGateButtonsHtml(html) : html;
}

function agentMessageStrategyClarificationBodyHtml(message, interactive) {
  return agentMessageStrategyClarificationHtml(message, { interactive });
}

function agentMessageHtml(message, labelStage = message?.stage, options = {}) {
  message = gateMessageForCurrentTool(message);
  const role = message.role === "user" ? "user" : "assistant";
  const isTuningProgress = role === "assistant"
    && String(message?.metadata?.kind || "") === "tool_progress"
    && Boolean(normalizeModelTuningProgress(message));
  const hasWorkflowError = role === "assistant"
    && hasWorkflowErrorDiagnostic(message?.metadata || {});
  const isStrategyClarification = role === "assistant"
    && !hasWorkflowError
    && isStrategyClarificationMessageController(message);
  // join_c1 turns carry no explicit metadata.kind (backend groups them with
  // "gate" for turn-boundary purposes at turn_handlers.py:612) but are the
  // same needs_confirmation moment — the C1 role-assignment form — so they
  // get the same card treatment.
  const isGate = role === "assistant"
    && !hasWorkflowError
    && (message?.metadata?.kind === "gate" || Boolean(message?.metadata?.join_c1));
  const hasWidget = isGate && driverGateHasWidgetController(message);
  const agentConversationOnly = agentGateUsesConversationOnly(options)
    && !(hasWidget && Boolean(options.isLatestGate));
  const conversationOnly = isGate && agentConversationOnly;
  const className = role === "user"
    ? "agent-message user"
    : `agent-message assistant${isGate ? " has-gate" : ""}${conversationOnly ? " conversation-only-gate" : ""}${isStrategyClarification ? " has-strategy-clarification" : ""}${hasWorkflowError ? " has-workflow-error" : ""}`;
  const streaming = agentMessageIsStreaming(message);
  const thinking = agentMessageIsThinking(message);
  const draftValues = message?.metadata?.draft_values;
  const hasDraftTable = role === "assistant"
    && message?.stage === "word_conclusion_draft"
    && hasReportDraftValues(draftValues)
    && !thinking;
  const visibleContent = role === "assistant" && agentGateUsesConversationOnly(options)
    ? normalizeAgentConversationGateContent(agentVisibleContent(message))
    : agentVisibleContent(message);
  const legacyContentHtml = thinking || hasDraftTable
    ? ""
    : formatAgentMessageContent(visibleContent, { markdown: role === "assistant" });
  const contentHtml = thinking
    ? agentThinkingHtml()
    : role === "assistant"
      ? workflowMessageContentHtml(message, () => legacyContentHtml)
      : legacyContentHtml;
  const memoryReferencesHtml = role === "assistant"
    ? agentMemoryReferencesHtml(message?.metadata?.memory_references)
    : "";
  const messageId = message?.id ? String(message.id) : "";
  const reportDraftHtml = hasDraftTable
    ? '<section class="report-draft-link"><strong>Draft report ready</strong><p>Review conclusions, save edits, and generate files in the report view.</p><button type="button" class="button compact" data-validation-view="report">View and edit reports</button></section>'
    : "";
  const idAttr = messageId ? ` data-agent-message-id="${escapeHtml(messageId)}"` : "";
  const stageAttr = message?.stage
    ? ` data-agent-stage="${escapeHtml(String(message.stage))}"`
    : "";
  // VD-2/UX-2: only the latest typed gate (stale-protection identical to manual
  // mode's latestInteractiveScreenMessageId / lastAssistantMessageId) renders
  // its widgets as interactive; earlier gate cards render the same widgets as
  // read-only snapshots so a stale card cannot be actioned against an
  // already-advanced step.
  const interactive = hasWidget
    && Boolean(options.isLatestGate)
    && !conversationOnly
    && driverGateMessageIsActionable(message);
  const clarificationInteractive = !agentConversationOnly && isStrategyClarification
    && Boolean(messageId)
    && messageId === lastAssistantMessageIdController(agentMessages);
  const rawBodyHtml = [
    `<div class="agent-message-content${hasDraftTable ? " hidden" : ""}" data-agent-streaming="${streaming ? "true" : "false"}" data-agent-thinking="${thinking ? "true" : "false"}">${contentHtml}</div>`,
    reportDraftHtml,
    isStrategyClarification
      ? agentMessageStrategyClarificationBodyHtml(message, clarificationInteractive)
      : "",
    role === "assistant" && hasWidget
      ? agentMessageGateBodyHtml(message, interactive, { conversationOnly })
      : "",
    role === "assistant" ? renderModelTuningMessageProgress(message) : "",
    role === "assistant" && !hasWidget ? `${agentMessageModelDeliveryHtml(message)}${agentMessageTablesHtml(message)}${agentMessageResultDatasetHtml(message)}${agentMessageReportDownloadHtml(message)}` : "",
    role === "assistant" && !conversationOnly ? agentMessageGateButtonHtml(message) : "",
  ].join("");
  const bodyHtml = agentConversationOnly
    && role === "assistant"
    && (isGate || hasWorkflowError || isStrategyClarification)
    ? stripGateButtonsHtml(rawBodyHtml)
    : rawBodyHtml;
  return [
    `<article class="${className}"${idAttr}${stageAttr}>`,
    role === "assistant" && (!options.hideMeta || isTuningProgress) ? `<div class="agent-message-meta">${escapeHtml(agentMessageMetaLabel(message, labelStage))}</div>` : "",
    // Agent prose stays in the normal conversation flow.  Functional widgets
    // inside bodyHtml (ingest notice, C1 table, screening panel, etc.) retain
    // their own visual shells; the entire reply is no longer wrapped in a
    // large coloured gate card.
    bodyHtml,
    memoryReferencesHtml,
    "</article>",
  ].join("");
}

function agentThinkingHtml() {
  return [
    '<span class="agent-thinking" role="status" aria-live="polite">',
    '<span class="agent-thinking-text">Thinking…</span>',
    '<span class="agent-thinking-dots" aria-hidden="true"><span></span><span></span><span></span></span>',
    "</span>",
  ].join("");
}

function agentValidatorAlias(validator) {
  return agentValidatorAliases[String(validator || "").trim()] || "";
}

function agentStageLabel(_stage) {
  return agentValidatorAlias(selectedTask?.validator) || "Agent";
}

function agentMessageMetaLabel(message, labelStage = message?.stage) {
  if (String(message?.metadata?.kind || "") === "tool_progress") {
    const tuningProgress = normalizeModelTuningProgress(message);
    if (tuningProgress) return tuningProgress.statusLabel;
  }
  const pieces = [agentStageLabel(labelStage)];
  const metadata = message?.metadata || {};
  const step = agentMessagePlanStep(metadata);
  const phase = metadata.phase || step?.phase || "";
  const stepTitle = metadata.step_title || step?.title || "";
  const runSeq = Number(metadata.run_seq);
  if (phase) pieces.push(String(phase));
  if (stepTitle) pieces.push(String(stepTitle));
  if (Number.isFinite(runSeq) && runSeq > 0) pieces.push(`Run ${runSeq}`);
  return pieces.filter(Boolean).join(" · ");
}

function agentMessagePlanStep(metadata = {}) {
  return planRailController.planStep(metadata, selectedTaskId);
}

function formatAgentMessageContent(content, { markdown = false } = {}) {
  if (markdown) return renderAgentMarkdown(content);
  return escapeHtml(content).replaceAll("\n", "<br>");
}

function shouldPreserveOptimisticAgentMessages(nextMessages = []) {
  const optimisticCount = agentMessages.filter((message) => message?.metadata?.optimistic).length;
  return optimisticCount > 0 && nextMessages.length < agentMessages.length;
}

function agentMessageCanPollIncrementally({ preserveOptimistic = false } = {}) {
  if (preserveOptimistic || !agentMessages.length) return false;
  if (latestPendingReportDraftMessageId(agentMessages)) return false;
  return !agentMessages.some((message) => message?.metadata?.optimistic || message?.metadata?.streaming);
}

function mergeIncrementalAgentMessages(nextMessages = []) {
  if (!nextMessages.length) return false;
  const seen = new Set(agentMessages.map((message) => message.id).filter(Boolean));
  const additions = nextMessages.filter((message) => !seen.has(message.id));
  if (!additions.length) return false;
  agentMessages = [...agentMessages, ...additions];
  return true;
}

async function loadAgentMessages(taskId = workbenchTaskId(), { preserveOptimistic = false } = {}) {
  const messageTask = (
    (taskId === projectedValidationChildTaskId && projectedValidationChildTask)
    || findTaskInCache(taskId)
    || selectedTask
  );
  // Driver tasks have a conversation in manual mode too (controls, no LLM).
  const hasConversation = selectedTaskIsAgentMode(messageTask) || taskUsesPlanRail(messageTask);
  if (!taskId || !hasConversation) {
    agentMessages = [];
    renderAgentConversation();
    return;
  }
  const useIncremental = agentMessageCanPollIncrementally({ preserveOptimistic });
  const lastMessageId = useIncremental ? agentMessages[agentMessages.length - 1]?.id : "";
  const suffix = lastMessageId ? `?after_id=${encodeURIComponent(lastMessageId)}` : "";
  const payload = await api(`api/tasks/${taskId}/agent/messages${suffix}`);
  if (!isWorkbenchTaskId(taskId)) return;
  const nextMessages = payload.messages || [];
  if (payload.incremental) {
    if (mergeIncrementalAgentMessages(nextMessages)) renderAgentConversation();
    return;
  }
  if (preserveOptimistic && shouldPreserveOptimisticAgentMessages(nextMessages)) return;
  agentMessages = nextMessages;
  renderAgentConversation();
}

// Small, stable polling fingerprint: streamed prose changes its length/tail;
// long-running tools change metadata.progress while keeping one message id.
// Avoid serializing every full historical message body on every poll.
function agentMessagePollSignature(messages = agentMessages) {
  if (!Array.isArray(messages)) return "[]";
  return JSON.stringify(messages.map((message) => {
    const content = String(message?.content || "");
    const metadata = message?.metadata || {};
    return [
      message?.id || "",
      message?.role || "",
      message?.stage || "",
      content.length,
      content.slice(-96),
      Boolean(metadata.streaming),
      metadata.kind || "",
      metadata.progress_updated_at || "",
      metadata.progress || null,
    ];
  }));
}

function agentStreamPollDelay(unchangedForMs = 0) {
  if (unchangedForMs >= AGENT_STREAM_POLL_LONG_AFTER_MS) {
    return AGENT_STREAM_POLL_LONG_INTERVAL_MS;
  }
  if (unchangedForMs >= AGENT_STREAM_POLL_IDLE_AFTER_MS) {
    return AGENT_STREAM_POLL_IDLE_INTERVAL_MS;
  }
  return AGENT_STREAM_POLL_INTERVAL_MS;
}

async function pollAgentMessagesUntilSettled(taskId, pendingPromise, { preserveOptimistic = false } = {}) {
  let settled = false;
  let unchangedForMs = 0;
  let messageSignature = agentMessagePollSignature();
  let resolveSettlement;
  const settlementSignal = new Promise((resolve) => {
    resolveSettlement = resolve;
  });
  pendingPromise.then(
    () => { settled = true; resolveSettlement("settled"); },
    () => { settled = true; resolveSettlement("settled"); },
  );
  while (!settled && isWorkbenchTaskId(taskId)) {
    const delay = agentStreamPollDelay(unchangedForMs);
    const wakeReason = await Promise.race([
      sleep(delay).then(() => "poll"),
      settlementSignal,
    ]);
    if (wakeReason === "settled" || settled || !isWorkbenchTaskId(taskId)) break;
    try {
      await loadAgentMessages(taskId, { preserveOptimistic });
      const nextSignature = agentMessagePollSignature();
      if (nextSignature === messageSignature) {
        unchangedForMs += delay;
      } else {
        messageSignature = nextSignature;
        unchangedForMs = 0;
      }
    } catch (_error) {
      // The primary request path owns user-visible errors.
      unchangedForMs += delay;
    }
  }
  await reloadDataWorkspace(taskId, { silent: true });
}

async function handleAgentMaterialSelectionRequest(taskId) {
  const task = findTaskInCache(taskId) || (selectedTaskId === taskId ? selectedTask : null);
  if (!task) {
    setActionStatus("Could not find the task.", "error", "Refresh the task list and try again.");
    return false;
  }
  const selectedMaterialsTask = await materialBindingDialog.ensureMaterialSelection(task, { force: true });
  if (!selectedMaterialsTask) {
    setActionStatus("Select validation files to continue.", "info", "After selecting files, scan them again.");
    return false;
  }
  selectedTaskId = selectedMaterialsTask.id;
  selectedTask = selectedMaterialsTask;
  rememberSelectedTaskId(selectedMaterialsTask.id);
  await refreshTasks();
  await reloadDataWorkspace(taskId, { silent: true });
  if (selectedTaskId === taskId) {
    setActionStatus("File selection saved.", "success", "Next step: scan the selected files.");
  }
  return true;
}

async function startAgentValidation() {
  const taskId = workbenchTaskId();
  if (!taskId) return;
  const input = $("agentComposerInput");
  const originalValue = input.value;
  const content = input.value.trim();
  if (!content) {
    setActionStatus("Enter a task or question for the agent.", "error");
    return;
  }
  // Agent mode is manual operation delegated to an LLM and therefore requires a
  // configured model. Manual risk intake is the one deterministic exception: the
  // existing risk state machine parses the operator's explicit analysis type and
  // material contract without invoking an LLM.
  const deterministicRiskIntake = selectedTaskNeedsManualRiskIntake();
  const deterministicPortfolioTurn = deterministicRiskIntake
    ? false
    : selectedTaskNeedsDeterministicPortfolioTurn();
  const deterministicTurn = deterministicRiskIntake || deterministicPortfolioTurn;
  if (!deterministicTurn) {
    const unavailableModelMessage = agentModelUnavailableMessage();
    if (showAgentModelGuidance(unavailableModelMessage)) return;
  }
  setAgentComposerNotice("");
  const modelId = deterministicTurn ? "" : ($("agentModelSelect")?.value || "");
  input.value = "";
  autoGrowComposerInput();
  updateAgentSendDisabled();
  const optimisticMessage = appendOptimisticAgentUserMessage(content, modelId);
  const optimisticThinkingMessage = appendOptimisticAgentThinkingMessage(modelId);
  const controller = new AbortController();
  agentRequestAbortControllers.set(taskId, controller);
  let result;
  try {
    // A revision or chat confirmation must see the latest local edits, even
    // when sent before the autosave delay or after a previous save failed.
    if (reportDraftState.get(taskId)) await reportDraftState.save(taskId);
    const requestBody = { content };
    if (!deterministicTurn) {
      requestBody.model_id = modelId || null;
      requestBody.effort = agentEffort();
      requestBody.acceptance_mode = agentAcceptanceModeValue();
    }
    const requestPromise = api(`api/tasks/${taskId}/agent/messages`, {
      method: "POST",
      signal: controller.signal,
      body: JSON.stringify(requestBody),
    });
    const streamPollPromise = pollAgentMessagesUntilSettled(taskId, requestPromise, { preserveOptimistic: true });
    result = await requestPromise;
    await streamPollPromise;
  } catch (error) {
    removeOptimisticAgentMessage(optimisticMessage.id);
    removeOptimisticAgentMessage(optimisticThinkingMessage.id);
    if (error?.name === "AbortError") {
      autoGrowComposerInput();
      updateAgentSendDisabled();
      setActionStatus("The current action has stopped. Enter your next instruction.", "success");
      return;
    }
    input.value = originalValue;
    autoGrowComposerInput();
    updateAgentSendDisabled();
    if (showAgentModelGuidance(agentModelConfigurationErrorMessage(error))) return;
    throw error;
  } finally {
    if (agentRequestAbortControllers.get(taskId) === controller) {
      agentRequestAbortControllers.delete(taskId);
    }
  }
  agentMessages = result.messages || agentMessages;
  renderAgentConversation();
  if (result.status === "cancel_requested") {
    await waitForAgentValidation(taskId, { stopping: true });
    return;
  }
  if (
    result.status === "awaiting_material_selection"
    || result.ui_action?.type === "select_validation_materials"
  ) {
    await handleAgentMaterialSelectionRequest(taskId);
    return;
  }
  if (result.status !== "accepted") return;
  await waitForAgentValidation(taskId);
}

async function uploadRiskAnalysisMaterials(files) {
  const taskId = requireTaskId(selectedTaskId, "Upload risk analysis files");
  if (
    !selectedTaskIsRiskAnalysisAgent()
    && !selectedTaskNeedsManualRiskIntake()
  ) {
    throw new Error("This task does not support risk analysis file uploads.");
  }
  const selectedFiles = Array.from(files || []);
  if (!selectedFiles.length) return;
  const uploadButton = $("riskMaterialUploadButton");
  if (uploadButton) uploadButton.disabled = true;
  setAgentComposerNotice(`Uploading ${selectedFiles.length} files...`);
  try {
    for (const file of selectedFiles) {
      await uploadDataset(taskId, file, { role: "sample" });
    }
    await reloadDataWorkspace(taskId, { silent: true });
    const names = selectedFiles.map((file) => file.name).join(",");
    const input = $("agentComposerInput");
    input.value = `Uploaded: ${names}. Check the table structure and fields, then continue the analysis.`;
    autoGrowComposerInput();
    updateAgentSendDisabled();
    setAgentComposerNotice(`Uploaded ${selectedFiles.length} files. Checking fields...`);
    await startAgentValidation();
  } finally {
    if (uploadButton) uploadButton.disabled = false;
    const picker = $("riskMaterialUploadInput");
    if (picker) picker.value = "";
  }
}

async function dispatchAgentValidation(taskId = selectedTaskId) {
  const normalizedTaskId = requireTaskId(taskId || selectedTaskId, "Initialize agent");
  const modelId = $("agentModelSelect").value || "";
  const result = await api(`/api/tasks/${normalizedTaskId}/agent/start`, {
    method: "POST",
    body: JSON.stringify({
      model_id: modelId || null,
      effort: agentEffort(),
      acceptance_mode: agentAcceptanceModeValue(),
    }),
  });
  agentMessages = result.messages || agentMessages;
  renderAgentConversation();
  if (result.status !== "accepted") return result;
  await waitForAgentValidation(normalizedTaskId);
  return result;
}

async function stopAgentValidation(taskId = workbenchTaskId()) {
  invalidateAgentBatchAutoRun();
  const normalizedTaskId = requireTaskId(taskId || selectedTaskId, "Stop agent");
  const controller = agentRequestAbortControllers.get(normalizedTaskId);
  if (controller) controller.abort();
  const result = await api(`api/tasks/${normalizedTaskId}/agent/stop`, {
    method: "POST",
  });
  agentMessages = result.messages || agentMessages;
  renderAgentConversation();
  updateAgentSendDisabled();
  if (result.status === "cancel_requested") {
    await waitForAgentValidation(normalizedTaskId, { stopping: true });
    return;
  }
  setActionStatus(result.message || "The current action has stopped. Enter your next instruction.", "success");
}

async function stopAgentValidationByMessage(content, taskId = workbenchTaskId()) {
  invalidateAgentBatchAutoRun();
  const normalizedTaskId = requireTaskId(taskId || selectedTaskId, "Stop agent");
  const text = String(content || "").trim();
  if (!agentComposerStopIntent(text)) {
    setAgentComposerNotice("Enter a clear stop command, such as Stop current action.", "info");
    return;
  }
  const input = $("agentComposerInput");
  if (input) {
    input.value = "";
    autoGrowComposerInput();
    updateAgentSendDisabled();
  }
  const result = await api(`api/tasks/${normalizedTaskId}/agent/messages`, {
    method: "POST",
    body: JSON.stringify({ content: text }),
  });
  agentMessages = result.messages || agentMessages;
  renderAgentConversation();
  updateAgentSendDisabled();
  if (result.status === "cancel_requested") {
    await waitForAgentValidation(normalizedTaskId, { stopping: true });
    return;
  }
  setActionStatus(result.message || "No agent action is running.", "info");
}

async function waitForAgentValidation(taskId, { stopping = false } = {}) {
  const busyText = stopping ? "Stopping agent..." : "Agent validation in progress...";
  setBusy("agent", busyText, taskId);
  setActionStatus(busyText, "busy");
  try {
    const progressPromise = pollValidationProgress(
      new Set(["scanned", "executed", "writing_artifacts", "failed", "succeeded", "review_required"]),
      taskId,
      { stopping, settleWhenServerIdle: true },
    );
    const streamPollPromise = pollAgentMessagesUntilSettled(taskId, progressPromise);
    const finalTask = await progressPromise;
    await streamPollPromise;
    if (isWorkbenchTaskId(taskId)) {
      await loadAgentMessages(taskId);
      await loadReportFields(taskId);
      if (stopping || agentValidationStopped(finalTask || workbenchTask())) {
        setActionStatus("Agent stopped. You can restart the step or continue from its current results.", "success");
        return finalTask;
      }
      if (agentValidationPaused(finalTask || workbenchTask())) {
        setActionStatus("The current stage has been completed and awaits your next instructions.", "success");
        return finalTask;
      }
      if (finalTask?.status === "failed" || selectedTask?.status === "failed") {
        setTaskFailureActionStatus(finalTask || selectedTask);
      } else {
        setActionStatus("Agent action complete.", "success");
      }
    }
    return finalTask;
  } finally {
    // Contract auto-continue nests startAgentValidation inside a parent-scoped
    // runAction. That outer finally only clears the parent, so the child busy
    // flag set here must be released or the composer stays in stop mode.
    if (taskBusyAction(taskId) === "agent") {
      setBusy(null, "", taskId);
    }
  }
}

function agentValidationStopped(task) {
  return task?.stopped === true;
}

function agentValidationPaused(task) {
  const status = task?.status || "";
  return ["scanned", "executed", "writing_artifacts", "review_required"].includes(status);
}

function invalidateAgentBatchAutoRun() {
  agentBatchAutoRunGeneration += 1;
}

function maybeResumeAgentValidationBatch() {
  if (!usesAgentValidationWorkbench(selectedTask)) return;
  void continueAgentValidationBatch();
}

function agentBatchChildIsTerminal(task) {
  return ["succeeded", "failed", "cancelled"].includes(
    String(task?.status || "").toLowerCase(),
  );
}

function agentBatchAutoRunIsFinished(payload) {
  const parentStatus = String(payload?.status || "").toLowerCase();
  if (["completed", "succeeded", "failed", "cancelled"].includes(parentStatus)) {
    return true;
  }
  const items = payload?.items || [];
  if (!items.length) return true;
  return items.every((item) => {
    const status = String(item.status || "").toLowerCase();
    if (["succeeded", "failed", "cancelled"].includes(status)) return true;
    return status === "review_required" && Boolean(item.reportComplete);
  });
}

async function agentBatchChildNeedsInputConfirmation(childId) {
  try {
    const record = await api(
      `/api/tasks/${encodeURIComponent(childId)}/validation-input-contract`,
    );
    return record?.status === "pending_confirmation" || record?.status === "blocked";
  } catch (_error) {
    return false;
  }
}

async function continueAgentValidationBatch({ resumeChildId = "" } = {}) {
  if (!usesAgentValidationWorkbench(selectedTask)) return;
  if (agentBatchAutoRunPromise) return agentBatchAutoRunPromise;
  const run = runContinueAgentValidationBatch({ resumeChildId });
  const tracked = run.finally(() => {
    if (agentBatchAutoRunPromise === tracked) agentBatchAutoRunPromise = null;
  });
  agentBatchAutoRunPromise = tracked;
  return agentBatchAutoRunPromise;
}

async function runContinueAgentValidationBatch({ resumeChildId = "" } = {}) {
  const generation = agentBatchAutoRunGeneration;
  const parentId = selectedTaskId;
  if (!parentId || !usesAgentValidationWorkbench(selectedTask)) return;
  agentAcceptanceMode = "auto_accept";
  renderAgentAcceptanceModePreference();
  let payload;
  try {
    await validationBatchPanelController.selectTask(selectedTask, { force: true });
    const raw = await api(`api/validation-batches/${encodeURIComponent(parentId)}`);
    payload = normalizeValidationBatchPayload(raw, parentId);
  } catch (error) {
    setActionStatus("Could not load batch models. Automatic review cannot start.", "error", error?.message || "");
    return;
  }
  if (generation !== agentBatchAutoRunGeneration || selectedTaskId !== parentId) return;
  if (agentBatchAutoRunIsFinished(payload)) return;
  if (!llmSettings.enabled_models?.length) {
    await loadLLMSettings({ silent: true });
    if (!llmSettings.enabled_models?.length) {
      setActionStatus("Configure an AI model", "info", "Select a configured AI model in the conversation to resume automatic review. You can still edit and confirm the draft.");
      return;
    }
  }
  const items = [...(payload.items || [])].sort((left, right) => left.ordinal - right.ordinal);
  const resumeId = String(resumeChildId || "").trim();
  let seenResume = !resumeId;
  setActionStatus("Checking the AI model for automatic review...", "busy");
  for (const item of items) {
    if (generation !== agentBatchAutoRunGeneration || selectedTaskId !== parentId) return;
    const childId = item.childTaskId;
    if (!childId) continue;
    if (item.pendingReportDraft) continue;
    if (!seenResume) {
      if (childId === resumeId) seenResume = true;
      else continue;
    }
    let child;
    try {
      child = await api(`api/tasks/${encodeURIComponent(childId)}`);
    } catch (error) {
      setActionStatus(
        `${item.modelName || "Current Model"}Could not load the model. Automatic review stopped.`,
        "error",
        error?.message || "",
      );
      return;
    }
    if (agentBatchChildIsTerminal(child)) continue;
    if (typeof validationBatchPanelController.selectChild === "function") {
      validationBatchPanelController.selectChild(childId);
    }
    await applyProjectedValidationChild(childId, { force: true });
    if (generation !== agentBatchAutoRunGeneration || selectedTaskId !== parentId) return;
    const modelLabel = [item.modelName, item.modelVersion].filter(Boolean).join(" · ")
      || "Current Model";
    setActionStatus(`Automatically reviewing: ${modelLabel}`, "busy");
    if (child.active_job_kind) {
      await waitForAgentValidation(childId);
    } else {
      const result = await dispatchAgentValidation(childId);
      if (result?.status === "awaiting_confirmation") {
        setActionStatus(
          `${modelLabel}Confirm ambiguous fields before automatic review can continue.`,
          "success",
        );
        return;
      }
    }
    if (generation !== agentBatchAutoRunGeneration || selectedTaskId !== parentId) return;
    let latest = child;
    try {
      latest = await api(`api/tasks/${encodeURIComponent(childId)}`);
    } catch (_error) {
      latest = child;
    }
    if (
      !agentBatchChildIsTerminal(latest)
      && await agentBatchChildNeedsInputConfirmation(childId)
    ) {
      setActionStatus(
        `${modelLabel}Confirm ambiguous fields before automatic review can continue.`,
        "success",
      );
      return;
    }
    try {
      await validationBatchPanelController.selectTask(selectedTask, { force: true });
    } catch (_error) {
      // Switcher refresh is presentational.
    }
  }
  if (generation !== agentBatchAutoRunGeneration || selectedTaskId !== parentId) return;
  setActionStatus("Automatic review complete for all models.", "success");
}

function prefillAgentTaskInstruction(task) {
  if (task?.run_mode !== "agent") return;
  if (usesAgentValidationWorkbench(task)) return;
  const input = $("agentComposerInput");
  if (!input || input.value.trim()) return;
  const definition = taskTypeDefinition(task.task_type || createTaskDialog.activeTaskType());
  input.value = definition.initialGoal;
  autoGrowComposerInput();
  updateAgentSendDisabled();
}

// UX-5: "Sending Message Interact" on a plan-rail no_progress event — focuses the composer
// without overwriting anything the user may already be drafting there.
function focusAgentComposerForIntervene() {
  const input = $("agentComposerInput");
  if (!input) return;
  input.focus();
}

function setCreateTaskSubmitting(isSubmitting) {
  const button = $("createTaskButton");
  if (!button) return;
  button.disabled = isSubmitting;
  button.dataset.createBusy = isSubmitting ? "true" : "false";
}

async function createTask() {
  const task = await createTaskDialog.createTask();
  if (!task) return null;
  selectedTaskId = task.id;
  selectedTask = task;
  rememberSelectedTaskId(task.id);
  renderStoredStateSummaries();
  const candidateLabLoadPromise = strategyCandidateLabController.selectTask(task);
  await refreshTasks();
  await reloadDataWorkspace(task.id, { silent: true });
  await loadReportFields();
  await candidateLabLoadPromise;
  setCreateStatus("Task created.");
  closeTaskDialog();
  prefillAgentTaskInstruction(task);
  return task;
}

async function refreshTasks() {
  taskCache = await api("api/tasks");
  syncSelectedTaskFromCache();
  for (const task of taskCache) {
    if (typeof reconcileDriverGateSubmissions === "function") {
      reconcileDriverGateSubmissions(task?.id, {
        serverBusy: Boolean(task?.active_job_kind),
      });
    }
  }
  ensureActiveTaskProgressPolling();
}

async function ensureValidationMaterialSelection(task) {
  if (!task || (task.task_type || "validation") !== "validation") return task;
  const selectedMaterialsTask = await materialBindingDialog.ensureMaterialSelection(task);
  if (!selectedMaterialsTask) {
    setActionStatus("Select validation files to continue.", "info");
    return null;
  }
  selectedTaskId = selectedMaterialsTask.id;
  selectedTask = selectedMaterialsTask;
  rememberSelectedTaskId(selectedMaterialsTask.id);
  await refreshTasks();
  return selectedTask || selectedMaterialsTask;
}

async function scanCurrentTask() {
  const taskId = selectedTaskId;
  const task = await ensureValidationMaterialSelection(selectedTask);
  const resolvedTaskId = task?.id || taskId;
  if (!resolvedTaskId) return;
  const controller = new AbortController();
  scanAbortController = controller;
  try {
    const result = await api(`api/tasks/${resolvedTaskId}/scan`, {
      method: "POST",
      signal: controller.signal,
    });
    if (selectedTaskId === resolvedTaskId) renderScanResult(result);
    await refreshTasks();
    if (selectedTaskId === resolvedTaskId) {
      if (selectedTask?.status === "failed") {
        setTaskFailureActionStatus(selectedTask);
        return;
      }
      setActionStatus(
        selectedTaskIsAgentMode(selectedTask) ? "Input file checks complete." : "File scan complete.",
        "success",
      );
      scrollToManualWorkflowSection("scan");
    }
  } finally {
    if (scanAbortController === controller) scanAbortController = null;
  }
}

async function createTaskAndScan() {
  if (createTaskInFlight) {
    setCreateStatus("Creating task...");
    return;
  }
  createTaskInFlight = true;
  setCreateTaskSubmitting(true);
  try {
    let task = await createTask();
    if (!task) return;
    task = await ensureValidationMaterialSelection(task);
    if (!task) return;
    const isValidationTask = (task.task_type || createTaskDialog.activeTaskType() || defaultTaskType) === "validation";
    if (usesAgentValidationWorkbench(task)) {
      await requestTaskSelection(task);
      setActionStatus("Checking the AI model for automatic review...", "busy");
      await continueAgentValidationBatch();
      return;
    }
    if (task.run_mode === "agent") {
      const taskId = task.id || selectedTaskId;
      const activeDialogTaskType = createTaskDialog.activeTaskType();
      const definition = taskTypeDefinition(task.task_type || activeDialogTaskType);
      setBusy(null, "", taskId);
      await loadAgentMessages(taskId);
      renderAll();
      if (!isValidationTask && task.task_type === "vintage") {
        await dispatchDriverStart(taskId);
        renderAll();
        setActionStatus("Risk analysis task created. Describe what you want to analyze.", "success");
        return;
      }
      if (!isValidationTask && task.task_type === "portfolio") {
        await dispatchDriverStart(taskId);
        renderAll();
        setActionStatus("Portfolio analysis task created. Confirm the portfolio settings to continue.", "success");
        return;
      }
      if (!isValidationTask && definition.initialGoal) {
        // createTask() already seeded the conversation composer via
        // prefillAgentTaskInstruction; just focus it (the V2 plan dialog is retired).
        $("agentComposerInput")?.focus?.();
        setActionStatus(`${definition.label}Task created. Review the suggested target, then confirm and send.`, "success");
        return;
      }
      setActionStatus("Task created. Enter your next instruction.", "success");
      return;
    }
    // Manual mode for a driver task (data_join / feature / modeling): start the
    // deterministic, control-driven flow (no LLM). Validation manual still scans.
    if (taskUsesPlanRail(task)) {
      const taskId = task.id || selectedTaskId;
      setBusy(null, "", taskId);
      await dispatchDriverStart(taskId);
      renderAll();
      setActionStatus(`${taskTypeDefinition(task.task_type).label}Task created. Review and confirm each step below.`, "success");
      return;
    }
    setBusy(null, "", null);
    setBusy("scan", "Task created. Scanning input files...", task.id);
    setActionStatus("Task created. Scanning input files...", "busy");
    try {
      await scanCurrentTask();
      await loadTaskEvidence(task.id);
    } finally {
      setBusy(null, "", task.id);
    }
  } finally {
    createTaskInFlight = false;
    setCreateTaskSubmitting(false);
  }
}

// Start a driver-based task's deterministic flow (manual mode, no LLM): POST the
// agent-start endpoint, which routes to the plan-conversation driver.
async function dispatchDriverStart(taskId = selectedTaskId) {
  const normalizedTaskId = requireTaskId(taskId || selectedTaskId, "Start");
  const result = await api(`/api/tasks/${normalizedTaskId}/agent/start`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  agentMessages = result.messages || agentMessages;
  renderAgentConversation();
  await reloadDataWorkspace(normalizedTaskId, { silent: true });
}

async function refreshStrategyCandidateLabAfterSettled(taskId, task) {
  if (
    selectedTaskId !== taskId
    || task?.task_type !== "strategy"
  ) {
    return;
  }
  try {
    await strategyCandidateLabController.refresh(taskId, { silent: true });
  } catch (_error) {
    // Candidate evidence is secondary to the main job lifecycle. A projection
    // refresh failure must not keep a completed Agent task inside the poller.
  }
}

async function pollValidationProgress(
  doneStatuses = terminalTaskStatuses,
  taskId = selectedTaskId,
  { stopping = false, background = false, settleWhenServerIdle = false } = {},
) {
  if (!taskId) return null;
  const claim = claimProgressPoll(progressPolls, taskId, { background });
  if (!claim.claimed) return claim.existing.promise;
  const pollState = claim.pollState;
  const promise = (async () => {
    const startedAt = Date.now();
    const timeoutMs = 1000 * 60 * 60;
    while (true) {
      if (pollState.cancelled) return null;
      await sleep(1000);
      if (pollState.cancelled) return null;
      await refreshTasks();
      let polledTask = findTaskInCache(taskId);
      if (!polledTask && isWorkbenchTaskId(taskId) && taskId !== selectedTaskId) {
        try {
          polledTask = await api(`api/tasks/${encodeURIComponent(taskId)}`);
        } catch (_error) {
          polledTask = null;
        }
      }
      if (!polledTask) return null;
      if (taskId === projectedValidationChildTaskId) {
        projectedValidationChildTask = polledTask;
      }
      if (isWorkbenchTaskId(taskId)) {
        await loadTaskEvidence(taskId);
        if (metricOverviewComplete(polledTask) && !currentMetricPreviewHasValues(taskId)) {
          await loadReportFields(taskId);
        }
        if (selectedTaskIsAgentMode(polledTask) || usesAgentValidationWorkbench(selectedTask)) {
          await loadAgentMessages(taskId);
        }
        renderChangedValidationViews();
      } else {
        renderTaskList();
      }

      const status = polledTask.status || "";
      const serverBusyAction = taskServerBusyAction(polledTask);
      const stopped = stopping && !serverBusyAction;
      const settledOnServerIdle = settleWhenServerIdle && !serverBusyAction;
      const reachedTerminalStatus = doneStatuses.has(status) && !serverBusyAction;
      if (stopping && !serverBusyAction) {
        if (isWorkbenchTaskId(taskId) && !background) {
          setActionStatus("Agent stopped. You can restart the step or continue from its current results.", "success");
        }
      }
      // Agent-stage exceptions may occur before a deterministic stage updates
      // the task status (for example while constructing the scan contract).
      // The job lease is the authoritative liveness signal in that gap: once
      // it is gone, return control to the composer instead of polling the stale
      // pre-stage status for an hour.
      if (!stopped && !settledOnServerIdle && reachedTerminalStatus) {
        if (isWorkbenchTaskId(taskId) && !background) {
          if (status === "failed" || status === "review_required") {
            setTaskFailureActionStatus(polledTask);
          } else {
            setActionStatus("Validation complete.", "success");
          }
        }
      }
      if (stopped || settledOnServerIdle || reachedTerminalStatus) {
        // Some focused source-level harnesses execute this poller in isolation.
        // Keep the secondary projection hook optional there, while the app
        // always supplies it.
        if (typeof refreshStrategyCandidateLabAfterSettled === "function") {
          await refreshStrategyCandidateLabAfterSettled(taskId, polledTask);
        }
        return polledTask;
      }

      // Status copy for in-flight polling is owned by taskActionStatusSnapshot()
      // via renderCurrentTask(); writing here too would alternate the pill text
      // between two sources every second.

      if (Date.now() - startedAt > timeoutMs) {
        if (isWorkbenchTaskId(taskId) && !background) {
          setActionStatus("Validation is still running. Refresh the results later.", "error");
        }
        return polledTask;
      }
    }
  })().finally(() => releaseProgressPoll(progressPolls, taskId, pollState));
  pollState.promise = promise;
  return promise;
}

async function validateCurrentTask(options = {}) {
  const taskId = selectedTaskId;
  if (!taskId) return;
  // A fresh notebook run produces a fresh reproducibility result; the entry
  // animation is allowed to play once for the new run.
  resetReproducibilityRenderSignatures();
  const result = await api(`api/tasks/${taskId}/notebook`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  if (selectedTaskId === taskId) {
    renderValidationResult(result);
    appendPendingReproducibilitySteps();
  }
  const finalTask = await pollValidationProgress(new Set(["executed", "failed", "scanned"]), taskId);
  if (selectedTaskId !== taskId) return;
  if (finalTask?.status === "scanned" || selectedTask?.status === "scanned") {
    setActionStatus("Notebook stopped. You can rerun it.", "success");
    return;
  }
  await loadReportFields(taskId);
  await loadTaskEvidence(taskId);
  if (selectedTask?.status === "failed" || selectedTask?.status === "review_required") {
    setTaskFailureActionStatus(selectedTask || finalTask);
  } else {
    setActionStatus("Validation complete.", "success");
    scrollToManualWorkflowSection("notebook");
  }
}

async function cancelCurrentNotebook() {
  const taskId = selectedTaskId;
  if (!taskId) return;
  await api(`api/tasks/${taskId}/notebook/cancel`, { method: "POST" });
  if (selectedTaskId === taskId) setActionStatus("StoppingNotebook...", "busy");
  const finalTask = await pollValidationProgress(new Set(["scanned", "failed"]), taskId);
  if (selectedTaskId !== taskId) return;
  await loadTaskEvidence(taskId);
  if (finalTask?.status === "failed" || selectedTask?.status === "failed") {
    setTaskFailureActionStatus(finalTask || selectedTask);
  } else {
    setActionStatus("Notebook stopped. You can rerun it.", "success");
  }
}

async function cancelCurrentMetrics() {
  const taskId = selectedTaskId;
  if (!taskId) return;
  await api(`api/tasks/${taskId}/metrics/cancel`, { method: "POST" });
  if (selectedTaskId === taskId) setActionStatus("Stopping indicator generation...", "busy");
  const finalTask = await pollValidationProgress(new Set(["executed", "writing_artifacts", "failed"]), taskId);
  if (selectedTaskId !== taskId) return;
  await loadTaskEvidence(taskId);
  if (finalTask?.status === "failed" || selectedTask?.status === "failed") {
    setTaskFailureActionStatus(finalTask || selectedTask);
  } else if (finalTask?.status === "writing_artifacts" || selectedTask?.status === "writing_artifacts") {
    setActionStatus("Metrics and Excel analysis ready.", "success");
  } else {
    setActionStatus("Metric calculation stopped. You can rerun it.", "success");
  }
}

async function cancelCurrentReport() {
  const taskId = selectedTaskId;
  if (!taskId) return;
  await api(`api/tasks/${taskId}/report/cancel`, { method: "POST" });
  if (selectedTaskId === taskId) setActionStatus("Stopping report generation...", "busy");
  const finalTask = await pollValidationProgress(new Set(["writing_artifacts", "succeeded", "review_required", "failed"]), taskId);
  if (selectedTaskId !== taskId) return;
  await loadTaskEvidence(taskId);
  if (finalTask?.status === "failed" || selectedTask?.status === "failed") {
    setTaskFailureActionStatus(finalTask || selectedTask);
  } else if ((finalTask?.report_available || selectedTask?.report_available) === true) {
    setActionStatus("Word report ready to download.", "success");
  } else {
    setActionStatus("Report generation stopped. You can rerun it.", "success");
  }
}

async function generateMetrics() {
  const taskId = selectedTaskId;
  if (!taskId) return;
  await api(`api/tasks/${taskId}/metrics`, { method: "POST" });
  if (selectedTaskId === taskId) {
    appendPendingMetricSteps();
    $("metricPreview").innerHTML =
      '<div class="result-summary empty">Generating metrics and Excel analysis...</div>';
  }
  const finalTask = await pollValidationProgress(new Set(["executed", "writing_artifacts", "failed"]), taskId);
  if (selectedTaskId !== taskId) return;
  await loadReportFields(taskId);
  await loadTaskEvidence(taskId);
  if (selectedTask?.status === "failed") {
    setTaskFailureActionStatus(selectedTask);
  } else if (finalTask?.status === "executed" || selectedTask?.status === "executed") {
    setActionStatus("Metric calculation stopped. You can rerun it.", "success");
  } else {
    setActionStatus("Metrics and Excel analysis ready.", "success");
    scrollToManualWorkflowSection("metrics");
  }
}

async function loadReportFields(taskId = workbenchTaskId()) {
  if (!taskId || (usesAgentValidationWorkbench(selectedTask) && taskId === selectedTaskId)) {
    renderMetricPreview({});
    return;
  }
  const payload = await api(`api/tasks/${taskId}/report-fields`);
  if (!isWorkbenchTaskId(taskId)) return;
  renderMetricPreview(
    payload.metric_values || {},
    payload.workbook_source,
    payload.metric_table_sections || [],
  );
}

async function generateReport() {
  const taskId = selectedTaskId;
  if (!taskId) return;
  await api(`api/tasks/${taskId}/report`, { method: "POST" });
  await pollValidationProgress(terminalTaskStatuses, taskId);
  if (selectedTaskId !== taskId) return;
  await loadReportFields(taskId);
  if (selectedTask?.status === "failed") {
    setTaskFailureActionStatus(selectedTask);
  } else {
    setActionStatus("Word report ready to download.", "success");
    scrollToManualWorkflowSection("report");
  }
}

function downloadWordReport() {
  const taskId = workbenchTaskId();
  if (!taskId) return;
  window.location.href = `api/tasks/${taskId}/report/download`;
}

function downloadExcelAnalysis() {
  const taskId = workbenchTaskId();
  if (!taskId) return;
  window.location.href = `api/tasks/${taskId}/analysis/download`;
}

function previewWordReport() {
  openWordPreviewDialog();
}

const PURGE_SUMMARY_FIELDS = [
  ["datasets", "Dataset"],
  ["joins", "JOIN"],
  ["plans", "Planned"],
  ["experiments", "Experiment"],
  ["model_artifacts", "Model outputs"],
  ["strategies", "Policy"],
  ["child_tasks", "Child validation tasks"],
  ["owned_batch_material_trees", "Uploaded batch files"],
];

function taskPurgeApiBase(task) {
  if (isValidationBatchTask(task)) return `api/validation-batches/${task.id}`;
  return `api/tasks/${task.id}`;
}

function validatedValidationBatchPurgeSummary(preview) {
  const invalid = () => {
    throw new Error("invalid validation batch purge preview");
  };
  if (!preview || typeof preview !== "object" || Array.isArray(preview)) invalid();
  const summary = preview.purge_summary;
  if (!summary || typeof summary !== "object" || Array.isArray(summary)) invalid();
  const requiredCounts = [
    preview.task_count,
    preview.child_task_count,
    preview.active_job_count,
    preview.owned_batch_material_tree_count,
    summary.child_tasks,
    summary.owned_batch_material_trees,
  ];
  if (!requiredCounts.every((value) => Number.isSafeInteger(value) && value >= 0)) {
    invalid();
  }
  if (
    preview.child_task_count < 1
    || preview.child_task_count > 10
    || preview.task_count !== preview.child_task_count + 1
    || preview.child_task_count !== summary.child_tasks
    || preview.owned_batch_material_tree_count !== summary.owned_batch_material_trees
    || preview.owned_batch_material_tree_count > 1
  ) {
    invalid();
  }
  if (
    !Object.values(summary).every(
      (value) => Number.isSafeInteger(value) && value >= 0,
    )
  ) {
    invalid();
  }
  return summary;
}

async function loadTaskPurgeSummary(task) {
  try {
    const preview = await api(`${taskPurgeApiBase(task)}/purge-preview`);
    const summary = isValidationBatchTask(task)
      ? validatedValidationBatchPurgeSummary(preview)
      : preview && preview.purge_summary ? preview.purge_summary : null;
    if (!summary) return [];
    const items = [];
    for (const [key, label] of PURGE_SUMMARY_FIELDS) {
      if (summary[key]) items.push({ key, label, count: summary[key] });
    }
    return items;
  } catch (error) {
    // A batch DELETE cascades to child tasks and owned uploads.  Never fall
    // back to an empty confirmation scope if its dedicated preview is down.
    if (isValidationBatchTask(task)) throw error;
    return [];
  }
}

async function reconcileTaskBeforeDelete(task) {
  if (!task?.id) return null;
  if (taskBusyActions.get(task.id) !== "agent" || taskServerBusyAction(task)) {
    return task;
  }
  try {
    await refreshTasks();
  } catch (_) {
    return task;
  }
  const latestTask = findTaskInCache(task.id);
  if (!latestTask) {
    setBusy(null, "", task.id);
    return null;
  }
  if (!taskServerBusyAction(latestTask)) {
    setBusy(null, "", task.id);
  }
  return latestTask;
}

async function deleteTask(task) {
  if (!task) return;
  const targetTask = await reconcileTaskBeforeDelete(task);
  if (!targetTask) {
    setActionStatus("The task no longer exists.", "success");
    return;
  }
  if (taskBusyAction(targetTask.id)) {
    setActionStatus("The task is running. Stop it or wait for it to finish before deleting.", "error");
    return;
  }
  if (taskServerBusyAction(targetTask)) {
    setActionStatus("A running task cannot be deleted.", "error");
    return;
  }
  let purgeItems = [];
  try {
    purgeItems = await loadTaskPurgeSummary(targetTask);
  } catch (error) {
    setActionStatus(
      "Could not determine which batch files would be deleted. Nothing was deleted.",
      "error",
      String(error?.message || error || "Please try again later."),
    );
    return;
  }
  const taskName = taskDisplayName(targetTask);
  const deletingBatch = isValidationBatchTask(targetTask);
  const childTaskCount = Number(
    purgeItems.find((item) => item.key === "child_tasks")?.count || 0,
  );
  const ownedMaterialTreeCount = Number(
    purgeItems.find((item) => item.key === "owned_batch_material_trees")?.count || 0,
  );
  const batchDeleteScope = deletingBatch
    ? `This will permanently delete ${childTaskCount} child validation tasks, task logs, and local output files${
        ownedMaterialTreeCount ? ", plus uploaded batch files" : ""
      }. Files at external paths will be kept. This cannot be undone.`
    : "Task records and local output files will be permanently deleted.";
  const confirmed = await showPlatformConfirm({
    title: "Delete Task",
    message: `Delete ${deletingBatch ? "validation batch" : "task"} [${taskName}]? ${batchDeleteScope}`,
    messageParts: [
      { text: deletingBatch ? "Delete validation batch " : "Delete task " },
      { text: `[${taskName}]`, strong: true },
      { text: `? ${batchDeleteScope}` },
    ],
    purgeItems,
    confirmText: "Delete",
    cancelText: "Cancel",
    tone: "danger",
  });
  if (!confirmed) {
    setActionStatus("Deletion cancelled.");
    return;
  }

  try {
    setBusy("delete", "Deleting task...", targetTask.id);
    setActionStatus("Deleting task...", "busy");
    renderAll();
    await api(taskPurgeApiBase(targetTask), { method: "DELETE" });
    if (selectedTaskId === targetTask.id) {
      selectedTaskId = null;
      selectedTask = null;
      rememberSelectedTaskId(null);
    }
    resultScrollPositionsByTask.delete(targetTask.id);
    persistResultScrollPositions();
    await refreshTasks();
    renderStoredStateSummaries();
    await loadReportFields();
    setActionStatus("Task deleted.", "success");
  } catch (error) {
    setActionStatus(error.message || "Could not delete the task.", "error");
  } finally {
    setBusy(null, "", targetTask.id);
    renderAll();
  }
}

async function runAction(action, options = {}) {
  const actionId = options.actionId || null;
  const taskScoped = options.taskScoped !== false;
  const taskId = Object.prototype.hasOwnProperty.call(options, "taskId")
    ? options.taskId
    : selectedTaskId;
  let shouldRenderAfter = options.renderAfter !== false;
  try {
    if (actionId && taskScoped) setBusy(actionId, options.busyText || "Processing...", taskId);
    await action();
  } catch (error) {
    shouldRenderAfter = true;
    if (error?.name === "AbortError") {
      if (actionId && taskScoped) setActionStatus(actionCancelledStatusTitle(actionId), "success");
      return;
    }
    if (selectedTaskId && taskScoped) {
      try {
        await refreshTasks();
      } catch (_) {
        // Keep the original action error visible when status refresh also fails.
      }
    }
    const message = error.message || "Operation failed";
    if (actionId === "agentMemory") setAgentMemoryStatus(message, "error");
    if (actionId === "draftTools") setDraftToolsStatus(message, "error");
    if (actionId && taskScoped) renderActionError(actionId, message);
    if (actionId && taskScoped) setActionStatus(actionFailureStatusTitle(actionId), "error", message);
    else if (!actionId) setCreateStatus(message, "error");
  } finally {
    if (actionId && taskScoped) setBusy(null, "", taskId);
    if (shouldRenderAfter) renderAll();
  }
}

function handleTaskListKeydown(event) {
  if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
  const rows = Array.from(document.querySelectorAll(".task-row"));
  if (rows.length === 0) return;
  event.preventDefault();
  const currentIndex = rows.indexOf(document.activeElement);
  const nextIndex = event.key === "ArrowDown"
    ? Math.min(rows.length - 1, currentIndex + 1)
    : Math.max(0, currentIndex - 1);
  rows[nextIndex < 0 ? 0 : nextIndex].focus();
}

async function copyText(text) {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    setActionStatus("Path copied.", "success");
  } catch (_) {
    setActionStatus("Browser does not allow automatic copying. Please select the path manually.", "error");
  }
}

function closeSidebarSettingsOnOutsideClick(event) {
  const settings = $("sidebarSettings");
  if (!settings?.open) return;
  const target = event.target;
  if (target instanceof Element && target.closest("#sidebarSettings")) return;
  settings.open = false;
}

function openGovernanceSettingsFromSidebar() {
  closeSidebarSettingsMenu();
  scheduleGovernanceSettingsFromSidebar();
}

function handleGovernanceSettingsPointerDown(event) {
  event.preventDefault();
  event.stopPropagation();
  closeSidebarSettingsMenu();
  scheduleGovernanceSettingsFromSidebar();
}

function workflowActionConfig(actionId) {
  if (actionId === "scan") {
    return { action: scanCurrentTask, busyText: "Scanning files..." };
  }
  if (actionId === "notebook") {
    return { action: validateCurrentTask, busyText: "Running validation..." };
  }
  if (actionId === "cancelNotebook") {
    return { action: cancelCurrentNotebook, busyText: "StoppingNotebook..." };
  }
  if (actionId === "metrics") {
    return { action: generateMetrics, busyText: "Generating metrics and Excel analysis..." };
  }
  if (actionId === "cancelMetrics") {
    return { action: cancelCurrentMetrics, busyText: "Stopping indicator generation..." };
  }
  if (actionId === "report") {
    return { action: generateReport, busyText: "Generating Word report..." };
  }
  if (actionId === "cancelReport") {
    return { action: cancelCurrentReport, busyText: "Stopping report generation..." };
  }
  if (actionId === "downloadWordReport") {
    return { action: downloadWordReport, busyText: "" };
  }
  if (actionId === "downloadExcelAnalysis") {
    return { action: downloadExcelAnalysis, busyText: "" };
  }
  if (actionId === "previewWordReport") {
    return { action: previewWordReport, busyText: "Opening Word preview..." };
  }
  return null;
}

function scrollStepTarget(targetId) {
  if (!targetId) return;
  $(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function scrollToManualWorkflowSection(stepId) {
  if (!stepId) return;
  // Agent mode owns its own scroll behavior (follow-the-stream); reusing
  // the manual jump there would fight the typewriter auto-scroll.
  if (selectedTaskIsAgentMode()) return;
  const step = workflowSteps.find((candidate) => candidate.id === stepId);
  if (!step?.target) return;
  // Capture the task id at scheduling time so a deferred-frame scroll does
  // not jump the panel to the wrong section after the user switched tasks
  // mid-action.
  const targetTaskId = selectedTaskId;
  window.requestAnimationFrame(() => {
    if (selectedTaskId !== targetTaskId) return;
    scrollStepTarget(step.target);
  });
}

function handleWorkflowStepperClick(event) {
  const summary = event.target.closest("[data-validation-stage-expansion] > summary");
  if (summary) {
    const details = summary.parentElement;
    expandedValidationStages.set(details.dataset.validationStageExpansion, !details.open);
    return;
  }
  if (planRailController.handleClick(event)) return;
  const actionButton = event.target.closest("[data-step-action]");
  if (actionButton) {
    event.preventDefault();
    event.stopPropagation();
    const actionId = actionButton.dataset.stepAction;
    const config = workflowActionConfig(actionId);
    if (config) runAction(config.action, { actionId, busyText: config.busyText });
    return;
  }
  const step = event.target.closest(".step[data-step-target]");
  if (step) scrollStepTarget(step.dataset.stepTarget);
}

function handleWorkflowStepperKeydown(event) {
  if (event.target.closest("[data-validation-stage-expansion] > summary")) return;
  if (!["Enter", " "].includes(event.key)) return;
  const step = event.target.closest(".step[data-step-target]");
  if (!step || event.target.closest("[data-step-action]")) return;
  event.preventDefault();
  scrollStepTarget(step.dataset.stepTarget);
}

$("createTaskOpenButton").onclick = openTaskTypeWelcome;
$("configureAgentModelButton").onclick = openLLMSettingsDialog;
$("createConfigureAgentModelButton").onclick = openLLMSettingsDialog;
$("collapsedCreateTaskButton").onclick = openTaskTypeWelcome;
$("welcomeTaskCards").onclick = openTaskDialogFromCard;
$("closeTaskDialogButton").onclick = closeTaskDialog;
$("openGovernanceSettingsButton").addEventListener("pointerdown", handleGovernanceSettingsPointerDown, true);
$("openGovernanceSettingsButton").onclick = openGovernanceSettingsFromSidebar;
$("closeGovernanceSettingsButton").onclick = closeGovernanceSettingsDialog;
$("governanceSettingsDialog").addEventListener("click", handleGovernanceSettingsNavClick);
$("governanceSettingsDialog").addEventListener("change", handleMemoryPolicyChange);
$("governanceSettingsSearch").oninput = handleGovernanceSettingsSearch;
$("governanceRefreshButton").onclick = refreshActiveGovernancePanel;
$("closeWordPreviewButton").onclick = closeWordPreviewDialog;
$("refreshExecutionEnvironmentOptionsButton").onclick = refreshExecutionEnvironmentOptions;
$("executionEnvironmentList").addEventListener("click", handleExecutionEnvironmentListClick);
$("executionEnvironmentList").addEventListener("keydown", handleExecutionEnvironmentListKeydown);
$("notebookMemoryLimitInput").addEventListener("change", handleNotebookMemoryLimitChange);
$("addLLMModelButton").onclick = addLLMModelProfile;
$("closeLLMEngineEditButton").onclick = closeLLMEngineEdit;
$("cancelLLMEngineEditButton").onclick = closeLLMEngineEdit;
$("saveLLMEngineEditButton").onclick = () =>
  runAction(saveLLMEngineEdit, { actionId: "llmSettings", busyText: "Saving model...", taskScoped: false });
$("testLLMEngineConnectionButton").onclick = testLLMEngineConnection;
$("sidebarCollapseButton").onclick = toggleSidebarCollapsed;
$("sidebarBackdrop").onclick = () => applySidebarCollapsed(true);
window.matchMedia("(max-width: 860px)").addEventListener("change", (event) => {
  if (event.matches) applySidebarCollapsed(true);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && window.matchMedia("(max-width: 860px)").matches && !document.querySelector("dialog[open]")) applySidebarCollapsed(true);
});
$("sidebarBrandTrigger").onclick = expandSidebarFromBrand;
$("sidebarBrandTrigger").onkeydown = handleSidebarBrandKeydown;
$("createTaskButton").onclick = () =>
  runAction(createTaskAndScan);
$("workflowStepper").onclick = handleWorkflowStepperClick;
$("workflowStepper").onkeydown = handleWorkflowStepperKeydown;
// The editable "Try again after editing parameters" form now lives in the middle workspace
// (#planRetryPanel), not the rail. Route its clicks (submit / schema fields)
// through the same plan-rail controller handler so retryPlanStep runs.
$("planRetryPanel").onclick = (event) => {
  planRailController.handleClick(event);
};
$("taskSearchInput").oninput = (event) => {
  taskSearchQuery = event.target.value;
  renderTaskList();
};
$("taskSearchToggle").onclick = toggleTaskSearch;
$("taskSearchClose").onclick = () => closeTaskSearch({ focusToggle: true });
$("searchScrim").onclick = () => closeTaskSearch({ focusToggle: true });
$("taskList").addEventListener("click", () => closeTaskSearch());
bindTaskRowPreview({
  list: $("taskList"),
  preview: $("taskRowPreview"),
  sidebar: document.querySelector(".task-sidebar"),
  getTask: (taskId) => taskCache.find((task) => task.id === taskId) || null,
  displayName: taskDisplayName,
  typeLabel: taskTypeLabel,
  ownerLabel: (task) => taskTypeDefinition(task.task_type).validatorLabel || "Head",
});
$("settingsMenu").onchange = handleSettingsMenuChange;
$("agentMemoryList").addEventListener("click", handleAgentMemoryListClick);
document.addEventListener("click", handleAgentMemoryInlineInspect);
$("refreshAgentMemoryButton").onclick = () =>
  runAction(loadAgentMemoryItems, { actionId: "agentMemory", busyText: "Loading task memories...", taskScoped: false });
$("draftManageDetails").addEventListener("toggle", (event) => {
  if (event.target.open && !draftToolsPanel.hasLoaded()) {
    runAction(loadDraftTools, { actionId: "draftTools", busyText: "Loading draft tool...", taskScoped: false });
  }
});
$("draftStatusFilter").onchange = () =>
  runAction(loadDraftTools, { actionId: "draftTools", busyText: "Loading draft tool...", taskScoped: false });
$("draftToolsList").addEventListener("click", handleDraftToolsListClick);
$("draftToolsList").addEventListener("keydown", handleDraftToolsListKeydown);
$("runDraftButton").onclick = () =>
  runAction(runDraftTool, { actionId: "draftTools", busyText: "Testing draft tool...", taskScoped: false });
$("promoteDraftButton").onclick = () =>
  runAction(promoteDraftTool, { actionId: "draftTools", busyText: "Approving draft tool...", taskScoped: false });
$("rejectDraftButton").onclick = () =>
  runAction(rejectDraftTool, { actionId: "draftTools", busyText: "Rejecting draft tool...", taskScoped: false });
$("llmModelProfiles").addEventListener("click", (event) => {
  const removeButton = event.target.closest("[data-llm-remove]");
  if (removeButton) {
    event.preventDefault();
    event.stopPropagation();
    runAction(() => removeLLMModelProfile(Number(removeButton.dataset.llmRemove)), {
      actionId: "llmSettings",
      busyText: "Deleting model...",
      taskScoped: false,
    });
    return;
  }
  const editItem = event.target.closest("[data-llm-edit]");
  if (editItem) openLLMEngineEdit(Number(editItem.dataset.llmEdit));
});
$("llmModelProfiles").addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const editItem = event.target.closest("[data-llm-edit]");
  if (!editItem) return;
  event.preventDefault();
  openLLMEngineEdit(Number(editItem.dataset.llmEdit));
});
$("agentModelSelect").onchange = (event) => {
  agentSelectedModelId = event.target.value;
  setAgentComposerNotice("");
  persistCurrentAgentComposerPreference({ model_id: agentSelectedModelId });
  event.target.blur();
};
$("agentEffortSelect").onchange = (event) => {
  agentSelectedEffort = normalizeAgentEffort(event.target.value);
  event.target.value = agentSelectedEffort;
  persistCurrentAgentComposerPreference({ effort: agentSelectedEffort });
  event.target.blur();
};
$("agentAcceptanceModeSelect").onchange = (event) => {
  const previousMode = agentAcceptanceMode;
  agentAcceptanceMode = normalizeAgentAcceptanceMode(event.target.value);
  event.target.value = agentAcceptanceMode;
  renderAgentAcceptanceModePreference();
  persistCurrentAgentComposerPreference({ acceptance_mode: agentAcceptanceMode });
  // Phase 0B: AUTO only operates low-risk nodes.  Mandatory business decisions
  // and effect authorizations always stay with the local human principal.
  if (agentAcceptanceMode === "auto_accept" && previousMode !== "auto_accept") {
    setAgentComposerNotice("Automatic mode handles low-risk steps. Business decisions and actions that change data or systems still require your confirmation.", "info");
  }
  event.target.blur();
};

// Per-task overrides take precedence; without a selected task the change
// belongs in the global preference store (used as the seed for new tasks).
function persistCurrentAgentComposerPreference(patch) {
  if (selectedTaskId) {
    updateAgentTaskComposerOverride(selectedTaskId, patch);
  } else {
    saveAgentComposerPreferences();
  }
}
function blurChipSelectIfFocused() {
  const focused = document.activeElement;
  if (!focused) return;
  if (!agentComposerSelectIds.includes(focused.id)) return;
  focused.blur();
}
const agentComposerSelectIds = ["agentAcceptanceModeSelect", "agentModelSelect", "agentEffortSelect"];
document.addEventListener(
  "mousedown",
  (event) => {
    const focused = document.activeElement;
    if (!focused) return;
    if (!agentComposerSelectIds.includes(focused.id)) return;
    const chip = focused.closest(".agent-composer-chip");
    if (chip && !chip.contains(event.target)) focused.blur();
  },
  true,
);
window.addEventListener("focus", () => {
  setTimeout(blurChipSelectIfFocused, 0);
});
for (const id of agentComposerSelectIds) {
  $(id).addEventListener("keyup", (event) => {
    if (event.key === "Escape") event.currentTarget.blur();
  });
}
$("riskMaterialUploadButton").onclick = () => {
  if (
    (
      !selectedTaskIsRiskAnalysisAgent()
      && !selectedTaskNeedsManualRiskIntake()
    )
    || taskBusyAction(selectedTaskId) === "agent"
  ) return;
  $("riskMaterialUploadInput")?.click();
};
$("riskMaterialUploadInput").addEventListener("change", (event) => {
  const files = event.currentTarget.files;
  if (!files?.length) return;
  runAction(
    () => uploadRiskAnalysisMaterials(files),
    { actionId: "agent", busyText: "Uploading and checking risk analysis files..." },
  );
});
$("sendAgentMessageButton").onclick = () => {
  if (agentSendIsStopMode()) {
    runAction(stopAgentValidation, {
      actionId: "agent",
      busyText: "Stopping agent...",
      taskId: workbenchTaskId(),
    });
    return;
  }
  runAction(startAgentValidation, {
    actionId: "agent",
    busyText: "Agent working...",
    taskId: workbenchTaskId(),
  });
};
$("agentComposerInput").addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  if (agentSendIsStopMode()) {
    const content = event.currentTarget.value.trim();
    if (!agentComposerStopIntent(content)) {
      setAgentComposerNotice("Agent is running. Enter Stop current action and press Enter to stop it.", "info");
      return;
    }
    runAction(
      () => stopAgentValidationByMessage(content),
      { actionId: "agent", busyText: "Stopping agent..." },
    );
    return;
  }
  if ($("sendAgentMessageButton")?.disabled) return;
  runAction(startAgentValidation, {
    actionId: "agent",
    busyText: "Agent working...",
    taskId: workbenchTaskId(),
  });
});
$("agentComposerInput").addEventListener("input", () => {
  autoGrowComposerInput();
  updateAgentSendDisabled();
});

function autoGrowComposerInput() {
  const input = $("agentComposerInput");
  if (!input) return;
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  requestAnimationFrame(syncAgentComposerClearance);
}

function agentSendIsStopMode() {
  return Boolean(selectedTaskIsAgentMode() && (
    taskBusyAction(selectedTaskId) === "agent"
    || taskBusyAction(workbenchTaskId()) === "agent"
  ));
}

function agentComposerStopIntent(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) return false;
  const negated = [
    "Don't stop.", "Don't stop.", "There's no need to stop.", "Don't stop.", "Don't stop.",
    "Don't cancel.", "No need to cancel.", "Don't cancel.", "Don't cancel it yet.", "Do not abort", "Don't interrupt.",
  ];
  if (negated.some((phrase) => text.includes(phrase))) return false;
  if (/[??]|Why?|Why?|What?|How's that?|Is it possible?|Did you?|Did you stop?|Did you stop?/.test(text)) return false;
  if (/(?:(?:Present.|Wait.|- Wait.|Run To|Execute To).{1,40}(?:Location|Back|Time)?|Yes..{1,40}(?:Location|Time))(?:Stop|Stop!|Pause|Abort)/.test(text)) return false;
  return [
    "Stop", "Stop!", "Termination", "Abort", "Cancel", "Stop!", "Don't run.",
    "stop", "cancel", "abort", "terminate",
  ].some((keyword) => text.includes(keyword));
}

function renderAgentSendButtonState() {
  const button = $("sendAgentMessageButton");
  if (!button) return false;
  const stopMode = agentSendIsStopMode();
  button.dataset.agentSendState = stopMode ? "stop" : "send";
  button.setAttribute("aria-label", stopMode ? "Stop the current agent action" : "Send Message");
  button.title = stopMode ? "Stop the current agent action" : "";
  return stopMode;
}

// Send is disabled until the user has typed something; while Agent is running,
// the same control becomes an always-enabled stop button.
function updateAgentSendDisabled() {
  const input = $("agentComposerInput");
  const button = $("sendAgentMessageButton");
  if (!input || !button) return;
  const stopMode = renderAgentSendButtonState();
  button.disabled = stopMode ? false : !input.value.trim();
}

updateAgentSendDisabled();

function agentEffort() {
  agentSelectedEffort = normalizeAgentEffort($("agentEffortSelect")?.value || agentSelectedEffort);
  return agentSelectedEffort;
}

function agentAcceptanceModeValue() {
  agentAcceptanceMode = normalizeAgentAcceptanceMode($("agentAcceptanceModeSelect")?.value || agentAcceptanceMode);
  return agentAcceptanceMode;
}
bindRunModeDeselectableCards();
validationBatchCreateController.bind();
bindDialogBackdropDismissal();
bindPlatformConfirmDialog();
materialBindingDialog.bind();
strategyCandidateLabController.bind(document);
mountGovernanceExtensions();
onSelectedTierChange(syncCreateTaskTierDefault);
createTaskDialog.bindMaterialSourceControls();
const pet = $("petCompanion");
if (pet) pet.addEventListener("pointerdown", startPetDrag);
$("leftResizeHandle").onpointerdown = (event) => startResizeDrag("left", event);
$("rightResizeHandle").onpointerdown = (event) => startResizeDrag("right", event);
$("leftResizeHandle").onkeydown = (event) => handleResizeKey("left", event);
$("rightResizeHandle").onkeydown = (event) => handleResizeKey("right", event);
$("resultScrollContent").addEventListener("scroll", handleResultScroll, { passive: true });
document.addEventListener("wheel", routeWorkspaceWheelToResult, { passive: false });
// Note real user-driven scroll inputs so recomputeAgentAutoScrollFollow can
// distinguish them from typewriter/restore-driven programmatic scrolls.
document.addEventListener("wheel", noteAgentUserScrollInput, { passive: true });
document.addEventListener("touchstart", noteAgentUserScrollInput, { passive: true });
document.addEventListener("touchmove", noteAgentUserScrollInput, { passive: true });
window.addEventListener("resize", syncTaskHeroGlassLayout);

$("taskHero")?.addEventListener("click", handleTaskHeroToggle);
// Re-measure once the fold animation settles so scroll padding and the glass
// tint reflect the hero's final height, not its mid-transition height.
$("taskHeroDetails")?.addEventListener("transitionend", () => syncTaskHeroGlassLayout());

$("taskList").onkeydown = handleTaskListKeydown;

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && taskSearchIsActive()) {
    closeTaskSearch({ focusToggle: true });
    return;
  }
  if (
    event.key === "Enter" &&
    event.target.closest("#taskDialog") &&
    event.target.tagName !== "TEXTAREA" &&
    !event.isComposing
  ) {
    event.preventDefault();
    runAction(createTaskAndScan);
  }
});

document.addEventListener("click", (event) => {
  const copyButton = event.target.closest("[data-copy]");
  if (copyButton) {
    event.preventDefault();
    copyText(copyButton.dataset.copy);
  }
});
document.addEventListener("click", closeSidebarSettingsOnOutsideClick);

installFormControlFocusRingGuard();
themeController.restoreTheme();
themeController.watchSystemTheme();
restoreTaskListSettings();
petCatalog.populateSelect($("settingsPetSelect"), document);
restorePetPreference();
restorePetPosition();
restoreLayoutWidths();
restoreSidebarCollapsed();
updateWorkspaceGreeting();
setInterval(updateWorkspaceGreeting, 60 * 1000);
renderSettingsState();
loadBranding();
loadExecutionEnvironmentSettings({ silent: true });
loadLLMSettings({ silent: true });
loadResultScrollPositions();
selectedTaskId = preferredStartupTaskId(
  initialTaskDeepLink,
  storedSelectedTaskId(),
) || null;
restoreSelectedTaskPlaceholder();
if (selectedTaskId) rememberSelectedTaskId(selectedTaskId);
else rememberSelectedTaskId(null);
renderCurrentTask({ force: true });
renderMetricPreview({});
renderStoredStateSummaries();
initializeApp();

function enableAppAnimationsAfterBoot() {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document.body.classList.add("anim-ready");
    });
  });
}

function finishAppBoot() {
  document.body.classList.remove("app-booting");
  enableAppAnimationsAfterBoot();
}

async function initializeApp() {
  let ready = false;
  try {
    await refreshTasks();
    await reloadDataWorkspace(selectedTaskId, { silent: true });
    const validationBatchLoadPromise = validationBatchPanelController.selectTask(selectedTask);
    const candidateLabLoadPromise = strategyCandidateLabController.selectTask(selectedTask);
    renderStoredStateSummaries();
    await loadReportFields();
    await loadTaskEvidence();
    await loadAgentMessages();
    await validationBatchLoadPromise;
    await candidateLabLoadPromise;
    ready = true;
  } catch (error) {
    const detail = error?.message || "";
    setActionStatus("Cannot connect to Risk Studio. Check that the service is running and try again.", "error", detail);
    setCreateStatus(detail || "Cannot connect to Risk Studio. Check that the service is running and try again.", "error");
  } finally {
    renderAll();
    await restoreResultScrollPositionAfterRender(selectedTaskId);
    validationBatchPanelController.focusRequestedItem();
    finishAppBoot();
  }
  if (ready) maybeResumeAgentValidationBatch();
}
