#!/bin/bash
# Stop both dashboards

echo "🛑 Stopping dashboards..."

# Stop Python HTTP server
pkill -f "python.*http.server 8080" 2>/dev/null

# Stop Node.js admin server
pkill -f "node.*server.js" 2>/dev/null

echo "✅ Dashboards stopped"
