from ytmusicapi import YTMusic
from langchain_core.tools import tool
import musicbrainzngs
import json
from duckduckgo_search import DDGS

# Initialize MusicBrainz
musicbrainzngs.set_useragent("PlaylistCurator", "0.1", "http://example.com")

@tool
def search_youtube_music(query: str, limit: int = 3) -> str:
    """
    Search for songs on YouTube Music.
    Returns a list of found songs with their titles, artists, and video IDs.
    """
    # ytmusicapi usually works without auth for search, but sometimes requires headers. 
    # We'll try without headers first.
    print(f"  🔍 Tool Call: Searching YouTube Music for '{query}'...")
    try:
        yt = YTMusic()
        results = yt.search(query, filter="songs", limit=limit)
        
        formatted_results = []
        for result in results:
            title = result.get("title")
            artists = ", ".join([a["name"] for a in result.get("artists", [])])
            video_id = result.get("videoId")
            formatted_results.append(f"Title: {title}, Artist: {artists}, ID: {video_id}")
            
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Error searching YouTube Music: {e}"

@tool
def search_musicbrainz(query: str, type: str = "artist") -> str:
    """
    Search MusicBrainz for artist, recording, or release information.
    'type' can be 'artist', 'release', or 'recording'.
    
    Use 'artist' to find: Country, Tags, Disambiguation.
    Use 'release' to find: Release Date, Label, Tracklist.
    Use 'recording' to find: Artist credits, Releases it appears on.
    """
    print(f"  🧠 Tool Call: Searching MusicBrainz for '{query}' (type: {type})...")
    try:
        if type == "artist":
            # Search for artist
            result = musicbrainzngs.search_artists(artist=query, limit=3)
            artists = result.get('artist-list', [])
            
            output = []
            for artist in artists:
                name = artist.get('name')
                country = artist.get('country', 'Unknown')
                disambiguation = artist.get('disambiguation', '')
                tags = [t['name'] for t in artist.get('tag-list', [])[:5]]
                
                output.append(f"Artist: {name} ({country}) - {disambiguation}. Tags: {', '.join(tags)}")
            return "\n".join(output)
            
        elif type == "recording":
             result = musicbrainzngs.search_recordings(recording=query, limit=3)
             recordings = result.get('recording-list', [])
             output = []
             for rec in recordings:
                 title = rec.get('title')
                 artist_credit = rec.get('artist-credit', [{}])
                 artist_name = artist_credit[0].get('artist', {}).get('name', 'Unknown') if artist_credit else "Unknown"
                 
                 releases = []
                 for r in rec.get('release-list', [])[:3]:
                     r_title = r.get('title')
                     r_date = r.get('date', 'Unknown Date')
                     releases.append(f"{r_title} ({r_date})")
                     
                 output.append(f"Recording: {title} by {artist_name}. Releases: {', '.join(releases)}")
             return "\n".join(output)
             
        elif type == "release":
            result = musicbrainzngs.search_releases(release=query, limit=3)
            releases = result.get('release-list', [])
            output = []
            for r in releases:
                title = r.get('title')
                artist = r.get('artist-credit', [{}])[0].get('artist', {}).get('name', 'Unknown')
                date = r.get('date', 'Unknown Date')
                label = r.get('label-info-list', [{}])[0].get('label', {}).get('name', 'Unknown Label') if r.get('label-info-list') else "Unknown Label"
                output.append(f"Release: {title} by {artist}. Date: {date}. Label: {label}")
            return "\n".join(output)

        return "Invalid search type. Use 'artist', 'release', or 'recording'."
        
    except Exception as e:
        return f"Error searching MusicBrainz: {e}"

@tool
def search_google(query: str) -> str:
    """
    Perform a web search using DuckDuckGo to find background info, history, or connections.
    Use this to find specific facts, trivia, or producer credits not in MusicBrainz.
    """
    print(f"  🌐 Tool Call: Searching Web for '{query}'...")
    try:
        results = DDGS().text(query, max_results=3)
        output = []
        for r in results:
            title = r.get('title')
            body = r.get('body')
            output.append(f"Source: {title}\nSummary: {body}\n")
        return "\n".join(output)
    except Exception as e:
        return f"Error searching web: {e}"
