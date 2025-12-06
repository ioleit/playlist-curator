import os
import json
import argparse
import pickle
import requests
import re
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Scopes required for managing playlists and videos
SCOPES = [
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

def get_authenticated_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('client_secrets.json'):
                print("❌ Error: client_secrets.json not found.")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)

def get_wikimedia_attribution(filename):
    """
    Fetch author, license, and source url from Wikimedia Commons for a given filename.
    """
    # Clean filename (remove file:// prefix if present)
    if filename.startswith('file://'):
        filename = filename.replace('file://', '')
    
    # Extract just the name if it's a path
    filename = os.path.basename(filename)
    
    print(f"    🔍 Searching Wikimedia for: {filename}...")
    
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "extmetadata",
        "format": "json"
    }
    headers = {
        'User-Agent': 'PlaylistCurator/1.0 (https://github.com/yourusername/playlist-curator; contact@example.com)'
    }
    
    try:
        resp = requests.get(url, params=params, headers=headers).json()
        
        # Handle case where response might be empty or invalid structure
        if 'query' not in resp:
            print("      ⚠️ Unexpected API response format.")
            return None
            
        pages = resp['query']['pages']
        page_id = next(iter(pages))
        
        if page_id == "-1":
             print("      ⚠️ Image not found on Wikimedia Commons.")
             return None
             
        metadata = pages[page_id]['imageinfo'][0]['extmetadata']
        
        # Clean HTML tags from values
        def clean_html(raw_html):
            cleanr = re.compile('<.*?>')
            return re.sub(cleanr, '', raw_html)

        artist = clean_html(metadata.get('Artist', {}).get('value', 'Unknown'))
        license_name = metadata.get('LicenseShortName', {}).get('value', 'Unknown License')
        license_url = metadata.get('LicenseUrl', {}).get('value', '')
        source_url = f"https://commons.wikimedia.org/wiki/File:{filename.replace(' ', '_')}"
        
        return f"\n\nImage Credit:\nTitle: {filename}\nAuthor: {artist}\nSource: {source_url}\nLicense: {license_name} {license_url}"
        
    except Exception as e:
        print(f"      ⚠️ Error fetching attribution: {e}")
        return None

def update_playlist_metadata(youtube, playlist_id, title, description):
    """
    Updates the playlist title, description, and ensures manual ordering.
    """
    print(f"  📝 Updating playlist metadata for {playlist_id}...")
    try:
        # First, just update snippet
        youtube.playlists().update(
            part="snippet",
            body={
                "id": playlist_id,
                "snippet": {
                    "title": title,
                    "description": description
                }
            }
        ).execute()
        print("    ✅ Playlist metadata updated.")
        
    except Exception as e:
        print(f"    ❌ Failed to update playlist metadata: {e}")

def update_video_metadata(youtube, video_id, title, description, attribution=""):
    """
    Updates the title and description of a video.
    """
    print(f"  📝 Updating metadata for {video_id}...")
    
    final_description = description
    if attribution:
        final_description += attribution
        
    try:
        youtube.videos().update(
            part="snippet",
            body={
                "id": video_id,
                "snippet": {
                    "title": title,
                    "description": final_description,
                    "categoryId": "10" # Music
                }
            }
        ).execute()
        print("    ✅ Metadata updated.")
    except Exception as e:
        print(f"    ❌ Failed to update metadata: {e}")

def get_playlist_items(youtube, playlist_id):
    """
    Returns a list of video items from the playlist.
    """
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

def insert_song_after(youtube, playlist_id, video_id_to_insert, position):
    """
    Inserts a video at a specific position in the playlist.
    """
    print(f"  ➕ Inserting song {video_id_to_insert} at pos {position}...")
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "position": position,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id_to_insert
                    }
                }
            }
        ).execute()
        print("    ✅ Song inserted.")
    except Exception as e:
        if "manualSortRequired" in str(e):
            print("    ❌ Failed to insert song: Playlist must be set to 'Manual' sorting in YouTube.")
            print("       ACTION: Go to YouTube -> Playlist -> Sort -> Manual (or drag a video).")
        else:
            print(f"    ❌ Failed to insert song: {e}")

