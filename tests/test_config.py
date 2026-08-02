import os
from pathlib import Path
from py_ai_memory.config import Config, generate_event_id

def test_config_paths(tmp_path):
    config = Config(tmp_path)
    assert config.project_dir == tmp_path
    assert config.memory_dir == tmp_path / '.ai-memory'
    assert config.logs_dir == config.memory_dir / 'logs'
    assert config.events_path == config.logs_dir / 'events.jsonl'
    assert config.audit_path == config.logs_dir / 'audit.jsonl'
    assert config.wiki_dir == config.memory_dir / 'wiki'
    assert config.index_dir == config.memory_dir / 'index'
    assert config.db_path == config.index_dir / 'memory.db'
    assert config.workstreams_dir == config.memory_dir / 'workstreams'
    assert config.handoffs_dir == config.memory_dir / 'handoffs'
    assert config.global_dir == Path.home() / '.ai-memory'
    assert config.global_events_path == config.global_dir / 'logs' / 'events.jsonl'
    assert config.global_db_path == config.global_dir / 'index' / 'memory.db'

def test_ensure_dirs(tmp_path):
    config = Config(tmp_path)
    config.ensure_dirs()
    assert config.logs_dir.exists()
    assert config.wiki_dir.exists()
    assert config.index_dir.exists()

def test_git_branch_fallback(tmp_path):
    config = Config(tmp_path)
    assert config.git_branch == "main"

def test_generate_event_id():
    evt_id = generate_event_id()
    assert evt_id.startswith("evt_")
    assert len(evt_id.split("_")) == 4
