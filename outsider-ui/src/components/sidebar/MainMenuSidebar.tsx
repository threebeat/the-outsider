import React, { useState } from 'react';
import Sidebar from './Sidebar';

interface MainMenuSidebarProps {
  username: string;
  onJoinLobby: (lobbyCode: string) => void;
  onCreateLobby: () => void;
  onLogout: () => void;
}

const MainMenuSidebar: React.FC<MainMenuSidebarProps> = ({
  username,
  onJoinLobby,
  onCreateLobby,
  onLogout
}) => {
  const [showJoinForm, setShowJoinForm] = useState(false);
  const [lobbyCode, setLobbyCode] = useState('');
  const [joinError, setJoinError] = useState('');

  const handleJoinSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const code = lobbyCode.trim().toUpperCase();
    if (!code) {
      setJoinError('Please enter a lobby code');
      return;
    }
    
    if (code.length < 4 || code.length > 10) {
      setJoinError('Invalid lobby code');
      return;
    }
    
    setJoinError('');
    onJoinLobby(code);
  };

  return (
    <Sidebar>
      {/* User Info */}
      <div className="p-6 border-b border-outsider-gray-800">
        <div className="space-y-1">
          <p className="text-xs text-outsider-gray-500">LOGGED IN AS</p>
          <p className="text-lg font-light">{username}</p>
        </div>
      </div>
      
      {/* Menu Options */}
      <div className="flex-1 p-6 space-y-4">
        <h2 className="text-xs text-outsider-gray-500 tracking-wider mb-4">MAIN MENU</h2>
        
        {!showJoinForm ? (
          <>
            <button
              onClick={onCreateLobby}
              className="sidebar-item w-full text-left"
            >
              CREATE NEW LOBBY
            </button>
            
            <button
              onClick={() => setShowJoinForm(true)}
              className="sidebar-item w-full text-left"
            >
              JOIN EXISTING LOBBY
            </button>
            
            <div className="pt-4">
              <button
                onClick={() => {}}
                className="sidebar-item w-full text-left text-outsider-gray-600"
              >
                HOW TO PLAY
              </button>
              
              <button
                onClick={() => {}}
                className="sidebar-item w-full text-left text-outsider-gray-600"
              >
                SETTINGS
              </button>
            </div>
          </>
        ) : (
          <form onSubmit={handleJoinSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs text-outsider-gray-500">LOBBY CODE</label>
              <input
                type="text"
                value={lobbyCode}
                onChange={(e) => setLobbyCode(e.target.value)}
                placeholder="ENTER CODE"
                className="input-primary uppercase"
                maxLength={10}
                autoFocus
              />
              {joinError && (
                <p className="text-red-500 text-xs">{joinError}</p>
              )}
            </div>
            
            <div className="flex space-x-2">
              <button type="submit" className="btn-primary flex-1">
                JOIN
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowJoinForm(false);
                  setLobbyCode('');
                  setJoinError('');
                }}
                className="btn-secondary flex-1"
              >
                CANCEL
              </button>
            </div>
          </form>
        )}
      </div>
      
      {/* Logout */}
      <div className="p-6 border-t border-outsider-gray-800">
        <button
          onClick={onLogout}
          className="text-outsider-gray-500 hover:text-outsider-white transition-colors text-sm"
        >
          LOGOUT
        </button>
      </div>
    </Sidebar>
  );
};

export default MainMenuSidebar;