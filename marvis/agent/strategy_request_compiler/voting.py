"""voting request-compiler handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import StandardWorkflowRequestDraft
    from . import StrategyRequestCompilation
    from . import _POOL_STRATEGY_TYPE_GROUNDING
    from . import _clarification
    from . import _utterance_chains_voting_search_operation

_VOTING_RULE_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])candidate-rule-[0-9a-f]{32}(?![A-Za-z0-9_-])"
)

_VOTING_SEARCH_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])voting-search-[0-9a-f]{32}(?![A-Za-z0-9_-])"
)

_VOTING_COMBO_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])voting-combo-[0-9a-f]{32}(?![A-Za-z0-9_-])"
)

_VOTING_SEARCH_SELECTION_INTENT_RE = re.compile(
    r"(?:Build|Physicalization|Generate|Create)[^;;.\n]{0,80}"
    r"(?:Voting|Vote.|n[-_ ]?of[-_ ]?k|Candidates)|"
    r"(?:Voting|Vote.|n[-_ ]?of[-_ ]?k|Search(?:Result|Evidence)|Group)"
    r"[^;;.\n]{0,80}(?:Build|Physicalization|Generate|Create)|"
    r"(?<![A-Za-z0-9_])(?:build|materialize|create|generate)"
    r"[^;.!?\n]{0,80}(?:voting|n[-_ ]?of[-_ ]?k|candidate)|"
    r"(?<![A-Za-z0-9_])(?:voting|n[-_ ]?of[-_ ]?k|search\s+(?:result|evidence))"
    r"[^;.!?\n]{0,80}(?:build|materialize|create|generate)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_SEARCH_SELECTION_HEURISTIC_RE = re.compile(
    r"(?:I'm sorry.[One, two, three, four, five, six, seven, eight, nine hundred.\d]+Synchronising folder|First(?:individual|Synchronising folder)|I'd better.(?:It's...)?|Best|"
    r"Best|Champion.|Top\s*[-#]?\s*\d+|Rank|Name|Just now.(?:That.|This.|It's...)?|"
    r"above|This combination.|The combination.)|"
    r"(?<![A-Za-z0-9_])(?:winner|champion|first|best|top\s*[-#]?\s*\d+|"
    r"rank(?:ing)?|previous|that\s+one|this\s+one)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_SEARCH_SELECTION_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:artifact_id|artifact_hash|artifact_content_hash|"
    r"expected_artifact_content_hash|search_content_hash|"
    r"expected_search_content_hash|expected_content_hash|content_hash|"
    r"(?:expected_)?pool_(?:revision|snapshot_hash|id)|"
    r"(?:expected_)?revision_id|pool_ref|dataset_id|dataset_binding|"
    r"(?:expected_)?dataset_content_hash|target_(?:col|polarity|semantics)|"
    r"target_binding|polarity|"
    r"sample_design_(?:ref|id|(?:content_)?hash|partition)|partition|"
    r"workspace_(?:revision|generation)|semantic_mapping(?:_hash)?|"
    r"requirement_bindings?|observation_bindings|provenance|rule_ids|"
    r"member_rule_ids|member_ids|entry_ids|selected_entry_ids|n|rank)"
    r"\s*(?:=|:|:)|"
    r"(?<![A-Za-z0-9_])(?:pool\s+(?:revision|snapshot\s+hash|id)|"
    r"revision\s+id|dataset\s+(?:id|content\s+hash)|content\s+hash|"
    r"target\s+(?:column|col|polarity|semantics)|polarity|"
    r"sample\s+design\s+(?:reference|ref|id|hash|partition)|"
    r"workspace\s+(?:revision|generation)|semantic\s+mapping(?:\s+hash)?|"
    r"requirement\s+bindings?)\s*(?:=|:|:)|"
    r"(?<![A-Za-z0-9_-])(?:candidate-rule|pool-entry)-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])|"
    r"(?:artifact|Work)\s*(?:id|hash|Hash.|References)|"
    r"(?:(?:(?:Policy|Rule)?Ji.|(?:Strategy\s+)?Pool)\s*"
    r"(?:Version|Revision|Quickshot(?:Hash.|hash)|ID|id)|"
    r"(?:Version|Revision)ID|(?:Dataset|Data)(?:ID|id|Contents(?:Hash.|hash))|"
    r"(?:Objective|Label|Bad Tag)(?:Columns|Fields|Polar|Semantics|Direction|Value)|"
    r"Sample design(?:References|ID|id|(?:Contents)?(?:Hash.|hash)|Division)|"
    r"Workspace(?:Version|Revision|Substitute|revision|generation)|"
    r"Semantic Map(?:(?:Hash.|hash))?|(?:Rule)?Require binding)\s*(?:=|:|:|Yes)",
    re.IGNORECASE,
)

_VOTING_SEARCH_SELECTION_FOLLOW_UP_RE = re.compile(
    r"(?:Add|Put it in.|Writing|Inclusion|Add|Add)"
    r"[^,,;;.\n]{0,24}(?:Policy pool|Rule pool|Pool)|"
    r"(?:Modify|Adjustment|Change|Edit)[^,,;;.\n]{0,20}"
    r"(?:Policy pool|Rule pool|Pool)|"
    r"(?:Settings|Set as|For)[^,,;;.\n]{0,20}(?:Reject|Approval|Review|Actions)|"
    r"(?:Into the pool.|Set Actions|Apply|Apply|Implementation|Accepted|Deployment|Online.|Production|Write back|Back up.)|"
    r"(?<![A-Za-z0-9_])(?:add\s+to\s+(?:the\s+)?(?:strategy\s+)?pool|"
    r"modify\s+(?:the\s+)?(?:strategy\s+)?pool|set\s+action|apply|adopt|"
    r"deploy|publish|write[- ]?back)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_SEARCH_SELECTION_RESEARCH_RE = re.compile(
    r"(?:Restart|Again.|Again.)?(?:Search|Find|Search|Search|Enumeration|Optimization|Filter)"
    r"[^,,;;.\n]{0,48}(?:Vote.|Voting|n[-_ ]?of[-_ ]?k)(?:Group|Candidates)?|"
    r"(?:Search|Find|Search|Find|Search|Enumeration|Optimization|Filter)"
    r"[^,,;;.\n]{0,16}(?:Again.|Once.|Better.(?:It's...)?(?:Group|Candidates))|"
    r"(?<![A-Za-z0-9_])(?:re-?search|search|find|enumerate|optimi[sz]e)"
    r"[^,;.!?\n]{0,48}(?:voting|n[-_ ]?of[-_ ]?k)(?:\s+combinations?)?"
    r"(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:re-?search|search(?:ing)?|find|enumerate|optimi[sz]e)"
    r"[^,;.!?\n]{0,32}(?:again|better\s+(?:combination|candidate))"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_SEARCH_SELECTION_NEGATED_RESEARCH_RE = re.compile(
    r"(?:No, no.|Don't.|No, I'm fine.|No need.|No, I don't.|Not yet.|Not yet.|Don't.|Ban)"
    r"[^,,;;.\n]{0,20}(?:Restart|Again.|Again.)?"
    r"(?:Search|Find|Search|Find|Search|Enumeration|Optimization|Filter)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|never|without)"
    r"[^,;.!?\n]{0,24}(?:re-?search|search(?:ing)?|find|enumerate|optimi[sz]e)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_SUBJECT_RE = re.compile(
    r"(?:Vote.|(?<![A-Za-z0-9_])(?:Voting|n[-_ ]?of[-_ ]?k)"
    r"(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_VOTING_SEARCH_INTENT_RE = re.compile(
    r"(?:Search|Find|Search|Search|Enumeration|Optimization|Filter)"
    r"[^,,;;.\n]{0,48}(?:Vote.|Voting|n[-_ ]?of[-_ ]?k)(?:Group|Candidates)?|"
    r"(?:Vote.|Voting|n[-_ ]?of[-_ ]?k)(?:Group|Candidates)?"
    r"[^,,;;.\n]{0,48}(?:Search|Find|Search|Search|Enumeration|Optimization|Filter)|"
    r"(?<![A-Za-z0-9_])(?:search|find|enumerate|optimi[sz]e|screen)"
    r"[^,;.!?\n]{0,48}(?:voting|n[-_ ]?of[-_ ]?k)(?:\s+combinations?)?|"
    r"(?<![A-Za-z0-9_])(?:voting|n[-_ ]?of[-_ ]?k)(?:\s+combinations?)?"
    r"[^,;.!?\n]{0,48}(?:search|find|enumerate|optimi[sz]e|screen)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_SEARCH_NEGATED_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|No, I don't.|Not yet.|Not yet.|Cancel|Stop)"
    r"[^,,;;.\n]{0,32}(?:Search|Find|Search|Search|Enumeration|Optimization|Filter|Comparison|"
    r"Vote.|Voting|n[-_ ]?of[-_ ]?k)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|cancel|stop)"
    r"[^,;.!?\n]{0,32}(?:search|find|enumerate|optimi[sz]e|screen|compare|"
    r"voting|n[-_ ]?of[-_ ]?k)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_SEARCH_RESULT_REFERENCE = (
    r"(?:Group|Candidates|Result|I'm sorry.[One, two, three, four, five, six, seven, eight, nine hundred.\d]+Synchronising folder|"
    r"Top\s*[-#]?\s*\d*)"
)

_VOTING_SEARCH_POOL_REFERENCE = (
    r"(?:Policy pool|Rule pool|(?<![A-Za-z0-9_])Pool(?![A-Za-z0-9_]))"
)

_VOTING_SEARCH_FOLLOW_UP_OPERATION_RE = re.compile(
    rf"(?:Build|Generate|Create|Physicalization)[^,,;;.\n]{{0,32}}"
    rf"(?:{_VOTING_SEARCH_RESULT_REFERENCE}|Voting|n[-_ ]?of[-_ ]?k)|"
    rf"(?:Selection|Select|Select|Selection|Adopt|Use)[^,,;;.\n]{{0,24}}"
    rf"{_VOTING_SEARCH_RESULT_REFERENCE}|"
    rf"(?:Apply|Apply|Implementation)[^,,;;.\n]{{0,32}}"
    rf"(?:{_VOTING_SEARCH_RESULT_REFERENCE}|Current Sample)|"
    rf"{_VOTING_SEARCH_RESULT_REFERENCE}[^,,;;.\n]{{0,24}}"
    r"(?:Apply|Apply|Implementation)|"
    r"(?:Add|Put it in.|Writing|Inclusion|Add|Add)"
    rf"[^,,;;.\n]{{0,24}}{_VOTING_SEARCH_POOL_REFERENCE}|"
    rf"(?:Modify|Adjustment|Change|Edit)[^,,;;.\n]{{0,16}}"
    rf"{_VOTING_SEARCH_POOL_REFERENCE}|"
    rf"{_VOTING_SEARCH_RESULT_REFERENCE}[^,,;;.\n]{{0,24}}"
    r"(?:Settings|Set as|For)[^,,;;.\n]{0,16}(?:Reject|Approval|Review|Actions)|"
    r"(?:Into the pool.|Set Actions|Accepted|Deployment|Online.|Production|Write back|Back up.)|"
    r"(?<![A-Za-z0-9_])(?:add|put|write|insert)"
    r"[^,;.!?\n]{0,32}(?:to|into)\s+(?:the\s+)?"
    r"(?:strategy\s+|rule\s+)?pool(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:use|adopt|apply)"
    r"[^,;.!?\n]{0,24}(?:top|first|second|third|result|combination|candidate)"
    r"(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:modify|change|update|edit)"
    r"[^,;.!?\n]{0,20}(?:strategy\s+|rule\s+)?pool(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])set[^,;.!?\n]{0,32}"
    r"(?:action|reject|approve|review)(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:build|create|materialize|select|choose|admit|"
    r"add\s+to\s+(?:the\s+)?(?:strategy\s+)?pool|set\s+action|adopt|"
    r"apply|deploy|publish|write[- ]?back)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_SEARCH_NEGATED_FOLLOW_UP_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|No, I don't.|Not yet.|Not yet.|No, I won't.|Not anymore.|No, no.|Don't.|Ban)"
    r"[^,,;;.\n]{0,16}(?:Build|Generate|Create|Physicalization|Selection|Select|Select|Selection|"
    r"Adopt|Use|Apply|Apply|Implementation|Into the pool.|Add|Put it in.|Writing|Inclusion|Add|Add|"
    r"Modify|Adjustment|Change|Edit|Settings|Set as|For|Accepted|Deployment|Online.|Production|Write back|Back up.)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|never|without)"
    r"[^,;.!?\n]{0,20}(?:build|create|materialize|select|choose|admit|"
    r"add|put|insert|use|apply|modify|change|update|edit|set|adopt|"
    r"deploy|publish|write[- ]?back)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_SEARCH_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:pool_ref|dataset_id|target_col|hit_matrix|"
    r"weights|amounts|search_result|artifact_id|content_hash)"
    r"(?![A-Za-z0-9_])|"
    r"(?:Dataset|Target column|Impact Matrix|Sample weights|Amount vector|Work)"
    r"\s*(?:ID|id|hash|Hash.|References)",
    re.IGNORECASE,
)

_VOTING_SEARCH_MEMBER_COUNT_PATTERNS = (
    re.compile(
        r"(?<![A-Za-z0-9_])(?:K|member[_ -]?count)"
        r"\s*(?:=|:|:|Yes)?\s*(?P<k>\d+)(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    re.compile(r"(?P<k>\d+)\s*(?:individual|Article|Item)?\s*Choose\s*(?P<n>\d+)"),
    re.compile(
        r"(?P<n>\d+)\s*(?:-|/|\s)\s*(?:of|OF)\s*(?P<k>\d+)",
        re.IGNORECASE,
    ),
)

_VOTING_SEARCH_METRIC_ALIASES = {
    "hit_count": "hit_count",
    "Number of hits": "hit_count",
    "Hits": "hit_count",
    "hit_share": "hit_share",
    "Ratio of hits to samples": "hit_share",
    "Life-rate ratio": "hit_share",
    "Hit rate": "hit_share",
    "good_count": "good_count",
    "Good sample numbers": "good_count",
    "bad_count": "bad_count",
    "Number of bad samples": "bad_count",
    "bad_rate": "bad_rate",
    "Bad sample rate": "bad_rate",
    "Bad rate": "bad_rate",
    "Bad debt rate": "bad_rate",
    "lift": "lift",
    "Increase": "lift",
    "bad_capture_rate": "bad_capture_rate",
    "Bad sample capture rate": "bad_capture_rate",
    "Bad sample recall rate": "bad_capture_rate",
    "weighted_hit_total": "weighted_hit_total",
    "Weighted total hit": "weighted_hit_total",
    "weighted_hit_share": "weighted_hit_share",
    "Share of weighted lives": "weighted_hit_share",
    "weighted_good_total": "weighted_good_total",
    "Total weighted samples": "weighted_good_total",
    "weighted_bad_total": "weighted_bad_total",
    "Total weighted bad sample": "weighted_bad_total",
    "weighted_bad_rate": "weighted_bad_rate",
    "Weighted bad sample rate": "weighted_bad_rate",
    "Weighted bad rate": "weighted_bad_rate",
    "weighted_bad_capture_rate": "weighted_bad_capture_rate",
    "Weighted bad sample capture rate": "weighted_bad_capture_rate",
    "hit_amount": "hit_amount",
    "Hit amount": "hit_amount",
    "hit_amount_share": "hit_amount_share",
    "The amount hit.": "hit_amount_share",
    "good_amount": "good_amount",
    "Good sample amount": "good_amount",
    "bad_amount": "bad_amount",
    "Bad sample amount": "bad_amount",
    "bad_amount_rate": "bad_amount_rate",
    "Bad sample value rate": "bad_amount_rate",
    "bad_amount_capture_rate": "bad_amount_capture_rate",
    "Rate of capture of bad sample amounts": "bad_amount_capture_rate",
}

_VOTING_SEARCH_METRIC_TOKEN = "|".join(
    re.escape(alias)
    for alias in sorted(
        _VOTING_SEARCH_METRIC_ALIASES,
        key=lambda value: (-len(value), value),
    )
)

_VOTING_SEARCH_OBJECTIVE_PATTERNS = (
    re.compile(
        r"(?:Objective|objective)\s*(?:Yes|Yes.|=|:|:)?\s*"
        r"(?P<direction>Maximize|Minimize|maximi[sz]e|minimi[sz]e)\s*"
        rf"(?P<metric>{_VOTING_SEARCH_METRIC_TOKEN})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Objective|objective)\s*(?:Yes|Yes.|=|:|:)?\s*"
        rf"(?P<metric>{_VOTING_SEARCH_METRIC_TOKEN})\s*"
        r"(?P<direction>Maximize|Minimize|maximi[sz]e|minimi[sz]e)",
        re.IGNORECASE,
    ),
)

_VOTING_SEARCH_CONSTRAINT_RE = re.compile(
    rf"(?<![A-Za-z0-9_])(?P<metric>{_VOTING_SEARCH_METRIC_TOKEN})\s*"
    r"(?P<operator>>=|<=|gte|lte|At least.|Not less than|No less than|Up to|No more than|Not higher)"
    r"\s*(?P<value>\d+(?:\.\d+)?%?)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_SEARCH_INCLUDE_LABEL_RE = re.compile(
    r"(?:Must Contain|Organisation|Inclusion|include(?:_rule_ids)?)"
    r"\s*(?:Rule|rule(?:s|_ids)?)?\s*(?:=|:|:)?",
    re.IGNORECASE,
)

_VOTING_SEARCH_EXCLUDE_LABEL_RE = re.compile(
    r"(?:Exclude|Remove|Get rid of it.|exclude(?:_rule_ids)?)"
    r"\s*(?:Rule|rule(?:s|_ids)?)?\s*(?:=|:|:)?",
    re.IGNORECASE,
)

_VOTING_SEARCH_NEGATED_LABEL_PREFIX_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|No, I don't.|Not yet.|Not yet.|Don't.|Ban|No, no.)\s*$|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|must\s+not|never)\s*$",
    re.IGNORECASE,
)

_VOTING_SEARCH_MAX_COMBINATIONS_RE = re.compile(
    r"(?<![A-Za-z0-9_])max[_ -]?combinations"
    r"\s*(?:=|:|:|Yes)?\s*(?P<value>\d+)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_BUILD_INTENT_RE = re.compile(
    r"(?:Build|Generate|Create|Measurement|Analysis|Evaluation|Do it.)"
    r"[^,,;;.\n]{0,40}(?:Vote.|Voting|n[-_ ]?of[-_ ]?k)|"
    r"(?:Vote.|Voting|n[-_ ]?of[-_ ]?k)"
    r"[^,,;;.\n]{0,40}(?:Build|Generate|Create|Measurement|Analysis|Evaluation)|"
    r"(?<![A-Za-z0-9_])(?:build|create|generate|evaluate|analy[sz]e)"
    r"[^,;.!?\n]{0,40}(?:voting|n[-_ ]?of[-_ ]?k)"
    r"(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:voting|n[-_ ]?of[-_ ]?k)"
    r"[^,;.!?\n]{0,40}(?:build|create|generate|evaluate|analy[sz]e)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_NEGATED_BUILD_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|No, I don't.|Not yet.|Not yet.|Cancel|Stop)"
    r"[^,,;;.\n]{0,24}(?:Build|Generate|Create|Measurement|Analysis|Evaluation|Vote.|Voting|n[-_ ]?of[-_ ]?k)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|cancel|stop)"
    r"[^,;.!?\n]{0,24}(?:build|create|generate|evaluate|voting|n[-_ ]?of[-_ ]?k)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_NONCOMMAND_RE = re.compile(
    r"[??]|"
    r"(?:Can you...|Can I?|Is it possible?|Is that okay?|Can you...|Do you want it?|Is it possible?|How's that?|What?|What?|"
    r"Assumptions|Suppose...|If|If|What if...|Presentation|Demonstration|Test|Example|Explain.|Explanation|"
    r"Introduction|Description|Tell me.|Presentation)"
    r"[^;;.\n]{0,220}(?:Build|Generate|Create|Measurement|Analysis|Evaluation|Vote.|Voting|n[-_ ]?of[-_ ]?k)|"
    r"(?:Yesterday.|Yesterday|Before|Before|Go on.|Last time.|Previous|Earlier|Once.|History|"
    r"Document|Report|Example:|Example|Original|Materials)"
    r"[^;;.\n]{0,220}(?:Build|Generate|Create|Measurement|Vote.|Voting|"
    r"n[-_ ]?of[-_ ]?k|candidate-rule-[0-9a-f]{32})|"
    r"(?:The future.|In the future|Later|Later.|Later.|Turn around.|Tomorrow.|The day after tomorrow.|Next week.|Next month|Next month|"
    r"End of the month|And then...|[One, two, two, three, four, five, six, seven, eight, nine, zero.-9]+Queen of Heaven.)"
    r"[^;;.\n]{0,220}(?:Build|Generate|Create|Measurement|Vote.|Voting|n[-_ ]?of[-_ ]?k)|"
    r"(?:Wait.|- Wait.)[^;;.\n]{0,100}(?:Back|After|Again.|That's right.)"
    r"[^;;.\n]{0,140}(?:Build|Generate|Create|Measurement|Vote.|Voting|n[-_ ]?of[-_ ]?k)|"
    r"(?<![A-Za-z0-9_])(?:can\s+you|could\s+you|would\s+you|"
    r"is\s+it\s+possible|what\s+if|suppose|assuming|hypothetically|"
    r"how\s+to|demonstrate|demo|test|example|yesterday|previously|"
    r"earlier|last\s+time|in\s+the\s+future|later|tomorrow|"
    r"next\s+(?:week|month)|when|once|after)"
    r"[^;.!?\n]{0,220}(?:build|create|generate|evaluate|analy[sz]e|"
    r"voting|n[-_ ]?of[-_ ]?k)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_POSTPOSED_CANCELLATION_RE = re.compile(
    r"(?:^|[,,;;..!??!]\s*)(?:Wait.|Wait a minute.|Forget it.|Let's do it.|I'm sorry.|"
    r"Cancel(?:Yeah.|Yes.)?|Withdrawn.|Undo|Stop|Not yet.(?:Yes.)?|Not for now.(?:Yes.)?|"
    r"Don't do it.(?:Yes.)?|Don't do it.(?:Yes.)?|Not implemented(?:Yes.)?)(?:[,,..!!??]?\s*)$|"
    r"(?:^|[,;.!?]\s*)(?:never\s+mind|forget\s+it|scratch\s+that|"
    r"cancel|abort|withdraw|stop|do(?:n't|\s+not)\s+(?:do|execute)\s+it)"
    r"(?:[,!.?]?\s*)$",
    re.IGNORECASE,
)

_VOTING_HEURISTIC_SELECTION_RE = re.compile(
    r"(?:I'd better.|Best|Best|Worst|Worst|Risk highest|The worst rate of bad.|You're the best.|"
    r"Automatic(?:Selection|Selection|Recommendations)|Just now.(?:Those.|These.|It's...)?|above|These rules.|The rules.)|"
    r"(?<![A-Za-z0-9_])(?:best|worst|top[- ]?\d*|highest[- ]risk|"
    r"automatically\s+(?:select|pick|recommend)|those|these|previous)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_FOLLOW_UP_RE = re.compile(
    r"(?:Add|Put it in.|Writing)[^,,;;.\n]{0,16}(?:Policy pool|Rule pool|Pool)|"
    r"(?:Into the pool.|Settings(?:Operations)?Actions|Accepted|Deployment|Online.|Production|Write back|Back up.)|"
    r"(?:and|And...|And then...|And then...|Again.|Meanwhile...|Catch.|Direct)"
    r"(?![^,,;;.\n]{0,24}(?:Comparison|Comparison))"
    r"[^,,;;.\n]{0,40}(?:Reject|Approval|Pass.|Review)|"
    r"(?<![A-Za-z0-9_])(?:add\s+to\s+(?:the\s+)?(?:strategy\s+)?pool|"
    r"set\s+action|adopt|deploy|publish|write[- ]?back)(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:and(?:\s+then)?|then|also)"
    r"(?![^,;.!?\n]{0,24}(?:compare|comparison))"
    r"[^,;.!?\n]{0,40}(?:reject|approve|review)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_OTHER_POOL_OPERATION_RE = re.compile(
    r"(?:Delete|Remove|Reorder|Reorder|Sort|Compile|Preview)"
    r"[^,,;;.\n]{0,32}(?:Policy pool|Rule pool|pool|pool-entry-|candidate-rule-)|"
    r"(?:Policy pool|Rule pool|pool)"
    r"[^,,;;.\n]{0,32}(?:Delete|Remove|Reorder|Reorder|Sort|Compile|Preview)|"
    r"(?<![A-Za-z0-9_])(?:remove|delete|reorder|sort|compile|preview)"
    r"[^,;.!?\n]{0,32}(?:strategy\s+pool|rule\s+pool|pool-entry-|candidate-rule-)|"
    r"(?<![A-Za-z0-9_])(?:strategy\s+pool|rule\s+pool|pool)"
    r"[^,;.!?\n]{0,32}(?:remove|delete|reorder|sort|compile|preview)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_NEGATED_CONTROL_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|Don't use it.|No choice.|Don't pick.|Exclude|Remove|Get rid of it.|Ignore|Delete|Remove)"
    r"[^,,;;.\n]{0,24}(?:candidate-rule-[0-9a-f]{32}|"
    r"n\s*(?:=|:|:|Yes)?\s*\d+)|"
    r"(?:candidate-rule-[0-9a-f]{32}|n\s*(?:=|:|:|Yes)?\s*\d+)"
    r"[^,,;;.\n]{0,16}(?:Don't.|No, I'm fine.|No choice.|Exclude|Remove|Get rid of it.|Ignore)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|exclude|omit|remove|delete)"
    r"[^,;.!?\n]{0,24}(?:candidate-rule-[0-9a-f]{32}|"
    r"n\s*(?:=|:)?\s*\d+)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_VOTING_COMMAND_CLAUSE_RE = re.compile(r"[^;;..!!??\n]+")

_VOTING_COMMAND_RESET_RE = re.compile(
    r"(?:Now.|This time.|This time.|Current|Next|Immediately|Now.|Please.|Again.|And then...|And then...)\s*$"
)

_VOTING_N_PATTERNS = (
    re.compile(
        r"(?:n|min[_ -]?hits?|Threshold|Minimum number of hits|At least it hit.|At least.)\s*"
        r"(?:=|:|:|Yes)?\s*(?P<n>\d+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<n>\d+)\s*(?:-|/|\s)\s*(?:of|OF)\s*(?P<k>\d+)",
        re.IGNORECASE,
    ),
    re.compile(r"(?P<k>\d+)\s*(?:individual)?\s*Choose\s*(?P<n>\d+)"),
    re.compile(
        r"(?:At least.|At least)\s*(?:Hit.)?\s*(?P<n>\d+)\s*(?:individual|Article|Item)?",
        re.IGNORECASE,
    ),
)

def _utterance_targets_voting_candidate_search(utterance: str) -> bool:
    """Reserve explicit Voting combination search before exact-member build."""

    return (
        not _utterance_targets_voting_search_selection(utterance)
        and _VOTING_SUBJECT_RE.search(utterance) is not None
        and _VOTING_SEARCH_INTENT_RE.search(utterance) is not None
    )

def _utterance_targets_voting_search_selection(utterance: str) -> bool:
    """Reserve an exact search-result materialization before search/build."""

    return (
        _VOTING_SEARCH_ID_TOKEN_RE.search(utterance) is not None
        and _VOTING_COMBO_ID_TOKEN_RE.search(utterance) is not None
        and _VOTING_SEARCH_SELECTION_INTENT_RE.search(utterance) is not None
    )

def _voting_search_text_has_positive_follow_up(text: str) -> bool:
    """Evaluate each follow-up operation against only its local polarity."""

    previous_end = 0
    for match in _VOTING_SEARCH_FOLLOW_UP_OPERATION_RE.finditer(text):
        local_start = max(
            previous_end,
            *(
                text.rfind(separator, previous_end, match.start()) + 1
                for separator in (
                    ",",
                    ",",
                    ";",
                    ";",
                    ".",
                    ".",
                    "!",
                    "!",
                    "?",
                    "?",
                )
            ),
        )
        fragment = text[local_start : match.end()]
        if _VOTING_SEARCH_NEGATED_FOLLOW_UP_RE.search(fragment) is None:
            return True
        previous_end = match.end()
    return False

def _voting_search_selection_has_positive_follow_up(text: str) -> bool:
    """Reject lifecycle chaining while allowing explicit negative disclaimers."""

    previous_end = 0
    for match in _VOTING_SEARCH_SELECTION_FOLLOW_UP_RE.finditer(text):
        clause_start = max(
            text.rfind(separator, 0, match.start()) + 1
            for separator in (";", ";", ".", ".", "!", "!", "?", "?")
        )
        clause_prefix = text[clause_start : match.start()]
        english_negation = tuple(
            re.finditer(
                r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|never|without)"
                r"(?![A-Za-z0-9_])",
                clause_prefix,
                re.IGNORECASE,
            )
        )
        if english_negation:
            after_negation = clause_prefix[english_negation[-1].end() :]
            if re.search(
                r"(?<![A-Za-z0-9_])(?:but|however|then)(?![A-Za-z0-9_])",
                after_negation,
                re.IGNORECASE,
            ) is None:
                previous_end = match.end()
                continue
        local_start = max(
            previous_end,
            *(
                text.rfind(separator, previous_end, match.start()) + 1
                for separator in (
                    ",",
                    ",",
                    ";",
                    ";",
                    ".",
                    ".",
                    "!",
                    "!",
                    "?",
                    "?",
                )
            ),
        )
        fragment = text[local_start : match.end()]
        if _VOTING_SEARCH_NEGATED_FOLLOW_UP_RE.search(fragment) is None:
            return True
        previous_end = match.end()
    return False

def _voting_search_selection_has_positive_research(text: str) -> bool:
    """Detect a second search command, excluding an explicitly negated one."""

    scrubbed = _VOTING_SEARCH_ID_TOKEN_RE.sub(
        lambda match: " " * len(match.group(0)),
        text,
    )
    scrubbed = _VOTING_COMBO_ID_TOKEN_RE.sub(
        lambda match: " " * len(match.group(0)),
        scrubbed,
    )
    for match in _VOTING_SEARCH_SELECTION_RESEARCH_RE.finditer(scrubbed):
        local_start = max(
            scrubbed.rfind(separator, 0, match.start()) + 1
            for separator in (",", ",", ";", ";", ".", ".", "!", "!", "?", "?")
        )
        if _VOTING_SEARCH_SELECTION_NEGATED_RESEARCH_RE.search(
            scrubbed[local_start : match.end()]
        ) is None:
            return True
    return False

def _utterance_targets_voting_candidate(utterance: str) -> bool:
    """Keep an explicit Voting request out of generic lifecycle/workflow routes."""

    return (
        _VOTING_SUBJECT_RE.search(utterance) is not None
        and len(tuple(_VOTING_RULE_ID_TOKEN_RE.finditer(utterance))) >= 2
    )

def _voting_positive_command_clause_spans(
    utterance: str,
) -> tuple[tuple[int, int], ...]:
    """Return one span per positive Voting command, preserving duplicates."""

    spans: list[tuple[int, int]] = []
    for clause_match in _VOTING_COMMAND_CLAUSE_RE.finditer(utterance):
        clause = clause_match.group(0)
        for command_match in _VOTING_BUILD_INTENT_RE.finditer(clause):
            prefix = clause[: command_match.start()]
            comma = max(prefix.rfind(","), prefix.rfind(","))
            local_start = comma + 1
            reset = _VOTING_COMMAND_RESET_RE.search(prefix)
            if reset is not None:
                local_start = max(local_start, reset.start())
            spans.append(
                (clause_match.start() + local_start, clause_match.end())
            )
    return tuple(spans)

def _voting_strategy_type_mentions(
    utterance: str,
) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        (strategy_type, match.start(), match.end())
        for strategy_type, pattern in _POOL_STRATEGY_TYPE_GROUNDING.items()
        for match in pattern.finditer(utterance)
    )

def _voting_n_mentions(
    utterance: str,
) -> tuple[tuple[int, int | None, int, int], ...]:
    mentions: list[tuple[int, int | None, int, int]] = []
    for pattern in _VOTING_N_PATTERNS:
        for match in pattern.finditer(utterance):
            k_token = match.groupdict().get("k")
            mentions.append(
                (
                    int(match.group("n")),
                    None if k_token is None else int(k_token),
                    match.start(),
                    match.end(),
                )
            )
    return tuple(mentions)

def _voting_mention_is_within(
    mention_start: int,
    mention_end: int,
    command_span: tuple[int, int],
) -> bool:
    return (
        command_span[0] <= mention_start
        and mention_end <= command_span[1]
    )

def _ground_voting_candidate_search(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Prove every search control came from this immediate user request."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if not _utterance_targets_voting_candidate_search(utterance):
        return _clarification(
            "Please specify the search, search or optimization of the currentStrategy Pool It's...Voting / n-of-k Group.",
            code="voting_search_intent_required",
            fields=("search_intent",),
        )
    if (
        _VOTING_SEARCH_NEGATED_RE.search(utterance) is not None
        or _VOTING_NONCOMMAND_RE.search(utterance) is not None
        or _VOTING_POSTPOSED_CANCELLATION_RE.search(utterance) is not None
    ):
        return _clarification(
            "Voting Group search must be an immediate positive order for the current round; query,"
            "Negative, hypothetical, historical/The search will not be started if the future description or end-of-the-word revocation is not available.",
            code="voting_search_positive_command_required",
            fields=("search_intent",),
        )
    if _utterance_chains_voting_search_operation(utterance):
        return _clarification(
            "This round only searchVoting grouping;building candidates, choosing groups, modifying or joining"
            "Strategy Pool,Applications, adoption and deployment must be subject to separate requests.",
            code="voting_search_single_step_required",
            fields=("next_action",),
        )
    if _VOTING_SEARCH_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Voting SearchedPool ref,dataset/target,And the center-by-line matrix, weight,"
            "Amount vector andartifact The identity can only be tied to the platform, and please remove these controls.",
            code="voting_search_platform_binding_forbidden",
            fields=("platform_binding",),
        )

    expected_type = str(inputs["strategy_type"])
    observed_types = {
        value for value, _start, _end in _voting_strategy_type_mentions(utterance)
    }
    if observed_types != {expected_type}:
        return _clarification(
            "Please specify and only indicate in the current search commandStrategy Pool Type;"
            "The platform does not select the type of strategy for the user.",
            code="voting_search_strategy_type_not_grounded",
            fields=("strategy_type",),
        )

    expected_member_count = int(inputs["member_count"])
    observed_member_counts = _voting_search_member_counts(utterance)
    if observed_member_counts != {expected_member_count}:
        return _clarification(
            "Please be clear and give each one.Voting GroupK/member_count(2 - 50 to that.",
            code="voting_search_member_count_not_grounded",
            fields=("member_count",),
        )

    expected_n = int(inputs["n"])
    n_bindings = _voting_n_bindings(utterance)
    observed_ns = {value for value, _k in n_bindings}
    explicit_ks = {value for _n, value in n_bindings if value is not None}
    if observed_ns != {expected_n} or (
        explicit_ks and explicit_ks != {expected_member_count}
    ):
        return _clarification(
            "Please be clear and give the onlyn,And make sure it's visible.n-of-k/(K Choosen)MediumK "
            "andmember_count Unanimously.",
            code="voting_search_n_not_grounded",
            fields=("n",),
        )

    observed_objectives = _voting_search_objectives(utterance)
    expected_objective = (
        str(inputs["objective"]["metric"]),
        str(inputs["objective"]["direction"]),
    )
    if observed_objectives != {expected_objective}:
        return _clarification(
            "Please write clearly and only after the Target labelobjective metric and"
            "maximize/minimize Direction.",
            code="voting_search_objective_not_grounded",
            fields=("objective",),
        )

    observed_constraints = _voting_search_constraints(utterance)
    expected_constraints = {
        (
            str(item["metric"]),
            str(item["operator"]),
            float(item["value"]),
        )
        for item in inputs["constraints"]
    }
    if observed_constraints != expected_constraints:
        return _clarification(
            "Voting Searchconstraints We can only use the current words in each case."
            "metric,gte/lte values;fixed to empty when not provided.",
            code="voting_search_constraints_not_grounded",
            fields=("constraints",),
        )

    include_ids, exclude_ids, all_labeled_ids = _voting_search_rule_controls(utterance)
    all_rule_ids = {
        match.group(0) for match in _VOTING_RULE_ID_TOKEN_RE.finditer(utterance)
    }
    expected_include = set(inputs["include_rule_ids"])
    expected_exclude = set(inputs["exclude_rule_ids"])
    if (
        include_ids != expected_include
        or exclude_ids != expected_exclude
        or all_rule_ids != all_labeled_ids
    ):
        return _clarification(
            "include/exclude Accepts only the complete currently requested word by word after the corresponding tab"
            "candidate-rule ID;pronouns, unnotifiedID,No omissions or omissions will be consumed.",
            code="voting_search_rule_controls_not_grounded",
            fields=("include_rule_ids", "exclude_rule_ids"),
        )

    observed_max = {
        int(match.group("value"))
        for match in _VOTING_SEARCH_MAX_COMBINATIONS_RE.finditer(utterance)
    }
    expected_max = int(inputs["max_combinations"])
    if (observed_max and observed_max != {expected_max}) or (
        not observed_max and expected_max != 10_000
    ):
        return _clarification(
            "max_combinations Only the only clear 1 of the current original language..10000 Integer number;"
            "The fixed number is 10000 when not provided.",
            code="voting_search_budget_not_grounded",
            fields=("max_combinations",),
        )
    return result

def _voting_search_member_counts(utterance: str) -> set[int]:
    values: set[int] = set()
    for pattern in _VOTING_SEARCH_MEMBER_COUNT_PATTERNS:
        for match in pattern.finditer(utterance):
            values.add(int(match.group("k")))
    return values

def _voting_search_objectives(utterance: str) -> set[tuple[str, str]]:
    values: set[tuple[str, str]] = set()
    for pattern in _VOTING_SEARCH_OBJECTIVE_PATTERNS:
        for match in pattern.finditer(utterance):
            raw_direction = match.group("direction").lower()
            direction = (
                "maximize"
                if raw_direction in {"Maximize", "maximize", "maximise"}
                else "minimize"
            )
            metric = _VOTING_SEARCH_METRIC_ALIASES[
                match.group("metric").casefold()
            ]
            values.add((metric, direction))
    return values

def _voting_search_constraints(
    utterance: str,
) -> set[tuple[str, str, float]]:
    values: set[tuple[str, str, float]] = set()
    for match in _VOTING_SEARCH_CONSTRAINT_RE.finditer(utterance):
        operator = match.group("operator").lower()
        normalized_operator = (
            "gte" if operator in {">=", "gte", "At least.", "Not less than", "No less than"} else "lte"
        )
        token = match.group("value")
        number = float(token[:-1]) / 100.0 if token.endswith("%") else float(token)
        metric = _VOTING_SEARCH_METRIC_ALIASES[
            match.group("metric").casefold()
        ]
        values.add((metric, normalized_operator, number))
    return values

def _voting_search_rule_controls(
    utterance: str,
) -> tuple[set[str], set[str], set[str]]:
    labels: list[tuple[int, int, str]] = []
    labels.extend(
        (match.start(), match.end(), "include")
        for match in _VOTING_SEARCH_INCLUDE_LABEL_RE.finditer(utterance)
    )
    labels.extend(
        (match.start(), match.end(), "exclude")
        for match in _VOTING_SEARCH_EXCLUDE_LABEL_RE.finditer(utterance)
    )
    labels.sort(key=lambda item: (item[0], item[1], item[2]))
    include: set[str] = set()
    exclude: set[str] = set()
    labeled: set[str] = set()
    for index, (start, end, kind) in enumerate(labels):
        clause_start = max(
            utterance.rfind(separator, 0, start)
            for separator in (";", ";", ".", ".", "!", "!", "?", "?", "\n")
        ) + 1
        clause_end_candidates = [
            position
            for separator in (";", ";", ".", ".", "!", "!", "?", "?", "\n")
            if (position := utterance.find(separator, end)) >= 0
        ]
        clause_end = (
            min(clause_end_candidates)
            if clause_end_candidates
            else len(utterance)
        )
        next_start = (
            labels[index + 1][0]
            if index + 1 < len(labels)
            and labels[index + 1][0] < clause_end
            else clause_end
        )
        if _VOTING_SEARCH_NEGATED_LABEL_PREFIX_RE.search(
            utterance[clause_start:start]
        ):
            continue
        for match in _VOTING_RULE_ID_TOKEN_RE.finditer(
            utterance,
            end,
            next_start,
        ):
            local_start = (
                max(
                    utterance.rfind(",", end, match.start()),
                    utterance.rfind(",", end, match.start()),
                    end - 1,
                )
                + 1
            )
            local_end_candidates = [
                position
                for separator in (",", ",")
                if (
                    position := utterance.find(
                        separator,
                        match.end(),
                        next_start,
                    )
                )
                >= 0
            ]
            local_end = (
                min(local_end_candidates)
                if local_end_candidates
                else next_start
            )
            if _VOTING_NEGATED_CONTROL_RE.search(
                utterance[local_start:local_end]
            ):
                continue
            rule_id = match.group(0)
            labeled.add(rule_id)
            if kind == "include":
                include.add(rule_id)
            else:
                exclude.add(rule_id)
    return include, exclude, labeled

def _ground_voting_candidate_build_from_search(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Ground one exact search/combo pointer pair in the current command."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if not _utterance_targets_voting_search_selection(utterance):
        return _clarification(
            "Please specify the requirement to complete from one.Voting search_id And a complete.combo_id "
            "Build or physically select candidates.",
            code="voting_search_selection_intent_required",
            fields=("build_intent", "search_id", "combo_id"),
        )
    if (
        _VOTING_NEGATED_BUILD_RE.search(utterance) is not None
        or _VOTING_NONCOMMAND_RE.search(utterance) is not None
        or _VOTING_POSTPOSED_CANCELLATION_RE.search(utterance) is not None
    ):
        return _clarification(
            "Voting Search result build must be a positive one-step command immediately executed in the current round; query sentence,"
            "Negative, hypothetical, historical/No candidate will be built for future description or end-of-story withdrawal.",
            code="voting_search_selection_positive_command_required",
            fields=("build_intent",),
        )
    if (
        _voting_search_selection_has_positive_research(utterance)
        or _voting_search_selection_has_positive_follow_up(utterance)
    ):
        return _clarification(
            "This round is only from precisionsearch_id/combo_id BuildVoting candidates;accession or modification"
            "Strategy Pool,Additional requests must be made for action, application, adoption, deployment and write-back.",
            code="voting_search_selection_single_step_required",
            fields=("next_action",),
        )
    if _VOTING_SEARCH_SELECTION_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Voting Search result build only acceptssearch_id,combo_id With Optionalstrategy_type;"
            "artifact/hash,rule/entry/member IDs,n andrank The government has been able to re-establish the platform."
            "It cannot be injected into natural languages.",
            code="voting_search_selection_platform_binding_forbidden",
            fields=("platform_binding",),
        )
    if _VOTING_SEARCH_SELECTION_HEURISTIC_RE.search(utterance) is not None:
        return _clarification(
            "Please take a full word for word.search_id andcombo_id;Even if it's all there.pointer,The platform."
            "I'm not gonna be the first, the best, the champion,Top N,The ranking or the \"just\" kind of inspirational choice.",
            code="voting_search_selection_explicit_ids_required",
            fields=("search_id", "combo_id"),
        )
    search_ids = tuple(
        match.group(0) for match in _VOTING_SEARCH_ID_TOKEN_RE.finditer(utterance)
    )
    combo_ids = tuple(
        match.group(0) for match in _VOTING_COMBO_ID_TOKEN_RE.finditer(utterance)
    )
    if search_ids != (inputs["search_id"],) or combo_ids != (inputs["combo_id"],):
        return _clarification(
            "Voting Search result build must be provided word for word and only completesearch_id With one"
            "Completecombo_id;The platform will not complete, replace, rank-based or consume the pronouns.",
            code="voting_search_selection_controls_not_grounded",
            fields=("search_id", "combo_id"),
        )
    observed_types = {
        value for value, _start, _end in _voting_strategy_type_mentions(utterance)
    }
    expected_type = inputs.get("strategy_type")
    if (
        expected_type is not None
        and observed_types != {expected_type}
    ) or (expected_type is None and observed_types):
        return _clarification(
            "Optionalstrategy_type Only the only clear line in the current request can be used word for wordStrategy Pool "
            "type; the model must be omitted and the only platform to be deciphered if not specified.",
            code="voting_search_selection_strategy_type_not_grounded",
            fields=("strategy_type",),
        )
    return result

def _ground_voting_candidate_build(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Prove the exact rule set and n came from one positive user command."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if _VOTING_NEGATED_BUILD_RE.search(utterance) is not None:
        return _clarification(
            "That's not true.Voting Candidates are not generated during this cycle."
            "If you need to continue, re-establish a clear positive construction request.",
            code="voting_candidate_build_intent_negated",
            fields=("build_intent",),
        )
    if (
        _VOTING_NONCOMMAND_RE.search(utterance) is not None
        or _VOTING_POSTPOSED_CANCELLATION_RE.search(utterance) is not None
    ):
        return _clarification(
            "The current words are words, assumptions./The future./The history, demonstration or withdrawal of the text at the end of the sentence is not a good idea."
            "Not considered immediateVoting The only positive command to build. Please repeat the one that you are building for this time"
            "Policy pool type, completerule_id List and Uniquen-of-k threshold.",
            code="voting_candidate_positive_command_required",
            fields=("build_intent",),
        )
    command_spans = _voting_positive_command_clause_spans(utterance)
    if not command_spans:
        return _clarification(
            "Please state clearly that you want to build or measure oneVoting / n-of-k Candidates, and one rule"
            "Request to give the type, complete of the policy poolrule_id List andn.",
            code="voting_candidate_build_intent_required",
            fields=("build_intent",),
        )
    if len(command_spans) != 1:
        return _clarification(
            "A request can only be made with one immediate execution.Voting Build/(a) Evaluation sub-paragraph;"
            "Please put each group together.rule_id andn-of-k Controls breaking into independent requests.",
            code="voting_candidate_single_command_required",
            fields=("build_intent",),
        )
    command_span = command_spans[0]
    if _VOTING_HEURISTIC_SELECTION_RE.search(utterance) is not None:
        return _clarification(
            "Voting Build must be named word for currentStrategy Pool Complete inrule_id;"
            "Models cannot be presented as automatic selection rules by the best, the highest risk, just what they are.",
            code="voting_candidate_explicit_rules_required",
            fields=("rule_ids",),
        )
    if (
        _VOTING_FOLLOW_UP_RE.search(utterance) is not None
        or _VOTING_OTHER_POOL_OPERATION_RE.search(utterance) is not None
    ):
        return _clarification(
            "This round only generates and calculatesVoting candidate;deleting, reordering, compiling, adding"
            "Strategy Pool,Additional requests must be made for the setting of operational actions, adoption, deployment or write-back.",
            code="voting_candidate_single_step_required",
            fields=("next_action",),
        )
    if _VOTING_NEGATED_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Current roundVoting Contains rejected, excluded or subsequently rewritten controlsrule_id/n;"
            "Please re-state the set of completes without historical or negative values.rule_id With the Onen.",
            code="voting_candidate_negated_control",
            fields=("rule_ids", "n"),
        )

    rule_matches = tuple(_VOTING_RULE_ID_TOKEN_RE.finditer(utterance))
    strategy_type_mentions = _voting_strategy_type_mentions(utterance)
    n_mentions = _voting_n_mentions(utterance)
    if (
        any(
            not _voting_mention_is_within(match.start(), match.end(), command_span)
            for match in rule_matches
        )
        or any(
            not _voting_mention_is_within(start, end, command_span)
            for _strategy_type, start, end in strategy_type_mentions
        )
        or any(
            not _voting_mention_is_within(start, end, command_span)
            for _n, _k, start, end in n_mentions
        )
    ):
        return _clarification(
            "Voting , completerule_id andn-of-k It must be all in the only place."
            "is in the construction sub-statement; the control in history, quotation, denial or other sub-rules is not consumed.",
            code="voting_candidate_controls_outside_command",
            fields=("strategy_type", "rule_ids", "n"),
        )

    observed_rule_ids = [match.group(0) for match in rule_matches]
    expected_rule_ids = list(inputs["rule_ids"])
    if (
        len(observed_rule_ids) != len(set(observed_rule_ids))
        or set(observed_rule_ids) != set(expected_rule_ids)
        or len(observed_rule_ids) != len(expected_rule_ids)
    ):
        return _clarification(
            "Please provide 2 to 50 completes without repetition, verbatimcandidate-rule ID;"
            "Models cannot complete, replace, omit or extrapolate rules from the pronoun.",
            code="voting_candidate_rules_not_grounded",
            fields=("rule_ids",),
        )

    strategy_type = str(inputs["strategy_type"])
    observed_strategy_types = {
        candidate for candidate, _start, _end in strategy_type_mentions
    }
    if observed_strategy_types != {strategy_type}:
        return _clarification(
            "Please indicate in a visible and single noteVoting SourceStrategy Pool type;missing, multiple"
            "The platform will not select for users if the type or the draft structure is inconsistentapproval/reject/"
            "limit/pricing/segmentation.",
            code="voting_candidate_strategy_type_not_grounded",
            fields=("strategy_type",),
        )

    n_bindings = _voting_n_bindings(
        utterance[command_span[0] : command_span[1]]
    )
    if (
        not n_bindings
        or {value for value, _k in n_bindings} != {inputs["n"]}
        or any(
            supplied_k is not None and supplied_k != len(expected_rule_ids)
            for _value, supplied_k in n_bindings
        )
    ):
        return _clarification(
            "Please specify and give the only number of rules.n-of-k Hit threshold, e.g. \"n=2)"
            "or \"3 Select 2\", multiple thresholds, wrongk The platform will not select for users if the draft is inconsistent.",
            code="voting_candidate_n_not_grounded",
            fields=("n",),
        )
    return result

def _voting_n_bindings(utterance: str) -> tuple[tuple[int, int | None], ...]:
    bindings: list[tuple[int, int | None]] = []
    for n, k, _start, _end in _voting_n_mentions(utterance):
        binding = (n, k)
        if binding not in bindings:
            bindings.append(binding)
    return tuple(bindings)
