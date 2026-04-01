"""
Tests for python-nlp-service app.py.

All external dependencies (spaCy, Neo4j, Ollama/requests, PyMuPDF) are mocked
so tests can run without any installed models or network services.
"""

import base64
import io
import json
import sys
import types
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: inject lightweight stubs for heavy dependencies before importing
# app so that the module-level initialize_nlp_models() call does not fail.
# ---------------------------------------------------------------------------

def _make_spacy_stub():
    """Return a minimal spacy stub whose load() returns a usable mock model."""
    spacy_mod = types.ModuleType("spacy")

    def _load(name):
        model = MagicMock()
        # doc.ents should be an iterable of entity-like objects
        ent = MagicMock()
        ent.text = "Berlin"
        ent.label_ = "LOC"
        ent.start_char = 0
        ent.end_char = 6
        doc = MagicMock()
        doc.ents = [ent]
        model.return_value = doc
        return model

    spacy_mod.load = _load
    return spacy_mod


def _make_fitz_stub():
    fitz_mod = types.ModuleType("fitz")

    class _FakeDoc:
        def __init__(self, pages=1, text="Hello world"):
            def _make_page(t):
                page = MagicMock()
                page.get_text.return_value = t
                pix = MagicMock()
                pix.tobytes = lambda fmt: b"PNGDATA"
                page.get_pixmap.return_value = pix
                return page
            self._pages = [_make_page(text) for _ in range(pages)]

        def __len__(self):
            return len(self._pages)

        def __iter__(self):
            return iter(self._pages)

        def close(self):
            pass

    def _open(stream=None, filetype=None):  # noqa: ARG001
        # Return a doc with 1 page and some default text
        doc = _FakeDoc()
        doc.__iter__ = lambda self: iter(self._pages)
        return doc

    fitz_mod.open = _open
    fitz_mod.Matrix = MagicMock(return_value=MagicMock())
    return fitz_mod


def _make_neo4j_stub():
    neo4j_mod = types.ModuleType("neo4j")
    neo4j_mod.GraphDatabase = MagicMock()
    return neo4j_mod


# Inject stubs before importing app
sys.modules.setdefault("spacy", _make_spacy_stub())
sys.modules.setdefault("fitz", _make_fitz_stub())
sys.modules.setdefault("neo4j", _make_neo4j_stub())

# Now import app (module-level code runs here)
import app as app_module  # noqa: E402

# Mark service as ready so endpoints don't return 503
app_module.service_ready = True
app_module.nlp_models = {
    "de": app_module.nlp_models.get("de") or MagicMock(),
    "en": app_module.nlp_models.get("en") or MagicMock(),
}

# Patch _get_nlp to always return a usable model that yields a predictable entity
def _patched_get_nlp(lang: str):
    model = MagicMock()
    ent = MagicMock()
    ent.text = "Berlin"
    ent.label_ = "LOC"
    ent.start_char = 0
    ent.end_char = 6
    doc = MagicMock()
    doc.ents = [ent]
    model.return_value = doc
    return model


app_module._get_nlp = _patched_get_nlp


@pytest.fixture()
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


# ===========================================================================
# 1. Health endpoint
# ===========================================================================

class TestHealth:
    def test_health_ready(self, client):
        """Returns 200 with healthy status when service is ready."""
        app_module.service_ready = True
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "healthy"
        assert body["ready"] is True

    def test_health_not_ready(self, client):
        """Returns 503 when service is not ready."""
        app_module.service_ready = False
        resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.get_json()
        assert body["status"] == "starting"
        assert body["ready"] is False
        app_module.service_ready = True  # restore


# ===========================================================================
# 2. Status endpoint
# ===========================================================================

class TestStatus:
    def test_status_structure(self, client):
        """Status endpoint returns expected keys."""
        resp = client.get("/status")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "version" in body
        assert "endpoints" in body
        assert "/health" in body["endpoints"]


# ===========================================================================
# 3. /process — NER endpoint
# ===========================================================================

