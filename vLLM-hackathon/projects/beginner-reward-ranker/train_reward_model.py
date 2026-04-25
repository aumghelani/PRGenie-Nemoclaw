"""
Reward Ranker — Train a reward model on collected preferences.

Loads preference pairs from preferences.jsonl and fine-tunes a small
language model to predict which response a human would prefer.

Uses TRL (Transformer Reinforcement Learning) library's RewardTrainer.

Prerequisites:
    - Collected preferences via collect_preferences.py (at least 20 pairs)

Usage:
    python3 train_reward_model.py
    python3 train_reward_model.py --epochs 3 --base-model distilbert-base-uncased
"""

import argparse
import json
import os

import torch
from datasets import Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, TrainingArguments
from trl import RewardTrainer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PREFERENCES_FILE = os.path.join(SCRIPT_DIR, "preferences.jsonl")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "reward-model")


def load_preferences() -> list[dict]:
    """Load preference pairs from JSONL file."""
    if not os.path.exists(PREFERENCES_FILE):
        print(f"ERROR: {PREFERENCES_FILE} not found.")
        print("Run 'python3 collect_preferences.py' and collect at least 20 preference pairs first.")
        raise SystemExit(1)

    records = []
    with open(PREFERENCES_FILE) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records)} preference pairs")

    if len(records) < 10:
        print(f"WARNING: Only {len(records)} pairs. Recommend at least 20 for meaningful training.")

    return records


def prepare_dataset(records: list[dict], tokenizer) -> Dataset:
    """Convert preference pairs into the format expected by RewardTrainer."""
    chosen_texts = []
    rejected_texts = []

    for r in records:
        # Format as: prompt + response
        chosen_text = f"Prompt: {r['prompt']}\n\nResponse: {r['chosen']}"
        rejected_text = f"Prompt: {r['prompt']}\n\nResponse: {r['rejected']}"
        chosen_texts.append(chosen_text)
        rejected_texts.append(rejected_text)

    # Tokenize
    chosen_encodings = tokenizer(
        chosen_texts, truncation=True, padding="max_length",
        max_length=512, return_tensors="pt",
    )
    rejected_encodings = tokenizer(
        rejected_texts, truncation=True, padding="max_length",
        max_length=512, return_tensors="pt",
    )

    dataset = Dataset.from_dict({
        "input_ids_chosen": chosen_encodings["input_ids"],
        "attention_mask_chosen": chosen_encodings["attention_mask"],
        "input_ids_rejected": rejected_encodings["input_ids"],
        "attention_mask_rejected": rejected_encodings["attention_mask"],
    })

    return dataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="distilbert-base-uncased",
                        help="Base model for reward model (small is fine)")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-5)
    args = parser.parse_args()

    print("=" * 55)
    print("  Reward Ranker — Training Reward Model")
    print(f"  Base model: {args.base_model}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 55)

    # Load preferences
    records = load_preferences()

    # Load tokenizer and model
    print(f"\nLoading base model: {args.base_model}")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model, num_labels=1,
    )

    # Prepare dataset
    print("Preparing dataset...")
    dataset = prepare_dataset(records, tokenizer)

    # Split into train/eval
    split = dataset.train_test_split(test_size=0.2, seed=42)
    print(f"  Train: {len(split['train'])} | Eval: {len(split['test'])}")

    # Training
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=5,
        remove_unused_columns=False,
        report_to="none",
    )

    trainer = RewardTrainer(
        model=model,
        args=training_args,
        train_dataset=split["train"],
        eval_dataset=split["test"],
        tokenizer=tokenizer,
    )

    print("\nTraining...")
    trainer.train()

    # Save
    print(f"\nSaving reward model to: {OUTPUT_DIR}")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print("\nDone! Next: python3 score_responses.py")


if __name__ == "__main__":
    main()
