import { useState } from 'react';

/**
 * Renders assistant message text with [Page X] citations converted to
 * interactive badge elements.
 */
function CitedText({ text }) {
  const parts = text.split(/(\[Page \d+\])/g);
  return (
    <>
      {parts.map((part, i) => {
        const match = part.match(/\[Page (\d+)\]/);
        if (match) {
          return (
            <span key={i} className="citation-badge" title={`Jump to page ${match[1]}`}>
              📄 p.{match[1]}
            </span>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

function SourcesPanel({ sources }) {
  return (
    <div className="sources-panel">
      {sources.map((src, i) => (
        <div key={i} className="source-card">
          <div className="source-header">
            <span className="source-page">
              {src.document_title
                ? `${src.document_title} — Page ${src.page_number ?? '?'}`
                : `Page ${src.page_number ?? '?'}`}
            </span>
            <span className="source-score">
              score: {src.reranker_score?.toFixed(3) ?? '—'}
            </span>
          </div>
          <div className="source-content">{src.content}</div>
        </div>
      ))}
    </div>
  );
}

function AgentSteps({ steps }) {
  if (!steps?.length) return null;
  return (
    <div className="agent-steps">
      {steps.map((step, i) => (
        <div key={i} className="agent-step">
          <div className="agent-step-label">Step {i + 1} · {step.thought}</div>
          <div className="agent-step-text">{step.action}</div>
        </div>
      ))}
    </div>
  );
}

export default function Message({ msg }) {
  const [showSources, setShowSources] = useState(false);

  if (msg.role === 'user') {
    return (
      <div className="message user">
        <div className="msg-avatar">👤</div>
        <div className="msg-body">
          <div className="msg-bubble">{msg.content}</div>
        </div>
      </div>
    );
  }

  // Typing indicator
  if (msg.typing) {
    return (
      <div className="message assistant">
        <div className="msg-avatar">🤖</div>
        <div className="msg-body">
          <div className="msg-bubble" style={{ padding: '8px 16px' }}>
            <div className="typing-indicator">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  const hasCitations = msg.citations?.length > 0;
  const hasSources = msg.sources?.length > 0;
  const hasAgentSteps = msg.agent_steps?.length > 0;
  const isStreaming = msg.streaming;
  const modeLabel = msg.mode === 'agent' ? '🧠 Agent' : msg.mode === 'stream' ? '⚡ Stream' : msg.mode === 'multi' ? '🗂 Multi-Doc' : '📚 RAG';
  const modeBadgeClass = msg.mode === 'agent' ? 'badge-violet' : msg.mode === 'stream' ? 'badge-green' : 'badge-blue';

  return (
    <div className="message assistant">
      <div className="msg-avatar">🤖</div>
      <div className="msg-body" style={{ maxWidth: '80%' }}>

        {/* Mode badge */}
        <div style={{ marginBottom: 4 }}>
          <span className={`badge ${modeBadgeClass}`}>{modeLabel}</span>
        </div>

        {/* Main bubble */}
        <div className={`msg-bubble ${isStreaming ? 'streaming-cursor' : ''}`}>
          {msg.content ? <CitedText text={msg.content} /> : null}
        </div>

        {/* Agent reasoning steps */}
        {hasAgentSteps && <AgentSteps steps={msg.agent_steps} />}

        {/* Citations row */}
        {hasCitations && (
          <div className="citations-row">
            <span className="citations-label">Sources:</span>
            {msg.citations.map((page) => (
              <span key={page} className="citation-badge">📄 p.{page}</span>
            ))}
          </div>
        )}

        {/* Sources toggle */}
        {hasSources && (
          <>
            <button
              className="sources-toggle"
              onClick={() => setShowSources((v) => !v)}
              id={`sources-toggle-${msg.id}`}
            >
              {showSources ? '▲' : '▼'}
              {showSources ? 'Hide' : 'Show'} {msg.sources.length} source chunks
            </button>
            {showSources && <SourcesPanel sources={msg.sources} />}
          </>
        )}
      </div>
    </div>
  );
}
