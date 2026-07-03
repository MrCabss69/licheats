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


def test_gateway_exposes_lichess_404_details():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    settings = Settings(db_url="sqlite:///:memory:", lichess_base_url="https://lichess.test")
    gateway = LichessGateway(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(LichessError) as exc_info:
        gateway.get_player("missing")

    assert exc_info.value.code == "lichess_http_error"
    assert exc_info.value.details["status_code"] == 404
