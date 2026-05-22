from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from marvis.agent.workflow_error_diagnostics import enrich_workflow_error_diagnostic
from marvis.llm_client import LLMClientError


_WORKFLOW_NAMES = {
    "data_join": "Data processing",
    "feature_analysis": "Characteristic analysis",
    "modeling": "Model development",
    "strategy": "Policy analysis",
    "vintage": "Vintage Risk analysis",
    "portfolio": "Group analysis",
}
_WORKFLOW_PROGRESS_INTENTS = frozenset(_WORKFLOW_NAMES)
_RECOVERY_DIAGNOSTIC_FIELDS = (
    "schema_version",
    "workflow",
    "code",
    "phase",
    "title",
    "summary",
    "cause",
    "location",
    "evidence",
    "actions",
    "agent_prompt",
    "recovery_actions",
    "retryable",
    "impact",
    "line_number",
    "expected_fields",
    "actual_fields",
    "auto_recoverable",
    "retry_instruction_sha256",
)
_LEGACY_CSV_FIELD_COUNT_RE = re.compile(
    r"Expected\s+(?P<expected>\d+)\s+fields?\s+in\s+line\s+"
    r"(?P<line>\d+),\s+saw\s+(?P<actual>\d+)",
    re.IGNORECASE,
)
_RETRY_NEGATION_RE = re.compile(
    r"(?:Not yet.|Don't do that again.?|Don't.|No, I'm fine.|No, I don't.|Not yet.|Pause|Cancel|Stop|"
    r"do\s+not|don't|dont|stop|cancel)",
    re.IGNORECASE,
)
_NEGATED_RETRY_ACTION_RE = re.compile(
    r"(?:Not yet.|Don't do that again.?|Don't.|No, I'm fine.|No, I don't.|Not yet.|Pause|Cancel|Stop|"
    r"do\s+not|don't|dont|stop|cancel)"
    r"\s*(?:(?:Now.|Immediately|Direct|Go on.|Again.)\s*)?"
    r"(?:Try again|Try again.|Restart(?:Read|Start|Implementation|Run|Start)|"
    r"Go on.(?:Current)?Failed(?:It's...)?[^,,,.;;!!??\n]{0,24}?Steps|"
    r"Reuse(?:Completed(?:It's...)?)?[^,,,.;;!!??\n]{0,32}?Checkpoints|"
    r"(?:From)?(?:Current)?Failed(?:It's...)?[^,,,.;;!!??\n]{0,24}Steps(?:Go on.)?|"
    r"retry|try\s+again|re-?run|restart|start)",
    re.IGNORECASE,
)
_RETRY_SCOPE_CONSTRAINT_RE = re.compile(
    r"(?:Not yet.|Don't do that again.?|Don't.|No, I'm fine.|No, I don't.|Not yet.|Pause|Cancel|Stop|"
    r"do\s+not|don't|dont|stop|cancel)\s*"
    r"(?:From the beginning.(?:Start)?(?:Implementation|Try again|Run)?|"
    r"(?:Restart)?(?:Implementation|Run|Start|Try again)\s*(?:The whole thing.|All|Complete)"
    r"(?:Process|Workstream|Tasks)|"
    r"(?:Restart)?(?:Implementation|Run|Try again)\s*(?:Already?|Already)?(?:Completed|Success)"
    r"(?:It's...)?(?:Steps|Part))",
    re.IGNORECASE,
)
_RETRY_PARAMETER_ADJUSTMENT_RE = re.compile(
    r"(?:Change(?:Done.|Yes)|Adjustment(?:Done.|Yes|Present.)|Set(?:Set)?(?:Done.|Yes)|"
    r"Replace|Change to|Modify to|Change|Replace|Adopt|(?<!No, no.)Use|"
    r"Algorithm\s*Use|Get rid of it.|Delete|Increase(?:Present.|to|Yes)|Reduction(?:Present.|to|Yes))",
    re.IGNORECASE,
)
_RETRY_TRAILING_CANCELLATION_RE = re.compile(
    r"(?:[,,,.;;!!\s]*(?:But...|But...|But...|And then...)?\s*"
    r"(?:No, I don't.|Forget it.|Cancel(?:Yeah.|Yes.)?|Pause(?:Yeah.|Yes.)?|Stop(?:Yeah.|Yes.)?|"
    r"Not yet.(?:Try again|Implementation|Run)?|I'll do it.))\s*[..!!\s]*$",
    re.IGNORECASE,
)
_RETRY_QUESTION_RE = re.compile(
    r"(?:Why?|Why?|What?|How's that?|Can you...|Is it possible?|Can I?|Can I?|Can you...|Is it possible?|"
    r"Do you want it?|What happens?|What?(?:Impact|Consequences)?|- You're not?\b|What?\b|[??])",
    re.IGNORECASE,
)
_RETRY_CLAUSE_SPLIT_RE = re.compile(
    r"[,,,.;;!!\n]+|"
    r"(?:and|And then...|Catch.)\s*(?=(?:From(?:Current)?Failed|Try again|Try again.|Restart|Start))"
)
_EXPLICIT_RETRY_RE = re.compile(
    r"^\s*(?:(?:Okay.?|Okay.|Yeah.|Agreed.|Confirm.)\s*)?"
    r"(?:(?:Please.|Trouble.|Now.|Direct|Immediately|Just...|and|And then...|Catch.)"
    r"(?:You.|agent)?(?:Help me.|Take my place.|For me.)?\s*)?"
    r"(?:(?:Please.)?(?:You.|agent)?(?:Help me.|Take my place.|For me.)\s*)?"
    r"(?:I'm...(?:Yes.|Yes.|Agreed.|Delegation of authority(?:You.)?)\s*)?"
    r"(?:"
    r"(?:Resolve|Processing|Rehabilitation|Restore)"
    r"[^,,,.;;!!??\n]{0,80}?(?:Try again|Restart(?:Implementation|Run|Start|Start))|"
    r"(?:From)?(?:Current)?Failed(?:It's...)?"
    r"[^,,,.;;!!??\n]{0,32}?Steps"
    r"(?:Go on.(?:Try again|Implementation|Run)?|Try again|Restart(?:Implementation|Run)|Implementation|Run)|"
    r"Reread(?:One second.|Materials|Documentation)?|"
    r"Go on.(?:Current)?Failed(?:It's...)?[^,,,.;;!!??\n]{0,24}?Steps|"
    r"Reuse(?:Completed(?:It's...)?)?[^,,,.;;!!??\n]{0,32}?Checkpoints|"
    r"Try again(?:One second.|Once.|Current(?:Failed)?(?:It's...)?[^,,,.;;!!??\n]{0,24}?(?:Steps|Actions)|"
    r"Failed(?:It's...)?[^,,,.;;!!??\n]{0,24}?(?:Steps|Actions)|"
    r"[^,,,.;;!!??\n]{0,16}?(?:Steps|Actions))?|"
    r"Try again.(?:One second.|Once.|Current steps|Step of failure)?|"
    r"Restart(?:Start|Implementation|Run|Start)"
    r"(?:One second.|Once.|Current)?(?:[^,,,.;;!!??\n]{0,24}?Steps|Workstream|Tasks|Analysis)?|"
    r"Start(?:Current)?(?:Data processing|Characteristic analysis|Model development|Policy analysis|Policy development|"
    r"vintage\s*Risk analysis|Risk analysis|Group analysis|Workstream|Tasks)?|"
    r"(?:please\s+)?(?:retry|try\s+again|re-?run|restart|start)"
    r")",
    re.IGNORECASE,
)
_RECOVERY_EXECUTION_CLAIM_RE = re.compile(
    r"(?:Already(?:The long run.)?(?:Copy that.|Start|Start|Start)|Copy that.[^.!?\n]{0,12}Delegation of authority|"
    r"In the process of|I'll...|From|Now.|Immediately|Please wait.)"
    r"[^.!?\n]{0,48}(?:Try again|Re-execution|Run again.|Run again.|Run again|Restoring implementation|Execute Current)|"
    r"(?:Next|And then...|After)?\s*(?:(?:I'm...|agent|Platform|System)\s*)?"
    r"(?:Yes, I will.|Yes.|Will|Ready.|I'm going to...)[^.!?\n]{0,48}"
    r"(?:Try again|Re-execution|Run again.|Run again.|Run again|Restoring implementation|Execute Current)|"
    r"(?:Already(?:The long run.)?Entering recovery process|"
    r"Restore(?:Operations|Tasks|Steps)?Already(?:The long run.)?Queue in.)|"
    r"(?:Automatic|Will|Yes.)(?:Increase|Increase|Adjustment|Modify|Optimization)"
    r"[^.!?\n]{0,24}(?:Memory|Resource constraints|Container limits|Allocation of resources|memory)",
    re.IGNORECASE,
)
_CONDITIONAL_RETRY_NOTICE_RE = re.compile(
    r"(?:If|If|Only|- Wait.|Wait|After a clear mandate|After confirmation)"
    r"[^.!?,,\n]{0,48}(?:That's right.|Square|Again.)?(?:Yes, I will.|Yes.|Will)?"
    r"[^.!?,,\n]{0,12}(?:Try again|Re-execution|Run again.|Run again.|Run again|Restoring implementation)",
    re.IGNORECASE,
)
_RECOVERY_REPLY_CLAUSE_SPLIT_RE = re.compile(r"[.!?!?;;,,\n]+")
_REPAIR_REQUEST_RE = re.compile(
    r"(?:Please.|Can you...|Yeah.|Can I?|Can you...|Is it possible?)?(?:You.|agent)?(?:Yeah.|Yes.)?"
    r"(?:Direct)?(?:Help me.|Take my place.|For me.)?(?:Resolve|Processing|Rehabilitation|Restore)"
    r"(?:This.|Current)?(?:Problem|Fault|Unusual)?(?:and)?(?:Try again|Re-execution|Go on.)?"
    r"(?:- You're not?|What?)?[..!!??\s]*$",
    re.IGNORECASE,
)
_FEATURE_SCREEN_ROLLBACK_RE = re.compile(
    r"(?:"
    r"(?:From|Back|Back to the...|Back to the...)\s*[()'\"`[][]]*"
    r"Feature Filter[()'\"`[][]]*\s*(?:Steps)?\s*"
    r"(?:Restart|Again.)(?:Implementation|Run|Start|Run!)|"
    r"(?:Restart|Again.)\s*(?:From)\s*[()'\"`[][]]*"
    r"Feature Filter[()'\"`[][]]*\s*(?:Steps)?\s*"
    r"(?:Implementation|Run|Start|Run!)"
    r")",
    re.IGNORECASE,
)
_FEATURE_EXCLUSION_RE = re.compile(
    r"(?:Please.\s*)?(?:Exclude|Remove|Get rid of it.|Delete)\s*(?P<features>.+)",
    re.IGNORECASE,
)
_NEGATED_FEATURE_REVISION_RE = re.compile(
    r"(?:Not yet.|Don't.|Don't.|No, I'm fine.|No, I don't.|Not yet.|Not yet.|Cancel|Stop|Pause)"
    r"[^\u3002!?!?\n]{0,32}?(?:Exclude|Remove|Get rid of it.|Delete|Feature Filter)",
    re.IGNORECASE,
)
_FEATURE_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_FEATURE_LIST_SPLIT_RE = re.compile(r"\s*(?:,|,|,|;|;|and|and|and)\s*")
_FEATURE_TOKEN_WRAPPERS = " \t\r\n`'()\"[][]()[]{}"
_TUNING_BUDGET_CONTEXT_RE = re.compile(
    r"(?:Transfer|Modified|Supersync|Pilot budget|Experimental budget|trial(?:s)?|n_trials)",
    re.IGNORECASE,
)
_TUNING_BUDGET_REVISION_ACTION_RE = re.compile(
    r"(?:Change(?:Done.|Yes)|Adjustment(?:Done.|Yes|Present.)|Set(?:Set)?(?:Done.|Yes)|"
    r"Reduction(?:Present.|to|Yes)|Only(?:Yes.|Yes|Yes.|Run!)|"
    r"No, I'm fine.[^.!?!?\n]{0,24}All these rounds.|"
    r"\d+\s*(?:Wheel|Number of times|trials?)(?:That's all.|Yeah.|Enough.))",
    re.IGNORECASE,
)
_TUNING_BUDGET_PAIR_RE = re.compile(
    r"(?P<recipe>light[\s_-]*gbm|lgb|xg[\s_-]*boost|xgb|cat[\s_-]*boost|cat)"
    r"\s*(?:It's...)?\s*(?:Transfer|Modified)?\s*(?:Budget|Rounds)?\s*"
    r"(?:=|:|:|Yes|For|Set as|Adjust to)\s*(?P<count>\d+)\s*(?:Wheel|Number of times|trials?)?",
    re.IGNORECASE,
)
_TUNING_BUDGET_UNKNOWN_PAIR_RE = re.compile(
    r"(?P<recipe>[A-Za-z][A-Za-z0-9_-]*)\s*"
    r"(?:=|:|:|Yes|For|Set as|Adjust to)\s*(?P<count>\d+)",
    re.IGNORECASE,
)
_TUNING_BUDGET_COUNT_RE = re.compile(
    r"(?P<count>\d+)\s*(?:Wheel|Number of times|trials?)",
    re.IGNORECASE,
)
_TUNING_BUDGET_DECIMAL_RE = re.compile(
    r"(?:[+-]?\d+\.\d+|[+-]\d+)\s*(?:Wheel|Number of times|trials?)",
    re.IGNORECASE,
)
_TUNING_CANCEL_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|Cancel|Stop|Pause)\s*(?:Again.)?(?:Do it.)?Transfer(?:Yes.)?\s*[..!!]*$",
    re.IGNORECASE,
)
_TUNING_RECIPE_ALIASES = {
    "lightgbm": "lgb",
    "lgb": "lgb",
    "xgboost": "xgb",
    "xgb": "xgb",
    "catboost": "catboost",
    "cat": "catboost",
}
_CHAMPION_REFIT_CONTEXT_RE = re.compile(
    r"(?:train\s*\+\s*test\s*(?:It's...)?(?:Full)?Retraining.|"
    r"(?:train\s*(?:and|and|\+)\s*test\s*)?Full training.|"
    r"Champion.(?:Model)?Retraining.|refit)",
    re.IGNORECASE,
)
_CHAMPION_REFIT_DISABLE_RE = re.compile(
    r"(?:Do not do it.|Don't.|No, I'm fine.|No, I don't.|Not implemented|Do Not|Skip|Cancel|Close|Disable)"
    r"[^.!?!?\n]{0,32}?"
    r"(?:train\s*\+\s*test|Full training.|Champion.(?:Model)?Retraining.|refit)",
    re.IGNORECASE,
)
_SELECTED_EXPERIMENT_ID_RE = re.compile(r"\bexperiment_[A-Za-z0-9]+\b")


