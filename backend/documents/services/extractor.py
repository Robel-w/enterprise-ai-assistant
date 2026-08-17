import fitz

class PDFExtractor:
    @staticmethod
    def extract_text(file_path):
        document=fitz.open(file_path)
        text=""
        for page in document:
            text += page.get_text( )
        return text      



