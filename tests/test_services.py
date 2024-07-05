import unittest
from licheats.services import LichessApiService, DataService, StatService
from licheats.shared import Player, Game


class TestDataService(unittest.TestCase):

    def setUp(self):
        self.service = DataService()

    def test_get_player(self):
        # Suponiendo que la base de datos siempre responde correctamente
        player = self.service.get_player('Fieber69')
        self.assertIsInstance(player, Player)

    def test_save_player(self):
        # Verificación de que no se lanzan excepciones; no verifica efectos secundarios
        player = Player(username='Fieber69')
        try:
            self.service.save_player(player)
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"save_player raised an exception {e}")
            
class TestLichessApiService(unittest.TestCase):

    def test_get_player(self):
        # Este método asume que la llamada a la API siempre funciona correctamente
        player = LichessApiService.get_player('Fieber69')
        self.assertIsInstance(player, Player)
        self.assertIsNotNone(player.username)

    def test_get_games(self):
        # Este método asume que siempre se obtiene una lista de juegos válida
        games = LichessApiService.get_games('Fieber69')
        self.assertIsInstance(games, list)
        for game in games:
            self.assertIsInstance(game, Game)


class TestStatService(unittest.TestCase):

    def test_analyze_player_games(self):
        # Supone que la recuperación y el análisis de datos siempre son correctos
        data_service = DataService()  # Esto necesitaría una instancia real
        stats = StatService.analyze_player_games(data_service, 'Fieber69')
        print(stats)
        self.assertIsInstance(stats, dict)

        
if __name__ == '__main__':
    unittest.main()
