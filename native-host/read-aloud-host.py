#!/usr/bin/env python3
"""Chrome/Brave native messaging host — forwards speak/stop to the warm speak daemon.

Chrome talks to this process over stdin/stdout using the native messaging
length-prefixed JSON protocol. We reply quickly, then the daemon does the
actual TTS so Chrome does not time out waiting for audio to finish.
"""

from __future__ import annotations

import json
import os
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DAEMON = Path(__file__).resolve().parent / "speak-daemon.py"
CACHE = Path.home() / ".cache/read-aloud"
SOCK = CACHE / "speak.sock"
PYTHON = APP_DIR / "venv" / "bin" / "python"


def read_message() -> dict | None:
    """Read one native-messaging frame from Chrome (4-byte LE length + JSON)."""
    raw_len = sys.stdin.buffer.read(4)
    if not raw_len:
        return None
    (length,) = struct.unpack("<I", raw_len)
    data = sys.stdin.buffer.read(length)
    if not data:
        return None
    return json.loads(data.decode("utf-8"))


def send_message(payload: dict) -> None:
    """Write one native-messaging frame back to Chrome."""
    encoded = json.dumps(payload).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def ensure_daemon() -> None:
    """Start speak-daemon if needed (first right-click after reboot)."""
    if _ping():
        return
    CACHE.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PATH"] = str(Path.home() / ".local/bin") + os.pathsep + env.get("PATH", "")
    subprocess.Popen(
        [str(PYTHON), str(DAEMON)],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    for _ in range(40):
        if _ping():
            return
        time.sleep(0.05)
    raise RuntimeError("Speak daemon failed to start")


def _ping() -> bool:
    try:
        resp = _send_daemon({"action": "ping"}, timeout=0.2)
        return bool(resp.get("ok"))
    except OSError:
        return False


def _send_daemon(msg: dict, timeout: float = 2.0) -> dict:
    payload = (json.dumps(msg) + "\n").encode("utf-8")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect(str(SOCK))
        sock.sendall(payload)
        data = b""
        while not data.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    if not data:
        return {"ok": False, "error": "No response from speak daemon"}
    return json.loads(data.decode("utf-8"))


def main() -> None:
    msg = read_message()
    if not msg:
        return
    try:
        ensure_daemon()
        action = msg.get("action") or "speak"
        if action == "stop":
            resp = _send_daemon({"action": "stop"})
        else:
            resp = _send_daemon(msg, timeout=2.0)
        send_message(resp if isinstance(resp, dict) else {"ok": True})
    except Exception as exc:  # noqa: BLE001
        send_message({"ok": False, "error": str(exc)})


if __name__ == "__main__":
    main()
