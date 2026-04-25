# Reward Ranker — Build a Human Feedback Loop for LLM Alignment

**Level:** Beginner | **Topic:** Reinforcement Learning | **Tier:** 1 (App Builder) | **GPU:** 1x L40S (48 GB)

Build a Gradio app that lets you play "judge" — the LLM generates two
different responses to the same prompt, and you pick the better one. Your
preferences are collected into a dataset that is then used to train a **reward
model**: a small classifier that learns to predict which responses humans prefer.

This is the foundation of RLHF (Reinforcement Learning from Human Feedback),
the technique used to align ChatGPT, Claude, and every modern chat model.

---

## Quick Start

```bash
# 1. Start vLLM to power response generation
bash /workspace/start_vllm_server.sh

# 2. Launch the preference collection app
python3 collect_preferences.py
# Open http://localhost:7860 — rank at least 20-30 pairs

# 3. Train a reward model on your preferences
python3 train_reward_model.py

# 4. See the reward model score new responses
python3 score_responses.py
```

---

## How RLHF Works (Big Picture)

```
 Step 1: Generate           Step 2: Human Ranks        Step 3: Train Reward Model
 ================           ===================        ==========================
 Prompt --> LLM             "Which is better?"          Learns to predict
      |-> Response A  --->   Human picks B     --->     human preference
      |-> Response B         (preference pair)          (reward score 0-1)

 Step 4 (future): Use reward model to fine-tune the LLM via RL (PPO/GRPO)
```

This project covers **Steps 1-3**. Step 4 is the natural extension
(see the Intermediate "Align It" project).

---

## Files

| File | Purpose |
|---|---|
| `collect_preferences.py` | Gradio app: shows two responses, you pick the winner |
| `train_reward_model.py` | Trains a reward model on your collected preferences using TRL |
| `score_responses.py` | Uses the trained reward model to score new responses |
| `sample_prompts.json` | Curated prompts designed to surface quality differences |

---

## What You'll Learn

| Concept | What it means |
|---|---|
| **Preference pair** | Two responses to the same prompt, labeled "chosen" and "rejected" |
| **Reward model** | A model that takes (prompt, response) and outputs a scalar reward score |
| **RLHF** | Using the reward model as a signal to improve the base LLM |
| **Temperature sampling** | Higher temperature = more diverse (and sometimes worse) responses |

---

## Ideas to Extend

- **Collect more data:** Rank 100+ pairs for a stronger reward model
- **Domain-specific ranking:** Focus on code quality, safety, or helpfulness
- **Leaderboard:** Score multiple models with your reward model and rank them
- **Export for alignment:** Save your preferences in the Anthropic HH-RLHF format
- **Graduate to DPO:** Use your preference data with the Align It project

---

## Why This Matters

Every production LLM goes through alignment:
- **Safety:** Reward models help detect harmful or biased outputs
- **Quality:** Human preferences capture nuances that automated metrics miss
- **Customization:** Enterprise teams train reward models on their own quality standards
- **Evaluation:** Reward models serve as automated evaluators in CI/CD pipelines
