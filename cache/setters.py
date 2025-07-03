"""
Redis Cache Setters for The Outsider Game.

All write operations for cached lobby and game data.
Handles fallbacks when Redis is unavailable.
"""

import logging
from typing import Optional, List, Dict, Any
from .client import redis_client
from .models import LobbyCache, GameCache, PlayerCache, MessageCache, VoteCache, RedisKeys, CacheTTL

logger = logging.getLogger(__name__)

# Lobby Operations
def create_lobby(code: str, name: str) -> bool:
    """Create a new lobby in Redis cache."""
    try:
        lobby = LobbyCache(code=code, name=name)
        key = RedisKeys.lobby_key(code)
        
        success = redis_client.set(key, lobby.to_dict(), CacheTTL.LOBBY_ACTIVE)
        if success:
            logger.info(f"Created lobby {code} in cache")
        return success
        
    except Exception as e:
        logger.error(f"Error creating lobby {code}: {e}")
        return False

def update_lobby(lobby: LobbyCache) -> bool:
    """Update lobby data in Redis cache."""
    try:
        key = RedisKeys.lobby_key(lobby.code)
        
        # Determine TTL based on state
        ttl = CacheTTL.LOBBY_ACTIVE if lobby.state in ['open', 'active'] else CacheTTL.LOBBY_ENDED
        
        success = redis_client.set(key, lobby.to_dict(), ttl)
        if success:
            logger.debug(f"Updated lobby {lobby.code} in cache")
        return success
        
    except Exception as e:
        logger.error(f"Error updating lobby {lobby.code}: {e}")
        return False

def delete_lobby(code: str) -> bool:
    """Delete lobby from Redis cache."""
    try:
        key = RedisKeys.lobby_key(code)
        success = redis_client.delete(key)
        
        if success:
            # Clean up related data
            redis_client.delete(RedisKeys.game_key(code))
            redis_client.delete(RedisKeys.messages_key(code))
            logger.info(f"Deleted lobby {code} from cache")
        
        return success
        
    except Exception as e:
        logger.error(f"Error deleting lobby {code}: {e}")
        return False

def add_player_to_lobby(code: str, player: PlayerCache) -> bool:
    """Add player to lobby."""
    try:
        # Get current lobby
        key = RedisKeys.lobby_key(code)
        data = redis_client.get(key)
        
        if not data:
            logger.warning(f"Cannot add player to non-existent lobby {code}")
            return False
        
        lobby = LobbyCache.from_dict(data)
        
        # Remove existing player with same session_id (if any)
        lobby.remove_player(player.session_id)
        
        # Add new player
        lobby.add_player(player)
        
        # Update lobby in cache
        success = update_lobby(lobby)
        
        if success:
            # Set player session mapping
            session_key = RedisKeys.player_session_key(player.session_id)
            redis_client.set(session_key, code, CacheTTL.PLAYER_SESSION)
            logger.info(f"Added player {player.username} to lobby {code}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error adding player {player.session_id} to lobby {code}: {e}")
        return False

def remove_player_from_lobby(code: str, session_id: str) -> bool:
    """Remove player from lobby."""
    try:
        # Get current lobby
        key = RedisKeys.lobby_key(code)
        data = redis_client.get(key)
        
        if not data:
            return True  # Lobby doesn't exist, consider removal successful
        
        lobby = LobbyCache.from_dict(data)
        
        # Remove player
        removed = lobby.remove_player(session_id)
        
        if removed:
            # Update lobby
            update_lobby(lobby)
            
            # Remove player session mapping
            session_key = RedisKeys.player_session_key(session_id)
            redis_client.delete(session_key)
            
            logger.info(f"Removed player {session_id} from lobby {code}")
        
        return removed
        
    except Exception as e:
        logger.error(f"Error removing player {session_id} from lobby {code}: {e}")
        return False

def update_player_in_lobby(code: str, player: PlayerCache) -> bool:
    """Update player data in lobby."""
    try:
        # Get current lobby
        key = RedisKeys.lobby_key(code)
        data = redis_client.get(key)
        
        if not data:
            return False
        
        lobby = LobbyCache.from_dict(data)
        
        # Find and update player
        for i, p in enumerate(lobby.players):
            if p.session_id == player.session_id:
                lobby.players[i] = player
                break
        else:
            # Player not found, add them
            lobby.add_player(player)
        
        success = update_lobby(lobby)
        if success:
            logger.debug(f"Updated player {player.session_id} in lobby {code}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error updating player {player.session_id} in lobby {code}: {e}")
        return False

