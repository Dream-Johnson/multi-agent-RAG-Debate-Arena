"""
Splits raw article text into overlapping chunks for embedding and retrieval.

Why chunk at all? If we embedded an entire article as a single vector, a
question about one narrow detail would get diluted by everything else in
the piece. Small, overlapping chunks let retrieval find just the passages
relevant to a specific question.

We use LangChain's RecursiveCharacterTextSplitter: it tries to split on
paragraph breaks first, then sentences, then words — only falling back to
a hard character cut if a piece still doesn't fit. This keeps chunks
semantically coherent instead of slicing mid-sentence.

Note: chunk_size/chunk_overlap here are measured in characters, not true
tokens (RecursiveCharacterTextSplitter's default length function is just
len() on the string). ~500 characters is roughly 100-150 English words —
a reasonable approximation of "500 tokens" without adding a tokenizer
dependency just for chunk sizing.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings

# Wikipedia's plain-text extracts include bare section headers
# ("History", "See also") as their own short lines. These produce
# near-empty chunks that add noise without useful content, so we
# drop anything too short to carry real meaning.
MIN_CHUNK_LENGTH = 20


def chunk_text(text: str) -> list[str]:
    """Split `text` into overlapping, semantically coherent chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        # Try splitting on these separators in order, only falling back to
        # the next (more aggressive) one if a chunk still exceeds chunk_size.
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)

    return [chunk.strip() for chunk in chunks if len(chunk.strip()) >= MIN_CHUNK_LENGTH]
