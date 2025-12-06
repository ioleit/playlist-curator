# Curator

**curator** is a CLI tool that transforms static playlists into immersive audio documentaries. It uses an LLM to generate historical context and "liner notes" for songs, synthesizes them into speech using local AI, and weaves them into a playable YouTube Music playlist.

## Architecture

```mermaid
graph LR
    A[Input: "1960s Jazz"] --> B(LLM Engine: OpenRouter)
    B --> C{Narrative JSON}
    C --> D[TTS Engine: Kokoro-82M]
    D --> E((Local Audio .wav))
    E --> F[YouTube Music Locker]
    F --> G[Final Playlist]
    H[Official Song Catalog] --> G
```

- **Voice uses `Kokoro-82M`**

## Getting Started

### Prerequisites

- Python 3.10+
- `pip`
- [ffmpeg](https://ffmpeg.org/) (required for audio/video processing)

### Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Setup (One-time)

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
    Edit `config.json` to include your OpenRouter API key and YouTube Channel ID.

## Usage Workflow

### 1. Configuration
Create a directory for your new playlist (e.g., `my_new_playlist`) inside `data/playlists/` and add a `config.json`.

**Example:** `data/playlists/my_new_playlist/config.json`
```json
{
    "topic": "The History of Funk",
    "duration": "30m",
    "system_prompt": "default"
}
```
*Note: The `topic` field will be used as the YouTube Playlist title.*

### 2. Run the Curator
This generates the script, audio, and video files locally.

```bash
python curator.py my_new_playlist
```

**Output:** Inside `data/playlists/my_new_playlist/`, you will find:
- `script.txt` & `tracks.json`
- `part_001.mp4`, `part_002.mp4`, etc. (Narration videos)
- `part_001.txt`, etc. (Descriptions/Credits)

### 3. Manual Upload (API Workaround)
Since the YouTube API has strict limits on video uploads, upload the generated clips manually.

1.  **Upload Videos:** Upload all `part_XXX.mp4` files to your YouTube channel.
    *   **Important:** Keep the video titles as `part_001.mp4`, `part_002.mp4`, etc. so the scripts can identify them.
2.  **Create Playlist:** Create a **new playlist on YouTube** with a temporary random name (e.g., "temp_playlist_123"). This is because the curator might have generated a fancy title for your playlist (overwriting your config), and we want to avoid confusion.
3.  **Add Videos:** Add your uploaded "part" videos to this temporary playlist.
4.  **Set Manual Sorting:** Ensure the playlist sorting is set to **Manual** (custom ordering) in YouTube settings, not "Date Added".

### 4. Generate Playlist Plan
This script scans your temporary YouTube playlist to find the video IDs of the clips you just uploaded and merges them with the songs found in `tracks.json`.

You must provide the temporary playlist name you used in step 3 via `--temp-name`.

```bash
python yt_music/post_upload.py data/playlists/my_new_playlist --temp-name "temp_playlist_123"
```

This creates `youtube_playlists.json` in your playlist folder—a "master plan" interleaving narration and songs.

### 5. Apply to YouTube
This executes the plan, organizing the YouTube playlist.

```bash
python yt_music/update_youtube_playlist.py data/playlists/my_new_playlist
```

**What this does:**
- Wipes the existing items in the YouTube playlist.
- Rebuilds it in the correct order: `Narration 1` -> `Song 1` -> `Narration 2` -> `Song 2`...
- Updates titles and descriptions of your narration videos (adding credits/attribution).

## Project Structure

-   `models/`: AI models and download script.
-   `curation/`: Logic for content generation and media processing.
-   `text_to_speech/`: Kokoro TTS wrapper.
-   `yt_music/`: Scripts for YouTube playlist management.
-   `curator.py`: Main entry point.
