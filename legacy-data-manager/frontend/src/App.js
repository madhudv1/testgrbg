import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AuthCallback from './components/AuthCallback';
import DirectoryList from './components/DirectoryList';
import DirectoryExplorer from './components/DirectoryExplorer';
import Klio from './components/Klio';
import './App.css';

function App() {
  const [selectedDirectory, setSelectedDirectory] = useState(null);
  const [activeTab, setActiveTab] = useState('age');
  const [typeSort, setTypeSort] = useState('count'); // 'count' or 'size'
  const [stats, setStats] = useState({
    staleDocuments: 0,
    duplicateDocuments: 0,
    sensitiveDocuments: 0,
    ageDistribution: {
      lessThanOneYear: 0,
      oneToThreeYears: 0,
      moreThanThreeYears: 0
    },
    fileTypes: {
      documents: { count: 0, size: 0 },
      spreadsheets: { count: 0, size: 0 },
      images: { count: 0, size: 0 },
      presentations: { count: 0, size: 0 },
      pdfs: { count: 0, size: 0 },
      others: { count: 0, size: 0 }
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

  const handleStatsUpdate = (newStats) => {
    console.log('handleStatsUpdate called with full details:', JSON.stringify(newStats, null, 2));
    console.log('Current stats before update full details:', JSON.stringify(stats, null, 2));
    setStats(prevStats => {
      const updatedStats = {
        ...prevStats,
        ...newStats,
        ageDistribution: {
          ...prevStats.ageDistribution,
          ...newStats.ageDistribution
        },
        fileTypes: {
          ...prevStats.fileTypes,
          ...newStats.fileTypes
        }
      };
      console.log('Updated stats full details:', JSON.stringify(updatedStats, null, 2));
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

  const renderFileTypeContent = () => {
    const totalCount = Object.values(stats.fileTypes).reduce((sum, type) => sum + type.count, 0);
    const totalSize = Object.values(stats.fileTypes).reduce((sum, type) => sum + type.size, 0);
    
    // Convert to array for sorting
    const typeArray = Object.entries(stats.fileTypes).map(([type, data]) => ({
      type,
      ...data,
      percentage: totalCount > 0 ? (data.count / totalCount * 100) : 0,
      sizePercentage: totalSize > 0 ? (data.size / totalSize * 100) : 0
    }));

    // Sort based on user preference
    typeArray.sort((a, b) => {
      if (typeSort === 'count') {
        return b.count - a.count;
      }
      return b.size - a.size;
    });

    return (
      <div className="type-content">
        <div className="type-header">
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
          {typeArray.map(({ type, count, size, percentage, sizePercentage }) => (
            <div key={type} className="type-bar">
              <span className="type-label">{type.charAt(0).toUpperCase() + type.slice(1)}</span>
              <div className="bar-container">
                <div 
                  className="bar" 
                  style={{ width: `${typeSort === 'count' ? percentage : sizePercentage}%` }}
                ></div>
              </div>
              <div className="type-stats">
                <span className="type-count">{count}</span>
                <span className="type-size">{formatBytes(size)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'age':
        return (
          <div className="age-bars">
            <div className="age-bar">
              <span className="age-label">&lt; 1 year</span>
              <div className="bar-container">
                <div className="bar" style={{ width: `${stats.ageDistribution.lessThanOneYear}%` }}></div>
              </div>
              <div className="percentage">
                {stats.ageDistribution.lessThanOneYear}%
              </div>
            </div>
            <div className="age-bar">
              <span className="age-label">1-3 years</span>
              <div className="bar-container">
                <div className="bar" style={{ width: `${stats.ageDistribution.oneToThreeYears}%` }}></div>
              </div>
              <div className="percentage">
                {stats.ageDistribution.oneToThreeYears}%
              </div>
            </div>
            <div className="age-bar">
              <span className="age-label">&gt; 3 years</span>
              <div className="bar-container">
                <div className="bar" style={{ width: `${stats.ageDistribution.moreThanThreeYears}%` }}></div>
              </div>
              <div className="percentage">
                {stats.ageDistribution.moreThanThreeYears}%
              </div>
            </div>
          </div>
        );
      case 'type':
        return renderFileTypeContent();
      case 'owner':
        return <div className="tab-content">Ownership analysis coming soon</div>;
      case 'usage':
        return <div className="tab-content">Usage analysis coming soon</div>;
      case 'risk':
        return <div className="tab-content">Risk analysis coming soon</div>;
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
                          className={`tab-button ${activeTab === 'age' ? 'active' : ''}`}
                          onClick={() => setActiveTab('age')}
                        >
                          Age
                        </button>
                        <button 
                          className={`tab-button ${activeTab === 'type' ? 'active' : ''}`}
                          onClick={() => setActiveTab('type')}
                        >
                          Type
                        </button>
                        <button 
                          className={`tab-button ${activeTab === 'owner' ? 'active' : ''}`}
                          onClick={() => setActiveTab('owner')}
                        >
                          Owner
                        </button>
                        <button 
                          className={`tab-button ${activeTab === 'usage' ? 'active' : ''}`}
                          onClick={() => setActiveTab('usage')}
                        >
                          Usage
                        </button>
                        <button 
                          className={`tab-button ${activeTab === 'risk' ? 'active' : ''}`}
                          onClick={() => setActiveTab('risk')}
                        >
                          Risk
                        </button>
                      </div>
                      <div className={`tab-content ${activeTab === 'age' ? 'active' : ''}`}>
                        {renderTabContent()}
                      </div>
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