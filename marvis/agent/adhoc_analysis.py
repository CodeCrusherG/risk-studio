"""S6 ad-hoc natural-language slice/aggregate turn wiring.

Ad-hoc "Question Number" ([Look at it through the channels. 5 Month-mortem]) has no workflow template: the LLM only
parses the utterance into a *structured* SliceSpec (it never computes a number —
INV-1), the platform validates every column against the dataset profile whitelist
and the op against the fixed operator set, and only after a Validation door. (a plain-
Chinese echo of exactly what will be grouped/measured/filtered) does the single-
step slice_aggregate plan run.

Parse failure or any hallucinated column produces a Chinese clarification question
(never a guess). The question-intent detector is deliberately conservative: a turn
that does not clearly read as a data question defaults back to the normal flow
(the caller keeps its original branch), so this never hijacks an unrelated turn.
"""

from __future__ import annotations

from dataclasses import dataclass
import json

from marvis.llm_prompts import SLICE_SPEC_SYS

# The whitelisted aggregate operators, mirrored from
# marvis.packs.data_ops.tools._metric_expr so the platform rejects a hallucinated
# op here (before ever building a plan) rather than deep inside the tool.
_ALLOWED_OPS = frozenset(
    {"count", "sum", "mean", "min", "max", "bad_rate", "approval_rate", "distinct"}
)
_OPS_NEEDING_COL = frozenset(
    {"sum", "mean", "min", "max", "bad_rate", "approval_rate", "distinct"}
)
_ALLOWED_FILTER_OPS = frozenset({"==", "!=", ">", ">=", "<", "<=", "in", "between"})
_MAX_GROUP_BY = 3
_MAX_FILTERS = 8

# Conservative Chinese/English question-intent Quoting words. A turn matches only when it
# reads as a data question; anything else defaults to the caller's original branch
# (The purpose of the defense is to take the same path.).
_QUESTION_HINTS = (
    "Take a look.",
    "Look at this.",
    "Statistics",
    "Distribution",
    "How much?",
    "Bad rate",
    "Pass rate",
    "Percentage",
    "Average",
    "Press",
    "Each",
    "Group",
    "count",
    "average",
    "distribution",
    "how many",
)


def detect_question_intent(utterance: str | None) -> bool:
    """True when the utterance clearly reads as an ad-hoc data question. Kept
    conservative on purpose: a non-match means the caller keeps its normal flow."""
    if not utterance:
        return False
    text = str(utterance).strip().lower()
    if not text:
        return False
    return any(hint.lower() in text for hint in _QUESTION_HINTS)


@dataclass(frozen=True)
class SliceMetric:
    op: str
    col: str | None = None

    def as_dict(self) -> dict:
        payload: dict = {"op": self.op}
        if self.col is not None:
            payload["col"] = self.col
        return payload


@dataclass(frozen=True)
class SliceFilter:
    col: str
    op: str
    value: object

    def as_dict(self) -> dict:
        return {"col": self.col, "op": self.op, "value": self.value}


@dataclass(frozen=True)
class SliceSpec:
    group_by: tuple[str, ...] = ()
    metrics: tuple[SliceMetric, ...] = ()
    filters: tuple[SliceFilter, ...] = ()
    month_col: str | None = None
    months: tuple[str, ...] = ()
    sort_by: str | None = None

    def tool_inputs(self, dataset_id: str) -> dict:
        """The slice_aggregate tool inputs for a confirmed spec (single-step plan)."""
        inputs: dict = {
            "dataset_id": dataset_id,
            "metrics": [metric.as_dict() for metric in self.metrics],
        }
        if self.group_by:
            inputs["group_by"] = list(self.group_by)
        if self.filters:
            inputs["filters"] = [f.as_dict() for f in self.filters]
        if self.month_col and self.months:
            inputs["month_col"] = self.month_col
            inputs["months"] = list(self.months)
        if self.sort_by:
            inputs["sort_by"] = self.sort_by
        return inputs


@dataclass(frozen=True)
class SliceSpecResult:
    """Either a validated spec that still needs the Validation door. (``clarify`` is None),
    or a Chinese clarification question (``spec`` is None)."""

    spec: SliceSpec | None = None
    clarify: str | None = None
    confirmation_text: str | None = None

    @property
    def needs_clarification(self) -> bool:
        return self.spec is None


