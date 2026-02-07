#!/bin/bash
# Start TR Admin Dashboard

cd "$(dirname "$0")/admin"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Set default password if not set
if [ -z "$ADMIN_PASSWORD" ]; then
    export ADMIN_PASSWORD="tr-admin-2024"
    echo "⚠️  Using default password: tr-admin-2024"
    echo "   Set ADMIN_PASSWORD env var for security"
fi

echo "🚀 Starting TR Admin Dashboard..."
node server.js &

echo ""
echo "Dashboards running:"
echo "  📊 TR Admin: http://localhost:8082"
echo "  🔒 Login: http://localhost:8082/login"
echo ""
echo "To stop: pkill -f 'node.*server.js'"
