"""
Runtime enforcement of governance constraints documented in docs/agents/SOUL.md files.
SOUL.md = documentation. This file = enforcement.
Import these constants in pipeline code — do NOT hardcode thresholds elsewhere.
"""

# ── Agent I — Horizon Ingestion ───────────────────────────────────────────────

AGENT_I_APPROVED_SOURCES = [
    "eur-lex.europa.eu",
    "nvlpubs.nist.gov",
    "iso.org",
    "federalregister.gov",
    "digital-strategy.ec.europa.eu",
    "csrc.nist.gov",
    "bsigroup.com",
]

AGENT_I_IN_SCOPE_FRAMEWORKS = [
    "EU AI Act",
    "NIST AI RMF 1.0",
    "ISO 42001:2023",
]

AGENT_I_MAX_CHUNK_TOKENS = 512

# ── Agent II — Persona Synthesis ──────────────────────────────────────────────

AGENT_II_TEMPERATURE = 0.1
AGENT_II_MAX_TOKENS = 2000
AGENT_II_MIN_RETRIEVAL_SPANS = 3
AGENT_II_TOP_K = 10

AGENT_II_PERSONA_STYLES = {
    "lead_auditor": {
        "output_style": "Formal. Citation-first. Risk-framed. EU AI Act penalty exposure noted.",
        "depth": "comprehensive",
    },
    "ml_engineer": {
        "output_style": "Technical. Implementation-focused. Code-adjacent where relevant.",
        "depth": "practical",
    },
    "legal_counsel": {
        "output_style": "Precise. Article-by-article. Obligation vs. recommendation distinguished.",
        "depth": "exhaustive",
    },
    "hr_auditor": {
        "output_style": "Policy-focused. Employment law context. Human rights framing.",
        "depth": "comprehensive",
    },
    "qa_engineer": {
        "output_style": "Process-focused. Testability and measurability emphasized.",
        "depth": "practical",
    },
}

# ── Agent III — Zero-Trust Critic ─────────────────────────────────────────────

AGENT_III_PERSONA_THRESHOLDS = {
    "lead_auditor": 0.96,
    "ml_engineer": 0.88,
    "legal_counsel": 0.96,
    "hr_auditor": 0.92,
    "qa_engineer": 0.90,
}

AGENT_III_FAILURE_THRESHOLDS = {
    "retry_single": 1,       # single blocked claim → expand retrieval (top-k=15)
    "decompose_query": 0.30, # >30% claims failed → decompose into sub-queries
    "insufficient_evidence": 0.50,  # >50% failed → INSUFFICIENT_EVIDENCE verdict
}

AGENT_III_HIGH_CONFIDENCE_CONTRADICTION_THRESHOLD = 0.90

AGENT_III_NLI_MODEL = "nlpaueb/legal-bert-base-uncased"

AGENT_III_EXPANDED_TOP_K = 15  # retry top-k after single claim failure

# ── Verdict labels ────────────────────────────────────────────────────────────

VERDICT_COMPLIANT = "COMPLIANT"
VERDICT_PARTIALLY_COMPLIANT = "PARTIALLY COMPLIANT"
VERDICT_NON_COMPLIANT = "NON_COMPLIANT"
VERDICT_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

NLI_DECISION_PASS = "PASS"
NLI_DECISION_FLAG = "FLAG"
NLI_DECISION_BLOCK = "BLOCK"
