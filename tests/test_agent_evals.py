"""
Runs the full eval suite against the configured LLM provider.
Skipped unless that provider's API key is set. Run with:  pytest -m llm
"""

import os

import pytest

from agent.chain import is_api_key_configured
from evals.cases import CASES
from evals.run import print_report, run_local, summarize

pytestmark = pytest.mark.llm


@pytest.mark.skipif(not is_api_key_configured(), reason="LLM provider API key not configured")
def test_agent_passes_eval_gates():
    rows = run_local(CASES)
    summary = summarize(rows, min_quality=float(os.getenv("EVAL_MIN_QUALITY", "0.8")))
    print_report(rows, summary)

    policy_failures = [
        f"{r['case_id']}: {k} {res['comment']}"
        for r in rows for k, res in r["scores"].items()
        if k.startswith("policy_") and res["score"] is not None and res["score"] < 1
    ]
    assert not policy_failures, "Policy violations:\n" + "\n".join(policy_failures)
    assert summary["quality_passed"], f"Quality {summary['quality_avg']:.1%} below {summary['min_quality']:.0%}"
