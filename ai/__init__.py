"""
AI Integration Module for The Outsider.

This module handles all OpenAI API interactions for AI players,
including question generation, answer generation, and location guessing.
AI player initialization is handled by player_initializer.
Name generation is now handled by utils.helpers for better integration.
Contains no game/lobby logic - purely AI prompting and player creation.
"""

from .question_generator import QuestionGenerator
from .answer_generator import AnswerGenerator
from .location_guesser import LocationGuesser
from .player_initializer import AIPlayerInitializer, ai_player_initializer
from .client import OpenAIClient

__all__ = [
    'QuestionGenerator',
    'AnswerGenerator', 
    'LocationGuesser',
    'AIPlayerInitializer',
    'ai_player_initializer',
    'OpenAIClient'
]