def update_player_connection(code: str, session_id: str, is_connected: bool) -> bool:
    """Update player connection status."""
    try:
        # Get current lobby
        key = RedisKeys.lobby_key(code)
        data = redis_client.get(key)
        
        if not data:
            return False
        
        lobby = LobbyCache.from_dict(data)
        
        # Find and update player connection status
        player = lobby.get_player(session_id)
        if player:
            player.is_connected = is_connected
            success = update_lobby(lobby)
            
            if success:
                logger.debug(f"Updated connection status for player {session_id} in lobby {code}: {is_connected}")
            return success
        
        return False
        
    except Exception as e:
        logger.error(f"Error updating connection for player {session_id} in lobby {code}: {e}")
        return False

def set_lobby_location(code: str, location: str) -> bool:
    """Set the location for a lobby."""
    try:
        # Get current lobby
        key = RedisKeys.lobby_key(code)
        data = redis_client.get(key)
        
        if not data:
            return False
        
        lobby = LobbyCache.from_dict(data)
        lobby.location = location
        
        success = update_lobby(lobby)
        if success:
            logger.info(f"Set location '{location}' for lobby {code}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error setting location for lobby {code}: {e}")
        return False

def set_lobby_state(code: str, state: str) -> bool:
    """Set the state for a lobby."""
    try:
        # Get current lobby
        key = RedisKeys.lobby_key(code)
        data = redis_client.get(key)
        
        if not data:
            return False
        
        lobby = LobbyCache.from_dict(data)
        lobby.state = state
        
        success = update_lobby(lobby)
        if success:
            logger.info(f"Set state '{state}' for lobby {code}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error setting state for lobby {code}: {e}")
        return False

# Game Operations
def create_game(game: GameCache) -> bool:
    """Create a new game in Redis cache."""
    try:
        key = RedisKeys.game_key(game.lobby_code)
        
        success = redis_client.set(key, game.to_dict(), CacheTTL.GAME_ACTIVE)
        if success:
            logger.info(f"Created game for lobby {game.lobby_code} in cache")
        return success
        
    except Exception as e:
        logger.error(f"Error creating game for lobby {game.lobby_code}: {e}")
        return False

def update_game(game: GameCache) -> bool:
    """Update game data in Redis cache."""
    try:
        key = RedisKeys.game_key(game.lobby_code)
        
        # Determine TTL based on state
        ttl = CacheTTL.GAME_ACTIVE if game.state in ['active', 'voting'] else CacheTTL.GAME_ENDED
        
        success = redis_client.set(key, game.to_dict(), ttl)
        if success:
            logger.debug(f"Updated game for lobby {game.lobby_code} in cache")
        return success
        
    except Exception as e:
        logger.error(f"Error updating game for lobby {game.lobby_code}: {e}")
        return False

def delete_game(lobby_code: str) -> bool:
    """Delete game from Redis cache."""
    try:
        key = RedisKeys.game_key(lobby_code)
        success = redis_client.delete(key)
        
        if success:
            logger.info(f"Deleted game for lobby {lobby_code} from cache")
        
        return success
        
    except Exception as e:
        logger.error(f"Error deleting game for lobby {lobby_code}: {e}")
        return False

def set_game_state(lobby_code: str, state: str) -> bool:
    """Set game state."""
    try:
        key = RedisKeys.game_key(lobby_code)
        data = redis_client.get(key)
        
        if not data:
            return False
        
        game = GameCache.from_dict(data)
        game.state = state
        
        success = update_game(game)
        if success:
            logger.info(f"Set game state '{state}' for lobby {lobby_code}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error setting game state for lobby {lobby_code}: {e}")
        return False

def set_game_winner(lobby_code: str, winner: str, reason: Optional[str] = None) -> bool:
    """Set game winner and reason."""
    try:
        key = RedisKeys.game_key(lobby_code)
        data = redis_client.get(key)
        
        if not data:
            return False
        
        game = GameCache.from_dict(data)
        game.winner = winner
        if reason:
            game.winner_reason = reason
        game.state = 'ended'
        
        success = update_game(game)
        if success:
            logger.info(f"Set game winner '{winner}' for lobby {lobby_code}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error setting game winner for lobby {lobby_code}: {e}")
        return False

def update_game_turn(lobby_code: str, current_player: str, turn_count: int) -> bool:
    """Update game turn information."""
    try:
        key = RedisKeys.game_key(lobby_code)
        data = redis_client.get(key)
        
        if not data:
            return False
        
        game = GameCache.from_dict(data)
        game.current_turn_player = current_player
        game.turn_count = turn_count
        
        success = update_game(game)
        if success:
            logger.debug(f"Updated turn for lobby {lobby_code}: player {current_player}, turn {turn_count}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error updating game turn for lobby {lobby_code}: {e}")
        return False

