/**
 * Speak Selection (Store) — content script.
 *
 * Speaks selected text with speechSynthesis (built into Chrome/Edge).
 * Side panel appears only when reading starts.
 */
(() => {
  if (window.__readAloudStoreLoaded) return;
  window.__readAloudStoreLoaded = true;

  const RATE_STEPS = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
  const PITCH_STEPS = [0.5, 0.75, 1, 1.25, 1.5];
  const VOLUME_STEPS = [0.25, 0.5, 0.75, 1];
  const DEFAULTS = {
    voiceURI: "",
    rateIndex: RATE_STEPS.indexOf(1),
    pitchIndex: PITCH_STEPS.indexOf(1),
    volumeIndex: VOLUME_STEPS.indexOf(1),
  };

  let utterQueue = [];
  let speaking = false;
  let paused = false;
  let lastSpeakText = "";

  const root = document.createElement("div");
  root.id = "read-aloud-root";
  root.className = "ra-hidden";
  root.innerHTML = `
    <div class="ra-panel">
      <div class="ra-head">
        <div class="ra-title">Speak Selection</div>
        <button class="ra-close" type="button" title="Close">×</button>
      </div>
      <label for="ra-voice">Voice</label>
      <select id="ra-voice"></select>
      <label for="ra-rate">Speed <span id="ra-rate-val">1x</span></label>
      <input id="ra-rate" type="range" min="0" max="${RATE_STEPS.length - 1}" step="1" />
      <label for="ra-pitch">Pitch <span id="ra-pitch-val">1x</span></label>
      <input id="ra-pitch" type="range" min="0" max="${PITCH_STEPS.length - 1}" step="1" />
      <label for="ra-volume">Volume <span id="ra-volume-val">1x</span></label>
      <input id="ra-volume" type="range" min="0" max="${VOLUME_STEPS.length - 1}" step="1" />
      <div class="ra-actions">
        <button class="ra-btn ra-speak" type="button">Speak</button>
        <button class="ra-btn ra-stop" type="button">Stop</button>
        <button class="ra-btn ra-resume" type="button">Resume</button>
      </div>
      <p class="ra-status" id="ra-status"></p>
    </div>
  `;
  document.documentElement.appendChild(root);

  const voiceEl = root.querySelector("#ra-voice");
  const rateEl = root.querySelector("#ra-rate");
  const pitchEl = root.querySelector("#ra-pitch");
  const volumeEl = root.querySelector("#ra-volume");
  const rateVal = root.querySelector("#ra-rate-val");
  const pitchVal = root.querySelector("#ra-pitch-val");
  const volumeVal = root.querySelector("#ra-volume-val");
  const statusEl = root.querySelector("#ra-status");

  function fmt(v) {
    return Number.isInteger(v) ? `${v}x` : `${v}x`;
  }

  function setStatus(text) {
    statusEl.textContent = text || "";
  }

  function showPanel() {
    root.classList.remove("ra-hidden");
    root.classList.add("ra-open");
  }

  function hidePanel() {
    root.classList.add("ra-hidden");
    root.classList.remove("ra-open", "ra-playing");
    setStatus("");
  }

  function loadVoicesIntoSelect(preferredURI) {
    const voices = speechSynthesis.getVoices();
    voiceEl.innerHTML = "";
    const sorted = [...voices].sort((a, b) => {
      const ae = a.lang.startsWith("en") ? 0 : 1;
      const be = b.lang.startsWith("en") ? 0 : 1;
      if (ae !== be) return ae - be;
      return a.name.localeCompare(b.name);
    });
    for (const v of sorted) {
      const opt = document.createElement("option");
      opt.value = v.voiceURI;
      opt.textContent = `${v.name} (${v.lang})`;
      voiceEl.appendChild(opt);
    }
    if (preferredURI && [...voiceEl.options].some((o) => o.value === preferredURI)) {
      voiceEl.value = preferredURI;
    } else {
      const enUS = sorted.find((v) => /en-US/i.test(v.lang) && /male|david|mark|guy|andrew/i.test(v.name));
      const en = sorted.find((v) => /en-US/i.test(v.lang)) || sorted.find((v) => v.lang.startsWith("en"));
      voiceEl.value = (enUS || en || sorted[0])?.voiceURI || "";
    }
  }

  async function loadSettings() {
    const stored = await chrome.storage.sync.get(DEFAULTS);
    const settings = { ...DEFAULTS, ...stored };
    rateEl.value = String(settings.rateIndex);
    pitchEl.value = String(settings.pitchIndex);
    volumeEl.value = String(settings.volumeIndex);
    rateVal.textContent = fmt(RATE_STEPS[settings.rateIndex] ?? 1);
    pitchVal.textContent = fmt(PITCH_STEPS[settings.pitchIndex] ?? 1);
    volumeVal.textContent = fmt(VOLUME_STEPS[settings.volumeIndex] ?? 1);
    loadVoicesIntoSelect(settings.voiceURI);
  }

  async function saveSettings() {
    await chrome.storage.sync.set({
      voiceURI: voiceEl.value,
      rateIndex: Number(rateEl.value),
      pitchIndex: Number(pitchEl.value),
      volumeIndex: Number(volumeEl.value),
    });
  }

  function selectedText() {
    return (window.getSelection()?.toString() || "").trim();
  }

  function chunkText(text) {
    const parts = [];
    const cleaned = text.replace(/\s+/g, " ").trim();
    if (cleaned.length <= 1800) return [cleaned];
    let remaining = cleaned;
    while (remaining) {
      if (remaining.length <= 1800) {
        parts.push(remaining);
        break;
      }
      const window = remaining.slice(0, 1800);
      let cut = Math.max(window.lastIndexOf(". "), window.lastIndexOf("? "), window.lastIndexOf("! "));
      if (cut < 400) cut = window.lastIndexOf(" ");
      if (cut < 1) cut = 1800;
      else cut += 1;
      parts.push(remaining.slice(0, cut).trim());
      remaining = remaining.slice(cut).trim();
    }
    return parts.filter(Boolean);
  }

  function stopSpeech() {
    // Prefer pause so Resume can continue mid-passage when the browser supports it.
    if (speechSynthesis.speaking && !speechSynthesis.paused) {
      speechSynthesis.pause();
      paused = true;
      root.classList.remove("ra-playing");
      setStatus("Paused");
      return;
    }
    speaking = false;
    paused = false;
    utterQueue = [];
    speechSynthesis.cancel();
    root.classList.remove("ra-playing");
    setStatus("Stopped");
  }

  function resumeSpeech() {
    if (speechSynthesis.paused || paused) {
      speechSynthesis.resume();
      paused = false;
      speaking = true;
      root.classList.add("ra-playing");
      setStatus("Playing…");
      return;
    }
    if (lastSpeakText) {
      speak(lastSpeakText);
      return;
    }
    setStatus("Nothing to resume");
    showPanel();
  }

  function speakNext() {
    if (!speaking || !utterQueue.length) {
      speaking = false;
      paused = false;
      root.classList.remove("ra-playing");
      setStatus(utterQueue.length ? "Ready" : "Done");
      return;
    }
    const text = utterQueue.shift();
    const u = new SpeechSynthesisUtterance(text);
    const voices = speechSynthesis.getVoices();
    const match = voices.find((v) => v.voiceURI === voiceEl.value);
    if (match) u.voice = match;
    u.rate = RATE_STEPS[Number(rateEl.value)] ?? 1;
    u.pitch = PITCH_STEPS[Number(pitchEl.value)] ?? 1;
    u.volume = VOLUME_STEPS[Number(volumeEl.value)] ?? 1;
    u.onend = () => speakNext();
    u.onerror = () => {
      setStatus("Speech error");
      speaking = false;
      paused = false;
      utterQueue = [];
      speechSynthesis.cancel();
      root.classList.remove("ra-playing");
    };
    speechSynthesis.speak(u);
  }

  async function speak(text) {
    const content = (text || selectedText()).trim();
    if (!content) {
      setStatus("Select text first");
      showPanel();
      return;
    }
    if (!window.speechSynthesis) {
      setStatus("Speech not supported in this browser");
      showPanel();
      return;
    }
    await saveSettings();
    lastSpeakText = content;
    speaking = false;
    paused = false;
    utterQueue = [];
    speechSynthesis.cancel();
    showPanel();
    speaking = true;
    root.classList.add("ra-playing");
    setStatus("Playing…");
    utterQueue = chunkText(content.slice(0, 50000));
    if (!speechSynthesis.getVoices().length) {
      await new Promise((r) => {
        speechSynthesis.addEventListener("voiceschanged", r, { once: true });
        setTimeout(r, 300);
      });
      loadVoicesIntoSelect(voiceEl.value);
    }
    speakNext();
  }

  root.querySelector(".ra-close").addEventListener("click", () => {
    speaking = false;
    paused = false;
    utterQueue = [];
    speechSynthesis.cancel();
    hidePanel();
  });
  root.querySelector(".ra-speak").addEventListener("click", () => speak());
  root.querySelector(".ra-stop").addEventListener("click", stopSpeech);
  root.querySelector(".ra-resume").addEventListener("click", resumeSpeech);

  for (const el of [voiceEl, rateEl, pitchEl, volumeEl]) {
    el.addEventListener("input", () => {
      rateVal.textContent = fmt(RATE_STEPS[Number(rateEl.value)] ?? 1);
      pitchVal.textContent = fmt(PITCH_STEPS[Number(pitchEl.value)] ?? 1);
      volumeVal.textContent = fmt(VOLUME_STEPS[Number(volumeEl.value)] ?? 1);
      saveSettings();
    });
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "read-aloud-speak") {
      if (message.showPanel) showPanel();
      speak(message.text || "");
      sendResponse({ ok: true });
      return true;
    }
    if (message?.type === "read-aloud-stop") {
      stopSpeech();
      sendResponse({ ok: true });
      return true;
    }
    if (message?.type === "read-aloud-resume") {
      resumeSpeech();
      sendResponse({ ok: true });
      return true;
    }
  });

  speechSynthesis.addEventListener("voiceschanged", () => {
    loadVoicesIntoSelect(voiceEl.value);
  });

  loadSettings();
})();
