"""cross request-compiler handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
import json
import math
import re
from typing import Any
import unicodedata

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import StandardWorkflowRequestDraft
    from . import StrategyRequestCompilation
    from . import _AUTOMATIC_TREE_ASSET_ID_TOKEN_RE
    from . import _AUTOMATIC_TREE_LEAF_ACTION_CHAIN_RE
    from . import _AUTOMATIC_TREE_LEAF_LIFECYCLE_CHAIN_RE
    from . import _AUTOMATIC_TREE_LEAF_NEGATED_REASON_CLAUSE_RE
    from . import _AUTOMATIC_TREE_LEAF_POOL_CHAIN_RE
    from . import _AUTOMATIC_TREE_LEAF_RATIONALE_DECISION_SUBJECT_RE
    from . import _AUTOMATIC_TREE_LEAF_REASON_EXTREME_RE
    from . import _AUTOMATIC_TREE_LEAF_REASON_FORBIDDEN_OPERATION_RE
    from . import _AUTOMATIC_TREE_LEAF_REASON_RE
    from . import _AUTOMATIC_TREE_LEAF_REASON_REPLACEMENT_RE
    from . import _AUTOMATIC_TREE_LEAF_REQUEST_PUNCTUATION_RE
    from . import _AUTOMATIC_TREE_LEAF_WRITEBACK_CHAIN_RE
    from . import _automatic_tree_column_mention_resolution
    from . import _automatic_tree_column_mentions
    from . import _automatic_tree_follow_up_action_is_negated
    from . import _automatic_tree_follow_up_clauses
    from . import _automatic_tree_leaf_all_reason_values
    from . import _automatic_tree_leaf_explicit_reasons
    from . import _automatic_tree_leaf_rationale_is_allowed
    from . import _automatic_tree_span_is_negated
    from . import _clarification
    from . import _explicit_manual_breakpoint_bindings

_CROSS_MATRIX_TARGET_RE = re.compile(
    r"(?:Two-dimensional.|2\s*[dD])[^,,;;.\n]{0,24}(?:Cross|cross)|"
    r"(?:Cross|cross)[^,,;;.\n]{0,24}(?:Matrix|matrix)",
    re.IGNORECASE,
)

_CROSS_MATRIX_BUILD_RE = re.compile(
    r"(?:Build|Generate|Create|Calculate|Analysis|Production|Do it.)|"
    r"(?<![A-Za-z0-9_])(?:build|create|generate|compute|analy[sz]e|make)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_MATRIX_NEGATED_BUILD_RE = re.compile(
    r"(?:Don't.|Not anymore.|No need.|No, I'm fine.|Don't.|Ban)\s*(?:Build|Generate|Create|Calculate|Analysis|Production|Do it.)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never)\s+"
    r"(?:build|create|generate|compute|analy[sz]e|make)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_MATRIX_NONCOMMAND_RE = re.compile(
    r"[??]|"
    r"(?:Can you...|Can I?|Is it possible?|Is that okay?|Can you...|Do you want it?|Is it possible?|How's that?|What?|What?|"
    r"Assumptions|Suppose...|If|If|What if...|Presentation|Demonstration|Test|Example|Annotations|Explanation|Introduction|"
    r"Description|Tell me.|Presentation)"
    r"[^;;.\n]{0,220}(?:Two-dimensional.|2\s*[dD]|Cross|cross|matrix)|"
    r"(?:Yesterday.|Yesterday|Before|Before|Go on.|Last time.|Previous|Earlier|Once.|History|"
    r"Document|Report|Example:|Example|Original|Materials|The future.|In the future|Later|Later.|Later.|"
    r"Turn around.|Tomorrow.|The day after tomorrow.|Next week.|Next month|Next month|End of the month|And then...)"
    r"[^;;.\n]{0,220}(?:Build|Generate|Create|Calculate|Analysis|Two-dimensional.|Cross|cross|matrix)|"
    r"(?<![A-Za-z0-9_])(?:can\s+you|could\s+you|would\s+you|"
    r"is\s+it\s+possible|what\s+if|suppose|assuming|hypothetically|"
    r"how\s+to|demonstrate|demo|test|example|yesterday|previously|"
    r"earlier|last\s+time|in\s+the\s+future|later|tomorrow|"
    r"next\s+(?:week|month)|when|once|after)"
    r"[^;.!?\n]{0,220}(?:build|create|generate|compute|analy[sz]e|"
    r"cross|matrix)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_MATRIX_POSTPONED_CANCELLATION_RE = re.compile(
    r"(?:^|[,,;;..!??!]\s*)(?:Wait.|Wait a minute.|Forget it.|Let's do it.|I'm sorry.|"
    r"Cancel(?:Yeah.|Yes.)?|Withdrawn.|Undo|Stop|Not yet.(?:Yes.)?|Not for now.(?:Yes.)?|"
    r"Don't do it.(?:Yes.)?|Don't do it.(?:Yes.)?|Not implemented(?:Yes.)?)(?:[,,..!!??]?\s*)$|"
    r"(?:^|[,;.!?]\s*)(?:never\s+mind|forget\s+it|scratch\s+that|"
    r"cancel|abort|withdraw|stop|do(?:n't|\s+not)\s+(?:do|execute)\s+it)"
    r"(?:[,!.?]?\s*)$",
    re.IGNORECASE,
)

_CROSS_MATRIX_CONTROL_REWRITE_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|Don't use it.|Do Not Use|Exclude|Remove|Get rid of it.)\s*(?:Use|Use)?"
    r"[^,,;;.\n]{0,32}(?:Equivalent|Equal number|Bits|& Equal|Wait for the width.|Carfone.|"
    r"Decision Tree|Category(?:Equivalent)?Box|quantile|equal[-_\s]*(?:frequency|width)|"
    r"chi[-_\s]*merge|chimerge|tree|categorical)|"
    r"(?:Change|Replace with|For|Replace|Not)|"
    r"(?<![A-Za-z0-9_])(?:instead\s+of|switch\s+to|change\s+to)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_MATRIX_COMMAND_CLAUSE_RE = re.compile(r"[^;;..!!??\n]+")

_CROSS_MATRIX_BIN_COUNT_RE = re.compile(
    r"(?<![A-Za-z0-9_.])(?P<count>\d{1,2})\s*(?:individual)?(?:Box|bins?)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_MATRIX_MIN_BIN_PCT_RE = re.compile(
    r"(?:Minimum box share|min[_\s-]*bin[_\s-]*(?:pct|share))\s*"
    r"(?:=|:|:|Yes)?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<pct>%?)",
    re.IGNORECASE,
)

_CROSS_MATRIX_SENTINEL_LABEL_RE = re.compile(
    r"(?:Sentry.(?:Value)?|Special value|sentinel(?:[_\s-]*values?)?)",
    re.IGNORECASE,
)

_CROSS_MATRIX_SENTINEL_STOP_RE = re.compile(
    r"[,,]\s*(?=(?:Minimum box share|min[_\s-]*bin|Amount released|Amount of letter|Amount borrowed|"
    r"Overdue amounts|Bad debt amount|Amount of loss|loan[_\s-]*amount|"
    r"overdue[_\s-]*amount|[xXyY]\s*Axis|Two axes.|Every(?:individual)?Axis|Target boxes))",
    re.IGNORECASE,
)

_CROSS_MATRIX_SENTINEL_NUMBER_RE = re.compile(
    r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
)

_CROSS_MATRIX_FOLLOW_UP_RE = re.compile(
    r"(?:Choose(?:Choice|Medium)?Grill|Piles into pool|Add Policy Pool|Into the pool.|Accepted|Deployment|Online.|Production|"
    r"Write back|Back up.|Generate(?:Python|SQL|Code)|"
    r"(?<![A-Za-z0-9_])(?:select\s+cells?|add\s+to\s+(?:strategy\s+)?pool|"
    r"adopt|deploy|write[-\s]*back|generate\s+(?:python|sql|code))"
    r"(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_CROSS_SEARCH_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])cross-search-[0-9a-f]{32}(?![A-Za-z0-9_-])"
)

_CROSS_PAIR_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])cross-pair-[0-9a-f]{32}(?![A-Za-z0-9_-])"
)

_CROSS_SEARCH_INTENT_RE = re.compile(
    r"(?:Search|Find|Search|Search|Enumeration|Filter|Comparison)"
    r"[^,,;;.\n]{0,64}(?:Cross|Cross)(?:\s*Matrix|Matrix)?"
    r"[^,,;;.\n]{0,32}(?:Group|Candidates|Characteristics are right.|pair)?|"
    r"(?:Cross|Cross)(?:\s*Matrix|Matrix)?"
    r"[^,,;;.\n]{0,48}(?:Group|Candidates|Characteristics are right.|pair)"
    r"[^,,;;.\n]{0,32}(?:Search|Find|Search|Enumeration|Filter|Comparison)|"
    r"(?<![A-Za-z0-9_])(?:search|find|enumerate|screen|compare)"
    r"[^;.!?\n]{0,64}cross(?:\s+matrix)?(?:\s+(?:candidate|feature))?"
    r"(?:\s+pairs?)?(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_SEARCH_SELECTION_INTENT_RE = re.compile(
    r"(?:Build|Physicalization|Generate|Create)[^;;.\n]{0,80}"
    r"(?:Cross|Cross|Search(?:Result|Evidence)|Group|Candidates)|"
    r"(?:Cross|Cross|Search(?:Result|Evidence)|Group)"
    r"[^;;.\n]{0,80}(?:Build|Physicalization|Generate|Create)|"
    r"(?<![A-Za-z0-9_])(?:build|materialize|create|generate)"
    r"[^;.!?\n]{0,80}(?:cross|search\s+(?:result|evidence)|candidate)|"
    r"(?<![A-Za-z0-9_])(?:cross|search\s+(?:result|evidence))"
    r"[^;.!?\n]{0,80}(?:build|materialize|create|generate)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_SEARCH_FEATURES_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:features?|feature[_\s-]*list|Characteristics(?:List)?)"
    r"\s*(?:=|:|:|Yes)\s*\[(?P<value>[^\]\n]{1,1000})\]",
    re.IGNORECASE,
)

_CROSS_SEARCH_MAX_PAIRS_RE = re.compile(
    r"(?<![A-Za-z0-9_])max[_\s-]*pairs?\s*(?:=|:|:|Yes)?\s*"
    r"(?P<value>\d{1,3})(?![A-Za-z0-9_])|"
    r"Most\s*(?:Evaluation|Search|Comparison|Enumeration)?\s*(?P<zh_value>\d{1,3})\s*"
    r"(?:individual|Group)?(?:Group|Characteristics are right.|pairs?)",
    re.IGNORECASE,
)

_CROSS_SEARCH_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:x_method|y_method|axis_methods?|methods?|"
    r"source_artifact_id|expected_artifact_content_hash|"
    r"expected_candidate_id|expected_evidence_hash|dataset_id|target_col|"
    r"candidate_asset|asset_hash|evidence_hash|pair_id|rank|winner|champion)"
    r"\s*(?:=|:|:)|"
    r"(?:Axis|Box)\s*(?:Methodology|method)\s*(?:=|:|:|Yes)|"
    r"(?:Work|Assets|Evidence|Dataset|Target column)\s*(?:ID|id|hash|Hash.)\s*(?:=|:|:|Yes)",
    re.IGNORECASE,
)

_CROSS_SEARCH_SELECTION_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:artifact_id|artifact_hash|asset_id|asset_hash|"
    r"content_hash|source_artifact_id|expected_[a-z0-9_]+|candidate_id|"
    r"evidence_hash|dataset_id|target_col|x_feature|x_method|y_feature|"
    r"y_method|axis_methods?|features?|max_pairs|rank|winner|champion)"
    r"\s*(?:=|:|:)|"
    r"(?<![A-Za-z0-9_-])candidate-asset-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])|"
    r"(?:Work|Assets|Evidence|Dataset|Target column|Axis|Boxing method|Rank)"
    r"\s*(?:ID|id|hash|Hash.|=|:|:|Yes)",
    re.IGNORECASE,
)

_CROSS_SEARCH_SELECTION_HEURISTIC_RE = re.compile(
    r"(?:I'm sorry.[One, two, three, four, five, six, seven, eight, nine hundred.\d]+Synchronising folder|First(?:individual|Synchronising folder)|I'd better.(?:It's...)?|"
    r"Best|Best|Champion.|Top\s*[-#]?\s*\d+|Rank|Name|Just now.(?:That.|This.|It's...)?|"
    r"above|This combination.|The combination.)|"
    r"(?<![A-Za-z0-9_])(?:winner|champion|first|best|top\s*[-#]?\s*\d+|"
    r"rank(?:ing)?|previous|that\s+one|this\s+one)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_SEARCH_RESEARCH_RE = re.compile(
    r"(?:Restart|Again.|Again.|Meanwhile...)\s*(?:Search|Find|Search|Enumeration|Filter|Comparison)"
    r"[^,,;;.\n]{0,48}(?:Cross|Cross)|"
    r"(?<![A-Za-z0-9_])(?:re-?search|search|find|enumerate|screen|compare)"
    r"[^,;.!?\n]{0,48}(?:again[^,;.!?\n]{0,16})?cross"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_SEARCH_FOLLOW_UP_RE = re.compile(
    r"(?:Build|Physicalization|Generate|Create|Selection|Select|Into the pool.|Add|Put it in.|Writing|Inclusion|"
    r"Set Actions|Apply|Accepted|Deployment|Online.|Production|Write back|Back up.)|"
    r"(?<![A-Za-z0-9_])(?:build|materialize|create|generate|select|choose|"
    r"add\s+to\s+(?:the\s+)?(?:strategy\s+)?pool|set\s+action|apply|"
    r"adopt|deploy|publish|write[- ]?back)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_SEARCH_SELECTION_FOLLOW_UP_RE = re.compile(
    r"(?:Into the pool.|Add|Put it in.|Writing|Inclusion|Modify(?:Policy pool|Rule pool|Pool)|Set Actions|"
    r"Apply|Accepted|Deployment|Online.|Production|Write back|Back up.)|"
    r"(?<![A-Za-z0-9_])(?:add\s+to\s+(?:the\s+)?(?:strategy\s+)?pool|"
    r"modify\s+(?:the\s+)?(?:strategy\s+)?pool|set\s+action|apply|adopt|"
    r"deploy|publish|write[- ]?back)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_SEARCH_NEGATION_PREFIX_RE = re.compile(
    r"(?:No, no.|Don't.|No, I'm fine.|No need.|No, I don't.|Not yet.|Not yet.|No, I won't.|Not anymore.|Don't.|Ban)\s*$|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|never|without)\s*$",
    re.IGNORECASE,
)

_CROSS_RULE_SUBJECT_RE = re.compile(
    r"(?:2|3)\s*[dD][^,,;;.\n]{0,24}(?:Cross|Cross)"
    r"[^,,;;.\n]{0,24}(?:Threshold)?Rule|"
    r"(?:Cross|Cross)[^,,;;.\n]{0,24}(?:Threshold|threshold)"
    r"[^,,;;.\n]{0,16}(?:Rule|rules?)|"
    r"(?:Cross|Cross)[^,,;;.\n]{0,16}(?:Rule|rules?)",
    re.IGNORECASE,
)

_CROSS_RULE_SEARCH_INTENT_RE = re.compile(
    r"(?:Search|Find|Digging|Enumeration|Filter|Explore)|"
    r"(?<![A-Za-z0-9_])(?:search|find|mine|enumerate|screen|explore)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_RULE_SEARCH_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])cross-rule-search-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_CROSS_RULE_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])cross-rule-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_CROSS_RULE_SELECTION_INTENT_RE = re.compile(
    r"(?:Build|Physicalization|Generate|Create)[^;;.\n]{0,80}(?:Cross|Cross|Rule|Candidates)|"
    r"(?:Cross|Cross|Rule|Search Results)[^;;.\n]{0,80}(?:Build|Physicalization|Generate|Create)|"
    r"(?<![A-Za-z0-9_])(?:build|materialize|create|generate)"
    r"[^;.!?\n]{0,80}(?:cross|rule|candidate)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_RULE_DIMENSION_RE = re.compile(
    r"(?<![A-Za-z0-9_])dimension\s*(?:=|:|:|Yes)?\s*(?P<value>[23])"
    r"(?![A-Za-z0-9_])|"
    r"(?P<zh_value>[23])\s*[dDV]",
    re.IGNORECASE,
)

_CROSS_RULE_MIN_LIFT_RE = re.compile(
    r"(?<![A-Za-z0-9_])min[_\s-]*lift\s*(?:=|:|:|Yes)?\s*"
    r"(?P<value>\d+(?:\.\d+)?)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_RULE_MIN_BAD_COUNT_RE = re.compile(
    r"(?<![A-Za-z0-9_])min[_\s-]*bad[_\s-]*count"
    r"\s*(?:=|:|:|Yes)?\s*(?P<value>\d+)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_RULE_MAX_HIT_SHARE_RE = re.compile(
    r"(?<![A-Za-z0-9_])max[_\s-]*hit[_\s-]*share"
    r"\s*(?:=|:|:|Yes)?\s*(?P<value>\d+(?:\.\d+)?)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_RULE_MIN_AMOUNT_LIFT_RE = re.compile(
    r"(?<![A-Za-z0-9_])min[_\s-]*amount[_\s-]*lift"
    r"\s*(?:=|:|:|Yes)?\s*(?P<value>null|none|\d+(?:\.\d+)?)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_RULE_MAX_TRIALS_RE = re.compile(
    r"(?<![A-Za-z0-9_])max[_\s-]*trials?"
    r"\s*(?:=|:|:|Yes)?\s*(?P<value>\d{1,5})(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_RULE_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:source_artifact_id|"
    r"expected_artifact_content_hash|expected_candidate_id|"
    r"expected_evidence_hash|dataset_id|target_col|thresholds?|directions?|"
    r"rule_id|rank|winner|champion|content_hash|artifact_id)"
    r"\s*(?:=|:|:)",
    re.IGNORECASE,
)

_CROSS_RULE_SELECTION_HEURISTIC_RE = re.compile(
    r"(?:I'm sorry.[One, two, three, four, five, six, seven, eight, nine hundred.\d]+Synchronising folder|First(?:individual|Synchronising folder|Article)|I'd better.(?:It's...)?|"
    r"Best|Best|Champion.|Top\s*[-#]?\s*\d+|Rank|Just now.(?:That.|This.|It's...)?|"
    r"above|This rule.|That rule.)|"
    r"(?<![A-Za-z0-9_])(?:winner|champion|first|best|top\s*[-#]?\s*\d+|"
    r"rank(?:ing)?|previous|that\s+one|this\s+one)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_METHOD_GROUNDING = {
    "equal_frequency": re.compile(
        r"(?:Equivalent|Equal number|Bits|quantile|equal[-_\s]*frequency)",
        re.IGNORECASE,
    ),
    "equal_width": re.compile(
        r"(?:& Equal|Wait for the width.|equal[-_\s]*width)",
        re.IGNORECASE,
    ),
    "chimerge": re.compile(r"(?:Carfone.|chi[-_\s]*merge|chimerge)", re.IGNORECASE),
    "tree": re.compile(r"(?:Decision Tree|tree)", re.IGNORECASE),
    "manual": re.compile(
        r"(?:Manual|Manual|manual)\s*(?:Box|Point|Breakpoints|breakpoints?)?",
        re.IGNORECASE,
    ),
    "categorical": re.compile(
        r"(?:Category Equivalent Box|Category Box|Equivalent Box|categorical)",
        re.IGNORECASE,
    ),
}

_CROSS_MATRIX_CELL_SELECTION_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])cross-matrix-cell-selection-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_CROSS_MATRIX_CELL_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])cross-cell-[0-9a-f]{32}(?![A-Za-z0-9_-])"
)

_CROSS_MATRIX_CELL_SELECTION_ACTION_RE = re.compile(
    r"(?:Physicalization|Solid|Select|Selection|Extract|References)"
    r"[^,,;;.\n]{0,24}(?:Grid|Cells|cell)|"
    r"(?:Grid|Cells|cell)"
    r"[^,,;;.\n]{0,24}(?:Physicalization|Solid|Select|Selection|Extract|References)|"
    r"(?<![A-Za-z0-9_])(?:materialize|select|pick|extract|reference)"
    r"(?:\s+the)?\s+(?:exact\s+)?cells?(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_MATRIX_CELL_SELECTION_VERB_RE = re.compile(
    r"(?:Physicalization|Solid|Select|Selection|Extract|References)|"
    r"(?<![A-Za-z0-9_])(?:materialize|select|pick|extract|reference)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_MATRIX_CELL_SELECTION_NEGATED_RE = re.compile(
    r"(?:Don't.|Not anymore.|No need.|No, I'm fine.|Don't.|Ban|Not|No, I'm not.)\s*"
    r"[^,,;;.\n]{0,160}(?:Physicalization|Solid|Select|Selection|Extract|References)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never)\s+"
    r"(?:materialize|select|pick|extract|reference)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_MATRIX_CELL_AMBIGUOUS_SELECTION_RE = re.compile(
    r"(?:I'd better.|Best|Best|Worst|Worst|High risk|Low risk|Risk highest|Risk lowest|"
    r"The highest rate of bad debts.|The worst rate of bad.|liftHighest|woeHighest|ivHighest|Front\s*\d+|Rank|Line|"
    r"(?<![A-Za-z0-9_])(?:best|worst|top[-\s]*\d+|highest|lowest|"
    r"riskiest|safest|rank(?:ed|ing)?)(?![A-Za-z0-9_]))"
    r"[^,,;;.\n]{0,32}(?:Grid|Cells|cells?)|"
    r"(?:Grid|Cells|cells?)[^,,;;.\n]{0,32}"
    r"(?:I'd better.|Best|Best|Worst|Worst|High risk|Low risk|Highest|Minimum|Rank|Line|"
    r"(?<![A-Za-z0-9_])(?:best|worst|top|highest|lowest|riskiest|safest|"
    r"rank(?:ed|ing)?)(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_CROSS_MATRIX_CELL_HEURISTIC_CONTROL_RE = re.compile(
    r"(?:Bad debt rate|Bad rate|Risk|lift|woe|iv|Percentage|Sample Volume|count|share|bad[-_\s]*rate)"
    r"[^,,;;.\n]{0,24}(?:>=|<=|>|<|Higher|Less than|Greater than|less than|Not less than|No more than|Threshold|Threshold)|"
    r"(?:>=|<=|>|<|Higher|Less than|Greater than|less than|Not less than|No more than|Threshold|Threshold)"
    r"[^,,;;.\n]{0,24}(?:Bad debt rate|Bad rate|Risk|lift|woe|iv|Percentage|Sample Volume|count|"
    r"share|bad[-_\s]*rate)",
    re.IGNORECASE,
)

_CROSS_MATRIX_CELL_NEGATED_FOLLOW_UP_RE = re.compile(
    r"(?:Yeah.\s*)?(?:Don't.|Not anymore.|No need.|No, I don't.|No, no.|Don't.|Ban)\s*(?:"
    r"(?:Add|Writing|Put it in.|Add)\s*(?:Policy pool|Rule pool|pool)|Into the pool.|"
    r"Settings?[^,,;;.\n]{0,12}(?:Actions|action)|"
    r"(?:Accepted|Deployment|Online.|Production|Write back|Back up.)"
    r"(?:(?:Yeah.|or|,|and)(?:No, no.|Don't.)?(?:Accepted|Deployment|Online.|Production|Write back|Back up.))*)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never)\s+(?:"
    r"add\s+(?:them?\s+)?to\s+(?:the\s+)?(?:strategy\s+)?pool|"
    r"set\s+(?:the\s+)?action|adopt|deploy|write[-\s]*back)"
    r"(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])without\s+(?:adding|adopting|deploying)"
    r"[^,,;;.\n]*(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_CROSS_MATRIX_CELL_ALLOWED_REQUEST_TOKEN_RE = re.compile(
    r"(?:Please.|Help me.|Trouble.|From|Yes.|- Put it on.|Will|Only|Only|Yeah.|and|and|But...(?:Yes.)?|But...|"
    r"One.|These.|Below|Assign|Precision|Complete|Two-dimensional.|Cross|Matrix|Candidates|Assets|Result|Medium|- Yes.|"
    r"Grid|Cells|Grill|Physicalization|Solid|Select|Selection|Extract|References|Pointer|Yes.|ID|id|"
    r"(?<![A-Za-z0-9_])(?:please|from|in|the|a|an|these|following|exact|"
    r"specified|cross|matrix|candidate|asset|result|cell|cells|materialize|"
    r"select|pick|extract|reference|pointer|only|and|but)(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

def _utterance_targets_cross_candidate_search(utterance: str) -> bool:
    """Reserve bounded Cross feature-pair search before explicit matrix build."""

    return (
        not _utterance_targets_cross_rule_search(utterance)
        and not _utterance_targets_cross_rule_selection(utterance)
        and not _utterance_targets_cross_search_selection(utterance)
        and _CROSS_SEARCH_INTENT_RE.search(utterance) is not None
    )

def _utterance_targets_cross_rule_search(utterance: str) -> bool:
    """Reserve bounded threshold-rule mining before Matrix pair routing."""

    return (
        not _utterance_targets_cross_rule_selection(utterance)
        and _CROSS_RULE_SUBJECT_RE.search(utterance) is not None
        and _CROSS_RULE_SEARCH_INTENT_RE.search(utterance) is not None
    )

def _utterance_targets_cross_rule_selection(utterance: str) -> bool:
    """Reserve one exact rule materialization before every Cross route."""

    return (
        _CROSS_RULE_SEARCH_ID_TOKEN_RE.search(utterance) is not None
        and _CROSS_RULE_ID_TOKEN_RE.search(utterance) is not None
        and _CROSS_RULE_SELECTION_INTENT_RE.search(utterance) is not None
    )

def _utterance_targets_cross_search_selection(utterance: str) -> bool:
    """Reserve exact search-pair materialization before search/build routes."""

    return (
        _CROSS_SEARCH_ID_TOKEN_RE.search(utterance) is not None
        and _CROSS_PAIR_ID_TOKEN_RE.search(utterance) is not None
        and _CROSS_SEARCH_SELECTION_INTENT_RE.search(utterance) is not None
    )

def _cross_search_has_positive_follow_up(utterance: str) -> bool:
    """Ignore explicit negative disclaimers while rejecting chained actions."""

    return _cross_search_pattern_has_positive(
        utterance,
        _CROSS_SEARCH_FOLLOW_UP_RE,
    )

def _cross_search_pattern_has_positive(
    utterance: str,
    pattern: re.Pattern[str],
) -> bool:
    for match in pattern.finditer(utterance):
        prefix = utterance[max(0, match.start() - 20) : match.start()]
        local_start = max(
            prefix.rfind(separator)
            for separator in (",", ",", ";", ";", ".", ".", "!", "!", "?", "?")
        )
        if _CROSS_SEARCH_NEGATION_PREFIX_RE.search(
            prefix[local_start + 1 :]
        ) is None:
            return True
    return False

def _cross_search_selection_has_positive_research(utterance: str) -> bool:
    """Search-like substrings inside exact pointer ids are not new commands."""

    scrubbed = _CROSS_SEARCH_ID_TOKEN_RE.sub(
        lambda match: " " * len(match.group(0)),
        utterance,
    )
    scrubbed = _CROSS_PAIR_ID_TOKEN_RE.sub(
        lambda match: " " * len(match.group(0)),
        scrubbed,
    )
    return _CROSS_SEARCH_RESEARCH_RE.search(scrubbed) is not None

def _utterance_targets_cross_matrix(utterance: str) -> bool:
    if (
        _utterance_targets_cross_rule_search(utterance)
        or _utterance_targets_cross_rule_selection(utterance)
    ):
        return False
    without_selection_ids = _CROSS_MATRIX_CELL_SELECTION_ID_TOKEN_RE.sub(
        " ", utterance
    )
    return _CROSS_MATRIX_TARGET_RE.search(without_selection_ids) is not None

def _utterance_targets_cross_matrix_cell_selection(utterance: str) -> bool:
    has_pointer_ids = (
        _AUTOMATIC_TREE_ASSET_ID_TOKEN_RE.search(utterance) is not None
        and _CROSS_MATRIX_CELL_ID_TOKEN_RE.search(utterance) is not None
    )
    if (
        _CROSS_MATRIX_CELL_SELECTION_ID_TOKEN_RE.search(utterance) is not None
        and not has_pointer_ids
    ):
        return False
    explicit_cell_action = (
        _CROSS_MATRIX_CELL_SELECTION_ACTION_RE.search(utterance) is not None
    )
    return (explicit_cell_action and _utterance_targets_cross_matrix(utterance)) or (
        has_pointer_ids
        and _CROSS_MATRIX_CELL_SELECTION_VERB_RE.search(utterance) is not None
    )

def _cross_positive_command_clause_spans(
    utterance: str,
) -> tuple[tuple[int, int], ...]:
    """Return clauses that contain one positive Cross build request."""

    spans: list[tuple[int, int]] = []
    for clause_match in _CROSS_MATRIX_COMMAND_CLAUSE_RE.finditer(utterance):
        clause = clause_match.group(0)
        if (
            _CROSS_MATRIX_TARGET_RE.search(clause) is not None
            and _CROSS_MATRIX_BUILD_RE.search(clause) is not None
            and _CROSS_MATRIX_NEGATED_BUILD_RE.search(clause) is None
        ):
            spans.append(clause_match.span())
    return tuple(spans)

def _cross_mention_is_within(
    start: int,
    end: int,
    command_span: tuple[int, int],
) -> bool:
    return command_span[0] <= start and end <= command_span[1]

def _cross_spans_are_near(
    utterance: str,
    first: tuple[int, int],
    second: tuple[int, int],
    *,
    maximum_gap: int = 32,
) -> bool:
    first_start, first_end = first
    second_start, second_end = second
    if first_end <= second_start:
        gap_start, gap_end = first_end, second_start
    elif second_end <= first_start:
        gap_start, gap_end = second_end, first_start
    else:
        gap_start = gap_end = max(first_start, second_start)
    return (
        gap_end - gap_start <= maximum_gap
        and not any(
            separator in utterance[gap_start:gap_end]
            for separator in (";", ";", ".", "\n")
        )
    )

def _cross_method_mentions(
    utterance: str,
) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        sorted(
            (
                (method, match.start(), match.end())
                for method, pattern in _CROSS_METHOD_GROUNDING.items()
                for match in pattern.finditer(utterance)
            ),
            key=lambda item: (item[1], item[2], item[0]),
        )
    )

def _cross_axis_method_is_grounded(
    utterance: str,
    *,
    feature: str,
    method: str,
    whitelist: Sequence[str],
    shared_method: bool,
    command_span: tuple[int, int],
) -> bool:
    feature_spans = [
        (start, end)
        for start, end, column in _automatic_tree_column_mentions(
            utterance,
            whitelist,
        )
        if column == feature
        and _cross_mention_is_within(start, end, command_span)
        and not _automatic_tree_span_is_negated(
            utterance,
            start=start,
            end=end,
        )
    ]
    method_spans = [
        (start, end)
        for observed_method, start, end in _cross_method_mentions(utterance)
        if observed_method == method
        and _cross_mention_is_within(start, end, command_span)
        and not _automatic_tree_span_is_negated(
            utterance,
            start=start,
            end=end,
        )
    ]
    if shared_method:
        return bool(feature_spans and method_spans)
    return any(
        _cross_spans_are_near(
            utterance,
            (feature_start, feature_end),
            (method_start, method_end),
        )
        for feature_start, feature_end in feature_spans
        for method_start, method_end in method_spans
    )

def _cross_amount_column_is_grounded(
    utterance: str,
    *,
    column: str,
    field: str,
    whitelist: Sequence[str],
    command_span: tuple[int, int],
) -> bool:
    label_pattern = (
        re.compile(r"(?:Loans|Letters|Borrowing)Amount|loan[_\s-]*amount", re.IGNORECASE)
        if field == "loan_amount_col"
        else re.compile(r"(?:Overdue|Bad debts.|Losses)Amount|overdue[_\s-]*amount", re.IGNORECASE)
    )
    column_spans = [
        (start, end)
        for start, end, observed in _automatic_tree_column_mentions(
            utterance,
            whitelist,
        )
        if observed == column and _cross_mention_is_within(start, end, command_span)
    ]
    label_spans = [
        match.span()
        for match in label_pattern.finditer(utterance)
        if _cross_mention_is_within(match.start(), match.end(), command_span)
    ]
    return any(
        _cross_spans_are_near(utterance, column_span, label_span, maximum_gap=48)
        for column_span in column_spans
        for label_span in label_spans
    )

def _cross_sentinel_literal(token: str) -> str | int | float | None:
    """Parse one explicitly written sentinel without guessing its JSON type."""

    value = token.strip()
    if not value:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        if value[0] == '"':
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return None
            return decoded if isinstance(decoded, str) else None
        inner = value[1:-1]
        return inner if "\\" not in inner else None
    if _CROSS_MATRIX_SENTINEL_NUMBER_RE.fullmatch(value) is not None:
        try:
            parsed = float(value) if any(mark in value.lower() for mark in (".", "e")) else int(value)
        except ValueError:
            return None
        if isinstance(parsed, float) and not math.isfinite(parsed):
            return None
        return parsed
    if re.fullmatch(r"[^\s,,,/;;..!!??]+", value) is not None:
        return value
    return None

def _cross_explicit_sentinel_values(
    utterance: str,
    *,
    command_span: tuple[int, int],
) -> tuple[tuple[str | int | float, ...] | None, bool]:
    """Return the exact sentinel sequence named in the positive command.

    ``None`` means no sentinel control was present. The boolean marks syntax that
    cannot be interpreted without guessing, which must fail closed.
    """

    command = utterance[command_span[0] : command_span[1]]
    labels = tuple(_CROSS_MATRIX_SENTINEL_LABEL_RE.finditer(command))
    if not labels:
        return None, False
    if len(labels) != 1:
        return (), True
    label = labels[0]
    prefix = command[: label.start()]
    reverse = re.search(r"(?:As|Consider|Consider|Press)\s*$", prefix)
    if reverse is not None:
        start = max(
            prefix.rfind(",", 0, reverse.start()),
            prefix.rfind(",", 0, reverse.start()),
        )
        body = prefix[start + 1 : reverse.start()]
    else:
        body = command[label.end() :]
        body = re.sub(
            r"^\s*(?:=|:|:|Yes|Yes.|Including|Organisation|Adopt|Use|Use)\s*",
            "",
            body,
        )
        stop = _CROSS_MATRIX_SENTINEL_STOP_RE.search(body)
        if stop is not None:
            body = body[: stop.start()]
    body = body.strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body:
        return (), True
    raw_tokens = re.split(r"\s*(?:,|,|,|/|and|and|and|\band\b)\s*", body)
    if not raw_tokens or any(not token for token in raw_tokens):
        return (), True
    values: list[str | int | float] = []
    identities: set[str] = set()
    for token in raw_tokens:
        value = _cross_sentinel_literal(token)
        if value is None:
            return (), True
        identity = json.dumps(
            [type(value).__name__, value],
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        if identity in identities:
            return (), True
        identities.add(identity)
        values.append(value)
    return tuple(values), False

def _cross_analysis_controls_not_grounded(
    utterance: str,
    *,
    inputs: Mapping[str, Any],
    whitelist: Sequence[str],
    command_span: tuple[int, int],
) -> tuple[str, ...]:
    missing: list[str] = []
    bin_mentions = tuple(_CROSS_MATRIX_BIN_COUNT_RE.finditer(utterance))
    if any(
        not _cross_mention_is_within(match.start(), match.end(), command_span)
        for match in bin_mentions
    ):
        missing.append("bin_count")
    observed_bin_counts = {int(match.group("count")) for match in bin_mentions}
    if observed_bin_counts:
        if observed_bin_counts != {inputs["bin_count"]}:
            missing.append("bin_count")
    elif inputs["bin_count"] != 10:
        missing.append("bin_count")

    min_pct_mentions = tuple(_CROSS_MATRIX_MIN_BIN_PCT_RE.finditer(utterance))
    if any(
        not _cross_mention_is_within(match.start(), match.end(), command_span)
        for match in min_pct_mentions
    ):
        missing.append("min_bin_pct")
    observed_min_pcts = {
        float(match.group("value")) / (100.0 if match.group("pct") else 1.0)
        for match in min_pct_mentions
    }
    if observed_min_pcts:
        if len(observed_min_pcts) != 1 or not math.isclose(
            next(iter(observed_min_pcts)),
            float(inputs["min_bin_pct"]),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            missing.append("min_bin_pct")
    elif not math.isclose(
        float(inputs["min_bin_pct"]),
        0.02,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        missing.append("min_bin_pct")

    for field in ("loan_amount_col", "overdue_amount_col"):
        if field in inputs and not _cross_amount_column_is_grounded(
            utterance,
            column=str(inputs[field]),
            field=field,
            whitelist=whitelist,
            command_span=command_span,
        ):
            missing.append(field)
    observed_sentinels, sentinel_syntax_ambiguous = _cross_explicit_sentinel_values(
        utterance,
        command_span=command_span,
    )
    expected_sentinels = tuple(inputs["sentinel_values"])
    if observed_sentinels is None:
        if expected_sentinels:
            missing.append("sentinel_values")
    else:
        observed_identities = {
            json.dumps(
                [type(value).__name__, value],
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            for value in observed_sentinels
        }
        expected_identities = {
            json.dumps(
                [type(value).__name__, value],
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            for value in expected_sentinels
        }
        if sentinel_syntax_ambiguous or observed_identities != expected_identities:
            missing.append("sentinel_values")
    observed_breakpoints, breakpoint_syntax_ambiguous = (
        _explicit_manual_breakpoint_bindings(
            utterance,
            whitelist=whitelist,
            command_span=command_span,
        )
    )
    expected_breakpoints = inputs.get("manual_breakpoints", {})
    if (
        breakpoint_syntax_ambiguous
        or observed_breakpoints != expected_breakpoints
    ):
        missing.append("manual_breakpoints")
    return tuple(dict.fromkeys(missing))

def _ground_cross_matrix_analysis(
    utterance: str,
    result: StrategyRequestCompilation,
    *,
    whitelist: tuple[str, ...],
) -> StrategyRequestCompilation:
    """Require an explicit positive 2D matrix command and two grounded axes."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if _CROSS_MATRIX_NEGATED_BUILD_RE.search(utterance) is not None:
        return _clarification(
            "The original denied 2D.Cross Matrix Build, so this time it won't be executed.",
            code="cross_matrix_build_intent_negated",
            fields=("build_intent",),
        )
    if (
        _CROSS_MATRIX_NONCOMMAND_RE.search(utterance) is not None
        or _CROSS_MATRIX_POSTPONED_CANCELLATION_RE.search(utterance) is not None
    ):
        return _clarification(
            "The current words are words, assumptions./The future./The history, demonstration or withdrawal of the text at the end of the sentence is not a good idea."
            "It can't be considered as immediate 2D.Cross Matrix . Please repeat this one-off"
            "Two sequenced axes to be constructed, each compartmented method and clear analytical parameters.",
            code="cross_matrix_positive_command_required",
            fields=("build_intent",),
        )
    command_spans = _cross_positive_command_clause_spans(utterance)
    if not command_spans:
        return _clarification(
            "Please send out a positive 2D.Cross Matrix building commands;viewing, describing or"
            "The hypothetical request does not create a candidate asset.",
            code="cross_matrix_build_intent_required",
            fields=("build_intent",),
        )
    if len(command_spans) != 1:
        return _clarification(
            "A request can only include a 2D immediate execution.Cross Matrix (a) Build sub-words;"
            "Please break down the various axes into separate requests.",
            code="cross_matrix_single_command_required",
            fields=("build_intent",),
        )
    command_span = command_spans[0]
    if (
        len(
            tuple(
                _CROSS_MATRIX_TARGET_RE.finditer(
                    utterance[command_span[0] : command_span[1]]
                )
            )
        )
        != 1
    ):
        return _clarification(
            "One request can only be made for one 2D.Cross Matrix;Please unplug multiple matrices.",
            code="cross_matrix_single_command_required",
            fields=("build_intent",),
        )
    if _CROSS_MATRIX_FOLLOW_UP_RE.search(utterance) is not None:
        return _clarification(
            "This round can only produce 2D.Cross Matrix anddevelopment evidence."
            "Selection, entry, code, writing back, adoption or deployment must be broken down into subsequent requests.",
            code="cross_matrix_single_step_required",
            fields=("next_action",),
        )
    if _CROSS_MATRIX_CONTROL_REWRITE_RE.search(utterance) is not None:
        return _clarification(
            "The original phrase contains the axis that were rejected or subsequently rewritten/Box control. Please keep only the final set"
            "The sequenced axis and boxing method is then re-transmitted and the platform does not select the old and new values for you.",
            code="cross_matrix_controls_rewritten",
            fields=("x_feature", "x_method", "y_feature", "y_method"),
        )

    mentions, ambiguous = _automatic_tree_column_mention_resolution(
        utterance,
        whitelist,
    )
    if ambiguous:
        return _clarification(
            "Cross-axis fields overlap or case-segregation in original text, write two in separator"
            "Accurate listing:" + ",".join(ambiguous) + ".",
            code="cross_matrix_axes_ambiguous",
            fields=ambiguous,
        )
    if any(
        not _cross_mention_is_within(start, end, command_span)
        for start, end, _column in mentions
    ):
        return _clarification(
            "Two-dimensional.Cross Matrix , the field and analysis column must be located in the only positive construction sub-rule;"
            "History, quotation, denial or other sub-statements are not consumed.",
            code="cross_matrix_controls_outside_command",
            fields=("x_feature", "y_feature"),
        )
    if any(
        _automatic_tree_span_is_negated(
            utterance,
            start=start,
            end=end,
        )
        for start, end, _column in mentions
    ):
        return _clarification(
            "The original phrase contains the negative field control. Please retain only the two orderly axes that are ultimately used.",
            code="cross_matrix_controls_rewritten",
            fields=("x_feature", "y_feature"),
        )

    positive_mentions = [
        (start, end, column)
        for start, end, column in mentions
    ]
    expected_columns = {inputs["x_feature"], inputs["y_feature"]}
    expected_columns.update(
        inputs[field]
        for field in ("loan_amount_col", "overdue_amount_col")
        if field in inputs
    )
    observed_columns = {column for _start, _end, column in positive_mentions}
    if not {inputs["x_feature"], inputs["y_feature"]} <= observed_columns:
        return _clarification(
            "Please clearly write two different cross-axis fields in the original language; the platform will not be listed from the white list"
            "Fill or guess the second axis.",
            code="cross_matrix_axes_not_grounded",
            fields=("x_feature", "y_feature"),
        )
    if observed_columns != expected_columns:
        return _clarification(
            "Please write only one clear axis to the stated amount column in the only construction sub-statement;"
            "The platform will not select two axes from the additional field, nor will it leave out the user-nominator field.",
            code="cross_matrix_axes_not_unique",
            fields=("x_feature", "y_feature"),
        )

    axis_order: list[str] = []
    for _start, _end, column in positive_mentions:
        if (
            column in {inputs["x_feature"], inputs["y_feature"]}
            and column not in axis_order
        ):
            axis_order.append(column)
    if axis_order != [inputs["x_feature"], inputs["y_feature"]]:
        return _clarification(
            "MatrixX/Y The direction must be consistent with the order of the first appearance of the two axes in the original language;"
            "Platform doesn't make models any different after they're transferred.asset hash.",
            code="cross_matrix_axis_order_not_grounded",
            fields=("x_feature", "y_feature"),
        )

    method_mentions = _cross_method_mentions(utterance)
    if any(
        not _cross_mention_is_within(start, end, command_span)
        for _method, start, end in method_mentions
    ):
        return _clarification(
            "The boxing method for both axes must be in the only positive construction sub-rule.",
            code="cross_matrix_controls_outside_command",
            fields=("x_method", "y_method"),
        )
    if any(
        _automatic_tree_span_is_negated(
            utterance,
            start=start,
            end=end,
        )
        for _method, start, end in method_mentions
    ):
        return _clarification(
            "The original phrase contains the negative boxing method. Please retain only the method used.",
            code="cross_matrix_controls_rewritten",
            fields=("x_method", "y_method"),
        )
    if {method for method, _start, _end in method_mentions} != {
        inputs["x_method"],
        inputs["y_method"],
    }:
        return _clarification(
            "(a) The compartmentalization method in the original language is not unique or inconsistent with the draft structured approach;"
            "The platform will not complete, replace or omit methods.",
            code="cross_matrix_methods_not_grounded",
            fields=("x_method", "y_method"),
        )

    shared_method = inputs["x_method"] == inputs["y_method"]
    missing_methods = [
        field
        for field, feature_field in (
            ("x_method", "x_feature"),
            ("y_method", "y_feature"),
        )
        if not _cross_axis_method_is_grounded(
            utterance,
            feature=inputs[feature_field],
            method=inputs[field],
            whitelist=whitelist,
            shared_method=shared_method,
            command_span=command_span,
        )
    ]
    if missing_methods:
        return _clarification(
            "Please specify the compartment method used for each of the two axes; the same method can be described once, the hybrid method"
            "The platform will not select a method for you.",
            code="cross_matrix_methods_not_grounded",
            fields=tuple(missing_methods),
        )
    missing_analysis_controls = _cross_analysis_controls_not_grounded(
        utterance,
        inputs=inputs,
        whitelist=whitelist,
        command_span=command_span,
    )
    if missing_analysis_controls:
        return _clarification(
            "Target boxes, minimum box percentage, value line and sentry values can only be stated in the original language;"
            "The platform default is used only when not specified and cannot be selected by the model.",
            code="cross_matrix_analysis_controls_not_grounded",
            fields=missing_analysis_controls,
        )
    return result

