from pathlib import Path
import io
import fitz
from PIL import Image
from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def validate_upload(filename: str, content: bytes):
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF, PNG, JPG and JPEG files are supported")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f"File exceeds {settings.max_upload_mb} MB limit")
    if not content:
        raise ValueError("Uploaded file is empty")
    signatures = {
        ".pdf": (b"%PDF",),
        ".png": (b"\x89PNG",),
        ".jpg": (b"\xff\xd8\xff",),
        ".jpeg": (b"\xff\xd8\xff",),
    }
    if not any(content.startswith(sig) for sig in signatures[ext]):
        raise ValueError("File content does not match its declared extension")


def _ocr_image(image: Image.Image) -> str:
    try:
        import pytesseract
        return pytesseract.image_to_string(image)
    except Exception:
        # OCR is a fallback. A readable digital PDF still works even when the
        # Tesseract desktop executable is not installed.
        return ""


def extract_text_bytes(filename: str, content: bytes) -> tuple[str, bool]:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        doc = fitz.open(stream=content, filetype="pdf")
        direct = "\n".join(page.get_text("text") for page in doc).strip()
        if len(direct) >= 40:
            doc.close()
            return direct, False

        ocr_parts = []
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_parts.append(_ocr_image(image))
        doc.close()
        return "\n".join(ocr_parts).strip(), True

    image = Image.open(io.BytesIO(content))
    return _ocr_image(image).strip(), True
