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

  console.log('Klio component state:', {
    isConnected,
    isLoading,
    showDirectorySelection,
    showAnalysisOptions,
    selectedDirectory
  });

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
    
    // Check connection status on mount
    console.log('Klio component mounted, checking connection...');
    const initializeConnection = async () => {
      try {
        const response = await fetch(`${config.apiBaseUrl}/api/v1/auth/google/status`, {
          ...config.fetchOptions
        });
        console.log('Initial connection check response:', response);
        const data = await response.json();
        console.log('Initial connection check data:', data);
        
        if (data.isAuthenticated) {
          console.log('User is authenticated, setting connected state');
          setIsConnected(true);
          await fetchDirectories();
        } else {
          console.log('User is not authenticated, showing connect button');
          setIsConnected(false);
        }
      } catch (error) {
        console.error('Error during initial connection check:', error);
        setIsConnected(false);
      }
    };

    initializeConnection();
  }, [location]);

  const handleCheckConnection = async () => {
    console.log('Checking connection status...');
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/v1/auth/google/status`, {
        ...config.fetchOptions
      });
      console.log('Connection check response:', response);
      const data = await response.json();
      console.log('Connection check data:', data);
      
      const connected = data.isAuthenticated === true;
      console.log('Setting connection state to:', connected);
      setIsConnected(connected);
      
      if (connected) {
        console.log('Connected, fetching directories...');
        await fetchDirectories();
      }
    } catch (error) {
      console.error('Error checking connection:', error);
      setIsConnected(false);
    }
  };

  const handleConnect = async () => {
    console.log('Initiating connection...');
    try {
      setIsLoading(true);
      const response = await fetch(`${config.apiBaseUrl}/api/v1/auth/google/login`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      console.log('Connect response:', response);
      
      if (!response.ok) {
        throw new Error(`Failed to get auth URL: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Connect data:', data);
      
      if (data.auth_url) {
        console.log('Redirecting to auth URL:', data.auth_url);
        // Add message before redirect
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: 'Redirecting you to Google for authentication...'
        }]);
        window.location.href = data.auth_url;
      } else {
        throw new Error('No authentication URL received from server');
      }
    } catch (error) {
      console.error('Error connecting:', error);
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: `Failed to connect: ${error.message}. Please try again.`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchDirectories = async () => {
    console.log('Fetching directories...');
    try {
      setIsLoading(true);
      const response = await fetch(`${config.apiBaseUrl}/api/v1/drive/directories`, {
        ...config.fetchOptions
      });
      
      console.log('Directories response:', response);
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        console.error('Failed to fetch directories:', response.status);
        if (response.status === 401) {
          console.log('Unauthorized, setting connected to false');
          setIsConnected(false);
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: 'Your Google Drive session has expired. Please connect again.'
          }]);
          return;
        }
        throw new Error(`Failed to fetch directories: ${response.status}`);
      }
      
      const directories = await response.json();
      console.log('Directories data:', directories);
      
      if (Array.isArray(directories) && directories.length > 0) {
        console.log('Found directories:', directories);
        setDirectories(directories);
        const directoryList = directories.map(dir => `• ${dir.name}`).join('\n');
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: `Here are your available directories:\n\n${directoryList}`
        }]);
      } else {
        console.log('No directories found in response');
        setDirectories([]);
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: 'I couldn\'t find any directories in your Google Drive.'
        }]);
      }
    } catch (error) {
      console.error('Error fetching directories:', error);
      setIsConnected(false);
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: 'Failed to fetch directories. Please try connecting again.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyze = async (directory) => {
    if (!directory) {
      console.error('handleAnalyze called with no directory');
      return;
    }
    
    try {
      console.log('Starting analysis for directory:', {
        id: directory.id,
        name: directory.name,
        mimeType: directory.mimeType
      });
      setIsLoading(true);
      
      const analyzeUrl = `${config.apiBaseUrl}/api/v1/drive/directories/${directory.id}/analyze`;
      console.log('Making analyze request to:', analyzeUrl);
      
      const response = await fetch(analyzeUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include'
      });

      console.log('Analysis response:', {
        status: response.status,
        ok: response.ok,
        statusText: response.statusText
      });

      if (!response.ok) {
        const errorData = await response.json().catch(e => ({ message: 'Failed to parse error response' }));
        console.error('Analysis failed:', {
          status: response.status,
          error: errorData
        });
        if (response.status === 401 || response.status === 403) {
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: 'I need access to your Google Drive. Please connect your Google account first.'
          }]);
          return;
        }
        throw new Error(errorData.message || `Analysis failed with status ${response.status}`);
      }

      const data = await response.json();
      console.log('Raw analysis data received:', data);
      
      // Calculate total sensitive documents across all age groups
      const totalSensitiveDocuments = [
        data.moreThanThreeYears?.total_sensitive || 0,
        data.oneToThreeYears?.total_sensitive || 0,
        data.lessThanOneYear?.total_sensitive || 0
      ].reduce((sum, count) => sum + count, 0);
      
      // Transform data to match expected structure
      const transformedData = {
        directory: directory,
        docCount: data.processed_files || 0,
        duplicateDocuments: data.total_duplicates || 0,
        sensitiveDocuments: data.total_sensitive_files || 0,
        ageDistribution: {
          moreThanThreeYears: transformAgeGroup(data.moreThanThreeYears),
          oneToThreeYears: transformAgeGroup(data.oneToThreeYears),
          lessThanOneYear: transformAgeGroup(data.lessThanOneYear)
        }
      };
      
      console.log('Transformed data before sending to parent:', transformedData);
      
      // Pass the transformed data to the parent component
      onStatsUpdate(transformedData);

      // Reset UI state after successful analysis
      setShowAnalysisOptions(false);
      setShowDirectorySelection(false);
      setSelectedDirectory(null);

      setMessages(prev => [...prev, {
        type: 'assistant',
        content: `Analysis complete for "${directory.name}". Check the dashboard for detailed insights.`
      }]);
    } catch (error) {
      console.error('Analysis error:', error);
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: `Sorry, I encountered an error during analysis: ${error.message}`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Helper function to transform an age group's data
  const transformAgeGroup = (groupData) => {
    if (!groupData) {
      return {
        types: {},
        risks: {},
        totalSensitive: 0,
        total_documents: 0
      };
    }

    // Transform file types
    const types = {};
    if (groupData.file_types) {
      // Calculate total files for percentage
      const totalFiles = Object.values(groupData.file_types)
        .reduce((sum, files) => sum + (Array.isArray(files) ? files.length : 0), 0);

      Object.entries(groupData.file_types).forEach(([type, files]) => {
        if (Array.isArray(files)) {
          types[type] = {
            count: files.length,
            size: files.reduce((sum, file) => sum + (parseInt(file.size) || 0), 0),
            percentage: totalFiles > 0 ? Math.round((files.length / totalFiles) * 100) : 0,
            files: files
          };
        }
      });
    }

    // Transform risks
    const risks = {};
    if (groupData.sensitive_info) {
      // Calculate total findings for percentage
      const totalFindings = Object.values(groupData.sensitive_info)
        .reduce((sum, findings) => sum + (Array.isArray(findings) ? findings.length : 0), 0);

      Object.entries(groupData.sensitive_info).forEach(([category, findings]) => {
        if (Array.isArray(findings)) {
          risks[category] = {
            count: findings.length,
            files: findings,
            confidence: findings.length > 0 
              ? findings.reduce((sum, finding) => sum + (finding.confidence || 0.8), 0) / findings.length 
              : 0,
            percentage: totalFindings > 0 ? Math.round((findings.length / totalFindings) * 100) : 0
          };
        }
      });
    }

    return {
      types,
      risks,
      totalSensitive: groupData.total_sensitive || 0,
      total_documents: groupData.total_documents || 0
    };
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

  const handleDirectorySelect = async (directory) => {
    console.log('Directory selected:', {
      id: directory.id,
      name: directory.name,
      mimeType: directory.mimeType
    });
    
    // First update the UI state
    setSelectedDirectory(directory);
    setShowDirectorySelection(false);
    
    // Then start the analysis
    await handleAnalyze(directory);
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
              {klioCommands.map((cmd) => (
                <button
                  key={cmd.name}
                  className="command-button"
                  onClick={() => handleCommand({ name: cmd.name })}
                  disabled={isLoading}
                >
                  {cmd.name}
                </button>
              ))}
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