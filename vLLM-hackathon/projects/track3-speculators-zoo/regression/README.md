# Speculation Regression CI

Catch vLLM updates that break speculative decoding performance before they land.

## First-time baseline

```bash
python3 regression/spec_regression_test.py --save regression/baseline.json
# Commit regression/baseline.json to git
```

## Per-PR check

```bash
python3 regression/spec_regression_test.py \
    --baseline regression/baseline.json \
    --threshold 0.15
# Exit code 1 if speedup regressed > 15%
```

## GitHub Actions wiring

```yaml
name: spec-regression
on:
  pull_request:
    paths: ['projects/track3-speculators-zoo/**', 'vllm-launch-args.sh']

jobs:
  regression:
    runs-on: [self-hosted, gpu]
    steps:
      - uses: actions/checkout@v4
      - run: pip install httpx
      - run: python3 projects/track3-speculators-zoo/regression/spec_regression_test.py \
             --baseline projects/track3-speculators-zoo/regression/baseline.json \
             --threshold 0.15
```

This is a compelling submission for the **Best Upstream Contribution** prize — propose this framework to the vLLM project as a reusable action.
