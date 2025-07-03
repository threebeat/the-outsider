"""
Database Package for The Outsider.

Provides clean imports for all database functionality.
"""

# Models
from .models import (
    Base,
    Lobby,
    Player,
    GameMessage,
    Vote,
    GameSession,
    GameStatistics
)

# Configuration and session management
from .config import (
    engine,
    SessionLocal,
    get_db_session,
    init_database,
    clean_database
)

# Import getter functions
from .getters import (
    get_player,
    get_players,
    get_players_from_lobby,
    get_lobby_by_code,
    get_lobby_by_id,
    get_player_by_session_id,
    get_player_by_id,
    get_player_by_username,
    get_open_lobbies,
    get_all_lobbies,
    get_game_statistics,
    get_active_game_session,
    get_latest_game_session,
    get_lobby_messages,
    get_lobby_votes,
    get_player_votes_cast,
    get_player_votes_received,
    get_game_sessions_for_lobby,
    get_lobby_by_player_session,
    is_username_taken,
    is_lobby_code_taken,
    can_join_lobby
)

# Import setter functions
from .setters import (
    create_lobby,
    create_player,
    set_lobby_active,
    set_lobby_open,
    update_player_connection,
    create_game_session,
    create_game_message,
    create_vote,
    update_game_statistics,
    delete_player,
    update_lobby_activity,
    update_player_last_seen,
    increment_player_questions_asked,
    increment_player_questions_answered,
    increment_player_votes_received,
    update_player_ai_strategy,
    end_game_session,
    reset_lobby_for_new_game,
    disconnect_all_players_in_lobby,
    delete_lobby,
    create_statistics_entry
)

__all__ = [
    # Models
    "Base",
    "Lobby",
    "Player", 
    "GameMessage",
    "Vote",
    "GameSession",
    "GameStatistics",
    
    # Configuration
    "engine",
    "SessionLocal", 
    "get_db_session",
    "init_database",
    "clean_database",
    
    # Getters
    "get_player",
    "get_players",
    "get_players_from_lobby",
    "get_lobby_by_code",
    "get_lobby_by_id",
    "get_player_by_session_id",
    "get_player_by_id", 
    "get_player_by_username",
    "get_open_lobbies",
    "get_all_lobbies",
    "get_game_statistics",
    "get_active_game_session",
    "get_latest_game_session",
    "get_lobby_messages",
    "get_lobby_votes",
    "get_player_votes_cast",
    "get_player_votes_received",
    "get_game_sessions_for_lobby",
    "get_lobby_by_player_session",
    "is_username_taken",
    "is_lobby_code_taken",
    "can_join_lobby",
    
    # Setters
    "create_lobby",
    "create_player",
    "set_lobby_active",
    "set_lobby_open", 
    "update_player_connection",
    "create_game_session",
    "create_game_message",
    "create_vote",
    "update_game_statistics",
    "delete_player",
    "update_lobby_activity",
    "update_player_last_seen",
    "increment_player_questions_asked",
    "increment_player_questions_answered",
    "increment_player_votes_received",
    "update_player_ai_strategy",
    "end_game_session",
    "reset_lobby_for_new_game",
    "disconnect_all_players_in_lobby",
    "delete_lobby",
    "create_statistics_entry",
]