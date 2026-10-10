"""Offline OCR adapter. Tesseract is optional and must be installed on-premises."""
import io
import os
import subprocess
from PIL import Image, ImageOps, UnidentifiedImageError

class OCRUnavailable(RuntimeError):
    pass

def recognize(data: bytes) -> str:
    if os.environ.get("MCIAS_LOCAL_OCR", "disabled") != "tesseract":
        raise OCRUnavailable("local OCR disabled")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 20_000_000:
                raise OCRUnavailable("image pixel limit exceeded")
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            clean = buffer.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise OCRUnavailable("invalid image") from exc
    language = os.environ.get("MCIAS_OCR_LANG", "eng")
    if not language or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+_" for c in language):
        raise OCRUnavailable("invalid OCR language")
    try:
        process = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", language],
            input=clean, capture_output=True, timeout=20, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        raise OCRUnavailable("OCR engine unavailable or timed out") from exc
    if process.returncode or len(process.stdout) > 2_000_000:
        raise OCRUnavailable("OCR engine failed")
    return process.stdout.decode("utf-8", errors="strict").strip()
