"""tree request-compiler handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
from collections.abc import Sequence
import math
import re
import unicodedata

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import AUTOMATIC_TREE_DIRECTIONS
    from . import StandardWorkflowRequestDraft
    from . import StrategyRequestCompilation
    from . import _SCORECARD_SECOND_OPERATION_RE
    from . import _clarification
    from . import _ratio_token_value
    from . import _utterance_requests_automatic_tree_follow_up
    from . import _utterance_supports_automatic_tree_column_role
    from . import _utterance_supports_automatic_tree_direction
    from . import _utterance_supports_automatic_tree_feature
    from . import _utterance_supports_automatic_tree_number

_AUTOMATIC_TREE_LEAF_SELECTION_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])automatic-tree-leaf-selection-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_INTERACTIVE_TREE_FRONTIER_SELECTION_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])interactive-tree-frontier-selection-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])"
    r"interactive-tree-frontier-group-selection-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_AUTOMATIC_TREE_ASSET_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])candidate-asset-[0-9a-f]{32}(?![A-Za-z0-9_-])"
)

_INTERACTIVE_TREE_SOURCE_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])"
    r"(?:candidate-asset|interactive-tree-revision)-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_INTERACTIVE_TREE_NODE_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])node-[0-9a-f]{20}(?![A-Za-z0-9_-])"
)

_INTERACTIVE_TREE_SPLIT_SEARCH_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])interactive-tree-split-search-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])interactive-tree-split-candidate-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_INTERACTIVE_TREE_REVISION_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])interactive-tree-revision-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_INTERACTIVE_TREE_FRONTIER_NODE_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:node|leaf)-[0-9a-f]{20}"
    r"(?![A-Za-z0-9_-])"
)

_INTERACTIVE_TREE_FRONTIER_SUBJECT_RE = re.compile(
    r"(?:Interactive(?:Pattern)?Tree|Tree Revision|Modify Tree|Front(?:Nodes)?|"
    r"interactive[-\s]*tree|tree\s+revision|frontier(?:\s+node)?)",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_FRONTIER_ACTION_RE = re.compile(
    r"(?:Physicalization|Solid|Create(?:Selection|Pointer)|Select)|"
    r"(?<![A-Za-z0-9_])(?:materialize|persist|select)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_FRONTIER_GROUP_SEMANTICS_RE = re.compile(
    r"(?<![A-Za-z0-9_])OR(?![A-Za-z0-9_])|"
    r"(?:Logical or|or relationship|Any(?:Nodes|Members)?Hit.|"
    r"(?:Press|Here.|Use)\s*or\s*(?:Relations|Conditions|Logical)?(?:Group|Group))",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_FRONTIER_GROUP_INTENT_RE = re.compile(
    r"(?:Group|Group|Group)|"
    r"(?<![A-Za-z0-9_])group(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_FRONTIER_GROUP_AMBIGUOUS_SELECTION_RE = re.compile(
    r"(?:All|All|Group|Group|Several|Multiple|These.|above|Just now.(?:Those.)?|"
    r"I'd better.|Best|Best|Worst|Worst|Risk highest|The worst rate of bad.|"
    r"Automatic(?:Selection|Selection|Recommendations))"
    r"[^,,;;.\n]{0,32}(?:Front|Nodes|Ip(?:Son|Nodes)?)|"
    r"(?<![A-Za-z0-9_])(?:all|every|some|several|these|those|"
    r"best|worst|highest[-\s]+risk|automatically\s+(?:select|pick|recommend))"
    r"[^,;.!?\n]{0,32}(?:frontier|nodes?|leaves)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_FRONTIER_GROUP_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:group_id|selection_id|selection_hash)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_FRONTIER_AMBIGUOUS_SELECTION_RE = re.compile(
    r"(?:I'd better.|Best|Best|Worst|Worst|Risk highest|The worst rate of bad.|"
    r"Automatic(?:Selection|Selection|Recommendations))"
    r"[^,,;;.\n]{0,24}(?:Front|Nodes|Ip(?:Son|Nodes)?)|"
    r"(?<![A-Za-z0-9_])(?:best|worst|highest[-\s]+risk|"
    r"automatically\s+(?:select|pick|recommend))"
    r"[^,;.!?\n]{0,24}(?:frontier|node|leaf)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_FRONTIER_NEGATED_OR_NONCURRENT_RE = re.compile(
    r"[??]|(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Cancel|Undo|Ban|"
    r"Can you...|Can I?|Is it possible?|Is that okay?|Can you...|How's that?|What?|Assumptions|Suppose...|If|"
    r"Later|The future.|In the future|Later.|Before|Before|Go on.|Last time.)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cancel|can\s+you|"
    r"could\s+you|how\s+to|what\s+if|later|previously|"
    r"in\s+the\s+future)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_FRONTIER_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:source_artifact_id|artifact_(?:id|hash)|"
    r"expected_[A-Za-z0-9_]*(?:hash|id)|revision_hash|semantic_tree_id|"
    r"tree_hash|fragment_(?:id|hash)|rule_id|effect_id|condition|metrics|"
    r"dataset_id|workspace_(?:revision|generation)|sample_design_ref)"
    r"(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:artifact|content|selection|tree|fragment)\s+hash"
    r"(?![A-Za-z0-9_])|(?:Work|Products|Contents|Selection|Tree|Snippet)\s*(?:hash|Hash.)",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_PRUNE_ACTION_RE = re.compile(
    r"(?:Cut|Cut the branches.|Delete(?:The|This.|Assign)?(?:Nodes|Subtree)|Merge(?:The|This.|Assign)?Subtree)|"
    r"(?<![A-Za-z0-9_])prune_subtree(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:prune|remove|delete)\s+"
    r"(?:the\s+)?(?:node|subtree)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_THRESHOLD_ACTION_RE = re.compile(
    r"(?:Adjustment|Reconciliation|Modify|Change|Settings|Set|Changes)"
    r"[^,,;;..!?!?\n]{0,180}(?:Split|Severation)?Threshold|"
    r"(?:Split|Severation)?Threshold"
    r"[^,,;;..!?!?\n]{0,180}(?:Adjustment|Reconciliation|Modify|Change|Settings|Set|For|Replace with)|"
    r"(?<![A-Za-z0-9_])adjust_split_threshold(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:adjust|change|set)\s+(?:the\s+)?"
    r"(?:split\s+)?threshold(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_FEATURE_ACTION_RE = re.compile(
    r"(?:Replace|Replacement|Modify|Adjustment|Change|Replace|Settings)"
    r"[^,,;;..!?!?\n]{0,180}(?:Split|Severation)?(?:Characteristics|Fields|Variables)|"
    r"(?:Split|Severation)?(?:Characteristics|Fields|Variables)"
    r"[^,,;;..!?!?\n]{0,180}(?:Replace|Replacement|Modify|Adjustment|For|Replace with|Change)|"
    r"(?<![A-Za-z0-9_])replace_split_feature(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:replace|change|set)\s+(?:the\s+)?"
    r"(?:split\s+)?feature(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_FEATURE_VALUE_RE = re.compile(
    r"(?:New\s*)?(?:Split|Severation)?(?:Characteristics|Fields|Variables)\s*"
    r"(?:Replace|Replacement|Modify|Adjustment|Settings|Change)?\s*"
    r"(?:Yes|Done.|Present.|=|:|:)\s*"
    r"(?P<zh_feature>[A-Za-z0-9_.\-\u4e00-\u9fff]+)|"
    r"(?<![A-Za-z0-9_])(?:replace|change|set)\s+(?:the\s+)?"
    r"(?:new\s+)?(?:split\s+)?feature\s+(?:to|=|:)\s*"
    r"(?P<en_feature>[A-Za-z0-9_.\-]+)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_THRESHOLD_AMBIGUOUS_RE = re.compile(
    r"(?:Tune it up a little bit.|Tranquility(?:Tight.|Section)?A little.|Optimization(?:One second.)?|Automatic(?:Adjustment|Reconciliation|Optimization|Selection|"
    r"Recommendations)|Best threshold|Best Threshold|Best suited threshold|All Nodes|All Nodes|Every node)|"
    r"(?<![A-Za-z0-9_])(?:slightly|best|optimal|automatically\s+"
    r"(?:adjust|optimi[sz]e|select)|all\s+nodes?|every\s+node)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_FEATURE_AMBIGUOUS_RE = re.compile(
    r"(?:Best Feature|Best features|It's the most appropriate.(?:It's...)?(?:Characteristics|Fields|Variables)|"
    r"Automatic(?:Selection|Recommendations|Replace|Replacement)(?:Characteristics|Fields|Variables)|"
    r"All Features|All features|Every feature)|"
    r"(?<![A-Za-z0-9_])(?:best|optimal)\s+(?:split\s+)?feature|"
    r"(?<![A-Za-z0-9_])automatically\s+(?:select|recommend|replace)"
    r"\s+(?:the\s+)?(?:split\s+)?feature(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_THRESHOLD_VALUE_RE = re.compile(
    r"(?:New\s*)?(?:Split|Severation)?Threshold\s*"
    r"(?:Adjustment|Reconciliation|Modify|Change|Settings|Set|Change)?\s*"
    r"(?:Yes|Done.|Present.|=|:|:)\s*"
    r"(?P<zh_value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)|"
    r"(?<![A-Za-z0-9_])(?:adjust|change|set)\s+(?:the\s+)?"
    r"(?:new\s+)?(?:split\s+)?threshold\s+(?:to|=|:)\s*"
    r"(?P<en_value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_AMBIGUOUS_NODE_RE = re.compile(
    r"(?:I'd better.|Best|Best|Worst|Risk highest|The worst rate of bad.|Automatic(?:Selection|Selection)|"
    r"Not good.|Instability)"
    r"[^,,;;.\n]{0,20}(?:Nodes|Subtree)|"
    r"(?<![A-Za-z0-9_])(?:best|worst|highest[- ]risk|unstable)"
    r"\s+(?:node|subtree)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_NEGATED_OR_NONCURRENT_RE = re.compile(
    r"[??]|(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Cancel|Undo|Ban|"
    r"Can you...|Can I?|Is it possible?|Is that okay?|Can you...|How's that?|What?|Assumptions|Suppose...|If|"
    r"Later|The future.|In the future|Later.|Before|Before|Go on.|Last time.)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cancel|can\s+you|"
    r"could\s+you|how\s+to|what\s+if|later|previously|"
    r"in\s+the\s+future)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_INTERACTIVE_TREE_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:source_artifact_id|expected_[A-Za-z0-9_]*hash|"
    r"dataset_id|workspace_(?:revision|generation)|sample_design_ref|"
    r"frontier_node_ids|visible_node_ids|metrics|condition|tree_json)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_APPLY_TARGET_RE = re.compile(
    r"(?:Automatic(?:Decision-making)?Tree|Decision Tree|Full Tree|"
    r"candidate-asset-[0-9a-f]{32}|"
    r"(?<![A-Za-z0-9_])(?:automatic|decision)\s+tree(?![A-Za-z0-9_]))"
    r"[^,,;;..!?!?\n]{0,100}"
    r"(?:Apply|Implementation|Write back|Back up.|Fill Back|Mark|"
    r"(?<![A-Za-z0-9_])(?:apply|write[-\s]*back|assign)(?![A-Za-z0-9_]))|"
    r"(?:Apply|Implementation|Write back|Back up.|Fill Back|Mark|"
    r"(?<![A-Za-z0-9_])(?:apply|write[-\s]*back|assign)(?![A-Za-z0-9_]))"
    r"[^,,;;..!?!?\n]{0,100}"
    r"(?:Automatic(?:Decision-making)?Tree|Decision Tree|Full Tree|"
    r"candidate-asset-[0-9a-f]{32}|"
    r"(?<![A-Za-z0-9_])(?:automatic|decision)\s+tree(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_APPLY_ACTION_RE = re.compile(
    r"(?:Apply|Implementation|Write back|Back up.|Fill Back|Mark)|"
    r"(?<![A-Za-z0-9_])(?:apply|write[-\s]*back|assign)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_APPLY_NOT_AUTHORIZED_RE = re.compile(
    r"[??]|"
    r"(?:Don't.|No, I'm fine.|No need.|Don't.|Ban|Cancel|Not yet.|Not yet.|Unauthorized|"
    r"Can you...|Can I?|Is it possible?|Is that okay?|Can you...|How's that?|What?|What?|Assumptions|Suppose...|If|"
    r"Later|The future.|In the future|Later.|Later.|Tomorrow.|Next week.|Next month|Before|Before|Go on.|Last time.)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cancel|can\s+you|"
    r"could\s+you|would\s+you|how\s+to|what\s+if|later|tomorrow|"
    r"previously|in\s+the\s+future)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_APPLY_FOLLOW_UP_RE = re.compile(
    r"(?:Policy pool|Rule pool|Into the pool.|Add[^,,;;.\n]{0,12}(?:Ji.|Pool)|"
    r"Accepted|Adopt|Deployment|Online.|Production|Publishe to?Production|Generate Report|Form a report|Report.|"
    r"Physicalization[^,,;;.\n]{0,16}(?:Ip|leaf)|Selection[^,,;;.\n]{0,16}(?:Ip|leaf)|"
    r"(?:Reject|Approval|Pass.|Review)[^,,;;.\n]{0,20}(?:Client|Hit.)|"
    r"(?<![A-Za-z0-9_])(?:strategy\s+pool|add\s+to\s+(?:the\s+)?pool|"
    r"adopt|deploy|production|go[-\s]+live|generate\s+(?:a\s+)?report|"
    r"materialize\s+(?:a\s+)?leaf|select\s+(?:a\s+)?leaf)"
    r"(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_APPLY_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:source_artifact_id|expected_(?:artifact_)?content_hash|"
    r"expected_asset_(?:id|hash)|expected_tree_result_hash|dataset_id|"
    r"workspace_revision|analysis_generation|semantic_mapping_hash|activate_result)"
    r"(?![A-Za-z0-9_])|"
    r"(?:artifact|Assets|Dataset|workspace|Workspace|Semantic Map)\s*(?:hash|Hash.|revision|Version)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_APPLY_OUTPUT_COLUMN_RE = re.compile(
    r"(?P<label>Leaf Node|Leaves.|leaf(?:\s*id)?|Rule|rule(?:\s*id)?)\s*"
    r"(?:It's...)?\s*(?:Output)?\s*(?:Fields|Columns)(?:Synchronising folder)?\s*"
    r"(?:Yes|Yes.|Please.|Set as|Set As|=|:|:)?\s*"
    r"(?P<column>[A-Za-z_][A-Za-z0-9_]{0,63})",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_APPLY_NAMED_OUTPUT_COLUMN_RE = re.compile(
    r"(?P<field>leaf_id_column|rule_id_column)\s*(?:=|:|:)\s*"
    r"(?P<column>[A-Za-z_][A-Za-z0-9_]{0,63})",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_APPLY_GENERIC_OUTPUT_COLUMN_RE = re.compile(
    r"(?:Output|Result)\s*(?:Fields|Columns)(?:Synchronising folder)?\s*"
    r"(?:Yes|Yes.|Please.|Set as|Set As|=|:|:)?\s*"
    r"[A-Za-z_][A-Za-z0-9_]{0,63}",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])leaf-[0-9a-f]{20}(?![A-Za-z0-9_-])"
)

_AUTOMATIC_TREE_LEAF_AMBIGUOUS_SELECTION_RE = re.compile(
    r"(?:I'd better.|Best|Best|Worst|Worst|"
    r"(?:Bad debt rate|Bad rate|Risk|Capture Rate|Pass rate|Proceeds)\s*"
    r"(?:Highest|Minimum|Max|Min)|"
    r"(?:Highest|Minimum|Max|Min)\s*"
    r"(?:Bad debt rate|Bad rate|Risk|Capture Rate|Pass rate|Proceeds)|"
    r"(?<![A-Za-z0-9_])(?:best|worst|"
    r"(?:highest|lowest|maximum|minimum)[-\s]+(?:bad[-\s]+rate|risk|lift|"
    r"capture[-\s]+rate|approval[-\s]+rate|profit))(?![A-Za-z0-9_]))"
    r"[^,,;;.\n]{0,20}(?:Ip(?:Son|Nodes)?|(?<![A-Za-z0-9_])leaf(?![A-Za-z0-9_]))|"
    r"(?:Ip(?:Son|Nodes)?|(?<![A-Za-z0-9_])leaf(?![A-Za-z0-9_]))"
    r"[^,,;;.\n]{0,20}(?:I'd better.|Best|Best|Worst|Worst|"
    r"(?:Bad debt rate|Bad rate|Risk|Capture Rate|Pass rate|Proceeds)\s*"
    r"(?:Highest|Minimum|Max|Min)|"
    r"(?<![A-Za-z0-9_])(?:best|worst|"
    r"(?:highest|lowest|maximum|minimum)[-\s]+(?:bad[-\s]+rate|risk|lift|"
    r"capture[-\s]+rate|approval[-\s]+rate|profit))(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_MATERIALIZATION_ACTION_RE = re.compile(
    r"(?:Physicalization|Solid|Select|(?<!Wait.)Selection)|"
    r"(?<![A-Za-z0-9_])(?:materialize|select|pick)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_REASON_RE = re.compile(
    r"(?:(?:Selection)?Rationale|Reason|Annotations)\s*(?:Yes.|Yes|[::])\s*"
    r"(?P<zh>(?:(?!(?:But...(?:Yes.)?|But...|But...|However,|But...|And...(?:Yes.)?))[^,,;;.])+)|"
    r"(?<![A-Za-z0-9_])(?:selection\s+reason|reason|rationale)"
    r"\s*(?::|is)\s*"
    r"(?P<en>(?:(?!(?<![A-Za-z0-9_])(?:but|yet|however|instead)"
    r"(?![A-Za-z0-9_]))[^,;.!?])+)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_REASON_NEGATION_RE = re.compile(
    r"(?:Don't.|No, no.|No need.|No, I don't.|Don't.|Ban)\s*(?:Use|Fill|Records|Reservations|Adopt)?\s*$|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never)\s+(?:use|record|keep)?\s*$",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_REASON_REPLACEMENT_RE = re.compile(
    r"(?:(?:Selection)?Rationale|Reason|Annotations)\s*(?:Yes.|Yes|[::])|"
    r"(?:For|Replace with|Replace|Replace with)|"
    r"(?<![A-Za-z0-9_])(?:(?:reason|rationale)\s*(?::|is)|instead|"
    r"rather\s+than)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_NEGATED_REASON_CLAUSE_RE = re.compile(
    r"(?:Don't.|No, no.|No need.|No, I don't.|Don't.|Ban)\s*(?:Use|Fill|Records|Reservations|Adopt)?\s*"
    r"(?:(?:Selection)?Rationale|Reason|Annotations)\s*(?:Yes.|Yes|[::])\s*"
    r"(?:(?!(?:But...(?:Yes.)?|But...|But...|However,|But...|And...(?:Yes.)?))[^,,;;.])+|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never)\s+"
    r"(?:use|record|keep)?\s*(?:selection\s+reason|reason|rationale)"
    r"\s*(?::|is)\s*(?:(?!(?<![A-Za-z0-9_])(?:but|yet|however|instead)"
    r"(?![A-Za-z0-9_]))[^,;.!?])+",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_REASON_FORBIDDEN_OPERATION_RE = re.compile(
    r"(?:Policy pool|Rule pool|(?<![A-Za-z0-9_])(?:strategy\s+)?pool(?![A-Za-z0-9_])|"
    r"Accepted|Deployment|Online.|Production|Input(?:Production|Use)|Publishe to?Production|Release|Enable|Entry into force|"
    r"Activate|Landing.|Implementation|Apply|Use|Run|Reject|Adoption of approvals|Approval|"
    r"Write back|Back up.|Fill Back|"
    r"(?<![A-Za-z0-9_])(?:adopt(?:s|ed|ing)?|deploy(?:s|ed|ing)?|"
    r"promot(?:e|es|ed|ing)|activat(?:e|es|ed|ing)|enabl(?:e|es|ed|ing)|"
    r"effective|publish(?:es|ed|ing)?|releas(?:e|es|ed|ing)|"
    r"launch(?:es|ed|ing)?|production|execut(?:e|es|ed|ing)|"
    r"appl(?:y|ies|ied|ying)|us(?:e|es|ed|ing)|run(?:s|ning)?|"
    r"reject(?:s|ed|ing)?|approv(?:e|es|ed|ing)|rout(?:e|es|ed|ing)|"
    r"go[-\s]+live|roll[-\s]+out|"
    r"write[-\s]*back)"
    r"(?![A-Za-z0-9_])|"
    r"(?:Actions|action)\s*(?:Replace with|Set as|Set As|[:=])|"
    r"(?:Reject|Pass.|Approval|Manual review|Review)[^,,;;.\n]{0,16}(?:Client|Hit.|Ip)|"
    r"(?:Client|Hit.|Ip)[^,,;;.\n]{0,16}(?:Reject|Pass.|Approval|Manual review|Review)|"
    r"(?<![A-Za-z0-9_])(?:reject|approve|review|route)"
    r"[^,;.!?\n]{0,32}(?:match(?:ing|ed)?|customers?|leaves?|leaf)|"
    r"(?<![A-Za-z0-9_])(?:match(?:ing|ed)?|customers?|leaves?|leaf)"
    r"[^,;.!?\n]{0,32}(?:reject|approve|review|route)(?![A-Za-z0-9_])|"
    r"(?:And then...|And then...|Catch.|Meanwhile...|Direct|"
    r"(?<![A-Za-z0-9_])(?:and\s+then|then|afterwards)(?![A-Za-z0-9_])))",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_REASON_EXTREME_RE = re.compile(
    r"(?=[^,,;;.\n]{0,120}(?:All|All|Other|Other|"
    r"(?<![A-Za-z0-9_])(?:all|every|any)\s+other(?![A-Za-z0-9_])))"
    r"(?=[^,,;;.\n]{0,120}(?:Higher|Less than|Greater than|less than|Better than|Less than|"
    r"(?<![A-Za-z0-9_])(?:higher|lower|greater|less|better|worse)"
    r"(?![A-Za-z0-9_])))|"
    r"(?:Highest|Minimum|Max|Min|I'd better.|Best|Worst|Worst|The most dangerous.|First|First|Rank|Line)|"
    r"I'm sorry.\s*(?:\d+|[One, two, three, four, five, six, seven, eight, nine hundred.]+)\s*(?:Synchronising folder|bit)?|"
    r"(?:Lower|Low|Head|Bottom of the mat.|End)|(?:NO\.?\s*1|#\s*1|Front\s*\d+\s*Synchronising folder)|"
    r"(?:Higher|Less than|Greater than|less than|Better than|Less than)[^,,;;.\n]{0,24}"
    r"(?:All|All|Other|Other)|"
    r"(?<![A-Za-z0-9_])(?:best|worst|top(?:[-\s]*\d+)?|most|least|highest|"
    r"lowest|maximum|minimum|largest|smallest|greatest|fewest|riskiest|safest|"
    r"optimal|leading|trailing|rank(?:ed|ing)?|number\s+(?:one|two|three|\d+)|"
    r"first|second|third|fourth|\d+(?:st|nd|rd|th)|no\.?\s*1|#\s*1|"
    r"(?:higher|lower|greater|less|better|worse)[^,;.!?\n]{0,16}\s+than\s+"
    r"(?:all|every|any)\s+other)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_RATIONALE_START_RE = re.compile(
    r"^(?:"
    r"(?:(?:Manual|Operations|Risk|Compliance|Regulation|Experts|Sample|Data|Model|Item|Candidates)\s*)?"
    r"(?:Confirm.|Review|Evaluation|Audit|Authentication|Analysis|Judgement|Discussion|Records|Audit|Test|Research|Request|Basis)|"
    r"(?:For|For|Follow-up)\s*[^,,;;.\n]{0,20}"
    r"(?:Confirm.|Review|Evaluation|Audit|Authentication|Analysis|Judgement|Discussion|Records|Audit|Test|Research)|"
    r"(?:(?:manual|business|risk|compliance|regulatory|expert|sample|data|"
    r"model|project)\s+)?(?:confirmation|review|assessment|validation|analysis|"
    r"judgment|discussion|audit|testing|research|requirement|evidence)|"
    r"(?:for|to\s+support)\s+[^,;.!?\n]{0,24}(?:review|assessment|validation|"
    r"analysis|audit|testing|research)"
    r")",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_RATIONALE_TOKEN_RE = re.compile(
    r"(?:Manual|Operations|Risk|Compliance|Regulation|Experts|Sample|Data|Model|Item|Candidates|The|This.|This time.|"
    r"Current round|Next round.|Follow-up|The future.|Phase|Leaf Node|Leaves.|Ip|For|For|By|As|- Wait.|Again.|"
    r"Confirm.|Review|Evaluation|Audit|Authentication|Analysis|Judgement|Discussion|Records|Audit|Test|Research|Request|Basis|Annotations|"
    r"(?<![A-Za-z0-9_])(?i:manual|business|risk|compliance|regulatory|expert|"
    r"sample|data|model|project|candidate|this|current|next|later|future|phase|"
    r"leaf|for|to|support|confirmation|review|assessment|validation|analysis|"
    r"judgment|discussion|audit|testing|research|requirement|evidence)"
    r"(?![A-Za-z0-9_])|[A-Z0-9][A-Z0-9._-]*|[\u00c0-\u024f]+)"
)

_AUTOMATIC_TREE_LEAF_RATIONALE_PUNCTUATION_RE = re.compile(
    r"[\s,,;;.::,.!?!?()()\[\]{}\-_/]+"
)

_AUTOMATIC_TREE_LEAF_RATIONALE_DECISION_SUBJECT_RE = re.compile(
    r"(?:Hit.|Client|Applicant|Borrower|User|Business Action|Policy pool|Rule pool|Production|Production)|"
    r"(?<![A-Za-z0-9_])(?:match(?:ing|ed)?|customers?|applicants?|borrowers?|"
    r"actions?|pool|production)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_ALLOWED_REQUEST_TOKEN_RE = re.compile(
    r"(?:Please.|Help me.|Trouble.|From|Yes.|- Put it on.|Will|Only|Only|Yeah.|and|and|or|But...(?:Yes.)?|But...|But...|"
    r"However,|But...|And...(?:Yes.)?|One.|This.|The|Assign|Precision|"
    r"Complete|Autotree|Candidate Tree|Decision Tree|Tree assets|Candidate assets|Assets|Tree|Medium|- Yes.|Lee.|It's...|"
    r"Leaf Node|Leaves.|Ip|Nodes|Physicalization|Solid|Select|(?<!Wait.)Selection|Pointer|References|"
    r"Again.|Confirm.|Yes.|ID|id|"
    r"(?<![A-Za-z0-9_])(?:please|from|in|the|a|an|this|that|exact|specified|"
    r"automatic|decision|candidate|tree|asset|leaf|node|materialize|select|pick|"
    r"pointer|reference|confirm|again|only|and|or|but|yet|however|instead)"
    r"(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_REQUEST_PUNCTUATION_RE = re.compile(
    r"[\s,,;;.::,.!?!?()()\[\]{}\-_/]+"
)

_AUTOMATIC_TREE_LEAF_POOL_CHAIN_RE = re.compile(
    r"(?:Add|Writing|Put it in.|Add to).{0,16}(?:Policy pool|strategy\s*pool)|Into the pool.|"
    r"(?<![A-Za-z0-9_])add\b.{0,24}\b(?:strategy\s*)?pool\b",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_ACTION_CHAIN_RE = re.compile(
    r"(?:and|And...|And then...|And then...|Again.|and|and|But...(?:Yes.)?|But...|But...|"
    r"and(?:\s+then)?|but|yet)"
    r"[^,,;;.\n]{0,48}"
    r"(?:Set As?[^,,;;.\n]{0,12}(?:Actions|action)|Reject|Adoption of approvals|Manual review|"
    r"(?<![A-Za-z0-9_])(?:set\s+(?:the\s+)?action|reject|approve|review)"
    r"(?![A-Za-z0-9_]))|"
    r"(?:As|Set as|Set As|Convert to|Implementation)"
    r"[^,,;;.\n]{0,20}"
    r"(?:Reject|Pass.|Approval|Manual review|Actions|"
    r"(?<![A-Za-z0-9_])(?:action|reject|approve|review)(?![A-Za-z0-9_]))|"
    r"(?:^|[,,;;])\s*(?:Direct|Immediately)?"
    r"(?:Reject|Jean.[^,,;;.\n]{0,20}Adoption of approvals|Turn[^,,;;.\n]{0,8}Manual review|"
    r"(?<![A-Za-z0-9_])action\s*[:=]\s*(?:reject|approve|review)"
    r"(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_LIFECYCLE_CHAIN_RE = re.compile(
    r"(?:and|And...|And then...|And then...|Again.|and|and|But...(?:Yes.)?|But...|But...|"
    r"and(?:\s+then)?|but|yet)"
    r"[^,,;;.\n]{0,40}(?:Accepted|Use this.(?:Article|individual)|Deployment|Online.|"
    r"(?<![A-Za-z0-9_])(?:adopt|deploy)(?![A-Za-z0-9_]))|"
    r"(?:^|[,,;;])\s*(?:Direct|Immediately)?(?:Accepted|Adopt|Deployment|Online.|"
    r"(?<![A-Za-z0-9_])(?:adopt|deploy)(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_WRITEBACK_CHAIN_RE = re.compile(
    r"(?:Write back|Back up.|write[-\s]*back)"
    r"[^,,;;.\n]{0,24}(?:Ip(?:Son|Nodes)?\s*(?:id|ID)?|leaf|Dataset|dataset)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_NEGATED_CLAUSE_RE = re.compile(
    r"(?:Yeah.\s*)?(?:Don't.|Not anymore.|No need.|No, I don't.|Don't.|Ban)\s*(?:"
    r"(?:Automatic\s*)?(?:Selection|Selection|Recommendations|Find out.)\s*"
    r"(?:I'd better.|Best|Best|Worst|Worst|Risk highest|The worst rate of bad.)?\s*Ip(?:Son|Nodes)?|"
    r"(?:Add|Writing|Put it in.|Add)\s*(?:Policy pool|Rule pool|pool)|"
    r"(?:Accepted|Deployment|Online.)(?:\s*or\s*(?:Accepted|Deployment|Online.))*"
    r")|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't)\s+(?:"
    r"(?:automatically\s+)?(?:select|pick)\s+(?:the\s+)?"
    r"(?:best|worst|highest[-\s]+risk)?\s*leaf|"
    r"add\s+(?:it\s+)?to\s+(?:the\s+)?(?:strategy\s+)?pool|"
    r"(?:adopt|deploy)(?:\s+it)?(?:\s+or\s+(?:adopt|deploy)(?:\s+it)?)*"
    r")(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])without\s+adding\s+(?:it\s+)?to\s+"
    r"(?:the\s+)?(?:strategy\s+)?pool(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_NODE_TOKEN_PATTERN = (
    r"(?:"
    r"(?:(?:Bad rate|Risk)\s*Highest(?:It's...)?|High risk|Terminal|End)\s*(?:Leaves.|Leaf Node|Nodes)|"
    r"Ip(?:Son|Nodes)?(?!Weights|Sample|Number)|"
    r"(?<![A-Za-z0-9_])(?:leaf|leaves)(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:high(?:est)?[-\s]+risk|terminal|end)[-\s]+nodes?"
    r"(?![A-Za-z0-9_])"
    r")"
)

_AUTOMATIC_TREE_DECISION_EFFECT_PATTERN = (
    r"(?:Reject(?!Rate|Number|Number|Percentage)|Pass.(?!Rate|Number|Number|Percentage)|"
    r"Approval(?!Rate|Number|Number|Percentage)|Review(?!Rate|Number|Number|Percentage)|"
    r"Amount|Pricing|Group|Actions|Policy|"
    r"(?<![A-Za-z0-9_])(?:action|reject|approve|review|limit|pricing|segment|strategy)"
    r"(?:s|d|ed|ing)?(?![A-Za-z0-9_]))"
)

_AUTOMATIC_TREE_MULTI_STEP_RE = re.compile(
    r"(?:And then...|And then...|After|Again.|Meanwhile...|and(?:and)?|and\s+then).{0,60}"
    r"(?:Automatic\s*)?(?:Selection|Selection|Recommendations|Find out.|(?<!Wait.)Choose|select|pick|identify|materialize|Add|add).{0,24}"
    r"(?:Ip(?:Son|Nodes)?(?!Weights|Sample|Number)|leaf|Policy pool|strategy\s*pool|pool)",
    re.IGNORECASE | re.DOTALL,
)

_AUTOMATIC_TREE_BEST_LEAF_RE = re.compile(
    r"(?:Automatic\s*)?(?:Selection|Selection|Recommendations|Find out.|(?<!Wait.)Choose|select|pick|identify).{0,12}"
    r"(?:I'd better.|Best|Best|best).{0,8}(?:Ip(?:Son|Nodes)?(?!Weights|Sample|Number)|leaf)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_REVERSED_BEST_LEAF_RE = re.compile(
    r"(?:I'd better.|Best|Best|best).{0,8}(?:Ip(?:Son|Nodes)?(?!Weights|Sample|Number)|leaf).{0,12}"
    r"(?:Automatic\s*)?(?:Selection|Selection|Recommendations|Find out.|(?<!Wait.)Choose|select|pick|identify)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_FOLLOW_UP_RE = re.compile(
    r"(?:Selection|Selection|Solid|Physicalization|(?<!Wait.)Choose|select|pick|materialize).{0,16}"
    r"(?:Ip(?:Son|Nodes)?(?!Weights|Sample|Number)|leaf)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_POOL_FOLLOW_UP_RE = re.compile(
    r"(?:Add|Writing|Put it in.|add).{0,16}(?:Policy pool|strategy\s*pool|pool)|Into the pool.",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_DECISION_FOLLOW_UP_RE = re.compile(
    r"(?:"
    r"(?:- Put it on.|Will)?\s*(?:Any|Any|Some.|The|This.)?\s*"
    r"(?:Ip(?:Son|Nodes)?(?!Weights|Sample|Number)|leaf)"
    r"[^,,;;.\n]{0,24}(?:As|Set as|Set As|Configure As|Use as|Convert to|Yes)"
    rf"[^,,;;.\n]{{0,16}}{_AUTOMATIC_TREE_DECISION_EFFECT_PATTERN}|"
    r"(?:Settings|Configure|Adopt|Use|- Put it on.|Will)"
    r"[^,,;;.\n]{0,20}(?:Ip(?:Son|Nodes)?(?!Weights|Sample|Number)|leaf)"
    rf"[^,,;;.\n]{{0,20}}{_AUTOMATIC_TREE_DECISION_EFFECT_PATTERN}"
    r")",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_HEURISTIC_LEAF_FOLLOW_UP_RE = re.compile(
    r"(?:Adopt|Use|Select|Selection|Selection|Recommendations|pick|select|use)"
    r"[^,,;;.\n]{0,20}(?:Bad rate|Risk|lift|Capture Rate|Pass rate|Proceeds|profit)?"
    r"[^,,;;.\n]{0,10}(?:Highest|Minimum|Max|Min|I'd better.|Best|Best|best|highest|lowest)"
    r"[^,,;;.\n]{0,10}(?:Ip(?:Son|Nodes)?(?!Weights|Sample|Number)|leaf)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_NODE_RANK_FOLLOW_UP_RE = re.compile(
    rf"(?:Rank|Sort|rank|sort)[^,,;;.\n]{{0,32}}{_AUTOMATIC_TREE_NODE_TOKEN_PATTERN}|"
    rf"{_AUTOMATIC_TREE_NODE_TOKEN_PATTERN}[^,,;;.\n]{{0,32}}(?:Rank|Sort|rank|sort)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_NODE_SELECT_FOLLOW_UP_RE = re.compile(
    rf"(?:Selection|Selection|Reservations|Adopt|Select|select|pick|retain|keep|use)"
    rf"[^,,;;.\n]{{0,24}}{_AUTOMATIC_TREE_NODE_TOKEN_PATTERN}|"
    rf"{_AUTOMATIC_TREE_NODE_TOKEN_PATTERN}[^,,;;.\n]{{0,24}}"
    r"(?:Selection|Selection|Reservations|select|pick|retain|keep)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_NODE_EXTRACT_FOLLOW_UP_RE = re.compile(
    rf"(?:Extract|extract)\s*(?!(?:Complete|All|All|complete|all))"
    rf"[^,,;;.\n]{{0,24}}{_AUTOMATIC_TREE_NODE_TOKEN_PATTERN}",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LIFECYCLE_FOLLOW_UP_RE = re.compile(
    r"(?:Accepted|Adopt)\s*(?:This one.|The|Current|The whole thing.)\s*(?:Tree|Decision Tree|Model|Result)|"
    r"(?:Deployment|Online.|Publishe to?Production|Upgrade to Production|Production)|"
    r"(?<![A-Za-z0-9_])(?:adopt\s+(?:it|this\s+tree|the\s+tree)|"
    r"deploy|promote(?:\s+(?:it|this\s+tree|the\s+tree))?)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_ID_WRITEBACK_RE = re.compile(
    r"(?:Write back|Back up.|Enduring|Save|write\s*back|persist|store)"
    r"[^,,;;.\n]{0,20}(?:Ip(?:Son|Nodes)?\s*(?:ID|id|Numbering)|leaf[-_\s]*id)|"
    r"(?:Ip(?:Son|Nodes)?\s*(?:ID|id|Numbering)|leaf[-_\s]*id)"
    r"[^,,;;.\n]{0,20}(?:Write back|Back up.|Enduring|Save|write\s*back|persist|store)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_DECISION_ARTIFACT_RE = re.compile(
    r"(?:Generate|Form|Development|Configure|Implementation|create|generate|form|formulate|define|configure|execute)"
    rf"[^,,;;.\n]{{0,24}}{_AUTOMATIC_TREE_DECISION_EFFECT_PATTERN}",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_FOLLOW_UP_CLAUSE_BOUNDARY_RE = re.compile(
    r"[,,;;.\n]+|"
    r"(?:But...(?:Yes.)?|But...|But...|But...|And...(?:Yes.)?|And...|Meanwhile...|And then...|And then...|After|Catch.)|"
    r"Back(?=\s*(?:Direct|Catch.|And then...|Again.|- Put it on.|Will|Yeah.|Jean.|Basis|Implementation|Settings|Adopt|Use|"
    r"Selection|Reject|Pass.|Give|Add|Writing))|"
    r"(?<!No, no.)(?<!Don't.)(?<!No need.)(?<!No, I'm fine.)(?<!No, I don't.)(?<!Ban)(?<!Don't.)"
    r"Again.(?=\s*(?:- Put it on.|Will|Yeah.|Jean.|Basis|Direct|Implementation|Settings|Adopt|Use|Selection|Reject|Pass.|"
    r"Give|Add|Writing))|"
    r"and|"
    r"and(?=(?:- Put it on.|Will|Yeah.|Jean.|Basis|Implementation|Settings|Adopt|Use|Selection|Reject|Pass.|Give|Add|Writing))|"
    r"(?<![A-Za-z0-9_])(?:but|however|yet|and|then|afterwards|after\s+that)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_FOLLOW_UP_NEGATION_RE = re.compile(
    r"(?:Don't.|No need.|No, I'm fine.|No, I don't.|Don't.|Ban|Not anymore.|"
    r"No, no.(?=\s*(?:- Put it on.|Will|Jean.|Yeah.|Basis|Direct|Automatic|Adopt|Use|Selection|Selection|Recommendations|"
    r"Physicalization|Solid|Select|Settings|Implementation|Reject|Pass.|Approval|Review|Give|As|Add|Writing|Put it in.))|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don[')]t|never|not)(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LEAF_TOKEN_RE = re.compile(
    _AUTOMATIC_TREE_NODE_TOKEN_PATTERN,
    re.IGNORECASE,
)

_AUTOMATIC_TREE_DECISION_EFFECT_RE = re.compile(
    _AUTOMATIC_TREE_DECISION_EFFECT_PATTERN,
    re.IGNORECASE,
)

_AUTOMATIC_TREE_FOLLOW_UP_ACTION_ANCHOR_RE = re.compile(
    r"(?:Selection|Selection|Recommendations|Find out.|(?<!Wait.)Choose|Add|Writing|Put it in.|Into the pool.|As|Set as|"
    r"Settings|Set As|Configure As|Use as|Convert to|Implementation|Give|Adopt|Use|Reject|Pass.|Approval|Review|"
    r"Rank|Sort|Reservations|Extract|Accepted|Deployment|Online.|Write back|Back up.|Enduring|Save|Generate|Form|"
    r"Development|Configure|"
    r"(?<![A-Za-z0-9_])(?:select|pick|identify|materialize|add|use|route|set|"
    r"make|reject|approve|review|rank|sort|retain|extract|adopt|deploy|promote|"
    r"persist|store|create|generate|form|formulate|define|configure|execute)"
    r"(?![A-Za-z0-9_]))",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_NEGATED_FOLLOW_UP_PREFIX_RE = re.compile(
    r"^(?:\s+|[-/:]|"
    r"(?:Again.|Automatic|Direct|Only|Only|- Put it on.|Will|Jean.|Yeah.|Here.|Basis|Based on|Press|Here.|Any|Any|"
    r"Some.|The|This.|These.|This one.|The whole thing.|All|All|High risk|Low risk|Risk|Bad rate|Here.|"
    r"Risk highest|Risk lowest|The worst rate of bad.|The worst.|I'd better.|Best|Best|Complete|Terminal|End|"
    r"Leaf Node|Leaves.|Ip|Nodes|Tree|Decision Tree|Model|Result|Let's go.|"
    r"Convert to|As|Set as|Settings|Set As|Configure|Configure As|Use as|Implementation|Conduct|Give|Adopt|Use|"
    r"Selection|Selection|Recommendations|Find out.|Select|Add|Writing|Put it in.|Into the pool.|Manual|Reject|Pass.|"
    r"Approval|Review|Amount|Pricing|Group|Rule|Actions|Policy|Policy pool|Rank|Sort|Reservations|"
    r"Extract|Accepted|Deployment|Online.|Write back|Back up.|Enduring|Save|Generate|Form|Development)|"
    r"(?<![A-Za-z0-9_])(?:auto|automatically|directly|the|any|a|an|all|some|"
    r"high(?:est)?[-\s]+risk|best|worst|leaf(?:[-_][A-Za-z0-9.]+)?|leaves|"
    r"to|as|manual|use|route|pick|select|set|make|turn|into|for|reject|"
    r"approve|review|rule|action|add|materialize|strategy|pool|rank|sort|"
    r"retain|extract|adopt|deploy|promote|persist|store|create|generate|form|"
    r"formulate|define|configure|execute|it|this|tree)"
    r"(?![A-Za-z0-9_]))*$",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_NEGATED_BUILD_RE = re.compile(
    r"(?:Don't.|No need.|No, I'm fine.|No, I don't.|Don't.|Ban|No, I don't.|No, I don't.)"
    r"[^,,;;.\n]{0,40}(?:Construction(?:One.)?(?:Automatic)?(?:Decision-making)?Tree|"
    r"(?:Build|Training|Create)[^,,;;.\n]{0,12}(?:Tree|Decision Tree))|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don[')]t|never|not)"
    r"[^,,;;.\n]{0,32}(?:build|train|create)"
    r"[^,,;;.\n]{0,12}(?:tree)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_DATASET_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:dataset(?:_id)?|sample(?:_id)?)(?![A-Za-z0-9_])"
    r"\s*(?:[::=]|Yes|Yes.)\s*[^\s,,;;.]+|"
    r"(?:Use|Use|Change|Switch(?:Present.)?|Replace)\s*(?:The other one.|Other|New|Assigned?)?\s*"
    r"(?:Dataset|Sample)(?!Weights|Number)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_TARGET_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:target(?:_col|\s+column)?|label(?:_col|\s+column)?)"
    r"(?![A-Za-z0-9_])\s*(?:[::=]|Yes|Yes.)\s*[^\s,,;;.]+|"
    r"(?:Objective|Label)(?:Columns|Fields)\s*(?:[::=]|Yes|Yes.|For|Switch to)\s*"
    r"[^\s,,;;.]+",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_LABEL_POLICY_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:drop|keep)[_\s-]*(?:nan|null|missing)[_\s-]*labels?"
    r"(?![A-Za-z0-9_])|"
    r"(?:Delete|Drop|Reservations|Fill|Ignore)[^,,;;.\n]{0,12}"
    r"(?:Empty|Missing|NULL|NaN)[^,,;;.\n]{0,6}(?:Label|Target value)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_BUDGET_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:budgets?\s*[.:]\s*)?max[_\s-]*"
    r"(?:rows|features|cells|nodes|cutpoints?)(?![A-Za-z0-9_])|"
    r"(?:Most|Up to|No more than|Only|Only|Limits)[^,,;;.\n]{0,16}"
    r"[0-9]+[^,,;;.\n]{0,8}(?:Okay.|Characteristics|Variables|Cells|Nodes|Point)",
    re.IGNORECASE,
)

_AUTOMATIC_TREE_DIRECTION_GROUNDING = {
    "increasing": (
        r"(?:Undo\s*)?(?:Incremental|Up)|Positive|"
        r"(?<![A-Za-z0-9_])increasing(?![A-Za-z0-9_])"
    ),
    "decreasing": (
        r"(?:Undo\s*)?(?:Decline|Down)|Negative|"
        r"(?<![A-Za-z0-9_])decreasing(?![A-Za-z0-9_])"
    ),
    "unordered": (
        r"Orderless|Unbound(?:Direction)?|Unbound|"
        r"(?<![A-Za-z0-9_])unordered(?![A-Za-z0-9_])"
    ),
}

_AUTOMATIC_TREE_NUMBER_LABELS = {
    "max_depth": (
        r"(?<![A-Za-z0-9_])max[_\s-]*depth(?![A-Za-z0-9_])|"
        r"Max(?:Tree)?Depth|Tree depth"
    ),
    "min_leaf_count": (
        r"(?<![A-Za-z0-9_])min[_\s-]*leaf[_\s-]*count(?![A-Za-z0-9_])|"
        r"Min(?:Ip(?:Son|Nodes)?)(?:Sample)?(?:Number|Volume)?|"
        r"Ip(?:Son|Nodes)?At least(?:Sample)?(?:Number|Volume)?"
    ),
    "min_weight_fraction_leaf": (
        r"(?<![A-Za-z0-9_])min[_\s-]*weight[_\s-]*fraction[_\s-]*leaf"
        r"(?![A-Za-z0-9_])|"
        r"Min(?:Ip(?:Son|Nodes)?)?Weights(?:Percentage|Percentage)|"
        r"Ip(?:Son|Nodes)?Min. weight(?:Percentage|Percentage)"
    ),
    "seed": r"(?:Random)?Feeds|(?<![A-Za-z0-9_])seed(?![A-Za-z0-9_])",
}

_AUTOMATIC_TREE_COLUMN_ROLE_LABELS = {
    "sample_weight_col": (
        r"sample[_\s-]*weight(?:[_\s-]*col)?|"
        r"Sample weights(?:Columns|Fields)?|Weights(?:Columns|Fields)"
    ),
    "loan_amount_col": (
        r"loan[_\s-]*amount(?:[_\s-]*col)?|"
        r"Amount released(?:Columns|Fields)?|Amount of loan(?:Columns|Fields)?"
    ),
    "overdue_amount_col": (r"overdue[_\s-]*amount(?:[_\s-]*col)?|Overdue amounts(?:Columns|Fields)?"),
}

def _automatic_tree_platform_control_clarification(
    utterance: str,
) -> StrategyRequestCompilation | None:
    if _AUTOMATIC_TREE_DATASET_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Auto-touch current taskdataset andworkspace,This request cannot be transposed."
            "Please switch first.workspace Or create new missions using target samples, and start building the results.",
            code="automatic_tree_build_dataset_context_required",
            fields=("dataset_id", "workspace_id"),
        )
    if _AUTOMATIC_TREE_TARGET_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Autotree destination bar bound by the current task context, not covered by this requesttarget_col."
            "Please confirm or switch the tab bar in the task before starting the build.",
            code="automatic_tree_build_target_context_required",
            fields=("target_col",),
        )
    if _AUTOMATIC_TREE_LABEL_POLICY_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "The empty tag processing strategy is bound by the Platform task contract and cannot be covered in this automatic tree request."
            "Please confirm the target tags' calibre.",
            code="automatic_tree_build_label_policy_not_overridable",
            fields=("drop_nan_labels",),
        )
    if _AUTOMATIC_TREE_BUDGET_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "The automatic tree implementation budget and its default values are governed by the Platform and cannot be covered by the present request;"
            "Asking for budget defaults will not createbuild.Use the current platform budget or adjust the governance configuration first.",
            code="automatic_tree_build_platform_budget_not_overridable",
            fields=(
                "budgets",
                "max_rows",
                "max_features",
                "max_cells",
                "max_nodes",
                "max_cutpoint",
            ),
        )
    return None

def _automatic_tree_leaf_has_positive_materialization_intent(utterance: str) -> bool:
    """Return true only for an explicit, non-negated pointer operation."""

    operation_text = _AUTOMATIC_TREE_LEAF_REASON_RE.sub(" ", utterance)
    for clause in _automatic_tree_follow_up_clauses(operation_text):
        for match in _AUTOMATIC_TREE_LEAF_MATERIALIZATION_ACTION_RE.finditer(clause):
            if re.search(r"(?:No, no.|Not|Nope.(?:Yes.)?)\s*$", clause[: match.start()]):
                continue
            if not _automatic_tree_follow_up_action_is_negated(
                clause,
                action_start=match.start(),
            ):
                return True
    return False

def _automatic_tree_leaf_explicit_reasons(utterance: str) -> tuple[str, ...]:
    reasons: list[str] = []
    for match in _AUTOMATIC_TREE_LEAF_REASON_RE.finditer(utterance):
        left = max(
            utterance.rfind(separator, 0, match.start())
            for separator in (",", ",", ";", ";", ".", "\n")
        )
        prefix = utterance[left + 1 : match.start()]
        if _AUTOMATIC_TREE_LEAF_REASON_NEGATION_RE.search(prefix) is not None:
            continue
        value = match.group("zh") or match.group("en") or ""
        canonical = " ".join(unicodedata.normalize("NFC", value).split())
        if canonical:
            reasons.append(canonical)
    return tuple(reasons)

def _automatic_tree_leaf_all_reason_values(utterance: str) -> tuple[str, ...]:
    return tuple(
        " ".join(
            unicodedata.normalize(
                "NFC",
                match.group("zh") or match.group("en") or "",
            ).split()
        )
        for match in _AUTOMATIC_TREE_LEAF_REASON_RE.finditer(utterance)
    )

def _automatic_tree_leaf_rationale_is_allowed(reason: str) -> bool:
    if _AUTOMATIC_TREE_LEAF_RATIONALE_START_RE.search(reason) is None:
        return False
    remaining = _AUTOMATIC_TREE_LEAF_RATIONALE_TOKEN_RE.sub(" ", reason)
    remaining = _AUTOMATIC_TREE_LEAF_RATIONALE_PUNCTUATION_RE.sub(" ", remaining)
    return not remaining.strip()

def _automatic_tree_leaf_unconsumed_request_text(utterance: str) -> str:
    """Remove the one allowed pointer operation and return every other demand.

    The grammar is intentionally narrow. New natural-language synonyms do not
    silently become executable multi-step operations; they require a safe
    clarification until the platform assigns them an explicit contract.
    """

    remaining = unicodedata.normalize("NFC", utterance)
    remaining = _AUTOMATIC_TREE_LEAF_NEGATED_REASON_CLAUSE_RE.sub(" ", remaining)
    remaining = _AUTOMATIC_TREE_LEAF_REASON_RE.sub(" ", remaining)
    remaining = _AUTOMATIC_TREE_LEAF_NEGATED_CLAUSE_RE.sub(" ", remaining)
    remaining = _AUTOMATIC_TREE_ASSET_ID_TOKEN_RE.sub(" ", remaining)
    remaining = _AUTOMATIC_TREE_LEAF_ID_TOKEN_RE.sub(" ", remaining)
    remaining = _AUTOMATIC_TREE_LEAF_ALLOWED_REQUEST_TOKEN_RE.sub(" ", remaining)
    remaining = _AUTOMATIC_TREE_LEAF_REQUEST_PUNCTUATION_RE.sub(" ", remaining)
    return " ".join(remaining.split())

def _ground_automatic_tree_leaf_materialization(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Fail closed unless one exact full-tree asset and leaf were named.

    This stage creates only an immutable pointer. It cannot rank/select on
    measured outcomes or smuggle a later Pool, action, lifecycle or writeback
    operation into the same confirmation.
    """

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    positive_operation_text = _AUTOMATIC_TREE_LEAF_NEGATED_CLAUSE_RE.sub(
        "",
        utterance,
    )

    if (
        _AUTOMATIC_TREE_LEAF_AMBIGUOUS_SELECTION_RE.search(positive_operation_text)
        is not None
    ):
        return _clarification(
            "Please copy a clear copy of the full tree result.leaf ID;No \"best\" or \"best\""
            "(Indicators such as the highest risk describe the choice of leaf nodes for you.",
            code="automatic_tree_leaf_selection_ambiguous",
            fields=("leaf_id",),
        )
    if not _automatic_tree_leaf_has_positive_materialization_intent(utterance):
        return _clarification(
            "The original words do not explicitly authorize a positive folicization; negative or only descriptionID Request"
            "Do not createpointer.If you need to continue, please re-identify the full asset to be physically converted.ID and"
            "Leaf NodeID.",
            code="automatic_tree_leaf_intent_negated",
            fields=("materialization_intent",),
        )
    reason_values = _automatic_tree_leaf_all_reason_values(utterance)
    explicit_reasons = _automatic_tree_leaf_explicit_reasons(utterance)
    if any(
        _AUTOMATIC_TREE_LEAF_REASON_REPLACEMENT_RE.search(reason) is not None
        for reason in reason_values
    ):
        return _clarification(
            "One request can only give one final answer.selection_reason;Reason content cannot be embedded again"
            "Reason field should read/Replace the instruction. Please only reconfirm after retaining the final reason.",
            code="automatic_tree_leaf_reason_not_grounded",
            fields=("selection_reason",),
        )
    if any(
        _AUTOMATIC_TREE_LEAF_REASON_EXTREME_RE.search(reason) is not None
        for reason in reason_values
    ):
        return _clarification(
            "The selection rationale should also not include a threshold, ranking or (best) by indicator/Worst \"Selecting leaf nodes for users"
            ". Please copy a clearly confirmed manual version of the full tree selectionleaf ID.",
            code="automatic_tree_leaf_selection_ambiguous",
            fields=("leaf_id", "selection_reason"),
        )
    if any(
        _AUTOMATIC_TREE_LEAF_REASON_FORBIDDEN_OPERATION_RE.search(reason) is not None
        for reason in reason_values
    ):
        return _clarification(
            "selection_reason Only this manual selection is recorded, and no subsequent entry into the pool is allowed."
            "Please untrace these operations as follow-up requests.",
            code="automatic_tree_leaf_single_step_required",
            fields=("selection_reason", "next_action"),
        )
    if any(
        not _automatic_tree_leaf_rationale_is_allowed(reason)
        or _AUTOMATIC_TREE_LEAF_RATIONALE_DECISION_SUBJECT_RE.search(reason) is not None
        for reason in explicit_reasons
    ):
        return _clarification(
            "selection_reason It must be manual./Operations/Risk/Compliance/The sample evaluation was based on short descriptions of the type,"
            "Please retain only this manual."
            "Select the basis, other actions are requested separately.",
            code="automatic_tree_leaf_reason_not_grounded",
            fields=("selection_reason",),
        )
    if any(
        pattern.search(positive_operation_text) is not None
        for pattern in (
            _AUTOMATIC_TREE_LEAF_POOL_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_ACTION_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_LIFECYCLE_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_WRITEBACK_CHAIN_RE,
        )
    ):
        return _clarification(
            "Creates only leaf node pointers in this cycle; joinStrategy Pool,Set up business actions, adopt,"
            "Deployment or transfer of leavesID Returning the data set must initiate separate follow-up requests.",
            code="automatic_tree_leaf_single_step_required",
            fields=("next_action",),
        )

    asset_ids = frozenset(
        match.group(0)
        for match in _AUTOMATIC_TREE_ASSET_ID_TOKEN_RE.finditer(utterance)
    )
    leaf_ids = frozenset(
        match.group(0) for match in _AUTOMATIC_TREE_LEAF_ID_TOKEN_RE.finditer(utterance)
    )
    ambiguous_fields: list[str] = []
    if len(asset_ids) != 1:
        ambiguous_fields.append("tree_asset_id")
    if len(leaf_ids) != 1:
        ambiguous_fields.append("leaf_id")
    if ambiguous_fields:
        return _clarification(
            "Please provide the full automatic tree verbatim in the same requestcandidate asset ID"
            "(candidate-asset- Back-up 32-bit lowercase hexadecimal) and one completeleaf ID"
            "(leaf- 20-bit lowercase hexadecimal; cannot be used for \"just now the tree\" or"
            "(This leaf is a pronoun.",
            code="automatic_tree_leaf_explicit_ids_required",
            fields=tuple(ambiguous_fields),
        )

    ungrounded: list[str] = []
    if asset_ids != {inputs["tree_asset_id"]}:
        ungrounded.append("tree_asset_id")
    if leaf_ids != {inputs["leaf_id"]}:
        ungrounded.append("leaf_id")
    if ungrounded:
        return _clarification(
            "Automatic tree assets or leaf nodes in the draft modelID This is not consistent with the user's original message. Please copy again"
            "Completetree asset ID andleaf ID;Platforms do not replace, complete or guessID.",
            code="automatic_tree_leaf_controls_not_grounded",
            fields=tuple(ungrounded),
        )

    selection_reason = inputs.get("selection_reason")
    reason_mismatch = bool(explicit_reasons or selection_reason is not None) and (
        len(explicit_reasons) != 1
        or not isinstance(selection_reason, str)
        or selection_reason != explicit_reasons[0]
    )
    if reason_mismatch:
        return _clarification(
            "selection_reason It must be used by the user to \"justify the selection\"/Rationale/Reason/(The report of the Secretary-General on the implementation of the United Nations Millennium Declaration)"
            "The only reason given in the obvious is entirely consistent; the model must also be used when the user does not give the reason"
            "Ignores the field. The platform does not recast, add or extrapolate the selection grounds.",
            code="automatic_tree_leaf_reason_not_grounded",
            fields=("selection_reason",),
        )

    if _automatic_tree_leaf_unconsumed_request_text(utterance):
        return _clarification(
            "This round only accepts a clear leaf node.pointer Physicalization; unattainable request"
            "Step to the interpretation of the contract. Please insert the rule/Strategy pool, business operations, adoption, commissioning or"
            "Write back the operation to be removed as a follow-up request.",
            code="automatic_tree_leaf_single_step_required",
            fields=("next_action",),
        )
    return result

