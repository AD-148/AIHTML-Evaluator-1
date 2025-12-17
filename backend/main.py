from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

try:
    from backend.llm_service import analyze_chat, EvaluationResult
except ImportError:
    try:
        from .llm_service import analyze_chat, EvaluationResult
    except ImportError:
         from llm_service import analyze_chat, EvaluationResult

load_dotenv()

app = FastAPI(title="HTML LLM Judge")

# Configure CORS for frontend
# In production, Nginx handles requests as same-origin.
# These origins are mainly for local development.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str

class ChatInput(BaseModel):
    messages: List[Message]
    model_provider: Optional[str] = "openai"

@app.get("/")
def read_root():
    return {"message": "HTML LLM Judge API is running"}

@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate_conversation(input_data: ChatInput):
    if not input_data.messages:
        raise HTTPException(status_code=400, detail="Messages cannot be empty")
    
    try:
        # Convert Pydantic models to dicts
        msgs = [m.model_dump() for m in input_data.messages]
        result = await analyze_chat(msgs)
        return result
    except Exception as e:
        logger.error(f"Error evaluating conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.staticfiles import StaticFiles

# Create static directory if it doesn't exist (it should)
# Ensure we serve the frontend
# mounted at the end to avoid overriding API routes
# Skip this if running on Vercel, as Vercel handles static files via rewrites
import os
if not os.environ.get("VERCEL"):
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    if os.path.exists(frontend_path):
        app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

import logging
import sys

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Backend Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
