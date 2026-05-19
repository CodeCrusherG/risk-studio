"""strategy_report driver-turn handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import _StrategyV2EvidenceSetupError

_STRATEGY_REPORT_POOL_TYPE_PATTERNS = {
    "approval": re.compile(
        r"(?:Approval|Access)|(?<![A-Za-z0-9_])approval(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "reject": re.compile(
        r"Reject|(?<![A-Za-z0-9_])reject(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "limit": re.compile(
        r"Amount|(?<![A-Za-z0-9_])limit(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "pricing": re.compile(
        r"Pricing|Interest rate|(?<![A-Za-z0-9_])pricing(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
    "segmentation": re.compile(
        r"Group|Layer|The guests.|"
        r"(?<![A-Za-z0-9_])segmentation(?![A-Za-z0-9_])",
        re.IGNORECASE,
    ),
}

_STRATEGY_REPORT_POOL_COMMAND_RE = re.compile(
    r"(?:Generate|Create|Production|Preparation|Form|One.|Here we go.|Give it to me.|Export|Build)"
    r"[^;;..!??\n]{0,80}(?:Report|Report)|"
    r"(?<![A-Za-z0-9_])(?:generate|create|build|produce|prepare|render|export)"
    r"[^;.!?\n]{0,80}\breport(?:\s+bundle)?\b",
    re.IGNORECASE,
)

_STRATEGY_REPORT_POOL_TITLE_RE = re.compile(
    r"(?:Title of report|Title|report\s+title|title)\s*"
    r"(?:Yes|Yes.|Please.|is|=|:|:)\s*"
    r"(?:[(\"'<][^)\"'>\n]{1,200}[)\"'>]|"
    r"[^,,;;..!??\n]{1,200})",
    re.IGNORECASE,
)

_STRATEGY_REPORT_POOL_SELECTOR_RE = re.compile(
    r"(?:Selection|Select|Use|Adopt|Targeted|Assign|Press|Based on|Change|I'll use it.|It's for the use.|It's...|"
    r"(?:Pool|Policy)\s*Type\s*(?:Yes|Yes.|=|:|:)|"
    r"(?<![A-Za-z0-9_])(?:select|choose|use|using|for|on|but|instead)"
    r"(?![A-Za-z0-9_]))\s*$",
    re.IGNORECASE,
)

_STRATEGY_REPORT_POOL_TYPE_NEGATION_RE = re.compile(
    r"(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Not yet.|Ban|Exclude|Remove|Not|No, it's not.|Not really.|"
    r"Do Not Use|No choice.|Select No)\s*(?:(?:Selection|Select|Use|Adopt|Targeted|Assign)\s*)?"
    r"[^,,;;..!??\n]{0,16}$|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|dont|not|never|without|exclude)"
    r"[^,;.!?\n]{0,20}$",
    re.IGNORECASE,
)

_STRATEGY_REPORT_POOL_HISTORY_RE = re.compile(
    r"(?:Yesterday.|Before|Before|Go on.|Last time.|Once.|History|Archived|Generated)|"
    r"(?<![A-Za-z0-9_])(?:yesterday|previously|earlier|historical|"
    r"last\s+time|archived|already\s+generated)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT = 64

_STRATEGY_REPORT_VOTING_SEARCH_REPLAY_LIMIT = (
    _STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT
)

_STRATEGY_REPORT_CROSS_SEARCH_REPLAY_LIMIT = (
    _STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT
)

_STRATEGY_REPORT_POOL_STABILITY_REPLAY_LIMIT = (
    _STRATEGY_REPORT_EVIDENCE_REPLAY_LIMIT
)

def _raise_corrupt_report_optional(
    label: str,
    *,
    cause: Exception | None = None,
) -> None:
    error = _StrategyV2EvidenceSetupError(
        "strategy_report_bundle_v2_optional_evidence_invalid",
        f"Latest{label} artifact Full authentication was not achieved; the platform did not retreat to old evidence.",
    )
    if cause is None:
        raise error
    raise error from cause