def _ground_interactive_tree_split_search(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Ground one aggregate-only node search without authorizing a tree edit."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if re.search(
        r"(?:Don't.|Don't.|No need.|Discussion only|Later|In the future|Once.|Is it possible?|Can you...|Can I?|"
        r"\b(?:not|do\s+not|don't|later|future|historical|whether|can\s+you)\b)",
        utterance,
        re.IGNORECASE,
    ):
        return _clarification(
            "The original words must be a current, positive, one-point search warrant; negative, asking,"
            "History, assumptions or future descriptions will not initiate searches.",
            code="interactive_tree_split_search_intent_negated",
            fields=("search_intent",),
        )
    if not (
        re.search(
            r"(?:Search|Analysis|Through|Candidates|Rank|Test|search|rank|candidate|"
            r"evaluate)",
            utterance,
            re.IGNORECASE,
        )
        and re.search(
            r"(?:Tree|Nodes|Split|Characteristics|tree|node|split|feature)",
            utterance,
            re.IGNORECASE,
        )
    ):
        return _clarification(
            "Please explicitly request that a split candidate be searched or analysed for an interactive tree node.",
            code="interactive_tree_split_search_explicit_intent_required",
            fields=("search_intent",),
        )
    if re.search(
        r"(?:Direct Replace|Direct Modify|Autoselect(?:Best|Best|Champion.)|First place.|"
        r"Keep building the trees.|Autorenew|Add Policy Pool|Into the pool.|Apply|Accepted|Deployment|Production|Generate Report|"
        r"replace\s+and\s+apply|select\s+(?:the\s+)?winner|"
        r"auto[- ]?build|continue\s+(?:the\s+)?tree|add\s+to\s+pool|"
        r"adopt|deploy|generate\s+(?:a\s+)?report)",
        utterance,
        re.IGNORECASE,
    ):
        return _clarification(
            "This round produces only nodal splitting candidate evidence; selects candidate, modifys tree, automatically renews,"
            "The entry, application, reporting, adoption or deployment of the pool must be broken down into a subsequent explicit request.",
            code="interactive_tree_split_search_single_step_required",
            fields=("next_action",),
        )
    if re.search(
        r"(?:artifact|content_hash|evidence_hash|sample_design_ref|"
        r"dataset_id|workspace_revision|registry_metadata_hash|"
        r"Hash products|Sample binding|Dataset binding)",
        utterance,
        re.IGNORECASE,
    ):
        return _clarification(
            "artifact,hash,data sets,workspace,The sample and tree parent chain were restored by the platform."
            "This can't be covered by the natural language search.",
            code="interactive_tree_split_search_platform_controls_forbidden",
            fields=("platform_bindings",),
        )
    source_matches = tuple(
        _INTERACTIVE_TREE_SOURCE_ID_TOKEN_RE.finditer(utterance)
    )
    node_matches = tuple(_INTERACTIVE_TREE_NODE_ID_TOKEN_RE.finditer(utterance))
    source_ids = frozenset(match.group(0) for match in source_matches)
    node_ids = frozenset(match.group(0) for match in node_matches)
    if (
        len(source_matches) != 1
        or len(source_ids) != 1
        or len(node_matches) != 1
        or len(node_ids) != 1
    ):
        return _clarification(
            "Please provide a full text verbatim and only a full textautomatic-tree/revision ID And one."
            "Completenode ID;The platform does not use the word \"worst nodes\" or rankings like \"the tree\"."
            "Choose for you.",
            code="interactive_tree_split_search_explicit_ids_required",
            fields=("source_tree_id", "node_id"),
        )
    ungrounded: list[str] = []
    if source_ids != {inputs["source_tree_id"]}:
        ungrounded.append("source_tree_id")
    if node_ids != {inputs["node_id"]}:
        ungrounded.append("node_id")
    all_feature_intent = re.search(
        r"(?:All Features|All features|Full Character|Full Character Set|"
        r"all\s+(?:authenticated\s+)?features?|full\s+feature\s+universe)",
        utterance,
        re.IGNORECASE,
    )
    if inputs["mode"] == "all_features":
        if all_feature_intent is None or "features" in inputs:
            ungrounded.append("mode")
    else:
        features = inputs.get("features")
        if (
            all_feature_intent is not None
            or not isinstance(features, list)
            or any(feature not in utterance for feature in features)
        ):
            ungrounded.append("features")
    for field in (
        "max_thresholds_per_feature",
        "max_row_evaluations",
    ):
        value = inputs[field]
        if re.search(
            rf"(?<![0-9A-Fa-f.]){re.escape(str(value))}(?![0-9A-Fa-f.])",
            utterance,
        ) is None:
            ungrounded.append(field)
    if ungrounded:
        return _clarification(
            "The scope and budget of the search must be fully consistent with the user ' s original language: a clear full-fledged feature or word-to-word presentation"
            "Features subset, with a budget for each feature threshold and headline assessment; Platform does not add defaults"
            "Or guess.",
            code="interactive_tree_split_search_controls_not_grounded",
            fields=tuple(dict.fromkeys(ungrounded)),
        )
    return result

