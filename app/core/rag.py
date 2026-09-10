"""
RAG (Retrieval Augmented Generation) core:
- Embeds text using a local sentence-transformers model (free, no API key)
- Stores/retrieves those embeddings in Pinecone
- Builds a grounded prompt for the LLM so it only answers from company docs
"""
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

from app.core.config import PINECONE_API_KEY, PINECONE_INDEX_NAME, EMBEDDING_DIMENSION
from app.core.llm import ask_llm

# Loaded once at import time - reused across requests
_embedder = SentenceTransformer("all-MiniLM-L6-v2")

_pc = Pinecone(api_key=PINECONE_API_KEY) if PINECONE_API_KEY else None


def ensure_index_exists():
    """Creates the Pinecone index if it doesn't already exist. Call once at startup/ingest time."""
    if _pc is None:
        raise RuntimeError("PINECONE_API_KEY is not set. Check your .env file.")

    existing = [idx["name"] for idx in _pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        _pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )


def get_index():
    ensure_index_exists()
    return _pc.Index(PINECONE_INDEX_NAME)


def embed_text(text: str) -> list[float]:
    return _embedder.encode(text).tolist()


def upsert_chunks(chunks: list[dict]):
    """
    chunks: list of {"id": str, "text": str, "source": str}
    Embeds each chunk and upserts into Pinecone with the original text
    stored in metadata (so we can retrieve it later without a second DB).
    """
    index = get_index()
    vectors = []
    for chunk in chunks:
        vectors.append({
            "id": chunk["id"],
            "values": embed_text(chunk["text"]),
            "metadata": {"text": chunk["text"], "source": chunk["source"]},
        })

    # Pinecone recommends batching upserts (e.g. 100 at a time)
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i:i + batch_size])


def retrieve_relevant_chunks(query: str, top_k: int = 4) -> list[str]:
    index = get_index()
    query_vector = embed_text(query)
    results = index.query(vector=query_vector, top_k=top_k, include_metadata=True)
    return [match["metadata"]["text"] for match in results["matches"]]


def get_rag_answer(query: str) -> str:
    """
    Full pipeline: retrieve relevant company doc chunks, then ask the LLM
    to answer ONLY using that context. This is what keeps the bot from
    answering random general-knowledge questions.
    """
    context_chunks = retrieve_relevant_chunks(query)

    if not context_chunks:
        return (
            "I don't have information about that in Sawaransoft's documents. "
            "Please contact the team directly for this query."
        )

    context = "\n\n".join(context_chunks)

    system_prompt = (
        "You are Sawaransoft's official company assistant. "
        "Answer the user's question using ONLY the context below, which comes "
        "from Sawaransoft's own documents. If the answer isn't in the context, "
        "say you don't have that information and suggest contacting the team. "
        "Do not answer questions unrelated to Sawaransoft.\n\n"
        f"Context:\n{context}"
    )

    return ask_llm(system_prompt=system_prompt, user_message=query)
