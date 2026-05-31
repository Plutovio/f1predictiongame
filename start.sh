#!/bin/bash
# start.sh — Render startup script
# Runs migrations, seeds data, syncs results, and starts the web server.
# This runs in the RUNTIME environment so DATABASE_URL is available.

set -e  # Exit on any error

echo ""
echo "========================================"
echo "   F1 Predictor — Startup Sequence"
echo "========================================"
echo ""

# 1. Run database migrations
echo "[1/4] Running database migrations..."
python manage.py migrate --noinput
echo "      Done."

# 2. Seed the 2026 season (teams, drivers, races) — idempotent
echo "[2/4] Seeding 2026 F1 season data..."
python manage.py seed_2026
echo "      Done."

# 3. Sync race results from Jolpica API (lightweight HTTP, no FastF1 download)
echo "[3/4] Syncing F1 race results from Jolpica API..."
python manage.py sync_jolpica --all-rounds || echo "      [WARN] Sync had issues — continuing startup"
echo "      Done."

# 4. Start the production web server
echo "[4/4] Starting Gunicorn web server..."
echo ""
exec gunicorn f1predictor.wsgi --log-file - --timeout 120 --workers 2
