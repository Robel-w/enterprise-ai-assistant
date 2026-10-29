from django.test import SimpleTestCase
from types import SimpleNamespace

from documents.services.chunker import TextChunker
from evaluation.metrics import reciprocal_rank


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
