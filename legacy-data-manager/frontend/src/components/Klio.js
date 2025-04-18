import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import config from '../config';
import '../styles/Klio.css';

const klioCommands = [
  { name: 'List Directories', description: 'Show available directories' },
  { name: 'Analyze', description: 'Analyze selected directory' },
  { name: 'Clean', description: 'Clean up selected directory' }
];

const analysisOptions = [
  { id: 'age', name: 'Age Based', enabled: true },
  { id: 'ownership', name: 'Ownership Based', enabled: false },
  { id: 'sensitive', name: 'Sensitive Info', enabled: false },
  { id: 'usage', name: 'Usage Pattern', enabled: false },
  { id: 'filetype', name: 'File Type', enabled: true }
];

const Klio = ({ onCommand, onStatsUpdate }) => {
  const [message, setMessage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [directories, setDirectories] = useState([]);
  const [selectedDirectory, setSelectedDirectory] = useState(null);
  const [messages, setMessages] = useState([
    {
      type: 'assistant',
      content: 'Welcome! Let me help you manage your documents.'
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [showDirectorySelection, setShowDirectorySelection] = useState(false);
  const [showAnalysisOptions, setShowAnalysisOptions] = useState(false);
  const [error, setError] = useState(null);
  
  const location = useLocation();

  useEffect(() => {
    // Check for auth error in URL params
    const urlParams = new URLSearchParams(window.location.search);
    const authError = urlParams.get('auth');
    const errorMessage = urlParams.get('message');
    
    if (authError === 'error') {
      setError(errorMessage || 'Failed to authenticate with Google Drive');
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: `Authentication failed: ${errorMessage || 'Please try connecting again.'}`
      }]);
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (authError === 'success') {
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: 'Successfully connected to Google Drive! I can help you analyze your documents. Try these commands:\n\n• "list directories" - Show available directories\n• "scan directory" - Analyze files in a directory\n• "help" - Show all available commands'
      }]);
      setIsConnected(true);
      window.history.replaceState({}, document.title, window.location.pathname);
      fetchDirectories();
    }
    
    // Check connection status
    handleCheckConnection();
  }, [location]);

  const handleCheckConnection = async () => {
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/v1/drive/auth/status`);
      const data = await response.json();
      
      if (!response.ok) {
        setIsConnected(false);
        if (response.status === 401) {
          setError("Google Drive session expired. Please reconnect.");
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: 'Your Google Drive session has expired. Please connect again.'
          }]);
        } else {
          setError(`Connection error: ${data.detail || 'Unknown error'}`);
        }
        return false;
      }
      
      setIsConnected(data.authenticated);
      setError(null);
      return data.authenticated;
    } catch (error) {
      console.error('Error checking connection:', error);
      setIsConnected(false);
      setError("Failed to check Google Drive connection status");
      return false;
    }
  };

  const handleConnect = async () => {
    try {
      setError(null);
      const response = await fetch(`${config.apiBaseUrl}/api/v1/drive/auth/url`);
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to get authentication URL');
      }
      
      // Store current URL to handle redirect back after auth
      localStorage.setItem('klio_redirect', window.location.href);
      window.location.href = data.auth_url;
    } catch (error) {
      console.error('Failed to get auth URL:', error);
      setError(error.message);
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: `Sorry, I encountered an error while trying to connect to Google Drive: ${error.message}`
      }]);
    }
  };

  const fetchDirectories = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${config.apiBaseUrl}/api/v1/drive/directories`);
      
      if (!response.ok) {
        if (response.status === 401) {
          setIsConnected(false);
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: 'Your Google Drive session has expired. Please connect again.'
          }]);
          return;
        }
        throw new Error('Failed to fetch directories');
      }
      
      const data = await response.json();
      setDirectories(data.directories || []);
      
      if (data.directories && data.directories.length > 0) {
        const directoryList = data.directories.map(dir => `• ${dir.name}`).join('\n');
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: `Here are your available directories:\n\n${directoryList}`
        }]);
      } else {
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: 'I couldn\'t find any directories in your Google Drive.'
        }]);
      }
    } catch (error) {
      console.error('Error fetching directories:', error);
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: 'Sorry, I encountered an error while trying to list directories.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyze = async (directory) => {
    if (!directory) return;
    
    try {
      setIsLoading(true);
      const response = await fetch(`${config.apiBaseUrl}/api/v1/drive/directories/${directory.id}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        if (response.status === 401 || response.status === 403) {
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: 'I need access to your Google Drive. Please connect your Google account first.'
          }]);
          return;
        }
        throw new Error(errorData.message || 'Analysis failed');
      }

      const data = await response.json();
      console.log('Raw analysis data:', data);

      // Process the analysis data into stats
      const stats = {
        staleDocuments: data.staleCount || 0,
        duplicateDocuments: data.duplicateCount || 0,
        sensitiveDocuments: data.sensitiveCount || 0,
        ageDistribution: {
          lessThanOneYear: data.ageDistribution?.lessThanOneYear || 0,
          oneToThreeYears: data.ageDistribution?.oneToThreeYears || 0,
          moreThanThreeYears: data.ageDistribution?.moreThanThreeYears || 0
        },
        fileTypes: {
          documents: { count: data.fileTypes?.documents?.count || 0, size: data.fileTypes?.documents?.size || 0 },
          spreadsheets: { count: data.fileTypes?.spreadsheets?.count || 0, size: data.fileTypes?.spreadsheets?.size || 0 },
          images: { count: data.fileTypes?.images?.count || 0, size: data.fileTypes?.images?.size || 0 },
          presentations: { count: data.fileTypes?.presentations?.count || 0, size: data.fileTypes?.presentations?.size || 0 },
          pdfs: { count: data.fileTypes?.pdfs?.count || 0, size: data.fileTypes?.pdfs?.size || 0 },
          others: { count: data.fileTypes?.others?.count || 0, size: data.fileTypes?.others?.size || 0 }
        }
      };

      console.log('Processed stats:', stats);
      onStatsUpdate(stats);

      // Reset UI state after successful analysis
      setShowAnalysisOptions(false);
      setShowDirectorySelection(false);
      setSelectedDirectory(null);

      setMessages(prev => [...prev, {
        type: 'assistant',
        content: 'Analysis complete. Check the dashboard for detailed insights.'
      }]);
    } catch (error) {
      console.error('Analysis error:', error);
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClean = async () => {
    if (!selectedDirectory) return;
    
    try {
      setIsLoading(true);
      // Implement cleaning logic here
      // This will depend on your backend API structure
    } catch (error) {
      console.error('Error cleaning directory:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCommand = (cmd) => {
    onCommand(cmd);
    
    switch (cmd.name.toLowerCase()) {
      case 'list directories':
        fetchDirectories();
        break;
      case 'analyze':
        setShowDirectorySelection(true);
        setShowAnalysisOptions(false);
        setSelectedDirectory(null);
        break;
      case 'clean':
        if (selectedDirectory) {
          handleClean();
        } else {
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: 'Please select a directory first.'
          }]);
        }
        break;
      default:
        console.warn('Unknown command:', cmd.name);
    }
  };

  const handleDirectorySelect = (directory) => {
    setSelectedDirectory(directory);
    setShowDirectorySelection(false);
    setShowAnalysisOptions(true);
  };

  const handleMessageSubmit = (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    // Add user message
    setMessages(prev => [...prev, {
      type: 'user',
      content: message
    }]);

    const lowerMessage = message.toLowerCase();

    if (!isConnected) {
      if (lowerMessage.includes('connect') || lowerMessage.includes('yes')) {
        handleConnect();
      } else {
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: 'I need access to your Google Drive to help you manage your documents. Just say "connect" when you\'re ready.'
        }]);
      }
    } else {
      // Handle connected state commands
      if (lowerMessage === 'list directories') {
        fetchDirectories();
      } else if (lowerMessage.startsWith('scan ')) {
        const directoryName = message.substring(5).trim();
        const directory = directories.find(dir => dir.name.toLowerCase() === directoryName.toLowerCase());
        if (directory) {
          handleAnalyze(directory);
        } else {
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: `I couldn't find a directory named "${directoryName}". Please try "list directories" to see available directories.`
          }]);
        }
      } else if (lowerMessage === 'help') {
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: 'Here are the available commands:\n\n' +
                  '• "list directories" - Show available directories\n' +
                  '• "scan [directory name]" - Analyze files in a directory\n' +
                  '• "help" - Show this help message'
        }]);
      } else {
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: 'I didn\'t understand that command. Try "help" to see available commands.'
        }]);
      }
    }

    setMessage('');
  };

  return (
    <div className="klio-container">
      <div className="klio-header">
        <div className="klio-header-left">
          <div className="klio-avatar">K</div>
          <div className="klio-name">Klio</div>
        </div>
        <button className="klio-more">⋯</button>
      </div>
      
      <div className="klio-content">
        <div className="chat-messages">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.type}`}>
              {msg.type === 'assistant' && (
                <div className="message-avatar">K</div>
              )}
              <div className="message-content">{msg.content}</div>
            </div>
          ))}
        </div>

        {!isConnected ? (
          <div className="connection-prompt">
            <button onClick={handleConnect} className="connect-button">
              Connect Google Drive
            </button>
          </div>
        ) : (
          <>
            <div className="command-buttons">
              <button
                className="command-button"
                onClick={() => handleCommand({ name: 'List Directories' })}
                disabled={isLoading}
              >
                List Directories
              </button>
              <button
                className="command-button"
                onClick={() => handleCommand({ name: 'Analyze' })}
                disabled={isLoading}
              >
                Analyze
              </button>
              <button
                className="command-button"
                onClick={() => handleCommand({ name: 'Clean' })}
                disabled={isLoading}
              >
                Clean
              </button>
            </div>

            {showDirectorySelection && (
              <div className="directory-selection">
                <h3>Select Directory to Analyze</h3>
                <button
                  className="directory-option"
                  onClick={() => handleDirectorySelect({ id: 'root', name: 'Entire Drive' })}
                >
                  Entire Drive
                </button>
                {directories.map((dir) => (
                  <button
                    key={dir.id}
                    className="directory-option"
                    onClick={() => handleDirectorySelect(dir)}
                  >
                    {dir.name}
                  </button>
                ))}
              </div>
            )}

            {showAnalysisOptions && (
              <div className="analysis-options">
                <h3>Select Analysis Type</h3>
                {analysisOptions.map((option) => (
                  <button
                    key={option.id}
                    className={`analysis-option ${option.enabled ? '' : 'disabled'}`}
                    onClick={() => option.enabled && handleAnalyze(selectedDirectory)}
                    disabled={!option.enabled || isLoading}
                  >
                    {option.name}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
      
      <form onSubmit={handleMessageSubmit} className="klio-input">
        <input
          type="text"
          placeholder="Type a message..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
      </form>
    </div>
  );
};

export default Klio; 