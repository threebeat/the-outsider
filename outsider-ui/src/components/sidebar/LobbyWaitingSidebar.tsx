import React from 'react';
import Sidebar from './Sidebar';

interface Player {
  id: string;
  username: string;
  isAI: boolean;
  isHost?: boolean;
}

interface LobbyWaitingSidebarProps {
  lobbyCode: string;
  lobbyName: string;
  players: Player[];
  currentUserId: string;
  isHost: boolean;
  onStartGame: () => void;
  onLeaveLobby: () => void;
}

const LobbyWaitingSidebar: React.FC<LobbyWaitingSidebarProps> = ({
  lobbyCode,
  lobbyName,
  players,
  currentUserId,
  isHost,
  onStartGame,
  onLeaveLobby
}) => {
  const minPlayers = 3;
  const maxPlayers = 8;
  const canStart = players.length >= minPlayers && isHost;

  return (
    <Sidebar>
      {/* Lobby Info */}
      <div className="p-6 border-b border-outsider-gray-800">
        <div className="space-y-3">
          <div>
            <p className="text-xs text-outsider-gray-500">LOBBY</p>
            <p className="text-lg font-light">{lobbyName}</p>
          </div>
          <div>
            <p className="text-xs text-outsider-gray-500">CODE</p>
            <p className="text-2xl font-mono tracking-wider">{lobbyCode}</p>
          </div>
        </div>
      </div>
      
      {/* Players List */}
      <div className="flex-1 p-6 overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs text-outsider-gray-500 tracking-wider">
            PLAYERS ({players.length}/{maxPlayers})
          </h2>
          {players.length < minPlayers && (
            <span className="text-xs text-outsider-gray-600">
              NEED {minPlayers - players.length} MORE
            </span>
          )}
        </div>
        
        <div className="space-y-2">
          {players.map((player) => (
            <div
              key={player.id}
              className={`flex items-center justify-between p-3 border border-outsider-gray-800 ${
                player.id === currentUserId ? 'bg-outsider-gray-800' : ''
              }`}
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
                {player.isHost && (
                  <span className="text-xs text-outsider-gray-500">HOST</span>
                )}
              </div>
            </div>
          ))}
        </div>
        
        {/* Empty slots */}
        {[...Array(Math.max(0, minPlayers - players.length))].map((_, i) => (
          <div
            key={`empty-${i}`}
            className="flex items-center p-3 border border-outsider-gray-800 border-dashed mt-2"
          >
            <div className="w-2 h-2 rounded-full bg-outsider-gray-800 mr-3" />
            <span className="text-outsider-gray-600">Waiting for player...</span>
          </div>
        ))}
      </div>
      
      {/* Actions */}
      <div className="p-6 border-t border-outsider-gray-800 space-y-3">
        {isHost ? (
          <>
            <button
              onClick={onStartGame}
              disabled={!canStart}
              className={`w-full ${
                canStart ? 'btn-primary' : 'btn-secondary opacity-50 cursor-not-allowed'
              }`}
            >
              {canStart ? 'START GAME' : `NEED ${minPlayers} PLAYERS`}
            </button>
            <button
              onClick={onLeaveLobby}
              className="w-full text-outsider-gray-500 hover:text-outsider-white transition-colors text-sm"
            >
              LEAVE LOBBY
            </button>
          </>
        ) : (
          <>
            <div className="text-center text-sm text-outsider-gray-500 py-2">
              Waiting for host to start...
            </div>
            <button
              onClick={onLeaveLobby}
              className="btn-secondary w-full"
            >
              LEAVE LOBBY
            </button>
          </>
        )}
      </div>
    </Sidebar>
  );
};

export default LobbyWaitingSidebar;