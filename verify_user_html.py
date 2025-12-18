from backend.advanced_analysis import AdvancedAnalyzer
import logging

# Configure logger to show the tool logs
logging.basicConfig(level=logging.INFO)

# The HTML provided by the user
user_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feedback Survey</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        :root {
            --color-primary-main: #0D6EFD;
            --color-primary-light: #428BFA;
            --color-primary-dark: #0A58CA;
            --color-secondary-main: #6C757D;
            --color-secondary-light: #868E96;
            --color-secondary-dark: #5C636A;
            --color-feedback-success: #198754;
            --color-feedback-error: #DC3545;
            --color-feedback-warning: #FFC107;
            --color-feedback-info: #0DCAF0;
            --color-neutral-white: #FFFFFF;
            --color-neutral-grey-900: #212529;
            --color-neutral-grey-500: #ADB5BD;
            --color-neutral-grey-100: #F8F9FA;
            --color-neutral-black: #000000;
            --font-family-sans: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --spacing-xs: 4px;
            --spacing-sm: 8px;
            --spacing-md: 16px;
            --spacing-lg: 24px;
            --spacing-xl: 32px;
            --spacing-xxl: 48px;
            --border-radius-sm: 0.25rem;
            --border-radius-md: 0.5rem;
            --border-radius-lg: 1rem;
            --border-radius-pill: 9999px
        }

        .hidden {
            display: none !important
        }

        html,
        body {
            margin: 0;
            padding: 0;
            height: 100%;
            width: 100%;
            overflow: hidden
        }

        *,
        *::before,
        *::after {
            box-sizing: border-box
        }

        @media (prefers-reduced-motion:reduce) {
            *,
            *::before,
            *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important
            }
        }
    </style>
</head>

