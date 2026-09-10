import os
import shutil

from fastapi import APIRouter, UploadFile, File

from app.core.config import COMPANY_DOCS_DIR
from app.core.pdf_loader import extract_text_from_pdf, chunk_text
from app.core.rag import upsert_chunks

router = APIRouter()


@router.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Admin-side endpoint: add a new company PDF to the knowledge base.
    Saves the file, extracts + chunks text, embeds, and upserts to Pinecone.

    Note: this is separate from the main /chat endpoint on purpose - this
    one is for YOU (or an admin) to grow the knowledge base, not for end
    users chatting with the bot.
    """
    os.makedirs(COMPANY_DOCS_DIR, exist_ok=True)
    filepath = os.path.join(COMPANY_DOCS_DIR, file.filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    full_text = extract_text_from_pdf(filepath)
    chunks = chunk_text(full_text)
    chunk_dicts = [
        {"id": f"{file.filename}-{i}", "text": chunk, "source": file.filename}
        for i, chunk in enumerate(chunks)
    ]
    upsert_chunks(chunk_dicts)

    return {"status": "success", "filename": file.filename, "chunks_added": len(chunk_dicts)}
