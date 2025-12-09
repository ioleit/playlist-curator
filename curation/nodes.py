import json
import os
import re
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langchain_core.callbacks import StdOutCallbackHandler
from ytmusicapi import YTMusic
from core.agent_state import AgentState
from .tools import search_youtube_music, search_musicbrainz, search_google
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
    skip_validation = state.get("skip_validation", False)
    if os.path.exists(prompt_file) and os.path.exists(response_file):
        try:
            with open(prompt_file, "r") as f:
                cached_prompt = f.read()
            
            # If skipping validation, we don't care about prompt equality
            if skip_validation or cached_prompt == full_prompt_text:
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
        openai_api_base="https://openrouter.ai/api/v1",
        streaming=True,
        verbose=True
    )
    
    tools = [search_youtube_music, search_wikipedia_images, search_musicbrainz, search_google]
    
    # Create the agent
    agent = create_react_agent(llm, tools, prompt=system_message)
    
    print(f"🤖 Consulting LLM Curator Agent for '{topic}'...")
    # Run the agent
    result = agent.invoke(
        {"messages": [HumanMessage(content=user_query)]},
        config={"callbacks": [StdOutCallbackHandler()]}
    )
    
    # Extract the final response
    last_message = result["messages"][-1]
    content = last_message.content
    
    # Save the response
    with open(response_file, "w") as f:
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
    skip_validation = state.get("skip_validation", False)
    
    if not raw_script:
        print("⚠️ No script to verify.")
        return {"narrative_segments": [], "verified_tracks": [], "segment_visual_prompts": []}

    # Extract Title
    playlist_title = None
    title_match = re.search(r'\[TITLE:\s*(.*?)\]', raw_script)
    if title_match:
        playlist_title = title_match.group(1).strip()
        print(f"📝 Found Generated Title: {playlist_title}")
    
    # Clean the title tag from the script so it doesn't get narrated
    raw_script = re.sub(r'\[TITLE:.*?\]', '', raw_script).strip()

    print("🕵️ Verifying curation and checking tracks...")
    
    # Regex to find [TRACK: Title by Artist | ID: video_id]
    track_pattern = re.compile(r'\[TRACK:\s*(.*?)\s*\|\s*ID:\s*([\w-]+)\s*\]')
    
    playlist_items = []
    
    # Initialize Markdown content (keeping for human readability)
    md_lines = []
    md_lines.append(f"# {playlist_title or state.get('topic', 'Curated Playlist')}")
    md_lines.append(f"\n**Topic:** {state.get('topic', 'Unknown')}")
    if state.get("duration"):
        md_lines.append(f"**Target Duration:** {state.get('duration')}")
    md_lines.append("\n---\n")
    
    yt = None
    if not skip_validation:
        yt = YTMusic()
    else:
        print("⏩ Skipping track validation (assuming tracks are valid)...")
    
    last_pos = 0
    narrative_count = 0
    
    for match in track_pattern.finditer(raw_script):
        # Add text before the match as a segment
        raw_segment = raw_script[last_pos:match.start()]
        
        clean_segment = clean_narrative_segment(raw_segment)
        image_url = extract_image_url(raw_segment)
        
        if clean_segment:
            narrative_count += 1
            filename_base = f"part_{narrative_count:03d}"
            
            # Add to JSON structure
            playlist_items.append({
                "type": "narrative",
                "text": clean_segment,
                "image_url": image_url,
                "audio_filename": f"{filename_base}.wav",
                "video_filename": f"{filename_base}.mp4"
            })
            
            # Add to Markdown
            md_lines.append(f"## Part {narrative_count}")
            if image_url:
                md_lines.append(f"![Visual]({image_url})")
            md_lines.append(f"\n{clean_segment}\n")
        
        title_artist = match.group(1)
        video_id = match.group(2)
        
        if skip_validation:
             # Assume valid
            print(f"  Skipping validation for: {title_artist} ({video_id})")
            playlist_items.append({
                "type": "track",
                "video_id": video_id,
                "title": title_artist, # Use original ref as title since we can't fetch real one
                "artist": "Unknown Artist", # We don't have artist without API
                "duration": 0,
                "original_ref": title_artist
            })
        else:
            # Verify with YTMusic
            print(f"  Checking track: {title_artist} ({video_id})...")
            try:
                song_details = yt.get_song(video_id)
                video_details = song_details.get('videoDetails', {})
                valid_title = video_details.get('title', 'Unknown Title')
                valid_author = video_details.get('author', 'Unknown Artist')
                
                print(f"    ✅ Verified: {valid_title} by {valid_author}")
                
                playlist_items.append({
                    "type": "track",
                    "video_id": video_id,
                    "title": valid_title,
                    "artist": valid_author,
                    "duration": video_details.get('lengthSeconds', 0),
                    "original_ref": title_artist
                })
                
            except Exception as e:
                print(f"    ❌ Validation failed for {video_id}: {e}")
                playlist_items.append({
                    "type": "track",
                    "video_id": video_id,
                    "original_ref": title_artist,
                    "error": str(e),
                    "verified": False
                })
            
        # Add track to Markdown
        track = playlist_items[-1]
        t_title = track.get("title", title_artist)
        t_artist = track.get("artist", "")
        t_id = track.get("video_id")
        
        md_lines.append(f"### 🎵 {t_title} - {t_artist}")
        if t_id:
             md_lines.append(f"[Listen on YouTube Music](https://music.youtube.com/watch?v={t_id})")
        md_lines.append("\n---\n")

        last_pos = match.end()
    
    # Add remaining text as final segment
    final_raw_segment = raw_script[last_pos:]
    final_clean_segment = clean_narrative_segment(final_raw_segment)
    final_image_url = extract_image_url(final_raw_segment)
    
    if final_clean_segment:
        narrative_count += 1
        filename_base = f"part_{narrative_count:03d}"
        
        playlist_items.append({
            "type": "narrative",
            "text": final_clean_segment,
            "image_url": final_image_url,
            "audio_filename": f"{filename_base}.wav",
            "video_filename": f"{filename_base}.mp4"
        })
        
        # Add to Markdown
        md_lines.append(f"## Part {narrative_count}")
        if final_image_url:
            md_lines.append(f"![Visual]({final_image_url})")
        md_lines.append(f"\n{final_clean_segment}\n")
    
    print(f"✨ Verification Complete! Generated {len(playlist_items)} items.")

    # Save Markdown playlist
    md_path = os.path.join(playlist_dir, "playlist.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))
    print(f"📄 Saved formatted playlist to: {md_path}")

    # Save Curated Playlist JSON
    curated_json_path = os.path.join(playlist_dir, "curated_playlist.json")
    curated_data = {
        "title": playlist_title or state.get("topic"),
        "topic": state.get("topic"),
        "items": playlist_items
    }
    
    with open(curated_json_path, "w") as f:
        json.dump(curated_data, f, indent=4)
    print(f"💾 Saved structured playlist to: {curated_json_path}")
    
    return {
        "curated_playlist": curated_data,
        "playlist_title": playlist_title
    }
