# Licheats

Licheats is a local toolkit for fetching Lichess player/game data, storing it in SQLite,
and producing JSON-safe opponent analysis for a Python library, a local FastAPI service,
and the companion Chrome extension.

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

## Local API

```bash
uv run licheats-api
curl http://127.0.0.1:8000/health
curl 'http://127.0.0.1:8000/players/fieber69/analysis?limit=100&refresh=false'
```

Endpoints:

- `GET /health`
- `GET /players/{username}/analysis?limit=100&refresh=false&perf_type=blitz`
- `POST /players/{username}/sync?limit=100&perf_type=blitz`

API responses are stable JSON DTOs. They do not expose SQLAlchemy objects, `Counter`,
`defaultdict`, or internal analyzer state.

## Chrome extension

The extension is a local development companion, not a Chrome Web Store product.

1. Start the API with `uv run licheats-api`.
2. Load `lichess-assistant-extension/chrome` as an unpacked extension.
3. Open a Lichess game page and open the extension popup.

The popup calls `http://127.0.0.1:8000` and handles the backend being unavailable.

## Tests

Offline tests should not call Lichess:

```bash
uv run pytest -q
```

Live tests, when added, must be opt-in:

```bash
LICHESS_API_TOKEN=... uv run pytest -m integration -q
```

## Data policy

Generated databases, exports, pickles, notebooks outputs, and large local datasets are
not tracked. Keep small deterministic fixtures under `tests/fixtures/` only.
