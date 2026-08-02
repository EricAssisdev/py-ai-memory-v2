import sys
import pytest
from unittest.mock import patch
from py_ai_memory.cli import main

def test_cli_status(memory_dir, capsys):
    test_args = ["memory.py", "--project-dir", str(memory_dir.project_dir), "status"]
    with patch.object(sys, 'argv', test_args):
        try:
            main()
        except SystemExit:
            pass
    captured = capsys.readouterr()
    assert "Active branch" in captured.out