def _clarify(message: str) -> SliceSpecResult:
    return SliceSpecResult(spec=None, clarify=message, confirmation_text=None)


def build_slice_spec_from_utterance(
    utterance: str,
    dataset_profile,
    llm,
    *,
    caller: str = "adhoc_analysis",
) -> SliceSpecResult:
    """Parse an utterance into a validated SliceSpec + confirmation text, or a
    Chinese clarification. ``dataset_profile`` is any iterable of column names (the
    whitelist). ``llm`` exposes ``.complete(system_prompt=, user_prompt=, ...)`` and
    returns a JSON string; the platform (not the LLM) validates columns/ops."""
    allowed_columns = _column_whitelist(dataset_profile)
    if not allowed_columns:
        return _clarify("No columns available for the current data set,Could not close temporary folder: s.")

    raw = _invoke_llm(utterance, allowed_columns, llm, caller=caller)
    if raw is None:
        return _clarify("I dont understand that.,Please, change your mind.,Or indicate which rows to group.,What are you looking at?.")
    parsed = _parse_json_object(raw)
    if parsed is None:
        return _clarify("I dont understand that.,Please, change your mind.,Or indicate which rows to group.,What are you looking at?.")
    if isinstance(parsed.get("clarify"), str) and parsed["clarify"].strip():
        return _clarify(parsed["clarify"].strip())

    return validate_slice_spec(parsed, allowed_columns)


def validate_slice_spec(parsed: dict, allowed_columns) -> SliceSpecResult:
    """Platform-side validation of an LLM-produced spec against the column
    whitelist + fixed operator set. Any unknown column / bad op -> a Chinese
    clarification (never a guess, never a silent drop)."""
    whitelist = _column_whitelist(allowed_columns)

    group_by = [str(col) for col in _as_list(parsed.get("group_by"))]
    if len(group_by) > _MAX_GROUP_BY:
        return _clarify(f"Support maximum press {_MAX_GROUP_BY} Column Group,Reduce the group dimensions, please..")
    for col in group_by:
        if col not in whitelist:
            return _clarify(f"No columns found[{col}],Please select the grouping column from the existing column.")

    raw_metrics = _as_list(parsed.get("metrics"))
    if not raw_metrics:
        return _clarify("No indicators identified for statistics,Please indicate the number.,The bad rate is equal to the average..")
    metrics: list[SliceMetric] = []
    for metric in raw_metrics:
        if not isinstance(metric, dict):
            return _clarify("Indicator format unrecognized,Please rephrase the indicators to be counted..")
        op = str(metric.get("op") or "")
        if op not in _ALLOWED_OPS:
            return _clarify(f"Counts are not supported for the time being[{op}],Available:Number/Peace./Mean/Min/Max/Bad rate/Pass rate/Go to the count again..")
        col = _optional_str(metric.get("col"))
        if op in _OPS_NEEDING_COL:
            if not col:
                return _clarify(f"Count![{op}]A column needs to be specified,Please indicate which column is to be counted..")
            if col not in whitelist:
                return _clarify(f"No columns found[{col}],Please select the columns from the existing ones to be counted.")
        metrics.append(SliceMetric(op=op, col=col if op in _OPS_NEEDING_COL else None))

    raw_filters = _as_list(parsed.get("filters"))
    if len(raw_filters) > _MAX_FILTERS:
        return _clarify(f"Most Support {_MAX_FILTERS} Filter Conditions,Please streamline the filter..")
    filters: list[SliceFilter] = []
    for f in raw_filters:
        if not isinstance(f, dict):
            return _clarify("Filter Condition Format Unrecognized,Please re-describe the filter..")
        col = _optional_str(f.get("col"))
        op = str(f.get("op") or "")
        if not col or col not in whitelist:
            return _clarify(f"Filter used columns[{col}]Cannot initialise Evolutions mail component.,Please select from the existing column.")
        if op not in _ALLOWED_FILTER_OPS:
            return _clarify(f"Disable filter comparator[{op}].")
        filters.append(SliceFilter(col=col, op=op, value=f.get("value")))

    month_col = _optional_str(parsed.get("month_col"))
    months = tuple(str(month) for month in _as_list(parsed.get("months")))
    if month_col and month_col not in whitelist:
        return _clarify(f"No timebar found[{month_col}],Please indicate which line to sift for the month..")
    if month_col and not months:
        return _clarify("Timebar specified but no month range,Please indicate the months to be observed..")

    sort_by = _optional_str(parsed.get("sort_by"))
    metric_labels = {_metric_label(m.op, m.col) for m in metrics}
    if sort_by and sort_by not in group_by and sort_by not in metric_labels:
        return _clarify(f"Sort by[{sort_by}]Must be a cluster column or selected indicator.")

    spec = SliceSpec(
        group_by=tuple(group_by),
        metrics=tuple(metrics),
        filters=tuple(filters),
        month_col=month_col if (month_col and months) else None,
        months=months if (month_col and months) else (),
        sort_by=sort_by,
    )
    return SliceSpecResult(
        spec=spec,
        clarify=None,
        confirmation_text=slice_spec_confirmation_text(spec),
    )


