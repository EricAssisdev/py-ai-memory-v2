import sys
import pytest
from unittest.mock import patch
from py_ai_memory.cli import main
from py_ai_memory.store import create_event, append_event

def test_cli_trust_commands(memory_dir, capsys):
    evt = create_event('observe', 'test')
    evt_id = append_event(memory_dir, evt)
    
    test_args = ["memory.py", "--project-dir", str(memory_dir.project_dir), "reject", evt_id, "--reason", "wrong"]
    with patch.object(sys, 'argv', test_args):
        try:
            main()
        except SystemExit:
            pass
            
    captured = capsys.readouterr()
    assert "Rejected" in captured.out
