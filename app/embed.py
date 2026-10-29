"""Deterministic 128-dimensional local embeddings for a self-contained demo."""
import hashlib
import math
import re

DIMENSIONS = 128

def embed(text: str) -> str:
    values = [0.0] * DIMENSIONS
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % DIMENSIONS
        values[index] += 1 if digest[4] & 1 else -1
    norm = math.sqrt(sum(x*x for x in values)) or 1.0
    return "[" + ",".join(f"{x/norm:.8f}" for x in values) + "]"
