"""
Redis Cache Module for The Outsider Game.

Handles temporary game and lobby data using Redis for fast operations.
Database is only used for persistent player and statistics data.
"""

from .client import redis_client
from .models import LobbyCache, GameCache, PlayerCache, MessageCache, VoteCache, RedisKeys, CacheTTL

# Import all getter functions
from .getters import (
    # Lobby operations
    get_lobby_by_code,
    get_all_active_lobbies,
    lobby_exists,
    get_lobby_player_count,
    get_players_in_lobby,
    get_human_players_in_lobby,
    get_ai_players_in_lobby,
    get_connected_players_in_lobby,
    get_player_in_lobby,
    find_player_lobby,
    
    # Game operations
    get_game_by_lobby,
    game_exists_for_lobby,
    get_all_active_games,
    
    # Message operations
    get_messages_for_lobby,
    
    # Vote operations
    get_votes_for_lobby,
    get_vote_count_for_player,
    has_player_voted,
    
    # Utility functions
    get_cache_stats,
    cleanup_expired_data
)

# Import all setter functions
from .setters import (
    # Lobby operations
    create_lobby,
    update_lobby,
    delete_lobby,
    add_player_to_lobby,
    remove_player_from_lobby,
    update_player_in_lobby,
    update_player_connection,
    set_lobby_location,
    set_lobby_state,
    
    # Game operations
    create_game,
    update_game,
    delete_game,
    set_game_state,
    set_game_winner,
    update_game_turn,
    set_voting_phase,
    
    # Message operations
    add_message_to_lobby,
    
    # Vote operations
    add_vote_to_lobby,
    clear_votes_for_round,
    
    # Cleanup operations
    cleanup_lobby_data,
    bulk_update_lobbies,
    bulk_update_games
)

__all__ = [
    # Client and models
    'redis_client',
    'LobbyCache', 
    'GameCache',
    'PlayerCache',
    'MessageCache',
    'VoteCache',
    'RedisKeys',
    'CacheTTL',
    
    # Getters
    'get_lobby_by_code',
    'get_all_active_lobbies',
    'lobby_exists',
    'get_lobby_player_count',
    'get_players_in_lobby',
    'get_human_players_in_lobby',
    'get_ai_players_in_lobby',
    'get_connected_players_in_lobby',
    'get_player_in_lobby',
    'find_player_lobby',
    'get_game_by_lobby',
    'game_exists_for_lobby',
    'get_all_active_games',
    'get_messages_for_lobby',
    'get_votes_for_lobby',
    'get_vote_count_for_player',
    'has_player_voted',
    'get_cache_stats',
    'cleanup_expired_data',
    
    # Setters
    'create_lobby',
    'update_lobby',
    'delete_lobby',
    'add_player_to_lobby',
    'remove_player_from_lobby',
    'update_player_in_lobby',
    'update_player_connection',
    'set_lobby_location',
    'set_lobby_state',
    'create_game',
    'update_game',
    'delete_game',
    'set_game_state',
    'set_game_winner',
    'update_game_turn',
    'set_voting_phase',
    'add_message_to_lobby',
    'add_vote_to_lobby',
    'clear_votes_for_round',
    'cleanup_lobby_data',
    'bulk_update_lobbies',
    'bulk_update_games'
]