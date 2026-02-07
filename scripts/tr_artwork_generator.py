#!/usr/bin/env python3
"""
TR Comic Artwork Generator
Generates comic panels using OpenAI Images API (GPT Image 1.5)
Reads comic scripts from .md files and outputs consistent artwork.
"""

import os
import re
import json
import base64
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from openai import OpenAI
from PIL import Image
from io import BytesIO

# TR Character consistency string - include in EVERY prompt
TR_CHARACTER = """Chubby middle-aged man named TR (Tubby Retard), yacht owner character:
- Wearing a white captain's hat with gold anchor emblem
- Blue Hawaiian shirt with orange/red hibiscus flowers
- Khaki shorts
- Often smoking a cigar
- Overconfident, slightly oblivious expression
- Heavyset build, rosy cheeks
- Cartoon comic book style, bold outlines, vibrant colors"""

# Style guide for consistency
COMIC_STYLE = """Comic book panel style:
- Bold black outlines
- Vibrant saturated colors
- Cartoon illustration style
- Clear readable expressions
- Yachting/marina setting
- Slightly exaggerated proportions for humor"""


@dataclass
class ComicPanel:
    number: int
    description: str
    dialogue: str
    dall_e_prompt: str
    caption: str = ""


@dataclass
class ComicScript:
    title: str
    slug: str
    location: str
    panels: List[ComicPanel]
    caption: str = ""
    status: str = "DRAFT"


