"""
Main lobby management system.

Handles lobby creation, lifecycle, and coordinates between
player management and cache persistence.
Uses Redis cache only, never touches database.
"""

import logging
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from .models import LobbyData, PlayerData, LobbyListItem
from .player_manager import PlayerManager
from utils.constants import GAME_CONFIG

# Import cache operations only
from cache import (
    create_lobby, get_lobby_by_code, delete_lobby, lobby_exists,
    get_players_in_lobby, LobbyCache, PlayerCache
)

logger = logging.getLogger(__name__)

class LobbyManager:
    """
    Main lobby management coordinator.
    Uses Redis cache only.
    """
    
    def __init__(self):
        self.player_manager = PlayerManager()
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
            lobby_code = custom_code or self._generate_lobby_code()
            
            # Check if code already exists in cache
            if lobby_exists(lobby_code):
                return False, "Lobby code already exists", None
            
            # Create lobby in cache
            success = create_lobby(lobby_code, name)
            
            if success:
                # Create lobby data object
                lobby_data = LobbyData(
                    code=lobby_code,
                    name=name,
                    created_at=datetime.now(),
                    max_players=max_players
                )
                
                logger.info(f"Created lobby: {lobby_code}")
                return True, "Lobby created successfully", lobby_data
            else:
                return False, "Failed to create lobby in cache", None
                
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
            # Get from cache
            lobby_cache = get_lobby_by_code(lobby_code)
            if not lobby_cache:
                return None
            
            # Convert cache lobby to lobby data
            lobby_data = LobbyData(
                code=lobby_cache.code,
                name=lobby_cache.name,
                created_at=datetime.fromisoformat(lobby_cache.created_at) if lobby_cache.created_at else datetime.now(),
                max_players=GAME_CONFIG['MAX_PLAYERS']  # Use default for now
            )
            
            # Load players from cache
            for cache_player in lobby_cache.players:
                player_data = PlayerData(
                    session_id=cache_player.session_id,
                    username=cache_player.username,
                    is_ai=cache_player.is_ai,
                    is_spectator=cache_player.is_spectator,
                    is_connected=cache_player.is_connected,
                    joined_at=datetime.now()  # Cache doesn't store join time
                )
                lobby_data.players.append(player_data)
            
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
                
                # Create player cache object and add to lobby
                player_cache = PlayerCache(
                    session_id=player_data.session_id,
                    username=player_data.username,
                    is_ai=player_data.is_ai,
                    is_spectator=player_data.is_spectator,
                    is_connected=player_data.is_connected
                )
                
                # Import cache setter to add player
                from cache import add_player_to_lobby
                add_player_to_lobby(lobby_code, player_cache)
                
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
                # Try to find in cache directly
                from cache import find_player_lobby
                lobby_code = find_player_lobby(session_id)
                
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
                
                # Remove from cache
                from cache import remove_player_from_lobby
                remove_player_from_lobby(lobby_code, session_id)
                
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
                # Try to find in cache directly
                from cache import find_player_lobby
                lobby_code = find_player_lobby(session_id)
                
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
                
                # Update connection status in cache
                from cache import update_player_connection
                update_player_connection(lobby_code, session_id, False)
                
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
                # Create AI player cache object and add to lobby
                ai_player_cache = PlayerCache(
                    session_id=ai_player_data.session_id,
                    username=ai_player_data.username,
                    is_ai=True,
                    is_spectator=False,
                    is_connected=True,
                    ai_personality=getattr(ai_player_data, 'ai_personality', None)
                )
                
                # Add to cache
                from cache import add_player_to_lobby
                add_player_to_lobby(lobby_code, ai_player_cache)
                
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
        # Check local mapping first
        lobby_code = self.session_lobby_map.get(session_id)
        
        if not lobby_code:
            # Try to find in cache
            from cache import find_player_lobby
            lobby_code = find_player_lobby(session_id)
            
            # Update local mapping if found
            if lobby_code:
                self.session_lobby_map[session_id] = lobby_code
        
        return lobby_code
    
    def get_active_lobbies(self) -> List[LobbyListItem]:
        """
        Get list of all active lobbies.
        
        Returns:
            List of lobby info
        """
        try:
            from cache import get_all_active_lobbies
            
            lobby_list = []
            active_lobbies = get_all_active_lobbies()
            
            for lobby_cache in active_lobbies:
                lobby_list.append(LobbyListItem(
                    code=lobby_cache.code,
                    name=lobby_cache.name,
                    player_count=len(lobby_cache.get_connected_players()),
                    max_players=GAME_CONFIG['MAX_PLAYERS'],
                    is_full=len(lobby_cache.get_connected_players()) >= GAME_CONFIG['MAX_PLAYERS'],
                    created_at=datetime.fromisoformat(lobby_cache.created_at) if lobby_cache.created_at else datetime.now()
                ))
            
            return lobby_list
            
        except Exception as e:
            logger.error(f"Error getting active lobbies: {e}")
            return []
    
    def cleanup_inactive_lobbies(self, hours_inactive: int = GAME_CONFIG['LOBBY_CLEANUP_HOURS']) -> int:
        """
        Clean up inactive lobbies.
        
        Args:
            hours_inactive: Hours of inactivity before cleanup
            
        Returns:
            Number of lobbies cleaned up
        """
        try:
            from cache import cleanup_expired_data
            
            # Use cache cleanup function
            result = cleanup_expired_data()
            cleaned_count = result.get('cleaned', 0)
            
            logger.info(f"Cleaned up {cleaned_count} inactive lobbies")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during lobby cleanup: {e}")
            return 0
    
    def _generate_lobby_code(self, length: int = 6) -> str:
        """Generate a random lobby code."""
        import random
        import string
        
        # Use mix of letters and numbers for better readability
        # Exclude easily confused characters: 0, O, I, 1
        chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        return ''.join(random.choices(chars, k=length))
    
    def _cleanup_lobby(self, lobby_code: str):
        """
        Clean up a lobby completely.
        
        Args:
            lobby_code: Code of the lobby to clean up
        """
        try:
            # Clean up session mappings
            sessions_to_remove = []
            for session_id, mapped_lobby_code in self.session_lobby_map.items():
                if mapped_lobby_code == lobby_code:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.session_lobby_map[session_id]
            
            # Remove from cache (includes all related data)
            from cache import cleanup_lobby_data
            cleanup_lobby_data(lobby_code)
            
            logger.info(f"Cleaned up lobby {lobby_code}")
            
        except Exception as e:
            logger.error(f"Error cleaning up lobby {lobby_code}: {e}")