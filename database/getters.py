"""
Universal Database Getters for The Outsider.

Contains all read operations from the database for persistent data only.
Lobbies and games are now handled by Redis cache.
All session management is contained within this module.
"""

import logging
from typing import List, Optional, Dict, Any

from .config import get_db_session
from .models import Player, GameStatistics

logger = logging.getLogger(__name__)

# ==============================================================================
# PLAYER GETTERS - PERSISTENT DATA ONLY
# ==============================================================================

def get_player_by_session_id(session_id: str) -> Optional[Player]:
    """Get a player by their session ID."""
    with get_db_session() as session:
        return session.query(Player).filter_by(session_id=session_id).first()

def get_player_by_id(player_id: int) -> Optional[Player]:
    """Get a player by their ID."""
    with get_db_session() as session:
        return session.query(Player).filter_by(id=player_id).first()

def get_player_by_username(username: str) -> Optional[Player]:
    """Get a player by username (most recent record)."""
    with get_db_session() as session:
        return session.query(Player).filter_by(username=username)\
            .order_by(Player.id.desc()).first()

def get_all_players() -> List[Player]:
    """Get all players."""
    with get_db_session() as session:
        return session.query(Player).all()

def get_human_players() -> List[Player]:
    """Get all human players."""
    with get_db_session() as session:
        return session.query(Player).filter_by(is_ai=False).all()

def get_ai_players() -> List[Player]:
    """Get all AI players."""
    with get_db_session() as session:
        return session.query(Player).filter_by(is_ai=True).all()

def get_players_by_type(is_ai: bool) -> List[Player]:
    """Get players by type (human or AI)."""
    with get_db_session() as session:
        return session.query(Player).filter_by(is_ai=is_ai).all()

def get_player_statistics(username: str) -> Optional[Player]:
    """Get player statistics by username."""
    return get_player_by_username(username)

def get_top_players_by_games_won(limit: int = 10) -> List[Player]:
    """Get top players by total games won."""
    with get_db_session() as session:
        return session.query(Player).filter(Player.total_games_won > 0)\
            .order_by(Player.total_games_won.desc())\
            .limit(limit).all()

def get_top_players_by_win_rate(limit: int = 10, min_games: int = 5) -> List[Player]:
    """Get top players by win rate (minimum games required)."""
    with get_db_session() as session:
        return session.query(Player).filter(
            Player.total_games_played >= min_games,
            Player.total_games_played > 0
        ).order_by(
            (Player.total_games_won * 1.0 / Player.total_games_played).desc()
        ).limit(limit).all()

def get_most_active_players(limit: int = 10) -> List[Player]:
    """Get most active players by total games played."""
    with get_db_session() as session:
        return session.query(Player).filter(Player.total_games_played > 0)\
            .order_by(Player.total_games_played.desc())\
            .limit(limit).all()

def is_username_taken(username: str, exclude_player_id: Optional[int] = None) -> bool:
    """Check if a username is already taken."""
    with get_db_session() as session:
        query = session.query(Player).filter_by(username=username)
        
        if exclude_player_id:
            query = query.filter(Player.id != exclude_player_id)
            
        return query.first() is not None

def player_exists_by_session(session_id: str) -> bool:
    """Check if a player exists with given session ID."""
    return get_player_by_session_id(session_id) is not None

# ==============================================================================
# STATISTICS GETTERS
# ==============================================================================

def get_game_statistics(lobby_code: str = 'main') -> Optional[GameStatistics]:
    """Get game statistics for a lobby."""
    with get_db_session() as session:
        return session.query(GameStatistics).filter_by(lobby_code=lobby_code).first()

def get_all_game_statistics() -> List[GameStatistics]:
    """Get all game statistics."""
    with get_db_session() as session:
        return session.query(GameStatistics).all()

def get_global_statistics() -> Dict[str, Any]:
    """Get aggregated global statistics."""
    stats = get_game_statistics('main')
    if not stats:
        return {
            'total_games': 0,
            'human_wins': 0,
            'ai_wins': 0,
            'human_win_rate': 0.0,
            'ai_win_rate': 0.0
        }
    
    human_win_rate = (stats.human_wins / stats.total_games * 100) if stats.total_games > 0 else 0.0
    ai_win_rate = (stats.ai_wins / stats.total_games * 100) if stats.total_games > 0 else 0.0
    
    return {
        'total_games': stats.total_games,
        'human_wins': stats.human_wins,
        'ai_wins': stats.ai_wins,
        'human_win_rate': round(human_win_rate, 1),
        'ai_win_rate': round(ai_win_rate, 1)
    }

def statistics_exist(lobby_code: str = 'main') -> bool:
    """Check if statistics exist for a lobby."""
    return get_game_statistics(lobby_code) is not None

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def get_database_health() -> Dict[str, Any]:
    """Get database health information."""
    try:
        with get_db_session() as session:
            # Test basic connectivity
            player_count = session.query(Player).count()
            stats_count = session.query(GameStatistics).count()
            
            return {
                'connected': True,
                'player_count': player_count,
                'statistics_count': stats_count,
                'status': 'healthy'
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'connected': False,
            'error': str(e),
            'status': 'unhealthy'
        }