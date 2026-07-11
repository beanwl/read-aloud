(() => {
  if (window.__readAloudLoaded) return;
  window.__readAloudLoaded = true;

  const MULTIPLIERS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 3, 4];
  const DEFAULT_INDEX = MULTIPLIERS.indexOf(1);
  const VOICES = [
    ["en-US-AndrewNeural", "Andrew"],
    ["en-US-GuyNeural", "Guy"],
    ["en-US-EricNeural", "Eric"],
    ["en-US-BrianNeural", "Brian"],
    ["en-US-ChristopherNeural", "Christopher"],
    ["en-US-JennyNeural", "Jenny"],
    ["en-US-AriaNeural", "Aria"],
    ["en-US-MichelleNeural", "Michelle"],
    ["en-US-EmmaNeural", "Emma"],
    ["en-US-AnaNeural", "Ana"],
  ];
  const DEFAULTS = {
    voice: "en-US-AndrewNeural",
    speedIndex: DEFAULT_INDEX,
    pitchIndex: DEFAULT_INDEX,
    volumeIndex: DEFAULT_INDEX,
  };

  const root = document.createElement("div");
  root.id = "read-aloud-root";
  root.className = "ra-hidden";
  root.innerHTML = `
    <div class="ra-panel">
      <div class="ra-head">
        <div class="ra-title">Read Aloud</div>
        <button class="ra-close" type="button" title="Close">×</button>
      </div>
      <label for="ra-voice">Voice</label>
      <select id="ra-voice"></select>
      <label for="ra-speed">Speed <span id="ra-speed-val">1x</span></label>
      <input id="ra-speed" type="range" min="0" max="8" step="1" />
      <label for="ra-volume">Volume <span id="ra-volume-val">1x</span></label>
      <input id="ra-volume" type="range" min="0" max="8" step="1" />
      <div class="ra-actions">
        <button class="ra-btn ra-speak" type="button">Speak</button>
        <button class="ra-btn ra-stop" type="button">Stop</button>
      </div>
      <p class="ra-status" id="ra-status"></p>
    </div>
  `;
  document.documentElement.appendChild(root);

  const voiceEl = root.querySelector("#ra-voice");
  const speedEl = root.querySelector("#ra-speed");
  const volumeEl = root.querySelector("#ra-volume");
  const speedVal = root.querySelector("#ra-speed-val");
  const volumeVal = root.querySelector("#ra-volume-val");
  const statusEl = root.querySelector("#ra-status");

  for (const [id, label] of VOICES) {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = label;
    voiceEl.appendChild(opt);
  }

  function formatMult(index) {
    const v = MULTIPLIERS[Number(index)] ?? 1;
    return `${v}x`;
  }

  function applySettings(settings) {
    voiceEl.value = settings.voice;
    speedEl.value = String(settings.speedIndex);
    volumeEl.value = String(settings.volumeIndex);
    speedVal.textContent = formatMult(settings.speedIndex);
    volumeVal.textContent = formatMult(settings.volumeIndex);
  }

  function currentSettings() {
    return {
      voice: voiceEl.value,
      speedIndex: Number(speedEl.value),
      volumeIndex: Number(volumeEl.value),
      pitchIndex: DEFAULT_INDEX,
    };
  }

  async function loadSettings() {
    const stored = await chrome.storage.sync.get(DEFAULTS);
    // Never restore panel visibility across pages.
    await chrome.storage.sync.remove("panelOpen");
    applySettings({ ...DEFAULTS, ...stored });
  }

  async function saveSettings() {
    await chrome.storage.sync.set(currentSettings());
  }

  function showPanel(playing = false) {
    root.classList.remove("ra-hidden");
    root.classList.add("ra-open");
    if (playing) {
      root.classList.add("ra-playing");
      setStatus("Reading…");
    }
  }

  function hidePanel() {
    root.classList.add("ra-hidden");
    root.classList.remove("ra-open", "ra-playing");
    setStatus("");
  }

  function setStatus(text) {
    statusEl.textContent = text || "";
  }

  function selectedText() {
    return (window.getSelection()?.toString() || "").trim();
  }

  let speakInFlight = false;

  async function speak(text) {
    const content = (text || selectedText()).trim();
    if (!content) {
      setStatus("Select text first");
      showPanel(false);
      return;
    }
    if (speakInFlight) {
      stop();
      return;
    }
    speakInFlight = true;
    showPanel(true);
    setStatus("Reading…");
    chrome.runtime.sendMessage({ type: "speak", text: content }, (response) => {
      speakInFlight = false;
      if (chrome.runtime.lastError) {
        setStatus(chrome.runtime.lastError.message);
        root.classList.remove("ra-playing");
        return;
      }
      if (!response?.ok) {
        setStatus(response?.error || "Failed");
        root.classList.remove("ra-playing");
        return;
      }
      setStatus("Playing…");
      // If playback dies silently, don't leave the UI stuck forever.
      setTimeout(() => {
        if (statusEl.textContent === "Playing…" || statusEl.textContent === "Reading…") {
          setStatus("Ready");
          root.classList.remove("ra-playing");
        }
      }, 120000);
    });
  }

  function stop() {
    speakInFlight = false;
    chrome.runtime.sendMessage({ type: "stop" }, () => {
      root.classList.remove("ra-playing");
      setStatus("Stopped");
    });
  }

  root.querySelector(".ra-close").addEventListener("click", () => {
    stop();
    hidePanel();
  });
  root.querySelector(".ra-speak").addEventListener("click", () => speak());
  root.querySelector(".ra-stop").addEventListener("click", stop);

  for (const el of [voiceEl, speedEl, volumeEl]) {
    el.addEventListener("input", () => {
      speedVal.textContent = formatMult(speedEl.value);
      volumeVal.textContent = formatMult(volumeEl.value);
      saveSettings();
    });
  }

  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "show-panel") {
      showPanel(Boolean(message.playing));
    }
    if (message?.type === "speak-done") {
      root.classList.remove("ra-playing");
      setStatus(message.error || "Ready");
    }
  });

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "sync") return;
    const next = currentSettings();
    for (const [key, change] of Object.entries(changes)) {
      if (key in next) next[key] = change.newValue;
    }
    applySettings(next);
  });

  loadSettings();
})();
