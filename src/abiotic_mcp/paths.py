"""Locations used by the server. Everything we write lives in the user's profile."""

import ctypes
import glob
import json
import os
from pathlib import Path

STATE_DIR = Path.home() / ".abiotic-mcp"
EDITOR_DIR = STATE_DIR / "editor"
SESSION_FILE = STATE_DIR / "session.json"
CONFIG_FILE = STATE_DIR / "config.json"
FILTER_CACHE = STATE_DIR / "BlueprintFilter.txt"

EPIC_MANIFESTS = r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests\*.item"
FALLBACK_INSTALL_GLOBS = [
    r"C:\Program Files\Epic Games\AbioticFactorModEdit*",
    r"D:\Epic Games\AbioticFactorModEdit*",
    r"D:\Program Files\Epic Games\AbioticFactorModEdit*",
]
EDITOR_EXE = Path("AbioticFactor/Binaries/Win64/AbioticFactorEditorCooked-Win64-Test.exe")


def load_config():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def documents_dir():
    """The real Documents folder, which OneDrive may have moved."""
    if os.name == "nt":
        buffer = ctypes.create_unicode_buffer(260)
        # CSIDL_PERSONAL = 5, SHGFP_TYPE_CURRENT = 0
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:
            return Path(buffer.value)
    return Path.home() / "Documents"


def startup_script():
    return documents_dir() / "UnrealEngine" / "Python" / "init_unreal.py"


def mods_dir():
    configured = load_config().get("mods_dir")
    return Path(configured) if configured else documents_dir() / "Abiotic Factor Mods"


def log_file():
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local) / "AbioticFactor" / "Saved" / "Logs" / "AbioticFactor.log"


def find_editor():
    """Return (install_dir, version), or (None, None) if the editor is not found."""
    configured = load_config().get("editor_dir")
    if configured and (Path(configured) / EDITOR_EXE).exists():
        return Path(configured), None
    for manifest in glob.glob(EPIC_MANIFESTS):
        try:
            data = json.loads(Path(manifest).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("DisplayName") == "Abiotic Factor Mod Editor":
            location = Path(data.get("InstallLocation", ""))
            if (location / EDITOR_EXE).exists():
                return location, data.get("AppVersionString")
    for pattern in FALLBACK_INSTALL_GLOBS:
        for candidate in glob.glob(pattern):
            if (Path(candidate) / EDITOR_EXE).exists():
                return Path(candidate), None
    return None, None