def _ground_cross_rule_search(
    utterance: str,
    result: StrategyRequestCompilation,
    *,
    whitelist: tuple[str, ...],
) -> StrategyRequestCompilation:
    """Ground every bounded rule-search control in the current command."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if not _utterance_targets_cross_rule_search(utterance):
        return _clarification(
            "Please specify that search 2D/3D Cross Rule on thresholds, to be provided in the current request"
            "features,dimension,Four.constraints andmax_trials.",
            code="cross_rule_search_intent_required",
            fields=("search_intent",),
        )
    if (
        re.search(
            r"(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Cancel|Stop)"
            r"[^,,;;.\n]{0,32}(?:Search|Find|Digging|Enumeration|Filter)|"
            r"(?<![A-Za-z0-9_])(?:do\s+not|don't|cancel|stop)"
            r"[^,;.!?\n]{0,32}(?:search|find|mine|enumerate|screen)",
            utterance,
            re.IGNORECASE,
        )
        is not None
        or _CROSS_MATRIX_NONCOMMAND_RE.search(utterance) is not None
        or _CROSS_MATRIX_POSTPONED_CANCELLATION_RE.search(utterance) is not None
    ):
        return _clarification(
            "Cross The threshold rule search must be an immediate positive order for the current round.",
            code="cross_rule_search_positive_command_required",
            fields=("search_intent",),
        )
    if _cross_search_pattern_has_positive(
        utterance,
        _CROSS_SEARCH_FOLLOW_UP_RE,
    ):
        return _clarification(
            "This round only searchCross Rule on thresholds; build candidates, pool, application, adoption and"
            "Deployment must be requested separately.",
            code="cross_rule_search_single_step_required",
            fields=("next_action",),
        )
    if _CROSS_RULE_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Cross (a) The threshold rules search for only fields, dimensions, four operational constraints and pilot budgets;"
            "Threshold, direction,artifact/hash,rule/rank/winner Both are restored or calculated by the platform.",
            code="cross_rule_search_platform_binding_forbidden",
            fields=("platform_binding",),
        )

    bindings = tuple(_CROSS_SEARCH_FEATURES_RE.finditer(utterance))
    if len(bindings) != 1:
        return _clarification(
            "Please, please, just use it.features=[Field 1, Field 2, ...] Give 2 to 12"
            "Can not delete folder: %s: No such folder",
            code="cross_rule_search_controls_not_grounded",
            fields=("features",),
        )
    observed_features = [
        token.strip().strip("'\"`")
        for token in re.split(r"[,,]", bindings[0].group("value"))
        if token.strip()
    ]
    if (
        observed_features != list(inputs["features"])
        or len(set(observed_features)) != len(observed_features)
        or any(feature not in whitelist for feature in observed_features)
    ):
        return _clarification(
            "features A list of the only white list fields in the current command must be verbatim equal;"
            "Models may not be supplemented, subtracted or reordered.",
            code="cross_rule_search_controls_not_grounded",
            fields=("features",),
        )

    dimensions = {
        int(match.group("value") or match.group("zh_value"))
        for match in _CROSS_RULE_DIMENSION_RE.finditer(utterance)
    }
    constraints = inputs["constraints"]
    min_lifts = {
        float(match.group("value"))
        for match in _CROSS_RULE_MIN_LIFT_RE.finditer(utterance)
    }
    min_bad_counts = {
        int(match.group("value"))
        for match in _CROSS_RULE_MIN_BAD_COUNT_RE.finditer(utterance)
    }
    max_hit_shares = {
        float(match.group("value"))
        for match in _CROSS_RULE_MAX_HIT_SHARE_RE.finditer(utterance)
    }
    raw_amount_lifts = {
        match.group("value").casefold()
        for match in _CROSS_RULE_MIN_AMOUNT_LIFT_RE.finditer(utterance)
    }
    amount_lifts = {
        None if value in {"null", "none"} else float(value)
        for value in raw_amount_lifts
    }
    max_trials = {
        int(match.group("value"))
        for match in _CROSS_RULE_MAX_TRIALS_RE.finditer(utterance)
    }
    if (
        dimensions != {inputs["dimension"]}
        or min_lifts != {float(constraints["min_lift"])}
        or min_bad_counts != {constraints["min_bad_count"]}
        or max_hit_shares != {float(constraints["max_hit_share"])}
        or amount_lifts != {constraints["min_amount_lift"]}
        or max_trials != {inputs["max_trials"]}
    ):
        return _clarification(
            "dimension,min_lift,min_bad_count,max_hit_share,"
            "min_amount_lift andmax_trials It must be clear and unique in the current order;"
            "The model cannot add default values or rewrite the constraint.",
            code="cross_rule_search_controls_not_grounded",
            fields=(
                "dimension",
                "constraints",
                "max_trials",
            ),
        )
    return result

def _ground_cross_rule_candidate_build(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Ground one exact search/rule pointer without heuristic selection."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if not _utterance_targets_cross_rule_selection(utterance):
        return _clarification(
            "Please provide a complete picture in the request for independence.cross-rule-search ID,A complete"
            " cross-rule ID,The project is based on a project called \"Counter-Wide\" and explicitly requires the building of candidates.",
            code="cross_rule_selection_intent_required",
            fields=("build_intent", "search_id", "rule_id"),
        )
    if _CROSS_RULE_SELECTION_HEURISTIC_RE.search(utterance) is not None:
        return _clarification(
            "Please take a full word for word.search_id andrule_id;The platform won't consume number one."
            "Best, champion,Top N,Rank or \"just now.\"",
            code="cross_rule_selection_explicit_ids_required",
            fields=("search_id", "rule_id"),
        )
    if (
        _CROSS_MATRIX_NEGATED_BUILD_RE.search(utterance) is not None
        or _CROSS_MATRIX_NONCOMMAND_RE.search(utterance) is not None
        or _CROSS_MATRIX_POSTPONED_CANCELLATION_RE.search(utterance) is not None
    ):
        return _clarification(
            "Cross The rule candidate must be a positive one-step order immediately executed on the current round.",
            code="cross_rule_selection_positive_command_required",
            fields=("build_intent",),
        )
    if _cross_search_pattern_has_positive(
        utterance,
        _CROSS_SEARCH_SELECTION_FOLLOW_UP_RE,
    ):
        return _clarification(
            "This round can only be built with one accuracyCross Rule candidates; access to pool, set-up actions, applications,"
            "Additional requests for acceptance and deployment are required.",
            code="cross_rule_selection_single_step_required",
            fields=("next_action",),
        )
    search_ids = tuple(
        match.group(0)
        for match in _CROSS_RULE_SEARCH_ID_TOKEN_RE.finditer(utterance)
    )
    rule_ids = tuple(
        match.group(0)
        for match in _CROSS_RULE_ID_TOKEN_RE.finditer(utterance)
    )
    if (
        search_ids != (inputs["search_id"],)
        or rule_ids != (inputs["rule_id"],)
    ):
        return _clarification(
            "Cross Ruled candidate build must be provided word for word and only completesearch_id "
            "With a completerule_id.",
            code="cross_rule_selection_ids_not_grounded",
            fields=("search_id", "rule_id"),
        )
    reason = inputs.get("selection_reason")
    if reason is not None:
        labeled = re.search(
            r"(?:Reason for selection|Rationale|Reason|Annotations|selection[_\s-]*reason)"
            r"\s*(?:=|:|:|Yes)\s*(?P<reason>[^;;.\n]{1,500})",
            utterance,
            re.IGNORECASE,
        )
        if labeled is None or " ".join(
            unicodedata.normalize("NFC", labeled.group("reason")).split()
        ) != reason:
            return _clarification(
                "selection_reason Only verbatim when the current command is visible.",
                code="cross_rule_selection_reason_not_grounded",
                fields=("selection_reason",),
            )
    return result

def _ground_cross_matrix_candidate_search(
    utterance: str,
    result: StrategyRequestCompilation,
    *,
    whitelist: tuple[str, ...],
) -> StrategyRequestCompilation:
    """Prove the bounded feature universe and pair budget came from this turn."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if not _utterance_targets_cross_candidate_search(utterance):
        return _clarification(
            "Please make sure you search.Cross Matrix Feature combination and provided in current request"
            "features=[...] andmax_pairs.",
            code="cross_search_intent_required",
            fields=("search_intent",),
        )
    if (
        re.search(
            r"(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Cancel|Stop)"
            r"[^,,;;.\n]{0,32}(?:Search|Find|Search|Enumeration|Filter|Comparison)|"
            r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|cancel|stop)"
            r"[^,;.!?\n]{0,32}(?:search|find|enumerate|screen|compare)",
            utterance,
            re.IGNORECASE,
        )
        is not None
        or _CROSS_MATRIX_NONCOMMAND_RE.search(utterance) is not None
        or _CROSS_MATRIX_POSTPONED_CANCELLATION_RE.search(utterance) is not None
    ):
        return _clarification(
            "Cross Matrix Automatic group search must be an immediate affirmative order for the current round;"
            "Question, denial, assumptions, history/The search will not be started if the future description or end-of-the-word revocation is not available.",
            code="cross_search_positive_command_required",
            fields=("search_intent",),
        )
    if _cross_search_has_positive_follow_up(utterance):
        return _clarification(
            "This round only searchCross Matrix characteristics grouping;building or selecting candidates, entering pools,"
            "Applications, adoption and deployment must be subject to separate requests.",
            code="cross_search_single_step_required",
            fields=("next_action",),
        )
    if _CROSS_SEARCH_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Cross Automatically search only acceptedfeatures andmax_pairs;Axis methodology, candidate assets,"
            "artifact/hash,pair/rank/winner Both are restored or calculated by the platform and cannot be injected.",
            code="cross_search_platform_binding_forbidden",
            fields=("platform_binding",),
        )

    bindings = tuple(_CROSS_SEARCH_FEATURES_RE.finditer(utterance))
    if len(bindings) != 1:
        return _clarification(
            "Please, please, just use it.features=[Field 1, Field 2, ...] Explicitly give 2 to 20"
            "candidate field; the platform will not fill or select fields for you from the context.",
            code="cross_search_controls_not_grounded",
            fields=("features",),
        )
    raw_tokens = re.split(r"[,,]", bindings[0].group("value"))
    observed_features = [
        token.strip().strip("'\"`")
        for token in raw_tokens
        if token.strip()
    ]
    expected_features = list(inputs["features"])
    if (
        len(observed_features) != len(expected_features)
        or observed_features != expected_features
        or len(set(observed_features)) != len(observed_features)
        or any(feature not in whitelist for feature in observed_features)
    ):
        return _clarification(
            "features Must be equal to 2 to 20 non-duplicate entries in the only list in the current command"
            "white list fields; models may not be supplemented, subtracted, reordered or used in target columns.",
            code="cross_search_controls_not_grounded",
            fields=("features",),
        )

    observed_max = {
        int(match.group("value") or match.group("zh_value"))
        for match in _CROSS_SEARCH_MAX_PAIRS_RE.finditer(utterance)
    }
    if observed_max != {int(inputs["max_pairs"])}:
        return _clarification(
            "max_pairs The integer number must be clearly stated in the current command and only written between 1 and 190;"
            "The platform will not allow models to supplement the default budget.",
            code="cross_search_controls_not_grounded",
            fields=("max_pairs",),
        )
    return result