class TRArtworkGenerator:
    def __init__(self, api_key: Optional[str] = None, output_dir: str = "comics/generated"):
        """Initialize generator with OpenAI API key."""
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        # Extract caption
        caption_match = re.search(r'## Caption:\s*\n+(.+?)(?=\n##|$)', content, re.DOTALL)
        caption = caption_match.group(1).strip() if caption_match else ""
        
        # Parse panels
        panels = []
        panel_sections = re.split(r'### Panel \d+:', content)[1:]  # Skip first empty split
        
        for i, section in enumerate(panel_sections, 1):
            panel = self._parse_panel(i, section)
            if panel:
                panels.append(panel)
        
        return ComicScript(
            title=title,
            slug=slug,
            location=location,
            panels=panels,
            caption=caption
        )
    
    def _parse_panel(self, number: int, section: str) -> Optional[ComicPanel]:
        """Parse a single panel section from the script."""
        # Extract scene description
        scene_match = re.search(r'\*\*Scene:\*\* (.+?)(?=\*\*|$)', section, re.DOTALL)
        description = scene_match.group(1).strip() if scene_match else ""
        
        # Extract dialogue
        dialogue_match = re.search(r'\*\*Dialogue:\*\*(.+?)(?=\*\*|$)', section, re.DOTALL)
        dialogue = dialogue_match.group(1).strip() if dialogue_match else ""
        
        # Extract DALL-E prompt if present
        prompt_match = re.search(r'\*\*DALL-E Prompt:\*\*\s*```(.+?)```', section, re.DOTALL)
        dall_e_prompt = prompt_match.group(1).strip() if prompt_match else ""
        
        # Extract caption
        caption_match = re.search(r'\*\*Caption:\*\* (.+?)(?=\*\*|$)', section, re.DOTALL)
        caption = caption_match.group(1).strip() if caption_match else ""
        
        if not description:
            return None
            
        return ComicPanel(
            number=number,
            description=description,
            dialogue=dialogue,
            dall_e_prompt=dall_e_prompt,
            caption=caption
        )
    
    def generate_panel_prompt(self, panel: ComicPanel, comic_title: str) -> str:
        """Generate a comprehensive prompt for a panel."""
        # Use existing DALL-E prompt if available, otherwise build from description
        if panel.dall_e_prompt:
            base_prompt = panel.dall_e_prompt
        else:
            base_prompt = panel.description
        
        # Build full prompt with consistency
        full_prompt = f"""{TR_CHARACTER}

{COMIC_STYLE}

Panel {panel.number} of 4 for comic titled "{comic_title}":
Scene: {base_prompt}

Make sure:
- TR is clearly visible with his signature captain's hat and Hawaiian shirt
- The scene is readable at comic panel size
- Expressions match the tone (comedic, exaggerated)
- Background elements support the yachting setting"""

        return full_prompt
    
    def generate_panel(self, prompt: str, size: str = "1024x1024", quality: str = "hd",
                      max_retries: int = 3) -> Optional[bytes]:
        """Generate a single panel image using OpenAI Images API."""
        import requests

        for attempt in range(max_retries):
            try:
                print(f"  Generating... (attempt {attempt + 1}/{max_retries})")

                response = self.client.images.generate(
                    model="dall-e-3",  # Use DALL-E 3 (more stable)
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    n=1
                )

                # Get image URL and download
                image_url = response.data[0].url

                # Download the image
                image_response = requests.get(image_url, timeout=30)
                image_response.raise_for_status()

                # Store the revised prompt for reference
                revised_prompt = getattr(response.data[0], 'revised_prompt', '')
                if revised_prompt:
                    print(f"  Revised prompt: {revised_prompt[:100]}...")

                return image_response.content

            except Exception as e:
                print(f"  Error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return None

        return None
    
    def save_panel(self, image_data: bytes, slug: str, panel_number: int, 
                   format: str = "png") -> str:
        """Save generated panel to disk."""
        filename = f"comic-{slug}-panel{panel_number}.{format}"
        filepath = self.output_dir / filename
        
        # Save raw image
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        # Also save a JPEG version for smaller file size if needed
        if format == "png":
            try:
                img = Image.open(BytesIO(image_data))
                jpeg_path = self.output_dir / f"comic-{slug}-panel{panel_number}.jpg"
                img.convert('RGB').save(jpeg_path, 'JPEG', quality=90)
                print(f"  Also saved JPEG: {jpeg_path}")
            except Exception as e:
                print(f"  Warning: Could not create JPEG: {e}")
        
        return str(filepath)
    
    def generate_comic(self, script_path: str, output_format: str = "png",
                      skip_existing: bool = True) -> Dict:
        """Generate all panels for a comic script."""
        print(f"\n🎨 Processing: {script_path}")
        
        # Parse script
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
        
        # Generate each panel
        for panel in script.panels:
            print(f"\n  Panel {panel.number}:")
            
            # Check if already exists
            output_file = self.output_dir / f"comic-{script.slug}-panel{panel.number}.{output_format}"
            if skip_existing and output_file.exists():
                print(f"    ⏭️  Skipping (already exists): {output_file}")
                results["panels"].append({
                    "number": panel.number,
                    "file": str(output_file),
                    "status": "skipped"
                })
                continue
            
            # Generate prompt
            prompt = self.generate_panel_prompt(panel, script.title)
            print(f"    Prompt: {prompt[:100]}...")
            
            # Generate image
            image_data = self.generate_panel(prompt)
            
            if image_data:
                # Save image
                filepath = self.save_panel(image_data, script.slug, panel.number, output_format)
                print(f"    ✅ Saved: {filepath}")
                results["panels"].append({
                    "number": panel.number,
                    "file": filepath,
                    "status": "generated"
                })
            else:
                print(f"    ❌ Failed to generate panel {panel.number}")
                results["panels"].append({
                    "number": panel.number,
                    "file": None,
                    "status": "failed"
                })
                results["status"] = "partial"
        
        return results
    
    def batch_generate(self, scripts_dir: str = "scripts", pattern: str = "comic-draft-*.md"):
        """Generate artwork for all draft scripts in directory."""
        scripts_path = Path(scripts_dir)
        script_files = list(scripts_path.glob(pattern))
        
        if not script_files:
            print(f"No scripts found matching {pattern} in {scripts_dir}")
            return []
        
        print(f"\n🚀 Batch generating {len(script_files)} comics...")
        
        all_results = []
        for script_file in script_files:
            results = self.generate_comic(str(script_file))
            all_results.append(results)
        
        # Summary
        print(f"\n📊 Summary:")
        successful = sum(1 for r in all_results if r["status"] == "success")
        partial = sum(1 for r in all_results if r["status"] == "partial")
        print(f"  ✅ Complete: {successful}")
        print(f"  ⚠️  Partial: {partial}")
        print(f"  📁 Output: {self.output_dir.absolute()}")
        
        return all_results
    
    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to URL-safe slug."""
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        text = text.strip('-')
        return text[:50]


def main():
    parser = argparse.ArgumentParser(description="Generate TR comic artwork")
    parser.add_argument("script", nargs="?", help="Path to comic script .md file")
    parser.add_argument("--batch", action="store_true", help="Generate all draft scripts")
    parser.add_argument("--scripts-dir", default="scripts", help="Directory containing scripts")
    parser.add_argument("--output", default="comics/generated", help="Output directory")
    parser.add_argument("--format", default="png", choices=["png", "jpg"], help="Output format")
    parser.add_argument("--regenerate", action="store_true", help="Regenerate existing panels")
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = TRArtworkGenerator(output_dir=args.output)
    
    if args.batch:
        # Generate all drafts
        results = generator.batch_generate(args.scripts_dir)
    elif args.script:
        # Generate single script
        results = generator.generate_comic(args.script, args.format, skip_existing=not args.regenerate)
        print(f"\nResults: {json.dumps(results, indent=2)}")
    else:
        parser.print_help()
        print("\n💡 Examples:")
        print("  python tr_artwork_generator.py scripts/comic-draft-test.md")
        print("  python tr_artwork_generator.py --batch --scripts-dir scripts")
        print("  python tr_artwork_generator.py --batch --regenerate  # Force regenerate all")


if __name__ == "__main__":
    main()
