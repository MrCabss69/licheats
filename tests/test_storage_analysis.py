import json
import time
from pathlib import Path
from threading import Thread

import pytest

from licheats.app import Licheats
from licheats.analysis import Analyzer
from licheats.lichess import LichessError, normalize_game, normalize_player
from licheats.schemas import AnalysisSummary, GameRecord
from licheats.settings import Settings
from licheats.storage import Repository

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture_player():
    return normalize_player(json.loads((FIXTURES / "player.json").read_text()))


def _fixture_games():
    return [normalize_game(json.loads(line)) for line in (FIXTURES / "games.ndjson").read_text().splitlines()]


def test_repository_uses_temp_sqlite_and_upserts():
    repo = Repository("sqlite:///:memory:")
    player = _fixture_player()
    games = _fixture_games()

    assert repo.upsert_player(player) == 1
    assert repo.upsert_games(games) == 2
    assert repo.get_player("FIEBER69").username == "fieber69"
    assert len(repo.get_games_for_player("fieber69", limit=10)) == 2


def test_repository_filters_cached_games_by_perf_type():
    repo = Repository("sqlite:///:memory:")
    player = _fixture_player()
    games = _fixture_games()
    rapid_game = games[0].model_copy(update={"id": "rapid-game", "perf": "rapid", "speed": "rapid"})

    repo.upsert_player(player)
    repo.upsert_games([*games, rapid_game])

    assert len(repo.get_games_for_player("fieber69", limit=10)) == 3
    assert [game.id for game in repo.get_games_for_player("fieber69", limit=10, perf_type="rapid")] == [
        "rapid-game"
    ]
    assert len(repo.get_games_for_player("fieber69", limit=10, perf_type="blitz")) == 2


def test_repository_light_upsert_preserves_existing_moves():
    repo = Repository("sqlite:///:memory:")
    player = _fixture_player()
    game = _fixture_games()[0]
    light_game = game.model_copy(update={"moves": ""})

    repo.upsert_player(player)
    repo.upsert_games([game])
    repo.upsert_games([light_game], preserve_existing_moves=True)

    cached = repo.get_games_for_player("fieber69", limit=1)[0]
    assert cached.moves == game.moves


def test_repository_sqlite_can_be_used_by_background_sync_thread(tmp_path):
    repo = Repository(f"sqlite:///{tmp_path / 'licheats.sqlite3'}")
    player = _fixture_player()
    games = _fixture_games()
    repo.upsert_player(player)
    assert repo.get_player("fieber69") is not None

    errors = []

    def worker():
        try:
            repo.upsert_games(games)
            assert len(repo.get_games_for_player("fieber69", limit=10)) == 2
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    thread = Thread(target=worker)
    thread.start()
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert errors == []


def test_analyzer_returns_json_safe_result_buckets():
    player = _fixture_player()
    games = _fixture_games()
    analysis = Analyzer().analyze(player, games, source="cache")

    assert isinstance(analysis.summary, AnalysisSummary)
    assert analysis.summary.total_games == 2
    assert analysis.summary.wins == 1
    assert analysis.summary.draws == 1
    assert analysis.by_color["white"].wins == 1
    assert analysis.castling["kingside"].wins == 1
    assert analysis.summary.avg_opponent_rating == 1700
    assert analysis.model_dump(mode="json")["summary"]["total_games"] == 2


def test_analyzer_counts_draws_but_not_aborted_games():
    player = _fixture_player()
    draw_game = _fixture_games()[1]
    aborted_game = draw_game.model_copy(update={"id": "aborted", "status": "aborted"})

    analysis = Analyzer().analyze(player, [draw_game, aborted_game], source="cache")

    assert analysis.summary.total_games == 2
    assert analysis.summary.draws == 1
    assert analysis.summary.unknown == 1


def test_analyzer_detects_queenside_castling_and_invalid_moves():
    player = _fixture_player()
    kingside_game = _fixture_games()[0]
    queenside_game = kingside_game.model_copy(
        update={
            "id": "queenside",
            "moves": "d4 d5 Nc3 Nf6 Bf4 e6 Qd2 Be7 O-O-O O-O",
        }
    )
    invalid_game = kingside_game.model_copy(update={"id": "invalid", "moves": "not-a-move"})

    analysis = Analyzer().analyze(player, [kingside_game, queenside_game, invalid_game])

    assert analysis.castling["kingside"].wins == 1
    assert analysis.castling["queenside"].wins == 1
    assert analysis.unsupported_metrics


