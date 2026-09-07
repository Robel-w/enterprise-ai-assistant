from documents.models import Conversation, Message
from documents.services.retriever import Retriever
from documents.services.llm import generate_answer
from documents.services.reranker import Reranker

class RAGService:

    @staticmethod
    def ask(question, document_id, conversation_id=None, top_k=5):

        # 1. Get or create conversation

        if conversation_id:
            conversation = Conversation.objects.get(
                id=conversation_id,
                document_id=document_id
            )
        else:
            conversation = Conversation.objects.create(
                document_id=document_id,
                title=question[:100]
            )

        # 2. Save user's question

        Message.objects.create(
            conversation=conversation,
            role="user",
            content=question
        )

        # 3. Retrieve relevant document chunks

        retrieved_results = Retriever.retrieve(
            question,
            document_id=document_id,
            top_k=20
        )

        reranked_results = Reranker.rerank(
            question,
            retrieved_results,
            top_k=5
        )

        if not retrieved_results:

            answer = (
                "I could not find relevant information "
                "in the document."
            )

            Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=answer
            )

            return {
                "answer": answer,
                "conversation_id": conversation.id,
                "sources": []
            }

        # 4. Build document context

        context_parts = []

        sources = []

        for item in reranked_results:
            result = item["result"]

            context_parts.append(
                result.content
            )

            sources.append({
                        
            "chunk_id": result.id,
            "page_number": result.page_number,
            "distance": float(result.distance),
            "reranker_score": item["score"],
            "content": result.content
            })

        context = "\n\n---\n\n".join(context_parts)

        # 5. Get conversation history

        messages = conversation.messages.order_by(
            "created_at"
        )

        history_parts = []

        for message in messages:

            history_parts.append(
                f"{message.role.upper()}: "
                f"{message.content}"
            )

        history = "\n".join(history_parts)

        # 6. Add history to context

        full_context = f"""
CONVERSATION HISTORY:

{history}

DOCUMENT CONTEXT:

{context}
"""

        # 7. Generate answer

        answer = generate_answer(
            question=question,
            context=full_context
        )

        # 8. Save assistant response

        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=answer
        )

        # 9. Return result

        return {
            "answer": answer,
            "conversation_id": conversation.id,
            "sources": sources
        }