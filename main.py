from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import librosa
import soundfile as sf
import io
from pydub import AudioSegment
import cloudinary.uploader
import tempfile
import os

# Initialize FastAPI
app = FastAPI()

# Cloudinary configuration
cloudinary.config(cloud_name="duowocved", api_key="516984976233131", api_secret="XgBdT78yTR2A56srD1Fzf1tqEyo")

# Audio processing configurations
SAMPLE_RATE = 16000
AUDIO_OPTIONS = {
    'high_pitch_low_tempo': (4, 0.02),
    'high_pitch_high_tempo': (4, 1.1),
    'low_pitch_low_tempo': (-4, 0.02),
    'low_pitch_high_tempo': (-4, 1.1)
}

def process_audio_data(audio_data, pitch_steps, tempo_rate):
    """Process audio with given pitch and tempo modifications."""
    try:
        audio, sr = librosa.load(io.BytesIO(audio_data), sr=SAMPLE_RATE)
        audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=pitch_steps, bins_per_octave=24)
        audio = librosa.effects.time_stretch(audio, rate=tempo_rate)
        
        buffer = io.BytesIO()
        sf.write(buffer, audio, sr, format='WAV')
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Audio processing error: {e}")
        return None

def convert_audio_format(audio_data, input_format, output_format='mp3'):
    """Convert audio between formats using pydub."""
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_data), format=input_format)
        buffer = io.BytesIO()
        audio.export(buffer, format=output_format)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Format conversion error: {e}")
        return None

async def upload_to_cloudinary(audio_data):
    """Upload audio to Cloudinary and return response."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        result = cloudinary.uploader.upload(
            tmp_path,
            resource_type="auto",
            folder="audio_processing"
        )
        os.unlink(tmp_path)
        
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "format": result["format"],
            "resource_type": result["resource_type"]
        }
    except Exception as e:
        print(f"Upload error: {e}")
        return None

@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...), option: str = Form('high_pitch_low_tempo')):
    """Process audio file with specified modifications and upload to Cloudinary."""
    try:
        # Get audio processing parameters
        if option not in AUDIO_OPTIONS:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid option. Choose from: {', '.join(AUDIO_OPTIONS.keys())}"}
            )
        
        pitch_factor, tempo_factor = AUDIO_OPTIONS[option]
        
        # Read and process file
        content = await file.read()
        input_format = file.filename.split('.')[-1].lower()
        
        # Convert to WAV if needed
        if input_format != 'wav':
            content = convert_audio_format(content, input_format, 'wav').read()
            if not content:
                return JSONResponse(status_code=500, content={"error": "Audio conversion failed"})
        
        # Process audio
        modified_audio = process_audio_data(content, pitch_factor, tempo_factor)
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