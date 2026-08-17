from .extractor import PDFExtractor
from .chunker import TextChunker
from .embeddings import create_embedding
from documents.models import DocumentChunk


class DocumentProcessor:

    @staticmethod
    def process_document(document):
        # 1. Extract text from PDF
        text = PDFExtractor.extract_text(
            document.file.path
        )

        # 2. Split text into chunks
        chunks = TextChunker.text_chunker(text)

        # 3. Generate embedding for every chunk
        for chunk in chunks:

            embedding = create_embedding(chunk)
            DocumentChunk.objects.create(
                document=document,
                content=chunk,
                embedding=embedding
            )