"""
API Route Handlers for The Outsider.

Pure routing layer that delegates to appropriate business logic modules.
Contains no business logic - only request/response handling.
"""

import logging
from flask import jsonify
from utils.helpers import get_random_available_name

logger = logging.getLogger(__name__)

def register_api_handlers(app, lobby_manager, game_manager):
    """
    Register all API route handlers.
    
    Args:
        app: Flask application instance
        lobby_manager: Lobby management instance  
        game_manager: Game management instance
    """

    @app.route('/api/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'message': 'The Outsider game server is running',
            'version': '3.0.0'
        })

    @app.route('/api/random-name')
    def get_random_name():
        """Get a random available name for players."""
        try:
            # Use helper function to get random available name
            random_name = get_random_available_name()
            
            if random_name:
                return jsonify({
                    'name': random_name,
                    'message': 'Random name generated successfully'
                })
            else:
                return jsonify({
                    'error': 'No available names found',
                    'message': 'All names are currently taken'
                }), 404
                
        except Exception as e:
            logger.error(f"Error generating random name: {e}")
            return jsonify({
                'error': 'Failed to generate random name',
                'message': 'Please try again or enter a name manually'
            }), 500

    @app.route('/api/stats')
    def get_stats():
        """Game statistics endpoint."""
        try:
            # Delegate to game manager for statistics
            stats = game_manager.get_game_statistics()
            
            if stats:
                return jsonify({
                    'human_wins': stats.get('human_wins', 0),
                    'ai_wins': stats.get('ai_wins', 0),
                    'total_games': stats.get('total_games', 0),
                    'human_win_rate': stats.get('human_win_rate', 0.0),
                    'avg_game_duration': stats.get('avg_game_duration', 0.0)
                })
            else:
                return jsonify({'message': 'No statistics available'})
                
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return jsonify({'error': 'Failed to get statistics'}), 500

    @app.route('/api/lobbies/active')
    def get_active_lobbies():
        """Get list of active lobbies."""
        try:
            # Delegate to lobby manager
            lobbies = lobby_manager.get_active_lobbies()
            return jsonify({'lobbies': lobbies})
            
        except Exception as e:
            logger.error(f"Error getting active lobbies: {e}")
            return jsonify({'error': 'Failed to get lobbies'}), 500

    @app.route('/api/lobbies/cleanup')
    def cleanup_inactive():
        """Clean up inactive lobbies (admin endpoint)."""
        try:
            # Delegate to lobby manager
            cleaned_count = lobby_manager.cleanup_inactive_lobbies()
            return jsonify({
                'message': f'Cleaned up {cleaned_count} inactive lobbies'
            })
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return jsonify({'error': 'Cleanup failed'}), 500
    
    @app.route('/api/ai/status')
    def get_ai_status():
        """Get AI system status."""
        try:
            # Delegate to game manager for AI status
            ai_status = game_manager.get_ai_status()
            return jsonify(ai_status)
            
        except Exception as e:
            logger.error(f"Error getting AI status: {e}")
            return jsonify({'error': 'Failed to get AI status'}), 500

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        return jsonify({'error': 'Internal server error'}), 500
    
    logger.info("API handlers registered successfully")