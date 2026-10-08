from pgvector.django import CosineDistance
from documents.models import DocumentChunk
from documents.services.embeddings import create_embedding


class Retriever:

    @staticmethod
    def retrieve(query, document_id, top_k=20, max_distance=0.60):
        """Retrieve top-k relevant chunks from a single document."""
        query_embedding = create_embedding(query)

        results = (
            DocumentChunk.objects
            .filter(document_id=document_id)
            .exclude(embedding=None)
            .annotate(
                distance=CosineDistance(
                    "embedding",
                    query_embedding
                )
            ).filter(
                distance__lte=max_distance
            ).order_by("distance")[:top_k]
        )

        return results

    @staticmethod
    def retrieve_multi(query, document_ids, top_k_per_doc=10, max_distance=0.60):
        """
        Retrieve top-k relevant chunks from each of the given documents.
        Returns a combined (non-deduped) list of DocumentChunk instances,
        each annotated with .distance.
        """
        query_embedding = create_embedding(query)
        all_results = []

        for doc_id in document_ids:
            results = (
                DocumentChunk.objects
                .filter(document_id=doc_id)
                .exclude(embedding=None)
                .annotate(
                    distance=CosineDistance(
                        "embedding",
                        query_embedding
                    )
                ).filter(
                    distance__lte=max_distance
                ).order_by("distance")[:top_k_per_doc]
            )
            all_results.extend(list(results))

        return all_results