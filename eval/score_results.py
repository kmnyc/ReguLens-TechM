"""
Phase 6C — Scoring engine.
Computes claim-level precision/recall/F1 and answer-level scores
from human-annotated results.

Usage:
    python eval/score_results.py \
        --results eval/results_YYYYMMDD_HHMM.json \
        --annotations eval/annotations_YYYYMMDD_HHMM.json \
        --output eval/scored_results_YYYYMMDD_HHMM.json
"""

import argparse
import json
import statistics
from datetime import datetime


PERSONA_THRESHOLDS = {
    "lead_auditor": 0.96,
    "ml_engineer": 0.88,
    "legal_counsel": 0.96,
}


def compute_claim_metrics(claims: list, annotations: dict) -> dict:
    """
    annotations keyed by claim_id → {"human_label": "supported"|"unsupported"|"contradicted"}
    nli_label mapping: entail→supported, neutral→unsupported, contradict→contradicted
    """
    NLI_MAP = {"entail": "supported", "neutral": "unsupported", "contradict": "contradicted"}

    TP = FP = FN = TN = 0
    agreements = []

    for claim in claims:
        cid = claim.get("claim_id") or claim.get("id")
        ann = annotations.get(str(cid), {})
        human_label = ann.get("human_label")
        nli_raw = claim.get("nli_verdict") or claim.get("verdict", "neutral")
        nli_label = NLI_MAP.get(nli_raw, "unsupported")

        if human_label is None:
            continue

        agreement = human_label == nli_label
        agreements.append(agreement)

        if human_label == "supported" and nli_label == "supported":
            TP += 1
        elif human_label == "supported" and nli_label != "supported":
            FN += 1
        elif human_label != "supported" and nli_label == "supported":
            FP += 1
        else:
            TN += 1

    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fnr = FN / (FN + TP) if (FN + TP) > 0 else 0.0
    accuracy = sum(agreements) / len(agreements) if agreements else 0.0

    return {
        "TP": TP, "FP": FP, "FN": FN, "TN": TN,
        "claim_precision": round(precision, 4),
        "claim_recall": round(recall, 4),
        "claim_f1": round(f1, 4),
        "false_negative_rate": round(fnr, 4),
        "verdict_agreement_accuracy": round(accuracy, 4),
    }


def compute_threshold_metrics(results: list, persona: str, threshold: float) -> dict:
    """
    For each claim, check if confidence above/below threshold matches human support label.
    Annotated results required — skips unannotated.
    """
    fp_count = fn_count = total = 0
    for r in results:
        if r.get("persona") != persona:
            continue
        for claim in r.get("claims", []):
            conf = claim.get("confidence", 0)
            decision = claim.get("decision", "")
            human = claim.get("_human_label")  # injected by annotation merge
            if human is None:
                continue
            total += 1
            if human == "supported" and conf < threshold:
                fp_count += 1  # supported claim blocked (false positive block)
            if human != "supported" and conf >= threshold:
                fn_count += 1  # unsupported claim passed (false negative pass)

    return {
        "persona": persona,
        "threshold": threshold,
        "false_positive_rate": round(fp_count / total, 4) if total else None,
        "false_negative_rate": round(fn_count / total, 4) if total else None,
        "claims_evaluated": total,
    }


def score_task(task_result: dict, task_annotations: dict) -> dict:
    claims = task_result.get("claims", [])
    claim_metrics = compute_claim_metrics(claims, task_annotations.get("claims", {}))
    answer_scores = task_annotations.get("answer_scores", {})

    return {
        "task_id": task_result["task_id"],
        "tier": task_result["tier"],
        "persona": task_result["persona"],
        "overall_verdict": task_result.get("overall_verdict"),
        "elapsed_seconds": task_result.get("elapsed_seconds"),
        "claim_metrics": claim_metrics,
        "answer_correctness": answer_scores.get("correctness"),
        "answer_completeness": answer_scores.get("completeness"),
        "legal_defensibility": answer_scores.get("legal_defensibility"),
        "citation_quality": answer_scores.get("citation_quality"),
        "would_use_without_modification": answer_scores.get("would_use_without_modification"),
    }


def compile_summary(scored: list) -> dict:
    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(statistics.mean(vals), 4) if vals else None

    claim_f1s = [s["claim_metrics"]["claim_f1"] for s in scored]
    claim_precs = [s["claim_metrics"]["claim_precision"] for s in scored]
    claim_recs = [s["claim_metrics"]["claim_recall"] for s in scored]
    fnrs = [s["claim_metrics"]["false_negative_rate"] for s in scored]
    correctness = [s["answer_correctness"] for s in scored]
    completeness = [s["answer_completeness"] for s in scored]
    defensibility = [s["legal_defensibility"] for s in scored]
    would_use = [s["would_use_without_modification"] for s in scored if s["would_use_without_modification"] is not None]

    by_tier = {}
    for tier in ["simple", "moderate", "complex"]:
        tier_tasks = [s for s in scored if s["tier"] == tier]
        by_tier[tier] = {
            "count": len(tier_tasks),
            "avg_claim_f1": mean([s["claim_metrics"]["claim_f1"] for s in tier_tasks]),
            "avg_correctness": mean([s["answer_correctness"] for s in tier_tasks]),
        }

    by_persona = {}
    for persona, threshold in PERSONA_THRESHOLDS.items():
        persona_tasks = [s for s in scored if s["persona"] == persona]
        by_persona[persona] = {
            "count": len(persona_tasks),
            "threshold": threshold,
            "avg_fnr": mean([s["claim_metrics"]["false_negative_rate"] for s in persona_tasks]),
            "avg_claim_f1": mean([s["claim_metrics"]["claim_f1"] for s in persona_tasks]),
        }

    return {
        "run_date": datetime.now().isoformat(),
        "tasks_scored": len(scored),
        "summary_metrics": {
            "claim_level_precision": mean(claim_precs),
            "claim_level_recall": mean(claim_recs),
            "claim_level_f1": mean(claim_f1s),
            "false_negative_rate_overall": mean(fnrs),
            "answer_correctness_mean": mean(correctness),
            "answer_completeness_mean": mean(completeness),
            "legal_defensibility_mean": mean(defensibility),
            "would_use_without_modification_pct": round(sum(would_use) / len(would_use), 4) if would_use else None,
        },
        "by_tier": by_tier,
        "by_persona": by_persona,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, help="Path to run_evaluation output JSON")
    parser.add_argument("--annotations", required=True, help="Path to human annotation JSON")
    parser.add_argument("--output", required=True, help="Path for scored output JSON")
    args = parser.parse_args()

    results = json.load(open(args.results))
    annotations = json.load(open(args.annotations))

    scored = []
    for r in results:
        task_ann = annotations.get(r["task_id"], {})
        scored.append(score_task(r, task_ann))

    summary = compile_summary(scored)
    output = {"summary": summary, "per_task": scored}
    json.dump(output, open(args.output, "w"), indent=2)

    print(f"Scored {len(scored)} tasks → {args.output}")
    print(f"Overall claim F1: {summary['summary_metrics']['claim_level_f1']}")
    print(f"Overall FNR:      {summary['summary_metrics']['false_negative_rate_overall']}")
    print(f"Answer correctness mean: {summary['summary_metrics']['answer_correctness_mean']}")


if __name__ == "__main__":
    main()
