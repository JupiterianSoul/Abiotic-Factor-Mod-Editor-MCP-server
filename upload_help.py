"""Explain upload failures from editor log lines. The panel's own errors are usually generic."""

import json
import re

# (what to look for in the log, what it means, what to do)
KNOWN = [
    (r'"logo"|invalid image dimensions', "mod.io rejected the listing image.",
     "Use a 16:9 PNG or JPEG, at least 512x288 and under 8 MB. make_listing_image can create one."),
    (r"29200|Unknown ApiError", "mod.io rejected a file in the mod folder. A .md file is the usual cause.",
     "Run check_upload, and remove what it lists. Upload zips the whole mod folder."),
    (r'"(?:name|summary|name_id)"[^}]*(?:required|invalid|taken|exceed)', "mod.io rejected the name or summary.",
     "Check the error text. The summary is limited to 250 characters, and names must be unique."),
    (r"response code 401|\b11005\b|not authenticated|Unauthorized|User is not authenticated", "The editor isn't logged in to mod.io.",
     "Restart the editor and log in to mod.io when it starts, not only to Epic."),
    (r"response code 403|\b15023\b|permission", "This mod.io account can't change that mod.",
     "Check the mod ID, and that you're logged in with the account that owns the mod."),
    (r"response code 413|too large|exceeds the maximum", "The upload is too large.",
     "Remove what you don't need from the mod folder. check_upload shows its size."),
    (r"Override target row", "An override row points at a base-game row that doesn't exist.",
     "Fix its row name, or turn off override_existing_row. check_mod_rows lists overrides."),
    (r"Global Static Switch", "A material changes Global Static Switch Parameter Values, which breaks console cooks.",
     "Start from a material that already has the feature enabled."),
    (r"collides with an already-registered mod row", "Two rows in the mod share a name.",
     "check_mod_rows lists them. Rename one."),
    (r"(?i)blueprint filter|not allowed in mods|blocked", "A Blueprint uses something the upload filter blocks.",
     "blueprint_filter_check lists each blocked call and its node."),
]
_ERROR_LINE = re.compile(r"\[Error\]|Warning: ModioErrorCode|response code [45]\d\d|AssetCheck: Error|\"error\"\s*:", re.I)


def explain(lines):
    """Pick out the failure lines, and match them against known causes."""
    errors = [x for x in lines if _ERROR_LINE.search(x) and "Raw MS filesystem error" not in x]
    found = []
    for pattern, cause, fix in KNOWN:
        rx = re.compile(pattern, re.I)
        match = next((x for x in errors if rx.search(x)), None)
        if match:
            found.append({"cause": cause, "fix": fix})
    return {"causes": found, "error_lines": errors[-15:],
            "note": "Nothing matched a known cause. Read error_lines." if errors and not found else
                    ("No upload errors in this part of the log." if not errors else "")}


def to_json(lines):
    return json.dumps(explain(lines), indent=2)