def _ground_interactive_tree_auto_continuation(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Ground one explicitly seeded and fully bounded subtree continuation."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if re.search(
        r"(?:Don't.|Don't.|No need.|Discussion only|Later|In the future|Is it possible?|Can you...|Can I?|"
        r"\b(?:not|do\s+not|don't|later|future|whether|can\s+you)\b)",
        utterance,
        re.IGNORECASE,
    ) or re.search(
        r"(?:Autorenew|Continue Auto|Keep building the trees.|To build a tree.|Keep growing.|"
        r"auto[- ]?continue|continue\s+(?:the\s+)?tree)",
        utterance,
        re.IGNORECASE,
    ) is None:
        return _clarification(
            "Please use the current, positive one-step command to explicitly require automatic renewal of the interactive tree.",
            code="interactive_tree_auto_continuation_intent_required",
            fields=("continuation_intent",),
        )
    if re.search(
        r"(?:Add Policy Pool|Into the pool.|Apply|Accepted|Deployment|Production|Generate Report|Report.|"
        r"Change it simultaneously|And adjust.|Search again.|add\s+to\s+pool|adopt|deploy|"
        r"generate\s+(?:a\s+)?report|and\s+apply)",
        utterance,
        re.IGNORECASE,
    ):
        return _clarification(
            "This round will allow only the continuation of the tree from the candidate that has been clearly chosen; entry into the pool, application, reporting,"
            "The adoption, deployment or other tree editor must be removed from the follow-up request.",
            code="interactive_tree_auto_continuation_single_step_required",
            fields=("next_action",),
        )
    if re.search(
        r"(?:artifact|content_hash|evidence_hash|sample_design_ref|"
        r"dataset_id|workspace_revision|registry_metadata_hash|"
        r"Hash products|Sample binding|Dataset binding)",
        utterance,
        re.IGNORECASE,
    ):
        return _clarification(
            "artifact,hash,data sets,workspace,The sample and the parent chain were restored by the platform."
            "This cannot be covered by a renewal request.",
            code="interactive_tree_auto_continuation_platform_controls_forbidden",
            fields=("platform_bindings",),
        )
    search_matches = tuple(
        _INTERACTIVE_TREE_SPLIT_SEARCH_ID_TOKEN_RE.finditer(utterance)
    )
    candidate_matches = tuple(
        _INTERACTIVE_TREE_SPLIT_CANDIDATE_ID_TOKEN_RE.finditer(utterance)
    )
    search_ids = frozenset(match.group(0) for match in search_matches)
    candidate_ids = frozenset(match.group(0) for match in candidate_matches)
    if (
        len(search_matches) != 1
        or len(search_ids) != 1
        or len(candidate_matches) != 1
        or len(candidate_ids) != 1
    ):
        return _clarification(
            "Please provide a full text verbatim and only a full textsplit search ID And a complete."
            " eligible candidate ID;Platforms will not be ranked, best or \"first\""
            "Picking a seed candidate for you.",
            code="interactive_tree_auto_continuation_explicit_ids_required",
            fields=("search_id", "candidate_id"),
        )
    ungrounded: list[str] = []
    if search_ids != {inputs["search_id"]}:
        ungrounded.append("search_id")
    if candidate_ids != {inputs["candidate_id"]}:
        ungrounded.append("candidate_id")
    for field in (
        "max_additional_depth",
        "min_gini_gain",
        "max_generated_nodes",
        "max_thresholds_per_feature",
        "max_row_evaluations",
    ):
        value = inputs[field]
        tokens = {str(value)}
        if isinstance(value, float) and value.is_integer():
            tokens.add(str(int(value)))
        if not any(
            re.search(
                rf"(?<![0-9A-Fa-f.]){re.escape(token)}"
                r"(?![0-9A-Fa-f.])",
                utterance,
            )
            for token in tokens
        ):
            ungrounded.append(field)
    for field in ("objective", "tie_break"):
        if inputs[field] not in utterance:
            ungrounded.append(field)
    reason = inputs.get("reason")
    if reason is not None and reason not in utterance:
        ungrounded.append("reason")
    if ungrounded:
        return _clarification(
            "The continuation must be given word for word.search/candidate ID,Add Depth, MinGini "
            "Gains, nodes ceiling, ceilings per feature threshold, headline assessment budget, and fixed"
            "objective andtie_break;Platforms do not fill defaults or candidate for a substitute.",
            code="interactive_tree_auto_continuation_controls_not_grounded",
            fields=tuple(dict.fromkeys(ungrounded)),
        )
    return result

