import io
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader


def extract_text(content: bytes, mime_type: str, filename: str) -> str:
    ext = Path(filename).suffix.lower()

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
