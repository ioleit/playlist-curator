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

def list_channel_playlists(channel_id):
    youtube = get_authenticated_service()
    print(f"Listing playlists for channel: {channel_id}")
    request = youtube.playlists().list(
        part="snippet",
        channelId=channel_id,
        maxResults=50
    )
    while request:
        response = request.execute()
        for item in response.get('items', []):
            print(f"- Title: {item['snippet']['title']}")
            print(f"  ID: {item['id']}")
        request = youtube.playlists().list_next(request, response)

if __name__ == "__main__":
    # Channel ID from config.json
    list_channel_playlists("UCx4R55pScJEBpZTgELMIxkg")
