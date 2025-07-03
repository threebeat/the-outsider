"""
Redis Cache Getters for The Outsider Game.

All read operations for cached lobby and game data.
Handles fallbacks when Redis is unavailable.
"""

import logging
from typing import Optional, List, Dict, Any
from .client import redis_client
from .models import LobbyCache, GameCache, PlayerCache, MessageCache, VoteCache, RedisKeys

logger = logging.getLogger(__name__)

# Lobby Operations
def get_lobby_by_code(code: str) -> Optional[LobbyCache]:
    """Get lobby by code from Redis cache."""
    try:
        key = RedisKeys.lobby_key(code)
        data = redis_client.get(key)
        
        if data:
            return LobbyCache.from_dict(data)
        return None
        
    except Exception as e:
        logger.error(f"Error getting lobby {code}: {e}")
        return None

def get_all_active_lobbies() -> List[LobbyCache]:
    """Get all active lobbies from Redis."""
    try:
        # Get all lobby keys
        lobby_keys = redis_client.keys("lobby:*")
        lobbies = []
        
        for key in lobby_keys:
            data = redis_client.get(key)
            if data:
                lobby = LobbyCache.from_dict(data)
                if lobby.state in ['open', 'active']:
                    lobbies.append(lobby)
        
        return lobbies
        
    except Exception as e:
        logger.error(f"Error getting active lobbies: {e}")
        return []

def lobby_exists(code: str) -> bool:
    """Check if lobby exists in Redis."""
    try:
        key = RedisKeys.lobby_key(code)
        return redis_client.exists(key)
    except Exception as e:
        logger.error(f"Error checking lobby existence {code}: {e}")
        return False

def get_lobby_player_count(code: str) -> int:
    """Get number of players in lobby."""
    try:
        lobby = get_lobby_by_code(code)
        if lobby:
            return len(lobby.get_connected_players())
        return 0
    except Exception as e:
        logger.error(f"Error getting player count for lobby {code}: {e}")
        return 0

def get_players_in_lobby(code: str) -> List[PlayerCache]:
    """Get all players in a lobby."""
    try:
        lobby = get_lobby_by_code(code)
        if lobby:
            return lobby.players
        return []
    except Exception as e:
        logger.error(f"Error getting players in lobby {code}: {e}")
        return []

def get_human_players_in_lobby(code: str) -> List[PlayerCache]:
    """Get human players in a lobby."""
    try:
        lobby = get_lobby_by_code(code)
        if lobby:
            return lobby.get_human_players()
        return []
    except Exception as e:
        logger.error(f"Error getting human players in lobby {code}: {e}")
        return []

def get_ai_players_in_lobby(code: str) -> List[PlayerCache]:
    """Get AI players in a lobby."""
    try:
        lobby = get_lobby_by_code(code)
        if lobby:
            return lobby.get_ai_players()
        return []
    except Exception as e:
        logger.error(f"Error getting AI players in lobby {code}: {e}")
        return []

def get_connected_players_in_lobby(code: str) -> List[PlayerCache]:
    """Get connected players in a lobby."""
    try:
        lobby = get_lobby_by_code(code)
        if lobby:
            return lobby.get_connected_players()
        return []
    except Exception as e:
        logger.error(f"Error getting connected players in lobby {code}: {e}")
        return []

def get_player_in_lobby(code: str, session_id: str) -> Optional[PlayerCache]:
    """Get specific player in a lobby."""
    try:
        lobby = get_lobby_by_code(code)
        if lobby:
            return lobby.get_player(session_id)
        return None
    except Exception as e:
        logger.error(f"Error getting player {session_id} in lobby {code}: {e}")
        return None

def find_player_lobby(session_id: str) -> Optional[str]:
    """Find which lobby a player is in by session_id."""
    try:
        # Check player session mapping first
        key = RedisKeys.player_session_key(session_id)
        lobby_code = redis_client.get(key)
        
        if lobby_code:
            # Verify player is still in that lobby
            if get_player_in_lobby(lobby_code, session_id):
                return lobby_code
        
        # Fallback: search all lobbies (slower)
        lobbies = get_all_active_lobbies()
        for lobby in lobbies:
            if lobby.get_player(session_id):
                return lobby.code
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding lobby for player {session_id}: {e}")
        return None

