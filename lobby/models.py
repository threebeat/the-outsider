"""
Data models for lobby management.

These are pure data structures used to pass information between
lobby management, game systems, and handlers.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class PlayerData:
    """Represents a player in a lobby."""
    session_id: str
    username: str
    is_ai: bool = False
    is_spectator: bool = False
    is_connected: bool = True
    joined_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'session_id': self.session_id,
            'username': self.username,
            'is_ai': self.is_ai,
            'is_spectator': self.is_spectator,
            'is_connected': self.is_connected,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None
        }

@dataclass 
class LobbyData:
    """Represents a lobby's current state."""
    code: str
    name: str
    created_at: datetime
    max_players: int = 8
    players: List[PlayerData] = field(default_factory=list)
    is_active: bool = True
    
    @property
    def player_count(self) -> int:
        """Total number of active players."""
        return len([p for p in self.players if not p.is_spectator])
    
    @property
    def human_count(self) -> int:
        """Number of human players."""
        return len([p for p in self.players if not p.is_ai and not p.is_spectator])
    
    @property
    def ai_count(self) -> int:
        """Number of AI players."""
        return len([p for p in self.players if p.is_ai and not p.is_spectator])
    
    @property
    def spectator_count(self) -> int:
        """Number of spectators."""
        return len([p for p in self.players if p.is_spectator])
    
    @property
    def is_full(self) -> bool:
        """Check if lobby is at max capacity."""
        return self.player_count >= self.max_players
    
    def get_player_by_session(self, session_id: str) -> Optional[PlayerData]:
        """Find player by session ID."""
        for player in self.players:
            if player.session_id == session_id:
                return player
        return None
    
    def get_player_by_username(self, username: str) -> Optional[PlayerData]:
        """Find player by username."""
        for player in self.players:
            if player.username == username:
                return player
        return None
    
    def get_human_players(self) -> List[PlayerData]:
        """Get all human players."""
        return [p for p in self.players if not p.is_ai and not p.is_spectator]
    
    def get_ai_players(self) -> List[PlayerData]:
        """Get all AI players."""
        return [p for p in self.players if p.is_ai and not p.is_spectator]
    
    def get_active_players(self) -> List[PlayerData]:
        """Get all active (non-spectator) players."""
        return [p for p in self.players if not p.is_spectator]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'code': self.code,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'max_players': self.max_players,
            'player_count': self.player_count,
            'human_count': self.human_count,
            'ai_count': self.ai_count,
            'spectator_count': self.spectator_count,
            'is_full': self.is_full,
            'is_active': self.is_active,
            'players': [p.to_dict() for p in self.players]
        }

@dataclass
class LobbyListItem:
    """Lightweight lobby info for listing active lobbies."""
    code: str
    name: str
    player_count: int
    max_players: int
    is_full: bool
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'code': self.code,
            'name': self.name,
            'player_count': self.player_count,
            'max_players': self.max_players,
            'is_full': self.is_full,
            'created_at': self.created_at.isoformat()
        }