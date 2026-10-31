"""Write guards from the editor-side code, with the unreal module stubbed out."""

import importlib
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "abiotic_mcp" / "editor_side"))
sys.modules.setdefault("unreal", types.ModuleType("unreal"))
commands = importlib.import_module("abiotic_commands")


@pytest.fixture(autouse=True)
def active_mod(monkeypatch):
    monkeypatch.setattr(commands, "_active_mod", lambda: "MyMod")
    monkeypatch.setattr(commands, "_config", lambda: {"protected_mods": ["Locked"]})


@pytest.mark.parametrize("path", ["/MyMod", "/MyMod/DataTables/DT_Recipes/row"])
def test_paths_inside_active_mod_are_writable(path):
    assert commands._require_writable(path) == "MyMod"


@pytest.mark.parametrize(
    "path",
    [
        "/Game/Items/x",
        "/Other/x",
        "/MyModEvil/x",
        "/MyMod/../Game/x",
        "/MyMod/DataTables/../../Game/x",
        "/MyMod/./x",
        "/MyMod//x",
        "/MyMod/a\\..\\b",
    ],
)
def test_paths_outside_active_mod_are_refused(path):
    with pytest.raises(PermissionError):
        commands._require_writable(path)


def test_protected_mod_is_refused(monkeypatch):
    monkeypatch.setattr(commands, "_active_mod", lambda: "Locked")
    with pytest.raises(PermissionError, match="protected"):
        commands._require_writable("/Locked/x")


@pytest.mark.parametrize("name", ["../x", "a/b", "a\\b", "", "a b", "a.b"])
def test_bad_asset_names_are_refused(name):
    with pytest.raises(ValueError):
        commands._require_asset_name(name)


def test_good_asset_name():
    commands._require_asset_name("recipe_mcp-new_2")
