# Chrome Web Store — Privacy tab (copy/paste)

Item: Speak Selection (`eldhkkcbhbifaaleikchnmacpbaglgbe`)

## Single purpose description

```
Read selected webpage text aloud using the browser’s built-in speech engine, with simple voice and speed controls.
```

## Permission justifications

### contextMenus
```
Adds a “Speak Selection” item to the right-click menu so users can start reading the text they selected.
```

### storage
```
Saves the user’s voice, speed, pitch, and volume preferences locally (and via browser sync if enabled) so settings persist between sessions.
```

### activeTab
```
Allows the extension to interact with the tab the user is using when they choose Speak Selection, so selected text on that page can be spoken.
```

### Host permission
```
Needed so the content script can run on normal http/https pages the user visits, show the side panel, and speak the text they highlight. The extension only uses the user’s selection for on-device speech and does not upload page content to our servers.
```

## Remote code

Select: **No, I am not using remote code**

(Do **not** choose Yes. Web Speech API is a built-in browser API, not remote code.)

If the form already has Yes selected, switch it to **No** and clear any remote-code justification.

## Data usage

Check **only**:
- [x] **Website content** — selected text is read so it can be spoken on the device

Leave all other boxes unchecked (no PII, health, financial, auth, location, history, etc.).

## Certifications

Check **all three**:
- [x] I do not sell or transfer user data to third parties…
- [x] I do not use or transfer user data for purposes unrelated to the single purpose…
- [x] I do not use or transfer user data for creditworthiness/lending…

## Privacy policy URL

```
https://beanwl.github.io/read-aloud/privacy.html
```

Then **Save draft** and return to Store listing → Submit for review.
