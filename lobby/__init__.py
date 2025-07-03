"""
Lobby Management System for The Outsider.

Handles lobby creation, player management, and lobby state.
Lobbies are containers where players gather before and during games.
"""

from .manager import LobbyManager
from .player_manager import PlayerManager  
from .models import LobbyData, PlayerData

__all__ = [
    'LobbyManager',
    'PlayerManager',
    'LobbyData', 
    'PlayerData'
]