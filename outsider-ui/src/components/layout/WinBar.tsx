import React, { useEffect, useState } from 'react';

interface WinBarProps {
  apiUrl?: string;
}

interface GameStats {
  human_wins: number;
  ai_wins: number;
  total_games: number;
}

const WinBar: React.FC<WinBarProps> = ({ apiUrl = 'http://localhost:5000' }) => {
  const [stats, setStats] = useState<GameStats>({
    human_wins: 0,
    ai_wins: 0,
    total_games: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch initial stats
    fetchStats();

    // Poll for updates every 10 seconds
    const interval = setInterval(fetchStats, 10000);

    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const winPercentage = stats.total_games > 0 
    ? (stats.human_wins / stats.total_games * 100).toFixed(1)
    : '0.0';

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-outsider-black border-b border-outsider-gray-800">
      <div className="flex items-center justify-between px-8 py-4">
        <div className="flex items-center space-x-8">
          <h1 className="text-xl font-light tracking-wider">THE OUTSIDER</h1>
          
          {!loading && (
            <div className="flex items-center space-x-6 text-sm">
              <div className="flex items-center space-x-2">
                <span className="text-outsider-gray-500">HUMANS</span>
                <span className="font-mono text-lg">{stats.human_wins}</span>
              </div>
              
              <div className="w-px h-6 bg-outsider-gray-700" />
              
              <div className="flex items-center space-x-2">
                <span className="font-mono text-lg">{stats.ai_wins}</span>
                <span className="text-outsider-gray-500">AI</span>
              </div>
              
              <div className="w-px h-6 bg-outsider-gray-700" />
              
              <div className="text-outsider-gray-500">
                <span className="font-mono">{winPercentage}%</span> HUMAN WIN RATE
              </div>
            </div>
          )}
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="text-xs text-outsider-gray-600">
            {stats.total_games} GAMES PLAYED
          </div>
        </div>
      </div>
      
      {/* Progress bar showing win ratio */}
      <div className="h-px bg-outsider-gray-800 relative">
        <div 
          className="absolute top-0 left-0 h-full bg-outsider-white transition-all duration-1000"
          style={{ width: `${winPercentage}%` }}
        />
      </div>
    </div>
  );
};

export default WinBar;