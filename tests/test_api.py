from datetime import datetime, timezone

from fastapi.testclient import TestClient

from licheats.api import create_app
from licheats.lichess import LichessError
from licheats.schemas import PlayerAnalysis, PlayerProfile, PlayerProfileSummary, ResultBucket, SyncJobStatus, SyncResult
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

    def sync_player(self, username, *, limit=100, perf_type=None, include_moves=True, page_size=1000):
        return SyncResult(username=username.lower(), players_upserted=1, games_upserted=0, fetched_games=0)

    def profile_summary(self, username):
        player = PlayerProfile(username=username.lower(), display_name=username, counts={"all": 15})
        return PlayerProfileSummary(
            player=player,
            generated_at=datetime.now(timezone.utc),
            total_games=15,
            wins=8,
            losses=5,
            draws=2,
            win_rate=53.33,
            ratings={"blitz": 1800},
        )

    def start_sync_job(
        self,
        username,
        *,
        limit=5000,
        perf_type=None,
        include_moves=False,
        page_size=1000,
    ):
        return SyncJobStatus(
            id="job-1",
            username=username.lower(),
            status="queued",
            limit=limit,
            perf_type=perf_type,
            include_moves=include_moves,
            page_size=page_size,
            updated_at=datetime.now(timezone.utc),
        )

    def get_sync_job(self, job_id):
        if job_id != "job-1":
            return None
        return SyncJobStatus(
            id=job_id,
            username="fieber69",
            status="complete",
            limit=5000,
            fetched_games=1000,
            upserted_games=1000,
            batches_completed=1,
            updated_at=datetime.now(timezone.utc),
        )


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


def test_profile_summary_and_sync_job_contracts():
    app = create_app(Settings(db_url="sqlite:///:memory:"), service=FakeService())
    client = TestClient(app)

    summary = client.get("/players/Fieber69/profile-summary")
    assert summary.status_code == 200
    assert summary.json()["total_games"] == 15
    assert summary.json()["player"]["username"] == "fieber69"

    started = client.post("/players/Fieber69/sync-jobs?limit=5000&include_moves=false&page_size=1000")
    assert started.status_code == 200
    assert started.json()["id"] == "job-1"
    assert started.json()["include_moves"] is False

    status = client.get("/sync-jobs/job-1")
    assert status.status_code == 200
    assert status.json()["status"] == "complete"
    assert status.json()["fetched_games"] == 1000

    missing = client.get("/sync-jobs/missing")
    assert missing.status_code == 404


def test_default_cors_allows_chrome_and_firefox_extension_origins():
    app = create_app(Settings(db_url="sqlite:///:memory:"), service=FakeService())
    client = TestClient(app)

    for origin in [
        "chrome-extension://abcdefghijklmnopabcdefghijklmnop",
        "moz-extension://d5f2a3b1-1c2d-4e5f-8a9b-0c1d2e3f4a5b",
    ]:
        response = client.options(
            "/players/fieber69/analysis",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin

        get_response = client.get(
            "/players/fieber69/analysis",
            headers={"Origin": origin},
        )

        assert get_response.status_code == 200
        assert get_response.headers["access-control-allow-origin"] == origin


def test_default_cors_blocks_untrusted_origins():
    app = create_app(Settings(db_url="sqlite:///:memory:"), service=FakeService())
    client = TestClient(app)

    response = client.options(
        "/players/fieber69/analysis",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


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
