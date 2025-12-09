import json
import os
import sys
from typing import Optional, Union, List, Any
from pydantic import BaseModel, Field, field_validator, ValidationError
import pytimeparse

# Base data directory and playlist subdirectory helpers
DATA_DIR = "data"
PLAYLISTS_DIR = os.path.join(DATA_DIR, "playlists")


def get_playlist_dir(playlist_id: str) -> str:
    """Absolute path to a playlist directory given its id."""
    return os.path.join(PLAYLISTS_DIR, playlist_id)


def playlist_path(playlist_id: str, *relative_parts: str) -> str:
    """Build a path inside a playlist directory from relative filenames."""
    return os.path.join(get_playlist_dir(playlist_id), *relative_parts)

class GlobalConfig(BaseModel):
    model: str = Field(default="google/gemini-2.0-flash-exp:free")
    channel_id: Optional[str] = None
    podcast_playlist_id: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    @field_validator("openrouter_api_key")
    @classmethod
    def check_api_key(cls, v):
        if v == "YOUR_API_KEY_HERE":
            return None
        return v

    @classmethod
    def load(cls, config_path: str = "config.json") -> "GlobalConfig":
        """Loads and validates the global configuration. Raises exceptions on failure."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file '{config_path}' not found.")
        
        with open(config_path, "r") as f:
            data = json.load(f)
        return cls(**data)

class PlaylistConfig(BaseModel):
    topic: Union[str, List[str]]
    duration: str
    system_prompt: str

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, v):
        if isinstance(v, list):
            return " ".join(v)
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v):
        seconds = pytimeparse.parse(v)
        if seconds is None:
            raise ValueError(f"Invalid duration format '{v}'")
        if seconds > 3 * 60 * 60:  # 3 hours
            raise ValueError(f"Duration '{v}' exceeds maximum of 3 hours.")
        return v

    def get_duration_seconds(self) -> int:
        return pytimeparse.parse(self.duration)

    @classmethod
    def load(cls, playlist_dir: str) -> "PlaylistConfig":
        """Loads and validates the playlist configuration. Raises exceptions on failure."""
        config_path = os.path.join(playlist_dir, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file '{config_path}' not found.")

        with open(config_path, "r") as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def load_for_id(cls, playlist_id: str) -> "PlaylistConfig":
        """Convenience loader using playlist id and the default data directory."""
        playlist_dir = get_playlist_dir(playlist_id)
        return cls.load(playlist_dir)