def _ground_interactive_tree_revision(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Ground one current edit over exact tree, split and threshold controls."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    threshold_action = (
        _INTERACTIVE_TREE_THRESHOLD_ACTION_RE.search(utterance) is not None
    )
    feature_action = (
        _INTERACTIVE_TREE_FEATURE_ACTION_RE.search(utterance) is not None
    )
    prune_action = _INTERACTIVE_TREE_PRUNE_ACTION_RE.search(utterance) is not None
    if _INTERACTIVE_TREE_AMBIGUOUS_NODE_RE.search(utterance) is not None:
        return _clarification(
            "Please clearly copy a currently visible whole from the authentic tree pouncesplit node ID;The platform won't."
            "Select your node by the word (best) (risk highest) (unstable) or by the word.",
            code="interactive_tree_revision_node_selection_ambiguous",
            fields=("node_id",),
        )
    if _INTERACTIVE_TREE_THRESHOLD_AMBIGUOUS_RE.search(utterance) is not None:
        fields = (
            ("node_id", "threshold")
            if re.search(
                r"(?:All Nodes|All Nodes|Every node|all\s+nodes?|every\s+node)",
                utterance,
                re.IGNORECASE,
            )
            else ("threshold",)
        )
        return _clarification(
            "Threshold adjustment must be named as a current visiblesplit node and give a limited new threshold;"
            "The platform does not \" automatically optimize \" or \" all nodes \" by \" set a little \" \" , \" optimal threshold \""
            "Search, recommend or batch change for the user.",
            code="interactive_tree_revision_threshold_ambiguous",
            fields=fields,
        )
    if _INTERACTIVE_TREE_FEATURE_AMBIGUOUS_RE.search(utterance) is not None:
        return _clarification(
            "The split character has to be named as a current visible feature.split node,One authentication feature and one."
            "limited threshold; Platform does not \"automatically recommend\" or \"all features\" directly by \"best features\""
            "Modifys the tree for the user. Please run the node candidate analysis separately before choosing it precisely.",
            code="interactive_tree_revision_feature_ambiguous",
            fields=("feature", "threshold"),
        )
    if (
        _INTERACTIVE_TREE_NEGATED_OR_NONCURRENT_RE.search(utterance) is not None
        or not (prune_action or threshold_action or feature_action)
    ):
        return _clarification(
            "The original words must be a current, positive cut or threshold adjustment order; a query, negative, hypothetical, future or"
            "History description does not create interactive tree revisions.",
            code="interactive_tree_revision_intent_negated",
            fields=("edit_intent",),
        )
    if _INTERACTIVE_TREE_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Tree products,hash,frontier,condition,metrics,Datasets and sample binding by"
            "The platform is restored and cannot be covered by this natural language request.",
            code="interactive_tree_revision_platform_controls_forbidden",
            fields=("platform_bindings",),
        )
    if (
        prune_action
        and (threshold_action or feature_action)
        or any(
        pattern.search(utterance) is not None
        for pattern in (
            _AUTOMATIC_TREE_LEAF_POOL_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_ACTION_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_LIFECYCLE_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_WRITEBACK_CHAIN_RE,
        )
        )
        or re.search(
        r"(?:Generate Report|Report.|Apply the whole tree|Continue to split automatically.|Continue Auto|"
        r"Physicalization[^,,;;.\n]{0,24}(?:Front|frontier)|"
        r"(?<![A-Za-z0-9_])(?:generate\s+(?:a\s+)?report|apply\s+tree|"
        r"apply\s+(?:it|the\s+tree)\s+to\s+(?:the\s+)?dataset|"
        r"materiali[sz]e\s+(?:the\s+)?frontier|"
        r"auto[- ]?continue)(?![A-Za-z0-9_]))",
        utterance,
        re.IGNORECASE,
        )
    ):
        return _clarification(
            "This round is allowed only onceprune_subtree oradjust_split_threshold;"
            "Frontline materialization, pool entry, business operations, tree-to-tree applications, continued fragmentation, reporting, adoption,"
            "Deployment or write-back must be completed as a follow-up request.",
            code="interactive_tree_revision_single_step_required",
            fields=("next_action",),
        )

    source_matches = tuple(
        _INTERACTIVE_TREE_SOURCE_ID_TOKEN_RE.finditer(utterance)
    )
    node_matches = tuple(_INTERACTIVE_TREE_NODE_ID_TOKEN_RE.finditer(utterance))
    source_ids = frozenset(match.group(0) for match in source_matches)
    node_ids = frozenset(match.group(0) for match in node_matches)
    missing_or_ambiguous: list[str] = []
    if len(source_matches) != 1 or len(source_ids) != 1:
        missing_or_ambiguous.append("source_tree_id")
    if len(node_matches) != 1 or len(node_ids) != 1:
        missing_or_ambiguous.append("node_id")
    if missing_or_ambiguous:
        return _clarification(
            "Please provide a word for word in the same order and only a complete copyautomatic-tree asset "
            "orinteractive-tree revision ID,And a complete.split node ID;"
            "The words (that tree just now) and (that node) cannot be used.",
            code="interactive_tree_revision_explicit_ids_required",
            fields=tuple(missing_or_ambiguous),
        )
    threshold_values = _interactive_tree_threshold_values(utterance)
    expected_operation = (
        "replace_split_feature"
        if feature_action
        else (
            "adjust_split_threshold"
            if threshold_action
            else "prune_subtree"
        )
    )
    if expected_operation in {
        "adjust_split_threshold",
        "replace_split_feature",
    } and len(threshold_values) != 1:
        return _clarification(
            "The division adjustment must be clear in the same order and give only one limited new one.threshold "
            "values; the platform does not extrapolate from descriptions, indicators or historical trees.",
            code="interactive_tree_revision_explicit_threshold_required",
            fields=("threshold",),
        )
    feature_values = _interactive_tree_feature_values(utterance)
    if (
        expected_operation == "replace_split_feature"
        and len(feature_values) != 1
    ):
        return _clarification(
            "The split feature must be given word for word in the same command and only a new one.feature;"
            "The platform does not extrapolate from ranking or tree structure.",
            code="interactive_tree_revision_explicit_feature_required",
            fields=("feature",),
        )

    ungrounded: list[str] = []
    if source_ids != {inputs["source_tree_id"]}:
        ungrounded.append("source_tree_id")
    if node_ids != {inputs["node_id"]}:
        ungrounded.append("node_id")
    if inputs["operation"] != expected_operation:
        ungrounded.append("operation")
    if expected_operation in {
        "adjust_split_threshold",
        "replace_split_feature",
    }:
        supplied_threshold = inputs.get("threshold")
        if (
            isinstance(supplied_threshold, bool)
            or not isinstance(supplied_threshold, int | float)
            or float(supplied_threshold) != threshold_values[0]
        ):
            ungrounded.append("threshold")
    elif "threshold" in inputs:
        ungrounded.append("threshold")
    if expected_operation == "replace_split_feature":
        if inputs.get("feature") != feature_values[0]:
            ungrounded.append("feature")
    elif "feature" in inputs:
        ungrounded.append("feature")
    if ungrounded:
        return _clarification(
            "The source tree, node, operation or new threshold in the draft model is not consistent with the user ' s original language;"
            "The platform does not replace, complete, guess, optimize or re-elect the control values.",
            code="interactive_tree_revision_controls_not_grounded",
            fields=tuple(ungrounded),
        )

    explicit_reasons = _automatic_tree_leaf_explicit_reasons(utterance)
    supplied_reason = inputs.get("reason")
    if bool(explicit_reasons or supplied_reason is not None) and (
        len(explicit_reasons) != 1
        or not isinstance(supplied_reason, str)
        or supplied_reason != explicit_reasons[0]
    ):
        return _clarification(
            "reason Only users with 'justifications '/Reason/Annotations/reason)Only word for visible labels"
            "Copy; the model must be omitted when not provided and the platform will not be written.",
            code="interactive_tree_revision_reason_not_grounded",
            fields=("reason",),
        )
    return result

