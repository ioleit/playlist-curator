from .tts import KokoroTTS
from core.agent_state import AgentState

# Initialize TTS engine (doing this globally to avoid reloading model on every call, 
# though in a real app you might want to manage this differently)
try:
    tts_engine = KokoroTTS()
except FileNotFoundError as e:
    print(f"Warning: TTS models not found. Please run models/download_models.py. {e}")
    tts_engine = None

import os

def generate_speech_node(state: AgentState):
    """
    Node that converts the generated text to speech.
    """
    text = state.get("text")
    if not text:
        return {"audio_path": None}
        
    if tts_engine:
        # Generate a unique filename based on topic or timestamp could be better, 
        # but for simplicity using a fixed name or derived from topic
        safe_topic = "".join(x for x in state["topic"] if x.isalnum())
        
        # Ensure data directory exists
        output_dir = "data"
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f"output_{safe_topic}.wav")
        
        audio_file = tts_engine.generate_audio(text, output_file=output_path)
        return {"audio_path": audio_file}
    else:
        print("TTS engine not available. Skipping speech generation.")
        return {"audio_path": None}

