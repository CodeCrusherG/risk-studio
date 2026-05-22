"""Utilities for normalizing LLM JSON replies."""

from __future__ import annotations

import json
import re
from typing import Any


_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_OPEN_THINK_RE = re.compile(r"<think>.*\Z", re.IGNORECASE | re.DOTALL)
_POSITIVE_DECISION_REJECTION_PATTERNS = (
    re.compile(
        r"(?:Reject|I disagree.|Not approved|Not accepted|I can't pass.|No way.|Rejected|Rejected.|Refusal|Objection.|"
        r"(?:Not yet|Not yet.|Not|Not yet.)(?:Delegation of authority|Approval|Agreed.|Confirm.|Audit|Review))",
    ),
    re.compile(
        r"(?:No, I can't.|Cannot|No way.|No, I shouldn't.(?:The)?|Don't.|Ban|Reject|I disagree.)"
        r".{0,8}(?:Confirm.|Go on.|Implementation|Pass.|Accepted|Approval)",
    ),
    re.compile(
        r"(?:Confirm.|Go on.|Implementation|Pass.|Accepted|Approval)"
        r".{0,6}(?:No, I'm fine.|No way.|No way.|Ban|Reject)",
    ),
    re.compile(
        r"\b(?:cannot|can't|must\s+not|should\s+not|do\s+not|reject|disagree)"
        r".{0,24}\b(?:confirm|continue|proceed|execute|pass|adopt|approve)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:no|nope|nah)\s*[.!?.!?]?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:decline|reject(?:ed|ing)?|not\s+acceptable|"
        r"unauthori[sz]ed|not\s+authori[sz]ed|not\s+approved|approval\s+pending)\b",
        re.IGNORECASE,
    ),
)


def strip_thinking(text: str) -> str:
    """Remove paired <think>...</think> blocks (and a trailing unclosed one).

    An unclosed <think> at the very end of a *complete* reply means the model
    never emitted an answer after it, so dropping from the open tag to the end
    is safe for the final-content case this is used in.
    """
    if not text:
        return text
    stripped = _THINK_BLOCK_RE.sub("", text)
    if "<think>" in stripped.lower():
        stripped = _OPEN_THINK_RE.sub("", stripped)
    return stripped


def load_json_object(raw: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Load a JSON object from a strict or lightly wrapped LLM reply."""
    if isinstance(raw, dict):
        return raw, None
    if not isinstance(raw, str):
        return None, "reply is not text"
    text = strip_thinking(raw).strip()
    candidates = [text]
    last_object = _extract_last_object(text)
    if last_object and last_object not in candidates:
        candidates.append(last_object)
    first_object = _extract_first_object(text)
    if first_object and first_object not in candidates:
        candidates.append(first_object)
    last_error = "no JSON object found"
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except (RecursionError, TypeError, ValueError) as exc:
            last_error = str(exc)
            continue
        if isinstance(data, dict):
            return data, None
        last_error = "JSON value is not an object"
    return None, last_error


def rejects_positive_decision(value: Any) -> bool:
    """Whether explanatory text explicitly rejects a positive action."""

    text = str(value or "").strip()
    return bool(text) and any(
        pattern.search(text)
        for pattern in _POSITIVE_DECISION_REJECTION_PATTERNS
    )


def _extract_first_object(text: str) -> str | None:
    start = text.find("{")
    while start >= 0:
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(text)):
            char = text[idx]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]
        start = text.find("{", start + 1)
    return None


def _extract_last_object(text: str) -> str | None:
    """Return the last top-level balanced ``{...}`` block, or ``None``."""
    last: str | None = None
    start = text.find("{")
    while start >= 0:
        depth = 0
        in_string = False
        escape = False
        end = -1
        for idx in range(start, len(text)):
            char = text[idx]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = idx
                    break
        if end >= 0:
            last = text[start:end + 1]
            start = text.find("{", end + 1)
        else:
            start = text.find("{", start + 1)
    return last


__all__ = ["load_json_object", "rejects_positive_decision", "strip_thinking"]
