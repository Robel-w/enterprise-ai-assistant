from documents.services.retriever import Retriever
from documents.services.llm import generate_answer


class RAGService:

    @staticmethod
    def ask(question, document_id, top_k=5):

        # 1. Retrieve relevant chunks
        results = Retriever.retrieve(
            question,
            document_id=document_id,
            top_k=top_k
        )

        # 2. If nothing was retrieved
        if not results:
            return {
                "answer": "I could not find relevant information in the document.",
                "sources": []
            }

        # 3. Build context from retrieved chunks
        context_parts = []

        sources = []

        for result in results:

            context_parts.append(
                result.content
            )

            sources.append({
                "chunk_id": result.id,
                "page_number": result.page_number,
                "distance": result.distance
            })

        context = "\n\n---\n\n".join(context_parts)

        # 4. Ask the LLM
        answer = generate_answer(
            question=question,
            context=context
        )

        # 5. Return answer + sources
        return {
            "answer": answer,
            "sources": sources
        }