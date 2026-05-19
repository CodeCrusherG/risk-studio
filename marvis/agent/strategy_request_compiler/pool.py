"""pool request-compiler handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
import json
import re
from typing import Any
import unicodedata

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import StandardWorkflowRequestDraft
    from . import StrategyRequestCompilation
    from . import _AUTOMATIC_TREE_ASSET_ID_TOKEN_RE
    from . import _AUTOMATIC_TREE_LEAF_SELECTION_ID_TOKEN_RE
    from . import _CROSS_MATRIX_CELL_SELECTION_ID_TOKEN_RE
    from . import _INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ID_TOKEN_RE
    from . import _INTERACTIVE_TREE_FRONTIER_SELECTION_ID_TOKEN_RE
    from . import _SCORECARD_CUTOFF_SELECTION_ID_TOKEN_RE
    from . import _STRATEGY_POOL_WORKFLOWS
    from . import _clarification
    from . import _impact_cube_strategy_type_mentions
    from . import _ungrounded_pool_actions
    from . import _utterance_contains_token
    from . import _voting_strategy_type_mentions
    from . import utterance_targets_candidate_monthly_stability

_POOL_SOURCE_LIKE_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:candidate-asset|automatic-tree-leaf-selection|"
    r"interactive-tree-frontier-group-selection|"
    r"interactive-tree-frontier-selection|cross-matrix-cell-selection|"
    r"scorecard-cutoff-selection)-"
    r"[A-Za-z0-9_-]+(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)

_POOL_SOURCE_PREFIX_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:candidate-asset|automatic-tree-leaf-selection|"
    r"interactive-tree-frontier-group-selection|"
    r"interactive-tree-frontier-selection|cross-matrix-cell-selection|"
    r"scorecard-cutoff-selection)-",
    re.IGNORECASE,
)

_POOL_SOURCE_CONFUSABLE_TRANSLATION = str.maketrans(
    {
        "\u200b": None,
        "\u200c": None,
        "\u200d": None,
        "\u2060": None,
        "\ufeff": None,
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "―": "-",
        "﹘": "-",
        "﹣": "-",
        "－": "-",
    }
)

_POOL_MAX_CONTROL_VALUE_CHARS = 4096

_POOL_MAX_UTTERANCE_CHARS = 8192

_POOL_MAX_CONTROL_LABEL_MATCHES = 32

_POOL_UNPARSEABLE_VALUE = object()

_POOL_MUTATION_WORKFLOWS = _STRATEGY_POOL_WORKFLOWS - {"strategy_pool_compile"}

_POOL_ADD_PLACEMENT_MODES = frozenset(
    {"before_selected_members", "replace_selected_members"}
)

_POOL_ACTION_GROUNDING = {
    "approval": re.compile(
        r"(?:Pass.|Approval|Access)|(?<![A-Za-z0-9_])(?:approve|approval)"
        r"(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "reject": re.compile(
        r"Reject|(?<![A-Za-z0-9_])reject(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "review": re.compile(
        r"(?:Manual review|Manual clearance|Review|Audit)|"
        r"(?<![A-Za-z0-9_])review(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "limit": re.compile(
        r"(?:Amount|Letters)|(?<![A-Za-z0-9_])limit(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "pricing": re.compile(
        r"(?:Pricing|Interest rate)|(?<![A-Za-z0-9_])(?:pricing|price)"
        r"(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "segment": re.compile(
        r"(?:Group|Layer)|(?<![A-Za-z0-9_])segment(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
}

_POOL_STRATEGY_TYPE_GROUNDING = {
    "approval": re.compile(
        r"(?:Approval|Access|approval(?=.{0,12}(?:Policy pool|pool|strategy)))",
        re.IGNORECASE,
    ),
    "reject": re.compile(
        r"(?:Reject(?:Policy|Rule)?Ji.|Reject Policy|reject(?=.{0,12}(?:Policy pool|pool|strategy)))",
        re.IGNORECASE,
    ),
    "limit": re.compile(
        r"(?:Amount|Letters|limit(?=.{0,12}(?:Policy pool|pool|strategy)))",
        re.IGNORECASE,
    ),
    "pricing": re.compile(
        r"(?:Pricing|Interest rate|pricing(?=.{0,12}(?:Policy pool|pool|strategy)))",
        re.IGNORECASE,
    ),
    "segmentation": re.compile(
        r"(?:Group|Layer|segment(?:ation)?(?=.{0,12}(?:Policy pool|pool|strategy)))",
        re.IGNORECASE,
    ),
}

_POOL_STRATEGY_TYPE_VALUE_GROUNDING = {
    "approval": re.compile(r"(?<![A-Za-z0-9_])approval(?![A-Za-z0-9_])|(?:Approval|Access)"),
    "reject": re.compile(r"(?<![A-Za-z0-9_])reject(?![A-Za-z0-9_])|Reject"),
    "limit": re.compile(r"(?<![A-Za-z0-9_])limit(?![A-Za-z0-9_])|(?:Amount|Letters)"),
    "pricing": re.compile(r"(?<![A-Za-z0-9_])pricing(?![A-Za-z0-9_])|(?:Pricing|Interest rate)"),
    "segmentation": re.compile(
        r"(?<![A-Za-z0-9_])segmentation(?![A-Za-z0-9_])|(?:Group|Layer)"
    ),
}

_POOL_APPLY_TARGET_RE = re.compile(
    r"(?=.*(?:Policy pool|Rule pool|strategy(?:\s|-|_)*pool|\bpool\b))"
    r"(?=.*(?:Current Sample|Current Data|current\s+(?:sample|dataset)))"
    r"(?=.*(?:Apply|Write back|Back up.|Fill Back|Mark|"
    r"(?<![A-Za-z0-9_])(?:apply|write[-\s]*back|assign)(?![A-Za-z0-9_])))",
    re.IGNORECASE,
)

_POOL_APPLY_POSITIVE_INTENT_RE = re.compile(
    r"(?:Apply|Write back|Back up.|Fill Back|Mark)"
    r"[^;;..!??\n]{0,180}(?:Policy pool|Rule pool|Current Sample|Current Data)|"
    r"(?:Policy pool|Rule pool)[^;;..!??\n]{0,180}"
    r"(?:Apply|Write back|Back up.|Fill Back|Mark)|"
    r"(?<![A-Za-z0-9_])(?:apply|write[-\s]*back|assign)"
    r"[^;.!?\n]{0,180}(?:pool|current\s+(?:sample|dataset))"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_APPLY_NONCURRENT_RE = re.compile(
    r"[??]|(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Not yet.|Cancel|Stop|Ban|"
    r"Can you...|Can I?|Is it possible?|Is that okay?|Can you...|How's that?|What?|What?|Assumptions|Suppose...|If|"
    r"Later|The future.|In the future|Later.|Before|Before|Go on.|Last time.)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cancel|can\s+you|"
    r"could\s+you|how\s+to|what\s+if|later|previously|"
    r"in\s+the\s+future)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_APPLY_SECOND_OPERATION_RE = re.compile(
    r"(?:Accepted|Adopt|Deployment|Online.|Production|Entry into force|Activate|Switch|Export|Download|"
    r"Add|Add|Into the pool.|Delete|Remove|Changes|Modify Action|Reorder|Sort|Compile|"
    r"Modify Policy Pool|Change(?:One second.)?(?:Policy pool|Rule pool)|Generate Report|Form a report|Report.)|"
    r"(?<![A-Za-z0-9_])(?:adopt|deploy|promote|activate|switch|export|"
    r"download|add|insert|remove|delete|reorder|compile|modify|"
    r"generate\s+(?:a\s+)?report)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_APPLY_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:expected_pool_revision|"
    r"expected_pool_snapshot_hash|pool_(?:id|artifact_id)|"
    r"artifact_(?:id|hash)|dataset_(?:id|content_hash)|sample_design_ref|"
    r"requirements(?:_hash)?|strategy_spec|design_hash|action_counts|"
    r"activated|adopted|deployed)(?![A-Za-z0-9_])|"
    r"(?:Pool|Policy pool|Dataset|dataset|artifact|Work|Products)\s*(?:hash|Hash.|revision|Version)",
    re.IGNORECASE,
)

_POOL_MATERIALIZE_TARGET_RE = re.compile(
    r"(?=.*(?:Policy pool|Rule pool|strategy(?:\s|-|_)*pool|\bpool\b))"
    r"(?=.*(?:Physicalization|Solid|Create|Generate|"
    r"(?<![A-Za-z0-9_])(?:materialize|create)(?![A-Za-z0-9_])))"
    r"(?=.*(?:Draft Policy|Draft strategy|draft\s+strategy|strategy\s+draft))",
    re.IGNORECASE,
)

_POOL_MATERIALIZE_POSITIVE_INTENT_RE = re.compile(
    r"(?:Physicalization|Solid|Create|Generate)[^;;..!??\n]{0,180}"
    r"(?:Draft Policy|Draft strategy|draft\s+strategy|strategy\s+draft)|"
    r"(?<![A-Za-z0-9_])(?:materialize|create)[^;.!?\n]{0,180}"
    r"(?:draft\s+strategy|strategy\s+draft)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_MATERIALIZE_NONCURRENT_RE = _POOL_APPLY_NONCURRENT_RE

_POOL_MATERIALIZE_SECOND_OPERATION_RE = re.compile(
    r"(?:Accepted|Adopt|Deployment|Online.|Production|Entry into force|Retrospect|Test|Authentication|Apply|Write back|"
    r"Generate Report|Form a report|Report.|Monitor|Floating|Export|Download)|"
    r"(?<![A-Za-z0-9_])(?:adopt|deploy|promote|backtest|test|validate|"
    r"apply|write[-\s]*back|report|monitor|export|download)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_MATERIALIZE_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:expected_pool_revision|"
    r"expected_pool_snapshot_hash|expected_pool_artifact_id|"
    r"expected_pool_artifact_content_hash|expected_design_hash|"
    r"pool_(?:id|artifact_id)|artifact_(?:id|hash)|strategy_spec|"
    r"requirements?|metrics?|design_hash)(?![A-Za-z0-9_])|"
    r"(?:Pool|Policy pool|artifact|Work|Products|design|Design)\s*"
    r"(?:hash|Hash.|revision|Version)",
    re.IGNORECASE,
)

_POOL_MATERIALIZE_NEGATED_LIFECYCLE_DISCLAIMER_RE = re.compile(
    r"(?:,|,|;|;)\s*(?:"
    r"(?:Don't.|No, I'm fine.|No need.|No, I don't.|No way.|No, I won't.)\s*"
    r"(?:Accepted|Adopt|Deployment|Online.|Production)"
    r"(?:\s*(?:or|and|,|and|And...?)\s*(?:Accepted|Adopt|Deployment|Online.|Production))*"
    r"|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|without)\s+"
    r"(?:adopt|deploy|promote)"
    r"(?:\s*(?:or|and|,)\s*(?:adopt|deploy|promote))*"
    r")\s*[..!]?\s*$",
    re.IGNORECASE,
)

_POOL_APPLY_OUTPUT_PREFIX_LABEL_RE = re.compile(
    r"(?:(?:Output|Fields|Listing)\s*Prefix|output_prefix|output\s+prefix|prefix)"
    r"\s*(?:Yes|Yes.|Set as|Set As|=|:|:)?",
    re.IGNORECASE,
)

_POOL_APPLY_OUTPUT_PREFIX_RE = re.compile(
    _POOL_APPLY_OUTPUT_PREFIX_LABEL_RE.pattern
    + r"\s*(?P<prefix>[A-Za-z_][A-Za-z0-9_]{0,47})"
    r"(?![A-Za-z0-9_./-])",
    re.IGNORECASE,
)

_POOL_VALIDATION_TARGET_RE = re.compile(
    r"(?=.*(?:Policy pool|Rule pool|strategy(?:\s|-|_)*pool|\bpool\b))"
    r"(?:(?=.*(?:Independent sample|Playback Independently|Playback Validation|Independent validation|"
    r"independent(?:ly)?\s+(?:(?:sample\s+)?replay|validat(?:e|ed|ion))|"
    r"replay\s+validation))|"
    r"(?=.*(?:Authentication Set|Validation of samples|Validation Partition|Ex-time samples|Timeout Authentication|Partition outside time|"
    r"(?<![A-Za-z0-9_])(?:validation|oot)(?![A-Za-z0-9_])))"
    r"(?=.*(?:Authentication|Playback|(?<![A-Za-z0-9_])(?:validate|replay)"
    r"(?![A-Za-z0-9_]))))",
    re.IGNORECASE,
)

_POOL_VALIDATION_POSITIVE_INTENT_RE = re.compile(
    r"(?:Implementation|Run|Start|Conduct|Do it.|Authentication|Playback)"
    r"[^;;..!??\n]{0,160}(?:Independent sample|Playback Independently|Playback Validation|Policy pool|Rule pool)|"
    r"(?:Independent sample|Playback Independently|Playback Validation|Policy pool|Rule pool)"
    r"[^;;..!??\n]{0,160}(?:Implementation|Run|Start|Conduct|Authentication|Playback)|"
    r"(?<![A-Za-z0-9_])(?:run|perform|execute|validate|replay)"
    r"[^;.!?\n]{0,160}(?:independent|replay|validation|oot|pool)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_VALIDATION_NONCURRENT_RE = re.compile(
    r"[??]|(?:- You're not?|And?)\s*$|(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Not yet.|Cancel|Stop|Ban|"
    r"Can you...|Can I?|Is it possible?|Is that okay?|Can you...|Can I?|Should I?|Do you want it?|Do you need it or not?|"
    r"How's that?|What?|What?|Assumptions|Suppose...|If|"
    r"Later|The future.|In the future|Later.|Later.|Turn around.|Wait a minute.|Later.|Just a minute.|"
    r"Tomorrow.|Tomorrow morning.|Tonight.|The day after tomorrow.|Next time.|Next week.|Next month|Next month|End of the month|And then...|"
    r"Before|Before|Go on.|Last time.|Previous|Previous Version|History|Once.|Tsang.|Yes.|"
    r"Completed)|"
    r"(?:Implementation|Run|Start|Conduct|Do it.|Authentication|Playback|Completed)(?:Yes.|Pass.)|"
    r"(?:Wait.|- Wait.|Sample|Data|Materials|Audit|Approval|Evaluation|Confirm.)"
    r"[^;;..!??\n]{0,24}(?:Back|After)|"
    r"Already[^;;..!??\n]{0,80}(?:Completed|Yes.|Checked|I'm sorry.)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cancel|can\s+(?:you|we)|"
    r"could\s+(?:you|we)|would\s+you|should\s+(?:we|i)|"
    r"do\s+we\s+need(?:\s+to)?|"
    r"is\s+it\s+possible|"
    r"tell\s+me\s+whether|how\s+to|what\s+if|later|previously|"
    r"in\s+the\s+future|tomorrow|next\s+time)(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:was|has\s+been)\b"
    r"[^;.!?\n]{0,80}\b(?:validated|replayed|completed)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_VALIDATION_SECOND_OPERATION_RE = re.compile(
    r"(?:Add|Add|Into the pool.|Delete|Remove|Changes|Modify Action|Reorder|Sort|Compile|"
    r"Modify Policy Pool|Apply|Write back|Back up.|Fill Back|Mark|Generate Report|Form a report|Report.|"
    r"Accepted|Adopt|Promotion|Raise to|Deployment|Online.|Production|Entry into force|Activate|Switch)|"
    r"(?<![A-Za-z0-9_])(?:add|insert|remove|delete|reorder|compile|"
    r"apply|write[-\s]*back|report|adopt|promote|deploy|activate|switch)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_VALIDATION_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:pool_ref|sample_design_ref|population|"
    r"comparison_mode|expected_pool_revision|expected_pool_snapshot_hash|"
    r"pool_(?:id|artifact_id)|artifact_(?:id|hash)|"
    r"dataset_(?:id|content_hash)|workspace_revision|target_col|"
    r"requirements(?:_hash)?|metrics?|validation_status)"
    r"(?![A-Za-z0-9_])|"
    r"(?:Pool|Policy pool|Dataset|dataset|artifact|Work|Products)"
    r"\s*(?:hash|Hash.|revision|Version)",
    re.IGNORECASE,
)

_POOL_VALIDATION_EVIDENCE_SCOPE_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:psi|stability|drift)(?![A-Za-z0-9_])|"
    r"(?:Stability|Floating)",
    re.IGNORECASE,
)

_POOL_VALIDATION_PARTITION_GROUNDING = {
    "validation": re.compile(
        r"(?:Authentication Set|Validation of samples|Validation Partition)|"
        r"(?:(?<![A-Za-z0-9_])(?:on|in)\s+validation"
        r"(?![A-Za-z0-9_])|"
        r"(?<![A-Za-z0-9_])validation"
        r"(?=\s*(?:Go, go, go!|Medium|Lee.|partition|sample|set|Independent sample|Playback Independently)))",
        re.IGNORECASE,
    ),
    "oot": re.compile(
        r"(?:Ex-time samples|Timeout Authentication|Partition outside time)|"
        r"(?<![A-Za-z0-9_])oot(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "development": re.compile(
        r"(?:Development set|Development of samples|Development of the partitions)|"
        r"(?<![A-Za-z0-9_])development(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
}

_POOL_STABILITY_TARGET_RE = re.compile(
    r"(?=.*(?:Policy pool|Rule pool|strategy(?:\s|-|_)*pool|\bpool\b))"
    r"(?=.*(?:Cross(?:Division|Sample)(?:Distribution)?(?:Stability|Floating)?|"
    r"Distribution(?:Stability|Floating)|Stability|Floating|"
    r"(?<![A-Za-z0-9_])psi(?![A-Za-z0-9_])|"
    r"cross[-\s]*partition\s+stability))",
    re.IGNORECASE,
)

_POOL_STABILITY_POSITIVE_INTENT_RE = re.compile(
    r"(?:Measurement|Measurement|Analysis|Calculate|Evaluation|Inspection)"
    r"[^;;..!??\n]{0,160}(?:Stability|Floating|PSI|Policy pool|Rule pool)|"
    r"(?:Policy pool|Rule pool)[^;;..!??\n]{0,160}"
    r"(?:Measurement|Measurement|Analysis|Calculate|Evaluation|Inspection)|"
    r"(?<![A-Za-z0-9_])(?:measure|calculate|analy[sz]e|assess|evaluate|check)"
    r"[^;.!?\n]{0,160}(?:stability|drift|psi|pool)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_STABILITY_NONCURRENT_RE = re.compile(
    r"[??]|(?:- You're not?|And?)\s*$|(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Not yet.|Cancel|Stop|Ban|"
    r"Can you...|Can I?|Is it possible?|Is that okay?|Can you...|Can I?|Should I?|Do you want it?|Do you need it or not?|"
    r"How's that?|What?|What?|Assumptions|Suppose...|If|Later|The future.|In the future|Later.|"
    r"Tomorrow.|Next time.|Before|Before|Go on.|Last time.|Previous|History|Once.|Yesterday.)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cancel|can\s+(?:you|we)|"
    r"could\s+(?:you|we)|would\s+you|should\s+(?:we|i)|how\s+to|"
    r"what\s+if|later|previously|historically|yesterday|tomorrow|"
    r"in\s+the\s+future)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_STABILITY_SECOND_OPERATION_RE = re.compile(
    r"(?:Add|Add|Into the pool.|Delete|Remove|Changes|Modify Action|Reorder|Sort|Compile|"
    r"Apply|Write back|Back up.|Fill Back|Mark|Generate Report|Form a report|Report.|"
    r"Create Policy|Accepted|Adopt|Promotion|Raise to|Deployment|Online.|Production|Entry into force|Activate|Switch)|"
    r"(?<![A-Za-z0-9_])(?:add|insert|remove|delete|reorder|compile|"
    r"apply|write[-\s]*back|report|create\s+strategy|adopt|promote|"
    r"deploy|activate|switch)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_STABILITY_PLATFORM_CONTROL_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:impact_cube_ref|pool_stability_ref|pool_ref|"
    r"sample_design_ref|artifact_id|content_hash|expected_[a-z0-9_]+|"
    r"pool_(?:id|revision|snapshot_hash)|dataset_(?:id|content_hash)|"
    r"workspace_revision|target_col|metrics?|psi_threshold|thresholds?)"
    r"(?![A-Za-z0-9_])|"
    r"(?:Pool|Policy pool|Dataset|dataset|artifact|Work|Products)"
    r"\s*(?:hash|Hash.|revision|Version)|"
    r"(?:PSI|Stability|Floating)\s*(?:Threshold|threshold)\s*(?:=|:|:)?\s*[-+]?\d",
    re.IGNORECASE,
)

_POOL_IMPACT_TARGET_RE = re.compile(
    r"(?=.*(?:Policy pool|Rule pool|strategy(?:\s|-|_)*pool|\bpool\b))"
    r"(?=.*(?:Impact|Effects|Falls|Month by Month|Pass rate|Bad debt rate|Risk rate|Measurement|Evaluation|Retrospect|"
    r"impact|effect|waterfall|monthly|approval\s+rate|bad\s+rate|risk\s+rate|"
    r"measure|assess|evaluat|backtest))",
    re.IGNORECASE,
)

_POOL_IMPACT_POSITIVE_INTENT_RE = re.compile(
    r"(?:Measurement|Evaluation|Analysis|Retrospect|Calculate|View|Take a look.|Look at this.)"
    r"[^;;..!??\n]{0,160}?(?:Impact|Effects|Falls|Month by Month|Policy pool|Rule pool)|"
    r"(?:Policy pool|Rule pool)[^;;..!??\n]{0,160}?"
    r"(?:Measurement|Evaluation|Analysis|Retrospect|Calculate|View|Take a look.|Look at this.)|"
    r"(?<![A-Za-z0-9_])(?:measure|assess|evaluate|analy[sz]e|calculate|backtest)"
    r"[^;.!?\n]{0,160}?(?:impact|effect|waterfall|monthly|pool)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_IMPACT_NEGATED_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Not yet.|Cancel|Stop|Ban)"
    r"[^;;..!??\n]{0,64}(?:Measurement|Evaluation|Analysis|Retrospect|Impact|Effects)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cancel|stop)"
    r"[^;.!?\n]{0,64}(?:measure|assess|evaluate|analy[sz]e|calculate|backtest)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_IMPACT_NONCOMMAND_RE = re.compile(
    r"[??]|(?:Can you...|Can I?|Is it possible?|Is that okay?|Can you...|How's that?|What?|What?|Assumptions|Suppose...|"
    r"If|If|Presentation|Demonstration|Example|Annotations|Explanation|Introduction|Yesterday.|Before|Before|Go on.|Last time.|"
    r"Once.|History|The future.|Later|Later.|Tomorrow.|Next week.|Next month)"
    r"[^;;.\n]{0,180}(?:Policy pool|Rule pool|Impact|Effects|Measurement|Evaluation|Retrospect)|"
    r"(?<![A-Za-z0-9_])(?:can\s+you|could\s+you|would\s+you|what\s+if|"
    r"how\s+to|example|demo|previously|yesterday|historically|later|tomorrow)"
    r"[^;.!?\n]{0,180}(?:pool|impact|effect|measure|assess|backtest)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_IMPACT_REPORT_ONLY_RE = re.compile(
    r"(?:Only|Only)\s*(?:Generate|Out|Write|Collapse|Summary)?\s*(?:Report|Document|Reporting|Summary)|"
    r"(?:Generate|Out|Write|Collapse|Summary|Production|Export|Download)"
    r"[^;;..!??\n]{0,32}(?:Report|Document|Reporting|Summary)|"
    r"(?:Report|Document|Reporting|Summary)"
    r"[^;;..!??\n]{0,24}(?:Generate|Production|Export|Download)|"
    r"(?:Report|Document|Reporting|Summary)\s*(?:Yeah.|That's all.|only)|"
    r"(?<![A-Za-z0-9_])(?:generate|create|write|export|download)"
    r"[^;.!?\n]{0,32}(?:report|document|summary)|"
    r"(?<![A-Za-z0-9_])(?:report|document|summary)\s+only"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_IMPACT_SECOND_OPERATION_RE = re.compile(
    r"(?:Add|Add|Into the pool.|Delete|Remove|Changes|Modify Action|Reorder|Sort|Compile|Preview|"
    r"Accepted|Adopt|Deployment|Online.|Production|Entry into force|Write back|Back up.|Create Policy|Generate Policy|"
    r"Vintage|Migration rate|Migration Matrix|Profit|Proceeds|Export|Download)|"
    r"(?<![A-Za-z0-9_])(?:add|insert|remove|delete|reorder|compile|preview|"
    r"adopt|deploy|promote|activate|write[-\s]*back|create\s+strategy|"
    r"vintage|roll[-\s]*rate|profit|export|download)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_IMPACT_BASELINE_MODE_RE = re.compile(
    r"(?:Relative|Compare(?:on)?|Compare(?:on)?|Comparison|Comparison| versus |\bvs\.?\b)"
    r"[^;;..!??\n]{0,80}(?:Baseline|baseline|strategy[-_A-Za-z0-9]+)|"
    r"(?:Baseline|baseline)[^;;..!??\n]{0,80}(?:Comparison|Comparison|Impact|Effects|vs)",
    re.IGNORECASE,
)

_POOL_IMPACT_ABSOLUTE_MODE_RE = re.compile(
    r"(?:Absolutely.(?:Effects|Impact|caliber)?|No, no.(?:Do it.|Yes.|Use)?(?:Baseline)?(?:Comparison|Comparison)|"
    r"No need.(?:Baseline)?(?:Comparison|Comparison))|"
    r"(?<![A-Za-z0-9_])absolute(?![A-Za-z0-9_])|"
    r"(?<![A-Za-z0-9_])(?:without|no)\s+baseline(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_IMPACT_STRATEGY_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_])strategy-[A-Za-z0-9][A-Za-z0-9_-]*"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_IMPACT_DROP_NAN_TRUE_RE = re.compile(
    r"(?:Clear|Confirm.|Allow|Agreed.)?\s*(?:Drop|Exclude|Remove|Delete)"
    r"[^;;..!??\n]{0,24}(?:NaN|nan|Empty Tab|Missing tab|Invalid Tab)|"
    r"drop[_\s-]*nan[_\s-]*labels?\s*(?:=|:)?\s*true|"
    r"(?<![A-Za-z0-9_])(?:drop|exclude)[^;.!?\n]{0,24}"
    r"(?:nan|missing)\s+labels?(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_IMPACT_DROP_NAN_NEGATED_RE = re.compile(
    r"(?:Don't.|No, no.|Ban|Reject|I disagree.|Unauthorized|No, I can't.)\s*"
    r"(?:Allow|Confirm.|Agreed.)?\s*(?:Drop|Exclude|Remove|Delete)"
    r"[^;;..!??\n]{0,24}(?:NaN|nan|Empty Tab|Missing tab|Invalid Tab)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never)\s+(?:drop|exclude)"
    r"[^;.!?\n]{0,24}(?:nan|missing)\s+labels?(?![A-Za-z0-9_])|"
    r"drop[_\s-]*nan[_\s-]*labels?\s*(?:=|:)?\s*false",
    re.IGNORECASE,
)

_POOL_PARTIAL_REORDER_RE = re.compile(
    r"(?:Fire!|Move|Move!|Line|Tranquility)(?:Present.|to|Yes.)?(?:Front|Back|Top|End|Finally.|"
    r"I'm sorry.[One, two, three, four, five, six, seven, eight, nine, nine hundred.-9]+(?:bit|individual|Article))|"
    r"(?:Move Up|Move Down)[One, two, three, four, five, six, seven, eight, nine, nine hundred.-9]+(?:bit|individual|Article)|"
    r"Top|Early|Line(?:Yes.)?(?:Top|First|End|Finally.)|First priority.|"
    r"(?:Switch|Swap)[^;;.\n]{0,200}(?:Order|Location)|"
    r"move\s+.*\s+(?:first|last|(?:to\s+)?(?:position\s+\d+|"
    r"(?:second|third|fourth)\s+(?:place|position)))|"
    r"swap\s+.*(?:order|position)",
    re.IGNORECASE,
)

_POOL_HEURISTIC_REORDER_RE = re.compile(
    r"(?:Press.{0,12}(?:Effects|Bad rate|lift|I'd better.|Best|Risk).{0,8}(?:Sort|Reorder)|"
    r"(?:Automatic|Smart).{0,8}(?:Sort|Reorder)|sort.{0,12}(?:best|effect|risk|lift))",
    re.IGNORECASE,
)

_POOL_ADD_INTENT_RE = re.compile(
    r"(?:Add|Add to?|Writing|Put it in.|Add|Put it in.|Inclusion|♪ Write to|Add to)"
    r"[^,,;;.\n]{0,160}(?:Policy pool|Rule pool|(?<![A-Za-z0-9_])"
    r"(?:strategy\s+)?pool(?![A-Za-z0-9_]))|"
    r"(?:Into the pool.)(?!Rationale|Reason|Annotations)|"
    r"(?<![A-Za-z0-9_])(?:add|append|insert|write)\b"
    r"[^,;.!?\n]{0,160}\bto\s+(?:the\s+)?"
    r"(?:(?:approval|reject|limit|pricing|segmentation)\s+)?"
    r"(?:(?:strategy|rule)\s+)?pool\b|"
    r"(?<![A-Za-z0-9_])put\b[^,;.!?\n]{0,160}\binto\s+(?:the\s+)?"
    r"(?:(?:approval|reject|limit|pricing|segmentation)\s+)?"
    r"(?:(?:strategy|rule)\s+)?pool\b",
    re.IGNORECASE,
)

_POOL_ADD_HYPOTHETICAL_RE = re.compile(
    r"[??]|"
    r"(?:Assumptions|Suppose...|If|If)\s*[^;;.\n]{0,180}(?:Add|Add|Put it in.|Inclusion|Into the pool.)|"
    r"(?:How's that?|What?|What?|Please describe|Explain.|Show me.|Show me.|Test it.|Example)"
    r"[^;;.\n]{0,180}(?:Add|Add|Put it in.|Inclusion|Into the pool.)|"
    r"(?:Document|Annotations|Example:|Example|Original|Materials|Report)[^;;.\n]{0,80}"
    r"(?:It says,|Reference|Say it.|Organisation|Presentation)[^;;.\n]{0,180}"
    r"(?:Add|Add|Put it in.|Inclusion|Into the pool.)|"
    r"(?:Document|Annotations|Example:|Example|Original|Materials|Report)[^;;.\n]{0,120}"
    r"(?:Default Action|Hit action.|default\s+action|hit\s+action)|"
    r"[(\"'(][^)\"');;.\n]{0,240}(?:Add|Add|Put it in.|Inclusion|Into the pool.)"
    r"[^)\"');;.\n]{0,240}[)\"')]|"
    r"[(\"'(][^)\"');;.\n]{0,240}"
    r"(?:Default Action|Hit action.|default\s+action|hit\s+action)"
    r"[^)\"');;.\n]{0,240}[)\"')]|"
    r"(?:Don't.|No, I'm fine.|Don't.|Please don't.|Exclude|Ignore)[^;;.\n]{0,48}"
    r"(?:(?:This.|The)\s*(?:source|ID|id|Source)|Source)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never)\s+use\s+"
    r"(?:this\s+|that\s+)?(?:source|id)(?![A-Za-z0-9_])|"
    r"(?:Only|Only)\s*(?:Tell|Annotations|Explanation|Presentation|Description)[^;;.\n]{0,180}"
    r"(?:Add|Into the pool.|Policy pool)|"
    r"(?:Evaluation|Analysis|Roger that.|Look at that.|View|Explanation|Simulation(?:One second.)?)[^;;.\n]{0,180}"
    r"(?:Add|Into the pool.|Policy pool)|"
    r"(?:Can you...|Can I?|Is it possible?|Is that okay?|Can you...)[^;;.\n]{0,180}"
    r"(?:Add|Into the pool.|Policy pool)|"
    r"(?:Yesterday.|Yesterday|Before|Before|Go on.|Last time.|Previous|Earlier|Once.|Already)"
    r"[^;;.\n]{0,180}(?:Add|Add|Put it in.|Inclusion|Into the pool.)|"
    r"(?:Rewrite|Redo|Dust|Translation|Repeat)[^;;.\n]{0,120}"
    r"(?:This.|That's the sentence.|Next sentence|Below|Text|Documentation|Contents)|"
    r"(?:Rewrite|Redo|Dust|Translation|Repeat)(?:Okay.|Done.|Yes|One second.)|"
    r"(?:Cannot|Not|I can't.)[^;;.\n]{0,80}(?:Add|Add|Put it in.|Inclusion|Into the pool.)|"
    r"(?:Add|Add|Put it in.|Inclusion|Into the pool.)(?:No, I'm fine.|Failed|I'm not going in there.|I'm not going.)|"
    r"(?:The future.|In the future|Later|After|Later.|Later.|Turn around.|Tomorrow.|Tomorrow morning.|Tonight.|The day after tomorrow.|"
    r"Next week.|Next month|Next month|End of the month|And then...|[One, two, two, three, four, five, six, seven, eight, nine, zero.-9]+Queen of Heaven.)"
    r"[^;;.\n]{0,180}"
    r"(?:Add|Into the pool.|Policy pool)|"
    r"(?:Wait.|- Wait.)?(?:Approval|Audit|Evaluation|Approval|Confirm.)"
    r"(?:Pass.|Completed|Agreed.|Approval)?(?:Back|After|Just...|Again.|That's right.)"
    r"[^;;.\n]{0,180}(?:Add|Add|Put it in.|Inclusion|Into the pool.)|"
    r"(?:Wait.|- Wait.)[^;;.\n]{0,100}(?:Again.|That's right.)[^;;.\n]{0,100}"
    r"(?:Add|Into the pool.|Policy pool)|"
    r"(?:Add|Add|Put it in.|Inclusion|Into the pool.)[^;;.\n]{0,100}"
    r"(?:Not permitted|Ban|No way.|Unenforceable)|"
    r"(?:What happens?|What happens?|What will happen?)|"
    r"(?<![A-Za-z0-9_])(?:what\s+if|suppose|assuming|hypothetically|"
    r"can\s+you|could\s+you|would\s+you|is\s+it\s+possible|"
    r"evaluate|analy[sz]e|explain|how\s+to|demonstrate|demo|test|"
    r"show\s+me\s+what\s+happens|documentation\s+says|example|"
    r"yesterday|previously|earlier|last\s+time|failed\s+to|"
    r"unable\s+to|could\s+not|couldn't|rewrite|rephrase|translate|"
    r"in\s+the\s+future|later|tomorrow|next\s+(?:week|month)|"
    r"after\s+approval|when|once)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_ADD_POSTPOSED_CANCELLATION_RE = re.compile(
    r"(?:^|[,,;;..!??!]\s*)(?:Wait.|Wait a minute.|Stop.|Wait a minute.)"
    r"[,,]?\s*(?:Or is it?\s*)?(?:(?:First\s*)?(?:No, I don't.|No, I don't.(?:Yes.)?|"
    r"I'm not coming in.(?:Yes.)?|Don't add.(?:Yes.)?|Don't go in.(?:Yes.)?))"
    r"(?:[,,..!!??]?\s*(?:Thank you.(?:You.)?|Thanks.|Good work.))?\s*$|"
    r"(?:^|[,,;;..!??!]\s*)(?:I'm...\s*)?I'm sorry."
    r"(?:[,,..!!??]?\s*(?:Thank you.(?:You.)?|Thanks.|Good work.))?\s*$|"
    r"(?:^|[,,;;..!??!]\s*)(?:Wait.|Wait a minute.|Wait a minute.|No, no.[,,]?\s*)?"
    r"(?:(?:Just now.|Front)(?:That.|Request|Operation)?\s*)?"
    r"(?:Forget it.|Dismissed|Withdrawn.|No, I'm fine.|I'm out.|I'm done.|Stop it.|Let's not do it.|"
    r"Cancel(?:Into the pool.|Operation|Implementation)?(?:Yeah.)?|Undo(?:Into the pool.|Operation|Implementation)?|"
    r"Don't.(?:Into the pool.|Implementation|Operation|Yes.)|Not yet.(?:Into the pool.|Implementation|Operation))"
    r"(?:[,,]\s*(?:This time.|This time.)?\s*(?:I'm done.|Stop it.|Not implemented))?"
    r"(?:[,,..!!??]?\s*(?:Thank you.(?:You.)?|Thanks.|Good work.|Trouble.(?:You.)?Yes.))?\s*$|"
    r"(?:^|[,;.!?]\s*)(?:actually\s+)?(?:no|never\s+mind|forget\s+it|"
    r"scratch\s+that|abort|withdraw|stop|cancel\s+(?:that|it)|"
    r"do(?:n't|\s+not)\s+(?:do|execute)\s+(?:that|it))"
    r"(?:[,!.?]?\s*(?:thanks(?:\s+a\s+lot)?|thank\s+you))?\s*$",
    re.IGNORECASE,
)

_POOL_ADD_LIFECYCLE_RE = re.compile(
    r"(?:Accepted|Adopt|Deployment|Online.|Production|Production|Production|Input|Publishe to?Production|"
    r"Publishe to?Online.|Push?Online.|Push production|Active|Landing execution|Immediate|- I'm gonna do it.?|"
    r"In use|Start Use|Enable|Entry into force|Activate)|"
    r"(?<![A-Za-z0-9_])(?:adopt(?:s|ed|ing)?|deploy(?:s|ed|ing)?|"
    r"promot(?:e|es|ed|ing)|activat(?:e|es|ed|ing)|"
    r"enabl(?:e|es|ed|ing)|ship(?:s|ped|ping)?|"
    r"push(?:es|ed|ing)?|releas(?:e|es|ed|ing)|"
    r"publish(?:es|ed|ing)?|launch(?:es|ed|ing)?|"
    r"productioniz(?:e|es|ed|ing)|execut(?:e|es|ed|ing)|run(?:s|ning)?|"
    r"use(?:s|d|ing)?[^;.!?\n]{0,32}(?:in|on)[-\s]+prod(?:uction)?|"
    r"put[^;.!?\n]{0,32}into[-\s]+prod(?:uction)?|"
    r"enter(?:s|ed|ing)?[-\s]+prod(?:uction)?|take[^;.!?\n]{0,20}live|"
    r"(?:go(?:es|ing)?|went)[-\s]+live|roll(?:s|ed|ing)?[-\s]+out)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_ADD_SECOND_OPERATION_RE = re.compile(
    r"(?:Delete|Delete it.|Delete|It's deleted.|Remove|Fall back.|Pull back.|Withdrawn.|Get rid of it.|Remove|Clear|"
    r"Kick|Take it off.|Remove)"
    r"[^;;.\n]{0,100}"
    r"(?:pool-entry|candidate-rule|"
    r"Policy pool|Rule pool|Entry|Rule|It's...|This.|This one.)|"
    r"(?:pool-entry|candidate-rule|Policy pool|Rule pool|Entry|Rule|It's...|This.|This one.)"
    r"[^;;.\n]{0,100}(?:Delete|Delete it.|Delete|It's deleted.|Remove|Fall back.|Pull back.|Withdrawn.|"
    r"Get rid of it.|Remove|Clear|Kick|Take it off.|Remove)|"
    r"(?:Actions)[^;;.\n]{0,32}(?:For|Replace with|Set As|Set As|Set as|Set|"
    r"Set|Set|Switch to|Switch to|Modify to)|"
    r"(?:pool-entry|candidate-rule|Entry|Rule|It's...|This.|This one.)[^;;.\n]{0,80}"
    r"(?:For|Replace with|Set As|Set As|Set as|Set|Set|Set|Switch to|Switch to|"
    r"Modify to)|"
    r"(?:Restart|Again.|And then...|And then...|Catch.|Again.)\s*(?:- Put it on.[^;;.\n]{0,48})?"
    r"(?:For|Replace with|Set As|Set As|Set as|Set|Set|Set|Switch to|Switch to)"
    r"\s*(?:approval|reject|review|limit|pricing|segment|Pass.|Reject|Review)|"
    r"(?:Adjustment|Modify|Change)[^;;.\n]{0,80}(?:Yes|Done.)\s*"
    r"(?:approval|reject|review|limit|pricing|segment|Pass.|Reject|Review)|"
    r"(?:Complete)?(?:Reorder|Sort)[^;;.\n]{0,100}(?:Policy pool|Rule pool)|"
    r"(?:Compile|Preview)[^;;.\n]{0,80}(?:Policy pool|Rule pool)|"
    r"(?:Policy pool|Rule pool)[^;;.\n]{0,80}(?:Compile|Preview)|"
    r"(?:Restart|Again.|And then...|And then...|Again.)\s*(?:Compile|Preview)|"
    r"(?:^|[,,;;..!??!]\s*)(?:(?:And then...|And then...|Catch.|Again.|And...|Meanwhile...|"
    r"After completion)\s*)?(?:Immediately\s*)?(?:Retrospect|Measurement(?:Effects|Impact)?|"
    r"Apply to?(?:Current)?Sample|Generate(?:Effects|Policy|Analysis)?Report|Form Document|"
    r"Submit(?:Approval|Audit|Evaluation)|Start(?:Approval|Audit|Evaluation)|Referral)|"
    r"(?:^|[,;.!?]\s*)(?:(?:then|next|afterwards|and)\s+)?"
    r"(?:immediately\s+)?(?:backtest|apply[^;.!?\n]{0,40}(?:sample|dataset)|"
    r"generate[^;.!?\n]{0,40}report|submit[^;.!?\n]{0,40}(?:approval|review))|"
    r"(?<![A-Za-z0-9_])(?:remove|delete)\b[^;.!?\n]{0,100}"
    r"(?:pool-entry|candidate-rule|pool|entry|rule)|"
    r"(?<![A-Za-z0-9_])(?:set|change|update|make)\b[^;.!?\n]{0,80}"
    r"(?:\baction\b|\b(?:approval|reject|review|limit|pricing|segment)\b)|"
    r"(?<![A-Za-z0-9_])(?:reorder|sort|compile|preview)\b"
    r"[^;.!?\n]{0,100}\bpool\b",
    re.IGNORECASE,
)

_POOL_MUTATION_INTENT_PATTERNS = {
    "strategy_pool_remove_entry": re.compile(
        r"(?:Delete|Delete it.|Delete|Remove|Fall back.|Pull back.|Get rid of it.|Remove|Kick|Take it off.|Remove)|"
        r"(?<![A-Za-z0-9_])(?:remove|delete)(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "strategy_pool_set_action": re.compile(
        r"(?:Actions[^;;.\n]{0,32})?(?:For|Replace with|Set As|Set As|Set as|Set|"
        r"Set|Set|Switch to|Switch to|Modify to)|"
        r"(?<![A-Za-z0-9_])(?:set|change|update)\b[^;.!?\n]{0,80}\baction\b",
        re.IGNORECASE,
    ),
    "strategy_pool_reorder": re.compile(
        r"(?:(?:Press)?Complete(?:Order)?\s*)?(?:Reorder|Sort)|"
        r"(?<![A-Za-z0-9_])(?:reorder|sort)(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
}

_POOL_MUTATION_NONCOMMAND_RE = re.compile(
    r"[??]|(?:Can you...|Can I?|Is it possible?|Is that okay?|Can you...)|"
    r"(?:Yesterday.|Yesterday|Before|Before|Go on.|Last time.|Previous|Earlier|Once.|Already)"
    r"[^;;.\n]{0,180}(?:Delete|Remove|Replace with|Settings|Reorder|Sort)|"
    r"(?:Rewrite|Redo|Dust|Translation|Repeat)[^;;.\n]{0,120}"
    r"(?:This.|That's the sentence.|Next sentence|Below|Text|Documentation|Contents)|"
    r"(?<![A-Za-z0-9_])(?:can|could|would)\s+you\b|"
    r"(?<![A-Za-z0-9_])(?:yesterday|previously|earlier|last\s+time|"
    r"rewrite|rephrase|translate)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_REASON_CANCELLATION_RE = re.compile(
    r"(?:Forget it.|Let's do it.|Retrovert.|Pause|Stop.|Let's go.|No, I don't.|Not yet.|Cancel|Undo|Withdrawn.)|"
    r"(?<![A-Za-z0-9_])(?:never\s+mind|forget\s+it|scratch\s+that|"
    r"hold\s+on|cancel|abort|withdraw|stop)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_ADD_STRATEGY_TYPE_LABEL_RE = re.compile(
    r"(?:Policy pool type|Pool\s*Type|strategy\s+pool\s+type|pool\s+type)"
    r"\s*(?:[::=]|Yes.|Yes)",
    re.IGNORECASE,
)

_POOL_ADD_DEFAULT_ACTION_LABEL_RE = re.compile(
    r"(?:(?:Pool|Policy pool)\s*)?Default Action|"
    r"(?<![A-Za-z0-9_])default\s+(?:pool\s+)?action"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_ADD_HIT_ACTION_LABEL_RE = re.compile(
    r"(?:Rule)?Hit action.|(?<![A-Za-z0-9_])(?:hit|match(?:ed)?)"
    r"\s+action(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_ADD_DEFAULT_REASON_CODE_LABEL_RE = re.compile(
    r"(?:(?:Pool|Policy pool)\s*)?Default(?:Actions)?Reason code|"
    r"(?<![A-Za-z0-9_])default(?:\s+action)?\s+"
    r"reason(?:\s+|[-_])code(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_ADD_HIT_REASON_CODE_LABEL_RE = re.compile(
    r"(?:Rule)?Hit.(?:Actions)?Reason code|"
    r"(?<![A-Za-z0-9_])(?:hit|match(?:ed)?)(?:\s+action)?\s+"
    r"reason(?:\s+|[-_])code(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_ADD_DEFAULT_OUTPUT_VALUE_LABEL_RE = re.compile(
    r"(?:(?:Pool|Policy pool)\s*)?Default(?:Actions)?Output value|"
    r"(?<![A-Za-z0-9_])default(?:\s+action)?\s+"
    r"output(?:\s+|[-_])value(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_ADD_HIT_OUTPUT_VALUE_LABEL_RE = re.compile(
    r"(?:Rule)?Hit.(?:Actions)?Output value|"
    r"(?<![A-Za-z0-9_])(?:hit|match(?:ed)?)(?:\s+action)?\s+"
    r"output(?:\s+|[-_])value(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_POOL_ADD_PLACEMENT_MODE_LABEL_RE = re.compile(
    r"(?:Placement|placement\s+mode)\s*(?:[::=]|Yes.|Yes)",
    re.IGNORECASE,
)

_POOL_ADD_BEFORE_SELECTED_MEMBERS_RE = re.compile(
    r"Reservations(?:Original|Selected|These.)?Members as retreats"
    r"\s*(?:,|,|And...|and|and)?\s*"
    r"(?:Will|- Put it on.)?\s*(?:Voting|Vote.(?:Candidates)?)?\s*"
    r"Put it on.(?:Original|Selected|These.)?Former members(?:Noodles.)?",
    re.IGNORECASE,
)

_POOL_ADD_REPLACE_SELECTED_MEMBERS_RE = re.compile(
    r"By\s*(?:Voting|Vote.(?:Candidates)?)\s*"
    r"(?:Alternative|Replace|Replace)(?:Original|Selected|These.)?Members",
    re.IGNORECASE,
)

_POOL_ADD_BEFORE_SELECTED_MEMBERS_EXPLANATION_RE = re.compile(
    r"Reservations(?:Original|Selected|These.)?Membership as outstanding\s*n\s*Rule 16 Subsequent rules of procedure",
    re.IGNORECASE,
)

_POOL_ADD_REASON_LABEL_RE = re.compile(
    r"(?:Into the pool.|Add|Operation)?Rationale\s*(?:[::=]|Yes.|Yes)\s*"
    r"(?P<zh>[^,,;;.\n]+)|"
    r"(?<![A-Za-z0-9_])(?:pool\s+reason|reason|rationale)"
    r"\s*(?::|=|is)\s*(?P<en>[^,;.!?\n]+)",
    re.IGNORECASE,
)

_POOL_ADD_STRATEGY_TYPE_NOUN_PATTERNS = {
    "approval": re.compile(
        r"(?:Approval|Access)(?:Policy|Rule)?Ji.|"
        r"(?:Approval|Access)\s*(?:(?:Strategy|Rule)\s*)?Pool|"
        r"(?<![A-Za-z0-9_])approval\s+(?:(?:strategy|rule)\s+)?pool"
        r"(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "reject": re.compile(
        r"Reject(?:Policy|Rule)?Ji.|Reject\s*(?:(?:Strategy|Rule)\s*)?Pool|"
        r"(?<![A-Za-z0-9_])reject\s+(?:(?:strategy|rule)\s+)?pool"
        r"(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "limit": re.compile(
        r"(?:Amount|Letters)(?:Policy|Rule)?Ji.|"
        r"(?:Amount|Letters)\s*(?:(?:Strategy|Rule)\s*)?Pool|"
        r"(?<![A-Za-z0-9_])limit\s+(?:(?:strategy|rule)\s+)?pool"
        r"(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "pricing": re.compile(
        r"(?:Pricing|Interest rate)(?:Policy|Rule)?Ji.|"
        r"(?:Pricing|Interest rate)\s*(?:(?:Strategy|Rule)\s*)?Pool|"
        r"(?<![A-Za-z0-9_])pricing\s+(?:(?:strategy|rule)\s+)?pool"
        r"(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "segmentation": re.compile(
        r"(?:Group|Layer)(?:Policy|Rule)?Ji.|"
        r"(?:Group|Layer)\s*(?:(?:Strategy|Rule)\s*)?Pool|"
        r"(?<![A-Za-z0-9_])segmentation\s+(?:(?:strategy|rule)\s+)?pool"
        r"(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
}

def utterance_targets_strategy_pool_stability(utterance: str) -> bool:
    """Reserve a positive current-Pool distribution-stability command."""

    if utterance_targets_candidate_monthly_stability(utterance):
        return False
    if _POOL_VALIDATION_TARGET_RE.search(utterance) is not None:
        return False
    if (
        _POOL_STABILITY_TARGET_RE.search(utterance) is None
        or _POOL_STABILITY_POSITIVE_INTENT_RE.search(utterance) is None
        or _POOL_IMPACT_REPORT_ONLY_RE.search(utterance) is not None
    ):
        return False
    return True

def _utterance_targets_strategy_pool_apply(utterance: str) -> bool:
    """Reserve any explicit current-Pool-to-current-sample application clause."""

    return _POOL_APPLY_TARGET_RE.search(utterance) is not None

def utterance_targets_strategy_pool_materialize(utterance: str) -> bool:
    """Reserve an explicit current-Pool-to-draft-Strategy command."""

    return _POOL_MATERIALIZE_TARGET_RE.search(utterance) is not None

def _utterance_targets_strategy_pool_validation(utterance: str) -> bool:
    """Reserve explicit independent validation/OOT Pool replay clauses."""

    return _POOL_VALIDATION_TARGET_RE.search(utterance) is not None

def _utterance_targets_strategy_pool_impact(utterance: str) -> bool:
    if utterance_targets_strategy_pool_stability(utterance):
        return False
    if _POOL_IMPACT_TARGET_RE.search(utterance) is None:
        return False
    if (
        _POOL_IMPACT_REPORT_ONLY_RE.search(utterance) is not None
        and _POOL_IMPACT_POSITIVE_INTENT_RE.search(utterance) is None
        and _POOL_IMPACT_NEGATED_RE.search(utterance) is None
        and _POOL_IMPACT_NONCOMMAND_RE.search(utterance) is None
    ):
        # "AddPool,And then generate impact reports." contains both Pool and effect, but
        # its report clause does not authorize an impact measurement.
        return False
    signals = tuple(
        match
        for pattern in (
            _POOL_IMPACT_POSITIVE_INTENT_RE,
            _POOL_IMPACT_NEGATED_RE,
            _POOL_IMPACT_NONCOMMAND_RE,
            _POOL_IMPACT_REPORT_ONLY_RE,
        )
        for match in pattern.finditer(utterance)
    )
    if not signals:
        return False
    other_operations = tuple(_POOL_IMPACT_SECOND_OPERATION_RE.finditer(utterance))
    if not other_operations:
        return True
    if _POOL_IMPACT_NEGATED_RE.search(utterance) is not None:
        # A negated impact clause followed by a separate positive operation
        # (for example "Don't retrace it. Just compile it.") must not hijack that operation.
        return False
    # "The evaluation willX Impact of joining the policy pool" describes one hypothetical add: its impact
    # phrase encloses the add verb and must stay on the existing add guardrail.
    # A standalone "MeasurementPool Impact, then compile/Deployment" span does not overlap the
    # second operation and must still force the impact-specific clarification.
    return any(
        all(
            signal.end() <= operation.start()
            or operation.end() <= signal.start()
            for operation in other_operations
        )
        for signal in signals
    )

def _ground_strategy_pool_apply_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Prove the one Pool type and optional output prefix came from this command."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if (
        _POOL_APPLY_NONCURRENT_RE.search(utterance) is not None
        or _POOL_APPLY_POSITIVE_INTENT_RE.search(utterance) is None
        or _POOL_APPLY_TARGET_RE.search(utterance) is None
    ):
        return _clarification(
            "Please specify the current type of a given type with a single, positive command on the current cycle"
            "Strategy Pool Apply or write back the current sample;denial, query, history/Future or hypothetical"
            "Description does not create derivative datasets.",
            code="strategy_pool_apply_positive_command_required",
            fields=("apply_intent",),
        )
    if _POOL_APPLY_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Pool revision/hash,artifact,data sets,SampleDesign,requirements,"
            "StrategySpec and life cycle status can only be restored by the platform; only available in the requestPool "
            "Type and optionaloutput_prefix.",
            code="strategy_pool_apply_platform_binding_forbidden",
            fields=("platform_binding",),
        )
    if _POOL_APPLY_SECOND_OPERATION_RE.search(utterance) is not None:
        return _clarification(
            "Strategy Pool Application must be the only operation in the current cycle;Pool Modify, adopt, activate,"
            "Deployment, go online, export or report must be broken down into a follow-up request.",
            code="strategy_pool_apply_single_operation_required",
            fields=("workflow",),
        )

    missing_controls: list[str] = []
    strategy_type = str(inputs.get("strategy_type") or "")
    mentioned_types = {
        item[0] for item in _voting_strategy_type_mentions(utterance)
    }
    pattern = _POOL_STRATEGY_TYPE_GROUNDING.get(strategy_type)
    if (
        pattern is None
        or pattern.search(utterance) is None
        or mentioned_types != {strategy_type}
    ):
        missing_controls.append(f"strategy_type {strategy_type or 'unknown'}")

    prefix_labels = tuple(_POOL_APPLY_OUTPUT_PREFIX_LABEL_RE.finditer(utterance))
    prefix_matches = tuple(_POOL_APPLY_OUTPUT_PREFIX_RE.finditer(utterance))
    prefix_mentions = tuple(match.group("prefix") for match in prefix_matches)
    output_prefix = inputs.get("output_prefix")
    if len(prefix_labels) != len(prefix_matches):
        missing_controls.append("output_prefix")
    elif output_prefix is None:
        if prefix_mentions:
            missing_controls.append("output_prefix")
    elif prefix_mentions != (output_prefix,):
        missing_controls.append(f"output_prefix {output_prefix}")

    if missing_controls:
        missing_controls = list(dict.fromkeys(missing_controls))
        return _clarification(
            "Strategy Pool The application can only be the only one in the original language.Pool Type and optionalASCII "
            "output prefix;currently unable to check:"
            + ",".join(missing_controls)
            + ".The platform doesn't speculate for the users.Pool,Prefix or any data/Evidence bound.",
            code="strategy_pool_apply_controls_not_grounded",
            fields=tuple(missing_controls),
        )
    return result

def _ground_strategy_pool_materialize_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Prove one current Pool type and a draft-only materialization command."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    intent_text = _POOL_MATERIALIZE_NEGATED_LIFECYCLE_DISCLAIMER_RE.sub(
        "",
        utterance,
    )
    if (
        _POOL_MATERIALIZE_NONCURRENT_RE.search(intent_text) is not None
        or _POOL_MATERIALIZE_POSITIVE_INTENT_RE.search(intent_text) is None
        or _POOL_MATERIALIZE_TARGET_RE.search(intent_text) is None
    ):
        return _clarification(
            "Please specify the current type of a given type with a single, positive command on the current cycle"
            "Strategy Pool Todraft Strategy;Negative, question, history./Future or"
            "Assume that the description does not create a strategy.",
            code="strategy_pool_materialize_positive_command_required",
            fields=("materialize_intent",),
        )
    if _POOL_MATERIALIZE_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Pool revision/hash,artifact,design hash,StrategySpec,"
            "requirements and indicators can only be restored by the platform; only requestedPool Type.",
            code="strategy_pool_materialize_platform_binding_forbidden",
            fields=("platform_binding",),
        )
    if _POOL_MATERIALIZE_SECOND_OPERATION_RE.search(intent_text) is not None:
        return _clarification(
            "Strategy Pool Physicalization must be the only operation in the current cycle; adopt, deploy, retrofit, apply,"
            "Reporting, monitoring and reportingDSL Export must be split into a follow-up request. This step is created onlydraft Strategy.",
            code="strategy_pool_materialize_single_operation_required",
            fields=("workflow",),
        )

    strategy_type = str(inputs.get("strategy_type") or "")
    mentioned_types = {
        item[0] for item in _voting_strategy_type_mentions(utterance)
    }
    pattern = _POOL_STRATEGY_TYPE_GROUNDING.get(strategy_type)
    if (
        pattern is None
        or pattern.search(utterance) is None
        or mentioned_types != {strategy_type}
    ):
        return _clarification(
            "Strategy Pool The only thing that's clear is the original language.Pool type;platforms do not"
            "Guess for the userPool,hash,StrategySpec,requirements or indicators.",
            code="strategy_pool_materialize_controls_not_grounded",
            fields=("strategy_type",),
        )
    return result

def _ground_strategy_pool_validation_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Prove Pool type and one independent partition came from this command."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if (
        _POOL_VALIDATION_NONCURRENT_RE.search(utterance) is not None
        or _POOL_VALIDATION_POSITIVE_INTENT_RE.search(utterance) is None
        or _POOL_VALIDATION_TARGET_RE.search(utterance) is None
    ):
        return _clarification(
            "Please specify a requirement for a single order in the current round, positive formapproval/reject "
            "Strategy Pool Implementationvalidation orOOT Independent sample playback validation;"
            "Negative, question, history./Future or hypothetical descriptions will not be implemented.",
            code="strategy_pool_validation_positive_command_required",
            fields=("validation_intent",),
        )
    if _POOL_VALIDATION_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "Pool/SampleDesign artifact,revision/hash,dataset/workspace,"
            "target,requirements,population,comparison_mode,Indicators and status"
            "Recovery from the platform only; request onlyPool Type andvalidation/OOT Division.",
            code="strategy_pool_validation_platform_binding_forbidden",
            fields=("platform_binding",),
        )
    if _POOL_VALIDATION_EVIDENCE_SCOPE_RE.search(utterance) is not None:
        return _clarification(
            "Independent sample playback validation only releases actualvalidation/OOT Actions, risks, amounts and months-by-month"
            "Play back evidence, do not calculate or claimPSI,Stability or drift; these must be used separately"
            "StabilityWorkflow.",
            code="strategy_pool_validation_evidence_scope_forbidden",
            fields=("evidence_scope",),
        )
    if _POOL_VALIDATION_SECOND_OPERATION_RE.search(utterance) is not None:
        return _clarification(
            "Strategy Pool Independent sample playback validation must be the only operation on the current cycle;Pool,"
            "Application must be completed in the form of a follow-up request for return, report, promotion, acceptance or deployment.",
            code="strategy_pool_validation_single_operation_required",
            fields=("workflow",),
        )

    missing_controls: list[str] = []
    strategy_type = str(inputs.get("strategy_type") or "")
    mentioned_types = {
        item[0] for item in _voting_strategy_type_mentions(utterance)
    }
    type_pattern = _POOL_STRATEGY_TYPE_GROUNDING.get(strategy_type)
    if (
        type_pattern is None
        or type_pattern.search(utterance) is None
        or mentioned_types != {strategy_type}
    ):
        missing_controls.append(f"strategy_type {strategy_type or 'unknown'}")

    partition = str(inputs.get("partition") or "")
    mentioned_partitions = {
        name
        for name, pattern in _POOL_VALIDATION_PARTITION_GROUNDING.items()
        if pattern.search(utterance) is not None
    }
    partition_pattern = _POOL_VALIDATION_PARTITION_GROUNDING.get(partition)
    if (
        partition_pattern is None
        or partition_pattern.search(utterance) is None
        or mentioned_partitions != {partition}
    ):
        missing_controls.append(f"partition {partition or 'unknown'}")

    if missing_controls:
        return _clarification(
            "Independent sample playback validation can only be used as the only clear word in the original language.approval/reject Pool "
            "Type and onevalidation/OOT partition;currently unrecognised:"
            + ",".join(dict.fromkeys(missing_controls))
            + ".The platform does not speculate about type, partition or evidence binding.",
            code="strategy_pool_validation_controls_not_grounded",
            fields=tuple(dict.fromkeys(missing_controls)),
        )
    return result

def _ground_strategy_pool_stability_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Prove the one current Pool type came from this stability command."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if (
        _POOL_STABILITY_NONCURRENT_RE.search(utterance) is not None
        or _POOL_STABILITY_POSITIVE_INTENT_RE.search(utterance) is None
        or _POOL_STABILITY_TARGET_RE.search(utterance) is None
        or _POOL_IMPACT_REPORT_ONLY_RE.search(utterance) is not None
    ):
        return _clarification(
            "Please use the current wheel, positive single command to explicitly require a measurement of the currentStrategy Pool "
            "..cross the partitionsPSI stability;denial, enquiring, history/Future, hypothetical or only report generation"
            "No measurements will be performed.",
            code="strategy_pool_stability_positive_command_required",
            fields=("stability_intent",),
        )
    if _POOL_STABILITY_PLATFORM_CONTROL_RE.search(utterance) is not None:
        return _clarification(
            "ImpactCube/Pool/SampleDesign artifact,revision/hash,dataset,"
            "Thresholds, indicators and results can only be frozen or calculated by the Platform; only five categories can be provided in the requestPool "
            "One of them.strategy_type.",
            code="strategy_pool_stability_platform_binding_forbidden",
            fields=("platform_binding",),
        )
    if _POOL_STABILITY_SECOND_OPERATION_RE.search(utterance) is not None:
        return _clarification(
            "Strategy Pool (a) Cross-zonal stability measurements must be the only operation in the current cycle;Pool Revision,"
            "Applications must be completed in the form of a follow-up request for write-back, report-up, creation, adoption, promotion or deployment.",
            code="strategy_pool_stability_single_operation_required",
            fields=("workflow",),
        )

    strategy_type = str(inputs.get("strategy_type") or "")
    mentioned_types = {
        item[0] for item in _impact_cube_strategy_type_mentions(utterance)
    }
    type_pattern = _POOL_STRATEGY_TYPE_GROUNDING.get(strategy_type)
    if (
        type_pattern is None
        or type_pattern.search(utterance) is None
        or mentioned_types != {strategy_type}
    ):
        return _clarification(
            "Cross-zonal stability can only be used as the only clear expression in the original language.approval,reject,limit,"
            "pricing orsegmentation Pool type;platforms do not come from action, indicators or history"
            "Evidence guess type.",
            code="strategy_pool_stability_controls_not_grounded",
            fields=(f"strategy_type {strategy_type or 'unknown'}",),
        )
    return result

def _ground_strategy_pool_impact_request(
    utterance: str,
    result: StrategyRequestCompilation,
    *,
    whitelist: tuple[str, ...],
) -> StrategyRequestCompilation:
    """Prove every executable measurement control came from this utterance."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if (
        _POOL_IMPACT_NEGATED_RE.search(utterance)
        or _POOL_IMPACT_NONCOMMAND_RE.search(utterance)
        or _POOL_IMPACT_REPORT_ONLY_RE.search(utterance)
    ):
        return _clarification(
            "Please specify the requirements in a single order in the current cycle, positive formStrategy Pool Impact measurement;"
            "Negative, question, history./The measurement will not be carried out in the future, or only in the generation of the report.",
            code="strategy_pool_impact_positive_command_required",
            fields=("measurement_intent",),
        )
    if _POOL_IMPACT_POSITIVE_INTENT_RE.search(utterance) is None:
        return _clarification(
            "There's no clear mandate for it.Strategy Pool Impact measurement. Please specify what you want to measure."
            " approval orreject Pool;Ben.Workflow Only read-only evidence is generated.",
            code="strategy_pool_impact_positive_command_required",
            fields=("measurement_intent",),
        )
    if _POOL_IMPACT_SECOND_OPERATION_RE.search(utterance):
        return _clarification(
            "Strategy Pool Impact measurement must be the only operation in the current cycle; enter, delete, modify, reorder,"
            "Compile, create strategies, write back, adopt or deploy in a form that is not followed up.",
            code="strategy_pool_impact_single_operation_required",
            fields=("workflow",),
        )

    missing_controls: list[str] = []
    strategy_type = str(inputs.get("strategy_type") or "")
    strategy_type_pattern = _POOL_STRATEGY_TYPE_GROUNDING.get(strategy_type)
    strategy_type_mentions = _voting_strategy_type_mentions(utterance)
    mentioned_strategy_types = {item[0] for item in strategy_type_mentions}
    selected_type_is_negated = any(
        item[0] == strategy_type
        and _pool_impact_span_is_negated(utterance, start=item[1])
        for item in strategy_type_mentions
    )
    if (
        strategy_type_pattern is None
        or strategy_type_pattern.search(utterance) is None
        or mentioned_strategy_types != {strategy_type}
        or selected_type_is_negated
    ):
        missing_controls.append(f"strategy_type {strategy_type or 'unknown'}")

    comparison_mode = str(inputs.get("comparison_mode") or "absolute")
    mentions_baseline_comparison = (
        _POOL_IMPACT_BASELINE_MODE_RE.search(utterance) is not None
    )
    mentions_absolute = _POOL_IMPACT_ABSOLUTE_MODE_RE.search(utterance) is not None
    if comparison_mode == "vs_baseline":
        if not mentions_baseline_comparison or mentions_absolute:
            missing_controls.append("comparison_mode vs_baseline")
        baseline_strategy_id = str(inputs.get("baseline_strategy_id") or "")
        baseline_id_mentions = tuple(
            _POOL_IMPACT_STRATEGY_ID_RE.finditer(utterance)
        )
        positively_mentioned_ids = {
            match.group(0).casefold()
            for match in baseline_id_mentions
            if not _pool_impact_span_is_negated(utterance, start=match.start())
        }
        negated_ids = {
            match.group(0).casefold()
            for match in baseline_id_mentions
            if _pool_impact_span_is_negated(utterance, start=match.start())
        }
        selected_id = baseline_strategy_id.casefold()
        if (
            not baseline_strategy_id
            or not _utterance_contains_token(utterance, baseline_strategy_id)
            or positively_mentioned_ids != {selected_id}
            or selected_id in negated_ids
        ):
            missing_controls.append(
                baseline_strategy_id or "baseline_strategy_id"
            )
    elif mentions_baseline_comparison or (
        _POOL_IMPACT_STRATEGY_ID_RE.search(utterance) is not None
    ):
        missing_controls.append("comparison_mode vs_baseline")

    mentioned_columns = tuple(
        column for column in whitelist if _utterance_contains_token(utterance, column)
    )
    explicit_column_bindings = _pool_impact_explicit_column_bindings(
        utterance,
        whitelist,
    )
    for field, values in explicit_column_bindings.items():
        selected = inputs.get(field)
        if len(values) != 1 or selected not in values:
            expected = "/".join(sorted(values)) or field
            missing_controls.append(f"{field} {expected}")
    for field in ("month_col", "loan_amount_col", "overdue_amount_col"):
        value = inputs.get(field)
        if isinstance(value, str):
            if (
                not _utterance_contains_token(utterance, value)
                or _pool_impact_token_is_negated(utterance, value)
                or any(
                    other != value
                    and _pool_impact_tokens_are_alternatives(
                        utterance, value, other
                    )
                    for other in mentioned_columns
                )
            ):
                missing_controls.append(f"{field} {value}")
    if inputs.get("drop_nan_labels") is True and (
        _POOL_IMPACT_DROP_NAN_TRUE_RE.search(utterance) is None
        or _POOL_IMPACT_DROP_NAN_NEGATED_RE.search(utterance) is not None
    ):
        missing_controls.append("drop_nan_labels=true")
    if missing_controls:
        rendered = ",".join(dict.fromkeys(missing_controls))
        return _clarification(
            "Strategy Pool Impact measurement can only be done in the user's original languagePool Type, baseline model/CompleteID,"
            "Precise listing and blank tag authorization; it is not possible to verify:"
            f"{rendered}.The platform will not be usedLLM And guessed data binding, columns,hash,Indicators or strategies.",
            code="strategy_pool_impact_controls_not_grounded",
            fields=tuple(dict.fromkeys(missing_controls)),
        )
    return result

