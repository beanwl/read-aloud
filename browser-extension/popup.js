/**
 * Toolbar popup — quick voice/speed/volume controls.
 * Values are stored in chrome.storage.sync (shared with the page side panel).
 */
const MULTIPLIERS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 3, 4];
const DEFAULT_INDEX = MULTIPLIERS.indexOf(1);

const VOICES = [
  ["en-US-AndrewNeural", "Andrew (US male)"],
  ["en-US-GuyNeural", "Guy (US male)"],
  ["en-US-EricNeural", "Eric (US male)"],
  ["en-US-BrianNeural", "Brian (US male)"],
  ["en-US-ChristopherNeural", "Christopher (US male)"],
  ["en-US-JennyNeural", "Jenny (US female)"],
  ["en-US-AriaNeural", "Aria (US female)"],
  ["en-US-MichelleNeural", "Michelle (US female)"],
  ["en-US-EmmaNeural", "Emma (US female)"],
  ["en-US-AnaNeural", "Ana (US female)"],
];

const DEFAULTS = {
  voice: "en-US-AndrewNeural",
  speedIndex: DEFAULT_INDEX,
  pitchIndex: DEFAULT_INDEX,
  volumeIndex: DEFAULT_INDEX,
};

const voiceEl = document.getElementById("voice");
const speedEl = document.getElementById("speed");
const pitchEl = document.getElementById("pitch");
const volumeEl = document.getElementById("volume");
const speedVal = document.getElementById("speedVal");
const pitchVal = document.getElementById("pitchVal");
const volumeVal = document.getElementById("volumeVal");
const statusEl = document.getElementById("status");

function formatMult(index) {
  const v = MULTIPLIERS[Number(index)] ?? 1;
  return Number.isInteger(v) ? `${v}x` : `${v}x`;
}

function fillVoices() {
  voiceEl.innerHTML = "";
  for (const [id, label] of VOICES) {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = label;
    voiceEl.appendChild(opt);
  }
}

function applyToUi(settings) {
  voiceEl.value = settings.voice;
  speedEl.value = String(settings.speedIndex);
  pitchEl.value = String(settings.pitchIndex);
  volumeEl.value = String(settings.volumeIndex);
  speedVal.textContent = formatMult(settings.speedIndex);
  pitchVal.textContent = formatMult(settings.pitchIndex);
  volumeVal.textContent = formatMult(settings.volumeIndex);
}

function currentSettings() {
  return {
    voice: voiceEl.value,
    speedIndex: Number(speedEl.value),
    pitchIndex: Number(pitchEl.value),
    volumeIndex: Number(volumeEl.value),
  };
}

async function loadSettings() {
  const stored = await chrome.storage.sync.get(DEFAULTS);
  return { ...DEFAULTS, ...stored };
}

async function saveSettings() {
  const settings = currentSettings();
  await chrome.storage.sync.set(settings);
  statusEl.textContent = "Saved";
  setTimeout(() => {
    if (statusEl.textContent === "Saved") statusEl.textContent = "";
  }, 900);
}

fillVoices();

loadSettings().then(applyToUi);

for (const el of [voiceEl, speedEl, pitchEl, volumeEl]) {
  el.addEventListener("input", () => {
    speedVal.textContent = formatMult(speedEl.value);
    pitchVal.textContent = formatMult(pitchEl.value);
    volumeVal.textContent = formatMult(volumeEl.value);
    saveSettings();
  });
}

document.getElementById("reset").addEventListener("click", async () => {
  applyToUi(DEFAULTS);
  await chrome.storage.sync.set(DEFAULTS);
  statusEl.textContent = "Reset to defaults";
});

document.getElementById("test").addEventListener("click", async () => {
  statusEl.textContent = "Testing…";
  const settings = currentSettings();
  await chrome.storage.sync.set(settings);
  chrome.runtime.sendMessage(
    { type: "test-speak", text: "This is a voice test." },
    (response) => {
      if (chrome.runtime.lastError) {
        statusEl.textContent = chrome.runtime.lastError.message;
        return;
      }
      statusEl.textContent = response?.ok ? "Playing…" : response?.error || "Failed";
    }
  );
});

document.getElementById("stop").addEventListener("click", () => {
  statusEl.textContent = "Stopping…";
  chrome.runtime.sendMessage({ type: "stop" }, (response) => {
    if (chrome.runtime.lastError) {
      statusEl.textContent = chrome.runtime.lastError.message;
      return;
    }
    statusEl.textContent = response?.ok === false ? response?.error || "Failed" : "Stopped";
  });
});

document.getElementById("resume").addEventListener("click", () => {
  statusEl.textContent = "Resuming…";
  chrome.runtime.sendMessage({ type: "resume" }, (response) => {
    if (chrome.runtime.lastError) {
      statusEl.textContent = chrome.runtime.lastError.message;
      return;
    }
    statusEl.textContent = response?.ok ? "Playing…" : response?.error || "Failed";
  });
});
