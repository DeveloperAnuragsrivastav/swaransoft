"""Groq text streaming and vision. Credentials never leave the backend."""
import base64
import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import GROQ_API_KEY, GROQ_TEXT_MODEL, GROQ_VISION_MODEL

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class ModelError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def headers() -> dict:
    if not GROQ_API_KEY or GROQ_API_KEY.startswith("your_"):
        raise ModelError("The assistant is not connected yet. Set GROQ_API_KEY in the server's .env file and restart the app.", 503)
    return {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}


def check_response(response: httpx.Response) -> None:
    if response.is_success:
        return
    if response.status_code in (401, 403):
        raise ModelError("Groq rejected the credentials or model access. Check the server's API key and model permissions.", 503)
    if response.status_code == 429:
        raise ModelError("The assistant has reached its request limit. Please wait a moment and try again.", 429)
    if response.status_code in (400, 404, 422):
        raise ModelError("Groq could not process this request. Check the configured model and try a shorter message or smaller image.")
    raise ModelError("The AI service is temporarily unavailable. Please try again shortly.")


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(45, connect=10))


async def stream_answer(system_prompt: str, message: str, history: list[dict]) -> AsyncIterator[str]:
    payload = {
        "model": GROQ_TEXT_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": message}],
        "stream": True, "temperature": 0.3, "max_completion_tokens": 4096,
    }
    try:
        async with client() as session:
            async with session.stream("POST", GROQ_CHAT_URL, headers=headers(), json=payload) as response:
                check_response(response)
                received = finished = False
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        if not received or not finished:
                            raise ModelError("The assistant returned an incomplete reply. Please try again.")
                        return
                    if not data:
                        continue
                    event = json.loads(data)
                    if event.get("error"):
                        raise ModelError("The AI service interrupted the reply. Please try again.")
                    choices = event.get("choices", [])
                    if not choices:
                        continue
                    choice = choices[0]
                    reason = choice.get("finish_reason")
                    if reason == "length":
                        raise ModelError("The reply reached its length limit. Please ask a more focused question.")
                    if reason is not None:
                        finished = reason == "stop"
                    # Ignore private reasoning fields; only answer content reaches the UI.
                    content = choice.get("delta", {}).get("content")
                    if isinstance(content, str) and content:
                        received = True
                        yield content
                raise ModelError("The connection ended before the reply was complete. Please try again.")
    except httpx.TimeoutException as exc:
        raise ModelError("The assistant took too long to respond. Please try again.", 504) from exc
    except httpx.HTTPError as exc:
        raise ModelError("The AI service could not be reached. Check the connection and try again.") from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise ModelError("The AI service returned an unreadable response. Please try again.") from exc


async def ask_llm_about_image(image_bytes: bytes, mime_type: str, question: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": GROQ_VISION_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
        ]}],
        "max_completion_tokens": 2048, "stream": False,
    }
    try:
        async with client() as session:
            response = await session.post(GROQ_CHAT_URL, headers=headers(), json=payload)
            check_response(response)
            text = response.json()["choices"][0]["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Empty image response")
            return text
    except httpx.TimeoutException as exc:
        raise ModelError("Image review timed out. Please try a smaller image.", 504) from exc
    except httpx.HTTPError as exc:
        raise ModelError("The image service could not be reached. Please try again.") from exc
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ModelError("The image service returned an unreadable response. Please try again.") from exc
