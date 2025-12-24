import os
import json
import asyncio
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import google.generativeai as genai
from dotenv import load_dotenv

try:
    from backend.advanced_analysis import AdvancedAnalyzer
except ImportError:
    from advanced_analysis import AdvancedAnalyzer

load_dotenv()

logger = logging.getLogger(__name__)

# Explicit Manual Fallback for Docker environment (Robust)
if not os.getenv("GEMINI_API_KEY"):
    logger.info("Env Key Missing. Attempting manual read of /app/.env")
    try:
        if os.path.exists("/app/.env"):
            with open("/app/.env", "r") as f:
                for line in f:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        val = line.strip().split("=", 1)[1]
                        # Remove quotes if present
                        if val.startswith('"') and val.endswith('"'): val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"): val = val[1:-1]
                        os.environ["GEMINI_API_KEY"] = val
                        logger.info("Successfully loaded GEMINI_API_KEY from /app/.env")
                        break
    except Exception as e:
        logger.error(f"Manual .env read failed: {e}")

# Data Models
class EvaluationResult(BaseModel):
    score_fidelity: int = Field(..., description="0-10 score for how well the HTML matches the user's request")
    score_syntax: int = Field(..., description="0-10 score for HTML syntax correctness")
    score_accessibility: int = Field(..., description="0-10 score for accessibility standards (WCAG)")
    score_responsiveness: int = Field(..., description="0-10 score for mobile adaptability")
    score_visual: int = Field(..., description="0-10 score for visual aesthetics and premium design quality")
    score_interactive: int = Field(..., description="0-10 score for SDK interactions and event handling")
    rationale: str = Field(..., description="Detailed explanation of the scores. Explicitly mention any criteria scoring below 70.")
    final_judgement: str = Field(..., description="Brief summary judgement")
    fixed_html: Optional[str] = Field(None, description="The improved/fixed HTML code if requested by the user")
    execution_trace: List[str] = Field(default_factory=list, description="Linear log of all backend tool actions")

# Prompts for Specialized Agents


PROMPT_FIDELITY = """
You are a QC Specialist.
Your goal is to verify if the HTML satisfies the user's request based on the UI Inventory.

INPUT DATA:
1. **User Requirement**: (Summary of what user wanted)
2. **HTML Code**: (The raw code)
3. **UI Inventory**: (List of detected elements: buttons, inputs, headings)

INSTRUCTIONS:
1. **CRITICAL INTENT CHECK (Pass/Fail)**:
   - Compare the 'User Requirement' against the 'UI Inventory'.
   - **FAIL (Score 0-1)**: If the user asked for a "Login Page" but the inventory shows a "Dashboard" or "Article".
   - **Rationale**: Must explicitly state: "Prompt Mismatch: Requested [X], but HTML structure indicates [Y]."
2. **Feature Matching**:
   - Check for specific requested elements (e.g., "Email Input", "Submit Button").
   - If a core element is missing, max score is 5.
3. **Scoring**:
   - **10**: Perfect intent match + All elements present.
   - **8-9**: Intent matches, but placeholder text or minor labels differ.
   - **5-7**: Core feature exists, but missing secondary requirements (e.g., missing "Forgot Password" link).
   - **0-1**: Completely wrong feature.

Output JSON: {
    "step_by_step_reasoning": "string",
    "score_fidelity": int,
    "rationale_fidelity": "string"
}
"""

PROMPT_ACCESSIBILITY = """
You are an Accessibility Auditor.
Calculate the score based strictly on the Axe-Core System Report.
MAX SCORE: 10.

INPUT DATA:
1. **Axe-Core Report**: (JSON list of violations: 'color-contrast', 'image-alt', 'label', etc.)

INSTRUCTIONS:
1. **Violation Calculation (Strict Math)**:
   - Start with **10 Points**.
   - For EACH unique violation type reported by Axe-Core, **SUBTRACT 2 POINTS**.
   - *Example*: If report contains ["color-contrast", "image-alt"], Score = 10 - 2 - 2 = 6.
2. **Critical Failure**:
   - If the report lists "critical" impact violations (like missing form labels), ensure the score does not exceed 6.
3. **Zero Bound**:
   - Minimum score is 0.

Output JSON: {
    "score_accessibility": int,
    "rationale_accessibility": "string"
}
"""

