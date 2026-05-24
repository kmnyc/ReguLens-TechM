"""
Phase 6D — Legal-BERT vs base model head-to-head.
Answers Jason Block's challenge: does Legal-BERT NLI outperform generic models
on regulatory text?

Models compared:
  A: nlpaueb/legal-bert-base-uncased  (current)
  B: cross-encoder/nli-deberta-v3-base (general NLI)
  C: facebook/bart-large-mnli          (general NLI, via HF Inference API)

Usage:
    pip install sentence-transformers
    export HUGGINGFACE_API_TOKEN=<token>
    python eval/nli_comparison.py \
        --tasks eval/benchmark_tasks.json \
        --annotations eval/annotations_YYYYMMDD_HHMM.json \
        --output eval/nli_comparison_results.json
"""

import argparse
import json
import os
import time
from datetime import datetime

import requests

HF_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")

MODELS = {
    "legal_bert": "nlpaueb/legal-bert-base-uncased",
    "deberta": "cross-encoder/nli-deberta-v3-base",
    "bart_mnli": "facebook/bart-large-mnli",
}


def load_cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder
    print(f"Loading {model_name}...")
    return CrossEncoder(model_name)


def score_claim_local(model, claim_text: str, source_span: str) -> dict:
    """Run NLI via local CrossEncoder. Returns verdict + confidence."""
    start = time.time()
    scores = model.predict([[source_span, claim_text]])
    elapsed = time.time() - start
    labels = ["contradict", "neutral", "entail"]
    idx = int(scores.argmax())
    return {
        "verdict": labels[idx],
        "confidence": float(scores.max()),
        "latency_ms": round(elapsed * 1000, 1),
        "raw_scores": {labels[i]: float(scores[i]) for i in range(3)},
    }


def score_claim_hf_api(model_id: str, claim_text: str, source_span: str) -> dict:
    """Run NLI via HuggingFace Inference API (for bart-large-mnli)."""
    url = f"https://api-inference.huggingface.co/models/{model_id}"
    payload = {"inputs": {"premise": source_span, "hypothesis": claim_text}}
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    start = time.time()
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        elapsed = time.time() - start

        scores = {item["label"].lower(): item["score"] for item in data[0]}
        verdict = max(scores, key=scores.get)
        confidence = scores[verdict]
        return {
            "verdict": verdict,
            "confidence": round(confidence, 4),
            "latency_ms": round(elapsed * 1000, 1),
            "raw_scores": scores,
        }
    except Exception as e:
        return {"verdict": "error", "confidence": 0.0, "latency_ms": 0, "error": str(e)}


