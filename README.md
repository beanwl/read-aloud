# Speak Selection

**Speak Selection** is the Chrome Web Store / Edge marketplace extension: highlight text → right-click → hear it read aloud with adjustable voice, speed, pitch, and volume (Web Speech API).

This repo also includes **Read Aloud**, a desktop TTS app (Tk GUI + optional Linux Pro stack) that uses Microsoft neural voices via [edge-tts](https://github.com/rany2/edge-tts) (default: **Andrew**, US male).

| Product | Where | Name |
|---------|--------|------|
| Marketplace extension | `browser-extension-store/` · [Chrome Web Store](https://chromewebstore.google.com/detail/speak-selection/eldhkkcbhbifaaleikchnmacpbaglgbe) | **Speak Selection** |
| Windows desktop app | `windows/` | **Read Aloud** |
| Linux Pro app + native extension | `read-aloud-gui.py`, `browser-extension/`, `native-host/` | **Read Aloud** |

**Repo:** https://github.com/beanwl/read-aloud  
**Privacy policy (Store):** https://beanwl.github.io/read-aloud/privacy.html

## Features

### Speak Selection (Chrome / Edge store)

- Right-click selected text → **Speak Selection**
- Side panel for voice, speed, pitch, volume
- Built-in browser voices (no native host; works on any OS)

See **[STORE.md](STORE.md)** to pack and publish.

### Read Aloud (Windows)

- **Desktop GUI** — paste clipboard, voice / speed / pitch / volume (0.25x–4x), Save Settings
- **Neural voices** via edge-tts (same Andrew / Jenny / etc. voices as Linux Pro)
- **Taskbar / Start Menu** shortcuts with the app icon (not the Python icon)
- **Single-instance GUI** — avoids two windows talking over each other

### Read Aloud (Linux Pro)

- **Desktop GUI** — paste clipboard, voice / speed / pitch / volume (0.25x–4x), Save Settings
- **Chrome extension** — highlight text → right-click → **Read Aloud**; side panel for controls
- **Warm speak daemon** — streams audio so speech starts in about a second
- **CLI** — speak clipboard, selection, or PDF pages
- **Single-instance GUI** — avoids two windows talking over each other

## Quick install (Windows)

Requirements: Windows 10/11, Python 3.10+

```powershell
git clone https://github.com/beanwl/read-aloud.git
cd read-aloud
powershell -ExecutionPolicy Bypass -File windows\install-windows.ps1
```

That creates a venv, installs dependencies, builds `windows\ReadAloud.exe` (custom icon), and adds Desktop / Start Menu / taskbar shortcuts.

Or run the GUI directly after `pip install -r requirements.txt` in a venv:

```powershell
.\venv\Scripts\pythonw.exe windows\read-aloud-gui-win.py
```

Settings are saved to `%AppData%\read-aloud\settings.json`.

Optional: load **Speak Selection** in Chrome via `chrome://extensions` → Developer mode → **Load unpacked** → `browser-extension-store\`.

## Requirements (Linux Pro)

- Linux (tested on Linux Mint / Ubuntu)
- Python 3.10+
- `paplay` (PulseAudio) or `mpv`
- `ffmpeg` (for streaming playback; often in `~/.local/bin` or apt)
- `xclip` (clipboard)
- Google Chrome or Brave (for the Pro extension)

## Quick install (Linux Pro)

```bash
git clone https://github.com/beanwl/read-aloud.git
cd read-aloud

python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# Optional system packages
sudo apt install xclip pulseaudio-utils poppler-utils   # poppler = PDF text extract
```

### Desktop app

```bash
./launch-read-aloud-gui.sh
```

Or search the app menu for **Read Aloud** (if the `.desktop` file is installed).

Settings are saved to `~/.config/read-aloud/settings.json`.

### Chrome / Brave Pro extension

```bash
./install-browser-integration.sh
# or guided helper:
./enable-in-chrome.sh
```

Then in Chrome:

1. Open `chrome://extensions`
2. Turn on **Developer mode**
3. **Load unpacked** → select `browser-extension/`
4. Reload the extension after updates

Right-click selected text → **Read Aloud**. The side panel appears only when you start a read (not on every page).

### Tester

```bash
./launch-read-aloud-tester.sh
```

Checks the speak daemon and plays a short sample.

## CLI usage

| Command | What it does |
|---------|----------------|
| `./speak.sh "hello"` | Speak the given text |
| `./speak-clipboard.sh` | Speak clipboard |
| `./speak-selection.sh` | Speak mouse selection (primary) |
| `./speak-pdf.sh file.pdf [page] [end]` | Speak PDF text |

Environment overrides:

```bash
export SPEAK_VOICE=en-US-JennyNeural   # voice id
export SPEAK_PLAYER=paplay             # audio player
```

## How it fits together (Linux Pro)

```
Chrome extension ──nativeMessaging──► read-aloud-host.py
                                              │
Desktop GUI  ──unix socket──────────► speak-daemon.py ──► edge-tts ──► paplay
CLI speak.sh ──────────────────────► edge-tts (direct) ──► paplay
```

- **`speak-daemon.py`** — long-running process; streams TTS for fast start and continuous reading
- **`read-aloud-host.py`** — Chrome native messaging bridge to the daemon
- **`read-aloud-gui.py`** — Tk GUI; also talks to the daemon

## Project layout

```
read-aloud/                        # GitHub repo slug (unchanged; keeps Pages privacy URL stable)
├── read-aloud-gui.py              # Linux Pro desktop app
├── read-aloud-tester.py           # Daemon / playback tester
├── speak*.sh                      # CLI helpers
├── windows/                       # Windows desktop app
│   ├── read-aloud-gui-win.py      # Tk GUI (edge-tts + Windows Media Player)
│   ├── install-windows.ps1        # venv, launcher exe, shortcuts, taskbar pin
│   ├── launch-read-aloud.vbs      # Shortcut helper
│   └── read-aloud.ico             # App / taskbar icon
├── browser-extension/             # Chrome MV3 Pro (native host / Linux) — Read Aloud
├── browser-extension-store/       # Chrome/Edge marketplace — Speak Selection
├── native-host/                   # Native messaging + speak daemon
├── store/                         # Listing assets + pack output
├── docs/                          # GitHub Pages (privacy.html)
├── STORE.md                       # How to publish Speak Selection
├── install-browser-integration.sh
├── enable-in-chrome.sh
├── ROADMAP.md
└── requirements.txt
```

## Chrome / Edge marketplace (Speak Selection)

```bash
# Test: Load unpacked → browser-extension-store/
./pack-store-extension.sh   # creates store/dist/*.zip for upload
```

See **[STORE.md](STORE.md)** for Chrome Web Store and Edge Add-ons submission steps.

Privacy policy: https://beanwl.github.io/read-aloud/privacy.html ([`docs/privacy.html`](docs/privacy.html)).

The **Pro** extension in `browser-extension/` needs a local native host and is **not** Store-ready.

## Troubleshooting (Windows)

| Problem | Fix |
|---------|-----|
| Taskbar shows Python icon | Re-run `windows\install-windows.ps1`, then launch from the **Read Aloud** shortcut (not raw `pythonw`) |
| No sound | Check Windows volume; confirm the status line leaves “Generating speech…” |
| Double voices | Close the other Read Aloud window — only one instance is allowed |
| `python` not found | Install Python 3.10+ and tick **Add python.exe to PATH** |

## Troubleshooting (Linux Pro)

| Problem | Fix |
|---------|-----|
| Stuck on “Reading…” | Run the tester; restart daemon: `pkill -f speak-daemon.py` then open the GUI again |
| Extension menu missing | Reload unpacked extension; refresh the page |
| Double voices | Close extra GUI windows; only one instance is allowed |
| Slow start | Ensure speak daemon is running (`~/.cache/read-aloud/speak.sock`) |
| No sound | Check `paplay` / volume; confirm `ffmpeg` is on `PATH` |

## License

Use freely for personal projects. Marketplace voices are the browser’s built-in Web Speech voices. Desktop (Windows / Linux Pro) voices are provided by Microsoft’s online TTS via edge-tts — respect their terms of use.