PROMPT_VISUAL_DESIGN = """
You are a Senior UI Designer.
Evaluate the visual quality based on the Computed Style DNA.
MAX SCORE: 10.

INPUT DATA:
1. **Style DNA** (JSON):
   - `typography`: Font family used on body.
   - `button_aesthetics`: Computed styles (padding, radius, shadow) of the primary button.
   - `layout_engine`: The display property of the main container (block, flex, grid).
2. **HTML Code**.

INSTRUCTIONS:
1. **Typography Check (Field: `typography`)**:
   - Check if the font string contains "Times New Roman", "serif" (without specific font), or is empty.
   - **DEDUCT 3** if generic/dated fonts are used.
   - **PASS** if "Inter", "Roboto", "System UI", "Sans-Serif", or specific Google Fonts are found.

2. **Button Sophistication (Field: `button_aesthetics`)**:
   - If value is "No Buttons Found", skip this check (unless user requested a button).
   - **Check Radius**: If `borderRadius` is "0px" (sharp box), it indicates unstyled HTML. **DEDUCT 2**.
   - **Check Padding**: If `padding` is small (e.g., "1px 6px"), it mimics a default browser button. **DEDUCT 2**.
   - **Check Shadow**: If `boxShadow` is "none" AND background is default gray, it looks plain. **DEDUCT 1**.

3. **Layout Logic (Field: `layout_engine`)**:
   - **Check Display**: If `layout_engine` is "block" and the HTML relies on `<br>` tags for spacing, **DEDUCT 2**.
   - **PASS** if `flex` or `grid` is detected.

4. **Scoring Summary**:
   - **10**: Modern fonts + Flex/Grid + styled buttons (padding > 8px, radius > 4px).
   - **7-8**: Good layout but boring typography.
   - **0-6**: "Times New Roman", default gray buttons, or broken layout.

Output JSON: {
    "step_by_step_reasoning": "string",
    "score_visual": int,
    "rationale_visual": "string"
}
"""

PROMPT_MOBILE_SDK = """
You are a Mobile QA Engineer.
Evaluate mobile rendering based on Viewport Logs.
MAX SCORE: 10.

INPUT DATA:
1. **Mobile Simulation Logs**: (Contains 'scrollWidth', 'clientWidth', and element overlaps).

INSTRUCTIONS:
1. **Overflow Check (Horizontal Scroll)**:
   - Scan logs for: "scrollWidth > clientWidth".
   - If `scrollWidth` is significantly larger than `clientWidth` (indicating horizontal scroll), **SCORE = 4 IMMEDIATELY**.
2. **Fixed Width Penalty**:
   - Look for elements with fixed widths (e.g., `width: 800px`) in the CSS/Logs.
   - If fixed width > 350px exists, **DEDUCT 3** (It will break on mobile).
3. **Scoring**:
   - **10**: No overflow, fluid widths (%), media queries present.
   - **7-9**: Minor padding issues detected in logs.
   - **0-6**: Horizontal scroll detected or fixed large widths found.

Output JSON: {
    "step_by_step_reasoning": "string",
    "score_responsiveness": int,
    "rationale_responsiveness": "string"
}
"""

