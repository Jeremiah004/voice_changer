from pydub import AudioSegment
def change_aac_to_wav_in_memory(input_file, output_path):
    """
    Convert an AAC file to WAV format in-memory.
    
    Parameters:
    - input_file: the AAC file as a binary stream
    """
    try:
        # Convert AAC to WAV using pydub (in-memory)
        sound = AudioSegment.from_file(input_file, format='aac')
        
        # Save the WAV to an in-memory buffer
        sound.export(output_path, format='wav')
    
    except Exception as e:
        print(f"{e}")


    
    
    
    
# Example usage
if __name__ == "__main__":
    input_aac = "voice change.aac"  # Replace with your AAC file path
    
    # Call the main function with the AAC file
    with open(input_aac, 'rb') as f:
        change_aac_to_wav_in_memory(f, "modified.wav")