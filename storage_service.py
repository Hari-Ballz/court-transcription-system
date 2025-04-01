import os
import json
import sqlite3
import hashlib
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from utils import create_logger

class StorageService:
    def __init__(self, db_path: str = "transcripts.db"):
        self.logger = create_logger("storage_service")
        self.db_path = db_path
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize the database with required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create transcripts table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS transcripts (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                case_id TEXT,
                hash TEXT NOT NULL
            )
            ''')
            
            # Create audit log table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                transcript_id TEXT NOT NULL,
                action TEXT NOT NULL,
                user TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (transcript_id) REFERENCES transcripts(id)
            )
            ''')
            
            conn.commit()
            conn.close()
            self.logger.info("Database initialized successfully")
        
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
    
    def store_transcript(self, transcript_id: str, transcript_data: Dict) -> bool:
        """
        Securely store a transcript
        
        Args:
            transcript_id: Unique identifier for the transcript
            transcript_data: Transcript data to store
            
        Returns:
            Success status
        """
        try:
            # Convert data to JSON
            json_data = json.dumps(transcript_data)
            
            # Generate hash for integrity verification
            data_hash = hashlib.sha256(json_data.encode()).hexdigest()
            
            # Current timestamp
            timestamp = datetime.now().isoformat()
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                '''
                INSERT INTO transcripts (id, data, created_at, updated_at, case_id, hash)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    transcript_id,
                    json_data,
                    timestamp,
                    timestamp,
                    transcript_data.get("case_details", {}).get("case_id"),
                    data_hash
                )
            )
            
            # Log the action
            log_id = str(uuid.uuid4())
            cursor.execute(
                '''
                INSERT INTO audit_log (id, transcript_id, action, user, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    log_id,
                    transcript_id,
                    "create",
                    "system",
                    timestamp,
                    f"Created transcript with {len(transcript_data.get('segments', []))} segments"
                )
            )
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Stored transcript {transcript_id} successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Error storing transcript: {str(e)}")
            return False
    
    def get_transcript(self, transcript_id: str) -> Optional[Dict]:
        """
        Retrieve a transcript by ID
        
        Args:
            transcript_id: The ID of the transcript to retrieve
            
        Returns:
            Transcript data or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT data, hash FROM transcripts WHERE id = ?",
                (transcript_id,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                json_data, stored_hash = result
                
                # Verify integrity
                computed_hash = hashlib.sha256(json_data.encode()).hexdigest()
                if computed_hash != stored_hash:
                    self.logger.error(f"Integrity check failed for transcript {transcript_id}")
                    return None
                
                # Parse and return the data
                return json.loads(json_data)
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error retrieving transcript: {str(e)}")
            return None
    
    def update_transcript_segment(
        self, transcript_id: str, segment_id: str, new_text: str, user: str
    ) -> bool:
        """
        Update a specific segment in a transcript
        
        Args:
            transcript_id: The ID of the transcript
            segment_id: The ID of the segment to update
            new_text: The new text for the segment
            user: The user making the update
            
        Returns:
            Success status
        """
        try:
            # Get the current transcript
            transcript = self.get_transcript(transcript_id)
            if not transcript:
                self.logger.error(f"Transcript {transcript_id} not found")
                return False
            
            # Find and update the segment
            segment_updated = False
            for segment in transcript.get("segments", []):
                if segment.get("id") == segment_id:
                    segment["text"] = new_text
                    segment_updated = True
                    break
            
            if not segment_updated:
                self.logger.error(f"Segment {segment_id} not found in transcript {transcript_id}")
                return False
            
            # Convert updated data to JSON
            json_data = json.dumps(transcript)
            
            # Generate new hash
            data_hash = hashlib.sha256(json_data.encode()).hexdigest()
            
            # Current timestamp
            timestamp = datetime.now().isoformat()
            
            # Update in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                '''
                UPDATE transcripts 
                SET data = ?, updated_at = ?, hash = ?
                WHERE id = ?
                ''',
                (json_data, timestamp, data_hash, transcript_id)
            )
            
            # Log the action
            log_id = str(uuid.uuid4())
            cursor.execute(
                '''
                INSERT INTO audit_log (id, transcript_id, action, user, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    log_id,
                    transcript_id,
                    "update_segment",
                    user,
                    timestamp,
                    f"Updated segment {segment_id}"
                )
            )
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Updated segment {segment_id} in transcript {transcript_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error updating transcript segment: {str(e)}")
            return False
    
    def delete_transcript(self, transcript_id: str, user: str) -> bool:
        """
        Delete a transcript
        
        Args:
            transcript_id: The ID of the transcript to delete
            user: The user performing the deletion
            
        Returns:
            Success status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if transcript exists
            cursor.execute("SELECT id FROM transcripts WHERE id = ?", (transcript_id,))
            if cursor.fetchone() is None:
                conn.close()
                self.logger.error(f"Transcript {transcript_id} not found")
                return False
            
            # Log the deletion first for audit purposes
            timestamp = datetime.now().isoformat()
            log_id = str(uuid.uuid4())
            cursor.execute(
                '''
                INSERT INTO audit_log (id, transcript_id, action, user, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    log_id,
                    transcript_id,
                    "delete",
                    user,
                    timestamp,
                    "Transcript deleted"
                )
            )
            
            # Delete the transcript
            cursor.execute("DELETE FROM transcripts WHERE id = ?", (transcript_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Deleted transcript {transcript_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error deleting transcript: {str(e)}")
            return False
    
    def list_transcripts(
        self, user_role: str, case_id: Optional[str] = None, limit: int = 10, offset: int = 0
    ) -> List[Dict]:
        """
        List available transcripts with pagination
        
        Args:
            user_role: The role of the requesting user
            case_id: Optional case ID to filter by
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of transcript summaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT id, data, created_at, updated_at, case_id
                FROM transcripts
            '''
            
            params = []
            if case_id:
                query += " WHERE case_id = ?"
                params.append(case_id)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                transcript_id, json_data, created_at, updated_at, case_id = row
                
                # Parse data to extract summary
                data = json.loads(json_data)
                
                # Create a summary based on user role
                summary = {
                    "id": transcript_id,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "case_id": case_id,
                    "segments_count": len(data.get("segments", [])),
                    "speakers_count": len(set([s.get("speaker") for s in data.get("segments", [])])) if data.get("segments") else 0,
                    "duration": data.get("segments", [])[-1].get("end_time", 0) if data.get("segments") else 0
                }
                
                # Include more details for judges and admins
                if user_role in ["judge", "admin"]:
                    summary["metadata"] = data.get("metadata", {})
                    if data.get("case_details"):
                        summary["case_details"] = data.get("case_details")
                
                results.append(summary)
            
            conn.close()
            return results
        
        except Exception as e:
            self.logger.error(f"Error listing transcripts: {str(e)}")
            return []
    
    def export_transcript(self, transcript_id: str, format: str = "pdf") -> Optional[str]:
        """
        Export a transcript in various formats
        
        Args:
            transcript_id: The ID of the transcript to export
            format: Export format (pdf, docx, txt)
            
        Returns:
            Path to the exported file or None if failed
        """
        try:
            # Get the transcript
            transcript = self.get_transcript(transcript_id)
            if not transcript:
                self.logger.error(f"Transcript {transcript_id} not found")
                return None
            
            # Create a temporary file for the export
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
                export_path = temp_file.name
            
            if format == "txt":
                # Simple text export
                with open(export_path, "w", encoding="utf-8") as f:
                    # Write header
                    f.write(f"TRANSCRIPT ID: {transcript_id}\n")
                    f.write(f"Date: {transcript.get('metadata', {}).get('created_at', 'Unknown')}\n")
                    if transcript.get("case_details"):
                        f.write(f"Case: {transcript.get('case_details', {}).get('case_title', 'Unknown')}\n")
                        f.write(f"Court: {transcript.get('case_details', {}).get('court', 'Unknown')}\n")
                        f.write(f"Judge: {transcript.get('case_details', {}).get('judge', 'Unknown')}\n")
                    
                    f.write("\n" + "="*80 + "\n\n")
                    
                    # Write segments
                    current_speaker = None
                    for segment in transcript.get("segments", []):
                        # Format timestamp
                        start_time = segment.get("start_time", 0)
                        start_mins = int(start_time // 60)
                        start_secs = int(start_time % 60)
                        timestamp = f"[{start_mins:02d}:{start_secs:02d}]"
                        
                        # Only print speaker when it changes
                        if segment.get("speaker") != current_speaker:
                            current_speaker = segment.get("speaker")
                            f.write(f"\n\n{current_speaker}: ")
                        
                        f.write(f"{segment.get('text', '')} {timestamp} ")
            
            elif format == "pdf":
                # For demo purposes, we'll just create a dummy PDF file
                # In a real implementation, use a library like ReportLab or WeasyPrint
                with open(export_path, "w", encoding="utf-8") as f:
                    f.write("PDF Export Placeholder - This would be a properly formatted PDF in production")
            
            else:
                self.logger.error(f"Unsupported export format: {format}")
                return None
            
            self.logger.info(f"Exported transcript {transcript_id} to {export_path}")
            return export_path
        
        except Exception as e:
            self.logger.error(f"Error exporting transcript: {str(e)}")
            return None