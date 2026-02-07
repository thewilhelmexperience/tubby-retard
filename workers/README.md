# TR Story Submission Automation - Setup Guide

This guide sets up automatic script generation from tubbyretard.com story submissions.

## Architecture

```
User submits form on tubbyretard.com
            ↓
    Cloudflare Worker receives POST
            ↓
    Worker sanitizes input (security)
            ↓
    Worker POSTs to OpenClaw /hooks/agent
            ↓
    Wilhelm receives message, generates script
            ↓
    Script saved to workspace for review
            ↓
    Tommy approves/edits, publishes comic
```

---

## Step 1: Configure OpenClaw Webhooks

### Via Onboard Wizard

1. Run `openclaw onboard`
2. When you reach the **Hooks** section, enable:
   - ✅ **Webhook endpoint** (`hooks.enabled: true`)
   - Set a strong secret token (`hooks.token`)
   - Path defaults to `/hooks` (keep this)

### Manual Config

Add to your OpenClaw config file:

```json
{
  "hooks": {
    "enabled": true,
    "token": "YOUR_SECRET_TOKEN_HERE",
    "path": "/hooks"
  }
}
```

**Generate a secure token:**
```bash
openssl rand -hex 32
```

Copy this token - you'll need it for the Worker config.

### Restart Gateway

After enabling hooks, restart your OpenClaw gateway process so the changes take effect.

---

## Step 2: Deploy Cloudflare Worker

### Prerequisites

- Cloudflare account with Workers enabled
- Wrangler CLI installed: `npm install -g wrangler`
- Authenticated: `wrangler login`

### Setup

1. Navigate to the worker directory:
   ```bash
   cd tr-website/workers
   ```

2. Update `wrangler.toml` with your settings:
   ```toml
   name = "tr-story-submission"
   ```

3. Set environment variables:
   ```bash
   # Your OpenClaw webhook URL (replace with your actual gateway address)
   wrangler secret put OPENCLAW_HOOK_URL
   # Enter: https://your-gateway-address:18789/hooks/agent
   
   # The secret token from Step 1
   wrangler secret put OPENCLAW_HOOK_TOKEN
   # Enter: your-secret-token-from-step-1
   
   # Your Telegram chat ID (so I can notify you)
   wrangler secret put TELEGRAM_CHAT_ID
   # Enter: 6285846217 (or your actual chat ID)
   ```

4. Deploy:
   ```bash
   wrangler deploy
   ```

5. Copy the worker URL (e.g., `https://tr-story-submission.your-account.workers.dev`)

---

## Step 3: Update tubbyretard.com Form

Change your form submission URL from Formspree to the Worker:

### Option A: Direct Form POST (Recommended)

Update `submit.html`:

```html
<form action="https://tr-story-submission.your-account.workers.dev" method="POST">
  <input type="text" name="title" placeholder="Story title" required>
  <textarea name="story" placeholder="Your story..." required></textarea>
  <input type="text" name="location" placeholder="Location (optional)">
  <button type="submit">Submit Story</button>
</form>
```

### Option B: Keep Formspree, Add Webhook

If you want to keep Formspree for email backup:

1. In Formspree dashboard, add a webhook
2. Set webhook URL to your Worker URL
3. Formspree will POST to both email AND your Worker

---

## Step 4: Test the Pipeline

1. Submit a test story on tubbyretard.com
2. Check Telegram - you should receive a message from me
3. I will generate a script draft and save it to:
   `tr-website/scripts/comic-draft-[slug].md`
4. Review the draft, edit if needed
5. Generate artwork and publish!

---

## Security Features

The Worker includes multiple security layers:

1. **Input Sanitization**
   - Strips HTML tags (`<script>`, `<iframe>`, etc.)
   - Removes dangerous characters (`;`, `|`, `$`, etc.)
   - Limits length (title: 100 chars, story: 2000 chars)

2. **Spam Detection**
   - Rejects URLs in submissions
   - Blocks common spam patterns
   - Requires minimum story length (20 chars)

3. **Authentication**
   - Hook token required for OpenClaw endpoint
   - Sent via Authorization header
   - Never exposed to frontend

4. **Error Handling**
   - Never exposes internal errors to users
   - Logs issues for debugging
   - Returns generic messages on failure

---

## How It Works

When a submission arrives:

1. **Worker receives POST** with title, story, location
2. **Sanitizes input** - removes anything dangerous
3. **Validates** - checks for spam, length requirements
4. **Generates slug** - creates URL-safe filename
5. **POSTs to OpenClaw** with formatted message
6. **I (Wilhelm) receive** the message instantly
7. **I generate script** with:
   - 4-panel structure
   - DALL-E prompts for each panel
   - Character consistency notes
   - Marked as `[DRAFT - PENDING REVIEW]`
8. **Script saved** to workspace
9. **You review** via Telegram or file system
10. **You approve** → generate artwork → publish!

---

## Troubleshooting

### Worker not receiving submissions
- Check Cloudflare Workers dashboard for logs
- Verify form action URL matches Worker route
- Test with curl: `curl -X POST worker-url -d '{"title":"Test","story":"Test story"}'`

### OpenClaw not receiving webhook
- Check OpenClaw gateway logs
- Verify token matches between Worker and OpenClaw config
- Test webhook directly: `curl -X POST gateway/hooks/agent -H "Authorization: Bearer TOKEN" ...`

### I'm not generating scripts
- Check that I received the Telegram message
- Check my session logs for errors
- Verify workspace directory is accessible

---

## Files Created

- `workers/story-submission-worker.js` - Cloudflare Worker code
- `workers/wrangler.toml` - Worker deployment config
- `config/openclaw-hooks-config.json` - OpenClaw config snippet

---

## Future Enhancements

- Rate limiting per IP (prevent spam)
- KV storage for submission tracking
- Queue system for batch processing
- Auto-response email to submitters
- Discord/Slack notifications

---

Ready to automate! 🚀🦜
