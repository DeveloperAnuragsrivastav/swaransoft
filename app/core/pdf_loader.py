"""
Extracts text from company PDFs and splits it into overlapping chunks
so each chunk is small enough to embed meaningfully.
"""
import os
import pdfplumber
from app.core.config import COMPANY_DOCS_DIR


def extract_text_from_pdf(filepath: str) -> str:
    text_parts = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Simple word-based chunking with overlap so context isn't lost
    at chunk boundaries.
    """
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def load_all_company_docs() -> list[dict]:
    """
    Reads every PDF in the company_docs folder, extracts + chunks text.
    Returns a list of dicts: {"id": ..., "text": ..., "source": filename}
    """
    all_chunks = []
    if not os.path.isdir(COMPANY_DOCS_DIR):
        return all_chunks

    for filename in os.listdir(COMPANY_DOCS_DIR):
        if not filename.lower().endswith(".pdf"):
            continue
        filepath = os.path.join(COMPANY_DOCS_DIR, filename)
        full_text = extract_text_from_pdf(filepath)
        chunks = chunk_text(full_text)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": f"{filename}-{i}",
                "text": chunk,
                "source": filename,
            })
    return all_chunks
