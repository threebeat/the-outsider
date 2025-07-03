"""
Answer Manager for The Outsider Game.

Handles ONLY answer flow, validation, and AI integration for answers.
Contains no question logic - purely answer management.

Key Logic: ai_generated=True means it's from the outsider AI (the AI in the game).
Regular AI players and humans use different flows.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class AnswerData:
    """Data about an answer being given."""
    answerer: str
    answer: str
    timestamp: datetime
    answer_to_question_id: Optional[str] = None
    ai_generated: bool = False  # True means from the outsider AI

class AnswerManager:
    """
    Manages answer flow in games.
    
    Handles answer validation and AI integration for answers only.
    Contains no question logic or turn logic - pure answer management.
    
    IMPORTANT: ai_generated=True means from the outsider AI (the AI in the game).
    """
    
    def __init__(self, max_answer_length: int = 300):
        """
        Initialize answer manager.
        
        Args:
            max_answer_length: Maximum characters allowed in answers
        """
        self.max_answer_length = max_answer_length
        logger.debug("Answer manager initialized")
    
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
            ai_generated: True if from the outsider AI, False for humans/regular AI
            
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
            
            ai_type = "outsider AI" if ai_generated else "human/regular AI"
            logger.debug(f"Created answer data: {answerer} ({ai_type})")
            return answer_data
            
        except Exception as e:
            logger.error(f"Error creating answer data: {e}")
            return None
    
    def generate_ai_answer(self, 
                         answerer: str,
                         question: str,
                         asker: str,
                         game_context: Dict[str, Any]) -> Optional[str]:
        """
        Generate an answer from the outsider AI who doesn't know the location.
        
        Args:
            answerer: Outsider AI answering the question
            question: The question being answered
            asker: Username of who asked the question
            game_context: Game context (conversation history, etc.)
            
        Returns:
            Generated answer string or None if failed
        """
        try:
            # The outsider AI doesn't know the location
            from ai import AnswerGenerator
            
            generator = AnswerGenerator()
            answer = generator.generate_answer(
                question=question,
                asker_name=asker,
                is_outsider=True,  # The AI is always the outsider
                location=None,  # Outsider doesn't know location
                ai_personality=game_context.get('ai_personality', 'curious'),
                previous_context=game_context.get('previous_context', [])
            )
            
            logger.info(f"Generated AI answer: {answerer}")
            return answer
            
        except ImportError:
            logger.warning("AI system not available for AI answer generation")
            return self._get_fallback_ai_answer(question)
            
        except Exception as e:
            logger.error(f"Error generating AI answer: {e}")
            return self._get_fallback_ai_answer(question)
    
    def handle_human_answer(self, 
                          answerer: str,
                          answer: str,
                          question_id: Optional[str] = None) -> Optional[AnswerData]:
        """
        Handle an answer from a human player (always a regular player, never outsider).
        
        Args:
            answerer: Human player answering the question
            answer: The answer text
            question_id: ID of question being answered
            
        Returns:
            AnswerData object or None if invalid
        """
        try:
            # Humans are never the outsider AI
            answer_data = self.create_answer_data(
                answerer=answerer,
                answer=answer,
                question_id=question_id,
                ai_generated=False
            )
            
            if answer_data:
                logger.info(f"Human answer processed: {answerer}")
            
            return answer_data
            
        except Exception as e:
            logger.error(f"Error handling human answer: {e}")
            return None
    
    def handle_ai_answer(self,
                       answerer: str,
                       question: str,
                       asker: str,
                       game_context: Dict[str, Any],
                       question_id: Optional[str] = None) -> Optional[AnswerData]:
        """
        Handle an answer from the outsider AI.
        
        Args:
            answerer: Outsider AI answering the question
            question: The question being answered
            asker: Username of who asked the question
            game_context: Game context for AI generation
            question_id: ID of question being answered
            
        Returns:
            AnswerData object or None if failed
        """
        try:
            # Generate answer from the outsider AI
            answer = self.generate_ai_answer(answerer, question, asker, game_context)
            
            if not answer:
                logger.error(f"Failed to generate AI answer for {answerer}")
                return None
            
            answer_data = self.create_answer_data(
                answerer=answerer,
                answer=answer,
                question_id=question_id,
                ai_generated=True  # From the outsider AI
            )
            
            if answer_data:
                logger.info(f"AI answer processed: {answerer}")
            
            return answer_data
            
        except Exception as e:
            logger.error(f"Error handling AI answer: {e}")
            return None
    
    def _get_fallback_ai_answer(self, question: str) -> str:
        """Get a fallback answer for the outsider AI when AI generation fails."""
        import random
        
        question_lower = question.lower()
        
        # Outsider AI answers are vague but confident, could apply anywhere
        if any(word in question_lower for word in ['first', 'notice', 'see']):
            fallback_answers = [
                "The atmosphere definitely stands out to me.",
                "I always notice how people interact in spaces like this.",
                "The environment has a very distinctive feel."
            ]
        elif any(word in question_lower for word in ['prepare', 'bring', 'need']):
            fallback_answers = [
                "I think it depends on what you're planning to do.",
                "I usually just bring the basics and see what's needed.",
                "Common sense preparation is usually enough."
            ]
        elif any(word in question_lower for word in ['rules', 'protocol', 'behavior']):
            fallback_answers = [
                "I think the usual social norms apply here.",
                "It's about being respectful and aware of your surroundings.", 
                "I try to follow the lead of others who seem to know what they're doing."
            ]
        else:
            fallback_answers = [
                "That's an interesting question - it really depends on the situation.",
                "I'd say it varies based on the context and what's happening.",
                "Good question - I think there are different ways to look at that."
            ]
        
        return random.choice(fallback_answers)
    
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
                'from_outsider': answer_data.ai_generated  # UI can show "outsider" label
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
    
    def analyze_ai_answer_quality(self, 
                                answer_data: AnswerData,
                                question: str,
                                known_location: str) -> Dict[str, Any]:
        """
        Analyze how well an outsider AI answer conceals their lack of knowledge.
        
        Args:
            answer_data: The answer data to analyze
            question: The original question
            known_location: The actual location (for comparison)
            
        Returns:
            Analysis results dictionary
        """
        try:
            if not answer_data.ai_generated:
                return {'error': 'Not an AI answer'}
            
            # Basic analysis (could be enhanced with AI)
            answer_lower = answer_data.answer.lower()
            location_lower = known_location.lower()
            
            # Check if answer accidentally reveals location knowledge
            reveals_location = location_lower in answer_lower
            
            # Check if answer is appropriately vague
            vague_indicators = ['depends', 'varies', 'generally', 'usually', 'typically']
            is_appropriately_vague = any(indicator in answer_lower for indicator in vague_indicators)
            
            # Check length (outsider answers tend to be shorter to avoid specifics)
            is_appropriate_length = len(answer_data.answer) < 150
            
            return {
                'reveals_location': reveals_location,
                'appropriately_vague': is_appropriately_vague,
                'appropriate_length': is_appropriate_length,
                'answer_quality_score': sum([
                    not reveals_location,
                    is_appropriately_vague,
                    is_appropriate_length
                ]) / 3.0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing AI answer quality: {e}")
            return {'error': str(e)}
    
    def get_answer_statistics(self, answers: List[AnswerData]) -> Dict[str, Any]:
        """
        Get statistics about answers given in the game.
        
        Args:
            answers: List of AnswerData objects
            
        Returns:
            Statistics dictionary
        """
        try:
            total_answers = len(answers)
            ai_answers = sum(1 for a in answers if a.ai_generated)
            human_answers = total_answers - ai_answers
            
            # Calculate average answer length
            avg_length = sum(len(a.answer) for a in answers) / total_answers if total_answers > 0 else 0
            
            return {
                'total_answers': total_answers,
                'ai_answers': ai_answers,  # From outsider AI
                'human_answers': human_answers,  # From humans and regular AI
                'average_answer_length': round(avg_length, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting answer statistics: {e}")
            return {}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the answer manager.
        
        Returns:
            Status information dictionary
        """
        return {
            'max_answer_length': self.max_answer_length,
            'manager_initialized': True,
            'handles_only': 'answers',
            'ai_generated_means': 'from_outsider_ai'
        }