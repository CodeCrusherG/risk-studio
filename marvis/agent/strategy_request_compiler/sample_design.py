"""sample_design request-compiler handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
import re
from typing import Any
from marvis.agent.strategy_workflows._foundation_delivery import is_sample_design_v2_fresh_partition_selector

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import StandardWorkflowRequestDraft
    from . import StrategyRequestCompilation
    from . import _DraftValidationError
    from . import _ROLL_RATE_COLUMN_ROLE_LABELS
    from . import _automatic_tree_column_mention_resolution
    from . import _clarification
    from . import _has_positive_chained_operation
    from . import _simple_partition_equality
    from . import _utterance_contains_token

_SAMPLE_DESIGN_SUBJECT_RE = re.compile(
    r"(?:Policy)?Sample(?:Design|Border|Programme)|sample(?:\s|-|_)*design|"
    r"performance\s+window|Performance(?:Window|Period).{0,20}(?:Grown up.|Observation|Sample)",
    re.IGNORECASE,
)

_SAMPLE_DESIGN_ACTION_RE = re.compile(
    r"(?:Create|Generate|Build|Create|Start|Completed|Design|Solid|Freeze|Physicalization|Calculate|Analysis|Explore|First.)|"
    r"(?<![A-Za-z0-9_])(?:create|build|design|freeze|materialize|"
    r"compute|analy[sz]e|explore)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_SAMPLE_DESIGN_NEGATED_ACTION_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|Don't.|Ban|Cancel|Not yet.|Not yet.)\s*"
    r"(?:Create|Generate|Build|Create|Start|Completed|Design|Solid|Freeze|Physicalization|Calculate|Analysis|Explore)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cancel)\s+"
    r"(?:create|build|design|freeze|materialize|compute|analy[sz]e|explore)",
    re.IGNORECASE,
)

_SAMPLE_DESIGN_NONCOMMAND_RE = re.compile(
    r"[??]|(?:Can you...|Can I?|Is it possible?|Is that okay?|Can you...|How's that?|What?|What?|Assumptions|Suppose...|If|"
    r"Yesterday.|Before|Before|Go on.|Last time.|History|The future.|In the future|Later|Later.|Tomorrow.|Next week.|Next month)|"
    r"(?<![A-Za-z0-9_])(?:can\s+you|could\s+you|would\s+you|what\s+if|"
    r"how\s+to|yesterday|previously|earlier|in\s+the\s+future|later|"
    r"tomorrow|next\s+(?:week|month))(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_SAMPLE_DESIGN_MATURITY_PATTERNS = {
    "confirmed_matured": re.compile(
        r"(?:Confirm.(?:Yes)?|Already|Already|Clear(?:Yes)?)(?:Total)?Grown up.|"
        r"Mature.{0,10}(?:Confirm.(?:Yes)?(?:Already)?Grown up.|mature|Confirmed)|"
        r"(?:confirmed|fully)\s+matured",
        re.IGNORECASE,
    ),
    "not_matured": re.compile(
        r"(?:Not yet|Not yet.|Not|No, no.)(?:Total)?Grown up.|not\s+(?:yet\s+)?matured?",
        re.IGNORECASE,
    ),
    "unknown": re.compile(
        r"(?:Mature|maturity).{0,12}(?:Unknown|I'm not sure.|I don't know.|unknown)|"
        r"(?:Unknown|I'm not sure.|I don't know.|unknown).{0,12}(?:Mature|maturity)",
        re.IGNORECASE,
    ),
}

_SAMPLE_DESIGN_V2_PLATFORM_CONTROL_RE = re.compile(
    r"\b(?:legacy_sample_design_ref|scope|policy|dataset_id|"
    r"expected_[a-z0-9_]*hash|workspace_(?:revision|generation)|"
    r"analysis_generation|semantic_mapping_hash|target_col|artifact(?:_id)?|"
    r"sample_design_(?:id|ref)|membership_(?:id|ref)|bundle_(?:id|ref)|"
    r"content_hash|request_hash)\b|"
    r"(?:Dataset|Sample|Work|Products|bundle|membership)\s*(?:ID|id|hash|Hash.|References)|"
    r"Workspace\s*(?:revision|generation|Version|Substitute)|Policy sample(?:Design)?\s*(?:ID|id|References)|"
    r"(?:Diagnosis)?Policy\s*(?:policy|Policy)|(?:Analysis)?Scope\s*(?:scope|Policy)",
    re.IGNORECASE,
)

_SAMPLE_V2_POPULATION_ROLE_RE = re.compile(
    r"(?:Approval(?:Overall|Sample)|approval\s+population|"
    r"Risk(?:Overall|Sample)|risk\s+population)",
    re.IGNORECASE,
)

_SAMPLE_V2_POPULATION_DIRECTION_RE = re.compile(
    r"(?P<exclusion>Exclude|Remove|Not included|exclusion|exclude)"
    r"|(?P<inclusion>(?<!No, no.)Inclusion|Organisation|Reservations|inclusion|include)",
    re.IGNORECASE,
)

_SAMPLE_DESIGN_V2_CHAIN_RE = re.compile(
    r"(?:Modelling|Training model|Scorecard|Autotree|Decision Tree|Leaf Node|Policy pool|Into the pool.|Accepted|Adopt|Deployment|"
    r"Production|Online.|Generate Report|Form a report|Report.|Model report|Clean|Pumpkin.(?:Fields|Columns|Variables)|"
    r"Add(?:Fields|Columns|Variables))|"
    r"(?<![A-Za-z0-9_])(?:model(?:ing)?|scorecard|automatic\s+tree|decision\s+tree|"
    r"strategy\s+pool|adopt|deploy|production|report|clean|derive)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_SAMPLE_DESIGN_V2_NULLABLE_STRING_SCHEMA = {
    "anyOf": [
        {"type": "string", "minLength": 1},
        {"type": "null"},
    ]
}

_SAMPLE_DESIGN_V2_SCALAR_SCHEMA = {
    "anyOf": [
        {"type": "string", "minLength": 1},
        {"type": "number"},
        {"type": "boolean"},
    ]
}

_SAMPLE_DESIGN_V2_CONDITION_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "column": {"type": "string", "minLength": 1},
                "operator": {
                    "type": "string",
                    "enum": ["eq", "ne", "gt", "gte", "lt", "lte"],
                },
                "value": _SAMPLE_DESIGN_V2_SCALAR_SCHEMA,
            },
            "required": ["column", "operator", "value"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "column": {"type": "string", "minLength": 1},
                "operator": {
                    "type": "string",
                    "enum": ["is_null", "is_not_null"],
                },
            },
            "required": ["column", "operator"],
            "additionalProperties": False,
        },
    ]
}

_SAMPLE_DESIGN_V2_POPULATION_FILTER_SCHEMA = {
    "anyOf": [
        {"type": "null"},
        {
            "type": "object",
            "properties": {
                "match": {"type": "string", "enum": ["all", "any"]},
                "conditions": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 8,
                    "items": _SAMPLE_DESIGN_V2_CONDITION_SCHEMA,
                },
            },
            "required": ["match", "conditions"],
            "additionalProperties": False,
        },
    ]
}

_SAMPLE_DESIGN_V2_PREDICATE_LEAF_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "op": {
                    "type": "string",
                    "enum": ["eq", "ne", "gt", "gte", "lt", "lte"],
                },
                "left": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "minLength": 1},
                    },
                    "required": ["column"],
                    "additionalProperties": False,
                },
                "right": {
                    "type": "object",
                    "properties": {
                        "literal": _SAMPLE_DESIGN_V2_SCALAR_SCHEMA,
                    },
                    "required": ["literal"],
                    "additionalProperties": False,
                },
            },
            "required": ["op", "left", "right"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "op": {
                    "type": "string",
                    "enum": ["is_null", "is_not_null"],
                },
                "arg": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "minLength": 1},
                    },
                    "required": ["column"],
                    "additionalProperties": False,
                },
            },
            "required": ["op", "arg"],
            "additionalProperties": False,
        },
    ]
}

_SAMPLE_DESIGN_V2_PARTITION_SELECTOR_SCHEMA = {
    "anyOf": [
        _SAMPLE_DESIGN_V2_PREDICATE_LEAF_SCHEMA,
        {
            "type": "object",
            "properties": {
                "op": {"type": "string", "enum": ["and", "or"]},
                "args": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 8,
                    "items": _SAMPLE_DESIGN_V2_PREDICATE_LEAF_SCHEMA,
                },
            },
            "required": ["op", "args"],
            "additionalProperties": False,
        },
    ]
}

_SAMPLE_DESIGN_V2_DATE_BOUND_SCHEMA = {
    "anyOf": [
        {"type": "string", "format": "date"},
        {"type": "null"},
    ]
}

_SAMPLE_DESIGN_V2_TIME_RANGE_SCHEMA = {
    "type": "object",
    "properties": {
        "start": _SAMPLE_DESIGN_V2_DATE_BOUND_SCHEMA,
        "end": _SAMPLE_DESIGN_V2_DATE_BOUND_SCHEMA,
    },
    "required": ["start", "end"],
    "additionalProperties": False,
}

_SAMPLE_DESIGN_V2_PARTITIONING_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "method": {"const": "predicate_ast"},
                "selectors": {
                    "type": "object",
                    "properties": {
                        "development": _SAMPLE_DESIGN_V2_PARTITION_SELECTOR_SCHEMA,
                        "validation": _SAMPLE_DESIGN_V2_PARTITION_SELECTOR_SCHEMA,
                        "oot": _SAMPLE_DESIGN_V2_PARTITION_SELECTOR_SCHEMA,
                    },
                    "required": ["development", "validation", "oot"],
                    "additionalProperties": False,
                },
            },
            "required": ["method", "selectors"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "method": {"const": "time_ranges"},
                "column": {"type": "string", "minLength": 1},
                "ranges": {
                    "type": "object",
                    "properties": {
                        "development": _SAMPLE_DESIGN_V2_TIME_RANGE_SCHEMA,
                        "validation": _SAMPLE_DESIGN_V2_TIME_RANGE_SCHEMA,
                        "oot": _SAMPLE_DESIGN_V2_TIME_RANGE_SCHEMA,
                    },
                    "required": ["development", "validation", "oot"],
                    "additionalProperties": False,
                },
            },
            "required": ["method", "column", "ranges"],
            "additionalProperties": False,
        },
    ]
}

_SAMPLE_DESIGN_V2_CORRECTION_WORKFLOW_INPUTS_SCHEMA = {
    "type": "object",
    "properties": {
        "target_bad_value": {"type": "integer", "enum": [0, 1]},
        "drop_nan_labels": {"type": "boolean"},
        "relationship": {
            "type": "string",
            "enum": ["nested_same_cohort", "parallel_time_cohorts"],
        },
        "approval_population": {
            "type": "object",
            "properties": {
                "inclusion": _SAMPLE_DESIGN_V2_POPULATION_FILTER_SCHEMA,
                "exclusion": _SAMPLE_DESIGN_V2_POPULATION_FILTER_SCHEMA,
            },
            "required": ["inclusion", "exclusion"],
            "additionalProperties": False,
        },
        "risk_population": {
            "type": "object",
            "properties": {
                "inclusion": _SAMPLE_DESIGN_V2_POPULATION_FILTER_SCHEMA,
                "exclusion": _SAMPLE_DESIGN_V2_POPULATION_FILTER_SCHEMA,
            },
            "required": ["inclusion", "exclusion"],
            "additionalProperties": False,
        },
        "partitioning": _SAMPLE_DESIGN_V2_PARTITIONING_SCHEMA,
        "maturity": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": [
                        "confirmed_matured",
                        "not_matured",
                        "unknown",
                        "unavailable",
                    ],
                },
                "performance_window_days": {
                    "anyOf": [
                        {"type": "integer", "minimum": 1},
                        {"type": "null"},
                    ]
                },
                "cutoff_date": _SAMPLE_DESIGN_V2_DATE_BOUND_SCHEMA,
                "reason": _SAMPLE_DESIGN_V2_NULLABLE_STRING_SCHEMA,
            },
            "required": [
                "status",
                "performance_window_days",
                "cutoff_date",
                "reason",
            ],
            "additionalProperties": False,
        },
        "performance_window": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["provided", "unavailable"],
                },
                "days": {
                    "anyOf": [
                        {"type": "integer", "minimum": 1},
                        {"type": "null"},
                    ]
                },
            },
            "required": ["status", "days"],
            "additionalProperties": False,
        },
        "observation_window": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["provided", "unavailable"],
                },
                "start": _SAMPLE_DESIGN_V2_DATE_BOUND_SCHEMA,
                "end": _SAMPLE_DESIGN_V2_DATE_BOUND_SCHEMA,
            },
            "required": ["status", "start", "end"],
            "additionalProperties": False,
        },
        "field_bindings": {
            "type": "object",
            "properties": {
                field: _SAMPLE_DESIGN_V2_NULLABLE_STRING_SCHEMA
                for field in (
                    "entity_field",
                    "time_field",
                    "group_field",
                    "month_field",
                    "weight_field",
                    "loan_amount_field",
                    "overdue_amount_field",
                )
            },
            "required": [
                "entity_field",
                "time_field",
                "group_field",
                "month_field",
                "weight_field",
                "loan_amount_field",
                "overdue_amount_field",
            ],
            "additionalProperties": False,
        },
        "historical_score": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["available", "unavailable", "not_applicable"],
                },
                "column": _SAMPLE_DESIGN_V2_NULLABLE_STRING_SCHEMA,
                "direction": {
                    "anyOf": [
                        {
                            "type": "string",
                            "enum": [
                                "higher_is_riskier",
                                "lower_is_riskier",
                            ],
                        },
                        {"type": "null"},
                    ]
                },
                "reason": _SAMPLE_DESIGN_V2_NULLABLE_STRING_SCHEMA,
            },
            "required": ["status", "column", "direction", "reason"],
            "additionalProperties": False,
        },
    },
    "required": [
        "target_bad_value",
        "drop_nan_labels",
        "relationship",
        "approval_population",
        "risk_population",
        "partitioning",
        "maturity",
        "performance_window",
        "observation_window",
        "field_bindings",
        "historical_score",
    ],
    "additionalProperties": False,
}

SAMPLE_DESIGN_V2_CORRECTION_JSON_SCHEMA = {
    "name": "strategy_sample_design_v2_correction",
    "strict": False,
    "schema": {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "request_kind": {"const": "standard_workflow"},
                    "workflow": {"const": "strategy_sample_design_v2"},
                    "workflow_inputs": (
                        _SAMPLE_DESIGN_V2_CORRECTION_WORKFLOW_INPUTS_SCHEMA
                    ),
                },
                "required": ["request_kind", "workflow", "workflow_inputs"],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {
                    "clarification": {"type": "string", "minLength": 1},
                },
                "required": ["clarification"],
                "additionalProperties": False,
            },
        ],
    },
}

def _roll_rate_explicit_column_bindings(
    utterance: str,
    *,
    whitelist: tuple[str, ...],
    target_col: str | None,
) -> tuple[dict[str, set[str]], bool]:
    """Bind exact resolved column mentions to explicit roll-rate roles only."""

    known_columns = tuple(
        dict.fromkeys(
            (
                *whitelist,
                *((target_col,) if target_col is not None else ()),
            )
        )
    )
    mentions, ambiguous = _automatic_tree_column_mention_resolution(
        utterance,
        known_columns,
    )
    if ambiguous:
        return {}, True

    bindings = {role: set() for role in _ROLL_RATE_COLUMN_ROLE_LABELS}
    for start, end, column in mentions:
        prefix = utterance[max(0, start - 48) : start]
        suffix = utterance[end : min(len(utterance), end + 48)]
        for role, label in _ROLL_RATE_COLUMN_ROLE_LABELS.items():
            before = re.compile(
                rf"(?:{label})\s*"
                rf"(?:(?:Yes|Yes.|Use|Use|Selection|Assign)\s*)?"
                rf"(?:=|:|:)?\s*$",
                re.IGNORECASE,
            )
            after = re.compile(
                rf"^\s*(?:(?:As|Use as|Yes.|Yes)\s*)?(?:{label})",
                re.IGNORECASE,
            )
            if before.search(prefix) or after.search(suffix):
                bindings[role].add(column)
    return (
        {role: values for role, values in bindings.items() if values},
        False,
    )

def _ground_roll_rate_column_bindings(
    utterance: str,
    result: StrategyRequestCompilation,
    *,
    whitelist: tuple[str, ...],
    target_col: str | None,
) -> StrategyRequestCompilation:
    draft = result.draft
    if not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "roll_rate_matrix"
    ):
        return result
    bindings, ambiguous = _roll_rate_explicit_column_bindings(
        utterance,
        whitelist=whitelist,
        target_col=target_col,
    )
    if ambiguous:
        return _clarification(
            "There is an overlap in the explicit listing in the rolling rate request; pleaseID,Time, status and balance weights"
            "One complete and only existing listing is provided separately.",
            code="roll_rate_column_binding_not_grounded",
            fields=("workflow_inputs",),
        )
    inputs = draft.workflow_inputs
    mismatched = tuple(
        role
        for role, values in bindings.items()
        if len(values) != 1 or inputs.get(role) not in values
    )
    if mismatched:
        return _clarification(
            "The rolling rate draft must be kept word for word and word for word.ID,(a) Time, status and balance weighting binding;"
            "No other data column can be replaced with the same.",
            code="roll_rate_column_binding_not_grounded",
            fields=mismatched,
        )
    return result

def utterance_targets_strategy_sample_design(utterance: str) -> bool:
    """Return true only when a build verb targets the sample-design subject.

    References such as ``Build automatic trees based on solid sample`` must remain with
    their downstream workflow, so co-occurrence anywhere in a clause is not
    sufficient authorization to materialize a new sample design.
    """

    before_subject_actions = {
        "Create",
        "Generate",
        "Build",
        "Create",
        "Start",
        "Completed",
        "Design",
        "Solid",
        "Freeze",
        "Physicalization",
        "create",
        "build",
        "design",
        "freeze",
        "materialize",
    }
    after_subject_actions = {
        "Create",
        "Generate",
        "Create",
        "Start",
        "Completed",
        "Solid",
        "Freeze",
        "Physicalization",
        "create",
        "freeze",
        "materialize",
    }
    reference_prefix = re.compile(
        r"(?:Based on|Use|References|Basis|According to|Dependency|Continue|using|based\s+on|refer(?:ring)?\s+to)\s*$",
        re.I,
    )
    past_prefix = re.compile(
        r"(?:Already|Already|Tsang.|Once.|Before|History|already|previously)\s*$",
        re.I,
    )
    for clause in _sample_design_clauses(utterance):
        subjects = tuple(_SAMPLE_DESIGN_SUBJECT_RE.finditer(clause))
        actions = tuple(_SAMPLE_DESIGN_ACTION_RE.finditer(clause))
        for subject in subjects:
            subject_prefix = clause[max(0, subject.start() - 14) : subject.start()]
            subject_is_reference = reference_prefix.search(subject_prefix) is not None
            for action in actions:
                if action.start() < subject.end() and subject.start() < action.end():
                    continue
                token = action.group(0).lower()
                action_prefix = clause[max(0, action.start() - 12) : action.start()]
                if _SAMPLE_DESIGN_NEGATED_ACTION_RE.search(
                    clause[max(0, action.start() - 12) : action.end()]
                ):
                    continue
                if action.end() <= subject.start():
                    gap = clause[action.end() : subject.start()]
                    if (
                        token in before_subject_actions
                        and len(gap) <= 24
                        and "It's..." not in gap
                        and past_prefix.search(action_prefix) is None
                    ):
                        return True
                elif subject.end() <= action.start():
                    gap = clause[subject.end() : action.start()]
                    if (
                        not subject_is_reference
                        and token in after_subject_actions
                        and len(gap) <= 8
                    ):
                        return True
    return False

def _sample_design_build_intent_negated(utterance: str) -> bool:
    subject = r"(?:(?:Policy)?Sample(?:Design|Border|Programme)|sample(?:\s|-|_)*design)"
    action = (
        r"(?:Create|Generate|Build|Create|Start|Completed|Design|Solid|Freeze|Physicalization|Calculate|Analysis|Explore|"
        r"create|build|design|freeze|materialize|compute|analy[sz]e|explore)"
    )
    negation = (
        r"(?:Don't.|No, I'm fine.|No need.|Don't.|Ban|Cancel|Not yet.|Not yet.|"
        r"do\s+not|don't|never|cancel)"
    )
    clauses = re.split(r"[;;..!??\n,,,/]+", utterance)
    return any(
        re.search(rf"{negation}\s*{action}.{{0,16}}{subject}", clause, re.I)
        or re.search(rf"{negation}\s*{subject}.{{0,12}}{action}", clause, re.I)
        for clause in clauses
    )

def _ground_strategy_sample_design_v2_request(
    utterance: str,
    result: StrategyRequestCompilation,
    *,
    whitelist: tuple[str, ...],
) -> StrategyRequestCompilation:
    """Ground every user-owned V2 control before a compatibility plan exists."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if _sample_design_build_intent_negated(utterance):
        return _clarification(
            "It's a negative or a null.V2 Sample design solidified and the current cycle does not create plans.",
            code="strategy_sample_design_v2_intent_negated",
            fields=("build_intent",),
        )
    if (
        not utterance_targets_strategy_sample_design(utterance)
        or _SAMPLE_DESIGN_NONCOMMAND_RE.search(utterance)
    ):
        return _clarification(
            "Please use a current, positive command to confirm it.V2 (a) Strategy sample design;"
            "Questions, assumptions, history or future descriptions will not be considered as immediate implementation of the mandate.",
            code="strategy_sample_design_v2_positive_command_required",
            fields=("build_intent",),
        )
    if _sample_design_v2_has_chained_operation(utterance):
        return _clarification(
            "This wheel can only generate compatible anchors and stabilize them.V2 Two-total sample evidence; modelling, comparison, reporting,"
            "Strategy Pool,Adoption and deployment must be completed in the form of a follow-up request.",
            code="strategy_sample_design_v2_single_step_required",
            fields=("next_action",),
        )
    if _SAMPLE_DESIGN_V2_PLATFORM_CONTROL_RE.search(utterance):
        return _clarification(
            "legacy ref,scope,policy,Data identity,workspace And all"
            " artifact/id/hash Both by Currenttask Tie, not injected by natural language.",
            code="strategy_sample_design_v2_platform_binding_forbidden",
            fields=("platform_binding",),
        )

    missing: list[str] = []
    performance = inputs["performance_window"]
    if not _sample_design_performance_grounded(
        utterance,
        status=performance["status"],
        days=performance["days"],
    ):
        missing.append("performance_window")
    observation = inputs["observation_window"]
    if not _sample_design_observation_grounded(
        utterance,
        status=observation["status"],
        start=observation["start"],
        end=observation["end"],
    ):
        missing.append("observation_window")
    maturity = inputs["maturity"]
    maturity_status_grounded = (
        _sample_design_maturity_grounded(utterance, maturity["status"])
        if maturity["status"] != "unavailable"
        else re.search(
            r"(?:Mature|maturity).{0,12}(?:Not yet.|Not yet.|Not provided|Not Available|unavailable)|"
            r"(?:Not yet.|Not yet.|Not provided|Not Available|unavailable).{0,12}(?:Mature|maturity)",
            utterance,
            re.I,
        )
        is not None
    )
    if not maturity_status_grounded:
        missing.append("maturity.status")
    maturity_days = maturity["performance_window_days"]
    if maturity_days is not None and not _sample_v2_maturity_days_grounded(
        utterance,
        maturity_days,
    ):
        missing.append("maturity.performance_window_days")
    maturity_cutoff = maturity["cutoff_date"]
    if maturity_cutoff is not None and not _sample_v2_maturity_cutoff_grounded(
        utterance,
        maturity_cutoff,
    ):
        missing.append("maturity.cutoff_date")
    maturity_reason = maturity["reason"]
    if maturity_reason is not None and not _sample_v2_maturity_reason_grounded(
        utterance,
        maturity_reason,
    ):
        missing.append("maturity.reason")
    if not _sample_design_target_bad_value_grounded(
        utterance,
        inputs["target_bad_value"],
    ):
        missing.append("target_bad_value")
    if not _sample_v2_drop_policy_grounded(utterance, inputs["drop_nan_labels"]):
        missing.append("drop_nan_labels")
    if not _sample_v2_relationship_grounded(
        utterance,
        inputs["relationship"],
    ):
        missing.append("relationship")

    for role, labels in (
        ("approval_population", ("Overall approval", "Sample approval", "approval population")),
        ("risk_population", ("Overall risk", "Risk sample", "risk population")),
    ):
        population = inputs[role]
        if population["inclusion"] is None and population["exclusion"] is None:
            if not _sample_v2_no_population_filters_grounded(utterance, labels):
                missing.append(role)
        else:
            for field in ("inclusion", "exclusion"):
                predicate = population[field]
                if predicate is not None and not _sample_v2_predicate_grounded(
                    utterance,
                    predicate,
                    role_labels=labels,
                    direction=field,
                ):
                    missing.append(f"{role}.{field}")

    partitioning = inputs["partitioning"]
    partition_labels = (
        ("development", ("Development", "development")),
        ("validation", ("Authentication", "validation")),
        ("oot", ("OOT", "Out of time.")),
    )
    if partitioning["method"] == "time_ranges":
        if not _sample_design_column_role_grounded(
            utterance,
            column=partitioning["column"],
            labels=(
                "Time-Cut-down",
                "Time unscramble",
                "Time field",
                "time partition column",
            ),
        ):
            missing.append("partitioning.column")
        for partition, labels in partition_labels:
            bounds = partitioning["ranges"][partition]
            if not _sample_v2_partition_time_range_grounded(
                utterance,
                start=bounds["start"],
                end=bounds["end"],
                labels=labels,
            ):
                missing.append(f"partitioning.ranges.{partition}")
    else:
        selectors = partitioning["selectors"]
        simple: dict[str, tuple[str, object]] = {}
        for partition, _labels in partition_labels:
            try:
                simple[partition] = _simple_partition_equality(
                    selectors[partition],
                    name=f"partitioning.selectors.{partition}",
                )
            except _DraftValidationError:
                simple = {}
                break
        simple_columns = {column for column, _value in simple.values()}
        if len(simple) == 3 and len(simple_columns) == 1:
            split_column = next(iter(simple_columns))
            for partition, labels in partition_labels:
                _column, value = simple[partition]
                if not _sample_v2_partition_equality_grounded(
                    utterance,
                    values=[value],
                    labels=labels,
                ):
                    missing.append(f"partitioning.selectors.{partition}")
            if not _sample_design_column_role_grounded(
                utterance,
                column=split_column,
                labels=("Cut", "Dismantling", "split column", "split_col"),
            ):
                missing.append("partitioning.column")
        else:
            for partition, labels in partition_labels:
                if not _sample_v2_partition_predicate_grounded(
                    utterance,
                    selectors[partition],
                    labels=labels,
                ):
                    missing.append(f"partitioning.selectors.{partition}")

    binding_labels = {
        "entity_field": ("Entity Fields", "Main field", "Client Fields", "entity field"),
        "time_field": ("Time field", "Date Field", "time field"),
        "group_field": ("Group Fields", "Group Fields", "group field"),
        "month_field": ("Month field", "Month field", "month field"),
        "weight_field": ("Weight Fields", "weight field"),
        "loan_amount_field": ("Amount of the loan field", "Loan Amount Fields", "loan amount field"),
        "overdue_amount_field": ("Overdue amount fields", "overdue amount field"),
    }
    for field, labels in binding_labels.items():
        value = inputs["field_bindings"][field]
        if value is None:
            if not _sample_v2_unavailable_role_grounded(utterance, labels):
                missing.append(f"field_bindings.{field}")
        elif not _sample_design_column_role_grounded(
            utterance,
            column=value,
            labels=labels,
        ):
            missing.append(f"field_bindings.{field}")
        for candidate in whitelist:
            if _sample_design_column_role_grounded(
                utterance,
                column=candidate,
                labels=labels,
            ) and value != candidate:
                missing.append(f"field_bindings.{field}={candidate}")

    historical = inputs["historical_score"]
    if not _sample_v2_historical_score_grounded(
        utterance,
        historical,
        whitelist=whitelist,
    ):
        missing.append("historical_score")
    if missing:
        fields = tuple(dict.fromkeys(missing))
        return _clarification(
            "V2 The sample design draft has control items that cannot be checked word for word:"
            + ",".join(fields)
            + ".The platform does not speculate, write or quietly downgrade.",
            code="strategy_sample_design_v2_controls_not_grounded",
            fields=fields,
        )
    return result

