import json
import hashlib
from pathlib import Path
from py_ai_memory.config import Config
from py_ai_memory.store import create_event, append_event, read_events, get_event
from py_ai_memory.audit import log_mutation

def compute_trust_state(event: dict, all_events: list[dict]) -> str:
    if event.get('type') == 'reject':
        return 'rejected'
        
    event_id = event.get('id', event.get('event_id'))
    superseded_by = [e for e in all_events if e.get('supersedes') == event_id]
    
    if any(e.get('type') == 'reject' for e in superseded_by):
        return 'rejected'
        
    if superseded_by:
        return 'superseded'
        
    if event.get('source') == 'inferred':
        return 'candidate'
        
    return 'verified'

def get_rejected_ids(config: Config) -> set[str]:
    events = read_events(config)
    rejected = set()
    for e in events:
        if e.get('type') == 'reject':
            rejected.add(e['id'])
            if e.get('supersedes'):
                rejected.add(e['supersedes'])
    return rejected

def correct_event(config: Config, target_id: str, new_content: str, *, actor: str = 'user') -> dict:
    target = get_event(config, target_id)
    if not target:
        raise ValueError("Target event not found")
        
    rejected = get_rejected_ids(config)
    if target_id in rejected:
        raise ValueError("Cannot correct an already rejected event")
        
    evt = create_event('correct', new_content, actor=actor, supersedes=target_id)
    append_event(config, evt)
    
    log_mutation(config, 'correct', target_id, actor, '')
    return evt

def reject_event(config: Config, target_id: str, reason: str, *, actor: str = 'user') -> dict:
    target = get_event(config, target_id)
    if not target:
        raise ValueError("Target event not found")
        
    rejected = get_rejected_ids(config)
    if target_id in rejected:
        raise ValueError("Event is already rejected")
        
    evt = create_event('reject', '', actor=actor, supersedes=target_id, reason=reason)
    append_event(config, evt)
    
    log_mutation(config, 'reject', target_id, actor, reason)
    return evt

def verify_event(config: Config, target_id: str, *, actor: str = 'user') -> dict:
    events = read_events(config)
    target = next((e for e in events if e['id'] == target_id), None)
    
    if not target:
        raise ValueError("Target event not found")
        
    state = compute_trust_state(target, events)
    if state != 'candidate':
        raise ValueError(f"Can only verify candidate events, this is {state}")
        
    evt = create_event('observe', f"Verified event {target_id}", actor=actor, source='observed', supersedes=target_id)
    append_event(config, evt)
    
    log_mutation(config, 'verify', target_id, actor, '')
    return evt

def get_supersession_chain(config: Config, event_id: str) -> list[dict]:
    events = {e['id']: e for e in read_events(config)}
    if event_id not in events:
        return []
        
    chain = [events[event_id]]
    
    # Walk backward
    curr = events[event_id]
    while curr.get('supersedes') and curr['supersedes'] in events:
        curr = events[curr['supersedes']]
        chain.insert(0, curr)
        
    # Walk forward
    curr_id = event_id
    while True:
        next_evt = next((e for e in events.values() if e.get('supersedes') == curr_id), None)
        if not next_evt:
            break
        chain.append(next_evt)
        curr_id = next_evt['id']
        
    return chain

def get_file_hash(path: str, project_dir: Path | None = None) -> str | None:
    if project_dir is None:
        p = Path(path)
    else:
        p = project_dir / path
        
    if not p.is_file():
        return None
        
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def make_file_ref(path: str, project_dir: Path | None = None) -> dict:
    h = get_file_hash(path, project_dir)
    return {"path": path, "git_hash": h or ""}

def check_file_refs(event: dict, project_dir: Path | None = None) -> list[dict]:
    stale = []
    refs = event.get('file_refs', [])
    if isinstance(refs, str):
        try:
            refs = json.loads(refs)
        except json.JSONDecodeError:
            refs = []
    if not refs:
        return stale
    for ref in refs:
        current_hash = get_file_hash(ref['path'], project_dir)
        if current_hash != ref.get('git_hash'):
            stale.append({
                "path": ref['path'],
                "stored_hash": ref.get('git_hash'),
                "current_hash": current_hash
            })
    return stale
