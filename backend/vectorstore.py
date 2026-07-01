"""
Pinecone vector database wrapper — the "VectorDB" in RAG.

Handles three things:
  1. Ensuring the index exists (creating it on first run if it doesn't)
  2. Upserting chunk embeddings, namespaced by debate topic
  3. Querying for the chunks most relevant to a question

Pinecone splits its API in two: a synchronous *control plane* (create/
describe/delete indexes — infrequent, administrative) and an asynchronous
*data plane* (upsert/query vectors — frequent, performance-sensitive).
We use the sync client for control-plane calls and a separate async
client for data-plane calls, matching that split.
"""

import time

from pinecone import AsyncIndex, Pinecone, ServerlessSpec

from config import settings

_pc = Pinecone(api_key=settings.pinecone_api_key)

# Set once ensure_index_exists() has successfully confirmed the index is
# ready, so repeated calls (one per debate) short-circuit instead of
# re-checking Pinecone every time. Lazy rather than checked at server
# startup: a broken Pinecone connection only breaks starting a debate,
# not the whole app (static files, the login page, etc. don't need it).
_index_ready = False


def ensure_index_exists() -> None:
    """
    Create the Pinecone index if it doesn't already exist, and block until
    it's ready to accept requests.

    Serverless indexes aren't usable the instant create_index() returns —
    Pinecone provisions them in the background. Without this wait, the
    first upsert right after creation could fail.
    """
    global _index_ready
    if _index_ready:
        return

    if not _pc.has_index(settings.pinecone_index_name):
        _pc.create_index(
            name=settings.pinecone_index_name,
            dimension=settings.pinecone_dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
        )

    while not _pc.describe_index(settings.pinecone_index_name).status.ready:
        time.sleep(1)

    _index_ready = True


def _get_index_host() -> str:
    """Look up the data-plane host URL for our index (needed by AsyncIndex)."""
    return _pc.describe_index(settings.pinecone_index_name).host


async def upsert_chunks(topic: str, chunks: list[str], embeddings: list[list[float]]) -> None:
    """
    Store each chunk's embedding in Pinecone, scoped to `topic`.

    We use `topic` as the Pinecone *namespace* — its built-in way to
    logically partition vectors within one index. Each debate topic gets
    its own namespace, so retrieval for one topic never accidentally pulls
    in chunks left over from a previous, unrelated debate.
    """
    vectors = [
        {
            "id": f"{topic}-{i}",
            "values": embedding,
            # Store the raw chunk text as metadata so a query can return
            # readable text directly, without a second lookup elsewhere.
            "metadata": {"text": chunk},
        }
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]

    host = _get_index_host()
    async with AsyncIndex(host=host, api_key=settings.pinecone_api_key) as index:
        await index.upsert(vectors=vectors, namespace=topic)


async def query_chunks(topic: str, query_embedding: list[float], top_k: int = 5) -> list[str]:
    """Return the `top_k` chunk texts most relevant to `query_embedding`."""
    host = _get_index_host()
    async with AsyncIndex(host=host, api_key=settings.pinecone_api_key) as index:
        response = await index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=topic,
            include_metadata=True,
        )

    return [match.metadata["text"] for match in response.matches]
