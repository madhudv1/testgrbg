import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AuthCallback from './components/AuthCallback';
import DirectoryList from './components/DirectoryList';
import DirectoryExplorer from './components/DirectoryExplorer';
import Klio from './components/Klio';
import './App.css';
import config from './config';

function App() {
  const [selectedDirectory, setSelectedDirectory] = useState(null);
  const [activeTab, setActiveTab] = useState('moreThanThreeYears');
  const [typeSort, setTypeSort] = useState('count'); // 'count' or 'size'
  const [stats, setStats] = useState({
    staleDocuments: 0,
    duplicateDocuments: 0,
    sensitiveDocuments: 0,
    ageDistribution: {
      // Dummy data for development
      moreThanThreeYears: {
        types: {
          documents: { count: 45, size: 15000000, percentage: 30 },
          spreadsheets: { count: 30, size: 8000000, percentage: 20 },
          presentations: { count: 15, size: 20000000, percentage: 10 },
          pdfs: { count: 30, size: 25000000, percentage: 20 },
          images: { count: 15, size: 12000000, percentage: 10 },
          others: { count: 15, size: 5000000, percentage: 10 }
        },
        risks: {
          pii: { count: 20, size: 5000000, percentage: 40 },
          financial: { count: 15, size: 4000000, percentage: 30 },
          legal: { count: 10, size: 3000000, percentage: 20 },
          confidential: { count: 5, size: 1000000, percentage: 10 }
        }
      },
      oneToThreeYears: {
        types: {
          documents: { count: 30, size: 10000000, percentage: 25 },
          spreadsheets: { count: 25, size: 6000000, percentage: 20 },
          presentations: { count: 20, size: 15000000, percentage: 15 },
          pdfs: { count: 25, size: 20000000, percentage: 20 },
          images: { count: 15, size: 10000000, percentage: 12 },
          others: { count: 10, size: 4000000, percentage: 8 }
        },
        risks: {
          pii: { count: 15, size: 4000000, percentage: 35 },
          financial: { count: 12, size: 3000000, percentage: 28 },
          legal: { count: 10, size: 2500000, percentage: 23 },
          confidential: { count: 6, size: 1500000, percentage: 14 }
        }
      },
      lessThanOneYear: {
        types: {
          documents: { count: 20, size: 8000000, percentage: 22 },
          spreadsheets: { count: 18, size: 5000000, percentage: 20 },
          presentations: { count: 15, size: 12000000, percentage: 16 },
          pdfs: { count: 20, size: 18000000, percentage: 22 },
          images: { count: 12, size: 9000000, percentage: 13 },
          others: { count: 7, size: 3000000, percentage: 7 }
        },
        risks: {
          pii: { count: 10, size: 3000000, percentage: 30 },
          financial: { count: 8, size: 2500000, percentage: 25 },
          legal: { count: 8, size: 2000000, percentage: 25 },
          confidential: { count: 6, size: 1500000, percentage: 20 }
        }
      }
    }
  });

  const handleKlioCommand = (command) => {
    switch (command.name.toLowerCase()) {
      case 'list directories':
        // Just trigger the directory listing in Klio
        break;
      case 'analyze':
        // Analysis will be handled by Klio component
        break;
      case 'clean':
        // Cleaning command will be handled by Klio component
        break;
      default:
        console.warn('Unknown command:', command.name);
    }
  };

  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    const stored = localStorage.getItem('isAuthenticated') === 'true';
    console.log('Initial auth state from localStorage:', stored);
    return stored;
  });
  const [authChecked, setAuthChecked] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [loading, setLoading] = useState(true);

  const handleGoogleSignIn = async () => {
    console.log('Starting Google Sign In...');
    try {
      setAuthError(null);
      const loginUrl = `${config.apiBaseUrl}/api/v1/auth/google/login`;
      console.log('Making auth URL request to:', loginUrl);
      console.log('Current config:', config);
      
      const response = await fetch(loginUrl, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
        }
      });
      
      console.log('Auth URL response:', response);
      console.log('Response status:', response.status);
      console.log('Response headers:', [...response.headers.entries()]);
      
      if (!response.ok) {
        throw new Error(`Failed to get auth URL: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Auth URL data:', data);
      console.log('Full auth URL for redirect:', data.auth_url);
      
      if (data.auth_url) {
        console.log('Redirecting to auth URL:', data.auth_url);
        // Force clear auth state before redirect
        setIsAuthenticated(false);
        localStorage.removeItem('isAuthenticated');
        window.location.href = data.auth_url;
      } else {
        throw new Error('No auth URL received');
      }
    } catch (error) {
      console.error('Error in handleGoogleSignIn:', error);
      setAuthError('Failed to initiate authentication. Please try again.');
    }
  };

  // MV TBD compare 
  const handleStatsUpdate = (newStats) => {
    console.log('Received new stats:', newStats);
    
    setStats(prevStats => {
      // Create updated stats object with the new structure
      const updatedStats = {
        ...prevStats,
        totalFiles: newStats.total_files,
        ageDistribution: {
          lessThanOneYear: newStats.ageDistribution?.lessThanOneYear || prevStats.ageDistribution.lessThanOneYear,
          oneToThreeYears: newStats.ageDistribution?.oneToThreeYears || prevStats.ageDistribution.oneToThreeYears,
          moreThanThreeYears: newStats.ageDistribution?.moreThanThreeYears || prevStats.ageDistribution.moreThanThreeYears
        }
      };
      
      console.log('Updated stats:', updatedStats);
      return updatedStats;
    });
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  const fileTypeColors = {
    documents: '#4285F4',    // Google Blue
    spreadsheets: '#0F9D58', // Google Green
    presentations: '#F4B400', // Google Yellow
    pdfs: '#DB4437',        // Google Red
    images: '#9C27B0',      // Purple
    others: '#757575'       // Gray
  };

  const renderFileTypeContent = () => {
    const { fileTypes } = stats;
    
    // Filter out types with both count and size as 0
    const nonEmptyTypes = Object.entries(fileTypes).filter(([_, type]) => 
      type.count > 0 || type.size > 0
    );
    
    // Calculate totals for percentage
    const totalCount = nonEmptyTypes.reduce((sum, [_, type]) => sum + type.count, 0);
    const totalSize = nonEmptyTypes.reduce((sum, [_, type]) => sum + type.size, 0);
    
    // Sort file types
    const sortedTypes = nonEmptyTypes.sort(([keyA, a], [keyB, b]) => {
      if (typeSort === 'count') {
        return b.count - a.count;
      }
      return b.size - a.size;
    });

    return (
      <div className="type-content">
        <div className="sort-toggle">
          <button 
            className={`sort-button ${typeSort === 'count' ? 'active' : ''}`}
            onClick={() => setTypeSort('count')}
          >
            Sort by Count
          </button>
          <button 
            className={`sort-button ${typeSort === 'size' ? 'active' : ''}`}
            onClick={() => setTypeSort('size')}
          >
            Sort by Size
          </button>
        </div>
        <div className="type-bars">
          {sortedTypes.map(([type, data]) => {
            const percentage = typeSort === 'count' 
              ? (data.count / totalCount * 100)
              : (data.size / totalSize * 100);
            
            return (
              <div key={type} className="type-bar">
                <span className="type-label">{type.charAt(0).toUpperCase() + type.slice(1)}</span>
                <div className="bar-container">
                  <div 
                    className="bar" 
                    style={{ 
                      width: `${percentage}%`,
                      backgroundColor: fileTypeColors[type],
                      opacity: 0.85
                    }}
                  ></div>
                </div>
                <div className="type-stats">
                  <span className="type-count">{data.count} files</span>
                  <span className="type-size">{formatBytes(data.size)}</span>
                  <span className="type-percentage">{percentage.toFixed(1)}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderRiskContent = () => {
    const total = stats.totalFiles || 0; // Use totalFiles from stats
    const sensitiveCount = stats.sensitiveDocuments || 0;
    
    // Ensure cleanCount is not negative if data is inconsistent
    const cleanCount = Math.max(0, total - sensitiveCount); 

    const sensitivePercentage = total > 0 ? (sensitiveCount / total * 100) : 0;
    const cleanPercentage = total > 0 ? (cleanCount / total * 100) : 0;

    // Define colors directly for clarity
    const sensitiveColor = '#DB4437'; // Red
    const cleanColor = '#0F9D58'; // Green

    return (
      <div className="risk-bars"> {/* Use a specific class */} 
        <div className="risk-bar"> {/* Class for individual bar row */} 
          <span className="risk-label">Sensitive</span>
          <div className="bar-container">
            <div 
              className="bar sensitive-bar" 
              style={{ 
                width: `${sensitivePercentage}%`,
                backgroundColor: sensitiveColor,
                opacity: 0.85
              }}
            ></div>
          </div>
          <div className="risk-stats"> {/* Specific class for stats */} 
            <span className="count">{sensitiveCount} files</span>
            <span className="percentage">{sensitivePercentage.toFixed(1)}%</span>
          </div>
        </div>
        <div className="risk-bar">
          <span className="risk-label">Clean</span>
          <div className="bar-container">
            <div 
              className="bar clean-bar" 
              style={{ 
                width: `${cleanPercentage}%`,
                backgroundColor: cleanColor,
                opacity: 0.85
              }}
            ></div>
          </div>
          <div className="risk-stats">
            <span className="count">{cleanCount} files</span>
            <span className="percentage">{cleanPercentage.toFixed(1)}%</span>
          </div>
        </div>
      </div>
    );
  };

  /* MV Original
  const renderAgeSection = (data, title) => {
    if (!data) return null;

    return (
      <div className="age-section">
        <h3>{title}</h3>
        
        {/* Types Section *}
        <div className="section-content">
          <h4>File Types</h4>
          <div className="type-bars">
            {Object.entries(data.types).map(([type, stats]) => (
              <div key={type} className="type-bar">
                <span className="type-label">{type.charAt(0).toUpperCase() + type.slice(1)}</span>
                <div className="bar-container">
                  <div 
                    className="bar" 
                    style={{ 
                      width: `${stats.percentage}%`,
                      backgroundColor: fileTypeColors[type],
                      opacity: 0.85
                    }}
                  ></div>
                </div>
                <div className="type-stats">
                  <span className="type-count">{stats.count} files</span>
                  <span className="type-size">{formatBytes(stats.size)}</span>
                  <span className="type-percentage">{stats.percentage}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Risks Section *}
        <div className="section-content">
          <h4>Risks</h4>
          <div className="risk-bars">
            {Object.entries(data.risks).map(([risk, stats]) => (
              <div key={risk} className="risk-bar">
                <span className="risk-label">{risk.charAt(0).toUpperCase() + risk.slice(1)}</span>
                <div className="bar-container">
                  <div 
                    className="bar" 
                    style={{ 
                      width: `${stats.percentage}%`,
                      backgroundColor: '#DB4437',
                      opacity: 0.85
                    }}
                  ></div>
                </div>
                <div className="risk-stats">
                  <span className="risk-count">{stats.count} files</span>
                  <span className="risk-size">{formatBytes(stats.size)}</span>
                  <span className="risk-percentage">{stats.percentage}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };*/

  const renderAgeSection = (data, title) => {    
    if (!data) {
      console.log('No data provided to renderAgeSection');
      return null;
    }

    // Calculate total PII items in this age category
    const totalPiiCount = Object.values(data.risks || {}).reduce((sum, risk) => 
      sum + (risk.count || 0), 0
    );

    // Calculate percentages for PII items
    const piiData = { ...data.risks };
    if (totalPiiCount > 0) {
      Object.keys(piiData).forEach(type => {
        if (piiData[type]) {
          piiData[type].percentage = Math.round((piiData[type].count / totalPiiCount) * 100);
        }
      });
    }

    // Colors for different PII types
    const piiColors = {
      //pii (red #FF6B6B)
      pii: '#FF6B6B',      // Coral Red
      email: '#FF6B6B',    // Coral Red

      //financial (mint #A8E6CF)
      financial: '#A8E6CF',    // Mint
      credit_card: '#A8E6CF',  // Mint
      
      //confidential (orange #FF9F43)
      confidential: '#FF9F43',  // Orange
      ip_address: '#FF9F43',    // Orange
      
      //legal (blue #4834D4)
      legal: '#4834D4',    // Blue
      ssn: '#4834D4',      // Blue
      phone: '#4834D4',    // Blue
    };

    return (
      <div className="age-section">
        <h3>{title}</h3>
        <div className="age-section-content">
          {/* Types Section */}
          <div className="section-content">
            <h4>File Types</h4>
            <div className="type-bars">
              {Object.entries(data.types || {}).map(([type, stats]) => {
                return (
                  <div key={type} className="type-bar">
                    <span className="type-label">{type.charAt(0).toUpperCase() + type.slice(1)}</span>
                    <div className="bar-container">
                      <div 
                        className="bar" 
                        style={{ 
                          width: `${stats.percentage}%`,
                          backgroundColor: fileTypeColors[type],
                          opacity: 0.85
                        }}
                      ></div>
                    </div>
                    <div className="type-stats">
                      <span className="type-count">{stats.count || 0} files</span>
                      <span className="type-size">{formatBytes(stats.size || 0)}</span>
                      <span className="type-percentage">{stats.percentage || 0}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* PII Section */}
          <div className="section-content">
            <h4>Risk {totalPiiCount > 0 && 
              <span className="pii-total">({totalPiiCount} items found)</span>
            }</h4>
            <div className="type-bars">
              {Object.entries(piiData || {}).map(([type, info]) => {
                if (info && info.count > 0) {
                  return (
                    <div key={type} className="type-bar">
                      <span className="type-label">
                        {type.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <div className="bar-container">
                        <div 
                          className="bar" 
                          style={{ 
                            width: `${info.percentage}%`,
                            backgroundColor: piiColors[type] || '#6C5CE7',
                            opacity: 0.85
                          }}
                        ></div>
                      </div>
                      <div className="type-stats">
                        <span className="type-count">{info.count} found</span>
                        <span className={`pii-badge ${info.confidence >= 0.9 ? 'high' : 'medium'}`}>
                          {Math.round((info.confidence || 0) * 100)}%
                        </span>
                        <span className="type-percentage">{info.percentage}%</span>
                      </div>
                    </div>
                  );
                }
                return null;
              }).filter(Boolean)}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'moreThanThreeYears':
        return renderAgeSection(stats.ageDistribution?.moreThanThreeYears, 'Files > 3 years old');
      case 'oneToThreeYears':
        return renderAgeSection(stats.ageDistribution?.oneToThreeYears, 'Files 1-3 years old');
      case 'lessThanOneYear':
        return renderAgeSection(stats.ageDistribution?.lessThanOneYear, 'Files < 1 year old');
      case 'type':
        return renderFileTypeContent();
      case 'owner':
        return <div className="tab-content">Ownership analysis coming soon</div>;
      case 'usage':
        return <div className="tab-content">Usage analysis coming soon</div>;
      case 'risk':
        return renderRiskContent();
      default:
        return null;
    }
  };

  return (
    <Router>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route
          path="/"
          element={
            <div className="app-container">
              <header className="app-header">
                <h1>grbg.ai</h1>
              </header>
              <div className="app-content">
                <div className="dashboard-section">
                  <div className="document-overview">
                    <h2>Document overview</h2>
                    <div className="stats-grid">
                      <div className="stat-card" title="Documents that haven't been accessed in the last 6 months">
                        <div className="stat-number">
                          {stats.staleDocuments.toLocaleString()}
                          {stats.staleDocuments > 0 && <span className="trend-up">↑</span>}
                        </div>
                        <div className="stat-label">Stale documents</div>
                      </div>
                      <div className="stat-card" title="Documents with similar content or identical names">
                        <div className="stat-number">
                          {stats.duplicateDocuments.toLocaleString()}
                          {stats.duplicateDocuments > 0 && <span className="trend-up">↑</span>}
                        </div>
                        <div className="stat-label">Duplicate documents</div>
                      </div>
                      <div className="stat-card" title="Documents that may contain sensitive information">
                        <div className="stat-number">
                          {stats.sensitiveDocuments.toLocaleString()}
                          {stats.sensitiveDocuments > 0 && <span className="trend-warning">!</span>}
                        </div>
                        <div className="stat-label">Sensitive documents</div>
                      </div>
                    </div>

                    <div className="age-distribution">
                      <div className="analysis-tabs">
                        <button 
                          className={`tab-button ${activeTab === 'moreThanThreeYears' ? 'active' : ''}`}
                          onClick={() => setActiveTab('moreThanThreeYears')}
                        >
                          &gt; 3 years
                        </button>
                        <button 
                          className={`tab-button ${activeTab === 'oneToThreeYears' ? 'active' : ''}`}
                          onClick={() => setActiveTab('oneToThreeYears')}
                        >
                          1-3 years
                        </button>
                        <button 
                          className={`tab-button ${activeTab === 'lessThanOneYear' ? 'active' : ''}`}
                          onClick={() => setActiveTab('lessThanOneYear')}
                        >
                          &lt; 1 year
                        </button>
                      </div>
                      {renderTabContent()}
                    </div>
                  </div>

                  <div className="bottom-panels">
                    <div className="categories">
                      <h3>Categories</h3>
                      <div className="category-list">
                        <div className="category-item">
                          <span>HR</span>
                          <button className="review-button">Review →</button>
                        </div>
                        <div className="category-item">
                          <span>Finance</span>
                          <button className="review-button">Review →</button>
                        </div>
                        <div className="category-item">
                          <span>Legal</span>
                          <button className="review-button">Review →</button>
                        </div>
                        <div className="category-item">
                          <span>Operations</span>
                          <span>0 min</span>
                        </div>
                      </div>
                    </div>

                    <div className="active-rules">
                      <h3>Active rules</h3>
                      <div className="rules-list">
                        <div className="rule-item">
                          <div className="rule-text">Find stale HR docs 'do *ay'</div>
                          <div className="rule-frequency">Daily →</div>
                        </div>
                        <div className="rule-item">
                          <div className="rule-text">Archive finance documents with Unused in 2 years</div>
                          <div className="rule-frequency">Weekly →</div>
                        </div>
                        <div className="rule-item">
                          <div className="rule-text">Flag sensitive files containing payment* ternatics</div>
                          <div className="rule-frequency">Monthly →</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="klio-section">
                  <Klio 
                    onCommand={handleKlioCommand}
                    onStatsUpdate={handleStatsUpdate}
                  />
                </div>
              </div>
            </div>
          }
        />
      </Routes>
    </Router>
  );
}

export default App; 