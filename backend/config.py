"""
Centralized application settings.

Instead of calling os.getenv() scattered across every file, every other
module imports the single `settings` object defined at the bottom of this
file. pydantic-settings reads from environment variables (and a .env file
locally), validates their types, and raises a clear error at startup if
something required is missing.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Tell pydantic-settings where to look for a local .env file.
    # In production (e.g. a deployed server) real env vars are set directly
    # and no .env file is needed — this is just for local development.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- Secrets (no defaults — app fails to start if these are missing) ---
    anthropic_api_key: str
    voyage_api_key: str
    pinecone_api_key: str
    app_password: str

    # --- Model choices (have sensible defaults, but overridable via .env) ---
    claude_model: str = "claude-haiku-4-5"
    voyage_model: str = "voyage-3.5"

    # --- Pinecone index configuration ---
    pinecone_index_name: str = "debate-rag"
    # Pinecone serverless indexes need a cloud provider + region pair.
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    # Embedding dimension must match whatever voyage_model produces.
    # voyage-3.5 outputs 1024-dimensional vectors.
    pinecone_dimension: int = 1024

    # --- Chunking parameters (used by chunking.py) ---
    chunk_size: int = 500
    chunk_overlap: int = 50


# Created once at import time. Every other module does:
#   from config import settings
settings = Settings()
