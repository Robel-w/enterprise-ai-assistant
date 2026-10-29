from django.test import SimpleTestCase
from types import SimpleNamespace

from documents.services.chunker import TextChunker
from documents.services.rag import RAGService, _parse_citations
from evaluation.metrics import reciprocal_rank
from unittest.mock import patch


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
