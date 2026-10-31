"""Localhost command listener that runs inside the Abiotic Factor Mod Editor.

Connections are handled on background threads, but every command runs on the
editor's main thread through a Slate tick callback, because the unreal API is
not thread safe. Uses only the standard library and the embedded unreal module.
"""

import importlib
import json
import os
import queue
import secrets
import socket
import sys
import threading
import traceback

import unreal

PROTOCOL_VERSION = 1
DEFAULT_PORT = 47821
MAX_REQUEST_BYTES = 16 * 1024 * 1024
HOST = "127.0.0.1"


def state_dir():
    return os.path.join(os.path.expanduser("~"), ".abiotic-mcp")


def session_path():
    return os.path.join(state_dir(), "session.json")


class _Job:
    def __init__(self, request):
        self.request = request
        self.response = None
        self.done = threading.Event()


class Listener:
    def __init__(self, port):
        self.port = port
        self.token = secrets.token_urlsafe(32)
        self.jobs = queue.Queue()
        self.running = True
        self.sock = None
        self.tick_handle = None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((HOST, self.port))
        self.sock.listen(8)
        self.tick_handle = unreal.register_slate_post_tick_callback(self._tick)
        threading.Thread(target=self._accept_loop, daemon=True).start()
        self._write_session()
        unreal.log("abiotic-mcp: listening on {}:{}".format(HOST, self.port))

    def stop(self):
        self.running = False
        if self.tick_handle is not None:
            unreal.unregister_slate_post_tick_callback(self.tick_handle)
            self.tick_handle = None
        if self.sock is not None:
            self.sock.close()
            self.sock = None
        try:
            os.remove(session_path())
        except OSError:
            pass

    def _write_session(self):
        os.makedirs(state_dir(), exist_ok=True)
        tmp = session_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "port": self.port,
                    "token": self.token,
                    "pid": os.getpid(),
                    "protocol": PROTOCOL_VERSION,
                },
                f,
            )
        os.replace(tmp, session_path())

    def _accept_loop(self):
        while self.running:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn):
        with conn:
            buffer = b""
            while self.running:
                try:
                    chunk = conn.recv(65536)
                except OSError:
                    return
                if not chunk:
                    return
                buffer += chunk
                if len(buffer) > MAX_REQUEST_BYTES:
                    return
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    response = self._handle_line(line)
                    try:
                        conn.sendall(json.dumps(response).encode("utf-8") + b"\n")
                    except OSError:
                        return

    def _handle_line(self, line):
        try:
            request = json.loads(line)
        except ValueError:
            return {"id": None, "ok": False, "error": "Invalid JSON"}
        request_id = request.get("id")
        if not secrets.compare_digest(str(request.get("token", "")), self.token):
            return {"id": request_id, "ok": False, "error": "Invalid token"}
        job = _Job(request)
        self.jobs.put(job)
        # The client applies its own timeout. Waiting here is safe because a
        # modal dialog in the editor only delays the tick, it does not lose it.
        while self.running:
            if job.done.wait(1.0):
                return job.response
        return {"id": request_id, "ok": False, "error": "Listener stopped"}

    def _tick(self, _delta):
        try:
            job = self.jobs.get_nowait()
        except queue.Empty:
            return
        request = job.request
        response = {"id": request.get("id")}
        try:
            result = self._dispatch(request.get("cmd"), request.get("args") or {})
            # Serialize here so a bad value is reported instead of dropping the connection.
            json.dumps(result)
            response.update(ok=True, result=result)
        except Exception as exc:
            response.update(
                ok=False,
                error="{}: {}".format(type(exc).__name__, exc),
                traceback=traceback.format_exc(),
            )
        job.response = response
        job.done.set()

    def _dispatch(self, cmd, args):
        if cmd == "ping":
            return {"protocol": PROTOCOL_VERSION, "pid": os.getpid()}
        if cmd == "reload":
            importlib.reload(_commands())
            return {"reloaded": True}
        handler = getattr(_commands(), "cmd_" + str(cmd), None)
        if handler is None:
            raise ValueError("Unknown command: {}".format(cmd))
        return handler(**args)


def _commands():
    import abiotic_commands

    return abiotic_commands


def start(port=None):
    """Start the listener, replacing any instance left by an earlier run."""
    previous = getattr(sys, "_abiotic_mcp_listener", None)
    if previous is not None:
        previous.stop()
    if port is None:
        port = int(os.environ.get("ABIOTIC_MCP_PORT", DEFAULT_PORT))
    listener = Listener(port)
    listener.start()
    sys._abiotic_mcp_listener = listener
    return listener
