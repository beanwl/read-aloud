#!/usr/bin/env python3
"""Read Aloud Tester — GUI to verify the speak daemon and local playback.

Use this when the Chrome panel is stuck on "Reading…" or audio is silent.
Check Daemon → Speak Test should produce Andrew's voice within ~1–2 seconds.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
PYTHON = APP_DIR / "venv" / "bin" / "python"
DAEMON = APP_DIR / "native-host" / "speak-daemon.py"
SOCK = Path.home() / ".cache/read-aloud/speak.sock"


def send(msg: dict, timeout: float = 3.0) -> dict:
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
        raise RuntimeError("No response from daemon")
    return json.loads(data.decode("utf-8"))


def ensure_daemon() -> None:
    try:
        send({"action": "ping"}, timeout=0.3)
        return
    except OSError:
        pass
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
    import time

    for _ in range(40):
        try:
            send({"action": "ping"}, timeout=0.2)
            return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("Could not start speak daemon")


class Tester(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Read Aloud Tester")
        self.geometry("460x360")
        self.minsize(420, 320)

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Read Aloud Tester", font=("Segoe UI", 14, "bold")).pack(
            anchor=tk.W
        )
        ttk.Label(
            frm,
            text="Checks the speak daemon and plays a short sample.",
        ).pack(anchor=tk.W, pady=(2, 10))

        self.status = tk.StringVar(value="Ready")
        ttk.Label(frm, textvariable=self.status).pack(anchor=tk.W, pady=(0, 8))

        self.text = tk.Text(frm, height=6, wrap=tk.WORD)
        self.text.pack(fill=tk.BOTH, expand=True)
        self.text.insert(
            "1.0",
            "This is a Read Aloud test. If you can hear this, speech is working.",
        )

        row = ttk.Frame(frm)
        row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(row, text="Check Daemon", command=self.check).pack(side=tk.LEFT)
        ttk.Button(row, text="Speak Test", command=self.speak).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Stop", command=self.stop).pack(side=tk.LEFT)

        self.after(200, self.check)

    def check(self) -> None:
        try:
            ensure_daemon()
            st = send({"action": "status"})
            self.status.set(
                f"Daemon OK — ffmpeg={st.get('ffmpeg')} paplay={st.get('paplay')} busy={st.get('busy')}"
            )
        except Exception as exc:  # noqa: BLE001
            self.status.set(f"Daemon FAIL: {exc}")
            messagebox.showerror("Read Aloud Tester", str(exc))

    def speak(self) -> None:
        text = self.text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Read Aloud Tester", "Enter some text first.")
            return
        try:
            ensure_daemon()
            resp = send(
                {
                    "action": "speak",
                    "text": text,
                    "voice": "en-US-AndrewNeural",
                    "rate": "+0%",
                    "volume": "+0%",
                    "pitch": "+0Hz",
                }
            )
            if not resp.get("ok"):
                raise RuntimeError(resp.get("error") or "Speak failed")
            self.status.set("Speaking… (you should hear audio within ~1–2 seconds)")
        except Exception as exc:  # noqa: BLE001
            self.status.set(f"Speak FAIL: {exc}")
            messagebox.showerror("Read Aloud Tester", str(exc))

    def stop(self) -> None:
        try:
            ensure_daemon()
            send({"action": "stop"})
            self.status.set("Stopped")
        except Exception as exc:  # noqa: BLE001
            self.status.set(f"Stop FAIL: {exc}")


def main() -> None:
    if not (APP_DIR / "venv/bin/python").exists():
        print("Missing venv at", APP_DIR / "venv", file=sys.stderr)
        sys.exit(1)
    Tester().mainloop()


if __name__ == "__main__":
    main()