def set_voting_phase(lobby_code: str, voting: bool) -> bool:
    """Set voting phase status."""
    try:
        key = RedisKeys.game_key(lobby_code)
        data = redis_client.get(key)
        
        if not data:
            return False
        
        game = GameCache.from_dict(data)
        game.voting_phase = voting
        if voting:
            game.state = 'voting'
        
        success = update_game(game)
        if success:
            logger.info(f"Set voting phase {voting} for lobby {lobby_code}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error setting voting phase for lobby {lobby_code}: {e}")
        return False

# Message Operations
def add_message_to_lobby(lobby_code: str, message: MessageCache) -> bool:
    """Add message to lobby message history."""
    try:
        key = RedisKeys.messages_key(lobby_code)
        
        # Get existing messages
        data = redis_client.get(key)
        messages = data if isinstance(data, list) else []
        
        # Add new message
        messages.append(message.to_dict())
        
        # Keep only last 100 messages
        if len(messages) > 100:
            messages = messages[-100:]
        
        success = redis_client.set(key, messages, CacheTTL.MESSAGES)
        if success:
            logger.debug(f"Added message to lobby {lobby_code}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error adding message to lobby {lobby_code}: {e}")
        return False

# Vote Operations
def add_vote_to_lobby(lobby_code: str, vote: VoteCache) -> bool:
    """Add vote to lobby vote history."""
    try:
        key = RedisKeys.votes_key(lobby_code, vote.vote_round)
        
        # Get existing votes for this round
        data = redis_client.get(key)
        votes = data if isinstance(data, list) else []
        
        # Remove any existing vote from this voter in this round
        votes = [v for v in votes if v.get('voter_session_id') != vote.voter_session_id]
        
        # Add new vote
        votes.append(vote.to_dict())
        
        success = redis_client.set(key, votes, CacheTTL.VOTES)
        if success:
            logger.info(f"Added vote from {vote.voter_session_id} for {vote.target_session_id} in lobby {lobby_code}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error adding vote to lobby {lobby_code}: {e}")
        return False

def clear_votes_for_round(lobby_code: str, round_num: int) -> bool:
    """Clear all votes for a specific round."""
    try:
        key = RedisKeys.votes_key(lobby_code, round_num)
        success = redis_client.delete(key)
        
        if success:
            logger.info(f"Cleared votes for lobby {lobby_code} round {round_num}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error clearing votes for lobby {lobby_code} round {round_num}: {e}")
        return False

# Cleanup Operations
def cleanup_lobby_data(code: str) -> bool:
    """Clean up all data related to a lobby."""
    try:
        # Delete all related keys
        lobby_key = RedisKeys.lobby_key(code)
        game_key = RedisKeys.game_key(code)
        messages_key = RedisKeys.messages_key(code)
        
        # Delete vote keys (check multiple rounds)
        for round_num in range(1, 6):  # Clean up to 5 rounds
            vote_key = RedisKeys.votes_key(code, round_num)
            redis_client.delete(vote_key)
        
        # Delete main keys
        redis_client.delete(lobby_key)
        redis_client.delete(game_key)
        redis_client.delete(messages_key)
        
        # Clean up player session mappings
        lobby_data = redis_client.get(lobby_key)
        if lobby_data:
            lobby = LobbyCache.from_dict(lobby_data)
            for player in lobby.players:
                session_key = RedisKeys.player_session_key(player.session_id)
                redis_client.delete(session_key)
        
        logger.info(f"Cleaned up all data for lobby {code}")
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning up lobby data for {code}: {e}")
        return False

def bulk_update_lobbies(lobbies: List[LobbyCache]) -> int:
    """Bulk update multiple lobbies. Returns count of successful updates."""
    try:
        success_count = 0
        for lobby in lobbies:
            if update_lobby(lobby):
                success_count += 1
        
        logger.info(f"Bulk updated {success_count}/{len(lobbies)} lobbies")
        return success_count
        
    except Exception as e:
        logger.error(f"Error in bulk lobby update: {e}")
        return 0

def bulk_update_games(games: List[GameCache]) -> int:
    """Bulk update multiple games. Returns count of successful updates."""
    try:
        success_count = 0
        for game in games:
            if update_game(game):
                success_count += 1
        
        logger.info(f"Bulk updated {success_count}/{len(games)} games")
        return success_count
        
    except Exception as e:
        logger.error(f"Error in bulk game update: {e}")
        return 0