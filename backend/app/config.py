from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # Login
    app_username: str = "admin"
    app_password: str = "admin123"
    app_session_token: str = "enterprise-rag-session"

    # Local LLM
    chat_model: str = "llama3.2"

    # Local embedding model
    embedding_model: str = "all-MiniLM-L6-v2"

    # Ollama server
    ollama_base_url: str = "http://localhost:11434"

    # RAG configuration
    top_k: int = 5
    min_similarity: float = 0.35

    # Chunking configuration
    chunk_size: int = 900
    chunk_overlap: int = 150

    # Data directory
    data_dir: str = "../data"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
