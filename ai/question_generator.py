"""
AI Question Generator for The Outsider.

Uses OpenAI API to generate contextual questions for AI players to ask other players.
Contains no game logic - purely AI prompting for question generation.
"""

import logging
from typing import Optional, List, Dict, Any
from .client import OpenAIClient, AIResponse

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """
    Generates questions for AI players using OpenAI API.
    
    Handles crafting prompts and generating appropriate questions
    for the outsider game context. Contains no game logic.
    """
    
    def __init__(self, openai_client: Optional[OpenAIClient] = None):
        """
        Initialize question generator.
        
        Args:
            openai_client: OpenAI client instance (creates new one if None)
        """
        self.client = openai_client or OpenAIClient()
        self.max_tokens = 100  # Questions should be concise
        self.temperature = 0.8  # Allow some creativity
        
        logger.debug("Question generator initialized")
    
    def generate_question(self, 
                         target_player: str,
                         is_outsider: bool = False,
                         location_hint: Optional[str] = None,
                         previous_questions: Optional[List[str]] = None,
                         ai_personality: Optional[str] = None) -> str:
        """
        Generate a question for an AI player to ask another player.
        
        Args:
            target_player: Username of the player being asked
            is_outsider: Whether the AI asking is the outsider (doesn't know location)
            location_hint: Hint about the location type (if AI knows it)
            previous_questions: List of questions already asked
            ai_personality: Personality traits for the AI (curious, analytical, etc.)
            
        Returns:
            Generated question string
        """
        try:
            # Create the prompt based on context
            prompt = self._build_question_prompt(
                target_player=target_player,
                is_outsider=is_outsider,
                location_hint=location_hint,
                previous_questions=previous_questions,
                ai_personality=ai_personality
            )
            
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.generate_completion(
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            if response.success:
                question = self._clean_question(response.content)
                logger.debug(f"Generated question for {target_player}: {question}")
                return question
            else:
                logger.warning(f"Failed to generate question: {response.error_message}")
                return self._get_fallback_question(target_player, is_outsider)
                
        except Exception as e:
            logger.error(f"Error generating question: {e}")
            return self._get_fallback_question(target_player, is_outsider)
    
    def generate_followup_question(self,
                                  target_player: str,
                                  previous_answer: str,
                                  is_outsider: bool = False) -> str:
        """
        Generate a follow-up question based on a previous answer.
        
        Args:
            target_player: Username of the player being asked
            previous_answer: The answer that was just given
            is_outsider: Whether the AI asking is the outsider
            
        Returns:
            Generated follow-up question string
        """
        try:
            prompt = f"""
            {target_player} just answered: "{previous_answer}"
            
            Generate a natural follow-up question that:
            - Builds on their answer
            - Sounds conversational and curious
            - Helps reveal more information about the location
            {"- Avoids revealing that you don't know the location" if is_outsider else ""}
            
            Format: Just the question, addressing {target_player} by name.
            """
            
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.generate_completion(
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            if response.success:
                question = self._clean_question(response.content)
                logger.debug(f"Generated follow-up question: {question}")
                return question
            else:
                logger.warning(f"Failed to generate follow-up: {response.error_message}")
                return self._get_fallback_followup(target_player, previous_answer)
                
        except Exception as e:
            logger.error(f"Error generating follow-up question: {e}")
            return self._get_fallback_followup(target_player, previous_answer)
    
    def _build_question_prompt(self,
                              target_player: str,
                              is_outsider: bool,
                              location_hint: Optional[str],
                              previous_questions: Optional[List[str]],
                              ai_personality: Optional[str]) -> str:
        """Build the prompt for question generation."""
        
        # Base context
        context_parts = [
            f"You are playing a social deduction game where you need to ask {target_player} a question."
        ]
        
        # Add outsider context
        if is_outsider:
            context_parts.append(
                "IMPORTANT: You are the 'outsider' - you don't know the secret location that everyone else knows. "
                "You must ask questions that help you figure out where you are, but WITHOUT revealing that you don't know. "
                "Ask questions that could apply to many locations, and sound natural."
            )
        else:
            context_parts.append(
                "You know the secret location and are trying to identify who the outsider is. "
                "Ask questions that would be easy to answer if someone knows the location, "
                "but difficult if they're the outsider who doesn't know."
            )
        
        # Add location hint if available
        if location_hint and not is_outsider:
            context_parts.append(f"The location context is: {location_hint}")
        
        # Add personality
        personality_traits = {
            'curious': 'Ask questions with genuine curiosity and interest.',
            'analytical': 'Ask logical, systematic questions that gather specific information.',
            'social': 'Ask questions about people and social interactions.',
            'cautious': 'Ask careful questions that don\'t reveal too much about your knowledge.',
            'direct': 'Ask straightforward, clear questions.',
            'creative': 'Ask unique or unexpected questions.'
        }
        
        if ai_personality and ai_personality in personality_traits:
            context_parts.append(personality_traits[ai_personality])
        
        # Add previous questions context
        if previous_questions:
            context_parts.append(f"Avoid repeating these previous questions: {', '.join(previous_questions[-3:])}")
        
        # Instructions
        context_parts.extend([
            f"Generate ONE question to ask {target_player}.",
            "Make it sound natural and conversational.",
            "Keep it concise (under 20 words).",
            f"Address {target_player} by name.",
            "Format: Just the question, no quotes or extra text."
        ])
        
        return "\n".join(context_parts)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI."""
        return (
            "You are an AI player in a social deduction game called 'The Outsider'. "
            "Your role is to generate natural, conversational questions that fit the game context. "
            "Be creative but appropriate. Keep questions concise and engaging."
        )
    
    def _clean_question(self, raw_question: str) -> str:
        """Clean and format the generated question."""
        try:
            # Remove quotes and extra whitespace
            question = raw_question.strip().strip('"\'')
            
            # Ensure it ends with a question mark
            if not question.endswith('?'):
                question += '?'
            
            # Capitalize first letter
            if question:
                question = question[0].upper() + question[1:]
            
            return question
            
        except Exception as e:
            logger.error(f"Error cleaning question: {e}")
            return raw_question
    
    def _get_fallback_question(self, target_player: str, is_outsider: bool) -> str:
        """Get a fallback question when AI generation fails."""
        import random
        
        if is_outsider:
            # Questions that could apply to many locations
            fallback_questions = [
                f"{target_player}, what's the first thing you notice when you arrive here?",
                f"{target_player}, how do you typically prepare before coming to a place like this?",
                f"{target_player}, what would you say is most important to remember here?",
                f"{target_player}, who else would you expect to see in a place like this?",
                f"{target_player}, what's the general atmosphere like here?"
            ]
        else:
            # Questions that might trip up an outsider
            fallback_questions = [
                f"{target_player}, what's the usual protocol when you first get here?",
                f"{target_player}, what equipment do you typically need in this environment?",
                f"{target_player}, what's the busiest time here usually?",
                f"{target_player}, what rules are most strictly enforced here?",
                f"{target_player}, what would be considered inappropriate behavior here?"
            ]
        
        return random.choice(fallback_questions)
    
    def _get_fallback_followup(self, target_player: str, previous_answer: str) -> str:
        """Get a fallback follow-up question."""
        import random
        
        fallback_followups = [
            f"{target_player}, can you tell me more about that?",
            f"{target_player}, what made you think of that specifically?",
            f"{target_player}, is that always the case here?",
            f"{target_player}, how does that compare to other places?",
            f"{target_player}, what would happen if that wasn't true?"
        ]
        
        return random.choice(fallback_followups)
    
    def test_generation(self) -> bool:
        """
        Test if question generation is working.
        
        Returns:
            True if test successful, False otherwise
        """
        try:
            test_question = self.generate_question("TestPlayer", is_outsider=True)
            return bool(test_question and "TestPlayer" in test_question and "?" in test_question)
        except Exception as e:
            logger.error(f"Question generation test failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the question generator.
        
        Returns:
            Status information dictionary
        """
        return {
            'client_available': self.client.is_available(),
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'can_generate': self.client.is_available()
        }