@dataclass(frozen=True)
class WorkflowFailureContext:
    message_id: str | None
    diagnostic: dict
    failure_envelope: dict | None


@dataclass(frozen=True)
class WorkflowRollbackIntent:
    """A fail-closed request to revise a completed upstream workflow step."""

    action: str
    root_step: str
    excluded_features: tuple[str, ...]


@dataclass(frozen=True)
class TuningBudgetRevisionIntent:
    """A typed, non-executing request to revise a failed tuning budget."""

    default_n_trials: int | None
    n_trials_by_recipe: tuple[tuple[str, int], ...]
    execute: bool = False


@dataclass(frozen=True)
class ChampionRefitRevisionIntent:
    """A typed failed-selection retry that explicitly disables optional refit."""

    refit_on_train_plus_test: bool
    selected_experiment_id: str | None = None


def parse_tuning_budget_revision_intent(
    text: str | None,
) -> TuningBudgetRevisionIntent | None:
    """Parse an explicit bounded tuning-budget revision without authorizing tuning.

    This parser deliberately remains separate from plain failed-step retry.  It
    accepts either concrete per-recipe assignments or one unambiguous global
    trial count, rejects questions/cancellation/malformed numbers, and always
    leaves execution behind the refreshed configuration confirmation gate.
    """

    normalized = " ".join(str(text or "").strip().split())
    if not normalized or _TUNING_BUDGET_CONTEXT_RE.search(normalized) is None:
        return None
    if (
        _RETRY_QUESTION_RE.search(normalized)
        or _RETRY_TRAILING_CANCELLATION_RE.search(normalized)
        or _TUNING_CANCEL_RE.search(normalized)
        or _TUNING_BUDGET_DECIMAL_RE.search(normalized)
    ):
        return None

    explicit: dict[str, int] = {}
    spans: list[tuple[int, int]] = []
    for match in _TUNING_BUDGET_PAIR_RE.finditer(normalized):
        token = re.sub(r"[\s_-]+", "", match.group("recipe").lower())
        recipe = _TUNING_RECIPE_ALIASES.get(token)
        count = int(match.group("count"))
        if recipe is None or count < 1 or count > 200:
            return None
        previous = explicit.get(recipe)
        if previous is not None and previous != count:
            return None
        explicit[recipe] = count
        spans.append(match.span())

    # A named assignment that is not one of the supported tuning recipes must
    # never silently degrade into a global budget (for example ``foo=1``).
    for match in _TUNING_BUDGET_UNKNOWN_PAIR_RE.finditer(normalized):
        if any(start <= match.start() and match.end() <= end for start, end in spans):
            continue
        token = re.sub(r"[\s_-]+", "", match.group("recipe").lower())
        if token not in _TUNING_RECIPE_ALIASES:
            return None

    if explicit:
        return TuningBudgetRevisionIntent(
            default_n_trials=None,
            n_trials_by_recipe=tuple(explicit.items()),
        )

    if _TUNING_BUDGET_REVISION_ACTION_RE.search(normalized) is None:
        return None

    counts = {int(match.group("count")) for match in _TUNING_BUDGET_COUNT_RE.finditer(normalized)}
    if len(counts) != 1:
        return None
    count = counts.pop()
    if count < 1 or count > 200:
        return None
    return TuningBudgetRevisionIntent(
        default_n_trials=count,
        n_trials_by_recipe=(),
    )


