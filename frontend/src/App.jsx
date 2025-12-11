import { useState, useRef, useEffect } from 'react';
import './index.css';

const App = () => {
  // Chat History: Array of { role: 'user' | 'assistant', content: string | object }
  // User content is simple text (or code wrapped in text).
  // Assistant content is the JSON evaluation result.
  const [chatHistory, setChatHistory] = useState([
    { role: 'system', content: "I am your AI HTML Judge. Send me HTML code to evaluate." }
  ]);

  const [inputVal, setInputVal] = useState(`<div class="card">\n  <h2>Hello World</h2>\n  <button>Click Me</button>\n</div>`);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const handleSend = async () => {
    if (!inputVal.trim()) return;

    // Add User Message
    const userMsg = { role: 'user', content: inputVal };
    const newHistory = [...chatHistory, userMsg];
    setChatHistory(newHistory);
    setLoading(true);
    setInputVal(""); // Clear input or keep it? Maybe clear for chat style.

    try {
      // Prepare payload: filter out system greeting for API if helpful, or keep it.
      // API expects strictly 'user' or 'assistant' roles usually, but our logic on backend prepends system prompt.
      // We should send valid OpenAI-like messages.
      const apiMessages = newHistory
        .filter(m => m.role !== 'system') // Don't send the FE-only greeting
        .map(m => ({
          role: m.role,
          content: typeof m.content === 'string' ? m.content : JSON.stringify(m.content)
        }));

      const response = await fetch('/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Evaluation failed');
      }

      const data = await response.json();

      // Add Assistant Message (Limit to what the UI needs, or store raw data?)
      // Store raw data so we can render the Score Card
      setChatHistory(prev => [...prev, { role: 'assistant', content: data }]);

    } catch (err) {
      setChatHistory(prev => [...prev, { role: 'assistant', content: { error: err.message } }]);
    } finally {
      setLoading(false);
    }
  };

  const renderMessage = (msg, index) => {
    if (msg.role === 'system') {
      return (
        <div key={index} className="message system-message">
          <i className="fa-solid fa-robot"></i> {msg.content}
        </div>
      );
    }

    if (msg.role === 'user') {
      return (
        <div key={index} className="message user-message">
          <div className="message-label">You</div>
          <pre className="code-block">{msg.content}</pre>
        </div>
      );
    }

    // Assistant Message (Evaluation Result)
    if (msg.role === 'assistant') {
      const result = msg.content;
      if (result.error) {
        return (
          <div key={index} className="message ai-message error">
            <strong>Error:</strong> {result.error}
          </div>
        )
      }

      return (
        <div key={index} className="message ai-message">
          <div className="message-label">AI Judge</div>
          <div className="scores-row">
            <span className={`score-badge ${getScoreColor(result.score_fidelity)}`}>Fidelity: {result.score_fidelity}</span>
            <span className={`score-badge ${getScoreColor(result.score_syntax)}`}>Syntax: {result.score_syntax}</span>
            <span className={`score-badge ${getScoreColor(result.score_accessibility)}`}>A11y: {result.score_accessibility}</span>
          </div>

          <div className="rationale-text">
            {result.rationale}
          </div>

          <div className="verdict-text">
            <strong>Verdict:</strong> {result.final_judgement}
          </div>
        </div>
      );
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'score-high';
    if (score >= 60) return 'score-mid';
    return 'score-low';
  };

  return (
    <div className="app-container chat-layout">
      <header>
        <h1>AI HTML Judge (Chat Mode)</h1>
      </header>

      <div className="chat-window">
        {chatHistory.map(renderMessage)}
        {loading && <div className="message system-message">Thinking...</div>}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <textarea
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          placeholder="Enter HTML or ask for changes..."
          onKeyDown={(e) => {
            if (e.ctrlKey && e.key === 'Enter') handleSend();
          }}
        />
        <button onClick={handleSend} disabled={loading || !inputVal.trim()}>
          Send
        </button>
      </div>
    </div>
  );
};

export default App;
