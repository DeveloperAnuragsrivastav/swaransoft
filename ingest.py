"""
Run this ONCE (and again any time you add/update PDFs) to load
company documents into Pinecone:

    python ingest.py

Make sure your PDFs are placed in app/data/company_docs/ first.
"""
from app.core.pdf_loader import load_all_company_docs
from app.core.rag import upsert_chunks

if __name__ == "__main__":
    print("Loading and chunking PDFs from app/data/company_docs/ ...")
    chunks = load_all_company_docs()

    if not chunks:
        print("No PDFs found. Add files to app/data/company_docs/ and re-run.")
    else:
        print(f"Found {len(chunks)} chunks. Embedding and upserting to Pinecone...")
        upsert_chunks(chunks)
        print("Done! Your chatbot is ready to answer from these documents.")
