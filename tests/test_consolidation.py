import sys
from unittest.mock import patch
from py_ai_memory.config import Config
from py_ai_memory.store import append_event, create_event, list_wiki_articles, read_wiki_article
from py_ai_memory.consolidation import consolidate_events
from py_ai_memory.cli import main

def test_consolidation_groups_by_tag(tmp_path):
    config = Config(tmp_path)
    append_event(config, create_event('observe', "Event 1", tags=["architecture"]))
    append_event(config, create_event('observe', "Event 2", tags=["architecture"]))
    
    count = consolidate_events(config)
    assert count == 1 # 1 wiki article created
    
    wikis = list_wiki_articles(config)
    assert len(wikis) == 1
    assert "architecture" in wikis[0].name
    
    meta, content = read_wiki_article(config, wikis[0].name)
    assert meta["title"] == "Consolidated: architecture"
    assert "architecture" in meta["tags"]
    assert "consolidated" in meta["tags"]
    assert len(meta["connections"]) == 2
    assert "Event 1" in content
    assert "Event 2" in content

def test_consolidation_requires_minimum_two_events(tmp_path):
    config = Config(tmp_path)
    append_event(config, create_event('observe', "Single event", tags=["isolated"]))
    
    count = consolidate_events(config)
    assert count == 0
    
    wikis = list_wiki_articles(config)
    assert len(wikis) == 0

def test_consolidation_idempotent(tmp_path):
    config = Config(tmp_path)
    append_event(config, create_event('observe', "Event 1", tags=["db"]))
    append_event(config, create_event('observe', "Event 2", tags=["db"]))
    
    count1 = consolidate_events(config)
    assert count1 == 1
    
    # Second run should skip already superseded events
    count2 = consolidate_events(config)
    assert count2 == 0
    
    wikis = list_wiki_articles(config)
    assert len(wikis) == 1

def test_cli_consolidate(tmp_path, capsys):
    config = Config(tmp_path)
    append_event(config, create_event('observe', "CLI Event 1", tags=["cli_tag"]))
    append_event(config, create_event('observe', "CLI Event 2", tags=["cli_tag"]))
    
    test_args = ["memory", "--project-dir", str(tmp_path), "consolidate"]
    with patch.object(sys, 'argv', test_args):
        main()
        
    captured = capsys.readouterr()
    assert "Consolidated 1 topics into Wiki articles." in captured.out
