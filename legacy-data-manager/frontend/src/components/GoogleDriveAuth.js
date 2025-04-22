import React, { useEffect, useState } from 'react';
import axios from 'axios';
import config from '../config';
import './GoogleDriveAuth.css';

const GoogleDriveAuth = ({ onAuthSuccess }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await axios.get(`${config.apiBaseUrl}/api/v1/auth/google/status`);
      if (response.data.isAuthenticated) {
        setIsAuthenticated(true);
        onAuthSuccess();
      }
    } catch (error) {
      setError('Failed to check authentication status');
      console.error('Auth status check error:', error);
    }
  };

  const handleAuth = async () => {
    try {
      const response = await axios.get(`${config.apiBaseUrl}/api/v1/auth/google/login`);
      window.location.href = response.data.auth_url;
    } catch (error) {
      setError('Failed to get authentication URL');
      console.error('Auth URL error:', error);
    }
  };

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="google-drive-auth">
      {!isAuthenticated && (
        <button 
          className="auth-button"
          onClick={handleAuth}
        >
          Authenticate with Google Drive
        </button>
      )}
    </div>
  );
};

export default GoogleDriveAuth; 