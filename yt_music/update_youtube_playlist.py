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
    parser = argparse.ArgumentParser(description="Update playlist from youtube_playlists.json")
    parser.add_argument("playlist_dir", help="Path to the playlist directory (e.g. data/playlists/space_jazz)")
    # Removed playlist_id argument as it comes from json now
    args = parser.parse_args()
    
    playlist_dir = args.playlist_dir
    json_path = os.path.join(playlist_dir, "youtube_playlists.json")
    
    if not os.path.exists(json_path):
        print(f"❌ Error: {json_path} not found. Run post_upload.py first.")
        return
        
    with open(json_path, "r") as f:
        playlist_data = json.load(f)
        
    playlist_id = playlist_data.get("playlist_id")
    if not playlist_id:
        print("❌ Error: No playlist_id in JSON.")
        return

    youtube = get_authenticated_service()
    if not youtube:
        return
        
    # 1. Update Playlist Metadata
    title = playlist_data.get("playlist_title", "Curated Playlist")
    desc = playlist_data.get("playlist_description", "")
    update_playlist_metadata(youtube, playlist_id, title, desc)
    
    # 2. Clear Playlist
    print("Fetching current playlist items to clear...")
    current_items = get_playlist_items(youtube, playlist_id)
    print(f"Found {len(current_items)} items to clear.")
    
    for item in current_items:
        try:
            youtube.playlistItems().delete(id=item['id']).execute()
            print(f"  Deleted item {item['id']}")
        except Exception as e:
            print(f"  Failed to delete item {item['id']}: {e}")

    # 3. Rebuild from JSON
    print("Rebuilding playlist...")
    items = playlist_data.get("items", [])
    
    for i, item in enumerate(items):
        vid_id = item['video_id']
        kind = item.get("kind", "video")
        print(f"  Adding {kind} ({i+1}/{len(items)}): {item.get('title', vid_id)}")
        
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": vid_id
                }
            }
        }
        
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body=body
            ).execute()
        except Exception as e:
            print(f"  ❌ Failed to add item: {e}")
            continue
            
        # 4. Update Video Metadata if needed (Narration)
        description = item.get("description")
        if description:
            # It's a narration part (or something we want to update)
            # Note: The title in JSON includes "Part N: Topic", which is what we want.
            update_video_metadata(youtube, vid_id, item['title'], description)

    print("\n🎉 Playlist update complete!")

if __name__ == "__main__":
    main()
