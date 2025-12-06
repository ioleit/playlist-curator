import os
import sys
import wave
import contextlib

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from curator_graph import app

def test_main_flow():
    topic = "IntegrationTest"
    initial_state = {"topic": topic, "text": None, "audio_path": None}
    
    print(f"Running workflow for topic: {topic}")
    result = app.invoke(initial_state)
    
    # Check result keys
    assert result['topic'] == topic
    assert result['text'] is not None
    assert result['audio_path'] is not None
    
    audio_path = result['audio_path']
    print(f"Generated audio path: {audio_path}")
    
    # Check file existence
    assert os.path.exists(audio_path), f"Audio file does not exist at {audio_path}"
    
    # Check WAV file properties
    with contextlib.closing(wave.open(audio_path, 'r')) as f:
        frames = f.getnframes()
        rate = f.getframerate()
        duration = frames / float(rate)
        channels = f.getnchannels()
        
        print(f"Audio duration: {duration:.2f}s")
        print(f"Sample rate: {rate}Hz")
        print(f"Channels: {channels}")
        
        assert duration > 0, "Audio duration should be positive"
        assert rate > 0, "Sample rate should be positive"
        assert channels > 0, "Channels should be positive"

if __name__ == "__main__":
    try:
        test_main_flow()
        print("Test passed!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)

