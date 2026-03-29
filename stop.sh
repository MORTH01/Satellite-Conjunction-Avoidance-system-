#!/bin/bash
# Stop all Conjunction Avoidance System processes

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}Stopping all services...${NC}"

# Kill by saved PIDs
if [ -f "$DIR/.pids" ]; then
  for pid in $(cat "$DIR/.pids"); do
    kill "$pid" 2>/dev/null && echo -e "${GREEN}✓  Stopped PID $pid${NC}" || true
  done
  rm "$DIR/.pids"
fi

# Also kill by name in case PIDs drifted
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "celery.*celery_app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

echo -e "${GREEN}✓  All services stopped${NC}"
echo -e "   PostgreSQL and Redis are still running (managed by Homebrew)"
echo -e "   To stop them too: brew services stop postgresql@15 redis"
