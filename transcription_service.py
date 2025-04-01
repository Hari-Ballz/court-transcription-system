import os
import time
import uuid
import numpy as np
import whisper
import torch
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import tempfile
from noise_suppression import NoiseSuppression
from diarization_service import DiarizationService
from storage_service import StorageService
from utils import create_logger

class CourtTranscriptionService:
    def __init__(
        self, 
        noise_suppression: NoiseSuppression,
        diarization_service: DiarizationService,
        storage_service: StorageService
    ):
        self.logger = create_logger("transcription_service")
        self.noise_suppression = noise_suppression
        self.diarization_service = diarization_service
        self.storage_service = storage_service
        
        # Initialize Whisper model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"Using device: {self.device}")
        
        # Load base model for better performance on limited hardware
        # In a production environment with more resources, use the medium or large model
        try:
            self.model = whisper.load_model("base").to(self.device)
            self.logger.info("Whisper base model loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading Whisper model: {str(e)}")
            self.logger.info("Attempting to load tiny model as fallback")
            try:
                self.model = whisper.load_model("tiny").to(self.device)
                self.logger.info("Whisper tiny model loaded successfully")
            except Exception as e2:
                self.logger.error(f"Error loading fallback model: {str(e2)}")
                raise RuntimeError("Failed to initialize Whisper model")
        
    def process_audio(self, audio_file: str, case_id: Optional[str] = None) -> Dict:
        """
        Process audio file with noise suppression, speech recognition, and speaker diarization
        
        Args:
            audio_file: Path to the audio file
            case_id: Optional case identifier
            
        Returns:
            Dictionary containing transcript information
        """
        self.logger.info(f"Processing audio file: {audio_file}")
        start_time = time.time()
        
        # Apply noise suppression
        try:
            clean_audio_file = self.noise_suppression.process(audio_file)
            self.logger.info(f"Noise suppression completed in {time.time() - start_time:.2f} seconds")
        except Exception as e:
            self.logger.error(f"Error in noise suppression: {str(e)}")
            self.logger.warning("Using original audio file without noise suppression")
            clean_audio_file = audio_file
        
        # Perform speaker diarization
        diarization_start = time.time()
        try:
            speaker_segments = self.diarization_service.diarize(clean_audio_file)
            self.logger.info(f"Speaker diarization completed in {time.time() - diarization_start:.2f} seconds")
        except Exception as e:
            self.logger.error(f"Error in speaker diarization: {str(e)}")
            self.logger.warning("Continuing without speaker information")
            speaker_segments = []
        
        # Run speech recognition with Whisper
        transcription_start = time.time()
        try:
            result = self.model.transcribe(clean_audio_file)
            transcribed_segments = result["segments"]
            self.logger.info(f"Speech recognition completed in {time.time() - transcription_start:.2f} seconds")
        except Exception as e:
            self.logger.error(f"Error in speech recognition: {str(e)}")
            raise Exception(f"Speech recognition failed: {str(e)}")
        
        # Combine speaker diarization with transcribed segments
        combined_segments = self._combine_transcription_with_speakers(
            transcribed_segments, speaker_segments
        )
        
        # Generate transcript ID
        transcript_id = str(uuid.uuid4())
        
        # Prepare metadata
        metadata = {
            "created_at": datetime.now().isoformat(),
            "audio_file": os.path.basename(audio_file),
            "processing_time": time.time() - start_time,
            "model": f"whisper-{self.model.name}",
            "device": str(self.device),
            "speakers_detected": len(set([s["speaker"] for s in speaker_segments])) if speaker_segments else 0,
            "case_id": case_id
        }
        
        # Store transcript in the storage service
        transcript = {
            "id": transcript_id,
            "segments": combined_segments,
            "metadata": metadata,
            "case_details": self._get_case_details(case_id) if case_id else None,
            "status": "success"
        }
        
        try:
            self.storage_service.store_transcript(transcript_id, transcript)
        except Exception as e:
            self.logger.error(f"Error storing transcript: {str(e)}")
            # Continue anyway since we can return the transcript directly
        
        self.logger.info(f"Audio processing completed in {time.time() - start_time:.2f} seconds")
        return transcript
        
    def _combine_transcription_with_speakers(
        self, 
        transcribed_segments: List[Dict], 
        speaker_segments: List[Dict]
    ) -> List[Dict]:
        """
        Match transcribed segments with speaker labels
        
        Args:
            transcribed_segments: Segments from Whisper
            speaker_segments: Segments from diarization
            
        Returns:
            Combined segments with speaker information
        """
        combined_segments = []
        
        for segment in transcribed_segments:
            segment_start = segment["start"]
            segment_end = segment["end"]
            
            # Find speaker with the most overlap
            best_speaker = "Unknown"
            max_overlap = 0
            
            for spk_segment in speaker_segments:
                overlap_start = max(segment_start, spk_segment["start"])
                overlap_end = min(segment_end, spk_segment["end"])
                overlap = max(0, overlap_end - overlap_start)
                
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = spk_segment["speaker"]
            
            # Add to combined segments
            combined_segments.append({
                "id": str(uuid.uuid4()),
                "speaker": best_speaker,
                "text": segment["text"],
                "start_time": segment_start,
                "end_time": segment_end,
                "confidence": float(segment.get("confidence", 0.0))
            })
        
        return combined_segments
    
    def _get_case_details(self, case_id: str) -> Dict:
        """
        Get case details from a hypothetical case management system
        
        In a real implementation, this would fetch data from a court case database
        """
        # Mock implementation for demonstration purposes
        return {
            "case_id": case_id,
            "case_title": f"Case #{case_id}",
            "court": "District Court",
            "judge": "Hon. Judge Smith",
            "date": datetime.now().strftime("%Y-%m-%d")
        }