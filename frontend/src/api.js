// API base URL — proxied through Vite dev server
const BASE = 'http://localhost:8000/api';

export async function fetchDocuments() {
  const res = await fetch(`${BASE}/documents/`);
  if (!res.ok) throw new Error('Failed to load documents');
  return res.json();
}

export async function uploadDocument(file, onProgress) {
  const form = new FormData();
  form.append('file', file);
  form.append('title', file.name.replace(/\.[^/.]+$/, ''));
  // owner=1 for dev; replace with auth token logic later
  form.append('owner', 1);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${BASE}/documents/`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`));
      }
    };
    xhr.onerror = () => reject(new Error('Network error'));
    xhr.send(form);
  });
}

export async function askDocument({ documentId, question, conversationId, topK = 5 }) {
  const res = await fetch(`${BASE}/documents/${documentId}/ask/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, conversation_id: conversationId, top_k: topK }),
  });
  if (!res.ok) throw new Error('Ask failed');
  return res.json();
}

/**
 * streamAskDocument — returns an async generator of events.
 * Each event is either { token, conversation_id } or { done, citations, sources, conversation_id }
 */
export async function* streamAskDocument({ documentId, question, conversationId, topK = 5 }) {
  const res = await fetch(`${BASE}/documents/${documentId}/stream-ask/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, conversation_id: conversationId, top_k: topK }),
  });

  if (!res.ok) throw new Error('Stream ask failed');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data:')) continue;
      const jsonStr = trimmed.slice(5).trim();
      if (!jsonStr) continue;
      try {
        yield JSON.parse(jsonStr);
      } catch { /* skip malformed */ }
    }
  }
}

export async function askMultiDocument({ documentIds, question, conversationId, topKPerDoc = 10, topKFinal = 5 }) {
  const res = await fetch(`${BASE}/ask-multi/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      document_ids: documentIds,
      conversation_id: conversationId,
      top_k_per_doc: topKPerDoc,
      top_k_final: topKFinal,
    }),
  });
  if (!res.ok) throw new Error('Multi-doc ask failed');
  return res.json();
}

export async function agentAsk({ documentIds, question, conversationId }) {
  const res = await fetch(`${BASE}/agent/ask/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, document_ids: documentIds, conversation_id: conversationId }),
  });
  if (!res.ok) throw new Error('Agent ask failed');
  return res.json();
}
