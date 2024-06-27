from typing import Union
from licheats.data import LichessClient,GameProcessor,PlayerProcessor 
from licheats.shared import Player, Game

class LichessApiService:
    """
    Usa LichessClient para extraer datos de la API,
    GameProcessor para transformar juegos en objetos Game,
    y PlayerProcessor para transformar datos de jugador en objetos Player.
    """

    @staticmethod
    def fetch_user_data(username: str) -> Union[Player, Union[Game]]:
        """
        Método estático para recuperar datos del usuario.
        
        Args:
        - username (str): Nombre de usuario en Lichess.
        
        Returns:
        - Player or Game: Objeto Player si se obtiene información de jugador,
          o Game si se obtiene información de juego.
        """
        lichess_client   = LichessClient()
        game_processor   = GameProcessor()
        player_processor = PlayerProcessor() 
        
        # Ejemplo de uso del cliente para obtener datos
        player_info = lichess_client.get_profile(username)
        player_games = lichess_client.get_games(username)
        
        if not player_info:
            return None, None
        player = player_processor.process(player_info)
        if not player_games:
            return player, None
        return player, [game_processor.process(g) for g in player_games]
        
        