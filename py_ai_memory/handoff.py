import json
from datetime import datetime, timezone, timedelta
from py_ai_memory.config import Config
from py_ai_memory.store import create_event, append_event, read_events, get_event
from py_ai_memory.trust import compute_trust_state

def create_handoff(config: Config, *, summary: str, decisions: list[str] | None = None, questions: list[str] | None = None, next_steps: list[str] | None = None, files_modified: list[str] | None = None, actor: str = 'user', expires_days: int = 7) -> dict:
    content = {
        "summary": summary,
        "decisions_made": decisions or [],
        "open_questions": questions or [],
        "next_steps": next_steps or [],
        "files_modified": files_modified or []
    }
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()
    ev = create_event('handoff', content, actor=actor)
    ev['expires_at'] = expires_at
    append_event(config, ev)
    return ev

def accept_handoff(config: Config, handoff_id: str | None = None, *, actor: str = 'user') -> dict:
    if not handoff_id:
        handoffs = list_handoffs(config, include_expired=False)
        if not handoffs:
            raise ValueError("No pending handoffs found.")
        handoff_id = handoffs[-1]['id']
    
    ev = create_event('correct', "Handoff accepted", actor=actor, supersedes=handoff_id)
    append_event(config, ev)
    return ev

def list_handoffs(config: Config, include_expired: bool = False) -> list[dict]:
    events = read_events(config)
    handoffs = []
    now = datetime.now(timezone.utc).isoformat()
    for ev in events:
        if ev.get('type') == 'handoff':
            state = compute_trust_state(ev, events)
            if state != 'superseded':
                exp = ev.get('expires_at')
                if not include_expired and exp and now > exp:
                    continue
                handoffs.append(ev)
    return handoffs

def get_handoff(config: Config, handoff_id: str) -> dict | None:
    return get_event(config, handoff_id)

def format_handoff(handoff: dict) -> str:
    lines = []
    lines.append(f"Handoff ID: {handoff['id']}")
    content = handoff.get('content', {})
    if isinstance(content, str):
        lines.append(f"Summary: {content}")
        return "\n".join(lines)
    lines.append(f"Summary: {content.get('summary', '')}")
    if content.get('decisions_made'):
        lines.append("Decisions:")
        for d in content['decisions_made']: lines.append(f" - {d}")
    if content.get('open_questions'):
        lines.append("Open Questions:")
        for d in content['open_questions']: lines.append(f" - {d}")
    if content.get('next_steps'):
        lines.append("Next Steps:")
        for d in content['next_steps']: lines.append(f" - {d}")
    return "\n".join(lines)

def format_handoff_list(handoffs: list[dict]) -> str:
    lines = []
    for h in handoffs:
        content = h.get('content', {})
        summary = content.get('summary', str(content)) if isinstance(content, dict) else str(content)
        lines.append(f"{h['id']} - {summary[:50]}")
    return "\n".join(lines)
