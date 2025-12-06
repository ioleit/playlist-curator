import os
import json
import argparse
import re
from urllib.parse import unquote
from googleapiclient.discovery import build
# Reuse authentication and helper from existing script
from update_youtube_playlist import get_authenticated_service, get_wikimedia_attribution

def get_playlist_id_by_name(youtube, channel_id, playlist_name):
    print(f"Searching for playlist '{playlist_name}' in channel '{channel_id}'...")
    request = youtube.playlists().list(
        part="snippet",
        channelId=channel_id,
        maxResults=50
    )
    while request:
        response = request.execute()
        for item in response.get('items', []):
            if item['snippet']['title'] == playlist_name:
                return item['id']
        request = youtube.playlists().list_next(request, response)
    return None

def get_all_playlist_items(youtube, playlist_id):
    items = []
    request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id,
        maxResults=50
    )
    while request:
        response = request.execute()
        items.extend(response.get('items', []))
        request = youtube.playlistItems().list_next(request, response)
    return items

def main():
    parser = argparse.ArgumentParser(description="Build youtube_playlists.json from uploaded clips and config.")
    parser.add_argument("playlist_dir", help="Path to the playlist directory (e.g. data/playlists/space_jazz)")
    parser.add_argument("--temp-name", help="Temporary name of the playlist on YouTube to look for (overrides topic name for search)", required=False)
    parser.add_argument("--playlist-id", help="Directly provide Playlist ID (skips search)", required=False)
    args = parser.parse_args()

    if not args.temp_name and not args.playlist_id:
        print("Error: Must provide either --temp-name or --playlist-id")
        return


    playlist_dir = args.playlist_dir
    if not os.path.exists(playlist_dir):
        print(f"Error: Directory {playlist_dir} not found.")
        return

    # Load configs
    if not os.path.exists("config.json"):
        print("Error: config.json not found in root.")
        return

    with open("config.json", "r") as f:
        global_config = json.load(f)
    
    config_path = os.path.join(playlist_dir, "config.json")
    tracks_path = os.path.join(playlist_dir, "tracks.json")
    script_path = os.path.join(playlist_dir, "script.txt")

    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        return
    
    with open(config_path, "r") as f:
        playlist_config = json.load(f)
    
    tracks = []
    if os.path.exists(tracks_path):
        with open(tracks_path, "r") as f:
            tracks = json.load(f)

    channel_id = global_config.get("channel_id")
    if not channel_id or channel_id == "UC_YOUR_CHANNEL_ID_HERE":
        print("Error: channel_id not set in config.json. Please add your YouTube Channel ID.")
        return

    youtube = get_authenticated_service()
    if not youtube:
        print("Authentication failed.")
        return

    playlist_title = playlist_config.get("topic", "Curated Playlist")
    
    playlist_id = args.playlist_id
    if not playlist_id:
        # Use temp_name for search
        search_title = args.temp_name
        playlist_id = get_playlist_id_by_name(youtube, channel_id, search_title)
        if not playlist_id:
            print(f"Error: Playlist '{search_title}' not found in channel {channel_id}.")
            return
    
    print(f"Found playlist ID: {playlist_id}")

    # Get all items in the playlist to find uploaded videos
    print("Fetching playlist items to find uploaded narration parts...")
    items = get_all_playlist_items(youtube, playlist_id)
    
    # Find narration parts by title
    # Expect titles like "part_001.mp4", "part_1.mp4", "part_001", etc.
    narration_parts = {}
    for item in items:
        title = item['snippet']['title']
        vid_id = item['contentDetails']['videoId']
        
        # Check pattern
        # Look for explicit part_N.mp4 or just part_N, allowing spaces or underscores
        match = re.search(r'part[ _](\d+)', title, re.IGNORECASE)
        
        if match:
            # Make sure it's not "Part 1: Topic" (which is the formatted title)
            # The formatted title usually has spaces or colon. 
            # If the user uploaded raw files, they likely don't have spaces if they matched "part_001.mp4"
            # But if we run this multiple times, the title might have changed!
            # The user said: "expect all the narration clips to be uploaded ... with their original path name ... as the title".
            # This implies a fresh upload or we need to be careful.
            # BUT, if we already renamed them, we can't find them by original name easily unless we store them.
            # The user implies this is for the "post upload" step, assuming fresh uploads or titles are preserved.
            # If titles are already changed, this might fail. I will assume titles are raw.
            part_num = int(match.group(1))
            narration_parts[part_num] = vid_id
            print(f"  Found narration part {part_num}: {title} ({vid_id})")

    if not narration_parts:
        print("Warning: No narration parts found in playlist matching 'part_N' pattern.")

    # Build script for image filenames (attribution)
    image_filenames = []
    if os.path.exists(script_path):
        with open(script_path, "r") as f:
            script_content = f.read()
            matches = re.findall(r'\[IMAGE_URL:\s*(.*?)\]', script_content)
            for m in matches:
                filename = m.split('/')[-1]
                filename = unquote(filename)
                image_filenames.append(filename)

    # Assemble the plan
    planned_items = []
    
    # Determine how many iterations (parts/tracks)
    max_part = max(narration_parts.keys()) if narration_parts else 0
    num_tracks = len(tracks)
    count = max(num_tracks, max_part)
    
    print(f"Constructing plan for {count} segments...")

    for i in range(count):
        idx = i # 0-based index
        part_num = idx + 1
        
        # 1. Add Narration Part
        if part_num in narration_parts:
            vid_id = narration_parts[part_num]
            
            # Generate Metadata
            desc_file = os.path.join(playlist_dir, f"part_{part_num:03d}.txt")
            description = ""
            if os.path.exists(desc_file):
                with open(desc_file, "r") as f:
                    description = f.read()
            
            attribution = ""
            if idx < len(image_filenames):
                img_file = image_filenames[idx]
                # Assuming get_wikimedia_attribution works relative to CWD or needs absolute?
                # The original script passed filename.
                # But get_wikimedia_attribution uses os.path.basename so it's fine.
                # It fetches from API.
                attribution = get_wikimedia_attribution(img_file)
            
            title = f"Part {part_num}: {playlist_config.get('topic', 'Jazz History')}"
            final_desc = description
            if attribution:
                final_desc += attribution

            planned_items.append({
                "kind": "narration",
                "video_id": vid_id,
                "title": title,
                "description": final_desc
            })
        else:
            print(f"  Warning: Missing narration part {part_num} in playlist uploads.")

        # 2. Add Song
        if idx < len(tracks):
            song = tracks[idx]
            planned_items.append({
                "kind": "song",
                "video_id": song['video_id'],
                "title": song.get('title', 'Unknown Song'),
                # We don't change song metadata usually
                "description": None 
            })

    output_data = {
        "playlist_id": playlist_id,
        "playlist_title": playlist_title,
        "playlist_description": "A journey through music and history. Generated by AI Curator.",
        "items": planned_items
    }
    
    out_path = os.path.join(playlist_dir, "youtube_playlists.json")
    with open(out_path, "w") as f:
        json.dump(output_data, f, indent=2)
        
    print(f"\n✅ Generated {out_path} with {len(planned_items)} items.")
    print("You can now run the update script to apply these changes.")

if __name__ == "__main__":
    main()

