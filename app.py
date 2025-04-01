import os
import time
import uuid
import json
from typing import List, Optional, Dict
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
from jwt.exceptions import InvalidTokenError

from transcription_service import CourtTranscriptionService
from diarization_service import DiarizationService
from noise_suppression import NoiseSuppression
from storage_service import StorageService
from utils import create_logger, generate_timestamp

# Initialize FastAPI
app = FastAPI(title="Court Transcription System API", 
              description="API for AI-powered courtroom transcription with speaker diarization")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
logger = create_logger("app")
noise_suppression = NoiseSuppression()
diarization_service = DiarizationService()
storage_service = StorageService()
transcription_service = CourtTranscriptionService(
    noise_suppression, 
    diarization_service,
    storage_service
)

# Authentication configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-development")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# User roles (simplified for demonstration)
ROLES = {
    "judge": ["read", "edit", "delete"],
    "advocate": ["read"],
    "clerk": ["read", "metadata"],
    "admin": ["read", "edit", "delete", "admin"]
}

# Mock user database (replace with actual database in production)
USERS_DB = {
    "judge1": {
        "username": "judge1",
        "hashed_password": "hashed_judge1_password",  # Use proper hashing in production
        "role": "judge",
        "full_name": "Hon. Judge Smith"
    },
    "advocate1": {
        "username": "advocate1",
        "hashed_password": "hashed_advocate1_password",
        "role": "advocate",
        "full_name": "Adv. Jane Doe"
    },
    "clerk1": {
        "username": "clerk1",
        "hashed_password": "hashed_clerk1_password",
        "role": "clerk",
        "full_name": "Court Clerk Johnson"
    }
}

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: str

class TranscriptSegment(BaseModel):
    id: str
    speaker: str
    text: str
    start_time: float
    end_time: float
    confidence: float
    case_id: Optional[str] = None

class TranscriptResponse(BaseModel):
    transcript_id: str
    segments: List[TranscriptSegment]
    case_details: Optional[Dict] = None
    metadata: Dict
    status: str

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        
    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            
    async def broadcast(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                await connection.send_json(message)

websocket_manager = WebSocketManager()

# Authentication functions
def verify_password(plain_password, hashed_password):
    # In production, use proper password verification
    return plain_password == hashed_password.replace("hashed_", "")

def get_user(username: str):
    if username in USERS_DB:
        user_dict = USERS_DB[username]
        return User(
            username=user_dict["username"],
            full_name=user_dict.get("full_name"),
            role=user_dict["role"]
        )
    return None

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, USERS_DB[username]["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

def has_permission(user: User, required_permission: str):
    if user.role not in ROLES:
        return False
    return required_permission in ROLES[user.role]

# Routes for authentication
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# API routes for transcription
@app.post("/api/upload-audio", response_model=dict)
async def upload_audio(
    file: UploadFile = File(...),
    case_id: str = Form(None),
    user: User = Depends(get_current_user)
):
    if not has_permission(user, "read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Save uploaded file
    file_location = f"uploads/{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    os.makedirs(os.path.dirname(file_location), exist_ok=True)
    
    with open(file_location, "wb+") as file_object:
        file_object.write(await file.read())
    
    # Process audio asynchronously (simplified for this example)
    job_id = str(uuid.uuid4())
    
    # In a real implementation, this would be a background task
    # For simplicity, we process synchronously here
    try:
        transcript = transcription_service.process_audio(file_location, case_id)
        return {
            "job_id": job_id,
            "status": "success",
            "message": "Audio processed successfully",
            "transcript_id": transcript["id"]
        }
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing audio: {str(e)}"
        )

@app.get("/api/transcript/{transcript_id}", response_model=TranscriptResponse)
async def get_transcript(
    transcript_id: str,
    user: User = Depends(get_current_user)
):
    if not has_permission(user, "read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        transcript = storage_service.get_transcript(transcript_id)
        if not transcript:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # Filter data based on user role
        if user.role == "clerk" and has_permission(user, "metadata"):
            # Clerks only see metadata
            return {
                "transcript_id": transcript_id,
                "segments": [],
                "metadata": transcript["metadata"],
                "status": "success",
                "case_details": transcript.get("case_details")
            }
        
        return transcript
    except Exception as e:
        logger.error(f"Error retrieving transcript: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving transcript: {str(e)}"
        )

@app.put("/api/transcript/{transcript_id}/segment/{segment_id}", response_model=dict)
async def update_transcript_segment(
    transcript_id: str,
    segment_id: str,
    text: str,
    user: User = Depends(get_current_user)
):
    if not has_permission(user, "edit"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        updated = storage_service.update_transcript_segment(
            transcript_id, segment_id, text, user.username
        )
        
        if updated:
            # Broadcast update to connected clients
            await websocket_manager.broadcast(
                transcript_id,
                {
                    "action": "segment_updated",
                    "segment_id": segment_id,
                    "text": text,
                    "updated_by": user.username
                }
            )
            
            return {"status": "success", "message": "Segment updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Segment not found")
    except Exception as e:
        logger.error(f"Error updating segment: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error updating segment: {str(e)}"
        )

@app.delete("/api/transcript/{transcript_id}", response_model=dict)
async def delete_transcript(
    transcript_id: str,
    user: User = Depends(get_current_user)
):
    if not has_permission(user, "delete"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        deleted = storage_service.delete_transcript(transcript_id, user.username)
        
        if deleted:
            return {"status": "success", "message": "Transcript deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Transcript not found")
    except Exception as e:
        logger.error(f"Error deleting transcript: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error deleting transcript: {str(e)}"
        )

@app.get("/api/transcripts", response_model=List[dict])
async def list_transcripts(
    user: User = Depends(get_current_user),
    case_id: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
):
    if not has_permission(user, "read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        transcripts = storage_service.list_transcripts(
            user_role=user.role,
            case_id=case_id,
            limit=limit,
            offset=offset
        )
        return transcripts
    except Exception as e:
        logger.error(f"Error listing transcripts: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error listing transcripts: {str(e)}"
        )

@app.get("/api/export-transcript/{transcript_id}", response_model=dict)
async def export_transcript(
    transcript_id: str,
    format: str = "pdf",
    user: User = Depends(get_current_user)
):
    if not has_permission(user, "read"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    try:
        export_url = storage_service.export_transcript(transcript_id, format)
        
        return {
            "status": "success",
            "export_url": export_url,
            "format": format
        }
    except Exception as e:
        logger.error(f"Error exporting transcript: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error exporting transcript: {str(e)}"
        )

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{transcript_id}")
async def websocket_endpoint(websocket: WebSocket, transcript_id: str):
    client_id = transcript_id
    await websocket_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
            # Process client messages if needed
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, client_id)

# Simple route for testing if the API is running
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": generate_timestamp()}

# Serve static files for uploads
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)