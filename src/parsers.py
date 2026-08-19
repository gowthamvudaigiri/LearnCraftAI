from __future__ import annotations
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup
import fitz
from src.config import SETTINGS, SUPPORTED_EXTENSIONS

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

def validate_uploads(files: list[tuple[str, bytes]]) -> None:
    if len(files) > SETTINGS.max_files:
        raise ValueError(f"Upload at most {SETTINGS.max_files} files.")
    if sum(len(data) for _, data in files) > SETTINGS.max_total_mb * 1024 * 1024:
        raise ValueError(f"Uploads must total at most {SETTINGS.max_total_mb} MB.")
    if sum(Path(name).suffix.lower() in {'.png','.jpg','.jpeg','.webp'} for name, _ in files) > SETTINGS.max_images:
        raise ValueError(f"Upload at most {SETTINGS.max_images} images.")
    for name, data in files:
        ext = Path(name).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")
        if ext == ".pdf" and not data.startswith(b"%PDF"):
            raise ValueError(f"{name} is not a valid PDF.")
        if ext in {".png"} and not data.startswith(b"\x89PNG"):
            raise ValueError(f"{name} is not a valid PNG.")

def extract_file(name: str, data: bytes) -> dict:
    ext = Path(name).suffix.lower(); text = ""; pages = 1; analysis_data = None
    if ext == ".pdf":
        doc = fitz.open(stream=data, filetype="pdf")
        if doc.needs_pass: raise ValueError(f"{name} is encrypted.")
        pages = min(len(doc), SETTINGS.max_pdf_pages)
        text = "\n".join(doc[i].get_text("text") for i in range(pages))
        if len(doc) > SETTINGS.max_pdf_pages:
            limited = fitz.open()
            limited.insert_pdf(doc,from_page=0,to_page=SETTINGS.max_pdf_pages-1)
            analysis_data = limited.tobytes(garbage=4,deflate=True)
            limited.close()
        else:
            analysis_data = data
        doc.close()
    elif ext in {".html", ".htm"}:
        text = BeautifulSoup(data, "html.parser").get_text(" ", strip=True)
    elif ext in {".txt", ".md"}:
        text = data.decode("utf-8", errors="replace")
    elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
        analysis_data = data

    uses_vision = analysis_data is not None
    status = "vision ready" if uses_vision and not text.strip() else "text + vision ready" if uses_vision else "read"
    return {
        "source_id": hashlib.sha256(data).hexdigest()[:16],
        "filename": name,
        "text": text[:50000],
        "pages": pages,
        "status": status,
        "mime_type": MIME_TYPES.get(ext),
        "analysis_data": analysis_data,
    }
