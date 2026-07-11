# Publish Speak Selection to Chrome Web Store & Edge Add-ons

This is the **marketplace** build: `browser-extension-store/` (store name: **Speak Selection**).

It uses the **Web Speech API** (built into Chrome and Edge). No Linux daemon, no `nativeMessaging`. Voices depend on the user’s OS/browser (quality varies; not the same as Andrew via edge-tts).

The Linux **Pro** extension remains in `browser-extension/` for local install and keeps the **Read Aloud** name.

## Test locally first

### Chrome
1. `chrome://extensions` → Developer mode → **Load unpacked**
2. Select `browser-extension-store/`
3. Open any article → highlight text → right-click → **Speak Selection**

### Edge
1. `edge://extensions` → Developer mode → **Load unpacked**
2. Same folder: `browser-extension-store/`

## Build the upload zip

```bash
./pack-store-extension.sh
```

Output: `store/dist/read-aloud-store-v1.0.1.zip` (version comes from `manifest.json`)

## Privacy policy URL (required)

Host `docs/privacy.html` via GitHub Pages:

1. Repo Settings → Pages → Deploy from branch `main` / folder `/docs`
2. Live URL (do **not** change while a listing is Pending review):  
   `https://beanwl.github.io/read-aloud/privacy.html`

The GitHub repo slug stays **`read-aloud`** on purpose so this Pages URL remains valid during Chrome Web Store review. Renaming the repo to `speak-selection` would move Pages to `/speak-selection/` and break the submitted privacy URL unless you update the listing (and possibly cancel/resubmit review).

## Chrome Web Store

1. Pay the one-time **$5** developer fee:  
   https://chrome.google.com/webstore/devconsole
2. **New item** → upload `store/dist/read-aloud-store-v*.zip`
3. Fill listing:
   - **Name:** Speak Selection
   - **Summary:** Right-click to hear selected text with adjustable speed and voice
   - **Category:** Productivity / Accessibility
   - **Language:** English
   - **Icon:** 128×128 (already in the zip)
   - **Screenshots:** 1280×800 or 640×400 — capture the side panel on a news page
4. **Privacy:**
   - Single purpose: read selected text aloud
   - Privacy policy URL (from above)
   - Justify permissions (contextMenus, storage, host access for selected text only)
5. Submit for review (often a few days)

### Renaming an item already in review

If you submitted under the wrong name (e.g. “Read Aloud”):

1. Open the item → **Store listing**
2. **⋮** menu → **Cancel review** (returns to Draft)
3. **Package** tab → upload the new zip (bump version in manifest first)
4. Update **Store listing** title and description to **Speak Selection**
5. **Save draft** → **Submit for review**

See also `store/LISTING-FILL.md` and `store/PRIVACY-FILL.md` for copy-paste text.

## Microsoft Edge Add-ons

1. Partner Center: https://partner.microsoft.com/dashboard/microsoftedge  
2. Create a new Edge extension product  
3. Upload the **same zip** (Chromium MV3)  
4. Reuse listing text + privacy policy URL  
5. Submit for certification  

Edge often accepts Chrome Web Store packages with minor listing differences.

## Listing copy (draft)

**Short description (≤132 chars):**  
Right-click any selected text to hear it read aloud. Choose voice, speed, pitch, and volume.

**Detailed description:**

```
Speak Selection reads the text you highlight on a webpage.

How to use
1. Select text on any page
2. Right-click → Speak Selection
3. Adjust voice, speed, pitch, or volume in the side panel
4. Click Stop anytime

Works in Google Chrome and Microsoft Edge using your browser’s built-in voices.
Settings sync with your browser account when sync is enabled.

Privacy: selected text stays on your device. We do not run servers that collect your reading content.
```

## After approval

- Share store links in the main README  
- Bump `version` in `browser-extension-store/manifest.json` for each update  
- Re-run `./pack-store-extension.sh` and upload a new zip  

**Store URL (same extension ID after rename):**  
https://chromewebstore.google.com/detail/speak-selection/eldhkkcbhbifaaleikchnmacpbaglgbe

## Note on voice quality

Marketplace users get **system/browser voices**. For Microsoft neural Andrew-quality voices on Linux, keep using the Pro build in this repo (`browser-extension/` + speak daemon).
