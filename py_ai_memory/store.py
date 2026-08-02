import json
import re
from datetime import datetime, timezone
from pathlib import Path
from py_ai_memory.config import Config, generate_event_id

def create_event(
    type: str,
    content: str | dict,
    *,
    actor: str = 'user',
    scope: str = 'project',
    branch: str = 'main',
    tags: list[str] | None = None,
    source: str = 'observed',
    supersedes: str | None = None,
    confidence: float = 1.0,
    file_refs: list[dict] | None = None,
    reason: str | None = None
) -> dict:
    evt = {
        "id": generate_event_id(),
        "type": type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "scope": scope,
        "branch": branch,
        "content": content,
        "tags": tags or [],
        "source": source,
        "supersedes": supersedes,
        "confidence": float(confidence),
        "file_refs": file_refs or []
    }
    if type == 'reject':
        evt['reason'] = reason or ''
    return evt

import os
import time

def append_event(config: Config, event: dict) -> str:
    config.ensure_dirs()
    lock_path = config.events_path.with_suffix('.lock')
    
    timeout = 15.0
    start_time = time.time()
    while True:
        try:
            os.mkdir(lock_path)
            break
        except FileExistsError:
            if time.time() - start_time > timeout:
                raise TimeoutError("Could not acquire lock for events.jsonl")
            time.sleep(0.05)
            
    try:
        with config.events_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(event) + '\n')
            f.flush()
            os.fsync(f.fileno())
    finally:
        try:
            os.rmdir(lock_path)
        except OSError:
            pass
            
    return event['id']

def read_events(config: Config, scope: str | None = None) -> list[dict]:
    if not config.events_path.is_file():
        return []
    
    events = []
    with config.events_path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            evt = json.loads(line)
            if scope and evt.get('scope') != scope:
                continue
            events.append(evt)
    return events

def get_event(config: Config, event_id: str) -> dict | None:
    for evt in read_events(config):
        if evt['id'] == event_id:
            return evt
    return None

def write_wiki_article(config: Config, filename: str, metadata: dict, content: str) -> Path:
    config.ensure_dirs()
    path = config.wiki_dir / filename
    
    fm_lines = ["---"]
    for k, v in metadata.items():
        fm_lines.append(f"{k}: {json.dumps(v)}")
    fm_lines.append("---")
    
    full_content = "\n".join(fm_lines) + "\n\n" + content
    path.write_text(full_content, encoding='utf-8')
    return path

def read_wiki_article(config: Config, filename: str) -> tuple[dict, str]:
    path = config.wiki_dir / filename
    if not path.is_file():
        raise FileNotFoundError(f"Wiki article not found: {filename}")
        
    text = path.read_text(encoding='utf-8')
    match = re.match(r'^---\n(.*?)\n---\n(.*)', text, re.DOTALL)
    
    metadata = {}
    content = text
    
    if match:
        fm_text = match.group(1)
        content = match.group(2).lstrip()
        for line in fm_text.splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                try:
                    metadata[k.strip()] = json.loads(v.strip())
                except json.JSONDecodeError:
                    metadata[k.strip()] = v.strip()
                    
    return metadata, content

def list_wiki_articles(config: Config) -> list[Path]:
    if not config.wiki_dir.is_dir():
        return []
    return list(config.wiki_dir.glob('*.md'))
