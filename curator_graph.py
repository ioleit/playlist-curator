from langgraph.graph import StateGraph, END
from core.agent_state import AgentState
from text_to_speech.nodes import generate_speech_node
from curation.nodes import curate_playlist_node, verify_curation_node
from curation.video_nodes import generate_images_node, create_video_node

# Build the graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("curate_playlist", curate_playlist_node)
builder.add_node("verify_curation", verify_curation_node)
builder.add_node("generate_speech", generate_speech_node)
builder.add_node("generate_images", generate_images_node)
builder.add_node("create_video", create_video_node)

# Set entry point
builder.set_entry_point("curate_playlist")

# Linear flow: Curate -> Verify -> Speech -> Images -> Video
builder.add_edge("curate_playlist", "verify_curation")
builder.add_edge("verify_curation", "generate_speech")
builder.add_edge("generate_speech", "generate_images") 
builder.add_edge("generate_images", "create_video")
builder.add_edge("create_video", END)

# Compile the graph
app = builder.compile()
