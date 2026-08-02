import sqlite3
import json
from py_ai_memory.config import Config
from py_ai_memory.store import read_events, list_wiki_articles, read_wiki_article

def get_db(config: Config) -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(config: Config) -> sqlite3.Connection:
    conn = get_db(config)
    conn.executescript("""
    CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
        event_id, type, content, tags, actor, scope, branch,
        tokenize = 'unicode61'
    );
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        actor TEXT NOT NULL,
        scope TEXT NOT NULL,
        branch TEXT NOT NULL,
        content TEXT NOT NULL,
        tags TEXT NOT NULL,
        source TEXT NOT NULL,
        supersedes TEXT,
        confidence REAL NOT NULL,
        file_refs TEXT NOT NULL,
        trust_state TEXT NOT NULL DEFAULT 'verified',
        reason TEXT
    );
    CREATE TABLE IF NOT EXISTS wiki_index (
        filepath TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        tags TEXT NOT NULL,
        content TEXT NOT NULL,
        derived_from TEXT NOT NULL DEFAULT '[]'
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS wiki_fts USING fts5(
        filepath, title, tags, content,
        tokenize = 'unicode61'
    );
    CREATE TABLE IF NOT EXISTS embeddings (
        event_id TEXT PRIMARY KEY,
        model TEXT NOT NULL,
        vector BLOB NOT NULL
    );
    CREATE TABLE IF NOT EXISTS memory_graph (
        source TEXT NOT NULL,
        target TEXT NOT NULL,
        relationship TEXT DEFAULT 'references',
        PRIMARY KEY (source, target)
    );
    """)
    return conn

def rebuild_index(config: Config) -> int:
    conn = init_db(config)
    conn.executescript("""
        DELETE FROM memory_fts;
        DELETE FROM events;
        DELETE FROM wiki_index;
        DELETE FROM wiki_fts;
        DELETE FROM embeddings;
        DELETE FROM memory_graph;
    """)
    
    events = read_events(config)
    
    # Calculate simple trust states for indexing (full trust engine is in Task 5)
    rejected_ids = set()
    superseded_ids = set()
    
    for evt in events:
        if evt.get('type') == 'reject':
            rejected_ids.add(evt['id'])
            if evt.get('supersedes'):
                rejected_ids.add(evt['supersedes'])
        elif evt.get('supersedes'):
            superseded_ids.add(evt['supersedes'])

    # Collect texts for batch embedding
    embed_batch_ids = []
    embed_batch_texts = []

    count = 0
    with conn:
        for evt in events:
            trust_state = 'verified'
            if evt['id'] in rejected_ids:
                trust_state = 'rejected'
            elif evt['id'] in superseded_ids:
                trust_state = 'superseded'
            elif evt.get('source') == 'inferred':
                trust_state = 'candidate'
                
            content_str = json.dumps(evt['content']) if isinstance(evt['content'], dict) else evt['content']
            
            conn.execute("""
                INSERT INTO events (event_id, type, timestamp, actor, scope, branch, content, tags, source, supersedes, confidence, file_refs, trust_state, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (evt['id'], evt['type'], evt['timestamp'], evt['actor'], evt['scope'], evt['branch'], content_str, json.dumps(evt.get('tags', [])), evt.get('source', 'observed'), evt.get('supersedes'), evt.get('confidence', 1.0), json.dumps(evt.get('file_refs', [])), trust_state, evt.get('reason')))
            
            conn.execute("""
                INSERT INTO memory_fts (event_id, type, content, tags, actor, scope, branch)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (evt['id'], evt['type'], content_str, " ".join(evt.get('tags', [])), evt['actor'], evt['scope'], evt['branch']))

            # Queue for batch embedding (skip rejected/superseded)
            if trust_state not in ('rejected', 'superseded'):
                embed_batch_ids.append(evt['id'])
                embed_batch_texts.append(content_str[:2000])  # Truncate for embedding model
            
            count += 1
            
        for wiki_path in list_wiki_articles(config):
            try:
                meta, content = read_wiki_article(config, wiki_path.name)
                tags = " ".join(meta.get('tags', []))
                title = meta.get('title', wiki_path.stem)
                conn.execute("INSERT INTO wiki_index (filepath, title, tags, content) VALUES (?, ?, ?, ?)", (wiki_path.name, title, tags, content))
                conn.execute("INSERT INTO wiki_fts (filepath, title, tags, content) VALUES (?, ?, ?, ?)", (wiki_path.name, title, tags, content))
                
                # Extract graph connections
                connections = meta.get('connections', [])
                if isinstance(connections, list):
                    for target in connections:
                        conn.execute("INSERT INTO memory_graph (source, target) VALUES (?, ?)", (wiki_path.name, str(target)))
                count += 1
            except Exception:
                pass

    # Batch embed all events
    if embed_batch_texts:
        from py_ai_memory.embeddings import embed_texts, store_embedding
        vectors, model_name = embed_texts(embed_batch_texts)
        for eid, vec in zip(embed_batch_ids, vectors):
            store_embedding(config, eid, vec, model_name)

    return count