def test_analyzer_characterizes_fixture_metrics_and_timeline_order():
    player = _fixture_player()
    analysis = Analyzer().analyze(player, list(reversed(_fixture_games())))

    assert analysis.summary.total_games == 2
    assert analysis.summary.wins == 1
    assert analysis.summary.draws == 1
    assert analysis.summary.win_rate == 50.0
    assert analysis.by_color["white"].wins == 1
    assert analysis.by_color["black"].draws == 1
    assert analysis.openings["C60 Ruy Lopez"].wins == 1
    assert analysis.queen_presence["both_queens_present_final"].total == 2
    assert analysis.time_controls == {"5+0": 2}
    assert [point.rating for point in analysis.rating_timeline] == [1800, 1810]


def test_analyzer_segments_openings_by_opponent_color():
    player = _fixture_player()
    analysis = Analyzer().analyze(player, _fixture_games())

    assert analysis.openings_by_color["white"]["C60 Ruy Lopez"].wins == 1
    # The color-split buckets must reconcile with the color-agnostic table.
    assert analysis.openings["C60 Ruy Lopez"].wins == 1
    assert "C60 Ruy Lopez" not in analysis.openings_by_color["black"]


class FakeRepository:
    def __init__(self):
        self.player = None
        self.games: list[GameRecord] = []
        self.upserted_players = 0
        self.upserted_games = 0

    def get_player(self, username):
        return self.player

    def get_games_for_player(self, username, limit=100, perf_type=None):
        games = [game for game in self.games if perf_type is None or game.perf == perf_type]
        return games[:limit]

    def upsert_player(self, player):
        self.player = player
        self.upserted_players += 1
        return 1

    def upsert_games(self, games, *, preserve_existing_moves=False):
        self.games = list(games)
        self.upserted_games += len(self.games)
        return len(self.games)


class FakeGateway:
    def __init__(self, player, games):
        self.player = player
        self.games = games
        self.player_calls = 0
        self.game_calls = 0

    def get_player(self, username):
        self.player_calls += 1
        return self.player

    def get_games(self, username, *, limit=100, perf_type=None, include_moves=True, page_size=1000):
        self.game_calls += 1
        return self.games[:limit]

    def iter_games(self, username, *, limit=100, perf_type=None, include_moves=True, page_size=1000):
        yield from self.get_games(
            username,
            limit=limit,
            perf_type=perf_type,
            include_moves=include_moves,
            page_size=page_size,
        )


def test_refresh_refetches_and_upserts_before_analysis():
    player = _fixture_player()
    games = _fixture_games()
    repository = FakeRepository()
    gateway = FakeGateway(player, games)
    app = Licheats(
        Settings(db_url="sqlite:///:memory:"),
        repository=repository,
        gateway=gateway,
        analyzer=Analyzer(),
    )

    analysis = app.analyze_player("fieber69", limit=1, refresh=True)

    assert analysis.source == "refresh"
    assert analysis.games_count == 1
    assert gateway.player_calls == 1
    assert gateway.game_calls == 1
    assert repository.upserted_players == 1
    assert repository.upserted_games == 1


def test_profile_summary_uses_profile_counts_without_fetching_games():
    player = _fixture_player()
    games = _fixture_games()
    metrics = []
    gateway = FakeGateway(player, games)
    app = Licheats(
        Settings(db_url="sqlite:///:memory:"),
        repository=FakeRepository(),
        gateway=gateway,
        analyzer=Analyzer(),
        metrics_callback=metrics.append,
    )

    summary = app.profile_summary("Fieber69")

    assert summary.total_games == 15
    assert summary.wins == 8
    assert summary.losses == 5
    assert summary.draws == 2
    assert summary.win_rate == 53.33
    assert summary.ratings["blitz"] == 1800
    assert gateway.player_calls == 1
    assert gateway.game_calls == 0
    assert metrics[0]["operation"] == "profile_summary"
    assert metrics[0]["total_known"] == 15


def test_sync_player_emits_phase_metrics():
    player = _fixture_player()
    games = _fixture_games()
    metrics = []
    app = Licheats(
        Settings(db_url="sqlite:///:memory:"),
        repository=FakeRepository(),
        gateway=FakeGateway(player, games),
        analyzer=Analyzer(),
        metrics_callback=metrics.append,
    )

    result = app.sync_player("fieber69", limit=2, perf_type="blitz")

    assert result.fetched_games == 2
    assert len(metrics) == 1
    sync_metrics = metrics[0]
    assert sync_metrics["operation"] == "sync_player"
    assert sync_metrics["username"] == "fieber69"
    assert sync_metrics["limit"] == 2
    assert sync_metrics["perf_type"] == "blitz"
    assert sync_metrics["include_moves"] is True
    assert sync_metrics["fetched_games"] == 2
    for key in [
        "fetch_player_ms",
        "fetch_games_ms",
        "upsert_player_ms",
        "upsert_games_ms",
        "total_ms",
    ]:
        assert sync_metrics[key] >= 0


