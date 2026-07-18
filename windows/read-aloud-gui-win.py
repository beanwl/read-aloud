#!/usr/bin/env python3
"""Read Aloud — Windows desktop GUI.

Fast path: local Windows SAPI voices (Speakonia-style, offline, instant start).
Neural path: edge-tts streamed into ffplay so speech starts before the full file downloads.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

APP_DIR = Path(__file__).resolve().parent.parent
WIN_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = Path.home() / "AppData" / "Roaming" / "read-aloud" / "settings.json"
ICON_PNG = APP_DIR / "browser-extension-store" / "icons" / "icon128.png"
ICON_ICO = WIN_DIR / "read-aloud.ico"
APP_USER_MODEL_ID = "Beanwl.ReadAloud"

MULTIPLIERS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
DEFAULT_MULT_INDEX = MULTIPLIERS.index(1.0)

# Fallback neural list if edge-tts voice query fails.
NEURAL_VOICE_FALLBACK: list[tuple[str, str]] = [
    ("Andrew Multi (neural, male) — latest", "en-US-AndrewMultilingualNeural"),
    ("Andrew (neural)", "en-US-AndrewNeural"),
    ("Guy (neural)", "en-US-GuyNeural"),
    ("Eric (neural)", "en-US-EricNeural"),
    ("Brian (neural)", "en-US-BrianNeural"),
    ("Brian Multilingual (neural)", "en-US-BrianMultilingualNeural"),
    ("Christopher (neural)", "en-US-ChristopherNeural"),
    ("Roger (neural)", "en-US-RogerNeural"),
    ("Steffan (neural)", "en-US-SteffanNeural"),
    ("Jenny (neural)", "en-US-JennyNeural"),
    ("Aria (neural)", "en-US-AriaNeural"),
    ("Ava (neural)", "en-US-AvaNeural"),
    ("Ava Multilingual (neural)", "en-US-AvaMultilingualNeural"),
    ("Michelle (neural)", "en-US-MichelleNeural"),
    ("Emma (neural)", "en-US-EmmaNeural"),
    ("Emma Multilingual (neural)", "en-US-EmmaMultilingualNeural"),
    ("Ana (neural)", "en-US-AnaNeural"),
]
# Newest broadly available US neural voice (Copilot / Multilingual).
DEFAULT_VOICE_ID = "en-US-AndrewMultilingualNeural"
VOICE_CACHE_PATH = Path.home() / "AppData" / "Roaming" / "read-aloud" / "voices-cache.json"


def _discover_local_voices() -> list[tuple[str, str]]:
    """All installed Windows TTS voices (classic SAPI + OneCore), Speakinia-style/fast."""
    ps = r"""
