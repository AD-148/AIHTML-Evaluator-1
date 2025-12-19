import json
import logging
import os
import tempfile
import re
import subprocess
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
import asyncio

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

    def _log_trace(self, icon: str, message: str):
        """Appends a structured log entry for the UI trace."""
        self.logs["execution_trace"].append(f":{icon}: {message}")

    async def analyze(self) -> Dict[str, str]:
        """
        SINGLE-PASS ANALYSIS: Launches Browser ONCE (Async), runs all checks sequentially.
        Returns dictionary of all context summaries.
        """
        self._log_trace("mag_right", f"Starting Static Code Analysis. PLAYWRIGHT_AVAILABLE={PLAYWRIGHT_AVAILABLE}")
        # 1. Structural Checks (No Browser)
        self._run_bs4_checks()
        self._log_trace("mag", "BS4 Checks Complete.")
        self._check_links()
        self._log_trace("link", "Link Checks Complete.")
        if HTML5_AVAILABLE:
            try:
                self._run_html5_validation()
                self._log_trace("clipboard", "HTML5 Validation Complete.")
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
                    page.on("pageerror", lambda exc: self._log_trace("boom", f"[CRITICAL] JS Error: {exc}"))

                    await page.set_content(self.html_content)

                    # --- PHASE A: AXE ACCESSIBILITY (Manual Injection) ---
                    self._log_trace("wheelchair", "Starting Axe-Core Accessibility Audit...")
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
                            self._log_trace("white_check_mark", "[PASS] Axe Accessibility: No violations found.")
                        else:
                            count = len(axe_results.get("violations"))
                            self._log_trace("x", f"[FAIL] Axe Accessibility: Found {count} rule violations.")
                            
                            # Detailed Reporting for Axe
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
                    self._log_trace("clipboard", "Scanning UI Inventory (Buttons, Inputs, Images)...")
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
                    self._log_trace("art", "Extracting Visual Style DNA (Fonts, Tokens)...")
                    dna = {"font_family": "Unknown", "modern_css": []}
                    try:
                        dna["font_family"] = await page.evaluate("window.getComputedStyle(document.body).fontFamily")
                        features = await page.evaluate("""() => {
                            const el = document.querySelector('button') || document.querySelector('.card') || document.querySelector('div');
                            const style = window.getComputedStyle(el || document.body);
                            const features = [];
                            if (style.boxShadow !== 'none') features.push('Shadows');
                            if (parseInt(style.borderRadius) > 0) features.push('Rounded Corners');
                            if (style.backgroundImage.includes('gradient')) features.push('Gradients');
                            if (style.backdropFilter !== 'none') features.push('Glassmorphism');
                            return features;
                        }""")
                        dna["modern_css"] = features
                    except Exception as e:
                        logger.error(f"Phase C (Visual) Failed: {e}")
                    
                    # Log Visual Verdict
                    if "times" in dna['font_family'].lower() or "serif" in dna['font_family'].lower() and "sans" not in dna['font_family'].lower():
                         self._log_trace("x", f"[FAIL] Typography: Outdated font detected ('{dna['font_family']}').")
                    else:
                         self._log_trace("white_check_mark", f"[PASS] Typography: Modern font detected ('{dna['font_family']}').")
                         
                    results["visual"] = self._generate_visual_summary(dna)

                    # --- PHASE D: MOBILE SIMULATION (Resize Page) ---
                    # 1. Portrait
                    try:
                        self._log_trace("iphone", "Resizing Viewport to iPhone 12 (390x844)...")
                        await page.set_viewport_size({'width': 390, 'height': 844})
                        await page.wait_for_timeout(200)
                        vp = await page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
                        self.logs["mobile_logs"].append(f"Viewport Verified: {vp['width']}x{vp['height']}")
                        
                        # Interactive Elements Test (Buttons, Links, Inputs, Custom Interactions)
                        # Added: .scratchpad, canvas, [onclick], [role=button]
                        elements = page.locator("button, a, input, textarea, select, [role='button'], [onclick], .scratchpad, .scratch-card, canvas")
                        count = await elements.count()
                        self.logs["mobile_logs"].append(f"Found {count} interactive targets.")
                        self._log_trace("mag", f"[INFO] Mobile: Found {count} interactive elements to test.")

                        for i in range(count): # Iterate ALL interactive elements
                            el = elements.nth(i)
                            if await el.is_visible():
                                try:
                                    tag = await el.evaluate("el => el.tagName.toLowerCase()")
                                    text = await el.text_content()
                                    text = text.strip()[:20] if text else "logging-in"
                                    
                                    # Log Intent
                                    self._log_trace("point_right", f"[INFO] Mobile: Approaching target #{i+1} (<{tag}> '{text}')...")
                                    
                                    # Scroll info
                                    await el.scroll_into_view_if_needed()
                                    
                                    inputType = await el.evaluate("el => el.getAttribute('type')")
                                    
                                    inputType = await el.evaluate("el => el.getAttribute('type')")
                                    name_attr = await el.evaluate("el => el.getAttribute('name')") or ""
                                    aria_label = await el.evaluate("el => el.getAttribute('aria-label')") or ""
                                    cls_attr = await el.evaluate("el => el.getAttribute('class')") or ""
                                    
                                    # Normalize strings for heuristics
                                    combined_desc = (text + " " + cls_attr + " " + aria_label + " " + name_attr).lower()

                                    # Determine Interaction Type
                                    if tag in ['input', 'textarea'] and inputType not in ['button', 'submit', 'checkbox', 'radio', 'range', 'color']:
                                        # Smart Input Filling
                                        fill_value = "test"
                                        log_action = "Typed 'test'"
                                        
                                        if "email" in inputType or "email" in name_attr.lower():
                                            fill_value = "test@example.com"
                                            log_action = "Typed valid email"
                                        elif "tel" in inputType or "phone" in name_attr.lower() or "mobile" in name_attr.lower():
                                            fill_value = "9876543210"
                                            log_action = "Typed phone number"
                                        elif inputType == "number":
                                            fill_value = "10"
                                            log_action = "Typed number"
                                        elif inputType == "date":
                                            fill_value = "2025-01-01"
                                            log_action = "Typed date"
                                        elif inputType == "url":
                                            fill_value = "https://example.com"
                                            log_action = "Typed URL"
                                        elif "search" in inputType:
                                            fill_value = "test query"
                                            log_action = "Typed search query"
                                        
                                        await el.fill(fill_value)
                                        self.logs["mobile_logs"].append(f"Target #{i+1} ({tag}): {log_action} ('{fill_value}').")
                                        self._log_trace("keyboard", f"[PASS] Mobile: {log_action} into <{tag} type='{inputType}'>.")
                                    
                                    elif "scratch" in combined_desc or "reveal" in combined_desc:
                                        # Scratch Card Gesture Simulation
                                        self._log_trace("point_up", f"[INFO] Mobile: Detected 'Scratch' intent on Target #{i+1}.")
                                        box = await el.bounding_box()
                                        if box:
                                            center_x = box['x'] + box['width'] / 2
                                            center_y = box['y'] + box['height'] / 2
                                            # Simulate a zigzag scratch
                                            await page.mouse.move(center_x - 20, center_y)
                                            await page.mouse.down()
                                            await page.mouse.move(center_x + 20, center_y, steps=5)
                                            await page.mouse.move(center_x - 20, center_y + 20, steps=5)
                                            await page.mouse.move(center_x + 20, center_y - 20, steps=5)
                                            await page.mouse.up()
                                            
                                            self.logs["mobile_logs"].append(f"Target #{i+1}: Performed Scratch Gesture.")
                                            self._log_trace("sparkles", f"[PASS] Mobile: Performed Scratch Gesture on <{tag}>.")
                                        else:
                                             self.logs["mobile_logs"].append(f"Target #{i+1}: Scratch failed (No Bounding Box).")

                                    elif "spin" in combined_desc or "wheel" in combined_desc:
                                        # Spin Wheel -> Tap with logging
                                        self._log_trace("point_up", f"[INFO] Mobile: Detected 'Spin' intent on Target #{i+1}.")
                                        await el.tap(timeout=2000)
                                        self.logs["mobile_logs"].append(f"Target #{i+1}: Spun the Wheel.")
                                        self._log_trace("dart", f"[PASS] Mobile: Tapped Scale/Spin/Wheel element.")
                                    
                                    else:
                                        # Standard Click/Tap interaction
                                        # Capture State Before
                                        url_before = page.url
                                        html_before = await page.content()
                                        
                                        # Tap with INCREASED TIMEOUT (2000ms)
                                        await el.tap(timeout=2000)
                                        await page.wait_for_timeout(600) # Wait for JS/Animation
                                        
                                        # Capture State After
                                        url_after = page.url
                                        html_after = await page.content()
                                        
                                        # Verify State Change
                                        if url_before != url_after:
                                             self._log_trace("rocket", f"[PASS] Mobile: Tapped <{tag}> and navigated to {url_after}.")
                                             self.logs["mobile_logs"].append(f"Target #{i+1}: Triggered Navigation.")
                                        elif html_before != html_after:
                                             self._log_trace("white_check_mark", f"[PASS] Mobile: Tapped <{tag}> and triggered UI update.")
                                             self.logs["mobile_logs"].append(f"Target #{i+1}: Triggered Visual Update.")
                                        else:
                                             # No change detected -> Likely broken listener
                                             self._log_trace("x", f"[FAIL] Mobile: Tapped <{tag}> but page state did not change (Unresponsive).")
                                             self.logs["mobile_logs"].append(f"Target #{i+1}: Unresponsive (No DOM/URL change).")
                                             
                                except Exception as e:
                                    self.logs["mobile_logs"].append(f"Target #{i+1}: FAILED INTERACTION. Error: {e}")
                                    self._log_trace("x", f"[FAIL] Mobile: Failed to tap target #{i+1}. Error: {e}")
                        
                        # 2. Landscape check
                        await page.set_viewport_size({"width": 844, "height": 390})
                        await page.wait_for_timeout(200)
                        scroll_width = await page.evaluate("document.body.scrollWidth")
                        if scroll_width > 844:
                            self.logs["mobile_logs"].append(f"LANDSCAPE FAIL: Horizontal scroll detected.")
                            self._log_trace("x", "[FAIL] Landscape Mode: Horizontal scroll detected.")
                        else:
                            self.logs["mobile_logs"].append("LANDSCAPE PASS: No horizontal scroll.")
                            self._log_trace("white_check_mark", "[PASS] Landscape Mode: No horizontal scroll.")
                            
                    except Exception as e:
                        logger.error(f"Phase D (Mobile iOS) Failed: {e}")
                        self.logs["mobile_logs"].append(f"iOS Check Crash: {e}")

                    # --- PHASE D1.5: RUNTIME ERROR CHECK ---
                    errors = [log for log in console_logs if "error" in log.lower() or "exception" in log.lower()]
                    if errors:
                        self.logs["mobile_logs"].insert(0, f"!!! CRITICAL JS ERRORS DETECTED ({len(errors)}) !!!")
                        self.logs["mobile_logs"].append(f"Runtime Errors Detected: {len(errors)} found.")
                        for err in errors[:3]:
                            self.logs["mobile_logs"].append(f"- {err}")
                    else:
                        self.logs["mobile_logs"].append("No Runtime Console Errors detected.")

                    # --- PHASE D2: ANDROID SIMULATION (Samsung Galaxy S20 / Pixel 5) ---
                    # Dimensions: 412x915
                    try:
                        self._log_trace("calling", "Resizing Viewport to Samsung/Android (412x915)...")
                        await page.set_viewport_size({'width': 412, 'height': 915})
                        await page.wait_for_timeout(200)
                        vp = await page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
                        self.logs["mobile_logs"].append(f"Android Viewport Verified: {vp['width']}x{vp['height']}")
                        
                        # Quick Tap Test for Android (Just checking first button to ensure no layout shift blocked it)
                        btn = page.locator("button, a, input[type='button'], input[type='submit']").first
                        if await btn.is_visible():
                            try:
                                await btn.tap(timeout=500)
                                self.logs["mobile_logs"].append(f"Android Target Check: Tappable.")
                                self._log_trace("white_check_mark", "[PASS] Android Check: Button is tappable.")
                            except:
                                 self.logs["mobile_logs"].append(f"Android Target Check: FAILED TAP (Layout Shift?).")
                                 self._log_trace("x", "[FAIL] Android Check: Button tap failed (Layout Shift?).")

                    except Exception as e:
                        logger.error(f"Phase D2 (Android) Failed: {e}")
                        self.logs["mobile_logs"].append(f"Android Check Crash: {e}")
                    
                    results["mobile"] = self._generate_mobile_summary()

                finally:
                    await browser.close()

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
                    self._log_trace("x", f"[FAIL] Link: Broken internal anchor ({href_log}).")
                else:
                     if i < 5: self._log_trace("white_check_mark", f"[PASS] Link: Valid internal anchor ({href_log}).")
            elif not href.startswith(('http', 'mailto', 'tel', '/')):
                 self.logs["warnings"].append(f"Suspicious Link: href='{href_log}' is likely invalid.")
                 self._log_trace("x", f"[FAIL] Link: Invalid href format ({href_log}).")
            else:
                 if i < 5: self._log_trace("white_check_mark", f"[PASS] Link: Valid href format ({href_log}).")




    def _generate_access_summary(self) -> str:
        lines = ["### SYSTEM REPORT: ACCESSIBILITY & SYNTAX"]
        if self.logs["score_cap"] < 100:
            lines.append(f"**OVERRIDE**: Score Max Capped at {self.logs['score_cap']}/100.")
        
        for item in self.logs["critical"]:
            lines.append(f"- [CRITICAL] {item}")
        for item in self.logs["warnings"]:
            lines.append(f"- [WARN] {item}")
            
        return "\n".join(lines)

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
