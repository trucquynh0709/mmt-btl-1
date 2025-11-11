#!/bin/bash
# ===============================================
# Launch Tracker and 3 Peer Nodes for WeApRous P2P
# ===============================================

# Kill any old instances on same ports (optional but recommended)
sudo lsof -ti :8000,7000,7001,7002 | xargs -r sudo kill -9

echo "Starting Tracker..."
python chat_app.py tracker &
TRACKER_PID=$!

echo "Starting Peer (admin)..."
python chat_app.py peer --port 7000 --username admin &
PEER1_PID=$!

echo "Starting Peer (user1)..."
python chat_app.py peer --port 7001 --username user1 &
PEER2_PID=$!

echo "Starting Peer (user2)..."
python chat_app.py peer --port 7002 --username user2 &
PEER3_PID=$!

# Function to clean up on Ctrl+C
cleanup() {
    echo ""
    echo "Stopping all nodes..."
    kill $TRACKER_PID $PEER1_PID $PEER2_PID $PEER3_PID 2>/dev/null
    sudo lsof -ti :8000,7000,7001,7002 | xargs -r sudo kill -9
    echo "All processes stopped."
    exit 0
}

# Trap Ctrl+C (SIGINT)
trap cleanup SIGINT

echo "Tracker PID: $TRACKER_PID"
echo "Peers running (admin:7000, user1:7001, user2:7002)"
echo "Press Ctrl+C to stop all nodes."

# Keep script alive
wait
