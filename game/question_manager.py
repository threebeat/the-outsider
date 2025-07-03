"""
Question Manager for The Outsider Game.

Handles ONLY question flow, validation, and AI integration for questions.
Contains no answer logic - purely question management.

Key Logic: ai_generated=True means it's from the outsider AI (the AI in the game).
Regular AI players and humans use different flows.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class QuestionData:
    """Data about a question being asked."""
    asker: str
    target: str
    question: str
    timestamp: datetime
    question_id: Optional[str] = None
    ai_generated: bool = False  # True means from the outsider AI

class QuestionManager:
    """
    Manages question flow in games.
    
    Handles question validation and AI integration for questions only.
    Contains no answer logic or turn logic - pure question management.
    
    IMPORTANT: ai_generated=True means from the outsider AI (the AI in the game).
    """
    
    def __init__(self, max_question_length: int = 200):
        """
        Initialize question manager.
        
        Args:
            max_question_length: Maximum characters allowed in questions
        """
        self.max_question_length = max_question_length
        logger.debug("Question manager initialized")
    
    def validate_question(self, question: str, asker: str, target: str) -> tuple[bool, str]:
        """
        Validate a question before it's asked.
        
        Args:
            question: The question text
            asker: Username of player asking
            target: Username of target player
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check for empty question
            if not question or not question.strip():
                return False, "Question cannot be empty"
            
            # Check question length
            if len(question) > self.max_question_length:
                return False, f"Question too long (max {self.max_question_length} characters)"
            
            # Check for empty usernames
            if not asker or not asker.strip():
                return False, "Asker username required"
            
            if not target or not target.strip():
                return False, "Target username required"
            
            # Check that asker isn't targeting themselves
            if asker.strip().lower() == target.strip().lower():
                return False, "Cannot ask questions to yourself"
            
            # Check for potentially inappropriate content (basic filter)
            inappropriate_words = ['fuck', 'shit', 'damn']  # Basic example
            question_lower = question.lower()
            for word in inappropriate_words:
                if word in question_lower:
                    return False, "Question contains inappropriate content"
            
            return True, "Question is valid"
            
        except Exception as e:
            logger.error(f"Error validating question: {e}")
            return False, "Question validation failed"
    
    def create_question_data(self, 
                           asker: str, 
                           target: str, 
                           question: str,
                           ai_generated: bool = False) -> Optional[QuestionData]:
        """
        Create question data object.
        
        Args:
            asker: Username of player asking
            target: Username of target player
            question: The question text
            ai_generated: True if from the outsider AI, False for humans/regular AI
            
        Returns:
            QuestionData object or None if invalid
        """
        try:
            # Validate the question first
            is_valid, error_message = self.validate_question(question, asker, target)
            if not is_valid:
                logger.warning(f"Invalid question: {error_message}")
                return None
            
            question_data = QuestionData(
                asker=asker.strip(),
                target=target.strip(),
                question=question.strip(),
                timestamp=datetime.now(),
                ai_generated=ai_generated
            )
            
            ai_type = "outsider AI" if ai_generated else "human/regular AI"
            logger.debug(f"Created question data: {asker} -> {target} ({ai_type})")
            return question_data
            
        except Exception as e:
            logger.error(f"Error creating question data: {e}")
            return None
    
    def generate_ai_question(self, 
                           asker: str,
                           target: str,
                           game_context: Dict[str, Any]) -> Optional[str]:
        """
        Generate a question from the outsider AI who doesn't know the location.
        
        Args:
            asker: Outsider AI asking the question
            target: Target player username
            game_context: Game context (previous questions, conversation history, etc.)
            
        Returns:
            Generated question string or None if failed
        """
        try:
            # The outsider AI doesn't know the location
            from ai import QuestionGenerator
            
            generator = QuestionGenerator()
            question = generator.generate_question(
                target_player=target,
                is_outsider=True,  # The AI is always the outsider
                location_hint=None,  # Outsider doesn't know location
                previous_questions=game_context.get('previous_questions', []),
                ai_personality=game_context.get('ai_personality', 'curious')
            )
            
            logger.info(f"Generated AI question: {asker} -> {target}")
            return question
            
        except ImportError:
            logger.warning("AI system not available for AI question generation")
            return self._get_fallback_ai_question(target)
            
        except Exception as e:
            logger.error(f"Error generating AI question: {e}")
            return self._get_fallback_ai_question(target)
    
    def handle_human_question(self, 
                            asker: str,
                            target: str, 
                            question: str) -> Optional[QuestionData]:
        """
        Handle a question from a human player (always a regular player, never outsider).
        
        Args:
            asker: Human player asking the question
            target: Target player username  
            question: The question text
            
        Returns:
            QuestionData object or None if invalid
        """
        try:
            # Humans are never the outsider AI
            question_data = self.create_question_data(
                asker=asker,
                target=target,
                question=question,
                ai_generated=False
            )
            
            if question_data:
                logger.info(f"Human question processed: {asker} -> {target}")
            
            return question_data
            
        except Exception as e:
            logger.error(f"Error handling human question: {e}")
            return None
    
    def handle_ai_question(self,
                         asker: str,
                         target: str,
                         game_context: Dict[str, Any]) -> Optional[QuestionData]:
        """
        Handle a question from the outsider AI.
        
        Args:
            asker: Outsider AI asking the question
            target: Target player username
            game_context: Game context for AI generation
            
        Returns:
            QuestionData object or None if failed
        """
        try:
            # Generate question from the outsider AI
            question = self.generate_ai_question(asker, target, game_context)
            
            if not question:
                logger.error(f"Failed to generate AI question for {asker}")
                return None
            
            question_data = self.create_question_data(
                asker=asker,
                target=target,
                question=question,
                ai_generated=True  # From the outsider AI
            )
            
            if question_data:
                logger.info(f"AI question processed: {asker} -> {target}")
            
            return question_data
            
        except Exception as e:
            logger.error(f"Error handling AI question: {e}")
            return None
    
    def _get_fallback_ai_question(self, target: str) -> str:
        """Get a fallback question for the outsider AI when AI generation fails."""
        import random
        
        # Outsider AI questions are vague and could apply to many locations
        fallback_questions = [
            f"{target}, what's the first thing you notice when you arrive here?",
            f"{target}, how do people usually behave in places like this?",
            f"{target}, what would you say is most important to remember here?",
            f"{target}, who else would you expect to see in a place like this?",
            f"{target}, what's the general atmosphere like here?"
        ]
        
        return random.choice(fallback_questions)
    
    def format_question_for_broadcast(self, question_data: QuestionData) -> Dict[str, Any]:
        """
        Format question data for broadcasting to players.
        
        Args:
            question_data: QuestionData object
            
        Returns:
            Dictionary ready for JSON serialization
        """
        try:
            return {
                'asker': question_data.asker,
                'target': question_data.target,
                'question': question_data.question,
                'timestamp': question_data.timestamp.isoformat(),
                'from_outsider': question_data.ai_generated  # UI can show "outsider" label
            }
            
        except Exception as e:
            logger.error(f"Error formatting question for broadcast: {e}")
            return {}
    
    def get_question_statistics(self, questions: List[QuestionData]) -> Dict[str, Any]:
        """
        Get statistics about questions asked in the game.
        
        Args:
            questions: List of QuestionData objects
            
        Returns:
            Statistics dictionary
        """
        try:
            total_questions = len(questions)
            ai_questions = sum(1 for q in questions if q.ai_generated)
            human_questions = total_questions - ai_questions
            
            return {
                'total_questions': total_questions,
                'ai_questions': ai_questions,  # From outsider AI
                'human_questions': human_questions,  # From humans and regular AI
            }
            
        except Exception as e:
            logger.error(f"Error getting question statistics: {e}")
            return {}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the question manager.
        
        Returns:
            Status information dictionary
        """
        return {
            'max_question_length': self.max_question_length,
            'manager_initialized': True,
            'handles_only': 'questions',
            'ai_generated_means': 'from_outsider_ai'
        }