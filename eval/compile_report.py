"""
Phase 6E — Compile final evaluation report.
Aggregates scored results + NLI comparison into ReguLens_Evaluation_Report_v1.json.

Usage:
    python eval/compile_report.py \
        --scored eval/scored_results_YYYYMMDD_HHMM.json \
        --nli eval/nli_comparison_results_YYYYMMDD_HHMM.json \
        --corpus-version <sha256_hash> \
        --output eval/ReguLens_Evaluation_Report_v1.json
"""

import argparse
import json
import statistics
from datetime import datetime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scored", required=True, help="Output of score_results.py")
    parser.add_argument("--nli", required=True, help="Output of nli_comparison.py")
    parser.add_argument("--corpus-version", default="unknown", help="SHA-256 corpus hash")
    parser.add_argument("--output", default="eval/ReguLens_Evaluation_Report_v1.json")
    args = parser.parse_args()

    scored_data = json.load(open(args.scored))
    nli_data = json.load(open(args.nli))

    summary = scored_data["summary"]
    sm = summary["summary_metrics"]
    by_persona = summary["by_persona"]
    by_tier = summary["by_tier"]

    per_task = scored_data["per_task"]
    elapsed_vals = [t.get("elapsed_seconds") for t in per_task if t.get("elapsed_seconds")]
    p95 = sorted(elapsed_vals)[int(len(elapsed_vals) * 0.95)] if elapsed_vals else None

    nli_models = nli_data.get("models", {})
    legal_bert_f1 = nli_models.get("legal_bert", {}).get("metrics", {}).get("per_class", {}).get("supported", {}).get("f1")
    deberta_f1 = nli_models.get("deberta", {}).get("metrics", {}).get("per_class", {}).get("supported", {}).get("f1")

    report = {
        "run_date": datetime.now().isoformat(),
        "corpus_version": args.corpus_version,
        "benchmark_tasks_run": len(per_task),
        "summary_metrics": {
            "claim_level_precision": sm.get("claim_level_precision"),
            "claim_level_recall": sm.get("claim_level_recall"),
            "claim_level_f1": sm.get("claim_level_f1"),
            "false_negative_rate_overall": sm.get("false_negative_rate_overall"),
            "answer_correctness_mean": sm.get("answer_correctness_mean"),
            "answer_completeness_mean": sm.get("answer_completeness_mean"),
            "legal_defensibility_mean": sm.get("legal_defensibility_mean"),
            "would_use_without_modification_pct": sm.get("would_use_without_modification_pct"),
        },
        "by_persona": {
            persona: {
                "fnr": data.get("avg_fnr"),
                "fpr": None,  # requires ROC annotation
                "threshold": data.get("threshold"),
                "avg_claim_f1": data.get("avg_claim_f1"),
            }
            for persona, data in by_persona.items()
        },
        "by_tier": {
            tier: {
                "count": data.get("count"),
                "avg_claim_f1": data.get("avg_claim_f1"),
                "avg_correctness": data.get("avg_correctness"),
            }
            for tier, data in by_tier.items()
        },
        "nli_comparison": {
            "legal_bert_f1": legal_bert_f1,
            "deberta_f1": deberta_f1,
            "winner": nli_data.get("winner"),
            "recommendation": nli_data.get("recommendation"),
        },
        "timing": {
            "avg_response_seconds": round(sum(elapsed_vals) / len(elapsed_vals), 2) if elapsed_vals else None,
            "p95_response_seconds": round(p95, 2) if p95 else None,
            "manual_baseline_seconds": None,  # fill from client (Bilal/Aditya/Prakash) feedback
        },
    }

    json.dump(report, open(args.output, "w"), indent=2)
    print(f"Report compiled → {args.output}")
    print(f"Claim F1: {report['summary_metrics']['claim_level_f1']}")
    print(f"FNR overall: {report['summary_metrics']['false_negative_rate_overall']}")
    print(f"NLI winner: {report['nli_comparison']['winner']}")
    print(f"manual_baseline_seconds: NULL — fill after client study returns")


if __name__ == "__main__":
    main()
