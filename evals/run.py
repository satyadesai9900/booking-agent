"""
Run the agent eval suite.

    python -m evals.run                    # run locally, print a report, write evals/results/*.json
    python -m evals.run --langsmith        # sync the dataset to LangSmith and record an experiment
    python -m evals.run --only flight-no-platform,thanks
    python -m evals.run --judge            # add the LLM-as-judge helpfulness score
    python -m evals.run --live-web         # real web fetches/search instead of a canned page
    python -m evals.run --live-email       # really send emails via Gmail (to EVAL_USER_EMAIL)
    python -m evals.run --live             # both
    python -m evals.run --repeat 5         # run each case 5 times to catch intermittent failures

Exits non-zero when a gate fails: any POLICY score below 100%, or the average QUALITY score
below --min-quality (default 0.8, or EVAL_MIN_QUALITY).
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

import evals  # noqa: F401  (isolates DATA_DIR before the agent modules load)

from evals.cases import CASES, reference_for
from evals.evaluators import POLICY_EVALUATORS, QUALITY_EVALUATORS, make_helpfulness_judge
from evals.harness import QuotaExhausted, build_eval_agent, check_live_email_ready, run_conversation
from agent.chain import ACTIVE_LLM, get_model, get_model_name

DATASET_NAME = "booking-agent-evals"
RESULTS_DIR = Path(__file__).parent / "results"
POLICY_KEYS = {"policy_forbidden_tools", "policy_emails_only_to_owner"}


def _select_cases(only: str) -> List[Dict[str, Any]]:
    if not only:
        return CASES
    wanted = {c.strip() for c in only.split(",") if c.strip()}
    unknown = wanted - {c["id"] for c in CASES}
    if unknown:
        sys.exit(f"Unknown case id(s): {sorted(unknown)}")
    return [c for c in CASES if c["id"] in wanted]


def _evaluators(judge: bool) -> List[Callable]:
    evaluators = POLICY_EVALUATORS + QUALITY_EVALUATORS
    if judge:
        evaluators = evaluators + [make_helpfulness_judge(get_model(temperature=0))]
    return evaluators


def summarize(rows: List[Dict[str, Any]], min_quality: float) -> Dict[str, Any]:
    """Average each metric over the cases it applies to, and decide the CI gates."""
    by_key: Dict[str, List[float]] = {}
    for row in rows:
        for key, res in row["scores"].items():
            if res["score"] is not None:
                by_key.setdefault(key, []).append(res["score"])
    metrics = {k: sum(v) / len(v) for k, v in sorted(by_key.items())}
    quality = [s for k, v in by_key.items() if k not in POLICY_KEYS and k != "helpfulness" for s in v]
    quality_avg = sum(quality) / len(quality) if quality else 0.0
    policy_ok = all(metrics.get(k, 1.0) == 1.0 for k in POLICY_KEYS)
    return {
        "metrics": metrics,
        "quality_avg": quality_avg,
        "policy_passed": policy_ok,
        "quality_passed": quality_avg >= min_quality,
        "min_quality": min_quality,
    }


def print_report(rows: List[Dict[str, Any]], summary: Dict[str, Any]) -> None:
    print(f"\nModel: {ACTIVE_LLM} / {get_model_name()}   Cases: {len(rows)}\n")
    for row in rows:
        failed = {k: r for k, r in row["scores"].items() if r["score"] is not None and r["score"] < 1}
        mark = "FAIL" if any(k in POLICY_KEYS for k in failed) else ("warn" if failed else " ok ")
        print(f"[{mark}] {row['case_id']}")
        for key, res in failed.items():
            print(f"         {key} = {res['score']:.2f}  {res['comment']}")
    print("\nMetric averages:")
    for key, value in summary["metrics"].items():
        tag = "POLICY " if key in POLICY_KEYS else "quality"
        print(f"  {tag}  {key:<30} {value:6.1%}")
    print(f"\nPolicy gate (100% required):          {'PASS' if summary['policy_passed'] else 'FAIL'}")
    print(f"Quality gate (avg {summary['quality_avg']:.1%} >= {summary['min_quality']:.0%}):  "
          f"{'PASS' if summary['quality_passed'] else 'FAIL'}")


def run_local(cases: List[Dict[str, Any]], judge: bool = False,
              live_web: bool = False, live_email: bool = False, repeat: int = 1) -> List[Dict[str, Any]]:
    """Run every case in-process (`repeat` times each) and score it. Returns one row per run."""
    agent = build_eval_agent()
    evaluators = _evaluators(judge)
    rows = []
    runs = [(case, n) for case in cases for n in range(1, repeat + 1)]
    for idx, (case, n) in enumerate(runs, 1):
        label = case["id"] if repeat == 1 else f"{case['id']}#{n}"
        print(f"  ({idx}/{len(runs)}) {label}", flush=True)
        try:
            outputs = run_conversation(agent, case["turns"], case_id=case["id"],
                                       live_web=live_web, live_email=live_email)
        except QuotaExhausted as exc:
            print(f"\nStopped early: provider daily quota exhausted.\n  {exc}")
            break
        reference = reference_for(case)
        scores = {}
        for evaluator in evaluators:
            res = evaluator(outputs, reference)
            scores[res["key"]] = res
        rows.append({"case_id": label, "category": case["category"], "outputs": outputs, "scores": scores})
    return rows


def sync_dataset(client, cases: List[Dict[str, Any]]) -> None:
    """Create or update the LangSmith dataset so it mirrors evals/cases.py (keyed by case id)."""
    if client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
    else:
        dataset = client.create_dataset(DATASET_NAME, description="Booking agent eval cases (evals/cases.py)")
    existing = {ex.metadata.get("case_id"): ex for ex in client.list_examples(dataset_id=dataset.id) if ex.metadata}
    for case in cases:
        inputs = {"case_id": case["id"], "turns": case["turns"]}
        outputs = reference_for(case)
        metadata = {"case_id": case["id"], "category": case["category"]}
        ex = existing.get(case["id"])
        if ex is None:
            client.create_example(inputs=inputs, outputs=outputs, metadata=metadata, dataset_id=dataset.id)
        elif ex.inputs != inputs or ex.outputs != outputs:
            client.update_example(ex.id, inputs=inputs, outputs=outputs, metadata=metadata)


def run_langsmith(cases: List[Dict[str, Any]], judge: bool = False,
                  live_web: bool = False, live_email: bool = False, repeat: int = 1) -> List[Dict[str, Any]]:
    """Run the suite as a LangSmith experiment. Returns rows in the same shape as run_local."""
    from langsmith import Client, evaluate

    client = Client()
    sync_dataset(client, CASES)
    agent = build_eval_agent()
    wanted = {c["id"] for c in cases}
    data = [ex for ex in client.list_examples(dataset_name=DATASET_NAME) if ex.inputs.get("case_id") in wanted]

    def target(inputs: Dict[str, Any]) -> Dict[str, Any]:
        return run_conversation(agent, inputs["turns"], case_id=inputs["case_id"],
                                live_web=live_web, live_email=live_email)

    results = evaluate(
        target,
        data=data,
        evaluators=_evaluators(judge),
        experiment_prefix=f"{ACTIVE_LLM}-{get_model_name()}".replace("/", "-"),
        metadata={"llm_provider": ACTIVE_LLM, "llm_model": get_model_name(), "git_sha": os.getenv("GITHUB_SHA", "local"),
                  "live_web": live_web, "live_email": live_email},
        max_concurrency=2,
        num_repetitions=repeat,
        client=client,
    )
    rows = []
    for item in results:
        scores = {r.key: {"key": r.key, "score": r.score, "comment": r.comment or ""}
                  for r in item["evaluation_results"]["results"]}
        case_id = item["example"].inputs.get("case_id")
        rows.append({"case_id": case_id, "category": item["example"].metadata.get("category"),
                     "outputs": item["run"].outputs, "scores": scores})
    print(f"\nLangSmith experiment: {results.experiment_name}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--langsmith", action="store_true", help="record the run as a LangSmith experiment")
    parser.add_argument("--only", default="", help="comma-separated case ids to run")
    parser.add_argument("--judge", action="store_true", help="add the LLM-as-judge helpfulness score")
    parser.add_argument("--live-web", action="store_true", help="use real web fetches and search")
    parser.add_argument("--live-email", action="store_true", help="send real emails via Gmail to EVAL_USER_EMAIL")
    parser.add_argument("--live", action="store_true", help="shorthand for --live-web --live-email")
    parser.add_argument("--repeat", type=int, default=1, help="run each case N times")
    parser.add_argument("--min-quality", type=float, default=float(os.getenv("EVAL_MIN_QUALITY", "0.8")))
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    live_web = args.live or args.live_web
    live_email = args.live or args.live_email
    if live_email:
        try:
            check_live_email_ready()
        except RuntimeError as exc:
            sys.exit(f"Cannot run with live email: {exc}")

    cases = _select_cases(args.only)
    mode = f"web={'live' if live_web else 'canned'}, email={'live' if live_email else 'outbox only'}"
    print(f"Running {len(cases)} eval case(s) against {ACTIVE_LLM} / {get_model_name()} ({mode})")
    runner = run_langsmith if args.langsmith else run_local
    rows = runner(cases, args.judge, live_web=live_web, live_email=live_email, repeat=max(1, args.repeat))
    expected_runs = len(cases) * max(1, args.repeat)
    if not rows:
        sys.exit("No cases completed.")
    summary = summarize(rows, args.min_quality)
    summary["incomplete"] = len(rows) < expected_runs
    print_report(rows, summary)
    if summary["incomplete"]:
        print(f"\nINCOMPLETE: only {len(rows)} of {expected_runs} runs finished; gates are not meaningful.")

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = RESULTS_DIR / f"{stamp}-{ACTIVE_LLM}.json"
    out_file.write_text(json.dumps({"model": get_model_name(), "provider": ACTIVE_LLM, "mode": mode, "summary": summary,
                                    "cases": rows}, indent=2, default=str), encoding="utf-8")
    print(f"\nFull results: {out_file}")
    if summary["incomplete"]:
        return 2
    return 0 if summary["policy_passed"] and summary["quality_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
