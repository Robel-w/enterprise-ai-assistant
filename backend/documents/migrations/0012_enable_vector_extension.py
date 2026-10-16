from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    dependencies = [("documents", "0011_conversation_documents_alter_conversation_document")]

    operations = [VectorExtension()]
