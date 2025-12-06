import os
import requests
import shutil
from core.agent_state import AgentState

def generate_images_node(state: AgentState):
    """
    Downloads images from the URLs provided in segment_visual_prompts.
    Falls back to placeholder if download fails.
    """
    prompts = state.get("segment_visual_prompts", [])
    playlist_dir = state.get("playlist_dir", "data")
    
    if not prompts:
        return {}
        
    print(f"🖼️  Processing {len(prompts)} images...")
    
    # Ensure we have a default placeholder just in case
    placeholder_path = os.path.join(playlist_dir, "placeholder.jpg")
    if not os.path.exists(placeholder_path):
        try:
            from PIL import Image
            img = Image.new('RGB', (1920, 1080), color = (73, 109, 137))
            img.save(placeholder_path)
        except ImportError:
            pass

    downloaded_images = []
    
    # Standard User-Agent to avoid 403 from Wikipedia/Wikimedia
    headers = {
        'User-Agent': 'PlaylistCuratorBot/1.0 (mailto:your-email@example.com)'
    }

    for i, url in enumerate(prompts):
        target_path = os.path.join(playlist_dir, f"image_{i+1:03d}.jpg")
        
        # Check if already downloaded to save time
        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            print(f"  - Image {i+1} already exists. Skipping download.")
            downloaded_images.append(target_path)
            continue
        
        if url and url.startswith("http"):
            print(f"  - Downloading image for segment {i+1}: {url}...")
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
        
        # Fallback
        if os.path.exists(placeholder_path):
            print(f"    ⚠️ Using placeholder for segment {i+1}")
            downloaded_images.append(placeholder_path)
        else:
            downloaded_images.append(None)
            
    return {"downloaded_images": downloaded_images}

def create_video_node(state: AgentState):
    """
    Takes audio files and downloaded images to create video files.
    Uses FFmpeg for Ken Burns effect or simple static image.
    """
    audio_paths = state.get("audio_paths", [])
    playlist_dir = state.get("playlist_dir", "data")
    
    if not audio_paths:
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
        return {"video_paths": []}
        
    print(f"🎥 Creating videos for {len(audio_paths)} segments using {ffmpeg_cmd}...")
    
    for i, audio_path in enumerate(audio_paths):
        if not os.path.exists(audio_path):
            continue
            
        filename = f"part_{i+1:03d}.mp4"
        output_path = os.path.join(playlist_dir, filename)
        
        # Skip if video already exists
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
             print(f"  - Video {filename} already exists. Skipping render.")
             video_paths.append(output_path)
             continue

        # Look for specific image first, then placeholder
        image_path = os.path.join(playlist_dir, f"image_{i+1:03d}.jpg")
        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
             image_path = os.path.join(playlist_dir, "placeholder.jpg")
             
        if not os.path.exists(image_path):
            print(f"  ⚠️ No image found for segment {i+1}. Skipping.")
            continue

        # Simple ffmpeg command to combine audio and image
        # Loop image, tune for still image, shortest (end when audio ends)
        # -pix_fmt yuv420p is needed for broad compatibility
        # Added scale filter to ensure dimensions are divisible by 2 for libx264
        cmd = (
            f"{ffmpeg_cmd} -y -loop 1 -i '{image_path}' -i '{audio_path}' "
            f"-c:v libx264 -c:a aac -b:a 192k -pix_fmt yuv420p "
            f"-vf 'scale=trunc(iw/2)*2:trunc(ih/2)*2' "
            f"-shortest '{output_path}' > /dev/null 2>&1"
        )
        
        print(f"  - Rendering {filename}...")
        ret = os.system(cmd)
        
        if ret == 0:
            video_paths.append(output_path)
        else:
            print(f"    ❌ FFmpeg failed for {filename}. (Command: {cmd})")
            
    print(f"✅ Created {len(video_paths)} video files.")
    
    return {"video_paths": video_paths}
