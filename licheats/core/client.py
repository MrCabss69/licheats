import pandas as pd
from licheats.services import LichessApiService, DataService, StatService
from licheats.shared import Player, Game

class Client:

    def __init__(self) -> None:
        self.api_service  = LichessApiService()
        self.data_service = DataService()
        self.stat_service = StatService()
        
    def resume_stats(self, player:Player, games:list[Game]) -> pd.DataFrame:
        self.stat_service.resume_stats(player, games)
    
    def get_player(self, username:str):
        player = self.data_service.get_player(username)
        if not player:
            player = self.api_service.get_player(username)
        return player

    def get_games(self, username:str):
        games = self.data_service.get_player_games(username)
        if not games:
            games = self.api_service.get_games(username)
        return games

    def save_player(self,player):
        self.data_service.save_player(player)

    def save_games(self,games):
        self.data_service.save_games(games)
