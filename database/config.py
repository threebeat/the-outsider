"""
Database Configuration for The Outsider.

Contains database engine setup, session management, and initialization functions.
"""

import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

from .models import Base, GameStatistics

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
        from .models import Lobby, Player, GameMessage, Vote, GameSession
        
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