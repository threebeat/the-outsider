import os
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Float, UniqueConstraint, Index
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.pool import NullPool
from config.settings import DATABASE_URL

logger = logging.getLogger(__name__)

# Database Setup
Base = declarative_base()

# Create engine with NullPool to avoid concurrency conflicts with eventlet
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}, 
        poolclass=NullPool,
        echo=False  # Set to True for SQL debugging
    )
else:
    # For PostgreSQL, use NullPool to avoid eventlet concurrency issues
    engine = create_engine(DATABASE_URL, poolclass=NullPool, echo=False)

# Create session factory
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
    """Context manager for database sessions with automatic commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        raise e
    finally:
        session.close()

# Core Database Models

class Lobby(Base):
    """
    Enhanced lobby model with comprehensive game state tracking.
    Supports multiple concurrent lobbies and detailed game metadata.
    """
    __tablename__ = 'lobbies'
    
    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    room = Column(String(50), unique=True, index=True, nullable=False)  # Keeping 'room' for backwards compatibility
    
    # Game state management
    state = Column(String(20), default='waiting', nullable=False)  # waiting, playing, voting, finished
    location = Column(String(100), nullable=True)  # Current game location
    outsider_sid = Column(String(100), nullable=True, index=True)  # AI player session ID
    
    # Turn and progression tracking
    turn = Column(Integer, default=0)  # Keep for backwards compatibility
    total_turns = Column(Integer, default=0)
    question_count = Column(Integer, default=0)
    max_questions = Column(Integer, default=5)  # Configurable question limit
    
    # Current question state
    current_question_asker = Column(String(100), nullable=True, index=True)  # Keep original name
    current_target = Column(String(100), nullable=True, index=True)  # Keep original name
    player_order = Column(Text, default='')  # Keep original name - Comma-separated SIDs
    
    # Game timing and metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Game configuration
    min_players = Column(Integer, default=2)
    max_players = Column(Integer, default=8)
    allow_spectators = Column(Boolean, default=True)
    auto_start = Column(Boolean, default=True)
    
    # Relationships
    players = relationship('Player', back_populates='lobby', cascade="all, delete-orphan")
    messages = relationship('Message', back_populates='lobby', cascade="all, delete-orphan")
    votes = relationship('Vote', back_populates='lobby', cascade="all, delete-orphan")
    game_sessions = relationship('GameSession', back_populates='lobby', cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_lobby_state_activity', 'state', 'last_activity'),
        Index('idx_lobby_room_state', 'room', 'state'),
    )
    
    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def get_active_players(self):
        """Get all non-spectator players."""
        return [p for p in self.players if not p.is_spectator and p.is_connected]
    
    def get_human_players(self):
        """Get all human (non-AI) players."""
        return [p for p in self.players if not p.is_ai and not p.is_spectator]

class Player(Base):
    """
    Enhanced player model with detailed tracking and statistics.
    """
    __tablename__ = 'players'
    
    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    sid = Column(String(100), nullable=False, index=True)  # Session ID
    username = Column(String(50), nullable=False)
    
    # Player type and state
    is_ai = Column(Boolean, default=False, nullable=False)
    is_spectator = Column(Boolean, default=False, nullable=False)
    is_connected = Column(Boolean, default=True, nullable=False)
    
    # Game state
    knows_location = Column(Boolean, default=True, nullable=False)  # False for outsider
    is_eliminated = Column(Boolean, default=False, nullable=False)
    
    # Timing information
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    disconnected_at = Column(DateTime(timezone=True), nullable=True)
    
    # Player statistics (for current game)
    questions_asked = Column(Integer, default=0)
    questions_answered = Column(Integer, default=0)
    votes_cast = Column(Integer, default=0)
    
    # Foreign key and relationship
    lobby_id = Column(Integer, ForeignKey('lobbies.id', ondelete='CASCADE'), nullable=False)
    lobby = relationship('Lobby', back_populates='players')
    
    # Relationships
    sent_messages = relationship('Message', foreign_keys='Message.sender_player_id', back_populates='sender')
    received_messages = relationship('Message', foreign_keys='Message.target_player_id', back_populates='target')
    cast_votes = relationship('Vote', foreign_keys='Vote.voter_player_id', back_populates='voter')
    received_votes = relationship('Vote', foreign_keys='Vote.target_player_id', back_populates='target')
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('lobby_id', 'sid', name='uq_player_lobby_sid'),
        UniqueConstraint('lobby_id', 'username', name='uq_player_lobby_username'),
        Index('idx_player_lobby_connected', 'lobby_id', 'is_connected'),
        Index('idx_player_sid_connected', 'sid', 'is_connected'),
    )
    
    def update_last_seen(self):
        """Update the last seen timestamp."""
        self.last_seen = datetime.now(timezone.utc)

class Message(Base):
    """
    Enhanced message model for tracking all game communications.
    """
    __tablename__ = 'messages'
    
    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Message content and metadata
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default='chat', nullable=False)  # chat, question, answer, system, vote
    
    # Relationships and context
    lobby_id = Column(Integer, ForeignKey('lobbies.id', ondelete='CASCADE'), nullable=False)
    sender_player_id = Column(Integer, ForeignKey('players.id', ondelete='SET NULL'), nullable=True)
    target_player_id = Column(Integer, ForeignKey('players.id', ondelete='SET NULL'), nullable=True)
    
    # Timing
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Question/Answer specific fields
    is_question = Column(Boolean, default=False)
    question_number = Column(Integer, nullable=True)  # Which question in the game sequence
    
    # Relationships
    lobby = relationship('Lobby', back_populates='messages')
    sender = relationship('Player', foreign_keys=[sender_player_id], back_populates='sent_messages')
    target = relationship('Player', foreign_keys=[target_player_id], back_populates='received_messages')
    
    # Indexes
    __table_args__ = (
        Index('idx_message_lobby_created', 'lobby_id', 'created_at'),
        Index('idx_message_type_lobby', 'message_type', 'lobby_id'),
    )

class Vote(Base):
    """
    Enhanced voting model with detailed tracking.
    """
    __tablename__ = 'votes'
    
    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Voting relationships (keeping original column names for compatibility)
    lobby_id = Column(Integer, ForeignKey('lobbies.id', ondelete='CASCADE'), nullable=False)
    voter_sid = Column(String(100), nullable=False)  # Keep original format for compatibility
    voted_for_sid = Column(String(100), nullable=False)  # Keep original format for compatibility
    voter_player_id = Column(Integer, ForeignKey('players.id', ondelete='CASCADE'), nullable=True)
    target_player_id = Column(Integer, ForeignKey('players.id', ondelete='CASCADE'), nullable=True)
    
    # Vote metadata
    vote_round = Column(Integer, default=1)  # Support for multiple voting rounds
    confidence = Column(Float, nullable=True)  # Optional confidence rating
    reasoning = Column(Text, nullable=True)  # Optional vote reasoning
    
    # Timing
    cast_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    lobby = relationship('Lobby', back_populates='votes')
    voter = relationship('Player', foreign_keys=[voter_player_id], back_populates='cast_votes')
    target = relationship('Player', foreign_keys=[target_player_id], back_populates='received_votes')
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('lobby_id', 'voter_sid', 'vote_round', name='uq_vote_per_round'),
        Index('idx_vote_lobby_round', 'lobby_id', 'vote_round'),
    )

class GameSession(Base):
    """
    Complete game session tracking for analytics and history.
    """
    __tablename__ = 'game_sessions'
    
    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Session metadata
    lobby_id = Column(Integer, ForeignKey('lobbies.id', ondelete='CASCADE'), nullable=False)
    session_number = Column(Integer, nullable=False)  # Sequential session number for the lobby
    
    # Game details
    location = Column(String(100), nullable=False)
    total_players = Column(Integer, nullable=False)
    human_players = Column(Integer, nullable=False)
    ai_players = Column(Integer, nullable=False)
    
    # Game progression
    total_questions = Column(Integer, default=0)
    total_votes = Column(Integer, default=0)
    winner = Column(String(20), nullable=True)  # 'humans', 'ai', or 'draw'
    winning_reason = Column(String(100), nullable=True)  # 'voted_out_ai', 'ai_guessed_location', etc.
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Game outcome details
    eliminated_player_id = Column(Integer, ForeignKey('players.id', ondelete='SET NULL'), nullable=True)
    ai_final_guess = Column(String(100), nullable=True)
    ai_guess_correct = Column(Boolean, nullable=True)
    
    # Relationships
    lobby = relationship('Lobby', back_populates='game_sessions')
    eliminated_player = relationship('Player', foreign_keys=[eliminated_player_id])
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('lobby_id', 'session_number', name='uq_session_per_lobby'),
        Index('idx_session_lobby_started', 'lobby_id', 'started_at'),
        Index('idx_session_winner_ended', 'winner', 'ended_at'),
    )

class WinCounter(Base):
    """
    Enhanced win tracking with detailed statistics.
    """
    __tablename__ = 'win_counters'
    
    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    room = Column(String(50), default='main', nullable=False, index=True)  # Keep original name
    
    # Win counts
    human_wins = Column(Integer, default=0, nullable=False)
    ai_wins = Column(Integer, default=0, nullable=False)
    draws = Column(Integer, default=0, nullable=False)
    
    # Detailed statistics
    total_games = Column(Integer, default=0, nullable=False)
    total_players_served = Column(Integer, default=0, nullable=False)
    avg_game_duration = Column(Float, nullable=True)  # Average in seconds
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_reset = Column(DateTime(timezone=True), nullable=True)
    
    def update_stats(self):
        """Update the last updated timestamp."""
        self.last_updated = datetime.now(timezone.utc)
    
    def get_win_rate(self, player_type='human'):
        """Calculate win rate for humans or AI."""
        if self.total_games == 0:
            return 0.0
        if player_type == 'human':
            return (self.human_wins / self.total_games) * 100
        elif player_type == 'ai':
            return (self.ai_wins / self.total_games) * 100
        return 0.0

class PlayerStatistics(Base):
    """
    Long-term player statistics across all games.
    """
    __tablename__ = 'player_statistics'
    
    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, index=True)
    
    # Game participation
    total_games = Column(Integer, default=0, nullable=False)
    games_as_human = Column(Integer, default=0, nullable=False)
    games_as_spectator = Column(Integer, default=0, nullable=False)
    
    # Performance metrics
    games_won = Column(Integer, default=0, nullable=False)
    games_lost = Column(Integer, default=0, nullable=False)
    times_voted_out = Column(Integer, default=0, nullable=False)
    correct_outsider_votes = Column(Integer, default=0, nullable=False)
    
    # Activity metrics
    total_questions_asked = Column(Integer, default=0, nullable=False)
    total_questions_answered = Column(Integer, default=0, nullable=False)
    total_votes_cast = Column(Integer, default=0, nullable=False)
    avg_game_duration = Column(Float, nullable=True)
    
    # Timestamps
    first_played = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_played = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    def get_win_rate(self):
        """Calculate overall win rate."""
        if self.total_games == 0:
            return 0.0
        return (self.games_won / self.total_games) * 100
    
    def get_accuracy_rate(self):
        """Calculate outsider identification accuracy."""
        if self.total_votes_cast == 0:
            return 0.0
        return (self.correct_outsider_votes / self.total_votes_cast) * 100

# Initialize database
def init_database():
    """Initialize the database with all tables."""
    try:
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

# Database helper functions (backwards compatibility + new features)

def get_lobby(session, room="main"):
    """Get or create a lobby for the given room."""
    try:
        lobby = session.query(Lobby).filter_by(room=room).first()
        if not lobby:
            lobby = Lobby(room=room)
            session.add(lobby)
            session.commit()
            logger.info(f"Created new lobby: {room}")
        return lobby
    except Exception as e:
        logger.error(f"Error getting/creating lobby {room}: {e}")
        session.rollback()
        raise

def get_players(session, lobby):
    """Get all players in a lobby."""
    try:
        return session.query(Player).filter_by(lobby_id=lobby.id).all()
    except Exception as e:
        logger.error(f"Error getting players for lobby {lobby.id}: {e}")
        return []

def get_active_players(session, lobby):
    """Get all connected, non-spectator players in a lobby."""
    try:
        return session.query(Player).filter_by(
            lobby_id=lobby.id, 
            is_connected=True, 
            is_spectator=False,
            is_eliminated=False
        ).all()
    except Exception as e:
        logger.error(f"Error getting active players for lobby {lobby.id}: {e}")
        return []

def get_player_by_sid(session, lobby, sid):
    """Get a player by session ID in a specific lobby."""
    try:
        return session.query(Player).filter_by(lobby_id=lobby.id, sid=sid).first()
    except Exception as e:
        logger.error(f"Error getting player with SID {sid} in lobby {lobby.id}: {e}")
        return None

def get_player_by_username(session, lobby, username):
    """Get a player by username in a specific lobby."""
    try:
        return session.query(Player).filter_by(lobby_id=lobby.id, username=username).first()
    except Exception as e:
        logger.error(f"Error getting player {username} in lobby {lobby.id}: {e}")
        return None

def add_player(session, lobby, sid, username, is_ai=False, is_spectator=False):
    """Add a new player to a lobby."""
    try:
        # Check if player already exists
        existing_player = get_player_by_sid(session, lobby, sid)
        if existing_player:
            existing_player.username = username
            existing_player.is_connected = True
            existing_player.disconnected_at = None
            existing_player.update_last_seen()
            session.commit()
            return existing_player
        
        # Check username uniqueness
        if get_player_by_username(session, lobby, username):
            raise ValueError(f"Username '{username}' already taken in lobby {lobby.room}")
        
        # Create new player
        player = Player(
            lobby_id=lobby.id,
            sid=sid,
            username=username,
            is_ai=is_ai,
            is_spectator=is_spectator,
            knows_location=True  # Will be set to False for outsider later
        )
        session.add(player)
        session.commit()
        
        lobby.update_activity()
        session.commit()
        
        logger.info(f"Added player {username} (SID: {sid}) to lobby {lobby.room}")
        return player
        
    except Exception as e:
        logger.error(f"Error adding player {username} to lobby {lobby.id}: {e}")
        session.rollback()
        raise

def remove_player(session, player):
    """Remove a player from the database."""
    try:
        lobby = player.lobby
        logger.info(f"Removing player {player.username} from lobby {lobby.room}")
        session.delete(player)
        lobby.update_activity()
        session.commit()
    except Exception as e:
        logger.error(f"Error removing player {player.id}: {e}")
        session.rollback()
        raise

def add_message(session, lobby, content, sender_player=None, target_player=None, 
                message_type='chat', is_question=False, question_number=None):
    """Add a message to the lobby with enhanced metadata."""
    try:
        message = Message(
            lobby_id=lobby.id,
            content=content,
            message_type=message_type,
            sender_player_id=sender_player.id if sender_player else None,
            target_player_id=target_player.id if target_player else None,
            is_question=is_question,
            question_number=question_number
        )
        session.add(message)
        lobby.update_activity()
        session.commit()
        return message
    except Exception as e:
        logger.error(f"Error adding message to lobby {lobby.id}: {e}")
        session.rollback()
        raise

def get_messages(session, lobby):
    """Get recent messages from a lobby."""
    try:
        return session.query(Message).filter_by(lobby_id=lobby.id)\
            .order_by(Message.created_at.desc()).limit(50).all()
    except Exception as e:
        logger.error(f"Error getting messages for lobby {lobby.id}: {e}")
        return []

def clear_votes(session, lobby):
    """Clear all votes for a lobby."""
    try:
        session.query(Vote).filter_by(lobby_id=lobby.id).delete()
        session.commit()
        logger.info(f"Cleared votes for lobby {lobby.room}")
    except Exception as e:
        logger.error(f"Error clearing votes for lobby {lobby.id}: {e}")
        session.rollback()
        raise

def get_vote_count(session, lobby, target_sid):
    """Get the number of votes for a specific player (backwards compatibility)."""
    try:
        return session.query(Vote).filter_by(lobby_id=lobby.id, voted_for_sid=target_sid).count()
    except Exception as e:
        logger.error(f"Error getting vote count for {target_sid}: {e}")
        return 0

def get_win_counter(session, room="main"):
    """Get or create win counter for a room."""
    try:
        counter = session.query(WinCounter).filter_by(room=room).first()
        if not counter:
            counter = WinCounter(room=room)
            session.add(counter)
            session.commit()
        return counter
    except Exception as e:
        logger.error(f"Error getting win counter for {room}: {e}")
        session.rollback()
        raise

def increment_human_wins(session, room="main"):
    """Increment human wins and update statistics."""
    try:
        counter = get_win_counter(session, room)
        counter.human_wins += 1
        counter.total_games += 1
        counter.update_stats()
        session.commit()
        logger.info(f"Incremented human wins for {room}: {counter.human_wins}")
        return counter
    except Exception as e:
        logger.error(f"Error incrementing human wins: {e}")
        session.rollback()
        raise

def increment_ai_wins(session, room="main"):
    """Increment AI wins and update statistics."""
    try:
        counter = get_win_counter(session, room)
        counter.ai_wins += 1
        counter.total_games += 1
        counter.update_stats()
        session.commit()
        logger.info(f"Incremented AI wins for {room}: {counter.ai_wins}")
        return counter
    except Exception as e:
        logger.error(f"Error incrementing AI wins: {e}")
        session.rollback()
        raise

def reset_win_counter(session, room="main"):
    """Reset the win counter for a room."""
    try:
        counter = get_win_counter(session, room)
        counter.human_wins = 0
        counter.ai_wins = 0
        counter.total_games = 0
        counter.last_reset = datetime.now(timezone.utc)
        counter.update_stats()
        session.commit()
        logger.info(f"Reset win counter for {room}")
        return counter
    except Exception as e:
        logger.error(f"Error resetting win counter: {e}")
        session.rollback()
        raise

def start_game_session(session, lobby, location, human_count, ai_count):
    """Start a new game session with tracking."""
    try:
        # Get the next session number
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
        
        # Update lobby state
        lobby.state = 'playing'
        lobby.location = location
        lobby.started_at = datetime.now(timezone.utc)
        lobby.question_count = 0
        lobby.update_activity()
        
        session.commit()
        logger.info(f"Started game session {session_number} in lobby {lobby.room}")
        return game_session
        
    except Exception as e:
        logger.error(f"Error starting game session: {e}")
        session.rollback()
        raise

def reset_lobby(session, lobby, preserve_win_counter=False):
    """Reset lobby to initial state for a new game."""
    try:
        # Clear game-specific data
        lobby.state = 'waiting'
        lobby.location = None
        lobby.outsider_sid = None
        lobby.turn = 0
        lobby.question_count = 0
        lobby.current_question_asker = None
        lobby.current_target = None
        lobby.player_order = ''
        lobby.started_at = None
        lobby.ended_at = None
        lobby.update_activity()
        
        # Reset player states but keep players connected
        for player in lobby.players:
            if player.is_connected:
                player.is_eliminated = False
                player.knows_location = True
                player.questions_asked = 0
                player.questions_answered = 0
                player.votes_cast = 0
        
        # Clear votes
        clear_votes(session, lobby)
        
        session.commit()
        logger.info(f"Reset lobby {lobby.room}")
        
    except Exception as e:
        logger.error(f"Error resetting lobby {lobby.id}: {e}")
        session.rollback()
        raise

# Initialize database on import
init_database()