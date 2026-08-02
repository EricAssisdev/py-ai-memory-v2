
from py_ai_memory.config import Config
from py_ai_memory.store import read_events, write_wiki_article, create_event, append_event
from py_ai_memory.index import index_event

def consolidate_events(config: Config) -> int:
    """
    Scans events, groups by tag, writes consolidated wiki articles, 
    and supersedes the old fragmented events.
    """
    events = read_events(config)
    
    # Track superseded and rejected events
    superseded_or_rejected = set()
    for ev in events:
        if ev.get('type') == 'reject':
            superseded_or_rejected.add(ev['id'])
            if ev.get('supersedes'):
                superseded_or_rejected.add(ev['supersedes'])
        elif ev.get('supersedes'):
            superseded_or_rejected.add(ev['supersedes'])

    # Group active events by first tag
    groups = {}
    for ev in events:
        if ev['id'] in superseded_or_rejected:
            continue
        if ev.get('type') == 'observe' and ev.get('tags'):
            tag = ev['tags'][0]
            groups.setdefault(tag, []).append(ev)
            
    count = 0
    for tag, evs in groups.items():
        if len(evs) < 2:
            continue # Need at least 2 events to consolidate
            
        # 1. Write File System Memory (Wiki)
        content_lines = [f"- [{e['timestamp']}] {e['content']}" for e in evs]
        content = f"# Consolidated Context: {tag}\n\n" + "\n".join(content_lines)
        
        filename = f"consolidated_{tag}.md"
        write_wiki_article(config, filename, {
            "title": f"Consolidated: {tag}",
            "tags": [tag, "consolidated"],
            "connections": [e['id'] for e in evs]
        }, content)
        
        # 2. Supersede old events to clean up short-term search
        for e in evs:
            sup_evt = create_event('supersede', f"Consolidated into {filename}", supersedes=e['id'], tags=["system"])
            append_event(config, sup_evt)
            index_event(config, sup_evt)
            
        count += 1
        
    return count
