import { useState, useEffect } from 'react';
import './index.css';
import Sidebar from './Sidebar';
import ChatArea from './ChatArea';
import { checkBackendHealth, fetchCurrentUser, fetchDocuments, signOut } from './api';
import { useToast } from './useToast';
import Login from './Login';

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
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const { toasts, addToast } = useToast();

  useEffect(() => {
    let active = true;
    checkBackendHealth()
      .then(() => setBackendStatus('connected'))
      .catch(() => { if (active) setBackendStatus('disconnected'); });
    fetchCurrentUser()
      .then((currentUser) => { if (active) setUser(currentUser); })
      .catch((error) => {
        if (active && error.status !== 401) addToast(error.message, 'error');
      })
      .finally(() => { if (active) setAuthLoading(false); });
    return () => { active = false; };
  }, [addToast]);

  useEffect(() => {
    if (!user) {
      setDocuments([]);
      setSelectedIds([]);
      return undefined;
    }
    const controller = new AbortController();
    fetchDocuments({ signal: controller.signal })
      .then(setDocuments)
      .catch((error) => {
        if (!controller.signal.aborted) addToast(error.message, 'error');
      });
    return () => controller.abort();
  }, [user, addToast]);

  const handleSignOut = async () => {
    try {
      await signOut();
      setUser(null);
      addToast('You have signed out.', 'info');
    } catch (error) {
      addToast(error.message, 'error');
    }
  };

  if (authLoading) {
    return <main className="auth-shell"><p className="auth-loading">Checking your session…</p></main>;
  }

  if (!user) {
    return <Login onSignedIn={setUser} />;
  }

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
        <span className="signed-in-user">{user.username}</span>
        <button className="sign-out-button" type="button" onClick={handleSignOut}>Sign out</button>
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
