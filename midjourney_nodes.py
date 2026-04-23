"""
MuAPI Midjourney ComfyUI Nodes
===============================
Focused nodes for Midjourney V7 / V8 / Niji on muapi.ai.

  MidjourneyV7    — POST /api/v1/midjourney-v7
  MidjourneyV8    — POST /api/v1/midjourney-v8
  MidjourneyNiji  — POST /api/v1/midjourney-niji

Each endpoint returns 4 images per run.

Auth:     x-api-key header
Polling:  GET /api/v1/predictions/{request_id}/result
Upload:   POST /api/v1/upload_file
"""

import io
import os
import time

import numpy as np
import requests
import torch
from PIL import Image

BASE_URL = "https://api.muapi.ai/api/v1"
POLL_INTERVAL = 5
MAX_WAIT = 600

ASPECT_RATIOS = ["1:1", "16:9", "9:16", "3:4", "4:3", "21:9"]

# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_api_key(api_key_input):
    """Return api_key_input if set, otherwise fall back to ~/.muapi/config.json."""
    if api_key_input and api_key_input.strip():
        return api_key_input.strip()
    config_path = os.path.expanduser("~/.muapi/config.json")
    if os.path.isfile(config_path):
        try:
            import json as _json
            with open(config_path) as f:
                key = _json.load(f).get("api_key", "")
            if key:
                return key
        except Exception:
            pass
    raise RuntimeError(
        "No API key found. Either paste your key into the api_key field, "
        "or run `muapi auth configure --api-key YOUR_KEY` in a terminal."
    )

def _upload_image(api_key, image_tensor):
    if image_tensor.dim() == 4:
        image_tensor = image_tensor[0]
    arr = (image_tensor.cpu().numpy() * 255).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, format="JPEG", quality=95)
    buf.seek(0)
    resp = requests.post(f"{BASE_URL}/upload_file",
                         headers={"x-api-key": api_key},
                         files={"file": ("image.jpg", buf, "image/jpeg")},
                         timeout=120)
    _check(resp)
    data = resp.json()
    u = data.get("url") or data.get("file_url") or data.get("output")
    if not u:
        raise RuntimeError(f"Upload missing URL: {data}")
    return str(u)

def _submit(api_key, endpoint, payload):
    resp = requests.post(f"{BASE_URL}/{endpoint}",
                         headers={"x-api-key": api_key, "Content-Type": "application/json"},
                         json=payload, timeout=60)
    _check(resp)
    rid = resp.json().get("request_id")
    if not rid:
        raise RuntimeError(f"No request_id: {resp.json()}")
    return rid

def _poll(api_key, request_id, tag):
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        resp = requests.get(f"{BASE_URL}/predictions/{request_id}/result",
                            headers={"x-api-key": api_key}, timeout=30)
        _check(resp)
        data = resp.json()
        status = data.get("status")
        print(f"[{tag}] {status}  {request_id}")
        if status == "completed":
            return data
        if status == "failed":
            raise RuntimeError(f"Failed: {data.get('error','unknown')}")
        time.sleep(POLL_INTERVAL)
    raise RuntimeError(f"Timeout: {request_id}")

def _extract_image_urls(result):
    """Pull the list of image URLs out of the prediction result."""
    urls = []
    out = result.get("outputs") or result.get("output") or result.get("result")
    if isinstance(out, dict):
        for key in ("images", "image_urls", "urls"):
            if isinstance(out.get(key), list):
                urls = [str(u) for u in out[key] if u]
                break
        if not urls and out.get("image_url"):
            urls = [str(out["image_url"])]
    elif isinstance(out, list):
        urls = [str(u) for u in out if u]
    elif isinstance(out, str):
        urls = [out]
    if not urls:
        for key in ("images", "image_urls", "urls"):
            if isinstance(result.get(key), list):
                urls = [str(u) for u in result[key] if u]
                break
    if not urls:
        raise RuntimeError(f"No image URLs in result: {result}")
    return urls

def _check(resp):
    if resp.status_code == 401:
        raise RuntimeError("Auth failed — check API key.")
    if resp.status_code == 402:
        raise RuntimeError("Insufficient credits — top up at muapi.ai")
    if resp.status_code == 429:
        raise RuntimeError("Rate limited — retry later.")
    resp.raise_for_status()

def _download_image(url):
    try:
        r = requests.get(url, timeout=180)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        arr = np.array(img).astype(np.float32) / 255.0
        return torch.from_numpy(arr)
    except Exception as e:
        print(f"[Midjourney] failed to download {url}: {e}")
        return torch.zeros(64, 64, 3)

def _urls_to_batch(urls):
    tensors = [_download_image(u) for u in urls]
    if not tensors:
        return torch.zeros(1, 64, 64, 3)
    heights = [t.shape[0] for t in tensors]
    widths = [t.shape[1] for t in tensors]
    h, w = max(heights), max(widths)
    padded = []
    for t in tensors:
        if t.shape[0] != h or t.shape[1] != w:
            pad = torch.zeros(h, w, 3)
            pad[:t.shape[0], :t.shape[1], :] = t
            padded.append(pad)
        else:
            padded.append(t)
    return torch.stack(padded, dim=0)

def _build_payload(prompt, aspect_ratio, stylize, chaos, weird,
                   negative_prompt, seed, image_url_str, api_key, ref_image):
    payload = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "stylize": int(stylize),
        "chaos": int(chaos),
        "weird": int(weird),
    }
    if negative_prompt and negative_prompt.strip():
        payload["negative_prompt"] = negative_prompt.strip()
    if seed and int(seed) > 0:
        payload["seed"] = int(seed)
    ref_url = None
    if image_url_str and image_url_str.strip():
        ref_url = image_url_str.strip()
    elif ref_image is not None:
        print("[Midjourney] Uploading reference image...")
        ref_url = _upload_image(api_key, ref_image)
    if ref_url:
        payload["image_url"] = ref_url
    return payload

