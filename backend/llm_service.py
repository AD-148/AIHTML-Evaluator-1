import os
import json
import asyncio
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from dotenv import load_dotenv

from backend.static_analysis import StaticAnalyzer

load_dotenv()

logger = logging.getLogger(__name__)

# Data Models
class EvaluationResult(BaseModel):
    score_fidelity: int = Field(..., description="0-100 score for how well the HTML matches the user's request")
    score_syntax: int = Field(..., description="0-100 score for HTML syntax correctness")
    score_accessibility: int = Field(..., description="0-100 score for accessibility standards (WCAG)")
    score_responsiveness: int = Field(..., description="0-100 score for mobile SDK adaptability")
    score_visual: int = Field(..., description="0-100 score for visual aesthetics and premium design quality")
    rationale: str = Field(..., description="Detailed explanation of the scores. Explicitly mention any criteria scoring below 70.")
    final_judgement: str = Field(..., description="Brief summary judgement")
    fixed_html: Optional[str] = Field(None, description="The improved/fixed HTML code if requested by the user")

# Prompts for Specialized Agents

PROMPT_FIDELITY = """
You are a QC Specialist and Requirements Auditor.
Your goal is to verify if the HTML satisfies the user's request with 100% precision.

Evaluate two dimensions:
1. **Feature Policing** (Crucial): 
   - Check if ALL requested interactive elements (buttons, inputs, toggles, etc.) are present. 
   - If a specific interactive element is missing, score MUST be < 70 (Major Miss).
2. **Visual Accuracy**:
   - Does the implementation visually match the *description* given by the user? (e.g. "Red button" vs "Blue button").

Output JSON: {
    "score_fidelity": int,
    "rationale_fidelity": "string"
}
"""

PROMPT_ACCESSIBILITY = """
You are an expert Accessibility Auditor (WCAG 2.1 AAA).
Your ONLY goal is to evaluate the ACCESSIBILITY of the provided HTML.
Reference the Static Analysis Report provided in the context. If the report finds errors (missing alt, missing labels), DEDUCT POINTS SEVERELY.
Output JSON: {"score_accessibility": int, "rationale_accessibility": "string"}
Threshold is 70. If issues exist, score MUST be < 70.
"""

PROMPT_VISUAL_DESIGN = """
You are a World-Class Creative Director and UI/UX Designer.
Your goal is to ensure the designs are PREMIUM, MODERN, and "WOW" the user.

Evaluate PURE AESTHETICS (Ignore functional requirements, focus on looks):
1. **Alignment & Spacing**:
   - Are elements perfectly aligned? Is whitespace consistent?
   - Deduct points for sloppy margins or misalignment.
2. **Visual Appeal**:
   - Is it "pretty" or "generic"? (Generic white/grey box = Max 60 score).
   - Usage of shadows, rounded corners, gradients, glassmorphism.
   - Typography hierarchies (Good contrast, readable fonts).

Output JSON: {
    "score_visual": int,
    "rationale_visual": "string"
}
If the design looks like a basic 1990s or 2000s page, score_visual MUST be < 50.
"""

PROMPT_MOBILE_SDK = """
You are a Mobile Platform Engineer specializing in WebView integrations (iOS/Android).
Your goal is to ensure this HTML renders perfectly in a Mobile SDK environment.

Evaluate:
1. **OS Compatibility**: 
   - Check for `safe-area-inset` support for notched phones.
   - Check for `-webkit-` prefixes where needed.
2. **Viewport & Fluidity**: 
   - MUST have `<meta name="viewport" ...>`.
   - CONTAINER WIDTHS which are fixed pixel values > 320px are FAILS. (Score < 60).
3. **Touch Targets**: 
   - Buttons/inputs must be large enough for fingers (>44px height).
4. **Scrolling**: 
   - NO horizontal scrolling allowed.

Output JSON: {
    "score_responsiveness": int,
    "rationale_responsiveness": "string"
}
"""

