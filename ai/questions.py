"""
AI Question Generation for The Outsider.

This module handles generating appropriate questions for AI players
based on game context and AI strategy.
"""

import logging
import random
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """Generates questions for AI players to ask during the game."""
    
    def __init__(self):
        # Base question templates that work for any location
        self.generic_questions = [
            "{target}, what's the first thing you notice when you arrive here?",
            "{target}, what would you typically wear in this place?", 
            "{target}, who else would you expect to see here?",
            "{target}, what sounds do you hear in this environment?",
            "{target}, what's the most important rule to follow here?",
            "{target}, what time of day is this place usually busiest?",
            "{target}, what would you bring with you to this place?",
            "{target}, how do people usually behave here?",
            "{target}, what's the main purpose of being here?",
            "{target}, what might make someone uncomfortable here?"
        ]
        
        # More specific question categories
        self.location_specific_questions = {
            'public_place': [
                "{target}, how crowded would you expect this place to be?",
                "{target}, what kind of security measures would you see here?",
                "{target}, how do people typically interact here?"
            ],
            'service_location': [
                "{target}, what kind of service would you expect here?",
                "{target}, who would be helping you in this place?",
                "{target}, what would you need to do before leaving?"
            ],
            'professional_environment': [
                "{target}, what kind of qualifications would you need here?",
                "{target}, what equipment would be essential here?",
                "{target}, what could go wrong in this environment?"
            ]
        }
        
        # Questions based on AI personality/strategy
        self.personality_questions = {
            'analytical': [
                "{target}, what's the most efficient way to navigate this place?",
                "{target}, what systems or processes are in place here?",
                "{target}, what would be the biggest safety concern here?"
            ],
            'social': [
                "{target}, how do people typically greet each other here?",
                "{target}, what would be considered rude behavior here?",
                "{target}, what brings people together in this place?"
            ],
            'cautious': [
                "{target}, what should someone be careful about here?",
                "{target}, what rules are strictly enforced here?",
                "{target}, what could get you in trouble here?"
            ],
            'curious': [
                "{target}, what's the most interesting thing about this place?",
                "{target}, what would surprise a first-time visitor here?",
                "{target}, what's different about this place compared to similar ones?"
            ]
        }
        
        # Follow-up questions based on previous responses
        self.follow_up_questions = [
            "{target}, can you tell me more about that?",
            "{target}, what made you think of that specifically?",
            "{target}, is that always the case here?",
            "{target}, how does that compare to other places?",
            "{target}, what would happen if that wasn't the case?"
        ]
    
    def generate_question(self, ai_player_data: Dict[str, Any], target_username: str,
                         game_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate an appropriate question for an AI player to ask.
        
        Args:
            ai_player_data: Information about the AI player
            target_username: Username of the player being asked
            game_context: Current game state and context
            
        Returns:
            Generated question string
        """
        try:
            # Determine AI personality (default to 'curious' if not specified)
            personality = ai_player_data.get('personality', 'curious')
            is_outsider = ai_player_data.get('is_outsider', False)
            questions_asked = ai_player_data.get('questions_asked', 0)
            
            # Choose question pool based on context
            question_pool = []
            
            # Add generic questions (always available)
            question_pool.extend(self.generic_questions)
            
            # Add personality-based questions
            if personality in self.personality_questions:
                question_pool.extend(self.personality_questions[personality])
            
            # Add follow-up questions if this isn't the first question
            if questions_asked > 0:
                question_pool.extend(self.follow_up_questions)
            
            # If we have game context, add more specific questions
            if game_context:
                location_type = self._categorize_location(game_context.get('location', ''))
                if location_type in self.location_specific_questions:
                    question_pool.extend(self.location_specific_questions[location_type])
            
            # For outsider AI, prefer more general questions to avoid revealing ignorance
            if is_outsider:
                question_pool = [q for q in question_pool if self._is_safe_outsider_question(q)]
            
            # Select and format question
            if question_pool:
                question_template = random.choice(question_pool)
                question = question_template.format(target=target_username)
                
                logger.debug(f"Generated question for AI {ai_player_data.get('username', 'Unknown')}: {question}")
                return question
            else:
                # Fallback to a very generic question
                return f"{target_username}, what's your impression of this place?"
                
        except Exception as e:
            logger.error(f"Error generating AI question: {e}")
            return f"{target_username}, what do you think about this situation?"
    
    def _categorize_location(self, location: str) -> str:
        """
        Categorize a location to determine appropriate question types.
        
        Args:
            location: The location name
            
        Returns:
            Category string
        """
        location_lower = location.lower()
        
        # Public places
        public_places = ['airport', 'museum', 'beach', 'park', 'zoo', 'theater']
        if any(place in location_lower for place in public_places):
            return 'public_place'
        
        # Service locations
        service_places = ['restaurant', 'bank', 'hospital', 'hotel', 'supermarket']
        if any(place in location_lower for place in service_places):
            return 'service_location'
        
        # Professional environments
        professional_places = ['military', 'embassy', 'corporate', 'university', 'studio']
        if any(place in location_lower for place in professional_places):
            return 'professional_environment'
        
        return 'generic'
    
    def _is_safe_outsider_question(self, question_template: str) -> bool:
        """
        Check if a question is safe for an outsider AI to ask.
        
        Args:
            question_template: The question template string
            
        Returns:
            Whether the question is safe for outsiders
        """
        # Avoid questions that might reveal too much knowledge about specifics
        unsafe_keywords = [
            'equipment', 'qualifications', 'systems', 'processes',
            'rules', 'security', 'safety concern', 'strictly enforced'
        ]
        
        question_lower = question_template.lower()
        return not any(keyword in question_lower for keyword in unsafe_keywords)
    
    def generate_follow_up_question(self, previous_answer: str, target_username: str,
                                   ai_personality: str = 'curious') -> str:
        """
        Generate a follow-up question based on a previous answer.
        
        Args:
            previous_answer: The answer that was just given
            target_username: Username of the target player
            ai_personality: AI's personality type
            
        Returns:
            Follow-up question string
        """
        try:
            # Simple follow-up generation based on answer content
            answer_lower = previous_answer.lower()
            
            # Look for keywords in the answer to generate relevant follow-ups
            if 'people' in answer_lower or 'person' in answer_lower:
                follow_ups = [
                    f"{target_username}, what kind of people specifically?",
                    f"{target_username}, how do those people usually interact?",
                    f"{target_username}, would you consider yourself one of those people?"
                ]
            elif 'time' in answer_lower or 'when' in answer_lower:
                follow_ups = [
                    f"{target_username}, what makes that timing important?",
                    f"{target_username}, would it be different at other times?",
                    f"{target_username}, how do you know when it's the right time?"
                ]
            elif 'important' in answer_lower or 'need' in answer_lower:
                follow_ups = [
                    f"{target_username}, why is that so important?",
                    f"{target_username}, what happens if you don't do that?",
                    f"{target_username}, who decides what's important here?"
                ]
            else:
                # Generic follow-ups
                follow_ups = [
                    f"{target_username}, that's interesting, why do you think that is?",
                    f"{target_username}, can you give me an example of that?",
                    f"{target_username}, is that your personal experience or general knowledge?"
                ]
            
            return random.choice(follow_ups)
            
        except Exception as e:
            logger.error(f"Error generating follow-up question: {e}")
            return f"{target_username}, can you elaborate on that?"
    
    def get_question_difficulty(self, question: str, location: str) -> float:
        """
        Assess how difficult a question might be for an outsider to answer.
        
        Args:
            question: The question text
            location: The game location
            
        Returns:
            Difficulty score from 0.0 (easy) to 1.0 (very difficult)
        """
        try:
            question_lower = question.lower()
            location_lower = location.lower()
            
            difficulty = 0.0
            
            # Questions about specific details are harder
            specific_keywords = ['equipment', 'rules', 'procedures', 'uniform', 'protocol']
            for keyword in specific_keywords:
                if keyword in question_lower:
                    difficulty += 0.3
            
            # Questions about insider knowledge are harder
            insider_keywords = ['usually', 'typically', 'always', 'never', 'standard']
            for keyword in insider_keywords:
                if keyword in question_lower:
                    difficulty += 0.2
            
            # Questions about sensory details might be easier
            sensory_keywords = ['see', 'hear', 'smell', 'feel', 'notice']
            for keyword in sensory_keywords:
                if keyword in question_lower:
                    difficulty -= 0.1
            
            # Cap the difficulty between 0.0 and 1.0
            return max(0.0, min(1.0, difficulty))
            
        except Exception as e:
            logger.error(f"Error calculating question difficulty: {e}")
            return 0.5  # Default to medium difficulty