def parse_champion_refit_revision_intent(
    text: str | None,
) -> ChampionRefitRevisionIntent | None:
    """Parse an explicit request to reuse a trained champion without final refit."""

    normalized = " ".join(str(text or "").strip().split())
    if (
        not normalized
        or _CHAMPION_REFIT_CONTEXT_RE.search(normalized) is None
        or _CHAMPION_REFIT_DISABLE_RE.search(normalized) is None
        or _RETRY_QUESTION_RE.search(normalized)
        or _RETRY_TRAILING_CANCELLATION_RE.search(normalized)
        or not is_explicit_workflow_retry(normalized)
    ):
        return None
    experiment_ids = list(dict.fromkeys(_SELECTED_EXPERIMENT_ID_RE.findall(normalized)))
    if len(experiment_ids) > 1:
        return None
    return ChampionRefitRevisionIntent(
        refit_on_train_plus_test=False,
        selected_experiment_id=experiment_ids[0] if experiment_ids else None,
    )


def parse_workflow_rollback_intent(text: str | None) -> WorkflowRollbackIntent | None:
    """Parse only an explicit feature-screen rollback with concrete columns.

    This is intentionally separate from :func:`is_explicit_workflow_retry`.
    A rollback changes the feature universe and invalidates every downstream
    output/decision, while a retry must preserve the failed step's inputs.  A
    question, cancellation, negated action, malformed identifier, or empty
    exclusion list therefore returns ``None`` and cannot mutate a plan.
    """

    normalized = " ".join(str(text or "").strip().split())
    if not normalized:
        return None
    if (
        _RETRY_QUESTION_RE.search(normalized)
        or _RETRY_TRAILING_CANCELLATION_RE.search(normalized)
        or _NEGATED_FEATURE_REVISION_RE.search(normalized)
    ):
        return None
    rollback_match = _FEATURE_SCREEN_ROLLBACK_RE.search(normalized)
    if rollback_match is None:
        return None
    # The exclusion clause must precede the requested rollback root.  This
    # prevents unrelated later prose from being interpreted as a feature list.
    prefix = normalized[: rollback_match.start()].rstrip(" ,,.;;::")
    exclusion_matches = list(_FEATURE_EXCLUSION_RE.finditer(prefix))
    if not exclusion_matches:
        return None
    raw_features = exclusion_matches[-1].group("features").strip()
    raw_features = re.sub(r"(?:♪ And the ♪)?Back\s*$", "", raw_features).rstrip(
        " ,,.;;::"
    )
    if not raw_features:
        return None

    features: list[str] = []
    for raw_token in _FEATURE_LIST_SPLIT_RE.split(raw_features):
        token = raw_token.strip(_FEATURE_TOKEN_WRAPPERS)
        if not token or _FEATURE_IDENTIFIER_RE.fullmatch(token) is None:
            return None
        if token not in features:
            features.append(token)
    if not features:
        return None
    return WorkflowRollbackIntent(
        action="revise_and_rerun",
        root_step="feature_screening",
        excluded_features=tuple(features),
    )


