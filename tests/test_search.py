import pytest
from py_ai_memory.search import rrf_score, temporal_decay, trust_boost

def test_rrf_score():
    assert rrf_score({'fts': 1, 'sem': 2}, k=60) == (1/61 + 1/62)

def test_temporal_decay():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    assert temporal_decay(now) == 1.0

def test_trust_boost():
    assert trust_boost('verified') == 1.0
    assert trust_boost('candidate') == 0.7
    assert trust_boost('superseded') is None
    assert trust_boost('rejected') is None
