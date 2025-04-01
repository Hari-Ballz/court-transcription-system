import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_BASE_URL } from '../config';
import '../styles/components/TranscriptList.css';

const TranscriptList = () => {
  const { user } = useAuth();
  const [transcripts, setTranscripts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [caseFilter, setCaseFilter] = useState('');
  
  useEffect(() => {
    fetchTranscripts();
  }, []);
  
  const fetchTranscripts = async () => {
    try {
      setLoading(true);
      
      const url = caseFilter
        ? `${API_BASE_URL}/api/transcripts?case_id=${caseFilter}`
        : `${API_BASE_URL}/api/transcripts`;
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${user.token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch transcripts');
      }
      const data = await response.json();
      setTranscripts(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const handleFilterChange = (e) => {
    setCaseFilter(e.target.value);
  };
  
  const handleFilterSubmit = (e) => {
    e.preventDefault();
    fetchTranscripts();
  };
  
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };
  
  const formatDuration = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    
    if (hours > 0) {
      return `${hours}h ${remainingMinutes}m`;
    } else {
      return `${minutes}m`;
    }
  };
  
  if (loading) return <div className="loading">Loading transcripts...</div>;
  if (error) return <div className="error">Error: {error}</div>;
  
  return (
    <div className="transcript-list">
      <div className="list-header">
        <h1>Court Transcripts</h1>
        
        <form className="filter-form" onSubmit={handleFilterSubmit}>
          <input
            type="text"
            placeholder="Filter by Case ID"
            value={caseFilter}
            onChange={handleFilterChange}
          />
          <button type="submit">Filter</button>
        </form>
        
        <div className="action-buttons">
          <Link to="/upload" className="upload-button">Upload New Recording</Link>
          <Link to="/record" className="record-button">Record New Session</Link>
        </div>
      </div>
      
      {transcripts.length === 0 ? (
        <div className="no-transcripts">
          <p>No transcripts found.</p>
          {caseFilter && (
            <p>Try clearing your filter or upload a new recording.</p>
          )}
        </div>
      ) : (
        <table className="transcripts-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Case ID</th>
              <th>Duration</th>
              <th>Speakers</th>
              <th>Segments</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {transcripts.map((transcript) => (
              <tr key={transcript.id}>
                <td>{formatDate(transcript.created_at)}</td>
                <td>{transcript.case_id || 'N/A'}</td>
                <td>{formatDuration(transcript.duration)}</td>
                <td>{transcript.speakers_count}</td>
                <td>{transcript.segments_count}</td>
                <td>
                  <Link 
                    to={`/transcript/${transcript.id}`}
                    className="view-button"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default TranscriptList;
