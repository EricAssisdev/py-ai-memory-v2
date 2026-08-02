import math
import pytest
from pathlib import Path
from py_ai_memory.config import Config
from py_ai_memory.embeddings import embed_hrr, cosine_similarity, store_embedding, load_embedding

def test_hrr_deterministic_and_similarity(tmp_path: Path):
    vec1 = embed_hrr("hello world")
    vec2 = embed_hrr("hello world")
    assert vec1 == vec2
    assert len(vec1) == 256
    
    vec3 = embed_hrr("different text entirely")
    sim_same = cosine_similarity(vec1, vec2)
    sim_diff = cosine_similarity(vec1, vec3)
    
    assert math.isclose(sim_same, 1.0, rel_tol=1e-5)
    assert sim_diff < sim_same

def test_store_and_load_embedding(tmp_path: Path):
    config = Config(tmp_path)
    config.ensure_dirs()
    
    vec = [0.1, -0.2, 0.3] + [0.0] * 253
    model = "hrr"
    event_id = "evt_123"
    
    store_embedding(config, event_id, vec, model)
    
    loaded = load_embedding(config, event_id)
    assert loaded is not None
    loaded_vec, loaded_model = loaded
    
    assert loaded_model == model
    assert len(loaded_vec) == 256
    for v1, v2 in zip(vec, loaded_vec):
        assert math.isclose(v1, v2, rel_tol=1e-5)
