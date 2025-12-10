import { useState, useEffect } from 'react';
import './index.css';

const App = () => {
  const [htmlInput, setHtmlInput] = useState(`<div class="card">\n  <h2>Hello World</h2>\n  <button>Click Me</button>\n</div>`);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleEvaluate = async () => {
    if (!htmlInput.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ html_content: htmlInput }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Evaluation failed');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-high';
    if (score >= 60) return 'text-mid';
    return 'text-low';
  };

  return (
    <div className="app-container">
      <header>
        <h1>AI HTML Judge</h1>
        <p className="subtitle">Evaluate Fidelity, Syntax, and Accessibility with LLM Logic</p>
      </header>

      <main className="main-grid">
        {/* Left Panel: Input */}
        <div className="card input-card">
          <div className="section-title">
            <i className="fa-solid fa-code"></i> Input HTML
          </div>
          <textarea
            value={htmlInput}
            onChange={(e) => setHtmlInput(e.target.value)}
            placeholder="Paste your HTML code here..."
            spellCheck="false"
          />
          <div className="action-bar">
            <button onClick={handleEvaluate} disabled={loading || !htmlInput.trim()}>
              {loading ? <span style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>Analying...</span> : 'Evaluate Code'}
            </button>
          </div>
        </div>

        {/* Right Panel: Results */}
        <div className="card results-card">
          <div className="section-title">
            <i className="fa-solid fa-chart-pie"></i> Analysis Report
          </div>

          {error && (
            <div style={{ color: '#ef4444', padding: '1rem', background: 'rgba(239,68,68,0.1)', borderRadius: '0.5rem' }}>
              Error: {error}
            </div>
          )}

          {!result && !loading && !error && (
            <div className="results-placeholder">
              <i className="fa-solid fa-robot" style={{ fontSize: '3rem', marginBottom: '1rem' }}></i>
              <p>Submit HTML code to see the AI evaluation.</p>
            </div>
          )}

          {loading && (
            <div className="results-placeholder">
              <div className="loading-spinner"></div>
              <p>Processing with LLM...</p>
            </div>
          )}

          {result && (
            <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div className="scores-container">
                <div className="score-card">
                  <div className={`score-value ${getScoreColor(result.score_fidelity)}`}>
                    {result.score_fidelity}
                  </div>
                  <div className="score-label">Fidelity</div>
                </div>
                <div className="score-card">
                  <div className={`score-value ${getScoreColor(result.score_syntax)}`}>
                    {result.score_syntax}
                  </div>
                  <div className="score-label">Syntax</div>
                </div>
                <div className="score-card">
                  <div className={`score-value ${getScoreColor(result.score_accessibility)}`}>
                    {result.score_accessibility}
                  </div>
                  <div className="score-label">Accessibility</div>
                </div>
              </div>

              <div className="section-title" style={{ fontSize: '1rem' }}>Rationale</div>
              <div className="rationale-box">
                {result.rationale}
              </div>

              <div className="judgement-box">
                <span style={{ opacity: 0.7 }}>Verdict: </span>
                {result.final_judgement}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;
