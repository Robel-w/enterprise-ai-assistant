from documents.models import Conversation, Message
from documents.services.retriever import Retriever
from documents.services.llm import generate_answer


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

        results = Retriever.retrieve(
            question,
            document_id=document_id,
            top_k=top_k
        )

        if not results:

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