def main():
    parser = argparse.ArgumentParser(description="Update an existing playlist: set titles, descriptions (with attribution), and interleave songs.")
    parser.add_argument("playlist_id", help="The ID of the YouTube Playlist you created manually")
    parser.add_argument("playlist_dir", help="Path to the playlist directory (e.g. data/playlists/space_jazz)")
    args = parser.parse_args()

    playlist_id = args.playlist_id
    playlist_dir = args.playlist_dir
    
    config_path = os.path.join(playlist_dir, "config.json")
    tracks_path = os.path.join(playlist_dir, "tracks.json")
    script_path = os.path.join(playlist_dir, "script.txt")
    
    if not os.path.exists(config_path) or not os.path.exists(tracks_path):
        print("❌ Error: Config or tracks file not found.")
        return

    with open(config_path, "r") as f:
        config = json.load(f)
    with open(tracks_path, "r") as f:
        tracks = json.load(f)
        
    # Parse script for image filenames
    image_filenames = []
    with open(script_path, "r") as f:
        script_content = f.read()
        # Find all [IMAGE_URL: ...] tags
        matches = re.findall(r'\[IMAGE_URL:\s*(.*?)\]', script_content)
        for m in matches:
            # Extract filename from URL
            filename = m.split('/')[-1]
            # Decode URL encoding if needed
            from urllib.parse import unquote
            filename = unquote(filename)
            image_filenames.append(filename)

    youtube = get_authenticated_service()
    if not youtube:
        return

    # 1. Update Playlist Metadata & Ensure accessible
    playlist_title = config.get("topic", "Curated Playlist")
    playlist_desc = "A journey through music and history. Generated by AI Curator."
    update_playlist_metadata(youtube, playlist_id, playlist_title, playlist_desc)

    # 2. Get current playlist items and CLEAR non-uploads
    print("Fetching current playlist items...")
    current_items = get_playlist_items(youtube, playlist_id)
    
    print("Identifying narration parts...")
    narration_part_ids = []
    items_to_remove = []
    
    for item in current_items:
        vid_id = item['contentDetails']['videoId']
        playlist_item_id = item['id']
        
        # Check if it is a song from our tracks
        is_song = False
        for t in tracks:
            if t['video_id'] == vid_id:
                is_song = True
                break
        
        if is_song:
            items_to_remove.append(playlist_item_id)
        else:
            # Assume it's a narration part
            narration_part_ids.append(vid_id)
            items_to_remove.append(playlist_item_id)
            
    print(f"Found {len(narration_part_ids)} narration parts and {len(items_to_remove)} items to clear.")
    
    # Purge Playlist
    print("Purging playlist...")
    for item_id in items_to_remove:
        try:
            youtube.playlistItems().delete(id=item_id).execute()
            print(f"  Deleted item {item_id}")
        except Exception as e:
            print(f"  Failed to delete {item_id}: {e}")
            
    # Rebuild
    print("Rebuilding playlist in correct order...")
    
    # Current insertion count for position
    current_pos = 0
    
    for i in range(len(narration_part_ids)):
        # Add Part
        part_vid_id = narration_part_ids[i]
        print(f"  Adding Part {i+1} ({part_vid_id})...")
        
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": part_vid_id
                }
            }
        }

        try:
             youtube.playlistItems().insert(
                part="snippet",
                body=body
            ).execute()
        except Exception as e:
             print(f"  ❌ Failed to add part: {e}")
             
        # Update Metadata for this Part
        part_num = i + 1
        desc_file = os.path.join(playlist_dir, f"part_{part_num:03d}.txt")
        description = ""
        if os.path.exists(desc_file):
            with open(desc_file, "r") as f:
                description = f.read()
        
        attribution = ""
        if i < len(image_filenames):
            img_file = image_filenames[i]
            attribution = get_wikimedia_attribution(img_file)
            
        title = f"Part {part_num}: {config.get('topic', 'Jazz History')}"
        update_video_metadata(youtube, part_vid_id, title, description, attribution if attribution else "")

        # Add Song (if exists for this index)
        if i < len(tracks):
            song = tracks[i]
            print(f"  Adding Song: {song['title']}...")
            
            body = {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": song['video_id']
                    }
                }
            }

            try:
                youtube.playlistItems().insert(
                    part="snippet",
                    body=body
                ).execute()
            except Exception as e:
                print(f"  ❌ Failed to add song: {e}")

    # Verify final order
    print("\n🔍 Verifying final playlist order...")
    final_items = get_playlist_items(youtube, playlist_id)
    for idx, item in enumerate(final_items):
        print(f"  {idx}: {item['snippet']['title']}")

    print("\n🎉 Playlist rebuild complete!")

if __name__ == "__main__":
    main()
