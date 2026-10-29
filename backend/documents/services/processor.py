from .extractor import PDFExtractor
from .chunker import TextChunker
from documents.models import DocumentChunk
from documents.services.embeddings import create_embeddings


class DocumentProcessor:
    @staticmethod
    def process_document(document):
        pages = PDFExtractor.extract_pages(
            document.file.path
        )
        objects = []
        for page in pages:
            chunks = TextChunker.text_chunker(
                page["text"]
            )
            for chunk in chunks:
                objects.append(DocumentChunk(
                    document=document,
                    page_number=page["page_number"],
                    content=chunk,
                ))

        embeddings = create_embeddings([item.content for item in objects])
        for index, (item, embedding) in enumerate(zip(objects, embeddings)):
            item.chunk_index = index
            item.embedding = embedding
        DocumentChunk.objects.bulk_create(objects, batch_size=100)
