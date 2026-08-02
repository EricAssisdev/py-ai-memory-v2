import pytest
from pathlib import Path
from py_ai_memory.config import Config
from py_ai_memory.store import create_event, append_event, read_events
from py_ai_memory.index import init_db, rebuild_index
from py_ai_memory.trust import correct_event, reject_event
from py_ai_memory.handoff import create_handoff, list_handoffs, accept_handoff

def test_full_workflow(tmp_path: Path):
    config = Config(tmp_path)
    config.ensure_dirs()
    init_db(config)
    
    e1 = create_event('observe', 'fact 1')
    e2 = create_event('observe', 'fact 2')
    id1 = append_event(config, e1)
    id2 = append_event(config, e2)
    
    count = rebuild_index(config)
    assert count == 2
    
    c1 = correct_event(config, id1, 'fact 1 corrected')
    r2 = reject_event(config, id2, 'wrong')
    
    events = read_events(config)
    assert len(events) == 4
    
    h = create_handoff(config, summary='session end handoff')
    pending = list_handoffs(config)
    assert len(pending) == 1
    
    accept_handoff(config, h['id'])
    assert len(list_handoffs(config)) == 0
