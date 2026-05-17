"""Deterministic natural-language routing for report-ready dataset analysis.

The parser only selects analysis sections and already-known columns.  It never
computes a metric and never invents a column: all numbers remain owned by the
``data_ops.profile_dataset`` tool.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re


_SECTION_ORDER = (
    "overview",
    "target",
    "missing",
    "distribution",
    "correlation",
)
_GENERAL_HINTS = (
    "- Im gonna analyze this sample.",
    "Analyse the current sample",
    "Sample analysis",
    "Data overview",
    "Data overview",
    "Data portrait",
    "profile dataset",
    "dataset profile",
)
_TARGET_HINTS = (
    "Target distribution",
    "targetDistribution",
    "target Distribution",
    "target distribution",
    "Tab Distribution",
)
_MISSING_HINTS = ("Missing", "Empty", "missing", "null rate", "nullRate")
_CORRELATION_HINTS = ("Relevance", "Related Matrix", "correlation", "correlation matrix")
_DISTRIBUTION_HINTS = (
    "Field Distribution",
    "Variable distribution",
    "Data distribution",
    "Frequency",
    "Histogram",
    "histogram",
    "frequency",
)
_OVERVIEW_HINTS = ("Data overview", "Data overview", "Field Overview", "Field Details", "overview")
_RESERVED_ASCII_TOKENS = frozenset(
    {
        "analyze",
        "analysis",
        "and",
        "at",
        "between",
        "calculate",
        "check",
        "column",
        "columns",
        "compute",
        "correlation",
        "current",
        "data",
        "dataset",
        "distribution",
        "field",
        "fields",
        "for",
        "frequency",
        "histogram",
        "look",
        "matrix",
        "missing",
        "null",
        "of",
        "or",
        "overview",
        "profile",
        "rate",
        "sample",
        "show",
        "target",
        "the",
        "variable",
        "variables",
        "versus",
        "vs",
        "with",
    }
)


@dataclass(frozen=True)
class DatasetAnalysisRequest:
    sections: tuple[str, ...]
    columns: tuple[str, ...] | None
    target_col: str | None


@dataclass(frozen=True)
class DatasetAnalysisRequestResult:
    request: DatasetAnalysisRequest | None = None
    clarification: str | None = None


def detect_dataset_analysis_intent(utterance: str | None) -> bool:
    """Return whether the utterance explicitly requests dataset diagnostics."""

    text = _normalized_text(utterance)
    if not text:
        return False
    return any(
        hint in text
        for hint in (
            *_GENERAL_HINTS,
            *_TARGET_HINTS,
            *_MISSING_HINTS,
            *_CORRELATION_HINTS,
            *_DISTRIBUTION_HINTS,
            *_OVERVIEW_HINTS,
        )
    )


def build_dataset_analysis_request(
    utterance: str,
    *,
    columns: Sequence[str],
    target_col: str | None,
    business_names: Mapping[str, str],
) -> DatasetAnalysisRequestResult:
    """Bind an analysis request to the current dataset's known semantics."""

    text = _normalized_text(utterance)
    ordered_columns = tuple(dict.fromkeys(str(column) for column in columns))
    column_set = frozenset(ordered_columns)
    if not ordered_columns:
        return _clarify("No field to analyse in the current data set.")
    if target_col is not None and target_col not in column_set:
        return _clarify(f"Configured target Fields[{target_col}]Not currently in data concentration,Please fix field mapping first.")

    is_general = any(hint in text for hint in _GENERAL_HINTS)
    requested: set[str] = set()
    if is_general:
        requested.update({"overview", "missing", "distribution", "correlation"})
        if target_col is not None:
            requested.add("target")
    else:
        if any(hint in text for hint in _OVERVIEW_HINTS):
            requested.add("overview")
        if any(hint in text for hint in _TARGET_HINTS):
            requested.add("target")
        if any(hint in text for hint in _MISSING_HINTS):
            requested.add("missing")
        if any(hint in text for hint in _DISTRIBUTION_HINTS):
            requested.add("distribution")
        if any(hint in text for hint in _CORRELATION_HINTS):
            requested.add("correlation")

    if not requested:
        return _clarify("Please check the data profile.,target Distribution,Missing,Distribution or related matrix.")
    if "target" in requested and target_col is None:
        return _clarify("Current sample is not confirmed target Fields,Please configure the semantic of the data first target.")

    selected = _mentioned_columns(
        text,
        columns=ordered_columns,
        business_names=business_names,
    )
    unknown = _unknown_ascii_column_mentions(text, column_set)
    if unknown:
        name = unknown[0]
        return _clarify(f"No fields in the current data set[{name}],Please use the existing field name or business name.")

    sections = tuple(section for section in _SECTION_ORDER if section in requested)
    return DatasetAnalysisRequestResult(
        request=DatasetAnalysisRequest(
            sections=sections,
            columns=selected or None,
            target_col=target_col,
        )
    )


def _mentioned_columns(
    text: str,
    *,
    columns: tuple[str, ...],
    business_names: Mapping[str, str],
) -> tuple[str, ...]:
    selected: list[str] = []
    for column in columns:
        raw = column.lower()
        if _contains_column_token(text, raw):
            selected.append(column)
            continue
        business_name = str(business_names.get(column) or "").strip().lower()
        if business_name and business_name in text:
            selected.append(column)
    return tuple(selected)


def _contains_column_token(text: str, column: str) -> bool:
    if not column:
        return False
    if column.isascii() and re.fullmatch(r"[a-z_][a-z0-9_]*", column):
        return re.search(rf"(?<![a-z0-9_]){re.escape(column)}(?![a-z0-9_])", text) is not None
    return column in text


def _unknown_ascii_column_mentions(
    text: str,
    known_columns: frozenset[str],
) -> tuple[str, ...]:
    known_lower = {column.lower() for column in known_columns}
    tokens = re.findall(r"[a-z_][a-z0-9_]*", text)
    unknown = [
        token
        for token in tokens
        if token not in known_lower and token not in _RESERVED_ASCII_TOKENS
    ]
    return tuple(dict.fromkeys(unknown))


def _clarify(message: str) -> DatasetAnalysisRequestResult:
    return DatasetAnalysisRequestResult(request=None, clarification=message)


def _normalized_text(value: str | None) -> str:
    return str(value or "").strip().lower()


__all__ = [
    "DatasetAnalysisRequest",
    "DatasetAnalysisRequestResult",
    "build_dataset_analysis_request",
    "detect_dataset_analysis_intent",
]
