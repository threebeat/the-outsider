"""
OpenAI API Client for The Outsider.

Handles OpenAI API connections, error handling, retries, and rate limiting.
Contains no game logic - purely API interaction utilities.
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Import OpenAI (will need to be installed)
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not installed. AI features will be disabled.")

class AIError(Exception):
    """Base exception for AI-related errors."""
    pass

class RateLimitError(AIError):
    """Raised when OpenAI rate limit is exceeded."""
    pass

class APIKeyError(AIError):
    """Raised when OpenAI API key is invalid or missing."""
    pass

class ContentFilterError(AIError):
    """Raised when content is filtered by OpenAI."""
    pass

class TokenLimitError(AIError):
    """Raised when token limit is exceeded."""
    pass

@dataclass
class AIResponse:
    """Response from OpenAI API."""
    content: str
    tokens_used: int
    model_used: str
    success: bool = True
    error_message: Optional[str] = None

class OpenAIClient:
    """
    OpenAI API client with error handling and retry logic.
    
    Handles all OpenAI API interactions with proper error handling,
    rate limiting, and retry logic. Contains no game logic.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to environment variable)
            model: OpenAI model to use
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.client = None
        self.max_retries = 3
        self.base_delay = 1.0  # seconds
        
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI library not available")
            return
            
        if not self.api_key:
            logger.error("OpenAI API key not provided")
            return
            
        try:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
    
    def is_available(self) -> bool:
        """Check if OpenAI client is available and configured."""
        return OPENAI_AVAILABLE and self.client is not None and self.api_key is not None
    
    def generate_completion(self, messages: List[Dict[str, str]], 
                          max_tokens: int = 150, 
                          temperature: float = 0.7) -> AIResponse:
        """
        Generate a completion from OpenAI API with error handling.
        
        Args:
            messages: List of message dictionaries for the conversation
            max_tokens: Maximum tokens to generate
            temperature: Temperature for randomness (0.0 to 1.0)
            
        Returns:
            AIResponse with content and metadata
        """
        if not self.is_available():
            return AIResponse(
                content="AI service unavailable",
                tokens_used=0,
                model_used=self.model,
                success=False,
                error_message="OpenAI client not available"
            )
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"OpenAI API attempt {attempt + 1}/{self.max_retries}")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=30.0  # 30 second timeout
                )
                
                # Extract response content
                content = response.choices[0].message.content
                if not content:
                    raise ContentFilterError("Empty response from OpenAI")
                
                tokens_used = response.usage.total_tokens if response.usage else 0
                
                logger.debug(f"OpenAI API success: {tokens_used} tokens used")
                
                return AIResponse(
                    content=content.strip(),
                    tokens_used=tokens_used,
                    model_used=self.model,
                    success=True
                )
                
            except openai.RateLimitError as e:
                last_error = RateLimitError(f"Rate limit exceeded: {e}")
                delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Rate limit hit, waiting {delay}s before retry {attempt + 1}")
                time.sleep(delay)
                
            except openai.AuthenticationError as e:
                # Don't retry authentication errors
                return AIResponse(
                    content="AI authentication failed",
                    tokens_used=0,
                    model_used=self.model,
                    success=False,
                    error_message=f"API key invalid: {e}"
                )
                
            except openai.BadRequestError as e:
                # Handle content filtering and token limits
                error_msg = str(e)
                if "content_filter" in error_msg.lower():
                    return AIResponse(
                        content="Content filtered",
                        tokens_used=0,
                        model_used=self.model,
                        success=False,
                        error_message=f"Content filtered: {e}"
                    )
                elif "token" in error_msg.lower():
                    return AIResponse(
                        content="Response too long",
                        tokens_used=0,
                        model_used=self.model,
                        success=False,
                        error_message=f"Token limit exceeded: {e}"
                    )
                else:
                    last_error = AIError(f"Bad request: {e}")
                
            except Exception as e:
                last_error = AIError(f"Unexpected error: {e}")
                delay = self.base_delay * (attempt + 1)
                logger.warning(f"API error, waiting {delay}s before retry {attempt + 1}: {e}")
                time.sleep(delay)
        
        # All retries failed
        error_msg = f"Failed after {self.max_retries} attempts: {last_error}"
        logger.error(error_msg)
        
        return AIResponse(
            content="AI service temporarily unavailable",
            tokens_used=0,
            model_used=self.model,
            success=False,
            error_message=error_msg
        )
    
    def test_connection(self) -> bool:
        """
        Test the OpenAI API connection.
        
        Returns:
            True if connection is working, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            test_messages = [
                {"role": "user", "content": "Say 'test' if you can hear me."}
            ]
            
            response = self.generate_completion(test_messages, max_tokens=10, temperature=0.0)
            return response.success and "test" in response.content.lower()
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def estimate_tokens(self, text: str) -> int:
        """
        Rough estimation of tokens for a given text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough approximation: ~4 characters per token for English
        return len(text) // 4 + 1
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current client status.
        
        Returns:
            Status information dictionary
        """
        return {
            'available': self.is_available(),
            'model': self.model,
            'has_api_key': bool(self.api_key),
            'max_retries': self.max_retries,
            'openai_installed': OPENAI_AVAILABLE
        }