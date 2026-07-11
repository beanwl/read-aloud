# Read Aloud

Speakonia-style text-to-speech for Linux: a desktop app, Chrome/Brave right-click extension, and CLI helpers. Uses Microsoft neural voices via [edge-tts](https://github.com/rany2/edge-tts) (default: **Andrew**, US male).

**Repo:** https://github.com/beanwl/read-aloud

## Features

- **Desktop GUI** — paste clipboard, voice / speed / pitch / volume (0.25x–4x), Save Settings
- **Chrome extension** — highlight text → right-click → **Read Aloud**; side panel for controls
- **Warm speak daemon** — streams audio so speech starts in about a second
- **CLI** — speak clipboard, selection, or PDF pages
- **Single-instance GUI** — avoids two windows talking over each other

## Requirements

- Linux (tested on Linux Mint / Ubuntu)
- Python 3.10+
- `paplay` (PulseAudio) or `mpv`
- `ffmpeg` (for streaming playback; often in `~/.local/bin` or apt)
- `xclip` (clipboard)
- Google Chrome or Brave (for the extension)

## Quick install

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

### Chrome / Brave extension

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

## How it fits together

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
read-aloud/
├── read-aloud-gui.py          # Desktop app
├── read-aloud-tester.py       # Daemon / playback tester
├── speak*.sh                  # CLI helpers
├── browser-extension/         # Chrome MV3 extension
├── native-host/               # Native messaging + speak daemon
├── install-browser-integration.sh
├── enable-in-chrome.sh
├── ROADMAP.md                 # Planned updates
└── requirements.txt
```

## Chrome Web Store

This build is **not Store-ready** as-is: it needs a local Linux native host. A public Store version would need Web Speech API or a cloud TTS backend. See [ROADMAP.md](ROADMAP.md).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Stuck on “Reading…” | Run the tester; restart daemon: `pkill -f speak-daemon.py` then open the GUI again |
| Extension menu missing | Reload unpacked extension; refresh the page |
| Double voices | Close extra GUI windows; only one instance is allowed |
| Slow start | Ensure speak daemon is running (`~/.cache/read-aloud/speak.sock`) |
| No sound | Check `paplay` / volume; confirm `ffmpeg` is on `PATH` |

## License

Use freely for personal projects. Voices are provided by Microsoft’s online TTS service via edge-tts — respect their terms of use.
