import pytest
from pathlib import Path
from py_ai_memory.config import Config
from py_ai_memory.handoff import create_handoff, accept_handoff, list_handoffs, get_handoff

def test_handoff_lifecycle(tmp_path: Path):
    config = Config(tmp_path)
    config.ensure_dirs()
    
    h1 = create_handoff(config, summary="Test handoff")
    assert h1['id'].startswith('evt_')
    
    pending = list_handoffs(config)
    assert len(pending) == 1
    assert pending[0]['id'] == h1['id']
    
    get_h = get_handoff(config, h1['id'])
    assert get_h['id'] == h1['id']
    
    acc = accept_handoff(config, h1['id'])
    assert acc['type'] == 'correct'
    
    pending_after = list_handoffs(config)
    assert len(pending_after) == 0
