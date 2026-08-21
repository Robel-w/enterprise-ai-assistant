from .extractor import PDFExtractor
from .chunker import TextChunker
from documents.models import DocumentChunk
from documents.services.embeddings import create_embedding


class DocumentProcessor:
    @staticmethod
    def process_document(document):
        pages = PDFExtractor.extract_pages(
            document.file.path
        )
        chunk_index = 0

        for page in pages:
            chunks = TextChunker.text_chunker(
                page["text"]
            )
            for chunk in chunks:
                embedding = create_embedding(chunk)
                DocumentChunk.objects.create(
                    document=document,
                    chunk_index=chunk_index,
                    page_number=page["page_number"],
                    content=chunk,
                    embedding=embedding
                )
                chunk_index += 1