"""Python client for MiniMax H3 video workflows on Muapi."""

import os
import time
from typing import Any, Dict, Optional

import requests


class MiniMaxH3API:
    """Submit and poll MiniMax H3 video-generation tasks."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.muapi.ai/api/v1"):
        self.api_key = api_key or os.getenv("MUAPI_API_KEY")
        if not self.api_key:
            raise ValueError("Set MUAPI_API_KEY or pass api_key to MiniMaxH3API().")
        self.base_url = base_url.rstrip("/")
        self.headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}

    def text_to_video(self, prompt: str, webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """Create a MiniMax H3 text-to-video task."""
        return self._submit("minimax-h3-text-to-video", self._payload(prompt, webhook_url=webhook_url))

    def image_to_video(self, prompt: str, image_url: str, webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """Create a MiniMax H3 image-to-video task."""
        return self._submit("minimax-h3-image-to-video", self._payload(prompt, image_url=image_url, webhook_url=webhook_url))

    def first_last_frame(
        self,
        prompt: str,
        first_frame_image: str,
        last_frame_image: str,
        webhook_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a MiniMax H3 first-and-last-frame video task."""
        return self._submit(
            "minimax-h3-first-last-frame",
            self._payload(prompt, first_frame_image=first_frame_image, last_frame_image=last_frame_image, webhook_url=webhook_url),
        )

    def get_result(self, request_id: str) -> Dict[str, Any]:
        """Retrieve the current task result."""
        response = requests.get(f"{self.base_url}/predictions/{request_id}/result", headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def wait_for_completion(self, request_id: str, poll_interval: int = 5, timeout: int = 600) -> Dict[str, Any]:
        """Poll a task until it succeeds, fails, or times out."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.get_result(request_id)
            if result.get("status") in {"completed", "success", "failed"}:
                return result
            time.sleep(poll_interval)
        raise TimeoutError(f"MiniMax H3 task {request_id} did not complete within {timeout} seconds.")

    def _submit(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(f"{self.base_url}/{endpoint}", json=payload, headers=self.headers, timeout=60)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _payload(prompt: str, **kwargs: Optional[str]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"prompt": prompt}
        payload.update({key: value for key, value in kwargs.items() if value is not None})
        return payload
