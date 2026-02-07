# TR Comic Generator - MidAPI.ai Edition

Generate consistent TR comic panels using Midjourney via MidAPI.ai API.

## Setup

1. **Get API Key:**
   - Sign up at https://midapi.ai
   - Get your API key from dashboard

2. **Upload TR Reference:**
   - Upload your `tr-character.png` to an image host (Imgur, Discord, etc.)
   - Get the direct image URL

3. **Install Dependencies:**
```bash
cd tr-website/scripts
source venv/bin/activate  # If using virtual env
pip install requests
```

4. **Set Environment Variables:**
```bash
export MIDAPI_KEY="your-midapi-key-here"
export TR_REFERENCE_URL="https://your-tr-image-url.png"
```

## Usage

### Generate Single Comic:
```bash
python tr_midapi_generator.py scripts/comic-draft-biggest-boat-in-the-harbor.md
```

### Generate All Drafts:
```bash
python tr_midapi_generator.py --batch --scripts-dir scripts
```

### Force Regenerate:
```bash
python tr_midapi_generator.py script.md --regenerate
```

### Speed Options:
```bash
# Fast (default) - balanced speed/cost
python tr_midapi_generator.py script.md --mode fast

# Turbo - fastest, premium price
python tr_midapi_generator.py script.md --mode turbo

# Relaxed - slowest, cheapest
python tr_midapi_generator.py script.md --mode relaxed
```

## How It Works

1. **Parses script** - Reads your .md comic scripts
2. **Simplifies prompts** - Converts detailed descriptions to Midjourney-friendly prompts
3. **Uses --oref** - Sends TR reference image for character consistency
4. **Generates 4 panels** - One at a time with character reference
5. **Downloads images** - Saves to `comics/generated/`

## Character Consistency

The script includes TR's description in every prompt:
- Chubby middle-aged man
- White captain's hat with gold anchor emblem
- Blue Hawaiian shirt with orange hibiscus flowers
- Khaki shorts, cigar in mouth

Plus uses `--oref` with your reference image URL.

## Pricing

MidAPI.ai pricing (approximate):
- **Relaxed mode:** ~$0.03-0.05 per image
- **Fast mode:** ~$0.05-0.08 per image  
- **Turbo mode:** ~$0.08-0.12 per image

4-panel comic: ~$0.20-0.50 depending on mode

## Troubleshooting

**"MIDAPI_KEY not set":**
- Make sure you exported the environment variable
- Or pass `--ref-url` with your character reference

**Character looks different:**
- Check your TR_REFERENCE_URL is a direct image link
- Make sure image is clear and shows TR clearly
- Use `--mode fast` or `--mode turbo` for better quality

**Generation fails:**
- Check your MidAPI.ai account has credits
- Try `--mode relaxed` (slower but more reliable)
- Check your API key is correct

## Output

Images saved as:
- `comics/generated/comic-{slug}-panel{1-4}.png`

## Notes

- Generation takes 30-60 seconds per panel (async)
- Script polls for completion automatically
- Failed panels can be retried with `--regenerate`
- Keep prompts simple - one clear scene per panel
