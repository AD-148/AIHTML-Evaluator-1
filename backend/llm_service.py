import os
import json
import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Data Models
class EvaluationResult(BaseModel):
    score_fidelity: int = Field(..., description="0-100 score for how well the HTML represents the desired output")
    score_syntax: int = Field(..., description="0-100 score for HTML syntax correctness")
    score_accessibility: int = Field(..., description="0-100 score for accessibility standards (WCAG)")
    score_responsiveness: int = Field(..., description="0-100 score for mobile responsiveness and adaptability")
    score_visual: int = Field(..., description="0-100 score for visual aesthetics and design quality")
    rationale: str = Field(..., description="Detailed explanation of the scores. Explicitly mention any criteria scoring below 70.")
    final_judgement: str = Field(..., description="Brief summary judgement")
    fixed_html: Optional[str] = Field(None, description="The improved/fixed HTML code if requested by the user")

SYSTEM_PROMPT = """
You are an expert Frontend QA Engineer and AI Judge.
Your goal is to evaluate HTML code and ASSIST the user in improving it.

CRITICAL: MAINTAIN CONTEXT OF THE HTML CODE.
The conversation history contains the initial HTML and subsequent modifications.
Always analyze the LATEST version of the HTML discussed in the chat history.

Your tasks:
1. Evaluate quality on these 5 parameters (0-100):
   - Fidelity: Accuracy to requirements/intent.
   - Syntax: Clenliness and validity of code.
   - Accessibility: WCAG compliance.
   - Responsiveness: Adaptability to different screen sizes (mobile/desktop).
   - Visual: Aesthetics, spacing, typography, and modern design principles.

2. Scoring Logic:
   - Threshold score is 70.
   - If any score is BELOW 70, you MUST explicitly mention it in the 'rationale' and explain why it failed the threshold.

3. Answer user questions about the code.

4. IMPROVE the code:
   - If the user asks for changes or if scores are low and improvements are obvious, generate the FULL, UPDATED HTML code.
   - Place this full new HTML in the 'fixed_html' JSON field.
   - Do NOT provide snippets. Provide the COMPLETE HTML block so it can be rendered as a preview.

Return the output strictly as a JSON object matching this structure:
{
    "score_fidelity": int,
    "score_syntax": int,
    "score_accessibility": int,
    "score_responsiveness": int,
    "score_visual": int,
    "rationale": "string explanation (flag scores < 70 here)",
    "final_judgement": "string summary",
    "fixed_html": "string (optional, but REQUIRED if user asks for changes)"
}
"""

async def analyze_chat(messages: List[dict]) -> EvaluationResult:
    api_key = os.getenv("OPENAI_API_KEY")
    
    # MOCK MODE Check
    # Ensure key is present, non-empty, and looks like a valid OpenAI key
    is_valid_key = api_key and api_key.strip().startswith("sk-") and len(api_key) > 20

    if not is_valid_key:
        logger.warning(f"Invalid or missing API Key ('{api_key if api_key else "None"}'). Returning mock data.")
        return EvaluationResult(
            score_fidelity=85,
            score_syntax=90,
            score_accessibility=60,
            score_responsiveness=75,
            score_visual=80,
            rationale="[MOCK] This is a mock response because OPENAI_API_KEY is missing or invalid. I see your previous messages and applied context. Accessibility is below 70 because aria-labels are missing.",
            final_judgement="Good start (Mock)"
        )

    client = AsyncOpenAI(api_key=api_key)

    # Prepend system prompt to the conversation history
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    try:
        # Wrap the API call with asyncio.wait_for to enforce strict timeout
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o",
                messages=full_messages,
                response_format={"type": "json_object"}
            ),
            timeout=30.0
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        return EvaluationResult(**data)
    
    except asyncio.TimeoutError:
        logger.error("LLM Call Timed Out (30s)")
        return EvaluationResult(
            score_fidelity=85,
            score_syntax=90,
            score_accessibility=60,
            score_responsiveness=75,
            score_visual=80,
            rationale="[TIMEOUT] The AI took too long to respond. Returning mock scores. I've also generated a sample fix below for you to test the UI.",
            final_judgement="Timeout (Mock Fallback)",
            fixed_html="<!-- Mock Fixed HTML -->\n<div class=\"container\" aria-label=\"Sample Container\">\n  <h1>Fixed Version</h1>\n  <p>This is a sample fixed HTML returned by the fallback mode.</p>\n  <form>\n    <label for=\"email\">Email:</label>\n    <input type=\"email\" id=\"email\" name=\"email\" required>\n    <button type=\"submit\">Submit</button>\n  </form>\n  <img src=\"https://via.placeholder.com/150\" alt=\"Placeholder Image\">\n</div>"
        )

    except Exception as e:
        logger.error(f"Error calling LLM: {e}", exc_info=True)
        # Fallback to Mock on error
        return EvaluationResult(
            score_fidelity=85,
            score_syntax=90,
            score_accessibility=60,
            score_responsiveness=75,
            score_visual=80,
            rationale=f"[FALLBACK] Verification failed (Error: {str(e)}). Using mock scores. Accessibility issues detected. Sample fix provided.",
            final_judgement="Good start (Mock Fallback)",
            fixed_html="<!-- Mock Fixed HTML -->\n<div class=\"container\" aria-label=\"Sample Container\">\n  <h1>Fixed Version</h1>\n  <p>This is a sample fixed HTML returned by the fallback mode.</p>\n  <form>\n    <label for=\"email\">Email:</label>\n    <input type=\"email\" id=\"email\" name=\"email\" required>\n    <button type=\"submit\">Submit</button>\n  </form>\n  <img src=\"https://via.placeholder.com/150\" alt=\"Placeholder Image\">\n</div>"
        )
