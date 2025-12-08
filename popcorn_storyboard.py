#!/usr/bin/env python3
"""
Popcorn Storyboard Generator
Inspired by Higgsfield Popcorn - Generate 4-8 consistent frames from text + reference images

Usage:
    python popcorn_storyboard.py --prompt "detective investigating a crime scene" --references https://example.com/char.png https://example.com/env.png --frames 6
"""

import asyncio
import argparse
import logging
import json
import sys
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel
import aiohttp

import os
import time
from dotenv import load_dotenv
load_dotenv()

from secrets import MUAPIAPP_API_KEY

class LLMClient:
    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.muapi.ai/api/v1"

    async def call(self, system_prompt: str, user_prompt: str, response_format: type = None, temperature: float = 0.7) -> dict:
        url = f"{self.base_url}/{self.model}"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
        
        payload = {
            "prompt": full_prompt,
        }

        begin = time.time()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                     text = await response.text()
                     raise Exception(f"Error: {response.status}, {text}")
                     
                result = await response.json()
                request_id = result["request_id"]
                logger.info(f"Task submitted. Request ID: {request_id}")

            result_url = f"{self.base_url}/predictions/{request_id}/result"
            headers = {"x-api-key": self.api_key}

            while True:
                async with session.get(result_url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        status = result["status"]

                        if status == "completed":
                            end = time.time()
                            logger.info(f"Task completed in {end - begin:.2f} seconds.")
                            text = result["outputs"][0]
                            
                            if response_format == dict:
                                try:
                                    clean_text = text.strip()
                                    if clean_text.startswith("```json"):
                                        clean_text = clean_text[7:]
                                    if clean_text.startswith("```"): 
                                        clean_text = clean_text[3:]
                                    if clean_text.endswith("```"):
                                        clean_text = clean_text[:-3]
                                    return json.loads(clean_text)
                                except json.JSONDecodeError:
                                    logger.warning("Failed to parse JSON from LLM response")
                                    return {"raw_output": text}
                            return text
                            
                        elif status == "failed":
                            raise Exception(f"Task failed: {result.get('error')}")
                    else:
                        text = await response.text()
                        raise Exception(f"Error: {response.status}, {text}")

                await asyncio.sleep(0.5)

class NanoBananaImageGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.muapi.ai/api/v1"
        
    async def _submit_and_poll(self, model: str, payload: dict) -> str:
        url = f"{self.base_url}/{model}"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            # Submit
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Error submitting to {model}: {response.status}, {text}")
                result = await response.json()
                request_id = result["request_id"]
                logger.info(f"Task submitted to {model}. Request ID: {request_id}")
            
            # Poll
            result_url = f"{self.base_url}/predictions/{request_id}/result"
            headers = {"x-api-key": self.api_key}
            
            while True:
                async with session.get(result_url, headers=headers) as response:
                    if response.status != 200:
                         text = await response.text()
                         raise Exception(f"Polling error: {response.status}, {text}")
                    
                    result = await response.json()
                    status = result["status"]
                    
                    if status == "completed":
                        return result["outputs"][0]
                    elif status == "failed":
                        raise Exception(f"Task failed: {result.get('error')}")
                    
                await asyncio.sleep(0.5)

    async def generate_image(self, prompt: str, aspect_ratio: str = "16:9") -> str:
        """Generate image from text (T2I)"""
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio
        }
        return await self._submit_and_poll("nano-banana", payload)
        
    async def generate_with_references(self, prompt: str, reference_images: List[str], aspect_ratio: str = "16:9") -> str:
        """Generate image with references (I2I/Edit)"""
        payload = {
            "prompt": prompt,
            "images_list": reference_images,
            "aspect_ratio": aspect_ratio
        }
        return await self._submit_and_poll("nano-banana-edit", payload)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# VISION ANALYSIS
# ============================================================================

async def ensure_url(image_path: str) -> str:
    """Validate that the input is a URL."""
    if not image_path.startswith(("http://", "https://")):
        raise ValueError(f"Invalid reference: '{image_path}'. References must be image URLs (starting with http:// or https://). Local files are not supported.")
    return image_path


