"""Local embedding provider dispatch — sentence-transformers (primary) and Ollama (fallback).

Provider selected via config.toml: embeddings.provider = "sentence-transformers" | "ollama"
Model: all-MiniLM-L6-v2 (384 dimensions, runs fully locally, no cloud call).
"""
import struct
from typing import Optional

_model_cache = None  # Lazy-loaded SentenceTransformer instance

# ---------------------------------------------------------------------------
# Chunking parameters
# ---------------------------------------------------------------------------

CHUNK_SIZE = 1200       # characters per chunk
CHUNK_OVERLAP = 200     # overlap between consecutive chunks
CHUNK_THRESHOLD = 600   # notes shorter than this get a single chunk = full body


def split_text_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list:
    """Split text into overlapping character-window chunks.

    Returns a list of chunk strings. Texts shorter than or equal to chunk_size
    are returned as a single-element list containing the full text (no split).

    Args:
        text: Input text to split.
        chunk_size: Maximum number of characters per chunk.
        overlap: Number of characters shared between consecutive chunks.

    Returns:
        List[str] — at least one element.
    """
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += chunk_size - overlap
    return chunks


def embed_chunks(
    text: str,
    provider: Optional[str] = None,
    batch_size: int = 32,
) -> list:
    """Split text into chunks and embed each one.

    Returns a list of (chunk_text, embedding_blob) tuples — one per chunk.
    Short texts produce a single-entry list containing (text, blob).

    Args:
        text: Input text to chunk and embed.
        provider: Embedding provider — passed to embed_texts().
        batch_size: Encoding batch size — passed to embed_texts().

    Returns:
        List[Tuple[str, bytes]] — parallel to split_text_into_chunks() output.
    """
    chunks = split_text_into_chunks(text)
    if not chunks:
        return []
    blobs = embed_texts(chunks, provider=provider, batch_size=batch_size)
    return list(zip(chunks, blobs))


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
            # Embed one at a time. UTF-8 multibyte chars inflate token count (Finnish etc.),
            # so start at 1000 chars and halve on context-length errors.
            blobs = []
            for text in texts:
                limit = 1000
                while True:
                    try:
                        r = ollama.embed(model="nomic-embed-text", input=[text[:limit]])
                        blobs.append(_serialize(r.embeddings[0]))
                        break
                    except Exception as inner:
                        if "context length" in str(inner).lower() and limit > 50:
                            limit //= 2
                        else:
                            raise
            return blobs
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
