import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_BASE_URL } from '../config';
import '../styles/components/UploadPage.css';

const UploadPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [caseId, setCaseId] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      // Check if it's an audio file
      if (!selectedFile.type.startsWith('audio/')) {
        setError('Please select an audio file');
        return;
      }
      
      setFile(selectedFile);
      setError(null);
    }
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a file');
      return;
    }
    
    try {
      setUploading(true);
      setProgress(0);
      
      // Create form data
      const formData = new FormData();
      formData.append('file', file);
      if (caseId) formData.append('case_id', caseId);
      
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 95) clearInterval(progressInterval);
          return Math.min(prev + 5, 95);
        });
      }, 500);
      
      // Upload file
      const response = await fetch(`${API_BASE_URL}/api/upload-audio`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.token}`
        },
        body: formData
      });
      
      clearInterval(progressInterval);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }
      
      setProgress(100);
      
      const data = await response.json();
      
      // Navigate to the transcript page
      setTimeout(() => {
        navigate(`/transcript/${data.transcript_id}`);
      }, 1000);
      
    } catch (err) {
      setError(err.message);
      setProgress(0);
    } finally {
      setUploading(false);
    }
  };
  
  return (
    <div className="upload-page">
      <h1>Upload Audio Recording</h1>
      <p className="instructions">
        Upload an audio file of a court session to generate a transcript with speaker identification.
      </p>
      
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit} className="upload-form">
        <div className="form-group">
          <label htmlFor="case-id">Case ID (optional):</label>
          <input
            type="text"
            id="case-id"
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
            placeholder="Enter case ID if applicable"
            disabled={uploading}
          />
        </div>
        
        <div className="form-group file-upload">
          <label htmlFor="audio-file">Audio File:</label>
          <input
            type="file"
            id="audio-file"
            accept="audio/*"
            onChange={handleFileChange}
            disabled={uploading}
          />
          {file && (
            <div className="file-info">
              <p>Selected file: {file.name}</p>
              <p>Size: {(file.size / (1024 * 1024)).toFixed(2)} MB</p>
            </div>
          )}
        </div>
        
        {uploading && (
          <div className="progress-container">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <div className="progress-text">
              {progress < 100 ? `Processing: ${progress}%` : 'Complete!'}
            </div>
          </div>
        )}
        
        <button 
          type="submit" 
          className="upload-button" 
          disabled={uploading || !file}
        >
          {uploading ? 'Processing...' : 'Upload and Process'}
        </button>
      </form>
      
      <div className="upload-notes">
        <h3>Notes:</h3>
        <ul>
          <li>Supported formats: WAV, MP3, FLAC, AAC</li>
          <li>Maximum file size: 200 MB</li>
          <li>For best results, use clear audio with minimal background noise</li>
          <li>Processing may take a few minutes depending on the audio length</li>
        </ul>
      </div>
    </div>
  );
};

export default UploadPage;
