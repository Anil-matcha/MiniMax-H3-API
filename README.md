# MiniMax H3 API: Python SDK and MiniMax H3 Image API

[![Powered by MuAPI](https://img.shields.io/badge/Powered%20by-MuAPI-6366f1?style=flat-square)](https://muapi.ai/minimax-h3?utm_source=github&utm_medium=badge&utm_campaign=minimax-h3-api)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

Python SDK for the **MiniMax H3 API** on [Muapi](https://muapi.ai/minimax-h3?utm_source=github&utm_medium=readme&utm_campaign=minimax-h3-api), with a REST example for the **MiniMax H3 Image API**. Generate video from text, animate a still image, guide a video with multimodal references, or create high-resolution images from text with one Muapi API key.

<p align="center"><a href="https://youtu.be/C_46zmUEHnQ"><img src="https://i.ytimg.com/vi/C_46zmUEHnQ/maxresdefault.jpg" width="720"></a></p>
<p align="center"><a href="https://youtu.be/C_46zmUEHnQ"><b>▶ Watch: How to Access MiniMax Hailuo H3 API (Step-by-Step Guide): Native 2K Video Generation with Sound</b></a></p>

## Related Projects

- [MiniMax H3 text-to-video playground](https://muapi.ai/playground/minimax-h3-text-to-video) — Try the primary SDK workflow in the browser before integrating it.
- [MiniMax-H3-Spicy-API](https://github.com/Anil-matcha/MiniMax-H3-Spicy-API) — compare the eight H3, H3 Max and H3 Max Turbo Spicy (relaxed-moderation) video endpoints with schemas, pricing and examples.
- [awesome-minimax-h3-prompts](https://github.com/Anil-matcha/awesome-minimax-h3-prompts) — Prompt gallery with runnable MuAPI examples and creator-ready video references.
- [Open-Generative-AI](https://github.com/Anil-matcha/Open-Generative-AI) — open-source studio and model hub for generative image and video workflows.
- [awesome-ai-video-models](https://github.com/Anil-matcha/awesome-ai-video-models) — compare leading AI video models, API access, and pricing.
- [Seedance-2-API](https://github.com/Anil-matcha/Seedance-2-API) — Python SDK for ByteDance Seedance text-to-video and image-to-video workflows.
- [Veo-4-API](https://github.com/Anil-matcha/Veo-4-API) — Python SDK for Google Veo video-generation workflows.
- [Flux-3-Dev-API](https://github.com/Anil-matcha/Flux-3-Dev-API) — unified image and video SDK for the FLUX 3 family.
- [minimax-music-3-api](https://github.com/SamurAIGPT/minimax-music-3-api) — Python SDK for MiniMax's Music 3.0 text-to-music model, same vendor family.
- [awesome-minimax-music-3-prompts](https://github.com/Anil-matcha/awesome-minimax-music-3-prompts) — Prompt gallery for MiniMax Music 3.0.
- [muapi-skills](https://github.com/SamurAIGPT/muapi-skills) — agent-ready skills for building generative-media pipelines.
- [muapi-cli](https://github.com/SamurAIGPT/muapi-cli) — CLI and MCP access to Muapi generation tasks.

## Features

- Text-to-video generation
- Image-to-video animation
- Reference-to-video generation with multimodal inputs
- First-and-last-frame guidance through image-to-video
- MiniMax H3 Image API text-to-image generation through the Muapi REST API
- Submit, poll, and webhook-ready asynchronous workflow
- Simple Python client built on `requests`

## MiniMax H3 Image API (Text to Image)

The **MiniMax H3 Image API** creates images from text prompts with built-in prompt enhancement. The standard text-to-image endpoint supports 13 aspect ratios, 1K, 2K, or 4K resolution, and PNG, JPG, or WebP output. This repository's Python client wraps the H3 video workflows; call the image endpoint with the same Muapi API key using the REST API:

```bash
curl -X POST https://api.muapi.ai/api/v1/minimax-h3-image-text-to-image \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A frosted glass serum bottle on wet travertine stone, soft morning light","aspect_ratio":"4:5","resolution":"2K","output_format":"png"}'

# Response: {"request_id":"REQUEST_ID"}
```

Image generation is asynchronous. Poll the request with the standard Muapi result endpoint until it completes, then read the generated image URL from the response:

```bash
curl https://api.muapi.ai/api/v1/predictions/REQUEST_ID/result \
  -H "x-api-key: YOUR_API_KEY"
```

See the [MiniMax H3 Image API guide](https://muapi.ai/minimax-h3-image?utm_source=github&utm_medium=readme&utm_campaign=minimax-h3-api) for the text-to-image and image-edit workflows.

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
| MiniMax H3 Image text-to-image | `POST /api/v1/minimax-h3-image-text-to-image` |
| Poll task | `GET /api/v1/predictions/{request_id}/result` |

See the full [MiniMax H3 API guide](https://muapi.ai/minimax-h3?utm_source=github&utm_medium=readme&utm_campaign=minimax-h3-api) and [Muapi documentation](https://docs.muapi.ai).

## License

MIT
