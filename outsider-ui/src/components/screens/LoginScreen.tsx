import React, { useState } from 'react';

interface LoginScreenProps {
  onLogin: (username: string) => void;
}

const LoginScreen: React.FC<LoginScreenProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate username
    const trimmedUsername = username.trim();
    if (!trimmedUsername) {
      setError('Please enter a name');
      return;
    }
    
    if (trimmedUsername.length < 2) {
      setError('Name must be at least 2 characters');
      return;
    }
    
    if (trimmedUsername.length > 20) {
      setError('Name must be 20 characters or less');
      return;
    }
    
    // Check for valid characters
    if (!/^[a-zA-Z0-9_-]+$/.test(trimmedUsername)) {
      setError('Name can only contain letters, numbers, - and _');
      return;
    }
    
    setError('');
    setIsLoading(true);
    
    // Simulate async login
    setTimeout(() => {
      onLogin(trimmedUsername);
    }, 500);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-md w-full space-y-8">
        {/* Logo/Title */}
        <div className="text-center space-y-2">
          <h1 className="text-6xl font-light tracking-wider">THE OUTSIDER</h1>
          <p className="text-outsider-gray-500 text-sm tracking-wide">
            A GAME OF DEDUCTION AND DECEPTION
          </p>
        </div>
        
        {/* Login Form */}
        <form onSubmit={handleSubmit} className="mt-12 space-y-6">
          <div className="space-y-4">
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="ENTER YOUR NAME"
              className="input-primary text-center tracking-wider"
              maxLength={20}
              disabled={isLoading}
              autoFocus
            />
            
            {error && (
              <p className="text-red-500 text-sm text-center">{error}</p>
            )}
          </div>
          
          <button
            type="submit"
            disabled={isLoading}
            className="btn-primary w-full tracking-wider"
          >
            {isLoading ? 'JOINING...' : 'JOIN GAME'}
          </button>
        </form>
        
        {/* Instructions */}
        <div className="mt-12 space-y-2 text-center text-outsider-gray-600 text-xs">
          <p>FIND THE AI OUTSIDER WHO DOESN'T KNOW THE LOCATION</p>
          <p>OR BLEND IN AS THE OUTSIDER AND GUESS THE SECRET</p>
        </div>
      </div>
    </div>
  );
};

export default LoginScreen;