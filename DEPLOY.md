# HTML Judge Deployment Guide (Amazon Linux 2023)

## Prerequisites
- **EC2 Instance**: Amazon Linux 2023 (t2.medium or larger recommended)
- **Security Group**: Allow TCP Ports `22` (SSH), `80` (Frontend), and `8000` (Backend).
- **SSH Key**: `D:\AI_html.pem` (Local)
- **Local Environment**: Python 3 installed, `package_for_aws.py` present.

---

## Part 1: Prepare & Upload (Run on Local Windows PC)

1.  **Package the Application**
    Open PowerShell in the project folder and run:
    ```powershell
    python package_for_aws.py
    ```
    *This creates `aws_deploy.tar.gz`.*

2.  **Upload to EC2**
    Run this command to send the package to your server:
    ```powershell
    scp -i "D:\AI_html.pem" aws_deploy.tar.gz ec2-user@ec2-13-127-198-212.ap-south-1.compute.amazonaws.com:~/
    ```

---

## Part 2: Clean Install & Launch (Run on EC2 SSH)

**Login to SSH**:
```powershell
ssh -i "D:\AI_html.pem" ec2-user@ec2-13-127-198-212.ap-south-1.compute.amazonaws.com
```

**Run the following block EXACTLY to wipe old versions and restart:**

```bash
# 1. STOP everything (Kill conflicting processes)
sudo fuser -k 80/tcp
sudo fuser -k 8000/tcp
sudo docker stop $(sudo docker ps -aq) 2>/dev/null
sudo docker rm $(sudo docker ps -aq) 2>/dev/null

# 2. CLEANUP old directory
rm -rf ~/html_judge
mkdir ~/html_judge

# 3. EXTRACT new code
tar -xzvf ~/aws_deploy.tar.gz -C ~/html_judge

# 4. SETUP BACKEND
cd ~/html_judge
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# CRITICAL: Address "Mock Data" by adding API Key
if [ ! -f .env ]; then
    echo "OPENAI_API_KEY=sk-placeholder" > .env
    echo "⚠️  EDIT .env FILE NOW TO ADD REAL KEY: nano .env"
fi

# 5. START BACKEND (Background)
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

# 6. SETUP & START FRONTEND (Background)
cd frontend
# Clean install
rm -rf node_modules package-lock.json dist
npm install
npm run build
# Start with Proxy
nohup sudo npm run preview -- --host 0.0.0.0 --port 80 > frontend.log 2>&1 &

echo "Deployment Complete!"
```

---

## Part 3: Verification

1.  Open Browser: **http://13.127.198.212**
2.  Check Title: Should say **"AI HTML Judge v2.0 (5-Agent)"**
3.  Check API: Submit a test. If it fails (Mock Data), check `.env` for API Key.

## Troubleshooting

- **"Address already in use"**: Run `sudo fuser -k 80/tcp` (or 8000).
- **"Timeout"**: Check AWS Security Groups (Port 80/8000 must be Open to 0.0.0.0/0).
- **"501 Not Implemented"**: You are running the simple Python server. Switch to `npm run preview`.
