# Speculative Decoding

Speculative decoding speeds up autoregressive generation by using a small,
fast "draft" model to propose `k` tokens at a time, which a larger "target"
model then verifies in a single forward pass.

## Mechanism

1. Draft model generates `k` candidate tokens (cheap)
2. Target model runs one forward pass over all `k` in parallel
3. Tokens that the target agrees with are accepted immediately
4. First rejected token is replaced with the target's distribution
5. Loop

When the draft model's distribution closely matches the target's, acceptance
rates are high (70-90%) and throughput scales near-linearly with `k`.

## Variants

- **Draft-model speculation**: use any small model of the same architecture
- **EAGLE**: lightweight draft heads trained specifically to match the target
- **Medusa**: multiple independent draft heads added to the target model itself
- **N-gram**: no draft model — speculate from observed token n-grams

## vLLM configuration

```
python3 -m vllm.entrypoints.openai.api_server \
    --model /models/llama-3.1-70b-instruct \
    --speculative-model /models/llama-3.1-8b-instruct \
    --num-speculative-tokens 5
```