def _ground_cross_matrix_candidate_build_from_search(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Ground one exact search/pair pointer pair in an independent turn."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if not _utterance_targets_cross_search_selection(utterance):
        return _clarification(
            "Please provide a complete copy of the follow-up independent requestCross search_id And a complete."
            "pair_id,The project is based on a project called \"Counter-Wide\" and explicitly requires the building of candidates.",
            code="cross_search_selection_intent_required",
            fields=("build_intent", "search_id", "pair_id"),
        )
    if (
        _CROSS_MATRIX_NEGATED_BUILD_RE.search(utterance) is not None
        or _CROSS_MATRIX_NONCOMMAND_RE.search(utterance) is not None
        or _CROSS_MATRIX_POSTPONED_CANCELLATION_RE.search(utterance) is not None
    ):
        return _clarification(
            "Cross The search result must be built with a positive one-step command immediately executed on the current round;"
            "Question, denial, assumptions, history/No candidate will be built for future description or end-of-story withdrawal.",
            code="cross_search_selection_positive_command_required",
            fields=("build_intent",),
        )
    if (
        _cross_search_selection_has_positive_research(utterance)
        or _cross_search_pattern_has_positive(
            utterance,
            _CROSS_SEARCH_SELECTION_FOLLOW_UP_RE,
        )
    ):
        return _clarification(
            "This round can only be from precision.search_id/pair_id Build OneCross Candidates;"
            "Research, pool, action setting, application, adoption, deployment or write-back must be done separately.",
            code="cross_search_selection_single_step_required",
            fields=("next_action",),
        )
    if _CROSS_SEARCH_SELECTION_HEURISTIC_RE.search(utterance) is not None:
        return _clarification(
            "Please take a full word for word.search_id andpair_id;Even if it's all there.pointer,"
            "The platform will not consume first place, best, champion,Top N,Rank or \"just now.\"",
            code="cross_search_selection_explicit_ids_required",
            fields=("search_id", "pair_id"),
        )
    if _CROSS_SEARCH_SELECTION_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Cross Search result build only acceptssearch_id andpair_id;artifact/hash,"
            "Axis field and methodology,asset,rank/winner Both are re-certified and restored by the platform.",
            code="cross_search_selection_platform_binding_forbidden",
            fields=("platform_binding",),
        )
    search_ids = tuple(
        match.group(0)
        for match in _CROSS_SEARCH_ID_TOKEN_RE.finditer(utterance)
    )
    pair_ids = tuple(
        match.group(0)
        for match in _CROSS_PAIR_ID_TOKEN_RE.finditer(utterance)
    )
    if search_ids != (inputs["search_id"],) or pair_ids != (inputs["pair_id"],):
        return _clarification(
            "Cross Search result build must be provided word for word and only completesearch_id and"
            "A completepair_id;The platform will not complete, replace, rank-based or consume the pronouns.",
            code="cross_search_selection_controls_not_grounded",
            fields=("search_id", "pair_id"),
        )
    return result

