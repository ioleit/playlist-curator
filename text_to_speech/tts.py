import soundfile as sf
from kokoro_onnx import Kokoro
import os

class KokoroTTS:
    def __init__(self, model_path="models/kokoro-v1.0.onnx", voices_path="models/voices-v1.0.bin"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if not os.path.exists(voices_path):
            raise FileNotFoundError(f"Voices file not found: {voices_path}")
            
        self.kokoro = Kokoro(model_path, voices_path)

    def generate_audio(self, text: str, output_file: str = "output.wav", voice: str = "af_heart", speed: float = 1.0, lang: str = "en-us"):
        """
        Generates audio from text and saves it to a file.
        
        Args:
            text (str): The text to convert to speech.
            output_file (str): The path to save the generated audio file.
            voice (str): The voice style to use.
            speed (float): The speed of the speech.
            lang (str): The language code.
            
        Returns:
            str: The path to the generated audio file.
        """
        print(f"Generating audio for text: '{text[:50]}...'")
        samples, sample_rate = self.kokoro.create(
            text, 
            voice=voice, 
            speed=speed, 
            lang=lang
        )
        
        sf.write(output_file, samples, sample_rate)
        print(f"Audio saved to {output_file}")
        return output_file

