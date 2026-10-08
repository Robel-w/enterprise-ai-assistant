from django.shortcuts import render
from django.http import StreamingHttpResponse
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response

from .serializers import (
    DocumentSerializer,
    AskQuestionSerializer,
    AskMultiDocumentSerializer,
    AgentAskSerializer,
)
from .models import Document
from .services.processor import DocumentProcessor
from .services.rag import RAGService
from .services.retriever import Retriever


# --------------------------------------------------------------------------- #
# Documents CRUD + single-doc ask + streaming ask                              #
# --------------------------------------------------------------------------- #

class DocumentViewSet(ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    def perform_create(self, serializer):
        document = serializer.save()
        DocumentProcessor.process_document(document)

    @action(detail=True, methods=["post"], url_path="ask")
    def ask(self, request, pk=None):
        """Single-document RAG with citation highlighting."""
        serializer = AskQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = RAGService.ask(
            question=serializer.validated_data["question"],
            document_id=pk,
            conversation_id=serializer.validated_data.get("conversation_id"),
            top_k=serializer.validated_data["top_k"],
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
        serializer = AskQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        generator = RAGService.ask_stream(
            question=serializer.validated_data["question"],
            document_id=pk,
            conversation_id=serializer.validated_data.get("conversation_id"),
            top_k=serializer.validated_data["top_k"],
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

        result = RAGService.ask_multi(
            question=d["question"],
            document_ids=d["document_ids"],
            conversation_id=d.get("conversation_id"),
            top_k_per_doc=d["top_k_per_doc"],
            top_k_final=d["top_k_final"],
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

        from .services.agent import AgentService

        result = AgentService.run(
            question=d["question"],
            document_ids=d["document_ids"],
            conversation_id=d.get("conversation_id"),
        )

        return Response(result, status=status.HTTP_200_OK)


# --------------------------------------------------------------------------- #
# Legacy views (kept for backward compatibility)                               #
# --------------------------------------------------------------------------- #

class SearchView(APIView):

    def post(self, request):
        query = request.data["query"]
        document_id = request.data["document_id"]

        results = Retriever.retrieve(
            query=query,
            document_id=document_id
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

        try:
            result = RAGService.ask(
                question=question,
                document_id=document_id
            )
            return Response(result)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )