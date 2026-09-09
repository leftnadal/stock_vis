"""Shared redaction boundary for persisted DailyPrice diagnostic errors.

Only synthetic credentials belong in tests. This is a log hygiene boundary,
not a claim that arbitrary free text can be proved to contain no secrets.
"""

from __future__ import annotations

import os
import re
from typing import Any, Mapping
from urllib.parse import quote, unquote, urlsplit


_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:password|passwd|pwd|db_password|pgpassword|secret|token|api_key)"
    r"\b\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_URI_CREDENTIALS = re.compile(r"(?i)([a-z][a-z0-9+.-]*://)[^\s/@]+@")


def redact_error_message(
    message: str, environment: Mapping[str, str] | None = None
) -> str:
    environment = os.environ if environment is None else environment
    secrets = {
        environment[key]
        for key in ("DB_PASSWORD", "PGPASSWORD")
        if environment.get(key)
    }
    for key in ("DATABASE_URL", "DB_URL"):
        try:
            password = urlsplit(environment.get(key, "")).password
        except ValueError:
            password = None
        if password:
            secrets.update((password, unquote(password)))
    variants = secrets | {quote(value, safe="") for value in secrets}
    redacted = message
    for secret in sorted(variants, key=len, reverse=True):
        redacted = redacted.replace(secret, "[REDACTED]")
    redacted = _URI_CREDENTIALS.sub(r"\1[REDACTED]@", redacted)
    return _ASSIGNMENT.sub(r"\1[REDACTED]", redacted)


def redact_persisted_errors(value: Any, *, in_error: bool = False) -> Any:
    """Copy an artifact, sanitizing every string in diagnostic error subtrees.

    A final serialization boundary also covers errors appended by callers after
    the probe returned. Ordinary observation payloads and their hashes are not
    rewritten; callers must not place credentials in research data.
    """
    if isinstance(value, dict):
        return {
            key: redact_persisted_errors(
                item,
                in_error=in_error or key in {
                    "failures", "failure", "errors", "error", "exception",
                    "exceptions", "error_message", "message",
                },
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_persisted_errors(item, in_error=in_error) for item in value]
    if in_error and isinstance(value, str):
        return redact_error_message(value)
    return value
