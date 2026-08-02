import pytest
from pathlib import Path
from py_ai_memory.trust import get_file_hash, make_file_ref, check_file_refs

def test_file_refs(tmp_path: Path):
    p = tmp_path / "test.txt"
    p.write_text("hello")
    
    ref = make_file_ref("test.txt", tmp_path)
    assert ref['path'] == "test.txt"
    assert len(ref['git_hash']) == 64
    
    ev = {"file_refs": [ref]}
    stale = check_file_refs(ev, tmp_path)
    assert len(stale) == 0
    
    p.write_text("changed")
    stale = check_file_refs(ev, tmp_path)
    assert len(stale) == 1
    assert stale[0]['path'] == "test.txt"
