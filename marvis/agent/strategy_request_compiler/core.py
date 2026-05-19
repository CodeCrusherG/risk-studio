"""core request-compiler handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations

# imports for names re-exported by the original module __all__
from marvis.agent.strategy_workflows import LEGACY_REPLAY_STANDARD_STRATEGY_WORKFLOWS  # noqa: F401, F811
from marvis.agent.strategy_workflows._univariate_scorecard import UNIVARIATE_BINNING_METHODS  # noqa: F401, F811
from marvis.agent.strategy_workflows._univariate_scorecard import UNIVARIATE_REFINEMENT_METHODS  # noqa: F401, F811
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
import json
import logging
import math
import re
from types import MappingProxyType
from typing import Any
from marvis.agent.json_reply import load_json_object
from marvis.agent.strategy_workflows import FRESH_STANDARD_STRATEGY_WORKFLOWS, REPLAYABLE_STANDARD_STRATEGY_WORKFLOWS, StrategyWorkflowResolutionContext, StrategyWorkflowResolutionMode, StrategyWorkflowValidationError, migrated_workflow_confirmation, resolve_strategy_request as resolve_standard_strategy_workflow
from marvis.llm_prompts import SAMPLE_DESIGN_V2_CORRECTION_SYS, STRATEGY_REQUEST_COMPILER_SYS
from marvis.packs.strategy.candidate_design import CANDIDATE_DESIGN_SCHEMA_VERSION, CandidateDesignError, normalize_candidate_design, normalize_candidate_economics_inputs
from marvis.packs.strategy.dsl import parse_strategy_spec
from marvis.packs.strategy.errors import StrategyError
from marvis.strategy_adoption import AdoptionReasonError, normalize_adoption_reason

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import SAMPLE_DESIGN_V2_CORRECTION_JSON_SCHEMA
    from . import _AUTOMATIC_TREE_APPLY_TARGET_RE
    from . import _AUTOMATIC_TREE_BEST_LEAF_RE
    from . import _AUTOMATIC_TREE_COLUMN_ROLE_LABELS
    from . import _AUTOMATIC_TREE_DECISION_ARTIFACT_RE
    from . import _AUTOMATIC_TREE_DECISION_EFFECT_RE
    from . import _AUTOMATIC_TREE_DIRECTION_GROUNDING
    from . import _AUTOMATIC_TREE_FOLLOW_UP_ACTION_ANCHOR_RE
    from . import _AUTOMATIC_TREE_HEURISTIC_LEAF_FOLLOW_UP_RE
    from . import _AUTOMATIC_TREE_LEAF_DECISION_FOLLOW_UP_RE
    from . import _AUTOMATIC_TREE_LEAF_FOLLOW_UP_RE
    from . import _AUTOMATIC_TREE_LEAF_ID_WRITEBACK_RE
    from . import _AUTOMATIC_TREE_LEAF_TOKEN_RE
    from . import _AUTOMATIC_TREE_LIFECYCLE_FOLLOW_UP_RE
    from . import _AUTOMATIC_TREE_MULTI_STEP_RE
    from . import _AUTOMATIC_TREE_NODE_EXTRACT_FOLLOW_UP_RE
    from . import _AUTOMATIC_TREE_NODE_RANK_FOLLOW_UP_RE
    from . import _AUTOMATIC_TREE_NODE_SELECT_FOLLOW_UP_RE
    from . import _AUTOMATIC_TREE_NUMBER_LABELS
    from . import _AUTOMATIC_TREE_POOL_FOLLOW_UP_RE
    from . import _AUTOMATIC_TREE_REVERSED_BEST_LEAF_RE
    from . import _POOL_ACTION_GROUNDING
    from . import _VOTING_COMMAND_CLAUSE_RE
    from . import _VOTING_SEARCH_INTENT_RE
    from . import _VOTING_SUBJECT_RE
    from . import _automatic_tree_column_mentions
    from . import _automatic_tree_feature_span_is_negated
    from . import _automatic_tree_follow_up_action_is_negated
    from . import _automatic_tree_follow_up_clauses
    from . import _automatic_tree_number_values
    from . import _automatic_tree_segment
    from . import _automatic_tree_span_is_negated
    from . import _automatic_tree_span_overlaps_columns
    from . import _automatic_tree_value_is_replaced
    from . import _ground_refinement_request
    from . import _voting_search_text_has_positive_follow_up
    from . import utterance_targets_strategy_sample_design

_SYSTEM = STRATEGY_REQUEST_COMPILER_SYS.text

logger = logging.getLogger(__name__)

STRATEGY_OPERATIONS = (
    "develop",
    "analyze",
    "backtest",
    "apply",
    "compare",
    "adopt",
    "report",
    "monitor",
    "mine_rules",
)

STRATEGY_TYPES = (
    "approval",
    "reject",
    "limit",
    "pricing",
    "segmentation",
)

STRATEGY_REQUEST_KINDS = (
    "strategy_lifecycle",
    "standard_workflow",
)

STANDARD_STRATEGY_WORKFLOWS = FRESH_STANDARD_STRATEGY_WORKFLOWS

AUTOMATIC_TREE_DIRECTIONS = (
    "increasing",
    "decreasing",
    "unordered",
)

_CANDIDATE_STABILITY_ASSET_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])candidate-asset-[0-9a-f]{32}(?![A-Za-z0-9_-])"
)

_CANDIDATE_STABILITY_POOL_ENTRY_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])pool-entry-[0-9a-f]{32}(?![A-Za-z0-9_-])"
)

_CANDIDATE_STABILITY_SUBJECT_RE = re.compile(
    r"(?:Candidates(?:Assets|Rule)?|Policy pool(?:Entry|Rule)|Pool\s*(?:entry|Entry)|"
    r"candidate(?:\s+asset)?|candidate-asset-|pool-entry-)",
    re.IGNORECASE,
)

_CANDIDATE_STABILITY_MEASUREMENT_RE = re.compile(
    r"(?:Month by Month|Monthly|Month|Multi-moon)[^;;..!??\n]{0,40}"
    r"(?:Stability|Distribution stable|PSI)|"
    r"(?:Stability|Distribution stable|PSI)[^;;..!??\n]{0,40}"
    r"(?:Month by Month|Monthly|Month|Multi-moon)|"
    r"(?<![A-Za-z0-9_])monthly[^;.!?\n]{0,40}"
    r"(?:stability|PSI)|"
    r"(?<![A-Za-z0-9_])(?:stability|PSI)[^;.!?\n]{0,40}"
    r"monthly(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CANDIDATE_STABILITY_ACTION_RE = re.compile(
    r"(?:Do it.|Calculate|Measurement|Analysis|Evaluation|Inspection|Generate|View)|"
    r"(?<![A-Za-z0-9_])(?:compute|calculate|measure|analy[sz]e|"
    r"assess|evaluate|check|build|show)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CANDIDATE_STABILITY_NOT_AUTHORIZED_RE = re.compile(
    r"[??]|(?:Don't.|No, I'm fine.|No need.|Don't.|Ban|Cancel|Not yet.|Not yet.|"
    r"Can you...|Can I?|Is it possible?|Is that okay?|Can you...|How's that?|What?|What?|Assumptions|Suppose...|If|"
    r"Later|The future.|In the future|Later.|Tomorrow.|Next week.|Next month|Before|Before|Go on.|Last time.)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cancel|can\s+you|"
    r"could\s+you|would\s+you|how\s+to|what\s+if|later|tomorrow|"
    r"previously|in\s+the\s+future)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CANDIDATE_STABILITY_SECOND_OPERATION_RE = re.compile(
    r"(?:Into the pool.|Add(?:Policy)?Ji.|Delete|Remove|Changes|Reorder|Compile|"
    r"Write back|Back up.|Generate Report|Form a report|Report.|Accepted|Adopt|Deployment|Online.|Production)|"
    r"(?<![A-Za-z0-9_])(?:add\s+to\s+(?:the\s+)?(?:strategy\s+)?pool|"
    r"remove|delete|reorder|compile|write[-\s]*back|"
    r"generate\s+(?:a\s+)?report|adopt|deploy|go[-\s]?live)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CANDIDATE_STABILITY_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:source_kind|source_artifact_id|"
    r"expected_(?:artifact_)?content_hash|expected_asset_(?:id|hash)|"
    r"expected_pool_(?:revision|snapshot_hash)|dataset_id|"
    r"expected_dataset_content_hash|workspace_(?:revision|generation)|"
    r"analysis_generation|semantic_mapping_hash|sample_design_ref|"
    r"target_col|month_col)(?![A-Za-z0-9_])|"
    r"(?:artifact|Dataset|workspace|Workspace|Sample design|Month)"
    r"\s*(?:ID|id|hash|Hash.|revision|Version|Fields|Columns)\s*(?:=|:|:)",
    re.IGNORECASE,
)

_STRATEGY_REPLY_MAX_CHARS = 100_000

_STRATEGY_REPLY_MAX_DEPTH = 64

_STRATEGY_REPLY_MAX_NODES = 10_000

_STRATEGY_POOL_WORKFLOWS = frozenset(
    {
        "strategy_pool_add_candidate",
        "strategy_pool_remove_entry",
        "strategy_pool_set_action",
        "strategy_pool_reorder",
        "strategy_pool_compile",
    }
)

_STRATEGY_POOL_MEASUREMENT_WORKFLOWS = frozenset({"strategy_pool_impact"})

_STRATEGY_POOL_APPLY_WORKFLOWS = frozenset({"strategy_pool_apply"})

_STRATEGY_POOL_MATERIALIZE_WORKFLOWS = frozenset(
    {"strategy_pool_materialize"}
)

_STRATEGY_POOL_VALIDATION_WORKFLOWS = frozenset(
    {"strategy_pool_validation"}
)

_REFINEMENT_SELECTION_ACTION_RE = re.compile(
    r"(?:Selection|Select|Reservations|Filter|As|select|keep|retain)", re.IGNORECASE
)

_REFINEMENT_MERGE_ACTION_RE = re.compile(r"(?:Merge|Side box|merge|combine)", re.IGNORECASE)

_RISK_THRESHOLD_EXPRESSION_RE = re.compile(
    r"(?:Observations)?(?:Bad rate|Bad debt rate|Risk rate|bad\s*rate|risk\s*rate)"
    r"\s*(?:Yes|Yes.|Yes|Yes.|Reactions|must\s+be|is)?\s*"
    r"(?P<operator>greater than or equal to|No less than|At least.|Not less than|Achieved|>=|≥|"
    r"less than or equal to|Not higher|Up to|Most|<=|≤|"
    r"Greater than|Higher|More than|>|less than|Less than|Less than|<|"
    r"greater\s+than\s+or\s+equal(?:\s+to)?|at\s+least|"
    r"less\s+than\s+or\s+equal(?:\s+to)?|at\s+most|"
    r"more\s+than|greater\s+than|less\s+than)"
    r"\s*(?P<value>Percent\s*[0-9]+(?:\.[0-9]+)?|"
    r"[0-9]+(?:\.[0-9]+)?\s*%|"
    r"(?:0(?:\.\d+)?|1(?:\.0+)?))",
    re.IGNORECASE,
)

_OPTIONAL_DRAFT_FIELDS = {
    "objective",
    "max_bad_rate",
    "min_approval_rate",
    "baseline_strategy_id",
    "strategy_id",
    "adoption_reason",
    "profit",
    "economics_inputs",
    "candidate_design",
    "strategy_spec",
}

_DRAFT_FIELDS = {"operation", "strategy_type"} | _OPTIONAL_DRAFT_FIELDS

_LIFECYCLE_DRAFT_FIELDS = _DRAFT_FIELDS | {"request_kind"}

_STANDARD_WORKFLOW_DRAFT_FIELDS = {
    "request_kind",
    "workflow",
    "workflow_inputs",
}

_PROFIT_FIELDS = {
    "ead_col",
    "pd_col",
    "annual_rate",
    "funding_rate",
    "lgd",
    "operating_cost_per_loan",
    "term_months",
}

_LIMIT_ECONOMICS_NAMES = ("pd", "lgd", "utilization")

_PRICING_ECONOMICS_NAMES = (
    "ead",
    "pd",
    "lgd",
    "funding_rate",
    "term_months",
    "operating_cost_per_loan",
)

_ECONOMICS_VALUE_MAXIMUMS = {
    "pd": 1.0,
    "lgd": 1.0,
    "utilization": 1.0,
    "funding_rate": 1.0,
}

_ECONOMICS_LABELS = {
    "ead": "EAD",
    "pd": "PD",
    "lgd": "LGD",
    "utilization": "Amount utilization",
    "funding_rate": "Cost of funds",
    "term_months": "Duration",
    "operating_cost_per_loan": "Single operating cost",
}

_CJK_RE = re.compile(r"[\u3400-\u9fff]")

_COLLECTION_STRATEGY_RE = re.compile(
    r"(?:Recover.|\bcollection(?:s)?(?:\s+|[-_])"
    r"(?:strategy|actions?|allocation|policy|workflow|campaign|frequency)\b)",
    re.IGNORECASE,
)

_NON_REPAIRABLE_CLARIFICATION_CODES = frozenset(
    {
        "candidate_economics_ambiguous",
        "candidate_economics_incomplete",
        "candidate_requires_observed_economics",
        "strategy_report_bundle_v2_platform_binding_forbidden",
        "strategy_dsl_delivery_platform_binding_forbidden",
        "strategy_request_too_complex",
    }
)

_CANDIDATE_DESIGN_JSON_SCHEMA = {
    "type": "object",
    "oneOf": [
        {
            "properties": {
                "schema_version": {"const": CANDIDATE_DESIGN_SCHEMA_VERSION},
                "method": {"const": "score_band_limit"},
                "score_col": {"type": "string", "minLength": 1},
                "n_bands": {"type": "integer", "minimum": 2, "maximum": 20},
                "limit_grid": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "uniqueItems": True,
                    "items": {"type": "number", "exclusiveMinimum": 0},
                },
                "max_expected_loss_per_account": {
                    "type": "number",
                    "minimum": 0,
                },
                "missing_policy": {"const": "zero_limit"},
            },
            "required": [
                "method",
                "score_col",
                "limit_grid",
                "max_expected_loss_per_account",
            ],
            "additionalProperties": False,
        },
        {
            "properties": {
                "schema_version": {"const": CANDIDATE_DESIGN_SCHEMA_VERSION},
                "method": {"const": "score_band_pricing"},
                "score_col": {"type": "string", "minLength": 1},
                "n_bands": {"type": "integer", "minimum": 2, "maximum": 20},
                "rate_grid": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "uniqueItems": True,
                    "items": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "min_roa": {"type": "number", "minimum": 0, "maximum": 1},
                "missing_policy": {"const": "highest_risk_rate"},
            },
            "required": ["method", "score_col", "rate_grid"],
            "additionalProperties": False,
        },
        {
            "properties": {
                "schema_version": {"const": CANDIDATE_DESIGN_SCHEMA_VERSION},
                "method": {"const": "single_variable_segmentation"},
                "feature_col": {"type": "string", "minLength": 1},
                "n_bands": {"type": "integer", "minimum": 2, "maximum": 20},
                "missing_policy": {"const": "separate_segment"},
            },
            "required": ["method", "feature_col"],
            "additionalProperties": False,
        },
    ],
}

STRATEGY_REQUEST_JSON_SCHEMA = {
    "name": "strategy_request_draft",
    "strict": False,
    "schema": {
        "type": "object",
        "properties": {
            "request_kind": {
                "type": "string",
                "enum": list(STRATEGY_REQUEST_KINDS),
            },
            "operation": {"type": "string", "enum": list(STRATEGY_OPERATIONS)},
            "strategy_type": {"type": "string", "enum": list(STRATEGY_TYPES)},
            "objective": {"type": "string", "minLength": 1},
            "max_bad_rate": {"type": "number", "minimum": 0, "maximum": 1},
            "min_approval_rate": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "baseline_strategy_id": {"type": "string", "minLength": 1},
            "strategy_id": {"type": "string", "minLength": 1},
            "adoption_reason": {"type": "string", "minLength": 1},
            "profit": {
                "type": "object",
                "properties": {
                    "ead_col": {"type": "string", "minLength": 1},
                    "pd_col": {"type": "string", "minLength": 1},
                    "annual_rate": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "funding_rate": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "lgd": {"type": "number", "minimum": 0, "maximum": 1},
                    "operating_cost_per_loan": {
                        "type": "number",
                        "minimum": 0,
                    },
                    "term_months": {"type": "integer", "minimum": 1},
                },
                "required": sorted(_PROFIT_FIELDS),
                "additionalProperties": False,
            },
            "economics_inputs": {
                "type": "object",
                "properties": {
                    "ead_col": {"type": "string", "minLength": 1},
                    "ead_value": {"type": "number", "minimum": 0},
                    "pd_col": {"type": "string", "minLength": 1},
                    "pd_value": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "lgd_col": {"type": "string", "minLength": 1},
                    "lgd_value": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "utilization_col": {"type": "string", "minLength": 1},
                    "utilization_value": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "funding_rate_col": {"type": "string", "minLength": 1},
                    "funding_rate_value": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "term_months_col": {"type": "string", "minLength": 1},
                    "term_months_value": {
                        "type": "number",
                        "exclusiveMinimum": 0,
                    },
                    "operating_cost_per_loan_col": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "operating_cost_per_loan_value": {
                        "type": "number",
                        "minimum": 0,
                    },
                },
                "oneOf": [
                    {
                        "allOf": [
                            {
                                "oneOf": [
                                    {"required": ["pd_col"]},
                                    {"required": ["pd_value"]},
                                ]
                            },
                            {
                                "oneOf": [
                                    {"required": ["lgd_col"]},
                                    {"required": ["lgd_value"]},
                                ]
                            },
                            {
                                "oneOf": [
                                    {"required": ["utilization_col"]},
                                    {"required": ["utilization_value"]},
                                ]
                            },
                            {
                                "not": {
                                    "anyOf": [
                                        {"required": ["ead_col"]},
                                        {"required": ["ead_value"]},
                                        {"required": ["funding_rate_col"]},
                                        {"required": ["funding_rate_value"]},
                                        {"required": ["term_months_col"]},
                                        {"required": ["term_months_value"]},
                                        {"required": ["operating_cost_per_loan_col"]},
                                        {"required": ["operating_cost_per_loan_value"]},
                                    ]
                                }
                            },
                        ]
                    },
                    {
                        "allOf": [
                            {
                                "oneOf": [
                                    {"required": ["ead_col"]},
                                    {"required": ["ead_value"]},
                                ]
                            },
                            {
                                "oneOf": [
                                    {"required": ["pd_col"]},
                                    {"required": ["pd_value"]},
                                ]
                            },
                            {
                                "oneOf": [
                                    {"required": ["lgd_col"]},
                                    {"required": ["lgd_value"]},
                                ]
                            },
                            {
                                "oneOf": [
                                    {"required": ["funding_rate_col"]},
                                    {"required": ["funding_rate_value"]},
                                ]
                            },
                            {
                                "oneOf": [
                                    {"required": ["term_months_col"]},
                                    {"required": ["term_months_value"]},
                                ]
                            },
                            {
                                "oneOf": [
                                    {"required": ["operating_cost_per_loan_col"]},
                                    {"required": ["operating_cost_per_loan_value"]},
                                ]
                            },
                            {
                                "not": {
                                    "anyOf": [
                                        {"required": ["utilization_col"]},
                                        {"required": ["utilization_value"]},
                                    ]
                                }
                            },
                        ]
                    },
                ],
                "additionalProperties": False,
            },
            "candidate_design": _CANDIDATE_DESIGN_JSON_SCHEMA,
            "strategy_spec": {"type": "object"},
            "workflow": {
                "type": "string",
                "enum": list(STANDARD_STRATEGY_WORKFLOWS),
            },
            "workflow_inputs": {"type": "object"},
            "clarification": {"type": "string", "minLength": 1},
        },
        "additionalProperties": False,
        "oneOf": [
            {"required": ["operation", "strategy_type"]},
            {
                "properties": {
                    "request_kind": {"const": "standard_workflow"},
                },
                "required": ["request_kind", "workflow", "workflow_inputs"],
            },
            {"required": ["clarification"]},
        ],
    },
}

@dataclass(frozen=True)
class StrategyRequestDraft(Mapping[str, Any]):
    """Canonical, platform-validated strategy request draft."""

    operation: str
    strategy_type: str
    objective: str | None = None
    max_bad_rate: float | None = None
    min_approval_rate: float | None = None
    baseline_strategy_id: str | None = None
    strategy_id: str | None = None
    adoption_reason: str | None = None
    profit: Mapping[str, Any] | None = None
    economics_inputs: Mapping[str, Any] | None = None
    candidate_design: Mapping[str, Any] | None = None
    strategy_spec: Mapping[str, Any] | None = None

    @property
    def request_kind(self) -> str:
        return "strategy_lifecycle"

    def __post_init__(self) -> None:
        if self.profit is not None:
            object.__setattr__(self, "profit", _deep_freeze(self.profit))
        if self.economics_inputs is not None:
            object.__setattr__(
                self,
                "economics_inputs",
                _deep_freeze(self.economics_inputs),
            )
        if self.candidate_design is not None:
            object.__setattr__(
                self,
                "candidate_design",
                _deep_freeze(self.candidate_design),
            )
        if self.strategy_spec is not None:
            object.__setattr__(
                self,
                "strategy_spec",
                _deep_freeze(self.strategy_spec),
            )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "operation": self.operation,
            "strategy_type": self.strategy_type,
        }
        for field_name in (
            "objective",
            "max_bad_rate",
            "min_approval_rate",
            "baseline_strategy_id",
            "strategy_id",
            "adoption_reason",
            "profit",
            "economics_inputs",
            "candidate_design",
            "strategy_spec",
        ):
            value = getattr(self, field_name)
            if value is not None:
                payload[field_name] = _deep_thaw(value)
        return payload

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())

@dataclass(frozen=True)
class StandardWorkflowRequestDraft(Mapping[str, Any]):
    """Canonical request for a built-in, deterministic strategy analysis."""

    workflow: str
    workflow_inputs: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "workflow_inputs",
            _deep_freeze(self.workflow_inputs),
        )

    @property
    def request_kind(self) -> str:
        return "standard_workflow"

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_kind": self.request_kind,
            "workflow": self.workflow,
            "workflow_inputs": _deep_thaw(self.workflow_inputs),
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())

CompiledStrategyRequestDraft = StrategyRequestDraft | StandardWorkflowRequestDraft

@dataclass(frozen=True)
class StrategyRequestCompilation:
    """A validated draft awaiting confirmation, or a Chinese clarification."""

    draft: CompiledStrategyRequestDraft | None
    clarification: str | None
    confirmation: str | None
    clarification_code: str | None = None
    clarification_fields: tuple[str, ...] = ()

    @property
    def validated_draft(self) -> CompiledStrategyRequestDraft | None:
        return self.draft

    @property
    def clarify(self) -> str | None:
        return self.clarification

    @property
    def confirmation_text(self) -> str | None:
        return self.confirmation

    @property
    def needs_clarification(self) -> bool:
        return self.draft is None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "draft": None if self.draft is None else self.draft.to_dict(),
            "clarification": self.clarification,
            "confirmation": self.confirmation,
        }
        if self.clarification_code is not None:
            payload["clarification_code"] = self.clarification_code
        if self.clarification_fields:
            payload["clarification_fields"] = list(self.clarification_fields)
        return payload

@dataclass(frozen=True)
class _ValidationOutcome:
    result: StrategyRequestCompilation
    accepted: bool
    error: str | None = None

def compile_strategy_request(
    utterance: str,
    *,
    allowed_columns: Iterable[str] | None,
    target_col: str | None = None,
    llm,
    caller: str = "strategy_request_compiler",
) -> StrategyRequestCompilation:
    """Compile one utterance with bounded semantic and format correction."""

    if not isinstance(utterance, str) or not utterance.strip():
        return _clarification("Please indicate the type of strategy that you wish to implement.")
    normalized_utterance = utterance.strip()
    if _COLLECTION_STRATEGY_RE.search(normalized_utterance):
        return _clarification(
            "The strategy of the collection action is not yet evaluated, cost, capacity and recovery."
            "Please indicate whether only a risk-based stratum analysis is required.",
            code="collection_strategy_unsupported",
            fields=("strategy_type", "collection_action_contract"),
        )
    whitelist = _column_whitelist(allowed_columns)
    observed_target = _normalized_target_col(target_col)
    prompt = _user_prompt(normalized_utterance, whitelist, target_col=observed_target)
    try:
        raw = _complete(llm, prompt=prompt, caller=caller)
    except Exception:
        return _clarification(
            "The strategy request cannot be resolved at this time, please try again or specify the operation, the type of strategy and the object of the strategy at a later stage."
        )
    outcome = _validate_reply(
        raw,
        whitelist,
        target_col=observed_target,
        caller=caller,
        attempt_kind="initial",
    )
    if outcome.accepted:
        grounded = _ground_refinement_request(
            normalized_utterance,
            outcome.result,
            whitelist=whitelist,
            target_col=observed_target,
        )
        if grounded.clarification_code == "roll_rate_column_binding_not_grounded":
            repair_prompt = _repair_prompt(
                prompt,
                raw=raw,
                error=(
                    f"{grounded.clarification_code}:{grounded.clarification}\n"
                    "Hold on.workflow=roll_rate_matrix,Only fixes the user's specified binding"
                    "id_col/time_col/status_col/balance_col;No other valid column may be replaced."
                ),
            )
            try:
                repaired = _complete(llm, prompt=repair_prompt, caller=caller)
            except Exception:
                return grounded
            repaired_outcome = _validate_reply(
                repaired,
                whitelist,
                target_col=observed_target,
                caller=caller,
                attempt_kind="roll_rate_column_correction",
            )
            if not (
                repaired_outcome.accepted
                and isinstance(
                    repaired_outcome.result.draft,
                    StandardWorkflowRequestDraft,
                )
                and repaired_outcome.result.draft.workflow == "roll_rate_matrix"
            ):
                return grounded
            return _ground_refinement_request(
                normalized_utterance,
                repaired_outcome.result,
                whitelist=whitelist,
                target_col=observed_target,
            )
        if (
            grounded.clarification_code
            == "strategy_sample_design_v2_workflow_required"
        ):
            return _correct_sample_design_v2_request(
                llm,
                utterance=normalized_utterance,
                whitelist=whitelist,
                target_col=observed_target,
                error=(
                    f"{grounded.clarification_code}:{grounded.clarification}\n"
                ),
                caller=caller,
            )
        return grounded
    if utterance_targets_strategy_sample_design(normalized_utterance):
        return _correct_sample_design_v2_request(
            llm,
            utterance=normalized_utterance,
            whitelist=whitelist,
            target_col=observed_target,
            error=outcome.error or "SampleDesign V2 The draft was not validated by the platform.",
            caller=caller,
        )
    if outcome.result.clarification_code in _NON_REPAIRABLE_CLARIFICATION_CODES:
        # These are platform-derived business-contract gaps, not JSON-format
        # mistakes. A second LLM pass cannot supply missing economics safely and
        # must not downgrade typed code/fields into a generic clarification.
        return outcome.result

    repair_prompt = _repair_prompt(
        prompt,
        raw=raw,
        error=outcome.error or "Output format invalid",
    )
    try:
        repaired = _complete(llm, prompt=repair_prompt, caller=caller)
    except Exception:
        return outcome.result
    repaired_outcome = _validate_reply(
        repaired,
        whitelist,
        target_col=observed_target,
        caller=caller,
        attempt_kind="generic_repair",
    )
    if repaired_outcome.accepted:
        return _ground_refinement_request(
            normalized_utterance,
            repaired_outcome.result,
            whitelist=whitelist,
            target_col=observed_target,
        )
    return repaired_outcome.result

def validate_strategy_request(
    payload: object,
    *,
    allowed_columns: Iterable[str] | None,
    target_col: str | None = None,
    allow_legacy_replay: bool = False,
) -> StrategyRequestCompilation:
    """Validate an already parsed request without invoking an LLM.

    Fresh callers intentionally cannot emit the retired V1 sample workflow.
    Only a persistence/recovery boundary may opt into ``allow_legacy_replay``.
    """

    return _validate_payload(
        payload,
        _column_whitelist(allowed_columns),
        target_col=_normalized_target_col(target_col),
        allow_legacy_replay=allow_legacy_replay,
    ).result

def strategy_request_confirmation_text(
    draft: CompiledStrategyRequestDraft,
) -> str:
    """Render a plain-Chinese echo of the request before any workflow runs."""

    if isinstance(draft, StandardWorkflowRequestDraft):
        return _standard_workflow_confirmation_text(draft)

    operation = _OPERATION_LABELS[draft.operation]
    strategy_type = _TYPE_LABELS[draft.strategy_type]
    details = [f"Recognized as [ ]{strategy_type}〕- I\'m sorry.{operation}〕Request"]
    if draft.strategy_id:
        details.append(f"PolicyID:{draft.strategy_id}")
    if draft.baseline_strategy_id:
        details.append(f"Baseline strategyID:{draft.baseline_strategy_id}")
    if draft.objective:
        details.append(f"Operational objectives:{draft.objective}")
    constraints: list[str] = []
    if draft.max_bad_rate is not None:
        constraints.append(f"Maximum bad debt rate{draft.max_bad_rate:.2%}")
    if draft.min_approval_rate is not None:
        constraints.append(f"Minimum pass rate{draft.min_approval_rate:.2%}")
    if constraints:
        details.append("Operational constraints:" + ",".join(constraints))
    if draft.profit is not None:
        details.append(
            "Profit caliber:"
            f"EAD Columns{draft.profit['ead_col']},PD Columns{draft.profit['pd_col']},"
            f"Annual interest rate{draft.profit['annual_rate']:.2%},"
            f"Cost of funds{draft.profit['funding_rate']:.2%},"
            f"LGD {draft.profit['lgd']:.2%},"
            f"Single operating cost{draft.profit['operating_cost_per_loan']:g},"
            f"Duration{draft.profit['term_months']} Month"
        )
    if draft.economics_inputs is not None:
        details.append(_economics_confirmation(draft))
    if draft.candidate_design is not None:
        details.append(_candidate_design_confirmation(draft))
    if draft.strategy_spec is not None:
        details.append(_strategy_spec_confirmation(draft.strategy_spec))
    if draft.adoption_reason:
        details.append(f"Reasons for adoption:{draft.adoption_reason}")
    details.append(
        "Please confirm the above calibre.Agent Only trusted tools are organized;"
        "All indicators are calculated by the Platform for certainty, and governance actions such as adoption still require corresponding manual validation."
    )
    return ";".join(details)

def _strategy_spec_confirmation(strategy_spec: Mapping[str, Any]) -> str:
    """Echo every executable rule/action so confirmation is not blind.

    The request row remains the authoritative canonical payload.  This text is
    a deterministic, human-reviewable projection: it contains no calculated
    metrics and does not ask the LLM to explain its own draft.
    """

    rules = list(strategy_spec.get("rules") or [])
    default_action = _compact_json(strategy_spec.get("default_action") or {})
    rendered = [
        f"Draft rules:{len(rules)} Rule, match.first_match,Default Action{default_action}"
    ]
    for index, rule in enumerate(rules, start=1):
        rule_id = str(rule.get("rule_id") or f"rule-{index}")
        priority = rule.get("priority")
        condition = _compact_json(rule.get("condition") or {})
        action = _compact_json(rule.get("action") or {})
        rendered.append(
            f"Rule{index} [{rule_id}](Priority{priority}):IF {condition} THEN {action}"
        )
    return ";".join(rendered)

def _compact_json(value: object) -> str:
    return json.dumps(
        _deep_thaw(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

def _complete(llm, *, prompt: str, caller: str):
    return llm.complete(
        system_prompt=_SYSTEM,
        user_prompt=prompt,
        temperature=0.0,
        response_format={"type": "json_object"},
        json_schema=STRATEGY_REQUEST_JSON_SCHEMA,
        # DeepSeek V4 counts reasoning tokens inside max_tokens.  This compiler
        # prompt is intentionally broad and needs enough bounded headroom for
        # thinking plus the final compact JSON decision.
        max_tokens=8192,
        stream=False,
        caller=caller,
        prompt_name=STRATEGY_REQUEST_COMPILER_SYS.name,
        prompt_version=STRATEGY_REQUEST_COMPILER_SYS.version,
    )

def _sample_design_v2_correction_prompt(
    utterance: str,
    *,
    whitelist: tuple[str, ...],
    target_col: str | None,
    error: str,
    format_repair: bool,
) -> str:
    opportunity = (
        "This is the only opportunity for a formal fix."
        if format_repair
        else "This is the only opportunity for semantic correction."
    )
    return (
        "[Original user intent\n"
        f"{utterance}\n"
        "[♪ White list ♪\n"
        f"{json.dumps(list(whitelist), ensure_ascii=False)}\n"
        "[Current Target Bar Roles\n"
        f"{json.dumps(target_col, ensure_ascii=False)}\n"
        "[Last output not verified through platform]\n"
        f"{error}\n"
        f"{opportunity}"
        "Fixed Outputstrategy_sample_design_v2 Other OrganiserDTO;"
        "All controls must be derived from the original intent and use a white list, and cannot be supplemented by default or guess."
        "workflow_inputs Must contain preciselytarget_bad_value,drop_nan_labels,"
        "relationship,approval_population,risk_population,partitioning,"
        "maturity,performance_window,observation_window,field_bindings,"
        "historical_score.relationship It's just...nested_same_cohort or"
        "parallel_time_cohorts."
        "time_ranges The partition must be in precise shape:"
        '{"method":"time_ranges","column":"Listing","ranges":'
        '{"development":{"start":"YYYY-MM-DDornull","end":"YYYY-MM-DDornull"},'
        '"validation":{"start":"YYYY-MM-DDornull","end":"YYYY-MM-DDornull"},'
        '"oot":{"start":"YYYY-MM-DDornull","end":"YYYY-MM-DDornull"}}}.'
        "predicate_ast Division must be usedmethod=predicate_ast And complete.selectors."
        "approval_population andrisk_population It has to be precise.inclusion,"
        "exclusion;Both at no screeningnull."
        "maturity Exact Includestatus,performance_window_days,cutoff_date,reason,"
        "status It's just...confirmed_matured,not_matured,unknown,unavailable;"
        "confirmed_matured Timeperformance_window_days andcutoff_date Requiredreason "
        "I must.null;not_matured Timeperformance_window_days,cutoff_date,From the original."
        "Non-emptyreason \"All shall be filled in,unknown/unavailable Timeperformance_window_days and"
        "cutoff_date I must.null,reason It must be a non-empty statement in the original language."
        "performance_window Exact Includestatus,days,status It's just...provided or"
        "unavailable,provided Timedays And will fill it with,unavailable Timedays I must.null;"
        "observation_window Exact Includestatus,start,end,status It's just...provided or"
        "unavailable,provided Timestart/end And will fill it with,unavailable Timestart andend I must."
        " null.field_bindings Exact Includeentity_field,time_field,"
        "group_field,month_field,weight_field,loan_amount_field,"
        "overdue_amount_field;The original phrase clearly indicates that the fields that are not available for the time being must be exportednull."
        "historical_score Exact Includestatus,column,"
        "direction,reason,status It's just...available,unavailable,not_applicable,"
        "available Timecolumn It's gonna be filled.direction It's just...higher_is_riskier or"
        "lower_is_riskier andreason I must.null;unavailable/not_applicable Time"
        "column anddirection "
        "I must.null,reason It must be a non-empty statement in the original language."
        "Only one outputJSON objects; only Chinese returns if information is insufficientclarification."
    )

def _complete_sample_design_v2_correction(
    llm,
    *,
    prompt: str,
    caller: str,
):
    return llm.complete(
        system_prompt=SAMPLE_DESIGN_V2_CORRECTION_SYS.text,
        user_prompt=prompt,
        temperature=0.0,
        response_format={"type": "json_object"},
        json_schema=SAMPLE_DESIGN_V2_CORRECTION_JSON_SCHEMA,
        max_tokens=8192,
        stream=False,
        caller=caller,
        prompt_name=SAMPLE_DESIGN_V2_CORRECTION_SYS.name,
        prompt_version=SAMPLE_DESIGN_V2_CORRECTION_SYS.version,
    )

def _correct_sample_design_v2_request(
    llm,
    *,
    utterance: str,
    whitelist: tuple[str, ...],
    target_col: str | None,
    error: str,
    caller: str,
) -> StrategyRequestCompilation:
    repair_prompt = _sample_design_v2_correction_prompt(
        utterance,
        whitelist=whitelist,
        target_col=target_col,
        error=error,
        format_repair=False,
    )
    try:
        repaired = _complete_sample_design_v2_correction(
            llm,
            prompt=repair_prompt,
            caller=caller,
        )
    except Exception:
        return _clarification(
            "It's not right for now.SampleDesign V2 Requests, please retest or supplement the full sample calibre at a later stage."
        )
    repaired_outcome = _validate_reply(
        repaired,
        whitelist,
        target_col=target_col,
        caller=caller,
        attempt_kind="sample_design_semantic_correction",
    )
    if repaired_outcome.accepted:
        if repaired_outcome.result.draft is None:
            return repaired_outcome.result
        return _ground_refinement_request(
            utterance,
            repaired_outcome.result,
            whitelist=whitelist,
            target_col=target_col,
        )
    if (
        repaired_outcome.result.clarification
        != "The draft strategy for model return is not validJSON object, re-profil the strategy request."
    ):
        return repaired_outcome.result

    format_repair_prompt = _sample_design_v2_correction_prompt(
        utterance,
        whitelist=whitelist,
        target_col=target_col,
        error=(
            repaired_outcome.result.clarification
            or repaired_outcome.error
            or "Output format invalid"
        ),
        format_repair=True,
    )
    try:
        format_repaired = _complete_sample_design_v2_correction(
            llm,
            prompt=format_repair_prompt,
            caller=caller,
        )
    except Exception:
        return repaired_outcome.result
    format_repaired_outcome = _validate_reply(
        format_repaired,
        whitelist,
        target_col=target_col,
        caller=caller,
        attempt_kind="sample_design_format_repair",
    )
    if format_repaired_outcome.accepted:
        if format_repaired_outcome.result.draft is None:
            return format_repaired_outcome.result
        return _ground_refinement_request(
            utterance,
            format_repaired_outcome.result,
            whitelist=whitelist,
            target_col=target_col,
        )
    return format_repaired_outcome.result

def _strategy_payload_within_limits(payload: object) -> bool:
    stack: list[tuple[object, int]] = [(payload, 0)]
    seen_containers: set[int] = set()
    node_count = 0
    while stack:
        value, depth = stack.pop()
        node_count += 1
        if node_count > _STRATEGY_REPLY_MAX_NODES or depth > _STRATEGY_REPLY_MAX_DEPTH:
            return False
        if isinstance(value, Mapping):
            identity = id(value)
            if identity in seen_containers:
                return False
            seen_containers.add(identity)
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, Sequence) and not isinstance(
            value, str | bytes | bytearray
        ):
            identity = id(value)
            if identity in seen_containers:
                return False
            seen_containers.add(identity)
            stack.extend((item, depth + 1) for item in value)
    return True

def _reply_edge_char_kind(text: str, *, first: bool) -> str:
    stripped = text.strip()
    if not stripped:
        return "none"
    char = stripped[0] if first else stripped[-1]
    if char == "{":
        return "brace_open"
    if char == "}":
        return "brace_close"
    if char == "[":
        return "bracket_open"
    if char == "]":
        return "bracket_close"
    if char in {'"', "'"}:
        return "quote"
    if char.isdigit():
        return "digit"
    if char.isalpha():
        return "letter"
    return "other"

def _reply_has_balanced_object(text: str) -> bool:
    """Detect a balanced object boundary without retaining or parsing content."""

    start = text.find("{")
    while start >= 0:
        depth = 0
        in_string = False
        escape = False
        for char in text[start:]:
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return True
                if depth < 0:
                    break
        start = text.find("{", start + 1)
    return False

def _log_json_parse_failure(
    raw: object,
    *,
    caller: str,
    attempt_kind: str,
) -> None:
    """Log shape-only diagnostics; never persist completion or prompt content."""

    text = raw if isinstance(raw, str) else ""
    lowered = text.lower()
    logger.warning(
        "strategy JSON parse failed caller=%s attempt_kind=%s "
        "chars=%d has_think=%s has_fence=%s "
        "first_char_kind=%s last_char_kind=%s "
        "brace_open=%d brace_close=%d bracket_open=%d bracket_close=%d "
        "balanced_object=%s",
        caller,
        attempt_kind,
        len(text),
        "<think" in lowered,
        "```" in text,
        _reply_edge_char_kind(text, first=True),
        _reply_edge_char_kind(text, first=False),
        text.count("{"),
        text.count("}"),
        text.count("["),
        text.count("]"),
        _reply_has_balanced_object(text),
    )

def _validate_reply(
    raw: object,
    whitelist: tuple[str, ...],
    *,
    target_col: str | None,
    caller: str,
    attempt_kind: str,
) -> _ValidationOutcome:
    if isinstance(raw, str) and len(raw) > _STRATEGY_REPLY_MAX_CHARS:
        return _invalid(
            "The model returns a draft strategy that is too long, and please reduce it to a clear strategy operation.",
            code="strategy_request_too_complex",
            fields=("reply",),
        )
    payload, error = load_json_object(raw)
    if payload is None:
        _log_json_parse_failure(
            raw,
            caller=caller,
            attempt_kind=attempt_kind,
        )
        message = "The draft strategy for model return is not validJSON object, re-profil the strategy request."
        return _ValidationOutcome(_clarification(message), False, error or message)
    return _validate_payload(
        payload,
        whitelist,
        target_col=target_col,
        allow_legacy_replay=False,
    )

def _validate_payload(
    payload: object,
    whitelist: tuple[str, ...],
    *,
    target_col: str | None,
    allow_legacy_replay: bool,
) -> _ValidationOutcome:
    if not isinstance(payload, Mapping):
        message = "The tactical request must beJSON object, please re-state."
        return _invalid(message)
    if not _strategy_payload_within_limits(payload):
        return _invalid(
            "The draft policy is too deep or too many fields, and please narrow down to a clear policy operation.",
            code="strategy_request_too_complex",
            fields=("payload",),
        )
    if any(not isinstance(key, str) for key in payload):
        return _invalid("The field name for the strategy request must be text, re-profiling.")

    if "clarification" in payload:
        if set(payload) != {"clarification"}:
            return _invalid("The clarification problem cannot arise at the same time as the draft strategy field. Please re-select an output.")
        value = payload["clarification"]
        if not isinstance(value, str) or not value.strip():
            return _invalid("The question of clarification must be non-empty.")
        return _ValidationOutcome(
            _clarification(_chinese_clarification(value)),
            True,
        )

    request_kind = payload.get("request_kind", "strategy_lifecycle")
    if not isinstance(request_kind, str) or request_kind not in STRATEGY_REQUEST_KINDS:
        return _invalid(
            "Unsupportedrequest_kind;It's just...strategy_lifecycle orstandard_workflow."
        )
    if request_kind == "standard_workflow":
        unexpected = sorted(set(payload) - _STANDARD_WORKFLOW_DRAFT_FIELDS)
        if unexpected:
            rendered = ",".join(f"[{field}]" for field in unexpected)
            return _invalid(
                f"StandardWorkflow Request contains unsupported fields{rendered},Please delete and restate."
            )
        return _validate_standard_workflow_payload(
            payload,
            whitelist,
            target_col=target_col,
            allow_legacy_replay=allow_legacy_replay,
        )

    unexpected = sorted(set(payload) - _LIFECYCLE_DRAFT_FIELDS)
    if unexpected:
        rendered = ",".join(f"[{field}]" for field in unexpected)
        return _invalid(f"Policy request contains unsupported fields{rendered},Please delete and restate.")
    if payload.get("request_kind") not in (None, "strategy_lifecycle"):
        return _invalid("The policy life cycle requestsrequest_kind It must be.strategy_lifecycle.")
    missing = [
        field for field in ("operation", "strategy_type") if field not in payload
    ]
    if missing:
        rendered = ",".join(missing)
        return _invalid(f"Not required fields recognized{rendered},Please add a new version of the strategy operation and the type of strategy.")

    operation = payload["operation"]
    if not isinstance(operation, str) or operation not in STRATEGY_OPERATIONS:
        return _invalid(
            "Unsupported policy operations; optional actions are:" + ",".join(STRATEGY_OPERATIONS) + "."
        )
    strategy_type = payload["strategy_type"]
    if not isinstance(strategy_type, str) or strategy_type not in STRATEGY_TYPES:
        return _invalid(
            "Unsupported policy type; optional type:" + ",".join(STRATEGY_TYPES) + "."
        )

    try:
        _validate_economics_field_ownership(payload, strategy_type=strategy_type)
        _validate_candidate_field_ownership(
            payload,
            operation=operation,
            strategy_type=strategy_type,
        )
        objective = _optional_text(payload, "objective")
        max_bad_rate = _optional_ratio(payload, "max_bad_rate")
        min_approval_rate = _optional_ratio(payload, "min_approval_rate")
        baseline_strategy_id = _optional_text(payload, "baseline_strategy_id")
        strategy_id = _optional_text(payload, "strategy_id")
        adoption_reason = _optional_adoption_reason(payload)
        profit = _optional_profit(payload, whitelist)
        economics_inputs = _optional_economics_inputs(
            payload,
            strategy_type=strategy_type,
            whitelist=whitelist,
        )
        candidate_design = _optional_candidate_design(
            payload,
            operation=operation,
            strategy_type=strategy_type,
            whitelist=whitelist,
        )
        if candidate_design is not None:
            try:
                economics_inputs = normalize_candidate_economics_inputs(
                    strategy_type,
                    economics_inputs,
                    allowed_columns=whitelist,
                )
            except CandidateDesignError as exc:
                raise _DraftValidationError(
                    str(exc),
                    code=exc.code,
                    fields=exc.fields,
                ) from exc
        strategy_spec = _optional_strategy_spec(
            payload,
            strategy_type=strategy_type,
            whitelist=whitelist,
        )
    except _DraftValidationError as exc:
        return _invalid(str(exc), code=exc.code, fields=exc.fields)

    draft = StrategyRequestDraft(
        operation=operation,
        strategy_type=strategy_type,
        objective=objective,
        max_bad_rate=max_bad_rate,
        min_approval_rate=min_approval_rate,
        baseline_strategy_id=baseline_strategy_id,
        strategy_id=strategy_id,
        adoption_reason=adoption_reason,
        profit=profit,
        economics_inputs=economics_inputs,
        candidate_design=candidate_design,
        strategy_spec=strategy_spec,
    )
    result = StrategyRequestCompilation(
        draft=draft,
        clarification=None,
        confirmation=strategy_request_confirmation_text(draft),
    )
    return _ValidationOutcome(result, True)

def _validate_standard_workflow_payload(
    payload: Mapping[str, Any],
    whitelist: tuple[str, ...],
    *,
    target_col: str | None,
    allow_legacy_replay: bool,
) -> _ValidationOutcome:
    missing = [
        field for field in ("workflow", "workflow_inputs") if field not in payload
    ]
    if missing:
        return _invalid("StandardWorkflow Request missing field:" + ",".join(missing) + ".")
    workflow = payload["workflow"]
    allowed_workflows = (
        REPLAYABLE_STANDARD_STRATEGY_WORKFLOWS
        if allow_legacy_replay
        else FRESH_STANDARD_STRATEGY_WORKFLOWS
    )
    if not isinstance(workflow, str) or workflow not in allowed_workflows:
        return _invalid(
            "Unsupported criteriaWorkflow;Optional value is:"
            + ",".join(allowed_workflows)
            + "."
        )
    raw_inputs = payload["workflow_inputs"]
    if not isinstance(raw_inputs, Mapping):
        return _invalid("workflow_inputs Must be an object.")
    if any(not isinstance(key, str) for key in raw_inputs):
        return _invalid("workflow_inputs field name must be text.")
    try:
        resolved = resolve_standard_strategy_workflow(
            workflow,
            raw_inputs,
            context=StrategyWorkflowResolutionContext(
                allowed_columns=whitelist,
                target_col=target_col,
            ),
            mode=(
                StrategyWorkflowResolutionMode.REPLAY
                if allow_legacy_replay
                else StrategyWorkflowResolutionMode.FRESH
            ),
        )
    except StrategyWorkflowValidationError as exc:
        return _invalid(str(exc), code=exc.code, fields=exc.fields)

    draft = StandardWorkflowRequestDraft(
        workflow=resolved.workflow_id,
        workflow_inputs=resolved.workflow_inputs,
    )
    return _ValidationOutcome(
        StrategyRequestCompilation(
            draft=draft,
            clarification=None,
            confirmation=resolved.confirmation,
        ),
        True,
    )

def _simple_partition_equality(
    predicate: Mapping[str, Any],
    *,
    name: str,
) -> tuple[str, object]:
    if (
        set(predicate) != {"op", "left", "right"}
        or predicate.get("op") != "eq"
        or not isinstance(predicate.get("left"), Mapping)
        or set(predicate["left"]) != {"column"}
        or not isinstance(predicate.get("right"), Mapping)
        or set(predicate["right"]) != {"literal"}
    ):
        raise _DraftValidationError(
            f"{name} It must be now.column == literal Simple equivalentpredicate.",
            code="strategy_sample_design_v2_native_bootstrap_required",
            fields=(name,),
        )
    literal = predicate["right"]["literal"]
    if literal is None or isinstance(
        literal, Mapping | Sequence
    ) and not isinstance(literal, str):
        raise _DraftValidationError(
            f"{name} literal Must be a non-empty mark.",
            fields=(name,),
        )
    return str(predicate["left"]["column"]), literal

def _utterance_chains_voting_search_operation(utterance: str) -> bool:
    """Detect a positive lifecycle follow-up even without a connector word."""

    search_seen = False
    for clause_match in _VOTING_COMMAND_CLAUSE_RE.finditer(utterance):
        clause = clause_match.group(0)
        if not search_seen:
            search_match = _VOTING_SEARCH_INTENT_RE.search(clause)
            search_seen = (
                _VOTING_SUBJECT_RE.search(clause) is not None
                and search_match is not None
            )
            if search_seen and search_match is not None:
                if _voting_search_text_has_positive_follow_up(
                    clause[: search_match.start()]
                ) or _voting_search_text_has_positive_follow_up(
                    clause[search_match.end() :]
                ):
                    return True
            continue
        if _voting_search_text_has_positive_follow_up(clause):
            return True
    return False

def _is_canonical_stored_strategy_report_request(
    draft: CompiledStrategyRequestDraft | None,
) -> bool:
    """Keep a fully identified stored-strategy report on its legacy route."""

    return bool(
        isinstance(draft, StrategyRequestDraft)
        and draft.operation == "report"
        and draft.strategy_spec is None
        and draft.strategy_id
    )

_ROLL_RATE_COLUMN_ROLE_LABELS = {
    "id_col": (
        r"(?:(?:Client|Account|Loans)\s*(?:ID|id|Numbering)\s*(?:Fields|Columns)?|"
        r"(?<![A-Za-z0-9_])id_col(?![A-Za-z0-9_]))"
    ),
    "time_col": (
        r"(?:(?:Time|Date|Month|Month age|MOB|mob)\s*(?:Fields|Columns)?|"
        r"(?<![A-Za-z0-9_])time_col(?![A-Za-z0-9_]))"
    ),
    "status_col": (
        r"(?:(?:Migration)?Status\s*(?:Fields|Columns)?|"
        r"(?<![A-Za-z0-9_])status_col(?![A-Za-z0-9_]))"
    ),
    "balance_col": (
        r"(?:(?:Balance(?:Weights)?|Amount weight)\s*(?:Fields|Columns)?|"
        r"(?<![A-Za-z0-9_])balance_col(?![A-Za-z0-9_]))"
    ),
}

def _utterance_targets_automatic_tree_apply(utterance: str) -> bool:
    """Recognize full-tree dataset writeback without stealing build/leaf turns."""

    return _AUTOMATIC_TREE_APPLY_TARGET_RE.search(utterance) is not None

def _utterance_requests_automatic_tree_follow_up(utterance: str) -> bool:
    follow_up_patterns = (
        _AUTOMATIC_TREE_MULTI_STEP_RE,
        _AUTOMATIC_TREE_BEST_LEAF_RE,
        _AUTOMATIC_TREE_REVERSED_BEST_LEAF_RE,
        _AUTOMATIC_TREE_LEAF_FOLLOW_UP_RE,
        _AUTOMATIC_TREE_POOL_FOLLOW_UP_RE,
        _AUTOMATIC_TREE_LEAF_DECISION_FOLLOW_UP_RE,
        _AUTOMATIC_TREE_HEURISTIC_LEAF_FOLLOW_UP_RE,
        _AUTOMATIC_TREE_NODE_RANK_FOLLOW_UP_RE,
        _AUTOMATIC_TREE_NODE_SELECT_FOLLOW_UP_RE,
        _AUTOMATIC_TREE_NODE_EXTRACT_FOLLOW_UP_RE,
        _AUTOMATIC_TREE_LIFECYCLE_FOLLOW_UP_RE,
        _AUTOMATIC_TREE_LEAF_ID_WRITEBACK_RE,
        _AUTOMATIC_TREE_DECISION_ARTIFACT_RE,
    )
    for clause in _automatic_tree_follow_up_clauses(utterance):
        leaf_matches = tuple(_AUTOMATIC_TREE_LEAF_TOKEN_RE.finditer(clause))
        effect_matches = tuple(_AUTOMATIC_TREE_DECISION_EFFECT_RE.finditer(clause))
        if leaf_matches:
            for effect_match in effect_matches:
                if not _automatic_tree_follow_up_action_is_negated(
                    clause,
                    action_start=effect_match.start(),
                ):
                    return True
        for pattern in follow_up_patterns:
            for match in pattern.finditer(clause):
                anchor = _AUTOMATIC_TREE_FOLLOW_UP_ACTION_ANCHOR_RE.search(
                    clause,
                    match.start(),
                    match.end(),
                )
                action_start = anchor.start() if anchor is not None else match.start()
                if not _automatic_tree_follow_up_action_is_negated(
                    clause,
                    action_start=action_start,
                ):
                    return True
    return False

def _utterance_supports_automatic_tree_feature(
    utterance: str,
    feature: str,
    *,
    whitelist: Sequence[str],
) -> bool:
    if any(
        _utterance_supports_automatic_tree_column_role(
            utterance,
            field=field,
            column=feature,
            whitelist=whitelist,
        )
        for field in _AUTOMATIC_TREE_COLUMN_ROLE_LABELS
    ):
        return False
    mentions = tuple(
        (start, end)
        for start, end, column in _automatic_tree_column_mentions(
            utterance,
            whitelist,
        )
        if column == feature
    )
    cue_pattern = re.compile(
        r"Characteristics|Candidate Variables|Input Variables|From Variable|features?|Build|"
        r"Construction(?:One.)?(?:Automatic)?(?:Decision-making)?Tree|build|tree",
        re.IGNORECASE,
    )
    blocker_pattern = re.compile(
        "|".join(
            f"(?:{pattern})"
            for pattern in (
                *_AUTOMATIC_TREE_COLUMN_ROLE_LABELS.values(),
                *_AUTOMATIC_TREE_NUMBER_LABELS.values(),
            )
        ),
        re.IGNORECASE,
    )
    for start, end in mentions:
        if _automatic_tree_feature_span_is_negated(
            utterance,
            start=start,
            end=end,
        ):
            continue
        segment, _, _ = _automatic_tree_segment(
            utterance,
            start=start,
            end=end,
            separators=(",", ",", ";", ";", ".", "\n"),
        )
        if cue_pattern.search(segment) is not None:
            return True
        sentence, sentence_left, _ = _automatic_tree_segment(
            utterance,
            start=start,
            end=end,
            separators=(";", ";", ".", "\n"),
        )
        feature_start = start - sentence_left
        feature_end = end - sentence_left
        for cue in cue_pattern.finditer(sentence):
            between = (
                sentence[cue.end() : feature_start]
                if cue.end() <= feature_start
                else sentence[feature_end : cue.start()]
            )
            if blocker_pattern.search(between) is None:
                return True
    return False

def _utterance_supports_automatic_tree_column_role(
    utterance: str,
    *,
    field: str,
    column: str,
    whitelist: Sequence[str],
) -> bool:
    label = _AUTOMATIC_TREE_COLUMN_ROLE_LABELS[field]
    resolved_mentions = tuple(
        (start, end)
        for start, end, resolved_column in _automatic_tree_column_mentions(
            utterance,
            whitelist,
        )
        if resolved_column == column
    )
    if not resolved_mentions:
        return False
    column_pattern = rf"(?<![A-Za-z0-9_]){re.escape(column)}(?![A-Za-z0-9_])"
    paired = re.compile(
        rf"(?:(?:{label})\s*(?:[::=]|Yes|Yes.|Use|Use|Remove|Set as)?\s*"
        rf"{column_pattern}|"
        rf"{column_pattern}\s*(?:As|Yes.|Yes|Use as|Set as)\s*(?:{label}))",
        re.IGNORECASE,
    )
    for match in paired.finditer(utterance):
        if not any(
            match.start() <= start and end <= match.end()
            for start, end in resolved_mentions
        ):
            continue
        if not _automatic_tree_span_is_negated(
            utterance,
            start=match.start(),
            end=match.end(),
        ) and not _automatic_tree_value_is_replaced(utterance, end=match.end()):
            return True
    replacement = re.compile(
        rf"(?:{label})\s*(?:[::=]|Yes|Yes.|Use|Use|Remove|Set as)?\s*"
        r"(?:From|By)?\s*[^\s,,;;.]+\s*"
        r"(?:For|Replace with|Adjust to|Replace with|Not|Not really.)\s*"
        rf"{column_pattern}",
        re.IGNORECASE,
    )
    return any(
        any(
            match.start() <= start and end <= match.end()
            for start, end in resolved_mentions
        )
        and not _automatic_tree_span_is_negated(
            utterance,
            start=match.start(),
            end=match.end(),
        )
        for match in replacement.finditer(utterance)
    )

def _utterance_supports_automatic_tree_direction(
    utterance: str,
    *,
    feature: str,
    direction: str,
    column_spans: Sequence[tuple[int, int]],
    whitelist: Sequence[str],
) -> bool:
    feature_mentions = tuple(
        (start, end)
        for start, end, column in _automatic_tree_column_mentions(
            utterance,
            whitelist,
        )
        if column == feature
    )
    for feature_start, feature_end in feature_mentions:
        segment, left, _ = _automatic_tree_segment(
            utterance,
            start=feature_start,
            end=feature_end,
            separators=(",", ",", ",", ";", ";", ".", "\n"),
        )
        feature_center = (feature_start + feature_end) / 2 - left
        candidates: list[tuple[float, str]] = []
        for candidate_direction, pattern in _AUTOMATIC_TREE_DIRECTION_GROUNDING.items():
            for direction_match in re.finditer(pattern, segment, re.IGNORECASE):
                absolute_start = left + direction_match.start()
                absolute_end = left + direction_match.end()
                if _automatic_tree_span_overlaps_columns(
                    absolute_start,
                    absolute_end,
                    column_spans,
                ) or _automatic_tree_span_is_negated(
                    utterance,
                    start=absolute_start,
                    end=absolute_end,
                ):
                    continue
                replacement = segment[
                    direction_match.end() : direction_match.end() + 16
                ]
                if re.match(r"\s*(?:For|Replace with|Adjust to|Not|Not really.)", replacement):
                    continue
                direction_center = (direction_match.start() + direction_match.end()) / 2
                candidates.append(
                    (abs(direction_center - feature_center), candidate_direction)
                )
        if not candidates:
            continue
        nearest_distance = min(distance for distance, _ in candidates)
        nearest = {
            candidate_direction
            for distance, candidate_direction in candidates
            if math.isclose(
                distance,
                nearest_distance,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        }
        if nearest == {direction}:
            return True
    return False

def _utterance_supports_automatic_tree_number(
    utterance: str,
    *,
    field: str,
    value: object,
    column_spans: Sequence[tuple[int, int]],
) -> bool:
    expected = float(value)
    return any(
        math.isclose(observed, expected, rel_tol=0.0, abs_tol=1e-12)
        for observed in _automatic_tree_number_values(
            utterance,
            field=field,
            column_spans=column_spans,
        )
    )

def _ungrounded_pool_actions(
    utterance: str,
    *actions: Mapping[str, Any],
) -> list[str]:
    missing: list[str] = []
    for action in actions:
        action_type = str(action.get("type") or "")
        pattern = _POOL_ACTION_GROUNDING.get(action_type)
        if pattern is None or pattern.search(utterance) is None:
            missing.append(f"typed action {action_type or 'unknown'}")
        reason_code = action.get("reason_code")
        if isinstance(reason_code, str) and not _utterance_contains_token(
            utterance, reason_code
        ):
            missing.append(reason_code)
        if action_type in {"limit", "pricing", "segment"} and not (
            _utterance_contains_pool_action_value(utterance, action.get("value"))
        ):
            missing.append(f"typed action value {action.get('value')}")
        output_value = action.get("output_value")
        if output_value is not None and not _utterance_contains_pool_action_value(
            utterance, output_value
        ):
            missing.append(f"typed action output_value {output_value}")
    return missing

def _utterance_contains_pool_action_value(utterance: str, value: object) -> bool:
    candidates = {str(value)}
    try:
        candidates.add(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    except (TypeError, ValueError):
        return False
    folded = utterance.casefold()
    return any(candidate.casefold() in folded for candidate in candidates)

def _utterance_supports_risk_threshold(
    utterance: str,
    *,
    operator: str,
    value: float,
) -> bool:
    return any(
        candidate_operator == operator
        and math.isclose(candidate_value, value, rel_tol=0.0, abs_tol=1e-12)
        for candidate_operator, candidate_value in _risk_threshold_expressions(
            utterance
        )
    )

def _utterance_contains_token(utterance: str, token: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])"
    return re.search(pattern, utterance) is not None

def _risk_threshold_expressions(utterance: str) -> tuple[tuple[str, float], ...]:
    expressions: list[tuple[str, float]] = []
    for match in _RISK_THRESHOLD_EXPRESSION_RE.finditer(utterance):
        expressions.append(
            (
                _normalized_threshold_operator(match.group("operator")),
                _ratio_token_value(match.group("value")),
            )
        )
    return tuple(expressions)

def _normalized_threshold_operator(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    if normalized in {
        "greater than or equal to",
        "No less than",
        "At least.",
        "Not less than",
        "Achieved",
        ">=",
        "≥",
        "greater than or equal",
        "greater than or equal to",
        "at least",
    }:
        return ">="
    if normalized in {
        "less than or equal to",
        "Not higher",
        "Up to",
        "Most",
        "<=",
        "≤",
        "less than or equal",
        "less than or equal to",
        "at most",
    }:
        return "<="
    if normalized in {"Greater than", "Higher", "More than", ">", "more than", "greater than"}:
        return ">"
    return "<"

def _ratio_token_value(value: str) -> float:
    normalized = re.sub(r"\s+", "", value)
    if normalized.startswith("Percent"):
        return float(normalized[len("Percent") :]) / 100.0
    if normalized.endswith("%"):
        return float(normalized[:-1]) / 100.0
    return float(normalized)

def _standard_workflow_confirmation_text(
    draft: StandardWorkflowRequestDraft,
) -> str:
    confirmation = migrated_workflow_confirmation(
        draft.workflow,
        draft.workflow_inputs,
    )
    if confirmation is None:  # pragma: no cover - catalog invariant
        raise ValueError(f"unsupported standard workflow {draft.workflow}")
    return confirmation

class _DraftValidationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_strategy_request",
        fields: Iterable[str] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.fields = tuple(dict.fromkeys(str(field) for field in fields))

def _optional_text(payload: Mapping[str, Any], key: str) -> str | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise _DraftValidationError(f"{key} It must be non-empty, please restate.")
    return value.strip()

def _optional_ratio(payload: Mapping[str, Any], key: str) -> float | None:
    if key not in payload:
        return None
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _DraftValidationError(f"{key} Must be a limited number between 0 and 1.")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise _DraftValidationError(f"{key} Must be a limited number between 0 and 1.")
    return number

def _optional_adoption_reason(payload: Mapping[str, Any]) -> str | None:
    if "adoption_reason" not in payload:
        return None
    try:
        return normalize_adoption_reason(payload["adoption_reason"])
    except AdoptionReasonError as exc:
        raise _DraftValidationError(str(exc)) from exc

def _optional_profit(
    payload: Mapping[str, Any], whitelist: tuple[str, ...]
) -> dict[str, Any] | None:
    if "profit" not in payload:
        return None
    profit = payload["profit"]
    if not isinstance(profit, Mapping):
        raise _DraftValidationError("Profit parametersprofit Must be an object.")
    if any(not isinstance(key, str) for key in profit):
        raise _DraftValidationError("The profit-column paragraph name must be the text.")
    missing = sorted(_PROFIT_FIELDS - set(profit))
    unexpected = sorted(set(profit) - _PROFIT_FIELDS)
    if missing:
        raise _DraftValidationError("Profit parameters missing fields:" + ",".join(missing) + ".")
    if unexpected:
        raise _DraftValidationError(
            "Profit parameters contain unsupported fields:" + ",".join(unexpected) + "."
        )
    ead_col = _required_text(profit["ead_col"], name="ProfitEAD Columnsead_col")
    pd_col = _required_text(profit["pd_col"], name="ProfitPD Columnspd_col")
    for name, column in (("ead_col", ead_col), ("pd_col", pd_col)):
        if column not in whitelist:
            raise _DraftValidationError(
                f"Profit parameters{name} Use column of the data set that does not exist{column}],Please select from the white list."
            )
    annual_rate = _bounded_number(
        profit["annual_rate"], name="Profitannual_rate", maximum=1
    )
    funding_rate = _bounded_number(
        profit["funding_rate"], name="Profitfunding_rate", maximum=1
    )
    lgd = _bounded_number(profit["lgd"], name="Profitlgd", maximum=1)
    operating_cost = _bounded_number(
        profit["operating_cost_per_loan"],
        name="Profitoperating_cost_per_loan",
    )
    term_months = profit["term_months"]
    if (
        isinstance(term_months, bool)
        or not isinstance(term_months, int)
        or term_months < 1
    ):
        raise _DraftValidationError("Profitterm_months Must be an integer greater than or equal to 1.")
    return {
        "ead_col": ead_col,
        "pd_col": pd_col,
        "annual_rate": annual_rate,
        "funding_rate": funding_rate,
        "lgd": lgd,
        "operating_cost_per_loan": operating_cost,
        "term_months": term_months,
    }

def _validate_economics_field_ownership(
    payload: Mapping[str, Any], *, strategy_type: str
) -> None:
    if "profit" in payload and strategy_type not in {"approval", "reject"}:
        raise _DraftValidationError(
            "profit Only for approval or rejection strategies; scale and pricing strategies requestedeconomics_inputs,"
            "The economic parameters are not accepted in the cluster strategy."
        )
    if "economics_inputs" in payload and strategy_type not in {"limit", "pricing"}:
        raise _DraftValidationError(
            "economics_inputs Only for size or pricing strategies; approval and rejection strategies are requestedprofit,"
            "The economic parameters are not accepted in the cluster strategy."
        )

def _validate_candidate_field_ownership(
    payload: Mapping[str, Any],
    *,
    operation: str,
    strategy_type: str,
) -> None:
    has_candidate = "candidate_design" in payload
    has_spec = "strategy_spec" in payload
    if has_candidate and has_spec:
        raise _DraftValidationError(
            "candidate_design andstrategy_spec One choice must be made;LLM Candidates and rule results should not be submitted simultaneously.",
            code="candidate_spec_mutually_exclusive",
            fields=("candidate_design", "strategy_spec"),
        )
    if has_candidate and (
        operation != "develop"
        or strategy_type not in {"limit", "pricing", "segmentation"}
    ):
        raise _DraftValidationError(
            "candidate_design Only forlimit,pricing,segmentation It's...develop Request.",
            code="candidate_design_not_allowed",
            fields=("candidate_design",),
        )
    if has_spec and strategy_type in {"limit", "pricing", "segmentation"}:
        raise _DraftValidationError(
            "Non-approval strategyStrategy DSL It must be generated by the determination of the Platform ' s candidate design tool;"
            "LLM Not to submitstrategy_spec,Action value or recommended result.",
            code="llm_strategy_spec_forbidden",
            fields=("strategy_spec",),
        )
    if (
        operation == "develop"
        and strategy_type in {"limit", "pricing", "segmentation"}
        and not has_candidate
    ):
        raise _DraftValidationError(
            f"Development{_TYPE_LABELS[strategy_type]}Yes.candidate_design;"
            "Please supplement the candidate list, the candidate grid and the necessary operational constraints and the platform ' s re-identification rules.",
            code="candidate_design_required",
            fields=("candidate_design",),
        )

def _optional_economics_inputs(
    payload: Mapping[str, Any],
    *,
    strategy_type: str,
    whitelist: tuple[str, ...],
) -> dict[str, Any] | None:
    if "economics_inputs" not in payload:
        return None
    raw_inputs = payload["economics_inputs"]
    if not isinstance(raw_inputs, Mapping):
        raise _DraftValidationError("Economic parameterseconomics_inputs Must be an object.")
    if any(not isinstance(key, str) for key in raw_inputs):
        raise _DraftValidationError("Economic parameterseconomics_inputs field name must be text.")

    names = (
        _LIMIT_ECONOMICS_NAMES if strategy_type == "limit" else _PRICING_ECONOMICS_NAMES
    )
    allowed_fields = {key for name in names for key in (f"{name}_col", f"{name}_value")}
    unexpected = sorted(set(raw_inputs) - allowed_fields)
    if unexpected:
        raise _DraftValidationError(
            f"{_TYPE_LABELS[strategy_type]}Economic parameters contain unsupported fields:"
            + ",".join(unexpected)
            + "."
        )

    normalized: dict[str, Any] = {}
    missing: list[str] = []
    for name in names:
        column_key = f"{name}_col"
        value_key = f"{name}_value"
        has_column = column_key in raw_inputs
        has_value = value_key in raw_inputs
        if has_column and has_value:
            raise _DraftValidationError(
                f"Economic parameters{name} It must be.{column_key} and{value_key} One out of two, not available at the same time.",
                code="candidate_economics_ambiguous",
                fields=(column_key, value_key),
            )
        if not has_column and not has_value:
            missing.append(f"{column_key}/{value_key}")
            continue
        if has_column:
            column = _required_text(
                raw_inputs[column_key],
                name=f"Economic parameters{column_key}",
            )
            if column not in whitelist:
                raise _DraftValidationError(
                    f"Economic parameters{column_key} Columns where data collection does not exist or is not strategic are used"
                    f"[{column}],Please select from the white list."
                )
            normalized[column_key] = column
            continue
        normalized[value_key] = _economics_value(name, raw_inputs[value_key])

    if missing:
        raise _DraftValidationError(
            f"{_TYPE_LABELS[strategy_type]}Economic parameters are incomplete and missing:"
            + ",".join(missing)
            + ".",
            code="candidate_economics_incomplete",
            fields=missing,
        )
    return normalized

def _economics_value(name: str, value: object) -> float:
    label = _ECONOMICS_LABELS[name]
    if name == "term_months":
        number = _bounded_number(value, name=f"Economic parameters{label}")
        if number <= 0:
            raise _DraftValidationError(f"Economic parameters{label} Must be a limited number greater than zero.")
        return number
    return _bounded_number(
        value,
        name=f"Economic parameters{label}",
        maximum=_ECONOMICS_VALUE_MAXIMUMS.get(name),
    )

def _economics_confirmation(draft: StrategyRequestDraft) -> str:
    assert draft.economics_inputs is not None
    names = (
        _LIMIT_ECONOMICS_NAMES
        if draft.strategy_type == "limit"
        else _PRICING_ECONOMICS_NAMES
    )
    items: list[str] = []
    for name in names:
        column_key = f"{name}_col"
        value_key = f"{name}_value"
        label = _ECONOMICS_LABELS[name]
        if column_key in draft.economics_inputs:
            items.append(f"{label} Take Data Columns{draft.economics_inputs[column_key]}")
        else:
            value = draft.economics_inputs[value_key]
            if name in _ECONOMICS_VALUE_MAXIMUMS:
                items.append(f"{label} Take Fixed Value{value:.2%}")
            elif name == "term_months":
                items.append(f"{label} Take Fixed Value{value:g} Month")
            else:
                items.append(f"{label} Take Fixed Value{value:g}")
    return f"{_TYPE_LABELS[draft.strategy_type]}Economic parameters:" + ",".join(items)

def _candidate_design_confirmation(draft: StrategyRequestDraft) -> str:
    assert draft.candidate_design is not None
    design = draft.candidate_design
    if draft.strategy_type == "limit":
        details = (
            f"Breakdown of assessments{design['score_col']},Fixed Equivalent{design['n_bands']} Box."
            "Candidates"
            + ",".join(f"{value:g}" for value in design["limit_grid"])
            + f",Single-household expected loss budget{design['max_expected_loss_per_account']:g}"
        )
    elif draft.strategy_type == "pricing":
        details = (
            f"Breakdown of assessments{design['score_col']},Fixed Equivalent{design['n_bands']} Box."
            "Year of the candidate ' s interest rate"
            + ",".join(f"{value:.2%}" for value in design["rate_grid"])
            + f",MinROA {design['min_roa']:.2%}"
        )
    else:
        details = (
            f"Single Variable Column{design['feature_col']},Fixed Equivalent{design['n_bands']} Box."
            "Risk labels are generated by the platform at a steady rate of sample badness"
        )
    return (
        f"Candidate design input:{details};Missing policy{design['missing_policy']}."
        "Only the search space and operational calibre are identified here, and recommended actions, rules and indicators have not yet been generated,"
        "It will be calculated by the platform ' s certainty."
    )

def _optional_candidate_design(
    payload: Mapping[str, Any],
    *,
    operation: str,
    strategy_type: str,
    whitelist: tuple[str, ...],
) -> dict[str, Any] | None:
    if "candidate_design" not in payload:
        return None
    if operation != "develop":
        raise _DraftValidationError(
            "candidate_design Only fordevelop Request.",
            code="candidate_design_not_allowed",
            fields=("candidate_design",),
        )
    try:
        return normalize_candidate_design(
            strategy_type,
            payload["candidate_design"],
            allowed_columns=whitelist,
        )
    except CandidateDesignError as exc:
        raise _DraftValidationError(
            str(exc),
            code=exc.code,
            fields=exc.fields,
        ) from exc

def _optional_strategy_spec(
    payload: Mapping[str, Any],
    *,
    strategy_type: str,
    whitelist: tuple[str, ...],
) -> dict[str, Any] | None:
    if "strategy_spec" not in payload:
        return None
    if strategy_type not in {"approval", "reject"}:
        raise _DraftValidationError(
            "Non-approval strategystrategy_spec The platform must be made certain of itself.LLM Not permitted to be submitted.",
            code="llm_strategy_spec_forbidden",
            fields=("strategy_spec",),
        )
    raw_spec = payload["strategy_spec"]
    if not isinstance(raw_spec, Mapping):
        raise _DraftValidationError("Draft strategic rulesstrategy_spec Must be an object.")
    raw_metadata = raw_spec.get("metadata", {})
    if raw_metadata not in ({}, {"lineage": {}}):
        raise _DraftValidationError(
            "Draft strategic rulesmetadata The platform is a platform that generates a new platform.LLM The outcome of the indicator or other metadata should not be included."
        )
    try:
        parsed = parse_strategy_spec(raw_spec)
    except (StrategyError, TypeError, ValueError) as exc:
        raise _DraftValidationError(
            "The format or value of the draft strategic rule is invalid. Check the rules conditions, priorities and actions."
        ) from exc
    if parsed.strategy_type != strategy_type:
        raise _DraftValidationError(
            "strategy_spec It's...strategy_type It must be consistent with the type of strategy requested."
        )
    unknown_columns = sorted(
        {
            field
            for rule in parsed.rules
            for field in _condition_fields(rule.condition)
            if field not in whitelist
        }
    )
    if unknown_columns:
        rendered = ",".join(f"[{column}]" for column in unknown_columns)
        raise _DraftValidationError(
            f"Policy conditions use columns where data is not available{rendered},Please select from the white list."
        )
    return parsed.to_dict()

def _condition_fields(condition: Mapping[str, Any]) -> tuple[str, ...]:
    op = condition["op"]
    if op in {"compare", "between", "is_null", "is_not_null"}:
        return (condition["field"],)
    if op in {"and", "or", "n_of_k"}:
        return tuple(
            field
            for argument in condition["args"]
            for field in _condition_fields(argument)
        )
    if op == "not":
        return _condition_fields(condition["arg"])
    return ()

def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, Sequence) and not isinstance(
        value, str | bytes | bytearray
    ):
        return tuple(_deep_freeze(item) for item in value)
    return value

def _deep_thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _deep_thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_deep_thaw(item) for item in value]
    return value

def _required_text(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _DraftValidationError(f"{name} It must be non-empty.")
    return value.strip()

def _bounded_number(
    value: object,
    *,
    name: str,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _DraftValidationError(f"{name} It must be limited.")
    number = float(value)
    if (
        not math.isfinite(number)
        or number < 0
        or (maximum is not None and number > maximum)
    ):
        if maximum is None:
            raise _DraftValidationError(f"{name} Must be a limited number greater than 0.")
        raise _DraftValidationError(f"{name} It must be 0 to{maximum:g} There are limited numbers between.")
    return number

def _column_whitelist(
    allowed_columns: Iterable[str] | None,
) -> tuple[str, ...]:
    if allowed_columns is None:
        return ()
    if isinstance(allowed_columns, str):
        values = (allowed_columns,)
    else:
        try:
            values = tuple(allowed_columns)
        except TypeError:
            return ()
    return tuple(sorted({column for column in values if isinstance(column, str)}))

def _normalized_target_col(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()

def _user_prompt(
    utterance: str,
    whitelist: tuple[str, ...],
    *,
    target_col: str | None,
) -> str:
    return (
        "[Data set white list]\n"
        f"{json.dumps(list(whitelist), ensure_ascii=False)}\n"
        "[Current Task Target Line (as onlylimit_pricing_matrix It's...target_col Sources of risk,"
        "♪ I'm not allowed to use it for strategy rules ♪\n"
        f"{json.dumps(target_col, ensure_ascii=False)}\n"
        "[User Policy Request]\n"
        f"{utterance}\n"
        "Output only draft structured strategy or one Chineseclarification,Do not output any indicator results."
        "Yes.limit/pricing/segmentation It's...develop Request, only draw.candidate_design "
        "Search space and user-specifically giveneconomics_inputs;Ban Outputstrategy_spec,Rules,"
        "Actions, default actions, recommended values or calculation indicators. Only returns if the necessary economic calibre is not availableclarification."
        "Yes.strategy_project_context,Only word-for-word copies of the deadlines specified by the useras_of,"
        "Optionalscope,business_context Text/null,Clear path and tasks for missing fieldssource_dir Down"
        "External report by user name is relative to file name. Output is forbidden.revision/CAS,message id/hash,"
        "dataset/Pool/backtest/monitoring Quoted,artifact id/hash,Source references, available conclusions or indicators."
        "Only the context of the project is updated at one time, and no serial sample, candidate, influence, reporting, adoption or deployment is allowed; noas_of"
        "I have to.clarification,Can't be implied today."
        "Yes.strategy_sample_design_v2,workflow_inputs It must contain precisely what the user clearly provides."
        " target_bad_value,drop_nan_labels,relationship,approval_population,"
        "risk_population,partitioning,maturity,performance_window,observation_window,"
        "field_bindings,historical_score.relationship The user must specify that"
        " nested_same_cohort orparallel_time_cohorts.All embedded fields,null,Status, columns, values,"
        "Direction andreason It is important that we be able to return to the original words verbatim.fresh population Nonnull inclusion/exclusion"
        " Only outputmatch=all/any and 1 to 8 simpleconditions;condition Only Enscend"
        " column/operator/value,is_null/is_not_null Does Not Containvalue.Ban Direct Outputpopulation"
        " predicate AST.approval/risk,inclusion/exclusion andoperator/column/value"
        " They must be tailored to each local context; performance windows, observation windows andmaturity cutoff Date may not be borrowed from one another."
        "A normal performance window cannot be borrowed solely from a mature performance window;maturity cutoff (b) The same sentence must be limited by maturity;"
        "historical_score , the field and direction must be tied to the same local sub-rule, and the direction of the other field cannot be borrowed."
        "The platform will benested_same_cohort,Both aggregates are non-calculated and three different simple equivalents in the same rowselector"
        " Roadway to thecompatibility (a) Chains;parallel_time_cohorts,time_ranges,Any total count or"
        "Complexselector The route to the original.V2,Derogation or demotion is prohibited."
        "scope/policy,legacy ref,dataset/workspace/target,membership/bundle/"
        "artifact id/hash All are prohibited from filling in, and are not subject to a combination of modelling, model comparison, reporting,Strategy Pool,"
        "Adopt or deploy."
        "Yes.strategy_model_evidence_v2,workflow_inputs must be empty; only current ones are aggregatedtask"
        " There is a candidate for the authentication list variable.SampleDesign/candidate/artifact References bound by platform; training,"
        "Model comparison, monthly/OOT/Proactive requests for validation of models, reporting, adoption or deployment mustclarification;"
        "It is acceptable to state explicitly that no follow-up actions are undertaken; (Previously/Existing/Authenticated only after the current integrator action"
        "To be considered a source state; (no aggregate) (no aggregate) must be (unaggregated)clarification."
        "Yes.strategy_model_score_comparison_v2,workflow_inputs Must and can only include users"
        "Word by word.population andpartition.population Allow onlyapproval/risk;partition "
        "Allow onlyoverall/development/validation/oot.SampleDesign,Model score evidence, fraction vector,"
        "artifact id/hash,dataset/ref andregistry CAS All currently available from the platformtask Automatically discover,"
        "Select the latest compatible version and complete authentication, and ban output. At least two different models are required; this step is only for physical comparison"
        "Evidence, fixed.no_selection,Select, choose, adopt, or deploy."
        "- When deployed, you mustclarification;It is acceptable to state explicitly that these follow-up actions are not undertaken."
        "Yes.strategy_report_bundle_v2,workflow_inputs Only specified by the user can be includedtitle "
        "andstatus;status Allow onlydraft/partial/final.Fixed defaults must be used when not provided by the user"
        " title=Policy and iterative review reports,status=partial.ProjectContext,SampleDesign,Pool,"
        "ImpactCube/CompatibilityPoolImpact,ModelEvidence/training/score,strategy identity,"
        "report revision/previous head CAS,generated_at,artifact id/hash,Source citation and"
        "All indicators must be omitted and precisely bound by the platform when it is planned to be created.approval/"
        "reject/limit/pricing/segmentation,But...strategy_type It is also important to omit. Reporting requests must be"
        "Current, positive, single-step orders; question, deny,"
        "Assumptions, demonstrations, historical descriptions only, or convoluted training, scoring, candidate, impact measurement, adoption, deployment,"
        "You must go online.clarification."
        "Yes.strategy_dsl_delivery,workflow_inputs Only the only complete in the user's original language can be included"
        "Optionalstrategy_id;No, I'm not.ID It must be omitted from the platform only if there is only one deliverables for the current task"
        "The only bound.strategy_ref,Policy Type/version/spec hash,dataset_ref,Datahash,"
        "workspace_ref/revision/generation/semantic hash,"
        "maximum_equivalence_rows,artifact id/hash,The outcome and all indicators are bound by the platform."
        "Prohibits output. The request must be current, positive, single-step export command; query, negative, hypothetical, demonstration,"
        "Only historical descriptions, or conjunctive applications, writing back, reporting, impact measurement, training, scoring, adoption, promotion,"
        "- When deployed, you mustclarification."
        "Yes.automatic_tree_candidate_build,Only if the user specifically provides the copy.features,"
        "Weights/Amount fields, directions and tree parameters; not to fill in data binding, target column, label strategy,"
        "Budget, results, leaves, actions, ranking or recommendation, neither co-selection norStrategy Pool."
        "Yes.automatic_tree_apply,Only the only complete version of the user's original language can be copied verbatimtree_asset_id;"
        "leaf_id_column andrule_id_column Only clear foliage bar clearly indicated for users/Only when the rules are drawn"
        "Copy, not provided must be omitted and controlledTool Use default values. Do not fill insource artifact,"
        "artifact hash,asset hash,tree result hash,dataset/hash,workspace lineage,"
        "activate_result,Outcomes or indicators. It only createsdevelopment / unvalidated It's a living thing."
        "Dataset, not active for currentworkspace;No co-selection of leaves.Strategy Pool,Operations, reporting,"
        "Adopt or deploy."
        "Yes.automatic_tree_leaf_materialization,Only the only user in the original language can be copied verbatim"
        "Completetree_asset_id,Only fullleaf_id,And the user uses 'justifications'/Rationale/Reason/(The report of the Secretary-General on the implementation of the United Nations Millennium Declaration)"
        "Word by Word when visibleselection_reason;Unvisible labels must be omitted. It is created only"
        "pointer,No copying of rules, conditions, indicators, actions or platformsartifact/hash,And no connection."
        "Strategy Pool,Operational, adoption, deployment orleaf ID Write back.selection_reason - Yes, sir."
        "No reason for replacement, subsequent action, life cycle operation or extreme value should be hidden/ranking in the syllable; it accepts only"
        "Manual/Operations/Risk/Compliance/The sample evaluation was based on short descriptions of the categories."
        "Yes.interactive_tree_split_search,Only word for user positive commands"
        "Only completesource_tree_id,Only completenode_id,Clear"
        "all_features/selected_features Scope, maximum threshold values per feature and headline assessment"
        "(a) Budget;selected_features The only feature that you can use is a list of unique features.all_features I have to."
        "Ignorefeatures.No default budget can be filled, no platform can be exportedartifact/hash,The father chain,"
        "condition,metrics,dataset/workspace/SampleDesign Or a fine line, not a single round."
        "Winners, re-trees, automatic renewal, pool, application, reporting, adoption or deployment."
        "Yes.interactive_tree_auto_continuation,Only word for current user"
        "The only complete part of the affirmative commandsearch_id,Only complete and clearly selected by the user"
        "candidate_id,max_additional_depth,min_gini_gain,"
        "max_generated_nodes,max_thresholds_per_feature,"
        "max_row_evaluations,And fixed.objective=max_gini_gain and"
        "tie_break=eligible_gain_feature_threshold_candidate_id.All controls"
        "It must be made explicit by the user, not supplemented by default values, not ranked, best or first named"
        "Seed candidate. Do not output or overwritesource tree,node,artifact/hash,The father chain,"
        "condition,metrics,dataset/workspace/SampleDesign;These are the ones that...search "
        "Evidence is restored. Threads are not allowed to change thresholds, change variables, cut, enter pools, apply, report,"
        "Adopt or deploy."
        "Yes.interactive_tree_revision,Only the only complete of the current user positive command can be copied verbatim"
        " source_tree_id(candidate-asset- orinteractive-tree-revision- 32-bit back"
        "Lowercase hexadecimal, only completesplit node_id(node- Back to 20-bit lowercase hexadecimal,"
        "Oneoperation=prune_subtree,adjust_split_threshold or"
        "replace_split_feature,And the word-for-words of the user-specific labelsreason."
        "adjust_split_threshold Only limited number of words must be copied.threshold;"
        "replace_split_feature I have to copy the only one word for word.feature And the only thing that's limited.threshold;"
        "prune_subtree We have to omit it.feature/threshold.(Tighten the \"best threshold\""
        "(\"Auto-optimizing\" for best features, vague, recommended or batch modification requests such as \"all nodes\" must"
        "clarification.No output"
        "artifact/hash,The father chain,tree/frontier/condition/metrics,dataset/workspace/"
        "SampleDesign The platform will not be the best, the highest risk, or the most unstable or unstable."
        "The pronouns are used to select nodes for users, and no other tree editing, front-line materialization, pool entry, business action,"
        "Automatically continue, whole-tree application, report, adopt, deploy or write back."
        "Yes.interactive_tree_frontier_group_materialization,Only copy users verbatim"
        "The only complete of the current positive commandrevision_id(interactive-tree-revision- Pick up."
        "32 Bitcase hexadecimal, 2 to 50 unduplicated completessource_node_ids(node- "
        "orleaf- 20-bit lowercase hexadecimal) and word-to-word consistency in user-specific labels"
        "selection_reason.User must be clearOR/Logical or/Semantics of any member; order of entry of members"
        "No semantics, platform pressrevision frontier sequence. Do not outputselection/group/"
        "revision artifact,hash,The father chain,semantic tree,fragment/rule/effect,condition/"
        "metrics,dataset/workspace/SampleDesign Or move. Not with all, best, worst, worst."
        "Highest risk, automatic ranking or pronoun to select nodes for users, and not to be serializedStrategy Pool,"
        "Operational actions, applications, adoption, deployment or write-back."
        "Yes.interactive_tree_frontier_materialization,Only word for word user positive"
        "The only complete part of the commandrevision_id(interactive-tree-revision- 32-bit lowercase"
        "Hexadecimal, only completesource_node_id(node- orleaf- 20-bit lowercase"
        "Hexadecimal) and word for word when user visible labelsselection_reason.No output"
        "selection/revision artifact,hash,The father chain,semantic tree,fragment/rule/effect,"
        "condition/metrics,dataset/workspace/SampleDesign or actions, all restored by the platform."
        "Nodes may be selected for users by reference to their best, worst, highest risk, automatic ranking or pronoun, or in a rotational chain"
        "Strategy Pool,Operational actions, adoption, deployment or write-back."
        "Yes.voting_candidate_search,The user must clearly provide it verbatim.strategy_type,"
        "member_count/K,n andobjective metric+direction;The Chinese indicator should be used onlysystem "
        "prompt List aliases and output correspondingcanonical metric,(b) Prohibiting the self-expanding of obscurities;"
        "constraints,include_rule_ids,"
        "exclude_rule_ids If you do not provide an empty array, you can also use the same number as the one you have.max_combinations The fixed number is 10000 when not provided."
        "include/exclude Only the current sentence is given after the corresponding labelcandidate-rule ID."
        "Minimizebad_rate/weighted_bad_rate/bad_amount_rate , must provide a positive number separately"
        "hit_share/weighted_hit_share/hit_amount_share It's...gte No, no, no, no, no, no."
        "Replace. Do not outputPool ref/revision/hash,dataset/target,Line-by-line Matrix/target/weights/"
        "amounts,artifact,result or has calculated ranking. This step is only searching, not building, not selecting, not modifying."
        "or joinPool,Not applied, not adopted, not deployed; search/Find/OptimizationVoting The original words of the combination must be given priority."
        "Road to Ben.Workflow orclarification."
        "Yes.voting_candidate_build_from_search,Only the only complete version of the current user request can be copied verbatim"
        "It's...search_id,Only completecombo_id And the only one that's available.strategy_type;strategy_type"
        " Not clear. Not to outputartifact/hash,rule/entry/member IDs,n,rank,"
        "winner/champion,Indicators, outcomes orPool I'm not allowed to be in the first place.Top N,"
        "Select the group of the same expression that you just have. This step is to build only candidates; join the pool with a string, modify itPool,Settings"
        "must be actiond, applied, adopted, deployed or returnedclarification.It must take precedence over research and"
        "Freedom.rule ID Voting Builds the route."
        "Yes.voting_candidate_build,Only word for word can be copied from the user.strategy_type,"
        "2 To 50 Completecandidate-rule ID and integern;No outputentry_id,Pool revision/hash,"
        "condition,Indicators, actions, recommendations or Platform data binding. The rules must be all from the same positive direction"
        "Voting/n-of-k Build commands; \"Better rules\" \"just those\" inspirational references, or a string of words linking to the pool,"
        "The action, adoption, deployment, and return must be clarified./The future./Historical description, presentation text, end of sentence"
        "Undo and multiplestrategy_type/n Candidates must also be clarified; visiblek I must.rule_ids Numbers are consistent."
        "Yes.candidate_monthly_stability,workflow_inputs You have to choose one: copy only."
        "Only full in user originalasset_id,Or just copying the user's specifics.strategy_type & Complete with Only"
        "entry_id.Ban Outputsource_kind,source artifact/hash,asset hash,Pool "
        "revision/hash,dataset/workspace/semantic,SampleDesign,target,month_col,"
        "Benchmarks, indicators or outcomes; these values are presented by the Platformpreflight Restore. Prosthesis, multiple.pointer,"
        "Question, deny, history./The future./Assume description, or joins a string of pools, deletes, reorders, compiles, writes back,"
        "Reporting, adoption and deployment mustclarification."
        "Yes.cross_matrix_candidate_search,Only the only user who can copy word for word"
        "features=[...] 2 to 20 white list fields and clear 1 in the list..190 "
        "max_pairs;You must not fill in the axle method, or the other.source artifact/"
        "candidate/evidence hash,dataset/target/sample,candidate asset,"
        "pair/rank/winner/champion,Indicator or result. Platform binds precise proof of single-variant parent and"
        " risk/development and byTool Select the highest ranking in parent evidence for each field"
        ". This step is to be searched only, not build, not select, not enter, not apply, not accept, not accept, not accept, not use, not use, not use, not use, not use, not use, not use, not use, not use, not use, not use, not use, not use,"
        "No deployment; follow-up actions for the same round mustclarification."
        "Yes.cross_matrix_candidate_build_from_search,Only the current textually"
        "Only complete in requestcross-search ID With the only completecross-pair ID.No way."
        "Outputartifact/hash,Axis Fields/Methodology,asset fingerprint,rank/winner/"
        "champion,Indicators or results should not be used as a basis forTop N,That or a pronoun."
        "Select. It must be a follow-up one-step construction request; research, enter, set actions,"
        "Application, adoption, deployment or return mustclarification."
        "Yes.cross_rule_search,Only the only user who can copy word for wordfeatures=[...] in the list"
        "2 to 12 white list fields,dimension=2/3,Completeconstraints"
        "(min_lift,min_bad_count,max_hit_share,min_amount_lift)and 1..5000 "
        "max_trials;All controls must be provided in the current request.source "
        "artifact/hash,dataset/target/sample,Threshold, direction,rule/rank/winner/"
        "champion,The platform restores thresholds and risk orientations from the latest authentication single variable evidence."
        "Andrisk/development Samples are budgeted for 2D/3D aggregate search. This step is only to search and"
        "The sequence is fully evaluated, and is not automatically selected, constructed, built, in-pooled, applied, not accepted, not deployed."
        "Yes.cross_rule_candidate_build_from_search,Only copying current request verbatim"
        "Only completecross-rule-search ID,Only completecross-rule ID,And users"
        "during the visible labelselection_reason;No visible labels must be omitted. No outputartifact/"
        "hash,Conditions, thresholds, direction,rank/winner/champion,Nor shall the indicators or results be used"
        "Number one, best,Top N or the pronoun selection. It only builds an unverified candidate precisely; enters the pool,"
        "Additional requests for action, application, adoption or deployment are required."
        "Yes.cross_matrix_analysis,Only two clear axle fields, each method and the user clearly gave them to you"
        "Parameters for single variables; no output of Platform data binding, target column, budget, boundary,cell,condition,"
        "Indicators,artifact/asset/effect/rule id,Actions or recommendations. It builds only 2D matrix evidence, not"
        "Serial selection, pool, code, write back, adopt or deploy; clear 2DCross Matrix Request is not allowed."
        "Change route to otherWorkflow."
        "Yes.cross_matrix_cell_selection,Only the only complete version of the user's original language can be copied verbatim"
        "cross_asset_id,1 400 completes without repetitioncross-cell ID,And when visible"
        "Word-to-word.selection_reason.No pronouns, no rankings, no verbs.Top N,Risk/Indicator extremes or thresholds"
        "Select the cells.cell is the syntax of a collection and is converted from platform to certainty by source matrix orderOR;No output"
        "condition,rule,effect,metrics,action Or any of them.artifact/hash Platform binding. It just..."
        "Createpointer,No strings.Strategy Pool,Operations, adoption, deployment, commissioning or write-back."
        "Yes.strategy_pool_add_candidate,candidate_asset_id andselection_id "
        "Strictly double-check and must reproduce the only complete text.ID;You must copy the tack type, the tack type, the tack type, the tack type, the tatter type, the tatter type, the tatter type, the tatter type, the tatter type, the tatter type, the tatter type, the tiding type, the tidbit type, the typography type, the tidly type, the tidly type."
        "Pool Default action and hit action tag, cannot be contrasted or reversed from actionPool Type.reason Only"
        "Word-by-word when visible labels are not indicated; default/Hit.reason_code,output_value and"
        "value You must also be classified word for word, without omitting or converse.placement_mode Only"
        "Text by Wordbefore_selected_members/replace_selected_members,or from (reserve members)"
        "As retreat and in front of the members/ByVoting Substitute member's double-check map; omitted when not provided by user."
        "Rejecting pool or serial adoption/On deployment"
        "It must be clarified.selection_id Only allowedautomatic-tree-leaf-selection-,"
        "interactive-tree-frontier-group-selection-,"
        "interactive-tree-frontier-selection-,cross-matrix-cell-selection- Pick up."
        "32 bit lowercase hexadecimal;completeCross Matrix asset"
        "Can't go straight into the pool.source ID The only positive entry order must be in the same sub-rule, not from the negative sub-rule,"
        "reason,Quoted or borrowed from the context of the pronoun; future/Conditional instructions, questions,how-to,And the demonstration and the test."
        "It must be clarified."
        "Yes.strategy_pool_stability,Only the only clear message in the current user positive command can be copied verbatim"
        "5 categoriesstrategy_type.partitions,exact ImpactCube/Pool/SampleDesign "
        "artifact,revision/hash,dataset/workspace/target,threshold,PSI,Distribution,"
        "All indicators and results are closed, created by the Platform and two stepsWorkflow Freezing or"
        "Determines the calculation of certainty. Negative, question, history/The future./Assumptions, reporting only, or same round of modificationsPool,Application,"
        "When creating, adopting, promoting, deploying,clarification.The result is a stable distribution across the regions."
        "Not independent effects validation, and it won't be modified.Pool Or enter the life cycle of the strategy."
        "Yes.strategy_impact_cube,Only five categories identified by the user can be copiedstrategy_type,"
        "Optionaldevelopment/validation/oot partitions,Precisionmonth_col/group_col/"
        "segment_col,Completecurrent_strategy_id,andtyped economics_inputs"
        "(Each one onlycolumn Or limited.scalar).No outputPool/SampleDesign artifact,"
        "revision/hash,population,target,metrics,condition orstrategy_spec."
        "(a) All non-empty available partitions in the latest sample design selected by the platform were omitted when the user did not specify the partition;"
        "The only semantic character that is identified is bound by the platform when the user does not specify the dimension column. Any original language control is omitted, and the user is not allowed to use the word \"syntax\" column."
        "Replacing, denying, or retrieving, reporting, adoption, promotion, deployment must be clarified."
        "Yes.strategy_dsl_delivery,Only the only complete option in the original user's language can be copied verbatim"
        " strategy_id;You must omit without calling. You cannot outputstrategy_ref,Policy Type/version/"
        "spec hash,dataset_ref/hash,workspace_ref/revision/generation/"
        "semantic hash,Sample budget, equivalentartifact id/hash,Code content,"
        "Equivalent result or indicator. It only exports offlinePython/SQL/JSON The evidence of the price is the same as the evidence that clearly indicates the range."
        "No serial application, write-back, report, impact measurement, training, rating, adoption, promotion or deployment shall be permitted."
        "Yes.strategy_pool_impact,Only copying the user's clearapproval/reject Pool Type,"
        "Optionalabsolute/vs_baseline Comparison mode, completenessbaseline_strategy_id,Precisionmonth_col/"
        "loan_amount_col/overdue_amount_col And clear.drop_nan_labels Boolean authorizes. Normal positive."
        "Request Defaultabsolute;vs_baseline It must be accompanied by a comparative expression and a complete baseline in the original language.ID."
        "Ban Outputdataset/target,Pool revision/hash,workspace,sample binding,semantic hash,"
        "metrics,conditions orstrategy_spec.Month not specified by user/The amount line must be omitted. The platform will only"
        "Use only recognized semantic characters; no charactersunavailable,The role of the Quartet is clear.Agent Don't guess."
        "limit/pricing/segmentation,Negative./Question/History/Report or change in the same cycle only/Accepted/Deployment must be clarified."
        "Yes.strategy_pool_validation,Only the only one in the current user positive command can be copied verbatim"
        "Five distinct categoriesstrategy_type andvalidation/oot partition."
        "Pool ref/revision/hash/artifact,SampleDesign membership/bundle/ref,"
        "dataset/workspace/target,requirements,population,comparison_mode,"
        "All entries are banned for indicators, months, status and results, and are planned to be created and implemented by the PlatformTool Recovery at implementation."
        "development,Missing or multiple types/Division, question,"
        "Negative, history./The future./Assumptions, or same round changesPool,Application, reporting, promotion, adoption, deployment"
        "I have to.clarification.It only releases.native typed independent replay evidence,"
        "No claim."
        "PSI,stability ordrift,I won't change it.Pool,Create, promote, adopt or deploy strategies."
        "Yes.strategy_pool_apply,Only the only five categories identified in the current user positive command can be copied"
        "strategy_type,and the user with \"Output prefix\"/output_prefix/output prefix/prefix)"
        "Optional for visible labelsASCII identifier output_prefix;If not provided, it must be omitted andTool"
        " Use the default value.expected Pool revision/snapshot hash,Pool/artifact,dataset,"
        "SampleDesign,requirements,StrategySpec,The target and life cycle state are completely off limits."
        "The request must clearly identify the currentPool Apply or write back the current sample,"
        "and must be current, positive, single-step; negative, question, history/The future./Assumptions, vagueness or morePool,"
        "Or in a string.Pool Modification, adoption, activation, deployment, online, export or reporting mustclarification."
        "The result is only the creation of non-variable data sets, not the activation of the current one.workspace,Not accepted, not deployed."
        "Yes.strategy_pool_materialize,Only the only clear message in the user 's current positive command can be copied"
        "Category 5strategy_type.Pool revision/snapshot hash,Pool artifact id/content "
        "hash,design hash,StrategySpec,requirements,Indicators and indicatorslifecycle All are forbidden."
        "Fill in, created and built by the platform in the planTool Restore at execution. Request must clearly identify the currentPool Physicalization/"
        "Solid/Create asdraft Strategy,and must be current, positive, single-step; negative, question,"
        "History/The future./Assumptions, vagueness or morePool,or in a chain of rotations, deployment, retrometry, application, reporting,"
        "Monitoring orDSL Export mustclarification.This step only createsdraft Strategy,Not adopted,"
        "No deployment, no claims of follow-upreadiness."
    )

def _repair_prompt(prompt: str, *, raw: object, error: str) -> str:
    if isinstance(raw, Mapping):
        raw_text = json.dumps(raw, ensure_ascii=False, default=str)
    else:
        raw_text = str(raw)
    raw_text = raw_text[:4000]
    return (
        f"{prompt}\n\n"
        "[Last output not verified through platform]\n"
        f"Error:{error}\n"
        f"Last output:{raw_text}\n"
        "This is the only opportunity to fix it. Please remove the unknown field, fix the type/Scope/(a) Listing;"
        "Only Chinese if you can't be sureclarification.The output of any indicator results is still prohibited."
    )

def _invalid(
    message: str,
    *,
    code: str = "invalid_strategy_request",
    fields: Iterable[str] = (),
) -> _ValidationOutcome:
    return _ValidationOutcome(
        _clarification(message, code=code, fields=fields),
        False,
        message,
    )

def _clarification(
    message: str,
    *,
    code: str = "clarification_required",
    fields: Iterable[str] = (),
) -> StrategyRequestCompilation:
    return StrategyRequestCompilation(
        draft=None,
        clarification=message,
        confirmation=None,
        clarification_code=code,
        clarification_fields=tuple(dict.fromkeys(str(field) for field in fields)),
    )

def _chinese_clarification(message: str) -> str:
    normalized = message.strip()
    if _CJK_RE.search(normalized):
        return normalized
    return "Please add more specific strategic operations, types of strategies and related target audiences."

_OPERATION_LABELS = {
    "develop": "Development",
    "analyze": "Analysis",
    "backtest": "Retrospect",
    "apply": "Apply",
    "compare": "Comparison",
    "adopt": "Accepted",
    "report": "Generate Report",
    "monitor": "Monitor",
    "mine_rules": "Rule dig",
}

_TYPE_LABELS = {
    "approval": "Approval strategy",
    "reject": "Reject Policy",
    "limit": "Scale Policy",
    "pricing": "Pricing policy",
    "segmentation": "Group Policy",
}
