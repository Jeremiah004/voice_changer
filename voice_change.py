from flask import Flask, request, send_file, jsonify
import librosa
import soundfile as sf
import io
from pydub import AudioSegment

app = Flask(__name__)

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

@app.route('/process-audio', methods=['POST'])
def process_audio():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Read the file content
        wav_data = file.read()

        # Get the pitch and tempo factors from the request
        option = request.form.get('option', 'high_pitch_low_tempo')

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
            return jsonify({"error": "Voice modification failed"}), 500

        # Step 2: Convert the modified WAV to MP3 (in-memory)
        mp3_audio = change_wav_mp3(modified_audio.read())
        if mp3_audio is None:
            return jsonify({"error": "WAV to MP3 conversion failed"}), 500

        # Step 3: Return the MP3 file
        return send_file(mp3_audio, mimetype='audio/mpeg', as_attachment=True, download_name='modified_audio.mp3')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
