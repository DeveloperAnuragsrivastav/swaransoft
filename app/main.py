from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import PROJECT_ROOT, GROQ_API_KEY, PINECONE_API_KEY

from app.routes import chat, upload, location

app = FastAPI(title="Swaran Soft Assistant")


@app.get("/health")
async def health():
    return {"status": "ok", "provider": "groq",
            "configured": bool(GROQ_API_KEY and not GROQ_API_KEY.startswith("your_")),
            "knowledge": "documents" if PINECONE_API_KEY and not PINECONE_API_KEY.startswith("your_") else "public_profile"}

app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(location.router)

# Serve the simple chat UI at the root
app.mount("/", StaticFiles(directory=PROJECT_ROOT / "static", html=True), name="static")
