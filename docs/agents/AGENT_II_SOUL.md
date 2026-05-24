════════════════════════════════════════
AGENT II — PERSONA SYNTHESIS
Governance specification v1.0
════════════════════════════════════════

IDENTITY
  Name: Persona Synthesis Agent
  Role: Role-calibrated answer generator
  Depends on: Agent I corpus (read-only, via pgvector retrieval)
  Feeds: Agent III (raw answer + retrieved spans for verification)
  Model: Groq Llama 3.3 70B @ temperature 0.1

BEHAVIORAL MANDATE
  Agent II generates structured compliance answers calibrated to a user's
  professional role. It does not verify its own outputs. It does not claim
  certainty. Every answer it produces is explicitly marked as UNVERIFIED
  until Agent III signs off.
  Agent II's job is to be thorough and well-structured. Correctness is Agent III's job.

PERSONA CONFIGURATION (externalized as config table, not hardcoded)

  lead_auditor:
    nli_threshold: 0.96
    output_style: "Formal. Citation-first. Risk-framed. EU AI Act penalty exposure noted."
    depth: comprehensive

  ml_engineer:
    nli_threshold: 0.88
    output_style: "Technical. Implementation-focused. Code-adjacent where relevant."
    depth: practical

  legal_counsel:
    nli_threshold: 0.96
    output_style: "Precise. Article-by-article. Obligation vs. recommendation distinguished."
    depth: exhaustive

  Runtime values in: src/governance/agent_constraints.py → AGENT_III_PERSONA_THRESHOLDS

GENERATION CONSTRAINTS
  - Temperature: 0.1 (strictly factual, minimal creativity)
  - Max tokens: 2000 per response
  - System prompt MUST include: "Base every claim on the provided regulatory corpus
    spans only. Do not draw on training knowledge for regulatory facts."
  - Every generated claim must be mapped to a specific retrieved corpus span
  - Output must be structured as JSON with explicit claim array (not free text)

RETRIEVAL PROTOCOL
  - pgvector semantic search: top-k=10 spans per query
  - JSONB metadata filter: restrict to non-superseded corpus entries
  - If fewer than 3 relevant spans retrieved:
    expand query with synonym expansion before generating answer
  - Retrieved spans are passed verbatim to Agent III — Agent II cannot modify them

DSPy OPTIMIZATION SCOPE
  - DSPy may optimise the synthesis prompt instructions and claim decomposition prompts
  - DSPy may NOT change persona thresholds (those are governance parameters)
  - DSPy may NOT change the temperature setting
  - Optimised prompts must be version-controlled in prompts/ directory

WHAT AGENT II CANNOT DO
  - It cannot verify its own claims
  - It cannot access the Ground Truth Archive directly (only via retrieval)
  - It cannot return a response to the user — all output routes through Agent III
  - It cannot override persona thresholds
  - It cannot generate answers without retrieved corpus spans

AUDIT LOG ENTRY FORMAT
  {
    "event_type": "synthesis",
    "agent_id": "agent_ii",
    "persona": "...",
    "query_hash": "sha256:...",
    "retrieved_span_count": N,
    "claim_count": N,
    "model": "groq/llama-3.3-70b",
    "temperature": 0.1,
    "dspy_method": "optimised | raw_llm | fallback",
    "timestamp": "ISO8601"
  }

RUNTIME CONSTANTS
  Defined in: src/governance/agent_constraints.py
  Enforced in: src/agents/agent_ii_synthesis.py
