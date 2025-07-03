import React from 'react';
import Sidebar from './Sidebar';

interface Player {
  id: string;
  username: string;
  isAI: boolean;
  isAlive?: boolean;
  hasVoted?: boolean;
}

interface GamePlayingSidebarProps {
  location?: string; // Hidden if player is outsider
  isOutsider: boolean;
  currentPlayer: string;
  players: Player[];
  phase: 'questioning' | 'voting' | 'ended';
  timeRemaining?: number;
  onVote?: (targetId: string) => void;
  onEndGame?: () => void;
}

const GamePlayingSidebar: React.FC<GamePlayingSidebarProps> = ({
  location,
  isOutsider,
  currentPlayer,
  players,
  phase,
  timeRemaining,
  onVote,
  onEndGame
}) => {
  const formatTime = (seconds?: number) => {
    if (!seconds) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const alivePlayers = players.filter(p => p.isAlive !== false);
  const eliminatedPlayers = players.filter(p => p.isAlive === false);

  return (
    <Sidebar>
      {/* Game Info */}
      <div className="p-6 border-b border-outsider-gray-800">
        <div className="space-y-3">
          <div>
            <p className="text-xs text-outsider-gray-500">LOCATION</p>
            {isOutsider ? (
              <p className="text-lg font-light text-red-500">UNKNOWN</p>
            ) : (
              <p className="text-lg font-light">{location}</p>
            )}
          </div>
          {isOutsider && (
            <div className="text-xs text-red-500 bg-red-500 bg-opacity-10 p-2 border border-red-500 border-opacity-50">
              YOU ARE THE OUTSIDER - BLEND IN!
            </div>
          )}
          <div>
            <p className="text-xs text-outsider-gray-500">PHASE</p>
            <p className="text-sm uppercase">{phase}</p>
          </div>
          {timeRemaining !== undefined && (
            <div>
              <p className="text-xs text-outsider-gray-500">TIME</p>
              <p className="text-2xl font-mono">{formatTime(timeRemaining)}</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Players Status */}
      <div className="flex-1 p-6 overflow-y-auto">
        <h2 className="text-xs text-outsider-gray-500 tracking-wider mb-4">
          PLAYERS ({alivePlayers.length} ALIVE)
        </h2>
        
        <div className="space-y-2">
          {alivePlayers.map((player) => (
            <div
              key={player.id}
              className={`flex items-center justify-between p-3 border transition-all ${
                phase === 'voting' && player.id !== currentPlayer
                  ? 'border-outsider-gray-600 hover:border-outsider-white cursor-pointer'
                  : 'border-outsider-gray-800'
              } ${
                player.username === currentPlayer ? 'bg-outsider-gray-800' : ''
              }`}
              onClick={() => {
                if (phase === 'voting' && player.id !== currentPlayer && onVote) {
                  onVote(player.id);
                }
              }}
            >
              <div className="flex items-center space-x-3">
                <div className={`w-2 h-2 rounded-full ${
                  player.isAI ? 'bg-outsider-gray-600' : 'bg-outsider-white'
                }`} />
                <span className={player.isAI ? 'text-outsider-gray-500' : ''}>
                  {player.username}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                {player.isAI && (
                  <span className="text-xs text-outsider-gray-600">AI</span>
                )}
                {phase === 'voting' && player.hasVoted && (
                  <span className="text-xs text-green-500">VOTED</span>
                )}
              </div>
            </div>
          ))}
        </div>
        
        {/* Eliminated Players */}
        {eliminatedPlayers.length > 0 && (
          <>
            <h3 className="text-xs text-outsider-gray-600 tracking-wider mt-6 mb-2">
              ELIMINATED
            </h3>
            <div className="space-y-2 opacity-50">
              {eliminatedPlayers.map((player) => (
                <div
                  key={player.id}
                  className="flex items-center p-3 border border-outsider-gray-800 line-through"
                >
                  <div className="w-2 h-2 rounded-full bg-outsider-gray-800 mr-3" />
                  <span>{player.username}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
      
      {/* Game Actions */}
      {phase === 'ended' && (
        <div className="p-6 border-t border-outsider-gray-800">
          <button
            onClick={onEndGame}
            className="btn-primary w-full"
          >
            RETURN TO LOBBY
          </button>
        </div>
      )}
      
      {/* Instructions */}
      {phase === 'questioning' && (
        <div className="p-6 border-t border-outsider-gray-800 text-xs text-outsider-gray-500">
          Ask questions to find the outsider
        </div>
      )}
      
      {phase === 'voting' && (
        <div className="p-6 border-t border-outsider-gray-800 text-xs text-outsider-gray-500">
          Click on a player to vote them out
        </div>
      )}
    </Sidebar>
  );
};

export default GamePlayingSidebar;