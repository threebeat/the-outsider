import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from config.settings import DATABASE_URL

logger = logging.getLogger(__name__)

# Database Setup
Base = declarative_base()

# Create engine with appropriate settings
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # For PostgreSQL, use simpler configuration
    engine = create_engine(DATABASE_URL)

# Create simple session factory
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db_session():
    """Get a database session with error handling."""
    try:
        return SessionLocal()
    except Exception as e:
        logger.error(f"Error creating database session: {e}")
        raise

def close_db_session(session):
    """Safely close a database session with error handling."""
    try:
        if session:
            session.close()
    except Exception as e:
        logger.error(f"Error closing session: {e}")

from contextlib import contextmanager

@contextmanager
def get_db():
    """Context manager for database sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# Database Models
class Lobby(Base):
    __tablename__ = 'lobbies'
    id = Column(Integer, primary_key=True)
    room = Column(String, unique=True, index=True)
    state = Column(String, default='waiting')
    location = Column(String, nullable=True)
    outsider_sid = Column(String, nullable=True)
    turn = Column(Integer, default=0)
    player_order = Column(Text, default='')  # Comma-separated SIDs
    question_count = Column(Integer, default=0)  # Track questions for voting
    current_question_asker = Column(String, nullable=True)  # SID of the current question asker
    current_target = Column(String, nullable=True)  # SID of the current target
    messages = relationship('Message', back_populates='lobby', cascade="all, delete-orphan")
    players = relationship('Player', back_populates='lobby', cascade="all, delete-orphan")

class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    sid = Column(String, index=True)
    username = Column(String)
    is_ai = Column(Boolean, default=False)
    lobby_id = Column(Integer, ForeignKey('lobbies.id'))
    lobby = relationship('Lobby', back_populates='players')

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    lobby_id = Column(Integer, ForeignKey('lobbies.id'))
    lobby = relationship('Lobby', back_populates='messages')

class Vote(Base):
    __tablename__ = 'votes'
    id = Column(Integer, primary_key=True)
    voter_sid = Column(String)  # Who voted
    voted_for_sid = Column(String)  # Who they voted for
    lobby_id = Column(Integer, ForeignKey('lobbies.id'))
    lobby = relationship('Lobby')

class WinCounter(Base):
    __tablename__ = 'win_counters'
    id = Column(Integer, primary_key=True)
    human_wins = Column(Integer, default=0)
    ai_wins = Column(Integer, default=0)
    room = Column(String, default='main')  # In case we want multiple rooms later

# Create all tables
Base.metadata.create_all(engine)

# Database helper functions
def get_lobby(session, room="main"):
    """Get or create a lobby for the given room."""
    lobby = session.query(Lobby).filter_by(room=room).first()
    if not lobby:
        lobby = Lobby(room=room)
        session.add(lobby)
        session.commit()
    return lobby

def get_players(session, lobby):
    """Get all players in a lobby."""
    return session.query(Player).filter_by(lobby_id=lobby.id).all()

def get_player_by_sid(session, lobby, sid):
    """Return the Player object for a given sid in a lobby, or None if not found."""
    return session.query(Player).filter_by(lobby_id=lobby.id, sid=sid).first()

def add_message(session, lobby, content):
    """Add a message to the lobby."""
    msg = Message(content=content, lobby=lobby)
    session.add(msg)
    session.commit()

def clear_votes(session, lobby):
    """Clear all votes for a lobby."""
    session.query(Vote).filter_by(lobby_id=lobby.id).delete()
    session.commit()

def get_vote_count(session, lobby, target_sid):
    """Get the number of votes for a specific player."""
    return session.query(Vote).filter_by(lobby_id=lobby.id, voted_for_sid=target_sid).count()

def get_player_by_username(session, lobby, username):
    """Return the Player object for a given username in a lobby, or None if not found."""
    return session.query(Player).filter_by(lobby_id=lobby.id, username=username).first()

def get_messages(session, lobby):
    """Get all messages in a lobby."""
    return session.query(Message).filter_by(lobby_id=lobby.id).order_by(Message.id).all()

def get_win_counter(session, room="main"):
    """Get the win counter for a room, creating it if it doesn't exist."""
    counter = session.query(WinCounter).filter_by(room=room).first()
    if not counter:
        counter = WinCounter(room=room, human_wins=0, ai_wins=0)
        session.add(counter)
        session.commit()
    return counter

def increment_human_wins(session, room="main"):
    """Increment human wins for a room."""
    counter = get_win_counter(session, room)
    counter.human_wins += 1
    session.commit()
    return counter

def increment_ai_wins(session, room="main"):
    """Increment AI wins for a room."""
    counter = get_win_counter(session, room)
    counter.ai_wins += 1
    session.commit()
    return counter

def reset_win_counter(session, room="main"):
    """Reset the win counter for a room."""
    counter = get_win_counter(session, room)
    counter.human_wins = 0
    counter.ai_wins = 0
    session.commit()
    return counter 