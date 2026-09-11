# Swaran Soft Assistant

A FastAPI chatbot with the approved Swaran Soft interface: enlarged original logo,
DM Sans and Syne typography, responsive conversation sidebar, formatted Markdown,
image attachments, voice input and read-aloud, and multilingual replies.

Groq supplies both text and image understanding. The app does not require Ollama.
Progress appears beneath the assistant name and is replaced by the streamed answer.
Progress labels describe application stages, not the model's private reasoning.

## Run locally

Use Python 3.11 or 3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `GROQ_API_KEY` in `.env`, then start the app:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Restart the server after changing `.env`.
The key stays on the server; `.env` and uploaded company PDFs are ignored by Git.

If you only need the public company profile (no Pinecone/PDF ingestion), use the
lighter `pip install -r requirements-web.txt` instead of the full requirements.

## Configuration

| Setting | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Required for AI replies and image review. Create a key in your Groq account. |
| `GROQ_TEXT_MODEL` | Defaults to `openai/gpt-oss-120b`. Change to a text model available to your account. |
| `GROQ_VISION_MODEL` | Defaults to `qwen/qwen3.6-27b`. Requires a Groq model with image support; this default is a preview model. |
| `PINECONE_API_KEY` | Optional company PDF knowledge base. Without it, answers use the bundled public company profile. |
| `PINECONE_INDEX_NAME` | Existing 384-dimensional MiniLM index name. |
| `ADMIN_UPLOAD_TOKEN` | A separate secret for the admin PDF upload endpoint. Blank disables uploads. Not needed for ordinary chat. |
| `COMPANY_ADDRESS` | Verified office address shown in location replies. |
| `COMPANY_LATITUDE`, `COMPANY_LONGITUDE` | Optional verified map coordinates. Leave both blank to omit the map. |

Never enter Groq keys in frontend code or chat messages. The connection label
means a key is configured, not that Groq has authenticated it. Invalid keys,
rate limits, network failures, and missing configuration appear as recoverable errors.

## Company documents

Set Pinecone configuration and install the full requirements. Place text-based
company PDFs in `app/data/company_docs/`, then run:

```bash
python ingest.py
```

The embedding model loads lazily when documents are queried or ingested. Its
first use downloads `all-MiniLM-L6-v2`. Pinecone and Groq require network access.
Scanned PDFs require OCR before ingestion.

`POST /upload/pdf` also ingests a PDF when an `Authorization: Bearer <admin token>`
header is provided. The token is never exposed in the public chat interface.
PDFs are limited to 20 MB. The direct ingestion script remains available without
the HTTP upload token to the person running the server.

The fallback public profile is a small, dated summary of https://swaransoft.com/,
not a live website search. Refresh `PUBLIC_PROFILE` as company details change.
Context sources identify documents retrieved for an answer, not sentence-level citations.

## Chat behavior

- `POST /chat/stream`: multipart fields `message`, optional `image`, `language`, and
  a JSON `history` list. Emits SSE `status`, `delta`, `done`, or `error` events.
- `POST /chat`: the same fields with a JSON response, preserving the original API.
- `GET /location`: configured office location. No invented coordinates.
- `GET /health`: application state and whether Groq is configured, without secrets.
- Supports English, Hindi, Tamil, Telugu, Marathi, Gujarati, Bengali, and Punjabi.
- Image uploads accept PNG/JPEG/WebP up to 4 MB and 20 megapixels. Images go to
  Groq for analysis. They are not added to the company knowledge base.
- Conversation text is kept in browser session storage. Only bounded recent
  history is sent with each request. Images are held in memory, not session storage;
  after reloading, reattach an image to retry its request.
- Stop cancels the browser request and upstream async streaming. Partial or failed
  assistant replies are excluded from later context.
- Voice input uses the browser's speech service and may require microphone
  permission. Read-aloud uses browser speech synthesis.

## Verification

```bash
python -m unittest discover -s tests -v
node --check static/chat.js
```

Tests use a mocked Groq transport. A real Groq key and a configured Pinecone index
are needed for live provider checks. No simulated responses are shipped in the UI.

The UI serves from the same origin as the API. Before exposing this internal app
publicly, deploy behind HTTPS, access controls, and request/rate limits appropriate
to your users. The document upload token protects only the ingestion endpoint.

## Reference

Branding and layout colours: [Swaran Soft](https://swaransoft.com/).
Provider contract: [Groq API compatibility](https://console.groq.com/docs/openai),
[supported models](https://console.groq.com/docs/models), and
[vision](https://console.groq.com/docs/vision).
Vendored Lucide, Marked, and DOMPurify retain their upstream license notices.
