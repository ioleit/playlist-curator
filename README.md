# curator

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

- **Voice should use`Kokoro-82M`**

## Getting Started

### Prerequisites

- Python 3.10+
- `pip`

### Installation

1.  Clone the repository (if you haven't already).
2.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

### Setup

Before running the application, you need to download the Kokoro-82M model and voice files.

Run the setup script:

```bash
python models/download_models.py
```

This will download `kokoro-v1.0.onnx` and `voices-v1.0.bin` into the `models/` directory.

### Usage

To test the text-to-speech generation with a sample workflow:

```bash
python main.py "Your Topic"
```

Example:

```bash
python main.py "The History of Jazz"
```

This will generate an audio file (e.g., `output_TheHistoryofJazz.wav`) in the current directory.

## Project Structure

-   `models/`: Contains the ONNX model and voice binaries, plus the download script.
-   `text_to_speech/`: Source code for text-to-speech functionality.
    -   `tts.py`: Wrapper for `kokoro-onnx`.
-   `curator_graph.py`: LangGraph workflow definition.
-   `main.py`: Entry point for the application.
