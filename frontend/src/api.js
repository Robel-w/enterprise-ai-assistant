// Use the same origin in development and production. Vite and nginx proxy API
// requests to Django, which also works when the frontend runs in a container.
const BASE = `${import.meta.env.VITE_API_BASE_URL ?? ''}/api`;

async function responseError(response, fallback) {
  const body = await response.json().catch(() => null);
  const detail = body?.detail ?? body?.error ?? body?.message;
  const error = new Error(typeof detail === 'string' ? detail : `${fallback} (${response.status})`);
  error.status = response.status;
  return error;
}

async function fetchCsrfToken() {
  const res = await fetch(`${BASE}/auth/csrf/`, { credentials: 'same-origin' });
  if (!res.ok) throw await responseError(res, 'Could not start a secure session');
  const body = await res.json();
  return body.csrfToken;
}

async function apiFetch(url, options = {}) {
  const method = (options.method ?? 'GET').toUpperCase();
  const headers = new Headers(options.headers ?? {});
  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
    headers.set('X-CSRFToken', await fetchCsrfToken());
  }
  return fetch(url, { ...options, headers, credentials: 'same-origin' });
}

export async function fetchCurrentUser() {
  const res = await apiFetch(`${BASE}/auth/me/`);
  if (!res.ok) throw await responseError(res, 'Could not check sign-in status');
  return res.json();
}

export async function signIn(username, password) {
  const res = await apiFetch(`${BASE}/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw await responseError(res, 'Sign-in failed');
  return res.json();
}

export async function signOut() {
  const res = await apiFetch(`${BASE}/auth/logout/`, { method: 'POST' });
  if (!res.ok) throw await responseError(res, 'Sign-out failed');
  return res.json();
}

export async function fetchDocuments(options = {}) {
  const res = await apiFetch(`${BASE}/documents/`, options);
  if (!res.ok) throw await responseError(res, 'Failed to load documents');
  return res.json();
}

export async function checkBackendHealth(options = {}) {
  const res = await fetch(`${BASE}/health/`, options);
  if (!res.ok) throw await responseError(res, 'Backend unavailable');
  return res.json();
}

export async function uploadDocument(file, onProgress) {
  const csrfToken = await fetchCsrfToken();
  const form = new FormData();
  form.append('file', file);
  form.append('title', file.name.replace(/\.[^/.]+$/, ''));

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${BASE}/documents/`);
    xhr.withCredentials = true;
    xhr.setRequestHeader('X-CSRFToken', csrfToken);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        let message = `Upload failed (${xhr.status})`;
        try {
          const body = JSON.parse(xhr.responseText);
          message = Object.values(body).flat().find((value) => typeof value === 'string') ?? message;
        } catch { /* Keep the status-based message for non-JSON responses. */ }
        reject(new Error(message));
      }
    };
    xhr.onerror = () => reject(new Error('Network error'));
    xhr.send(form);
  });
}

export async function askDocument({ documentId, question, conversationId, topK = 5 }) {
  const res = await apiFetch(`${BASE}/documents/${documentId}/ask/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, conversation_id: conversationId, top_k: topK }),
  });
  if (!res.ok) throw await responseError(res, 'Ask failed');
  return res.json();
}

/**
 * streamAskDocument — returns an async generator of events.
 * Each event is either { token, conversation_id } or { done, citations, sources, conversation_id }
 */
export async function* streamAskDocument({ documentId, question, conversationId, topK = 5 }) {
  const res = await apiFetch(`${BASE}/documents/${documentId}/stream-ask/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, conversation_id: conversationId, top_k: topK }),
  });

  if (!res.ok) throw await responseError(res, 'Stream ask failed');

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
  const res = await apiFetch(`${BASE}/ask-multi/`, {
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
  if (!res.ok) throw await responseError(res, 'Multi-doc ask failed');
  return res.json();
}

export async function agentAsk({ documentIds, question, conversationId }) {
  const res = await apiFetch(`${BASE}/agent/ask/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, document_ids: documentIds, conversation_id: conversationId }),
  });
  if (!res.ok) throw await responseError(res, 'Agent ask failed');
  return res.json();
}
