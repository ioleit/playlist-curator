from typing import TypedDict, Optional

class AgentState(TypedDict):
    topic: str
    text: Optional[str]
    audio_path: Optional[str]

