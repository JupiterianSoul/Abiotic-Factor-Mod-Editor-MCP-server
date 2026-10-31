"""Reads Deep Field's Blueprint filter, the list of what mods may call.

Rule lines look like "Allow /Script/Engine.Actor" or
"Block /Script/Engine.Skeleton AddCompatibleSkeleton". The most specific
matching rule decides. The editor enforces the list itself: this module lets
the server check a symbol before generating Blueprint logic that uses it.
"""

import urllib.request

from . import paths

FILTER_URL = "https://cdn.abfmods.com/blueprint-filter/1.5/BlueprintFilter.txt"


def parse(text):
    rules = []
    version = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("# ContentVersion"):
            version = line.split()[-1]
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0] in ("Allow", "Block") and len(parts) >= 2:
            member = parts[2] if len(parts) > 2 else None
            rules.append((parts[0], parts[1], member))
    return version, rules


def load(refresh=True):
    """Fetch the current filter, falling back to the last downloaded copy."""
    if refresh:
        try:
            request = urllib.request.Request(FILTER_URL, headers={"User-Agent": "abiotic-mcp"})
            with urllib.request.urlopen(request, timeout=10) as response:
                text = response.read().decode("utf-8")
            paths.STATE_DIR.mkdir(parents=True, exist_ok=True)
            paths.FILTER_CACHE.write_text(text, encoding="utf-8")
            return parse(text)
        except OSError:
            pass
    try:
        return parse(paths.FILTER_CACHE.read_text(encoding="utf-8"))
    except OSError:
        raise RuntimeError("Blueprint filter unavailable: no network and no cached copy.") from None


def _matches(scope, target):
    return target == scope or target.startswith(scope + ".") or target.startswith(scope + "/")


def check(rules, target, member=None):
    """Return the deciding rule for a class or module path and optional function."""
    best = None
    best_score = (-1, -1)
    for action, scope, rule_member in rules:
        if not _matches(scope, target):
            continue
        if rule_member is not None and rule_member != member:
            continue
        score = (1 if rule_member else 0, len(scope))
        if score >= best_score:
            best, best_score = (action, scope, rule_member), score
    if best is None:
        return {"verdict": "not_listed", "rule": None}
    return {
        "verdict": "allowed" if best[0] == "Allow" else "blocked",
        "rule": " ".join(part for part in best if part),
    }
