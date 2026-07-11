const HOST = "com.readaloud.speak";
const MENU_ID = "read-aloud-selection";
const MULTIPLIERS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 3, 4];
const DEFAULT_INDEX = MULTIPLIERS.indexOf(1);
const DEFAULTS = {
  voice: "en-US-AndrewNeural",
  speedIndex: DEFAULT_INDEX,
  pitchIndex: DEFAULT_INDEX,
  volumeIndex: DEFAULT_INDEX,
};

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: MENU_ID,
      title: "Read Aloud",
      contexts: ["selection"],
    });
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== MENU_ID) return;
  const text = (info.selectionText || "").trim();
  if (!text) {
    notify("Nothing selected", "Highlight some text first.");
    return;
  }
  if (tab?.id != null) {
    chrome.tabs.sendMessage(tab.id, { type: "show-panel", playing: true }).catch(() => {});
  }
  const result = await speak(text);
  if (result?.ok === false && tab?.id != null) {
    chrome.tabs
      .sendMessage(tab.id, { type: "speak-done", error: result.error || "Failed" })
      .catch(() => {});
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "speak" || message?.type === "test-speak") {
    const tabId = sender.tab?.id;
    speak(message.text || "This is a voice test.")
      .then((result) => {
        if (result?.ok === false && tabId != null) {
          chrome.tabs
            .sendMessage(tabId, { type: "speak-done", error: result.error || "Failed" })
            .catch(() => {});
        }
        sendResponse(result);
      })
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }
  if (message?.type === "stop") {
    stop()
      .then((result) => sendResponse(result))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }
});

async function getSettings() {
  return { ...DEFAULTS, ...(await chrome.storage.sync.get(DEFAULTS)) };
}

function pitchFromMultiplier(value) {
  const hz = Math.round(20 * Math.log2(value));
  return `${hz >= 0 ? "+" : ""}${hz}Hz`;
}

function formatPercent(value) {
  const n = Math.round((value - 1) * 100);
  return `${n >= 0 ? "+" : ""}${n}%`;
}

async function speak(text) {
  // Stop is handled inside the native host when a new speak starts.
  // Skipping an extra native round-trip here saves noticeable delay.
  const settings = await getSettings();
  const speed = MULTIPLIERS[settings.speedIndex] ?? 1;
  const pitch = MULTIPLIERS[settings.pitchIndex] ?? 1;
  const volume = MULTIPLIERS[settings.volumeIndex] ?? 1;
  const payload = {
    action: "speak",
    text,
    voice: settings.voice,
    rate: formatPercent(speed),
    pitch: pitchFromMultiplier(pitch),
    volume: formatPercent(volume),
  };
  return sendNative(payload);
}

async function stop() {
  return sendNative({ action: "stop" });
}

function sendNative(payload) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendNativeMessage(HOST, payload, (response) => {
        if (chrome.runtime.lastError) {
          notify(
            "Read Aloud not connected",
            "Run ~/Tools/read-aloud/install-browser-integration.sh then reload the extension."
          );
          resolve({ ok: false, error: chrome.runtime.lastError.message });
          return;
        }
        if (response && response.ok === false) {
          notify("Read Aloud failed", response.error || "Unknown error");
          resolve(response);
          return;
        }
        resolve(response || { ok: true });
      });
    } catch (err) {
      notify("Read Aloud error", String(err));
      resolve({ ok: false, error: String(err) });
    }
  });
}

function notify(title, message) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: "icons/icon128.png",
    title,
    message,
  });
}
