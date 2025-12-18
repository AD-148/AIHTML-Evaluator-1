import os
import json
import asyncio
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from dotenv import load_dotenv

from backend.advanced_analysis import AdvancedAnalyzer

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

INPUT:
- User HTML Code
- SYSTEM REPORT (UI Inventory): Count of elements and computed styles (e.g. Real Button Color).

INSTRUCTIONS:
1. **Compare Inventory**: 
   - If User asked for "Blue Button" and Report says "Primary Button Computed Style: rgb(255, 0, 0)" (Red), DEDUCT points.
   - If User asked for "3 Inputs" and Report says "Found 1 Input", DEDUCT points.
2. **Evaluate Dimensions**:
   - **Feature Policing** (Crucial): Check presence of all elements.
   - **Visual Accuracy**: Check styles.

Evaluate two dimensions:
1. **Feature Policing** (Crucial): 
   - Check if ALL requested interactive elements (buttons, inputs, toggles, etc.) are present. 
   - If a specific interactive element is missing, score MUST be < 70 (Major Miss).
2. **Visual Accuracy**:
   - Does the implementation visually match the *description* given by the user? (e.g. "Red button" vs "Blue button").

### SCORING RUBRIC (FEW-SHOT EXAMPLES):
- **Scenario A**: User asked for "Login Form with Google Button". HTML has form but missing Google button.
  - Score: 60
  - Rationale: "Major feature missing (Google Button)."
- **Scenario B**: User asked for "Blue Card". HTML is a Card but background is white (default).
  - Score: 75
  - Rationale: "Functional elements present, but major visual mismatch (Wrong color)."
- **Scenario C**: User asked for "Hero Section". HTML matches description perfectly.
  - Score: 100
  - Rationale: "Perfect match."

Output JSON: {
    "step_by_step_reasoning": "First, I checked... Then I saw...",
    "score_fidelity": int,
    "rationale_fidelity": "string"
}
"""

PROMPT_ACCESSIBILITY = """
You are an expert Accessibility Auditor (WCAG 2.1 AAA).
Your goal is to evaluate the ACCESSIBILITY of the provided HTML based on the provided SYSTEM REPORT.

INPUT:
- User HTML Code
- SYSTEM REPORT (Truth Source): Contains strict logs of missing alts, contrast issues, etc.

INSTRUCTIONS:
1. **Trust the System Report**: If the report says "Image missing alt", it IS missing. Do not debate it.
2. **Score Cap**: The report may define a "Score Cap" (e.g. Max 60). You CANNOT score higher than this cap.
3. **Deductions**:
   - Critical Violations (e.g. missing alt, no labels): -20 points each.
   - Serious Violations (e.g. contrast): -10 points each.
4. **Rationale**:
   - First, list the Critical/Serious violations found by the System.
   - Then, add any manual observations.

Output JSON: {"score_accessibility": int, "rationale_accessibility": "string"}
"""

PROMPT_VISUAL_DESIGN = """
You are a World-Class Creative Director and UI/UX Designer.
Your goal is to ensure the designs are PREMIUM, MODERN, and "WOW" the user.

INPUT:
- User HTML Code
- SYSTEM REPORT (Style DNA): Detected Fonts and CSS Features.

INSTRUCTIONS:
1. **Analyze Signals**:
   - If Report says "Generic/Outdated Font (Times New Roman)", score MUST match "1995 Web" level (< 60).
   - If Report says "Detected Shadows, Gradients", score is boosted (70-90 range depending on harmony).
   - If Report says "flat/basic design", score can max out at 70 (Bootstrap level).

Evaluate PURE AESTHETICS (Ignore functional requirements, focus on looks):
1. **Alignment & Spacing**:
   - Are elements perfectly aligned? Is whitespace consistent?
   - Deduct points for sloppy margins or misalignment.
2. **Visual Appeal**:
   - Is it "pretty" or "generic"? (Generic white/grey box = Max 60 score).
   - Usage of shadows, rounded corners, gradients, glassmorphism.
   - Typography hierarchies (Good contrast, readable fonts).

### SCORING RUBRIC (FEW-SHOT EXAMPLES):
- **Score 95-100**: Modern, ample whitespace, subtle shadows, custom font (Inter/Roboto), consistent color palette. Looks like a Dribbble shot.
- **Score 70-80**: Standard Bootstrap-like look. Clean but boring. Default blue links or buttons.
- **Score 40-60**: "1995 Web". Times New Roman, zero CSS padding, default browser borders. 
- **Score <40**: Broken layout, overlapping text.

Output JSON: {
    "step_by_step_reasoning": "Analyzed alignment... Checked typography...",
    "score_visual": int,
    "rationale_visual": "string"
}
If the design looks like a basic 1990s or 2000s page, score_visual MUST be < 50.
"""

PROMPT_MOBILE_SDK = """
You are a Mobile Platform Engineer specializing in WebView integrations (iOS/Android).
Your goal is to ensure this HTML renders perfectly in a Mobile SDK environment.

INPUT:
- User HTML Code
- SYSTEM REPORT (Truth Source): Logs from a real Mobile Viewport Simulation (iPhone 12).

INSTRUCTIONS:
1. **Trust the Simulation**: 
   - If the log says "Target #1 FAILED TAP", it is a critical failure (-20 pts).
   - If the log says "Runtime Errors Detected", deduct -15 pts.
   - If "LANDSCAPE FAIL" is present, deduct -10 pts.
