import pytest
from py_ai_memory.store import create_event, append_event, write_wiki_article
from py_ai_memory.index import init_db, rebuild_index, search_fts, get_db

def test_index_and_search(memory_dir):
    evt1 = create_event('observe', 'Find this keyword in search')
    evt2 = create_event('observe', 'Another unrelated event')
    append_event(memory_dir, evt1)
    append_event(memory_dir, evt2)
    
    write_wiki_article(memory_dir, 'doc.md', {'title': 'Doc'}, 'keyword is here too')
    
    count = rebuild_index(memory_dir)
    assert count == 3
    
    results = search_fts(memory_dir, 'keyword')
    assert len(results) == 2
