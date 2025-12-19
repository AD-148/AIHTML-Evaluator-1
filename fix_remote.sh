#!/bin/bash
set -e

echo "Installing Missing System Dependencies for Playwright..."
# Install common missing deps for Chromium on Amazon Linux 2023 / Fedora
sudo dnf install -y \
    at-spi2-atk \
    atk \
    cairo \
    cups-libs \
    dbus-glib \
    dbus-libs \
    fontconfig \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    pango \
    alsa-lib \
    libxkbcommon \
    libxshmfence \
    mesa-libgbm \
    gtk3

echo "System dependencies installed."

# Verify API Key
cd ~/html_judge
if grep -q "sk-placeholder" .env; then
    echo "WARNING: .env still has placeholder key."
    # Check if there is a .env in the old AIHTML-Evaluator-1 folder?
    if [ -f ~/AIHTML-Evaluator-1/backend/.env ]; then
        echo "Found potential backup in ~/AIHTML-Evaluator-1/backend/.env"
        cp ~/AIHTML-Evaluator-1/backend/.env .env
        echo "Restored .env from backup."
    elif [ -f ~/backend/.env ]; then
        echo "Found potential backup in ~/backend/.env"
        cp ~/backend/.env .env
        echo "Restored .env from backup."
    else 
        echo "CRITICAL: No backup .env found. User must update manually."
    fi
else
    echo ".env appears to have a real key (or at least not the default placeholder)."
fi

echo "Restarting Backend to apply environment changes..."
sudo pkill -f uvicorn || true
source venv/bin/activate
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

echo "Fix complete."
