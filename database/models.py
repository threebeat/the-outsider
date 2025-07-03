"""
Database Models for The Outsider.

Contains SQLAlchemy model definitions for persistent data only.
Lobbies and games are now handled by Redis cache.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Float, Index
from sqlalchemy.orm import relationship, declarative_base

# Create the base class for models
Base = declarative_base()

class Player(Base):
    """Represents a player in the game - persistent data only."""
    
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), nullable=False, index=True)  # Socket.IO session ID
    username = Column(String(50), nullable=False)
    
    # Player type and status
    is_ai = Column(Boolean, default=False, nullable=False)  # AI players are automatically outsiders
    is_spectator = Column(Boolean, default=False, nullable=False)
    
    # Persistent game statistics
    total_games_played = Column(Integer, default=0)
    total_games_won = Column(Integer, default=0)
    total_questions_asked = Column(Integer, default=0)
    total_questions_answered = Column(Integer, default=0)
    total_votes_received = Column(Integer, default=0)
    
    # AI-specific fields
    ai_personality = Column(String(50), nullable=True)  # aggressive, cautious, analytical, etc.
    ai_strategy = Column(Text, nullable=True)  # JSON string for AI strategy data
    
    # Indexes
    __table_args__ = (
        Index('idx_player_session_username', 'session_id', 'username'),
        Index('idx_player_ai', 'is_ai'),
    )
    
    def __repr__(self):
        return f"<Player(username='{self.username}', is_ai={self.is_ai})>"

class GameStatistics(Base):
    """Global game statistics and win counters."""
    
    __tablename__ = 'statistics'
    
    id = Column(Integer, primary_key=True)
    lobby_code = Column(String(50), default='main', index=True)
    
    # Win counters - simple tracking only
    human_wins = Column(Integer, default=0)
    ai_wins = Column(Integer, default=0)
    total_games = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<GameStatistics(human_wins={self.human_wins}, ai_wins={self.ai_wins})>"