from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .serializers import DocumentSerializer
from .models import Document
from rest_framework import status
from rest_framework.response import Response 
from .services.processor import DocumentProcessor
from documents.services.rag import RAGService
class DocumentViewSet(ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    def perform_create(self, serializer):
        document = serializer.save()
        DocumentProcessor.process_document(document) 




from rest_framework.views import APIView
from rest_framework.response import Response
from documents.services.retriever import Retriever

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
            result = RAGService.answer(
                question=question,
                document_id=document_id
            )

            return Response(result)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )