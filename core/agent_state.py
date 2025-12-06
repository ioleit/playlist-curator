from typing import TypedDict, Optional, List, Any

class AgentState(TypedDict):
    topic: str
    num_songs: int
    playlist_dir: str
    system_prompt: Optional[str]
    text: Optional[str]              # Deprecated
    raw_script: Optional[str]        # The original LLM output with [TRACK] tags
    narrative_segments: List[str]    # List of clean text segments
    segment_visual_prompts: List[str] # List of image prompts/search queries for each segment
    verified_tracks: List[dict]      # List of verified track objects
    audio_paths: List[str]           # List of paths to generated audio files
    video_paths: List[str]           # List of paths to generated video files