PROMPT_SYNTAX = """
You are a Frontend Architect.
Evaluate code quality.
MAX SCORE: 10.

INPUT DATA:
1. **HTML Code**.
2. **Syntax Logs**: (Console errors regarding parsing).

INSTRUCTIONS:
1. **Structure Check**:
   - Valid DOCTYPE?
   - Properly closed tags?
   - Clean indentation?
2. **Logic Validation**:
   - If User Requirement asked for JS logic (e.g., "calculate total"), check if `<script>` exists.
   - If logic is missing, **DEDUCT 4**.
3. **Scoring**:
   - **10**: Valid, clean, logical.
   - **8**: Minor formatting issues.
   - **<6**: Broken tags, missing required JS logic.

Output JSON: {
    "step_by_step_reasoning": "string",
    "score_syntax": int,
    "rationale_syntax": "string",
    "fixed_html": "string or null"
}
"""

PROMPT_SDK_INTERACTION = """
You are an SDK Integration Specialist.
Analyze the 'Flight Recorder' logs to verify User Interaction Flow.
MAX SCORE: 10.

INPUT DATA:
1. **Interaction Logs**: (List of strings starting with `[MockSDK]`, `[DOM_CHANGE]`, or `[ERROR]`).

INSTRUCTIONS:
1. **Classify Interaction Types**:
   - **Type A: Selection Buttons** (e.g., Ratings, Radio, Options). 
     - **SUCCESS**: If the log shows `[DOM_CHANGE]` (e.g., class changed, "selected" added).
     - **Note**: These do NOT need to trigger `[MockSDK]` immediately.
   - **Type B: Primary Actions** (e.g., Submit, Close, Next).
     - **SUCCESS**: If the log shows `[MockSDK]` event (e.g., `trackEvent`, `dismissMessage`) OR navigation.

2. **Evaluate The Flow**:
   - Look for the "Unlocking" pattern: Did clicking Type A buttons eventually lead to `[DOM_CHANGE] Submit Button is now ENABLED`? 
   - If the Submit button was initially disabled but became enabled after interactions, **SCORE THIS HIGHLY**.

3. **Defect Detection**:
   - **Dead Buttons**: Button clicked -> No `[DOM_CHANGE]` AND No `[MockSDK]`. **DEDUCT 3**.
   - **Broken Submit**: If Submit button is clicked but logic fails (no event). **DEDUCT 3**.

4. **Scoring**:
   - **10**: Perfect Flow (Selections update UI -> Submit triggers SDK).
   - **8**: Buttons react visually, but SDK event is missing on final submit.
   - **5**: Buttons click but show no visual feedback (no class change).
   - **0-3**: JS Errors or unclickable elements.

Output JSON: {
    "step_by_step_reasoning": "string",
    "score_interactive": int,
    "rationale_interactive": "string"
}
"""

PROMPT_AGGREGATOR = """
You are the Lead Judge.
Aggregate the 6 specialist reports into a final verdict.

INPUT:
- Specialist Reports (JSON)

GOAL:
Produce a final JSON with scores (0-10) and a markdown rationale.

Output JSON MUST match:
{
    "score_fidelity": int,
    "score_syntax": int,
    "score_accessibility": int,
    "score_responsiveness": int,
    "score_visual": int,
    "score_interactive": int,
    "rationale": "markdown string",
    "final_judgement": "string",
    "fixed_html": "string or null"
}

Format for 'rationale':
### Agent Reports
* **Fidelity**: ...
* **Visual**: ...
* **Mobile**: ...
* **Accessibility**: ...
* **Syntax**: ...
* **Interactive**: ...

### Verdict
[Summary]
"""

