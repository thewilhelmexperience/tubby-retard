#!/usr/bin/env python3
"""
TR Comic Artwork Generator - MidAPI.ai Edition (Fixed)
Generates consistent comic panels using Midjourney via MidAPI.ai API
Correct API endpoints and parameters
"""

import os
import re
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import requests

# Default settings
DEFAULT_VERSION = "7"
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_SPEED = "fast"  # relaxed, fast, turbo


@dataclass
class ComicPanel:
    number: int
    title: str
    scene: str
    description: str
    simplified_prompt: str


@dataclass
class ComicScript:
    title: str
    slug: str
    location: str
    panels: List[ComicPanel]
    caption: str = ""


class MidAPIGenerator:
    def __init__(self, api_key: Optional[str] = None, 
                 tr_reference_url: Optional[str] = None,
                 output_dir: str = "comics/generated"):
        """Initialize MidAPI.ai generator."""
        self.api_key = api_key or os.getenv("MIDAPI_KEY")
        self.tr_reference_url = tr_reference_url or os.getenv("TR_REFERENCE_URL")
        self.base_url = "https://api.midapi.ai/api/v1/mj"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.api_key:
            raise ValueError("MidAPI key required. Set MIDAPI_KEY env var.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def parse_script_file(self, script_path: str) -> ComicScript:
        """Parse a comic script markdown file."""
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Extract title
        title_match = re.search(r'\*\*Title:\*\* (.+)', content)
        title = title_match.group(1) if title_match else "Untitled"
        
        # Extract slug
        slug_match = re.search(r'\*\*Slug:\*\* (.+)', content)
        slug = slug_match.group(1) if slug_match else self._slugify(title)
        
        # Extract location
        location_match = re.search(r'\*\*Location:\*\* (.+)', content)
        location = location_match.group(1) if location_match else "Unknown"
        
        # Parse panels
        panels = []
        panel_sections = re.split(r'### Panel \d+:', content)[1:]
        
        for i, section in enumerate(panel_sections, 1):
            panel = self._parse_panel(i, section)
            if panel:
                panels.append(panel)
        
        return ComicScript(title=title, slug=slug, location=location, panels=panels)
    
    def _parse_panel(self, number: int, section: str) -> Optional[ComicPanel]:
        """Parse a single panel section."""
        lines = section.strip().split('\n')
        panel_title = lines[0].strip() if lines else f"Panel {number}"
        
        # Extract scene
        scene_match = re.search(r'\*\*Scene:\*\* (.+?)(?=\*\*|$)', section, re.DOTALL)
        scene = scene_match.group(1).strip() if scene_match else ""
        
        # Extract caption
        caption_match = re.search(r'\*\*Caption:\*\* (.+?)(?=\*\*|$)', section, re.DOTALL)
        caption = caption_match.group(1).strip() if caption_match else ""
        
        if not scene:
            return None
        
        simplified = self._simplify_prompt(scene, caption)
        
        return ComicPanel(
            number=number,
            title=panel_title,
            scene=scene,
            description=caption,
            simplified_prompt=simplified
        )
    
    def _build_panel_prompt(self, panel: ComicPanel, comic_title: str) -> str:
        """Build specific prompt for each panel to match comic-003 style."""
        
        # TR character description - matching original comic style
        tr_character = """cartoon style TR: chubby exaggerated proportions, big round belly, simple cartoon face with dots for eyes, wide expressive mouth, white captain's hat with gold anchor emblem, bright blue Hawaiian shirt with big orange hibiscus flowers, khaki shorts, flip flops, holding cigar, bold black outlines, flat bright colors, simple shading, Sunday comics style"""
        
        # Panel-specific scenes with humor
        panel_prompts = {
            1: f"Professional yacht captain at helm holding radio microphone looking worried and confused, 80-foot yacht approaching tropical harbor entrance with palm trees, bright blue Caribbean water, sunny day, TR not visible yet, {tr_character}",
            
            2: f"TR grabbing radio from captain's hand, TR face bright red shouting angry with veins popping, mouth wide open yelling, captain looking shocked and annoyed in background, yacht bridge interior with controls and windows, dramatic action, {tr_character}",
            
            3: f"TR standing at yacht bow with arms crossed looking smug and self-important, big confident grin, captain at helm behind him looking worried and anxious, yacht entering tropical marina, palm trees and docks visible, {tr_character}",
            
            4: f"TR's face frozen in shock and embarrassment, eyes wide, mouth agape, behind him THREE ENORMOUS mega yachts 150+ feet long docked in marina, tiny 80-foot boat in foreground, size contrast visual gag, crew in uniforms on mega yachts, {tr_character}"
        }
        
        return panel_prompts.get(panel.number, f"{panel.simplified_prompt}, {tr_character}")
    
    def generate_panel(self, panel: ComicPanel, comic_title: str,
                      version: str = DEFAULT_VERSION,
                      speed: str = DEFAULT_SPEED,
                      max_retries: int = 3) -> Optional[str]:
        """Generate a single panel using MidAPI.ai."""
        
        # Build specific prompt for this panel
        prompt = self._build_panel_prompt(panel, comic_title)
        
        print(f"  Panel {panel.number} prompt: {prompt[:120]}...")
        
        payload = {
            "taskType": "mj_txt2img",
            "prompt": prompt,
            "speed": speed,
            "aspectRatio": DEFAULT_ASPECT_RATIO,
            "version": version
        }
        
        # Add character reference if available
        if self.tr_reference_url:
            payload["cref"] = self.tr_reference_url
            print(f"  Using character reference: {self.tr_reference_url[:50]}...")
        
        for attempt in range(max_retries):
            try:
                print(f"  Submitting task... (attempt {attempt + 1}/{max_retries})")
                
                # Submit generation task
                response = requests.post(
                    f"{self.base_url}/generate",
                    headers=self.headers,
                    json=payload,
                    timeout=60
                )
                
                result = response.json()
                
                if result.get("code") != 200:
                    print(f"  API Error: {result.get('msg', 'Unknown error')}")
                    if attempt < max_retries - 1:
                        time.sleep(5)
                        continue
                    return None
                
                task_id = result["data"]["taskId"]
                print(f"  Task started: {task_id}")
                
                # Wait for completion
                image_url = self._wait_for_completion(task_id)
                if image_url:
                    return image_url
                    
            except Exception as e:
                print(f"  Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return None
        
        return None
    
    def _wait_for_completion(self, task_id: str, max_wait: int = 300) -> Optional[str]:
        """Poll for task completion."""
        start_time = time.time()
        poll_interval = 10  # Check every 10 seconds initially
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.base_url}/record-info?taskId={task_id}",
                    headers=self.headers,
                    timeout=30
                )
                
                result = response.json()
                
                if result.get("code") != 200:
                    print(f"  Status check error: {result.get('msg')}")
                    time.sleep(poll_interval)
                    continue
                
                data = result["data"]
                success_flag = data.get("successFlag", 0)
                
                if success_flag == 0:
                    print(f"  Generating... ({int(time.time() - start_time)}s)")
                elif success_flag == 1:
                    # Success - get image URLs
                    result_info = data.get("resultInfoJson", {})
                    urls = result_info.get("resultUrls", [])
                    if urls:
                        # Return first image (you can upscale later if needed)
                        return urls[0].get("resultUrl")
                    return None
                elif success_flag in [2, 3]:
                    # Failed
                    error_msg = data.get("errorMessage", "Generation failed")
                    print(f"  Generation failed: {error_msg}")
                    return None
                
                time.sleep(poll_interval)
                
            except Exception as e:
                print(f"  Poll error: {e}")
                time.sleep(poll_interval)
        
        print("  Timeout waiting for generation")
        return None
    
    def download_image(self, url: str, filepath: Path) -> bool:
        """Download image from URL to local file."""
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            print(f"  Download error: {e}")
            return False
    
    def generate_comic(self, script_path: str, version: str = DEFAULT_VERSION,
                      speed: str = DEFAULT_SPEED,
                      skip_existing: bool = True) -> Dict:
        """Generate all panels for a comic script."""
        print(f"\n🎨 Processing: {script_path}")
        
        script = self.parse_script_file(script_path)
        print(f"  Title: {script.title}")
        print(f"  Slug: {script.slug}")
        print(f"  Panels: {len(script.panels)}")
        
        results = {
            "title": script.title,
            "slug": script.slug,
            "panels": [],
            "status": "success"
        }
        
        for panel in script.panels:
            print(f"\n  Panel {panel.number}: {panel.title}")
            
            # Check if already exists
            output_file = self.output_dir / f"comic-{script.slug}-panel{panel.number}.png"
            if skip_existing and output_file.exists():
                print(f"    ⏭️  Skipping (already exists)")
                results["panels"].append({
                    "number": panel.number,
                    "file": str(output_file),
                    "status": "skipped"
                })
                continue
            
            # Generate image
            image_url = self.generate_panel(panel, script.title, version, speed)
            
            if image_url:
                # Download and save
                if self.download_image(image_url, output_file):
                    print(f"    ✅ Saved: {output_file}")
                    results["panels"].append({
                        "number": panel.number,
                        "file": str(output_file),
                        "url": image_url,
                        "status": "generated"
                    })
                else:
                    print(f"    ⚠️  Generated but failed to download")
                    results["panels"].append({
                        "number": panel.number,
                        "file": None,
                        "url": image_url,
                        "status": "download_failed"
                    })
            else:
                print(f"    ❌ Failed to generate")
                results["panels"].append({
                    "number": panel.number,
                    "file": None,
                    "status": "failed"
                })
                results["status"] = "partial"
        
        return results
    
    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to URL-safe slug."""
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        text = text.strip('-')
        return text[:50]


def main():
    parser = argparse.ArgumentParser(description="Generate TR comics with MidAPI.ai")
    parser.add_argument("script", nargs="?", help="Path to comic script .md file")
    parser.add_argument("--batch", action="store_true", help="Generate all draft scripts")
    parser.add_argument("--scripts-dir", default="scripts", help="Directory containing scripts")
    parser.add_argument("--output", default="comics/generated", help="Output directory")
    parser.add_argument("--ref-url", help="TR character reference image URL")
    parser.add_argument("--version", default="7", help="Midjourney model version (6, 6.1, 7)")
    parser.add_argument("--speed", default="fast", choices=["relaxed", "fast", "turbo"],
                       help="Generation speed (affects cost)")
    parser.add_argument("--regenerate", action="store_true", help="Force regenerate existing panels")
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv("MIDAPI_KEY"):
        print("❌ Error: MIDAPI_KEY environment variable required")
        print("   Get your key at: https://midapi.ai")
        print("   Then run: export MIDAPI_KEY='your-key-here'")
        return
    
    # Initialize generator
    try:
        generator = MidAPIGenerator(
            tr_reference_url=args.ref_url,
            output_dir=args.output
        )
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    if args.batch:
        scripts_path = Path(args.scripts_dir)
        script_files = list(scripts_path.glob("comic-draft-*.md"))
        
        if not script_files:
            print(f"No scripts found in {args.scripts_dir}")
            return
        
        print(f"\n🚀 Batch generating {len(script_files)} comics...")
        
        for script_file in script_files:
            results = generator.generate_comic(
                str(script_file),
                version=args.version,
                speed=args.speed,
                skip_existing=not args.regenerate
            )
            print(f"\n  Results: {json.dumps(results, indent=2)}")
    
    elif args.script:
        results = generator.generate_comic(
            args.script,
            version=args.version,
            speed=args.speed,
            skip_existing=not args.regenerate
        )
        print(f"\n✅ Done!")
        print(f"   Generated: {sum(1 for p in results['panels'] if p['status'] == 'generated')}")
        print(f"   Failed: {sum(1 for p in results['panels'] if p['status'] == 'failed')}")
        print(f"   Output: {generator.output_dir.absolute()}")
    
    else:
        parser.print_help()
        print("\n💡 Examples:")
        print("  export MIDAPI_KEY='your-key'")
        print("  export TR_REFERENCE_URL='https://your-tr-image.png'")
        print("  python tr_midapi_generator.py scripts/comic-draft-biggest-boat-in-the-harbor.md")


if __name__ == "__main__":
    main()
