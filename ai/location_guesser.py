"""
AI Location Guesser for The Outsider.

Uses OpenAI API to help outsider AI players analyze context and guess the secret location.
Contains no game logic - purely AI prompting for location analysis.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from .client import OpenAIClient, AIResponse

logger = logging.getLogger(__name__)

class LocationGuesser:
    """
    Helps outsider AI players guess the secret location using OpenAI API.
    
    Analyzes conversation context and generates educated guesses
    about the secret location. Contains no game logic.
    """
    
    def __init__(self, openai_client: Optional[OpenAIClient] = None):
        """
        Initialize location guesser.
        
        Args:
            openai_client: OpenAI client instance (creates new one if None)
        """
        self.client = openai_client or OpenAIClient()
        self.max_tokens = 200  # Location analysis can be longer
        self.temperature = 0.3  # Lower temperature for more analytical responses
        
        logger.debug("Location guesser initialized")
    
    def analyze_context_and_guess(self,
                                 conversation_history: List[Dict[str, str]],
                                 possible_locations: List[str],
                                 confidence_threshold: float = 0.6) -> Tuple[Optional[str], float, str]:
        """
        Analyze conversation context and guess the most likely location.
        
        Args:
            conversation_history: List of Q&A pairs with 'question', 'answer', 'asker', 'answerer'
            possible_locations: List of possible location names to choose from
            confidence_threshold: Minimum confidence to return a guess
            
        Returns:
            Tuple of (location_guess, confidence_score, reasoning)
        """
        try:
            if not conversation_history:
                logger.warning("No conversation history provided for location guessing")
                return None, 0.0, "No context available"
            
            # Build analysis prompt
            prompt = self._build_analysis_prompt(conversation_history, possible_locations)
            
            messages = [
                {"role": "system", "content": self._get_analysis_system_prompt()},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.generate_completion(
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            if response.success:
                location, confidence, reasoning = self._parse_analysis_response(response.content, possible_locations)
                
                if confidence >= confidence_threshold:
                    logger.info(f"Location guess: {location} (confidence: {confidence:.2f})")
                    return location, confidence, reasoning
                else:
                    logger.debug(f"Confidence too low for guess: {confidence:.2f} < {confidence_threshold}")
                    return None, confidence, reasoning
            else:
                logger.warning(f"Failed to analyze context: {response.error_message}")
                return self._get_fallback_guess(conversation_history, possible_locations)
                
        except Exception as e:
            logger.error(f"Error analyzing context: {e}")
            return self._get_fallback_guess(conversation_history, possible_locations)
    
    def get_quick_guess(self,
                       recent_clues: List[str],
                       possible_locations: List[str],
                       max_guesses: int = 3) -> List[Tuple[str, float]]:
        """
        Get quick location guesses based on recent clues.
        
        Args:
            recent_clues: List of recent answers or context clues
            possible_locations: List of possible locations
            max_guesses: Maximum number of guesses to return
            
        Returns:
            List of (location, confidence_score) tuples, sorted by confidence
        """
        try:
            if not recent_clues:
                return []
            
            prompt = f"""
            Based on these recent clues from a location guessing game:
            {chr(10).join(f"- {clue}" for clue in recent_clues)}
            
            Analyze which locations from this list are most likely:
            {', '.join(possible_locations)}
            
            For each likely location, provide:
            1. Location name
            2. Confidence score (0.0-1.0)
            3. Brief reasoning
            
            Format each guess as: "LOCATION: [name] | CONFIDENCE: [score] | REASON: [reasoning]"
            Only include locations with confidence > 0.3
            Order by confidence (highest first)
            """
            
            messages = [
                {"role": "system", "content": self._get_quick_guess_system_prompt()},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.generate_completion(
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            if response.success:
                guesses = self._parse_quick_guesses(response.content, possible_locations)
                return guesses[:max_guesses]
            else:
                logger.warning(f"Failed to get quick guess: {response.error_message}")
                return self._get_fallback_quick_guesses(recent_clues, possible_locations, max_guesses)
                
        except Exception as e:
            logger.error(f"Error getting quick guess: {e}")
            return []
    
    def evaluate_clue_relevance(self,
                               clue: str,
                               possible_locations: List[str]) -> Dict[str, float]:
        """
        Evaluate how relevant a clue is to each possible location.
        
        Args:
            clue: A single clue or answer from the game
            possible_locations: List of possible locations
            
        Returns:
            Dictionary mapping location names to relevance scores (0.0-1.0)
        """
        try:
            prompt = f"""
            Analyze this clue from a location guessing game: "{clue}"
            
            Rate how relevant this clue is to each of these locations (0.0-1.0):
            {', '.join(possible_locations)}
            
            Consider:
            - Direct mentions or implications
            - Context that would fit the location
            - Activities, objects, or situations described
            
            Format: "LOCATION: [name] | RELEVANCE: [score]"
            Include all locations, even with score 0.0
            """
            
            messages = [
                {"role": "system", "content": "You are an expert at analyzing contextual clues for location identification."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.generate_completion(
                messages=messages,
                max_tokens=150,
                temperature=0.2  # Very low temperature for consistent analysis
            )
            
            if response.success:
                return self._parse_relevance_scores(response.content, possible_locations)
            else:
                logger.warning(f"Failed to evaluate clue relevance: {response.error_message}")
                return {loc: 0.1 for loc in possible_locations}  # Uniform low scores
                
        except Exception as e:
            logger.error(f"Error evaluating clue relevance: {e}")
            return {loc: 0.0 for loc in possible_locations}
    
    def _build_analysis_prompt(self, conversation_history: List[Dict[str, str]], possible_locations: List[str]) -> str:
        """Build the prompt for comprehensive location analysis."""
        
        # Format conversation history
        conversation_text = []
        for entry in conversation_history[-10:]:  # Last 10 exchanges
            question = entry.get('question', '')
            answer = entry.get('answer', '')
            asker = entry.get('asker', 'Someone')
            answerer = entry.get('answerer', 'Someone')
            
            if question and answer:
                conversation_text.append(f"{asker} asked {answerer}: \"{question}\"")
                conversation_text.append(f"{answerer} answered: \"{answer}\"")
        
        prompt = f"""
        You are the "outsider" in a social deduction game. Everyone else knows a secret location, but you don't.
        
        Here's the conversation so far:
        {chr(10).join(conversation_text)}
        
        Possible locations to choose from:
        {', '.join(possible_locations)}
        
        Analyze the conversation and determine which location is most likely based on:
        1. Direct mentions or strong implications
        2. Activities, objects, or situations described
        3. Rules, protocols, or behaviors mentioned
        4. Environmental details or atmosphere
        5. Types of people who would be there
        
        Provide your analysis in this format:
        LOCATION: [your best guess]
        CONFIDENCE: [0.0-1.0]
        REASONING: [detailed explanation of why this location fits the clues]
        
        If you're not confident enough to guess, use LOCATION: UNKNOWN
        """
        
        return prompt
    
    def _get_analysis_system_prompt(self) -> str:
        """Get the system prompt for location analysis."""
        return (
            "You are an expert detective analyzing conversational clues to identify a secret location. "
            "Be logical and systematic in your analysis. Consider all evidence carefully. "
            "Be honest about confidence levels - only guess if you have strong evidence."
        )
    
    def _get_quick_guess_system_prompt(self) -> str:
        """Get the system prompt for quick guessing."""
        return (
            "You are analyzing clues to quickly identify possible locations. "
            "Be efficient but thorough. Focus on the strongest connections between clues and locations."
        )
    
    def _parse_analysis_response(self, response: str, possible_locations: List[str]) -> Tuple[Optional[str], float, str]:
        """Parse the analysis response to extract location, confidence, and reasoning."""
        try:
            lines = response.strip().split('\n')
            location = None
            confidence = 0.0
            reasoning = "No reasoning provided"
            
            for line in lines:
                line = line.strip()
                if line.startswith('LOCATION:'):
                    location_text = line.split(':', 1)[1].strip()
                    if location_text != 'UNKNOWN' and location_text in possible_locations:
                        location = location_text
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line.split(':', 1)[1].strip())
                        confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
                    except ValueError:
                        confidence = 0.0
                elif line.startswith('REASONING:'):
                    reasoning = line.split(':', 1)[1].strip()
            
            return location, confidence, reasoning
            
        except Exception as e:
            logger.error(f"Error parsing analysis response: {e}")
            return None, 0.0, "Failed to parse response"
    
    def _parse_quick_guesses(self, response: str, possible_locations: List[str]) -> List[Tuple[str, float]]:
        """Parse quick guess response into list of (location, confidence) tuples."""
        try:
            guesses = []
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if 'LOCATION:' in line and 'CONFIDENCE:' in line:
                    try:
                        # Extract location
                        location_part = line.split('LOCATION:')[1].split('|')[0].strip()
                        if location_part in possible_locations:
                            # Extract confidence
                            confidence_part = line.split('CONFIDENCE:')[1].split('|')[0].strip()
                            confidence = float(confidence_part)
                            confidence = max(0.0, min(1.0, confidence))
                            
                            guesses.append((location_part, confidence))
                    except (IndexError, ValueError) as e:
                        logger.debug(f"Failed to parse guess line: {line} - {e}")
                        continue
            
            # Sort by confidence (highest first)
            guesses.sort(key=lambda x: x[1], reverse=True)
            return guesses
            
        except Exception as e:
            logger.error(f"Error parsing quick guesses: {e}")
            return []
    
    def _parse_relevance_scores(self, response: str, possible_locations: List[str]) -> Dict[str, float]:
        """Parse relevance scores from response."""
        try:
            scores = {}
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if 'LOCATION:' in line and 'RELEVANCE:' in line:
                    try:
                        location_part = line.split('LOCATION:')[1].split('|')[0].strip()
                        relevance_part = line.split('RELEVANCE:')[1].strip()
                        
                        if location_part in possible_locations:
                            relevance = float(relevance_part)
                            relevance = max(0.0, min(1.0, relevance))
                            scores[location_part] = relevance
                    except (IndexError, ValueError):
                        continue
            
            # Fill in missing locations with 0.0
            for location in possible_locations:
                if location not in scores:
                    scores[location] = 0.0
            
            return scores
            
        except Exception as e:
            logger.error(f"Error parsing relevance scores: {e}")
            return {loc: 0.0 for loc in possible_locations}
    
    def _get_fallback_guess(self, conversation_history: List[Dict[str, str]], 
                           possible_locations: List[str]) -> Tuple[Optional[str], float, str]:
        """Get a fallback guess using simple keyword matching."""
        try:
            import random
            from collections import Counter
            
            # Extract all answers
            answers = []
            for entry in conversation_history:
                if 'answer' in entry:
                    answers.append(entry['answer'].lower())
            
            if not answers:
                return None, 0.0, "No conversation data available"
            
            # Simple keyword scoring
            location_scores = {}
            for location in possible_locations:
                score = 0
                location_keywords = location.lower().split()
                
                for answer in answers:
                    for keyword in location_keywords:
                        if keyword in answer:
                            score += 1
                
                location_scores[location] = score
            
            if not any(location_scores.values()):
                return None, 0.0, "No keyword matches found"
            
            best_location = max(location_scores.items(), key=lambda x: x[1])
            confidence = min(0.6, best_location[1] * 0.1)  # Cap at 0.6
            
            return best_location[0], confidence, f"Keyword matching fallback (score: {best_location[1]})"
            
        except Exception as e:
            logger.error(f"Error in fallback guess: {e}")
            return None, 0.0, "Fallback failed"
    
    def _get_fallback_quick_guesses(self, recent_clues: List[str], 
                                   possible_locations: List[str], 
                                   max_guesses: int) -> List[Tuple[str, float]]:
        """Get fallback quick guesses using simple matching."""
        try:
            import random
            
            # Random selection with low confidence
            selected = random.sample(possible_locations, min(max_guesses, len(possible_locations)))
            return [(loc, random.uniform(0.2, 0.4)) for loc in selected]
            
        except Exception as e:
            logger.error(f"Error in fallback quick guesses: {e}")
            return []
    
    def test_analysis(self) -> bool:
        """
        Test if location analysis is working.
        
        Returns:
            True if test successful, False otherwise
        """
        try:
            test_history = [
                {"question": "What do you wear here?", "answer": "Usually a uniform", "asker": "A", "answerer": "B"}
            ]
            test_locations = ["Hospital", "School", "Airport"]
            
            location, confidence, reasoning = self.analyze_context_and_guess(test_history, test_locations, 0.1)
            return confidence > 0.0 and bool(reasoning)
            
        except Exception as e:
            logger.error(f"Location analysis test failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the location guesser.
        
        Returns:
            Status information dictionary
        """
        return {
            'client_available': self.client.is_available(),
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'can_analyze': self.client.is_available()
        }