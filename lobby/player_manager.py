"""
Player management for lobbies.

Handles player operations like joining, leaving, validation, and AI player management.
"""

import logging
from typing import Optional, List, Tuple
from datetime import datetime
from .models import PlayerData, LobbyData
from utils.constants import AI_NAMES
from utils.helpers import validate_username, get_available_ai_name

logger = logging.getLogger(__name__)

class PlayerManager:
    """Manages player operations within lobbies."""
    
    def __init__(self):
        pass
    
    def add_player(self, lobby_data: LobbyData, session_id: str, username: str, 
                  is_spectator: bool = False, is_ai: bool = False) -> Tuple[bool, str, Optional[PlayerData]]:
        """
        Add a player to a lobby.
        
        Args:
            lobby_data: The lobby to add player to
            session_id: Player's session ID
            username: Player's chosen username
            is_spectator: Whether player is joining as spectator
            is_ai: Whether this is an AI player
            
        Returns:
            tuple: (success, message, player_data)
        """
        try:
            # Validate username for human players
            if not is_ai:
                is_valid, error_msg = validate_username(username)
                if not is_valid:
                    return False, error_msg or "Invalid username", None
            
            # Check if lobby is full (spectators can always join)
            if not is_spectator and lobby_data.is_full:
                return False, f"Lobby is full ({lobby_data.max_players} players max)", None
            
            # Check if username is already taken
            existing_player = lobby_data.get_player_by_username(username)
            if existing_player:
                return False, f"Username '{username}' is already taken", None
            
            # Check if session already has a player
            existing_session = lobby_data.get_player_by_session(session_id)
            if existing_session:
                return False, "Session already has a player in this lobby", None
            
            # Create player data
            player_data = PlayerData(
                session_id=session_id,
                username=username,
                is_ai=is_ai,
                is_spectator=is_spectator,
                is_connected=True,
                joined_at=datetime.utcnow()
            )
            
            # Add to lobby
            lobby_data.players.append(player_data)
            
            logger.info(f"Player {username} ({'AI' if is_ai else 'Human'}) added to lobby {lobby_data.code}")
            return True, "Player added successfully", player_data
            
        except Exception as e:
            logger.error(f"Error adding player: {e}")
            return False, "Failed to add player", None
    
    def remove_player(self, lobby_data: LobbyData, session_id: str) -> Tuple[bool, str, Optional[str]]:
        """
        Remove a player from a lobby.
        
        Args:
            lobby_data: The lobby to remove player from
            session_id: Session ID of player to remove
            
        Returns:
            tuple: (success, message, removed_username)
        """
        try:
            player = lobby_data.get_player_by_session(session_id)
            if not player:
                return False, "Player not found in lobby", None
            
            # Remove player
            lobby_data.players.remove(player)
            
            logger.info(f"Player {player.username} removed from lobby {lobby_data.code}")
            return True, f"Player {player.username} removed", player.username
            
        except Exception as e:
            logger.error(f"Error removing player: {e}")
            return False, "Failed to remove player", None
    
    def disconnect_player(self, lobby_data: LobbyData, session_id: str) -> Tuple[bool, str, Optional[str]]:
        """
        Mark a player as disconnected without removing them.
        
        Args:
            lobby_data: The lobby containing the player
            session_id: Session ID of player to disconnect
            
        Returns:
            tuple: (success, message, disconnected_username)
        """
        try:
            player = lobby_data.get_player_by_session(session_id)
            if not player:
                return False, "Player not found in lobby", None
            
            # Mark as disconnected
            player.is_connected = False
            
            logger.info(f"Player {player.username} disconnected from lobby {lobby_data.code}")
            return True, f"Player {player.username} disconnected", player.username
            
        except Exception as e:
            logger.error(f"Error disconnecting player: {e}")
            return False, "Failed to disconnect player", None
    
    def reconnect_player(self, lobby_data: LobbyData, session_id: str, new_session_id: str) -> Tuple[bool, str, Optional[PlayerData]]:
        """
        Reconnect a disconnected player with a new session ID.
        
        Args:
            lobby_data: The lobby containing the player
            session_id: Original session ID
            new_session_id: New session ID
            
        Returns:
            tuple: (success, message, player_data)
        """
        try:
            player = lobby_data.get_player_by_session(session_id)
            if not player:
                return False, "Player not found in lobby", None
            
            # Update session ID and mark as connected
            player.session_id = new_session_id
            player.is_connected = True
            
            logger.info(f"Player {player.username} reconnected to lobby {lobby_data.code}")
            return True, f"Player {player.username} reconnected", player
            
        except Exception as e:
            logger.error(f"Error reconnecting player: {e}")
            return False, "Failed to reconnect player", None
    
    def add_ai_player(self, lobby_data: LobbyData) -> Tuple[bool, str, Optional[PlayerData]]:
        """
        Add an AI player to a lobby.
        
        Args:
            lobby_data: The lobby to add AI player to
            
        Returns:
            tuple: (success, message, ai_player_data)
        """
        try:
            # Check if lobby is full
            if lobby_data.is_full:
                return False, "Lobby is full", None
            
            # Get existing player names
            existing_names = [p.username for p in lobby_data.players]
            
            # Get available AI name
            ai_name = get_available_ai_name(existing_names)
            if not ai_name:
                return False, "No AI names available", None
            
            # Generate unique session ID for AI
            ai_session_id = f"ai_{lobby_data.code}_{len(lobby_data.get_ai_players()) + 1}"
            
            # Add AI player
            return self.add_player(
                lobby_data=lobby_data,
                session_id=ai_session_id,
                username=ai_name,
                is_ai=True
            )
            
        except Exception as e:
            logger.error(f"Error adding AI player: {e}")
            return False, "Failed to add AI player", None
    
    def remove_ai_player(self, lobby_data: LobbyData) -> Tuple[bool, str, Optional[str]]:
        """
        Remove an AI player from a lobby.
        
        Args:
            lobby_data: The lobby to remove AI player from
            
        Returns:
            tuple: (success, message, removed_ai_name)
        """
        try:
            ai_players = lobby_data.get_ai_players()
            if not ai_players:
                return False, "No AI players to remove", None
            
            # Remove the last AI player
            ai_player = ai_players[-1]
            return self.remove_player(lobby_data, ai_player.session_id)
            
        except Exception as e:
            logger.error(f"Error removing AI player: {e}")
            return False, "Failed to remove AI player", None
    
    def get_player_list(self, lobby_data: LobbyData, include_disconnected: bool = True) -> List[PlayerData]:
        """
        Get a list of players in the lobby.
        
        Args:
            lobby_data: The lobby to get players from
            include_disconnected: Whether to include disconnected players
            
        Returns:
            List of player data
        """
        if include_disconnected:
            return lobby_data.players.copy()
        else:
            return [p for p in lobby_data.players if p.is_connected]
    
    def get_connected_players(self, lobby_data: LobbyData) -> List[PlayerData]:
        """Get only connected players."""
        return self.get_player_list(lobby_data, include_disconnected=False)
    
    def cleanup_disconnected_players(self, lobby_data: LobbyData, 
                                   timeout_minutes: int = 10) -> List[str]:
        """
        Clean up players who have been disconnected for too long.
        
        Args:
            lobby_data: The lobby to clean up
            timeout_minutes: Minutes after which to remove disconnected players
            
        Returns:
            List of usernames of removed players
        """
        try:
            from datetime import timedelta
            
            removed_players = []
            current_time = datetime.utcnow()
            
            # For simplicity, we'll just track disconnection from when is_connected was set to False
            # In a real implementation, you'd want to track disconnection time
            players_to_remove = []
            
            for player in lobby_data.players:
                if not player.is_connected and not player.is_ai:
                    # For now, remove all disconnected human players
                    # In future, could implement timeout logic based on disconnection time
                    players_to_remove.append(player)
            
            for player in players_to_remove:
                lobby_data.players.remove(player)
                removed_players.append(player.username)
                logger.info(f"Cleaned up disconnected player {player.username} from lobby {lobby_data.code}")
            
            return removed_players
            
        except Exception as e:
            logger.error(f"Error cleaning up disconnected players: {e}")
            return []