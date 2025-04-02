import React, { useState, useEffect } from 'react';
import axios from 'axios';

const DirectoryExplorer = () => {
  const [currentFolder, setCurrentFolder] = useState(null);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);

  const fetchDirectoryContents = async (folderId) => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`/api/v1/directories/${folderId}/files`);
      setFiles(response.data.files);
      setCurrentFolder(folderId);
    } catch (err) {
      setError('Failed to fetch directory contents');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const analyzeDirectory = async () => {
    if (!currentFolder) return;
    
    try {
      setLoading(true);
      setError(null);
      const response = await axios.post(`/api/v1/directories/${currentFolder}/analyze`);
      setAnalysisResults(response.data);
    } catch (err) {
      setError('Failed to analyze directory');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Directory Explorer</h2>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {loading && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
        </div>
      )}

      {!currentFolder ? (
        <div className="text-center py-4">
          <p className="mb-4">Enter a Google Drive folder ID to explore:</p>
          <input
            type="text"
            placeholder="Enter folder ID"
            className="border p-2 rounded mr-2"
            onChange={(e) => setCurrentFolder(e.target.value)}
          />
          <button
            onClick={() => fetchDirectoryContents(currentFolder)}
            className="bg-blue-500 text-white px-4 py-2 rounded"
          >
            Explore
          </button>
        </div>
      ) : (
        <div>
          <div className="flex justify-between items-center mb-4">
            <button
              onClick={() => setCurrentFolder(null)}
              className="bg-gray-500 text-white px-4 py-2 rounded"
            >
              Back
            </button>
            <button
              onClick={analyzeDirectory}
              className="bg-green-500 text-white px-4 py-2 rounded"
            >
              Analyze Directory
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {files.map((file) => (
              <div key={file.id} className="border p-4 rounded">
                <h3 className="font-bold">{file.name}</h3>
                <p className="text-sm text-gray-600">{file.mimeType}</p>
              </div>
            ))}
          </div>

          {analysisResults && (
            <div className="mt-8">
              <h3 className="text-xl font-bold mb-4">Analysis Results</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {analysisResults.results.map((result) => (
                  <div key={result.file_id} className="border p-4 rounded">
                    <h4 className="font-bold">{result.name}</h4>
                    <div className="mt-2">
                      <p><strong>Primary Category:</strong> {result.analysis.primary_category}</p>
                      <p><strong>Secondary Category:</strong> {result.analysis.secondary_category}</p>
                      <p><strong>Confidence:</strong> {(result.analysis.confidence_score * 100).toFixed(1)}%</p>
                      <p><strong>Key Topics:</strong> {result.analysis.key_topics.join(', ')}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DirectoryExplorer; 