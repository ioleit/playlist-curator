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
    Updates the title, description, and status (unlisted, not for kids, music category) of a video.
    """
    # print(f"  📝 Updating metadata for {video_id}...")
    
    final_description = description
    if attribution:
        final_description += attribution
        
    try:
        youtube.videos().update(
            part="snippet,status",
            body={
                "id": video_id,
                "snippet": {
                    "title": title,
                    "description": final_description,
                    "categoryId": "10" # Music
                },
                "status": {
                    "privacyStatus": "unlisted",
                    "selfDeclaredMadeForKids": False
                }
            }
        ).execute()
        # print("    ✅ Metadata updated.")
    except Exception as e:
        print(f"    ❌ Failed to update metadata for {video_id}: {e}")

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

def main():
    parser = argparse.ArgumentParser(description="Update playlist from youtube_playlists.json")
    parser.add_argument("playlist_dir", help="Path to the playlist directory (e.g. data/playlists/space_jazz)")
    args = parser.parse_args()
    
    # Load global config for podcast playlist
    global_config = {}
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            global_config = json.load(f)
            
    podcast_playlist_id = global_config.get("podcast_playlist_id")
    
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
            # print(f"  Deleted item {item['id']}")
        except Exception as e:
            print(f"  ❌ Failed to delete item {item['id']}: {e}")

    # Pre-fetch podcast playlist items if configured
    podcast_video_ids = set()
    if podcast_playlist_id:
        print(f"Fetching podcast playlist ({podcast_playlist_id}) items...")
        try:
            p_items = get_playlist_items(youtube, podcast_playlist_id)
            for item in p_items:
                podcast_video_ids.add(item['contentDetails']['videoId'])
        except Exception as e:
             print(f"⚠️ Error fetching podcast playlist: {e}")

    # 3. Rebuild from JSON
    print("Rebuilding playlist...")
    items = playlist_data.get("items", [])
    
    print(f"  Adding {len(items)} items to playlist...")
    for i, item in enumerate(items):
        vid_id = item['video_id']
        kind = item.get("kind", "video")
        
        # Add to main playlist (Sequential)
        try:
            body = {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": vid_id
                    }
                }
            }
            # Position is implicitly "end of playlist", which preserves order during sequential insert
            youtube.playlistItems().insert(
                part="snippet",
                body=body
            ).execute()
            print(f"    ✅ Added {kind}: {item.get('title', vid_id)}")
        except Exception as e:
            print(f"    ❌ Failed to add item {vid_id}: {e}")
            
        # 4. Update Video Metadata if needed
        description = item.get("description")
        if description:
            update_video_metadata(youtube, vid_id, item['title'], description)

        # 5. Add to Global Podcast Playlist (Narrations ONLY)
        if podcast_playlist_id and kind == "narration":
            if vid_id not in podcast_video_ids:
                print(f"    🎙️ Adding narration {vid_id} to global podcast playlist...")
                try:
                    podcast_body = {
                        "snippet": {
                            "playlistId": podcast_playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": vid_id
                            }
                        }
                    }
                    youtube.playlistItems().insert(
                        part="snippet",
                        body=podcast_body
                    ).execute()
                    podcast_video_ids.add(vid_id)
                    print("      ✅ Added to podcast playlist.")
                except Exception as e:
                    print(f"      ❌ Failed to add to podcast playlist: {e}")

    print("\n🎉 Playlist update complete!")

if __name__ == "__main__":
    main()

