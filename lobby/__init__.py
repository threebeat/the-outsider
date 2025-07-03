"""
Lobby Module for The Outsider.

Contains all lobby management logic and components.
Handles lobby creation, player management, and connection tracking.
"""

from .models import LobbyData, PlayerData, LobbyListItem
from .manager import LobbyManager
from .player_manager import PlayerManager
from .connection_manager import ConnectionManager, PlayerSession
from .lobby_creator import LobbyCreator, LobbyConfiguration

__all__ = [
    # Data models
    'LobbyData',
    'PlayerData',
    'LobbyListItem',
    'PlayerSession', 
    'LobbyConfiguration',
    
    # Managers
    'LobbyManager',
    'PlayerManager',
    'ConnectionManager',
    'LobbyCreator'
]