def _sample_design_v2_has_chained_operation(utterance: str) -> bool:
    return _has_positive_chained_operation(
        utterance,
        operation_re=_SAMPLE_DESIGN_V2_CHAIN_RE,
    )

def _sample_v2_value_grounded(utterance: str, value: object) -> bool:
    if isinstance(value, str):
        return _utterance_contains_token(utterance, value) or value in utterance
    return re.search(rf"(?<![0-9.]){re.escape(str(value))}(?![0-9.])", utterance) is not None

def _sample_v2_drop_policy_grounded(utterance: str, expected: bool) -> bool:
    true_match = re.search(
        r"(?:Drop|Exclude|Remove|Delete).{0,12}(?:NaN|nan|Empty Tab|Missing tab)|"
        r"(?:NaN|nan|Empty Tab|Missing tab).{0,12}(?:Drop|Exclude|Remove|Delete)|"
        r"(?:drop|exclude).{0,12}(?:nan|missing)\s+labels?",
        utterance,
        re.I,
    )
    false_match = re.search(
        r"(?:Do Not Abandon|Not ruled out.|Reservations).{0,12}(?:NaN|nan|Empty Tab|Missing tab)|"
        r"(?:do\s+not|don't)\s+(?:drop|exclude).{0,12}(?:nan|missing)\s+labels?",
        utterance,
        re.I,
    )
    return false_match is not None if expected is False else true_match is not None and false_match is None

