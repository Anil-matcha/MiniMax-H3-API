import unittest
from unittest.mock import Mock, patch

from minimax_h3_api import MiniMaxH3API


class MiniMaxH3APITest(unittest.TestCase):
    def setUp(self):
        self.api = MiniMaxH3API(api_key="test-key")
        self.response = Mock()
        self.response.json.return_value = {"request_id": "req-123", "status": "processing"}

    @patch("minimax_h3_api.requests.post")
    def test_text_to_video_uses_current_contract(self, post):
        post.return_value = self.response

        self.api.text_to_video(
            "A cinematic sunrise",
            aspect_ratio="9:16",
            resolution="2k",
            duration=10,
            webhook_url="https://example.com/webhook",
        )

        post.assert_called_once_with(
            "https://api.muapi.ai/api/v1/minimax-h3-text-to-video",
            json={
                "prompt": "A cinematic sunrise",
                "aspect_ratio": "9:16",
                "resolution": "2k",
                "duration": 10,
                "webhook_url": "https://example.com/webhook",
            },
            headers=self.api.headers,
            timeout=60,
        )
        self.response.raise_for_status.assert_called_once_with()

    @patch("minimax_h3_api.requests.post")
    def test_image_to_video_supports_last_frame(self, post):
        post.return_value = self.response

        self.api.image_to_video(
            "Camera pushes in",
            "https://example.com/first.jpg",
            last_image_url="https://example.com/last.jpg",
            duration=15,
        )

        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "prompt": "Camera pushes in",
                "image_url": "https://example.com/first.jpg",
                "last_image_url": "https://example.com/last.jpg",
                "resolution": "2k",
                "duration": 15,
            },
        )

    @patch("minimax_h3_api.requests.post")
    def test_reference_to_video_uses_multimodal_inputs(self, post):
        post.return_value = self.response

        self.api.reference_to_video(
            "Create a product reveal",
            reference_images=("https://example.com/product.jpg",),
            reference_videos=["https://example.com/motion.mp4"],
            reference_audios=["https://example.com/audio.mp3"],
        )

        self.assertEqual(post.call_args.args[0], "https://api.muapi.ai/api/v1/minimax-h3-reference-to-video")
        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "prompt": "Create a product reveal",
                "reference_images": ["https://example.com/product.jpg"],
                "reference_videos": ["https://example.com/motion.mp4"],
                "reference_audios": ["https://example.com/audio.mp3"],
                "aspect_ratio": "16:9",
                "resolution": "2k",
                "duration": 5,
            },
        )

    @patch("minimax_h3_api.requests.post")
    def test_reference_to_video_requires_visual_reference(self, post):
        with self.assertRaisesRegex(ValueError, "at least one reference image or reference video"):
            self.api.reference_to_video(
                "Create a video",
                reference_audios=["https://example.com/audio.mp3"],
            )
        post.assert_not_called()

    @patch("minimax_h3_api.requests.post")
    def test_first_last_frame_compatibility_alias_uses_image_to_video(self, post):
        post.return_value = self.response

        with self.assertWarns(DeprecationWarning):
            self.api.first_last_frame(
                "Transition between frames",
                "https://example.com/first.jpg",
                "https://example.com/last.jpg",
            )

        self.assertEqual(
            post.call_args.args[0],
            "https://api.muapi.ai/api/v1/minimax-h3-image-to-video",
        )
        self.assertEqual(post.call_args.kwargs["json"]["image_url"], "https://example.com/first.jpg")
        self.assertEqual(post.call_args.kwargs["json"]["last_image_url"], "https://example.com/last.jpg")


if __name__ == "__main__":
    unittest.main()