def _pool_impact_span_is_negated(utterance: str, *, start: int) -> bool:
    prefix = utterance[max(0, start - 32) : start]
    return re.search(
        r"(?:Don't.|Don't.|No, I'm fine.|Do Not Use|Ban|Exclude|Remove|Not|No, it's not.|Not really.)"
        r"[^,,;;..!??\n]{0,16}$|"
        r"(?<![A-Za-z0-9_])(?:do\s+not|don't|not|exclude|without)"
        r"[^,;.!?\n]{0,16}$",
        prefix,
        re.IGNORECASE,
    ) is not None

def _pool_impact_token_is_negated(utterance: str, token: str) -> bool:
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )
    return any(
        _pool_impact_span_is_negated(utterance, start=match.start())
        for match in pattern.finditer(utterance)
    )

def _pool_impact_explicit_column_bindings(
    utterance: str,
    whitelist: tuple[str, ...],
) -> dict[str, set[str]]:
    labels = {
        "month_col": (
            r"(?:Month|Month|Month of application|Observation month)(?:Fields|Columns)|"
            r"(?<![A-Za-z0-9_])month(?:_col|\s+column)(?![A-Za-z0-9_])"
        ),
        "loan_amount_col": (
            r"(?:Loans|Loans|Borrowing)Amount(?:Fields|Columns)|"
            r"(?<![A-Za-z0-9_])loan(?:_amount_col|\s+amount\s+column)"
            r"(?![A-Za-z0-9_])"
        ),
        "overdue_amount_col": (
            r"Overdue amounts(?:Fields|Columns)|"
            r"(?<![A-Za-z0-9_])overdue(?:_amount_col|\s+amount\s+column)"
            r"(?![A-Za-z0-9_])"
        ),
    }
    bindings = {field: set() for field in labels}
    for column in sorted(whitelist, key=len, reverse=True):
        token = (
            rf"(?<![A-Za-z0-9_]){re.escape(column)}(?![A-Za-z0-9_])"
        )
        for field, label in labels.items():
            before = re.compile(
                rf"(?:{label})\s*(?:(?:Yes|Yes.|Use|Use|Selection|Assign)\s*)?"
                rf"(?:=|:|:)?\s*{token}",
                re.IGNORECASE,
            )
            after = re.compile(
                rf"{token}\s*(?:(?:As|Use as|Yes.|Yes)\s*)?(?:{label})",
                re.IGNORECASE,
            )
            if before.search(utterance) or after.search(utterance):
                bindings[field].add(column)
    return {field: values for field, values in bindings.items() if values}

