from __future__ import annotations

from collections.abc import Callable
import json
import re

from marvis.agent.prompts import (
    AGENT_SYSTEM_PROMPT,
    RISK_METRIC_INTERPRETATION_GUIDANCE,
    WORD_CONCLUSION_SYSTEM_PROMPT,
    WORD_CONCLUSION_V2_SYSTEM_PROMPT,
)
from marvis.agent.instruction_router import route_instruction
from marvis.agent.semantic_authorization import review_semantic_authorization
from marvis.model_algorithms import (
    is_platform_default_training_description,
    model_training_report_text,
)
from marvis.repositories.tasks import AGENT_REPORT_CONCLUSION_KEYS, AGENT_REPORT_WRITABLE_KEYS
from marvis.domain import TaskRecord
from marvis.llm_client import LLMClientError, OpenAICompatibleLLMClient
from marvis.report_texts import report_text_values_from_results
from marvis.validation.lift_ranking import assess_lift_ranking
from marvis.validation.overfitting import overfitting_check_from_validation_results
from marvis.validation.results import validation_results_from_dict
from marvis.validation.stress_risk import (
    stress_ks_risk,
    stress_psi_risk,
    stress_risk_label,
    worst_stress_risk,
)
from marvis.validation_report_copy import narrative_report_values
from marvis.agent_memory.prompting import (
    add_memory_to_prompt_payload,
    attach_memory_metadata,
    memory_context_was_truncated,
    normalize_memory_context,
)


REQUIRED_AGENT_REPORT_KEYS = tuple(sorted(AGENT_REPORT_CONCLUSION_KEYS))
_V2_FINAL_CONCLUSION_FORBIDDEN_PATTERNS = (
    re.compile(r"Materials(?:Scan|Identification|Perfect)"),
    re.compile(r"Verify input contract"),
    re.compile(r"PMML\s*(?:Full)?(?:Score|Rating)(?:Test|Completed|Pass.|Success|Overwrite|Sample|Time-consuming)?", re.IGNORECASE),
    re.compile(r"Report(?:Already|Enter|Generate|Outputs|Final)"),
    re.compile(r"Finalized|Recommendations(?:Yes.)?Antenatal review|Proposed review(?:Report|Conclusions)|Confirm.\s*Word", re.IGNORECASE),
    re.compile(r"Directly.(?:Deployment|Production)"),
)
_V2_PMML_SCORING_LEGACY_PATTERN = re.compile(
    r"Revertible(?:Sex)?|(?:Score|Rating|Deployment)?Coherence|Notebook\s*Model|Code Model|Original code model",
    re.IGNORECASE,
)
GLOBAL_AGENT_EVIDENCE_KEYS = frozenset(
    {
        "scan",
        "notebook_steps",
        "contract",
        "reproducibility",
        "pmml_scoring",
        "validation_results",
        "report_fields",
        "report_draft",
        "visible_stage_summaries",
    }
)
STAGE_EVIDENCE_KEYS = {
    "scan": ("scan", "contract", "notebook_steps"),
    "reproducibility": (
        "notebook_steps",
        "contract",
        "reproducibility",
        "pmml_scoring",
    ),
    "report": ("report_fields",),
}
SCAN_REQUIRED_CHECK_LABELS = (
    "Notebook Documentation",
    "Sample data",
    "PMML Model",
    "Data dictionary",
    "Notebook RMC Contracts",
)
SCAN_SUCCESS_STATUSES = {"success", "passed", "pass", "ok", "Pass.", "It's passed."}
METRICS_VALIDATION_RESULT_KEYS = (
    "model_name",
    "model_version",
    "algorithm",
    "target_type",
    "basic_info",
    "effectiveness",
    "overfitting_check",
    "stress_test",
)
WORD_CONCLUSION_MONTHLY_LIMIT = 12
WORD_CONCLUSION_FEATURE_LIMIT = 20
WORD_CONCLUSION_STRESS_CATEGORY_LIMIT = 20
WORD_CONCLUSION_PSI_BIN_LIMIT = 12
WORD_CONCLUSION_VISIBLE_SUMMARY_LIMIT = 8
WORD_CONCLUSION_VISIBLE_SUMMARY_CHARS = 1200
METRICS_BIN_TABLE_LIMIT = 10
REPRODUCIBILITY_NOTEBOOK_STEP_LIMIT = 16
REPRODUCIBILITY_CONTRACT_FEATURE_LIMIT = 20
NOTEBOOK_CONTRACT_SOURCE_PREVIEW_LIMIT = 3
NOTEBOOK_CONTRACT_SOURCE_PREVIEW_CHARS = 500
NOTEBOOK_FAILURE_CELL_LIMIT = 3
NOTEBOOK_FAILURE_SOURCE_CHARS = 1200
NOTEBOOK_FAILURE_FILE_LIMIT = 20
NOTEBOOK_FAILURE_LINE_LIMIT = 12
# Raw chart series that balloon the prompt without helping LLM reasoning
# (each curve carries thousands of (x, y) samples — easily 10+ MB total).
# AUC/KS summary numbers used in image-1's analysis already live in
# effectiveness.overall, so dropping the raw curves keeps the analysis honest
# while shrinking the prompt by >99%.
OVERSIZED_EFFECTIVENESS_KEYS = frozenset({"roc_ks_curves"})
START_VALIDATION_GUIDANCE_FRAGMENTS = (
    "It's a good way to help start the validation.",
    "If you need to start, enter",
    "Please enter \"Initiation of validation\"",
    'Please enter"Start Authentication"',
    "Enter Start Validation",
    'Input"Start Authentication"',
)
CONVERSATION_MEMORY_MAX_MESSAGES = 48
CONVERSATION_MEMORY_MAX_CHARS = 32000
CONVERSATION_MEMORY_MESSAGE_MAX_CHARS = 2400
GREETING_CHAT_FALLBACK = (
    "Hello, I'm here. You can ask me directly about the results, the meaning of the indicators, the results.PMML or the report concludes,"
    "And you can tell me what you want to do next."
)
STAGE_SUMMARY_MAX_TOKENS = {
    "metrics": 4096,
}
METRICS_SUMMARY_REQUIRED_SECTIONS = (
    "Overall judgement",
    "Performance",
    "Stability performance",
    "Pressure test risk",
    "Recommendations",
)
AGENT_RESPONSE_PREAMBLE_PATTERNS = (
    r"^(?:Okay.|Okay.|Copy that.|Understood.|Yeah.)[,,.!!\s]*",
    r"^(?:I will.|I'll...)?(?:Compliance|Based on|According to)(?:You.|You.)?It's...?(?:Instructions|Request)[,,.!!\s]*",
    # The trailing terminator is required (+, not *): otherwise the bare Analysis/Summary
    # alternatives match mid-sentence and delete the opening clause of legitimate
    # content like "The following is a detailed account of the present validation analysis." → "Details.".
    r"^Here's what I'm talking about.(?:Targeted|About|Based on)[^\n]{0,160}?(?:Validation analysis|Phase analysis|Analysis notes|Validation Summary|Analysis|Summary)[.::\s]+",
)
AGENT_RESPONSE_LEADING_SEPARATOR_PATTERN = re.compile(r"^(?:[-*_]\s*){3,}\s*")

# Start-family negation markers — mirror is_continue_validation_intent's
# negation_markers so "Don't start checking." / "Do not start authentication" short-circuit to chat
# before the direct-phrase substring branch can fire. Includes the generic
# negators plan_driver._NEGATED_CONFIRM already trusts (Not yet./Don't./Don't./No, I'm fine./
# No, I don't./Not yet./Not yet.) so phrasings not enumerated below are still caught.
START_VALIDATION_NEGATION_MARKERS = (
    "Do Not Start",
    "Don't start.",
    "Don't start yet.",
    "Don't start.",
    "Not now.",
    "Not for now.",
    "Don't start.",
    "No need to start.",
    "No need to start.",
    "I don't want to start.",
    "There's no need to start.",
    "I'm not going to start.",
    "It won't start.",
    "- Not yet.",
    "Do Not Start",
    "Do Not Start",
    "Don't start.",
    "Not implemented",
    "Do Not Execute",
    "Don't do it.",
    "Do Not Run",
    "Do Not Run",
    "No, no, no, no!",
    "Don't run!",
    "Not yet.",
    "Don't.",
    "Don't.",
    "No, I'm fine.",
    "No, I don't.",
    "Not yet.",
    "Not yet.",
    "Pause",
)
# English-negation parity with plan_driver._NEGATED_CONFIRM's do-not / don't
# family, so "do not start validation" / "don't run validation" stay chat.
_START_VALIDATION_ENGLISH_NEGATION = re.compile(
    r"\b(?:do\s*not|don't|dont|not)\s+(?:start|run|validate)\b",
    re.IGNORECASE,
)
# Interrogative guard — mirror plan_driver._QUESTION's particle set plus
# start-context interrogatives. NOTE: bare trailing 'Yeah.' is intentionally
# EXCLUDED (unlike plan_driver._QUESTION) because 'Let's do it.'/'Let's get started.'/'Run.'/
# 'Run.' are legitimate start affirmatives in direct_commands, not questions.
_START_QUESTION = re.compile(
    r"[??]|- You're not?|And?$|When?|When?|Do you want it?|Do you need it or not?|Can you...|Can I?|Isn't that right?",
    re.IGNORECASE,
)
_VALIDATION_AUTHORIZATION_QUESTION = re.compile(
    r"[??]|- You're not?(?:[\s..!!]*$)|And?(?:[\s..!!]*$)|Why?|What?(?:Sample)?|How's that?|"
    r"What is it?|What is it?|What?(?:Meaning|Impact|Reason|Role)|What?(?:Impact|Difference|Meaning)|"
    r"Do you want it?|Do you need it or not?|Can you...|Can I?|Okay?|Okay?|Right?|Isn't that right?",
    re.IGNORECASE,
)


def is_start_validation_intent(content: str) -> bool:
    text = content.strip().lower()
    if not text:
        return False
    # Question guard on RAW text (like plan_driver.is_confirm) so trailing
    # particles / question marks disqualify interrogatives before any positive
    # match. 'Yeah.$' is deliberately not treated as a question here.
    if _START_QUESTION.search(text):
        return False
    if _START_VALIDATION_ENGLISH_NEGATION.search(text):
        return False
    compact = "".join(text.split())
    # Drop interior punctuation for the negation scan, same as
    # is_continue_validation_intent, so "No, no, no. Let's get this thing checked." normalizes cleanly.
    compact_np = compact
    for ch in ",.,;:,;:":
        compact_np = compact_np.replace(ch, "")
    if any(marker in compact_np for marker in START_VALIDATION_NEGATION_MARKERS):
        return False
    direct_phrases = (
        "Start Authentication",
        "Start Model Validation",
        "Start Authentication",
        "Start Model Validation",
        "Execute Authentication",
        "Execute Model Validation",
        "Run Authentication",
        "Run Model Validation",
        "Run validation",
        "Run Model Validation",
        "Start",
        "Start running",
        "Start running.",
        "Run.",
        "Run it.",
        "Run!",
        "Start Task",
        "Start the mission.",
        "startvalidation",
        "runvalidation",
        "validatethistask",
    )
    if any(phrase in compact for phrase in direct_phrases):
        return True
    direct_commands = {
        "Start",
        "Let's do it.",
        "Start",
        "Let's get started.",
        "Run",
        "Run.",
        "Implementation",
        "Let's do it.",
        "Run.",
        "start",
        "run",
        "validate",
    }
    return compact.strip("..!!??") in direct_commands


