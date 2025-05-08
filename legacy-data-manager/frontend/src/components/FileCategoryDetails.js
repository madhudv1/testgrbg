import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import config from '../config';
import './SensitiveContent.css';

const FileCategoryDetails = () => {
  const { ageGroup, fileType } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const filesPerPage = 20;

  // Restore state from location or localStorage
  const stats = location.state?.stats || JSON.parse(localStorage.getItem('stats')) || null;
  const selectedDirectory = location.state?.selectedDirectory || JSON.parse(localStorage.getItem('selectedDirectory')) || null;
  const activeTab = location.state?.activeTab || localStorage.getItem('activeTab') || 'moreThanThreeYears';
  const returnTo = location.state?.returnTo || '/';
  const directoryId = location.state?.directoryId || selectedDirectory?.id;

  // Save stats and activeTab to localStorage for back navigation
  useEffect(() => {
    if (stats) localStorage.setItem('stats', JSON.stringify(stats));
    if (activeTab) localStorage.setItem('activeTab', activeTab);
  }, [stats, activeTab]);

  const fetchFiles = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      if (!stats) {
        setError('No analysis data found. Please run analysis first.');
        return;
      }

      let url;
      if (directoryId) {
        url = `${config.apiBaseUrl}/api/v1/drive/directories/${directoryId}/files`;
      } else {
        url = `${config.apiBaseUrl}/api/v1/drive/files`;
      }

      const response = await axios.get(url, {
        params: {
          age_group: ageGroup,
          file_type: fileType,
          page: currentPage,
          per_page: filesPerPage
        }
      });

      if (!response.data || !response.data.files) {
        throw new Error('Invalid response format from server');
      }

      setFiles(response.data.files);
      setTotalPages(Math.ceil(response.data.total / filesPerPage));
    } catch (err) {
      console.error('Error fetching files:', err);
      if (err.response?.status === 404) {
        setError('No files found for this file type. Please run analysis first.');
      } else {
        setError(`Failed to fetch files: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  }, [ageGroup, fileType, currentPage, filesPerPage, stats, directoryId]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleSelectFile = (fileId) => {
    setSelectedFiles(prev => {
      const newSelected = new Set(prev);
      if (newSelected.has(fileId)) {
        newSelected.delete(fileId);
      } else {
        newSelected.add(fileId);
      }
      return newSelected;
    });
  };

  const handleSelectAll = () => {
    if (selectedFiles.size === files.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(files.map(file => file.id)));
    }
  };

  const handleAction = (action) => {
    // Placeholder for action handlers
    console.log(`Action ${action} triggered for files:`, Array.from(selectedFiles));
  };

  const handleBack = () => {
    navigate(returnTo, {
      state: {
        selectedDirectory,
        activeTab,
        stats
      }
    });
  };

  if (loading) {
    return (
      <div className="sensitive-content-container">
        <div className="loading-spinner">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="sensitive-content-container">
        <div className="error-message">
          <p>{error}</p>
          <button onClick={handleBack} className="back-button">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="sensitive-content-container">
      <div className="sensitive-content-header">
        <div className="header-left">
          <button onClick={handleBack} className="back-button">
            ← Back
          </button>
          <h2>{fileType.charAt(0).toUpperCase() + fileType.slice(1)} Files - {ageGroup}</h2>
        </div>
        <div className="action-buttons">
          <button
            className="action-button delete"
            disabled={selectedFiles.size === 0}
            onClick={() => handleAction('delete')}
          >
            Delete
          </button>
          <button
            className="action-button archive"
            disabled={selectedFiles.size === 0}
            onClick={() => handleAction('archive')}
          >
            Archive
          </button>
          <button
            className="action-button review"
            disabled={selectedFiles.size === 0}
            onClick={() => handleAction('review')}
          >
            Schedule Review
          </button>
        </div>
      </div>

      <div className="sensitive-content-table">
        <table>
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  checked={selectedFiles.size === files.length}
                  onChange={handleSelectAll}
                />
              </th>
              <th>File Name</th>
              <th>Location</th>
              <th>Last Modified</th>
              <th>Owner</th>
              <th>File Size</th>
              <th>Type</th>
            </tr>
          </thead>
          <tbody>
            {files.map(file => (
              <tr key={file.id} className={selectedFiles.has(file.id) ? 'selected' : ''}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedFiles.has(file.id)}
                    onChange={() => handleSelectFile(file.id)}
                  />
                </td>
                <td>{file.name}</td>
                <td>{file.location}</td>
                <td>{new Date(file.modifiedTime).toLocaleDateString()}</td>
                <td>{file.owner}</td>
                <td>{file.size ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : '-'}</td>
                <td>{file.mimeType || file.type || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="pagination">
        <button
          onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
          disabled={currentPage === 1}
        >
          Previous
        </button>
        <span>
          Page {currentPage} of {totalPages}
        </span>
        <button
          onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
          disabled={currentPage === totalPages}
        >
          Next
        </button>
      </div>
    </div>
  );
};

export default FileCategoryDetails; 