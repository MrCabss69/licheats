
from licheats.services import LichessApiService, DataService, StatService

class Client:

    def __init__(self) -> None:
        self.api_service = LichessApiService()
        self.data_service = DataService()
        self.stat_service = StatService()
    
    def get_player(self, username:str):
        player = self.data_service.get_player(username)
        if not player:
            player = self.api_service.get_player(username)
        return player

    def get_games(self, username:str):
        player = self.get_player(username)
        games = self.data_service.get_player_games(player)
        if not games:
            games = self.api_service.get_games(username)
        return games

    def save_player(self,player):
        self.data_service.save_player(player)

    def save_games(self,games):
        self.data_service.save_games(games)
