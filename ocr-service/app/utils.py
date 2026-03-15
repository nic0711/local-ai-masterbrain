"""
Utility-Funktionen für OCR Service
"""

import os
import asyncio
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Unterstützte Dateiformate
SUPPORTED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.webp'}
SUPPORTED_MIME_TYPES = {
    'application/pdf',
    'image/png',
    'image/jpeg',
    'image/tiff',
    'image/bmp',
    'image/webp'
}


def validate_file_type(filename: str) -> bool:
    """
    Validiere Dateityp basierend auf Dateiendung
    
    Args:
        filename: Name der Datei
        
    Returns:
        bool: True wenn unterstützt, False sonst
    """
    if not filename:
        return False
    
    file_ext = Path(filename).suffix.lower()
    return file_ext in SUPPORTED_EXTENSIONS



async def cleanup_temp_files(file_paths: List[str], delay: int = 0) -> None:
    """
    Lösche temporäre Dateien asynchron
    
    Args:
        file_paths: Liste der zu löschenden Dateipfade
        delay: Verzögerung in Sekunden vor dem Löschen
    """
    if delay > 0:
        await asyncio.sleep(delay)
    
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Deleted temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not delete temp file {file_path}: {e}")


def ensure_directory(directory_path: str) -> bool:
    """
    Stelle sicher, dass ein Verzeichnis existiert
    
    Args:
        directory_path: Pfad zum Verzeichnis
        
    Returns:
        bool: True wenn erfolgreich erstellt/existiert
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Could not create directory {directory_path}: {e}")
        return False


def get_file_size(file_path: str) -> Optional[int]:
    """
    Hole Dateigröße in Bytes
    
    Args:
        file_path: Pfad zur Datei
        
    Returns:
        int: Dateigröße in Bytes oder None bei Fehler
    """
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.warning(f"Could not get file size for {file_path}: {e}")
        return None


def format_confidence_score(confidence: float) -> str:
    """
    Formatiere Konfidenz-Score für Ausgabe
    
    Args:
        confidence: Konfidenz-Wert zwischen 0 und 1
        
    Returns:
        str: Formatierter Konfidenz-String
    """
    percentage = confidence * 100
    if percentage >= 90:
        return f"🟢 {percentage:.1f}% (Excellent)"
    elif percentage >= 75:
        return f"🟡 {percentage:.1f}% (Good)"
    elif percentage >= 50:
        return f"🟠 {percentage:.1f}% (Fair)"
    else:
        return f"🔴 {percentage:.1f}% (Poor)"


def extract_text_statistics(text: str) -> dict:
    """
    Extrahiere Statistiken aus erkanntem Text
    
    Args:
        text: Erkannter Text
        
    Returns:
        dict: Statistiken über den Text
    """
    if not text:
        return {
            "character_count": 0,
            "word_count": 0,
            "line_count": 0,
            "paragraph_count": 0,
            "has_numbers": False,
            "has_special_chars": False
        }
    
    lines = text.split('\n')
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    words = text.split()
    
    return {
        "character_count": len(text),
        "word_count": len(words),
        "line_count": len(lines),
        "paragraph_count": len(paragraphs),
        "has_numbers": any(char.isdigit() for char in text),
        "has_special_chars": any(not char.isalnum() and not char.isspace() for char in text),
        "average_word_length": sum(len(word) for word in words) / len(words) if words else 0
    }


def convert_layout_to_markdown(layout_data: List[dict]) -> str:
    """
    Konvertiere Layout-Daten zu Markdown
    
    Args:
        layout_data: Layout-Daten von OCR
        
    Returns:
        str: Markdown-formatierter Text
    """
    if not layout_data:
        return ""
    
    markdown_parts = []
    
    for page_data in layout_data:
        page_num = page_data.get("page", 1)
        boxes = page_data.get("boxes", [])
        
        if len(layout_data) > 1:
            markdown_parts.append(f"## Seite {page_num}\n")
        
        for box in boxes:
            text = box.get("text", "").strip()
            confidence = box.get("confidence", 0)
            
            if text and confidence > 0.5:
                # Einfache Heuristik für Überschriften (große Konfidenz + kurzer Text)
                if confidence > 0.9 and len(text.split()) <= 5:
                    markdown_parts.append(f"### {text}\n")
                else:
                    markdown_parts.append(f"{text}\n")
        
        markdown_parts.append("\n")
    
    return "".join(markdown_parts)


def sanitize_filename(filename: str) -> str:
    """
    Bereinige Dateinamen für sichere Verwendung
    
    Args:
        filename: Ursprünglicher Dateiname
        
    Returns:
        str: Bereinigter Dateiname
    """
    # Entferne gefährliche Zeichen
    dangerous_chars = '<>:"/\\|?*'
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Begrenze Länge
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    
    return f"{name}{ext}"


async def monitor_processing_time(func, *args, **kwargs):
    """
    Überwache Verarbeitungszeit einer Funktion
    
    Args:
        func: Auszuführende Funktion
        *args, **kwargs: Funktionsargumente
        
    Returns:
        tuple: (Ergebnis, Verarbeitungszeit)
    """
    import time
    start_time = time.time()
    
    try:
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        
        processing_time = time.time() - start_time
        return result, processing_time
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Function {func.__name__} failed after {processing_time:.2f}s: {e}")
        raise