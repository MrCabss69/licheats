import json
from pathlib import Path

import httpx
import pytest

from licheats.lichess import LichessError, LichessGateway, lichess_time_to_datetime
from licheats.settings import Settings

FIXTURES = Path(__file__).parent / "fixtures"


def test_gateway_parses_ndjson_and_normalizes_millis():
    player_payload = (FIXTURES / "player.json").read_text()
    games_payload = (FIXTURES / "games.ndjson").read_text()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/user/fieber69":
            return httpx.Response(200, json=json.loads(player_payload))
        if request.url.path == "/api/games/user/fieber69":
            assert request.url.params["max"] == "2"
            assert request.url.params["moves"] == "true"
            assert request.url.params["perfType"] == "blitz"
            return httpx.Response(200, text=games_payload)
        return httpx.Response(404)

    settings = Settings(db_url="sqlite:///:memory:", lichess_base_url="https://lichess.test")
    gateway = LichessGateway(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))

    player = gateway.get_player("fieber69")
    games = gateway.get_games("fieber69", limit=2, perf_type="blitz")

    assert player.username == "fieber69"
    assert len(games) == 2
    assert games[0].created_at == lichess_time_to_datetime(1720118791833)
    assert games[0].white_id == "fieber69"


def test_gateway_supports_light_pull_without_moves():
    games_payload = (FIXTURES / "games.ndjson").read_text()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/games/user/fieber69"
        assert request.url.params["moves"] == "false"
        return httpx.Response(200, text=games_payload)

    settings = Settings(db_url="sqlite:///:memory:", lichess_base_url="https://lichess.test")
    gateway = LichessGateway(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))

    games = gateway.get_games("fieber69", limit=2, include_moves=False)

    assert len(games) == 2
    assert games[0].opening_name == "Ruy Lopez"


def test_gateway_paginates_games_with_until_cursor():
    page_one = "\n".join((FIXTURES / "games.ndjson").read_text().splitlines())
    older = json.loads((FIXTURES / "games.ndjson").read_text().splitlines()[0])
    older["id"] = "g0"
    older["createdAt"] = 1720018791833
    seen_until = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/games/user/fieber69"
        if "until" not in request.url.params:
            return httpx.Response(200, text=page_one)
        seen_until.append(request.url.params["until"])
        return httpx.Response(200, text=json.dumps(older))

    settings = Settings(db_url="sqlite:///:memory:", lichess_base_url="https://lichess.test")
    gateway = LichessGateway(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))

    games = gateway.get_games("fieber69", limit=3, page_size=2)

    assert [game.id for game in games] == ["g1", "g2", "g0"]
    assert seen_until == ["1720118791832"]


def test_gateway_exposes_lichess_404_details():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    settings = Settings(db_url="sqlite:///:memory:", lichess_base_url="https://lichess.test")
    gateway = LichessGateway(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(LichessError) as exc_info:
        gateway.get_player("missing")

    assert exc_info.value.code == "lichess_http_error"
    assert exc_info.value.details["status_code"] == 404


def test_streaming_games_expose_lichess_404_details():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="missing games")

    settings = Settings(db_url="sqlite:///:memory:", lichess_base_url="https://lichess.test")
    gateway = LichessGateway(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(LichessError) as exc_info:
        gateway.get_games("missing", limit=1)

    assert exc_info.value.code == "lichess_http_error"
    assert exc_info.value.details["status_code"] == 404
    assert exc_info.value.details["body"] == "missing games"
