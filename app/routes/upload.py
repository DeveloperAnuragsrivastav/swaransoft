"""Authenticated administrative ingestion; never called by the public chat UI."""
import asyncio
import secrets
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Header, HTTPException

from app.core.config import COMPANY_DOCS_DIR, ADMIN_UPLOAD_TOKEN
from app.core.pdf_loader import extract_text_from_pdf, chunk_text
from app.core.rag import upsert_chunks

router = APIRouter()


def ingest_pdf(data: bytes, filename: str) -> dict:
    directory = Path(COMPANY_DOCS_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".pdf", delete=False) as output:
            output.write(data)
            temporary = Path(output.name)
        chunks = chunk_text(extract_text_from_pdf(str(temporary)))
        if not chunks:
            raise HTTPException(422, "This PDF has no extractable text. Use a text PDF or run OCR first.")
        document_id = secrets.token_hex(12)
        upsert_chunks([{"id": f"{document_id}-{i}", "text": text, "source": filename}
                       for i, text in enumerate(chunks)])
        temporary.rename(directory / f"{document_id}.pdf")
        temporary = None
        return {"status": "success", "filename": filename, "chunks_added": len(chunks)}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@router.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...), authorization: str = Header("")):
    if not ADMIN_UPLOAD_TOKEN:
        raise HTTPException(503, "PDF uploads are disabled. Configure the server's admin upload token first.")
    if not secrets.compare_digest(authorization, f"Bearer {ADMIN_UPLOAD_TOKEN}"):
        raise HTTPException(401, "An admin upload token is required.")
    filename = Path((file.filename or "document.pdf").replace("\\", "/")).name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Upload a PDF file.")
    data = await file.read(20 * 1024 * 1024 + 1)
    await file.close()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "PDFs must be smaller than 20 MB.")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(415, "The file is not a valid PDF.")
    try:
        return await asyncio.to_thread(ingest_pdf, data, filename)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "The PDF could not be indexed. Check the PDF and the server's Pinecone configuration.") from exc
