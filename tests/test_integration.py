import os
import sys
import wave
import contextlib

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from curator import build_workflow

def test_main_flow():
    # SKIP integration test if no API key is present to avoid failure in CI/pre-commit
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Skipping integration test: No API key found.")
        return

    topic = "IntegrationTest"
    playlist_id = "integration_test"
    # Use a temp dir for playlist
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            playlist_dir = os.path.join("data", "playlists", playlist_id)
            os.makedirs(playlist_dir, exist_ok=True)

            # Create a dummy config
            config_path = os.path.join(playlist_dir, "config.json")
            with open(config_path, "w") as f:
                f.write(json.dumps({
                    "topic": topic,
                    "duration": "10m",
                    "system_prompt": "default"
                }))

            initial_state = {
                "playlist_id": playlist_id
            }
            
            print(f"Running workflow for topic: {topic}")
            app = build_workflow(inference_only=True) # Run inference only to avoid TTS costs/time
            result = app.invoke(initial_state)
            
            # Check result keys
            assert result['raw_script'] is not None
        finally:
            os.chdir(original_cwd)
        
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

