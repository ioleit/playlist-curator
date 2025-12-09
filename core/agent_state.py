from typing import TypedDict, Optional, List


class AgentState(TypedDict, total=False):
    # Core identifiers / flags
    playlist_id: str
    skip_validation: bool

    # Curation payload between nodes
    raw_script: Optional[str]  # The original LLM output with [TRACK] tags
    curated_playlist: Optional[dict]
