import sys
import json
import os
import time
from langgraph.graph import StateGraph, END
from core.agent_state import AgentState
from text_to_speech.nodes import generate_speech_node
from curation.nodes import curate_playlist_node, verify_curation_node
from curation.video_nodes import generate_images_node, create_video_node

# --- Graph Definition ---

# Build the graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("curate_playlist", curate_playlist_node)
builder.add_node("verify_curation", verify_curation_node)
builder.add_node("generate_speech", generate_speech_node)
builder.add_node("generate_images", generate_images_node)
builder.add_node("create_video", create_video_node)

# Set entry point
builder.set_entry_point("curate_playlist")

# Linear flow: Curate -> Verify -> Speech -> Images -> Video
builder.add_edge("curate_playlist", "verify_curation")
builder.add_edge("verify_curation", "generate_speech")
builder.add_edge("generate_speech", "generate_images") 
builder.add_edge("generate_images", "create_video")
builder.add_edge("create_video", END)

# Compile the graph
app = builder.compile()

# --- Main Execution ---

def main():
    start_time = time.time()
    print("🚀 Starting Playlist Curator Workflow...")

    # Default to "example" if no argument provided
    playlist_name = "example"
    if len(sys.argv) > 1:
        playlist_name = sys.argv[1]
    
    # Construct paths
    base_dir = "data/playlists"
    playlist_dir = os.path.join(base_dir, playlist_name)
    config_path = os.path.join(playlist_dir, "config.json")
    
    # Ensure playlist directory exists
    if not os.path.exists(playlist_dir):
        print(f"Error: Playlist directory '{playlist_dir}' not found.")
        print(f"Expected structure: {base_dir}/<name>/config.json")
        sys.exit(1)
        
    # Load config
    try:
        with open(config_path, "r") as f:
            request_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        sys.exit(1)

    topic = request_config.get("topic", "Artificial Intelligence")
    num_songs = request_config.get("num_songs", 5)
    system_prompt = request_config.get("system_prompt", "default")
        
    print(f"Running workflow for playlist: {playlist_name}")
    print(f"Topic: {topic}")
    print(f"Output directory: {playlist_dir}")
    
    initial_state = {
        "topic": topic,
        "num_songs": num_songs,
        "playlist_dir": playlist_dir,
        "system_prompt": system_prompt,
        "text": None,
        "audio_path": None
    }
    
    # Run the graph
    result = app.invoke(initial_state)
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"\n✅ Workflow Complete in {duration:.2f} seconds")
    
    # Print summary
    text = result.get('text')
    text_preview = text[:200] + "..." if text and len(text) > 200 else text
    print(f"Generated Text (preview): {text_preview}")
    
    audio_paths = result.get('audio_paths', [])
    video_paths = result.get('video_paths', [])
    
    if audio_paths:
        print(f"\n🎧 Generated {len(audio_paths)} Audio Segments")
        
    if video_paths:
        print(f"\n🎬 Generated {len(video_paths)} Video Segments:")
        for path in video_paths:
            print(f"  - {path}")

if __name__ == "__main__":
    main()

