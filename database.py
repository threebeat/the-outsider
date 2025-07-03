"""
Database models and initialization for The Outsider game.

This module contains all database models and helper functions for managing
lobbies, players, games, and statistics in the social deduction game.
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Float, Index
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    # Default to PostgreSQL for production, SQLite for development
    if os.getenv('RENDER'):
        logger.error("DATABASE_URL not set in production environment!")
        raise ValueError("DATABASE_URL environment variable is required")
    else:
        DATABASE_URL = 'sqlite:///game.db'
        logger.info("Using SQLite for development")

# Handle Render's PostgreSQL URL format
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Create database engine
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv('SQL_DEBUG', 'false').lower() == 'true',
        connect_args={"check_same_thread": False},
        poolclass=NullPool
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv('SQL_DEBUG', 'false').lower() == 'true',
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=30,
        pool_timeout=30,
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db_session():
    """Context manager for database sessions with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()

# Database Models

class Lobby(Base):
    """Represents a game lobby where players join and play."""
    
    __tablename__ = 'lobbies'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    
    # Game state
    state = Column(String(20), default='waiting')  # waiting, playing, voting, finished
    location = Column(String(100), nullable=True)  # Current game location
    max_players = Column(Integer, default=8)
    
    # Turn management
    current_turn = Column(Integer, default=0)
    question_count = Column(Integer, default=0)
    max_questions = Column(Integer, default=5)
    
    # AI Integration
    ai_difficulty = Column(String(20), default='normal')  # easy, normal, hard
    outsider_player_id = Column(Integer, ForeignKey('players.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    players = relationship('Player', back_populates='lobby', cascade='all, delete-orphan', foreign_keys='Player.lobby_id')
    messages = relationship('GameMessage', back_populates='lobby', cascade='all, delete-orphan')
    votes = relationship('Vote', back_populates='lobby', cascade='all, delete-orphan')
    sessions = relationship('GameSession', back_populates='lobby', cascade='all, delete-orphan')
    outsider = relationship('Player', foreign_keys=[outsider_player_id], post_update=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_lobby_state_activity', 'state', 'last_activity'),
        Index('idx_lobby_code_state', 'code', 'state'),
    )
    
    def __repr__(self):
        return f"<Lobby(code='{self.code}', state='{self.state}')>"
    
    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    @property
    def active_players(self) -> List['Player']:
        """Get all connected, active players."""
        return [p for p in self.players if p.is_connected and not p.is_spectator]
    
    @property
    def human_players(self) -> List['Player']:
        """Get all human (non-AI) players."""
        return [p for p in self.active_players if not p.is_ai]
    
    @property
    def ai_players(self) -> List['Player']:
        """Get all AI players."""
        return [p for p in self.active_players if p.is_ai]

class Player(Base):
    """Represents a player in the game."""
    
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), nullable=False, index=True)  # Socket.IO session ID
    username = Column(String(50), nullable=False)
    
    # Player type and status
    is_ai = Column(Boolean, default=False, nullable=False)
    is_spectator = Column(Boolean, default=False, nullable=False)
    is_connected = Column(Boolean, default=True, nullable=False)
    is_outsider = Column(Boolean, default=False, nullable=False)
    
    # Game statistics
    questions_asked = Column(Integer, default=0)
    questions_answered = Column(Integer, default=0)
    votes_received = Column(Integer, default=0)
    
    # AI-specific fields
    ai_personality = Column(String(50), nullable=True)  # aggressive, cautious, analytical, etc.
    ai_strategy = Column(Text, nullable=True)  # JSON string for AI strategy data
    
    # Timestamps
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Foreign key
    lobby_id = Column(Integer, ForeignKey('lobbies.id'), nullable=False)
    
    # Relationships
    lobby = relationship('Lobby', back_populates='players', foreign_keys=[lobby_id])
    sent_messages = relationship('GameMessage', foreign_keys='GameMessage.sender_id', back_populates='sender')
    received_messages = relationship('GameMessage', foreign_keys='GameMessage.target_id', back_populates='target')
    votes_cast = relationship('Vote', foreign_keys='Vote.voter_id', back_populates='voter')
    votes_against = relationship('Vote', foreign_keys='Vote.target_id', back_populates='target')
    
    # Indexes
    __table_args__ = (
        Index('idx_player_lobby_session', 'lobby_id', 'session_id'),
        Index('idx_player_lobby_username', 'lobby_id', 'username'),
        Index('idx_player_connected', 'is_connected', 'last_seen'),
    )
    
    def __repr__(self):
        return f"<Player(username='{self.username}', is_ai={self.is_ai})>"
    
    def update_last_seen(self):
        """Update the last seen timestamp."""
        self.last_seen = datetime.now(timezone.utc)

