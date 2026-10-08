from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = "__all__"


class AskQuestionSerializer(serializers.Serializer):
    question = serializers.CharField()
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    top_k = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=20
    )


class AskMultiDocumentSerializer(serializers.Serializer):
    question = serializers.CharField()
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=10,
    )
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    top_k_per_doc = serializers.IntegerField(required=False, default=10, min_value=1, max_value=20)
    top_k_final = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)


class AgentAskSerializer(serializers.Serializer):
    question = serializers.CharField()
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=10,
    )
    conversation_id = serializers.IntegerField(required=False, allow_null=True)