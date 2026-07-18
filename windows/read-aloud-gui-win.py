#!/usr/bin/env python3
"""Read Aloud — Windows desktop GUI (edge-tts + Windows Media Player)."""

from __future__ import annotations

import asyncio
import atexit
import json
import math
import msvcrt
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

APP_DIR = Path(__file__).resolve().parent.parent
WIN_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = Path.home() / "AppData" / "Roaming" / "read-aloud" / "settings.json"
LOCK_PATH = Path.home() / "AppData" / "Local" / "read-aloud" / "gui.lock"
ICON_PNG = APP_DIR / "browser-extension-store" / "icons" / "icon128.png"
ICON_ICO = WIN_DIR / "read-aloud.ico"
APP_USER_MODEL_ID = "Beanwl.ReadAloud"

MULTIPLIERS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
DEFAULT_MULT_INDEX = MULTIPLIERS.index(1.0)

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


def _format_multiplier(value: float) -> str:
    if value == int(value):
        return f"{int(value)}x"
    return f"{value:g}x"


def _percent_from_multiplier(value: float) -> str:
    return f"{int(round((value - 1) * 100)):+d}%"


def _pitch_from_multiplier(value: float) -> str:
    hz = int(round(20 * math.log2(value)))
    return f"{hz:+d}Hz"


def _read_clipboard_text() -> str:
    try:
        root = tk._default_root
        if root is None:
            tmp = tk.Tk()
            tmp.withdraw()
            try:
                return tmp.clipboard_get().strip()
            finally:
                tmp.destroy()
        return root.clipboard_get().strip()
    except tk.TclError:
        return ""


