from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from licheats.shared import Base, Player, Game

class DatabaseManager:
    def __init__(self, engine_url='sqlite:////home/jd/Documentos/CODIGO/Lichess-Openings/licheats/data/ajedrez.db'):
        self.engine = create_engine(engine_url, echo=False)
        Base.metadata.create_all(self.engine)
        # Crear una Session factory que no expire los objetos tras commit
        self.Session = scoped_session(sessionmaker(bind=self.engine, expire_on_commit=False))
        self.page_size = 100

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            print(f"Error during database operation: {e}")
            session.rollback()
            raise
        finally:
            # No cerrar la sesión aquí para reutilizar y mantener objetos persistentes
            pass

    def save_player(self, player: Player):
        with self.session_scope() as session:
            session.add(player)

    def save_game(self, game: Game):
        with self.session_scope() as session:
            session.add(game)

    def get_player(self, username: str) -> Player:
        with self.session_scope() as session:
            player = session.query(Player).options(
                joinedload(Player.games_as_white),
                joinedload(Player.games_as_black)
            ).filter_by(username=username).one_or_none()
            return player

    def get_player_games(self, player_id: str, max_games: int = 100):
        
        with self.session_scope() as session:
            # Consulta paginada con cargas anticipadas para evitar consultas adicionales
            games = session.query(Game).options(
                joinedload(Game.white_player),
                joinedload(Game.black_player)
            ).filter(
                (Game.players_white_id == player_id) | (Game.players_black_id == player_id)
            ).order_by(Game.created_at.desc())
            if max_games is not None:
                games = games.limit(max_games).all()
            else:
                games = games.all()
            return games


    def delete_player(self, player_id: str):
        with self.session_scope() as session:
            player = session.query(Player).filter_by(username=player_id).one_or_none()
            if player:
                session.delete(player)

    def close_session(self):
        """Manually close the session if needed."""
        self.Session.remove()
