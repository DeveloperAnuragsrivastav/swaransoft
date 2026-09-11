"""
Central place to load all environment/config values.
Nothing else in the app should read os.environ directly - import from here.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# --- Pinecone ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "sawaransoft-chatbot")
EMBEDDING_DIMENSION = 384  # matches all-MiniLM-L6-v2

# --- Groq (server-side credentials only) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "openai/gpt-oss-120b")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")
MAX_IMAGE_BYTES = 4 * 1024 * 1024
ADMIN_UPLOAD_TOKEN = os.getenv("ADMIN_UPLOAD_TOKEN", "")

# --- Company location ---
COMPANY_LOCATION = {
    "name": os.getenv("COMPANY_NAME", "Swaran Soft"),
    "address": os.getenv("COMPANY_ADDRESS", ""),
    "latitude": float(os.environ["COMPANY_LATITUDE"]) if os.getenv("COMPANY_LATITUDE") else None,
    "longitude": float(os.environ["COMPANY_LONGITUDE"]) if os.getenv("COMPANY_LONGITUDE") else None,
}
COMPANY_LOCATION["maps_link"] = None
if COMPANY_LOCATION["latitude"] is not None and COMPANY_LOCATION["longitude"] is not None:
    if not (-90 <= COMPANY_LOCATION["latitude"] <= 90 and -180 <= COMPANY_LOCATION["longitude"] <= 180):
        raise ValueError("Company coordinates are outside the valid range.")
    COMPANY_LOCATION["maps_link"] = (
        f"https://www.google.com/maps?q={COMPANY_LOCATION['latitude']},{COMPANY_LOCATION['longitude']}"
    )

# --- Paths ---
COMPANY_DOCS_DIR = str(PROJECT_ROOT / "app/data/company_docs")
