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
    def fetch_user_data(username: str) -> Union[Player, list[Game], list[str]]:
        """
        Método estático para recuperar datos del usuario.
        
        Args:
        - username (str): Nombre de usuario en Lichess.
        
        Returns:
        - Union[Player, list[Game]]: Objeto Player si se obtiene información de jugador,
          o lista de Game si se obtiene información de juegos.
        """
        lichess_client = LichessClient()
        player_info    = lichess_client.get_profile(username)
        player_games   = lichess_client.get_games(username)
        if not player_info:
            return None

        player = PlayerProcessor().process(player_info)
        if not player_games:
            return player, None, ["Not player games available"]
        
        games, errors =  [], []
        for game_data in player_games:
            try:
                processed_game = GameProcessor.process(game_data)
                games.append(processed_game)
            except ValueError as e:
                errors.append(f"Error processing game {game_data.get('id', 'Unknown')}: {str(e)}")
        if not games and errors:
            raise Exception("No games could be processed successfully: " + ", ".join(errors))
        return player, games, errors