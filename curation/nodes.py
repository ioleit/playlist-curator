import json
import os
import re
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from ytmusicapi import YTMusic
from core.agent_state import AgentState
from .tools import search_youtube_music
from .image_tools import search_wikipedia_images

def curate_playlist_node(state: AgentState):
    # Load global config
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}
    
    model_name = config.get("model", "google/gemini-2.0-flash-exp:free")
    api_key = config.get("openrouter_api_key", os.environ.get("OPENROUTER_API_KEY"))
    
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("Warning: OpenRouter API key not found in config.json or environment.")
    
    topic = state.get("topic", "Jazz history")
    duration = state.get("duration", "30m")
    duration_text = duration
    playlist_dir = state.get("playlist_dir", "data")
    
    # Ensure playlist directory exists (should be done by main, but safe to ensure)
    os.makedirs(playlist_dir, exist_ok=True)
    
    prompt_file = os.path.join(playlist_dir, "prompt.txt")
    response_file = os.path.join(playlist_dir, "response.txt")
    
    # Load system prompt from file
    system_prompt_name = state.get("system_prompt", "default")
    if not system_prompt_name.endswith(".md"):
        system_prompt_name += ".md"
        
    current_dir = os.path.dirname(os.path.abspath(__file__))
    instruction_path = os.path.join(current_dir, "instructions", system_prompt_name)
    
    try:
        with open(instruction_path, "r") as f:
            system_message_template = f.read()
    except FileNotFoundError:
        print(f"Warning: Instruction file {instruction_path} not found. Using default.")
        default_path = os.path.join(current_dir, "instructions", "default.md")
        with open(default_path, "r") as f:
            system_message_template = f.read()
            
    # Check if template supports duration parameter to avoid KeyErrors for old templates
    if "{duration}" in system_message_template:
        system_message = system_message_template.format(topic=topic, duration=duration_text)
    else:
        # Fallback if template doesn't have duration (should update templates)
        system_message = system_message_template.format(topic=topic)
    
    user_query = f"Create the curated playlist for {topic}"
    full_prompt_text = f"SYSTEM:\n{system_message}\n\nUSER:\n{user_query}"
    
    # Check for resumability
    if os.path.exists(prompt_file) and os.path.exists(response_file):
        try:
            with open(prompt_file, "r") as f:
                cached_prompt = f.read()
            
            if cached_prompt == full_prompt_text:
                print("⏩ Resuming from cached response...")
                with open(response_file, "r") as f:
                    cached_content = f.read()
                # IMPORTANT: We must also load verification cache if possible, 
                # but verify_curation_node handles that or we pass raw_script
                return {"text": cached_content, "raw_script": cached_content}
            else:
                print("🔄 Prompt changed, regenerating...")
        except Exception as e:
            print(f"Error reading cache: {e}, regenerating...")

    # Save the prompt
    with open(prompt_file, "w") as f:
        f.write(full_prompt_text)

    llm = ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1"
    )
    
    tools = [search_youtube_music, search_wikipedia_images]
    
    # Create the agent
    agent = create_react_agent(llm, tools, prompt=system_message)
    
    print(f"🤖 Consulting LLM Curator Agent for '{topic}'...")
    # Run the agent
    result = agent.invoke({"messages": [HumanMessage(content=user_query)]})
    
    # Extract the final response
    last_message = result["messages"][-1]
    content = last_message.content
    
    # Save the response
    with open(response_file, "w") as f:
        f.write(content)
        
    # Also save as script.txt for easier user access (as per previous main.py behavior)
    script_file = os.path.join(playlist_dir, "script.txt")
    with open(script_file, "w") as f:
        f.write(content)
    
    print(f"✨ Curation Complete! Script length: {len(content)} characters")
    
    return {"text": content, "raw_script": content}

def clean_narrative_segment(text: str) -> str:
    """
    Cleans up markdown artifacts, labels, and image prompts from the narrative text
    so they don't get read by the TTS.
    """
    # Remove [IMAGE_URL: ...]
    text = re.sub(r'\[IMAGE_URL:.*?\]', '', text, flags=re.DOTALL)

    # Remove bold headers like **(Narration)**, **(Intro)**, **(Outro)**
    text = re.sub(r'\*\*\([A-Za-z0-9\s]+\)\*\*', '', text)
    
    # Remove just **Bold** headers if they appear at start of lines
    text = re.sub(r'^\s*\*\*.*?\*\*\s*$', '', text, flags=re.MULTILINE)
    
    # Remove markdown bold syntax but keep text
    text = text.replace('**', '')
    
    # Remove markdown italic syntax
    text = text.replace('*', '')
    
    return text.strip()

