"""
Lobby management for The Outsider.

This module handles lobby creation, player management, and lobby state transitions.
"""

import logging
from typing import Optional, List, Dict
from database import (
    get_db_session, create_lobby, get_lobby_by_code, add_player_to_lobby,
    remove_player_from_lobby, disconnect_player, reset_lobby
)
from utils.constants import GAME_STATES, GAME_CONFIG
from utils.helpers import generate_lobby_code, validate_username, get_available_ai_name

logger = logging.getLogger(__name__)

class LobbyManager:
    """Manages lobby operations and player management."""
    
    def __init__(self):
        self.active_lobbies: Dict[str, dict] = {}  # In-memory lobby cache
        
    def create_lobby(self, lobby_name: str, lobby_code: Optional[str] = None, 
                    max_players: int = GAME_CONFIG['MAX_PLAYERS']) -> tuple[bool, str, Optional[dict]]:
        """
        Create a new game lobby.
        
        Args:
            lobby_name: Name of the lobby
            lobby_code: Optional custom lobby code
            max_players: Maximum number of players
            
        Returns:
            tuple: (success, message, lobby_data)
        """
        try:
            # Generate code if not provided
            if not lobby_code:
                lobby_code = generate_lobby_code()
            
            with get_db_session() as session:
                # Check if lobby code already exists
                existing_lobby = get_lobby_by_code(session, lobby_code)
                if existing_lobby:
                    return False, "Lobby code already exists", None
                
                # Create lobby in database
                lobby = create_lobby(session, lobby_code, lobby_name, max_players)
                
                # Add to active lobbies cache
                lobby_data = {
                    'id': lobby.id,
                    'code': lobby.code,
                    'name': lobby.name,
                    'state': lobby.state,
                    'max_players': lobby.max_players,
                    'created_at': lobby.created_at,
                    'players': []
                }
                self.active_lobbies[lobby_code] = lobby_data
                
                logger.info(f"Created lobby: {lobby_code}")
                return True, "Lobby created successfully", lobby_data
                
        except Exception as e:
            logger.error(f"Error creating lobby: {e}")
            return False, "Failed to create lobby", None
    
    def join_lobby(self, lobby_code: str, session_id: str, username: str, 
                  is_spectator: bool = False) -> tuple[bool, str, Optional[dict]]:
        """
        Add a player to a lobby.
        
        Args:
            lobby_code: Code of the lobby to join
            session_id: Player's session ID
            username: Player's username
            is_spectator: Whether player is joining as spectator
            
        Returns:
            tuple: (success, message, player_data)
        """
        try:
            # Validate username
            is_valid, error_msg = validate_username(username)
            if not is_valid:
                return False, error_msg, None
            
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return False, "Lobby not found", None
                
                # Check if lobby is full
                if len(lobby.active_players) >= lobby.max_players and not is_spectator:
                    return False, f"Lobby is full ({lobby.max_players} players max)", None
                
                # Check if game is in progress and joining as spectator
                if lobby.state == GAME_STATES['PLAYING'] and not is_spectator:
                    return False, "Game in progress. You can join as a spectator.", None
                
                # Add player to lobby
                player = add_player_to_lobby(session, lobby, session_id, username, 
                                           is_spectator=is_spectator)
                
                # Update lobby cache
                if lobby_code in self.active_lobbies:
                    self.active_lobbies[lobby_code]['players'] = [
                        {
                            'id': p.id,
                            'username': p.username,
                            'is_ai': p.is_ai,
                            'is_spectator': p.is_spectator,
                            'is_connected': p.is_connected
                        }
                        for p in lobby.active_players
                    ]
                
                player_data = {
                    'id': player.id,
                    'username': player.username,
                    'is_ai': player.is_ai,
                    'is_spectator': player.is_spectator,
                    'session_id': player.session_id
                }
                
                logger.info(f"Player {username} joined lobby {lobby_code}")
                return True, "Joined lobby successfully", player_data
                
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Error joining lobby: {e}")
            return False, "Failed to join lobby", None
    
    def leave_lobby(self, session_id: str) -> tuple[bool, str, Optional[str]]:
        """
        Remove a player from their lobby.
        
        Args:
            session_id: Player's session ID
            
        Returns:
            tuple: (success, message, lobby_code)
        """
        try:
            lobby_code = None
            
            with get_db_session() as session:
                # Find player's lobby
                for code, lobby_data in self.active_lobbies.items():
                    lobby = get_lobby_by_code(session, code)
                    if lobby:
                        for player in lobby.players:
                            if player.session_id == session_id:
                                lobby_code = code
                                
                                # Remove player
                                remove_player_from_lobby(session, player)
                                
                                # Update cache
                                self.active_lobbies[code]['players'] = [
                                    {
                                        'id': p.id,
                                        'username': p.username,
                                        'is_ai': p.is_ai,
                                        'is_spectator': p.is_spectator,
                                        'is_connected': p.is_connected
                                    }
                                    for p in lobby.active_players
                                ]
                                
                                logger.info(f"Player {player.username} left lobby {code}")
                                return True, "Left lobby successfully", lobby_code
                
                return False, "Player not found in any lobby", None
                
        except Exception as e:
            logger.error(f"Error leaving lobby: {e}")
            return False, "Failed to leave lobby", None
    
    def disconnect_player(self, session_id: str) -> tuple[bool, str, Optional[str]]:
        """
        Mark a player as disconnected without removing them.
        
        Args:
            session_id: Player's session ID
            
        Returns:
            tuple: (success, message, lobby_code)
        """
        try:
            lobby_code = None
            
            with get_db_session() as session:
                # Find player's lobby
                for code, lobby_data in self.active_lobbies.items():
                    lobby = get_lobby_by_code(session, code)
                    if lobby:
                        for player in lobby.players:
                            if player.session_id == session_id:
                                lobby_code = code
                                
                                # Disconnect player
                                disconnect_player(session, player)
                                
                                logger.info(f"Player {player.username} disconnected from lobby {code}")
                                return True, "Player disconnected", lobby_code
                
                return False, "Player not found", None
                
        except Exception as e:
            logger.error(f"Error disconnecting player: {e}")
            return False, "Failed to disconnect player", None
    
    def add_ai_player(self, lobby_code: str) -> tuple[bool, str, Optional[dict]]:
        """
        Add an AI player to a lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            tuple: (success, message, ai_player_data)
        """
        try:
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return False, "Lobby not found", None
                
                # Get existing player names
                existing_names = [p.username for p in lobby.active_players]
                
                # Get available AI name
                ai_name = get_available_ai_name(existing_names)
                if not ai_name:
                    return False, "No AI names available", None
                
                # Generate unique session ID for AI
                ai_session_id = f"ai_{lobby_code}_{len(lobby.ai_players) + 1}"
                
                # Add AI player
                ai_player = add_player_to_lobby(session, lobby, ai_session_id, ai_name, is_ai=True)
                
                # Update cache
                if lobby_code in self.active_lobbies:
                    self.active_lobbies[lobby_code]['players'] = [
                        {
                            'id': p.id,
                            'username': p.username,
                            'is_ai': p.is_ai,
                            'is_spectator': p.is_spectator,
                            'is_connected': p.is_connected
                        }
                        for p in lobby.active_players
                    ]
                
                ai_data = {
                    'id': ai_player.id,
                    'username': ai_player.username,
                    'is_ai': True,
                    'session_id': ai_player.session_id
                }
                
                logger.info(f"Added AI player {ai_name} to lobby {lobby_code}")
                return True, "AI player added", ai_data
                
        except Exception as e:
            logger.error(f"Error adding AI player: {e}")
            return False, "Failed to add AI player", None
    
    def get_lobby_data(self, lobby_code: str) -> Optional[dict]:
        """
        Get current lobby data.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Lobby data dictionary or None
        """
        try:
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return None
                
                players_data = []
                for player in lobby.active_players:
                    players_data.append({
                        'id': player.id,
                        'username': player.username,
                        'is_ai': player.is_ai,
                        'is_spectator': player.is_spectator,
                        'is_connected': player.is_connected,
                        'is_outsider': player.is_outsider,
                        'questions_asked': player.questions_asked,
                        'questions_answered': player.questions_answered
                    })
                
                return {
                    'code': lobby.code,
                    'name': lobby.name,
                    'state': lobby.state,
                    'location': lobby.location,
                    'current_turn': lobby.current_turn,
                    'question_count': lobby.question_count,
                    'max_questions': lobby.max_questions,
                    'max_players': lobby.max_players,
                    'players': players_data,
                    'total_players': len(players_data),
                    'human_players': len([p for p in players_data if not p['is_ai']]),
                    'ai_players': len([p for p in players_data if p['is_ai']])
                }
                
        except Exception as e:
            logger.error(f"Error getting lobby data: {e}")
            return None
    
    def reset_lobby(self, lobby_code: str) -> bool:
        """
        Reset a lobby to waiting state.
        
        Args:
            lobby_code: Code of the lobby to reset
            
        Returns:
            Success status
        """
        try:
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return False
                
                reset_lobby(session, lobby)
                logger.info(f"Reset lobby {lobby_code}")
                return True
                
        except Exception as e:
            logger.error(f"Error resetting lobby: {e}")
            return False
    
    def cleanup_inactive_lobbies(self, hours_inactive: int = GAME_CONFIG['LOBBY_CLEANUP_HOURS']) -> int:
        """
        Clean up inactive lobbies.
        
        Args:
            hours_inactive: Hours of inactivity before cleanup
            
        Returns:
            Number of lobbies cleaned up
        """
        try:
            from database import cleanup_inactive_lobbies
            
            with get_db_session() as session:
                cleaned_count = cleanup_inactive_lobbies(session, hours_inactive)
                
                # Also clean up memory cache
                inactive_codes = []
                for code in self.active_lobbies.keys():
                    lobby_data = self.get_lobby_data(code)
                    if not lobby_data:
                        inactive_codes.append(code)
                
                for code in inactive_codes:
                    del self.active_lobbies[code]
                
                logger.info(f"Cleaned up {cleaned_count} inactive lobbies")
                return cleaned_count
                
        except Exception as e:
            logger.error(f"Error during lobby cleanup: {e}")
            return 0
    
    def get_active_lobbies(self) -> List[dict]:
        """
        Get list of all active lobbies.
        
        Returns:
            List of lobby info dictionaries
        """
        lobbies_info = []
        for code in self.active_lobbies.keys():
            lobby_data = self.get_lobby_data(code)
            if lobby_data:
                lobbies_info.append({
                    'code': lobby_data['code'],
                    'name': lobby_data['name'],
                    'state': lobby_data['state'],
                    'players': lobby_data['total_players'],
                    'max_players': lobby_data['max_players']
                })
        
        return lobbies_info