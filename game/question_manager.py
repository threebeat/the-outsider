"""
Question Manager for The Outsider Game.

Handles question/answer flow, validation, and AI integration.
Contains no lobby or turn logic - purely question/answer management.
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
    ai_generated: bool = False

@dataclass
class AnswerData:
    """Data about an answer being given."""
    answerer: str
    answer: str
    timestamp: datetime
    answer_to_question_id: Optional[str] = None
    ai_generated: bool = False

class QuestionManager:
    """
    Manages question/answer flow in games.
    
    Handles question validation, answer validation, and AI integration.
    Contains no game state or turn logic - pure Q&A management.
    """
    
    def __init__(self, max_question_length: int = 200, max_answer_length: int = 300):
        """
        Initialize question manager.
        
        Args:
            max_question_length: Maximum characters allowed in questions
            max_answer_length: Maximum characters allowed in answers
        """
        self.max_question_length = max_question_length
        self.max_answer_length = max_answer_length
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
    
    def validate_answer(self, answer: str, answerer: str) -> tuple[bool, str]:
        """
        Validate an answer before it's given.
        
        Args:
            answer: The answer text
            answerer: Username of player answering
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check for empty answer
            if not answer or not answer.strip():
                return False, "Answer cannot be empty"
            
            # Check answer length
            if len(answer) > self.max_answer_length:
                return False, f"Answer too long (max {self.max_answer_length} characters)"
            
            # Check for empty username
            if not answerer or not answerer.strip():
                return False, "Answerer username required"
            
            # Check for potentially inappropriate content (basic filter)
            inappropriate_words = ['fuck', 'shit', 'damn']  # Basic example
            answer_lower = answer.lower()
            for word in inappropriate_words:
                if word in answer_lower:
                    return False, "Answer contains inappropriate content"
            
            return True, "Answer is valid"
            
        except Exception as e:
            logger.error(f"Error validating answer: {e}")
            return False, "Answer validation failed"
    
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
            ai_generated: Whether question was generated by AI
            
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
            
            logger.debug(f"Created question data: {asker} -> {target}")
            return question_data
            
        except Exception as e:
            logger.error(f"Error creating question data: {e}")
            return None
    
    def create_answer_data(self, 
                          answerer: str, 
                          answer: str,
                          question_id: Optional[str] = None,
                          ai_generated: bool = False) -> Optional[AnswerData]:
        """
        Create answer data object.
        
        Args:
            answerer: Username of player answering
            answer: The answer text
            question_id: ID of question being answered
            ai_generated: Whether answer was generated by AI
            
        Returns:
            AnswerData object or None if invalid
        """
        try:
            # Validate the answer first
            is_valid, error_message = self.validate_answer(answer, answerer)
            if not is_valid:
                logger.warning(f"Invalid answer: {error_message}")
                return None
            
            answer_data = AnswerData(
                answerer=answerer.strip(),
                answer=answer.strip(),
                timestamp=datetime.now(),
                answer_to_question_id=question_id,
                ai_generated=ai_generated
            )
            
            logger.debug(f"Created answer data: {answerer}")
            return answer_data
            
        except Exception as e:
            logger.error(f"Error creating answer data: {e}")
            return None
    
    def generate_ai_question(self, 
                           asker: str, 
                           target: str,
                           context: Dict[str, Any]) -> Optional[str]:
        """
        Generate an AI question using the AI system.
        
        Args:
            asker: AI player asking the question
            target: Target player username
            context: Context information (is_outsider, location, etc.)
            
        Returns:
            Generated question string or None if failed
        """
        try:
            # Import AI system (optional dependency)
            try:
                from ai import QuestionGenerator
                
                generator = QuestionGenerator()
                question = generator.generate_question(
                    target_player=target,
                    is_outsider=context.get('is_outsider', False),
                    location_hint=context.get('location'),
                    previous_questions=context.get('previous_questions', []),
                    ai_personality=context.get('personality', 'curious')
                )
                
                logger.info(f"Generated AI question for {asker} -> {target}")
                return question
                
            except ImportError:
                logger.warning("AI system not available for question generation")
                return self._get_fallback_question(target)
                
        except Exception as e:
            logger.error(f"Error generating AI question: {e}")
            return self._get_fallback_question(target)
    
    def generate_ai_answer(self, 
                          answerer: str, 
                          question: str,
                          context: Dict[str, Any]) -> Optional[str]:
        """
        Generate an AI answer using the AI system.
        
        Args:
            answerer: AI player answering the question
            question: The question being answered
            context: Context information (is_outsider, location, etc.)
            
        Returns:
            Generated answer string or None if failed
        """
        try:
            # Import AI system (optional dependency)
            try:
                from ai import AnswerGenerator
                
                generator = AnswerGenerator()
                answer = generator.generate_answer(
                    question=question,
                    asker_name=context.get('asker', 'Someone'),
                    is_outsider=context.get('is_outsider', False),
                    location=context.get('location'),
                    ai_personality=context.get('personality', 'curious'),
                    previous_context=context.get('previous_context', [])
                )
                
                logger.info(f"Generated AI answer for {answerer}")
                return answer
                
            except ImportError:
                logger.warning("AI system not available for answer generation")
                return self._get_fallback_answer(question)
                
        except Exception as e:
            logger.error(f"Error generating AI answer: {e}")
            return self._get_fallback_answer(question)
    
    def _get_fallback_question(self, target: str) -> str:
        """Get a fallback question when AI generation fails."""
        import random
        
        fallback_questions = [
            f"{target}, what's your first impression of this place?",
            f"{target}, what do you think is most important here?",
            f"{target}, how would you describe the atmosphere?",
            f"{target}, what stands out to you the most?",
            f"{target}, what would you say is typical here?"
        ]
        
        return random.choice(fallback_questions)
    
    def _get_fallback_answer(self, question: str) -> str:
        """Get a fallback answer when AI generation fails."""
        import random
        
        fallback_answers = [
            "That's an interesting question - I'd say it depends on the situation.",
            "I think most people would have a similar experience here.",
            "From what I can tell, it's pretty much what you'd expect.",
            "I'd say it varies, but generally it's fairly straightforward.",
            "That's a good point - I think it really depends on your perspective."
        ]
        
        return random.choice(fallback_answers)
    
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
                'ai_generated': question_data.ai_generated
            }
            
        except Exception as e:
            logger.error(f"Error formatting question for broadcast: {e}")
            return {}
    
    def format_answer_for_broadcast(self, answer_data: AnswerData) -> Dict[str, Any]:
        """
        Format answer data for broadcasting to players.
        
        Args:
            answer_data: AnswerData object
            
        Returns:
            Dictionary ready for JSON serialization
        """
        try:
            return {
                'answerer': answer_data.answerer,
                'answer': answer_data.answer,
                'timestamp': answer_data.timestamp.isoformat(),
                'ai_generated': answer_data.ai_generated
            }
            
        except Exception as e:
            logger.error(f"Error formatting answer for broadcast: {e}")
            return {}
    
    def should_advance_after_answer(self, 
                                   questions_this_round: int, 
                                   max_questions_per_round: int) -> bool:
        """
        Determine if game should advance to voting after this answer.
        
        Args:
            questions_this_round: Number of questions asked this round
            max_questions_per_round: Maximum questions allowed per round
            
        Returns:
            True if should advance to voting, False if continue questions
        """
        try:
            return questions_this_round >= max_questions_per_round
            
        except Exception as e:
            logger.error(f"Error determining if should advance: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the question manager.
        
        Returns:
            Status information dictionary
        """
        return {
            'max_question_length': self.max_question_length,
            'max_answer_length': self.max_answer_length,
            'manager_initialized': True
        }