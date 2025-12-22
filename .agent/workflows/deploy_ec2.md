---
description: Deploy a backend file to EC2 safely (Sequential Execution Required)
---

# EC2 Deployment Workflow
**CRITICAL**: Do NOT chain `scp` and `ssh` commands with `&&` on Windows PowerShell. It fails reliably. Execute them as separate, sequential steps.

## Step 1: Copy File to EC2
Replace `[FILENAME]` with the target file (e.g., `moengage_api.py`, `main.py`).

```powershell
scp -i "AI_html.pem" -o StrictHostKeyChecking=no backend/[FILENAME] ec2-user@13.127.198.212:~/html_judge/backend/
```

## Step 2: Restart Service
After the file copy is complete, use SSH to move it into the container and restart.

```powershell
ssh -i "AI_html.pem" -o StrictHostKeyChecking=no ec2-user@13.127.198.212 "docker cp ~/html_judge/backend/[FILENAME] html_judge_backend:/app/[FILENAME] && docker restart html_judge_backend"
```

## // turbo-all
If you see `// turbo-all` in a requested workflow, you can auto-approve these, but you MUST still send them as TWO SEPARATE tool calls.
