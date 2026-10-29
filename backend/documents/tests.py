from django.test import Client, SimpleTestCase
from types import SimpleNamespace

from documents.services.chunker import TextChunker
from documents.services.rag import RAGService, _parse_citations
from documents.serializers import DocumentSerializer
from documents.views import (
    DocumentViewSet,
    _validate_conversation_access,
    _validate_owned_document_ids,
)
from rest_framework.exceptions import NotFound, ValidationError
from evaluation.metrics import reciprocal_rank
from unittest.mock import Mock, patch
from types import SimpleNamespace


class TextChunkerTests(SimpleTestCase):
    def test_chunks_preserve_text_and_overlap(self):
        text = "First sentence is here. Second sentence is here. Third sentence is here."
        chunks = TextChunker.text_chunker(text, chunk_size=35, overlap=8)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk == chunk.strip() for chunk in chunks))
        self.assertIn("First sentence is here.", " ".join(chunks))
        self.assertTrue(any(set(a.split()) & set(b.split()) for a, b in zip(chunks, chunks[1:])))

    def test_empty_text_returns_no_chunks(self):
        self.assertEqual(TextChunker.text_chunker("  "), [])


class ReciprocalRankTests(SimpleTestCase):
    def test_rank_uses_evidence_text_not_database_ids(self):
        chunks = [
            SimpleNamespace(content="unrelated material"),
            SimpleNamespace(content="The key evidence appears here."),
        ]
        self.assertEqual(reciprocal_rank(chunks, "KEY EVIDENCE"), 0.5)

    def test_missing_evidence_has_zero_rank(self):
        self.assertEqual(reciprocal_rank([], "specific evidence"), 0)


class CitationParsingTests(SimpleTestCase):
    def test_parses_unique_page_citations(self):
        self.assertEqual(_parse_citations("Claim [Page 4]. Another [Page 2][Page 4]."), [2, 4])


class EmptyRetrievalTests(SimpleTestCase):
    @patch("documents.services.rag.Reranker.rerank")
    @patch("documents.services.rag.Retriever.retrieve", return_value=[])
    @patch("documents.services.rag.Message.objects.create")
    @patch("documents.services.rag._get_or_create_conversation")
    def test_ask_returns_fallback_without_reranking(self, get_conversation, _save, _retrieve, rerank):
        get_conversation.return_value = SimpleNamespace(id=10)
        result = RAGService.ask("No answer?", document_id=4)
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["citations"], [])
        rerank.assert_not_called()

    @patch("documents.services.rag.Reranker.rerank")
    @patch("documents.services.rag.Retriever.retrieve", return_value=[])
    @patch("documents.services.rag.Message.objects.create")
    @patch("documents.services.rag._get_or_create_conversation")
    def test_stream_returns_fallback_without_reranking(self, get_conversation, _save, _retrieve, rerank):
        get_conversation.return_value = SimpleNamespace(id=11)
        frames = list(RAGService.ask_stream("No answer?", document_id=4))
        self.assertEqual(len(frames), 2)
        rerank.assert_not_called()


class DocumentOwnershipTests(SimpleTestCase):
    def test_document_owner_and_file_url_are_not_writable_or_exposed(self):
        serializer = DocumentSerializer()
        self.assertTrue(serializer.fields["owner"].read_only)
        self.assertTrue(serializer.fields["file"].write_only)

    @patch("documents.views.Document.objects.filter")
    def test_owner_filter_is_applied_to_document_list(self, document_filter):
        user = SimpleNamespace(id=17)
        marker = object()
        document_filter.return_value = marker
        view = DocumentViewSet()
        view.request = SimpleNamespace(user=user)
        self.assertIs(view.get_queryset(), marker)
        document_filter.assert_called_once_with(owner=user)

    @patch("documents.views.DocumentProcessor.process_document")
    def test_upload_assigns_owner_from_authenticated_request(self, process_document):
        user = SimpleNamespace(id=21)
        document = SimpleNamespace(id=8)
        view = DocumentViewSet()
        view.request = SimpleNamespace(user=user)
        serializer = SimpleNamespace(save=Mock(return_value=document))
        view.perform_create(serializer)
        serializer.save.assert_called_once_with(owner=user)
        process_document.assert_called_once_with(document)

    @patch("documents.views.Document.objects.filter")
    def test_rejects_ids_not_owned_by_request_user(self, document_filter):
        document_filter.return_value.values_list.return_value = [3]
        with self.assertRaises(NotFound):
            _validate_owned_document_ids(SimpleNamespace(id=1), [3, 4])

    def test_rejects_duplicate_document_ids(self):
        with self.assertRaises(ValidationError):
            _validate_owned_document_ids(SimpleNamespace(id=1), [3, 3])

    @patch("documents.views.Document.objects.filter")
    @patch("documents.views.Conversation.objects.get")
    def test_rejects_conversations_with_foreign_documents(self, get_conversation, document_filter):
        get_conversation.return_value = SimpleNamespace(
            document_id=None,
            documents=SimpleNamespace(values_list=Mock(return_value=[9])),
        )
        document_filter.return_value.values_list.return_value = []
        with self.assertRaises(NotFound):
            _validate_conversation_access(SimpleNamespace(id=1), 4)

    def test_unauthenticated_api_cannot_list_documents(self):
        response = self.client.get("/api/documents/")
        self.assertEqual(response.status_code, 403)

    def test_csrf_endpoint_sets_cookie_and_login_rejects_missing_token(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/api/auth/csrf/")
        self.assertIn("csrftoken", response.cookies)
        denied = client.post(
            "/api/auth/login/",
            data='{"username":"demo","password":"bad"}',
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)
