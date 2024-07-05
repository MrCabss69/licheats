import unittest
from licheats import Client
from licheats.shared import Player, Game

LICHESS_USER = 'Fieber69'

class TestClient(unittest.TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_player(self):
        player = self.client.get_player(LICHESS_USER)
        self.assertIsInstance(player, Player)
        self.assertIsNotNone(player)
        assert player.username == LICHESS_USER

    def test_get_games(self):
        games = self.client.get_player_games(LICHESS_USER)
        self.assertIsInstance(games, list)
        for g in games:
            self.assertIsInstance(g, Game)
            
# Run the tests
if __name__ == '__main__':
    unittest.main()