def _pool_impact_tokens_are_alternatives(
    utterance: str,
    left_token: str,
    right_token: str,
) -> bool:
    token_patterns = (
        re.compile(
            rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )
        for token in (left_token, right_token)
    )
    left_matches, right_matches = (tuple(pattern.finditer(utterance)) for pattern in token_patterns)
    for left in left_matches:
        for right in right_matches:
            first, second = sorted((left, right), key=lambda item: item.start())
            between = utterance[first.end() : second.start()]
            if len(between) <= 24 and re.search(
                r"(?:Or...|Or...|Or is it?|or|/|\bor\b)", between, re.IGNORECASE
            ):
                return True
    return False

def _pool_clause_prefix(
    utterance: str,
    *,
    start: int,
) -> str:
    left = max(
        utterance.rfind(separator, 0, start)
        for separator in (",", ",", ";", ";", ".", ".", "\n")
    )
    return utterance[left + 1 : start]

def _pool_operation_is_negated(utterance: str, *, start: int) -> bool:
    prefix = _pool_clause_prefix(utterance, start=start)
    negations = tuple(
        re.finditer(
            r"(?:Don't.|No, I'm fine.|Not anymore.|No need.|No need.|No, I don't.|No, I can't.|No way.|Not permitted|No, I don't.|"
            r"I'm not going to.|Not yet.|Not yet.|Don't.|Please don't.|Don't do it.|Do not|Ban|It's forbidden.|No way.|Reject|Cancel|"
            r"Undo|Stop|Abandon|Pause|No, no.|Not|None|Nope.)|"
            r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cannot|can't|won't|"
            r"must\s+not|mustn't|should\s+not|shouldn't|not|without|cancel|"
            r"stop|avoid|refrain)(?![A-Za-z0-9_])",
            prefix,
            re.IGNORECASE,
        )
    )
    if not negations:
        return False
    negation = negations[-1]
    return (
        re.search(
            r"(?:But...(?:Yes.)?|And...(?:Yes.)?|For|Replace with|Turn around.)|"
            r"(?<![A-Za-z0-9_])(?:but|instead|rather\s+than)(?![A-Za-z0-9_])",
            prefix[negation.end() :],
            re.IGNORECASE,
        )
        is None
    )

