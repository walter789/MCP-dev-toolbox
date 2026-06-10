import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from config import WORKSPACE_ROOT
from indexer.chunker import CodeChunk, chunk_workspace

MODEL_NAME = "all-MiniLM-L6-v2"  # ~80 MB, fast, good general-purpose embeddings
INDEX_DIR = WORKSPACE_ROOT / ".mcp_index"
CHUNKS_FILE = INDEX_DIR / "chunks.json"
EMBEDDINGS_FILE = INDEX_DIR / "embeddings.npy"
META_FILE = INDEX_DIR / "meta.json"

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def build_index(base_path: str = ".") -> dict:
    """Chunk the workspace, embed every chunk, and persist the index to disk."""
    INDEX_DIR.mkdir(exist_ok=True)

    chunks = chunk_workspace(base_path)
    if not chunks:
        return {"status": "error", "message": "No indexable files found."}

    texts = [c.content for c in chunks]
    model = _get_model()
    t0 = time.time()
    embeddings = model.encode(texts, show_progress_bar=False, batch_size=64)
    elapsed = round(time.time() - t0, 2)

    np.save(str(EMBEDDINGS_FILE), embeddings.astype(np.float32))
    CHUNKS_FILE.write_text(
        json.dumps([asdict(c) for c in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    META_FILE.write_text(
        json.dumps({
            "model": MODEL_NAME,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "chunk_count": len(chunks),
            "embed_seconds": elapsed,
        }),
        encoding="utf-8",
    )
    return {
        "status": "ok",
        "chunks": len(chunks),
        "embed_seconds": elapsed,
        "model": MODEL_NAME,
    }


def load_index() -> tuple[list[CodeChunk], np.ndarray] | None:
    """Load persisted index from disk. Returns None if index doesn't exist."""
    if not CHUNKS_FILE.exists() or not EMBEDDINGS_FILE.exists():
        return None
    raw = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    chunks = [CodeChunk(**c) for c in raw]
    embeddings = np.load(str(EMBEDDINGS_FILE))
    return chunks, embeddings


def search(query: str, top_k: int = 5) -> list[dict]:
    """Embed the query and return top-K most similar chunks by cosine similarity."""
    index = load_index()
    if index is None:
        return []

    chunks, embeddings = index
    model = _get_model()
    query_emb = model.encode([query], show_progress_bar=False)[0].astype(np.float32)

    # Cosine similarity: normalise both sides, then dot product
    corpus_norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    corpus_norms = np.where(corpus_norms == 0, 1e-9, corpus_norms)
    normed = embeddings / corpus_norms
    query_norm = query_emb / (np.linalg.norm(query_emb) or 1e-9)
    scores = normed @ query_norm

    top_indices = np.argsort(scores)[::-1][:top_k]
    results = []
    for i in top_indices:
        c = chunks[i]
        results.append({
            "score": round(float(scores[i]), 4),
            "file": c.file_path,
            "start_line": c.start_line,
            "end_line": c.end_line,
            "type": c.chunk_type,
            "name": c.name,
            "snippet": c.content[:300] + ("..." if len(c.content) > 300 else ""),
        })
    return results
