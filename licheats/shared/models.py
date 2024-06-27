from sqlalchemy import JSON, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Player(Base):
    __tablename__ = 'players'
    id = Column(String, primary_key=True)
    username = Column(String, unique=True)
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

    players_white_id = Column(String, ForeignKey('players.id'))
    players_black_id = Column(String, ForeignKey('players.id'))

    white_player = relationship("Player", foreign_keys=[players_white_id], back_populates="games_as_white")
    black_player = relationship("Player", foreign_keys=[players_black_id], back_populates="games_as_black")