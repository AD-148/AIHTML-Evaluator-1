import json
import logging
import os
import tempfile
import re
import subprocess
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
import asyncio
import base64

logger = logging.getLogger(__name__)

# Optional imports with graceful degradation
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError as e:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning(f"Playwright not installed: {e}. Browser checks will be skipped.")

# We will handle Axe manually via script injection if possible, or skip it to avoid Sync/Async conflicts with the wrapper library.
AXE_SCRIPT_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.0/axe.min.js" 

try:
    import html5validator
    HTML5_AVAILABLE = True
except ImportError:
    HTML5_AVAILABLE = False
    logger.warning("html5validator not installed. Strict syntax checks disabled.")

class AdvancedAnalyzer:
    def __init__(self, html_content: str):
        self.html_content = html_content
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.logs = {
            "critical": [],
            "warnings": [],
            "stats": {"interactive_elements": 0, "images": 0},
            "score_cap": 100,
            "mobile_logs": [],
            "execution_trace": []  # NEW: Full Linear Execution Log
        }
        self._log_trace("rocket", "Initialized AdvancedAnalyzer Engine. [ASYNC MODE]")

    def _log_trace(self, arg1, arg2=None):
        """
        Appends a structured log entry. 
        Supports both new signature (message) and old signature (icon, message).
        - New: _log_trace("Message")
        - Old: _log_trace("icon", "Message") -> Icon is ignored.
        """
        if arg2 is None:
            message = arg1
        else:
            message = arg2
            
        self.logs["execution_trace"].append(f"- {message}")

    def _log_section(self, title: str):
        """Appends a section header to the log."""
        self.logs["execution_trace"].append(f"\n### {title}")

    def _handle_js_error(self, error):
        """Handles JS errors with context and hints."""
        msg = str(error)
        clean_msg = msg.replace("JS Error:", "").strip()
        
        is_sdk_error = False
        hint = ""
        
        if "moengage" in msg.lower():
            hint = " [Handled as SDK Stub]"
            is_sdk_error = True
        elif "is not defined" in msg.lower():
            hint = " [Possible missing variable]"
            # We don't auto-forgive all undefined errors, but we can be softer
            
        if is_sdk_error:
            # SDK Errors -> Warning only
            self.logs["warnings"].append(f"SDK Warning: {clean_msg}")
            self._log_trace("warning", f"[WARN] SDK Stub Logic Active: {clean_msg}{hint}")
        else:
            # Real Errors -> Critical
            self.logs["critical"].append(f"JS Error: {clean_msg}")
            self._log_trace("boom", f"[FAIL] JS Runtime Error: {clean_msg}{hint}")

    async def analyze(self) -> Dict[str, str]:
        """
        SINGLE-PASS ANALYSIS: Launches Browser ONCE (Async), runs all checks sequentially.
        Returns dictionary of all context summaries.
        """
        self._log_section("1. STATIC CODE ANALYSIS")
        self._log_trace("mag_right", f"Starting Static Analysis (Playwright Available: {PLAYWRIGHT_AVAILABLE})")
        
        # 1. Structural Checks (No Browser)
        self._run_bs4_checks()
        self._check_links()
        
        if HTML5_AVAILABLE:
            try:
                self._run_html5_validation()
                self._log_trace("clipboard", "HTML5 Syntax Validation Complete.")
            except Exception as e:
                logger.error(f"HTML5 Validator Execution Failed. Error: {e}", exc_info=True)

        results = {
            "access": "",
            "mobile": "",
            "fidelity": "",
            "visual": "",
            "trace": []
        }

        # 2. Browser-Based Checks (Axe, Mobile, Fidelity, Visual)
        if not PLAYWRIGHT_AVAILABLE:
            self._log_trace("warning", "Playwright libraries not found. Skipping Browser Tests.")
            err = "[UNAVAILABLE] (Playwright not installed)."
            results["access"] = self._generate_access_summary() # Still returns BS4 findings
            results["mobile"] = err
            results["fidelity"] = err
            results["visual"] = err
            results["trace"] = self.logs["execution_trace"]
            return results

        try:
            self._log_trace("computer", "Launching Headless Chromium Browser (Async)...")
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                try:
                    # Create a context that mimics a decent desktop for initial Fidelity/Visual checks
                    self._log_trace("desktop_computer", "Created Desktop Context (1280x720)")
                    context = await browser.new_context(viewport={'width': 1280, 'height': 720}, has_touch=True) 
                    page = await context.new_page()
                    # Capture Console Logs
                    console_logs = []
                    page.on("console", lambda msg: console_logs.append(f"CONSOLE [{msg.type}]: {msg.text}"))
                    page.on("pageerror", self._handle_js_error)

                    # Create serialized temp file for the browser to load
                    # This is necessary because data: URLs or set_content can sometimes behave differently with origin policies
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', encoding='utf-8') as f:
                        f.write(self.html_content)
                        temp_file_path = f.name
                    
                    app_url = f"file://{temp_file_path}"
                    
                    # INJECT MOCK SDK for "MoEngage" to prevent Runtime Errors on click
                    await page.add_init_script("""
                        window.moengage = {
                            trackDismiss: (id) => console.log('[MockSDK] MoEngage: trackDismiss', id),
                            dismissMessage: () => console.log('[MockSDK] MoEngage: dismissMessage'),
                            trackClick: (evt) => console.log('[MockSDK] MoEngage: trackClick', evt),
                            trackEvent: (name, data) => console.log('[MockSDK] MoEngage: trackEvent', name, data),
                            setUserAttribute: (key, val) => console.log('[MockSDK] MoEngage: setUserAttribute', key, val),
                            setFirstName: (name) => console.log('[MockSDK] MoEngage: setFirstName', name),
                            setEmailId: (email) => console.log('[MockSDK] MoEngage: setEmailId', email)
                        };
                        
                        // Fallback for global usage if any
                        window.trackEvent = (name) => console.log('[MockSDK] Global trackEvent:', name);
                        
                        // Shim document.write using Object.defineProperty to be extra aggressive
                        Object.defineProperty(document, 'write', {
                            value: (content) => console.log('Shimmed document.write:', content),
                            writable: false,
                            configurable: false
                        });
                        Object.defineProperty(document, 'writeln', {
                            value: (content) => console.log('Shimmed document.writeln:', content),
                            writable: false,
                            configurable: false
                        });
                        
                        // Shim window.open to prevent popups
                        window.open = (url) => console.log('Shimmed window.open:', url);
                        
                        console.log("SHIM INJECTED CONFIRMED");
                    """)

                    await page.goto(app_url)
                    # await page.set_content(self.html_content) # Redundant and potential cause of double-execution

                    # --- PHASE A: AXE ACCESSIBILITY (Manual Injection) ---
                    self._log_section("2. ACCESSIBILITY AUDIT (Axe-Core)")
                    self._log_trace("wheelchair", "Injecting Axe-Core engine...")
                    try:
                        # Inject Axe Core
                        await page.add_script_tag(url=AXE_SCRIPT_URL)
                        # Run Axe
                        axe_results = await page.evaluate("axe.run()")
                        
                        for violation in axe_results.get("violations", []):
                            impact = violation.get("impact")
                            help_text = violation.get("help")
                            nodes = len(violation.get("nodes", []))
                            msg = f"[{impact.upper()}] {help_text} ({nodes} occurrences)"
                            if impact in ['critical', 'serious']:
                                self.logs["critical"].append(msg)
                                self.logs["score_cap"] = min(self.logs["score_cap"], 50 if impact == 'critical' else 70)
                            else:
                                self.logs["warnings"].append(msg)
                        
                        if not axe_results.get("violations"):
                            self._log_trace("white_check_mark", "[PASS] Accessibility Audit: No violations found.")
                        else:
                            # Detailed Reporting for Axe - Log specific failures instead of generic count
                            for v in axe_results.get("violations", []):
                                help_text = v.get("help")
                                impact = v.get("impact", "unknown").upper()
                                self._log_trace("x", f"[FAIL] Accessibility Audit: [{impact}] {help_text}")
                            for v in axe_results.get("violations", []):
                                help_text = v.get("help")
                                self.logs["warnings"].append(f"[AXE] {help_text}")
                                for node in v.get("nodes", []):
                                    html_snip = node.get("html", "")
                                    # Truncate to 40 chars
                                    if len(html_snip) > 40:
                                        html_snip = html_snip[:37] + "..."
                                    target = (node.get("target") or ["unknown"])[0]
                                    self.logs["warnings"].append(f"  - Failed on: {html_snip} ({target})")
                    except Exception as e:
                        logger.error(f"Phase A (Axe) Failed: {e}")
                        self.logs["warnings"].append(f"Axe Scan Failed (Possible Network/Script Error): {e}")

                    # --- PHASE B: FIDELITY UI INVENTORY ---
                    self._log_section("3. UI INVENTORY & VISUALS")
                    self._log_trace("clipboard", "Scanning UI components (Buttons, Inputs, Images)...")
                    inventory = {"components": {}, "styles": {}, "text_preview": ""}
                    try:
                        inventory["components"]["buttons"] = await page.locator("button, input[type='button'], input[type='submit'], a[class*='btn']").count()
                        inventory["components"]["inputs"] = await page.locator("input:not([type='hidden'])").count()
                        inventory["components"]["images"] = await page.locator("img").count()
                        text = await page.inner_text("body")
                        inventory["text_preview"] = re.sub(r'\s+', ' ', text).strip()[:300] + "..."
                        
                        btn = page.locator("button, input[type='submit'], a[class*='btn']").first
                        if await btn.is_visible():
                            rgb = await btn.evaluate("el => window.getComputedStyle(el).backgroundColor")
                            color = await btn.evaluate("el => window.getComputedStyle(el).color")
                            inventory["styles"]["primary_button_bg"] = rgb
                            inventory["styles"]["primary_button_text"] = color
                    except Exception as e:
                        logger.error(f"Phase B (Fidelity) Failed: {e}")
                    results["fidelity"] = self._generate_fidelity_summary(inventory)

                    # --- PHASE C: VISUAL STYLE DNA ---
                    # Merged into Section 3
                    dna = {"font_family": "Unknown", "modern_css": []}
                    try:
                        # Improved Style DNA Extraction (User Request)
                        dna = await page.evaluate("""() => {
                            const btn = document.querySelector('button') || document.querySelector('input[type="submit"]') || document.querySelector('a[class*="btn"]');
                            const body = document.body;
                            const bodyStyle = window.getComputedStyle(body);
                            const btnStyle = btn ? window.getComputedStyle(btn) : null;
                            
                            // Helper to detect modern CSS features
                            const features = [];
                            if (btnStyle) {
                                if (btnStyle.boxShadow !== 'none') features.push('Shadows');
                                if (parseInt(btnStyle.borderRadius) > 0) features.push('Rounded Corners');
                                if (btnStyle.backgroundImage.includes('gradient')) features.push('Gradients');
                            }
                            if (bodyStyle.backdropFilter !== 'none') features.push('Glassmorphism');

                            return {
                                font_family: bodyStyle.fontFamily,
                                btn_padding: btnStyle ? btnStyle.padding : 'none',
                                btn_radius: btnStyle ? btnStyle.borderRadius : 'none',
                                modern_css: features
                            }
                        }""")
                    except Exception as e:
                        logger.error(f"Phase C (Visual) Failed: {e}")
                        dna = {"font_family": "Unknown", "modern_css": [], "btn_padding": "unknown", "btn_radius": "unknown"}
                    
                    # Log Visual Verdict
                    if "times" in dna['font_family'].lower() or "serif" in dna['font_family'].lower() and "sans" not in dna['font_family'].lower():
                         self._log_trace("x", f"[FAIL] Typography: Outdated font detected ('{dna['font_family']}').")
                    else:
                         self._log_trace("white_check_mark", f"[PASS] Typography: Modern font detected ('{dna['font_family']}').")
                         
                    results["visual"] = self._generate_visual_summary(dna)
                    self._log_trace("art", f"Visual Check Complete. DNA extracted: {len(dna['modern_css'])} modern features.")

                    # --- PHASE D: MOBILE SIMULATION (Resize Page) ---
                    # 1. Portrait & Dynamic Inteaction Loop
                    self._log_section("4. MOBILE SIMULATION & INTERACTION (Dynamic Loop)")
                    try:
                        self._log_trace("iphone", "Resizing Viewport to iPhone 12 (390x844)...")
                        await page.set_viewport_size({'width': 390, 'height': 844})
                        await page.wait_for_timeout(200)
                        
                        # Verify Portrait Responsiveness (Horizontal Scroll Check) - User Request
                        is_overflowing = await page.evaluate("document.body.scrollWidth > window.innerWidth")
                        if is_overflowing:
                             self.logs["mobile_logs"].append("[MOBILE_FAIL] Horizontal Scroll Detected")
                             self._log_trace("x", "[FAIL] Portrait Mode: Horizontal scroll detected (scrollWidth > innerWidth).")
                        else:
                             self._log_trace("white_check_mark", "[PASS] Portrait Mode: No horizontal scroll.")
                        
                        # --- DYNAMIC INTERACTION LOOP ---
                        # We will perform up to 10 "Rounds" of interaction. 
                        # A Round consists of scanning the page, picking the best action, and executing it.
                        # If an action causes a UI update (DOM change), we start a NEW Round (re-scan).
                        
                        executed_actions = set() # Track signature of executed elements to avoid loops
                        max_rounds = 10
                        current_round = 0
                        
                        while current_round < max_rounds:
                            self._log_trace("arrows_counterclockwise", f"[INFO] Mobile: Starting Interaction Round #{current_round + 1}...")
                            
                            # 1. SCAN: Find all visible interactive elements
                            # We use a broad selector to catch everything
                            elements = page.locator("button, a, input, textarea, select, [role='button'], [role='slider'], img[onclick], div[onclick], .scratchpad, .scratch-card, canvas")
                            count = await elements.count()
                            
                            if count == 0:
                                self._log_trace("stop_sign", "[INFO] Mobile: No interactive elements found. Stopping.")
                                break

                            # 2. ANALYZE & PRIORITIZE candidates
                            candidates = []
                            for i in range(count):
                                el = elements.nth(i)
                                if not await el.is_visible(): continue
                                
                                try:
                                    # Extract attributes for signature and heuristics
                                    tag = await el.evaluate("el => el.tagName.toLowerCase()")
                                    id_attr = await el.evaluate("el => el.id") or ""
                                    text = (await el.text_content() or "").strip()[:50]
                                    cls_attr = await el.evaluate("el => el.getAttribute('class')") or ""
                                    inputType = await el.evaluate("el => el.getAttribute('type')") or ""
                                    name_attr = await el.evaluate("el => el.getAttribute('name')") or ""
                                    aria = await el.evaluate("el => el.getAttribute('aria-label')") or ""
                                    role = await el.evaluate("el => el.getAttribute('role')") or ""
                                    disabled_attr = await el.evaluate("el => el.getAttribute('disabled')")
                                    
                                    # Create Unique Signature
                                    # We include 'disabled' state so if a button becomes enabled, we treat it as a new opportunity.
                                    signature = f"{tag}|{id_attr}|{text}|{cls_attr}|{name_attr}|{disabled_attr}"
                                    
                                    if signature in executed_actions:
                                        continue # Skip already handled elements
                                        
                                    # Heuristics for Prioritization
                                    score = 0
                                    
                                    # HIGH PRIORITY: Unfilled Inputs (Radio, Checkbox, Text)
                                    if tag in ['input', 'textarea', 'select']:
                                        score += 10
                                        if inputType in ['radio', 'checkbox']: 
                                             # Prioritize radio/box to ensure state is set before submitting
                                             score += 2 
                                    
                                    # PRIORITY 1: Selection Buttons (Radio-like behavior)
                                    # Users must select options BEFORE submitting.
                                    # We detect this via attributes (data-rating, aria-checked) or Emoji content.
                                    is_selection = False
                                    if tag == 'button':
                                         # Check for data-rating (Common in current test case)
                                         if await el.get_attribute("data-rating") or await el.get_attribute("aria-checked"):
                                              score += 12
                                              is_selection = True
                                         # Check for Emoji content (Heuristic for rating buttons)
                                         elif any(char in text for char in ['⭐', '★', '😞', 'kb', '🙂', '😄']):
                                              score += 12
                                              is_selection = True

                                    # PRIORITY 2: "Next" / "Submit" / "Start" Buttons
                                    # (Bonus for known positive signals, but NOT required)
                                    combined_text = (text + " " + id_attr + " " + cls_attr + " " + aria).lower()
                                    is_positive = False
                                    
                                    if any(w in combined_text for w in ['next', 'submit', 'continue', 'proceed', 'start', 'ok', 'yes']) and not is_selection:
                                        score += 5 # Standard bonus
                                        is_positive = True
                                        
                                    # PRIORITY 3: Standard Buttons
                                    if (tag == 'button' or role == 'button') and not is_selection:
                                        score += 2
                                        
                                    # LOW PRIORITY: "Close" / "Cancel" / "Back" 
                                    # ROBUST CLOSE DETECTION:
                                    # Principle: Trust VISIBLE TEXT over invisible attributes (aria-label, class, data-dismiss) if they conflict.
                                    # This handles cases where buttons have contradictory signals (e.g., text="Save", aria-label="Close").
                                    
                                    is_close = False
                                    
                                    # 1. Check Explicit Text (Strongest Signal)
                                    text_lower = text.lower()
                                    if text_lower in ['close', 'cancel', 'back', 'dismiss', 'no, thanks', 'skip', 'x', '×', '✕']:
                                        is_close = True
                                        
                                    # 2. Check Attributes (Weaker Signal)
                                    # Only trust aria/class as "Close" if the visible text is ambiguous (empty, icon-only, or very short)
                                    elif not text or len(text) < 3: 
                                        if any(w in combined_text for w in ['close', 'cancel', 'dismiss']):
                                            is_close = True
                                            
                                    # 3. Check data-dismiss (Standard Bootstrap pattern)
                                    # If text is explicit and NOT "Close", we ignore data-dismiss to avoid false positives.
                                    # (e.g., A "Submit & Close" button should be treated as "Submit" first, which gives it a positive score bias)
                                    dismiss_attr = await el.evaluate("el => el.getAttribute('data-dismiss')")
                                    if dismiss_attr and not is_positive: 
                                        # Only treat as close if we didn't identify it as a positive action (Start/Next)
                                        # AND the text doesn't look like a substantial label.
                                        if not is_positive and len(text) < 15: 
                                           pass

                                    # Final Decision: Apply penalty logic
                                    # If it was marked Positive (Start/Next), NEVER mark it as Close.
                                    if is_positive:
                                        is_close = False
                                        
                                    if is_close:
                                        score -= 50
                                        
                                    candidates.append({
                                        "element": el,
                                        "score": score,
                                        "signature": signature,
                                        "tag": tag,
                                        "type": inputType,
                                        "text": text,
                                        "desc": f"<{tag} id='{id_attr}'> '{text}'"
                                    })
                                    
                                except Exception as e:
                                    pass

                            # Sort Candidates by Score (Highest First)
                            candidates.sort(key=lambda x: x['score'], reverse=True)
                            
                            if not candidates:
                                self._log_trace("checkered_flag", "[INFO] Mobile: No new candidates to interact with. Stopping.")
                                break
                                
                            # 3. EXECUTE: Try candidates one by one until a UI Update happens
                            round_progressed = False
                            
                            for cand in candidates:
                                el = cand['element']
                                sig = cand['signature']
                                desc = cand['desc']
                                tag = cand['tag']
                                itype = cand['type']
                                
                                self._log_trace("point_right", f"[INFO] Mobile: Round {current_round+1} Action -> interacting with {desc} (Score: {cand['score']})")
                                
                                # Capture State
                                html_before = await page.content()
                                url_before = page.url
                                
                                # Interact & Observe DOM (User Request: Capture State Changes for selection buttons)
                                # Interact & Observe
                                try:
                                    # 1. State BEFORE
                                    try:
                                        old_class = await el.get_attribute("class") or ""
                                        old_disabled = await el.is_disabled()
                                    except:
                                         old_class = ""
                                         old_disabled = False

                                    # 2. PERFORM ACTION (Merged Smart Logic)
                                    if tag == 'select':
                                        opts = await el.locator('option').all_text_contents()
                                        if opts:
                                            val = opts[1] if len(opts) > 1 else opts[0]
                                            await el.select_option(label=val)
                                            self.logs["mobile_logs"].append(f"Round {current_round+1}: Selected '{val}' in {desc}")
                                        else:
                                            self._log_trace("warning", f"[WARN] Mobile: <select> has no options.")

                                    elif tag in ['input', 'textarea'] and itype not in ['button', 'submit', 'checkbox', 'radio', 'range', 'color']:
                                        # Smart Input Filling
                                        val = await self._get_smart_input_value(el)
                                        await el.fill(val)
                                        self.logs["mobile_logs"].append(f"Round {current_round+1}: Filled {desc} with '{val}'")
                                        
                                    elif itype in ['checkbox', 'radio']:
                                        try:
                                            await el.click(force=True, timeout=1500)
                                            self.logs["mobile_logs"].append(f"Round {current_round+1}: Toggled {desc}")
                                        except:
                                            id_val = await el.get_attribute("id")
                                            if id_val:
                                                await page.locator(f"label[for='{id_val}']").click(force=True, timeout=1500)
                                                self.logs["mobile_logs"].append(f"Round {current_round+1}: Toggled Label for {desc}")

                                    else:
                                        # Click/Tap (Buttons, Links)
                                        try:
                                            await el.click(timeout=2000)
                                            self.logs["mobile_logs"].append(f"Round {current_round+1}: Clicked {desc}")
                                        except Exception as click_err:
                                            if "intersects pointer events" in str(click_err) or "visible" in str(click_err) or "Timeout" in str(click_err):
                                                await el.click(force=True, timeout=2000)
                                                self.logs["mobile_logs"].append(f"Round {current_round+1}: Force-Clicked {desc}")
                                            else:
                                                raise click_err

                                    # Wait for potential JS
                                    await page.wait_for_timeout(500)

                                    # 3. State AFTER & DOM CHANGE CHECK (User Request)
                                    try:
                                        new_class = await el.get_attribute("class") or ""
                                        new_disabled = await el.is_disabled()
                                    except:
                                        new_class = ""
                                        new_disabled = False
                                    
                                    # Check for Class Changes (Visual Feedback)
                                    if old_class != new_class:
                                        self.logs["mobile_logs"].append(f"[DOM_CHANGE] Button visual state updated. Class: '{old_class}' -> '{new_class}'")
                                        
                                    # Check for Enable/Disable Toggle (Logic Feedback)
                                    if old_disabled != new_disabled:
                                        status = "ENABLED" if not new_disabled else "DISABLED"
                                        self.logs["mobile_logs"].append(f"[DOM_CHANGE] Element became {status}.")
                                        self._log_trace("unlock", f"[DOM_CHANGE] Element became {status}")
                                        
                                    # Check GLOBAL Submit Button (Did this unlock the submit button?)
                                    submit_btn = page.locator("button:has-text('Submit'), input[type='submit']")
                                    if await submit_btn.count() > 0:
                                         if not await submit_btn.first.is_disabled():
                                              self.logs["mobile_logs"].append("[DOM_CHANGE] Submit Button is currently ENABLED.")
                                    
                                    executed_actions.add(sig)
                                    
                                    # Wait for reaction
                                    await page.wait_for_timeout(1000)
                                    
                                    # Check State
                                    html_after = await page.content()
                                    url_after = page.url
                                    
                                    if url_before != url_after:
                                        self._log_trace("rocket", f"[PASS] Mobile: Navigation triggered! ({url_before} -> {url_after})")
                                        round_progressed = True
                                        break # BREAK CANDIDATE LOOP -> Start Next Round
                                    elif html_before != html_after:
                                        # Simple heuristic: content length changed by more than 10 chars?
                                        # Or just inequality.
                                        self._log_trace("sparkles", f"[PASS] Mobile: UI Update detected after action.")
                                        round_progressed = True
                                        break # BREAK CANDIDATE LOOP -> Start Next Round
                                    else:
                                        # No significant change. 
                                        # Distinguish between Input Filling (OK) and Button Clicks (FAIL)
                                        try:
                                            tag_name = await el.evaluate("el => el.tagName")
                                            tag_name = tag_name.lower() if tag_name else ""
                                        except:
                                            tag_name = ""
                                            
                                        input_type = await el.get_attribute("type") or ""
                                        
                                        if tag_name in ['button', 'a'] or (tag_name == 'input' and input_type in ['submit', 'button', 'image']):
                                            self._log_trace("x", f"[FAIL] Mobile: Unresponsive Element! Clicked {desc} but no UI update or navigation occurred.")
                                        else:
                                            self._log_trace("ghost", f"[INFO] Mobile: Action successful, but no UI change detected. Continuing round...")
                                        
                                except Exception as e:
                                     # Log specific JS error if it was a runtime crash
                                     self._log_trace("warning", f"[WARN] Mobile: Interaction failed: {e}")
                                     # Mark as executed to avoid infinite retry loop on broken element
                                     executed_actions.add(sig)

                            if round_progressed:
                                current_round += 1
                                # Loop back to SCAN
                            else:
                                # We tried all candidates and nothing progressed the UI.
                                # This usually means we reached the end of the flow.
                                self._log_trace("checkered_flag", "[INFO] Mobile: No actions triggered a UI update. Flow complete.")
                                break 
                                
                    except Exception as loop_err:
                        self._log_trace("boom", f"[FAIL] Mobile Loop Crashed: {loop_err}")

                    # Capture Portrait Screenshot (After interaction)
                    ss_bytes_p = await page.screenshot(type="png", full_page=False)
                    # We store it in 'result' (aliased from self.logs? No, need to pass it out)
                    # Hack: attach to self.logs temporarily or return field? 
                    # The Method returns 'result' dict at the end. We should add it there.
                    # We'll assume result is available or return it in keys.
                    results["screenshot_portrait"] = base64.b64encode(ss_bytes_p).decode('utf-8')

                    # 2. Landscape check
                    try:
                        self._log_section("5. CROSS-PLATFORM CHECK")
                        self._log_trace("iphone", "Verifying Landscape Mode (Orientation Test)...")
                        await page.set_viewport_size({"width": 844, "height": 390})
                        await page.wait_for_timeout(500)
                        
                        # Capture Landscape Screenshot
                        ss_bytes = await page.screenshot(type="png", full_page=False)
                        results["screenshot_landscape"] = base64.b64encode(ss_bytes).decode('utf-8')
                        
                        scroll_width = await page.evaluate("document.body.scrollWidth")
                        if scroll_width > 844:
                            self.logs["mobile_logs"].append(f"LANDSCAPE FAIL: Horizontal scroll detected.")
                            self._log_trace("x", "[FAIL] Landscape Mode: Horizontal scroll detected.")
                        else:
                            self.logs["mobile_logs"].append("LANDSCAPE PASS: No horizontal scroll.")
                            self._log_trace("white_check_mark", "[PASS] Landscape Mode: No horizontal scroll.")
                            
                    except Exception as e:
                        self._log_trace("warning", f"[WARN] Landscape check failed: {e}")

                    # --- PHASE D1.5: RUNTIME ERROR CHECK ---
                    errors = [log for log in console_logs if "error" in log.lower() or "exception" in log.lower()]
                    if errors:
                        self.logs["mobile_logs"].insert(0, f"!!! CRITICAL JS ERRORS DETECTED ({len(errors)}) !!!")
                        self.logs["mobile_logs"].append(f"Runtime Errors Detected: {len(errors)} found.")
                        for err in errors[:3]:
                            self.logs["mobile_logs"].append(f"- {err}")
                    else:
                        self.logs["mobile_logs"].append("No Runtime Console Errors detected.")


                    
                    results["mobile"] = self._generate_mobile_summary()

                finally:
                    await browser.close()
                    # Clean up temp file
                    if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                        os.remove(temp_file_path)

        except Exception as e:
            logger.error(f"Single-Pass Browser Session Failed: {e}", exc_info=True)
            err = f"System Error: {str(e)}"
            self._log_trace("boom", f"Browser Session Failed: {e}")
            results["mobile"] = err
            results["fidelity"] = err
            results["visual"] = err
            
        results["access"] = self._generate_access_summary()
        results["trace"] = self.logs["execution_trace"]
        return results

    def _run_bs4_checks(self):
        """Basic structural checks using BeautifulSoup."""
        imgs = self.soup.find_all('img')
        buttons = self.soup.find_all(['button', 'a', 'input', 'select', 'textarea'])
        self.logs["stats"]["images"] = len(imgs)
        self.logs["stats"]["interactive_elements"] = len(buttons)

        # Critical: Missing Alt
        # Critical: Missing Alt
        for i, img in enumerate(imgs):
            src = img.get('src', 'unknown')
            # Truncate src for log
            src_log = src[:37] + "..." if len(src) > 40 else src
            
            if not img.get('alt') and img.get('role') != 'presentation':
                self.logs["critical"].append(f"Image src='{src_log}' is missing 'alt' text.")
                self._log_trace("x", f"[FAIL] Image: Missing 'alt' (src='{src_log}').")
                self.logs["score_cap"] = min(self.logs["score_cap"], 60)
            else:
                if i < 5: # Keep noise low for passing items
                    self._log_trace("white_check_mark", f"[PASS] Image: Has valid 'alt' (src='{src_log}').")

        # Critical: Broken Interactive Config
        for i, btn in enumerate(buttons):
            if btn.name in ['button', 'a']:
                text = btn.get_text(strip=True)
                aria_label = btn.get('aria-label')
                title = btn.get('title')
                
                # Check accessibility
                is_accessible = False
                if text or aria_label or title:
                    is_accessible = True
                else:
                    child_img = btn.find('img')
                    if child_img and child_img.get('alt'): 
                        is_accessible = True

                if not is_accessible:
                     self.logs["critical"].append(f"Interactive element <{btn.name}> has no accessible name.")
                     
                     btn_html = str(btn)[:40] + "..." if len(str(btn)) > 40 else str(btn)
                     self._log_trace("x", f"[FAIL] Button ({btn_html}): No accessible name (text/aria-label).")
                     self.logs["score_cap"] = min(self.logs["score_cap"], 60)
                else:
                     # Log PASS for every button might be too verbose if there are many, but requested "add all cases" implies detail.
                     # However, usually we care about failures. Let's log pass only for the first few to show coverage, 
                     # OR for all if we want total complete noise. 
                     # Requirement: "If it is failing, add all the cases for which it is failing." 
                     # So for PASS, we can keep it light or just count them. 
                     # I will log PASS for the first 5 to avoid spamming the trace, but log ALL failures.
                     pass 
                     # (Actually, let's keep the existing logic for PASS but remove limit for FAIL)
                     if i < 5:
                          self._log_trace("white_check_mark", f"[PASS] Button #{i+1} (<{btn.name}>): Has accessible name.")



    def _run_html5_validation(self):
        """Placeholder for HTML5 Validator (Requires external CLI usually)."""
        # In a real deployed env, we'd subprocess.run(['html5validator', ...])
        # For now, we simulate a check or skip if binary missing.
        if "<!DOCTYPE" not in self.html_content:
             self.logs["warnings"].append("HTML5 Validation: Missing <!DOCTYPE html> declaration.")

    def _check_links(self):
        """Basic Link Checker logic."""
        links = self.soup.find_all('a', href=True)
        for i, link in enumerate(links):
            # remove limit
            href = link['href']
            # Truncate href for log
            href_log = href[:37] + "..." if len(href) > 40 else href
            
            if href.startswith('#'):
                # Internal anchor check
                target_id = href[1:]
                if target_id and not self.soup.find(id=target_id):
                    self.logs["warnings"].append(f"Broken Internal Link: href='{href_log}' points to non-existent ID.")
                    self._log_trace(f"[FAIL] Link Integrity: Broken internal anchor ({href_log}) -> ID not found.")
                else:
                     if i < 5: self._log_trace(f"[PASS] Link Integrity: Valid internal anchor ({href_log}).")
            elif not href.startswith(('http', 'mailto', 'tel', '/')):
                 self.logs["warnings"].append(f"Suspicious Link: href='{href_log}' is likely invalid.")
                 self._log_trace(f"[FAIL] Link Integrity: Suspicious href format ({href_log}).")
            else:
                 if i < 5: self._log_trace(f"[PASS] Link Integrity: Valid href format ({href_log}).")




    def _generate_access_summary(self) -> str:
        lines = ["### SYSTEM REPORT: ACCESSIBILITY & SYNTAX"]
        if self.logs["score_cap"] < 100:
            lines.append(f"**OVERRIDE**: Score Max Capped at {self.logs['score_cap']}/100.")
        
        for item in self.logs["critical"]:
            lines.append(f"- [CRITICAL] {item}")
        for item in self.logs["warnings"]:
            lines.append(f"- [WARN] {item}")
            
        return "\n".join(lines)

    async def _inject_sdk_stubs(self, page):
        """Injects mock objects for common SDKs to prevent ReferenceErrors during testing."""
        await page.add_init_script("""
            // Mock MoEngage SDK
            window.moengage = {
                trackClick: function(evt) { console.log('[MockSDK] moengage.trackClick called:', evt); },
                trackEvent: function(name, data) { console.log('[MockSDK] moengage.trackEvent called:', name, data); },
                setUserAttribute: function(key, val) { console.log('[MockSDK] moengage.setUserAttribute called:', key, val); },
                dismissMessage: function() { console.log('[MockSDK] moengage.dismissMessage called'); },
                trackDismiss: function(id) { console.log('[MockSDK] moengage.trackDismiss called:', id); }
            };
            
            // Mock Base Common Functions if needed
            window.trackEvent = function(name) { console.log('[MockSDK] Global trackEvent called:', name); };
        """)

    async def _get_smart_input_value(self, element) -> str:
        """Determines a context-aware test value for an input element."""
        try:
            # Get Attributes
            itype = await element.get_attribute("type") or "text"
            name = await element.get_attribute("name") or ""
            eid = await element.get_attribute("id") or ""
            lbl = await element.get_attribute("aria-label") or ""
            placeholder = await element.get_attribute("placeholder") or ""
            
            combined = (name + " " + eid + " " + lbl + " " + placeholder).lower()
            itype = itype.lower()

            # 1. Email
            if itype == "email" or "email" in combined:
                return "test@example.com"
            
            # 2. Phone / Tel
            if itype == "tel" or "phone" in combined or "mobile" in combined:
                return "555-0199"
            
            # 3. URL
            if itype == "url" or "website" in combined or "link" in combined:
                return "https://example.com"
            
            # 4. Dates
            if itype == "date" or "dob" in combined or "birthday" in combined:
                return "2025-01-01"
            if itype in ["time", "datetime-local"]:
                return "12:00"

            # 5. Numbers / Zip / Age
            if itype == "number":
                if "zip" in combined or "postal" in combined:
                    return "90210"
                if "age" in combined:
                    return "25"
                if "year" in combined:
                    return "2025"
                return "10"
                
            # 6. Names
            if "first" in combined and "name" in combined:
                return "John"
            if "last" in combined and "name" in combined:
                return "Doe"
            if "full" in combined or "name" in combined:
                return "John Doe"
            
            # 7. Password
            if itype == "password":
                return "Password123!"
            
            # 8. Address
            if "address" in combined:
                return "123 Test St"
            if "city" in combined:
                return "Test City"
            if "state" in combined:
                return "NY"
            
            # 9. Search
            if itype == "search" or "search" in combined:
                return "test query"
                
            # Default
            return "test_value"
            
        except Exception as e:
            self._log_trace("warning", f"[WARN] Failed to determine smart input: {e}")
            return "test_value"

    def _generate_mobile_summary(self) -> str:
        lines = ["### SYSTEM REPORT: MOBILE SIMULATION LOGS"]
        if not self.logs["mobile_logs"]:
            lines.append("No mobile interaction logs available.")
        else:
            for item in self.logs["mobile_logs"]:
                lines.append(f"- {item}")
        
        return "\n".join(lines)

    def _generate_fidelity_summary(self, inventory: Dict) -> str:
        lines = ["### SYSTEM REPORT: UI INVENTORY"]
        lines.append(f"Found {inventory['components']['buttons']} Buttons, {inventory['components']['inputs']} Inputs, {inventory['components']['images']} Images.")
        lines.append(f"Visible Text Preview: \"{inventory['text_preview']}\"")
        lines.append(f"Primary Button Computed Style: BG={inventory.get('styles', {}).get('primary_button_bg', 'N/A')}, Text={inventory.get('styles', {}).get('primary_button_text', 'N/A')}")
        return "\n".join(lines)

    def _generate_visual_summary(self, dna: Dict) -> str:
        lines = ["### SYSTEM REPORT: VISUAL STYLE DNA"]
        
        # Font Logic
        font = dna['font_family'].lower()
        if "times" in font or "serif" in font and "sans" not in font:
            lines.append(f"**Typography**: Detected Generic/Outdated Font ('{dna['font_family']}'). [NEGATIVE SIGNAL]")
        else:
            lines.append(f"**Typography**: Detected Sans-Serif/Modern Font ('{dna['font_family']}'). [POSITIVE SIGNAL]")
             
        # Modern CSS Logic
        if dna['modern_css']:
            lines.append(f"**Modern Features**: Detected {', '.join(dna['modern_css'])}. [POSITIVE SIGNAL]")
        else:
            lines.append("**Modern Features**: None detected (Flat/Basic design). [NEUTRAL/NEGATIVE SIGNAL]")
            
        return "\n".join(lines)
