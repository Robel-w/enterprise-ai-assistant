import { useState, useEffect } from 'react';
import './index.css';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';
import { checkBackendHealth, fetchDocuments } from './api';
import { useToast } from './useToast';

const MODES = [
  { id: 'rag',    label: 'Research',     activeClass: 'active-rag',    desc: 'Retrieval-augmented generation with citations' },
  { id: 'stream', label: 'Live answer',  activeClass: 'active-stream', desc: 'Streamed token-by-token answers' },
  { id: 'multi',  label: 'Across files', activeClass: 'active-rag',    desc: 'Search across multiple documents' },
  { id: 'agent',  label: 'Agent',        activeClass: 'active-agent',  desc: 'Autonomous agentic reasoning with tools' },
];

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [mode, setMode] = useState('rag');
  const [backendStatus, setBackendStatus] = useState('checking');
  const { toasts, addToast } = useToast();

  useEffect(() => {
    const controller = new AbortController();
    fetchDocuments({ signal: controller.signal })
      .then(setDocuments)
      .catch((error) => {
        if (!controller.signal.aborted) addToast(error.message, 'error');
      });
    checkBackendHealth({ signal: controller.signal })
      .then(() => setBackendStatus('connected'))
      .catch(() => {
        if (!controller.signal.aborted) setBackendStatus('disconnected');
      });
    return () => controller.abort();
  }, [addToast]);

  const handleUpload = (doc) => {
    setDocuments((prev) => [doc, ...prev]);
    setSelectedIds([doc.id]);
    addToast(`"${doc.title}" uploaded and processed! ✨`, 'success');
  };

  const selectedMode = MODES.find((m) => m.id === mode);
  const conversationKey = `${selectedIds.join(',')}:${mode}`;

  return (
    <div className="app-shell">
      {/* Topbar */}
      <header className="topbar">
        <div className="topbar-logo">
          <div className="topbar-logo-icon" aria-hidden="true">A</div>
          <div className="topbar-logo-name">Archive <span>/ Research desk</span></div>
        </div>
        <div className="topbar-spacer" />
        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginRight: 12 }}>
          <span className="selection-summary">{selectedIds.length === 0
            ? 'No document selected'
            : selectedIds.length === 1
            ? `1 document · ${selectedMode?.desc}`
            : `${selectedIds.length} documents · Multi-doc mode`}</span>
        </div>
        <div
          className={`status-dot ${backendStatus}`}
          title={`Backend ${backendStatus}`}
          role="status"
          aria-label={`Backend ${backendStatus}`}
        />
      </header>

      {/* Sidebar */}
      <Sidebar
        documents={documents}
        selectedIds={selectedIds}
        onSelect={setSelectedIds}
        onUpload={handleUpload}
      />

      {/* Main area */}
      <div className="main" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Mode bar */}
        <nav className="mode-bar" aria-label="Chat mode selector">
          <span className="mode-bar-label">Mode</span>
          {MODES.map((m) => (
            <button
              key={m.id}
              id={`mode-btn-${m.id}`}
              className={`mode-btn ${mode === m.id ? m.activeClass : ''}`}
              onClick={() => setMode(m.id)}
              title={m.desc}
            >
              {m.label}
            </button>
          ))}
        </nav>

        {/* Chat */}
        <ChatArea
          key={conversationKey}
          selectedIds={selectedIds}
          mode={mode}
          addToast={addToast}
        />
      </div>

      {/* Toast notifications */}
      <div className="toast-container" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>
            {t.type === 'success' ? '✓' : t.type === 'error' ? '✕' : 'ℹ'}
            {t.message}
          </div>
        ))}
      </div>
    </div>
  );
}
