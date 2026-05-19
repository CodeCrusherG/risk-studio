"""refinement_report request-compiler handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
from collections.abc import Sequence
import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import StandardWorkflowRequestDraft
    from . import StrategyRequestCompilation
    from . import _POOL_MUTATION_WORKFLOWS
    from . import _REFINEMENT_MERGE_ACTION_RE
    from . import _REFINEMENT_SELECTION_ACTION_RE
    from . import _STRATEGY_POOL_APPLY_WORKFLOWS
    from . import _STRATEGY_POOL_MATERIALIZE_WORKFLOWS
    from . import _STRATEGY_POOL_MEASUREMENT_WORKFLOWS
    from . import _STRATEGY_POOL_VALIDATION_WORKFLOWS
    from . import _STRATEGY_POOL_WORKFLOWS
    from . import _clarification
    from . import _explicit_manual_breakpoint_bindings
    from . import _ground_automatic_tree_apply
    from . import _ground_automatic_tree_candidate_build
    from . import _ground_automatic_tree_leaf_materialization
    from . import _ground_candidate_monthly_stability_request
    from . import _ground_cross_matrix_analysis
    from . import _ground_cross_matrix_candidate_build_from_search
    from . import _ground_cross_matrix_candidate_search
    from . import _ground_cross_matrix_cell_selection
    from . import _ground_cross_rule_candidate_build
    from . import _ground_cross_rule_search
    from . import _ground_interactive_tree_auto_continuation
    from . import _ground_interactive_tree_frontier_group_materialization
    from . import _ground_interactive_tree_frontier_materialization
    from . import _ground_interactive_tree_revision
    from . import _ground_interactive_tree_split_search
    from . import _ground_model_score_comparison_v2_request
    from . import _ground_roll_rate_column_bindings
    from . import _ground_scorecard_band_build
    from . import _ground_scorecard_cutoff_selection
    from . import _ground_strategy_impact_cube_request
    from . import _ground_strategy_model_evidence_v2_request
    from . import _ground_strategy_pool_apply_request
    from . import _ground_strategy_pool_impact_request
    from . import _ground_strategy_pool_materialize_request
    from . import _ground_strategy_pool_request
    from . import _ground_strategy_pool_stability_request
    from . import _ground_strategy_pool_validation_request
    from . import _ground_strategy_sample_design_v2_request
    from . import _ground_univariate_candidate_analysis
    from . import _ground_voting_candidate_build
    from . import _ground_voting_candidate_build_from_search
    from . import _ground_voting_candidate_search
    from . import _is_canonical_stored_strategy_report_request
    from . import _utterance_contains_token
    from . import _utterance_supports_risk_threshold
    from . import _utterance_targets_automatic_tree_apply
    from . import _utterance_targets_cross_candidate_search
    from . import _utterance_targets_cross_matrix
    from . import _utterance_targets_cross_matrix_cell_selection
    from . import _utterance_targets_cross_rule_search
    from . import _utterance_targets_cross_rule_selection
    from . import _utterance_targets_cross_search_selection
    from . import _utterance_targets_strategy_model_evidence_v2
    from . import _utterance_targets_strategy_pool_apply
    from . import _utterance_targets_strategy_pool_impact
    from . import _utterance_targets_strategy_pool_validation
    from . import _utterance_targets_voting_candidate
    from . import _utterance_targets_voting_candidate_search
    from . import _utterance_targets_voting_search_selection
    from . import utterance_targets_candidate_monthly_stability
    from . import utterance_targets_interactive_tree_frontier_group_materialization
    from . import utterance_targets_interactive_tree_frontier_materialization
    from . import utterance_targets_model_score_comparison_v2
    from . import utterance_targets_scorecard_band_build
    from . import utterance_targets_scorecard_cutoff_selection
    from . import utterance_targets_strategy_impact_cube
    from . import utterance_targets_strategy_pool_materialize
    from . import utterance_targets_strategy_pool_stability
    from . import utterance_targets_strategy_sample_design

_PROJECT_CONTEXT_SUBJECT_RE = re.compile(
    r"(?:Policy)?Item(?:Context|Status|Background|Situation)|Current item(?:Status|Situation)|"
    r"History(?:Version)?Policy(?:Effects|Rewind|Recalling)?|project\s+context|"
    r"current\s+project\s+(?:status|context)|historical\s+strateg(?:y|ies)",
    re.IGNORECASE,
)

_PROJECT_CONTEXT_ACTION_RE = re.compile(
    r"(?:Collapse|Combination|Summary|Collection|Create|Create|Generate|Solid|Refresh|Update|Supplementary|Records|Inventory|Rewind|"
    r"materialize|collect|build|create|refresh|update|record|review)",
    re.IGNORECASE,
)

_PROJECT_CONTEXT_NONCOMMAND_RE = re.compile(
    r"[??]|(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Cancel|Assumptions|If|Later|Later.|The future.)|"
    r"(?:do\s+not|don't|never|cancel|what\s+if|later|in\s+the\s+future)",
    re.IGNORECASE,
)

_PROJECT_CONTEXT_CHAINED_ACTION_RE = re.compile(
    r"(?:And then...|Catch.|And then...|And...|and|Again.).{0,24}"
    r"(?:Sample design|Single Variable|Modelling|Build a tree.|Decision Tree|Into the pool.|Policy development|Impact measurement|Report|Accepted|Deployment|Online.)",
    re.IGNORECASE,
)

_STRATEGY_REPORT_DEFAULT_TITLE = "Policy iterative review report"

_STRATEGY_REPORT_DEFAULT_STATUS = "partial"

_STRATEGY_REPORT_SUBJECT_RE = re.compile(
    r"(?:Policy(?:Organisation|Development|Analysis|Item)?Review report|"
    r"Governance(?:It's...)?Policy(?:Organisation)?(?:Evaluation)?Report|"
    r"StrategyReportBundle(?:\s*V2)?|"
    r"governed\s+strategy\s+report(?:\s+bundle)?|"
    r"strategy\s+(?:iteration|development|review)\s+report(?:\s+bundle)?|"
    r"report\s+bundle\s+(?:for|on)\s+(?:the\s+)?(?:current\s+)?strategy)",
    re.IGNORECASE,
)

_STRATEGY_REPORT_STORED_STRATEGY_RE = re.compile(
    r"(?:Existing|Saved|Created|Existing)"
    r"[^;;..!??\n]{0,24}Policy(?:Evaluation)?Report|"
    r"(?<![A-Za-z0-9_])(?:existing|saved|stored)"
    r"[^;.!?\n]{0,32}\bstrategy(?:\s+review)?\s+report\b",
    re.IGNORECASE,
)

_STRATEGY_REPORT_ACTION_RE = re.compile(
    r"(?:Generate|Create|Production|Preparation|Form|One.|Here we go.|Give it to me.|Export|Build)"
    r"[^;;..!??\n]{0,80}(?:Report|Report)|"
    r"(?<![A-Za-z0-9_])(?:generate|create|build|produce|prepare|render|export)"
    r"[^;.!?\n]{0,80}\breport(?:\s+bundle)?\b",
    re.IGNORECASE,
)

_STRATEGY_REPORT_NEGATED_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Not yet.|Cancel|Stop|Ban|Don't.|No, no.(?!Yes.))"
    r"[^;;..!??\n]{0,48}(?:Generate|Create|Production|Preparation|Form|Export|Report)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|not|never|cancel|stop)"
    r"[^;.!?\n]{0,48}(?:generate|create|build|produce|prepare|render|export)"
    r"[^;.!?\n]{0,32}\breport\b",
    re.IGNORECASE,
)

_STRATEGY_REPORT_NONCOMMAND_RE = re.compile(
    r"[??]|(?:Can you...|Can I?|Is it possible?|Is that okay?|Can you...|Do you want it?|Is it possible?|How's that?|What?|What?|Assumptions|Suppose...|If|"
    r"If|Presentation|Demonstration|Example|Curriculum|Explain.|Explain.)|"
    r"(?<![A-Za-z0-9_])(?:can\s+you|could\s+you|would\s+you|"
    r"should\s+(?:i|we)|is\s+it\s+possible|what\s+if|suppose|assuming|"
    r"how\s+to|hypothetical(?:ly)?|example|demo|test|tutorial)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_STRATEGY_REPORT_PAST_RE = re.compile(
    r"(?:Yesterday.|Before|Before|Go on.|Last time.|Once.|History)|"
    r"(?:Already|Already)\s*(?:Generate|Create|Production|Preparation|Form|Export)|"
    r"(?<![A-Za-z0-9_])(?:yesterday|previously|earlier|historically|"
    r"last\s+time|in\s+the\s+past|already\s+(?:generated|created|"
    r"built|produced|prepared|rendered|exported))(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_STRATEGY_REPORT_CURRENT_RE = re.compile(
    r"(?:Now.|This time.|This time.|Restart|Regenerated|Immediately|Now.)|"
    r"(?<![A-Za-z0-9_])(?:now|currently|this\s+time|again|regenerate)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_STRATEGY_REPORT_RETRIEVAL_RE = re.compile(
    r"(?:View|Take a look.|Look at this.|Open|Access|Out|Search|Look back.|Download)"
    r"[^;;..!??\n]{0,80}(?:Report|Report)|"
    r"(?<![A-Za-z0-9_])(?:view|open|retrieve|get|fetch|show|download)"
    r"[^;.!?\n]{0,80}\breport(?:\s+bundle)?\b",
    re.IGNORECASE,
)

_STRATEGY_REPORT_CHAINED_OPERATION_RE = re.compile(
    r"(?:Training(?:Model)?|Modelling|(?:Model|Data)?Rating|Score|"
    r"(?:Generate|Build|Development|Filter|Analysis)(?:Policy)?Candidates|"
    r"(?:Measurement|Calculate|Evaluation|Retrospect)(?:Current)?(?:Policy pool|Pool)?(?:It's...)?Impact|"
    r"Impact measurement|Accepted|Adopt|Deployment|Online.|Production)|"
    r"(?<![A-Za-z0-9_])(?:train(?:ing)?(?:\s+(?:a\s+)?model)?|"
    r"score(?:\s+(?:the\s+)?(?:model|data|dataset))|"
    r"(?:build|create|generate|develop|select|analy[sz]e)\s+"
    r"(?:a\s+)?(?:strategy\s+)?candidate|"
    r"(?:measure|calculate|assess|backtest)(?:\s+(?:the\s+)?)?"
    r"(?:strategy\s+pool\s+)?impact|adopt|deploy|go[-\s]?live|"
    r"put\s+into\s+production)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_STRATEGY_REPORT_CHAIN_NEGATION_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|Not anymore.|Not really.|Not|No, no.|Ban|Avoid)\s*$|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|not|never|without)\s*$",
    re.IGNORECASE,
)

_STRATEGY_REPORT_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:project_context_ref|sample_design_ref|candidate_pool_ref|"
    r"candidate_stability_ref|pool_impact_ref|impact_cube_ref|"
    r"strategy_identity|model_evidence_ref|"
    r"training_evidence_ref|score_evidence_ref|report_revision|"
    r"previous_report_id|previous_report_content_hash|generated_at|"
    r"strategy_id|strategy_version|artifact_id|content_hash|"
    r"expected_[a-z0-9_]+|cas|metrics?)(?![A-Za-z0-9_])|"
    r"(?:Project context|Sample design|Policy pool|Impact measurement|Model evidence|Training evidence|Rating evidence)"
    r"\s*(?:artifact|Work|Products)?\s*(?:ID|id|hash|Hash.|References)|"
    r"(?:Report|report)\s*(?:revision|Version)\s*(?:=|:|:)\s*\d+|"
    r"(?:Generate Time|generated\s+at)\s*(?:=|:|:)|"
    r"(?:Pass rate|Approval rate|Access rate|Bad debt rate|Risk rate|Overdue rate|"
    r"KS|AUC|PSI|Proceeds|Profit|Losses)\s*(?:=|:|:|Yes)\s*[-+]?\d",
    re.IGNORECASE,
)

_STRATEGY_REPORT_TITLE_RE = re.compile(
    r"(?:Title of report|Title|report\s+title|title)\s*"
    r"(?:Yes|Yes.|Please.|is|=|:|:)\s*"
    r"(?:[(\"'<](?P<quoted>[^)\"'>\n]{1,200})[)\"'>]|"
    r"(?P<plain>[^,,;;..!??\n]{1,200}))",
    re.IGNORECASE,
)

_STRATEGY_REPORT_STATUS_VALUE_PATTERNS = {
    "draft": re.compile(
        r"(?:Draft|Draft)|(?<![A-Za-z0-9_])draft(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "partial": re.compile(
        r"(?:Stage|Part|Centre)|"
        r"(?<![A-Za-z0-9_])partial(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "final": re.compile(
        r"(?:Eventually.|Final|Final)|"
        r"(?<![A-Za-z0-9_])final(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
}

_STRATEGY_REPORT_STATUS_LABEL_RE = re.compile(
    r"(?:Report)?Status|(?<![A-Za-z0-9_])status(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_STRATEGY_REPORT_STATUS_NEGATION_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Not yet.|Ban|Exclude|Not|No, it's not.|Not really.|Do Not Use)"
    r"[^,,;;..!??\n]{0,20}$|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|not|never|without|exclude)"
    r"[^,;.!?\n]{0,20}$",
    re.IGNORECASE,
)

_STRATEGY_REPORT_STATUS_HISTORY_RE = re.compile(
    r"(?:Yesterday.|Before|Before|Go on.|Last time.|Once.|History|Archived|Generated)|"
    r"(?<![A-Za-z0-9_])(?:yesterday|previously|earlier|historical|"
    r"last\s+time|archived|already\s+generated)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_STRATEGY_DSL_DELIVERY_FORMAT_SEQUENCE = (
    r"(?:Python|SQL|JSON)"
    r"(?:(?:\s*(?:[,,/+]|and|and|and|and)\s*|\s+)"
    r"(?:Python|SQL|JSON)){1,2}"
)

_STRATEGY_DSL_DELIVERY_SUBJECT_RE = re.compile(
    r"(?:Policy(?:DSL|Code|Delivery package|Delivery documents)|"
    r"Policy[^;;..!??\n]{0,48}(?:DSL|Code|Delivery package|Delivery documents|"
    + _STRATEGY_DSL_DELIVERY_FORMAT_SEQUENCE
    + r")|"
    + _STRATEGY_DSL_DELIVERY_FORMAT_SEQUENCE
    + r"[^;;..!??\n]{0,40}(?:Policy|Code|Delivery)|"
    r"\bstrategy\b[^;.!?\n]{0,64}(?:DSL|code|delivery|delivery\s+bundle|"
    + _STRATEGY_DSL_DELIVERY_FORMAT_SEQUENCE
    + r")\b)",
    re.IGNORECASE,
)

_STRATEGY_DSL_DELIVERY_ACTION_RE = re.compile(
    r"(?:Export|Generate|Create|Build|Pack up.|Delivery|Download)"
    r"[^;;..!??\n]{0,80}(?:Policy(?:DSL|Code|Delivery)|Python|SQL|JSON)|"
    r"(?<![A-Za-z0-9_])(?:export|generate|create|build|package|deliver|download)"
    r"[^;.!?\n]{0,80}\b(?:strategy\s+)?"
    r"(?:DSL|code|delivery|Python|SQL|JSON)\b",
    re.IGNORECASE,
)

_STRATEGY_DSL_DELIVERY_NEGATED_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Not yet.|Cancel|Stop|Ban|Don't.|No, no.(?!Yes.))"
    r"[^;;..!??\n]{0,48}(?:Export|Generate|Create|Build|Pack up.|Delivery|Download)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|not|never|cancel|stop)"
    r"[^;.!?\n]{0,48}(?:export|generate|create|build|package|deliver|download)",
    re.IGNORECASE,
)

_STRATEGY_DSL_DELIVERY_NONCOMMAND_RE = re.compile(
    r"[??]|(?:Can you...|Can I?|Is it possible?|Is that okay?|Can you...|Do you want it?|Is it possible?|How's that?|What?|What?|"
    r"Assumptions|Suppose...|If|If|Presentation|Demonstration|Example|Curriculum|Explain.|Explain.)|"
    r"(?<![A-Za-z0-9_])(?:can\s+you|could\s+you|would\s+you|"
    r"should\s+(?:i|we)|is\s+it\s+possible|what\s+if|suppose|assuming|"
    r"how\s+to|hypothetical(?:ly)?|example|demo|test|tutorial)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_STRATEGY_DSL_DELIVERY_PAST_RE = re.compile(
    r"(?:Yesterday.|Before|Before|Go on.|Last time.|Once.|History)|"
    r"(?:Already|Already)\s*(?:Export|Generate|Create|Build|Pack up.|Delivery|Download)|"
    r"(?<![A-Za-z0-9_])(?:yesterday|previously|earlier|historically|"
    r"last\s+time|in\s+the\s+past|already\s+(?:exported|generated|created|"
    r"built|packaged|delivered|downloaded))(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_STRATEGY_DSL_DELIVERY_CURRENT_RE = re.compile(
    r"(?:Now.|This time.|This time.|Restart|Export|Immediately|Now.)|"
    r"(?<![A-Za-z0-9_])(?:now|currently|this\s+time|again|re-export)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_STRATEGY_DSL_DELIVERY_CHAIN_RE = re.compile(
    r"(?:Apply|Write back|Back up.|Accepted|Adopt|Deployment|Online.|Production|Promotion|Generate Report|Create Report|"
    r"Impact measurement|Training(?:Model)?|Modelling|(?:Model|Data)?Rating)|"
    r"(?<![A-Za-z0-9_])(?:apply|write\s*back|adopt|deploy|go[-\s]?live|"
    r"put\s+into\s+production|promote|generate\s+(?:a\s+)?report|"
    r"measure\s+impact|train(?:\s+(?:a\s+)?model)?|score)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_STRATEGY_DSL_DELIVERY_CHAIN_NEGATION_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|Not anymore.|Not really.|Not|No, no.|Ban|Avoid)\s*$|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|not|never|without)\s*$",
    re.IGNORECASE,
)

_STRATEGY_DSL_DELIVERY_NEGATED_CHAIN_LIST_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|Not anymore.|Ban|Avoid|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|never|without))\s*"
    r"(?:Apply|Write back|Back up.|Accepted|Adopt|Deployment|Online.|Production|Promotion|Generate Report|Create Report|"
    r"Impact measurement|Training(?:Model)?|Modelling|(?:Model|Data)?Rating|"
    r"apply|write\s*back|adopt|deploy|go[-\s]?live|promote|"
    r"generate\s+(?:a\s+)?report|measure\s+impact|"
    r"train(?:\s+(?:a\s+)?model)?|score)"
    r"(?:\s*(?:,|,|,|or|and|and|and|/|\band\b|\bor\b)\s*"
    r"(?:Apply|Write back|Back up.|Accepted|Adopt|Deployment|Online.|Production|Promotion|Generate Report|Create Report|"
    r"Impact measurement|Training(?:Model)?|Modelling|(?:Model|Data)?Rating|"
    r"apply|write\s*back|adopt|deploy|go[-\s]?live|promote|"
    r"generate\s+(?:a\s+)?report|measure\s+impact|"
    r"train(?:\s+(?:a\s+)?model)?|score))*",
    re.IGNORECASE,
)

_STRATEGY_DSL_DELIVERY_PLATFORM_CONTROL_RE = re.compile(
    r"\b(?:strategy_ref|dataset_ref|workspace_ref|workspace_revision|"
    r"analysis_generation|semantic_mapping_hash|expected_strategy_type|expected_version|"
    r"expected_spec_hash|expected_content_hash|maximum_equivalence_rows|"
    r"source_row_count|sample_count|sample_hash|result_hashes|content_hash|"
    r"artifact_id|delivery_id|equivalence_id)\b|"
    r"(?:Policy(?:Version|Type|Hash.)|Sample(?:Data)?(?:ID|Hash.)|"
    r"Dataset(?:ID|Hash.)|Data Hash|Equivalent(?:Verify)?(?:Sample)?(?:Upper limit|Lines)|"
    r"ProductsID|WorkID)\s*"
    r"(?:(?:Settings|Set|Assign|Adjustment|Change)?(?:Yes|Done.)|Use|Adopt|Remove|=|:|:)?\s*"
    r"(?:[-+]?\d+(?:\.\d+)?|[A-Za-z][A-Za-z0-9_.:-]*)|"
    r"(?:Use|Use|Adopt|Assign)\s*(?:Dataset|Sample data)\s*"
    r"(?:(?:Yes|Yes.)|=|:|:)?\s*[A-Za-z0-9][A-Za-z0-9_.:-]*|"
    r"(?:Approval|Access|Reject|Amount|Limits|Letters|Pricing|Interest rate|Group|Layer)\s*Policy|"
    r"Version\s*(?:(?:Yes|Yes.)|=|:|:)?\s*\d+(?!\d)|"
    r"(?:v(?:ersion)?\s*\d+)[^,,;;..!??\n]{0,12}Policy|"
    r"Policy[^,,;;..!??\n]{0,12}(?:v(?:ersion)?\s*\d+)|"
    r"\d+\s*Okay.[^,,;;..!??\n]{0,12}Equivalent|"
    r"Equivalent[^,,;;..!??\n]{0,12}\d+\s*Okay.|"
    r"\b(?:strategy\s+(?:version|type|hash)|"
    r"dataset(?:\s+(?:id|hash))?|data\s+hash|"
    r"workspace\s+(?:revision|generation)|semantic\s+mapping\s+hash|"
    r"artifact\s+id)\s*(?:(?:is|to|as)|=|:)?\s*"
    r"(?:[-+]?\d+(?:\.\d+)?|[A-Za-z][A-Za-z0-9_.:-]*)\b|"
    r"\b(?:approval|admission|reject(?:ion)?|limit|pricing|segmentation)"
    r"\s+strategy\b|"
    r"\b(?:v(?:ersion)?\s*\d+)[^;,.!?\n]{0,20}\bstrategy\b|"
    r"\bstrategy\b[^;,.!?\n]{0,20}\b(?:v(?:ersion)?\s*\d+)\b|"
    r"\b(?:use|using|with|select|choose)\s+(?:the\s+)?dataset\s+"
    r"[A-Za-z0-9][A-Za-z0-9_.:-]*\b|"
    r"\b\d+\s*[- ]?\s*rows?\b[^;,.!?\n]{0,24}\bequivalence\b|"
    r"\bequivalence\b[^;,.!?\n]{0,24}\b\d+\s*[- ]?\s*rows?\b|"
    r"\b(?:maximum|max(?:imum)?|limit(?:ed)?\s+to)\s+\d+\s+"
    r"(?:equivalence(?:\s+(?:sample|check))?\s+rows?|"
    r"rows?\s+for\s+equivalence)\b|"
    r"\bequivalence(?:\s+(?:sample|check))?\s+(?:limit|rows?)\s*"
    r"(?:(?:is|to)|=|:)?\s*\d+\b",
    re.IGNORECASE,
)

_STRATEGY_DSL_DELIVERY_STRATEGY_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_])strategy-[A-Za-z0-9][A-Za-z0-9_-]*"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

def _ground_refinement_request(
    utterance: str,
    result: StrategyRequestCompilation,
    *,
    whitelist: tuple[str, ...],
    target_col: str | None,
) -> StrategyRequestCompilation:
    draft = result.draft
    if _utterance_targets_voting_search_selection(utterance):
        if not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow == "voting_candidate_build_from_search"
        ):
            return _clarification(
                "The exact words are from one.Voting Full Search Resultsearch_id andcombo_id "
                "Build candidate, only compiled asvoting_candidate_build_from_search;We can't change the route."
                "Research, freedom.rule ID Build, use or otherwiseWorkflow.",
                code="voting_search_selection_workflow_required",
                fields=("workflow",),
            )
        return _ground_voting_candidate_build_from_search(utterance, result)
    if utterance_targets_strategy_dsl_delivery(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "strategy_dsl_delivery"
    ):
        return _clarification(
            "The original words clearly require the export of offline strategy codes and equivalent evidence, which can only be compiled into"
            "strategy_dsl_delivery;We can't change course to a common strategy application, reporting,"
            "Adopt or deploy.",
            code="strategy_dsl_delivery_workflow_required",
            fields=("workflow",),
        )
    if (
        utterance_targets_strategy_report_bundle_v2(utterance)
        and not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow == "strategy_report_bundle_v2"
        )
        and not _is_canonical_stored_strategy_report_request(draft)
    ):
        return _clarification(
            "The original language explicitly requires the production of reports subject to the governance strategy review, which can only be compiled and translated into"
            "strategy_report_bundle_v2;We can't change course to generic strategy reports, training,"
            "Rating, candidate, impact measurement, adoption or deployment.",
            code="strategy_report_bundle_v2_workflow_required",
            fields=("workflow",),
        )
    if utterance_targets_strategy_project_context(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "strategy_project_context"
    ):
        return _clarification(
            "The original words clearly require a consolidation of the current status or historical strategy of the project, which can only be translated as"
            "strategy_project_context;The route cannot be changed to the life cycle of the sample, candidate analysis, reporting or common strategy.",
            code="strategy_project_context_workflow_required",
            fields=("workflow",),
        )
    if utterance_targets_strategy_sample_design(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "strategy_sample_design_v2"
    ):
        return _clarification(
            "The original words clearly require solidification of the strategy sample design, which can only be compiled intostrategy_sample_design_v2;"
            "We can't change the route to modeling, building trees,Strategy Pool,Reporting or common strategy life cycle.",
            code="strategy_sample_design_v2_workflow_required",
            fields=("workflow",),
        )
    if _utterance_targets_strategy_model_evidence_v2(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "strategy_model_evidence_v2"
    ):
        return _clarification(
            "The original language explicitly requires that the existing authentication sheet evidence be aggregated and can only be compiled into"
            "strategy_model_evidence_v2;There can be no diversion to training, model comparison, reporting or deployment.",
            code="strategy_model_evidence_v2_workflow_required",
            fields=("workflow",),
        )
    if utterance_targets_model_score_comparison_v2(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "strategy_model_score_comparison_v2"
    ):
        return _clarification(
            "The original words clearly require that the materialized model rate comparative evidence, which can only be compiled into"
            "strategy_model_score_comparison_v2;We can't change course to training."
            "Championships choose, adopt or deploy.",
            code="strategy_model_score_comparison_v2_workflow_required",
            fields=("workflow",),
        )
    if utterance_targets_candidate_monthly_stability(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "candidate_monthly_stability"
    ):
        return _clarification(
            "The original statement expressly requires that the assets be presented or that the assets be used for the purpose of the application.Strategy Pool Monthly stability of the item/PSI,"
            "Only compiled ascandidate_monthly_stability;We can't change the route to universal surveillance."
            "Pool Impact measurement or otherWorkflow.",
            code="candidate_monthly_stability_workflow_required",
            fields=("workflow",),
        )
    if (
        utterance_targets_scorecard_cutoff_selection(utterance)
        and not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow
            in {"scorecard_band_build", "scorecard_cutoff_selection"}
        )
    ):
        return _clarification(
            "The words clearly require the integrity of the system.Scorecard Select exactly one in the fractional bandcutoff,"
            "Only compiled asscorecard_cutoff_selection;We can't change the route to the fractional belt."
            "Automatically recommend,Strategy Pool,Adopt or deploy.",
            code="scorecard_cutoff_selection_workflow_required",
            fields=("workflow",),
        )
    if utterance_targets_scorecard_band_build(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "scorecard_band_build"
    ):
        return _clarification(
            "The original words clearly require complete constructionScorecard The split band, only compiled into"
            "scorecard_band_build;We can't change the course.cutoff Select, automatically recommend,"
            "Strategy Pool,Adopt or deploy.",
            code="scorecard_band_build_workflow_required",
            fields=("workflow",),
        )
    if utterance_targets_interactive_tree_frontier_group_materialization(
        utterance
    ) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow
        == "interactive_tree_frontier_group_materialization"
    ):
        return _clarification(
            "The original words clearly require an interactive tree.revision More precise objectsfrontier "
            "node/leaf It's...OR Grouping, only compiled as"
            "interactive_tree_frontier_group_materialization;We can't change the course."
            " singleton,Cut, trim,Strategy Pool or otherWorkflow.",
            code="interactive_tree_frontier_group_workflow_required",
            fields=("workflow",),
        )
    if utterance_targets_interactive_tree_frontier_materialization(
        utterance
    ) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "interactive_tree_frontier_materialization"
    ):
        return _clarification(
            "The original words clearly require an interactive tree.revision Exact Physicalizationfrontier node/leaf,"
            "Only compiled asinteractive_tree_frontier_materialization;We can't change the route."
            "To trim, to automatically choose, to choose,Strategy Pool or otherWorkflow.",
            code="interactive_tree_frontier_workflow_required",
            fields=("workflow",),
        )
    if _utterance_targets_automatic_tree_apply(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow in {"automatic_tree_apply", "interactive_tree_revision"}
    ):
        return _clarification(
            "The original phrase expressly requires that the whole automatic tree be returned to the current sample and can only be translated into"
            "automatic_tree_apply;We can't change the route to a common strategy, build a tree, and a leaf node."
            "Physicalization, entry into the pool or otherWorkflow.",
            code="automatic_tree_apply_workflow_required",
            fields=("workflow",),
        )
    if utterance_targets_strategy_pool_materialize(utterance):
        if not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow == "strategy_pool_materialize"
        ):
            return _clarification(
                "The original is clearly a requirement to put the currentStrategy Pool \"To become something durable.\"draft Strategy,"
                "Only compiled asstrategy_pool_materialize;We can't change the course.Pool Compile previews,"
                "Existing policybuild,Adoption, deployment or otherWorkflow.",
                code="strategy_pool_materialize_workflow_required",
                fields=("workflow",),
            )
        # This dedicated command owns the whole utterance. Ground it now so
        # words such as "backtest/report" in a chained follow-up cannot be
        # mistaken for a different Pool workflow before the single-operation
        # guard reports the precise materialization error.
        return _ground_strategy_pool_materialize_request(utterance, result)
    if _utterance_targets_strategy_pool_apply(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and (
            draft.workflow == "strategy_pool_apply"
            or draft.workflow == "automatic_tree_apply"
            or draft.workflow in _POOL_MUTATION_WORKFLOWS
        )
    ):
        return _clarification(
            "The original is clearly a requirement to put the currentStrategy Pool Apply or write back the current sample, only as"
            "strategy_pool_apply;We can't change the course.Pool Compile previews, generic existing strategies,"
            "Impact measurement, adoption, deployment or otherWorkflow.",
            code="strategy_pool_apply_workflow_required",
            fields=("workflow",),
        )
    if utterance_targets_strategy_pool_stability(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "strategy_pool_stability"
    ):
        return _clarification(
            "The original words clearly require measurement of the currentStrategy Pool The distribution of the trans-zonal is stable, and can only be compiled as"
            "strategy_pool_stability;We can't change the course.ImpactCube,Independent Results Validation,"
            "Reporting or life cycle operations.",
            code="strategy_pool_stability_workflow_required",
            fields=("workflow",),
        )
    if _utterance_targets_strategy_pool_validation(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "strategy_pool_validation"
    ):
        return _clarification(
            "The original requirement is clear for the currentStrategy Pool Implementationvalidation/OOT Independent sample"
            "Playback validation, only compiled asstrategy_pool_validation;We can't change the course."
            " Pool Impact, monthly stability, compilation, application, reporting or life cycle operations.",
            code="strategy_pool_validation_workflow_required",
            fields=("workflow",),
        )
    if utterance_targets_strategy_impact_cube(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and draft.workflow == "strategy_impact_cube"
    ):
        return _clarification(
            "The original language clearly requires five types of harmonization.Strategy ImpactCube,Only compiled as"
            "strategy_impact_cube;You can't downgrade toapproval/reject Old impact caliber,"
            "Pool Revision, reporting, adoption or deployment.",
            code="strategy_impact_cube_workflow_required",
            fields=("workflow",),
        )
    if _utterance_targets_strategy_pool_impact(utterance) and not (
        isinstance(draft, StandardWorkflowRequestDraft)
        and (
            draft.workflow in {"strategy_pool_impact", "strategy_impact_cube"}
            or (
                draft.workflow == "candidate_monthly_stability"
                and utterance_targets_candidate_monthly_stability(utterance)
            )
        )
    ):
        return _clarification(
            "The exact words of the original requestStrategy Pool Impact measurement, only compiled intostrategy_pool_impact;"
            "We can't change the course.Pool Revision, common strategy life cycle, reporting or otherWorkflow.",
            code="strategy_pool_impact_workflow_required",
            fields=("workflow",),
        )
    if (
        _utterance_targets_cross_rule_selection(utterance)
        and not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow
            == "cross_rule_candidate_build_from_search"
        )
    ):
        return _clarification(
            "The original text is clear.Cross rule search_id andrule_id And it requires precise construction."
            "Candidates, only compiled ascross_rule_candidate_build_from_search;"
            "You can't select, re-search or reroute by ranking.Cross Matrix.",
            code="cross_rule_selection_workflow_required",
            fields=("workflow",),
        )
    if (
        _utterance_targets_cross_rule_search(utterance)
        and not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow == "cross_rule_search"
        )
    ):
        return _clarification(
            "Word explicitly requires search 2D/3D Cross Threshold rule, only compiled into"
            "cross_rule_search;We can't change the course.Cross Matrix Fields Against Search,"
            "A visible double-axis construction or a common strategy life cycle.",
            code="cross_rule_search_workflow_required",
            fields=("workflow",),
        )
    if (
        _utterance_targets_cross_search_selection(utterance)
        and not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow
            == "cross_matrix_candidate_build_from_search"
        )
    ):
        return _clarification(
            "The original text is clear.Cross search_id andpair_id The blog also asks for a precise selection of candidates."
            "Only compiled ascross_matrix_candidate_build_from_search;"
            "No search, ranking or reroutingWorkflow.",
            code="cross_search_selection_workflow_required",
            fields=("workflow",),
        )
    if (
        _utterance_targets_cross_candidate_search(utterance)
        and not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow == "cross_matrix_candidate_search"
        )
    ):
        return _clarification(
            "The original message clearly requires a search.Cross Matrix Feature group, only compiled into"
            "cross_matrix_candidate_search;Can't change the route to a visible double-axis construction,"
            "Common strategy life cycle or otherWorkflow.",
            code="cross_candidate_search_workflow_required",
            fields=("workflow",),
        )
    if (
        _utterance_targets_cross_matrix_cell_selection(utterance)
        and not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow == "cross_matrix_cell_selection"
        )
    ):
        return _clarification(
            "The exact words are fromCross Matrix Select cells precisely, only to be compiled into"
            "cross_matrix_cell_selection;Can't change course to matrix construction, common strategy life cycle."
            "or otherWorkflow.",
            code="cross_matrix_cell_selection_workflow_required",
            fields=("workflow",),
        )
    if (
        _utterance_targets_cross_matrix(utterance)
        and not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow
            in {
                "cross_matrix_analysis",
                "cross_matrix_cell_selection",
                "cross_matrix_candidate_search",
                "cross_matrix_candidate_build_from_search",
            }
        )
    ):
        return _clarification(
            "The exact exact words are 2D.Cross Matrix,Only compiled ascross_matrix_analysis;"
            "Common strategy life cycle or otherWorkflow We can't consume these two cross-axis.",
            code="cross_matrix_workflow_required",
            fields=("workflow",),
        )
    if (
        draft is not None
        and _utterance_targets_voting_candidate_search(utterance)
        and not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow == "voting_candidate_search"
        )
    ):
        return _clarification(
            "The original language explicitly requires search, search or optimizationVoting Group, only compiled as"
            "voting_candidate_search;No rerouting to visible membership, common strategy"
            "Life cycle or otherWorkflow.",
            code="voting_candidate_search_workflow_required",
            fields=("workflow",),
        )
    if (
        draft is not None
        and _utterance_targets_voting_candidate(utterance)
        and not (
            isinstance(draft, StandardWorkflowRequestDraft)
            and draft.workflow in {"voting_candidate_search", "voting_candidate_build"}
        )
    ):
        return _clarification(
            "Name it clearly.Voting / n-of-k and multiple completescandidate-rule ID,"
            "Only compiled asvoting_candidate_build;Common strategy life cycle or other"
            "Workflow These controls cannot be consumed.",
            code="voting_candidate_workflow_required",
            fields=("workflow",),
        )
    if not isinstance(draft, StandardWorkflowRequestDraft):
        return result
    if draft.workflow == "roll_rate_matrix":
        return _ground_roll_rate_column_bindings(
            utterance,
            result,
            whitelist=whitelist,
            target_col=target_col,
        )
    if draft.workflow == "strategy_project_context":
        return _ground_strategy_project_context_request(utterance, result)
    if draft.workflow == "strategy_sample_design_v2":
        return _ground_strategy_sample_design_v2_request(
            utterance,
            result,
            whitelist=whitelist,
        )
    if draft.workflow == "strategy_model_evidence_v2":
        return _ground_strategy_model_evidence_v2_request(utterance, result)
    if draft.workflow == "strategy_model_score_comparison_v2":
        return _ground_model_score_comparison_v2_request(utterance, result)
    if draft.workflow == "candidate_monthly_stability":
        return _ground_candidate_monthly_stability_request(utterance, result)
    if draft.workflow == "scorecard_band_build":
        return _ground_scorecard_band_build(utterance, result)
    if draft.workflow == "scorecard_cutoff_selection":
        return _ground_scorecard_cutoff_selection(utterance, result)
    if draft.workflow == "strategy_dsl_delivery":
        return _ground_strategy_dsl_delivery_request(utterance, result)
    if draft.workflow == "strategy_report_bundle_v2":
        return _ground_strategy_report_bundle_v2_request(utterance, result)
    if draft.workflow == "strategy_pool_stability":
        return _ground_strategy_pool_stability_request(utterance, result)
    if draft.workflow == "strategy_impact_cube":
        return _ground_strategy_impact_cube_request(
            utterance,
            result,
            whitelist=whitelist,
        )
    if draft.workflow in _STRATEGY_POOL_APPLY_WORKFLOWS:
        return _ground_strategy_pool_apply_request(utterance, result)
    if draft.workflow in _STRATEGY_POOL_MATERIALIZE_WORKFLOWS:
        return _ground_strategy_pool_materialize_request(utterance, result)
    if draft.workflow in _STRATEGY_POOL_VALIDATION_WORKFLOWS:
        return _ground_strategy_pool_validation_request(utterance, result)
    if draft.workflow in _STRATEGY_POOL_MEASUREMENT_WORKFLOWS:
        return _ground_strategy_pool_impact_request(
            utterance,
            result,
            whitelist=whitelist,
        )
    if draft.workflow in _STRATEGY_POOL_WORKFLOWS:
        return _ground_strategy_pool_request(utterance, result)
    if draft.workflow == "automatic_tree_candidate_build":
        return _ground_automatic_tree_candidate_build(
            utterance,
            result,
            whitelist=whitelist,
        )
    if draft.workflow == "automatic_tree_apply":
        return _ground_automatic_tree_apply(
            utterance,
            result,
            whitelist=whitelist,
        )
    if draft.workflow == "automatic_tree_leaf_materialization":
        return _ground_automatic_tree_leaf_materialization(utterance, result)
    if draft.workflow == "interactive_tree_split_search":
        return _ground_interactive_tree_split_search(utterance, result)
    if draft.workflow == "interactive_tree_auto_continuation":
        return _ground_interactive_tree_auto_continuation(utterance, result)
    if draft.workflow == "interactive_tree_revision":
        return _ground_interactive_tree_revision(utterance, result)
    if draft.workflow == "interactive_tree_frontier_group_materialization":
        return _ground_interactive_tree_frontier_group_materialization(
            utterance,
            result,
        )
    if draft.workflow == "interactive_tree_frontier_materialization":
        return _ground_interactive_tree_frontier_materialization(
            utterance,
            result,
        )
    if draft.workflow == "voting_candidate_search":
        return _ground_voting_candidate_search(utterance, result)
    if draft.workflow == "voting_candidate_build_from_search":
        return _ground_voting_candidate_build_from_search(utterance, result)
    if draft.workflow == "voting_candidate_build":
        return _ground_voting_candidate_build(utterance, result)
    if draft.workflow == "cross_rule_search":
        return _ground_cross_rule_search(
            utterance,
            result,
            whitelist=whitelist,
        )
    if draft.workflow == "cross_rule_candidate_build_from_search":
        return _ground_cross_rule_candidate_build(utterance, result)
    if draft.workflow == "cross_matrix_candidate_search":
        return _ground_cross_matrix_candidate_search(
            utterance,
            result,
            whitelist=whitelist,
        )
    if draft.workflow == "cross_matrix_candidate_build_from_search":
        return _ground_cross_matrix_candidate_build_from_search(
            utterance,
            result,
        )
    if draft.workflow == "cross_matrix_cell_selection":
        return _ground_cross_matrix_cell_selection(utterance, result)
    if draft.workflow == "cross_matrix_analysis":
        return _ground_cross_matrix_analysis(
            utterance,
            result,
            whitelist=whitelist,
        )
    if draft.workflow == "univariate_candidate_analysis":
        return _ground_univariate_candidate_analysis(
            utterance,
            result,
            whitelist=whitelist,
        )
    if draft.workflow != "univariate_candidate_refinement":
        return result
    inputs = draft.to_dict()["workflow_inputs"]
    missing_controls: list[str] = []
    source_candidate_id = inputs.get("source_candidate_id")
    if source_candidate_id is not None and not _utterance_contains_token(
        utterance, source_candidate_id
    ):
        missing_controls.append("source_candidate_id")
    if source_candidate_id is None:
        observed_breakpoints, breakpoint_syntax_ambiguous = (
            _explicit_manual_breakpoint_bindings(
                utterance,
                whitelist=whitelist,
            )
        )
        if (
            breakpoint_syntax_ambiguous
            or observed_breakpoints != inputs.get("manual_breakpoints", {})
        ):
            missing_controls.append("manual_breakpoints")

    selection = inputs["selection"]
    if "source_bin_ids" in selection:
        if not _REFINEMENT_SELECTION_ACTION_RE.search(utterance):
            missing_controls.append("Select Action")
        missing_controls.extend(
            bin_id
            for bin_id in selection["source_bin_ids"]
            if not _utterance_contains_token(utterance, bin_id)
        )
    else:
        threshold = selection["risk_threshold"]
        if not _utterance_supports_risk_threshold(
            utterance,
            operator=threshold["operator"],
            value=threshold["value"],
        ):
            missing_controls.append("Clear threshold for observed bad rate")

    merge_groups = inputs["merge_groups"]
    if merge_groups:
        if not _REFINEMENT_MERGE_ACTION_RE.search(utterance):
            missing_controls.append("Merge Actions")
        missing_controls.extend(
            bin_id
            for group in merge_groups
            for bin_id in group
            if not _utterance_contains_token(utterance, bin_id)
        )
    if not missing_controls:
        return result
    return _clarification(
        "Please specify the options to be selected.source bin id,or give a verifiable threshold for the observational bad rate;"
        "Merge/Also refer to the fullness of the analysis when selecting an existing boxcandidate ID."
        "I will not generate a threshold or a box by myself, based on vague expressions such as (best of all).",
        code="strategy_refinement_controls_not_grounded",
        fields=tuple(dict.fromkeys(missing_controls)),
    )

def _ground_strategy_project_context_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if (
        not utterance_targets_strategy_project_context(utterance)
        or _PROJECT_CONTEXT_NONCOMMAND_RE.search(utterance)
    ):
        return _clarification(
            "Please send a single copy of the current status of the project./Positive orders in the context of historical strategies;"
            "The statement, denial, assumption or future description will not update the evidence of the project.",
            code="strategy_project_context_positive_command_required",
            fields=("materialize_intent",),
        )
    if _PROJECT_CONTEXT_CHAINED_ACTION_RE.search(utterance):
        return _clarification(
            "This round will only fix the project status and historical evidence; sample design, candidate analysis, impact measurement,"
            "Reporting, adoption or deployment must be carried out in subsequent governance steps.",
            code="strategy_project_context_single_step_required",
            fields=("next_action",),
        )

    missing: list[str] = []
    if not _project_context_date_is_grounded(utterance, inputs["as_of"]):
        missing.append("as_of")
    scope = inputs.get("scope")
    if isinstance(scope, str) and scope not in utterance:
        missing.append("scope")
    for field_path, value in inputs["business_context"].items():
        if isinstance(value, str):
            if value not in utterance:
                missing.append(f"business_context.{field_path}")
        elif not _project_context_unavailable_is_grounded(utterance, field_path):
            missing.append(f"business_context.{field_path}")
    for field_path in inputs["explicit_unavailable"]:
        if not _project_context_unavailable_is_grounded(utterance, field_path):
            missing.append(f"explicit_unavailable.{field_path}")
    for filename in inputs["external_report_filenames"]:
        # Preserve the exact relative path the user supplied.  Accepting only
        # its basename would let an LLM silently select a different same-name
        # file from a subdirectory of the task source boundary.
        if filename not in utterance:
            missing.append(f"external_report_filenames.{filename}")
    if missing:
        return _clarification(
            "Deadlines, project text, clearly unusable fields and external reporting file names can only be used in the user language;"
            "The platform does not allow the model to write background, missing status or evidence files. Please add or delete fields that are not in the original language.",
            code="strategy_project_context_controls_not_grounded",
            fields=tuple(missing),
        )
    return result

def _project_context_date_is_grounded(utterance: str, iso_date: str) -> bool:
    if iso_date in utterance:
        return True
    year, month, day = (int(part) for part in iso_date.split("-"))
    return re.search(
        rf"(?<!\d){year}\s*Year\s*0?{month}\s*Month\s*0?{day}\s*Day(?!\d)",
        utterance,
    ) is not None

_PROJECT_CONTEXT_UNAVAILABLE_RE = re.compile(
    r"(?:Not yet.|Not available|Not yet.|No, I'm not.|Not provided|Not Available|I don't know.|Unknown|To be completed|"
    r"unavailable|not\s+available|unknown|missing)",
    re.IGNORECASE,
)

_PROJECT_CONTEXT_FIELD_LABELS = {
    "approval": re.compile(r"Pass rate|Approval rate|Access rate|approval", re.IGNORECASE),
    "risk": re.compile(r"Bad debt rate|Risk rate|Overdue rate|risk|bad\s+rate", re.IGNORECASE),
    "volume": re.compile(r"Number of applications|Import|Loans|Volume of business|Size|volume", re.IGNORECASE),
    "economics": re.compile(r"Proceeds|Profit|Cost|Economy|economics|profit", re.IGNORECASE),
    "background": re.compile(r"Background|background", re.IGNORECASE),
    "scope": re.compile(r"Scope|The guests.|Channels|Products|scope", re.IGNORECASE),
    "history": re.compile(r"History|Old version|Previous|history|historical", re.IGNORECASE),
    "historical_strategy_reviews": re.compile(
        r"History(?:Version)?Policy|Historical material|Old version policy|history|historical",
        re.IGNORECASE,
    ),
    "sample": re.compile(r"Sample|sample", re.IGNORECASE),
}

def _project_context_unavailable_is_grounded(
    utterance: str,
    field_path: str,
) -> bool:
    if _PROJECT_CONTEXT_UNAVAILABLE_RE.search(utterance) is None:
        return False
    if field_path in utterance:
        return True
    components = tuple(reversed(field_path.split(".")))
    return any(
        label.search(utterance) is not None
        for component in components
        if (label := _PROJECT_CONTEXT_FIELD_LABELS.get(component)) is not None
    )

def utterance_targets_strategy_project_context(utterance: str) -> bool:
    """Recognize an explicit project-context materialization request."""

    return bool(
        _PROJECT_CONTEXT_SUBJECT_RE.search(utterance)
        and _PROJECT_CONTEXT_ACTION_RE.search(utterance)
    )

def utterance_targets_strategy_dsl_delivery(utterance: str) -> bool:
    """Recognize an explicit offline Strategy DSL delivery request."""

    return bool(
        _STRATEGY_DSL_DELIVERY_SUBJECT_RE.search(utterance)
        and _STRATEGY_DSL_DELIVERY_ACTION_RE.search(utterance)
    )

def _ground_strategy_dsl_delivery_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]

    if _STRATEGY_DSL_DELIVERY_NEGATED_RE.search(utterance):
        return _clarification(
            "Negative policy code export requests do not create or execute delivery plans;"
            "Please issue a separate affirmative order if it is necessary to do so.",
            code="strategy_dsl_delivery_intent_negated",
            fields=("delivery_intent",),
        )
    if (
        not utterance_targets_strategy_dsl_delivery(utterance)
        or _STRATEGY_DSL_DELIVERY_NONCOMMAND_RE.search(utterance)
        or (
            _STRATEGY_DSL_DELIVERY_PAST_RE.search(utterance)
            and _STRATEGY_DSL_DELIVERY_CURRENT_RE.search(utterance) is None
        )
    ):
        return _clarification(
            "Please send out the current strategy once and for all.Python,SQL,JSON - It's the same as the evidence."
            "Positive command; not creating delivery by asking questions, assumptions, demonstrations or just historical descriptions.",
            code="strategy_dsl_delivery_positive_command_required",
            fields=("delivery_intent",),
        )
    if _strategy_dsl_delivery_has_positive_chained_operation(utterance):
        return _clarification(
            "This round can only export offline strategy codes and equivalent evidence; apply, write back, report, impact measurement,"
            "Training, scoring, adoption, promotion or deployment must be independently requested as a follow-up.",
            code="strategy_dsl_delivery_single_operation_required",
            fields=("next_action",),
        )
    if _STRATEGY_DSL_DELIVERY_PLATFORM_CONTROL_RE.search(utterance):
        return _clarification(
            "Policy delivery is only allowed to be provided by usersstrategy_id;Policy type,version/spec hash,"
            "Activity data sets andhash,Sample budget, equivalentartifact id/hash The platform binds the results.",
            code="strategy_dsl_delivery_platform_binding_forbidden",
            fields=("platform_bindings",),
        )

    mentioned_ids = tuple(
        dict.fromkeys(
            match.group(0)
            for match in _STRATEGY_DSL_DELIVERY_STRATEGY_ID_RE.finditer(
                utterance
            )
        )
    )
    selected_id = inputs.get("strategy_id")
    if selected_id is None:
        if mentioned_ids:
            return _clarification(
                "Complete in originalstrategy_id Delivery requests must be entered word for word; platform will not ignore"
                "The government has already called for a strategy and has moved to another one.",
                code="strategy_dsl_delivery_controls_not_grounded",
                fields=("strategy_id",),
            )
    elif mentioned_ids != (selected_id,):
        return _clarification(
            "Policy delivery can only be the only complete word word by wordstrategy_id;MultipleID,"
            "Neither the omission nor the model replacement will be implemented.",
            code="strategy_dsl_delivery_controls_not_grounded",
            fields=("strategy_id",),
        )
    return result

def _strategy_dsl_delivery_has_positive_chained_operation(
    utterance: str,
) -> bool:
    active_text = _STRATEGY_DSL_DELIVERY_NEGATED_CHAIN_LIST_RE.sub(
        " ",
        utterance,
    )
    for match in _STRATEGY_DSL_DELIVERY_CHAIN_RE.finditer(active_text):
        prefix = active_text[max(0, match.start() - 16) : match.start()]
        if _STRATEGY_DSL_DELIVERY_CHAIN_NEGATION_RE.search(prefix) is None:
            return True
    return False

def utterance_targets_strategy_report_bundle_v2(utterance: str) -> bool:
    """Recognize a command-shaped governed strategy-report request."""

    return bool(
        _STRATEGY_REPORT_STORED_STRATEGY_RE.search(utterance) is None
        and _STRATEGY_REPORT_RETRIEVAL_RE.search(utterance) is None
        and _STRATEGY_REPORT_SUBJECT_RE.search(utterance)
        and _STRATEGY_REPORT_ACTION_RE.search(utterance)
    )

def _ground_strategy_report_bundle_v2_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]

    if _STRATEGY_REPORT_NEGATED_RE.search(utterance):
        return _clarification(
            "The negative reporting request will not create or implement a reporting plan; please issue a separate affirmative order if implementation is required.",
            code="strategy_report_bundle_v2_intent_negated",
            fields=("report_intent",),
        )
    if (
        not utterance_targets_strategy_report_bundle_v2(utterance)
        or _STRATEGY_REPORT_NONCOMMAND_RE.search(utterance)
        or (
            _STRATEGY_REPORT_PAST_RE.search(utterance)
            and not _STRATEGY_REPORT_CURRENT_RE.search(utterance)
        )
    ):
        return _clarification(
            "Please issue a single affirmative order immediately generating a report to be evaluated for the governance strategy;"
            "A report will not be created by a query, assumption, demonstration or just a historical description.",
            code="strategy_report_bundle_v2_positive_command_required",
            fields=("report_intent",),
        )
    if _strategy_report_has_positive_chained_operation(utterance):
        return _clarification(
            "Only reports can be generated during this cycle; training, scoring, candidate build/Analysis, impact measurement,"
            "Adoption, deployment or online must be independently requested as a follow-up.",
            code="strategy_report_bundle_v2_single_operation_required",
            fields=("next_action",),
        )
    if _STRATEGY_REPORT_PLATFORM_CONTROL_RE.search(utterance):
        return _clarification(
            "Reports are only available to userstitle/status;ProjectContext,SampleDesign,"
            "Pool,ImpactCube/CompatibilityPoolImpact,Model evidence, strategic identity,"
            "revision/CAS,generated_at,artifact id/hash The Platform bound both the indicators and the indicators.",
            code="strategy_report_bundle_v2_platform_binding_forbidden",
            fields=("platform_bindings",),
        )

    missing: list[str] = []
    title_mentions = _strategy_report_title_mentions(utterance)
    if len(title_mentions) > 1:
        missing.append("title")
    elif title_mentions:
        if inputs["title"] != title_mentions[0]:
            missing.append("title")
    elif inputs["title"] != _STRATEGY_REPORT_DEFAULT_TITLE:
        missing.append("title")

    positive_statuses, negated_statuses = _strategy_report_status_mentions(
        utterance
    )
    status_mentions = set(positive_statuses)
    negated_status_mentions = set(negated_statuses)
    if inputs["status"] in negated_status_mentions:
        missing.append("status")
    elif len(status_mentions) > 1:
        missing.append("status")
    elif status_mentions:
        if inputs["status"] != next(iter(status_mentions)):
            missing.append("status")
    elif inputs["status"] != _STRATEGY_REPORT_DEFAULT_STATUS:
        missing.append("status")

    if missing:
        return _clarification(
            "The title and status of the report can only be used word for word word word word word word word word word word; the platform is used regularly when not available"
            "[The report of the Strategy Review andpartial,Models are not allowed to be supplemented or overwhelmed.",
            code="strategy_report_bundle_v2_controls_not_grounded",
            fields=tuple(dict.fromkeys(missing)),
        )
    return result

def _strategy_report_has_positive_chained_operation(utterance: str) -> bool:
    for match in _STRATEGY_REPORT_CHAINED_OPERATION_RE.finditer(utterance):
        prefix = utterance[max(0, match.start() - 16) : match.start()]
        if _STRATEGY_REPORT_CHAIN_NEGATION_RE.search(prefix) is None:
            return True
    return False

def _strategy_report_title_mentions(utterance: str) -> tuple[str, ...]:
    values: list[str] = []
    for match in _STRATEGY_REPORT_TITLE_RE.finditer(utterance):
        value = (match.group("quoted") or match.group("plain") or "").strip()
        if value and value not in values:
            values.append(value)
    return tuple(values)

def _strategy_report_status_mentions(
    utterance: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return positive and prohibited status controls from the report command."""

    masked = list(utterance)
    for match in _STRATEGY_REPORT_TITLE_RE.finditer(utterance):
        masked[match.start() : match.end()] = " " * (
            match.end() - match.start()
        )
    command_text = "".join(masked)
    action_matches = tuple(_STRATEGY_REPORT_ACTION_RE.finditer(command_text))
    if not action_matches:
        return (), ()

    positive: list[str] = []
    negated: list[str] = []
    for status, value_pattern in _STRATEGY_REPORT_STATUS_VALUE_PATTERNS.items():
        for value_match in value_pattern.finditer(command_text):
            if (
                _STRATEGY_REPORT_STATUS_HISTORY_RE.search(
                    _strategy_report_control_clause(
                        command_text,
                        start=value_match.start(),
                        end=value_match.end(),
                    )
                )
                or not _strategy_report_status_shares_command(
                    command_text,
                    value_start=value_match.start(),
                    value_end=value_match.end(),
                    action_matches=action_matches,
                )
            ):
                continue
            if _strategy_report_status_span_is_negated(
                command_text,
                start=value_match.start(),
            ):
                negated.append(status)
                break
            if _strategy_report_status_has_positive_assignment(
                command_text,
                value_start=value_match.start(),
                value_end=value_match.end(),
            ) or any(
                action.start() <= value_match.start()
                and value_match.end() <= action.end()
                for action in action_matches
            ):
                positive.append(status)
                break
    return tuple(positive), tuple(negated)

