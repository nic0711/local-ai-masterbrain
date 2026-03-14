"""
Hybrid OCR Service - Kombiniert mehrere OCR-Engines für beste Ergebnisse
Unterstützt: TrOCR (Microsoft), Surya OCR, Tesseract
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
import os
import uuid
import logging
from typing import Optional, List
import json
import time
from datetime import datetime
import io
from PIL import Image

from ocr_engines import OCREngineManager
from models import OCRRequest, OCRResponse, OCRResult
from utils import cleanup_temp_files, validate_file_type

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TrOCR Service",
    description="State-of-the-art OCR Service mit Microsoft TrOCR für LocalSupabase Stack",
    version="2.0.0"
)

# CORS für n8n und andere Services
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OCR Engine Manager initialisieren
ocr_manager = OCREngineManager()

# Temp directories
TEMP_DIR = "/data/temp"
INPUT_DIR = "/data/input"
OUTPUT_DIR = "/data/output"

for dir_path in [TEMP_DIR, INPUT_DIR, OUTPUT_DIR]:
    os.makedirs(dir_path, exist_ok=True)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "trocr", "version": "2.0.0"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    engines_status = ocr_manager.get_engine_status()
    available_engines = ocr_manager.get_available_engines()
    return {
        "status": "healthy",
        "engines": engines_status,
        "available_engines": available_engines,
        "temp_dir": os.path.exists(TEMP_DIR),
        "input_dir": os.path.exists(INPUT_DIR),
        "output_dir": os.path.exists(OUTPUT_DIR)
    }


@app.post("/ocr/process", response_model=OCRResponse)
async def process_ocr(
    file: UploadFile = File(...),
    engine: str = Form("auto"),
    language: str = Form("en"),
    confidence_threshold: float = Form(0.7),
    output_format: str = Form("json")
):
    """
    Hauptendpoint für OCR-Verarbeitung mit Microsoft TrOCR
    
    Args:
        file: Upload-Datei (PDF, Bild, etc.)
        engine: OCR-Engine ("auto", "trocr", "surya", "tesseract")
        language: Sprachen-Code (z.B. "en", "de")
        confidence_threshold: Mindest-Konfidenz für Texterkennung
        output_format: Ausgabeformat ("json", "text")
    """
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Keine Datei hochgeladen")
    
    # Datei-Validierung
    if not validate_file_type(file.filename):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file type. Supported: PDF, PNG, JPG, JPEG, TIFF, BMP"
        )
    
    # Unique ID für diesen Request
    request_id = str(uuid.uuid4())
    temp_file_path = os.path.join(TEMP_DIR, f"{request_id}_{file.filename}")
    
    try:
        # Datei speichern
        async with aiofiles.open(temp_file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"Processing file: {file.filename} with engine: {engine}")
        
        # OCR verarbeiten
        result = await ocr_manager.extract_text(temp_file_path, engine)
        
        # Response erstellen
        response = OCRResponse(
            request_id=request_id,
            filename=file.filename,
            engine_used=result.get("engine_used", "unknown"),
            processing_time=result.get("processing_time", 0.0),
            confidence_score=result.get("confidence", 0.0),
            text=result.get("text", ""),
            layout_data=None,  # TrOCR focuses on text extraction
            metadata={
                "available_engines": ocr_manager.get_available_engines(),
                "language": language,
                "output_format": output_format
            }
        )
        
        logger.info(f"OCR completed for {file.filename} in {result.get('processing_time', 0):.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")
    
    finally:
        # Cleanup
        await cleanup_temp_files([temp_file_path])


@app.post("/ocr/batch")
async def process_batch_ocr(
    files: List[UploadFile] = File(...),
    engine: str = Form("auto"),
    language: str = Form("en"),
    confidence_threshold: float = Form(0.7)
):
    """Batch-Verarbeitung mehrerer Dateien"""
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch")
    
    results = []
    temp_files = []
    
    try:
        for file in files:
            if not validate_file_type(file.filename):
                continue
                
            request_id = str(uuid.uuid4())
            temp_file_path = os.path.join(TEMP_DIR, f"{request_id}_{file.filename}")
            temp_files.append(temp_file_path)
            
            # Datei speichern
            async with aiofiles.open(temp_file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # OCR verarbeiten
            result = await ocr_manager.extract_text(temp_file_path, engine)
            
            results.append({
                "filename": file.filename,
                "request_id": request_id,
                "engine_used": result.get("engine_used", "unknown"),
                "processing_time": result.get("processing_time", 0.0),
                "confidence_score": result.get("confidence", 0.0),
                "text": result.get("text", ""),
                "layout_data": None
            })
        
        return {
            "batch_id": str(uuid.uuid4()),
            "total_files": len(files),
            "processed_files": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch OCR processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")
    
    finally:
        # Cleanup
        await cleanup_temp_files(temp_files)


@app.post("/ocr/process-folder")
async def process_folder_ocr(
    folder_path: str = Form("input"),
    engine: str = Form("auto"),
    language: str = Form("en"),
    confidence_threshold: float = Form(0.7),
    save_results: bool = Form(True),
    archive_files: bool = Form(False)
):
    """
    Verarbeite alle Dateien in einem lokalen Ordner
    
    Args:
        folder_path: Relativer Pfad zum Ordner (input, temp, oder absoluter Pfad)
        engine: OCR-Engine ("auto", "trocr", "tesseract")
        language: Sprachen-Code
        confidence_threshold: Mindest-Konfidenz
        save_results: Ergebnisse in JSON-Datei speichern
        archive_files: Verarbeitete Dateien archivieren statt löschen
    """
    
    # Pfad bestimmen
    if folder_path in ["input", "temp", "output"]:
        if folder_path == "input":
            source_dir = INPUT_DIR
        elif folder_path == "temp":
            source_dir = TEMP_DIR
        else:
            source_dir = OUTPUT_DIR
    else:
        # Absoluter Pfad (mit Sicherheitsprüfung)
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            raise HTTPException(status_code=400, detail=f"Folder not found: {folder_path}")
        source_dir = folder_path
    
    if not os.path.exists(source_dir):
        raise HTTPException(status_code=400, detail=f"Source directory not found: {source_dir}")
    
    # Alle unterstützten Dateien finden
    supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']
    files_to_process = []
    
    for filename in os.listdir(source_dir):
        file_path = os.path.join(source_dir, filename)
        if os.path.isfile(file_path) and any(filename.lower().endswith(ext) for ext in supported_extensions):
            files_to_process.append(file_path)
    
    if not files_to_process:
        return {
            "message": "No supported files found in directory",
            "directory": source_dir,
            "supported_extensions": supported_extensions
        }
    
    # Batch-ID für diese Verarbeitung
    batch_id = str(uuid.uuid4())
    results = []
    processed_files = []
    
    try:
        logger.info(f"Processing {len(files_to_process)} files from {source_dir}")
        
        for file_path in files_to_process:
            filename = os.path.basename(file_path)
            
            try:
                # OCR verarbeiten
                result = await ocr_manager.extract_text(file_path, engine)
                
                file_result = {
                    "filename": filename,
                    "file_path": file_path,
                    "request_id": str(uuid.uuid4()),
                    "engine_used": result.get("engine_used", "unknown"),
                    "processing_time": result.get("processing_time", 0.0),
                    "confidence_score": result.get("confidence", 0.0),
                    "text": result.get("text", ""),
                    "file_size": os.path.getsize(file_path),
                    "processed_at": time.time()
                }
                
                results.append(file_result)
                processed_files.append(file_path)
                
                logger.info(f"Processed {filename} successfully")
                
            except Exception as e:
                logger.error(f"Failed to process {filename}: {str(e)}")
                results.append({
                    "filename": filename,
                    "file_path": file_path,
                    "error": str(e),
                    "status": "failed"
                })
        
        # Ergebnisse speichern wenn gewünscht
        if save_results:
            results_file = os.path.join(OUTPUT_DIR, f"batch_results_{batch_id}.json")
            async with aiofiles.open(results_file, 'w') as f:
                await f.write(json.dumps({
                    "batch_id": batch_id,
                    "processed_at": time.time(),
                    "source_directory": source_dir,
                    "total_files": len(files_to_process),
                    "successful": len([r for r in results if "error" not in r]),
                    "failed": len([r for r in results if "error" in r]),
                    "results": results
                }, indent=2))
            
            logger.info(f"Results saved to {results_file}")
        
        # Dateien archivieren oder löschen
        if archive_files and processed_files:
            archive_dir = os.path.join(OUTPUT_DIR, f"archive_{batch_id}")
            os.makedirs(archive_dir, exist_ok=True)
            
            for file_path in processed_files:
                if os.path.exists(file_path):
                    filename = os.path.basename(file_path)
                    archive_path = os.path.join(archive_dir, filename)
                    os.rename(file_path, archive_path)
            
            logger.info(f"Archived {len(processed_files)} files to {archive_dir}")
        
        return {
            "batch_id": batch_id,
            "source_directory": source_dir,
            "total_files": len(files_to_process),
            "processed_successfully": len([r for r in results if "error" not in r]),
            "failed": len([r for r in results if "error" in r]),
            "results": results,
            "results_saved": save_results,
            "files_archived": archive_files and len(processed_files) > 0
        }
        
    except Exception as e:
        logger.error(f"Folder OCR processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Folder processing failed: {str(e)}")


@app.post("/pdf/analyze")
async def analyze_pdf_type(
    file: UploadFile = File(...)
):
    """
    Analysiert PDF-Typ ohne vollständige OCR-Verarbeitung
    Bestimmt ob PDF Text- oder Bild-basiert ist
    """
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Keine Datei hochgeladen")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Nur PDF-Dateien werden unterstützt")
    
    request_id = str(uuid.uuid4())
    temp_file_path = os.path.join(TEMP_DIR, f"{request_id}_{file.filename}")
    
    try:
        # Datei speichern
        async with aiofiles.open(temp_file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # PDF-Typ analysieren mit pdftotext
        import subprocess
        
        try:
            # Versuche Text zu extrahieren
            result = subprocess.run(
                ['pdftotext', temp_file_path, '-'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                extracted_text = result.stdout.strip()
                text_length = len(extracted_text)
                
                # Bestimme PDF-Typ basierend auf extrahiertem Text
                is_text_pdf = text_length > 100  # Mehr als 100 Zeichen = Text-PDF
                
                return {
                    "pdf_type": "text" if is_text_pdf else "image",
                    "text_length": text_length,
                    "needs_ocr": not is_text_pdf,
                    "analysis_method": "pdftotext",
                    "filename": file.filename,
                    "request_id": request_id
                }
            else:
                # pdftotext fehlgeschlagen, wahrscheinlich Bild-PDF
                return {
                    "pdf_type": "image",
                    "text_length": 0,
                    "needs_ocr": True,
                    "analysis_method": "pdftotext_failed",
                    "filename": file.filename,
                    "request_id": request_id,
                    "error": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {
                "pdf_type": "image",
                "text_length": 0,
                "needs_ocr": True,
                "analysis_method": "timeout",
                "filename": file.filename,
                "request_id": request_id,
                "error": "Analysis timeout"
            }
            
    except Exception as e:
        logger.error(f"PDF analysis failed: {str(e)}")
        return {
            "pdf_type": "image",
            "text_length": 0,
            "needs_ocr": True,
            "analysis_method": "error",
            "filename": file.filename,
            "request_id": request_id,
            "error": str(e)
        }
    
    finally:
        # Cleanup
        await cleanup_temp_files([temp_file_path])


@app.post("/pdf/analyze-type")
async def analyze_pdf_type(file: UploadFile = File(...)):
    """
    Analyze PDF to determine if it contains extractable text or needs OCR
    
    Args:
        file: PDF file to analyze
        
    Returns:
        Analysis results with PDF type information
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported for this endpoint")
    
    request_id = str(uuid.uuid4())
    temp_file_path = None
    
    try:
        # Save uploaded file temporarily
        temp_file_path = f"/data/temp/{request_id}_{file.filename}"
        
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Analyze PDF type
        ocr_engine_manager = OCREngineManager()
        pdf_analysis = ocr_engine_manager._analyze_pdf_type(temp_file_path)
        
        return {
            "request_id": request_id,
            "filename": file.filename,
            "pdf_analysis": pdf_analysis,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"PDF analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF analysis failed: {str(e)}")
    
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {temp_file_path}: {e}")