def is_continue_validation_intent(content: str) -> bool:
    text = content.strip().lower()
    if not text:
        return False
    compact = "".join(text.split()).strip("..!!??")
    # Drop interior punctuation so acknowledged-continue phrasings like
    # "I see. Go ahead and verify." share a normal form with "Let's go on with the test.". Without
    # this, the Chinese comma blocks affix stripping and the matcher
    # routes the user's intent into the chat-question branch.
    for ch in ",.,;:,;:":
        compact = compact.replace(ch, "")
    negation_markers = (
        "No more.",
        "Don't go on.",
        "I'm not going to go on.",
        "Not for now.",
        "Not for now.",
        "No need to continue.",
        "Don't go on.",
        "No need to continue.",
        "No need to continue.",
        "I don't want to go on.",
        "There's no need to continue.",
        "I'm not going to go on.",
        "I won't go on.",
    )
    if any(marker in compact for marker in negation_markers):
        return False
    direct_phrases = {
        "Go on.",
        "Go on.",
        "Please continue.",
        "Next",
        "Go on with the next step.",
        "Implement next steps",
        "Continue",
        "Continue Authentication",
        "Down.",
        "You can go on.",
        "Confirm that you're going to continue.",
        "goon",
        "continue",
        "next",
    }
    if compact in direct_phrases:
        return True
    if _is_continue_report_draft_intent(compact):
        return True
    # Substring fallback for unambiguous continue fragments. After the
    # negation markers above were ruled out, finding any of these inside
    # the compacted message means the user wants to advance even though
    # they prefixed an acknowledgment.
    unambiguous_continue_fragments = (
        "Continue Authentication",
        "Continue",
        "Go on with the next step.",
        "Implement next steps",
    )
    if any(fragment in compact for fragment in unambiguous_continue_fragments):
        return True
    normalized = _strip_continue_command_affixes(compact)
    return normalized in direct_phrases or _is_continue_report_draft_intent(normalized)


def _is_continue_report_draft_intent(value: str) -> bool:
    if "Go on." not in value and "Next" not in value and "Implementation" not in value:
        return False
    report_actions = (
        "Continue generating reports",
        "Continue Generatingword",
        "Keep writing the report.",
        "Continuing drafting of the report",
        "Continue to generate drafts",
        "Work on the drafts continued",
        "Continue to generate conclusions",
        "Continue drafting conclusions",
        "Continue to generate three segments",
        "Continue drafting three paragraphs.",
        "Next Generation Report",
        "Next Generationword",
        "Implementation report",
        "Conclusions of the implementation report",
    )
    return any(action in value for action in report_actions)


def _strip_continue_command_affixes(value: str) -> str:
    text = value
    # Sorted longest-first so multi-char acknowledgments ("I see.") strip
    # cleanly before the shorter overlap ("Understood.") gets a chance to leave a
    # trailing "Yes." stuck on the front of the remaining phrase.
    prefixes = (
        "I see.",
        "Got it.",
        "Okay.",
        "Got it.",
        "Copy that.",
        "Roger that.",
        "Yes.",
        "Understood.",
        "Okay.",
        "Trouble.",
        "Help me.",
        "Confirm.",
        "Yeah.",
        "Please.",
        "Well...",
        "First",
        "Okay.",
        "Yeah.",
        "ok",
    )
    suffixes = ("One second.", "Down", "Yeah.", "Yes.")
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if text.startswith(prefix) and len(text) > len(prefix):
                text = text[len(prefix) :]
                changed = True
        for suffix in suffixes:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)]
                changed = True
    return text


def is_agent_advance_intent(content: str) -> bool:
    return is_start_validation_intent(content) or is_continue_validation_intent(content)


def review_validation_instruction_authorization(
    model_profile: dict,
    *,
    gate_context: str,
    instruction: str,
) -> dict | None:
    """Return audited evidence only for a two-pass, fail-closed authorization.

    Legacy model validation does not have a PlanDriver gate object, but Agent mode
    still exposes a free-text confirmation seam.  Reuse the same router and
    independent semantic reviewer as PlanDriver while keeping the executable
    decision parameter-free: a condition, question, adjustment, rejection,
    malformed reply, or client failure can never become an advance command.
    """

    normalized_instruction = str(instruction or "").strip()
    if (
        not model_profile
        or not normalized_instruction
        or _VALIDATION_AUTHORIZATION_QUESTION.search(normalized_instruction)
        or _is_greeting_message(normalized_instruction)
    ):
        return None
    client = OpenAICompatibleLLMClient(model_profile)
    try:
        route = route_instruction(
            client,
            gate_context=gate_context,
            instruction=instruction,
            strict_contract=True,
        )
    except Exception:
        return None
    if (
        route.get("action") != "confirm"
        or route.get("confidence") != "high"
        or route.get("explicit_authorization") is not True
        or bool(route.get("constraint"))
        or bool(route.get("params"))
    ):
        return None
    review = review_semantic_authorization(
        client,
        gate_context=gate_context,
        instruction=instruction,
        proposed_params={},
    )
    if not review.authorized:
        return None
    return {
        "evidence_quote": review.evidence_quote,
        "reason": review.reason,
        "confidence": review.confidence,
        "route_reason": str(route.get("reason") or ""),
    }


def _compact_agent_command(content: str) -> str:
    return "".join(str(content or "").strip().lower().split()).strip("..!!??")


def is_agent_material_reselection_intent(content: str) -> bool:
    compact = _compact_agent_command(content)
    if not compact:
        return False
    selection_markers = (
        "Reselect",
        "Re-select",
        "Re-select",
        "Replacement",
        "Change it.",
        "Change it.",
        "Re-lock",
        "Modify selection of materials",
        "Modify File Selection",
    )
    material_markers = (
        "Materials",
        "Authentication file",
        "notebook",
        "Sample",
        "pmml",
        "Data dictionary",
    )
    return any(marker in compact for marker in selection_markers) and any(
        marker in compact for marker in material_markers
    )


def is_agent_report_revision_intent(content: str) -> bool:
    compact = _compact_agent_command(content)
    if not compact:
        return False
    revision_markers = (
        "Amendments",
        "Corrigendum",
        "Correct",
        "Modify",
        "Adjustment",
        "Rewrite",
        "Replace with",
        "Redo",
        "Replace",
        "Delete",
        "Delete it.",
        "Don't mention it.",
        "No more.",
        "Evaluation only",
        "Keep Only",
        "Supplementary",
    )
    report_markers = (
        "Report",
        "Draft",
        "Three paragraphs.",
        "Conclusions",
        "Summary of stress tests",
        "Pressure impact recommendations",
        "Final validation conclusion",
        "Overview",
        "Scope of application",
        "Bad sample.",
        "Good sample.",
        "word",
        "excel",
        "Expenditure",
        "Letters",
    )
    return any(marker in compact for marker in revision_markers) and any(
        marker in compact for marker in report_markers
    )


def agent_rerun_stage(content: str) -> str | None:
    compact = _compact_agent_command(content)
    if not compact:
        return None
    if is_agent_material_reselection_intent(content):
        return None
    if is_agent_report_revision_intent(content):
        return "word_conclusion_draft"
    rerun_markers = (
        "Restart",
        "Run again.",
        "Redo",
        "Again.",
        "Redo",
        "Run again!",
        "Re-execution",
        "Regenerated",
        "Write again.",
        "From the beginning.",
        "From the beginning.",
        "From the beginning.",
        "From the beginning.",
    )
    if not any(marker in compact for marker in rerun_markers):
        return None
    if _matches_rerun_stage(
        compact,
        (
            "From the beginning.",
            "From the beginning.",
            "From the beginning.",
            "From the beginning.",
            "From the first step",
            "From Step 1",
            "From Step 1",
            "Step one.",
            "Full Process",
            "All Processes",
            "Full process",
            "Full implementation",
            "Full Runback",
            "Full",
            "Re-introduce",
            "All of them.",
            "Re-execut All",
            "Re-execut all of it.",
            "Run it all again.",
            "Run again.",
        ),
    ):
        return "scan"
    if _matches_rerun_stage(
        compact,
        (
            "Step four.",
            "Step 4",
            "4Step",
            "Step 4",
            "Step four",
            "Phase IV",
            "Phase 4",
            "Phase 4",
            "Phase IV",
            "step4",
            "Step 4",
            "Fourth step",
            "Report",
            "word",
            "Draft",
            "Conclusions",
            "Three paragraphs.",
            "Summary of the three paragraphs",
            "Three paragraphs of the conclusions",
            "Write a report.",
            "Generate Report",
            "Report Generation",
            "wordReport",
            "Final report",
        ),
    ):
        return "word_conclusion_draft"
    if _matches_rerun_stage(
        compact,
        (
            "Step three.",
            "Step 3",
            "3Step",
            "Step 3",
            "Step 3",
            "Phase III",
            "Phase 3",
            "Phase 3",
            "Phase III",
            "step3",
            "Step 3",
            "Third step",
            "Effects",
            "Stability",
            "Effect stability",
            "Effects and stability",
            "Model Effects",
            "Model Effects&Stability",
            "Indicators",
            "Overview of indicators",
            "ks",
            "psi",
            "auc",
            "Box",
            "Pressure test",
            "Compromise",
            "oot",
        ),
    ):
        return "metrics"
    if _matches_rerun_stage(
        compact,
        (
            "Step two.",
            "Step 2",
            "2Step",
            "Step 2",
            "Step two",
            "Phase II",
            "Phase 2",
            "Phase 2",
            "Phase II",
            "step2",
            "Step 2",
            "Second step",
            "Rewind",
            "Recurring",
            "Revertible",
            "Recoverability",
            "Model recurrence",
            "Models Recapable",
            "Revert Authentication",
            "Recoverability validation",
            "notebook",
            "The scores are the same.",
            "Consistency of scores",
            "Modelling Code",
            "pmmlScore",
            "Coherence of deployment",
        ),
    ):
        return "reproducibility"
    if _matches_rerun_stage(
        compact,
        (
            "Step one.",
            "Step 1",
            "1Step",
            "Step 1",
            "Step one.",
            "Phase I",
            "Phase 1",
            "Phase 1",
            "Phase I",
            "step1",
            "Step 1",
            "First step",
            "Materials",
            "Perfect",
            "Completeness",
            "Material completeness",
            "Complete Verification",
            "Completeness check",
            "Material completeness verification",
            "Material Identification",
            "Material scanning",
            "Read",
            "Identification",
            "Scan",
            "Contents",
            "Documentation",
            "rmcContracts",
        ),
    ):
        return "scan"
    return None


def _matches_rerun_stage(compact: str, markers: tuple[str, ...]) -> bool:
    return any(marker in compact for marker in markers)


def is_stop_validation_intent(content: str) -> bool:
    text = content.strip().lower()
    if not text:
        return False
    negated_phrases = (
        "Don't stop.",
        "Don't stop.",
        "There's no need to stop.",
        "Don't stop.",
        "Don't stop.",
        "Don't cancel.",
        "No need to cancel.",
        "Don't cancel.",
        "Don't cancel it yet.",
        "Do not abort",
        "Don't interrupt.",
    )
    if any(phrase in text for phrase in negated_phrases):
        return False
    if re.search(r"[??]|Why?|Why?|What?|How's that?|Is it possible?|Did you?|Did you stop?|Did you stop?", text):
        return False
    if re.search(
        r"(?:"
        r"(?:Present.|Wait.|- Wait.|Run To|Execute To).{1,40}(?:Location|Back|Time)?"
        r"|Yes..{1,40}(?:Location|Time)"
        r")(?:Stop|Stop!|Pause|Abort)",
        text,
    ):
        return False
    keywords = (
        "Stop",
        "Stop!",
        "Termination",
        "Abort",
        "Cancel",
        "Stop!",
        "Don't run.",
        "stop",
        "cancel",
        "abort",
        "terminate",
    )
    return any(keyword in text for keyword in keywords)


