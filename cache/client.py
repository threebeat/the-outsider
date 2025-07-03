"""
Redis Client Configuration for The Outsider Game.

Manages Redis connection with proper error handling and fallbacks.
"""

import os
import json
import logging
from typing import Any, Optional, Dict, List
import redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client wrapper with error handling and fallbacks."""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Establish Redis connection."""
        try:
            # Get Redis configuration from environment or use defaults
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_db = int(os.getenv('REDIS_DB', 0))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            
            # Try URL first (for production), then individual params
            if redis_url and redis_url != 'redis://localhost:6379':
                self.client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
            else:
                self.client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
            
            # Test connection
            self.client.ping()
            self.connected = True
            logger.info("Redis connection established successfully")
            
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Redis connection failed: {e}. Using fallback mode.")
            self.connected = False
            self.client = None
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            self.connected = False
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected and available."""
        if not self.connected or not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except (ConnectionError, TimeoutError, RedisError):
            self.connected = False
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with fallback."""
        if not self.is_connected():
            logger.debug(f"Redis unavailable, returning None for key: {key}")
            return None
        
        try:
            value = self.client.get(key)
            if value and value.startswith(('{', '[')):
                return json.loads(value)
            return value
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Redis get failed for key {key}: {e}")
            return None
        except json.JSONDecodeError:
            return value
        except Exception as e:
            logger.error(f"Unexpected error getting key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, expiry: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiry."""
        if not self.is_connected():
            logger.debug(f"Redis unavailable, cannot set key: {key}")
            return False
        
        try:
            # Serialize complex objects as JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if expiry:
                return bool(self.client.setex(key, expiry, value))
            else:
                return bool(self.client.set(key, value))
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Redis set failed for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.is_connected():
            return False
        
        try:
            return bool(self.client.delete(key))
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Redis delete failed for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.is_connected():
            return False
        
        try:
            return bool(self.client.exists(key))
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Redis exists check failed for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking key {key}: {e}")
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern."""
        if not self.is_connected():
            return []
        
        try:
            return self.client.keys(pattern)
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Redis keys failed for pattern {pattern}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting keys {pattern}: {e}")
            return []
    
    def flushdb(self) -> bool:
        """Clear all keys in current database."""
        if not self.is_connected():
            return False
        
        try:
            self.client.flushdb()
            return True
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"Redis flushdb failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in flushdb: {e}")
            return False

# Global Redis client instance
redis_client = RedisClient()