def _sample_v2_relationship_grounded(
    utterance: str,
    relationship: object,
) -> bool:
    """Require the user to state the two-population relationship explicitly."""

    if relationship not in {"nested_same_cohort", "parallel_time_cohorts"}:
        return False
    observed: set[str] = set()
    for clause in _sample_design_clauses(utterance):
        has_both_roles = (
            re.search(r"(?:Overall approval|Sample approval|approval\s+population)", clause, re.I)
            is not None
            and re.search(r"(?:Overall risk|Risk sample|risk\s+population)", clause, re.I)
            is not None
        )
        if not has_both_roles:
            continue
        if re.search(
            r"(?:nested[_\s-]*same[_\s-]*cohort|"
            r"(?:Same amount|Same.|Same).{0,8}(?:cohort|Queue|Sample).{0,16}"
            r"(?:Embedded|Organisation|Subset)|"
            r"(?:Embedded|Organisation|Subset).{0,16}(?:Same amount|Same.|Same).{0,8}"
            r"(?:cohort|Queue|Sample))",
            clause,
            re.I,
        ):
            observed.add("nested_same_cohort")
        if re.search(
            r"(?:parallel[_\s-]*time[_\s-]*cohorts?|"
            r"(?:Parallel|Parallel|Independence).{0,10}(?:Time|Time|Month).{0,8}"
            r"(?:cohort|Queue|Sample)|"
            r"(?:Time|Time|Month).{0,8}(?:cohort|Queue|Sample).{0,10}"
            r"(?:Parallel|Parallel|Independence))",
            clause,
            re.I,
        ):
            observed.add("parallel_time_cohorts")
    return observed == {relationship}