@app.get("/engines")
async def list_engines():
    """Liste verfügbare OCR-Engines"""
    engines_status = ocr_manager.get_engine_status()
    available_engines = ocr_manager.get_available_engines()
    
    return {
        "available_engines": available_engines,
        "engine_status": engines_status,
        "recommended": "trocr" if "trocr" in available_engines else available_engines[0] if available_engines else "none"
    }


@app.get("/stats")
async def get_stats():
    """Service-Statistiken"""
    engines_status = ocr_manager.get_engine_status()
    available_engines = ocr_manager.get_available_engines()
    
    return {
        "service": "TrOCR Service",
        "version": "2.0.0",
        "engines": {
            "total_available": len(available_engines),
            "engines": available_engines,
            "status": engines_status
        },
        "directories": {
            "temp": os.path.exists(TEMP_DIR),
            "input": os.path.exists(INPUT_DIR),
            "output": os.path.exists(OUTPUT_DIR)
        }
    }


@app.post("/pdf/to-png")
async def convert_pdf_to_png(
    file: UploadFile = File(...),
    dpi: int = Query(300, description="DPI for image conversion (300-600 recommended)"),
    page: int = Query(1, description="Page number to convert (1-based, 0 = all pages)")
):
    """
    Convert a PDF page to PNG image optimized for OCR
    
    Args:
        file: PDF file to convert
        dpi: Resolution for conversion (300-600 DPI recommended)
        page: Page number to convert (1-based indexing, 0 = all pages as ZIP)
    
    Returns:
        PNG image as binary response or ZIP file for all pages
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Validate DPI range
    if not 150 <= dpi <= 600:
        raise HTTPException(status_code=400, detail="DPI must be between 150 and 600")
    
    try:
        # Save uploaded file temporarily
        temp_pdf_path = f"/data/temp/{file.filename}_{int(time.time())}.pdf"
        
        with open(temp_pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        if page == 0:
            # Convert all pages and return as ZIP
            import zipfile
            import tempfile
            
            # Get page count first
            import fitz
            pdf_doc = fitz.open(temp_pdf_path)
            page_count = len(pdf_doc)
            pdf_doc.close()
            
            # Create ZIP file with all pages
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for page_num in range(page_count):
                    png_data = await ocr_manager.convert_pdf_page_to_png(temp_pdf_path, page_num, dpi)
                    zip_file.writestr(f"page_{page_num + 1}.png", png_data)
            
            # Clean up temp file
            os.remove(temp_pdf_path)
            
            zip_buffer.seek(0)
            return Response(
                content=zip_buffer.getvalue(),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename={file.filename}_all_pages.zip",
                    "X-Page-Count": str(page_count),
                    "X-DPI": str(dpi)
                }
            )
        else:
            # Convert single page to PNG
            png_data = await ocr_manager.convert_pdf_page_to_png(temp_pdf_path, page - 1, dpi)
            
            # Clean up temp file
            os.remove(temp_pdf_path)
            
            # Return PNG as binary response
            return Response(
                content=png_data,
                media_type="image/png",
                headers={
                    "Content-Disposition": f"attachment; filename=page_{page}.png",
                    "X-Page-Number": str(page),
                    "X-DPI": str(dpi)
                }
            )
        
    except Exception as e:
        logger.error(f"PDF to PNG conversion failed: {e}")
        # Clean up temp file if it exists
        if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"PDF conversion failed: {str(e)}")


@app.post("/pdf/to-png-all")
async def convert_pdf_all_pages_to_png(
    file: UploadFile = File(...),
    dpi: int = Query(300, description="DPI for image conversion (300-600 recommended)"),
    format: str = Query("zip", description="Output format: 'zip' or 'json'")
):
    """
    Convert ALL pages of a PDF to PNG images
    
    Args:
        file: PDF file to convert
        dpi: Resolution for conversion (300-600 DPI recommended)
        format: Output format - 'zip' for ZIP file, 'json' for base64 encoded images
    
    Returns:
        ZIP file with all pages or JSON with base64 encoded images
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Validate DPI range
    if not 150 <= dpi <= 600:
        raise HTTPException(status_code=400, detail="DPI must be between 150 and 600")
    
    try:
        # Save uploaded file temporarily
        temp_pdf_path = f"/data/temp/{file.filename}_{int(time.time())}.pdf"
        
        with open(temp_pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Get page count
        import fitz
        pdf_doc = fitz.open(temp_pdf_path)
        page_count = len(pdf_doc)
        pdf_doc.close()
        
        if format.lower() == "zip":
            # Return as ZIP file
            import zipfile
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for page_num in range(page_count):
                    png_data = await ocr_manager.convert_pdf_page_to_png(temp_pdf_path, page_num, dpi)
                    zip_file.writestr(f"page_{page_num + 1}.png", png_data)
            
            # Clean up temp file
            os.remove(temp_pdf_path)
            
            zip_buffer.seek(0)
            return Response(
                content=zip_buffer.getvalue(),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename={file.filename}_all_pages.zip",
                    "X-Page-Count": str(page_count),
                    "X-DPI": str(dpi)
                }
            )
        else:
            # Return as JSON with base64 encoded images
            import base64
            
            pages = []
            for page_num in range(page_count):
                png_data = await ocr_manager.convert_pdf_page_to_png(temp_pdf_path, page_num, dpi)
                base64_data = base64.b64encode(png_data).decode('utf-8')
                pages.append({
                    "page_number": page_num + 1,
                    "image_base64": base64_data,
                    "size_bytes": len(png_data)
                })
            
            # Clean up temp file
            os.remove(temp_pdf_path)
            
            return {
                "filename": file.filename,
                "page_count": page_count,
                "dpi": dpi,
                "pages": pages,
                "total_size_bytes": sum(page["size_bytes"] for page in pages)
            }
        
    except Exception as e:
        logger.error(f"PDF to PNG conversion failed: {e}")
        # Clean up temp file if it exists
        if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"PDF conversion failed: {str(e)}")


