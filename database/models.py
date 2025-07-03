"""
Database Models for The Outsider.

Contains all SQLAlchemy model definitions for the game.
Pure data models with no business logic.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Float, Index
from sqlalchemy.orm import relationship, declarative_base

# Create the base class for models
Base = declarative_base()

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
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    players = relationship('Player', back_populates='lobby', cascade='all, delete-orphan')
    messages = relationship('GameMessage', back_populates='lobby', cascade='all, delete-orphan')
    votes = relationship('Vote', back_populates='lobby', cascade='all, delete-orphan')
    sessions = relationship('GameSession', back_populates='lobby', cascade='all, delete-orphan')
    
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

class Player(Base):
    """Represents a player in the game."""
    
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), nullable=False, index=True)  # Socket.IO session ID
    username = Column(String(50), nullable=False)
    
    # Player type and status
    is_ai = Column(Boolean, default=False, nullable=False)  # AI players are automatically outsiders
    is_spectator = Column(Boolean, default=False, nullable=False)
    is_connected = Column(Boolean, default=True, nullable=False)
    
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
    lobby = relationship('Lobby', back_populates='players')
    sent_messages = relationship('GameMessage', foreign_keys='GameMessage.sender_id', back_populates='sender')
    received_messages = relationship('GameMessage', foreign_keys='GameMessage.target_id', back_populates='target')
    votes_cast = relationship('Vote', foreign_keys='Vote.voter_id', back_populates='voter')
    votes_against = relationship('Vote', foreign_keys='Vote.target_id', back_populates='target')
    
    # Indexes
    __table_args__ = (
        Index('idx_player_lobby_session', 'lobby_id', 'session_id'),
        Index('idx_player_lobby_username', 'lobby_id', 'username'),
        Index('idx_player_connected', 'is_connected', 'last_seen'),
        Index('idx_player_ai', 'is_ai', 'lobby_id'),
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
    ai_eliminated = Column(Boolean, nullable=True)  # Was an AI player eliminated
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