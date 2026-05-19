"""scorecard request-compiler handlers (executed into the package namespace by __init__.py)."""
from __future__ import annotations
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
import json
import math
import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # names defined by sibling lanes; merged into one namespace at runtime
    from . import StandardWorkflowRequestDraft
    from . import StrategyRequestCompilation
    from . import _CANDIDATE_STABILITY_ACTION_RE
    from . import _CANDIDATE_STABILITY_ASSET_ID_TOKEN_RE
    from . import _CANDIDATE_STABILITY_MEASUREMENT_RE
    from . import _CANDIDATE_STABILITY_NOT_AUTHORIZED_RE
    from . import _CANDIDATE_STABILITY_PLATFORM_CONTROL_RE
    from . import _CANDIDATE_STABILITY_POOL_ENTRY_ID_TOKEN_RE
    from . import _CANDIDATE_STABILITY_SECOND_OPERATION_RE
    from . import _CANDIDATE_STABILITY_SUBJECT_RE
    from . import _POOL_STRATEGY_TYPE_GROUNDING
    from . import _automatic_tree_span_is_negated
    from . import _clarification
    from . import _cross_mention_is_within
    from . import _voting_strategy_type_mentions

_SCORECARD_SUBJECT_RE = re.compile(
    r"(?:Scorecard|Scorecard).{0,20}"
    r"(?:Split Belt|Rating tape|Slotting|Trail|Subband|Split\s*\d+\s*Trail|cutoff|Passeline)|"
    r"(?:Split Belt|Rating tape|Slotting|Trail|Subband|cutoff|Passeline)"
    r".{0,20}(?:Scorecard|Scorecard)",
    re.IGNORECASE,
)

_SCORECARD_BUILD_ACTION_RE = re.compile(
    r"(?:Build|Generate|Create|Calculate|Design|Physicalization|Split|Division(?:Yes|Done.)?)|"
    r"(?<![A-Za-z0-9_])(?:build|create|generate|compute|design|materialize)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_SCORECARD_SELECTION_ACTION_RE = re.compile(
    r"(?:Selection|Select|Physicalization)|"
    r"(?<![A-Za-z0-9_])(?:select|choose|materialize)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_SCORECARD_NOT_AUTHORIZED_RE = re.compile(
    r"[??]|(?:Don't.|No, I'm fine.|No need.|Not yet.|Not yet.|Cancel|Undo|Ban|"
    r"Can you...|Can I?|Is it possible?|Is that okay?|Can you...|How's that?|What?|Assumptions|Suppose...|If|"
    r"Later|The future.|In the future|Later.|Before|Before|Go on.|Last time.)|"
    r"(?<![A-Za-z0-9_])(?:do\s+not|don't|never|cancel|can\s+you|"
    r"could\s+you|how\s+to|what\s+if|later|previously|"
    r"in\s+the\s+future)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_SCORECARD_HEURISTIC_SELECTION_RE = re.compile(
    r"(?:I'd better.|Best|Best|Worst|Risk highest|The worst rate of bad.|Automatic(?:Selection|Selection|Recommendations)|"
    r"Press(?:Bad rate|Pass rate|KS|AUC|Lift|Proceeds|Profit).{0,16}(?:Selection|Recommendations))|"
    r"(?<![A-Za-z0-9_])(?:best|worst|top[- ]?\d*|highest[- ]risk|"
    r"automatically\s+(?:select|choose|recommend)|recommend)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_SCORECARD_SECOND_OPERATION_RE = re.compile(
    r"(?:Add|Put it in.|Writing|Inclusion)[^,,;;.\n]{0,20}(?:Policy pool|Rule pool|Pool)|"
    r"(?:Into the pool.|Apply|Write back|Back up.|Accepted|Adopt|Deployment|Online.|Production|Generate Report|Report.)|"
    r"(?<![A-Za-z0-9_])(?:add\s+to\s+(?:the\s+)?(?:strategy\s+)?pool|"
    r"apply|write[-\s]*back|adopt|deploy|go[-\s]?live|"
    r"generate\s+(?:a\s+)?report)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_SCORECARD_BIN_COUNT_RE = re.compile(
    r"(?:Equivalent\s*)?(?P<count>\d+)\s*(?:Trail|- Yeah.|bands?)",
    re.IGNORECASE,
)

_SCORECARD_RAW_PD_EDGES_RE = re.compile(
    r"(?:raw\s*pd|Original\s*PD|Original bad debt probability)"
    r"(?:\s*(?:Subband)?(?:Border|Point|edges?))?\s*(?:Yes|Yes.|=|:|:)?\s*"
    r"[\[[](?P<body>[^\]]]{1,500})[\]]]",
    re.IGNORECASE,
)

