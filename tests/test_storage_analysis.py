import json
from pathlib import Path

from licheats.app import Licheats
from licheats.analysis import Analyzer
from licheats.lichess import normalize_game, normalize_player
from licheats.schemas import GameRecord
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


def test_analyzer_returns_json_safe_result_buckets():
    player = _fixture_player()
    games = _fixture_games()
    analysis = Analyzer().analyze(player, games, source="cache")

    assert analysis.summary["total_games"] == 2
    assert analysis.summary["wins"] == 1
    assert analysis.summary["draws"] == 1
    assert analysis.by_color["white"].wins == 1
    assert analysis.castling["kingside"].wins == 1
    assert analysis.summary["avg_opponent_rating"] == 1700
    analysis.model_dump(mode="json")


def test_analyzer_counts_draws_but_not_aborted_games():
    player = _fixture_player()
    draw_game = _fixture_games()[1]
    aborted_game = draw_game.model_copy(update={"id": "aborted", "status": "aborted"})

    analysis = Analyzer().analyze(player, [draw_game, aborted_game], source="cache")

    assert analysis.summary["total_games"] == 2
    assert analysis.summary["draws"] == 1
    assert analysis.summary["unknown"] == 1


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


class FakeRepository:
    def __init__(self):
        self.player = None
        self.games: list[GameRecord] = []
        self.upserted_players = 0
        self.upserted_games = 0

    def get_player(self, username):
        return self.player

    def get_games_for_player(self, username, limit=100):
        return self.games[:limit]

    def upsert_player(self, player):
        self.player = player
        self.upserted_players += 1
        return 1

    def upsert_games(self, games):
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

    def get_games(self, username, *, limit=100, perf_type=None):
        self.game_calls += 1
        return self.games[:limit]


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
