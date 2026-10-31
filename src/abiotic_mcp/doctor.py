"""Diagnostics for 'abiotic-mcp doctor'."""

import sys

from . import TESTED_EDITOR_VERSION, TESTED_ENGINE_PREFIX, installer, paths
from .bridge import Bridge, EditorCommandError, EditorNotConnected


def _report(ok, label, fix=""):
    print("[{}] {}".format("ok" if ok else "!!", label))
    if fix and not ok:
        print("     fix: {}".format(fix))
    return ok


def run():
    healthy = _report(
        sys.version_info >= (3, 10),
        "Python {}.{}".format(*sys.version_info[:2]),
        "Install Python 3.10 or newer, or use uv.",
    )
    install_dir, version = paths.find_editor()
    healthy &= _report(
        install_dir is not None,
        "Mod Editor at {}".format(install_dir),
        "Install the Abiotic Factor Mod Editor from the Epic Games Launcher, or set "
        "editor_dir in {}.".format(paths.CONFIG_FILE),
    )
    if version and not version.startswith(TESTED_EDITOR_VERSION):
        print("[warn] Editor version {} is untested (tested with {}).".format(version, TESTED_EDITOR_VERSION))

    script = paths.startup_script()
    installed = (
        script.exists()
        and installer.BEGIN in script.read_text(encoding="utf-8")
        and (paths.EDITOR_DIR / "abiotic_listener.py").exists()
    )
    healthy &= _report(installed, "Startup script at {}".format(script), "Run: abiotic-mcp install")

    try:
        status = Bridge(timeout=10).call("status")
    except (EditorNotConnected, EditorCommandError) as exc:
        return _report(False, "Editor reachable on localhost", str(exc)) and healthy
    _report(True, "Editor reachable, engine {}".format(status["engine_version"]))
    if not status["engine_version"].startswith(TESTED_ENGINE_PREFIX):
        print("[warn] Engine {} is untested (tested with {}.x).".format(status["engine_version"], TESTED_ENGINE_PREFIX))
    healthy &= _report(
        status["active_mod"] is not None,
        "Open mod: {}".format(status["active_mod"]),
        "Load a mod project in the Mod Browser.",
    )
    return healthy