def _is_greeting_message(content: str) -> bool:
    compact = "".join(content.strip().lower().split()).strip("..!!??~~")
    return compact in {
        "Hello.",
        "Hello.",
        "hello",
        "hi",
        "hey",
        "Hey.",
        "Hello?",
        "Are you here?",
    }


def _chat_fallback_for_message(user_message: str) -> str:
    if _is_greeting_message(user_message):
        return GREETING_CHAT_FALLBACK
    return "I can't get this answer through the big model right now. Check the big model.API Configure, network connectivity or retry at a later date."


def _looks_like_start_validation_guidance(content: str) -> bool:
    return any(fragment in content for fragment in START_VALIDATION_GUIDANCE_FRAGMENTS)


def agent_conclusions_confirmed(values: dict[str, str]) -> bool:
    return all(str(values.get(key) or "").strip() for key in REQUIRED_AGENT_REPORT_KEYS)


def latest_report_draft_context(messages: list[dict]) -> dict:
    """Read the current editable narrative, including deliberate empty values.

    A streaming placeholder has no draft values yet; it must not hide the saved
    draft that a rewrite is based on. An incomplete saved draft is still the
    current draft and must never fall back to an older confirmable version.
    """
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        if message.get("stage") == "word_conclusion_confirmed":
            return {}
        if message.get("stage") != "word_conclusion_draft":
            continue
        metadata = message.get("metadata") or {}
        values = metadata.get("draft_values")
        revision = metadata.get("report_revision")
        if not isinstance(values, dict):
            continue
        if not isinstance(revision, int) or isinstance(revision, bool):
            return {}
        return {
            "message_id": message.get("id"),
            "report_revision": revision,
            "draft_edit_revision": metadata.get("draft_edit_revision", 0),
            "text_values": {
                key: value for key, value in values.items()
                if key in AGENT_REPORT_WRITABLE_KEYS and isinstance(value, str)
            },
        }
    return {}


def summarize_stage(
    *,
    task: TaskRecord,
    stage: str,
    evidence: dict,
    memory_context: dict | None = None,
    model_profile: dict,
    fallback: str,
    on_delta: Callable[[str], None] | None = None,
) -> tuple[str, dict]:
    prompt = _stage_prompt(
        task=task,
        stage=stage,
        evidence=evidence,
        memory_context=memory_context,
    )
    # LLM-5: memory injection is one of the three named highest-volume prompt
    # touch points; surface the truncation flag on this call's audit record.
    truncated = memory_context_was_truncated(normalize_memory_context(memory_context))
    client = _client(model_profile)
    try:
        content = client.complete(
            system_prompt=AGENT_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=STAGE_SUMMARY_MAX_TOKENS.get(stage),
            on_delta=on_delta,
            truncated=truncated,
        )
    except LLMClientError as exc:
        guarded_fallback = (
            _sectioned_metrics_summary(fallback, fallback)
            if stage == "metrics"
            else fallback
        )
        return guarded_fallback, {"llm_error": str(exc), "fallback": True}
    cleaned = _strip_agent_response_preamble(content or fallback)
    metadata = {"fallback": False}
    if stage == "metrics":
        missing_sections = _missing_metrics_summary_sections(cleaned)
        if missing_sections:
            repair_prompt = _metrics_summary_repair_prompt(
                prompt,
                previous_response=cleaned,
                missing_sections=missing_sections,
            )
            try:
                repaired_content = client.complete(
                    system_prompt=AGENT_SYSTEM_PROMPT,
                    user_prompt=repair_prompt,
                    temperature=0.1,
                    max_tokens=STAGE_SUMMARY_MAX_TOKENS.get(stage),
                    truncated=truncated,
                )
            except LLMClientError as exc:
                repaired_content = ""
                metadata["llm_repair_error"] = str(exc)
            repaired = _strip_agent_response_preamble(repaired_content or "")
            if repaired and not _missing_metrics_summary_sections(repaired):
                cleaned = repaired
                metadata["summary_repaired"] = True
            else:
                cleaned = _sectioned_metrics_summary(cleaned, fallback)
                metadata["fallback"] = True
                metadata["summary_repair_failed"] = True
    guarded = _guard_stage_summary(
        task=task,
        stage=stage,
        evidence=evidence,
        content=cleaned,
        fallback=fallback,
    )
    if guarded != cleaned:
        metadata["guarded_stage_summary"] = True
        if stage == "scan":
            metadata["guarded_scan_summary"] = True
    return guarded, attach_memory_metadata(metadata, memory_context, use_reason=stage)


def _missing_metrics_summary_sections(content: str) -> list[str]:
    text = str(content or "")
    missing: list[str] = []
    for section in METRICS_SUMMARY_REQUIRED_SECTIONS:
        heading = re.compile(
            rf"(?m)^\s{{0,3}}(?:#{{1,6}}\s*|[-+*]\s+|\d+[.,)]\s*)?"
            rf"(?:\*\*|__)?{re.escape(section)}"
            r"(?:\*\*|__)?\s*(?::|:|$)",
        )
        if not heading.search(text):
            missing.append(section)
    return missing


