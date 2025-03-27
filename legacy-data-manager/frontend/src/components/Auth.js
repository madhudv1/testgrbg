import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Auth = ({ onAuthenticated }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    console.log('Auth component mounted');
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      console.log('Checking auth status...');
      const response = await axios.get('http://localhost:8000/api/v1/drive/auth/status', {
        withCredentials: true
      });
      console.log('Auth status response:', response.data);
      setIsAuthenticated(response.data.authenticated);
    } catch (error) {
      console.error('Error checking auth status:', error);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAuth = async () => {
    try {
      console.log('Getting auth URL...');
      const response = await axios.get('http://localhost:8000/api/v1/drive/auth/url', {
        withCredentials: true
      });
      console.log('Auth URL:', response.data.auth_url);
      
      // Open the auth URL in a new window
      const authWindow = window.open(response.data.auth_url, '_blank');
      
      // Poll for authentication status
      const pollInterval = setInterval(async () => {
        try {
          console.log('Polling auth status...');
          const statusResponse = await axios.get('http://localhost:8000/api/v1/drive/auth/status', {
            withCredentials: true
          });
          console.log('Poll response:', statusResponse.data);
          
          if (statusResponse.data.authenticated) {
            console.log('Authentication successful!');
            setIsAuthenticated(true);
            clearInterval(pollInterval);
            onAuthenticated();
          }
        } catch (error) {
          console.error('Error polling auth status:', error);
        }
      }, 2000); // Check every 2 seconds

      // Clear interval after 5 minutes (timeout)
      setTimeout(() => {
        clearInterval(pollInterval);
        console.log('Auth polling timeout');
      }, 300000);
    } catch (error) {
      console.error('Error getting auth URL:', error);
    }
  };

  const handleContinue = () => {
    console.log('Continuing to chat...');
    onAuthenticated();
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  console.log('Auth component render - isAuthenticated:', isAuthenticated);

  if (isAuthenticated) {
    return (
      <div className="text-center p-4">
        <div className="text-green-600 mb-4">✓ Authenticated with Google Drive</div>
        <button
          onClick={handleContinue}
          className="bg-primary-500 text-white px-6 py-2 rounded-lg hover:bg-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          Continue to Chat
        </button>
        <div className="mt-4">
          <button
            onClick={checkAuthStatus}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Refresh Status
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="text-center p-4">
      <div className="mb-4">
        <p className="text-gray-600">Please authenticate with Google Drive to access your files.</p>
      </div>
      <button
        onClick={handleAuth}
        className="bg-primary-500 text-white px-6 py-2 rounded-lg hover:bg-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500"
      >
        Authenticate with Google Drive
      </button>
    </div>
  );
};

export default Auth; 