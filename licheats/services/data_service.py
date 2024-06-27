from licheats.shared.statistics import color_stats
from licheats.data.load import DatabaseManager

class DataService:
    def __init__(self):
        self.data_manager = DatabaseManager()
    
    def get_username_data(self, username):
        # returns (player, games) if username is in db, else return None
        pass
    
    def add_player_data(self,player, games):
        pass
    
    def add_games(self):
        pass