class VisionAdapter:
    """
    Vision-capable adapter using GPT-5-Nano:
    - Accepts image URLs
    - Produces structured analysis + description
    """

    BASE_URL = "https://api.muapi.ai/api/v1"
    MODEL = "gpt-5-nano"

    def __init__(self, api_key: str):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("API key missing")

    async def analyze(
        self,
        prompt: str,
        image_url: str
    ) -> dict:
        """
        Given an image URL, produce structured analysis.
        Returns a dict: { summary, tags, objects, colors, suggestions }
        """
        # Ensure we have a URL
        image_url = await ensure_url(image_url)

        submit_url = f"{self.BASE_URL}/{self.MODEL}"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        payload = {
            "prompt": f"Analyze these images and return structured JSON: {prompt}",
            "image_url": image_url,
        }

        async with aiohttp.ClientSession() as session:
            # Submit
            logger.info(f"[VisionAdapter] Submitting analysis request for {image_url}")
            async with session.post(submit_url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    logger.error(f"[VisionAdapter] Submit failed: {resp.status}")
                    raise RuntimeError(f"MuAPI vision submit error {resp.status}: {await resp.text()}")
                data = await resp.json() 
                request_id = data["request_id"]
                logger.info(f"[VisionAdapter] Request submitted. ID: {request_id}")
    
            # Poll
            result_url = f"{self.BASE_URL}/predictions/{request_id}/result"
    
            while True:
                await asyncio.sleep(0.5)

                async with session.get(result_url, headers={"x-api-key": self.api_key}) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"MuAPI poll error {resp.status}: {await resp.text()}")

                    result = await resp.json()
                    status = result["status"]

                    if status == "completed":
                        logger.info(f"[VisionAdapter] Request {request_id} completed.")
                        output_text = result["outputs"][0]

                        # Try to parse JSON (if model outputs JSON)
                        try:
                            return json.loads(output_text)
                        except:
                            # If it's plain text, wrap it
                            return {"summary": output_text}

                    if status == "failed":
                        logger.info(f"[VisionAdapter] Request {request_id} failed.")
                        raise RuntimeError(f"MuAPI vision task failed: {result.get('error')}")

                    logger.debug(f"[VisionAdapter] Polling {request_id}: {status}...")


# ============================================================================
# DATA MODELS
# ============================================================================

class ReferenceImage(BaseModel):
    """Analyzed reference image"""
    url: str
    type: str  # "character", "environment", "prop", "lighting"
    description: str
    key_features: List[str]


class FramePlan(BaseModel):
    """Plan for a single frame in the sequence"""
    frame_number: int
    shot_type: str  # "wide", "medium", "close_up", "extreme_close_up"
    camera_angle: str  # "eye_level", "low_angle", "high_angle", "dutch_angle"
    description: str
    focus_elements: List[str]
    composition_notes: str
    duration_hint: float = 1.5  # seconds per frame
    background_id: str # Added this field


class BackgroundPlan(BaseModel):
    """Plan for a background/environment"""
    id: str  # e.g., "bg_1", "kitchen", "studio"
    description: str
    frames: List[int]  # List of frame numbers that use this background


class PopcornSequence(BaseModel):
    """Complete sequence plan"""
    prompt: str
    num_frames: int
    references: List[ReferenceImage]
    frames: List[FramePlan]
    backgrounds: List[BackgroundPlan] # Added this field
    style: str
    consistency_rules: str


# ============================================================================
# REFERENCE ANALYZER
# ============================================================================

class ReferenceAnalyzer:
    """Analyze reference images using vision AI"""
    
    def __init__(self, vision: VisionAdapter, llm: LLMClient):
        self.vision = vision
        self.llm = llm
    
    async def analyze_reference(self, image_url: str, index: int) -> ReferenceImage:
        """Analyze a single reference image"""
        logger.info(f"  Analyzing reference {index + 1}...")
        
        # Step 1: Vision analysis
        analysis_prompt = """Describe this image in detail:
- What type of subject is this? (character, environment, object, lighting setup)
- Key visual features (colors, textures, style, mood)
- Notable details for consistency (clothing, architecture, props)

Return JSON: {"type": "...", "description": "...", "key_features": [...]}"""
        
        vision_result = await self.vision.analyze(analysis_prompt, image_url)
        
        # Step 2: Structure the analysis
        ref_type = vision_result.get("type", "unknown")
        description = vision_result.get("description", vision_result.get("summary", ""))
        features = vision_result.get("key_features", [])
        
        # If features not provided, extract from description
        if not features and description:
            features = description.split(", ")[:5]
        
        return ReferenceImage(
            url=image_url,
            type=ref_type,
            description=description,
            key_features=features
        )


# ============================================================================
# SEQUENCE PLANNER
# ============================================================================

