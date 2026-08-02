import pytest
from py_ai_memory.audit import log_mutation, read_audit_log, format_audit_log

def test_audit_log(memory_dir):
    log_mutation(memory_dir, 'correct', 'evt_123', 'user', 'typo')
    entries = read_audit_log(memory_dir)
    
    assert len(entries) == 1
    assert entries[0]['action'] == 'correct'
    assert entries[0]['target_id'] == 'evt_123'
    assert 'content' not in entries[0]
    
    out = format_audit_log(entries)
    assert 'evt_123' in out
    assert 'correct' in out