def latest_unresolved_workflow_failure(
    messages: list[dict],
    *,
    workflow: str,
) -> WorkflowFailureContext | None:
    """Return the latest failure that has not been superseded by progress.

    Recovery replies are deliberately transparent: they keep the same failure
    anchor so a user can ask several questions without accidentally rerunning
    setup. A new C1/gate/plan/setup message is a progress boundary and clears it.
    """

    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        metadata = message.get("metadata") or {}
        if metadata.get("intent") == "workflow_recovery_chat":
            continue

        diagnostic = metadata.get("error_diagnostic")
        envelope = metadata.get("failure_envelope")
        if isinstance(diagnostic, dict):
            return WorkflowFailureContext(
                message_id=_optional_text(message.get("id")),
                diagnostic=_safe_diagnostic(diagnostic, workflow=workflow),
                failure_envelope=dict(envelope) if isinstance(envelope, dict) else None,
            )
        if isinstance(envelope, dict):
            return WorkflowFailureContext(
                message_id=_optional_text(message.get("id")),
                diagnostic=_diagnostic_from_failure_envelope(workflow, envelope),
                failure_envelope=dict(envelope),
            )
        if metadata.get("error") is True:
            legacy = _legacy_csv_diagnostic(workflow, str(message.get("content") or ""))
            if legacy is not None:
                return WorkflowFailureContext(
                    message_id=_optional_text(message.get("id")),
                    diagnostic=legacy,
                    failure_envelope={"retryable": True},
                )
            return None
        if _is_workflow_progress_message(message, metadata):
            return None
    return None


