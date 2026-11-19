"""Guarded, intentionally narrow local action request semantics.

This is not an autonomous agent tool registry. It exposes one reversible
local operation that requires an authenticated administrator click.
"""

from __future__ import annotations

import hashlib
import time

ACTION_TTL_SECONDS = 10 * 60
MAX_NOTE_LENGTH = 4000
MAX_PENDING_ACTIONS = 20
MAX_SAVED_NOTES = 100


class ActionConflict(Exception):
    """A proposed action cannot transition to the requested state."""


def validate_note(value: object) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= MAX_NOTE_LENGTH:
        raise ValueError("Note must contain 1–4000 characters")
    return value.strip()


def note_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_seconds() -> int:
    return int(time.time())
