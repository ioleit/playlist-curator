import os
import requests
import sys

MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

def download_file(url, filename):
    # Determine the directory of the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    if os.path.exists(file_path):
        # Check if file is empty or too small (heuristic for broken download)
        if os.path.getsize(file_path) > 1024: 
            print(f"{file_path} already exists. Skipping download.")
            return
        else:
            print(f"{file_path} exists but seems too small. Re-downloading.")

    print(f"Downloading {filename} from {url} to {file_path}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded {filename}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {filename}: {e}")
        sys.exit(1)

def main():
    download_file(MODEL_URL, "kokoro-v1.0.onnx")
    download_file(VOICES_URL, "voices-v1.0.bin")

if __name__ == "__main__":
    main()