class GameMessage(Base):
    """Represents messages exchanged during the game."""
    
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default='chat')  # chat, question, answer, system, ai_thinking
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Foreign keys
    lobby_id = Column(Integer, ForeignKey('lobbies.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('players.id'), nullable=True)  # Null for system messages
    target_id = Column(Integer, ForeignKey('players.id'), nullable=True)  # For directed questions
    
    # Question/answer tracking
    is_question = Column(Boolean, default=False)
    question_number = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)  # AI confidence in response
    
    # Relationships
    lobby = relationship('Lobby', back_populates='messages')
    sender = relationship('Player', foreign_keys=[sender_id], back_populates='sent_messages')
    target = relationship('Player', foreign_keys=[target_id], back_populates='received_messages')
    
    # Indexes
    __table_args__ = (
        Index('idx_message_lobby_created', 'lobby_id', 'created_at'),
        Index('idx_message_type_lobby', 'message_type', 'lobby_id'),
    )
    
    def __repr__(self):
        return f"<GameMessage(type='{self.message_type}', sender='{self.sender.username if self.sender else 'System'}')>"

class Vote(Base):
    """Represents votes cast during the voting phase."""
    
    __tablename__ = 'votes'
    
    id = Column(Integer, primary_key=True)
    
    # Timestamps
    cast_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Foreign keys
    lobby_id = Column(Integer, ForeignKey('lobbies.id'), nullable=False)
    voter_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    target_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    
    # Vote metadata
    vote_round = Column(Integer, default=1)
    confidence = Column(Float, nullable=True)  # Optional confidence level (0.0-1.0)
    reasoning = Column(Text, nullable=True)  # AI reasoning for vote
    
    # Relationships
    lobby = relationship('Lobby', back_populates='votes')
    voter = relationship('Player', foreign_keys=[voter_id], back_populates='votes_cast')
    target = relationship('Player', foreign_keys=[target_id], back_populates='votes_against')
    
    # Indexes
    __table_args__ = (
        Index('idx_vote_lobby_round', 'lobby_id', 'vote_round'),
        Index('idx_vote_cast_at', 'cast_at'),
    )
    
    def __repr__(self):
        return f"<Vote(voter='{self.voter.username}', target='{self.target.username}')>"

class GameSession(Base):
    """Represents a complete game session with results."""
    
    __tablename__ = 'game_sessions'
    
    id = Column(Integer, primary_key=True)
    session_number = Column(Integer, nullable=False)  # Sequential number for this lobby
    
    # Game details
    location = Column(String(100), nullable=False)
    total_players = Column(Integer, nullable=False)
    human_players = Column(Integer, nullable=False)
    ai_players = Column(Integer, nullable=False)
    
    # Game results
    winner = Column(String(20), nullable=True)  # 'humans', 'ai', 'draw'
    winner_reason = Column(String(100), nullable=True)
    outsider_eliminated = Column(Boolean, nullable=True)
    ai_guessed_correctly = Column(Boolean, nullable=True)
    ai_final_guess = Column(String(100), nullable=True)
    
    # Game metrics
    total_questions = Column(Integer, default=0)
    total_votes = Column(Integer, default=0)
    duration_seconds = Column(Integer, nullable=True)
    
    # AI Analysis
    ai_performance_score = Column(Float, nullable=True)  # How well AI performed
    human_suspicion_level = Column(Float, nullable=True)  # How suspicious humans were
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Foreign key
    lobby_id = Column(Integer, ForeignKey('lobbies.id'), nullable=False)
    eliminated_player_id = Column(Integer, ForeignKey('players.id'), nullable=True)
    
    # Relationships
    lobby = relationship('Lobby', back_populates='sessions')
    eliminated_player = relationship('Player', foreign_keys=[eliminated_player_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_session_lobby_started', 'lobby_id', 'started_at'),
        Index('idx_session_winner_ended', 'winner', 'ended_at'),
    )
    
    def __repr__(self):
        return f"<GameSession(session={self.session_number}, winner='{self.winner}')>"

class GameStatistics(Base):
    """Global game statistics and win counters."""
    
    __tablename__ = 'statistics'
    
    id = Column(Integer, primary_key=True)
    lobby_code = Column(String(50), default='main', index=True)
    
    # Win counters
    human_wins = Column(Integer, default=0)
    ai_wins = Column(Integer, default=0)
    total_games = Column(Integer, default=0)
    
    # Performance metrics
    avg_game_duration = Column(Float, nullable=True)  # Average duration in seconds
    avg_questions_per_game = Column(Float, nullable=True)
    human_win_rate = Column(Float, nullable=True)  # Percentage
    avg_players_per_game = Column(Float, nullable=True)
    
    # Advanced analytics
    most_popular_locations = Column(Text, nullable=True)  # JSON array
    ai_difficulty_stats = Column(Text, nullable=True)  # JSON object
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<GameStatistics(human_wins={self.human_wins}, ai_wins={self.ai_wins})>"
    
    def update_stats(self):
        """Recalculate derived statistics."""
        if self.total_games > 0:
            self.human_win_rate = (self.human_wins / self.total_games) * 100
        self.last_updated = datetime.now(timezone.utc)

# Database initialization and helper functions

def init_database():
    """Initialize the database and create all tables."""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Create default statistics entry
        with get_db_session() as session:
            stats = session.query(GameStatistics).filter_by(lobby_code='main').first()
            if not stats:
                stats = GameStatistics(lobby_code='main')
                session.add(stats)
                logger.info("Created default game statistics")
                
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def create_lobby(session, code: str, name: str, max_players: int = 8) -> Lobby:
    """Create a new lobby."""
    lobby = Lobby(
        code=code,
        name=name,
        max_players=max_players
    )
    session.add(lobby)
    session.flush()  # Get the ID without committing
    logger.info(f"Created lobby: {code}")
    return lobby

def get_lobby_by_code(session, code: str) -> Optional[Lobby]:
    """Get a lobby by its code."""
    return session.query(Lobby).filter_by(code=code).first()

def add_player_to_lobby(session, lobby: Lobby, session_id: str, username: str, 
                       is_ai: bool = False, is_spectator: bool = False) -> Player:
    """Add a player to a lobby."""
    # Check if player already exists (reconnection)
    existing_player = session.query(Player).filter_by(
        lobby_id=lobby.id, 
        session_id=session_id
    ).first()
    
    if existing_player:
        existing_player.username = username
        existing_player.is_connected = True
        existing_player.update_last_seen()
        logger.info(f"Reconnected player: {username}")
        return existing_player
    
    # Check username uniqueness in active players
    username_taken = session.query(Player).filter_by(
        lobby_id=lobby.id,
        username=username,
        is_connected=True
    ).first()
    
    if username_taken:
        raise ValueError(f"Username '{username}' is already taken")
    
    # Check lobby capacity
    active_count = len(lobby.active_players)
    if active_count >= lobby.max_players:
        raise ValueError(f"Lobby is full ({lobby.max_players} players max)")
    
    player = Player(
        lobby_id=lobby.id,
        session_id=session_id,
        username=username,
        is_ai=is_ai,
        is_spectator=is_spectator
    )
    session.add(player)
    session.flush()
    
    lobby.update_activity()
    logger.info(f"Added player '{username}' to lobby '{lobby.code}'")
    return player

def remove_player_from_lobby(session, player: Player):
    """Remove a player from their lobby."""
    lobby = player.lobby
    logger.info(f"Removing player '{player.username}' from lobby '{lobby.code}'")
    session.delete(player)
    lobby.update_activity()

def disconnect_player(session, player: Player):
    """Mark a player as disconnected."""
    player.is_connected = False
    player.lobby.update_activity()
    logger.info(f"Disconnected player: {player.username}")

def start_game_session(session, lobby: Lobby, location: str) -> GameSession:
    """Start a new game session."""
    human_count = len(lobby.human_players)
    ai_count = len(lobby.ai_players)
    
    # Get next session number
    last_session = session.query(GameSession).filter_by(lobby_id=lobby.id)\
        .order_by(GameSession.session_number.desc()).first()
    session_number = (last_session.session_number + 1) if last_session else 1
    
    game_session = GameSession(
        lobby_id=lobby.id,
        session_number=session_number,
        location=location,
        total_players=human_count + ai_count,
        human_players=human_count,
        ai_players=ai_count,
        started_at=datetime.now(timezone.utc)
    )
    session.add(game_session)
    session.flush()
    
    # Update lobby state
    lobby.state = 'playing'
    lobby.location = location
    lobby.started_at = datetime.now(timezone.utc)
    lobby.current_turn = 0
    lobby.question_count = 0
    lobby.update_activity()
    
    logger.info(f"Started game session {session_number} in lobby '{lobby.code}' with location '{location}'")
    return game_session

def end_game_session(session, lobby: Lobby, winner: str, reason: str, 
                    eliminated_player: Optional[Player] = None,
                    ai_guess: Optional[str] = None, ai_correct: bool = False):
    """End the current game session."""
    current_session = session.query(GameSession).filter_by(lobby_id=lobby.id)\
        .order_by(GameSession.session_number.desc()).first()
    
    if current_session and not current_session.ended_at:
        current_session.ended_at = datetime.now(timezone.utc)
        current_session.winner = winner
        current_session.winner_reason = reason
        current_session.total_questions = lobby.question_count
        current_session.ai_final_guess = ai_guess
        current_session.ai_guessed_correctly = ai_correct
        
        if eliminated_player:
            current_session.eliminated_player_id = eliminated_player.id
            current_session.outsider_eliminated = eliminated_player.is_outsider
        
        # Calculate duration
        if current_session.started_at:
            duration = current_session.ended_at - current_session.started_at
            current_session.duration_seconds = int(duration.total_seconds())
        
        # Update lobby state
        lobby.state = 'finished'
        lobby.ended_at = current_session.ended_at
        lobby.update_activity()
        
        # Update global statistics
        update_game_statistics(session, lobby.code, winner, current_session.duration_seconds)
        
        logger.info(f"Ended game session in lobby '{lobby.code}': {winner} won ({reason})")

def update_game_statistics(session, lobby_code: str, winner: str, duration_seconds: int):
    """Update global game statistics."""
    stats = session.query(GameStatistics).filter_by(lobby_code=lobby_code).first()
    if not stats:
        stats = GameStatistics(lobby_code=lobby_code)
        session.add(stats)
    
    stats.total_games += 1
    if winner == 'humans':
        stats.human_wins += 1
    elif winner == 'ai':
        stats.ai_wins += 1
    
    # Update averages
    if duration_seconds:
        if stats.avg_game_duration:
            stats.avg_game_duration = (stats.avg_game_duration + duration_seconds) / 2
        else:
            stats.avg_game_duration = duration_seconds
    
    stats.update_stats()

def reset_lobby(session, lobby: Lobby):
    """Reset a lobby to waiting state."""
    lobby.state = 'waiting'
    lobby.location = None
    lobby.current_turn = 0
    lobby.question_count = 0
    lobby.outsider_player_id = None
    lobby.started_at = None
    lobby.ended_at = None
    lobby.update_activity()
    
    # Reset player states
    for player in lobby.players:
        if player.is_connected:
            player.is_outsider = False
            player.questions_asked = 0
            player.questions_answered = 0
            player.votes_received = 0
    
    # Clear votes
    session.query(Vote).filter_by(lobby_id=lobby.id).delete()
    
    logger.info(f"Reset lobby '{lobby.code}' to waiting state")

def get_game_statistics(session, lobby_code: str = 'main') -> Optional[GameStatistics]:
    """Get game statistics for a lobby."""
    return session.query(GameStatistics).filter_by(lobby_code=lobby_code).first()

def cleanup_inactive_lobbies(session, hours_inactive: int = 24):
    """Clean up lobbies that have been inactive for too long."""
    from datetime import timedelta
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_inactive)
    
    inactive_lobbies = session.query(Lobby).filter(
        Lobby.last_activity < cutoff_time,
        Lobby.state.in_(['finished', 'waiting'])
    ).all()
    
    for lobby in inactive_lobbies:
        logger.info(f"Cleaning up inactive lobby: {lobby.code}")
        session.delete(lobby)
    
    return len(inactive_lobbies)

if __name__ == "__main__":
    # Initialize database when run directly
    init_database()
    print("Database initialized successfully!")