def _interactive_tree_threshold_values(utterance: str) -> tuple[float, ...]:
    values: list[float] = []
    for match in _INTERACTIVE_TREE_THRESHOLD_VALUE_RE.finditer(utterance):
        token = match.group("zh_value") or match.group("en_value")
        try:
            value = float(token)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(value):
            values.append(value)
    return tuple(values)

def _interactive_tree_feature_values(utterance: str) -> tuple[str, ...]:
    values: list[str] = []
    for match in _INTERACTIVE_TREE_FEATURE_VALUE_RE.finditer(utterance):
        value = match.group("zh_feature") or match.group("en_feature")
        if value:
            values.append(value)
    return tuple(values)

def utterance_targets_interactive_tree_frontier_group_materialization(
    utterance: str,
) -> bool:
    """Recognize an explicit interactive-tree frontier OR-group action."""

    return bool(
        _INTERACTIVE_TREE_FRONTIER_SUBJECT_RE.search(utterance)
        and _INTERACTIVE_TREE_FRONTIER_ACTION_RE.search(utterance)
        and (
            _INTERACTIVE_TREE_FRONTIER_GROUP_SEMANTICS_RE.search(utterance)
            or _INTERACTIVE_TREE_FRONTIER_GROUP_INTENT_RE.search(utterance)
        )
        and (
            _INTERACTIVE_TREE_REVISION_ID_TOKEN_RE.search(utterance)
            or re.search(
                r"(?:Interactive(?:Pattern)?Tree|Tree Revision|tree\s+revision).{0,80}"
                r"(?:Front|frontier)",
                utterance,
                re.IGNORECASE,
            )
        )
    )

