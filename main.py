from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse, JSONResponse
import librosa
import soundfile as sf
import io
from pydub import AudioSegment

app = FastAPI()

def voice_changer(input_data, pitch_factor=1.25, tempo_factor=1.15):
    try:
        audio, sr = librosa.load(io.BytesIO(input_data), sr=16000)

        # Apply pitch shift
        audio_pitch_shifted = librosa.effects.pitch_shift(audio, sr=sr, n_steps=int(pitch_factor), bins_per_octave=24)

        # Apply time stretch (tempo change)
        audio_time_stretched = librosa.effects.time_stretch(audio_pitch_shifted, rate=tempo_factor)

        output_buffer = io.BytesIO()
        sf.write(output_buffer, audio_time_stretched, sr, format='WAV')
        output_buffer.seek(0)
        return output_buffer

    except Exception as e:
        print(f"Error: {e}")
        return None

def change_wav_mp3(input_file):
    try:
        sound = AudioSegment.from_file(io.BytesIO(input_file), format='wav')
        mp3_buffer = io.BytesIO()
        sound.export(mp3_buffer, format="mp3")
        mp3_buffer.seek(0)
        return mp3_buffer
    except Exception as e:
        print(f"The problem: {e}")
        return None

@app.post("/process-audio")
async def process_audio(
    file: UploadFile = File(...),
    option: str = Form('high_pitch_low_tempo')
):
    try:
        # Read the file content
        wav_data = await file.read()

        # Map options to pitch and tempo factors
        options_map = {
            'high_pitch_low_tempo': (4, 0.7),
            'high_pitch_high_tempo': (4, 1.5),
            'low_pitch_low_tempo': (-4, 0.7),
            'low_pitch_high_tempo': (-4, 1.5)
        }
        
        pitch_factor, tempo_factor = options_map.get(option, (4, 0.7))

        # Step 1: Modify the voice (pitch and tempo) in-memory
        modified_audio = voice_changer(wav_data, pitch_factor, tempo_factor)
        if modified_audio is None:
            return JSONResponse(status_code=500, content={"error": "Voice modification failed"})

        # Step 2: Convert the modified WAV to MP3 (in-memory)
        mp3_audio = change_wav_mp3(modified_audio.read())
        if mp3_audio is None:
            return JSONResponse(status_code=500, content={"error": "WAV to MP3 conversion failed"})

        # Step 3: Return the MP3 file as a streaming response
        return StreamingResponse(mp3_audio, media_type="audio/mpeg", headers={"Content-Disposition": "attachment; filename=modified_audio.mp3"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
