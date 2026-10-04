from pathlib import Path
import fitz
from docx import Document

ALLOWED = {".pdf", ".docx"}

def extract_text(path):
    suffix = Path(path).suffix.lower()
    if suffix not in ALLOWED:
        raise ValueError("Only PDF and DOCX files are supported.")

    if suffix == ".pdf":
        doc = fitz.open(path)
        return "\n".join(page.get_text() for page in doc)

    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)
