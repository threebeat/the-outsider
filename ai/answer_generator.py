"""
AI Answer Generator for The Outsider.

Uses OpenAI API to generate contextual answers for AI players when responding to questions.
Contains no game logic - purely AI prompting for answer generation.
"""

import logging
from typing import Optional, List, Dict, Any
from .client import OpenAIClient, AIResponse

logger = logging.getLogger(__name__)

class AnswerGenerator:
    """
    Generates answers for AI players using OpenAI API.
    
    Handles crafting prompts and generating appropriate responses
    to questions in the outsider game context. Contains no game logic.
    """
    
    def __init__(self, openai_client: Optional[OpenAIClient] = None):
        """
        Initialize answer generator.
        
        Args:
            openai_client: OpenAI client instance (creates new one if None)
        """
        self.client = openai_client or OpenAIClient()
        self.max_tokens = 120  # Answers can be slightly longer than questions
        self.temperature = 0.7  # Balanced creativity
        
        logger.debug("Answer generator initialized")
    
    def generate_answer(self,
                       question: str,
                       asker_name: str,
                       is_outsider: bool = False,
                       location: Optional[str] = None,
                       ai_personality: Optional[str] = None,
                       previous_context: Optional[List[str]] = None) -> str:
        """
        Generate an answer to a question for an AI player.
        
        Args:
            question: The question being asked
            asker_name: Username of the player asking the question
            is_outsider: Whether the AI answering is the outsider (doesn't know location)
            location: The actual location (if AI knows it)
            ai_personality: Personality traits for the AI
            previous_context: Previous questions/answers for context
            
        Returns:
            Generated answer string
        """
        try:
            # Create the prompt based on context
            prompt = self._build_answer_prompt(
                question=question,
                asker_name=asker_name,
                is_outsider=is_outsider,
                location=location,
                ai_personality=ai_personality,
                previous_context=previous_context
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
                answer = self._clean_answer(response.content)
                logger.debug(f"Generated answer to '{question}': {answer}")
                return answer
            else:
                logger.warning(f"Failed to generate answer: {response.error_message}")
                return self._get_fallback_answer(question, is_outsider)
                
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return self._get_fallback_answer(question, is_outsider)
    
    def generate_clarification_answer(self,
                                    original_question: str,
                                    followup_question: str,
                                    asker_name: str,
                                    is_outsider: bool = False,
                                    location: Optional[str] = None) -> str:
        """
        Generate an answer to a follow-up or clarification question.
        
        Args:
            original_question: The original question that was asked
            followup_question: The follow-up question being asked
            asker_name: Username of the player asking
            is_outsider: Whether the AI answering is the outsider
            location: The actual location (if AI knows it)
            
        Returns:
            Generated clarification answer string
        """
        try:
            prompt = f"""
            You were previously asked: "{original_question}"
            Now {asker_name} is asking a follow-up: "{followup_question}"
            
            Context:
            {"You are the outsider who doesn't know the secret location. Give vague but plausible answers." if is_outsider else f"You know the location is: {location}. Answer based on this knowledge."}
            
            Generate a natural response that:
            - Builds on your previous implied answer
            - Sounds confident and knowledgeable
            {"- Doesn't reveal that you don't know the location" if is_outsider else ""}
            - Is conversational and brief (1-2 sentences)
            
            Format: Just your answer, no quotes.
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
                answer = self._clean_answer(response.content)
                logger.debug(f"Generated clarification answer: {answer}")
                return answer
            else:
                logger.warning(f"Failed to generate clarification: {response.error_message}")
                return self._get_fallback_clarification(followup_question, is_outsider)
                
        except Exception as e:
            logger.error(f"Error generating clarification: {e}")
            return self._get_fallback_clarification(followup_question, is_outsider)
    
    def _build_answer_prompt(self,
                            question: str,
                            asker_name: str,
                            is_outsider: bool,
                            location: Optional[str],
                            ai_personality: Optional[str],
                            previous_context: Optional[List[str]]) -> str:
        """Build the prompt for answer generation."""
        
        context_parts = [
            f"{asker_name} asked you: \"{question}\""
        ]
        
        # Add role context
        if is_outsider:
            context_parts.extend([
                "IMPORTANT: You are the 'outsider' - you don't know the secret location that everyone else knows.",
                "You must answer the question in a way that:",
                "- Sounds confident and knowledgeable", 
                "- Doesn't reveal that you don't know the location",
                "- Could plausibly apply to many different locations",
                "- Sounds natural and not suspicious",
                "Give a vague but believable answer that could work anywhere."
            ])
        else:
            context_parts.extend([
                f"You know the secret location is: {location}",
                "Answer the question based on your knowledge of this specific location.",
                "Be confident and specific enough to sound knowledgeable,",
                "but not so specific that you give away the location obviously."
            ])
        
        # Add personality traits
        personality_styles = {
            'curious': 'Answer with enthusiasm and maybe ask something back.',
            'analytical': 'Give a logical, systematic answer with details.',
            'social': 'Answer in a friendly, conversational way.',
            'cautious': 'Give a careful, measured response.',
            'direct': 'Answer straightforwardly and concisely.',
            'creative': 'Give an interesting or unique perspective.'
        }
        
        if ai_personality and ai_personality in personality_styles:
            context_parts.append(personality_styles[ai_personality])
        
        # Add previous context if available
        if previous_context:
            context_parts.append(f"Keep your answer consistent with previous conversation: {' '.join(previous_context[-2:])}")
        
        # Instructions
        context_parts.extend([
            "Generate a natural response (1-2 sentences).",
            "Sound confident and conversational.",
            "Don't overthink it - be natural.",
            "Format: Just your answer, no quotes or extra text."
        ])
        
        return "\n".join(context_parts)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI."""
        return (
            "You are an AI player in a social deduction game called 'The Outsider'. "
            "Your role is to generate natural, conversational answers to questions. "
            "Be confident but not overly detailed. Sound like a real person would."
        )
    
    def _clean_answer(self, raw_answer: str) -> str:
        """Clean and format the generated answer."""
        try:
            # Remove quotes and extra whitespace
            answer = raw_answer.strip().strip('"\'')
            
            # Capitalize first letter
            if answer:
                answer = answer[0].upper() + answer[1:]
            
            # Ensure it doesn't end with a question mark unless it's actually a question
            if answer.endswith('?') and not any(word in answer.lower() for word in ['what', 'where', 'when', 'why', 'how', 'who', 'which']):
                answer = answer[:-1] + '.'
            
            return answer
            
        except Exception as e:
            logger.error(f"Error cleaning answer: {e}")
            return raw_answer
    
    def _get_fallback_answer(self, question: str, is_outsider: bool) -> str:
        """Get a fallback answer when AI generation fails."""
        import random
        
        question_lower = question.lower()
        
        if is_outsider:
            # Vague answers that could apply anywhere
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
        else:
            # More specific answers (but still generic since we don't have location context)
            fallback_answers = [
                "From my experience, it's usually pretty straightforward.",
                "I think most people would agree it's fairly typical for places like this.",
                "It's generally what you'd expect in this kind of environment.",
                "That's definitely something to keep in mind here."
            ]
        
        return random.choice(fallback_answers)
    
    def _get_fallback_clarification(self, question: str, is_outsider: bool) -> str:
        """Get a fallback clarification answer."""
        import random
        
        if is_outsider:
            fallback_clarifications = [
                "I mean, it's hard to explain exactly, but you know what I mean.",
                "Well, it's just the general vibe I get from places like this.",
                "I think most people would have a similar experience."
            ]
        else:
            fallback_clarifications = [
                "What I meant was the standard approach that most people take.",
                "It's just the typical way things work in this environment.",
                "I'm referring to the common practices you'd see here."
            ]
        
        return random.choice(fallback_clarifications)
    
    def test_generation(self) -> bool:
        """
        Test if answer generation is working.
        
        Returns:
            True if test successful, False otherwise
        """
        try:
            test_answer = self.generate_answer(
                question="What do you think about this place?",
                asker_name="TestPlayer",
                is_outsider=True
            )
            return bool(test_answer and len(test_answer.strip()) > 5)
        except Exception as e:
            logger.error(f"Answer generation test failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the answer generator.
        
        Returns:
            Status information dictionary
        """
        return {
            'client_available': self.client.is_available(),
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'can_generate': self.client.is_available()
        }