def _metrics_summary_repair_prompt(
    original_prompt: str,
    *,
    previous_response: str,
    missing_sections: list[str],
) -> str:
    try:
        payload = json.loads(original_prompt)
    except (TypeError, json.JSONDecodeError):
        payload = {"original_request": str(original_prompt or "")}
    payload["previous_response"] = str(previous_response or "")[:12_000]
    payload["repair_request"] = {
        "reason": "stage summary is missing required sections",
        "missing_sections": list(missing_sections),
        "required_sections": list(METRICS_SUMMARY_REQUIRED_SECTIONS),
        "instruction": (
            "Please rephrase the current phase analysis to use the five headings above each; each section should be based on the originalevidence The blogger says:"
            "You may not create indicators or add only headings. Only rewritten analytical text."
        ),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _sectioned_metrics_summary(content: str, fallback: str) -> str:
    overall = str(content or fallback or "Platform indicators have been generated and are reviewed in conjunction with the page evidence.").strip()
    return (
        f"Overall judgement\n{overall}\n\n"
        "Performance\nPlease calculate the platformKS,AUC and sample layering.\n\n"
        "Stability performance\nPlease calculate the platformPSI,The results are measured by period and outside the sample.\n\n"
        "Pressure test risk\nPlease base the Platform ' s generation of high, medium and low risk layers and the influence of the corresponding data sources.\n\n"
        "Recommendations\nOngoing monitoring and manual review in conjunction with the above-mentioned definitive indicators and stress tests."
    )


def compose_agent_start_message(
    *,
    task: TaskRecord,
    model_profile: dict,
    on_delta: Callable[[str], None] | None = None,
) -> tuple[str, dict]:
    prompt = _stage_prompt(
        task=task,
        stage="agent_start",
        evidence={
            "next_tool": "scan_materials",
            "tool_purpose": "IdentificationNotebook,Sample data,PMML Models, data dictionary and checkNotebook RMC Contracts",
        },
    )
    fallback = (
        "I will first verify the integrity of this certification as a credit wind model."
        "Then call the Material Identification Tool to read, identify and check the directory of key documentsNotebook RMC Contract."
    )
    try:
        content = _client(model_profile).complete(
            system_prompt=AGENT_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.2,
            on_delta=on_delta,
        )
    except LLMClientError as exc:
        return fallback, {"llm_error": str(exc), "fallback": True}
    return _strip_agent_response_preamble(content or fallback), {"fallback": False}


def failure_summary(
    *,
    task: TaskRecord,
    stage: str,
    error: str,
    evidence: dict | None = None,
    memory_context: dict | None = None,
    model_profile: dict,
    on_delta: Callable[[str], None] | None = None,
) -> tuple[str, dict]:
    failure_evidence = {"failed_stage": stage, "error": error}
    if isinstance(evidence, dict):
        notebook_failure = _compact_notebook_failure_evidence(
            evidence.get("notebook_steps")
        )
        if notebook_failure:
            failure_evidence["notebook_failure"] = notebook_failure
        scan = _compact_scan_evidence(evidence.get("scan"))
        if scan:
            failure_evidence["scan"] = scan
    prompt = _stage_prompt(
        task=task,
        stage="failure",
        evidence=failure_evidence,
        memory_context=memory_context,
    )
    fallback = f"Failure phase:{stage}\nDirect causes:{error}\nPossible cause: Please check the input of materials, the implementation environment and upstream products at this stage.\nNext: Amended and re-executed from the failure phase."
    try:
        content = _client(model_profile).complete(
            system_prompt=AGENT_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.1,
            on_delta=on_delta,
        )
    except LLMClientError as exc:
        return fallback, {"llm_error": str(exc), "fallback": True}
    return _strip_agent_response_preamble(content or fallback), attach_memory_metadata(
        {"fallback": False},
        memory_context,
        use_reason="failure",
    )


def answer_chat_message(
    *,
    task: TaskRecord,
    user_message: str,
    conversation: list[dict],
    evidence: dict,
    memory_context: dict | None = None,
    model_profile: dict,
    on_delta: Callable[[str], None] | None = None,
) -> tuple[str, dict]:
    prompt = _chat_prompt(
        task=task,
        user_message=user_message,
        conversation=conversation,
        evidence=evidence,
        memory_context=memory_context,
    )
    fallback = _chat_fallback_for_message(user_message)
    # LLM-5: memory injection is one of the three named highest-volume prompt
    # touch points; surface the truncation flag on this call's audit record.
    truncated = memory_context_was_truncated(normalize_memory_context(memory_context))
    try:
        raw_content = _client(model_profile).complete(
            system_prompt=AGENT_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.2,
            on_delta=on_delta,
            truncated=truncated,
        )
        content = (raw_content or "").strip()
    except LLMClientError as exc:
        return fallback, {"llm_error": str(exc), "fallback": True}
    if not content:
        return fallback, {"fallback": True, "empty_llm_response": True}
    if _is_greeting_message(user_message) and _looks_like_start_validation_guidance(
        content
    ):
        return fallback, {"fallback": True, "llm_response_replaced": True}
    return _strip_agent_response_preamble(content), attach_memory_metadata(
        {"fallback": False},
        memory_context,
        use_reason="chat",
    )


def _strip_agent_response_preamble(content: str) -> str:
    original = str(content or "").strip()
    if not original:
        return ""
    text = original
    for _ in range(6):
        before = text
        text = AGENT_RESPONSE_LEADING_SEPARATOR_PATTERN.sub("", text).lstrip()
        for pattern in AGENT_RESPONSE_PREAMBLE_PATTERNS:
            text = re.sub(pattern, "", text, count=1).lstrip()
            text = AGENT_RESPONSE_LEADING_SEPARATOR_PATTERN.sub("", text).lstrip()
        if text == before:
            break
    return text.strip() or original


def generate_word_conclusions(
    *,
    task: TaskRecord,
    evidence: dict,
    memory_context: dict | None = None,
    model_profile: dict,
    user_instruction: str | None = None,
) -> tuple[dict[str, str], dict]:
    prompt = _stage_prompt(
        task=task,
        stage="word_conclusion_draft",
        evidence=evidence,
        memory_context=memory_context,
        user_instruction=user_instruction,
    )
    try:
        content = _client(model_profile).complete(
            system_prompt=(
                WORD_CONCLUSION_V2_SYSTEM_PROMPT
                if task.validation_workflow_version == 2
                else WORD_CONCLUSION_SYSTEM_PROMPT
            ),
            user_prompt=prompt,
            temperature=0.2,
            response_format={"type": "json_object"},
            stream=False,
        )
        values = _parse_conclusion_json(content)
        values = _with_narrative_report_seeds(task, values)
        values = _with_training_description_seed(task, values, evidence)
        if task.validation_workflow_version == 2:
            _validate_v2_word_conclusions(values)
    except (LLMClientError, ValueError) as exc:
        return {}, attach_memory_metadata(
            {"llm_error": str(exc), "fallback": True, "confirmable": False},
            memory_context,
            use_reason="word_conclusion_draft",
        )
    return values, attach_memory_metadata(
        {"fallback": False},
        memory_context,
        use_reason="word_conclusion_draft",
    )


def fallback_word_conclusions(
    *,
    task: TaskRecord,
    evidence: dict | None = None,
) -> dict[str, str]:
    name = task.model_name or "This Model"
    deterministic = _fallback_conclusions_from_validation_evidence(
        evidence=evidence,
        validation_workflow_version=task.validation_workflow_version,
    )
    if deterministic is not None:
        return _with_training_description_seed(
            task,
            _with_narrative_report_seeds(task, deterministic),
            evidence,
        )
    if task.validation_workflow_version == 2:
        return _with_training_description_seed(
            task,
            _with_narrative_report_seeds(
                task,
                {
                    "TEXT:pressure_test_summary": (
                        "The Platform has completed the output of the indicators related to model pressure testing."
                        "It is recommended that the certification staff review the stress scenarios in a structured and detailed manner.KS,PSI And grade the distribution change."
                    ),
                    "TEXT:pressure_impact_recommendation": (
                        "It is recommended that the data sources and feature categories with a high impact in model pressure tests be set up with an upper-line monitoring threshold;"
                        "In the event of significant stability or a reduction in differentiated capabilities, the quality of the source and the distribution of samples should be reviewed before continuing to be used."
                    ),
                    "TEXT:final_validation_conclusion": (
                        f"There is a lack of immediate evaluation at present{name}- Evidence of structuralization of effects, external stability of samples, composting and pressure risk,"
                        "It is therefore not possible to draw conclusions on the availability of models.PMMLDeployment is available."
                    ),
                },
            ),
            evidence,
        )
    return _with_training_description_seed(
        task,
        _with_narrative_report_seeds(
            task,
            {
                "TEXT:pressure_test_summary": (
                    "The Platform has completed the output of the pressure test related indicators."
                    "Suggested combination of certification officersExcel We'll review the situation in detail.KS,PSI And grade the distribution change."
                ),
                "TEXT:pressure_impact_recommendation": (
                    "It is recommended that the data sources and feature categories with high impact in the pressure test be set up with an upper-line monitoring threshold;"
                    "In the event of significant stability or a reduction in differentiated capabilities, the quality of the source and the distribution of samples should be reviewed before continuing to be used."
                ),
                "TEXT:final_validation_conclusion": (
                    f"This validation is around{name}Develop material integrity,Notebook Recoverability, model effects, stability and pressure testing."
                    "From the current Platform product, the core validation process has been implemented to the stage of the report ' s outcome candidate generation; the final compliance requirement should remain structured,"
                    "The stress test is detailed and the tester)s review is confirmed.Word Pre-conclusion focus checkOOT Distinguishing effects,PSI Stability and key variable stress performance."
                ),
            },
        ),
        evidence,
    )


def _fallback_conclusions_from_validation_evidence(
    *,
    evidence: dict | None,
    validation_workflow_version: int | None = None,
) -> dict[str, str] | None:
    if not isinstance(evidence, dict):
        return None
    raw_results = evidence.get("validation_results")
    if not isinstance(raw_results, dict):
        return None
    payload = dict(raw_results)
    overfitting = payload.pop("overfitting_check", None)
    try:
        results = validation_results_from_dict(payload)
    except ValueError:
        return None
    if not isinstance(overfitting, dict):
        overfitting = overfitting_check_from_validation_results(payload)

    computed = report_text_values_from_results(results)
    pressure_summary = computed.get(
        "TEXT:pressure_test_summary",
        "The Platform has completed the stress tests, for which specific indicators are providedExcel Detailed.",
    )
    baseline_ks = results.stress_test.baseline.ks
    category_risks: list[str | None] = []
    for item in results.stress_test.per_category:
        if item.status != "completed":
            category_risks.append(None)
            continue
        category_risks.append(worst_stress_risk(
            stress_ks_risk(baseline_ks, item.ks_after)
            if item.ks_after is not None
            else None,
            stress_psi_risk(item.psi_vs_baseline),
        ))
    pressure_risk = worst_stress_risk(*category_risks)
    pressure_label = stress_risk_label(pressure_risk)
    oot = next(
        (row for row in results.effectiveness.overall if row.split == "oot"),
        None,
    )
    oot_text = (
        f"OOT KS {oot.ks:.4f}(I\'m just showing, not participating in the decision-making.OOT PSI {oot.psi_vs_train:.4f}"
        if oot is not None
        else "OOT KS/PSI Data Missing"
    )
    if results.pmml_scoring is not None:
        scoring_text = f"PMML Rating{('Pass.' if results.pmml_scoring.status == 'pass' else 'Not adopted')}"
    else:
        scoring_text = "Notebook The results of the scores are in the details of the structural tests."

    if pressure_risk == "high":
        recommendation = (
            "(b) The pressure test has a high-risk scenario, which should check missing sources, sample distribution and compartment migration;"
            "Antenatal delivery should be monitored and melted, and a backup rating or manual review programme should be prepared."
        )
    elif pressure_risk == "medium":
        recommendation = (
            "Pressure tests meet early warning thresholds, recommend manual verification of abnormal categories and notify the modelling team;"
            "We need to get it on the line.KS,PSI With the missing ratio of the source."
        )
    else:
        recommendation = (
            "The pressure tests did not identify high-risk scenarios and could be continued to be assessed in conjunction with other determinative door closures;"
            "General should be implemented after you go onlineKS,PSI The main reason is that the information is not available."
        )
    metrics_text = _effectiveness_metric_sentence(results.effectiveness.overall)
    stability_text = _oot_stability_sentence(oot)
    overfit_text = _overfitting_sentence(overfitting)
    bin_text = _binning_sentence(results)
    conclusion_parts = [
        metrics_text,
        oot_text,
        stability_text,
        overfit_text,
        bin_text,
        f"The highest pressure test is{pressure_label}",
    ]
    if validation_workflow_version != 2:
        conclusion_parts.insert(0, scoring_text)
    conclusion = (
        ";".join(part for part in conclusion_parts if part)
        + ".This paragraph provides a conservative retreat of certainty after the failure of the large model text generation, with indicators taken from the Platform results;"
        "End-use decisions still need to be reviewed in conjunction with the stability, stress testing and integrity of reporting."
    )
    return {
        "TEXT:pressure_test_summary": pressure_summary,
        "TEXT:pressure_impact_recommendation": recommendation,
        "TEXT:final_validation_conclusion": conclusion,
        "TEXT:model_training_description": model_training_report_text(
            results.algorithm,
            results.basic_info.hyperparameters,
        ),
    }


def _effectiveness_metric_sentence(overall: list) -> str:
    by_split = {row.split: row for row in overall}
    parts: list[str] = []
    for split, label in (("train", "Train"), ("test", "Test"), ("oot", "OOT")):
        row = by_split.get(split)
        if row is None:
            continue
        parts.append(
            f"{label} KS {row.ks:.4f},AUC {row.auc:.4f},PSI {row.psi_vs_train:.4f}"
        )
    return ";".join(parts) if parts else "KS/AUC/PSI Data Missing"


def _oot_stability_sentence(oot) -> str:
    if oot is None:
        return "Insufficient evidence of external stability of samples"
    psi = float(oot.psi_vs_train)
    if psi < 0.10:
        return f"Exterior stability acceptable (OOT PSI {psi:.4f})"
    if psi < 0.25:
        return f"Ex-sample stability requires attention (infra)OOT PSI {psi:.4f})"
    return f"Equivalent transport of samples (outside distribution)OOT PSI {psi:.4f})"


def _overfitting_sentence(overfitting: dict | None) -> str:
    if not isinstance(overfitting, dict):
        return "Insufficient evidence of completion of the inspection"
    status = str(overfitting.get("status") or "")
    relative_diff = overfitting.get("train_test_relative_diff")
    abs_diff = overfitting.get("train_oot_abs_diff")
    relative_text = (
        f"{relative_diff:.2%}"
        if isinstance(relative_diff, (int, float))
        else "Unknown"
    )
    abs_text = (
        f"{abs_diff:.4f}"
        if isinstance(abs_diff, (int, float))
        else "Unknown"
    )
    if status == "fail":
        return (
            f"!!No pass of the proposed inspection (intrain-test Relatively bad{relative_text},"
            f"train-OOT Absolutely not.{abs_text})!!,There is a risk of a reduction in the desired or external effects of the sample"
        )
    if status == "pass":
        return "The government has been working on the issue of the (Face of the Nation) and has been working on the issue.train/test/OOT Distinguishing capacity gaps within thresholds"
    return "Insufficient evidence of completion of the inspection"


_LIFT_STRENGTH_LABELS = {
    "fail": "Not achieved",
    "weak": "Weakness",
    "ok": "Jean-Claude.",
    "strong": "Better.",
    "unknown": "Insufficient evidence",
}
_MONOTONICITY_LABELS = {
    "monotonic": "Overdue rates are largely monotonous",
    "mostly_monotonic": "Overdue rates are largely monotonous",
    "broken": "There's multiple overhangs on the overdue rate.",
    "unknown": "There's not enough evidence for monophonics.",
}


def _mark_fail_phrase(text: str, *, fail: bool) -> str:
    return f"!!{text}!!" if fail else text


def _binning_sentence(results) -> str:
    ranking = assess_lift_ranking(_effectiveness_payload_for_lift(results))
    oot = next(
        (item for item in ranking.get("splits") or [] if item.get("split") == "oot"),
        None,
    )
    if not isinstance(oot, dict):
        return "The breakdown of the boxes is detailed and structured."
    bins = oot.get("independent_quantile") or oot.get("train_aligned") or {}
    if not isinstance(bins, dict):
        bins = {}
    head_value = oot.get("head_lift_5pct")
    tail_value = oot.get("tail_lift_5pct")
    head_strength = str(oot.get("head_5pct_strength") or "unknown")
    tail_strength = str(oot.get("tail_5pct_strength") or "unknown")
    if head_value is None:
        head_value = bins.get("head_group_lift")
        head_strength = str(bins.get("head_group_strength") or head_strength)
    if tail_value is None:
        tail_value = bins.get("tail_group_lift")
        tail_strength = str(bins.get("tail_group_strength") or tail_strength)
    if head_value is None and tail_value is None:
        return "The breakdown of the boxes is detailed and structured."
    kind = "Independent 10-centre semibox" if oot.get("independent_quantile") else "Box"
    head_text = (
        f"Headlift {head_value:.2f}({_LIFT_STRENGTH_LABELS.get(head_strength, 'Insufficient evidence')})"
        if isinstance(head_value, (int, float))
        else "Headlift Missing"
    )
    tail_text = (
        f"Endlift {tail_value:.2f}({_LIFT_STRENGTH_LABELS.get(tail_strength, 'Insufficient evidence')})"
        if isinstance(tail_value, (int, float))
        else "Endlift Missing"
    )
    monotonicity = str(bins.get("bad_rate_monotonicity") or "unknown")
    mono_text = _MONOTONICITY_LABELS.get(monotonicity, "There's not enough evidence for monophonics.")
    return (
        f"OOT {kind}"
        f"{_mark_fail_phrase(head_text, fail=head_strength in {'fail', 'weak'})},"
        f"{_mark_fail_phrase(tail_text, fail=tail_strength in {'fail', 'weak'})},"
        f"{_mark_fail_phrase(mono_text, fail=monotonicity == 'broken')}"
    )


def _effectiveness_payload_for_lift(results) -> dict:
    def tables(payload: object) -> dict[str, list[dict[str, object]]]:
        if not isinstance(payload, dict):
            return {}
        converted: dict[str, list[dict[str, object]]] = {}
        for split, rows in payload.items():
            converted[str(split)] = [
                {
                    "lift": getattr(row, "lift", None),
                    "bad_rate": getattr(row, "bad_rate", None),
                }
                for row in rows or []
            ]
        return converted

    return {
        "overall": [
            {
                "split": row.split,
                "head_lift_5pct": row.head_lift_5pct,
                "tail_lift_5pct": row.tail_lift_5pct,
            }
            for row in results.effectiveness.overall
        ],
        "bin_tables": tables(results.effectiveness.bin_tables),
        "independent_quantile_bin_tables": tables(
            results.effectiveness.independent_quantile_bin_tables
        ),
    }


def _client(model_profile: dict) -> OpenAICompatibleLLMClient:
    return OpenAICompatibleLLMClient(model_profile)


def _stage_prompt(
    *,
    task: TaskRecord,
    stage: str,
    evidence: dict,
    memory_context: dict | None = None,
    user_instruction: str | None = None,
) -> str:
    instructions = _stage_instructions(
        stage,
        validation_workflow_version=task.validation_workflow_version,
    )
    payload = {
        "stage": stage,
        "task": _llm_task_meta(task),
        "evidence": _sanitize_llm_payload(
            _stage_scoped_evidence(
                stage,
                evidence,
                validation_workflow_version=task.validation_workflow_version,
            ),
            task,
        ),
        "instructions": instructions,
    }
    if user_instruction:
        payload["user_instruction"] = _sanitize_llm_text(user_instruction, task)
        payload["instructions"] = (
            instructions
            + "This is a user request to recreate the content of this phase, which must be met as a matter of priorityuser_instruction in which the requirements for change are included;"
            "The old wording should not be repeated because of the existence of the old draft."
        )
    if stage == "word_conclusion_draft" and evidence.get("report_draft"):
        payload["instructions"] += (
            "evidence.report_draft.text_values The draft report is currently in storage but not yet confirmed."
            "It is used as the starting point for the revision to retain the business facts and the active clearing of fields for which the user has not requested the modification;"
            "According touser_instruction Modify the specified paragraph. The values in the draft are not evidence of the Platform ' s indicators,"
            "Indicators and judgement can still only be based on certainty."
        )
    payload = add_memory_to_prompt_payload(payload, memory_context)
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


def _stage_scoped_evidence(
    stage: str,
    evidence: dict,
    *,
    validation_workflow_version: int | None = None,
) -> dict:
    if not isinstance(evidence, dict):
        return evidence
    if stage == "scan":
        return _scan_stage_evidence(evidence)
    if stage == "reproducibility":
        if validation_workflow_version == 2:
            return _pmml_scoring_stage_evidence(evidence)
        return _reproducibility_stage_evidence(evidence)
    if stage == "metrics":
        return _metrics_stage_evidence(evidence)
    if stage == "word_conclusion_draft":
        return _word_conclusion_stage_evidence(
            evidence,
            validation_workflow_version=validation_workflow_version,
        )
    keys = STAGE_EVIDENCE_KEYS.get(stage)
    if not keys or not _looks_like_global_agent_evidence(evidence):
        return _slim_evidence_for_llm(evidence)
    return _slim_evidence_for_llm(
        {
            key: evidence.get(key)
            for key in keys
            if evidence.get(key) is not None
        }
    )


def _metrics_stage_evidence(evidence: dict) -> dict:
    if not _looks_like_global_agent_evidence(evidence):
        return _slim_evidence_for_llm(evidence)
    validation_results = evidence.get("validation_results")
    if not isinstance(validation_results, dict):
        return {"validation_results": validation_results}
    return {
        "validation_results": _compact_metrics_validation_results(
            {
                key: validation_results.get(key)
                for key in METRICS_VALIDATION_RESULT_KEYS
                if key in validation_results
            }
        )
    }


def _pmml_scoring_stage_evidence(evidence: dict) -> dict:
    validation_results = evidence.get("validation_results")
    scoring = _compact_pmml_scoring_evidence(
        evidence.get("pmml_scoring"),
        validation_results.get("pmml_scoring")
        if isinstance(validation_results, dict)
        else None,
    )
    return {"pmml_scoring": scoring}


def _reproducibility_stage_evidence(evidence: dict) -> dict:
    if not _looks_like_global_agent_evidence(evidence):
        return _slim_evidence_for_llm(evidence)
    validation_results = evidence.get("validation_results")
    scoped: dict[str, object] = {}

    notebook_steps = _compact_notebook_steps_for_reproducibility(
        evidence.get("notebook_steps")
    )
    if notebook_steps or "notebook_steps" in evidence:
        scoped["notebook_steps"] = notebook_steps

    notebook_failure = _compact_notebook_failure_evidence(
        evidence.get("notebook_steps")
    )
    if notebook_failure:
        scoped["notebook_failure"] = notebook_failure

    contract = _compact_contract_for_reproducibility(evidence.get("contract"))
    if contract or "contract" in evidence:
        scoped["contract"] = contract

    reproducibility = _compact_reproducibility_evidence(
        evidence.get("reproducibility"),
        validation_results.get("reproducibility") if isinstance(validation_results, dict) else None,
    )
    if reproducibility or "reproducibility" in evidence:
        scoped["reproducibility"] = reproducibility

    return scoped


def _compact_notebook_steps_for_reproducibility(steps: object) -> list[dict]:
    if isinstance(steps, dict):
        steps = steps.get("steps")
    if not isinstance(steps, list):
        return []
    compact = []
    for step in steps[:REPRODUCIBILITY_NOTEBOOK_STEP_LIMIT]:
        if not isinstance(step, dict):
            continue
        compact.append(
            {
                key: step.get(key)
                for key in (
                    "id",
                    "title",
                    "status",
                    "cell_count",
                    "elapsed_seconds",
                    "system",
                )
                if step.get(key) not in (None, "")
            }
        )
    return compact


def _compact_notebook_failure_evidence(notebook_steps: object) -> dict:
    if not isinstance(notebook_steps, dict):
        return {}
    cells = notebook_steps.get("cells")
    if not isinstance(cells, list):
        return {}
    steps_by_id = _notebook_steps_by_id(notebook_steps.get("steps"))
    failed_cells: list[dict] = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        if str(cell.get("status") or "").lower() != "failed":
            continue
        compact = {
            key: cell.get(key)
            for key in (
                "cell_index",
                "step_id",
                "exception_name",
                "exception_value",
                "traceback_preview",
            )
            if cell.get(key) not in (None, "")
        }
        step = steps_by_id.get(str(cell.get("step_id") or ""))
        if step:
            compact["step_title"] = step.get("title")
        source_preview = str(cell.get("source_preview") or "").strip()
        if source_preview:
            compact["source_preview"] = _truncate_llm_text(
                source_preview,
                NOTEBOOK_FAILURE_SOURCE_CHARS,
            )
        referenced_files = cell.get("referenced_files")
        if isinstance(referenced_files, list) and referenced_files:
            compact["referenced_files"] = [
                str(item)
                for item in referenced_files[:NOTEBOOK_FAILURE_FILE_LIMIT]
                if str(item).strip()
            ]
        access_lines = cell.get("file_access_lines")
        if isinstance(access_lines, list) and access_lines:
            compact["file_access_lines"] = [
                _truncate_llm_text(str(item), NOTEBOOK_FAILURE_SOURCE_CHARS)
                for item in access_lines[:NOTEBOOK_FAILURE_LINE_LIMIT]
                if str(item).strip()
            ]
        failed_cells.append(compact)
        if len(failed_cells) >= NOTEBOOK_FAILURE_CELL_LIMIT:
            break
    if not failed_cells:
        return {}
    return {
        "source": "notebook_execution_progress",
        "read_only": True,
        "failed_cells": failed_cells,
        "interpretation_rule": (
            "Answer!Notebook Missing or Failedcell Use priority when it's a problem.failed_cells Medium"
            "source_preview,referenced_files andfile_access_lines;Do not guess based only on the wrong text."
        ),
    }


def _notebook_steps_by_id(steps: object) -> dict[str, dict]:
    if not isinstance(steps, list):
        return {}
    return {
        str(step.get("id") or ""): step
        for step in steps
        if isinstance(step, dict) and step.get("id")
    }


def _compact_contract_for_reproducibility(contract: object) -> dict:
    if not isinstance(contract, dict):
        return {}
    compact = {
        key: contract.get(key)
        for key in (
            "algorithm",
            "target_col",
            "score_col",
            "split_col",
            "time_col",
            "pmml_output_field",
            "score_decimal_places",
        )
        if contract.get(key) not in (None, "")
    }
    feature_columns = contract.get("feature_columns")
    if isinstance(feature_columns, list):
        compact["feature_count"] = len(feature_columns)
        compact["feature_columns_sample"] = feature_columns[
            :REPRODUCIBILITY_CONTRACT_FEATURE_LIMIT
        ]
    return compact


def _slim_evidence_for_llm(evidence: dict) -> dict:
    if not isinstance(evidence, dict):
        return evidence
    slim = dict(evidence)
    validation_results = slim.get("validation_results")
    if isinstance(validation_results, dict):
        slim["validation_results"] = _slim_validation_results_for_llm(validation_results)
    return slim


def _word_conclusion_stage_evidence(
    evidence: dict,
    *,
    validation_workflow_version: int | None = None,
) -> dict:
    if not _looks_like_global_agent_evidence(evidence):
        return _slim_evidence_for_llm(evidence)
    validation_results = evidence.get("validation_results")
    scoped: dict[str, object] = {}

    scan = _compact_scan_evidence(evidence.get("scan"))
    if scan:
        scoped["scan"] = scan

    pmml_scoring = _compact_pmml_scoring_evidence(
        evidence.get("pmml_scoring"),
        validation_results.get("pmml_scoring")
        if isinstance(validation_results, dict)
        else None,
    )
    if pmml_scoring:
        scoped["pmml_scoring"] = pmml_scoring

    if validation_workflow_version != 2:
        reproducibility = _compact_reproducibility_evidence(
            evidence.get("reproducibility"),
            validation_results.get("reproducibility")
            if isinstance(validation_results, dict)
            else None,
        )
        if reproducibility:
            scoped["reproducibility"] = reproducibility

    compact_validation = _compact_word_validation_results(
        validation_results,
        validation_workflow_version=validation_workflow_version,
    )
    if compact_validation:
        scoped["validation_results"] = compact_validation

    report_fields = evidence.get("report_fields")
    if report_fields is not None:
        scoped["report_fields"] = report_fields
    report_draft = evidence.get("report_draft")
    if isinstance(report_draft, dict):
        scoped["report_draft"] = report_draft

    visible_summaries = _compact_visible_stage_summaries(
        evidence.get("visible_stage_summaries")
    )
    if visible_summaries:
        scoped["visible_stage_summaries"] = visible_summaries

    return scoped


def _compact_scan_evidence(scan: object) -> dict:
    if not isinstance(scan, dict):
        return {}
    checks = scan.get("checks")
    if not isinstance(checks, list):
        checks = []
    compact_checks = []
    for check in checks[:20]:
        if not isinstance(check, dict):
            continue
        compact_checks.append(
            {
                key: check.get(key)
                for key in ("id", "label", "status", "message")
                if check.get(key) not in (None, "")
            }
        )
    compact = {
        "checks": compact_checks,
        "scan_interpretation": _scan_interpretation(compact_checks),
    }
    notebook_contract = _compact_notebook_contract_evidence(
        scan.get("notebook_contract")
    )
    if notebook_contract:
        compact["notebook_contract"] = notebook_contract
    return compact


def _compact_notebook_contract_evidence(contract: object) -> dict:
    if not isinstance(contract, dict):
        return {}
    compact = {
        key: contract.get(key)
        for key in (
            "read_only",
            "source",
            "sample_df_defined",
            "score_fn_defined",
            "target_col_defined",
            "algorithm_defined",
            "target_col",
            "algorithm",
            "algorithm_raw",
            "algorithm_source",
            "algorithm_valid",
            "algorithm_error",
            "error",
        )
        if contract.get(key) not in (None, "")
    }
    for key in ("missing_names", "invalid_names", "contract_cell_indexes"):
        value = contract.get(key)
        if isinstance(value, list) and value:
            compact[key] = value[:20]
    previews = contract.get("source_previews")
    if isinstance(previews, list) and previews:
        compact["source_previews"] = [
            _truncate_llm_text(str(preview), NOTEBOOK_CONTRACT_SOURCE_PREVIEW_CHARS)
            for preview in previews[:NOTEBOOK_CONTRACT_SOURCE_PREVIEW_LIMIT]
            if str(preview).strip()
        ]
    return compact


def _compact_reproducibility_evidence(*candidates: object) -> dict:
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        compact = {
            key: candidate.get(key)
            for key in ("summary", "sample_size", "seed")
            if candidate.get(key) is not None
        }
        if compact:
            return compact
    return {}


def _compact_pmml_scoring_evidence(*candidates: object) -> dict:
    fields = (
        "schema_version",
        "engine",
        "engine_version",
        "output_field",
        "input_row_count",
        "success_count",
        "failure_count",
        "null_count",
        "non_finite_count",
        "elapsed_seconds",
        "rows_per_second",
        "chunk_size",
        "required_input_count",
        "missing_inputs",
        "status",
        "bounded_errors",
    )
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        compact = {
            key: candidate.get(key)
            for key in fields
            if candidate.get(key) is not None
        }
        if compact:
            return compact
    return {}


def _compact_word_validation_results(
    validation_results: object,
    *,
    validation_workflow_version: int | None = None,
) -> dict:
    if not isinstance(validation_results, dict):
        return {}
    slim = _slim_validation_results_for_llm(validation_results)
    compact: dict[str, object] = {}
    for key in ("model_name", "model_version", "algorithm", "target_type"):
        if slim.get(key) is not None:
            compact[key] = slim.get(key)

    basic_info = _compact_basic_info_for_word(slim.get("basic_info"))
    if basic_info:
        compact["basic_info"] = basic_info

    if validation_workflow_version != 2:
        reproducibility = _compact_reproducibility_evidence(
            slim.get("reproducibility")
        )
        if reproducibility:
            compact["reproducibility"] = reproducibility

    pmml_scoring = _compact_pmml_scoring_evidence(slim.get("pmml_scoring"))
    if pmml_scoring:
        compact["pmml_scoring"] = pmml_scoring

    raw_effectiveness = slim.get("effectiveness")
    effectiveness = _compact_effectiveness_for_word(raw_effectiveness)
    if isinstance(raw_effectiveness, dict):
        ranking = assess_lift_ranking(raw_effectiveness)
        if ranking["splits"]:
            effectiveness["lift_ranking_assessment"] = ranking
    if effectiveness:
        compact["effectiveness"] = effectiveness

    overfitting = slim.get("overfitting_check")
    if isinstance(overfitting, dict):
        compact["overfitting_check"] = dict(overfitting)

    stress_test = _compact_stress_test_for_word(slim.get("stress_test"))
    if stress_test:
        compact["stress_test"] = stress_test
    return compact


def _compact_basic_info_for_word(basic_info: object) -> dict:
    if not isinstance(basic_info, dict):
        return {}
    compact: dict[str, object] = {}
    for key in ("sample_period", "split_summary", "monthly_distribution"):
        value = basic_info.get(key)
        if isinstance(value, list):
            compact[key] = _tail_list(value, WORD_CONCLUSION_MONTHLY_LIMIT)
        elif value is not None:
            compact[key] = value
    feature_importance = basic_info.get("feature_importance")
    if isinstance(feature_importance, list):
        compact["feature_importance"] = feature_importance[:WORD_CONCLUSION_FEATURE_LIMIT]
    hyperparameters = basic_info.get("hyperparameters")
    if isinstance(hyperparameters, dict) and hyperparameters:
        compact["hyperparameters"] = dict(list(hyperparameters.items())[:50])
    return compact


def _compact_effectiveness_for_word(effectiveness: object) -> dict:
    if not isinstance(effectiveness, dict):
        return {}
    compact: dict[str, object] = {}
    for key in ("overall", "monthly_ks", "monthly_psi", "psi_stability_table"):
        value = effectiveness.get(key)
        if not isinstance(value, list):
            if value is not None:
                compact[key] = value
            continue
        if key in {"monthly_ks", "monthly_psi"}:
            compact[key] = _tail_list(value, WORD_CONCLUSION_MONTHLY_LIMIT)
        elif key == "psi_stability_table":
            compact[key] = value[:WORD_CONCLUSION_PSI_BIN_LIMIT]
        else:
            compact[key] = value
    return compact


def _compact_stress_test_for_word(stress_test: object) -> dict:
    if not isinstance(stress_test, dict):
        return {}
    compact: dict[str, object] = {}
    baseline = stress_test.get("baseline")
    if isinstance(baseline, dict):
        compact["baseline"] = {
            key: value
            for key, value in baseline.items()
            if key != "bin_table"
        }
    elif baseline is not None:
        compact["baseline"] = baseline
    per_category = stress_test.get("per_category")
    if isinstance(per_category, list):
        compact["per_category"] = [
            _compact_stress_category(item)
            for item in per_category[:WORD_CONCLUSION_STRESS_CATEGORY_LIMIT]
            if isinstance(item, dict)
        ]
    if stress_test.get("status") is not None:
        compact["status"] = stress_test.get("status")
    return compact


def _compact_stress_category(category: dict) -> dict:
    compact = {
        key: value
        for key, value in category.items()
        if key != "bin_table"
    }
    dropped = compact.get("dropped_features")
    if isinstance(dropped, list):
        compact["dropped_features"] = dropped[:WORD_CONCLUSION_FEATURE_LIMIT]
    return compact


def _compact_visible_stage_summaries(summaries: object) -> list[dict]:
    if not isinstance(summaries, list):
        return []
    compact = []
    for item in summaries[-WORD_CONCLUSION_VISIBLE_SUMMARY_LIMIT:]:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content") or "")
        compact.append(
            {
                "stage": str(item.get("stage") or ""),
                "content": _truncate_llm_text(
                    content,
                    WORD_CONCLUSION_VISIBLE_SUMMARY_CHARS,
                ),
            }
        )
    return compact


def _tail_list(value: list, limit: int) -> list:
    if len(value) <= limit:
        return value
    return value[-limit:]


def _slim_validation_results_for_llm(validation_results: dict) -> dict:
    if not isinstance(validation_results, dict):
        return validation_results
    slim = dict(validation_results)
    effectiveness = slim.get("effectiveness")
    if isinstance(effectiveness, dict):
        slim["effectiveness"] = {
            key: value
            for key, value in effectiveness.items()
            if key not in OVERSIZED_EFFECTIVENESS_KEYS
        }
    return slim


def _compact_metrics_validation_results(validation_results: dict) -> dict:
    if not isinstance(validation_results, dict):
        return validation_results
    compact: dict[str, object] = {
        key: validation_results.get(key)
        for key in ("model_name", "model_version", "algorithm", "target_type")
        if validation_results.get(key) is not None
    }
    raw_basic_info = validation_results.get("basic_info")
    basic_info = _compact_basic_info_for_word(raw_basic_info)
    if basic_info:
        compact["basic_info"] = basic_info

    effectiveness = _compact_effectiveness_for_word(
        validation_results.get("effectiveness")
    )
    raw_effectiveness = validation_results.get("effectiveness")
    if isinstance(raw_effectiveness, dict):
        for table_key in ("bin_tables", "independent_quantile_bin_tables"):
            tables = raw_effectiveness.get(table_key)
            if isinstance(tables, dict):
                effectiveness[table_key] = {
                    str(split): rows[:METRICS_BIN_TABLE_LIMIT]
                    for split, rows in tables.items()
                    if isinstance(rows, list)
                }
        ranking = assess_lift_ranking(raw_effectiveness)
        if ranking["splits"]:
            effectiveness["lift_ranking_assessment"] = ranking
    if effectiveness:
        compact["effectiveness"] = effectiveness

    overfitting = validation_results.get("overfitting_check")
    if isinstance(overfitting, dict):
        compact["overfitting_check"] = dict(overfitting)

    stress_test = _compact_stress_test_for_word(
        validation_results.get("stress_test")
    )
    raw_stress_test = validation_results.get("stress_test")
    if stress_test and isinstance(raw_stress_test, dict):
        source_counts = raw_stress_test.get("category_source_counts")
        if isinstance(source_counts, dict):
            stress_test["category_source_counts"] = dict(source_counts)
        unclassified = raw_stress_test.get("unclassified_features")
        if isinstance(unclassified, list):
            stress_test["unclassified_feature_count"] = len(unclassified)
            stress_test["unclassified_features_sample"] = unclassified[
                :WORD_CONCLUSION_FEATURE_LIMIT
            ]
    if stress_test:
        compact["stress_test"] = stress_test
    return compact


def _scan_stage_evidence(evidence: dict) -> dict:
    scoped = dict(evidence)
    checks = scoped.get("checks")
    if not isinstance(checks, list) and isinstance(scoped.get("scan"), dict):
        checks = scoped["scan"].get("checks")
        notebook_contract = _compact_notebook_contract_evidence(
            scoped["scan"].get("notebook_contract")
        )
        if notebook_contract:
            scoped["scan"] = {**scoped["scan"], "notebook_contract": notebook_contract}
    else:
        notebook_contract = _compact_notebook_contract_evidence(
            scoped.get("notebook_contract")
        )
        if notebook_contract:
            scoped["notebook_contract"] = notebook_contract
    scoped["scan_interpretation"] = _scan_interpretation(
        checks if isinstance(checks, list) else []
    )
    return scoped


def _scan_interpretation(checks: list[dict]) -> dict:
    checks_by_label = {
        str(check.get("label") or check.get("name") or ""): check
        for check in checks
        if isinstance(check, dict)
    }
    detected: list[str] = []
    missing: list[str] = []
    for label in SCAN_REQUIRED_CHECK_LABELS:
        check = checks_by_label.get(label)
        if check and _scan_check_passed(check):
            detected.append(label)
        else:
            missing.append(label)
    return {
        "required_materials": list(SCAN_REQUIRED_CHECK_LABELS),
        "detected_required_materials": detected,
        "missing_required_materials": missing,
        "required_materials_complete": not missing,
        "not_required_in_scan_stage": [
            "pickle/pkl Model",
            "Verify the results between the sample and the rating output",
            "KS/PSI/AUC Effort of impact indicators",
        ],
        "interpretation_rule": (
            "checks Mediumsuccess/passed/By indicating that the counterpart material or contract has been met,"
            "No further description of the situation as missing.pickle/pkl,Rating Output andKS/PSI/AUC It is an optional material or a follow-up phase result,"
            "Required input not in the material scanning phase."
        ),
    }


def _scan_check_passed(check: dict) -> bool:
    status = str(check.get("status") or "").strip().lower()
    message = str(check.get("message") or "")
    return (
        status in SCAN_SUCCESS_STATUSES
        or message.startswith("Recognized")
        or message.startswith("Defined")
    )


def _guard_stage_summary(
    *,
    task: TaskRecord,
    stage: str,
    evidence: dict,
    content: str,
    fallback: str,
) -> str:
    if (
        stage == "reproducibility"
        and task.validation_workflow_version == 2
        and _V2_PMML_SCORING_LEGACY_PATTERN.search(content)
    ):
        return fallback
    if stage != "scan" or not isinstance(evidence, dict):
        return content
    interpretation = _scan_stage_evidence(evidence).get("scan_interpretation", {})
    if not interpretation.get("required_materials_complete"):
        return content
    if not _scan_summary_claims_missing_complete_materials(content):
        return content
    return (
        "The material completion check is complete.Notebook,Sample data,PMML Models, data dictionary and"
        "Notebook RMC The contract has been adopted; no missing essential materials are currently being identified."
    )


def _scan_summary_claims_missing_complete_materials(content: str) -> bool:
    text = str(content or "")
    if not text:
        return False
    if re.search(r"(Not found|None).{0,12}(Missing|Missing|Lack)", text):
        return False
    return bool(
        re.search(
            r"Missing|Lack|Not provided|No, I'm not.|Not recognized|Not detected|Unchecked|Suggested addition|Supplementary.{0,12}(Documentation|Materials|Output|Result)|Missing",
            text,
            flags=re.IGNORECASE,
        )
    )


def _looks_like_global_agent_evidence(evidence: dict) -> bool:
    return any(key in evidence for key in GLOBAL_AGENT_EVIDENCE_KEYS)


def _chat_prompt(
    *,
    task: TaskRecord,
    user_message: str,
    conversation: list[dict],
    evidence: dict,
    memory_context: dict | None = None,
) -> str:
    conversation_memory = _conversation_memory(
        conversation=conversation,
        task=task,
        current_user_message=user_message,
    )
    payload = {
            "stage": "chat",
            "task": _llm_task_meta(task),
            "user_message": _sanitize_llm_text(user_message, task),
            "conversation_memory": conversation_memory,
            "available_evidence": _sanitize_llm_payload(
                _chat_evidence_for_llm(evidence), task
            ),
            "instructions": _chat_instructions(user_message),
        }
    payload = add_memory_to_prompt_payload(payload, memory_context)
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


def _conversation_memory(
    *,
    conversation: list[dict],
    task: TaskRecord,
    current_user_message: str,
) -> dict:
    messages = _conversation_memory_messages(conversation, task)
    previous_messages = messages
    if messages and messages[-1]["role"] == "user" and messages[-1]["content"] == _sanitize_llm_text(
        current_user_message, task
    ):
        previous_messages = messages[:-1]
    previous_user_question = _last_message_content(previous_messages, role="user")
    previous_assistant_answer = _last_message_content(previous_messages, role="assistant")
    kept_messages, omitted_count = _fit_conversation_memory(messages)
    return {
        "scope": "same_agent_task",
        "description": "User problems in the same authentication task,Agent Response and phase-out history for subsequent follow-up.",
        "messages": kept_messages,
        "omitted_message_count": omitted_count,
        "previous_user_question": previous_user_question,
        "previous_assistant_answer": previous_assistant_answer,
        "follow_up_guidance": (
            "If Currentuser_message It's a omission of the main language, a previous round or a question of what the effect is./Why?/The blogger says:"
            "We must give priority to theprevious_user_question andprevious_assistant_answer The issue of completion of the theme,"
            "Do not extend to unrelated certification stages or to generalization into a whole certification analysis."
        ),
    }


def _conversation_memory_messages(conversation: list[dict], task: TaskRecord) -> list[dict]:
    messages = []
    current_draft = latest_report_draft_context(conversation)
    for message in conversation:
        content = str(message.get("content") or "")
        if current_draft and message.get("id") == current_draft["message_id"]:
            content = json.dumps(current_draft["text_values"], ensure_ascii=False)
        content = _truncate_llm_text(
            _sanitize_llm_text(content, task),
            CONVERSATION_MEMORY_MESSAGE_MAX_CHARS,
        )
        if not content:
            continue
        messages.append(
            {
                "role": str(message.get("role") or ""),
                "stage": str(message.get("stage") or ""),
                "content": content,
            }
        )
    return messages


def _fit_conversation_memory(messages: list[dict]) -> tuple[list[dict], int]:
    kept: list[dict] = []
    total_chars = 0
    for message in reversed(messages):
        content_length = len(message["content"])
        if kept and (
            len(kept) >= CONVERSATION_MEMORY_MAX_MESSAGES
            or total_chars + content_length > CONVERSATION_MEMORY_MAX_CHARS
        ):
            break
        kept.append(message)
        total_chars += content_length
    kept.reverse()
    return kept, max(0, len(messages) - len(kept))


def _chat_evidence_for_llm(evidence: dict) -> dict:
    if not isinstance(evidence, dict):
        return evidence
    if not _looks_like_global_agent_evidence(evidence):
        return _slim_evidence_for_llm(evidence)
    scoped = _word_conclusion_stage_evidence(evidence)
    notebook_failure = _compact_notebook_failure_evidence(
        evidence.get("notebook_steps")
    )
    if notebook_failure:
        scoped["notebook_failure"] = notebook_failure
    return scoped


def _last_message_content(messages: list[dict], *, role: str) -> str:
    for message in reversed(messages):
        if message["role"] == role and message["content"]:
            return message["content"]
    return ""


def _truncate_llm_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max(0, max_chars - 8)].rstrip() + "…[Interrupt]"


