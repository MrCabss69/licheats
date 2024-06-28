from licheats.shared import Game  # Asumiendo que el modelo Game está en models.py

class GameProcessor:
    @staticmethod
    def process(data):
        """Process and store a game record from a dictionary into the ORM model."""
        # Verificar campos requeridos
        required_fields = ['id', 'rated', 'variant', 'speed', 'perf', 'createdAt',
                           'lastMoveAt', 'status', 'players', 'moves', 'clock', 'opening']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        try:
            # Crear instancia del juego
            game = Game(
                id=data['id'],
                rated=data['rated'],
                variant=data['variant'],
                speed=data['speed'],
                perf=data['perf'],
                created_at=data['createdAt'],
                last_move_at=data['lastMoveAt'],
                status=data['status'],
                winner=data.get('winner'),
                moves=data['moves'],
                initial_fen=data.get('initialFen'),
                clock_initial=data['clock']['initial'],
                clock_increment=data['clock']['increment'],
                clock_total_time=data['clock']['totalTime'],
                players_white_id=data['players']['white']['user']['id'],
                players_black_id=data['players']['black']['user']['id'],
                players_white_rating=data['players']['white']['rating'],
                players_black_rating=data['players']['black']['rating'],
                tournament_id=data.get('tournament'),
                # Incorporar información de la apertura
                opening_eco=data['opening']['eco'] if 'opening' in data else None,
                opening_name=data['opening']['name'] if 'opening' in data else None,
                opening_ply=data['opening']['ply'] if 'opening' in data else None
            )
            return game
        except KeyError as e:
            raise ValueError(f"Invalid or missing data for key: {str(e)}")