async def analyze_chat(messages: List[dict]) -> EvaluationResult:
    api_key = os.getenv("GEMINI_API_KEY")
    
    # 1. EXTRACT HTML FROM CONVERSATION
    last_html = ""
    user_prompt_summary = "User Request Not Found"
    
    # Iterate backwards to find HTML and the preceding user prompt
    for i, msg in enumerate(reversed(messages)):
        content = msg.get("content", "")
        if "<div" in content or "<html" in content or "<!DOCTYPE" in content:
            last_html = content
            # Try to find the user prompt immediately preceding this
            # Since we are reversing, the "next" item is the one before it in history
            if i + 1 < len(messages):
                 # We need to look at the original list order to be safe, but here we can just grab the next item in reversed list 
                 # which corresponds to the message BEFORE the HTML response.
                 prev_msg = messages[-(i+2)] 
                 if prev_msg.get("role") == "user":
                     user_prompt_summary = prev_msg.get("content", "")[:500] # Truncate for tokens
            break
            
    # Fallback: if no HTML found in history (direct injection?), look at last user message
    if user_prompt_summary == "User Request Not Found":
         for msg in reversed(messages):
             if msg.get("role") == "user":
                 user_prompt_summary = msg.get("content", "")[:500]
                 break

    # MOCK/VALIDATION Check
    if not api_key:
        logger.warning("Mock Mode: Proceeding with Local Analysis before returning mock (Missing GEMINI_API_KEY).")
        api_key = None 

    # Configure Gemini
    if api_key:
        genai.configure(api_key=api_key)

    # 2. RUN ADVANCED ANALYSIS
    context_access = ""
    context_mobile = ""
    context_fidelity = ""
    context_visual = ""
    execution_trace = []
    
    if last_html:
        try:
            # Run unified single-pass analysis
            analyzer = AdvancedAnalyzer(last_html)
            results = await analyzer.analyze()
            context_access = results["access"]
            context_mobile = results["mobile"] # Contains Interaction Logs
            context_fidelity = results["fidelity"]
            context_visual = results["visual"]
            execution_trace = results.get("trace", [])
        except Exception as e:
            logger.error(f"Advanced Analysis Pipeline Failed completely. Falling back to empty contexts. Error: {e}", exc_info=True)
            context_access = f"System Error: {str(e)}"
            context_mobile = "Mobile Simulation skipped due to error."
            context_fidelity = "Fidelity Check skipped due to error."
            context_visual = "Visual Check skipped due to error."
            execution_trace = [f"error: Advanced Analysis Canceled. Exception: {str(e)}"]

    # 3. RUN MULTI-AGENT EVALUATION (6 Agents)
    if not api_key:
        mock = _get_mock_result()
        mock.execution_trace = execution_trace
        logger.info(f"DEBUG: Returning Mock. Captured Trace Length: {len(execution_trace)}")
        print(f"DEBUG: Captured Trace: {execution_trace}")
        return mock
        
    try:
        # Pass User Prompt to Fidelity
        fidelity_context = f"USER PROMPT SUMMARY: {user_prompt_summary}\n\n{context_fidelity}"
        
        # We don't pass a client instance, we just use the configured genai lib
        results = await asyncio.gather(
            _run_agent(PROMPT_ACCESSIBILITY, messages, context_access),
            _run_agent(PROMPT_VISUAL_DESIGN, messages, context_visual),
            _run_agent(PROMPT_MOBILE_SDK, messages, context_mobile),
            _run_agent(PROMPT_SYNTAX, messages, context_access),
            _run_agent(PROMPT_FIDELITY, messages, fidelity_context),
            _run_agent(PROMPT_SDK_INTERACTION, messages, context_mobile) # New Agent
        )
        
        acc_result, vis_result, mob_result, syn_result, fid_result, sdk_result = results
        
        # Normalize keys to prevent "Field required" errors if agents return generic "score"
        _normalize_keys(acc_result, "score_accessibility")
        _normalize_keys(vis_result, "score_visual")
        _normalize_keys(mob_result, "score_responsiveness")
        _normalize_keys(syn_result, "score_syntax")
        _normalize_keys(fid_result, "score_fidelity")
        _normalize_keys(sdk_result, "score_interactive")

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
            "agent_fidelity": fid_result,
            "agent_interactive": sdk_result
        }
        
        # Call the Aggregator to synthesize the final verdict
        final_verdict = await _run_agent(
            PROMPT_AGGREGATOR, 
            messages, 
            f"SPECIALIST REPORTS: {json.dumps(agent_reports)}"
        )
        
        # Validate Aggregator Output has all required fields
        required_fields = ["score_fidelity", "score_syntax", "score_accessibility", "score_responsiveness", "score_visual", "score_interactive", "rationale", "final_judgement"]
        missing_fields = [f for f in required_fields if f not in final_verdict]

        if missing_fields:
            logger.warning(f"Aggregator output missing fields {missing_fields}. Falling back to manual merging.")
            final_scores = {}
            final_scores.update(acc_result)
            final_scores.update(vis_result)
            final_scores.update(mob_result)
            final_scores.update(syn_result)
            final_scores.update(fid_result)
            final_scores.update(sdk_result)
            
            # Ensure zeroes for any totally missing keys in individual results
            for k in ["score_fidelity", "score_syntax", "score_accessibility", "score_responsiveness", "score_visual", "score_interactive"]:
                if k not in final_scores:
                    final_scores[k] = 0

            combined_rationale = (
                f"**Fidelity**: {final_scores.get('rationale_fidelity', 'N/A')}\n"
                f"**Visual Design**: {final_scores.get('rationale_visual', 'N/A')}\n"
                f"**Mobile SDK**: {final_scores.get('rationale_responsiveness', 'N/A')}\n"
                f"**Accessibility**: {final_scores.get('rationale_accessibility', 'N/A')}\n"
                f"**Syntax**: {final_scores.get('rationale_syntax', 'N/A')}\n"
                f"**Interactive**: {final_scores.get('rationale_interactive', 'N/A')}\n"
                f"[Note: Lead Judge unavailable, using raw reports.]"
            )
            final_verdict = final_scores
            final_verdict["rationale"] = combined_rationale
            final_verdict["rationale"] = combined_rationale
            final_verdict["final_judgement"] = "Evaluated by 5 Specialist AI Agents (Lead Judge Unavailable)."
            final_verdict["fixed_html"] = final_scores.get("fixed_html")

        # Fallback if Aggregator fails to return valid JSON or specific fields
        # But generally, we trust the Aggregator. 
        # We enforce the Static Analysis Cap one last time just in case the LLM ignores it, 
        # though the Accessibility Agent should have handled it.
        
        # No longer need manual capping here as the Agent Prompt instructions (+ Context) handle it better.
        # No longer need manual capping here as the Agent Prompt instructions (+ Context) handle it better.
        # But we can keep a safeguard if needed. For now, trusting the "Tool-Augmented" prompt.

        final_verdict["execution_trace"] = execution_trace
        return EvaluationResult(**final_verdict)

    except Exception as e:
        logger.error(f"CRITICAL: Multi-Agent Execution Aggregation Failed. Returning Mock Data. Error: {e}", exc_info=True)
        return _get_mock_result(error_msg=str(e))

