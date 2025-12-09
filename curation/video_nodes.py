import os
import requests
import shutil
import json
from core.agent_state import AgentState
from core.config import get_playlist_dir, playlist_path

def generate_images_node(state: AgentState):
    """
    Downloads images from the URLs provided in curated_playlist.json.
    Falls back to placeholder if download fails.
    """
    playlist_id = state["playlist_id"]
    playlist_dir = get_playlist_dir(playlist_id)
    curated_json_path = playlist_path(playlist_id, "curated_playlist.json")
    
    if not os.path.exists(curated_json_path):
        print(f"❌ Error: {curated_json_path} not found. Cannot download images.")
        raise FileNotFoundError(f"{curated_json_path} missing")
        
    try:
        with open(curated_json_path, "r") as f:
            curated_data = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in {curated_json_path}")
        raise

    items = curated_data.get("items", [])
    # Filter for narrative items that have an image_url
    narrative_items = [item for item in items if item.get("type") == "narrative"]
    
    if not narrative_items:
        return {}
        
    print(f"🖼️  Processing images for {len(narrative_items)} segments...")
    
    # Ensure we have a default placeholder just in case
    placeholder_path = playlist_path(playlist_id, "placeholder.jpg")
    if not os.path.exists(placeholder_path):
        try:
            from PIL import Image
            img = Image.new('RGB', (1920, 1080), color = (73, 109, 137))
            img.save(placeholder_path)
        except ImportError:
            print("❌ Error: Pillow library not found. Cannot create placeholder image.")
            print("   Please install it using: pip install Pillow")
            print("   Without an image, video generation will be skipped.")

    downloaded_images = []
    
    # Standard User-Agent to avoid 403 from Wikipedia/Wikimedia
    headers = {
        'User-Agent': 'PlaylistCuratorBot/1.0 (mailto:your-email@example.com)'
    }

    for i, item in enumerate(narrative_items):
        url = item.get("image_url")
        # Determine image filename based on the audio filename pattern or a new field
        # We'll use the base of the audio filename but with .jpg extension
        audio_filename = item.get("audio_filename")
        if not audio_filename:
             continue
             
        base_name = os.path.splitext(audio_filename)[0]
        target_path = playlist_path(playlist_id, f"{base_name}.jpg")
        
        # Check if already downloaded to save time
        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            print(f"  - Image for {base_name} already exists. Skipping download.")
            downloaded_images.append(target_path)
            continue
        
        if url and url.startswith("http"):
            print(f"  - Downloading image for {base_name}: {url}...")
            try:
                response = requests.get(url, headers=headers, stream=True, timeout=10)
                if response.status_code == 200:
                    with open(target_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    print(f"    ✅ Saved to {target_path}")
                    downloaded_images.append(target_path)
                    continue
                else:
                    print(f"    ❌ Failed to download (status {response.status_code})")
            except Exception as e:
                print(f"    ❌ Error downloading: {e}")
            
    return {"downloaded_images": downloaded_images}

def create_video_node(state: AgentState):
    """
    Takes audio files and downloaded images to create video files.
    Uses FFmpeg for Ken Burns effect or simple static image.
    """
    playlist_id = state.get("playlist_id", "example")
    playlist_dir = get_playlist_dir(playlist_id)
    curated_json_path = playlist_path(playlist_id, "curated_playlist.json")
    
    if not os.path.exists(curated_json_path):
        print(f"❌ Error: {curated_json_path} not found. Cannot create videos.")
        raise FileNotFoundError(f"{curated_json_path} missing")
        
    try:
        with open(curated_json_path, "r") as f:
            curated_data = json.load(f)
    except json.JSONDecodeError:
        raise

    items = curated_data.get("items", [])
    narrative_items = [item for item in items if item.get("type") == "narrative"]
    
    if not narrative_items:
        return {"video_paths": []}
        
    video_paths = []
    
    # Detect ffmpeg binary
    ffmpeg_cmd = shutil.which("ffmpeg")
    if not ffmpeg_cmd:
        # Try common Homebrew path if not found in PATH
        possible_path = "/opt/homebrew/bin/ffmpeg"
        if os.path.exists(possible_path):
            ffmpeg_cmd = possible_path
            
    if not ffmpeg_cmd:
        print("❌ Error: FFmpeg not found. Please install it (e.g., 'brew install ffmpeg').")
        raise RuntimeError("FFmpeg not found")
        
    print(f"🎥 Creating videos for {len(narrative_items)} segments using {ffmpeg_cmd}...")
    
    from speech_to_video.video_creator import VideoCreator
    creator = VideoCreator(output_dir=playlist_dir)

    for i, item in enumerate(narrative_items):
        audio_filename = item.get("audio_filename")
        video_filename = item.get("video_filename")
        
        if not audio_filename or not video_filename:
            print(f"  ❌ Error: Missing filename config for item {i}")
            continue
            
        audio_path = playlist_path(playlist_id, audio_filename)
        output_path = playlist_path(playlist_id, video_filename)
        
        if not os.path.exists(audio_path):
            print(f"  ⚠️ Audio missing: {audio_filename}. Skipping.")
            continue
            
        # Skip if video already exists
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
             print(f"  - Video {video_filename} already exists. Skipping render.")
             video_paths.append(output_path)
             continue

        # Look for specific image first
        # We assume image has same base name as audio/video but .jpg
        base_name = os.path.splitext(audio_filename)[0]
        image_path = playlist_path(playlist_id, f"{base_name}.jpg")
        
        # If specific image exists, use it
        # If not, pass None so VideoCreator finds the background.png and uses waveform
        if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
            pass # image_path is valid
        else:
            image_path = None # Trigger fallback in VideoCreator
            
        result_path = creator.create_video(
            audio_path=audio_path, 
            image_path=image_path, 
            output_filename=video_filename,
            use_waveform=(image_path is None) # Force waveform if falling back
        )
        
        if result_path:
            video_paths.append(result_path)
            
    print(f"✅ Created {len(video_paths)} video files.")
    
    return {"video_paths": video_paths}