$ErrorActionPreference = 'SilentlyContinue'
$seen = @{}
# Classic desktop voices
try {
  Add-Type -AssemblyName System.Speech
  $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
  foreach ($v in $s.GetInstalledVoices()) {
    if (-not $v.Enabled) { continue }
    $name = $v.VoiceInfo.Name
    $short = ($name -replace '^Microsoft ','') -replace ' Desktop$',''
    $key = $short.ToLowerInvariant()
    if ($seen.ContainsKey($key)) { continue }
    $seen[$key] = $true
    Write-Output ("sapi`t$short — local/fast`tsapi:$name")
  }
} catch {}
# OneCore voices (often includes Mark and others not in classic SAPI)
try {
  $cat = New-Object -ComObject SAPI.SpObjectTokenCategory
  $cat.SetId('HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices', $false)
  $tokens = @($cat.EnumerateTokens())
  foreach ($t in $tokens) {
    $desc = $t.GetDescription()
    $short = (($desc -split ' - ')[0] -replace '^Microsoft ','')
    $key = $short.ToLowerInvariant()
    if ($seen.ContainsKey($key)) { continue }
    $seen[$key] = $true
    Write-Output ("onecore`t$short — local/fast`tonecore:$($t.Id)")
  }
} catch {}
"""
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            **_no_window_kwargs(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return [
            ("David — local/fast", "sapi:Microsoft David Desktop"),
            ("Zira — local/fast", "sapi:Microsoft Zira Desktop"),
        ]
    voices: list[tuple[str, str]] = []
    for line in (proc.stdout or "").splitlines():
        parts = line.strip().split("\t")
        if len(parts) != 3:
            continue
        _kind, label, vid = parts
        voices.append((label, vid))
    if not voices:
        return [
            ("David — local/fast", "sapi:Microsoft David Desktop"),
            ("Zira — local/fast", "sapi:Microsoft Zira Desktop"),
        ]
    voices.sort(key=lambda item: item[0].lower())
    return voices


def _neural_label(short_name: str, gender: str = "") -> str:
    nice = short_name.removeprefix("en-US-").replace("Neural", "").replace("Multilingual", " Multi")
    tag = f"{nice} (neural"
    if gender:
        tag += f", {gender.lower()}"
    tag += ")"
    if short_name == DEFAULT_VOICE_ID:
        tag += " — latest"
    return tag


def _discover_neural_voices() -> list[tuple[str, str]]:
    """All en-US neural voices from edge-tts (cached for fast startup)."""
    try:
        if VOICE_CACHE_PATH.exists():
            age = time.time() - VOICE_CACHE_PATH.stat().st_mtime
            if age < 7 * 24 * 3600:
                data = json.loads(VOICE_CACHE_PATH.read_text(encoding="utf-8"))
                cached = [(str(a), str(b)) for a, b in data.get("neural", [])]
                if cached:
                    return cached
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass

    try:
        import edge_tts

        async def _list() -> list[dict]:
            return await edge_tts.list_voices()

        raw = asyncio.run(_list())
    except Exception:
        return list(NEURAL_VOICE_FALLBACK)

    voices: list[tuple[str, str]] = []
    for item in raw:
        short = item.get("ShortName") or ""
        locale = item.get("Locale") or ""
        if not short.startswith("en-US-") or locale != "en-US":
            continue
        voices.append((_neural_label(short, item.get("Gender") or ""), short))
    voices.sort(key=lambda item: (0 if item[1] == DEFAULT_VOICE_ID else 1, item[0].lower()))
    if not voices:
        return list(NEURAL_VOICE_FALLBACK)
    try:
        VOICE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        VOICE_CACHE_PATH.write_text(
            json.dumps({"neural": voices}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
    return voices


def _build_voice_catalog() -> list[tuple[str, str]]:
    local = _discover_local_voices()
    neural = _discover_neural_voices()
    # Put latest US neural first, then other neural, then local/fast.
    latest = [v for v in neural if v[1] == DEFAULT_VOICE_ID]
    other_neural = [v for v in neural if v[1] != DEFAULT_VOICE_ID]
    return latest + other_neural + local


def _format_multiplier(value: float) -> str:
    if value == int(value):
        return f"{int(value)}x"
    return f"{value:g}x"


def _percent_from_multiplier(value: float) -> str:
    return f"{int(round((value - 1) * 100)):+d}%"


def _pitch_from_multiplier(value: float) -> str:
    hz = int(round(20 * math.log2(value)))
    return f"{hz:+d}Hz"


def _sapi_rate_from_multiplier(value: float) -> int:
    """Map 0.25x–4x onto SAPI Rate (-10…10)."""
    return max(-10, min(10, int(round(5 * math.log2(value)))))


def _sapi_volume_from_multiplier(value: float) -> int:
    return max(0, min(100, int(round(value * 100))))


def _is_local_voice(voice_id: str) -> bool:
    return voice_id.startswith("sapi:") or voice_id.startswith("onecore:")


def _no_window_kwargs() -> dict:
    if sys.platform != "win32":
        return {}
    return {"creationflags": subprocess.CREATE_NO_WINDOW}


def _kill_process_tree(proc: subprocess.Popen | None) -> None:
    if not proc:
        return
    extras = getattr(proc, "_read_aloud_extras", None) or []
    for extra in list(extras) + [proc]:
        if extra.poll() is not None:
            continue
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(extra.pid)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    **_no_window_kwargs(),
                )
            else:
                extra.terminate()
                extra.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            try:
                extra.kill()
            except OSError:
                pass


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
    """Named mutex so a second taskbar click focuses the open window instead of erroring."""

    def __init__(self) -> None:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetLastError(0)
        self._mutex = kernel32.CreateMutexW(None, False, "Local\\Beanwl.ReadAloud.SingleInstance")
        already_exists = kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
        if not self._mutex or already_exists:
            if self._mutex:
                kernel32.CloseHandle(self._mutex)
            self._mutex = None
            raise BlockingIOError
        atexit.register(self.release)

    def release(self) -> None:
        if not self._mutex:
            return
        try:
            import ctypes

            ctypes.windll.kernel32.ReleaseMutex(self._mutex)
            ctypes.windll.kernel32.CloseHandle(self._mutex)
        except OSError:
            pass
        self._mutex = None


def _focus_existing_window() -> bool:
    """Bring an already-running Read Aloud window to the front."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if buf.value == "Read Aloud":
            found.append(hwnd)
        return True

    user32.EnumWindows(_enum, 0)
    if not found:
        return False
    hwnd = found[0]
    SW_RESTORE = 9
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    return True


