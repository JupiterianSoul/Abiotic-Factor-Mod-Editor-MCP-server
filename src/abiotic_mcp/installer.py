"""Installs the editor-side scripts into the user's profile. Needs no admin rights."""

import json
import shutil
import sys
from importlib import resources

from . import paths

BEGIN = "# BEGIN abiotic-mcp (managed block, remove with: abiotic-mcp uninstall)"
END = "# END abiotic-mcp"
EDITOR_FILES = ("abiotic_listener.py", "abiotic_commands.py", "start_listener.py")


def _block():
    script = (paths.EDITOR_DIR / "start_listener.py").as_posix()
    # The startup path is shared by every Unreal Editor on this PC, so the
    # listener only starts inside the Abiotic Factor Mod Editor.
    return "\n".join(
        [
            BEGIN,
            "import unreal as _abiotic_unreal",
            'if _abiotic_unreal.SystemLibrary.get_game_name() == "AbioticFactor":',
            "    import runpy as _abiotic_runpy",
            "    _abiotic_runpy.run_path({!r})".format(script),
            END,
            "",
        ]
    )


def strip_block(text):
    start = text.find(BEGIN)
    if start < 0:
        return text
    end = text.find(END, start)
    if end < 0:
        return text
    return (text[:start] + text[end + len(END) :].lstrip("\r\n")).strip("\r\n")


def install():
    paths.EDITOR_DIR.mkdir(parents=True, exist_ok=True)
    source = resources.files("abiotic_mcp") / "editor_side"
    for name in EDITOR_FILES:
        (paths.EDITOR_DIR / name).write_text((source / name).read_text(encoding="utf-8"), encoding="utf-8")

    script = paths.startup_script()
    script.parent.mkdir(parents=True, exist_ok=True)
    existing = strip_block(script.read_text(encoding="utf-8")) if script.exists() else ""
    prefix = existing + "\n\n" if existing else ""
    script.write_text(prefix + _block(), encoding="utf-8")
    print("Installed editor scripts to {}".format(paths.EDITOR_DIR))
    print("Added startup block to {}".format(script))


def uninstall():
    script = paths.startup_script()
    if script.exists():
        remaining = strip_block(script.read_text(encoding="utf-8"))
        if remaining:
            script.write_text(remaining + "\n", encoding="utf-8")
        else:
            script.unlink()
            for folder in (script.parent, script.parent.parent):
                try:
                    folder.rmdir()
                except OSError:
                    break
        print("Removed startup block from {}".format(script))
    if paths.STATE_DIR.exists():
        shutil.rmtree(paths.STATE_DIR)
        print("Removed {}".format(paths.STATE_DIR))
    print("Restart the Mod Editor if it is open. Mod projects were not changed.")


def client_config():
    command = shutil.which("abiotic-mcp") or sys.argv[0]
    return json.dumps({"mcpServers": {"abiotic": {"command": command, "args": ["serve"]}}}, indent=2)
