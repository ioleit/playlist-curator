# YouTube Music Integration Workflow

This directory contains the tools for finalizing your curated playlist on YouTube. The workflow is designed to work around API quotas by using **manual uploads** for heavy video files, while using scripts for lightweight metadata and playlist management.

## ⚠️ API Quota & Cost

**Free Quota: 10,000 units per day.**

The workflow is optimized to be cheap:

*   **Video Uploads:** 1600 units per video. (This is why we do this **MANUALLY**).
*   **Playlist Updates:** ~50 units per insert/delete.
*   **Metadata Updates:** ~50 units per video update.
*   **Reads/Searches:** ~1 unit.

**Estimated Cost per 10-track Playlist:**
*   **Step 1 (Uploads):** 0 units (Manual).
*   **Step 2 (Plan):** ~5-10 units (Read playlist).
*   **Step 3 (Update):**
    *   Clear old items: 10 * 50 = 500
    *   Add new items: 20 * 50 = 1000 (10 songs + 10 narrations)
    *   Update Metadata: 10 * 50 = 500
    *   Sync to Podcast: 10 * 50 = 500 (First time only)
    *   **Total:** ~2,500 units.

You can comfortably manage ~3-4 full playlists per day on the free tier.

---

## Prerequisities

1.  **YouTube Channel:** You need a channel.
2.  **Global Podcast Playlist:** Create a standard playlist on your channel (e.g., "AI Curator Episodes") to serve as the "Podcast" container.
    *   Copy its Playlist ID (from the URL `list=PL...`).
    *   Add it to your `config.json` as `"podcast_playlist_id": "PL..."`.
3.  **Secrets:** Ensure `client_secrets.json` is in the project root.

---

## The Workflow

### 1. Manual Upload (The Heavy Lifting)
Go to [YouTube Studio](https://studio.youtube.com/) and create a new **Private or Unlisted** playlist for your specific topic (e.g., "Space Jazz").

*   **Upload** all your generated `part_XXX.mp4` narration files to this playlist.
*   **Title Requirement:** Ensure the video titles contain "part 1", "part 2", etc. (e.g., `part_001.mp4`).
    *   *Tip:* You can drag-and-drop the files directly; YouTube usually preserves the filename as the title.
*   **Wait:** Ensure uploads are finished processing.

### 2. Generate the Plan (`post_upload.py`)
This script matches your uploaded videos with your generated script and tracks to build the final playlist structure.

```bash
# Usage: python3 -m yt_music.post_upload <playlist_dir> --playlist-id <Manual_Playlist_ID>

python3 -m yt_music.post_upload data/playlists/space_jazz --playlist-id PLx4...
```

*   **What it does:**
    *   Finds the uploads in the specified playlist.
    *   Enriches `curated_playlist.json` in your playlist folder.
    *   Constructs rich descriptions with transcript, links, and attribution.

### 3. Apply Changes (`update_youtube_playlist.py`)
This script executes the plan, updating metadata and organizing the playlist.

```bash
# Usage: python3 -m yt_music.update_youtube_playlist <playlist_dir>

python3 -m yt_music.update_youtube_playlist data/playlists/space_jazz
```

*   **What it does:**
    *   **Updates Metadata:** Sets Titles to `<Topic> (Episode N)` and applies the rich description.
    *   **Visibility:** Sets narration videos to `Unlisted` and `Music` category.
    *   **Podcast Sync:** Adds narration videos to your Global Podcast Playlist (so they appear in YT Music as episodes).
    *   **Playlist Construction:** Clears the manual playlist and rebuilds it: `Narration 1 -> Song 1 -> Narration 2 -> Song 2...`

### 4. Final Verification
Go to YouTube and check the playlist.
*   Ensure the order is correct (Narration -> Song).
*   Check that narration videos have the correct "Episode" titles and descriptions.
*   Check that the videos appear in your "Podcast" playlist.
