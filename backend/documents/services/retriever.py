from pgvector.django import CosineDistance
from documents.models import DocumentChunk
from documents.services.embeddings import create_embedding

class Retriever:
    @staticmethod
    def retrieve(query, document_id, top_k=20,max_distance=0.60):

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




    