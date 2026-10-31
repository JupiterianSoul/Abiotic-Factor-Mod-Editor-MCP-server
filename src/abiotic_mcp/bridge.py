"""Client for the listener running inside the Mod Editor."""

import itertools
import json
import socket

from . import paths

HOST = "127.0.0.1"
OPEN_EDITOR_HINT = (
    "Open the Abiotic Factor Mod Editor and load a mod project, then retry. "
    "If it is already open, restart it once after running 'abiotic-mcp install', "
    "or run 'abiotic-mcp doctor'."
)


class EditorNotConnected(RuntimeError):
    pass


class EditorCommandError(RuntimeError):
    pass


class Bridge:
    def __init__(self, timeout=120.0):
        self.timeout = timeout
        self._ids = itertools.count(1)

    def _session(self):
        try:
            return json.loads(paths.SESSION_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise EditorNotConnected(OPEN_EDITOR_HINT) from None

    def call(self, command, **args):
        session = self._session()
        request = {"id": next(self._ids), "token": session["token"], "cmd": command, "args": args}
        try:
            with socket.create_connection((HOST, session["port"]), timeout=self.timeout) as conn:
                conn.sendall(json.dumps(request).encode("utf-8") + b"\n")
                reply = self._read_line(conn)
        except socket.timeout:
            raise EditorCommandError(
                "The editor did not answer in time. Close any open dialog in the editor, then retry."
            ) from None
        except OSError:
            raise EditorNotConnected(OPEN_EDITOR_HINT) from None
        response = json.loads(reply)
        if not response.get("ok"):
            raise EditorCommandError(response.get("error", "Unknown editor error"))
        return response["result"]

    @staticmethod
    def _read_line(conn):
        chunks = []
        while True:
            chunk = conn.recv(1 << 20)
            if not chunk:
                raise OSError("Connection closed")
            chunks.append(chunk)
            if b"\n" in chunk:
                return b"".join(chunks)