def _ground_interactive_tree_frontier_group_materialization(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Require one explicit 2..50-member OR pointer over one exact revision."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if (
        _INTERACTIVE_TREE_FRONTIER_GROUP_AMBIGUOUS_SELECTION_RE.search(utterance)
        is not None
        or _AUTOMATIC_TREE_LEAF_REASON_EXTREME_RE.search(utterance) is not None
        or _INTERACTIVE_TREE_FRONTIER_GROUP_SEMANTICS_RE.search(utterance)
        is None
    ):
        return _clarification(
            "Please from the interactive treerevision Completefrontier Copy 2 to 50 in list"
            "Clearnode/leaf ID,And make clear that they pressOR grouping;platforms will not be all, best,"
            "The worst, risk or indicator ranking is your node.",
            code="interactive_tree_frontier_group_selection_ambiguous",
            fields=("source_node_ids", "or_semantics"),
        )
    if (
        _INTERACTIVE_TREE_FRONTIER_NEGATED_OR_NONCURRENT_RE.search(utterance)
        is not None
        or _INTERACTIVE_TREE_FRONTIER_ACTION_RE.search(utterance) is None
    ):
        return _clarification(
            "The words must be a current, positive, interactive tree front.OR Grouping of the physical command;"
            "Question, deny, assume, history or future description will not be createdgroup pointer.",
            code="interactive_tree_frontier_group_intent_negated",
            fields=("materialization_intent",),
        )
    if (
        _INTERACTIVE_TREE_FRONTIER_PLATFORM_CONTROL_RE.search(utterance)
        is not None
        or _INTERACTIVE_TREE_FRONTIER_GROUP_PLATFORM_CONTROL_RE.search(utterance)
        is not None
    ):
        return _clarification(
            "selection/group/revision artifact,hash,tree,fragment,condition,"
            "metrics,Datasets andworkspace Tie resumed from platform, not specified by natural language"
            "Or cover.",
            code="interactive_tree_frontier_group_platform_controls_forbidden",
            fields=("platform_bindings",),
        )
    if any(
        pattern.search(utterance) is not None
        for pattern in (
            _AUTOMATIC_TREE_LEAF_POOL_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_ACTION_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_LIFECYCLE_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_WRITEBACK_CHAIN_RE,
            _SCORECARD_SECOND_OPERATION_RE,
        )
    ):
        return _clarification(
            "Only one interactive tree is created this timefrontier OR group pointer;AddStrategy "
            "Pool,The establishment of operational actions, applications, adoption, deployment or write-back must initiate follow-up requests separately.",
            code="interactive_tree_frontier_group_single_step_required",
            fields=("next_action",),
        )

    revision_matches = tuple(
        _INTERACTIVE_TREE_REVISION_ID_TOKEN_RE.finditer(utterance)
    )
    node_matches = tuple(
        _INTERACTIVE_TREE_FRONTIER_NODE_ID_TOKEN_RE.finditer(utterance)
    )
    revision_ids = frozenset(match.group(0) for match in revision_matches)
    observed_node_ids = tuple(match.group(0) for match in node_matches)
    node_ids = frozenset(observed_node_ids)
    missing_or_ambiguous: list[str] = []
    if len(revision_matches) != 1 or len(revision_ids) != 1:
        missing_or_ambiguous.append("revision_id")
    if (
        not 2 <= len(node_matches) <= 50
        or len(node_ids) != len(node_matches)
    ):
        missing_or_ambiguous.append("source_node_ids")
    if missing_or_ambiguous:
        return _clarification(
            "Please provide a word for word in the same order and only a complete copyinteractive-tree "
            "revision ID,And 2 to 50 non-duplicate completesfrontier node/leaf "
            "ID;No pronouns, no cut-offs.ID Or repeat.ID.",
            code="interactive_tree_frontier_group_explicit_ids_required",
            fields=tuple(missing_or_ambiguous),
        )

    ungrounded: list[str] = []
    if revision_ids != {inputs["revision_id"]}:
        ungrounded.append("revision_id")
    supplied_node_ids = inputs.get("source_node_ids")
    if (
        not isinstance(supplied_node_ids, list)
        or len(supplied_node_ids) != len(node_ids)
        or frozenset(supplied_node_ids) != node_ids
    ):
        ungrounded.append("source_node_ids")
    if ungrounded:
        return _clarification(
            "in the draft modelrevision orfrontier node/leaf ID Gather & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & & &"
            "inconsistent; Platform does not replace, complete, guess, add or delete nodes. Members enter order"
            "No semantics, final order byrevision frontier Normative.",
            code="interactive_tree_frontier_group_controls_not_grounded",
            fields=tuple(ungrounded),
        )

    explicit_reasons = _automatic_tree_leaf_explicit_reasons(utterance)
    supplied_reason = inputs.get("selection_reason")
    if bool(explicit_reasons or supplied_reason is not None) and (
        len(explicit_reasons) != 1
        or not isinstance(supplied_reason, str)
        or supplied_reason != explicit_reasons[0]
    ):
        return _clarification(
            "selection_reason Only users with 'selection reasons '/Rationale/Reason/Annotations/reason)"
            "Only word-for-word transcription is possible when visible indications are given; models must be omitted when not provided.",
            code="interactive_tree_frontier_group_reason_not_grounded",
            fields=("selection_reason",),
        )
    return result

