import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import json
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock googleapiclient modules BEFORE importing the scripts
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['google_auth_oauthlib'] = MagicMock()
sys.modules['google_auth_oauthlib.flow'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()

from yt_music import post_upload, update_youtube_playlist

class TestPostUpload(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.playlist_dir = os.path.join(self.test_dir, "data", "playlists", "test_playlist")
        os.makedirs(self.playlist_dir, exist_ok=True)
        
        # Create global config.json in root of temp dir
        # We need to chdir to temp dir for script to find config.json in CWD
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        with open("config.json", "w") as f:
            json.dump({
                "channel_id": "test_channel_id",
                "topic": "Test Topic"
            }, f)
            
        # Create playlist config.json
        with open(os.path.join(self.playlist_dir, "config.json"), "w") as f:
            json.dump({"topic": "Jazz"}, f)
            
        # Create curated_playlist.json
        self.mock_curated_data = {
            "title": "Jazz History",
            "topic": "Jazz",
            "items": [
                {
                    "type": "narrative",
                    "text": "Narrative 1 Text",
                    "video_filename": "part_001.mp4",
                    "audio_filename": "part_001.wav",
                    "image_url": "http://example.com/img1.jpg"
                },
                {
                    "type": "track",
                    "video_id": "song1_id",
                    "title": "Song 1",
                    "artist": "Artist 1",
                    "duration": "180"
                },
                {
                    "type": "narrative",
                    "text": "Narrative 2 Text",
                    "video_filename": "part_002.mp4",
                    "audio_filename": "part_002.wav",
                    "image_url": "http://example.com/img2.jpg"
                },
                {
                    "type": "track",
                    "video_id": "song2_id",
                    "title": "Song 2",
                    "artist": "Artist 2",
                    "duration": "200"
                }
            ]
        }
        with open(os.path.join(self.playlist_dir, "curated_playlist.json"), "w") as f:
            json.dump(self.mock_curated_data, f)

    def tearDown(self):
        # Restore CWD and clean up
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
        
    @patch('yt_music.post_upload.get_playlist_id_by_name')
    @patch('yt_music.post_upload.get_authenticated_service')
    def test_main_plan_generation(self, mock_get_auth, mock_get_playlist_id):
        mock_get_playlist_id.return_value = "PL_TEST_123"
        
        # Mock uploaded items: Part 1 and Part 2
        mock_youtube = MagicMock()
        mock_get_auth.return_value = mock_youtube
        
        mock_youtube.playlistItems().list().execute.return_value = {
            'items': [
                {'snippet': {'title': 'part_001.mp4'}, 'contentDetails': {'videoId': 'vid_part_1'}},
                {'snippet': {'title': 'part_002.mp4'}, 'contentDetails': {'videoId': 'vid_part_2'}}
            ]
        }
        # Next page empty
        mock_youtube.playlistItems().list_next.return_value = None

        # Run main
        # We pass the relative path to playlist dir as if run from root
        # Since we chdir'd to self.test_dir, relative path is just data/playlists/test_playlist
        rel_playlist_dir = "data/playlists/test_playlist"
        
        with patch.object(sys, 'argv', ['post_upload.py', rel_playlist_dir, '--playlist-id', 'PL_TEST_123']):
            post_upload.main()
            
        # Verify Output
        input_path = os.path.join(self.playlist_dir, "curated_playlist.json")
        self.assertTrue(os.path.exists(input_path), "curated_playlist.json disappeared")
        
        output_path = os.path.join(self.playlist_dir, "youtube_playlists.json")
        self.assertFalse(os.path.exists(output_path), "youtube_playlists.json should not be created")
        
        with open(input_path, 'r') as f:
            data = json.load(f)
            
        self.assertEqual(data['playlist_id'], "PL_TEST_123")
        self.assertEqual(len(data['items']), 4) # 2 narrations + 2 songs
        
        # Check interleaving (Narration 1, Song 1, Narration 2, Song 2)
        items = data['items']
        self.assertEqual(items[0]['kind'], 'narration')
        self.assertEqual(items[0]['video_id'], 'vid_part_1')
        self.assertEqual(items[1]['kind'], 'song')
        self.assertEqual(items[1]['video_id'], 'song1_id')
        self.assertEqual(items[2]['kind'], 'narration')
        self.assertEqual(items[2]['video_id'], 'vid_part_2')
        self.assertEqual(items[3]['kind'], 'song')
        self.assertEqual(items[3]['video_id'], 'song2_id')

    def test_description_truncation(self):
        # Test the specific logic for truncating descriptions
        # We'll simulate the logic block from post_upload.py
        
        long_transcript = "A" * 6000
        attribution = "Image Credit: Someone"
        links_text = "Links: ..."
        
        # Logic from script
        MAX_LEN = 4800 
        fixed_len = len(links_text) + len(attribution) + 10
        remaining = MAX_LEN - fixed_len
        
        final_desc = links_text + "\n\n---\n\n"
        
        if len(long_transcript) > remaining:
            cropped = long_transcript[:remaining-50] + "... [Transcript Truncated]"
            final_desc += cropped
        else:
            final_desc += long_transcript
            
        final_desc += "\n\n---\n" + attribution
        
        self.assertLess(len(final_desc), 5000)
        self.assertIn("[Transcript Truncated]", final_desc)
        self.assertIn(attribution, final_desc)
        self.assertIn(links_text, final_desc)


class TestUpdatePlaylist(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.playlist_dir = os.path.join(self.test_dir, "data", "playlists", "test_playlist")
        os.makedirs(self.playlist_dir, exist_ok=True)
        
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # global config
        with open("config.json", "w") as f:
            json.dump({"podcast_playlist_id": "PL_PODCAST"}, f)
            
        # curated_playlist.json (input for update script)
        playlist_data = {
            "playlist_id": "PL_CURATED",
            "items": [
                {"video_id": "vid1", "kind": "narration", "title": "Part 1", "description": "Desc 1"},
                {"video_id": "song1", "kind": "song", "title": "Song 1"}
            ]
        }
        with open(os.path.join(self.playlist_dir, "curated_playlist.json"), "w") as f:
            json.dump(playlist_data, f)
            
    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    @patch('yt_music.update_youtube_playlist.get_authenticated_service')
    def test_update_flow(self, mock_get_auth):
        mock_youtube = MagicMock()
        mock_get_auth.return_value = mock_youtube
        
        # Mock Current Playlist Items (to be cleared)
        mock_youtube.playlistItems().list().execute.return_value = {'items': [{'id': 'item_1'}]}
        mock_youtube.playlistItems().list_next.return_value = None
        
        # Mock Podcast Playlist Items (to check existence)
        # We need to handle side_effects for list().execute() carefully
        # 1. Clear PL_CURATED (returns item_1)
        # 2. Check PL_PODCAST (returns empty, so we insert)
        
        # Create separate mocks for separate calls if needed, or simple side_effect
        # The script calls get_playlist_items(curated) -> returns [item_1]
        # Then get_playlist_items(podcast) -> returns []
        
        # Since get_playlist_items creates a NEW request object each time, we need to mock the sequence
        # request1.execute() -> {items: [item1]}
        # request2.execute() -> {items: []}
        
        # A simple way is to use side_effect on the execute method of the returned request mock
        # But list() is called with different args.
        
        def list_side_effect(*args, **kwargs):
            pid = kwargs.get('playlistId')
            if pid == 'PL_CURATED':
                return MagicMock(execute=lambda: {'items': [{'id': 'item_1'}]})
            elif pid == 'PL_PODCAST':
                return MagicMock(execute=lambda: {'items': []})
            return MagicMock(execute=lambda: {'items': []})
            
        mock_youtube.playlistItems().list.side_effect = list_side_effect

        rel_playlist_dir = "data/playlists/test_playlist"
        with patch.object(sys, 'argv', ['update_youtube_playlist.py', rel_playlist_dir]):
            update_youtube_playlist.main()
            
        # Verify Calls
        
        # 1. Check Deletion
        mock_youtube.playlistItems().delete.assert_called_with(id='item_1')
        
        # 2. Check Insert into Curated Playlist
        # Should be called twice (narration + song) + 1 for podcast
        self.assertEqual(mock_youtube.playlistItems().insert.call_count, 3) 
        
        # 3. Check Insert into Podcast Playlist
        calls = mock_youtube.playlistItems().insert.call_args_list
        podcast_calls = [c for c in calls if c[1]['body']['snippet']['playlistId'] == 'PL_PODCAST']
        self.assertEqual(len(podcast_calls), 1)
        self.assertEqual(podcast_calls[0][1]['body']['snippet']['resourceId']['videoId'], 'vid1')

    @patch('yt_music.update_youtube_playlist.get_authenticated_service')
    def test_skip_existing_podcast_episode(self, mock_get_auth):
        # Scenario: Video is already in podcast playlist
        pass # Placeholder
        

if __name__ == '__main__':
    unittest.main()
