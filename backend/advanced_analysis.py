import json
import logging
import os
import tempfile
import re
import subprocess
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Optional imports with graceful degradation
try:
    from axe_core_python.sync_playwright import Axe
    from playwright.sync_api import sync_playwright
    AXE_AVAILABLE = True
except ImportError:
    AXE_AVAILABLE = False
    logger.warning("Axe/Playwright not installed. Accessibility checks will be limited to BeautifulSoup.")

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
            "mobile_logs": []
        }

    def analyze(self) -> Dict[str, str]:
        """
        SINGLE-PASS ANALYSIS: Launches Browser ONCE, runs all checks sequentially.
        Returns dictionary of all context summaries.
        """
        # 1. Structural Checks (No Browser)
        self._run_bs4_checks()
        self._check_links()
        if HTML5_AVAILABLE:
            try:
                self._run_html5_validation()
            except Exception as e:
                logger.error(f"HTML5 Validator Execution Failed (Java/vnu.jar missing?). Error: {e}", exc_info=True)

        results = {
            "access": "",
            "mobile": "",
            "fidelity": "",
            "visual": ""
        }

        # 2. Browser-Based Checks (Axe, Mobile, Fidelity, Visual)
        if not AXE_AVAILABLE:
            err = "[UNAVAILABLE] (Playwright not installed)."
            results["access"] = self._generate_access_summary() # Still returns BS4 findings
            results["mobile"] = err
            results["fidelity"] = err
            results["visual"] = err
            return results

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    # Create a context that mimics a decent desktop for initial Fidelity/Visual checks
                    context = browser.new_context(viewport={'width': 1280, 'height': 720}) 
                    page = context.new_page()
                    # Capture Console Logs
                    console_logs = []
                    page.on("console", lambda msg: console_logs.append(f"CONSOLE [{msg.type}]: {msg.text}"))

                    page.set_content(self.html_content)
                    
                    # --- PHASE A: AXE ACCESSIBILITY ---
                    try:
                        axe_results = Axe().run(page)
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
                    except Exception as e:
                        logger.error(f"Phase A (Axe) Failed: {e}")
                        self.logs["warnings"].append(f"Axe Scan Failed: {e}")

                    # --- PHASE B: FIDELITY UI INVENTORY ---
                    inventory = {"components": {}, "styles": {}, "text_preview": ""}
                    try:
                        inventory["components"]["buttons"] = page.locator("button, input[type='button'], input[type='submit'], a[class*='btn']").count()
                        inventory["components"]["inputs"] = page.locator("input:not([type='hidden'])").count()
                        inventory["components"]["images"] = page.locator("img").count()
                        text = page.inner_text("body")
                        inventory["text_preview"] = re.sub(r'\s+', ' ', text).strip()[:300] + "..."
                        
                        btn = page.locator("button, input[type='submit'], a[class*='btn']").first
                        if btn.is_visible():
                            rgb = btn.evaluate("el => window.getComputedStyle(el).backgroundColor")
                            color = btn.evaluate("el => window.getComputedStyle(el).color")
                            inventory["styles"]["primary_button_bg"] = rgb
                            inventory["styles"]["primary_button_text"] = color
                    except Exception as e:
                        logger.error(f"Phase B (Fidelity) Failed: {e}")
                    results["fidelity"] = self._generate_fidelity_summary(inventory)

                    # --- PHASE C: VISUAL STYLE DNA ---
                    dna = {"font_family": "Unknown", "modern_css": []}
                    try:
                        dna["font_family"] = page.evaluate("window.getComputedStyle(document.body).fontFamily")
                        features = page.evaluate("""() => {
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
                    results["visual"] = self._generate_visual_summary(dna)

                    # --- PHASE D: MOBILE SIMULATION (Resize Page) ---
                    # 1. Portrait
                    try:
                        page.set_viewport_size({'width': 390, 'height': 844})
                        page.wait_for_timeout(200)
                        vp = page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
                        self.logs["mobile_logs"].append(f"Viewport Verified: {vp['width']}x{vp['height']}")
                        
                        # Tap Test
                        buttons = page.locator("button, a, input[type='button'], input[type='submit']")
                        count = buttons.count()
                        self.logs["mobile_logs"].append(f"Found {count} clickable targets.")
                        for i in range(min(count, 5)): # Limit to 5 checks for speed
                            btn = buttons.nth(i)
                            if btn.is_visible():
                                try:
                                    btn.tap(timeout=500) # Short timeout
                                except:
                                    self.logs["mobile_logs"].append(f"Target #{i+1}: FAILED TAP.")
                        
                        # 2. Landscape check
                        page.set_viewport_size({"width": 844, "height": 390})
                        page.wait_for_timeout(200)
                        scroll_width = page.evaluate("document.body.scrollWidth")
                        if scroll_width > 844:
                            self.logs["mobile_logs"].append(f"LANDSCAPE FAIL: Horizontal scroll detected.")
                        else:
                            self.logs["mobile_logs"].append("LANDSCAPE PASS: No horizontal scroll.")
                            
                    except Exception as e:
                        logger.error(f"Phase D (Mobile iOS) Failed: {e}")
                        self.logs["mobile_logs"].append(f"iOS Check Crash: {e}")

                    # --- PHASE D1.5: RUNTIME ERROR CHECK ---
                    errors = [log for log in console_logs if "error" in log.lower()]
                    if errors:
                        self.logs["mobile_logs"].append(f"Runtime Errors Detected: {len(errors)} found.")
                        for err in errors[:3]:
                            self.logs["mobile_logs"].append(f"- {err}")
                    else:
                        self.logs["mobile_logs"].append("No Runtime Console Errors detected.")

                    # --- PHASE D2: ANDROID SIMULATION (Samsung Galaxy S20 / Pixel 5) ---
                    # Dimensions: 412x915
                    try:
                        page.set_viewport_size({'width': 412, 'height': 915})
                        page.wait_for_timeout(200)
                        vp = page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
                        self.logs["mobile_logs"].append(f"Android Viewport Verified: {vp['width']}x{vp['height']}")
                        
                        # Quick Tap Test for Android (Just checking first button to ensure no layout shift blocked it)
                        btn = page.locator("button, a, input[type='button'], input[type='submit']").first
                        if btn.is_visible():
                            try:
                                btn.tap(timeout=500)
                                self.logs["mobile_logs"].append(f"Android Target Check: Tappable.")
                            except:
                                 self.logs["mobile_logs"].append(f"Android Target Check: FAILED TAP (Layout Shift?).")

                    except Exception as e:
                        logger.error(f"Phase D2 (Android) Failed: {e}")
                        self.logs["mobile_logs"].append(f"Android Check Crash: {e}")
                    
                    results["mobile"] = self._generate_mobile_summary()

                finally:
                    browser.close()

        except Exception as e:
            logger.error(f"Single-Pass Browser Session Failed: {e}", exc_info=True)
            err = f"System Error: {str(e)}"
            results["mobile"] = err
            results["fidelity"] = err
            results["visual"] = err
            
        results["access"] = self._generate_access_summary()
        return results

    def _run_bs4_checks(self):
        """Basic structural checks using BeautifulSoup."""
        imgs = self.soup.find_all('img')
        buttons = self.soup.find_all(['button', 'a', 'input', 'select', 'textarea'])
        self.logs["stats"]["images"] = len(imgs)
        self.logs["stats"]["interactive_elements"] = len(buttons)

        # Critical: Missing Alt
        for i, img in enumerate(imgs):
            if not img.get('alt') and img.get('role') != 'presentation':
                self.logs["critical"].append(f"Image <img src='{img.get('src', 'unknown')}'> is missing 'alt' text.")
                self.logs["score_cap"] = min(self.logs["score_cap"], 60)

        # Critical: Broken Interactive Config
        for i, btn in enumerate(buttons):
            if btn.name in ['button', 'a']:
                text = btn.get_text(strip=True)
                aria_label = btn.get('aria-label')
                title = btn.get('title')
                if not text and not aria_label and not title:
                     child_img = btn.find('img')
                     if child_img and child_img.get('alt'): continue
                     self.logs["critical"].append(f"Interactive element <{btn.name}> has no accessible name.")
                     self.logs["score_cap"] = min(self.logs["score_cap"], 60)



    def _run_html5_validation(self):
        """Placeholder for HTML5 Validator (Requires external CLI usually)."""
        # In a real deployed env, we'd subprocess.run(['html5validator', ...])
        # For now, we simulate a check or skip if binary missing.
        if "<!DOCTYPE" not in self.html_content:
             self.logs["warnings"].append("HTML5 Validation: Missing <!DOCTYPE html> declaration.")

    def _check_links(self):
        """Basic Link Checker logic."""
        links = self.soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            if href.startswith('#'):
                # Internal anchor check
                target_id = href[1:]
                if target_id and not self.soup.find(id=target_id):
                    self.logs["warnings"].append(f"Broken Internal Link: href='{href}' points to non-existent ID.")
            elif not href.startswith(('http', 'mailto', 'tel', '/')):
                 self.logs["warnings"].append(f"Suspicious Link: href='{href}' is likely invalid.")




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
