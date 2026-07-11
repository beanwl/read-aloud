# Roadmap — planned updates

Ideas and next steps for Read Aloud. Order may change.

## Near term

- [ ] **README screenshots** — GUI + Chrome right-click panel
- [ ] **Hotkey** — global shortcut (e.g. speak selection without opening the GUI)
- [ ] **Stop from tray / notification** — easier stop while reading long articles
- [ ] **Sync settings** — share voice/speed between desktop GUI and Chrome extension
- [ ] **Better status** — show “Playing…” / progress in the GUI footer while the daemon speaks

## Chrome Web Store (optional track)

Current extension depends on a **local native host** (Linux only). Store users won’t have that.

Possible paths:

1. **Lite Store build** — Web Speech API only (weaker voices, no install)
2. **Cloud TTS build** — Microsoft/Google/Amazon API (good voices; needs keys + privacy policy)
3. **Keep GitHub “Pro”** — current edge-tts + daemon for Linux power users

Checklist if publishing:

- [ ] Developer account ($5)
- [ ] Remove `nativeMessaging` from Store zip (or ship a separate lite package)
- [ ] Privacy policy URL
- [ ] Screenshots + store listing copy
- [ ] Trim host permissions where possible

## Quality / performance

- [ ] Prefetch / keep Edge TTS connection warmer across reads
- [ ] Optional offline fallback voice (e.g. Piper) when offline
- [ ] Pause / resume (not only Stop)
- [ ] Highlight current sentence in the GUI text box while speaking

## Packaging

- [ ] `.deb` or Flatpak for one-click install
- [ ] Auto-start speak daemon via systemd user unit (in addition to autostart `.desktop`)
- [ ] Windows port (Wine Speakonia already exists separately; native Windows edge-tts path)

## Docs / polish

- [x] README + install steps
- [x] Code comments on main modules
- [ ] Man page or `--help` for all CLI scripts
- [ ] CONTRIBUTING.md for pull requests

---

Suggestions welcome via GitHub Issues: https://github.com/beanwl/read-aloud/issues
