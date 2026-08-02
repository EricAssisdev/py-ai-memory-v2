import hashlib
import struct
import math
import sqlite3
from typing import Tuple, List, Optional
from py_ai_memory.config import Config

_backend_cache = None
_model_cache = None

def detect_backend() -> str:
    try:
        import fastembed
        return "fastembed"
    except ImportError:
        try:
            import sentence_transformers
            return "sentence-transformers"
        except ImportError:
            return "hrr"

def _get_model():
    """Returns cached (backend, model) tuple. Model is loaded once per process."""
    global _backend_cache, _model_cache
    if _backend_cache is not None:
        return _backend_cache, _model_cache
    
    _backend_cache = detect_backend()
    if _backend_cache == "fastembed":
        from fastembed import TextEmbedding
        _model_cache = TextEmbedding()
    elif _backend_cache == "sentence-transformers":
        from sentence_transformers import SentenceTransformer
        _model_cache = SentenceTransformer('all-MiniLM-L6-v2')
    else:
        _model_cache = None
    return _backend_cache, _model_cache

def embed_text(text: str) -> Tuple[List[float], str]:
    backend, model = _get_model()
    if backend == "fastembed":
        embeddings = list(model.embed([text]))
        return embeddings[0].tolist(), "fastembed"
    elif backend == "sentence-transformers":
        embedding = model.encode(text)
        return embedding.tolist(), "sentence-transformers"
    else:
        return embed_hrr(text), "hrr"

def embed_texts(texts: List[str]) -> Tuple[List[List[float]], str]:
    backend, model = _get_model()
    if backend == "fastembed":
        embeddings = list(model.embed(texts))
        return [e.tolist() for e in embeddings], "fastembed"
    elif backend == "sentence-transformers":
        embeddings = model.encode(texts)
        return [e.tolist() for e in embeddings], "sentence-transformers"
    else:
        return [embed_hrr(text) for text in texts], "hrr"

def embed_hrr(text: str) -> List[float]:
    if not text:
        return [0.0] * 256
    text = text.lower()
    vector = [0.0] * 256
    ngrams = [text[i:i+3] for i in range(max(1, len(text) - 2))]
    for ngram in ngrams:
        h = hashlib.sha256(ngram.encode('utf-8')).digest()
        seed = struct.unpack('<Q', h[:8])[0]
        idx = seed % 256
        val = ((seed >> 8) % 3) - 1.0
        vector[idx] += val
    
    norm = math.sqrt(sum(x*x for x in vector))
    if norm > 0:
        return [x / norm for x in vector]
    return [0.0] * 256

def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot_product = sum(x*y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x*x for x in a))
    norm_b = math.sqrt(sum(y*y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def store_embedding(config: Config, event_id: str, vector: List[float], model: str) -> None:
    db_path = config.db_path
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS embeddings (
            event_id TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            vector BLOB NOT NULL
        )
    ''')
    vector_blob = struct.pack(f'{len(vector)}f', *vector)
    cursor.execute('''
        INSERT OR REPLACE INTO embeddings (event_id, model, vector)
        VALUES (?, ?, ?)
    ''', (event_id, model, vector_blob))
    conn.commit()
    conn.close()

def load_embedding(config: Config, event_id: str) -> Optional[Tuple[List[float], str]]:
    db_path = config.db_path
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT vector, model FROM embeddings WHERE event_id = ?', (event_id,))
        row = cursor.fetchone()
        if row:
            vector_blob, model = row
            count = len(vector_blob) // struct.calcsize('f')
            vector = list(struct.unpack(f'{count}f', vector_blob))
            return vector, model
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()
    return None

def search_semantic(config: Config, query: str, limit: int = 20) -> List[Tuple[str, float]]:
    query_vector, q_model = embed_text(query)
    db_path = config.db_path
    if not db_path.exists():
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT event_id, vector FROM embeddings')
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()

    results = []
    for event_id, vector_blob in rows:
        count = len(vector_blob) // struct.calcsize('f')
        vector = list(struct.unpack(f'{count}f', vector_blob))
        score = cosine_similarity(query_vector, vector)
        results.append((event_id, score))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]
