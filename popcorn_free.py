#!/usr/bin/env python3
"""
FREE Popcorn Storyboard Generator
Uses Groq AI + Pollinations.AI (100% FREE)

Usage:
    python popcorn_free.py --prompt "detective investigating a crime scene" --frames 6 --style "cinematic noir"
    python popcorn_free.py --manual_shots "wide shot of detective" "close up of evidence" --style "noir"
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
import urllib.parse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GroqLLMClient:
    """LLM client using Groq API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"
    
    async def call(self, system_prompt: str, user_prompt: str, response_format: type = None, temperature: float = 0.7) -> dict:
        """Call Groq API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Groq API Error: {response.status}, {text}")
                
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                
                if response_format == dict:
                    try:
                        clean_text = content.strip()
                        if clean_text.startswith("```json"):
                            clean_text = clean_text[7:]
                        if clean_text.startswith("```"):
                            clean_text = clean_text[3:]
                        if clean_text.endswith("```"):
                            clean_text = clean_text[:-3]
                        
                        # Find JSON
                        start = clean_text.find("{")
                        end = clean_text.rfind("}") + 1
                        if start != -1 and end > start:
                            clean_text = clean_text[start:end]
                        
                        return json.loads(clean_text)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON from LLM response")
                        return {"raw_output": content}
                
                return content


class PollinationsImageGen:
    """Image generation using Pollinations.AI"""
    
    def __init__(self):
        self.base_url = "https://image.pollinations.ai/prompt"
    
    async def generate_image(self, prompt: str, aspect_ratio: str = "16:9") -> str:
        """Generate image from text"""
        encoded_prompt = urllib.parse.quote(prompt)
        width, height = (1024, 576) if aspect_ratio == "16:9" else (768, 768)
        image_url = f"{self.base_url}/{encoded_prompt}?width={width}&height={height}&nologo=true&enhance=true"
        return image_url
    
    async def generate_with_references(self, prompt: str, reference_images: List[str], aspect_ratio: str = "16:9") -> str:
        """Generate with references (simplified - just use prompt)"""
        # Pollinations doesn't support reference images, so we enhance the prompt
        enhanced_prompt = f"{prompt}, maintaining consistent style and characters"
        return await self.generate_image(enhanced_prompt, aspect_ratio)


class ReferenceImage(BaseModel):
    """Analyzed reference image"""
    url: str
    type: str
    description: str
    key_features: List[str]


class FramePlan(BaseModel):
    """Plan for a single frame"""
    frame_number: int
    shot_type: str
    camera_angle: str
    description: str
    focus_elements: List[str]
    composition_notes: str
    duration_hint: float = 1.5
    background_id: str


class BackgroundPlan(BaseModel):
    """Plan for a background"""
    id: str
    description: str
    frames: List[int]


class PopcornSequence(BaseModel):
    """Complete sequence plan"""
    prompt: str
    num_frames: int
    references: List[ReferenceImage]
    frames: List[FramePlan]
    backgrounds: List[BackgroundPlan]
    style: str
    consistency_rules: str


class ReferenceAnalyzer:
    """Analyze reference images using Groq vision (simulated)"""
    
    def __init__(self, llm: GroqLLMClient):
        self.llm = llm
    
    async def analyze_reference(self, image_url: str, index: int) -> ReferenceImage:
        """Analyze a reference image"""
        logger.info(f"  Analyzing reference {index + 1}...")
        
        # Since Groq doesn't have vision, we do text-based analysis
        analysis_prompt = f"""Analyze this reference image URL and infer its content: {image_url}

Based on the URL and common patterns, describe:
- Type: character, environment, object, or lighting
- Description: What this likely shows
- Key features: 3-5 notable visual elements

