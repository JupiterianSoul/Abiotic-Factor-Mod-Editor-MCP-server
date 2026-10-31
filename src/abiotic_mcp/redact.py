"""Removes secrets from editor log text before it is returned to a client."""

import re

_PATTERNS = [
    re.compile(r"(-AUTH_(?:LOGIN|PASSWORD)=)\S*", re.I),
    re.compile(r"(-epicusername=)(?:\"[^\"]*\"|\S*)", re.I),
    re.compile(r"(-epicuserid=)\S*", re.I),
    re.compile(r"(api_key=)[^\s&\"']*", re.I),
    re.compile(r"((?:access_|refresh_|auth_)?token[=: ]+)[^\s&\"',]*", re.I),
    re.compile(r"(exchange_?code[=: ]+)[^\s&\"',]*", re.I),
    re.compile(r"(Authorization: *(?:Bearer +)?)\S+", re.I),
]


def redact(text):
    for pattern in _PATTERNS:
        text = pattern.sub(r"\1REDACTED", text)
    return text
