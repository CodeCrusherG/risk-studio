"""Deterministic natural-language compiler for governed dataset transforms.

The compiler emits only the closed operation grammar accepted by
``marvis.data.transforms``.  It deliberately does not accept or synthesize
SQL/Python source, and it fails closed when a field or a destructive choice is
ambiguous.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
import re


_TRANSFORM_HINTS = (
    "Rename",
    "Change of name",
    "Fill",
    "Completion",
    "Type Conversion",
    "Convert to",
    "Convert to",
    "Filter",
    "Filter",
    "Go heavy.",
    "Derived Fields",
    "Add Field",
    "rename",
    "fill missing",
    "impute",
    "cast ",
    "filter rows",
    "deduplicate",
    "derive ",
    "create column",
)
_DELETE_HINT = re.compile(r"(?:Delete|Delete it.|Remove|Get rid of it.|\bdrop\b|\bremove\b)", re.I)
_NON_DATA_DELETE_HINT = re.compile(r"(?:Rule|Policy|Nodes|Tasks|Report|Documentation|plan|rule|strategy)", re.I)
_DATA_DELETE_HINT = re.compile(
    r"(?:Columns|Fields|Variables|Label|Cell phone number|Amount|Income|\bcolumns?\b|\bfields?\b|[a-z_][a-z0-9_]*)",
    re.I,
)
_SOURCE_CODE_REQUEST = re.compile(
    r"(?:Use|Use|Implementation|Run|write|run|execute|using)\s*(?:One\s*)?"
    r"(?:sql|python)(?:\s*(?:Code|Script|code|script))?",
    re.I,
)
_ACTION_START = re.compile(
    r"^(?:(?:And then...|Again.|And...|and|and\s+then)\s*)?"
    r"(?:- Put it on.|Will|Use|Use|rename\b|drop\b|remove\b|fill\b|impute\b|"
    r"cast\b|Filter|Filter|filter\b|Add|Create|Pumpkin.|derive\b|create\b|add\b|"
    r"Delete|Delete it.|Remove|Get rid of it.|Press.+?Go heavy.|deduplicate\b)",
    re.I,
)
_PROTECTED_ROLES = frozenset({"target", "id", "phone", "idcard"})
_EXPLICIT_DROP_CONFIRMATION = re.compile(
    r"(?:Im...\s*)?(?:Clear\s*)?Confirm.\s*(?:Yes.|Implementation)?\s*(?:Delete|Delete it.|Remove|Get rid of it.)"
    r"|\b(?:i\s+)?confirm(?:ed)?\b.{0,30}\b(?:drop|remove)\b",
    re.I,
)
_DESTINATION_PATTERN = r"(?:`[^`]+`|'[^']+'|\"[^\"]+\"|[\w\u4e00-\u9fff.\-]+)"
_SAFE_INTEGER_MAX = 2**53 - 1
_TYPE_ALIASES = {
    "Integer": "INTEGER",
    "Int": "INTEGER",
    "Long": "BIGINT",
    "Floating Point Number": "DOUBLE",
    "Floating Point Type": "DOUBLE",
    "Value": "DOUBLE",
    "String": "VARCHAR",
    "Text": "VARCHAR",
    "Date": "DATE",
    "Time": "TIMESTAMP",
    "Timetamp": "TIMESTAMP",
    "Boolean": "BOOLEAN",
    "Boolean Value": "BOOLEAN",
}
_SAFE_TYPE = re.compile(
    r"^(?:BOOLEAN|TINYINT|SMALLINT|INTEGER|BIGINT|HUGEINT|"
    r"UTINYINT|USMALLINT|UINTEGER|UBIGINT|REAL|FLOAT|DOUBLE|VARCHAR|DATE|"
    r"TIMESTAMP|TIMESTAMP WITH TIME ZONE|DECIMAL\([1-9]\d*,\s*\d+\))$",
    re.I,
)
_STATISTIC_METHODS = {
    "Mean": "mean",
    "Average": "mean",
    "mean": "mean",
    "average": "mean",
    "Medium": "median",
    "median": "median",
    "Min": "min",
    "minimum": "min",
    "min": "min",
    "Maximum": "max",
    "maximum": "max",
    "max": "max",
}


@dataclass(frozen=True)
class DatasetTransformRequest:
    operations: tuple[dict[str, object], ...]
    confirm_protected_drop: bool = False


@dataclass(frozen=True)
class DatasetTransformRequestResult:
    request: DatasetTransformRequest | None = None
    clarification: str | None = None
    operations: tuple[dict[str, object], ...] = ()
    protected_fields: tuple[str, ...] = ()


class _NeedClarification(ValueError):
    pass


class _ColumnResolver:
    def __init__(
        self,
        columns: Sequence[str],
        business_names: Mapping[str, str],
    ) -> None:
        ordered = tuple(dict.fromkeys(str(column) for column in columns))
        if not ordered or any(not column.strip() for column in ordered):
            raise _NeedClarification("No valid processed field in the current data set.")
        self.columns = ordered
        aliases: dict[str, list[str]] = {}
        for column in ordered:
            aliases.setdefault(column.casefold(), []).append(column)
            business_name = str(business_names.get(column) or "").strip()
            if business_name:
                aliases.setdefault(business_name.casefold(), []).append(column)
        self._aliases = aliases
        alternatives = sorted(aliases, key=lambda value: (-len(value), value))
        self.pattern = (
            r"(?<![A-Za-z0-9_])(?:"
            + "|".join(re.escape(value) for value in alternatives)
            + r")(?![A-Za-z0-9_])"
        )

    def resolve(self, value: str) -> str:
        cleaned = _clean_field_token(value)
        matches = self._aliases.get(cleaned.casefold(), [])
        if not matches:
            raise _NeedClarification(
                f"No fields in the current data set[{cleaned or value.strip()}],Please use the existing field name or business name."
            )
        unique = tuple(dict.fromkeys(matches))
        if len(unique) != 1:
            raise _NeedClarification(
                f"Field Name[{cleaned}]Corresponds to multiple fields,Please change to the original field name."
            )
        return unique[0]

    def resolve_list(self, value: str) -> list[str]:
        tokens = _split_field_list(value)
        if not tokens:
            raise _NeedClarification("Please specify the fields to be processed.")
        resolved = [self.resolve(token) for token in tokens]
        if len(resolved) != len(set(resolved)):
            raise _NeedClarification("The same field is specified repeatedly,Please confirm and try again..")
        return resolved


def detect_dataset_transform_intent(utterance: str | None) -> bool:
    """Return whether text explicitly requests a governed dataset change."""

    text = str(utterance or "").strip().casefold()
    if not text:
        return False
    if any(hint in text for hint in _TRANSFORM_HINTS):
        return True
    if re.search(r"(?:Add|Create|Calculate)\s*(?:Fields|Columns|Variables)?\s*[\w\u4e00-\u9fff]+\s*=", text):
        return True
    if _DELETE_HINT.search(text):
        return not _NON_DATA_DELETE_HINT.search(text) and bool(
            _DATA_DELETE_HINT.search(text)
        )
    return False


def build_dataset_transform_request(
    utterance: str,
    *,
    columns: Sequence[str],
    business_names: Mapping[str, str],
    semantic_mapping: object,
) -> DatasetTransformRequestResult:
    """Compile a natural-language request into the closed transform grammar."""

    text = str(utterance or "").strip()
    if not text:
        return _clarify("Please indicate how the current data set is processed..")
    try:
        semantic_names, roles, target_col = _semantic_parts(semantic_mapping)
        merged_names = dict(semantic_names)
        merged_names.update({str(key): str(value) for key, value in business_names.items()})
        virtual_columns = tuple(dict.fromkeys(str(column) for column in columns))
        virtual_names = {
            column: name
            for column, name in merged_names.items()
            if column in virtual_columns
        }
        virtual_roles = {
            column: role
            for column, role in roles.items()
            if column in virtual_columns
        }
        virtual_target = target_col if target_col in virtual_columns else None
        resolver = _ColumnResolver(virtual_columns, virtual_names)
        if _SOURCE_CODE_REQUEST.search(text):
            raise _NeedClarification(
                "Data processing not accepted SQL or Python Code;Please describe directly the renaming,Delete,Fill,Convert,Filter,Im not sure Im gonna be able to get you out of here.."
            )

        operations: list[dict[str, object]] = []
        confirmed_protected: list[str] = []
        pending_protected: list[str] = []
        for clause in _split_clauses(text):
            operation = _parse_clause(clause, resolver)
            if operation["op"] == "drop_columns":
                protected_in_action = [
                    column
                    for column in operation["columns"]  # type: ignore[union-attr]
                    if column == virtual_target
                    or virtual_roles.get(column) in _PROTECTED_ROLES
                ]
                if protected_in_action:
                    destination = (
                        confirmed_protected
                        if _EXPLICIT_DROP_CONFIRMATION.search(clause)
                        else pending_protected
                    )
                    destination.extend(protected_in_action)
            operations = _append_or_merge(operations, operation)
            (
                virtual_columns,
                virtual_names,
                virtual_roles,
                virtual_target,
            ) = _advance_virtual_schema(
                virtual_columns,
                virtual_names,
                virtual_roles,
                virtual_target,
                operation,
            )
            if virtual_columns:
                resolver = _ColumnResolver(virtual_columns, virtual_names)
        if not operations:
            raise _NeedClarification(
                "Please rename it clearly.,Delete,Missing Fill,Type Conversion,Conditional Filter,Numerical derivative or reset parameters."
            )

        pending = tuple(dict.fromkeys(pending_protected))
        canonical_operations = tuple(operations)
        if pending:
            labels = ",".join(pending)
            return DatasetTransformRequestResult(
                request=None,
                clarification=(
                    f"Fields {labels} Yes. target or key identification field."
                    f"If you still want to delete,Please respond clearly.(Confirm Delete {labels})."
                ),
                operations=canonical_operations,
                protected_fields=pending,
            )
        confirmed = bool(confirmed_protected)
        return DatasetTransformRequestResult(
            request=DatasetTransformRequest(
                operations=canonical_operations,
                confirm_protected_drop=confirmed,
            ),
            operations=canonical_operations,
        )
    except _NeedClarification as exc:
        return _clarify(str(exc))


def _parse_clause(clause: str, resolver: _ColumnResolver) -> dict[str, object]:
    text = clause.strip(" ,,;;.")
    lowered = text.casefold()
    if re.search(r"(?:Go heavy.|\bdeduplicat(?:e|ion)\b|remove\s+duplicates)", lowered):
        return _parse_deduplicate(text, resolver)
    if re.search(r"(?:Rename|Change of name|\brename\b)", lowered):
        return _parse_rename(text, resolver)
    if re.search(r"(?:Fill|Completion|\bfill\b|\bimpute\b)", lowered):
        return _parse_fill(text, resolver)
    if re.search(r"(?:Tight turn.|Try to spin|Type Conversion|Convert to|Convert to|\bcast\b)", lowered):
        return _parse_cast(text, resolver)
    if re.search(r"(?:Filter|Filter|\bfilter\b|keep\s+rows\s+where)", lowered):
        return _parse_filter(text, resolver)
    if re.search(r"(?:Add|Create|Pumpkin.|\bderive\b|create\s+column|add\s+column)", lowered):
        return _parse_derive(text, resolver)
    if _DELETE_HINT.search(lowered):
        return _parse_drop(text, resolver)
    raise _NeedClarification(f"Could not determine the parameters for processing data at this step:[{text}].")


def _parse_rename(text: str, resolver: _ColumnResolver) -> dict[str, object]:
    alias = resolver.pattern
    patterns = (
        re.compile(
            rf"(?:- Put it on.|Will)?\s*(?P<src>{alias})\s*(?:Fields|Columns)?\s*"
            rf"(?:Rename As|Change name|rename\s+(?:to|as))\s*(?P<dst>{_DESTINATION_PATTERN})",
            re.I,
        ),
        re.compile(
            rf"\brename\s+(?:column\s+)?(?P<src>{alias})\s+"
            rf"(?:to|as)\s+(?P<dst>{_DESTINATION_PATTERN})",
            re.I,
        ),
    )
    matches = _unique_matches(text, patterns)
    marker_count = len(re.findall(r"(?:Rename(?:Yes)?|Change of name(?:Yes)?|\brename\b)", text, re.I))
    if not matches or len(matches) != marker_count:
        raise _NeedClarification("Rename requires clarity of existing fields and new field names.")
    mapping: dict[str, str] = {}
    for match in matches:
        source = resolver.resolve(match.group("src"))
        destination = _unquote(match.group("dst")).strip()
        if not destination or "\x00" in destination:
            raise _NeedClarification("New field name cannot be empty.")
        if source in mapping:
            raise _NeedClarification(f"Fields[{source}]Renamed repeatedly,Please keep only one target name.")
        if destination in resolver.columns and destination != source:
            raise _NeedClarification(f"New field name[{destination}]Exists,Please change your name..")
        mapping[source] = destination
    return {"op": "rename_columns", "mapping": mapping}


def _parse_drop(text: str, resolver: _ColumnResolver) -> dict[str, object]:
    chinese = re.search(
        r"(?:Confirm.\s*)?(?:Delete|Delete it.|Remove|Get rid of it.)\s*(?:Fields|Columns|Variables)?\s*(?P<items>.+)$",
        text,
        re.I,
    )
    english = re.search(
        r"(?:\bconfirm(?:ed)?\s+)?\b(?:drop|remove)\s+"
        r"(?:columns?|fields?)?\s*(?P<items>.+)$",
        text,
        re.I,
    )
    match = chinese or english
    if match is None:
        raise _NeedClarification("Delete Fields Need Clear To Delete.")
    columns = resolver.resolve_list(match.group("items"))
    return {"op": "drop_columns", "columns": columns}


def _parse_fill(text: str, resolver: _ColumnResolver) -> dict[str, object]:
    alias = resolver.pattern
    patterns = (
        re.compile(
            rf"(?:and)?(?:Use|Use)\s*(?P<method>.+?)\s*(?:Fill|Completion)\s*"
            rf"(?P<column>{alias})(?:Fields)?(?:Its...)?(?:Missing value|Empty)?$",
            re.I,
        ),
        re.compile(
            rf"(?:Fill|Completion)\s*(?P<column>{alias})(?:Fields)?(?:Its...)?(?:Missing value|Empty)?"
            rf"\s*(?:Yes|Use|Use)\s*(?P<method>.+)$",
            re.I,
        ),
        re.compile(
            rf"\b(?:fill|impute)\s+(?:missing(?:\s+values?)?(?:\s+in)?\s+)?"
            rf"(?P<column>{alias})(?:\s+missing(?:\s+values?)?)?\s+"
            rf"(?:with|using)\s+(?P<method>.+)$",
            re.I,
        ),
    )
    match = next((pattern.search(text) for pattern in patterns if pattern.search(text)), None)
    if match is None:
        unknown = _likely_unknown_field(text, resolver)
        if unknown:
            resolver.resolve(unknown)
        raise _NeedClarification("Missing fill requires clear fields,and constant or mean/median/min/max Methodology.")
    column = resolver.resolve(match.group("column"))
    raw_method = match.group("method").strip(" ,,.")
    normalized_method = raw_method.casefold().strip()
    statistic = _STATISTIC_METHODS.get(normalized_method)
    if statistic is not None:
        fill: dict[str, object] = {"column": column, "method": statistic}
    else:
        constant_text = re.sub(
            r"^(?:Constant|constant)\s*[::]?\s*", "", raw_method, flags=re.I
        )
        value = _parse_literal(constant_text)
        if value is None:
            raise _NeedClarification("Missing value is no longer valid null Fill,Please provide non-empty constants.")
        fill = {"column": column, "method": "constant", "value": value}
    return {"op": "fill_missing", "fills": [fill]}


def _parse_cast(text: str, resolver: _ColumnResolver) -> dict[str, object]:
    alias = resolver.pattern
    patterns = (
        re.compile(
            rf"(?:Will|- Put it on.)?\s*(?P<column>{alias})\s*"
            rf"(?P<mode>Try|Wrong.|Clear.|Strict|try|strict)?\s*"
            rf"(?:Type)?(?:Convert|Turn|cast)\s*(?:Yes|Done.|to)\s*(?P<type>.+)$",
            re.I,
        ),
        re.compile(
            rf"(?P<mode>try|strict)?\s*\bcast\s+(?P<column>{alias})\s+"
            rf"to\s+(?P<type>.+?)(?:\s+(?:using|in)\s+"
            rf"(?P<mode_after>try|strict)\s*(?:mode)?)?$",
            re.I,
        ),
    )
    match = next((pattern.search(text) for pattern in patterns if pattern.search(text)), None)
    if match is None:
        unknown = _likely_unknown_field(text, resolver)
        if unknown:
            resolver.resolve(unknown)
        raise _NeedClarification("Type conversion requires clear fields,Type of target and strict or try Mode.")
    column = resolver.resolve(match.group("column"))
    groups = match.groupdict()
    raw_mode = groups.get("mode") or groups.get("mode_after")
    if raw_mode is None:
        raise _NeedClarification(
            f"Fields[{column}]Type conversion requires selection strict(Failure is stopped.)or try(Failed to empty)Mode."
        )
    mode = "try" if raw_mode.casefold() in {"try", "Try", "Wrong.", "Clear."} else "strict"
    target_type = _normalize_type(match.group("type"))
    return {
        "op": "cast_columns",
        "casts": [{"column": column, "to_type": target_type, "mode": mode}],
    }


def _parse_filter(text: str, resolver: _ColumnResolver) -> dict[str, object]:
    body = re.sub(
        r"^.*?(?:Filter|Filter|filter\s+rows(?:\s+where)?|keep\s+rows\s+where)\s*",
        "",
        text,
        count=1,
        flags=re.I,
    ).strip()
    if not body:
        raise _NeedClarification("Conditions filter requires field,Comparer and value.")
    parts, connectors = _split_conditions(body)
    predicates = [_parse_condition(part, resolver) for part in parts]
    if len(predicates) == 1:
        predicate = predicates[0]
    else:
        logical = {connector for connector in connectors}
        if len(logical) != 1:
            raise _NeedClarification("Use it also AND and OR Please describe in stages.,Avoiding a hierarchy of conditions.")
        predicate = {"op": logical.pop(), "args": predicates}
    return {"op": "filter_rows", "predicate": predicate}


def _parse_condition(text: str, resolver: _ColumnResolver) -> dict[str, object]:
    clause = text.strip(" ,,.()")
    match = re.match(rf"(?P<column>{resolver.pattern})\s*(?P<rest>.+)$", clause, re.I)
    if match is None:
        unknown = re.match(r"[`'\"]?([A-Za-z_][A-Za-z0-9_]*|[\u4e00-\u9fff]+)", clause)
        if unknown:
            resolver.resolve(unknown.group(1))
        raise _NeedClarification(f"Could not close temporary folder: s[{clause}],Please specify the fields,Comparers and values.")
    column = resolver.resolve(match.group("column"))
    rest = match.group("rest").strip()
    null_operators = (
        (r"^(?:Not Empty|Non-empty|is\s+not\s+null)$", "is_not_null"),
        (r"^(?:Empty|is empty|is\s+null)$", "is_null"),
    )
    for pattern, operation in null_operators:
        if re.fullmatch(pattern, rest, re.I):
            return {"op": operation, "arg": {"column": column}}
    operators = (
        (r"^(?:greater than or equal to|Not less than|At least.|>=|≥)\s*(.+)$", "gte"),
        (r"^(?:less than or equal to|Not greater than|Up to|<=|≤)\s*(.+)$", "lte"),
        (r"^(?:Not equal to|!=|<>)\s*(.+)$", "ne"),
        (r"^(?:Greater than|More than|>)\s*(.+)$", "gt"),
        (r"^(?:less than|Less than|<)\s*(.+)$", "lt"),
        (r"^(?:Equal|Yes|==|=)\s*(.+)$", "eq"),
    )
    for pattern, operation in operators:
        compared = re.fullmatch(pattern, rest, re.I)
        if compared:
            value = _parse_literal(compared.group(1))
            if value is None and operation in {"eq", "ne"}:
                null_operation = "is_null" if operation == "eq" else "is_not_null"
                return {"op": null_operation, "arg": {"column": column}}
            return {
                "op": operation,
                "left": {"column": column},
                "right": {"literal": value},
            }
    raise _NeedClarification(f"Filter Fields[{column}]Missing supported comparators or values.")


def _parse_derive(text: str, resolver: _ColumnResolver) -> dict[str, object]:
    patterns = (
        re.compile(
            rf"(?:Add|Create|Pumpkin.)\s*(?:Fields|Columns|Variables)?\s*"
            rf"(?P<name>{_DESTINATION_PATTERN})\s*(?:=|Yes)\s*(?P<expression>.+)$",
            re.I,
        ),
        re.compile(
            rf"\b(?:derive|create|add)\s+(?:column\s+)?"
            rf"(?P<name>{_DESTINATION_PATTERN})\s*(?:=|as)\s*(?P<expression>.+)$",
            re.I,
        ),
    )
    match = next((pattern.search(text) for pattern in patterns if pattern.search(text)), None)
    if match is None:
        raise _NeedClarification("The derivative field needs to provide a new field name and a limited binary algorithm expression.")
    name = _unquote(match.group("name")).strip()
    if not name or name in resolver.columns:
        raise _NeedClarification(f"Derived field name[{name}]Empty or Existing,Please change your name..")
    expression = _parse_arithmetic(match.group("expression"), resolver)
    return {
        "op": "derive_columns",
        "derivations": [{"name": name, "expression": expression}],
    }


def _parse_arithmetic(text: str, resolver: _ColumnResolver) -> dict[str, object]:
    match = re.fullmatch(
        r"\s*(?P<left>.+?)\s*(?P<operator>Divide by|Multiply|Modelling|Add|Less|[+\-*/%])"
        r"\s*(?P<right>.+?)\s*",
        text,
        re.I,
    )
    if match is None:
        raise _NeedClarification("The derivative expression supports only between two fields or values +,-,*,/,% Operations.")
    operation = {
        "+": "add",
        "Add": "add",
        "-": "subtract",
        "Less": "subtract",
        "*": "multiply",
        "Multiply": "multiply",
        "/": "divide",
        "Divide by": "divide",
        "%": "modulo",
        "Modelling": "modulo",
    }[match.group("operator").casefold()]
    return {
        "op": operation,
        "left": _parse_arithmetic_operand(match.group("left"), resolver),
        "right": _parse_arithmetic_operand(match.group("right"), resolver),
    }


def _parse_arithmetic_operand(text: str, resolver: _ColumnResolver) -> dict[str, object]:
    token = text.strip()
    try:
        return {"column": resolver.resolve(token)}
    except _NeedClarification:
        value = _parse_literal(token)
        if isinstance(value, bool) or value is None or not isinstance(value, (int, float)):
            raise _NeedClarification(
                f"In arithmetic expression[{token}]Not an existing field or limited value."
            ) from None
        return {"literal": value}


def _parse_deduplicate(text: str, resolver: _ColumnResolver) -> dict[str, object]:
    chinese = re.search(r"Press\s*(?P<keys>.+?)\s*Go heavy.", text, re.I)
    english = re.search(
        r"\bdeduplicate(?:\s+rows)?\s+by\s+(?P<keys>.+?)"
        r"(?=\s+order\s+by|\s+keep(?:ing)?\b|$)",
        text,
        re.I,
    )
    key_match = chinese or english
    if key_match is None:
        raise _NeedClarification("Its a matter of making one or more clear. key Fields.")
    keys = resolver.resolve_list(key_match.group("keys"))
    order_by: list[dict[str, str]] = []
    nulls = "first" if re.search(r"(?:Empty front|nulls\s+first)", text, re.I) else "last"

    for match in re.finditer(
        rf"(?:Reservations|Remove)\s*(?P<column>{resolver.pattern})\s*"
        rf"(?P<direction>Latest|At the latest.|Max|First|Min)\s*(?:One.|Records)?",
        text,
        re.I,
    ):
        direction = "desc" if match.group("direction") in {"Latest", "At the latest.", "Max"} else "asc"
        order_by.append(
            {
                "column": resolver.resolve(match.group("column")),
                "direction": direction,
                "nulls": nulls,
            }
        )
    for match in re.finditer(
        rf"\border\s+by\s+(?P<column>{resolver.pattern})\s*"
        rf"(?P<direction>asc|desc)?(?:\s+nulls\s+(?P<nulls>first|last))?",
        text,
        re.I,
    ):
        raw_direction = match.group("direction")
        if raw_direction is None:
            raise _NeedClarification("Reordering sorting fields needs to be clear asc or desc.")
        order_by.append(
            {
                "column": resolver.resolve(match.group("column")),
                "direction": raw_direction.casefold(),
                "nulls": (match.group("nulls") or nulls).casefold(),
            }
        )
    if not order_by and chinese is not None:
        tail = text[chinese.end() :]
        for match in re.finditer(
            rf"Press\s*(?P<column>{resolver.pattern})\s*(?P<direction>Raise|Descending|asc|desc)",
            tail,
            re.I,
        ):
            direction = "desc" if match.group("direction").casefold() in {"Descending", "desc"} else "asc"
            order_by.append(
                {
                    "column": resolver.resolve(match.group("column")),
                    "direction": direction,
                    "nulls": nulls,
                }
            )
    if not order_by:
        raise _NeedClarification("Re-loading also requires clear sorting and ascending/Descending,To determine which record is kept.")
    ordered_columns = [item["column"] for item in order_by]
    if len(ordered_columns) != len(set(ordered_columns)):
        raise _NeedClarification("To reorder fields cannot be repeated.")
    return {"op": "deduplicate", "keys": keys, "order_by": order_by}


def _split_clauses(text: str) -> tuple[str, ...]:
    coarse = re.split(r"[;;.\n]+", text)
    result: list[str] = []
    for item in coarse:
        for remaining in _split_sequenced_actions(item.strip()):
            if not remaining:
                continue
            start = 0
            for match in re.finditer(r"[,,]", remaining):
                tail = remaining[match.end() :].lstrip()
                if _ACTION_START.match(tail):
                    result.append(remaining[start : match.start()].strip())
                    start = match.end()
            result.append(remaining[start:].strip())
    return tuple(item for item in result if item)


def _split_sequenced_actions(text: str) -> tuple[str, ...]:
    if not text:
        return ()
    result: list[str] = []
    start = 0
    sequence = re.compile(r"(?:And then...|And then...|Catch.|and\s+then|and(?=\s*(?:Delete|Delete it.|Remove|Get rid of it.)))", re.I)
    for match in sequence.finditer(text):
        tail = text[match.end() :].lstrip()
        if not _ACTION_START.match(tail):
            continue
        result.append(text[start : match.start()].strip())
        start = match.end()
    result.append(text[start:].strip())
    return tuple(item for item in result if item)


def _split_conditions(text: str) -> tuple[list[str], list[str]]:
    connector_pattern = re.compile(
        r"\s*(And...|and|and|and|Or...|or|\b(?:and|or)\b)\s*", re.I
    )
    parts: list[str] = []
    connectors: list[str] = []
    start = 0
    quote: str | None = None
    index = 0
    while index < len(text):
        char = text[index]
        if char in {"'", '"', "`"}:
            quote = None if quote == char else char if quote is None else quote
            index += 1
            continue
        if quote is None:
            match = connector_pattern.match(text, index)
            if match:
                part = text[start:index].strip()
                if not part:
                    raise _NeedClarification("The filter condition connector requires complete conditions before and after.")
                parts.append(part)
                connectors.append(
                    "or" if match.group(1).casefold() in {"Or...", "or", "or"} else "and"
                )
                index = match.end()
                start = index
                continue
        index += 1
    final = text[start:].strip()
    if not final:
        raise _NeedClarification("The filter condition connector requires complete conditions before and after.")
    parts.append(final)
    return parts, connectors


def _append_or_merge(
    operations: list[dict[str, object]],
    operation: dict[str, object],
) -> list[dict[str, object]]:
    if not operations or operations[-1]["op"] != operation["op"]:
        operations.append(operation)
        return operations
    current = operations[-1]
    op = str(operation["op"])
    if op == "rename_columns":
        mapping = dict(current["mapping"])  # type: ignore[arg-type]
        incoming = dict(operation["mapping"])  # type: ignore[arg-type]
        if set(mapping.values()) & set(incoming):
            # The incoming rename consumes a name produced by the preceding
            # rename, so it must remain a separate ordered kernel operation.
            operations.append(operation)
            return operations
        duplicate = set(mapping) & set(incoming)
        if duplicate:
            raise _NeedClarification(
                f"Fields[{sorted(duplicate)[0]}]Renamed repeatedly,Please keep only one target name."
            )
        mapping.update(incoming)
        current["mapping"] = mapping
        return operations
    member = {
        "drop_columns": "columns",
        "cast_columns": "casts",
        "fill_missing": "fills",
        "derive_columns": "derivations",
    }.get(op)
    if member is not None:
        if op in {"cast_columns", "fill_missing"}:
            item_key = "casts" if op == "cast_columns" else "fills"
            prior_columns = {
                str(item["column"])
                for item in current[item_key]  # type: ignore[union-attr]
            }
            incoming_columns = {
                str(item["column"])
                for item in operation[item_key]  # type: ignore[union-attr]
            }
            if prior_columns & incoming_columns:
                # Repeating a cast/fill on one column is an ordered request,
                # not two simultaneous members of the same kernel step.
                operations.append(operation)
                return operations
        if op == "derive_columns":
            prior_names = {
                str(item["name"])
                for item in current["derivations"]  # type: ignore[union-attr]
            }
            incoming_references = _referenced_columns(
                operation["derivations"]  # type: ignore[arg-type]
            )
            if prior_names & incoming_references:
                operations.append(operation)
                return operations
        current[member] = [
            *list(current[member]),  # type: ignore[arg-type]
            *list(operation[member]),  # type: ignore[arg-type]
        ]
        return operations
    operations.append(operation)
    return operations


def _advance_virtual_schema(
    columns: Sequence[str],
    business_names: Mapping[str, str],
    roles: Mapping[str, str],
    target_col: str | None,
    operation: Mapping[str, object],
) -> tuple[tuple[str, ...], dict[str, str], dict[str, str], str | None]:
    """Project one parsed operation onto the schema seen by later clauses."""

    next_columns = list(columns)
    next_names = dict(business_names)
    next_roles = dict(roles)
    next_target = target_col
    op = str(operation.get("op") or "")
    if op == "rename_columns":
        mapping = dict(operation["mapping"])  # type: ignore[arg-type]
        next_columns = [str(mapping.get(column, column)) for column in next_columns]
        for source, destination in mapping.items():
            source_name = str(source)
            destination_name = str(destination)
            if source_name in next_names:
                next_names[destination_name] = next_names.pop(source_name)
            if source_name in next_roles:
                next_roles[destination_name] = next_roles.pop(source_name)
            if next_target == source_name:
                next_target = destination_name
    elif op == "drop_columns":
        dropped = {str(column) for column in operation["columns"]}  # type: ignore[union-attr]
        next_columns = [column for column in next_columns if column not in dropped]
        for column in dropped:
            next_names.pop(column, None)
            next_roles.pop(column, None)
        if next_target in dropped:
            next_target = None
    elif op == "derive_columns":
        for derivation in operation["derivations"]:  # type: ignore[union-attr]
            name = str(derivation["name"])
            next_columns.append(name)
    if not next_columns:
        raise _NeedClarification("Deleting cannot remove all fields of the current data set.")
    if len(next_columns) != len(set(next_columns)):
        raise _NeedClarification("Data processing creates duplicate field names,Please rename or assign fields.")
    return tuple(next_columns), next_names, next_roles, next_target


def _referenced_columns(value: object) -> set[str]:
    if isinstance(value, Mapping):
        referenced = (
            {str(value["column"])} if "column" in value else set()
        )
        for item in value.values():
            referenced.update(_referenced_columns(item))
        return referenced
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        referenced: set[str] = set()
        for item in value:
            referenced.update(_referenced_columns(item))
        return referenced
    return set()


def _semantic_parts(
    semantic_mapping: object,
) -> tuple[Mapping[str, str], Mapping[str, str], str | None]:
    if isinstance(semantic_mapping, Mapping):
        names = semantic_mapping.get("business_names", {})
        roles = semantic_mapping.get("field_roles", {})
        target = semantic_mapping.get("target_col")
    else:
        names = getattr(semantic_mapping, "business_names", {})
        roles = getattr(semantic_mapping, "field_roles", {})
        target = getattr(semantic_mapping, "target_col", None)
    if not isinstance(names, Mapping) or not isinstance(roles, Mapping):
        raise _NeedClarification("Current data semantic map invalid,Please modify field configuration first.")
    return (
        {str(key): str(value) for key, value in names.items()},
        {str(key): str(value) for key, value in roles.items()},
        str(target) if target is not None else None,
    )


def _normalize_type(value: str) -> str:
    stripped = value.strip(" ,,.").strip()
    alias = _TYPE_ALIASES.get(stripped.casefold())
    normalized = alias or " ".join(stripped.upper().split())
    if not _SAFE_TYPE.fullmatch(normalized):
        raise _NeedClarification(f"Target type[{stripped}]Not on the security type white list..")
    decimal = re.fullmatch(r"DECIMAL\(([1-9]\d*),\s*(\d+)\)", normalized, re.I)
    if decimal:
        precision = int(decimal.group(1))
        scale = int(decimal.group(2))
        if precision > 38 or scale > precision:
            raise _NeedClarification("DECIMAL The precision must not exceed 38,and scale Cant be greater than precision.")
        return f"DECIMAL({precision},{scale})"
    return normalized


def _parse_literal(value: str) -> object:
    text = value.strip(" ,,.").strip()
    if not text:
        raise _NeedClarification("Compare value or fill value cannot be empty.")
    if (
        len(text) >= 2
        and text[0] == text[-1]
        and text[0] in {"'", '"', "`"}
    ):
        return text[1:-1]
    lowered = text.casefold()
    if lowered in {"null", "none", "Empty"}:
        return None
    if lowered in {"true", "Yes.", "True"}:
        return True
    if lowered in {"false", "Yes", "False"}:
        return False
    if re.fullmatch(r"[+-]?\d+", text):
        integer = int(text)
        if abs(integer) > _SAFE_INTEGER_MAX:
            raise _NeedClarification("Integer number exceeding accuracy JSON Scope,Please narrow down or change to control. DECIMAL Convert.")
        return integer
    if re.fullmatch(r"[+-]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?", text):
        number = float(text)
        if not math.isfinite(number):
            raise _NeedClarification("Value must be limited.")
        return number
    if re.search(r"(?:;|--|/\*|\*/|\bselect\b|\bimport\b|__)", text, re.I):
        raise _NeedClarification("Value contains unsupported codes or expressions,Please provide a general amount.")
    return text


def _clean_field_token(value: str) -> str:
    text = _unquote(str(value).strip())
    text = re.sub(r"^(?:Fields|Columns|Variables)\s*", "", text, flags=re.I)
    text = re.sub(r"^(?:column|field)\s+", "", text, flags=re.I)
    text = re.sub(r"\s*(?:Fields|Columns|Variables)$", "", text, flags=re.I)
    text = re.sub(r"\s+(?:column|field)$", "", text, flags=re.I)
    return text.strip()


def _split_field_list(value: str) -> list[str]:
    cleaned = value.strip(" ,,.").strip()
    cleaned = re.sub(r"\s*(?:Fields|Columns|Variables)\s*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+(?:columns?|fields?)\s*$", "", cleaned, flags=re.I)
    return [
        item.strip()
        for item in re.split(r"\s*(?:,|,|,|and|and|and|\band\b)\s*", cleaned, flags=re.I)
        if item.strip()
    ]


def _likely_unknown_field(text: str, resolver: _ColumnResolver) -> str | None:
    known = {column.casefold() for column in resolver.columns}
    reserved = {
        "fill",
        "missing",
        "with",
        "using",
        "impute",
        "cast",
        "to",
        "try",
        "strict",
        "mean",
        "median",
        "min",
        "max",
        "double",
        "integer",
        "varchar",
        "date",
        "timestamp",
    }
    for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
        lowered = token.casefold()
        if lowered not in known and lowered not in reserved:
            return token
    return None


def _unique_matches(text: str, patterns: Sequence[re.Pattern[str]]) -> list[re.Match[str]]:
    matches = [match for pattern in patterns for match in pattern.finditer(text)]
    unique: dict[tuple[int, int], re.Match[str]] = {}
    for match in matches:
        unique.setdefault(match.span(), match)
    return [unique[key] for key in sorted(unique)]


def _unquote(value: str) -> str:
    text = str(value).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"', "`"}:
        return text[1:-1]
    return text


def _clarify(message: str) -> DatasetTransformRequestResult:
    return DatasetTransformRequestResult(request=None, clarification=message)


__all__ = [
    "DatasetTransformRequest",
    "DatasetTransformRequestResult",
    "build_dataset_transform_request",
    "detect_dataset_transform_intent",
]
