import os
import json
import argparse
import re
from urllib.parse import unquote
from googleapiclient.discovery import build
# Reuse authentication and helper from existing script
try:
    from .update_youtube_playlist import get_authenticated_service, get_wikimedia_attribution
except ImportError:
    from yt_music.update_youtube_playlist import get_authenticated_service, get_wikimedia_attribution

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
    parser = argparse.ArgumentParser(description="Enrich curated_playlist.json with uploaded clips metadata.")
    parser.add_argument("playlist_dir", help="Path to the playlist directory (e.g. data/playlists/space_jazz)")
    parser.add_argument("--playlist-id", help="The ID of the manual playlist containing your uploads", required=True)
    args = parser.parse_args()

    playlist_dir = args.playlist_dir
    if not os.path.exists(playlist_dir):
        print(f"Error: Directory {playlist_dir} not found.")
        return

    # Load configs
    from core.config import GlobalConfig, PlaylistConfig
    from core.models.playlist import CuratedPlaylist

    try:
        global_config = GlobalConfig.load()
    except Exception as e:
        print(f"Error loading global config: {e}")
        return
    
    try:
        playlist_config = PlaylistConfig.load(playlist_dir)
    except Exception as e:
        print(f"Error loading playlist config: {e}")
        return
    
    try:
        curated_playlist = CuratedPlaylist.load(playlist_dir)
    except Exception as e:
        print(f"Error loading curated playlist: {e}")
        return

    items = curated_playlist.items
    if not items:
        print("Error: curated_playlist.json has no items.")
        return

    channel_id = global_config.channel_id
    if not channel_id or channel_id == "UC_YOUR_CHANNEL_ID_HERE":
        print("Error: channel_id not set in config.json. Please add your YouTube Channel ID.")
        return

    youtube = get_authenticated_service()
    if not youtube:
        print("Authentication failed.")
        return

    playlist_title = curated_playlist.title or playlist_config.topic
    playlist_title += " (Narrated)"
    
    playlist_id = args.playlist_id
    if not playlist_id:
        print("Error: Must provide --playlist-id")
        return
    
    print(f"Found playlist ID: {playlist_id}")

    # Get all items in the playlist to find uploaded videos
    print("Fetching playlist items to find uploaded narration parts...")
    yt_items = get_all_playlist_items(youtube, playlist_id)
    
    # Find narration parts by title matching "part_N" pattern
    # The assumption is the user uploaded the generated files part_001.mp4, etc.
    narration_uploads = {}
    for item in yt_items:
        title = item['snippet']['title']
        vid_id = item['contentDetails']['videoId']
        
        match = re.search(r'part[ _](\d+)', title, re.IGNORECASE)
        if match:
            part_num = int(match.group(1))
            narration_uploads[part_num] = vid_id
            print(f"  Found narration part {part_num}: {title} ({vid_id})")

    if not narration_uploads:
        print("Warning: No narration parts found in playlist matching 'part_N' pattern.")

    # Assemble the plan
    print(f"Enriching curated playlist with {len(items)} items...")

    narrative_counter = 0

    for idx, item in enumerate(items):
        if item.type == "narrative":
            narrative_counter += 1
            item.kind = "narration"
            
            # Find the uploaded video ID for this part
            vid_id = narration_uploads.get(narrative_counter)
            
            if not vid_id:
                print(f"  Warning: Missing upload for narrative part {narrative_counter}")
                continue
            
            item.video_id = vid_id
                
            # Prepare metadata
            part_title = f"{curated_playlist.topic} (Episode {narrative_counter})"
            item.title = part_title # Update title for YouTube
            
            # Links to prev/next songs
            # Look backwards for previous track
            prev_track = None
            for i in range(idx - 1, -1, -1):
                if items[i].type == "track":
                    prev_track = items[i]
                    break
            
            # Look forwards for next track
            next_track = None
            for i in range(idx + 1, len(items)):
                if items[i].type == "track":
                    next_track = items[i]
                    break
            
            intro_note = (
                f"This video is part of the narrated playlist '{playlist_title}'. "
                "It provides context and history for the music and is best experienced as part of the full journey."
            )
            playlist_link = f"🎧 Full Playlist: https://www.youtube.com/playlist?list={playlist_id}"
            
            links_block = [intro_note, "", playlist_link]
            
            if prev_track:
                p_title = prev_track.title or 'Previous Song'
                p_id = prev_track.video_id
                links_block.append(f"⏮️ Previous Song: {p_title} (https://youtu.be/{p_id})")
                
            if next_track:
                n_title = next_track.title or 'Next Song'
                n_id = next_track.video_id
                links_block.append(f"⏭️ Next Song: {n_title} (https://youtu.be/{n_id})")

            links_text = "\n".join(links_block)
            
            # Attribution
            footer = ""
            image_url = item.image_url
            if image_url:
                filename = image_url.split('/')[-1]
                filename = unquote(filename)
                attribution = get_wikimedia_attribution(filename)
                if attribution:
                    footer = "\n\n---\n" + attribution
            
            # Transcript
            description = item.text or ""
            
            # Combine
            MAX_LEN = 4800 
            fixed_len = len(links_text) + len(footer) + 10 
            remaining = MAX_LEN - fixed_len
            
            final_desc = links_text + "\n\n---\n\n"
            
            if len(description) > remaining:
                cropped_desc = description[:remaining-50] + "... [Transcript Truncated]"
                final_desc += cropped_desc
            else:
                final_desc += description
            
            final_desc += footer
            
            item.description = final_desc
            
        elif item.type == "track":
            item.kind = "song"
            # Tracks already have video_id and title
            # description is None or not set, which is fine

    curated_playlist.playlist_id = playlist_id
    curated_playlist.playlist_title = playlist_title
    curated_playlist.playlist_description = f"A curated music journey about {curated_playlist.topic}. Listen to the full experience with narration."
    
    # Write back to curated_playlist.json
    try:
        curated_playlist.save(playlist_dir)
        print(f"\n✅ Enriched curated_playlist.json with YouTube metadata.")
        print("You can now run the update script to apply these changes.")
    except Exception as e:
        print(f"Error saving enriched playlist: {e}")

if __name__ == "__main__":
    main()
