import json
from datetime import datetime, timezone
from py_ai_memory.config import Config

def log_mutation(config: Config, action: str, target_id: str, actor: str, reason: str = '') -> None:
    config.ensure_dirs()
    
    entry = {
        "action": action,
        "target_id": target_id,
        "actor": actor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason
    }
    
    with config.audit_path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')

def read_audit_log(config: Config) -> list[dict]:
    if not config.audit_path.is_file():
        return []
        
    entries = []
    with config.audit_path.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries

def format_audit_log(entries: list[dict]) -> str:
    lines = []
    for e in entries:
        dt = e['timestamp'][:19].replace('T', ' ')
        r_str = f" - Reason: {e['reason']}" if e.get('reason') else ""
        lines.append(f"[{dt}] {e['actor']} -> {e['action']} on {e['target_id']}{r_str}")
    return "\n".join(lines)
