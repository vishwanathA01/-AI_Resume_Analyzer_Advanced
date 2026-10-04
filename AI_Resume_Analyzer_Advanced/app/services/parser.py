from pathlib import Path
import zipfile
import fitz
from docx import Document
from docx.opc.exceptions import PackageNotFoundError

ALLOWED = {".pdf", ".docx"}

def extract_text(path):
    suffix = Path(path).suffix.lower()
    if suffix not in ALLOWED:
        raise ValueError("Only PDF and DOCX files are supported.")

    try:
        if suffix == ".pdf":
            with fitz.open(path) as doc:
                return "\n".join(page.get_text() for page in doc)

        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    except (
        fitz.FileDataError,
        fitz.EmptyFileError,
        PackageNotFoundError,
        zipfile.BadZipFile,
        ValueError,
    ) as error:
        raise ValueError("The selected file is not a readable PDF or DOCX resume.") from error
