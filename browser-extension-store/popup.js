/**
 * Speak Selection (Store) — toolbar popup.
 * Stop / Resume talk to the active tab's content script (Web Speech API).
 */
const statusEl = document.getElementById("status");

async function sendToActiveTab(message) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id == null) throw new Error("No active tab");
  return chrome.tabs.sendMessage(tab.id, message);
}

document.getElementById("open-options").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

document.getElementById("stop").addEventListener("click", async () => {
  statusEl.textContent = "Stopping…";
  try {
    await sendToActiveTab({ type: "read-aloud-stop" });
    statusEl.textContent = "Paused / stopped";
  } catch (err) {
    statusEl.textContent = "Open a normal webpage first";
  }
});

document.getElementById("resume").addEventListener("click", async () => {
  statusEl.textContent = "Resuming…";
  try {
    await sendToActiveTab({ type: "read-aloud-resume" });
    statusEl.textContent = "Playing…";
  } catch (err) {
    statusEl.textContent = "Open a normal webpage first";
  }
});

document.getElementById("test").addEventListener("click", async () => {
  statusEl.textContent = "Testing…";
  try {
    await sendToActiveTab({
      type: "read-aloud-speak",
      text: "This is a voice test.",
      showPanel: true,
    });
    statusEl.textContent = "Playing…";
  } catch (err) {
    statusEl.textContent = "Open a normal webpage first";
  }
});
