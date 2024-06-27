from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker # , relationship
from contextlib import contextmanager
from licheats.shared import Player, Game

Base = declarative_base()

class DatabaseManager:
    def __init__(self, engine_url='sqlite:///ajedrez.db'):
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

    def add_player(self, player):
        with self.session_scope() as session:
            session.add(player)

    def add_game(self, game):
        with self.session_scope() as session:
            session.add(game)

    def find_player_by_username(self, username):
        with self.session_scope() as session:
            return session.query(Player).filter(Player.username == username).one_or_none()

    def find_games_by_player(self, player_id):
        with self.session_scope() as session:
            return session.query(Game).filter_by(players_white_id=player_id).all() + \
                   session.query(Game).filter_by(players_black_id=player_id).all()

    def delete_player(self, player_id):
        with self.session_scope() as session:
            player = session.query(Player).filter(Player.id == player_id).one()
            session.delete(player)