def acquire_single_instance() -> SingleInstanceLock:
    try:
        return SingleInstanceLock()
    except BlockingIOError:
        _focus_existing_window()
        sys.exit(0)


def _which_player(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    # Common WinGet / local installs may not be on PATH for GUI launches.
    candidates = [
        Path.home()
        / "AppData"
        / "Local"
        / "Microsoft"
        / "WinGet"
        / "Packages"
        / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        / "ffmpeg-8.1.1-full_build"
        / "bin"
        / f"{name}.exe",
        Path(r"C:\ffmpeg\bin") / f"{name}.exe",
        Path(r"C:\Program Files\ffmpeg\bin") / f"{name}.exe",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    # Broader WinGet search (version folder names vary).
    winget_root = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_root.exists():
        matches = list(winget_root.glob(f"Gyan.FFmpeg*/ffmpeg-*/bin/{name}.exe"))
        if matches:
            return str(matches[0])
    return None


def _speak_local(
    text: str,
    voice_id: str,
    speed_mult: float,
    volume_mult: float,
) -> subprocess.Popen:
    """Speak via local Windows SAPI / OneCore (Speakonia-style) — starts immediately."""
    kind, payload = voice_id.split(":", 1)
    rate = _sapi_rate_from_multiplier(speed_mult)
    volume = _sapi_volume_from_multiplier(volume_mult)
    # mkstemp leaves the handle open; on Windows that locks the file from PowerShell.
    fd, raw_path = tempfile.mkstemp(prefix="read-aloud-sapi-", suffix=".txt")
    os.close(fd)
    text_file = Path(raw_path)
    text_file.write_text(text, encoding="utf-8")
    text_path = str(text_file).replace("'", "''")
    payload_lit = payload.replace("'", "''")

    if kind == "onecore":
        select_block = f"""
$cat = New-Object -ComObject SAPI.SpObjectTokenCategory
$cat.SetId('HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech_OneCore\\Voices', $false)
foreach ($t in @($cat.EnumerateTokens())) {{
  if ($t.Id -eq '{payload_lit}') {{ $voice.Voice = $t; break }}
}}
"""
        fallback_name = ""
    else:
        voice_token = (
            payload.replace("Microsoft ", "").replace(" Desktop", "").replace("'", "''")
        )
        select_block = f"""
foreach ($v in $voice.GetVoices()) {{
  $desc = $v.GetDescription()
  if ($desc -like '*{voice_token}*' -or $desc -like '*{payload_lit}*') {{
    $voice.Voice = $v
    break
  }}
}}
"""
        fallback_name = payload_lit

    ps = f"""
$ErrorActionPreference = 'Stop'
$text = [System.IO.File]::ReadAllText('{text_path}')
$ok = $false
try {{
  $voice = New-Object -ComObject SAPI.SpVoice
  {select_block}
  $voice.Rate = {rate}
  $voice.Volume = {volume}
  $voice.Speak($text) | Out-Null
  $ok = $true
}} catch {{ }}
if (-not $ok) {{
  Add-Type -AssemblyName System.Speech
  $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
  try {{
    if ('{fallback_name}') {{ $synth.SelectVoice('{fallback_name}') }}
  }} catch {{ }}
  $synth.Rate = {rate}
  $synth.Volume = {volume}
  $synth.Speak($text)
}}
Remove-Item -LiteralPath '{text_path}' -Force -ErrorAction SilentlyContinue
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
        **_no_window_kwargs(),
    )


def _speak_edge_stream(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    volume: str,
    should_stop,
) -> subprocess.Popen:
    """Stream edge-tts → ffmpeg (wav) → ffplay so audio starts before download finishes."""
    import edge_tts

    ffplay = _which_player("ffplay")
    ffmpeg = _which_player("ffmpeg")
    if not ffplay or not ffmpeg:
        raise RuntimeError(
            "ffmpeg/ffplay not found for neural voices. Install ffmpeg:\n"
            "winget install Gyan.FFmpeg\n"
            "Or pick a local/fast voice (David / Mark / Zira)."
        )

    # Same reliable pipeline as the Linux speak-daemon (mp3 pipe → wav → player).
    ff = subprocess.Popen(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-f",
            "wav",
            "pipe:1",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        **_no_window_kwargs(),
    )
    play = subprocess.Popen(
        [
            ffplay,
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "error",
            "-f",
            "wav",
            "-i",
            "pipe:0",
        ],
        stdin=ff.stdout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **_no_window_kwargs(),
    )
    if ff.stdout:
        ff.stdout.close()
    play._read_aloud_extras = [ff]  # type: ignore[attr-defined]

    async def _pump() -> None:
        assert ff.stdin is not None
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
        try:
            async for chunk in communicate.stream():
                if should_stop():
                    break
                if chunk["type"] == "audio":
                    ff.stdin.write(chunk["data"])
                    ff.stdin.flush()
        finally:
            try:
                ff.stdin.close()
            except OSError:
                pass

    def _runner() -> None:
        try:
            asyncio.run(_pump())
        except Exception:
            _kill_process_tree(play)

    threading.Thread(target=_runner, daemon=True).start()
    return play


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
        self._last_clipboard = ""
        self._poll_ms = 350
        self.voices = _build_voice_catalog()

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
        self.voice_var = tk.StringVar(value=DEFAULT_VOICE_ID)
        self.voice_display = ttk.Combobox(
            props,
            values=[v[0] for v in self.voices],
            state="readonly",
            width=32,
        )
        self.voice_display.pack(fill=tk.X, pady=(2, 10))
        default_label = next(
            (label for label, vid in self.voices if vid == DEFAULT_VOICE_ID),
            self.voices[0][0] if self.voices else "Andrew Multi (neural) — latest",
        )
        self.voice_display.set(default_label)
        self.voice_var.set(DEFAULT_VOICE_ID)

        def on_voice_pick(_event=None) -> None:
            idx = self.voice_display.current()
            if idx >= 0:
                self.voice_var.set(self.voices[idx][1])
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
        _kill_process_tree(self._player_proc)
        self._player_proc = None
        self._busy = False
        self.status.config(text="Stopped")

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

        voice = self.voice_var.get()
        speed_mult = MULTIPLIERS[int(self.speed_var.get())]
        volume_mult = MULTIPLIERS[int(self.volume_var.get())]
        rate = _percent_from_multiplier(speed_mult)
        pitch = _pitch_from_multiplier(MULTIPLIERS[int(self.pitch_var.get())])
        volume = _percent_from_multiplier(volume_mult)

        if _is_local_voice(voice):
            self.status.config(text="Speaking…")
        else:
            self.status.config(text="Starting neural voice…")

        def worker() -> None:
            try:
                if _is_local_voice(voice):
                    proc = _speak_local(text, voice, speed_mult, volume_mult)
                    self._player_proc = proc
                    proc.wait()
                else:
                    def should_stop() -> bool:
                        return gen != self._speak_generation

                    self.root.after(0, lambda: self.status.config(text="Speaking…"))
                    proc = _speak_edge_stream(text, voice, rate, pitch, volume, should_stop)
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
        self.status.config(text="Ready")

    def _load_settings(self) -> None:
        data: dict = {}
        if SETTINGS_PATH.exists():
            try:
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}

        # Prefer latest US neural unless the user explicitly saved another voice after this change.
        voice = data.get("voice", DEFAULT_VOICE_ID)
        prefer_latest = data.get("prefer_latest_us", True)
        if prefer_latest and voice != DEFAULT_VOICE_ID:
            # One-time move onto Andrew Multilingual (latest American neural).
            voice = DEFAULT_VOICE_ID
            data["voice"] = voice
            data["prefer_latest_us"] = False
            try:
                SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
                SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except OSError:
                pass

        self.voice_var.set(voice)
        for label, vid in self.voices:
            if vid == voice:
                self.voice_display.set(label)
                break
        else:
            fallback = next(
                ((label, vid) for label, vid in self.voices if vid == DEFAULT_VOICE_ID),
                self.voices[0] if self.voices else ("Andrew Multi (neural) — latest", DEFAULT_VOICE_ID),
            )
            self.voice_display.set(fallback[0])
            self.voice_var.set(fallback[1])
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
            "prefer_latest_us": False,
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
