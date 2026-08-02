# py-ai-memory v2 🧠

![Status](https://img.shields.io/badge/status-production_ready-success)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Architecture](https://img.shields.io/badge/architecture-Enterprise_Grade-purple)

An advanced, enterprise-grade persistent memory system for autonomous AI agents. Built to solve the "context window decay" and "hallucination loop" problems found in long-running, multi-agent AI coding sessions.

## 🌟 The Problem

Most AI agent memory systems rely purely on naive Vector Databases. Over time, these systems suffer from outdated information overriding new context, causing agents to get stuck in hallucination loops. Furthermore, in corporate environments, sending source code context to external SaaS vector databases poses significant privacy and compliance risks.

## ✨ The Solution

`py-ai-memory-v2` introduces a multi-tiered, 100% local architecture:

1. **Immutable Ledger (Short-Term Memory):** An append-only JSONL log (`events.jsonl`) that records every observation, decision, and state change. Nothing is ever deleted, providing a perfect cryptographic-like audit trail.
2. **Wiki Articles (Long-Term Memory):** Background consolidation groups raw events into dense, highly-structured Markdown documents (`.ai-memory/wiki/`).
3. **GraphRAG:** Wiki articles are linked via YAML frontmatter, creating a Knowledge Graph that allows the AI to traverse architectural dependencies (e.g., *Frontend* -> depends on -> *Auth Service*).
4. **Hybrid Search Engine:** Combines **FTS5** (Full-Text Search) and **Semantic Vector Search** using RRF (Reciprocal Rank Fusion). Scores are further weighted by **Temporal Decay** (newer is better) and **Trust State** (verified vs. assumption).
5. **Thread-Safe Concurrency:** Features an OS-level Atomic File Locking mechanism, allowing massive fleets of parallel subagents to write memories simultaneously without data corruption.

## 🚀 Key Features

- **Zero Data Leakage:** Uses SQLite, local Markdown, and local JSONL. No SaaS lock-in, zero network calls for storage. Perfect for high-compliance corporate environments.
- **Atomic File Locking:** Stress-tested against hundreds of concurrent write threads with 0% data corruption.
- **Handoff Protocol:** Seamless state transfer between parallel agents and sequential user sessions.
- **Self-Healing:** Agents can mark previous assumptions as "rejected" (tombstoning), which removes them from active search without breaking the immutable audit log.

## 🛠️ Installation

Ensure you have Python 3.12+ and `uv` installed.

```bash
git clone https://github.com/EricAssisdev/py-ai-memory-v2.git
cd py-ai-memory-v2
uv sync
```

## 📖 Usage Guide

The system exposes a robust CLI for agents to interact with:

### 1. Initialize the Memory Workspace
```bash
uv run memory init
```
*Creates the `.ai-memory/` local database structure in the current project.*

### 2. Add a Memory Event
```bash
uv run memory add "Decided to use PostgreSQL 16 due to JSONB performance requirements" --tags architecture database
```
*Appends the event to the immutable ledger and indexes it.*

### 3. Search Memory (Hybrid)
```bash
uv run memory search "database architecture" --limit 5
```
*Returns the most relevant events and Wiki articles, ranked by hybrid semantic+FTS scoring and temporal decay.*

### 4. Consolidate (Long-Term Memory)
```bash
uv run memory consolidate
```
*Reads active raw events and consolidates them into dense Knowledge Graph Wiki articles, marking the raw events as superseded.*

### 5. Handoffs
```bash
uv run memory handoff "Summarized frontend state" --next_steps "Implement auth guard"
uv run memory handoffs
uv run memory accept <handoff_id>
```

## 🏗️ Architecture

```text
.ai-memory/
├── logs/
│   └── events.jsonl       # The Immutable Source of Truth
├── index/
│   └── memory.db          # SQLite Database (FTS5 + GraphRAG + Embeddings)
└── wiki/
    ├── architecture.md    # Consolidated Knowledge Graph Nodes
    └── ...
```

## 🛡️ License

This project is licensed under the MIT License - see the LICENSE file for details.
