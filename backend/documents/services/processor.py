from .extractor import PDFExtractor
from .chunker import TextChunker
from documents.models import DocumentChunk

class DocumentProcessor:
    @staticmethod
    def process_document(document):
        text = PDFExtractor.extract_text(
            document.file.path
        )

        chunks = TextChunker.chunk_text(text)

        for index, chunk in enumerate(chunks):

            DocumentChunk.objects.create(
                document=document,
                chunk_index=index,
                content=chunk
            )