import { useState, useRef } from 'react';
import { uploadDocument } from './api';

export default function Sidebar({ documents, selectedIds, onSelect, onUpload }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileRef = useRef(null);

  const handleFile = async (file) => {
    if (!file || !file.name.endsWith('.pdf')) {
      alert('Only PDF files are supported.');
      return;
    }
    setUploading(true);
    setProgress(0);
    try {
      const doc = await uploadDocument(file, setProgress);
      onUpload(doc);
    } catch (e) {
      alert('Upload failed: ' + e.message);
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const toggle = (id) => {
    if (selectedIds.includes(id)) {
      onSelect(selectedIds.filter((i) => i !== id));
    } else {
      onSelect([...selectedIds, id]);
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-section">
        <div className="sidebar-section-title">Upload Document</div>
        {uploading ? (
          <div className="upload-progress">
            <span>📄</span>
            <div className="progress-bar-track" style={{ flex: 1 }}>
              <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{progress}%</span>
          </div>
        ) : (
          <label
            className={`doc-upload-zone ${dragging ? 'dragging' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            htmlFor="file-upload"
          >
            <div className="upload-icon">📁</div>
            <div className="upload-text">Drop PDF or click to browse</div>
            <div className="upload-hint">PDF files only</div>
            <input
              id="file-upload"
              ref={fileRef}
              type="file"
              accept=".pdf"
              style={{ display: 'none' }}
              onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
            />
          </label>
        )}
      </div>

      <div className="sidebar-section" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div className="sidebar-section-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Documents</span>
          <span style={{ fontWeight: 400, color: 'var(--color-primary)', fontSize: '0.68rem' }}>
            {selectedIds.length > 0 ? `${selectedIds.length} selected` : `${documents.length} total`}
          </span>
        </div>

        {documents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--color-text-faint)', fontSize: '0.8rem' }}>
            No documents yet.<br />Upload a PDF to get started.
          </div>
        ) : (
          <div className="doc-list">
            {documents.map((doc) => {
              const sel = selectedIds.includes(doc.id);
              return (
                <div
                  key={doc.id}
                  className={`doc-item ${sel ? 'selected' : ''}`}
                  onClick={() => toggle(doc.id)}
                  role="checkbox"
                  aria-checked={sel}
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && toggle(doc.id)}
                >
                  <div className="doc-checkbox">
                    {sel && (
                      <svg viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="1.5,6 4.5,9 10.5,3" />
                      </svg>
                    )}
                  </div>
                  <div className="doc-icon">📄</div>
                  <div className="doc-info">
                    <div className="doc-name" title={doc.title}>{doc.title}</div>
                    <div className="doc-meta">ID #{doc.id}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {selectedIds.length > 1 && (
        <div className="sidebar-section">
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: 'var(--color-green)' }}>
            <span>✓</span>
            <span>Multi-doc mode active</span>
            <span className="badge badge-green">{selectedIds.length} docs</span>
          </div>
        </div>
      )}
    </aside>
  );
}
