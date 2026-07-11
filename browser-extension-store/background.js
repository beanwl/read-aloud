/**
 * Speak Selection (Store) — background service worker.
 *
 * Marketplace build: uses the page's Web Speech API via the content script.
 * No nativeMessaging / local daemon — works on Chrome and Edge for everyone.
 */
const MENU_ID = "read-aloud-selection";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: MENU_ID,
      title: "Speak Selection",
      contexts: ["selection"],
    });
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== MENU_ID) return;
  const text = (info.selectionText || "").trim();
  if (!text || tab?.id == null) return;

  try {
    await chrome.tabs.sendMessage(tab.id, {
      type: "read-aloud-speak",
      text,
      showPanel: true,
    });
  } catch (err) {
    // Page may block content scripts (chrome://, Web Store, PDF viewer, etc.).
    console.warn("Speak Selection: page not reachable", err);
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "get-settings") {
    chrome.storage.sync.get(null).then((stored) => sendResponse({ ok: true, settings: stored }));
    return true;
  }
});