def _sample_v2_no_population_filters_grounded(
    utterance: str,
    labels: Sequence[str],
) -> bool:
    expected_role = re.compile(
        "|".join(
            re.escape(label)
            for label in sorted(labels, key=len, reverse=True)
        ),
        re.I,
    )
    no_filter = re.compile(
        r"(?:(?:Average|Both)?(?:Yes|Yes.)?Full Table)|"
        r"(?:None|No, I'm not.|Do Not Set|Do Not Set|Do Not Use|Do not do it.|No need.)\s*(?:Any)?\s*"
        r"(?:(?:Nacho.|Inclusion\s*(?:and|and|or|/)?\s*Exclude|Filter|Filter)(?:Conditions)?|"
        r"inclusion\s*(?:or|and|and|/|or|and)\s*exclusion\s*(?:Filter|Filter)?|"
        r"(?:Extra|Attach)?Conditions)|"
        r"(?:(?:no|without)\s+(?:population\s+)?filters?|"
        r"inclusion\s*(?:=|:)?\s*(?:none|null)\s*(?:and|,|,|,|/)\s*"
        r"exclusion\s*(?:=|:)?\s*(?:none|null))",
        re.I,
    )
    positive_filter = re.compile(
        r"(?:Inclusion|Organisation|Reservations|Exclude|Remove|Not included|inclusion|include|"
        r"exclusion|exclude).{0,40}"
        r"(?:Not equal to|Equal|No, I'm not.|greater than or equal to|less than or equal to|Greater than|less than|"
        r"!=|<>|>=|<=|(?<![<>!=])=(?!=)|\b(?:eq|ne|gt|gte|lt|lte)\b)",
        re.I,
    )
    combined_population_clause = any(
        expected_role.search(clause) is not None
        and len(tuple(_SAMPLE_V2_POPULATION_ROLE_RE.finditer(clause))) >= 2
        and no_filter.search(clause) is not None
        and positive_filter.search(clause) is None
        for clause in _sample_design_control_segments(utterance)
    )
    if combined_population_clause:
        return True
    return any(
        no_filter.search(segment) is not None
        and positive_filter.search(segment) is None
        for segment in _sample_v2_role_owned_segments(utterance, labels)
    )

