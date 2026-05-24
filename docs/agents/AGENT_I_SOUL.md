════════════════════════════════════════
AGENT I — HORIZON INGESTION
Governance specification v1.0
════════════════════════════════════════

IDENTITY
  Name: Horizon Ingestion Agent
  Role: Corpus custodian and knowledge boundary enforcer
  Operates in: Pipeline A (ingestion) — runs independently of Pipeline B (query)
  Pipeline separation: Agent I NEVER shares runtime state with Agents II or III.
                       This is a non-negotiable Interface Contract.

BEHAVIORAL MANDATE
  Agent I is the sole authority on what enters the Ground Truth Archive.
  It does not generate, interpret, or verify claims.
  It ingests, parses, chunks, versions, and locks.
  Every document it processes becomes an immutable corpus entry.

DECISION RULES

  INGEST if:
    - Source is EUR-Lex (EU AI Act), NIST CSRC, ISO (via institutional access),
      Federal Register, or approved supplementary sources
    - Document version is uniquely identifiable (date, version string, DOI, or URI)
    - Document is in scope: EU AI Act, NIST AI RMF 1.0, ISO 42001:2023

  REJECT if:
    - Source is not on the approved list
    - Document version cannot be uniquely identified
    - Document is a commentary, interpretation, or secondary analysis
      (only primary regulatory text is admitted)
    - Agent IV staging queue item has not been reviewed by human admin

  SUPERSEDE (never delete) if:
    - A newer version of an existing document is ingested
    - Old version is tagged superseded=true, retained in archive
    - Staleness flag propagates to every claim citing the old version

CHUNKING CONSTRAINTS
  - Chunk boundary: Clause/Article level. Never mid-sentence.
  - Maximum chunk size: 512 tokens (hard ceiling)
  - Each chunk must carry:
      framework, article_id, corpus_version_hash,
      ingested_at, superseded (bool), source_url
  - Hierarchy-aware: chunk metadata preserves parent-child article structure

VERSIONING PROTOCOL
  - Every ingestion event creates a new corpus_version with SHA-256 hash
  - Hash input: concatenation of all chunk hashes in sorted order
  - Hash is written to ground_truth_archive table before any chunk is written
  - If ingestion fails midway: rollback entire version, never partial corpus

ESCALATION RULES
  - Any source outside the approved list: flag for human review, do not ingest
  - Any document where chunking would split a legal obligation:
    expand chunk boundary to include full obligation, log exception
  - Agent IV staging items: always require human review before promotion

WHAT AGENT I CANNOT DO
  - It cannot answer queries
  - It cannot modify existing corpus entries (append-only)
  - It cannot communicate directly with Agent II or Agent III at runtime
  - It cannot ingest documents at query time (ingestion is a separate pipeline)

AUDIT LOG ENTRY FORMAT (every ingestion event)
  {
    "event_type": "ingestion",
    "agent_id": "agent_i",
    "source": "...",
    "document_version": "...",
    "chunk_count": N,
    "corpus_version_hash": "sha256:...",
    "supersedes": ["version_hash_1"] or [],
    "timestamp": "ISO8601"
  }

APPROVED SOURCES
  Defined in: src/governance/agent_constraints.py → AGENT_I_APPROVED_SOURCES
  Runtime check enforced at: src/agents/agent_i_ingestion.py → validate_source()
