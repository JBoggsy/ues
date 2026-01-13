#!/bin/bash
# Start the UES Web UI development server
#
# Usage:
#   ./scripts/start-webapp.sh [--port PORT]
#
# This script will:
#   1. Check for Node.js and npm
#   2. Install dependencies if node_modules doesn't exist
#   3. Start the development server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WEBAPP_DIR="$PROJECT_ROOT/webapp"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🌐 UES Web UI Starter${NC}"
echo ""

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed.${NC}"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${YELLOW}Warning: Node.js version 18+ recommended (found v$NODE_VERSION)${NC}"
fi

# Check for npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed.${NC}"
    exit 1
fi

cd "$WEBAPP_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    npm install
    echo ""
fi

# Start the development server
echo -e "${GREEN}🚀 Starting Web UI development server...${NC}"
echo "   URL: http://localhost:5173"
echo ""
npm run dev
