import logging
from backend.advanced_analysis import AdvancedAnalyzer

logging.basicConfig(level=logging.INFO)

def test_advanced_analyzer():
    print("Testing AdvancedAnalyzer Pipeline...")
    
    # Sample HTML with mobile issues (small button) and accessibility issues (missing alt)
    bad_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="width: 500px"> <!-- Fixed width bad for mobile -->
        <h1>Title</h1>
        <img src="cat.jpg"> <!-- Missing alt -->
        
        <!-- Small button, might be hard to tap or throw console error if JS missing -->
        <button onclick="console.error('Simulated Failure')">Click Me</button> 
        
        <a href="#missingID">Broken Internal Link</a>
    </body>
    </html>
    """
    
    analyzer = AdvancedAnalyzer(bad_html)
    
    print("Starting Single-Pass Analysis Check...")
    
    # NEW API: Single call returns all
    results = analyzer.analyze()

    print("\n[1] Testing Accessibility Context...")
    acc_summary = results["access"]
    print(">>> ACCESSIBILITY REPORT START")
    print(acc_summary)
    print(">>> ACCESSIBILITY REPORT END")
    assert "ACCESSIBILITY & SYNTAX" in acc_summary
    assert "CRITICAL" in acc_summary # Should find the missing alt

    print("\n[2] Testing Mobile SDK Context...")
    mob_summary = results["mobile"]
    print(">>> MOBILE REPORT START")
    print(mob_summary)
    print(">>> MOBILE REPORT END")
    
    if "Playwright not installed" in mob_summary:
        print("[WARN] Playwright skipped.")
    else:
        assert "Found" in mob_summary and "clickable targets" in mob_summary

    print("\n[3] Testing Fidelity UI Inventory...")
    fid_summary = results["fidelity"]
    print(">>> FIDELITY REPORT START")
    print(fid_summary)
    print(">>> FIDELITY REPORT END")
    
    if "Playwright not installed" in fid_summary:
        print("[WARN] Fidelity skipped.")
    else:
        assert "Buttons" in fid_summary
        assert "Text Preview" in fid_summary

    print("\n[4] Testing Visual Style DNA...")
    vis_summary = results["visual"]
    print(">>> VISUAL REPORT START")
    print(vis_summary)
    print(">>> VISUAL REPORT END")
    
    if "Playwright not installed" in vis_summary:
        print("[WARN] Visual skipped.")
    else:
        assert "Typography" in vis_summary
        assert "Modern Features" in vis_summary

if __name__ == "__main__":
    test_advanced_analyzer()