def utterance_targets_interactive_tree_frontier_materialization(
    utterance: str,
) -> bool:
    """Recognize only an explicit interactive-tree revision frontier action."""

    return bool(
        not utterance_targets_interactive_tree_frontier_group_materialization(
            utterance
        )
        and
        _INTERACTIVE_TREE_FRONTIER_SUBJECT_RE.search(utterance)
        and _INTERACTIVE_TREE_FRONTIER_ACTION_RE.search(utterance)
        and (
            _INTERACTIVE_TREE_REVISION_ID_TOKEN_RE.search(utterance)
            or re.search(
                r"(?:Interactive(?:Pattern)?Tree|Tree Revision|tree\s+revision).{0,80}"
                r"(?:Front|frontier)",
                utterance,
                re.IGNORECASE,
            )
        )
    )

def _ground_interactive_tree_frontier_materialization(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Require one current singleton pointer over an exact revision frontier."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if (
        _INTERACTIVE_TREE_FRONTIER_AMBIGUOUS_SELECTION_RE.search(utterance)
        is not None
        or _AUTOMATIC_TREE_LEAF_REASON_EXTREME_RE.search(utterance) is not None
    ):
        return _clarification(
            "Please from the interactive treerevision Completefrontier Copy a clear copy in the list.node/leaf "
            "ID;The platform will not be chosen for you by ranking as the best, worst, risk or indicator.",
            code="interactive_tree_frontier_selection_ambiguous",
            fields=("source_node_id",),
        )
    if (
        _INTERACTIVE_TREE_FRONTIER_NEGATED_OR_NONCURRENT_RE.search(utterance)
        is not None
        or _INTERACTIVE_TREE_FRONTIER_ACTION_RE.search(utterance) is None
    ):
        return _clarification(
            "The original words must be a current, positive interactive tree front-line materialization command; a question, a negative, a negative, a negative, a negative, and a positive, a positive, an interactive tree-fronting command."
            "Assuming that no history or future description will be createdselection pointer.",
            code="interactive_tree_frontier_intent_negated",
            fields=("materialization_intent",),
        )
    if _INTERACTIVE_TREE_FRONTIER_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "selection/revision artifact,hash,tree,fragment,condition,metrics,"
            "Datasets andworkspace The binding is restored by the platform and cannot be specified or covered by natural languages.",
            code="interactive_tree_frontier_platform_controls_forbidden",
            fields=("platform_bindings",),
        )
    if any(
        pattern.search(utterance) is not None
        for pattern in (
            _AUTOMATIC_TREE_LEAF_POOL_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_ACTION_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_LIFECYCLE_CHAIN_RE,
            _AUTOMATIC_TREE_LEAF_WRITEBACK_CHAIN_RE,
        )
    ):
        return _clarification(
            "Only one interactive tree is created this timefrontier pointer;AddStrategy Pool,"
            "The establishment of operational actions, adoption, deployment or write-back must initiate follow-up requests separately.",
            code="interactive_tree_frontier_single_step_required",
            fields=("next_action",),
        )

    revision_matches = tuple(
        _INTERACTIVE_TREE_REVISION_ID_TOKEN_RE.finditer(utterance)
    )
    node_matches = tuple(
        _INTERACTIVE_TREE_FRONTIER_NODE_ID_TOKEN_RE.finditer(utterance)
    )
    revision_ids = frozenset(match.group(0) for match in revision_matches)
    node_ids = frozenset(match.group(0) for match in node_matches)
    missing_or_ambiguous: list[str] = []
    if len(revision_matches) != 1 or len(revision_ids) != 1:
        missing_or_ambiguous.append("revision_id")
    if len(node_matches) != 1 or len(node_ids) != 1:
        missing_or_ambiguous.append("source_node_id")
    if missing_or_ambiguous:
        return _clarification(
            "Please provide a word for word in the same order and only a complete copyinteractive-tree "
            "revision ID,And a complete.frontier node/leaf ID;Unable to use"
            "(The last amendment to the article, the words (this frontier node), etc.",
            code="interactive_tree_frontier_explicit_ids_required",
            fields=tuple(missing_or_ambiguous),
        )

    ungrounded: list[str] = []
    if revision_ids != {inputs["revision_id"]}:
        ungrounded.append("revision_id")
    if node_ids != {inputs["source_node_id"]}:
        ungrounded.append("source_node_id")
    if ungrounded:
        return _clarification(
            "in the draft modelrevision orfrontier node/leaf ID (a) Is inconsistent with the original language of the user;"
            "The platform does not replace, complete, guess or re-elect nodes.",
            code="interactive_tree_frontier_controls_not_grounded",
            fields=tuple(ungrounded),
        )

    explicit_reasons = _automatic_tree_leaf_explicit_reasons(utterance)
    supplied_reason = inputs.get("selection_reason")
    if bool(explicit_reasons or supplied_reason is not None) and (
        len(explicit_reasons) != 1
        or not isinstance(supplied_reason, str)
        or supplied_reason != explicit_reasons[0]
    ):
        return _clarification(
            "selection_reason Only users with 'selection reasons '/Rationale/Reason/Annotations/reason)"
            "Only word-for-word transcription is possible when visible indications are given; models must be omitted when not provided.",
            code="interactive_tree_frontier_reason_not_grounded",
            fields=("selection_reason",),
        )
    return result

def _automatic_tree_apply_explicit_columns(
    utterance: str,
) -> tuple[dict[str, frozenset[str]], tuple[tuple[int, int], ...]]:
    values: dict[str, set[str]] = {
        "leaf_id_column": set(),
        "rule_id_column": set(),
    }
    spans: list[tuple[int, int]] = []
    for match in _AUTOMATIC_TREE_APPLY_OUTPUT_COLUMN_RE.finditer(utterance):
        label = match.group("label").casefold()
        field = (
            "leaf_id_column"
            if ("Ip" in label or "leaf" in label)
            else "rule_id_column"
        )
        values[field].add(match.group("column"))
        spans.append(match.span())
    for match in _AUTOMATIC_TREE_APPLY_NAMED_OUTPUT_COLUMN_RE.finditer(utterance):
        field = match.group("field").casefold()
        values[field].add(match.group("column"))
        spans.append(match.span())
    return (
        {field: frozenset(columns) for field, columns in values.items()},
        tuple(spans),
    )

def _automatic_tree_apply_has_unlabeled_output_column(
    utterance: str,
    labeled_spans: Sequence[tuple[int, int]],
) -> bool:
    for match in _AUTOMATIC_TREE_APPLY_GENERIC_OUTPUT_COLUMN_RE.finditer(utterance):
        if not any(
            start <= match.start() and match.end() <= end
            for start, end in labeled_spans
        ):
            return True
    return False

