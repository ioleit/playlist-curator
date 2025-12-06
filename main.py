import sys
import json
import os
import time
from curator_graph import app

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
        
    print(f"Running workflow for playlist: {playlist_name}")
    print(f"Topic: {topic}")
    print(f"Output directory: {playlist_dir}")
    
    initial_state = {
        "topic": topic,
        "num_songs": num_songs,
        "playlist_dir": playlist_dir,
        "text": None,
        "audio_path": None
    }
    
    # Run the graph
    result = app.invoke(initial_state)
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"\n✅ Workflow Complete in {duration:.2f} seconds")
    
    # Save the generated text script to the directory as well
    if result.get('text'):
        script_path = os.path.join(playlist_dir, "script.txt")
        with open(script_path, "w") as f:
            f.write(result['text'])
        print(f"Script saved to: {script_path}")

    # Save verified tracks if available
    if result.get('verified_tracks'):
        tracks_path = os.path.join(playlist_dir, "tracks.json")
        with open(tracks_path, "w") as f:
            json.dump(result['verified_tracks'], f, indent=2)
        print(f"Verified tracks saved to: {tracks_path}")
        
        print("\n🎶 Verified Tracks Found:")
        for track in result['verified_tracks']:
             print(f"  - {track.get('title')} by {track.get('artist')} (ID: {track.get('video_id')})")
        print("")

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
            
        # Generate a simple m3u playlist for local testing
        m3u_path = os.path.join(playlist_dir, "playlist_local.m3u")
        with open(m3u_path, "w") as f:
            # Interleave Logic: Audio Segment 1 -> Track 1 -> Audio Segment 2 -> ...
            
            segments = result.get("narrative_segments", [])
            tracks = result.get("verified_tracks", [])
            
            # Usually we have N+1 segments for N tracks (Intro -> Track -> Middle -> Track -> Outro)
            # But let's be robust to any count
            
            max_len = max(len(video_paths), len(tracks))
            
            for i in range(max_len):
                # Add narrative segment if available
                if i < len(video_paths):
                     f.write(f"{os.path.abspath(video_paths[i])}\n")
                
                # Add music track link
                if i < len(tracks):
                     track = tracks[i]
                     f.write(f"#EXTINF:{track.get('duration', 0)},{track.get('title')} - {track.get('artist')}\n")
                     f.write(f"https://music.youtube.com/watch?v={track.get('video_id')}\n")

        print(f"\nGenerated local M3U playlist at: {m3u_path}")

if __name__ == "__main__":
    main()
