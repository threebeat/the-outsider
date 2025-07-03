"""
AI Integration Module for The Outsider.

This module handles all OpenAI API interactions for AI players,
including question generation, answer generation, and location guessing.
Name generation is now handled by utils.helpers for better integration.
Contains no game/lobby logic - purely AI prompting.
"""

from .question_generator import QuestionGenerator
from .answer_generator import AnswerGenerator
from .location_guesser import LocationGuesser
from .client import OpenAIClient

__all__ = [
    'QuestionGenerator',
    'AnswerGenerator', 
    'LocationGuesser',
    'OpenAIClient'
]