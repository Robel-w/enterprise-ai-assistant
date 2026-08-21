from documents.services.retriever import Retriever
from documents.services.llm import generate_answer


class RAGService:

    @staticmethod
    def answer(question, document_id, top_k=5):

        chunks = Retriever.retrieve(
            query=question,
            document_id=document_id,
            top_k=top_k
        )

        context = "\n\n".join(
            chunk.content
            for chunk in chunks
        )

        answer = generate_answer(
            question=question,
            context=context
        )

        return {
            "answer": answer,
            "sources": [
                {
                    "chunk_id": chunk.id,
                    "page": chunk.page_number,
                    "content": chunk.content,
                    "distance": float(chunk.distance)
                }
                for chunk in chunks
            ]
        }