def _pool_add_intent_state(utterance: str) -> tuple[bool, bool]:
    reason_spans = _pool_add_reason_spans(utterance)
    matches = tuple(
        match
        for match in _POOL_ADD_INTENT_RE.finditer(utterance)
        if not any(left <= match.start() < right for left, right in reason_spans)
    )
    states = tuple(
        not _pool_operation_is_negated(utterance, start=match.start())
        for match in matches
    )
    return (
        bool(matches),
        bool(matches)
        and any(states)
        and all(states)
        and _POOL_ADD_HYPOTHETICAL_RE.search(utterance) is None
        and _POOL_ADD_POSTPOSED_CANCELLATION_RE.search(utterance) is None,
    )

def _pool_mutation_has_positive_intent(
    utterance: str,
    workflow: str,
    inputs: Mapping[str, Any],
) -> bool:
    pattern = _POOL_MUTATION_INTENT_PATTERNS.get(workflow)
    if pattern is None:
        return False
    reason_spans = _pool_add_reason_spans(utterance)
    matches = tuple(
        match
        for match in pattern.finditer(utterance)
        if not any(left <= match.start() < right for left, right in reason_spans)
    )
    states = tuple(
        not _pool_operation_is_negated(utterance, start=match.start())
        for match in matches
    )
    return (
        len(matches) == 1
        and any(states)
        and all(states)
        and _POOL_MUTATION_NONCOMMAND_RE.search(utterance) is None
        and not _pool_mutation_unconsumed_text(
            utterance,
            workflow=workflow,
            inputs=inputs,
            intent_match=matches[0] if len(matches) == 1 else None,
        )
    )

