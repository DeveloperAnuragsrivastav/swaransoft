"""
Central place to load all environment/config values.
Nothing else in the app should read os.environ directly - import from here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Pinecone ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "sawaransoft-chatbot")
EMBEDDING_DIMENSION = 384  # matches all-MiniLM-L6-v2

# --- Ollama (local LLM) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "llama3.1")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava")

# --- Company location ---
COMPANY_LOCATION = {
    "name": os.getenv("COMPANY_NAME", "Sawaransoft"),
    "address": os.getenv("COMPANY_ADDRESS", "Address not set"),
    "latitude": float(os.getenv("COMPANY_LATITUDE", "0")),
    "longitude": float(os.getenv("COMPANY_LONGITUDE", "0")),
}
COMPANY_LOCATION["maps_link"] = (
    f"https://www.google.com/maps?q={COMPANY_LOCATION['latitude']},{COMPANY_LOCATION['longitude']}"
)

# --- Paths ---
COMPANY_DOCS_DIR = "app/data/company_docs"
