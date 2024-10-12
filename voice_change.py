from flask import Flask, request, send_file, jsonify
import librosa
import soundfile as sf
import io
from pydub import AudioSegment
import os



app = Flask(__name__)


def voice_changer(input_data, pitch_factor=1.25, tempo_factor=1.15):
    """
    Change the pitch and tempo of an audio file in-memory and return modified data.
    
    Parameters:
    - input_data: in-memory WAV file (binary data)
    - pitch_factor: the factor by which to shift the pitch
    - tempo_factor: the factor by which to change the tempo
    """
    try:
        # Load audio from the in-memory WAV file
        audio, sr = librosa.load(io.BytesIO(input_data), sr=16000)

        # Apply pitch shift
        audio_pitch_shifted = librosa.effects.pitch_shift(audio, sr=sr, n_steps=int(pitch_factor), bins_per_octave=24)

        # Apply time stretch (tempo change)
        audio_time_stretched = librosa.effects.time_stretch(audio_pitch_shifted, rate=tempo_factor)

        # Save the modified audio to an in-memory buffer
        output_buffer = io.BytesIO()
        sf.write(output_buffer, audio_time_stretched, sr, format='WAV')

        # Return the modified audio data (in-memory)
        output_buffer.seek(0)
        return output_buffer

    except Exception as e:
        print(f"Error: {e}")
        return None


def change_wav_mp3(input_file):
    """
    Convert a WAV file (in-memory) to an MP3 file (in-memory).
    """
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
    """
    API endpoint to process a WAV file: modify voice, and return MP3.
    """
    try:
        # Check if a file is in the request
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        # Get the uploaded WAV file
        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Read the file content
        wav_data = file.read()

        # Get the pitch and tempo option from the form
        option = request.form.get('option', 'high_pitch_low_tempo')  # Default option

        # Define the pitch and tempo based on the option
        options_map = {
            'high_pitch_low_tempo': (4, 0.7),  
            'high_pitch_high_tempo': (4, 1.5), 
            'low_pitch_low_tempo': (-4, 0.7),  
            'low_pitch_high_tempo': (-4, 1.5)  
        }

        # Get the pitch and tempo factors based on the user's selected option
        pitch_factor, tempo_factor = options_map.get(option, (4, 0.7))  # Default to high pitch, low tempo

        # Step 1: Modify the voice (pitch and tempo) in-memory
        modified_audio = voice_changer(wav_data, pitch_factor, tempo_factor)

        if modified_audio is None:
            return jsonify({"error": "Error during voice modification"}), 500

        # Step 2: Convert the modified WAV to MP3 (in-memory)
        mp3_audio = change_wav_mp3(modified_audio.read())

        if mp3_audio is None:
            return jsonify({"error": "Error during WAV to MP3 conversion"}), 500

        # Step 3: Send the final MP3 as a downloadable response
        return send_file(mp3_audio, as_attachment=True, download_name="output_modified.mp3", mimetype="audio/mpeg")

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
