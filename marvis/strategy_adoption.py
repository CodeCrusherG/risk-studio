"""Shared validation for evidence-bound strategy adoption reasons.

The plan may carry an empty string while it is waiting at the adoption gate, but
that pending value is never a valid business decision.  Both the gate path and
the persistence/tool boundaries use this module so a direct invocation cannot
turn a blank or placeholder into an adopted strategy.
"""

from __future__ import annotations

import re


class AdoptionReasonError(ValueError):
    """Raised when a strategy adoption reason is not a real business reason."""


ADOPTION_REASON_MIN_LENGTH = 2
_PLACEHOLDER_KEY_RE = re.compile(r"[\s()()\[\][]<><>::,,..!!??_\-/\\]+")
_PLACEHOLDER_KEYS = frozenset({
    "todo",
    "todoTo be confirmed",
    "tbd",
    "pending",
    "pendingapproval",
    "pendingconfirmation",
    "placeholder",
    "na",
    "none",
    "null",
    "Placed",
    "Placeholder",
    "To be confirmed",
    "Confirmed pending adoption",
    "To be completed",
    "To be completed",
})
_PLACEHOLDER_PREFIXES = (
    "todo",
    "tbd",
    "pending",
    "placeholder",
    "Placed",
    "To be confirmed",
    "Pending",
    "To be completed",
    "To be completed",
)


def normalize_adoption_reason(value: object) -> str:
    """Return a trimmed adoption reason or fail closed on pending placeholders."""

    if not isinstance(value, str):
        raise AdoptionReasonError("The reasons for adoption must be non-empty text and not be available for confirmation of position.")
    reason = value.strip()
    if not reason:
        raise AdoptionReasonError("The reasons for adoption cannot be empty and cannot be used for the status to be confirmed.")
    if len(reason) < ADOPTION_REASON_MIN_LENGTH:
        raise AdoptionReasonError(
            f"At least it's a reason to accept.{ADOPTION_REASON_MIN_LENGTH} a character."
        )
    placeholder_key = _PLACEHOLDER_KEY_RE.sub("", reason).casefold()
    if (
        not placeholder_key
        or placeholder_key in _PLACEHOLDER_KEYS
        or any(placeholder_key.startswith(prefix) for prefix in _PLACEHOLDER_PREFIXES)
    ):
        raise AdoptionReasonError(
            "Reasons for admission cannot be used pending confirmation,TODO,pending or other placeholder text."
        )
    return reason


def is_valid_adoption_reason(value: object) -> bool:
    """Cheap predicate for gate rendering/guards without duplicating policy."""

    try:
        normalize_adoption_reason(value)
    except AdoptionReasonError:
        return False
    return True


__all__ = [
    "ADOPTION_REASON_MIN_LENGTH",
    "AdoptionReasonError",
    "is_valid_adoption_reason",
    "normalize_adoption_reason",
]
