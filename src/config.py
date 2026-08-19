from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    max_files: int = 10
    max_total_mb: int = 50
    max_pdf_pages: int = 25
    max_images: int = 10
    max_repairs: int = 2
    parser_version: str = "1.0"

SETTINGS = Settings()
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".html", ".htm", ".txt", ".md"}
