# Licheats

Licheats is a local toolkit for fetching Lichess player/game data, storing it in SQLite,
and producing JSON-safe opponent analysis for a Python library, a local FastAPI service,
and the companion browser extension.

The project was modernized from an old prototype. The old `from licheats import Client`
API is intentionally removed. Use `Licheats` and `Settings` instead.

## Install

```bash
uv sync
```

Runtime data is not stored inside the source tree by default. Configure it with:

```bash
export LICHEATS_DB_URL="sqlite:////absolute/path/to/licheats.sqlite3"
export LICHESS_API_TOKEN="optional-token-for-authenticated-requests"
```

If `LICHEATS_DB_URL` is not set, Licheats creates a SQLite database in the user data
directory for this platform.

The old committed token must be revoked in Lichess. It was removed from the code, but
repository history may still contain it.

## Python usage

```python
from licheats import Licheats, Settings

app = Licheats(Settings.from_env())
analysis = app.analyze_player("fieber69", limit=100, refresh=True, perf_type="blitz")
print(analysis.summary)
```

`refresh=True` means: fetch fresh data from Lichess, upsert SQLite, then analyze the
persisted records. `refresh=False` analyzes cached SQLite data and only syncs when the
player/games are missing.

For instant product surfaces, use the profile-only summary first. It reads Lichess profile
aggregates (`count`, ratings, play time) without downloading games:

```python
summary = app.profile_summary("fieber69")
print(summary.total_games, summary.win_rate, summary.ratings)
```

## Local API

```bash
uv run licheats-api
curl http://127.0.0.1:8000/health
curl 'http://127.0.0.1:8000/players/fieber69/profile-summary'
curl 'http://127.0.0.1:8000/players/fieber69/analysis?limit=100&refresh=false'
curl -X POST 'http://127.0.0.1:8000/players/fieber69/sync-jobs?limit=5000&include_moves=false&page_size=1000'
```

Endpoints:

- `GET /health`
- `GET /players/{username}/profile-summary`
- `GET /players/{username}/analysis?limit=100&refresh=false&perf_type=blitz`
- `POST /players/{username}/sync?limit=100&perf_type=blitz&include_moves=true`
- `POST /players/{username}/sync-jobs?limit=5000&include_moves=false&page_size=1000`
- `GET /sync-jobs/{job_id}`

API responses are stable JSON DTOs. They do not expose SQLAlchemy objects, `Counter`,
`defaultdict`, or internal analyzer state.

The game gateway streams Lichess NDJSON line by line and paginates with `until`. Background
sync jobs are intentionally in-memory and local-only: they are suitable for this single-user
desktop workflow, not a distributed queue. Light pulls (`include_moves=false`) preserve any
previously cached SAN moves instead of clobbering style data.

## Browser extension (Chrome & Firefox)

The extension is a local development companion, not a store-published product. A single
Manifest V3 build works in both Chromium browsers and Firefox — the extension source lives
in `lichess-assistant-extension/chrome/` (folder name is historical; it is cross-browser).

First, always start the API:

```bash
uv run licheats-api   # serves http://127.0.0.1:8000
```

### Chrome / Edge / Brave / Opera / Vivaldi / Arc

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked** and select `lichess-assistant-extension/chrome/`.

### Firefox (115+)

1. Open `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on…**.
3. Select `lichess-assistant-extension/chrome/manifest.json`.
4. If prompted, grant the host permission for `http://127.0.0.1:8000` so the popup can
   reach the local API. Temporary add-ons are removed when Firefox restarts.

### Using it

Open a Lichess game page, then open the popup. The popup detects the opponent and the
color you are playing, renders an instant profile summary, then enriches the view with
cached game analysis. Refresh starts a background light sync and updates the UI as batches
arrive. The header keeps an explicit coverage indicator such as `100/5000 games` plus a
small coverage bar, so partial samples are visible instead of implied as full history. It
fails gracefully (with a retry) when the backend is down.

Compatibility notes:

- Uses only callback-style `chrome.*` APIs (`tabs`, `runtime`), which Firefox supports via
  the `chrome` alias, and no background service worker (kept out for Firefox < 121).
- The backend CORS policy (`LICHEATS_CORS_ORIGIN_REGEX`) accepts both `chrome-extension://`
  and `moz-extension://` origins by default.
- **Safari** is not supported without converting the extension via Xcode.

## Tests

Offline tests should not call Lichess:

```bash
uv run pytest -q
uv run ruff check .
node --check lichess-assistant-extension/chrome/popup.js
node --check lichess-assistant-extension/chrome/content.js
```

Live tests, when added, must be opt-in:

```bash
LICHESS_API_TOKEN=... uv run pytest -m integration -q
```

For ad-hoc performance probes:

```bash
uv run python scripts/perf_probe.py --username fieber69 --skip-endpoints --moves-experiment --limit 100
uv run python scripts/perf_probe.py --username fieber69 --full-history --full-history-max 5000
```

## Data policy

Generated databases, exports, pickles, notebooks outputs, and large local datasets are
not tracked. Keep small deterministic fixtures under `tests/fixtures/` only.
