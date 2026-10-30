"""Local semantic embeddings using FastEmbed's BGE small English model."""
import os
from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384
WINDOW_WORDS = 250
WINDOW_OVERLAP = 40


@lru_cache(maxsize=1)
def get_model() -> TextEmbedding:
    """Load the ONNX model once per process; Docker pre-downloads its files."""
    return TextEmbedding(
        model_name=MODEL_NAME,
        cache_dir=os.getenv("EMBEDDING_CACHE_DIR", "/srv/model-cache"),
    )


def _windows(text: str):
    words = text.split()
    if not words:
        raise ValueError("Cannot embed empty text")
    for start in range(0, len(words), WINDOW_WORDS - WINDOW_OVERLAP):
        yield " ".join(words[start:start + WINDOW_WORDS])
        if start + WINDOW_WORDS >= len(words):
            break


def embed(text: str) -> str:
    """Encode all of a chunk, averaging windows for older oversized chunks."""
    vectors = np.asarray(list(get_model().embed(list(_windows(text)))), dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[1] != DIMENSIONS:
        raise ValueError(f"Expected {DIMENSIONS}-dimensional embeddings")
    mean = vectors.mean(axis=0)
    norm = float(np.linalg.norm(mean))
    if norm == 0:
        raise ValueError("Embedding model returned a zero vector")
    normalized = mean / norm
    return "[" + ",".join(f"{float(value):.8f}" for value in normalized) + "]"