class SequencePlanner:
    """Plan shot sequence - adapts to ANY use case (storytelling, product, architecture, etc.)"""
    
    def __init__(self, llm: LLMClient):
        self.llm = llm
    
    async def plan_sequence(
        self,
        prompt: str,
        num_frames: int,
        references: List[ReferenceImage],
        style: str = "cinematic realistic"
    ) -> PopcornSequence:
        """Plan a coherent sequence of frames - adapts to prompt context"""
        logger.info(f"Planning {num_frames}-frame sequence...")
        
        # Build context from references
        ref_context = self._build_reference_context(references)
        
        # Create planning prompt - LET THE LLM DECIDE THE APPROACH
        planning_prompt = f"""You are a professional visual planner. Analyze the user's request and plan {num_frames} frames accordingly.

USER PROMPT: "{prompt}"

REFERENCE IMAGES AVAILABLE:
{ref_context}

STYLE: {style}

TASK: Plan {num_frames} frames that best fulfill the user's prompt.

CONTEXT DETECTION:
- If prompt is about storytelling/narrative → plan cinematic shots (wide, close-up, camera angles)
- If prompt is about product photography → plan product shots (front view, side view, top view, detail shots)
- If prompt is about architecture → plan architectural views (exterior, interior, details, context)
- If prompt is about fashion → plan fashion shots (full body, detail shots, poses)
- If prompt is about anything else → adapt intelligently

SHOT TYPE GUIDANCE:
- Storytelling: "wide_shot", "close_up", "medium_shot", "over_shoulder", etc.
- Product: "front_view", "side_view", "top_view", "45_degree_angle", "detail_shot", "lifestyle_shot"
- Architecture: "exterior_wide", "interior_view", "detail_element", "aerial_view"
- Fashion: "full_body", "upper_body", "detail_closeup", "editorial_pose"
- Generic: describe the view naturally

CAMERA ANGLE GUIDANCE:
- Storytelling: "eye_level", "low_angle", "high_angle", "dutch_angle"
- Product: "straight_on", "slightly_elevated", "45_degree", "overhead"
- Architecture: "street_level", "elevated", "birds_eye"
- Fashion: "eye_level", "low_angle", "high_fashion_angle"
- Generic: describe the angle naturally

Each frame should:
1. Use the reference images for consistency
2. Vary views/angles for visual interest
3. Maintain consistent lighting and style
4. Create a natural progression

BACKGROUND/ENVIRONMENT HANDLING:
- Analyze the prompt to determine needed backgrounds
- Product photography/static scenes → Usually 1 consistent background
- Storytelling with movement → May need multiple backgrounds
- Define the specific backgrounds needed for this sequence

Examples:
- Prompt: "product shots for e-commerce" → All frames: same white/studio background
- Prompt: "hero escapes building and runs to car" → Frame 1: building interior, Frame 2-3: street, Frame 4: car
- Prompt: "detective in crowded market" → Background: "Bustling market street with colorful stalls, awnings, cobblestone path, and atmospheric lighting" (Note: NO mention of detective)
- Prompt: "orange cup on table" → Background: "Empty wooden table surface with blurred kitchen background" (Note: NO mention of cup)

CRITICAL CONSISTENCY RULES:
- Subject/product/character must look IDENTICAL in every frame
- Lighting approach and color palette must match across all frames
- Style must be uniform ({style})
- Background consistency: decide based on prompt context

Return JSON:
{{
  "backgrounds": [
    {{
      "id": "bg_1",
      "description": "Detailed description of the SETTING ONLY. Do NOT mention the main character, product, or subject. Describe the environment as if the subject is not there.",
      "frames": [1, 2, 3, 4]
    }}
  ],
  "frames": [
    {{
      "frame_number": 1,
      "shot_type": "<appropriate shot type based on context>",
      "camera_angle": "<appropriate angle based on context>",
      "description": "Detailed description of what we see in this frame",
      "focus_elements": ["element1", "element2"],
      "composition_notes": "Technical composition details",
      "background_id": "bg_1"
    }},
    ...
  ],
  "consistency_rules": "Summary of what must stay consistent across all frames"
}}

IMPORTANT: 
1. Choose shot_type and camera_angle terminology that matches the context of the prompt.
2. Define backgrounds separately in the 'backgrounds' list.
3. Link each frame to a background_id."""

        response = await self.llm.call(
            system_prompt="You are an expert visual planner who adapts to any creative brief - from film to product photography to architecture to fashion and beyond.",
            user_prompt=planning_prompt,
            response_format=dict,
            temperature=0.4
        )
        
        # Parse response
        frames = []
        for f in response["frames"]:
            # Ensure background_id exists, default to first bg if missing
            if "background_id" not in f and response.get("backgrounds"):
                f["background_id"] = response["backgrounds"][0]["id"]
            frames.append(FramePlan(**f))
            
        backgrounds = [BackgroundPlan(**b) for b in response.get("backgrounds", [])]
        consistency_rules = response.get("consistency_rules", "Maintain visual consistency")
        
        return PopcornSequence(
            prompt=prompt,
            num_frames=num_frames,
            references=references,
            frames=frames,
            backgrounds=backgrounds,
            style=style,
            consistency_rules=consistency_rules
        )
    
    def _build_reference_context(self, references: List[ReferenceImage]) -> str:
        """Build text context from reference images"""
        lines = []
        for i, ref in enumerate(references):
            lines.append(f"Reference {i+1} ({ref.type}):")
            lines.append(f"  Description: {ref.description}")
            lines.append(f"  Key features: {', '.join(ref.key_features)}")
        return "\n".join(lines)


