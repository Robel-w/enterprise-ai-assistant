from django.http import FileResponse, StreamingHttpResponse
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from .serializers import (
    DocumentSerializer,
    AskQuestionSerializer,
    AskMultiDocumentSerializer,
    AgentAskSerializer,
)
from .models import Conversation, Document
from .services.processor import DocumentProcessor
from .services.rag import RAGService
from .services.retriever import Retriever


# --------------------------------------------------------------------------- #
# Documents CRUD + single-doc ask + streaming ask                              #
# --------------------------------------------------------------------------- #

def _validate_owned_document_ids(user, document_ids):
    try:
        document_ids = [int(document_id) for document_id in document_ids]
    except (TypeError, ValueError) as exc:
        raise NotFound("One or more documents were not found.") from exc
    if len(set(document_ids)) != len(document_ids):
        raise ValidationError({"document_ids": "Duplicate document IDs are not allowed."})
    owned_ids = set(Document.objects.filter(
        owner=user, id__in=document_ids
    ).values_list("id", flat=True))
    if owned_ids != set(document_ids):
        # Do not reveal whether an inaccessible document ID exists.
        raise NotFound("One or more documents were not found.")
    return document_ids


def _validate_conversation_access(user, conversation_id, required_document_id=None):
    if conversation_id is None:
        return
    try:
        conversation_id = int(conversation_id)
    except (TypeError, ValueError) as exc:
        raise NotFound("Conversation not found.") from exc
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist as exc:
        raise NotFound("Conversation not found.") from exc

    document_ids = set(conversation.documents.values_list("id", flat=True))
    if conversation.document_id:
        document_ids.add(conversation.document_id)
    owned_ids = set(Document.objects.filter(
        owner=user, id__in=document_ids
    ).values_list("id", flat=True))
    if not document_ids or owned_ids != document_ids:
        raise NotFound("Conversation not found.")
    if required_document_id is not None and required_document_id not in document_ids:
        raise NotFound("Conversation not found.")

class DocumentViewSet(ModelViewSet):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        document = serializer.save(owner=self.request.user)
        DocumentProcessor.process_document(document)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document = self.get_object()
        return FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=document.file.name.rsplit("/", 1)[-1],
            content_type="application/pdf",
        )

    @action(detail=True, methods=["post"], url_path="ask")
    def ask(self, request, pk=None):
        """Single-document RAG with citation highlighting."""
        document = self.get_object()
        serializer = AskQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _validate_conversation_access(
            request.user,
            serializer.validated_data.get("conversation_id"),
            required_document_id=document.id,
        )

        result = RAGService.ask(
            question=serializer.validated_data["question"],
            document_id=document.id,
            conversation_id=serializer.validated_data.get("conversation_id"),
            top_k=serializer.validated_data["top_k"],
            owner=request.user,
        )

        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="stream-ask")
    def stream_ask(self, request, pk=None):
        """
        Streaming single-document RAG via Server-Sent Events (SSE).
        The client should read the response as an event stream.
        Each event:
          data: {"token": "...", "conversation_id": N}\n\n
        Final event:
          data: {"done": true, "citations": [...], "sources": [...], "conversation_id": N}\n\n
        """
        document = self.get_object()
        serializer = AskQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _validate_conversation_access(
            request.user,
            serializer.validated_data.get("conversation_id"),
            required_document_id=document.id,
        )

        generator = RAGService.ask_stream(
            question=serializer.validated_data["question"],
            document_id=document.id,
            conversation_id=serializer.validated_data.get("conversation_id"),
            top_k=serializer.validated_data["top_k"],
            owner=request.user,
        )

        response = StreamingHttpResponse(
            generator,
            content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


# --------------------------------------------------------------------------- #
# Multi-document ask                                                           #
# --------------------------------------------------------------------------- #

class AskMultiDocumentView(APIView):
    """
    POST /api/ask-multi/
    Body: { "question": "...", "document_ids": [1, 2, 3], "conversation_id": null }
    """
    def post(self, request):
        serializer = AskMultiDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        owned_ids = _validate_owned_document_ids(request.user, d["document_ids"])
        _validate_conversation_access(request.user, d.get("conversation_id"))

        result = RAGService.ask_multi(
            question=d["question"],
            document_ids=owned_ids,
            conversation_id=d.get("conversation_id"),
            top_k_per_doc=d["top_k_per_doc"],
            top_k_final=d["top_k_final"],
            owner=request.user,
        )

        return Response(result, status=status.HTTP_200_OK)


# --------------------------------------------------------------------------- #
# Agentic workflow                                                             #
# --------------------------------------------------------------------------- #

class AgentAskView(APIView):
    """
    POST /api/agent/ask/
    Body: { "question": "...", "document_ids": [1, 2], "conversation_id": null }
    Returns the agent's final answer with reasoning steps.
    """
    def post(self, request):
        serializer = AgentAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        owned_ids = _validate_owned_document_ids(request.user, d["document_ids"])
        _validate_conversation_access(request.user, d.get("conversation_id"))

        from .services.agent import AgentService

        result = AgentService.run(
            question=d["question"],
            document_ids=owned_ids,
            conversation_id=d.get("conversation_id"),
            owner=request.user,
        )

        return Response(result, status=status.HTTP_200_OK)


# --------------------------------------------------------------------------- #
# Legacy views (kept for backward compatibility)                               #
# --------------------------------------------------------------------------- #

class SearchView(APIView):

    def post(self, request):
        query = request.data["query"]
        document_id = request.data["document_id"]
        document_id = _validate_owned_document_ids(request.user, [document_id])[0]

        results = Retriever.retrieve(
            query=query,
            document_id=document_id,
            owner=request.user,
        )

        data = [
            {
                "content": chunk.content,
                "distance": float(chunk.distance)
            }
            for chunk in results
        ]

        return Response(data)


class AskDocumentView(APIView):

    def post(self, request):
        question = request.data.get("question")
        document_id = request.data.get("document_id")

        if not question:
            return Response(
                {"error": "Question is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not document_id:
            return Response(
                {"error": "document_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        document_id = _validate_owned_document_ids(request.user, [document_id])[0]
        _validate_conversation_access(request.user, request.data.get("conversation_id"), document_id)

        try:
            result = RAGService.ask(
                question=question,
                document_id=document_id,
                conversation_id=request.data.get("conversation_id"),
                owner=request.user,
            )
            return Response(result)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
