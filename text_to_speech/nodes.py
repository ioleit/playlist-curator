from .tts import KokoroTTS
from core.agent_state import AgentState
from core.config import get_playlist_dir, playlist_path
import os
import json

# Initialize TTS engine (doing this globally to avoid reloading model on every call, 
# though in a real app you might want to manage this differently)
try:
    tts_engine = KokoroTTS()
except FileNotFoundError as e:
    print(f"Warning: TTS models not found. Please run models/download_models.py. {e}")
    tts_engine = None

def generate_speech_node(state: AgentState):
    """
    Node that converts the generated text segments to speech files.
    """
    # Load curated playlist from JSON
    playlist_id = state["playlist_id"]
    playlist_dir = get_playlist_dir(playlist_id)
    curated_json_path = playlist_path(playlist_id, "curated_playlist.json")
    
    if not os.path.exists(curated_json_path):
        print(f"❌ Error: {curated_json_path} not found. Cannot generate speech.")
        # Fail early
        raise FileNotFoundError(f"{curated_json_path} missing")
        
    try:
        with open(curated_json_path, "r") as f:
            curated_data = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in {curated_json_path}")
        raise

    items = curated_data.get("items", [])
    narrative_items = [item for item in items if item.get("type") == "narrative"]
    
    if not narrative_items:
        print("⚠️ No narrative segments found in curated playlist.")
        return {"audio_paths": []}
        
    if tts_engine:
        os.makedirs(playlist_dir, exist_ok=True)
        
        audio_paths = []
        
        print(f"🗣️  Generating audio for {len(narrative_items)} segments...")
        
        for i, item in enumerate(narrative_items):
            segment = item.get("text", "")
            if not segment.strip():
                continue
                
            # Use filename from JSON
            wav_filename = item.get("audio_filename")
            if not wav_filename:
                # Fallback should not happen if verified correctly, but just in case
                print(f"  ❌ Error: Missing audio_filename for segment {i+1}")
                continue
                
            wav_path = playlist_path(playlist_id, wav_filename)
            
            # Check if audio already exists to save time
            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                 print(f"  - Audio {wav_filename} already exists. Skipping generation.")
                 audio_paths.append(wav_path)
                 continue

            print(f"  - Generating {wav_filename} ({len(segment)} chars)...")
            audio_file = tts_engine.generate_audio(segment, output_file=wav_path)
            audio_paths.append(audio_file)
            
        print(f"💾 Generated {len(audio_paths)} audio files.")
        return {"audio_paths": audio_paths}
    else:
        print("❌ TTS engine not available. Cannot generate speech.")
        raise RuntimeError("TTS engine not available")
