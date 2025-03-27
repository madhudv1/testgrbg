import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import Auth from './Auth';

const ChatInterface = () => {
  const [messages, setMessages] = useState([{
    type: 'bot',
    content: 'Welcome! You can use the following commands:\n- help: Show available commands\n- list: List recent files\n- inactive: Show inactive files\n- find <filename>: Search for a specific file\n- status: Check authentication status'
  }]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authError, setAuthError] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    console.log('ChatInterface mounted');
    checkAuthStatus();
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const checkAuthStatus = async () => {
    try {
      console.log('Checking auth status in ChatInterface...');
      const response = await axios.get('http://localhost:8000/api/v1/drive/auth/status', {
        withCredentials: true
      });
      console.log('Auth status response:', response.data);
      setIsAuthenticated(response.data.authenticated);
      if (!response.data.authenticated) {
        setAuthError(true);
      }
    } catch (error) {
      console.error('Error checking auth status:', error);
      setAuthError(true);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { type: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/api/v1/chat/message', 
        { message: userMessage },
        { withCredentials: true }
      );

      setMessages(prev => [...prev, { type: 'bot', content: response.data.content }]);
    } catch (error) {
      console.error('Error sending message:', error);
      if (error.response?.status === 401) {
        setAuthError(true);
        setMessages(prev => [...prev, { 
          type: 'bot', 
          content: 'Authentication error. Please click the "Re-authenticate" button below to fix this.' 
        }]);
      } else {
        setMessages(prev => [...prev, { 
          type: 'bot', 
          content: 'Sorry, I encountered an error. Please try again.' 
        }]);
      }
    } finally {
      setIsLoading(false);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  };

  const handleAuthenticated = () => {
    console.log('Handling authentication in ChatInterface');
    setIsAuthenticated(true);
    setAuthError(false);
    setMessages([{
      type: 'bot',
      content: 'Welcome! You are now authenticated with Google Drive. You can use the following commands:\n- help: Show available commands\n- list: List recent files\n- inactive: Show inactive files\n- find <filename>: Search for a specific file\n- status: Check authentication status'
    }]);
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
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      <div className="h-[600px] overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.type === 'user'
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-3">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSubmit} className="border-t p-4">
        <div className="flex space-x-4">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
            disabled={isLoading}
            autoFocus
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-primary-500 text-white px-6 py-2 rounded-lg hover:bg-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface; 