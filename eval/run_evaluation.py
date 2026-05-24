"""
Phase 6B — Evaluation runner.
Runs all 30 benchmark tasks against the live API and saves results.

Usage:
    export AUTH_TOKEN=<clerk_jwt>
    export API_BASE=https://api.regulens.app   # or Render URL
    python eval/run_evaluation.py
"""

import json
import os
import time
from datetime import datetime

import httpx

API_BASE = os.getenv("API_BASE", "https://regulens-api-bnlw.onrender.com")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
TASKS_FILE = "eval/benchmark_tasks.json"
RESULTS_FILE = f"eval/results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
TIMEOUT_SECONDS = 120


def run_benchmark(task: dict, auth_token: str) -> dict:
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    start = time.time()
    try:
        resp = httpx.post(
            f"{API_BASE}/api/query",
            json={"query": task["query"], "persona": task["persona"]},
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        result = resp.json()
        error = None
    except Exception as e:
        result = {}
        error = str(e)

    elapsed = time.time() - start

    audit_hashes = result.get("audit_hashes", [])
    return {
        "task_id": task["id"],
        "tier": task["tier"],
        "persona": task["persona"],
        "query": task["query"],
        "frameworks": task["frameworks"],
        "elapsed_seconds": round(elapsed, 2),
        "overall_verdict": result.get("overall_verdict"),
        "claim_count": len(result.get("claims", [])),
        "avg_confidence": result.get("avg_confidence"),
        "claims": result.get("claims", []),
        "raw_answer": result.get("raw_answer", ""),
        "audit_hash": audit_hashes[-1] if audit_hashes else None,
        "error": error,
    }


def main():
    tasks = json.load(open(TASKS_FILE))
    print(f"Loaded {len(tasks)} tasks from {TASKS_FILE}")
    print(f"API: {API_BASE}")
    print(f"Auth: {'SET' if AUTH_TOKEN else 'NOT SET (unauthenticated)'}")
    print()

    results = []
    for i, task in enumerate(tasks, 1):
        print(f"[{i:02d}/{len(tasks)}] {task['id']} ({task['tier']}) — {task['query'][:60]}...")
        result = run_benchmark(task, AUTH_TOKEN)
        verdict = result.get("overall_verdict") or result.get("error", "ERROR")
        conf = result.get("avg_confidence")
        conf_str = f"{conf:.3f}" if conf is not None else "N/A"
        print(f"         → {verdict} | conf={conf_str} | {result['elapsed_seconds']}s")
        results.append(result)

    json.dump(results, open(RESULTS_FILE, "w"), indent=2)

    # Summary stats
    verdicts = [r["overall_verdict"] for r in results if r["overall_verdict"]]
    errors = [r for r in results if r["error"]]
    elapsed_vals = [r["elapsed_seconds"] for r in results]
    conf_vals = [r["avg_confidence"] for r in results if r["avg_confidence"] is not None]

    print()
    print("=" * 60)
    print(f"Completed {len(results)} tasks → {RESULTS_FILE}")
    print(f"Errors: {len(errors)}")
    print(f"Avg response time: {sum(elapsed_vals)/len(elapsed_vals):.1f}s")
    if conf_vals:
        print(f"Avg confidence: {sum(conf_vals)/len(conf_vals):.3f}")
    from collections import Counter
    print("Verdict distribution:", dict(Counter(verdicts)))


if __name__ == "__main__":
    main()