def is_explicit_workflow_retry(text: str | None) -> bool:
    """Require an unambiguous command before executing a failed workflow again."""

    normalized = " ".join(str(text or "").strip().split()).lower()
    if not normalized:
        return False
    # Negation is scoped to the retry action.  Constraints such as
    # "Don't start from scratch.", "No sample weights." and "OOT Not to participate in the selection of merits" describe how
    # to resume; they are not a cancellation of the retry itself.
    without_scope_constraints = _RETRY_SCOPE_CONSTRAINT_RE.sub("", normalized)
    if (
        _NEGATED_RETRY_ACTION_RE.search(without_scope_constraints)
        or _RETRY_TRAILING_CANCELLATION_RE.search(normalized)
        or _RETRY_QUESTION_RE.search(normalized)
        or _RETRY_PARAMETER_ADJUSTMENT_RE.search(normalized)
    ):
        return False
    # Evaluate command clauses rather than requiring the entire message to be
    # a canned phrase.  This keeps the execution decision deterministic while
    # accepting a failed-step command embedded in a longer configuration note.
    return any(
        _EXPLICIT_RETRY_RE.fullmatch(clause.strip()) is not None
        for clause in _RETRY_CLAUSE_SPLIT_RE.split(normalized)
        if clause.strip()
    )