Return JSON: {{"type": "...", "description": "...", "key_features": [...]}}"""
        
        try:
            result = await self.llm.call("You are an image analyst.", analysis_prompt, response_format=dict, temperature=0.5)
            
            return ReferenceImage(
                url=image_url,
                type=result.get("type", "unknown"),
                description=result.get("description", "Reference image"),
                key_features=result.get("key_features", ["visual reference"])
            )
        except:
            # Fallback
            return ReferenceImage(
                url=image_url,
                type="reference",
                description="Reference image for consistency",
                key_features=["visual style", "character design", "environment"]
            )


class SequencePlanner:
    """Plan shot sequence using Groq AI"""
    
    def __init__(self, llm: GroqLLMClient):
        self.llm = llm
    
    async def plan_sequence(
        self,
        prompt: str,
        num_frames: int,
        references: List[ReferenceImage],
        style: str = "cinematic"
    ) -> PopcornSequence:
        """Plan a coherent sequence"""
        logger.info(f"Planning {num_frames}-frame sequence...")
        
        ref_context = self._build_reference_context(references)
        
        planning_prompt = f"""You are a professional visual planner. Plan {num_frames} frames for: "{prompt}"

REFERENCE IMAGES:
{ref_context}

STYLE: {style}

Plan {num_frames} frames with varied shots (wide, medium, close-up, etc.) and angles.

BACKGROUND HANDLING:
- Analyze if scene needs 1 background (static) or multiple (movement)
- Describe backgrounds WITHOUT mentioning the main subject
- Example: "Empty wooden table" not "Cup on table"

