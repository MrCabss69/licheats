import pandas as pd 
from sqlalchemy import JSON, Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.inspection import inspect

Base = declarative_base()


class Player(Base):
    __tablename__ = 'players'
    username = Column(String, primary_key=True, unique=True)
    title = Column(String)
    flair = Column(String)
    patron = Column(Boolean)
    created_at = Column(DateTime)
    seen_at = Column(DateTime)
    play_time_total = Column(Integer)
    play_time_tv = Column(Integer)
    url = Column(String)
    followable = Column(Boolean)
    following = Column(Boolean)
    blocking = Column(Boolean)
    follows_you = Column(Boolean)
    perfs = Column(JSON)
    counts = Column(JSON)
    streamer_info = Column(JSON)
    
    games_as_white = relationship("Game", back_populates="white_player", foreign_keys="[Game.players_white_id]")
    games_as_black = relationship("Game", back_populates="black_player", foreign_keys="[Game.players_black_id]")
    
    
    def to_dict(self):
        return {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs}
    
    @staticmethod
    def to_dataframe(players):
        """ Convert a list of Player instances to a pandas DataFrame. """
        return pd.DataFrame([player.to_dict() for player in players])
    
    def __repr__(self):
        return f"<Player(username='{self.username}', title='{self.title}', patron={self.patron}, created_at={self.created_at})>"

    def __str__(self):
        return f"Player {self.username} (Title: {self.title}, Patron: {'Yes' if self.patron else 'No'})"
    
class Game(Base):
    __tablename__ = 'games'
    id = Column(String, primary_key=True)
    rated = Column(Boolean)
    variant = Column(String)
    speed = Column(String)
    perf = Column(String)
    created_at = Column(DateTime)
    last_move_at = Column(DateTime)
    status = Column(String)
    winner = Column(String)
    moves = Column(String)
    initial_fen = Column(String)
    opening_eco = Column(String, nullable=True)
    opening_name = Column(String, nullable=True)
    opening_ply = Column(Integer, nullable=True)
    clock_initial = Column(Integer, nullable=True)
    clock_increment = Column(Integer, nullable=True)
    clock_total_time = Column(Integer, nullable=True)
    players_white_rating = Column(Integer, nullable=True)
    players_black_rating = Column(Integer, nullable=True)
    tournament_id = Column(String, nullable=True)

    players_white_id = Column(String, ForeignKey('players.username'))
    players_black_id = Column(String, ForeignKey('players.username'))
    
    

    white_player = relationship("Player", foreign_keys=[players_white_id], back_populates="games_as_white")
    black_player = relationship("Player", foreign_keys=[players_black_id], back_populates="games_as_black")
    
    
    __table_args__ = (
        Index('idx_players_white_id', 'players_white_id'),
        Index('idx_players_black_id', 'players_black_id'),
    )
    
    def to_dict(self):
        return {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs}
    
    @staticmethod
    def to_dataframe(games):
        """ Convert a list of Game instances to a pandas DataFrame. """
        return pd.DataFrame([game.to_dict() for game in games])
    
    def __repr__(self):
        return (f"<Game(id='{self.id}', variant='{self.variant}', speed='{self.speed}', "
                f"status='{self.status}', winner='{self.winner}, players_white='{self.players_white_id}')>")

    def __str__(self):
        return (f"Game {self.id} ({self.variant} | {self.speed}) - Winner: {self.winner}")
