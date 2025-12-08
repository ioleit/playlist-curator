import sys
import json
import os
import time
import argparse
import shutil
import pytimeparse
from langgraph.graph import StateGraph, END
from core.agent_state import AgentState
from text_to_speech.nodes import generate_speech_node
from curation.nodes import curate_playlist_node, verify_curation_node
from curation.video_nodes import generate_images_node, create_video_node

# --- Graph Definition ---

def build_workflow(inference_only=False):
    # Build the graph
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("curate_playlist", curate_playlist_node)
    builder.add_node("verify_curation", verify_curation_node)
    
    # Only add speech and video nodes if not in inference-only mode
    if not inference_only:
        builder.add_node("generate_speech", generate_speech_node)
        builder.add_node("generate_images", generate_images_node)
        builder.add_node("create_video", create_video_node)

    # Set entry point
    builder.set_entry_point("curate_playlist")

    # Linear flow: Curate -> Verify -> (Maybe Speech -> Images -> Video)
    if inference_only:
         builder.add_edge("curate_playlist", "verify_curation")
         builder.add_edge("verify_curation", END)
    else:
        builder.add_edge("curate_playlist", "verify_curation")
        builder.add_edge("verify_curation", "generate_speech")
        # Temporarily stopped here in previous edits, but restoring logic for full flow if wanted,
        # or keeping the shortcut. Let's keep the shortcut logic consistent with previous state
        # but allow full flow if we wanted to uncomment.
        
        # builder.add_edge("generate_speech", "generate_images") 
        # builder.add_edge("generate_images", "create_video")
        # builder.add_edge("create_video", END)
        
        # Current shortcut: End after speech
        builder.add_edge("generate_speech", END)

    # Compile the graph
    return builder.compile()

# --- Main Execution ---

def main():
    start_time = time.time()
    print("🚀 Starting Playlist Curator Workflow...")

    # Parse arguments
    parser = argparse.ArgumentParser(description="Playlist Curator Workflow")
    parser.add_argument("playlist_name", nargs="?", default="example", help="Name of the playlist directory (in data/playlists/)")
    parser.add_argument("--clean", action="store_true", help="Remove generated files before starting")
    parser.add_argument("--inference-only", action="store_true", help="Only generate the playlist text/script, skip TTS and video generation")
    args = parser.parse_args()
    
    playlist_name = args.playlist_name
    
    # Construct paths
    base_dir = "data/playlists"
    playlist_dir = os.path.join(base_dir, playlist_name)
    config_path = os.path.join(playlist_dir, "config.json")
    
    # Ensure playlist directory exists
    if not os.path.exists(playlist_dir):
        print(f"Error: Playlist directory '{playlist_dir}' not found.")
        print(f"Expected structure: {base_dir}/<name>/config.json")
        sys.exit(1)

    # Handle --clean
    if args.clean:
        print(f"⚠️  WARNING: You are about to delete all generated files in '{playlist_dir}'.")
        print(f"    This will preserve 'config.json' but remove scripts, audio, video, and images.")
        
        # Non-interactive mode check could be added here, but user asked for confirmation
        try:
            confirm = input("    Are you sure you want to continue? (y/N): ").strip().lower()
        except EOFError:
            confirm = 'n' # Safe default for non-interactive
            
        if confirm != 'y':
            print("Clean cancelled.")
            sys.exit(0)
        
        # Perform clean
        print(f"Cleaning '{playlist_dir}'...")
        count = 0
        for filename in os.listdir(playlist_dir):
            if filename != "config.json":
                file_path = os.path.join(playlist_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                        count += 1
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        count += 1
                except Exception as e:
                    print(f"  Failed to delete {filename}. Reason: {e}")
        print(f"Clean complete. Removed {count} items.\n")
        
    # Load config
    try:
        with open(config_path, "r") as f:
            request_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        sys.exit(1)

    topic = request_config.get("topic", "Artificial Intelligence")
    if isinstance(topic, list):
        topic = " ".join(topic)
    system_prompt = request_config.get("system_prompt", "default")
    duration_str = request_config.get("duration", "30m") # Default to 30m if not specified

    if duration_str:
        seconds = pytimeparse.parse(duration_str)
        if seconds is None:
            print(f"Error: Invalid duration format '{duration_str}'")
            sys.exit(1)
        if seconds > 3 * 60 * 60: # 3 hours
            print(f"Error: Duration '{duration_str}' exceeds maximum of 3 hours.")
            sys.exit(1)
        print(f"Target Duration: {duration_str} ({seconds} seconds)")

    print(f"Running workflow for playlist: {playlist_name}")
    print(f"Topic: {topic}")
    print(f"Output directory: {playlist_dir}")
    if args.inference_only:
        print("Mode: Inference Only (No Audio/Video Generation)")
    
    initial_state = {
        "topic": topic,
        "duration": duration_str,
        "playlist_dir": playlist_dir,
        "system_prompt": system_prompt,
        "text": None,
        "audio_path": None
    }
    
    # Run the graph
    print("Building workflow graph...")
    app = build_workflow(inference_only=args.inference_only)
    print("Executing workflow...")
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
