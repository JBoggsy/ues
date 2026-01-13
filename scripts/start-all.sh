#!/bin/bash
# Start both the UES API server and Web UI
#
# Usage:
#   ./scripts/start-all.sh
#
# This script starts:
#   1. UES API server on http://localhost:8000
#   2. UES Web UI on http://localhost:5173

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting UES (API + Web UI)${NC}"
echo ""

# Function to clean up background processes on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $API_PID 2>/dev/null || true
    kill $WEBAPP_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start API server in background
echo "Starting API server..."
cd "$PROJECT_ROOT"
if command -v uv &> /dev/null; then
    uv run uvicorn main:app --reload &
else
    python -m uvicorn main:app --reload &
fi
API_PID=$!
sleep 2

# Start Web UI in background
echo "Starting Web UI..."
cd "$PROJECT_ROOT/webapp"
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run dev &
WEBAPP_PID=$!

echo ""
echo -e "${GREEN}✅ UES is running!${NC}"
echo "   API:    http://localhost:8000"
echo "   Docs:   http://localhost:8000/docs"
echo "   Web UI: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for processes
wait
