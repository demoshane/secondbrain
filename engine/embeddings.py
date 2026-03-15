"""Local embedding provider dispatch — sentence-transformers (primary) and Ollama (fallback).

Provider selected via config.toml: embeddings.provider = "sentence-transformers" | "ollama"
Model: all-MiniLM-L6-v2 (384 dimensions, runs fully locally, no cloud call).
"""
import struct
from typing import Optional

_model_cache = None  # Lazy-loaded SentenceTransformer instance


def _get_model():
    """Lazy-load the sentence-transformers model (avoids 90MB download on import)."""
    global _model_cache
    if _model_cache is None:
        from sentence_transformers import SentenceTransformer
        _model_cache = SentenceTransformer("all-MiniLM-L6-v2")
    return _model_cache


def _serialize(vector) -> bytes:
    """Convert float list or numpy array to sqlite-vec float32 BLOB (little-endian)."""
    try:
        import numpy as np
        if hasattr(vector, "astype"):
            return vector.astype(np.float32).tobytes()
    except ImportError:
        pass
    return struct.pack("%sf" % len(vector), *vector)


def embed_texts(texts: list, provider: Optional[str] = None,
                batch_size: int = 32) -> list:
    """Embed a list of texts and return serialized float32 BLOBs.

    Args:
        texts: List of strings to embed.
        provider: "sentence-transformers" (default) or "ollama".
                  If None, loads from config.
        batch_size: Number of texts per encoding batch (sentence-transformers only).

    Returns:
        List of bytes objects — one float32 BLOB per input text, compatible with sqlite-vec.

    Raises:
        ValueError: Unknown provider.
        RuntimeError: Ollama not running (provider="ollama").
    """
    if not texts:
        return []

    if provider is None:
        from pathlib import Path
        from engine.config_loader import load_config
        cfg = load_config(Path(".meta/config.toml"))
        provider = cfg.get("embeddings", {}).get("provider", "ollama")

    if provider == "sentence-transformers":
        model = _get_model()
        vectors = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        return [_serialize(v) for v in vectors]

    elif provider == "ollama":
        try:
            import ollama
            resp = ollama.embed(model="nomic-embed-text", input=texts)
            return [_serialize(v) for v in resp["embeddings"]]
        except Exception as e:
            err_type = type(e).__name__
            if "connect" in str(e).lower() or "connection" in str(e).lower():
                raise RuntimeError(
                    "[ERROR] Ollama provider selected but Ollama is not running. "
                    "Start Ollama or set embeddings.provider = \"sentence-transformers\" "
                    "in config.toml."
                ) from e
            raise RuntimeError(
                f"[ERROR] Ollama embed failed ({err_type}): {e}"
            ) from e

    else:
        raise ValueError(
            f"Unknown embedding provider: {provider!r}. "
            "Valid values: 'sentence-transformers', 'ollama'"
        )
