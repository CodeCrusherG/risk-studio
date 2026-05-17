"""Natural-language compiler for governed, task-owned dataset exports.

This module only recognizes explicit exports of the current dataset/sample to
CSV or Excel.  Reports, strategies and rules are intentionally outside this
route so an Agent cannot accidentally substitute a raw-data export for a
domain report workflow.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re


_DATASET_SCOPE = re.compile(
    r"(?:Current|This one.|This time.)(?:It's...)?(?:Dataset|Data|Sample)"
    r"|(?:current|this)\s+(?:dataset|data|sample)\b",
    re.IGNORECASE,
)
_EXPORT_ACTION = re.compile(r"(?:Export|Download|\bexport\b|\bdownload\b)", re.IGNORECASE)
_CSV_FORMAT = re.compile(r"(?<![A-Za-z0-9_])csv(?![A-Za-z0-9_])", re.IGNORECASE)
_XLSX_FORMAT = re.compile(
    r"(?<![A-Za-z0-9_])(?:xlsx|excel)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
_NON_DATA_OBJECT = re.compile(
    r"(?:Policy|Rule|Report|Document|Templates|Analysis|Missing(?:Value)?Analysis|Statistics(?:Result|Analysis|Overview)?|"
    r"Data overview|Sample overview|Data dictionary|Field Dictionary|"
    r"strategy|rules?|reports?|documents?|templates?|analysis\s+results?|"
    r"missing(?:ness)?\s+analysis|statistics?|data\s+(?:summary|profile|dictionary))",
    re.IGNORECASE,
)
_TEXT_MODE = re.compile(
    r"(?:These.)?(?:Columns|Fields|Variables)?\s*(?:Press|Here.)(?:Pure)?Text(?:Format)?(?:Export|Writing)?"
    r"|(?:treat|write|export)?\s*(?:these\s+)?(?:columns?|fields?)?\s*as\s+text\b",
    re.IGNORECASE,
)
_FIELD_SPLIT = re.compile(r"\s*(?:,|,|,|and|and|and|\band\b|\+)\s*", re.IGNORECASE)


@dataclass(frozen=True)
class DatasetExportRequest:
    format: str
    text_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class DatasetExportRequestResult:
    request: DatasetExportRequest | None = None
    clarification: str | None = None


class _NeedClarification(ValueError):
    pass


class _ColumnResolver:
    def __init__(
        self,
        columns: Sequence[str],
        business_names: Mapping[str, str],
    ) -> None:
        ordered = tuple(dict.fromkeys(str(column).strip() for column in columns))
        if not ordered or any(not column for column in ordered):
            raise _NeedClarification("The current data set does not have a valid field to export.")
        aliases: dict[str, list[str]] = {}
        for column in ordered:
            aliases.setdefault(column.casefold(), []).append(column)
            business_name = str(business_names.get(column) or "").strip()
            if business_name:
                aliases.setdefault(business_name.casefold(), []).append(column)
        self._aliases = aliases

    def resolve(self, value: str) -> str:
        cleaned = _clean_field(value)
        matches = tuple(dict.fromkeys(self._aliases.get(cleaned.casefold(), ())))
        if not matches:
            raise _NeedClarification(
                f"There are no fields in the current data set '{cleaned or value.strip()}],"
                "Please use the existing field name or business name."
            )
        if len(matches) != 1:
            raise _NeedClarification(
                f"Field name '{cleaned}]For multiple fields, change the original field name."
            )
        return matches[0]


def detect_dataset_export_intent(utterance: str | None) -> bool:
    """Detect explicit current-dataset exports, including format questions.

    A missing or conflicting supported format is still an export intent: the
    turn handler owns the clarification instead of letting the request fall
    through to a generic chat path.
    """

    text = str(utterance or "").strip()
    if not text:
        return False
    if not (_DATASET_SCOPE.search(text) and _EXPORT_ACTION.search(text)):
        return False
    return not _export_object_is_non_data(text)


def build_dataset_export_request(
    utterance: str,
    *,
    columns: Sequence[str],
    business_names: Mapping[str, str],
) -> DatasetExportRequestResult:
    """Compile an export utterance into the closed Tool input subset."""

    text = str(utterance or "").strip()
    try:
        if not text:
            raise _NeedClarification("Please indicate the current data to be exported and chooseCSV orExcel format.")
        if not (_DATASET_SCOPE.search(text) and _EXPORT_ACTION.search(text)):
            if _NON_DATA_OBJECT.search(text):
                raise _NeedClarification(
                    "Only the current data set (original breakdown) is exported here; the analysis results, data dictionary, policy, rules or reports"
                    "Use the corresponding analysis or report export function."
                )
            raise _NeedClarification("Please specify whether you want to export the current data set or current sample.")
        if _export_object_is_non_data(text):
            raise _NeedClarification(
                "Only the current data set (original breakdown) is exported here; the analysis results, data dictionary, policy, rules or reports"
                "Use the corresponding analysis or report export function."
            )

        has_csv = bool(_CSV_FORMAT.search(text))
        has_xlsx = bool(_XLSX_FORMAT.search(text))
        if has_csv and has_xlsx:
            raise _NeedClarification("One time, please choose.CSV orExcel One of the export formats.")
        if not has_csv and not has_xlsx:
            raise _NeedClarification("ChooseCSV orExcel Export the format.")

        resolver = _ColumnResolver(columns, business_names)
        text_columns = _parse_text_columns(text, resolver)
        return DatasetExportRequestResult(
            request=DatasetExportRequest(
                format="csv" if has_csv else "xlsx",
                text_columns=text_columns,
            )
        )
    except _NeedClarification as exc:
        return DatasetExportRequestResult(clarification=str(exc))


def _parse_text_columns(text: str, resolver: _ColumnResolver) -> tuple[str, ...]:
    marker = _TEXT_MODE.search(text)
    if marker is None:
        return ()

    prefix = text[: marker.start()].strip()
    # Text-mode fields are expected in the final comma/semicolon-delimited
    # clause immediately before "By Text" / "as text".
    segment = re.split(r"[,,;;..]", prefix)[-1].strip()
    if segment == prefix:
        formats = [
            match
            for pattern in (_CSV_FORMAT, _XLSX_FORMAT)
            for match in pattern.finditer(prefix)
        ]
        if formats:
            segment = prefix[max(formats, key=lambda item: item.end()).end() :]
    segment = segment.strip(" ,,;;::")
    segment = re.sub(
        r"^(?:- Put it on.|Will|And put|And will|and\s+|export\s+|write\s+|treat\s+)",
        "",
        segment,
        flags=re.I,
    )
    segment = re.sub(
        r"^(?:Current|This one.|This time.)(?:It's...)?(?:Dataset|Data|Sample)"
        r"(?:Medium(?:It's...)?|Lee.(?:It's...)?|Internal(?:It's...)?)?\s*",
        "",
        segment,
    )
    segment = re.sub(r"(?:These.)?(?:Columns|Fields|Variables)\s*$", "", segment).strip()
    if not segment:
        raise _NeedClarification("Please specify which fields need to be exported by text.")

    tokens = [item for item in _FIELD_SPLIT.split(segment) if item.strip()]
    if not tokens:
        raise _NeedClarification("Please specify which fields need to be exported by text.")
    resolved = tuple(dict.fromkeys(resolver.resolve(item) for item in tokens))
    return resolved


def _export_object_is_non_data(text: str) -> bool:
    """Reject a nearer report/rule object even when data is mentioned as context."""

    action = _EXPORT_ACTION.search(text)
    if action is None:
        return False
    formats = [
        match
        for pattern in (_CSV_FORMAT, _XLSX_FORMAT)
        for match in pattern.finditer(text, action.end())
    ]
    if formats:
        nearest_format = min(formats, key=lambda item: item.start())
        if _NON_DATA_OBJECT.search(text[action.end() : nearest_format.start()]):
            return True
    else:
        # With no format token, inspect the object after the action so
        # "Export the analysis of the current data" remains owned by the analysis/report routes.
        # Purpose clauses do not redefine the exported object, e.g.
        # "Export current data for follow-up report" is still a raw-dataset export.
        suffix = text[action.end() :]
        object_clause = re.split(
            r"(?:For|For|- Yes.|to be used for|\b(?:for|to)\s+(?:a\s+)?(?:later|subsequent)\b)",
            suffix,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        if _NON_DATA_OBJECT.search(object_clause):
            return True

    clause_start = max(
        text.rfind(",", 0, action.start()),
        text.rfind(",", 0, action.start()),
        text.rfind(";", 0, action.start()),
        text.rfind(";", 0, action.start()),
        text.rfind(".", 0, action.start()),
    )
    prefix = text[clause_start + 1 : action.start()]
    dataset_matches = list(_DATASET_SCOPE.finditer(prefix))
    non_data_matches = list(_NON_DATA_OBJECT.finditer(prefix))
    return bool(
        non_data_matches
        and (
            not dataset_matches
            or non_data_matches[-1].start() > dataset_matches[-1].start()
        )
    )


def _clean_field(value: str) -> str:
    cleaned = str(value).strip().strip("`'\"")
    return re.sub(r"\s*(?:These.)?(?:Columns|Fields|Variables)\s*$", "", cleaned).strip()


__all__ = [
    "DatasetExportRequest",
    "DatasetExportRequestResult",
    "build_dataset_export_request",
    "detect_dataset_export_intent",
]
