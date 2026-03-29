#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Conjunction Avoidance System — macOS setup (no Docker)
# Run once: bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  Conjunction Avoidance System — macOS Setup"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 1. Check .env ──────────────────────────────────────────────────────────
if [ ! -f "$DIR/.env" ]; then
  cp "$DIR/.env.example" "$DIR/.env"
  echo -e "${YELLOW}⚠  Created .env file. Please fill in your Space-Track credentials:${NC}"
  echo -e "   Open .env and set SPACETRACK_USER and SPACETRACK_PASS"
  echo ""
  echo "   Run:  nano $DIR/.env"
  echo ""
  exit 1
fi

SPACETRACK_USER=$(grep SPACETRACK_USER "$DIR/.env" | cut -d= -f2 | tr -d ' ')
SPACETRACK_PASS=$(grep SPACETRACK_PASS "$DIR/.env" | cut -d= -f2 | tr -d ' ')

if [[ "$SPACETRACK_USER" == *"example"* ]] || [ -z "$SPACETRACK_USER" ]; then
  echo -e "${RED}✗  SPACETRACK_USER not set in .env${NC}"
  echo "   Run:  nano $DIR/.env"
  exit 1
fi
echo -e "${GREEN}✓  .env configured (${SPACETRACK_USER})${NC}"

# ── 2. Check Homebrew ──────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
  echo ""
  echo -e "${YELLOW}Installing Homebrew (package manager for macOS)...${NC}"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Add brew to PATH for Apple Silicon
  if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
fi
echo -e "${GREEN}✓  Homebrew ready${NC}"

# ── 3. Install PostgreSQL ──────────────────────────────────────────────────
if ! command -v psql &>/dev/null; then
  echo -e "${CYAN}Installing PostgreSQL...${NC}"
  brew install postgresql@15
  brew link postgresql@15 --force
fi
echo -e "${GREEN}✓  PostgreSQL ready${NC}"

# ── 4. Install Redis ──────────────────────────────────────────────────────
if ! command -v redis-server &>/dev/null; then
  echo -e "${CYAN}Installing Redis...${NC}"
  brew install redis
fi
echo -e "${GREEN}✓  Redis ready${NC}"

# ── 5. Start services ─────────────────────────────────────────────────────
echo -e "${CYAN}Starting PostgreSQL and Redis...${NC}"
brew services start postgresql@15 2>/dev/null || brew services restart postgresql@15
brew services start redis 2>/dev/null || brew services restart redis
sleep 2

# ── 6. Create database ────────────────────────────────────────────────────
createdb conjunction_db 2>/dev/null && echo -e "${GREEN}✓  Database created${NC}" || echo -e "${GREEN}✓  Database already exists${NC}"

# ── 7. Check Python ───────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo -e "${CYAN}Installing Python 3.11...${NC}"
  brew install python@3.11
fi
PYTHON=$(command -v python3.11 || command -v python3)
echo -e "${GREEN}✓  Python: $($PYTHON --version)${NC}"

# ── 8. Python virtual environment ────────────────────────────────────────
echo -e "${CYAN}Setting up Python virtual environment...${NC}"
cd "$DIR/backend"
$PYTHON -m venv .venv
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo -e "${GREEN}✓  Python dependencies installed${NC}"

# ── 9. Check Node.js ──────────────────────────────────────────────────────
if ! command -v node &>/dev/null; then
  echo -e "${CYAN}Installing Node.js...${NC}"
  brew install node
fi
echo -e "${GREEN}✓  Node.js: $(node --version)${NC}"

# ── 10. Frontend dependencies ────────────────────────────────────────────
echo -e "${CYAN}Installing frontend dependencies...${NC}"
cd "$DIR/frontend"
npm install --silent
echo -e "${GREEN}✓  Frontend dependencies installed${NC}"

# ── 11. Seed demo data ───────────────────────────────────────────────────
echo -e "${CYAN}Loading demo data...${NC}"
cd "$DIR/backend"
source .venv/bin/activate
export SPACETRACK_USER SPACETRACK_PASS
export DATABASE_URL="postgresql+asyncpg://localhost/conjunction_db"
export DATABASE_URL_SYNC="postgresql://localhost/conjunction_db"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="dev-secret-key"
python seed_demo.py && echo -e "${GREEN}✓  Demo data loaded${NC}" || echo -e "${YELLOW}⚠  Demo data skipped (already loaded or error)${NC}"

echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  Setup complete! Now run:  bash start.sh"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