PROMPT_SYNTAX = """
You are a Senior Frontend Architect.
Evaluate the code quality, syntax validity, and JavaScript interactivity.

Evaluate:
1. **Clean Code**: Proper nesting, valid tags.
2. **Interactivity**: 
   - If User requested logic (e.g. "Calculate"), check if JS exists and works.
   - No dead script tags.

Output JSON: {
    "score_syntax": int,
    "rationale_syntax": "string",
    "fixed_html": "string (FULL fixed HTML code if improvements needed, else null)"
}
"""

PROMPT_AGGREGATOR = """
You are the Lead Judge.
Aggregate the reports from the 5 specialists (Fidelity, Accessibility, Visual, Mobile SDK, Syntax).

Your Goals:
1. **Synthesize**: Combine the 5 rationales into a single coherent verdict.
2. **Standards**: Keep strict WHATWG and W3C standards in mind.
3. **Conflict Resolution**: If Visual says "Great" but Fidelity says "Missing Feature", side with Fidelity for the final verdict summary but keep the scores separate.

Output JSON MUST match this EXACT structure:
{
    "score_fidelity": int,
    "score_syntax": int,
    "score_accessibility": int,
    "score_responsiveness": int,
    "score_visual": int,
    "rationale": "string",
    "final_judgement": "string",
    "fixed_html": "string or null"
}
"""

async def analyze_chat(messages: List[dict]) -> EvaluationResult:
    api_key = os.getenv("OPENAI_API_KEY")
    
    # 1. EXTRACT HTML FROM CONVERSATION
    last_html = ""
    for msg in reversed(messages):
        content = msg.get("content", "")
        if "<div" in content or "<html" in content or "<!DOCTYPE" in content:
            last_html = content
            break
    
    # MOCK/VALIDATION Check
    if not api_key or not api_key.strip().startswith("sk-"):
        return _get_mock_result()

    client = AsyncOpenAI(api_key=api_key)

    # 2. RUN STATIC ANALYSIS
    static_report = {"static_score": 100, "issues": []}
    if last_html:
        try:
            analyzer = StaticAnalyzer(last_html)
            static_report = analyzer.analyze()
        except Exception as e:
            logger.error(f"Static Analysis Failed: {e}")
            static_report["issues"].append(f"Static Analysis Error: {str(e)}")

    # 3. RUN MULTI-AGENT EVALUATION (5 Agents)
    try:
        results = await asyncio.gather(
            _run_agent(client, PROMPT_ACCESSIBILITY, messages, f"Static Analysis Report: {json.dumps(static_report)}"),
            _run_agent(client, PROMPT_VISUAL_DESIGN, messages),
            _run_agent(client, PROMPT_MOBILE_SDK, messages),
            _run_agent(client, PROMPT_SYNTAX, messages),
            _run_agent(client, PROMPT_FIDELITY, messages)
        )
        
        acc_result, vis_result, mob_result, syn_result, fid_result = results
        
        # Normalize keys to prevent "Field required" errors if agents return generic "score"
        _normalize_keys(acc_result, "score_accessibility")
        _normalize_keys(vis_result, "score_visual")
        _normalize_keys(mob_result, "score_responsiveness")
        _normalize_keys(syn_result, "score_syntax")
        _normalize_keys(fid_result, "score_fidelity")

        # 4. LEAD JUDGE AGGREGATION
        # Collect all individual reports
        agent_reports = {
            "static_analysis": static_report,
            "agent_accessibility": acc_result,
            "agent_visual": vis_result,
            "agent_mobile_sdk": mob_result,
            "agent_syntax": syn_result,
            "agent_fidelity": fid_result
        }
        
        # Call the Aggregator to synthesize the final verdict
        final_verdict = await _run_agent(
            client, 
            PROMPT_AGGREGATOR, 
            messages, 
            f"SPECIALIST REPORTS: {json.dumps(agent_reports)}"
        )
        
        # Validate Aggregator Output has all required fields
        required_fields = ["score_fidelity", "score_syntax", "score_accessibility", "score_responsiveness", "score_visual", "rationale", "final_judgement"]
        missing_fields = [f for f in required_fields if f not in final_verdict]

        if missing_fields:
            logger.warning(f"Aggregator output missing fields {missing_fields}. Falling back to manual merging.")
            final_scores = {}
            final_scores.update(acc_result)
            final_scores.update(vis_result)
            final_scores.update(mob_result)
            final_scores.update(syn_result)
            final_scores.update(fid_result)
            
            # Ensure zeroes for any totally missing keys in individual results
            for k in ["score_fidelity", "score_syntax", "score_accessibility", "score_responsiveness", "score_visual"]:
                if k not in final_scores:
                    final_scores[k] = 0

            combined_rationale = (
                f"**Fidelity**: {final_scores.get('rationale_fidelity', 'N/A')}\n"
                f"**Visual Design**: {final_scores.get('rationale_visual', 'N/A')}\n"
                f"**Mobile SDK**: {final_scores.get('rationale_responsiveness', 'N/A')}\n"
                f"**Accessibility**: {final_scores.get('rationale_accessibility', 'N/A')}\n"
                f"**Syntax**: {final_scores.get('rationale_syntax', 'N/A')}\n"
                f"[Note: Lead Judge unavailable, using raw reports.]"
            )
            final_verdict = final_scores
            final_verdict["rationale"] = combined_rationale
            final_verdict["final_judgement"] = "Evaluated by 5 Specialist AI Agents (Lead Judge Unavailable)."
            final_verdict["fixed_html"] = final_scores.get("fixed_html")

        # Fallback if Aggregator fails to return valid JSON or specific fields
        # But generally, we trust the Aggregator. 
        # We enforce the Static Analysis Cap one last time just in case the LLM ignores it, 
        # though the Accessibility Agent should have handled it.
        
        if static_report["issues"] and final_verdict.get("score_accessibility", 100) > static_report["static_score"]:
             final_verdict["score_accessibility"] = static_report["static_score"]
             final_verdict["rationale"] = final_verdict.get("rationale", "") + f" [System Enforced: Accessibility score capped due to static errors.]"

        return EvaluationResult(**final_verdict)

    except Exception as e:
        logger.error(f"Multi-Agent Execution Failed: {e}", exc_info=True)
        return _get_mock_result(error_msg=str(e))

