def retrieval_hit(retrieved_chunks, evidence_snippet):
    """Return reciprocal rank of the first chunk containing evidence."""
    if not evidence_snippet:
        return None
    evidence = evidence_snippet.casefold()
    for rank, chunk in enumerate(retrieved_chunks, start=1):
        if evidence in getattr(chunk, "content", "").casefold():
            return 1 / rank
    return 0


def reciprocal_rank(retrieved_chunks, evidence_snippet):
    """Return the reciprocal rank of the first chunk containing evidence."""
    if not evidence_snippet:
        return None
    evidence = evidence_snippet.casefold()
    for rank, chunk in enumerate(retrieved_chunks, start=1):
        content = getattr(chunk, "content", "")
        if evidence in content.casefold():
            return 1 / rank
    return 0
