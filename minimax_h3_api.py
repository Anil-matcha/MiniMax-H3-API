"""Python client for MiniMax H3 video workflows on Muapi."""

import os
import time
import warnings
from typing import Any, Dict, Iterable, Optional

import requests


class MiniMaxH3API:
    """Submit and poll MiniMax H3 video-generation tasks."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.muapi.ai/api/v1"):
        self.api_key = api_key or os.getenv("MUAPI_API_KEY")
        if not self.api_key:
            raise ValueError("Set MUAPI_API_KEY or pass api_key to MiniMaxH3API().")
        self.base_url = base_url.rstrip("/")
        self.headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}

    def text_to_video(
        self,
        prompt: str,
        webhook_url: Optional[str] = None,
        *,
        aspect_ratio: str = "16:9",
        resolution: str = "2k",
        duration: int = 5,
    ) -> Dict[str, Any]:
        """Create a MiniMax H3 text-to-video task."""
        return self._submit(
            "minimax-h3-text-to-video",
            self._payload(
                prompt,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                duration=duration,
                webhook_url=webhook_url,
            ),
        )

    def image_to_video(
        self,
        prompt: str,
        image_url: str,
        webhook_url: Optional[str] = None,
        *,
        last_image_url: Optional[str] = None,
        resolution: str = "2k",
        duration: int = 5,
    ) -> Dict[str, Any]:
        """Create a MiniMax H3 image-to-video task."""
        return self._submit(
            "minimax-h3-image-to-video",
            self._payload(
                prompt,
                image_url=image_url,
                last_image_url=last_image_url,
                resolution=resolution,
                duration=duration,
                webhook_url=webhook_url,
            ),
        )

    def reference_to_video(
        self,
        prompt: str,
        reference_images: Optional[Iterable[str]] = None,
        reference_videos: Optional[Iterable[str]] = None,
        reference_audios: Optional[Iterable[str]] = None,
        webhook_url: Optional[str] = None,
        *,
        aspect_ratio: str = "16:9",
        resolution: str = "2k",
        duration: int = 5,
    ) -> Dict[str, Any]:
        """Create a MiniMax H3 reference-to-video task.

        At least one image or video reference is required. Audio references
        are optional and cannot be used on their own.
        """
        images = list(reference_images or [])
        videos = list(reference_videos or [])
        audios = list(reference_audios or [])
        if not images and not videos:
            raise ValueError("Provide at least one reference image or reference video.")

        return self._submit(
            "minimax-h3-reference-to-video",
            self._payload(
                prompt,
                reference_images=images,
                reference_videos=videos,
                reference_audios=audios,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                duration=duration,
                webhook_url=webhook_url,
            ),
        )

    def first_last_frame(
        self,
        prompt: str,
        first_frame_image: str,
        last_frame_image: str,
        webhook_url: Optional[str] = None,
        *,
        resolution: str = "2k",
        duration: int = 5,
    ) -> Dict[str, Any]:
        """Create a first/last-frame task through image-to-video.

        This compatibility method replaces the removed
        ``minimax-h3-first-last-frame`` endpoint. New code should call
        :meth:`image_to_video` with ``last_image_url`` directly.
        """
        warnings.warn(
            "first_last_frame() is deprecated; use image_to_video(..., last_image_url=...) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.image_to_video(
            prompt,
            first_frame_image,
            webhook_url=webhook_url,
            last_image_url=last_frame_image,
            resolution=resolution,
            duration=duration,
        )

    def get_result(self, request_id: str) -> Dict[str, Any]:
        """Retrieve the current task result."""
        response = requests.get(f"{self.base_url}/predictions/{request_id}/result", headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def wait_for_completion(self, request_id: str, poll_interval: float = 5, timeout: float = 600) -> Dict[str, Any]:
        """Poll a task until it succeeds, fails, or times out."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.get_result(request_id)
            if result.get("status") in {"completed", "success", "failed", "cancelled"}:
                return result
            time.sleep(poll_interval)
        raise TimeoutError(f"MiniMax H3 task {request_id} did not complete within {timeout} seconds.")

    def _submit(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(f"{self.base_url}/{endpoint}", json=payload, headers=self.headers, timeout=60)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _payload(prompt: str, **kwargs: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"prompt": prompt}
        payload.update({key: value for key, value in kwargs.items() if value is not None})
        return payload
