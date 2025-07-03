"""
Universal Database Setters for The Outsider.

Contains all write operations to the database for persistent data only.
Lobbies and games are now handled by Redis cache.
All session management is contained within this module.
"""

import logging
from typing import Optional

from .config import get_db_session
from .models import Player, GameStatistics

logger = logging.getLogger(__name__)

# ==============================================================================
# PLAYER SETTERS - PERSISTENT DATA ONLY
# ==============================================================================

def create_player(session_id: str, username: str, 
                 is_ai: bool = False, is_spectator: bool = False,
                 ai_personality: Optional[str] = None) -> Player:
    """Create a new player record."""
    with get_db_session() as session:
        player = Player(
            session_id=session_id,
            username=username,
            is_ai=is_ai,
            is_spectator=is_spectator,
            ai_personality=ai_personality
        )
        session.add(player)
        session.flush()
        logger.info(f"Created player '{username}' (AI: {is_ai})")
        return player

def update_player(player_id: int, 
                 username: Optional[str] = None,
                 ai_personality: Optional[str] = None,
                 ai_strategy: Optional[str] = None) -> bool:
    """Update player information."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if not player:
            return False
            
        if username is not None:
            player.username = username
        if ai_personality is not None:
            player.ai_personality = ai_personality
        if ai_strategy is not None:
            player.ai_strategy = ai_strategy
            
        logger.info(f"Updated player {player_id}")
        return True

def update_player_by_session(session_id: str,
                           username: Optional[str] = None,
                           ai_personality: Optional[str] = None,
                           ai_strategy: Optional[str] = None) -> bool:
    """Update player information by session ID."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(session_id=session_id).first()
        if not player:
            return False
            
        if username is not None:
            player.username = username
        if ai_personality is not None:
            player.ai_personality = ai_personality
        if ai_strategy is not None:
            player.ai_strategy = ai_strategy
            
        logger.info(f"Updated player by session {session_id}")
        return True

def delete_player(player_id: int) -> bool:
    """Delete a player from the database."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            username = player.username
            session.delete(player)
            logger.info(f"Deleted player '{username}'")
            return True
        return False

def delete_player_by_session(session_id: str) -> bool:
    """Delete a player by session ID."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(session_id=session_id).first()
        if player:
            username = player.username
            session.delete(player)
            logger.info(f"Deleted player '{username}' by session")
            return True
        return False

# ==============================================================================
# PLAYER STATISTICS SETTERS
# ==============================================================================

def increment_player_games_played(player_id: int) -> bool:
    """Increment the number of games played by a player."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            player.total_games_played += 1
            logger.debug(f"Incremented games played for player {player.username}")
            return True
        return False

def increment_player_games_won(player_id: int) -> bool:
    """Increment the number of games won by a player."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            player.total_games_won += 1
            logger.debug(f"Incremented games won for player {player.username}")
            return True
        return False

def increment_player_questions_asked(player_id: int, count: int = 1) -> bool:
    """Increment the number of questions asked by a player."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            player.total_questions_asked += count
            logger.debug(f"Incremented questions asked for player {player.username}")
            return True
        return False

def increment_player_questions_answered(player_id: int, count: int = 1) -> bool:
    """Increment the number of questions answered by a player."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            player.total_questions_answered += count
            logger.debug(f"Incremented questions answered for player {player.username}")
            return True
        return False

def increment_player_votes_received(player_id: int, count: int = 1) -> bool:
    """Increment the number of votes received by a player."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            player.total_votes_received += count
            logger.debug(f"Incremented votes received for player {player.username}")
            return True
        return False

def update_player_statistics(player_id: int,
                           games_played: Optional[int] = None,
                           games_won: Optional[int] = None,
                           questions_asked: Optional[int] = None,
                           questions_answered: Optional[int] = None,
                           votes_received: Optional[int] = None) -> bool:
    """Update multiple player statistics at once."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if not player:
            return False
            
        if games_played is not None:
            player.total_games_played = games_played
        if games_won is not None:
            player.total_games_won = games_won
        if questions_asked is not None:
            player.total_questions_asked = questions_asked
        if questions_answered is not None:
            player.total_questions_answered = questions_answered
        if votes_received is not None:
            player.total_votes_received = votes_received
            
        logger.info(f"Updated statistics for player {player.username}")
        return True

