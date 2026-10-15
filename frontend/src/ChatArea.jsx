import { useState, useRef, useEffect, useCallback } from 'react';
import Message from './Message';
import PromptBar from './PromptBar';
import { Attachment01Icon, Globe02Icon } from '@hugeicons/core-free-icons';
import { askDocument, streamAskDocument, askMultiDocument, agentAsk } from './api';

const PROMPT_SOURCES = [
  {
    key: 'files',
    name: 'Photos & files',
    description: 'Attach context to your question',
    icon: Attachment01Icon,
    attach: true,
  },
  {
    key: 'web',
    name: 'Web search',
    description: 'Search live sources',
    icon: Globe02Icon,
  },
];

const SUGGESTIONS = [
  'Summarize this document',
  'What are the main themes?',
  'Who are the key characters?',
  'What happens at the end?',
];

let msgId = 0;
const makeId = () => ++msgId;

export default function ChatArea({ selectedIds, mode, addToast }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const bottomRef = useRef(null);

  // Reset conversation when document selection changes
  useEffect(() => {
    setMessages([]);
    setConversationId(null);
  }, [selectedIds.join(','), mode]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const appendMsg = (msg) =>
    setMessages((prev) => [...prev, { id: makeId(), ...msg }]);

  const updateLastAssistant = (updater) =>
    setMessages((prev) => {
      const copy = [...prev];
      const last = copy.findLastIndex((m) => m.role === 'assistant');
      if (last !== -1) copy[last] = updater(copy[last]);
      return copy;
    });

  const sendMessage = useCallback(async (text) => {
    const question = (text ?? input).trim();
    if (!question) return;
    if (selectedIds.length === 0) {
      addToast('Please select at least one document first.', 'error');
      return;
    }

    setInput('');
    setLoading(true);

    appendMsg({ role: 'user', content: question });

    try {
      if (mode === 'stream') {
        // ---- Streaming ---- //
        if (selectedIds.length !== 1) {
          addToast('Streaming mode requires exactly 1 document selected.', 'error');
          setLoading(false);
          return;
        }
        // Placeholder bubble
        const placeholderId = makeId();
        setMessages((prev) => [...prev, {
          id: placeholderId,
          role: 'assistant',
          content: '',
          streaming: true,
          mode: 'stream',
          citations: [],
          sources: [],
        }]);

        let convId = conversationId;
        const gen = streamAskDocument({
          documentId: selectedIds[0],
          question,
          conversationId: convId,
        });

        for await (const event of gen) {
          if (event.token) {
            setMessages((prev) => {
              const copy = [...prev];
              const idx = copy.findLastIndex((m) => m.id === placeholderId);
              if (idx !== -1) copy[idx] = { ...copy[idx], content: copy[idx].content + event.token };
              return copy;
            });
          }
          if (event.done) {
            setMessages((prev) => {
              const copy = [...prev];
              const idx = copy.findLastIndex((m) => m.id === placeholderId);
              if (idx !== -1) copy[idx] = {
                ...copy[idx],
                streaming: false,
                citations: event.citations ?? [],
                sources: event.sources ?? [],
              };
              return copy;
            });
            if (!convId && event.conversation_id) {
              setConversationId(event.conversation_id);
            }
          }
        }

      } else if (mode === 'agent') {
        // ---- Agent ---- //
        appendMsg({ role: 'assistant', typing: true, mode: 'agent' });
        const result = await agentAsk({
          documentIds: selectedIds,
          question,
          conversationId,
        });
        updateLastAssistant(() => ({
          id: makeId(),
          role: 'assistant',
          content: result.answer,
          citations: result.citations ?? [],
          sources: result.sources ?? [],
          agent_steps: result.agent_steps ?? [],
          mode: 'agent',
        }));
        if (!conversationId) setConversationId(result.conversation_id);

      } else if (selectedIds.length > 1 || mode === 'multi') {
        // ---- Multi-doc ---- //
        appendMsg({ role: 'assistant', typing: true, mode: 'multi' });
        const result = await askMultiDocument({
          documentIds: selectedIds,
          question,
          conversationId,
        });
        updateLastAssistant(() => ({
          id: makeId(),
          role: 'assistant',
          content: result.answer,
          citations: result.citations ?? [],
          sources: result.sources ?? [],
          mode: 'multi',
        }));
        if (!conversationId) setConversationId(result.conversation_id);

      } else {
        // ---- Single-doc RAG ---- //
        appendMsg({ role: 'assistant', typing: true, mode: 'rag' });
        const result = await askDocument({
          documentId: selectedIds[0],
          question,
          conversationId,
        });
        updateLastAssistant(() => ({
          id: makeId(),
          role: 'assistant',
          content: result.answer,
          citations: result.citations ?? [],
          sources: result.sources ?? [],
          mode: 'rag',
        }));
        if (!conversationId) setConversationId(result.conversation_id);
      }

    } catch (err) {
      updateLastAssistant((m) => m.typing
        ? { id: makeId(), role: 'assistant', content: `Error: ${err.message}`, citations: [], sources: [], mode }
        : { ...m, streaming: false }
      );
      addToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [input, selectedIds, mode, conversationId, addToast]);

  const isEmpty = messages.length === 0;

  return (
    <div className="main">
      <div className="messages-area">
        {isEmpty && (
          <div className="empty-state">
            <div className="empty-icon">💬</div>
            <h2 className="empty-title">Ask anything about your documents</h2>
            <p className="empty-desc">
              Select one or more documents from the sidebar, choose a mode, and start chatting.
              Citations will appear inline as <span className="citation-badge">📄 p.12</span> badges.
            </p>
            <div className="suggestion-chips">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="chip" onClick={() => sendMessage(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <Message key={msg.id} msg={msg} />
        ))}

        <div ref={bottomRef} />
      </div>

      <div className="input-area">
        {conversationId && (
          <div style={{ fontSize: '0.7rem', color: 'var(--color-text-faint)', marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
            <span>Conversation #{conversationId}</span>
            <button
              style={{ fontSize: '0.68rem', background: 'none', border: 'none', color: 'var(--color-text-faint)', cursor: 'pointer', textDecoration: 'underline' }}
              onClick={() => { setConversationId(null); setMessages([]); }}
            >
              New chat
            </button>
          </div>
        )}
        <PromptBar
          placeholder={
            selectedIds.length === 0
              ? 'Select a document to start chatting…'
              : mode === 'agent'
              ? 'Ask the AI agent anything…'
              : mode === 'stream'
              ? 'Ask for a streamed answer…'
              : selectedIds.length > 1
              ? `Ask across ${selectedIds.length} documents…`
              : 'Ask about this document…'
          }
          busy={loading}
          sources={PROMPT_SOURCES}
          commands={[]}
          onSend={(text) => sendMessage(text)}
          onStop={() => undefined}
          onAttach={() => {
            const picker = document.createElement('input');
            picker.type = 'file';
            picker.multiple = true;
            picker.accept = '.pdf,.txt,.doc,.docx';
            return new Promise((resolve) => {
              picker.onchange = () => resolve(Array.from(picker.files ?? []).map((file) => file.name));
              picker.click();
            });
          }}
          models={[]}
          efforts={[]}
          background="var(--color-surface-elevated)"
          color="var(--color-text)"
          menuBackground="var(--color-surface)"
          width={760}
          radius={14}
        />
      </div>
    </div>
  );
}
