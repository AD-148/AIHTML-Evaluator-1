from bs4 import BeautifulSoup
from typing import List, Dict, Any

class StaticAnalyzer:
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.issues = []

    def analyze(self) -> Dict[str, Any]:
        """
        Runs a suite of static checks and returns a report.
        """
        self.issues = []
        self._check_images()
        self._check_buttons()
        self._check_inputs()
        self._check_structure()
        
        score_deduction = len(self.issues) * 10 
        base_score = 100
        static_score = max(0, base_score - score_deduction)

        return {
            "static_score": static_score,
            "issues": self.issues
        }

    def _check_images(self):
        """Check for missing alt text on images."""
        images = self.soup.find_all('img')
        for img in images:
            if not img.get('alt'):
                self.issues.append(f"Image missing alt text: {str(img)[:50]}...")

    def _check_buttons(self):
        """Check for buttons without text or aria-labels."""
        buttons = self.soup.find_all('button')
        for btn in buttons:
            text = btn.get_text(strip=True)
            aria_label = btn.get('aria-label')
            aria_labelledby = btn.get('aria-labelledby')
            
            if not text and not aria_label and not aria_labelledby:
                self.issues.append(f"Button missing accessible name (text or aria-label): {str(btn)[:50]}...")

    def _check_inputs(self):
        """Check for inputs without associated labels."""
        inputs = self.soup.find_all('input')
        for inp in inputs:
            # Skip hidden, submit, reset, button types
            if inp.get('type') in ['hidden', 'submit', 'reset', 'button', 'image']:
                continue
            
            # Check for aria-label or aria-labelledby
            if inp.get('aria-label') or inp.get('aria-labelledby'):
                continue
            
            # Check for implicit label (wrapped in <label>)
            if inp.find_parent('label'):
                continue
            
            # Check for explicit label (for attribute)
            input_id = inp.get('id')
            if input_id:
                label = self.soup.find('label', attrs={'for': input_id})
                if label:
                    continue
            
            self.issues.append(f"Input field missing label: {str(inp)[:50]}...")

    def _check_structure(self):
        """Check for basic HTML structure."""
        if not self.soup.find('html', attrs={'lang': True}):
            self.issues.append("<html> tag missing 'lang' attribute.")
        
        if not self.soup.find('title'):
            self.issues.append("<title> tag missing in <head>.")
        
        meta_viewport = self.soup.find('meta', attrs={'name': 'viewport'})
        if not meta_viewport:
            self.issues.append("Missing viewport meta tag for responsiveness.")
