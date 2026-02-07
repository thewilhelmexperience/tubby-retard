#!/usr/bin/env python3
"""
TR Comic Artwork Generator - MidAPI.ai Edition
Generates consistent comic panels using Midjourney via MidAPI.ai API
Uses --oref (Omni Reference) for TR character consistency
"""

import os
import re
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import requests

# Default settings
DEFAULT_MODEL = "midjourney-v7"
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_MODE = "fast"  # relaxed, fast, turbo


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
        self.base_url = "https://api.midapi.ai/v1"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.api_key:
            raise ValueError("MidAPI key required. Set MIDAPI_KEY env var or pass to constructor.")
    
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
        # Extract panel title (usually first line)
        lines = section.strip().split('\n')
        panel_title = lines[0].strip() if lines else f"Panel {number}"
        
        # Extract scene
        scene_match = re.search(r'\*\*Scene:\*\* (.+?)(?=\*\*|$)', section, re.DOTALL)
        scene = scene_match.group(1).strip() if scene_match else ""
        
        # Extract caption (for context)
        caption_match = re.search(r'\*\*Caption:\*\* (.+?)(?=\*\*|$)', section, re.DOTALL)
        caption = caption_match.group(1).strip() if caption_match else ""
        
        if not scene:
            return None
        
        # Create simplified prompt for Midjourney
        simplified = self._simplify_prompt(scene, caption)
        
        return ComicPanel(
            number=number,
            title=panel_title,
            scene=scene,
            description=caption,
            simplified_prompt=simplified
        )
    
    def _simplify_prompt(self, scene: str, caption: str) -> str:
        """Convert detailed description to Midjourney-friendly prompt."""
        # Remove narrative elements, keep visual description
        # Limit to one clear sentence
        
        # Clean up the scene
        scene = scene.replace('\n', ' ').strip()
        
        # Take first sentence or first 200 chars
        if '.' in scene:
            scene = scene.split('.')[0] + '.'
        
        if len(scene) > 200:
            scene = scene[:200] + '...'
        
        return scene
    
    def generate_panel(self, panel: ComicPanel, comic_title: str,
                      model: str = DEFAULT_MODEL,
                      mode: str = DEFAULT_MODE,
                      max_retries: int = 3) -> Optional[str]:
        """Generate a single panel using MidAPI.ai."""
        
        # Build the prompt - keep it simple and visual
        prompt = f"""{panel.simplified_prompt}

TR character: chubby middle-aged man, white captain's hat with gold anchor emblem, blue Hawaiian shirt with orange hibiscus flowers, khaki shorts, cigar in mouth

Style: comic book panel, bold black outlines, vibrant colors, cartoon illustration, clean composition"""

        print(f"  Prompt: {prompt[:150]}...")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "model": model,
            "mode": mode,
            "aspect_ratio": DEFAULT_ASPECT_RATIO
        }
        
        # Add character reference if available
        if self.tr_reference_url:
            payload["cref"] = self.tr_reference_url
            print(f"  Using character reference: {self.tr_reference_url[:50]}...")
        
        for attempt in range(max_retries):
            try:
                print(f"  Generating... (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(
                    f"{self.base_url}/imagine",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code != 200:
                    print(f"  API Error: {response.status_code} - {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(5)
                        continue
                    return None
                
                data = response.json()
                
                # Check if we got a job ID (async generation)
                if "job_id" in data:
                    job_id = data["job_id"]
                    print(f"  Job started: {job_id}")
                    
                    # Wait for completion
                    image_url = self._wait_for_job(job_id, headers)
                    if image_url:
                        return image_url
                
                # Direct URL response
                elif "url" in data:
                    return data["url"]
                
                elif "image_url" in data:
                    return data["image_url"]
                
                else:
                    print(f"  Unexpected response: {data}")
                    return None
                    
            except Exception as e:
                print(f"  Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return None
        
        return None
    
    def _wait_for_job(self, job_id: str, headers: Dict, 
                     max_wait: int = 120, poll_interval: int = 5) -> Optional[str]:
        """Poll for job completion."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.base_url}/job/{job_id}",
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "unknown")
                    
                    if status == "completed":
                        # Get the image URL
                        if "url" in data:
                            return data["url"]
                        elif "image_url" in data:
                            return data["image_url"]
                        elif "output" in data and "url" in data["output"]:
                            return data["output"]["url"]
                    
                    elif status == "failed":
                        print(f"  Job failed: {data.get('error', 'Unknown error')}")
                        return None
                    
                    print(f"  Status: {status}... waiting")
                
                time.sleep(poll_interval)
                
            except Exception as e:
                print(f"  Poll error: {e}")
                time.sleep(poll_interval)
        
        print("  Timeout waiting for job completion")
        return None
    
    def download_image(self, url: str, filepath: Path) -> bool:
        """Download image from URL to local file."""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            print(f"  Download error: {e}")
            return False
    
    def generate_comic(self, script_path: str, model: str = DEFAULT_MODEL,
                      mode: str = DEFAULT_MODE,
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
            image_url = self.generate_panel(panel, script.title, model, mode)
            
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
    parser.add_argument("--model", default="midjourney-v7", help="Midjourney model version")
    parser.add_argument("--mode", default="fast", choices=["relaxed", "fast", "turbo"],
                       help="Generation mode (affects speed and cost)")
    parser.add_argument("--regenerate", action="store_true", help="Force regenerate existing panels")
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv("MIDAPI_KEY") and not args.ref_url:
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
        # Generate all drafts
        scripts_path = Path(args.scripts_dir)
        script_files = list(scripts_path.glob("comic-draft-*.md"))
        
        if not script_files:
            print(f"No scripts found in {args.scripts_dir}")
            return
        
        print(f"\n🚀 Batch generating {len(script_files)} comics...")
        
        for script_file in script_files:
            results = generator.generate_comic(
                str(script_file),
                model=args.model,
                mode=args.mode,
                skip_existing=not args.regenerate
            )
            print(f"\n  Results: {json.dumps(results, indent=2)}")
    
    elif args.script:
        # Generate single script
        results = generator.generate_comic(
            args.script,
            model=args.model,
            mode=args.mode,
            skip_existing=not args.regenerate
        )
        print(f"\n✅ Done!")
        print(f"   Generated: {sum(1 for p in results['panels'] if p['status'] == 'generated')}")
        print(f"   Failed: {sum(1 for p in results['panels'] if p['status'] == 'failed')}")
        print(f"   Output: {generator.output_dir.absolute()}")
    
    else:
        parser.print_help()
        print("\n💡 Examples:")
        print("  # Generate single comic with character reference:")
        print("  export MIDAPI_KEY='your-key'")
        print("  export TR_REFERENCE_URL='https://your-tr-image.png'")
        print("  python tr_midapi_generator.py scripts/comic-draft-biggest-boat-in-the-harbor.md")
        print("")
        print("  # Generate all drafts:")
        print("  python tr_midapi_generator.py --batch --scripts-dir scripts")
        print("")
        print("  # Force regenerate with turbo speed:")
        print("  python tr_midapi_generator.py script.md --mode turbo --regenerate")


if __name__ == "__main__":
    main()
