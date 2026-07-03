# Lichess Assistant Extension

Local development companion for Licheats.

1. Start the backend with `uv run licheats-api` from the repo root.
2. Load this `chrome/` directory as an unpacked extension.
3. Open a Lichess game page and open the popup.

The popup calls `http://127.0.0.1:8000/players/{username}/analysis`.
