import sys
import os

# Add project root to path so we can import from text_to_speech and speech_to_video
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from text_to_speech.tts import KokoroTTS
from speech_to_video.video_creator import VideoCreator

def test_generation():
    text = "This is a test of the speech to video system using the new background compositing feature. We expect to see a waveform over the background image."
    output_dir = "speech_to_video/test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Generate Audio
    print("--- Step 1: generating audio ---")
    tts = KokoroTTS()
    audio_file = os.path.join(output_dir, "test_audio.wav")
    tts.generate_audio(text, output_file=audio_file)
    
    if not os.path.exists(audio_file):
        print("Failed to generate audio.")
        return

    # 2. Generate Video
    print("\n--- Step 2: generating video ---")
    creator = VideoCreator(output_dir=output_dir)
    
    # We want to test the fallback logic, so we won't provide an image path explicitly,
    # but we ensure a background.png exists in data/ or the output dir if we want to test that specific case.
    # The user said "global" background.png is at data/background.png.
    
    video_path = creator.create_video(audio_file)
    
    if video_path and os.path.exists(video_path):
        print(f"\nSUCCESS: Video generated at {video_path}")
    else:
        print("\nFAILURE: Video generation failed.")

if __name__ == "__main__":
    test_generation()


