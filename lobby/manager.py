"""
Main lobby management system.

Handles lobby creation, lifecycle, and coordinates between
player management and database persistence.
"""

import logging
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from .models import LobbyData, PlayerData, LobbyListItem
from .player_manager import PlayerManager
from utils.constants import GAME_CONFIG
from utils.helpers import generate_lobby_code

# Import database access functions (pure data access)
from database import (
    get_db_session, create_lobby_record, get_lobby_by_code, 
    update_lobby_record, delete_lobby_record
)

logger = logging.getLogger(__name__)

class LobbyManager:
    """Main lobby management coordinator."""
    
    def __init__(self):
        self.player_manager = PlayerManager()
        self.active_lobbies: Dict[str, LobbyData] = {}  # In-memory cache
        self.session_lobby_map: Dict[str, str] = {}  # session_id -> lobby_code
    
    def create_lobby(self, name: str, custom_code: Optional[str] = None, 
                    max_players: int = GAME_CONFIG['MAX_PLAYERS']) -> Tuple[bool, str, Optional[LobbyData]]:
        """
        Create a new lobby.
        
        Args:
            name: Name of the lobby
            custom_code: Optional custom lobby code
            max_players: Maximum number of players
            
        Returns:
            tuple: (success, message, lobby_data)
        """
        try:
            # Generate code if not provided
            lobby_code = custom_code or generate_lobby_code()
            
            # Check if code already exists
            if lobby_code in self.active_lobbies:
                return False, "Lobby code already exists", None
            
            # Check database as well
            with get_db_session() as session:
                existing_lobby = get_lobby_by_code(session, lobby_code)
                if existing_lobby:
                    return False, "Lobby code already exists", None
                
                # Create lobby record in database
                db_lobby = create_lobby_record(session, lobby_code, name, max_players)
                
                # Create lobby data object
                lobby_data = LobbyData(
                    code=lobby_code,
                    name=name,
                    created_at=db_lobby.created_at,
                    max_players=max_players
                )
                
                # Add to active lobbies cache
                self.active_lobbies[lobby_code] = lobby_data
                
                logger.info(f"Created lobby: {lobby_code}")
                return True, "Lobby created successfully", lobby_data
                
        except Exception as e:
            logger.error(f"Error creating lobby: {e}")
            return False, "Failed to create lobby", None
    
    def get_lobby(self, lobby_code: str) -> Optional[LobbyData]:
        """
        Get lobby data by code.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Lobby data or None if not found
        """
        try:
            # Check cache first
            if lobby_code in self.active_lobbies:
                return self.active_lobbies[lobby_code]
            
            # Load from database if not in cache
            with get_db_session() as session:
                db_lobby = get_lobby_by_code(session, lobby_code)
                if not db_lobby:
                    return None
                
                # Convert database lobby to lobby data
                lobby_data = LobbyData(
                    code=db_lobby.code,
                    name=db_lobby.name,
                    created_at=db_lobby.created_at,
                    max_players=db_lobby.max_players
                )
                
                # Load players from database
                from database_getters import get_active_players_in_lobby
                for db_player in get_active_players_in_lobby(db_lobby.id):
                    player_data = PlayerData(
                        session_id=db_player.session_id,
                        username=db_player.username,
                        is_ai=db_player.is_ai,
                        is_spectator=db_player.is_spectator,
                        is_connected=db_player.is_connected,
                        joined_at=db_player.joined_at
                    )
                    lobby_data.players.append(player_data)
                
                # Add to cache
                self.active_lobbies[lobby_code] = lobby_data
                
                return lobby_data
                
        except Exception as e:
            logger.error(f"Error getting lobby {lobby_code}: {e}")
            return None
    
    def join_lobby(self, lobby_code: str, session_id: str, username: str, 
                  is_spectator: bool = False) -> Tuple[bool, str, Optional[PlayerData]]:
        """
        Add a player to a lobby.
        
        Args:
            lobby_code: Code of the lobby to join
            session_id: Player's session ID
            username: Player's username
            is_spectator: Whether joining as spectator
            
        Returns:
            tuple: (success, message, player_data)
        """
        try:
            # Get lobby
            lobby_data = self.get_lobby(lobby_code)
            if not lobby_data:
                return False, "Lobby not found", None
            
            # Add player using player manager
            success, message, player_data = self.player_manager.add_player(
                lobby_data, session_id, username, is_spectator
            )
            
            if success and player_data:
                # Update session mapping
                self.session_lobby_map[session_id] = lobby_code
                
                # Persist to database
                self._sync_lobby_to_database(lobby_data)
                
            return success, message, player_data
            
        except Exception as e:
            logger.error(f"Error joining lobby: {e}")
            return False, "Failed to join lobby", None
    
    def leave_lobby(self, session_id: str) -> Tuple[bool, str, Optional[str]]:
        """
        Remove a player from their lobby.
        
        Args:
            session_id: Player's session ID
            
        Returns:
            tuple: (success, message, lobby_code)
        """
        try:
            # Find player's lobby
            lobby_code = self.session_lobby_map.get(session_id)
            if not lobby_code:
                return False, "Player not in any lobby", None
            
            lobby_data = self.get_lobby(lobby_code)
            if not lobby_data:
                return False, "Lobby not found", None
            
            # Remove player using player manager
            success, message, removed_username = self.player_manager.remove_player(
                lobby_data, session_id
            )
            
            if success:
                # Update session mapping
                if session_id in self.session_lobby_map:
                    del self.session_lobby_map[session_id]
                
                # Persist to database
                self._sync_lobby_to_database(lobby_data)
                
                # Clean up empty lobby
                if len(lobby_data.players) == 0:
                    self._cleanup_lobby(lobby_code)
                
            return success, message, lobby_code
            
        except Exception as e:
            logger.error(f"Error leaving lobby: {e}")
            return False, "Failed to leave lobby", None
    
    def disconnect_player(self, session_id: str) -> Tuple[bool, str, Optional[str]]:
        """
        Mark a player as disconnected.
        
        Args:
            session_id: Player's session ID
            
        Returns:
            tuple: (success, message, lobby_code)
        """
        try:
            # Find player's lobby
            lobby_code = self.session_lobby_map.get(session_id)
            if not lobby_code:
                return False, "Player not in any lobby", None
            
            lobby_data = self.get_lobby(lobby_code)
            if not lobby_data:
                return False, "Lobby not found", None
            
            # Disconnect player using player manager
            success, message, disconnected_username = self.player_manager.disconnect_player(
                lobby_data, session_id
            )
            
            if success:
                # Remove from session mapping but keep in lobby for potential reconnection
                if session_id in self.session_lobby_map:
                    del self.session_lobby_map[session_id]
                
                # Persist to database
                self._sync_lobby_to_database(lobby_data)
                
            return success, message, lobby_code
            
        except Exception as e:
            logger.error(f"Error disconnecting player: {e}")
            return False, "Failed to disconnect player", None
    
    def add_ai_player(self, lobby_code: str) -> Tuple[bool, str, Optional[PlayerData]]:
        """
        Add an AI player to a lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            tuple: (success, message, ai_player_data)
        """
        try:
            lobby_data = self.get_lobby(lobby_code)
            if not lobby_data:
                return False, "Lobby not found", None
            
            # Add AI player using player manager
            success, message, ai_player_data = self.player_manager.add_ai_player(lobby_data)
            
            if success and ai_player_data:
                # Persist to database
                self._sync_lobby_to_database(lobby_data)
                
            return success, message, ai_player_data
            
        except Exception as e:
            logger.error(f"Error adding AI player: {e}")
            return False, "Failed to add AI player", None
    
    def get_player_lobby(self, session_id: str) -> Optional[str]:
        """
        Get the lobby code for a player's session.
        
        Args:
            session_id: Player's session ID
            
        Returns:
            Lobby code or None
        """
        return self.session_lobby_map.get(session_id)
    
    def get_active_lobbies(self) -> List[LobbyListItem]:
        """
        Get list of all active lobbies.
        
        Returns:
            List of lobby info
        """
        lobby_list = []
        for lobby_data in self.active_lobbies.values():
            if lobby_data.is_active:
                lobby_list.append(LobbyListItem(
                    code=lobby_data.code,
                    name=lobby_data.name,
                    player_count=lobby_data.player_count,
                    max_players=lobby_data.max_players,
                    is_full=lobby_data.is_full,
                    created_at=lobby_data.created_at
                ))
        
        return lobby_list
    
    def cleanup_inactive_lobbies(self, hours_inactive: int = GAME_CONFIG['LOBBY_CLEANUP_HOURS']) -> int:
        """
        Clean up inactive lobbies.
        
        Args:
            hours_inactive: Hours of inactivity before cleanup
            
        Returns:
            Number of lobbies cleaned up
        """
        try:
            from datetime import timedelta
            
            cleaned_count = 0
            current_time = datetime.utcnow()
            cutoff_time = current_time - timedelta(hours=hours_inactive)
            
            # Find lobbies to clean up
            lobbies_to_cleanup = []
            for lobby_code, lobby_data in self.active_lobbies.items():
                # Clean up if old and empty, or very old
                if (lobby_data.created_at < cutoff_time and len(lobby_data.players) == 0) or \
                   (lobby_data.created_at < current_time - timedelta(hours=hours_inactive * 2)):
                    lobbies_to_cleanup.append(lobby_code)
            
            # Clean up lobbies
            for lobby_code in lobbies_to_cleanup:
                self._cleanup_lobby(lobby_code)
                cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} inactive lobbies")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during lobby cleanup: {e}")
            return 0
    
    def _sync_lobby_to_database(self, lobby_data: LobbyData):
        """
        Synchronize lobby data to database.
        
        Args:
            lobby_data: Lobby data to sync
        """
        try:
            with get_db_session() as session:
                # Update lobby record (players are managed separately in the database)
                update_lobby_record(session, lobby_data.code, {
                    'name': lobby_data.name,
                    'max_players': lobby_data.max_players,
                    'is_active': lobby_data.is_active
                })
                
        except Exception as e:
            logger.error(f"Error syncing lobby to database: {e}")
    
    def _cleanup_lobby(self, lobby_code: str):
        """
        Clean up a lobby completely.
        
        Args:
            lobby_code: Code of the lobby to clean up
        """
        try:
            # Remove from cache
            if lobby_code in self.active_lobbies:
                del self.active_lobbies[lobby_code]
            
            # Clean up session mappings
            sessions_to_remove = []
            for session_id, mapped_lobby_code in self.session_lobby_map.items():
                if mapped_lobby_code == lobby_code:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.session_lobby_map[session_id]
            
            # Remove from database
            with get_db_session() as session:
                delete_lobby_record(session, lobby_code)
            
            logger.info(f"Cleaned up lobby {lobby_code}")
            
        except Exception as e:
            logger.error(f"Error cleaning up lobby {lobby_code}: {e}")