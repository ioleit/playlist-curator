import unittest
from unittest.mock import MagicMock, patch, mock_open
import json
import os
from curation.nodes import verify_curation_node

class TestVerifyCuration(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
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
            "playlist_dir": "/tmp/test_playlist",
            "raw_script": self.sample_script,
            "topic": "Test Topic"
        }

    @patch("curation.nodes.YTMusic")
    @patch("curation.nodes.json.dump")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.join", side_effect=lambda *args: "/".join(args))
    def test_verify_curation_structure(self, mock_path_join, mock_file, mock_json_dump, MockYTMusic):
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

        # Retrieve the data passed to json.dump for curated_playlist.json
        # We expect json.dump to be called twice: once for playlist.md (wait no, playlist.md is write), 
        # once for curated_playlist.json, and once for tracks.json.
        # Let's filter for the one that looks like our playlist structure.
        
        curated_data = None
        for call in mock_json_dump.call_args_list:
            data = call[0][0]
            if "items" in data and "title" in data:
                curated_data = data
                break
        
        self.assertIsNotNone(curated_data, "curated_playlist.json structure not passed to json.dump")

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

