#!/bin/bash
# Test script for OpenClaw webhook endpoint
# Usage: ./test-webhook.sh "your-hook-token" "http://gateway:port"

TOKEN=${1:-"YOUR_TOKEN_HERE"}
URL=${2:-"http://localhost:18789/hooks/agent"}

echo "Testing OpenClaw webhook..."
echo "URL: $URL"
echo ""

curl -X POST "$URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "📝 New TR Story Submission\n\n**Title:** The Great Anchor Drag\n**Location:** Florida Keys\n**Slug:** great-anchor-drag\n\n**Story:**\nTR decided to anchor in a crowded mooring field. He dropped the hook in 10 feet of water with 200 feet of chain. When the wind shifted, his boat started doing donuts around everyone else. He blamed the 'tide' even though it was dead calm.\n\n---\nPlease generate a comic script for this story and save it to tr-website/scripts/comic-draft-great-anchor-drag.md",
    "name": "TR-Test",
    "channel": "telegram",
    "deliver": true,
    "wakeMode": "now",
    "timeoutSeconds": 120
  }'

echo ""
echo ""
echo "Test complete!"
