# Sawaransoft Company Chatbot

A chatbot that answers questions **only** about Sawaransoft, using your own
company PDFs as its knowledge base. Also supports:
- 📍 Company location queries (returns exact address + embedded map)
- 🖼️ Image uploads (ask questions about a photo/scanned document)
- 📄 PDF-based knowledge (RAG — Retrieval Augmented Generation)

100% free stack — no paid API keys required except Pinecone's free tier.

---

## 1. Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed locally
- A free [Pinecone](https://www.pinecone.io) account + API key

### Pull the required local models
```bash
ollama pull llama3.1   # text answers
ollama pull llava       # image understanding
```
Keep Ollama running in the background (it runs as a local server automatically after install).

---

## 2. Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # on Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# then edit .env and add your PINECONE_API_KEY + company address
```

---

## 3. Add your company documents

Place your company PDFs into:
```
app/data/company_docs/
```

Then run the ingestion script (loads + embeds + stores them in Pinecone):
```bash
python ingest.py
```

Re-run this any time you add or update PDFs.

---

## 4. Run the app

```bash
uvicorn app.main:app --reload
```

Open your browser at: **http://localhost:8000**

---

## 5. How it works

1. **Text question** → checked for location keywords first → otherwise sent through
   the RAG pipeline: your question is embedded, relevant PDF chunks are retrieved
   from Pinecone, and the local LLM answers using ONLY that context.
2. **Location question** (e.g. "where are you located?") → answered instantly from
   a fixed config (`app/core/config.py`), never guessed by the LLM.
3. **Image upload** → sent to the local vision model (`llava`) for description/Q&A.

---

## 6. Project structure

```
app/
├── main.py              # FastAPI app entrypoint
├── routes/
│   ├── chat.py          # /chat endpoint
│   ├── upload.py        # /upload/pdf and /upload/image endpoints
│   └── location.py       # /location endpoint
├── core/
│   ├── config.py        # loads .env values
│   ├── rag.py            # embeddings + Pinecone + grounded answering
│   ├── pdf_loader.py     # PDF text extraction + chunking
│   ├── llm.py            # Ollama wrapper (text + vision)
│   └── location.py       # location keyword detection
├── data/company_docs/    # put your PDFs here
static/index.html          # simple chat UI
ingest.py                  # one-time script to load PDFs into Pinecone
```

---

## 7. Multi-language support

The chatbot auto-detects the user's language (English, Hindi, Tamil, Telugu,
Marathi, Gujarati, Bengali, Punjabi) and replies in the same language. Users
can also force a specific language using the dropdown in the UI.

**How it works:** the user's message is translated to English internally
(so RAG/location logic only deals with one language), processed as normal,
then the final answer is translated back. This uses `deep-translator`
(free, no API key) which **requires internet access** — unlike the rest of
the stack (Ollama, Pinecone embeddings) which can run offline once set up.

If the user only sends an image (no typed text), the language defaults to
English since there's nothing to detect from.

---

## 8. Voice chat (input + output)

Voice is handled entirely in the browser using the **Web Speech API** — no
new Python packages, no server changes needed.

- **🎤 mic button** — click it, speak your question, and it auto-fills the
  text box and sends it for you. Uses `SpeechRecognition`.
- **"Read replies aloud" checkbox** — when checked, the bot's text answer
  is also spoken out loud using `speechSynthesis`.
- Both respect the **language dropdown** — e.g. select Hindi, and the mic
  listens for Hindi speech and replies are spoken in Hindi.

**Browser support:** works in Chrome and Edge. Voice input needs internet
(like the translation feature) since recognition runs through the browser's
speech service. If a browser doesn't support it, the mic button shows an
alert instead of failing silently.

---

## 9. Things to customize before your demo

- [ ] Fill in real `COMPANY_ADDRESS`, `COMPANY_LATITUDE`, `COMPANY_LONGITUDE` in `.env`
- [ ] Add your real company PDFs to `app/data/company_docs/`
- [ ] Run `python ingest.py`
- [ ] Test a few sample questions (see below)

### Sample test questions
- "Where is Sawaransoft located?" → should return address + map
- "What services does Sawaransoft offer?" → should answer from your PDF
- "What's the capital of France?" → should say it doesn't have that info (this proves it's scoped correctly)
- Upload an image → ask "what is in this image?"
