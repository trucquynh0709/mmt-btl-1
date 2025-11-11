#!/bin/bash
# ===================================================
# CO3094 Assignment 1 – Auto Runner
# Launch Proxy, Backend, and WebApp (WeApRous)
# ===================================================

# Exit on error
set -e

echo "=== Starting CO3094 Web Server Stack ==="

# Optional: add project to PYTHONPATH (for imports)
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Start backend
echo "[1/3] Starting backend on port 9000..."
python start_backend.py --server-ip 0.0.0.0 --server-port 9000 &

# Start proxy
echo "[2/3] Starting proxy on port 8080..."
python start_proxy.py --server-ip 0.0.0.0 --server-port 8080 &

# Start webapp
echo "[3/3] Starting webapp (WeApRous) on port 8000..."
python start_sampleapp.py --server-ip 0.0.0.0 --server-port 8000 &

echo "All servers are running in background!"
echo "Access via:"
echo "  Proxy : http://127.0.0.1:8080"
echo "  Backend : http://127.0.0.1:9000"
echo "  WebApp : http://127.0.0.1:8000"
echo "---------------------------------------------"
echo "Press Ctrl+C to stop all servers."

# Keep script alive so Ctrl+C kills background jobs
wait

#sudo fuser -k 8080/tcp 9000/tcp 8000/tcp || true