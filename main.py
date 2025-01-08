from fastapi import FastAPI, File, UploadFile, Form
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
            bins_per_octave=12  # Reduced for better performance
        )
        
        # Write to buffer with optimized settings
        buffer = io.BytesIO()
        sf.write(buffer, audio, sr, format='WAV', subtype='PCM_16')
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Audio processing error: {e}")
        return None

def convert_audio_format(audio_data, input_format, output_format='mp3'):
    """Convert audio between formats with optimized settings."""
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=input_format)
        
        # Optimize conversion settings
        buffer = io.BytesIO()
        export_params = {
            'format': output_format,
            'bitrate': '128k',  # Reduced bitrate for faster processing
            'parameters': ['-ac', '1']  # Convert to mono for smaller file size
        }
        audio.export(buffer, **export_params)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Format conversion error: {e}")
        return None

async def upload_to_cloudinary(audio_data):
    """Upload audio to Cloudinary with optimized settings."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        # Optimize upload settings
        result = cloudinary.uploader.upload(
            tmp_path,
            resource_type="auto",
            folder="audio_processing",
            quality="auto:low",  # Optimize for performance
            fetch_format="auto"
        )
        os.unlink(tmp_path)
        
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "format": result["format"]
        }
    except Exception as e:
        print(f"Upload error: {e}")
        return None

@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...), option: str = Form('1')):
    """Process audio file with specified pitch modifications."""
    try:
        # Validate option
        if option not in AUDIO_OPTIONS:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid option. Choose from: {', '.join(AUDIO_OPTIONS.keys())}"}
            )
        
        pitch_factor = AUDIO_OPTIONS[option]
        
        # Read file content
        content = await file.read()
        input_format = file.filename.split('.')[-1].lower()
        
        # Convert to WAV if needed
        if input_format != 'wav':
            content = convert_audio_format(content, input_format, 'wav').read()
            if not content:
                return JSONResponse(status_code=500, content={"error": "Audio conversion failed"})
        
        # Process audio
        modified_audio = process_audio_data(content, pitch_factor)
        if not modified_audio:
            return JSONResponse(status_code=500, content={"error": "Voice modification failed"})
        
        # Convert to MP3
        mp3_audio = convert_audio_format(modified_audio.read(), 'wav', 'mp3')
        if not mp3_audio:
            return JSONResponse(status_code=500, content={"error": "Final conversion failed"})
        
        # Upload and return results
        result = await upload_to_cloudinary(mp3_audio.read())
        if not result:
            return JSONResponse(status_code=500, content={"error": "Upload to Cloudinary failed"})
        
        return result

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})