def _cross_matrix_cell_rationale_is_allowed(reason: str) -> bool:
    without_cell_terms = re.sub(
        r"(?:Two-dimensional.|Cross|Cross\s+Matrix|matrix|Here.(?:Some.|Two.)?|These.|Two.|Multiple|"
        r"Grid|Cells|cells?)",
        " ",
        reason,
        flags=re.IGNORECASE,
    )
    return _automatic_tree_leaf_rationale_is_allowed(without_cell_terms)

def _cross_matrix_cell_has_positive_selection_intent(utterance: str) -> bool:
    operation_text = _AUTOMATIC_TREE_LEAF_REASON_RE.sub(" ", utterance)
    operation_text = _CROSS_MATRIX_CELL_NEGATED_FOLLOW_UP_RE.sub(" ", operation_text)
    for clause in _automatic_tree_follow_up_clauses(operation_text):
        for match in _CROSS_MATRIX_CELL_SELECTION_VERB_RE.finditer(clause):
            prefix = clause[: match.start()]
            if re.search(r"(?:No, no.|Not|Nope.(?:Yes.)?)\s*$", prefix):
                continue
            if not _automatic_tree_follow_up_action_is_negated(
                clause,
                action_start=match.start(),
            ):
                return True
    return False

def _cross_matrix_cell_unconsumed_request_text(utterance: str) -> str:
    remaining = unicodedata.normalize("NFC", utterance)
    remaining = _AUTOMATIC_TREE_LEAF_NEGATED_REASON_CLAUSE_RE.sub(" ", remaining)
    remaining = _AUTOMATIC_TREE_LEAF_REASON_RE.sub(" ", remaining)
    remaining = _CROSS_MATRIX_CELL_NEGATED_FOLLOW_UP_RE.sub(" ", remaining)
    remaining = _AUTOMATIC_TREE_ASSET_ID_TOKEN_RE.sub(" ", remaining)
    remaining = _CROSS_MATRIX_CELL_ID_TOKEN_RE.sub(" ", remaining)
    remaining = _CROSS_MATRIX_CELL_ALLOWED_REQUEST_TOKEN_RE.sub(" ", remaining)
    remaining = _AUTOMATIC_TREE_LEAF_REQUEST_PUNCTUATION_RE.sub(" ", remaining)
    return " ".join(remaining.split())

