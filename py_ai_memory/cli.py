import sys
import argparse
import json
from pathlib import Path

from py_ai_memory.config import Config
from py_ai_memory.store import create_event, append_event, read_events
from py_ai_memory.index import init_db, rebuild_index, index_event
from py_ai_memory.search import hybrid_search, format_search
from py_ai_memory.trust import correct_event, reject_event, verify_event, get_supersession_chain
from py_ai_memory.audit import read_audit_log, format_audit_log
from py_ai_memory.handoff import create_handoff, accept_handoff, list_handoffs, format_handoff_list
from py_ai_memory.consolidation import consolidate_events


def cmd_init(args, config: Config):
    config.ensure_dirs()
    init_db(config)
    print(f"Initialized ai-memory in {config.memory_dir}")

def cmd_status(args, config: Config):
    events = read_events(config)
    print(f"Project dir: {config.project_dir}")
    print(f"Active branch: {config.git_branch}")
    print(f"Total events: {len(events)}")

def cmd_add(args, config: Config):
    event = create_event('observe', args.content, tags=args.tags)
    evt_id = append_event(config, event)
    index_event(config, event)
    print(f"Added event: {evt_id}")

def cmd_rebuild(args, config: Config):
    count = rebuild_index(config)
    print(f"Rebuilt index with {count} items")

def cmd_search(args, config: Config):
    results = hybrid_search(config, args.query, limit=args.limit)
    print(format_search(results))

def cmd_reject(args, config):
    evt = reject_event(config, args.target_id, args.reason)
    print(f"Rejected {args.target_id} -> Tombstone: {evt['id']}")

def cmd_correct(args, config):
    evt = correct_event(config, args.target_id, args.content)
    print(f"Corrected {args.target_id} -> New event: {evt['id']}")

def cmd_verify(args, config):
    evt = verify_event(config, args.target_id)
    print(f"Verified {args.target_id}")

def cmd_history(args, config):
    chain = get_supersession_chain(config, args.target_id)
    for c in chain:
        print(f"[{c['timestamp']}] {c['id']} ({c['type']})")

def cmd_audit(args, config):
    entries = read_audit_log(config)
    print(format_audit_log(entries))

def cmd_handoff(args, config):
    evt = create_handoff(config, summary=args.summary, decisions=args.decisions, questions=args.questions, next_steps=args.next_steps, files_modified=args.files)
    print(f"Created handoff: {evt['id']}")

def cmd_handoffs(args, config):
    handoffs = list_handoffs(config, include_expired=args.all)
    print(format_handoff_list(handoffs))

def cmd_accept(args, config):
    evt = accept_handoff(config, args.target_id)
    print(f"Accepted handoff -> New event: {evt['id']}")

def cmd_consolidate(args, config: Config):
    count = consolidate_events(config)
    print(f"Consolidated {count} topics into Wiki articles.")


def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    
    parser = argparse.ArgumentParser(prog="memory", description="py-ai-memory CLI")
    parser.add_argument("--project-dir", type=str, help="Project directory")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    init_p = subparsers.add_parser("init", help="Initialize memory in project")
    status_p = subparsers.add_parser("status", help="Show memory status")
    
    add_p = subparsers.add_parser("add", help="Add an observe event")
    add_p.add_argument("content", type=str, help="Event content")
    add_p.add_argument("--tags", type=str, nargs="*", help="Tags for event")
    
    rebuild_p = subparsers.add_parser("rebuild", help="Rebuild the search index")
    
    search_p = subparsers.add_parser("search", help="Search the memory index")
    search_p.add_argument("query", type=str, help="Search query")
    search_p.add_argument("--limit", type=int, default=10, help="Maximum number of results")
    
    reject_p = subparsers.add_parser("reject")
    reject_p.add_argument("target_id")
    reject_p.add_argument("--reason", required=True)

    correct_p = subparsers.add_parser("correct")
    correct_p.add_argument("target_id")
    correct_p.add_argument("content")

    verify_p = subparsers.add_parser("verify")
    verify_p.add_argument("target_id")

    history_p = subparsers.add_parser("history")
    history_p.add_argument("target_id")

    audit_p = subparsers.add_parser("audit")
    
    handoff_p = subparsers.add_parser("handoff")
    handoff_p.add_argument("summary")
    handoff_p.add_argument("--decisions", nargs="*")
    handoff_p.add_argument("--questions", nargs="*")
    handoff_p.add_argument("--next_steps", nargs="*")
    handoff_p.add_argument("--files", nargs="*")

    handoffs_p = subparsers.add_parser("handoffs")
    handoffs_p.add_argument("--all", action="store_true")

    accept_p = subparsers.add_parser("accept")
    accept_p.add_argument("target_id", nargs="?", default=None)

    p_consolidate = subparsers.add_parser('consolidate', help="Consolidate old events into Wiki articles")
    p_consolidate.set_defaults(func=cmd_consolidate)


    args = parser.parse_args()
    config = Config(Path(args.project_dir) if args.project_dir else None)
    
    if args.command == "init":
        cmd_init(args, config)
    elif args.command == "status":
        cmd_status(args, config)
    elif args.command == "add":
        cmd_add(args, config)
    elif args.command == "rebuild":
        cmd_rebuild(args, config)
    elif args.command == "search":
        cmd_search(args, config)
    elif args.command == "reject":
        cmd_reject(args, config)
    elif args.command == "correct":
        cmd_correct(args, config)
    elif args.command == "verify":
        cmd_verify(args, config)
    elif args.command == "history":
        cmd_history(args, config)
    elif args.command == "audit":
        cmd_audit(args, config)
    elif args.command == "handoff":
        cmd_handoff(args, config)
    elif args.command == "handoffs":
        cmd_handoffs(args, config)
    elif args.command == "accept":
        cmd_accept(args, config)
    elif args.command == "consolidate":
        cmd_consolidate(args, config)


if __name__ == "__main__":
    main()
