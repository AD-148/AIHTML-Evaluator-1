#!/bin/bash
set -e

echo "Stopping services..."
sudo pkill -f uvicorn || true
sudo pkill -f npm || true
sudo pkill -f vite || true

echo "Extracting update..."
tar -xzf ~/aws_deploy.tar.gz -C ~/html_judge

echo "Starting Backend..."
cd ~/html_judge
source venv/bin/activate
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

echo "Starting Frontend..."
cd frontend
# No need to npm install if dependencies haven't changed much, specifically for speed.
# mostly src changes.
nohup sudo npm run preview -- --host 0.0.0.0 --port 80 > frontend.log 2>&1 &

echo "Update Complete!"
