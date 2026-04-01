"""
Tests for the OCR Service FastAPI application.

All OCR engine calls are mocked so tests run without GPU/model downloads.
The FastAPI app is tested via TestClient from httpx (starlette).
"""

import io
import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# ---------------------------------------------------------------------------
# Stub out heavy imports before the app modules are imported
# ---------------------------------------------------------------------------

# Stub torch so OCREngineManager.__init__ doesn't fail on cuda check
torch_stub = MagicMock()
torch_stub.cuda.is_available.return_value = False
sys.modules.setdefault("torch", torch_stub)

# Stub transformers
transformers_stub = MagicMock()
sys.modules.setdefault("transformers", transformers_stub)
sys.modules.setdefault("transformers.TrOCRProcessor", MagicMock())
sys.modules.setdefault("transformers.VisionEncoderDecoderModel", MagicMock())

# Stub surya
surya_stub = MagicMock()
sys.modules.setdefault("surya", surya_stub)
sys.modules.setdefault("surya.ocr", surya_stub)
sys.modules.setdefault("surya.model", surya_stub)
sys.modules.setdefault("surya.model.detection", surya_stub)
sys.modules.setdefault("surya.model.detection.model", surya_stub)
sys.modules.setdefault("surya.model.recognition", surya_stub)
sys.modules.setdefault("surya.model.recognition.model", surya_stub)
sys.modules.setdefault("surya.model.recognition.processor", surya_stub)

# Stub pytesseract
pytesseract_stub = MagicMock()
sys.modules.setdefault("pytesseract", pytesseract_stub)

# Stub cv2
cv2_stub = MagicMock()
sys.modules.setdefault("cv2", cv2_stub)

# Stub fitz / pymupdf
fitz_stub = MagicMock()
sys.modules.setdefault("fitz", fitz_stub)

# ---------------------------------------------------------------------------
# Now set up the app's sys.path and import
# ---------------------------------------------------------------------------

APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))


def _make_mock_engine_manager():
    """Return a fully mocked OCREngineManager."""
    manager = MagicMock()
    manager.get_engine_status.return_value = {
        "trocr": False,
        "surya": False,
        "tesseract": True,
    }
    manager.get_available_engines.return_value = ["tesseract"]
    manager.extract_text = AsyncMock(return_value={
        "text": "Hello World",
        "engine_used": "tesseract",
        "processing_time": 0.5,
        "confidence": 0.85,
    })
    manager._analyze_pdf_type = MagicMock(return_value={
        "needs_ocr": False,
        "text_length": 500,
        "word_count": 80,
        "extracted_text": "Sample PDF text",
        "analysis_method": "pymupdf_text_extraction",
        "pdf_type": "text",
    })
    return manager


# Patch OCREngineManager and os.makedirs before importing main so the
# module-level instantiation and directory creation are mocked.
with patch("ocr_engines.OCREngineManager", return_value=_make_mock_engine_manager()), \
     patch("os.makedirs"):
    import main as app_module  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
import tempfile

# Redirect all file I/O to a real temp directory (avoids /data not existing)
_test_tmpdir = tempfile.mkdtemp()
app_module.TEMP_DIR = _test_tmpdir
app_module.INPUT_DIR = _test_tmpdir
app_module.OUTPUT_DIR = _test_tmpdir

client = TestClient(app_module.app)

# Replace the module-level ocr_manager with a fresh mock for each test
_mock_manager = _make_mock_engine_manager()
app_module.ocr_manager = _mock_manager


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _png_bytes() -> bytes:
    """Minimal valid 1x1 white PNG."""
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (1, 1), color=(255, 255, 255))
    img.save(buf, format="PNG")
    return buf.getvalue()


def _small_pdf_bytes() -> bytes:
    """Minimal PDF-like bytes (not a real PDF, but enough for upload tests)."""
    return b"%PDF-1.4 fake content"


# ---------------------------------------------------------------------------
# Tests: Health / root endpoints
# ---------------------------------------------------------------------------

