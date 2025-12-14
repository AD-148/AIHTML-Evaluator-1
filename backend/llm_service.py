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
Your goal is to evaluate HTML code and ASSIST the user in improving it.

CRITICAL: MAINTAIN CONTEXT OF THE HTML CODE.
The conversation history contains the initial HTML and subsequent modifications.
Always analyze the LATEST version of the HTML discussed in the chat history.

Your tasks:
1. Evaluate quality: Fidelity (0-100), Syntax (0-100), Accessibility (0-100).
2. Answer user questions about the code.
3. IMPROVE the code:
    - If the user asks for changes (e.g., "make it blue", "fix the contrast"), you MUST generate the FULL, UPDATED HTML code.
    - Place this full new HTML in the 'fixed_html' JSON field.
    - Do NOT provide snippets. Provide the COMPLETE HTML block so it can be rendered as a preview.
    - If no changes are requested, 'fixed_html' can be null or the current HTML.

Return the output strictly as a JSON object matching this structure:
{
    "score_fidelity": int,
    "score_syntax": int,
    "score_accessibility": int,
    "rationale": "string explanation (answer the user's question here)",
    "final_judgement": "string summary",
    "fixed_html": "string (optional, but REQUIRED if user asks for changes)"
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
