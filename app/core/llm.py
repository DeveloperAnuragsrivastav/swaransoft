"""
Thin wrapper around Ollama's local API so the rest of the app
doesn't need to know HTTP details. Requires Ollama running locally
(https://ollama.com) with the models pulled:
    ollama pull llama3.1
    ollama pull llava
"""
import base64
import requests

from app.core.config import OLLAMA_BASE_URL, OLLAMA_TEXT_MODEL, OLLAMA_VISION_MODEL


def ask_llm(system_prompt: str, user_message: str) -> str:
    """Text-only question, grounded by system_prompt (RAG context)."""
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_TEXT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def ask_llm_about_image(image_bytes: bytes, question: str = "What is in this image?") -> str:
    """
    Sends an image to the local vision model (llava) along with a question.
    Used for the 'user uploads a photo/document image' feature.
    """
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": question,
                    "images": [encoded_image],
                }
            ],
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]
