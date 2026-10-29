
import re


class TextChunker:
    @staticmethod
    def text_chunker(text, chunk_size=500, overlap=75):
        """Split text near sentence/word boundaries with a small overlap."""
        if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
            raise ValueError("Require chunk_size > overlap >= 0.")

        text = text.strip()
        if not text:
            return []

        chunks = []
        start = 0
        while start < len(text):
            hard_end = min(start + chunk_size, len(text))
            end = hard_end
            if hard_end < len(text):
                # Prefer a sentence boundary in the latter half; otherwise a word boundary.
                window = text[start:hard_end]
                sentence_ends = [m.end() for m in re.finditer(r"[.!?](?:\s|$)", window)]
                boundary = next((p for p in reversed(sentence_ends) if p >= chunk_size // 2), None)
                if boundary is None:
                    boundary = window.rfind(" ")
                if boundary > 0:
                    end = start + boundary

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break

            next_start = max(start + 1, end - overlap)
            # Do not begin the next chunk halfway through a word.
            while next_start < end and not text[next_start - 1].isspace():
                next_start += 1
            start = next_start

        return chunks
