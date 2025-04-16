import React, { useEffect } from 'react';
import axios from 'axios';
import config from '../config';
import './Auth.css';

const Auth = ({ onAuthSuccess }) => {
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await axios.get(`${config.apiBaseUrl}/api/v1/drive/auth/status`);
        if (response.data.authenticated) {
          onAuthSuccess();
        }
      } catch (error) {
        console.error('Error checking auth status:', error);
      }
    };
    checkAuth();
  }, [onAuthSuccess]);

  const handleAuth = async () => {
    try {
      const response = await axios.get(`${config.apiBaseUrl}/api/v1/drive/auth/url`);
      window.location.href = response.data.auth_url;
    } catch (error) {
      console.error('Error getting auth URL:', error);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-content">
        <h1>Hi, I am Klio</h1>
        <p>How can I assist you with your legacy data today?</p>
        <button onClick={handleAuth} className="auth-button">
          Connect with Google Drive
        </button>
        <p className="auth-note">
          Klio needs access to your Google Drive to help you manage and analyze your files.
        </p>
      </div>
    </div>
  );
};

export default Auth; 