def _pool_source_prefix_count(utterance: str) -> int:
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFKC", utterance)
        if unicodedata.category(character) not in {"Cf", "Mn", "Me"}
    ).translate(
        _POOL_SOURCE_CONFUSABLE_TRANSLATION
        | str.maketrans(
            {
                "а": "a",
                "А": "A",
                "е": "e",
                "Е": "E",
                "о": "o",
                "О": "O",
                "с": "c",
                "С": "C",
                "х": "x",
                "Х": "X",
            }
        )
    )
    return sum(1 for _ in _POOL_SOURCE_PREFIX_RE.finditer(normalized))

_POOL_COMMAND_GLUE_RE = re.compile(
    r"(?:Please.|Please.|Trouble.|Please.|Help me.|Help.|Take my place.|Give it to me.|I want it.|I want to.|I hope...|"
    r"Now.|Immediately|Direct|This time.|This time.|Current|First|Just...|- Put it on.|Will|From|Yes.|Present.|to|"
    r"This.|This one.|The|above|Below|Select Results|Selection result|Candidate assets|Rule of candidacy|"
    r"Candidates|Assets|Leaf Node|Leaves.|Result|Rule pool|Policy pool|Rule|Policy|Ji.|Entry|"
    r"One.|One.|Medium|Lee.|Internal|It's...|Actions|Press|Complete|All|All|Order|In turn|"
    r"and|and|and)|"
    r"(?<![A-Za-z0-9_])(?:please|kindly|i\s+want\s+to|"
    r"i\s+would\s+like\s+to|help\s+me|for\s+me|now|immediately|"
    r"directly|this|that|the|selected|selection|candidate|asset|rule|"
    r"leaf|result|from|in|inside|of|action|complete|full|order|all|"
    r"strategy|pool|entry|and|to)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

def _pool_strip_spans(text: str, spans: Sequence[tuple[int, int]]) -> str:
    characters = list(text)
    for left, right in spans:
        for index in range(max(left, 0), min(right, len(characters))):
            characters[index] = " "
    return "".join(characters)

def _pool_command_residual(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = _POOL_COMMAND_GLUE_RE.sub(" ", text)
    return re.sub(r"[\s,,;;..!??!::=,'\"()()()()[]\[\]{}]+", "", text)

def _pool_mutation_unconsumed_text(
    utterance: str,
    *,
    workflow: str,
    inputs: Mapping[str, Any],
    intent_match: re.Match[str] | None,
) -> str:
    if intent_match is None:
        return utterance
    spans: list[tuple[int, int]] = [intent_match.span()]
    identifiers: list[str] = []
    if workflow in {"strategy_pool_remove_entry", "strategy_pool_set_action"}:
        for field in ("rule_id", "entry_id"):
            value = inputs.get(field)
            if isinstance(value, str):
                identifiers.append(value)
    elif workflow == "strategy_pool_reorder":
        ordered_ids = inputs.get("ordered_ids")
        if isinstance(ordered_ids, Sequence) and not isinstance(
            ordered_ids, str | bytes | bytearray
        ):
            identifiers.extend(value for value in ordered_ids if isinstance(value, str))
    for identifier in identifiers:
        spans.extend(match.span() for match in re.finditer(re.escape(identifier), utterance))
    strategy_type = str(inputs.get("strategy_type") or "")
    strategy_type_pattern = _POOL_STRATEGY_TYPE_GROUNDING.get(strategy_type)
    if strategy_type_pattern is not None:
        spans.extend(
            match.span() for match in strategy_type_pattern.finditer(utterance)
        )
    if workflow == "strategy_pool_set_action":
        action = inputs.get("action")
        action_type = str(action.get("type") or "") if isinstance(action, Mapping) else ""
        action_pattern = _POOL_ACTION_GROUNDING.get(action_type)
        if action_pattern is not None:
            spans.extend(match.span() for match in action_pattern.finditer(utterance))
    spans.extend(_pool_add_reason_spans(utterance))
    reason = inputs.get("reason")
    if isinstance(reason, str) and reason:
        spans.extend(match.span() for match in re.finditer(re.escape(reason), utterance))
    return _pool_command_residual(_pool_strip_spans(utterance, spans))

def _pool_add_unconsumed_text(utterance: str) -> str:
    spans: list[tuple[int, int]] = []
    spans.extend(match.span() for match in _POOL_ADD_INTENT_RE.finditer(utterance))
    spans.extend(
        match.span()
        for pattern in (
            _AUTOMATIC_TREE_ASSET_ID_TOKEN_RE,
            _AUTOMATIC_TREE_LEAF_SELECTION_ID_TOKEN_RE,
            _INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ID_TOKEN_RE,
            _INTERACTIVE_TREE_FRONTIER_SELECTION_ID_TOKEN_RE,
            _CROSS_MATRIX_CELL_SELECTION_ID_TOKEN_RE,
            _SCORECARD_CUTOFF_SELECTION_ID_TOKEN_RE,
        )
        for match in pattern.finditer(utterance)
    )
    for pattern in (
        _POOL_ADD_STRATEGY_TYPE_LABEL_RE,
        _POOL_ADD_DEFAULT_ACTION_LABEL_RE,
        _POOL_ADD_HIT_ACTION_LABEL_RE,
        _POOL_ADD_DEFAULT_REASON_CODE_LABEL_RE,
        _POOL_ADD_HIT_REASON_CODE_LABEL_RE,
        _POOL_ADD_DEFAULT_OUTPUT_VALUE_LABEL_RE,
        _POOL_ADD_HIT_OUTPUT_VALUE_LABEL_RE,
        _POOL_ADD_PLACEMENT_MODE_LABEL_RE,
    ):
        spans.extend(
            (match.start(), _pool_add_clause_end(utterance, start=match.end()))
            for match in pattern.finditer(utterance)
        )
    for pattern in (
        _POOL_ADD_BEFORE_SELECTED_MEMBERS_RE,
        _POOL_ADD_REPLACE_SELECTED_MEMBERS_RE,
        _POOL_ADD_BEFORE_SELECTED_MEMBERS_EXPLANATION_RE,
    ):
        spans.extend(match.span() for match in pattern.finditer(utterance))
    spans.extend(_pool_add_negated_follow_up_spans(utterance))
    spans.extend(_pool_add_reason_spans(utterance))
    return _pool_command_residual(_pool_strip_spans(utterance, spans))

def _pool_add_negated_follow_up_spans(
    utterance: str,
) -> tuple[tuple[int, int], ...]:
    clause_spans: set[tuple[int, int]] = set()
    for pattern in (
        _POOL_ADD_LIFECYCLE_RE,
        _POOL_ADD_SECOND_OPERATION_RE,
        _POOL_PARTIAL_REORDER_RE,
        _POOL_HEURISTIC_REORDER_RE,
    ):
        for match in pattern.finditer(utterance):
            negated = (
                _pool_lifecycle_operation_is_negated(
                    utterance,
                    start=match.start(),
                )
                if pattern is _POOL_ADD_LIFECYCLE_RE
                else _pool_operation_is_negated(utterance, start=match.start())
            )
            if not negated:
                continue
            left = max(
                utterance.rfind(separator, 0, match.start())
                for separator in (",", ",", ";", ";", ".", ".", "\n")
            )
            right = _pool_add_clause_end(utterance, start=match.end())
            if _POOL_ADD_INTENT_RE.search(utterance[left + 1 : right]) is None:
                clause_spans.add((left + 1, right))
    return tuple(sorted(clause_spans))

def _pool_lifecycle_operation_is_negated(utterance: str, *, start: int) -> bool:
    prefix = _pool_clause_prefix(utterance, start=start)
    return (
        re.search(
            r"(?:Don't.|No, I'm fine.|Not anymore.|No need.|No need.|No, I don't.|No, I can't.|No way.|Not permitted|Not yet.|"
            r"Not yet.|Don't.|Please don't.|Don't do it.|Do not|Ban|It's forbidden.|No way.|No, no.|Not|None|Nope.(?:Yes.)?)"
            r"\s*(?:Again.|Conduct|Immediately|Direct)?\s*"
            r"(?:(?:Accepted|Adopt|Deployment|Online.|Production|Production|Production|Input|"
            r"Publishe to?Production|Publishe to?Online.|Push?Online.|Push production|Active|Landing execution|"
            r"Immediate|- I'm gonna do it.?|In use|Start Use|Enable|Entry into force|Activate)"
            r"\s*(?:or|and|and|and|,)?\s*)*$|"
            r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cannot|can't|won't|"
            r"must\s+not|mustn't|should\s+not|shouldn't|not|without)\s+"
            r"(?:(?:adopt(?:s|ed|ing)?|deploy(?:s|ed|ing)?|"
            r"promot(?:e|es|ed|ing)|activat(?:e|es|ed|ing)|"
            r"enabl(?:e|es|ed|ing)|ship(?:s|ped|ping)?|"
            r"push(?:es|ed|ing)?|releas(?:e|es|ed|ing)|"
            r"publish(?:es|ed|ing)?|launch(?:es|ed|ing)?|"
            r"productioniz(?:e|es|ed|ing)|execut(?:e|es|ed|ing)|run(?:s|ning)?|"
            r"use(?:s|d|ing)?[^;.!?\n]{0,32}(?:in|on)[-\s]+prod(?:uction)?|"
            r"put[^;.!?\n]{0,32}into[-\s]+prod(?:uction)?|"
            r"enter(?:s|ed|ing)?[-\s]+prod(?:uction)?|"
            r"take[^;.!?\n]{0,20}live|"
            r"(?:go(?:es|ing)?|went)[-\s]+live|"
            r"roll(?:s|ed|ing)?[-\s]+out)\s*(?:or|and)?\s*)*$",
            prefix,
            re.IGNORECASE,
        )
        is not None
    )

def _pool_add_has_positive_lifecycle_follow_up(utterance: str) -> bool:
    positive_lifecycle = any(
        not _pool_lifecycle_operation_is_negated(utterance, start=match.start())
        for match in _POOL_ADD_LIFECYCLE_RE.finditer(utterance)
    )
    positive_second_operation = any(
        not _pool_operation_is_negated(utterance, start=match.start())
        for pattern in (
            _POOL_ADD_SECOND_OPERATION_RE,
            _POOL_PARTIAL_REORDER_RE,
            _POOL_HEURISTIC_REORDER_RE,
        )
        for match in pattern.finditer(utterance)
    )
    return positive_lifecycle or positive_second_operation

def _pool_add_strategy_types(utterance: str) -> tuple[frozenset[str], bool]:
    reason_spans = _pool_add_reason_spans(utterance)
    add_target_matches = tuple(
        match
        for match in _POOL_ADD_INTENT_RE.finditer(utterance)
        if not _pool_operation_is_negated(utterance, start=match.start())
        and not any(left <= match.start() < right for left, right in reason_spans)
    )
    observed: set[str] = set()
    add_targets_valid = True
    for match in add_target_matches:
        add_target = match.group(0)
        if _pool_add_body_is_negated(add_target):
            add_targets_valid = False
            continue
        observed.update(
            strategy_type
            for strategy_type, pattern in _POOL_ADD_STRATEGY_TYPE_NOUN_PATTERNS.items()
            if pattern.search(add_target) is not None
        )
    label_bodies = _pool_add_label_bodies(
        utterance,
        _POOL_ADD_STRATEGY_TYPE_LABEL_RE,
    )
    for label_value in label_bodies:
        observed.update(
            strategy_type
            for strategy_type, pattern in _POOL_STRATEGY_TYPE_VALUE_GROUNDING.items()
            if pattern.search(label_value) is not None
        )
    raw_label_count = _pool_add_label_match_count(
        utterance,
        _POOL_ADD_STRATEGY_TYPE_LABEL_RE,
    )
    return (
        frozenset(observed),
        add_targets_valid
        and raw_label_count == len(label_bodies)
        and raw_label_count <= 1,
    )

def _pool_add_reason_value_spans(utterance: str) -> tuple[tuple[int, int], ...]:
    spans: list[tuple[int, int]] = []
    for match in _POOL_ADD_REASON_LABEL_RE.finditer(utterance):
        group = "zh" if match.group("zh") is not None else "en"
        spans.append(match.span(group))
    return tuple(spans)

def _pool_add_reason_spans(utterance: str) -> tuple[tuple[int, int], ...]:
    return tuple(
        match.span() for match in _POOL_ADD_REASON_LABEL_RE.finditer(utterance)
    )

def _pool_add_label_match_count(utterance: str, pattern: re.Pattern[str]) -> int:
    reason_spans = _pool_add_reason_spans(utterance)
    return sum(
        1
        for match in pattern.finditer(utterance)
        if not any(left <= match.start() < right for left, right in reason_spans)
    )

def _pool_add_clause_end(utterance: str, *, start: int) -> int:
    """Find the next top-level clause boundary without splitting data values."""

    opening = {"[": "]", "{": "}", "(": ")"}
    closing = frozenset(opening.values())
    stack: list[str] = []
    quote: str | None = None
    escaped = False
    for index in range(start, len(utterance)):
        char = utterance[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            continue
        if char in opening:
            stack.append(opening[char])
            continue
        if char in closing:
            if stack and stack[-1] == char:
                stack.pop()
            continue
        if stack:
            continue
        if char in {";", ";", ".", "\n", "?", "?", "!", "!", ","}:
            return index
        if char == ",":
            before = utterance[index - 1] if index > 0 else ""
            after = utterance[index + 1] if index + 1 < len(utterance) else ""
            if before.isdigit() and after.isdigit():
                continue
            return index
        if char == ".":
            before = utterance[index - 1] if index > 0 else ""
            after = utterance[index + 1] if index + 1 < len(utterance) else ""
            if before.isdigit() and after.isdigit():
                continue
            if after and not after.isspace() and after not in ",,;;..!??!":
                continue
            return index
    return len(utterance)

def _pool_add_authorized_clause_spans(
    utterance: str,
) -> tuple[tuple[int, int], ...]:
    """Return positive add clauses; IDs elsewhere cannot authorize a mutation."""

    reason_spans = _pool_add_reason_value_spans(utterance)
    spans: list[tuple[int, int]] = []
    for match in _POOL_ADD_INTENT_RE.finditer(utterance):
        if any(left <= match.start() < right for left, right in reason_spans):
            continue
        if _pool_operation_is_negated(utterance, start=match.start()):
            continue
        left = max(
            utterance.rfind(separator, 0, match.start())
            for separator in (",", ",", ";", ";", ".", ".", "\n")
        )
        prefix = utterance[left + 1 : match.start()]
        contrasts = tuple(
            re.finditer(
                r"(?:But...(?:Yes.)?|But...|It's...|Turn around.)|"
                r"(?<![A-Za-z0-9_])(?:but|instead|rather\s+than)"
                r"(?![A-Za-z0-9_])",
                prefix,
                re.IGNORECASE,
            )
        )
        if contrasts:
            left += contrasts[-1].end()
        right = _pool_add_clause_end(utterance, start=match.end())
        spans.append((left + 1, right))
    return tuple(dict.fromkeys(spans))

def _pool_add_label_is_negated(utterance: str, *, start: int) -> bool:
    prefix = _pool_clause_prefix(utterance, start=start)
    return (
        re.search(
            r"(?:Don't.|No, I'm fine.|No, I shouldn't.|No, I can't.|No way.|Not really.|No, it's not.|Not|Not|Don't.|Ban|Cancel)"
            r"\s*(?:Use|Settings|Selection|Adopt)?\s*(?:Here.|The|One.|the)?\s*$|"
            r"(?<![A-Za-z0-9_])(?:not|non|never)[-\s]*$|"
            r"(?<![A-Za-z0-9_])(?:do\s+not|don't|cannot|can't|must\s+not|"
            r"should\s+not)\s+(?:use|set|choose)\s*$",
            prefix,
            re.IGNORECASE,
        )
        is not None
    )

def _pool_add_body_is_negated(body: str) -> bool:
    return (
        re.search(
            r"(?:^|\s|But...|But...|But...|And...|,|,)(?:Please.\s*)?"
            r"(?:Don't.|No, I'm fine.|No, I shouldn't.|No, I can't.|No way.|Not really.|Not really.|No way.|Not at all.|No, it's not.|"
            r"Not|Not|Don't.|Ban|Cancel|"
            r"Exclude|Remove|Ignore|Except|Other Organiser|Excluded)|"
            r"(?:Not|Exclude|Remove|Ignore|Except|Other Organiser|Excluded)"
            r"(?=Approval|Access|Reject|Amount|Letters|Pricing|Interest rate|Group|Layer|"
            r"approval|reject|review|limit|pricing|segment)|"
            r"(?:Except...|Divide|Does Not Contain)\s*(?:Approval|Access|Reject|Amount|Letters|Pricing|"
            r"Interest rate|Group|Layer|approval|reject|review|limit|pricing|segment)|"
            r"(?:Approval|Access|Reject|Amount|Letters|Pricing|Interest rate|Group|Layer|"
            r"approval|reject|review|limit|pricing|segment)"
            r"[^;;.\n]{0,24}(?:Outside|Outside|Except|Exclude|Remove|Ignore|Other Organiser|Excluded)|"
            r"(?:^|\s|but\s+)(?<![A-Za-z0-9_])(?:do\s+not|don't|cannot|can't|"
            r"must\s+not|should\s+not|not|never|without|avoid|exclude(?:d|s|ing)?|"
            r"except(?:ed|ing)?|omit(?:ted|ting)?|ignor(?:e|ed|ing))"
            r"(?![A-Za-z0-9_])|"
            r"(?<![A-Za-z0-9_])(?:approval|reject|review|limit|pricing|segment)"
            r"\s+(?:is\s+)?(?:excluded|excepted|omitted|ignored)"
            r"(?![A-Za-z0-9_])|"
            r"(?<![A-Za-z0-9_])anything\s+but\s+"
            r"(?:approval|reject|review|limit|pricing|segment)"
            r"(?![A-Za-z0-9_])|"
            r"(?<![A-Za-z0-9_])(?:anything\s+)?other\s+than\s+"
            r"(?:approval|reject|review|limit|pricing|segment)"
            r"(?![A-Za-z0-9_])",
            body,
            re.IGNORECASE,
        )
        is not None
    )

def _pool_add_label_bodies(utterance: str, pattern: re.Pattern[str]) -> tuple[str, ...]:
    bodies: list[str] = []
    reason_spans = _pool_add_reason_value_spans(utterance)
    matches: list[re.Match[str]] = []
    for match in pattern.finditer(utterance):
        matches.append(match)
        if len(matches) > _POOL_MAX_CONTROL_LABEL_MATCHES:
            return ()
    for match in matches:
        if any(left <= match.start() < right for left, right in reason_spans):
            continue
        if _pool_add_label_is_negated(utterance, start=match.start()):
            continue
        right = _pool_add_clause_end(utterance, start=match.end())
        body = utterance[match.end() : right]
        body = re.sub(r"^\s*(?:[::=]|Yes.|Yes)?\s*", "", body)
        body = body.strip()
        if body and not _pool_add_body_is_negated(body):
            bodies.append(body)
    return tuple(bodies)

def _pool_add_labeled_action_types(
    utterance: str,
    *,
    pattern: re.Pattern[str],
) -> tuple[frozenset[str], ...]:
    return tuple(
        frozenset(
            action_type
            for action_type, grounding in _POOL_ACTION_GROUNDING.items()
            if grounding.search(body) is not None
        )
        for body in _pool_add_label_bodies(utterance, pattern)
    )

def _pool_add_action_body_residual(
    body: str,
    action: Mapping[str, Any],
) -> str:
    action_type = str(action.get("type") or "")
    pattern = _POOL_ACTION_GROUNDING.get(action_type)
    spans: list[tuple[int, int]] = []
    if pattern is not None:
        spans.extend(match.span() for match in pattern.finditer(body))
    if action_type in {"limit", "pricing", "segment"}:
        value = action.get("value")
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
            pass
        for candidate in candidates:
            spans.extend(
                match.span()
                for match in re.finditer(re.escape(candidate), body, re.IGNORECASE)
            )
    return _pool_command_residual(_pool_strip_spans(body, spans))

def _pool_add_strategy_type_body_residual(body: str, strategy_type: str) -> str:
    pattern = _POOL_STRATEGY_TYPE_VALUE_GROUNDING.get(strategy_type)
    spans = tuple(match.span() for match in pattern.finditer(body)) if pattern else ()
    return _pool_command_residual(_pool_strip_spans(body, spans))

def _pool_reason_has_active_language(reason: str) -> bool:
    if _POOL_REASON_CANCELLATION_RE.search(reason) is not None:
        return True
    return any(
        pattern.search(reason) is not None
        for pattern in (
            _POOL_ADD_INTENT_RE,
            _POOL_ADD_LIFECYCLE_RE,
            _POOL_ADD_SECOND_OPERATION_RE,
            _POOL_PARTIAL_REORDER_RE,
            _POOL_HEURISTIC_REORDER_RE,
            *_POOL_MUTATION_INTENT_PATTERNS.values(),
        )
    )

def _pool_add_parse_complete_value(body: str) -> object:
    text = body.strip()
    if not text or len(text) > _POOL_MAX_CONTROL_VALUE_CHARS:
        return _POOL_UNPARSEABLE_VALUE
    try:
        return json.loads(
            text,
            object_pairs_hook=_pool_add_unique_json_object,
            parse_constant=_pool_add_reject_json_constant,
            parse_float=Decimal,
        )
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
        pass
    if text.startswith(("[", "{")):
        return _POOL_UNPARSEABLE_VALUE
    if text.casefold() in {
        "nan",
        "+nan",
        "-nan",
        "inf",
        "+inf",
        "-inf",
        "infinity",
        "+infinity",
        "-infinity",
    }:
        return _POOL_UNPARSEABLE_VALUE
    number = re.fullmatch(
        r"(?P<number>[-+]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)"
        r"(?:\.[0-9]+)?)(?P<percent>\s*%)?",
        text,
    )
    if number is not None:
        token = number.group("number").replace(",", "")
        unsigned = token.lstrip("+-")
        integer_part = unsigned.split(".", 1)[0]
        if len(integer_part) > 1 and integer_part.startswith("0"):
            return _POOL_UNPARSEABLE_VALUE
        try:
            value: object = Decimal(token) if "." in token else int(token)
        except (InvalidOperation, ValueError):
            return _POOL_UNPARSEABLE_VALUE
        return value / 100 if number.group("percent") else value
    if text[0] in {"'", '"'} or text[-1] in {"'", '"'}:
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
            return text[1:-1]
        return _POOL_UNPARSEABLE_VALUE
    return unicodedata.normalize("NFC", text)

def _pool_add_unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result

def _pool_add_reject_json_constant(token: str) -> object:
    raise ValueError(f"non-finite JSON constant: {token}")

def _pool_add_values_equal(observed: object, expected: object) -> bool:
    try:
        return _pool_add_comparison_value(observed) == _pool_add_comparison_value(
            expected
        )
    except (InvalidOperation, RecursionError, TypeError, ValueError):
        return False

def _pool_add_comparison_value(value: object) -> object:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return (type(value).__name__, value)
    if isinstance(value, int | float | Decimal):
        numeric = value if isinstance(value, Decimal) else Decimal(str(value))
        if not numeric.is_finite():
            raise ValueError("non-finite numeric value")
        return ("number", numeric)
    if isinstance(value, list):
        return ("array", tuple(_pool_add_comparison_value(item) for item in value))
    if isinstance(value, dict):
        return (
            "object",
            tuple(
                (key, _pool_add_comparison_value(item))
                for key, item in sorted(value.items())
            ),
        )
    raise TypeError("unsupported comparison value")

def _pool_add_body_matches_action_value(
    body: str,
    *,
    action_type: str,
    expected: object,
) -> bool:
    grounding = _POOL_ACTION_GROUNDING.get(action_type)
    if grounding is None:
        return False
    match = grounding.search(body)
    if match is None:
        return False
    value_text = re.sub(
        r"^\s*(?:[::=]|Yes.|Yes)?\s*",
        "",
        body[match.end() :],
    )
    return _pool_add_values_equal(
        _pool_add_parse_complete_value(value_text),
        expected,
    )

def _pool_add_body_matches_complete_value(body: str, expected: object) -> bool:
    return _pool_add_values_equal(
        _pool_add_parse_complete_value(body),
        expected,
    )

def _pool_add_action_payload_controls(
    utterance: str,
    action: Mapping[str, Any],
    *,
    action_bodies: Sequence[str],
    reason_code_label: re.Pattern[str],
    output_value_label: re.Pattern[str],
) -> tuple[str, ...]:
    missing: list[str] = []
    reason_code_bodies = _pool_add_label_bodies(utterance, reason_code_label)
    reason_code_label_count = _pool_add_label_match_count(
        utterance,
        reason_code_label,
    )
    reason_code = action.get("reason_code")
    if bool(reason_code_label_count or reason_code is not None) and (
        reason_code_label_count != len(reason_code_bodies)
        or reason_code_label_count != 1
        or len(reason_code_bodies) != 1
        or not isinstance(reason_code, str)
        or reason_code_bodies[0] != reason_code
    ):
        missing.append("reason_code")
    action_type = str(action.get("type") or "")
    if action_type in {"limit", "pricing", "segment"} and (
        len(action_bodies) != 1
        or not _pool_add_body_matches_action_value(
            action_bodies[0],
            action_type=action_type,
            expected=action.get("value"),
        )
    ):
        missing.append("value")
    output_value = action.get("output_value")
    output_value_bodies = _pool_add_label_bodies(utterance, output_value_label)
    output_value_label_count = _pool_add_label_match_count(
        utterance,
        output_value_label,
    )
    if bool(output_value_label_count or output_value is not None) and (
        output_value_label_count != len(output_value_bodies)
        or output_value_label_count != 1
        or len(output_value_bodies) != 1
        or output_value is None
        or not _pool_add_body_matches_complete_value(
            output_value_bodies[0],
            output_value,
        )
    ):
        missing.append("output_value")
    return tuple(missing)

def _pool_add_placement_modes(
    utterance: str,
) -> tuple[frozenset[str], bool, bool]:
    """Read only an exact label or one of the two reviewed Chinese semantics."""

    reason_spans = _pool_add_reason_spans(utterance)
    label_bodies = _pool_add_label_bodies(
        utterance,
        _POOL_ADD_PLACEMENT_MODE_LABEL_RE,
    )
    label_count = _pool_add_label_match_count(
        utterance,
        _POOL_ADD_PLACEMENT_MODE_LABEL_RE,
    )
    observed: set[str] = set()
    label_values_valid = label_count == len(label_bodies) and label_count <= 1
    for body in label_bodies:
        if body in _POOL_ADD_PLACEMENT_MODES:
            observed.add(body)
            continue
        body_matches = {
            mode
            for mode, pattern in (
                (
                    "before_selected_members",
                    _POOL_ADD_BEFORE_SELECTED_MEMBERS_RE,
                ),
                (
                    "replace_selected_members",
                    _POOL_ADD_REPLACE_SELECTED_MEMBERS_RE,
                ),
            )
            if (
                (match := pattern.fullmatch(body)) is not None
                and match.start() == 0
            )
        }
        if len(body_matches) != 1:
            label_values_valid = False
        observed.update(body_matches)

    phrase_matches: list[tuple[str, re.Match[str]]] = []
    for mode, pattern in (
        ("before_selected_members", _POOL_ADD_BEFORE_SELECTED_MEMBERS_RE),
        ("replace_selected_members", _POOL_ADD_REPLACE_SELECTED_MEMBERS_RE),
    ):
        phrase_matches.extend((mode, match) for match in pattern.finditer(utterance))
    phrase_values_valid = True
    for mode, match in phrase_matches:
        if any(left <= match.start() < right for left, right in reason_spans):
            continue
        if _pool_operation_is_negated(utterance, start=match.start()):
            phrase_values_valid = False
            continue
        observed.add(mode)

    explicit = label_count > 0 or any(
        not any(left <= match.start() < right for left, right in reason_spans)
        for _mode, match in phrase_matches
    )
    return (
        frozenset(observed),
        label_values_valid and phrase_values_valid,
        explicit,
    )

def _pool_add_explicit_reasons(utterance: str) -> tuple[str, ...]:
    return tuple(
        (match.group("zh") or match.group("en")).strip()
        for match in _POOL_ADD_REASON_LABEL_RE.finditer(utterance)
    )

def _ground_strategy_pool_add_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Bind one explicit selection/asset and three independently labeled controls."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]

    if len(utterance) > _POOL_MAX_UTTERANCE_CHARS:
        return _clarification(
            "SingleStrategy Pool The entry command is too long; please keep only onesource ID,"
            "Policy pool type, default action, hit action and optional rationale.",
            code="strategy_pool_add_request_too_large",
            fields=("utterance",),
        )

    has_intent, has_positive_intent = _pool_add_intent_state(utterance)
    if not has_positive_intent:
        code = (
            "strategy_pool_add_intent_negated"
            if has_intent
            else "strategy_pool_add_intent_required"
        )
        return _clarification(
            "I don't know what to say. I don't know what to do.Strategy Pool Into the pool; no negative requests"
            "CreatePool revision.Please state the fullness of the list.source ID.",
            code=code,
            fields=("pool_add_intent",),
        )
    if _pool_add_has_positive_lifecycle_follow_up(utterance):
        return _clarification(
            "This round can only include one clear candidate in reversible.draft Strategy Pool;Adoption, deployment,"
            "Access or commissioning must be initiated separately in a follow-up request.",
            code="strategy_pool_add_single_step_required",
            fields=("next_action",),
        )

    candidate_matches = tuple(_AUTOMATIC_TREE_ASSET_ID_TOKEN_RE.finditer(utterance))
    selection_matches = tuple(
        match
        for pattern in (
            _AUTOMATIC_TREE_LEAF_SELECTION_ID_TOKEN_RE,
            _INTERACTIVE_TREE_FRONTIER_GROUP_SELECTION_ID_TOKEN_RE,
            _INTERACTIVE_TREE_FRONTIER_SELECTION_ID_TOKEN_RE,
            _CROSS_MATRIX_CELL_SELECTION_ID_TOKEN_RE,
            _SCORECARD_CUTOFF_SELECTION_ID_TOKEN_RE,
        )
        for match in pattern.finditer(utterance)
    )
    candidate_ids = frozenset(match.group(0) for match in candidate_matches)
    selection_ids = frozenset(match.group(0) for match in selection_matches)
    source_like_matches = tuple(_POOL_SOURCE_LIKE_TOKEN_RE.finditer(utterance))
    source_like_ids = frozenset(match.group(0) for match in source_like_matches)
    source_prefix_count = _pool_source_prefix_count(utterance)
    canonical_source_ids = candidate_ids | selection_ids
    source_count = len(candidate_matches) + len(selection_matches)
    authorized_spans = _pool_add_authorized_clause_spans(utterance)
    authorized_candidate_matches = tuple(
        match
        for match in candidate_matches
        if any(
            left <= match.start() and match.end() <= right
            for left, right in authorized_spans
        )
    )
    authorized_selection_matches = tuple(
        match
        for match in selection_matches
        if any(
            left <= match.start() and match.end() <= right
            for left, right in authorized_spans
        )
    )
    authorized_source_like_matches = tuple(
        match
        for match in source_like_matches
        if any(
            left <= match.start() and match.end() <= right
            for left, right in authorized_spans
        )
    )
    authorized_canonical_matches = (
        authorized_candidate_matches + authorized_selection_matches
    )
    authorized_source_like_ids = frozenset(
        match.group(0) for match in authorized_source_like_matches
    )
    authorized_canonical_ids = frozenset(
        match.group(0) for match in authorized_canonical_matches
    )
    if (
        source_count != 1
        or len(source_like_matches) != 1
        or source_like_ids != canonical_source_ids
        or source_prefix_count != len(source_like_matches)
        or len(authorized_spans) != 1
        or len(authorized_canonical_matches) != 1
        or len(authorized_source_like_matches) != 1
        or authorized_source_like_ids != authorized_canonical_ids
    ):
        legacy_asset_id = inputs.get("candidate_asset_id")
        if (
            source_count == 0
            and not source_like_matches
            and source_prefix_count == 0
            and isinstance(legacy_asset_id, str)
        ):
            return _clarification(
                "Please specify in the original languageStrategy Pool , completeID andtyped "
                f"action;Can not verify this:{legacy_asset_id}.The platform will not be usedLLM "
                "Guess.ID,Actions, sequences,hash or indicators.",
                code="strategy_pool_controls_not_grounded",
                fields=(legacy_asset_id,),
            )
        return _clarification(
            "Please provide a full text verbatim and only a full textcandidate_asset_id orselection_id;"
            "selection_id It must be.automatic-tree-leaf-selection-,"
            "interactive-tree-frontier-selection-,cross-matrix-cell-selection- "
            "orscorecard-cutoff-selection- "
            "32-bit lowercase hexadecimal characters, which cannot be given both sources.",
            code="strategy_pool_add_source_required",
            fields=("candidate_asset_id", "selection_id"),
        )
    expected_source_field = (
        "selection_id" if authorized_selection_matches else "candidate_asset_id"
    )
    observed_source_id = authorized_canonical_matches[0].group(0)
    if (
        set(inputs) & {"candidate_asset_id", "selection_id"} != {expected_source_field}
        or inputs.get(expected_source_field) != observed_source_id
    ):
        return _clarification(
            "The source of the pool in the draft model is not consistent with the user ' s original language; the platform will not replace, complete or"
            "Guess.candidate_asset_id/selection_id.",
            code="strategy_pool_add_source_not_grounded",
            fields=(expected_source_field,),
        )

    missing_controls: list[str] = []
    observed_strategy_types, strategy_type_labels_valid = _pool_add_strategy_types(
        utterance
    )
    strategy_type_bodies = _pool_add_label_bodies(
        utterance,
        _POOL_ADD_STRATEGY_TYPE_LABEL_RE,
    )
    if (
        not strategy_type_labels_valid
        or observed_strategy_types != {inputs["strategy_type"]}
        or any(
            _pool_add_strategy_type_body_residual(body, inputs["strategy_type"])
            for body in strategy_type_bodies
        )
    ):
        missing_controls.append("strategy_type")
    for field, pattern, reason_code_label, output_value_label in (
        (
            "default_action",
            _POOL_ADD_DEFAULT_ACTION_LABEL_RE,
            _POOL_ADD_DEFAULT_REASON_CODE_LABEL_RE,
            _POOL_ADD_DEFAULT_OUTPUT_VALUE_LABEL_RE,
        ),
        (
            "action",
            _POOL_ADD_HIT_ACTION_LABEL_RE,
            _POOL_ADD_HIT_REASON_CODE_LABEL_RE,
            _POOL_ADD_HIT_OUTPUT_VALUE_LABEL_RE,
        ),
    ):
        action_bodies = _pool_add_label_bodies(utterance, pattern)
        action_label_count = _pool_add_label_match_count(utterance, pattern)
        labeled_types = _pool_add_labeled_action_types(utterance, pattern=pattern)
        expected_type = inputs[field]["type"]
        if (
            action_label_count != 1
            or action_label_count != len(action_bodies)
            or len(labeled_types) != 1
            or labeled_types[0] != {expected_type}
            or (
                len(action_bodies) == 1
                and _pool_add_action_body_residual(action_bodies[0], inputs[field])
            )
        ):
            missing_controls.append(field)
        payload_controls = _pool_add_action_payload_controls(
            utterance,
            inputs[field],
            action_bodies=action_bodies,
            reason_code_label=reason_code_label,
            output_value_label=output_value_label,
        )
        if payload_controls:
            missing_controls.append(field)
    if missing_controls:
        return _clarification(
            "Please indicate the type of policy pool, in a visible manner.Pool Default and hit actions; three are"
            "Independent control. Platforms don't extrapolate from action words.Pool Type, and no two movements."
            "Can not verify this:" + ",".join(dict.fromkeys(missing_controls)) + ".",
            code="strategy_pool_add_controls_not_grounded",
            fields=tuple(dict.fromkeys(missing_controls)),
        )

    observed_placement_modes, placement_values_valid, placement_is_explicit = (
        _pool_add_placement_modes(utterance)
    )
    placement_mode = inputs.get("placement_mode")
    if (
        placement_mode is not None
        and (
            not placement_values_valid
            or observed_placement_modes != {placement_mode}
        )
    ) or (placement_mode is None and placement_is_explicit):
        return _clarification(
            "Optionalplacement_mode Only by \"place\": "
            "before_selected_members/replace_selected_members)Or clear Chinese"
            "(Retention of a member as a recant and placement before a member/ByVoting Substitute members) landing;"
            "There is no speculation when there is a lack, a ambiguity, a conflict or a lack of consistency with the draft.",
            code="strategy_pool_add_placement_mode_not_grounded",
            fields=("placement_mode",),
        )

    explicit_reasons = _pool_add_explicit_reasons(utterance)
    reason = inputs.get("reason")
    if bool(explicit_reasons or reason is not None) and (
        len(explicit_reasons) != 1
        or not isinstance(reason, str)
        or reason != explicit_reasons[0]
    ):
        return _clarification(
            "Optionalreason Need to use \"wells\" with users/Rationale/reason)Visible"
            "Only text is word for word; the model must be omitted when not given in a visible form.",
            code="strategy_pool_add_reason_not_grounded",
            fields=("reason",),
        )
    if isinstance(reason, str) and _pool_reason_has_active_language(reason):
        return _clarification(
            "reason It only describes the passive basis of the operation and cannot carry the pool, delete, modify,"
            "Reorder, revoke or otherwise operate.",
            code="strategy_pool_reason_not_passive",
            fields=("reason",),
        )
    if residual := _pool_add_unconsumed_text(utterance):
        return _clarification(
            "Strategy Pool The entering pool may contain only a clear command sub-rule and known visible control label;"
            "Historical description, recitation, description in consideration, withdrawal statement or other unconsumptionable operation will not be performed.",
            code="strategy_pool_add_command_not_explicit",
            fields=(residual[:80],),
        )
    return result

def _ground_strategy_pool_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    """Prove that every executable Pool control came from the user text."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    workflow = draft.workflow

    if workflow == "strategy_pool_add_candidate":
        return _ground_strategy_pool_add_request(utterance, result)

    if workflow == "strategy_pool_reorder" and (
        _POOL_PARTIAL_REORDER_RE.search(utterance)
        or _POOL_HEURISTIC_REORDER_RE.search(utterance)
    ):
        return _clarification(
            "Strategy Pool Re-aligning must provide the current pool fullrule_id/entry_id (b) Complete, non-duplicate sequence;"
            "It cannot be said that a particular article is placed ahead of it, nor is it automatically sorted by effect, bad rate or recommendation.",
            code="strategy_pool_full_order_required",
            fields=("ordered_ids",),
        )

    missing_controls: list[str] = []
    strategy_type = str(inputs.get("strategy_type") or "")
    strategy_type_pattern = _POOL_STRATEGY_TYPE_GROUNDING.get(strategy_type)
    if strategy_type_pattern is None or strategy_type_pattern.search(utterance) is None:
        missing_controls.append(f"strategy_type {strategy_type or 'unknown'}")
    if workflow in {"strategy_pool_remove_entry", "strategy_pool_set_action"}:
        identifier_name = "rule_id" if "rule_id" in inputs else "entry_id"
        identifier = inputs[identifier_name]
        if not _utterance_contains_token(utterance, identifier):
            missing_controls.append(identifier)
        if workflow == "strategy_pool_set_action":
            missing_controls.extend(
                _ungrounded_pool_actions(utterance, inputs["action"])
            )
    elif workflow == "strategy_pool_reorder":
        ordered_ids = inputs["ordered_ids"]
        positions = [utterance.find(identifier) for identifier in ordered_ids]
        missing_controls.extend(
            identifier
            for identifier, position in zip(ordered_ids, positions, strict=True)
            if position < 0
        )
        observed_positions = [position for position in positions if position >= 0]
        if observed_positions != sorted(observed_positions):
            missing_controls.append("Full order in user original words")
    elif workflow == "strategy_pool_compile":
        pass

    reason = inputs.get("reason")
    if isinstance(reason, str) and reason.casefold() not in utterance.casefold():
        missing_controls.append(reason)

    if missing_controls:
        rendered = ",".join(dict.fromkeys(missing_controls))
        return _clarification(
            "Please specify in the original languageStrategy Pool , completeID andtyped action;"
            f"Can not verify this:{rendered}.The platform will not be usedLLM Guess.ID,Actions, sequences,hash or indicators.",
            code="strategy_pool_controls_not_grounded",
            fields=tuple(dict.fromkeys(missing_controls)),
        )
    if isinstance(reason, str) and _pool_reason_has_active_language(reason):
        return _clarification(
            "reason It only describes the passive basis of the operation and cannot carry the pool, delete, modify,"
            "Reorder, revoke or otherwise operate.",
            code="strategy_pool_reason_not_passive",
            fields=("reason",),
        )
    if workflow in _POOL_MUTATION_INTENT_PATTERNS and not (
        _pool_mutation_has_positive_intent(utterance, workflow, inputs)
    ):
        return _clarification(
            "The original words do not explicitly authorize a positive execution on the current round.Strategy Pool amending;negative,"
            "Question, history description, failure, revocation or other unconsumption does not create newPool revision.",
            code="strategy_pool_mutation_intent_required",
            fields=("pool_mutation_intent",),
        )
    return result
