from licheats.shared.statistics import color_stats


    
class StatService:
    
    def __init__(self):
        pass
    
    def get_player_resume(self, player, games):
        
        return {
            "color_stats": color_stats(player),
            # "queen_trade_stats": self.queen_trade_stats(self.db_manager, username),
            # "castling_stats": self.castling_stats(self.db_manager, username),
            # "loosing_matter_stats": self.loosing_matter_stats(self.db_manager, username),
            # "winning_matter_stats": self.winning_matter_stats(self.db_manager, username),
            # "speed_stats": self.speed_stats(self.db_manager, username),
            # "time_preference_stats": self.time_preference_stats(self.db_manager, username)
        }