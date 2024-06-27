

class PlayerProcessor:
    @staticmethod
    def process(data):
        """Transforma los datos de la API de Lichess a un formato ORM."""
        transformed_data = {
            'id': data['id'],
            'username': data['username'],
            'rating': data.get('perfs', {}).get('blitz', {}).get('rating', 1500),  # Ejemplo con blitz
            'games_played': sum(data.get('count', {}).values()),  # Total de partidas jugadas
        }
        return transformed_data
