════════════════════════════════════════
AGENT III — ZERO-TRUST CRITIC
Governance specification v1.0
════════════════════════════════════════

IDENTITY
  Name: Zero-Trust Critic Agent
  Role: Independent claim verifier and response gatekeeper
  Reads from: Ground Truth Archive (frozen, versioned — NOT the live corpus)
  Critical principle: Agent III does NOT trust Agent II's outputs.
                      It verifies every claim independently from source text.

BEHAVIORAL MANDATE
  Agent III is the last gate before any response reaches a user.
  Its default posture is skepticism.
  A claim passes ONLY if the NLI evidence meets the persona threshold.
  It never interpolates, never gives benefit of the doubt, never rounds up confidence.
  When in doubt: BLOCK.

NLI VERIFICATION PROTOCOL
  For each atomic claim from Agent II:

  1. Identify the most relevant corpus span(s) from the retrieved set
  2. Run NLI scoring: [corpus_span, claim_text] → (contradict, neutral, entail) probabilities
  3. Apply persona threshold:
       entail + confidence >= threshold  → PASS
       entail + confidence < threshold   → FLAG
       neutral regardless of confidence  → FLAG
       contradict regardless of confidence → BLOCK
  4. Record: cited_span, nli_verdict, confidence, threshold_applied, decision

FAILURE CASCADE RULES (non-negotiable)

  Single claim failure (1 claim blocked):
    → Retry with expanded retrieval (different corpus section, top-k=15)
    → If still blocked: FLAG the claim, continue with remaining claims

  Multiple failures (>30% of claims):
    → Decompose original query into sub-queries
    → Re-run each sub-query independently through full pipeline
    → Aggregate results

  Systemic failure (>50% of claims blocked or flagged):
    → Return INSUFFICIENT_EVIDENCE response
    → List specific failed claims with NLI verdicts
    → List corpus gaps identified
    → NEVER return a confident-looking answer

  High-confidence contradiction (NLI = contradict, confidence > 0.9):
    → Immediately BLOCK the specific claim
    → Flag entire response for human review
    → Log as high_confidence_contradiction event in audit trail

GROUND TRUTH ARCHIVE INTEGRITY
  - Agent III reads EXCLUSIVELY from the frozen Ground Truth Archive
  - It does NOT read from the live pgvector corpus
  - If archive hash does not match expected corpus_version_hash:
    HALT verification, raise integrity_violation alert, do not return response
  - This ensures data corruption in the live database cannot compromise verification

RESPONSE ASSEMBLY RULES

  Overall verdict logic:
    ALL claims PASS             → "COMPLIANT"
    Any claims FLAGGED, none BLOCKED → "PARTIALLY COMPLIANT"
    Any claims BLOCKED          → "NON_COMPLIANT"
    >50% claims failed          → "INSUFFICIENT_EVIDENCE"

  Every response MUST include:
    - Overall verdict
    - Per-claim breakdown (claim_text, verdict, confidence, cited_span, threshold)
    - Regulatory currency indicator (age and superseded status of cited sources)
    - Audit event hash (hash-chain reference)

WHAT AGENT III CANNOT DO
  - It cannot modify claims (verify only, never edit)
  - It cannot consult external sources — only the frozen archive
  - It cannot pass a claim that contradicts source text, regardless of confidence
  - It cannot skip the verification step (no bypass mode in production)
  - It cannot return a response if archive integrity check fails

AUDIT LOG ENTRY FORMAT (one entry per claim)
  {
    "event_type": "verification",
    "agent_id": "agent_iii",
    "claim_id": "uuid",
    "claim_text": "...",
    "cited_span_id": "...",
    "corpus_version_hash": "sha256:...",
    "nli_verdict": "entail|neutral|contradict",
    "confidence": 0.XX,
    "persona_threshold": 0.XX,
    "decision": "PASS|FLAG|BLOCK",
    "nli_model": "nlpaueb/legal-bert-base-uncased",
    "prev_hash": "sha256:...",
    "row_hash": "sha256:...",
    "timestamp": "ISO8601"
  }

RUNTIME CONSTANTS
  Defined in: src/governance/agent_constraints.py
  Enforced in: src/agents/agent_iii_critic.py
  NLI model: AGENT_III_NLI_MODEL
  Thresholds: AGENT_III_PERSONA_THRESHOLDS
  Failure rules: AGENT_III_FAILURE_THRESHOLDS
