#!/bin/bash

echo "Starting AutoClipper Services..."

# Start Gateway on port 8001
python api/gumloop_gateway.py &
GATEWAY_PID=$!

# Start Render Worker on port 8000
python render/worker.py &
WORKER_PID=$!

echo "✅ Gateway running on http://localhost:8001 (PID: $GATEWAY_PID)"
echo "✅ Render Worker running on http://localhost:8000 (PID: $WORKER_PID)"
echo ""
echo "To stop: kill $GATEWAY_PID $WORKER_PID"
echo ""
echo "Test health: curl http://localhost:8001/health"