def _strategy_report_control_clause(
    utterance: str,
    *,
    start: int,
    end: int,
) -> str:
    separators = (",", ",", ";", ";", ".", ".", "!", "!", "?", "?", "\n")
    clause_start = max(
        utterance.rfind(separator, 0, start) for separator in separators
    )
    clause_end_candidates = [
        position
        for separator in separators
        if (position := utterance.find(separator, end)) >= 0
    ]
    clause_end = (
        min(clause_end_candidates)
        if clause_end_candidates
        else len(utterance)
    )
    return utterance[clause_start + 1 : clause_end]

def _strategy_report_status_has_positive_assignment(
    utterance: str,
    *,
    value_start: int,
    value_end: int,
) -> bool:
    before = utterance[max(0, value_start - 32) : value_start]
    if re.search(
        r"(?:Set as|Set As|For|Adopt|Use|Use|Selection|Assign As|It's...)\s*$|"
        r"(?<![A-Za-z0-9_])(?:set\s+to|use|as|instead)(?![A-Za-z0-9_])\s*$",
        before,
        re.IGNORECASE,
    ):
        return True
    label_matches = tuple(_STRATEGY_REPORT_STATUS_LABEL_RE.finditer(before))
    if label_matches:
        tail = before[label_matches[-1].end() :]
        if re.fullmatch(
            r"\s*(?:(?:Settings|Set|Assign|Set|Freeze.)\s*)?"
            r"(?:(?:Yes|Yes.|Use|Adopt|Set as|Set As|=|:|:|is)\s*)?",
            tail,
            re.IGNORECASE,
        ):
            return True

    after = utterance[value_end : value_end + 24]
    return re.match(
        r"\s*(?:Version|Report)?\s*(?:(?:As|Set as|Set As|is)\s*)?"
        r"(?:(?:Report)?Status|(?<![A-Za-z0-9_])status(?![A-Za-z0-9_]))",
        after,
        re.IGNORECASE,
    ) is not None

def _strategy_report_status_shares_command(
    utterance: str,
    *,
    value_start: int,
    value_end: int,
    action_matches: Sequence[re.Match[str]],
) -> bool:
    for action in action_matches:
        between = utterance[
            min(action.start(), value_start) : max(action.end(), value_end)
        ]
        if re.search(r"[;;..!?!?\n]", between) is None:
            return True
    return False

def _strategy_report_status_span_is_negated(
    utterance: str,
    *,
    start: int,
) -> bool:
    prefix = utterance[max(0, start - 32) : start]
    return _STRATEGY_REPORT_STATUS_NEGATION_RE.search(prefix) is not None
