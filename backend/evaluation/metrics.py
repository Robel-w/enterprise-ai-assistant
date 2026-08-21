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