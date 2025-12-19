#!/bin/bash
set -e

echo "Killing old processes..."
# Kill specific PIDs found earlier just in case
sudo kill -9 257349 283899 283950 283963 || true
# Kill by name
sudo pkill -f uvicorn || true
sudo pkill -f npm || true
sudo pkill -f vite || true
sudo pkill -f python3 || true
sudo pkill -f node || true

# Docker cleanup
if sudo docker ps -q >/dev/null 2>&1; then
    sudo docker stop $(sudo docker ps -aq) || true
    sudo docker rm $(sudo docker ps -aq) || true
fi

echo "Waiting for ports to clear..."
sleep 2

echo "Starting Backend..."
cd ~/html_judge
source venv/bin/activate
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

echo "Starting Frontend..."
cd frontend
nohup sudo npm run preview -- --host 0.0.0.0 --port 80 > frontend.log 2>&1 &

echo "Restart Complete!"
