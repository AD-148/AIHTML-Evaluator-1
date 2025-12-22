from fastapi import FastAPI, HTTPException, UploadFile, File
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

@app.post("/batch/process")
async def batch_evaluate(file: UploadFile = File(...)):
    """
    Accepts an Excel file with a 'Prompt' column.
    Generates HTML (via MoEngage Streaming API) and evaluates it.
    Appends results to the ORIGINAL sheet and returns it.
    """
    try:
        # 1. Imports
        import pandas as pd
        from io import BytesIO
        try:
        try:
             from backend.moengage_api import generate_html_from_stream, create_new_session
        except ImportError:
             from moengage_api import generate_html_from_stream, create_new_session

        # 2. Read Valid Excel
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        
        if "Prompt" not in df.columns:
             raise HTTPException(status_code=400, detail="Excel must have a 'Prompt' column (Case-sensitive).")
             
        # 3. Iterate & Process (Preserving Original Rows)
        # We will create lists to populate new columns
        generated_htmls = []
        debug_raw_msgs = []
        debug_full_msgs = []
        debug_api_logs = []
        
        score_fids = []
        score_viss = []
        score_accs = []
        score_resps = []
        score_syns = []
        verdicts = []
        rationales = []
        test_logs = []
        
        for index, row in df.iterrows():
            prompt = str(row['Prompt'])
            logger.info(f"Processing Row {index+1}: {prompt[:30]}...")

            # 1. Capture Raw and Full Prompt
            debug_raw_msgs.append(prompt)
            # Access constant from module dynamically if needed, or import
            try:
                from backend.moengage_api import BYPASS_INSTRUCTION, create_new_session
            except ImportError:
                from moengage_api import BYPASS_INSTRUCTION, create_new_session
            
            debug_full_msgs.append(prompt + BYPASS_INSTRUCTION)

            # A. Create New Session for this Prompt
            session_id = create_new_session()
            if not session_id:
                logger.error(f"Row {index+1}: Failed to create session.")
                # Fallback or Error? 
                # We will mark as Error to be safe, or try without session (api might fail)
                session_id = None 

            # B. Generate HTML with dynamic session
            html_content, api_log = generate_html_from_stream(prompt, session_id)
            debug_api_logs.append(api_log)
            
            # If generation failed completely
            if not html_content:
                generated_htmls.append("GENERATION_FAILED")
                score_fids.append(0)
                score_viss.append(0)
                score_accs.append(0)
                score_resps.append(0)
                score_syns.append(0)
                verdicts.append("ERROR")
                rationales.append("Failed to generate HTML from API.")
                test_logs.append(f"API Error: {api_log}")
                continue

            generated_htmls.append(html_content)

            # B. Evaluate
            try:
                # Reuse existing logic
                eval_result = await analyze_chat([{"role": "user", "content": html_content}])
                
                score_fids.append(eval_result.score_fidelity)
                score_viss.append(eval_result.score_visual)
                score_accs.append(eval_result.score_accessibility)
                score_resps.append(eval_result.score_responsiveness)
                # Ensure syntax score exists if not in model yet, or fallback
                score_syns.append(getattr(eval_result, 'score_syntax', 0))
                
                verdicts.append(eval_result.final_judgement)
                rationales.append(eval_result.rationale)
                
                # Join execution trace
                trace_str = "\n".join(eval_result.execution_trace)
                test_logs.append(trace_str)
                
            except Exception as e:
                logger.error(f"Row {index+1} Eval Failed: {e}")
                score_fids.append(0)
                score_viss.append(0)
                score_accs.append(0)
                score_resps.append(0)
                score_syns.append(0)
                verdicts.append("EVAL_ERROR")
                rationales.append(f"Evaluation Exception: {str(e)}")
                test_logs.append(str(e))
                
        # 4. Append Columns to DataFrame
        # Add Debug Columns First
        df['Debug_Raw_Parsing_Prompt'] = debug_raw_msgs
        df['Debug_Full_API_Prompt'] = debug_full_msgs
        df['Debug_API_Response'] = debug_api_logs
        df['Clean_HTML_Output'] = generated_htmls # Duplicate for clarity
        
        df['Generated_HTML'] = generated_htmls
        df['Score_Fidelity'] = score_fids
        df['Score_Visual'] = score_viss
        df['Score_Accessibility'] = score_accs
        df['Score_Responsiveness'] = score_resps
        df['Score_Syntax'] = score_syns
        df['Verdict'] = verdicts
        df['Rationale'] = rationales
        df['Test_Log'] = test_logs
        
        # 5. Return File
        output_stream = BytesIO()
        df.to_excel(output_stream, index=False)
        output_stream.seek(0)
        
        from fastapi.responses import StreamingResponse
        headers = {
            'Content-Disposition': 'attachment; filename="evaluated_results.xlsx"'
        }
        return StreamingResponse(output_stream, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)

    except Exception as e:
        logger.error(f"Batch Processing Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.staticfiles import StaticFiles

# Create static directory if it doesn't exist (it should)
# Ensure we serve the frontend
# mounted at the end to avoid overriding API routes
# Skip this if running on Vercel, as Vercel handles static files via rewrites
import os
# Static files should be handled by Nginx or Vercel
# app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

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
