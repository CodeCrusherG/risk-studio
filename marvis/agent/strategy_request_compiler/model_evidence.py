"""model_evidence request-compiler handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import StandardWorkflowRequestDraft
    from . import StrategyRequestCompilation
    from . import _clarification
    from . import _sample_design_clauses

_MODEL_EVIDENCE_SUBJECT_RE = re.compile(
    r"(?:Model\s*Evidence|Model evidence|Single Variable(?:Candidates)?Evidence(?:Package|Summary)?|"
    r"Authentication Single Variables(?:Candidates)?(?:Evidence|Result))",
    re.IGNORECASE,
)

_MODEL_EVIDENCE_ACTION_RE = re.compile(
    r"(?:Summary|Reassembly|Physicalization|Solid|Generate|Create|Collapse|materialize|aggregate|collect|build|create)",
    re.IGNORECASE,
)

_MODEL_EVIDENCE_CHAIN_RE = re.compile(
    r"(?:Training(?:Model)?|Modelling|Model comparison|Comparative Model|Model comparison|Month by Month|Month|OOT|Out of time.|"
    r"Validation Model|Model validation|Generate Report|Form a report|Report.|Deployment|Production|Online.|Accepted)|"
    r"(?<![A-Za-z0-9_])(?:train(?:ing)?|model\s+comparison|compare\s+models?|"
    r"monthly|out[-_\s]*of[-_\s]*time|validation|report|deploy|production|adopt)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_MODEL_EVIDENCE_NONCOMMAND_RE = re.compile(
    r"[??]|(?:Can you...|Can I?|Is it possible?|Did you?|Yes|Is that okay?|Can you...|How's that?|What?|What?|Assumptions|Suppose...|If|"
    r"The future.|In the future|Later|Later.|Tomorrow.|Next week.|Next month)|"
    r"(?<![A-Za-z0-9_])(?:can\s+you|could\s+you|would\s+you|what\s+if|"
    r"how\s+to|in\s+the\s+future|later|tomorrow|next\s+(?:week|month))"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_MODEL_EVIDENCE_PLATFORM_CONTROL_RE = re.compile(
    r"\b(?:artifact_id|candidate_id|evidence_hash|content_hash|sample_design_ref|"
    r"membership_artifact_id|bundle_artifact_id|expected_[a-z0-9_]*(?:hash|id))\b|"
    r"(?:Work|Candidates|Evidence|Sample design|bundle|membership)\s*(?:ID|id|hash|Hash.|References)",
    re.IGNORECASE,
)

_MODEL_SCORE_COMPARISON_SUBJECT_RE = re.compile(
    r"(?:Model(?:Rating|Score)(?:Evidence)?(?:Comparison|Comparison)|"
    r"(?:Comparison|Comparison)(?:Current Task(?:Medium)?|Existing|Authenticated)?(?:It's...)?(?:Two.|Multiple|At least two.)?Model(?:Rating|Score)(?:Evidence)?|"
    r"model[-_\s]*score(?:\s+evidence)?\s+comparison|compare\s+(?:the\s+)?(?:model\s+)?scores?)",
    re.IGNORECASE,
)

_MODEL_SCORE_COMPARISON_ACTION_RE = re.compile(
    r"(?:Physicalization|Solid|Generate|Create|Build|Comparison|Comparison|materialize|build|create|compare)",
    re.IGNORECASE,
)

_MODEL_SCORE_COMPARISON_NONCOMMAND_RE = re.compile(
    r"[??]|(?:Can you...|Can I?|Is it possible?|Is that okay?|Can you...|How's that?|What?|What?|Assumptions|If|The future.|Later)|"
    r"(?<![A-Za-z0-9_])(?:can\s+you|could\s+you|would\s+you|what\s+if|how\s+to|later)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_MODEL_SCORE_COMPARISON_PLATFORM_CONTROL_RE = re.compile(
    r"\b(?:artifact(?:_id|_ids)?|dataset(?:_id|_ref)?|sample_design_ref|"
    r"model_score_evidence_refs?|evidence_artifact_id|score_vector_artifact_id|"
    r"expected_[a-z0-9_]+|registry_token|cas|content_hash|"
    r"selected_model_evidence_ref)\b|"
    r"(?:Work|Products|Dataset|Sample design|Rating evidence|Score vector)\s*(?:ID|id|hash|Hash.|References)|"
    r"(?:CAS|registry)\s*(?:token|token)",
    re.IGNORECASE,
)

_MODEL_SCORE_COMPARISON_SELECTION_RE = re.compile(
    r"(?:Selection|Selection|Recommendations|Sure.)(?:Champion.|Winner.|Best|Best)?|The champion model.|"
    r"(?:Accepted|Adopt|Deployment|Production|Online.)|"
    r"(?<![A-Za-z0-9_])(?:select|recommend|choose|pick|adopt|deploy|go[-\s]?live)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_MODEL_SCORE_COMPARISON_POPULATIONS = {
    "approval": re.compile(
        r"(?<![A-Za-z0-9_])approval(?![A-Za-z0-9_])|Overall approval|Total number of applications",
        re.IGNORECASE,
    ),
    "risk": re.compile(
        r"(?<![A-Za-z0-9_])risk(?![A-Za-z0-9_])|Overall risk",
        re.IGNORECASE,
    ),
}

_MODEL_SCORE_COMPARISON_PARTITIONS = {
    "overall": re.compile(
        r"(?<![A-Za-z0-9_])overall(?![A-Za-z0-9_])|Overall Division|Full Partition",
        re.IGNORECASE,
    ),
    "development": re.compile(
        r"(?<![A-Za-z0-9_])development(?![A-Za-z0-9_])|Development of the partitions|Development of samples",
        re.IGNORECASE,
    ),
    "validation": re.compile(
        r"(?<![A-Za-z0-9_])validation(?![A-Za-z0-9_])|Validation Partition|Validation of samples",
        re.IGNORECASE,
    ),
    "oot": re.compile(
        r"(?<![A-Za-z0-9_])oot(?![A-Za-z0-9_])|Partition outside time|Ex-time samples",
        re.IGNORECASE,
    ),
}

def utterance_targets_model_score_comparison_v2(utterance: str) -> bool:
    """Reserve explicit model-score comparison for its non-selecting Workflow."""

    return bool(
        _MODEL_SCORE_COMPARISON_SUBJECT_RE.search(utterance)
        and _MODEL_SCORE_COMPARISON_ACTION_RE.search(utterance)
    )

def _utterance_targets_strategy_model_evidence_v2(utterance: str) -> bool:
    historical_or_negated_action = re.compile(
        r"(?:Yesterday.|Before|Before|Go on.|Last time.|History|Tsang.|Once.|Already|Already|"
        r"Not|No, I'm not.|Did you?|Don't.|No, I'm fine.|No need.|Don't.|Ban|Cancel|Not yet.|Not yet.)\s*$|"
        r"(?<![A-Za-z0-9_])(?:yesterday|previously|earlier|already|"
        r"do\s+not|don't|never|cancel)\s*$",
        re.I,
    )
    for clause in _sample_design_clauses(utterance):
        subjects = tuple(_MODEL_EVIDENCE_SUBJECT_RE.finditer(clause))
        actions = tuple(_MODEL_EVIDENCE_ACTION_RE.finditer(clause))
        for action in actions:
            prefix = clause[max(0, action.start() - 24) : action.start()]
            if historical_or_negated_action.search(prefix):
                continue
            if any(
                (
                    action.end() <= subject.start()
                    and subject.start() - action.end() <= 48
                )
                or (
                    subject.end() <= action.start()
                    and action.start() - subject.end() <= 32
                )
                for subject in subjects
            ):
                return True
    return False

def _ground_model_score_comparison_v2_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    if _MODEL_SCORE_COMPARISON_PLATFORM_CONTROL_RE.search(utterance):
        return _clarification(
            "Model score comparisonSampleDesign,Rating evidence, fraction vector,artifact id/hash "
            "andregistry CAS All by Currenttask Automatically discovered and reviewed, not injected by natural language.",
            code="strategy_model_score_comparison_v2_platform_binding_forbidden",
            fields=("task_context",),
        )
    if (
        not utterance_targets_model_score_comparison_v2(utterance)
        or _MODEL_SCORE_COMPARISON_NONCOMMAND_RE.search(utterance)
    ):
        return _clarification(
            "Please clearly issue a current, positive model rating comparison of evidence materialization order.",
            code="strategy_model_score_comparison_v2_positive_command_required",
            fields=("build_intent",),
        )
    if _has_positive_chained_operation(
        utterance,
        operation_re=_MODEL_SCORE_COMPARISON_SELECTION_RE,
    ):
        return _clarification(
            "Ben.Workflow Only physical comparison of evidence and fixedno_selection;The winner's choice,"
            "Adoption and deployment must be a follow-up independent governance exercise.",
            code="strategy_model_score_comparison_v2_selection_forbidden",
            fields=("selection",),
        )
    inputs = draft.workflow_inputs
    populations = {
        value
        for value, pattern in _MODEL_SCORE_COMPARISON_POPULATIONS.items()
        if pattern.search(utterance)
    }
    partitions = {
        value
        for value, pattern in _MODEL_SCORE_COMPARISON_PARTITIONS.items()
        if pattern.search(utterance)
    }
    missing: list[str] = []
    if populations != {inputs["population"]}:
        missing.append("population")
    if partitions != {inputs["partition"]}:
        missing.append("partition")
    if missing:
        return _clarification(
            "Model scores must be made clear word for wordpopulation andpartition;"
            "The platform does not allow models to fill the default or to rewrite business slices.",
            code="strategy_model_score_comparison_v2_dimensions_not_grounded",
            fields=missing,
        )
    return result

def _ground_strategy_model_evidence_v2_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    if _model_evidence_v2_has_positive_chain(utterance):
        return _clarification(
            "CurrentModelEvidence V2 Only for the Currenttask Candidates for the existing authentication single variable;"
            "Training, model comparison, monthly/OOT/The validation model, reporting, adoption and deployment must be divided and awaiting corresponding authentication evidence.",
            code="strategy_model_evidence_v2_univariate_only",
            fields=("requested_evidence",),
        )
    if _MODEL_EVIDENCE_PLATFORM_CONTROL_RE.search(utterance):
        return _clarification(
            "ModelEvidence It's...SampleDesign,candidate andartifact id/hash All by Currenttask The government has not yet made any progress."
            "It cannot be injected into natural languages.",
            code="strategy_model_evidence_v2_platform_binding_forbidden",
            fields=("task_context",),
        )
    if (
        not _utterance_targets_strategy_model_evidence_v2(utterance)
        or _MODEL_EVIDENCE_NONCOMMAND_RE.search(utterance)
    ):
        return _clarification(
            "Please send a clear and current positive command, which will be submitted only to the existing authentication single variable.ModelEvidence V2.",
            code="strategy_model_evidence_v2_positive_command_required",
            fields=("build_intent",),
        )
    return result

def _has_positive_chained_operation(
    utterance: str,
    *,
    operation_re: re.Pattern[str],
) -> bool:
    """Return true only when a clause positively requests a chained operation."""

    boundaries = ";;..!??\n,,,/"
    for match in operation_re.finditer(utterance):
        left = max(utterance.rfind(mark, 0, match.start()) for mark in boundaries) + 1
        prefix = utterance[left : match.start()]
        if re.search(
            r"(?:No, I don't.|No, I'm fine.|Not yet.|Not yet.|Don't.|No need.|Not anymore.|Do not do it.|"
            r"Don't.|Ban|No, I won't.|Not|No, I'm not.|Not really.|Not|No, no.(?!Only|Only))"
            r"\s*(?:Again.|Conduct|Do it.|Generate|Form|Output|Enter|Start|Implementation|"
            r"Training|Build|Create|Create|Accepted|Adopt|Deployment|Production|Online.)?\s*$|"
            r"(?:(?:do\s+not\s+need\s+to|don't\s+need\s+to|"
            r"do\s+not|don't|never|without|no)\s+)"
            r"(?:(?:further\s+)?(?:do|generate|create|run)\s+)?$",
            prefix,
            re.I,
        ):
            continue
        return True
    return False

def _model_evidence_v2_has_positive_chain(utterance: str) -> bool:
    """Return true only for a positively requested downstream operation."""

    return _has_positive_chained_operation(
        utterance,
        operation_re=_MODEL_EVIDENCE_CHAIN_RE,
    )