def _chat_instructions(user_message: str) -> str:
    instructions = (
        _llm_task_reference_instruction()
        + "If the user is just greeting, chilling or talking, it should respond naturally and briefly."
        "Do not give a fixed start password or process guide.conversation The user is clearly detached from the current model validation task in multiple consecutive rounds,"
        "You can be reminded, after a short answer, that it is primarily used to explain the results of the validation,PMML,Meaning of indicators and report conclusions."
        "If the question is,PMML,The process, the meaning of the indicator or the interpretation of the outcome of the current mission,"
        "Please verify that the credit style model is used to provide a clear explanation in Chinese; the evidence can be cited when citing the Platform evidence."
        "If you have no evidence, you can state it as a generic explanation."
        "Use Priorityavailable_evidence.validation_results,report_fields.metric_values,"
        "report_fields.text_values andvisible_stage_summaries Answer; the chart should be interpreted according to its underlying structured data,"
        "Don't pretend to see pixels directly."
        "available_evidence.report_draft.text_values The report is the report that the user currently has saved but not yet confirmed."
        "(a) To use it as a priority when discussing or revising the current draft, rather than using the old draft session as an updated version;"
        "Draft text cannot be overwrittenreport_fields.metric_values orvalidation_results Indicator of certainty."
        "If User AskNotebook,RMC Contract field orRMC_ALGORITHM Current value, priority"
        "available_evidence.scan.notebook_contract;The evidence is from the platform.Notebook The only static scan that reads is the one that shows the story."
        "Original filling values, NDAMs and causes of errors may be specified, but not claimed to have been modifiedNotebook,And don't ask the user to open it manually."
        "Notebook Other Organiserevidence field."
        "If User AskNotebook Failed to execute, missing which document, or some othercell Why are you making mistakes?"
        "available_evidence.notebook_failure.failed_cells Failed incell Source summary,referenced_files "
        "andfile_access_lines;Don't just say it.FileNotFoundError Text, task name, filename or historical experience guess."
        "In the same authentication taskconversation_memory is the memory of a session in the task.user_message It's a succession of questions."
        "Ignore the main language or only the implications/Reason/Keep saying it. It has to be done first.conversation_memory.previous_user_question "
        "andprevious_assistant_answer Completing theme; answers are about the theme of the previous round of user questions, not automatically extended"
        "It is not relevant to the certification phase or the overall certification conclusion."
        "If the answer relates toKS,PSI,AUC,Indicators such as stability or differentiated capabilities must be interpreted according to the following operational calibre and cannot be detached from the model scenario:"
        + RISK_METRIC_INTERPRETATION_GUIDANCE
    )
    if _is_greeting_message(user_message):
        instructions += "Currentuser_message It's a greeting or a chill, just say hi and say you can continue to answer."
    return instructions