@app.get("/pdf/page-count")
async def get_pdf_page_count(file: UploadFile = File(...)):
    """
    Get the number of pages in a PDF file
    
    Args:
        file: PDF file to analyze
    
    Returns:
        Page count information
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Save uploaded file temporarily
        temp_pdf_path = f"/data/temp/{file.filename}_{int(time.time())}.pdf"
        
        with open(temp_pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Get page count
        import fitz
        pdf_doc = fitz.open(temp_pdf_path)
        page_count = len(pdf_doc)
        pdf_doc.close()
        
        # Clean up temp file
        os.remove(temp_pdf_path)
        
        return {
            "filename": file.filename,
            "page_count": page_count,
            "pages": list(range(1, page_count + 1))
        }
        
    except Exception as e:
        logger.error(f"PDF page count failed: {e}")
        # Clean up temp file if it exists
        if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"PDF page count failed: {str(e)}")


@app.post("/pdf/to-png-combined")
async def convert_pdf_to_combined_png(
    file: UploadFile = File(...),
    dpi: int = Query(300, description="DPI for image conversion (300-600 recommended)"),
    layout: str = Query("vertical", description="Layout: 'vertical' or 'horizontal'"),
    max_width: int = Query(2000, description="Maximum width for combined image")
):
    """
    Convert ALL pages of a PDF to a single combined PNG image
    Perfect for n8n Tesseract processing - no ZIP handling needed!
    
    Args:
        file: PDF file to convert
        dpi: Resolution for conversion (300-600 DPI recommended)
        layout: How to combine pages - 'vertical' (stack) or 'horizontal' (side by side)
        max_width: Maximum width to prevent huge images
    
    Returns:
        Single PNG image with all pages combined
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Validate DPI range
    if not 150 <= dpi <= 600:
        raise HTTPException(status_code=400, detail="DPI must be between 150 and 600")
    
    try:
        # Save uploaded file temporarily
        temp_pdf_path = f"/data/temp/{file.filename}_{int(time.time())}.pdf"
        
        with open(temp_pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Get all pages as individual PNG data
        import fitz
        pdf_doc = fitz.open(temp_pdf_path)
        page_count = len(pdf_doc)
        pdf_doc.close()
        
        if page_count == 1:
            # Single page - just convert normally
            png_data = await ocr_manager.convert_pdf_page_to_png(temp_pdf_path, 0, dpi)
            os.remove(temp_pdf_path)
            
            return Response(
                content=png_data,
                media_type="image/png",
                headers={
                    "Content-Disposition": f"attachment; filename=combined_{file.filename}.png",
                    "X-Page-Count": "1",
                    "X-DPI": str(dpi),
                    "X-Layout": "single"
                }
            )
        
        # Multiple pages - combine them
        page_images = []
        for page_num in range(page_count):
            png_data = await ocr_manager.convert_pdf_page_to_png(temp_pdf_path, page_num, dpi)
            page_image = Image.open(io.BytesIO(png_data))
            page_images.append(page_image)
        
        # Calculate combined image dimensions
        if layout.lower() == "vertical":
            # Stack vertically
            total_width = max(img.width for img in page_images)
            total_height = sum(img.height for img in page_images)
            
            # Scale down if too wide
            if total_width > max_width:
                scale_factor = max_width / total_width
                total_width = max_width
                total_height = int(total_height * scale_factor)
                page_images = [img.resize((int(img.width * scale_factor), int(img.height * scale_factor)), Image.Resampling.LANCZOS) for img in page_images]
            
            # Create combined image
            combined_image = Image.new('L', (total_width, total_height), color=255)  # White background
            
            y_offset = 0
            for img in page_images:
                # Center horizontally if needed
                x_offset = (total_width - img.width) // 2
                combined_image.paste(img, (x_offset, y_offset))
                y_offset += img.height
                
        else:  # horizontal
            # Side by side
            total_width = sum(img.width for img in page_images)
            total_height = max(img.height for img in page_images)
            
            # Scale down if too wide
            if total_width > max_width:
                scale_factor = max_width / total_width
                total_width = max_width
                total_height = int(total_height * scale_factor)
                page_images = [img.resize((int(img.width * scale_factor), int(img.height * scale_factor)), Image.Resampling.LANCZOS) for img in page_images]
            
            # Create combined image
            combined_image = Image.new('L', (total_width, total_height), color=255)  # White background
            
            x_offset = 0
            for img in page_images:
                # Center vertically if needed
                y_offset = (total_height - img.height) // 2
                combined_image.paste(img, (x_offset, y_offset))
                x_offset += img.width
        
        # Convert combined image to PNG bytes
        png_buffer = io.BytesIO()
        combined_image.save(png_buffer, format='PNG', dpi=(dpi, dpi))
        png_buffer.seek(0)
        
        # Clean up
        os.remove(temp_pdf_path)
        for img in page_images:
            img.close()
        
        return Response(
            content=png_buffer.getvalue(),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=combined_{file.filename}.png",
                "X-Page-Count": str(page_count),
                "X-DPI": str(dpi),
                "X-Layout": layout,
                "X-Combined-Size": f"{combined_image.width}x{combined_image.height}"
            }
        )
        
    except Exception as e:
        logger.error(f"PDF to combined PNG conversion failed: {e}")
        # Clean up temp file if it exists
        if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"PDF conversion failed: {str(e)}")


