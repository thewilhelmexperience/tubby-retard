#!/usr/bin/env python3
"""
TR Comic Text Overlay Tool
Adds speech bubbles, captions, and dialogue to generated comic panels
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap


@dataclass
class SpeechBubble:
    text: str
    speaker: str  # "TR", "Captain", "Narrator", etc.
    position: str  # "top-left", "top-right", "bottom-left", "bottom-right", "center", "custom"
    x: int = 0  # For custom positioning
    y: int = 0
    width: int = 300  # Max width in pixels
    style: str = "round"  # "round", "square", "thought", "shout"


@dataclass
class ComicPanel:
    number: int
    image_path: str
    bubbles: List[SpeechBubble]
    caption: str = ""  # Narrative caption at bottom


class TextOverlayTool:
    def __init__(self, output_dir: str = "comics/final"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default fonts - will fall back to system defaults if not found
        try:
            # Comic-style fonts (will use system defaults if not available)
            self.bubble_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
            self.caption_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            self.narrator_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", 14)
        except:
            # Fallback to default font
            self.bubble_font = ImageFont.load_default()
            self.caption_font = ImageFont.load_default()
            self.narrator_font = ImageFont.load_default()
    
    def load_panel_data(self, script_path: str) -> List[ComicPanel]:
        """Extract dialogue and captions from comic script."""
        with open(script_path, 'r') as f:
            content = f.read()
        
        panels = []
        panel_sections = re.split(r'### Panel \d+:', content)[1:]
        
        for i, section in enumerate(panel_sections, 1):
            panel = self._parse_panel_text(i, section)
            if panel:
                panels.append(panel)
        
        return panels
    
    def _parse_panel_text(self, number: int, section: str) -> Optional[ComicPanel]:
        """Parse dialogue and captions from panel section."""
        # Find image path
        slug_match = re.search(r'\*\*Slug:\*\* (.+)', section)
        if not slug_match:
            # Get slug from parent document
            return None
        
        slug = slug_match.group(1).strip()
        image_path = f"comics/generated/comic-{slug}-panel{number}.png"
        
        # Extract dialogue
        bubbles = []
        dialogue_match = re.search(r'\*\*Dialogue:\*\*(.+?)(?=\*\*|$)', section, re.DOTALL)
        if dialogue_match:
            dialogue_text = dialogue_match.group(1).strip()
            # Parse "Speaker: Text" format
            lines = dialogue_text.split('\n')
            for line in lines:
                if ':' in line and not line.startswith('-'):
                    speaker, text = line.split(':', 1)
                    speaker = speaker.strip('- ')
                    text = text.strip('" ')
                    
                    # Determine position based on speaker and panel number
                    position = self._get_bubble_position(number, speaker)
                    
                    bubbles.append(SpeechBubble(
                        text=text,
                        speaker=speaker,
                        position=position,
                        style="round"
                    ))
        
        # Extract caption
        caption_match = re.search(r'\*\*Caption:\*\* (.+?)(?=\*\*|$)', section, re.DOTALL)
        caption = caption_match.group(1).strip() if caption_match else ""
        
        return ComicPanel(
            number=number,
            image_path=image_path,
            bubbles=bubbles,
            caption=caption
        )
    
    def _get_bubble_position(self, panel_number: int, speaker: str) -> str:
        """Determine bubble position based on speaker and panel layout."""
        # Default positioning logic
        if speaker == "TR":
            # TR is usually the focus, position his bubbles prominently
            if panel_number % 2 == 1:  # Odd panels
                return "top-right"
            else:
                return "bottom-right"
        elif speaker == "Captain":
            # Captain often reacts from background
            if panel_number % 2 == 1:
                return "bottom-left"
            else:
                return "top-left"
        elif "thought" in speaker.lower() or "thinking" in speaker.lower():
            return "top-center"
        else:
            return "bottom-center"
    
    def create_speech_bubble(self, draw: ImageDraw.Draw, bubble: SpeechBubble, 
                            panel_width: int, panel_height: int) -> Tuple[int, int, int, int]:
        """Draw a speech bubble and return its bounding box."""
        # Calculate bubble dimensions
        max_width = bubble.width
        wrapped_text = textwrap.fill(bubble.text, width=30)  # ~30 chars per line
        lines = wrapped_text.split('\n')
        
        # Get text dimensions
        line_heights = [draw.textbbox((0, 0), line, font=self.bubble_font)[3] - 
                       draw.textbbox((0, 0), line, font=self.bubble_font)[1] for line in lines]
        max_line_height = max(line_heights) if line_heights else 20
        
        text_width = max([draw.textbbox((0, 0), line, font=self.bubble_font)[2] - 
                         draw.textbbox((0, 0), line, font=self.bubble_font)[0] for line in lines])
        text_height = sum(line_heights) + (len(lines) - 1) * 5  # 5px spacing between lines
        
        # Bubble padding
        padding = 15
        bubble_width = min(text_width + padding * 2, max_width)
        bubble_height = text_height + padding * 2
        
        # Calculate position based on requested location
        x, y = self._calculate_bubble_position(bubble.position, bubble_width, bubble_height, 
                                              panel_width, panel_height, bubble.x, bubble.y)
        
        # Draw bubble based on style
        if bubble.style == "round":
            # Rounded rectangle bubble
            corner_radius = 20
            draw.rounded_rectangle([x, y, x + bubble_width, y + bubble_height], 
                                 radius=corner_radius, fill="white", outline="black", width=2)
            
            # Add little tail pointing to speaker (simplified - always points down)
            tail_x = x + bubble_width // 2
            tail_y = y + bubble_height
            draw.polygon([(tail_x - 10, tail_y), (tail_x + 10, tail_y), (tail_x, tail_y + 15)], 
                        fill="white", outline="black")
            
        elif bubble.style == "thought":
            # Cloud-like bubble for thoughts
            draw.ellipse([x, y, x + bubble_width, y + bubble_height], fill="white", outline="black", width=2)
            # Small bubbles leading to character
            draw.ellipse([x + 10, y + bubble_height, x + 20, y + bubble_height + 10], fill="white", outline="black")
            draw.ellipse([x + 5, y + bubble_height + 8, x + 12, y + bubble_height + 15], fill="white", outline="black")
            
        elif bubble.style == "shout":
            # Jagged edges for shouting
            points = self._create_shout_bubble_points(x, y, bubble_width, bubble_height)
            draw.polygon(points, fill="white", outline="black")
        
        else:  # square or default
            draw.rectangle([x, y, x + bubble_width, y + bubble_height], 
                         fill="white", outline="black", width=2)
        
        # Draw text
        text_y = y + padding
        for line in lines:
            text_x = x + padding
            draw.text((text_x, text_y), line, fill="black", font=self.bubble_font)
            text_y += max_line_height + 5
        
        # Add speaker label if not narrator
        if bubble.speaker and bubble.speaker not in ["Narrator", "Caption"]:
            label_text = f"— {bubble.speaker}"
            label_y = y + bubble_height + 5
            draw.text((x, label_y), label_text, fill="#666666", font=self.narrator_font)
        
        return (x, y, x + bubble_width, y + bubble_height)
    
    def _calculate_bubble_position(self, position: str, bubble_width: int, bubble_height: int,
                                  panel_width: int, panel_height: int, 
                                  custom_x: int = 0, custom_y: int = 0) -> Tuple[int, int]:
        """Calculate bubble position based on requested location."""
        margin = 20
        
        if position == "top-left":
            return (margin, margin)
        elif position == "top-right":
            return (panel_width - bubble_width - margin, margin)
        elif position == "top-center":
            return ((panel_width - bubble_width) // 2, margin)
        elif position == "bottom-left":
            return (margin, panel_height - bubble_height - margin - 30)  # Extra space for caption
        elif position == "bottom-right":
            return (panel_width - bubble_width - margin, panel_height - bubble_height - margin - 30)
        elif position == "bottom-center":
            return ((panel_width - bubble_width) // 2, panel_height - bubble_height - margin - 30)
        elif position == "center":
            return ((panel_width - bubble_width) // 2, (panel_height - bubble_height) // 2)
        elif position == "custom":
            return (custom_x, custom_y)
        else:
            # Default to top-right
            return (panel_width - bubble_width - margin, margin)
    
    def _create_shout_bubble_points(self, x: int, y: int, width: int, height: int) -> List[Tuple[int, int]]:
        """Create jagged points for shout bubble."""
        import random
        random.seed(42)  # Consistent randomness
        
        points = []
        # Top edge
        for i in range(0, width, 15):
            offset = random.randint(-3, 3)
            points.append((x + i, y + offset))
        # Right edge
        for i in range(0, height, 15):
            offset = random.randint(-3, 3)
            points.append((x + width + offset, y + i))
        # Bottom edge
        for i in range(width, 0, -15):
            offset = random.randint(-3, 3)
            points.append((x + i, y + height + offset))
        # Left edge
        for i in range(height, 0, -15):
            offset = random.randint(-3, 3)
            points.append((x + offset, y + i))
        
        return points
    
    def add_caption(self, draw: ImageDraw.Draw, caption: str, panel_width: int, panel_height: int):
        """Add narrative caption at bottom of panel."""
        if not caption:
            return
        
        # Wrap caption text
        max_width = panel_width - 40  # 20px margin each side
        wrapped = textwrap.fill(caption, width=60)  # ~60 chars per line
        lines = wrapped.split('\n')
        
        # Calculate caption box
        line_height = 20
        caption_height = len(lines) * line_height + 20  # 10px padding
        
        # Draw caption background
        caption_y = panel_height - caption_height - 10
        draw.rectangle([10, caption_y, panel_width - 10, panel_height - 10], 
                      fill=(255, 255, 240), outline=(200, 200, 180), width=1)
        
        # Draw caption text
        text_y = caption_y + 10
        for line in lines:
            draw.text((20, text_y), line, fill="#333333", font=self.caption_font)
            text_y += line_height
    
    def process_panel(self, panel: ComicPanel, output_filename: str):
        """Process a single panel - add bubbles and caption."""
        # Load image
        image_path = Path(panel.image_path)
        if not image_path.exists():
            print(f"  ⚠️  Image not found: {image_path}")
            return False
        
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        width, height = img.size
        
        # Add speech bubbles
        for bubble in panel.bubbles:
            self.create_speech_bubble(draw, bubble, width, height)
        
        # Add caption
        self.add_caption(draw, panel.caption, width, height)
        
        # Save final image
        output_path = self.output_dir / output_filename
        img.save(output_path, "PNG")
        print(f"  ✅ Saved: {output_path}")
        
        return True
    
    def process_comic(self, script_path: str):
        """Process all panels for a comic."""
        print(f"\n📝 Processing text overlays for: {script_path}")
        
        panels = self.load_panel_data(script_path)
        
        if not panels:
            print("  ⚠️  No panel data found")
            return
        
        success_count = 0
        for panel in panels:
            print(f"\n  Panel {panel.number}:")
            
            # Generate output filename
            slug_match = re.search(r'comic-draft-(.+)\.md', Path(script_path).name)
            slug = slug_match.group(1) if slug_match else "unknown"
            output_filename = f"comic-{slug}-panel{panel.number}-final.png"
            
            if self.process_panel(panel, output_filename):
                success_count += 1
        
        print(f"\n✅ Complete! Processed {success_count}/{len(panels)} panels")
        print(f"   Output: {self.output_dir.absolute()}")


def main():
    parser = argparse.ArgumentParser(description="Add text overlays to TR comics")
    parser.add_argument("script", help="Path to comic script .md file")
    parser.add_argument("--output", default="comics/final", help="Output directory")
    parser.add_argument("--font-size", type=int, default=18, help="Font size for bubbles")
    
    args = parser.parse_args()
    
    tool = TextOverlayTool(output_dir=args.output)
    tool.process_comic(args.script)


if __name__ == "__main__":
    main()