def _ground_cross_matrix_cell_selection(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Bind an exact Cross asset and explicit cell set to one pointer operation."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    positive_operation_text = _CROSS_MATRIX_CELL_NEGATED_FOLLOW_UP_RE.sub(
        " ", utterance
    )
    positive_operation_text = _AUTOMATIC_TREE_LEAF_REASON_RE.sub(
        " ", positive_operation_text
    )

    if (
        _CROSS_MATRIX_CELL_AMBIGUOUS_SELECTION_RE.search(positive_operation_text)
        is not None
        or _CROSS_MATRIX_CELL_HEURISTIC_CONTROL_RE.search(positive_operation_text)
        is not None
    ):
        return _clarification(
            "Please from fullCross Matrix Make sure you copy it clearly in the result.cell ID;You can't rank by,"
            "Values, risk descriptions or indicator thresholds select cells for you.",
            code="cross_matrix_cell_selection_ambiguous",
            fields=("cell_ids",),
        )
    if (
        _CROSS_MATRIX_CELL_SELECTION_NEGATED_RE.search(positive_operation_text)
        is not None
        or not _cross_matrix_cell_has_positive_selection_intent(utterance)
    ):
        return _clarification(
            "I don't know what to say. I don't know what to do.Cross Matrix cell selection;negative or only"
            "DescriptionID Request will not be createdpointer.Please state the whole thing.Cross asset ID and"
            "All to choosecell ID.",
            code="cross_matrix_cell_intent_negated",
            fields=("selection_intent",),
        )

    reason_values = _automatic_tree_leaf_all_reason_values(utterance)
    explicit_reasons = _automatic_tree_leaf_explicit_reasons(utterance)
    if any(
        _AUTOMATIC_TREE_LEAF_REASON_REPLACEMENT_RE.search(reason) is not None
        for reason in reason_values
    ):
        return _clarification(
            "One request can only give one final answer.selection_reason;Reasons cannot be embedded"
            "field or replace command.",
            code="cross_matrix_cell_reason_not_grounded",
            fields=("selection_reason",),
        )
    if any(
        _AUTOMATIC_TREE_LEAF_REASON_EXTREME_RE.search(reason) is not None
        or _CROSS_MATRIX_CELL_HEURISTIC_CONTROL_RE.search(reason) is not None
        for reason in reason_values
    ):
        return _clarification(
            "selection_reason Please keep only the syntax of the indicator ' s extreme, ranking or threshold."
            "Manually clear selection basis.",
            code="cross_matrix_cell_selection_ambiguous",
            fields=("cell_ids", "selection_reason"),
        )
    if any(
        _AUTOMATIC_TREE_LEAF_REASON_FORBIDDEN_OPERATION_RE.search(reason) is not None
        for reason in reason_values
    ):
        return _clarification(
            "selection_reason No hiding.Strategy Pool,Operational, adoption, deployment or"
            "Write back requests; these operations must be broken down into follow-up requests.",
            code="cross_matrix_cell_single_step_required",
            fields=("selection_reason", "next_action"),
        )
    if any(
        not _cross_matrix_cell_rationale_is_allowed(reason)
        or _AUTOMATIC_TREE_LEAF_RATIONALE_DECISION_SUBJECT_RE.search(reason)
        is not None
        for reason in explicit_reasons
    ):
        return _clarification(
            "selection_reason It must be manual./Operations/Risk/Compliance/The sample evaluation was based on short descriptions of the type,"
            "It cannot include hit customers, business movements, strategic pools or production operations.",
            code="cross_matrix_cell_reason_not_grounded",
            fields=("selection_reason",),
        )

    active_follow_up_text = _CROSS_MATRIX_CELL_NEGATED_FOLLOW_UP_RE.sub(
        " ", positive_operation_text
    )
    if any(
        pattern.search(active_follow_up_text) is not None
        for pattern in (
            _AUTOMATIC_TREE_LEAF_POOL_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_ACTION_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_LIFECYCLE_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_WRITEBACK_CHAIN_RE,
        )
    ):
        return _clarification(
            "Only current roundCross Matrix Cell Selectionpointer;AddStrategy Pool,"
            "The establishment of operational actions, adoption, deployment or write-back must initiate follow-up requests separately.",
            code="cross_matrix_cell_single_step_required",
            fields=("next_action",),
        )

    asset_matches = tuple(_AUTOMATIC_TREE_ASSET_ID_TOKEN_RE.finditer(utterance))
    cell_matches = tuple(_CROSS_MATRIX_CELL_ID_TOKEN_RE.finditer(utterance))
    asset_ids = frozenset(match.group(0) for match in asset_matches)
    cell_ids = frozenset(match.group(0) for match in cell_matches)
    ambiguous_fields: list[str] = []
    if len(asset_matches) != 1 or len(asset_ids) != 1:
        ambiguous_fields.append("cross_asset_id")
    if (
        not 1 <= len(cell_matches) <= 400
        or len(cell_matches) != len(cell_ids)
    ):
        ambiguous_fields.append("cell_ids")
    if ambiguous_fields:
        return _clarification(
            "Please provide a word for word in the same request and only a full copyCross candidate asset ID"
            "(candidate-asset- 32-bit lowercase hexadecimal) and 1 to 400"
            "Completeness without repetitioncell ID(cross-cell- Back-up 32-bit lowercase hexadecimal;"
            "No, not \"just\" words like \"the grids.\"",
            code="cross_matrix_cell_explicit_ids_required",
            fields=tuple(ambiguous_fields),
        )

    ungrounded: list[str] = []
    if asset_ids != {inputs["cross_asset_id"]}:
        ungrounded.append("cross_asset_id")
    if cell_ids != set(inputs["cell_ids"]):
        ungrounded.append("cell_ids")
    if ungrounded:
        return _clarification(
            "in the draft modelCross asset orcell ID This is not consistent with the user 's original message. Platform does not"
            "Replace, complete, sort or guessID.",
            code="cross_matrix_cell_controls_not_grounded",
            fields=tuple(ungrounded),
        )

    selection_reason = inputs.get("selection_reason")
    if bool(explicit_reasons or selection_reason is not None) and (
        len(explicit_reasons) != 1
        or not isinstance(selection_reason, str)
        or selection_reason != explicit_reasons[0]
    ):
        return _clarification(
            "selection_reason It must be used by the user to \"select the reason.\"/Rationale/Reason/Note 'in-kind"
            "The only reason is entirely consistent; the model must be omitted if no justification is given.",
            code="cross_matrix_cell_reason_not_grounded",
            fields=("selection_reason",),
        )

    if _cross_matrix_cell_unconsumed_request_text(utterance):
        return _clarification(
            "This round only accepts one clear one.Cross Matrix Cellspointer Select; request also"
            "The contents cannot be explained by the one-step contract."
            "Follow-up request.",
            code="cross_matrix_cell_single_step_required",
            fields=("next_action",),
        )
    return result
