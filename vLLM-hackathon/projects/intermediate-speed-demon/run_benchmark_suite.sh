#!/bin/bash
# =============================================================================
# Speed Demon — Full Benchmark Suite
#
# Runs the complete benchmark pipeline:
#   1. Baseline (70B, no speculation)
#   2. Speculative decoding (70B + 8B draft, K=5)
#   3. Generate comparison charts
#
# Usage:
#   bash run_benchmark_suite.sh              # Default: 50 requests per workload
#   NUM_REQUESTS=20 bash run_benchmark_suite.sh  # Quick run
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export NUM_REQUESTS="${NUM_REQUESTS:-50}"

echo "============================================="
echo "  Speed Demon — Full Benchmark Suite"
echo "  Requests per workload: $NUM_REQUESTS"
echo "============================================="
echo ""

# Step 1: Baseline
echo ">>> Step 1/3: Baseline benchmark"
bash "${SCRIPT_DIR}/benchmark_baseline.sh"
echo ""

# Step 2: Speculative decoding
echo ">>> Step 2/3: Speculative decoding benchmark"
bash "${SCRIPT_DIR}/benchmark_speculative.sh"
echo ""

# Step 3: Generate charts
echo ">>> Step 3/3: Generating comparison charts"
python3 "${SCRIPT_DIR}/plot_results.py"

echo ""
echo "============================================="
echo "  Suite complete!"
echo ""
echo "  Results:  ${SCRIPT_DIR}/results/"
echo "  Charts:   ${SCRIPT_DIR}/charts/"
echo ""
echo "  Next steps:"
echo "    - Run 'python3 sweep_spec_tokens.py' to test K=1,3,5,7,9"
echo "    - Open charts/ in Jupyter or download via Brev"
echo "============================================="
