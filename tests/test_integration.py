import os
import sys
import wave
import contextlib

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from curator import build_workflow

def test_main_flow():
    # SKIP integration test if no API key is present to avoid failure in CI/pre-commit
    if not os.environ.get("OPENROUTER_API_KEY") and not os.path.exists("config.json"):
        print("Skipping integration test: No API key or config found.")
        return

    topic = "IntegrationTest"
    # Use a temp dir for playlist
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a dummy config
        config_path = os.path.join(temp_dir, "config.json")
        with open(config_path, "w") as f:
            f.write('{"topic": "IntegrationTest", "model": "google/gemini-2.0-flash-exp:free"}')

        initial_state = {
            "topic": topic, 
            "playlist_dir": temp_dir,
            "system_prompt": "default"
        }
        
        print(f"Running workflow for topic: {topic}")
        app = build_workflow(inference_only=True) # Run inference only to avoid TTS costs/time
        result = app.invoke(initial_state)
        
        # Check result keys
        assert result['topic'] == topic
        assert result['text'] is not None
        
        # We can't check audio_paths because we ran inference_only=True
        # If we want to test audio, we need TTS mock or real TTS.
        
        print("Integration test finished (Inference Only).")

if __name__ == "__main__":
    try:
        test_main_flow()
        print("Test passed!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)

