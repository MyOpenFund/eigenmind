"""Unit tests for the optional use_ocr override of the ChunkNorris path."""
import inspect

from eigenmind.core.chunking import _file_parser_for, chunk_with_chunknorris


def test_chunk_with_chunknorris_accepts_use_ocr_kwarg():
    params = inspect.signature(chunk_with_chunknorris).parameters
    assert "use_ocr" in params
    assert params["use_ocr"].default is None


def test_pdf_parser_honors_explicit_never():
    parser = _file_parser_for(".pdf", use_ocr="never")
    assert parser.use_ocr == "never"


def test_pdf_parser_default_is_env_driven(monkeypatch):
    # With OCR unavailable (default in test env), None must yield "never",
    # exactly as before the change.
    monkeypatch.setattr("eigenmind.core.chunking.ocr_available", lambda: False)
    parser = _file_parser_for(".pdf", use_ocr=None)
    assert parser.use_ocr == "never"


def test_non_pdf_parsers_ignore_use_ocr():
    parser = _file_parser_for(".docx", use_ocr="always")
    assert type(parser).__name__ == "DocxParser"