def _ground_automatic_tree_apply(
    utterance: str,
    result: StrategyRequestCompilation,
    *,
    whitelist: tuple[str, ...],
) -> StrategyRequestCompilation:
    """Bind one affirmative command to one exact tree and optional columns."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]

    if (
        _AUTOMATIC_TREE_APPLY_ACTION_RE.search(utterance) is None
        or _AUTOMATIC_TREE_APPLY_NOT_AUTHORIZED_RE.search(utterance) is not None
    ):
        return _clarification(
            "The original words are not authorized to be written in full, immediately and positively."
            "No hypothetical, historical or future description will create derivative datasets; please reissue separate data sets"
            "Execute the order.",
            code="automatic_tree_apply_intent_not_authorized",
            fields=("apply_intent",),
        )
    if _AUTOMATIC_TREE_APPLY_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Autotreeartifact/hash,Datasets andworkspace lineage It has to be from the platform."
            "The current task is re-read and bound and cannot be specified or covered by natural languages.",
            code="automatic_tree_apply_platform_binding_forbidden",
            fields=("platform_binding",),
        )
    if _AUTOMATIC_TREE_APPLY_FOLLOW_UP_RE.search(utterance) is not None:
        return _clarification(
            "This round only includes one full automatic tree certainty in a non-variable derivative data set; enters the pool,"
            "The selection, operational action, reporting, adoption and deployment of leaf nodes must be broken down into follow-up requests.",
            code="automatic_tree_apply_single_step_required",
            fields=("next_action",),
        )

    asset_mentions = tuple(
        match.group(0)
        for match in _AUTOMATIC_TREE_ASSET_ID_TOKEN_RE.finditer(utterance)
    )
    if len(asset_mentions) != 1:
        return _clarification(
            "Please write back the same order verbatim and only provide a full automatic treeasset ID"
            "(candidate-asset- Backstep 32-bit lowercase hexadecimal; not \"just now\""
            "The tree.",
            code="automatic_tree_apply_explicit_asset_required",
            fields=("tree_asset_id",),
        )
    if asset_mentions[0] != inputs["tree_asset_id"]:
        return _clarification(
            "Autotree in Model Draftasset ID Not in line with user ' s original language; platform will not replace,"
            "Complete or guess fulltree asset ID.",
            code="automatic_tree_apply_controls_not_grounded",
            fields=("tree_asset_id",),
        )

    explicit_columns, labeled_spans = _automatic_tree_apply_explicit_columns(
        utterance
    )
    if _automatic_tree_apply_has_unlabeled_output_column(
        utterance,
        labeled_spans,
    ) or any(len(values) > 1 for values in explicit_columns.values()):
        return _clarification(
            "Output columns must be clearly labelled as leaf nodes or rules columns, and each role must have a maximum of one final"
            "Listing; simply saying (output column) does not determine which result to cover.",
            code="automatic_tree_apply_output_column_ambiguous",
            fields=("leaf_id_column", "rule_id_column"),
        )

    ungrounded: list[str] = []
    for field, values in explicit_columns.items():
        explicit = next(iter(values)) if values else None
        if inputs.get(field) != explicit:
            ungrounded.append(field)
    if ungrounded:
        return _clarification(
            "Leaf nodes in the draft model/Rule output columns must be word for word for listings marked in a user-specific format"
            "Consistent; users must omit andTool Use the controlled default value.",
            code="automatic_tree_apply_controls_not_grounded",
            fields=tuple(ungrounded),
        )

    source_columns = {column.casefold() for column in whitelist}
    collisions = [
        field
        for field in ("leaf_id_column", "rule_id_column")
        if isinstance(inputs.get(field), str)
        and inputs[field].casefold() in source_columns
    ]
    if collisions:
        return _clarification(
            "Auto Tree Return column does not override existing fields of the current sample. Please be a leaf node column and a rule column"
            "Select a new listing.",
            code="automatic_tree_apply_output_column_conflict",
            fields=tuple(collisions),
        )
    return result

def _ground_automatic_tree_candidate_build(
    utterance: str,
    result: StrategyRequestCompilation,
    *,
    whitelist: tuple[str, ...],
) -> StrategyRequestCompilation:
    """Prove every tree-build control came from the user's original text."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if _AUTOMATIC_TREE_NEGATED_BUILD_RE.search(utterance) is not None:
        return _clarification(
            "The original words expressly negate automatic tree construction, so this time no creation or executionbuild."
            "If you need to build a tree, re-establish a clear positive construction request.",
            code="automatic_tree_build_intent_negated",
            fields=("build_intent",),
        )
    platform_control_clarification = _automatic_tree_platform_control_clarification(
        utterance
    )
    if platform_control_clarification is not None:
        return platform_control_clarification
    if _utterance_requests_automatic_tree_follow_up(utterance):
        return _clarification(
            "Auto-trees need to be confirmed in a auditable step by step: this time only stand-alone tree construction can be completed."
            "After construction is completed, look at the Platform Leaf evidence and quote the following specific requestleaf;"
            "The platform won't letLLM Automatically select the Best Leave or write directlyStrategy Pool.",
            code="automatic_tree_build_single_step_required",
            fields=("workflow_step", "leaf_id"),
        )

    column_mentions, ambiguous_columns = _automatic_tree_column_mention_resolution(
        utterance,
        whitelist,
    )
    if ambiguous_columns:
        return _clarification(
            "Auto-tree field names overlap or case-segregation in original language. Write in a separator-by-segregation"
            "Accurate listing:"
            + ",".join(ambiguous_columns)
            + ".The platform does not speculate in white list order.",
            code="automatic_tree_build_column_mention_ambiguous",
            fields=ambiguous_columns,
        )
    column_spans = tuple((start, end) for start, end, _ in column_mentions)
    missing_controls: list[str] = []
    missing_controls.extend(
        feature
        for feature in inputs["features"]
        if not _utterance_supports_automatic_tree_feature(
            utterance,
            feature,
            whitelist=whitelist,
        )
    )
    explicit_features = tuple(
        column
        for column in whitelist
        if _utterance_supports_automatic_tree_feature(
            utterance,
            column,
            whitelist=whitelist,
        )
    )
    missing_controls.extend(
        f"features includes {feature}"
        for feature in explicit_features
        if feature not in inputs["features"]
    )
    for field in (
        "sample_weight_col",
        "loan_amount_col",
        "overdue_amount_col",
    ):
        column = inputs.get(field)
        if isinstance(
            column, str
        ) and not _utterance_supports_automatic_tree_column_role(
            utterance,
            field=field,
            column=column,
            whitelist=whitelist,
        ):
            missing_controls.append(f"{field}={column}")
        explicit_columns = tuple(
            candidate
            for candidate in whitelist
            if _utterance_supports_automatic_tree_column_role(
                utterance,
                field=field,
                column=candidate,
                whitelist=whitelist,
            )
        )
        missing_controls.extend(
            f"{field}={candidate}"
            for candidate in explicit_columns
            if column != candidate
        )

    for feature, direction in inputs.get("directions", {}).items():
        if not _utterance_supports_automatic_tree_direction(
            utterance,
            feature=feature,
            direction=direction,
            column_spans=column_spans,
            whitelist=whitelist,
        ):
            missing_controls.append(f"{feature}={direction}")
    direction_features = tuple(dict.fromkeys((*explicit_features, *inputs["features"])))
    supplied_directions = inputs.get("directions", {})
    for feature in direction_features:
        explicit_directions = tuple(
            direction
            for direction in AUTOMATIC_TREE_DIRECTIONS
            if _utterance_supports_automatic_tree_direction(
                utterance,
                feature=feature,
                direction=direction,
                column_spans=column_spans,
                whitelist=whitelist,
            )
        )
        missing_controls.extend(
            f"directions.{feature}={direction}"
            for direction in explicit_directions
            if supplied_directions.get(feature) != direction
        )
    for field in (
        "max_depth",
        "min_leaf_count",
        "min_weight_fraction_leaf",
        "seed",
    ):
        if field in inputs and not _utterance_supports_automatic_tree_number(
            utterance,
            field=field,
            value=inputs[field],
            column_spans=column_spans,
        ):
            missing_controls.append(f"{field}={inputs[field]}")
        explicit_values = _automatic_tree_number_values(
            utterance,
            field=field,
            column_spans=column_spans,
        )
        supplied_value = inputs.get(field)
        missing_controls.extend(
            f"{field}={_automatic_tree_number_text(field, explicit_value)}"
            for explicit_value in explicit_values
            if supplied_value is None
            or not math.isclose(
                float(supplied_value),
                explicit_value,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        )

    if not missing_controls:
        return result
    unique_missing = tuple(dict.fromkeys(missing_controls))
    return _clarification(
        "Please specify in the original language all the characteristics of the automatic tree candidate and the weights actually to be covered,"
        "Amount column, direction or tree parameter; not possible to reconcile:"
        + ",".join(unique_missing)
        + ".The platform will not be usedLLM guess columns, parameters, default values, results or recommendations.",
        code="automatic_tree_build_controls_not_grounded",
        fields=unique_missing,
    )

def _automatic_tree_follow_up_clauses(utterance: str) -> tuple[str, ...]:
    """Split follow-up semantics so negation cannot hide a later positive action."""

    clauses = tuple(
        clause.strip()
        for clause in _AUTOMATIC_TREE_FOLLOW_UP_CLAUSE_BOUNDARY_RE.split(utterance)
        if clause.strip()
    )
    return clauses or (utterance,)

def _automatic_tree_follow_up_action_is_negated(
    clause: str,
    *,
    action_start: int,
) -> bool:
    """Accept negation only when it strictly scopes the leaf follow-up action."""

    negations = tuple(
        match
        for match in _AUTOMATIC_TREE_FOLLOW_UP_NEGATION_RE.finditer(
            clause,
            0,
            action_start,
        )
    )
    if not negations:
        return False
    closest = negations[-1]
    between = clause[closest.end() : action_start]
    return _AUTOMATIC_TREE_NEGATED_FOLLOW_UP_PREFIX_RE.fullmatch(between) is not None

def _automatic_tree_segment(
    utterance: str,
    *,
    start: int,
    end: int,
    separators: Sequence[str],
) -> tuple[str, int, int]:
    left = max(utterance.rfind(separator, 0, start) for separator in separators) + 1
    right_candidates = [
        position
        for separator in separators
        if (position := utterance.find(separator, end)) >= 0
    ]
    right = min(right_candidates, default=len(utterance))
    return utterance[left:right], left, right

def _automatic_tree_column_mentions(
    utterance: str,
    whitelist: Sequence[str],
) -> tuple[tuple[int, int, str], ...]:
    mentions, _ = _automatic_tree_column_mention_resolution(utterance, whitelist)
    return mentions

def _automatic_tree_column_mention_resolution(
    utterance: str,
    whitelist: Sequence[str],
) -> tuple[tuple[tuple[int, int, str], ...], tuple[str, ...]]:
    """Resolve contained names and fail closed on genuinely ambiguous overlaps."""

    candidates: list[tuple[int, int, str, int, bool]] = []
    for order, column in enumerate(whitelist):
        pattern = re.compile(
            rf"(?<![A-Za-z0-9_]){re.escape(column)}(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )
        candidates.extend(
            (
                match.start(),
                match.end(),
                column,
                order,
                match.group(0) == column,
            )
            for match in pattern.finditer(utterance)
        )

    components: list[list[tuple[int, int, str, int, bool]]] = []
    component_end = -1
    for candidate in sorted(candidates, key=lambda item: (item[0], item[1], item[3])):
        if not components or candidate[0] >= component_end:
            components.append([candidate])
            component_end = candidate[1]
            continue
        components[-1].append(candidate)
        component_end = max(component_end, candidate[1])

    accepted: list[tuple[int, int, str]] = []
    ambiguous: set[str] = set()
    for component in components:
        spans = {(start, end) for start, end, *_ in component}
        if len(spans) == 1:
            chosen_span = next(iter(spans))
        else:
            containers = [
                (start, end)
                for start, end in spans
                if all(
                    start <= other_start and other_end <= end
                    for other_start, other_end in spans
                )
            ]
            if len(containers) != 1:
                ambiguous.update(candidate[2] for candidate in component)
                continue
            chosen_span = containers[0]

        choices = [candidate for candidate in component if candidate[:2] == chosen_span]
        exact_choices = [candidate for candidate in choices if candidate[4]]
        if len(exact_choices) == 1:
            chosen = exact_choices[0]
        elif len(choices) == 1:
            chosen = choices[0]
        else:
            ambiguous.update(candidate[2] for candidate in choices)
            continue
        accepted.append((chosen[0], chosen[1], chosen[2]))

    ordered_ambiguities = tuple(column for column in whitelist if column in ambiguous)
    return (
        tuple(sorted(accepted, key=lambda item: (item[0], item[1], item[2]))),
        ordered_ambiguities,
    )

def _automatic_tree_span_is_negated(
    utterance: str,
    *,
    start: int,
    end: int,
) -> bool:
    segment, left, right = _automatic_tree_segment(
        utterance,
        start=start,
        end=end,
        separators=(",", ",", ",", ";", ";", ".", "\n"),
    )
    local_start = start - left
    local_end = end - left
    prefix = segment[max(0, local_start - 24) : local_start]
    suffix = segment[local_end : min(len(segment), local_end + 24)]
    negative_prefix = re.compile(
        r"(?:Don't.|No need.|No, I'm fine.|Do Not Use|No choice.|Don't.|Ban|Exclude|Remove|Get rid of it.|"
        r"No, it's not.|Not really.|Not|No, no.)\s*"
        r"(?:Again.|Use|Use|Selection|Choose|Organisation|Add|Settings|Set as|As)?\s*$",
        re.IGNORECASE,
    )
    negative_suffix = re.compile(
        r"^\s*(?:Don't.|No need.|No, I'm fine.|Do Not Use|No choice.|Inaction|Don't.|Ban|Exclude|"
        r"Remove|Get rid of it.|No, it's not.|Not really.|Not)",
        re.IGNORECASE,
    )
    return (
        negative_prefix.search(prefix) is not None
        or negative_suffix.search(suffix) is not None
        or right < end
    )

def _automatic_tree_feature_span_is_negated(
    utterance: str,
    *,
    start: int,
    end: int,
) -> bool:
    """Extend local negation across an explicitly excluded feature list."""

    if _automatic_tree_span_is_negated(utterance, start=start, end=end):
        return True
    segment, left, _ = _automatic_tree_segment(
        utterance,
        start=start,
        end=end,
        separators=(",", ",", ";", ";", ".", "\n"),
    )
    local_start = start - left
    prefix = segment[:local_start]
    scoped = re.search(
        r"(?P<cue>Don't.(?:Use|Selection|Choose)?|No need.(?:Use|Selection|Choose)?|"
        r"No, I'm fine.|Do Not Use|No choice.|Ban|Exclude|Remove|Get rid of it.|Remove|Except...|Divide)"
        r"\s*(?:Characteristics|Candidate Variables|Input Variables|From Variable)?\s*(?P<body>.*)$",
        prefix,
        re.IGNORECASE,
    )
    if scoped is None:
        return False
    cue = scoped.group("cue")
    following_sentence = utterance[
        end : utterance.find(".", end) if "." in utterance[end:] else len(utterance)
    ]
    if cue in {"Divide", "Except..."} and re.search(
        r"(?:And...|Yeah.|And...|And then...|And...)", following_sentence
    ):
        # Chinese (Except...A,It's still working.B) is additive rather than exclusionary.
        return False
    return (
        re.search(
            r"(?:But...(?:Yes.)?|And...(?:Yes.)?|For|Change|Turn around.)\s*"
            r"(?:Use|Selection|Select|Reservations|Add)?",
            scoped.group("body"),
            re.IGNORECASE,
        )
        is None
    )

def _automatic_tree_span_overlaps_columns(
    start: int,
    end: int,
    column_spans: Sequence[tuple[int, int]],
) -> bool:
    return any(
        start < column_end and column_start < end
        for column_start, column_end in column_spans
    )

def _automatic_tree_value_is_replaced(utterance: str, *, end: int) -> bool:
    return (
        re.match(
            r"\s*(?:For|Replace with|Adjust to|Replace with|Not|Not really.)",
            utterance[end:],
        )
        is not None
    )

def _automatic_tree_number_values(
    utterance: str,
    *,
    field: str,
    column_spans: Sequence[tuple[int, int]],
) -> tuple[float, ...]:
    label = _AUTOMATIC_TREE_NUMBER_LABELS[field]
    expression = re.compile(
        rf"(?:{label})\s*(?:[::=]|Yes|Set as|Set As|Set|Set As)?\s*"
        r"(?P<value>Percent\s*[0-9]+(?:\.[0-9]+)?|"
        r"[0-9]+(?:\.[0-9]+)?\s*%)?"
        r"(?P<number>[0-9]+(?:\.[0-9]+)?)?",
        re.IGNORECASE,
    )
    observed_values: list[float] = []
    for match in expression.finditer(utterance):
        if _automatic_tree_span_overlaps_columns(
            match.start(),
            match.end(),
            column_spans,
        ) or _automatic_tree_span_is_negated(
            utterance,
            start=match.start(),
            end=match.end(),
        ):
            continue
        token = match.group("value") or match.group("number")
        if token is None:
            continue
        replacement = re.match(
            r"\s*(?:For|Replace with|Adjust to|Replace with|Not|Not really.)\s*"
            r"(?P<value>Percent\s*[0-9]+(?:\.[0-9]+)?|"
            r"[0-9]+(?:\.[0-9]+)?\s*%|[0-9]+(?:\.[0-9]+)?)",
            utterance[match.end() :],
        )
        if replacement is not None:
            replacement_token = replacement.group("value")
            replacement_value = _automatic_tree_number_token_value(
                field,
                replacement_token,
            )
            if (
                replacement_value is not None
                and replacement_value not in observed_values
            ):
                observed_values.append(replacement_value)
            continue
        observed = _automatic_tree_number_token_value(field, token)
        if observed is None:
            continue
        if observed not in observed_values:
            observed_values.append(observed)
    return tuple(observed_values)

def _automatic_tree_number_token_value(field: str, token: str) -> float | None:
    if field == "min_weight_fraction_leaf":
        return _ratio_token_value(token)
    if "Percent" in token or "%" in token:
        return None
    return float(token)

def _automatic_tree_number_text(field: str, value: float) -> str:
    if field in {"max_depth", "min_leaf_count", "seed"}:
        return str(int(value))
    return format(value, ".15g")
