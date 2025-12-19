import unittest
from advanced_analysis import AdvancedAnalyzer
from bs4 import BeautifulSoup

class TestReportingImprovements(unittest.TestCase):
    def test_image_reporting_truncation_and_limits(self):
        # Create HTML with 10 failing images (missing alt) with long sources
        long_src = "https://example.com/very/long/path/to/image/that/exceeds/40/chars/image.jpg"
        html = "".join([f'<img src="{long_src}_{i}">' for i in range(10)])
        
        analyzer = AdvancedAnalyzer(html)
        analyzer._run_bs4_checks()
        
        # Verify NO limit (all 10 should be in critical logs or trace)
        # Note: _run_bs4_checks populates self.logs["critical"] and self.logs["execution_trace"]
        
        critical_logs = analyzer.logs["critical"]
        trace = analyzer.logs["execution_trace"]
        
        # Check count
        failing_images = [log for log in critical_logs if "missing 'alt'" in log]
        self.assertEqual(len(failing_images), 10, "Should report ALL 10 failing images")
        
        # Check truncation in trace
        # The trace format is: :x: [FAIL] Image: Missing 'alt' (src='...').
        fail_traces = [t for t in trace if "[FAIL] Image" in t]
        self.assertEqual(len(fail_traces), 10)
        
        # Verify truncation ellipis
        self.assertIn("...", fail_traces[0], "Source should be truncated")
        self.assertLess(len(fail_traces[0]), 150, "Log entry should be reasonably short")

    def test_link_reporting(self):
        # HTML with 6 broken links
        html = "".join([f'<a href="#broken{i}">link</a>' for i in range(6)])
        analyzer = AdvancedAnalyzer(html)
        analyzer._check_links()
        
        warnings = analyzer.logs["warnings"]
        self.assertEqual(len(warnings), 6, "Should report ALL 6 broken links (limit removed)")

if __name__ == '__main__':
    unittest.main()
