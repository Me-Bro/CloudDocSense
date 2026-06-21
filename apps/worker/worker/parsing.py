"""Document parsing -> list of (page, text) segments.

M1 scope: plain text, PDF, DOCX. Image / scanned-doc parsing via a vision
model is M2 (ING-2) and raises UnsupportedFileType here for now.
"""
from io import BytesIO

# (page_number_or_None, text)
Segment = tuple[int | None, str]


class UnsupportedFileType(Exception):
    pass


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def parse(filename: str, mime_type: str | None, data: bytes) -> list[Segment]:
    ext = _ext(filename)
    mime = (mime_type or "").lower()

    if ext in ("txt", "md", "text") or mime.startswith("text/"):
        return [(None, data.decode("utf-8", errors="replace"))]

    if ext == "pdf" or mime == "application/pdf":
        return _parse_pdf(data)

    if ext in ("docx",) or mime == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return _parse_docx(data)

    if ext in ("png", "jpg", "jpeg", "gif", "webp", "tiff") or mime.startswith("image/"):
        raise UnsupportedFileType(
            f"Image/scanned parsing is M2 (vision model): {filename}"
        )

    raise UnsupportedFileType(f"Unsupported file type: {filename} ({mime_type})")


def _parse_pdf(data: bytes) -> list[Segment]:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    segments: list[Segment] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            segments.append((i, text))
    return segments


def _parse_docx(data: bytes) -> list[Segment]:
    from docx import Document as DocxDocument

    doc = DocxDocument(BytesIO(data))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return [(None, "\n".join(paragraphs))]