def record_game_results_for_players(player_results: dict) -> int:
    """
    Record game results for multiple players.
    
    Args:
        player_results: Dict with player_id as key and dict with stats as value
                       e.g. {player_id: {'won': True, 'questions_asked': 5}}
    
    Returns:
        Number of players successfully updated
    """
    updated_count = 0
    
    with get_db_session() as session:
        for player_id, results in player_results.items():
            player = session.query(Player).filter_by(id=player_id).first()
            if player:
                # Always increment games played
                player.total_games_played += 1
                
                # Increment games won if they won
                if results.get('won', False):
                    player.total_games_won += 1
                
                # Update statistics if provided
                if 'questions_asked' in results:
                    player.total_questions_asked += results['questions_asked']
                if 'questions_answered' in results:
                    player.total_questions_answered += results['questions_answered']
                if 'votes_received' in results:
                    player.total_votes_received += results['votes_received']
                
                updated_count += 1
                logger.debug(f"Updated game results for player {player.username}")
    
    logger.info(f"Updated game results for {updated_count} players")
    return updated_count

# ==============================================================================
# GAME STATISTICS SETTERS
# ==============================================================================

def create_statistics_entry(lobby_code: str = 'main') -> GameStatistics:
    """Create a new statistics entry."""
    with get_db_session() as session:
        stats = GameStatistics(lobby_code=lobby_code)
        session.add(stats)
        session.flush()
        logger.info(f"Created statistics entry for lobby '{lobby_code}'")
        return stats

def update_game_statistics(lobby_code: str = 'main', winner: Optional[str] = None) -> bool:
    """Update global game statistics."""
    with get_db_session() as session:
        stats = session.query(GameStatistics).filter_by(lobby_code=lobby_code).first()
        if not stats:
            stats = GameStatistics(lobby_code=lobby_code)
            session.add(stats)
        
        stats.total_games += 1
        
        if winner == 'humans':
            stats.human_wins += 1
        elif winner == 'ai':
            stats.ai_wins += 1
        
        logger.info(f"Updated statistics for '{lobby_code}': {winner} won (Total: {stats.total_games})")
        return True

def increment_human_wins(lobby_code: str = 'main') -> bool:
    """Increment human wins count."""
    return update_game_statistics(lobby_code, 'humans')

def increment_ai_wins(lobby_code: str = 'main') -> bool:
    """Increment AI wins count."""
    return update_game_statistics(lobby_code, 'ai')

def increment_total_games(lobby_code: str = 'main') -> bool:
    """Increment total games count without declaring a winner."""
    with get_db_session() as session:
        stats = session.query(GameStatistics).filter_by(lobby_code=lobby_code).first()
        if not stats:
            stats = GameStatistics(lobby_code=lobby_code)
            session.add(stats)
        
        stats.total_games += 1
        logger.info(f"Incremented total games for '{lobby_code}': {stats.total_games}")
        return True

def reset_statistics(lobby_code: str = 'main') -> bool:
    """Reset statistics for a lobby."""
    with get_db_session() as session:
        stats = session.query(GameStatistics).filter_by(lobby_code=lobby_code).first()
        if stats:
            stats.human_wins = 0
            stats.ai_wins = 0
            stats.total_games = 0
            logger.info(f"Reset statistics for lobby '{lobby_code}'")
            return True
        return False

def delete_statistics(lobby_code: str) -> bool:
    """Delete statistics entry for a lobby."""
    with get_db_session() as session:
        stats = session.query(GameStatistics).filter_by(lobby_code=lobby_code).first()
        if stats:
            session.delete(stats)
            logger.info(f"Deleted statistics for lobby '{lobby_code}'")
            return True
        return False

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def bulk_create_players(player_data: list) -> int:
    """
    Bulk create multiple players.
    
    Args:
        player_data: List of dicts with player information
    
    Returns:
        Number of players successfully created
    """
    created_count = 0
    
    with get_db_session() as session:
        for data in player_data:
            try:
                player = Player(**data)
                session.add(player)
                created_count += 1
            except Exception as e:
                logger.warning(f"Failed to create player {data.get('username', 'unknown')}: {e}")
        
        logger.info(f"Bulk created {created_count} players")
    
    return created_count

def cleanup_old_players(days_old: int = 30) -> int:
    """
    Clean up old player records that haven't been active.
    Note: Since we removed timestamps, this is a placeholder for now.
    """
    # Implementation would need additional timestamp field or different approach
    logger.info("Player cleanup not implemented without timestamps")
    return 0