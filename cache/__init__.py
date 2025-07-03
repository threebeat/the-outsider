"""
Redis Cache Module for The Outsider Game.

Handles temporary game and lobby data using Redis for fast operations.
"""

from .client import redis_client
from .models import LobbyCache, GameCache, PlayerCache
from .getters import *
from .setters import *

__all__ = [
    'redis_client',
    'LobbyCache', 
    'GameCache',
    'PlayerCache'
]