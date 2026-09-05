import { useEffect, useRef, useState } from 'react';
import { api, endpoints } from '../api';

const SUGGESTIONS = [
  'Summarize the current open incidents',
  'What usually causes an air compressor to overheat?',
  'How should I prioritize and resolve an overheating incident?',
  'Top preventive maintenance tips for diesel generators',
];

const SHOW_ROLE = {
  user: 'You',
  assistant: 'Thibitisha',
};

export default function AiChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, busy]);

  async function send(text) {
    const question = (text ?? input).trim();
    if (!question || busy) return;

    const history = messages.map((m) => ({ role: m.role, content: m.content })).slice(-12);
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setInput('');
    setBusy(true);
    setError(null);
    try {
      const data = await api.post(endpoints.aiChat, { message: question, history });
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="d-flex flex-column" style={{ height: 'calc(100vh - 190px)' }}>
      <div className="mb-3">
        <h1 className="fs-3 mb-1">AI Assistant</h1>
        <p className="mb-0 text-secondary">
          Ask about equipment faults, incident priorities, or repair steps. Backed by Groq
          (<code>groq/compound-mini</code>) with a live snapshot of the facility.
        </p>
      </div>

      {!messages.length && (
        <div className="mb-3 d-flex gap-2 flex-wrap">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="btn btn-sm btn-outline-primary" onClick={() => send(s)}>
              <i className="ti ti-sparkles me-1"></i>{s}
            </button>
          ))}
        </div>
      )}

      <div ref={scrollRef} className="card flex-grow-1 overflow-auto mb-3">
        {!messages.length && !busy ? (
          <div className="d-flex flex-column align-items-center justify-content-center text-secondary h-100 p-4">
            <i className="ti ti-robot fs-1 mb-2 text-primary"></i>
            <div className="text-center">
              <p className="mb-1">Type a question or tap a suggestion above.</p>
              <small>Example: “Which incidents need attention right now and why?”</small>
            </div>
          </div>
        ) : (
          <div className="p-3 d-flex flex-column gap-3">
            {messages.map((m, i) => (
              <div key={i} className={`d-flex ${m.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}>
                <div
                  className={`rounded-3 px-3 py-2 text-start ${m.role === 'user' ? 'bg-primary text-white' : 'bg-light'}`}
                  style={{ maxWidth: '78%', whiteSpace: 'pre-wrap' }}
                >
                  <div className={`small fw-semibold mb-1 ${m.role === 'user' ? 'text-white-50' : 'text-primary'}`}>
                    {SHOW_ROLE[m.role] || m.role}
                  </div>
                  {m.content}
                </div>
              </div>
            ))}
            {busy && (
              <div className="d-flex justify-content-start">
                <div className="rounded-3 px-3 py-2 bg-light text-secondary">
                  <i className="ti ti-loader ti-spin me-1"></i>Thinking…
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="alert alert-danger py-2 mb-2">AI request failed: {error}</div>
      )}

      <div className="input-group">
        <textarea
          className="form-control"
          rows="2"
          placeholder="Ask the maintenance assistant…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={busy}
        />
        <button className="btn btn-primary" onClick={() => send()} disabled={busy || !input.trim()}>
          <i className={`ti ${busy ? 'ti-loader ti-spin' : 'ti-send'}`}></i> Send
        </button>
      </div>
    </div>
  );
}