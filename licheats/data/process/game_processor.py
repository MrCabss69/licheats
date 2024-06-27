
class GameProcessor:
    @staticmethod
    def process(data):
        """Transforma los datos de partidas de la API de Lichess a un formato ORM."""
        transformed_data = {
            'game_id': data['id'],
            'rated': data['rated'],
            'variant': data['variant'],
            'speed': data['speed'],
            'perf': data['perf'],
            'created_at': data['createdAt'],
            'last_move_at': data['lastMoveAt'],
            'status': data['status'],
            'winner': data['winner'],
            'moves': data['moves'],
            'opening_name': data.get('opening', {}).get('name', 'Unknown'),
        }
        return transformed_data
