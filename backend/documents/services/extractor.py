import fitz


class PDFExtractor:

    @staticmethod
    def extract_pages(file_path):
        document = fitz.open(file_path)

        pages = []

        for page_number, page in enumerate(document, start=1):
            text = page.get_text()

            if text.strip():
                pages.append({
                    "page_number": page_number,
                    "text": text
                })

        document.close()

        return pages