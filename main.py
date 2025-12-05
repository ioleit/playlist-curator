import sys
from curator_graph import app

def main():
    if len(sys.argv) > 1:
        topic = sys.argv[1]
    else:
        topic = "Artificial Intelligence"
        
    print(f"Running workflow for topic: {topic}")
    
    initial_state = {"topic": topic, "text": None, "audio_path": None}
    
    # Run the graph
    result = app.invoke(initial_state)
    
    print("\n--- Workflow Complete ---")
    print(f"Topic: {result['topic']}")
    print(f"Generated Text: {result['text']}")
    print(f"Audio Path: {result['audio_path']}")

    if result['audio_path']:
        print(f"\nYou can play the audio with: afplay {result['audio_path']} (on macOS) or aplay/mpv/vlc")

if __name__ == "__main__":
    main()

