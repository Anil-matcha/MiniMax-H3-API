# MiniMax H3 API: Python SDK for AI Video Generation

[![Powered by MuAPI](https://img.shields.io/badge/Powered%20by-MuAPI-6366f1?style=flat-square)](https://muapi.ai/minimax-h3?utm_source=github&utm_medium=badge&utm_campaign=minimax-h3-api)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

Python SDK for the **MiniMax H3 API** on [Muapi](https://muapi.ai/minimax-h3?utm_source=github&utm_medium=readme&utm_campaign=minimax-h3-api). Generate video from text, animate a still image, or guide a new video with image, video, and optional audio references using one API key.

<p align="center"><a href="https://youtu.be/C_46zmUEHnQ"><img src="https://i.ytimg.com/vi/C_46zmUEHnQ/maxresdefault.jpg" width="720"></a></p>
<p align="center"><a href="https://youtu.be/C_46zmUEHnQ"><b>▶ Watch: How to Access MiniMax Hailuo H3 API (Step-by-Step Guide): Native 2K Video Generation with Sound</b></a></p>

## Related Projects

- [Open-Generative-AI](https://github.com/Anil-matcha/Open-Generative-AI) — open-source studio and model hub for generative image and video workflows.
- [awesome-ai-video-models](https://github.com/Anil-matcha/awesome-ai-video-models) — compare leading AI video models, API access, and pricing.
- [Seedance-2-API](https://github.com/Anil-matcha/Seedance-2-API) — Python SDK for ByteDance Seedance text-to-video and image-to-video workflows.
- [Veo-4-API](https://github.com/Anil-matcha/Veo-4-API) — Python SDK for Google Veo video-generation workflows.
- [Flux-3-Dev-API](https://github.com/Anil-matcha/Flux-3-Dev-API) — unified image and video SDK for the FLUX 3 family.
- [Generative-Media-Skills](https://github.com/SamurAIGPT/Generative-Media-Skills) — agent-ready skills for building generative-media pipelines.
- [muapi-cli](https://github.com/SamurAIGPT/muapi-cli) — CLI and MCP access to Muapi generation tasks.

## Features

- Text-to-video generation
- Image-to-video animation
- Reference-to-video generation with multimodal inputs
- First-and-last-frame guidance through image-to-video
- Submit, poll, and webhook-ready asynchronous workflow
- Simple Python client built on `requests`

## Installation

```bash
pip install minimax-h3-api
```

Or install from source:

```bash
git clone https://github.com/Anil-matcha/MiniMax-H3-API.git
cd MiniMax-H3-API
pip install -e .
```

Set your Muapi API key:

```bash
export MUAPI_API_KEY=your_muapi_api_key
```

## Quick start

```python
from minimax_h3_api import MiniMaxH3API

api = MiniMaxH3API()

task = api.text_to_video(
    "A cinematic tracking shot of a silver sports car driving through a rain-soaked city at night",
    aspect_ratio="16:9",
    resolution="2k",
    duration=5,
)

result = api.wait_for_completion(task["request_id"])
print(result["outputs"][0])
```

## Workflows

### Text to video

```python
task = api.text_to_video(
    prompt="A lone astronaut walking through a field of bioluminescent flowers, slow camera dolly in"
)
```

### Image to video

```python
task = api.image_to_video(
    prompt="The camera slowly pushes in as a warm breeze moves through the subject's hair",
    image_url="https://example.com/source-image.jpg",
    last_image_url="https://example.com/final-frame.jpg",
    duration=5,
)
```

### Reference to video

```python
task = api.reference_to_video(
    prompt="Use the references to create a cinematic product reveal with a slow camera orbit",
    reference_images=["https://example.com/product.jpg"],
    reference_videos=["https://example.com/motion-reference.mp4"],
    reference_audios=["https://example.com/soundtrack.mp3"],
    aspect_ratio="16:9",
    resolution="2k",
    duration=5,
)
```

At least one `reference_images` or `reference_videos` URL is required. Audio references are optional and cannot be used alone.

### First and last frame compatibility alias

Existing integrations can continue using `first_last_frame()`. It now maps to the current image-to-video endpoint with `image_url` and `last_image_url`; new code should call `image_to_video()` directly.

## API endpoints

| Workflow | Endpoint |
| --- | --- |
| Text to Video | `POST /api/v1/minimax-h3-text-to-video` |
| Image to Video | `POST /api/v1/minimax-h3-image-to-video` |
| Reference to Video | `POST /api/v1/minimax-h3-reference-to-video` |
| Poll task | `GET /api/v1/predictions/{request_id}/result` |

See the full [MiniMax H3 API guide](https://muapi.ai/minimax-h3?utm_source=github&utm_medium=readme&utm_campaign=minimax-h3-api) and [Muapi documentation](https://docs.muapi.ai).

## License

MIT