def is_explicit_cancelled_workflow_resume(text: str | None) -> bool:
    """Recognize a deliberate resume command after the user stopped a plan.

    A bare ``Go on.`` is intentionally accepted only in the cancelled-plan
    recovery context. Questions, parameter changes and negated commands remain
    non-executing conversation, matching failed-workflow recovery semantics.
    """

    normalized = " ".join(str(text or "").strip().split()).lower()
    if not normalized:
        return False
    without_scope_constraints = _RETRY_SCOPE_CONSTRAINT_RE.sub("", normalized)
    if (
        _NEGATED_RETRY_ACTION_RE.search(without_scope_constraints)
        or _RETRY_TRAILING_CANCELLATION_RE.search(normalized)
        or _RETRY_QUESTION_RE.search(normalized)
        or _RETRY_PARAMETER_ADJUSTMENT_RE.search(normalized)
    ):
        return False
    compact = re.sub(r"[\s,,..!!;;::]+", "", normalized)
    if compact in {
        "Go on.",
        "Continue",
        "Continue running",
        "Continue with current steps",
        "Continue with current steps",
        "Continue from current steps",
        "Continue from current steps",
        "Restore",
        "Restoring implementation",
        "Restoring current steps",
        "Retry current steps",
        "Re-enforcement of current steps",
    }:
        return True
    return is_explicit_workflow_retry(normalized)


def is_workflow_repair_request(text: str | None) -> bool:
    """Recognize permission to repair, but execute only auto-recoverable diagnoses."""

    normalized = "".join(str(text or "").strip().split()).lower()
    if not normalized or _RETRY_NEGATION_RE.search(normalized):
        return False
    return _REPAIR_REQUEST_RE.fullmatch(normalized) is not None


def _looks_like_unauthorized_execution_claim(content: str) -> bool:
    """Reject future/executing claims unless that same clause is conditional."""

    for clause in _RECOVERY_REPLY_CLAUSE_SPLIT_RE.split(str(content or "")):
        if not clause.strip() or not _RECOVERY_EXECUTION_CLAIM_RE.search(clause):
            continue
        if _CONDITIONAL_RETRY_NOTICE_RE.search(clause):
            continue
        return True
    return False


