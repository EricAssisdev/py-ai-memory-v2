import pytest
from py_ai_memory.config import Config
from py_ai_memory.index import init_db, rebuild_index
from py_ai_memory.store import write_wiki_article

def test_graph_extraction(tmp_path):
    config = Config(tmp_path)
    write_wiki_article(config, "node_a.md", {"title": "Node A", "connections": ["node_b", "node_c"]}, "Content A")
    write_wiki_article(config, "node_b.md", {"title": "Node B", "connections": ["node_c"]}, "Content B")
    
    rebuild_index(config)
    
    conn = init_db(config)
    cur = conn.execute("SELECT source, target FROM memory_graph ORDER BY source, target")
    results = [dict(r) for r in cur]
    
    assert len(results) == 3
    assert results[0]['source'] == 'node_a.md'
    assert results[0]['target'] == 'node_b'