def extract_image_url(text: str) -> str:
    """
    Extracts the image URL from a text segment.
    Returns None if none found.
    """
    match = re.search(r'\[IMAGE_URL:\s*(.*?)\]', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def verify_curation_node(state: AgentState):
    """
    Parses the raw script, verifies tracks, extracts image URLs,
    separates narrative text, and extracts the playlist title.
    """
    raw_script = state.get("raw_script") or state.get("text")
    playlist_dir = state.get("playlist_dir", "data")
    config_path = os.path.join(playlist_dir, "config.json")
    tracks_file = os.path.join(playlist_dir, "tracks.json")
    
    if not raw_script:
        print("⚠️ No script to verify.")
        return {"narrative_segments": [], "verified_tracks": [], "segment_visual_prompts": []}

    # Extract Title
    playlist_title = None
    title_match = re.search(r'\[TITLE:\s*(.*?)\]', raw_script)
    if title_match:
        playlist_title = title_match.group(1).strip()
        print(f"📝 Found Generated Title: {playlist_title}")
        
        # Update config.json with the new title
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                
                config["topic"] = playlist_title # Update the topic/title
                
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=4)
                print(f"    ✅ Updated config.json with new title.")
            except Exception as e:
                print(f"    ❌ Failed to update config.json: {e}")
    
    # Clean the title tag from the script so it doesn't get narrated
    raw_script = re.sub(r'\[TITLE:.*?\]', '', raw_script).strip()

    # Check if we already have verified tracks to save time/API calls
    # This is a simple optimization: if tracks.json exists and script hasn't changed (implied by caller), use it.
    # However, we need to re-parse narrative segments and image URLs because those aren't in tracks.json fully structured yet.
    # So we'll still parse, but maybe skip the network call if we match the ID?
    
    existing_tracks = {}
    if os.path.exists(tracks_file):
        try:
            with open(tracks_file, "r") as f:
                track_list = json.load(f)
                for t in track_list:
                    existing_tracks[t['video_id']] = t
            print(f"⏩ Loaded {len(existing_tracks)} previously verified tracks.")
        except:
            pass

    print("🕵️ Verifying curation and checking tracks...")
    
    # Regex to find [TRACK: Title by Artist | ID: video_id]
    track_pattern = re.compile(r'\[TRACK:\s*(.*?)\s*\|\s*ID:\s*([\w-]+)\s*\]')
    
    verified_tracks = []
    narrative_segments = []
    segment_visual_prompts = []
    last_pos = 0
    
    yt = YTMusic()
    
    for match in track_pattern.finditer(raw_script):
        # Add text before the match as a segment
        raw_segment = raw_script[last_pos:match.start()]
        
        clean_segment = clean_narrative_segment(raw_segment)
        image_url = extract_image_url(raw_segment)
        
        if clean_segment:
            narrative_segments.append(clean_segment)
            segment_visual_prompts.append(image_url) # Storing URL in prompts list for now
        else:
            pass
        
        title_artist = match.group(1)
        video_id = match.group(2)
        
        # Verify with YTMusic
        if video_id in existing_tracks:
             print(f"  ✅ Using cached track: {existing_tracks[video_id]['title']}")
             verified_tracks.append(existing_tracks[video_id])
        else:
            print(f"  Checking track: {title_artist} ({video_id})...")
            try:
                song_details = yt.get_song(video_id)
                video_details = song_details.get('videoDetails', {})
                valid_title = video_details.get('title', 'Unknown Title')
                valid_author = video_details.get('author', 'Unknown Artist')
                
                print(f"    ✅ Verified: {valid_title} by {valid_author}")
                
                verified_tracks.append({
                    "original_ref": title_artist,
                    "video_id": video_id,
                    "title": valid_title,
                    "artist": valid_author,
                    "duration": video_details.get('lengthSeconds', 0)
                })
                
            except Exception as e:
                print(f"    ❌ Validation failed for {video_id}: {e}")
                verified_tracks.append({
                    "original_ref": title_artist,
                    "video_id": video_id,
                    "error": str(e),
                    "verified": False
                })
            
        last_pos = match.end()
    
    # Add remaining text as final segment
    final_raw_segment = raw_script[last_pos:]
    final_clean_segment = clean_narrative_segment(final_raw_segment)
    final_image_url = extract_image_url(final_raw_segment)
    
    if final_clean_segment:
        narrative_segments.append(final_clean_segment)
        segment_visual_prompts.append(final_image_url)
    
    print(f"✨ Verification Complete! Found {len(verified_tracks)} tracks, {len(narrative_segments)} narrative segments, and {len(segment_visual_prompts)} image URLs.")

    # Save verified tracks
    with open(tracks_file, "w") as f:
        json.dump(verified_tracks, f, indent=2)
    print(f"Verified tracks saved to: {tracks_file}")
    
    return {
        "narrative_segments": narrative_segments,
        "verified_tracks": verified_tracks,
        "segment_visual_prompts": segment_visual_prompts,
        "playlist_title": playlist_title
    }
