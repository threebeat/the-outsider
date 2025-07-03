"""
Handlers Module for The Outsider.

Contains all web layer handlers (Socket.IO and API) with no business logic.
Handlers coordinate between web layer and business logic modules.
"""

from .socket_handlers import register_socket_handlers
from .api_handlers import register_api_handlers

__all__ = [
    'register_socket_handlers',
    'register_api_handlers'
]