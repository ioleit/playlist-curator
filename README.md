# 🎵 Playlist Curator

A CLI tool to generate narrated music playlists.

It uses an LLM to generate historical context and "liner notes" for songs, synthesizes them into speech using local AI, and weaves them into a playable YouTube Music playlist.

### 📦 Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### ⚙️ Setup (One-time)

1.  **Download Models:**
    Run the setup script to download the Kokoro-82M model and voice files:
    ```bash
    python models/download_models.py
    ```
    This places `kokoro-v1.0.onnx` and `voices-v1.0.bin` in `models/`.

2.  **Authentication:**
    Ensure you have a `client_secrets.json` file in the root directory for YouTube API access (OAuth 2.0 Client ID).

3.  **Configuration:**
    Copy `config.json.example` to `config.json` and fill in your details:
    ```bash
    cp config.json.example config.json
    ```
    Edit `config.json` to include your OpenRouter API key, YouTube Channel ID, etc.

## 🚀 Usage Workflow

### 📝 1. Configuration
Create a directory for your new playlist (e.g., `my_new_playlist`) inside `data/playlists/` and add a `config.json`.

**Example:** `data/playlists/my_new_playlist/config.json`
```json
{
    "topic": "History of G-Funk",
    "duration": "30m",
    "system_prompt": "default"
}
```

### 🏃 2. Run the Curator
This generates the script, audio, and video files locally.

```bash
python curator.py my_new_playlist
```

**Output:** Inside `data/playlists/my_new_playlist/`, you will find:
- `curated_playlist.json`
- `response.txt`
- `part_001.mp4`, `part_002.mp4`, etc. (Narration videos)
- `part_001.txt`, etc. (Descriptions/Credits)
- etc.

### 📤 3. Manual Upload (API Workaround)
Since the YouTube API has strict limits on video uploads, upload the generated clips manually.

1.  **Upload Videos:** Upload all `my_new_playlist_part_XXX.mp4` files to your YouTube channel.
2.  **Create Playlist:** Create a **new playlist on YouTube** with a temporary random name (e.g., "temp_playlist_123").
    *   *Important:* Ensure the playlist sorting is set to **Manual** (custom ordering) in YouTube settings, not "Date Added".
3.  **Add Videos:** Add your uploaded "part" videos to this temporary playlist.
4.  **Sync Local Data:** Run the post-upload tool.

```bash
python -m yt_music.post_upload data/playlists/my_new_playlist --playlist-id PLxyz
```

This enriches `curated_playlist.json` in your playlist folder with YouTube video IDs and descriptions.

### ✨ 4. Apply to YouTube
This executes the plan, organizing the YouTube playlist.

```bash
python -m yt_music.update_youtube_playlist data/playlists/my_new_playlist
```
