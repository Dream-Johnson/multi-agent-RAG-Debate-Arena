"""
Turns text chunks into embedding vectors using Voyage AI.

Each chunk of article text becomes a list of floats (a vector) that
captures its semantic meaning. Pinecone indexes these vectors so we can
find the chunks most relevant to a query by comparing vector similarity,
instead of relying on exact keyword matches.

Voyage's models are trained with an *asymmetric* setup: documents being
indexed and search queries are embedded slightly differently for better
retrieval accuracy. That's why there are two functions below instead of
one — always pair embed_documents() (indexing) with embed_query()
(searching), never use one for both.
"""

import voyageai

from config import settings

# Voyage's embed() endpoint caps how many texts can go in a single request
# (confirmed via voyageai.VOYAGE_EMBED_BATCH_SIZE). A Wikipedia article can
# easily chunk into 100-300+ pieces, so we batch requests instead of
# sending everything at once.
BATCH_SIZE = voyageai.VOYAGE_EMBED_BATCH_SIZE

_client = voyageai.AsyncClient(api_key=settings.voyage_api_key)


async def embed_documents(chunks: list[str]) -> list[list[float]]:
    """Embed a list of article chunks for storage in Pinecone."""
    all_embeddings: list[list[float]] = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        result = await _client.embed(
            batch, model=settings.voyage_model, input_type="document"
        )
        all_embeddings.extend(result.embeddings)

    return all_embeddings


async def embed_query(query: str) -> list[float]:
    """Embed a single search query for retrieval against Pinecone."""
    result = await _client.embed(
        [query], model=settings.voyage_model, input_type="query"
    )
    return result.embeddings[0]
