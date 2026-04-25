#!/bin/bash
# Run all 3 GuideLLM scenarios back-to-back. Results go to results/*.json.
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p results

for scenario in chat code summarize; do
    echo "============================================="
    echo "  Scenario: $scenario"
    echo "============================================="
    guidellm run --config "scenarios/${scenario}.yaml"
done

echo ""
echo "Done. Results:"
ls -la results/
echo ""
echo "Quick stats:"
for f in results/*.json; do
    name=$(basename "$f" .json)
    echo "--- $name ---"
    python3 -c "
import json
d = json.load(open('$f'))
# GuideLLM output schema — adjust if the version you're on differs
summary = d.get('summary', d)
print(f\"  TTFT p99:   {summary.get('time_to_first_token', {}).get('p99', 'n/a')} ms\")
print(f\"  Throughput: {summary.get('output_tokens_per_second', {}).get('mean', 'n/a')} tok/s\")
"
done