# Game Operations
def get_game_by_lobby(lobby_code: str) -> Optional[GameCache]:
    """Get game data for a lobby."""
    try:
        key = RedisKeys.game_key(lobby_code)
        data = redis_client.get(key)
        
        if data:
            return GameCache.from_dict(data)
        return None
        
    except Exception as e:
        logger.error(f"Error getting game for lobby {lobby_code}: {e}")
        return None

def game_exists_for_lobby(lobby_code: str) -> bool:
    """Check if game exists for lobby."""
    try:
        key = RedisKeys.game_key(lobby_code)
        return redis_client.exists(key)
    except Exception as e:
        logger.error(f"Error checking game existence for lobby {lobby_code}: {e}")
        return False

def get_all_active_games() -> List[GameCache]:
    """Get all active games."""
    try:
        game_keys = redis_client.keys("game:*")
        games = []
        
        for key in game_keys:
            data = redis_client.get(key)
            if data:
                game = GameCache.from_dict(data)
                if game.state in ['active', 'voting']:
                    games.append(game)
        
        return games
        
    except Exception as e:
        logger.error(f"Error getting active games: {e}")
        return []

# Message Operations
def get_messages_for_lobby(lobby_code: str, limit: int = 50) -> List[MessageCache]:
    """Get recent messages for a lobby."""
    try:
        key = RedisKeys.messages_key(lobby_code)
        data = redis_client.get(key)
        
        if data and isinstance(data, list):
            messages = [MessageCache.from_dict(msg) for msg in data[-limit:]]
            return messages
        return []
        
    except Exception as e:
        logger.error(f"Error getting messages for lobby {lobby_code}: {e}")
        return []

# Vote Operations
def get_votes_for_lobby(lobby_code: str, round_num: int = 1) -> List[VoteCache]:
    """Get votes for a lobby in a specific round."""
    try:
        key = RedisKeys.votes_key(lobby_code, round_num)
        data = redis_client.get(key)
        
        if data and isinstance(data, list):
            votes = [VoteCache.from_dict(vote) for vote in data]
            return votes
        return []
        
    except Exception as e:
        logger.error(f"Error getting votes for lobby {lobby_code} round {round_num}: {e}")
        return []

def get_vote_count_for_player(lobby_code: str, target_session_id: str, round_num: int = 1) -> int:
    """Get vote count for a specific player."""
    try:
        votes = get_votes_for_lobby(lobby_code, round_num)
        return len([v for v in votes if v.target_session_id == target_session_id])
    except Exception as e:
        logger.error(f"Error getting vote count for player {target_session_id}: {e}")
        return 0

def has_player_voted(lobby_code: str, voter_session_id: str, round_num: int = 1) -> bool:
    """Check if player has already voted in this round."""
    try:
        votes = get_votes_for_lobby(lobby_code, round_num)
        return any(v.voter_session_id == voter_session_id for v in votes)
    except Exception as e:
        logger.error(f"Error checking if player {voter_session_id} has voted: {e}")
        return False

# Utility Functions
def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics and health info."""
    try:
        if not redis_client.is_connected():
            return {
                'connected': False,
                'total_lobbies': 0,
                'total_games': 0,
                'total_keys': 0
            }
        
        lobby_keys = redis_client.keys("lobby:*")
        game_keys = redis_client.keys("game:*")
        all_keys = redis_client.keys("*")
        
        return {
            'connected': True,
            'total_lobbies': len(lobby_keys),
            'total_games': len(game_keys),
            'total_keys': len(all_keys),
            'lobby_keys': lobby_keys[:10],  # Sample
            'game_keys': game_keys[:10]     # Sample
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {
            'connected': False,
            'error': str(e)
        }

def cleanup_expired_data() -> Dict[str, Any]:
    """Clean up any expired or orphaned data."""
    try:
        if not redis_client.is_connected():
            return {'cleaned': 0, 'error': 'Redis not connected'}
        
        cleaned = 0
        
        # Remove empty lobbies
        lobby_keys = redis_client.keys("lobby:*")
        for key in lobby_keys:
            data = redis_client.get(key)
            if data:
                lobby = LobbyCache.from_dict(data)
                if len(lobby.get_connected_players()) == 0:
                    redis_client.delete(key)
                    cleaned += 1
        
        return {'cleaned': cleaned}
        
    except Exception as e:
        logger.error(f"Error cleaning up expired data: {e}")
        return {'cleaned': 0, 'error': str(e)}