_SCORECARD_SELECTION_REASON_RE = re.compile(
    r"(?:Reason for selection|Rationale|Reason|Annotations|reason)\s*(?:Yes|Yes.|=|:|:)\s*"
    r"(?P<reason>[^;;..!??\n]{1,500})",
    re.IGNORECASE,
)

_SCORECARD_BAND_ASSET_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])scorecard-band-asset-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_SCORECARD_CUTOFF_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])scorecard-cutoff-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

_SCORECARD_CUTOFF_SELECTION_ID_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])scorecard-cutoff-selection-[0-9a-f]{32}"
    r"(?![A-Za-z0-9_-])"
)

def _explicit_manual_breakpoint_bindings(
    utterance: str,
    *,
    whitelist: Sequence[str],
    command_span: tuple[int, int] | None = None,
) -> tuple[dict[str, list[float]], bool]:
    """Parse only explicit ``feature manual Point[..]`` controls."""

    bindings: dict[str, list[float]] = {}
    ambiguous = False
    for column in sorted(whitelist, key=len, reverse=True):
        token = (
            rf"(?<![A-Za-z0-9_]){re.escape(column)}"
            rf"(?![A-Za-z0-9_])"
        )
        pattern = re.compile(
            rf"{token}\s*(?:Axis\s*)?(?:(?:Use|Use|Press|Adopt)\s*)?"
            rf"(?:Manual|Manual|manual)\s*(?:Box\s*)?"
            rf"(?:Point|Breakpoints|breakpoints?)\s*(?:(?:Yes|Yes.)\s*)?"
            rf"(?:=|:|:)?\s*\[(?P<points>[^\[\]]*)\]",
            re.IGNORECASE,
        )
        for match in pattern.finditer(utterance):
            if command_span is not None and not _cross_mention_is_within(
                match.start(),
                match.end(),
                command_span,
            ):
                ambiguous = True
                continue
            if _automatic_tree_span_is_negated(
                utterance,
                start=match.start(),
                end=match.end(),
            ):
                ambiguous = True
                continue
            raw = (
                "["
                + match.group("points").replace(",", ",").replace(",", ",")
                + "]"
            )
            try:
                values = json.loads(raw)
            except json.JSONDecodeError:
                ambiguous = True
                continue
            if (
                not isinstance(values, list)
                or not 1 <= len(values) <= 19
                or any(
                    isinstance(item, bool)
                    or not isinstance(item, int | float)
                    or (
                        isinstance(item, int)
                        and abs(item) > 2**53 - 1
                    )
                    for item in values
                )
            ):
                ambiguous = True
                continue
            points = [float(item) for item in values]
            if (
                any(not math.isfinite(item) for item in points)
                or any(
                    left >= right
                    for left, right in zip(points, points[1:], strict=False)
                )
                or column in bindings
            ):
                ambiguous = True
                continue
            bindings[column] = points
    return bindings, ambiguous

def _ground_univariate_candidate_analysis(
    utterance: str,
    result: StrategyRequestCompilation,
    *,
    whitelist: tuple[str, ...],
) -> StrategyRequestCompilation:
    """Keep user-owned manual cutpoints byte-for-byte grounded in this turn."""

    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    observed, ambiguous = _explicit_manual_breakpoint_bindings(
        utterance,
        whitelist=whitelist,
    )
    expected = inputs.get("manual_breakpoints", {})
    if not ambiguous and observed == expected:
        return result
    return _clarification(
        "manual The box shall be named by \"field\"manual Point[Value 1, Value 2])Quite clearly"
        "Strictly incremental cut points for each field; the platform does not allow models to be supplemented, sequenced or other numbers to be cut points.",
        code="univariate_manual_breakpoints_not_grounded",
        fields=("manual_breakpoints",),
    )

def utterance_targets_candidate_monthly_stability(utterance: str) -> bool:
    """Reserve candidate/Pool-entry monthly PSI for its governed Workflow."""

    return bool(
        _CANDIDATE_STABILITY_SUBJECT_RE.search(utterance)
        and _CANDIDATE_STABILITY_MEASUREMENT_RE.search(utterance)
    )

def utterance_targets_scorecard_cutoff_selection(utterance: str) -> bool:
    """Reserve explicit scorecard cutoff materialization for its pointer Workflow."""

    scorecard_context = bool(
        _SCORECARD_SUBJECT_RE.search(utterance)
        or _SCORECARD_BAND_ASSET_ID_TOKEN_RE.search(utterance)
    )
    return bool(
        scorecard_context
        and re.search(r"(?:cutoff|Passeline|Fraction Line)", utterance, re.IGNORECASE)
        and _SCORECARD_SELECTION_ACTION_RE.search(utterance)
    )

