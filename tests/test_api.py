from datetime import datetime, timezone

from fastapi.testclient import TestClient

from licheats.api import create_app
from licheats.lichess import LichessError
from licheats.schemas import PlayerAnalysis, PlayerProfile, ResultBucket, SyncResult
from licheats.settings import Settings


class FakeService:
    def __init__(self):
        self.refresh_seen = None

    def analyze_player(self, username, *, limit=100, refresh=False, perf_type=None):
        self.refresh_seen = refresh
        player = PlayerProfile(username=username.lower(), display_name=username)
        return PlayerAnalysis(
            player=player,
            games_count=0,
            source="refresh" if refresh else "cache",
            generated_at=datetime.now(timezone.utc),
            summary={"total_games": 0, "wins": 0, "losses": 0, "draws": 0, "win_rate": 0.0},
            by_color={"unknown": ResultBucket()},
            openings={},
            castling={},
            queen_presence={},
            time_controls={},
            rating_timeline=[],
        )

    def sync_player(self, username, *, limit=100, perf_type=None):
        return SyncResult(username=username.lower(), players_upserted=1, games_upserted=0, fetched_games=0)


def test_health_and_analysis_contract():
    service = FakeService()
    app = create_app(Settings(db_url="sqlite:///:memory:"), service=service)
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/players/Fieber69/analysis?refresh=true")

    assert response.status_code == 200
    body = response.json()
    assert body["player"]["username"] == "fieber69"
    assert body["source"] == "refresh"
    assert service.refresh_seen is True


class MissingPlayerService:
    def analyze_player(self, username, *, limit=100, refresh=False, perf_type=None):
        raise LichessError(
            "Lichess returned HTTP 404",
            code="lichess_http_error",
            details={"status_code": 404},
        )

    def sync_player(self, username, *, limit=100, perf_type=None):
        raise AssertionError("sync should not be called")


class BrokenService:
    def analyze_player(self, username, *, limit=100, refresh=False, perf_type=None):
        raise RuntimeError("database password leaked")

    def sync_player(self, username, *, limit=100, perf_type=None):
        raise AssertionError("sync should not be called")


def test_api_maps_lichess_404_to_not_found():
    app = create_app(Settings(db_url="sqlite:///:memory:"), service=MissingPlayerService())
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/players/missing/analysis")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "lichess_http_error"


def test_api_hides_unexpected_exception_details():
    app = create_app(Settings(db_url="sqlite:///:memory:"), service=BrokenService())
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/players/fieber69/analysis")

    assert response.status_code == 500
    assert response.json()["error"]["message"] == "Unexpected internal error."
    assert "password" not in response.text
