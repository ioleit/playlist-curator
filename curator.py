import sys
import os
import time
import argparse
import shutil
from langgraph.graph import StateGraph, END
from core.agent_state import AgentState
from text_to_speech.nodes import generate_speech_node
from curation.nodes import curate_playlist_node, verify_curation_node
from curation.video_nodes import generate_images_node, create_video_node
from core.config import PlaylistConfig, get_playlist_dir

# --- Graph Definition ---

def build_workflow(inference_only=False):
    builder = StateGraph(AgentState)

    builder.add_node("curate_playlist", curate_playlist_node)
    builder.add_node("verify_curation", verify_curation_node)
    if not inference_only:
        builder.add_node("generate_speech", generate_speech_node)
        builder.add_node("generate_images", generate_images_node)
        builder.add_node("create_video", create_video_node)
    builder.set_entry_point("curate_playlist")

    builder.add_edge("curate_playlist", "verify_curation")

    if inference_only:
         builder.add_edge("verify_curation", END)
    else:
        builder.add_edge("verify_curation", "generate_speech")
        builder.add_edge("generate_speech", "generate_images")
        builder.add_edge("generate_images", "create_video")
        builder.add_edge("create_video", END)

    return builder.compile()

# --- Main Execution ---

def main():
    start_time = time.time()
    print("🚀 Starting Playlist Curator Workflow...")

    # Parse arguments
    parser = argparse.ArgumentParser(description="Playlist Curator Workflow")
    parser.add_argument("playlist_id", help="ID/name of the playlist (under data/playlists/)")
    parser.add_argument("--clean", action="store_true", help="Remove generated files before starting")
    parser.add_argument("--inference-only", action="store_true", help="Only generate the playlist text/script, skip TTS and video generation")
    parser.add_argument("--skip-validation", action="store_true", help="Skip checking for prompt equality and re-validating tracks (implies resume)")
    args = parser.parse_args()
    
    playlist_id = args.playlist_id
    
    # Construct paths
    playlist_dir = get_playlist_dir(playlist_id)
    config_path = os.path.join(playlist_dir, "config.json")
    
    # Ensure playlist directory exists
    if not os.path.exists(playlist_dir):
        print(f"Error: Playlist directory '{playlist_dir}' not found.")
        print(f"Expected structure: data/playlists/<id>/config.json")
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
    playlist_config = PlaylistConfig.load(playlist_dir)

    topic = playlist_config.topic
    system_prompt = playlist_config.system_prompt
    duration_str = playlist_config.duration
    seconds = playlist_config.get_duration_seconds()

    print(f"Target Duration: {duration_str} ({seconds} seconds)")

    print(f"Running workflow for playlist: {playlist_id}")
    print(f"Topic: {topic}")
    print(f"Output directory: {playlist_dir}")
    if args.inference_only:
        print("Mode: Inference Only (No Audio/Video Generation)")
    
    initial_state = {
        "playlist_id": playlist_id,
        "skip_validation": args.skip_validation
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
    raw_script = result.get('raw_script')
    script_preview = raw_script[:200] + "..." if raw_script and len(raw_script) > 200 else raw_script
    print(f"Generated Script (preview): {script_preview}")
    
    curated = result.get("curated_playlist")
    if curated:
        items = curated.get("items", [])
        narrations = sum(1 for i in items if i.get("type") == "narrative")
        tracks = sum(1 for i in items if i.get("type") == "track")
        print(f"\n📄 Curated items -> Narrations: {narrations}, Tracks: {tracks}")

if __name__ == "__main__":
    main()