2. **Evaluate**:
   - **OS Compatibility**: `safe-area-inset`, `-webkit-` prefixes.
   - **Viewport**: Must have correct `<meta name="viewport">`.
   - **Orientation**: Check if design works in both Portrait and Landscape (via logs).
   - **Touch Targets**: Check simulation logs for tappability.
   - **Scrolling**: No horizontal scrolling.

Output JSON: {
    "step_by_step_reasoning": "Checked viewport... Analyzed simulation logs...",
    "score_responsiveness": int,
    "rationale_responsiveness": "string"
}
"""

PROMPT_SYNTAX = """
You are a Senior Frontend Architect.
Evaluate the code quality, syntax validity, and JavaScript interactivity.

INPUT:
- User HTML Code
- SYSTEM REPORT (Syntax Logs): HTML5 Validator & BS4 Structural Checks.

INSTRUCTIONS:
1. **Trust Syntax Logs**:
   - If Report says "Missing <!DOCTYPE>", deduct 10 pts.
   - If Report says "Tags not closed" or "Nesting error", deduct strict points.
2. **Evaluate**:
   - **Clean Code**: Proper nesting, valid tags.
   - **Interactivity**: 
     - If User requested logic (e.g. "Calculate"), check if JS exists and works.
     - No dead script tags.

Output JSON: {
    "step_by_step_reasoning": "Checked tag validity... Verified JS...",
    "score_syntax": int,
    "rationale_syntax": "string",
    "fixed_html": "string (FULL fixed HTML code if improvements needed, else null)"
}
"""

PROMPT_AGGREGATOR = """
You are the Lead Judge.
Aggregate the reports from the 5 specialists (Fidelity, Accessibility, Visual, Mobile SDK, Syntax).

INPUT:
- User HTML Code
- SPECIALIST REPORTS (JSON): Contains both "Analysis Logs" (Tools) and "Agent Scores".

Your Goals:
1. **Synthesize**: Combine the 5 rationales into a structured verdict.
2. **PRIORITIZE TOOL EVIDENCE**: 
   - If 'static_analysis' logs a Critical Error, BUT 'agent_accessibility' ignored it, you MUST side with the TOOL and lower the score.
   - If 'mobile_analysis' says "Failed Tap", but 'agent_mobile_sdk' gave 100, you MUST lower the score.
   - **Ground Truth Hierarchy**: Tool Logs > Agent Opinion.
3. **Conflict Resolution**: If Visual says "Great" but Fidelity says "Missing Feature", side with Fidelity.

Output JSON MUST match this EXACT structure:
{
    "score_fidelity": int,
    "score_syntax": int,
    "score_accessibility": int,
    "score_responsiveness": int,
    "score_visual": int,
    "rationale": "string -> MUST BE MARKDOWN FORMATTED. Use bullet points for each agent's finding, followed by a '### Verdict' section.",
    "final_judgement": "string",
    "fixed_html": "string or null"
}

Format for 'rationale':
### Agent Reports
* **Fidelity**: [Why score?] ...
* **Visual**: [Why score?] ...
* **Mobile**: [Why score?] ...
* **Accessibility**: [Why score?] ...
* **Syntax**: [Why score?] ...

### Verdict
[Final concise summary of the decision, mentioning the biggest blocker if any]
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

    # 2. RUN ADVANCED ANALYSIS
    context_access = ""
    context_mobile = ""
    context_fidelity = ""
    context_visual = ""
    
    if last_html:
        try:
            # Run unified single-pass analysis
            results = analyzer.analyze()
            context_access = results["access"]
            context_mobile = results["mobile"]
            context_fidelity = results["fidelity"]
            context_visual = results["visual"]
        except Exception as e:
            logger.error(f"Advanced Analysis Pipeline Failed completely. Falling back to empty contexts. Error: {e}", exc_info=True)
            context_access = f"System Error: {str(e)}"
            context_mobile = "Mobile Simulation skipped due to error."
            context_fidelity = "Fidelity Check skipped due to error."
            context_visual = "Visual Check skipped due to error."

    # 3. RUN MULTI-AGENT EVALUATION (5 Agents)
    try:
        results = await asyncio.gather(
            _run_agent(client, PROMPT_ACCESSIBILITY, messages, context_access),
            _run_agent(client, PROMPT_VISUAL_DESIGN, messages, context_visual),
            _run_agent(client, PROMPT_MOBILE_SDK, messages, context_mobile),
            _run_agent(client, PROMPT_SYNTAX, messages, context_access),
            _run_agent(client, PROMPT_FIDELITY, messages, context_fidelity)
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
            "static_analysis": context_access,
            "mobile_analysis": context_mobile,
            "fidelity_inventory": context_fidelity,
            "visual_dna": context_visual,
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
        
        # No longer need manual capping here as the Agent Prompt instructions (+ Context) handle it better.
        # But we can keep a safeguard if needed. For now, trusting the "Tool-Augmented" prompt.

        return EvaluationResult(**final_verdict)

    except Exception as e:
        logger.error(f"CRITICAL: Multi-Agent Execution Aggregation Failed. Returning Mock Data. Error: {e}", exc_info=True)
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
                response_format={"type": "json_object"},
                temperature=0.0,
                seed=42
            ),
            timeout=30.0
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Agent Execution Failed for prompt '{system_prompt[:30]}...'. Error: {e}", exc_info=True)
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
