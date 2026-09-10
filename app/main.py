from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.routes import chat, upload, location

app = FastAPI(title="Sawaransoft Company Chatbot")

# Allow the simple frontend (or any origin during development) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(location.router)

# Serve the simple chat UI at the root
app.mount("/", StaticFiles(directory="static", html=True), name="static")
