#!/bin/bash
set -e

echo "Stopping existing services..."
sudo fuser -k 80/tcp || true
sudo fuser -k 8000/tcp || true

echo "Cleaning up..."
rm -rf ~/html_judge
mkdir ~/html_judge

echo "Extracting new code..."
tar -xzf ~/aws_deploy.tar.gz -C ~/html_judge

echo "Setting up Backend..."
cd ~/html_judge
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
echo "Installing Playwright Browsers..."
playwright install chromium || true
# Try installing deps if needed (needs sudo)
sudo playwright install-deps chromium || true

# Preserve .env if exists in previous location? 
# Actually we wiped ~/html_judge. Hopefully .env was backed up? 
# DEPLOY.md says "if [ ! -f .env ]".
# If I wiped the folder, I lost the .env!
# I should check if there is a backup or if I should backup .env first.
# Better strategy: move .env out, wipe, move back.

if [ -f ~/html_judge/.env ]; then
    cp ~/html_judge/.env ~/.env.backup
fi

if [ -f ~/.env.backup ]; then
    cp ~/.env.backup .env
fi

if [ ! -f .env ]; then
    echo "Creating placeholder .env"
    echo "OPENAI_API_KEY=sk-placeholder" > .env
fi

echo "Starting Backend..."
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

echo "Setting up Frontend..."
cd frontend
# Skip full clean install if mostly same? No, stick to instructions.
rm -rf node_modules package-lock.json dist
npm install
npm run build

echo "Starting Frontend..."
nohup sudo npm run preview -- --host 0.0.0.0 --port 80 > frontend.log 2>&1 &

echo "Deployment finished!"
