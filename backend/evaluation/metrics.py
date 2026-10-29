def retrieval_hit(retrieved_chunks, expected_pages):
    """
    Returns 1 if at least one retrieved chunk
    comes from an expected page.
    """

    if not expected_pages:
        return None

    retrieved_pages = {
        chunk.page_number
        for chunk in retrieved_chunks
    }

    return int(
        bool(retrieved_pages.intersection(expected_pages))
    )


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
