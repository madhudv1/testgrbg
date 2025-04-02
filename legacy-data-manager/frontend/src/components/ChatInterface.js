import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import Auth from './Auth';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authError, setAuthError] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const [currentFolder, setCurrentFolder] = useState(null);
  const [files, setFiles] = useState([]);
  const [analysisResults, setAnalysisResults] = useState(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    console.log('ChatInterface mounted');
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const addMessage = (type, content) => {
    setMessages(prev => [...prev, { type, content }]);
    setInput(''); // Clear input after adding message
  };

  const handleCommand = async (command) => {
    if (!command.trim()) return;

    setIsLoading(true);
    // Split the command into parts but preserve original case for the command string
    const parts = command.split(' ');
    const baseCommand = parts[0].toLowerCase(); // Only lowercase the command word for checking
    const originalCommand = command; // Keep original case for the full command

    // Add user message to chat
    addMessage('user', command);

    try {
      let response;
      switch (baseCommand) {
        case 'directories':
          response = await fetch('http://localhost:8000/api/v1/drive/directories', { credentials: 'include' });
          if (!response.ok) {
            const errorText = await response.text();
            addMessage('assistant', `Error fetching directories: ${response.status} ${response.statusText} - ${errorText}`);
            return;
          }
          const dirsData = await response.json();
          if (dirsData.directories && dirsData.directories.length > 0) {
            const directoriesList = dirsData.directories.map(dir => `- ${dir.name} (ID: ${dir.id})`).join('\n');
            addMessage('assistant', `Here are your top-level directories:\n${directoriesList}`);
          } else {
            addMessage('assistant', 'No directories found.');
          }
          break;

        case 'categorize':
          if (parts.length < 2) {
            addMessage('assistant', 'Please provide a directory ID. Usage: categorize <directory_id>');
            return;
          }
          // Use original command to preserve case of the directory ID
          response = await fetch('http://localhost:8000/api/v1/chat/messages', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ message: originalCommand })
          });
          const result = await response.json();
          
          if (result.type === 'categorization') {
            const summary = result.content.summary;
            let responseText = '📊 Directory Categorization Summary:\n\n';
            
            // File Type Summary
            responseText += '📁 By File Type:\n';
            Object.entries(summary.by_type).forEach(([type, count]) => {
              responseText += `- ${type.charAt(0).toUpperCase() + type.slice(1)}: ${count}\n`;
            });
            
            // Internal/External Summary
            responseText += '\n👥 By Ownership:\n';
            responseText += `- Internal Files: ${summary.internal_files}\n`;
            responseText += `- External Files: ${summary.external_files}\n`;
            
            // Department Summary
            responseText += '\n🏢 By Department:\n';
            Object.entries(summary.by_department).forEach(([dept, count]) => {
              if (count > 0) { // Only show departments with files
                responseText += `- ${dept.charAt(0).toUpperCase() + dept.slice(1)}: ${count}\n`;
              }
            });
            
            // Time-based Summary
            responseText += '\n⏰ By Last Access:\n';
            responseText += `- Recent Files (≤30 days): ${summary.recent_files}\n`;
            responseText += `- Older Files: ${summary.total_files - summary.recent_files}\n`;
            
            // Size-based Summary
            responseText += '\n📦 By Size:\n';
            responseText += `- Large Files (>10MB): ${summary.large_files}\n`;
            
            // Total Statistics
            responseText += '\n📈 Total Statistics:\n';
            responseText += `- Total Files: ${summary.total_files}\n`;
            responseText += `- Total Size: ${(summary.total_size / (1024 * 1024)).toFixed(2)} MB\n`;
            
            addMessage('assistant', responseText);
          } else {
            addMessage('assistant', result.content);
          }
          break;

        case 'find':
          if (parts.length < 2) {
            addMessage('assistant', 'Please provide a search query. Usage: find <query>');
            return;
          }
          // Use original command to preserve case of the search query
          response = await fetch('/api/v1/chat/messages', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ message: originalCommand })
          });
          const searchResult = await response.json();
          addMessage('assistant', searchResult.content);
          break;

        case 'help':
          addMessage('assistant', `Available commands:
- help: Show this help message
- directories: List your top-level folders
- inactive: List inactive files
- status: Check authentication status
- categorize <directory_id>: Categorize files in a directory`);
          break;

        case 'inactive':
          response = await fetch('http://localhost:8000/api/v1/drive/files/inactive', { credentials: 'include' });
          const inactiveData = await response.json();
          if (inactiveData.files && inactiveData.files.length > 0) {
            const inactiveList = inactiveData.files.map(file => 
              `- ${file.name} (ID: ${file.id}, Last modified: ${file.modifiedTime})`
            ).join('\n');
            addMessage('assistant', `Here are your inactive files:\n${inactiveList}`);
          } else {
            addMessage('assistant', 'No inactive files found.');
          }
          break;

        case 'status':
          response = await fetch('http://localhost:8000/api/v1/drive/auth/status', { credentials: 'include' });
          if (!response.ok) {
            const errorText = await response.text();
            addMessage('assistant', `Error fetching status: ${response.status} ${response.statusText} - ${errorText}`);
            return;
          }
          const statusData = await response.json();
          setIsAuthenticated(statusData.authenticated);
          if (!statusData.authenticated) {
            setAuthError(true);
            addMessage('assistant', 'You are not authenticated. Please authenticate to continue.');
            return;
          }
          addMessage('assistant', 'You are authenticated and ready to use the system.');
          break;
      }
    } catch (error) {
      addMessage('assistant', `Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    handleCommand(input);
  };

  const handleAuthenticated = () => {
    console.log('Handling authentication in ChatInterface');
    setIsAuthenticated(true);
    setAuthError(false);
    addMessage('assistant', 'Welcome! You are authenticated. Type "help" for commands.');
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  };

  console.log('ChatInterface render - isAuthenticated:', isAuthenticated, 'authError:', authError);

  if (!isAuthenticated || authError) {
    return (
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Welcome to Legacy Data Manager</h2>
          {authError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
              Authentication error. Please re-authenticate to continue.
            </div>
          )}
          <Auth onAuthenticated={handleAuthenticated} />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 bg-opacity-50 backdrop-blur-xl shadow-2xl rounded-xl border border-gray-700/50">
      <div className="p-6 border-b border-gray-700/50">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 rounded-full bg-gradient-to-r from-blue-300 to-blue-600"></div>
          <h2 className="text-xl font-semibold text-white">Legacy Data Manager</h2>
        </div>
      </div>
      
      <div className="h-[32rem] overflow-y-auto p-6 bg-gray-900/50 space-y-6">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} group`}
          >
            {message.type !== 'user' && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-300 to-blue-600 flex items-center justify-center text-white text-sm font-medium mr-3 shadow-lg">
                A
              </div>
            )}
            <div
              className={`max-w-[80%] ${message.type === 'user' ? 'order-1' : 'order-2'}`}
            >
              <div
                className={`p-4 rounded-2xl shadow-lg backdrop-blur-sm ${
                  message.type === 'user'
                    ? 'bg-gradient-to-r from-pink-500 to-purple-600 text-white ml-4'
                    : message.type === 'error'
                    ? 'bg-red-500/10 border border-red-500/50 text-red-500'
                    : 'bg-gradient-to-r from-blue-300 via-blue-400 to-blue-600 text-white'
                }`}
              >
                <pre className="whitespace-pre-wrap font-sans">{message.content}</pre>
              </div>
              <div className={`text-xs text-gray-400 mt-1 ${message.type === 'user' ? 'text-right mr-4' : 'ml-4'}`}>
                {new Date().toLocaleTimeString()}
              </div>
            </div>
            {message.type === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-pink-500 to-purple-600 flex items-center justify-center text-white text-sm font-medium ml-3 shadow-lg">
                U
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center justify-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce [animation-delay:-0.3s]"></div>
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce [animation-delay:-0.15s]"></div>
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce"></div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-6 border-t border-gray-700/50 bg-gray-800/50">
        <div className="mb-4 flex flex-wrap gap-2">
          <button 
            onClick={() => setInput('help')}
            className="px-3 py-1 text-sm bg-gradient-to-r from-blue-300/10 to-blue-600/10 hover:from-blue-300/20 hover:to-blue-600/20 text-gray-300 rounded-full transition-all border border-blue-500/20"
          >
            help
          </button>
          <button 
            onClick={() => setInput('directories')}
            className="px-3 py-1 text-sm bg-gradient-to-r from-blue-300/10 to-blue-600/10 hover:from-blue-300/20 hover:to-blue-600/20 text-gray-300 rounded-full transition-all border border-blue-500/20"
          >
            directories
          </button>
          <button 
            onClick={() => setInput('status')}
            className="px-3 py-1 text-sm bg-gradient-to-r from-blue-300/10 to-blue-600/10 hover:from-blue-300/20 hover:to-blue-600/20 text-gray-300 rounded-full transition-all border border-blue-500/20"
          >
            status
          </button>
          <button 
            onClick={() => setInput('inactive')}
            className="px-3 py-1 text-sm bg-gradient-to-r from-blue-300/10 to-blue-600/10 hover:from-blue-300/20 hover:to-blue-600/20 text-gray-300 rounded-full transition-all border border-blue-500/20"
          >
            inactive
          </button>
        </div>
        <form onSubmit={handleSubmit} className="relative">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a command or click one above..."
            className="w-full p-4 bg-gray-900/50 backdrop-blur-sm border border-gray-700/50 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400/50 focus:border-transparent pr-24"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading}
            className="absolute right-2 top-2 px-4 py-2 bg-gradient-to-r from-pink-500 to-purple-600 text-white rounded-lg hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-purple-500/50 disabled:opacity-50 transition-all duration-200 backdrop-blur-sm"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatInterface;
