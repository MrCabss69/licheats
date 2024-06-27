
from licheats.services import LichessApiService, DataService, StatService

class Client:
    def __init__(self) -> None:
        self.api_service = LichessApiService()
        self.data_service = DataService()
        self.stat_service = StatService()
    
    def get_user_resume(self, username:str):

        # 1. Ver si el usuario está en la base de datos
        # 1.1 Si está - actualizar sus datos y almacenar nuevas partidas en la base de datos de haberlas
        # 1.2 Si no está - obtener los datos de usuario y todas las partidas y almacenarlas en la base de datos
        user_data = self.data_service.get_username_data(username) # returns (player, games)
        if not user_data:
            player, games, errors = self.api_service.fetch_user_data(username)
            self.data_service.add_player_data(player, games)
        else:
            player, games = user_data
            errors = None
            
        print(player, games, errors)

        
        # 2. Con los datos actualizados obtener estadísticas específicas:
        # color_stats - consultar en la base de datos las partidas y analizarlas, devolviendo los resultados obtenidos (win/draw/loss) con cada color,
        # queen_trade_stats - consultar en la base de datos las partidas y analizarlas, devolviendo en las que se ha cambiado damas en los primeros 20 movimientos, y los que no, y los resultados obtenidos (win/draw/loss)
        # castling_stats - consultar en la base de datos las partidas y analizarlas, devolviendo en las que ha hecho enroque CON CADA COLOR (en este caso es relevante), y los resultados obtenidos (win/draw/loss)
        # loosing_matter_stats - consultar en la base de datos las partidas y analizarlas, devolviendo los motivos de pérdida, las veces que se ha perdido (tiempo, abandono, jaque mate)
        # winning_matter_stats - consultar en la base de datos las partidas y analizarlas, devolviendo los motivos de ganancia, las veces que se ha perdido (tiempo, abandono, jaque mate)
        # speed_stats - consultar en la base de datos las partidas y analizarlas, devolviendo la pérdida en centipeones por movimiento del jugador por tramo de tiempo
        # insights = self.stat_service.get_player_resume(player, games)
        # print(player, games, insights)