#!/usr/bin/env bash
# Quick verification that PRClaw can talk to the Brev-hosted vLLM.
# Run from PRDEMO/ root after setting .env to point at Brev.
#
# Usage:
#   bash scripts/test_against_brev.sh
#   bash scripts/test_against_brev.sh http://localhost:5000   # override URL
set -euo pipefail

BASE="${1:-${VLLM_BASE_URL:-http://localhost:5000/v1}}"
# strip trailing /v1 for the bare-server checks
ROOT="${BASE%/v1}"

echo "=== 1) vLLM /v1/models reachable? ==="
curl -sS --max-time 5 "${ROOT}/v1/models" || { echo; echo "FAIL: cannot reach $ROOT/v1/models"; exit 1; }
echo
echo

echo "=== 2) Bare chat completion (no tools) ==="
curl -sS --max-time 30 "${ROOT}/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{"model":"nemotron","messages":[{"role":"user","content":"Say PRCLAW_OK in 5 words."}],"max_tokens":30,"temperature":0.0}' \
  | head -c 800
echo
echo

echo "=== 3) Tool-calling round-trip (the Triage path) ==="
curl -sS --max-time 60 "${ROOT}/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -H 'x-nvext-priority: high' \
  -H 'x-nvext-predicted-osl: 200' \
  -H 'x-nvext-request-class: agent.first' \
  -d '{
    "model":"nemotron",
    "messages":[
      {"role":"system","content":"Return a structured analysis."},
      {"role":"user","content":"PR adds Redis caching but no TTL. Call submit_triage."}
    ],
    "tools":[{"type":"function","function":{
      "name":"submit_triage","description":"x",
      "parameters":{"type":"object","required":["priority"],
        "properties":{"priority":{"type":"string","enum":["high","medium","low"]}}}
    }}],
    "tool_choice":{"type":"function","function":{"name":"submit_triage"}},
    "max_tokens":200,"temperature":0.0
  }' | head -c 1500
echo
echo

echo "=== 4) PRClaw end-to-end pipeline (real LLM) ==="
./.venv/Scripts/python.exe -m pytest tests/test_pipeline_e2e.py::test_pr_pipeline_full_flow -v 2>&1 | tail -20

echo
echo "If steps 1-3 returned data and step 4 PASSED, PRClaw is wired to Brev."