def compute_metrics(predictions: list, human_labels: list) -> dict:
    """
    predictions: list of verdict strings (entail/neutral/contradict)
    human_labels: list of strings (supported/unsupported/contradicted)
    """
    NLI_TO_HUMAN = {"entail": "supported", "neutral": "unsupported", "contradict": "contradicted"}
    assert len(predictions) == len(human_labels)

    classes = ["supported", "unsupported", "contradicted"]
    metrics = {}

    for cls in classes:
        TP = sum(1 for p, h in zip(predictions, human_labels) if NLI_TO_HUMAN.get(p) == cls and h == cls)
        FP = sum(1 for p, h in zip(predictions, human_labels) if NLI_TO_HUMAN.get(p) == cls and h != cls)
        FN = sum(1 for p, h in zip(predictions, human_labels) if NLI_TO_HUMAN.get(p) != cls and h == cls)
        prec = TP / (TP + FP) if (TP + FP) > 0 else 0
        rec = TP / (TP + FN) if (TP + FN) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        metrics[cls] = {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)}

    accuracy = sum(1 for p, h in zip(predictions, human_labels) if NLI_TO_HUMAN.get(p) == h) / len(predictions)

    # False negative rate for compliance: unsupported claims that passed as supported
    fn_compliance = sum(
        1 for p, h in zip(predictions, human_labels)
        if NLI_TO_HUMAN.get(p) == "supported" and h != "supported"
    )
    total_non_supported = sum(1 for h in human_labels if h != "supported")
    fnr = fn_compliance / total_non_supported if total_non_supported > 0 else 0

    return {
        "accuracy": round(accuracy, 4),
        "false_negative_rate_compliance": round(fnr, 4),
        "per_class": metrics,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default="eval/benchmark_tasks.json")
    parser.add_argument("--annotations", required=True, help="Human annotation JSON")
    parser.add_argument("--output", default=f"eval/nli_comparison_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    parser.add_argument("--skip-bart", action="store_true", help="Skip HF API model (no token)")
    args = parser.parse_args()

    tasks = json.load(open(args.tasks))
    annotations = json.load(open(args.annotations))

    # Load local models
    legal_bert = load_cross_encoder(MODELS["legal_bert"])
    deberta = load_cross_encoder(MODELS["deberta"])

    results = {name: {"predictions": [], "latencies": []} for name in MODELS}
    human_labels_all = []
    pairs_evaluated = 0

    for task in tasks:
        task_ann = annotations.get(task["id"], {})
        claims_ann = task_ann.get("claims", {})

        # Use gold_standard_answer as source span proxy if no retrieved spans
        source_span = task.get("gold_standard_answer", task["query"])
        if source_span == "TODO" or not source_span:
            continue

        for claim_id, ann in claims_ann.items():
            claim_text = ann.get("claim_text", "")
            human_label = ann.get("human_label", "")
            if not claim_text or not human_label:
                continue

            human_labels_all.append(human_label)
            pairs_evaluated += 1

            # Legal-BERT
            r = score_claim_local(legal_bert, claim_text, source_span)
            results["legal_bert"]["predictions"].append(r["verdict"])
            results["legal_bert"]["latencies"].append(r["latency_ms"])

            # DeBERTa
            r = score_claim_local(deberta, claim_text, source_span)
            results["deberta"]["predictions"].append(r["verdict"])
            results["deberta"]["latencies"].append(r["latency_ms"])

            # BART via HF API
            if not args.skip_bart:
                r = score_claim_hf_api(MODELS["bart_mnli"], claim_text, source_span)
                results["bart_mnli"]["predictions"].append(r.get("verdict", "error"))
                results["bart_mnli"]["latencies"].append(r["latency_ms"])

    print(f"Evaluated {pairs_evaluated} claim-source pairs")

    comparison = {}
    for model_key, data in results.items():
        if not data["predictions"]:
            continue
        metrics = compute_metrics(data["predictions"], human_labels_all[:len(data["predictions"])])
        avg_latency = sum(data["latencies"]) / len(data["latencies"])
        comparison[model_key] = {
            "model": MODELS[model_key],
            "metrics": metrics,
            "avg_latency_ms": round(avg_latency, 1),
            "pairs_evaluated": len(data["predictions"]),
        }

    # Determine winner by compliance FNR (lower = better) then F1
    def rank_key(item):
        m = item[1]["metrics"]
        return (m["false_negative_rate_compliance"], -m["per_class"].get("supported", {}).get("f1", 0))

    ranked = sorted(comparison.items(), key=rank_key)
    winner = ranked[0][0] if ranked else "unknown"

    output = {
        "run_date": datetime.now().isoformat(),
        "pairs_evaluated": pairs_evaluated,
        "winner": winner,
        "recommendation": f"Use {MODELS.get(winner, winner)} for Agent III NLI verification.",
        "models": comparison,
    }

    json.dump(output, open(args.output, "w"), indent=2)
    print(f"Results → {args.output}")
    print(f"Winner: {winner} (lowest compliance FNR)")
    for name, data in ranked:
        m = data["metrics"]
        print(f"  {name}: FNR={m['false_negative_rate_compliance']} accuracy={m['accuracy']} latency={data['avg_latency_ms']}ms")


if __name__ == "__main__":
    main()
