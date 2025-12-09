import unittest
from unittest.mock import MagicMock, patch
import json
import os
import shutil
import tempfile
from curation.nodes import verify_curation_node

class TestVerifyCuration(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        self.playlist_id = "test_playlist"
        self.playlist_dir = os.path.join("data", "playlists", self.playlist_id)
        os.makedirs(self.playlist_dir, exist_ok=True)

        with open(os.path.join(self.playlist_dir, "config.json"), "w") as f:
            json.dump({
                "topic": "Test Topic",
                "duration": "15m",
                "system_prompt": "default"
            }, f)

        self.sample_script = """
[TITLE: Test Playlist Title]

Welcome to the show.
[TRACK: Song A by Artist A | ID: video_id_1]

This is the second segment.
[IMAGE_URL: http://example.com/image.jpg]

[TRACK: Song B by Artist B | ID: video_id_2]

Outro text.
"""
        self.state = {
            "playlist_id": self.playlist_id,
            "raw_script": self.sample_script
        }

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)

    @patch("curation.nodes.YTMusic")
    def test_verify_curation_structure(self, MockYTMusic):
        # Setup YTMusic mock
        mock_yt = MockYTMusic.return_value
        mock_yt.get_song.side_effect = [
            # Song 1
            {
                "videoDetails": {
                    "title": "Verified Title A",
                    "author": "Verified Artist A",
                    "lengthSeconds": "180"
                }
            },
            # Song 2
            {
                "videoDetails": {
                    "title": "Verified Title B",
                    "author": "Verified Artist B",
                    "lengthSeconds": "240"
                }
            }
        ]

        # Run the function
        result = verify_curation_node(self.state)

        curated_data = result["curated_playlist"]

        # 1. Check Top Level Fields
        self.assertEqual(curated_data["title"], "Test Playlist Title")
        self.assertEqual(curated_data["topic"], "Test Topic")

        items = curated_data["items"]
        self.assertEqual(len(items), 5) # Intro -> Track 1 -> Seg 2 -> Track 2 -> Outro

        # 2. Check Item Types and Order
        self.assertEqual(items[0]["type"], "narrative")
        self.assertEqual(items[1]["type"], "track")
        self.assertEqual(items[2]["type"], "narrative")
        self.assertEqual(items[3]["type"], "track")
        self.assertEqual(items[4]["type"], "narrative")

        # 3. Check Narrative Content
        self.assertIn("Welcome to the show", items[0]["text"])
        self.assertEqual(items[0]["audio_filename"], "part_001.wav")
        self.assertEqual(items[0]["video_filename"], "part_001.mp4")

        # Check Image URL extraction
        self.assertEqual(items[2]["image_url"], "http://example.com/image.jpg")
        self.assertEqual(items[2]["audio_filename"], "part_002.wav")

        # 4. Check Track Content
        self.assertEqual(items[1]["video_id"], "video_id_1")
        self.assertEqual(items[1]["title"], "Verified Title A")
        self.assertEqual(items[1]["artist"], "Verified Artist A")
        
        self.assertEqual(items[3]["video_id"], "video_id_2")

if __name__ == "__main__":
    unittest.main()