class SingleInstanceLock:
    def __init__(self) -> None:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._fd = open(LOCK_PATH, "a+b")
        try:
            msvcrt.locking(self._fd.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            self._fd.close()
            self._fd = None
            raise BlockingIOError from exc
        atexit.register(self.release)

    def release(self) -> None:
        if not self._fd:
            return
        try:
            self._fd.seek(0)
            msvcrt.locking(self._fd.fileno(), msvcrt.LK_UNLCK, 1)
            self._fd.close()
        except OSError:
            pass
        self._fd = None


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


def _play_mp3(path: Path) -> subprocess.Popen:
    """Play MP3 via Windows Media Player COM (no extra window)."""
    ps = f"""
$ErrorActionPreference = 'Stop'
$player = New-Object -ComObject WMPlayer.OCX
$player.URL = '{str(path).replace("'", "''")}'
$player.settings.volume = 100
$player.controls.play()
while ($player.playState -ne 1) {{
  Start-Sleep -Milliseconds 150
}}
"""
    return subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


async def _synthesize(text: str, voice: str, rate: str, pitch: str, volume: str, out: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
    await communicate.save(str(out))


class ReadAloudApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Read Aloud")
        self.root.geometry("820x560")
        self.root.minsize(720, 480)
        self._set_window_icon()

        self._busy = False
        self._speak_generation = 0
        self._player_proc: subprocess.Popen | None = None
        self._temp_mp3: Path | None = None
        self._last_clipboard = ""
        self._poll_ms = 350

        self._build_ui()
        self._load_settings()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        clip = self._read_clipboard()
        self._last_clipboard = clip
        if clip:
            self._set_text(clip)
        self._poll_clipboard()

    def _set_window_icon(self) -> None:
        if ICON_ICO.exists():
            try:
                self.root.iconbitmap(default=str(ICON_ICO))
            except tk.TclError:
                pass
        if ICON_PNG.exists():
            try:
                img = tk.PhotoImage(file=str(ICON_PNG))
                self.root.iconphoto(True, img)
                self._icon_img = img
            except tk.TclError:
                pass
        if sys.platform == "win32" and ICON_ICO.exists():
            try:
                import ctypes

                hwnd = self.root.winfo_id()
                # Load icons for title bar + Alt-Tab; taskbar follows AppUserModelID + shortcut.
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x0010
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1
                hicon_big = ctypes.windll.user32.LoadImageW(
                    0, str(ICON_ICO), IMAGE_ICON, 32, 32, LR_LOADFROMFILE
                )
                hicon_small = ctypes.windll.user32.LoadImageW(
                    0, str(ICON_ICO), IMAGE_ICON, 16, 16, LR_LOADFROMFILE
                )
                if hicon_big:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                if hicon_small:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
            except OSError:
                pass

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(10, 8))
        header.pack(fill=tk.X)
        ttk.Label(header, text="Read Aloud", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(header, text="Paste + Speak", command=self.paste_and_speak).pack(
            side=tk.RIGHT, padx=(6, 0)
        )
        ttk.Button(header, text="Clear", command=self.clear_text).pack(side=tk.RIGHT)

        body = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        props = ttk.LabelFrame(body, text="Speech Properties", padding=10)
        text_frame = ttk.Frame(body)
        body.add(props, weight=0)
        body.add(text_frame, weight=1)

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
        ).pack(fill=tk.X, pady=(0, 8))

        btns = ttk.Frame(props)
        btns.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btns, text="Speak", command=self.speak).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Stop", command=self.stop).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Save Settings", command=self._save_settings).pack(fill=tk.X, pady=2)

        self.status = ttk.Label(props, text="Ready", wraplength=220)
        self.status.pack(anchor=tk.W, pady=(12, 0))

        self.text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Segoe UI", 11))
        self.text.pack(fill=tk.BOTH, expand=True)

    def _on_slider_move(self, _value=None) -> None:
        self.pitch_label.config(text=f"Pitch: {_format_multiplier(MULTIPLIERS[int(self.pitch_var.get())])}")
        self.speed_label.config(text=f"Speed: {_format_multiplier(MULTIPLIERS[int(self.speed_var.get())])}")
        self.volume_label.config(text=f"Volume: {_format_multiplier(MULTIPLIERS[int(self.volume_var.get())])}")

    def _set_text(self, value: str) -> None:
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", value)

    def _get_text(self) -> str:
        return self.text.get("1.0", tk.END).strip()

    def _read_clipboard(self) -> str:
        try:
            return self.root.clipboard_get().strip()
        except tk.TclError:
            return ""

    def _poll_clipboard(self) -> None:
        clip = self._read_clipboard()
        if clip and clip != self._last_clipboard:
            self._last_clipboard = clip
            self._set_text(clip)
        self.root.after(self._poll_ms, self._poll_clipboard)

    def clear_text(self) -> None:
        self._set_text("")

    def paste_and_speak(self) -> None:
        clip = self._read_clipboard()
        if clip:
            self._last_clipboard = clip
            self._set_text(clip)
        self.speak()

    def stop(self) -> None:
        self._speak_generation += 1
        if self._player_proc and self._player_proc.poll() is None:
            self._player_proc.terminate()
            try:
                self._player_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._player_proc.kill()
        self._player_proc = None
        self._cleanup_temp()
        self._busy = False
        self.status.config(text="Stopped")

    def _cleanup_temp(self) -> None:
        if self._temp_mp3 and self._temp_mp3.exists():
            try:
                self._temp_mp3.unlink()
            except OSError:
                pass
        self._temp_mp3 = None

    def speak(self) -> None:
        text = self._get_text()
        if not text:
            messagebox.showinfo("Read Aloud", "Paste or type some text first.")
            return
        if self._busy:
            self.stop()
        self._busy = True
        self._speak_generation += 1
        gen = self._speak_generation
        self.status.config(text="Generating speech…")

        voice = self.voice_var.get()
        rate = _percent_from_multiplier(MULTIPLIERS[int(self.speed_var.get())])
        pitch = _pitch_from_multiplier(MULTIPLIERS[int(self.pitch_var.get())])
        volume = _percent_from_multiplier(MULTIPLIERS[int(self.volume_var.get())])

        def worker() -> None:
            tmp = Path(tempfile.mkstemp(prefix="read-aloud-", suffix=".mp3")[1])
            try:
                asyncio.run(_synthesize(text, voice, rate, pitch, volume, tmp))
                if gen != self._speak_generation:
                    tmp.unlink(missing_ok=True)
                    return
                self._temp_mp3 = tmp
                self.root.after(0, lambda: self.status.config(text="Speaking…"))
                proc = _play_mp3(tmp)
                self._player_proc = proc
                proc.wait()
            except Exception as exc:
                self.root.after(
                    0,
                    lambda: messagebox.showerror("Read Aloud", f"Could not speak text:\n{exc}"),
                )
            finally:
                if gen == self._speak_generation:
                    self.root.after(0, self._speak_done)

        threading.Thread(target=worker, daemon=True).start()

    def _speak_done(self) -> None:
        self._busy = False
        self._player_proc = None
        self._cleanup_temp()
        self.status.config(text="Ready")

    def _load_settings(self) -> None:
        if not SETTINGS_PATH.exists():
            self._on_slider_move()
            return
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._on_slider_move()
            return
        voice = data.get("voice", "en-US-AndrewNeural")
        self.voice_var.set(voice)
        for label, vid in VOICES:
            if vid == voice:
                self.voice_display.set(label)
                break
        for key, var in (
            ("pitch_index", self.pitch_var),
            ("speed_index", self.speed_var),
            ("volume_index", self.volume_var),
        ):
            if key in data:
                try:
                    var.set(int(data[key]))
                except (TypeError, ValueError):
                    pass
        self._on_slider_move()

    def _save_settings(self) -> None:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "voice": self.voice_var.get(),
            "pitch_index": int(self.pitch_var.get()),
            "speed_index": int(self.speed_var.get()),
            "volume_index": int(self.volume_var.get()),
        }
        SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.status.config(text="Settings saved")

    def _on_close(self) -> None:
        self.stop()
        self.root.destroy()


def _set_app_user_model_id() -> None:
    """Make Windows treat this as Read Aloud (not pythonw) for the taskbar icon."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except OSError:
        pass


def main() -> None:
    _set_app_user_model_id()
    acquire_single_instance()
    root = tk.Tk()
    ReadAloudApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
