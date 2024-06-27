from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime

Base = declarative_base()


class Player(Base):
    __tablename__ = 'players'
    username = Column(String, primary_key=True)
    
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
    opening_eco = Column(String)
    opening_name = Column(String)
    opening_ply = Column(Integer)
    clock_initial = Column(Integer)
    clock_increment = Column(Integer)
    clock_totalTime = Column(Integer)
    players_white_username = Column(String)
    players_black_username = Column(String)
    players_white_rating = Column(Integer)
    players_black_rating = Column(Integer)

    
class Move:
    pass