def utterance_targets_scorecard_band_build(utterance: str) -> bool:
    """Reserve complete scorecard-band generation without cutoff selection."""

    return bool(
        not utterance_targets_scorecard_cutoff_selection(utterance)
        and _SCORECARD_SUBJECT_RE.search(utterance)
        and _SCORECARD_BUILD_ACTION_RE.search(utterance)
    )

def _scorecard_raw_pd_edge_mentions(
    utterance: str,
) -> tuple[tuple[float, ...], ...] | None:
    """Parse only explicitly labelled raw-PD arrays; malformed arrays fail closed."""

    mentions: list[tuple[float, ...]] = []
    for match in _SCORECARD_RAW_PD_EDGES_RE.finditer(utterance):
        tokens = [
            token.strip()
            for token in re.split(r"[,,]", match.group("body"))
        ]
        if not tokens or any(not token for token in tokens):
            return None
        values: list[float] = []
        for token in tokens:
            try:
                value = float(Decimal(token))
            except (InvalidOperation, OverflowError, ValueError):
                return None
            if not math.isfinite(value):
                return None
            values.append(value)
        mentions.append(tuple(values))
    return tuple(mentions)

def _ground_scorecard_band_build(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if _SCORECARD_HEURISTIC_SELECTION_RE.search(
        utterance
    ) or _SCORECARD_SECOND_OPERATION_RE.search(utterance):
        return _clarification(
            "Scorecard fraction belt construction must be a single step; Autoselect/Rankcutoff,"
            "The entry, application, return, reporting, adoption or deployment must be broken down into subsequent requests.",
            code="scorecard_band_single_step_required",
            fields=("workflow",),
        )
    if (
        _SCORECARD_NOT_AUTHORIZED_RE.search(utterance)
        or _SCORECARD_BUILD_ACTION_RE.search(utterance) is None
    ):
        return _clarification(
            "Please use the current wheel, positive command to explicitly require constructionScorecard Full fraction strip.",
            code="scorecard_band_positive_command_required",
            fields=("build_intent",),
        )
    bin_counts = tuple(
        int(match.group("count"))
        for match in _SCORECARD_BIN_COUNT_RE.finditer(utterance)
    )
    raw_edges = _scorecard_raw_pd_edge_mentions(utterance)
    expected_count = inputs.get("bin_count")
    expected_edges = inputs.get("raw_pd_band_edges")
    if (
        raw_edges is None
        or (expected_count is not None and bin_counts != (expected_count,))
        or (expected_count is None and bin_counts)
        or (
            expected_edges is not None
            and raw_edges != (tuple(float(value) for value in expected_edges),)
        )
        or (expected_edges is None and raw_edges)
    ):
        return _clarification(
            "bin_count orraw_pd_band_edges Only the only visible value of the round can be used word for word;"
            "It's not available either.Tool Default equal frequency 10 slots.",
            code="scorecard_band_controls_not_grounded",
            fields=("bin_count", "raw_pd_band_edges"),
        )
    return result

def _ground_scorecard_cutoff_selection(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    assets = tuple(
        match.group(0)
        for match in _SCORECARD_BAND_ASSET_ID_TOKEN_RE.finditer(utterance)
    )
    cutoffs = tuple(
        match.group(0)
        for match in _SCORECARD_CUTOFF_ID_TOKEN_RE.finditer(utterance)
    )
    if len(assets) != 1 or len(cutoffs) != 1:
        return _clarification(
            "Scorecard cutoff Selection must be provided word for word and only complete"
            "scorecard-band-asset ID With a completescorecard-cutoff ID;"
            "The selection cannot be automatic on the basis of the best, bad, ranking or recommendation.",
            code="scorecard_cutoff_explicit_id_required",
            fields=("asset_id", "cutoff_id"),
        )
    if _SCORECARD_SECOND_OPERATION_RE.search(utterance):
        return _clarification(
            "Scorecard cutoff The selection must be a separate step; enter the pool, apply, write back,"
            "Reporting, adoption or deployment must be split into follow-up requests.",
            code="scorecard_cutoff_single_step_required",
            fields=("workflow",),
        )
    if (
        _SCORECARD_NOT_AUTHORIZED_RE.search(utterance)
        or _SCORECARD_SELECTION_ACTION_RE.search(utterance) is None
    ):
        return _clarification(
            "Please select one clearly using the current round, positive commandScorecard cutoff.",
            code="scorecard_cutoff_positive_command_required",
            fields=("selection_intent",),
        )
    if (
        _SCORECARD_HEURISTIC_SELECTION_RE.search(utterance)
        or assets != (inputs["asset_id"],)
        or cutoffs != (inputs["cutoff_id"],)
    ):
        return _clarification(
            "Scorecard asset/cutoff It must be the only completeness of the user's original language.pointer "
            "Word by word; Platform does not replace, complete, rank or recommend.",
            code="scorecard_cutoff_controls_not_grounded",
            fields=("asset_id", "cutoff_id"),
        )
    reasons = tuple(
        match.group("reason").strip()
        for match in _SCORECARD_SELECTION_REASON_RE.finditer(utterance)
    )
    reason = inputs.get("reason")
    if bool(reasons or reason is not None) and (
        len(reasons) != 1
        or not isinstance(reason, str)
        or reasons[0] != reason
    ):
        return _clarification(
            "Optionalreason It must be used by the user to \"justify the selection\"/Rationale/Reason/Note"
            "Only text is consistent word for word; when not indicated, it must be omitted.",
            code="scorecard_cutoff_reason_not_grounded",
            fields=("reason",),
        )
    return result

def _ground_candidate_monthly_stability_request(
    utterance: str,
    result: StrategyRequestCompilation,
) -> StrategyRequestCompilation:
    draft = result.draft
    assert isinstance(draft, StandardWorkflowRequestDraft)
    inputs = draft.to_dict()["workflow_inputs"]
    if not utterance_targets_candidate_monthly_stability(utterance):
        return _clarification(
            "The original words are not clear./Pool Entry and month-by-month stability orPSI;"
            "Ben.Workflow No substitute.Pool Impact, generic surveillance or other candidate operations.",
            code="candidate_monthly_stability_measurement_required",
            fields=("measurement_intent",),
        )
    if (
        _CANDIDATE_STABILITY_NOT_AUTHORIZED_RE.search(utterance)
        or _CANDIDATE_STABILITY_ACTION_RE.search(utterance) is None
    ):
        return _clarification(
            "Please use the current round, positive command, to explicitly require the calculation of an asset with a single variable."
            "Or currentStrategy Pool Monthly stability of an item/PSI.",
            code="candidate_monthly_stability_positive_command_required",
            fields=("measurement_intent",),
        )
    if _CANDIDATE_STABILITY_SECOND_OPERATION_RE.search(utterance):
        return _clarification(
            "The candidate must be the only one in the current cycle; enter, delete, reorder, compile,"
            "Write back, report, adopt or deploy, please untrace as a follow-up request.",
            code="candidate_monthly_stability_single_operation_required",
            fields=("workflow",),
        )
    if _CANDIDATE_STABILITY_PLATFORM_CONTROL_RE.search(utterance):
        return _clarification(
            "The candidate is stable on a month-by-month basis.artifact/hash,Pool revision,Activitiesworkspace,"
            "SampleDesign The month field can only be restored by the platform, not specified in the request.",
            code="candidate_monthly_stability_platform_binding_forbidden",
            fields=("platform_binding",),
        )

    asset_ids = tuple(
        match.group(0)
        for match in _CANDIDATE_STABILITY_ASSET_ID_TOKEN_RE.finditer(utterance)
    )
    entry_ids = tuple(
        match.group(0)
        for match in _CANDIDATE_STABILITY_POOL_ENTRY_ID_TOKEN_RE.finditer(
            utterance
        )
    )
    if "asset_id" in inputs:
        expected = str(inputs["asset_id"])
        if (
            len(asset_ids) != 1
            or asset_ids[0] != expected
            or entry_ids
        ):
            return _clarification(
                "Please provide a full single variable verbatim and only one full variablecandidate-asset ID;"
                "Proximity, missing, multipleID Or it's happening at the same time.Pool entry The platform doesn't guess.",
                code="candidate_monthly_stability_source_not_grounded",
                fields=("asset_id",),
            )
        return result

    expected_entry = str(inputs.get("entry_id") or "")
    strategy_type = str(inputs.get("strategy_type") or "")
    mentioned_types = {
        item[0] for item in _voting_strategy_type_mentions(utterance)
    }
    type_pattern = _POOL_STRATEGY_TYPE_GROUNDING.get(strategy_type)
    if (
        asset_ids
        or len(entry_ids) != 1
        or entry_ids[0] != expected_entry
        or type_pattern is None
        or type_pattern.search(utterance) is None
        or mentioned_types != {strategy_type}
    ):
        return _clarification(
            "Pool The item-month stability needs to be clear and provided only in the same requestStrategy Pool "
            "Type with a completepool-entry ID;Platforms do not come from action, history or otherPool Guess.",
            code="candidate_monthly_stability_source_not_grounded",
            fields=("strategy_type", "entry_id"),
        )
    return result
