@echo off
echo Starting HTML LLM Judge (Full Stack)...

:: Start Backend
start "Backend API" cmd /k "cd backend && py -m uvicorn main:app --reload --port 8000"

:: Start Frontend (using explicit path just in case)
start "Frontend Dev Server" cmd /k "cd frontend && "C:\Program Files\nodejs\npm.cmd" run dev"

echo.
echo App launching... 
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:5173 (Wait for it to open)
pause
