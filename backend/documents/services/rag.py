import re

from documents.models import Conversation, Message, Document
from documents.services.retriever import Retriever
from documents.services.llm import generate_answer, generate_answer_stream
from documents.services.reranker import Reranker


def _build_context(reranked_results):
    """
    Build numbered context string and sources list from reranked chunks.
    Each chunk is labelled with its page number so the LLM can cite it.
    Returns (context_str, sources_list).
    """
    context_parts = []
    sources = []

    for item in reranked_results:
        result = item["result"]
        label = f"[Page {result.page_number}]" if result.page_number else ""
        context_parts.append(
            f"{label}\n{result.content}"
        )
        sources.append({
            "chunk_id": result.id,
            "page_number": result.page_number,
            "distance": float(result.distance),
            "reranker_score": item["score"],
            "content": result.content,
        })

    context = "\n\n---\n\n".join(context_parts)
    return context, sources


def _parse_citations(answer):
    """
    Extract unique page numbers cited as [Page X] in the answer text.
    Returns a sorted list of ints.
    """
    matches = re.findall(r"\[Page (\d+)\]", answer)
    return sorted({int(m) for m in matches})


def _get_or_create_conversation(conversation_id, document_id=None, title=""):
    """
    Get an existing conversation or create a new one.
    Supports both single-doc and multi-doc conversations via the
    extended Conversation model (document FK is nullable).
    """
    if conversation_id:
        return Conversation.objects.get(id=conversation_id)

    kwargs = {"title": title[:100]}
    if document_id:
        kwargs["document_id"] = document_id

    return Conversation.objects.create(**kwargs)


def _build_history_context(conversation):
    messages = conversation.messages.order_by("created_at")
    parts = [
        f"{msg.role.upper()}: {msg.content}"
        for msg in messages
    ]
    return "\n".join(parts)


class RAGService:

    # ------------------------------------------------------------------ #
    #  Single-document ask (with citation highlighting)                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def ask(question, document_id, conversation_id=None, top_k=5):

        conversation = _get_or_create_conversation(
            conversation_id,
            document_id=document_id,
            title=question
        )

        # Save user message
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=question
        )

        # Retrieve & rerank
        retrieved = Retriever.retrieve(question, document_id=document_id, top_k=20)
        reranked = Reranker.rerank(question, retrieved, top_k=top_k)

        if not retrieved:
            answer = "I could not find relevant information in the document."
            Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=answer
            )
            return {
                "answer": answer,
                "conversation_id": conversation.id,
                "sources": [],
                "citations": [],
            }

        # Build context with page labels
        history = _build_history_context(conversation)
        doc_context, sources = _build_context(reranked)
        full_context = (
            f"CONVERSATION HISTORY:\n{history}\n\n"
            f"DOCUMENT CONTEXT:\n{doc_context}"
        )

        # Generate answer
        answer = generate_answer(question=question, context=full_context)
        citations = _parse_citations(answer)

        # Save assistant message
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=answer
        )

        return {
            "answer": answer,
            "conversation_id": conversation.id,
            "sources": sources,
            "citations": citations,
        }

    # ------------------------------------------------------------------ #
    #  Streaming single-document ask                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def ask_stream(question, document_id, conversation_id=None, top_k=5):
        """
        Generator that yields SSE-formatted strings.
        Saves the complete answer + sources to the DB when the stream ends.
        Yields:
            data: <json>\n\n  — for each token chunk
            data: [DONE]\n\n  — when stream is finished
        """
        import json

        conversation = _get_or_create_conversation(
            conversation_id,
            document_id=document_id,
            title=question
        )

        # Save user message
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=question
        )

        # Retrieve & rerank
        retrieved = Retriever.retrieve(question, document_id=document_id, top_k=20)
        reranked = Reranker.rerank(question, retrieved, top_k=top_k)

        if not retrieved:
            fallback = "I could not find relevant information in the document."
            Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=fallback
            )
            yield f"data: {json.dumps({'token': fallback, 'conversation_id': conversation.id})}\n\n"
            yield f"data: {json.dumps({'done': True, 'citations': [], 'sources': [], 'conversation_id': conversation.id})}\n\n"
            return

        history = _build_history_context(conversation)
        doc_context, sources = _build_context(reranked)
        full_context = (
            f"CONVERSATION HISTORY:\n{history}\n\n"
            f"DOCUMENT CONTEXT:\n{doc_context}"
        )

        # Stream tokens
        full_answer = []
        for token in generate_answer_stream(question=question, context=full_context):
            full_answer.append(token)
            yield f"data: {json.dumps({'token': token, 'conversation_id': conversation.id})}\n\n"

        # Persist the complete answer to DB
        complete_answer = "".join(full_answer)
        citations = _parse_citations(complete_answer)

        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=complete_answer
        )

        # Send final metadata frame
        yield f"data: {json.dumps({'done': True, 'citations': citations, 'sources': sources, 'conversation_id': conversation.id})}\n\n"

    # ------------------------------------------------------------------ #
    #  Multi-document ask                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def ask_multi(question, document_ids, conversation_id=None, top_k_per_doc=10, top_k_final=5):
        """
        Ask a question across multiple documents.
        Retrieves from each document independently, merges and reranks.
        Conversation is created without a single document FK.
        """
        conversation = _get_or_create_conversation(
            conversation_id,
            document_id=None,
            title=question
        )

        # Associate documents with this conversation
        docs = Document.objects.filter(id__in=document_ids)
        conversation.documents.set(docs)

        Message.objects.create(
            conversation=conversation,
            role="user",
            content=question
        )

        # Retrieve from each document
        all_chunks = []
        for doc_id in document_ids:
            chunks = Retriever.retrieve(question, document_id=doc_id, top_k=top_k_per_doc)
            all_chunks.extend(list(chunks))

        if not all_chunks:
            answer = "I could not find relevant information in any of the selected documents."
            Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=answer
            )
            return {
                "answer": answer,
                "conversation_id": conversation.id,
                "sources": [],
                "citations": [],
            }

        # Rerank the combined pool
        reranked = Reranker.rerank(question, all_chunks, top_k=top_k_final)

        # Build context — include document title for multi-doc attribution
        context_parts = []
        sources = []

        for item in reranked:
            result = item["result"]
            doc_title = result.document.title
            label = f"[Document: {doc_title} | Page {result.page_number}]"
            context_parts.append(f"{label}\n{result.content}")
            sources.append({
                "chunk_id": result.id,
                "document_id": result.document_id,
                "document_title": doc_title,
                "page_number": result.page_number,
                "distance": float(result.distance),
                "reranker_score": item["score"],
                "content": result.content,
            })

        history = _build_history_context(conversation)
        doc_context = "\n\n---\n\n".join(context_parts)
        full_context = (
            f"CONVERSATION HISTORY:\n{history}\n\n"
            f"DOCUMENT CONTEXT:\n{doc_context}"
        )

        answer = generate_answer(question=question, context=full_context)
        citations = _parse_citations(answer)

        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=answer
        )

        return {
            "answer": answer,
            "conversation_id": conversation.id,
            "sources": sources,
            "citations": citations,
        }