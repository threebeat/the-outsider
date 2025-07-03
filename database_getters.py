"""
Universal Database Getters for The Outsider.

Contains all read operations from the database. All session management
is contained within this module - other modules should never handle sessions directly.
"""

import logging
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from database import get_db_session, Lobby, Player, GameMessage, Vote, GameSession, GameStatistics

logger = logging.getLogger(__name__)

# ==============================================================================
# UNIVERSAL GETTERS - ALL READ OPERATIONS
# ==============================================================================

def get_player(lobby_id: Optional[int] = None, 
               player_id: Optional[int] = None,
               session_id: Optional[str] = None,
               username: Optional[str] = None,
               is_ai: Optional[bool] = None,
               is_connected: Optional[bool] = True,
               is_spectator: Optional[bool] = None) -> Optional[Player]:
    """
    Universal player getter that can search by any combination of criteria.
    
    Args:
        lobby_id: Filter by lobby ID
        player_id: Filter by player ID
        session_id: Filter by session ID
        username: Filter by username
        is_ai: Filter by AI status (True for AI players/outsiders, False for humans)
        is_connected: Filter by connection status (defaults to True)
        is_spectator: Filter by spectator status
    
    Returns:
        First matching player or None
    """
    with get_db_session() as session:
        query = session.query(Player)
        
        if player_id is not None:
            query = query.filter(Player.id == player_id)
        if lobby_id is not None:
            query = query.filter(Player.lobby_id == lobby_id)
        if session_id is not None:
            query = query.filter(Player.session_id == session_id)
        if username is not None:
            query = query.filter(Player.username == username)
        if is_ai is not None:
            query = query.filter(Player.is_ai == is_ai)
        if is_connected is not None:
            query = query.filter(Player.is_connected == is_connected)
        if is_spectator is not None:
            query = query.filter(Player.is_spectator == is_spectator)
            
        return query.first()

def get_players(lobby_id: Optional[int] = None,
                is_ai: Optional[bool] = None,
                is_connected: Optional[bool] = True,
                is_spectator: Optional[bool] = None,
                limit: Optional[int] = None) -> List[Player]:
    """
    Universal players getter that can search by any combination of criteria.
    
    Args:
        lobby_id: Filter by lobby ID
        is_ai: Filter by AI status (True for AI players/outsiders, False for humans)
        is_connected: Filter by connection status (defaults to True)
        is_spectator: Filter by spectator status
        limit: Maximum number of results
    
    Returns:
        List of matching players
    """
    with get_db_session() as session:
        query = session.query(Player)
        
        if lobby_id is not None:
            query = query.filter(Player.lobby_id == lobby_id)
        if is_ai is not None:
            query = query.filter(Player.is_ai == is_ai)
        if is_connected is not None:
            query = query.filter(Player.is_connected == is_connected)
        if is_spectator is not None:
            query = query.filter(Player.is_spectator == is_spectator)
            
        if limit is not None:
            query = query.limit(limit)
            
        return query.all()

def get_lobby_by_code(code: str) -> Optional[Lobby]:
    """Get a lobby by its code."""
    with get_db_session() as session:
        return session.query(Lobby).filter_by(code=code).first()

def get_lobby_by_id(lobby_id: int) -> Optional[Lobby]:
    """Get a lobby by its ID."""
    with get_db_session() as session:
        return session.query(Lobby).filter_by(id=lobby_id).first()

def get_player_by_session_id(session_id: str) -> Optional[Player]:
    """Get a player by their session ID."""
    return get_player(session_id=session_id, is_connected=True)

def get_player_by_id(player_id: int) -> Optional[Player]:
    """Get a player by their ID."""
    return get_player(player_id=player_id)

def get_player_by_username(lobby_id: int, username: str) -> Optional[Player]:
    """Get a player by username in a specific lobby."""
    return get_player(lobby_id=lobby_id, username=username, is_connected=True)

def get_active_lobbies() -> List[Lobby]:
    """Get all active lobbies."""
    with get_db_session() as session:
        return session.query(Lobby).filter(
            Lobby.state.in_(['waiting', 'playing'])
        ).all()

def get_all_lobbies() -> List[Lobby]:
    """Get all lobbies."""
    with get_db_session() as session:
        return session.query(Lobby).all()

def get_game_statistics(lobby_code: str = 'main') -> Optional[GameStatistics]:
    """Get game statistics for a lobby."""
    with get_db_session() as session:
        return session.query(GameStatistics).filter_by(lobby_code=lobby_code).first()

