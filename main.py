from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import librosa
import soundfile as sf
import io
from pydub import AudioSegment
import cloudinary
import cloudinary.uploader
import tempfile
import os

app = FastAPI()

# Configure Cloudinary
cloudinary.config(
    cloud_name="duowocved",
    api_key="516984976233131",
    api_secret="XgBdT78yTR2A56srD1Fzf1tqEyo"
)

def voice_changer(input_data, pitch_factor=1.25, tempo_factor=1.15):
    try:
        audio, sr = librosa.load(io.BytesIO(input_data), sr=16000)
        audio_pitch_shifted = librosa.effects.pitch_shift(audio, sr=sr, n_steps=int(pitch_factor), bins_per_octave=24)
        audio_time_stretched = librosa.effects.time_stretch(audio_pitch_shifted, rate=tempo_factor)
        
        output_buffer = io.BytesIO()
        sf.write(output_buffer, audio_time_stretched, sr, format='WAV')
        output_buffer.seek(0)
        return output_buffer
    except Exception as e:
        print(f"Error: {e}")
        return None

def convert_to_mp3(input_file, input_format):
    try:
        audio = AudioSegment.from_file(io.BytesIO(input_file), format=input_format)
        mp3_buffer = io.BytesIO()
        audio.export(mp3_buffer, format="mp3")
        mp3_buffer.seek(0)
        return mp3_buffer
    except Exception as e:
        print(f"Conversion error: {e}")
        return None

@app.post("/process-audio")
async def process_audio(
    file: UploadFile = File(...),
    option: str = Form('high_pitch_low_tempo')
):
    try:
        # Read file content
        content = await file.read()
        
        # Determine input format from filename
        input_format = file.filename.split('.')[-1].lower()
        
        # Map options
        options_map = {
            'high_pitch_low_tempo': (4, 0.02),
            'high_pitch_high_tempo': (4, 1.1),
            'low_pitch_low_tempo': (-4, 0.02),
            'low_pitch_high_tempo': (-4, 1.1)
        }
        pitch_factor, tempo_factor = options_map.get(option, (4, 0.02))

        # Convert to WAV for processing if needed
        if input_format != 'wav':
            wav_buffer = convert_to_mp3(content, input_format)
            if wav_buffer is None:
                return JSONResponse(status_code=500, content={"error": "Audio conversion failed"})
            content = wav_buffer.read()

        # Modify voice
        modified_audio = voice_changer(content, pitch_factor, tempo_factor)
        if modified_audio is None:
            return JSONResponse(status_code=500, content={"error": "Voice modification failed"})

        # Convert to MP3
        mp3_audio = convert_to_mp3(modified_audio.read(), 'wav')
        if mp3_audio is None:
            return JSONResponse(status_code=500, content={"error": "Final conversion failed"})

        # Save to temporary file for Cloudinary upload
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tmp.write(mp3_audio.read())
            tmp_path = tmp.name

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            tmp_path,
            resource_type="auto",
            folder="audio_processing"
        )

        # Clean up temp file
        os.unlink(tmp_path)

        # Return Cloudinary details
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "format": result["format"],
            "resource_type": result["resource_type"]
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})