def _sample_v2_predicate_grounded(
    utterance: str,
    predicate: object,
    *,
    role_labels: Sequence[str],
    direction: str,
) -> bool:
    if direction not in {"inclusion", "exclusion"}:
        return False
    for role_segment in _sample_v2_role_owned_segments(utterance, role_labels):
        markers = tuple(_SAMPLE_V2_POPULATION_DIRECTION_RE.finditer(role_segment))
        for index, marker in enumerate(markers):
            if marker.lastgroup != direction:
                continue
            end = (
                markers[index + 1].start()
                if index + 1 < len(markers)
                else len(role_segment)
            )
            local = role_segment[marker.start() : end]
            if _sample_v2_predicate_semantics_grounded(local, predicate):
                return True
    return False

def _sample_v2_role_owned_segments(
    utterance: str,
    labels: Sequence[str],
) -> tuple[str, ...]:
    expected = re.compile(
        "|".join(
            re.escape(label)
            for label in sorted(labels, key=len, reverse=True)
        ),
        re.I,
    )
    segments: list[str] = []
    for clause in _sample_design_clauses(utterance):
        roles = tuple(_SAMPLE_V2_POPULATION_ROLE_RE.finditer(clause))
        for index, role in enumerate(roles):
            if expected.search(role.group(0)) is None:
                continue
            start = 0 if index == 0 else role.start()
            end = roles[index + 1].start() if index + 1 < len(roles) else len(clause)
            segments.append(clause[start:end].strip())
    return tuple(segments)

