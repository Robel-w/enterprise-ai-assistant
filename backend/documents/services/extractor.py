import fitz

class PDFExtractor:
    @staticmethod
    def exstact_text(file_path):
        document=fitz.open(file_path)
        txt=""
        for page in document:
            text += page.get_text( )
        return text      

