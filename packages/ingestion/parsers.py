import io
import os
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader

from .image_parser import IMAGE_EXTENSIONS, IMAGE_MIMES, extract_image
from .msproject_parser import PROJECT_EXTENSIONS, extract_msproject, is_msproject_file
from .xlsx_parser import extract_xlsx

XLSX_EXTENSIONS = {".xlsx", ".xlsm"}
XLSX_MIMES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel.sheet.macroEnabled.12",
}


def _get_ingest_settings() -> dict:
    """Load optional settings when running inside API/worker."""
    try:
        from config import get_settings

        s = get_settings()
        return {
            "ocr_language": getattr(s, "ocr_language", "rus+eng"),
            "vision_fallback": getattr(s, "ingest_vision_fallback", True),
            "vision_model": getattr(s, "ingest_vision_model", "gpt-4o-mini"),
            "openai_api_key": s.openai_api_key,
            "openai_base_url": s.openai_base_url,
            "mpxj_jar_path": getattr(s, "mpxj_jar_path", os.environ.get("MPXJ_JAR_PATH", "/app/lib/mpxj.jar")),
        }
    except ImportError:
        return {
            "ocr_language": os.environ.get("OCR_LANGUAGE", "rus+eng"),
            "vision_fallback": os.environ.get("INGEST_VISION_FALLBACK", "true").lower() == "true",
            "vision_model": os.environ.get("INGEST_VISION_MODEL", "gpt-4o-mini"),
            "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "openai_base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "mpxj_jar_path": os.environ.get("MPXJ_JAR_PATH", "/app/lib/mpxj.jar"),
        }


def extract_text(content: bytes, mime_type: str, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    settings = _get_ingest_settings()

    if ext in XLSX_EXTENSIONS or mime_type in XLSX_MIMES:
        return extract_xlsx(content, filename)

    if ext in IMAGE_EXTENSIONS or mime_type in IMAGE_MIMES:
        return extract_image(
            content,
            mime_type,
            filename,
            ocr_language=settings["ocr_language"],
            vision_fallback=settings["vision_fallback"],
            vision_model=settings["vision_model"],
            openai_api_key=settings["openai_api_key"],
            openai_base_url=settings["openai_base_url"],
        )

    if is_msproject_file(content, ext, mime_type):
        return extract_msproject(content, filename, mpxj_jar_path=settings["mpxj_jar_path"])

    if mime_type == "text/plain" or ext in (".txt", ".md", ".csv"):
        return content.decode("utf-8", errors="replace")

    if mime_type == "application/pdf" or ext == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[Page {i + 1}]\n{text}")
        return "\n\n".join(pages)

    if mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ) or ext == ".docx":
        doc = DocxDocument(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    if mime_type in ("text/html", "application/xhtml+xml") or ext in (".html", ".htm"):
        soup = BeautifulSoup(content, "lxml")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    try:
        return content.decode("utf-8", errors="replace")
    except Exception:
        return ""
