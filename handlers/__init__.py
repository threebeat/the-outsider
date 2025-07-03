"""
Event handlers module for The Outsider.

This module contains Socket.IO event handlers and REST API route handlers
for the Flask-SocketIO backend.
"""

from .socket_events import register_socket_handlers
from .api_routes import register_api_routes

__all__ = [
    'register_socket_handlers',
    'register_api_routes'
]