async def _run_agent(client, system_prompt, messages, context_str="") -> Dict:
    """Helper to run a single agent."""
    full_messages = [{"role": "system", "content": system_prompt}]
    if context_str:
        full_messages.append({"role": "system", "content": f"CONTEXT: {context_str}"})
    full_messages.extend(messages)

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o",
                messages=full_messages,
                response_format={"type": "json_object"}
            ),
            timeout=30.0
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Agent failed: {system_prompt[:20]}... Error: {e}")
        # Return error as rationale so it appears in UI
        return {
            "rationale": f"Agent Error: {str(e)}",
            "score": 0
        } 

def _get_mock_result(error_msg=""):
    return EvaluationResult(
        score_fidelity=85,
        score_syntax=90,
        score_accessibility=60,
        score_responsiveness=75,
        score_visual=40,
        rationale=f"[MOCK/ERROR] System returned mock data. {error_msg}. Visual score is low to demonstrate strictness.",
        final_judgement="Mock Result",
        fixed_html="<div>Mock Fixed HTML</div>"
    )

def _normalize_keys(result_dict: Dict, target_score_key: str):
    """
    Helper to ensure the dict has the target_score_key.
    If 'score' exists but target_score_key doesn't, map it.
    If neither exists, default to 0 to prevent validation error.
    """
    if not isinstance(result_dict, dict):
        logger.warning(f"Agent returned non-dict result: {result_dict}")
        result_dict = {}

    if target_score_key not in result_dict:
        if "score" in result_dict:
            result_dict[target_score_key] = result_dict.pop("score")
        else:
            result_dict[target_score_key] = 0
            
    # Ensure all required keys for fallback exist if possible
    # (Mapping rationale if generic 'rationale' key exists but specific one doesn't)
    target_rationale_key = target_score_key.replace("score_", "rationale_")
    if target_rationale_key not in result_dict:
        if "rationale" in result_dict:
             result_dict[target_rationale_key] = result_dict.get("rationale")
        elif "analysis" in result_dict:
             result_dict[target_rationale_key] = result_dict.get("analysis")
        else:
             result_dict[target_rationale_key] = "No rationale provided."