def _sample_v2_predicate_semantics_grounded(
    text: str,
    predicate: object,
) -> bool:
    if not is_sample_design_v2_fresh_partition_selector(predicate):
        return False
    assert isinstance(predicate, Mapping)
    op = predicate.get("op")
    if op not in {"and", "or"}:
        leaf_pattern = _sample_v2_predicate_leaf_grounding_pattern(predicate)
        return leaf_pattern is not None and re.search(
            leaf_pattern,
            text,
            re.I,
        ) is not None
    if op in {"and", "or"}:
        args = predicate.get("args")
        assert isinstance(args, Sequence)
        patterns = [
            _sample_v2_predicate_leaf_grounding_pattern(item)
            for item in args
        ]
        if any(pattern is None for pattern in patterns):
            return False
        connector = (
            r"(?:and|And...|Meanwhile...|(?<![A-Za-z0-9_])and(?![A-Za-z0-9_]))"
            if op == "and"
            else r"(?:or|Or...|(?<![A-Za-z0-9_])or(?![A-Za-z0-9_]))"
        )
        opposite = (
            r"(?:or|Or...|(?<![A-Za-z0-9_])or(?![A-Za-z0-9_]))"
            if op == "and"
            else r"(?:and|And...|Meanwhile...|(?<![A-Za-z0-9_])and(?![A-Za-z0-9_]))"
        )
        joined = patterns[0] + "".join(
            rf"\s*(?:,|,)?\s*(?:{connector})\s*{pattern}"
            for pattern in patterns[1:]
        )
        match = re.search(joined, text, re.I)
        return match is not None and re.search(
            opposite,
            match.group(0),
            re.I,
        ) is None
    return False

def _sample_v2_predicate_leaf_grounding_pattern(
    predicate: object,
) -> str | None:
    if not isinstance(predicate, Mapping):
        return None
    op = predicate.get("op")
    if op in {"eq", "ne", "gt", "gte", "lt", "lte"}:
        left = _sample_v2_operand_pattern(predicate.get("left"))
        right = _sample_v2_operand_pattern(predicate.get("right"))
        operator = _sample_v2_operator_pattern(str(op))
        if left is None or right is None or operator is None:
            return None
        return rf"{left}.{{0,24}}?(?:{operator}).{{0,24}}?{right}"
    if op not in {"is_null", "is_not_null"}:
        return None
    arg = _sample_v2_operand_pattern(predicate.get("arg"))
    if arg is None:
        return None
    null_operator = (
        r"(?:(?<!No, no.)Empty|(?<!No, no.)is empty|is\s+null)"
        if op == "is_null"
        else r"(?:Not Empty|Not empty|Non-empty|is\s+not\s+null)"
    )
    return (
        rf"(?:{arg}.{{0,16}}?(?:{null_operator})|"
        rf"(?:{null_operator}).{{0,16}}?{arg})"
    )

def _sample_v2_operand_pattern(value: object) -> str | None:
    if not isinstance(value, Mapping):
        return None
    if set(value) == {"column"}:
        return _sample_v2_token_pattern(value["column"])
    if set(value) == {"literal"}:
        return _sample_v2_token_pattern(value["literal"])
    return None

def _sample_v2_token_pattern(value: object) -> str:
    text = _sample_design_scalar_text(value)
    escaped = re.escape(text)
    if re.fullmatch(r"[A-Za-z0-9_.-]+", text):
        return rf"(?<![A-Za-z0-9_.-]){escaped}(?![A-Za-z0-9_.-])"
    return escaped

def _sample_v2_operator_pattern(operator: str) -> str | None:
    return {
        "eq": (
            r"(?:(?<!No, no.)(?<!Greater than)(?<!less than)Equal|(?<!No, no.)Yes|(?<!No, no.)Yes.|"
            r"(?<![<>!=])=(?!=)|(?<![A-Za-z0-9_])"
            r"(?:eq|equals?|equal\s+to)(?![A-Za-z0-9_]))"
        ),
        "ne": (
            r"(?:Not equal to|No, I'm not.|No, it's not.|!=|<>|(?<![A-Za-z0-9_])"
            r"(?:ne|not\s+equal(?:\s+to)?)(?![A-Za-z0-9_]))"
        ),
        "gt": (
            r"(?:Greater than(?!Equal)|Higher|>(?!=)|(?<![A-Za-z0-9_])"
            r"(?:gt|greater\s+than)(?![A-Za-z0-9_]))"
        ),
        "gte": (
            r"(?:greater than or equal to|Not less than|At least.|>=|(?<![A-Za-z0-9_])"
            r"(?:gte|greater\s+than\s+or\s+equal(?:\s+to)?|at\s+least)"
            r"(?![A-Za-z0-9_]))"
        ),
        "lt": (
            r"(?:less than(?!Equal)|Less than|<(?!=)|(?<![A-Za-z0-9_])"
            r"(?:lt|less\s+than)(?![A-Za-z0-9_]))"
        ),
        "lte": (
            r"(?:less than or equal to|Not greater than|Up to|<=|(?<![A-Za-z0-9_])"
            r"(?:lte|less\s+than\s+or\s+equal(?:\s+to)?|at\s+most)"
            r"(?![A-Za-z0-9_]))"
        ),
    }.get(operator)

def _sample_v2_maturity_days_grounded(
    utterance: str,
    days: object,
) -> bool:
    if isinstance(days, bool) or not isinstance(days, int):
        return False
    contexts = tuple(
        clause
        for clause in _sample_design_clauses(utterance)
        if re.search(
            r"(?:Grown up.(?:degrees)?(?:Performance)?Window|Maturity|"
            r"maturity.{0,12}performance\s+window)",
            clause,
            re.I,
        )
        or (
            re.search(r"(?:Mature|maturity)", clause, re.I)
            and re.search(r"(?:Performance period|performance\s+window)", clause, re.I)
        )
    )
    observed = {
        int(value)
        for clause in contexts
        for value in re.findall(r"(?<!\d)(\d{1,6})\s*(?:Oh, my God.|days?)(?!\w)", clause, re.I)
    }
    return observed == {days}

def _sample_v2_maturity_cutoff_grounded(
    utterance: str,
    cutoff: object,
) -> bool:
    if not isinstance(cutoff, str):
        return False
    date_pattern = r"\d{4}-\d{2}-\d{2}"
    maturity_label = r"(?:Grown up.(?:degrees)?|maturity)"
    cutoff_label = r"(?:Quantity|Deadline|cutoff(?:\s+date)?)"
    contexts = tuple(
        clause
        for clause in _sample_design_clauses(utterance)
        if re.search(
            rf"{maturity_label}.{{0,16}}{cutoff_label}|"
            rf"{cutoff_label}.{{0,16}}{maturity_label}",
            clause,
            re.I,
        )
    )
    dates = {
        value
        for clause in contexts
        for value in re.findall(date_pattern, clause)
    }
    return dates == {cutoff}

def _sample_v2_maturity_reason_grounded(
    utterance: str,
    reason: object,
) -> bool:
    if not isinstance(reason, str) or not reason:
        return False
    return any(
        re.search(r"(?:Grown up.(?:degrees)?(?:Reason|Rationale)|maturity\s+reason)", clause, re.I)
        is not None
        and _sample_v2_value_grounded(clause, reason)
        for clause in _sample_design_clauses(utterance)
    )

