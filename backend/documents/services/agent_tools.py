"""
agent_tools.py — Concrete implementations of tools available to the RAG agent.
Each tool takes a query + document_ids and returns a plain-text result
that the agent will use as its "observation".
"""
from documents.services.retriever import Retriever
from documents.services.reranker import Reranker
from documents.services.llm import generate_answer


def tool_search_document(question: str, document_ids: list, top_k: int = 5, owner=None) -> str:
    """
    Retrieve and rerank relevant chunks from one or more documents,
    then format them as a plain-text observation for the agent.
    """
    if len(document_ids) == 1:
        chunks = Retriever.retrieve(
            question, document_id=document_ids[0], top_k=20, owner=owner
        )
    else:
        chunks = Retriever.retrieve_multi(
            question, document_ids=document_ids, top_k_per_doc=10, owner=owner
        )

    if not chunks:
        return "No relevant content found in the document(s)."

    reranked = Reranker.rerank(question, chunks, top_k=top_k)

    parts = []
    for item in reranked:
        result = item["result"]
        label = (
            f"[Document: {result.document.title} | Page {result.page_number}]"
            if result.page_number
            else f"[Document: {result.document.title}]"
        )
        parts.append(f"{label}\n{result.content}")

    return "\n\n---\n\n".join(parts)


def tool_summarize_document(document_ids: list, owner=None) -> str:
    """
    Produce a brief summary of the document(s) by retrieving
    a broad sample of chunks and asking the LLM to summarize.
    """
    from documents.models import DocumentChunk

    summaries = []
    for doc_id in document_ids:
        # Grab the first 10 chunks (beginning of document = best summary signal)
        queryset = DocumentChunk.objects.filter(document_id=doc_id)
        if owner is not None:
            queryset = queryset.filter(document__owner=owner)
        chunks = (
            queryset
            .exclude(embedding=None)
            .order_by("chunk_index")[:10]
        )
        combined = "\n\n".join(c.content for c in chunks)
        if not combined:
            summaries.append(f"Document {doc_id}: No content available.")
            continue

        summary = generate_answer(
            question="Provide a concise summary of this document in 3-5 sentences.",
            context=combined
        )
        doc_title = chunks[0].document.title if chunks else f"Document {doc_id}"
        summaries.append(f"**{doc_title}**:\n{summary}")

    return "\n\n".join(summaries)


def tool_answer_directly(question: str) -> str:
    """
    Answer a general knowledge question without document retrieval.
    Used when the agent decides RAG is not needed.
    """
    return generate_answer(
        question=question,
        context="(No document context — answer from general knowledge)"
    )
