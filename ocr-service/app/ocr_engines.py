"""
Advanced OCR Engines - TrOCR (Primary) + Surya OCR (Fallback) + Tesseract (Backup)
"""

import time
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
import os
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import io

# Increase PIL decompression-bomb limit for large PDFs.
# Default is ~178 MP. We raise to 300 MP to handle high-DPI PDFs.
# WARNING: Only accept files from trusted sources when this limit is raised.
Image.MAX_IMAGE_PIXELS = 300_000_000  # 300 MP

# PDF processing imports
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# TrOCR imports (Microsoft's state-of-the-art OCR)
try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    import torch
    TROCR_AVAILABLE = True
except ImportError:
    TROCR_AVAILABLE = False

# Surya OCR imports
try:
    from surya.ocr import run_ocr
    from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
    from surya.model.recognition.model import load_model as load_rec_model
    from surya.model.recognition.processor import load_processor as load_rec_processor
    SURYA_AVAILABLE = True
except ImportError:
    SURYA_AVAILABLE = False

# Tesseract OCR imports
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from models import OCRRequest, OCRResult

logger = logging.getLogger(__name__)

class OCREngineManager:
    """
    Manages multiple OCR engines with intelligent fallback strategy.
    Priority: TrOCR > Surya OCR > Tesseract OCR
    """
    
    def __init__(self):
        self.trocr_processor = None
        self.trocr_model = None
        self.surya_det_model = None
        self.surya_det_processor = None
        self.surya_rec_model = None
        self.surya_rec_processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info("Initializing OCR engines...")
        self._initialize_engines()
        logger.info("OCR engines initialization completed")
    
    def _initialize_engines(self):
        """Initialize all available OCR engines"""
        
        # Initialize TrOCR (Microsoft's state-of-the-art OCR)
        if TROCR_AVAILABLE:
            try:
                logger.info(f"Initializing TrOCR on {self.device}...")
                
                # Use TrOCR large model for best quality
                model_name = "microsoft/trocr-large-printed"
                
                self.trocr_processor = TrOCRProcessor.from_pretrained(model_name)
                self.trocr_model = VisionEncoderDecoderModel.from_pretrained(model_name)
                
                if self.device == "cuda":
                    self.trocr_model = self.trocr_model.to(self.device)
                
                self.trocr_model.eval()
                logger.info("TrOCR initialized successfully")
                        
            except Exception as e:
                logger.error(f"Failed to initialize TrOCR: {e}")
                self.trocr_model = None
                self.trocr_processor = None
        else:
            logger.warning("TrOCR not available - transformers/torch not installed")
        
        # Initialize Surya OCR
        if SURYA_AVAILABLE:
            try:
                logger.info("Initializing Surya OCR...")
                self.surya_det_model = load_det_model()
                self.surya_det_processor = load_det_processor()
                self.surya_rec_model = load_rec_model()
                self.surya_rec_processor = load_rec_processor()
                logger.info("Surya OCR initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Surya OCR: {e}")
                self.surya_det_model = None
        else:
            logger.warning("Surya OCR not available")
        
        # Tesseract is always available as backup
        if not TESSERACT_AVAILABLE:
            logger.warning("Tesseract OCR not available")
    
    def _convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """
        Convert PDF pages to PIL Images for OCR processing
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of PIL Images, one per page
        """
        if not PDF_AVAILABLE:
            raise Exception("PyMuPDF not available for PDF processing")
        
        images = []
        
        try:
            # Open PDF
            pdf_document = fitz.open(pdf_path)
            logger.info(f"PDF opened successfully. Pages: {len(pdf_document)}")
            
            # Convert each page to image
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                
                # Increase resolution for better OCR (600 DPI for better quality)
                mat = fitz.Matrix(600/72, 600/72)  # 600 DPI instead of 300 DPI
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image with optimal settings for OCR
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Resize image if too large (OCR works better with moderate sizes)
                max_dimension = 3000  # Optimal for OCR
                if max(image.size) > max_dimension:
                    ratio = max_dimension / max(image.size)
                    new_size = (int(image.width * ratio), int(image.height * ratio))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
                    logger.info(f"Resized image from {pix.width}x{pix.height} to {image.size} for better OCR")
                
                # Convert to grayscale for better OCR (if not already)
                if image.mode != 'L':
                    image = image.convert('L')
                
                # Enhance contrast for better text recognition
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.2)  # Slight contrast boost
                
                logger.info(f"Page {page_num + 1} converted to image: {image.size} pixels")
                
                # Store original image for TrOCR and preprocessed for Tesseract
                images.append(image)
            
            pdf_document.close()
            logger.info(f"Successfully converted {len(images)} pages to images")
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            raise Exception(f"PDF to image conversion failed: {str(e)}")
        
        return images
    
    def _analyze_pdf_type(self, pdf_path: str) -> Dict[str, Any]:
        """
        Analyze PDF to determine if it contains extractable text or needs OCR
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict with analysis results
        """
        if not PDF_AVAILABLE:
            return {"needs_ocr": True, "text_length": 0, "analysis_method": "no_pymupdf"}
        
        try:
            # Open PDF
            pdf_document = fitz.open(pdf_path)
            total_text = ""
            
            # Extract text from all pages
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                page_text = page.get_text()
                total_text += page_text
            
            pdf_document.close()
            
            # Analyze text content
            text_length = len(total_text.strip())
            word_count = len(total_text.split())
            
            # Determine if OCR is needed
            # If we have substantial text (>100 chars and >10 words), it's likely a text PDF
            needs_ocr = text_length < 100 or word_count < 10
            
            return {
                "needs_ocr": needs_ocr,
                "text_length": text_length,
                "word_count": word_count,
                "extracted_text": total_text if not needs_ocr else "",
                "analysis_method": "pymupdf_text_extraction",
                "pdf_type": "image" if needs_ocr else "text"
            }
            
        except Exception as e:
            logger.error(f"PDF analysis failed: {e}")
            return {
                "needs_ocr": True,
                "text_length": 0,
                "analysis_method": "error",
                "error": str(e)
            }

    async def extract_text(self, file_path: str, engine_preference: str = "auto") -> Dict[str, Any]:
        """
        Extract text from image or PDF using the best available OCR engine
        
        Args:
            file_path: Path to the image or PDF file
            engine_preference: "trocr", "surya", "tesseract", or "auto"
        
        Returns:
            Dict with extracted text and metadata
        """
        start_time = time.time()
        
        try:
            # Check if file is PDF
            if file_path.lower().endswith('.pdf'):
                # First, analyze PDF type
                pdf_analysis = self._analyze_pdf_type(file_path)
                
                if not pdf_analysis["needs_ocr"]:
                    # PDF already contains extractable text - no OCR needed
                    processing_time = time.time() - start_time
                    
                    return {
                        "text": pdf_analysis["extracted_text"],
                        "engine_used": "pdf_text_extraction",
                        "processing_time": processing_time,
                        "confidence": 1.0,  # Perfect confidence for direct text extraction
                        "file_path": file_path,
                        "pdf_analysis": pdf_analysis,
                        "pages_processed": 0,  # No OCR pages processed
                        "method": "direct_text_extraction"
                    }
                else:
                    # PDF needs OCR - convert to images and process
                    logger.info(f"PDF needs OCR (text_length: {pdf_analysis['text_length']}, word_count: {pdf_analysis.get('word_count', 0)})")
                    
                    images = self._convert_pdf_to_images(file_path)
                    
                    # Process all pages with OCR
                    all_text = []
                    for i, image in enumerate(images):
                        logger.info(f"Processing PDF page {i+1}/{len(images)} with OCR")
                        page_result = await self._process_image(image, engine_preference)
                        if page_result.strip():
                            all_text.append(f"--- Page {i+1} ---\n{page_result}")
                    
                    combined_text = "\n\n".join(all_text)
                    engine_used = self._get_engine_for_preference(engine_preference)
                    
                    processing_time = time.time() - start_time
                    
                    return {
                        "text": combined_text,
                        "engine_used": engine_used,
                        "processing_time": processing_time,
                        "confidence": 0.95 if engine_used == "trocr" else 0.85 if engine_used == "surya" else 0.75,
                        "file_path": file_path,
                        "pdf_analysis": pdf_analysis,
                        "pages_processed": len(images),
                        "method": "ocr_processing"
                    }
                
            else:
                # Load single image
                image = Image.open(file_path).convert('RGB')
                combined_text = await self._process_image(image, engine_preference)
                engine_used = self._get_engine_for_preference(engine_preference)
                
                processing_time = time.time() - start_time
                
                return {
                    "text": combined_text,
                    "engine_used": engine_used,
                    "processing_time": processing_time,
                    "confidence": 0.95 if engine_used == "trocr" else 0.85 if engine_used == "surya" else 0.75,
                    "file_path": file_path,
                    "method": "image_ocr"
                }
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return {
                "text": "",
                "engine_used": "none",
                "processing_time": time.time() - start_time,
                "confidence": 0.0,
                "error": str(e),
                "file_path": file_path,
                "method": "error"
            }
    
    def _get_engine_for_preference(self, engine_preference: str) -> str:
        """Get the actual engine that will be used for given preference"""
        if engine_preference == "auto":
            if self.trocr_model is not None:
                return "trocr"
            elif self.surya_det_model is not None:
                return "surya"
            elif TESSERACT_AVAILABLE:
                return "tesseract"
            else:
                return "none"
        elif engine_preference == "trocr" and self.trocr_model is not None:
            return "trocr"
        elif engine_preference == "surya" and self.surya_det_model is not None:
            return "surya"
        elif engine_preference == "tesseract" and TESSERACT_AVAILABLE:
            return "tesseract"
        else:
            return self._get_engine_for_preference("auto")
    
    async def _process_image(self, image: Image.Image, engine_preference: str = "auto") -> str:
        """
        Process a single image with OCR
        
        Args:
            image: PIL Image
            engine_preference: "trocr", "surya", "tesseract", or "auto"
        
        Returns:
            Extracted text
        """
        # Determine which engine to use
        if engine_preference == "auto":
            if self.trocr_model is not None:
                return await self._extract_with_trocr(image)
            elif self.surya_det_model is not None:
                return await self._extract_with_surya(image)
            elif TESSERACT_AVAILABLE:
                return await self._extract_with_tesseract(image)
            else:
                raise Exception("No OCR engines available")
        elif engine_preference == "trocr" and self.trocr_model is not None:
            return await self._extract_with_trocr(image)
        elif engine_preference == "surya" and self.surya_det_model is not None:
            return await self._extract_with_surya(image)
        elif engine_preference == "tesseract" and TESSERACT_AVAILABLE:
            return await self._extract_with_tesseract(image)
        else:
            # Fallback to any available engine
            return await self._process_image(image, "auto")
    
    async def _extract_with_trocr(self, image: Image.Image) -> str:
        """Extract text using TrOCR"""
        try:
            # Preprocess image for TrOCR (keep RGB)
            processed_image = self._preprocess_image_for_ocr(image, for_trocr=True)
            pixel_values = self.trocr_processor(processed_image, return_tensors="pt").pixel_values
            
            if self.device == "cuda":
                pixel_values = pixel_values.to(self.device)
            
            # Generate text
            with torch.no_grad():
                generated_ids = self.trocr_model.generate(pixel_values)
                generated_text = self.trocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            return generated_text.strip()
            
        except Exception as e:
            logger.error(f"TrOCR extraction failed: {e}")
            raise e
    
    async def _extract_with_surya(self, image: Image.Image) -> str:
        """Extract text using Surya OCR"""
        try:
            # Convert PIL image to format expected by Surya
            images = [image]
            langs = ["en"]  # Default to English, can be made configurable
            
            # Run OCR
            predictions = run_ocr(
                images, 
                langs, 
                self.surya_det_model, 
                self.surya_det_processor,
                self.surya_rec_model, 
                self.surya_rec_processor
            )
            
            # Extract text from predictions
            text_lines = []
            for pred in predictions[0].text_lines:
                text_lines.append(pred.text)
            
            return "\n".join(text_lines)
            
        except Exception as e:
            logger.error(f"Surya OCR extraction failed: {e}")
            raise e
    
    async def _extract_with_tesseract(self, image: Image.Image) -> str:
        """Extract text using Tesseract OCR with multiple PSM modes"""
        try:
            logger.info(f"Tesseract processing image: {image.size} pixels, mode: {image.mode}")
            
            # Convert PIL Image to OpenCV format
            if image.mode == 'L':
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_GRAY2BGR)
            elif image.mode == 'RGB':
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            else:
                # Convert to RGB first, then to BGR
                rgb_image = image.convert('RGB')
                cv_image = cv2.cvtColor(np.array(rgb_image), cv2.COLOR_RGB2BGR)
            
            # Try key PSM modes for documents (simplified)
            psm_modes = [
                3,   # Fully automatic page segmentation (best for documents)
                6,   # Uniform block of text
                4,   # Single column of text
            ]
            
            best_text = ""
            best_confidence = 0.0
            
            for psm in psm_modes:
                try:
                    # Simple Tesseract configuration for documents
                    config = f'--oem 1 --psm {psm}'
                    
                    # Extract text with German language
                    text = pytesseract.image_to_string(cv_image, lang="deu", config=config)
                    
                    # Get confidence data
                    data = pytesseract.image_to_data(cv_image, lang="deu", config=config, output_type=pytesseract.Output.DICT)
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    logger.info(f"Tesseract PSM {psm}: {len(text.strip())} chars, confidence: {avg_confidence:.1f}%")
                    
                    # Keep best result
                    if len(text.strip()) > len(best_text.strip()) and avg_confidence > 30:
                        best_text = text
                        best_confidence = avg_confidence / 100.0
                        
                except Exception as e:
                    logger.warning(f"Tesseract PSM {psm} failed: {str(e)}")
                    continue
            
            # Clean up text
            cleaned_text = best_text.strip()
            
            logger.info(f"Tesseract best result: {len(cleaned_text)} characters, confidence: {best_confidence:.2f}")
            
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Tesseract processing failed: {str(e)}")
            raise e
    
    def get_available_engines(self) -> List[str]:
        """Get list of available OCR engines"""
        engines = []
        if self.trocr_model is not None:
            engines.append("trocr")
        if self.surya_det_model is not None:
            engines.append("surya")
        if TESSERACT_AVAILABLE:
            engines.append("tesseract")
        return engines
    
    def get_engine_status(self) -> Dict[str, bool]:
        """Get status of all OCR engines"""
        return {
            "trocr": self.trocr_model is not None,
            "surya": self.surya_det_model is not None,
            "tesseract": TESSERACT_AVAILABLE
        }

    def _preprocess_image_for_ocr(self, image: Image.Image, for_trocr: bool = False) -> Image.Image:
        """
        Preprocess image for better OCR results
        
        Args:
            image: PIL Image to preprocess
            for_trocr: If True, keep RGB for TrOCR compatibility
            
        Returns:
            Preprocessed PIL Image
        """
        try:
            # For TrOCR, keep RGB mode; for Tesseract, convert to grayscale
            if not for_trocr and image.mode != 'L':
                image = image.convert('L')
            elif for_trocr and image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Enhanced preprocessing for Tesseract (gentler approach)
            if not for_trocr:
                # Enhance contrast
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.4)  # Moderate contrast boost
                
                # Enhance sharpness
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(1.2)  # Moderate sharpness boost
                
                # Optional: Apply gentle noise reduction
                image = image.filter(ImageFilter.MedianFilter(size=3))
            else:
                # Basic enhancement for TrOCR
                # Enhance contrast
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.3)  # Moderate contrast boost
                
                # Enhance sharpness
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(1.1)  # Slight sharpness boost
            
            logger.info(f"Image preprocessed for OCR: {image.size} pixels, mode: {image.mode}, for_trocr: {for_trocr}")

            return image
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            return image  # Return original if preprocessing fails

    async def convert_pdf_page_to_png(self, pdf_path: str, page_num: int = 0, dpi: int = 300) -> bytes:
        """
        Convert a specific PDF page to PNG bytes optimized for OCR
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to convert (0-based)
            dpi: Resolution for conversion
            
        Returns:
            PNG image data as bytes
        """
        if not PDF_AVAILABLE:
            raise Exception("PyMuPDF not available for PDF processing")
        
        try:
            # Open PDF
            pdf_document = fitz.open(pdf_path)
            
            # Validate page number
            if page_num >= len(pdf_document):
                raise Exception(f"Page {page_num + 1} does not exist. PDF has {len(pdf_document)} pages.")
            
            logger.info(f"Converting PDF page {page_num + 1} to PNG at {dpi} DPI")
            
            # Load specific page
            page = pdf_document.load_page(page_num)
            
            # Create transformation matrix for desired DPI
            mat = fitz.Matrix(dpi/72, dpi/72)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Optimize image for OCR
            optimized_image = self._optimize_image_for_ocr(image)
            
            # Convert back to PNG bytes
            img_buffer = io.BytesIO()
            optimized_image.save(img_buffer, format='PNG', dpi=(dpi, dpi), optimize=True)
            png_data = img_buffer.getvalue()
            
            # Close PDF
            pdf_document.close()
            
            logger.info(f"Successfully converted page {page_num + 1} to PNG: {optimized_image.size} pixels, {len(png_data)} bytes")
            
            return png_data
            
        except Exception as e:
            logger.error(f"PDF to PNG conversion failed: {e}")
            raise e

    def _optimize_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Optimize image specifically for OCR processing
        
        Args:
            image: PIL Image to optimize
            
        Returns:
            Optimized PIL Image
        """
        try:
            # Convert to grayscale for better OCR performance
            if image.mode != 'L':
                image = image.convert('L')
            
            # Resize if too large (OCR works better with moderate sizes)
            max_dimension = 3000
            if max(image.size) > max_dimension:
                ratio = max_dimension / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"Resized image to {new_size} for optimal OCR")
            
            # Enhance contrast slightly
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            # Enhance sharpness slightly
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            return image
            
        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            return image  # Return original if optimization fails


# Globale Instanz
ocr_processor = OCREngineManager()