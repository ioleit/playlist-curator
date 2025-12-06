import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def get_authenticated_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    return build('youtube', 'v3', credentials=creds)

def list_playlist_items(playlist_id):
    youtube = get_authenticated_service()
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50
    )
    response = request.execute()
    print(f"Items in playlist {playlist_id}:")
    for item in response.get('items', []):
        print(f"- Title: {item['snippet']['title']}")
        print(f"  ID: {item['snippet']['resourceId']['videoId']}")

if __name__ == "__main__":
    list_playlist_items("PLga258EXDBTzTGWoR6LQ-OX72rTQdDUIC")

