const RATE_STEPS = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
const PITCH_STEPS = [0.5, 0.75, 1, 1.25, 1.5];
const VOLUME_STEPS = [0.25, 0.5, 0.75, 1];
const DEFAULTS = {
  voiceURI: "",
  rateIndex: RATE_STEPS.indexOf(1),
  pitchIndex: PITCH_STEPS.indexOf(1),
  volumeIndex: VOLUME_STEPS.indexOf(1),
};

const voiceEl = document.getElementById("voice");
const rateEl = document.getElementById("rate");
const pitchEl = document.getElementById("pitch");
const volumeEl = document.getElementById("volume");
const rateVal = document.getElementById("rateVal");
const pitchVal = document.getElementById("pitchVal");
const volumeVal = document.getElementById("volumeVal");
const statusEl = document.getElementById("status");

function fmt(v) {
  return `${v}x`;
}

function fillVoices(preferred) {
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
  if (preferred && [...voiceEl.options].some((o) => o.value === preferred)) {
    voiceEl.value = preferred;
  }
}

function apply(settings) {
  rateEl.value = String(settings.rateIndex);
  pitchEl.value = String(settings.pitchIndex);
  volumeEl.value = String(settings.volumeIndex);
  rateVal.textContent = fmt(RATE_STEPS[settings.rateIndex] ?? 1);
  pitchVal.textContent = fmt(PITCH_STEPS[settings.pitchIndex] ?? 1);
  volumeVal.textContent = fmt(VOLUME_STEPS[settings.volumeIndex] ?? 1);
  fillVoices(settings.voiceURI);
}

async function load() {
  const stored = await chrome.storage.sync.get(DEFAULTS);
  apply({ ...DEFAULTS, ...stored });
}

async function save() {
  await chrome.storage.sync.set({
    voiceURI: voiceEl.value,
    rateIndex: Number(rateEl.value),
    pitchIndex: Number(pitchEl.value),
    volumeIndex: Number(volumeEl.value),
  });
  statusEl.textContent = "Saved";
  setTimeout(() => {
    if (statusEl.textContent === "Saved") statusEl.textContent = "";
  }, 1000);
}

for (const el of [rateEl, pitchEl, volumeEl]) {
  el.addEventListener("input", () => {
    rateVal.textContent = fmt(RATE_STEPS[Number(rateEl.value)] ?? 1);
    pitchVal.textContent = fmt(PITCH_STEPS[Number(pitchEl.value)] ?? 1);
    volumeVal.textContent = fmt(VOLUME_STEPS[Number(volumeEl.value)] ?? 1);
  });
}

document.getElementById("save").addEventListener("click", save);
document.getElementById("reset").addEventListener("click", async () => {
  apply(DEFAULTS);
  await chrome.storage.sync.set(DEFAULTS);
  statusEl.textContent = "Reset to defaults";
});

speechSynthesis.addEventListener("voiceschanged", () => fillVoices(voiceEl.value));
load();
