import os
import json
from typing import Optional, Union, List, Literal
from pydantic import BaseModel, Field
from core.config import get_playlist_dir

class CuratedPlaylistItem(BaseModel):
    type: Literal["narrative", "track", "invalid"]
    # Common fields
    video_id: Optional[str] = None
    title: Optional[str] = None
    kind: Optional[str] = None # 'narration' or 'song' (optional enrichment)
    
    # Track specific
    artist: Optional[str] = None
    duration: Optional[Union[str, int]] = None
    original_ref: Optional[str] = None
    error: Optional[str] = None
    verified: Optional[bool] = None

    # Narrative specific
    text: Optional[str] = None
    image_url: Optional[str] = None
    audio_filename: Optional[str] = None
    video_filename: Optional[str] = None
    description: Optional[str] = None

    @classmethod
    def make_narrative(cls, text: str, image_url: Optional[str], filename_base: str) -> "CuratedPlaylistItem":
        return cls(
            type="narrative",
            text=text,
            image_url=image_url,
            audio_filename=f"{filename_base}.wav",
            video_filename=f"{filename_base}.mp4"
        )

    @classmethod
    def make_track(cls, video_id: str, title: str, artist: str, duration: Union[str, int], original_ref: str) -> "CuratedPlaylistItem":
        return cls(
            type="track",
            video_id=video_id,
            title=title,
            artist=artist,
            duration=duration,
            original_ref=original_ref,
            verified=True
        )

    @classmethod
    def make_invalid(cls, original_ref: str, video_id: Optional[str] = None, error: str = "Unknown error") -> "CuratedPlaylistItem":
        return cls(
            type="invalid",
            video_id=video_id,
            original_ref=original_ref,
            error=error,
            verified=False,
            # Provide fallbacks for mandatory-ish fields if needed by consumers, 
            # though consumers should check type="invalid"
            title=original_ref,
            artist="Unknown Artist"
        )
    
    @classmethod
    def make_track_fallback(cls, original_ref: str, video_id: str) -> "CuratedPlaylistItem":
        """Used when skipping validation: assumes valid but minimal info."""
        return cls(
            type="track",
            video_id=video_id,
            title=original_ref, 
            artist="Unknown Artist",
            duration=0,
            original_ref=original_ref
        )

class CuratedPlaylist(BaseModel):
    title: str
    topic: str
    items: List[CuratedPlaylistItem]
    playlist_id: Optional[str] = None
    playlist_title: Optional[str] = None
    playlist_description: Optional[str] = None

    @classmethod
    def load(cls, playlist_dir: str) -> "CuratedPlaylist":
        """Loads and validates the curated playlist JSON. Raises exceptions on failure."""
        json_path = os.path.join(playlist_dir, "curated_playlist.json")
        if not os.path.exists(json_path):
             raise FileNotFoundError(f"Curated playlist file '{json_path}' not found.")
        
        with open(json_path, "r") as f:
            data = json.load(f)
        return cls(**data)

    def save(self, playlist_dir: str):
        """Saves the curated playlist to JSON."""
        json_path = os.path.join(playlist_dir, "curated_playlist.json")
        with open(json_path, "w") as f:
            f.write(self.model_dump_json(indent=4))

    @classmethod
    def load_for_id(cls, playlist_id: str) -> "CuratedPlaylist":
        """Convenience loader using playlist id and the default data directory."""
        playlist_dir = get_playlist_dir(playlist_id)
        return cls.load(playlist_dir)

    def save_for_id(self, playlist_id: str):
        """Convenience saver using playlist id and the default data directory."""
        playlist_dir = get_playlist_dir(playlist_id)
        self.save(playlist_dir)

