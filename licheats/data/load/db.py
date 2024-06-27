from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from licheats.shared import Base, Player, Game

class DatabaseManager:
    def __init__(self, engine_url='sqlite:////home/jd/Documentos/CODIGO/Lichess-Openings/licheats/data/load/ajedrez.db'):
        self.engine = create_engine(engine_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        

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
            session.close()

    def save_player(self, player: Player):
        with self.session_scope() as session:
            session.add(player)

    def save_game(self, game: Game):
        with self.session_scope() as session:
            session.add(game)

    def get_player(self, username: str) -> Player:
        with self.session_scope() as session:
            return session.query(Player).filter_by(username=username).one_or_none()

    def get_player_games(self, player_id: str):
        with self.session_scope() as session:
            games_white = session.query(Game).filter_by(players_white_username=player_id).all()
            games_black = session.query(Game).filter_by(players_black_username=player_id).all()
            return games_white + games_black

    def delete_player(self, player_id: str):
        with self.session_scope() as session:
            player = session.query(Player).filter_by(id=player_id).one_or_none()
            if player:
                session.delete(player)
