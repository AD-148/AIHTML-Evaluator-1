import { useState, useRef, useEffect } from 'react';
import './index.css';

const App = () => {
  // --- STATE ---
  const [activeTab, setActiveTab] = useState('analysis'); // 'analysis', 'chat', 'preview'
  const [htmlInput, setHtmlInput] = useState(`<div class="card">\n  <h2>Hello World</h2>\n  <button>Click Me</button>\n</div>`);
  const [chatHistory, setChatHistory] = useState([]); // [{ role: 'user'|'assistant'|'system', content: ... }]
  const [latestAnalysis, setLatestAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const messagesEndRef = useRef(null);

  // Ref to track if we just did an initial analysis (to auto-switch tabs)
  const isInitialAnalysis = useRef(true);

  // --- ACTIONS ---

  // 1. Initial Evaluation (triggered from Left Panel)
  const handleEvaluate = async () => {
    if (!htmlInput.trim()) return;

    setLoading(true);
    setLatestAnalysis(null);
    setActiveTab('analysis');
    isInitialAnalysis.current = true;

    // Reset Chat History with the new context
    const initialMsg = { role: 'user', content: `Evaluate this HTML:\n${htmlInput}` };
    const newHistory = [initialMsg];
    setChatHistory(newHistory);

    try {
      const data = await callApi(newHistory);
      setLatestAnalysis(data);
      // Add assistant response to history
      setChatHistory(prev => [...prev, { role: 'assistant', content: data }]);
    } catch (err) {
      console.error("Evaluation error:", err);
      setLatestAnalysis({ error: err.message });
      setChatHistory(prev => [...prev, { role: 'assistant', content: { error: err.message } }]);
    } finally {
      setLoading(false);
    }
  };

  // 2. Chat Interaction (triggered from Chat Tab)
  const handleChatSend = async () => {
    if (!chatInput.trim()) return;

    const userMsg = { role: 'user', content: chatInput };
    const newHistory = [...chatHistory, userMsg];
    setChatHistory(newHistory);
    setChatInput("");
    setLoading(true);
    isInitialAnalysis.current = false;

    try {
      const data = await callApi(newHistory);
      setChatHistory(prev => [...prev, { role: 'assistant', content: data }]);

      // If the response contains a "final_judgement" that looks like code, or if we want to update preview
      // Ideally, the Preview tab should show the latest HTML discussed. 
      // For now, Preview shows the Input HTML unless the AI explicitly outputted new HTML.
      // Since our current backend returns JSON evaluation, maybe we need to ask AI to output code in a specific field?
      // Or we infer it. The current prompt asks for JSON scores.
      // For "Fix this", the prompt might need adjustment, or we assume the AI handles it within 'rationale' or we need a new field.
      // *Correction*: The current backend ONLY returns JSON scores. 
      // To get fixed HTML, the AI needs to put it in 'rationale' or we need a code field. 
      // Let's assume for now the AI puts code in 'rationale' if asked.

    } catch (err) {
      console.error("Chat error:", err);
      setChatHistory(prev => [...prev, { role: 'assistant', content: { error: err.message } }]);
    } finally {
      setLoading(false);
    }
  };

  const callApi = async (messages) => {
    // Filter out internal system messages if any (we don't have them yet)
    // Map content objects to strings if needed, but our backend expects objects or strings?
    // Backend expects: List[Message] where Message is { role, content: str }
    // But our history has 'content' as objects for Assistant. We need to stringify them.

    const apiMessages = messages.map(m => ({
      role: m.role,
      content: typeof m.content === 'string' ? m.content : JSON.stringify(m.content)
    }));

    const response = await fetch('/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: apiMessages }),
    });

    if (!response.ok) {
      let errorDetail = 'Request failed';
      try {
        const err = await response.json();
        errorDetail = err.detail || errorDetail;
      } catch (parseErr) {
        console.error("Error parsing error response:", parseErr);
        // Fallback if response isn't JSON
        const text = await response.text();
        errorDetail = text || errorDetail;
      }
      console.error(`API Error (${response.status}):`, errorDetail);
      throw new Error(errorDetail);
    }
    return await response.json();
  };

  // Auto-scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, activeTab]);


  // --- RENDER HELPERS ---

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-high';
    if (score >= 60) return 'text-mid';
    return 'text-low';
  };

  // Helper to extract code from rationale if present or use fixed_html
  const getPreviewCode = () => {
    // 1. Look for explicit 'fixed_html' in the last assistant message
    for (let i = chatHistory.length - 1; i >= 0; i--) {
      const msg = chatHistory[i];
      if (msg.role === 'assistant' && msg.content && msg.content.fixed_html) {
        return msg.content.fixed_html;
      }
    }

    // 2. Fallback: Parse from rationale (legacy support or if LLM messes up)
    for (let i = chatHistory.length - 1; i >= 0; i--) {
      const msg = chatHistory[i];
      if (msg.role === 'assistant' && msg.content && msg.content.rationale) {
        const match = msg.content.rationale.match(/```html([\s\S]*?)```/);
        if (match) return match[1];
      }
    }

    // 3. Default to input
    return htmlInput;
  };

  // 3. Apply Fix Feature
  const handleApplyFix = (fixedHtml) => {
    if (!fixedHtml) return;
    setHtmlInput(fixedHtml);
    // Optional: Switch to analysis tab to verify? Or just show a toast?
    // For now, let's keep it simple.
    // If we are in 'chat', maybe we want to see the preview?
    // Let's force a preview update effectively by updating the input.
  };

  return (
    <div className="app-container">
      <header>
        <h1>AI HTML Judge</h1>
      </header>

      <main className="main-grid">
        {/* LEFT PANEL: INPUT */}
        <div className="card input-card">
          <div className="section-title">
            <i className="fa-solid fa-code"></i> Input / Editor
          </div>
          <textarea
            value={htmlInput}
            onChange={(e) => setHtmlInput(e.target.value)}
            placeholder="Paste your HTML code here..."
            spellCheck="false"
          />
          <div className="action-bar">
            <button onClick={handleEvaluate} disabled={loading || !htmlInput.trim()}>
              {loading ? 'Analyzing...' : 'Evaluate'}
            </button>
          </div>
        </div>

        {/* RIGHT PANEL: HYBRID TABS */}
        <div className="card results-card" style={{ display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>

          {/* TABS HEADER */}
          <div className="tabs-header">
            <button
              className={`tab-btn ${activeTab === 'analysis' ? 'active' : ''}`}
              onClick={() => setActiveTab('analysis')}
            >
              <i className="fa-solid fa-chart-pie"></i> Analysis
            </button>
            <button
              className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              <i className="fa-solid fa-comments"></i> Chat & Fix
            </button>
            <button
              className={`tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
              onClick={() => setActiveTab('preview')}
            >
              <i className="fa-solid fa-eye"></i> Preview
            </button>
          </div>

          {/* TAB CONTENT AREA */}
          <div className="tab-content" style={{ padding: '1.5rem', flex: 1, overflowY: 'auto' }}>

            {/* 1. ANALYSIS TAB */}
            {activeTab === 'analysis' && (
              <div className="fade-in">
                {!latestAnalysis && !loading && (
                  <div className="results-placeholder">
                    <i className="fa-solid fa-arrow-left" style={{ fontSize: '2rem', marginBottom: '1rem' }}></i>
                    <p>Submit code to see analysis.</p>
                  </div>
                )}

                {latestAnalysis && latestAnalysis.error && (
                  <div style={{ color: '#ef4444' }}>Error: {latestAnalysis.error}</div>
                )}

                {latestAnalysis && !latestAnalysis.error && (
                  <>
                    <div className="scores-container">
                      <div className="score-card">
                        <div className={`score-value ${getScoreColor(latestAnalysis.score_fidelity)}`}>{latestAnalysis.score_fidelity}</div>
                        <div className="score-label">Fidelity</div>
                      </div>
                      <div className="score-card">
                        <div className={`score-value ${getScoreColor(latestAnalysis.score_syntax)}`}>{latestAnalysis.score_syntax}</div>
                        <div className="score-label">Syntax</div>
                      </div>
                      <div className="score-card">
                        <div className={`score-value ${getScoreColor(latestAnalysis.score_accessibility)}`}>{latestAnalysis.score_accessibility}</div>
                        <div className="score-label">Accessibility</div>
                      </div>
                    </div>
                    <div className="section-title" style={{ fontSize: '1rem' }}>Rationale</div>
                    <div className="rationale-box">{latestAnalysis.rationale}</div>
                    <div className="judgement-box">
                      <span style={{ opacity: 0.7 }}>Verdict: </span>{latestAnalysis.final_judgement}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* 2. CHAT TAB */}
            {activeTab === 'chat' && (
              <div className="chat-layout fade-in" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <div className="chat-messages" style={{ flex: 1, overflowY: 'auto', marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {chatHistory.length === 0 && <div className="results-placeholder"><p>Start evaluating to chat.</p></div>}

                  {chatHistory.map((msg, idx) => (
                    msg.role === 'user' ? (
                      <div key={idx} className="message user-message" style={{ padding: '0.8rem', fontSize: '0.9rem' }}>
                        <strong>You:</strong> <pre style={{ whiteSpace: 'pre-wrap', marginTop: '0.5rem' }}>{msg.content}</pre>
                      </div>
                    ) : (
                      <div key={idx} className="message ai-message" style={{ padding: '0.8rem', fontSize: '0.9rem' }}>
                        <strong>AI:</strong>
                        {msg.content.error ? (
                          <div style={{ color: 'red' }}>{msg.content.error}</div>
                        ) : (
                          <div>
                            {/* Just show rationale in chat for brevity */}
                            <div style={{ marginBottom: '0.5rem' }}>{msg.content.rationale}</div>
                            {/* Show concise scores */}
                            <div style={{ fontSize: '0.8rem', opacity: 0.7, marginBottom: '0.5rem' }}>
                              F: {msg.content.score_fidelity} | S: {msg.content.score_syntax} | A: {msg.content.score_accessibility}
                            </div>
                            {/* Apply Fix Button */}
                            {msg.content.fixed_html && (
                              <button
                                onClick={() => handleApplyFix(msg.content.fixed_html)}
                                style={{
                                  fontSize: '0.8rem',
                                  padding: '0.3rem 0.6rem',
                                  background: '#22c55e',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '0.3rem',
                                  cursor: 'pointer'
                                }}
                              >
                                <i className="fa-solid fa-check"></i> Apply Fix to Editor
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  ))}
                  {loading && <div className="message system-message">Thinking...</div>}
                  <div ref={messagesEndRef} />
                </div>

                <div className="chat-input-row" style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleChatSend()}
                    placeholder="Ask for fixes (e.g., 'Fix the contrast')..."
                    className="chat-input"
                    style={{ flex: 1, padding: '0.8rem', borderRadius: '0.5rem', border: '1px solid #334155', background: '#0f172a', color: 'white' }}
                  />
                  <button onClick={handleChatSend} disabled={loading || !chatInput.trim()} style={{ padding: '0 1rem' }}>
                    <i className="fa-solid fa-paper-plane"></i>
                  </button>
                </div>
              </div>
            )}

            {/* 3. PREVIEW TAB */}
            {activeTab === 'preview' && (
              <div className="fade-in" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <div className="preview-toolbar" style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Rendering safe HTML</span>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {/* Show Apply button in Preview if we are viewing a 'fixed' version that is different from input? 
                         Currently getPreviewCode returns fixed_html if present. 
                         So if what we are seeing is NOT what is in the editor, allow applying it.
                     */}
                    {getPreviewCode() !== htmlInput && (
                      <button
                        onClick={() => handleApplyFix(getPreviewCode())}
                        style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem', background: '#22c55e', border: 'none', borderRadius: '0.3rem', color: 'white', cursor: 'pointer' }}
                      >
                        Apply Fix
                      </button>
                    )}
                    <button
                      onClick={() => navigator.clipboard.writeText(getPreviewCode())}
                      style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem', background: '#334155', border: 'none', borderRadius: '0.3rem', color: 'white', cursor: 'pointer' }}
                    >
                      Copy Code
                    </button>
                  </div>
                </div>
                <div className="preview-frame-container" style={{ flex: 1, background: 'white', borderRadius: '0.5rem', overflow: 'hidden' }}>
                  {/* We use an iframe to isolate styles */}
                  <iframe
                    title="preview"
                    srcDoc={getPreviewCode()}
                    sandbox="allow-scripts"
                    style={{ width: '100%', height: '100%', border: 'none' }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;
