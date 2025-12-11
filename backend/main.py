from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
try:
    from .llm_service import analyze_html, EvaluationResult
except ImportError:
    from llm_service import analyze_html, EvaluationResult

load_dotenv()

app = FastAPI(title="HTML LLM Judge")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class HTMLInput(BaseModel):
    html_content: str
    model_provider: Optional[str] = "openai" # placeholder for future expansion

@app.get("/")
def read_root():
    return {"message": "HTML LLM Judge API is running"}

@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate_html(input_data: HTMLInput):
    if not input_data.html_content.strip():
        raise HTTPException(status_code=400, detail="HTML content cannot be empty")
    
    try:
        result = await analyze_html(input_data.html_content)
        return result
    except Exception as e:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
