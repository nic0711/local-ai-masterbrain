"""
Pydantic Models für OCR Service
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class OCRRequest(BaseModel):
    """Request Model für OCR-Verarbeitung"""
    file_path: str
    engine: str = Field(default="auto", description="OCR Engine: auto, tesseract, easyocr, surya, hybrid")
    language: str = Field(default="deu+eng", description="Sprachen-Code")
    extract_layout: bool = Field(default=True, description="Layout-Analyse aktivieren")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Mindest-Konfidenz")
    output_format: str = Field(default="json", description="Ausgabeformat: json, text, markdown")


class TextBox(BaseModel):
    """Textbox mit Position und Konfidenz"""
    text: str
    confidence: float
    bbox: List[int] = Field(description="Bounding box [x1, y1, x2, y2]")


class LayoutData(BaseModel):
    """Layout-Informationen einer Seite"""
    page: int
    boxes: List[TextBox]


class OCRResult(BaseModel):
    """Ergebnis der OCR-Verarbeitung"""
    text: str
    confidence_score: float
    layout_data: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = {}
    engine_used: Optional[str] = None
    processing_time: Optional[float] = None


class OCRResponse(BaseModel):
    """API Response für OCR-Request"""
    request_id: str
    filename: str
    engine_used: str
    processing_time: float
    confidence_score: float
    text: str
    layout_data: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)


class BatchOCRResponse(BaseModel):
    """Response für Batch-Verarbeitung"""
    batch_id: str
    total_files: int
    processed_files: int
    failed_files: int
    results: List[OCRResponse]
    processing_time: float
    timestamp: datetime = Field(default_factory=datetime.now)


class EngineStatus(BaseModel):
    """Status einer OCR-Engine"""
    name: str
    available: bool
    version: Optional[str] = None
    supported_languages: List[str] = []
    performance_score: Optional[float] = None


class ServiceStats(BaseModel):
    """Service-Statistiken"""
    total_processed: int
    engine_usage: Dict[str, int]
    average_processing_time: float
    error_count: int
    uptime: float
    available_engines: List[EngineStatus]