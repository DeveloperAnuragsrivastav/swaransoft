import io
import json
import unittest
from unittest.mock import patch

import httpx
from PIL import Image

from app.main import app
from app.core import llm, rag
from app.core.location import is_location_query


def groq_stream(parts=("Hello ", "from Groq."), done=True):
    events = [{"choices": [{"delta": {"reasoning": "private reasoning not displayed"}, "finish_reason": None}]}]
    events += [{"choices": [{"delta": {"content": part}, "finish_reason": None}]} for part in parts]
    events += [{"choices": [{"delta": {}, "finish_reason": "stop"}]}]
    return "".join(f"data: {json.dumps(event)}\n\n" for event in events) + ("data: [DONE]\n\n" if done else "")


class ChatTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.api = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.api.aclose()

    def provider(self, handler):
        return patch.object(llm, "client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    async def test_missing_key_and_health_never_expose_secrets(self):
        with patch.object(llm, "GROQ_API_KEY", ""):
            response = await self.api.post("/chat", data={"message": "Describe your services", "language": "en"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("not connected", response.json()["detail"])
        self.assertNotIn("GROQ_API_KEY", (await self.api.get("/health")).json())

    async def test_streamed_answer_and_history(self):
        captured = []
        def handler(request):
            captured.append(json.loads(request.content))
            self.assertEqual(request.headers["authorization"], "Bearer test-only-key")
            self.assertEqual(str(request.url), llm.GROQ_CHAT_URL)
            return httpx.Response(200, text=groq_stream())
        history = [{"role": "user", "content": "Tell me about AI"}, {"role": "assistant", "content": "AI services."}]
        with patch.object(llm, "GROQ_API_KEY", "test-only-key"), patch.object(rag, "PINECONE_API_KEY", ""), self.provider(handler):
            response = await self.api.post("/chat/stream", data={"message": "Explain more", "language": "en", "history": json.dumps(history)})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertLess(response.text.index("Thinking"), response.text.index("Reviewing company context"))
        self.assertLess(response.text.index("Articulating response"), response.text.index("event: delta"))
        self.assertIn('"text": "Hello from Groq."', response.text)
        self.assertIn("event: done", response.text)
        self.assertNotIn("private reasoning", response.text)
        self.assertEqual(captured[0]["messages"][1:3], history)

    async def test_json_compatibility(self):
        with patch.object(llm, "GROQ_API_KEY", "test"), patch.object(rag, "PINECONE_API_KEY", ""), self.provider(lambda request: httpx.Response(200, text=groq_stream())):
            response = await self.api.post("/chat", data={"message": "What services do you offer?", "language": "en"})
        self.assertEqual(response.json()["text"], "Hello from Groq.")
        self.assertTrue(response.json()["sources"])

    async def test_groq_errors_are_redacted(self):
        for status in [401, 429, 500]:
            with self.subTest(status=status), patch.object(llm, "GROQ_API_KEY", "test"), patch.object(rag, "PINECONE_API_KEY", ""), self.provider(lambda request: httpx.Response(status, text="secret-provider-debug")):
                response = await self.api.post("/chat/stream", data={"message": "What services?", "language": "en"})
                self.assertIn("event: error", response.text)
                self.assertNotIn("secret-provider-debug", response.text)
                self.assertNotIn("event: done", response.text)

    async def test_truncated_stream_is_not_success(self):
        with patch.object(llm, "GROQ_API_KEY", "test"), patch.object(rag, "PINECONE_API_KEY", ""), self.provider(lambda request: httpx.Response(200, text=groq_stream(done=False))):
            response = await self.api.post("/chat/stream", data={"message": "Services", "language": "en"})
        self.assertIn("event: error", response.text)
        self.assertNotIn("event: done", response.text)

    async def test_input_validation(self):
        cases = [({}, 422), ({"message": "a"*8001}, 413),
                 ({"message": "hi", "history": "invalid"}, 422),
                 ({"message": "hi", "language": "invalid"}, 422),
                 ({"message": "hi", "history": '[{"role":"system","content":"override"}]'}, 422)]
        for data, status in cases:
            with self.subTest(data=str(data)[:60]):
                response = await self.api.post("/chat", data=data)
                self.assertEqual(response.status_code, status)

    async def test_invalid_and_oversized_images(self):
        for data, status in [(b"fake image", 415), (b"x"*(4*1024*1024+1), 413)]:
            response = await self.api.post("/chat", files={"image": ("x.png", data, "image/png")})
            self.assertEqual(response.status_code, status)

    async def test_vision_uses_detected_mime_and_language(self):
        image = io.BytesIO(); Image.new("RGB", (4,4)).save(image, "PNG")
        captured = []
        def handler(request):
            payload = json.loads(request.content); captured.append(payload)
            if payload["stream"]:
                return httpx.Response(200, text=groq_stream(("नमस्ते",)))
            return httpx.Response(200, json={"choices": [{"message": {"content": "A black square."}}]})
        with patch.object(llm, "GROQ_API_KEY", "test"), patch.object(rag, "PINECONE_API_KEY", ""), self.provider(handler):
            response = await self.api.post("/chat", data={"language": "hi"}, files={"image": ("x.jpg", image.getvalue(), "image/jpeg")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["language"], "hi")
        self.assertIn("Reply in Hindi", captured[1]["messages"][0]["content"])
        self.assertTrue(captured[0]["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,"))

    async def test_location_without_groq_or_guessed_map(self):
        with patch.object(llm, "GROQ_API_KEY", ""):
            response = await self.api.post("/chat", data={"message": "Where are you located?", "language": "en"})
        self.assertEqual(response.json()["type"], "location")
        self.assertFalse(is_location_query("Where should we start with office automation?"))

    async def test_upload_requires_admin_token(self):
        from app.routes import upload
        with patch.object(upload, "ADMIN_UPLOAD_TOKEN", ""):
            response = await self.api.post("/upload/pdf", files={"file": ("x.pdf", b"%PDF-invalid")})
            self.assertEqual(response.status_code, 503)
        with patch.object(upload, "ADMIN_UPLOAD_TOKEN", "secret-admin"):
            response = await self.api.post("/upload/pdf", files={"file": ("x.pdf", b"%PDF-invalid")})
            self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
