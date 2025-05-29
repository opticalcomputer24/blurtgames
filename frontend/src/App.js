import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import { jwtDecode } from 'jwt-decode';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Utility function to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('blurt_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// Login Component
const Login = ({ onLogin }) => {
  const [formData, setFormData] = useState({ username: '', posting_key: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API}/auth/login`, {
        username: formData.username,
        posting_key: formData.posting_key
      });

      localStorage.setItem('blurt_token', response.data.access_token);
      localStorage.setItem('blurt_username', response.data.username);
      onLogin(response.data.username);
    } catch (error) {
      console.error('Login failed:', error);
      setError(error.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl border border-white/20">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">🧩 Blurt Quest</h1>
          <p className="text-blue-200">Puzzle for Tokens</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Blurt Username
            </label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20"
              placeholder="Enter your Blurt username"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Posting Key
            </label>
            <input
              type="password"
              value={formData.posting_key}
              onChange={(e) => setFormData({ ...formData, posting_key: e.target.value })}
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20"
              placeholder="Enter your posting key"
              required
            />
          </div>

          {error && (
            <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-3 text-red-200 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-400/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
          >
            {loading ? 'Authenticating...' : 'Sign In with Blurt'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-blue-200">
          <p>🔐 Secure authentication with Blurt blockchain</p>
          <p className="mt-1">Complete puzzles to earn BLURT tokens!</p>
        </div>
      </div>
    </div>
  );
};

// Game Dashboard Component
const GameDashboard = ({ username, onLogout }) => {
  const [userProfile, setUserProfile] = useState(null);
  const [currentLevel, setCurrentLevel] = useState(null);
  const [gameState, setGameState] = useState('dashboard'); // dashboard, playing, results
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(60);
  const [levelResult, setLevelResult] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchUserProfile();
    fetchLeaderboard();
  }, []);

  const fetchUserProfile = async () => {
    try {
      const response = await axios.get(`${API}/user/profile`, {
        headers: getAuthHeaders()
      });
      setUserProfile(response.data);
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      if (error.response?.status === 401) {
        onLogout();
      }
    }
  };

  const fetchLeaderboard = async () => {
    try {
      const response = await axios.get(`${API}/game/leaderboard`);
      setLeaderboard(response.data.leaderboard);
    } catch (error) {
      console.error('Failed to fetch leaderboard:', error);
    }
  };

  const startLevel = async (level) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/game/level/${level}`, {
        headers: getAuthHeaders()
      });
      
      setQuestions(response.data.questions);
      setCurrentLevel(level);
      setAnswers(new Array(response.data.questions.length).fill(-1));
      setCurrentQuestion(0);
      setTimeRemaining(level * 30 + 60); // More time for higher levels
      setGameState('playing');
    } catch (error) {
      console.error('Failed to start level:', error);
      alert(error.response?.data?.detail || 'Failed to start level');
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = (answerIndex) => {
    const newAnswers = [...answers];
    newAnswers[currentQuestion] = answerIndex;
    setAnswers(newAnswers);

    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else {
      submitLevel(newAnswers);
    }
  };

  const submitLevel = async (finalAnswers) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/game/level/${currentLevel}/submit`, {
        answers: finalAnswers,
        time_taken: (currentLevel * 30 + 60) - timeRemaining
      }, {
        headers: getAuthHeaders()
      });

      setLevelResult(response.data);
      setGameState('results');
      await fetchUserProfile(); // Refresh profile
      await fetchLeaderboard(); // Refresh leaderboard
    } catch (error) {
      console.error('Failed to submit level:', error);
      alert('Failed to submit answers');
    } finally {
      setLoading(false);
    }
  };

  const backToDashboard = () => {
    setGameState('dashboard');
    setCurrentLevel(null);
    setQuestions([]);
    setAnswers([]);
    setCurrentQuestion(0);
    setLevelResult(null);
  };

  // Timer effect
  useEffect(() => {
    if (gameState === 'playing' && timeRemaining > 0) {
      const timer = setTimeout(() => {
        setTimeRemaining(timeRemaining - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else if (gameState === 'playing' && timeRemaining === 0) {
      submitLevel(answers);
    }
  }, [timeRemaining, gameState]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getRewardForLevel = (level) => level * 1.0;

  if (loading && gameState === 'dashboard') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  // Results Screen
  if (gameState === 'results' && levelResult) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 px-4 py-8">
        <div className="max-w-2xl mx-auto bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl border border-white/20">
          <div className="text-center">
            <div className="text-6xl mb-4">
              {levelResult.level_completed ? '🎉' : '😞'}
            </div>
            <h2 className="text-3xl font-bold text-white mb-2">
              {levelResult.level_completed ? 'Level Completed!' : 'Level Failed'}
            </h2>
            <p className="text-blue-200 mb-6">
              Level {levelResult.level} - {levelResult.level_completed ? 'Well done!' : 'Try again!'}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-white/5 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-white">{levelResult.correct_answers}</div>
              <div className="text-blue-200">Correct Answers</div>
            </div>
            <div className="bg-white/5 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-white">{levelResult.score}</div>
              <div className="text-blue-200">Points Earned</div>
            </div>
          </div>

          {levelResult.level_completed && levelResult.reward_earned > 0 && (
            <div className="bg-gradient-to-r from-yellow-600/20 to-orange-600/20 border border-yellow-500/30 rounded-lg p-4 mb-6">
              <div className="text-center">
                <div className="text-2xl">🏆</div>
                <div className="text-lg font-semibold text-yellow-200">
                  Reward Earned: {levelResult.reward_earned} BLURT
                </div>
                <div className="text-sm text-yellow-300">
                  Reward will be distributed manually by witness
                </div>
              </div>
            </div>
          )}

          <div className="flex gap-4">
            <button
              onClick={backToDashboard}
              className="flex-1 bg-gradient-to-r from-gray-600 to-gray-700 text-white py-3 px-6 rounded-lg font-semibold hover:from-gray-700 hover:to-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-400/50 transition-all duration-200"
            >
              Back to Dashboard
            </button>
            {levelResult.next_level_unlocked && (
              <button
                onClick={() => startLevel(currentLevel + 1)}
                className="flex-1 bg-gradient-to-r from-green-600 to-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-green-700 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-green-400/50 transition-all duration-200"
              >
                Next Level
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Game Playing Screen
  if (gameState === 'playing' && questions.length > 0) {
    const question = questions[currentQuestion];
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 mb-6 shadow-2xl border border-white/20">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold text-white">Level {currentLevel}</h2>
                <p className="text-blue-200">Question {currentQuestion + 1} of {questions.length}</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-white">{formatTime(timeRemaining)}</div>
                <div className="text-blue-200">Time Remaining</div>
              </div>
            </div>
            
            {/* Progress Bar */}
            <div className="mt-4 bg-white/10 rounded-full h-2">
              <div 
                className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${((currentQuestion + 1) / questions.length) * 100}%` }}
              ></div>
            </div>
          </div>

          {/* Question */}
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl border border-white/20">
            <div className="mb-6">
              <div className="inline-block bg-gradient-to-r from-blue-500 to-purple-500 text-white px-3 py-1 rounded-full text-sm font-semibold mb-4">
                {question.category.toUpperCase()}
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">{question.question}</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {question.options.map((option, index) => (
                <button
                  key={index}
                  onClick={() => submitAnswer(index)}
                  className="p-4 bg-white/5 hover:bg-white/10 border border-white/20 rounded-lg text-white text-left transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                >
                  <div className="flex items-center">
                    <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold mr-3">
                      {String.fromCharCode(65 + index)}
                    </div>
                    <span>{option}</span>
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-6 flex justify-between items-center">
              <div className="text-blue-200">
                Points for this question: {question.points}
              </div>
              {timeRemaining <= 10 && (
                <div className="text-red-400 font-bold animate-pulse">
                  ⏰ Hurry up!
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Dashboard Screen
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 px-4 py-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 mb-8 shadow-2xl border border-white/20">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">🧩 Blurt Quest</h1>
              <p className="text-blue-200">Welcome back, {username}!</p>
            </div>
            <button
              onClick={onLogout}
              className="bg-red-500/20 hover:bg-red-500/30 text-red-200 px-4 py-2 rounded-lg border border-red-500/30 transition-all duration-200"
            >
              Logout
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* User Stats */}
          <div className="lg:col-span-1">
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 shadow-2xl border border-white/20 mb-6">
              <h2 className="text-2xl font-bold text-white mb-4">Your Progress</h2>
              {userProfile && (
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-blue-200">Current Level:</span>
                    <span className="text-white font-bold">{userProfile.current_level}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-blue-200">Total Score:</span>
                    <span className="text-white font-bold">{userProfile.total_score}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-blue-200">Levels Completed:</span>
                    <span className="text-white font-bold">{userProfile.levels_completed}</span>
                  </div>
                  <div className="bg-white/10 rounded-full h-3 mt-4">
                    <div 
                      className="bg-gradient-to-r from-green-500 to-blue-500 h-3 rounded-full"
                      style={{ width: `${(userProfile.levels_completed / 10) * 100}%` }}
                    ></div>
                  </div>
                  <div className="text-center text-blue-200 text-sm">
                    {userProfile.levels_completed}/10 Levels Complete
                  </div>
                </div>
              )}
            </div>

            {/* Leaderboard */}
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 shadow-2xl border border-white/20">
              <h2 className="text-2xl font-bold text-white mb-4">🏆 Leaderboard</h2>
              <div className="space-y-2">
                {leaderboard.slice(0, 5).map((player, index) => (
                  <div key={player.username} className="flex justify-between items-center p-2 bg-white/5 rounded-lg">
                    <div className="flex items-center">
                      <span className="text-2xl mr-2">
                        {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}`}
                      </span>
                      <span className="text-white font-semibold">{player.username}</span>
                    </div>
                    <span className="text-blue-200">{player.total_score}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Game Levels */}
          <div className="lg:col-span-2">
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 shadow-2xl border border-white/20">
              <h2 className="text-2xl font-bold text-white mb-6">Game Levels</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {Array.from({ length: 10 }, (_, i) => i + 1).map((level) => {
                  const isUnlocked = userProfile && level <= userProfile.current_level;
                  const isCompleted = userProfile && userProfile.completed_levels.includes(level);
                  const reward = getRewardForLevel(level);

                  return (
                    <div key={level} className="text-center">
                      <button
                        onClick={() => isUnlocked && startLevel(level)}
                        disabled={!isUnlocked}
                        className={`w-full h-24 rounded-xl font-bold text-lg transition-all duration-200 ${
                          isCompleted 
                            ? 'bg-gradient-to-br from-green-500 to-green-600 text-white shadow-lg' 
                            : isUnlocked
                            ? 'bg-gradient-to-br from-blue-500 to-purple-600 text-white hover:scale-105 shadow-lg'
                            : 'bg-gray-600/50 text-gray-400 cursor-not-allowed'
                        }`}
                      >
                        {isCompleted ? '✅' : level}
                      </button>
                      <div className="mt-2">
                        <div className="text-white font-semibold">Level {level}</div>
                        <div className="text-blue-200 text-sm">{reward} BLURT</div>
                        <div className="text-blue-300 text-xs">
                          {level <= 3 ? 'Beginner' : level <= 6 ? 'Intermediate' : level <= 8 ? 'Advanced' : 'Expert'}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-8 text-center">
                <div className="bg-gradient-to-r from-yellow-600/20 to-orange-600/20 border border-yellow-500/30 rounded-lg p-4">
                  <div className="text-lg font-semibold text-yellow-200 mb-2">💰 Reward System</div>
                  <div className="text-sm text-yellow-300">
                    Complete levels to earn BLURT tokens! Rewards increase with difficulty.
                    <br />
                    Level 1-5: 1-5 BLURT • Level 6-10: 6-10 BLURT
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('blurt_token');
    const username = localStorage.getItem('blurt_username');
    
    if (token && username) {
      try {
        const decoded = jwtDecode(token);
        const currentTime = Date.now() / 1000;
        
        if (decoded.exp > currentTime) {
          setUser(username);
        } else {
          // Token expired
          localStorage.removeItem('blurt_token');
          localStorage.removeItem('blurt_username');
        }
      } catch (error) {
        // Invalid token
        localStorage.removeItem('blurt_token');
        localStorage.removeItem('blurt_username');
      }
    }
    
    setLoading(false);
  }, []);

  const handleLogin = (username) => {
    setUser(username);
  };

  const handleLogout = () => {
    localStorage.removeItem('blurt_token');
    localStorage.removeItem('blurt_username');
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="App">
      {user ? (
        <GameDashboard username={user} onLogout={handleLogout} />
      ) : (
        <Login onLogin={handleLogin} />
      )}
    </div>
  );
}

export default App;
