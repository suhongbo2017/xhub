#!/bin/bash
# X-HUB v1.0.0 — Startup Script
cd "$(dirname "$0")"

echo "=== X-HUB Downloader v1.0.0 ==="
echo "Starting server on port 8866..."

# Auto-create & activate venv
if [ ! -d "venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

# Install dependencies
echo "[2/3] Installing requirements..."
pip install -q -r requirements.txt

# Start server
echo "[3/3] Launching uvicorn..."
exec uvicorn server:app --host 0.0.0.0 --port 8866
