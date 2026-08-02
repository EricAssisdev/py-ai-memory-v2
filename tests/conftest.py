import pytest
from pathlib import Path
from py_ai_memory.config import Config

@pytest.fixture
def memory_dir(tmp_path: Path) -> Config:
    config = Config(tmp_path)
    config.ensure_dirs()
    return config
