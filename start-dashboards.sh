#!/bin/bash
# Start both dashboards

echo "🚀 Starting TR Dashboards..."
echo ""

# Start main project dashboard (Python)
if ! curl -s http://localhost:8080 > /dev/null; then
    echo "📊 Starting Project Dashboard on http://localhost:8080..."
    python3 -m http.server 8080 --directory /home/captain_tommy/.openclaw/workspace > /tmp/dashboard.log 2>&1 &
else
    echo "📊 Project Dashboard already running on http://localhost:8080"
fi

# Start TR admin dashboard (Node.js)
if ! curl -s http://localhost:8082 > /dev/null; then
    echo "🦜 Starting TR Admin Dashboard on http://localhost:8082..."
    cd /home/captain_tommy/.openclaw/workspace/tr-website/admin
    
    # Install deps if needed
    if [ ! -d "node_modules" ]; then
        echo "   Installing dependencies..."
        npm install
    fi
    
    node server.js > /tmp/tr-admin.log 2>&1 &
else
    echo "🦜 TR Admin Dashboard already running on http://localhost:8082"
fi

echo ""
echo "✅ Both dashboards are running!"
echo ""
echo "Dashboards:"
echo "  📊 Main Projects:  http://localhost:8080/dashboard.html"
echo "  🦜 TR Admin:      http://localhost:8082/login"
echo ""
echo "To stop: ./stop-dashboards.sh"
