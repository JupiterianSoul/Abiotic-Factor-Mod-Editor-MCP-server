"""Tests for everything that runs outside the editor."""

import json
import socket
import threading

import pytest

from abiotic_mcp import blueprint_filter, installer, paths
from abiotic_mcp.bridge import Bridge, EditorCommandError, EditorNotConnected
from abiotic_mcp.redact import redact

FILTER = """# ABF-BlueprintFilter 1
# ContentVersion 123
Block /Script/Engine
Allow /Script/Engine.Actor
Block /Script/Engine.Skeleton AddCompatibleSkeleton
Allow /Script/Engine.Skeleton
"""


def test_filter_most_specific_rule_wins():
    version, rules = blueprint_filter.parse(FILTER)
    assert version == "123"
    assert blueprint_filter.check(rules, "/Script/Engine.GameMode")["verdict"] == "blocked"
    assert blueprint_filter.check(rules, "/Script/Engine.Actor")["verdict"] == "allowed"
    assert blueprint_filter.check(rules, "/Script/Engine.Skeleton", "Other")["verdict"] == "allowed"
    assert blueprint_filter.check(rules, "/Script/Engine.Skeleton", "AddCompatibleSkeleton")["verdict"] == "blocked"
    assert blueprint_filter.check(rules, "/Script/EngineExtra.Thing")["verdict"] == "not_listed"


def test_redact_removes_secrets():
    line = (
        '-AUTH_LOGIN=unused -AUTH_PASSWORD=abc123 -epicusername="Some Name" '
        "GET /v1/me?api_key=deadbeef&x=1 access_token=secret Authorization: Bearer xyz"
    )
    cleaned = redact(line)
    for secret in ("abc123", "Some Name", "deadbeef", "secret", "xyz"):
        assert secret not in cleaned
    assert "x=1" in cleaned


def test_strip_block_keeps_user_code():
    text = "print('mine')\n\n" + installer.BEGIN + "\ncode\n" + installer.END + "\nprint('after')\n"
    assert installer.strip_block(text) == "print('mine')\n\nprint('after')"
    assert installer.strip_block("no block") == "no block"


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    state = tmp_path / "state"
    monkeypatch.setattr(paths, "STATE_DIR", state)
    monkeypatch.setattr(paths, "EDITOR_DIR", state / "editor")
    monkeypatch.setattr(paths, "SESSION_FILE", state / "session.json")
    monkeypatch.setattr(paths, "CONFIG_FILE", state / "config.json")
    monkeypatch.setattr(paths, "documents_dir", lambda: tmp_path / "docs")
    return tmp_path


def test_install_and_uninstall_leave_nothing_behind(isolated):
    installer.install()
    script = paths.startup_script()
    assert installer.BEGIN in script.read_text(encoding="utf-8")
    assert (paths.EDITOR_DIR / "abiotic_listener.py").exists()
    installer.install()
    assert script.read_text(encoding="utf-8").count(installer.BEGIN) == 1
    installer.uninstall()
    assert not script.exists()
    assert not paths.STATE_DIR.exists()
    assert not (isolated / "docs" / "UnrealEngine").exists()


def test_uninstall_preserves_existing_startup_script(isolated):
    script = paths.startup_script()
    script.parent.mkdir(parents=True)
    script.write_text("print('mine')\n", encoding="utf-8")
    installer.install()
    installer.uninstall()
    assert script.read_text(encoding="utf-8") == "print('mine')\n"


def test_bridge_without_session_gives_clear_message(isolated):
    with pytest.raises(EditorNotConnected, match="Open the Abiotic Factor Mod Editor"):
        Bridge().call("status")


def _serve_once(server, reply):
    conn, _ = server.accept()
    with conn:
        conn.recv(65536)
        conn.sendall(json.dumps(reply).encode() + b"\n")


@pytest.mark.parametrize(
    "reply,expected",
    [({"id": 1, "ok": True, "result": {"a": 1}}, {"a": 1}), ({"id": 1, "ok": False, "error": "boom"}, None)],
)
def test_bridge_round_trip(isolated, reply, expected):
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    threading.Thread(target=_serve_once, args=(server, reply), daemon=True).start()
    paths.STATE_DIR.mkdir(parents=True)
    paths.SESSION_FILE.write_text(json.dumps({"port": server.getsockname()[1], "token": "t"}), encoding="utf-8")
    try:
        if expected is None:
            with pytest.raises(EditorCommandError, match="boom"):
                Bridge(timeout=5).call("x")
        else:
            assert Bridge(timeout=5).call("x") == expected
    finally:
        server.close()