def index_event(config: Config, event: dict) -> None:
    """Index a single event into FTS and embeddings. Called on `memory add`."""
    conn = init_db(config)
    content_str = json.dumps(event['content']) if isinstance(event['content'], dict) else event['content']
    tags_str = " ".join(event.get('tags', []))

    with conn:
        # Insert into events table
        conn.execute("""
            INSERT OR REPLACE INTO events (event_id, type, timestamp, actor, scope, branch, content, tags, source, supersedes, confidence, file_refs, trust_state, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (event['id'], event['type'], event['timestamp'], event['actor'], event['scope'], event['branch'], content_str, json.dumps(event.get('tags', [])), event.get('source', 'observed'), event.get('supersedes'), event.get('confidence', 1.0), json.dumps(event.get('file_refs', [])), 'verified', event.get('reason')))

        # Insert into FTS
        conn.execute("""
            INSERT INTO memory_fts (event_id, type, content, tags, actor, scope, branch)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event['id'], event['type'], content_str, tags_str, event['actor'], event['scope'], event['branch']))

    # Generate and store embedding
    from py_ai_memory.embeddings import embed_text, store_embedding
    vector, model_name = embed_text(content_str[:2000])
    store_embedding(config, event['id'], vector, model_name)

def _sanitize_fts_query(query: str) -> str:
    """Sanitize a query for FTS5 MATCH syntax. Removes special chars, wraps each word in quotes."""
    import re
    # Remove FTS5 special chars that cause syntax errors
    cleaned = re.sub(r'[^\w\s]', ' ', query, flags=re.UNICODE)
    words = [w.strip() for w in cleaned.split() if w.strip()]
    if not words:
        return '""'
    # Quote each word and join with OR for flexible matching
    return " OR ".join(f'"{w}"' for w in words)

def search_fts(config: Config, query: str, scope: str | None = None, limit: int = 10) -> list[dict]:
    conn = get_db(config)
    results = []
    safe_query = _sanitize_fts_query(query)
    
    try:
        cur = conn.execute(f"""
            SELECT e.*, m.rank 
            FROM memory_fts m
            JOIN events e ON m.event_id = e.event_id
            WHERE memory_fts MATCH ? AND e.trust_state NOT IN ('rejected', 'superseded')
            ORDER BY m.rank LIMIT ?
        """, (safe_query, limit))
        
        for row in cur:
            d = dict(row)
            d['is_wiki'] = False
            results.append(d)
    except Exception:
        pass  # FTS failure should not prevent semantic search
        
    try:
        cur = conn.execute(f"""
            SELECT w.*, wf.rank 
            FROM wiki_fts wf
            JOIN wiki_index w ON wf.filepath = w.filepath
            WHERE wiki_fts MATCH ?
            ORDER BY wf.rank LIMIT ?
        """, (safe_query, limit))
        
        for row in cur:
            d = dict(row)
            d['is_wiki'] = True
            results.append(d)
    except Exception:
        pass
        
    return sorted(results, key=lambda x: x['rank'])
