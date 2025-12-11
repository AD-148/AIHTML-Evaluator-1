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

SYSTEM_PROMPT = """
You are an expert Frontend QA Engineer and AI Judge. 
Your task is to evaluate the provided HTML code snippet based on the following criteria:
1. Fidelity: How 'good' and realistic does the code look? (0-100)
2. Syntax: Is the HTML valid? Are tags closed? (0-100)
3. Accessibility: Does it follow basic accessibility principles? (0-100)

Return the output strictly as a JSON object matching this structure:
{
    "score_fidelity": int,
    "score_syntax": int,
    "score_accessibility": int,
    "rationale": "string explanation",
    "final_judgement": "string summary"
}
"""

async def analyze_html(html_content: str) -> EvaluationResult:
    api_key = os.getenv("OPENAI_API_KEY")
    
    # MOCK MODE: If no API key is set, return a dummy result so the UI can be tested.
    if not api_key:
        print("No API Key found. Returning mock data.")
        return EvaluationResult(
            score_fidelity=85,
            score_syntax=90,
            score_accessibility=60,
            rationale="[MOCK] The HTML structure is generally valid. However, some accessibility attributes like 'alt' for images might be missing. This is a generated mock response because no OpenAI API key was found in the environment variables.",
            final_judgement="Good start, but needs accessibility improvements."
        )

    client = AsyncOpenAI(api_key=api_key)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o", # Or gpt-3.5-turbo
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Evaluate this HTML:\n\n{html_content}"}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        return EvaluationResult(**data)
    
    except Exception as e:
        print(f"Error calling LLM: {e}")
        # Fallback error response
        return EvaluationResult(
            score_fidelity=0,
            score_syntax=0,
            score_accessibility=0,
            rationale=f"Error occurred during LLM evaluation: {str(e)}",
            final_judgement="Evaluation Failed"
        )
