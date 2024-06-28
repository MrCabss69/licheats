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
    def get_player(username:str) -> Player:
        player_info    = LichessClient().get_profile(username)
        player         = PlayerProcessor().process(player_info)
        return player

    @staticmethod
    def get_games(username:str, max_games:int=None) -> Union[Game]:
        player_games   = LichessClient().get_games(username, max_games=None)
        if not player_games:
            return None
        games = []
        for game_data in player_games:
            try:
                processed_game = GameProcessor.process(game_data)
                games.append(processed_game)
            except:
                pass
        return games