def test_analyze_player_emits_cache_metrics_without_changing_json_contract():
    player = _fixture_player()
    games = _fixture_games()
    repository = FakeRepository()
    repository.player = player
    repository.games = games
    metrics = []
    app = Licheats(
        Settings(db_url="sqlite:///:memory:"),
        repository=repository,
        gateway=FakeGateway(player, games),
        analyzer=Analyzer(),
        metrics_callback=metrics.append,
    )

    analysis = app.analyze_player("fieber69", limit=2, refresh=False)

    payload = analysis.model_dump(mode="json")
    assert payload["games_count"] == 2
    assert "summary" in payload
    assert "openings_by_color" in payload
    assert len(metrics) == 1
    analysis_metrics = metrics[0]
    assert analysis_metrics["operation"] == "analyze_player"
    assert analysis_metrics["source"] == "cache"
    assert analysis_metrics["games_count"] == 2
    assert analysis_metrics["initial_cached_games"] == 2
    assert analysis.coverage.games_analyzed == 2
    assert analysis.coverage.total_known == 15
    assert analysis.coverage.is_syncing is False
    assert "sync_ms" not in analysis_metrics
    for key in [
        "initial_get_player_ms",
        "query_games_ms",
        "analyzer_ms",
        "total_ms",
    ]:
        assert analysis_metrics[key] >= 0


def test_analyze_player_emits_sync_and_analysis_metrics_on_refresh():
    player = _fixture_player()
    games = _fixture_games()
    metrics = []
    app = Licheats(
        Settings(db_url="sqlite:///:memory:"),
        repository=FakeRepository(),
        gateway=FakeGateway(player, games),
        analyzer=Analyzer(),
        metrics_callback=metrics.append,
    )

    analysis = app.analyze_player("fieber69", limit=2, refresh=True)

    assert analysis.source == "refresh"
    assert [item["operation"] for item in metrics] == ["sync_player", "analyze_player"]
    assert metrics[1]["sync_ms"] >= 0
    assert metrics[1]["post_sync_query_ms"] >= 0


class BrokenGateway:
    def get_player(self, username):
        raise LichessError("boom", code="lichess_transport_error")

    def get_games(self, username, *, limit=100, perf_type=None, include_moves=True, page_size=1000):
        raise AssertionError("get_games should not be called")


def test_sync_player_emits_error_metrics_for_lichess_failures():
    metrics = []
    app = Licheats(
        Settings(db_url="sqlite:///:memory:"),
        repository=FakeRepository(),
        gateway=BrokenGateway(),
        analyzer=Analyzer(),
        metrics_callback=metrics.append,
    )

    with pytest.raises(LichessError):
        app.sync_player("fieber69")

    assert metrics[0]["operation"] == "sync_player"
    assert metrics[0]["lichess_error_code"] == "lichess_transport_error"
    assert metrics[0]["total_ms"] >= 0


def test_cached_analysis_honors_perf_type_without_refreshing():
    player = _fixture_player()
    games = _fixture_games()
    rapid_game = games[0].model_copy(update={"id": "rapid-game", "perf": "rapid", "speed": "rapid"})
    repository = FakeRepository()
    repository.player = player
    repository.games = [*games, rapid_game]
    gateway = FakeGateway(player, repository.games)
    app = Licheats(
        Settings(db_url="sqlite:///:memory:"),
        repository=repository,
        gateway=gateway,
        analyzer=Analyzer(),
    )

    analysis = app.analyze_player("fieber69", limit=10, refresh=False, perf_type="rapid")

    assert analysis.source == "cache"
    assert analysis.games_count == 1
    assert gateway.player_calls == 0
    assert gateway.game_calls == 0


def test_background_sync_job_flushes_light_batches_and_reports_status():
    player = _fixture_player()
    games = _fixture_games()
    repository = FakeRepository()
    metrics = []
    app = Licheats(
        Settings(db_url="sqlite:///:memory:"),
        repository=repository,
        gateway=FakeGateway(player, games),
        analyzer=Analyzer(),
        metrics_callback=metrics.append,
    )

    job = app.start_sync_job("fieber69", limit=2, include_moves=False, page_size=1)

    for _ in range(50):
        status = app.get_sync_job(job.id)
        if status and status.status in {"complete", "failed"}:
            break
        time.sleep(0.01)

    assert status is not None
    assert status.status == "complete"
    assert status.fetched_games == 2
    assert status.upserted_games == 2
    assert status.batches_completed == 2
    assert status.include_moves is False
    assert status.total_known == 15
    assert repository.upserted_players == 1
    assert [item["operation"] for item in metrics if item["operation"].startswith("sync_job")] == [
        "sync_job_batch",
        "sync_job_batch",
        "sync_job",
    ]
