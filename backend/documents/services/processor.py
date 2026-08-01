try:
    import fitz  # type: ignore[import-not-found]
except ImportError:
    import pymupdf as fitz  # type: ignore[import-not-found]
