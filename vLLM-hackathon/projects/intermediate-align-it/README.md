# Align It — Fine-tune an LLM with Direct Preference Optimization (DPO)

**Level:** Intermediate | **Topic:** Reinforcement Learning | **Tier:** 2 (Performance) | **GPU:** 2x A100 (80 GB)

Go beyond reward modeling — actually **change the model's behavior** using
Direct Preference Optimization (DPO). You'll take a preference dataset, run
DPO training on Llama 3.1 8B with LoRA adapters, and serve the aligned model
through vLLM to see measurable differences in response quality.

DPO is the technique behind many commercial LLM alignment pipelines. Unlike
classic RLHF (which requires a separate reward model + PPO), DPO directly
optimizes the policy model from preference pairs — simpler, more stable,
and increasingly the industry standard.

---

## Quick Start

```bash
# 1. Generate preference data from the base model
python3 generate_preferences.py

# 2. Run DPO training with LoRA
python3 train_dpo.py

# 3. Serve the aligned model and compare before/after
bash serve_aligned.sh

# 4. Interactive comparison: base vs aligned
python3 evaluate_alignment.py
```

---

## How DPO Works

```
Traditional RLHF:
  Preferences -> Train Reward Model -> PPO fine-tune (complex, unstable)

DPO (Direct Preference Optimization):
  Preferences -> Direct policy update (one step, stable, same result)

  Loss = -log sigmoid(beta * (log pi(chosen) - log pi(rejected)
                              - log pi_ref(chosen) + log pi_ref(rejected)))

  In plain English: make the model more likely to produce "chosen" responses
  and less likely to produce "rejected" responses, relative to the base model.
```

---

## Files

| File | Purpose |
|---|---|
| `generate_preferences.py` | Creates preference pairs by sampling the base model at different temperatures |
| `train_dpo.py` | DPO training on Llama 3.1 8B using TRL + LoRA (memory-efficient) |
| `serve_aligned.sh` | Serves both base and aligned models for comparison |
| `evaluate_alignment.py` | Side-by-side evaluation with automated and manual scoring |

---

## What You'll Learn

| Concept | What it means |
|---|---|
| **DPO** | Direct Preference Optimization — aligns models without a reward model |
| **LoRA** | Low-Rank Adaptation — trains only ~1% of parameters, uses minimal VRAM |
| **KL divergence** | Keeps the aligned model close to the base, prevents catastrophic forgetting |
| **Beta parameter** | Controls alignment strength — too high = ignores preferences, too low = overfits |
| **Win rate** | Fraction of prompts where aligned model is preferred over base |

---

## Ideas to Extend

- **Custom preference data:** Collect your own with the Reward Ranker project
- **Sweep beta:** Try beta=0.05, 0.1, 0.2, 0.5 and measure win rate at each
- **Domain-specific alignment:** Focus on code quality, safety, or conciseness
- **GRPO:** Try Group Relative Policy Optimization (TRL's `GRPOTrainer`) as an alternative
- **Evaluation:** Run lm-eval before/after to check for capability regression

---

## Why This Matters for Enterprise

DPO is how companies customize LLMs for their specific needs:
- **Brand voice:** Align responses to match company communication style
- **Safety policies:** Reduce unwanted outputs without retraining from scratch
- **Domain expertise:** Steer the model toward preferred technical approaches
- **Cost efficiency:** LoRA adapters are small (<100 MB) and hot-swappable at serve time
