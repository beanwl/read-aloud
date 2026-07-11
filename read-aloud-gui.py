#!/usr/bin/env python3
"""Read Aloud — Speakonia-style GUI with voice/pitch/speed/volume controls."""

from __future__ import annotations

import atexit
import fcntl
import json
import math
import os
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

APP_DIR = Path(__file__).resolve().parent
PYTHON = APP_DIR / "venv" / "bin" / "python"
DAEMON = APP_DIR / "native-host" / "speak-daemon.py"
CACHE = Path.home() / ".cache/read-aloud"
SOCK = CACHE / "speak.sock"
LOCK_PATH = Path.home() / ".cache/read-aloud.lock"
SETTINGS_PATH = Path.home() / ".config/read-aloud/settings.json"

# Discrete multiplier steps shown on sliders (1x = normal).
MULTIPLIERS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
DEFAULT_MULT_INDEX = MULTIPLIERS.index(1.0)


def _format_multiplier(value: float) -> str:
    if value == int(value):
        return f"{int(value)}x"
    return f"{value:g}x"


def _percent_from_multiplier(value: float) -> str:
    return f"{int(round((value - 1) * 100)):+d}%"


def _pitch_from_multiplier(value: float) -> str:
    hz = int(round(20 * math.log2(value)))
    return f"{hz:+d}Hz"


def _daemon_send(msg: dict, timeout: float = 2.0) -> dict:
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
        raise RuntimeError("No response from speak daemon")
    return json.loads(data.decode("utf-8"))


def _daemon_ping() -> bool:
    try:
        return bool(_daemon_send({"action": "ping"}, timeout=0.2).get("ok"))
    except OSError:
        return False


def ensure_speak_daemon() -> None:
    if _daemon_ping():
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
        if _daemon_ping():
            return
        time.sleep(0.05)
    raise RuntimeError("Speak daemon failed to start")


class SingleInstanceLock:
    """Only allow one Read Aloud window at a time."""

    def __init__(self) -> None:
        self._fd = None
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._fd = open(LOCK_PATH, "w")
        try:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._fd.close()
            self._fd = None
            raise
        self._fd.write(str(os.getpid()))
        self._fd.flush()
        atexit.register(self.release)

    def release(self) -> None:
        if not self._fd:
            return
        try:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            self._fd.close()
        except OSError:
            pass
        self._fd = None
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except OSError:
            pass


def acquire_single_instance() -> SingleInstanceLock:
    try:
        return SingleInstanceLock()
    except BlockingIOError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Read Aloud",
            "Read Aloud is already running.\n\n"
            "Close the other window first — two copies will talk over each other.",
        )
        root.destroy()
        sys.exit(0)

VOICES: list[tuple[str, str]] = [
    ("Andrew (US male)", "en-US-AndrewNeural"),
    ("Guy (US male)", "en-US-GuyNeural"),
    ("Eric (US male)", "en-US-EricNeural"),
    ("Brian (US male)", "en-US-BrianNeural"),
    ("Christopher (US male)", "en-US-ChristopherNeural"),
    ("Jenny (US female)", "en-US-JennyNeural"),
    ("Aria (US female)", "en-US-AriaNeural"),
    ("Michelle (US female)", "en-US-MichelleNeural"),
    ("Emma (US female)", "en-US-EmmaNeural"),
    ("Ana (US female)", "en-US-AnaNeural"),
]


class ReadAloudApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Read Aloud")
        self.root.geometry("820x560")
        self.root.minsize(720, 480)
        try:
            self.root.tk.call("wm", "class", self.root._w, "ReadAloud", "read-aloud")
        except tk.TclError:
            pass
        self._set_window_icon()

        self._busy = False
        self._speak_generation = 0
        self._last_clipboard = ""
        self._poll_ms = 350

        self._build_ui()
        self._load_settings()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        try:
            ensure_speak_daemon()
        except Exception:
            pass

        clip = self._read_clipboard()
        self._last_clipboard = clip
        if clip:
            self._set_text(clip)
        self._poll_clipboard()
        if clip:
            self.root.after(200, self.speak)

    def _set_window_icon(self) -> None:
        icon_path = Path.home() / ".local/share/icons/read-aloud.png"
        if not icon_path.exists():
            return
        try:
            img = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, img)
            self._icon_img = img
        except tk.TclError:
            pass

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(10, 8))
        header.pack(fill=tk.X)
        ttk.Label(header, text="Read Aloud", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(header, text="Paste + Speak", command=self.paste_and_speak).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(header, text="Clear", command=self.clear_text).pack(side=tk.RIGHT)

        body = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        props = ttk.LabelFrame(body, text="Speech Properties", padding=10)
        text_frame = ttk.Frame(body)
        body.add(props, weight=0)
        body.add(text_frame, weight=1)

        # Voice
        ttk.Label(props, text="Voice").pack(anchor=tk.W)
        self.voice_var = tk.StringVar(value="en-US-AndrewNeural")
        self.voice_display = ttk.Combobox(
            props,
            values=[v[0] for v in VOICES],
            state="readonly",
            width=28,
        )
        self.voice_display.pack(fill=tk.X, pady=(2, 10))
        self.voice_display.set("Andrew (US male)")

        def on_voice_pick(_event=None) -> None:
            idx = self.voice_display.current()
            if idx >= 0:
                self.voice_var.set(VOICES[idx][1])
                self._save_settings()

        self.voice_display.bind("<<ComboboxSelected>>", on_voice_pick)

        # Sliders — discrete steps: 0.25x … 4x
        self.pitch_var = tk.IntVar(value=DEFAULT_MULT_INDEX)
        self.speed_var = tk.IntVar(value=DEFAULT_MULT_INDEX)
        self.volume_var = tk.IntVar(value=DEFAULT_MULT_INDEX)

        self.pitch_label = ttk.Label(props, text="Pitch: 1x")
        self.pitch_label.pack(anchor=tk.W)
        ttk.Scale(
            props,
            from_=0,
            to=len(MULTIPLIERS) - 1,
            orient=tk.HORIZONTAL,
            variable=self.pitch_var,
            command=self._on_slider_move,
        ).pack(fill=tk.X, pady=(0, 8))

        self.speed_label = ttk.Label(props, text="Speed: 1x")
        self.speed_label.pack(anchor=tk.W)
        ttk.Scale(
            props,
            from_=0,
            to=len(MULTIPLIERS) - 1,
            orient=tk.HORIZONTAL,
            variable=self.speed_var,
            command=self._on_slider_move,
        ).pack(fill=tk.X, pady=(0, 8))

        self.volume_label = ttk.Label(props, text="Volume: 1x")
        self.volume_label.pack(anchor=tk.W)
        ttk.Scale(
            props,
            from_=0,
            to=len(MULTIPLIERS) - 1,
            orient=tk.HORIZONTAL,
            variable=self.volume_var,
            command=self._on_slider_move,
        ).pack(fill=tk.X, pady=(0, 12))

        btn_row = ttk.Frame(props)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Test", command=self.test_voice).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_row, text="Save Settings", command=self.save_settings_clicked).pack(
            side=tk.LEFT, padx=(6, 0), fill=tk.X, expand=True
        )
        ttk.Button(btn_row, text="Reset", command=self.reset_voice).pack(
            side=tk.LEFT, padx=(6, 0), fill=tk.X, expand=True
        )

        self.text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Segoe UI", 11), padx=8, pady=8)
        self.text.pack(fill=tk.BOTH, expand=True)

        footer = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        footer.pack(fill=tk.X)
        self.speak_btn = ttk.Button(footer, text="▶  Speak", command=self.speak)
        self.speak_btn.pack(side=tk.LEFT)
        self.stop_btn = ttk.Button(footer, text="■  Stop", command=self.stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.status = ttk.Label(footer, text="Copy text (Ctrl+C) while app is open")
        self.status.pack(side=tk.RIGHT)

    def _mult(self, var: tk.IntVar) -> float:
        idx = max(0, min(int(round(var.get())), len(MULTIPLIERS) - 1))
        return MULTIPLIERS[idx]

    def _on_slider_move(self, _value: str) -> None:
        for var in (self.pitch_var, self.speed_var, self.volume_var):
            var.set(int(round(var.get())))
        self._update_labels()
        self._save_settings()

    def _update_labels(self) -> None:
        self.pitch_label.config(text=f"Pitch: {_format_multiplier(self._mult(self.pitch_var))}")
        self.speed_label.config(text=f"Speed: {_format_multiplier(self._mult(self.speed_var))}")
        self.volume_label.config(text=f"Volume: {_format_multiplier(self._mult(self.volume_var))}")

    def _settings_dict(self) -> dict:
        return {
            "voice": self.voice_var.get(),
            "pitchIndex": int(self.pitch_var.get()),
            "speedIndex": int(self.speed_var.get()),
            "volumeIndex": int(self.volume_var.get()),
            "geometry": self.root.geometry(),
        }

    def _save_settings(self) -> None:
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(json.dumps(self._settings_dict(), indent=2), encoding="utf-8")
        except OSError:
            pass

    def save_settings_clicked(self) -> None:
        self._save_settings()
        self._status("Settings saved")

    def _load_settings(self) -> None:
        if not SETTINGS_PATH.exists():
            return
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        voice = data.get("voice") or "en-US-AndrewNeural"
        label = next((name for name, vid in VOICES if vid == voice), None)
        if label:
            self.voice_var.set(voice)
            self.voice_display.set(label)

        for key, var in (
            ("pitchIndex", self.pitch_var),
            ("speedIndex", self.speed_var),
            ("volumeIndex", self.volume_var),
        ):
            try:
                idx = int(data.get(key, DEFAULT_MULT_INDEX))
            except (TypeError, ValueError):
                idx = DEFAULT_MULT_INDEX
            var.set(max(0, min(idx, len(MULTIPLIERS) - 1)))

        geom = data.get("geometry")
        if isinstance(geom, str) and "x" in geom:
            try:
                self.root.geometry(geom)
            except tk.TclError:
                pass
        self._update_labels()

    def reset_voice(self) -> None:
        self.voice_var.set("en-US-AndrewNeural")
        self.voice_display.set("Andrew (US male)")
        self.pitch_var.set(DEFAULT_MULT_INDEX)
        self.speed_var.set(DEFAULT_MULT_INDEX)
        self.volume_var.set(DEFAULT_MULT_INDEX)
        self._update_labels()
        self._save_settings()

    def test_voice(self) -> None:
        self.stop()
        self._set_text("This is a voice test.")
        self.speak()

    def _tts_settings(self) -> tuple[str, str, str, str]:
        speed = self._mult(self.speed_var)
        volume = self._mult(self.volume_var)
        pitch = self._mult(self.pitch_var)
        return (
            self.voice_var.get(),
            _percent_from_multiplier(speed),
            _percent_from_multiplier(volume),
            _pitch_from_multiplier(pitch),
        )

    def _on_close(self) -> None:
        self._save_settings()
        self.stop()
        self.root.destroy()

    def _poll_clipboard(self) -> None:
        clip = self._read_clipboard()
        if clip and clip != self._last_clipboard:
            self._last_clipboard = clip
            self._on_new_copy(clip)
        self.root.after(self._poll_ms, self._poll_clipboard)

    def _on_new_copy(self, clip: str) -> None:
        self._set_text(clip)
        self._status(f"New copy — reading {len(clip)} chars...")
        self.stop()
        self.speak()

    def _set_text(self, content: str) -> None:
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, content)

    def clear_text(self) -> None:
        self.text.delete("1.0", tk.END)
        self._last_clipboard = ""

    def paste_and_speak(self) -> None:
        clip = self._read_clipboard()
        if clip:
            self._last_clipboard = clip
            self._set_text(clip)
        elif not self.text.get("1.0", tk.END).strip():
            self._status("Clipboard is empty")
            return
        self.stop()
        self.speak()

    def _read_clipboard(self) -> str:
        self.root.update_idletasks()
        for cmd in (
            ["xclip", "-selection", "clipboard", "-o"],
            ["wl-paste", "-n"],
            ["xsel", "--clipboard", "--output"],
        ):
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode != 0:
                continue
            try:
                out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
                text = out.decode("utf-8", errors="replace").strip()
                if text:
                    return text
            except subprocess.CalledProcessError:
                pass
        try:
            clip = self.root.clipboard_get()
            if isinstance(clip, str) and clip.strip():
                return clip.strip()
        except tk.TclError:
            pass
        return ""

    def _status(self, msg: str) -> None:
        self.status.config(text=msg)
        self.root.update_idletasks()

    def speak(self) -> None:
        content = self.text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Read Aloud", "No text. Copy something first (Ctrl+C).")
            return
        if self._busy:
            self.stop()
        self._speak_generation += 1
        generation = self._speak_generation
        self._busy = True
        self.speak_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._status("Starting…")
        threading.Thread(
            target=self._speak_worker,
            args=(content[:50000], generation),
            daemon=True,
        ).start()

    def _speak_worker(self, content: str, generation: int) -> None:
        try:
            ensure_speak_daemon()
            if generation != self._speak_generation:
                return
            voice, rate, volume, pitch = self._tts_settings()
            resp = _daemon_send(
                {
                    "action": "speak",
                    "text": content,
                    "voice": voice,
                    "rate": rate,
                    "volume": volume,
                    "pitch": pitch,
                }
            )
            if not resp.get("ok"):
                raise RuntimeError(resp.get("error") or "Speak failed")
            if generation != self._speak_generation:
                return
            self.root.after(0, lambda: self._status("Playing…"))
            # Wait until daemon finishes (or this speak is cancelled).
            while generation == self._speak_generation:
                try:
                    st = _daemon_send({"action": "status"}, timeout=0.5)
                except OSError:
                    break
                if not st.get("busy"):
                    break
                time.sleep(0.25)
        except Exception as exc:  # noqa: BLE001
            if generation == self._speak_generation:
                self.root.after(0, lambda e=str(exc): self._on_error(f"Speech failed:\n{e}"))
                return
        finally:
            if generation == self._speak_generation:
                self.root.after(0, self._on_done)

    def stop(self) -> None:
        self._speak_generation += 1
        try:
            if _daemon_ping():
                _daemon_send({"action": "stop"}, timeout=0.5)
        except Exception:
            pass
        if self._busy:
            self._on_done()

    def _on_done(self) -> None:
        self._busy = False
        self.speak_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self._status("Ready — copy text to auto-read")

    def _on_error(self, msg: str) -> None:
        self._on_done()
        messagebox.showerror("Read Aloud", msg)


def main() -> None:
    lock = acquire_single_instance()
    root = tk.Tk(className="read-aloud")
    app = ReadAloudApp(root)
    try:
        root.mainloop()
    finally:
        app.stop()
        lock.release()


if __name__ == "__main__":
    main()
