from backend.static_analysis import StaticAnalyzer

def test_static_analyzer():
    # 1. Bad HTML
    bad_html = """
    <html>
        <body>
            <img src="foo.jpg"> <!-- Missing alt -->
            <button></button> <!-- Missing text -->
            <input type="text"> <!-- Missing label -->
        </body>
    </html>
    """
    
    analyzer = StaticAnalyzer(bad_html)
    report = analyzer.analyze()
    
    print("--- BAD HTML REPORT ---")
    print(f"Score: {report['static_score']}")
    print("Issues:")
    for issue in report['issues']:
        print(f"- {issue}")

    assert report['static_score'] < 100
    assert any("missing alt" in i for i in report['issues'])
    assert any("missing accessible name" in i for i in report['issues'])

    # 2. Good HTML
    good_html = """
    <html lang="en">
        <head>
            <title>Test</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body>
            <img src="foo.jpg" alt="A foo image">
            <button>Click Me</button>
            <label for="email">Email</label>
            <input type="email" id="email">
        </body>
    </html>
    """
    analyzer2 = StaticAnalyzer(good_html)
    report2 = analyzer2.analyze()
    
    print("\n--- GOOD HTML REPORT ---")
    print(f"Score: {report2['static_score']}")
    print("Issues:", report2['issues'])
    
    assert report2['static_score'] == 100
    assert len(report2['issues']) == 0
    print("\nSUCCESS: Static Analyzer works as expected!")

if __name__ == "__main__":
    test_static_analyzer()
