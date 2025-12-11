from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sys
import os
import traceback

# Add the parent directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from backend.main import app
except Exception as e:
    # If import fails, create a dummy app to serve the error as JSON
    app = FastAPI()
    error_msg = f"Failed to import backend: {str(e)}\n{traceback.format_exc()}"
    print(error_msg) # Log to Vercel console

    @app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def catch_all(path_name: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Backend Import Failed",
                "detail": error_msg,
                "sys_path": sys.path,
                "cwd": os.getcwd(),
                "listdir": os.listdir(os.getcwd()) if os.path.exists(os.getcwd()) else "cwd not found"
            }
        )
