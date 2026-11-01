"""Checks shared by the write tools and the log reader. No editor or Windows calls, so they can be tested offline."""

import re

MASK = "<hidden>"
# Content roots a mod must never write to. Unreal treats package paths as case-insensitive.
BASE_ROOTS = ("game", "engine", "script", "temp", "memory")

_FIELD = (r"[A-Za-z_\-]*(?:key|token|secret|password|passwd|auth|code|session|email|user_?id|user_?name|login|credential)"
          r"[A-Za-z_\-]*")
_RULES = [
    (re.compile(r"(https?://[^\s?\"']+)\?[^\s\"']*"), lambda m: m.group(1) + "?" + MASK),
    (re.compile(r"(?i)\b(bearer|basic)\s+\S+"), lambda m: m.group(1) + " " + MASK),
    (re.compile(r"""(?ix)(["']?\b""" + _FIELD + r"""\b["']?\s*(?:=|:)\s*)("[^"]*"|'[^']*'|[^\s,;&}\])]+)"""),
     lambda m: m.group(0) if _harmless(m.group(2)) else m.group(1) + MASK),
    (re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+"), lambda m: MASK),
    (re.compile(r"\b[A-Fa-f0-9]{16,}\b"), lambda m: MASK),
    (re.compile(r"(?<![/\\\w.])[A-Za-z0-9_\-]{24,}(?:\.[A-Za-z0-9_\-]+){0,2}(?![/\\\w])"), lambda m: MASK),
]
_CATEGORY = re.compile(r"^(?:\[[^\]]*\])*Log\w+: (?:\w+: )?")


def _harmless(value):
    """Short numbers such as HTTP or mod.io error codes help with debugging and aren't secret."""
    return value.isdigit() and len(value) <= 6


def redact(line):
    """Hide auth codes, API keys and account details in one log line."""
    head = _CATEGORY.match(line)
    head = head.group(0) if head else ""
    body = line[len(head):]
    for rx, repl in _RULES:
        body = rx.sub(repl, body)
    return head + body


def base_path_problem(path):
    """Why a package path may not be written to, or None if it's fine. Mods live at /<ModRoot>/..."""
    text = str(path or "").strip()
    if "\\" in text or not text.startswith("/"):
        return f"'{text}' is not a content path like /MyMod/Folder/Asset"
    parts = text.split("/")[1:]
    if any(part in ("", ".", "..") for part in parts):
        return f"'{text}' is not a plain content path"
    if parts[0].lower() in BASE_ROOTS:
        return f"'{text}' is base-game or engine content, which mods can't change"
    return None
