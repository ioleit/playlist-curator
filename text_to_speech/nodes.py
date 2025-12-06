from .tts import KokoroTTS
from core.agent_state import AgentState
import os

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
    segments = state.get("narrative_segments", [])
    
    # Fallback for backward compatibility if only monolithic text exists
    if not segments and state.get("text"):
         print("⚠️ No segments found, treating full text as single segment.")
         segments = [state.get("text")]

    if not segments:
        return {"audio_paths": []}
        
    if tts_engine:
        # Use the playlist directory if available, otherwise fallback to data
        output_dir = state.get("playlist_dir", "data")
        os.makedirs(output_dir, exist_ok=True)
        
        audio_paths = []
        
        print(f"🗣️  Generating audio for {len(segments)} segments...")
        
        for i, segment in enumerate(segments):
            if not segment.strip():
                continue
                
            # Format: part_001.wav, part_002.wav, etc.
            filename_base = f"part_{i+1:03d}"
            wav_filename = f"{filename_base}.wav"
            txt_filename = f"{filename_base}.txt"
            
            wav_path = os.path.join(output_dir, wav_filename)
            txt_path = os.path.join(output_dir, txt_filename)
            
            # Save the text file
            with open(txt_path, "w") as f:
                f.write(segment)
            
            # Check if audio already exists to save time
            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                 # Check if text content has changed? For now assume file existence is enough for simple caching
                 # In a real system we'd hash the text and check against metadata
                 print(f"  - Audio Part {i+1} already exists. Skipping generation.")
                 audio_paths.append(wav_path)
                 continue

            print(f"  - Generating Part {i+1} ({len(segment)} chars)...")
            audio_file = tts_engine.generate_audio(segment, output_file=wav_path)
            audio_paths.append(audio_file)
            
        print(f"💾 Generated {len(audio_paths)} audio files.")
        return {"audio_paths": audio_paths}
    else:
        print("⚠️ TTS engine not available. Skipping speech generation.")
        return {"audio_paths": []}