def _sample_v2_partition_equality_grounded(
    utterance: str,
    *,
    values: Sequence[object],
    labels: Sequence[str],
) -> bool:
    label_pattern = "|".join(
        re.escape(label) for label in sorted(labels, key=len, reverse=True)
    )
    matches = [
        match
        for clause in _sample_design_clauses(utterance)
        if (match := re.search(rf"(?:{label_pattern})", clause, re.I))
    ]
    if len(matches) != 1:
        return False
    clause_match = matches[0]
    clause = clause_match.string
    remainder = clause[clause_match.end() :]
    if re.match(
        r"^\s*(?:Sample)?\s*(?:Remove?Value|values?)\s*"
        r"(?:Not equal to|No, I'm not.|No, it's not.|!=|<>|Greater than|less than|Higher|Less than|>=|<=|>|<)",
        remainder,
        re.I,
    ):
        return False
    if re.match(
        r"^\s*(?:Sample)?\s*(?:(?:Remove?Value|values?)\s*(?:Yes|Yes.|Equal|=)?|"
        r"(?:Yes|Yes.|Equal|=))",
        remainder,
        re.I,
    ) is None:
        return False
    return _sample_design_split_values_grounded(
        utterance,
        values=values,
        labels=labels,
    )

def _sample_v2_partition_predicate_grounded(
    utterance: str,
    predicate: object,
    *,
    labels: Sequence[str],
) -> bool:
    role = "|".join(
        re.escape(label) for label in sorted(labels, key=len, reverse=True)
    )
    clauses = tuple(
        clause
        for clause in _sample_design_clauses(utterance)
        if re.search(
            rf"(?:{role}).{{0,10}}(?:Conditions|The word.|selector|predicate)",
            clause,
            re.I,
        )
    )
    return (
        len(clauses) == 1
        and _sample_v2_predicate_semantics_grounded(clauses[0], predicate)
    )

def _sample_v2_partition_time_range_grounded(
    utterance: str,
    *,
    start: object,
    end: object,
    labels: Sequence[str],
) -> bool:
    role = "|".join(
        re.escape(label) for label in sorted(labels, key=len, reverse=True)
    )
    clauses = tuple(
        segment
        for segment in _sample_design_control_segments(utterance)
        if re.search(rf"(?:{role})", segment, re.I)
    )
    if len(clauses) != 1:
        return False
    clause = clauses[0]
    date_pattern = r"\d{4}-\d{2}-\d{2}"
    expected = {
        value for value in (start, end) if isinstance(value, str)
    }
    observed = set(re.findall(date_pattern, clause))
    if expected != observed:
        return False
    if isinstance(start, str) and isinstance(end, str):
        return (
            re.search(
                rf"{re.escape(start)}\s*(?:to|Present.|~|—|–|to|through)\s*"
                rf"{re.escape(end)}",
                clause,
                re.I,
            )
            is not None
        )
    if start is None:
        return re.search(
            r"(?:Start|Start|start).{0,8}(?:None|Not yet.|Open|none|null)",
            clause,
            re.I,
        ) is not None
    return re.search(
        r"(?:End|Closing|end).{0,8}(?:None|Not yet.|Open|none|null)",
        clause,
        re.I,
    ) is not None

def _sample_v2_unavailable_role_grounded(
    utterance: str,
    labels: Sequence[str],
) -> bool:
    role = "(?:" + "|".join(re.escape(label) for label in labels) + ")"
    unavailable = r"(?:Not yet.|Not yet.|No, I'm not.|Not provided|Not available for the time being|Not available|Not Available|Not applicable|unavailable|not\s+available|none|null)"
    return (
        re.search(
            rf"{role}.{{0,12}}(?:{unavailable})|(?:{unavailable}).{{0,12}}{role}",
            utterance,
            re.I,
        )
        is not None
    )

def _sample_v2_historical_score_grounded(
    utterance: str,
    historical: Mapping[str, Any],
    *,
    whitelist: Sequence[str],
) -> bool:
    subject = r"(?:History|History Rating|History model fractions|historical\s+score)"
    status = historical["status"]
    if status == "available":
        column = historical["column"]
        direction = historical["direction"]
        owned_clauses = tuple(
            clause
            for clause in _sample_design_clauses(utterance)
            if re.search(subject, clause, re.I)
            and _sample_v2_value_grounded(clause, column)
        )
        if len(owned_clauses) != 1:
            return False
        clause = owned_clauses[0]
        if any(
            candidate != column
            and _sample_v2_value_grounded(clause, candidate)
            for candidate in whitelist
        ):
            return False
        direction_patterns = {
            "higher_is_riskier": (
                r"(?:The higher the risk.|The higher the risk, the higher the risk.|High-risk.|higher[_\s-]*is[_\s-]*riskier)"
            ),
            "lower_is_riskier": (
                r"(?:The lower the risk.|The lower the risk, the higher the risk.|Low-level, high-risk.|lower[_\s-]*is[_\s-]*riskier)"
            ),
        }
        observed = {
            candidate
            for candidate, pattern in direction_patterns.items()
            if re.search(pattern, clause, re.I)
        }
        return observed == {direction}
    status_pattern = (
        r"(?:Not yet.|Not yet.|No, I'm not.|Not provided|Not Available|unavailable)"
        if status == "unavailable"
        else r"(?:Not applicable|not[_\s-]*applicable)"
    )
    return any(
        re.search(
            rf"{subject}.{{0,16}}(?:{status_pattern})|"
            rf"(?:{status_pattern}).{{0,16}}{subject}",
            clause,
            re.I,
        )
        and _sample_v2_value_grounded(clause, historical["reason"])
        for clause in _sample_design_clauses(utterance)
    )

def _sample_design_clauses(utterance: str) -> tuple[str, ...]:
    return tuple(
        clause.strip()
        for clause in re.split(r"[;;..!??\n]+", utterance)
        if clause.strip()
    )

def _sample_design_control_segments(utterance: str) -> tuple[str, ...]:
    """Split scalar controls without borrowing labels or values from neighbors."""

    return tuple(
        segment.strip()
        for segment in re.split(r"[;;..!??\n,,,]+", utterance)
        if segment.strip()
    )

def _sample_design_performance_grounded(
    utterance: str,
    *,
    status: str,
    days: object,
) -> bool:
    labels = re.compile(r"Performance(?:Window|Period)|performance\s+window", re.I)
    maturity_labels = re.compile(
        r"Grown up.(?:degrees)?(?:Performance)?(?:Window|Period)|"
        r"maturity.{0,12}performance\s+window",
        re.I,
    )
    clauses = tuple(
        clause
        for clause in _sample_design_clauses(utterance)
        if labels.search(clause) and maturity_labels.search(clause) is None
    )
    if not clauses:
        return False
    unavailable = any(
        re.search(
            r"(?:Not yet.|Not yet.|No, I'm not.|Not provided|Not Available|I don't know.|Unknown|"
            r"unavailable|not\s+available|unknown)",
            clause,
            re.I,
        )
        for clause in clauses
    )
    explicit_days = {
        int(match.group(1))
        for clause in clauses
        for match in re.finditer(r"(?<!\d)(\d{1,6})\s*(?:Oh, my God.|days?)(?!\w)", clause, re.I)
    }
    negated_days = any(
        re.search(
            r"(?:No, it's not.|Not really.|No, I'm not.|not)\s*\d{1,6}\s*(?:Oh, my God.|days?)",
            clause,
            re.I,
        )
        for clause in clauses
    )
    if status == "unavailable":
        return unavailable and not explicit_days and not negated_days
    return (
        isinstance(days, int)
        and not isinstance(days, bool)
        and not unavailable
        and not negated_days
        and explicit_days == {days}
    )