def _run_midjourney(endpoint, tag, prompt, aspect_ratio, stylize, chaos, weird,
                    negative_prompt, seed, image_url, ref_image, api_key):
    api_key = _load_api_key(api_key)
    payload = _build_payload(prompt, aspect_ratio, stylize, chaos, weird,
                             negative_prompt, seed, image_url, api_key, ref_image)
    print(f"[{tag}] Submitting...")
    rid = _submit(api_key, endpoint, payload)
    result = _poll(api_key, rid, tag)
    urls = _extract_image_urls(result)
    print(f"[{tag}] Done — {len(urls)} image(s)")
    batch = _urls_to_batch(urls)
    return (batch, urls[0], "\n".join(urls), rid)


# ── Base Node ──────────────────────────────────────────────────────────────────

def _common_inputs(default_prompt):
    return {
        "required": {
            "prompt": ("STRING", {"multiline": True, "default": default_prompt}),
            "aspect_ratio": (ASPECT_RATIOS, {"default": "1:1"}),
            "stylize": ("INT", {"default": 100, "min": 0, "max": 1000, "step": 10,
                "tooltip": "How artistic the result is (0–1000). Lower = literal, higher = stylized."}),
            "chaos": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1,
                "tooltip": "Variation across the 4 images (0–100)."}),
            "weird": ("INT", {"default": 0, "min": 0, "max": 3000, "step": 50,
                "tooltip": "Adds unconventional aesthetics (0–3000)."}),
        },
        "optional": {
            "api_key": ("STRING", {"multiline": False, "default": ""}),
            "negative_prompt": ("STRING", {"multiline": True, "default": "",
                "tooltip": "Things to exclude (e.g. 'text, watermark, blurry')."}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 4294967295, "step": 1,
                "tooltip": "0 = random. Same seed + prompt ≈ similar result."}),
            "image_url": ("STRING", {"multiline": False, "default": "",
                "tooltip": "Optional reference image URL. Overrides ref_image if both set."}),
            "ref_image": ("IMAGE", {"tooltip": "Optional reference image (uploaded to muapi)."}),
        },
    }


# ── Nodes ──────────────────────────────────────────────────────────────────────

class MidjourneyV7:
    """
    Midjourney V7 (Text-to-Image)
    ------------------------------
    Generates 4 photorealistic images per run.
    Supply an optional reference image URL or IMAGE input to guide style/content.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return _common_inputs("A majestic snow leopard resting on a mountain cliff at golden hour, hyperrealistic photography")
    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("images", "first_url", "all_urls", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎨 Midjourney"

    def run(self, prompt, aspect_ratio, stylize, chaos, weird,
            api_key="", negative_prompt="", seed=0, image_url="", ref_image=None):
        return _run_midjourney("midjourney-v7", "Midjourney V7",
                               prompt, aspect_ratio, stylize, chaos, weird,
                               negative_prompt, seed, image_url, ref_image, api_key)


class MidjourneyV8:
    """
    Midjourney V8 (Text-to-Image)
    ------------------------------
    Latest Midjourney generation — 4 images per run with improved coherence
    and detail vs V7. Reference image guidance supported.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return _common_inputs("A cinematic portrait of a lone astronaut on a neon-lit desert planet, ultra detailed, 8K")
    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("images", "first_url", "all_urls", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎨 Midjourney"

    def run(self, prompt, aspect_ratio, stylize, chaos, weird,
            api_key="", negative_prompt="", seed=0, image_url="", ref_image=None):
        return _run_midjourney("midjourney-v8", "Midjourney V8",
                               prompt, aspect_ratio, stylize, chaos, weird,
                               negative_prompt, seed, image_url, ref_image, api_key)


class MidjourneyNiji:
    """
    Midjourney Niji (Anime / Illustration)
    ---------------------------------------
    Optimized for anime, manga, and stylized illustrations.
    4 images per run. Reference image guidance supported.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return _common_inputs("Anime-style illustration of a young swordswoman under cherry blossoms, Studio Ghibli inspired, soft lighting")
    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("images", "first_url", "all_urls", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎨 Midjourney"

    def run(self, prompt, aspect_ratio, stylize, chaos, weird,
            api_key="", negative_prompt="", seed=0, image_url="", ref_image=None):
        return _run_midjourney("midjourney-niji", "Midjourney Niji",
                               prompt, aspect_ratio, stylize, chaos, weird,
                               negative_prompt, seed, image_url, ref_image, api_key)


class MidjourneyApiKey:
    """
    Store your MuAPI API key once and wire it to any Midjourney node.
    Leave all node api_key fields empty — they auto-read from this node
    or from ~/.muapi/config.json (set via `muapi auth configure`).
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "api_key": ("STRING", {"multiline": False, "default": "",
                "tooltip": "Your muapi.ai API key. Get one at muapi.ai → Dashboard → API Keys"}),
        }}
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("api_key",)
    FUNCTION = "run"
    CATEGORY = "🎨 Midjourney"

    def run(self, api_key):
        return (_load_api_key(api_key),)


NODE_CLASS_MAPPINGS = {
    "MidjourneyApiKey": MidjourneyApiKey,
    "MidjourneyV7":     MidjourneyV7,
    "MidjourneyV8":     MidjourneyV8,
    "MidjourneyNiji":   MidjourneyNiji,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MidjourneyApiKey": "🔑 Midjourney API Key",
    "MidjourneyV7":     "🎨 Midjourney V7",
    "MidjourneyV8":     "🎨 Midjourney V8",
    "MidjourneyNiji":   "🎨 Midjourney Niji",
}