def _llm_task_meta(task: TaskRecord) -> dict:
    status_message = task.status_message
    if status_message is not None:
        status_message = _sanitize_llm_text(status_message, task)
    return {
        "model_display_name": _model_display_name(task),
        "model_name": task.model_name or "Current Model",
        "model_version": task.model_version,
        "algorithm": task.algorithm,
        "status": task.status.value,
        "status_message": status_message,
    }


def _model_display_name(task: TaskRecord) -> str:
    name = task.model_name or "Current Model"
    version = str(task.model_version or "").strip()
    return f"{name}({version})" if version else name


def _llm_task_reference_instruction() -> str:
    return (
        "Use when current task or current model is involvedtask.model_display_name / The name of the model is called,"
        "Do not output, repeat or quote internal tasksID."
    )


def _sanitize_llm_payload(value: object, task: TaskRecord) -> object:
    if isinstance(value, str):
        return _sanitize_llm_text(value, task)
    if isinstance(value, list):
        return [_sanitize_llm_payload(item, task) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_llm_payload(item, task) for item in value]
    if isinstance(value, dict):
        # Only sanitize values, never keys. Keys are structural field names; a
        # key that happens to contain the task id should not be rewritten into a
        # display name (which would corrupt the payload schema seen by the LLM).
        return {
            key: _sanitize_llm_payload(item, task)
            for key, item in value.items()
        }
    return value


