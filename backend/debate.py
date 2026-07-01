"""
Orchestrates one full debate end-to-end:
  1. RAG ingestion: fetch the Wikipedia article for `topic`, chunk it,
     embed the chunks, and store them in Pinecone (so the agents have
     something to retrieve from)
  2. Run Agent 1 (FOR) and Agent 2 (AGAINST) concurrently — they're
     independent of each other, so there's no reason to wait for one
     before starting the other
  3. Run Agent 3 (Judge) on the two finished arguments
"""

import asyncio

from agents import generate_argument, judge_debate
from chunking import chunk_text
from embeddings import embed_documents
from models import DebateResult
from vectorstore import ensure_index_exists, upsert_chunks
from wikipedia_service import fetch_wikipedia_article


async def _ingest_topic(topic: str) -> None:
    """
    RAG ingestion pipeline: Wikipedia -> chunks -> embeddings -> Pinecone.

    This has to fully complete before any agent can retrieve anything —
    there's nothing stored for this topic until we put it there.
    """
    # ensure_index_exists() is synchronous and can block for several
    # seconds (it polls Pinecone with time.sleep while a new index
    # provisions). Running it directly here would freeze the event loop
    # for every other concurrent request — asyncio.to_thread() runs it on
    # a background thread instead, keeping the server responsive. Only
    # actually blocks on the first debate ever run (it's a no-op after).
    await asyncio.to_thread(ensure_index_exists)

    article_text = await fetch_wikipedia_article(topic)
    chunks = chunk_text(article_text)
    chunk_embeddings = await embed_documents(chunks)
    await upsert_chunks(topic, chunks, chunk_embeddings)


async def run_debate(topic: str) -> DebateResult:
    """Run one complete debate on `topic` and return the full result."""
    await _ingest_topic(topic)

    # FOR and AGAINST don't depend on each other's output, so we run them
    # concurrently with asyncio.gather instead of one after another — this
    # roughly halves the wall-clock time spent waiting on Claude.
    for_argument, against_argument = await asyncio.gather(
        generate_argument(topic, "FOR"),
        generate_argument(topic, "AGAINST"),
    )

    verdict = await judge_debate(topic, for_argument, against_argument)

    return DebateResult(
        topic=topic,
        for_argument=for_argument,
        against_argument=against_argument,
        verdict=verdict,
    )