Return ONLY valid JSON:
{{
  "backgrounds": [
    {{
      "id": "bg_1",
      "description": "Setting description WITHOUT subject",
      "frames": [1, 2, 3, 4]
    }}
  ],
  "frames": [
    {{
      "frame_number": 1,
      "shot_type": "wide shot",
      "camera_angle": "eye level",
      "description": "Detailed frame description",
      "focus_elements": ["element1", "element2"],
      "composition_notes": "Composition details",
      "background_id": "bg_1"
    }}
  ],
  "consistency_rules": "What must stay consistent"
}}"""

        response = await self.llm.call(
            system_prompt="You are an expert cinematographer and visual planner.",
            user_prompt=planning_prompt,
            response_format=dict,
            temperature=0.4
        )
        
        # Parse response
        frames = []
        for f in response.get("frames", []):
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
    
    async def plan_manual_sequence(
        self,
        manual_shots: List[str],
        references: List[ReferenceImage],
        style: str
    ) -> PopcornSequence:
        """Plan sequence from manual shot descriptions"""
        logger.info(f"Planning {len(manual_shots)} manual shots...")
        
        frames = []
        for i, shot_desc in enumerate(manual_shots):
            frames.append(FramePlan(
                frame_number=i + 1,
                shot_type="custom",
                camera_angle="as described",
                description=shot_desc,
                focus_elements=[shot_desc.split()[0]],
                composition_notes=f"Manual shot: {shot_desc}",
                background_id="bg_1"
            ))
        
        backgrounds = [BackgroundPlan(
            id="bg_1",
            description="Scene environment",
            frames=list(range(1, len(manual_shots) + 1))
        )]
        
        return PopcornSequence(
            prompt="Manual Mode",
            num_frames=len(manual_shots),
            references=references,
            frames=frames,
            backgrounds=backgrounds,
            style=style,
            consistency_rules="Maintain consistent style across all frames"
        )
    
    def _build_reference_context(self, references: List[ReferenceImage]) -> str:
        """Build text context from references"""
        if not references:
            return "No reference images provided"
        
        lines = []
        for i, ref in enumerate(references):
            lines.append(f"Reference {i+1} ({ref.type}):")
            lines.append(f"  Description: {ref.description}")
            lines.append(f"  Key features: {', '.join(ref.key_features)}")
        return "\n".join(lines)


class BackgroundGenerator:
    """Generate background images"""
    
    def __init__(self, image_gen: PollinationsImageGen, output_dir: Path, style: str):
        self.image_gen = image_gen
        self.output_dir = output_dir / "backgrounds"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.style = style
    
    async def generate_backgrounds(self, sequence: PopcornSequence) -> Dict[str, Dict[str, str]]:
        """Generate all backgrounds"""
        logger.info(f"Generating {len(sequence.backgrounds)} background(s)...")
        
        bg_data = {}
        
        for bg in sequence.backgrounds:
            logger.info(f"  Generating background '{bg.id}'...")
            
            prompt = f"{self.style} style. {bg.description}. background, environment, high quality, 4k"
            
            bg_url = await self.image_gen.generate_image(prompt, "16:9")
            
            # Download
            bg_filename = f"{bg.id}.png"
            bg_path_local = self.output_dir / bg_filename
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(bg_url) as response:
                        if response.status == 200:
                            with open(bg_path_local, 'wb') as f:
                                f.write(await response.read())
                            bg_data[bg.id] = {"path": str(bg_path_local), "url": bg_url}
                            logger.info(f"    ✓ Saved: {bg_path_local.name}")
                        else:
                            bg_data[bg.id] = {"path": bg_url, "url": bg_url}
            except Exception as e:
                logger.error(f"    ✗ Download error: {e}")
                bg_data[bg.id] = {"path": bg_url, "url": bg_url}
            
            await asyncio.sleep(1)
        
        return bg_data


class FrameGenerator:
    """Generate frames"""
    
    def __init__(self, image_gen: PollinationsImageGen, output_dir: Path, style: str):
        self.image_gen = image_gen
        self.output_dir = output_dir / "frames"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.style = style
    
    async def generate_frames(
        self,
        sequence: PopcornSequence,
        bg_data: Dict[str, Dict[str, str]]
    ) -> List[str]:
        """Generate all frames"""
        logger.info(f"Generating {sequence.num_frames} frames...")
        
        user_ref_urls = [ref.url for ref in sequence.references]
        first_frame_details = None
        frame_paths = []
        
        for frame in sequence.frames:
            logger.info(f"  Frame {frame.frame_number}/{sequence.num_frames}: {frame.shot_type}")
            
            prompt = self._build_frame_prompt(frame, sequence, first_frame_details)
            
            if frame.frame_number == 1:
                first_frame_details = self._extract_detail_hints(frame)
            
            # Generate
            current_refs = user_ref_urls.copy()
            frame_url = await self.image_gen.generate_with_references(
                prompt=prompt,
                reference_images=current_refs,
                aspect_ratio="16:9"
            )
            
            # Download
            frame_filename = f"frame_{frame.frame_number:02d}.png"
            frame_path_local = self.output_dir / frame_filename
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(frame_url) as response:
                        if response.status == 200:
                            with open(frame_path_local, 'wb') as f:
                                f.write(await response.read())
                            frame_paths.append(str(frame_path_local))
                            logger.info(f"    ✓ Saved: {frame_path_local.name}")
                        else:
                            frame_paths.append(frame_url)
            except Exception as e:
                logger.error(f"    ✗ Download error: {e}")
                frame_paths.append(frame_url)
            
            await asyncio.sleep(1)
        
        return frame_paths
    
    def _extract_detail_hints(self, frame: FramePlan) -> str:
        """Extract consistency hints"""
        desc = frame.description.lower()
        hints = []
        
        if "glove" in desc:
            hints.append("wearing gloves")
        if "watch" in desc:
            hints.append("wearing watch")
        if "glass" in desc and "wearing" in desc:
            hints.append("wearing glasses")
        
        return ", ".join(hints) if hints else ""
    
    def _build_frame_prompt(self, frame: FramePlan, sequence: PopcornSequence, first_frame_details: Optional[str] = None) -> str:
        """Build frame prompt"""
        prompt_parts = [
            f"{sequence.style} style",
            f"{frame.shot_type.replace('_', ' ')} from {frame.camera_angle.replace('_', ' ')}",
            frame.description,
        ]
        
        if first_frame_details and frame.frame_number > 1:
            prompt_parts.append(f"MAINTAIN: {first_frame_details}")
        
        prompt_parts.extend([
            frame.composition_notes,
            sequence.consistency_rules,
            "professional cinematography",
            "high quality, 4k"
        ])
        
        return ", ".join([p for p in prompt_parts if p])


class FreePopcornGenerator:
    """Popcorn generator using free APIs"""
    
    def __init__(self, groq_key: str, output_dir: str, style: str = "cinematic"):
        self.llm = GroqLLMClient(groq_key)
        self.image_gen = PollinationsImageGen()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.style = style
        
        self.analyzer = ReferenceAnalyzer(self.llm)
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
        """Generate complete sequence"""
        logger.info(f"🍿 FREE Popcorn Generator")
        logger.info(f"  AI: Groq")
        logger.info(f"  Images: Pollinations.AI")
        
        if manual_shots:
            logger.info(f"  Mode: MANUAL ({len(manual_shots)} shots)")
        else:
            logger.info(f"  Mode: AUTO")
            logger.info(f"  Prompt: {prompt}")
            logger.info(f"  Frames: {num_frames}")
        
        logger.info(f"  References: {len(reference_urls)}")
        logger.info(f"  Style: {self.style}")
        
        # Step 1: Analyze references
        logger.info("\n📸 Step 1: Analyzing references...")
        references = []
        for i, url in enumerate(reference_urls):
            ref = await self.analyzer.analyze_reference(url, i)
            references.append(ref)
            logger.info(f"    ✓ {ref.type}: {ref.description[:50]}...")
        
        # Step 2: Plan sequence
        logger.info("\n🎬 Step 2: Planning sequence...")
        if manual_shots:
            sequence = await self.planner.plan_manual_sequence(manual_shots, references, self.style)
        else:
            sequence = await self.planner.plan_sequence(prompt, num_frames, references, self.style)
        
        logger.info(f"    ✓ Planned {len(sequence.frames)} frames")
        
        # Step 3: Generate backgrounds
        logger.info("\n🏙️  Step 3: Generating backgrounds...")
        bg_data = await self.bg_generator.generate_backgrounds(sequence)
        logger.info(f"    ✓ Generated {len(bg_data)} backgrounds")
        
        # Step 4: Generate frames
        logger.info("\n🖼️  Step 4: Generating frames...")
        frame_paths = await self.generator.generate_frames(sequence, bg_data)
        logger.info(f"    ✓ Generated {len(frame_paths)} frames")
        
        # Step 5: Save metadata
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
                "consistency_rules": sequence.consistency_rules,
                "generator": "FREE (Groq + Pollinations.AI)"
            }, f, indent=2)
        
        logger.info(f"\n✅ Complete!")
        logger.info(f"   Output: {self.output_dir}")
        
        return {
            "sequence": sequence,
            "frame_paths": frame_paths,
            "output_dir": str(self.output_dir)
        }


async def main():
    parser = argparse.ArgumentParser(description="FREE Popcorn Storyboard Generator")
    
    parser.add_argument("--prompt", help="Scene description (Auto Mode)")
    parser.add_argument("--manual_shots", nargs="+", help="Manual shot descriptions")
    parser.add_argument("--references", nargs="+", default=[], help="Reference image URLs")
    parser.add_argument("--frames", type=int, default=6, help="Number of frames")
    parser.add_argument("--style", default="cinematic", help="Visual style")
    parser.add_argument("--output", default="popcorn_output_free", help="Output directory")
    
    args = parser.parse_args()
    
    # Validate
    if not args.prompt and not args.manual_shots:
        print("Error: Provide --prompt OR --manual_shots")
        sys.exit(1)
    
    if args.frames < 2 or args.frames > 12:
        if not args.manual_shots:
            print("Error: Frames must be 2-12")
            sys.exit(1)
    
    # Get Groq key
    try:
        from secrets import GROQ_API_KEY
        groq_key = GROQ_API_KEY
    except:
        print("\n❌ Error: GROQ_API_KEY not found in secrets.py")
        print("Get FREE key at: https://console.groq.com/keys")
        sys.exit(1)
    
    if not groq_key or groq_key == "your-groq-key-here":
        print("\n❌ Add your Groq API key to secrets.py")
        print("Get it FREE at: https://console.groq.com/keys")
        sys.exit(1)
    
    # Create output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output) / f"sequence_{timestamp}"
    
    # Generate
    generator = FreePopcornGenerator(groq_key, str(output_dir), args.style)
    
    try:
        result = await generator.generate(
            prompt=args.prompt if args.prompt else "Manual Mode",
            reference_urls=args.references,
            num_frames=args.frames if not args.manual_shots else len(args.manual_shots),
            manual_shots=args.manual_shots
        )
        print(f"\n🎉 Success! Output: {result['output_dir']}")
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
