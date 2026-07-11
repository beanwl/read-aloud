# Publish Read Aloud to Chrome Web Store & Edge Add-ons

This is the **marketplace** build: `browser-extension-store/`.

It uses the **Web Speech API** (built into Chrome and Edge). No Linux daemon, no `nativeMessaging`. Voices depend on the user’s OS/browser (quality varies; not the same as Andrew via edge-tts).

The Linux **Pro** extension remains in `browser-extension/` for local install.

## Test locally first

### Chrome
1. `chrome://extensions` → Developer mode → **Load unpacked**
2. Select `browser-extension-store/`
3. Open any article → highlight text → right-click → **Read Aloud**

### Edge
1. `edge://extensions` → Developer mode → **Load unpacked**
2. Same folder: `browser-extension-store/`

## Build the upload zip

```bash
./pack-store-extension.sh
```

Output: `store/dist/read-aloud-store-v1.0.0.zip`

## Privacy policy URL (required)

Host `store/privacy.html` somewhere public. Easiest with GitHub Pages:

1. Repo Settings → Pages → Deploy from branch `main` / folder `/store`  
   **or** copy `privacy.html` to `docs/privacy.html` and enable Pages on `/docs`
2. Use a URL like:  
   `https://beanwl.github.io/read-aloud/privacy.html`

Until Pages is enabled, you can temporarily use the raw GitHub URL only if the store accepts it (Chrome usually wants a normal https page). Prefer GitHub Pages.

## Chrome Web Store

1. Pay the one-time **$5** developer fee:  
   https://chrome.google.com/webstore/devconsole
2. **New item** → upload `store/dist/read-aloud-store-v*.zip`
3. Fill listing:
   - **Name:** Read Aloud
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
Read Aloud speaks the text you highlight on a webpage.

How to use
1. Select text on any page
2. Right-click → Read Aloud
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

## Note on voice quality

Marketplace users get **system/browser voices**. For Microsoft neural Andrew-quality voices on Linux, keep using the Pro build in this repo (`browser-extension/` + speak daemon).
