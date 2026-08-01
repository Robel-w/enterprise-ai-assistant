from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .serializers import DocumentSerializer
from .models import Document

class DocumentViewSet(ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
