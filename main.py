from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import librosa
import soundfile as sf
import io
from pydub import AudioSegment
import cloudinary.uploader
import tempfile
import os
import random

# Initialize FastAPI
app = FastAPI()

# Define allowed origins
origins = [
    "http://localhost:5173",
    "https://stealth-frontend.onrender.com",
    "https://stealth-backend-kj78.onrender.com",
    "https://voice-changer-3.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # Added to ensure all response headers are accessible
)

# Cloudinary configuration
cloudinary.config(cloud_name="duowocved", api_key="516984976233131", api_secret="XgBdT78yTR2A56srD1Fzf1tqEyo")

# Audio processing configurations
SAMPLE_RATE = 22050  # Increased sample rate for better performance
AUDIO_OPTIONS = {
    '0': 4,
    '1': -4,
    '2': lambda: random.uniform(-6, 6)
}

def process_audio_data(audio_data, pitch_steps):
    """Process audio with optimized pitch modifications."""
    if not audio_data:
        raise ValueError("No audio data provided")
        
    try:
        # Load audio with reduced duration for testing
        audio, sr = librosa.load(io.BytesIO(audio_data), sr=SAMPLE_RATE, duration=None)
        
        # Apply pitch shift with optimized parameters
        if callable(pitch_steps):
            pitch_steps = pitch_steps()
            
        audio = librosa.effects.pitch_shift(
            audio, 
            sr=sr, 
            n_steps=pitch_steps, 
            bins_per_octave=12
        )
        
        # Write to buffer with optimized settings
        buffer = io.BytesIO()
        sf.write(buffer, audio, sr, format='WAV', subtype='PCM_16')
        buffer.seek(0)
        return buffer
    except Exception as e:
        raise ValueError(f"Audio processing failed: {str(e)}")

def convert_audio_format(audio_data, input_format, output_format='mp3'):
    """Convert audio between formats with optimized settings."""
    if not audio_data:
        raise ValueError("No audio data provided")
        
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=input_format)
        
        buffer = io.BytesIO()
        export_params = {
            'format': output_format,
            'bitrate': '128k',
            'parameters': ['-ac', '1']
        }
        audio.export(buffer, **export_params)
        buffer.seek(0)
        return buffer
    except Exception as e:
        raise ValueError(f"Format conversion failed: {str(e)}")

async def upload_to_cloudinary(audio_data):
    """Upload audio to Cloudinary with optimized settings."""
    if not audio_data:
        raise ValueError("No audio data provided")
        
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        result = cloudinary.uploader.upload(
            tmp_path,
            resource_type="auto",
            folder="audio_processing",
            quality="auto:low",
            fetch_format="auto"
        )
        os.unlink(tmp_path)
        
        if not result or 'secure_url' not in result:
            raise ValueError("Cloudinary upload failed")
            
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "format": result["format"]
        }
    except Exception as e:
        raise ValueError(f"Upload failed: {str(e)}")

@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...), option: str = Form('1')):
    """Process audio file with specified pitch modifications."""
    try:
        # Validate option
        if option not in AUDIO_OPTIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid option. Choose from: {', '.join(AUDIO_OPTIONS.keys())}"
            )
        
        pitch_factor = AUDIO_OPTIONS[option]
        
        # Read file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file provided")
            
        input_format = file.filename.split('.')[-1].lower()
        
        # Convert to WAV if needed
        if input_format != 'wav':
            wav_buffer = convert_audio_format(content, input_format, 'wav')
            content = wav_buffer.read()
        
        # Process audio
        modified_audio = process_audio_data(content, pitch_factor)
        
        # Convert to MP3
        mp3_audio = convert_audio_format(modified_audio.read(), 'wav', 'mp3')
        
        # Upload and return results
        result = await upload_to_cloudinary(mp3_audio.read())
        return result

    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Processing failed: {str(e)}"})