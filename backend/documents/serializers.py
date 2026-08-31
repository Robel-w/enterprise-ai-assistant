from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields ="__all__"
        
class AskQuestionSerializer(serializers.Serializer):
    question = serializers.CharField()
    top_k = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=20
    )