# ============================================================================
# BACKGROUND GENERATOR
# ============================================================================

class BackgroundGenerator:
    """Generate background reference images"""
    
    def __init__(self, image_gen: NanoBananaImageGenerator, output_dir: Path, style: str):
        self.image_gen = image_gen
        self.output_dir = output_dir / "backgrounds"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.style = style
        
    async def generate_backgrounds(self, sequence: PopcornSequence) -> Dict[str, Dict[str, str]]:
        """Generate all planned backgrounds. Returns dict of id -> {path: local_path, url: original_url}"""
        logger.info(f"Generating {len(sequence.backgrounds)} background(s)...")
        
        bg_data = {}
        
        for bg in sequence.backgrounds:
            logger.info(f"  Generating background '{bg.id}': {bg.description[:50]}...")
            
            # Build prompt - Clean environment description
            # We rely on the planner to have removed the subject from the description
            prompt = (
                f"{self.style} style. {bg.description}. "
                "background reference, location shot, environmental view, high quality, 4k"
            )
            
            # Generate
            bg_url = await self.image_gen.generate_image(
                prompt=prompt,
                aspect_ratio="16:9"
            )
            
            # Download
            bg_filename = f"{bg.id}.png"
            bg_path_local = self.output_dir / bg_filename
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(bg_url) as response:
                        if response.status == 200:
                            with open(bg_path_local, 'wb') as f:
                                while True:
                                    chunk = await response.content.read(1024)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                            bg_data[bg.id] = {"path": str(bg_path_local), "url": bg_url}
                            logger.info(f"    ✓ Saved: {bg_path_local.name}")
                        else:
                            logger.error(f"    ✗ Failed to download background {bg.id}")
                            bg_data[bg.id] = {"path": bg_url, "url": bg_url}
            except Exception as e:
                logger.error(f"    ✗ Download error for {bg.id}: {e}")
                bg_data[bg.id] = {"path": bg_url, "url": bg_url}
                
        return bg_data


# ============================================================================
# FRAME GENERATOR
# ============================================================================

