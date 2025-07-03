"""
Database module for The Outsider game.

Organized into three sections:
1. Initialization - Sets up database and creates default lobby
2. Universal Getters - Read operations from database
3. Universal Setters - Write operations to database
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
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

# ==============================================================================
# DATABASE MODELS
# ==============================================================================

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

# ==============================================================================
# SECTION 1: INITIALIZATION
# ==============================================================================

def init_database():
    """Initialize the database, create tables, and create default lobby."""
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
        
        # Clean the database but preserve statistics
        clean_database()
        
        # Create default lobby using lobby_creator
        from lobby.lobby_creator import LobbyCreator
        lobby_creator = LobbyCreator()
        success, message, lobby_config = lobby_creator.create_default_lobby()
        
        if success:
            logger.info(f"Created default lobby: {message}")
        else:
            logger.warning(f"Failed to create default lobby: {message}")
                
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def clean_database():
    """
    Clean all transient game data while preserving statistics.
    
    Removes:
    - All lobbies and their cascading data (players, votes, messages, sessions)
    - Does NOT remove GameStatistics (preserves human vs AI score)
    """
    try:
        with get_db_session() as session:
            # Count items before cleanup for logging
            lobby_count = session.query(Lobby).count()
            player_count = session.query(Player).count()
            message_count = session.query(GameMessage).count()
            vote_count = session.query(Vote).count()
            session_count = session.query(GameSession).count()
            
            # Delete all lobbies (cascades to players, messages, votes, sessions)
            session.query(Lobby).delete()
            
            # Log what was cleaned
            logger.info(f"Database cleanup complete:")
            logger.info(f"  - Removed {lobby_count} lobbies")
            logger.info(f"  - Removed {player_count} players")
            logger.info(f"  - Removed {message_count} messages")
            logger.info(f"  - Removed {vote_count} votes")
            logger.info(f"  - Removed {session_count} game sessions")
            
            # Verify statistics are preserved
            stats = session.query(GameStatistics).filter_by(lobby_code='main').first()
            if stats:
                logger.info(f"Preserved game statistics: Humans {stats.human_wins} - {stats.ai_wins} AI")
            
            return {
                'lobbies_removed': lobby_count,
                'players_removed': player_count,
                'messages_removed': message_count,
                'votes_removed': vote_count,
                'sessions_removed': session_count
            }
            
    except Exception as e:
        logger.error(f"Failed to clean database: {e}")
        raise

# ==============================================================================
# SECTION 2: UNIVERSAL GETTERS
# ==============================================================================

def get_lobby_by_code(session, code: str) -> Optional[Lobby]:
    """Get a lobby by its code."""
    return session.query(Lobby).filter_by(code=code).first()

def get_lobby_by_id(session, lobby_id: int) -> Optional[Lobby]:
    """Get a lobby by its ID."""
    return session.query(Lobby).filter_by(id=lobby_id).first()

def get_player_by_session_id(session, session_id: str) -> Optional[Player]:
    """Get a player by their session ID."""
    return session.query(Player).filter_by(session_id=session_id, is_connected=True).first()

def get_player_by_username(session, lobby_id: int, username: str) -> Optional[Player]:
    """Get a player by username in a specific lobby."""
    return session.query(Player).filter_by(
        lobby_id=lobby_id,
        username=username,
        is_connected=True
    ).first()

def get_active_lobbies(session) -> List[Lobby]:
    """Get all active lobbies."""
    return session.query(Lobby).filter(
        Lobby.state.in_(['waiting', 'playing'])
    ).all()

def get_game_statistics(session, lobby_code: str = 'main') -> Optional[GameStatistics]:
    """Get game statistics for a lobby."""
    return session.query(GameStatistics).filter_by(lobby_code=lobby_code).first()

def get_active_game_session(session, lobby_id: int) -> Optional[GameSession]:
    """Get the active game session for a lobby."""
    return session.query(GameSession).filter_by(
        lobby_id=lobby_id,
        ended_at=None
    ).first()

def get_player_count_in_lobby(session, lobby_id: int) -> int:
    """Get the number of active players in a lobby."""
    return session.query(Player).filter_by(
        lobby_id=lobby_id,
        is_connected=True,
        is_spectator=False
    ).count()

def get_ai_players_in_lobby(session, lobby_id: int) -> List[Player]:
    """Get all AI players in a lobby."""
    return session.query(Player).filter_by(
        lobby_id=lobby_id,
        is_ai=True,
        is_connected=True
    ).all()

def get_human_players_in_lobby(session, lobby_id: int) -> List[Player]:
    """Get all human players in a lobby."""
    return session.query(Player).filter_by(
        lobby_id=lobby_id,
        is_ai=False,
        is_connected=True,
        is_spectator=False
    ).all()

# ==============================================================================
# SECTION 3: UNIVERSAL SETTERS
# ==============================================================================

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

def create_player(session, lobby_id: int, session_id: str, username: str, 
                 is_ai: bool = False, is_spectator: bool = False,
                 ai_personality: Optional[str] = None) -> Player:
    """Create a new player."""
    player = Player(
        lobby_id=lobby_id,
        session_id=session_id,
        username=username,
        is_ai=is_ai,
        is_spectator=is_spectator,
        ai_personality=ai_personality
    )
    session.add(player)
    session.flush()
    logger.info(f"Created player '{username}' in lobby {lobby_id} (AI: {is_ai})")
    return player

def update_lobby_state(session, lobby: Lobby, new_state: str):
    """Update lobby state."""
    lobby.state = new_state
    lobby.update_activity()
    logger.info(f"Updated lobby {lobby.code} state to: {new_state}")

def update_player_connection(session, player: Player, connected: bool):
    """Update player connection status."""
    player.is_connected = connected
    player.update_last_seen()
    logger.info(f"Updated player {player.username} connection: {connected}")

def set_player_as_outsider(session, player: Player):
    """Mark a player as the outsider."""
    player.is_outsider = True
    if player.lobby:
        player.lobby.outsider_player_id = player.id
    logger.info(f"Set player {player.username} as outsider")

def create_game_session(session, lobby: Lobby, location: str) -> GameSession:
    """Create a new game session."""
    # Get next session number
    last_session = session.query(GameSession).filter_by(lobby_id=lobby.id)\
        .order_by(GameSession.session_number.desc()).first()
    session_number = (last_session.session_number + 1) if last_session else 1
    
    # Count players
    human_count = len(lobby.human_players)
    ai_count = len(lobby.ai_players)
    
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
    
    # Update lobby
    lobby.state = 'playing'
    lobby.location = location
    lobby.started_at = datetime.now(timezone.utc)
    lobby.current_turn = 0
    lobby.question_count = 0
    lobby.update_activity()
    
    logger.info(f"Created game session {session_number} in lobby '{lobby.code}' with location '{location}'")
    return game_session

def create_game_message(session, lobby_id: int, content: str, message_type: str = 'chat',
                       sender_id: Optional[int] = None, target_id: Optional[int] = None,
                       is_question: bool = False) -> GameMessage:
    """Create a new game message."""
    message = GameMessage(
        lobby_id=lobby_id,
        content=content,
        message_type=message_type,
        sender_id=sender_id,
        target_id=target_id,
        is_question=is_question
    )
    session.add(message)
    session.flush()
    return message

def create_vote(session, lobby_id: int, voter_id: int, target_id: int,
               vote_round: int = 1, confidence: Optional[float] = None,
               reasoning: Optional[str] = None) -> Vote:
    """Create a new vote."""
    vote = Vote(
        lobby_id=lobby_id,
        voter_id=voter_id,
        target_id=target_id,
        vote_round=vote_round,
        confidence=confidence,
        reasoning=reasoning
    )
    session.add(vote)
    session.flush()
    logger.info(f"Created vote in lobby {lobby_id}")
    return vote

def update_game_statistics(session, winner: str):
    """Update global game statistics."""
    stats = get_game_statistics(session)
    if not stats:
        stats = GameStatistics(lobby_code='main')
        session.add(stats)
    
    stats.total_games += 1
    if winner == 'humans':
        stats.human_wins += 1
    elif winner == 'ai':
        stats.ai_wins += 1
    
    stats.update_stats()
    logger.info(f"Updated statistics: {winner} won (Total: {stats.total_games})")

def delete_player(session, player: Player):
    """Delete a player from the database."""
    username = player.username
    lobby_code = player.lobby.code if player.lobby else "unknown"
    session.delete(player)
    logger.info(f"Deleted player '{username}' from lobby '{lobby_code}'")