def get_active_game_session(lobby_id: int) -> Optional[GameSession]:
    """Get the active game session for a lobby."""
    with get_db_session() as session:
        return session.query(GameSession).filter_by(
            lobby_id=lobby_id,
            ended_at=None
        ).first()

def get_latest_game_session(lobby_id: int) -> Optional[GameSession]:
    """Get the most recent game session for a lobby."""
    with get_db_session() as session:
        return session.query(GameSession).filter_by(lobby_id=lobby_id)\
            .order_by(GameSession.session_number.desc()).first()

def get_player_count_in_lobby(lobby_id: int) -> int:
    """Get the number of active players in a lobby."""
    return len(get_players(lobby_id=lobby_id, is_connected=True, is_spectator=False))

def get_ai_players_in_lobby(lobby_id: int) -> List[Player]:
    """Get all AI players (outsiders) in a lobby."""
    return get_players(lobby_id=lobby_id, is_ai=True, is_connected=True)

def get_human_players_in_lobby(lobby_id: int) -> List[Player]:
    """Get all human players in a lobby."""
    return get_players(lobby_id=lobby_id, is_ai=False, is_connected=True, is_spectator=False)

def get_all_players_in_lobby(lobby_id: int) -> List[Player]:
    """Get all connected players in a lobby (both human and AI)."""
    return get_players(lobby_id=lobby_id, is_connected=True)

def get_active_players_in_lobby(lobby_id: int) -> List[Player]:
    """Get all active (non-spectator) players in a lobby."""
    return get_players(lobby_id=lobby_id, is_connected=True, is_spectator=False)

def get_lobby_messages(lobby_id: int, limit: int = 50) -> List[GameMessage]:
    """Get recent messages from a lobby."""
    with get_db_session() as session:
        return session.query(GameMessage).filter_by(lobby_id=lobby_id)\
            .order_by(GameMessage.created_at.desc())\
            .limit(limit).all()

def get_lobby_votes(lobby_id: int, vote_round: int = 1) -> List[Vote]:
    """Get votes from a specific round in a lobby."""
    with get_db_session() as session:
        return session.query(Vote).filter_by(
            lobby_id=lobby_id,
            vote_round=vote_round
        ).all()

def get_player_votes_cast(player_id: int, lobby_id: int) -> List[Vote]:
    """Get all votes cast by a player in a lobby."""
    with get_db_session() as session:
        return session.query(Vote).filter_by(
            voter_id=player_id,
            lobby_id=lobby_id
        ).all()

def get_player_votes_received(player_id: int, lobby_id: int) -> List[Vote]:
    """Get all votes received by a player in a lobby."""
    with get_db_session() as session:
        return session.query(Vote).filter_by(
            target_id=player_id,
            lobby_id=lobby_id
        ).all()

def get_game_sessions_for_lobby(lobby_id: int) -> List[GameSession]:
    """Get all game sessions for a lobby."""
    with get_db_session() as session:
        return session.query(GameSession).filter_by(lobby_id=lobby_id)\
            .order_by(GameSession.session_number.desc()).all()

def get_lobby_by_player_session(session_id: str) -> Optional[Lobby]:
    """Get lobby that a player session is connected to."""
    player = get_player(session_id=session_id, is_connected=True)
    if player:
        return get_lobby_by_id(player.lobby_id)
    return None

def is_username_taken(lobby_id: int, username: str, exclude_player_id: Optional[int] = None) -> bool:
    """Check if a username is already taken in a lobby."""
    with get_db_session() as session:
        query = session.query(Player).filter_by(
            lobby_id=lobby_id,
            username=username,
            is_connected=True
        )
        
        if exclude_player_id:
            query = query.filter(Player.id != exclude_player_id)
            
        return query.first() is not None

def is_lobby_code_taken(code: str) -> bool:
    """Check if a lobby code is already in use."""
    with get_db_session() as session:
        return session.query(Lobby).filter_by(code=code).first() is not None

def get_lobby_capacity_info(lobby_id: int) -> dict:
    """Get capacity information for a lobby."""
    with get_db_session() as session:
        lobby = session.query(Lobby).filter_by(id=lobby_id).first()
        if not lobby:
            return {}
        
        player_count = len(get_players(lobby_id=lobby_id, is_connected=True, is_spectator=False))
        
        return {
            'current_players': player_count,
            'max_players': lobby.max_players,
            'can_join': player_count < lobby.max_players,
            'slots_available': lobby.max_players - player_count
        }