class FrameGenerator:
    """Generate consistent frames using nano-banana-edit"""
    
    def __init__(self, image_gen: NanoBananaImageGenerator, output_dir: Path, style: str):
        self.image_gen = image_gen
        self.output_dir = output_dir / "frames"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.style = style
    
    async def generate_frames(
        self,
        sequence: PopcornSequence,
        bg_data: Dict[str, Dict[str, str]]
    ) -> List[str]:
        """Generate all frames using reference images for consistency"""
        logger.info(f"Generating {sequence.num_frames} frames...")
        
        # Collect user-provided reference URLs
        user_ref_urls = [ref.url for ref in sequence.references]
        
        # Track first frame details for consistency
        first_frame_details = None
        
        # Generate frames
        frame_paths = []
        for frame in sequence.frames:
            logger.info(f"  Frame {frame.frame_number}/{sequence.num_frames}: {frame.shot_type}")
            
            # Build frame prompt with detail consistency
            prompt = self._build_frame_prompt(frame, sequence, first_frame_details)
            
            # Extract details from first frame for future consistency
            if frame.frame_number == 1:
                first_frame_details = self._extract_detail_hints(frame)
            
            # Prepare references for this frame
            current_frame_refs = user_ref_urls.copy()
            current_bg_info = bg_data.get(frame.background_id)
            if current_bg_info and current_bg_info.get("url"):
                current_frame_refs.append(current_bg_info["url"])

            # Generate with references
            frame_url = await self.image_gen.generate_with_references(
                prompt=prompt,
                reference_images=current_frame_refs,
                aspect_ratio="16:9"
            )
            
            # Download frame
            frame_filename = f"frame_{frame.frame_number:02d}.png"
            frame_path_local = self.output_dir / frame_filename
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(frame_url) as response:
                        if response.status == 200:
                            with open(frame_path_local, 'wb') as f:
                                while True:
                                    chunk = await response.content.read(1024)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                            frame_paths.append(str(frame_path_local))
                            logger.info(f"    ✓ Saved: {frame_path_local.name}")
                        else:
                            frame_paths.append(frame_url)
            except Exception as e:
                logger.error(f"    ✗ Download error for frame {frame.frame_number}: {e}")
                frame_paths.append(frame_url)
        
        return frame_paths
    
    def _extract_detail_hints(self, frame: FramePlan) -> str:
        """Extract detail-level consistency hints from first frame description"""
        desc = frame.description.lower()
        hints = []
        
        # SUBJECT/CHARACTER DETAILS (accessories, props that should stay consistent)
        # Check for accessories/props mentioned
        if "glove" in desc:
            hints.append("wearing gloves")
        elif "bare hand" in desc or "no glove" in desc:
            hints.append("bare hands (no gloves)")
        
        if "watch" in desc:
            hints.append("wearing watch")
        
        if "glass" in desc and "wearing" in desc:
            hints.append("wearing glasses")
        elif "no glass" in desc:
            hints.append("no glasses")
        
        if "holding" in desc:
            # Extract what's being held
            for item in ["cup", "mug", "phone", "bag", "tool", "book", "pen", "bottle", "box"]:
                if item in desc:
                    hints.append(f"holding {item}")
        
        return ", ".join(hints) if hints else ""
    
    def _build_frame_prompt(self, frame: FramePlan, sequence: PopcornSequence, first_frame_details: Optional[str] = None) -> str:
        """Build detailed prompt for frame generation with detail consistency"""
        
        # Build base components
        prompt_parts = [
            f"{sequence.style} style",
            f"{frame.shot_type.replace('_', ' ')} from {frame.camera_angle.replace('_', ' ')}",
            frame.description,
        ]
        
        # Add detail consistency for frames 2+
        if first_frame_details and frame.frame_number > 1:
            prompt_parts.append(f"MAINTAIN EXACT DETAILS FROM FRAME 1: {first_frame_details}")
        
        prompt_parts.extend([
            frame.composition_notes,
            sequence.consistency_rules,
            "subject naturally integrated in scene with proper lighting",
            "match scene lighting and atmosphere",
            "blend seamlessly with environment",
            "professional storyboard frame",
            "consistent with reference images",
            "cinematic framing",
            "high quality"
        ])
        
        return ", ".join([p for p in prompt_parts if p])





# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

class PopcornGenerator:
    """Main orchestrator for Popcorn-style generation"""
    
    def __init__(self, muapi_key: str, output_dir: str, style: str = "cinematic realistic"):
        self.llm = LLMClient(muapi_key, model="gpt-5-mini")
        self.vision = VisionAdapter(muapi_key)
        self.image_gen = NanoBananaImageGenerator(muapi_key)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.style = style
        
        self.analyzer = ReferenceAnalyzer(self.vision, self.llm)
        self.planner = SequencePlanner(self.llm)
        self.bg_generator = BackgroundGenerator(self.image_gen, self.output_dir, style)
        self.generator = FrameGenerator(self.image_gen, self.output_dir, style)
    
    async def generate(
        self,
        prompt: str,
        reference_urls: List[str],
        num_frames: int = 6,
        manual_shots: Optional[List[str]] = None
    ) -> Dict:
        """Generate a Popcorn-style sequence"""
        logger.info(f"🍿 Popcorn Generator Starting...")
        if manual_shots:
            logger.info(f"  Mode: MANUAL ({len(manual_shots)} shots)")
        else:
            logger.info(f"  Mode: AUTO (Prompt: {prompt})")
            logger.info(f"  Frames: {num_frames}")
            
        logger.info(f"  References: {len(reference_urls)}")
        logger.info(f"  Style: {self.style}")
        
        # Step 1: Analyze references
        logger.info("\n📸 Step 1: Analyzing reference images...")
        references = []
        for i, url in enumerate(reference_urls):
            ref = await self.analyzer.analyze_reference(url, i)
            references.append(ref)
            logger.info(f"    ✓ {ref.type}: {ref.description[:60]}...")
        
        # Step 2: Plan sequence
        logger.info("\n🎬 Step 2: Planning shot sequence...")
        if manual_shots:
            sequence = await self.planner.plan_manual_sequence(manual_shots, references, self.style)
        else:
            sequence = await self.planner.plan_sequence(prompt, num_frames, references, self.style)
            
        logger.info(f"    ✓ Planned {len(sequence.frames)} frames")
        logger.info(f"    Consistency: {sequence.consistency_rules}")
        
        # Step 3: Generate backgrounds
        bg_data = {}
        logger.info("\n🏙️  Step 3: Generating backgrounds...")
        bg_data = await self.bg_generator.generate_backgrounds(sequence)
        logger.info(f"    ✓ Generated {len(bg_data)} backgrounds")

        # Step 4: Generate frames
        logger.info("\n🖼️  Step 4: Generating frames...")
        frame_paths = await self.generator.generate_frames(sequence, bg_data)
            
        logger.info(f"    ✓ Generated {len(frame_paths)} frames")
        
        # Step 5: Save sequence data
        sequence_file = self.output_dir / "sequence.json"
        with open(sequence_file, 'w') as f:
            json.dump({
                "prompt": prompt if not manual_shots else "Manual Mode",
                "manual_shots": manual_shots,
                "num_frames": len(sequence.frames),
                "references": [ref.model_dump() for ref in references],
                "frames": [frame.model_dump() for frame in sequence.frames],
                "backgrounds": [bg.model_dump() for bg in sequence.backgrounds],
                "frame_paths": frame_paths,
                "bg_paths": bg_data,
                "style": self.style,
                "consistency_rules": sequence.consistency_rules
            }, f, indent=2)
        
        logger.info(f"\n✅ Sequence complete!")
        logger.info(f"   Frames: {self.output_dir}/frames/")
        logger.info(f"   Data: {sequence_file}")
        
        return {
            "sequence": sequence,
            "frame_paths": frame_paths,
            "output_dir": str(self.output_dir)
        }


# ============================================================================
# CLI
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Popcorn Storyboard Generator")
    
    parser.add_argument(
        "--prompt",
        help="Text prompt describing the scene/action (Required for Auto Mode)"
    )
    
    parser.add_argument(
        "--manual_shots",
        nargs="+",
        help="List of manual shot descriptions (Enables Manual Mode)"
    )
    
    parser.add_argument(
        "--references",
        nargs="+",
        default=[],
        help="Reference image URLs (up to 4 recommended)"
    )
    
    parser.add_argument(
        "--frames",
        type=int,
        default=6,
        help="Number of frames to generate (Auto Mode only)"
    )
    
    parser.add_argument(
        "--style",
        default="cinematic realistic",
        help="Visual style (e.g., 'anime', 'watercolor', 'noir film')"
    )
    

    
    parser.add_argument(
        "--output",
        default="popcorn_output",
        help="Output directory"
    )
    

    
    args = parser.parse_args()
    
    # Validate
    if not args.prompt and not args.manual_shots:
        print("Error: Must provide either --prompt OR --manual_shots")
        sys.exit(1)
        
    if args.manual_shots and len(args.manual_shots) < 1:
        print("Error: Manual mode requires at least 1 shot description")
        sys.exit(1)
    
    if args.frames < 2 or args.frames > 12:
        if not args.manual_shots: # Only enforce for auto mode
            print("Error: Frames must be between 2-12")
            sys.exit(1)
    
    if len(args.references) > 4:
        print("Warning: More than 4 references may reduce consistency")
    
    # Get API keys
    muapi_key = MUAPIAPP_API_KEY
    
    if not muapi_key:
        print("Error: MUAPIAPP_API_KEY missing in secrets.py")
        sys.exit(1)
    
    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output) / f"sequence_{timestamp}"
    
    # Generate
    generator = PopcornGenerator(muapi_key, str(output_dir), args.style)
    
    try:
        result = await generator.generate(
            prompt=args.prompt if args.prompt else "Manual Mode",
            reference_urls=args.references,
            num_frames=args.frames if not args.manual_shots else len(args.manual_shots),
            manual_shots=args.manual_shots
        )
        print(f"\n🎉 Success! Frames saved to: {result['output_dir']}")
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