def _sanitize_llm_text(value: str, task: TaskRecord) -> str:
    task_id = str(task.id or "")
    if not task_id:
        return value
    return value.replace(task_id, _model_display_name(task))


def _stage_instructions(
    stage: str,
    *,
    validation_workflow_version: int | None = None,
) -> str:
    reference_instruction = _llm_task_reference_instruction()
    if stage == "agent_start":
        return (
            reference_instruction
            + "At most, two sentences. First, you will be able to start the mission as a credit-risk management expert."
            "It is further indicated that the material identification tool will be called for the next time; no identification is claimed."
        )
    if stage == "scan":
        return (
            reference_instruction
            + "For the current material completeness phase only, with a maximum of 2 sentences, indicating that the material is identified, missing orNotebook RMC Contract check status."
            "Ifevidence.scan.notebook_contract orevidence.notebook_contract There is."
            "It's only static scans on the platform.Notebook Summary of the compact, which can be used for illustrationRMC_ALGORITHM,"
            "RMC_TARGET_COL The original value of the phrase and the results of the consolidation; it cannot be claimed that these have been provided with evidence."
            "I must.evidence.scan_interpretation.required_materials_complete and"
            "missing_required_materials applicable;required_materials_complete=true The blog is also available."
            "It's just a sign.Notebook,Sample data,PMML Models, data dictionary andNotebook RMC The contract has been fulfilled."
            "Not to mention missing, undetected model files,PMML,pickle/pkl,Validate sample and rating output orKS/PSI/AUC The middle result is:"
            "Nor are these material which has been satisfied or not required to be added to the proposal."
            "pickle/pkl Not currently required for scanning;KS/PSI/AUC The results of the subsequent stabilization phase are calculated,"
            "Not an input file for the material scanning phase."
            "Do not analyze the points for consistency,AUC,KS,PSI,Pressure testing or final report findings."
        )
    if stage == "reproducibility":
        if validation_workflow_version == 2:
            return (
                reference_instruction
                + "Only for the currentPMML The scoring test phase is divided into (conclusions, rating coverage, anomalies, performance, recommendations)."
                "Use onlyevidence.pmml_scoring,Interpretationinput_row_count,success_count,failure_count,"
                "null_count,non_finite_count,missing_inputs,status,elapsed_seconds androws_per_second."
                "No claims of executionNotebook,Code Model Rating or Code Modelling andPMML (a) Consistency comparison of scores;"
                "No current or subsequent amendments may be recommendedNotebook Model execution, code model rating,"
                "Code Models andPMML (a) Validation of the points for consistency;"
                "Do not analyze material adequacy,AUC,KS,PSI,The following is a short box, monthly stability, model pressure test or report output, and the results of the study are available for consultation."
                "Do not give the overall validation conclusion."
            )
        return (
            reference_instruction
            + "Only for the current model 's replicability/The fractional consistency phase is divided into (conclusions, evidence, risk implications, recommendations)."
            "Use onlyevidence.reproducibility,contract andnotebook_steps The evidence in it."
            "Don't analyze the material. Don't analyze it.AUC,KS,PSI,The first of these is the case of a small group of people who are not able to use the data to support their own efforts."
            "Do not give the overall validation conclusion, nor output the entire validation working floor structure."
        )
    if stage == "metrics":
        return (
            reference_instruction
            + "For the current phase of effects and stability only, it is divided into (overall judgement, performance of effects, performance of stability, pressure test risk, recommendations)."
            "The depth of the analysis of the performance of effects must be consistent with the stability of performance and stress test risk: not just writtenKS/AUC Number orlift Whether to cross one."
            "It has to be combined.evidence.validation_results.effectiveness.lift_ranking_assessment "
            "5 per cent at the end of the evaluationlift Range, box-by-box overdue rate/Single grouplift Whether to single-hub and end-of-pipe distinctions are drawn;"
            "Head 0.99 It shall be judged as weak and shall not be adopted, although it is less than 1."
            "Unadopted, misaligned, weaklift,The box is in reverse.PSI≥0.25,The government has been working with the government to improve the quality of the data."
            "It has to be used.!!Key phrases!! Wrap (single phrases only) not to be used in passages!! !!."
            "Ifcross_task_memory It's a model of the same kind. It has to compare history.KS/AUC/PSI(And the match, the end.lift I am not a good friend of mine."
            "The general judgement is that no comparable historical model is available, and that no comparison is made."
            "Pressure test risks must be fully covered./Medium/Low risk layer or clear evidence of insufficient evidence and a full conclusion in a sentence;"
            "No stopover in half sentence, bullet in the project or only \"KS The decrease is not complete, etc."
            "Do not review the process of implementation of material completeness or consistency of scores and do not produce consolidated conclusions for the final report."
            "ExplanationKS,PSI,AUC,Stability or distinction of capabilities must be judged by the following operational calibre and cannot be detached from the model scenario:"
            + RISK_METRIC_INTERPRETATION_GUIDANCE
        )
    if stage == "report":
        return (
            reference_instruction
            + "Only for the current reporting output phase, with a maximum of 2 sentences, indicates the status of the product generated, previewed or downloaded."
            "Do not re-analyse material completeness, fraction consistency or impact stability indicators."
        )
    if stage == "word_conclusion_draft":
        if validation_workflow_version == 2:
            return (
                reference_instruction
                + "Generate finalWord The three paragraphs of the report are the only language to be used.evidence given inPMML Rating, scoring."
                "Impact and stability indicators, model pressure test layers and phase summaries; not to be compiledKS,AUC,PSI,Sample volume,"
                "Data source name or regulatory conclusion, and may not claim to have been enforcedNotebook,A comparison of the score or score scores of the code model."
                "The output must beJSON object, which must contain:"
                "TEXT:pressure_test_summary,TEXT:pressure_impact_recommendation,"
                "TEXT:final_validation_conclusion,TEXT:model_training_description."
                "TEXT:pressure_test_summary The purpose of the model pressure test must be specified,"
                "Methods and observed high/Medium/Low-risk data source or feature category layer, with baseline definedKS Dismissed from categoriesKS/PSI;"
                "\"and not just repeat.\"-9999]Mechanical list. When insufficient evidence is available, it is clear that a layer cannot be completed."
                "TEXT:model_training_description Must introduce the actual algorithm of this model and quote"
                "evidence.validation_results.basic_info.hyperparameters Key parameters"
                "(Likemax_depth,learning_rate,num_boost_round/best_iteration);"
                "The introduction to the generic textbook of the algorithm must not be simply pasted, nor may it be written in case of supersensory evidence to be confirmed."
                "TEXT:pressure_impact_recommendation The above risk hierarchy must be monitored, replaced, downgraded,"
                "Manual review or access restriction recommendations.TEXT:final_validation_conclusion The project will be a major event in the world, and will be a major event in the world."
                "WritingTrain/Test/OOT It's...KS,AUC,PSI,The government has also been able to provide a comprehensive assessment of the impact of the project on the environment and evaluate stability, alignment, pressure testing and the sorting of boxes;"
                "Boxes andlift Requiredlift_ranking_assessment:The idea of a single-tune, end-end range and distinction is to see if it is being pulled apart."
                "It's not just becauselift Crosses 1. Use a phrase that is either unworked or clearly not good!! !! Pack it."
                "The same set of words should not be used.cross_task_memory A comparison of historical models with restraint is required;"
                "The reference must be restrained and the platform indicators must not be rewritten."
                "TEXT:final_validation_conclusion The government has been able to provide the necessary information to the public."
                "Recommendations 1 to 2 natural segments, with direct evaluation of distinction effects, external stability, risk overload,"
                "Model pressure tests for key findings and final prudential judgement; maximum one short sentencePMML The deployment is available,"
                "It shall not be written that it is either deployable or operational."
                "No restatement of material scanning, material completeness, validation of input contracts,PMML Rating sample size or time-consuming,"
                "Information on the process of the Platform ' s implementation steps, reporting on the status of outputs, the finalization phase, the pre-natal review arrangements, etc.;"
                "Ifevidence.visible_stage_summaries Model effects are interpreted with stability and the elements of model evaluation must be incorporated;"
                "PMML The evidence is used to determine whether it can be expressed briefly asPMML Deployment is available."
            )
        return (
            reference_instruction
            + "Generate finalWord The three paragraphs of the report are the only language to be used.evidence the structural indicators,"
            "Recurring conclusions, pressure test layers and phase summaries; not fabricatedKS,AUC,PSI,Sample volume,"
            "Data source name or regulatory conclusion. Output must beJSON object, which must contain:"
            "TEXT:pressure_test_summary,TEXT:pressure_impact_recommendation,"
            "TEXT:final_validation_conclusion,TEXT:model_training_description."
            "TEXT:pressure_test_summary The purpose, method and observed height of the pressure test must be specified/Medium/Low-risk data source layers;"
            "The list of machines should not be repeated."
            "TEXT:model_training_description The model must be presented in practical terms and must quote the training superb that has been given."
            "The introduction of general textbooks must not be exported."
            "TEXT:pressure_impact_recommendation The above risk hierarchy must be monitored, replaced, downgraded,"
            "Manual review or access restriction recommendations.TEXT:final_validation_conclusion The government has been able to provide the necessary information to the public."
            "Recommendation 1 to 2 natural segments covering development processes or material completeness,Notebook Recoverability, consistency of scores,"
            "Distinguishing effects, stability, stress tests, reporting output status and final prudential judgement;"
            "Ifevidence.visible_stage_summaries The replicative or effect-stabilizing interpretation has already been made, and the elements must be incorporated,"
            "It cannot be reduced to a general conclusion."
        )
    if stage == "failure":
        return (
            reference_instruction
            + "It is divided into (failure phase, direct cause, possible cause, next step).evidence.notebook_failure There is."
            "It must be based on the failure of the people.cell Source summary,referenced_files andfile_access_lines JudgementNotebook "
            "Which documents were actually cited; not only the error text should be used as a basis for speculation, nor should the name of the task or model be misconceived as missing."
        )
    return reference_instruction + "Generate prudent, professional, evidence-based statements in Chinese."


