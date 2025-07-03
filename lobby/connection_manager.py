"""
Connection Manager for The Outsider Lobbies.

Handles player connections, disconnections, and session tracking.
Contains no game logic - purely connection and session management.
"""

import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class PlayerSession:
    """Information about a player's session."""
    username: str
    socket_id: str
    lobby_code: Optional[str]
    connection_time: datetime
    last_activity: datetime
    is_connected: bool = True
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class ConnectionManager:
    """
    Manages player connections and sessions across lobbies.
    
    Handles connection tracking, disconnection detection, and session management.
    Contains no lobby or game logic - pure connection management.
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        """
        Initialize connection manager.
        
        Args:
            session_timeout_minutes: Minutes before inactive session expires
        """
        self.sessions: Dict[str, PlayerSession] = {}  # socket_id -> PlayerSession
        self.username_to_session: Dict[str, str] = {}  # username -> socket_id
        self.session_timeout_minutes = session_timeout_minutes
        logger.debug("Connection manager initialized")
    
    def register_connection(self, 
                          socket_id: str, 
                          username: str,
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None) -> Tuple[bool, str]:
        """
        Register a new player connection.
        
        Args:
            socket_id: Unique socket connection ID
            username: Player's username
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if username is already connected
            if username in self.username_to_session:
                existing_socket_id = self.username_to_session[username]
                if existing_socket_id in self.sessions and self.sessions[existing_socket_id].is_connected:
                    return False, f"Username {username} is already connected"
                else:
                    # Clean up stale session
                    self._cleanup_stale_session(username)
            
            # Create new session
            session = PlayerSession(
                username=username,
                socket_id=socket_id,
                lobby_code=None,
                connection_time=datetime.now(),
                last_activity=datetime.now(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.sessions[socket_id] = session
            self.username_to_session[username] = socket_id
            
            logger.info(f"Registered connection: {username} ({socket_id})")
            return True, f"Connected as {username}"
            
        except Exception as e:
            logger.error(f"Error registering connection: {e}")
            return False, "Failed to register connection"
    
    def unregister_connection(self, socket_id: str) -> Tuple[bool, str, Optional[str]]:
        """
        Unregister a player connection.
        
        Args:
            socket_id: Socket connection ID to unregister
            
        Returns:
            Tuple of (success, message, username)
        """
        try:
            if socket_id not in self.sessions:
                return False, "Connection not found", None
            
            session = self.sessions[socket_id]
            username = session.username
            lobby_code = session.lobby_code
            
            # Mark as disconnected
            session.is_connected = False
            
            # Clean up mappings
            if username in self.username_to_session:
                del self.username_to_session[username]
            
            del self.sessions[socket_id]
            
            logger.info(f"Unregistered connection: {username} ({socket_id})")
            return True, f"{username} disconnected", username
            
        except Exception as e:
            logger.error(f"Error unregistering connection: {e}")
            return False, "Failed to unregister connection", None
    
    def update_activity(self, socket_id: str) -> bool:
        """
        Update last activity time for a session.
        
        Args:
            socket_id: Socket connection ID
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            if socket_id in self.sessions:
                self.sessions[socket_id].last_activity = datetime.now()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating activity: {e}")
            return False
    
    def associate_with_lobby(self, socket_id: str, lobby_code: str) -> bool:
        """
        Associate a player session with a lobby.
        
        Args:
            socket_id: Socket connection ID
            lobby_code: Lobby code to associate with
            
        Returns:
            True if associated successfully, False otherwise
        """
        try:
            if socket_id in self.sessions:
                self.sessions[socket_id].lobby_code = lobby_code
                self.update_activity(socket_id)
                logger.debug(f"Associated {socket_id} with lobby {lobby_code}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error associating with lobby: {e}")
            return False
    
    def disassociate_from_lobby(self, socket_id: str) -> Optional[str]:
        """
        Disassociate a player session from its lobby.
        
        Args:
            socket_id: Socket connection ID
            
        Returns:
            Previous lobby code, or None if not associated
        """
        try:
            if socket_id in self.sessions:
                session = self.sessions[socket_id]
                previous_lobby = session.lobby_code
                session.lobby_code = None
                self.update_activity(socket_id)
                logger.debug(f"Disassociated {socket_id} from lobby {previous_lobby}")
                return previous_lobby
            return None
            
        except Exception as e:
            logger.error(f"Error disassociating from lobby: {e}")
            return None
    
    def get_session_by_socket(self, socket_id: str) -> Optional[PlayerSession]:
        """
        Get player session by socket ID.
        
        Args:
            socket_id: Socket connection ID
            
        Returns:
            PlayerSession or None if not found
        """
        return self.sessions.get(socket_id)
    
    def get_session_by_username(self, username: str) -> Optional[PlayerSession]:
        """
        Get player session by username.
        
        Args:
            username: Player username
            
        Returns:
            PlayerSession or None if not found
        """
        try:
            socket_id = self.username_to_session.get(username)
            if socket_id:
                return self.sessions.get(socket_id)
            return None
            
        except Exception as e:
            logger.error(f"Error getting session by username: {e}")
            return None
    
    def get_socket_id_by_username(self, username: str) -> Optional[str]:
        """
        Get socket ID by username.
        
        Args:
            username: Player username
            
        Returns:
            Socket ID or None if not found
        """
        return self.username_to_session.get(username)
    
    def get_username_by_socket(self, socket_id: str) -> Optional[str]:
        """
        Get username by socket ID.
        
        Args:
            socket_id: Socket connection ID
            
        Returns:
            Username or None if not found
        """
        session = self.sessions.get(socket_id)
        return session.username if session else None
    
    def get_lobby_by_socket(self, socket_id: str) -> Optional[str]:
        """
        Get lobby code by socket ID.
        
        Args:
            socket_id: Socket connection ID
            
        Returns:
            Lobby code or None if not in a lobby
        """
        session = self.sessions.get(socket_id)
        return session.lobby_code if session else None
    
    def get_connected_players_in_lobby(self, lobby_code: str) -> List[str]:
        """
        Get list of connected players in a specific lobby.
        
        Args:
            lobby_code: Lobby code
            
        Returns:
            List of usernames of connected players in the lobby
        """
        try:
            connected_players = []
            for session in self.sessions.values():
                if (session.is_connected and 
                    session.lobby_code == lobby_code):
                    connected_players.append(session.username)
            
            return connected_players
            
        except Exception as e:
            logger.error(f"Error getting connected players in lobby: {e}")
            return []
    
    def is_user_connected(self, username: str) -> bool:
        """
        Check if a user is currently connected.
        
        Args:
            username: Player username
            
        Returns:
            True if connected, False otherwise
        """
        try:
            session = self.get_session_by_username(username)
            return session is not None and session.is_connected
            
        except Exception as e:
            logger.error(f"Error checking user connection: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired inactive sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(minutes=self.session_timeout_minutes)
            expired_sessions = []
            
            for socket_id, session in self.sessions.items():
                if session.last_activity < cutoff_time:
                    expired_sessions.append(socket_id)
            
            cleaned_count = 0
            for socket_id in expired_sessions:
                success, _, _ = self.unregister_connection(socket_id)
                if success:
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired sessions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    def force_disconnect_user(self, username: str) -> bool:
        """
        Force disconnect a user (admin function).
        
        Args:
            username: Username to disconnect
            
        Returns:
            True if disconnected successfully, False otherwise
        """
        try:
            session = self.get_session_by_username(username)
            if session:
                success, _, _ = self.unregister_connection(session.socket_id)
                logger.info(f"Force disconnected user: {username}")
                return success
            return False
            
        except Exception as e:
            logger.error(f"Error force disconnecting user: {e}")
            return False
    
    def _cleanup_stale_session(self, username: str) -> None:
        """Clean up a stale session for a username."""
        try:
            if username in self.username_to_session:
                socket_id = self.username_to_session[username]
                if socket_id in self.sessions:
                    del self.sessions[socket_id]
                del self.username_to_session[username]
                logger.debug(f"Cleaned up stale session for {username}")
                
        except Exception as e:
            logger.error(f"Error cleaning up stale session: {e}")
    
    def get_connection_stats(self) -> Dict[str, any]:
        """
        Get connection statistics.
        
        Returns:
            Dictionary with connection statistics
        """
        try:
            total_sessions = len(self.sessions)
            connected_sessions = sum(1 for s in self.sessions.values() if s.is_connected)
            
            # Group by lobby
            lobby_counts = {}
            for session in self.sessions.values():
                if session.is_connected and session.lobby_code:
                    lobby_counts[session.lobby_code] = lobby_counts.get(session.lobby_code, 0) + 1
            
            return {
                'total_sessions': total_sessions,
                'connected_sessions': connected_sessions,
                'disconnected_sessions': total_sessions - connected_sessions,
                'players_in_lobbies': sum(lobby_counts.values()),
                'active_lobbies': len(lobby_counts),
                'lobby_distribution': lobby_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting connection stats: {e}")
            return {}
    
    def get_session_info(self, socket_id: str) -> Dict[str, any]:
        """
        Get detailed session information.
        
        Args:
            socket_id: Socket connection ID
            
        Returns:
            Session information dictionary
        """
        try:
            session = self.sessions.get(socket_id)
            if not session:
                return {}
            
            return {
                'username': session.username,
                'socket_id': session.socket_id,
                'lobby_code': session.lobby_code,
                'connection_time': session.connection_time.isoformat(),
                'last_activity': session.last_activity.isoformat(),
                'is_connected': session.is_connected,
                'session_duration_minutes': (datetime.now() - session.connection_time).total_seconds() / 60
            }
            
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return {}
    
    def get_status(self) -> Dict[str, any]:
        """
        Get current status of the connection manager.
        
        Returns:
            Status information dictionary
        """
        stats = self.get_connection_stats()
        return {
            'session_timeout_minutes': self.session_timeout_minutes,
            'manager_initialized': True,
            **stats
        }