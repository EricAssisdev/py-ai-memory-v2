import pytest
import json
from py_ai_memory.store import append_event, read_events, get_event, create_event, write_wiki_article, read_wiki_article, list_wiki_articles

def test_create_and_append_event(memory_dir):
    event = create_event('observe', 'Test content', tags=['test'])
    assert event['type'] == 'observe'
    assert event['content'] == 'Test content'
    assert event['tags'] == ['test']
    assert event['confidence'] == 1.0

    evt_id = append_event(memory_dir, event)
    assert evt_id == event['id']
    
    events = read_events(memory_dir)
    assert len(events) == 1
    assert events[0]['id'] == evt_id

def test_get_event(memory_dir):
    event = create_event('observe', 'Content')
    evt_id = append_event(memory_dir, event)
    
    fetched = get_event(memory_dir, evt_id)
    assert fetched is not None
    assert fetched['id'] == evt_id
    
    assert get_event(memory_dir, 'nonexistent') is None

def test_wiki_operations(memory_dir):
    metadata = {'title': 'Test Wiki', 'tags': ['wiki']}
    content = '# Hello World'
    
    path = write_wiki_article(memory_dir, 'test.md', metadata, content)
    assert path.exists()
    
    articles = list_wiki_articles(memory_dir)
    assert len(articles) == 1
    assert articles[0].name == 'test.md'
    
    read_meta, read_content = read_wiki_article(memory_dir, 'test.md')
    assert read_meta['title'] == 'Test Wiki'
    assert read_content.strip() == '# Hello World'
