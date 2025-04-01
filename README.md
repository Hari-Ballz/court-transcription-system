# AI-Powered Court Transcription System

A real-time court transcription system that combines multi-microphone audio processing with machine learning to automate documentation of judicial proceedings.

## Features

- Speech recognition using Whisper
- Speaker diarization (identifying different speakers)
- Noise suppression for court environments
- Secure storage with role-based access control
- Real-time transcript viewing and editing
- Export to PDF and text formats

## Prerequisites

- Python 3.9 or higher
- Node.js 16 or higher
- FFmpeg
- A Hugging Face token for speaker diarization

## Installation

### Step 1: Set up the Backend

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables (add these to your .env file):
   ```
   HF_TOKEN=your_huggingface_token_here
   SECRET_KEY=your_secret_key_for_jwt_here
   ```

### Step 2: Set up the Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set the API URL in the .env file:
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```

## Running the Application

### Start the Backend Server

1. Activate the virtual environment (if not already activated)
2. Navigate to the backend directory
3. Run the server:
   ```bash
   python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
   ```

### Start the Frontend Server

1. In a separate terminal, navigate to the frontend directory
2. Start the development server:
   ```bash
   npm run dev
   ```

3. Access the application at http://localhost:5173

## Usage

1. Login using the provided demo credentials:
   - Judge: username `judge1`, password `judge1_password`
   - Advocate: username `advocate1`, password `advocate1_password`
   - Clerk: username `clerk1`, password `clerk1_password`

2. Upload an audio recording or record directly in the browser

3. View and edit transcripts based on your role permissions

4. Export transcripts as needed

## Project Structure

```
court-transcription-system/
├── backend/            # FastAPI backend
├── frontend/           # React/Vite frontend
├── uploads/            # Uploaded audio files
├── logs/               # Application logs
├── venv/               # Python virtual environment
├── .env                # Environment variables
└── requirements.txt    # Python dependencies