@app.post("/pdf/to-png-smart")
async def convert_pdf_smart(
    file: UploadFile = File(...),
    dpi: int = Query(300, description="DPI for image conversion (300-600 recommended)"),
    max_pages_combined: int = Query(3, description="Maximum pages to combine (1-5)")
):
    """
    SMART PDF to PNG conversion - automatically handles single and multi-page PDFs
    
    Logic:
    - 1 page: Convert normally
    - 2-3 pages: Combine vertically into single PNG
    - 4+ pages: Convert first page only + warning
    
    Perfect for n8n workflows - no complex handling needed!
    
    Args:
        file: PDF file to convert
        dpi: Resolution for conversion (300-600 DPI recommended)
        max_pages_combined: Maximum pages to combine (1-5)
    
    Returns:
        Single PNG image with optimal handling
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Validate parameters
    if not 150 <= dpi <= 600:
        raise HTTPException(status_code=400, detail="DPI must be between 150 and 600")
    
    if not 1 <= max_pages_combined <= 5:
        raise HTTPException(status_code=400, detail="max_pages_combined must be between 1 and 5")
    
    try:
        # Save uploaded file temporarily
        temp_pdf_path = f"/data/temp/{file.filename}_{int(time.time())}.pdf"
        
        with open(temp_pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Get page count
        import fitz
        pdf_doc = fitz.open(temp_pdf_path)
        page_count = len(pdf_doc)
        pdf_doc.close()
        
        # Smart decision logic
        if page_count == 1:
            # Single page - convert normally
            png_data = await ocr_manager.convert_pdf_page_to_png(temp_pdf_path, 0, dpi)
            os.remove(temp_pdf_path)
            
            return Response(
                content=png_data,
                media_type="image/png",
                headers={
                    "Content-Disposition": f"attachment; filename=smart_{file.filename}.png",
                    "X-Page-Count": "1",
                    "X-DPI": str(dpi),
                    "X-Processing": "single_page",
                    "X-Warning": "none"
                }
            )
            
        elif page_count <= max_pages_combined:
            # Few pages - combine vertically
            page_images = []
            for page_num in range(page_count):
                png_data = await ocr_manager.convert_pdf_page_to_png(temp_pdf_path, page_num, dpi)
                page_image = Image.open(io.BytesIO(png_data))
                page_images.append(page_image)
            
            # Combine vertically with optimal sizing
            total_width = max(img.width for img in page_images)
            total_height = sum(img.height for img in page_images)
            
            # Limit total height to prevent huge images
            max_height = 8000  # Reasonable limit for OCR
            if total_height > max_height:
                scale_factor = max_height / total_height
                total_width = int(total_width * scale_factor)
                total_height = max_height
                page_images = [img.resize((int(img.width * scale_factor), int(img.height * scale_factor)), Image.Resampling.LANCZOS) for img in page_images]
            
            # Create combined image
            combined_image = Image.new('L', (total_width, total_height), color=255)
            
            y_offset = 0
            for img in page_images:
                x_offset = (total_width - img.width) // 2  # Center horizontally
                combined_image.paste(img, (x_offset, y_offset))
                y_offset += img.height
            
            # Convert to PNG
            png_buffer = io.BytesIO()
            combined_image.save(png_buffer, format='PNG', dpi=(dpi, dpi))
            png_buffer.seek(0)
            
            # Clean up
            os.remove(temp_pdf_path)
            for img in page_images:
                img.close()
            
            return Response(
                content=png_buffer.getvalue(),
                media_type="image/png",
                headers={
                    "Content-Disposition": f"attachment; filename=smart_{file.filename}.png",
                    "X-Page-Count": str(page_count),
                    "X-DPI": str(dpi),
                    "X-Processing": "combined_vertical",
                    "X-Warning": "none",
                    "X-Combined-Size": f"{combined_image.width}x{combined_image.height}"
                }
            )
            
        else:
            # Many pages - convert first page only with warning
            png_data = await ocr_manager.convert_pdf_page_to_png(temp_pdf_path, 0, dpi)
            os.remove(temp_pdf_path)
            
            warning_msg = f"PDF has {page_count} pages, only processed page 1. Use /pdf/to-png-combined for all pages."
            
            return Response(
                content=png_data,
                media_type="image/png",
                headers={
                    "Content-Disposition": f"attachment; filename=smart_{file.filename}_page1.png",
                    "X-Page-Count": str(page_count),
                    "X-DPI": str(dpi),
                    "X-Processing": "first_page_only",
                    "X-Warning": warning_msg,
                    "X-Skipped-Pages": str(page_count - 1)
                }
            )
        
    except Exception as e:
        logger.error(f"Smart PDF conversion failed: {e}")
        # Clean up temp file if it exists
        if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"PDF conversion failed: {str(e)}")


@app.post("/debug/file-info")
async def debug_file_info(file: UploadFile = File(...)):
    """
    Debug endpoint to check what file information is received
    Helps troubleshoot n8n file upload issues
    """
    try:
        # Read first few bytes to check file signature
        content_start = await file.read(10)
        await file.seek(0)  # Reset file pointer
        
        # Get file info
        file_info = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file.size if hasattr(file, 'size') else "unknown",
            "first_10_bytes": list(content_start),
            "first_10_bytes_hex": content_start.hex(),
            "is_pdf_signature": content_start.startswith(b'%PDF'),
            "filename_extension": file.filename.split('.')[-1].lower() if file.filename and '.' in file.filename else "no_extension"
        }
        
        return {
            "status": "success",
            "file_info": file_info,
            "validation": {
                "has_filename": bool(file.filename),
                "filename_ends_with_pdf": file.filename.lower().endswith('.pdf') if file.filename else False,
                "content_type_is_pdf": file.content_type == 'application/pdf' if file.content_type else False,
                "has_pdf_signature": content_start.startswith(b'%PDF'),
                "overall_is_pdf": (
                    file.filename and file.filename.lower().endswith('.pdf') and 
                    content_start.startswith(b'%PDF')
                )
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "file_info": {
                "filename": getattr(file, 'filename', 'unknown'),
                "content_type": getattr(file, 'content_type', 'unknown')
            }
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)