async def _run_agent(system_prompt, messages, context_str="") -> Dict:
    """Helper to run a single agent using Gemini 1.5 Pro."""
    # Construct a single comprehensive prompt for Gemini
    # Gemini handles "system instruction" separately, which is great.
    
    # 1. Prepare Content
    chat_history_str = ""
    for m in messages:
         role = m.get("role", "user")
         content = m.get("content", "")
         chat_history_str += f"\n[{role.upper()}]: {content}\n"
         
    final_prompt = f"{chat_history_str}\n\nCONTEXT:\n{context_str}\n\nProduce your analysis in JSON format."

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-pro",
            system_instruction=system_prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        response = await model.generate_content_async(final_prompt)
        content = response.text
        
        # Redundant cleanup just in case, though mime_type should handle it
        if content.strip().startswith("```"):
            content = content.strip().split("\n", 1)[1] if "\n" in content else content
            if content.strip().endswith("```"):
                content = content.strip()[:-3]
        
        return json.loads(content)
    except Exception as e:
        logger.error(f"Agent Execution Failed. Error: {e}", exc_info=True)
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
        fixed_html="<div>Mock Fixed HTML</div>",
        execution_trace=[":rocket: Mock Trace Started", ":mag: Scanning Code...", ":warning: Mock Mode Active"]
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
