import json
import math
from datetime import datetime, timezone
from py_ai_memory.config import Config
from py_ai_memory.index import search_fts
from py_ai_memory.embeddings import search_semantic
from py_ai_memory.trust import get_supersession_chain, check_file_refs

def rrf_score(ranks: dict[str, int], k: int = 60) -> float:
    score = 0.0
    for channel, rank in ranks.items():
        score += 1.0 / (k + rank)
    return score

def temporal_decay(timestamp: str, lambda_: float = 0.01) -> float:
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
        return math.exp(-lambda_ * age_days)
    except ValueError:
        return 0.5

def trust_boost(trust_state: str) -> float | None:
    if trust_state == 'verified':
        return 1.0
    elif trust_state == 'candidate':
        return 0.7
    return None

def hybrid_search(config: Config, query: str, *, scope: str | None = None, limit: int = 10, budget_chars: int = 16000) -> list[dict]:
    fts_results = search_fts(config, query, scope=scope, limit=limit * 2)
    semantic_results = search_semantic(config, query, limit=limit * 2)

    # If both channels return nothing, bail
    if not fts_results and not semantic_results:
        return []

    # Build event lookup from FTS results
    fts_events = {e.get('event_id', e.get('id', e.get('filepath', ''))): e for e in fts_results}
    
    # Build event lookup from semantic results (fetch full events for those not in FTS)
    from py_ai_memory.store import get_event
    semantic_events = {}
    sem_cosine_scores = {}
    for eid, cosine_score in semantic_results:
        sem_cosine_scores[eid] = cosine_score
        if eid not in fts_events:
            ev = get_event(config, eid)
            if ev:
                semantic_events[eid] = ev

    all_events = {**fts_events, **semantic_events}
    
    # Build rank maps
    fts_ranks = {e.get('event_id', e.get('id', e.get('filepath', ''))): idx+1 for idx, e in enumerate(fts_results)}
    sem_ranks = {eid: idx+1 for idx, (eid, _) in enumerate(semantic_results)}

    scored_events = []
    from py_ai_memory.store import read_events
    from py_ai_memory.trust import compute_trust_state
    all_store_events = read_events(config)

    for eid, ev in all_events.items():
        ranks = {}
        if eid in fts_ranks:
            ranks['fts'] = fts_ranks[eid]
        if eid in sem_ranks:
            ranks['sem'] = sem_ranks[eid]
            
        rrf = rrf_score(ranks)

        # Boost by cosine similarity if available (adds semantic differentiation)
        cosine = sem_cosine_scores.get(eid, 0.0)
        semantic_boost = 1.0 + max(0.0, cosine)  # range [1.0, 2.0]

        ts = compute_trust_state(ev, all_store_events)
        
        tb = trust_boost(ts)
        if tb is None:
            continue
            
        td = temporal_decay(ev.get('timestamp', ''))
        final_score = rrf * semantic_boost * tb * td
        
        scored_events.append({
            'event_id': eid,
            'content': ev.get('content', ''),
            'score': final_score,
            'trust_state': ts,
            'timestamp': ev.get('timestamp', ''),
            'tags': ev.get('tags', []),
            'event_raw': ev
        })

    scored_events.sort(key=lambda x: x['score'], reverse=True)

    deduped = []
    seen_chains = set()
    for item in scored_events:
        chain = get_supersession_chain(config, item['event_id'])
        chain_ids = frozenset(e['id'] for e in chain)
        if chain_ids not in seen_chains:
            seen_chains.add(chain_ids)
            latest = chain[-1] if chain else item['event_raw']
            if latest['id'] == item['event_id']:
                if budget_chars > 0:
                    budget_chars -= len(str(item['content']))
                    if budget_chars < 0:
                        break
                
                stale_refs = check_file_refs(item['event_raw'], config.project_dir)
                item['stale_refs'] = stale_refs
                
                del item['event_raw']
                deduped.append(item)
    
    return deduped[:limit]

def format_recall(results: list[dict]) -> str:
    return json.dumps(results, indent=2)

def format_search(results: list[dict]) -> str:
    lines = []
    for r in results:
        ts = r.get('timestamp', '')
        state = r.get('trust_state', '')
        score = r.get('score', 0)
        lines.append(f"[{ts}] ({state}) [score: {score:.3f}] - {r.get('event_id')}")
        if r.get('stale_refs'):
            lines.append("  ⚠️ Stale references detected:")
            for ref in r['stale_refs']:
                lines.append(f"    - {ref['path']}")
        lines.append(f"  {r.get('content')}")
        lines.append("-" * 40)
    return "\n".join(lines)