def _parse_conclusion_json(content: str) -> dict[str, str]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM Return is not validJSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("word conclusion response must be a JSON object")
    values = {
        key: str(payload.get(key) or "").strip()
        for key in REQUIRED_AGENT_REPORT_KEYS
    }
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise ValueError("word conclusion response missing keys: " + ", ".join(missing))
    for key in AGENT_REPORT_WRITABLE_KEYS - AGENT_REPORT_CONCLUSION_KEYS:
        extra = str(payload.get(key) or "").strip()
        if extra:
            values[key] = extra
    return values


def _with_narrative_report_seeds(task: TaskRecord, values: dict[str, str]) -> dict[str, str]:
    merged = dict(values)
    for key, seed in narrative_report_values(task.model_name).items():
        if not str(merged.get(key) or "").strip():
            merged[key] = seed
    return merged


def _with_training_description_seed(
    task: TaskRecord,
    values: dict[str, str],
    evidence: dict | None = None,
) -> dict[str, str]:
    merged = dict(values)
    current = merged.get("TEXT:model_training_description")
    if not is_platform_default_training_description(current, task.algorithm):
        return merged
    seeded = _training_description_from_evidence(task, evidence)
    if seeded:
        merged["TEXT:model_training_description"] = seeded
    return merged


def _training_description_from_evidence(
    task: TaskRecord,
    evidence: dict | None,
) -> str:
    algorithm = str(task.algorithm or "").strip()
    hyperparameters = None
    if isinstance(evidence, dict):
        raw_results = evidence.get("validation_results")
        if isinstance(raw_results, dict):
            algorithm = str(raw_results.get("algorithm") or algorithm).strip()
            basic_info = raw_results.get("basic_info")
            if isinstance(basic_info, dict) and isinstance(basic_info.get("hyperparameters"), dict):
                hyperparameters = basic_info.get("hyperparameters")
    if not algorithm:
        return ""
    try:
        return model_training_report_text(algorithm, hyperparameters)
    except ValueError:
        return ""


def _validate_v2_word_conclusions(values: dict[str, str]) -> None:
    conclusion = values.get("TEXT:final_validation_conclusion", "")
    for pattern in _V2_FINAL_CONCLUSION_FORBIDDEN_PATTERNS:
        if pattern.search(conclusion):
            raise ValueError(
                "V2 final validation conclusion contains forbidden process narration"
            )
