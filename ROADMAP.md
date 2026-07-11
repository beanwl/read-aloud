# Roadmap — planned updates

Ideas and next steps for **Speak Selection** (Chrome Web Store) and **Read Aloud** (Linux Pro). Order may change.

## Near term

- [ ] **README screenshots** — GUI + Chrome right-click panel
- [ ] **Hotkey** — global shortcut (e.g. speak selection without opening the GUI)
- [ ] **Stop from tray / notification** — easier stop while reading long articles
- [ ] **Sync settings** — share voice/speed between desktop GUI and Chrome extension
- [ ] **Better status** — show “Playing…” / progress in the GUI footer while the daemon speaks

## Chrome Web Store / Edge Add-ons

- [x] Marketplace build (`browser-extension-store/`) using Web Speech API
- [x] Pack script + privacy policy + STORE.md submission guide
- [ ] Developer accounts ($5 Chrome; Microsoft Partner Center for Edge)
- [ ] Screenshots (1280×800)
- [ ] Enable GitHub Pages for privacy URL
- [ ] Submit Chrome Web Store listing
- [ ] Submit Edge Add-ons listing
- [ ] Optional later: cloud TTS “premium” voices in Store build

Current extension depends on a **local native host** (Linux only) for the Pro build. Store users get the Web Speech build instead.

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