<body class="bg-black bg-opacity-50 flex items-center justify-center p-4">
    <div id="main-container" class="relative rounded-lg shadow-xl w-full max-w-lg portrait:aspect-[9/16] landscape:aspect-video md:aspect-auto md:max-h-[90vh] overflow-hidden bg-white">
        <button id="close-button" class="absolute top-4 right-4 z-50 w-8 h-8 flex items-center justify-center rounded-full bg-gray-200 hover:bg-gray-300 text-gray-700 text-2xl leading-none transition-colors focus:ring-2 focus:ring-offset-2 focus:ring-gray-400" tabindex="0" aria-label="Close dialog">&times;</button>
        <div id="screen-1" class="h-full w-full overflow-y-auto p-6 landscape:p-8">
            <div class="h-full flex flex-col items-center justify-center space-y-6 landscape:space-y-4">
                <h1 class="text-2xl landscape:text-xl font-bold text-center text-gray-900">Are you finding what you're looking for on our site today?</h1>
                <div class="flex flex-col w-full space-y-4 landscape:space-y-3 max-w-sm">
                    <button id="yes-button" class="w-full py-3 px-6 rounded-lg font-medium text-white transition-colors focus:ring-2 focus:ring-offset-2 focus:ring-blue-500" style="background-color:var(--color-primary-main)" tabindex="0">Yes, I am!</button>
                    <button id="no-button" class="w-full py-3 px-6 rounded-lg font-medium text-white transition-colors focus:ring-2 focus:ring-offset-2 focus:ring-gray-500" style="background-color:var(--color-secondary-main)" tabindex="0">No, not really.</button>
                </div>
            </div>
        </div>
        <div id="screen-2" class="hidden h-full w-full overflow-y-auto p-6 landscape:p-8">
            <div class="h-full flex flex-col items-center justify-center space-y-6 landscape:space-y-4">
                <div id="thank-you-message" class="text-center space-y-4 landscape:space-y-3">
                    <h2 class="text-2xl landscape:text-xl font-bold text-gray-900" id="thank-you-title">Thank You</h2>
                    <p class="text-base landscape:text-sm text-gray-700" id="thank-you-text">We appreciate your feedback.</p>
                </div>
                <button id="done-button" class="mt-4 py-3 px-8 rounded-lg font-medium text-white transition-colors focus:ring-2 focus:ring-offset-2 focus:ring-blue-500" style="background-color:var(--color-primary-main)" tabindex="0">Done</button>
            </div>
        </div>
    </div>
    <script>
        window.onload = function() {
            const screen1 = document.getElementById('screen-1');
            const screen2 = document.getElementById('screen-2');
            const yesButton = document.getElementById('yes-button');
            const noButton = document.getElementById('no-button');
            const closeButton = document.getElementById('close-button');
            const doneButton = document.getElementById('done-button');
            const thankYouTitle = document.getElementById('thank-you-title');
            const thankYouText = document.getElementById('thank-you-text');
            let userChoice = '';

            function updateViewState(activeScreen) {
                if (activeScreen === 'screen-1') {
                    screen1.classList.remove('hidden');
                    screen2.classList.add('hidden');
                } else if (activeScreen === 'screen-2') {
                    screen1.classList.add('hidden');
                    screen2.classList.remove('hidden');
                }
            }

            function handleYesClick() {
                userChoice = 'yes';
                thankYouTitle.textContent = 'Great to hear!';
                thankYouText.textContent = 'Thanks for your feedback.';
                updateViewState('screen-2');
                if (window.moengage) {
                    window.moengage.trackEvent('MOE_RESPONSE_SUBMITTED', {
                        response: 'yes',
                        question: "Are you finding what you're looking for on our site today?"
                    }, {}, {}, false, true);
                }
            }

            function handleNoClick() {
                userChoice = 'no';
                thankYouTitle.textContent = "We're sorry to hear that.";
                thankYouText.textContent = 'How can we improve? (Optional: You could follow up with an open-ended input field here)';
                updateViewState('screen-2');
                if (window.moengage) {
                    window.moengage.trackEvent('MOE_RESPONSE_SUBMITTED', {
                        response: 'no',
                        question: "Are you finding what you're looking for on our site today?"
                    }, {}, {}, false, true);
                }
            }

            function handleDoneClick() {
                if (window.moengage) {
                    window.moengage.trackClick('done-button');
                    window.moengage.dismissMessage();
                }
            }

            function handleCloseClick() {
                if (window.moengage) {
                    window.moengage.trackDismiss('close-button');
                    window.moengage.dismissMessage();
                }
            }

            function handleKeyPress(event, callback) {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    callback();
                }
            }

            function init() {
                yesButton.addEventListener('click', handleYesClick);
                yesButton.addEventListener('keypress', function(e) {
                    handleKeyPress(e, handleYesClick)
                });
                noButton.addEventListener('click', handleNoClick);
                noButton.addEventListener('keypress', function(e) {
                    handleKeyPress(e, handleNoClick)
                });
                doneButton.addEventListener('click', handleDoneClick);
                doneButton.addEventListener('keypress', function(e) {
                    handleKeyPress(e, handleDoneClick)
                });
                closeButton.addEventListener('click', handleCloseClick);
                closeButton.addEventListener('keypress', function(e) {
                    handleKeyPress(e, handleCloseClick)
                });
                updateViewState('screen-1');
            }
            init();
        }
    </script>
</body>
</html>
"""

def verify_tool_signals():
    print("Running AdvancedAnalyzer on USER HTML...")
    analyzer = AdvancedAnalyzer(user_html)
    results = analyzer.analyze()
    
    print("\n" + "="*50)
    print(" RAW TOOL EVIDENCE (Verification Info)")
    print("="*50)

    # 1. VISUAL: Check for Inter font
    print("\n[1] VISUAL AGENT EVIDENCE (Style DNA):")
    print(results['visual'])
    
    # 2. MOBILE: Check for Runtime Errors
    print("\n[2] MOBILE AGENT EVIDENCE (Simulation Logs):")
    print(results['mobile'])
    
    # 3. ACCESSIBILITY: Check for Alt text failure
    print("\n[3] ACCESSIBILITY AGENT EVIDENCE (Axe Logs):")
    print(results['access'])

    # 4. FIDELITY: Check button counts
    print("\n[4] FIDELITY AGENT EVIDENCE (Inventory):")
    print(results['fidelity'])

if __name__ == "__main__":
    verify_tool_signals()
