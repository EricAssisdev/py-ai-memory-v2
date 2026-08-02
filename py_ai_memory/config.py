import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

class Config:
    def __init__(self, project_dir: Path | None = None):
        self.project_dir = project_dir if project_dir is not None else Path.cwd()

    @property
    def memory_dir(self) -> Path:
        return self.project_dir / '.ai-memory'

    @property
    def logs_dir(self) -> Path:
        return self.memory_dir / 'logs'

    @property
    def events_path(self) -> Path:
        return self.logs_dir / 'events.jsonl'

    @property
    def audit_path(self) -> Path:
        return self.logs_dir / 'audit.jsonl'

    @property
    def wiki_dir(self) -> Path:
        return self.memory_dir / 'wiki'

    @property
    def index_dir(self) -> Path:
        return self.memory_dir / 'index'

    @property
    def db_path(self) -> Path:
        return self.index_dir / 'memory.db'

    @property
    def workstreams_dir(self) -> Path:
        return self.memory_dir / 'workstreams'

    @property
    def handoffs_dir(self) -> Path:
        return self.memory_dir / 'handoffs'

    @property
    def global_dir(self) -> Path:
        return Path.home() / '.ai-memory'

    @property
    def global_events_path(self) -> Path:
        return self.global_dir / 'logs' / 'events.jsonl'

    @property
    def global_db_path(self) -> Path:
        return self.global_dir / 'index' / 'memory.db'

    @property
    def git_branch(self) -> str:
        git_head = self.project_dir / '.git' / 'HEAD'
        if git_head.is_file():
            try:
                content = git_head.read_text('utf-8').strip()
                if content.startswith('ref: refs/heads/'):
                    return content.split('ref: refs/heads/')[1].replace('/', '-')
                return content[:8]
            except Exception:
                pass
        return 'main'

    def ensure_dirs(self) -> None:
        for d in [self.logs_dir, self.wiki_dir, self.index_dir, self.workstreams_dir, self.handoffs_dir, self.global_dir / 'logs', self.global_dir / 'index']:
            d.mkdir(parents=True, exist_ok=True)


def generate_event_id() -> str:
    dt = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    hex_str = secrets.token_hex(2)
    return f"evt_{dt}_{hex_str}"
