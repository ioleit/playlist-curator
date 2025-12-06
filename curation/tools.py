from ytmusicapi import YTMusic
from langchain_core.tools import tool

@tool
def search_youtube_music(query: str, limit: int = 3) -> str:
    """
    Search for songs on YouTube Music.
    Returns a list of found songs with their titles, artists, and video IDs.
    """
    # ytmusicapi usually works without auth for search, but sometimes requires headers. 
    # We'll try without headers first.
    print(f"  🔍 Tool Call: Searching YouTube Music for '{query}'...")
    yt = YTMusic()
    results = yt.search(query, filter="songs", limit=limit)
    
    formatted_results = []
    for result in results:
        title = result.get("title")
        artists = ", ".join([a["name"] for a in result.get("artists", [])])
        video_id = result.get("videoId")
        formatted_results.append(f"Title: {title}, Artist: {artists}, ID: {video_id}")
        
    return "\n".join(formatted_results)

