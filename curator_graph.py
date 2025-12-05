from langgraph.graph import StateGraph, END
from core.agent_state import AgentState
from text_to_speech.nodes import generate_speech_node

def generate_text_node(state: AgentState):
    """
    Mock LLM node that generates text based on a topic.
    In a real application, this would call an LLM (e.g., OpenAI, Anthropic).
    """
    topic = state["topic"]
    # Simple mock generation
    generated_text = f"Here is a short explanation about {topic}. It is a very interesting subject that many people enjoy learning about. I hope this helps you understand it better."
    
    print(f"Generated text: {generated_text}")
    return {"text": generated_text}

# Build the graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("generate_text", generate_text_node)
builder.add_node("generate_speech", generate_speech_node)

# Set entry point
builder.set_entry_point("generate_text")

# Add edges
builder.add_edge("generate_text", "generate_speech")
builder.add_edge("generate_speech", END)

# Compile the graph
app = builder.compile()
