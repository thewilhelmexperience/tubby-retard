# TR Comic Artwork Generator

Generate comic panels using OpenAI Images API (GPT Image 1.5)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

## Usage

### Generate single comic:
```bash
python tr_artwork_generator.py scripts/comic-draft-biggest-boat-in-the-harbor.md
```

### Generate all drafts:
```bash
python tr_artwork_generator.py --batch --scripts-dir scripts
```

### Force regenerate (overwrite existing):
```bash
python tr_artwork_generator.py --batch --regenerate
```

### Custom output directory:
```bash
python tr_artwork_generator.py --batch --output comics/published
```

## Output

Generated panels saved as:
- `comics/generated/comic-{slug}-panel{1-4}.png`
- Also creates `.jpg` versions for smaller file size

## Tips for Good Results

1. **Review scripts first** - Make sure panel descriptions are clear
2. **Check first panel** - If TR looks wrong, the rest will too
3. **Regenerate bad panels** - Use `--regenerate` on specific scripts
4. **Consistent sizing** - All panels are 1024x1024 by default
5. **High quality** - Uses `gpt-image-1.5` with "high" quality setting

## Cost Estimate

- GPT Image 1.5 @ 1024x1024, high quality: ~$0.08-0.20 per image
- 4-panel comic: ~$0.32-0.80 per comic

## Workflow Integration

After artwork generation:
1. Review generated panels in `comics/generated/`
2. Copy approved panels to `comics/published/`
3. Update HTML comic page with new panel paths
4. Add to archive
5. Queue for social media posting