def slice_spec_confirmation_text(spec: SliceSpec) -> str:
    """The Validation door. copy: a plain-Chinese echo of exactly what will run, so the
    user confirms thecaliber before any aggregate executes (Make sure the door is clear.)."""
    group_text = ",".join(spec.group_by) if spec.group_by else "All samples"
    metric_text = ",".join(_metric_display(m) for m in spec.metrics)
    parts = [f"will press〔{group_text}〕Statistics〔{metric_text}〕"]
    if spec.month_col and spec.months:
        parts.append(f",Time frame〔{','.join(spec.months)}〕")
    if spec.filters:
        filter_text = ",".join(f"{f.col}{f.op}{f.value}" for f in spec.filters)
        parts.append(f",Filter〔{filter_text}〕")
    parts.append(",Confirm.?")
    return "".join(parts)


_METRIC_DISPLAY = {
    "count": "Number",
    "sum": "Peace.",
    "mean": "Mean",
    "min": "Min",
    "max": "Maximum",
    "bad_rate": "Bad rate",
    "approval_rate": "Pass rate",
    "distinct": "Go to the count again.",
}


def _metric_display(metric: SliceMetric) -> str:
    label = _METRIC_DISPLAY.get(metric.op, metric.op)
    return label if not metric.col else f"{metric.col} Its...{label}"


def _metric_label(op: str, col: str | None) -> str:
    # Mirror marvis.packs.data_ops.tools._metric_label so sort_by can name a
    # metric output label consistently across the platform boundary.
    return op if op == "count" or not col else f"{op}_{col}"


def _invoke_llm(utterance: str, allowed_columns, llm, *, caller: str) -> str | None:
    user_prompt = (
        f"Available white lists for data sets:{list(allowed_columns)}\n"
        f"User problems:{utterance}\n"
        "Please structure the output. JSON Specifications(or clarify)."
    )
    try:
        return llm.complete(
            system_prompt=SLICE_SPEC_SYS.text,
            user_prompt=user_prompt,
            temperature=0.0,
            stream=False,
            caller=caller,
            prompt_name=SLICE_SPEC_SYS.name,
            prompt_version=SLICE_SPEC_SYS.version,
        )
    except Exception:
        return None


def _parse_json_object(raw: str) -> dict | None:
    text = str(raw or "").strip()
    if not text:
        return None
    # Tolerate a fenced ```json block or leading prose before the JSON object.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _column_whitelist(dataset_profile) -> tuple[str, ...]:
    if dataset_profile is None:
        return ()
    columns: list[str] = []
    for column in dataset_profile:
        name = str(column)
        if name and name not in columns:
            columns.append(name)
    return tuple(columns)


def _as_list(value) -> list:
    return list(value) if isinstance(value, (list, tuple)) else []


def _optional_str(value) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


__all__ = [
    "SliceFilter",
    "SliceMetric",
    "SliceSpec",
    "SliceSpecResult",
    "build_slice_spec_from_utterance",
    "detect_question_intent",
    "slice_spec_confirmation_text",
    "validate_slice_spec",
]
