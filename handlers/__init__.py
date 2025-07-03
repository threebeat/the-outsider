"""
Event Handlers for The Outsider.

Contains all Socket.IO event handlers and API route handlers,
keeping the main app.py minimal and focused on server setup.
"""

from .socket_handlers import register_socket_handlers
from .api_handlers import register_api_handlers

__all__ = [
    'register_socket_handlers',
    'register_api_handlers'
]