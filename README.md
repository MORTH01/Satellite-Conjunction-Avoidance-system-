# Conjunction Avoidance System — No Docker Setup

Works on macOS 12 (Monterey) and above. No Docker required.

---

## You need one thing first

Register FREE at: https://www.space-track.org/auth/createAccount
Use your email and a password. That is the only external API.

---

## Setup (run once)

Step 1 — Configure credentials:
  cp .env.example .env
  nano .env
  → Set SPACETRACK_USER and SPACETRACK_PASS

Step 2 — Install everything:
  bash setup.sh
  (installs Homebrew, PostgreSQL, Redis, Python packages, Node packages)

---

## Every time you want to run

  bash start.sh
  → Opens http://localhost:5173 automatically

## Stop

  bash stop.sh

---

## Logs

  tail -f logs/api.log
  tail -f logs/worker.log
  tail -f logs/frontend.log
