import os
import json
from pydantic import BaseModel, Field
from typing import Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# Data Models
class EvaluationResult(BaseModel):
    score_fidelity: int = Field(..., description="0-100 score for how well the HTML represents the desired output")
    score_syntax: int = Field(..., description="0-100 score for HTML syntax correctness")
    score_accessibility: int = Field(..., description="0-100 score for accessibility standards (WCAG)")
    rationale: str = Field(..., description="Detailed explanation of the scores")
    final_judgement: str = Field(..., description="Brief summary judgement")
    fixed_html: Optional[str] = Field(None, description="The improved/fixed HTML code if requested by the user")

SYSTEM_PROMPT = """
You are an expert Frontend QA Engineer and AI Judge. 
Your task is to evaluate the provided HTML code snippet based on the following criteria:
1. Fidelity: How 'good' and realistic does the code look? (0-100)
2. Syntax: Is the HTML valid? Are tags closed? (0-100)
3. Accessibility: Does it follow basic accessibility principles? (0-100)

If the user asks to FIX or IMPROVE the code, or if you find critical errors, provide the full corrected HTML in the 'fixed_html' field.

Return the output strictly as a JSON object matching this structure:
{
    "score_fidelity": int,
    "score_syntax": int,
    "score_accessibility": int,
    "rationale": "string explanation",
    "final_judgement": "string summary",
    "fixed_html": "string (optional, only if fixes requested)"
}
"""

from typing import List

import logging

logger = logging.getLogger(__name__)

async def analyze_chat(messages: List[dict]) -> EvaluationResult:
    api_key = os.getenv("OPENAI_API_KEY")
    
    # MOCK MODE
    if not api_key:
        logger.warning("No API Key found. Returning mock data.")
        return EvaluationResult(
            score_fidelity=85,
            score_syntax=90,
            score_accessibility=60,
            rationale="[MOCK] This is a mock response because OPENAI_API_KEY is missing. I see your previous messages and applied context.",
            final_judgement="Good start (Mock)"
        )

    client = AsyncOpenAI(api_key=api_key)

    # Prepend system prompt to the conversation history
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=full_messages,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        return EvaluationResult(**data)
    
    except Exception as e:
        logger.error(f"Error calling LLM: {e}", exc_info=True)
        return EvaluationResult(
            score_fidelity=0,
            score_syntax=0,
            score_accessibility=0,
            rationale=f"Error occurred during LLM evaluation: {str(e)}",
            final_judgement="Evaluation Failed"
        )
