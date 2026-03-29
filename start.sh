#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Conjunction Avoidance System — Start everything
# Run: bash start.sh
# ─────────────────────────────────────────────────────────────────────────────

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env
if [ ! -f "$DIR/.env" ]; then
  echo -e "${RED}✗  .env not found. Run: bash setup.sh first${NC}"
  exit 1
fi

export $(grep -v '^#' "$DIR/.env" | grep -v '^$' | xargs)
export DATABASE_URL="postgresql+asyncpg://localhost/conjunction_db"
export DATABASE_URL_SYNC="postgresql://localhost/conjunction_db"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="${SECRET_KEY:-dev-secret-key}"

echo ""
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  Conjunction Avoidance System — Starting"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Ensure Postgres + Redis running
brew services start postgresql@15 2>/dev/null || true
brew services start redis 2>/dev/null || true
sleep 1

# Create log directory
mkdir -p "$DIR/logs"

echo -e "${GREEN}✓  PostgreSQL and Redis running${NC}"

# ── Kill any previous instances ──────────────────────────────────────────
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "celery.*conjunction" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 1

# ── Start FastAPI backend ─────────────────────────────────────────────────
echo -e "${CYAN}Starting API server...${NC}"
cd "$DIR/backend"
source .venv/bin/activate
export SPACETRACK_USER SPACETRACK_PASS DATABASE_URL DATABASE_URL_SYNC REDIS_URL SECRET_KEY
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
  > "$DIR/logs/api.log" 2>&1 &
API_PID=$!
echo -e "${GREEN}✓  API server started (PID $API_PID) → http://localhost:8000${NC}"
echo -e "   Logs: $DIR/logs/api.log"

# ── Start Celery worker ───────────────────────────────────────────────────
echo -e "${CYAN}Starting Celery worker...${NC}"
cd "$DIR/backend"
source .venv/bin/activate
nohup celery -A app.workers.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  > "$DIR/logs/worker.log" 2>&1 &
WORKER_PID=$!
echo -e "${GREEN}✓  Celery worker started (PID $WORKER_PID)${NC}"
echo -e "   Logs: $DIR/logs/worker.log"

# ── Start Celery Beat (scheduler) ────────────────────────────────────────
echo -e "${CYAN}Starting scheduler (every 6h screen)...${NC}"
cd "$DIR/backend"
source .venv/bin/activate
nohup celery -A app.workers.celery_app beat \
  --loglevel=info \
  > "$DIR/logs/scheduler.log" 2>&1 &
BEAT_PID=$!
echo -e "${GREEN}✓  Scheduler started (PID $BEAT_PID)${NC}"

# ── Wait for API to be ready ─────────────────────────────────────────────
echo -e "${CYAN}Waiting for API to be ready...${NC}"
for i in {1..20}; do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓  API is ready${NC}"
    break
  fi
  sleep 1
  if [ $i -eq 20 ]; then
    echo -e "${YELLOW}⚠  API taking longer than expected. Check logs/api.log${NC}"
  fi
done

# ── Start frontend ────────────────────────────────────────────────────────
echo -e "${CYAN}Starting frontend...${NC}"
cd "$DIR/frontend"
nohup npm run dev > "$DIR/logs/frontend.log" 2>&1 &
FRONT_PID=$!
echo -e "${GREEN}✓  Frontend started (PID $FRONT_PID)${NC}"

# Save PIDs for stop script
echo "$API_PID $WORKER_PID $BEAT_PID $FRONT_PID" > "$DIR/.pids"

sleep 2

echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  Everything is running!"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Dashboard →  ${CYAN}http://localhost:5173${NC}"
echo -e "  API docs  →  ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo -e "  To stop everything:  ${YELLOW}bash stop.sh${NC}"
echo -e "  To view logs:        ${YELLOW}tail -f logs/api.log${NC}"
echo ""

# Open browser automatically
sleep 2
open "http://localhost:5173" 2>/dev/null || true