class TestProcessText:
    def test_process_valid_text(self, client):
        """Valid text returns entities list."""
        app_module.service_ready = True
        resp = client.post(
            "/process",
            json={"text": "Berlin ist eine Stadt.", "lang": "de"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["processed"] is True
        assert isinstance(body["entities"], list)

    def test_process_missing_text_field(self, client):
        """Missing 'text' key returns 400."""
        resp = client.post("/process", json={"lang": "de"})
        assert resp.status_code == 400

    def test_process_empty_text(self, client):
        """Empty string for text returns 400."""
        resp = client.post("/process", json={"text": ""})
        assert resp.status_code == 400

    def test_process_text_too_long(self, client):
        """Text exceeding MAX_TEXT_LENGTH returns 413."""
        long_text = "a" * (app_module.MAX_TEXT_LENGTH + 1)
        resp = client.post("/process", json={"text": long_text})
        assert resp.status_code == 413

    def test_process_no_json_body(self, client):
        """Non-JSON request body returns 400."""
        resp = client.post("/process", data="not json", content_type="text/plain")
        assert resp.status_code == 400

    def test_process_unsupported_lang_defaults_to_de(self, client):
        """Unsupported language silently falls back to 'de'."""
        resp = client.post("/process", json={"text": "Test", "lang": "zz"})
        assert resp.status_code == 200
        assert resp.get_json()["language"] == "de"

    def test_process_service_not_ready(self, client):
        """Returns 503 when service is not ready."""
        app_module.service_ready = False
        resp = client.post("/process", json={"text": "Test"})
        assert resp.status_code == 503
        app_module.service_ready = True


# ===========================================================================
# 4. /pdf/analyze-type
# ===========================================================================

class TestPdfAnalyzeType:
    def test_missing_file(self, client):
        """No file in request returns 400."""
        resp = client.post("/pdf/analyze-type")
        assert resp.status_code == 400

    def test_valid_pdf(self, client):
        """Valid PDF upload returns expected JSON keys."""
        fake_pdf = b"%PDF-1.4 fake"
        data = {"file": (io.BytesIO(fake_pdf), "test.pdf")}
        resp = client.post(
            "/pdf/analyze-type",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "extracted_text" in body
        assert "needs_ocr" in body
        assert "page_count" in body

    def test_file_too_large(self, client):
        """File exceeding MAX_FILE_SIZE returns 413."""
        big_content = b"x" * (app_module.MAX_FILE_SIZE + 1)
        data = {"file": (io.BytesIO(big_content), "big.pdf")}
        resp = client.post(
            "/pdf/analyze-type",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 413


# ===========================================================================
# 5. /pdf/to-png-smart
# ===========================================================================

class TestPdfToPngSmart:
    def test_missing_file(self, client):
        resp = client.post("/pdf/to-png-smart")
        assert resp.status_code == 400

    def test_valid_pdf_returns_pages(self, client):
        fake_pdf = b"%PDF-1.4 fake"
        data = {"file": (io.BytesIO(fake_pdf), "test.pdf")}
        resp = client.post(
            "/pdf/to-png-smart",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "pages" in body
        assert "page_count" in body
        assert isinstance(body["pages"], list)


# ===========================================================================
# 6. /pdf/extract
# ===========================================================================

class TestPdfExtract:
    def test_missing_file(self, client):
        resp = client.post("/pdf/extract")
        assert resp.status_code == 400

    def test_direct_text_extraction(self, client):
        """PDF with enough text does not trigger OCR."""
        fake_pdf = b"%PDF-1.4 fake"
        # Patch _pdf_extract_text to return text long enough to skip OCR
        with patch.object(app_module, "_pdf_extract_text", return_value=("Long enough text " * 5, 1)):
            data = {"file": (io.BytesIO(fake_pdf), "test.pdf")}
            resp = client.post(
                "/pdf/extract",
                data=data,
                content_type="multipart/form-data",
            )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "text" in body
        assert body["needs_ocr"] is False

    def test_ocr_path_ollama_error_returns_502(self, client):
        """When Ollama is unreachable during OCR, returns 502."""
        fake_pdf = b"%PDF-1.4 fake"
        with patch.object(app_module, "_pdf_extract_text", return_value=("", 1)), \
             patch.object(app_module, "_pdf_to_png_pages", return_value=[b"PNGDATA"]), \
             patch.object(app_module, "_ocr_image_with_ollama", side_effect=RuntimeError("Ollama nicht erreichbar")):
            data = {"file": (io.BytesIO(fake_pdf), "test.pdf")}
            resp = client.post(
                "/pdf/extract",
                data=data,
                content_type="multipart/form-data",
            )
        assert resp.status_code == 502


# ===========================================================================
# 7. /document/analyze
# ===========================================================================

class TestDocumentAnalyze:
    def test_json_text_input(self, client):
        """JSON with text field returns entities."""
        resp = client.post(
            "/document/analyze",
            json={"text": "Angela Merkel war Bundeskanzlerin.", "lang": "de"},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "entities" in body
        assert "entity_count" in body

    def test_empty_text_returns_400(self, client):
        """Empty text in JSON body returns 400."""
        resp = client.post("/document/analyze", json={"text": ""})
        assert resp.status_code == 400

    def test_service_not_ready_returns_503(self, client):
        app_module.service_ready = False
        resp = client.post("/document/analyze", json={"text": "Test"})
        assert resp.status_code == 503
        app_module.service_ready = True


# ===========================================================================
# 8. /graph/query input validation
# ===========================================================================

class TestGraphQuery:
    def _neo4j_session_mock(self):
        """Returns a context-manager mock for driver.session()."""
        driver = MagicMock()
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        session.run = MagicMock(return_value=[])
        driver.session = MagicMock(return_value=session)
        return driver

    def test_missing_query_returns_400(self, client):
        resp = client.post("/graph/query", json={"limit": 5})
        assert resp.status_code == 400

    def test_invalid_limit_type_returns_400(self, client):
        """Non-integer limit should return 400 instead of crashing."""
        resp = client.post("/graph/query", json={"query": "Berlin", "limit": "bad"})
        assert resp.status_code == 400

    def test_no_json_body_returns_400(self, client):
        resp = client.post("/graph/query", data="not json", content_type="text/plain")
        assert resp.status_code == 400

    def test_valid_query_returns_results(self, client):
        """Valid query with mocked Neo4j returns result structure."""
        driver = self._neo4j_session_mock()
        with patch.object(app_module, "_get_neo4j", return_value=driver):
            resp = client.post("/graph/query", json={"query": "Berlin"})
        assert resp.status_code == 200
        body = resp.get_json()
        assert "results" in body
        assert "total" in body

    def test_limit_capped_at_50(self, client):
        """limit > 50 is silently capped to 50."""
        driver = self._neo4j_session_mock()
        with patch.object(app_module, "_get_neo4j", return_value=driver):
            resp = client.post("/graph/query", json={"query": "Berlin", "limit": 999})
        assert resp.status_code == 200


# ===========================================================================
# 9. /graph/index input validation
# ===========================================================================

class TestGraphIndex:
    def _neo4j_driver_mock(self):
        driver = MagicMock()
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        session.run = MagicMock(return_value=MagicMock())
        driver.session = MagicMock(return_value=session)
        return driver

    def test_missing_path_returns_400(self, client):
        resp = client.post("/graph/index", json={"text": "some text"})
        assert resp.status_code == 400

    def test_text_too_long_returns_413(self, client):
        long_text = "a" * (app_module.MAX_TEXT_LENGTH + 1)
        resp = client.post("/graph/index", json={"path": "/notes/test.md", "text": long_text})
        assert resp.status_code == 413

    def test_valid_index_request(self, client):
        driver = self._neo4j_driver_mock()
        with patch.object(app_module, "_get_neo4j", return_value=driver):
            resp = client.post(
                "/graph/index",
                json={
                    "path": "/notes/test.md",
                    "title": "Test Note",
                    "text": "Berlin ist eine deutsche Stadt.",
                    "tags": ["geography"],
                    "vault": "personal",
                    "lang": "de",
                },
            )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "ok"
        assert "entities_indexed" in body


# ===========================================================================
# 10. Internal helper: _needs_ocr
# ===========================================================================

class TestNeedsOcr:
    def test_empty_text_needs_ocr(self):
        assert app_module._needs_ocr("") is True

    def test_short_text_needs_ocr(self):
        assert app_module._needs_ocr("short") is True

    def test_long_text_no_ocr(self):
        assert app_module._needs_ocr("x" * 100) is False