def _sample_design_observation_grounded(
    utterance: str,
    *,
    status: str,
    start: object,
    end: object,
) -> bool:
    label = r"(?:Observation(?:Window|Period)|observation\s+window)"
    clauses = tuple(
        clause
        for clause in _sample_design_clauses(utterance)
        if re.search(label, clause, re.I)
    )
    if not clauses:
        return False
    unavailable = any(
        re.search(
            r"(?:Not yet.|Not yet.|No, I'm not.|Not provided|Not Available|I don't know.|Unknown|"
            r"unavailable|not\s+available|unknown)",
            clause,
            re.I,
        )
        for clause in clauses
    )
    date_pattern = r"\d{4}-\d{2}-\d{2}"
    dates = {
        token
        for clause in clauses
        for token in re.findall(date_pattern, clause)
    }
    if status == "unavailable":
        return unavailable and not dates
    if not isinstance(start, str) or not isinstance(end, str) or unavailable:
        return False

    pairs: set[tuple[str, str]] = set()
    for clause in clauses:
        range_patterns = (
            rf"{label}.{{0,32}}?({date_pattern})\s*(?:to|Present.|~|—|–|to|through)\s*({date_pattern})",
            rf"({date_pattern})\s*(?:to|Present.|~|—|–|to|through)\s*({date_pattern}).{{0,20}}?{label}",
        )
        for pattern in range_patterns:
            pairs.update(re.findall(pattern, clause, re.I))
        starts = re.findall(
            rf"(?:Start|Start|start)\s*(?:Yes|Yes.|=|:|:)?\s*({date_pattern})",
            clause,
            re.I,
        )
        ends = re.findall(
            rf"(?:End|Closing|end)\s*(?:Yes|Yes.|=|:|:)?\s*({date_pattern})",
            clause,
            re.I,
        )
        if len(starts) == 1 and len(ends) == 1:
            pairs.add((starts[0], ends[0]))
    return pairs == {(start, end)} and dates == {start, end}

def _sample_design_maturity_grounded(utterance: str, status: str) -> bool:
    if re.search(
        r"(?:Mature|maturity).{0,16}(?:Not|No, no.)(?:Yes.)?Confirm.(?:Already|Already)?Grown up.|"
        r"(?:Not|No, no.)(?:Yes.)?Confirm.(?:Already|Already)?Grown up.|"
        r"(?:No, it's not.|Not really.)(?:Already|Already)?Grown up.|not\s+confirmed\s+matured",
        utterance,
        re.I,
    ):
        return False
    observed = {
        candidate
        for candidate, pattern in _SAMPLE_DESIGN_MATURITY_PATTERNS.items()
        if pattern.search(utterance) is not None
    }
    return observed == {status}

def _sample_design_target_bad_value_grounded(
    utterance: str,
    target_bad_value: int,
) -> bool:
    bad_values = _sample_design_binary_role_values(
        utterance,
        label=r"(?:Bad(?:Sample|Client|Label|Category)?|Bad debts.|bad(?:\s+(?:sample|label|class))?)",
    )
    bad_values.update(
        int(value)
        for value in re.findall(
            r"(?<![A-Za-z0-9_])target_bad_value\s*(?:=|:|:)\s*([01])(?!\d)",
            utterance,
            re.I,
        )
    )
    good_values = _sample_design_binary_role_values(
        utterance,
        label=r"(?:Okay.(?:Sample|Client|Label|Category)?|Normal Sample|good(?:\s+(?:sample|label|class))?)",
    )
    return bad_values == {target_bad_value} and (
        not good_values or good_values == {1 - target_bad_value}
    )

def _sample_design_binary_role_values(
    utterance: str,
    *,
    label: str,
) -> set[int]:
    values: set[int] = set()
    patterns = (
        rf"(?<!\d)([01])(?!\d)\s*(?:Yeah.\s*)?(?:Yes.|Yes|Representative|Organisation|Mark as|Encoding As)\s*{label}",
        rf"{label}\s*(?:Value|Tab Value|Encoding)?\s*(?:Yes.|Yes|=|:|:)\s*([01])(?!\d)",
    )
    for pattern in patterns:
        values.update(int(value) for value in re.findall(pattern, utterance, re.I))
    return values

def _sample_design_column_role_grounded(
    utterance: str,
    *,
    column: str,
    labels: Sequence[str],
) -> bool:
    column_pattern = re.escape(column)
    label_pattern = "|".join(re.escape(label) for label in labels)
    for match in re.finditer(
        rf"(?<![A-Za-z0-9_]){column_pattern}(?![A-Za-z0-9_])",
        utterance,
        re.I,
    ):
        separators = (";", ";", ".", "\n", ",", ",", ",")
        left = max(
            utterance.rfind(separator, 0, match.start())
            for separator in separators
        ) + 1
        right_candidates = [
            position
            for separator in separators
            if (position := utterance.find(separator, match.end())) >= 0
        ]
        right = min(right_candidates) if right_candidates else len(utterance)
        if re.search(label_pattern, utterance[left:right], re.I):
            return True
    return False

def _sample_design_split_values_grounded(
    utterance: str,
    *,
    values: Sequence[object],
    labels: Sequence[str],
) -> bool:
    label_pattern = "|".join(
        re.escape(label) for label in sorted(labels, key=len, reverse=True)
    )
    matches: list[tuple[str, re.Match[str]]] = []
    for clause in _sample_design_clauses(utterance):
        match = re.search(rf"(?:{label_pattern})", clause, re.I)
        if match is not None:
            matches.append((clause, match))
    if len(matches) != 1:
        return False
    clause, role_match = matches[0]
    remainder = clause[role_match.end() :]
    remainder = re.sub(
        r"^\s*(?:Sample)?\s*(?:Remove?Value|values?)?\s*(?:Yes|Yes.|=|:|:)?\s*",
        "",
        remainder,
        flags=re.I,
    ).strip()
    if not values:
        return bool(
            re.search(
                r"(?:Not yet.|No, I'm not.|Not provided|Not Available|Empty|Empty array|unavailable|none|empty)",
                remainder,
                re.I,
            )
        )
    if re.search(
        r"(?:Not yet.|No, I'm not.|Not provided|Not Available|Empty|Empty array|unavailable|none|empty)",
        remainder,
        re.I,
    ):
        return False
    raw_tokens = re.split(r"\s*(?:,|,|,|and|and|and)\s*", remainder)
    tokens = {
        token.strip().strip("[]()(){}\"'` ").casefold()
        for token in raw_tokens
        if token.strip().strip("[]()(){}\"'` ")
    }
    expected = {
        _sample_design_scalar_text(value).casefold()
        for value in values
    }
    return tokens == expected

def _sample_design_scalar_text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
