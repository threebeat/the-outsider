"""
Redis Cache Models for The Outsider Game.

Data structures for temporary lobby and game information stored in Redis.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
import json

@dataclass
class PlayerCache:
    """Cached player information."""
    session_id: str
    username: str
    is_ai: bool = False
    is_spectator: bool = False
    is_connected: bool = True
    questions_asked: int = 0
    questions_answered: int = 0
    votes_received: int = 0
    ai_personality: Optional[str] = None
    ai_strategy: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlayerCache':
        """Create PlayerCache from dictionary."""
        return cls(**data)

@dataclass
class LobbyCache:
    """Cached lobby information."""
    code: str
    name: str
    state: str = 'open'  # open, active
    location: Optional[str] = None
    created_at: Optional[str] = None
    players: List[PlayerCache] = field(default_factory=list)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        data = asdict(self)
        # Convert PlayerCache objects to dicts
        data['players'] = [player.to_dict() if isinstance(player, PlayerCache) else player for player in self.players]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LobbyCache':
        """Create LobbyCache from dictionary."""
        # Convert player dicts back to PlayerCache objects
        if 'players' in data and data['players']:
            data['players'] = [
                PlayerCache.from_dict(player) if isinstance(player, dict) else player 
                for player in data['players']
            ]
        return cls(**data)
    
    def add_player(self, player: PlayerCache) -> None:
        """Add player to lobby."""
        if player not in self.players:
            self.players.append(player)
    
    def remove_player(self, session_id: str) -> bool:
        """Remove player by session_id."""
        initial_count = len(self.players)
        self.players = [p for p in self.players if p.session_id != session_id]
        return len(self.players) < initial_count
    
    def get_player(self, session_id: str) -> Optional[PlayerCache]:
        """Get player by session_id."""
        for player in self.players:
            if player.session_id == session_id:
                return player
        return None
    
    def get_human_players(self) -> List[PlayerCache]:
        """Get all human players."""
        return [p for p in self.players if not p.is_ai]
    
    def get_ai_players(self) -> List[PlayerCache]:
        """Get all AI players."""
        return [p for p in self.players if p.is_ai]
    
    def get_connected_players(self) -> List[PlayerCache]:
        """Get all connected players."""
        return [p for p in self.players if p.is_connected]

@dataclass
class GameCache:
    """Cached game session information."""
    lobby_code: str
    session_number: int
    location: str
    total_players: int
    human_players: int
    ai_players: int
    state: str = 'active'  # active, voting, ended
    winner: Optional[str] = None  # 'humans', 'ai', 'draw'
    winner_reason: Optional[str] = None
    ai_eliminated: Optional[bool] = None
    ai_guessed_correctly: Optional[bool] = None
    ai_final_guess: Optional[str] = None
    total_questions: int = 0
    total_votes: int = 0
    duration_seconds: Optional[int] = None
    ai_performance_score: Optional[float] = None
    human_suspicion_level: Optional[float] = None
    started_at: Optional[str] = None
    eliminated_player_session_id: Optional[str] = None
    current_turn_player: Optional[str] = None
    turn_count: int = 0
    voting_phase: bool = False
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameCache':
        """Create GameCache from dictionary."""
        return cls(**data)

@dataclass
class MessageCache:
    """Cached game message."""
    content: str
    message_type: str = 'chat'  # chat, question, answer, system, ai_thinking
    lobby_code: str = ''
    sender_session_id: Optional[str] = None
    target_session_id: Optional[str] = None
    is_question: bool = False
    question_number: Optional[int] = None
    confidence_score: Optional[float] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageCache':
        """Create MessageCache from dictionary."""
        return cls(**data)

@dataclass
class VoteCache:
    """Cached vote information."""
    lobby_code: str
    voter_session_id: str
    target_session_id: str
    vote_round: int = 1
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoteCache':
        """Create VoteCache from dictionary."""
        return cls(**data)

# Redis key patterns for organized storage
class RedisKeys:
    """Redis key patterns for consistent data organization."""
    
    # Lobby data
    LOBBY = "lobby:{code}"
    LOBBIES_ACTIVE = "lobbies:active"
    
    # Game data
    GAME = "game:{lobby_code}"
    GAMES_ACTIVE = "games:active"
    
    # Messages (with TTL)
    MESSAGES = "messages:{lobby_code}"
    
    # Votes (with TTL)
    VOTES = "votes:{lobby_code}:{round}"
    
    # Player session mapping
    PLAYER_SESSION = "player:session:{session_id}"
    LOBBY_PLAYERS = "lobby:players:{code}"
    
    @staticmethod
    def lobby_key(code: str) -> str:
        return RedisKeys.LOBBY.format(code=code)
    
    @staticmethod
    def game_key(lobby_code: str) -> str:
        return RedisKeys.GAME.format(lobby_code=lobby_code)
    
    @staticmethod
    def messages_key(lobby_code: str) -> str:
        return RedisKeys.MESSAGES.format(lobby_code=lobby_code)
    
    @staticmethod
    def votes_key(lobby_code: str, round_num: int) -> str:
        return RedisKeys.VOTES.format(lobby_code=lobby_code, round=round_num)
    
    @staticmethod
    def player_session_key(session_id: str) -> str:
        return RedisKeys.PLAYER_SESSION.format(session_id=session_id)
    
    @staticmethod
    def lobby_players_key(code: str) -> str:
        return RedisKeys.LOBBY_PLAYERS.format(code=code)

# Default TTL values (in seconds)
class CacheTTL:
    """Default TTL values for different types of cached data."""
    
    LOBBY_ACTIVE = 3600 * 6      # 6 hours
    LOBBY_ENDED = 3600 * 24      # 24 hours  
    GAME_ACTIVE = 3600 * 3       # 3 hours
    GAME_ENDED = 3600 * 24       # 24 hours
    MESSAGES = 3600 * 24         # 24 hours
    VOTES = 3600 * 24            # 24 hours
    PLAYER_SESSION = 3600 * 12   # 12 hours