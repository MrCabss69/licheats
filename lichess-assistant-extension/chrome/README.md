# Lichess Assistant Extension

Local development companion for Licheats. A single Manifest V3 build runs in both
Chromium browsers and Firefox (the `chrome/` folder name is historical).

## 1. Start the backend

```bash
uv run licheats-api   # http://127.0.0.1:8000
```

## 2. Load the extension

**Chrome / Edge / Brave / Opera / Vivaldi / Arc**

1. `chrome://extensions` → enable **Developer mode**.
2. **Load unpacked** → select this `chrome/` folder.

**Firefox (115+)**

1. `about:debugging#/runtime/this-firefox` → **Load Temporary Add-on…**.
2. Select `manifest.json` in this folder.
3. Grant the `http://127.0.0.1:8000` host permission if prompted. Temporary add-ons are
   removed on restart.

## 3. Use it

Open a Lichess game page, then open the popup. It calls
`http://127.0.0.1:8000/players/{username}/profile-summary` first, so the top summary can
appear from profile aggregates without downloading games. It then calls
`/players/{username}/analysis?limit=100&refresh=false` for prep/style/trends.

The refresh button starts `/players/{username}/sync-jobs?limit=5000&include_moves=false`
and polls `/sync-jobs/{job_id}`. The popup updates as batches arrive and keeps sample
coverage visible in the header with text and a compact progress bar.

## Notes

- Cross-browser: only callback-style `chrome.*` APIs and no background worker, so the same
  files load in Chromium and Firefox. Firefox identity is set via
  `browser_specific_settings.gecko` in `manifest.json` (ignored by Chromium).
- Local-only by design. Opponent detection depends on current Lichess DOM selectors in
  `content.js`; if Lichess changes its markup, update the selectors and the static contract
  tests (`tests/test_extension_static.py`) before treating the popup as broken.
- The backend must allow the extension origin. `LICHEATS_CORS_ORIGIN_REGEX` accepts
  `chrome-extension://` and `moz-extension://` by default.