class TestHealthEndpoints:

    def test_root_returns_healthy(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_health_check_returns_engines(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "engines" in data
        assert "available_engines" in data

    def test_engines_endpoint(self):
        response = client.get("/engines")
        assert response.status_code == 200
        data = response.json()
        assert "available_engines" in data
        assert "engine_status" in data

    def test_stats_endpoint(self):
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


# ---------------------------------------------------------------------------
# Tests: /ocr/process – file upload validation
# ---------------------------------------------------------------------------

class TestOCRProcessValidation:

    def test_no_file_returns_422(self):
        """Missing file body should return 422 Unprocessable Entity."""
        response = client.post("/ocr/process")
        assert response.status_code == 422

    def test_unsupported_file_type_returns_400(self):
        """A .exe upload should be rejected with 400."""
        data = {"engine": "auto", "language": "en", "confidence_threshold": "0.7", "output_format": "json"}
        files = {"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")}
        response = client.post("/ocr/process", files=files, data=data)
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_file_too_large_returns_413(self):
        """A file exceeding MAX_UPLOAD_SIZE_BYTES should be rejected with 413."""
        from utils import MAX_UPLOAD_SIZE_BYTES
        # Fake oversized content by patching validate_file_size
        with patch("main.validate_file_size", return_value=False):
            files = {"file": ("test.png", _png_bytes(), "image/png")}
            data = {"engine": "auto", "language": "en", "confidence_threshold": "0.7", "output_format": "json"}
            response = client.post("/ocr/process", files=files, data=data)
        assert response.status_code == 413

    def test_valid_png_upload_succeeds(self):
        """A valid PNG file should be processed successfully."""
        files = {"file": ("test.png", _png_bytes(), "image/png")}
        data = {"engine": "auto", "language": "en", "confidence_threshold": "0.7", "output_format": "json"}
        response = client.post("/ocr/process", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert result["text"] == "Hello World"
        assert result["engine_used"] == "tesseract"
        assert "request_id" in result

    def test_valid_pdf_upload_succeeds(self):
        """A file with .pdf extension should be accepted."""
        files = {"file": ("document.pdf", _small_pdf_bytes(), "application/pdf")}
        data = {"engine": "auto", "language": "en", "confidence_threshold": "0.7", "output_format": "json"}
        response = client.post("/ocr/process", files=files, data=data)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Tests: /ocr/process – OCR engine mock behaviour
# ---------------------------------------------------------------------------

class TestOCRProcessEngines:

    def test_engine_used_is_returned(self):
        """Response must include which engine was used."""
        files = {"file": ("img.jpg", _png_bytes(), "image/jpeg")}
        data = {"engine": "tesseract", "language": "en", "confidence_threshold": "0.7", "output_format": "json"}
        response = client.post("/ocr/process", files=files, data=data)
        assert response.status_code == 200
        assert response.json()["engine_used"] == "tesseract"

    def test_ocr_engine_error_returns_500(self):
        """When the engine raises, the endpoint should return 500."""
        app_module.ocr_manager.extract_text = AsyncMock(side_effect=RuntimeError("GPU OOM"))
        files = {"file": ("img.png", _png_bytes(), "image/png")}
        data = {"engine": "auto", "language": "en", "confidence_threshold": "0.7", "output_format": "json"}
        response = client.post("/ocr/process", files=files, data=data)
        assert response.status_code == 500
        # Restore
        app_module.ocr_manager.extract_text = AsyncMock(return_value={
            "text": "Hello World",
            "engine_used": "tesseract",
            "processing_time": 0.5,
            "confidence": 0.85,
        })

    def test_confidence_score_in_response(self):
        """Confidence score should be present and within 0-1."""
        files = {"file": ("img.png", _png_bytes(), "image/png")}
        data = {"engine": "auto", "language": "en", "confidence_threshold": "0.7", "output_format": "json"}
        response = client.post("/ocr/process", files=files, data=data)
        assert response.status_code == 200
        score = response.json()["confidence_score"]
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Tests: /ocr/batch
# ---------------------------------------------------------------------------

class TestBatchOCR:

    def test_batch_with_valid_files(self):
        files = [
            ("files", ("a.png", _png_bytes(), "image/png")),
            ("files", ("b.png", _png_bytes(), "image/png")),
        ]
        data = {"engine": "auto", "language": "en", "confidence_threshold": "0.7"}
        response = client.post("/ocr/batch", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert result["total_files"] == 2
        assert "results" in result

    def test_batch_too_many_files_returns_400(self):
        """More than 10 files should be rejected."""
        files = [("files", (f"img{i}.png", _png_bytes(), "image/png")) for i in range(11)]
        data = {"engine": "auto", "language": "en", "confidence_threshold": "0.7"}
        response = client.post("/ocr/batch", files=files, data=data)
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Tests: Path traversal prevention (sanitize_filename)
# ---------------------------------------------------------------------------

class TestSanitizeFilename:

    def test_sanitize_removes_path_traversal(self):
        from utils import sanitize_filename
        assert ".." not in sanitize_filename("../../etc/passwd")
        assert "/" not in sanitize_filename("../../etc/passwd")

    def test_sanitize_keeps_valid_name(self):
        from utils import sanitize_filename
        result = sanitize_filename("document.pdf")
        assert result == "document.pdf"

    def test_sanitize_empty_string(self):
        from utils import sanitize_filename
        assert sanitize_filename("") == "unknown"

    def test_sanitize_dotdot_only(self):
        from utils import sanitize_filename
        assert sanitize_filename("..") == "unknown"

    def test_sanitize_removes_null_byte(self):
        from utils import sanitize_filename
        result = sanitize_filename("file\x00.png")
        assert "\x00" not in result


# ---------------------------------------------------------------------------
# Tests: validate_file_size
# ---------------------------------------------------------------------------

class TestValidateFileSize:

    def test_zero_bytes_rejected(self):
        from utils import validate_file_size
        assert validate_file_size(0) is False

    def test_normal_size_accepted(self):
        from utils import validate_file_size
        assert validate_file_size(1024) is True

    def test_oversized_rejected(self):
        from utils import validate_file_size
        assert validate_file_size(100 * 1024 * 1024) is False  # 100 MB

    def test_exact_limit_accepted(self):
        from utils import validate_file_size, MAX_UPLOAD_SIZE_BYTES
        assert validate_file_size(MAX_UPLOAD_SIZE_BYTES) is True

    def test_just_over_limit_rejected(self):
        from utils import validate_file_size, MAX_UPLOAD_SIZE_BYTES
        assert validate_file_size(MAX_UPLOAD_SIZE_BYTES + 1) is False


# ---------------------------------------------------------------------------
# Tests: validate_file_type
# ---------------------------------------------------------------------------

class TestValidateFileType:

    def test_pdf_accepted(self):
        from utils import validate_file_type
        assert validate_file_type("report.pdf") is True

    def test_png_accepted(self):
        from utils import validate_file_type
        assert validate_file_type("scan.PNG") is True

    def test_jpeg_accepted(self):
        from utils import validate_file_type
        assert validate_file_type("photo.JPEG") is True

    def test_exe_rejected(self):
        from utils import validate_file_type
        assert validate_file_type("evil.exe") is False

    def test_empty_name_rejected(self):
        from utils import validate_file_type
        assert validate_file_type("") is False

    def test_no_extension_rejected(self):
        from utils import validate_file_type
        assert validate_file_type("noextension") is False


# ---------------------------------------------------------------------------
# Tests: /pdf/analyze-type
# ---------------------------------------------------------------------------

class TestPDFAnalyzeType:

    def test_non_pdf_returns_400(self):
        files = {"file": ("image.png", _png_bytes(), "image/png")}
        response = client.post("/pdf/analyze-type", files=files)
        assert response.status_code == 400

    def test_valid_pdf_returns_analysis(self):
        files = {"file": ("doc.pdf", _small_pdf_bytes(), "application/pdf")}
        response = client.post("/pdf/analyze-type", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "pdf_analysis" in data
        assert "request_id" in data