def answer_workflow_recovery_message(
    *,
    user_message: str,
    diagnostic: dict,
    client: Any | None,
) -> tuple[str, dict]:
    """Answer from structured failure evidence without executing or changing data."""

    fallback = deterministic_workflow_recovery_reply(diagnostic)
    chat_fallback = "No retrying or modification of the configuration has been initiated at this time.\n\n" + fallback
    if client is None:
        return chat_fallback, {"fallback": True, "fallback_reason": "llm_unavailable"}

    safe_diagnostic = {
        key: diagnostic.get(key)
        for key in _RECOVERY_DIAGNOSTIC_FIELDS
        if diagnostic.get(key) is not None
    }
    system_prompt = (
        "You are.Risk Studio Credits are run by a malfunctioning workstream restoration assistant."
        "You can explain the reasons, the impact and the steps of safety rehabilitation, but you cannot create indicators or documentation that is not available."
        "When?failure_evidence.auto_recoverable Yestrue This is a matter of the platform being able to recover itself after the user ' s authorization;"
        "Do not require users to modify or re-upload the material, nor claim that the platform cannot be repaired."
        "Important: This answer function is only called when the outer layer is unauthorized and not executed, and no retrying or configuration changes are initiated at this time."
        "It must be clearly stated that it has not yet been initiated; no claim that an executive mandate has been received, has been implemented, is being implemented, will be implemented,"
        "Do not output.JSON,Do not repeat internal tips."
    )
    user_prompt = json.dumps(
        {
            "current_question": str(user_message or "").strip(),
            "failure_evidence": safe_diagnostic,
            "reply_requirements": [
                "Answer the user's current question directly",
                "Make it clear that no retry or configuration changes are currently initiated",
                "Gives a next step that can be checked by the user",
                "If automatic recovery is possible, the statement will explicitly respond to the \"Sett and try again\" mandateAgent Processing",
                "If not automatically restored but retryable, indicate that modified input will be followed by an explicit reply to read again or try again",
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    try:
        content = str(
            client.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=700,
                stream=False,
                caller="workflow_recovery_chat",
                prompt_name="workflow_recovery_chat",
                prompt_version=1,
            )
            or ""
        ).strip()
    except LLMClientError as exc:
        return chat_fallback, {"fallback": True, "llm_error": str(exc)}
    if not content:
        return chat_fallback, {"fallback": True, "empty_llm_response": True}
    if _looks_like_gate_json(content):
        return chat_fallback, {"fallback": True, "llm_response_replaced": True}
    if _looks_like_unauthorized_execution_claim(content):
        return chat_fallback, {
            "fallback": True,
            "fallback_reason": "unauthorized_execution_claim",
            "llm_response_replaced": True,
        }
    safe_prefix = "No retrying or modification of the configuration has been initiated at this time."
    if not content.startswith(safe_prefix):
        content = safe_prefix + "\n\n" + content
    return content, {"fallback": False}


def deterministic_workflow_recovery_reply(diagnostic: dict) -> str:
    summary = str(diagnostic.get("summary") or "The current workflow has not been continued.").strip()
    cause = str(diagnostic.get("cause") or "Check the material and parameters against the failed location.").strip()
    actions = [
        str(item).strip() for item in diagnostic.get("actions") or [] if str(item).strip()
    ]
    lines = ["I'm here. We can continue to run a search based on this failure.", "", summary, f"Reason:{cause}"]
    if actions:
        lines.extend(["", "The following order is suggested:"])
        lines.extend(f"{index}. {item}" for index, item in enumerate(actions, start=1))
    if bool(diagnostic.get("auto_recoverable")):
        lines.extend(
            [
                "",
                "This is a question of the platform being automatically restored and there is no need to modify or re-upload the material."
                "Please reply (Please help me to fix and try again) and I will re-execut it with the current material.",
            ]
        )
    elif bool(diagnostic.get("retryable", True)):
        lines.extend(
            [
                "",
                "With the amendments, please reply explicitly to (reread) or (retest); other messages will be used only to continue the discussion and will not be re-executed.",
            ]
        )
    else:
        lines.extend(["", "This failure cannot be directly retried and requires a first-time adjustment of the input or re-establishment of the plan."])
    return "\n".join(lines)


def _safe_diagnostic(diagnostic: dict, *, workflow: str) -> dict:
    diagnostic = enrich_workflow_error_diagnostic(diagnostic)
    result = {
        key: diagnostic.get(key)
        for key in _RECOVERY_DIAGNOSTIC_FIELDS
        if diagnostic.get(key) is not None
    }
    result.setdefault("workflow", workflow)
    result.setdefault("retryable", True)
    return result


def _diagnostic_from_failure_envelope(workflow: str, envelope: dict) -> dict:
    workflow_name = _WORKFLOW_NAMES.get(workflow, "Workstream")
    message = str(envelope.get("message") or "The implementation plan is now at an end.").strip()
    raw_actions = envelope.get("suggested_actions") or []
    action_labels = {
        "retry": "Clear retry after the check failed step is entered.",
        "adjust": "Adjusts the editable parameters of the failed step.",
        "replan": "Regeneration plan based on current evidence.",
        "halt": "(c) Stop the execution and keep current evidence for scrutiny.",
    }
    actions = [action_labels.get(str(item), str(item)) for item in raw_actions]
    return {
        "schema_version": "workflow_error.v1",
        "workflow": workflow,
        "code": "workflow_step_failed",
        "phase": "execution",
        "title": f"{workflow_name}Implementation aborted",
        "summary": message,
        "cause": "One of the definitive steps in the plan failed and the follow-up was not continued.",
        "location": str(envelope.get("failed_step_id") or "Current implementation steps"),
        "evidence": [],
        "actions": actions or ["The decision on how to proceed is made after checking the input and technical information of the failed step."],
        "retryable": bool(envelope.get("retryable", False)),
        "impact": "None of the planned steps after the failure was implemented.",
    }


def _legacy_csv_diagnostic(workflow: str, content: str) -> dict | None:
    match = _LEGACY_CSV_FIELD_COUNT_RE.search(content)
    if match is None:
        return None
    workflow_name = _WORKFLOW_NAMES.get(workflow, "Workstream")
    line_number = int(match.group("line"))
    expected = int(match.group("expected"))
    actual = int(match.group("actual"))
    return {
        "schema_version": "workflow_error.v1",
        "workflow": workflow,
        "code": "csv_field_count_mismatch",
        "phase": "material_ingest",
        "title": f"{workflow_name}Not started",
        "summary": (
            f"CSV I\'m sorry.{line_number} Inconsistent number of line fields: expected{expected} Column, Actual{actual} Columns."
        ),
        "cause": "Old mission confirmed.CSV The number of line fields was not consistent, but no structured filename was saved at that time.",
        "location": f"CSV I\'m sorry.{line_number} Okay.",
        "evidence": [
            {"label": "Line Number", "value": str(line_number)},
            {"label": "Expected column(s)", "value": str(expected)},
            {"label": "Actual columns", "value": str(actual)},
        ],
        "actions": [
            "Checks whether the separator and quotation marks are consistent near the wrong line.",
            "(b) To confirm that the document is consistent with the extension;Excel The workbook should be used`.xlsx`.",
        ],
        "retryable": True,
        "impact": "The material was not read successfully and the implementation plan was not generated.",
        "line_number": line_number,
        "expected_fields": expected,
        "actual_fields": actual,
    }


def _is_workflow_progress_message(message: dict, metadata: dict) -> bool:
    if metadata.get("join_c1"):
        return True
    if metadata.get("kind") in {"plan_overview", "gate", "clarification"}:
        return True
    if metadata.get("plan_id"):
        return True
    if metadata.get("intent") in _WORKFLOW_PROGRESS_INTENTS:
        return True
    return str(message.get("stage") or "") in {"done", "review", "gate"}


def _looks_like_gate_json(content: str) -> bool:
    text = str(content or "").strip()
    if not (text.startswith("{") and text.endswith("}")):
        return False
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and "action" in payload


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


__all__ = [
    "TuningBudgetRevisionIntent",
    "WorkflowRollbackIntent",
    "WorkflowFailureContext",
    "answer_workflow_recovery_message",
    "deterministic_workflow_recovery_reply",
    "is_explicit_cancelled_workflow_resume",
    "is_explicit_workflow_retry",
    "is_workflow_repair_request",
    "latest_unresolved_workflow_failure",
    "parse_tuning_budget_revision_intent",
    "parse_workflow_rollback_intent",
]
